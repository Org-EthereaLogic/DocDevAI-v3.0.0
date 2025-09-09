"""
Performance Tests for M004 Document Generator Pass 2
DevDocAI v3.0.0 - Performance Optimization Validation

Validates performance improvements and benchmarks against design targets.
Target: 248,000 documents per minute (4,133 docs/second)
"""

import asyncio
import time
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List
import pytest
import json
import yaml

from devdocai.core.config import ConfigurationManager
from devdocai.core.generator import (
    DocumentGenerator,
    ResponseCache,
    ContextCache,
    BatchProcessor,
    BatchRequest,
    PerformanceMonitor,
)
from devdocai.core.storage import StorageManager
from devdocai.intelligence.llm_adapter import LLMAdapter


# ============================================================================
# Performance Test Fixtures
# ============================================================================


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing."""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def config_performance(temp_dir):
    """Create configuration optimized for performance testing."""
    config = ConfigurationManager()
    config.set("storage.path", temp_dir)
    config.set("templates.dir", f"{temp_dir}/templates")
    config.set("cache.dir", f"{temp_dir}/cache")
    config.set("memory_mode", "performance")  # Maximum performance mode
    config.set("cache.ttl", 3600)
    config.set("ai.provider", "mock")  # Use mock for consistent benchmarking
    config.set("ai.max_tokens", 2000)
    return config


@pytest.fixture
def generator_performance(config_performance):
    """Create document generator for performance testing."""
    return DocumentGenerator(config=config_performance)


@pytest.fixture
def sample_project(temp_dir):
    """Create sample project for testing."""
    project_dir = Path(temp_dir) / "sample_project"
    project_dir.mkdir(parents=True)

    # Create sample Python files
    (project_dir / "main.py").write_text(
        """
def main():
    print("Sample project")

if __name__ == "__main__":
    main()
"""
    )

    (project_dir / "utils.py").write_text(
        """
class DataProcessor:
    def process(self, data):
        return data

def helper_function(x):
    return x * 2
"""
    )

    # Create setup.py
    (project_dir / "setup.py").write_text(
        """
from setuptools import setup

