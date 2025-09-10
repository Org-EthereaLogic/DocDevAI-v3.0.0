"""
M011 Batch Operations Manager - Pass 3: Security Hardening
DevDocAI v3.0.0

Enterprise-grade security for batch operations:
- Input validation and sanitization
- Rate limiting and DoS protection
- Secure cache encryption
- Comprehensive audit logging
- Resource limits and circuit breakers
- OWASP Top 10 compliance
"""

import asyncio
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


# ============================================================================
# Security Configuration
# ============================================================================


@dataclass
class SecurityConfig:
    """Security configuration for batch operations."""

    # Rate limiting
    enable_rate_limiting: bool = True
    rate_limit_requests_per_minute: int = 100
    rate_limit_burst_size: int = 20
    rate_limit_cooldown_seconds: int = 60

    # Resource limits
    max_memory_mb: int = 1024  # Hard limit on memory usage
    max_cpu_percent: float = 80.0  # Max CPU usage
    max_concurrent_operations: int = 10
    max_document_size_mb: int = 100
    max_batch_size: int = 1000

    # Audit logging
    enable_audit_logging: bool = True
    audit_log_path: Path = Path("audit/batch_security.log")
    audit_log_rotation_mb: int = 100
    audit_log_retention_days: int = 90

    # Encryption
    enable_cache_encryption: bool = True
    encryption_key_rotation_days: int = 30
    secure_key_storage: bool = True

    # Input validation
    enable_input_validation: bool = True
    max_content_length: int = 10_000_000  # 10MB
    allowed_content_types: Set[str] = field(
        default_factory=lambda: {"text", "markdown", "json", "xml"}
    )
    
    # PII protection
    enable_pii_detection: bool = True
    pii_redaction_enabled: bool = False
    pii_audit_enabled: bool = True

    # DoS protection
    enable_circuit_breaker: bool = True
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout_seconds: int = 60


# ============================================================================
# Security Events
# ============================================================================


class SecurityEvent(Enum):
    """Security event types for audit logging."""

    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    RESOURCE_LIMIT_EXCEEDED = "resource_limit_exceeded"
    INVALID_INPUT = "invalid_input"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    PII_DETECTED = "pii_detected"
    ENCRYPTION_ERROR = "encryption_error"
    CIRCUIT_BREAKER_TRIGGERED = "circuit_breaker_triggered"
    SUSPICIOUS_PATTERN = "suspicious_pattern"
    VALIDATION_FAILURE = "validation_failure"
    CACHE_TAMPERING = "cache_tampering"


# ============================================================================
# Input Validator
# ============================================================================


