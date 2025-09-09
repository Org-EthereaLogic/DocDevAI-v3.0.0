"""
Security-Focused Unit Tests for M008 LLM Adapter - Pass 3
DevDocAI v3.0.0 - Security Hardening Tests for 95% coverage
Tests rate limiting, request signing, audit logging, and enhanced PII detection
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta
import json
import time
import hmac
import hashlib
import secrets
import threading
import logging
from io import StringIO

import pytest

from devdocai.intelligence.llm_adapter import (
    LLMAdapter,
    RateLimiter,
    RequestSigner,
    AuditLogger,
    SecurityEvent,
    RateLimitExceededError,
    RequestSignatureError,
    LLMResponse,
    ProviderError,
    # Import PII patterns for testing
    _EMAIL_PATTERN,
    _PHONE_PATTERN,
    _SSN_PATTERN,
    _API_KEY_PATTERN,
    _CREDIT_CARD_PATTERN,
    _IP_ADDRESS_PATTERN,
    _PASSPORT_PATTERN,
    _AWS_KEY_PATTERN,
    _GITHUB_TOKEN_PATTERN,
)
from devdocai.core.config import ConfigurationManager


class TestRateLimiter(unittest.TestCase):
    """Test token bucket rate limiter for API throttling."""

    def setUp(self):
        """Set up test fixtures."""
        self.limiter = RateLimiter(tokens_per_minute=60, burst_capacity=10)

    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization with token bucket."""
        self.assertEqual(self.limiter.capacity, 10)
        self.assertEqual(self.limiter.tokens, 10)
        self.assertAlmostEqual(self.limiter.fill_rate, 1.0, places=2)  # 60/60

    def test_token_acquisition(self):
        """Test acquiring tokens for requests."""
        # Should succeed with initial tokens
        self.assertTrue(self.limiter.acquire(1))
        self.assertEqual(self.limiter.tokens, 9)

        # Should succeed with multiple tokens
        self.assertTrue(self.limiter.acquire(5))
        self.assertEqual(self.limiter.tokens, 4)

        # Should fail when not enough tokens
        self.assertFalse(self.limiter.acquire(5))
        self.assertEqual(self.limiter.tokens, 4)  # Unchanged

    def test_token_refill(self):
        """Test token refill over time."""
        # Use all tokens
        self.limiter.tokens = 0

        # Wait for refill (simulate 2 seconds passing)
        time.sleep(2.1)  # Allow some buffer for timing

        # Try to acquire - should have refilled ~2 tokens
        self.assertTrue(self.limiter.acquire(1))

    def test_wait_time_calculation(self):
        """Test calculation of wait time for next token."""
        # Use all tokens
        self.limiter.tokens = 0

        # Should need to wait ~1 second for 1 token at 60/min rate
        wait_time = self.limiter.get_wait_time()
        self.assertAlmostEqual(wait_time, 1.0, delta=0.1)

        # With tokens available, wait time should be 0
        self.limiter.tokens = 5
        wait_time = self.limiter.get_wait_time()
        self.assertEqual(wait_time, 0.0)

    def test_burst_capacity(self):
        """Test burst capacity limits."""
        # Should not exceed capacity even with long wait
        self.limiter.tokens = 0
        self.limiter.last_update = time.time() - 100  # 100 seconds ago

        # Acquire to trigger refill
        self.limiter.acquire(1)

        # Should be capped at capacity
        self.assertLessEqual(self.limiter.tokens, self.limiter.capacity)

    def test_thread_safety(self):
        """Test thread-safe token acquisition."""
        successful_acquisitions = []

        def acquire_tokens():
            if self.limiter.acquire(1):
                successful_acquisitions.append(1)

        # Create multiple threads trying to acquire tokens
        threads = []
        for _ in range(15):  # More than capacity
            thread = threading.Thread(target=acquire_tokens)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Should only succeed up to capacity
        self.assertLessEqual(len(successful_acquisitions), self.limiter.capacity)


