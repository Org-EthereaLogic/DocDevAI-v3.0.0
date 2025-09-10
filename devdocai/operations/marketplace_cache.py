"""
M013 Template Marketplace - Cache Management
DevDocAI v3.0.0 - Pass 4: Refactoring & Integration

This module contains all caching strategies and optimizations extracted from
the performance module for clean separation of concerns.
"""

import logging
import pickle
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .marketplace_types import CacheEntry, CacheLevel

logger = logging.getLogger(__name__)


class CacheMetrics:
    """Metrics tracking for cache operations."""

    def __init__(self):
        """Initialize cache metrics."""
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.total_size_bytes = 0
        self.operation_times: List[float] = []
        self._lock = threading.Lock()

    def record_hit(self):
        """Record a cache hit."""
        with self._lock:
            self.hits += 1

    def record_miss(self):
        """Record a cache miss."""
        with self._lock:
            self.misses += 1

    def record_eviction(self):
        """Record a cache eviction."""
        with self._lock:
            self.evictions += 1

    def record_operation(self, duration_ms: float):
        """Record operation time."""
        with self._lock:
            self.operation_times.append(duration_ms)
            # Keep only last 1000 operations
            if len(self.operation_times) > 1000:
                self.operation_times = self.operation_times[-1000:]

    def get_hit_ratio(self) -> float:
        """Get cache hit ratio."""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total

    def get_avg_operation_time(self) -> float:
        """Get average operation time in ms."""
        if not self.operation_times:
            return 0.0
        return sum(self.operation_times) / len(self.operation_times)

    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics as dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_ratio": self.get_hit_ratio(),
            "evictions": self.evictions,
            "total_size_bytes": self.total_size_bytes,
            "avg_operation_ms": self.get_avg_operation_time(),
        }


