"""
M010 SBOM Generator - Security Module
DevDocAI v3.0.0 - Security infrastructure for SBOM generation

This module provides comprehensive security controls including rate limiting,
circuit breaker patterns, PII detection, path validation, and input sanitization.
"""

import logging
import re
import threading
import time
from collections import defaultdict
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger(f"{__name__}.audit")


# ============================================================================
# Security Constants
# ============================================================================

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB max file size
MAX_DEPENDENCY_COUNT = 10000  # Maximum dependencies to process
MAX_PROCESSING_TIME = 300  # 5 minutes max processing time
RATE_LIMIT_REQUESTS = 100  # Max requests per minute
RATE_LIMIT_WINDOW = 60  # Rate limit window in seconds
MAX_PATH_DEPTH = 10  # Maximum directory traversal depth
MIN_KEY_SIZE = 32  # Minimum encryption key size in bytes

# PII Detection Patterns
PII_PATTERNS = [
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "email"),
    (r"\b(?:\d{3}-\d{2}-\d{4}|\d{9})\b", "ssn"),
    (r"\b(?:\d{4}[\s-]?){3}\d{4}\b", "credit_card"),
    (r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", "phone"),
    (r"\b(?:eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)\b", "jwt"),
    (r"\b(?:sk_live_|pk_live_|sk_test_|pk_test_)[A-Za-z0-9]{24,}\b", "api_key"),
    (r"\b(?:ghp_|gho_|ghu_|ghs_|ghr_)[A-Za-z0-9]{36,}\b", "github_token"),
    (r"\b(?:xox[baprs]-[A-Za-z0-9]{10,48})\b", "slack_token"),
]

# Allowed file extensions for dependency files
ALLOWED_DEPENDENCY_FILES = {
    ".txt",
    ".toml",
    ".json",
    ".xml",
    ".csproj",
    ".mod",
    ".sum",
    ".lock",
    ".config",
}


# ============================================================================
# Security Manager
# ============================================================================


class SecurityManager:
    """Centralized security management for SBOM operations."""

    def __init__(self):
        """Initialize security manager."""
        self._rate_limiter = RateLimiter(RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW)
        self._circuit_breaker = CircuitBreaker()
        self._pii_detector = PIIDetector()
        self._path_validator = PathValidator()
        self._input_sanitizer = InputSanitizer()

    def validate_path(self, path: Path, base_path: Optional[Path] = None) -> bool:
        """Validate path for traversal attacks."""
        return self._path_validator.validate(path, base_path)

    def sanitize_input(self, value: str, input_type: str = "generic") -> str:
        """Sanitize input to prevent injection attacks."""
        return self._input_sanitizer.sanitize(value, input_type)

    def detect_pii(self, content: str) -> List[Tuple[str, str]]:
        """Detect PII in content."""
        return self._pii_detector.detect(content)

    def check_rate_limit(self, operation: str) -> bool:
        """Check if operation is within rate limits."""
        return self._rate_limiter.check(operation)

    def circuit_breaker_call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        return self._circuit_breaker.call(func, *args, **kwargs)


# ============================================================================
# Rate Limiter
# ============================================================================


class RateLimiter:
    """Rate limiting for resource-intensive operations."""

    def __init__(self, max_requests: int, window_seconds: int):
        """Initialize rate limiter."""
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._requests = defaultdict(list)
        self._lock = threading.RLock()

    def check(self, operation: str) -> bool:
        """Check if operation is within rate limits."""
        with self._lock:
            now = time.time()
            window_start = now - self._window_seconds

            # Clean old requests
            self._requests[operation] = [t for t in self._requests[operation] if t > window_start]

            # Check limit
            if len(self._requests[operation]) >= self._max_requests:
                audit_logger.warning(
                    f"Rate limit exceeded for operation: {operation}",
                    extra={"security_event": "rate_limit_exceeded"},
                )
                return False

            # Add request
            self._requests[operation].append(now)
            return True


# ============================================================================
# Circuit Breaker
# ============================================================================


