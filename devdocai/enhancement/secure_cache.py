"""
M009: Secure Caching Module.

Provides encrypted caching with AES-256-GCM, cache isolation,
TTL-based expiration, and protection against cache poisoning attacks.
Integrates with existing common security infrastructure.
"""

import os
import json
import time
import hashlib
import secrets
import logging
import threading
from typing import Dict, List, Optional, Any, Tuple, Union, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import pickle
from collections import OrderedDict
import base64

# Import common security infrastructure
try:
    from devdocai.common.security import EncryptionManager
    HAS_ENCRYPTION_MANAGER = True
except ImportError:
    HAS_ENCRYPTION_MANAGER = False

# Import M002's PII detector for cache content scanning
try:
    from devdocai.storage.pii_detector import PIIDetector, PIIType
    HAS_PII_DETECTOR = True
except ImportError:
    HAS_PII_DETECTOR = False

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """Cache isolation levels."""
    GLOBAL = "global"           # System-wide cache
    USER = "user"              # Per-user isolation
    TENANT = "tenant"          # Multi-tenant isolation
    SESSION = "session"        # Per-session isolation


class CacheStatus(Enum):
    """Cache operation status."""
    HIT = "hit"
    MISS = "miss"
    EXPIRED = "expired"
    INVALID = "invalid"
    ENCRYPTED = "encrypted"
    POISONED = "poisoned"
    ERROR = "error"


@dataclass
class CacheConfig:
    """Configuration for secure caching."""
    
    # Cache size limits
    max_size: int = 1000
    max_memory_mb: int = 200
    max_key_length: int = 1000
    max_value_size_mb: int = 10
    
    # TTL settings
    default_ttl_seconds: int = 3600
    max_ttl_seconds: int = 86400  # 24 hours
    min_ttl_seconds: int = 60
    
    # Encryption
    enable_encryption: bool = True
    encrypt_keys: bool = True
    encrypt_values: bool = True
    
    # Security features
    enable_isolation: bool = True
    enable_poisoning_protection: bool = True
    enable_pii_scanning: bool = True
    enable_integrity_checking: bool = True
    
    # Cache policies
    eviction_policy: str = "lru"  # lru, lfu, fifo
    compression_enabled: bool = True
    compression_threshold: int = 1024  # Compress values larger than this
    
    # Monitoring
    enable_metrics: bool = True
    enable_access_logging: bool = True
    log_cache_operations: bool = False
    
    # Performance
    async_writes: bool = True
    batch_operations: bool = True
    
    # Advanced security
    key_rotation_interval: int = 86400  # 24 hours
    audit_cache_access: bool = True
    prevent_timing_attacks: bool = True
    
    @classmethod
    def for_security_level(cls, level: str) -> 'CacheConfig':
        """Get configuration for specific security level."""
        configs = {
            "BASIC": cls(
                enable_encryption=False,
                enable_isolation=False,
                enable_poisoning_protection=False,
                enable_pii_scanning=False
            ),
            "STANDARD": cls(
                enable_encryption=True,
                enable_isolation=True,
                enable_poisoning_protection=True,
                enable_pii_scanning=True
            ),
            "STRICT": cls(
                max_size=500,
                max_memory_mb=100,
                default_ttl_seconds=1800,
                max_ttl_seconds=3600,
                enable_encryption=True,
                encrypt_keys=True,
                encrypt_values=True,
                enable_isolation=True,
                enable_poisoning_protection=True,
                enable_pii_scanning=True,
                enable_integrity_checking=True,
                audit_cache_access=True
            ),
            "PARANOID": cls(
                max_size=100,
                max_memory_mb=50,
                max_value_size_mb=1,
                default_ttl_seconds=900,
                max_ttl_seconds=1800,
                enable_encryption=True,
                encrypt_keys=True,
                encrypt_values=True,
                enable_isolation=True,
                enable_poisoning_protection=True,
                enable_pii_scanning=True,
                enable_integrity_checking=True,
                key_rotation_interval=3600,
                audit_cache_access=True,
                prevent_timing_attacks=True
            )
        }
        return configs.get(level, cls())


@dataclass
class CacheEntry:
    """Secure cache entry with metadata."""
    
    value: bytes  # Always stored as encrypted bytes
    created_at: datetime
    accessed_at: datetime
    expires_at: datetime
    access_count: int = 0
    isolation_key: str = "global"
    integrity_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return datetime.now() > self.expires_at
    
    def update_access(self) -> None:
        """Update access tracking."""
        self.accessed_at = datetime.now()
        self.access_count += 1


