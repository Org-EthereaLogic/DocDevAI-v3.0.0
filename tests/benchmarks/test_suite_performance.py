"""
Performance Benchmarking Suite for M006 Suite Manager Pass 2
DevDocAI v3.0.0

This test suite validates that the Pass 2 performance optimizations meet or exceed targets:
- Suite Generation: <2s for 10 documents (improved from <5s)
- Consistency Analysis: <1s for 100 documents (improved from <2s)
- Impact Analysis: <1s for 500+ document suites
- Memory efficiency: Adaptive based on M001 modes
- Concurrent operations: 50+ supported
"""

import pytest
import asyncio
import time
import psutil
import os
from typing import List, Dict, Any
from unittest.mock import Mock, AsyncMock, patch
import concurrent.futures
from pathlib import Path

# Import both original and optimized versions for comparison
from devdocai.core.suite import SuiteManager
from devdocai.core.suite_optimized import (
    OptimizedSuiteManager,
    PerformanceMonitor,
    perf_monitor,
    SuiteConfig,
    ChangeType,
    ImpactSeverity
)
from devdocai.core.config import ConfigurationManager
from devdocai.core.storage import StorageManager, Document
from devdocai.core.generator import DocumentGenerator
from devdocai.core.tracking import TrackingMatrix, DependencyGraph, RelationshipType


