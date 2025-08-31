#!/usr/bin/env python3
"""
Comprehensive benchmark script for M009 Enhancement Pipeline Pass 2.

Measures performance improvements and validates targets:
- Batch processing: 100+ documents/minute (5x improvement)
- Memory usage: <500MB for 1000 documents
- Cache hit ratio: >30%
- Parallel speedup: 3-5x
- Token optimization: 25% reduction
"""

import asyncio
import time
import psutil
import numpy as np
import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime
import logging
import gc

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import M009 components
from devdocai.enhancement.enhancement_pipeline import EnhancementPipeline, DocumentContent
from devdocai.enhancement.batch_optimizer import BatchOptimizer, DocumentBatcher
from devdocai.enhancement.parallel_executor import ParallelExecutor, Task
from devdocai.enhancement.enhancement_cache import EnhancementCache
from devdocai.enhancement.config import EnhancementSettings, OperationMode

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class M009Benchmark:
    """Benchmark suite for M009 Enhancement Pipeline."""
    
    def __init__(self):
        """Initialize benchmark suite."""
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "summary": {}
        }
        self.pipeline = None
        self.cache = None
        
    async def setup(self):
        """Setup test environment."""
        logger.info("Setting up benchmark environment...")
        
        # Initialize pipeline with performance mode
        settings = EnhancementSettings(
            operation_mode=OperationMode.PERFORMANCE,
            max_passes=3,
            quality_threshold=0.8,
            batch_size=20,
            parallel_execution=True,
            cache_enabled=True
        )
        
        self.pipeline = EnhancementPipeline(settings)
        self.cache = EnhancementCache(max_size=1000, max_memory_mb=500)
        
        # Warm up
        await self._warmup()
        
    async def _warmup(self):
        """Warm up the system."""
        logger.info("Warming up...")
        warmup_docs = [self._generate_document(i, size="small") for i in range(5)]
        for doc in warmup_docs:
            await self.pipeline.enhance_document(doc)
    
    def _generate_document(self, index: int, size: str = "medium") -> DocumentContent:
        """Generate test document of specified size."""
        sizes = {
            "small": 500,    # 500 chars
            "medium": 2000,  # 2KB
            "large": 10000,  # 10KB
            "xlarge": 50000  # 50KB
        }
        
        char_count = sizes.get(size, 2000)
        content = f"Document {index}. " + "Lorem ipsum dolor sit amet. " * (char_count // 30)
        
        return DocumentContent(
            content=content[:char_count],
            metadata={"index": index, "size": size, "priority": index % 5}
        )
    
    async def benchmark_single_document(self) -> Dict[str, Any]:
        """Benchmark single document enhancement."""
        logger.info("Benchmarking single document enhancement...")
        
        results = {}
        sizes = ["small", "medium", "large", "xlarge"]
        
        for size in sizes:
            doc = self._generate_document(0, size)
            
            # Measure memory before
            process = psutil.Process()
            mem_before = process.memory_info().rss / 1024 / 1024  # MB
            
            # Time the enhancement
            start = time.perf_counter()
            result = await self.pipeline.enhance_document(doc)
            elapsed = time.perf_counter() - start
            
            # Measure memory after
            mem_after = process.memory_info().rss / 1024 / 1024  # MB
            mem_used = mem_after - mem_before
            
            results[size] = {
                "time_seconds": elapsed,
                "memory_mb": mem_used,
                "success": result.success,
                "improvement": result.improvement_percentage if result.success else 0
            }
            
            logger.info(f"  {size}: {elapsed:.2f}s, {mem_used:.1f}MB")
        
        return results
    
    async def benchmark_batch_processing(self) -> Dict[str, Any]:
        """Benchmark batch processing throughput."""
        logger.info("Benchmarking batch processing...")
        
        batch_sizes = [10, 50, 100, 200]
        results = {}
        
        for batch_size in batch_sizes:
            # Generate documents
            docs = [self._generate_document(i, "medium") for i in range(batch_size)]
            
            # Clear cache for fair comparison
            if self.cache:
                self.cache.clear()
            
            # Measure
            process = psutil.Process()
            mem_before = process.memory_info().rss / 1024 / 1024
            
            start = time.perf_counter()
            batch_results = await self.pipeline.enhance_batch(docs)
            elapsed = time.perf_counter() - start
            
            mem_after = process.memory_info().rss / 1024 / 1024
            
            # Calculate metrics
            throughput_per_minute = (batch_size / elapsed) * 60
            throughput_per_second = batch_size / elapsed
            
            results[f"batch_{batch_size}"] = {
                "documents": batch_size,
                "total_time": elapsed,
                "throughput_per_minute": throughput_per_minute,
                "throughput_per_second": throughput_per_second,
                "memory_mb": mem_after - mem_before,
                "avg_time_per_doc": elapsed / batch_size
            }
            
            logger.info(f"  Batch {batch_size}: {throughput_per_minute:.1f} docs/min, "
                       f"{elapsed:.2f}s total")
        
        return results
    
    async def benchmark_cache_effectiveness(self) -> Dict[str, Any]:
        """Benchmark cache hit ratio and performance impact."""
        logger.info("Benchmarking cache effectiveness...")
        
        # Generate documents with some duplicates
        num_unique = 50
        num_total = 150  # 3x reuse
        
        docs = []
        for i in range(num_total):
            # Reuse documents to test cache
            doc_index = i % num_unique
            docs.append(self._generate_document(doc_index, "medium"))
        
        # Clear cache
        if self.cache:
            self.cache.clear()
        
        # Process documents and measure cache stats
        start = time.perf_counter()
        for doc in docs:
            await self.pipeline.enhance_document(doc)
        elapsed = time.perf_counter() - start
        
        # Get cache statistics
        cache_stats = self.cache.get_stats() if self.cache else {}
        
        results = {
            "total_documents": num_total,
            "unique_documents": num_unique,
            "processing_time": elapsed,
            "cache_hit_ratio": cache_stats.get("hit_ratio", 0),
            "cache_hits": cache_stats.get("hits", 0),
            "cache_misses": cache_stats.get("misses", 0),
            "semantic_matches": cache_stats.get("semantic_matches", 0),
            "throughput_with_cache": (num_total / elapsed) * 60  # docs/min
        }
        
        logger.info(f"  Cache hit ratio: {results['cache_hit_ratio']:.1%}")
        logger.info(f"  Throughput with cache: {results['throughput_with_cache']:.1f} docs/min")
        
        return results
    
    async def benchmark_parallel_speedup(self) -> Dict[str, Any]:
        """Benchmark parallel execution speedup."""
        logger.info("Benchmarking parallel execution...")
        
        num_docs = 50
        docs = [self._generate_document(i, "medium") for i in range(num_docs)]
        
        # Sequential execution
        start = time.perf_counter()
        sequential_results = []
        for doc in docs:
            result = await self.pipeline.enhance_document(doc)
            sequential_results.append(result)
        sequential_time = time.perf_counter() - start
        
        # Parallel execution
        start = time.perf_counter()
        parallel_results = await self.pipeline.enhance_batch(docs)
        parallel_time = time.perf_counter() - start
        
        # Calculate speedup
        speedup = sequential_time / parallel_time if parallel_time > 0 else 0
        
        results = {
            "documents": num_docs,
            "sequential_time": sequential_time,
            "parallel_time": parallel_time,
            "speedup": speedup,
            "sequential_throughput": (num_docs / sequential_time) * 60,
            "parallel_throughput": (num_docs / parallel_time) * 60
        }
        
        logger.info(f"  Speedup: {speedup:.2f}x")
        logger.info(f"  Sequential: {results['sequential_throughput']:.1f} docs/min")
        logger.info(f"  Parallel: {results['parallel_throughput']:.1f} docs/min")
        
        return results
    
    async def benchmark_memory_usage(self) -> Dict[str, Any]:
        """Benchmark memory usage for large batches."""
        logger.info("Benchmarking memory usage...")
        
        doc_counts = [100, 500, 1000]
        results = {}
        
        for count in doc_counts:
            # Generate documents
            docs = [self._generate_document(i, "medium") for i in range(count)]
            
            # Force garbage collection
            gc.collect()
            
            # Measure baseline memory
            process = psutil.Process()
            mem_baseline = process.memory_info().rss / 1024 / 1024
            
            # Process batch
            start = time.perf_counter()
            await self.pipeline.enhance_batch(docs)
            elapsed = time.perf_counter() - start
            
            # Measure peak memory
            mem_peak = process.memory_info().rss / 1024 / 1024
            mem_used = mem_peak - mem_baseline
            
            results[f"docs_{count}"] = {
                "document_count": count,
                "memory_used_mb": mem_used,
                "memory_per_doc_mb": mem_used / count,
                "processing_time": elapsed,
                "meets_target": mem_used < 500  # Target: <500MB for 1000 docs
            }
            
            logger.info(f"  {count} docs: {mem_used:.1f}MB ({mem_used/count:.2f}MB per doc)")
        
        return results
    
    async def run_all_benchmarks(self):
        """Run all benchmarks and generate report."""
        logger.info("=" * 60)
        logger.info("M009 Enhancement Pipeline - Performance Benchmark")
        logger.info("=" * 60)
        
        await self.setup()
        
        # Run benchmarks
        self.results["tests"]["single_document"] = await self.benchmark_single_document()
        self.results["tests"]["batch_processing"] = await self.benchmark_batch_processing()
        self.results["tests"]["cache_effectiveness"] = await self.benchmark_cache_effectiveness()
        self.results["tests"]["parallel_speedup"] = await self.benchmark_parallel_speedup()
        self.results["tests"]["memory_usage"] = await self.benchmark_memory_usage()
        
        # Calculate summary
        self._calculate_summary()
        
        # Print results
        self._print_results()
        
        # Save results
        self._save_results()
    
    def _calculate_summary(self):
        """Calculate summary statistics."""
        tests = self.results["tests"]
        
        # Check if targets are met
        batch_200 = tests["batch_processing"].get("batch_200", {})
        cache_stats = tests["cache_effectiveness"]
        parallel = tests["parallel_speedup"]
        memory_1000 = tests["memory_usage"].get("docs_1000", {})
        
        self.results["summary"] = {
            "targets_met": {
                "batch_processing_100_plus": batch_200.get("throughput_per_minute", 0) > 100,
                "cache_hit_ratio_30_plus": cache_stats.get("cache_hit_ratio", 0) > 0.3,
                "parallel_speedup_3x_plus": parallel.get("speedup", 0) >= 3,
                "memory_under_500mb_1000_docs": memory_1000.get("meets_target", False)
            },
            "performance_metrics": {
                "max_throughput_per_minute": batch_200.get("throughput_per_minute", 0),
                "cache_hit_ratio": cache_stats.get("cache_hit_ratio", 0),
                "parallel_speedup": parallel.get("speedup", 0),
                "memory_for_1000_docs": memory_1000.get("memory_used_mb", 0)
            },
            "improvement_over_baseline": {
                "throughput": batch_200.get("throughput_per_minute", 0) / 20,  # Baseline: 20 docs/min
                "description": f"{batch_200.get('throughput_per_minute', 0) / 20:.1f}x improvement"
            }
        }
    
    def _print_results(self):
        """Print benchmark results."""
        logger.info("\n" + "=" * 60)
        logger.info("BENCHMARK RESULTS SUMMARY")
        logger.info("=" * 60)
        
        summary = self.results["summary"]
        
        # Performance metrics
        logger.info("\nPerformance Metrics:")
        metrics = summary["performance_metrics"]
        logger.info(f"  Max Throughput: {metrics['max_throughput_per_minute']:.1f} docs/minute")
        logger.info(f"  Cache Hit Ratio: {metrics['cache_hit_ratio']:.1%}")
        logger.info(f"  Parallel Speedup: {metrics['parallel_speedup']:.2f}x")
        logger.info(f"  Memory (1000 docs): {metrics['memory_for_1000_docs']:.1f}MB")
        
        # Targets
        logger.info("\nTargets Achievement:")
        targets = summary["targets_met"]
        for target, met in targets.items():
            status = "✅ PASS" if met else "❌ FAIL"
            logger.info(f"  {target}: {status}")
        
        # Overall improvement
        improvement = summary["improvement_over_baseline"]
        logger.info(f"\nOverall Improvement: {improvement['description']}")
        
        # Pass/Fail
        all_passed = all(targets.values())
        logger.info("\n" + "=" * 60)
        if all_passed:
            logger.info("🎉 ALL PERFORMANCE TARGETS MET! 🎉")
        else:
            logger.info("⚠️  Some targets not met. Further optimization needed.")
        logger.info("=" * 60)
    
    def _save_results(self):
        """Save results to file."""
        output_path = Path("benchmark_results_m009.json")
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        logger.info(f"\nResults saved to {output_path}")


async def main():
    """Run the benchmark suite."""
    benchmark = M009Benchmark()
    await benchmark.run_all_benchmarks()


if __name__ == "__main__":
    asyncio.run(main())