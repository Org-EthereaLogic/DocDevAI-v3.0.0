"""Output formatters for M004 Document Generator."""

from .markdown import MarkdownOutput
from .html import HtmlOutput

__all__ = [
    'MarkdownOutput',
    'HtmlOutput'
]