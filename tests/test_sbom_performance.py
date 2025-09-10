"""
Tests for M010 SBOM Generator - Performance Optimization
DevDocAI v3.0.0

This test suite validates performance optimizations including:
- Parallel dependency scanning
- Multi-tier caching
- Batch vulnerability scanning
- Async I/O operations
- Streaming exports
- Memory management
"""

import asyncio
import json
import time
from unittest.mock import MagicMock, patch

import pytest

from devdocai.compliance.sbom_performance import (
    AsyncFileHandler,
    BatchProcessor,
    CacheManager,
    ConnectionPool,
    MemoryManager,
    MultiTierCache,
    ParallelProcessor,
    PerformanceMonitor,
    PerformanceOptimizer,
    StreamingExporter,
    cached_result,
    measure_performance,
)

# ============================================================================
# Multi-Tier Cache Tests
# ============================================================================


class TestMultiTierCache:
    """Test multi-tier caching system."""

    def test_cache_basic_operations(self):
        """Test basic cache get/set operations."""
        cache = MultiTierCache(max_size=3, ttl_seconds=10)

        # Test set and get
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        # Test miss
        assert cache.get("nonexistent") is None

        # Test hit ratio
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss
        assert cache.hit_ratio == 2 / 3  # 2 hits, 1 miss

    def test_cache_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = MultiTierCache(max_size=3, ttl_seconds=10)

        # Fill cache
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Access key1 to make it recently used
        cache.get("key1")

        # Add new item, should evict key2 (least recently used)
        cache.set("key4", "value4")

        assert cache.get("key1") == "value1"  # Still exists
        assert cache.get("key2") is None  # Evicted
        assert cache.get("key3") == "value3"  # Still exists
        assert cache.get("key4") == "value4"  # New item

    def test_cache_ttl_expiration(self):
        """Test TTL expiration."""
        cache = MultiTierCache(max_size=10, ttl_seconds=0.1)  # 100ms TTL

        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        # Wait for expiration
        time.sleep(0.2)
        assert cache.get("key1") is None  # Expired

    def test_cache_stats(self):
        """Test cache statistics."""
        cache = MultiTierCache(max_size=10, ttl_seconds=10)

        cache.set("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss

        stats = cache.get_stats()
        assert stats["size"] == 1
        assert stats["max_size"] == 10
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_ratio"] == 0.5


class TestCacheManager:
    """Test cache manager."""

    def test_cache_manager_initialization(self):
        """Test cache manager initialization."""
        manager = CacheManager()

        assert manager.dependency_cache is not None
        assert manager.license_cache is not None
        assert manager.vulnerability_cache is not None

    def test_cache_key_generation(self):
        """Test cache key generation."""
        manager = CacheManager()

        key1 = manager.get_cache_key("func", ["arg1", "arg2"], {"kwarg": "value"})
        key2 = manager.get_cache_key("func", ["arg1", "arg2"], {"kwarg": "value"})
        key3 = manager.get_cache_key("func", ["arg1", "arg3"], {"kwarg": "value"})

        assert key1 == key2  # Same inputs produce same key
        assert key1 != key3  # Different inputs produce different keys
        assert len(key1) == 64  # SHA256 hash length

    def test_cache_cleanup(self):
        """Test cache cleanup."""
        manager = CacheManager()

        # Add items to caches
        manager.dependency_cache.set("key1", "value1")
        manager.license_cache.set("key2", "value2")
        manager.vulnerability_cache.set("key3", "value3")

        # Perform cleanup (won't remove non-expired items)
        manager.periodic_cleanup()

        assert manager.dependency_cache.get("key1") == "value1"
        assert manager.license_cache.get("key2") == "value2"
        assert manager.vulnerability_cache.get("key3") == "value3"


# ============================================================================
# Performance Monitor Tests
# ============================================================================


class TestPerformanceMonitor:
    """Test performance monitoring."""

    def test_record_operation(self):
        """Test recording operation metrics."""
        monitor = PerformanceMonitor()

        monitor.record_operation("scan", 0.5, size=100, cache_hit=False)
        monitor.record_operation("scan", 0.3, size=50, cache_hit=True)
        monitor.record_operation("detect", 0.1, cache_hit=False)

        metrics = monitor.get_metrics()

        assert metrics["total_operations"] == 3
        assert "scan" in metrics["operations"]
        assert "detect" in metrics["operations"]

        scan_metrics = metrics["operations"]["scan"]
        assert scan_metrics["count"] == 2
        assert scan_metrics["total_time"] == 0.8
        assert scan_metrics["min_time"] == 0.3
        assert scan_metrics["max_time"] == 0.5
        assert scan_metrics["cache_hits"] == 1
        assert scan_metrics["cache_misses"] == 1
        assert scan_metrics["total_size"] == 150


# ============================================================================
# Parallel Processing Tests
# ============================================================================


class TestParallelProcessor:
    """Test parallel processing utilities."""

    def test_process_batch(self):
        """Test batch processing."""
        processor = ParallelProcessor(max_workers=2)

        items = list(range(10))

        def square(x):
            return x * x

        results = processor.process_batch(items, square, chunk_size=3)

        # Verify results
        expected = [x * x for x in items]
        assert len(results) == len(expected)
        # Results might be out of order due to parallel processing

        processor.shutdown()

    def test_map_async(self):
        """Test async mapping."""
        processor = ParallelProcessor(max_workers=2)

        items = [1, 2, 3, 4, 5]

        def double(x):
            return x * 2

        results = processor.map_async(double, items)

        assert len(results) == len(items)
        # Verify all items were processed (order might differ)

        processor.shutdown()

    def test_error_handling(self):
        """Test error handling in parallel processing."""
        processor = ParallelProcessor(max_workers=2)

        items = [1, 2, "invalid", 4]

        def process(x):
            if isinstance(x, str):
                raise ValueError("Invalid input")
            return x * 2

        results = processor.process_batch(items, process, chunk_size=2)

        # Should handle errors gracefully
        assert len(results) == len(items)
        assert None in results  # Failed item returns None

        processor.shutdown()


# ============================================================================
# Async I/O Tests
# ============================================================================


class TestAsyncFileHandler:
    """Test async file operations."""

    @pytest.mark.asyncio
    async def test_read_write_async(self, tmp_path):
        """Test async read/write operations."""
        file_path = tmp_path / "test.txt"
        content = "Test content\nLine 2"

        # Write async
        await AsyncFileHandler.write_file_async(file_path, content)

        # Read async
        read_content = await AsyncFileHandler.read_file_async(file_path)

        assert read_content == content

    @pytest.mark.asyncio
    async def test_json_async(self, tmp_path):
        """Test async JSON operations."""
        file_path = tmp_path / "test.json"
        data = {"key": "value", "number": 42, "list": [1, 2, 3]}

        # Write JSON async
        await AsyncFileHandler.write_json_async(file_path, data)

        # Read JSON async
        read_data = await AsyncFileHandler.read_json_async(file_path)

        assert read_data == data

    @pytest.mark.asyncio
    async def test_error_handling(self, tmp_path):
        """Test error handling in async operations."""
        # Try to read non-existent file
        file_path = tmp_path / "nonexistent.txt"

        with pytest.raises(FileNotFoundError):
            await AsyncFileHandler.read_file_async(file_path)


# ============================================================================
# Batch Processing Tests
# ============================================================================


class TestBatchProcessor:
    """Test batch processing."""

    def test_batch_accumulation(self):
        """Test batch accumulation and processing."""
        processor = BatchProcessor(batch_size=3)

        # Add items to batch
        assert processor.add_to_batch("op1", "item1") is None
        assert processor.add_to_batch("op2", "item2") is None

        # Third item triggers batch processing
        batch = processor.add_to_batch("op3", "item3")

        assert batch is not None
        assert len(batch) == 3
        assert batch[0] == ("op1", "item1")
        assert batch[1] == ("op2", "item2")
        assert batch[2] == ("op3", "item3")

    def test_flush_batch(self):
        """Test flushing remaining items."""
        processor = BatchProcessor(batch_size=5)

        processor.add_to_batch("op1", "item1")
        processor.add_to_batch("op2", "item2")

        # Flush remaining items
        batch = processor.flush()

        assert len(batch) == 2
        assert batch[0] == ("op1", "item1")
        assert batch[1] == ("op2", "item2")

        # Queue should be empty
        assert processor.flush() == []


# ============================================================================
# Memory Management Tests
# ============================================================================


class TestMemoryManager:
    """Test memory management."""

    @patch("psutil.Process")
    def test_memory_check(self, mock_process_class):
        """Test memory checking."""
        mock_process = MagicMock()
        mock_process.memory_info.return_value.rss = 50 * 1024 * 1024  # 50MB
        mock_process_class.return_value = mock_process

        manager = MemoryManager(max_memory_mb=100)

        # First checks don't actually check (interval)
        for _ in range(9):
            assert manager.check_memory() is True

        # 10th check performs actual memory check
        assert manager.check_memory() is True  # 50MB < 100MB limit

        # Simulate exceeding memory
        mock_process.memory_info.return_value.rss = 150 * 1024 * 1024  # 150MB

        # Need to reach check interval again
        for _ in range(9):
            manager.check_memory()

        assert manager.check_memory() is False  # 150MB > 100MB limit

    @patch("psutil.virtual_memory")
    @patch("psutil.Process")
    def test_memory_stats(self, mock_process_class, mock_virtual_memory):
        """Test memory statistics."""
        mock_process = MagicMock()
        mock_process.memory_info.return_value.rss = 100 * 1024 * 1024
        mock_process.memory_info.return_value.vms = 200 * 1024 * 1024
        mock_process.memory_percent.return_value = 5.0
        mock_process_class.return_value = mock_process

        mock_virtual_memory.return_value.available = 4 * 1024 * 1024 * 1024

        manager = MemoryManager()
        stats = manager.get_memory_stats()

        assert stats["rss_mb"] == 100.0
        assert stats["vms_mb"] == 200.0
        assert stats["percent"] == 5.0
        assert stats["available_mb"] == 4096.0


# ============================================================================
# Connection Pool Tests
# ============================================================================


class TestConnectionPool:
    """Test connection pooling."""

    def test_connection_management(self):
        """Test connection pool management."""
        pool = ConnectionPool(max_connections=5)

        # Get connection
        conn1 = pool.get_connection("api.example.com")
        assert conn1 is not None
        assert conn1["requests"] == 1

        # Get same connection again
        conn2 = pool.get_connection("api.example.com")
        assert conn2 is conn1
        assert conn2["requests"] == 2

        # Get different endpoint
        conn3 = pool.get_connection("api.other.com")
        assert conn3 is not conn1
        assert conn3["requests"] == 1

        # Close all connections
        pool.close_all()

        # New connection after close
        conn4 = pool.get_connection("api.example.com")
        assert conn4["requests"] == 1  # Reset after close


# ============================================================================
# Streaming Export Tests
# ============================================================================


class TestStreamingExporter:
    """Test streaming export."""

    @pytest.mark.asyncio
    async def test_stream_json_export(self, tmp_path):
        """Test streaming JSON export."""
        output_path = tmp_path / "large_sbom.json"

        # Create large data structure
        data = {"packages": [{"name": f"package_{i}", "version": f"1.0.{i}"} for i in range(1000)]}

        # Stream export
        await StreamingExporter.stream_json_export(data, output_path)

        # Verify file was created and contains correct data
        assert output_path.exists()

        with open(output_path) as f:
            loaded_data = json.load(f)

        assert len(loaded_data["packages"]) == 1000
        assert loaded_data["packages"][0]["name"] == "package_0"
        assert loaded_data["packages"][999]["name"] == "package_999"


# ============================================================================
# Performance Optimizer Tests
# ============================================================================


class TestPerformanceOptimizer:
    """Test performance optimizer."""

    def test_optimizer_initialization(self):
        """Test optimizer initialization."""
        optimizer = PerformanceOptimizer()

        assert optimizer.cache_manager is not None
        assert optimizer.perf_monitor is not None
        assert optimizer.parallel_processor is not None
        assert optimizer.batch_processor is not None
        assert optimizer.memory_manager is not None
        assert optimizer.connection_pool is not None

    def test_optimization_settings(self):
        """Test optimization settings for operations."""
        optimizer = PerformanceOptimizer()

        # Test dependency scan settings
        dep_settings = optimizer.optimize_operation("dependency_scan")
        assert dep_settings["parallel"] is True
        assert dep_settings["cache"] is True
        assert dep_settings["max_workers"] == 8

        # Test vulnerability scan settings
        vuln_settings = optimizer.optimize_operation("vulnerability_scan")
        assert vuln_settings["parallel"] is True
        assert vuln_settings["cache"] is True
        assert vuln_settings["batch"] is True

        # Test export settings
        export_settings = optimizer.optimize_operation("sbom_export")
        assert export_settings["streaming"] is True
        assert export_settings["parallel"] is False

    def test_performance_report(self):
        """Test performance report generation."""
        optimizer = PerformanceOptimizer()

        # Record some operations
        optimizer.perf_monitor.record_operation("test_op", 0.5, size=100)

        report = optimizer.get_performance_report()

        assert "cache_stats" in report
        assert "performance_metrics" in report
        assert "memory_stats" in report

        # Check structure
        assert "dependency" in report["cache_stats"]
        assert "total_operations" in report["performance_metrics"]
        assert "rss_mb" in report["memory_stats"]

    def test_cleanup(self):
        """Test resource cleanup."""
        optimizer = PerformanceOptimizer()

        # Should not raise any errors
        optimizer.cleanup()


# ============================================================================
# Decorator Tests
# ============================================================================


class TestDecorators:
    """Test performance decorators."""

    def test_cached_result_decorator(self):
        """Test cached result decorator."""

        class TestClass:
            def __init__(self):
                self._cache_manager = CacheManager()
                self.call_count = 0

            @cached_result("dependency")
            def expensive_operation(self, arg1, arg2):
                self.call_count += 1
                return f"result_{arg1}_{arg2}"

        obj = TestClass()

        # First call - not cached
        result1 = obj.expensive_operation("a", "b")
        assert result1 == "result_a_b"
        assert obj.call_count == 1

        # Second call - should be cached
        result2 = obj.expensive_operation("a", "b")
        assert result2 == "result_a_b"
        assert obj.call_count == 1  # Not incremented

        # Different arguments - not cached
        result3 = obj.expensive_operation("c", "d")
        assert result3 == "result_c_d"
        assert obj.call_count == 2

    def test_measure_performance_decorator(self):
        """Test performance measurement decorator."""

        class TestClass:
            def __init__(self):
                self._perf_monitor = PerformanceMonitor()

            @measure_performance("custom_op")
            def timed_operation(self, value):
                time.sleep(0.01)  # Simulate work
                return value * 2

        obj = TestClass()

        result = obj.timed_operation(5)
        assert result == 10

        # Check that operation was recorded
        metrics = obj._perf_monitor.get_metrics()
        assert "custom_op" in metrics["operations"]
        assert metrics["operations"]["custom_op"]["count"] == 1
        assert metrics["operations"]["custom_op"]["total_time"] >= 0.01


# ============================================================================
# Integration Tests
# ============================================================================


class TestPerformanceIntegration:
    """Integration tests for performance optimizations."""

    def test_parallel_caching_integration(self):
        """Test integration of parallel processing with caching."""
        optimizer = PerformanceOptimizer()

        # Create items to process
        items = list(range(100))

        def process_item(item):
            # Simulate work
            time.sleep(0.001)
            return item * item

        # Process items in parallel
        start_time = time.time()
        results = optimizer.parallel_processor.process_batch(items, process_item, chunk_size=10)
        duration = time.time() - start_time

        # Should be faster than sequential (100 * 0.001 = 0.1s)
        assert duration < 0.1
        assert len(results) == 100

        optimizer.cleanup()

    @pytest.mark.asyncio
    async def test_async_batch_integration(self, tmp_path):
        """Test integration of async I/O with batch processing."""
        optimizer = PerformanceOptimizer()

        # Create batch of files to write
        files_data = [
            (tmp_path / f"file_{i}.json", {"id": i, "data": f"content_{i}"}) for i in range(10)
        ]

        # Write files asynchronously
        tasks = [AsyncFileHandler.write_json_async(path, data) for path, data in files_data]
        await asyncio.gather(*tasks)

        # Verify all files were written
        for path, expected_data in files_data:
            assert path.exists()
            data = await AsyncFileHandler.read_json_async(path)
            assert data == expected_data

        optimizer.cleanup()


# ============================================================================
# Benchmark Tests
# ============================================================================


@pytest.mark.benchmark
class TestPerformanceBenchmarks:
    """Benchmark tests to validate performance targets."""

    def test_cache_performance(self, benchmark):
        """Benchmark cache operations."""
        cache = MultiTierCache(max_size=1000, ttl_seconds=3600)

        # Pre-populate cache
        for i in range(100):
            cache.set(f"key_{i}", f"value_{i}")

        def cache_operations():
            # Mix of hits and misses
            for i in range(50):
                cache.get(f"key_{i}")  # Hit
            for i in range(100, 110):
                cache.get(f"key_{i}")  # Miss

        benchmark(cache_operations)

        # Should complete quickly
        assert cache.hit_ratio > 0.7  # Most operations are hits

    def test_parallel_processing_speedup(self, benchmark):
        """Benchmark parallel processing speedup."""
        processor = ParallelProcessor(max_workers=8)

        items = list(range(500))

        def cpu_bound_task(x):
            # Simulate CPU-intensive work
            result = 0
            for i in range(1000):
                result += x * i
            return result

        def parallel_run():
            return processor.process_batch(items, cpu_bound_task, chunk_size=50)

        result = benchmark(parallel_run)

        processor.shutdown()

        # Verify correctness
        assert len(result) == 500

    @pytest.mark.asyncio
    async def test_streaming_export_memory(self, tmp_path):
        """Test streaming export memory efficiency."""
        import psutil

        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024

        # Create large SBOM data (simulate 1000+ packages)
        large_data = {
            "packages": [
                {
                    "name": f"package_{i}",
                    "version": f"1.0.{i}",
                    "description": "A" * 1000,  # Large description
                    "dependencies": [f"dep_{j}" for j in range(10)],
                }
                for i in range(1000)
            ]
        }

        output_path = tmp_path / "large_sbom.json"

        # Stream export
        await StreamingExporter.stream_json_export(large_data, output_path)

        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory

        # Memory increase should be minimal due to streaming
        assert memory_increase < 50  # Less than 50MB increase
        assert output_path.exists()

        # Verify file size is substantial
        file_size_mb = output_path.stat().st_size / 1024 / 1024
        assert file_size_mb > 1  # Should be >1MB
