"""
Secure caching mechanism for MIAIR Engine with HMAC-based keys.

Prevents cache poisoning, timing attacks, and memory exhaustion.
"""

import hmac
import hashlib
import time
import json
import pickle
import logging
import secrets
import threading
from typing import Any, Dict, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import OrderedDict
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass
class SecureCacheConfig:
    """Configuration for secure cache."""
    # Size limits
    max_cache_size: int = 512
    max_entry_size_bytes: int = 1024 * 1024  # 1MB per entry
    max_total_memory_mb: int = 100
    
    # Time limits
    default_ttl_seconds: int = 3600  # 1 hour
    max_ttl_seconds: int = 86400  # 24 hours
    cleanup_interval_seconds: int = 300  # 5 minutes
    
    # Security settings
    use_hmac: bool = True
    validate_entries: bool = True
    constant_time_comparison: bool = True
    partition_cache: bool = True
    add_key_entropy: bool = True
    
    # Versioning
    cache_version: str = "1.0.0"
    invalidate_on_version_change: bool = True
    
    # Behavior
    log_cache_hits: bool = False
    log_security_events: bool = True
    serialize_method: str = "json"  # json or pickle


@dataclass
class CacheEntry:
    """Secure cache entry with validation."""
    key: str
    value: Any
    created_at: float
    expires_at: float
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    checksum: Optional[str] = None
    partition: Optional[str] = None
    size_bytes: int = 0
    
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return time.time() > self.expires_at
    
    def validate_checksum(self, value_bytes: bytes) -> bool:
        """Validate entry checksum."""
        if not self.checksum:
            return True
        expected = hashlib.sha256(value_bytes).hexdigest()
        return hmac.compare_digest(self.checksum, expected)
    
    def update_access(self):
        """Update access statistics."""
        self.access_count += 1
        self.last_accessed = time.time()


