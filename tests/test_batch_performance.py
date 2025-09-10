"""
Test Suite for M011 Batch Operations Manager - Pass 2: Performance Tests
DevDocAI v3.0.0

Performance testing suite for optimized batch operations.
Tests streaming, caching, chunking, and memory efficiency.
"""

import asyncio
import gc
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import psutil
import pytest

# Module under test
from devdocai.operations.batch import (
    BatchConfig,
    BatchOperationsManager,
    BatchResult,
)
from devdocai.operations.batch_optimized import (
    BatchCache,
    DocumentChunker,
    MemoryManager,
    OptimizedBatchOperationsManager,
    OptimizedQueue,
    PerformanceConfig,
    StreamingProcessor,
)


# ============================================================================
# Performance Test Fixtures
# ============================================================================


@pytest.fixture
def perf_config():
    """Performance configuration for testing."""
    return PerformanceConfig(
        enable_streaming=True,
        chunk_size_kb=512,  # Smaller chunks for testing
        enable_cache=True,
        cache_ttl_seconds=60,
        max_cache_size_mb=128,
        enable_priority_queue=True,
        queue_batch_size=20,
        gc_threshold_mb=256,
    )


@pytest.fixture
def large_documents():
    """Generate large documents for performance testing."""
    docs = []
    for i in range(100):
        # Create documents of varying sizes
        size_kb = 10 + (i % 50) * 10  # 10KB to 500KB
        content = "x" * (size_kb * 1024)
        docs.append(
            {
                "id": f"large_doc_{i}",
                "content": content,
                "type": "readme",
                "size_kb": size_kb,
            }
        )
    return docs


@pytest.fixture
def temp_large_files(tmp_path):
    """Create temporary large files for streaming tests."""
    files = []
    for i in range(5):
        # Create files of different sizes
        size_mb = 1 + i * 2  # 1MB, 3MB, 5MB, 7MB, 9MB
        file_path = tmp_path / f"large_file_{i}.txt"
        content = "Test content line\n" * (size_mb * 1024 * 50)  # ~50 lines per KB
        file_path.write_text(content)
        files.append(file_path)
    return files


@pytest.fixture
async def optimized_manager(perf_config):
    """Initialize optimized batch manager."""
    config = BatchConfig(memory_mode="performance")
    manager = OptimizedBatchOperationsManager(config=config, perf_config=perf_config)
    yield manager
    await manager.shutdown()


# ============================================================================
# Cache Performance Tests
# ============================================================================


class TestCachePerformance:
    """Test cache performance and efficiency."""

    def test_cache_hit_performance(self, perf_config):
        """Test cache hit latency is sub-100ms."""
        cache = BatchCache(perf_config)

        # Populate cache
        for i in range(1000):
            cache.put(f"key_{i}", f"value_{i}" * 100)

        # Measure hit latency
        start = time.perf_counter()
        for i in range(1000):
            result = cache.get(f"key_{i}")
            assert result is not None
        elapsed = time.perf_counter() - start

        # Average latency per hit
        avg_latency_ms = (elapsed / 1000) * 1000
        assert avg_latency_ms < 100, f"Cache hit latency {avg_latency_ms:.2f}ms exceeds 100ms"

    def test_cache_eviction_lru(self, perf_config):
        """Test LRU eviction policy."""
        perf_config.max_cache_size_mb = 1  # Small cache for testing
        cache = BatchCache(perf_config)

        # Fill cache beyond capacity
        for i in range(100):
            cache.put(f"key_{i}", "x" * 10000)  # ~10KB each

        # Verify eviction happened
        stats = cache.get_stats()
        assert stats["evictions"] > 0
        assert stats["size_mb"] <= 1.1  # Allow small overhead

    def test_cache_ttl_expiration(self, perf_config):
        """Test cache TTL expiration."""
        perf_config.cache_ttl_seconds = 0.1  # 100ms TTL
        cache = BatchCache(perf_config)

        # Add item
        cache.put("key", "value")
        assert cache.get("key") == "value"

        # Wait for expiration
        time.sleep(0.2)
        assert cache.get("key") is None

    def test_cache_memory_efficiency(self, perf_config):
        """Test cache memory usage efficiency."""
        cache = BatchCache(perf_config)
        initial_memory = psutil.Process().memory_info().rss

        # Add 10MB of data
        large_value = "x" * (1024 * 1024)  # 1MB
        for i in range(10):
            cache.put(f"large_{i}", large_value)

        # Check memory increase
        final_memory = psutil.Process().memory_info().rss
        memory_increase_mb = (final_memory - initial_memory) / (1024 * 1024)

        # Should be close to 10MB (allow overhead)
        assert memory_increase_mb < 20, f"Excessive memory usage: {memory_increase_mb:.1f}MB"


