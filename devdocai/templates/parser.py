"""
Template parser for M006 Template Registry.

This module provides parsing and rendering capabilities for templates,
supporting variables, sections, conditionals, loops, and includes.
"""

import re
from typing import Dict, List, Any, Optional, Tuple
import logging
from pathlib import Path

from .models import Template, TemplateRenderContext, TemplateVariable
from .exceptions import (
    TemplateParseError,
    TemplateRenderError,
    TemplateIncludeError,
    TemplateVariableError
)

logger = logging.getLogger(__name__)


class TemplateParser:
    """Parser for template content with variable substitution and control structures."""
    
    # Regex patterns for template syntax
    VARIABLE_PATTERN = re.compile(r'\{\{([^}]+)\}\}')
    SECTION_PATTERN = re.compile(r'<!-- SECTION: (\w+) -->(.*?)<!-- END SECTION: \1 -->', re.DOTALL)
    CONDITIONAL_PATTERN = re.compile(r'<!-- IF ([^-]+) -->(.*?)<!-- END IF -->', re.DOTALL)
    LOOP_PATTERN = re.compile(r'<!-- FOR (\w+) IN (\w+) -->(.*?)<!-- END FOR -->', re.DOTALL)
    INCLUDE_PATTERN = re.compile(r'<!-- INCLUDE ([^-]+) -->')
    COMMENT_PATTERN = re.compile(r'<!-- COMMENT: [^-]+ -->')
    
    def __init__(self):
        """Initialize template parser."""
        self._include_cache: Dict[str, str] = {}
        self._max_include_depth = 5
        
    def parse(self, template: Template, context: TemplateRenderContext) -> str:
        """
        Parse and render a template with the given context.
        
        Args:
            template: Template to parse
            context: Rendering context with variables and data
            
        Returns:
            Rendered template content
            
        Raises:
            TemplateParseError: If parsing fails
            TemplateRenderError: If rendering fails
        """
        try:
            content = template.content
            
            # Process in order of precedence
            content = self._process_comments(content)
            content = self._process_includes(content, context, depth=0)
            content = self._process_loops(content, context)
            content = self._process_conditionals(content, context)
            content = self._process_sections(content, context)
            content = self._process_variables(content, context, template.variables)
            
            return content.strip()
            
        except Exception as e:
            if isinstance(e, (TemplateParseError, TemplateRenderError)):
                raise
            raise TemplateParseError(f"Failed to parse template: {str(e)}")
    
    def _process_comments(self, content: str) -> str:
        """Remove comment blocks from content."""
        return self.COMMENT_PATTERN.sub('', content)
    
    def _process_includes(self, content: str, context: TemplateRenderContext, depth: int) -> str:
        """Process template includes."""
        if depth >= self._max_include_depth:
            raise TemplateIncludeError("max_depth", f"Maximum include depth ({self._max_include_depth}) exceeded")
        
        def replace_include(match):
            include_path = match.group(1).strip()
            
            # Check cache first
            if include_path in self._include_cache:
                included_content = self._include_cache[include_path]
            else:
                # Load included template (this would integrate with the registry)
                included_content = self._load_include(include_path)
                self._include_cache[include_path] = included_content
            
            # Recursively process includes in the included content
            return self._process_includes(included_content, context, depth + 1)
        
        return self.INCLUDE_PATTERN.sub(replace_include, content)
    
    def _load_include(self, include_path: str) -> str:
        """Load included template content."""
        # This will be implemented to work with the registry
        # For now, return a placeholder
        return f"<!-- Included: {include_path} -->"
    
    def _process_loops(self, content: str, context: TemplateRenderContext) -> str:
        """Process FOR loops in template."""
        def replace_loop(match):
            item_var = match.group(1).strip()
            collection_var = match.group(2).strip()
            loop_content = match.group(3)
            
            if collection_var not in context.loops:
                logger.warning(f"Loop variable '{collection_var}' not found in context")
                return ""
            
            collection = context.loops[collection_var]
            if not isinstance(collection, (list, tuple)):
                raise TemplateParseError(f"Loop variable '{collection_var}' is not iterable")
            
            results = []
            for item in collection:
                # Create temporary context with loop variable
                loop_context = TemplateRenderContext(
                    variables={**context.variables, item_var: item},
                    sections=context.sections,
                    loops=context.loops
                )
                # Process loop content with temporary context
                processed = self._process_variables(loop_content, loop_context, [])
                results.append(processed)
            
            return "\n".join(results)
        
        return self.LOOP_PATTERN.sub(replace_loop, content)
    
    def _process_conditionals(self, content: str, context: TemplateRenderContext) -> str:
        """Process IF conditionals in template."""
        def replace_conditional(match):
            condition = match.group(1).strip()
            conditional_content = match.group(2)
            
            # Evaluate condition
            if self._evaluate_condition(condition, context):
                return conditional_content
            return ""
        
        return self.CONDITIONAL_PATTERN.sub(replace_conditional, content)
    
    def _evaluate_condition(self, condition: str, context: TemplateRenderContext) -> bool:
        """Evaluate a conditional expression."""
        try:
            # Simple evaluation - check if variable exists and is truthy
            # This could be extended to support more complex expressions
            if condition in context.variables:
                return bool(context.variables[condition])
            
            # Check for negation
            if condition.startswith("NOT "):
                var_name = condition[4:].strip()
                return var_name not in context.variables or not context.variables[var_name]
            
            # Check for equality
            if "==" in condition:
                left, right = condition.split("==", 1)
                left_val = context.variables.get(left.strip(), left.strip())
                right_val = context.variables.get(right.strip(), right.strip().strip('"\''))
                return str(left_val) == str(right_val)
            
            return False
            
        except Exception as e:
            logger.warning(f"Failed to evaluate condition '{condition}': {e}")
            return False
    
    def _process_sections(self, content: str, context: TemplateRenderContext) -> str:
        """Process sections in template."""
        def replace_section(match):
            section_name = match.group(1)
            section_content = match.group(2)
            
            # Check if section should be included
            if section_name in context.sections:
                if context.sections[section_name]:
                    return section_content
                return ""
            
            # Default to including section if not specified
            return section_content
        
        return self.SECTION_PATTERN.sub(replace_section, content)
    
    def _process_variables(self, content: str, context: TemplateRenderContext, 
                          variables: List[TemplateVariable]) -> str:
        """Process variable substitutions in template."""
        missing_vars = []
        
        def replace_variable(match):
            var_expr = match.group(1).strip()
            
            # Handle nested property access (e.g., user.name)
            parts = var_expr.split('.')
            value = context.variables
            
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    # Check if variable has a default value
                    for var in variables:
                        if var.name == var_expr and var.default is not None:
                            return str(var.default)
                    
                    # Track missing required variables
                    for var in variables:
                        if var.name == var_expr and var.required:
                            missing_vars.append(var_expr)
                    
                    # Return placeholder for missing variable
                    return f"{{{{{var_expr}}}}}"
            
            return str(value)
        
        result = self.VARIABLE_PATTERN.sub(replace_variable, content)
        
        if missing_vars:
            raise TemplateRenderError("Missing required variables", missing_vars)
        
        return result
    
    def extract_variables(self, content: str) -> List[str]:
        """Extract all variable names from template content."""
        variables = set()
        
        # Extract from variable placeholders
        for match in self.VARIABLE_PATTERN.finditer(content):
            var_expr = match.group(1).strip()
            # Handle nested properties
            base_var = var_expr.split('.')[0]
            variables.add(base_var)
        
        # Extract from conditionals
        for match in self.CONDITIONAL_PATTERN.finditer(content):
            condition = match.group(1).strip()
            # Extract variable names from condition
            for word in condition.split():
                if word not in ['NOT', '==', '!=', 'AND', 'OR'] and not word.startswith('"'):
                    variables.add(word)
        
        # Extract from loops
        for match in self.LOOP_PATTERN.finditer(content):
            collection_var = match.group(2).strip()
            variables.add(collection_var)
        
        return sorted(list(variables))
    
    def validate_syntax(self, content: str) -> Tuple[bool, List[str]]:
        """
        Validate template syntax.
        
        Returns:
            Tuple of (is_valid, errors)
        """
        errors = []
        
        # Check for balanced variable brackets
        open_count = content.count("{{")
        close_count = content.count("}}")
        if open_count != close_count:
            errors.append(f"Unbalanced variable brackets: {open_count} open, {close_count} close")
        
        # Check for unclosed sections
        section_starts = re.findall(r'<!-- SECTION: (\w+) -->', content)
        section_ends = re.findall(r'<!-- END SECTION: (\w+) -->', content)
        
        for section in section_starts:
            if section not in section_ends:
                errors.append(f"Unclosed section: {section}")
        
        for section in section_ends:
            if section not in section_starts:
                errors.append(f"Section end without start: {section}")
        
        # Check for unclosed conditionals
        if_count = len(re.findall(r'<!-- IF', content))
        endif_count = len(re.findall(r'<!-- END IF -->', content))
        if if_count != endif_count:
            errors.append(f"Unbalanced conditionals: {if_count} IF, {endif_count} END IF")
        
        # Check for unclosed loops
        for_count = len(re.findall(r'<!-- FOR', content))
        endfor_count = len(re.findall(r'<!-- END FOR -->', content))
        if for_count != endfor_count:
            errors.append(f"Unbalanced loops: {for_count} FOR, {endfor_count} END FOR")
        
        return len(errors) == 0, errors