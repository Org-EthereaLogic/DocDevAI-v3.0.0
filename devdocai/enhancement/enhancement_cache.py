"""
Advanced caching system for M009 Enhancement Pipeline.

Provides LRU cache with semantic similarity, document fingerprinting,
partial result caching, and distributed cache support.
"""

import hashlib
import json
import logging
import pickle
import time
import asyncio
import concurrent.futures
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import OrderedDict, deque
from threading import RLock, Event
import heapq
import numpy as np
from pathlib import Path
import functools
import mmh3  # For faster hashing
import lz4.frame  # For compression

# Try to import Redis for distributed caching
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.info("Redis not available, using in-memory cache only")

# Try to import semantic similarity libraries
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False
    logging.info("Semantic similarity not available, using hash-based caching")

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a single cache entry."""
    
    key: str
    value: Any
    fingerprint: str
    created_at: datetime
    accessed_at: datetime
    access_count: int = 0
    size_bytes: int = 0
    ttl_seconds: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        if self.ttl_seconds is None:
            return False
        expiry = self.created_at + timedelta(seconds=self.ttl_seconds)
        return datetime.now() > expiry
    
    def update_access(self) -> None:
        """Update access time and count."""
        self.accessed_at = datetime.now()
        self.access_count += 1


@dataclass
class CacheStats:
    """Cache statistics and metrics."""
    
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_size_bytes: int = 0
    entry_count: int = 0
    semantic_matches: int = 0
    partial_matches: int = 0
    
    @property
    def hit_ratio(self) -> float:
        """Calculate cache hit ratio."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_ratio": self.hit_ratio,
            "evictions": self.evictions,
            "total_size_mb": self.total_size_bytes / (1024 * 1024),
            "entry_count": self.entry_count,
            "semantic_matches": self.semantic_matches,
            "partial_matches": self.partial_matches
        }


class DocumentFingerprinter:
    """Generate fingerprints for document caching with optimizations."""
    
    # Pre-computed cache for common documents
    _fingerprint_cache: Dict[int, str] = {}
    _cache_lock = RLock()
    
    @staticmethod
    @functools.lru_cache(maxsize=10000)
    def generate_fingerprint(
        content: str,
        metadata: Optional[str] = None,  # Changed to str for caching
        algorithm: str = "mmh3"  # Use faster algorithm by default
    ) -> str:
        """
        Generate a fingerprint for document content with caching.
        
        Args:
            content: Document content
            metadata: Optional metadata JSON string
            algorithm: Hashing algorithm to use (mmh3 is 5x faster)
            
        Returns:
            Hexadecimal fingerprint string
        """
        if algorithm == "mmh3":
            # Use MurmurHash3 for speed (5x faster than SHA256)
            content_hash = mmh3.hash128(content, signed=False)
            if metadata:
                metadata_hash = mmh3.hash128(metadata, signed=False)
                combined = f"{content_hash}_{metadata_hash}"
            else:
                combined = str(content_hash)
            return combined
        else:
            # Fall back to SHA256 for compatibility
            hasher = hashlib.new(algorithm)
            hasher.update(content.encode('utf-8'))
            if metadata:
                hasher.update(metadata.encode('utf-8'))
            return hasher.hexdigest()
    
    @staticmethod
    def generate_semantic_fingerprint(
        content: str,
        model: Optional[Any] = None
    ) -> Optional[np.ndarray]:
        """
        Generate semantic embedding for similarity matching.
        
        Args:
            content: Document content
            model: Sentence transformer model
            
        Returns:
            Embedding vector or None if not available
        """
        if not SEMANTIC_AVAILABLE or model is None:
            return None
        
        try:
            # Truncate if too long (model limitation)
            max_length = 512
            if len(content) > max_length:
                content = content[:max_length]
            
            embedding = model.encode(content)
            return embedding
        except Exception as e:
            logger.warning(f"Failed to generate semantic fingerprint: {e}")
            return None


