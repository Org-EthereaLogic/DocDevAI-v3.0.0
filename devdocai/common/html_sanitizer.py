"""
Centralized HTML sanitization utility for DevDocAI.

This module provides secure HTML sanitization using proper HTML parsing
instead of regex-based filtering, which is vulnerable to bypasses.
"""

import html
import logging
from typing import Set, Dict, Optional, List
from urllib.parse import urlparse

try:
    import bleach
    from bleach.css_sanitizer import CSSSanitizer
    BLEACH_AVAILABLE = True
except ImportError:
    BLEACH_AVAILABLE = False
    
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

logger = logging.getLogger(__name__)


class HtmlSanitizer:
    """
    Secure HTML sanitizer that uses proper HTML parsing libraries.
    
    Falls back through multiple levels of sanitization:
    1. Bleach (if available) - Most secure
    2. BeautifulSoup (if available) - Good security
    3. HTML escaping - Safe but removes all formatting
    
    Never uses regex for HTML parsing as it's fundamentally insecure.
    """
    
    # Conservative allowlist of safe HTML tags
    DEFAULT_ALLOWED_TAGS = {
        'p', 'br', 'strong', 'em', 'b', 'i', 'u', 
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'blockquote', 'pre', 'code',
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'div', 'span', 'a', 'img'
    }
    
    # Safe attributes for allowed tags
    DEFAULT_ALLOWED_ATTRIBUTES = {
        'a': ['href', 'title'],
        'img': ['src', 'alt', 'title', 'width', 'height'],
        'blockquote': ['cite'],
        '*': ['class', 'id']  # Allow class and id on all tags
    }
    
    # Safe URL schemes
    ALLOWED_PROTOCOLS = ['http', 'https', 'mailto', 'ftp']
    
    def __init__(
        self,
        allowed_tags: Optional[Set[str]] = None,
        allowed_attributes: Optional[Dict[str, List[str]]] = None,
        allowed_protocols: Optional[List[str]] = None,
        strip_comments: bool = True,
        strip_scripts: bool = True
    ):
        """
        Initialize the HTML sanitizer.
        
        Args:
            allowed_tags: Set of allowed HTML tags (uses defaults if None)
            allowed_attributes: Dict of allowed attributes per tag
            allowed_protocols: List of allowed URL protocols
            strip_comments: Whether to remove HTML comments
            strip_scripts: Whether to remove script tags and content
        """
        self.allowed_tags = allowed_tags or self.DEFAULT_ALLOWED_TAGS
        self.allowed_attributes = allowed_attributes or self.DEFAULT_ALLOWED_ATTRIBUTES
        self.allowed_protocols = allowed_protocols or self.ALLOWED_PROTOCOLS
        self.strip_comments = strip_comments
        self.strip_scripts = strip_scripts
        
        # Initialize CSS sanitizer if bleach is available
        if BLEACH_AVAILABLE:
            self.css_sanitizer = CSSSanitizer(
                allowed_css_properties=['color', 'font-size', 'font-weight', 'text-align']
            )
        else:
            self.css_sanitizer = None
            
        # Log sanitizer configuration
        if BLEACH_AVAILABLE:
            logger.info("HTML sanitizer initialized with bleach (most secure)")
        elif BS4_AVAILABLE:
            logger.info("HTML sanitizer initialized with BeautifulSoup (secure)")
        else:
            logger.warning("HTML sanitizer using escaping only (no HTML formatting will be preserved)")
    
    def sanitize(self, html_content: str, allow_styles: bool = False) -> str:
        """
        Sanitize HTML content using the best available method.
        
        Args:
            html_content: HTML content to sanitize
            allow_styles: Whether to allow CSS styles (default: False)
            
        Returns:
            Sanitized HTML content
        """
        if not html_content:
            return ""
        
        # Use bleach if available (most secure)
        if BLEACH_AVAILABLE:
            return self._sanitize_with_bleach(html_content, allow_styles)
        
        # Fall back to BeautifulSoup if available
        if BS4_AVAILABLE:
            return self._sanitize_with_beautifulsoup(html_content)
        
        # Last resort: escape everything
        return self._escape_html(html_content)
    
    def _sanitize_with_bleach(self, html_content: str, allow_styles: bool) -> str:
        """Sanitize using bleach library."""
        try:
            # Configure bleach parameters
            attrs = dict(self.allowed_attributes)
            if allow_styles and self.css_sanitizer:
                attrs['*'] = attrs.get('*', []) + ['style']
            
            # Clean the HTML
            cleaned = bleach.clean(
                html_content,
                tags=list(self.allowed_tags),
                attributes=attrs,
                protocols=self.allowed_protocols,
                strip=True,
                strip_comments=self.strip_comments,
                css_sanitizer=self.css_sanitizer if allow_styles else None
            )
            
            return cleaned
            
        except Exception as e:
            logger.error(f"Bleach sanitization failed: {e}")
            # Fall back to BeautifulSoup
            if BS4_AVAILABLE:
                return self._sanitize_with_beautifulsoup(html_content)
            return self._escape_html(html_content)
    
    def _sanitize_with_beautifulsoup(self, html_content: str) -> str:
        """Sanitize using BeautifulSoup HTML parser."""
        try:
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style tags completely
            if self.strip_scripts:
                for script in soup(['script', 'style']):
                    script.decompose()
            
            # Remove comments
            if self.strip_comments:
                for comment in soup.find_all(text=lambda text: isinstance(text, str) and text.strip().startswith('<!--')):
                    comment.extract()
            
            # Process all tags
            for tag in soup.find_all(True):
                # Remove disallowed tags but keep content
                if tag.name not in self.allowed_tags:
                    tag.unwrap()
                    continue
                
                # Clean attributes
                allowed_attrs = self.allowed_attributes.get(tag.name, [])
                allowed_attrs += self.allowed_attributes.get('*', [])
                
                # Remove disallowed attributes
                for attr in list(tag.attrs.keys()):
                    if attr not in allowed_attrs:
                        del tag[attr]
                    # Validate URLs
                    elif attr in ['href', 'src', 'cite']:
                        url = tag[attr]
                        if not self._is_safe_url(url):
                            del tag[attr]
                    # Remove event handlers
                    elif attr.startswith('on'):
                        del tag[attr]
            
            return str(soup)
            
        except Exception as e:
            logger.error(f"BeautifulSoup sanitization failed: {e}")
            return self._escape_html(html_content)
    
    def _escape_html(self, html_content: str) -> str:
        """
        Escape all HTML entities (safest but removes all formatting).
        
        This is the fallback when no HTML parsing library is available.
        """
        return html.escape(html_content, quote=True)
    
    def _is_safe_url(self, url: str) -> bool:
        """
        Check if a URL is safe based on protocol.
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL is safe, False otherwise
        """
        if not url:
            return True
        
        # Allow relative URLs
        if not url.startswith(('http://', 'https://', 'ftp://', 'mailto:', '//', ':')):
            return True
        
        # Parse and check protocol
        try:
            parsed = urlparse(url)
            
            # Check for javascript: and data: URLs
            if parsed.scheme in ['javascript', 'data', 'vbscript']:
                return False
            
            # Check against allowed protocols
            if parsed.scheme and parsed.scheme not in self.allowed_protocols:
                return False
                
            return True
            
        except Exception:
            # If parsing fails, consider it unsafe
            return False
    
    def strip_all_tags(self, html_content: str) -> str:
        """
        Remove all HTML tags, keeping only text content.
        
        Args:
            html_content: HTML content to strip
            
        Returns:
            Plain text content
        """
        if not html_content:
            return ""
        
        if BS4_AVAILABLE:
            try:
                soup = BeautifulSoup(html_content, 'html.parser')
                return soup.get_text(separator=' ', strip=True)
            except Exception as e:
                logger.error(f"Failed to strip tags with BeautifulSoup: {e}")
        
        if BLEACH_AVAILABLE:
            try:
                return bleach.clean(html_content, tags=[], strip=True)
            except Exception as e:
                logger.error(f"Failed to strip tags with bleach: {e}")
        
        # Fallback: just escape everything
        return html.escape(html_content)


# Singleton instance for convenience
_default_sanitizer = None


def get_sanitizer() -> HtmlSanitizer:
    """Get the default HTML sanitizer instance."""
    global _default_sanitizer
    if _default_sanitizer is None:
        _default_sanitizer = HtmlSanitizer()
    return _default_sanitizer


def sanitize_html(
    html_content: str,
    allowed_tags: Optional[Set[str]] = None,
    allow_styles: bool = False
) -> str:
    """
    Convenience function to sanitize HTML content.
    
    Args:
        html_content: HTML content to sanitize
        allowed_tags: Optional set of allowed tags (uses defaults if None)
        allow_styles: Whether to allow CSS styles
        
    Returns:
        Sanitized HTML content
    """
    if allowed_tags:
        sanitizer = HtmlSanitizer(allowed_tags=allowed_tags)
    else:
        sanitizer = get_sanitizer()
    
    return sanitizer.sanitize(html_content, allow_styles=allow_styles)


def strip_html_tags(html_content: str) -> str:
    """
    Convenience function to strip all HTML tags from content.
    
    Args:
        html_content: HTML content to strip
        
    Returns:
        Plain text content
    """
    sanitizer = get_sanitizer()
    return sanitizer.strip_all_tags(html_content)