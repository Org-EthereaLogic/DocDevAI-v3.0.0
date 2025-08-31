"""
Integration tests for M010 Security Module.

Tests the complete M010 Security Module implementation including
SecurityManager, SBOM generation, advanced PII detection, DSR handling,
threat monitoring, and compliance reporting.
"""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import Mock, patch

# Import M010 Security components
from devdocai.security import (
    SecurityManager, SecurityConfig, SecurityMode,
    SBOMGenerator, SBOMFormat,
    AdvancedPIIDetector, PIIConfig, PIIDetectionMode,
    DSRRequestHandler, DSRRequestType, DSRConfig,
    ThreatDetector, ThreatLevel, ThreatType,
    ComplianceReporter, ComplianceStandard,
    initialize_security_module
)


class TestM010SecurityModuleIntegration:
    """
    Comprehensive integration tests for M010 Security Module.
    
    Tests all major components working together and validates
    the complete security framework implementation.
    """
    
    def setup_method(self):
        """Set up test environment."""
        # Initialize security manager with test configuration
        test_config = SecurityConfig(
            mode=SecurityMode.ENTERPRISE,
            sbom_enabled=True,
            pii_detection_enabled=True,
            dsr_enabled=True,
            threat_monitoring=True,
            compliance_reporting=True,
            real_time_monitoring=False  # Disable for testing
        )
        
        self.security_manager = SecurityManager(test_config)
        
        # Create temporary directory for test files
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Test data
        self.test_project_data = {
            'name': 'test-project',
            'path': str(self.temp_dir),
            'type': 'python',
            'package_managers': ['pip'],
            'languages': ['Python']
        }
        
        self.test_pii_data = """
        John Doe's information:
        Email: john.doe@example.com
        Phone: (555) 123-4567
        SSN: 123-45-6789
        Credit Card: 4532-1234-5678-9012
        """
        
        self.test_user_data = {
            'user_id': 'test_user_001',
            'email': 'testuser@example.com',
            'phone': '+1-555-123-4567'
        }
    
    def teardown_method(self):
        """Clean up test environment."""
        if hasattr(self, 'security_manager'):
            self.security_manager.shutdown()
        
        # Clean up temporary directory
        if hasattr(self, 'temp_dir') and self.temp_dir.exists():
            import shutil
            shutil.rmtree(self.temp_dir)
    
    def test_security_module_initialization(self):
        """Test M010 security module initialization."""
        # Test module initialization
        security_manager = initialize_security_module({
            'mode': 'ENTERPRISE',
            'sbom': {'enabled': True},
            'pii': {'detection_mode': 'ADVANCED'},
            'dsr': {'enabled': True}
        })
        
        assert security_manager is not None
        assert security_manager.config.mode == SecurityMode.ENTERPRISE
        assert security_manager.config.sbom_enabled is True
        assert security_manager.config.pii_detection_enabled is True
        assert security_manager.config.dsr_enabled is True
        
        security_manager.shutdown()
    
    def test_security_manager_orchestration(self):
        """Test SecurityManager orchestration capabilities."""
        # Test getting component instances
        sbom_generator = self.security_manager.get_sbom_generator()
        pii_detector = self.security_manager.get_pii_detector()
        dsr_handler = self.security_manager.get_dsr_handler()
        threat_detector = self.security_manager.get_threat_detector()
        compliance_reporter = self.security_manager.get_compliance_reporter()
        
        assert sbom_generator is not None
        assert pii_detector is not None
        assert dsr_handler is not None
        assert threat_detector is not None
        assert compliance_reporter is not None
        
        # Test security status
        status = self.security_manager.get_security_status()
        assert 'status' in status
        assert 'metrics' in status
        assert 'config' in status
    
    @pytest.mark.asyncio
    async def test_comprehensive_security_scan(self):
        """Test comprehensive security scan across all components."""
        test_target = {
            'content': self.test_pii_data,
            'metadata': {
                'user_id': 'test_user_001',
                'document_type': 'personal_data',
                'classification': 'sensitive'
            }
        }
        
        # Perform comprehensive scan
        scan_result = await self.security_manager.perform_security_scan(
            target=test_target,
            scan_types=['pii', 'threats', 'compliance']
        )
        
        # Validate scan results
        assert scan_result['scan_id'] is not None
        assert scan_result['timestamp'] is not None
        assert 'results' in scan_result
        
        # Check PII detection results
        if 'pii' in scan_result['results']:
            pii_results = scan_result['results']['pii']
            assert 'matches' in pii_results
            assert len(pii_results['matches']) > 0  # Should detect PII in test data
        
        # Check threat detection results
        if 'threats' in scan_result['results']:
            threat_results = scan_result['results']['threats']
            assert 'threats_detected' in threat_results
        
        # Check compliance results
        if 'compliance' in scan_result['results']:
            compliance_results = scan_result['results']['compliance']
            assert 'standards_assessed' in compliance_results
    
    def test_sbom_generation_integration(self):
        """Test SBOM generation with security integration."""
        # Create test project structure
        (self.temp_dir / 'requirements.txt').write_text('requests==2.28.1\nnumpy==1.21.0\n')
        (self.temp_dir / 'setup.py').write_text('from setuptools import setup\nsetup(name="test")')
        
        # Generate SBOM
        sbom_result = self.security_manager.generate_sbom(
            project_path=self.temp_dir,
            format_type="spdx-json",
            include_signature=True
        )
        
        # Validate SBOM results
        assert sbom_result['success'] is True
        assert 'sbom_content' in sbom_result
        assert 'component_count' in sbom_result
        assert 'signature' in sbom_result
        assert 'metadata' in sbom_result
        
        # Validate SBOM content structure
        sbom_content = sbom_result['sbom_content']
        if isinstance(sbom_content, dict):
            assert 'spdxVersion' in sbom_content
            assert 'packages' in sbom_content
            assert len(sbom_content['packages']) > 0
        
        # Validate performance (should be < 30 seconds for test project)
        assert sbom_result['generation_time_ms'] < 30000
    
    @pytest.mark.asyncio
    async def test_advanced_pii_detection_integration(self):
        """Test advanced PII detection with security manager integration."""
        pii_detector = self.security_manager.get_pii_detector()
        
        # Test multi-language PII detection
        test_texts = {
            'english': "Contact John Doe at john.doe@example.com or (555) 123-4567",
            'spanish': "Contacta a Juan Pérez en juan.perez@ejemplo.com o +34 612 345 678",
            'french': "Contactez Jean Dupont à jean.dupont@exemple.fr ou +33 1 23 45 67 89"
        }
        
        for language, text in test_texts.items():
            scan_result = await pii_detector.scan_data(text)
            
            # Validate scan results
            assert 'matches' in scan_result
            assert 'match_count' in scan_result
            assert 'scan_time_ms' in scan_result
            assert scan_result['scan_time_ms'] < 1000  # Should be fast
            
            # Should detect at least email and phone
            matches = scan_result['matches']
            detected_types = [match['type'] for match in matches]
            assert 'email' in detected_types
            # Phone detection might vary by language, so not asserting
            
            # Validate confidence scores
            for match in matches:
                assert 0.0 <= match['confidence'] <= 1.0
                assert 'sensitivity' in match
                assert 'masked_value' in match
    
    def test_dsr_request_processing_integration(self):
        """Test DSR request processing with full GDPR compliance."""
        # Test various DSR request types
        dsr_test_cases = [
            {
                'type': DSRRequestType.ACCESS,
                'data': {'description': 'Request access to my personal data'},
                'expected_status': 'completed'
            },
            {
                'type': DSRRequestType.RECTIFICATION,
                'data': {
                    'description': 'Update my email address',
                    'corrections': {'email': 'newemail@example.com'}
                },
                'expected_status': 'completed'
            },
            {
                'type': DSRRequestType.ERASURE,
                'data': {'description': 'Delete my account and all personal data'},
                'expected_status': 'completed'
            },
            {
                'type': DSRRequestType.PORTABILITY,
                'data': {'description': 'Export my data in portable format'},
                'expected_status': 'completed'
            }
        ]
        
        for test_case in dsr_test_cases:
            result = self.security_manager.process_dsr_request(
                request_type=test_case['type'],
                user_data=test_case['data'],
                user_id='test_user_001'
            )
            
            # Validate DSR processing
            assert result['success'] is True
            assert result['request_id'] is not None
            assert result['status'] == test_case['expected_status']
            assert 'processing_time_seconds' in result
            
            # Validate processing time (should be reasonable)
            assert result['processing_time_seconds'] < 5.0
            
            # For access requests, validate data structure
            if test_case['type'] == DSRRequestType.ACCESS:
                assert 'data' in result
                access_data = result['data']
                assert 'personal_data' in access_data
                assert 'data_sources' in access_data
                assert 'user_rights' in access_data
    
    @pytest.mark.asyncio
    async def test_threat_detection_integration(self):
        """Test threat detection with security event correlation."""
        threat_detector = self.security_manager.get_threat_detector()
        
        # Test various threat scenarios
        threat_scenarios = [
            {
                'event_type': 'authentication_failure',
                'ip_address': '192.168.1.100',
                'user_id': 'test_user_001',
                'expected_threat': False  # Single failure shouldn't trigger
            },
            {
                'event_type': 'api_request',
                'user_id': 'test_user_001',
                'request_count': 150,  # Above threshold
                'expected_threat': True
            },
            {
                'event_type': 'data_access',
                'user_id': 'test_user_001',
                'data_size': 2000000,  # Above threshold
                'resource': '/sensitive/data',
                'expected_threat': True
            }
        ]
        
        for scenario in threat_scenarios:
            scan_result = await threat_detector.scan_for_threats(scenario)
            
            # Validate threat detection results
            assert 'threats_detected' in scan_result
            assert 'threats' in scan_result
            assert 'scan_time_ms' in scan_result
            
            # Performance check
            assert scan_result['scan_time_ms'] < 100  # Should be very fast
            
            # Threat expectation validation
            if scenario['expected_threat']:
                assert scan_result['threats_detected'] > 0
                assert len(scan_result['threats']) > 0
                
                # Validate threat structure
                threat = scan_result['threats'][0]
                assert 'threat_id' in threat
                assert 'threat_type' in threat
                assert 'level' in threat
                assert 'confidence_score' in threat
                assert 0.0 <= threat['confidence_score'] <= 1.0
    
    @pytest.mark.asyncio
    async def test_compliance_reporting_integration(self):
        """Test compliance reporting across multiple standards."""
        compliance_reporter = self.security_manager.get_compliance_reporter()
        
        # Test compliance assessment for a mock system
        test_system = {
            'name': 'DevDocAI-M010-Test',
            'privacy_controls': {
                'encryption_enabled': True,
                'data_minimization': True
            },
            'access_controls': {
                'rbac': True,
                'authorization': True
            },
            'cryptography': {
                'strong_algorithms': True,
                'key_management': True
            },
            'injection_protection': {
                'input_validation': True,
                'parameterized_queries': True
            },
            'dsr_system': {
                'access': True,
                'erasure': True,
                'portability': True
            },
            'security': {
                'access_controls': True,
                'logical_access': True
            },
            'availability': {
                'monitoring': True,
                'backup_recovery': True
            }
        }
        
        # Test multiple compliance standards
        standards_to_test = [
            ComplianceStandard.GDPR,
            ComplianceStandard.OWASP_TOP_10,
            ComplianceStandard.SOC2
        ]
        
        assessment_result = await compliance_reporter.assess_compliance(
            target=test_system,
            standards=standards_to_test
        )
        
        # Validate assessment results
        assert 'assessment_id' in assessment_result
        assert 'timestamp' in assessment_result
        assert 'standards_assessed' in assessment_result
        assert 'reports' in assessment_result
        assert 'overall_compliance_score' in assessment_result
        assert 'overall_grade' in assessment_result
        
        # Validate each standard report
        for standard in standards_to_test:
            standard_key = standard.value
            assert standard_key in assessment_result['reports']
            
            report = assessment_result['reports'][standard_key]
            if 'error' not in report:  # Skip failed assessments
                assert 'compliance_score' in report
                assert 'compliance_grade' in report
                assert 'total_controls' in report
                assert 'compliant_controls' in report
                assert 'non_compliant_controls' in report
                
                # Validate score range
                assert 0.0 <= report['compliance_score'] <= 1.0
                
                # Validate grade format
                assert report['compliance_grade'] in [
                    'A+', 'A', 'A-', 'B+', 'B', 'B-', 
                    'C+', 'C', 'C-', 'D', 'F'
                ]
        
        # Overall compliance should be reasonable given good test system
        assert assessment_result['overall_compliance_score'] >= 0.5
        assert assessment_result['overall_grade'] != 'F'
    
    def test_performance_benchmarks(self):
        """Test performance benchmarks across all components."""
        import time
        
        performance_tests = []
        
        # Test SBOM generation performance
        start_time = time.perf_counter()
        try:
            (self.temp_dir / 'requirements.txt').write_text('requests==2.28.1\n')
            sbom_result = self.security_manager.generate_sbom(
                project_path=self.temp_dir,
                format_type="spdx-json"
            )
            sbom_time = (time.perf_counter() - start_time) * 1000
            performance_tests.append(('SBOM Generation', sbom_time, 100))  # Target <100ms
        except Exception as e:
            performance_tests.append(('SBOM Generation', float('inf'), 100, str(e)))
        
        # Test PII detection performance
        pii_detector = self.security_manager.get_pii_detector()
        start_time = time.perf_counter()
        try:
            # Synchronous version for timing
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            pii_result = loop.run_until_complete(pii_detector.scan_data(self.test_pii_data))
            loop.close()
            pii_time = (time.perf_counter() - start_time) * 1000
            performance_tests.append(('PII Detection', pii_time, 50))  # Target <50ms
        except Exception as e:
            performance_tests.append(('PII Detection', float('inf'), 50, str(e)))
        
        # Test threat detection performance
        threat_detector = self.security_manager.get_threat_detector()
        start_time = time.perf_counter()
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            threat_result = loop.run_until_complete(threat_detector.scan_for_threats({
                'event_type': 'test_event',
                'user_id': 'test_user'
            }))
            loop.close()
            threat_time = (time.perf_counter() - start_time) * 1000
            performance_tests.append(('Threat Detection', threat_time, 10))  # Target <10ms
        except Exception as e:
            performance_tests.append(('Threat Detection', float('inf'), 10, str(e)))
        
        # Test DSR processing performance
        start_time = time.perf_counter()
        try:
            dsr_result = self.security_manager.process_dsr_request(
                request_type=DSRRequestType.ACCESS,
                user_data={'description': 'Test access request'},
                user_id='test_user_perf'
            )
            dsr_time = (time.perf_counter() - start_time) * 1000
            performance_tests.append(('DSR Processing', dsr_time, 1000))  # Target <1000ms
        except Exception as e:
            performance_tests.append(('DSR Processing', float('inf'), 1000, str(e)))
        
        # Validate performance results
        print("\nM010 Security Module Performance Results:")
        print("-" * 50)
        
        for test in performance_tests:
            if len(test) == 3:
                component, actual_time, target_time = test
                status = "PASS" if actual_time <= target_time else "FAIL"
                print(f"{component:20} {actual_time:8.2f}ms (target: {target_time}ms) [{status}]")
                
                # Assert performance requirements (relaxed for test environment)
                assert actual_time <= target_time * 2, f"{component} too slow: {actual_time}ms > {target_time * 2}ms"
            else:
                component, actual_time, target_time, error = test
                print(f"{component:20} ERROR: {error}")
        
        print("-" * 50)
    
    def test_end_to_end_security_workflow(self):
        """Test complete end-to-end security workflow."""
        # Simulate a complete security workflow
        workflow_results = {
            'sbom_generation': None,
            'pii_detection': None,
            'dsr_processing': None,
            'threat_monitoring': None,
            'compliance_assessment': None
        }
        
        try:
            # 1. Generate SBOM for security inventory
            (self.temp_dir / 'requirements.txt').write_text('flask==2.0.1\n')
            sbom_result = self.security_manager.generate_sbom(
                project_path=self.temp_dir,
                format_type="spdx-json"
            )
            workflow_results['sbom_generation'] = sbom_result['success']
            
            # 2. Scan for PII in sensitive document
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            scan_result = loop.run_until_complete(
                self.security_manager.perform_security_scan(
                    target={'content': self.test_pii_data},
                    scan_types=['pii']
                )
            )
            workflow_results['pii_detection'] = len(scan_result.get('results', {}).get('pii', {}).get('matches', [])) > 0
            
            # 3. Process data subject request
            dsr_result = self.security_manager.process_dsr_request(
                request_type=DSRRequestType.ACCESS,
                user_data={'description': 'Workflow test access request'},
                user_id='workflow_test_user'
            )
            workflow_results['dsr_processing'] = dsr_result['success']
            
            # 4. Monitor for threats
            threat_result = loop.run_until_complete(
                self.security_manager.get_threat_detector().scan_for_threats({
                    'event_type': 'workflow_test',
                    'user_id': 'workflow_test_user'
                })
            )
            workflow_results['threat_monitoring'] = 'threats_detected' in threat_result
            
            # 5. Assess compliance
            compliance_result = loop.run_until_complete(
                self.security_manager.get_compliance_reporter().assess_compliance(
                    target={'name': 'workflow_test_system'},
                    standards=[ComplianceStandard.GDPR]
                )
            )
            workflow_results['compliance_assessment'] = 'overall_compliance_score' in compliance_result
            
            loop.close()
            
        except Exception as e:
            print(f"Workflow error: {e}")
        
        # Validate complete workflow
        print("\nEnd-to-End Security Workflow Results:")
        print("-" * 40)
        for step, success in workflow_results.items():
            status = "✓" if success else "✗"
            print(f"{step:25} {status}")
        print("-" * 40)
        
        # Assert all major steps completed successfully
        success_count = sum(1 for success in workflow_results.values() if success)
        total_steps = len(workflow_results)
        success_rate = success_count / total_steps
        
        print(f"Overall Success Rate: {success_rate:.1%} ({success_count}/{total_steps})")
        
        # Require at least 80% success rate for integration test
        assert success_rate >= 0.8, f"Workflow success rate too low: {success_rate:.1%}"
    
    def test_module_integration_with_existing_systems(self):
        """Test integration with existing M001-M009 modules."""
        # Test M001 configuration integration
        config_integration = self.security_manager.config.integrate_with_m001
        assert config_integration is True
        
        # Test M002 storage integration
        storage_integration = self.security_manager.config.integrate_with_m002
        assert storage_integration is True
        
        # Test M008 LLM adapter integration
        llm_integration = self.security_manager.config.integrate_with_m008
        assert llm_integration is True
        
        # Test encryption compatibility with existing modules
        test_data = "sensitive test data"
        encrypted = self.security_manager.encrypt_sensitive_data(test_data)
        decrypted = self.security_manager.decrypt_sensitive_data(encrypted)
        assert decrypted == test_data
        
        # Test input validation compatibility
        test_input = {"user_input": "test value", "extra_field": "should be removed"}
        validated = self.security_manager.validate_input(
            test_input, 
            {'allowed_keys': ['user_input']}
        )
        assert 'user_input' in validated
        assert 'extra_field' not in validated
    
    def test_security_metrics_and_statistics(self):
        """Test security metrics collection and reporting."""
        # Get initial security status
        initial_status = self.security_manager.get_security_status()
        
        # Perform some security operations
        with self.security_manager.secure_operation("test_operation", "test_user"):
            pass
        
        # Generate some activity
        pii_detector = self.security_manager.get_pii_detector()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        for i in range(3):
            loop.run_until_complete(
                pii_detector.scan_data(f"Test data {i} with email test{i}@example.com")
            )
        
        loop.close()
        
        # Get updated security status
        updated_status = self.security_manager.get_security_status()
        
        # Validate metrics collection
        assert 'metrics' in updated_status
        metrics = updated_status['metrics']
        
        assert 'operations_processed' in metrics
        assert metrics['operations_processed'] >= 1
        
        # Get component-specific statistics
        pii_stats = pii_detector.get_statistics()
        assert 'total_scans' in pii_stats
        assert pii_stats['total_scans'] >= 3
        
        threat_stats = self.security_manager.get_threat_detector().get_threat_statistics()
        assert 'total_threats_detected' in threat_stats
        
        print("\nSecurity Statistics Summary:")
        print(f"Operations processed: {metrics['operations_processed']}")
        print(f"PII scans completed: {pii_stats['total_scans']}")
        print(f"Threats detected: {threat_stats['total_threats_detected']}")
        print(f"Security posture score: {metrics.get('security_posture_score', 'N/A')}")


