"""
M009 Enhancement Pipeline - Iterative Document Improvement System.

This module provides iterative document enhancement capabilities using
multi-LLM synthesis, quality tracking, and intelligent optimization strategies.
"""

from .enhancement_pipeline import (
    EnhancementPipeline,
    EnhancementResult,
    EnhancementConfig
)

from .enhancement_strategies import (
    EnhancementStrategy,
    ClarityStrategy,
    CompletenessStrategy,
    ConsistencyStrategy,
    AccuracyStrategy,
    ReadabilityStrategy,
    StrategyFactory
)

from .quality_tracker import (
    QualityTracker,
    QualityMetrics,
    ImprovementReport
)

from .enhancement_history import (
    EnhancementHistory,
    EnhancementVersion,
    VersionComparison
)

from .cost_optimizer import (
    CostOptimizer,
    CostMetrics,
    OptimizationResult
)

from .config import (
    EnhancementSettings,
    StrategyConfig,
    PipelineConfig,
    OperationMode
)

__all__ = [
    # Pipeline
    'EnhancementPipeline',
    'EnhancementResult',
    'EnhancementConfig',
    
    # Strategies
    'EnhancementStrategy',
    'ClarityStrategy',
    'CompletenessStrategy',
    'ConsistencyStrategy',
    'AccuracyStrategy',
    'ReadabilityStrategy',
    'StrategyFactory',
    
    # Quality Tracking
    'QualityTracker',
    'QualityMetrics',
    'ImprovementReport',
    
    # History Management
    'EnhancementHistory',
    'EnhancementVersion',
    'VersionComparison',
    
    # Cost Optimization
    'CostOptimizer',
    'CostMetrics',
    'OptimizationResult',
    
    # Configuration
    'EnhancementSettings',
    'StrategyConfig',
    'PipelineConfig',
    'OperationMode'
]

__version__ = '1.0.0'