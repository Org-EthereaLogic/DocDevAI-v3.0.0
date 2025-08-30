"""
M006 Template Registry Module.

This module provides comprehensive template management capabilities
for the DevDocAI system, including 30+ document templates,
template parsing, validation, and registry management.
"""

from .registry import TemplateRegistry
from .template import Template
from .models import (
    TemplateCategory,
    TemplateType,
    TemplateMetadata,
    TemplateVariable,
    TemplateSection,
    TemplateSearchCriteria,
    TemplateRenderContext,
    TemplateValidationResult
)
from .loader import TemplateLoader
from .validator import TemplateValidator
from .parser import TemplateParser
from .categories import CategoryManager
from .exceptions import (
    TemplateError,
    TemplateNotFoundError,
    TemplateParseError,
    TemplateValidationError,
    TemplateRenderError,
    TemplateCategoryError,
    TemplateVersionError,
    TemplateStorageError,
    TemplatePermissionError,
    TemplateDuplicateError,
    TemplateIncludeError,
    TemplateVariableError
)

__all__ = [
    # Main classes
    'TemplateRegistry',
    'Template',
    'TemplateLoader',
    'TemplateValidator',
    'TemplateParser',
    'CategoryManager',
    
    # Models
    'TemplateCategory',
    'TemplateType',
    'TemplateMetadata',
    'TemplateVariable',
    'TemplateSection',
    'TemplateSearchCriteria',
    'TemplateRenderContext',
    'TemplateValidationResult',
    
    # Exceptions
    'TemplateError',
    'TemplateNotFoundError',
    'TemplateParseError',
    'TemplateValidationError',
    'TemplateRenderError',
    'TemplateCategoryError',
    'TemplateVersionError',
    'TemplateStorageError',
    'TemplatePermissionError',
    'TemplateDuplicateError',
    'TemplateIncludeError',
    'TemplateVariableError',
]

# Module version
__version__ = "1.0.0"

# Module metadata
__author__ = "DevDocAI"
__description__ = "Template Registry and Management System"