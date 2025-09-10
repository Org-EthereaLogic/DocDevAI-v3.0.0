"""Tests for M012 Version Control Integration - Pass 3: Security Hardening
DevDocAI v3.0.0

Comprehensive security tests for version control operations with:
- Input validation and sanitization tests
- Path traversal prevention tests
- Command injection protection tests
- HMAC integrity verification tests
- Audit logging validation
- Rate limiting tests
- Access control tests
- OWASP Top 10 compliance validation

Test Coverage Target: 95%+
"""

import json
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from devdocai.operations.version_security import (
    AccessController,
    AccessLevel,
    AuditLogger,
    CommandSanitizer,
    GitSecurityValidator,
    IntegrityVerifier,
    RateLimiter,
    SecurityContext,
    SecurityEvent,
    SecurityEventType,
    SecurityLevel,
    SecurityManager,
)


class TestGitSecurityValidator:
    """Test Git security validator."""

    def setup_method(self):
        """Set up test validator."""
        self.validator = GitSecurityValidator()

    def test_validate_path_valid(self):
        """Test valid path validation."""
        result = self.validator.validate_path("docs/readme.md", Path("/tmp/repo"))
        assert result.valid
        assert result.security_level == SecurityLevel.LOW

    def test_validate_path_traversal_attempt(self):
        """Test path traversal detection."""
        result = self.validator.validate_path("../../../etc/passwd", Path("/tmp/repo"))
        assert not result.valid
        assert "Dangerous pattern" in result.message
        assert result.security_level == SecurityLevel.CRITICAL

    def test_validate_path_null_byte(self):
        """Test null byte injection detection."""
        result = self.validator.validate_path("file.txt\x00.sh", Path("/tmp/repo"))
        assert not result.valid
        assert "Null byte" in result.message
        assert result.security_level == SecurityLevel.CRITICAL

    def test_validate_path_too_long(self):
        """Test path length validation."""
        long_path = "a" * 5000
        result = self.validator.validate_path(long_path, Path("/tmp/repo"))
        assert not result.valid
        assert "Path too long" in result.message
        assert result.security_level == SecurityLevel.HIGH

    def test_validate_path_absolute_when_relative_expected(self):
        """Test absolute path detection when relative expected."""
        result = self.validator.validate_path("/etc/passwd", Path("/tmp/repo"))
        assert not result.valid
        assert "Absolute path not allowed" in result.message
        assert result.security_level == SecurityLevel.HIGH

    def test_validate_branch_name_valid(self):
        """Test valid branch name."""
        result = self.validator.validate_branch_name("feature/auth-system")
        assert result.valid
        assert result.sanitized_value == "feature/auth-system"

    def test_validate_branch_name_with_dangerous_chars(self):
        """Test branch name sanitization."""
        result = self.validator.validate_branch_name("feature; rm -rf /")
        assert result.valid  # Sanitized
        assert result.sanitized_value == "feature__rm__rf__"
        assert "sanitized" in result.message.lower()

    def test_validate_branch_name_too_long(self):
        """Test branch name length validation."""
        long_name = "a" * 300
        result = self.validator.validate_branch_name(long_name)
        assert not result.valid
        assert "too long" in result.message

    def test_validate_commit_message_valid(self):
        """Test valid commit message."""
        result = self.validator.validate_commit_message("feat: Add authentication system")
        assert result.valid
        assert result.sanitized_value == "feat: Add authentication system"

    def test_validate_commit_message_with_pii(self):
        """Test PII detection in commit message."""
        message = "Update user SSN 123-45-6789 in database"
        result = self.validator.validate_commit_message(message)
        assert not result.valid
        assert "PII detected" in result.message
        assert result.security_level == SecurityLevel.HIGH

    def test_validate_commit_message_with_control_chars(self):
        """Test control character sanitization."""
        message = "Update\x00\x1ffile"
        result = self.validator.validate_commit_message(message)
        assert result.valid
        assert result.sanitized_value == "Updatefile"

    def test_validate_tag_name_valid(self):
        """Test valid tag name."""
        result = self.validator.validate_tag_name("v1.0.0")
        assert result.valid
        assert result.sanitized_value == "v1.0.0"

    def test_validate_tag_name_sanitization(self):
        """Test tag name sanitization."""
        result = self.validator.validate_tag_name("v1.0.0; echo hacked")
        assert result.valid  # Sanitized
        assert result.sanitized_value == "v1.0.0__echo_hacked"

    def test_validate_file_content_valid(self):
        """Test valid file content."""
        content = "# Documentation\n\nThis is valid content."
        result = self.validator.validate_file_content(content, "readme.md")
        assert result.valid
        assert result.security_level == SecurityLevel.LOW

    def test_validate_file_content_too_large(self):
        """Test file size validation."""
        large_content = "a" * (101 * 1024 * 1024)  # 101MB
        result = self.validator.validate_file_content(large_content, "large.md")
        assert not result.valid
        assert "File too large" in result.message
        assert result.security_level == SecurityLevel.MEDIUM

    def test_validate_file_content_with_pii(self):
        """Test PII detection in file content (warning only)."""
        content = "Contact: john@example.com, Phone: 555-123-4567"
        result = self.validator.validate_file_content(content, "contact.md")
        assert result.valid  # PII in content is allowed with warning
        assert result.security_level == SecurityLevel.MEDIUM  # Elevated due to PII


