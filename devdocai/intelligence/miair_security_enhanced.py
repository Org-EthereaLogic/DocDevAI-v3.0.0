"""
M003 MIAIR Engine - Enhanced Security Implementation
DevDocAI v3.0.0 - Pass 3: Security Hardening

Comprehensive security enhancements including:
- 12+ PII pattern detection
- Document integrity validation
- Comprehensive audit logging
- Enhanced DOS/DDOS protection
- OWASP Top 10 compliance
"""

import base64
import hashlib
import hmac
import html
import ipaddress
import json
import logging
import re
import secrets
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from threading import Lock
from typing import Any, Dict, List, Optional

import jwt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Configure security loggers
security_logger = logging.getLogger("devdocai.security")
audit_logger = logging.getLogger("devdocai.audit")


# ============================================================================
# Security Constants and Enums
# ============================================================================


class SecurityLevel(Enum):
    """Security level classifications."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AuditEvent(Enum):
    """Audit event types for comprehensive logging."""

    # Authentication Events
    AUTH_LOGIN_SUCCESS = "auth.login.success"
    AUTH_LOGIN_FAILURE = "auth.login.failure"
    AUTH_TOKEN_GENERATED = "auth.token.generated"
    AUTH_TOKEN_VALIDATED = "auth.token.validated"
    AUTH_TOKEN_EXPIRED = "auth.token.expired"
    AUTH_SESSION_CREATED = "auth.session.created"
    AUTH_SESSION_DESTROYED = "auth.session.destroyed"

    # Document Operations
    DOC_ACCESS = "document.access"
    DOC_CREATED = "document.created"
    DOC_MODIFIED = "document.modified"
    DOC_DELETED = "document.deleted"
    DOC_OPTIMIZED = "document.optimized"
    DOC_PII_DETECTED = "document.pii_detected"
    DOC_MALICIOUS_DETECTED = "document.malicious_detected"

    # Security Events
    SEC_RATE_LIMIT_EXCEEDED = "security.rate_limit_exceeded"
    SEC_VALIDATION_FAILED = "security.validation_failed"
    SEC_INJECTION_ATTEMPT = "security.injection_attempt"
    SEC_PII_VIOLATION = "security.pii_violation"
    SEC_RESOURCE_EXHAUSTION = "security.resource_exhaustion"
    SEC_UNAUTHORIZED_ACCESS = "security.unauthorized_access"
    SEC_INTEGRITY_VIOLATION = "security.integrity_violation"

    # System Events
    SYS_CONFIG_CHANGED = "system.config_changed"
    SYS_PERFORMANCE_ANOMALY = "system.performance_anomaly"
    SYS_ERROR = "system.error"
    SYS_CIRCUIT_BREAKER_OPEN = "system.circuit_breaker_open"
    SYS_CIRCUIT_BREAKER_CLOSED = "system.circuit_breaker_closed"


# ============================================================================
# Enhanced PII Detection System
# ============================================================================


class PIIDetector:
    """
    Comprehensive PII detection with 12+ patterns.
    Implements privacy protection and compliance requirements.
    """

    # Comprehensive PII patterns (12+ types)
    PII_PATTERNS = {
        # Financial Information
        "ssn": re.compile(
            r"\b(?!000|666|9\d{2})\d{3}[-\s]?(?!00)\d{2}[-\s]?(?!0000)\d{4}\b",
            re.IGNORECASE,
        ),
        "credit_card": re.compile(
            r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|"
            r"3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|"
            r"(?:2131|1800|35\d{3})\d{11})\b"
        ),
        "bank_account": re.compile(r"\b[0-9]{8,17}\b"),
        "iban": re.compile(r"\b[A-Z]{2}[0-9]{2}[A-Z0-9]{4}[0-9]{7}([A-Z0-9]?){0,16}\b"),
        "routing_number": re.compile(
            r"\b(?:0[0-9]|1[0-2]|2[1-9]|3[0-2]|6[1-9]|7[0-2]|8[0]|9[0-1])[0-9]{7}\b"
        ),
        # Contact Information
        "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        "phone": re.compile(r"\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b"),
        "international_phone": re.compile(r"\b\+[1-9]\d{1,14}\b"),
        # Network Information
        "ipv4": re.compile(
            r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
            r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
        ),
        "ipv6": re.compile(r"\b(?:[A-F0-9]{1,4}:){7}[A-F0-9]{1,4}\b", re.IGNORECASE),
        "mac_address": re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b"),
        # Identity Documents
        "passport": re.compile(r"\b[A-Z][0-9]{8}\b"),
        "drivers_license": re.compile(r"\b[A-Z]{1,2}[0-9]{6,8}\b"),
        "national_id": re.compile(r"\b[A-Z0-9]{6,12}\b"),
        # Personal Information
        "date_of_birth": re.compile(
            r"\b(?:0[1-9]|1[0-2])[-/.](?:0[1-9]|[12][0-9]|3[01])[-/.]" r"(?:19|20)\d{2}\b"
        ),
        "age": re.compile(r"\b(?:age|aged?)\s*:?\s*(\d{1,3})\b", re.IGNORECASE),
        # Medical Information
        "medical_record": re.compile(
            r"\b(?:MRN|Medical Record #?)\s*:?\s*([A-Z0-9]{6,12})\b", re.IGNORECASE
        ),
        "health_insurance": re.compile(r"\b[A-Z]{3}[0-9]{9}\b"),
        # Credentials and Keys
        "aws_access_key": re.compile(r"\b(?:AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}\b"),
        "aws_secret_key": re.compile(r"\b[A-Za-z0-9/+=]{40}\b"),
        "api_key": re.compile(
            r"\b(?:api[_-]?key|apikey)\s*[:=]\s*([a-zA-Z0-9]{32,})\b", re.IGNORECASE
        ),
        "jwt_token": re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
        "private_key": re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
        "password": re.compile(r"\b(?:password|passwd|pwd)\s*[:=]\s*([^\s]{8,})\b", re.IGNORECASE),
        # Vehicle Information
        "license_plate": re.compile(r"\b[A-Z]{1,3}[-\s]?[A-Z0-9]{1,4}[-\s]?[A-Z0-9]{1,4}\b"),
        "vin": re.compile(r"\b[A-HJ-NPR-Z0-9]{17}\b"),
    }

    # PII severity levels
    PII_SEVERITY = {
        "ssn": SecurityLevel.CRITICAL,
        "credit_card": SecurityLevel.CRITICAL,
        "bank_account": SecurityLevel.CRITICAL,
        "medical_record": SecurityLevel.CRITICAL,
        "private_key": SecurityLevel.CRITICAL,
        "aws_secret_key": SecurityLevel.CRITICAL,
        "password": SecurityLevel.CRITICAL,
        "passport": SecurityLevel.HIGH,
        "drivers_license": SecurityLevel.HIGH,
        "date_of_birth": SecurityLevel.HIGH,
        "health_insurance": SecurityLevel.HIGH,
        "api_key": SecurityLevel.HIGH,
        "jwt_token": SecurityLevel.HIGH,
        "email": SecurityLevel.MEDIUM,
        "phone": SecurityLevel.MEDIUM,
        "ipv4": SecurityLevel.MEDIUM,
        "ipv6": SecurityLevel.MEDIUM,
        "age": SecurityLevel.LOW,
        "license_plate": SecurityLevel.LOW,
    }

    def __init__(self, enable_masking: bool = True):
        """Initialize PII detector with optional masking."""
        self.enable_masking = enable_masking
        self._detection_cache = {}
        self._cache_lock = Lock()

    def detect(self, text: str) -> Dict[str, List[str]]:
        """
        Detect all PII in text and return categorized results.

        Args:
            text: Text to scan for PII

        Returns:
            Dictionary mapping PII types to found values
        """
        if not text:
            return {}

        # Check cache
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        with self._cache_lock:
            if text_hash in self._detection_cache:
                return self._detection_cache[text_hash]

        detected_pii = {}

        for pii_type, pattern in self.PII_PATTERNS.items():
            matches = pattern.findall(text)
            if matches:
                # Store unique matches
                detected_pii[pii_type] = list(set(matches))

                # Log detection based on severity
                severity = self.PII_SEVERITY.get(pii_type, SecurityLevel.INFO)
                if severity in [SecurityLevel.CRITICAL, SecurityLevel.HIGH]:
                    security_logger.warning(
                        f"PII detected - Type: {pii_type}, Severity: {severity.value}, "
                        f"Count: {len(detected_pii[pii_type])}"
                    )

        # Cache result
        with self._cache_lock:
            self._detection_cache[text_hash] = detected_pii
            # LRU eviction
            if len(self._detection_cache) > 1000:
                oldest = next(iter(self._detection_cache))
                del self._detection_cache[oldest]

        return detected_pii

    def mask(self, text: str, detected_pii: Optional[Dict[str, List[str]]] = None) -> str:
        """
        Mask PII in text with secure placeholders.

        Args:
            text: Text containing PII
            detected_pii: Pre-detected PII (optional)

        Returns:
            Text with PII masked
        """
        if not self.enable_masking:
            return text

        if detected_pii is None:
            detected_pii = self.detect(text)

        masked_text = text

        for pii_type, values in detected_pii.items():
            for value in values:
                # Create type-specific mask
                if pii_type == "email":
                    parts = value.split("@")
                    mask = f"{parts[0][:2]}***@***.***"
                elif pii_type in ["ssn", "credit_card", "bank_account"]:
                    mask = f"[{pii_type.upper()}-****{value[-4:]}]"
                elif pii_type in ["phone", "international_phone"]:
                    mask = f"[PHONE-****{value[-4:]}]"
                else:
                    mask = f"[{pii_type.upper()}-REDACTED]"

                masked_text = masked_text.replace(value, mask)

        return masked_text

    def get_severity_summary(self, detected_pii: Dict[str, List[str]]) -> Dict[str, int]:
        """Get summary of PII by severity level."""
        summary = {
            SecurityLevel.CRITICAL: 0,
            SecurityLevel.HIGH: 0,
            SecurityLevel.MEDIUM: 0,
            SecurityLevel.LOW: 0,
            SecurityLevel.INFO: 0,
        }

        for pii_type, values in detected_pii.items():
            severity = self.PII_SEVERITY.get(pii_type, SecurityLevel.INFO)
            summary[severity] += len(values)

        return {k.value: v for k, v in summary.items() if v > 0}


# ============================================================================
# Document Integrity System
# ============================================================================


class DocumentIntegrity:
    """
    Document integrity validation using checksums and signatures.
    Implements HMAC-SHA256 for tamper detection.
    """

    def __init__(self, secret_key: Optional[bytes] = None):
        """Initialize with secret key for HMAC operations."""
        if secret_key is None:
            # Generate secure random key
            secret_key = secrets.token_bytes(32)
        self.secret_key = secret_key
        self._checksum_cache = {}
        self._cache_lock = Lock()

    def calculate_checksum(self, document: str) -> str:
        """
        Calculate SHA-256 checksum for document integrity.

        Args:
            document: Document content

        Returns:
            Hex-encoded SHA-256 checksum
        """
        if not document:
            return ""

        # Check cache
        with self._cache_lock:
            if document in self._checksum_cache:
                return self._checksum_cache[document]

        checksum = hashlib.sha256(document.encode("utf-8")).hexdigest()

        # Cache result
        with self._cache_lock:
            self._checksum_cache[document] = checksum
            # LRU eviction
            if len(self._checksum_cache) > 500:
                oldest = next(iter(self._checksum_cache))
                del self._checksum_cache[oldest]

        return checksum

    def sign_document(self, document: str, metadata: Optional[Dict] = None) -> str:
        """
        Create HMAC-SHA256 signature for document.

        Args:
            document: Document content
            metadata: Optional metadata to include in signature

        Returns:
            Base64-encoded signature
        """
        if not document:
            return ""

        # Combine document and metadata for signature
        sign_data = {
            "content": document,
            "checksum": self.calculate_checksum(document),
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }

        sign_bytes = json.dumps(sign_data, sort_keys=True).encode("utf-8")
        signature = hmac.new(self.secret_key, sign_bytes, hashlib.sha256).digest()

        return base64.b64encode(signature).decode("utf-8")

    def verify_signature(
        self, document: str, signature: str, metadata: Optional[Dict] = None
    ) -> bool:
        """
        Verify document signature.

        Args:
            document: Document content
            signature: Base64-encoded signature to verify
            metadata: Metadata used in signature

        Returns:
            True if signature is valid
        """
        try:
            expected_signature = self.sign_document(document, metadata)
            return hmac.compare_digest(signature, expected_signature)
        except Exception:
            return False

    def verify_checksum(self, document: str, expected_checksum: str) -> bool:
        """
        Verify document checksum.

        Args:
            document: Document content
            expected_checksum: Expected SHA-256 checksum

        Returns:
            True if checksum matches
        """
        actual_checksum = self.calculate_checksum(document)
        return hmac.compare_digest(actual_checksum, expected_checksum)


# ============================================================================
# Comprehensive Audit Logger
# ============================================================================


@dataclass
class AuditLogEntry:
    """Structured audit log entry."""

    timestamp: datetime
    event_type: AuditEvent
    severity: SecurityLevel
    user_id: Optional[str]
    session_id: Optional[str]
    ip_address: Optional[str]
    resource: Optional[str]
    action: str
    result: str
    details: Dict[str, Any]

    def to_json(self) -> str:
        """Convert to JSON for logging."""
        return json.dumps(
            {
                "timestamp": self.timestamp.isoformat(),
                "event_type": self.event_type.value,
                "severity": self.severity.value,
                "user_id": self.user_id,
                "session_id": self.session_id,
                "ip_address": self.ip_address,
                "resource": self.resource,
                "action": self.action,
                "result": self.result,
                "details": self.details,
            }
        )


class AuditLogger:
    """
    Comprehensive audit logging system for security events.
    Tracks all security-relevant operations with forensic detail.
    """

    def __init__(self, enable_encryption: bool = True):
        """Initialize audit logger with optional encryption."""
        self.enable_encryption = enable_encryption
        self._entries_buffer = deque(maxlen=10000)
        self._buffer_lock = Lock()

        if enable_encryption:
            # Generate encryption key for sensitive audit data
            salt = secrets.token_bytes(16)
            kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
            key = base64.urlsafe_b64encode(kdf.derive(b"audit-log-key"))
            self._cipher = Fernet(key)
        else:
            self._cipher = None

    def log(
        self,
        event_type: AuditEvent,
        severity: SecurityLevel,
        action: str,
        result: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[Dict] = None,
    ):
        """
        Log an audit event with comprehensive details.

        Args:
            event_type: Type of audit event
            severity: Security severity level
            action: Action performed
            result: Result of action (success/failure)
            user_id: User identifier
            session_id: Session identifier
            ip_address: Client IP address
            resource: Resource accessed
            details: Additional event details
        """
        entry = AuditLogEntry(
            timestamp=datetime.utcnow(),
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            resource=resource,
            action=action,
            result=result,
            details=details or {},
        )

        # Store in buffer
        with self._buffer_lock:
            self._entries_buffer.append(entry)

        # Log based on severity
        log_message = entry.to_json()

        if self.enable_encryption and severity in [
            SecurityLevel.CRITICAL,
            SecurityLevel.HIGH,
        ]:
            # Encrypt sensitive audit logs
            log_message = self._cipher.encrypt(log_message.encode()).decode()

        if severity == SecurityLevel.CRITICAL:
            audit_logger.critical(log_message)
        elif severity == SecurityLevel.HIGH:
            audit_logger.error(log_message)
        elif severity == SecurityLevel.MEDIUM:
            audit_logger.warning(log_message)
        else:
            audit_logger.info(log_message)

    def log_pii_detection(
        self,
        document_id: str,
        pii_summary: Dict[str, int],
        user_id: Optional[str] = None,
    ):
        """Log PII detection event."""
        self.log(
            event_type=AuditEvent.DOC_PII_DETECTED,
            severity=(
                SecurityLevel.HIGH
                if any(k in ["critical", "high"] for k in pii_summary)
                else SecurityLevel.MEDIUM
            ),
            action="PII detection",
            result="detected",
            user_id=user_id,
            resource=document_id,
            details={"pii_summary": pii_summary},
        )

    def log_rate_limit_violation(self, user_id: str, ip_address: str, limit: int, window: int):
        """Log rate limit violation."""
        self.log(
            event_type=AuditEvent.SEC_RATE_LIMIT_EXCEEDED,
            severity=SecurityLevel.MEDIUM,
            action="Rate limit check",
            result="exceeded",
            user_id=user_id,
            ip_address=ip_address,
            details={"limit": limit, "window_seconds": window},
        )

    def log_security_validation_failure(
        self, validation_type: str, reason: str, content_sample: str = None
    ):
        """Log security validation failure."""
        self.log(
            event_type=AuditEvent.SEC_VALIDATION_FAILED,
            severity=SecurityLevel.HIGH,
            action=f"Security validation: {validation_type}",
            result="failed",
            details={
                "validation_type": validation_type,
                "reason": reason,
                "content_sample": content_sample[:100] if content_sample else None,
            },
        )

    def get_recent_events(
        self, count: int = 100, event_type: Optional[AuditEvent] = None
    ) -> List[AuditLogEntry]:
        """Get recent audit events from buffer."""
        with self._buffer_lock:
            events = list(self._entries_buffer)

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        return events[-count:]


# ============================================================================
# Enhanced Rate Limiting and DOS Protection
# ============================================================================


class CircuitBreaker:
    """
    Circuit breaker pattern for DOS protection.
    Prevents cascading failures and resource exhaustion.
    """

    class State(Enum):
        CLOSED = "closed"  # Normal operation
        OPEN = "open"  # Blocking requests
        HALF_OPEN = "half_open"  # Testing recovery

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Failures before opening circuit
            recovery_timeout: Seconds before attempting recovery
            success_threshold: Successes needed to close circuit
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.state = self.State.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self._lock = Lock()

    def call(self, func, *args, **kwargs):
        """
        Execute function through circuit breaker.

        Args:
            func: Function to execute
            *args, **kwargs: Function arguments

        Returns:
            Function result

        Raises:
            ResourceLimitError: If circuit is open
        """
        with self._lock:
            if self.state == self.State.OPEN:
                if (
                    self.last_failure_time
                    and time.time() - self.last_failure_time > self.recovery_timeout
                ):
                    self.state = self.State.HALF_OPEN
                    self.success_count = 0
                else:
                    raise ResourceLimitError("Circuit breaker is open")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        """Handle successful call."""
        with self._lock:
            if self.state == self.State.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self.state = self.State.CLOSED
                    self.failure_count = 0
                    audit_logger.info(
                        f"Circuit breaker closed after {self.success_count} successes"
                    )
            elif self.state == self.State.CLOSED:
                self.failure_count = 0

    def _on_failure(self):
        """Handle failed call."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == self.State.HALF_OPEN:
                self.state = self.State.OPEN
                audit_logger.warning("Circuit breaker reopened after failure in half-open state")
            elif self.state == self.State.CLOSED and self.failure_count >= self.failure_threshold:
                self.state = self.State.OPEN
                audit_logger.error(f"Circuit breaker opened after {self.failure_count} failures")


