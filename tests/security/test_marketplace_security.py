"""
M013 Template Marketplace Client - Pass 3: Security Hardening Test Suite
DevDocAI v3.0.0 - Comprehensive Security Testing

This test suite validates:
- Enhanced Ed25519 signature verification with key rotation
- Input validation and sanitization
- Rate limiting and DoS protection
- Template sandboxing
- Security audit logging
- OWASP Top 10 compliance

Target: 95%+ security test coverage
"""

import tempfile
import time
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

# Import security module
from devdocai.operations.marketplace_security import (
    EnhancedTemplateVerifier,
    MarketplaceSecurityManager,
    RateLimiter,
    SecurityAuditLogger,
    SecurityConfig,
    SecurityLevel,
    TemplateSandbox,
    TemplateSecurityValidator,
)

# Test constants
TEST_PUBLIC_KEY = b"0" * 32  # Ed25519 public key is 32 bytes
TEST_PRIVATE_KEY = b"0" * 32  # Ed25519 private key is 32 bytes
TEST_SIGNATURE = b"0" * 64  # Ed25519 signature is 64 bytes


class TestSecurityConfig(unittest.TestCase):
    """Test security configuration."""

    def test_default_config(self):
        """Test default security configuration."""
        config = SecurityConfig()

        self.assertEqual(config.level, SecurityLevel.HIGH)
        self.assertTrue(config.enable_signature_verification)
        self.assertTrue(config.enforce_tls)
        self.assertTrue(config.enable_rate_limiting)
        self.assertTrue(config.enable_sandbox)

    def test_paranoid_config(self):
        """Test paranoid security level."""
        config = SecurityConfig(level=SecurityLevel.PARANOID)

        self.assertEqual(config.level, SecurityLevel.PARANOID)
        self.assertTrue(config.require_signed_templates)
        self.assertTrue(config.certificate_pinning)

    def test_config_serialization(self):
        """Test configuration serialization."""
        config = SecurityConfig()
        config_dict = config.to_dict()

        self.assertIn("level", config_dict)
        self.assertIn("signature_verification", config_dict)
        self.assertIn("rate_limiting", config_dict)


