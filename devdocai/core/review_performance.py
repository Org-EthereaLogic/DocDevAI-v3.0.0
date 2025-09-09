"""
M007 Review Engine - Performance Optimization Components
DevDocAI v3.0.0

Extracted performance components for cleaner separation of concerns.
Implements multi-tier caching, parallel processing, and batch optimization.
"""

import time
import pickle
import zlib
import hashlib
import logging
import asyncio
import threading
from typing import Dict, Any, List, Optional, Tuple
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache, wraps
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Performance constants
MAX_CACHE_SIZE_MB = 100
DEFAULT_CACHE_TTL = 3600  # 1 hour
DEFAULT_BATCH_SIZE = 10
DEFAULT_MAX_WORKERS = 8
CHUNK_SIZE = 10000  # For document chunking


@dataclass
class PerformanceMetrics:
    """Performance metrics tracking."""
    total_analyzed: int = 0
    total_time: float = 0.0
    avg_time_per_doc: float = 0.0
    cache_hit_rate: float = 0.0
    cache_stats: Dict[str, int] = field(default_factory=lambda: {
        "hits": 0,
        "misses": 0,
        "evictions": 0
    })


class CacheManager:
    """Manages multi-tier caching with compression."""
    
    def __init__(self, max_size: int = 100, ttl: int = DEFAULT_CACHE_TTL):
        """Initialize cache manager."""
        self._cache = {}  # L1: In-memory cache
        self._compressed_cache = {}  # L2: Compressed cache
        self._cache_ttl = ttl
        self._max_size = max_size
        self._cache_queue = deque(maxlen=max_size)  # LRU tracking
        self._cache_lock = threading.RLock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }
    
    def get_cache_key(self, document: Any) -> str:
        """Generate cache key for document with optimized hashing."""
        try:
            import xxhash
            content_hash = xxhash.xxh64(document.content.encode()).hexdigest()
        except ImportError:
            content_hash = hashlib.md5(document.content.encode()).hexdigest()
        return f"{document.id}_{document.type}_{content_hash}"
    
    async def get(self, cache_key: str) -> Optional[Any]:
        """Get result from multi-tier cache."""
        with self._cache_lock:
            # Check L1 cache (in-memory)
            if cache_key in self._cache:
                cached_data = self._cache[cache_key]
                if time.time() - cached_data["timestamp"] < self._cache_ttl:
                    self._stats["hits"] += 1
                    # Move to end of queue (most recently used)
                    try:
                        self._cache_queue.remove(cache_key)
                    except ValueError:
                        pass
                    self._cache_queue.append(cache_key)
                    result = cached_data["data"]
                    if hasattr(result, 'from_cache'):
                        result.from_cache = True
                    return result
            
            # Check L2 cache (compressed)
            if cache_key in self._compressed_cache:
                compressed_data = self._compressed_cache[cache_key]
                if time.time() - compressed_data["timestamp"] < self._cache_ttl:
                    self._stats["hits"] += 1
                    # Decompress and promote to L1
                    result = self._decompress(compressed_data["data"])
                    self._cache[cache_key] = {
                        "data": result,
                        "timestamp": compressed_data["timestamp"]
                    }
                    if hasattr(result, 'from_cache'):
                        result.from_cache = True
                    return result
            
            self._stats["misses"] += 1
            return None
    
    def store(self, cache_key: str, data: Any) -> None:
        """Store result in multi-tier cache."""
        with self._cache_lock:
            # Determine cache tier based on size
            data_size = len(str(data))
            timestamp = time.time()
            
            if data_size < 10000:  # < 10KB goes to L1
                self._cache[cache_key] = {
                    "data": data,
                    "timestamp": timestamp
                }
            else:  # Larger results go to L2 (compressed)
                compressed = self._compress(data)
                self._compressed_cache[cache_key] = {
                    "data": compressed,
                    "timestamp": timestamp
                }
            
            # Track in LRU queue
            if cache_key not in self._cache_queue:
                self._cache_queue.append(cache_key)
            
            # Manage cache size
            self._evict_if_needed()
    
    def _compress(self, data: Any) -> bytes:
        """Compress data for memory-efficient caching."""
        serialized = pickle.dumps(data)
        compressed = zlib.compress(serialized, level=6)
        return compressed
    
    def _decompress(self, compressed: bytes) -> Any:
        """Decompress cached data."""
        decompressed = zlib.decompress(compressed)
        return pickle.loads(decompressed)
    
    def _evict_if_needed(self) -> None:
        """Manage cache size using LRU eviction."""
        while len(self._cache) + len(self._compressed_cache) > self._max_size:
            if self._cache_queue:
                oldest_key = self._cache_queue.popleft()
                if oldest_key in self._cache:
                    del self._cache[oldest_key]
                if oldest_key in self._compressed_cache:
                    del self._compressed_cache[oldest_key]
                self._stats["evictions"] += 1
    
    def clear(self) -> None:
        """Clear all caches and reset statistics."""
        with self._cache_lock:
            self._cache.clear()
            self._compressed_cache.clear()
            self._cache_queue.clear()
            self._stats = {
                "hits": 0,
                "misses": 0,
                "evictions": 0
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._cache_lock:
            total = self._stats["hits"] + self._stats["misses"]
            hit_rate = self._stats["hits"] / total if total > 0 else 0
            return {
                **self._stats,
                "hit_rate": hit_rate,
                "size": len(self._cache) + len(self._compressed_cache),
                "max_size": self._max_size
            }


class ParallelProcessor:
    """Manages parallel processing with controlled concurrency."""
    
    def __init__(self, max_workers: int = DEFAULT_MAX_WORKERS):
        """Initialize parallel processor."""
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="review_worker"
        )
        self._semaphore_map = {}
    
    async def process_parallel(
        self,
        tasks: List[Tuple[str, asyncio.Task]],
        max_concurrent: int = 6
    ) -> List[Tuple[str, Any]]:
        """Execute tasks with controlled concurrency."""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def run_with_semaphore(name: str, task: asyncio.Task):
            async with semaphore:
                try:
                    return name, await task
                except Exception as e:
                    logger.error(f"Task {name} failed: {e}")
                    return name, None
        
        results = await asyncio.gather(
            *[run_with_semaphore(name, task) for name, task in tasks],
            return_exceptions=False
        )
        
        return results
    
    async def process_batch(
        self,
        items: List[Any],
        processor_func,
        batch_size: int = DEFAULT_BATCH_SIZE
    ) -> List[Any]:
        """Process items in batches for better performance."""
        results = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[processor_func(item) for item in batch],
                return_exceptions=False
            )
            results.extend(batch_results)
        
        return results
    
    def chunk_document(self, content: str, chunk_size: int = CHUNK_SIZE) -> List[str]:
        """Split document into chunks for parallel processing."""
        if len(content) <= chunk_size:
            return [content]
        
        chunks = []
        current_chunk = ""
        sentences = content.split('. ')
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence
            else:
                current_chunk += sentence + '. '
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    async def run_in_executor(self, func, *args):
        """Run CPU-bound function in executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, func, *args)
    
    def shutdown(self) -> None:
        """Shutdown executor."""
        self._executor.shutdown(wait=True)


class PerformanceMonitor:
    """Monitors and tracks performance metrics."""
    
    def __init__(self):
        """Initialize performance monitor."""
        self._metrics = PerformanceMetrics()
        self._lock = threading.Lock()
    
    def update_metrics(
        self,
        elapsed_time: float,
        from_cache: bool = False,
        cache_stats: Optional[Dict[str, int]] = None
    ) -> None:
        """Update performance metrics."""
        with self._lock:
            self._metrics.total_analyzed += 1
            
            if not from_cache:
                self._metrics.total_time += elapsed_time
                
                # Calculate average time per document (excluding cached)
                non_cached = self._metrics.total_analyzed - self._metrics.cache_stats.get("hits", 0)
                if non_cached > 0:
                    self._metrics.avg_time_per_doc = self._metrics.total_time / non_cached
            
            # Update cache stats if provided
            if cache_stats:
                self._metrics.cache_stats = cache_stats
                total = cache_stats.get("hits", 0) + cache_stats.get("misses", 0)
                if total > 0:
                    self._metrics.cache_hit_rate = cache_stats["hits"] / total
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        with self._lock:
            return {
                "total_analyzed": self._metrics.total_analyzed,
                "total_time": self._metrics.total_time,
                "avg_time_per_doc": self._metrics.avg_time_per_doc,
                "cache_hit_rate": self._metrics.cache_hit_rate,
                "cache_stats": self._metrics.cache_stats.copy()
            }
    
    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._metrics = PerformanceMetrics()


def performance_timer(func):
    """Decorator to measure function execution time."""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        elapsed = time.time() - start
        logger.debug(f"{func.__name__} took {elapsed:.3f}s")
        return result
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        logger.debug(f"{func.__name__} took {elapsed:.3f}s")
        return result
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper