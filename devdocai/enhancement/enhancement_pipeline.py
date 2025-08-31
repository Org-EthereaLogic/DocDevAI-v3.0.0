"""
Main Enhancement Pipeline orchestrator for M009.

Coordinates iterative document improvement using multiple strategies,
quality tracking, and cost optimization.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json

# Import configuration
from .config import (
    EnhancementSettings,
    OperationMode,
    EnhancementType,
    PipelineConfig
)

# Import module components (will be implemented)
from .enhancement_strategies import StrategyFactory, EnhancementStrategy
from .quality_tracker import QualityTracker, QualityMetrics
from .enhancement_history import EnhancementHistory, EnhancementVersion
from .cost_optimizer import CostOptimizer, CostMetrics

# Import integrated modules
try:
    from devdocai.miair.engine_unified import UnifiedMIAIREngine
    from devdocai.quality.analyzer_unified import UnifiedQualityAnalyzer
    from devdocai.llm_adapter.adapter_unified import UnifiedLLMAdapter
    from devdocai.generator.core.document_generator import DocumentGenerator
    INTEGRATIONS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Some integrations not available: {e}")
    INTEGRATIONS_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class DocumentContent:
    """Represents document content for enhancement."""
    
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    doc_type: str = "markdown"
    language: str = "en"
    version: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "metadata": self.metadata,
            "doc_type": self.doc_type,
            "language": self.language,
            "version": self.version,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class EnhancementResult:
    """Result of document enhancement."""
    
    original_content: str
    enhanced_content: str
    improvements: List[Dict[str, Any]]
    quality_before: float
    quality_after: float
    improvement_percentage: float
    strategies_applied: List[str]
    total_cost: float
    processing_time: float
    enhancement_passes: int
    success: bool
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "original_content": self.original_content[:500] + "..." if len(self.original_content) > 500 else self.original_content,
            "enhanced_content": self.enhanced_content[:500] + "..." if len(self.enhanced_content) > 500 else self.enhanced_content,
            "improvements": self.improvements,
            "quality_before": self.quality_before,
            "quality_after": self.quality_after,
            "improvement_percentage": self.improvement_percentage,
            "strategies_applied": self.strategies_applied,
            "total_cost": self.total_cost,
            "processing_time": self.processing_time,
            "enhancement_passes": self.enhancement_passes,
            "success": self.success,
            "errors": self.errors,
            "metadata": self.metadata
        }


@dataclass
class EnhancementConfig:
    """Configuration for enhancement operation."""
    
    strategies: List[EnhancementType] = field(default_factory=lambda: [
        EnhancementType.CLARITY,
        EnhancementType.COMPLETENESS,
        EnhancementType.READABILITY
    ])
    max_passes: int = 5
    quality_threshold: float = 0.8
    improvement_threshold: float = 0.05
    cost_limit: float = 0.50
    timeout: int = 300
    parallel: bool = True
    preserve_style: bool = True
    selective_enhancement: Optional[List[str]] = None  # Enhance only specific sections
    
    @classmethod
    def from_settings(cls, settings: EnhancementSettings) -> 'EnhancementConfig':
        """Create config from settings."""
        enabled_strategies = [
            strategy_type
            for strategy_type, config in settings.strategies.items()
            if config.enabled
        ]
        
        return cls(
            strategies=enabled_strategies,
            max_passes=settings.pipeline.max_enhancement_passes,
            quality_threshold=0.8,
            improvement_threshold=settings.pipeline.min_improvement_threshold,
            cost_limit=settings.pipeline.max_cost_per_document,
            timeout=settings.pipeline.timeout_seconds,
            parallel=settings.pipeline.parallel_processing
        )


class EnhancementPipeline:
    """
    Main enhancement pipeline orchestrator.
    
    Coordinates iterative document improvement using multiple strategies,
    quality tracking, and cost optimization.
    """
    
    def __init__(
        self,
        settings: Optional[EnhancementSettings] = None,
        llm_adapter: Optional[Any] = None,
        quality_analyzer: Optional[Any] = None,
        miair_engine: Optional[Any] = None
    ):
        """Initialize the enhancement pipeline."""
        self.settings = settings or EnhancementSettings()
        self.config = PipelineConfig()
        
        # Initialize components
        self.strategy_factory = StrategyFactory(self.settings)
        self.quality_tracker = QualityTracker()
        self.history = EnhancementHistory()
        self.cost_optimizer = CostOptimizer(self.settings.pipeline)
        
        # Initialize integrations
        self._init_integrations(llm_adapter, quality_analyzer, miair_engine)
        
        # Performance tracking
        self._executor = ThreadPoolExecutor(
            max_workers=self.config.max_concurrent_enhancements
        )
        self._cache: Dict[str, EnhancementResult] = {}
        
        logger.info(f"Enhancement Pipeline initialized with mode: {self.settings.operation_mode}")
    
    def _init_integrations(
        self,
        llm_adapter: Optional[Any],
        quality_analyzer: Optional[Any],
        miair_engine: Optional[Any]
    ) -> None:
        """Initialize module integrations."""
        # LLM Adapter (M008)
        if llm_adapter:
            self.llm_adapter = llm_adapter
        elif INTEGRATIONS_AVAILABLE:
            try:
                self.llm_adapter = UnifiedLLMAdapter(
                    mode="PERFORMANCE",  # Use performance mode for efficiency
                    config=self.settings.llm_settings
                )
            except Exception as e:
                logger.warning(f"Failed to initialize LLM adapter: {e}")
                self.llm_adapter = None
        else:
            self.llm_adapter = None
        
        # Quality Analyzer (M005)
        if quality_analyzer:
            self.quality_analyzer = quality_analyzer
        elif INTEGRATIONS_AVAILABLE:
            try:
                self.quality_analyzer = UnifiedQualityAnalyzer(mode="OPTIMIZED")
            except Exception as e:
                logger.warning(f"Failed to initialize quality analyzer: {e}")
                self.quality_analyzer = None
        else:
            self.quality_analyzer = None
        
        # MIAIR Engine (M003)
        if miair_engine:
            self.miair_engine = miair_engine
        elif INTEGRATIONS_AVAILABLE:
            try:
                self.miair_engine = UnifiedMIAIREngine(mode="OPTIMIZED")
            except Exception as e:
                logger.warning(f"Failed to initialize MIAIR engine: {e}")
                self.miair_engine = None
        else:
            self.miair_engine = None
    
    async def enhance_document(
        self,
        document: Union[str, DocumentContent],
        config: Optional[EnhancementConfig] = None
    ) -> EnhancementResult:
        """
        Enhance a single document iteratively.
        
        Args:
            document: Document content or DocumentContent object
            config: Enhancement configuration
            
        Returns:
            EnhancementResult with enhanced content and metrics
        """
        start_time = time.time()
        config = config or EnhancementConfig.from_settings(self.settings)
        
        # Convert string to DocumentContent if needed
        if isinstance(document, str):
            document = DocumentContent(content=document)
        
        # Check cache
        cache_key = self._get_cache_key(document, config)
        if self.settings.pipeline.use_cache and cache_key in self._cache:
            logger.info("Returning cached enhancement result")
            return self._cache[cache_key]
        
        # Initialize tracking
        original_content = document.content
        current_content = original_content
        enhancement_passes = 0
        total_cost = 0.0
        improvements = []
        strategies_applied = []
        errors = []
        
        try:
            # Measure initial quality
            initial_quality = await self._measure_quality(original_content)
            current_quality = initial_quality
            
            # Create initial version in history
            self.history.add_version(
                content=original_content,
                quality_score=initial_quality,
                metadata={"version": "original"}
            )
            
            # Get strategies based on priority
            strategies = self._get_ordered_strategies(config.strategies)
            
            # Enhancement loop
            for pass_num in range(1, config.max_passes + 1):
                if pass_num > 1:
                    # Check if we've reached quality threshold
                    if current_quality >= config.quality_threshold:
                        logger.info(f"Quality threshold reached: {current_quality:.2f}")
                        break
                    
                    # Check cost limit
                    if total_cost >= config.cost_limit:
                        logger.warning(f"Cost limit reached: ${total_cost:.2f}")
                        break
                
                logger.info(f"Enhancement pass {pass_num}/{config.max_passes}")
                
                # Apply strategies
                pass_improvements = []
                pass_cost = 0.0
                
                for strategy in strategies:
                    if strategy.name not in strategies_applied:
                        # Apply strategy
                        result = await self._apply_strategy(
                            strategy,
                            current_content,
                            document.metadata
                        )
                        
                        if result["success"]:
                            current_content = result["enhanced_content"]
                            pass_improvements.append(result["improvement"])
                            pass_cost += result["cost"]
                            strategies_applied.append(strategy.name)
                            
                            # Track in history
                            self.history.add_version(
                                content=current_content,
                                quality_score=result.get("quality", current_quality),
                                metadata={
                                    "pass": pass_num,
                                    "strategy": strategy.name,
                                    "improvement": result["improvement"]
                                }
                            )
                        else:
                            errors.append(f"Strategy {strategy.name} failed: {result.get('error', 'Unknown error')}")
                
                # Measure quality after pass
                new_quality = await self._measure_quality(current_content)
                quality_improvement = new_quality - current_quality
                
                # Check if improvement is significant
                if quality_improvement < config.improvement_threshold:
                    logger.info(f"Improvement below threshold: {quality_improvement:.3f}")
                    if self.settings.pipeline.rollback_on_degradation and quality_improvement < 0:
                        # Rollback to previous version
                        current_content = self.history.get_previous_version().content
                        logger.warning("Rolled back due to quality degradation")
                    else:
                        # Stop if no significant improvement
                        break
                
                current_quality = new_quality
                total_cost += pass_cost
                improvements.extend(pass_improvements)
                enhancement_passes = pass_num
                
                # MIAIR optimization if enabled
                if self.settings.pipeline.use_miair_optimization and self.miair_engine:
                    current_content = await self._apply_miair_optimization(current_content)
            
            # Calculate final metrics
            final_quality = await self._measure_quality(current_content)
            improvement_percentage = ((final_quality - initial_quality) / initial_quality) * 100
            
            # Create result
            result = EnhancementResult(
                original_content=original_content,
                enhanced_content=current_content,
                improvements=improvements,
                quality_before=initial_quality,
                quality_after=final_quality,
                improvement_percentage=improvement_percentage,
                strategies_applied=strategies_applied,
                total_cost=total_cost,
                processing_time=time.time() - start_time,
                enhancement_passes=enhancement_passes,
                success=True,
                errors=errors,
                metadata={
                    "document_type": document.doc_type,
                    "language": document.language,
                    "config": config.__dict__
                }
            )
            
            # Cache result
            if self.settings.pipeline.use_cache:
                self._cache[cache_key] = result
            
            # Log metrics
            logger.info(f"Enhancement complete: {improvement_percentage:.1f}% improvement, "
                       f"{enhancement_passes} passes, ${total_cost:.2f} cost")
            
            return result
            
        except Exception as e:
            logger.error(f"Enhancement failed: {e}")
            return EnhancementResult(
                original_content=original_content,
                enhanced_content=current_content,
                improvements=improvements,
                quality_before=initial_quality if 'initial_quality' in locals() else 0,
                quality_after=current_quality if 'current_quality' in locals() else 0,
                improvement_percentage=0,
                strategies_applied=strategies_applied,
                total_cost=total_cost,
                processing_time=time.time() - start_time,
                enhancement_passes=enhancement_passes,
                success=False,
                errors=errors + [str(e)]
            )
    
    async def enhance_batch(
        self,
        documents: List[Union[str, DocumentContent]],
        config: Optional[EnhancementConfig] = None
    ) -> List[EnhancementResult]:
        """
        Enhance multiple documents in batch.
        
        Args:
            documents: List of documents to enhance
            config: Enhancement configuration
            
        Returns:
            List of EnhancementResult objects
        """
        config = config or EnhancementConfig.from_settings(self.settings)
        
        if config.parallel and len(documents) > 1:
            # Process in parallel
            tasks = [
                self.enhance_document(doc, config)
                for doc in documents
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle exceptions
            final_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Batch enhancement failed for document {i}: {result}")
                    # Create failure result
                    doc_content = documents[i].content if isinstance(documents[i], DocumentContent) else documents[i]
                    final_results.append(EnhancementResult(
                        original_content=doc_content,
                        enhanced_content=doc_content,
                        improvements=[],
                        quality_before=0,
                        quality_after=0,
                        improvement_percentage=0,
                        strategies_applied=[],
                        total_cost=0,
                        processing_time=0,
                        enhancement_passes=0,
                        success=False,
                        errors=[str(result)]
                    ))
                else:
                    final_results.append(result)
            
            return final_results
        else:
            # Process sequentially
            results = []
            for doc in documents:
                result = await self.enhance_document(doc, config)
                results.append(result)
            return results
    
    async def _measure_quality(self, content: str) -> float:
        """Measure document quality using the quality analyzer."""
        if self.quality_analyzer:
            try:
                analysis = await self.quality_analyzer.analyze({"content": content})
                return analysis.get("overall_score", 0.5)
            except Exception as e:
                logger.warning(f"Quality measurement failed: {e}")
                return 0.5
        else:
            # Simple fallback quality measurement
            return self._simple_quality_score(content)
    
    def _simple_quality_score(self, content: str) -> float:
        """Simple quality scoring fallback."""
        score = 0.5  # Base score
        
        # Length bonus
        if 100 < len(content) < 10000:
            score += 0.1
        
        # Structure bonus (paragraphs)
        if content.count('\n\n') > 2:
            score += 0.1
        
        # Headers bonus (markdown)
        if content.count('#') > 0:
            score += 0.1
        
        # Sentences
        if content.count('.') > 5:
            score += 0.1
        
        # Cap at 1.0
        return min(score, 1.0)
    
    async def _apply_strategy(
        self,
        strategy: EnhancementStrategy,
        content: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply a single enhancement strategy."""
        try:
            # Use strategy to enhance content
            enhanced = await strategy.enhance(content, metadata)
            
            # Measure quality improvement
            quality = await self._measure_quality(enhanced)
            
            # Calculate cost (simplified for now)
            cost = self.cost_optimizer.calculate_cost(
                content_length=len(content),
                strategy_name=strategy.name
            )
            
            return {
                "success": True,
                "enhanced_content": enhanced,
                "improvement": {
                    "strategy": strategy.name,
                    "description": f"Applied {strategy.name} enhancement",
                    "quality_delta": quality - await self._measure_quality(content)
                },
                "quality": quality,
                "cost": cost
            }
        except Exception as e:
            logger.error(f"Strategy {strategy.name} failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "enhanced_content": content,
                "cost": 0
            }
    
    async def _apply_miair_optimization(self, content: str) -> str:
        """Apply MIAIR entropy optimization."""
        if self.miair_engine:
            try:
                result = await self.miair_engine.optimize_document(
                    content=content,
                    target_quality=0.9
                )
                return result.get("optimized_content", content)
            except Exception as e:
                logger.warning(f"MIAIR optimization failed: {e}")
        return content
    
    def _get_ordered_strategies(
        self,
        strategy_types: List[EnhancementType]
    ) -> List[EnhancementStrategy]:
        """Get strategies ordered by priority."""
        strategies = []
        for strategy_type in strategy_types:
            if strategy_type in self.settings.strategies:
                config = self.settings.strategies[strategy_type]
                if config.enabled:
                    strategy = self.strategy_factory.create_strategy(strategy_type)
                    strategies.append((config.priority, strategy))
        
        # Sort by priority (lower number = higher priority)
        strategies.sort(key=lambda x: x[0])
        return [s[1] for s in strategies]
    
    def _get_cache_key(
        self,
        document: DocumentContent,
        config: EnhancementConfig
    ) -> str:
        """Generate cache key for document and config."""
        import hashlib
        content_hash = hashlib.md5(document.content.encode()).hexdigest()
        config_str = str(sorted(config.__dict__.items()))
        config_hash = hashlib.md5(config_str.encode()).hexdigest()
        return f"{content_hash}_{config_hash}"
    
    def get_enhancement_history(self, doc_id: Optional[str] = None) -> List[EnhancementVersion]:
        """Get enhancement history for a document."""
        return self.history.get_versions(doc_id)
    
    def compare_versions(
        self,
        version1: int,
        version2: int,
        doc_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Compare two enhancement versions."""
        return self.history.compare_versions(version1, version2, doc_id)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of enhancement metrics."""
        return {
            "total_documents": len(self._cache),
            "average_improvement": self.quality_tracker.get_average_improvement(),
            "total_cost": self.cost_optimizer.get_total_cost(),
            "strategies_usage": self.strategy_factory.get_usage_stats(),
            "cache_hit_rate": self._calculate_cache_hit_rate()
        }
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        # This would track actual hits/misses in production
        return len(self._cache) * 0.35 if self._cache else 0.0  # Simulated 35% hit rate
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        self._executor.shutdown(wait=True)
        self._cache.clear()
        if hasattr(self.llm_adapter, 'cleanup'):
            await self.llm_adapter.cleanup()
        logger.info("Enhancement Pipeline cleaned up")