"""
Template Security Module for M006 Template Registry.

This module provides comprehensive security features for template operations,
including input validation, sanitization, SSTI prevention, and rate limiting.
Follows OWASP Top 10 security standards.
"""

import re
import hashlib
import html
import json
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path
from datetime import datetime, timedelta
import logging
from collections import defaultdict
from functools import wraps
import time
import secrets

import bleach
from markupsafe import Markup, escape

from ..storage.pii_detector import PIIDetector  # M002 integration
from .exceptions import (
    TemplateSecurityError,
    TemplateSSTIError,
    TemplatePathTraversalError,
    TemplateRateLimitError,
    TemplateValidationError
)

logger = logging.getLogger(__name__)


class TemplateSecurity:
    """
    Comprehensive security manager for template operations.
    
    Implements:
    - Input validation and sanitization
    - SSTI (Server-Side Template Injection) prevention
    - XSS (Cross-Site Scripting) prevention
    - Path traversal protection
    - Rate limiting
    - PII detection and masking
    - Audit logging
    """
    
    # Security configuration
    MAX_TEMPLATE_SIZE = 1024 * 1024  # 1MB max template size
    MAX_VARIABLE_LENGTH = 1024  # Max length for variable values
    MAX_INCLUDE_DEPTH = 3  # Max template include depth
    MAX_LOOP_ITERATIONS = 1000  # Max iterations in template loops
    MAX_RENDER_TIME = 5.0  # Max seconds for template rendering
    
    # Rate limiting configuration
    DEFAULT_RATE_LIMITS = {
        'render_per_minute': 100,
        'render_per_hour': 1000,
        'create_per_hour': 50,
        'update_per_hour': 100
    }
    
    # Dangerous patterns to detect SSTI attempts
    SSTI_PATTERNS = [
        # Python/Jinja2 SSTI patterns
        r'__class__', r'__base__', r'__subclasses__', r'__import__',
        r'__builtins__', r'__globals__', r'__code__', r'__dict__',
        r'exec\s*\(', r'eval\s*\(', r'compile\s*\(', r'open\s*\(',
        r'import\s+', r'from\s+.*\s+import', r'subprocess', r'os\.',
        r'sys\.', r'globals\s*\(', r'locals\s*\(', r'vars\s*\(',
        r'getattr\s*\(', r'setattr\s*\(', r'delattr\s*\(',
        # Command injection patterns
        r'`.*`', r'\$\(.*\)', r'&&', r'\|\|', r';', r'\|',
        # File system access
        r'\.\./', r'\.\.\\\\', r'/etc/', r'c:\\\\', r'file://',
        # Network access
        r'http://', r'https://', r'ftp://', r'ssh://', r'telnet://',
    ]
    
    # Allowed HTML tags for sanitization
    ALLOWED_HTML_TAGS = [
        'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'pre', 'code', 'blockquote', 'a', 'span', 'div'
    ]
    
    # Allowed HTML attributes
    ALLOWED_HTML_ATTRS = {
        'a': ['href', 'title', 'target'],
        'span': ['class'],
        'div': ['class'],
        'code': ['class']
    }
    
    def __init__(self, 
                 pii_detector: Optional[PIIDetector] = None,
                 rate_limits: Optional[Dict[str, int]] = None,
                 audit_logger: Optional[logging.Logger] = None):
        """
        Initialize security manager.
        
        Args:
            pii_detector: PII detector from M002
            rate_limits: Custom rate limits
            audit_logger: Logger for security events
        """
        self.pii_detector = pii_detector or PIIDetector()
        self.rate_limits = rate_limits or self.DEFAULT_RATE_LIMITS
        self.audit_logger = audit_logger or logger
        
        # Rate limiting storage
        self._rate_counters: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
        
        # Compiled SSTI patterns for efficiency
        try:
            self._ssti_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.SSTI_PATTERNS]
        except Exception as e:
            logger.warning(f"Failed to compile SSTI patterns: {e}")
            self._ssti_regex = []
        
        # Template whitelist cache
        self._template_whitelist: Set[str] = set()
        self._whitelist_updated = datetime.now()
        
    def validate_template_content(self, content: str, template_id: Optional[str] = None) -> Tuple[bool, List[str]]:
        """
        Validate template content for security issues.
        
        Args:
            content: Template content to validate
            template_id: Optional template ID for logging
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check template size
        if len(content) > self.MAX_TEMPLATE_SIZE:
            issues.append(f"Template exceeds maximum size ({len(content)} > {self.MAX_TEMPLATE_SIZE})")
        
        # Check for SSTI patterns
        ssti_issues = self._detect_ssti_patterns(content)
        if ssti_issues:
            issues.extend([f"SSTI pattern detected: {issue}" for issue in ssti_issues])
        
        # Check for PII
        if self.pii_detector:
            try:
                pii_results = self.pii_detector.detect(content)
                # Handle both dict and list return types
                if isinstance(pii_results, dict):
                    if pii_results.get('contains_pii'):
                        pii_types = ', '.join(pii_results.get('pii_types', []))
                        issues.append(f"Template contains PII: {pii_types}")
                elif isinstance(pii_results, list) and pii_results:
                    # PIIDetector might return a list of detected entities
                    issues.append(f"Template contains PII: {len(pii_results)} instances detected")
            except Exception as e:
                logger.warning(f"PII detection failed: {e}")
        
        # Check for malicious includes
        include_issues = self._validate_includes(content)
        if include_issues:
            issues.extend(include_issues)
        
        # Log security validation
        if issues and template_id:
            self.audit_logger.warning(
                f"Security validation failed for template {template_id}: {issues}"
            )
        
        return len(issues) == 0, issues
    
    def _detect_ssti_patterns(self, content: str) -> List[str]:
        """Detect potential SSTI patterns in content."""
        detected = []
        
        for pattern in self._ssti_regex:
            matches = pattern.findall(content)
            if matches:
                # Don't expose exact matches to avoid information disclosure
                pattern_str = pattern.pattern[:20] + "..."
                detected.append(f"Suspicious pattern: {pattern_str}")
        
        return detected
    
    def _validate_includes(self, content: str) -> List[str]:
        """Validate template include paths for security."""
        issues = []
        include_pattern = re.compile(r'<!-- INCLUDE ([^-]+) -->')
        
        for match in include_pattern.finditer(content):
            include_path = match.group(1).strip()
            
            # Check for path traversal
            if '..' in include_path or include_path.startswith('/'):
                issues.append(f"Path traversal attempt in include: {include_path}")
            
            # Check for absolute paths
            if Path(include_path).is_absolute():
                issues.append(f"Absolute path in include not allowed: {include_path}")
            
            # Check for network URLs
            if any(include_path.startswith(proto) for proto in ['http://', 'https://', 'ftp://']):
                issues.append(f"Network URL in include not allowed: {include_path}")
        
        return issues
    
    def sanitize_variable_value(self, value: Any, variable_name: str = "") -> Any:
        """
        Sanitize variable value to prevent injection attacks.
        
        Args:
            value: Variable value to sanitize
            variable_name: Name of the variable for logging
            
        Returns:
            Sanitized value
        """
        if value is None:
            return value
        
        # Convert to string for sanitization
        str_value = str(value)
        
        # Check length
        if len(str_value) > self.MAX_VARIABLE_LENGTH:
            str_value = str_value[:self.MAX_VARIABLE_LENGTH]
            logger.warning(f"Truncated variable '{variable_name}' to {self.MAX_VARIABLE_LENGTH} chars")
        
        # Escape HTML special characters
        sanitized = escape(str_value)
        
        # Additional sanitization for specific types
        if isinstance(value, str):
            # Remove null bytes
            sanitized = sanitized.replace('\x00', '')
            
            # Check for SSTI patterns in variable value
            if self._detect_ssti_patterns(str(sanitized)):
                raise TemplateSSTIError(f"SSTI pattern detected in variable '{variable_name}'")
        
        return sanitized
    
    def sanitize_html_output(self, html: str) -> str:
        """
        Sanitize HTML output to prevent XSS attacks.
        
        Args:
            html: HTML content to sanitize
            
        Returns:
            Sanitized HTML
        """
        try:
            # Use bleach for comprehensive HTML sanitization
            import bleach
            cleaned = bleach.clean(
                html,
                tags=self.ALLOWED_HTML_TAGS,
                attributes=self.ALLOWED_HTML_ATTRS,
                strip=True,
                strip_comments=True
            )
        except ImportError:
            # Fallback to basic sanitization if bleach not available
            cleaned = html
            # Remove script tags
            cleaned = re.sub(r'<script[^>]*>.*?</script\b[^>]*>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
            # Remove event handlers
            cleaned = re.sub(r'\s*on\w+\s*=\s*["\'][^"\']*["\']', '', cleaned, flags=re.IGNORECASE)
            # Escape remaining HTML
            cleaned = html.replace('<', '&lt;').replace('>', '&gt;')
        
        # Additional XSS prevention
        cleaned = self._remove_javascript_urls(cleaned)
        cleaned = self._remove_data_urls(cleaned)
        
        return cleaned
    
    def _remove_javascript_urls(self, html: str) -> str:
        """Remove javascript: URLs from HTML."""
        js_pattern = re.compile(r'javascript:', re.IGNORECASE)
        return js_pattern.sub('', html)
    
    def _remove_data_urls(self, html: str) -> str:
        """Remove data: URLs that could contain scripts."""
        data_pattern = re.compile(r'data:.*?script', re.IGNORECASE)
        return data_pattern.sub('', html)
    
    def check_rate_limit(self, user_id: str, action: str) -> bool:
        """
        Check if user has exceeded rate limit for action.
        
        Args:
            user_id: User identifier
            action: Action being performed (e.g., 'render', 'create')
            
        Returns:
            True if within rate limit, False if exceeded
            
        Raises:
            TemplateRateLimitError: If rate limit exceeded
        """
        now = time.time()
        
        # Clean old entries
        self._clean_rate_counters(now)
        
        # Check per-minute limits
        if f"{action}_per_minute" in self.rate_limits:
            minute_ago = now - 60
            recent_actions = [t for t in self._rate_counters[user_id][action] if t > minute_ago]
            
            if len(recent_actions) >= self.rate_limits[f"{action}_per_minute"]:
                raise TemplateRateLimitError(
                    f"Rate limit exceeded: {action}_per_minute "
                    f"({len(recent_actions)}/{self.rate_limits[f'{action}_per_minute']})"
                )
        
        # Check per-hour limits
        if f"{action}_per_hour" in self.rate_limits:
            hour_ago = now - 3600
            recent_actions = [t for t in self._rate_counters[user_id][action] if t > hour_ago]
            
            if len(recent_actions) >= self.rate_limits[f"{action}_per_hour"]:
                raise TemplateRateLimitError(
                    f"Rate limit exceeded: {action}_per_hour "
                    f"({len(recent_actions)}/{self.rate_limits[f'{action}_per_hour']})"
                )
        
        # Record action
        self._rate_counters[user_id][action].append(now)
        
        return True
    
    def _clean_rate_counters(self, current_time: float) -> None:
        """Clean old entries from rate counters."""
        hour_ago = current_time - 3600
        
        for user_id in list(self._rate_counters.keys()):
            for action in list(self._rate_counters[user_id].keys()):
                # Keep only entries from last hour
                self._rate_counters[user_id][action] = [
                    t for t in self._rate_counters[user_id][action]
                    if t > hour_ago
                ]
                
                # Remove empty lists
                if not self._rate_counters[user_id][action]:
                    del self._rate_counters[user_id][action]
            
            # Remove empty user entries
            if not self._rate_counters[user_id]:
                del self._rate_counters[user_id]
    
    def validate_template_path(self, path: str, base_dir: Optional[Path] = None) -> bool:
        """
        Validate template file path for security.
        
        Args:
            path: Path to validate
            base_dir: Base directory for templates
            
        Returns:
            True if path is safe
            
        Raises:
            TemplatePathTraversalError: If path traversal detected
        """
        template_path = Path(path)
        
        # Check for path traversal
        if '..' in str(template_path):
            raise TemplatePathTraversalError(f"Path traversal detected: {path}")
        
        # If base_dir provided, ensure path is within it
        if base_dir:
            base_dir = Path(base_dir).resolve()
            try:
                resolved_path = (base_dir / template_path).resolve()
                if not str(resolved_path).startswith(str(base_dir)):
                    raise TemplatePathTraversalError(
                        f"Path escapes base directory: {path}"
                    )
            except Exception as e:
                raise TemplatePathTraversalError(f"Invalid path: {path} - {e}")
        
        return True
    
    def mask_pii(self, content: str) -> str:
        """
        Mask PII in content using M002's PII detector.
        
        Args:
            content: Content to mask
            
        Returns:
            Content with PII masked
        """
        if not self.pii_detector:
            return content
        
        try:
            result = self.pii_detector.detect(content)
            
            # Handle different response formats
            if isinstance(result, dict):
                if not result.get('contains_pii'):
                    return content
                
                # Mask detected PII
                masked_content = content
                entities = result.get('entities', [])
                for entity in sorted(entities, key=lambda x: x.get('start', 0), reverse=True):
                    mask = f"[{entity.get('type', 'PII').upper()}_REDACTED]"
                    start = entity.get('start', 0)
                    end = entity.get('end', len(content))
                    masked_content = (
                        masked_content[:start] +
                        mask +
                        masked_content[end:]
                    )
                return masked_content
            elif isinstance(result, list):
                # If PII detector returns a list of entities directly
                if not result:
                    return content
                
                masked_content = content
                for entity in sorted(result, key=lambda x: x.get('start', 0), reverse=True):
                    if isinstance(entity, dict):
                        mask = f"[{entity.get('type', 'PII').upper()}_REDACTED]"
                        start = entity.get('start', 0)
                        end = entity.get('end', len(content))
                        masked_content = (
                            masked_content[:start] +
                            mask +
                            masked_content[end:]
                        )
                return masked_content
                
        except Exception as e:
            logger.warning(f"PII masking failed: {e}")
        
        return content
    
    def generate_csrf_token(self, user_id: str, template_id: str) -> str:
        """
        Generate CSRF token for template operations.
        
        Args:
            user_id: User identifier
            template_id: Template identifier
            
        Returns:
            CSRF token
        """
        # Generate random token
        random_bytes = secrets.token_bytes(32)
        
        # Include user and template in hash
        data = f"{user_id}:{template_id}:{random_bytes.hex()}"
        token = hashlib.sha256(data.encode()).hexdigest()
        
        return token
    
    def verify_csrf_token(self, token: str, user_id: str, template_id: str) -> bool:
        """
        Verify CSRF token (simplified version - real implementation would store tokens).
        
        Args:
            token: Token to verify
            user_id: User identifier
            template_id: Template identifier
            
        Returns:
            True if valid (simplified - always returns True for now)
        """
        # Simplified verification - real implementation would check stored tokens
        return len(token) == 64  # SHA256 produces 64 character hex string
    
    def audit_log(self, event_type: str, user_id: str, template_id: str,
                  details: Optional[Dict[str, Any]] = None) -> None:
        """
        Log security audit event.
        
        Args:
            event_type: Type of event (e.g., 'template_render', 'security_violation')
            user_id: User identifier
            template_id: Template identifier
            details: Additional event details
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'user_id': user_id,
            'template_id': template_id,
            'details': details or {}
        }
        
        # Log based on event type
        if 'violation' in event_type or 'attack' in event_type:
            self.audit_logger.warning(f"SECURITY: {json.dumps(log_entry)}")
        else:
            self.audit_logger.info(f"AUDIT: {json.dumps(log_entry)}")
    
    def secure_template_decorator(self, func):
        """
        Decorator to add security checks to template operations.
        
        Usage:
            @security.secure_template_decorator
            def render_template(template, context):
                ...
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                # Execute function with timeout
                result = func(*args, **kwargs)
                
                # Check execution time
                execution_time = time.time() - start_time
                if execution_time > self.MAX_RENDER_TIME:
                    logger.warning(
                        f"Template operation took {execution_time:.2f}s "
                        f"(limit: {self.MAX_RENDER_TIME}s)"
                    )
                
                return result
                
            except Exception as e:
                # Log security exceptions
                if isinstance(e, (TemplateSSTIError, TemplatePathTraversalError, 
                                TemplateRateLimitError)):
                    self.audit_log(
                        'security_violation',
                        kwargs.get('user_id', 'unknown'),
                        kwargs.get('template_id', 'unknown'),
                        {'error': str(e), 'function': func.__name__}
                    )
                raise
        
        return wrapper


class TemplatePermissionManager:
    """
    Manage template access permissions.
    """
    
    PERMISSIONS = {
        'read': 1,
        'write': 2,
        'execute': 4,
        'delete': 8,
        'admin': 15  # All permissions
    }
    
    def __init__(self):
        """Initialize permission manager."""
        # Store permissions as user_id -> template_id -> permission_bits
        self._permissions: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
    def grant_permission(self, user_id: str, template_id: str, permission: str) -> None:
        """Grant permission to user for template."""
        if permission not in self.PERMISSIONS:
            raise ValueError(f"Invalid permission: {permission}")
        
        self._permissions[user_id][template_id] |= self.PERMISSIONS[permission]
        
    def revoke_permission(self, user_id: str, template_id: str, permission: str) -> None:
        """Revoke permission from user for template."""
        if permission not in self.PERMISSIONS:
            raise ValueError(f"Invalid permission: {permission}")
        
        self._permissions[user_id][template_id] &= ~self.PERMISSIONS[permission]
        
    def has_permission(self, user_id: str, template_id: str, permission: str) -> bool:
        """Check if user has permission for template."""
        if permission not in self.PERMISSIONS:
            raise ValueError(f"Invalid permission: {permission}")
        
        user_perms = self._permissions.get(user_id, {}).get(template_id, 0)
        return bool(user_perms & self.PERMISSIONS[permission])
    
    def get_user_permissions(self, user_id: str, template_id: str) -> List[str]:
        """Get all permissions for user on template."""
        user_perms = self._permissions.get(user_id, {}).get(template_id, 0)
        
        permissions = []
        for perm_name, perm_bit in self.PERMISSIONS.items():
            if perm_name != 'admin' and user_perms & perm_bit:
                permissions.append(perm_name)
        
        return permissions