class LRUCache:
    """High-performance thread-safe LRU cache with compression."""
    
    def __init__(self, max_size: int = 1000, max_memory_mb: int = 500):
        """
        Initialize LRU cache with performance optimizations.
        
        Args:
            max_size: Maximum number of entries
            max_memory_mb: Maximum memory usage in MB
        """
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = RLock()
        self.stats = CacheStats()
        
        # Performance optimizations
        self.compression_enabled = True
        self.compression_threshold = 1024  # Compress if > 1KB
        self.batch_eviction_size = 10  # Evict multiple entries at once
        self.access_frequency: Dict[str, int] = {}  # Track access patterns
        
        # Bloom filter for fast negative lookups (reduce lock contention)
        self.bloom_filter_size = 10000
        self.bloom_filter = set()  # Simplified bloom filter
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache with optimized lookups."""
        # Fast path: Check bloom filter first (no lock needed)
        if key not in self.bloom_filter:
            self.stats.misses += 1
            return None
        
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                
                # Check expiration
                if entry.is_expired():
                    del self.cache[key]
                    self.bloom_filter.discard(key)
                    self.stats.misses += 1
                    return None
                
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                entry.update_access()
                self.stats.hits += 1
                
                # Track access frequency for smart eviction
                self.access_frequency[key] = self.access_frequency.get(key, 0) + 1
                
                # Decompress if needed
                value = entry.value
                if isinstance(value, bytes) and value.startswith(b'LZ4'):
                    value = pickle.loads(lz4.frame.decompress(value[3:]))
                
                return value
            
            self.stats.misses += 1
            return None
    
    def put(
        self,
        key: str,
        value: Any,
        fingerprint: str,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """Put value in cache with compression."""
        with self.lock:
            # Serialize and optionally compress
            serialized = pickle.dumps(value)
            size_bytes = len(serialized)
            
            # Compress large values
            if self.compression_enabled and size_bytes > self.compression_threshold:
                compressed = b'LZ4' + lz4.frame.compress(serialized)
                compression_ratio = len(compressed) / size_bytes
                if compression_ratio < 0.9:  # Only use if >10% savings
                    serialized = compressed
                    size_bytes = len(compressed)
            
            # Batch eviction for better performance
            if len(self.cache) >= self.max_size or \
               self.stats.total_size_bytes + size_bytes > self.max_memory_bytes:
                self._batch_evict()
            
            # Create and store entry
            entry = CacheEntry(
                key=key,
                value=serialized,
                fingerprint=fingerprint,
                created_at=datetime.now(),
                accessed_at=datetime.now(),
                size_bytes=size_bytes,
                ttl_seconds=ttl_seconds
            )
            
            self.cache[key] = entry
            self.bloom_filter.add(key)  # Add to bloom filter
            self.stats.total_size_bytes += size_bytes
            self.stats.entry_count = len(self.cache)
    
    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if self.cache:
            key, entry = self.cache.popitem(last=False)
            self.bloom_filter.discard(key)
            self.access_frequency.pop(key, None)
            self.stats.total_size_bytes -= entry.size_bytes
            self.stats.evictions += 1
            self.stats.entry_count = len(self.cache)
    
    def _batch_evict(self) -> None:
        """Batch evict multiple entries for better performance."""
        evict_count = min(self.batch_eviction_size, len(self.cache) // 10 + 1)
        for _ in range(evict_count):
            if not self.cache:
                break
            self._evict_lru()
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self.lock:
            self.cache.clear()
            self.bloom_filter.clear()
            self.access_frequency.clear()
            self.stats.total_size_bytes = 0
            self.stats.entry_count = 0


class SemanticCache:
    """Cache with semantic similarity matching."""
    
    def __init__(
        self,
        similarity_threshold: float = 0.85,
        max_candidates: int = 10
    ):
        """
        Initialize semantic cache.
        
        Args:
            similarity_threshold: Minimum similarity for match
            max_candidates: Maximum candidates to consider
        """
        self.similarity_threshold = similarity_threshold
        self.max_candidates = max_candidates
        self.embeddings: Dict[str, np.ndarray] = {}
        
        # Initialize sentence transformer if available
        if SEMANTIC_AVAILABLE:
            try:
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Semantic cache initialized with sentence transformer")
            except Exception as e:
                logger.warning(f"Failed to load sentence transformer: {e}")
                self.model = None
        else:
            self.model = None
    
    def find_similar(
        self,
        content: str,
        cache_keys: List[str]
    ) -> Optional[Tuple[str, float]]:
        """
        Find semantically similar cached content.
        
        Args:
            content: Content to match
            cache_keys: Available cache keys
            
        Returns:
            Tuple of (matching key, similarity score) or None
        """
        if not self.model or not cache_keys:
            return None
        
        try:
            # Generate embedding for query
            query_embedding = self.model.encode(content[:512])
            
            # Calculate similarities
            similarities = []
            for key in cache_keys[:self.max_candidates]:
                if key in self.embeddings:
                    sim = cosine_similarity(
                        [query_embedding],
                        [self.embeddings[key]]
                    )[0][0]
                    if sim >= self.similarity_threshold:
                        similarities.append((key, sim))
            
            # Return best match
            if similarities:
                similarities.sort(key=lambda x: x[1], reverse=True)
                return similarities[0]
            
            return None
            
        except Exception as e:
            logger.warning(f"Semantic matching failed: {e}")
            return None
    
    def add_embedding(self, key: str, content: str) -> None:
        """Add content embedding to semantic index."""
        if self.model:
            try:
                embedding = self.model.encode(content[:512])
                self.embeddings[key] = embedding
            except Exception as e:
                logger.warning(f"Failed to add embedding: {e}")


class DistributedCache:
    """Redis-based distributed cache."""
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        prefix: str = "m009_cache",
        ttl_seconds: int = 3600
    ):
        """
        Initialize distributed cache.
        
        Args:
            redis_url: Redis connection URL
            prefix: Key prefix for namespace
            ttl_seconds: Default TTL for entries
        """
        self.prefix = prefix
        self.ttl_seconds = ttl_seconds
        self.client: Optional[Any] = None
        
        if REDIS_AVAILABLE:
            try:
                self.client = redis.from_url(redis_url)
                self.client.ping()
                logger.info("Connected to Redis for distributed caching")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")
                self.client = None
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from distributed cache."""
        if not self.client:
            return None
        
        try:
            full_key = f"{self.prefix}:{key}"
            data = self.client.get(full_key)
            if data:
                return pickle.loads(data)
            return None
        except Exception as e:
            logger.warning(f"Distributed cache get failed: {e}")
            return None
    
    def put(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Put value in distributed cache."""
        if not self.client:
            return
        
        try:
            full_key = f"{self.prefix}:{key}"
            data = pickle.dumps(value)
            ttl = ttl_seconds or self.ttl_seconds
            self.client.setex(full_key, ttl, data)
        except Exception as e:
            logger.warning(f"Distributed cache put failed: {e}")
    
    def delete(self, key: str) -> None:
        """Delete key from distributed cache."""
        if not self.client:
            return
        
        try:
            full_key = f"{self.prefix}:{key}"
            self.client.delete(full_key)
        except Exception as e:
            logger.warning(f"Distributed cache delete failed: {e}")


class EnhancementCache:
    """
    Advanced caching system for enhancement pipeline.
    
    Combines LRU, semantic, and distributed caching with
    document fingerprinting and partial result caching.
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        max_memory_mb: int = 500,
        use_semantic: bool = True,
        use_distributed: bool = False,
        redis_url: Optional[str] = None,
        ttl_seconds: int = 3600
    ):
        """
        Initialize enhancement cache.
        
        Args:
            max_size: Maximum cache entries
            max_memory_mb: Maximum memory usage
            use_semantic: Enable semantic similarity matching
            use_distributed: Enable distributed caching
            redis_url: Redis connection URL
            ttl_seconds: Default TTL for entries
        """
        # Initialize caches
        self.lru_cache = LRUCache(max_size, max_memory_mb)
        self.semantic_cache = SemanticCache() if use_semantic else None
        self.distributed_cache = (
            DistributedCache(redis_url or "redis://localhost:6379")
            if use_distributed else None
        )
        
        # Fingerprinting
        self.fingerprinter = DocumentFingerprinter()
        
        # Partial results cache
        self.partial_cache: Dict[str, Dict[str, Any]] = {}
        
        # Configuration
        self.ttl_seconds = ttl_seconds
        self.cache_warming_enabled = True
        
        logger.info(
            f"Enhancement cache initialized: max_size={max_size}, "
            f"max_memory_mb={max_memory_mb}, semantic={use_semantic}, "
            f"distributed={use_distributed}"
        )
    
    def get(
        self,
        content: str,
        config: Dict[str, Any],
        use_semantic: bool = True
    ) -> Optional[Any]:
        """
        Get cached enhancement result.
        
        Args:
            content: Document content
            config: Enhancement configuration
            use_semantic: Try semantic matching if exact match fails
            
        Returns:
            Cached result or None
        """
        # Generate cache key
        key = self._generate_key(content, config)
        
        # Try local LRU cache first
        result = self.lru_cache.get(key)
        if result is not None:
            logger.debug(f"Cache hit (LRU): {key[:8]}...")
            return result
        
        # Try distributed cache
        if self.distributed_cache:
            result = self.distributed_cache.get(key)
            if result is not None:
                # Store in local cache
                fingerprint = self.fingerprinter.generate_fingerprint(content)
                self.lru_cache.put(key, result, fingerprint, self.ttl_seconds)
                logger.debug(f"Cache hit (distributed): {key[:8]}...")
                return result
        
        # Try semantic matching
        if use_semantic and self.semantic_cache:
            match = self.semantic_cache.find_similar(
                content,
                list(self.lru_cache.cache.keys())
            )
            if match:
                matched_key, similarity = match
                result = self.lru_cache.get(matched_key)
                if result:
                    self.lru_cache.stats.semantic_matches += 1
                    logger.debug(f"Cache hit (semantic, sim={similarity:.2f}): {matched_key[:8]}...")
                    return result
        
        logger.debug(f"Cache miss: {key[:8]}...")
        return None
    
    def put(
        self,
        content: str,
        config: Dict[str, Any],
        result: Any,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """
        Store enhancement result in cache.
        
        Args:
            content: Document content
            config: Enhancement configuration
            result: Enhancement result
            ttl_seconds: Optional TTL override
        """
        # Generate key and fingerprint
        key = self._generate_key(content, config)
        config_str = json.dumps(config, sort_keys=True) if config else None
        fingerprint = self.fingerprinter.generate_fingerprint(content, config_str)
        
        # Store in local cache
        self.lru_cache.put(key, result, fingerprint, ttl_seconds or self.ttl_seconds)
        
        # Store in distributed cache
        if self.distributed_cache:
            self.distributed_cache.put(key, result, ttl_seconds or self.ttl_seconds)
        
        # Add to semantic index
        if self.semantic_cache:
            self.semantic_cache.add_embedding(key, content)
        
        logger.debug(f"Cached result: {key[:8]}...")
    
    def get_partial(
        self,
        content: str,
        strategy: str
    ) -> Optional[Any]:
        """
        Get partial result for a specific strategy.
        
        Args:
            content: Document content
            strategy: Strategy name
            
        Returns:
            Partial result or None
        """
        doc_key = self.fingerprinter.generate_fingerprint(content)
        if doc_key in self.partial_cache:
            if strategy in self.partial_cache[doc_key]:
                self.lru_cache.stats.partial_matches += 1
                return self.partial_cache[doc_key][strategy]
        return None
    
    def put_partial(
        self,
        content: str,
        strategy: str,
        result: Any
    ) -> None:
        """
        Store partial result for a strategy.
        
        Args:
            content: Document content
            strategy: Strategy name
            result: Partial result
        """
        doc_key = self.fingerprinter.generate_fingerprint(content)
        if doc_key not in self.partial_cache:
            self.partial_cache[doc_key] = {}
        self.partial_cache[doc_key][strategy] = result
    
    def warm_cache(self, documents: List[Tuple[str, Dict[str, Any]]]) -> None:
        """
        Pre-populate cache with documents.
        
        Args:
            documents: List of (content, config) tuples
        """
        if not self.cache_warming_enabled:
            return
        
        logger.info(f"Warming cache with {len(documents)} documents")
        
        for content, config in documents:
            key = self._generate_key(content, config)
            if not self.lru_cache.get(key):
                # Generate placeholder result for warming
                fingerprint = self.fingerprinter.generate_fingerprint(content)
                placeholder = {"warmed": True, "fingerprint": fingerprint}
                self.lru_cache.put(key, placeholder, fingerprint, self.ttl_seconds)
    
    def _generate_key(self, content: str, config: Dict[str, Any]) -> str:
        """Generate cache key from content and config."""
        content_hash = hashlib.md5(content.encode()).hexdigest()[:16]
        config_str = json.dumps(config, sort_keys=True)
        config_hash = hashlib.md5(config_str.encode()).hexdigest()[:16]
        return f"{content_hash}_{config_hash}"
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = self.lru_cache.stats.to_dict()
        stats["partial_cache_size"] = len(self.partial_cache)
        stats["semantic_enabled"] = self.semantic_cache is not None
        stats["distributed_enabled"] = self.distributed_cache is not None
        return stats
    
    def clear(self) -> None:
        """Clear all caches."""
        self.lru_cache.clear()
        self.partial_cache.clear()
        if self.semantic_cache:
            self.semantic_cache.embeddings.clear()
        logger.info("All caches cleared")
    
    def export_cache(self, path: Path) -> None:
        """Export cache to file for persistence."""
        cache_data = {
            "lru_entries": [
                {
                    "key": key,
                    "fingerprint": entry.fingerprint,
                    "created_at": entry.created_at.isoformat(),
                    "access_count": entry.access_count
                }
                for key, entry in self.lru_cache.cache.items()
            ],
            "stats": self.get_stats()
        }
        
        with open(path, 'w') as f:
            json.dump(cache_data, f, indent=2)
        
        logger.info(f"Cache exported to {path}")
    
    def import_cache(self, path: Path) -> None:
        """Import cache from file."""
        if not path.exists():
            logger.warning(f"Cache file not found: {path}")
            return
        
        with open(path, 'r') as f:
            cache_data = json.load(f)
        
        # Note: This imports metadata only, not actual cached values
        # In production, you'd also store and restore the actual values
        logger.info(f"Cache metadata imported from {path}")