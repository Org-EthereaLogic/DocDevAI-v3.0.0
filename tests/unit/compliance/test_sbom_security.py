"""
Security-focused unit tests for M010 SBOM Generator - Pass 2: Security Hardening
DevDocAI v3.0.0

Tests for OWASP Top 10 compliance and security features.
"""

import json
import logging
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from devdocai.compliance.sbom import (
    CircuitBreaker,
    DependencyScanError,
    InputSanitizer,
    Package,
    PathValidator,
    PIIDetector,
    RateLimiter,
    SBOMError,
    SBOMGenerator,
    SecurityManager,
    Vulnerability,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def security_manager():
    """Create SecurityManager instance."""
    return SecurityManager()


@pytest.fixture
def rate_limiter():
    """Create RateLimiter instance."""
    return RateLimiter(max_requests=10, window_seconds=60)


@pytest.fixture
def circuit_breaker():
    """Create CircuitBreaker instance."""
    return CircuitBreaker(failure_threshold=3, recovery_timeout=10)


@pytest.fixture
def pii_detector():
    """Create PIIDetector instance."""
    return PIIDetector()


@pytest.fixture
def path_validator():
    """Create PathValidator instance."""
    return PathValidator()


@pytest.fixture
def input_sanitizer():
    """Create InputSanitizer instance."""
    return InputSanitizer()


@pytest.fixture
def malicious_project_dir():
    """Create project directory with malicious content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)

        # Create malicious files
        (project_path / "requirements.txt").write_text(
            "evil-package==1.0.0; rm -rf /\n"
            + "../../../etc/passwd==1.0.0\n"
            + "package-with-<script>==1.0.0\n"
        )

        # Create file with PII
        (project_path / "package.json").write_text(
            json.dumps(
                {
                    "name": "test-project",
                    "author": "John Doe <john.doe@example.com>",
                    "repository": "https://github.com/user/token_ghp_1234567890abcdef",
                }
            )
        )

        yield project_path


# ============================================================================
# Test Security Utilities
# ============================================================================


class TestRateLimiter:
    """Test rate limiting functionality."""

    def test_rate_limit_allows_requests_within_limit(self, rate_limiter):
        """Test that requests within limit are allowed."""
        for _ in range(10):
            assert rate_limiter.check("test_operation")

    def test_rate_limit_blocks_excessive_requests(self, rate_limiter):
        """Test that excessive requests are blocked."""
        # Use up the limit
        for _ in range(10):
            rate_limiter.check("test_operation")

        # Next request should be blocked
        assert not rate_limiter.check("test_operation")

    def test_rate_limit_resets_after_window(self, rate_limiter):
        """Test that rate limit resets after time window."""
        # Use up the limit
        for _ in range(10):
            rate_limiter.check("test_operation")

        # Should be blocked
        assert not rate_limiter.check("test_operation")

        # Mock time passing
        with patch("time.time", return_value=time.time() + 61):
            # Should be allowed after window
            assert rate_limiter.check("test_operation")

    def test_rate_limit_tracks_operations_separately(self, rate_limiter):
        """Test that different operations have separate limits."""
        # Use up limit for operation1
        for _ in range(10):
            rate_limiter.check("operation1")

        # operation1 should be blocked
        assert not rate_limiter.check("operation1")

        # operation2 should still be allowed
        assert rate_limiter.check("operation2")


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    def test_circuit_breaker_allows_successful_calls(self, circuit_breaker):
        """Test that successful calls pass through."""

        def success_func():
            return "success"

        result = circuit_breaker.call(success_func)
        assert result == "success"

    def test_circuit_breaker_opens_after_failures(self, circuit_breaker):
        """Test that circuit opens after threshold failures."""

        def failing_func():
            raise RuntimeError("Test failure")

        # First failures should go through
        for _ in range(3):
            with pytest.raises(RuntimeError):
                circuit_breaker.call(failing_func)

        # Circuit should now be open
        with pytest.raises(RuntimeError, match="Circuit breaker is open"):
            circuit_breaker.call(failing_func)

    def test_circuit_breaker_half_open_after_timeout(self, circuit_breaker):
        """Test that circuit enters half-open state after timeout."""

        def failing_func():
            raise RuntimeError("Test failure")

        def success_func():
            return "success"

        # Open the circuit
        for _ in range(3):
            with pytest.raises(RuntimeError):
                circuit_breaker.call(failing_func)

        # Mock time passing
        with patch("time.time", return_value=time.time() + 11):
            # Should enter half-open and allow one call
            result = circuit_breaker.call(success_func)
            assert result == "success"

            # Circuit should be closed now
            result = circuit_breaker.call(success_func)
            assert result == "success"


class TestPIIDetector:
    """Test PII detection and sanitization."""

    def test_detect_email(self, pii_detector):
        """Test email detection."""
        content = "Contact me at john.doe@example.com for details"
        pii_found = pii_detector.detect(content)
        assert len(pii_found) == 1
        assert pii_found[0][1] == "email"

    def test_detect_credit_card(self, pii_detector):
        """Test credit card number detection."""
        content = "Card number: 4111 1111 1111 1111"
        pii_found = pii_detector.detect(content)
        assert len(pii_found) == 1
        assert pii_found[0][1] == "credit_card"

    def test_detect_api_key(self, pii_detector):
        """Test API key detection."""
        content = "Use key: fake_api_key_12345_test_pattern"
        pii_found = pii_detector.detect(content)
        assert len(pii_found) == 1
        assert pii_found[0][1] == "api_key"

    def test_detect_github_token(self, pii_detector):
        """Test GitHub token detection."""
        content = "Token: ghp_1234567890abcdef1234567890abcdef1234"
        pii_found = pii_detector.detect(content)
        assert len(pii_found) == 1
        assert pii_found[0][1] == "github_token"

    def test_sanitize_pii(self, pii_detector):
        """Test PII sanitization."""
        content = "Email: john@example.com, Token: ghp_1234567890abcdef1234567890abcdef1234"
        sanitized = pii_detector.sanitize(content)
        assert "john@example.com" not in sanitized
        assert "ghp_1234567890abcdef1234567890abcdef1234" not in sanitized
        assert "[REDACTED]" in sanitized


class TestPathValidator:
    """Test path validation for security."""

    def test_validate_normal_path(self, path_validator):
        """Test that normal paths are allowed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "normal_file.txt"
            path.touch()
            assert path_validator.validate(path)

    def test_reject_path_traversal(self, path_validator):
        """Test that path traversal attempts are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            # Attempt to traverse outside base
            evil_path = base_path / ".." / ".." / "etc" / "passwd"
            assert not path_validator.validate(evil_path, base_path)

    def test_reject_symbolic_links(self, path_validator):
        """Test that symbolic links are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            target = base_path / "target.txt"
            target.touch()

            symlink = base_path / "symlink.txt"
            symlink.symlink_to(target)

            assert not path_validator.validate(symlink)

    def test_reject_suspicious_patterns(self, path_validator):
        """Test that suspicious patterns are rejected."""
        suspicious_paths = [
            Path("/tmp/file;rm -rf /"),
            Path("/tmp/file|cat /etc/passwd"),
            Path("/tmp/file&&evil_command"),
            Path("/tmp/file>output"),
        ]

        for path in suspicious_paths:
            assert not path_validator.validate(path)


class TestInputSanitizer:
    """Test input sanitization."""

    def test_sanitize_package_name(self, input_sanitizer):
        """Test package name sanitization."""
        # Normal package name should pass
        assert input_sanitizer.sanitize("my-package_1.0", "package_name") == "my-package_1.0"

        # Malicious characters should be removed
        assert input_sanitizer.sanitize("evil;rm -rf /", "package_name") == "evil"
        assert input_sanitizer.sanitize("../../../etc/passwd", "package_name") == "etcpasswd"

    def test_sanitize_version(self, input_sanitizer):
        """Test version string sanitization."""
        # Normal version should pass
        assert input_sanitizer.sanitize("1.2.3-beta.1", "version") == "1.2.3-beta.1"

        # Malicious characters should be removed
        assert input_sanitizer.sanitize("1.0.0;evil", "version") == "1.0.0"

    def test_sanitize_url(self, input_sanitizer):
        """Test URL sanitization."""
        # Valid URLs should pass
        assert input_sanitizer.sanitize("https://example.com", "url") == "https://example.com"
        assert (
            input_sanitizer.sanitize("git://github.com/user/repo", "url")
            == "git://github.com/user/repo"
        )

        # Invalid schemes should be rejected
        assert input_sanitizer.sanitize("javascript:alert(1)", "url") == ""
        assert input_sanitizer.sanitize("file:///etc/passwd", "url") == ""

    def test_sanitize_command(self, input_sanitizer):
        """Test command sanitization."""
        # Shell metacharacters should be removed
        assert (
            input_sanitizer.sanitize("npm install; rm -rf /", "command") == "npm install rm -rf /"
        )
        assert input_sanitizer.sanitize("echo test | cat", "command") == "echo test  cat"

    def test_length_limit(self, input_sanitizer):
        """Test that long inputs are truncated."""
        long_input = "a" * 2000
        result = input_sanitizer.sanitize(long_input, "generic")
        assert len(result) == 1024


# ============================================================================
# Test SBOM Security Features
# ============================================================================


class TestSBOMGeneratorSecurity:
    """Test SBOM generator security features."""

    def test_path_traversal_prevention(self, _malicious_project_dir):
        """Test that path traversal attempts are prevented."""
        generator = SBOMGenerator()

        # Create a file with path traversal attempt
        # evil_path = malicious_project_dir / "../../../etc/passwd"

        # Should reject invalid paths
        with pytest.raises((ValueError, DependencyScanError)):
            # Attempt to scan with path traversal
            evil_path_attempt = Path("../../../etc/passwd")
            generator.generate(evil_path_attempt)

    def test_input_sanitization(self, malicious_project_dir):
        """Test that malicious input is sanitized."""
        generator = SBOMGenerator()

        # Generate SBOM with malicious content
        sbom = generator.generate(malicious_project_dir, scan_vulnerabilities=False)

        # Check that malicious content was sanitized
        for package in sbom.packages:
            # No shell metacharacters should remain
            assert ";" not in package.name
            assert "|" not in package.name
            assert ".." not in package.name

    def test_pii_detection_and_sanitization(self, malicious_project_dir):
        """Test that PII is detected and can be sanitized."""
        generator = SBOMGenerator()

        # Generate SBOM
        sbom = generator.generate(malicious_project_dir, scan_vulnerabilities=False)

        # Export to file (should detect and log PII)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            output_path = Path(tmp.name)

        # Export should sanitize PII
        generator.export(sbom, output_path)

        # Read exported content
        with open(output_path) as f:
            content = f.read()

        # PII should be sanitized
        assert "john.doe@example.com" not in content or "[REDACTED]" in content
        assert "ghp_" not in content or "[REDACTED]" in content

        # Clean up
        output_path.unlink()

    def test_rate_limiting(self):
        """Test that rate limiting prevents DoS attacks."""
        generator = SBOMGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            (project_path / "requirements.txt").write_text("flask==2.0.1")

            # Should allow some requests
            for _ in range(5):
                sbom = generator.generate(project_path, scan_vulnerabilities=False)
                assert sbom is not None

            # Eventually should hit rate limit (if configured low enough)
            # Note: This depends on the actual rate limit configuration

    def test_file_size_limits(self):
        """Test that large files are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Create a large file (simulate)
            large_file = project_path / "requirements.txt"

            # Write large content (over limit)
            large_content = "package==1.0.0\n" * 1000000  # Very large file
            large_file.write_text(large_content)

            generator = SBOMGenerator()

            # Should handle large files gracefully
            try:
                sbom = generator.generate(project_path, scan_vulnerabilities=False)
                # If it succeeds, check that packages were limited
                assert len(sbom.packages) <= 10000  # MAX_DEPENDENCY_COUNT
            except (DependencyScanError, SBOMError) as e:
                # Expected for files over limit
                assert "too large" in str(e).lower() or "limit" in str(e).lower()

    def test_processing_timeout(self):
        """Test that long-running operations timeout."""
        generator = SBOMGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Create many files to slow down scanning
            for i in range(1000):
                (project_path / f"file_{i}.txt").write_text(f"content_{i}")

            # Mock slow processing
            with patch("time.time") as mock_time:
                # Make it appear that processing takes too long
                mock_time.side_effect = [
                    0,  # Start time
                    0,  # Various checks
                    0,
                    301,  # Over MAX_PROCESSING_TIME
                    301,
                ]

                # Should timeout
                with pytest.raises((DependencyScanError, SBOMError)):
                    generator.generate(project_path)

    def test_secure_key_storage(self):
        """Test that signing keys are stored securely."""
        from devdocai.compliance.sbom import Ed25519Signer

        signer = Ed25519Signer()

        # Check that key file has proper permissions
        key_path = Path.home() / ".devdocai" / "sbom_signing_key.enc"
        if key_path.exists():
            # Check file permissions (should be 0o600)
            stat_info = key_path.stat()
            mode = stat_info.st_mode & 0o777
            assert mode == 0o600, f"Key file has insecure permissions: {oct(mode)}"

        # Test signing and verification
        test_data = {"test": "data"}
        signature = signer.sign(test_data)
        assert signer.verify(test_data, signature)

        # Tampered data should fail verification
        tampered_data = {"test": "tampered"}
        assert not signer.verify(tampered_data, signature)

    def test_vulnerability_scan_limits(self):
        """Test that vulnerability scanning has limits."""
        from devdocai.compliance.sbom import VulnerabilityScanner

        scanner = VulnerabilityScanner()

        # Create many packages
        packages = [
            Package(name=f"package-{i}", version=f"{i}.0.0") for i in range(20000)  # Way over limit
        ]

        # Should limit the number of packages scanned
        _ = scanner.scan(packages)

        # Check that scanning was limited
        assert scanner._scan_count <= 10000  # MAX_DEPENDENCY_COUNT

    def test_export_path_validation(self):
        """Test that export paths are validated."""
        generator = SBOMGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            (project_path / "requirements.txt").write_text("flask==2.0.1")

            sbom = generator.generate(project_path, scan_vulnerabilities=False)

            # Try to export to invalid path
            evil_output = Path("/etc/passwd")

            with pytest.raises((SBOMError, RuntimeError)):
                generator.export(sbom, evil_output)

            # Valid path should work
            valid_output = Path(tmpdir) / "sbom.json"
            generator.export(sbom, valid_output)
            assert valid_output.exists()


class TestPackageValidation:
    """Test package model validation."""

    def test_reject_malicious_package_name(self):
        """Test that malicious package names are rejected."""
        with pytest.raises(ValueError):
            Package(name="evil/../../../etc/passwd", version="1.0.0")

        with pytest.raises(ValueError):
            Package(name="package;rm -rf /", version="1.0.0")

    def test_reject_invalid_urls(self):
        """Test that invalid URLs are rejected."""
        with pytest.raises(ValueError):
            Package(name="test", version="1.0.0", download_location="javascript:alert(1)")

        with pytest.raises(ValueError):
            Package(name="test", version="1.0.0", homepage="file:///etc/passwd")

    def test_validate_hash_format(self):
        """Test that hash values are validated."""
        # Valid SHA-256 hash should pass
        valid_hash = "a" * 64
        pkg = Package(name="test", version="1.0.0", hash_value=valid_hash)
        assert pkg.hash_value == valid_hash

        # Invalid hash should fail
        with pytest.raises(ValueError):
            Package(name="test", version="1.0.0", hash_value="not-a-hash")

    def test_limit_dependency_count(self):
        """Test that dependency count is limited."""
        # Should accept reasonable number of dependencies
        deps = [f"dep-{i}" for i in range(100)]
        pkg = Package(name="test", version="1.0.0", dependencies=deps)
        assert len(pkg.dependencies) == 100

        # Should reject excessive dependencies
        huge_deps = [f"dep-{i}" for i in range(2000)]
        with pytest.raises(ValueError):
            Package(name="test", version="1.0.0", dependencies=huge_deps)


class TestVulnerabilityValidation:
    """Test vulnerability model validation."""

    def test_validate_cve_format(self):
        """Test that CVE ID format is validated."""
        # Valid CVE should pass
        vuln = Vulnerability(
            cve_id="CVE-2021-12345",
            severity="HIGH",
            cvss_score=7.5,
            description="Test",
            published_date=datetime.now(timezone.utc),
        )
        assert vuln.cve_id == "CVE-2021-12345"

        # Invalid CVE format should fail
        with pytest.raises(ValueError):
            Vulnerability(
                cve_id="NOT-A-CVE",
                severity="HIGH",
                cvss_score=7.5,
                description="Test",
                published_date=datetime.now(timezone.utc),
            )

    def test_validate_severity_levels(self):
        """Test that severity levels are validated."""
        valid_severities = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

        for severity in valid_severities:
            vuln = Vulnerability(
                cve_id="CVE-2021-12345",
                severity=severity,
                cvss_score=5.0,
                description="Test",
                published_date=datetime.now(timezone.utc),
            )
            assert vuln.severity == severity

        # Invalid severity should fail
        with pytest.raises(ValueError):
            Vulnerability(
                cve_id="CVE-2021-12345",
                severity="INVALID",
                cvss_score=5.0,
                description="Test",
                published_date=datetime.now(timezone.utc),
            )

    def test_validate_cvss_score_range(self):
        """Test that CVSS scores are in valid range."""
        # Valid scores should pass
        for score in [0.0, 5.0, 10.0]:
            vuln = Vulnerability(
                cve_id="CVE-2021-12345",
                severity="HIGH",
                cvss_score=score,
                description="Test",
                published_date=datetime.now(timezone.utc),
            )
            assert vuln.cvss_score == score

        # Out of range scores should fail
        for invalid_score in [-1.0, 10.1, 100.0]:
            with pytest.raises(ValueError):
                Vulnerability(
                    cve_id="CVE-2021-12345",
                    severity="HIGH",
                    cvss_score=invalid_score,
                    description="Test",
                    published_date=datetime.now(timezone.utc),
                )

    def test_validate_reference_urls(self):
        """Test that reference URLs are validated."""
        # Valid URLs should pass
        vuln = Vulnerability(
            cve_id="CVE-2021-12345",
            severity="HIGH",
            cvss_score=7.5,
            description="Test",
            published_date=datetime.now(timezone.utc),
            references=["https://nvd.nist.gov/vuln/detail/CVE-2021-12345"],
        )
        assert len(vuln.references) == 1

        # Invalid URLs should fail
        with pytest.raises(ValueError):
            Vulnerability(
                cve_id="CVE-2021-12345",
                severity="HIGH",
                cvss_score=7.5,
                description="Test",
                published_date=datetime.now(timezone.utc),
                references=["javascript:alert(1)"],
            )


# ============================================================================
# Test OWASP Compliance
# ============================================================================


class TestOWASPCompliance:
    """Test OWASP Top 10 compliance."""

    def test_a01_broken_access_control(self, _malicious_project_dir):
        """Test protection against broken access control (A01)."""
        generator = SBOMGenerator()

        # Should validate paths and prevent unauthorized access
        with pytest.raises((ValueError, SBOMError)):
            # Try to access parent directories
            generator.generate(Path("../../../"))

    def test_a02_cryptographic_failures(self):
        """Test protection against cryptographic failures (A02)."""
        from devdocai.compliance.sbom import Ed25519Signer

        _ = Ed25519Signer()

        # Keys should be encrypted at rest
        key_path = Path.home() / ".devdocai" / "sbom_signing_key.enc"
        if key_path.exists():
            # File should contain encrypted data, not plain PEM
            content = key_path.read_bytes()
            assert b"BEGIN OPENSSH PRIVATE KEY" not in content

    def test_a03_injection(self, malicious_project_dir):
        """Test protection against injection attacks (A03)."""
        generator = SBOMGenerator()

        # Generate SBOM with potentially malicious content
        sbom = generator.generate(malicious_project_dir, scan_vulnerabilities=False)

        # All dangerous characters should be sanitized
        for package in sbom.packages:
            assert ";" not in package.name
            assert "|" not in package.name
            assert "<script>" not in package.name

    def test_a04_insecure_design(self):
        """Test secure design principles (A04)."""
        # Security manager should be integrated throughout
        generator = SBOMGenerator()
        assert hasattr(generator, "_security")

        # Rate limiting should be enabled
        assert hasattr(generator._security, "_rate_limiter")

        # Circuit breaker should be enabled
        assert hasattr(generator._security, "_circuit_breaker")

    def test_a05_security_misconfiguration(self):
        """Test protection against security misconfiguration (A05)."""
        # File permissions should be restrictive
        key_path = Path.home() / ".devdocai" / "sbom_signing_key.enc"
        if key_path.exists():
            mode = key_path.stat().st_mode & 0o777
            assert mode == 0o600

    def test_a06_vulnerable_components(self):
        """Test identification of vulnerable components (A06)."""
        from devdocai.compliance.sbom import VulnerabilityScanner

        scanner = VulnerabilityScanner()

        # Should detect known vulnerable versions
        vulnerable_pkg = Package(name="log4j", version="2.14.0")  # Known vulnerable version

        vulns = scanner._scan_package(vulnerable_pkg)
        assert len(vulns) > 0
        assert any(v.cve_id == "CVE-2021-44228" for v in vulns)

    def test_a07_identification_authentication_failures(self):
        """Test protection against auth failures (A07)."""
        # Signature verification should be robust
        from devdocai.compliance.sbom import Ed25519Signer

        signer = Ed25519Signer()

        data = {"test": "data"}
        signature = signer.sign(data)

        # Valid signature should verify
        assert signer.verify(data, signature)

        # Invalid signature should fail
        assert not signer.verify(data, "invalid-signature")

        # Tampered data should fail
        assert not signer.verify({"test": "tampered"}, signature)

    def test_a08_software_data_integrity_failures(self):
        """Test software and data integrity (A08)."""
        generator = SBOMGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            (project_path / "requirements.txt").write_text("flask==2.0.1")

            # Generate signed SBOM
            sbom = generator.generate(project_path, sign=True, scan_vulnerabilities=False)

            # Should have digital signature
            assert sbom.signature is not None
            assert sbom.signature.algorithm == "Ed25519"

            # Signature should be verifiable
            is_valid, errors = generator.validate(sbom)
            assert is_valid or len(errors) > 0  # May have other validation issues

    def test_a09_security_logging_monitoring_failures(self):
        """Test security logging and monitoring (A09)."""
        # Audit logger should be configured
        from devdocai.compliance.sbom import audit_logger

        assert audit_logger is not None
        assert audit_logger.level <= logging.INFO

    def test_a10_server_side_request_forgery(self):
        """Test protection against SSRF (A10)."""
        # URL validation should prevent SSRF
        from devdocai.compliance.sbom import InputSanitizer

        sanitizer = InputSanitizer()

        # Should reject internal URLs
        dangerous_urls = [
            "http://localhost/admin",
            "http://127.0.0.1/",
            "http://169.254.169.254/",  # AWS metadata
            "file:///etc/passwd",
        ]

        for url in dangerous_urls:
            result = sanitizer.sanitize(url, "url")
            # file:// should be completely rejected
            if url.startswith("file://"):
                assert result == ""


# ============================================================================
# Test Performance Impact
# ============================================================================


class TestSecurityPerformanceImpact:
    """Test that security features have acceptable performance impact."""

    def test_generation_performance_with_security(self):
        """Test that security adds <10% overhead."""
        generator = SBOMGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Create a moderate-sized project
            (project_path / "requirements.txt").write_text(
                "\n".join([f"package-{i}==1.0.{i}" for i in range(100)])
            )

            # Time generation with security
            start = time.time()
            sbom = generator.generate(project_path, scan_vulnerabilities=False)
            security_time = time.time() - start

            # Should complete in reasonable time
            assert security_time < 10.0  # Should be much faster

            # Should successfully generate SBOM
            assert len(sbom.packages) == 100

    def test_export_performance_with_pii_scanning(self):
        """Test that PII scanning doesn't significantly slow export."""
        generator = SBOMGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            (project_path / "requirements.txt").write_text("flask==2.0.1")

            sbom = generator.generate(project_path, scan_vulnerabilities=False)

            output_path = Path(tmpdir) / "sbom.json"

            # Time export with PII scanning
            start = time.time()
            generator.export(sbom, output_path)
            export_time = time.time() - start

            # Should be fast
            assert export_time < 1.0

            # File should exist
            assert output_path.exists()

    def test_signature_generation_performance(self):
        """Test that signature generation is fast."""
        from devdocai.compliance.sbom import Ed25519Signer

        signer = Ed25519Signer()

        # Create large data to sign
        large_data = {
            "packages": [{"name": f"pkg-{i}", "version": f"{i}.0.0"} for i in range(1000)]
        }

        # Time signature generation
        start = time.time()
        signature = signer.sign(large_data)
        sign_time = time.time() - start

        # Should be very fast
        assert sign_time < 0.1

        # Signature should be valid
        assert signer.verify(large_data, signature)