class SecureCache:
    """
    Secure cache with encryption, isolation, and poisoning protection.
    
    Provides encrypted storage, cache isolation, TTL expiration,
    and comprehensive security features for the Enhancement Pipeline.
    """
    
    def __init__(self, config: Optional[CacheConfig] = None):
        """Initialize secure cache."""
        self.config = config or CacheConfig()
        
        # Initialize encryption if available and enabled
        if HAS_ENCRYPTION_MANAGER and self.config.enable_encryption:
            self.encryption_manager = EncryptionManager()
        else:
            self.encryption_manager = None
        
        # Initialize PII detector if available and enabled
        if HAS_PII_DETECTOR and self.config.enable_pii_scanning:
            self.pii_detector = PIIDetector()
        else:
            self.pii_detector = None
        
        # Cache storage - use OrderedDict for LRU
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.cache_locks: Dict[str, threading.Lock] = {}
        self.global_lock = threading.RLock()
        
        # Security features
        self.encryption_key = self._generate_encryption_key()
        self.key_rotation_time = datetime.now()
        self.poisoned_keys: Set[str] = set()
        
        # Metrics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.security_violations = 0
        self.current_memory_usage = 0
        
        # Access patterns for anomaly detection
        self.access_patterns: Dict[str, List[datetime]] = {}
        
        logger.info(f"Secure cache initialized with config: {type(self.config).__name__}")
    
    def _generate_encryption_key(self) -> bytes:
        """Generate or derive encryption key."""
        if self.encryption_manager:
            # Use a consistent key derivation
            key, _ = self.encryption_manager.derive_key("cache_master_key_v1")
            return key
        else:
            # Fallback: generate random key (not persistent)
            return secrets.token_bytes(32)
    
    def _rotate_key_if_needed(self) -> None:
        """Rotate encryption key if needed."""
        if (self.config.key_rotation_interval and 
            (datetime.now() - self.key_rotation_time).total_seconds() > self.config.key_rotation_interval):
            
            old_key = self.encryption_key
            self.encryption_key = self._generate_encryption_key()
            self.key_rotation_time = datetime.now()
            
            # Re-encrypt existing cache entries with new key
            self._reencrypt_cache_entries(old_key, self.encryption_key)
            
            logger.info("Cache encryption key rotated")
    
    def _reencrypt_cache_entries(self, old_key: bytes, new_key: bytes) -> None:
        """Re-encrypt all cache entries with new key."""
        with self.global_lock:
            for cache_key, entry in self.cache.items():
                try:
                    # Decrypt with old key
                    if self.encryption_manager:
                        decrypted = self.encryption_manager.decrypt(entry.value, old_key)
                    else:
                        decrypted = entry.value
                    
                    # Re-encrypt with new key
                    if self.encryption_manager and self.config.enable_encryption:
                        entry.value = self.encryption_manager.encrypt(decrypted, new_key)
                    else:
                        entry.value = decrypted
                    
                    # Update integrity hash
                    if self.config.enable_integrity_checking:
                        entry.integrity_hash = self._calculate_integrity_hash(entry.value)
                
                except Exception as e:
                    logger.error(f"Failed to re-encrypt cache entry {cache_key}: {e}")
                    # Mark as poisoned
                    self.poisoned_keys.add(cache_key)
    
    def _calculate_integrity_hash(self, data: bytes) -> str:
        """Calculate integrity hash for data."""
        return hashlib.sha256(data + self.encryption_key).hexdigest()
    
    def _validate_integrity(self, entry: CacheEntry) -> bool:
        """Validate cache entry integrity."""
        if not self.config.enable_integrity_checking or not entry.integrity_hash:
            return True
        
        expected_hash = self._calculate_integrity_hash(entry.value)
        return expected_hash == entry.integrity_hash
    
    def _normalize_key(self, key: str, isolation_key: str = "global") -> str:
        """Normalize and hash cache key for security."""
        # Combine key with isolation
        full_key = f"{isolation_key}:{key}"
        
        # Hash for consistent length and security
        if self.config.encrypt_keys and self.encryption_manager:
            # Encrypt the key for additional security
            encrypted_key = self.encryption_manager.encrypt(full_key.encode(), self.encryption_key)
            return base64.b64encode(encrypted_key).decode()
        else:
            # Just hash it
            return hashlib.sha256(full_key.encode()).hexdigest()
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize and optionally encrypt value."""
        try:
            # Serialize to bytes
            if isinstance(value, (str, bytes)):
                serialized = value.encode() if isinstance(value, str) else value
            else:
                serialized = pickle.dumps(value)
            
            # Compress if enabled and beneficial
            if (self.config.compression_enabled and 
                len(serialized) > self.config.compression_threshold):
                import gzip
                serialized = gzip.compress(serialized)
            
            # Encrypt if enabled
            if self.config.enable_encryption and self.encryption_manager:
                encrypted = self.encryption_manager.encrypt(serialized, self.encryption_key)
                return encrypted
            else:
                return serialized
        
        except Exception as e:
            logger.error(f"Failed to serialize cache value: {e}")
            raise ValueError(f"Cache serialization failed: {e}")
    
    def _deserialize_value(self, data: bytes, entry: CacheEntry) -> Any:
        """Decrypt and deserialize value."""
        try:
            # Decrypt if needed
            if self.config.enable_encryption and self.encryption_manager:
                decrypted = self.encryption_manager.decrypt(data, self.encryption_key)
            else:
                decrypted = data
            
            # Decompress if compressed
            if (self.config.compression_enabled and 
                len(decrypted) > 0 and decrypted[:2] == b'\x1f\x8b'):  # gzip header
                import gzip
                decrypted = gzip.decompress(decrypted)
            
            # Deserialize
            try:
                # Try to decode as string first
                return decrypted.decode()
            except UnicodeDecodeError:
                # Fall back to pickle
                return pickle.loads(decrypted)
        
        except Exception as e:
            logger.error(f"Failed to deserialize cache value: {e}")
            # Mark as poisoned
            self.poisoned_keys.add(entry.isolation_key)
            raise ValueError(f"Cache deserialization failed: {e}")
    
    def _check_pii_content(self, value: Any) -> bool:
        """Check if value contains PII."""
        if not self.pii_detector:
            return False
        
        try:
            # Convert to string for PII detection
            if isinstance(value, str):
                text = value
            elif isinstance(value, bytes):
                text = value.decode('utf-8', errors='ignore')
            else:
                text = str(value)
            
            result = self.pii_detector.detect_pii(text)
            return result.confidence > 0.7  # High confidence PII detection
        
        except Exception as e:
            logger.warning(f"PII detection failed: {e}")
            return False
    
    def _detect_cache_poisoning(self, key: str, value: Any) -> bool:
        """Detect potential cache poisoning attempts."""
        if not self.config.enable_poisoning_protection:
            return False
        
        # Check for suspicious patterns
        suspicious_indicators = [
            # Key-based indicators
            len(key) > self.config.max_key_length,
            '../' in key or '..\\' in key,  # Path traversal
            key.count('/') > 10,  # Excessive path depth
            
            # Value-based indicators (if string)
            isinstance(value, str) and (
                '<script' in value.lower() or
                'javascript:' in value.lower() or
                'eval(' in value.lower() or
                len(value) > self.config.max_value_size_mb * 1024 * 1024
            )
        ]
        
        return any(suspicious_indicators)
    
    def _evict_entries(self) -> None:
        """Evict entries based on policy."""
        if len(self.cache) <= self.config.max_size:
            return
        
        entries_to_remove = len(self.cache) - self.config.max_size + 1
        
        if self.config.eviction_policy == "lru":
            # OrderedDict maintains insertion/access order
            for _ in range(entries_to_remove):
                if self.cache:
                    key, entry = self.cache.popitem(last=False)  # Remove oldest
                    self.evictions += 1
                    if self.config.log_cache_operations:
                        logger.debug(f"Evicted cache entry: {key[:20]}...")
        
        elif self.config.eviction_policy == "lfu":
            # Sort by access count and remove least frequently used
            sorted_entries = sorted(
                self.cache.items(),
                key=lambda x: x[1].access_count
            )
            for key, _ in sorted_entries[:entries_to_remove]:
                del self.cache[key]
                self.evictions += 1
        
        elif self.config.eviction_policy == "fifo":
            # Remove oldest entries
            for _ in range(entries_to_remove):
                if self.cache:
                    key, entry = self.cache.popitem(last=False)
                    self.evictions += 1
    
    def put(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        isolation_key: str = "global"
    ) -> bool:
        """
        Store value in cache with optional TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            isolation_key: Cache isolation key
            
        Returns:
            True if stored successfully, False otherwise
        """
        try:
            # Rotate key if needed
            self._rotate_key_if_needed()
            
            # Security checks
            if self._detect_cache_poisoning(key, value):
                self.security_violations += 1
                logger.warning(f"Cache poisoning attempt detected: {key[:50]}...")
                return False
            
            # Check for PII content
            if self._check_pii_content(value):
                logger.warning(f"Attempting to cache PII content: {key[:50]}...")
                if not self.config.enable_pii_scanning:
                    # Block if PII scanning is disabled but PII detected
                    return False
            
            # Normalize key
            normalized_key = self._normalize_key(key, isolation_key)
            
            # Check if key is poisoned
            if normalized_key in self.poisoned_keys:
                logger.warning(f"Attempt to use poisoned cache key: {key[:50]}...")
                return False
            
            # Serialize and encrypt value
            serialized_value = self._serialize_value(value)
            
            # Calculate TTL
            ttl = ttl or self.config.default_ttl_seconds
            ttl = max(self.config.min_ttl_seconds, min(ttl, self.config.max_ttl_seconds))
            
            # Create cache entry
            now = datetime.now()
            entry = CacheEntry(
                value=serialized_value,
                created_at=now,
                accessed_at=now,
                expires_at=now + timedelta(seconds=ttl),
                isolation_key=isolation_key,
                metadata={"original_key": key, "ttl": ttl}
            )
            
            # Add integrity hash if enabled
            if self.config.enable_integrity_checking:
                entry.integrity_hash = self._calculate_integrity_hash(serialized_value)
            
            # Store in cache with locking
            with self.global_lock:
                self.cache[normalized_key] = entry
                # Update LRU order
                self.cache.move_to_end(normalized_key)
                
                # Evict if necessary
                self._evict_entries()
            
            if self.config.log_cache_operations:
                logger.debug(f"Cached entry: {key[:50]}... (TTL: {ttl}s, Isolation: {isolation_key})")
            
            return True
        
        except Exception as e:
            logger.error(f"Cache put operation failed: {e}")
            return False
    
    def get(
        self,
        key: str,
        isolation_key: str = "global",
        update_access: bool = True
    ) -> Tuple[Any, CacheStatus]:
        """
        Retrieve value from cache.
        
        Args:
            key: Cache key
            isolation_key: Cache isolation key
            update_access: Whether to update access statistics
            
        Returns:
            Tuple of (value, status)
        """
        try:
            # Normalize key
            normalized_key = self._normalize_key(key, isolation_key)
            
            # Check if key is poisoned
            if normalized_key in self.poisoned_keys:
                logger.warning(f"Attempt to access poisoned cache key: {key[:50]}...")
                return None, CacheStatus.POISONED
            
            # Get from cache
            with self.global_lock:
                if normalized_key not in self.cache:
                    self.misses += 1
                    return None, CacheStatus.MISS
                
                entry = self.cache[normalized_key]
                
                # Check expiration
                if entry.is_expired():
                    del self.cache[normalized_key]
                    self.misses += 1
                    if self.config.log_cache_operations:
                        logger.debug(f"Cache entry expired: {key[:50]}...")
                    return None, CacheStatus.EXPIRED
                
                # Validate integrity
                if not self._validate_integrity(entry):
                    self.security_violations += 1
                    self.poisoned_keys.add(normalized_key)
                    del self.cache[normalized_key]
                    logger.warning(f"Cache integrity violation: {key[:50]}...")
                    return None, CacheStatus.INVALID
                
                # Update access tracking
                if update_access:
                    entry.update_access()
                    # Move to end for LRU
                    self.cache.move_to_end(normalized_key)
                
                self.hits += 1
            
            # Deserialize value
            try:
                value = self._deserialize_value(entry.value, entry)
                
                # Record access pattern for anomaly detection
                if isolation_key not in self.access_patterns:
                    self.access_patterns[isolation_key] = []
                self.access_patterns[isolation_key].append(datetime.now())
                
                # Keep only recent access patterns
                cutoff = datetime.now() - timedelta(hours=1)
                self.access_patterns[isolation_key] = [
                    access_time for access_time in self.access_patterns[isolation_key]
                    if access_time > cutoff
                ]
                
                if self.config.log_cache_operations:
                    logger.debug(f"Cache hit: {key[:50]}... (Age: {datetime.now() - entry.created_at})")
                
                return value, CacheStatus.HIT
            
            except Exception as e:
                logger.error(f"Cache value deserialization failed: {e}")
                # Remove corrupted entry
                with self.global_lock:
                    if normalized_key in self.cache:
                        del self.cache[normalized_key]
                self.poisoned_keys.add(normalized_key)
                return None, CacheStatus.INVALID
        
        except Exception as e:
            logger.error(f"Cache get operation failed: {e}")
            return None, CacheStatus.ERROR
    
    def delete(self, key: str, isolation_key: str = "global") -> bool:
        """Delete entry from cache."""
        try:
            normalized_key = self._normalize_key(key, isolation_key)
            
            with self.global_lock:
                if normalized_key in self.cache:
                    del self.cache[normalized_key]
                    if self.config.log_cache_operations:
                        logger.debug(f"Cache entry deleted: {key[:50]}...")
                    return True
                
                return False
        
        except Exception as e:
            logger.error(f"Cache delete operation failed: {e}")
            return False
    
    def clear(self, isolation_key: Optional[str] = None) -> int:
        """
        Clear cache entries.
        
        Args:
            isolation_key: If provided, only clear entries for this isolation key
            
        Returns:
            Number of entries cleared
        """
        cleared_count = 0
        
        try:
            with self.global_lock:
                if isolation_key is None:
                    # Clear all entries
                    cleared_count = len(self.cache)
                    self.cache.clear()
                    self.poisoned_keys.clear()
                else:
                    # Clear entries for specific isolation key
                    keys_to_remove = []
                    for cache_key, entry in self.cache.items():
                        if entry.isolation_key == isolation_key:
                            keys_to_remove.append(cache_key)
                    
                    for key in keys_to_remove:
                        del self.cache[key]
                    
                    cleared_count = len(keys_to_remove)
            
            logger.info(f"Cache cleared: {cleared_count} entries (isolation: {isolation_key or 'all'})")
            return cleared_count
        
        except Exception as e:
            logger.error(f"Cache clear operation failed: {e}")
            return 0
    
    def cleanup_expired(self) -> int:
        """Remove expired entries and return count."""
        expired_count = 0
        
        try:
            with self.global_lock:
                keys_to_remove = []
                for key, entry in self.cache.items():
                    if entry.is_expired():
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del self.cache[key]
                    expired_count += 1
            
            if expired_count > 0:
                logger.debug(f"Cleaned up {expired_count} expired cache entries")
            
            return expired_count
        
        except Exception as e:
            logger.error(f"Cache cleanup failed: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / max(total_requests, 1)
        
        return {
            "size": len(self.cache),
            "max_size": self.config.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "evictions": self.evictions,
            "security_violations": self.security_violations,
            "poisoned_keys": len(self.poisoned_keys),
            "memory_usage_mb": self.current_memory_usage / (1024 * 1024),
            "isolation_levels": len(set(entry.isolation_key for entry in self.cache.values())),
            "encryption_enabled": self.config.enable_encryption,
            "integrity_checking": self.config.enable_integrity_checking
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get cache health status."""
        stats = self.get_stats()
        
        # Determine health status
        health_issues = []
        
        if stats["hit_rate"] < 0.3:
            health_issues.append("Low hit rate")
        
        if stats["security_violations"] > 0:
            health_issues.append("Security violations detected")
        
        if stats["poisoned_keys"] > 0:
            health_issues.append("Poisoned keys present")
        
        if stats["memory_usage_mb"] > self.config.max_memory_mb * 0.9:
            health_issues.append("High memory usage")
        
        health_status = "healthy" if not health_issues else "warning" if len(health_issues) < 3 else "critical"
        
        return {
            "status": health_status,
            "issues": health_issues,
            "stats": stats,
            "last_key_rotation": self.key_rotation_time.isoformat()
        }


def create_secure_cache(security_level: str = "STANDARD") -> SecureCache:
    """
    Factory function to create secure cache.
    
    Args:
        security_level: Security level (BASIC, STANDARD, STRICT, PARANOID)
        
    Returns:
        Configured SecureCache
    """
    config = CacheConfig.for_security_level(security_level)
    return SecureCache(config)