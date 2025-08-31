"""
M009 Enhancement Pipeline - Unified Iterative Document Improvement System.

Pass 4: Refactoring - Consolidated architecture with mode-based operation.

This module provides iterative document enhancement capabilities with:
- Unified pipeline supporting BASIC, PERFORMANCE, SECURE, and ENTERPRISE modes
- Consolidated caching system with intelligent feature selection
- Mode-driven configuration with backward compatibility
- 40-50% code reduction while preserving all functionality
"""

# Import unified components (preferred)
from .enhancement_unified import (
    UnifiedEnhancementPipeline,
    UnifiedPipelineMetrics,
    create_unified_pipeline,
    create_basic_pipeline,
    create_performance_pipeline,
    create_secure_pipeline,
    create_enterprise_pipeline
)

from .config_unified import (
    UnifiedEnhancementSettings,
    UnifiedOperationMode,
    UnifiedStrategyConfig,
    UnifiedPipelineConfig,
    create_basic_settings,
    create_performance_settings,
    create_secure_settings,
    create_enterprise_settings
)

from .cache_unified import (
    UnifiedCache,
    UnifiedCacheMode,
    UnifiedCacheConfig,
    create_unified_cache,
    create_basic_cache,
    create_performance_cache,
    create_secure_cache,
    create_enterprise_cache
)

# Import core components (still used by unified system)
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

# Backward compatibility imports (original interfaces)
from .enhancement_pipeline import (
    EnhancementPipeline,
    EnhancementResult,
    EnhancementConfig,
    DocumentContent
)

from .config import (
    EnhancementSettings,
    StrategyConfig,
    PipelineConfig,
    OperationMode,
    EnhancementType
)

# Security components (for SECURE/ENTERPRISE modes)
try:
    from .pipeline_secure import SecurityContext, SecurityOperationResult
    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False

__all__ = [
    # Unified Components (Preferred)
    'UnifiedEnhancementPipeline',
    'UnifiedPipelineMetrics',
    'create_unified_pipeline',
    'create_basic_pipeline',
    'create_performance_pipeline', 
    'create_secure_pipeline',
    'create_enterprise_pipeline',
    
    # Unified Configuration
    'UnifiedEnhancementSettings',
    'UnifiedOperationMode',
    'UnifiedStrategyConfig',
    'UnifiedPipelineConfig',
    'create_basic_settings',
    'create_performance_settings',
    'create_secure_settings',
    'create_enterprise_settings',
    
    # Unified Cache
    'UnifiedCache',
    'UnifiedCacheMode',
    'UnifiedCacheConfig',
    'create_unified_cache',
    'create_basic_cache',
    'create_performance_cache',
    'create_secure_cache',
    'create_enterprise_cache',
    
    # Core Components
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
    
    # Backward Compatibility
    'EnhancementPipeline',
    'EnhancementResult',
    'EnhancementConfig',
    'DocumentContent',
    'EnhancementSettings',
    'StrategyConfig',
    'PipelineConfig',
    'OperationMode',
    'EnhancementType'
]

# Add security components if available
if SECURITY_AVAILABLE:
    __all__.extend(['SecurityContext', 'SecurityOperationResult'])

__version__ = '1.0.0'