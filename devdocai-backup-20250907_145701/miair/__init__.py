"""
M003: MIAIR Engine
Meta-Iterative AI Refinement engine for documentation quality optimization.

This module implements mathematical optimization using entropy calculations:
- Entropy threshold: 0.35
- Target entropy: 0.15
- Formula: S = -Σ[p(xi) × log2(p(xi))] × f(Tx)

Integration with:
- M001: Configuration Manager for settings
- M002: Local Storage for document management
- M008: LLM Adapter for AI enhancement (future)
- M009: Enhancement Pipeline for quality improvement (future)

Pass 1 Implementation Features:
- Core Shannon entropy calculation
- Semantic element extraction and analysis
- 4 operation modes (BASIC, PERFORMANCE, SECURE, ENTERPRISE)
- Quality metrics and improvement measurement
- Document optimization strategies
- M001/M002 integration
"""

from typing import List, Dict, Optional, Tuple
import logging

# Import core components
from .engine_unified import MIAIREngineUnified, create_miair_engine, optimize_document, analyze_document
from .entropy_calculator import EntropyCalculator
from .semantic_analyzer import SemanticAnalyzer
from .quality_metrics import QualityMetrics
from .optimization_strategies import create_strategy, OptimizationStrategy
from .models import (
    # Core models
    Document, 
    OperationMode,
    DocumentType,
    ElementType,
    SemanticElement,
    
    # Result models
    OptimizationResult,
    AnalysisResult,
    QualityScore,
    ValidationResult,
    CachedResult,
    
    # Configuration
    MIAIRConfig,
    
    # Type aliases
    DocumentID,
    EntropyScore,
    QualityPercentage,
    ImprovementPercentage
)

logger = logging.getLogger(__name__)

__version__ = "3.0.0"
__module_id__ = "M003"
__module_name__ = "MIAIR Engine"

# Public API exports
__all__ = [
    # Main engine
    'MIAIREngineUnified',
    'create_miair_engine',
    'optimize_document',
    'analyze_document',
    
    # Core components
    'EntropyCalculator',
    'SemanticAnalyzer', 
    'QualityMetrics',
    'OptimizationStrategy',
    'create_strategy',
    
    # Models and enums
    'Document',
    'OperationMode',
    'DocumentType', 
    'ElementType',
    'SemanticElement',
    
    # Results
    'OptimizationResult',
    'AnalysisResult',
    'QualityScore',
    'ValidationResult',
    'CachedResult',
    
    # Configuration
    'MIAIRConfig',
    
    # Type aliases
    'DocumentID',
    'EntropyScore',
    'QualityPercentage',
    'ImprovementPercentage',
    
    # Module metadata
    '__version__',
    '__module_id__',
    '__module_name__'
]

# Initialize module
logger.info(f"M003 MIAIR Engine v{__version__} loaded successfully")
logger.debug(f"Available operation modes: {[mode.value for mode in OperationMode]}")
logger.debug(f"Mathematical constants: entropy_threshold=0.35, target_entropy=0.15, quality_gate=85%")