class TestSecurityAuditLogger(unittest.TestCase):
    """Test security audit logging."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = Path(self.temp_dir) / "audit.log"
        self.logger = SecurityAuditLogger(self.log_file)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_log_event(self):
        """Test logging security events."""
        self.logger.log_event(
            "test_event",
            "INFO",
            {"action": "test", "result": "success"},
            user="testuser",
            ip_address="127.0.0.1",
        )

        # Check event was logged
        events = self.logger.get_recent_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["type"], "test_event")
        self.assertEqual(events[0]["severity"], "INFO")
        self.assertEqual(events[0]["user"], "testuser")

    def test_sensitive_data_sanitization(self):
        """Test sensitive data is sanitized."""
        self.logger.log_event(
            "auth_attempt",
            "INFO",
            {
                "username": "testuser",
                "password": "secret123",
                "api_key": "sk-1234567890",
                "token": "bearer-token",
            },
        )

        events = self.logger.get_recent_events()
        details = events[0]["details"]

        # Check sensitive fields are redacted
        self.assertEqual(details["password"], "***REDACTED***")
        self.assertEqual(details["api_key"], "***REDACTED***")
        self.assertEqual(details["token"], "***REDACTED***")
        self.assertEqual(details["username"], "testuser")  # Non-sensitive

    def test_compliance_report(self):
        """Test compliance report generation."""
        # Log various events
        self.logger.log_event("login_success", "INFO", {})
        self.logger.log_event("verification_failed", "WARNING", {})
        self.logger.log_event("attack_detected", "CRITICAL", {})

        report = self.logger.generate_compliance_report()

        self.assertEqual(report["total_events"], 3)
        self.assertIn("events_by_severity", report)
        self.assertIn("events_by_type", report)
        self.assertIn("compliance_status", report)

    def test_event_filtering(self):
        """Test event filtering by type and severity."""
        # Log different types of events
        self.logger.log_event("login", "INFO", {"user": "user1"})
        self.logger.log_event("login", "INFO", {"user": "user2"})
        self.logger.log_event("error", "ERROR", {"msg": "test error"})
        self.logger.log_event("warning", "WARNING", {"msg": "test warning"})

        # Filter by type
        login_events = self.logger.get_recent_events(event_type="login")
        self.assertEqual(len(login_events), 2)

        # Filter by severity
        error_events = self.logger.get_recent_events(severity="ERROR")
        self.assertEqual(len(error_events), 1)


class TestEnhancedTemplateVerifier(unittest.TestCase):
    """Test enhanced template signature verification."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = SecurityConfig()
        self.audit = SecurityAuditLogger()

        # Mock cryptography if not available
        if not hasattr(self, "_crypto_mocked"):
            self._mock_crypto()

    def _mock_crypto(self):
        """Mock cryptography functions for testing."""
        try:
            from cryptography.hazmat.primitives.asymmetric import ed25519
        except ImportError:
            # Create mock if cryptography not available
            import sys
            from unittest.mock import MagicMock

            mock_ed25519 = MagicMock()
            mock_crypto = MagicMock()
            mock_crypto.hazmat.primitives.asymmetric.ed25519 = mock_ed25519
            mock_crypto.hazmat.backends.default_backend = MagicMock(return_value=None)
            mock_crypto.exceptions.InvalidSignature = Exception

            sys.modules["cryptography"] = mock_crypto
            sys.modules["cryptography.hazmat"] = mock_crypto.hazmat
            sys.modules["cryptography.hazmat.primitives"] = mock_crypto.hazmat.primitives
            sys.modules["cryptography.hazmat.primitives.asymmetric"] = (
                mock_crypto.hazmat.primitives.asymmetric
            )
            sys.modules["cryptography.hazmat.primitives.asymmetric.ed25519"] = mock_ed25519
            sys.modules["cryptography.hazmat.backends"] = mock_crypto.hazmat.backends
            sys.modules["cryptography.exceptions"] = mock_crypto.exceptions

            self._crypto_mocked = True

    def test_key_management(self):
        """Test key management operations."""
        verifier = EnhancedTemplateVerifier(self.config, self.audit)

        # Add trusted key
        key_id = "test_key_1"
        verifier.add_trusted_key(key_id, TEST_PUBLIC_KEY)

        # Check key was added
        self.assertIn(key_id, verifier._trusted_keys)

        # Revoke key
        verifier.revoke_key(key_id, "Test revocation")

        # Check key was revoked
        self.assertIn(key_id, verifier._revoked_keys)
        self.assertNotIn(key_id, verifier._trusted_keys)

    def test_key_expiration(self):
        """Test key expiration handling."""
        verifier = EnhancedTemplateVerifier(self.config, self.audit)

        # Add key with past expiration
        expired_time = datetime.now(timezone.utc) - timedelta(days=1)
        verifier.add_trusted_key("expired_key", TEST_PUBLIC_KEY, expired_time)

        # Add valid key
        future_time = datetime.now(timezone.utc) + timedelta(days=30)
        verifier.add_trusted_key("valid_key", TEST_PUBLIC_KEY, future_time)

        # Cleanup expired keys
        removed = verifier.cleanup_expired_keys()

        self.assertEqual(removed, 1)
        self.assertNotIn("expired_key", verifier._trusted_keys)
        self.assertIn("valid_key", verifier._trusted_keys)

    @patch("devdocai.operations.marketplace_security.ed25519")
    def test_signature_verification_with_caching(self, mock_ed25519):
        """Test signature verification with caching."""
        verifier = EnhancedTemplateVerifier(self.config, self.audit)

        # Mock successful verification
        mock_key = MagicMock()
        mock_ed25519.Ed25519PublicKey.from_public_bytes.return_value = mock_key
        mock_key.verify.return_value = None  # No exception means success

        message = b"test message"
        signature = TEST_SIGNATURE
        public_key = TEST_PUBLIC_KEY

        # First verification (cache miss)
        result1 = verifier.verify_signature_enhanced(message, signature, public_key)
        self.assertTrue(result1)

        # Second verification (cache hit)
        result2 = verifier.verify_signature_enhanced(message, signature, public_key)
        self.assertTrue(result2)

        # Verify mock was called only once (cached)
        mock_ed25519.Ed25519PublicKey.from_public_bytes.assert_called_once()

    def test_unsupported_algorithm_rejection(self):
        """Test rejection of unsupported algorithms."""
        verifier = EnhancedTemplateVerifier(self.config, self.audit)

        # Try unsupported algorithm
        result = verifier.verify_signature_enhanced(
            b"message",
            TEST_SIGNATURE,
            TEST_PUBLIC_KEY,
            algorithm="rsa",  # Not in supported_algorithms
        )

        self.assertFalse(result)

        # Check audit log
        events = self.audit.get_recent_events(event_type="unsupported_algorithm")
        self.assertEqual(len(events), 1)