class TestCommandSanitizer:
    """Test command sanitizer."""

    def setup_method(self):
        """Set up test sanitizer."""
        self.sanitizer = CommandSanitizer()

    def test_sanitize_safe_command(self):
        """Test safe Git command."""
        is_safe, error = self.sanitizer.sanitize_git_command("status", [])
        assert is_safe
        assert error is None

    def test_sanitize_dangerous_command(self):
        """Test dangerous Git command blocking."""
        is_safe, error = self.sanitizer.sanitize_git_command("filter-branch", ["--all"])
        assert not is_safe
        assert "Dangerous Git command blocked" in error

    def test_sanitize_command_with_shell_metacharacters(self):
        """Test shell metacharacter detection."""
        is_safe, error = self.sanitizer.sanitize_git_command("commit", ["-m", "test; rm -rf /"])
        assert not is_safe
        assert "Shell metacharacters detected" in error

    def test_sanitize_command_with_command_substitution(self):
        """Test command substitution detection."""
        is_safe, error = self.sanitizer.sanitize_git_command("commit", ["-m", "$(whoami)"])
        assert not is_safe
        assert "Command substitution detected" in error

    def test_sanitize_command_with_backticks(self):
        """Test backtick command substitution detection."""
        is_safe, error = self.sanitizer.sanitize_git_command("commit", ["-m", "`id`"])
        assert not is_safe
        assert "Command substitution detected" in error

    def test_escape_shell_arg(self):
        """Test shell argument escaping."""
        escaped = self.sanitizer.escape_shell_arg("test'value")
        assert "'" not in escaped or escaped == "'test'\"'\"'value'"  # Properly escaped


class TestIntegrityVerifier:
    """Test integrity verifier."""

    def setup_method(self):
        """Set up test verifier."""
        self.verifier = IntegrityVerifier()

    def test_generate_hmac(self):
        """Test HMAC generation."""
        data = "test data"
        signature = self.verifier.generate_hmac(data)
        assert len(signature) == 64  # SHA256 hex digest
        assert all(c in "0123456789abcdef" for c in signature)

    def test_verify_hmac_valid(self):
        """Test HMAC verification with valid signature."""
        data = "test data"
        signature = self.verifier.generate_hmac(data)
        assert self.verifier.verify_hmac(data, signature)

    def test_verify_hmac_invalid(self):
        """Test HMAC verification with invalid signature."""
        data = "test data"
        fake_signature = "0" * 64
        assert not self.verifier.verify_hmac(data, fake_signature)

    def test_sign_document(self):
        """Test document signing."""
        doc_id = "doc123"
        content = "Document content"
        signature = self.verifier.sign_document(doc_id, content)
        assert len(signature) == 64
        assert doc_id in self.verifier._signatures

    def test_verify_document_valid(self):
        """Test document verification with valid signature."""
        doc_id = "doc123"
        content = "Document content"
        signature = self.verifier.sign_document(doc_id, content)
        assert self.verifier.verify_document(doc_id, content, signature)

    def test_verify_document_tampered(self):
        """Test document verification with tampered content."""
        doc_id = "doc123"
        content = "Original content"
        signature = self.verifier.sign_document(doc_id, content)
        tampered_content = "Tampered content"
        assert not self.verifier.verify_document(doc_id, tampered_content, signature)


