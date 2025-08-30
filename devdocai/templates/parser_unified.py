"""
Unified Template Parser for M006 - Pass 4 Refactoring.

This module provides a single, configurable template parser that combines
all features from the base, optimized, and secure parser implementations.
"""

import re
import ast
import html
from typing import Dict, List, Optional, Any, Set, Tuple, Pattern
from pathlib import Path
from dataclasses import dataclass
import logging
import hashlib
from functools import lru_cache

from .exceptions import (
    TemplateParseError,
    TemplateSecurityError,
    TemplateSyntaxError
)

logger = logging.getLogger(__name__)


@dataclass
class ParserConfig:
    """Configuration for the unified parser."""
    # Performance options
    enable_cache: bool = False
    cache_size: int = 1000
    enable_compilation: bool = False
    
    # Security options
    enable_security: bool = False
    enable_ssti_protection: bool = False
    enable_xss_protection: bool = False
    enable_path_traversal_check: bool = False
    enable_sandbox: bool = False
    
    # Parsing options
    max_template_size: int = 10 * 1024 * 1024  # 10MB
    max_parse_depth: int = 100
    max_variable_length: int = 1000
    allow_functions: bool = False
    allow_filters: bool = True
    
    @classmethod
    def basic(cls) -> 'ParserConfig':
        """Basic configuration with minimal features."""
        return cls()
    
    @classmethod
    def performance(cls) -> 'ParserConfig':
        """Performance-optimized configuration."""
        return cls(
            enable_cache=True,
            cache_size=2000,
            enable_compilation=True
        )
    
    @classmethod
    def secure(cls) -> 'ParserConfig':
        """Security-hardened configuration."""
        return cls(
            enable_security=True,
            enable_ssti_protection=True,
            enable_xss_protection=True,
            enable_path_traversal_check=True,
            enable_sandbox=True,
            allow_functions=False
        )
    
    @classmethod
    def enterprise(cls) -> 'ParserConfig':
        """Enterprise configuration with all features."""
        return cls(
            enable_cache=True,
            cache_size=2000,
            enable_compilation=True,
            enable_security=True,
            enable_ssti_protection=True,
            enable_xss_protection=True,
            enable_path_traversal_check=True,
            enable_sandbox=True,
            allow_functions=False
        )


