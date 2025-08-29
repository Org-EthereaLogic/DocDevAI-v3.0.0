"""
M004 Document Generator - Output Components (Unified).

Exports unified output generators with backward compatibility aliases.
"""

from .unified_html_output import (
    UnifiedHTMLOutput,
    SecurityLevel,
    create_html_output,
    # Backward compatibility
    UnifiedHTMLOutput as HTMLOutput,
    UnifiedHTMLOutput as SecureHTMLOutput,
    UnifiedHTMLOutput as HtmlOutput,
    UnifiedHTMLOutput as SecureHtmlOutput
)

from .markdown import MarkdownOutput

__all__ = [
    'UnifiedHTMLOutput',
    'HTMLOutput',
    'SecureHTMLOutput',
    'HtmlOutput',
    'SecureHtmlOutput',
    'SecurityLevel',
    'create_html_output',
    'MarkdownOutput'
]
