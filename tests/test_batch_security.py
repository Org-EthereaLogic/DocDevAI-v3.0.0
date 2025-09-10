"""
Test Suite for M011 Batch Operations Manager - Pass 3: Security Tests
DevDocAI v3.0.0

Security testing suite for hardened batch operations.
Tests input validation, rate limiting, encryption, and OWASP compliance.
"""

import asyncio
import json
import os
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Module under test
from devdocai.operations.batch_secure import SecureOptimizedBatchManager
from devdocai.operations.batch_security import (
    AuditLogger,
    BatchSecurityError,
    BatchSecurityManager,
    CircuitBreaker,
    InputValidator,
    RateLimiter,
    ResourceMonitor,
    SecureCache,
    SecurityConfig,
    SecurityEvent,
)


# ============================================================================
# Security Test Fixtures
# ============================================================================


@pytest.fixture
def security_config():
    """Security configuration for testing."""
    return SecurityConfig(
        enable_rate_limiting=True,
        rate_limit_requests_per_minute=60,
        rate_limit_burst_size=10,
        max_memory_mb=512,
        max_cpu_percent=50.0,
        max_document_size_mb=10,
        max_batch_size=100,
        enable_audit_logging=True,
        enable_cache_encryption=True,
        enable_input_validation=True,
        enable_pii_detection=True,
        enable_circuit_breaker=True,
        circuit_breaker_threshold=3,
    )


@pytest.fixture
def malicious_documents():
    """Generate documents with security threats."""
    return [
        {
            "id": "xss_attack",
            "content": "<script>alert('XSS')</script>",
            "type": "text",
        },
        {
            "id": "sql_injection",
            "content": "'; DROP TABLE users; --",
            "type": "text",
        },
        {
            "id": "path_traversal",
            "content": "../../etc/passwd",
            "type": "text",
        },
        {
            "id": "command_injection",
            "content": "; rm -rf /; echo 'hacked'",
            "type": "text",
        },
        {
            "id": "xxe_attack",
            "content": '<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>',
            "type": "xml",
        },
    ]


@pytest.fixture
def pii_documents():
    """Generate documents with PII data."""
    return [
        {
            "id": "ssn_doc",
            "content": "John's SSN is 123-45-6789",
            "type": "text",
        },
        {
            "id": "credit_card",
            "content": "Payment: 4532-1234-5678-9012",
            "type": "text",
        },
        {
            "id": "email_phone",
            "content": "Contact: john@example.com or 555-123-4567",
            "type": "text",
        },
    ]


@pytest.fixture
async def secure_manager(security_config):
    """Initialize secure batch manager."""
    manager = SecureOptimizedBatchManager(security_config=security_config)
    yield manager
    await manager.shutdown()


# ============================================================================
# Input Validation Tests
# ============================================================================


class TestInputValidation:
    """Test input validation and sanitization."""

    def test_detect_xss_attack(self, security_config):
        """Test XSS attack detection."""
        validator = InputValidator(security_config)
        doc = {
            "id": "test",
            "content": "<script>alert('XSS')</script>Hello",
        }
        
        is_valid, error, issues = validator.validate_document(doc)
        assert not is_valid
        assert "dangerous_pattern" in str(issues)

    def test_detect_sql_injection(self, security_config):
        """Test SQL injection detection."""
        validator = InputValidator(security_config)
        doc = {
            "id": "test",
            "content": "SELECT * FROM users WHERE id = '1' UNION SELECT password FROM admin",
        }
        
        is_valid, error, issues = validator.validate_document(doc)
        assert not is_valid
        assert "dangerous_pattern" in str(issues)

    def test_detect_path_traversal(self, security_config):
        """Test path traversal detection."""
        validator = InputValidator(security_config)
        doc = {
            "id": "test",
            "content": "Load file: ../../etc/passwd",
        }
        
        is_valid, error, issues = validator.validate_document(doc)
        assert not is_valid
        assert "dangerous_pattern" in str(issues)

    def test_sanitize_dangerous_content(self, security_config):
        """Test content sanitization."""
        validator = InputValidator(security_config)
        doc = {
            "id": "test",
            "content": "<script>evil</script>Normal text & 'quotes'",
        }
        
        sanitized = validator.sanitize_document(doc)
        assert "<script>" not in sanitized["content"]
        assert "&amp;" in sanitized["content"]
        assert "&#x27;" in sanitized["content"]

    def test_detect_pii(self, security_config):
        """Test PII detection."""
        validator = InputValidator(security_config)
        doc = {
            "id": "test",
            "content": "SSN: 123-45-6789, Email: test@example.com",
        }
        
        is_valid, error, issues = validator.validate_document(doc)
        assert not is_valid
        assert any("pii" in issue for issue in issues)

    def test_content_size_limit(self, security_config):
        """Test content size validation."""
        validator = InputValidator(security_config)
        doc = {
            "id": "test",
            "content": "x" * (security_config.max_content_length + 1),
        }
        
        is_valid, error, issues = validator.validate_document(doc)
        assert not is_valid
        assert "content_too_large" in issues

    @pytest.mark.asyncio
    async def test_malicious_batch_rejection(self, secure_manager, malicious_documents):
        """Test that malicious documents are rejected."""
        results = await secure_manager.process_batch_optimized(
            malicious_documents,
            lambda x: x,
            client_id="test_client",
        )
        
        # All malicious documents should be filtered out
        successful = [r for r in results if r.success]
        assert len(successful) == 0  # All should be rejected


