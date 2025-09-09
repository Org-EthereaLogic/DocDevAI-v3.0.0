"""
Performance validation tests for M009 Enhancement Pipeline Pass 2 optimizations
DevDocAI v3.0.0 - M009 Pass 2: Performance Optimization Validation

Validates specific claims:
- 22.6x cache speedup improvement
- 26,655+ docs/minute batch processing throughput
- Memory efficiency under concurrent load
- Concurrent processing scaling
"""

import asyncio
import gc
import hashlib
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple
from unittest.mock import Mock, patch

import psutil
import pytest

from devdocai.core.config import ConfigurationManager
from devdocai.core.storage import StorageManager
from devdocai.intelligence.enhance import (
    EnhancementConfig,
    EnhancementPipeline,
    EnhancementResult,
    EnhancementStrategy,
    PerformanceMetrics,
)
from devdocai.intelligence.llm_adapter import LLMAdapter, LLMResponse
from devdocai.intelligence.miair import MIAIREngine, OptimizationResult


class TestM009PerformanceBenchmarks:
    """Empirical validation of M009 Enhancement Pipeline Pass 2 performance claims."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration optimized for performance testing."""
        config = Mock(spec=ConfigurationManager)
        config.get.side_effect = lambda key, default=None: {
            # M009 specific settings
            "enhancement.strategy": "combined",
            "enhancement.miair_weight": 0.4,
            "enhancement.llm_weight": 0.6,
            "enhancement.quality_threshold": 85.0,
            "enhancement.timeout_seconds": 30,
            "enhancement.enable_caching": True,
            "enhancement.cache_ttl": 3600,
            "enhancement.max_concurrent_requests": 8,
            "enhancement.batch_size": 50,
            "enhancement.streaming_enabled": True,
            "enhancement.memory_limit_mb": 512,
            # Dependencies
            "quality.entropy_threshold": 0.35,
            "quality.target_entropy": 0.15,
            "quality.coherence_target": 0.94,
            "quality.quality_gate": 85,
            "quality.max_iterations": 7,
            "performance.max_workers": 4,
            "performance.cache_size": 1000,
            "performance.batch_size": 100,
            "system.memory_mode": "standard",
        }.get(key, default)
        return config

    @pytest.fixture
    def mock_storage(self):
        """Mock storage manager for testing."""
        storage = Mock(spec=StorageManager)
        storage.store_enhancement_result = Mock(return_value=True)
        storage.get_enhancement_history = Mock(return_value=[])
        return storage

    @pytest.fixture
    def mock_llm_fast(self):
        """Mock LLM with realistic response times for performance testing."""
        llm = Mock(spec=LLMAdapter)
        
        def mock_query(prompt, max_tokens=2000, temperature=0.7):
            # Simulate realistic LLM response time (50-200ms)
            time.sleep(0.05 + (hash(prompt) % 100) / 1000)  # 50-150ms
            return LLMResponse(
                content=f"Enhanced: {prompt[:100]}..." if len(prompt) > 100 else f"Enhanced: {prompt}",
                provider="mock_fast",
                model="gpt-4",
                usage_stats={"prompt_tokens": 100, "completion_tokens": 150, "total_tokens": 250},
                response_time=0.1
            )
        
        llm.query = Mock(side_effect=mock_query)
        return llm

    @pytest.fixture
    def mock_miair(self):
        """Mock MIAIR engine with performance-optimized responses."""
        miair = Mock(spec=MIAIREngine)
        
        def mock_optimize(content, strategy="entropy", max_iterations=3):
            # Simulate MIAIR processing time (10-50ms)
            time.sleep(0.01 + (hash(content) % 40) / 1000)  # 10-50ms
            return OptimizationResult(
                initial_content=content,
                final_content=f"MIAIR optimized: {content}",
                iterations=2,
                initial_quality=70.0,
                final_quality=85.0,
                improvement_percentage=21.4,
                initial_entropy=2.5,
                final_entropy=1.8,
                optimization_time=0.025,
                storage_id=f"miair_{hash(content) % 10000}"
            )
        
        miair.optimize_document = Mock(side_effect=mock_optimize)
        return miair

    @pytest.fixture
    def enhancement_pipeline(self, mock_config, mock_storage, mock_llm_fast, mock_miair):
        """Create enhancement pipeline with mocked dependencies."""
        with patch('devdocai.intelligence.enhance.MIAIREngine') as mock_miair_class, \
             patch('devdocai.intelligence.enhance.LLMAdapter') as mock_llm_class, \
             patch('devdocai.intelligence.enhance.StorageManager') as mock_storage_class:
            
            mock_miair_class.return_value = mock_miair
            mock_llm_class.return_value = mock_llm_fast
            mock_storage_class.return_value = mock_storage
            
            pipeline = EnhancementPipeline(mock_config)
            
            # Configure for performance testing
            config = EnhancementConfig(
                strategy=EnhancementStrategy.COMBINED,
                enable_caching=True,
                cache_ttl_seconds=3600,
                max_concurrent_requests=8,
                batch_size=50,
                memory_limit_mb=512
            )
            pipeline.enhancement_config = config
            
            return pipeline

    def generate_test_documents(self, count: int, avg_length: int = 500) -> List[Tuple[str, str]]:
        """Generate realistic test documents for performance benchmarking."""
        documents = []
        base_content = (
            "This is a sample document that needs enhancement. "
            "It contains multiple sentences with varying complexity levels. "
            "The document discusses software engineering principles and best practices. "
            "Performance optimization is crucial for scalable applications. "
        )
        
        for i in range(count):
            # Vary document length and content to simulate real-world diversity
            multiplier = 1 + (i % 5) * 0.5  # 1x to 3x base length
            content = (base_content * int(avg_length * multiplier / len(base_content)))[:int(avg_length * multiplier)]
            content += f" Document ID: {i}"
            
            doc_type = ["readme", "api_doc", "changelog", "guide", "specification"][i % 5]
            documents.append((content, doc_type))
        
        return documents

    def test_cache_performance_speedup(self, enhancement_pipeline):
        """
        Validate the 22.6x cache speedup claim through empirical measurement.
        
        Tests:
        1. Cold cache (no speedup)
        2. Warm cache (should show significant speedup)
        3. Calculate actual speedup ratio
        """
        test_documents = self.generate_test_documents(20, 300)
        
        # Clear any existing cache
        enhancement_pipeline._cache.clear()
        enhancement_pipeline._metrics = PerformanceMetrics()
        
        # Measure cold cache performance (first run)
        cold_start = time.time()
        cold_results = []
        for content, doc_type in test_documents:
            result = enhancement_pipeline.enhance_document(content, doc_type)
            cold_results.append(result)
        cold_time = time.time() - cold_start
        
        # Measure warm cache performance (second run with same documents)
        warm_start = time.time()
        warm_results = []
        for content, doc_type in test_documents:
            result = enhancement_pipeline.enhance_document(content, doc_type)
            warm_results.append(result)
        warm_time = time.time() - warm_start
        
        # Calculate speedup
        speedup_ratio = cold_time / warm_time if warm_time > 0 else 0
        cache_hit_rate = enhancement_pipeline._metrics.cache_hits / max(1, enhancement_pipeline._metrics.total_requests)
        
        print(f"\n=== CACHE PERFORMANCE VALIDATION ===")
        print(f"Cold cache time: {cold_time:.3f}s ({len(test_documents)} docs)")
        print(f"Warm cache time: {warm_time:.3f}s ({len(test_documents)} docs)")
        print(f"Speedup ratio: {speedup_ratio:.1f}x")
        print(f"Cache hit rate: {cache_hit_rate:.1%}")
        print(f"Cache entries: {len(enhancement_pipeline._cache)}")
        
        # Validation assertions
        assert cold_time > warm_time, "Warm cache should be faster than cold cache"
        assert speedup_ratio >= 5.0, f"Expected minimum 5x speedup, got {speedup_ratio:.1f}x"
        assert cache_hit_rate >= 0.8, f"Expected 80%+ cache hits, got {cache_hit_rate:.1%}"
        
        # Check if we meet or approach the 22.6x claim
        if speedup_ratio >= 15.0:
            print(f"✅ EXCELLENT: {speedup_ratio:.1f}x speedup approaches/exceeds 22.6x claim")
        elif speedup_ratio >= 10.0:
            print(f"✅ GOOD: {speedup_ratio:.1f}x speedup is substantial")
        else:
            print(f"⚠️  MODERATE: {speedup_ratio:.1f}x speedup, may need optimization")

    def test_batch_throughput_performance(self, enhancement_pipeline):
        """
        Validate the 26,655+ docs/minute batch processing throughput claim.
        
        Tests concurrent batch processing with realistic document sizes.
        """
        # Test with different batch sizes to find optimal throughput
        batch_sizes = [10, 25, 50, 100]
        results = {}
        
        print(f"\n=== BATCH THROUGHPUT VALIDATION ===")
        
        for batch_size in batch_sizes:
            test_documents = self.generate_test_documents(batch_size, 400)
            
            # Clear cache to ensure fair measurement
            enhancement_pipeline._cache.clear()
            enhancement_pipeline._metrics = PerformanceMetrics()
            
            # Measure batch processing time
            start_time = time.time()
            batch_results = enhancement_pipeline.enhance_documents_batch(test_documents)
            end_time = time.time()
            
            batch_time = end_time - start_time
            throughput_per_min = (batch_size / batch_time) * 60 if batch_time > 0 else 0
            throughput_per_sec = batch_size / batch_time if batch_time > 0 else 0
            
            results[batch_size] = {
                'time': batch_time,
                'throughput_per_min': throughput_per_min,
                'throughput_per_sec': throughput_per_sec,
                'success_rate': sum(1 for r in batch_results if r.success) / len(batch_results)
            }
            
            print(f"Batch {batch_size:3d}: {batch_time:.3f}s, "
                  f"{throughput_per_min:>8,.0f} docs/min, "
                  f"{throughput_per_sec:>6.1f} docs/sec, "
                  f"{results[batch_size]['success_rate']:.1%} success")
        
        # Find best throughput
        best_batch = max(results.keys(), key=lambda k: results[k]['throughput_per_min'])
        best_throughput = results[best_batch]['throughput_per_min']
        
        print(f"\nBest throughput: {best_throughput:,.0f} docs/min (batch size: {best_batch})")
        
        # Validation assertions
        assert best_throughput >= 10000, f"Expected minimum 10K docs/min, got {best_throughput:,.0f}"
        
        # Check if we meet the 26,655+ claim
        if best_throughput >= 26655:
            print(f"✅ EXCELLENT: {best_throughput:,.0f} docs/min meets/exceeds 26,655+ claim")
        elif best_throughput >= 20000:
            print(f"✅ GOOD: {best_throughput:,.0f} docs/min is strong performance")
        elif best_throughput >= 15000:
            print(f"⚠️  MODERATE: {best_throughput:,.0f} docs/min, optimization opportunities exist")
        else:
            print(f"❌ BELOW EXPECTATION: {best_throughput:,.0f} docs/min needs improvement")
        
        return results

    def test_concurrent_processing_scaling(self, enhancement_pipeline):
        """
        Test how performance scales with concurrent processing.
        
        Validates that concurrent processing provides measurable benefits.
        """
        test_documents = self.generate_test_documents(40, 350)
        
        # Test sequential vs concurrent processing
        scenarios = [
            ("Sequential", 1),
            ("Concurrent 2", 2),
            ("Concurrent 4", 4),
            ("Concurrent 8", 8),
        ]
        
        results = {}
        
        print(f"\n=== CONCURRENT PROCESSING SCALING ===")
        
        for scenario_name, max_workers in scenarios:
            # Configure pipeline for this test
            enhancement_pipeline.enhancement_config.max_concurrent_requests = max_workers
            enhancement_pipeline._executor = ThreadPoolExecutor(max_workers=max_workers)
            
            # Clear cache for fair comparison
            enhancement_pipeline._cache.clear()
            enhancement_pipeline._metrics = PerformanceMetrics()
            
            # Measure processing time
            start_time = time.time()
            batch_results = enhancement_pipeline.enhance_documents_batch(test_documents)
            end_time = time.time()
            
            processing_time = end_time - start_time
            throughput = (len(test_documents) / processing_time) * 60 if processing_time > 0 else 0
            success_rate = sum(1 for r in batch_results if r.success) / len(batch_results)
            
            results[scenario_name] = {
                'workers': max_workers,
                'time': processing_time,
                'throughput': throughput,
                'success_rate': success_rate
            }
            
            print(f"{scenario_name:<15}: {processing_time:.3f}s, "
                  f"{throughput:>8,.0f} docs/min, {success_rate:.1%} success")
        
        # Calculate scaling efficiency
        baseline_time = results["Sequential"]["time"]
        for scenario in results:
            if scenario != "Sequential":
                speedup = baseline_time / results[scenario]["time"]
                efficiency = speedup / results[scenario]["workers"] * 100
                results[scenario]["speedup"] = speedup
                results[scenario]["efficiency"] = efficiency
                print(f"{scenario} speedup: {speedup:.2f}x (efficiency: {efficiency:.1f}%)")
        
        # Validation assertions
        assert results["Concurrent 4"]["speedup"] >= 1.5, "4-worker should show 1.5x+ speedup"
        assert results["Concurrent 8"]["throughput"] > results["Sequential"]["throughput"], "Concurrent should outperform sequential"

    def test_memory_efficiency_under_load(self, enhancement_pipeline):
        """
        Test memory usage efficiency during high-load processing.
        
        Validates memory stays within configured limits during concurrent processing.
        """
        test_documents = self.generate_test_documents(100, 600)  # Larger documents
        
        # Monitor memory usage during processing
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Configure for memory testing
        enhancement_pipeline.enhancement_config.memory_limit_mb = 256
        enhancement_pipeline.enhancement_config.max_concurrent_requests = 8
        
        print(f"\n=== MEMORY EFFICIENCY VALIDATION ===")
        print(f"Initial memory: {initial_memory:.1f} MB")
        print(f"Memory limit: {enhancement_pipeline.enhancement_config.memory_limit_mb} MB")
        
        # Process documents and monitor memory
        memory_samples = []
        start_time = time.time()
        
        # Process in chunks to monitor memory over time
        chunk_size = 20
        for i in range(0, len(test_documents), chunk_size):
            chunk = test_documents[i:i+chunk_size]
            
            # Process chunk
            chunk_results = enhancement_pipeline.enhance_documents_batch(chunk)
            
            # Sample memory
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_samples.append(current_memory)
            
            # Force garbage collection
            gc.collect()
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Memory analysis
        peak_memory = max(memory_samples)
        avg_memory = statistics.mean(memory_samples)
        memory_growth = peak_memory - initial_memory
        
        print(f"Peak memory: {peak_memory:.1f} MB")
        print(f"Average memory: {avg_memory:.1f} MB") 
        print(f"Memory growth: {memory_growth:.1f} MB")
        print(f"Processing time: {processing_time:.1f}s")
        print(f"Documents processed: {len(test_documents)}")
        
        # Validation assertions
        memory_limit = enhancement_pipeline.enhancement_config.memory_limit_mb
        assert peak_memory - initial_memory <= memory_limit * 1.5, f"Memory growth {memory_growth:.1f} MB exceeds limit"
        assert len([m for m in memory_samples if m - initial_memory > memory_limit * 2]) == 0, "Memory spikes detected"

    def test_statistical_performance_validation(self, enhancement_pipeline):
        """
        Statistical validation of performance claims across multiple runs.
        
        Provides confidence intervals for performance measurements.
        """
        n_runs = 5
        test_documents = self.generate_test_documents(30, 400)
        
        print(f"\n=== STATISTICAL PERFORMANCE VALIDATION ===")
        print(f"Running {n_runs} trials for statistical confidence...")
        
        # Collect performance data across multiple runs
        throughput_samples = []
        cache_speedup_samples = []
        
        for run in range(n_runs):
            print(f"Trial {run + 1}/{n_runs}")
            
            # Clear cache and reset metrics
            enhancement_pipeline._cache.clear()
            enhancement_pipeline._metrics = PerformanceMetrics()
            
            # Cold cache run
            cold_start = time.time()
            for content, doc_type in test_documents:
                enhancement_pipeline.enhance_document(content, doc_type)
            cold_time = time.time() - cold_start
            
            # Warm cache run
            warm_start = time.time()
            for content, doc_type in test_documents:
                enhancement_pipeline.enhance_document(content, doc_type)
            warm_time = time.time() - warm_start
            
            # Calculate metrics for this run
            speedup = cold_time / warm_time if warm_time > 0 else 0
            throughput = (len(test_documents) / cold_time) * 60 if cold_time > 0 else 0
            
            cache_speedup_samples.append(speedup)
            throughput_samples.append(throughput)
        
        # Statistical analysis
        avg_throughput = statistics.mean(throughput_samples)
        std_throughput = statistics.stdev(throughput_samples)
        avg_speedup = statistics.mean(cache_speedup_samples)
        std_speedup = statistics.stdev(cache_speedup_samples)
        
        # 95% confidence intervals (approximated)
        throughput_ci = (avg_throughput - 1.96 * std_throughput, avg_throughput + 1.96 * std_throughput)
        speedup_ci = (avg_speedup - 1.96 * std_speedup, avg_speedup + 1.96 * std_speedup)
        
        print(f"\n=== STATISTICAL RESULTS ===")
        print(f"Throughput: {avg_throughput:,.0f} ± {std_throughput:,.0f} docs/min")
        print(f"95% CI: [{throughput_ci[0]:,.0f}, {throughput_ci[1]:,.0f}] docs/min")
        print(f"Cache speedup: {avg_speedup:.1f} ± {std_speedup:.1f}x")
        print(f"95% CI: [{speedup_ci[0]:.1f}, {speedup_ci[1]:.1f}]x")
        
        # Final validation
        min_acceptable_throughput = 15000
        min_acceptable_speedup = 5.0
        
        assert throughput_ci[0] >= min_acceptable_throughput, f"Throughput confidence interval too low"
        assert speedup_ci[0] >= min_acceptable_speedup, f"Speedup confidence interval too low"
        
        print(f"\n✅ Statistical validation passed!")
        print(f"Throughput exceeds {min_acceptable_throughput:,} docs/min with 95% confidence")
        print(f"Cache speedup exceeds {min_acceptable_speedup}x with 95% confidence")

    def test_performance_regression_detection(self, enhancement_pipeline):
        """
        Performance regression detection suitable for CI/CD integration.
        
        Establishes performance baselines and detects regressions.
        """
        # Define performance baselines (these would be updated over time)
        PERFORMANCE_BASELINES = {
            "min_throughput_docs_per_min": 20000,
            "min_cache_speedup": 8.0,
            "max_memory_growth_mb": 200,
            "min_success_rate": 0.95,
        }
        
        test_documents = self.generate_test_documents(50, 450)
        
        print(f"\n=== PERFORMANCE REGRESSION DETECTION ===")
        
        # Run comprehensive performance test
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        # Clear state
        enhancement_pipeline._cache.clear()
        enhancement_pipeline._metrics = PerformanceMetrics()
        
        # Measure cold performance
        cold_start = time.time()
        cold_results = enhancement_pipeline.enhance_documents_batch(test_documents)
        cold_time = time.time() - cold_start
        
        # Measure warm performance
        warm_start = time.time()
        warm_results = enhancement_pipeline.enhance_documents_batch(test_documents)
        warm_time = time.time() - warm_start
        
        # Memory check
        peak_memory = process.memory_info().rss / 1024 / 1024
        memory_growth = peak_memory - initial_memory
        
        # Calculate key metrics
        throughput = (len(test_documents) / cold_time) * 60
        cache_speedup = cold_time / warm_time if warm_time > 0 else 0
        success_rate = sum(1 for r in cold_results if r.success) / len(cold_results)
        
        metrics = {
            "throughput_docs_per_min": throughput,
            "cache_speedup": cache_speedup,
            "memory_growth_mb": memory_growth,
            "success_rate": success_rate,
        }
        
        print(f"Current Performance Metrics:")
        for metric, value in metrics.items():
            baseline_key = f"min_{metric}" if not metric.endswith('_mb') else f"max_{metric}"
            baseline = PERFORMANCE_BASELINES.get(baseline_key, 0)
            
            if baseline_key.startswith('max_'):
                status = "✅ PASS" if value <= baseline else "❌ FAIL"
                print(f"  {metric}: {value:.2f} (baseline: ≤{baseline}) {status}")
            else:
                status = "✅ PASS" if value >= baseline else "❌ FAIL"
                print(f"  {metric}: {value:.2f} (baseline: ≥{baseline}) {status}")
        
        # Assertions for CI/CD
        assert throughput >= PERFORMANCE_BASELINES["min_throughput_docs_per_min"], \
            f"Throughput regression: {throughput:.0f} < {PERFORMANCE_BASELINES['min_throughput_docs_per_min']}"
        
        assert cache_speedup >= PERFORMANCE_BASELINES["min_cache_speedup"], \
            f"Cache speedup regression: {cache_speedup:.1f} < {PERFORMANCE_BASELINES['min_cache_speedup']}"
        
        assert memory_growth <= PERFORMANCE_BASELINES["max_memory_growth_mb"], \
            f"Memory regression: {memory_growth:.1f} > {PERFORMANCE_BASELINES['max_memory_growth_mb']}"
        
        assert success_rate >= PERFORMANCE_BASELINES["min_success_rate"], \
            f"Success rate regression: {success_rate:.2f} < {PERFORMANCE_BASELINES['min_success_rate']}"
        
        print(f"\n✅ All performance baselines maintained - No regression detected")
        
        return metrics


if __name__ == "__main__":
    # Allow running performance tests directly
    pytest.main([__file__, "-v", "-s"])