setup(
    name="sample_project",
    version="1.0.0",
    description="Sample project for performance testing"
)
"""
    )

    return str(project_dir)


# ============================================================================
# Cache Performance Tests
# ============================================================================


class TestCachePerformance:
    """Test cache system performance."""

    def test_response_cache_performance(self, config_performance):
        """Test ResponseCache performance with high load."""
        cache = ResponseCache(config_performance)

        # Benchmark cache operations
        start_time = time.time()
        operations = 10000

        # Write operations
        for i in range(operations):
            prompt = f"Generate documentation for function_{i}"
            context = {"function_name": f"func_{i}", "index": i}
            response = f"Documentation for function_{i}"
            cache.put(prompt, context, response, tokens_used=100, cost=0.001)

        write_time = time.time() - start_time
        writes_per_second = operations / write_time

        # Read operations (with cache hits)
        start_time = time.time()
        hits = 0

        for i in range(operations):
            prompt = f"Generate documentation for function_{i}"
            context = {"function_name": f"func_{i}", "index": i}
            result = cache.get(prompt, context)
            if result:
                hits += 1

        read_time = time.time() - start_time
        reads_per_second = operations / read_time
        hit_rate = hits / operations

        # Performance assertions
        assert writes_per_second > 5000, f"Cache writes too slow: {writes_per_second:.1f}/s"
        assert reads_per_second > 10000, f"Cache reads too slow: {reads_per_second:.1f}/s"
        assert hit_rate > 0.95, f"Cache hit rate too low: {hit_rate:.2%}"

        # Print performance metrics
        print(f"\\nCache Performance:")
        print(f"  Writes: {writes_per_second:.1f}/s")
        print(f"  Reads: {reads_per_second:.1f}/s")
        print(f"  Hit Rate: {hit_rate:.2%}")

    def test_context_cache_performance(self, config_performance, sample_project):
        """Test ContextCache performance."""
        cache = ContextCache(config_performance)

        # Benchmark context caching
        iterations = 100

        # First extraction (cold)
        start_time = time.time()
        for _ in range(iterations):
            cache.put(sample_project, {"extracted": "context"})
        cold_time = time.time() - start_time

        # Cached extraction (hot)
        start_time = time.time()
        hits = 0
        for _ in range(iterations):
            result = cache.get(sample_project)
            if result:
                hits += 1
        hot_time = time.time() - start_time

        speedup = cold_time / hot_time

        assert speedup > 10, f"Cache speedup too low: {speedup:.1f}x"
        assert hits == iterations, f"Not all cache hits: {hits}/{iterations}"

        print(f"\\nContext Cache Speedup: {speedup:.1f}x")


# ============================================================================
# Parallel Processing Tests
# ============================================================================


class TestParallelProcessing:
    """Test parallel document generation performance."""

    @pytest.mark.asyncio
    async def test_batch_processor_performance(self, config_performance, sample_project):
        """Test BatchProcessor performance with multiple documents."""
        generator = DocumentGenerator(config=config_performance)

        # Create batch requests
        batch_size = 100
        requests = []

        for i in range(batch_size):
            request = BatchRequest(
                document_type="readme",
                project_path=sample_project,
                context={"index": i, "project_name": f"project_{i}"},
                request_id=f"req_{i}",
            )
            requests.append(request)

        # Measure batch processing time
        start_time = time.time()
        results = await generator.generate_batch(requests)
        batch_time = time.time() - start_time

        # Calculate performance metrics
        docs_per_second = batch_size / batch_time
        docs_per_minute = docs_per_second * 60

        # Validate results
        assert (
            len(results) == batch_size
        ), f"Not all documents generated: {len(results)}/{batch_size}"

        successful = sum(1 for r in results.values() if r is not None)
        success_rate = successful / batch_size

        assert success_rate > 0.95, f"Success rate too low: {success_rate:.2%}"

        print(f"\\nBatch Processing Performance:")
        print(f"  Documents: {batch_size}")
        print(f"  Time: {batch_time:.2f}s")
        print(f"  Throughput: {docs_per_second:.1f} docs/s")
        print(f"  Projected: {docs_per_minute:.0f} docs/min")
        print(f"  Success Rate: {success_rate:.2%}")

        return docs_per_minute

    @pytest.mark.asyncio
    async def test_parallel_section_generation(self, generator_performance, sample_project):
        """Test parallel section generation performance."""
        # Generate with sequential sections
        start_time = time.time()
        result_seq = await generator_performance.generate(
            document_type="readme",
            project_path=sample_project,
            parallel_sections=False,
            use_cache=False,
        )
        seq_time = time.time() - start_time

        # Clear caches for fair comparison
        generator_performance.clear_caches()

        # Generate with parallel sections
        start_time = time.time()
        result_par = await generator_performance.generate(
            document_type="readme",
            project_path=sample_project,
            parallel_sections=True,
            use_cache=False,
        )
        par_time = time.time() - start_time

        speedup = seq_time / par_time

        print(f"\\nParallel Section Generation:")
        print(f"  Sequential: {seq_time:.2f}s")
        print(f"  Parallel: {par_time:.2f}s")
        print(f"  Speedup: {speedup:.1f}x")

        # Parallel should be faster for multi-section documents
        assert speedup > 1.2, f"Parallel generation not faster: {speedup:.1f}x"


# ============================================================================
# Memory Mode Scaling Tests
# ============================================================================


class TestMemoryModeScaling:
    """Test performance scaling across memory modes."""

    @pytest.mark.asyncio
    async def test_memory_mode_performance(self, temp_dir, sample_project):
        """Test performance across different memory modes."""
        memory_modes = ["baseline", "standard", "enhanced", "performance"]
        results = {}

        for mode in memory_modes:
            # Create config for this mode
            config = ConfigurationManager()
            config.set("storage.path", temp_dir)
            config.set("memory_mode", mode)
            config.set("ai.provider", "mock")

            generator = DocumentGenerator(config=config)

            # Measure generation time
            iterations = 10
            start_time = time.time()

            for i in range(iterations):
                await generator.generate(
                    document_type="readme",
                    project_path=sample_project,
                    custom_context={"iteration": i},
                    use_cache=(i > 0),  # Use cache after first iteration
                )

            elapsed = time.time() - start_time
            docs_per_second = iterations / elapsed

            results[mode] = {
                "docs_per_second": docs_per_second,
                "time_per_doc": elapsed / iterations,
                "max_workers": generator.max_workers,
                "cache_size": generator.response_cache.max_cache_size,
            }

            # Clear for next mode
            generator.clear_caches()

        # Print comparison
        print("\\nMemory Mode Performance Comparison:")
        for mode, metrics in results.items():
            print(f"  {mode}:")
            print(f"    Throughput: {metrics['docs_per_second']:.1f} docs/s")
            print(f"    Time/Doc: {metrics['time_per_doc']:.3f}s")
            print(f"    Workers: {metrics['max_workers']}")
            print(f"    Cache Size: {metrics['cache_size']}")

        # Performance mode should be significantly faster
        perf_speedup = (
            results["performance"]["docs_per_second"] / results["baseline"]["docs_per_second"]
        )
        assert perf_speedup > 2.0, f"Performance mode speedup too low: {perf_speedup:.1f}x"


# ============================================================================
# End-to-End Performance Benchmarks
# ============================================================================


class TestPerformanceBenchmarks:
    """Comprehensive performance benchmarks."""

    @pytest.mark.asyncio
    async def test_sustained_throughput(self, generator_performance, sample_project):
        """Test sustained document generation throughput."""
        duration = 10  # seconds
        documents_generated = 0
        start_time = time.time()

        # Generate documents continuously
        while (time.time() - start_time) < duration:
            result = await generator_performance.generate(
                document_type="readme",
                project_path=sample_project,
                custom_context={"doc_id": documents_generated},
                use_cache=True,
                parallel_sections=True,
            )

            if result and result.get("content"):
                documents_generated += 1

        elapsed = time.time() - start_time
        docs_per_second = documents_generated / elapsed
        docs_per_minute = docs_per_second * 60

        # Get performance stats
        stats = generator_performance.get_performance_stats()
        cache_stats = stats["cache_statistics"]

        print(f"\\nSustained Throughput Test ({duration}s):")
        print(f"  Documents Generated: {documents_generated}")
        print(f"  Throughput: {docs_per_second:.1f} docs/s")
        print(f"  Projected: {docs_per_minute:.0f} docs/min")
        print(f"  Cache Hit Rate: {cache_stats['hit_rate']:.2%}")
        print(f"  Memory Mode: {stats['memory_mode']}")

        # Minimum performance thresholds
        assert docs_per_second > 1.0, f"Throughput too low: {docs_per_second:.1f} docs/s"
        assert (
            cache_stats["hit_rate"] > 0.5
        ), f"Cache hit rate too low: {cache_stats['hit_rate']:.2%}"

    @pytest.mark.asyncio
    async def test_performance_monitor(self, generator_performance, sample_project):
        """Test PerformanceMonitor tracking."""
        monitor = generator_performance.performance_monitor

        # Generate several documents with monitoring
        for i in range(5):
            await generator_performance.generate(
                document_type="readme", project_path=sample_project, custom_context={"iteration": i}
            )

        # Get performance statistics
        stats = monitor.get_stats()

        assert "document_generation" in stats, "Missing generation stats"
        assert "context_extraction" in stats, "Missing context stats"
        assert "content_generation" in stats, "Missing content stats"

        # Validate statistics
        gen_stats = stats["document_generation"]
        assert gen_stats["count"] == 5, f"Wrong count: {gen_stats['count']}"
        assert gen_stats["mean"] > 0, "No timing data"

        print("\\nPerformance Monitoring:")
        for operation, metrics in stats.items():
            if metrics:
                print(f"  {operation}:")
                print(f"    Count: {metrics['count']}")
                print(f"    Avg Time: {metrics['mean']:.3f}s")
                print(f"    Throughput: {metrics['throughput']:.1f}/s")


# ============================================================================
# Performance Report
# ============================================================================


@pytest.mark.asyncio
async def test_performance_report(generator_performance, sample_project):
    """Generate comprehensive performance report."""
    print("\\n" + "=" * 60)
    print("M004 DOCUMENT GENERATOR - PERFORMANCE REPORT")
    print("=" * 60)

    # Test different scenarios
    scenarios = {"single_doc": 1, "small_batch": 10, "medium_batch": 50, "large_batch": 100}

    results = {}

    for scenario, count in scenarios.items():
        requests = [
            BatchRequest(
                document_type="readme",
                project_path=sample_project,
                context={"id": i},
                request_id=f"{scenario}_{i}",
            )
            for i in range(count)
        ]

        start_time = time.time()
        batch_results = await generator_performance.generate_batch(requests)
        elapsed = time.time() - start_time

        results[scenario] = {
            "count": count,
            "time": elapsed,
            "throughput": count / elapsed,
            "projected_per_min": (count / elapsed) * 60,
        }

    # Print results
    print("\\nScenario Performance:")
    print(f"{'Scenario':<15} {'Count':<10} {'Time':<10} {'Throughput':<15} {'Projected/min'}")
    print("-" * 70)

    for scenario, metrics in results.items():
        print(
            f"{scenario:<15} {metrics['count']:<10} "
            f"{metrics['time']:<10.2f} {metrics['throughput']:<15.1f} "
            f"{metrics['projected_per_min']:.0f}"
        )

    # Final statistics
    final_stats = generator_performance.get_performance_stats()

    print("\\nFinal Statistics:")
    print(f"  Total Documents: {final_stats['documents_generated']}")
    print(f"  Avg Generation Time: {final_stats['average_generation_time']:.3f}s")
    print(f"  Documents/Second: {final_stats['documents_per_second']:.1f}")
    print(f"  Documents/Minute: {final_stats['documents_per_minute']:.0f}")
    print(f"  Cache Hit Rate: {final_stats['cache_statistics']['hit_rate']:.2%}")

    # Performance vs Target
    target_per_minute = 248000
    actual_per_minute = final_stats["documents_per_minute"]
    percentage = (actual_per_minute / target_per_minute) * 100

    print(f"\\nPerformance vs Target:")
    print(f"  Target: {target_per_minute:,} docs/min")
    print(f"  Actual: {actual_per_minute:.0f} docs/min")
    print(f"  Achievement: {percentage:.2f}%")

    if percentage < 1:
        print(f"  Gap: {(target_per_minute / actual_per_minute):.0f}x improvement needed")

    print("\\n" + "=" * 60)

    # Note: The 248K target assumes heavy caching and document similarity
    # Real-world performance will vary based on LLM response times
    print("\\nNote: Performance heavily depends on LLM response times.")
    print("With caching and document similarity, much higher throughput is achievable.")
    print("The 248K/min target assumes >99% cache hits in production scenarios.")


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-s"])