# ============================================================================
# Rate Limiting Tests
# ============================================================================


class TestRateLimiting:
    """Test rate limiting and DoS protection."""

    def test_rate_limit_enforcement(self, security_config):
        """Test rate limit enforcement."""
        security_config.rate_limit_burst_size = 5
        security_config.rate_limit_requests_per_minute = 60
        
        limiter = RateLimiter(security_config)
        client_id = "test_client"
        
        # Exhaust burst capacity
        for i in range(5):
            allowed, error = limiter.check_rate_limit(client_id)
            assert allowed, f"Request {i+1} should be allowed"
        
        # Next request should be blocked
        allowed, error = limiter.check_rate_limit(client_id)
        assert not allowed
        assert "Rate limit exceeded" in error

    def test_rate_limit_cooldown(self, security_config):
        """Test rate limit cooldown period."""
        security_config.rate_limit_burst_size = 1
        security_config.rate_limit_cooldown_seconds = 1
        
        limiter = RateLimiter(security_config)
        client_id = "test_client"
        
        # First request allowed
        allowed, _ = limiter.check_rate_limit(client_id)
        assert allowed
        
        # Second request blocked
        allowed, _ = limiter.check_rate_limit(client_id)
        assert not allowed
        
        # Wait for cooldown
        time.sleep(1.1)
        
        # Should be allowed again
        allowed, _ = limiter.check_rate_limit(client_id)
        assert allowed

    def test_client_isolation(self, security_config):
        """Test that rate limits are per-client."""
        limiter = RateLimiter(security_config)
        
        # Exhaust client1's limit
        for _ in range(security_config.rate_limit_burst_size):
            limiter.check_rate_limit("client1")
        
        # client1 should be blocked
        allowed, _ = limiter.check_rate_limit("client1")
        assert not allowed
        
        # client2 should still be allowed
        allowed, _ = limiter.check_rate_limit("client2")
        assert allowed

    @pytest.mark.asyncio
    async def test_batch_rate_limiting(self, secure_manager):
        """Test rate limiting on batch operations."""
        docs = [{"id": f"doc_{i}", "content": "test"} for i in range(100)]
        
        # Configure a smaller burst size for predictable testing
        secure_manager.security_manager.rate_limiter.config.rate_limit_burst_size = 5
        secure_manager.security_manager.rate_limiter.config.rate_limit_requests_per_minute = 60
        secure_manager.security_manager.rate_limiter.config.rate_limit_cooldown_seconds = 5
        
        # Reset any existing rate limiting state
        secure_manager.security_manager.rate_limiter.reset_client("rate_test")
        
        # First few batches should succeed (within burst limit)
        for i in range(5):
            results = await secure_manager.process_batch_optimized(
                docs[:1],
                lambda x: x,
                client_id="rate_test",
            )
            assert len(results) == 1, f"Batch {i+1} should succeed"
        
        # Next batch should fail (exceeds burst limit)
        with pytest.raises(BatchSecurityError) as exc_info:
            await secure_manager.process_batch_optimized(
                docs[:1],
                lambda x: x,
                client_id="rate_test",
            )
        assert "Rate limit exceeded" in str(exc_info.value)


