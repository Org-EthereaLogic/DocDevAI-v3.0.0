"""
Comprehensive security test suite for M004 Document Generator Pass 3.

Tests all security components including validation, sanitization, 
template sandboxing, access controls, and threat detection.
"""

import pytest
import tempfile
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import security components
from devdocai.generator.utils.security_validator import EnhancedSecurityValidator, SecurityValidationError
from devdocai.generator.core.secure_template_loader import SecureTemplateLoader, TemplateSecurityError
from devdocai.generator.outputs.secure_html_output import SecureHtmlOutput, SecurityError
from devdocai.generator.security.security_monitor import SecurityMonitor, SecurityIncident
from devdocai.generator.security.pii_protection import PIIProtectionEngine, PIISensitivity, PIIAction
from devdocai.generator.security.access_control import AccessController, AccessLevel, ResourceType
from devdocai.generator.core.engine import DocumentGenerator


class TestSecurityValidator:
    """Test comprehensive input validation and threat detection."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.validator = EnhancedSecurityValidator()
    
    def test_xss_pattern_detection(self):
        """Test XSS pattern detection in inputs."""
        malicious_inputs = {
            'script_tag': '<script>alert("xss")</script>',
            'javascript_url': 'javascript:alert("xss")',
            'event_handler': '<img src="x" onerror="alert(1)">',
            'iframe_tag': '<iframe src="javascript:alert(1)"></iframe>'
        }
        
        result = self.validator.validate_template_inputs_secure(
            malicious_inputs, [], 'test_client'
        )
        
        assert not result['valid']
        assert len(result['errors']) > 0
        assert any('XSS' in error for error in result['errors'])
        assert result['security_score'] < 50
    
    def test_template_injection_detection(self):
        """Test template injection pattern detection."""
        injection_inputs = {
            'jinja2_injection': '{{ config.__class__.__init__.__globals__["os"].system("ls") }}',
            'django_injection': '{% load os %}{% system "rm -rf /" %}',
            'expression_injection': '${java.lang.Runtime.getRuntime().exec("cmd")}'
        }
        
        result = self.validator.validate_template_inputs_secure(
            injection_inputs, [], 'test_client'
        )
        
        assert not result['valid']
        assert any('Template injection' in error for error in result['errors'])
    
    def test_sql_injection_detection(self):
        """Test SQL injection pattern detection."""
        sql_inputs = {
            'union_attack': "'; DROP TABLE users; --",
            'boolean_attack': "' OR 1=1 --",
            'comment_attack': "admin'/**/OR/**/1=1#"
        }
        
        result = self.validator.validate_template_inputs_secure(
            sql_inputs, [], 'test_client'
        )
        
        assert not result['valid']
        assert any('SQL injection' in error for error in result['errors'])
    
    def test_path_traversal_detection(self):
        """Test path traversal attack detection."""
        traversal_inputs = {
            'basic_traversal': '../../../etc/passwd',
            'encoded_traversal': '%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd',
            'unicode_traversal': '..\\..\\..\\windows\\system32\\config\\sam'
        }
        
        result = self.validator.validate_template_inputs_secure(
            traversal_inputs, [], 'test_client'
        )
        
        assert not result['valid']
        assert any('Path traversal' in error for error in result['errors'])
    
    def test_command_injection_detection(self):
        """Test command injection detection."""
        command_inputs = {
            'pipe_command': 'test.txt | rm -rf /',
            'semicolon_command': 'test.txt; cat /etc/passwd',
            'backtick_command': 'test`whoami`.txt'
        }
        
        result = self.validator.validate_template_inputs_secure(
            command_inputs, [], 'test_client'
        )
        
        assert not result['valid']
        assert any('Command injection' in error for error in result['errors'])
    
    def test_unicode_normalization_attack(self):
        """Test unicode normalization attack detection."""
        # Unicode characters that normalize to dangerous sequences
        unicode_attack = "℠cript"  # Normalizes to "script"
        
        result = self.validator.validate_field_secure('test', unicode_attack, 'test_client')
        
        assert len(result['errors']) > 0
    
    def test_rate_limiting(self):
        """Test validation rate limiting."""
        # Exceed rate limit
        for _ in range(105):  # Above default limit of 100
            result = self.validator.validate_template_inputs_secure(
                {'test': 'value'}, [], 'test_client'
            )
        
        # Should be rate limited
        assert not result['valid']
        assert 'rate limit' in result['errors'][0].lower()
    
    def test_input_size_limits(self):
        """Test input size validation."""
        large_input = {'huge_field': 'x' * (2 * 1024 * 1024)}  # 2MB
        
        result = self.validator.validate_template_inputs_secure(
            large_input, [], 'test_client'
        )
        
        assert not result['valid']
        assert any('too large' in error.lower() for error in result['errors'])
    
    def test_safe_inputs_validation(self):
        """Test that safe inputs pass validation."""
        safe_inputs = {
            'name': 'John Doe',
            'email': 'john.doe@example.com',
            'description': 'This is a safe description.',
            'version': '1.2.3'
        }
        
        result = self.validator.validate_template_inputs_secure(
            safe_inputs, ['name'], 'test_client'
        )
        
        assert result['valid']
        assert result['security_score'] == 100
        assert len(result['errors']) == 0


class TestTemplateSecurityLoader:
    """Test secure template loading and sandboxing."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.loader = SecureTemplateLoader(self.temp_dir, strict_mode=True)
    
    def teardown_method(self):
        """Cleanup test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_template_sandboxing(self):
        """Test that templates are executed in a sandboxed environment."""
        # Create malicious template
        malicious_template = self.temp_dir / "malicious.j2"
        malicious_template.write_text("""
        {{ config.__class__.__init__.__globals__['os'].system('echo pwned') }}
        """)
        
        with pytest.raises(TemplateSecurityError):
            self.loader.render_template_secure("malicious.j2", {}, "test_client")
    
    def test_template_path_traversal_prevention(self):
        """Test prevention of path traversal in template names."""
        with pytest.raises(TemplateSecurityError):
            self.loader.render_template_secure("../../../etc/passwd", {}, "test_client")
    
    def test_template_size_limits(self):
        """Test template size limits."""
        # Create oversized template
        large_template = self.temp_dir / "large.j2"
        large_template.write_text("x" * (200 * 1024))  # 200KB > 100KB limit
        
        with pytest.raises(TemplateSecurityError):
            self.loader.render_template_secure("large.j2", {}, "test_client")
    
    def test_template_integrity_checking(self):
        """Test template integrity verification."""
        # Create template
        template = self.temp_dir / "test.j2"
        template.write_text("Hello {{ name }}!")
        
        # Load and get initial render
        content, metadata = self.loader.render_template_secure("test.j2", {"name": "World"}, "test_client")
        assert "Hello World!" in content
        
        # Modify template (simulating tampering)
        template.write_text("Hello {{ name }}! TAMPERED")
        
        # Should detect integrity failure
        with pytest.raises(TemplateSecurityError):
            self.loader.render_template_secure("test.j2", {"name": "World"}, "test_client")
    
    def test_template_rate_limiting(self):
        """Test template access rate limiting."""
        template = self.temp_dir / "test.j2"
        template.write_text("Hello {{ name }}!")
        
        # Exceed rate limit
        for i in range(52):  # Above limit of 50 per hour
            try:
                self.loader.render_template_secure("test.j2", {"name": f"User{i}"}, "test_client")
            except TemplateSecurityError as e:
                if "Access denied" in str(e):
                    break
        else:
            pytest.fail("Rate limiting not enforced")
    
    def test_safe_template_rendering(self):
        """Test that safe templates render correctly."""
        template = self.temp_dir / "safe.j2"
        template.write_text("""
        # {{ title }}
        
        Welcome {{ user_name }}!
        
        ## Features
        {% for feature in features %}
        - {{ feature }}
        {% endfor %}
        """)
        
        variables = {
            "title": "Test Document",
            "user_name": "John Doe", 
            "features": ["Security", "Performance", "Reliability"]
        }
        
        content, metadata = self.loader.render_template_secure("safe.j2", variables, "test_client")
        
        assert "Test Document" in content
        assert "John Doe" in content
        assert "Security" in content
        assert len(metadata['security_checks']) > 0


class TestSecureHtmlOutput:
    """Test secure HTML output with XSS prevention."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.html_output = SecureHtmlOutput(strict_mode=True)
    
    def test_xss_prevention_in_html_output(self):
        """Test XSS prevention in HTML output."""
        malicious_content = """
        # Test Document
        
        <script>alert('xss')</script>
        
        [Click here](javascript:alert('xss'))
        
        <img src="x" onerror="alert('xss')">
        """
        
        mock_metadata = Mock()
        mock_metadata.name = "test"
        mock_metadata.title = "Test"
        mock_metadata.author = "Test"
        mock_metadata.type = "test"
        mock_metadata.version = "1.0"
        
        result = self.html_output.format_content_secure(
            malicious_content, mock_metadata, "test_client"
        )
        
        html_content = result['html_content']
        
        # Should not contain dangerous patterns
        assert '<script>' not in html_content
        assert 'javascript:' not in html_content
        assert 'onerror=' not in html_content
        
        # Should contain CSP header
        assert 'csp_header' in result['security_metadata']
        assert 'script-src \'none\'' in result['security_metadata']['csp_header']
    
    def test_html_sanitization(self):
        """Test HTML tag sanitization."""
        dangerous_html = """
        <iframe src="malicious.html"></iframe>
        <object data="malicious.swf"></object>
        <embed src="malicious.swf">
        <link rel="stylesheet" href="malicious.css">
        <meta http-equiv="refresh" content="0;url=malicious.html">
        """
        
        mock_metadata = Mock()
        mock_metadata.name = "test"
        mock_metadata.title = "Test"
        mock_metadata.author = "Test"
        mock_metadata.type = "test"
        mock_metadata.version = "1.0"
        
        result = self.html_output.format_content_secure(
            dangerous_html, mock_metadata, "test_client"
        )
        
        html_content = result['html_content']
        
        # Dangerous tags should be removed
        assert '<iframe' not in html_content
        assert '<object' not in html_content
        assert '<embed' not in html_content
        assert '<link' not in html_content
        assert '<meta http-equiv' not in html_content
    
    def test_css_security(self):
        """Test CSS security in generated HTML."""
        result = self.html_output._get_secure_css()
        
        # Should not contain dangerous CSS patterns
        assert 'expression(' not in result
        assert '@import' not in result
        assert 'javascript:' not in result
    
    def test_content_size_limits(self):
        """Test content size limits."""
        huge_content = "x" * (60 * 1024 * 1024)  # 60MB > 50MB limit
        
        mock_metadata = Mock()
        mock_metadata.name = "test"
        mock_metadata.title = "Test"
        mock_metadata.author = "Test"
        mock_metadata.type = "test"
        mock_metadata.version = "1.0"
        
        with pytest.raises(SecurityError):
            self.html_output.format_content_secure(
                huge_content, mock_metadata, "test_client"
            )