class EnhancedRateLimiter:
    """
    Enhanced rate limiter with IP-based tracking and exponential backoff.
    """

    def __init__(
        self,
        max_calls: int = 100,
        window_seconds: int = 60,
        enable_backoff: bool = True,
    ):
        """
        Initialize enhanced rate limiter.

        Args:
            max_calls: Maximum calls per window
            window_seconds: Time window in seconds
            enable_backoff: Enable exponential backoff
        """
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.enable_backoff = enable_backoff

        self._calls = defaultdict(deque)
        self._violations = defaultdict(int)
        self._lock = Lock()

    def check_limit(self, identifier: str) -> bool:
        """
        Check if identifier has exceeded rate limit.

        Args:
            identifier: Unique identifier (user_id, IP, etc.)

        Returns:
            True if within limit, False if exceeded
        """
        with self._lock:
            now = time.time()

            # Clean old entries
            calls = self._calls[identifier]
            while calls and now - calls[0] > self.window_seconds:
                calls.popleft()

            # Check limit
            if len(calls) >= self.max_calls:
                self._violations[identifier] += 1

                # Apply exponential backoff
                if self.enable_backoff:
                    backoff_multiplier = min(2 ** self._violations[identifier], 32)
                    if len(calls) >= self.max_calls * backoff_multiplier:
                        return False

                return False

            # Record call
            calls.append(now)

            # Reset violations on successful call
            if identifier in self._violations:
                del self._violations[identifier]

            return True

    def get_remaining_calls(self, identifier: str) -> int:
        """Get remaining calls for identifier."""
        with self._lock:
            now = time.time()
            calls = self._calls[identifier]

            # Clean old entries
            while calls and now - calls[0] > self.window_seconds:
                calls.popleft()

            return max(0, self.max_calls - len(calls))

    def reset(self, identifier: str):
        """Reset rate limit for identifier."""
        with self._lock:
            if identifier in self._calls:
                del self._calls[identifier]
            if identifier in self._violations:
                del self._violations[identifier]


