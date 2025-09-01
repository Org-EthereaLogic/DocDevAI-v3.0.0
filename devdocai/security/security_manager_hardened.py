"""
Hardened Security Manager for M010 Security Module
Integrates all hardened security components with enterprise-grade features.
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import logging
import threading
from enum import Enum

# Import existing security components
from .optimized.compliance_optimized import ComplianceManagerOptimized
from .optimized.pii_optimized import PIIDetectorOptimized as PrivacyGuardOptimized
from .optimized.sbom_optimized import SBOMGeneratorOptimized
from .optimized.threat_optimized import ThreatDetectorOptimized
from .compliance_reporter import ComplianceReporter
from .security_manager import SecurityManager as BaseSecurityManager

# Import hardened components
from .hardened.crypto_manager import CryptoManager
from .hardened.threat_intelligence import (
    ThreatIntelligenceEngine, 
    ThreatSeverity, 
    ThreatType,
    ThreatIndicator,
    ThreatEvent
)
from .hardened.zero_trust import (
    ZeroTrustManager,
    Identity,
    Resource,
    AccessContext,
    AccessDecision,
    TrustLevel,
    ResourceType
)
from .hardened.audit_forensics import (
    AuditForensics,
    AuditLevel,
    EventCategory,
    AuditEvent,
    ForensicArtifact
)
from .hardened.security_orchestrator import (
    SecurityOrchestrator,
    SecurityIncident,
    IncidentSeverity,
    IncidentStatus
)

logger = logging.getLogger(__name__)


class SecurityPosture(Enum):
    """Overall security posture levels."""
    CRITICAL = 1  # Under active attack
    HIGH_RISK = 2  # Significant vulnerabilities
    ELEVATED = 3  # Some concerns
    NORMAL = 4  # Standard operations
    HARDENED = 5  # Maximum security


class HardenedSecurityManager:
    """
    Enterprise-grade hardened security manager with advanced features.
    
    Integrates:
    - Advanced cryptographic operations (Ed25519, HMAC)
    - Threat intelligence with real-time correlation
    - Zero-trust architecture enforcement
    - Tamper-proof audit with blockchain chaining
    - Security orchestration and automated response
    - All existing optimized security components
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the hardened security manager."""
        self.config = config or {}
        
        # Initialize base components (from Pass 1 & 2)
        self.compliance_manager = ComplianceManagerOptimized()
        self.privacy_guard = PrivacyGuardOptimized()
        self.sbom_generator = SBOMGeneratorOptimized()
        self.threat_detector = ThreatDetectorOptimized()
        self.compliance_reporter = ComplianceReporter()
        
        # Initialize hardened components (Pass 3)
        self.crypto_manager = CryptoManager()
        self.threat_intelligence = ThreatIntelligenceEngine(
            self.config.get('threat_feeds', {})
        )
        self.zero_trust = ZeroTrustManager(
            self.config.get('zero_trust', {})
        )
        self.audit_forensics = AuditForensics()
        self.security_orchestrator = SecurityOrchestrator(
            self.config.get('soar', {})
        )
        
        # Security posture tracking
        self._security_posture = SecurityPosture.NORMAL
        self._risk_score = 0.0
        self._active_threats: List[ThreatEvent] = []
        self._active_incidents: List[str] = []
        
        # Performance metrics
        self._metrics = {
            'operations_processed': 0,
            'threats_detected': 0,
            'incidents_responded': 0,
            'access_decisions': 0,
            'audit_events': 0
        }
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Start background tasks
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """Start background security monitoring tasks."""
        # Key rotation scheduler
        threading.Timer(86400, self._rotate_keys_task).start()  # Daily
        
        # Threat feed update
        threading.Timer(3600, self._update_threat_feeds_task).start()  # Hourly
        
        # Security posture assessment
        threading.Timer(300, self._assess_security_posture_task).start()  # Every 5 min
    
    def _rotate_keys_task(self):
        """Background task for key rotation."""
        try:
            self.crypto_manager.rotate_keys('master')
            self.audit_forensics.log_event(
                level=AuditLevel.INFO,
                category=EventCategory.SECURITY,
                action='key_rotation',
                actor='system',
                target='master_keys',
                result='success'
            )
        except Exception as e:
            logger.error(f"Key rotation failed: {e}")
        
        # Reschedule
        threading.Timer(86400, self._rotate_keys_task).start()
    
    def _update_threat_feeds_task(self):
        """Background task for threat feed updates."""
        asyncio.create_task(self._update_threat_feeds())
        
        # Reschedule
        threading.Timer(3600, self._update_threat_feeds_task).start()
    
    async def _update_threat_feeds(self):
        """Update threat intelligence feeds."""
        feeds = self.config.get('threat_feeds', {})
        
        for feed_name, feed_config in feeds.items():
            try:
                indicators = await self.threat_intelligence.fetch_threat_feed(
                    feed_config['url'],
                    feed_config.get('type', 'misp')
                )
                
                for indicator in indicators:
                    self.threat_intelligence.add_indicator(indicator)
                
                logger.info(f"Updated {feed_name}: {len(indicators)} indicators")
            except Exception as e:
                logger.error(f"Failed to update {feed_name}: {e}")
    
    def _assess_security_posture_task(self):
        """Background task for security posture assessment."""
        self._assess_security_posture()
        
        # Reschedule
        threading.Timer(300, self._assess_security_posture_task).start()
    
    def _assess_security_posture(self):
        """Assess overall security posture."""
        with self._lock:
            # Calculate risk score
            risk_factors = {
                'active_threats': len(self._active_threats) * 0.2,
                'active_incidents': len(self._active_incidents) * 0.15,
                'failed_auth': self._get_failed_auth_rate() * 0.1,
                'compliance_gaps': self._get_compliance_gaps() * 0.15,
                'vulnerability_score': self._get_vulnerability_score() * 0.2,
                'anomaly_score': self._get_anomaly_score() * 0.2
            }
            
            self._risk_score = min(1.0, sum(risk_factors.values()))
            
            # Determine posture
            if self._risk_score >= 0.8:
                self._security_posture = SecurityPosture.CRITICAL
            elif self._risk_score >= 0.6:
                self._security_posture = SecurityPosture.HIGH_RISK
            elif self._risk_score >= 0.4:
                self._security_posture = SecurityPosture.ELEVATED
            elif self._risk_score >= 0.2:
                self._security_posture = SecurityPosture.NORMAL
            else:
                self._security_posture = SecurityPosture.HARDENED
            
            # Log posture change
            self.audit_forensics.log_event(
                level=AuditLevel.INFO,
                category=EventCategory.SECURITY,
                action='posture_assessment',
                actor='system',
                target='security_posture',
                result=self._security_posture.name,
                metadata={'risk_score': self._risk_score, 'factors': risk_factors}
            )
    
    def _get_failed_auth_rate(self) -> float:
        """Get failed authentication rate."""
        # Query recent auth events
        audit_trail = self.audit_forensics.get_audit_trail(limit=100)
        auth_events = [
            e for e in audit_trail 
            if e.get('category') == EventCategory.AUTHENTICATION.value
        ]
        
        if not auth_events:
            return 0.0
        
        failed = sum(1 for e in auth_events if e.get('result') == 'failure')
        return failed / len(auth_events)
    
    def _get_compliance_gaps(self) -> float:
        """Get compliance gap score."""
        compliance_status = self.compliance_manager.get_compliance_status()
        
        total_requirements = sum(
            len(framework.get('requirements', [])) 
            for framework in compliance_status.values()
        )
        
        if total_requirements == 0:
            return 0.0
        
        met_requirements = sum(
            framework.get('compliance_score', 0) * len(framework.get('requirements', [])) / 100
            for framework in compliance_status.values()
        )
        
        return 1.0 - (met_requirements / total_requirements)
    
    def _get_vulnerability_score(self) -> float:
        """Get vulnerability score from threat detection."""
        threats = self.threat_detector.get_threat_summary()
        
        if threats['total_threats'] == 0:
            return 0.0
        
        # Weight by severity
        severity_weights = {
            'critical': 1.0,
            'high': 0.7,
            'medium': 0.4,
            'low': 0.1
        }
        
        weighted_score = sum(
            threats.get(f'{sev}_threats', 0) * weight
            for sev, weight in severity_weights.items()
        )
        
        return min(1.0, weighted_score / 10)  # Normalize
    
    def _get_anomaly_score(self) -> float:
        """Get anomaly score from threat intelligence."""
        # Simplified anomaly score calculation
        stats = self.threat_intelligence.get_threat_statistics()
        
        critical_indicators = stats.get('severity_distribution', {}).get('critical', 0)
        high_indicators = stats.get('severity_distribution', {}).get('high', 0)
        
        return min(1.0, (critical_indicators * 0.1 + high_indicators * 0.05))
    
    def process_access_request(
        self,
        identity_id: str,
        resource_id: str,
        action: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Process access request through zero-trust verification.
        
        Returns:
            Tuple of (allowed, details)
        """
        with self._lock:
            start_time = time.time()
            
            # Get identity and resource
            identity = self.zero_trust._identities.get(identity_id)
            resource = self.zero_trust._resources.get(resource_id)
            
            if not identity or not resource:
                self.audit_forensics.log_event(
                    level=AuditLevel.WARNING,
                    category=EventCategory.AUTHORIZATION,
                    action='access_request',
                    actor=identity_id,
                    target=resource_id,
                    result='denied',
                    metadata={'reason': 'entity_not_found'}
                )
                return False, {'reason': 'Entity not found'}
            
            # Create access context
            access_context = AccessContext(
                identity=identity,
                resource=resource,
                action=action,
                timestamp=datetime.utcnow(),
                location=context.get('location') if context else None,
                device_id=context.get('device_id') if context else None,
                network_zone=context.get('network_zone') if context else None,
                session_id=context.get('session_id') if context else None,
                risk_indicators=context.get('risk_indicators', []) if context else []
            )
            
            # Zero-trust verification
            decision, details = self.zero_trust.verify_access(access_context)
            
            # Check threat intelligence
            if context and 'source_ip' in context:
                threat_indicator = self.threat_intelligence.check_indicator(
                    context['source_ip']
                )
                if threat_indicator and threat_indicator.severity in [
                    ThreatSeverity.CRITICAL, 
                    ThreatSeverity.HIGH
                ]:
                    decision = AccessDecision.DENY
                    details['threat_detected'] = True
            
            # Sign access token if allowed
            if decision == AccessDecision.ALLOW:
                permissions = self.zero_trust.enforce_least_privilege(
                    identity_id, 
                    resource_id
                )
                token = self.zero_trust.create_access_token(
                    identity, 
                    resource, 
                    permissions
                )
                details['access_token'] = token
                details['permissions'] = permissions
            
            # Audit the access attempt
            self.audit_forensics.log_event(
                level=AuditLevel.INFO if decision == AccessDecision.ALLOW else AuditLevel.WARNING,
                category=EventCategory.AUTHORIZATION,
                action='access_request',
                actor=identity_id,
                target=resource_id,
                result=decision.value,
                metadata=details,
                source_ip=context.get('source_ip') if context else None,
                session_id=context.get('session_id') if context else None
            )
            
            # Update metrics
            self._metrics['access_decisions'] += 1
            
            # Performance tracking
            elapsed = time.time() - start_time
            details['processing_time'] = elapsed
            
            return decision == AccessDecision.ALLOW, details
    
    def detect_and_respond(
        self,
        data: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Detect threats and automatically respond.
        
        Args:
            data: Data to analyze
            context: Additional context
        
        Returns:
            Detection and response results
        """
        with self._lock:
            results = {
                'threats_detected': [],
                'yara_matches': [],
                'anomalies': [],
                'incidents_created': [],
                'playbooks_triggered': [],
                'actions_taken': []
            }
            
            # YARA-based threat hunting
            yara_matches = self.threat_intelligence.hunt_threats(data)
            results['yara_matches'] = yara_matches
            
            # Check for known indicators
            if context and 'indicators' in context:
                for indicator_value in context['indicators']:
                    threat_indicator = self.threat_intelligence.check_indicator(
                        indicator_value
                    )
                    if threat_indicator:
                        results['threats_detected'].append({
                            'indicator': indicator_value,
                            'type': threat_indicator.type,
                            'severity': threat_indicator.severity.value,
                            'source': threat_indicator.source
                        })
            
            # Anomaly detection
            if context and 'features' in context:
                is_anomaly, score = self.threat_intelligence.detect_anomalies(
                    context['features']
                )
                if is_anomaly:
                    results['anomalies'].append({
                        'type': 'behavioral',
                        'score': score,
                        'detected_at': datetime.utcnow().isoformat()
                    })
            
            # Create incident if threats detected
            if yara_matches or results['threats_detected'] or results['anomalies']:
                # Determine severity
                severity = IncidentSeverity.LOW
                if any(m.get('severity') == 'critical' for m in yara_matches):
                    severity = IncidentSeverity.CRITICAL
                elif any(m.get('severity') == 'high' for m in yara_matches):
                    severity = IncidentSeverity.HIGH
                elif yara_matches or results['threats_detected']:
                    severity = IncidentSeverity.MEDIUM
                
                # Create incident
                incident_id = self.security_orchestrator.create_incident(
                    title=f"Automated Threat Detection - {datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
                    description=f"Detected {len(yara_matches)} YARA matches, "
                               f"{len(results['threats_detected'])} threat indicators, "
                               f"{len(results['anomalies'])} anomalies",
                    incident_type='malware' if yara_matches else 'suspicious_behavior',
                    severity=severity,
                    affected_assets=context.get('affected_assets', ['unknown']),
                    indicators=results['threats_detected']
                )
                
                results['incidents_created'].append(incident_id)
                self._active_incidents.append(incident_id)
                
                # Log to audit
                self.audit_forensics.log_event(
                    level=AuditLevel.CRITICAL if severity == IncidentSeverity.CRITICAL else AuditLevel.WARNING,
                    category=EventCategory.SECURITY,
                    action='threat_detected',
                    actor='threat_detection_system',
                    target='system',
                    result='incident_created',
                    metadata={'incident_id': incident_id, 'detection_results': results},
                    correlation_id=incident_id
                )
                
                # Update metrics
                self._metrics['threats_detected'] += len(yara_matches) + len(results['threats_detected'])
                self._metrics['incidents_responded'] += 1
            
            return results
    
    def collect_forensic_evidence(
        self,
        artifact_type: str,
        source: str,
        data: bytes,
        incident_id: Optional[str] = None
    ) -> str:
        """
        Collect and store forensic evidence.
        
        Returns:
            Artifact ID
        """
        # Sign the artifact for integrity
        signature, sig_metadata = self.crypto_manager.sign_data(data)
        
        # Collect artifact
        artifact_id = self.audit_forensics.collect_artifact(
            artifact_type=artifact_type,
            source=source,
            data=data,
            metadata={
                'signature': signature.hex(),
                'signature_metadata': sig_metadata,
                'incident_id': incident_id,
                'collected_by': 'forensics_system'
            }
        )
        
        # If associated with incident, update incident
        if incident_id:
            incident = self.security_orchestrator.get_incident(incident_id)
            if incident:
                incident.metadata['artifacts'] = incident.metadata.get('artifacts', [])
                incident.metadata['artifacts'].append(artifact_id)
        
        return artifact_id
    
    def verify_audit_integrity(
        self,
        start_block: int = 0,
        end_block: Optional[int] = None
    ) -> Tuple[bool, List[str]]:
        """
        Verify audit log integrity using blockchain verification.
        
        Returns:
            Tuple of (is_valid, issues)
        """
        return self.audit_forensics.verify_integrity(start_block, end_block)
    
    def generate_security_report(
        self,
        report_type: str = 'executive',
        period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Generate comprehensive security report.
        
        Args:
            report_type: Type of report (executive, technical, compliance)
            period_days: Report period in days
        
        Returns:
            Report data
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=period_days)
        
        report = {
            'report_type': report_type,
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'security_posture': {
                'current': self._security_posture.name,
                'risk_score': self._risk_score,
                'trend': self._calculate_posture_trend()
            },
            'metrics': dict(self._metrics),
            'threat_intelligence': self.threat_intelligence.get_threat_statistics(),
            'zero_trust': self.zero_trust.get_statistics(),
            'audit': self.audit_forensics.get_statistics(),
            'soar': self.security_orchestrator.get_statistics(),
            'compliance': {}
        }
        
        # Add compliance reports
        for framework in ['SOC2', 'GDPR', 'HIPAA']:
            try:
                compliance_report = self.audit_forensics.generate_compliance_report(
                    start_date, 
                    end_date, 
                    framework
                )
                report['compliance'][framework] = compliance_report
            except Exception as e:
                logger.error(f"Failed to generate {framework} report: {e}")
        
        # Executive summary
        if report_type == 'executive':
            report['executive_summary'] = self._generate_executive_summary(report)
        
        # Technical details
        elif report_type == 'technical':
            report['technical_details'] = {
                'active_threats': [t.__dict__ for t in self._active_threats],
                'recent_incidents': self._get_recent_incidents(),
                'vulnerability_analysis': self._get_vulnerability_analysis()
            }
        
        return report
    
    def _calculate_posture_trend(self) -> str:
        """Calculate security posture trend."""
        # Simplified trend calculation
        recent_events = self.audit_forensics.get_audit_trail(limit=1000)
        
        critical_events = sum(
            1 for e in recent_events 
            if e.get('level') == AuditLevel.CRITICAL.value
        )
        
        if critical_events > 10:
            return 'degrading'
        elif critical_events > 5:
            return 'stable'
        else:
            return 'improving'
    
    def _generate_executive_summary(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary."""
        return {
            'key_findings': [
                f"Security posture: {report['security_posture']['current']}",
                f"Risk score: {report['security_posture']['risk_score']:.2%}",
                f"Active incidents: {report['soar']['active_incidents']}",
                f"Threats detected: {report['metrics']['threats_detected']}"
            ],
            'recommendations': self._get_security_recommendations(),
            'compliance_summary': {
                framework: data.get('statistics', {})
                for framework, data in report['compliance'].items()
            }
        }
    
    def _get_recent_incidents(self) -> List[Dict[str, Any]]:
        """Get recent security incidents."""
        incidents = []
        
        for incident_id in self._active_incidents[-10:]:
            incident = self.security_orchestrator.get_incident(incident_id)
            if incident:
                incidents.append({
                    'id': incident.incident_id,
                    'title': incident.title,
                    'severity': incident.severity.name,
                    'status': incident.status.value,
                    'created_at': incident.created_at.isoformat()
                })
        
        return incidents
    
    def _get_vulnerability_analysis(self) -> Dict[str, Any]:
        """Get vulnerability analysis."""
        return {
            'threat_summary': self.threat_detector.get_threat_summary(),
            'privacy_risks': self.privacy_guard.get_statistics(),
            'compliance_gaps': self.compliance_manager.get_compliance_status()
        }
    
    def _get_security_recommendations(self) -> List[str]:
        """Get security recommendations based on current posture."""
        recommendations = []
        
        if self._security_posture == SecurityPosture.CRITICAL:
            recommendations.extend([
                "Immediate incident response required",
                "Isolate affected systems",
                "Engage incident response team"
            ])
        elif self._security_posture == SecurityPosture.HIGH_RISK:
            recommendations.extend([
                "Review and patch critical vulnerabilities",
                "Increase monitoring frequency",
                "Conduct security assessment"
            ])
        elif self._security_posture == SecurityPosture.ELEVATED:
            recommendations.extend([
                "Review security policies",
                "Update threat intelligence feeds",
                "Conduct security awareness training"
            ])
        else:
            recommendations.extend([
                "Maintain current security practices",
                "Continue regular security assessments",
                "Keep security tools updated"
            ])
        
        return recommendations
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for all components."""
        return {
            'hardened_components': {
                'crypto_operations': self.crypto_manager.get_key_info('master'),
                'threat_intelligence': self.threat_intelligence.get_threat_statistics(),
                'zero_trust': self.zero_trust.get_statistics(),
                'audit_forensics': self.audit_forensics.get_statistics(),
                'soar': self.security_orchestrator.get_statistics()
            },
            'optimized_components': {
                'compliance': self.compliance_manager.get_statistics(),
                'privacy': self.privacy_guard.get_statistics(),
                'sbom': self.sbom_generator.get_statistics(),
                'threat_detection': self.threat_detector.get_threat_summary()
            },
            'overall_metrics': self._metrics,
            'security_posture': {
                'level': self._security_posture.name,
                'risk_score': self._risk_score
            }
        }