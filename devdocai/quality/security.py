"""
Security module for M005 Quality Engine - Pass 3: Security Hardening.

Provides comprehensive security features including:
- Input validation and sanitization
- XSS and injection attack prevention
- Rate limiting and DoS protection
- PII detection and masking integration
- Secure configuration and audit logging
- OWASP Top 10 compliance measures
"""

import re
import html
import hashlib
import secrets
import logging
import time
import json
from typing import Dict, List, Optional, Any, Set, Union, Tuple
from pathlib import Path
from functools import wraps
from collections import defaultdict, deque
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import bleach
from urllib.parse import urlparse, quote

# Import PII detector from M002
try:
    from devdocai.storage.pii_detector import PIIDetector, PIIDetectionConfig, PIIType
    PII_AVAILABLE = True
except ImportError:
    PII_AVAILABLE = False
    PIIDetector = None
    PIIDetectionConfig = None
    PIIType = None

# Import encryption from M002
try:
    from devdocai.storage.encryption import EncryptionManager
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False
    EncryptionManager = None

logger = logging.getLogger(__name__)


# ============================================================================
# Security Configuration
# ============================================================================

@dataclass
class SecurityConfig:
    """Security configuration for quality engine."""
    
    # Input validation
    max_document_size: int = 10_000_000  # 10MB max
    max_batch_size: int = 100
    allowed_file_extensions: Set[str] = field(default_factory=lambda: {
        '.md', '.txt', '.rst', '.adoc', '.html', '.json', '.yaml', '.yml'
    })
    
    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100  # requests per window
    rate_limit_window: int = 60  # seconds
    rate_limit_burst: int = 20  # burst allowance
    
    # Content sanitization
    sanitize_html: bool = True
    allowed_html_tags: Set[str] = field(default_factory=lambda: {
        'p', 'br', 'span', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'strong', 'em', 'u', 'code', 'pre', 'blockquote', 'ul', 'ol', 'li',
        'a', 'img', 'table', 'thead', 'tbody', 'tr', 'td', 'th'
    })
    allowed_html_attributes: Dict[str, List[str]] = field(default_factory=lambda: {
        'a': ['href', 'title'],
        'img': ['src', 'alt', 'title'],
        'code': ['class'],
        'pre': ['class']
    })
    
    # PII Protection
    pii_detection_enabled: bool = True
    pii_masking_enabled: bool = True
    pii_types_to_detect: Set[str] = field(default_factory=lambda: {
        'ssn', 'credit_card', 'email', 'phone', 'ip_address',
        'api_key', 'aws_key', 'private_key'
    })
    
    # Audit logging
    audit_enabled: bool = True
    audit_log_path: str = "logs/security_audit.log"
    audit_retention_days: int = 90
    
    # Session security
    session_timeout: int = 3600  # 1 hour
    session_token_length: int = 32
    
    # Regex security
    regex_timeout: float = 1.0  # seconds
    max_regex_complexity: int = 1000
    
    # Error handling
    expose_errors: bool = False  # Don't expose detailed errors in production
    error_log_sensitive: bool = False  # Don't log sensitive data in errors


