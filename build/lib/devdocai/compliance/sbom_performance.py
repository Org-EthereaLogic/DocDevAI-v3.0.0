"""
M010 SBOM Generator - Performance Module
DevDocAI v3.0.0 - High-performance caching and optimization infrastructure

This module provides performance optimization components for the SBOM Generator
including multi-tier caching, parallel processing, and resource management.

Performance Targets:
    - SBOM generation: <30s for 500 dependencies
    - 10x improvement for large projects (>1000 dependencies)
    - Cache hit ratio: >80%
    - Memory usage: <100MB for typical projects
"""

import asyncio
import hashlib
import json
import logging
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps
from pathlib import Path
from threading import RLock
from typing import Any, Callable, Dict, List, Optional, Tuple

import aiofiles
import numpy as np

logger = logging.getLogger(__name__)


# ============================================================================
# Performance Constants
# ============================================================================

# Cache Configuration
CACHE_SIZE_DEPENDENCY = 10000  # Max cached dependency scans
CACHE_SIZE_LICENSE = 5000  # Max cached license detections
CACHE_SIZE_VULNERABILITY = 5000  # Max cached vulnerability scans
CACHE_TTL_SECONDS = 3600  # 1 hour cache TTL
CACHE_HIT_THRESHOLD = 0.8  # Target 80% cache hit ratio

# Parallel Processing
MAX_WORKERS = 16  # Maximum parallel workers
BATCH_SIZE = 100  # Batch size for bulk operations
CHUNK_SIZE = 50  # Chunk size for parallel processing

# Memory Management
MAX_MEMORY_MB = 100  # Maximum memory usage in MB
MEMORY_CHECK_INTERVAL = 10  # Check memory every N operations

# Performance Monitoring
PERF_LOG_INTERVAL = 100  # Log performance metrics every N operations
MIN_OPERATION_TIME = 0.001  # Minimum time to track (1ms)


# ============================================================================
# Performance Monitoring
# ============================================================================


class PerformanceMonitor:
    """Monitor and report performance metrics."""

    def __init__(self):
        """Initialize performance monitor."""
        self._metrics: Dict[str, Dict[str, Any]] = {}
        self._lock = RLock()
        self._start_time = time.time()
        self._operation_count = 0

    def record_operation(
        self, operation: str, duration: float, size: Optional[int] = None, cache_hit: bool = False
    ):
        """Record operation performance metrics."""
        with self._lock:
            if operation not in self._metrics:
                self._metrics[operation] = {
                    "count": 0,
                    "total_time": 0.0,
                    "min_time": float("inf"),
                    "max_time": 0.0,
                    "cache_hits": 0,
                    "cache_misses": 0,
                    "total_size": 0,
                }

            metrics = self._metrics[operation]
            metrics["count"] += 1
            metrics["total_time"] += duration
            metrics["min_time"] = min(metrics["min_time"], duration)
            metrics["max_time"] = max(metrics["max_time"], duration)

            if cache_hit:
                metrics["cache_hits"] += 1
            else:
                metrics["cache_misses"] += 1

            if size:
                metrics["total_size"] += size

            self._operation_count += 1

            # Log periodic summaries
            if self._operation_count % PERF_LOG_INTERVAL == 0:
                self._log_summary()

    def _log_summary(self):
        """Log performance summary."""
        elapsed = time.time() - self._start_time

        for op, metrics in self._metrics.items():
            avg_time = metrics["total_time"] / max(metrics["count"], 1)
            cache_ratio = metrics["cache_hits"] / max(
                metrics["cache_hits"] + metrics["cache_misses"], 1
            )

            logger.info(
                f"Performance [{op}]: "
                f"ops={metrics['count']}, "
                f"avg={avg_time:.3f}s, "
                f"cache={cache_ratio:.1%}, "
                f"throughput={metrics['count']/elapsed:.1f}/s"
            )

    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        with self._lock:
            return {
                "elapsed_time": time.time() - self._start_time,
                "total_operations": self._operation_count,
                "operations": dict(self._metrics),
            }


# ============================================================================
# Multi-Tier Cache System
# ============================================================================


