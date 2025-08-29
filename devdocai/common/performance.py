"""
Unified performance optimization module for DevDocAI.

Consolidates caching, pooling, and optimization utilities from all modules.
Provides consistent performance enhancements across the system.
"""

import time
import hashlib
import pickle
import threading
import weakref
from typing import Any, Dict, Optional, Callable, TypeVar, Generic, Tuple, List
from functools import wraps, lru_cache
from collections import OrderedDict
from datetime import datetime, timedelta
from contextlib import contextmanager
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import psutil
import gc

logger = logging.getLogger(__name__)

T = TypeVar('T')


# ============================================================================
# CACHING UTILITIES
# ============================================================================

class LRUCache(Generic[T]):
    """
    Thread-safe LRU cache with TTL support.
    
    Enhanced version consolidating caching from all modules.
    """
    
    def __init__(self, max_size: int = 128, ttl_seconds: Optional[int] = None):
        """
        Initialize LRU cache.
        
        Args:
            max_size: Maximum cache size
            ttl_seconds: Time-to-live in seconds (None for no expiry)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict[str, Tuple[T, Optional[datetime]]] = OrderedDict()
        self.lock = threading.RLock()
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[T]:
        """Get item from cache."""
        with self.lock:
            if key not in self.cache:
                self.misses += 1
                return None
            
            value, expiry = self.cache[key]
            
            # Check expiry
            if expiry and datetime.now() > expiry:
                del self.cache[key]
                self.misses += 1
                return None
            
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            self.hits += 1
            return value
    
    def put(self, key: str, value: T):
        """Put item in cache."""
        with self.lock:
            # Calculate expiry
            expiry = None
            if self.ttl_seconds:
                expiry = datetime.now() + timedelta(seconds=self.ttl_seconds)
            
            # Add to cache
            self.cache[key] = (value, expiry)
            self.cache.move_to_end(key)
            
            # Evict if necessary
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)
    
    def clear(self):
        """Clear cache."""
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            total = self.hits + self.misses
            hit_rate = self.hits / total if total > 0 else 0
            
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': hit_rate,
                'ttl_seconds': self.ttl_seconds
            }


class ContentCache:
    """
    Content-based cache using hash keys.
    
    Useful for caching based on content rather than explicit keys.
    """
    
    def __init__(self, max_size: int = 256):
        """Initialize content cache."""
        self.cache = LRUCache[Any](max_size=max_size)
    
    def _compute_key(self, content: Any) -> str:
        """Compute cache key from content."""
        try:
            # Try to pickle for consistent hashing
            content_bytes = pickle.dumps(content, protocol=pickle.HIGHEST_PROTOCOL)
        except (pickle.PickleError, TypeError):
            # Fall back to string representation
            content_bytes = str(content).encode('utf-8')
        
        return hashlib.sha256(content_bytes).hexdigest()
    
    def get(self, content: Any) -> Optional[Any]:
        """Get result for content."""
        key = self._compute_key(content)
        return self.cache.get(key)
    
    def put(self, content: Any, result: Any):
        """Store result for content."""
        key = self._compute_key(content)
        self.cache.put(key, result)
    
    def clear(self):
        """Clear cache."""
        self.cache.clear()


def cached(max_size: int = 128, ttl_seconds: Optional[int] = None):
    """
    Decorator for caching function results.
    
    Args:
        max_size: Maximum cache size
        ttl_seconds: Time-to-live in seconds
    """
    def decorator(func):
        cache = LRUCache[Any](max_size=max_size, ttl_seconds=ttl_seconds)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            key = f"{args}:{kwargs}"
            
            # Check cache
            result = cache.get(key)
            if result is not None:
                return result
            
            # Compute result
            result = func(*args, **kwargs)
            
            # Store in cache
            cache.put(key, result)
            
            return result
        
        # Add cache management methods
        wrapper.cache = cache
        wrapper.clear_cache = cache.clear
        wrapper.cache_stats = cache.get_stats
        
        return wrapper
    
    return decorator


# ============================================================================
# CONNECTION POOLING
# ============================================================================

class ConnectionPool:
    """
    Generic connection pool for database connections.
    
    Provides connection reuse and management.
    """
    
    def __init__(self, 
                 create_connection: Callable[[], Any],
                 max_connections: int = 10,
                 timeout: float = 30.0):
        """
        Initialize connection pool.
        
        Args:
            create_connection: Function to create new connection
            max_connections: Maximum pool size
            timeout: Connection timeout in seconds
        """
        self.create_connection = create_connection
        self.max_connections = max_connections
        self.timeout = timeout
        
        self.pool: List[Any] = []
        self.in_use: weakref.WeakSet = weakref.WeakSet()
        self.lock = threading.Lock()
        self.semaphore = threading.Semaphore(max_connections)
    
    def get_connection(self):
        """Get connection from pool."""
        if not self.semaphore.acquire(timeout=self.timeout):
            raise TimeoutError("Connection pool timeout")
        
        with self.lock:
            # Try to get existing connection
            while self.pool:
                conn = self.pool.pop()
                if self._is_valid(conn):
                    self.in_use.add(conn)
                    return conn
                else:
                    self._close_connection(conn)
            
            # Create new connection
            conn = self.create_connection()
            self.in_use.add(conn)
            return conn
    
    def return_connection(self, conn: Any):
        """Return connection to pool."""
        with self.lock:
            if conn in self.in_use:
                self.in_use.discard(conn)
                
                if len(self.pool) < self.max_connections:
                    self.pool.append(conn)
                else:
                    self._close_connection(conn)
            
            self.semaphore.release()
    
    @contextmanager
    def connection(self):
        """Context manager for connection usage."""
        conn = self.get_connection()
        try:
            yield conn
        finally:
            self.return_connection(conn)
    
    def _is_valid(self, conn: Any) -> bool:
        """Check if connection is valid."""
        try:
            # Try to execute simple query
            if hasattr(conn, 'execute'):
                conn.execute("SELECT 1")
            return True
        except:
            return False
    
    def _close_connection(self, conn: Any):
        """Close connection."""
        try:
            if hasattr(conn, 'close'):
                conn.close()
        except:
            pass
    
    def close_all(self):
        """Close all connections."""
        with self.lock:
            for conn in self.pool:
                self._close_connection(conn)
            self.pool.clear()


# ============================================================================
# BATCH PROCESSING
# ============================================================================

class BatchProcessor:
    """
    Batch processing utilities for improved throughput.
    
    Consolidates batch processing from various modules.
    """
    
    def __init__(self, 
                 batch_size: int = 100,
                 flush_interval: float = 1.0,
                 max_workers: int = 4):
        """
        Initialize batch processor.
        
        Args:
            batch_size: Maximum batch size
            flush_interval: Auto-flush interval in seconds
            max_workers: Number of worker threads
        """
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.max_workers = max_workers
        
        self.batch: List[Any] = []
        self.lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.last_flush = time.time()
        
        # Start auto-flush thread
        self.flush_thread = threading.Thread(target=self._auto_flush, daemon=True)
        self.flush_thread.start()
    
    def add(self, item: Any, processor: Callable[[List[Any]], None]):
        """
        Add item to batch.
        
        Args:
            item: Item to process
            processor: Function to process batch
        """
        with self.lock:
            self.batch.append((item, processor))
            
            if len(self.batch) >= self.batch_size:
                self._flush()
    
    def _flush(self):
        """Flush current batch."""
        if not self.batch:
            return
        
        # Group by processor
        groups: Dict[Callable, List[Any]] = {}
        for item, processor in self.batch:
            if processor not in groups:
                groups[processor] = []
            groups[processor].append(item)
        
        # Process each group
        for processor, items in groups.items():
            self.executor.submit(processor, items)
        
        self.batch.clear()
        self.last_flush = time.time()
    
    def _auto_flush(self):
        """Auto-flush thread."""
        while True:
            time.sleep(self.flush_interval)
            
            with self.lock:
                if self.batch and time.time() - self.last_flush >= self.flush_interval:
                    self._flush()
    
    def flush_now(self):
        """Force flush immediately."""
        with self.lock:
            self._flush()
    
    def shutdown(self):
        """Shutdown batch processor."""
        self.flush_now()
        self.executor.shutdown(wait=True)


# ============================================================================
# RESOURCE MONITORING
# ============================================================================

class ResourceMonitor:
    """
    Monitor and optimize resource usage.
    
    Provides memory and CPU monitoring with optimization triggers.
    """
    
    def __init__(self, 
                 memory_threshold_mb: int = 500,
                 cpu_threshold_percent: float = 80.0):
        """
        Initialize resource monitor.
        
        Args:
            memory_threshold_mb: Memory usage threshold
            cpu_threshold_percent: CPU usage threshold
        """
        self.memory_threshold_mb = memory_threshold_mb
        self.cpu_threshold_percent = cpu_threshold_percent
        self.process = psutil.Process()
        self.start_time = time.time()
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage."""
        memory_info = self.process.memory_info()
        return {
            'rss_mb': memory_info.rss / (1024 * 1024),
            'vms_mb': memory_info.vms / (1024 * 1024),
            'percent': self.process.memory_percent()
        }
    
    def get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        # Use interval=None for non-blocking call to avoid 100ms sleep delay
        # This provides instant CPU usage based on previous measurement
        return self.process.cpu_percent(interval=None)
    
    def check_resources(self) -> Tuple[bool, List[str]]:
        """
        Check if resources are within limits.
        
        Returns:
            Tuple of (within_limits, warnings)
        """
        warnings = []
        
        # Check memory
        memory = self.get_memory_usage()
        if memory['rss_mb'] > self.memory_threshold_mb:
            warnings.append(f"Memory usage {memory['rss_mb']:.1f}MB exceeds threshold {self.memory_threshold_mb}MB")
        
        # Check CPU
        cpu = self.get_cpu_usage()
        if cpu > self.cpu_threshold_percent:
            warnings.append(f"CPU usage {cpu:.1f}% exceeds threshold {self.cpu_threshold_percent}%")
        
        return len(warnings) == 0, warnings
    
    def optimize_memory(self):
        """Trigger memory optimization."""
        # Force garbage collection
        gc.collect()
        
        # Clear caches if available
        try:
            from functools import lru_cache
            # Clear all LRU caches
            gc.collect()
        except:
            pass
    
    @contextmanager
    def monitor(self, operation_name: str):
        """
        Context manager for monitoring operations.
        
        Usage:
            with monitor.monitor('heavy_operation'):
                # Perform operation
                pass
        """
        start_memory = self.get_memory_usage()
        start_cpu = self.get_cpu_usage()
        start_time = time.time()
        
        try:
            yield
        finally:
            # Log resource usage
            duration = time.time() - start_time
            end_memory = self.get_memory_usage()
            end_cpu = self.get_cpu_usage()
            
            memory_delta = end_memory['rss_mb'] - start_memory['rss_mb']
            
            logger.info(f"Operation '{operation_name}' completed in {duration:.2f}s, "
                       f"memory delta: {memory_delta:.1f}MB, "
                       f"avg CPU: {(start_cpu + end_cpu) / 2:.1f}%")


