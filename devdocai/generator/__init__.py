"""
M004: Document Generator - AI-powered document generation system for DevDocAI.

This module provides template-based document generation with multi-format output,
content intelligence integration, and storage management.

Performance targets (Pass 2):
- Generation: <2 seconds for templates <50KB
- Concurrent: 100+ simultaneous generations
- Template loading: <100ms

Quality targets:
- Test coverage: 40-50% (Pass 1), 95% (Pass 3)
- Input validation and error handling
- Integration with M001, M002, M003
"""

from .core.unified_engine import UnifiedDocumentGenerator as DocumentGenerator
# Now using M006's template registry through adapter for proper integration
from .core.template_registry_adapter import TemplateRegistryAdapter as TemplateLoader
from .core.content_processor import ContentProcessor
from .outputs.markdown import MarkdownOutput
from .outputs.html import HtmlOutput
from .utils.validators import InputValidator
from .utils.formatters import ContentFormatter

__all__ = [
    'DocumentGenerator',
    'TemplateLoader', 
    'ContentProcessor',
    'MarkdownOutput',
    'HtmlOutput',
    'InputValidator',
    'ContentFormatter'
]

__version__ = '3.0.0'