class TestRequestSigner(unittest.TestCase):
    """Test HMAC-SHA256 request signing for integrity."""

    def setUp(self):
        """Set up test fixtures."""
        self.secret_key = "test-secret-key-123"
        self.signer = RequestSigner(self.secret_key)

    def test_request_signing(self):
        """Test signing requests with HMAC-SHA256."""
        provider = "openai"
        prompt = "Generate a summary"

        signature_data = self.signer.sign_request(provider, prompt)

        # Check signature data structure
        self.assertIn("signature", signature_data)
        self.assertIn("timestamp", signature_data)
        self.assertIn("nonce", signature_data)
        self.assertIn("provider", signature_data)

        # Verify signature format (64 hex chars for SHA256)
        self.assertEqual(len(signature_data["signature"]), 64)

        # Verify nonce is unique
        nonce1 = signature_data["nonce"]
        signature_data2 = self.signer.sign_request(provider, prompt)
        nonce2 = signature_data2["nonce"]
        self.assertNotEqual(nonce1, nonce2)

    def test_signature_verification(self):
        """Test signature verification and integrity."""
        provider = "claude"
        prompt = "Test prompt"

        # Sign request
        signature_data = self.signer.sign_request(provider, prompt)

        # Should verify correctly
        self.assertTrue(self.signer.verify_signature(provider, prompt, signature_data))

        # Should fail with wrong prompt
        self.assertFalse(self.signer.verify_signature(provider, "Different prompt", signature_data))

        # Should fail with wrong provider
        self.assertFalse(self.signer.verify_signature("openai", prompt, signature_data))

        # Should fail with tampered signature
        tampered_data = signature_data.copy()
        tampered_data["signature"] = "a" * 64
        self.assertFalse(self.signer.verify_signature(provider, prompt, tampered_data))

    def test_replay_attack_prevention(self):
        """Test prevention of replay attacks using nonce and timestamp."""
        provider = "gemini"
        prompt = "Generate code"

        # Sign request
        signature_data = self.signer.sign_request(provider, prompt)

        # First verification should succeed
        self.assertTrue(self.signer.verify_signature(provider, prompt, signature_data))

        # Replay with same nonce should fail
        self.assertFalse(self.signer.verify_signature(provider, prompt, signature_data))

    def test_timestamp_validation(self):
        """Test timestamp validation within replay window."""
        provider = "local"
        prompt = "Test"

        # Create signature with old timestamp
        old_timestamp = datetime.now() - timedelta(minutes=10)
        signature_data = self.signer.sign_request(provider, prompt, timestamp=old_timestamp)

        # Should fail due to old timestamp (outside 5-minute window)
        self.assertFalse(self.signer.verify_signature(provider, prompt, signature_data))

        # Create signature with recent timestamp
        recent_timestamp = datetime.now() - timedelta(minutes=2)
        signature_data = self.signer.sign_request(provider, prompt, timestamp=recent_timestamp)

        # Should succeed within window
        self.assertTrue(self.signer.verify_signature(provider, prompt, signature_data))

    def test_nonce_cache_limit(self):
        """Test nonce cache doesn't grow unbounded."""
        provider = "test"
        prompt = "test"

        # Generate many signatures
        for i in range(1500):  # More than maxlen=1000
            sig = self.signer.sign_request(provider, f"prompt{i}")
            self.signer.verify_signature(provider, f"prompt{i}", sig)

        # Nonce cache should be limited
        self.assertLessEqual(len(self.signer.seen_nonces), 1000)


