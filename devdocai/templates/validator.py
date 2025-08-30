"""
Template validator for M006 Template Registry.

This module provides validation capabilities for templates,
ensuring syntax correctness and structural integrity.
"""

import re
from typing import List, Set, Optional
import logging

from .models import (
    Template,
    TemplateValidationResult,
    TemplateVariable,
    TemplateMetadata
)
from .parser import TemplateParser
from .exceptions import TemplateValidationError

logger = logging.getLogger(__name__)


class TemplateValidator:
    """Validator for template syntax and structure."""
    
    def __init__(self):
        """Initialize template validator."""
        self.parser = TemplateParser()
        self._max_template_size = 1024 * 1024  # 1MB
        self._max_variable_count = 100
        self._max_include_count = 20
        
    def validate(self, template: Template) -> TemplateValidationResult:
        """
        Validate a template for syntax and structural correctness.
        
        Args:
            template: Template to validate
            
        Returns:
            Validation result with errors and warnings
        """
        errors = []
        warnings = []
        
        try:
            # Validate metadata
            metadata_errors = self._validate_metadata(template.metadata)
            errors.extend(metadata_errors)
            
            # Validate content size
            if len(template.content) > self._max_template_size:
                errors.append(f"Template content exceeds maximum size ({self._max_template_size} bytes)")
            
            # Validate syntax
            syntax_valid, syntax_errors = self.parser.validate_syntax(template.content)
            if not syntax_valid:
                errors.extend(syntax_errors)
            
            # Validate variables
            var_errors, var_warnings = self._validate_variables(template)
            errors.extend(var_errors)
            warnings.extend(var_warnings)
            
            # Check for missing and unused variables
            missing_vars, unused_vars = self._check_variable_usage(template)
            if missing_vars:
                warnings.append(f"Variables referenced but not defined: {', '.join(missing_vars)}")
            if unused_vars:
                warnings.append(f"Variables defined but not used: {', '.join(unused_vars)}")
            
            # Validate sections
            section_errors = self._validate_sections(template)
            errors.extend(section_errors)
            
            # Validate includes
            include_errors = self._validate_includes(template)
            errors.extend(include_errors)
            
            # Check for security issues
            security_warnings = self._check_security(template)
            warnings.extend(security_warnings)
            
            return TemplateValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                missing_variables=missing_vars,
                unused_variables=unused_vars
            )
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            errors.append(f"Unexpected validation error: {str(e)}")
            return TemplateValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings
            )
    
    def _validate_metadata(self, metadata: TemplateMetadata) -> List[str]:
        """Validate template metadata."""
        errors = []
        
        # Validate required fields
        if not metadata.name:
            errors.append("Template name is required")
        elif len(metadata.name) > 100:
            errors.append("Template name exceeds 100 characters")
        
        if not metadata.description:
            errors.append("Template description is required")
        elif len(metadata.description) > 500:
            errors.append("Template description exceeds 500 characters")
        
        # Validate ID format
        if metadata.id and not re.match(r'^[a-zA-Z0-9_-]+$', metadata.id):
            errors.append(f"Invalid template ID format: {metadata.id}")
        
        # Validate tags
        if len(metadata.tags) > 20:
            errors.append("Too many tags (maximum 20)")
        
        for tag in metadata.tags:
            if len(tag) > 50:
                errors.append(f"Tag '{tag}' exceeds 50 characters")
            if not re.match(r'^[a-zA-Z0-9_-]+$', tag):
                errors.append(f"Invalid tag format: {tag}")
        
        return errors
    
    def _validate_variables(self, template: Template) -> tuple[List[str], List[str]]:
        """Validate template variables."""
        errors = []
        warnings = []
        
        if len(template.variables) > self._max_variable_count:
            errors.append(f"Too many variables (maximum {self._max_variable_count})")
        
        variable_names = set()
        for var in template.variables:
            # Check for duplicate variable names
            if var.name in variable_names:
                errors.append(f"Duplicate variable name: {var.name}")
            variable_names.add(var.name)
            
            # Validate variable name format
            if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', var.name):
                errors.append(f"Invalid variable name format: {var.name}")
            
            # Validate validation pattern if provided
            if var.validation_pattern:
                try:
                    re.compile(var.validation_pattern)
                except re.error as e:
                    errors.append(f"Invalid regex pattern for variable '{var.name}': {e}")
            
            # Check for conflicting settings
            if not var.required and var.default is None:
                warnings.append(f"Optional variable '{var.name}' has no default value")
            
            # Validate variable type
            valid_types = ['string', 'number', 'boolean', 'list', 'object', 'date', 'email', 'url']
            if var.type not in valid_types:
                errors.append(f"Invalid variable type '{var.type}' for variable '{var.name}'")
        
        return errors, warnings
    
    def _check_variable_usage(self, template: Template) -> tuple[List[str], List[str]]:
        """Check for missing and unused variables."""
        # Extract variables referenced in content
        referenced_vars = set(self.parser.extract_variables(template.content))
        
        # Get defined variables
        defined_vars = {var.name for var in template.variables}
        
        # Find missing and unused
        missing_vars = list(referenced_vars - defined_vars)
        unused_vars = list(defined_vars - referenced_vars)
        
        return missing_vars, unused_vars
    
    def _validate_sections(self, template: Template) -> List[str]:
        """Validate template sections."""
        errors = []
        
        section_names = set()
        for section in template.sections:
            # Check for duplicate section names
            if section.name in section_names:
                errors.append(f"Duplicate section name: {section.name}")
            section_names.add(section.name)
            
            # Validate section name format
            if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', section.name):
                errors.append(f"Invalid section name format: {section.name}")
            
            # Check if section is referenced in content
            section_pattern = f"<!-- SECTION: {section.name} -->"
            if section_pattern not in template.content:
                errors.append(f"Section '{section.name}' defined but not used in template")
        
        return errors
    
    def _validate_includes(self, template: Template) -> List[str]:
        """Validate template includes."""
        errors = []
        
        if len(template.includes) > self._max_include_count:
            errors.append(f"Too many includes (maximum {self._max_include_count})")
        
        for include in template.includes:
            # Validate include path format
            if not include:
                errors.append("Empty include path")
            elif '..' in include:
                errors.append(f"Include path contains parent directory reference: {include}")
            elif include.startswith('/'):
                errors.append(f"Include path is absolute: {include}")
        
        # Check for circular includes (simple check)
        if template.metadata.id in template.includes:
            errors.append("Template includes itself")
        
        return errors
    
    def _check_security(self, template: Template) -> List[str]:
        """Check for potential security issues in template."""
        warnings = []
        
        # Check for potential script injection
        script_patterns = [
            r'<script[^>]*>',
            r'javascript:',
            r'on\w+\s*=',  # Event handlers
            r'eval\s*\(',
            r'exec\s*\('
        ]
        
        for pattern in script_patterns:
            if re.search(pattern, template.content, re.IGNORECASE):
                warnings.append(f"Potential security risk: pattern '{pattern}' found in template")
        
        # Check for SQL-like patterns (potential injection)
        sql_patterns = [
            r'\bDROP\s+TABLE\b',
            r'\bDELETE\s+FROM\b',
            r'\bUPDATE\s+.*\s+SET\b',
            r'\bINSERT\s+INTO\b'
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, template.content, re.IGNORECASE):
                warnings.append(f"Potential SQL pattern found: '{pattern}'")
        
        # Check for excessive use of special characters
        special_char_count = len(re.findall(r'[<>\"\'`]', template.content))
        if special_char_count > len(template.content) * 0.1:  # More than 10%
            warnings.append("High concentration of special characters detected")
        
        return warnings
    
    def validate_render_context(self, template: Template, context: dict) -> List[str]:
        """
        Validate that a render context has all required variables.
        
        Args:
            template: Template to validate against
            context: Render context dictionary
            
        Returns:
            List of validation errors
        """
        errors = []
        
        for var in template.variables:
            if var.required and var.name not in context:
                errors.append(f"Required variable '{var.name}' not provided in context")
            
            if var.name in context:
                value = context[var.name]
                
                # Type validation
                if var.type == 'number' and not isinstance(value, (int, float)):
                    errors.append(f"Variable '{var.name}' should be a number")
                elif var.type == 'boolean' and not isinstance(value, bool):
                    errors.append(f"Variable '{var.name}' should be a boolean")
                elif var.type == 'list' and not isinstance(value, (list, tuple)):
                    errors.append(f"Variable '{var.name}' should be a list")
                elif var.type == 'object' and not isinstance(value, dict):
                    errors.append(f"Variable '{var.name}' should be an object")
                
                # Pattern validation
                if var.validation_pattern and var.type == 'string':
                    if not re.match(var.validation_pattern, str(value)):
                        errors.append(f"Variable '{var.name}' does not match validation pattern")
        
        return errors