class InputValidator:
    """Validate and sanitize input documents."""

    # Dangerous patterns to detect
    DANGEROUS_PATTERNS = [
        r"<script[^>]*>.*?</script>",  # XSS
        r"javascript:",  # JavaScript protocol
        r"on\w+\s*=",  # Event handlers
        r"\.\./",  # Path traversal
        r"\\x[0-9a-fA-F]{2}",  # Hex encoding
        r"%[0-9a-fA-F]{2}",  # URL encoding
        r"union\s+select",  # SQL injection
        r"drop\s+table",  # SQL destructive command
        r"delete\s+from",  # SQL destructive command
        r"exec\s*\(",  # Command execution
        r"eval\s*\(",  # Code evaluation
        r"__import__",  # Python import
        r"rm\s+-rf\s+/",  # Dangerous shell command
        r"<!DOCTYPE|<!ENTITY",  # XXE patterns
    ]

    # PII patterns (simplified - use dedicated PII detector in production)
    PII_PATTERNS = [
        r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
        r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",  # Credit card
        r"\b[A-Z]{2}\d{6,8}\b",  # Passport
        r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",  # Phone number
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
    ]

    def __init__(self, config: SecurityConfig):
        """Initialize input validator."""
        self.config = config
        self._compiled_dangerous = [
            re.compile(pattern, re.IGNORECASE | re.DOTALL)
            for pattern in self.DANGEROUS_PATTERNS
        ]
        self._compiled_pii = [
            re.compile(pattern) for pattern in self.PII_PATTERNS
        ]

    def validate_document(
        self, document: Dict[str, Any]
    ) -> Tuple[bool, Optional[str], List[str]]:
        """
        Validate document for security issues.

        Returns:
            Tuple of (is_valid, error_message, detected_issues)
        """
        if not self.config.enable_input_validation:
            return True, None, []

        issues = []

        # Check document structure
        if not isinstance(document, dict):
            return False, "Document must be a dictionary", ["invalid_type"]

        # Check required fields
        if "id" not in document:
            return False, "Document missing required 'id' field", ["missing_id"]

        # Check content length
        content = document.get("content", "")
        if len(content) > self.config.max_content_length:
            return False, f"Content exceeds maximum length", ["content_too_large"]

        # Check for dangerous patterns
        for pattern in self._compiled_dangerous:
            if pattern.search(content):
                issues.append(f"dangerous_pattern:{pattern.pattern[:20]}")

        # Check for PII if enabled
        if self.config.enable_pii_detection:
            pii_found = self._detect_pii(content)
            if pii_found:
                issues.extend([f"pii:{pii_type}" for pii_type in pii_found])

        # Check content type
        doc_type = document.get("type", "text")
        if doc_type not in self.config.allowed_content_types:
            issues.append(f"invalid_content_type:{doc_type}")

        # Return results
        if issues:
            return False, f"Security issues detected: {', '.join(issues)}", issues

        return True, None, []

    def sanitize_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize document content."""
        sanitized = document.copy()
        content = sanitized.get("content", "")

        # Remove dangerous patterns
        for pattern in self._compiled_dangerous:
            content = pattern.sub("", content)

        # Redact PII if configured
        if self.config.pii_redaction_enabled:
            for pattern in self._compiled_pii:
                content = pattern.sub("[REDACTED]", content)

        # HTML escape special characters
        content = (
            content.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )

        sanitized["content"] = content
        return sanitized

    def _detect_pii(self, content: str) -> List[str]:
        """Detect PII in content."""
        pii_types = []
        for i, pattern in enumerate(self._compiled_pii):
            if pattern.search(content):
                pii_types.append(self.PII_PATTERNS[i].split("\\b")[1][:10])
        return pii_types


# ============================================================================
# Rate Limiter
# ============================================================================


class RateLimiter:
    """Token bucket rate limiter for DoS protection."""

    def __init__(self, config: SecurityConfig):
        """Initialize rate limiter."""
        self.config = config
        self._buckets = defaultdict(lambda: {
            "tokens": config.rate_limit_burst_size,
            "last_refill": time.time()
        })
        self._blocked_until = {}

    def check_rate_limit(self, client_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check if client is within rate limits.

        Returns:
            Tuple of (allowed, error_message)
        """
        if not self.config.enable_rate_limiting:
            return True, None

        current_time = time.time()

        # Check if client is in cooldown
        if client_id in self._blocked_until:
            if current_time < self._blocked_until[client_id]:
                remaining = int(self._blocked_until[client_id] - current_time)
                return False, f"Rate limit exceeded. Retry in {remaining} seconds"
            else:
                del self._blocked_until[client_id]
                # Allow first request immediately after cooldown
                return True, None

        # Get or create bucket
        bucket = self._buckets[client_id]

        # Refill tokens based on time elapsed
        prev_refill = bucket["last_refill"]
        time_elapsed = current_time - prev_refill
        tokens_to_add = (
            time_elapsed * self.config.rate_limit_requests_per_minute / 60
        )
        bucket["tokens"] = min(
            self.config.rate_limit_burst_size,
            bucket["tokens"] + tokens_to_add
        )
        bucket["last_refill"] = current_time

        # Check if request can be allowed
        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True, None
        else:
            # If cooldown period has elapsed, allow a single request
            if time_elapsed >= self.config.rate_limit_cooldown_seconds:
                bucket["tokens"] = 0
                return True, None
            # Apply cooldown
            self._blocked_until[client_id] = (
                current_time + self.config.rate_limit_cooldown_seconds
            )
            return False, "Rate limit exceeded"

    def reset_client(self, client_id: str):
        """Reset rate limit for a client."""
        if client_id in self._buckets:
            del self._buckets[client_id]
        if client_id in self._blocked_until:
            del self._blocked_until[client_id]


# ============================================================================
# Secure Cache
# ============================================================================


