"""
Unified Cache System for M009 Enhancement Pipeline - Pass 4: Refactoring.

Consolidates enhancement_cache.py and secure_cache.py into a single,
mode-driven caching solution with intelligent feature selection.

Features:
- Mode-based configuration (basic, performance, secure, enterprise)
- LRU caching with optional semantic similarity
- Encryption support with AES-256-GCM
- Cache isolation and TTL management
- PII detection and security validation
- Compression and distributed cache support
"""

import hashlib
import json
import logging
import pickle
import time
import asyncio
import secrets
import threading
from typing import Dict, List, Optional, Any, Tuple, Union, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from collections import OrderedDict
import base64

# Optional dependencies with graceful degradation
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    import lz4.frame
    LZ4_AVAILABLE = True
except ImportError:
    LZ4_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False

# Security components
try:
    from devdocai.common.security import EncryptionManager
    HAS_ENCRYPTION_MANAGER = True
except ImportError:
    HAS_ENCRYPTION_MANAGER = False

try:
    from devdocai.storage.pii_detector import PIIDetector, PIIType
    HAS_PII_DETECTOR = True
except ImportError:
    HAS_PII_DETECTOR = False

logger = logging.getLogger(__name__)


class UnifiedCacheMode(Enum):
    """Cache operation modes aligned with pipeline modes."""
    BASIC = "basic"           # Simple hash-based cache, no encryption
    PERFORMANCE = "performance"  # LRU with semantic similarity and compression
    SECURE = "secure"         # Encrypted cache with isolation and PII scanning
    ENTERPRISE = "enterprise"  # Full feature set including distributed caching


class CacheStatus(Enum):
    """Cache operation status."""
    HIT = "hit"
    MISS = "miss"
    EXPIRED = "expired"
    INVALID = "invalid"
    ENCRYPTED = "encrypted"
    POISONED = "poisoned"
    SECURITY_VIOLATION = "security_violation"
    ERROR = "error"


@dataclass
class UnifiedCacheEntry:
    """Unified cache entry supporting all modes."""
    
    key: str
    value: Any
    fingerprint: str
    created_at: datetime
    accessed_at: datetime
    access_count: int = 0
    size_bytes: int = 0
    ttl_seconds: Optional[int] = None
    
    # Security attributes
    isolation_key: Optional[str] = None
    encrypted: bool = False
    pii_detected: bool = False
    integrity_hash: Optional[str] = None
    
    # Performance attributes
    compressed: bool = False
    semantic_embedding: Optional[Any] = None
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.ttl_seconds is None:
            return False
        expiry = self.created_at + timedelta(seconds=self.ttl_seconds)
        return datetime.now() > expiry
    
    def update_access(self) -> None:
        """Update access tracking."""
        self.accessed_at = datetime.now()
        self.access_count += 1
    
    def validate_integrity(self) -> bool:
        """Validate entry integrity."""
        if not self.integrity_hash:
            return True
        
        current_hash = hashlib.sha256(str(self.value).encode()).hexdigest()
        return current_hash == self.integrity_hash


@dataclass
class UnifiedCacheStats:
    """Comprehensive cache statistics."""
    
    # Basic stats
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_size_bytes: int = 0
    entry_count: int = 0
    
    # Performance stats
    semantic_matches: int = 0
    compression_saves_bytes: int = 0
    
    # Security stats
    encryption_operations: int = 0
    pii_violations: int = 0
    integrity_failures: int = 0
    isolation_violations: int = 0
    
    @property
    def hit_ratio(self) -> float:
        """Calculate hit ratio."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    @property
    def compression_ratio(self) -> float:
        """Calculate compression savings ratio."""
        if self.total_size_bytes == 0:
            return 0.0
        return self.compression_saves_bytes / self.total_size_bytes
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive stats summary."""
        return {
            "performance": {
                "hits": self.hits,
                "misses": self.misses,
                "hit_ratio": self.hit_ratio,
                "evictions": self.evictions,
                "total_size_mb": self.total_size_bytes / (1024 * 1024),
                "entry_count": self.entry_count,
                "semantic_matches": self.semantic_matches,
                "compression_ratio": self.compression_ratio
            },
            "security": {
                "encryption_operations": self.encryption_operations,
                "pii_violations": self.pii_violations,
                "integrity_failures": self.integrity_failures,
                "isolation_violations": self.isolation_violations
            }
        }