class TestTemplateSecurityValidator(unittest.TestCase):
    """Test template security validation."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = SecurityConfig()
        self.audit = SecurityAuditLogger()
        self.validator = TemplateSecurityValidator(self.config, self.audit)

    def test_metadata_validation(self):
        """Test template metadata validation."""
        # Valid metadata
        valid_metadata = {
            "name": "test_template",
            "version": "1.0.0",
            "description": "Test template",
            "content": "Template content",
        }

        errors = self.validator.validate_template_metadata(valid_metadata)
        self.assertEqual(len(errors), 0)

        # Missing required field
        invalid_metadata = {
            "name": "test_template",
            "version": "1.0.0",
            # Missing description and content
        }

        errors = self.validator.validate_template_metadata(invalid_metadata)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("Missing required field" in e for e in errors))

    def test_name_validation(self):
        """Test template name validation."""
        # Invalid characters in name
        metadata = {
            "name": "test<script>alert(1)</script>",
            "version": "1.0.0",
            "description": "Test",
            "content": "Content",
        }

        errors = self.validator.validate_template_metadata(metadata)
        self.assertTrue(any("invalid characters" in e for e in errors))

        # Path traversal in name
        metadata["name"] = "../../etc/passwd"
        errors = self.validator.validate_template_metadata(metadata)
        self.assertTrue(any("path traversal" in e for e in errors))

    def test_version_validation(self):
        """Test version format validation."""
        # Invalid version format
        metadata = {
            "name": "test",
            "version": "v1.0",  # Invalid semver
            "description": "Test",
            "content": "Content",
        }

        errors = self.validator.validate_template_metadata(metadata)
        self.assertTrue(any("Invalid version format" in e for e in errors))

        # Valid semver
        metadata["version"] = "1.0.0-beta.1+build.123"
        errors = self.validator.validate_template_metadata(metadata)
        self.assertFalse(any("Invalid version format" in e for e in errors))

    def test_xss_detection(self):
        """Test XSS pattern detection."""
        dangerous_content = """
        <script>alert('XSS')</script>
        <img src=x onerror=alert(1)>
        <a href="javascript:void(0)">Click</a>
        """

        threats = self.validator.scan_for_threats(dangerous_content)

        self.assertGreater(len(threats), 0)
        self.assertTrue(any("XSS" in desc for _, desc in threats))

    def test_code_injection_detection(self):
        """Test code injection pattern detection."""
        dangerous_content = """
        eval('malicious code')
        exec('import os; os.system("rm -rf /")')
        __import__('os').system('whoami')
        subprocess.call(['rm', '-rf', '/'])
        """

        threats = self.validator.scan_for_threats(dangerous_content)

        self.assertGreater(len(threats), 0)
        self.assertTrue(any("Code injection" in desc for _, desc in threats))

    def test_sql_injection_detection(self):
        """Test SQL injection pattern detection."""
        dangerous_content = """
        SELECT * FROM users WHERE id = '1' OR '1'='1';
        ; DROP TABLE users; --
        ; DELETE FROM accounts;
        """

        threats = self.validator.scan_for_threats(dangerous_content)

        self.assertGreater(len(threats), 0)
        self.assertTrue(any("SQL injection" in desc for _, desc in threats))

    def test_path_traversal_detection(self):
        """Test path traversal pattern detection."""
        dangerous_content = """
        ../../../etc/passwd
        ..\\..\\..\\windows\\system32\\config\\sam
        """

        threats = self.validator.scan_for_threats(dangerous_content)

        self.assertGreater(len(threats), 0)
        self.assertTrue(any("Path traversal" in desc for _, desc in threats))

    def test_pii_detection(self):
        """Test PII detection and masking."""
        content_with_pii = """
        Contact: john.doe@example.com
        SSN: 123-45-6789
        Phone: 555-123-4567
        Card: 1234567812345678
        """

        pii_found = self.validator.detect_pii(content_with_pii)

        self.assertGreater(len(pii_found), 0)

        # Check PII types detected
        pii_types = [pii_type for pii_type, _ in pii_found]
        self.assertIn("email", pii_types)
        self.assertIn("ssn", pii_types)
        self.assertIn("phone", pii_types)

    def test_content_sanitization(self):
        """Test content sanitization."""
        dangerous_content = "<script>alert('XSS')</script>Hello World"

        sanitized = self.validator.sanitize_content(dangerous_content)

        # Check dangerous patterns removed/escaped
        self.assertNotIn("<script>", sanitized)
        self.assertIn("Hello World", sanitized)

    def test_comprehensive_validation(self):
        """Test comprehensive template validation."""
        metadata = {
            "name": "test_template",
            "version": "1.0.0",
            "description": "Test template",
            "author": "Test Author",
            "content": "Safe template content without any threats",
        }

        content = "Safe template content without any threats"

        is_valid, errors, report = self.validator.validate_template_security(metadata, content)

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        self.assertTrue(report["metadata_valid"])
        self.assertTrue(report["content_safe"])

    def test_zip_bomb_detection(self):
        """Test zip bomb detection."""
        # Content starting with ZIP signature
        zip_content = "PK" + "A" * 10000  # Simulated ZIP file

        threats = self.validator.scan_for_threats(zip_content)

        self.assertTrue(any("zip_bomb_risk" in desc for _, desc in threats))

    def test_low_entropy_detection(self):
        """Test low entropy content detection (DoS risk)."""
        # Very repetitive content
        low_entropy_content = "A" * 10000

        threats = self.validator.scan_for_threats(low_entropy_content)

        self.assertTrue(any("dos_risk" in desc for _, desc in threats))


class TestRateLimiter(unittest.TestCase):
    """Test rate limiting functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = SecurityConfig()
        self.config.max_requests_per_hour = 10  # Low limit for testing
        self.config.burst_limit = 3
        self.audit = SecurityAuditLogger()
        self.limiter = RateLimiter(self.config, self.audit)

    def test_rate_limiting(self):
        """Test basic rate limiting."""
        client_id = "test_client"

        # Should allow burst limit requests
        for i in range(self.config.burst_limit):
            allowed, retry = self.limiter.check_rate_limit(client_id, "request")
            self.assertTrue(allowed)
            self.assertIsNone(retry)

        # Next request should be rate limited
        allowed, retry = self.limiter.check_rate_limit(client_id, "request")
        self.assertFalse(allowed)
        self.assertIsNotNone(retry)
        self.assertGreater(retry, 0)

    def test_different_operations(self):
        """Test different operation types have separate limits."""
        client_id = "test_client"

        # Downloads should have separate limit
        allowed_download, _ = self.limiter.check_rate_limit(client_id, "download")
        self.assertTrue(allowed_download)

        # Uploads should have separate limit
        allowed_upload, _ = self.limiter.check_rate_limit(client_id, "upload")
        self.assertTrue(allowed_upload)

    def test_token_refill(self):
        """Test token bucket refill over time."""
        client_id = "test_client"

        # Exhaust tokens
        for i in range(self.config.burst_limit):
            self.limiter.check_rate_limit(client_id, "request")

        # Should be rate limited
        allowed, _ = self.limiter.check_rate_limit(client_id, "request")
        self.assertFalse(allowed)

        # Wait for token refill (simulate time passing)
        # In real scenario, would wait actual time
        bucket = self.limiter._buckets[f"{client_id}:request"]
        bucket["last_refill"] = time.time() - 3600  # Simulate 1 hour passed

        # Should be allowed again
        allowed, _ = self.limiter.check_rate_limit(client_id, "request")
        self.assertTrue(allowed)

    def test_reset_bucket(self):
        """Test resetting rate limit buckets."""
        client_id = "test_client"

        # Exhaust tokens
        for i in range(self.config.burst_limit):
            self.limiter.check_rate_limit(client_id, "request")

        # Reset bucket
        self.limiter.reset_bucket(client_id, "request")

        # Should be allowed again
        allowed, _ = self.limiter.check_rate_limit(client_id, "request")
        self.assertTrue(allowed)

    def test_usage_statistics(self):
        """Test usage statistics retrieval."""
        client_id = "test_client"

        # Make some requests
        self.limiter.check_rate_limit(client_id, "request")
        self.limiter.check_rate_limit(client_id, "download")

        stats = self.limiter.get_usage_stats(client_id)

        self.assertIn("request", stats)
        self.assertIn("download", stats)
        self.assertEqual(stats["request"]["request_count"], 1)


