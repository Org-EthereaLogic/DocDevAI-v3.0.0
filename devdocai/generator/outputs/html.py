"""
M004 Document Generator - HTML output formatter.

Handles HTML conversion from markdown with styling, table of contents,
and responsive design features.
"""

import logging
import re
from typing import Optional, Dict, Any
from pathlib import Path

try:
    import markdown
    from markdown.extensions import toc, tables, fenced_code, codehilite
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False
    logging.warning("python-markdown not available. HTML output will be limited.")

from ..core.template_loader import TemplateMetadata
from ...common.logging import get_logger

logger = get_logger(__name__)


class HtmlOutput:
    """
    Formats document content for HTML output.
    
    Features:
    - Markdown to HTML conversion
    - CSS styling and responsive design
    - Syntax highlighting for code blocks
    - Table of contents generation
    - Print-friendly styling
    """
    
    def __init__(self):
        """Initialize the HTML formatter."""
        self.markdown_processor = None
        
        if MARKDOWN_AVAILABLE:
            # Configure markdown processor with extensions
            self.markdown_processor = markdown.Markdown(
                extensions=[
                    'toc',
                    'tables',
                    'fenced_code',
                    'codehilite',
                    'attr_list',
                    'def_list'
                ],
                extension_configs={
                    'toc': {
                        'toc_depth': 6,
                        'anchorlink': True,
                        'title': 'Table of Contents'
                    },
                    'codehilite': {
                        'css_class': 'highlight',
                        'use_pygments': True
                    }
                }
            )
        
        logger.debug("HtmlOutput initialized")
    
    def format_content(
        self, 
        content: str, 
        template_metadata: TemplateMetadata,
        include_css: bool = True,
        include_toc: bool = False,
        responsive: bool = True
    ) -> str:
        """
        Format content for HTML output.
        
        Args:
            content: Processed markdown content
            template_metadata: Template metadata for context
            include_css: Whether to include CSS styling
            include_toc: Whether to include table of contents
            responsive: Whether to include responsive design CSS
            
        Returns:
            Complete HTML document
        """
        try:
            if not MARKDOWN_AVAILABLE:
                return self._create_basic_html(content, template_metadata, include_css)
            
            # Convert markdown to HTML
            html_content = self.markdown_processor.convert(content)
            
            # Get table of contents if available
            toc_html = ""
            if include_toc and hasattr(self.markdown_processor, 'toc'):
                toc_html = self.markdown_processor.toc
            
            # Create complete HTML document
            full_html = self._create_html_document(
                html_content,
                template_metadata,
                toc_html,
                include_css,
                responsive
            )
            
            # Reset markdown processor for next use
            self.markdown_processor.reset()
            
            logger.debug(f"HTML formatting completed ({len(full_html)} characters)")
            return full_html
            
        except Exception as e:
            logger.error(f"HTML formatting failed: {e}")
            # Fallback to basic HTML
            return self._create_basic_html(content, template_metadata, include_css)
    
    def get_default_css(self, responsive: bool = True) -> str:
        """
        Get default CSS styles for HTML documents.
        
        Args:
            responsive: Whether to include responsive design rules
            
        Returns:
            CSS stylesheet content
        """
        css = """
        /* DevDocAI Document Styles */
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
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Open Sans', 'Helvetica Neue', sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            background-color: var(--background-color);
            max-width: 900px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        /* Typography */
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
        h5 { font-size: 1.125rem; }
        h6 { font-size: 1rem; }
        
        p {
            margin-bottom: 1rem;
        }
        
        /* Links */
        a {
            color: var(--accent-color);
            text-decoration: none;
        }
        
        a:hover {
            text-decoration: underline;
        }
        
        /* Lists */
        ul, ol {
            margin-bottom: 1rem;
            padding-left: 2rem;
        }
        
        li {
            margin-bottom: 0.5rem;
        }
        
        /* Code */
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
        
        /* Tables */
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
        
        /* Blockquotes */
        blockquote {
            border-left: 4px solid var(--accent-color);
            padding-left: 1rem;
            margin: 1rem 0;
            font-style: italic;
            color: var(--secondary-color);
        }
        
        /* Horizontal Rules */
        hr {
            border: none;
            height: 1px;
            background-color: var(--border-color);
            margin: 2rem 0;
        }
        
        /* Table of Contents */
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
        
        .toc a {
            display: block;
            padding: 0.25rem 0;
        }
        
        /* Document Header */
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
        """
        
        if responsive:
            css += """
        
        /* Responsive Design */
        @media (max-width: 768px) {
            body {
                padding: 1rem;
            }
            
            h1 { font-size: 1.875rem; }
            h2 { font-size: 1.5rem; }
            h3 { font-size: 1.25rem; }
            
            table {
                font-size: 0.875rem;
            }
            
            pre {
                padding: 0.75rem;
            }
        }
        
        @media (max-width: 480px) {
            body {
                padding: 0.75rem;
            }
            
            h1 { font-size: 1.5rem; }
            h2 { font-size: 1.25rem; }
        }
        """
        
        css += """
        
        /* Print Styles */
        @media print {
            body {
                max-width: none;
                padding: 0;
                color: black;
                background: white;
            }
            
            .toc {
                page-break-after: always;
            }
            
            h1, h2, h3 {
                page-break-after: avoid;
            }
            
            pre, table {
                page-break-inside: avoid;
            }
            
            a {
                color: black;
                text-decoration: none;
            }
            
            a[href]:after {
                content: " (" attr(href) ")";
                font-size: 0.8em;
            }
        }
        """
        
        return css
    
    def _create_html_document(
        self,
        content: str,
        template_metadata: TemplateMetadata,
        toc_html: str = "",
        include_css: bool = True,
        responsive: bool = True
    ) -> str:
        """Create complete HTML document structure."""
        
        # Document title
        title = template_metadata.title or template_metadata.name
        
        # CSS styles
        css_content = ""
        if include_css:
            css_content = f"<style>\n{self.get_default_css(responsive)}\n</style>"
        
        # Table of contents
        toc_section = ""
        if toc_html:
            toc_section = f'<div class="toc">\n{toc_html}\n</div>'
        
        # Document header
        header_section = self._create_document_header(template_metadata)
        
        # Complete HTML document
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="generator" content="DevDocAI v3.0.0">
    <meta name="template" content="{template_metadata.name}">
    <title>{title}</title>
    {css_content}
