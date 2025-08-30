"""
M004 Document Generator - Core Components (Unified).

Exports unified components with backward compatibility aliases.
"""

# Now using M006's template registry through adapter for proper integration
from .template_registry_adapter import (
    TemplateRegistryAdapter as UnifiedTemplateLoader,
    TemplateMetadata,
    SecurityLevel,
    # Backward compatibility
    TemplateRegistryAdapter as TemplateLoader,
    TemplateRegistryAdapter as SecureTemplateLoader
)

# Helper function for creating template loader
def create_template_loader(*args, **kwargs):
    """Create a template loader instance (uses M006 registry through adapter)."""
    return UnifiedTemplateLoader(*args, **kwargs)

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
