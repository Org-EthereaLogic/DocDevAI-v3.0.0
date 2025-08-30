"""
Secure Template Parser for M006 Template Registry.

This module provides a security-hardened template parser that prevents
SSTI, XSS, and other injection attacks while maintaining functionality.
"""

import re
import html
from typing import Dict, List, Any, Optional, Tuple, Set
from pathlib import Path
import logging
import hashlib
from functools import lru_cache

from .models import Template, TemplateRenderContext, TemplateVariable
from .template_security import TemplateSecurity, TemplatePermissionManager
from .template_sandbox import TemplateSandbox, SafeTemplateContext
from .exceptions import (
    TemplateParseError,
    TemplateRenderError,
    TemplateIncludeError,
    TemplateVariableError,
    TemplateSSTIError,
    TemplateSecurityError
)

logger = logging.getLogger(__name__)


class SecureTemplateParser:
    """
    Security-hardened template parser with SSTI prevention and sandboxed execution.
    
    Features:
    - SSTI prevention through sandboxed evaluation
    - XSS protection via output sanitization
    - Path traversal prevention for includes
    - Resource limits and timeout protection
    - PII detection and masking
    - Comprehensive audit logging
    """
    
    # Secure regex patterns - more restrictive than original
    VARIABLE_PATTERN = re.compile(r'\{\{([a-zA-Z_][a-zA-Z0-9_\.]{0,63})\}\}')
    SECTION_PATTERN = re.compile(r'<!-- SECTION: ([a-zA-Z_][a-zA-Z0-9_]{0,31}) -->(.*?)<!-- END SECTION: \1 -->', re.DOTALL)
    CONDITIONAL_PATTERN = re.compile(r'<!-- IF ([^-]{1,100}) -->(.*?)<!-- END IF -->', re.DOTALL)
    LOOP_PATTERN = re.compile(r'<!-- FOR ([a-zA-Z_][a-zA-Z0-9_]{0,31}) IN ([a-zA-Z_][a-zA-Z0-9_]{0,31}) -->(.*?)<!-- END FOR -->', re.DOTALL)
    INCLUDE_PATTERN = re.compile(r'<!-- INCLUDE ([a-zA-Z0-9_\-/\.]{1,255}) -->')
    COMMENT_PATTERN = re.compile(r'<!-- COMMENT: [^-]+ -->')
    
    # Security configuration
    MAX_INCLUDE_DEPTH = 3
    MAX_LOOP_ITERATIONS = 100
    MAX_TEMPLATE_SIZE = 500 * 1024  # 500KB
    MAX_VARIABLE_NAME_LENGTH = 64
    MAX_RENDERED_SIZE = 1024 * 1024  # 1MB
    
    def __init__(self,
                 security: Optional[TemplateSecurity] = None,
                 sandbox: Optional[TemplateSandbox] = None,
                 permission_manager: Optional[TemplatePermissionManager] = None,
                 template_base_dir: Optional[Path] = None):
        """
        Initialize secure parser.
        
        Args:
            security: Security manager instance
            sandbox: Sandbox instance
            permission_manager: Permission manager
            template_base_dir: Base directory for template includes
        """
        self.security = security or TemplateSecurity()
        self.sandbox = sandbox or TemplateSandbox()
        self.permission_manager = permission_manager or TemplatePermissionManager()
        self.template_base_dir = template_base_dir or Path.cwd() / "templates"
        
        # Caches for performance
        self._include_cache: Dict[str, str] = {}
        self._validation_cache: Dict[str, bool] = {}
        
        # Security state
        self._current_user_id: Optional[str] = None
        self._render_count = 0
        
    def parse(self, template: Template, context: TemplateRenderContext,
             user_id: Optional[str] = None) -> str:
        """
        Parse and render template with security checks.
        
        Args:
            template: Template to parse
            context: Rendering context
            user_id: User ID for permission checks
            
        Returns:
            Rendered and sanitized template content
            
        Raises:
            TemplateSecurityError: If security violation detected
            TemplateRenderError: If rendering fails
        """
        self._current_user_id = user_id or "anonymous"
        
        try:
            # Check permissions
            if user_id and not self.permission_manager.has_permission(
                user_id, template.metadata.id, 'execute'
            ):
                raise TemplateSecurityError(f"User {user_id} lacks execute permission")
            
            # Check rate limits
            self.security.check_rate_limit(self._current_user_id, 'render')
            
            # Validate template content
            is_valid, issues = self._validate_template_security(template)
            if not is_valid:
                self.security.audit_log(
                    'template_validation_failed',
                    self._current_user_id,
                    template.metadata.id,
                    {'issues': issues}
                )
                raise TemplateSecurityError(f"Template validation failed: {issues}")
            
            # Sanitize context variables
            safe_context = self._sanitize_context(context)
            
            # Parse template with security
            content = template.content
            
            # Check template size
            if len(content) > self.MAX_TEMPLATE_SIZE:
                raise TemplateSecurityError(
                    f"Template too large ({len(content)} > {self.MAX_TEMPLATE_SIZE})"
                )
            
            # Process template in sandboxed environment
            with self.sandbox.sandboxed_context():
                content = self._process_comments(content)
                content = self._process_includes_secure(content, safe_context, depth=0)
                content = self._process_loops_secure(content, safe_context)
                content = self._process_conditionals_secure(content, safe_context)
                content = self._process_sections(content, safe_context)
                content = self._process_variables_secure(content, safe_context, template.variables)
            
            # Sanitize output to prevent XSS
            content = self.security.sanitize_html_output(content)
            
            # Check rendered size
            if len(content) > self.MAX_RENDERED_SIZE:
                raise TemplateRenderError(
                    f"Rendered content too large ({len(content)} > {self.MAX_RENDERED_SIZE})"
                )
            
            # Mask PII if configured
            if template.metadata.mask_pii:
                content = self.security.mask_pii(content)
            
            # Log successful render
            self.security.audit_log(
                'template_rendered',
                self._current_user_id,
                template.metadata.id,
                {'render_count': self._render_count}
            )
            
            self._render_count += 1
            return content.strip()
            
        except Exception as e:
            # Log error
            self.security.audit_log(
                'template_render_error',
                self._current_user_id,
                template.metadata.id if template else 'unknown',
                {'error': str(e)}
            )
            
            if isinstance(e, (TemplateSecurityError, TemplateRenderError)):
                raise
            raise TemplateRenderError(f"Secure parsing failed: {e}")
        
        finally:
            self._current_user_id = None
    
    def _validate_template_security(self, template: Template) -> Tuple[bool, List[str]]:
        """Validate template for security issues."""
        # Check cache
        cache_key = hashlib.sha256(template.content.encode()).hexdigest()
        if cache_key in self._validation_cache:
            return self._validation_cache[cache_key], []
        
        # Perform validation
        is_valid, issues = self.security.validate_template_content(
            template.content,
            template.metadata.id
        )
        
        # Cache result
        self._validation_cache[cache_key] = is_valid
        
        return is_valid, issues
    
    def _sanitize_context(self, context: TemplateRenderContext) -> TemplateRenderContext:
        """Sanitize all context variables."""
        safe_variables = {}
        
        for key, value in context.variables.items():
            # Validate variable name
            if not self._is_safe_variable_name(key):
                logger.warning(f"Skipping unsafe variable name: {key}")
                continue
            
            # Sanitize value
            safe_value = self.security.sanitize_variable_value(value, key)
            safe_variables[key] = safe_value
        
        # Create safe context
        return TemplateRenderContext(
            variables=safe_variables,
            sections=context.sections,
            loops=context.loops
        )
    
    def _is_safe_variable_name(self, name: str) -> bool:
        """Check if variable name is safe."""
        # Check length
        if len(name) > self.MAX_VARIABLE_NAME_LENGTH:
            return False
        
        # Check pattern (alphanumeric and underscore only)
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
            return False
        
        # Check for dangerous names
        dangerous_names = {
            '__class__', '__import__', '__builtins__', '__globals__',
            'exec', 'eval', 'compile', 'open', 'input'
        }
        if name in dangerous_names:
            return False
        
        return True
    
    def _process_comments(self, content: str) -> str:
        """Remove comments from content."""
        return self.COMMENT_PATTERN.sub('', content)
    
    def _process_includes_secure(self, content: str, context: TemplateRenderContext, 
                                 depth: int) -> str:
        """Process includes with security checks."""
        if depth >= self.MAX_INCLUDE_DEPTH:
            raise TemplateIncludeError(
                "max_depth",
                f"Maximum include depth ({self.MAX_INCLUDE_DEPTH}) exceeded"
            )
        
        def replace_include(match):
            include_path = match.group(1).strip()
            
            # Validate path security
            try:
                self.security.validate_template_path(include_path, self.template_base_dir)
            except Exception as e:
                logger.error(f"Include path validation failed: {e}")
                return f"<!-- Include blocked: security violation -->"
            
            # Check permissions for included template
            if self._current_user_id and not self.permission_manager.has_permission(
                self._current_user_id, include_path, 'read'
            ):
                return f"<!-- Include blocked: permission denied -->"
            
            # Load and cache include
            if include_path in self._include_cache:
                included_content = self._include_cache[include_path]
            else:
                included_content = self._load_include_secure(include_path)
                if included_content:
                    self._include_cache[include_path] = included_content
            
            if not included_content:
                return f"<!-- Include not found: {html.escape(include_path)} -->"
            
            # Recursively process includes
            return self._process_includes_secure(included_content, context, depth + 1)
        
        return self.INCLUDE_PATTERN.sub(replace_include, content)
    
    def _load_include_secure(self, include_path: str) -> Optional[str]:
        """Securely load included template."""
        try:
            # Construct safe path
            full_path = (self.template_base_dir / include_path).resolve()
            
            # Verify path is within base directory
            if not str(full_path).startswith(str(self.template_base_dir.resolve())):
                logger.error(f"Path traversal attempt: {include_path}")
                return None
            
            # Check file exists
            if not full_path.exists() or not full_path.is_file():
                return None
            
            # Read file with size limit
            content = full_path.read_text(encoding='utf-8')
            
            if len(content) > self.MAX_TEMPLATE_SIZE:
                logger.error(f"Included template too large: {include_path}")
                return None
            
            # Validate included content
            is_valid, issues = self.security.validate_template_content(content)
            if not is_valid:
                logger.error(f"Included template failed validation: {issues}")
                return None
            
            return content
            
        except Exception as e:
            logger.error(f"Failed to load include {include_path}: {e}")
            return None
    
    def _process_loops_secure(self, content: str, context: TemplateRenderContext) -> str:
        """Process loops with security limits."""
        def replace_loop(match):
            item_var = match.group(1).strip()
            collection_var = match.group(2).strip()
            loop_content = match.group(3)
            
            # Validate variable names
            if not self._is_safe_variable_name(item_var):
                return "<!-- Loop blocked: unsafe variable name -->"
            
            if not self._is_safe_variable_name(collection_var):
                return "<!-- Loop blocked: unsafe collection name -->"
            
            if collection_var not in context.loops:
                return ""
            
            collection = context.loops[collection_var]
            if not isinstance(collection, (list, tuple)):
                return "<!-- Loop blocked: collection not iterable -->"
            
            # Limit iterations
            if len(collection) > self.MAX_LOOP_ITERATIONS:
                logger.warning(
                    f"Loop truncated from {len(collection)} to {self.MAX_LOOP_ITERATIONS} items"
                )
                collection = collection[:self.MAX_LOOP_ITERATIONS]
            
            results = []
            for item in collection:
                # Sanitize loop item
                safe_item = self.security.sanitize_variable_value(item, item_var)
                
                # Create temporary context
                loop_context = TemplateRenderContext(
                    variables={**context.variables, item_var: safe_item},
                    sections=context.sections,
                    loops=context.loops
                )
                
                # Process loop content
                processed = self._process_variables_secure(
                    loop_content, loop_context, []
                )
                results.append(processed)
            
            return "\n".join(results)
        
        return self.LOOP_PATTERN.sub(replace_loop, content)
    
    def _process_conditionals_secure(self, content: str, 
                                    context: TemplateRenderContext) -> str:
        """Process conditionals with secure evaluation."""
        def replace_conditional(match):
            condition = match.group(1).strip()
            conditional_content = match.group(2)
            
            # Evaluate condition securely
            try:
                if self._evaluate_condition_secure(condition, context):
                    return conditional_content
            except Exception as e:
                logger.warning(f"Conditional evaluation failed: {e}")
            
            return ""
        
        return self.CONDITIONAL_PATTERN.sub(replace_conditional, content)
    
    def _evaluate_condition_secure(self, condition: str, 
                                  context: TemplateRenderContext) -> bool:
        """Securely evaluate conditional expression."""
        try:
            # Simple safe evaluation - no code execution
            
            # Check for NOT operator
            if condition.startswith("NOT "):
                var_name = condition[4:].strip()
                if not self._is_safe_variable_name(var_name):
                    return False
                return var_name not in context.variables or not context.variables[var_name]
            
            # Check for equality (safe string comparison only)
            if "==" in condition:
                parts = condition.split("==", 1)
                if len(parts) != 2:
                    return False
                
                left = parts[0].strip()
                right = parts[1].strip()
                
                # Get values safely
                left_val = context.variables.get(left, left) if self._is_safe_variable_name(left) else left
                right_val = context.variables.get(right, right) if self._is_safe_variable_name(right) else right
                
                # Remove quotes if present
                if right_val.startswith('"') and right_val.endswith('"'):
                    right_val = right_val[1:-1]
                
                return str(left_val) == str(right_val)
            
            # Simple variable check
            if self._is_safe_variable_name(condition):
                return bool(context.variables.get(condition))
            
            return False
            
        except Exception as e:
            logger.warning(f"Condition evaluation error: {e}")
            return False
    
    def _process_sections(self, content: str, context: TemplateRenderContext) -> str:
        """Process sections."""
        def replace_section(match):
            section_name = match.group(1)
            section_content = match.group(2)
            
            # Validate section name
            if not self._is_safe_variable_name(section_name):
                return "<!-- Section blocked: unsafe name -->"
            
            # Check if section should be included
            if section_name in context.sections:
                if context.sections[section_name]:
                    return section_content
                return ""
            
            # Default to including section
            return section_content
        
        return self.SECTION_PATTERN.sub(replace_section, content)
    
    def _process_variables_secure(self, content: str, context: TemplateRenderContext,
                                 variables: List[TemplateVariable]) -> str:
        """Process variables with security checks."""
        missing_vars = []
        
        def replace_variable(match):
            var_expr = match.group(1).strip()
            
            # Validate variable expression
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_\.]*$', var_expr):
                return f"{{{{{html.escape(var_expr)}}}}}"
            
            # Handle nested property access safely
            parts = var_expr.split('.')
            
            # Validate each part
            for part in parts:
                if not self._is_safe_variable_name(part):
                    return f"{{{{{html.escape(var_expr)}}}}}"
            
            # Navigate safely through nested structure
            value = context.variables
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    # Check for default value
                    for var in variables:
                        if var.name == var_expr and var.default is not None:
                            return html.escape(str(var.default))
                    
                    # Track missing required variables
                    for var in variables:
                        if var.name == var_expr and var.required:
                            missing_vars.append(var_expr)
                    
                    return f"{{{{{html.escape(var_expr)}}}}}"
            
            # Sanitize and return value
            return html.escape(str(value))
        
        result = self.VARIABLE_PATTERN.sub(replace_variable, content)
        
        if missing_vars:
            raise TemplateRenderError(f"Missing required variables: {missing_vars}")
        
        return result
    
    @lru_cache(maxsize=128)
    def extract_variables(self, content: str) -> List[str]:
        """Extract variable names from template content."""
        variables = set()
        
        # Only extract from safe patterns
        for match in self.VARIABLE_PATTERN.finditer(content):
            var_expr = match.group(1).strip()
            base_var = var_expr.split('.')[0]
            if self._is_safe_variable_name(base_var):
                variables.add(base_var)
        
        return sorted(list(variables))
    
    def validate_syntax(self, content: str) -> Tuple[bool, List[str]]:
        """Validate template syntax with security checks."""
        errors = []
        
        # Check for balanced brackets
        open_count = content.count("{{")
        close_count = content.count("}}")
        if open_count != close_count:
            errors.append(f"Unbalanced variable brackets: {open_count} open, {close_count} close")
        
        # Security validation
        is_valid, security_issues = self.security.validate_template_content(content)
        if not is_valid:
            errors.extend(security_issues)
        
        # Check sections
        section_starts = re.findall(r'<!-- SECTION: ([a-zA-Z_][a-zA-Z0-9_]*) -->', content)
        section_ends = re.findall(r'<!-- END SECTION: ([a-zA-Z_][a-zA-Z0-9_]*) -->', content)
        
        for section in section_starts:
            if section not in section_ends:
                errors.append(f"Unclosed section: {section}")
        
        for section in section_ends:
            if section not in section_starts:
                errors.append(f"Section end without start: {section}")
        
        return len(errors) == 0, errors