"""
Template Registry Adapter for M004-M006 Integration.

This adapter bridges M004's UnifiedTemplateLoader interface with M006's
UnifiedTemplateRegistry, enabling M004 to leverage M006's production templates,
security features, and performance optimizations while maintaining backward compatibility.

Created as part of the critical refactoring to eliminate duplicate template systems
and properly integrate M004 (Document Generator) with M006 (Template Registry).
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

# Import M006's UnifiedTemplateRegistry and related components
from ...templates.registry_unified import (
    UnifiedTemplateRegistry,
    RegistryConfig,
    OperationMode
)
from ...templates.models import (
    Template as M006Template,
    TemplateRenderContext,
    TemplateSearchCriteria,
    TemplateCategory,
    TemplateType
)

# Import M004's existing types for compatibility
from .unified_template_loader import (
    TemplateMetadata,
    SecurityLevel,
    TemplateSecurityError
)

# Import common utilities
from ...common.logging import get_logger
from ...common.errors import DevDocAIError
from ...common.performance import LRUCache

logger = get_logger(__name__)


class TemplateRegistryAdapter:
    """
    Adapter that provides M004's UnifiedTemplateLoader interface while
    delegating to M006's UnifiedTemplateRegistry for actual functionality.
    
    This adapter ensures backward compatibility for all existing M004 code
    while leveraging M006's superior template system with 35+ production templates.
    """
    
    # Mapping from M004's SecurityLevel to M006's OperationMode
    SECURITY_TO_MODE_MAP = {
        SecurityLevel.NONE: OperationMode.BASIC,
        SecurityLevel.BASIC: OperationMode.BASIC,
        SecurityLevel.STANDARD: OperationMode.PERFORMANCE,
        SecurityLevel.STRICT: OperationMode.ENTERPRISE
    }
    
    def __init__(self,
                 template_dir: Optional[Path] = None,
                 security_level: SecurityLevel = SecurityLevel.STANDARD,
                 cache_enabled: bool = None,
                 cache_size: int = 100,
                 enable_audit: bool = False,
                 enable_caching: bool = None,  # Backward compatibility alias
                 **kwargs):
        """
        Initialize the adapter with M004-compatible parameters.
        
        Args:
            template_dir: Template directory (kept for compatibility, M006 handles this)
            security_level: Security level from M004
            cache_enabled: Whether to enable caching
            cache_size: Size of cache
            enable_audit: Whether to enable audit logging
        """
        # Handle backward compatibility for cache parameter names
        if cache_enabled is None and enable_caching is not None:
            cache_enabled = enable_caching
        elif cache_enabled is None:
            cache_enabled = True  # Default value
        
        self.template_dir = template_dir
        self.security_level = security_level
        self.cache_enabled = cache_enabled
        self.cache_size = cache_size
        self.enable_audit = enable_audit
        
        # Map M004's security level to M006's operation mode
        operation_mode = self.SECURITY_TO_MODE_MAP[security_level]
        
        # Create M006 registry configuration
        registry_config = RegistryConfig.from_mode(operation_mode)
        registry_config.enable_cache = cache_enabled
        registry_config.cache_size = cache_size
        registry_config.enable_audit_logging = enable_audit
        
        # Initialize M006's UnifiedTemplateRegistry
        self.registry = UnifiedTemplateRegistry(
            config=registry_config,
            mode=operation_mode
        )
        
        # Cache for template metadata conversion
        self._metadata_cache = LRUCache(max_size=cache_size) if cache_enabled else None
        
        # Default user ID for M004 operations (M004 doesn't have user concept)
        self.default_user_id = "m004_generator"
        
        logger.info(
            f"TemplateRegistryAdapter initialized: "
            f"security={security_level.value}, mode={operation_mode.name}, "
            f"cache={cache_enabled}, audit={enable_audit}"
        )
    
    def load_template(self,
                     template_name: str,
                     template_type: Optional[str] = None,
                     variables: Optional[Dict[str, Any]] = None) -> Tuple[Any, TemplateMetadata]:
        """
        Load a template by name (M004 interface).
        
        Args:
            template_name: Name of the template to load
            template_type: Optional template type filter
            variables: Optional variables for validation
            
        Returns:
            Tuple of (template object, metadata)
        """
        try:
            # Use template name as ID for M006 (can be enhanced with proper mapping later)
            template_id = self._name_to_id(template_name, template_type)
            
            # Get template from M006 registry
            m006_template = self.registry.get_template(template_id, self.default_user_id)
            
            # Convert M006 template metadata to M004 format
            m004_metadata = self._convert_metadata(m006_template)
            
            # Return template object and metadata (M004 expects this tuple)
            return m006_template, m004_metadata
            
        except Exception as e:
            logger.error(f"Failed to load template '{template_name}': {e}")
            raise DevDocAIError(f"Template loading failed: {e}")
    
    def render_template(self,
                       template: Any,
                       context: Dict[str, Any],
                       strict: bool = False) -> str:
        """
        Render a template with context (M004 interface).
        
        Args:
            template: Template object (from load_template)
            context: Context dictionary for rendering
            strict: Whether to use strict mode
            
        Returns:
            Rendered template string
        """
        try:
            # Convert to M006 template if needed
            if isinstance(template, M006Template):
                # Create TemplateRenderContext from dict
                render_context = self._create_render_context(context)
                
                # Use template ID from the template object
                template_id = template.id if hasattr(template, 'id') else str(template)
                
                # Render using M006 registry
                return self.registry.render_template(
                    template_id=template_id,
                    context=render_context,
                    user_id=self.default_user_id
                )
            else:
                # Handle legacy template object (backward compatibility)
                # Try to render directly if it has a render method
                if hasattr(template, 'render'):
                    return template.render(context)
                else:
                    raise DevDocAIError(f"Invalid template object type: {type(template)}")
                    
        except Exception as e:
            logger.error(f"Failed to render template: {e}")
            raise DevDocAIError(f"Template rendering failed: {e}")
    
    def render(self, template_name: str, **context) -> str:
        """
        Convenience method to load and render in one call (M004 interface).
        
        Args:
            template_name: Name of template to render
            **context: Context variables for rendering
            
        Returns:
            Rendered template string
        """
        template, _ = self.load_template(template_name)
        return self.render_template(template, context)
    
    def get_metadata(self, template_name: str) -> TemplateMetadata:
        """
        Get template metadata (M004 interface).
        
        Args:
            template_name: Name of the template
            
        Returns:
            Template metadata in M004 format
        """
        # Check cache first
        if self._metadata_cache:
            cached = self._metadata_cache.get(template_name)
            if cached:
                return cached
        
        # Load template to get metadata
        _, metadata = self.load_template(template_name)
        
        # Cache the metadata
        if self._metadata_cache:
            self._metadata_cache.set(template_name, metadata)
        
        return metadata
    
    def get_template_info(self, template_name: str) -> Dict[str, Any]:
        """
        Get template information as dictionary (M004 interface).
        
        Args:
            template_name: Name of the template
            
        Returns:
            Template information dictionary
        """
        metadata = self.get_metadata(template_name)
        return metadata.to_dict()
    
    def list_templates(self, filter_type: Optional[str] = None) -> List[str]:
        """
        List available templates (M004 interface).
        
        Args:
            filter_type: Optional type filter
            
        Returns:
            List of template names
        """
        try:
            # Create search criteria for M006
            criteria = TemplateSearchCriteria()
            if filter_type:
                criteria.type = filter_type
            
            # Search templates in M006 registry
            templates = self.registry.search_templates(criteria, self.default_user_id)
            
            # Extract template names
            template_names = []
            for template in templates:
                name = template.metadata.get('name', template.id)
                template_names.append(name)
            
            return sorted(template_names)
            
        except Exception as e:
            logger.error(f"Failed to list templates: {e}")
            return []
    
    def clear_cache(self) -> None:
        """Clear all caches (M004 interface)."""
        if self._metadata_cache:
            self._metadata_cache.clear()
        
        # M006 registry manages its own caches internally
        # We can request metrics reset if needed
        if hasattr(self.registry, '_metrics'):
            self.registry._metrics['cache_hits'] = 0
            self.registry._metrics['cache_misses'] = 0
        
        logger.debug("Template caches cleared")
    
    def validate_template(self, template_name: str) -> bool:
        """
        Validate a template (M004 interface).
        
        Args:
            template_name: Name of template to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Try to load the template
            template, metadata = self.load_template(template_name)
            
            # If loading succeeds, template is valid
            return True
            
        except Exception as e:
            logger.warning(f"Template validation failed for '{template_name}': {e}")
            return False
    
    # Private helper methods
    
    def _name_to_id(self, template_name: str, template_type: Optional[str] = None) -> str:
        """
        Convert M004 template name to M006 template ID.
        
        For now, we use the name as ID. This can be enhanced with a proper
        mapping table if M006 templates have different ID conventions.
        
        Args:
            template_name: Template name from M004
            template_type: Optional type hint
            
        Returns:
            Template ID for M006
        """
        # Simple conversion: use name as ID
        # Can be enhanced with mapping logic if needed
        if template_type:
            return f"{template_type}/{template_name}"
        return template_name
    
    def _convert_metadata(self, m006_template: M006Template) -> TemplateMetadata:
        """
        Convert M006 template to M004 TemplateMetadata.
        
        Args:
            m006_template: Template from M006 registry
            
        Returns:
            TemplateMetadata in M004 format
        """
        # Extract metadata from M006 template
        m006_meta = m006_template.metadata if hasattr(m006_template, 'metadata') else {}
        
        # Map to M004 TemplateMetadata
        return TemplateMetadata(
            name=m006_meta.get('name', m006_template.id if hasattr(m006_template, 'id') else 'unknown'),
            title=m006_meta.get('title', m006_meta.get('name', 'Untitled')),
            type=m006_meta.get('type', 'general'),
            category=m006_meta.get('category', 'default'),
            description=m006_meta.get('description'),
            version=m006_meta.get('version', '1.0'),
            author=m006_meta.get('author'),
            created_date=m006_meta.get('created_date'),
            variables=m006_meta.get('variables', []),
            optional_variables=m006_meta.get('optional_variables', []),
            sections=m006_meta.get('sections', []),
            tags=m006_meta.get('tags', []),
            metadata=m006_meta.get('metadata', {}),
            content=m006_template.content if hasattr(m006_template, 'content') else None,
            file_path=Path(m006_meta.get('file_path')) if m006_meta.get('file_path') else None,
            checksum=m006_meta.get('checksum'),
            trust_level=m006_meta.get('trust_level')
        )
    
    def _create_render_context(self, context_dict: Dict[str, Any]) -> TemplateRenderContext:
        """
        Create M006 TemplateRenderContext from M004 context dictionary.
        
        Args:
            context_dict: Context dictionary from M004
            
        Returns:
            TemplateRenderContext for M006
        """
        # Extract sections and loops if present in the context
        sections = {}
        loops = {}
        variables = {}
        
        for key, value in context_dict.items():
            if key.startswith('section_'):
                # Handle section flags
                sections[key.replace('section_', '')] = bool(value)
            elif key.startswith('loop_'):
                # Handle loop data
                loops[key.replace('loop_', '')] = value if isinstance(value, list) else [value]
            else:
                # Everything else is a variable
                variables[key] = value
        
        # Create TemplateRenderContext with proper structure
        render_context = TemplateRenderContext(
            variables=variables,
            sections=sections,
            loops=loops
        )
        
        return render_context
    
    # Compatibility methods for smooth transition
    
    def __getattr__(self, name):
        """
        Delegate unknown attributes to the M006 registry for forward compatibility.
        
        This allows gradual migration where new code can use M006 features
        directly through the adapter.
        """
        if hasattr(self.registry, name):
            return getattr(self.registry, name)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")


# Alias for drop-in replacement
UnifiedTemplateLoader = TemplateRegistryAdapter


__all__ = [
    'TemplateRegistryAdapter',
    'UnifiedTemplateLoader',  # Alias for backward compatibility
    'TemplateMetadata',
    'SecurityLevel',
    'TemplateSecurityError'
]