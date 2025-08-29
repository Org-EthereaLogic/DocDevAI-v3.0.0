"""
M005: Quality Engine - Document quality analysis and enforcement.

This module provides comprehensive quality analysis for documentation,
including multi-dimensional scoring, quality gate enforcement, and
integration with other DevDocAI modules.

Performance targets:
- Analysis speed: < 500ms per document
- Quality gate: 85% minimum score
- Coverage: 80-85% (Pass 1)
"""

from .analyzer import QualityAnalyzer
from .models import (
    QualityConfig,
    QualityReport,
    QualityDimension,
    DimensionScore,
    QualityIssue,
    SeverityLevel,
    AnalysisRequest,
    ValidationRule
)
from .scoring import QualityScorer, ScoringMetrics
from .dimensions import (
    DimensionAnalyzer,
    CompletenessAnalyzer,
    ClarityAnalyzer,
    StructureAnalyzer,
    AccuracyAnalyzer,
    FormattingAnalyzer
)
from .validators import (
    DocumentValidator,
    MarkdownValidator,
    CodeDocumentValidator
)
from .exceptions import (
    QualityEngineError,
    QualityGateFailure,
    DimensionAnalysisError,
    ValidationError,
    IntegrationError,
    ScoringError,
    ConfigurationError
)

__version__ = "1.0.0"
__all__ = [
    # Main analyzer
    "QualityAnalyzer",
    
    # Models
    "QualityConfig",
    "QualityReport",
    "QualityDimension",
    "DimensionScore",
    "QualityIssue",
    "SeverityLevel",
    "AnalysisRequest",
    "ValidationRule",
    
    # Scoring
    "QualityScorer",
    "ScoringMetrics",
    
    # Dimensions
    "DimensionAnalyzer",
    "CompletenessAnalyzer",
    "ClarityAnalyzer",
    "StructureAnalyzer",
    "AccuracyAnalyzer",
    "FormattingAnalyzer",
    
    # Validators
    "DocumentValidator",
    "MarkdownValidator",
    "CodeDocumentValidator",
    
    # Exceptions
    "QualityEngineError",
    "QualityGateFailure",
    "DimensionAnalysisError",
    "ValidationError",
    "IntegrationError",
    "ScoringError",
    "ConfigurationError"
]