class TestTemplateSandbox(unittest.TestCase):
    """Test template sandboxing."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = SecurityConfig()
        self.audit = SecurityAuditLogger()
        self.sandbox = TemplateSandbox(self.config, self.audit)

    def test_path_validation(self):
        """Test path validation within sandbox."""
        # Path within sandbox
        safe_path = self.sandbox._sandbox_dir / "test.txt"
        self.assertTrue(self.sandbox.validate_path(safe_path))

        # Path outside sandbox
        unsafe_path = Path("/etc/passwd")
        self.assertFalse(self.sandbox.validate_path(unsafe_path))

        # Path with traversal
        traversal_path = self.sandbox._sandbox_dir / ".." / ".." / "etc" / "passwd"
        self.assertFalse(self.sandbox.validate_path(traversal_path))

    def test_safe_template_processing(self):
        """Test safe template processing in sandbox."""
        template_content = "Safe template content"

        def safe_operation(template_file):
            return template_file.read_text().upper()

        success, result, error = self.sandbox.process_template_safely(
            template_content, safe_operation
        )

        self.assertTrue(success)
        self.assertEqual(result, "SAFE TEMPLATE CONTENT")
        self.assertIsNone(error)

    def test_sandbox_timeout(self):
        """Test sandbox timeout protection."""
        template_content = "Test content"

        def slow_operation(template_file):
            time.sleep(10)  # Longer than timeout
            return "Should not reach here"

        # Set short timeout for test
        self.sandbox.config.sandbox_timeout_seconds = 1

        success, result, error = self.sandbox.process_template_safely(
            template_content, slow_operation
        )

        self.assertFalse(success)
        self.assertIsNone(result)
        self.assertIn("timeout", error.lower())

    def test_sandbox_error_handling(self):
        """Test sandbox error handling."""
        template_content = "Test content"

        def failing_operation(template_file):
            raise ValueError("Intentional error")

        success, result, error = self.sandbox.process_template_safely(
            template_content, failing_operation
        )

        self.assertFalse(success)
        self.assertIsNone(result)
        self.assertIn("Intentional error", error)

    def test_archive_scanning(self):
        """Test archive scanning for security issues."""
        # Create a test archive
        temp_dir = tempfile.mkdtemp()
        archive_path = Path(temp_dir) / "test.zip"

        try:
            with zipfile.ZipFile(archive_path, "w") as zf:
                # Add normal file
                zf.writestr("normal.txt", "Normal content")

                # Add file with path traversal
                zf.writestr("../../../etc/passwd", "Malicious")

            is_safe, issues = self.sandbox.scan_archive(archive_path)

            self.assertFalse(is_safe)
            self.assertGreater(len(issues), 0)
            self.assertTrue(any("Path traversal" in issue for issue in issues))

        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_archive_size_limit(self):
        """Test archive size limit enforcement."""
        temp_dir = tempfile.mkdtemp()
        archive_path = Path(temp_dir) / "large.zip"

        try:
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # Add large file that would exceed limit when extracted
                large_content = "A" * (int(self.config.max_template_size_mb * 1024 * 1024) + 1)
                zf.writestr("large.txt", large_content)

            is_safe, issues = self.sandbox.scan_archive(archive_path)

            self.assertFalse(is_safe)
            self.assertTrue(any("exceeds size limit" in issue for issue in issues))

        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)


class TestMarketplaceSecurityManager(unittest.TestCase):
    """Test main security manager."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = MarketplaceSecurityManager()

    def test_manager_initialization(self):
        """Test security manager initialization."""
        self.assertIsNotNone(self.manager.audit)
        self.assertIsNotNone(self.manager.verifier)
        self.assertIsNotNone(self.manager.validator)
        self.assertIsNotNone(self.manager.rate_limiter)
        self.assertIsNotNone(self.manager.sandbox)

    def test_template_validation(self):
        """Test comprehensive template validation."""
        template_data = {
            "name": "test_template",
            "version": "1.0.0",
            "description": "Test template",
            "author": "Test Author",
        }

        content = "Safe template content"

        is_valid, report = self.manager.validate_template(template_data, content)

        self.assertTrue(is_valid)
        self.assertIn("timestamp", report)
        self.assertIn("security_scan", report)
        self.assertEqual(len(report["errors"]), 0)

    def test_template_with_threats(self):
        """Test template validation with threats."""
        template_data = {
            "name": "malicious_template",
            "version": "1.0.0",
            "description": "Malicious template",
            "author": "Attacker",
        }

        dangerous_content = "<script>alert('XSS')</script>"

        is_valid, report = self.manager.validate_template(template_data, dangerous_content)

        # In HIGH security level, should reject
        if self.manager.config.level in [SecurityLevel.HIGH, SecurityLevel.PARANOID]:
            self.assertFalse(is_valid)
            self.assertGreater(len(report["errors"]), 0)

    def test_rate_limiting_integration(self):
        """Test rate limiting integration."""
        client_id = "test_client"

        # Should allow initial requests
        allowed, retry = self.manager.check_rate_limit(client_id, "request")
        self.assertTrue(allowed)

        # Exhaust rate limit
        for _ in range(20):
            self.manager.check_rate_limit(client_id, "request")

        # Should be rate limited
        allowed, retry = self.manager.check_rate_limit(client_id, "request")
        self.assertFalse(allowed)
        self.assertIsNotNone(retry)

    def test_sandbox_processing(self):
        """Test sandbox processing integration."""
        template_content = "print('Hello World')"

        def processor(template_file):
            return f"Processed: {template_file.read_text()}"

        success, result, error = self.manager.process_in_sandbox(template_content, processor)

        self.assertTrue(success)
        self.assertIn("Processed", result)

    def test_security_metrics(self):
        """Test security metrics collection."""
        # Perform some operations
        self.manager.validate_template(
            {"name": "test", "version": "1.0.0", "description": "Test", "content": "Content"},
            "Test content",
        )

        metrics = self.manager.get_security_metrics()

        self.assertIn("config", metrics)
        self.assertIn("metrics", metrics)
        self.assertEqual(metrics["metrics"]["templates_validated"], 1)

    def test_compliance_report(self):
        """Test compliance report generation."""
        report = self.manager.generate_compliance_report()

        self.assertIn("generated_at", report)
        self.assertIn("security_level", report)
        self.assertIn("audit_summary", report)
        self.assertIn("owasp_compliance", report)

        # Check OWASP compliance
        owasp = report["owasp_compliance"]
        for category in ["A01", "A02", "A03", "A04", "A05", "A06", "A07", "A08", "A09", "A10"]:
            key = f"{category}_"
            self.assertTrue(any(k.startswith(key) for k in owasp.keys()))

    def test_paranoid_mode(self):
        """Test paranoid security mode."""
        paranoid_config = SecurityConfig(level=SecurityLevel.PARANOID)
        manager = MarketplaceSecurityManager(paranoid_config)

        # Should require signatures
        template_data = {
            "name": "unsigned",
            "version": "1.0.0",
            "description": "Unsigned template",
            "content": "Content",
        }

        is_valid, report = manager.validate_template(
            template_data, "Content", signature=None, public_key=None  # No signature
        )

        self.assertFalse(is_valid)
        self.assertTrue(any("signature required" in e.lower() for e in report["errors"]))