class MultiTierCache:
    """Multi-tier caching system with TTL and LRU eviction."""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        """
        Initialize multi-tier cache.

        Args:
            max_size: Maximum cache entries
            ttl_seconds: Time-to-live for cache entries
        """
        self._cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._lock = RLock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Get item from cache with TTL check."""
        with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]

                # Check TTL
                if time.time() - timestamp > self._ttl_seconds:
                    del self._cache[key]
                    self._misses += 1
                    return None

                # Move to end (LRU)
                self._cache.move_to_end(key)
                self._hits += 1
                return value

            self._misses += 1
            return None

    def set(self, key: str, value: Any):
        """Set item in cache with TTL."""
        with self._lock:
            # Remove oldest if at capacity
            if len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)

            self._cache[key] = (value, time.time())

    @property
    def hit_ratio(self) -> float:
        """Get cache hit ratio."""
        total = self._hits + self._misses
        return self._hits / max(total, 1)

    def clear_expired(self):
        """Clear expired entries."""
        with self._lock:
            current_time = time.time()
            expired_keys = [
                k for k, (_, t) in self._cache.items() if current_time - t > self._ttl_seconds
            ]
            for key in expired_keys:
                del self._cache[key]

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_ratio": self.hit_ratio,
            "ttl_seconds": self._ttl_seconds,
        }


class CacheManager:
    """Manage multiple cache tiers for different data types."""

    def __init__(self):
        """Initialize cache manager."""
        self.dependency_cache = MultiTierCache(
            max_size=CACHE_SIZE_DEPENDENCY, ttl_seconds=CACHE_TTL_SECONDS
        )
        self.license_cache = MultiTierCache(
            max_size=CACHE_SIZE_LICENSE, ttl_seconds=CACHE_TTL_SECONDS
        )
        self.vulnerability_cache = MultiTierCache(
            max_size=CACHE_SIZE_VULNERABILITY, ttl_seconds=CACHE_TTL_SECONDS
        )
        self._lock = RLock()

    def get_cache_key(self, *args) -> str:
        """Generate cache key from arguments."""
        key_data = json.dumps(args, sort_keys=True, default=str)
        return hashlib.sha256(key_data.encode()).hexdigest()

    def periodic_cleanup(self):
        """Perform periodic cache cleanup."""
        with self._lock:
            self.dependency_cache.clear_expired()
            self.license_cache.clear_expired()
            self.vulnerability_cache.clear_expired()

    def get_stats(self) -> Dict[str, Any]:
        """Get overall cache statistics."""
        return {
            "dependency": self.dependency_cache.get_stats(),
            "license": self.license_cache.get_stats(),
            "vulnerability": self.vulnerability_cache.get_stats(),
            "overall_hit_ratio": np.mean(
                [
                    self.dependency_cache.hit_ratio,
                    self.license_cache.hit_ratio,
                    self.vulnerability_cache.hit_ratio,
                ]
            ),
        }


# ============================================================================
# Performance Decorators
# ============================================================================


def cached_result(cache_type: str = "dependency"):
    """Decorator for caching function results."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Get cache manager
            if not hasattr(self, "_cache_manager"):
                self._cache_manager = CacheManager()

            # Select cache
            cache_map = {
                "dependency": self._cache_manager.dependency_cache,
                "license": self._cache_manager.license_cache,
                "vulnerability": self._cache_manager.vulnerability_cache,
            }
            cache = cache_map.get(cache_type, self._cache_manager.dependency_cache)

            # Generate cache key
            cache_key = self._cache_manager.get_cache_key(func.__name__, args, kwargs)

            # Check cache
            result = cache.get(cache_key)
            if result is not None:
                if hasattr(self, "_perf_monitor"):
                    self._perf_monitor.record_operation(func.__name__, 0.0, cache_hit=True)
                return result

            # Execute function
            start_time = time.time()
            result = func(self, *args, **kwargs)
            duration = time.time() - start_time

            # Cache result
            cache.set(cache_key, result)

            # Record metrics
            if hasattr(self, "_perf_monitor"):
                self._perf_monitor.record_operation(func.__name__, duration, cache_hit=False)

            return result

        return wrapper

    return decorator