def enhanced_rate_limit(
    max_calls: int = 100,
    window_seconds: int = 60,
    identifier_func: Optional[callable] = None,
):
    """
    Enhanced rate limiting decorator with flexible identifier.

    Args:
        max_calls: Maximum calls per window
        window_seconds: Time window in seconds
        identifier_func: Function to extract identifier from args
    """
    limiter = EnhancedRateLimiter(max_calls, window_seconds)
    audit = AuditLogger()

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract identifier
            if identifier_func:
                identifier = identifier_func(*args, **kwargs)
            else:
                # Default to function name
                identifier = func.__name__

            # Check rate limit
            if not limiter.check_limit(identifier):
                remaining = limiter.get_remaining_calls(identifier)

                # Log violation
                audit.log_rate_limit_violation(
                    user_id=identifier,
                    ip_address=kwargs.get("ip_address", "unknown"),
                    limit=max_calls,
                    window=window_seconds,
                )

                raise ResourceLimitError(
                    f"Rate limit exceeded: {max_calls} calls per {window_seconds}s. "
                    f"Remaining: {remaining}"
                )

            return func(*args, **kwargs)

        return wrapper

    return decorator


# ============================================================================
# Authentication and Session Management
# ============================================================================


class AuthenticationManager:
    """
    Token-based authentication system using JWT.
    Implements secure session management.
    """

    def __init__(self, secret_key: Optional[str] = None, token_expiry_hours: int = 1):
        """
        Initialize authentication manager.

        Args:
            secret_key: Secret key for JWT signing
            token_expiry_hours: Token expiration time
        """
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.token_expiry = timedelta(hours=token_expiry_hours)
        self._sessions = {}
        self._lock = Lock()
        self.audit = AuditLogger()

    def generate_token(
        self,
        user_id: str,
        ip_address: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        Generate JWT token for user.

        Args:
            user_id: User identifier
            ip_address: Client IP address
            metadata: Additional token metadata

        Returns:
            JWT token string
        """
        now = datetime.utcnow()
        session_id = secrets.token_hex(16)

        payload = {
            "user_id": user_id,
            "session_id": session_id,
            "exp": now + self.token_expiry,
            "iat": now,
            "nbf": now,
            "jti": secrets.token_hex(16),
            "ip": ip_address,
            "metadata": metadata or {},
        }

        token = jwt.encode(payload, self.secret_key, algorithm="HS256")

        # Store session
        with self._lock:
            self._sessions[session_id] = {
                "user_id": user_id,
                "created": now,
                "last_activity": now,
                "ip_address": ip_address,
                "active": True,
            }

        # Audit log
        self.audit.log(
            event_type=AuditEvent.AUTH_TOKEN_GENERATED,
            severity=SecurityLevel.INFO,
            action="Generate token",
            result="success",
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
        )

        return token

    def validate_token(self, token: str, ip_address: Optional[str] = None) -> Optional[Dict]:
        """
        Validate JWT token.

        Args:
            token: JWT token to validate
            ip_address: Client IP to verify

        Returns:
            Token payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])

            # Verify IP if provided
            if ip_address and payload.get("ip") != ip_address:
                self.audit.log(
                    event_type=AuditEvent.SEC_UNAUTHORIZED_ACCESS,
                    severity=SecurityLevel.HIGH,
                    action="Token validation",
                    result="IP mismatch",
                    user_id=payload.get("user_id"),
                    ip_address=ip_address,
                    details={"expected_ip": payload.get("ip")},
                )
                return None

            # Check session
            session_id = payload.get("session_id")
            with self._lock:
                if session_id in self._sessions:
                    session = self._sessions[session_id]
                    if session["active"]:
                        session["last_activity"] = datetime.utcnow()
                        return payload

            return None

        except jwt.ExpiredSignatureError:
            self.audit.log(
                event_type=AuditEvent.AUTH_TOKEN_EXPIRED,
                severity=SecurityLevel.INFO,
                action="Token validation",
                result="expired",
            )
            return None
        except jwt.InvalidTokenError as e:
            self.audit.log(
                event_type=AuditEvent.SEC_VALIDATION_FAILED,
                severity=SecurityLevel.MEDIUM,
                action="Token validation",
                result="invalid",
                details={"error": str(e)},
            )
            return None

    def revoke_token(self, session_id: str):
        """Revoke a session/token."""
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id]["active"] = False

                self.audit.log(
                    event_type=AuditEvent.AUTH_SESSION_DESTROYED,
                    severity=SecurityLevel.INFO,
                    action="Revoke token",
                    result="success",
                    session_id=session_id,
                )

    def cleanup_expired_sessions(self):
        """Remove expired sessions."""
        with self._lock:
            now = datetime.utcnow()
            expired = []

            for session_id, session in self._sessions.items():
                if now - session["created"] > self.token_expiry:
                    expired.append(session_id)

            for session_id in expired:
                del self._sessions[session_id]


