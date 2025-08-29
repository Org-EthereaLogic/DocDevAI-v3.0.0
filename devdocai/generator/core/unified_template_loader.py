"""
M004 Document Generator - Unified Template Loader (Refactored).

Combines basic and secure template loading functionality into a single,
configurable component with optional security features.

Pass 4 Refactoring: Consolidates template_loader.py and secure_template_loader.py
to eliminate duplication while preserving all functionality.
"""

import os
import yaml
import hashlib
import logging
import json
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from datetime import datetime
from functools import lru_cache
from enum import Enum

try:
    import jinja2
    from jinja2 import Environment, FileSystemLoader, Template, meta, select_autoescape
    from jinja2.sandbox import SandboxedEnvironment
    from jinja2.exceptions import TemplateError, SecurityError
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

from ...common.performance import LRUCache, ContentCache
from ...common.errors import DevDocAIError
from ...common.logging import get_logger
from ...common.security import AuditLogger, get_audit_logger

logger = get_logger(__name__)


class SecurityLevel(Enum):
    """Security levels for template loading."""
    NONE = "none"  # No security (fastest)
    BASIC = "basic"  # Basic validation only
    STANDARD = "standard"  # Standard security with sandboxing
    STRICT = "strict"  # Maximum security with all checks enabled


class TemplateSecurityError(DevDocAIError):
    """Exception raised for template security violations."""
    pass


@dataclass
class TemplateMetadata:
    """Unified metadata for document templates."""
    
    name: str
    title: str
    type: str  # template type (technical, user, project, etc.)
    category: str  # subcategory within type
    description: Optional[str] = None
    version: str = "1.0"
    author: Optional[str] = None
    created_date: Optional[str] = None
    variables: List[str] = field(default_factory=list)
    optional_variables: List[str] = field(default_factory=list)
    sections: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    content: Optional[str] = None
    file_path: Optional[Path] = None
    
    # Security metadata (optional)
    checksum: Optional[str] = None
    last_validated: Optional[datetime] = None
    trust_level: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            'name': self.name,
            'title': self.title,
            'type': self.type,
            'category': self.category,
            'description': self.description,
            'version': self.version,
            'author': self.author,
            'created_date': self.created_date,
            'variables': self.variables,
            'optional_variables': self.optional_variables,
            'sections': self.sections,
            'tags': self.tags,
            'metadata': self.metadata,
            'checksum': self.checksum,
            'trust_level': self.trust_level
        }