class CircuitBreaker:
    """Circuit breaker pattern for external operations."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        """Initialize circuit breaker."""
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._failures = 0
        self._last_failure = None
        self._state = "closed"  # closed, open, half-open
        self._lock = threading.RLock()

    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        with self._lock:
            # Check if circuit is open
            if self._state == "open":
                if self._last_failure:
                    elapsed = time.time() - self._last_failure
                    if elapsed > self._recovery_timeout:
                        self._state = "half-open"
                        audit_logger.info(
                            "Circuit breaker entering half-open state",
                            extra={"security_event": "circuit_breaker_half_open"},
                        )
                    else:
                        raise RuntimeError("Circuit breaker is open")

            try:
                result = func(*args, **kwargs)

                # Reset on success
                if self._state == "half-open":
                    self._state = "closed"
                    self._failures = 0
                    audit_logger.info(
                        "Circuit breaker closed after recovery",
                        extra={"security_event": "circuit_breaker_closed"},
                    )

                return result

            except Exception:
                self._failures += 1
                self._last_failure = time.time()

                if self._failures >= self._failure_threshold:
                    self._state = "open"
                    audit_logger.error(
                        f"Circuit breaker opened after {self._failures} failures",
                        extra={"security_event": "circuit_breaker_opened"},
                    )

                raise


# ============================================================================
# PII Detector
# ============================================================================


class PIIDetector:
    """Detect and sanitize PII in content."""

    def __init__(self):
        """Initialize PII detector."""
        self._patterns = [(re.compile(p), t) for p, t in PII_PATTERNS]

    def detect(self, content: str) -> List[Tuple[str, str]]:
        """Detect PII in content."""
        found_pii = []

        for pattern, pii_type in self._patterns:
            matches = pattern.findall(content)
            for match in matches:
                found_pii.append((match, pii_type))
                audit_logger.warning(
                    f"PII detected: type={pii_type}",
                    extra={"security_event": "pii_detected", "pii_type": pii_type},
                )

        return found_pii

    def sanitize(self, content: str) -> str:
        """Remove or mask PII from content."""
        sanitized = content

        for pattern, pii_type in self._patterns:
            if pii_type in ["email", "ssn", "credit_card", "phone"]:
                # Mask sensitive data
                sanitized = pattern.sub(lambda m: "*" * len(m.group()), sanitized)
            else:
                # Remove tokens and keys completely
                sanitized = pattern.sub("[REDACTED]", sanitized)

        return sanitized


# ============================================================================
# Path Validator
# ============================================================================


class PathValidator:
    """Validate file paths for security."""

    def validate(self, path: Path, base_path: Optional[Path] = None) -> bool:
        """Validate path for traversal attacks."""
        try:
            # Resolve to absolute path
            resolved = path.resolve()

            # Check if path exists and is accessible
            if not resolved.exists():
                return True  # Non-existent paths are safe

            # Check for symbolic links
            if resolved.is_symlink():
                audit_logger.warning(
                    f"Symbolic link detected: {path}", extra={"security_event": "symlink_detected"}
                )
                return False

            # Check traversal depth
            parts = resolved.parts
            if len(parts) > MAX_PATH_DEPTH:
                audit_logger.warning(
                    f"Path depth exceeds limit: {path}",
                    extra={"security_event": "path_depth_exceeded"},
                )
                return False

            # Check if within base path
            if base_path:
                base_resolved = base_path.resolve()
                if not str(resolved).startswith(str(base_resolved)):
                    audit_logger.warning(
                        f"Path traversal attempt: {path}",
                        extra={"security_event": "path_traversal_attempt"},
                    )
                    return False

            # Check for suspicious patterns
            suspicious_patterns = ["..", "~", "$", "|", ";", "&", ">", "<"]
            path_str = str(path)
            for pattern in suspicious_patterns:
                if pattern in path_str:
                    audit_logger.warning(
                        f"Suspicious pattern in path: {path}",
                        extra={"security_event": "suspicious_path_pattern"},
                    )
                    return False

            return True

        except Exception as e:
            audit_logger.error(
                f"Path validation error: {e}", extra={"security_event": "path_validation_error"}
            )
            return False


# ============================================================================
# Input Sanitizer
# ============================================================================


class InputSanitizer:
    """Sanitize user input to prevent injection attacks."""

    def sanitize(self, value: str, input_type: str = "generic") -> str:
        """Sanitize input based on type."""
        if not value:
            return value

        # Remove null bytes
        sanitized = value.replace("\x00", "")

        # Type-specific sanitization
        if input_type == "package_name":
            # Allow only alphanumeric, dash, underscore, dot
            sanitized = re.sub(r"[^a-zA-Z0-9\-_\.]", "", sanitized)

        elif input_type == "version":
            # Allow semantic versioning characters
            sanitized = re.sub(r"[^a-zA-Z0-9\-_\.\+~^]", "", sanitized)

        elif input_type == "url":
            # Basic URL sanitization
            parsed = urlparse(sanitized)
            if parsed.scheme not in ["http", "https", "git"]:
                sanitized = ""

        elif input_type == "command":
            # Remove shell metacharacters
            shell_meta = ["|", ";", "&", ">", "<", "`", "$", "(", ")", "{", "}", "[", "]"]
            for char in shell_meta:
                sanitized = sanitized.replace(char, "")

        # Limit length
        max_length = 1024
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]

        return sanitized