# ============================================================================
# Input Validation and Sanitization
# ============================================================================


class InputValidator:
    """
    Comprehensive input validation and sanitization.
    Prevents injection attacks and validates data types.
    """

    # Maximum sizes for different input types
    MAX_SIZES = {
        "document": 10 * 1024 * 1024,  # 10MB
        "prompt": 50000,  # 50K chars
        "metadata": 10000,  # 10K chars
        "identifier": 256,  # 256 chars
    }

    # Malicious patterns to detect
    MALICIOUS_PATTERNS = [
        # XSS patterns
        re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
        re.compile(r"javascript:", re.IGNORECASE),
        re.compile(r"on\w+\s*=", re.IGNORECASE),
        re.compile(r"<iframe[^>]*>", re.IGNORECASE),
        re.compile(r"<embed[^>]*>", re.IGNORECASE),
        re.compile(r"<object[^>]*>", re.IGNORECASE),
        # SQL injection patterns
        re.compile(r"(\bUNION\b.*\bSELECT\b|\bDROP\b.*\bTABLE\b)", re.IGNORECASE),
        re.compile(r"(;|\||--)\s*(DELETE|UPDATE|INSERT|DROP)", re.IGNORECASE),
        # Command injection patterns
        re.compile(r"[;&|`$].*?(rm|del|format|shutdown)", re.IGNORECASE),
        # Path traversal patterns
        re.compile(r"\.\.[/\\]"),
        re.compile(r"[/\\]\.\.[/\\]"),
        # Prompt injection patterns
        re.compile(r"(ignore|disregard|forget).*?(previous|above|prior)", re.IGNORECASE),
        re.compile(r"(system|assistant|human):\s*", re.IGNORECASE),
        re.compile(r"###\s*(instruction|command|directive)", re.IGNORECASE),
    ]

    @classmethod
    def validate_document(cls, document: str, max_size: Optional[int] = None) -> str:
        """
        Validate and sanitize document input.

        Args:
            document: Document content to validate
            max_size: Maximum allowed size

        Returns:
            Sanitized document

        Raises:
            SecurityValidationError: If validation fails
        """
        if not document:
            return ""

        if not isinstance(document, str):
            raise SecurityValidationError("Document must be a string")

        # Check size
        max_size = max_size or cls.MAX_SIZES["document"]
        if len(document.encode("utf-8")) > max_size:
            raise SecurityValidationError(f"Document exceeds {max_size} bytes")

        # Check for malicious patterns
        for pattern in cls.MALICIOUS_PATTERNS:
            if pattern.search(document):
                security_logger.warning(f"Malicious pattern detected: {pattern.pattern[:50]}")
                raise SecurityValidationError("Document contains potentially malicious content")

        # HTML escape
        return html.escape(document)

    @classmethod
    def validate_identifier(cls, identifier: str) -> str:
        """
        Validate identifier (user_id, session_id, etc.).

        Args:
            identifier: Identifier to validate

        Returns:
            Validated identifier

        Raises:
            SecurityValidationError: If validation fails
        """
        if not identifier:
            raise SecurityValidationError("Identifier cannot be empty")

        if not isinstance(identifier, str):
            raise SecurityValidationError("Identifier must be a string")

        # Check length
        if len(identifier) > cls.MAX_SIZES["identifier"]:
            raise SecurityValidationError(
                f"Identifier exceeds {cls.MAX_SIZES['identifier']} characters"
            )

        # Allow only alphanumeric, dash, underscore
        if not re.match(r"^[a-zA-Z0-9_-]+$", identifier):
            raise SecurityValidationError("Invalid identifier format")

        return identifier

    @classmethod
    def validate_metadata(cls, metadata: Dict) -> Dict:
        """
        Validate metadata dictionary.

        Args:
            metadata: Metadata to validate

        Returns:
            Validated metadata

        Raises:
            SecurityValidationError: If validation fails
        """
        if not metadata:
            return {}

        if not isinstance(metadata, dict):
            raise SecurityValidationError("Metadata must be a dictionary")

        # Check size
        metadata_str = json.dumps(metadata)
        if len(metadata_str) > cls.MAX_SIZES["metadata"]:
            raise SecurityValidationError(
                f"Metadata exceeds {cls.MAX_SIZES['metadata']} characters"
            )

        # Validate each value
        validated = {}
        for key, value in metadata.items():
            # Validate key
            if not isinstance(key, str) or not re.match(r"^[a-zA-Z0-9_-]+$", key):
                continue

            # Validate value (only allow basic types)
            if isinstance(value, (str, int, float, bool, type(None))):
                if isinstance(value, str):
                    value = html.escape(value[:1000])  # Limit string length
                validated[key] = value
            elif isinstance(value, (list, dict)):
                # Recursively validate nested structures (limited depth)
                try:
                    validated[key] = json.loads(json.dumps(value, default=str)[:1000])
                except:
                    pass

        return validated

    @classmethod
    def sanitize_for_llm(cls, content: str) -> str:
        """
        Sanitize content for LLM processing.

        Args:
            content: Content to sanitize

        Returns:
            Sanitized content safe for LLM
        """
        if not content:
            return ""

        # Remove prompt injection patterns
        sanitized = content

        # Replace dangerous patterns
        injection_patterns = [
            (
                r"(ignore|disregard|forget).*?(previous|above|prior)",
                "[INSTRUCTION REMOVED]",
            ),
            (r"(system|assistant|human):\s*", ""),
            (r"###\s*(instruction|command|directive)", "[DIRECTIVE REMOVED]"),
            (r"<\|.*?\|>", ""),  # Remove special tokens
        ]

        for pattern, replacement in injection_patterns:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

        # Limit length
        if len(sanitized) > cls.MAX_SIZES["prompt"]:
            sanitized = sanitized[: cls.MAX_SIZES["prompt"]] + "... [truncated]"

        return sanitized


