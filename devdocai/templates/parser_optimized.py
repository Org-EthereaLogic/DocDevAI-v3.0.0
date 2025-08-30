"""
Optimized Template Parser for M006 Template Registry - Pass 2 Performance.

This module provides performance-optimized parsing with compiled patterns,
efficient substitution, and caching mechanisms.
"""

import re
from typing import Dict, List, Any, Optional, Tuple, Pattern
import logging
from functools import lru_cache
import hashlib

from .models import Template, TemplateRenderContext, TemplateVariable
from .exceptions import (
    TemplateParseError,
    TemplateRenderError,
    TemplateIncludeError,
    TemplateVariableError
)

logger = logging.getLogger(__name__)


class CompiledPattern:
    """Pre-compiled regex patterns for efficient matching."""
    
    __slots__ = ['variable', 'section', 'conditional', 'loop', 'include', 'comment']
    
    def __init__(self):
        """Initialize and compile all patterns once."""
        self.variable = re.compile(r'\{\{([^}]+)\}\}')
        self.section = re.compile(r'<!-- SECTION: (\w+) -->(.*?)<!-- END SECTION: \1 -->', re.DOTALL)
        self.conditional = re.compile(r'<!-- IF ([^-]+) -->(.*?)<!-- END IF -->', re.DOTALL)
        self.loop = re.compile(r'<!-- FOR (\w+) IN (\w+) -->(.*?)<!-- END FOR -->', re.DOTALL)
        self.include = re.compile(r'<!-- INCLUDE ([^-]+) -->')
        self.comment = re.compile(r'<!-- COMMENT: [^-]+ -->')


# Global compiled patterns instance
PATTERNS = CompiledPattern()


