"""
M004 Document Generator - Core Components (Unified).

Exports unified components with backward compatibility aliases.
"""

from .unified_template_loader import (
    UnifiedTemplateLoader,
    TemplateMetadata,
    SecurityLevel,
    create_template_loader,
    # Backward compatibility
    UnifiedTemplateLoader as TemplateLoader,
    UnifiedTemplateLoader as SecureTemplateLoader
)

from .unified_engine import (
    UnifiedDocumentGenerator,
    UnifiedGenerationConfig,
    GenerationResult,
    EngineMode,
    create_generator,
    # Backward compatibility
    UnifiedDocumentGenerator as DocumentGenerator,
    UnifiedGenerationConfig as GenerationConfig
)

from .content_processor import ContentProcessor

__all__ = [
    'UnifiedTemplateLoader',
    'TemplateLoader',
    'SecureTemplateLoader',
    'TemplateMetadata',
    'SecurityLevel',
    'create_template_loader',
    'UnifiedDocumentGenerator',
    'DocumentGenerator',
    'UnifiedGenerationConfig',
    'GenerationConfig',
    'GenerationResult',
    'EngineMode',
    'create_generator',
    'ContentProcessor'
]