@dataclass
class UnifiedCacheConfig:
    """Unified cache configuration for all modes."""
    
    # Basic configuration
    max_size: int = 500
    max_memory_mb: int = 100
    default_ttl_seconds: int = 3600
    
    # Mode-specific features
    enable_semantic_similarity: bool = False
    enable_compression: bool = False
    enable_encryption: bool = False
    enable_isolation: bool = False
    enable_pii_scanning: bool = False
    enable_distributed: bool = False
    
    # Performance settings
    semantic_similarity_threshold: float = 0.8
    compression_threshold_bytes: int = 1024
    
    # Security settings
    isolation_levels: Set[str] = field(default_factory=set)
    max_key_length: int = 500
    max_value_size_mb: int = 5
    
    # Distributed cache settings
    redis_url: Optional[str] = None
    redis_prefix: str = "m009_cache"
    redis_ttl_seconds: int = 7200
    
    @classmethod
    def for_mode(cls, mode: UnifiedCacheMode, **overrides) -> 'UnifiedCacheConfig':
        """Create configuration for specific mode."""
        if mode == UnifiedCacheMode.BASIC:
            config = cls(
                max_size=200,
                max_memory_mb=50,
                default_ttl_seconds=1800,  # 30 minutes
                enable_semantic_similarity=False,
                enable_compression=False,
                enable_encryption=False,
                enable_isolation=False,
                enable_pii_scanning=False,
                enable_distributed=False
            )
        
        elif mode == UnifiedCacheMode.PERFORMANCE:
            config = cls(
                max_size=2000,
                max_memory_mb=300,
                default_ttl_seconds=3600,  # 1 hour
                enable_semantic_similarity=SEMANTIC_AVAILABLE,
                enable_compression=LZ4_AVAILABLE,
                enable_encryption=False,
                enable_isolation=False,
                enable_pii_scanning=False,
                enable_distributed=REDIS_AVAILABLE,
                semantic_similarity_threshold=0.85
            )
        
        elif mode == UnifiedCacheMode.SECURE:
            config = cls(
                max_size=1000,
                max_memory_mb=200,
                default_ttl_seconds=1800,  # 30 minutes for security
                enable_semantic_similarity=False,  # Disable for security
                enable_compression=False,  # May interfere with encryption
                enable_encryption=HAS_ENCRYPTION_MANAGER,
                enable_isolation=True,
                enable_pii_scanning=HAS_PII_DETECTOR,
                enable_distributed=False,  # Security first
                isolation_levels={"user", "session"}
            )
        
        elif mode == UnifiedCacheMode.ENTERPRISE:
            config = cls(
                max_size=5000,
                max_memory_mb=512,
                default_ttl_seconds=7200,  # 2 hours
                enable_semantic_similarity=SEMANTIC_AVAILABLE,
                enable_compression=LZ4_AVAILABLE,
                enable_encryption=HAS_ENCRYPTION_MANAGER,
                enable_isolation=True,
                enable_pii_scanning=HAS_PII_DETECTOR,
                enable_distributed=REDIS_AVAILABLE,
                isolation_levels={"user", "session", "tenant"}
            )
        
        else:
            config = cls()
        
        # Apply overrides
        for key, value in overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        return config