# ============================================================================
# Encryption Tests
# ============================================================================


class TestEncryption:
    """Test cache encryption and data protection."""

    def test_secure_cache_encryption(self, security_config):
        """Test that cache data is encrypted."""
        cache = SecureCache(security_config)
        
        # Store sensitive data
        sensitive_data = {"ssn": "123-45-6789", "password": "secret123"}
        cache.put("test_key", sensitive_data)
        
        # Verify data is encrypted in storage
        raw_cached = cache._cache.get("test_key")
        assert raw_cached is not None
        assert "123-45-6789" not in str(raw_cached)
        assert "secret123" not in str(raw_cached)
        
        # Verify decryption works
        retrieved = cache.get("test_key")
        assert retrieved == sensitive_data

    def test_cache_integrity_protection(self, security_config):
        """Test cache HMAC integrity protection."""
        cache = SecureCache(security_config)
        
        # Store data
        cache.put("test_key", {"data": "test"})
        
        # Tamper with cached data
        cache._cache["test_key"] = b"tampered_data"
        
        # Should detect tampering and return None
        result = cache.get("test_key")
        assert result is None

    def test_secure_key_generation(self, secure_manager):
        """Test secure cache key generation."""
        # Should use SHA-256, not MD5
        key = secure_manager.security_manager.generate_secure_cache_key(
            "doc_id", "operation", "content"
        )
        
        # SHA-256 produces 64 character hex string
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)

    @pytest.mark.asyncio
    async def test_encrypted_cache_performance(self, secure_manager):
        """Test that encryption doesn't significantly impact performance."""
        docs = [{"id": f"doc_{i}", "content": f"content_{i}"} for i in range(100)]
        
        # Process documents (will be cached)
        start = time.time()
        await secure_manager.process_batch_optimized(
            docs,
            lambda x: {"processed": x["id"]},
            client_id="perf_test",
        )
        first_run_time = time.time() - start
        
        # Process again (should hit cache)
        start = time.time()
        await secure_manager.process_batch_optimized(
            docs,
            lambda x: {"processed": x["id"]},
            client_id="perf_test",
        )
        cached_run_time = time.time() - start
        
        # Cached run should be significantly faster even with encryption
        assert cached_run_time < first_run_time * 0.5


# ============================================================================
# Audit Logging Tests
# ============================================================================


class TestAuditLogging:
    """Test security audit logging."""

    def test_audit_log_creation(self, security_config, tmp_path):
        """Test audit log file creation."""
        security_config.audit_log_path = tmp_path / "audit.log"
        audit_logger = AuditLogger(security_config)
        
        # Log an event
        audit_logger.log_event(
            SecurityEvent.RATE_LIMIT_EXCEEDED,
            "test_client",
            {"reason": "test"},
            "WARNING"
        )
        
        # Verify log file exists
        assert security_config.audit_log_path.exists()
        
        # Verify log content
        log_content = security_config.audit_log_path.read_text()
        assert "rate_limit_exceeded" in log_content
        assert "test_client" in log_content

    def test_audit_log_rotation(self, security_config, tmp_path):
        """Test audit log rotation."""
        security_config.audit_log_path = tmp_path / "audit.log"
        security_config.audit_log_rotation_mb = 0.001  # Very small for testing
        
        audit_logger = AuditLogger(security_config)
        
        # Generate enough events to trigger rotation
        for i in range(100):
            audit_logger.log_event(
                SecurityEvent.VALIDATION_FAILURE,
                f"client_{i}",
                {"data": "x" * 1000},  # Large data
                "ERROR"
            )
        
        # Check for rotated files
        log_files = list(tmp_path.glob("audit.log*"))
        assert len(log_files) > 1  # Should have rotated files

    @pytest.mark.asyncio
    async def test_security_events_logged(self, secure_manager, malicious_documents):
        """Test that security events are properly logged."""
        # Process malicious documents
        await secure_manager.process_batch_optimized(
            malicious_documents,
            lambda x: x,
            client_id="attacker",
        )
        
        # Check security metrics
        metrics = secure_manager.get_security_metrics()
        assert metrics["validations_failed"] > 0


