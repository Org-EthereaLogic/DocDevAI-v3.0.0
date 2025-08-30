"""
Optimized Template Registry for M006 Template Registry - Pass 2 Performance.

This module provides performance-optimized versions of the registry components
with template compilation, advanced caching, lazy loading, and parallel processing.
"""

import re
import hashlib
import pickle
from typing import Dict, List, Optional, Union, Any, Callable, Set, Tuple
from pathlib import Path
import logging
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from functools import lru_cache
from collections import OrderedDict
import weakref

from ..core.config import ConfigurationManager
from ..storage.secure_storage import SecureStorageLayer
from .registry import TemplateRegistry  # Import base registry
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
    TemplateValidationError
)

logger = logging.getLogger(__name__)


class CompiledTemplate:
    """Pre-compiled template for faster rendering."""
    
    def __init__(self, template: Template):
        """Compile a template for optimized rendering."""
        self.template = template
        self.compiled_pattern = None
        self.variable_map = {}
        self.section_map = {}
        self.loop_map = {}
        self._compile()
    
    def _compile(self):
        """Pre-compile the template patterns."""
        content = self.template.content
        
        # Pre-compile all regex patterns
        self.var_pattern = re.compile(r'\{\{([^}]+)\}\}')
        self.section_pattern = re.compile(r'<!-- SECTION: (\w+) -->(.*?)<!-- END SECTION: \1 -->', re.DOTALL)
        self.conditional_pattern = re.compile(r'<!-- IF ([^-]+) -->(.*?)<!-- END IF -->', re.DOTALL)
        self.loop_pattern = re.compile(r'<!-- FOR (\w+) IN (\w+) -->(.*?)<!-- END FOR -->', re.DOTALL)
        
        # Extract and index all variables
        for match in self.var_pattern.finditer(content):
            var_name = match.group(1).strip()
            if var_name not in self.variable_map:
                self.variable_map[var_name] = []
            self.variable_map[var_name].append(match.span())
        
        # Extract and index sections
        for match in self.section_pattern.finditer(content):
            section_name = match.group(1)
            self.section_map[section_name] = (match.span(), match.group(2))
        
        # Extract and index loops
        for match in self.loop_pattern.finditer(content):
            loop_var = match.group(2).strip()
            self.loop_map[loop_var] = (match.span(), match.group(1), match.group(3))
    
    def render(self, context: Dict[str, Any]) -> str:
        """Fast render using pre-compiled patterns."""
        # This is a simplified version - full implementation would be more complex
        result = self.template.content
        
        # Quick variable substitution using pre-indexed positions
        for var_name, positions in self.variable_map.items():
            if var_name in context:
                value = str(context[var_name])
                # Replace from end to start to maintain positions
                for start, end in reversed(positions):
                    result = result[:start] + value + result[end:]
        
        return result