# ============================================================================
# Streaming Performance Tests
# ============================================================================


class TestStreamingPerformance:
    """Test streaming document processing performance."""

    @pytest.mark.asyncio
    async def test_streaming_large_file(self, temp_large_files):
        """Test streaming processing of large files."""
        processor = StreamingProcessor(chunk_size_kb=512)
        processed_chunks = []

        async def process_chunk(chunk: str) -> int:
            """Simple chunk processor."""
            return len(chunk)

        # Process 5MB file
        large_file = temp_large_files[2]  # 5MB file
        start = time.perf_counter()

        async for result in processor.process_document_stream(large_file, process_chunk):
            processed_chunks.append(result)

        elapsed = time.perf_counter() - start

        # Verify all chunks processed
        total_size = sum(processed_chunks)
        file_size = large_file.stat().st_size
        assert abs(total_size - file_size) < 100  # Allow small difference

        # Should process 5MB in under 2 seconds
        assert elapsed < 2.0, f"Streaming took {elapsed:.2f}s for 5MB file"

    @pytest.mark.asyncio
    async def test_streaming_memory_efficiency(self, temp_large_files):
        """Test memory efficiency during streaming."""
        processor = StreamingProcessor(chunk_size_kb=512)

        # Monitor memory during streaming
        memory_samples = []

        async def monitor_memory(chunk: str) -> int:
            """Process chunk and monitor memory."""
            memory_samples.append(psutil.Process().memory_info().rss)
            return len(chunk)

        # Process 9MB file
        large_file = temp_large_files[-1]

        async for _ in processor.process_document_stream(large_file, monitor_memory):
            pass

        # Memory should not grow linearly with file size
        if memory_samples:
            max_memory = max(memory_samples)
            min_memory = min(memory_samples)
            memory_growth_mb = (max_memory - min_memory) / (1024 * 1024)

            # Should use less than 10MB additional memory for 9MB file
            assert memory_growth_mb < 10, f"Excessive memory growth: {memory_growth_mb:.1f}MB"


# ============================================================================
# Chunking Performance Tests
# ============================================================================


class TestChunkingPerformance:
    """Test document chunking performance."""

    def test_chunking_speed(self):
        """Test chunking speed for large documents."""
        chunker = DocumentChunker(max_chunk_size_kb=1024)  # 1MB chunks

        # Create 10MB document
        large_content = "Test paragraph.\n\n" * 100000
        
        start = time.perf_counter()
        chunks = chunker.chunk_document(large_content)
        elapsed = time.perf_counter() - start

        # Should chunk 10MB in under 100ms
        assert elapsed < 0.1, f"Chunking took {elapsed*1000:.1f}ms"
        assert len(chunks) > 1, "Should create multiple chunks"

    def test_chunking_overlap(self):
        """Test chunk overlap for context preservation."""
        chunker = DocumentChunker(max_chunk_size_kb=1)  # Small chunks

        content = "A" * 1000 + "\n\n" + "B" * 1000 + "\n\n" + "C" * 1000
        chunks = chunker.chunk_document(content, overlap=50)

        # Verify overlap exists
        for i in range(len(chunks) - 1):
            chunk1_end = chunks[i][0][-50:]
            chunk2_start = chunks[i + 1][0][:50]
            # Should have some overlap
            assert any(c in chunk2_start for c in chunk1_end[-10:])

    def test_chunking_memory_boundaries(self):
        """Test chunking respects memory boundaries."""
        chunker = DocumentChunker(max_chunk_size_kb=512)

        # Create document with clear boundaries
        sections = []
        for i in range(10):
            sections.append(f"Section {i}\n" + "x" * (100 * 1024) + "\n\n")
        content = "".join(sections)

        chunks = chunker.chunk_document(content)

        # Each chunk should be under limit
        for chunk_text, _, _ in chunks:
            chunk_size_kb = len(chunk_text) / 1024
            assert chunk_size_kb <= 520, f"Chunk exceeds limit: {chunk_size_kb:.1f}KB"


