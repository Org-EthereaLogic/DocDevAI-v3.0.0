"""
M003 MIAIR Engine - Final Unified Implementation (Pass 4 Refactoring)

Simplified unified MIAIR Engine that consolidates all functionality while
maintaining compatibility with existing models.
"""

import asyncio
import hashlib
import logging
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from .models import (
    Document, OperationMode, OptimizationResult, AnalysisResult,
    QualityScore, SemanticElement
)
from .config_unified import UnifiedMIAIRConfig
from .entropy_calculator import EntropyCalculator
from .semantic_analyzer import SemanticAnalyzer
from .quality_metrics import QualityMetrics
from .optimization_strategies import create_strategy

# Try to import M001/M002 integrations
try:
    from ..core.config import ConfigurationManager
except ImportError:
    ConfigurationManager = None

try:
    from ..storage.storage_manager_unified import UnifiedStorageManager
except ImportError:
    UnifiedStorageManager = None


logger = logging.getLogger(__name__)


class MIAIREngineUnified:
    """
    Unified MIAIR Engine - Pass 4 Refactoring.
    
    Consolidates engine_unified.py, performance_optimized.py, and secure_engine.py
    into a single implementation with mode-based behavior.
    
    Modes:
    - BASIC: Core functionality only
    - PERFORMANCE: Optimized with caching and parallel processing
    - SECURE: Security hardened with validation
    - ENTERPRISE: All features enabled
    """
    
    def __init__(
        self,
        mode: OperationMode = OperationMode.BASIC,
        config_manager: Optional['ConfigurationManager'] = None,
        storage_manager: Optional['UnifiedStorageManager'] = None,
        config: Optional[UnifiedMIAIRConfig] = None
    ):
        """Initialize unified MIAIR Engine."""
        self.mode = mode
        self.logger = logging.getLogger(f"{__name__}.{mode.value}")
        
        # Integration points
        self.config_manager = config_manager
        self.storage_manager = storage_manager
        
        # Load configuration
        if config:
            self.config = config
        elif mode == OperationMode.BASIC:
            self.config = UnifiedMIAIRConfig.for_basic_mode()
        elif mode == OperationMode.PERFORMANCE:
            self.config = UnifiedMIAIRConfig.for_performance_mode()
        elif mode == OperationMode.SECURE:
            self.config = UnifiedMIAIRConfig.for_secure_mode()
        elif mode == OperationMode.ENTERPRISE:
            self.config = UnifiedMIAIRConfig.for_enterprise_mode()
        else:
            self.config = UnifiedMIAIRConfig()
        
        # Core components
        self.entropy_calculator = EntropyCalculator()
        self.semantic_analyzer = SemanticAnalyzer()
        self.quality_metrics = QualityMetrics()
        
        # Simple cache for performance modes
        self.cache: Dict[str, Any] = {} if self.config.enable_caching else None
        
        # Metrics tracking
        self.total_documents_processed = 0
        self.total_processing_time = 0.0
        
        self.logger.info(f"MIAIR Engine initialized in {mode.value} mode")
    
    async def analyze_document(
        self,
        document: Document,
        include_semantic: bool = True
    ) -> AnalysisResult:
        """
        Analyze document quality and structure.
        
        Returns AnalysisResult compatible with existing models.
        """
        start_time = time.perf_counter()
        
        # Check cache if enabled
        cache_key = None
        if self.config.enable_caching and self.cache is not None:
            cache_key = self._generate_cache_key(document)
            if cache_key in self.cache:
                self.logger.debug(f"Cache hit for document {document.id}")
                return self.cache[cache_key]
        
        # Calculate entropy
        entropy = self.entropy_calculator.calculate_entropy(document)
        
        # Semantic analysis
        semantic_elements = []
        if include_semantic:
            semantic_elements = self.semantic_analyzer.extract_semantic_elements(document)
        
        # Calculate quality score
        quality_score = self.quality_metrics.calculate_quality_score(
            document,
            semantic_elements
        )
        
        # Determine if meets quality gate
        meets_gate = quality_score.overall >= self.config.quality_gate
        
        # Calculate improvement potential
        improvement_potential = max(0, 100.0 - quality_score.overall)
        
        # Create result
        result = AnalysisResult(
            entropy=entropy,
            quality_score=quality_score,
            semantic_elements=semantic_elements,
            improvement_potential=improvement_potential,
            meets_quality_gate=meets_gate,
            patterns={}
        )
        
        # Cache result if enabled
        if cache_key and self.cache is not None:
            self.cache[cache_key] = result
        
        # Update metrics
        self.total_documents_processed += 1
        self.total_processing_time += (time.perf_counter() - start_time)
        
        return result
    
    async def optimize_document(
        self,
        document: Document,
        target_quality: float = 85.0,
        max_iterations: int = 10
    ) -> OptimizationResult:
        """
        Optimize document to achieve target quality.
        
        Returns OptimizationResult compatible with existing models.
        """
        start_time = time.perf_counter()
        
        # Initial analysis
        initial_analysis = await self.analyze_document(document)
        initial_entropy = initial_analysis.entropy
        
        # Check if already meets target
        if initial_analysis.quality_score.overall >= target_quality:
            return OptimizationResult(
                document=document,
                initial_entropy=initial_entropy,
                final_entropy=initial_entropy,
                improvement=0.0,
                iterations=0,
                quality_score=initial_analysis.quality_score,
                execution_time_ms=(time.perf_counter() - start_time) * 1000
            )
        
        # Create optimization strategy
        strategy = create_strategy(document.type)
        
        # Optimization loop
        current_doc = document
        iterations = 0
        
        for i in range(max_iterations):
            iterations = i + 1
            
            # Apply optimization
            optimized_content = strategy.optimize(
                current_doc.content,
                self._generate_suggestions(initial_analysis)
            )
            
            # Create new document with optimized content
            current_doc = Document(
                id=document.id,
                content=optimized_content,
                type=document.type,
                title=document.title,
                metadata=document.metadata
            )
            
            # Re-analyze
            analysis = await self.analyze_document(current_doc)
            
            # Check if target reached
            if analysis.quality_score.overall >= target_quality:
                break
        
        # Final analysis
        final_analysis = await self.analyze_document(current_doc)
        
        # Calculate improvement
        improvement = final_analysis.quality_score.overall - initial_analysis.quality_score.overall
        
        return OptimizationResult(
            document=current_doc,
            initial_entropy=initial_entropy,
            final_entropy=final_analysis.entropy,
            improvement=improvement,
            iterations=iterations,
            quality_score=final_analysis.quality_score,
            execution_time_ms=(time.perf_counter() - start_time) * 1000
        )
    
    async def batch_process(
        self,
        documents: List[Document],
        operation: str = 'analyze'
    ) -> List[Any]:
        """Process multiple documents in batch."""
        results = []
        
        if self.config.enable_parallel and self.mode in [OperationMode.PERFORMANCE, OperationMode.ENTERPRISE]:
            # Parallel processing
            if operation == 'analyze':
                tasks = [self.analyze_document(doc) for doc in documents]
            else:
                tasks = [self.optimize_document(doc) for doc in documents]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions
            results = [r for r in results if not isinstance(r, Exception)]
        else:
            # Sequential processing
            for doc in documents:
                try:
                    if operation == 'analyze':
                        result = await self.analyze_document(doc)
                    else:
                        result = await self.optimize_document(doc)
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Error processing document {doc.id}: {e}")
        
        return results
    
    def _generate_cache_key(self, document: Document) -> str:
        """Generate cache key for document."""
        content_hash = hashlib.md5(document.content.encode()).hexdigest()
        return f"{document.type.value}:{content_hash}"
    
    def _generate_suggestions(self, analysis: AnalysisResult) -> List[str]:
        """Generate improvement suggestions from analysis."""
        suggestions = []
        
        if analysis.entropy > self.config.entropy_threshold:
            suggestions.append(f"Reduce entropy from {analysis.entropy:.3f} to below {self.config.entropy_threshold}")
        
        if analysis.quality_score.completeness < 80:
            suggestions.append("Improve content completeness")
        
        if analysis.quality_score.clarity < 70:
            suggestions.append("Improve clarity and readability")
        
        if analysis.quality_score.consistency < 75:
            suggestions.append("Ensure consistent terminology")
        
        return suggestions
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get engine performance metrics."""
        avg_time = self.total_processing_time / max(1, self.total_documents_processed)
        
        return {
            'mode': self.mode.value,
            'total_documents': self.total_documents_processed,
            'total_time': self.total_processing_time,
            'avg_time_per_doc': avg_time,
            'throughput_per_minute': (self.total_documents_processed / max(0.001, self.total_processing_time)) * 60 if self.total_processing_time > 0 else 0,
            'cache_size': len(self.cache) if self.cache else 0
        }
    
    def reset_metrics(self) -> None:
        """Reset performance metrics."""
        self.total_documents_processed = 0
        self.total_processing_time = 0.0
        if self.cache:
            self.cache.clear()
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the engine."""
        self.logger.info(f"Shutting down MIAIR Engine ({self.mode.value} mode)")
        
        # Clear cache
        if self.cache:
            self.cache.clear()
        
        # Log final metrics
        metrics = self.get_metrics()
        self.logger.info(f"Final metrics: {metrics}")


# Factory functions for easy instantiation
def create_basic_engine(**kwargs) -> MIAIREngineUnified:
    """Create engine in BASIC mode."""
    return MIAIREngineUnified(mode=OperationMode.BASIC, **kwargs)


def create_performance_engine(**kwargs) -> MIAIREngineUnified:
    """Create engine in PERFORMANCE mode."""
    return MIAIREngineUnified(mode=OperationMode.PERFORMANCE, **kwargs)


def create_secure_engine(**kwargs) -> MIAIREngineUnified:
    """Create engine in SECURE mode."""
    return MIAIREngineUnified(mode=OperationMode.SECURE, **kwargs)


def create_enterprise_engine(**kwargs) -> MIAIREngineUnified:
    """Create engine in ENTERPRISE mode."""
    return MIAIREngineUnified(mode=OperationMode.ENTERPRISE, **kwargs)