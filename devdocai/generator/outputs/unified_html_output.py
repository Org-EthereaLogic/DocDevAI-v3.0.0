"""
M004 Document Generator - Unified HTML Output Generator (Refactored).

Combines basic and secure HTML output functionality into a single,
configurable component with optional security features.

Pass 4 Refactoring: Consolidates html.py and secure_html_output.py
to eliminate duplication while preserving all functionality.
"""

import os
import re
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
import html
import urllib.parse

try:
    import bleach
    from markupsafe import Markup
    BLEACH_AVAILABLE = True
except ImportError:
    BLEACH_AVAILABLE = False

try:
    from markdown import Markdown
    from markdown.extensions import Extension
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False

from ...common.logging import get_logger
from ...common.errors import DevDocAIError
from ...common.security import get_audit_logger
from ...common.performance import LRUCache

logger = get_logger(__name__)


class SecurityLevel(Enum):
    """Security levels for HTML output."""
    NONE = "none"  # No sanitization (fastest)
    BASIC = "basic"  # Basic HTML escaping
    STANDARD = "standard"  # Standard sanitization with bleach
    STRICT = "strict"  # Maximum security with CSP and strict sanitization


class HTMLOutputError(DevDocAIError):
    """Exception for HTML output errors."""
    pass


class UnifiedHTMLOutput:
    """
    Unified HTML output generator with configurable security levels.
    
    Features:
    - Backward compatible with both basic and secure output generators
    - Configurable security levels (none, basic, standard, strict)
    - Performance optimized with caching
    - Optional XSS protection and CSP headers
    - Markdown to HTML conversion with security
    """
    
    # Default allowed tags for standard security
    DEFAULT_ALLOWED_TAGS = [
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'p', 'br', 'hr',
        'strong', 'b', 'em', 'i', 'u',
        'ul', 'ol', 'li',
        'a', 'img',
        'pre', 'code', 'blockquote',
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'div', 'span', 'section', 'article', 'aside',
        'header', 'footer', 'nav'
    ]
    
    # Default allowed attributes
    DEFAULT_ALLOWED_ATTRIBUTES = {
        'a': ['href', 'title', 'target', 'rel'],
        'img': ['src', 'alt', 'title', 'width', 'height'],
        'code': ['class'],
        'pre': ['class'],
        'div': ['class', 'id'],
        'span': ['class', 'id'],
        'th': ['colspan', 'rowspan'],
        'td': ['colspan', 'rowspan']
    }
    
    # Strict mode allowed tags (minimal set)
    STRICT_ALLOWED_TAGS = [
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'p', 'br', 'hr',
        'strong', 'em',
        'ul', 'ol', 'li',
        'pre', 'code', 'blockquote'
    ]
    
    # Strict mode attributes (very limited)
    STRICT_ALLOWED_ATTRIBUTES = {
        'code': ['class'],
        'pre': ['class']
    }
    
    # Default CSP policy for strict mode
    DEFAULT_CSP_POLICY = {
        'default-src': ["'self'"],
        'script-src': ["'none'"],
        'style-src': ["'self'", "'unsafe-inline'"],
        'img-src': ["'self'", 'data:', 'https:'],
        'font-src': ["'self'"],
        'connect-src': ["'none'"],
        'media-src': ["'none'"],
        'object-src': ["'none'"],
        'frame-src': ["'none'"],
        'base-uri': ["'self'"],
        'form-action': ["'self'"],
        'frame-ancestors': ["'none'"]
    }
    
    def __init__(
        self,
        security_level: SecurityLevel = SecurityLevel.STANDARD,
        output_dir: Optional[Path] = None,
        enable_caching: bool = True,
        cache_size: int = 50,
        enable_audit: bool = None,
        custom_css: Optional[str] = None,
        custom_js: Optional[str] = None,
        allowed_tags: Optional[List[str]] = None,
        allowed_attributes: Optional[Dict[str, List[str]]] = None,
        csp_policy: Optional[Dict[str, List[str]]] = None,
        **kwargs
    ):
        """
        Initialize unified HTML output generator.
        
        Args:
            security_level: Security level to apply
            output_dir: Directory for output files
            enable_caching: Enable output caching
            cache_size: Maximum cache size
            enable_audit: Enable audit logging
            custom_css: Custom CSS styles
            custom_js: Custom JavaScript (only in NONE/BASIC modes)
            allowed_tags: Custom allowed HTML tags
            allowed_attributes: Custom allowed HTML attributes
            csp_policy: Custom Content Security Policy
            **kwargs: Additional configuration options
        """
        self.security_level = security_level
        self.output_dir = output_dir or Path.cwd() / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Auto-enable audit for higher security levels
        if enable_audit is None:
            self.enable_audit = security_level in (SecurityLevel.STANDARD, SecurityLevel.STRICT)
        else:
            self.enable_audit = enable_audit
        
        # Initialize caching
        self.enable_caching = enable_caching
        if enable_caching:
            self._cache = LRUCache(maxsize=cache_size)
        
        # Initialize audit logger if needed
        if self.enable_audit:
            self._audit_logger = get_audit_logger()
        
        # Set allowed tags and attributes based on security level
        if security_level == SecurityLevel.STRICT:
            self.allowed_tags = allowed_tags or self.STRICT_ALLOWED_TAGS
            self.allowed_attributes = allowed_attributes or self.STRICT_ALLOWED_ATTRIBUTES
            self.csp_policy = csp_policy or self.DEFAULT_CSP_POLICY
        else:
            self.allowed_tags = allowed_tags or self.DEFAULT_ALLOWED_TAGS
            self.allowed_attributes = allowed_attributes or self.DEFAULT_ALLOWED_ATTRIBUTES
            self.csp_policy = csp_policy
        
        # Handle custom CSS/JS based on security level
        self.custom_css = custom_css
        if security_level in (SecurityLevel.NONE, SecurityLevel.BASIC):
            self.custom_js = custom_js
        else:
            if custom_js:
                logger.warning(f"Custom JavaScript disabled in {security_level.value} mode")
            self.custom_js = None
        
        # Initialize Markdown converter if available
        if MARKDOWN_AVAILABLE:
            self._init_markdown_converter()
        else:
            self.markdown = None
        
        logger.info(
            f"Initialized UnifiedHTMLOutput with security_level={security_level.value}, "
            f"caching={enable_caching}, audit={self.enable_audit}"
        )
    
    def _init_markdown_converter(self):
        """Initialize Markdown converter with security considerations."""
        extensions = ['fenced_code', 'tables', 'toc', 'nl2br']
        
        if self.security_level in (SecurityLevel.NONE, SecurityLevel.BASIC):
            # Allow more extensions in low security modes
            extensions.extend(['attr_list', 'def_list', 'footnotes'])
        
        self.markdown = Markdown(extensions=extensions)
    
    def generate(
        self,
        content: str,
        title: str = "Document",
        metadata: Optional[Dict[str, Any]] = None,
        format_type: str = "markdown",
        output_file: Optional[str] = None,
        template: Optional[str] = None,
        validate: Optional[bool] = None
    ) -> str:
        """
        Generate HTML output from content.
        
        Args:
            content: Input content (markdown or HTML)
            title: Document title
            metadata: Document metadata
            format_type: Input format type (markdown/html)
            output_file: Optional output file name
            template: Optional HTML template
            validate: Override validation setting
            
        Returns:
            Generated HTML string
        """
        if validate is None:
            validate = self.security_level != SecurityLevel.NONE
        
        # Check cache if enabled
        cache_key = None
        if self.enable_caching:
            cache_key = self._generate_cache_key(content, title, metadata)
            if cache_key in self._cache:
                logger.debug(f"Using cached output for {title}")
                return self._cache[cache_key]
        
        try:
            # Convert content if needed
            if format_type == "markdown":
                html_content = self._convert_markdown(content)
            else:
                html_content = content
            
            # Sanitize based on security level
            if self.security_level != SecurityLevel.NONE:
                html_content = self._sanitize_html(html_content)
            
            # Apply template
            if template:
                final_html = self._apply_template(html_content, title, metadata, template)
            else:
                final_html = self._generate_full_html(html_content, title, metadata)
            
            # Validate if required
            if validate:
                self._validate_output(final_html)
            
            # Cache result
            if self.enable_caching and cache_key:
                self._cache[cache_key] = final_html
            
            # Save to file if requested
            if output_file:
                self._save_output(final_html, output_file)
            
            # Audit log if enabled
            if self.enable_audit:
                self._audit_logger.log_event(
                    "html_generated",
                    title=title,
                    security_level=self.security_level.value,
                    output_file=output_file
                )
            
            return final_html
            
        except Exception as e:
            logger.error(f"Error generating HTML output: {e}")
            raise HTMLOutputError(f"Failed to generate HTML: {e}")
    
    def _generate_cache_key(self, content: str, title: str, metadata: Optional[Dict]) -> str:
        """Generate cache key for content."""
        key_parts = [content, title, str(metadata), self.security_level.value]
        key_string = "|".join(str(p) for p in key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _convert_markdown(self, content: str) -> str:
        """Convert markdown to HTML."""
        if not self.markdown:
            raise HTMLOutputError("Markdown library not available")
        
        try:
            return self.markdown.convert(content)
        except Exception as e:
            logger.error(f"Markdown conversion error: {e}")
            raise HTMLOutputError(f"Failed to convert markdown: {e}")
    
    def _sanitize_html(self, html_content: str) -> str:
        """Sanitize HTML based on security level."""
        if self.security_level == SecurityLevel.BASIC:
            # Basic HTML escaping
            return html.escape(html_content)
        
        elif self.security_level in (SecurityLevel.STANDARD, SecurityLevel.STRICT):
            if not BLEACH_AVAILABLE:
                # Fallback to basic escaping if bleach not available
                logger.warning("Bleach not available, falling back to basic sanitization")
                return html.escape(html_content)
            
            # Use bleach for sanitization
            return bleach.clean(
                html_content,
                tags=self.allowed_tags,
                attributes=self.allowed_attributes,
                strip=True,
                strip_comments=True
            )
        
        return html_content
    
    def _generate_full_html(
        self,
        content: str,
        title: str,
        metadata: Optional[Dict[str, Any]]
    ) -> str:
        """Generate complete HTML document."""
        # Build CSS
        css_parts = [self._get_default_css()]
        if self.custom_css:
            css_parts.append(self.custom_css)
        css_content = "\n".join(css_parts)
        
        # Build meta tags
        meta_tags = self._generate_meta_tags(metadata)
        
        # Build CSP header if needed
        csp_header = ""
        if self.security_level == SecurityLevel.STRICT and self.csp_policy:
            csp_header = self._generate_csp_meta_tag()
        
        # Build JavaScript (if allowed)
        js_content = ""
        if self.custom_js and self.security_level in (SecurityLevel.NONE, SecurityLevel.BASIC):
            js_content = f"<script>{self.custom_js}</script>"
        
        # Generate HTML
        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    {csp_header}
    {meta_tags}
    <title>{html.escape(title)}</title>
    <style>
    {css_content}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{html.escape(title)}</h1>
            {self._generate_metadata_section(metadata)}
        </header>
        <main>
            {content}
        </main>
        <footer>
            <p>Generated by DevDocAI v3.0.0 on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </footer>
    </div>
    {js_content}
</body>
</html>"""
        
        return html_template
    
    def _get_default_css(self) -> str:
        """Get default CSS styles."""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background-color: white;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        
        header {
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        
        h1 {
            color: #2c3e50;
            margin-bottom: 10px;
        }
        
        h2, h3, h4, h5, h6 {
            color: #34495e;
            margin-top: 25px;
            margin-bottom: 15px;
        }
        
        p {
            margin-bottom: 15px;
        }
        
        code {
            background-color: #f4f4f4;
            padding: 2px 5px;
            border-radius: 3px;
            font-family: 'Courier New', Courier, monospace;
        }
        
        pre {
            background-color: #f4f4f4;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            margin-bottom: 20px;
        }
        
        pre code {
            background-color: transparent;
            padding: 0;
        }
        
        ul, ol {
            margin-left: 30px;
            margin-bottom: 15px;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        
        th, td {
            border: 1px solid #ddd;
            padding: 10px;
            text-align: left;
        }
        
        th {
            background-color: #f4f4f4;
            font-weight: bold;
        }
        
        footer {
            margin-top: 50px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }
        
        .metadata {
            background-color: #f9f9f9;
            padding: 10px;
            border-radius: 5px;
            margin-top: 10px;
            font-size: 0.9em;
        }
        
        .metadata dl {
            display: grid;
            grid-template-columns: auto 1fr;
            gap: 5px 15px;
        }
        
        .metadata dt {
            font-weight: bold;
            color: #666;
        }
        
        .metadata dd {
            margin: 0;
        }
        """
    
    def _generate_meta_tags(self, metadata: Optional[Dict[str, Any]]) -> str:
        """Generate HTML meta tags from metadata."""
        if not metadata:
            return ""
        
        meta_tags = []
        
        # Standard meta tags
        if 'description' in metadata:
            meta_tags.append(f'<meta name="description" content="{html.escape(str(metadata["description"]))}">')
        if 'author' in metadata:
            meta_tags.append(f'<meta name="author" content="{html.escape(str(metadata["author"]))}">')
        if 'keywords' in metadata:
            keywords = metadata['keywords']
            if isinstance(keywords, list):
                keywords = ', '.join(keywords)
            meta_tags.append(f'<meta name="keywords" content="{html.escape(keywords)}">')
        
        return "\n    ".join(meta_tags)
    
    def _generate_csp_meta_tag(self) -> str:
        """Generate Content Security Policy meta tag."""
        if not self.csp_policy:
            return ""
        
        policy_parts = []
        for directive, values in self.csp_policy.items():
            value_str = " ".join(values)
            policy_parts.append(f"{directive} {value_str}")
        
        policy = "; ".join(policy_parts)
        return f'<meta http-equiv="Content-Security-Policy" content="{policy}">'
    
    def _generate_metadata_section(self, metadata: Optional[Dict[str, Any]]) -> str:
        """Generate metadata display section."""
        if not metadata:
            return ""
        
        items = []
        for key, value in metadata.items():
            if key not in ['description', 'content']:  # Skip large fields
                items.append(f"<dt>{html.escape(key.replace('_', ' ').title())}:</dt>")
                items.append(f"<dd>{html.escape(str(value))}</dd>")
        
        if not items:
            return ""
        
        return f"""
        <div class="metadata">
            <dl>
                {''.join(items)}
            </dl>
        </div>
        """
    
    def _apply_template(
        self,
        content: str,
        title: str,
        metadata: Optional[Dict[str, Any]],
        template: str
    ) -> str:
        """Apply a custom HTML template."""
        # Simple template variable replacement
        replacements = {
            '{{title}}': html.escape(title),
            '{{content}}': content,
            '{{date}}': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            '{{metadata}}': self._generate_metadata_section(metadata)
        }
        
        result = template
        for key, value in replacements.items():
            result = result.replace(key, value)
        
        return result
    
    def _validate_output(self, html_content: str):
        """Validate generated HTML output."""
        # Check for common issues
        if not html_content:
            raise HTMLOutputError("Empty HTML output")
        
        if self.security_level == SecurityLevel.STRICT:
            # Check for script tags
            if '<script' in html_content.lower():
                raise HTMLOutputError("Script tags not allowed in strict mode")
            
            # Check for inline event handlers
            event_pattern = r'on\w+\s*='
            if re.search(event_pattern, html_content, re.IGNORECASE):
                raise HTMLOutputError("Inline event handlers not allowed in strict mode")
    
    def _save_output(self, html_content: str, filename: str):
        """Save HTML output to file."""
        output_path = self.output_dir / filename
        if not output_path.suffix:
            output_path = output_path.with_suffix('.html')
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info(f"HTML output saved to {output_path}")
        except Exception as e:
            logger.error(f"Error saving HTML output: {e}")
            raise HTMLOutputError(f"Failed to save output: {e}")
    
    def clear_cache(self):
        """Clear output cache."""
        if self.enable_caching:
            self._cache.clear()
            logger.info("HTML output cache cleared")
    
    # Backward compatibility methods
    
    def render(self, content: str, title: str = "Document", **kwargs) -> str:
        """Backward compatible render method."""
        return self.generate(content, title, **kwargs)
    
    def save(self, content: str, filename: str, **kwargs):
        """Backward compatible save method."""
        html_content = self.generate(content, **kwargs)
        self._save_output(html_content, filename)


# Backward compatibility aliases
HTMLOutput = UnifiedHTMLOutput  # Alias for basic output compatibility
SecureHTMLOutput = UnifiedHTMLOutput  # Alias for secure output compatibility


def create_html_output(
    security_level: Union[str, SecurityLevel] = "standard",
    **kwargs
) -> UnifiedHTMLOutput:
    """
    Factory function to create an HTML output generator with specified security level.
    
    Args:
        security_level: Security level (none/basic/standard/strict) or SecurityLevel enum
        **kwargs: Additional configuration options
        
    Returns:
        Configured UnifiedHTMLOutput instance
    """
    if isinstance(security_level, str):
        security_level = SecurityLevel(security_level.lower())
    
    return UnifiedHTMLOutput(security_level=security_level, **kwargs)