class OptimizedTemplateParser:
    """Performance-optimized template parser with caching and compilation."""
    
    def __init__(self, cache_size: int = 128):
        """
        Initialize optimized parser.
        
        Args:
            cache_size: Size of LRU cache for parsed results
        """
        self._include_cache: Dict[str, str] = {}
        self._parse_cache: Dict[str, Any] = {}
        self._max_include_depth = 5
        self._cache_size = cache_size
        
        # Create LRU cached version of parse method
        self._cached_parse = lru_cache(maxsize=cache_size)(self._parse_internal)
    
    def parse(self, template: Template, context: TemplateRenderContext) -> str:
        """
        Parse and render a template with optimized performance.
        
        Args:
            template: Template to parse
            context: Rendering context with variables and data
            
        Returns:
            Rendered template content
        """
        # Generate cache key
        cache_key = self._generate_cache_key(template, context)
        
        # Check parse cache
        if cache_key in self._parse_cache:
            return self._parse_cache[cache_key]
        
        try:
            # Use optimized parsing
            result = self._parse_optimized(template, context)
            
            # Cache result
            self._parse_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            if isinstance(e, (TemplateParseError, TemplateRenderError)):
                raise
            raise TemplateParseError(f"Failed to parse template: {str(e)}")
    
    def _parse_optimized(self, template: Template, context: TemplateRenderContext) -> str:
        """Optimized parsing with minimal regex operations."""
        content = template.content
        
        # Single-pass processing where possible
        # Remove comments first (fastest operation)
        content = PATTERNS.comment.sub('', content)
        
        # Process includes (may add more content)
        if '<!-- INCLUDE' in content:
            content = self._process_includes_fast(content, context)
        
        # Process loops (complex, do before conditionals)
        if '<!-- FOR' in content:
            content = self._process_loops_fast(content, context)
        
        # Process conditionals
        if '<!-- IF' in content:
            content = self._process_conditionals_fast(content, context)
        
        # Process sections
        if '<!-- SECTION:' in content:
            content = self._process_sections_fast(content, context)
        
        # Process variables (most common, do last for efficiency)
        if '{{' in content:
            content = self._process_variables_fast(content, context, template.variables)
        
        return content.strip()
    
    def _process_includes_fast(self, content: str, context: TemplateRenderContext, depth: int = 0) -> str:
        """Fast include processing with caching."""
        if depth >= self._max_include_depth:
            raise TemplateIncludeError("max_depth", f"Maximum include depth ({self._max_include_depth}) exceeded")
        
        # Use finditer for single-pass processing
        matches = list(PATTERNS.include.finditer(content))
        if not matches:
            return content
        
        # Process from end to preserve positions
        for match in reversed(matches):
            include_path = match.group(1).strip()
            
            # Check cache
            if include_path in self._include_cache:
                included_content = self._include_cache[include_path]
            else:
                included_content = self._load_include(include_path)
                self._include_cache[include_path] = included_content
            
            # Recursively process includes
            included_content = self._process_includes_fast(included_content, context, depth + 1)
            
            # Replace in content
            start, end = match.span()
            content = content[:start] + included_content + content[end:]
        
        return content
    
    def _process_loops_fast(self, content: str, context: TemplateRenderContext) -> str:
        """Fast loop processing with pre-compiled patterns."""
        matches = list(PATTERNS.loop.finditer(content))
        if not matches:
            return content
        
        # Process from end to preserve positions
        for match in reversed(matches):
            item_var = match.group(1).strip()
            collection_var = match.group(2).strip()
            loop_content = match.group(3)
            
            if collection_var not in context.loops:
                logger.warning(f"Loop variable '{collection_var}' not found in context")
                content = content[:match.start()] + content[match.end():]
                continue
            
            collection = context.loops[collection_var]
            if not isinstance(collection, (list, tuple)):
                raise TemplateParseError(f"Loop variable '{collection_var}' is not iterable")
            
            # Batch process loop items
            results = []
            for item in collection:
                # Fast variable substitution for loop content
                item_content = loop_content
                item_content = item_content.replace(f"{{{{{item_var}}}}}", str(item))
                
                # Process nested variables if needed
                if '{{' in item_content:
                    temp_context = TemplateRenderContext(
                        variables={**context.variables, item_var: item},
                        sections=context.sections,
                        loops=context.loops
                    )
                    item_content = self._process_variables_fast(item_content, temp_context, [])
                
                results.append(item_content)
            
            # Replace loop with results
            start, end = match.span()
            content = content[:start] + "\n".join(results) + content[end:]
        
        return content
    
    def _process_conditionals_fast(self, content: str, context: TemplateRenderContext) -> str:
        """Fast conditional processing."""
        matches = list(PATTERNS.conditional.finditer(content))
        if not matches:
            return content
        
        # Process from end to preserve positions
        for match in reversed(matches):
            condition = match.group(1).strip()
            conditional_content = match.group(2)
            
            # Fast condition evaluation
            if self._evaluate_condition_fast(condition, context):
                replacement = conditional_content
            else:
                replacement = ""
            
            start, end = match.span()
            content = content[:start] + replacement + content[end:]
        
        return content
    
    def _evaluate_condition_fast(self, condition: str, context: TemplateRenderContext) -> bool:
        """Fast condition evaluation with caching."""
        # Simple truthiness check
        if condition in context.variables:
            return bool(context.variables[condition])
        
        # Negation check
        if condition.startswith("NOT "):
            var_name = condition[4:].strip()
            return var_name not in context.variables or not context.variables[var_name]
        
        # Equality check (optimized)
        if "==" in condition:
            parts = condition.split("==", 1)
            if len(parts) == 2:
                left = parts[0].strip()
                right = parts[1].strip().strip('"\'')
                left_val = context.variables.get(left, left)
                right_val = context.variables.get(right, right)
                return str(left_val) == str(right_val)
        
        return False
    
    def _process_sections_fast(self, content: str, context: TemplateRenderContext) -> str:
        """Fast section processing."""
        matches = list(PATTERNS.section.finditer(content))
        if not matches:
            return content
        
        # Process from end to preserve positions
        for match in reversed(matches):
            section_name = match.group(1)
            section_content = match.group(2)
            
            # Check if section should be included
            include_section = context.sections.get(section_name, True)
            
            start, end = match.span()
            if include_section:
                content = content[:start] + section_content + content[end:]
            else:
                content = content[:start] + content[end:]
        
        return content
    
    def _process_variables_fast(self, content: str, context: TemplateRenderContext, 
                               variables: List[TemplateVariable]) -> str:
        """Ultra-fast variable substitution using string operations."""
        # Build variable map for quick lookup
        var_map = {}
        for var in variables:
            if var.name in context.variables:
                var_map[var.name] = str(context.variables[var.name])
            elif var.default is not None:
                var_map[var.name] = str(var.default)
        
        # Add all context variables
        for key, value in context.variables.items():
            if key not in var_map:
                var_map[key] = str(value) if not isinstance(value, dict) else str(value)
        
        # Single-pass replacement using regex with function
        def replace_var(match):
            var_expr = match.group(1).strip()
            
            # Handle nested property access
            if '.' in var_expr:
                parts = var_expr.split('.')
                value = context.variables
                for part in parts:
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        return match.group(0)  # Return original if not found
                return str(value)
            
            # Direct lookup
            return var_map.get(var_expr, match.group(0))
        
        return PATTERNS.variable.sub(replace_var, content)
    
    def _load_include(self, include_path: str) -> str:
        """Load included template content."""
        # Placeholder - would integrate with registry
        return f"<!-- Included: {include_path} -->"
    
    def _generate_cache_key(self, template: Template, context: TemplateRenderContext) -> str:
        """Generate efficient cache key using hashing."""
        # Create deterministic key
        key_parts = [
            template.metadata.id,
            str(sorted(context.variables.items())),
            str(sorted(context.sections.items())),
            str(sorted((k, len(v)) for k, v in context.loops.items()))
        ]
        key_str = "|".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def extract_variables(self, content: str) -> List[str]:
        """Extract all variable names from template content."""
        variables = set()
        
        # Use compiled pattern for speed
        for match in PATTERNS.variable.finditer(content):
            var_expr = match.group(1).strip()
            base_var = var_expr.split('.')[0]
            variables.add(base_var)
        
        # Extract from conditionals
        for match in PATTERNS.conditional.finditer(content):
            condition = match.group(1).strip()
            # Quick extraction
            for word in condition.split():
                if word not in ['NOT', '==', '!=', 'AND', 'OR'] and not word.startswith('"'):
                    variables.add(word)
        
        # Extract from loops
        for match in PATTERNS.loop.finditer(content):
            collection_var = match.group(2).strip()
            variables.add(collection_var)
        
        return sorted(list(variables))
    
    @lru_cache(maxsize=256)
    def validate_syntax(self, content: str) -> Tuple[bool, List[str]]:
        """
        Validate template syntax with caching.
        
        Returns:
            Tuple of (is_valid, errors)
        """
        errors = []
        
        # Fast bracket counting
        open_count = content.count("{{")
        close_count = content.count("}}")
        if open_count != close_count:
            errors.append(f"Unbalanced variable brackets: {open_count} open, {close_count} close")
        
        # Use regex for section validation
        section_starts = set(re.findall(r'<!-- SECTION: (\w+) -->', content))
        section_ends = set(re.findall(r'<!-- END SECTION: (\w+) -->', content))
        
        unclosed = section_starts - section_ends
        if unclosed:
            errors.append(f"Unclosed sections: {', '.join(unclosed)}")
        
        unopened = section_ends - section_starts
        if unopened:
            errors.append(f"Section ends without starts: {', '.join(unopened)}")
        
        # Fast conditional counting
        if_count = content.count('<!-- IF')
        endif_count = content.count('<!-- END IF -->')
        if if_count != endif_count:
            errors.append(f"Unbalanced conditionals: {if_count} IF, {endif_count} END IF")
        
        # Fast loop counting
        for_count = content.count('<!-- FOR')
        endfor_count = content.count('<!-- END FOR -->')
        if for_count != endfor_count:
            errors.append(f"Unbalanced loops: {for_count} FOR, {endfor_count} END FOR")
        
        return len(errors) == 0, errors
    
    def clear_cache(self):
        """Clear all parser caches."""
        self._include_cache.clear()
        self._parse_cache.clear()
        self._cached_parse.cache_clear()
        logger.info("Cleared parser caches")