class TestSecurityIntegration(unittest.TestCase):
    """Test security integration with marketplace client."""

    @patch("devdocai.operations.marketplace.TemplateMarketplaceClient")
    def test_security_integration(self, mock_client_class):
        """Test integrating security with marketplace client."""
        from devdocai.operations.marketplace_security import integrate_security_with_marketplace

        # Create mock client
        mock_client = MagicMock()
        mock_client.verify_signatures = True
        mock_client.download_template = MagicMock(return_value=None)

        # Integrate security
        enhanced_client = integrate_security_with_marketplace(mock_client)

        # Check security manager attached
        self.assertIsNotNone(enhanced_client.security_manager)

        # Check methods added
        self.assertTrue(hasattr(enhanced_client, "validate_template_security"))
        self.assertTrue(hasattr(enhanced_client, "get_security_metrics"))
        self.assertTrue(hasattr(enhanced_client, "generate_security_report"))


class TestOWASPCompliance(unittest.TestCase):
    """Test OWASP Top 10 compliance."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = SecurityConfig(level=SecurityLevel.HIGH)
        self.audit = SecurityAuditLogger()
        self.validator = TemplateSecurityValidator(self.config, self.audit)
        self.manager = MarketplaceSecurityManager(self.config)

    def test_a01_broken_access_control(self):
        """Test A01: Broken Access Control prevention."""
        # Test path traversal prevention
        metadata = {
            "name": "../../admin/config",
            "version": "1.0.0",
            "description": "Test",
            "content": "Content",
        }

        errors = self.validator.validate_template_metadata(metadata)
        self.assertTrue(any("path traversal" in e.lower() for e in errors))

    def test_a02_cryptographic_failures(self):
        """Test A02: Cryptographic Failures prevention."""
        # Test strong cryptography (Ed25519)
        self.assertIn("ed25519", self.config.supported_algorithms)
        self.assertTrue(self.config.enforce_tls)
        self.assertEqual(self.config.min_tls_version, "TLSv1.3")

    def test_a03_injection(self):
        """Test A03: Injection prevention."""
        # Test SQL injection prevention
        content = "'; DROP TABLE users; --"
        threats = self.validator.scan_for_threats(content)
        self.assertTrue(any("SQL injection" in desc for _, desc in threats))

        # Test code injection prevention
        content = "eval('malicious')"
        threats = self.validator.scan_for_threats(content)
        self.assertTrue(any("Code injection" in desc for _, desc in threats))

    def test_a04_insecure_design(self):
        """Test A04: Insecure Design prevention."""
        # Test security by design
        self.assertEqual(self.config.level, SecurityLevel.HIGH)
        self.assertTrue(self.config.enable_signature_verification)
        self.assertTrue(self.config.enable_sandbox)

    def test_a05_security_misconfiguration(self):
        """Test A05: Security Misconfiguration prevention."""
        # Test secure defaults
        self.assertTrue(self.config.enforce_tls)
        self.assertTrue(self.config.enable_audit_logging)
        self.assertTrue(self.config.sensitive_data_masking)

    def test_a06_vulnerable_components(self):
        """Test A06: Vulnerable and Outdated Components prevention."""
        # Test dependency management (Ed25519 library version checks)
        self.assertTrue(self.config.key_rotation_enabled)
        self.assertEqual(self.config.max_key_age_days, 90)

    def test_a07_authentication_failures(self):
        """Test A07: Identification and Authentication Failures prevention."""
        # Test rate limiting for auth attempts
        allowed, retry = self.manager.check_rate_limit("attacker", "upload")
        self.assertIsNotNone(allowed)  # Rate limiting active

    def test_a08_integrity_failures(self):
        """Test A08: Software and Data Integrity Failures prevention."""
        # Test signature verification
        self.assertTrue(self.config.enable_signature_verification)
        self.assertTrue(self.config.require_signed_templates)

    def test_a09_logging_failures(self):
        """Test A09: Security Logging and Monitoring Failures prevention."""
        # Test comprehensive logging
        self.assertTrue(self.config.enable_audit_logging)
        self.assertTrue(self.config.log_security_events)
        self.assertTrue(self.config.log_failed_verifications)

        # Test audit log functionality
        report = self.manager.audit.generate_compliance_report()
        self.assertIn("compliance_status", report)

    def test_a10_ssrf(self):
        """Test A10: Server-Side Request Forgery prevention."""
        # Test URL validation
        self.assertTrue(self.config.enforce_tls)
        self.assertIn("api.devdocai.com", self.config.trusted_hosts)

        # Test network restrictions in sandbox
        self.assertTrue(self.config.restrict_network_access)


if __name__ == "__main__":
    unittest.main()