</head>
<body>
    {header_section}
    {toc_section}
    <div class="document-content">
        {content}
    </div>
    <footer style="margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--border-color); color: var(--secondary-color); font-size: 0.875rem; text-align: center;">
        Generated by <strong>DevDocAI v3.0.0</strong> using template: {template_metadata.name}
    </footer>
</body>
</html>"""
        
        return html
    
    def _create_document_header(self, template_metadata: TemplateMetadata) -> str:
        """Create document header with metadata."""
        title = template_metadata.title or template_metadata.name
        
        meta_items = []
        
        if template_metadata.author:
            meta_items.append(f"<span><strong>Author:</strong> {template_metadata.author}</span>")
        
        meta_items.append(f"<span><strong>Type:</strong> {template_metadata.type}</span>")
        
        if template_metadata.version:
            meta_items.append(f"<span><strong>Version:</strong> {template_metadata.version}</span>")
        
        from datetime import datetime
        meta_items.append(f"<span><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</span>")
        
        meta_html = "\n        ".join(meta_items)
        
        return f"""<header class="document-header">
    <h1>{title}</h1>
    <div class="document-meta">
        {meta_html}
    </div>
</header>"""
    
    def _create_basic_html(
        self, 
        content: str, 
        template_metadata: TemplateMetadata, 
        include_css: bool
    ) -> str:
        """Create basic HTML when python-markdown is not available."""
        title = template_metadata.title or template_metadata.name
        
        # Convert basic markdown manually
        html_content = self._basic_markdown_to_html(content)
        
        css_content = ""
        if include_css:
            css_content = f"<style>\n{self.get_default_css()}\n</style>"
        
        header_section = self._create_document_header(template_metadata)
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="generator" content="DevDocAI v3.0.0 (Basic HTML)">
    <title>{title}</title>
    {css_content}
</head>
<body>
    {header_section}
    <div class="document-content">
        {html_content}
    </div>
    <footer style="margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #ccc; color: #666; font-size: 0.875rem; text-align: center;">
        Generated by <strong>DevDocAI v3.0.0</strong> (Basic HTML mode)
    </footer>
</body>
</html>"""
    
    def _basic_markdown_to_html(self, content: str) -> str:
        """Basic markdown to HTML conversion without external libraries."""
        html = content
        
        # Headers
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
        html = re.sub(r'^##### (.+)$', r'<h5>\1</h5>', html, flags=re.MULTILINE)
        html = re.sub(r'^###### (.+)$', r'<h6>\1</h6>', html, flags=re.MULTILINE)
        
        # Bold and italic
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        
        # Links
        html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)
        
        # Code (simple)
        html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
        
        # Line breaks to paragraphs
        paragraphs = html.split('\n\n')
        html_paragraphs = []
        
        for para in paragraphs:
            para = para.strip()
            if para:
                if not para.startswith('<'):
                    para = f"<p>{para}</p>"
                html_paragraphs.append(para)
        
        return '\n\n'.join(html_paragraphs)