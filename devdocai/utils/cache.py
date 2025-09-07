"""
Caching Utilities - DevDocAI v3.0.0
Pass 4: Simplified thread-safe cache
"""

import time
import threading
from typing import Any, Optional, Tuple, Dict


class CacheManager:
    """Thread-safe cache with TTL support."""
    
    def __init__(self, max_size: int = 128, default_ttl: int = 3600):
        """Initialize cache manager."""
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.RLock()
        self.max_size = max_size
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if expiry > time.time():
                    return value
                del self._cache[key]  # Remove expired
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache with TTL."""
        if ttl is None:
            ttl = self.default_ttl
        
        with self._lock:
            # Simple LRU: remove oldest if at capacity
            if len(self._cache) >= self.max_size and key not in self._cache:
                oldest = min(self._cache.keys(), key=lambda k: self._cache[k][1])
                del self._cache[oldest]
            
            self._cache[key] = (value, time.time() + ttl)
    
    def invalidate(self, key: str) -> bool:
        """Remove key from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()