class LRUCache:
    """Least Recently Used cache implementation."""

    def __init__(self, max_size: int = 100):
        """
        Initialize LRU cache.

        Args:
            max_size: Maximum number of items in cache
        """
        self.max_size = max_size
        self.cache: Dict[str, Any] = {}
        self.access_order: List[str] = []
        self._lock = threading.RLock()
        self.metrics = CacheMetrics()

    def get(self, key: str) -> Optional[Any]:
        """
        Get item from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        start_time = time.time()

        with self._lock:
            if key in self.cache:
                # Move to end (most recently used)
                self.access_order.remove(key)
                self.access_order.append(key)
                self.metrics.record_hit()
                value = self.cache[key]
            else:
                self.metrics.record_miss()
                value = None

        duration_ms = (time.time() - start_time) * 1000
        self.metrics.record_operation(duration_ms)

        return value

    def set(self, key: str, value: Any) -> bool:
        """
        Store item in cache.

        Args:
            key: Cache key
            value: Value to cache

        Returns:
            True if stored successfully
        """
        start_time = time.time()

        with self._lock:
            # Remove if already exists
            if key in self.cache:
                self.access_order.remove(key)

            # Evict LRU item if at capacity
            elif len(self.cache) >= self.max_size:
                lru_key = self.access_order.pop(0)
                del self.cache[lru_key]
                self.metrics.record_eviction()

            # Add new item
            self.cache[key] = value
            self.access_order.append(key)

        duration_ms = (time.time() - start_time) * 1000
        self.metrics.record_operation(duration_ms)

        return True

    def remove(self, key: str) -> bool:
        """
        Remove item from cache.

        Args:
            key: Cache key

        Returns:
            True if removed
        """
        with self._lock:
            if key in self.cache:
                del self.cache[key]
                self.access_order.remove(key)
                return True
            return False

    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self.cache.clear()
            self.access_order.clear()

    def size(self) -> int:
        """Get number of items in cache."""
        return len(self.cache)


class TTLCache:
    """Time-To-Live cache implementation."""

    def __init__(self, default_ttl: int = 3600):
        """
        Initialize TTL cache.

        Args:
            default_ttl: Default TTL in seconds
        """
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self.metrics = CacheMetrics()

    def get(self, key: str) -> Optional[Any]:
        """
        Get item from cache if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        start_time = time.time()

        with self._lock:
            if key in self.cache:
                entry = self.cache[key]
                if datetime.now() < entry.expires_at:
                    entry.hit_count += 1
                    self.metrics.record_hit()
                    value = entry.value
                else:
                    # Expired - remove it
                    del self.cache[key]
                    self.metrics.record_miss()
                    value = None
            else:
                self.metrics.record_miss()
                value = None

        duration_ms = (time.time() - start_time) * 1000
        self.metrics.record_operation(duration_ms)

        return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Store item in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds (uses default if None)

        Returns:
            True if stored successfully
        """
        start_time = time.time()
        ttl = ttl or self.default_ttl

        with self._lock:
            entry = CacheEntry(
                key=key,
                value=value,
                cached_at=datetime.now(),
                expires_at=datetime.now() + timedelta(seconds=ttl),
                cache_level=CacheLevel.MEMORY,
            )
            self.cache[key] = entry

        duration_ms = (time.time() - start_time) * 1000
        self.metrics.record_operation(duration_ms)

        return True

    def remove(self, key: str) -> bool:
        """
        Remove item from cache.

        Args:
            key: Cache key

        Returns:
            True if removed
        """
        with self._lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False

    def cleanup(self) -> int:
        """
        Remove expired entries.

        Returns:
            Number of entries removed
        """
        removed = 0
        now = datetime.now()

        with self._lock:
            expired_keys = [key for key, entry in self.cache.items() if now >= entry.expires_at]

            for key in expired_keys:
                del self.cache[key]
                self.metrics.record_eviction()
                removed += 1

        return removed

    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self.cache.clear()


class MultiTierCache:
    """Multi-tier caching with memory and disk layers."""

    def __init__(
        self,
        cache_dir: Path,
        memory_size: int = 100,
        disk_size_mb: float = 500,
        ttl_seconds: int = 3600,
    ):
        """
        Initialize multi-tier cache.

        Args:
            cache_dir: Directory for disk cache
            memory_size: Max items in memory cache
            disk_size_mb: Max disk cache size in MB
            ttl_seconds: Default TTL
        """
        self.memory_cache = LRUCache(max_size=memory_size)
        self.ttl_cache = TTLCache(default_ttl=ttl_seconds)

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.disk_size_bytes = disk_size_mb * 1024 * 1024

        self._lock = threading.RLock()
        self.metrics = CacheMetrics()

    def get(self, key: str) -> Optional[Any]:
        """
        Get from cache (checks memory then disk).

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        # Check memory cache first
        value = self.memory_cache.get(key)
        if value is not None:
            return value

        # Check TTL cache
        value = self.ttl_cache.get(key)
        if value is not None:
            # Promote to memory cache
            self.memory_cache.set(key, value)
            return value

        # Check disk cache
        value = self._get_from_disk(key)
        if value is not None:
            # Promote to memory cache
            self.memory_cache.set(key, value)
            self.metrics.record_hit()
            return value

        self.metrics.record_miss()
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Store in cache (memory and disk).

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL in seconds

        Returns:
            True if stored successfully
        """
        # Store in memory cache
        self.memory_cache.set(key, value)

        # Store in TTL cache
        self.ttl_cache.set(key, value, ttl)

        # Store on disk
        return self._save_to_disk(key, value)

    def remove(self, key: str) -> bool:
        """
        Remove from all cache tiers.

        Args:
            key: Cache key

        Returns:
            True if removed from any tier
        """
        removed = False

        # Remove from memory
        if self.memory_cache.remove(key):
            removed = True

        # Remove from TTL cache
        if self.ttl_cache.remove(key):
            removed = True

        # Remove from disk
        if self._remove_from_disk(key):
            removed = True

        return removed

    def _get_from_disk(self, key: str) -> Optional[Any]:
        """Get item from disk cache."""
        cache_file = self.cache_dir / f"{key}.cache"

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"Failed to load from disk cache: {e}")
            return None

    def _save_to_disk(self, key: str, value: Any) -> bool:
        """Save item to disk cache."""
        cache_file = self.cache_dir / f"{key}.cache"

        try:
            with open(cache_file, "wb") as f:
                pickle.dump(value, f)
            return True
        except Exception as e:
            logger.error(f"Failed to save to disk cache: {e}")
            return False

    def _remove_from_disk(self, key: str) -> bool:
        """Remove item from disk cache."""
        cache_file = self.cache_dir / f"{key}.cache"

        if cache_file.exists():
            try:
                cache_file.unlink()
                return True
            except Exception as e:
                logger.error(f"Failed to remove from disk cache: {e}")

        return False

    def cleanup(self) -> int:
        """
        Clean up expired entries and old disk files.

        Returns:
            Number of entries cleaned
        """
        # Clean TTL cache
        removed = self.ttl_cache.cleanup()

        # Clean old disk files
        now = datetime.now()
        for cache_file in self.cache_dir.glob("*.cache"):
            try:
                # Check file age
                mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                if (now - mtime).total_seconds() > 86400:  # 24 hours
                    cache_file.unlink()
                    removed += 1
            except Exception:
                pass

        return removed

    def clear(self):
        """Clear all cache tiers."""
        self.memory_cache.clear()
        self.ttl_cache.clear()

        # Clear disk cache
        for cache_file in self.cache_dir.glob("*.cache"):
            try:
                cache_file.unlink()
            except Exception:
                pass

    def get_metrics(self) -> Dict[str, Any]:
        """Get combined metrics from all tiers."""
        return {
            "memory": self.memory_cache.metrics.get_metrics(),
            "ttl": self.ttl_cache.metrics.get_metrics(),
            "combined": self.metrics.get_metrics(),
        }


class CacheWarmup:
    """Cache warmup utilities."""

    @staticmethod
    def warmup_cache(
        cache: Any,
        keys: List[str],
        loader: Callable[[str], Any],
        parallel: bool = True,
        max_workers: int = 4,
    ) -> int:
        """
        Warm up cache with specified keys.

        Args:
            cache: Cache instance
            keys: Keys to preload
            loader: Function to load values
            parallel: Use parallel loading
            max_workers: Max parallel workers

        Returns:
            Number of items loaded
        """
        loaded = 0

        if parallel:
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(loader, key): key for key in keys}

                for future in concurrent.futures.as_completed(futures):
                    key = futures[future]
                    try:
                        value = future.result()
                        if value is not None:
                            cache.set(key, value)
                            loaded += 1
                    except Exception as e:
                        logger.error(f"Failed to load {key}: {e}")
        else:
            for key in keys:
                try:
                    value = loader(key)
                    if value is not None:
                        cache.set(key, value)
                        loaded += 1
                except Exception as e:
                    logger.error(f"Failed to load {key}: {e}")

        logger.info(f"Cache warmup complete: {loaded}/{len(keys)} items loaded")
        return loaded


def create_cache(cache_type: str = "multi", cache_dir: Optional[Path] = None, **kwargs) -> Any:
    """
    Factory function to create cache instance.

    Args:
        cache_type: Type of cache (lru, ttl, multi)
        cache_dir: Directory for disk cache
        **kwargs: Additional cache parameters

    Returns:
        Cache instance
    """
    if cache_type == "lru":
        max_size = kwargs.get("max_size", 100)
        return LRUCache(max_size=max_size)

    elif cache_type == "ttl":
        default_ttl = kwargs.get("default_ttl", 3600)
        return TTLCache(default_ttl=default_ttl)

    elif cache_type == "multi":
        cache_dir = cache_dir or Path.home() / ".devdocai" / "cache"
        memory_size = kwargs.get("memory_size", 100)
        disk_size_mb = kwargs.get("disk_size_mb", 500)
        ttl_seconds = kwargs.get("ttl_seconds", 3600)

        return MultiTierCache(
            cache_dir=cache_dir,
            memory_size=memory_size,
            disk_size_mb=disk_size_mb,
            ttl_seconds=ttl_seconds,
        )

    else:
        raise ValueError(f"Unknown cache type: {cache_type}")
