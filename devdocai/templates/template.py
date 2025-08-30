"""
Template model and operations for M006 Template Registry.

This module provides the core Template class with operations
for template manipulation, rendering, and management.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import copy
import logging

from .models import (
    Template as TemplateModel,
    TemplateMetadata,
    TemplateVariable,
    TemplateSection,
    TemplateRenderContext,
    TemplateValidationResult
)
from .parser import TemplateParser
from .validator import TemplateValidator
from .exceptions import (
    TemplateRenderError,
    TemplateValidationError,
    TemplateVariableError
)

logger = logging.getLogger(__name__)


class Template:
    """Enhanced template class with operations."""
    
    def __init__(self, model: TemplateModel):
        """
        Initialize template.
        
        Args:
            model: Template model
        """
        self._model = model
        self._parser = TemplateParser()
        self._validator = TemplateValidator()
        self._render_cache: Dict[str, str] = {}
        
    @property
    def model(self) -> TemplateModel:
        """Get the underlying template model."""
        return self._model
    
    @property
    def metadata(self) -> TemplateMetadata:
        """Get template metadata."""
        return self._model.metadata
    
    @property
    def content(self) -> str:
        """Get template content."""
        return self._model.content
    
    @property
    def variables(self) -> List[TemplateVariable]:
        """Get template variables."""
        return self._model.variables
    
    @property
    def sections(self) -> List[TemplateSection]:
        """Get template sections."""
        return self._model.sections
    
    def render(self, context: Optional[Dict[str, Any]] = None,
              validate_context: bool = True) -> str:
        """
        Render the template with the given context.
        
        Args:
            context: Variable values for rendering
            validate_context: Whether to validate context before rendering
            
        Returns:
            Rendered template content
            
        Raises:
            TemplateRenderError: If rendering fails
            TemplateValidationError: If context validation fails
        """
        context = context or {}
        
        # Validate context if requested
        if validate_context:
            errors = self._validator.validate_render_context(self._model, context)
            if errors:
                raise TemplateValidationError(errors)
        
        # Create render context
        render_context = self._create_render_context(context)
        
        # Check cache
        cache_key = self._get_cache_key(render_context)
        if cache_key in self._render_cache:
            logger.debug(f"Using cached render for template {self.metadata.id}")
            return self._render_cache[cache_key]
        
        try:
            # Parse and render template
            rendered = self._parser.parse(self._model, render_context)
            
            # Cache the result
            self._render_cache[cache_key] = rendered
            
            # Update usage count
            self._model.metadata.usage_count += 1
            self._model.metadata.updated_at = datetime.now()
            
            return rendered
            
        except Exception as e:
            if isinstance(e, TemplateRenderError):
                raise
            raise TemplateRenderError(f"Failed to render template: {str(e)}")
    
    def _create_render_context(self, context: Dict[str, Any]) -> TemplateRenderContext:
        """Create render context from dictionary."""
        # Separate different types of context data
        variables = {}
        sections = {}
        loops = {}
        
        for key, value in context.items():
            if key.startswith('section_'):
                # Section inclusion flags
                section_name = key[8:]  # Remove 'section_' prefix
                sections[section_name] = bool(value)
            elif key.startswith('loop_'):
                # Loop data
                loop_name = key[5:]  # Remove 'loop_' prefix
                if isinstance(value, (list, tuple)):
                    loops[loop_name] = value
            else:
                # Regular variables
                variables[key] = value
        
        # Add default values for missing optional variables
        for var in self._model.variables:
            if var.name not in variables and not var.required and var.default is not None:
                variables[var.name] = var.default
        
        return TemplateRenderContext(
            variables=variables,
            sections=sections,
            loops=loops
        )
    
    def _get_cache_key(self, context: TemplateRenderContext) -> str:
        """Generate cache key for render context."""
        import hashlib
        import json
        
        # Create a deterministic string representation
        context_str = json.dumps({
            'variables': context.variables,
            'sections': context.sections,
            'loops': [str(v) for v in context.loops.values()]
        }, sort_keys=True, default=str)
        
        # Hash it
        return hashlib.md5(f"{self.metadata.id}:{context_str}".encode()).hexdigest()
    
    def validate(self) -> TemplateValidationResult:
        """
        Validate the template.
        
        Returns:
            Validation result
        """
        return self._validator.validate(self._model)
    
    def clone(self, new_id: Optional[str] = None, 
             new_name: Optional[str] = None) -> "Template":
        """
        Create a clone of this template.
        
        Args:
            new_id: ID for the cloned template
            new_name: Name for the cloned template
            
        Returns:
            Cloned template
        """
        # Deep copy the model
        cloned_model = copy.deepcopy(self._model)
        
        # Update metadata
        if new_id:
            cloned_model.metadata.id = new_id
        else:
            cloned_model.metadata.id = f"{self.metadata.id}_copy"
        
        if new_name:
            cloned_model.metadata.name = new_name
        else:
            cloned_model.metadata.name = f"{self.metadata.name} (Copy)"
        
        cloned_model.metadata.is_custom = True
        cloned_model.metadata.created_at = datetime.now()
        cloned_model.metadata.updated_at = datetime.now()
        cloned_model.metadata.usage_count = 0
        
        return Template(cloned_model)
    
    def add_variable(self, variable: TemplateVariable) -> None:
        """
        Add a variable to the template.
        
        Args:
            variable: Variable to add
            
        Raises:
            TemplateVariableError: If variable already exists
        """
        # Check for duplicates
        for existing_var in self._model.variables:
            if existing_var.name == variable.name:
                raise TemplateVariableError(variable.name, "Variable already exists")
        
        self._model.variables.append(variable)
        self._model.metadata.updated_at = datetime.now()
        
        # Clear render cache as template structure changed
        self._render_cache.clear()
    
    def remove_variable(self, variable_name: str) -> bool:
        """
        Remove a variable from the template.
        
        Args:
            variable_name: Name of variable to remove
            
        Returns:
            True if removed, False if not found
        """
        for i, var in enumerate(self._model.variables):
            if var.name == variable_name:
                self._model.variables.pop(i)
                self._model.metadata.updated_at = datetime.now()
                self._render_cache.clear()
                return True
        return False
    
    def update_variable(self, variable_name: str, 
                       updates: Dict[str, Any]) -> bool:
        """
        Update a variable's properties.
        
        Args:
            variable_name: Name of variable to update
            updates: Dictionary of updates
            
        Returns:
            True if updated, False if not found
        """
        for var in self._model.variables:
            if var.name == variable_name:
                for key, value in updates.items():
                    if hasattr(var, key):
                        setattr(var, key, value)
                self._model.metadata.updated_at = datetime.now()
                self._render_cache.clear()
                return True
        return False
    
    def add_section(self, section: TemplateSection) -> None:
        """
        Add a section to the template.
        
        Args:
            section: Section to add
        """
        self._model.sections.append(section)
        self._model.metadata.updated_at = datetime.now()
        self._render_cache.clear()
    
    def remove_section(self, section_name: str) -> bool:
        """
        Remove a section from the template.
        
        Args:
            section_name: Name of section to remove
            
        Returns:
            True if removed, False if not found
        """
        for i, section in enumerate(self._model.sections):
            if section.name == section_name:
                self._model.sections.pop(i)
                self._model.metadata.updated_at = datetime.now()
                self._render_cache.clear()
                return True
        return False
    
    def update_content(self, new_content: str) -> None:
        """
        Update the template content.
        
        Args:
            new_content: New template content
        """
        self._model.content = new_content
        self._model.metadata.updated_at = datetime.now()
        self._render_cache.clear()
        
        # Extract and update variables from new content
        extracted_vars = self._parser.extract_variables(new_content)
        
        # Add new variables that aren't defined
        existing_var_names = {var.name for var in self._model.variables}
        for var_name in extracted_vars:
            if var_name not in existing_var_names:
                # Add as optional variable by default
                new_var = TemplateVariable(
                    name=var_name,
                    description=f"Variable {var_name}",
                    required=False,
                    type="string"
                )
                self._model.variables.append(new_var)
    
    def merge(self, other: "Template") -> None:
        """
        Merge another template into this one.
        
        Args:
            other: Template to merge
        """
        # Merge variables (avoiding duplicates)
        existing_var_names = {var.name for var in self._model.variables}
        for var in other.variables:
            if var.name not in existing_var_names:
                self._model.variables.append(copy.deepcopy(var))
        
        # Merge sections (avoiding duplicates)
        existing_section_names = {section.name for section in self._model.sections}
        for section in other.sections:
            if section.name not in existing_section_names:
                self._model.sections.append(copy.deepcopy(section))
        
        # Merge tags
        existing_tags = set(self._model.metadata.tags)
        for tag in other.metadata.tags:
            if tag not in existing_tags:
                self._model.metadata.tags.append(tag)
        
        # Merge includes
        existing_includes = set(self._model.includes)
        for include in other.model.includes:
            if include not in existing_includes:
                self._model.includes.append(include)
        
        self._model.metadata.updated_at = datetime.now()
        self._render_cache.clear()
    
    def clear_cache(self) -> None:
        """Clear the render cache."""
        self._render_cache.clear()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert template to dictionary.
        
        Returns:
            Dictionary representation
        """
        return self._model.model_dump()