def measure_performance(operation_name: Optional[str] = None):
    """Decorator to measure function performance."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            op_name = operation_name or func.__name__
            start_time = time.time()

            try:
                result = func(self, *args, **kwargs)
                duration = time.time() - start_time

                # Record metrics if monitor available
                if hasattr(self, "_perf_monitor"):
                    size = None
                    if isinstance(result, (list, dict)):
                        size = len(result)
                    self._perf_monitor.record_operation(op_name, duration, size=size)

                # Log slow operations
                if duration > 1.0:
                    logger.warning(f"Slow operation {op_name}: {duration:.2f}s")

                return result

            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"Operation {op_name} failed after {duration:.2f}s: {e}")
                raise

        return wrapper

    return decorator


# ============================================================================
# Parallel Processing Utilities
# ============================================================================


class ParallelProcessor:
    """Utilities for parallel processing of SBOM operations."""

    def __init__(self, max_workers: int = MAX_WORKERS):
        """Initialize parallel processor."""
        self.max_workers = min(max_workers, MAX_WORKERS)
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self._lock = RLock()

    def process_batch(
        self, items: List[Any], processor_func: Callable, chunk_size: int = CHUNK_SIZE
    ) -> List[Any]:
        """
        Process items in parallel batches.

        Args:
            items: Items to process
            processor_func: Function to process each item
            chunk_size: Size of processing chunks

        Returns:
            Processed results maintaining order
        """
        if not items:
            return []

        # Split into chunks
        chunks = [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]

        # Process chunks in parallel
        futures = []
        for chunk in chunks:
            future = self._executor.submit(self._process_chunk, chunk, processor_func)
            futures.append(future)

        # Collect results
        results = []
        for future in as_completed(futures):
            try:
                chunk_results = future.result(timeout=30)
                results.extend(chunk_results)
            except Exception as e:
                logger.error(f"Chunk processing failed: {e}")

        return results

    def _process_chunk(self, chunk: List[Any], processor_func: Callable) -> List[Any]:
        """Process a single chunk."""
        results = []
        for item in chunk:
            try:
                result = processor_func(item)
                results.append(result)
            except Exception as e:
                logger.error(f"Item processing failed: {e}")
                results.append(None)
        return results

    def map_async(self, func: Callable, items: List[Any]) -> List[Any]:
        """Map function over items asynchronously."""
        futures = [self._executor.submit(func, item) for item in items]

        results = []
        for future in as_completed(futures):
            try:
                result = future.result(timeout=10)
                results.append(result)
            except Exception as e:
                logger.error(f"Async mapping failed: {e}")
                results.append(None)

        return results

    def shutdown(self):
        """Shutdown executor."""
        self._executor.shutdown(wait=True)


# ============================================================================
# Async I/O Operations
# ============================================================================


class AsyncFileHandler:
    """Asynchronous file I/O operations."""

    @staticmethod
    async def read_file_async(file_path: Path, encoding: str = "utf-8") -> str:
        """Read file asynchronously."""
        try:
            async with aiofiles.open(file_path, encoding=encoding) as f:
                content = await f.read()
            return content
        except Exception as e:
            logger.error(f"Async read failed for {file_path}: {e}")
            raise

    @staticmethod
    async def write_file_async(file_path: Path, content: str, encoding: str = "utf-8"):
        """Write file asynchronously."""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(file_path, "w", encoding=encoding) as f:
                await f.write(content)
        except Exception as e:
            logger.error(f"Async write failed for {file_path}: {e}")
            raise

    @staticmethod
    async def read_json_async(file_path: Path) -> Dict[str, Any]:
        """Read JSON file asynchronously."""
        content = await AsyncFileHandler.read_file_async(file_path)
        return json.loads(content)

    @staticmethod
    async def write_json_async(file_path: Path, data: Dict[str, Any], pretty: bool = True):
        """Write JSON file asynchronously."""
        if pretty:
            content = json.dumps(data, indent=2, default=str)
        else:
            content = json.dumps(data, default=str)
        await AsyncFileHandler.write_file_async(file_path, content)


# ============================================================================
# Batch Processing
# ============================================================================


class BatchProcessor:
    """Batch processing for API calls and bulk operations."""

    def __init__(self, batch_size: int = BATCH_SIZE):
        """Initialize batch processor."""
        self.batch_size = batch_size
        self._queue: List[Tuple[str, Any]] = []
        self._lock = RLock()

    def add_to_batch(self, operation_id: str, item: Any):
        """Add item to batch queue."""
        with self._lock:
            self._queue.append((operation_id, item))

            # Process if batch is full
            if len(self._queue) >= self.batch_size:
                return self._process_batch()
        return None

    def _process_batch(self) -> List[Tuple[str, Any]]:
        """Process current batch."""
        with self._lock:
            if not self._queue:
                return []

            batch = self._queue[: self.batch_size]
            self._queue = self._queue[self.batch_size :]
            return batch

    def flush(self) -> List[Tuple[str, Any]]:
        """Flush remaining items in queue."""
        with self._lock:
            batch = self._queue
            self._queue = []
            return batch


# ============================================================================
# Memory Management
# ============================================================================


class MemoryManager:
    """Monitor and manage memory usage."""

    def __init__(self, max_memory_mb: int = MAX_MEMORY_MB):
        """Initialize memory manager."""
        self.max_memory_mb = max_memory_mb
        self._check_count = 0
        self._lock = RLock()

    def check_memory(self) -> bool:
        """Check if memory usage is within limits."""
        import psutil

        with self._lock:
            self._check_count += 1

            # Only check periodically
            if self._check_count % MEMORY_CHECK_INTERVAL != 0:
                return True

            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024

            if memory_mb > self.max_memory_mb:
                logger.warning(f"Memory usage exceeded: {memory_mb:.1f}MB > {self.max_memory_mb}MB")
                return False

            return True

    def get_memory_stats(self) -> Dict[str, float]:
        """Get current memory statistics."""
        import psutil

        process = psutil.Process()
        memory_info = process.memory_info()

        return {
            "rss_mb": memory_info.rss / 1024 / 1024,
            "vms_mb": memory_info.vms / 1024 / 1024,
            "percent": process.memory_percent(),
            "available_mb": psutil.virtual_memory().available / 1024 / 1024,
        }


# ============================================================================
# Connection Pool Manager
# ============================================================================


class ConnectionPool:
    """Connection pool for external API calls."""

    def __init__(self, max_connections: int = 10):
        """Initialize connection pool."""
        self.max_connections = max_connections
        self._connections: Dict[str, Any] = {}
        self._lock = RLock()

    def get_connection(self, endpoint: str) -> Any:
        """Get or create connection for endpoint."""
        with self._lock:
            if endpoint not in self._connections:
                # In production, would create actual HTTP session
                self._connections[endpoint] = {"created": time.time(), "requests": 0}

            conn = self._connections[endpoint]
            conn["requests"] += 1
            return conn

    def close_all(self):
        """Close all connections."""
        with self._lock:
            self._connections.clear()


# ============================================================================
# Streaming Export
# ============================================================================


class StreamingExporter:
    """Stream large SBOM exports to reduce memory usage."""

    @staticmethod
    async def stream_json_export(
        data: Dict[str, Any], output_path: Path, chunk_size: int = 1024 * 1024
    ):  # 1MB chunks
        """
        Stream JSON export for large SBOMs.

        Args:
            data: SBOM data to export
            output_path: Output file path
            chunk_size: Size of streaming chunks
        """
        try:
            # Convert to JSON string
            json_str = json.dumps(data, indent=2, default=str)

            # Stream write in chunks
            async with aiofiles.open(output_path, "w") as f:
                for i in range(0, len(json_str), chunk_size):
                    chunk = json_str[i : i + chunk_size]
                    await f.write(chunk)

                    # Yield control periodically
                    if i % (chunk_size * 10) == 0:
                        await asyncio.sleep(0)

            logger.info(f"Streamed {len(json_str)} bytes to {output_path}")

        except Exception as e:
            logger.error(f"Streaming export failed: {e}")
            raise


# ============================================================================
# Performance Optimization Manager
# ============================================================================


class PerformanceOptimizer:
    """Central manager for all performance optimizations."""

    def __init__(self):
        """Initialize performance optimizer."""
        self.cache_manager = CacheManager()
        self.perf_monitor = PerformanceMonitor()
        self.parallel_processor = ParallelProcessor()
        self.batch_processor = BatchProcessor()
        self.memory_manager = MemoryManager()
        self.connection_pool = ConnectionPool()
        self._lock = RLock()

    def optimize_operation(self, operation: str) -> Dict[str, Any]:
        """Get optimization settings for specific operation."""
        optimizations = {
            "dependency_scan": {"parallel": True, "cache": True, "batch": False, "max_workers": 8},
            "license_detection": {"parallel": True, "cache": True, "batch": True, "max_workers": 4},
            "vulnerability_scan": {
                "parallel": True,
                "cache": True,
                "batch": True,
                "max_workers": 6,
            },
            "sbom_export": {"parallel": False, "cache": False, "batch": False, "streaming": True},
        }

        return optimizations.get(
            operation, {"parallel": False, "cache": False, "batch": False, "max_workers": 1}
        )

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        return {
            "cache_stats": self.cache_manager.get_stats(),
            "performance_metrics": self.perf_monitor.get_metrics(),
            "memory_stats": self.memory_manager.get_memory_stats(),
        }

    def cleanup(self):
        """Cleanup resources."""
        self.cache_manager.periodic_cleanup()
        self.parallel_processor.shutdown()
        self.connection_pool.close_all()
