"""
M004 Document Generator - Utility Components (Unified).

Exports unified validators with backward compatibility aliases.
"""

from .unified_validators import (
    UnifiedValidator,
    ValidationLevel,
    ValidationError,
    create_validator,
    # Backward compatibility
    UnifiedValidator as Validator,
    UnifiedValidator as InputValidator,
    UnifiedValidator as SecurityValidator,
    UnifiedValidator as EnhancedSecurityValidator
)

from .formatters import ContentFormatter

__all__ = [
    'UnifiedValidator',
    'Validator',
    'InputValidator',
    'SecurityValidator',
    'EnhancedSecurityValidator',
    'ValidationLevel',
    'ValidationError',
    'create_validator',
    'ContentFormatter'
]