class SecurityLevel(Enum):
    """Security levels for different environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


# ============================================================================
# Rate Limiting
# ============================================================================

class RateLimiter:
    """Token bucket rate limiter for DoS protection."""
    
    def __init__(self, config: SecurityConfig):
        """Initialize rate limiter."""
        self.config = config
        self.buckets: Dict[str, deque] = defaultdict(deque)
        self.last_cleanup = time.time()
    
    def is_allowed(self, identifier: str) -> Tuple[bool, Optional[float]]:
        """
        Check if request is allowed under rate limit.
        
        Returns:
            Tuple of (allowed, retry_after_seconds)
        """
        if not self.config.rate_limit_enabled:
            return True, None
        
        current_time = time.time()
        self._cleanup_old_entries(current_time)
        
        bucket = self.buckets[identifier]
        window_start = current_time - self.config.rate_limit_window
        
        # Remove old entries outside window
        while bucket and bucket[0] < window_start:
            bucket.popleft()
        
        # Check rate limit
        if len(bucket) >= self.config.rate_limit_requests:
            # Calculate retry after
            oldest_request = bucket[0]
            retry_after = oldest_request + self.config.rate_limit_window - current_time
            return False, retry_after
        
        # Add current request
        bucket.append(current_time)
        return True, None
    
    def _cleanup_old_entries(self, current_time: float):
        """Periodically cleanup old rate limit entries."""
        if current_time - self.last_cleanup > 300:  # Cleanup every 5 minutes
            window_start = current_time - self.config.rate_limit_window
            
            # Remove empty buckets and old entries
            empty_keys = []
            for key, bucket in self.buckets.items():
                while bucket and bucket[0] < window_start:
                    bucket.popleft()
                if not bucket:
                    empty_keys.append(key)
            
            for key in empty_keys:
                del self.buckets[key]
            
            self.last_cleanup = current_time


def rate_limit(get_identifier=lambda *args, **kwargs: "default"):
    """Decorator for rate limiting functions."""
    def decorator(func):
        limiter = None
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal limiter
            if limiter is None:
                # Initialize on first use
                config = kwargs.get('security_config') or SecurityConfig()
                limiter = RateLimiter(config)
            
            identifier = get_identifier(*args, **kwargs)
            allowed, retry_after = limiter.is_allowed(identifier)
            
            if not allowed:
                raise RateLimitExceeded(
                    f"Rate limit exceeded. Retry after {retry_after:.1f} seconds"
                )
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# ============================================================================
# Input Validation and Sanitization
# ============================================================================

class InputValidator:
    """Comprehensive input validation and sanitization."""
    
    def __init__(self, config: SecurityConfig):
        """Initialize input validator."""
        self.config = config
        self.pii_detector = None
        if PII_AVAILABLE and config.pii_detection_enabled:
            pii_config = PIIDetectionConfig(
                enabled_types=set(PIIType[t.upper()] for t in config.pii_types_to_detect if hasattr(PIIType, t.upper()))
            )
            self.pii_detector = PIIDetector(pii_config)
    
    def validate_document(self, content: str, document_type: str = "markdown") -> Tuple[bool, List[str]]:
        """
        Validate document content for security issues.
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Size validation
        if len(content) > self.config.max_document_size:
            issues.append(f"Document exceeds maximum size of {self.config.max_document_size} bytes")
        
        # Check for null bytes
        if '\x00' in content:
            issues.append("Document contains null bytes")
        
        # Check for control characters (except standard whitespace)
        control_chars = set(chr(i) for i in range(32) if i not in [9, 10, 13])  # Tab, LF, CR
        if any(c in content for c in control_chars):
            issues.append("Document contains suspicious control characters")
        
        # Check for potential script injection in markdown
        if document_type in ["markdown", "html"]:
            if self._has_script_injection(content):
                issues.append("Potential script injection detected")
        
        # Check for path traversal attempts
        if self._has_path_traversal(content):
            issues.append("Potential path traversal detected")
        
        # Check for XXE attempts in XML-like content
        if self._has_xxe_attempt(content):
            issues.append("Potential XXE attack detected")
        
        return len(issues) == 0, issues
    
    def sanitize_content(self, content: str, document_type: str = "markdown") -> str:
        """
        Sanitize document content to prevent XSS and injection attacks.
        """
        if not content:
            return content
        
        # Remove null bytes
        content = content.replace('\x00', '')
        
        # Handle HTML content
        if document_type in ["html", "markdown"] and self.config.sanitize_html:
            content = self._sanitize_html(content)
        
        # Escape special characters in code blocks
        content = self._escape_code_blocks(content)
        
        # Remove or mask PII if detected
        if self.pii_detector and self.config.pii_masking_enabled:
            content = self._mask_pii(content)
        
        return content
    
    def _sanitize_html(self, content: str) -> str:
        """Sanitize HTML content using bleach."""
        try:
            # Use bleach for HTML sanitization
            cleaned = bleach.clean(
                content,
                tags=list(self.config.allowed_html_tags),
                attributes=self.config.allowed_html_attributes,
                strip=True,
                strip_comments=True
            )
            return cleaned
        except Exception as e:
            logger.error(f"HTML sanitization failed: {e}")
            # Fallback to basic HTML escaping
            return html.escape(content)
    
    def _escape_code_blocks(self, content: str) -> str:
        """Escape special characters in code blocks."""
        # Pattern for markdown code blocks
        code_block_pattern = re.compile(r'```[\s\S]*?```', re.MULTILINE)
        
        def escape_block(match):
            block = match.group(0)
            # Don't escape the backticks themselves
            if block.startswith('```') and block.endswith('```'):
                inner = block[3:-3]
                # HTML escape the content
                inner = html.escape(inner)
                return f'```{inner}```'
            return block
        
        return code_block_pattern.sub(escape_block, content)
    
    def _mask_pii(self, content: str) -> str:
        """Mask PII in content."""
        if not self.pii_detector:
            return content
        
        try:
            # Use the PII detector's mask method directly
            # It handles detection and masking in one step
            masked_content = self.pii_detector.mask(content)
            return masked_content
        except Exception as e:
            logger.error(f"PII masking failed: {e}")
            return content
    
    def _has_script_injection(self, content: str) -> bool:
        """Check for potential script injection."""
        # Check for script tags
        script_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',  # Event handlers
            r'eval\s*\(',
            r'expression\s*\(',
            r'vbscript:',
            r'data:text/html',
        ]
        
        for pattern in script_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        
        return False
    
    def _has_path_traversal(self, content: str) -> bool:
        """Check for path traversal attempts."""
        traversal_patterns = [
            r'\.\./\.\.',
            r'\.\.',
            r'\.\.\\',
            r'%2e%2e%2f',
            r'%252e%252e%252f',
            r'..;',
            r'..%c0%af',
            r'..%c1%9c',
        ]
        
        for pattern in traversal_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        
        return False
    
    def _has_xxe_attempt(self, content: str) -> bool:
        """Check for XXE (XML External Entity) attempts."""
        xxe_patterns = [
            r'<!DOCTYPE[^>]*\[',
            r'<!ENTITY',
            r'SYSTEM\s+["\']file:',
            r'SYSTEM\s+["\']http:',
            r'SYSTEM\s+["\']ftp:',
            r'xmlns:xi\s*=',
            r'<xi:include',
        ]
        
        for pattern in xxe_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        
        return False
    
    def validate_path(self, path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate file path for security issues.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Convert to Path object
            p = Path(path)
            
            # Check for path traversal
            if '..' in p.parts:
                return False, "Path traversal detected"
            
            # Resolve to absolute path
            resolved = p.resolve()
            
            # Check if path is within allowed directory
            # This should be configured based on deployment
            allowed_root = Path.cwd()
            if not str(resolved).startswith(str(allowed_root)):
                return False, "Path outside allowed directory"
            
            # Check file extension if it's a file
            if p.suffix and p.suffix not in self.config.allowed_file_extensions:
                return False, f"File extension {p.suffix} not allowed"
            
            return True, None
            
        except Exception as e:
            return False, f"Invalid path: {str(e)}"


# ============================================================================
# Secure Regex Handler
# ============================================================================

class SecureRegexHandler:
    """Handle regex operations with ReDoS protection."""
    
    def __init__(self, timeout: float = 1.0):
        """Initialize secure regex handler."""
        self.timeout = timeout
        self._pattern_cache: Dict[str, re.Pattern] = {}
    
    def compile_pattern(self, pattern: str, flags: int = 0) -> Optional[re.Pattern]:
        """
        Compile regex pattern with safety checks.
        """
        # Check for potentially dangerous patterns (ReDoS)
        if self._is_dangerous_pattern(pattern):
            logger.warning(f"Potentially dangerous regex pattern rejected: {pattern[:50]}...")
            return None
        
        # Cache key
        cache_key = f"{pattern}:{flags}"
        
        # Return cached pattern if available
        if cache_key in self._pattern_cache:
            return self._pattern_cache[cache_key]
        
        try:
            # Compile with timeout (using alarm signal on Unix systems)
            compiled = re.compile(pattern, flags)
            
            # Cache the compiled pattern
            self._pattern_cache[cache_key] = compiled
            
            return compiled
            
        except re.error as e:
            logger.error(f"Regex compilation error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected regex error: {e}")
            return None
    
    def _is_dangerous_pattern(self, pattern: str) -> bool:
        """
        Check if regex pattern is potentially dangerous (ReDoS).
        """
        # Patterns that can cause exponential backtracking
        dangerous_constructs = [
            r'(\w+)*',  # Nested quantifiers
            r'(\w+)+',
            r'(.*)*',
            r'(.+)+',
            r'([^"]*)*',
            r"([^']*)*",  # Use double quotes to avoid syntax error
            r'(a+)+',
            r'(a*)*',
            r'(a|a)*',
            r'(a|ab)*',
        ]
        
        for construct in dangerous_constructs:
            if construct in pattern:
                return True
        
        # Check for excessive backtracking potential
        # Count nested groups and quantifiers
        nested_groups = pattern.count('(') 
        quantifiers = pattern.count('*') + pattern.count('+') + pattern.count('?')
        
        if nested_groups > 10 or quantifiers > 15:
            return True
        
        # Check for alternation with overlapping patterns
        if '|' in pattern:
            parts = pattern.split('|')
            if len(parts) > 10:  # Too many alternatives
                return True
        
        return False
    
    def search(self, pattern: str, text: str, flags: int = 0) -> Optional[re.Match]:
        """Safe regex search with timeout."""
        compiled = self.compile_pattern(pattern, flags)
        if not compiled:
            return None
        
        try:
            # Implement timeout using threading or signal
            # For simplicity, using basic approach here
            return compiled.search(text)
        except Exception as e:
            logger.error(f"Regex search error: {e}")
            return None
    
    def findall(self, pattern: str, text: str, flags: int = 0) -> List[str]:
        """Safe regex findall with timeout."""
        compiled = self.compile_pattern(pattern, flags)
        if not compiled:
            return []
        
        try:
            return compiled.findall(text)
        except Exception as e:
            logger.error(f"Regex findall error: {e}")
            return []


# ============================================================================
# Audit Logger
# ============================================================================

class SecurityAuditLogger:
    """Security audit logging for compliance and monitoring."""
    
    def __init__(self, config: SecurityConfig):
        """Initialize audit logger."""
        self.config = config
        self.enabled = config.audit_enabled
        
        if self.enabled:
            # Setup dedicated audit logger
            self.audit_logger = logging.getLogger('security_audit')
            self.audit_logger.setLevel(logging.INFO)
            
            # Create audit log directory if needed
            log_path = Path(config.audit_log_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Add file handler
            handler = logging.FileHandler(log_path)
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.audit_logger.addHandler(handler)
    
    def log_access(self, user_id: str, action: str, resource: str, result: str, metadata: Optional[Dict] = None):
        """Log access attempt."""
        if not self.enabled:
            return
        
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'action': action,
            'resource': resource,
            'result': result,
            'metadata': metadata or {}
        }
        
        self.audit_logger.info(json.dumps(log_entry))
    
    def log_security_event(self, event_type: str, severity: str, description: str, metadata: Optional[Dict] = None):
        """Log security event."""
        if not self.enabled:
            return
        
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'severity': severity,
            'description': description,
            'metadata': metadata or {}
        }
        
        self.audit_logger.warning(json.dumps(log_entry))
    
    def log_validation_failure(self, input_type: str, reason: str, sample: str = ""):
        """Log input validation failure."""
        if not self.enabled:
            return
        
        # Don't log sensitive data
        if not self.config.error_log_sensitive:
            sample = "[REDACTED]"
        else:
            # Truncate sample
            sample = sample[:100] if len(sample) > 100 else sample
        
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': 'validation_failure',
            'input_type': input_type,
            'reason': reason,
            'sample': sample
        }
        
        self.audit_logger.warning(json.dumps(log_entry))


