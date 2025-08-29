"""
M004 Document Generator - Secure template loader with sandboxing.

Provides secure template loading with Jinja2 sandboxing, access controls,
and template integrity verification.
"""

import os
import hashlib
import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime
import threading
import re

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    from jinja2.sandbox import SandboxedEnvironment
    from jinja2.exceptions import TemplateError, SecurityError
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

from .template_loader import TemplateLoader, TemplateMetadata
from ...common.logging import get_logger
from ...common.errors import DevDocAIError
from ...common.security import AuditLogger, get_audit_logger

logger = get_logger(__name__)


class TemplateSecurityError(DevDocAIError):
    """Exception raised for template security violations."""
    pass


class SecureTemplateEnvironment:
    """
    Secure Jinja2 template environment with comprehensive sandboxing.
    
    Security Features:
    - Sandboxed execution environment
    - Restricted function access
    - Template complexity limits
    - Execution timeout protection
    - Access control verification
    - Template integrity checks
    """
    
    # Allowed functions and filters in templates
    ALLOWED_FUNCTIONS = {
        'range', 'len', 'str', 'int', 'float', 'bool', 'list', 'dict', 'set',
        'min', 'max', 'sum', 'abs', 'round', 'sorted', 'reversed',
        'upper', 'lower', 'title', 'capitalize', 'strip', 'split', 'join',
        'replace', 'format', 'startswith', 'endswith'
    }
    
    ALLOWED_FILTERS = {
        'upper', 'lower', 'title', 'capitalize', 'trim', 'strip',
        'replace', 'regex_replace', 'length', 'first', 'last',
        'join', 'split', 'slice', 'batch', 'groupby',
        'sort', 'reverse', 'unique', 'max', 'min', 'sum',
        'map', 'select', 'reject', 'selectattr', 'rejectattr',
        'default', 'safe', 'escape', 'urlencode', 'wordwrap'
    }
    
    # Blocked attributes and methods
    BLOCKED_ATTRIBUTES = {
        '__class__', '__dict__', '__doc__', '__globals__', '__module__',
        '__name__', '__qualname__', '__annotations__', '__file__',
        'func_globals', 'gi_frame', 'gi_code', 'cr_frame', 'cr_code',
        '__import__', 'compile', 'eval', 'exec', 'execfile', 'file',
        'input', 'open', 'raw_input', 'reload', '__builtins__'
    }
    
    # Template complexity limits
    MAX_TEMPLATE_SIZE = 100 * 1024  # 100KB
    MAX_RENDER_TIME = 30  # seconds
    MAX_LOOP_ITERATIONS = 1000
    MAX_RECURSION_DEPTH = 10
    MAX_INCLUDE_DEPTH = 5
    
    def __init__(self, template_dir: Path, strict_mode: bool = True):
        """
        Initialize secure template environment.
        
        Args:
            template_dir: Directory containing templates
            strict_mode: Enable strict security mode
        """
        self.template_dir = template_dir
        self.strict_mode = strict_mode
        self.audit_logger = get_audit_logger()
        self._lock = threading.Lock()
        
        # Template access tracking
        self.access_log: Dict[str, List[datetime]] = {}
        self.template_checksums: Dict[str, str] = {}
        
        if not JINJA2_AVAILABLE:
            logger.warning("Jinja2 not available. Template functionality will be limited.")
            self.environment = None
            return
        
        # Create sandboxed environment
        self.environment = SandboxedEnvironment(
            loader=FileSystemLoader(str(template_dir), encoding='utf-8'),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True
        )
        
        # Configure security restrictions
        self._configure_sandbox()
        
        # Load template metadata and verify integrity
        self._load_and_verify_templates()
        
        logger.info(f"Secure template environment initialized: {template_dir}, strict={strict_mode}")
    
    def _configure_sandbox(self):
        """Configure Jinja2 sandbox security restrictions."""
        if not self.environment:
            return
        
        # Set allowed globals
        safe_globals = {
            name: getattr(__builtins__, name) 
            for name in self.ALLOWED_FUNCTIONS 
            if hasattr(__builtins__, name)
        }
        self.environment.globals.update(safe_globals)
        
        # Configure filters (only allow safe ones)
        allowed_filters = {
            name: filter_func 
            for name, filter_func in self.environment.filters.items()
            if name in self.ALLOWED_FILTERS
        }
        self.environment.filters = allowed_filters
        
        # Install security callbacks
        self.environment.overlayed = True
        
        # Custom attribute access control
        original_getattr = self.environment.getattr
        
        def secure_getattr(obj, name, default=None):
            if name in self.BLOCKED_ATTRIBUTES:
                raise SecurityError(f"Access to '{name}' is not allowed")
            return original_getattr(obj, name, default)
        
        self.environment.getattr = secure_getattr
    
    def _load_and_verify_templates(self):
        """Load templates and calculate integrity checksums."""
        if not self.template_dir.exists():
            logger.warning(f"Template directory does not exist: {self.template_dir}")
            return
        
        for template_file in self.template_dir.glob('**/*.j2'):
            try:
                content = template_file.read_text(encoding='utf-8')
                checksum = hashlib.sha256(content.encode()).hexdigest()
                
                template_name = str(template_file.relative_to(self.template_dir))
                self.template_checksums[template_name] = checksum
                
                logger.debug(f"Template integrity recorded: {template_name}")
                
            except Exception as e:
                logger.error(f"Failed to load template {template_file}: {e}")
    
    def render_template_secure(
        self, 
        template_name: str, 
        variables: Dict[str, Any],
        client_id: str = 'anonymous'
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Securely render a template with comprehensive security checks.
        
        Args:
            template_name: Name of template to render
            variables: Template variables
            client_id: Client identifier for audit logging
            
        Returns:
            Tuple of (rendered_content, security_metadata)
        """
        if not self.environment:
            raise TemplateSecurityError("Template environment not available")
        
        security_metadata = {
            'template_name': template_name,
            'client_id': client_id,
            'timestamp': datetime.now().isoformat(),
            'security_checks': [],
            'warnings': []
        }
        
        try:
            # Pre-render security checks
            self._pre_render_security_checks(template_name, variables, client_id)
            security_metadata['security_checks'].append('pre_render_passed')
            
            # Load and verify template
            template = self._load_template_secure(template_name)
            security_metadata['security_checks'].append('template_loaded')
            
            # Verify template integrity
            if not self._verify_template_integrity(template_name):
                raise TemplateSecurityError(f"Template integrity check failed: {template_name}")
            security_metadata['security_checks'].append('integrity_verified')
            
            # Sanitize variables
            sanitized_variables = self._sanitize_template_variables(variables)
            security_metadata['security_checks'].append('variables_sanitized')
            
            # Render with timeout protection
            rendered_content = self._render_with_protection(template, sanitized_variables)
            security_metadata['security_checks'].append('render_completed')
            
            # Post-render security validation
            self._post_render_security_checks(rendered_content, template_name)
            security_metadata['security_checks'].append('post_render_passed')
            
            # Log successful render
            self._log_template_access(template_name, client_id, 'render_success')
            
            logger.debug(f"Template rendered securely: {template_name} for client {client_id}")
            return rendered_content, security_metadata
            
        except Exception as e:
            self._log_template_access(template_name, client_id, 'render_failed', str(e))
            logger.error(f"Secure template render failed: {e}")
            raise TemplateSecurityError(f"Template rendering failed: {str(e)}")
    
    def _pre_render_security_checks(
        self, 
        template_name: str, 
        variables: Dict[str, Any], 
        client_id: str
    ):
        """Pre-render security validation."""
        
        # Check template access permissions
        if not self._check_template_access_allowed(template_name, client_id):
            raise TemplateSecurityError(f"Access denied to template: {template_name}")
        
        # Validate template name
        if not self._is_safe_template_name(template_name):
            raise TemplateSecurityError(f"Invalid template name: {template_name}")
        
        # Check variable complexity
        var_size = len(json.dumps(variables, default=str))
        if var_size > 1024 * 1024:  # 1MB limit
            raise TemplateSecurityError("Template variables too large")
        
        # Check for dangerous variable names
        dangerous_vars = ['__class__', '__dict__', '__globals__', 'self', 'config']
        for var_name in variables:
            if var_name in dangerous_vars:
                raise TemplateSecurityError(f"Dangerous variable name: {var_name}")
    
    def _load_template_secure(self, template_name: str):
        """Securely load template with size and content validation."""
        try:
            template_path = self.template_dir / template_name
            
            # Check template exists and is within template directory
            if not template_path.exists():
                raise TemplateSecurityError(f"Template not found: {template_name}")
            
            if not str(template_path.resolve()).startswith(str(self.template_dir.resolve())):
                raise TemplateSecurityError(f"Template path traversal attempt: {template_name}")
            
            # Check template size
            template_size = template_path.stat().st_size
            if template_size > self.MAX_TEMPLATE_SIZE:
                raise TemplateSecurityError(f"Template too large: {template_size} bytes")
            
            # Load template content and validate
            content = template_path.read_text(encoding='utf-8')
            if not self._validate_template_content(content):
                raise TemplateSecurityError(f"Template contains unsafe content: {template_name}")
            
            # Get template from Jinja2 environment
            template = self.environment.get_template(template_name)
            return template
            
        except TemplateError as e:
            raise TemplateSecurityError(f"Template error: {str(e)}")
    
    def _validate_template_content(self, content: str) -> bool:
        """Validate template content for security issues."""
        
        # Check for dangerous template constructs
        dangerous_patterns = [
            r'config\.',  # Config object access
            r'request\.',  # Request object access
            r'session\.',  # Session object access
            r'__import__',  # Import statements
            r'eval\s*\(',  # eval() calls
            r'exec\s*\(',  # exec() calls
            r'open\s*\(',  # file operations
            r'import\s+\w+',  # import statements
            r'from\s+\w+\s+import',  # from import statements
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                logger.warning(f"Dangerous pattern detected in template: {pattern}")
                if self.strict_mode:
                    return False
        
        return True
    
    def _verify_template_integrity(self, template_name: str) -> bool:
        """Verify template hasn't been tampered with."""
        if template_name not in self.template_checksums:
            logger.warning(f"No integrity checksum for template: {template_name}")
            return True  # Allow if no checksum recorded
        
        try:
            template_path = self.template_dir / template_name
            current_content = template_path.read_text(encoding='utf-8')
            current_checksum = hashlib.sha256(current_content.encode()).hexdigest()
            
            expected_checksum = self.template_checksums[template_name]
            
            if current_checksum != expected_checksum:
                logger.error(f"Template integrity check failed: {template_name}")
                self.audit_logger.log_event('template_integrity_failure', {
                    'template_name': template_name,
                    'expected_checksum': expected_checksum,
                    'current_checksum': current_checksum
                })
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Template integrity check error: {e}")
            return False
    
    def _sanitize_template_variables(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize template variables for safe rendering."""
        sanitized = {}
        
        for key, value in variables.items():
            # Ensure key is safe
            safe_key = re.sub(r'[^a-zA-Z0-9_]', '_', key)
            
            if isinstance(value, str):
                # Basic HTML escaping for string values
                sanitized[safe_key] = self._escape_string(value)
            elif isinstance(value, (int, float, bool)):
                sanitized[safe_key] = value
            elif isinstance(value, (list, tuple)):
                sanitized[safe_key] = [self._escape_string(str(item)) if isinstance(item, str) else item for item in value]
            elif isinstance(value, dict):
                sanitized[safe_key] = {k: self._escape_string(str(v)) if isinstance(v, str) else v for k, v in value.items()}
            else:
                # Convert other types to safe strings
                sanitized[safe_key] = self._escape_string(str(value))
        
        return sanitized
    
    def _escape_string(self, value: str) -> str:
        """Escape potentially dangerous string content."""
        import html
        # HTML escape
        escaped = html.escape(value)
        
        # Additional escaping for template contexts
        escaped = escaped.replace('{', '&#123;')
        escaped = escaped.replace('}', '&#125;')
        
        return escaped
    
    def _render_with_protection(self, template, variables: Dict[str, Any]) -> str:
        """Render template with timeout and resource protection."""
        import signal
        import threading
        
        result = {'content': '', 'error': None}
        
        def render_worker():
            try:
                result['content'] = template.render(**variables)
            except Exception as e:
                result['error'] = e
        
        # Use thread-based timeout (signal-based timeout doesn't work well with Jinja2)
        worker_thread = threading.Thread(target=render_worker)
        worker_thread.start()
        worker_thread.join(timeout=self.MAX_RENDER_TIME)
        
        if worker_thread.is_alive():
            raise TemplateSecurityError(f"Template rendering timeout ({self.MAX_RENDER_TIME}s)")
        
        if result['error']:
            raise result['error']
        
        return result['content']
    
    def _post_render_security_checks(self, content: str, template_name: str):
        """Post-render security validation."""
        
        # Check rendered content size
        if len(content) > 10 * 1024 * 1024:  # 10MB limit
            raise TemplateSecurityError("Rendered content too large")
        
        # Check for potential information disclosure
        dangerous_content_patterns = [
            r'password\s*[:=]\s*\w+',
            r'secret\s*[:=]\s*\w+',
            r'api_key\s*[:=]\s*\w+',
            r'token\s*[:=]\s*\w+',
        ]
        
        for pattern in dangerous_content_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                logger.warning(f"Potential sensitive data in rendered template: {template_name}")
                # Don't fail in non-strict mode, just log
                if self.strict_mode:
                    raise TemplateSecurityError("Rendered content contains potential sensitive data")
    
    def _is_safe_template_name(self, template_name: str) -> bool:
        """Check if template name is safe."""
        # Allow only alphanumeric, hyphens, underscores, dots, and forward slashes
        safe_pattern = re.compile(r'^[a-zA-Z0-9._/-]+$')
        
        if not safe_pattern.match(template_name):
            return False
        
        # Prevent path traversal
        if '..' in template_name or template_name.startswith('/'):
            return False
        
        return True
    
    def _check_template_access_allowed(self, template_name: str, client_id: str) -> bool:
        """Check if client has access to template."""
        # For now, implement basic rate limiting
        # In production, this would integrate with proper access control
        
        with self._lock:
            now = datetime.now()
            key = f"{client_id}:{template_name}"
            
            if key not in self.access_log:
                self.access_log[key] = []
            
            # Remove old access attempts (last hour)
            cutoff = now.replace(hour=now.hour-1) if now.hour > 0 else now.replace(day=now.day-1, hour=23)
            self.access_log[key] = [access for access in self.access_log[key] if access > cutoff]
            
            # Check rate limit (50 template renders per hour per client)
            if len(self.access_log[key]) >= 50:
                return False
            
            self.access_log[key].append(now)
            return True
    
    def _log_template_access(
        self, 
        template_name: str, 
        client_id: str, 
        action: str, 
        details: Optional[str] = None
    ):
        """Log template access for audit purposes."""
        event_data = {
            'template_name': template_name,
            'client_id': client_id,
            'action': action,
            'timestamp': datetime.now().isoformat()
        }
        
        if details:
            event_data['details'] = details
        
        self.audit_logger.log_event('template_access', event_data)
    
    def get_template_security_status(self, template_name: str) -> Dict[str, Any]:
        """Get security status for a template."""
        status = {
            'template_name': template_name,
            'exists': False,
            'integrity_verified': False,
            'content_safe': False,
            'size_ok': False,
            'access_count_last_hour': 0
        }
        
        try:
            template_path = self.template_dir / template_name
            
            if template_path.exists():
                status['exists'] = True
                
                # Check size
                template_size = template_path.stat().st_size
                status['size_ok'] = template_size <= self.MAX_TEMPLATE_SIZE
                
                # Check integrity
                status['integrity_verified'] = self._verify_template_integrity(template_name)
                
                # Check content
                content = template_path.read_text(encoding='utf-8')
                status['content_safe'] = self._validate_template_content(content)
                
                # Check access count
                access_count = 0
                for key, accesses in self.access_log.items():
                    if key.endswith(f":{template_name}"):
                        access_count += len(accesses)
                status['access_count_last_hour'] = access_count
        
        except Exception as e:
            logger.error(f"Failed to get template security status: {e}")
        
        return status
    
    def refresh_template_checksums(self):
        """Refresh template integrity checksums."""
        logger.info("Refreshing template integrity checksums")
        self.template_checksums.clear()
        self._load_and_verify_templates()


class SecureTemplateLoader(TemplateLoader):
    """
    Secure template loader with enhanced security controls.
    
    Extends the base TemplateLoader with:
    - Secure template environment
    - Access control verification
    - Template integrity checking
    - Comprehensive audit logging
    """
    
    def __init__(self, template_dir: Path, strict_mode: bool = True):
        """Initialize secure template loader."""
        super().__init__(template_dir)
        self.secure_environment = SecureTemplateEnvironment(template_dir, strict_mode)
        self.audit_logger = get_audit_logger()
        
        logger.info(f"SecureTemplateLoader initialized: {template_dir}")
    
    def render_template_secure(
        self, 
        template_name: str, 
        variables: Dict[str, Any],
        client_id: str = 'anonymous'
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Render template with comprehensive security controls.
        
        Args:
            template_name: Template to render
            variables: Template variables
            client_id: Client identifier
            
        Returns:
            Tuple of (rendered_content, security_metadata)
        """
        try:
            return self.secure_environment.render_template_secure(
                template_name, variables, client_id
            )
        except Exception as e:
            self.audit_logger.log_event('template_render_failed', {
                'template_name': template_name,
                'client_id': client_id,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            raise
    
    def get_template_security_report(self) -> Dict[str, Any]:
        """Get comprehensive security report for all templates."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_templates': len(self.templates),
            'templates': {},
            'security_summary': {
                'safe_templates': 0,
                'unsafe_templates': 0,
                'integrity_failures': 0
            }
        }
        
        for template_name in self.templates:
            template_status = self.secure_environment.get_template_security_status(template_name)
            report['templates'][template_name] = template_status
            
            # Update summary
            if (template_status['content_safe'] and 
                template_status['integrity_verified'] and 
                template_status['size_ok']):
                report['security_summary']['safe_templates'] += 1
            else:
                report['security_summary']['unsafe_templates'] += 1
            
            if not template_status['integrity_verified']:
                report['security_summary']['integrity_failures'] += 1
        
        return report