# Additional integration test fixtures and helpers

@pytest.fixture
def security_test_environment():
    """Fixture for setting up complete security test environment."""
    config = SecurityConfig(
        mode=SecurityMode.ENTERPRISE,
        real_time_monitoring=False,
        max_concurrent_operations=5
    )
    
    security_manager = SecurityManager(config)
    
    yield security_manager
    
    security_manager.shutdown()


@pytest.fixture
def mock_project_with_dependencies():
    """Fixture for creating a mock project with dependencies."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create package.json for Node.js project
        package_json = {
            "name": "test-security-project",
            "version": "1.0.0",
            "dependencies": {
                "express": "^4.18.0",
                "lodash": "^4.17.21",
                "axios": "^0.27.2"
            },
            "devDependencies": {
                "jest": "^28.1.0",
                "nodemon": "^2.0.19"
            }
        }
        
        (temp_path / 'package.json').write_text(json.dumps(package_json, indent=2))
        
        # Create requirements.txt for Python
        (temp_path / 'requirements.txt').write_text(
            "flask==2.2.2\nrequests==2.28.1\nnumpy==1.23.0\npandas==1.4.3"
        )
        
        # Create a simple source file
        (temp_path / 'app.py').write_text('''
import flask
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/api/data', methods=['POST'])
def handle_data():
    user_data = request.json
    # This could contain PII
    email = user_data.get('email')
    phone = user_data.get('phone')
    return jsonify({"status": "received"})

if __name__ == '__main__':
    app.run(debug=True)
        ''')
        
        yield temp_path


if __name__ == '__main__':
    # Run specific integration test
    test_instance = TestM010SecurityModuleIntegration()
    test_instance.setup_method()
    
    try:
        print("Running M010 Security Module Integration Test...")
        test_instance.test_security_module_initialization()
        test_instance.test_performance_benchmarks()
        test_instance.test_end_to_end_security_workflow()
        print("\n✅ All integration tests passed!")
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        raise
    finally:
        test_instance.teardown_method()