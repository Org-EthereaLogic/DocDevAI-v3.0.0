"""Core generation components for M004 Document Generator."""

from .engine import DocumentGenerator, GenerationConfig, GenerationResult
from .template_loader import TemplateLoader, TemplateMetadata
from .content_processor import ContentProcessor

__all__ = [
    'DocumentGenerator',
    'GenerationConfig',
    'GenerationResult',
    'TemplateLoader',
    'TemplateMetadata',
    'ContentProcessor'
]