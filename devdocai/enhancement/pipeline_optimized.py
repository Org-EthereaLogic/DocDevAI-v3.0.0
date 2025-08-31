"""
Optimized Enhancement Pipeline for M009 with all performance optimizations.

Integrates advanced caching, batch processing, parallel execution,
and performance monitoring for maximum throughput.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple, Union, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import hashlib

# Import base pipeline
from .enhancement_pipeline import (
    EnhancementPipeline,
    DocumentContent,
    EnhancementResult,
    EnhancementConfig
)

# Import performance components
from .enhancement_cache import EnhancementCache
from .batch_optimizer import BatchOptimizer, StreamingBatchProcessor
from .parallel_executor import ParallelExecutor, AsyncParallelExecutor
from .performance_monitor import PerformanceMonitor

# Import other components
from .config import EnhancementSettings, OperationMode
from .enhancement_strategies import StrategyFactory
from .quality_tracker import QualityTracker
from .cost_optimizer import CostOptimizer

logger = logging.getLogger(__name__)


@dataclass
class OptimizationConfig:
    """Configuration for performance optimizations."""
    
    # Caching
    enable_caching: bool = True
    cache_size: int = 1000
    cache_memory_mb: int = 200
    use_semantic_cache: bool = True
    use_distributed_cache: bool = False
    redis_url: Optional[str] = None
    
    # Batching
    enable_batching: bool = True
    batch_size: int = 10
    max_batch_memory_mb: int = 50
    use_similarity_grouping: bool = True
    
    # Parallelization
    enable_parallel: bool = True
    max_workers: int = 4
    max_concurrent: int = 10
    use_process_pool: bool = False
    
    # Performance monitoring
    enable_monitoring: bool = True
    enable_bottleneck_detection: bool = True
    enable_adaptive_tuning: bool = False
    monitoring_interval: float = 1.0
    
    # Optimization modes
    fast_path_threshold: int = 500  # Characters for fast path
    lazy_loading: bool = True
    connection_pooling: bool = True
    request_coalescing: bool = True
    circuit_breaker: bool = True
    
    @classmethod
    def for_mode(cls, mode: str) -> 'OptimizationConfig':
        """Get configuration for specific mode."""
        configs = {
            "BASIC": cls(
                enable_caching=False,
                enable_batching=False,
                enable_parallel=False,
                enable_monitoring=False
            ),
            "PERFORMANCE": cls(
                enable_caching=True,
                cache_size=2000,
                enable_batching=True,
                batch_size=20,
                enable_parallel=True,
                max_workers=8,
                enable_monitoring=True
            ),
            "BALANCED": cls(
                enable_caching=True,
                cache_size=1000,
                enable_batching=True,
                batch_size=10,
                enable_parallel=True,
                max_workers=4,
                enable_monitoring=True
            ),
            "AGGRESSIVE": cls(
                enable_caching=True,
                cache_size=5000,
                cache_memory_mb=500,
                use_semantic_cache=True,
                use_distributed_cache=True,
                enable_batching=True,
                batch_size=50,
                enable_parallel=True,
                max_workers=16,
                max_concurrent=20,
                use_process_pool=True,
                enable_monitoring=True,
                enable_adaptive_tuning=True
            )
        }
        return configs.get(mode, cls())


class OptimizedEnhancementPipeline(EnhancementPipeline):
    """
    Optimized enhancement pipeline with performance features.
    
    Extends base pipeline with caching, batching, parallelization,
    and monitoring for maximum performance.
    """
    
    def __init__(
        self,
        settings: Optional[EnhancementSettings] = None,
        optimization_config: Optional[OptimizationConfig] = None,
        mode: str = "PERFORMANCE"
    ):
        """
        Initialize optimized pipeline.
        
        Args:
            settings: Enhancement settings
            optimization_config: Optimization configuration
            mode: Optimization mode
        """
        # Initialize base pipeline
        super().__init__(settings)
        
        # Optimization configuration
        self.opt_config = optimization_config or OptimizationConfig.for_mode(mode)
        
        # Initialize performance components
        self._init_performance_components()
        
        # Metrics
        self.total_enhanced = 0
        self.cache_hits = 0
        self.cache_misses = 0
        
        logger.info(f"Optimized pipeline initialized with mode: {mode}")
    
    def _init_performance_components(self) -> None:
        """Initialize performance optimization components."""
        # Cache
        if self.opt_config.enable_caching:
            self.cache = EnhancementCache(
                max_size=self.opt_config.cache_size,
                max_memory_mb=self.opt_config.cache_memory_mb,
                use_semantic=self.opt_config.use_semantic_cache,
                use_distributed=self.opt_config.use_distributed_cache,
                redis_url=self.opt_config.redis_url
            )
        else:
            self.cache = None
        
        # Batch optimizer
        if self.opt_config.enable_batching:
            self.batch_optimizer = BatchOptimizer(
                batch_size=self.opt_config.batch_size,
                max_workers=self.opt_config.max_workers,
                max_memory_mb=self.opt_config.max_batch_memory_mb,
                use_similarity_grouping=self.opt_config.use_similarity_grouping
            )
            self.streaming_processor = StreamingBatchProcessor(
                batch_size=self.opt_config.batch_size
            )
        else:
            self.batch_optimizer = None
            self.streaming_processor = None
        
        # Parallel executor
        if self.opt_config.enable_parallel:
            self.parallel_executor = ParallelExecutor(
                max_workers=self.opt_config.max_workers,
                use_processes=self.opt_config.use_process_pool
            )
            self.async_executor = AsyncParallelExecutor(
                max_concurrent=self.opt_config.max_concurrent
            )
        else:
            self.parallel_executor = None
            self.async_executor = None
        
        # Performance monitor
        if self.opt_config.enable_monitoring:
            self.monitor = PerformanceMonitor(
                enable_bottleneck_detection=self.opt_config.enable_bottleneck_detection,
                enable_adaptive_tuning=self.opt_config.enable_adaptive_tuning,
                monitoring_interval=self.opt_config.monitoring_interval
            )
        else:
            self.monitor = None
        
        # Connection pool for LLM adapter
        if self.opt_config.connection_pooling and self.llm_adapter:
            # Configure connection pooling in LLM adapter
            if hasattr(self.llm_adapter, 'configure_pooling'):
                self.llm_adapter.configure_pooling(
                    pool_size=self.opt_config.max_workers * 2,
                    max_overflow=10
                )
    
    async def enhance_document(
        self,
        document: Union[str, DocumentContent],
        config: Optional[EnhancementConfig] = None
    ) -> EnhancementResult:
        """
        Enhanced document processing with optimizations.
        
        Args:
            document: Document content
            config: Enhancement configuration
            
        Returns:
            Enhancement result
        """
        # Start monitoring
        if self.monitor:
            monitor_ctx = self.monitor.measure("document_enhancement")
            monitor_ctx.__enter__()
        
        try:
            # Convert to DocumentContent if needed
            if isinstance(document, str):
                document = DocumentContent(content=document)
            
            # Check for fast path (small documents)
            if len(document.content) < self.opt_config.fast_path_threshold:
                return await self._fast_path_enhancement(document, config)
            
            # Check cache
            if self.cache:
                cached_result = self.cache.get(
                    document.content,
                    config.__dict__ if config else {},
                    use_semantic=self.opt_config.use_semantic_cache
                )
                
                if cached_result:
                    self.cache_hits += 1
                    if self.monitor:
                        self.monitor.metrics_collector.increment_counter("cache_hits")
                    logger.debug("Cache hit for document enhancement")
                    return cached_result
                else:
                    self.cache_misses += 1
                    if self.monitor:
                        self.monitor.metrics_collector.increment_counter("cache_misses")
            
            # Perform enhancement with parallelization
            if self.parallel_executor and config and len(config.strategies) > 1:
                result = await self._parallel_enhancement(document, config)
            else:
                # Fall back to base implementation
                result = await super().enhance_document(document, config)
            
            # Cache result
            if self.cache and result.success:
                self.cache.put(
                    document.content,
                    config.__dict__ if config else {},
                    result
                )
            
            # Update metrics
            self.total_enhanced += 1
            
            return result
            
        finally:
            if self.monitor:
                monitor_ctx.__exit__(None, None, None)
    
    async def _fast_path_enhancement(
        self,
        document: DocumentContent,
        config: Optional[EnhancementConfig]
    ) -> EnhancementResult:
        """
        Fast path for small documents.
        
        Args:
            document: Document content
            config: Enhancement configuration
            
        Returns:
            Enhancement result
        """
        start_time = time.time()
        
        # Use minimal strategies for small documents
        if config and hasattr(config, 'strategies'):
            # Use only first 2 strategies for speed
            config.strategies = config.strategies[:2]
            config.max_passes = min(config.max_passes, 2)
        
        # Process with base implementation
        result = await super().enhance_document(document, config)
        
        if self.monitor:
            self.monitor.record_operation(
                "fast_path",
                time.time() - start_time,
                result.success,
                {"doc_size": len(document.content)}
            )
        
        return result
    
    async def _parallel_enhancement(
        self,
        document: DocumentContent,
        config: EnhancementConfig
    ) -> EnhancementResult:
        """
        Parallel strategy execution for enhancement.
        
        Args:
            document: Document content
            config: Enhancement configuration
            
        Returns:
            Enhancement result
        """
        start_time = time.time()
        
        # Get strategies
        strategies = self._get_ordered_strategies(config.strategies)
        
        # Execute strategies in parallel
        strategy_results = await self.parallel_executor.execute_strategies_parallel(
            document.content,
            strategies,
            document.metadata
        )
        
        # Measure quality
        initial_quality = await self._measure_quality(document.content)
        final_quality = await self._measure_quality(strategy_results["enhanced_content"])
        
        # Calculate improvement
        improvement_percentage = ((final_quality - initial_quality) / initial_quality) * 100
        
        # Create result
        result = EnhancementResult(
            original_content=document.content,
            enhanced_content=strategy_results["enhanced_content"],
            improvements=strategy_results["improvements"],
            quality_before=initial_quality,
            quality_after=final_quality,
            improvement_percentage=improvement_percentage,
            strategies_applied=strategy_results["strategies_applied"],
            total_cost=0.1 * len(strategies),  # Simplified cost calculation
            processing_time=time.time() - start_time,
            enhancement_passes=1,  # Single parallel pass
            success=len(strategy_results["errors"]) == 0,
            errors=strategy_results["errors"]
        )
        
        return result
    
    async def enhance_batch(
        self,
        documents: List[Union[str, DocumentContent]],
        config: Optional[EnhancementConfig] = None
    ) -> List[EnhancementResult]:
        """
        Enhanced batch processing with optimizations.
        
        Args:
            documents: List of documents
            config: Enhancement configuration
            
        Returns:
            List of enhancement results
        """
        if not self.batch_optimizer:
            # Fall back to base implementation
            return await super().enhance_batch(documents, config)
        
        # Start monitoring
        if self.monitor:
            monitor_ctx = self.monitor.measure("batch_enhancement")
            monitor_ctx.__enter__()
        
        try:
            # Optimize and process batch
            batch_result = await self.batch_optimizer.optimize_and_process(
                documents,
                lambda content, metadata: self.enhance_document(
                    DocumentContent(content=content, metadata=metadata),
                    config
                ),
                progress_callback=self._batch_progress_callback
            )
            
            # Extract results
            results = []
            for doc_id, result in batch_result["results"].items():
                if isinstance(result, EnhancementResult):
                    results.append(result)
                else:
                    # Create placeholder for failed documents
                    results.append(EnhancementResult(
                        original_content="",
                        enhanced_content="",
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
            
            # Log metrics
            metrics = batch_result["metrics"]
            logger.info(
                f"Batch processing complete: {metrics['documents_processed']} docs, "
                f"{metrics['throughput_docs_per_min']:.1f} docs/min"
            )
            
            if self.monitor:
                self.monitor.record_operation(
                    "batch_processing",
                    metrics["total_time"],
                    True,
                    {
                        "docs_processed": metrics["documents_processed"],
                        "throughput": metrics["throughput_docs_per_min"]
                    }
                )
            
            return results
            
        finally:
            if self.monitor:
                monitor_ctx.__exit__(None, None, None)
    
    async def enhance_stream(
        self,
        document_stream: AsyncIterator[Union[str, DocumentContent]],
        config: Optional[EnhancementConfig] = None
    ) -> AsyncIterator[EnhancementResult]:
        """
        Stream processing for memory efficiency.
        
        Args:
            document_stream: Async iterator of documents
            config: Enhancement configuration
            
        Yields:
            Enhancement results as they complete
        """
        if not self.streaming_processor:
            # Process one by one without streaming optimization
            async for doc in document_stream:
                yield await self.enhance_document(doc, config)
            return
        
        # Use streaming processor
        async for batch_result in self.streaming_processor.process_stream(
            document_stream,
            lambda content, metadata: self.enhance_document(
                DocumentContent(content=content, metadata=metadata),
                config
            )
        ):
            # Yield individual results from batch
            for doc_id, result in batch_result.results.items():
                if isinstance(result, EnhancementResult):
                    yield result
    
    async def _batch_progress_callback(
        self,
        processed: int,
        total: int
    ) -> None:
        """Callback for batch processing progress."""
        if processed % 10 == 0:
            logger.info(f"Batch progress: {processed}/{total} documents")
    
    def warm_cache(self, sample_documents: List[Tuple[str, Dict[str, Any]]]) -> None:
        """
        Warm cache with sample documents.
        
        Args:
            sample_documents: List of (content, config) tuples
        """
        if self.cache:
            self.cache.warm_cache(sample_documents)
            logger.info(f"Cache warmed with {len(sample_documents)} samples")
    
    def apply_adaptive_tuning(self) -> None:
        """Apply adaptive performance tuning based on metrics."""
        if not self.monitor or not self.monitor.adaptive_tuner:
            return
        
        recommendations = self.monitor.get_tuning_recommendations()
        
        if recommendations:
            # Apply batch size adjustment
            if "batch_size" in recommendations and self.batch_optimizer:
                self.batch_optimizer.batcher.batch_size = recommendations["batch_size"]
            
            # Apply worker adjustment
            if "max_workers" in recommendations and self.parallel_executor:
                # Note: ThreadPoolExecutor doesn't support dynamic resizing
                # This would require recreating the executor
                logger.info(f"Recommended worker adjustment: {recommendations['max_workers']}")
            
            # Apply cache size adjustment
            if "cache_size" in recommendations and self.cache:
                self.cache.lru_cache.max_size = recommendations["cache_size"]
            
            logger.info(f"Applied adaptive tuning: {recommendations}")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        report = {
            "pipeline_metrics": {
                "total_enhanced": self.total_enhanced,
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses,
                "cache_hit_ratio": self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0
            }
        }
        
        # Add cache stats
        if self.cache:
            report["cache_stats"] = self.cache.get_stats()
        
        # Add batch optimizer stats
        if self.batch_optimizer:
            report["batch_stats"] = self.batch_optimizer.get_global_metrics()
        
        # Add parallel executor stats
        if self.parallel_executor:
            report["parallel_stats"] = self.parallel_executor.get_metrics()
        
        # Add monitor report
        if self.monitor:
            report["monitor_report"] = self.monitor.generate_report()
        
        return report
    
    async def cleanup(self) -> None:
        """Clean up resources and save performance data."""
        # Generate final report
        report = self.get_performance_report()
        
        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = Path(f"m009_performance_{timestamp}.json")
        
        import json
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Performance report saved to {report_path}")
        
        # Shutdown components
        if self.monitor:
            self.monitor.shutdown()
        
        if self.parallel_executor:
            self.parallel_executor.shutdown()
        
        if self.cache:
            self.cache.clear()
        
        # Call base cleanup
        await super().cleanup()
        
        logger.info("Optimized pipeline cleanup complete")


def create_optimized_pipeline(
    mode: str = "PERFORMANCE",
    **kwargs
) -> OptimizedEnhancementPipeline:
    """
    Factory function to create optimized pipeline.
    
    Args:
        mode: Optimization mode (BASIC, PERFORMANCE, BALANCED, AGGRESSIVE)
        **kwargs: Additional configuration
        
    Returns:
        Configured optimized pipeline
    """
    settings = kwargs.get("settings") or EnhancementSettings()
    opt_config = OptimizationConfig.for_mode(mode)
    
    # Override with kwargs
    for key, value in kwargs.items():
        if hasattr(opt_config, key):
            setattr(opt_config, key, value)
    
    return OptimizedEnhancementPipeline(
        settings=settings,
        optimization_config=opt_config,
        mode=mode
    )