class TestAuditLogger:
    """Test audit logger."""

    def setup_method(self):
        """Set up test logger."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = Path(self.temp_dir) / "audit.log"
        self.logger = AuditLogger(self.log_file)

    def test_log_event(self):
        """Test event logging."""
        event = SecurityEvent(
            event_type=SecurityEventType.ACCESS_DENIED,
            message="Access denied to resource",
            severity=SecurityLevel.HIGH,
            user_id="user123",
        )
        self.logger.log_event(event)

        # Check in-memory storage
        recent = self.logger.get_recent_events(1)
        assert len(recent) == 1
        assert recent[0].message == "Access denied to resource"

        # Check file storage
        assert self.log_file.exists()
        with open(self.log_file) as f:
            log_entry = json.loads(f.readline())
            assert log_entry["message"] == "Access denied to resource"
            assert log_entry["event_type"] == "access_denied"

    def test_get_event_statistics(self):
        """Test event statistics."""
        # Log multiple events
        for _ in range(3):
            self.logger.log_event(
                SecurityEvent(
                    event_type=SecurityEventType.AUTHENTICATION_FAILURE,
                    message="Auth failed",
                    severity=SecurityLevel.HIGH,
                )
            )

        self.logger.log_event(
            SecurityEvent(
                event_type=SecurityEventType.RATE_LIMIT,
                message="Rate limited",
                severity=SecurityLevel.MEDIUM,
            )
        )

        stats = self.logger.get_event_statistics()
        assert stats[SecurityEventType.AUTHENTICATION_FAILURE] == 3
        assert stats[SecurityEventType.RATE_LIMIT] == 1

    def test_detect_suspicious_patterns(self):
        """Test suspicious pattern detection."""
        # Generate authentication failures
        for i in range(4):
            self.logger.log_event(
                SecurityEvent(
                    event_type=SecurityEventType.AUTHENTICATION_FAILURE,
                    message=f"Auth failed {i}",
                    severity=SecurityLevel.HIGH,
                    timestamp=datetime.now(),
                )
            )

        patterns = self.logger.detect_suspicious_patterns()
        assert any("authentication failures" in p.lower() for p in patterns)

    def test_detect_path_traversal_attempts(self):
        """Test path traversal detection."""
        self.logger.log_event(
            SecurityEvent(
                event_type=SecurityEventType.PATH_TRAVERSAL,
                message="Path traversal attempt",
                severity=SecurityLevel.CRITICAL,
            )
        )

        patterns = self.logger.detect_suspicious_patterns()
        assert any("path traversal" in p.lower() for p in patterns)


class TestRateLimiter:
    """Test rate limiter."""

    def setup_method(self):
        """Set up test limiter."""
        self.limiter = RateLimiter(rate=5, window=1)  # 5 requests per second

    def test_rate_limit_allowed(self):
        """Test requests within rate limit."""
        identifier = "user123"

        for _ in range(5):
            allowed, retry_after = self.limiter.check_rate_limit(identifier)
            assert allowed
            assert retry_after is None

    def test_rate_limit_exceeded(self):
        """Test rate limit exceeded."""
        identifier = "user123"

        # Exhaust rate limit
        for _ in range(5):
            self.limiter.check_rate_limit(identifier)

        # Next request should be denied
        allowed, retry_after = self.limiter.check_rate_limit(identifier)
        assert not allowed
        assert retry_after > 0

    def test_rate_limit_window_expiry(self):
        """Test rate limit window expiry."""
        identifier = "user123"

        # Exhaust rate limit
        for _ in range(5):
            self.limiter.check_rate_limit(identifier)

        # Wait for window to expire
        time.sleep(1.1)

        # Should be allowed again
        allowed, retry_after = self.limiter.check_rate_limit(identifier)
        assert allowed
        assert retry_after is None

    def test_rate_limit_reset(self):
        """Test rate limit reset."""
        identifier = "user123"

        # Exhaust rate limit
        for _ in range(5):
            self.limiter.check_rate_limit(identifier)

        # Reset
        self.limiter.reset(identifier)

        # Should be allowed again
        allowed, retry_after = self.limiter.check_rate_limit(identifier)
        assert allowed


class TestAccessController:
    """Test access controller."""

    def setup_method(self):
        """Set up test controller."""
        self.controller = AccessController()

    def test_generate_token(self):
        """Test token generation."""
        token = self.controller.generate_token("user123", AccessLevel.READ)
        assert len(token) > 20
        assert token in self.controller._tokens

    def test_validate_token_valid(self):
        """Test valid token validation."""
        token = self.controller.generate_token("user123", AccessLevel.WRITE)
        context = self.controller.validate_token(token)

        assert context is not None
        assert context.user_id == "user123"
        assert context.access_level == AccessLevel.WRITE
        assert context.authenticated

    def test_validate_token_invalid(self):
        """Test invalid token validation."""
        context = self.controller.validate_token("invalid_token")
        assert context is None

    def test_validate_token_expired(self):
        """Test expired token validation."""
        token = self.controller.generate_token("user123", AccessLevel.READ)

        # Manually expire token
        context = self.controller._tokens[token]
        context.timestamp = datetime.now() - timedelta(hours=25)

        # Should be invalid
        validated = self.controller.validate_token(token)
        assert validated is None
        assert token not in self.controller._tokens

    def test_check_permission_read(self):
        """Test read permission check."""
        context = SecurityContext(
            user_id="user123", access_level=AccessLevel.READ, authenticated=True
        )

        assert self.controller.check_permission(context, "read")
        assert self.controller.check_permission(context, "list")
        assert not self.controller.check_permission(context, "write")
        assert not self.controller.check_permission(context, "delete")

    def test_check_permission_write(self):
        """Test write permission check."""
        context = SecurityContext(
            user_id="user123", access_level=AccessLevel.WRITE, authenticated=True
        )

        assert self.controller.check_permission(context, "read")
        assert self.controller.check_permission(context, "write")
        assert self.controller.check_permission(context, "update")
        assert self.controller.check_permission(context, "commit")

    def test_check_permission_admin(self):
        """Test admin permission check."""
        context = SecurityContext(
            user_id="admin", access_level=AccessLevel.ADMIN, authenticated=True
        )

        # Admin has all permissions
        assert self.controller.check_permission(context, "read")
        assert self.controller.check_permission(context, "write")
        assert self.controller.check_permission(context, "delete")
        assert self.controller.check_permission(context, "admin")
        assert self.controller.check_permission(context, "anything")

    def test_check_permission_not_authenticated(self):
        """Test permission check without authentication."""
        context = SecurityContext(
            user_id="user123",
            access_level=AccessLevel.ADMIN,
            authenticated=False,  # Not authenticated
        )

        assert not self.controller.check_permission(context, "read")

    def test_revoke_token(self):
        """Test token revocation."""
        token = self.controller.generate_token("user123", AccessLevel.READ)
        assert token in self.controller._tokens

        self.controller.revoke_token(token)
        assert token not in self.controller._tokens

        # Should not be valid anymore
        context = self.controller.validate_token(token)
        assert context is None


class TestSecurityManager:
    """Test security manager."""

    def setup_method(self):
        """Set up test manager."""
        self.config = {
            "enforce_authentication": True,
            "enforce_rate_limiting": True,
            "enforce_integrity": True,
            "max_repository_size": 1024 * 1024,  # 1MB for testing
        }
        self.manager = SecurityManager(self.config)

    def test_validate_repository_path_valid(self):
        """Test valid repository path validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            assert self.manager.validate_repository_path(repo_path)

    def test_validate_repository_path_invalid(self):
        """Test invalid repository path validation."""
        # Path traversal attempt
        assert not self.manager.validate_repository_path(Path("../../../etc"))

    def test_validate_repository_size_exceeded(self):
        """Test repository size validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            # Create large file
            large_file = repo_path / "large.bin"
            large_file.write_bytes(b"x" * (2 * 1024 * 1024))  # 2MB

            assert not self.manager.validate_repository_path(repo_path)

    def test_sign_commit(self):
        """Test commit signing."""
        commit_data = {"hash": "abc123", "message": "Test commit", "author": "test@example.com"}

        signature = self.manager.sign_commit(commit_data)
        assert len(signature) == 64

    def test_verify_commit_signature_valid(self):
        """Test valid commit signature verification."""
        commit_data = {"hash": "abc123", "message": "Test commit", "author": "test@example.com"}

        signature = self.manager.sign_commit(commit_data)
        assert self.manager.verify_commit_signature(commit_data, signature)

    def test_verify_commit_signature_invalid(self):
        """Test invalid commit signature verification."""
        commit_data = {"hash": "abc123", "message": "Test commit", "author": "test@example.com"}

        fake_signature = "0" * 64
        assert not self.manager.verify_commit_signature(commit_data, fake_signature)

    def test_secure_operation_decorator_authenticated(self):
        """Test secure operation decorator with authentication."""
        # Create authenticated context
        token = self.manager.access_controller.generate_token("user123", AccessLevel.WRITE)
        context = self.manager.access_controller.validate_token(token)

        @self.manager.secure_operation("test_operation", context)
        def test_func():
            return "success"

        result = test_func()
        assert result == "success"

    def test_secure_operation_decorator_not_authenticated(self):
        """Test secure operation decorator without authentication."""
        context = SecurityContext(authenticated=False)

        @self.manager.secure_operation("test_operation", context)
        def test_func():
            return "success"

        with pytest.raises(PermissionError, match="Authentication required"):
            test_func()

    def test_secure_operation_decorator_rate_limited(self):
        """Test secure operation decorator with rate limiting."""
        # Create authenticated context
        token = self.manager.access_controller.generate_token("user123", AccessLevel.WRITE)
        context = self.manager.access_controller.validate_token(token)

        # Set very low rate limit
        self.manager.rate_limiter = RateLimiter(rate=1, window=1)

        @self.manager.secure_operation("test_operation", context)
        def test_func():
            return "success"

        # First call should succeed
        assert test_func() == "success"

        # Second call should be rate limited
        with pytest.raises(RuntimeError, match="Rate limit exceeded"):
            test_func()

    def test_get_security_report(self):
        """Test security report generation."""
        # Generate some events
        self.manager.audit.log_event(
            SecurityEvent(
                event_type=SecurityEventType.ACCESS_DENIED,
                message="Test event",
                severity=SecurityLevel.HIGH,
            )
        )

        report = self.manager.get_security_report()

        assert "event_statistics" in report
        assert "recent_events" in report
        assert "suspicious_patterns" in report
        assert "active_tokens" in report
        assert "rate_limit_status" in report


class TestSecurityIntegration:
    """Integration tests for security features."""

    def test_complete_security_workflow(self):
        """Test complete security workflow."""
        # Initialize security manager
        config = {
            "enforce_authentication": True,
            "enforce_rate_limiting": True,
            "enforce_integrity": True,
        }
        manager = SecurityManager(config)

        # Generate token
        token = manager.access_controller.generate_token("user123", AccessLevel.WRITE)

        # Validate token
        context = manager.access_controller.validate_token(token)
        assert context is not None

        # Check permissions
        assert manager.access_controller.check_permission(context, "write")

        # Validate path
        result = manager.validator.validate_path("docs/readme.md", Path("/tmp"))
        assert result.valid

        # Sign document
        signature = manager.integrity.sign_document("doc123", "content")
        assert manager.integrity.verify_document("doc123", "content", signature)

        # Check rate limiting
        allowed, _ = manager.rate_limiter.check_rate_limit("user123")
        assert allowed

        # Log event
        manager.audit.log_event(
            SecurityEvent(
                event_type=SecurityEventType.ACCESS_DENIED,
                message="Test event",
                severity=SecurityLevel.LOW,
                user_id="user123",
            )
        )

        # Get report
        report = manager.get_security_report()
        assert report["event_statistics"][SecurityEventType.ACCESS_DENIED] > 0

    def test_security_breach_detection(self):
        """Test security breach detection workflow."""
        manager = SecurityManager({})

        # Simulate multiple authentication failures
        for i in range(5):
            manager.audit.log_event(
                SecurityEvent(
                    event_type=SecurityEventType.AUTHENTICATION_FAILURE,
                    message=f"Failed login attempt {i}",
                    severity=SecurityLevel.HIGH,
                    timestamp=datetime.now(),
                )
            )

        # Simulate path traversal attempt
        manager.audit.log_event(
            SecurityEvent(
                event_type=SecurityEventType.PATH_TRAVERSAL,
                message="Path traversal detected",
                severity=SecurityLevel.CRITICAL,
            )
        )

        # Simulate command injection attempt
        manager.audit.log_event(
            SecurityEvent(
                event_type=SecurityEventType.COMMAND_INJECTION,
                message="Command injection detected",
                severity=SecurityLevel.CRITICAL,
            )
        )

        # Check suspicious pattern detection
        patterns = manager.audit.detect_suspicious_patterns()
        assert len(patterns) >= 3
        assert any("authentication" in p.lower() for p in patterns)
        assert any("path traversal" in p.lower() for p in patterns)
        assert any("command injection" in p.lower() for p in patterns)


if __name__ == "__main__":
    pytest.main(
        [__file__, "-v", "--cov=devdocai.operations.version_security", "--cov-report=term-missing"]
    )
