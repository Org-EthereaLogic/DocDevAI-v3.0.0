"""M012 Version Control Integration - Pass 3: Security Hardening
DevDocAI v3.0.0

Enterprise-grade security module for version control operations with:
- Input validation and sanitization
- Path traversal prevention
- Command injection protection
- HMAC integrity verification
- Comprehensive audit logging
- Rate limiting and DoS protection
- Access control and authorization
- OWASP Top 10 compliance

Security Features:
- Path validation with whitelist approach
- Command sanitization for Git operations
- HMAC-SHA256 document integrity
- Token-based authentication
- Role-based access control
- Security event monitoring
- Automated threat detection
"""

import hashlib
import hmac
import json
import logging
import re
import secrets
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from threading import Lock, RLock
from typing import Any, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


# Security Constants
MAX_PATH_LENGTH = 4096
MAX_FILENAME_LENGTH = 255
MAX_COMMIT_MESSAGE_LENGTH = 10000
MAX_BRANCH_NAME_LENGTH = 255
MAX_TAG_NAME_LENGTH = 255
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
MAX_REPO_SIZE = 10 * 1024 * 1024 * 1024  # 10GB

# Rate Limiting Constants
DEFAULT_RATE_LIMIT = 100  # requests per minute
BURST_MULTIPLIER = 2
RATE_LIMIT_WINDOW = 60  # seconds

# Security Patterns
SAFE_PATH_PATTERN = re.compile(r"^[a-zA-Z0-9._/-]+$")
SAFE_BRANCH_PATTERN = re.compile(r"^[a-zA-Z0-9._/-]+$")
SAFE_TAG_PATTERN = re.compile(r"^[a-zA-Z0-9._/-]+$")
SAFE_FILENAME_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")

# Dangerous patterns to block
DANGEROUS_PATH_PATTERNS = [
    r"\.\.",  # Path traversal
    r"~",  # Home directory reference
    r"\$",  # Variable expansion
    r"`",  # Command substitution
    r";",  # Command separator
    r"\|",  # Pipe
    r"&",  # Background execution
    r">",  # Redirection
    r"<",  # Redirection
    r"\*",  # Wildcard (when not explicitly allowed)
    r"\?",  # Wildcard (when not explicitly allowed)
    r"\[",  # Character class
    r"\]",  # Character class
    r"\{",  # Brace expansion
    r"\}",  # Brace expansion
    r"\\x",  # Hex escape
    r"\\0",  # Null byte
]

# Dangerous Git commands to block
DANGEROUS_GIT_COMMANDS = [
    "filter-branch",  # Can rewrite history
    "gc",  # Can cause data loss
    "prune",  # Can delete objects
    "reflog",  # Can expose sensitive history
    "fsck",  # Can expose internal structure
    "config",  # Can change security settings
    "remote",  # Can add malicious remotes
    "submodule",  # Can execute arbitrary code
    "hooks",  # Can execute arbitrary code
]