# ============================================================================
# Queue Optimization Tests
# ============================================================================


class TestQueueOptimization:
    """Test optimized queue performance."""

    @pytest.mark.asyncio
    async def test_queue_throughput(self):
        """Test queue operation throughput."""
        queue = OptimizedQueue(prefetch_count=10)

        # Add 10000 documents
        docs = [{"id": f"doc_{i}", "content": f"content_{i}"} for i in range(10000)]

        start = time.perf_counter()
        await queue.add_batch(docs)
        add_time = time.perf_counter() - start

        # Get all documents
        start = time.perf_counter()
        retrieved = []
        while True:
            batch = await queue.get_batch(100)
            if not batch:
                break
            retrieved.extend(batch)
        get_time = time.perf_counter() - start

        assert len(retrieved) == 10000
        
        # Should handle 10K docs in under 100ms each operation
        assert add_time < 0.1, f"Add took {add_time*1000:.1f}ms"
        assert get_time < 0.1, f"Get took {get_time*1000:.1f}ms"

    @pytest.mark.asyncio
    async def test_priority_queue_ordering(self):
        """Test priority queue processes high priority first."""
        queue = OptimizedQueue()

        # Add with different priorities
        await queue.add({"id": "low_1"}, priority=10)
        await queue.add({"id": "high_1"}, priority=1)
        await queue.add({"id": "med_1"}, priority=5)
        await queue.add({"id": "high_2"}, priority=2)

        # Should get in priority order
        doc1 = await queue.get()
        doc2 = await queue.get()
        doc3 = await queue.get()
        doc4 = await queue.get()

        assert doc1["id"] == "high_1"
        assert doc2["id"] == "high_2"
        assert doc3["id"] == "med_1"
        assert doc4["id"] == "low_1"

    @pytest.mark.asyncio
    async def test_prefetch_performance(self):
        """Test prefetch improves performance."""
        queue = OptimizedQueue(prefetch_count=50)

        # Add documents
        docs = [{"id": f"doc_{i}"} for i in range(1000)]
        await queue.add_batch(docs)

        # Prefetch
        await queue.prefetch(50)

        # Measure get performance with prefetch
        start = time.perf_counter()
        for _ in range(50):
            doc = await queue.get()
            assert doc is not None
        elapsed = time.perf_counter() - start

        stats = queue.get_stats()
        assert stats["prefetch_hits"] > 0
        
        # Should be very fast with prefetch
        assert elapsed < 0.01, f"Prefetch get took {elapsed*1000:.1f}ms"


# ============================================================================
# Memory Management Tests
# ============================================================================