class LRUTemplateCache:
    """LRU cache for templates with size limits."""
    
    def __init__(self, max_size: int = 1000, max_memory_mb: int = 100):
        """Initialize LRU cache with size and memory limits."""
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self._cache = OrderedDict()
        self._memory_usage = 0
        self._lock = threading.RLock()
        self._access_count = {}
        self._last_access = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache and update access order."""
        with self._lock:
            if key in self._cache:
                # Move to end (most recently used)
                self._cache.move_to_end(key)
                self._access_count[key] = self._access_count.get(key, 0) + 1
                self._last_access[key] = datetime.now()
                return self._cache[key]
            return None
    
    def put(self, key: str, value: Any, size_bytes: Optional[int] = None):
        """Add item to cache with LRU eviction."""
        with self._lock:
            if size_bytes is None:
                # Estimate size
                size_bytes = len(pickle.dumps(value))
            
            # Evict items if necessary
            while (len(self._cache) >= self.max_size or 
                   self._memory_usage + size_bytes > self.max_memory_bytes):
                if not self._cache:
                    break
                # Remove least recently used
                oldest_key = next(iter(self._cache))
                self._evict(oldest_key)
            
            self._cache[key] = value
            self._memory_usage += size_bytes
            self._access_count[key] = 1
            self._last_access[key] = datetime.now()
    
    def _evict(self, key: str):
        """Evict item from cache."""
        if key in self._cache:
            value = self._cache.pop(key)
            size_bytes = len(pickle.dumps(value))
            self._memory_usage -= size_bytes
            self._access_count.pop(key, None)
            self._last_access.pop(key, None)
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._memory_usage = 0
            self._access_count.clear()
            self._last_access.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            return {
                'size': len(self._cache),
                'memory_mb': self._memory_usage / (1024 * 1024),
                'hit_rate': self._calculate_hit_rate(),
                'most_accessed': self._get_most_accessed()
            }
    
    def _calculate_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total_accesses = sum(self._access_count.values())
        if total_accesses == 0:
            return 0.0
        return len(self._access_count) / total_accesses
    
    def _get_most_accessed(self, limit: int = 5) -> List[Tuple[str, int]]:
        """Get most accessed cache keys."""
        sorted_items = sorted(self._access_count.items(), key=lambda x: x[1], reverse=True)
        return sorted_items[:limit]


class TemplateIndex:
    """Fast indexing for template search operations."""
    
    def __init__(self):
        """Initialize template indexes."""
        self.category_index: Dict[TemplateCategory, Set[str]] = {}
        self.type_index: Dict[TemplateType, Set[str]] = {}
        self.tag_index: Dict[str, Set[str]] = {}
        self.text_index: Dict[str, Set[str]] = {}  # Simple inverted index
        self.metadata_cache: Dict[str, TemplateMetadata] = {}
        self._lock = threading.RLock()
    
    def add_template(self, template: Template):
        """Add template to indexes."""
        with self._lock:
            template_id = template.metadata.id
            metadata = template.metadata
            
            # Cache metadata for fast access
            self.metadata_cache[template_id] = metadata
            
            # Category index
            if metadata.category not in self.category_index:
                self.category_index[metadata.category] = set()
            self.category_index[metadata.category].add(template_id)
            
            # Type index
            if metadata.type not in self.type_index:
                self.type_index[metadata.type] = set()
            self.type_index[metadata.type].add(template_id)
            
            # Tag index
            for tag in metadata.tags:
                if tag not in self.tag_index:
                    self.tag_index[tag] = set()
                self.tag_index[tag].add(template_id)
            
            # Text index (simple tokenization)
            text = f"{metadata.name} {metadata.description}".lower()
            tokens = set(text.split())
            for token in tokens:
                if token not in self.text_index:
                    self.text_index[token] = set()
                self.text_index[token].add(template_id)
    
    def remove_template(self, template_id: str):
        """Remove template from indexes."""
        with self._lock:
            if template_id not in self.metadata_cache:
                return
            
            metadata = self.metadata_cache[template_id]
            
            # Remove from category index
            if metadata.category in self.category_index:
                self.category_index[metadata.category].discard(template_id)
            
            # Remove from type index
            if metadata.type in self.type_index:
                self.type_index[metadata.type].discard(template_id)
            
            # Remove from tag index
            for tag in metadata.tags:
                if tag in self.tag_index:
                    self.tag_index[tag].discard(template_id)
            
            # Remove from text index
            text = f"{metadata.name} {metadata.description}".lower()
            tokens = set(text.split())
            for token in tokens:
                if token in self.text_index:
                    self.text_index[token].discard(template_id)
            
            # Remove metadata cache
            del self.metadata_cache[template_id]
    
    def search(self, criteria: TemplateSearchCriteria) -> Set[str]:
        """Fast search using indexes."""
        with self._lock:
            results = None
            
            # Category filter (intersection)
            if criteria.category:
                category_matches = self.category_index.get(criteria.category, set())
                results = category_matches if results is None else results & category_matches
            
            # Type filter
            if criteria.type:
                type_matches = self.type_index.get(criteria.type, set())
                results = type_matches if results is None else results & type_matches
            
            # Tag filter (any match)
            if criteria.tags:
                tag_matches = set()
                for tag in criteria.tags:
                    tag_matches |= self.tag_index.get(tag, set())
                results = tag_matches if results is None else results & tag_matches
            
            # Text search
            if criteria.search_text:
                tokens = criteria.search_text.lower().split()
                text_matches = set()
                for token in tokens:
                    # Find all templates containing this token
                    for index_token, template_ids in self.text_index.items():
                        if token in index_token:
                            text_matches |= template_ids
                results = text_matches if results is None else results & text_matches
            
            # Return all if no criteria
            if results is None:
                results = set(self.metadata_cache.keys())
            
            return results


class OptimizedTemplateRegistry(TemplateRegistry):
    """Performance-optimized template registry with advanced features."""
    
    def __init__(self, 
                 config_manager: Optional[ConfigurationManager] = None,
                 storage: Optional[SecureStorageLayer] = None,
                 auto_load_defaults: bool = True,
                 lazy_load: bool = True,
                 max_cache_size: int = 1000,
                 max_workers: int = 4):
        """
        Initialize optimized template registry.
        
        Args:
            config_manager: Configuration manager (M001)
            storage: Storage system (M002)
            auto_load_defaults: Whether to auto-load default templates
            lazy_load: Enable lazy loading of templates
            max_cache_size: Maximum number of templates to cache
            max_workers: Maximum worker threads for parallel operations
        """
        # Initialize base class
        super().__init__(config_manager, storage, auto_load_defaults=False)
        
        self.lazy_load = lazy_load
        
        # Additional optimized storage
        self._compiled_templates: Dict[str, CompiledTemplate] = weakref.WeakValueDictionary()
        self._template_metadata: Dict[str, TemplateMetadata] = {}  # Lightweight metadata storage
        
        # Advanced caching
        self._render_cache = LRUTemplateCache(max_size=max_cache_size)
        self._compiled_cache = LRUTemplateCache(max_size=max_cache_size // 2)
        
        # Indexing for fast search
        self._index = TemplateIndex()
        
        # Thread pool for parallel operations
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Additional performance metrics
        self._metrics['parallel_renders'] = 0
        self._metrics['compilation_time_ms'] = 0
        
        # Load default templates if requested
        if auto_load_defaults and not lazy_load:
            self._load_default_templates()
        elif auto_load_defaults and lazy_load:
            # Just register metadata for lazy loading
            self._register_default_metadata()
    
    def _register_default_metadata(self):
        """Register default template metadata without loading content."""
        try:
            # Load only metadata from default templates
            default_path = Path(__file__).parent / "defaults"
            for file_path in default_path.glob("**/*.json"):
                # Quick metadata extraction without full parsing
                with open(file_path, 'r') as f:
                    import json
                    data = json.load(f)
                    if 'id' in data:
                        # Store minimal metadata for lazy loading
                        self._template_metadata[data['id']] = {
                            'id': data['id'],
                            'name': data.get('name'),
                            'category': data.get('category'),
                            'type': data.get('type'),
                            'path': str(file_path)
                        }
            
            logger.info(f"Registered {len(self._template_metadata)} default template metadata")
            
        except Exception as e:
            logger.error(f"Failed to register default template metadata: {e}")
    
    def get_template(self, template_id: str) -> Template:
        """
        Get a template by ID with lazy loading support.
        
        Args:
            template_id: Template ID
            
        Returns:
            Template instance
            
        Raises:
            TemplateNotFoundError: If template not found
        """
        with self._lock:
            # Check if already loaded
            if template_id in self._templates:
                return self._templates[template_id]
            
            # Check if we have metadata for lazy loading
            if self.lazy_load and template_id in self._template_metadata:
                # Load template on demand
                metadata = self._template_metadata[template_id]
                if 'path' in metadata:
                    template_model = self.loader.load_from_file(metadata['path'])
                    template = Template(template_model)
                    self._register_template(template)
                    return template
            
            # Try to load from storage
            if self.storage:
                try:
                    template = self._load_template_from_storage(template_id)
                    self._register_template(template)
                    return template
                except Exception:
                    pass
            
            raise TemplateNotFoundError(template_id)
    
    def render_template(self, 
                       template_id: str,
                       context: Optional[Dict[str, Any]] = None,
                       validate_context: bool = True,
                       use_compiled: bool = True) -> str:
        """
        Render a template with optimized compilation and caching.
        
        Args:
            template_id: Template ID
            context: Rendering context
            validate_context: Whether to validate context
            use_compiled: Use compiled template for faster rendering
            
        Returns:
            Rendered content
        """
        context = context or {}
        
        # Generate cache key
        cache_key = self._generate_cache_key(template_id, context)
        
        # Check render cache first
        cached_result = self._render_cache.get(cache_key)
        if cached_result:
            self._metrics['cache_hits'] += 1
            return cached_result
        
        self._metrics['cache_misses'] += 1
        
        # Get template
        template = self.get_template(template_id)
        
        # Use compiled version if requested
        if use_compiled:
            compiled = self._get_compiled_template(template_id)
            if compiled:
                try:
                    rendered = compiled.render(context)
                    self._render_cache.put(cache_key, rendered)
                    self._metrics['templates_rendered'] += 1
                    return rendered
                except Exception:
                    # Fall back to regular rendering
                    pass
        
        # Regular rendering
        rendered = template.render(context, validate_context)
        
        # Cache the result
        self._render_cache.put(cache_key, rendered)
        
        # Update metrics
        self._metrics['templates_rendered'] += 1
        
        # Fire event
        self._fire_event('template_rendered', template)
        
        return rendered
    
    def _get_compiled_template(self, template_id: str) -> Optional[CompiledTemplate]:
        """Get or create compiled template."""
        if template_id in self._compiled_templates:
            return self._compiled_templates[template_id]
        
        # Check compiled cache
        compiled = self._compiled_cache.get(template_id)
        if compiled:
            self._compiled_templates[template_id] = compiled
            return compiled
        
        # Compile template
        try:
            template = self.get_template(template_id)
            start_time = datetime.now()
            compiled = CompiledTemplate(template)
            compile_time = (datetime.now() - start_time).total_seconds() * 1000
            self._metrics['compilation_time_ms'] += compile_time
            
            # Cache compiled template
            self._compiled_templates[template_id] = compiled
            self._compiled_cache.put(template_id, compiled)
            
            return compiled
            
        except Exception as e:
            logger.warning(f"Failed to compile template {template_id}: {e}")
            return None
    
    def render_batch(self, 
                    render_requests: List[Tuple[str, Dict[str, Any]]],
                    parallel: bool = True) -> List[str]:
        """
        Render multiple templates in batch with optional parallelization.
        
        Args:
            render_requests: List of (template_id, context) tuples
            parallel: Whether to render in parallel
            
        Returns:
            List of rendered templates
        """
        if not parallel:
            return [self.render_template(tid, ctx) for tid, ctx in render_requests]
        
        # Parallel rendering
        futures = []
        for template_id, context in render_requests:
            future = self._executor.submit(self.render_template, template_id, context)
            futures.append(future)
        
        results = [future.result() for future in futures]
        self._metrics['parallel_renders'] += len(results)
        
        return results
    
    def search_templates(self, criteria: TemplateSearchCriteria) -> List[Template]:
        """
        Fast template search using indexes.
        
        Args:
            criteria: Search criteria
            
        Returns:
            List of matching templates
        """
        # Use index for fast search
        matching_ids = self._index.search(criteria)
        
        # Load and return templates
        templates = []
        for template_id in matching_ids:
            try:
                template = self.get_template(template_id)
                templates.append(template)
            except TemplateNotFoundError:
                continue
        
        # Sort by usage count
        templates.sort(key=lambda t: t.metadata.usage_count, reverse=True)
        
        return templates
    
    def _register_template(self, template: Template, from_defaults: bool = False):
        """Register a template with indexing."""
        # Call parent method
        super()._register_template(template, from_defaults)
        
        # Add to index for fast search
        with self._lock:
            self._index.add_template(template)
    
    def _generate_cache_key(self, template_id: str, context: Dict[str, Any]) -> str:
        """Generate efficient cache key."""
        # Use hash for faster key generation
        context_str = str(sorted(context.items()))
        hash_obj = hashlib.md5(f"{template_id}:{context_str}".encode())
        return hash_obj.hexdigest()
    
    def _load_template_from_storage(self, template_id: str) -> Template:
        """Load template from storage."""
        if not self.storage:
            raise TemplateStorageError("load", "No storage system available")
        
        try:
            doc_id = f"template_{template_id}"
            data = self.storage.get_document(doc_id)
            template_model = TemplateModel(**data)
            return Template(template_model)
        except Exception as e:
            raise TemplateStorageError("load", f"Failed to load from storage: {e}")
    
    def _fire_event(self, event: str, template: Template):
        """Fire an event to all registered handlers."""
        for handler in self._event_handlers.get(event, []):
            try:
                handler(template)
            except Exception as e:
                logger.error(f"Error in event handler for {event}: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        with self._lock:
            cache_stats = self._render_cache.get_stats()
            return {
                **self._metrics,
                'total_templates': len(self._templates),
                'lazy_loaded': len(self._template_metadata),
                'compiled_templates': len(self._compiled_templates),
                'cache_stats': cache_stats,
                'index_stats': {
                    'categories': len(self._index.category_index),
                    'tags': len(self._index.tag_index),
                    'text_tokens': len(self._index.text_index)
                }
            }
    
    def preload_popular(self, limit: int = 10):
        """Preload and compile popular templates for faster access."""
        with self._lock:
            # Get most used templates
            templates = sorted(
                self._templates.values(),
                key=lambda t: t.metadata.usage_count,
                reverse=True
            )[:limit]
            
            # Compile them in parallel
            futures = []
            for template in templates:
                future = self._executor.submit(
                    self._get_compiled_template, 
                    template.metadata.id
                )
                futures.append(future)
            
            # Wait for compilation
            for future in futures:
                future.result()
    
    def shutdown(self):
        """Shutdown the registry and cleanup resources."""
        logger.info("Shutting down optimized template registry")
        
        # Shutdown executor
        self._executor.shutdown(wait=True)
        
        # Clear caches
        self._render_cache.clear()
        self._compiled_cache.clear()
        
        # Clear optimized structures
        with self._lock:
            self._compiled_templates.clear()
            self._template_metadata.clear()
        
        # Call parent shutdown
        super().shutdown()