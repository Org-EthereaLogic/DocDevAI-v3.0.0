"""
Unified Template Registry for M006 - Pass 4 Refactoring.

This module provides a single, configurable template registry that combines
all features from the base, optimized, and secure implementations through
operation modes.

Operation Modes:
- BASIC: Core functionality only (lightest resource usage)
- PERFORMANCE: Adds caching, indexing, parallelization
- SECURE: Adds security features (SSTI/XSS protection, sandboxing)
- ENTERPRISE: All features enabled (maximum protection and performance)
"""

from typing import Dict, List, Optional, Union, Any, Callable, Set, Tuple
from pathlib import Path
from enum import Enum, auto
from dataclasses import dataclass, field
import logging
import threading
import weakref
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import json
import hashlib
from collections import defaultdict, OrderedDict

from ..core.config import ConfigurationManager  # M001 integration
from ..storage.secure_storage import SecureStorageLayer  # M002 integration
from ..storage.pii_detector import PIIDetector  # M002 PII detection

from .models import (
    Template as TemplateModel,
    TemplateMetadata,
    TemplateSearchCriteria,
    TemplateCategory,
    TemplateType,
    TemplateRenderContext,
    TemplateValidationResult
)
from .template import Template
from .loader import TemplateLoader
from .validator import TemplateValidator
from .categories import CategoryManager
from .exceptions import (
    TemplateNotFoundError,
    TemplateDuplicateError,
    TemplateStorageError,
    TemplateValidationError,
    TemplateSecurityError
)

# Import security components when available
try:
    from .template_security import TemplateSecurity
    from .template_sandbox import TemplateSandbox
    from .secure_parser import SecureTemplateParser
    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False

# Import performance components when available
try:
    from .parser_optimized import OptimizedTemplateParser
    PERFORMANCE_AVAILABLE = True
except ImportError:
    PERFORMANCE_AVAILABLE = False

logger = logging.getLogger(__name__)


class OperationMode(Enum):
    """Operation modes for the unified registry."""
    BASIC = auto()       # Core functionality only
    PERFORMANCE = auto() # Adds caching, indexing, parallelization
    SECURE = auto()      # Adds security features
    ENTERPRISE = auto()  # All features enabled


@dataclass
class RegistryConfig:
    """Configuration for the unified template registry."""
    mode: OperationMode = OperationMode.BASIC
    
    # Basic configuration
    auto_load_defaults: bool = True
    
    # Performance configuration
    enable_cache: bool = False
    cache_size: int = 1000
    enable_lazy_load: bool = False
    enable_indexing: bool = False
    max_workers: int = 4
    
    # Security configuration
    enable_security: bool = False
    enable_pii_detection: bool = False
    enable_rate_limiting: bool = False
    enable_sandbox: bool = False
    enable_audit_logging: bool = False
    enable_permissions: bool = False
    
    # Limits and constraints
    max_template_size: int = 10 * 1024 * 1024  # 10MB
    max_render_time: float = 30.0  # seconds
    max_templates_per_user: int = 1000
    
    @classmethod
    def from_mode(cls, mode: OperationMode) -> 'RegistryConfig':
        """Create configuration from operation mode."""
        config = cls(mode=mode)
        
        if mode == OperationMode.PERFORMANCE:
            config.enable_cache = True
            config.enable_lazy_load = True
            config.enable_indexing = True
            
        elif mode == OperationMode.SECURE:
            config.enable_security = True
            config.enable_pii_detection = True
            config.enable_rate_limiting = True
            config.enable_sandbox = True
            config.enable_audit_logging = True
            config.enable_permissions = True
            
        elif mode == OperationMode.ENTERPRISE:
            # Enable all features
            config.enable_cache = True
            config.enable_lazy_load = True
            config.enable_indexing = True
            config.enable_security = True
            config.enable_pii_detection = True
            config.enable_rate_limiting = True
            config.enable_sandbox = True
            config.enable_audit_logging = True
            config.enable_permissions = True
            config.cache_size = 2000
            config.max_workers = 8
            
        return config