class TestAuditLogger(unittest.TestCase):
    """Test structured audit logging for security events."""

    def setUp(self):
        """Set up test fixtures."""
        self.logger = AuditLogger("test.audit")

        # Capture log output
        self.log_capture = StringIO()
        handler = logging.StreamHandler(self.log_capture)
        handler.setFormatter(logging.Formatter("%(message)s"))
        self.logger.logger.handlers = [handler]
        self.logger.logger.setLevel(logging.INFO)

    def test_request_id_generation(self):
        """Test unique request ID generation."""
        id1 = self.logger.generate_request_id()
        id2 = self.logger.generate_request_id()

        # Should be unique
        self.assertNotEqual(id1, id2)

        # Should have expected format
        self.assertTrue(id1.startswith("req_"))
        self.assertIn("_", id1)

        # Counter should increment
        self.assertEqual(self.logger.request_counter, 2)

    def test_event_logging(self):
        """Test logging of security events."""
        request_id = "test_req_123"
        provider = "openai"

        # Log an API call event
        self.logger.log_event(
            SecurityEvent.API_CALL, request_id, provider, {"action": "start", "tokens": 100}
        )

        # Check logged output
        log_output = self.log_capture.getvalue()
        self.assertIn(request_id, log_output)
        self.assertIn(provider, log_output)
        self.assertIn("api_call", log_output)

        # Parse JSON log entry
        log_data = json.loads(log_output.strip())
        self.assertEqual(log_data["event_type"], "api_call")
        self.assertEqual(log_data["request_id"], request_id)
        self.assertEqual(log_data["provider"], provider)

    def test_pii_sanitization_in_logs(self):
        """Test PII is sanitized in log entries."""
        request_id = "test_req_456"
        provider = "claude"

        # Log with PII in details
        details = {
            "prompt": "Email me at john@example.com or call 555-123-4567",
            "api_key": "sk-abc123def456",
        }

        self.logger.log_event(
            SecurityEvent.API_CALL, request_id, provider, details, sanitize_pii=True
        )

        # Check PII is sanitized
        log_output = self.log_capture.getvalue()
        self.assertNotIn("john@example.com", log_output)
        self.assertNotIn("555-123-4567", log_output)
        self.assertNotIn("sk-abc123def456", log_output)
        self.assertIn("[EMAIL]", log_output)
        self.assertIn("[PHONE]", log_output)

    def test_event_severity_levels(self):
        """Test different severity levels for events."""
        # Clear previous logs
        self.log_capture.truncate(0)
        self.log_capture.seek(0)

        # Set to capture all levels
        self.logger.logger.setLevel(logging.DEBUG)

        # Test ERROR level
        with patch.object(self.logger.logger, "error") as mock_error:
            self.logger.log_event(
                SecurityEvent.SIGNATURE_VALIDATION_FAILED,
                "req_001",
                "openai",
                {"error": "Invalid signature"},
            )
            mock_error.assert_called_once()

        # Test WARNING level
        with patch.object(self.logger.logger, "warning") as mock_warning:
            self.logger.log_event(
                SecurityEvent.RATE_LIMIT_EXCEEDED, "req_002", "claude", {"wait_time": 5.0}
            )
            mock_warning.assert_called_once()

        # Test INFO level
        with patch.object(self.logger.logger, "info") as mock_info:
            self.logger.log_event(
                SecurityEvent.CACHE_HIT, "req_003", "local", {"tokens_saved": 100}
            )
            mock_info.assert_called_once()