class UnifiedCache:
    """
    Unified cache system consolidating performance and security features.
    
    Provides mode-based operation with feature selection based on requirements.
    """
    
    def __init__(
        self,
        mode: UnifiedCacheMode = UnifiedCacheMode.PERFORMANCE,
        config: Optional[UnifiedCacheConfig] = None
    ):
        """
        Initialize unified cache.
        
        Args:
            mode: Cache operation mode
            config: Cache configuration (auto-generated if None)
        """
        self.mode = mode
        self.config = config or UnifiedCacheConfig.for_mode(mode)
        
        # Initialize storage
        self._cache: OrderedDict[str, UnifiedCacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        
        # Initialize statistics
        self.stats = UnifiedCacheStats()
        
        # Initialize optional components
        self._init_components()
        
        logger.info(f"Unified cache initialized in {mode.value.upper()} mode")
        logger.info(f"Features: {self._get_enabled_features()}")
    
    def _init_components(self) -> None:
        """Initialize mode-specific components."""
        # Encryption manager
        if self.config.enable_encryption and HAS_ENCRYPTION_MANAGER:
            try:
                self.encryption_manager = EncryptionManager()
            except Exception as e:
                logger.warning(f"Failed to initialize encryption: {e}")
                self.encryption_manager = None
                self.config.enable_encryption = False
        else:
            self.encryption_manager = None
        
        # PII detector
        if self.config.enable_pii_scanning and HAS_PII_DETECTOR:
            try:
                self.pii_detector = PIIDetector()
            except Exception as e:
                logger.warning(f"Failed to initialize PII detector: {e}")
                self.pii_detector = None
                self.config.enable_pii_scanning = False
        else:
            self.pii_detector = None
        
        # Semantic similarity
        if self.config.enable_semantic_similarity and SEMANTIC_AVAILABLE:
            try:
                self.semantic_model = SentenceTransformer('all-MiniLM-L6-v2')
            except Exception as e:
                logger.warning(f"Failed to initialize semantic model: {e}")
                self.semantic_model = None
                self.config.enable_semantic_similarity = False
        else:
            self.semantic_model = None
        
        # Redis connection
        if self.config.enable_distributed and REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(
                    self.config.redis_url or "redis://localhost:6379/0"
                )
                # Test connection
                self.redis_client.ping()
            except Exception as e:
                logger.warning(f"Failed to initialize Redis: {e}")
                self.redis_client = None
                self.config.enable_distributed = False
        else:
            self.redis_client = None
    
    def _get_enabled_features(self) -> List[str]:
        """Get list of enabled features."""
        features = []
        if self.config.enable_semantic_similarity:
            features.append("semantic")
        if self.config.enable_compression:
            features.append("compression")
        if self.config.enable_encryption:
            features.append("encryption")
        if self.config.enable_isolation:
            features.append("isolation")
        if self.config.enable_pii_scanning:
            features.append("pii_scanning")
        if self.config.enable_distributed:
            features.append("distributed")
        return features
    
    def get(
        self,
        key: str,
        config_dict: Optional[Dict[str, Any]] = None,
        isolation_key: Optional[str] = None,
        use_semantic: bool = False
    ) -> Tuple[Any, CacheStatus]:
        """
        Get value from cache with mode-specific features.
        
        Args:
            key: Cache key (content hash or identifier)
            config_dict: Configuration for semantic similarity
            isolation_key: Isolation key for secure modes
            use_semantic: Enable semantic similarity matching
            
        Returns:
            Tuple of (value, status)
        """
        with self._lock:
            # Generate full cache key
            full_key = self._generate_cache_key(key, isolation_key)
            
            # Direct hit check
            if full_key in self._cache:
                entry = self._cache[full_key]
                
                # Check expiration
                if entry.is_expired():
                    del self._cache[full_key]
                    self.stats.misses += 1
                    return None, CacheStatus.EXPIRED
                
                # Validate integrity (secure modes)
                if self.config.enable_encryption and not entry.validate_integrity():
                    del self._cache[full_key]
                    self.stats.integrity_failures += 1
                    return None, CacheStatus.INVALID
                
                # Check isolation (secure modes)
                if self.config.enable_isolation and not self._check_isolation(entry, isolation_key):
                    self.stats.isolation_violations += 1
                    return None, CacheStatus.SECURITY_VIOLATION
                
                # Update access tracking
                entry.update_access()
                self._cache.move_to_end(full_key)
                self.stats.hits += 1
                
                # Decrypt if needed
                value = self._decrypt_value(entry.value) if entry.encrypted else entry.value
                
                return value, CacheStatus.HIT
            
            # Semantic similarity search (performance modes)
            if (use_semantic and 
                self.config.enable_semantic_similarity and 
                self.semantic_model is not None):
                
                semantic_result = self._semantic_search(key, isolation_key)
                if semantic_result:
                    self.stats.semantic_matches += 1
                    return semantic_result, CacheStatus.HIT
            
            # Distributed cache check
            if self.config.enable_distributed and self.redis_client:
                distributed_result = self._get_distributed(full_key)
                if distributed_result:
                    # Store in local cache
                    self.put(key, distributed_result, isolation_key=isolation_key)
                    return distributed_result, CacheStatus.HIT
            
            self.stats.misses += 1
            return None, CacheStatus.MISS
    
    def put(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        isolation_key: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Put value in cache with mode-specific processing.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            isolation_key: Isolation key for secure modes
            metadata: Additional metadata
            
        Returns:
            True if successfully cached
        """
        with self._lock:
            try:
                # Security validation
                if not self._validate_cache_input(key, value):
                    return False
                
                # PII scanning (secure modes)
                if self.config.enable_pii_scanning and self.pii_detector:
                    if self._detect_pii(value):
                        self.stats.pii_violations += 1
                        logger.warning("PII detected in cache value - blocking")
                        return False
                
                # Generate cache key
                full_key = self._generate_cache_key(key, isolation_key)
                
                # Prepare value for storage
                processed_value = self._process_value_for_storage(value)
                
                # Calculate size
                size_bytes = len(str(processed_value).encode())
                
                # Check size limits
                if size_bytes > (self.config.max_value_size_mb * 1024 * 1024):
                    logger.warning(f"Value too large for cache: {size_bytes} bytes")
                    return False
                
                # Generate semantic embedding (performance modes)
                semantic_embedding = None
                if self.config.enable_semantic_similarity and self.semantic_model:
                    try:
                        text_content = str(value)[:1000]  # Limit for performance
                        semantic_embedding = self.semantic_model.encode(text_content)
                    except Exception as e:
                        logger.debug(f"Failed to generate semantic embedding: {e}")
                
                # Create cache entry
                entry = UnifiedCacheEntry(
                    key=full_key,
                    value=processed_value,
                    fingerprint=hashlib.md5(str(value).encode()).hexdigest(),
                    created_at=datetime.now(),
                    accessed_at=datetime.now(),
                    size_bytes=size_bytes,
                    ttl_seconds=ttl or self.config.default_ttl_seconds,
                    isolation_key=isolation_key,
                    encrypted=self.config.enable_encryption,
                    semantic_embedding=semantic_embedding,
                    metadata=metadata or {}
                )
                
                # Generate integrity hash
                if self.config.enable_encryption:
                    entry.integrity_hash = hashlib.sha256(str(value).encode()).hexdigest()
                
                # Eviction if needed
                self._evict_if_needed()
                
                # Store entry
                self._cache[full_key] = entry
                self._cache.move_to_end(full_key)
                
                # Update stats
                self.stats.entry_count = len(self._cache)
                self.stats.total_size_bytes += size_bytes
                
                # Distributed cache storage
                if self.config.enable_distributed and self.redis_client:
                    self._put_distributed(full_key, value, ttl)
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to put value in cache: {e}")
                return False
    
    def _generate_cache_key(self, key: str, isolation_key: Optional[str] = None) -> str:
        """Generate full cache key with isolation."""
        if self.config.enable_isolation and isolation_key:
            return f"{isolation_key}:{key}"
        return key
    
    def _validate_cache_input(self, key: str, value: Any) -> bool:
        """Validate cache input for security."""
        # Key length check
        if len(key) > self.config.max_key_length:
            logger.warning(f"Cache key too long: {len(key)} > {self.config.max_key_length}")
            return False
        
        # Basic value validation
        if value is None:
            return False
        
        return True
    
    def _detect_pii(self, value: Any) -> bool:
        """Detect PII in cache value."""
        if not self.pii_detector:
            return False
        
        try:
            text_content = str(value)[:10000]  # Limit scanning for performance
            pii_results = self.pii_detector.detect_pii(text_content)
            return len(pii_results.detected_types) > 0
        except Exception as e:
            logger.debug(f"PII detection failed: {e}")
            return False
    
    def _process_value_for_storage(self, value: Any) -> Any:
        """Process value for storage (compression, encryption)."""
        processed_value = value
        
        # Compression (performance modes)
        if (self.config.enable_compression and 
            LZ4_AVAILABLE and 
            len(str(value).encode()) > self.config.compression_threshold_bytes):
            try:
                serialized = pickle.dumps(value)
                compressed = lz4.frame.compress(serialized)
                if len(compressed) < len(serialized):
                    processed_value = {
                        "_compressed": True,
                        "_data": base64.b64encode(compressed).decode()
                    }
                    self.stats.compression_saves_bytes += len(serialized) - len(compressed)
            except Exception as e:
                logger.debug(f"Compression failed: {e}")
        
        # Encryption (secure modes)
        if self.config.enable_encryption and self.encryption_manager:
            try:
                encrypted_value = self._encrypt_value(processed_value)
                processed_value = encrypted_value
                self.stats.encryption_operations += 1
            except Exception as e:
                logger.warning(f"Encryption failed: {e}")
        
        return processed_value
    
    def _encrypt_value(self, value: Any) -> str:
        """Encrypt cache value."""
        if not self.encryption_manager:
            return value
        
        try:
            serialized = json.dumps(value, default=str)
            encrypted = self.encryption_manager.encrypt_data(serialized.encode())
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Value encryption failed: {e}")
            return value
    
    def _decrypt_value(self, encrypted_value: str) -> Any:
        """Decrypt cache value."""
        if not self.encryption_manager:
            return encrypted_value
        
        try:
            encrypted_data = base64.b64decode(encrypted_value.encode())
            decrypted = self.encryption_manager.decrypt_data(encrypted_data)
            return json.loads(decrypted.decode())
        except Exception as e:
            logger.error(f"Value decryption failed: {e}")
            return encrypted_value
    
    def _check_isolation(self, entry: UnifiedCacheEntry, isolation_key: Optional[str]) -> bool:
        """Check cache isolation."""
        if not self.config.enable_isolation:
            return True
        
        # Global cache accessible to all
        if entry.isolation_key is None:
            return True
        
        # Check key match
        return entry.isolation_key == isolation_key
    
    def _semantic_search(self, query: str, isolation_key: Optional[str] = None) -> Optional[Any]:
        """Search cache using semantic similarity."""
        if not self.semantic_model:
            return None
        
        try:
            query_embedding = self.semantic_model.encode(query[:1000])
            best_match = None
            best_score = 0.0
            
            for entry in self._cache.values():
                # Check isolation
                if not self._check_isolation(entry, isolation_key):
                    continue
                
                # Check expiration
                if entry.is_expired():
                    continue
                
                # Compare embeddings
                if entry.semantic_embedding is not None:
                    similarity = cosine_similarity(
                        query_embedding.reshape(1, -1),
                        entry.semantic_embedding.reshape(1, -1)
                    )[0][0]
                    
                    if similarity > best_score and similarity >= self.config.semantic_similarity_threshold:
                        best_score = similarity
                        best_match = entry
            
            if best_match:
                best_match.update_access()
                value = self._decrypt_value(best_match.value) if best_match.encrypted else best_match.value
                return value
            
        except Exception as e:
            logger.debug(f"Semantic search failed: {e}")
        
        return None
    
    def _get_distributed(self, key: str) -> Optional[Any]:
        """Get value from distributed cache."""
        if not self.redis_client:
            return None
        
        try:
            redis_key = f"{self.config.redis_prefix}:{key}"
            cached_data = self.redis_client.get(redis_key)
            
            if cached_data:
                return pickle.loads(cached_data)
        except Exception as e:
            logger.debug(f"Distributed cache get failed: {e}")
        
        return None
    
    def _put_distributed(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Put value in distributed cache."""
        if not self.redis_client:
            return
        
        try:
            redis_key = f"{self.config.redis_prefix}:{key}"
            serialized_value = pickle.dumps(value)
            ttl_seconds = ttl or self.config.redis_ttl_seconds
            
            self.redis_client.setex(redis_key, ttl_seconds, serialized_value)
        except Exception as e:
            logger.debug(f"Distributed cache put failed: {e}")
    
    def _evict_if_needed(self) -> None:
        """Evict entries if cache limits exceeded."""
        # Size-based eviction
        while len(self._cache) >= self.config.max_size:
            self._evict_lru()
        
        # Memory-based eviction
        max_bytes = self.config.max_memory_mb * 1024 * 1024
        while self.stats.total_size_bytes > max_bytes and self._cache:
            self._evict_lru()
        
        # TTL-based cleanup
        self._cleanup_expired()
    
    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._cache:
            return
        
        key, entry = self._cache.popitem(last=False)
        self.stats.evictions += 1
        self.stats.total_size_bytes -= entry.size_bytes
        logger.debug(f"Evicted cache entry: {key}")
    
    def _cleanup_expired(self) -> None:
        """Remove expired entries."""
        expired_keys = []
        
        for key, entry in self._cache.items():
            if entry.is_expired():
                expired_keys.append(key)
        
        for key in expired_keys:
            entry = self._cache.pop(key)
            self.stats.total_size_bytes -= entry.size_bytes
            logger.debug(f"Removed expired entry: {key}")
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self.stats = UnifiedCacheStats()
            
            # Clear distributed cache if enabled
            if self.redis_client:
                try:
                    keys = self.redis_client.keys(f"{self.config.redis_prefix}:*")
                    if keys:
                        self.redis_client.delete(*keys)
                except Exception as e:
                    logger.debug(f"Failed to clear distributed cache: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        with self._lock:
            self.stats.entry_count = len(self._cache)
            return self.stats.get_summary()
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get cache health status."""
        health_issues = []
        health_score = 100
        
        # Check hit ratio
        if self.stats.hit_ratio < 0.5:
            health_issues.append("Low cache hit ratio")
            health_score -= 20
        
        # Check memory usage
        memory_usage_ratio = self.stats.total_size_bytes / (self.config.max_memory_mb * 1024 * 1024)
        if memory_usage_ratio > 0.9:
            health_issues.append("High memory usage")
            health_score -= 25
        
        # Check security violations
        if self.stats.pii_violations > 0:
            health_issues.append("PII violations detected")
            health_score -= 30
        
        if self.stats.integrity_failures > 0:
            health_issues.append("Integrity check failures")
            health_score -= 20
        
        health_status = "healthy"
        if health_score < 90:
            health_status = "warning"
        if health_score < 70:
            health_status = "degraded"
        if health_score < 50:
            health_status = "critical"
        
        return {
            "status": health_status,
            "score": max(health_score, 0),
            "issues": health_issues,
            "memory_usage_ratio": memory_usage_ratio,
            "hit_ratio": self.stats.hit_ratio
        }
    
    def cleanup_expired(self) -> int:
        """Clean up expired entries and return count."""
        with self._lock:
            initial_count = len(self._cache)
            self._cleanup_expired()
            return initial_count - len(self._cache)


# Factory functions for easy instantiation

def create_unified_cache(
    mode: Union[str, UnifiedCacheMode] = UnifiedCacheMode.PERFORMANCE,
    **config_overrides
) -> UnifiedCache:
    """
    Factory function to create unified cache.
    
    Args:
        mode: Cache operation mode
        **config_overrides: Configuration overrides
        
    Returns:
        Configured UnifiedCache
    """
    if isinstance(mode, str):
        mode = UnifiedCacheMode(mode.lower())
    
    config = UnifiedCacheConfig.for_mode(mode, **config_overrides)
    return UnifiedCache(mode, config)


def create_basic_cache(**overrides) -> UnifiedCache:
    """Create BASIC mode cache."""
    return create_unified_cache(UnifiedCacheMode.BASIC, **overrides)


def create_performance_cache(**overrides) -> UnifiedCache:
    """Create PERFORMANCE mode cache."""
    return create_unified_cache(UnifiedCacheMode.PERFORMANCE, **overrides)


def create_secure_cache(**overrides) -> UnifiedCache:
    """Create SECURE mode cache."""
    return create_unified_cache(UnifiedCacheMode.SECURE, **overrides)


def create_enterprise_cache(**overrides) -> UnifiedCache:
    """Create ENTERPRISE mode cache."""
    return create_unified_cache(UnifiedCacheMode.ENTERPRISE, **overrides)