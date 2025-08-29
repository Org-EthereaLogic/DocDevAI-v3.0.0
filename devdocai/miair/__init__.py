"""
MIAIR Engine Module - Mathematical Intelligence for AI-Augmented Information Retrieval.

This module provides document analysis and optimization using Shannon entropy,
quality scoring, and pattern recognition.

The engine is now unified with three configurable modes:
- Standard: Balanced performance and features
- Optimized: High-performance parallel processing
- Secure: Enhanced security with validation and audit logging
"""

# Import unified engine (new primary interface)
from .engine_unified import (
    EngineMode,
    UnifiedMIAIRConfig,
    AnalysisResult,
    UnifiedMIAIREngine,
    create_engine,
    create_standard_engine,
    create_optimized_engine,
    create_secure_engine
)

# Import core components (kept for backward compatibility)
from .entropy import ShannonEntropyCalculator
from .scorer import QualityScorer, QualityMetrics, ScoringWeights
from .optimizer import MIAIROptimizer, OptimizationConfig, OptimizationResult
from .patterns import PatternRecognizer, PatternAnalysis, Pattern

# Import optimized components (kept for backward compatibility)
from .entropy_optimized import OptimizedShannonEntropyCalculator
from .scorer_optimized import OptimizedQualityScorer
from .patterns_optimized import OptimizedPatternRecognizer

# Import security components
from .validators import InputValidator, ValidationConfig, ValidationError
from .rate_limiter import RateLimiter, RateLimitConfig, RateLimitExceeded
from .secure_cache import SecureCache, SecureCacheConfig
from .audit import AuditLogger, AuditConfig, SecurityEventType, SeverityLevel

# Deprecated: Old engine imports (will be removed in v4.0.0)
import warnings

def _deprecated_engine_warning(engine_name: str):
    warnings.warn(
        f"{engine_name} is deprecated and will be removed in v4.0.0. "
        f"Use UnifiedMIAIREngine or create_engine() instead.",
        DeprecationWarning,
        stacklevel=2
    )

# Keep old imports for backward compatibility with deprecation warnings
try:
    from .engine import MIAIREngine as _OldMIAIREngine
    from .engine_optimized import OptimizedMIAIREngine as _OldOptimizedEngine
    from .engine_secure import SecureMIAIREngine as _OldSecureEngine
    
    class MIAIREngine(_OldMIAIREngine):
        """Deprecated: Use UnifiedMIAIREngine or create_standard_engine() instead."""
        def __init__(self, *args, **kwargs):
            _deprecated_engine_warning("MIAIREngine")
            super().__init__(*args, **kwargs)
    
    class OptimizedMIAIREngine(_OldOptimizedEngine):
        """Deprecated: Use UnifiedMIAIREngine or create_optimized_engine() instead."""
        def __init__(self, *args, **kwargs):
            _deprecated_engine_warning("OptimizedMIAIREngine")
            super().__init__(*args, **kwargs)
    
    class SecureMIAIREngine(_OldSecureEngine):
        """Deprecated: Use UnifiedMIAIREngine or create_secure_engine() instead."""
        def __init__(self, *args, **kwargs):
            _deprecated_engine_warning("SecureMIAIREngine")
            super().__init__(*args, **kwargs)
    
except ImportError:
    # Old engines not available (already removed)
    pass

__version__ = '3.0.0'

__all__ = [
    # Unified Engine (primary interface)
    'UnifiedMIAIREngine',
    'EngineMode',
    'UnifiedMIAIRConfig',
    'AnalysisResult',
    'create_engine',
    'create_standard_engine',
    'create_optimized_engine',
    'create_secure_engine',
    
    # Core Components
    'ShannonEntropyCalculator',
    'QualityScorer',
    'QualityMetrics',
    'ScoringWeights',
    'MIAIROptimizer',
    'OptimizationConfig',
    'OptimizationResult',
    'PatternRecognizer',
    'PatternAnalysis',
    'Pattern',
    
    # Optimized Components
    'OptimizedShannonEntropyCalculator',
    'OptimizedQualityScorer',
    'OptimizedPatternRecognizer',
    
    # Security Components
    'InputValidator',
    'ValidationConfig',
    'ValidationError',
    'RateLimiter',
    'RateLimitConfig',
    'RateLimitExceeded',
    'SecureCache',
    'SecureCacheConfig',
    'AuditLogger',
    'AuditConfig',
    'SecurityEventType',
    'SeverityLevel'
]

# Convenience: Set default engine creator
Engine = UnifiedMIAIREngine  # Alias for the main engine class