class TestPIIProtection:
    """Test PII detection and protection."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.pii_protection = PIIProtectionEngine()
    
    def test_ssn_detection(self):
        """Test SSN detection and masking."""
        content_with_ssn = "My SSN is 123-45-6789 and should be protected."
        
        result = self.pii_protection.scan_and_protect(
            content_with_ssn, 'input', 'test_client'
        )
        
        assert result['pii_detected']
        assert 'ssn' in result['pii_types_found']
        assert '123-45-6789' not in result['protected_content']
    
    def test_credit_card_detection(self):
        """Test credit card detection with Luhn validation."""
        # Valid credit card number (passes Luhn algorithm)
        content_with_cc = "My credit card is 4111 1111 1111 1111."
        
        result = self.pii_protection.scan_and_protect(
            content_with_cc, 'input', 'test_client', require_explicit_consent=True
        )
        
        assert result['pii_detected']
        assert 'credit_card' in result['pii_types_found']
        # Should be blocked due to critical sensitivity
        assert result['processing_blocked']
    
    def test_email_masking(self):
        """Test email detection and masking."""
        content_with_email = "Contact me at john.doe@example.com for more info."
        
        result = self.pii_protection.scan_and_protect(
            content_with_email, 'input', 'test_client'
        )
        
        assert result['pii_detected']
        assert 'email' in result['pii_types_found']
        # Email should be masked but domain preserved
        assert 'j***e@example.com' in result['protected_content'] or '@example.com' in result['protected_content']
    
    def test_multiple_pii_types(self):
        """Test detection of multiple PII types."""
        content_with_multiple_pii = """
        Name: John Doe
        SSN: 123-45-6789
        Email: john.doe@example.com
        Phone: (555) 123-4567
        Credit Card: 4111-1111-1111-1111
        """
        
        result = self.pii_protection.scan_and_protect(
            content_with_multiple_pii, 'input', 'test_client'
        )
        
        assert result['pii_detected']
        assert len(result['pii_types_found']) >= 3  # SSN, email, phone minimum
        assert len(result['actions_taken']) > 0
    
    def test_pii_policy_enforcement(self):
        """Test PII policy enforcement."""
        # Content with medical record number (should be blocked)
        content_with_medical = "Patient MRN123456789 requires immediate attention."
        
        result = self.pii_protection.scan_and_protect(
            content_with_medical, 'input', 'test_client'
        )
        
        if result['pii_detected'] and 'medical_record' in result['pii_types_found']:
            # Medical records have BLOCK policy by default
            assert result['processing_blocked']
    
    def test_false_positive_handling(self):
        """Test handling of potential false positives."""
        content_no_pii = """
        This is a safe document about:
        - Software development
        - API design
        - Testing strategies
        Version: 1.2.3
        """
        
        result = self.pii_protection.scan_and_protect(
            content_no_pii, 'input', 'test_client'
        )
        
        assert not result['processing_blocked']
        # Some low-confidence matches might be detected but shouldn't block


class TestAccessControl:
    """Test access control and rate limiting."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.access_controller = AccessController()
    
    def test_client_registration(self):
        """Test client registration and profiling."""
        profile = self.access_controller.register_client(
            'test_client', AccessLevel.AUTHENTICATED
        )
        
        assert profile.client_id == 'test_client'
        assert profile.access_level == AccessLevel.AUTHENTICATED
        assert len(profile.granted_permissions) > 0
        assert profile.security_score == 100
    
    def test_permission_checking(self):
        """Test permission-based access control."""
        # Register public client
        self.access_controller.register_client('public_client', AccessLevel.PUBLIC)
        
        # Should have limited permissions
        allowed, reason, metadata = self.access_controller.check_access(
            'public_client', ResourceType.TEMPLATE, 'read'
        )
        assert allowed
        
        # Should not have admin permissions
        allowed, reason, metadata = self.access_controller.check_access(
            'public_client', ResourceType.ADMIN_FUNCTION, 'execute'
        )
        assert not allowed
        assert 'Permission denied' in reason
    
    def test_rate_limiting(self):
        """Test rate limiting functionality."""
        client_id = 'rate_test_client'
        
        # Register client with low limits
        profile = self.access_controller.register_client(client_id, AccessLevel.PUBLIC)
        
        # Exceed rate limit
        success_count = 0
        for i in range(25):  # Above public limit of 20
            allowed, reason, stats = self.access_controller.check_rate_limit(
                client_id, 'template_render'
            )
            if allowed:
                success_count += 1
        
        # Should hit rate limit
        assert success_count <= 20
    
    def test_client_blocking(self):
        """Test client blocking functionality."""
        client_id = 'block_test_client'
        self.access_controller.register_client(client_id, AccessLevel.AUTHENTICATED)
        
        # Block client
        self.access_controller.block_client(client_id, 60, "Security violation")
        
        # Should be blocked
        allowed, reason, metadata = self.access_controller.check_access(
            client_id, ResourceType.TEMPLATE, 'read'
        )
        assert not allowed
        assert 'blocked' in reason.lower()
    
    def test_risk_score_calculation(self):
        """Test client risk score calculation."""
        client_id = 'risk_test_client'
        self.access_controller.register_client(client_id, AccessLevel.AUTHENTICATED)
        
        # Simulate suspicious activity
        for _ in range(5):
            self.access_controller._record_failed_attempt(
                client_id, 'permission_denied', 'test'
            )
        
        risk_assessment = self.access_controller.calculate_client_risk_score(client_id)
        
        assert risk_assessment['risk_score'] > 0
        assert len(risk_assessment['factors']) > 0
        assert risk_assessment['recommendation'] in ['allow', 'monitor', 'monitor_closely', 'block']
    
    def test_quota_enforcement(self):
        """Test resource quota enforcement."""
        client_id = 'quota_test_client'
        profile = self.access_controller.register_client(client_id, AccessLevel.PUBLIC)
        
        # Simulate quota usage
        profile.quotas_used['documents_per_day'] = 10  # At public limit
        
        # Should fail quota check
        quota_check = self.access_controller._check_quotas(
            profile, ResourceType.DOCUMENT, 'write'
        )
        
        assert not quota_check['allowed']
        assert 'quota exceeded' in quota_check['reason'].lower()