class SecurityValidator:
    """Security validation for templates."""
    
    # Dangerous patterns for SSTI
    SSTI_PATTERNS = [
        r'__class__', r'__base__', r'__subclasses__',
        r'__globals__', r'__init__', r'__builtins__',
        r'__import__', r'__mro__', r'__dict__',
        r'eval\s*\(', r'exec\s*\(', r'compile\s*\(',
        r'open\s*\(', r'file\s*\(', r'input\s*\(',
        r'os\.', r'sys\.', r'subprocess\.',
        r'globals\s*\(', r'locals\s*\(', r'vars\s*\(',
        r'getattr\s*\(', r'setattr\s*\(', r'delattr\s*\(',
        r'\[\s*[\'\"]\s*__.*__\s*[\'\"]\s*\]',  # ['__class__'] access
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',  # onclick, onload, etc.
        r'<iframe[^>]*>',
        r'<embed[^>]*>',
        r'<object[^>]*>',
    ]
    
    # Path traversal patterns
    PATH_PATTERNS = [
        r'\.\./\.\.',  # ../..
        r'\.\.[/\\]',   # ../ or ..\
        r'[/\\]\.\.',   # /.. or \..
        r'\w+:[/\\]',   # C:/ or D:\
    ]
    
    def __init__(self, config: ParserConfig):
        self.config = config
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for efficiency."""
        if self.config.enable_ssti_protection:
            self.ssti_regex = re.compile(
                '|'.join(self.SSTI_PATTERNS),
                re.IGNORECASE | re.DOTALL
            )
        
        if self.config.enable_xss_protection:
            self.xss_regex = re.compile(
                '|'.join(self.XSS_PATTERNS),
                re.IGNORECASE | re.DOTALL
            )
        
        if self.config.enable_path_traversal_check:
            self.path_regex = re.compile(
                '|'.join(self.PATH_PATTERNS),
                re.IGNORECASE
            )
    
    def validate(self, content: str) -> Tuple[bool, List[str]]:
        """
        Validate content for security issues.
        
        Returns:
            Tuple of (is_safe, list_of_issues)
        """
        if not self.config.enable_security:
            return True, []
        
        issues = []
        
        # Check for SSTI
        if self.config.enable_ssti_protection:
            if self.ssti_regex.search(content):
                issues.append("SSTI pattern detected")
        
        # Check for XSS
        if self.config.enable_xss_protection:
            if self.xss_regex.search(content):
                issues.append("XSS pattern detected")
        
        # Check for path traversal
        if self.config.enable_path_traversal_check:
            if self.path_regex.search(content):
                issues.append("Path traversal pattern detected")
        
        return len(issues) == 0, issues
    
    def sanitize(self, content: str) -> str:
        """Sanitize content to remove security risks."""
        if not self.config.enable_security:
            return content
        
        # HTML escape for XSS protection
        if self.config.enable_xss_protection:
            content = html.escape(content)
        
        # Remove SSTI patterns
        if self.config.enable_ssti_protection:
            content = self.ssti_regex.sub('', content)
        
        # Remove path traversal patterns
        if self.config.enable_path_traversal_check:
            content = self.path_regex.sub('', content)
        
        return content


class UnifiedTemplateParser:
    """
    Unified template parser with configurable features.
    
    Supports basic {{variable}} substitution with optional advanced features
    based on configuration.
    """
    
    # Basic variable pattern: {{variable}} or {{variable|filter}}
    VARIABLE_PATTERN = re.compile(
        r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)'
        r'(?:\s*\|\s*([a-zA-Z_][a-zA-Z0-9_]*))?\s*\}\}'
    )
    
    # Control structures (if enabled)
    IF_PATTERN = re.compile(r'\{%\s*if\s+(.*?)\s*%\}(.*?)\{%\s*endif\s*%\}', re.DOTALL)
    FOR_PATTERN = re.compile(r'\{%\s*for\s+(\w+)\s+in\s+(.*?)\s*%\}(.*?)\{%\s*endfor\s*%\}', re.DOTALL)
    
    # Built-in filters
    FILTERS = {
        'upper': lambda x: str(x).upper(),
        'lower': lambda x: str(x).lower(),
        'title': lambda x: str(x).title(),
        'strip': lambda x: str(x).strip(),
        'escape': lambda x: html.escape(str(x)),
        'default': lambda x, d='': x if x else d,
        'length': lambda x: len(x) if hasattr(x, '__len__') else 0,
        'truncate': lambda x, n=50: str(x)[:n] + '...' if len(str(x)) > n else str(x),
    }
    
    def __init__(self, config: Optional[ParserConfig] = None):
        """
        Initialize unified parser.
        
        Args:
            config: Parser configuration
        """
        self.config = config or ParserConfig()
        self.security = SecurityValidator(self.config) if self.config.enable_security else None
        
        # Cache for compiled templates
        if self.config.enable_cache:
            self._cache: Dict[str, Any] = {}
            self._cache_hits = 0
            self._cache_misses = 0
        else:
            self._cache = None
        
        # Track parsing depth for recursion prevention
        self._parse_depth = 0
    
    def parse(self, template: str, context: Dict[str, Any]) -> str:
        """
        Parse and render a template with the given context.
        
        Args:
            template: Template string
            context: Variable context
            
        Returns:
            Rendered template
            
        Raises:
            TemplateParseError: If parsing fails
            TemplateSecurityError: If security check fails
        """
        # Size check
        if len(template) > self.config.max_template_size:
            raise TemplateParseError(f"Template exceeds max size of {self.config.max_template_size}")
        
        # Security validation
        if self.security:
            is_safe, issues = self.security.validate(template)
            if not is_safe:
                raise TemplateSecurityError(f"Security validation failed: {', '.join(issues)}")
        
        # Check cache
        if self._cache is not None:
            cache_key = self._get_cache_key(template)
            if cache_key in self._cache:
                self._cache_hits += 1
                compiled = self._cache[cache_key]
                return self._render_compiled(compiled, context)
            self._cache_misses += 1
        
        # Parse template
        try:
            self._parse_depth = 0
            result = self._parse_internal(template, context)
            
            # Cache if enabled
            if self._cache is not None and self.config.enable_compilation:
                cache_key = self._get_cache_key(template)
                compiled = self._compile_template(template)
                self._cache[cache_key] = compiled
            
            return result
            
        except RecursionError:
            raise TemplateParseError("Maximum parse depth exceeded")
        except Exception as e:
            raise TemplateParseError(f"Parse error: {str(e)}")
    
    def _parse_internal(self, template: str, context: Dict[str, Any]) -> str:
        """Internal parsing logic."""
        # Check recursion depth
        self._parse_depth += 1
        if self._parse_depth > self.config.max_parse_depth:
            raise TemplateParseError("Maximum parse depth exceeded")
        
        result = template
        
        # Process control structures if functions are allowed
        if self.config.allow_functions:
            # Process if statements
            result = self._process_if_statements(result, context)
            
            # Process for loops
            result = self._process_for_loops(result, context)
        
        # Process variables
        result = self._process_variables(result, context)
        
        self._parse_depth -= 1
        return result
    
    def _process_variables(self, template: str, context: Dict[str, Any]) -> str:
        """Process variable substitutions."""
        def replace_variable(match):
            var_path = match.group(1)
            filter_name = match.group(2)
            
            # Validate variable name length
            if len(var_path) > self.config.max_variable_length:
                return match.group(0)  # Return unchanged
            
            # Get variable value
            try:
                value = self._get_variable_value(var_path, context)
            except Exception:
                value = ''  # Default to empty string
            
            # Apply filter if specified
            if filter_name and self.config.allow_filters:
                value = self._apply_filter(value, filter_name)
            
            # Security sanitization
            if self.security and self.config.enable_xss_protection:
                value = html.escape(str(value))
            
            return str(value)
        
        return self.VARIABLE_PATTERN.sub(replace_variable, template)
    
    def _get_variable_value(self, var_path: str, context: Dict[str, Any]) -> Any:
        """Get variable value from context using dot notation."""
        parts = var_path.split('.')
        value = context
        
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part, '')
            elif hasattr(value, part):
                value = getattr(value, part)
            else:
                return ''
        
        return value
    
    def _apply_filter(self, value: Any, filter_name: str) -> Any:
        """Apply a filter to a value."""
        if filter_name in self.FILTERS:
            try:
                return self.FILTERS[filter_name](value)
            except Exception:
                return value
        return value
    
    def _process_if_statements(self, template: str, context: Dict[str, Any]) -> str:
        """Process if statements in template."""
        def replace_if(match):
            condition = match.group(1)
            content = match.group(2)
            
            # Simple condition evaluation (safe)
            try:
                # Only allow simple variable checks
                if self._evaluate_condition(condition, context):
                    return self._parse_internal(content, context)
                return ''
            except Exception:
                return ''
        
        return self.IF_PATTERN.sub(replace_if, template)
    
    def _process_for_loops(self, template: str, context: Dict[str, Any]) -> str:
        """Process for loops in template."""
        def replace_for(match):
            var_name = match.group(1)
            iterable_expr = match.group(2)
            content = match.group(3)
            
            try:
                # Get iterable from context
                iterable = self._get_variable_value(iterable_expr, context)
                
                if not hasattr(iterable, '__iter__'):
                    return ''
                
                results = []
                for item in iterable:
                    # Create new context with loop variable
                    loop_context = dict(context)
                    loop_context[var_name] = item
                    results.append(self._parse_internal(content, loop_context))
                
                return ''.join(results)
            except Exception:
                return ''
        
        return self.FOR_PATTERN.sub(replace_for, template)
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Safely evaluate a simple condition."""
        # Only allow simple variable existence checks
        condition = condition.strip()
        
        # Check for simple variable
        if condition in context:
            return bool(context[condition])
        
        # Check for "not variable"
        if condition.startswith('not '):
            var = condition[4:].strip()
            if var in context:
                return not bool(context[var])
        
        return False
    
    def _get_cache_key(self, template: str) -> str:
        """Generate cache key for template."""
        return hashlib.md5(template.encode()).hexdigest()
    
    def _compile_template(self, template: str) -> Any:
        """Compile template for faster rendering (if enabled)."""
        # This is a simplified compilation that pre-parses the template
        # In a real implementation, this could generate bytecode or an AST
        return {
            'template': template,
            'variables': list(self.VARIABLE_PATTERN.findall(template)),
            'has_control': bool(self.IF_PATTERN.search(template) or self.FOR_PATTERN.search(template))
        }
    
    def _render_compiled(self, compiled: Any, context: Dict[str, Any]) -> str:
        """Render a compiled template."""
        # For now, just parse normally
        # In a real implementation, this would use the compiled representation
        return self._parse_internal(compiled['template'], context)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get parser metrics."""
        metrics = {}
        
        if self._cache is not None:
            total = self._cache_hits + self._cache_misses
            metrics['cache_hits'] = self._cache_hits
            metrics['cache_misses'] = self._cache_misses
            metrics['cache_hit_rate'] = self._cache_hits / total if total > 0 else 0.0
            metrics['cache_size'] = len(self._cache)
        
        return metrics
    
    def clear_cache(self) -> None:
        """Clear the parser cache."""
        if self._cache is not None:
            self._cache.clear()
            self._cache_hits = 0
            self._cache_misses = 0


# Convenience functions for different configurations
def create_parser(mode: str = "basic") -> UnifiedTemplateParser:
    """
    Create a parser with the specified mode.
    
    Args:
        mode: One of 'basic', 'performance', 'secure', 'enterprise'
        
    Returns:
        Configured UnifiedTemplateParser
    """
    configs = {
        'basic': ParserConfig.basic(),
        'performance': ParserConfig.performance(),
        'secure': ParserConfig.secure(),
        'enterprise': ParserConfig.enterprise()
    }
    
    config = configs.get(mode, ParserConfig.basic())
    return UnifiedTemplateParser(config)


# For backward compatibility
TemplateParser = UnifiedTemplateParser