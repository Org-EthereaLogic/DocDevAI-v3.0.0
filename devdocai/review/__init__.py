"""
M007 Review Engine Module.

Provides multi-dimensional document analysis and review capabilities with
PII detection, comprehensive review criteria, and integration with M001-M006 modules.
"""

from .review_engine import ReviewEngine, ReviewEngineConfig
from .models import (
    ReviewResult,
    ReviewDimension,
    ReviewSeverity,
    ReviewIssue,
    DimensionResult,
    ReviewMetrics,
    ReviewStatus
)
from .dimensions import (
    BaseDimension,
    TechnicalAccuracyDimension,
    CompletenessDimension,
    ConsistencyDimension,
    StyleFormattingDimension,
    SecurityPIIDimension,
    get_default_dimensions
)

__all__ = [
    # Engine
    'ReviewEngine',
    'ReviewEngineConfig',
    
    # Models
    'ReviewResult',
    'ReviewDimension',
    'ReviewSeverity',
    'ReviewIssue',
    'DimensionResult',
    'ReviewMetrics',
    'ReviewStatus',
    
    # Dimensions
    'BaseDimension',
    'TechnicalAccuracyDimension',
    'CompletenessDimension',
    'ConsistencyDimension',
    'StyleFormattingDimension',
    'SecurityPIIDimension',
    'get_default_dimensions',
]

__version__ = "1.0.0"