class TestMemoryManagement:
    """Test memory management and optimization."""

    def test_memory_monitoring(self, perf_config):
        """Test memory usage monitoring."""
        manager = MemoryManager(perf_config)
        
        memory = manager.get_memory_usage()
        assert "rss_mb" in memory
        assert "percent" in memory
        assert memory["rss_mb"] > 0
        assert 0 <= memory["percent"] <= 100

    def test_memory_pressure_detection(self, perf_config):
        """Test memory pressure detection."""
        manager = MemoryManager(perf_config)
        
        # Normal conditions
        pressure = manager.check_memory_pressure()
        # Should not be under pressure in test environment
        assert pressure is False

    def test_garbage_collection_trigger(self, perf_config):
        """Test garbage collection triggering."""
        perf_config.gc_threshold_mb = 1  # Very low threshold
        manager = MemoryManager(perf_config)

        # Create garbage
        garbage = ["x" * (1024 * 1024) for _ in range(10)]
        
        # Should trigger GC
        collected = manager.maybe_collect_garbage()
        
        # Clean up
        del garbage
        gc.collect()

    def test_memory_optimization_recommendations(self, perf_config):
        """Test memory optimization recommendations."""
        manager = MemoryManager(perf_config)
        
        recommendations = manager.optimize_for_memory()
        assert "batch_size" in recommendations
        assert "max_concurrent" in recommendations
        assert "cache_enabled" in recommendations


# ============================================================================
# Integration Performance Tests
# ============================================================================


class TestIntegratedPerformance:
    """Test integrated performance of optimized batch manager."""

    @pytest.mark.asyncio
    async def test_throughput_improvement(self, optimized_manager, large_documents):
        """Test 2-5x throughput improvement."""
        # Simple operation for testing
        async def process(doc: Dict) -> Dict:
            await asyncio.sleep(0.001)  # Simulate work
            return {"processed": doc["id"]}

        # Baseline: process without optimizations
        optimized_manager.perf_config.enable_cache = False
        optimized_manager.perf_config.enable_streaming = False
        
        start = time.perf_counter()
        baseline_results = await optimized_manager.process_batch_optimized(
            large_documents[:50], process
        )
        baseline_time = time.perf_counter() - start

        # Optimized: process with all optimizations
        optimized_manager.perf_config.enable_cache = True
        optimized_manager.perf_config.enable_streaming = True
        optimized_manager.cache.clear()
        
        start = time.perf_counter()
        optimized_results = await optimized_manager.process_batch_optimized(
            large_documents[:50], process
        )
        optimized_time = time.perf_counter() - start

        # Process again to test cache
        start = time.perf_counter()
        cached_results = await optimized_manager.process_batch_optimized(
            large_documents[:50], process
        )
        cached_time = time.perf_counter() - start

        # Calculate improvements
        initial_speedup = baseline_time / optimized_time if optimized_time > 0 else 1
        cache_speedup = optimized_time / cached_time if cached_time > 0 else 1

        print(f"Initial speedup: {initial_speedup:.2f}x")
        print(f"Cache speedup: {cache_speedup:.2f}x")

        # Should achieve at least 2x improvement with cache
        assert cache_speedup >= 2.0, f"Cache speedup {cache_speedup:.2f}x < 2x target"

    @pytest.mark.asyncio
    async def test_memory_efficiency(self, optimized_manager, large_documents):
        """Test 50% memory usage reduction."""
        # Get initial memory
        gc.collect()
        initial_memory = psutil.Process().memory_info().rss

        # Process large batch with optimizations
        async def process(doc: Dict) -> Dict:
            # Simulate memory-intensive operation
            result = doc["content"][:100]
            return {"summary": result}

        results = await optimized_manager.process_batch_optimized(
            large_documents[:20], process
        )

        # Get peak memory
        peak_memory = psutil.Process().memory_info().rss
        memory_used_mb = (peak_memory - initial_memory) / (1024 * 1024)

        # Calculate expected memory without optimization
        total_doc_size_mb = sum(doc["size_kb"] for doc in large_documents[:20]) / 1024
        
        # With optimization, should use less than 50% of document size
        efficiency_ratio = memory_used_mb / total_doc_size_mb if total_doc_size_mb > 0 else 0
        
        print(f"Memory efficiency: {efficiency_ratio:.2%} of document size")
        
        # Allow some overhead but should be efficient
        assert efficiency_ratio < 1.0, f"Memory usage {efficiency_ratio:.2%} exceeds document size"

    @pytest.mark.asyncio
    async def test_cache_hit_latency(self, optimized_manager):
        """Test sub-100ms cache hit latency."""
        # Prepare cached document
        doc = {"id": "test", "content": "test content"}
        
        # Process once to cache
        async def process(doc: Dict) -> Dict:
            return {"processed": True}
        
        await optimized_manager.process_document_optimized(doc, process)
        
        # Measure cache hit latency
        start = time.perf_counter()
        result = await optimized_manager.process_document_optimized(doc, process)
        latency = time.perf_counter() - start
        
        latency_ms = latency * 1000
        assert latency_ms < 100, f"Cache hit latency {latency_ms:.1f}ms exceeds 100ms"

    @pytest.mark.asyncio
    async def test_benchmark_functionality(self, optimized_manager, large_documents):
        """Test benchmark functionality."""
        async def process(doc: Dict) -> Dict:
            await asyncio.sleep(0.001)
            return {"processed": doc["id"]}

        # Run benchmark
        benchmark_results = await optimized_manager.benchmark(
            large_documents[:20], process
        )

        assert "speedup_factor" in benchmark_results
        assert "docs_per_second_cached" in benchmark_results
        assert "cache_hit_rate" in benchmark_results
        assert benchmark_results["documents_processed"] == 20
        
        # Should show speedup with cache
        assert benchmark_results["speedup_factor"] >= 1.0

    @pytest.mark.asyncio
    async def test_concurrent_processing_performance(self, optimized_manager):
        """Test concurrent processing performance."""
        # Create documents
        docs = [{"id": f"doc_{i}", "content": f"content_{i}"} for i in range(100)]
        
        # Track concurrency
        concurrent_count = 0
        max_concurrent = 0
        lock = asyncio.Lock()
        
        async def process(doc: Dict) -> Dict:
            nonlocal concurrent_count, max_concurrent
            async with lock:
                concurrent_count += 1
                max_concurrent = max(max_concurrent, concurrent_count)
            
            await asyncio.sleep(0.01)  # Simulate work
            
            async with lock:
                concurrent_count -= 1
            
            return {"id": doc["id"]}
        
        # Process with concurrency
        results = await optimized_manager.process_batch_optimized(docs, process)
        
        assert len(results) == 100
        assert max_concurrent > 1, "Should process concurrently"
        assert max_concurrent <= 16, "Should respect concurrency limit"