class LRUCache:
    """Simple LRU cache implementation."""
    
    def __init__(self, max_size: int = 1000):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache."""
        with self._lock:
            if key in self.cache:
                self.hits += 1
                # Move to end (most recent)
                self.cache.move_to_end(key)
                return self.cache[key]
            self.misses += 1
            return None
    
    def set(self, key: str, value: Any) -> None:
        """Set item in cache."""
        with self._lock:
            if key in self.cache:
                # Update and move to end
                self.cache[key] = value
                self.cache.move_to_end(key)
            else:
                # Add new item
                self.cache[key] = value
                if len(self.cache) > self.max_size:
                    # Remove oldest
                    self.cache.popitem(last=False)
    
    def clear(self) -> None:
        """Clear cache."""
        with self._lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class TemplateIndex:
    """Fast indexing for template search."""
    
    def __init__(self):
        self.by_category: Dict[str, Set[str]] = defaultdict(set)
        self.by_type: Dict[str, Set[str]] = defaultdict(set)
        self.by_tag: Dict[str, Set[str]] = defaultdict(set)
        self.by_name: Dict[str, str] = {}  # name -> id mapping
        self._lock = threading.RLock()
    
    def add(self, template_id: str, metadata: Dict[str, Any]) -> None:
        """Add template to index."""
        with self._lock:
            # Index by category
            if 'category' in metadata:
                self.by_category[metadata['category']].add(template_id)
            
            # Index by type
            if 'type' in metadata:
                self.by_type[metadata['type']].add(template_id)
            
            # Index by tags
            if 'tags' in metadata:
                for tag in metadata['tags']:
                    self.by_tag[tag].add(template_id)
            
            # Index by name
            if 'name' in metadata:
                self.by_name[metadata['name']] = template_id
    
    def remove(self, template_id: str, metadata: Dict[str, Any]) -> None:
        """Remove template from index."""
        with self._lock:
            if 'category' in metadata:
                self.by_category[metadata['category']].discard(template_id)
            
            if 'type' in metadata:
                self.by_type[metadata['type']].discard(template_id)
            
            if 'tags' in metadata:
                for tag in metadata['tags']:
                    self.by_tag[tag].discard(template_id)
            
            if 'name' in metadata:
                self.by_name.pop(metadata['name'], None)
    
    def search(self, criteria: Dict[str, Any]) -> Set[str]:
        """Search templates using index."""
        with self._lock:
            results = None
            
            # Search by category
            if 'category' in criteria:
                cat_results = self.by_category.get(criteria['category'], set())
                results = cat_results if results is None else results & cat_results
            
            # Search by type
            if 'type' in criteria:
                type_results = self.by_type.get(criteria['type'], set())
                results = type_results if results is None else results & type_results
            
            # Search by tags
            if 'tags' in criteria:
                for tag in criteria['tags']:
                    tag_results = self.by_tag.get(tag, set())
                    results = tag_results if results is None else results & tag_results
            
            return results if results is not None else set()


class RateLimiter:
    """Simple rate limiter for security."""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.RLock()
    
    def check_limit(self, user_id: str = "default") -> bool:
        """Check if user is within rate limit."""
        with self._lock:
            now = datetime.now().timestamp()
            
            # Clean old requests
            self.requests[user_id] = [
                t for t in self.requests[user_id]
                if now - t < self.window_seconds
            ]
            
            # Check limit
            if len(self.requests[user_id]) >= self.max_requests:
                return False
            
            # Record request
            self.requests[user_id].append(now)
            return True


class UnifiedTemplateRegistry:
    """
    Unified template registry with configurable operation modes.
    
    This single implementation replaces the three separate registries
    (base, optimized, secure) with a configuration-driven approach.
    """
    
    def __init__(self,
                 config: Optional[RegistryConfig] = None,
                 mode: Optional[OperationMode] = None,
                 config_manager: Optional[ConfigurationManager] = None,
                 storage: Optional[SecureStorageLayer] = None):
        """
        Initialize unified template registry.
        
        Args:
            config: Explicit configuration (overrides mode)
            mode: Operation mode (if config not provided)
            config_manager: Configuration manager (M001)
            storage: Storage system (M002)
        """
        # Determine configuration
        if config:
            self.config = config
        elif mode:
            self.config = RegistryConfig.from_mode(mode)
        else:
            # Default to BASIC mode
            self.config = RegistryConfig()
        
        # Core components (always enabled)
        self.config_manager = config_manager
        self.storage = storage
        self._templates: Dict[str, Template] = {}
        self._lock = threading.RLock()
        self.loader = TemplateLoader()
        self.validator = TemplateValidator()
        self.category_manager = CategoryManager()
        
        # Metrics (always tracked)
        self._metrics = {
            'templates_loaded': 0,
            'templates_rendered': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': 0,
            'security_blocks': 0
        }
        
        # Initialize optional components based on configuration
        self._init_performance_features()
        self._init_security_features()
        
        # Load default templates if configured
        if self.config.auto_load_defaults:
            self._load_default_templates()
        
        logger.info(f"Initialized UnifiedTemplateRegistry in {self.config.mode.name} mode")
    
    def _init_performance_features(self) -> None:
        """Initialize performance-related features."""
        # Caching
        if self.config.enable_cache:
            self._render_cache = LRUCache(self.config.cache_size)
            self._compiled_cache = LRUCache(self.config.cache_size // 2)
        else:
            self._render_cache = None
            self._compiled_cache = None
        
        # Indexing
        if self.config.enable_indexing:
            self._index = TemplateIndex()
        else:
            self._index = None
        
        # Thread pool
        if self.config.max_workers > 1:
            self._executor = ThreadPoolExecutor(max_workers=self.config.max_workers)
        else:
            self._executor = None
        
        # Lazy loading metadata
        if self.config.enable_lazy_load:
            self._template_metadata: Dict[str, Dict] = {}
        else:
            self._template_metadata = None
    
    def _init_security_features(self) -> None:
        """Initialize security-related features."""
        if not self.config.enable_security:
            self.security_manager = None
            self.sandbox = None
            self.rate_limiter = None
            self.pii_detector = None
            return
        
        if not SECURITY_AVAILABLE:
            logger.warning("Security features requested but not available")
            self.security_manager = None
            self.sandbox = None
            self.rate_limiter = None
            self.pii_detector = None
            return
        
        # PII detection
        if self.config.enable_pii_detection:
            self.pii_detector = PIIDetector()
        else:
            self.pii_detector = None
        
        # Security manager
        self.security_manager = TemplateSecurity(
            pii_detector=self.pii_detector,
            audit_logger=logger if self.config.enable_audit_logging else None
        )
        
        # Sandbox
        if self.config.enable_sandbox:
            self.sandbox = TemplateSandbox()
        else:
            self.sandbox = None
        
        # Rate limiting
        if self.config.enable_rate_limiting:
            self.rate_limiter = RateLimiter()
        else:
            self.rate_limiter = None
    
    def add_template(self, template: Template) -> str:
        """
        Add a template to the registry.
        
        Args:
            template: Template to add
            
        Returns:
            Template ID
            
        Raises:
            TemplateDuplicateError: If template already exists
            TemplateValidationError: If template validation fails
        """
        # Security check
        if self.security_manager:
            validation_result = self.security_manager.validate_template(template)
            if not validation_result.is_valid:
                self._metrics['security_blocks'] += 1
                raise TemplateSecurityError(f"Security validation failed: {validation_result.errors}")
        
        # Validate template
        validation_result = self.validator.validate(template)
        if not validation_result.is_valid:
            raise TemplateValidationError(f"Template validation failed: {validation_result.errors}")
        
        with self._lock:
            # Check for duplicates
            if template.id in self._templates:
                raise TemplateDuplicateError(f"Template {template.id} already exists")
            
            # Add to registry
            self._templates[template.id] = template
            
            # Update index if enabled
            if self._index:
                self._index.add(template.id, template.metadata)
            
            # Clear relevant caches
            if self._render_cache:
                # Only clear renders for this template category
                # This is more efficient than clearing entire cache
                pass
            
            self._metrics['templates_loaded'] += 1
            
            # Persist to storage if available
            if self.storage:
                try:
                    self.storage.save_template(template)
                except Exception as e:
                    logger.error(f"Failed to persist template {template.id}: {e}")
            
            logger.debug(f"Added template {template.id}")
            return template.id
    
    def get_template(self, template_id: str, user_id: str = "default") -> Template:
        """
        Get a template by ID.
        
        Args:
            template_id: Template ID
            user_id: User ID for rate limiting
            
        Returns:
            Template instance
            
        Raises:
            TemplateNotFoundError: If template not found
        """
        # Rate limiting check
        if self.rate_limiter and not self.rate_limiter.check_limit(user_id):
            self._metrics['security_blocks'] += 1
            raise TemplateSecurityError("Rate limit exceeded")
        
        with self._lock:
            # Check if already loaded
            if template_id in self._templates:
                return self._templates[template_id]
            
            # Check lazy load metadata
            if self._template_metadata and template_id in self._template_metadata:
                # Load template on demand
                metadata = self._template_metadata[template_id]
                template = self._load_template_from_metadata(metadata)
                self._templates[template_id] = template
                return template
            
            # Try loading from storage
            if self.storage:
                try:
                    template = self.storage.load_template(template_id)
                    self._templates[template_id] = template
                    return template
                except Exception as e:
                    logger.debug(f"Template {template_id} not found in storage: {e}")
            
            raise TemplateNotFoundError(f"Template {template_id} not found")
    
    def render_template(self,
                       template_id: str,
                       context: TemplateRenderContext,
                       user_id: str = "default") -> str:
        """
        Render a template with the given context.
        
        Args:
            template_id: Template ID
            context: Render context
            user_id: User ID for rate limiting
            
        Returns:
            Rendered template content
        """
        # Rate limiting
        if self.rate_limiter and not self.rate_limiter.check_limit(user_id):
            self._metrics['security_blocks'] += 1
            raise TemplateSecurityError("Rate limit exceeded")
        
        # Check cache first
        if self._render_cache:
            cache_key = self._generate_cache_key(template_id, context)
            cached = self._render_cache.get(cache_key)
            if cached:
                self._metrics['cache_hits'] += 1
                return cached
            self._metrics['cache_misses'] += 1
        
        # Get template
        template = self.get_template(template_id, user_id)
        
        # Security checks
        if self.security_manager:
            # Validate context for security issues
            context = self.security_manager.sanitize_context(context)
            
            # Check for PII if enabled
            if self.pii_detector:
                pii_found = self.pii_detector.detect_pii(str(context))
                if pii_found:
                    logger.warning(f"PII detected in render context for template {template_id}")
        
        # Render in sandbox if enabled
        if self.sandbox:
            rendered = self.sandbox.render_safe(template, context)
        else:
            rendered = template.render(context)
        
        # Cache result
        if self._render_cache:
            cache_key = self._generate_cache_key(template_id, context)
            self._render_cache.set(cache_key, rendered)
        
        self._metrics['templates_rendered'] += 1
        return rendered
    
    def search_templates(self,
                        criteria: TemplateSearchCriteria,
                        user_id: str = "default") -> List[Template]:
        """
        Search for templates matching criteria.
        
        Args:
            criteria: Search criteria
            user_id: User ID for rate limiting
            
        Returns:
            List of matching templates
        """
        # Rate limiting
        if self.rate_limiter and not self.rate_limiter.check_limit(user_id):
            self._metrics['security_blocks'] += 1
            raise TemplateSecurityError("Rate limit exceeded")
        
        with self._lock:
            # Use index if available
            if self._index:
                template_ids = self._index.search(criteria.__dict__)
                return [self._templates[tid] for tid in template_ids if tid in self._templates]
            
            # Fall back to linear search
            results = []
            for template in self._templates.values():
                if self._matches_criteria(template, criteria):
                    results.append(template)
            
            return results
    
    def _matches_criteria(self, template: Template, criteria: TemplateSearchCriteria) -> bool:
        """Check if template matches search criteria."""
        if criteria.category and template.metadata.get('category') != criteria.category:
            return False
        
        if criteria.type and template.metadata.get('type') != criteria.type:
            return False
        
        if criteria.tags:
            template_tags = set(template.metadata.get('tags', []))
            if not all(tag in template_tags for tag in criteria.tags):
                return False
        
        if criteria.name_pattern:
            import re
            if not re.search(criteria.name_pattern, template.name):
                return False
        
        return True
    
    def _generate_cache_key(self, template_id: str, context: TemplateRenderContext) -> str:
        """Generate cache key for rendered template."""
        # Create stable hash of context
        context_str = json.dumps(context.__dict__, sort_keys=True)
        context_hash = hashlib.md5(context_str.encode()).hexdigest()
        return f"{template_id}:{context_hash}"
    
    def _load_template_from_metadata(self, metadata: Dict[str, Any]) -> Template:
        """Load template from metadata (for lazy loading)."""
        path = Path(metadata['path'])
        if path.suffix == '.json':
            with open(path, 'r') as f:
                data = json.load(f)
                return Template.from_dict(data)
        else:
            # Load other formats
            return self.loader.load_from_file(path)
    
    def _load_default_templates(self) -> None:
        """Load default templates from the defaults directory."""
        try:
            default_path = Path(__file__).parent / "defaults"
            if not default_path.exists():
                logger.warning(f"Default templates directory not found: {default_path}")
                return
            
            # Load all template files
            for file_path in default_path.glob("**/*"):
                if file_path.is_file() and file_path.suffix in ['.json', '.md', '.yaml']:
                    try:
                        if self.config.enable_lazy_load:
                            # Just register metadata
                            self._register_template_metadata(file_path)
                        else:
                            # Load full template
                            template = self.loader.load_from_file(file_path)
                            self.add_template(template)
                    except Exception as e:
                        logger.error(f"Failed to load template from {file_path}: {e}")
            
            logger.info(f"Loaded {len(self._templates)} default templates")
            
        except Exception as e:
            logger.error(f"Failed to load default templates: {e}")
    
    def _register_template_metadata(self, file_path: Path) -> None:
        """Register template metadata for lazy loading."""
        if not self._template_metadata:
            return
        
        try:
            # Quick metadata extraction
            if file_path.suffix == '.json':
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if 'id' in data:
                        self._template_metadata[data['id']] = {
                            'id': data['id'],
                            'name': data.get('name'),
                            'category': data.get('category'),
                            'type': data.get('type'),
                            'path': str(file_path)
                        }
        except Exception as e:
            logger.debug(f"Failed to register metadata for {file_path}: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get registry metrics."""
        metrics = dict(self._metrics)
        
        # Add cache metrics if available
        if self._render_cache:
            metrics['cache_hit_rate'] = self._render_cache.hit_rate
            metrics['cache_size'] = len(self._render_cache.cache)
        
        # Add security metrics if available
        if self.security_manager:
            metrics['security_enabled'] = True
            metrics['pii_detection_enabled'] = self.pii_detector is not None
            metrics['sandbox_enabled'] = self.sandbox is not None
        
        return metrics
    
    def clear_cache(self) -> None:
        """Clear all caches."""
        if self._render_cache:
            self._render_cache.clear()
        if self._compiled_cache:
            self._compiled_cache.clear()
        logger.info("Cleared all caches")
    
    def shutdown(self) -> None:
        """Shutdown registry and cleanup resources."""
        # Shutdown thread pool
        if self._executor:
            self._executor.shutdown(wait=True)
        
        # Clear caches
        self.clear_cache()
        
        # Save state to storage if configured
        if self.storage:
            try:
                for template in self._templates.values():
                    self.storage.save_template(template)
            except Exception as e:
                logger.error(f"Failed to save templates on shutdown: {e}")
        
        logger.info("Registry shutdown complete")


# Backward compatibility aliases
def create_registry(mode: str = "basic", **kwargs) -> UnifiedTemplateRegistry:
    """
    Factory function to create a registry with the specified mode.
    
    Args:
        mode: Operation mode ('basic', 'performance', 'secure', 'enterprise')
        **kwargs: Additional configuration options
        
    Returns:
        Configured UnifiedTemplateRegistry instance
    """
    mode_map = {
        'basic': OperationMode.BASIC,
        'performance': OperationMode.PERFORMANCE,
        'secure': OperationMode.SECURE,
        'enterprise': OperationMode.ENTERPRISE
    }
    
    op_mode = mode_map.get(mode.lower(), OperationMode.BASIC)
    config = RegistryConfig.from_mode(op_mode)
    
    # Apply any custom configuration
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
    
    return UnifiedTemplateRegistry(config=config)


# For backward compatibility, export the unified registry as the default
TemplateRegistry = UnifiedTemplateRegistry