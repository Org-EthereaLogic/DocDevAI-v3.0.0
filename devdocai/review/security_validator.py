"""
Security Validator for M007 Review Engine.

Implements comprehensive security validation, input sanitization,
rate limiting, and OWASP Top 10 protections.
"""

import re
import os
import hashlib
import secrets
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime, timedelta
from collections import defaultdict, deque
from functools import wraps
from dataclasses import dataclass, field
from enum import Enum
import json
import bleach
import html
from urllib.parse import urlparse, quote
import asyncio
from contextlib import contextmanager

# Security constants
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10MB
MAX_PATH_LENGTH = 255
MAX_FIELD_LENGTH = 1024
MAX_ARRAY_SIZE = 1000
MAX_RECURSION_DEPTH = 10
RATE_LIMIT_WINDOW = 60  # seconds
MAX_REQUESTS_PER_WINDOW = 100
MAX_BURST_SIZE = 20

# Regex timeout protection
REGEX_TIMEOUT = 2.0  # seconds

logger = logging.getLogger(__name__)


class SecurityThreat(Enum):
    """Types of security threats."""
    SQL_INJECTION = "sql_injection"
    XSS = "cross_site_scripting"
    PATH_TRAVERSAL = "path_traversal"
    COMMAND_INJECTION = "command_injection"
    XXE = "xml_external_entity"
    SSRF = "server_side_request_forgery"
    LDAP_INJECTION = "ldap_injection"
    REGEX_DOS = "regex_denial_of_service"
    BUFFER_OVERFLOW = "buffer_overflow"
    INSECURE_DESERIALIZATION = "insecure_deserialization"
    HARDCODED_SECRETS = "hardcoded_secrets"
    WEAK_CRYPTO = "weak_cryptography"
    RACE_CONDITION = "race_condition"
    FILE_UPLOAD = "malicious_file_upload"


@dataclass
class ValidationResult:
    """Result of security validation."""
    is_valid: bool
    sanitized_content: Optional[str] = None
    threats_detected: List[SecurityThreat] = field(default_factory=list)
    error_message: Optional[str] = None
    risk_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RateLimitState:
    """State for rate limiting."""
    requests: deque = field(default_factory=deque)
    tokens: float = MAX_BURST_SIZE
    last_update: float = field(default_factory=time.time)