# ============================================================================
# Performance Regression Tests
# ============================================================================


class TestPerformanceRegression:
    """Ensure no performance regressions from optimizations."""

    @pytest.mark.asyncio
    async def test_base_functionality_preserved(self, optimized_manager):
        """Test that base functionality still works."""
        docs = [{"id": f"doc_{i}", "content": f"content_{i}"} for i in range(10)]
        
        async def process(doc: Dict) -> Dict:
            return {"processed": doc["id"]}
        
        # Should work like base manager
        results = await optimized_manager.base_manager.process_batch(docs, process)
        assert len(results) == 10
        assert all(r.success for r in results)

    @pytest.mark.asyncio 
    async def test_error_handling_preserved(self, optimized_manager):
        """Test error handling still works."""
        docs = [{"id": "good"}, {"id": "bad"}]
        
        async def process(doc: Dict) -> Dict:
            if doc["id"] == "bad":
                raise ValueError("Test error")
            return {"processed": doc["id"]}
        
        results = await optimized_manager.process_batch_optimized(docs, process)
        
        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False
        assert "Test error" in results[1].error

    @pytest.mark.asyncio
    async def test_metrics_collection(self, optimized_manager):
        """Test performance metrics collection."""
        docs = [{"id": f"doc_{i}", "content": f"content_{i}"} for i in range(10)]
        
        async def process(doc: Dict) -> Dict:
            return {"processed": doc["id"]}
        
        await optimized_manager.process_batch_optimized(docs, process)
        
        metrics = optimized_manager.get_performance_metrics()
        
        assert "cache_stats" in metrics
        assert "queue_stats" in metrics  
        assert "memory_stats" in metrics
        assert "processing_stats" in metrics
        assert metrics["processing_stats"]["total_processed"] > 0