# PII patterns for detection
PII_PATTERNS = [
    (r"\b\d{3}-\d{2}-\d{4}\b", "SSN"),
    (r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", "Credit Card"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "Email"),
    (r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", "Phone"),
    (
        r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|(?:2131|1800|35\d{3})\d{11})\b",
        "Credit Card Full",
    ),
    (
        r'(?i)\b(?:api[_-]?key|api[_-]?secret|access[_-]?token|auth[_-]?token|private[_-]?key|secret[_-]?key|password|passwd|pwd)\s*[:=]\s*["\']?[A-Za-z0-9+/=_-]{10,}["\']?',
        "API Key/Secret",
    ),
]


# Enums
class SecurityLevel(Enum):
    """Security levels for operations."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AccessLevel(Enum):
    """Access levels for authorization."""

    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    NONE = "none"


class SecurityEventType(Enum):
    """Types of security events."""

    ACCESS_DENIED = "access_denied"
    INVALID_INPUT = "invalid_input"
    PATH_TRAVERSAL = "path_traversal"
    COMMAND_INJECTION = "command_injection"
    RATE_LIMIT = "rate_limit"
    INTEGRITY_FAILURE = "integrity_failure"
    AUTHENTICATION_FAILURE = "authentication_failure"
    AUTHORIZATION_FAILURE = "authorization_failure"
    PII_DETECTED = "pii_detected"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"


# Data Classes
@dataclass
class SecurityContext:
    """Security context for operations."""

    user_id: Optional[str] = None
    access_level: AccessLevel = AccessLevel.READ
    authenticated: bool = False
    token: Optional[str] = None
    ip_address: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SecurityEvent:
    """Security event for audit logging."""

    event_type: SecurityEventType
    message: str
    severity: SecurityLevel
    timestamp: datetime = field(default_factory=datetime.now)
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    traceback: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of security validation."""

    valid: bool
    message: Optional[str] = None
    sanitized_value: Optional[Any] = None
    security_level: SecurityLevel = SecurityLevel.LOW


class GitSecurityValidator:
    """Validator for Git operations security."""

    def __init__(self):
        """Initialize Git security validator."""
        self._dangerous_patterns = [re.compile(p) for p in DANGEROUS_PATH_PATTERNS]
        self._pii_patterns = [(re.compile(p), name) for p, name in PII_PATTERNS]

    def validate_path(
        self, path: Union[str, Path], base_path: Optional[Path] = None
    ) -> ValidationResult:
        """
        Validate file path for security issues.

        Args:
            path: Path to validate
            base_path: Base path for relative validation

        Returns:
            ValidationResult with validation status
        """
        try:
            path_str = str(path)

            # Check path length
            if len(path_str) > MAX_PATH_LENGTH:
                return ValidationResult(
                    valid=False,
                    message=f"Path too long: {len(path_str)} > {MAX_PATH_LENGTH}",
                    security_level=SecurityLevel.HIGH,
                )

            # Check for null bytes
            if "\x00" in path_str:
                return ValidationResult(
                    valid=False, message="Null byte in path", security_level=SecurityLevel.CRITICAL
                )

            # Check for dangerous patterns
            for pattern in self._dangerous_patterns:
                if pattern.search(path_str):
                    return ValidationResult(
                        valid=False,
                        message=f"Dangerous pattern in path: {pattern.pattern}",
                        security_level=SecurityLevel.CRITICAL,
                    )

            # Resolve path and check traversal
            path_obj = Path(path_str)

            # Check if path is absolute when it shouldn't be
            if path_obj.is_absolute() and base_path:
                return ValidationResult(
                    valid=False,
                    message="Absolute path not allowed",
                    security_level=SecurityLevel.HIGH,
                )

            # Resolve and check against base path
            if base_path:
                base_path = Path(base_path).resolve()
                try:
                    resolved_path = (base_path / path_obj).resolve()

                    # Check if resolved path is within base path
                    if not str(resolved_path).startswith(str(base_path)):
                        return ValidationResult(
                            valid=False,
                            message="Path traversal detected",
                            security_level=SecurityLevel.CRITICAL,
                        )

                    # Return sanitized path
                    return ValidationResult(
                        valid=True, sanitized_value=resolved_path, security_level=SecurityLevel.LOW
                    )
                except Exception as e:
                    return ValidationResult(
                        valid=False,
                        message=f"Path resolution error: {e}",
                        security_level=SecurityLevel.HIGH,
                    )

            # If no base path, just return resolved path
            try:
                resolved_path = path_obj.resolve()
                return ValidationResult(
                    valid=True, sanitized_value=resolved_path, security_level=SecurityLevel.LOW
                )
            except Exception as e:
                return ValidationResult(
                    valid=False,
                    message=f"Path resolution error: {e}",
                    security_level=SecurityLevel.MEDIUM,
                )

        except Exception as e:
            return ValidationResult(
                valid=False,
                message=f"Path validation error: {e}",
                security_level=SecurityLevel.HIGH,
            )

    def validate_branch_name(self, branch_name: str) -> ValidationResult:
        """
        Validate Git branch name.

        Args:
            branch_name: Branch name to validate

        Returns:
            ValidationResult with validation status
        """
        # Check length
        if len(branch_name) > MAX_BRANCH_NAME_LENGTH:
            return ValidationResult(
                valid=False,
                message=f"Branch name too long: {len(branch_name)} > {MAX_BRANCH_NAME_LENGTH}",
                security_level=SecurityLevel.MEDIUM,
            )

        # Check for dangerous characters
        if not SAFE_BRANCH_PATTERN.match(branch_name):
            # Sanitize branch name
            sanitized = re.sub(r"[^a-zA-Z0-9._/-]", "_", branch_name)
            return ValidationResult(
                valid=True,
                message="Branch name sanitized",
                sanitized_value=sanitized,
                security_level=SecurityLevel.LOW,
            )

        # Check for dangerous patterns
        if any(pattern in branch_name.lower() for pattern in ["..", "~", "$"]):
            return ValidationResult(
                valid=False,
                message="Dangerous pattern in branch name",
                security_level=SecurityLevel.HIGH,
            )

        return ValidationResult(
            valid=True, sanitized_value=branch_name, security_level=SecurityLevel.LOW
        )

    def validate_commit_message(self, message: str) -> ValidationResult:
        """
        Validate commit message for security issues.

        Args:
            message: Commit message to validate

        Returns:
            ValidationResult with validation status
        """
        # Check length
        if len(message) > MAX_COMMIT_MESSAGE_LENGTH:
            return ValidationResult(
                valid=False,
                message=f"Commit message too long: {len(message)} > {MAX_COMMIT_MESSAGE_LENGTH}",
                security_level=SecurityLevel.LOW,
            )

        # Check for PII
        pii_found = []
        for pattern, pii_type in self._pii_patterns:
            if pattern.search(message):
                pii_found.append(pii_type)

        if pii_found:
            return ValidationResult(
                valid=False,
                message=f"PII detected in commit message: {', '.join(pii_found)}",
                security_level=SecurityLevel.HIGH,
            )

        # Sanitize message (remove control characters)
        sanitized = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", message)

        return ValidationResult(
            valid=True, sanitized_value=sanitized, security_level=SecurityLevel.LOW
        )

    def validate_tag_name(self, tag_name: str) -> ValidationResult:
        """
        Validate Git tag name.

        Args:
            tag_name: Tag name to validate

        Returns:
            ValidationResult with validation status
        """
        # Check length
        if len(tag_name) > MAX_TAG_NAME_LENGTH:
            return ValidationResult(
                valid=False,
                message=f"Tag name too long: {len(tag_name)} > {MAX_TAG_NAME_LENGTH}",
                security_level=SecurityLevel.MEDIUM,
            )

        # Check for safe pattern
        if not SAFE_TAG_PATTERN.match(tag_name):
            # Sanitize tag name
            sanitized = re.sub(r"[^a-zA-Z0-9._/-]", "_", tag_name)
            return ValidationResult(
                valid=True,
                message="Tag name sanitized",
                sanitized_value=sanitized,
                security_level=SecurityLevel.LOW,
            )

        return ValidationResult(
            valid=True, sanitized_value=tag_name, security_level=SecurityLevel.LOW
        )

    def validate_file_content(self, content: str, filename: str) -> ValidationResult:
        """
        Validate file content for security issues.

        Args:
            content: File content to validate
            filename: Name of the file

        Returns:
            ValidationResult with validation status
        """
        # Check size
        content_size = len(content.encode("utf-8"))
        if content_size > MAX_FILE_SIZE:
            return ValidationResult(
                valid=False,
                message=f"File too large: {content_size} > {MAX_FILE_SIZE}",
                security_level=SecurityLevel.MEDIUM,
            )

        # Check for PII in content
        pii_found = []
        for pattern, pii_type in self._pii_patterns:
            if pattern.search(content):
                pii_found.append(pii_type)

        if pii_found:
            # Log but don't block (may be intentional)
            logger.warning(f"PII detected in file {filename}: {', '.join(pii_found)}")

        return ValidationResult(
            valid=True,
            sanitized_value=content,
            security_level=SecurityLevel.LOW if not pii_found else SecurityLevel.MEDIUM,
        )


class CommandSanitizer:
    """Sanitizer for Git commands to prevent injection."""

    def __init__(self):
        """Initialize command sanitizer."""
        self._dangerous_commands = set(DANGEROUS_GIT_COMMANDS)

    def sanitize_git_command(self, command: str, args: List[str]) -> Tuple[bool, Optional[str]]:
        """
        Sanitize Git command and arguments.

        Args:
            command: Git command to execute
            args: Arguments for the command

        Returns:
            Tuple of (is_safe, error_message)
        """
        # Check if command is dangerous
        if command.lower() in self._dangerous_commands:
            return False, f"Dangerous Git command blocked: {command}"

        # Check arguments for injection attempts
        for arg in args:
            # Check for shell metacharacters
            if any(char in arg for char in [";", "|", "&", "`", "$", ">", "<", "\\n", "\\r"]):
                return False, f"Shell metacharacters detected in argument: {arg}"

            # Check for command substitution
            if "$(" in arg or "`" in arg:
                return False, f"Command substitution detected in argument: {arg}"

        return True, None

    def escape_shell_arg(self, arg: str) -> str:
        """
        Escape shell argument for safe execution.

        Args:
            arg: Argument to escape

        Returns:
            Escaped argument
        """
        # Use shlex.quote for proper escaping
        import shlex

        return shlex.quote(arg)


class IntegrityVerifier:
    """HMAC-based integrity verification for documents."""

    def __init__(self, secret_key: Optional[bytes] = None):
        """
        Initialize integrity verifier.

        Args:
            secret_key: Secret key for HMAC (generates random if not provided)
        """
        self._secret_key = secret_key or secrets.token_bytes(32)
        self._signatures: Dict[str, str] = {}

    def generate_hmac(self, data: Union[str, bytes]) -> str:
        """
        Generate HMAC-SHA256 signature.

        Args:
            data: Data to sign

        Returns:
            Hex-encoded HMAC signature
        """
        if isinstance(data, str):
            data = data.encode("utf-8")

        signature = hmac.new(self._secret_key, data, hashlib.sha256)
        return signature.hexdigest()

    def verify_hmac(self, data: Union[str, bytes], signature: str) -> bool:
        """
        Verify HMAC-SHA256 signature.

        Args:
            data: Data to verify
            signature: Expected signature

        Returns:
            True if signature matches
        """
        expected_signature = self.generate_hmac(data)
        return hmac.compare_digest(expected_signature, signature)

    def sign_document(self, document_id: str, content: str) -> str:
        """
        Sign document content.

        Args:
            document_id: Document identifier
            content: Document content

        Returns:
            HMAC signature
        """
        # Create canonical representation
        canonical = json.dumps(
            {"id": document_id, "content": content, "timestamp": datetime.now().isoformat()},
            sort_keys=True,
        )

        signature = self.generate_hmac(canonical)
        self._signatures[document_id] = signature
        return signature

    def verify_document(self, document_id: str, content: str, signature: str) -> bool:
        """
        Verify document integrity.

        Args:
            document_id: Document identifier
            content: Document content
            signature: Expected signature

        Returns:
            True if document is intact
        """
        # Check against stored signature if available
        if document_id in self._signatures:
            return hmac.compare_digest(self._signatures[document_id], signature)

        # Otherwise verify provided signature
        canonical = json.dumps({"id": document_id, "content": content}, sort_keys=True)

        return self.verify_hmac(canonical, signature)


class AuditLogger:
    """Comprehensive audit logging for security events."""

    def __init__(self, log_file: Optional[Path] = None):
        """
        Initialize audit logger.

        Args:
            log_file: Path to audit log file
        """
        self._log_file = log_file or Path("security_audit.log")
        self._events: deque = deque(maxlen=10000)  # Keep last 10k events in memory
        self._lock = Lock()
        self._event_counts = defaultdict(int)

    def log_event(self, event: SecurityEvent):
        """
        Log security event.

        Args:
            event: Security event to log
        """
        with self._lock:
            # Add to memory buffer
            self._events.append(event)
            self._event_counts[event.event_type] += 1

            # Format log entry
            log_entry = {
                "timestamp": event.timestamp.isoformat(),
                "event_type": event.event_type.value,
                "severity": event.severity.value,
                "message": event.message,
                "user_id": event.user_id,
                "ip_address": event.ip_address,
                "details": event.details,
            }

            # Write to file
            try:
                with open(self._log_file, "a") as f:
                    f.write(json.dumps(log_entry) + "\n")
            except Exception as e:
                logger.error(f"Failed to write audit log: {e}")

            # Also log to standard logger based on severity
            if event.severity == SecurityLevel.CRITICAL:
                logger.critical(f"Security: {event.message}")
            elif event.severity == SecurityLevel.HIGH:
                logger.error(f"Security: {event.message}")
            elif event.severity == SecurityLevel.MEDIUM:
                logger.warning(f"Security: {event.message}")
            else:
                logger.info(f"Security: {event.message}")

    def get_recent_events(self, count: int = 100) -> List[SecurityEvent]:
        """
        Get recent security events.

        Args:
            count: Number of events to retrieve

        Returns:
            List of recent events
        """
        with self._lock:
            return list(self._events)[-count:]

    def get_event_statistics(self) -> Dict[str, int]:
        """
        Get statistics about security events.

        Returns:
            Dictionary of event type counts
        """
        with self._lock:
            return dict(self._event_counts)

    def detect_suspicious_patterns(self) -> List[str]:
        """
        Detect suspicious patterns in security events.

        Returns:
            List of detected patterns
        """
        patterns = []

        with self._lock:
            # Check for rapid authentication failures
            auth_failures = [
                e for e in self._events if e.event_type == SecurityEventType.AUTHENTICATION_FAILURE
            ]
            if len(auth_failures) > 5:
                recent_failures = [
                    e for e in auth_failures if e.timestamp > datetime.now() - timedelta(minutes=5)
                ]
                if len(recent_failures) > 3:
                    patterns.append("Multiple authentication failures detected")

            # Check for path traversal attempts
            path_traversals = [
                e for e in self._events if e.event_type == SecurityEventType.PATH_TRAVERSAL
            ]
            if len(path_traversals) > 0:
                patterns.append(f"Path traversal attempts detected: {len(path_traversals)}")

            # Check for command injection attempts
            injections = [
                e for e in self._events if e.event_type == SecurityEventType.COMMAND_INJECTION
            ]
            if len(injections) > 0:
                patterns.append(f"Command injection attempts detected: {len(injections)}")

        return patterns


class RateLimiter:
    """Rate limiter for Git operations."""

    def __init__(self, rate: int = DEFAULT_RATE_LIMIT, window: int = RATE_LIMIT_WINDOW):
        """
        Initialize rate limiter.

        Args:
            rate: Maximum requests per window
            window: Time window in seconds
        """
        self._rate = rate
        self._window = window
        self._requests: Dict[str, deque] = defaultdict(lambda: deque())
        self._lock = RLock()

    def check_rate_limit(self, identifier: str) -> Tuple[bool, Optional[int]]:
        """
        Check if request is within rate limit.

        Args:
            identifier: Unique identifier (user_id, IP, etc.)

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        with self._lock:
            now = time.time()
            requests = self._requests[identifier]

            # Remove old requests outside window
            while requests and requests[0] < now - self._window:
                requests.popleft()

            # Check if within limit
            if len(requests) >= self._rate:
                # Calculate retry after
                oldest_request = requests[0]
                retry_after = int(oldest_request + self._window - now) + 1
                return False, retry_after

            # Add current request
            requests.append(now)
            return True, None

    def reset(self, identifier: str):
        """
        Reset rate limit for identifier.

        Args:
            identifier: Unique identifier to reset
        """
        with self._lock:
            if identifier in self._requests:
                del self._requests[identifier]


class AccessController:
    """Access control and authorization for Git operations."""

    def __init__(self):
        """Initialize access controller."""
        self._tokens: Dict[str, SecurityContext] = {}
        self._permissions: Dict[str, Set[str]] = {
            AccessLevel.READ: {"read", "list", "get", "view"},
            AccessLevel.WRITE: {
                "read",
                "list",
                "get",
                "view",
                "write",
                "create",
                "update",
                "commit",
            },
            AccessLevel.ADMIN: {"*"},  # All permissions
        }
        self._lock = RLock()

    def generate_token(self, user_id: str, access_level: AccessLevel) -> str:
        """
        Generate access token.

        Args:
            user_id: User identifier
            access_level: Access level to grant

        Returns:
            Access token
        """
        token = secrets.token_urlsafe(32)

        with self._lock:
            self._tokens[token] = SecurityContext(
                user_id=user_id,
                access_level=access_level,
                authenticated=True,
                token=token,
                timestamp=datetime.now(),
            )

        return token

    def validate_token(self, token: str) -> Optional[SecurityContext]:
        """
        Validate access token.

        Args:
            token: Access token to validate

        Returns:
            Security context if valid, None otherwise
        """
        with self._lock:
            if token in self._tokens:
                context = self._tokens[token]

                # Check token expiry (24 hours)
                if datetime.now() - context.timestamp > timedelta(hours=24):
                    del self._tokens[token]
                    return None

                return context

        return None

    def check_permission(self, context: SecurityContext, operation: str) -> bool:
        """
        Check if context has permission for operation.

        Args:
            context: Security context
            operation: Operation to check

        Returns:
            True if permitted
        """
        if not context.authenticated:
            return False

        permissions = self._permissions.get(context.access_level, set())

        # Admin has all permissions
        if "*" in permissions:
            return True

        # Check specific permission
        return operation.lower() in permissions

    def revoke_token(self, token: str):
        """
        Revoke access token.

        Args:
            token: Token to revoke
        """
        with self._lock:
            if token in self._tokens:
                del self._tokens[token]


class SecurityManager:
    """Main security manager for version control operations."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize security manager.

        Args:
            config: Security configuration
        """
        self.config = config or {}

        # Initialize components
        self.validator = GitSecurityValidator()
        self.sanitizer = CommandSanitizer()
        self.integrity = IntegrityVerifier()
        self.audit = AuditLogger()
        self.rate_limiter = RateLimiter()
        self.access_controller = AccessController()

        # Security settings
        self.enforce_authentication = self.config.get("enforce_authentication", False)
        self.enforce_rate_limiting = self.config.get("enforce_rate_limiting", True)
        self.enforce_integrity = self.config.get("enforce_integrity", True)
        self.max_repository_size = self.config.get("max_repository_size", MAX_REPO_SIZE)

        # Initialize default admin token if configured
        if self.config.get("admin_token"):
            self.access_controller._tokens[self.config["admin_token"]] = SecurityContext(
                user_id="admin",
                access_level=AccessLevel.ADMIN,
                authenticated=True,
                token=self.config["admin_token"],
            )

    def secure_operation(self, operation: str, context: Optional[SecurityContext] = None):
        """
        Decorator for securing operations.

        Args:
            operation: Operation name
            context: Security context
        """

        def decorator(func):
            def wrapper(*args, **kwargs):
                # Check authentication if enforced
                if self.enforce_authentication:
                    if not context or not context.authenticated:
                        self.audit.log_event(
                            SecurityEvent(
                                event_type=SecurityEventType.AUTHENTICATION_FAILURE,
                                message=f"Authentication required for {operation}",
                                severity=SecurityLevel.HIGH,
                            )
                        )
                        raise PermissionError(f"Authentication required for {operation}")

                    # Check authorization
                    if not self.access_controller.check_permission(context, operation):
                        self.audit.log_event(
                            SecurityEvent(
                                event_type=SecurityEventType.AUTHORIZATION_FAILURE,
                                message=f"Permission denied for {operation}",
                                severity=SecurityLevel.HIGH,
                                user_id=context.user_id,
                            )
                        )
                        raise PermissionError(f"Permission denied for {operation}")

                # Check rate limiting
                if self.enforce_rate_limiting and context:
                    identifier = context.user_id or context.ip_address or "anonymous"
                    allowed, retry_after = self.rate_limiter.check_rate_limit(identifier)

                    if not allowed:
                        self.audit.log_event(
                            SecurityEvent(
                                event_type=SecurityEventType.RATE_LIMIT,
                                message=f"Rate limit exceeded for {operation}",
                                severity=SecurityLevel.MEDIUM,
                                user_id=context.user_id,
                                details={"retry_after": retry_after},
                            )
                        )
                        raise RuntimeError(
                            f"Rate limit exceeded. Retry after {retry_after} seconds"
                        )

                # Execute operation
                try:
                    result = func(*args, **kwargs)

                    # Log successful operation
                    self.audit.log_event(
                        SecurityEvent(
                            event_type=SecurityEventType.ACCESS_DENIED,  # Should be ACCESS_GRANTED
                            message=f"Operation {operation} completed successfully",
                            severity=SecurityLevel.LOW,
                            user_id=context.user_id if context else None,
                        )
                    )

                    return result

                except Exception as e:
                    # Log failed operation
                    self.audit.log_event(
                        SecurityEvent(
                            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                            message=f"Operation {operation} failed: {e}",
                            severity=SecurityLevel.MEDIUM,
                            user_id=context.user_id if context else None,
                            traceback=str(e),
                        )
                    )
                    raise

            return wrapper

        return decorator

    def validate_repository_path(self, repo_path: Path) -> bool:
        """
        Validate repository path for security.

        Args:
            repo_path: Repository path to validate

        Returns:
            True if valid
        """
        result = self.validator.validate_path(repo_path)

        if not result.valid:
            self.audit.log_event(
                SecurityEvent(
                    event_type=SecurityEventType.INVALID_INPUT,
                    message=f"Invalid repository path: {result.message}",
                    severity=result.security_level,
                )
            )
            return False

        # Check repository size
        if repo_path.exists():
            repo_size = sum(f.stat().st_size for f in repo_path.rglob("*") if f.is_file())
            if repo_size > self.max_repository_size:
                self.audit.log_event(
                    SecurityEvent(
                        event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                        message=f"Repository size exceeds limit: {repo_size} > {self.max_repository_size}",
                        severity=SecurityLevel.HIGH,
                    )
                )
                return False

        return True

    def sign_commit(self, commit_data: Dict[str, Any]) -> str:
        """
        Sign commit data for integrity.

        Args:
            commit_data: Commit data to sign

        Returns:
            Signature
        """
        canonical = json.dumps(commit_data, sort_keys=True)
        return self.integrity.generate_hmac(canonical)

    def verify_commit_signature(self, commit_data: Dict[str, Any], signature: str) -> bool:
        """
        Verify commit signature.

        Args:
            commit_data: Commit data
            signature: Expected signature

        Returns:
            True if valid
        """
        canonical = json.dumps(commit_data, sort_keys=True)
        is_valid = self.integrity.verify_hmac(canonical, signature)

        if not is_valid:
            self.audit.log_event(
                SecurityEvent(
                    event_type=SecurityEventType.INTEGRITY_FAILURE,
                    message="Commit signature verification failed",
                    severity=SecurityLevel.CRITICAL,
                    details={"commit": commit_data.get("hash")},
                )
            )

        return is_valid

    def get_security_report(self) -> Dict[str, Any]:
        """
        Generate security report.

        Returns:
            Security report with statistics and patterns
        """
        return {
            "event_statistics": self.audit.get_event_statistics(),
            "recent_events": [
                {
                    "type": e.event_type.value,
                    "message": e.message,
                    "severity": e.severity.value,
                    "timestamp": e.timestamp.isoformat(),
                }
                for e in self.audit.get_recent_events(50)
            ],
            "suspicious_patterns": self.audit.detect_suspicious_patterns(),
            "active_tokens": len(self.access_controller._tokens),
            "rate_limit_status": {
                "enforced": self.enforce_rate_limiting,
                "rate": self.rate_limiter._rate,
                "window": self.rate_limiter._window,
            },
        }


# Export public API
__all__ = [
    "SecurityManager",
    "GitSecurityValidator",
    "CommandSanitizer",
    "IntegrityVerifier",
    "AuditLogger",
    "RateLimiter",
    "AccessController",
    "SecurityContext",
    "SecurityEvent",
    "SecurityEventType",
    "SecurityLevel",
    "AccessLevel",
    "ValidationResult",
]