class SecurityValidator:
    """
    Comprehensive security validator for review operations.
    
    Features:
    - Input validation and sanitization
    - OWASP Top 10 protection
    - Rate limiting with token bucket
    - Path traversal prevention
    - ReDoS protection
    - Audit logging
    - Content security scanning
    """
    
    # Pre-compiled safe regex patterns with timeout protection
    SQL_INJECTION_PATTERNS = [
        re.compile(r'\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE)\b.*\b(FROM|INTO|TABLE|WHERE)\b', re.IGNORECASE),
        re.compile(r'(\bOR\b|\bAND\b).*=.*', re.IGNORECASE),
        re.compile(r'(;|--|\*|\/\*|\*\/|xp_|sp_|0x)', re.IGNORECASE),
        re.compile(r"('|\"|`)(.*)(DROP|DELETE|INSERT|UPDATE|SELECT)(.*)\1", re.IGNORECASE),
    ]
    
    XSS_PATTERNS = [
        re.compile(r'<script[^>]*>.*?</script[^>]*>', re.IGNORECASE | re.DOTALL),
        re.compile(r'javascript:', re.IGNORECASE),
        re.compile(r'on\w+\s*=', re.IGNORECASE),  # Event handlers
        re.compile(r'<iframe[^>]*>', re.IGNORECASE),
        re.compile(r'<embed[^>]*>', re.IGNORECASE),
        re.compile(r'<object[^>]*>', re.IGNORECASE),
        re.compile(r'eval\s*\(', re.IGNORECASE),
        re.compile(r'expression\s*\(', re.IGNORECASE),
    ]
    
    COMMAND_INJECTION_PATTERNS = [
        re.compile(r'[;&|`$]'),  # Shell metacharacters
        re.compile(r'\$\([^)]+\)'),  # Command substitution
        re.compile(r'`[^`]+`'),  # Backticks
        re.compile(r'\|\||\&\&'),  # Command chaining
        re.compile(r'(nc|netcat|curl|wget|bash|sh|cmd|powershell)\s+', re.IGNORECASE),
    ]
    
    PATH_TRAVERSAL_PATTERNS = [
        re.compile(r'\.\.[\\/]'),  # ../ or ..\
        re.compile(r'\.\.%2[fF]'),  # URL encoded ../
        re.compile(r'\.\.%5[cC]'),  # URL encoded ..\
        re.compile(r'/etc/passwd|/etc/shadow|/windows/system32', re.IGNORECASE),
        re.compile(r'[cC]:\\'),  # Windows paths
    ]
    
    XXE_PATTERNS = [
        re.compile(r'<!DOCTYPE[^>]*\[.*ENTITY.*\]>', re.IGNORECASE | re.DOTALL),
        re.compile(r'SYSTEM\s+["\']file:', re.IGNORECASE),
        re.compile(r'<!ENTITY[^>]*SYSTEM', re.IGNORECASE),
    ]
    
    HARDCODED_SECRET_PATTERNS = [
        re.compile(r'(api[_-]?key|apikey|secret|password|passwd|pwd|token|auth)\s*[:=]\s*["\'][^"\']{8,}["\']', re.IGNORECASE),
        re.compile(r'["\'][a-zA-Z0-9+/]{40,}={0,2}["\']'),  # Base64 encoded secrets
        re.compile(r'["\'][0-9a-fA-F]{32,}["\']'),  # Hex encoded secrets
        re.compile(r'(sk|pk)_[a-zA-Z]+_[a-zA-Z0-9]{32,}'),  # Stripe-like keys
        re.compile(r'AIza[0-9A-Za-z-_]{35}'),  # Google API keys
    ]
    
    # Allowed HTML tags and attributes for content
    ALLOWED_TAGS = [
        'p', 'br', 'span', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'a', 'img', 'strong', 'em', 'code', 'pre',
        'blockquote', 'table', 'thead', 'tbody', 'tr', 'td', 'th'
    ]
    
    ALLOWED_ATTRIBUTES = {
        '*': ['class', 'id'],
        'a': ['href', 'title', 'target'],
        'img': ['src', 'alt', 'width', 'height'],
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize security validator."""
        self.config = config or {}
        self.rate_limiters: Dict[str, RateLimitState] = {}
        self.audit_log: List[Dict[str, Any]] = []
        self.blocked_ips: Set[str] = set()
        self.security_headers = self._get_security_headers()
        self._init_logging()
    
    def _init_logging(self):
        """Initialize security audit logging."""
        self.audit_logger = logging.getLogger(f"{__name__}.audit")
        self.audit_logger.setLevel(logging.INFO)
        
        # Create audit log handler if not exists
        if not self.audit_logger.handlers:
            handler = logging.FileHandler('security_audit.log')
            handler.setFormatter(
                logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            )
            self.audit_logger.addHandler(handler)
    
    def _get_security_headers(self) -> Dict[str, str]:
        """Get recommended security headers."""
        return {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Content-Security-Policy': "default-src 'self'",
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
        }
    
    def validate_document(
        self,
        content: str,
        document_type: str = "generic",
        metadata: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Comprehensive document validation.
        
        Checks for:
        - Size limits
        - Malicious content
        - OWASP vulnerabilities
        - Encoding issues
        """
        threats = []
        risk_score = 0.0
        
        # Size validation
        if len(content) > MAX_DOCUMENT_SIZE:
            return ValidationResult(
                is_valid=False,
                error_message=f"Document exceeds maximum size of {MAX_DOCUMENT_SIZE} bytes",
                risk_score=10.0
            )
        
        # Check for various injection attacks
        if self._check_sql_injection(content):
            threats.append(SecurityThreat.SQL_INJECTION)
            risk_score += 8.0
        
        if self._check_xss(content):
            threats.append(SecurityThreat.XSS)
            risk_score += 7.0
        
        if self._check_command_injection(content):
            threats.append(SecurityThreat.COMMAND_INJECTION)
            risk_score += 9.0
        
        if self._check_path_traversal(content):
            threats.append(SecurityThreat.PATH_TRAVERSAL)
            risk_score += 6.0
        
        if self._check_xxe(content):
            threats.append(SecurityThreat.XXE)
            risk_score += 7.0
        
        if self._check_hardcoded_secrets(content):
            threats.append(SecurityThreat.HARDCODED_SECRETS)
            risk_score += 5.0
        
        # Sanitize content
        sanitized = self.sanitize_content(content, document_type)
        
        # Log security event
        self._log_security_event(
            "document_validation",
            {
                "document_type": document_type,
                "threats": [t.value for t in threats],
                "risk_score": risk_score,
                "content_hash": hashlib.sha256(content.encode()).hexdigest()[:16]
            }
        )
        
        return ValidationResult(
            is_valid=len(threats) == 0 or risk_score < 5.0,
            sanitized_content=sanitized,
            threats_detected=threats,
            risk_score=min(risk_score, 10.0),
            metadata={
                "validation_timestamp": datetime.now().isoformat(),
                "document_type": document_type
            }
        )
    
    def _check_sql_injection(self, content: str) -> bool:
        """Check for SQL injection patterns."""
        for pattern in self.SQL_INJECTION_PATTERNS:
            try:
                if self._safe_regex_search(pattern, content):
                    return True
            except TimeoutError:
                logger.warning("SQL injection check timed out")
                return True  # Treat timeout as suspicious
        return False
    
    def _check_xss(self, content: str) -> bool:
        """Check for XSS patterns."""
        for pattern in self.XSS_PATTERNS:
            try:
                if self._safe_regex_search(pattern, content):
                    return True
            except TimeoutError:
                logger.warning("XSS check timed out")
                return True
        return False
    
    def _check_command_injection(self, content: str) -> bool:
        """Check for command injection patterns."""
        for pattern in self.COMMAND_INJECTION_PATTERNS:
            try:
                if self._safe_regex_search(pattern, content):
                    return True
            except TimeoutError:
                logger.warning("Command injection check timed out")
                return True
        return False
    
    def _check_path_traversal(self, content: str) -> bool:
        """Check for path traversal patterns."""
        for pattern in self.PATH_TRAVERSAL_PATTERNS:
            try:
                if self._safe_regex_search(pattern, content):
                    return True
            except TimeoutError:
                logger.warning("Path traversal check timed out")
                return True
        return False
    
    def _check_xxe(self, content: str) -> bool:
        """Check for XXE patterns."""
        for pattern in self.XXE_PATTERNS:
            try:
                if self._safe_regex_search(pattern, content):
                    return True
            except TimeoutError:
                logger.warning("XXE check timed out")
                return True
        return False
    
    def _check_hardcoded_secrets(self, content: str) -> bool:
        """Check for hardcoded secrets."""
        for pattern in self.HARDCODED_SECRET_PATTERNS:
            try:
                if self._safe_regex_search(pattern, content):
                    return True
            except TimeoutError:
                logger.warning("Secret check timed out")
                return True
        return False
    
    def _safe_regex_search(self, pattern: re.Pattern, text: str, timeout: float = REGEX_TIMEOUT) -> bool:
        """
        Safely search regex with timeout protection against ReDoS.
        """
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Regex execution timed out")
        
        # Set timeout
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(timeout))
        
        try:
            result = pattern.search(text) is not None
            signal.alarm(0)  # Cancel alarm
            return result
        except TimeoutError:
            raise
        finally:
            signal.signal(signal.SIGALRM, old_handler)
    
    def sanitize_content(self, content: str, content_type: str = "text") -> str:
        """
        Sanitize content based on type.
        
        - HTML: Use bleach for sanitization
        - Text: Basic escaping
        - Code: Preserve but escape dangerous patterns
        """
        if content_type == "html":
            # HTML sanitization
            return bleach.clean(
                content,
                tags=self.ALLOWED_TAGS,
                attributes=self.ALLOWED_ATTRIBUTES,
                strip=True
            )
        elif content_type == "code":
            # Code sanitization - preserve structure but escape dangerous patterns
            sanitized = content
            # Remove obvious secrets
            sanitized = re.sub(
                r'(api[_-]?key|password|secret|token)\s*[:=]\s*["\'][^"\']+["\']',
                r'\1="[REDACTED]"',
                sanitized,
                flags=re.IGNORECASE
            )
            return sanitized
        else:
            # Text sanitization - basic HTML escaping
            return html.escape(content)
    
    def validate_path(self, path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate file path for security issues.
        
        Returns:
            Tuple of (is_valid, sanitized_path)
        """
        # Check length
        if len(path) > MAX_PATH_LENGTH:
            return False, None
        
        # Check for path traversal
        if '..' in path or path.startswith('/'):
            return False, None
        
        # Normalize path
        try:
            safe_path = Path(path).resolve()
            
            # Ensure path is within allowed directory
            base_dir = Path.cwd()
            if not str(safe_path).startswith(str(base_dir)):
                return False, None
            
            return True, str(safe_path)
        except Exception as e:
            logger.warning(f"Path validation failed: {e}")
            return False, None
    
    def check_rate_limit(self, client_id: str, action: str = "review") -> bool:
        """
        Check if client has exceeded rate limit.
        
        Uses token bucket algorithm for smooth rate limiting.
        """
        key = f"{client_id}:{action}"
        now = time.time()
        
        if key not in self.rate_limiters:
            self.rate_limiters[key] = RateLimitState()
        
        state = self.rate_limiters[key]
        
        # Update tokens based on time elapsed
        time_elapsed = now - state.last_update
        state.tokens = min(
            MAX_BURST_SIZE,
            state.tokens + (time_elapsed * MAX_REQUESTS_PER_WINDOW / RATE_LIMIT_WINDOW)
        )
        state.last_update = now
        
        # Check if request can proceed
        if state.tokens >= 1:
            state.tokens -= 1
            state.requests.append(now)
            
            # Clean old requests
            cutoff = now - RATE_LIMIT_WINDOW
            while state.requests and state.requests[0] < cutoff:
                state.requests.popleft()
            
            return True
        
        # Rate limit exceeded
        self._log_security_event(
            "rate_limit_exceeded",
            {"client_id": client_id, "action": action}
        )
        return False
    
    def validate_metadata(self, metadata: Dict[str, Any]) -> ValidationResult:
        """
        Validate metadata for security issues.
        """
        threats = []
        sanitized = {}
        
        def validate_value(value: Any, depth: int = 0) -> Any:
            """Recursively validate values."""
            if depth > MAX_RECURSION_DEPTH:
                raise ValueError("Maximum recursion depth exceeded")
            
            if isinstance(value, str):
                # Check string length
                if len(value) > MAX_FIELD_LENGTH:
                    raise ValueError(f"Field exceeds maximum length of {MAX_FIELD_LENGTH}")
                
                # Check for injection patterns
                if self._check_sql_injection(value):
                    threats.append(SecurityThreat.SQL_INJECTION)
                if self._check_xss(value):
                    threats.append(SecurityThreat.XSS)
                
                return html.escape(value)
            
            elif isinstance(value, (list, tuple)):
                if len(value) > MAX_ARRAY_SIZE:
                    raise ValueError(f"Array exceeds maximum size of {MAX_ARRAY_SIZE}")
                return [validate_value(v, depth + 1) for v in value]
            
            elif isinstance(value, dict):
                return {k: validate_value(v, depth + 1) for k, v in value.items()}
            
            elif isinstance(value, (int, float, bool, type(None))):
                return value
            
            else:
                # Don't allow arbitrary objects
                raise ValueError(f"Invalid value type: {type(value)}")
        
        try:
            for key, value in metadata.items():
                if not isinstance(key, str) or len(key) > 100:
                    continue
                sanitized[key] = validate_value(value)
            
            return ValidationResult(
                is_valid=len(threats) == 0,
                sanitized_content=json.dumps(sanitized),
                threats_detected=threats
            )
        
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_message=str(e),
                threats_detected=threats
            )
    
    def create_secure_hash(self, content: str, salt: Optional[str] = None) -> str:
        """Create secure hash of content."""
        if salt is None:
            salt = secrets.token_hex(16)
        
        # Use PBKDF2 for secure hashing
        import hashlib
        hash_obj = hashlib.pbkdf2_hmac(
            'sha256',
            content.encode(),
            salt.encode(),
            100000  # iterations
        )
        return f"{salt}:{hash_obj.hex()}"
    
    def verify_secure_hash(self, content: str, hash_value: str) -> bool:
        """Verify secure hash."""
        try:
            salt, hash_hex = hash_value.split(':')
            expected = self.create_secure_hash(content, salt)
            return secrets.compare_digest(expected, hash_value)
        except Exception:
            return False
    
    def _log_security_event(self, event_type: str, details: Dict[str, Any]):
        """Log security event for audit trail."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "details": details
        }
        
        self.audit_log.append(event)
        self.audit_logger.info(json.dumps(event))
        
        # Keep audit log size limited
        if len(self.audit_log) > 10000:
            self.audit_log = self.audit_log[-5000:]
    
    def get_security_report(self) -> Dict[str, Any]:
        """Generate security report."""
        return {
            "total_validations": len(self.audit_log),
            "blocked_ips": list(self.blocked_ips),
            "rate_limiters_active": len(self.rate_limiters),
            "recent_threats": self._get_recent_threats(),
            "security_headers": self.security_headers
        }
    
    def _get_recent_threats(self) -> List[Dict[str, Any]]:
        """Get recent security threats from audit log."""
        threats = []
        for event in self.audit_log[-100:]:  # Last 100 events
            if event.get("event_type") == "document_validation":
                details = event.get("details", {})
                if details.get("threats"):
                    threats.append({
                        "timestamp": event["timestamp"],
                        "threats": details["threats"],
                        "risk_score": details.get("risk_score", 0)
                    })
        return threats[-10:]  # Return last 10 threats
    
    @contextmanager
    def secure_context(self, operation: str):
        """Context manager for secure operations."""
        start_time = time.time()
        try:
            self._log_security_event(f"{operation}_start", {"timestamp": start_time})
            yield
        except Exception as e:
            self._log_security_event(
                f"{operation}_error",
                {"error": str(e), "timestamp": time.time()}
            )
            raise
        finally:
            self._log_security_event(
                f"{operation}_complete",
                {"duration": time.time() - start_time}
            )