class TestSuitePerformance:
    """Performance benchmarks for Suite Manager optimizations."""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for testing."""
        config = Mock(spec=ConfigurationManager)
        storage = Mock(spec=StorageManager)
        generator = Mock(spec=DocumentGenerator)
        tracking = Mock(spec=TrackingMatrix)
        
        # Configure memory mode responses
        config.get_memory_mode.return_value = "performance"  # 8GB mode
        
        # Configure storage to be fast
        storage.save_document = AsyncMock(return_value=True)
        storage.get_document = AsyncMock(return_value=None)
        storage.list_documents = AsyncMock(return_value=[])
        storage.begin_transaction = AsyncMock()
        storage.commit = AsyncMock()
        storage.rollback = AsyncMock()
        
        # Configure generator for fast responses
        async def generate_doc(template, context):
            await asyncio.sleep(0.001)  # Simulate minimal generation time
            return Document(
                id=context.get("id", "test_doc"),
                content=f"Generated content for {context.get('id', 'test')}",
                type=context.get("type", "markdown")
            )
        generator.generate = AsyncMock(side_effect=generate_doc)
        
        # Configure tracking
        graph = DependencyGraph()
        tracking.get_dependency_graph = AsyncMock(return_value=graph)
        
        return config, storage, generator, tracking
    
    @pytest.fixture
    async def optimized_manager(self, mock_dependencies):
        """Create optimized suite manager."""
        config, storage, generator, tracking = mock_dependencies
        return OptimizedSuiteManager(
            config=config,
            storage=storage,
            generator=generator,
            tracking=tracking
        )
    
    @pytest.fixture
    async def original_manager(self, mock_dependencies):
        """Create original suite manager for comparison."""
        config, storage, generator, tracking = mock_dependencies
        return SuiteManager(
            config=config,
            storage=storage,
            generator=generator,
            tracking=tracking
        )
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_suite_generation_performance(self, optimized_manager):
        """Test suite generation meets <2s target for 10 documents."""
        # Create suite configuration with 10 documents
        suite_config = SuiteConfig(
            suite_id="perf_test_suite",
            documents=[
                {"id": f"doc_{i}", "type": "markdown", "template": "default"}
                for i in range(10)
            ],
            cross_references={
                "doc_0": ["doc_1", "doc_2"],
                "doc_1": ["doc_3", "doc_4"]
            }
        )
        
        # Measure generation time
        start_time = time.time()
        result = await optimized_manager.generate_suite(suite_config)
        generation_time = time.time() - start_time
        
        # Assertions
        assert result.success
        assert len(result.documents) == 10
        assert generation_time < 2.0, f"Suite generation took {generation_time:.2f}s (target: <2s)"
        
        # Check performance stats
        assert "throughput" in result.performance_stats
        assert result.performance_stats["throughput"] > 5  # >5 docs/second
        
        print(f"✓ Suite generation: {generation_time:.3f}s for 10 documents")
        print(f"  Throughput: {result.performance_stats['throughput']:.1f} docs/s")
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_consistency_analysis_performance(self, optimized_manager):
        """Test consistency analysis meets <1s target for 100 documents."""
        # Mock 100 documents for analysis
        documents = [
            Document(
                id=f"doc_{i}",
                content=f"Content for document {i} with [[reference_{i}]]",
                type="markdown" if i % 2 == 0 else "api"
            )
            for i in range(100)
        ]
        
        # Mock storage to return documents
        optimized_manager.storage.list_documents = AsyncMock(
            return_value=[doc.id for doc in documents]
        )
        optimized_manager.storage.get_document = AsyncMock(
            side_effect=lambda doc_id: next(
                (doc for doc in documents if doc.id == doc_id), None
            )
        )
        
        # Measure analysis time
        start_time = time.time()
        report = await optimized_manager.analyze_consistency("test_suite")
        analysis_time = time.time() - start_time
        
        # Assertions
        assert report.total_documents == 100
        assert analysis_time < 1.0, f"Consistency analysis took {analysis_time:.2f}s (target: <1s)"
        
        # Check performance stats
        assert "throughput" in report.performance_stats
        assert report.performance_stats["throughput"] > 100  # >100 docs/second
        
        print(f"✓ Consistency analysis: {analysis_time:.3f}s for 100 documents")
        print(f"  Throughput: {report.performance_stats['throughput']:.1f} docs/s")
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_impact_analysis_performance(self, optimized_manager):
        """Test impact analysis maintains <1s for large dependency graphs."""
        # Create a large dependency graph
        graph = DependencyGraph()
        
        # Add 500 nodes
        for i in range(500):
            graph.add_node(f"doc_{i}")
        
        # Add edges to create complex dependencies
        for i in range(500):
            # Each doc depends on 2-5 others
            for j in range(2, min(5, 500-i)):
                if i+j < 500:
                    graph.add_edge(f"doc_{i}", f"doc_{i+j}", RelationshipType.DEPENDS_ON)
        
        # Mock tracking to return large graph
        optimized_manager.tracking.get_dependency_graph = AsyncMock(return_value=graph)
        
        # Measure impact analysis time
        start_time = time.time()
        impact = await optimized_manager.analyze_impact("doc_0", ChangeType.BREAKING_CHANGE)
        analysis_time = time.time() - start_time
        
        # Assertions
        assert analysis_time < 1.0, f"Impact analysis took {analysis_time:.2f}s (target: <1s)"
        assert impact.accuracy_score >= 0.95
        assert impact.severity in [ImpactSeverity.HIGH, ImpactSeverity.CRITICAL]
        
        print(f"✓ Impact analysis: {analysis_time:.3f}s for 500-node graph")
        print(f"  Affected documents: {impact.total_affected}")
        print(f"  Accuracy: {impact.accuracy_score:.2%}")
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_concurrent_operations(self, optimized_manager):
        """Test support for 50+ concurrent operations."""
        # Create multiple suite configurations
        suite_configs = [
            SuiteConfig(
                suite_id=f"concurrent_suite_{i}",
                documents=[
                    {"id": f"suite_{i}_doc_{j}", "type": "markdown"}
                    for j in range(5)
                ]
            )
            for i in range(50)
        ]
        
        # Run 50 concurrent suite generations
        start_time = time.time()
        tasks = [
            optimized_manager.generate_suite(config)
            for config in suite_configs
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Count successes
        successful = sum(1 for r in results if not isinstance(r, Exception) and r.success)
        
        # Assertions
        assert successful >= 45, f"Only {successful}/50 concurrent operations succeeded"
        assert total_time < 30, f"50 concurrent operations took {total_time:.2f}s (target: <30s)"
        
        throughput = (successful * 5) / total_time  # Total docs generated per second
        
        print(f"✓ Concurrent operations: {successful}/50 succeeded in {total_time:.2f}s")
        print(f"  Overall throughput: {throughput:.1f} docs/s")
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_memory_mode_adaptation(self, mock_dependencies):
        """Test performance scales with memory modes."""
        config, storage, generator, tracking = mock_dependencies
        
        results = {}
        
        for mode in ["minimal", "balanced", "performance", "maximum"]:
            config.get_memory_mode.return_value = mode
            
            manager = OptimizedSuiteManager(
                config=config,
                storage=storage,
                generator=generator,
                tracking=tracking
            )
            
            # Check configuration
            batch_size = manager.get_batch_size()
            cache_size = manager.get_cache_size()
            
            # Run a consistency analysis
            documents = [
                Document(id=f"doc_{i}", content=f"Content {i}", type="markdown")
                for i in range(50)
            ]
            
            manager.storage.list_documents = AsyncMock(
                return_value=[doc.id for doc in documents]
            )
            manager.storage.get_document = AsyncMock(
                side_effect=lambda doc_id: next(
                    (doc for doc in documents if doc.id == doc_id), None
                )
            )
            
            start_time = time.time()
            report = await manager.analyze_consistency("test_suite")
            analysis_time = time.time() - start_time
            
            results[mode] = {
                "batch_size": batch_size,
                "cache_size": cache_size,
                "analysis_time": analysis_time
            }
        
        # Verify scaling
        assert results["minimal"]["batch_size"] < results["maximum"]["batch_size"]
        assert results["minimal"]["cache_size"] < results["maximum"]["cache_size"]
        assert results["maximum"]["analysis_time"] <= results["minimal"]["analysis_time"]
        
        print("✓ Memory mode adaptation:")
        for mode, stats in results.items():
            print(f"  {mode}: batch={stats['batch_size']}, "
                  f"cache={stats['cache_size']}, time={stats['analysis_time']:.3f}s")
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_cache_effectiveness(self, optimized_manager):
        """Test caching improves performance on repeated operations."""
        suite_config = SuiteConfig(
            suite_id="cache_test",
            documents=[
                {"id": f"doc_{i}", "type": "markdown"}
                for i in range(10)
            ]
        )
        
        # First generation (cache miss)
        start_time = time.time()
        result1 = await optimized_manager.generate_suite(suite_config)
        first_time = time.time() - start_time
        
        # Second generation (cache hit)
        start_time = time.time()
        result2 = await optimized_manager.generate_suite(suite_config)
        second_time = time.time() - start_time
        
        # Cache should make second call much faster
        assert second_time < first_time * 0.1, "Cache not effective"
        assert result2.performance_stats.get("cache_hit") == True
        
        # Check cache statistics
        stats = optimized_manager.get_performance_stats()
        assert stats["caching"]["cache_hits"] > 0
        assert stats["caching"]["cache_hit_ratio"] > 0
        
        print(f"✓ Cache effectiveness:")
        print(f"  First call: {first_time:.3f}s (cache miss)")
        print(f"  Second call: {second_time:.3f}s (cache hit)")
        print(f"  Speedup: {first_time/second_time:.1f}x")
        print(f"  Cache hit ratio: {stats['caching']['cache_hit_ratio']:.2%}")
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_performance_vs_original(self, optimized_manager, original_manager):
        """Compare optimized version against original implementation."""
        # Test configuration
        suite_config = SuiteConfig(
            suite_id="comparison_test",
            documents=[
                {"id": f"doc_{i}", "type": "markdown"}
                for i in range(20)
            ]
        )
        
        # Measure original implementation
        start_time = time.time()
        original_result = await original_manager.generate_suite(suite_config)
        original_time = time.time() - start_time
        
        # Measure optimized implementation
        start_time = time.time()
        optimized_result = await optimized_manager.generate_suite(suite_config)
        optimized_time = time.time() - start_time
        
        # Calculate improvement
        improvement = (original_time - optimized_time) / original_time * 100
        speedup = original_time / optimized_time
        
        # Assertions
        assert optimized_time < original_time, "Optimized version should be faster"
        assert improvement > 50, f"Expected >50% improvement, got {improvement:.1f}%"
        
        print(f"✓ Performance comparison:")
        print(f"  Original: {original_time:.3f}s")
        print(f"  Optimized: {optimized_time:.3f}s")
        print(f"  Improvement: {improvement:.1f}%")
        print(f"  Speedup: {speedup:.1f}x")
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_memory_usage(self, optimized_manager):
        """Test memory usage remains efficient during operations."""
        process = psutil.Process(os.getpid())
        
        # Get baseline memory
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Generate multiple large suites
        for i in range(5):
            suite_config = SuiteConfig(
                suite_id=f"memory_test_{i}",
                documents=[
                    {"id": f"suite_{i}_doc_{j}", "type": "markdown"}
                    for j in range(100)
                ]
            )
            await optimized_manager.generate_suite(suite_config)
        
        # Check memory after operations
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - baseline_memory
        
        # Memory increase should be reasonable (<100MB for this test)
        assert memory_increase < 100, f"Memory increased by {memory_increase:.1f}MB"
        
        print(f"✓ Memory usage:")
        print(f"  Baseline: {baseline_memory:.1f}MB")
        print(f"  Final: {final_memory:.1f}MB")
        print(f"  Increase: {memory_increase:.1f}MB")
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_performance_monitor(self, optimized_manager):
        """Test performance monitoring capabilities."""
        # Perform various operations
        suite_config = SuiteConfig(
            suite_id="monitor_test",
            documents=[{"id": f"doc_{i}", "type": "markdown"} for i in range(5)]
        )
        
        await optimized_manager.generate_suite(suite_config)
        await optimized_manager.analyze_consistency("monitor_test")
        await optimized_manager.analyze_impact("doc_0", ChangeType.UPDATE)
        
        # Get performance statistics
        stats = optimized_manager.get_performance_stats()
        
        # Verify statistics are collected
        assert stats["operations"]["suite_generations"] > 0
        assert stats["operations"]["consistency_analyses"] > 0
        assert stats["operations"]["impact_analyses"] > 0
        assert stats["performance"]["avg_generation_time"] > 0
        assert stats["performance"]["avg_consistency_time"] > 0
        assert stats["performance"]["avg_impact_time"] > 0
        
        # Check global performance monitor
        suite_stats = perf_monitor.get_stats("suite_generation")
        assert suite_stats["total_calls"] > 0
        assert suite_stats["avg_duration"] > 0
        assert suite_stats["throughput"] > 0
        
        print("✓ Performance monitoring:")
        print(f"  Operations tracked: {sum(stats['operations'].values())}")
        print(f"  Avg generation time: {stats['performance']['avg_generation_time']:.3f}s")
        print(f"  Avg consistency time: {stats['performance']['avg_consistency_time']:.3f}s")
        print(f"  Avg impact time: {stats['performance']['avg_impact_time']:.3f}s")


if __name__ == "__main__":
    # Run benchmarks with detailed output
    pytest.main([
        __file__,
        "-v",
        "-s",
        "-m", "benchmark",
        "--tb=short"
    ])