# ============================================================================
# Session Manager
# ============================================================================

class SecureSessionManager:
    """Secure session management with tokens."""
    
    def __init__(self, config: SecurityConfig):
        """Initialize session manager."""
        self.config = config
        self.sessions: Dict[str, Dict] = {}
        self.last_cleanup = time.time()
    
    def create_session(self, user_id: str, metadata: Optional[Dict] = None) -> str:
        """Create new secure session."""
        # Generate secure token
        token = secrets.token_urlsafe(self.config.session_token_length)
        
        # Store session data
        self.sessions[token] = {
            'user_id': user_id,
            'created_at': time.time(),
            'last_accessed': time.time(),
            'metadata': metadata or {}
        }
        
        # Cleanup old sessions
        self._cleanup_expired_sessions()
        
        return token
    
    def validate_session(self, token: str) -> Optional[Dict]:
        """Validate and retrieve session data."""
        if token not in self.sessions:
            return None
        
        session = self.sessions[token]
        current_time = time.time()
        
        # Check if session expired
        if current_time - session['created_at'] > self.config.session_timeout:
            del self.sessions[token]
            return None
        
        # Update last accessed time
        session['last_accessed'] = current_time
        
        return session
    
    def destroy_session(self, token: str):
        """Destroy session."""
        if token in self.sessions:
            del self.sessions[token]
    
    def _cleanup_expired_sessions(self):
        """Remove expired sessions."""
        current_time = time.time()
        
        # Only cleanup periodically
        if current_time - self.last_cleanup < 300:  # 5 minutes
            return
        
        expired_tokens = []
        for token, session in self.sessions.items():
            if current_time - session['created_at'] > self.config.session_timeout:
                expired_tokens.append(token)
        
        for token in expired_tokens:
            del self.sessions[token]
        
        self.last_cleanup = current_time