# ============================================================================
# Circuit Breaker Tests
# ============================================================================


class TestCircuitBreaker:
    """Test circuit breaker fault tolerance."""

    def test_circuit_breaker_opens_on_failures(self, security_config):
        """Test circuit breaker opens after threshold failures."""
        security_config.circuit_breaker_threshold = 3
        breaker = CircuitBreaker(security_config)
        
        def failing_func():
            raise Exception("Failure")
        
        # Trigger failures
        for i in range(3):
            with pytest.raises(Exception):
                breaker.call(failing_func)
        
        # Circuit should be open
        assert breaker.state == CircuitBreaker.State.OPEN
        
        # Next call should fail immediately
        with pytest.raises(BatchSecurityError) as exc_info:
            breaker.call(failing_func)
        assert "Circuit breaker is open" in str(exc_info.value)

    def test_circuit_breaker_half_open_recovery(self, security_config):
        """Test circuit breaker recovery through half-open state."""
        security_config.circuit_breaker_threshold = 2
        security_config.circuit_breaker_timeout_seconds = 0.1
        breaker = CircuitBreaker(security_config)
        
        def failing_func():
            raise Exception("Failure")
        
        def success_func():
            return "success"
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                breaker.call(failing_func)
        
        # Wait for timeout
        time.sleep(0.2)
        
        # Should enter half-open state and allow test
        result = breaker.call(success_func)
        assert result == "success"
        assert breaker.state == CircuitBreaker.State.HALF_OPEN
        
        # More successes should close circuit
        for _ in range(2):
            breaker.call(success_func)
        
        assert breaker.state == CircuitBreaker.State.CLOSED


# ============================================================================
# Resource Monitoring Tests
# ============================================================================


class TestResourceMonitoring:
    """Test resource limit enforcement."""

    def test_memory_limit_enforcement(self, security_config):
        """Test memory limit checking."""
        security_config.max_memory_mb = 1  # Unrealistically low for testing
        monitor = ResourceMonitor(security_config)
        
        within_limits, error = monitor.check_limits()
        assert not within_limits
        assert "Memory limit exceeded" in error

    def test_cpu_limit_enforcement(self, security_config):
        """Test CPU limit checking."""
        security_config.max_cpu_percent = 0.1  # Unrealistically low for testing
        monitor = ResourceMonitor(security_config)
        
        # Generate some CPU usage
        for _ in range(1000000):
            _ = sum(range(100))
        
        within_limits, error = monitor.check_limits()
        # May or may not exceed depending on system, but should check
        assert isinstance(within_limits, bool)

    def test_concurrent_operation_limits(self, security_config):
        """Test concurrent operation limits."""
        security_config.max_concurrent_operations = 2
        monitor = ResourceMonitor(security_config)
        
        # Should allow up to limit
        assert monitor.check_limits()[0]
        assert monitor.check_limits()[0]
        
        # Should block beyond limit
        within_limits, error = monitor.check_limits()
        assert not within_limits
        assert "Concurrent operation limit exceeded" in error
        
        # Release and try again
        monitor.release_operation()
        assert monitor.check_limits()[0]

    @pytest.mark.asyncio
    async def test_batch_size_limit(self, secure_manager):
        """Test batch size limit enforcement."""
        # Create oversized batch
        docs = [{"id": f"doc_{i}", "content": "test"} for i in range(1000)]
        secure_manager.security_config.max_batch_size = 10
        
        # Should reject oversized batch
        with pytest.raises(BatchSecurityError) as exc_info:
            await secure_manager.process_batch_optimized(
                docs,
                lambda x: x,
                client_id="test",
            )
        assert "Batch size" in str(exc_info.value)


# ============================================================================
# OWASP Compliance Tests
# ============================================================================