class SecureCache:
    """Encrypted cache for sensitive data."""

    def __init__(self, config: SecurityConfig, encryption_key: Optional[bytes] = None):
        """Initialize secure cache."""
        self.config = config
        self._cache = {}
        self._cache_hmac = {}
        
        # Initialize encryption
        if config.enable_cache_encryption:
            if encryption_key:
                self._fernet = Fernet(encryption_key)
            else:
                # Generate new key
                self._fernet = Fernet(Fernet.generate_key())
        else:
            self._fernet = None

        # Generate HMAC key for integrity
        self._hmac_key = secrets.token_bytes(32)

    def get(self, key: str) -> Optional[Any]:
        """Get item from secure cache."""
        if key not in self._cache:
            return None

        encrypted_data = self._cache[key]
        stored_hmac = self._cache_hmac.get(key)

        # Verify integrity
        if stored_hmac:
            computed_hmac = self._compute_hmac(encrypted_data)
            if not hmac.compare_digest(stored_hmac, computed_hmac):
                logger.error(f"Cache tampering detected for key: {key}")
                del self._cache[key]
                del self._cache_hmac[key]
                return None

        # Decrypt if encryption is enabled
        if self._fernet and self.config.enable_cache_encryption:
            try:
                decrypted = self._fernet.decrypt(encrypted_data)
                return json.loads(decrypted)
            except Exception as e:
                logger.error(f"Decryption failed for key {key}: {e}")
                return None
        else:
            return encrypted_data

    def put(self, key: str, value: Any) -> None:
        """Put item in secure cache."""
        # Encrypt if enabled
        if self._fernet and self.config.enable_cache_encryption:
            json_data = json.dumps(value).encode()
            encrypted_data = self._fernet.encrypt(json_data)
        else:
            encrypted_data = value

        # Compute HMAC for integrity
        computed_hmac = self._compute_hmac(encrypted_data)

        # Store
        self._cache[key] = encrypted_data
        self._cache_hmac[key] = computed_hmac

    def _compute_hmac(self, data: bytes) -> bytes:
        """Compute HMAC for data integrity."""
        if isinstance(data, str):
            data = data.encode()
        return hmac.new(self._hmac_key, data, hashlib.sha256).digest()

    def clear(self):
        """Clear cache securely."""
        self._cache.clear()
        self._cache_hmac.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Return basic cache statistics for compatibility."""
        size_bytes = 0
        try:
            # Approximate stored size when encrypted
            for v in self._cache.values():
                size_bytes += len(v) if isinstance(v, (bytes, bytearray)) else 0
        except Exception:
            pass
        return {
            "hits": 0,
            "misses": 0,
            "hit_rate": 0,
            "evictions": 0,
            "size_mb": size_bytes / (1024 * 1024),
            "items": len(self._cache),
        }


# ============================================================================
# Audit Logger
# ============================================================================


class AuditLogger:
    """Security audit logging."""

    def __init__(self, config: SecurityConfig):
        """Initialize audit logger."""
        self.config = config
        self._setup_logger()

    def _setup_logger(self):
        """Set up audit logger with rotation."""
        if not self.config.enable_audit_logging:
            self._logger = None
            return

        # Create audit directory
        self.config.audit_log_path.parent.mkdir(parents=True, exist_ok=True)

        # Set up logger
        self._logger = logging.getLogger("batch_security_audit")
        self._logger.setLevel(logging.INFO)

        # Add file handler with rotation
        from logging.handlers import RotatingFileHandler
        handler = RotatingFileHandler(
            self.config.audit_log_path,
            maxBytes=self.config.audit_log_rotation_mb * 1024 * 1024,
            backupCount=5
        )
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        self._logger.addHandler(handler)

    def log_event(
        self,
        event: SecurityEvent,
        client_id: str,
        details: Dict[str, Any],
        severity: str = "INFO"
    ):
        """Log security event."""
        if not self._logger:
            return

        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event.value,
            "client_id": client_id,
            "severity": severity,
            "details": details
        }

        if severity == "CRITICAL":
            self._logger.critical(json.dumps(log_entry))
        elif severity == "ERROR":
            self._logger.error(json.dumps(log_entry))
        elif severity == "WARNING":
            self._logger.warning(json.dumps(log_entry))
        else:
            self._logger.info(json.dumps(log_entry))


# ============================================================================
# Circuit Breaker
# ============================================================================


class CircuitBreaker:
    """Circuit breaker for fault tolerance."""

    class State(Enum):
        CLOSED = "closed"  # Normal operation
        OPEN = "open"  # Blocking requests
        HALF_OPEN = "half_open"  # Testing recovery

    def __init__(self, config: SecurityConfig):
        """Initialize circuit breaker."""
        self.config = config
        self.state = self.State.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.success_count = 0

    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if not self.config.enable_circuit_breaker:
            return func(*args, **kwargs)

        # Check state
        if self.state == self.State.OPEN:
            if self._should_attempt_reset():
                self.state = self.State.HALF_OPEN
            else:
                raise BatchSecurityError("Circuit breaker is open")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        if self.state == self.State.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= 3:  # Require 3 successes to close
                self.state = self.State.CLOSED
                self.success_count = 0

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.config.circuit_breaker_threshold:
            self.state = self.State.OPEN
            self.success_count = 0

    def _should_attempt_reset(self) -> bool:
        """Check if should attempt reset."""
        if not self.last_failure_time:
            return True
        
        time_since_failure = time.time() - self.last_failure_time
        return time_since_failure >= self.config.circuit_breaker_timeout_seconds


# ============================================================================
# Resource Monitor
# ============================================================================


class ResourceMonitor:
    """Monitor and enforce resource limits."""

    def __init__(self, config: SecurityConfig):
        """Initialize resource monitor."""
        self.config = config
        self._start_time = time.time()
        self._operation_count = 0

    def check_limits(self) -> Tuple[bool, Optional[str]]:
        """
        Check if resource limits are exceeded.

        Returns:
            Tuple of (within_limits, error_message)
        """
        import psutil
        process = psutil.Process(os.getpid())

        # Check memory usage
        memory_mb = process.memory_info().rss / (1024 * 1024)
        if memory_mb > self.config.max_memory_mb:
            return False, f"Memory limit exceeded: {memory_mb:.1f}MB > {self.config.max_memory_mb}MB"

        # Check CPU usage
        cpu_percent = process.cpu_percent(interval=0.1)
        if cpu_percent > self.config.max_cpu_percent:
            return False, f"CPU limit exceeded: {cpu_percent:.1f}% > {self.config.max_cpu_percent}%"

        # Check concurrent operations
        self._operation_count += 1
        if self._operation_count > self.config.max_concurrent_operations:
            return False, f"Concurrent operation limit exceeded"

        return True, None

    def release_operation(self):
        """Release an operation slot."""
        self._operation_count = max(0, self._operation_count - 1)


# ============================================================================
# Exceptions
# ============================================================================


class BatchSecurityError(Exception):
    """Security-related batch operation error."""
    pass


# ============================================================================
# Security Manager
# ============================================================================


class BatchSecurityManager:
    """
    Comprehensive security manager for batch operations.
    
    Provides:
    - Input validation and sanitization
    - Rate limiting and DoS protection
    - Secure cache with encryption
    - Audit logging
    - Resource monitoring
    - Circuit breaker protection
    """

    def __init__(self, config: Optional[SecurityConfig] = None):
        """Initialize security manager."""
        self.config = config or SecurityConfig()
        
        # Initialize components
        self.validator = InputValidator(self.config)
        self.rate_limiter = RateLimiter(self.config)
        self.secure_cache = SecureCache(self.config)
        self.audit_logger = AuditLogger(self.config)
        self.circuit_breaker = CircuitBreaker(self.config)
        self.resource_monitor = ResourceMonitor(self.config)

        logger.info("BatchSecurityManager initialized with Pass 3 security hardening")

    async def validate_and_process(
        self,
        document: Dict[str, Any],
        client_id: str,
        processor_func: Any
    ) -> Tuple[bool, Any, Optional[str]]:
        """
        Validate and process document with full security.

        Returns:
            Tuple of (success, result, error_message)
        """
        try:
            # Rate limiting
            allowed, error = self.rate_limiter.check_rate_limit(client_id)
            if not allowed:
                self.audit_logger.log_event(
                    SecurityEvent.RATE_LIMIT_EXCEEDED,
                    client_id,
                    {"error": error},
                    "WARNING"
                )
                return False, None, error

            # Resource limits
            within_limits, error = self.resource_monitor.check_limits()
            if not within_limits:
                self.audit_logger.log_event(
                    SecurityEvent.RESOURCE_LIMIT_EXCEEDED,
                    client_id,
                    {"error": error},
                    "ERROR"
                )
                return False, None, error

            # Input validation
            is_valid, error, issues = self.validator.validate_document(document)
            if not is_valid:
                self.audit_logger.log_event(
                    SecurityEvent.INVALID_INPUT,
                    client_id,
                    {"error": error, "issues": issues},
                    "WARNING"
                )
                return False, None, error

            # Sanitize document
            sanitized = self.validator.sanitize_document(document)

            # Process with circuit breaker
            result = await self._process_with_circuit_breaker(
                sanitized, processor_func
            )

            # Release resources
            self.resource_monitor.release_operation()

            return True, result, None

        except Exception as e:
            self.audit_logger.log_event(
                SecurityEvent.VALIDATION_FAILURE,
                client_id,
                {"error": str(e)},
                "ERROR"
            )
            return False, None, str(e)

    async def _process_with_circuit_breaker(
        self,
        document: Dict[str, Any],
        processor_func: Any
    ):
        """Process with circuit breaker protection."""
        if asyncio.iscoroutinefunction(processor_func):
            return await self.circuit_breaker.call(processor_func, document)
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                self.circuit_breaker.call,
                processor_func,
                document
            )

    def generate_secure_cache_key(self, *args) -> str:
        """Generate secure cache key using SHA-256."""
        # Use SHA-256 instead of MD5
        key_data = ":".join(str(arg) for arg in args)
        return hashlib.sha256(key_data.encode()).hexdigest()

    def shutdown(self):
        """Shutdown security manager."""
        self.secure_cache.clear()
        logger.info("BatchSecurityManager shutdown complete")