class AccessController:
    """
    Role-based access control for review operations.
    """
    
    ROLES = {
        "admin": ["*"],  # All permissions
        "reviewer": ["review.create", "review.read", "review.update"],
        "viewer": ["review.read"],
        "auditor": ["review.read", "audit.read"],
    }
    
    def __init__(self):
        """Initialize access controller."""
        self.user_roles: Dict[str, List[str]] = {}
        self.role_permissions: Dict[str, List[str]] = self.ROLES.copy()
        self.access_log: List[Dict[str, Any]] = []
    
    def grant_role(self, user_id: str, role: str):
        """Grant role to user."""
        if role not in self.role_permissions:
            raise ValueError(f"Invalid role: {role}")
        
        if user_id not in self.user_roles:
            self.user_roles[user_id] = []
        
        if role not in self.user_roles[user_id]:
            self.user_roles[user_id].append(role)
            self._log_access("role_granted", user_id, {"role": role})
    
    def revoke_role(self, user_id: str, role: str):
        """Revoke role from user."""
        if user_id in self.user_roles and role in self.user_roles[user_id]:
            self.user_roles[user_id].remove(role)
            self._log_access("role_revoked", user_id, {"role": role})
    
    def check_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has permission."""
        if user_id not in self.user_roles:
            return False
        
        for role in self.user_roles[user_id]:
            role_perms = self.role_permissions.get(role, [])
            if "*" in role_perms or permission in role_perms:
                self._log_access("permission_granted", user_id, {"permission": permission})
                return True
        
        self._log_access("permission_denied", user_id, {"permission": permission})
        return False
    
    def _log_access(self, event_type: str, user_id: str, details: Dict[str, Any]):
        """Log access control event."""
        self.access_log.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "details": details
        })
        
        # Keep log size limited
        if len(self.access_log) > 10000:
            self.access_log = self.access_log[-5000:]
    
    def get_user_permissions(self, user_id: str) -> List[str]:
        """Get all permissions for user."""
        permissions = set()
        
        for role in self.user_roles.get(user_id, []):
            role_perms = self.role_permissions.get(role, [])
            if "*" in role_perms:
                return ["*"]  # Admin has all permissions
            permissions.update(role_perms)
        
        return list(permissions)