class SecureCache:
    """
    Secure caching implementation for MIAIR Engine.
    
    Security features:
    - HMAC-based key generation
    - Entry validation with checksums
    - Constant-time comparison
    - Cache partitioning
    - Automatic expiration
    - Size limits enforcement
    - Protection against timing attacks
    """
    
    def __init__(self, config: Optional[SecureCacheConfig] = None):
        """Initialize secure cache."""
        self.config = config or SecureCacheConfig()
        
        # Generate secret key for HMAC
        self.secret_key = secrets.token_bytes(32)
        
        # Cache storage (ordered for LRU)
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.partitions: Dict[str, OrderedDict[str, CacheEntry]] = {}
        
        # Locking for thread safety
        self.lock = threading.RLock()
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.security_violations = 0
        self.total_memory_bytes = 0
        
        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        
        logger.info("Secure cache initialized with max size: %d", self.config.max_cache_size)
    
    def get(self, 
            key: str,
            partition: Optional[str] = None,
            validate: bool = True) -> Optional[Any]:
        """
        Get value from cache with security validation.
        
        Args:
            key: Cache key
            partition: Optional cache partition
            validate: Whether to validate entry
            
        Returns:
            Cached value or None if not found/invalid
        """
        with self.lock:
            # Generate secure key
            secure_key = self._generate_secure_key(key, partition)
            
            # Get from appropriate storage
            storage = self._get_storage(partition)
            
            if secure_key not in storage:
                self.misses += 1
                return None
            
            entry = storage[secure_key]
            
            # Check expiration
            if entry.is_expired():
                self._evict_entry(secure_key, partition, reason="expired")
                self.misses += 1
                return None
            
            # Validate if requested
            if validate and self.config.validate_entries:
                value_bytes = self._serialize_value(entry.value)
                if not entry.validate_checksum(value_bytes):
                    self._handle_security_violation("checksum_mismatch", secure_key)
                    self._evict_entry(secure_key, partition, reason="invalid_checksum")
                    return None
            
            # Update access stats and move to end (LRU)
            entry.update_access()
            storage.move_to_end(secure_key)
            
            self.hits += 1
            
            if self.config.log_cache_hits:
                logger.debug("Cache hit for key: %s", key[:20])
            
            return entry.value
    
    def put(self,
            key: str,
            value: Any,
            ttl: Optional[int] = None,
            partition: Optional[str] = None) -> bool:
        """
        Store value in cache with security measures.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            partition: Optional cache partition
            
        Returns:
            True if stored successfully
        """
        # Validate TTL
        if ttl is None:
            ttl = self.config.default_ttl_seconds
        elif ttl > self.config.max_ttl_seconds:
            ttl = self.config.max_ttl_seconds
        
        # Serialize and check size
        try:
            value_bytes = self._serialize_value(value)
            size_bytes = len(value_bytes)
            
            if size_bytes > self.config.max_entry_size_bytes:
                logger.warning("Cache entry too large: %d bytes", size_bytes)
                return False
            
        except Exception as e:
            logger.error("Failed to serialize cache value: %s", e)
            return False
        
        with self.lock:
            # Check memory limits
            if not self._check_memory_limit(size_bytes):
                self._evict_lru_entries(size_bytes)
            
            # Generate secure key
            secure_key = self._generate_secure_key(key, partition)
            
            # Create entry
            entry = CacheEntry(
                key=secure_key,
                value=value,
                created_at=time.time(),
                expires_at=time.time() + ttl,
                checksum=hashlib.sha256(value_bytes).hexdigest() if self.config.validate_entries else None,
                partition=partition,
                size_bytes=size_bytes
            )
            
            # Store in appropriate location
            storage = self._get_storage(partition)
            
            # Check size limit
            if len(storage) >= self.config.max_cache_size:
                self._evict_lru_entries(size_bytes, partition)
            
            # Store entry
            storage[secure_key] = entry
            self.total_memory_bytes += size_bytes
            
            return True
    
    def invalidate(self,
                  key: Optional[str] = None,
                  partition: Optional[str] = None,
                  pattern: Optional[str] = None):
        """
        Invalidate cache entries.
        
        Args:
            key: Specific key to invalidate
            partition: Invalidate entire partition
            pattern: Invalidate keys matching pattern
        """
        with self.lock:
            if key:
                # Invalidate specific key
                secure_key = self._generate_secure_key(key, partition)
                self._evict_entry(secure_key, partition, reason="invalidated")
                
            elif partition:
                # Invalidate entire partition
                if partition in self.partitions:
                    for key in list(self.partitions[partition].keys()):
                        self._evict_entry(key, partition, reason="partition_invalidated")
                    del self.partitions[partition]
                    
            elif pattern:
                # Invalidate by pattern (simplified - could use regex)
                for storage in [self.cache] + list(self.partitions.values()):
                    keys_to_remove = [k for k in storage.keys() if pattern in k]
                    for key in keys_to_remove:
                        self._evict_entry(key, None, reason="pattern_invalidated")
            else:
                # Clear all
                self.clear()
    
    def clear(self):
        """Clear entire cache."""
        with self.lock:
            self.cache.clear()
            self.partitions.clear()
            self.total_memory_bytes = 0
            logger.info("Cache cleared")
    
    def _generate_secure_key(self, key: str, partition: Optional[str] = None) -> str:
        """Generate secure cache key using HMAC."""
        if not self.config.use_hmac:
            return f"{partition or 'default'}:{key}"
        
        # Create key material
        key_material = f"{self.config.cache_version}:{partition or 'default'}:{key}"
        
        # Add entropy if configured
        if self.config.add_key_entropy:
            # Add some deterministic entropy based on key characteristics
            entropy = hashlib.md5(key.encode()).hexdigest()[:8]
            key_material = f"{key_material}:{entropy}"
        
        # Generate HMAC
        hmac_key = hmac.new(
            self.secret_key,
            key_material.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac_key
    
    def _get_storage(self, partition: Optional[str] = None) -> OrderedDict:
        """Get appropriate storage for partition."""
        if not self.config.partition_cache or partition is None:
            return self.cache
        
        if partition not in self.partitions:
            self.partitions[partition] = OrderedDict()
        
        return self.partitions[partition]
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for storage."""
        if self.config.serialize_method == "pickle":
            return pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
        else:
            # JSON serialization
            if isinstance(value, (dict, list, str, int, float, bool, type(None))):
                return json.dumps(value).encode('utf-8')
            else:
                # Fall back to pickle for complex objects
                return pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
    
    def _check_memory_limit(self, additional_bytes: int) -> bool:
        """Check if adding bytes would exceed memory limit."""
        max_bytes = self.config.max_total_memory_mb * 1024 * 1024
        return (self.total_memory_bytes + additional_bytes) <= max_bytes
    
    def _evict_lru_entries(self, 
                          needed_bytes: int,
                          partition: Optional[str] = None):
        """Evict least recently used entries to make space."""
        storage = self._get_storage(partition)
        
        while len(storage) >= self.config.max_cache_size or \
              not self._check_memory_limit(needed_bytes):
            
            if not storage:
                break
            
            # Get least recently used (first item)
            lru_key = next(iter(storage))
            self._evict_entry(lru_key, partition, reason="lru_eviction")
    
    def _evict_entry(self,
                    key: str,
                    partition: Optional[str] = None,
                    reason: str = "unknown"):
        """Evict entry from cache."""
        storage = self._get_storage(partition)
        
        if key in storage:
            entry = storage[key]
            self.total_memory_bytes -= entry.size_bytes
            del storage[key]
            self.evictions += 1
            
            if self.config.log_security_events and reason != "lru_eviction":
                logger.debug("Cache entry evicted: %s (reason: %s)", key[:20], reason)
    
    def _handle_security_violation(self, violation_type: str, key: str):
        """Handle security violation."""
        self.security_violations += 1
        
        if self.config.log_security_events:
            logger.warning("Cache security violation: %s for key %s", 
                          violation_type, key[:20])
    
    def _cleanup_loop(self):
        """Periodically clean up expired entries."""
        while True:
            time.sleep(self.config.cleanup_interval_seconds)
            self._cleanup_expired()
    
    def _cleanup_expired(self):
        """Remove expired cache entries."""
        with self.lock:
            expired_count = 0
            
            # Check all storages
            all_storages = [("default", self.cache)] + \
                          [(p, s) for p, s in self.partitions.items()]
            
            for partition_name, storage in all_storages:
                expired_keys = []
                
                for key, entry in storage.items():
                    if entry.is_expired():
                        expired_keys.append(key)
                
                for key in expired_keys:
                    partition = partition_name if partition_name != "default" else None
                    self._evict_entry(key, partition, reason="expired")
                    expired_count += 1
            
            if expired_count > 0:
                logger.info("Cleaned up %d expired cache entries", expired_count)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            total_entries = len(self.cache) + \
                          sum(len(p) for p in self.partitions.values())
            
            hit_rate = self.hits / max(self.hits + self.misses, 1)
            
            return {
                'total_entries': total_entries,
                'memory_usage_mb': self.total_memory_bytes / (1024 * 1024),
                'hit_rate': hit_rate,
                'hits': self.hits,
                'misses': self.misses,
                'evictions': self.evictions,
                'security_violations': self.security_violations,
                'partitions': len(self.partitions),
                'config': {
                    'max_size': self.config.max_cache_size,
                    'max_memory_mb': self.config.max_total_memory_mb,
                    'using_hmac': self.config.use_hmac,
                    'validation_enabled': self.config.validate_entries
                }
            }
    
    def warm_cache(self, entries: Dict[str, Any], partition: Optional[str] = None):
        """Pre-populate cache with entries."""
        success_count = 0
        
        for key, value in entries.items():
            if self.put(key, value, partition=partition):
                success_count += 1
        
        logger.info("Warmed cache with %d entries", success_count)
        return success_count


def cached_secure(ttl: int = 3600,
                 partition: Optional[str] = None,
                 key_prefix: Optional[str] = None):
    """
    Decorator for secure caching of function results.
    
    Args:
        ttl: Time to live in seconds
        partition: Cache partition
        key_prefix: Optional prefix for cache key
    """
    def decorator(func):
        # Get or create cache instance
        cache = SecureCache()
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_parts = [key_prefix or func.__name__]
            
            # Add args to key
            for arg in args:
                if isinstance(arg, (str, int, float, bool)):
                    key_parts.append(str(arg))
                elif hasattr(arg, '__class__'):
                    # Skip 'self' or complex objects
                    continue
            
            # Add kwargs to key
            for k, v in sorted(kwargs.items()):
                if isinstance(v, (str, int, float, bool)):
                    key_parts.append(f"{k}={v}")
            
            cache_key = ":".join(key_parts)
            
            # Try to get from cache
            cached_value = cache.get(cache_key, partition=partition)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            cache.put(cache_key, result, ttl=ttl, partition=partition)
            
            return result
        
        # Attach cache to wrapper for access
        wrapper.cache = cache
        return wrapper
    
    return decorator


# Global secure cache instance
_default_cache = None


def get_cache(config: Optional[SecureCacheConfig] = None) -> SecureCache:
    """Get or create default cache instance."""
    global _default_cache
    
    if _default_cache is None or config is not None:
        _default_cache = SecureCache(config)
    
    return _default_cache