"""
M004 Document Generator - Content processing engine.

Handles template rendering, variable substitution, and content transformation
using Jinja2 template engine with custom filters and functions.
"""

import logging
import re
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

import jinja2
from jinja2 import Environment, BaseLoader, StrictUndefined, select_autoescape

from ...common.errors import DevDocAIError
from ...common.logging import get_logger

logger = get_logger(__name__)


class ContentProcessor:
    """
    Processes template content with user inputs and generates final document content.
    
    Features:
    - Jinja2 template rendering
    - Custom filters for document formatting
    - Variable substitution with validation
    - Content sanitization and formatting
    """
    
    def __init__(self):
        """Initialize the content processor."""
        # Create Jinja2 environment for content processing
        self.jinja_env = Environment(
            loader=BaseLoader(),  # We'll pass content directly
            autoescape=select_autoescape([]),  # No auto-escaping for document content
            trim_blocks=True,
            lstrip_blocks=True,
            undefined=StrictUndefined  # Fail on undefined variables
        )
        
        # Register custom filters and functions
        self._register_custom_filters()
        self._register_global_functions()
        
        logger.debug("ContentProcessor initialized")
    
    def process_content(
        self, 
        template_content: str, 
        inputs: Dict[str, Any],
        required_variables: Optional[List[str]] = None
    ) -> str:
        """
        Process template content with provided inputs.
        
        Args:
            template_content: Raw template content with Jinja2 syntax
            inputs: Dictionary of input values for template variables
            required_variables: List of required variables for validation
            
        Returns:
            Processed content with variables substituted
            
        Raises:
            DevDocAIError: If template processing fails
        """
        try:
            # Validate required variables if specified
            if required_variables:
                self._validate_required_variables(inputs, required_variables)
            
            # Create template from content
            template = self.jinja_env.from_string(template_content)
            
            # Prepare context with default values
            context = self._prepare_context(inputs)
            
            # Render template
            rendered_content = template.render(**context)
            
            # Post-process content
            processed_content = self._post_process_content(rendered_content)
            
            logger.debug(f"Content processed successfully ({len(processed_content)} characters)")
            return processed_content
            
        except jinja2.UndefinedError as e:
            error_msg = f"Template variable not defined: {str(e)}"
            logger.error(error_msg)
            raise DevDocAIError(error_msg)
            
        except jinja2.TemplateError as e:
            error_msg = f"Template processing error: {str(e)}"
            logger.error(error_msg)
            raise DevDocAIError(error_msg)
            
        except Exception as e:
            error_msg = f"Content processing failed: {str(e)}"
            logger.error(error_msg)
            raise DevDocAIError(error_msg)
    
    def validate_template_syntax(self, template_content: str) -> List[str]:
        """
        Validate template syntax without rendering.
        
        Args:
            template_content: Template content to validate
            
        Returns:
            List of syntax error messages (empty if valid)
        """
        errors = []
        
        try:
            # Try to parse the template
            self.jinja_env.from_string(template_content)
            logger.debug("Template syntax validation passed")
            
        except jinja2.TemplateSyntaxError as e:
            error_msg = f"Syntax error at line {e.lineno}: {e.message}"
            errors.append(error_msg)
            logger.warning(error_msg)
            
        except Exception as e:
            error_msg = f"Template validation error: {str(e)}"
            errors.append(error_msg)
            logger.warning(error_msg)
        
        return errors
    
    def extract_variables(self, template_content: str) -> List[str]:
        """
        Extract all variables used in template content.
        
        Args:
            template_content: Template content to analyze
            
        Returns:
            List of variable names found in template
        """
        try:
            from jinja2 import meta
            
            # Parse the template AST to find variables
            ast = self.jinja_env.parse(template_content)
            variables = meta.find_undeclared_variables(ast)
            
            return list(variables)
            
        except Exception as e:
            logger.warning(f"Failed to extract variables: {e}")
            return []
    
    def _validate_required_variables(self, inputs: Dict[str, Any], required: List[str]) -> None:
        """Validate that all required variables are present in inputs."""
        missing_vars = []
        
        for var in required:
            if var not in inputs or inputs[var] is None:
                missing_vars.append(var)
        
        if missing_vars:
            raise DevDocAIError(f"Missing required variables: {', '.join(missing_vars)}")
    
    def _prepare_context(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare template context with inputs and default values."""
        context = inputs.copy()
        
        # Add default values
        context.setdefault('generated_date', datetime.now().strftime('%Y-%m-%d'))
        context.setdefault('generated_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        context.setdefault('version', '1.0')
        
        # Add utility objects
        context['now'] = datetime.now()
        
        return context
    
    def _post_process_content(self, content: str) -> str:
        """Post-process rendered content for cleanup and formatting."""
        # Remove excessive blank lines (more than 2 consecutive)
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        
        # Trim whitespace from lines while preserving intentional indentation
        lines = content.split('\n')
        processed_lines = []
        
        for line in lines:
            # Only trim trailing whitespace, preserve leading whitespace
            processed_lines.append(line.rstrip())
        
        # Join lines and ensure content ends with single newline
        content = '\n'.join(processed_lines)
        content = content.strip() + '\n' if content.strip() else ''
        
        return content
    
    def _register_custom_filters(self) -> None:
        """Register custom Jinja2 filters for document processing."""
        
        def markdown_link(text: str, url: str) -> str:
            """Create markdown link."""
            return f"[{text}]({url})"
        
        def markdown_code(code: str, language: str = "") -> str:
            """Create markdown code block."""
            return f"```{language}\n{code}\n```"
        
        def markdown_table(data: List[Dict[str, Any]], headers: Optional[List[str]] = None) -> str:
            """Convert list of dictionaries to markdown table."""
            if not data:
                return ""
            
            if not headers:
                headers = list(data[0].keys())
            
            # Create header row
            header_row = "| " + " | ".join(str(h) for h in headers) + " |"
            separator_row = "|" + "|".join([" --- " for _ in headers]) + "|"
            
            # Create data rows
            data_rows = []
            for row in data:
                row_values = [str(row.get(header, "")) for header in headers]
                data_rows.append("| " + " | ".join(row_values) + " |")
            
            return "\n".join([header_row, separator_row] + data_rows)
        
        def format_list(items: List[Any], list_type: str = "bullet") -> str:
            """Format list as markdown."""
            if not items:
                return ""
            
            if list_type == "numbered":
                return "\n".join(f"{i+1}. {item}" for i, item in enumerate(items))
            else:  # bullet list
                return "\n".join(f"- {item}" for item in items)
        
        def format_date(date_input: Union[str, datetime], format_str: str = "%Y-%m-%d") -> str:
            """Format date with custom format."""
            try:
                if isinstance(date_input, str):
                    # Try to parse ISO format
                    dt = datetime.fromisoformat(date_input.replace('Z', '+00:00'))
                elif isinstance(date_input, datetime):
                    dt = date_input
                else:
                    return str(date_input)
                
                return dt.strftime(format_str)
                
            except Exception:
                return str(date_input)
        
        def slugify(text: str) -> str:
            """Convert text to URL-friendly slug."""
            import re
            text = str(text).lower()
            text = re.sub(r'[^\w\s-]', '', text)
            text = re.sub(r'[-\s]+', '-', text)
            return text.strip('-')
        
        def truncate_words(text: str, length: int = 50) -> str:
            """Truncate text to specified number of words."""
            words = str(text).split()
            if len(words) <= length:
                return text
            return ' '.join(words[:length]) + '...'
        
        def capitalize_first(text: str) -> str:
            """Capitalize first letter of each sentence."""
            if not text:
                return text
            
            sentences = text.split('. ')
            capitalized = [s.capitalize() for s in sentences]
            return '. '.join(capitalized)
        
        # Register all filters
        filters = {
            'markdown_link': markdown_link,
            'markdown_code': markdown_code,
            'markdown_table': markdown_table,
            'format_list': format_list,
            'format_date': format_date,
            'slugify': slugify,
            'truncate_words': truncate_words,
            'capitalize_first': capitalize_first
        }
        
        for name, func in filters.items():
            self.jinja_env.filters[name] = func
        
        logger.debug(f"Registered {len(filters)} custom filters")
    
    def _register_global_functions(self) -> None:
        """Register global functions available in templates."""
        
        def range_function(*args):
            """Wrapper for Python's range function."""
            return range(*args)
        
        def enumerate_function(iterable, start=0):
            """Wrapper for Python's enumerate function."""
            return enumerate(iterable, start)
        
        def len_function(obj):
            """Wrapper for Python's len function."""
            return len(obj)
        
        def max_function(*args, **kwargs):
            """Wrapper for Python's max function."""
            return max(*args, **kwargs)
        
        def min_function(*args, **kwargs):
            """Wrapper for Python's min function."""
            return min(*args, **kwargs)
        
        def sum_function(iterable, start=0):
            """Wrapper for Python's sum function."""
            return sum(iterable, start)
        
        # Register global functions
        globals_dict = {
            'range': range_function,
            'enumerate': enumerate_function,
            'len': len_function,
            'max': max_function,
            'min': min_function,
            'sum': sum_function
        }
        
        for name, func in globals_dict.items():
            self.jinja_env.globals[name] = func
        
        logger.debug(f"Registered {len(globals_dict)} global functions")