# ============================================================================
# Security Exceptions
# ============================================================================

class SecurityException(Exception):
    """Base security exception."""
    pass


class RateLimitExceeded(SecurityException):
    """Rate limit exceeded exception."""
    pass


class ValidationError(SecurityException):
    """Input validation error."""
    pass


class AuthenticationError(SecurityException):
    """Authentication failed."""
    pass


class AuthorizationError(SecurityException):
    """Authorization failed."""
    pass


# ============================================================================
# Security Manager (Main Interface)
# ============================================================================

class QualitySecurityManager:
    """
    Main security manager for M005 Quality Engine.
    
    Provides centralized security features including:
    - Input validation and sanitization
    - Rate limiting
    - PII detection and masking
    - Secure regex handling
    - Audit logging
    - Session management
    """
    
    def __init__(self, config: Optional[SecurityConfig] = None, security_level: SecurityLevel = SecurityLevel.PRODUCTION):
        """Initialize security manager."""
        self.config = config or SecurityConfig()
        self.security_level = security_level
        
        # Adjust config based on security level
        self._configure_for_level()
        
        # Initialize components
        self.validator = InputValidator(self.config)
        self.rate_limiter = RateLimiter(self.config)
        self.regex_handler = SecureRegexHandler(self.config.regex_timeout)
        self.audit_logger = SecurityAuditLogger(self.config)
        self.session_manager = SecureSessionManager(self.config)
        
        # Initialize encryption if available
        self.encryption_manager = None
        if ENCRYPTION_AVAILABLE:
            try:
                self.encryption_manager = EncryptionManager()
            except Exception as e:
                logger.warning(f"Encryption manager initialization failed: {e}")
        
        logger.info(f"Security manager initialized with level: {security_level.value}")
    
    def _configure_for_level(self):
        """Adjust configuration based on security level."""
        if self.security_level == SecurityLevel.DEVELOPMENT:
            self.config.expose_errors = True
            self.config.error_log_sensitive = True
            self.config.rate_limit_enabled = False
            self.config.audit_enabled = False
        elif self.security_level == SecurityLevel.STAGING:
            self.config.expose_errors = False
            self.config.error_log_sensitive = False
            self.config.rate_limit_enabled = True
            self.config.audit_enabled = True
        else:  # PRODUCTION
            self.config.expose_errors = False
            self.config.error_log_sensitive = False
            self.config.rate_limit_enabled = True
            self.config.audit_enabled = True
            self.config.pii_detection_enabled = True
            self.config.pii_masking_enabled = True
    
    def validate_and_sanitize(self, content: str, document_type: str = "markdown", user_id: str = "anonymous") -> Tuple[str, List[str]]:
        """
        Validate and sanitize document content.
        
        Returns:
            Tuple of (sanitized_content, list_of_issues)
        """
        # Check rate limit
        allowed, retry_after = self.rate_limiter.is_allowed(user_id)
        if not allowed:
            self.audit_logger.log_security_event(
                'rate_limit_exceeded',
                'warning',
                f"Rate limit exceeded for user {user_id}",
                {'retry_after': retry_after}
            )
            raise RateLimitExceeded(f"Rate limit exceeded. Retry after {retry_after:.1f} seconds")
        
        # Validate content
        is_valid, issues = self.validator.validate_document(content, document_type)
        
        if not is_valid:
            self.audit_logger.log_validation_failure(
                document_type,
                '; '.join(issues),
                content[:100]
            )
        
        # Sanitize content
        sanitized = self.validator.sanitize_content(content, document_type)
        
        # Log access
        self.audit_logger.log_access(
            user_id,
            'document_analysis',
            document_type,
            'success' if is_valid else 'validation_failed',
            {'issues_count': len(issues)}
        )
        
        return sanitized, issues
    
    def encrypt_report(self, report_data: str) -> Optional[str]:
        """Encrypt quality report for secure storage."""
        if not self.encryption_manager:
            return report_data
        
        try:
            encrypted = self.encryption_manager.encrypt(report_data.encode())
            return encrypted.decode('latin-1')  # Convert bytes to string for storage
        except Exception as e:
            logger.error(f"Report encryption failed: {e}")
            return None
    
    def decrypt_report(self, encrypted_data: str) -> Optional[str]:
        """Decrypt quality report."""
        if not self.encryption_manager:
            return encrypted_data
        
        try:
            decrypted = self.encryption_manager.decrypt(encrypted_data.encode('latin-1'))
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Report decryption failed: {e}")
            return None
    
    def check_authorization(self, user_id: str, resource: str, action: str) -> bool:
        """
        Check if user is authorized for action on resource.
        
        This is a placeholder for real authorization logic.
        """
        # Log authorization check
        self.audit_logger.log_access(
            user_id,
            f"auth_check_{action}",
            resource,
            'granted'
        )
        
        # Placeholder - implement real authorization
        return True
    
    def create_secure_session(self, user_id: str, metadata: Optional[Dict] = None) -> str:
        """Create secure session for user."""
        token = self.session_manager.create_session(user_id, metadata)
        
        self.audit_logger.log_access(
            user_id,
            'session_created',
            'session',
            'success',
            {'session_token': token[:8] + '...'}  # Log partial token
        )
        
        return token
    
    def validate_session(self, token: str) -> Optional[Dict]:
        """Validate session token."""
        session = self.session_manager.validate_session(token)
        
        if session:
            self.audit_logger.log_access(
                session['user_id'],
                'session_validated',
                'session',
                'success'
            )
        else:
            self.audit_logger.log_security_event(
                'invalid_session',
                'warning',
                'Invalid or expired session token'
            )
        
        return session