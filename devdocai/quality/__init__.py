"""
M005 Quality Engine - Unified Implementation.

Provides comprehensive document quality analysis with configurable
operation modes for performance and security optimization.
"""

from .config import (
    QualityEngineConfig,
    OperationMode,
    CacheStrategy,
    PerformanceConfig,
    SecurityConfig,
    QualityThresholds,
    DimensionWeights,
    PRESETS
)

from .models import (
    QualityConfig,
    QualityReport,
    DimensionScore,
    QualityDimension,
    QualityIssue,
    SeverityLevel
)

from .analyzer_unified import UnifiedQualityAnalyzer

from .dimensions_unified import (
    UnifiedCompletenessAnalyzer,
    UnifiedClarityAnalyzer,
    UnifiedStructureAnalyzer,
    UnifiedAccuracyAnalyzer,
    UnifiedFormattingAnalyzer
)

from .base_dimension import (
    BaseDimensionAnalyzer,
    PatternBasedAnalyzer,
    StructuralAnalyzer,
    MetricsBasedAnalyzer,
    AnalysisContext
)

from .scoring import QualityScorer, ScoringMetrics

from .validators import (
    DocumentValidator,
    MarkdownValidator,
    CodeDocumentValidator
)

from .exceptions import (
    QualityEngineError,
    QualityGateFailure,
    IntegrationError,
    DimensionAnalysisError
)

from .utils import (
    calculate_readability,
    extract_code_blocks,
    extract_sections,
    count_words,
    count_sentences,
    count_syllables,
    find_urls,
    find_images,
    calculate_hash,
    sanitize_regex,
    truncate_text,
    normalize_whitespace,
    detect_language,
    calculate_complexity,
    chunk_text,
    merge_issues,
    COMMON_PATTERNS
)

# Main API - Unified analyzer is the primary interface
QualityAnalyzer = UnifiedQualityAnalyzer

# Convenience function for quick analysis
def analyze_document(
    content: str,
    document_type: str = "markdown",
    mode: OperationMode = OperationMode.BALANCED
) -> QualityReport:
    """
    Convenience function for quick document analysis.
    
    Args:
        content: Document content to analyze
        document_type: Type of document
        mode: Operation mode for analysis
        
    Returns:
        Quality report
    """
    config = QualityEngineConfig.from_mode(mode)
    analyzer = UnifiedQualityAnalyzer(config)
    
    with analyzer:
        return analyzer.analyze(content, document_type)


# Version information
__version__ = "3.0.0"
__author__ = "DevDocAI Team"

# Export main components
__all__ = [
    # Main analyzer
    'QualityAnalyzer',
    'UnifiedQualityAnalyzer',
    'analyze_document',
    
    # Configuration
    'QualityEngineConfig',
    'OperationMode',
    'CacheStrategy',
    'PerformanceConfig',
    'SecurityConfig',
    'QualityThresholds',
    'DimensionWeights',
    'PRESETS',
    
    # Models
    'QualityConfig',
    'QualityReport',
    'DimensionScore',
    'QualityDimension',
    'QualityIssue',
    'SeverityLevel',
    
    # Dimension analyzers
    'UnifiedCompletenessAnalyzer',
    'UnifiedClarityAnalyzer',
    'UnifiedStructureAnalyzer',
    'UnifiedAccuracyAnalyzer',
    'UnifiedFormattingAnalyzer',
    
    # Base classes
    'BaseDimensionAnalyzer',
    'PatternBasedAnalyzer',
    'StructuralAnalyzer',
    'MetricsBasedAnalyzer',
    'AnalysisContext',
    
    # Components
    'QualityScorer',
    'ScoringMetrics',
    'DocumentValidator',
    'MarkdownValidator',
    'CodeDocumentValidator',
    
    # Exceptions
    'QualityEngineError',
    'QualityGateFailure',
    'IntegrationError',
    'DimensionAnalysisError',
    
    # Utilities
    'calculate_readability',
    'extract_code_blocks',
    'extract_sections',
    'count_words',
    'find_urls',
    'calculate_complexity',
    'COMMON_PATTERNS',
    
    # Version
    '__version__',
]