# ============================================================================
# Security Exception Classes
# ============================================================================


class SecurityValidationError(Exception):
    """Raised when security validation fails."""

    pass


class ResourceLimitError(Exception):
    """Raised when resource limits are exceeded."""

    pass


class AuthenticationError(Exception):
    """Raised when authentication fails."""

    pass


class IntegrityError(Exception):
    """Raised when data integrity validation fails."""

    pass


# ============================================================================
# Utility Functions
# ============================================================================


def calculate_exponential_backoff(
    attempt: int, base_delay: float = 1.0, max_delay: float = 300.0
) -> float:
    """
    Calculate exponential backoff with jitter.

    Args:
        attempt: Current attempt number
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds

    Returns:
        Backoff delay in seconds
    """
    import random

    delay = min(base_delay * (2**attempt), max_delay)
    jitter = random.uniform(0, delay * 0.1)  # Add 10% jitter
    return delay + jitter


def validate_ip_address(ip: str) -> bool:
    """
    Validate IP address (IPv4 or IPv6).

    Args:
        ip: IP address string

    Returns:
        True if valid IP address
    """
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def generate_secure_token(length: int = 32) -> str:
    """
    Generate cryptographically secure random token.

    Args:
        length: Token length in bytes

    Returns:
        Hex-encoded token string
    """
    return secrets.token_hex(length)


def constant_time_compare(a: str, b: str) -> bool:
    """
    Constant-time string comparison to prevent timing attacks.

    Args:
        a, b: Strings to compare

    Returns:
        True if strings are equal
    """
    return hmac.compare_digest(a, b)
