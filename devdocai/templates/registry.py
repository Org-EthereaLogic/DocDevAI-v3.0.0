"""
Template Registry for M006 Template Registry.

This module provides the main registry class for managing templates,
integrating with storage, validation, and other system components.
"""

from typing import Dict, List, Optional, Union, Any, Callable
from pathlib import Path
import logging
from datetime import datetime
import threading

from ..core.config import ConfigurationManager  # M001 integration
from ..storage.secure_storage import SecureStorageLayer  # M002 integration
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


class TemplateRegistry:
    """
    Main template registry for managing templates across the system.
    
    This class provides a centralized interface for template management,
    including CRUD operations, search, validation, and integration
    with other system modules.
    """
    
    def __init__(self, 
                 config_manager: Optional[ConfigurationManager] = None,
                 storage: Optional[SecureStorageLayer] = None,
                 auto_load_defaults: bool = True):
        """
        Initialize template registry.
        
        Args:
            config_manager: Configuration manager (M001)
            storage: Storage system (M002)
            auto_load_defaults: Whether to auto-load default templates
        """
        self.config_manager = config_manager
        self.storage = storage
        
        # Core components
        self.loader = TemplateLoader()
        self.validator = TemplateValidator()
        self.category_manager = CategoryManager()
        
        # Template storage
        self._templates: Dict[str, Template] = {}
        self._lock = threading.RLock()
        
        # Event handlers
        self._event_handlers: Dict[str, List[Callable]] = {
            'template_created': [],
            'template_updated': [],
            'template_deleted': [],
            'template_rendered': []
        }
        
        # Performance metrics
        self._metrics = {
            'templates_loaded': 0,
            'templates_rendered': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # Load default templates if requested
        if auto_load_defaults:
            self._load_default_templates()
    
    def _load_default_templates(self) -> None:
        """Load default templates from the defaults directory."""
        try:
            default_templates = self.loader.load_defaults()
            for template_model in default_templates:
                template = Template(template_model)
                self._register_template(template, from_defaults=True)
            
            logger.info(f"Loaded {len(default_templates)} default templates")
            self._metrics['templates_loaded'] += len(default_templates)
            
        except Exception as e:
            logger.error(f"Failed to load default templates: {e}")
    
    def create_template(self, 
                       metadata: TemplateMetadata,
                       content: str,
                       variables: Optional[List] = None,
                       sections: Optional[List] = None,
                       validate: bool = True) -> Template:
        """
        Create a new template.
        
        Args:
            metadata: Template metadata
            content: Template content
            variables: Template variables
            sections: Template sections
            validate: Whether to validate the template
            
        Returns:
            Created template
            
        Raises:
            TemplateDuplicateError: If template with same ID exists
            TemplateValidationError: If validation fails
        """
        with self._lock:
            # Check for duplicates
            if metadata.id in self._templates:
                raise TemplateDuplicateError(metadata.id)
            
            # Create template model
            template_model = TemplateModel(
                metadata=metadata,
                content=content,
                variables=variables or [],
                sections=sections or []
            )
            
            # Create template wrapper
            template = Template(template_model)
            
            # Validate if requested
            if validate:
                validation_result = template.validate()
                if not validation_result.is_valid:
                    raise TemplateValidationError(validation_result.errors, validation_result.warnings)
            
            # Register template
            self._register_template(template)
            
            # Persist to storage if available
            if self.storage:
                self._persist_template(template)
            
            # Fire event
            self._fire_event('template_created', template)
            
            logger.info(f"Created template: {metadata.id}")
            return template
    
    def _register_template(self, template: Template, from_defaults: bool = False) -> None:
        """Register a template in the registry."""
        self._templates[template.metadata.id] = template
        self.category_manager.add_template(template.model)
        
        if from_defaults:
            # Mark as non-custom for default templates
            template.model.metadata.is_custom = False
    
    def get_template(self, template_id: str) -> Template:
        """
        Get a template by ID.
        
        Args:
            template_id: Template ID
            
        Returns:
            Template instance
            
        Raises:
            TemplateNotFoundError: If template not found
        """
        with self._lock:
            if template_id not in self._templates:
                # Try to load from storage
                if self.storage:
                    try:
                        template = self._load_template_from_storage(template_id)
                        self._register_template(template)
                        return template
                    except Exception:
                        pass  # Fall through to not found error
                
                raise TemplateNotFoundError(template_id)
            
            return self._templates[template_id]
    
    def update_template(self, 
                       template_id: str,
                       updates: Dict[str, Any],
                       validate: bool = True) -> Template:
        """
        Update an existing template.
        
        Args:
            template_id: Template ID
            updates: Dictionary of updates
            validate: Whether to validate after update
            
        Returns:
            Updated template
            
        Raises:
            TemplateNotFoundError: If template not found
            TemplateValidationError: If validation fails
        """
        with self._lock:
            template = self.get_template(template_id)
            
            # Apply updates
            for key, value in updates.items():
                if key == 'content':
                    template.update_content(value)
                elif key == 'metadata':
                    for meta_key, meta_value in value.items():
                        if hasattr(template.metadata, meta_key):
                            setattr(template.metadata, meta_key, meta_value)
                elif hasattr(template.model, key):
                    setattr(template.model, key, value)
            
            template.model.metadata.updated_at = datetime.now()
            
            # Validate if requested
            if validate:
                validation_result = template.validate()
                if not validation_result.is_valid:
                    raise TemplateValidationError(validation_result.errors, validation_result.warnings)
            
            # Persist to storage
            if self.storage:
                self._persist_template(template)
            
            # Fire event
            self._fire_event('template_updated', template)
            
            logger.info(f"Updated template: {template_id}")
            return template
    
    def delete_template(self, template_id: str) -> bool:
        """
        Delete a template.
        
        Args:
            template_id: Template ID
            
        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            if template_id not in self._templates:
                return False
            
            template = self._templates[template_id]
            
            # Remove from registry
            del self._templates[template_id]
            self.category_manager.remove_template(template_id)
            
            # Remove from storage
            if self.storage:
                self._remove_template_from_storage(template_id)
            
            # Fire event
            self._fire_event('template_deleted', template)
            
            logger.info(f"Deleted template: {template_id}")
            return True
    
    def list_templates(self, 
                      category: Optional[TemplateCategory] = None,
                      template_type: Optional[TemplateType] = None,
                      active_only: bool = True) -> List[Template]:
        """
        List templates with optional filtering.
        
        Args:
            category: Filter by category
            template_type: Filter by type
            active_only: Only return active templates
            
        Returns:
            List of templates
        """
        with self._lock:
            templates = list(self._templates.values())
            
            # Apply filters
            if category:
                templates = [t for t in templates if t.metadata.category == category]
            
            if template_type:
                templates = [t for t in templates if t.metadata.type == template_type]
            
            if active_only:
                templates = [t for t in templates if t.metadata.is_active]
            
            # Sort by usage count (most used first)
            templates.sort(key=lambda t: t.metadata.usage_count, reverse=True)
            
            return templates
    
    def search_templates(self, criteria: TemplateSearchCriteria) -> List[Template]:
        """
        Search templates based on criteria.
        
        Args:
            criteria: Search criteria
            
        Returns:
            List of matching templates
        """
        with self._lock:
            results = []
            
            for template in self._templates.values():
                if self._matches_criteria(template, criteria):
                    results.append(template)
            
            # Sort by relevance (usage count for now)
            results.sort(key=lambda t: t.metadata.usage_count, reverse=True)
            
            return results
    
    def _matches_criteria(self, template: Template, criteria: TemplateSearchCriteria) -> bool:
        """Check if template matches search criteria."""
        # Category filter
        if criteria.category and template.metadata.category != criteria.category:
            return False
        
        # Type filter
        if criteria.type and template.metadata.type != criteria.type:
            return False
        
        # Tags filter
        if criteria.tags:
            template_tags = set(template.metadata.tags)
            criteria_tags = set(criteria.tags)
            if not criteria_tags.intersection(template_tags):
                return False
        
        # Author filter
        if criteria.author and template.metadata.author != criteria.author:
            return False
        
        # Custom filter
        if criteria.is_custom is not None and template.metadata.is_custom != criteria.is_custom:
            return False
        
        # Active filter
        if criteria.is_active is not None and template.metadata.is_active != criteria.is_active:
            return False
        
        # Text search
        if criteria.search_text:
            text = criteria.search_text.lower()
            if (text not in template.metadata.name.lower() and
                text not in template.metadata.description.lower() and
                not any(text in tag.lower() for tag in template.metadata.tags)):
                return False
        
        return True
    
    def render_template(self, 
                       template_id: str,
                       context: Optional[Dict[str, Any]] = None,
                       validate_context: bool = True) -> str:
        """
        Render a template with the given context.
        
        Args:
            template_id: Template ID
            context: Rendering context
            validate_context: Whether to validate context
            
        Returns:
            Rendered content
            
        Raises:
            TemplateNotFoundError: If template not found
        """
        template = self.get_template(template_id)
        
        try:
            rendered = template.render(context, validate_context)
            
            # Update metrics
            self._metrics['templates_rendered'] += 1
            
            # Fire event
            self._fire_event('template_rendered', template)
            
            return rendered
            
        except Exception as e:
            logger.error(f"Failed to render template {template_id}: {e}")
            raise
    
    def validate_template(self, template_id: str) -> TemplateValidationResult:
        """
        Validate a template.
        
        Args:
            template_id: Template ID
            
        Returns:
            Validation result
        """
        template = self.get_template(template_id)
        return template.validate()
    
    def clone_template(self, 
                      template_id: str,
                      new_id: Optional[str] = None,
                      new_name: Optional[str] = None) -> Template:
        """
        Clone an existing template.
        
        Args:
            template_id: Source template ID
            new_id: New template ID
            new_name: New template name
            
        Returns:
            Cloned template
        """
        source_template = self.get_template(template_id)
        cloned_template = source_template.clone(new_id, new_name)
        
        # Register the clone
        self._register_template(cloned_template)
        
        # Persist to storage
        if self.storage:
            self._persist_template(cloned_template)
        
        return cloned_template
    
    def get_categories(self) -> List[TemplateCategory]:
        """Get all available categories."""
        return self.category_manager.get_all_categories()
    
    def get_category_statistics(self) -> Dict[TemplateCategory, Dict]:
        """Get statistics for all categories."""
        return self.category_manager.get_category_statistics()
    
    def get_popular_templates(self, limit: int = 10) -> List[Template]:
        """Get most popular templates."""
        with self._lock:
            templates = list(self._templates.values())
            templates.sort(key=lambda t: t.metadata.usage_count, reverse=True)
            return templates[:limit]
    
    def import_template(self, file_path: Union[str, Path]) -> Template:
        """
        Import a template from file.
        
        Args:
            file_path: Path to template file
            
        Returns:
            Imported template
        """
        template_model = self.loader.load_from_file(file_path)
        template = Template(template_model)
        
        # Check for duplicates
        if template.metadata.id in self._templates:
            # Generate unique ID
            base_id = template.metadata.id
            counter = 1
            while f"{base_id}_{counter}" in self._templates:
                counter += 1
            template.model.metadata.id = f"{base_id}_{counter}"
        
        # Mark as custom
        template.model.metadata.is_custom = True
        
        # Register template
        self._register_template(template)
        
        # Persist to storage
        if self.storage:
            self._persist_template(template)
        
        return template
    
    def export_template(self, 
                       template_id: str,
                       file_path: Union[str, Path],
                       format: Optional[str] = None) -> None:
        """
        Export a template to file.
        
        Args:
            template_id: Template ID
            file_path: Export file path
            format: Export format
        """
        template = self.get_template(template_id)
        self.loader.save_to_file(template.model, file_path, format)
    
    def add_event_handler(self, event: str, handler: Callable) -> None:
        """Add an event handler."""
        if event in self._event_handlers:
            self._event_handlers[event].append(handler)
    
    def remove_event_handler(self, event: str, handler: Callable) -> None:
        """Remove an event handler."""
        if event in self._event_handlers and handler in self._event_handlers[event]:
            self._event_handlers[event].remove(handler)
    
    def _fire_event(self, event: str, template: Template) -> None:
        """Fire an event to all registered handlers."""
        for handler in self._event_handlers.get(event, []):
            try:
                handler(template)
            except Exception as e:
                logger.error(f"Error in event handler for {event}: {e}")
    
    def _persist_template(self, template: Template) -> None:
        """Persist template to storage."""
        if not self.storage:
            return
        
        try:
            # Use M002 storage system
            data = template.to_dict()
            self.storage.create_document(
                f"template_{template.metadata.id}",
                data,
                {"type": "template", "category": template.metadata.category.value}
            )
        except Exception as e:
            logger.error(f"Failed to persist template {template.metadata.id}: {e}")
    
    def _load_template_from_storage(self, template_id: str) -> Template:
        """Load template from storage."""
        if not self.storage:
            raise TemplateStorageError("load", "No storage system available")
        
        try:
            doc_id = f"template_{template_id}"
            data = self.storage.get_document(doc_id)
            
            # Convert back to template model
            template_model = TemplateModel(**data)
            return Template(template_model)
            
        except Exception as e:
            raise TemplateStorageError("load", f"Failed to load from storage: {e}")
    
    def _remove_template_from_storage(self, template_id: str) -> None:
        """Remove template from storage."""
        if not self.storage:
            return
        
        try:
            doc_id = f"template_{template_id}"
            self.storage.delete_document(doc_id)
        except Exception as e:
            logger.error(f"Failed to remove template {template_id} from storage: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get registry metrics."""
        with self._lock:
            return {
                **self._metrics,
                'total_templates': len(self._templates),
                'active_templates': sum(1 for t in self._templates.values() if t.metadata.is_active),
                'custom_templates': sum(1 for t in self._templates.values() if t.metadata.is_custom)
            }
    
    def clear_cache(self) -> None:
        """Clear all template caches."""
        with self._lock:
            for template in self._templates.values():
                template.clear_cache()
            self.loader.clear_cache()
    
    def shutdown(self) -> None:
        """Shutdown the registry and cleanup resources."""
        logger.info("Shutting down template registry")
        
        # Clear caches
        self.clear_cache()
        
        # Clear event handlers
        self._event_handlers.clear()
        
        # Clear templates
        with self._lock:
            self._templates.clear()
            self.category_manager.clear()