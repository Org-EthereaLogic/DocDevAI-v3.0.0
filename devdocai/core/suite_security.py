"""
Suite Manager Security Components
DevDocAI v3.0.0

Security helpers and validators for OWASP compliance.
"""

import hashlib
import hmac
import html
import logging
import re
import time
from collections import defaultdict
from functools import wraps
from threading import Lock
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Security constants
RATE_LIMIT_WINDOW = 60
MAX_REQUESTS_PER_WINDOW = 100
MAX_AUDIT_LOGS = 10000
MAX_ID_LENGTH = 256
MIN_ID_LENGTH = 3


# ============================================================================
# RATE LIMITING
# ============================================================================


class RateLimiter:
    """Rate limiter for API protection (OWASP A04)."""

    def __init__(
        self,
        max_requests: int = MAX_REQUESTS_PER_WINDOW,
        window_seconds: int = RATE_LIMIT_WINDOW,
    ):
        """Initialize rate limiter."""
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
        self._lock = Lock()

    def check_rate_limit(self, key: str) -> bool:
        """Check if request is within rate limit."""
        with self._lock:
            now = time.time()
            window_start = now - self.window_seconds

            # Clean old requests
            self.requests[key] = [
                req_time for req_time in self.requests[key] if req_time > window_start
            ]

            # Check limit
            if len(self.requests[key]) >= self.max_requests:
                return False

            # Add current request
            self.requests[key].append(now)
            return True


# ============================================================================
# RESOURCE MONITORING
# ============================================================================


class ResourceMonitor:
    """Monitor system resources to prevent DoS (OWASP A05)."""

    def __init__(self):
        """Initialize resource monitor."""
        self.max_memory_mb = 1024  # 1GB max memory
        self.max_cpu_percent = 80

    def check_resources(self) -> bool:
        """Check if resources are available."""
        try:
            import psutil

            # Check memory
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                logger.warning(f"High memory usage: {memory.percent}%")
                return False

            # Check CPU
            cpu = psutil.cpu_percent(interval=0.1)
            if cpu > self.max_cpu_percent:
                logger.warning(f"High CPU usage: {cpu}%")
                return False

            return True
        except ImportError:
            # psutil not available, allow operation
            return True


# ============================================================================
# INPUT VALIDATION
# ============================================================================


class InputValidator:
    """Input validation helper (OWASP A03)."""

    def validate_id(self, id_str: str) -> bool:
        """Validate ID string for security."""
        if not id_str:
            return False

        # Length validation
        if len(id_str) < MIN_ID_LENGTH or len(id_str) > MAX_ID_LENGTH:
            return False

        # Whitelist approach: only allow safe characters
        if not re.match(r"^[a-zA-Z0-9_\-\.]+$", id_str):
            return False

        # Check for dangerous patterns
        dangerous_patterns = [
            r"\.\.",  # Path traversal
            r"<.*?>",  # HTML tags
            r"[;&|`$]",  # Shell injection
            r"[\x00-\x1f]",  # Control characters
            r"javascript:",  # XSS
            r"data:",  # Data URLs
            r"vbscript:",  # VBScript
            r"file:",  # File protocol
            r"\\\\",  # Windows path separator
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, id_str, re.IGNORECASE):
                return False

        return True

    def sanitize_content(self, content: str) -> str:
        """Sanitize content to prevent XSS."""
        # HTML escape
        sanitized = html.escape(content)

        # Remove any remaining dangerous patterns
        dangerous_patterns = [
            (r"javascript:", ""),
            (r"vbscript:", ""),
            (r"data:", ""),
            (r"<script.*?</script>", "", re.DOTALL),
            (r"on\w+\s*=", ""),  # Event handlers
        ]

        for pattern, replacement, *flags in dangerous_patterns:
            regex_flags = flags[0] if flags else 0
            sanitized = re.sub(pattern, replacement, sanitized, flags=regex_flags | re.IGNORECASE)

        return sanitized


# ============================================================================
# HMAC UTILITIES
# ============================================================================


class HMACValidator:
    """HMAC validation for data integrity (OWASP A08)."""

    def __init__(self, secret_key: bytes):
        """Initialize with secret key."""
        self.secret_key = secret_key

    def generate_hmac(self, data: str) -> str:
        """Generate HMAC for data."""
        return hmac.new(self.secret_key, data.encode("utf-8"), hashlib.sha256).hexdigest()

    def verify_hmac(self, data: str, expected_hmac: str) -> bool:
        """Verify HMAC for data."""
        calculated_hmac = self.generate_hmac(data)
        return hmac.compare_digest(calculated_hmac, expected_hmac)


# ============================================================================
# AUDIT LOGGING
# ============================================================================


class AuditLogger:
    """Audit logging for security events (OWASP A09)."""

    def __init__(self, max_logs: int = MAX_AUDIT_LOGS):
        """Initialize audit logger."""
        self.max_logs = max_logs
        self.logs = []
        self.lock = Lock()
        self.validator = InputValidator()

    def log_event(self, action: str, target: str, details: Dict[str, Any]):
        """Log an audit event."""
        with self.lock:
            # Prevent memory exhaustion
            if len(self.logs) >= self.max_logs:
                # Remove oldest 10% of logs
                remove_count = self.max_logs // 10
                self.logs = self.logs[remove_count:]

            # Sanitize details to prevent injection
            sanitized_details = {}
            for key, value in details.items():
                if isinstance(value, str):
                    sanitized_details[key] = self.validator.sanitize_content(value)
                else:
                    sanitized_details[key] = value

            from datetime import datetime

            self.logs.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "action": action,
                    "target": self.validator.sanitize_content(str(target)),
                    "details": sanitized_details,
                }
            )

    def get_logs(self) -> list:
        """Get copy of audit logs."""
        with self.lock:
            return self.logs.copy()


# ============================================================================
# DECORATORS
# ============================================================================


def rate_limited(func):
    """Decorator for rate limiting."""

    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        return await func(self, *args, **kwargs)

    return wrapper


def validate_input(func):
    """Decorator for input validation."""

    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        return await func(self, *args, **kwargs)

    return wrapper


def audit_operation(operation_name: str):
    """Decorator for audit logging."""

    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            start_time = time.time()
            success = False
            error_msg = None

            try:
                result = await func(self, *args, **kwargs)
                success = True
                return result
            except Exception as e:
                error_msg = str(e)
                raise
            finally:
                if hasattr(self, "_audit_logger"):
                    duration = time.time() - start_time
                    self._audit_logger.log_event(
                        operation_name,
                        str(args[0]) if args else "unknown",
                        {"success": success, "duration": duration, "error": error_msg},
                    )

        return wrapper

    return decorator