# ============================================================================
# PERFORMANCE PROFILING
# ============================================================================

def profile_performance(func):
    """
    Decorator for profiling function performance.
    
    Logs execution time and resource usage.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        monitor = ResourceMonitor()
        
        with monitor.monitor(func.__name__):
            start = time.perf_counter()
            
            try:
                result = func(*args, **kwargs)
                
                # Log success
                duration = time.perf_counter() - start
                logger.debug(f"{func.__name__} completed in {duration:.4f}s")
                
                return result
                
            except Exception as e:
                # Log failure
                duration = time.perf_counter() - start
                logger.error(f"{func.__name__} failed after {duration:.4f}s: {e}")
                raise
    
    return wrapper


# ============================================================================
# PARALLEL EXECUTION
# ============================================================================

class ParallelExecutor:
    """
    Utilities for parallel execution of tasks.
    
    Provides both thread and process-based parallelism.
    """
    
    def __init__(self, max_workers: Optional[int] = None, use_processes: bool = False):
        """
        Initialize parallel executor.
        
        Args:
            max_workers: Maximum number of workers (None for CPU count)
            use_processes: Use processes instead of threads
        """
        if max_workers is None:
            max_workers = psutil.cpu_count()
        
        self.max_workers = max_workers
        self.use_processes = use_processes
        
        if use_processes:
            self.executor = ProcessPoolExecutor(max_workers=max_workers)
        else:
            self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    def map(self, func: Callable, items: List[Any]) -> List[Any]:
        """
        Map function over items in parallel.
        
        Args:
            func: Function to apply
            items: Items to process
            
        Returns:
            List of results
        """
        futures = [self.executor.submit(func, item) for item in items]
        return [future.result() for future in futures]
    
    def execute(self, tasks: List[Callable]) -> List[Any]:
        """
        Execute multiple tasks in parallel.
        
        Args:
            tasks: List of callables
            
        Returns:
            List of results
        """
        futures = [self.executor.submit(task) for task in tasks]
        return [future.result() for future in futures]
    
    async def map_async(self, func: Callable, items: List[Any]) -> List[Any]:
        """
        Async version of map.
        
        Args:
            func: Async function to apply
            items: Items to process
            
        Returns:
            List of results
        """
        tasks = [func(item) for item in items]
        return await asyncio.gather(*tasks)
    
    def shutdown(self):
        """Shutdown executor."""
        self.executor.shutdown(wait=True)


# ============================================================================
# LAZY LOADING
# ============================================================================

class LazyLoader:
    """
    Lazy loading utilities for deferred initialization.
    
    Useful for expensive resources that may not be needed.
    """
    
    def __init__(self, loader: Callable[[], Any]):
        """
        Initialize lazy loader.
        
        Args:
            loader: Function to load resource
        """
        self.loader = loader
        self._value = None
        self._loaded = False
        self.lock = threading.Lock()
    
    @property
    def value(self) -> Any:
        """Get lazily loaded value."""
        if not self._loaded:
            with self.lock:
                if not self._loaded:
                    self._value = self.loader()
                    self._loaded = True
        return self._value
    
    def is_loaded(self) -> bool:
        """Check if value is loaded."""
        return self._loaded
    
    def reset(self):
        """Reset loader."""
        with self.lock:
            self._value = None
            self._loaded = False


def lazy_property(func):
    """
    Decorator for lazy property initialization.
    
    Property is computed once on first access.
    """
    attr_name = f'_lazy_{func.__name__}'
    
    @property
    @wraps(func)
    def wrapper(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, func(self))
        return getattr(self, attr_name)
    
    return wrapper


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'LRUCache',
    'ContentCache',
    'cached',
    'ConnectionPool',
    'BatchProcessor',
    'ResourceMonitor',
    'profile_performance',
    'ParallelExecutor',
    'LazyLoader',
    'lazy_property'
]