class TestLLMAdapterSecurity(unittest.TestCase):
    """Test LLMAdapter security features integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = Mock(spec=ConfigurationManager)
        self.mock_config.get_api_key.return_value = "test-api-key"
        self.adapter = LLMAdapter(self.mock_config)

    def test_rate_limiting_integration(self):
        """Test rate limiting prevents excessive API calls."""
        # Configure strict rate limit for testing
        self.adapter.configure_rate_limits("openai", tokens_per_minute=1, burst_capacity=1)

        # Mock the provider to avoid actual API calls
        mock_provider = Mock()
        mock_provider.generate.return_value = LLMResponse(
            content="Test response", provider="openai", tokens_used=100, cost=0.01, latency=0.5
        )
        self.adapter.providers["openai"] = mock_provider

        # First call should succeed
        response = self.adapter.generate("Test prompt", provider="openai", use_cache=False)
        self.assertIsNotNone(response)

        # Second immediate call should fail with rate limit
        with self.assertRaises(RateLimitExceededError):
            self.adapter.generate("Test prompt 2", provider="openai", use_cache=False)

    def test_request_signing_integration(self):
        """Test request signing and verification."""
        prompt = "Generate documentation"
        provider = "claude"

        # Sign a request
        signature_data = self.adapter.sign_request(provider, prompt)
        self.assertIsNotNone(signature_data)

        # Mock provider
        mock_provider = Mock()
        mock_provider.generate.return_value = LLMResponse(
            content="Signed response", provider=provider, tokens_used=50, cost=0.005, latency=0.3
        )
        self.adapter.providers[provider] = mock_provider

        # Generate with valid signature should succeed
        response = self.adapter.generate(
            prompt,
            provider=provider,
            verify_signature=True,
            signature_data=signature_data,
            use_cache=False,
        )
        self.assertIsNotNone(response)

        # Generate with invalid signature should fail
        invalid_signature = signature_data.copy()
        invalid_signature["signature"] = "invalid"

        with self.assertRaises(RequestSignatureError):
            self.adapter.generate(
                prompt,
                provider=provider,
                verify_signature=True,
                signature_data=invalid_signature,
                use_cache=False,
            )

        # Verify signature request without data should fail
        with self.assertRaises(RequestSignatureError):
            self.adapter.generate(
                prompt,
                provider=provider,
                verify_signature=True,
                signature_data=None,
                use_cache=False,
            )

    def test_audit_logging_integration(self):
        """Test audit logging of API calls and security events."""
        # Mock provider
        mock_provider = Mock()
        mock_provider.generate.return_value = LLMResponse(
            content="Test", provider="gemini", tokens_used=10, cost=0.001, latency=0.1
        )
        self.adapter.providers["gemini"] = mock_provider

        # Capture audit logs
        with patch.object(self.adapter.audit_logger, "log_event") as mock_log:
            # Generate response
            response = self.adapter.generate("Test", provider="gemini", use_cache=False)

            # Should log API call start and success
            calls = mock_log.call_args_list
            event_types = [call[0][0] for call in calls]
            self.assertIn(SecurityEvent.API_CALL, event_types)

            # Check for proper request ID
            request_ids = [call[0][1] for call in calls]
            self.assertTrue(all(rid.startswith("req_") for rid in request_ids))

    def test_enhanced_pii_detection(self):
        """Test enhanced PII detection patterns."""
        test_cases = {
            "email": "Contact user@example.com for details",
            "phone": "Call me at 555-123-4567",
            "ssn": "SSN: 123-45-6789",
            "credit_card": "Card: 4111 1111 1111 1111",
            "ip_address": "Server at 192.168.1.1",
            "aws_key": "AWS Key: AKIAIOSFODNN7EXAMPLE",
            "github_token": "Token: ghp_1234567890abcdef1234567890abcdef1234",
        }

        for pii_type, text in test_cases.items():
            detected = self.adapter.detect_pii(text)
            self.assertIn(
                pii_type.replace("_", "") + "s", detected.keys(), f"Failed to detect {pii_type}"
            )

    def test_security_metrics(self):
        """Test retrieval of security metrics."""
        metrics = self.adapter.get_security_metrics()

        # Check metric structure
        self.assertIn("rate_limits", metrics)
        self.assertIn("audit_stats", metrics)
        self.assertIn("pii_patterns", metrics)
        self.assertIn("request_signing", metrics)

        # Check rate limits for each provider
        for provider in ["openai", "claude", "gemini", "local"]:
            self.assertIn(provider, metrics["rate_limits"])
            provider_limits = metrics["rate_limits"][provider]
            self.assertIn("tokens_available", provider_limits)
            self.assertIn("capacity", provider_limits)

        # Check audit stats
        self.assertIn("total_requests", metrics["audit_stats"])
        self.assertIsInstance(metrics["audit_stats"]["total_requests"], int)

    def test_rate_limit_configuration(self):
        """Test dynamic rate limit configuration."""
        # Configure custom limits
        self.adapter.configure_rate_limits("openai", tokens_per_minute=120, burst_capacity=20)

        # Check configuration took effect
        status = self.adapter.get_rate_limit_status("openai")
        self.assertEqual(status["capacity"], 20)
        self.assertAlmostEqual(status["fill_rate_per_second"], 2.0, places=1)

        # Test unknown provider
        status = self.adapter.get_rate_limit_status("unknown_provider")
        self.assertIn("error", status)

    def test_audit_level_configuration(self):
        """Test setting audit logging levels."""
        # Set to WARNING level
        self.adapter.set_audit_level("WARNING")
        self.assertEqual(self.adapter.audit_logger.logger.level, logging.WARNING)

        # Set to ERROR level
        self.adapter.set_audit_level("ERROR")
        self.assertEqual(self.adapter.audit_logger.logger.level, logging.ERROR)

        # Invalid level should raise error
        with self.assertRaises(ValueError):
            self.adapter.set_audit_level("INVALID")

    def test_pii_detection_without_sanitization(self):
        """Test PII detection returns actual values."""
        text = "Email john@example.com or call 555-123-4567 with API key sk-test123"

        detected = self.adapter.detect_pii(text)

        # Should detect and return actual values
        self.assertEqual(detected["emails"], ["john@example.com"])
        self.assertEqual(detected["phones"], ["555-123-4567"])
        self.assertTrue(any("sk-test123" in key for key in detected.get("api_keys", [])))

    def test_concurrent_rate_limiting(self):
        """Test rate limiting under concurrent access."""
        # Configure rate limit
        self.adapter.configure_rate_limits("local", tokens_per_minute=6, burst_capacity=2)

        # Mock provider
        mock_provider = Mock()
        mock_provider.generate.return_value = LLMResponse(
            content="Test", provider="local", tokens_used=10, cost=0.0, latency=0.01
        )
        self.adapter.providers["local"] = mock_provider

        results = []
        errors = []

        def make_request(i):
            try:
                response = self.adapter.generate(f"Test {i}", provider="local", use_cache=False)
                results.append(response)
            except RateLimitExceededError as e:
                errors.append(e)

        # Make concurrent requests
        threads = []
        for i in range(5):  # More than burst capacity
            thread = threading.Thread(target=make_request, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should have some successes and some rate limit errors
        self.assertGreater(len(results), 0)
        self.assertGreater(len(errors), 0)
        self.assertLessEqual(len(results), 2)  # Burst capacity

    def test_security_event_logging(self):
        """Test logging of various security events."""
        # Test PII detection logging
        with patch.object(self.adapter.audit_logger, "log_event") as mock_log:
            self.adapter.detect_pii("Email: test@example.com")

            # Should log PII detection event
            mock_log.assert_called()
            call_args = mock_log.call_args[0]
            self.assertEqual(call_args[0], SecurityEvent.PII_DETECTED)

    def test_fallback_with_rate_limiting(self):
        """Test fallback behavior when rate limited."""
        # Configure strict rate limit for primary provider
        self.adapter.configure_rate_limits("openai", tokens_per_minute=1, burst_capacity=1)

        # Mock providers
        for provider_name in ["openai", "claude", "local"]:
            mock_provider = Mock()
            mock_provider.generate.side_effect = (
                RateLimitExceededError("Rate limited") if provider_name == "openai" else None
            )
            if provider_name != "openai":
                mock_provider.generate.return_value = LLMResponse(
                    content=f"{provider_name} response",
                    provider=provider_name,
                    tokens_used=10,
                    cost=0.001 if provider_name != "local" else 0.0,
                    latency=0.1,
                )
            self.adapter.providers[provider_name] = mock_provider

        # Use all tokens for openai
        limiter = self.adapter.rate_limiters["openai"]
        limiter.tokens = 0

        # Should fallback to next provider
        response = self.adapter.generate("Test", provider="openai", use_cache=False)
        self.assertIn(response.provider, ["claude", "local"])


class TestPIIPatterns(unittest.TestCase):
    """Test enhanced PII detection patterns."""

    def test_email_pattern(self):
        """Test email detection pattern."""
        test_cases = [
            ("user@example.com", True),
            ("john.doe+tag@company.co.uk", True),
            ("invalid.email", False),
            ("@example.com", False),
        ]

        for text, should_match in test_cases:
            matches = _EMAIL_PATTERN.findall(text)
            if should_match:
                self.assertTrue(matches, f"Failed to match: {text}")
            else:
                self.assertFalse(matches, f"Should not match: {text}")

    def test_phone_pattern(self):
        """Test phone number detection pattern."""
        test_cases = [
            ("555-123-4567", True),
            ("555.123.4567", True),
            ("5551234567", True),
            ("123-45", False),
            ("abc-def-ghij", False),
        ]

        for text, should_match in test_cases:
            matches = _PHONE_PATTERN.findall(text)
            if should_match:
                self.assertTrue(matches, f"Failed to match: {text}")
            else:
                self.assertFalse(matches, f"Should not match: {text}")

    def test_ssn_pattern(self):
        """Test SSN detection pattern."""
        test_cases = [
            ("123-45-6789", True),
            ("000-00-0000", True),
            ("123-456789", False),
            ("12-345-6789", False),
        ]

        for text, should_match in test_cases:
            matches = _SSN_PATTERN.findall(text)
            if should_match:
                self.assertTrue(matches, f"Failed to match: {text}")
            else:
                self.assertFalse(matches, f"Should not match: {text}")

    def test_api_key_patterns(self):
        """Test API key detection patterns."""
        # Standard API keys
        test_cases = [
            ("sk-proj-abc123def456", True),
            ("api_key: secret123", True),
            ("API-KEY: token456", True),
            ("regular-text", False),
        ]

        for text, should_match in test_cases:
            matches = _API_KEY_PATTERN.findall(text)
            if should_match:
                self.assertTrue(matches, f"Failed to match: {text}")

        # AWS keys
        aws_key = "AKIAIOSFODNN7EXAMPLE"
        matches = _AWS_KEY_PATTERN.findall(aws_key)
        self.assertTrue(matches)

        # GitHub tokens
        github_token = "ghp_1234567890abcdef1234567890abcdef1234"
        matches = _GITHUB_TOKEN_PATTERN.findall(github_token)
        self.assertTrue(matches)

    def test_credit_card_pattern(self):
        """Test credit card detection pattern."""
        test_cases = [
            ("4111 1111 1111 1111", True),
            ("4111-1111-1111-1111", True),
            ("4111111111111111", True),
            ("1234 5678", False),
            ("not-a-card-number", False),
        ]

        for text, should_match in test_cases:
            matches = _CREDIT_CARD_PATTERN.findall(text)
            if should_match:
                self.assertTrue(matches, f"Failed to match: {text}")
            else:
                self.assertFalse(matches, f"Should not match: {text}")

    def test_ip_address_pattern(self):
        """Test IP address detection pattern."""
        test_cases = [
            ("192.168.1.1", True),
            ("10.0.0.1", True),
            ("255.255.255.255", True),
            ("256.1.1.1", True),  # Pattern doesn't validate ranges
            ("192.168", False),
            ("not.an.ip.address", False),
        ]

        for text, should_match in test_cases:
            matches = _IP_ADDRESS_PATTERN.findall(text)
            if should_match:
                self.assertTrue(matches, f"Failed to match: {text}")
            else:
                self.assertFalse(matches, f"Should not match: {text}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=devdocai.intelligence.llm_adapter", "--cov-report=html"])
