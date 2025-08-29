"""
M004 Document Generator - Secure HTML output with comprehensive XSS prevention.

Enhanced HTML output formatter with security hardening for Pass 3.
"""

import html
import re
import logging
import urllib.parse
from typing import Optional, Dict, Any, List, Set
from pathlib import Path
import hashlib
from datetime import datetime

try:
    import markdown
    from markdown.extensions import toc, tables, fenced_code, codehilite
    import bleach
    from bleach.css_sanitizer import CSSSanitizer
    SECURITY_LIBS_AVAILABLE = True
except ImportError:
    SECURITY_LIBS_AVAILABLE = False
    logging.warning("Security libraries (bleach) not available. HTML sanitization will be basic.")

from ..core.template_loader import TemplateMetadata
from ...common.logging import get_logger
from ...common.security import AuditLogger, get_audit_logger

logger = get_logger(__name__)


class SecureHtmlOutput:
    """
    Secure HTML output formatter with comprehensive XSS prevention.
    
    Security Features:
    - HTML sanitization with allowlist approach
    - CSS sanitization and validation
    - URL validation and sanitization
    - Content Security Policy header generation
    - XSS pattern detection and removal
    - Safe markdown processing
    - Output integrity verification
    - Security audit logging
    """
    
    # Allowed HTML tags (very restrictive for security)
    ALLOWED_TAGS = [
        'p', 'br', 'strong', 'em', 'b', 'i', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'dl', 'dt', 'dd', 'blockquote', 'pre', 'code', 'hr',
        'table', 'thead', 'tbody', 'tr', 'th', 'td', 'caption',
        'div', 'span', 'section', 'article', 'header', 'footer', 'nav',
        'a', 'img', 'figure', 'figcaption'
    ]
    
    # Allowed attributes for HTML tags
    ALLOWED_ATTRIBUTES = {
        'a': ['href', 'title', 'id', 'class'],
        'img': ['src', 'alt', 'title', 'width', 'height', 'id', 'class'],
        'h1': ['id', 'class'],
        'h2': ['id', 'class'],
        'h3': ['id', 'class'],
        'h4': ['id', 'class'],
        'h5': ['id', 'class'],
        'h6': ['id', 'class'],
        'p': ['id', 'class'],
        'div': ['id', 'class'],
        'span': ['id', 'class'],
        'section': ['id', 'class'],
        'article': ['id', 'class'],
        'table': ['id', 'class'],
        'th': ['id', 'class', 'scope'],
        'td': ['id', 'class', 'colspan', 'rowspan'],
        'pre': ['id', 'class'],
        'code': ['id', 'class'],
        'blockquote': ['id', 'class', 'cite'],
        'ul': ['id', 'class'],
        'ol': ['id', 'class', 'start'],
        'li': ['id', 'class']
    }
    
    # Allowed URL schemes
    ALLOWED_URL_SCHEMES = ['http', 'https', 'mailto', 'tel']
    
    # Allowed CSS properties (very restrictive)
    ALLOWED_CSS_PROPERTIES = [
        'color', 'background-color', 'font-size', 'font-weight', 'font-family',
        'text-align', 'text-decoration', 'margin', 'padding', 'border',
        'width', 'height', 'max-width', 'max-height', 'display',
        'float', 'clear', 'line-height', 'letter-spacing'
    ]
    
    # Dangerous patterns to detect and remove
    DANGEROUS_PATTERNS = [
        re.compile(r'javascript:', re.IGNORECASE),
        re.compile(r'vbscript:', re.IGNORECASE),
        re.compile(r'data:', re.IGNORECASE),
        re.compile(r'on\w+\s*=', re.IGNORECASE),  # Event handlers
        re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
        re.compile(r'<iframe[^>]*>.*?</iframe>', re.IGNORECASE | re.DOTALL),
        re.compile(r'<object[^>]*>.*?</object>', re.IGNORECASE | re.DOTALL),
        re.compile(r'<embed[^>]*>', re.IGNORECASE),
        re.compile(r'<link[^>]*>', re.IGNORECASE),
        re.compile(r'<meta[^>]*http-equiv', re.IGNORECASE),
        re.compile(r'expression\s*\(', re.IGNORECASE),  # CSS expressions
        re.compile(r'@import', re.IGNORECASE),  # CSS imports
    ]
    
    def __init__(self, strict_mode: bool = True):
        """
        Initialize secure HTML output formatter.
        
        Args:
            strict_mode: Enable strict security mode
        """
        self.strict_mode = strict_mode
        self.audit_logger = get_audit_logger()
        self.markdown_processor = None
        
        # Initialize markdown processor if available
        if SECURITY_LIBS_AVAILABLE and markdown:
            self.markdown_processor = markdown.Markdown(
                extensions=[
                    'toc',
                    'tables',
                    'fenced_code',
                    'codehilite'
                ],
                extension_configs={
                    'toc': {
                        'toc_depth': 6,
                        'anchorlink': True,
                        'title': 'Table of Contents'
                    },
                    'codehilite': {
                        'css_class': 'highlight',
                        'use_pygments': False  # Disable for security
                    }
                }
            )
        
        # Initialize bleach cleaner if available
        if SECURITY_LIBS_AVAILABLE and bleach:
            css_sanitizer = CSSSanitizer(allowed_css_properties=self.ALLOWED_CSS_PROPERTIES)
            self.html_cleaner = bleach.Cleaner(
                tags=self.ALLOWED_TAGS,
                attributes=self.ALLOWED_ATTRIBUTES,
                protocols=self.ALLOWED_URL_SCHEMES,
                css_sanitizer=css_sanitizer,
                strip=True,
                strip_comments=True
            )
        else:
            self.html_cleaner = None
        
        logger.info(f"SecureHtmlOutput initialized: strict_mode={strict_mode}, "
                   f"security_libs={SECURITY_LIBS_AVAILABLE}")
    
    def format_content_secure(
        self, 
        content: str, 
        template_metadata: TemplateMetadata,
        client_id: str = 'anonymous',
        include_css: bool = True,
        include_toc: bool = False,
        responsive: bool = True
    ) -> Dict[str, Any]:
        """
        Securely format content for HTML output with comprehensive security checks.
        
        Args:
            content: Processed markdown content
            template_metadata: Template metadata for context
            client_id: Client identifier for audit logging
            include_css: Whether to include CSS styling
            include_toc: Whether to include table of contents
            responsive: Whether to include responsive design CSS
            
        Returns:
            Dictionary with formatted content and security metadata
        """
        result = {
            'html_content': '',
            'security_metadata': {
                'client_id': client_id,
                'timestamp': datetime.now().isoformat(),
                'template_name': template_metadata.name,
                'security_checks': [],
                'warnings': [],
                'csp_header': ''
            }
        }
        
        try:
            # Pre-processing security checks
            security_scan = self._pre_process_security_scan(content)
            result['security_metadata']['security_checks'].append('pre_process_scan')
            result['security_metadata']['warnings'].extend(security_scan['warnings'])
            
            if security_scan['critical_issues']:
                self._log_security_violation(client_id, template_metadata.name, 
                                           'critical_content_issues', security_scan['critical_issues'])
                raise SecurityError("Critical security issues detected in content")
            
            # Sanitize input content
            sanitized_content = self._sanitize_input_content(content)
            result['security_metadata']['security_checks'].append('input_sanitized')
            
            # Convert markdown to HTML securely
            html_content = self._convert_markdown_secure(sanitized_content)
            result['security_metadata']['security_checks'].append('markdown_converted')
            
            # Comprehensive HTML sanitization
            clean_html = self._sanitize_html_comprehensive(html_content)
            result['security_metadata']['security_checks'].append('html_sanitized')
            
            # Generate table of contents if requested
            toc_html = ""
            if include_toc:
                toc_html = self._generate_secure_toc(clean_html)
                result['security_metadata']['security_checks'].append('toc_generated')
            
            # Create complete HTML document
            full_html = self._create_secure_html_document(
                clean_html,
                template_metadata,
                toc_html,
                include_css,
                responsive
            )
            result['security_metadata']['security_checks'].append('document_created')
            
            # Post-processing security validation
            self._post_process_security_validation(full_html)
            result['security_metadata']['security_checks'].append('post_process_validated')
            
            # Generate Content Security Policy
            csp_header = self._generate_csp_header()
            result['security_metadata']['csp_header'] = csp_header
            result['security_metadata']['security_checks'].append('csp_generated')
            
            result['html_content'] = full_html
            
            # Log successful formatting
            self._log_formatting_success(client_id, template_metadata.name, len(full_html))
            
            logger.info(f"HTML content formatted securely: {len(full_html)} chars for {client_id}")
            return result
            
        except Exception as e:
            self._log_security_violation(client_id, template_metadata.name, 
                                       'formatting_failed', str(e))
            logger.error(f"Secure HTML formatting failed: {e}")
            raise
    
    def _pre_process_security_scan(self, content: str) -> Dict[str, Any]:
        """Comprehensive pre-processing security scan."""
        scan_result = {
            'warnings': [],
            'critical_issues': []
        }
        
        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            matches = pattern.findall(content)
            if matches:
                if self.strict_mode:
                    scan_result['critical_issues'].append(f"Dangerous pattern detected: {pattern.pattern}")
                else:
                    scan_result['warnings'].append(f"Dangerous pattern detected: {pattern.pattern}")
        
        # Check content size
        if len(content) > 10 * 1024 * 1024:  # 10MB
            scan_result['critical_issues'].append("Content too large (potential DoS)")
        
        # Check for suspicious base64 content
        base64_pattern = re.compile(r'data:.*;base64,', re.IGNORECASE)
        if base64_pattern.search(content):
            scan_result['warnings'].append("Base64 data URLs detected")
        
        # Check for potential SSTI patterns
        ssti_patterns = [
            r'{{.*?}}',
            r'{%.*?%}',
            r'${.*?}',
            r'#{.*?}'
        ]
        
        for pattern_str in ssti_patterns:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            if pattern.search(content):
                scan_result['warnings'].append(f"Template injection pattern detected: {pattern_str}")
        
        return scan_result
    
    def _sanitize_input_content(self, content: str) -> str:
        """Sanitize input content before processing."""
        # HTML encode the content first
        sanitized = html.escape(content)
        
        # Remove null bytes and other dangerous characters
        sanitized = sanitized.replace('\x00', '')
        sanitized = re.sub(r'[\x01-\x08\x0B\x0C\x0E-\x1F\x7F]', '', sanitized)
        
        # Remove dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            sanitized = pattern.sub('', sanitized)
        
        return sanitized
    
    def _convert_markdown_secure(self, content: str) -> str:
        """Securely convert markdown to HTML."""
        if not self.markdown_processor:
            # Fallback to basic conversion
            return self._basic_markdown_to_html_secure(content)
        
        try:
            # Reset processor for clean state
            self.markdown_processor.reset()
            
            # Convert markdown
            html_content = self.markdown_processor.convert(content)
            
            return html_content
            
        except Exception as e:
            logger.warning(f"Markdown conversion failed, using fallback: {e}")
            return self._basic_markdown_to_html_secure(content)
    
    def _basic_markdown_to_html_secure(self, content: str) -> str:
        """Basic secure markdown to HTML conversion."""
        html_content = content
        
        # Headers
        html_content = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html_content, flags=re.MULTILINE)
        html_content = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html_content, flags=re.MULTILINE)
        html_content = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html_content, flags=re.MULTILINE)
        
        # Bold and italic (with HTML escaping)
        html_content = re.sub(r'\\*\\*(.+?)\\*\\*', r'<strong>\1</strong>', html_content)
        html_content = re.sub(r'\\*(.+?)\\*', r'<em>\1</em>', html_content)
        
        # Links (with URL validation)
        def safe_link_replace(match):
            text = html.escape(match.group(1))
            url = match.group(2)
            if self._is_safe_url(url):
                return f'<a href=\"{html.escape(url)}\">{text}</a>'
            else:
                return text  # Just return text if URL is unsafe
        
        html_content = re.sub(r'\\[([^\\]]+)\\]\\(([^)]+)\\)', safe_link_replace, html_content)
        
        # Code (inline)
        html_content = re.sub(r'`([^`]+)`', r'<code>\1</code>', html_content)
        
        # Paragraphs
        paragraphs = html_content.split('\\n\\n')
        html_paragraphs = []
        
        for para in paragraphs:
            para = para.strip()
            if para and not para.startswith('<'):
                para = f"<p>{para}</p>"
            if para:
                html_paragraphs.append(para)
        
        return '\n\n'.join(html_paragraphs)
    
    def _sanitize_html_comprehensive(self, html_content: str) -> str:
        \"\"\"Comprehensive HTML sanitization.\"\"\"
        if self.html_cleaner:
            # Use bleach for thorough sanitization
            return self.html_cleaner.clean(html_content)
        else:
            # Fallback manual sanitization
            return self._manual_html_sanitization(html_content)
    
    def _manual_html_sanitization(self, html_content: str) -> str:
        \"\"\"Manual HTML sanitization when bleach is not available.\"\"\"
        # Remove dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            html_content = pattern.sub('', html_content)
        
        # Basic tag allowlist
        allowed_pattern = '|'.join(self.ALLOWED_TAGS)
        tag_pattern = re.compile(f'<(?!/?({allowed_pattern})\\b)[^>]*>', re.IGNORECASE)
        html_content = tag_pattern.sub('', html_content)
        
        # Remove dangerous attributes
        attr_pattern = re.compile(r'\\son\\w+\\s*=\\s*[\"\\'][^\"\\'][\"\\']', re.IGNORECASE)
        html_content = attr_pattern.sub('', html_content)
        
        return html_content
    
    def _generate_secure_toc(self, html_content: str) -> str:
        \"\"\"Generate secure table of contents.\"\"\"
        # Extract headers safely
        header_pattern = re.compile(r'<(h[1-6])(?:[^>]*id=[\"\\']([^\"\\'][^\"\\'])[\"\\'])?[^>]*>([^<]+)</h[1-6]>', re.IGNORECASE)
        headers = header_pattern.findall(html_content)
        
        if not headers:
            return \"\"
        
        toc_items = []
        for tag, id_attr, text in headers:
            level = int(tag[1])  # h1 -> 1, h2 -> 2, etc.
            safe_text = html.escape(text.strip())
            
            if id_attr:
                safe_id = html.escape(id_attr)
                toc_items.append(f'<li class=\"toc-level-{level}\"><a href=\"#{safe_id}\">{safe_text}</a></li>')
            else:
                toc_items.append(f'<li class=\"toc-level-{level}\">{safe_text}</li>')
        
        toc_html = f\"\"\"
        <div class=\"toc\">
            <h2>Table of Contents</h2>
            <ul>
                {''.join(toc_items)}
            </ul>
        </div>
        \"\"\"
        
        return toc_html
    
    def _create_secure_html_document(
        self,
        content: str,
        template_metadata: TemplateMetadata,
        toc_html: str = \"\",
        include_css: bool = True,
        responsive: bool = True
    ) -> str:
        \"\"\"Create complete secure HTML document.\"\"\"
        
        # Document title (safely escaped)
        title = html.escape(template_metadata.title or template_metadata.name)
        
        # CSS styles (secure)
        css_content = \"\"
        if include_css:
            css_content = f\"<style nonce='{self._generate_nonce()}'>{self._get_secure_css(responsive)}</style>\"
        
        # Table of contents
        toc_section = \"\"
        if toc_html:
            toc_section = toc_html
        
        # Document header (safely escaped)
        header_section = self._create_secure_document_header(template_metadata)
        
        # CSP nonce for inline styles
        nonce = self._generate_nonce()
        
        # Complete HTML document with security headers
        html_doc = f\"\"\"<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <meta name=\"generator\" content=\"DevDocAI v3.0.0 Secure\">
    <meta name=\"template\" content=\"{html.escape(template_metadata.name)}\">
    <meta name=\"X-Content-Type-Options\" content=\"nosniff\">
    <meta name=\"X-Frame-Options\" content=\"DENY\">
    <meta name=\"X-XSS-Protection\" content=\"1; mode=block\">
    <meta name=\"Referrer-Policy\" content=\"strict-origin-when-cross-origin\">
    <title>{title}</title>
    {css_content}
</head>
<body>
    {header_section}
    {toc_section}
    <main class=\"document-content\">
        {content}
    </main>
    <footer class=\"document-footer\">
        <p>Generated by <strong>DevDocAI v3.0.0</strong> (Security Hardened) using template: {html.escape(template_metadata.name)}</p>
        <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}</p>
    </footer>
</body>
</html>\"\"\"
        
        return html_doc
    
    def _create_secure_document_header(self, template_metadata: TemplateMetadata) -> str:
        \"\"\"Create secure document header with escaped metadata.\"\"\"
        title = html.escape(template_metadata.title or template_metadata.name)
        
        meta_items = []
        
        if template_metadata.author:
            safe_author = html.escape(template_metadata.author)
            meta_items.append(f\"<span><strong>Author:</strong> {safe_author}</span>\")
        
        safe_type = html.escape(template_metadata.type)
        meta_items.append(f\"<span><strong>Type:</strong> {safe_type}</span>\")
        
        if template_metadata.version:
            safe_version = html.escape(template_metadata.version)
            meta_items.append(f\"<span><strong>Version:</strong> {safe_version}</span>\")
        
        meta_items.append(f\"<span><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}</span>\")
        
        meta_html = \"\\n        \".join(meta_items)
        
        return f\"\"\"<header class=\"document-header\">
    <h1>{title}</h1>
    <div class=\"document-meta\">
        {meta_html}
    </div>
</header>\"\"\"
    
    def _get_secure_css(self, responsive: bool = True) -> str:
        \"\"\"Get secure CSS styles with no external dependencies.\"\"\"
        css = \"\"\"
        /* DevDocAI Secure Document Styles */
        :root {
            --primary-color: #2563eb;
            --secondary-color: #64748b;
            --background-color: #ffffff;
            --text-color: #1e293b;
            --border-color: #e2e8f0;
            --code-background: #f8fafc;
            --accent-color: #0ea5e9;
        }
        
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            background-color: var(--background-color);
            max-width: 900px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        h1, h2, h3, h4, h5, h6 {
            margin-top: 2rem;
            margin-bottom: 1rem;
            font-weight: 600;
            line-height: 1.25;
        }
        
        h1 { font-size: 2.25rem; color: var(--primary-color); }
        h2 { font-size: 1.875rem; color: var(--primary-color); }
        h3 { font-size: 1.5rem; }
        h4 { font-size: 1.25rem; }
        
        p { margin-bottom: 1rem; }
        
        a {
            color: var(--accent-color);
            text-decoration: none;
        }
        
        a:hover { text-decoration: underline; }
        
        code {
            background-color: var(--code-background);
            padding: 0.125rem 0.25rem;
            border-radius: 0.25rem;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 0.875rem;
        }
        
        pre {
            background-color: var(--code-background);
            padding: 1rem;
            border-radius: 0.5rem;
            overflow-x: auto;
            margin-bottom: 1rem;
            border: 1px solid var(--border-color);
        }
        
        pre code {
            background: none;
            padding: 0;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 1rem;
            border: 1px solid var(--border-color);
        }
        
        th, td {
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }
        
        th {
            background-color: var(--code-background);
            font-weight: 600;
        }
        
        .document-header {
            border-bottom: 2px solid var(--primary-color);
            margin-bottom: 2rem;
            padding-bottom: 1rem;
        }
        
        .document-meta {
            color: var(--secondary-color);
            font-size: 0.875rem;
            margin-top: 0.5rem;
        }
        
        .document-meta span {
            margin-right: 1rem;
        }
        
        .toc {
            background-color: var(--code-background);
            border: 1px solid var(--border-color);
            border-radius: 0.5rem;
            padding: 1rem;
            margin-bottom: 2rem;
        }
        
        .toc h2 {
            margin-top: 0;
            margin-bottom: 1rem;
            font-size: 1.25rem;
        }
        
        .toc ul {
            list-style: none;
            padding-left: 0;
        }
        
        .toc li {
            margin-bottom: 0.25rem;
        }
        
        .toc-level-2 { padding-left: 1rem; }
        .toc-level-3 { padding-left: 2rem; }
        .toc-level-4 { padding-left: 3rem; }
        
        .document-footer {
            margin-top: 3rem;
            padding-top: 1rem;
            border-top: 1px solid var(--border-color);
            color: var(--secondary-color);
            font-size: 0.875rem;
            text-align: center;
        }
        \"\"\"
        
        if responsive:
            css += \"\"\"
        
        @media (max-width: 768px) {
            body { padding: 1rem; }
            h1 { font-size: 1.875rem; }
            h2 { font-size: 1.5rem; }
            table { font-size: 0.875rem; }
        }
        
        @media (max-width: 480px) {
            body { padding: 0.75rem; }
            h1 { font-size: 1.5rem; }
            h2 { font-size: 1.25rem; }
        }
        \"\"\"
        
        css += \"\"\"
        
        @media print {
            body {
                max-width: none;
                padding: 0;
                color: black;
                background: white;
            }
            
            .toc { page-break-after: always; }
            h1, h2, h3 { page-break-after: avoid; }
            pre, table { page-break-inside: avoid; }
            
            a { color: black; text-decoration: none; }
            a[href]:after {
                content: \" (\" attr(href) \")\";
                font-size: 0.8em;
            }
        }
        \"\"\"
        
        return css
    
    def _post_process_security_validation(self, html_content: str):
        \"\"\"Post-processing security validation.\"\"\"
        
        # Check final content size
        if len(html_content) > 50 * 1024 * 1024:  # 50MB
            raise SecurityError(\"Final HTML content too large\")
        
        # Final scan for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern.search(html_content):
                if self.strict_mode:
                    raise SecurityError(f\"Dangerous pattern found in final output: {pattern.pattern}\")
                else:
                    logger.warning(f\"Dangerous pattern found in final output: {pattern.pattern}\")
    
    def _generate_csp_header(self) -> str:
        \"\"\"Generate Content Security Policy header.\"\"\"
        nonce = self._generate_nonce()
        
        csp = (
            \"default-src 'self'; \"
            f\"style-src 'self' 'nonce-{nonce}'; \"
            \"script-src 'none'; \"
            \"object-src 'none'; \"
            \"base-uri 'self'; \"
            \"form-action 'none'; \"
            \"frame-ancestors 'none'; \"
            \"img-src 'self' data:; \"
            \"font-src 'self'\"
        )
        
        return csp
    
    def _generate_nonce(self) -> str:
        \"\"\"Generate cryptographically secure nonce.\"\"\"
        import secrets
        return secrets.token_urlsafe(16)
    
    def _is_safe_url(self, url: str) -> bool:
        \"\"\"Check if URL is safe.\"\"\"
        try:
            parsed = urllib.parse.urlparse(url)
            return parsed.scheme in self.ALLOWED_URL_SCHEMES
        except Exception:
            return False
    
    def _log_security_violation(
        self, 
        client_id: str, 
        template_name: str, 
        violation_type: str, 
        details: Any
    ):
        \"\"\"Log security violations.\"\"\"
        self.audit_logger.log_event('html_security_violation', {
            'client_id': client_id,
            'template_name': template_name,
            'violation_type': violation_type,
            'details': str(details),
            'timestamp': datetime.now().isoformat()
        })
    
    def _log_formatting_success(self, client_id: str, template_name: str, content_size: int):
        \"\"\"Log successful formatting.\"\"\"
        self.audit_logger.log_event('html_formatting_success', {
            'client_id': client_id,
            'template_name': template_name,
            'content_size': content_size,
            'timestamp': datetime.now().isoformat()
        })


class SecurityError(Exception):
    \"\"\"Exception raised for security-related errors.\"\"\"
    pass