class UnifiedTemplateLoader:
    """
    Unified template loader with configurable security levels.
    
    Features:
    - Backward compatible with both basic and secure loaders
    - Configurable security levels (none, basic, standard, strict)
    - Performance optimized with caching
    - Optional sandboxing and validation
    - Audit logging when security is enabled
    """
    
    # Security constants
    MAX_TEMPLATE_SIZE = 1024 * 1024  # 1MB
    MAX_INCLUDE_DEPTH = 5
    MAX_LOOP_ITERATIONS = 1000
    MAX_TEMPLATE_COMPLEXITY = 100
    
    # Restricted functions in strict mode
    RESTRICTED_FUNCTIONS = {
        'eval', 'exec', 'compile', '__import__', 'open',
        'file', 'input', 'raw_input', 'execfile', 'reload'
    }
    
    # Safe global functions
    SAFE_GLOBALS = {
        'range': range,
        'len': len,
        'str': str,
        'int': int,
        'float': float,
        'bool': bool,
        'list': list,
        'dict': dict,
        'set': set,
        'tuple': tuple,
        'abs': abs,
        'min': min,
        'max': max,
        'sum': sum,
        'round': round,
        'sorted': sorted,
        'reversed': reversed,
        'enumerate': enumerate,
        'zip': zip,
        'any': any,
        'all': all,
    }
    
    def __init__(
        self,
        template_dir: Optional[Path] = None,
        security_level: SecurityLevel = SecurityLevel.STANDARD,
        enable_caching: bool = True,
        cache_size: int = 100,
        enable_audit: bool = None,
        custom_filters: Optional[Dict[str, Any]] = None,
        custom_globals: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Initialize unified template loader.
        
        Args:
            template_dir: Directory containing templates
            security_level: Security level to apply
            enable_caching: Enable template caching
            cache_size: Maximum cache size
            enable_audit: Enable audit logging (auto-enabled for standard/strict)
            custom_filters: Custom Jinja2 filters
            custom_globals: Custom global functions (security validated)
            **kwargs: Additional configuration options
        """
        if not JINJA2_AVAILABLE:
            raise ImportError("Jinja2 is required for template loading")
        
        self.template_dir = template_dir or Path(__file__).parent.parent / "templates"
        self.security_level = security_level
        self.enable_caching = enable_caching
        
        # Auto-enable audit for higher security levels
        if enable_audit is None:
            self.enable_audit = security_level in (SecurityLevel.STANDARD, SecurityLevel.STRICT)
        else:
            self.enable_audit = enable_audit
        
        # Initialize caching
        if self.enable_caching:
            self._template_cache = LRUCache(maxsize=cache_size)
            self._metadata_cache = LRUCache(maxsize=cache_size)
            self._compiled_cache = {}
        
        # Initialize audit logger if needed
        if self.enable_audit:
            self._audit_logger = get_audit_logger()
        
        # Initialize Jinja2 environment based on security level
        self._init_environment(custom_filters, custom_globals)
        
        # Thread lock for cache operations
        self._cache_lock = threading.Lock()
        
        # Template registry
        self._template_registry: Dict[str, TemplateMetadata] = {}
        self._discover_templates()
        
        logger.info(
            f"Initialized UnifiedTemplateLoader with security_level={security_level.value}, "
            f"caching={enable_caching}, audit={self.enable_audit}"
        )
    
    def _init_environment(
        self,
        custom_filters: Optional[Dict[str, Any]] = None,
        custom_globals: Optional[Dict[str, Any]] = None
    ):
        """Initialize Jinja2 environment based on security level."""
        
        if self.security_level == SecurityLevel.NONE:
            # Basic environment with no security
            self.env = Environment(
                loader=FileSystemLoader(str(self.template_dir)),
                autoescape=False,
                trim_blocks=True,
                lstrip_blocks=True
            )
        
        elif self.security_level == SecurityLevel.BASIC:
            # Basic environment with autoescape
            self.env = Environment(
                loader=FileSystemLoader(str(self.template_dir)),
                autoescape=select_autoescape(['html', 'xml']),
                trim_blocks=True,
                lstrip_blocks=True
            )
        
        else:  # STANDARD or STRICT
            # Sandboxed environment with security restrictions
            self.env = SandboxedEnvironment(
                loader=FileSystemLoader(str(self.template_dir)),
                autoescape=select_autoescape(['html', 'xml']),
                trim_blocks=True,
                lstrip_blocks=True,
                max_string_length=self.MAX_TEMPLATE_SIZE
            )
            
            # Apply strict restrictions
            if self.security_level == SecurityLevel.STRICT:
                self.env.globals = self.SAFE_GLOBALS.copy()
                # Disable dangerous operations
                self.env.call_binop = self._safe_binop
                self.env.call_unop = self._safe_unop
        
        # Add custom filters if provided (with validation)
        if custom_filters:
            self._add_custom_filters(custom_filters)
        
        # Add custom globals if provided (with validation)
        if custom_globals and self.security_level != SecurityLevel.STRICT:
            self._add_custom_globals(custom_globals)
    
    def _safe_binop(self, context, operator, left, right):
        """Safe binary operation handler for strict mode."""
        # Prevent potentially dangerous operations
        if operator == 'pow' and isinstance(right, (int, float)) and right > 100:
            raise SecurityError("Power operation with large exponent not allowed")
        return self.env._default_binop(context, operator, left, right)
    
    def _safe_unop(self, context, operator, arg):
        """Safe unary operation handler for strict mode."""
        return self.env._default_unop(context, operator, arg)
    
    def _add_custom_filters(self, filters: Dict[str, Any]):
        """Add custom filters with security validation."""
        for name, func in filters.items():
            if self.security_level == SecurityLevel.STRICT:
                # Validate filter function in strict mode
                if not callable(func):
                    logger.warning(f"Skipping non-callable filter: {name}")
                    continue
                if name in self.RESTRICTED_FUNCTIONS:
                    logger.warning(f"Skipping restricted filter: {name}")
                    continue
            self.env.filters[name] = func
    
    def _add_custom_globals(self, globals_dict: Dict[str, Any]):
        """Add custom globals with security validation."""
        for name, value in globals_dict.items():
            if name not in self.RESTRICTED_FUNCTIONS:
                self.env.globals[name] = value
    
    def _discover_templates(self):
        """Discover and register all available templates."""
        if not self.template_dir.exists():
            logger.warning(f"Template directory does not exist: {self.template_dir}")
            return
        
        for template_file in self.template_dir.glob("**/*.md"):
            try:
                metadata = self._load_template_metadata(template_file)
                if metadata:
                    self._template_registry[metadata.name] = metadata
                    logger.debug(f"Registered template: {metadata.name}")
            except Exception as e:
                logger.error(f"Error loading template {template_file}: {e}")
    
    def _load_template_metadata(self, template_path: Path) -> Optional[TemplateMetadata]:
        """Load and parse template metadata from file."""
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Security check for file size
            if self.security_level != SecurityLevel.NONE:
                if len(content) > self.MAX_TEMPLATE_SIZE:
                    raise TemplateSecurityError(f"Template exceeds size limit: {template_path}")
            
            # Extract YAML frontmatter
            if content.startswith('---'):
                end_marker = content.find('---', 3)
                if end_marker != -1:
                    frontmatter = content[3:end_marker].strip()
                    template_content = content[end_marker + 3:].strip()
                    
                    try:
                        metadata_dict = yaml.safe_load(frontmatter) or {}
                    except yaml.YAMLError as e:
                        logger.error(f"Invalid YAML in template {template_path}: {e}")
                        return None
                    
                    # Create metadata object
                    metadata = TemplateMetadata(
                        name=metadata_dict.get('name', template_path.stem),
                        title=metadata_dict.get('title', ''),
                        type=metadata_dict.get('type', 'general'),
                        category=metadata_dict.get('category', 'default'),
                        description=metadata_dict.get('description'),
                        version=metadata_dict.get('version', '1.0'),
                        author=metadata_dict.get('author'),
                        created_date=metadata_dict.get('created_date'),
                        variables=metadata_dict.get('variables', []),
                        optional_variables=metadata_dict.get('optional_variables', []),
                        sections=metadata_dict.get('sections', []),
                        tags=metadata_dict.get('tags', []),
                        metadata=metadata_dict.get('metadata', {}),
                        content=template_content,
                        file_path=template_path
                    )
                    
                    # Add security metadata if enabled
                    if self.security_level in (SecurityLevel.STANDARD, SecurityLevel.STRICT):
                        metadata.checksum = hashlib.sha256(content.encode()).hexdigest()
                        metadata.last_validated = datetime.now()
                        metadata.trust_level = self._calculate_trust_level(template_path)
                    
                    return metadata
            
        except Exception as e:
            logger.error(f"Error loading template metadata from {template_path}: {e}")
        
        return None
    
    def _calculate_trust_level(self, template_path: Path) -> str:
        """Calculate trust level for a template."""
        # Simple trust calculation based on location
        if "system" in str(template_path) or "core" in str(template_path):
            return "system"
        elif "user" in str(template_path):
            return "user"
        else:
            return "untrusted"
    
    def load_template(
        self,
        template_name: str,
        validate: Optional[bool] = None,
        use_cache: Optional[bool] = None
    ) -> Tuple[Template, TemplateMetadata]:
        """
        Load a template by name with optional validation.
        
        Args:
            template_name: Name of template to load
            validate: Override validation setting
            use_cache: Override cache setting
            
        Returns:
            Tuple of (compiled template, metadata)
        """
        # Use instance defaults if not specified
        if validate is None:
            validate = self.security_level != SecurityLevel.NONE
        if use_cache is None:
            use_cache = self.enable_caching
        
        # Check cache first
        if use_cache and template_name in self._compiled_cache:
            logger.debug(f"Using cached template: {template_name}")
            return self._compiled_cache[template_name], self._template_registry[template_name]
        
        # Get metadata
        if template_name not in self._template_registry:
            raise DevDocAIError(f"Template not found: {template_name}")
        
        metadata = self._template_registry[template_name]
        
        # Validate if required
        if validate:
            self._validate_template(metadata)
        
        # Load and compile template
        try:
            template = self.env.get_template(f"{template_name}.md")
            
            # Cache if enabled
            if use_cache:
                with self._cache_lock:
                    self._compiled_cache[template_name] = template
            
            # Audit log if enabled
            if self.enable_audit:
                self._audit_logger.log_event(
                    "template_loaded",
                    template=template_name,
                    security_level=self.security_level.value
                )
            
            return template, metadata
            
        except Exception as e:
            logger.error(f"Error loading template {template_name}: {e}")
            raise DevDocAIError(f"Failed to load template: {e}")
    
    def _validate_template(self, metadata: TemplateMetadata):
        """Validate template based on security level."""
        if self.security_level == SecurityLevel.NONE:
            return
        
        # Basic validation
        if not metadata.content:
            raise TemplateSecurityError("Template has no content")
        
        if self.security_level in (SecurityLevel.STANDARD, SecurityLevel.STRICT):
            # Check for dangerous patterns
            dangerous_patterns = [
                r'\{\{.*eval.*\}\}',
                r'\{\{.*exec.*\}\}',
                r'\{\{.*__.*\}\}',
                r'\{\{.*import.*\}\}',
            ]
            
            for pattern in dangerous_patterns:
                if re.search(pattern, metadata.content, re.IGNORECASE):
                    raise TemplateSecurityError(f"Dangerous pattern detected in template")
            
            # Verify checksum if available
            if metadata.checksum:
                current_checksum = hashlib.sha256(metadata.content.encode()).hexdigest()
                if current_checksum != metadata.checksum:
                    raise TemplateSecurityError("Template integrity check failed")
    
    def render_template(
        self,
        template_name: str,
        context: Dict[str, Any],
        validate_context: Optional[bool] = None,
        timeout: Optional[int] = None
    ) -> str:
        """
        Render a template with the given context.
        
        Args:
            template_name: Name of template to render
            context: Template context variables
            validate_context: Validate context before rendering
            timeout: Rendering timeout in seconds (for strict mode)
            
        Returns:
            Rendered template string
        """
        if validate_context is None:
            validate_context = self.security_level != SecurityLevel.NONE
        
        # Load template
        template, metadata = self.load_template(template_name)
        
        # Validate context if required
        if validate_context:
            self._validate_context(context, metadata)
        
        # Render with timeout protection in strict mode
        if self.security_level == SecurityLevel.STRICT and timeout:
            return self._render_with_timeout(template, context, timeout)
        else:
            return template.render(**context)
    
    def _validate_context(self, context: Dict[str, Any], metadata: TemplateMetadata):
        """Validate template context against metadata."""
        # Check required variables
        missing_vars = set(metadata.variables) - set(context.keys())
        if missing_vars:
            raise DevDocAIError(f"Missing required variables: {missing_vars}")
        
        # Validate context types in strict mode
        if self.security_level == SecurityLevel.STRICT:
            for key, value in context.items():
                if callable(value) and not isinstance(value, (str, int, float, bool, list, dict)):
                    raise TemplateSecurityError(f"Callable values not allowed in strict mode: {key}")
    
    def _render_with_timeout(self, template: Template, context: Dict[str, Any], timeout: int) -> str:
        """Render template with timeout protection."""
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Template rendering timeout")
        
        # Set timeout signal
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)
        
        try:
            result = template.render(**context)
            signal.alarm(0)  # Cancel timeout
            return result
        except TimeoutError:
            raise TemplateSecurityError(f"Template rendering exceeded timeout of {timeout} seconds")
    
    def list_templates(self, filter_type: Optional[str] = None) -> List[TemplateMetadata]:
        """List all available templates with optional filtering."""
        templates = list(self._template_registry.values())
        
        if filter_type:
            templates = [t for t in templates if t.type == filter_type]
        
        return templates
    
    def clear_cache(self):
        """Clear all template caches."""
        if self.enable_caching:
            with self._cache_lock:
                self._compiled_cache.clear()
                if hasattr(self, '_template_cache'):
                    self._template_cache.clear()
                if hasattr(self, '_metadata_cache'):
                    self._metadata_cache.clear()
            logger.info("Template cache cleared")
    
    def get_template_info(self, template_name: str) -> Dict[str, Any]:
        """Get detailed information about a template."""
        if template_name not in self._template_registry:
            raise DevDocAIError(f"Template not found: {template_name}")
        
        metadata = self._template_registry[template_name]
        return metadata.to_dict()
    
    # Backward compatibility methods
    
    def load(self, template_name: str) -> Tuple[Template, TemplateMetadata]:
        """Backward compatible load method."""
        return self.load_template(template_name)
    
    def render(self, template_name: str, **context) -> str:
        """Backward compatible render method."""
        return self.render_template(template_name, context)
    
    def get_metadata(self, template_name: str) -> TemplateMetadata:
        """Get template metadata."""
        if template_name not in self._template_registry:
            raise DevDocAIError(f"Template not found: {template_name}")
        return self._template_registry[template_name]


# Backward compatibility aliases
TemplateLoader = UnifiedTemplateLoader  # Alias for basic loader compatibility
SecureTemplateLoader = UnifiedTemplateLoader  # Alias for secure loader compatibility


def create_template_loader(
    security_level: Union[str, SecurityLevel] = "standard",
    **kwargs
) -> UnifiedTemplateLoader:
    """
    Factory function to create a template loader with specified security level.
    
    Args:
        security_level: Security level (none/basic/standard/strict) or SecurityLevel enum
        **kwargs: Additional configuration options
        
    Returns:
        Configured UnifiedTemplateLoader instance
    """
    if isinstance(security_level, str):
        security_level = SecurityLevel(security_level.lower())
    
    return UnifiedTemplateLoader(security_level=security_level, **kwargs)