class TestSecurityMonitor:
    """Test security monitoring and incident management."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.monitor = SecurityMonitor()
    
    def test_security_event_reporting(self):
        """Test security event reporting."""
        incident_id = self.monitor.report_security_event(
            'xss', 'high', 'test_client', 'test_template',
            'XSS attempt detected', {'pattern': '<script>'}
        )
        
        # Should create incident for high severity
        assert incident_id != ""
        assert incident_id in self.monitor.active_incidents
    
    def test_incident_management(self):
        """Test incident creation and management."""
        self.monitor.report_xss_attempt(
            'test_client', 'test_template', '<script>alert(1)</script>', 'input_field'
        )
        
        assert len(self.monitor.active_incidents) > 0
        
        # Check incident details
        incident = list(self.monitor.active_incidents.values())[0]
        assert incident.category == self.monitor.CATEGORY_XSS
        assert incident.severity == self.monitor.SEVERITY_HIGH
        assert incident.client_id == 'test_client'
    
    def test_anomaly_detection(self):
        """Test anomaly detection."""
        # Simulate burst of violations
        for _ in range(6):  # Above threshold of 5 in 5 minutes
            self.monitor.report_security_event(
                'validation', 'medium', 'test_client', 'test_template',
                'Validation failure', {}
            )
        
        # Should detect anomaly and create DoS incident
        dos_incidents = [
            incident for incident in self.monitor.active_incidents.values()
            if incident.category == self.monitor.CATEGORY_DOS
        ]
        assert len(dos_incidents) > 0
    
    def test_client_risk_scoring(self):
        """Test client risk scoring."""
        client_id = 'risk_client'
        
        # Simulate security violations
        self.monitor.report_xss_attempt(client_id, 'template1', '<script>', 'field1')
        self.monitor.report_injection_attempt(client_id, 'template2', 'sql', 'DROP TABLE')
        
        risk_score = self.monitor.get_client_risk_score(client_id)
        
        assert risk_score['risk_score'] > 0
        assert len(risk_score['factors']) > 0
    
    def test_security_dashboard(self):
        """Test security dashboard generation."""
        # Generate some incidents
        self.monitor.report_security_event(
            'xss', 'high', 'client1', 'template1', 'XSS attempt', {}
        )
        self.monitor.report_security_event(
            'injection', 'critical', 'client2', 'template2', 'SQL injection', {}
        )
        
        dashboard = self.monitor.get_security_dashboard()
        
        assert 'incidents' in dashboard
        assert dashboard['incidents']['active'] >= 2
        assert 'clients' in dashboard
        assert 'templates' in dashboard


class TestIntegratedSecurity:
    """Test integrated security across all components."""
    
    def setup_method(self):
        """Setup integrated test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Create a simple template
        template = self.temp_dir / "test.j2"
        template.write_text("Hello {{ name }}! Your email is {{ email }}.")
        
        self.generator = DocumentGenerator(
            template_dir=self.temp_dir,
            security_enabled=True,
            strict_mode=True
        )
    
    def teardown_method(self):
        """Cleanup test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_end_to_end_security_flow(self):
        """Test complete secure document generation flow."""
        # Register client
        self.generator.access_controller.register_client(
            'integration_client', AccessLevel.AUTHENTICATED
        )
        
        # Generate document with safe inputs
        safe_inputs = {
            'name': 'John Doe',
            'email': 'john.doe@example.com'
        }
        
        result = self.generator.generate_document_secure(
            'test.j2', safe_inputs, 'integration_client'
        )
        
        assert result.success
        assert 'Hello John Doe!' in result.content
        assert len(result.metadata['security_checks']) > 5  # Multiple security checks
    
    def test_malicious_input_blocking(self):
        """Test that malicious inputs are blocked."""
        # Register client
        self.generator.access_controller.register_client(
            'malicious_client', AccessLevel.AUTHENTICATED
        )
        
        # Attempt generation with malicious inputs
        malicious_inputs = {
            'name': '<script>alert("xss")</script>',
            'email': 'admin\' OR 1=1 --'
        }
        
        result = self.generator.generate_document_secure(
            'test.j2', malicious_inputs, 'malicious_client'
        )
        
        # Should be blocked due to security violations
        assert not result.success
        assert 'validation failed' in result.error_message.lower() or 'blocked' in result.error_message.lower()
    
    def test_pii_protection_integration(self):
        """Test PII protection in document generation."""
        # Register client
        self.generator.access_controller.register_client(
            'pii_client', AccessLevel.AUTHENTICATED
        )
        
        # Generate document with PII
        pii_inputs = {
            'name': 'John Doe',
            'email': 'john.doe@example.com',
            'ssn': '123-45-6789'  # This should trigger PII protection
        }
        
        # Add SSN field to template
        pii_template = self.temp_dir / "pii_test.j2"
        pii_template.write_text("Name: {{ name }}, Email: {{ email }}, SSN: {{ ssn }}")
        
        result = self.generator.generate_document_secure(
            'pii_test.j2', pii_inputs, 'pii_client'
        )
        
        if result.success:
            # PII should be masked in output
            assert '123-45-6789' not in result.content
        # Or generation might be blocked due to PII policy
    
    def test_rate_limiting_integration(self):
        """Test rate limiting in document generation."""
        # Register client with low limits
        self.generator.access_controller.register_client(
            'rate_limited_client', AccessLevel.PUBLIC
        )
        
        # Exceed rate limit
        success_count = 0
        for i in range(25):  # Above public limit
            result = self.generator.generate_document_secure(
                'test.j2', {'name': f'User{i}', 'email': f'user{i}@example.com'}, 
                'rate_limited_client'
            )
            if result.success:
                success_count += 1
        
        # Should hit rate limit
        assert success_count <= 20
    
    def test_access_control_integration(self):
        """Test access control integration."""
        # Register public client
        self.generator.access_controller.register_client(
            'public_client', AccessLevel.PUBLIC
        )
        
        # Try to access admin functions (should fail)
        result = self.generator.generate_document_secure(
            'test.j2', {'name': 'User', 'email': 'user@example.com'}, 
            'public_client'
        )
        
        # Basic template access should work for public clients
        # but with limited functionality
        if not result.success:
            assert 'access denied' in result.error_message.lower() or 'permission' in result.error_message.lower()


class TestSecurityPerformance:
    """Test security performance impact."""
    
    def setup_method(self):
        """Setup performance test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Create test template
        template = self.temp_dir / "perf_test.j2"
        template.write_text("Hello {{ name }}! Welcome to {{ app_name }}.")
        
        self.secure_generator = DocumentGenerator(
            template_dir=self.temp_dir,
            security_enabled=True,
            strict_mode=True
        )
        
        self.insecure_generator = DocumentGenerator(
            template_dir=self.temp_dir,
            security_enabled=False,
            strict_mode=False
        )
    
    def teardown_method(self):
        """Cleanup test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_security_overhead(self):
        """Test security overhead is reasonable."""
        import time
        
        # Register client for secure generator
        self.secure_generator.access_controller.register_client(
            'perf_client', AccessLevel.AUTHENTICATED
        )
        
        test_inputs = {
            'name': 'Performance Test',
            'app_name': 'DocDevAI'
        }
        
        # Time secure generation
        start_time = time.time()
        secure_result = self.secure_generator.generate_document_secure(
            'perf_test.j2', test_inputs, 'perf_client'
        )
        secure_time = time.time() - start_time
        
        # Time insecure generation
        start_time = time.time()
        insecure_result = self.insecure_generator.generate_document(
            'perf_test.j2', test_inputs
        )
        insecure_time = time.time() - start_time
        
        # Both should succeed
        assert secure_result.success
        assert insecure_result.success
        
        # Security overhead should be reasonable (< 500% of baseline)
        overhead_ratio = secure_time / insecure_time if insecure_time > 0 else 1
        assert overhead_ratio < 5.0, f"Security overhead too high: {overhead_ratio:.2f}x"
        
        print(f"Security overhead: {overhead_ratio:.2f}x ({secure_time:.3f}s vs {insecure_time:.3f}s)")


@pytest.fixture
def security_test_environment():
    """Fixture for security testing environment."""
    temp_dir = Path(tempfile.mkdtemp())
    
    # Create test templates
    safe_template = temp_dir / "safe.j2"
    safe_template.write_text("# {{ title }}\n\nHello {{ name }}!")
    
    yield temp_dir
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)


def test_security_regression_suite(security_test_environment):
    """Comprehensive security regression test."""
    generator = DocumentGenerator(
        template_dir=security_test_environment,
        security_enabled=True,
        strict_mode=True
    )
    
    # Register test client
    generator.access_controller.register_client('regression_client', AccessLevel.AUTHENTICATED)
    
    # Test cases that should pass
    safe_test_cases = [
        {'title': 'Safe Document', 'name': 'User'},
        {'title': 'Test Report', 'name': 'John Doe'},
        {'title': 'API Documentation', 'name': 'Developer'}
    ]
    
    for test_case in safe_test_cases:
        result = generator.generate_document_secure('safe.j2', test_case, 'regression_client')
        assert result.success, f"Safe test case failed: {test_case}"
    
    # Test cases that should be blocked
    malicious_test_cases = [
        {'title': '<script>alert("xss")</script>', 'name': 'Attacker'},
        {'title': 'Normal', 'name': '{{ config.__class__ }}'},
        {'title': 'Test', 'name': 'user\' OR 1=1 --'}
    ]
    
    for test_case in malicious_test_cases:
        result = generator.generate_document_secure('safe.j2', test_case, 'regression_client')
        assert not result.success, f"Malicious test case should have been blocked: {test_case}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])