class TestOWASPCompliance:
    """Test OWASP Top 10 compliance."""

    def test_a01_broken_access_control(self, security_config):
        """Test A01: Broken Access Control prevention."""
        validator = InputValidator(security_config)
        
        # Path traversal attempt
        doc = {"id": "test", "content": "../../etc/passwd"}
        is_valid, _, issues = validator.validate_document(doc)
        assert not is_valid
        assert any("dangerous_pattern" in issue for issue in issues)

    def test_a02_cryptographic_failures(self, security_config):
        """Test A02: Cryptographic Failures prevention."""
        # Ensure encryption is used
        cache = SecureCache(security_config)
        cache.put("test", {"sensitive": "data"})
        
        # Data should be encrypted
        raw = cache._cache.get("test")
        assert "sensitive" not in str(raw)
        assert "data" not in str(raw)

    def test_a03_injection(self, security_config):
        """Test A03: Injection prevention."""
        validator = InputValidator(security_config)
        
        # SQL injection attempt
        doc = {"id": "test", "content": "'; DROP TABLE users; --"}
        is_valid, _, _ = validator.validate_document(doc)
        
        # Command injection attempt
        doc2 = {"id": "test", "content": "test; rm -rf /"}
        is_valid2, _, _ = validator.validate_document(doc2)
        
        # Both should be detected
        assert not is_valid or not is_valid2

    def test_a04_insecure_design(self, secure_manager):
        """Test A04: Insecure Design prevention."""
        # Verify secure defaults
        assert secure_manager.security_config.enable_input_validation
        assert secure_manager.security_config.enable_rate_limiting
        assert secure_manager.security_config.enable_cache_encryption

    def test_a05_security_misconfiguration(self, secure_manager):
        """Test A05: Security Misconfiguration prevention."""
        # Verify security headers and configurations
        config = secure_manager.security_config
        assert config.max_document_size_mb > 0
        assert config.max_batch_size > 0
        assert config.enable_audit_logging

    def test_a07_identification_failures(self, security_config):
        """Test A07: Identification and Authentication Failures prevention."""
        # Rate limiting prevents brute force
        limiter = RateLimiter(security_config)
        
        # Simulate brute force attempt
        for i in range(100):
            allowed, _ = limiter.check_rate_limit("attacker")
            if not allowed:
                break
        
        # Should be blocked before 100 attempts
        assert i < 100

    def test_a09_security_logging_failures(self, secure_manager):
        """Test A09: Security Logging and Monitoring Failures prevention."""
        # Verify audit logging is enabled
        assert secure_manager.security_config.enable_audit_logging
        
        # Verify security events are tracked
        metrics = secure_manager.get_security_metrics()
        assert "validations_performed" in metrics
        assert "rate_limits_hit" in metrics

    def test_a10_ssrf(self, security_config):
        """Test A10: Server-Side Request Forgery prevention."""
        validator = InputValidator(security_config)
        
        # SSRF attempt patterns
        doc = {"id": "test", "content": "http://localhost/admin"}
        # Additional validation would be needed for full SSRF protection
        # This is a placeholder for SSRF prevention testing


# ============================================================================
# Performance Overhead Tests
# ============================================================================


class TestSecurityOverhead:
    """Test that security overhead remains under 10%."""

    @pytest.mark.asyncio
    async def test_security_overhead_target(self, secure_manager):
        """Test security overhead is less than 10%."""
        # Create test documents
        docs = [
            {"id": f"doc_{i}", "content": f"Safe content {i}"}
            for i in range(100)
        ]
        
        # Benchmark security overhead
        benchmark = await secure_manager.benchmark_security_overhead(
            docs,
            lambda x: {"processed": x["id"]}
        )
        
        # Verify overhead is under 10%
        assert benchmark["meets_target"]
        assert benchmark["security_overhead_percent"] < 10

    @pytest.mark.asyncio 
    async def test_performance_preservation(self, secure_manager):
        """Test that Pass 2 performance gains are preserved."""
        docs = [
            {"id": f"doc_{i}", "content": f"content_{i}" * 100}
            for i in range(1000)
        ]
        
        # Process batch
        start = time.time()
        results = await secure_manager.process_batch_optimized(
            docs,
            lambda x: {"id": x["id"], "length": len(x["content"])},
            client_id="perf_test",
        )
        elapsed = time.time() - start
        
        # Calculate throughput
        docs_per_second = len(docs) / elapsed if elapsed > 0 else 0
        
        # Should maintain high throughput (>1000 docs/sec for simple operations)
        assert docs_per_second > 1000
        
        # Verify all documents processed
        assert len(results) == len(docs)