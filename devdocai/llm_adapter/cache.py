"""
M008: Advanced Caching System for LLM Adapter.

Implements intelligent caching with:
- LRU cache for exact matches
- Semantic similarity matching (mock implementation without API keys)
- TTL-based expiration
- Provider-specific caching
- Cache statistics and monitoring
"""

import asyncio
import hashlib
import json
import time
import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
import numpy as np

from .providers.base import LLMRequest, LLMResponse

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Individual cache entry with metadata."""
    response: LLMResponse
    request_hash: str
    prompt_embedding: Optional[np.ndarray]  # For semantic matching
    timestamp: float
    ttl_seconds: int
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    provider: Optional[str] = None
    model: Optional[str] = None
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return time.time() - self.timestamp > self.ttl_seconds
    
    def update_access(self) -> None:
        """Update access statistics."""
        self.access_count += 1
        self.last_accessed = time.time()


@dataclass
class CacheStats:
    """Cache performance statistics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    semantic_matches: int = 0
    exact_matches: int = 0
    expired_evictions: int = 0
    size_evictions: int = 0
    total_response_time_saved_ms: float = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    @property
    def avg_time_saved_ms(self) -> float:
        """Average response time saved per hit."""
        return self.total_response_time_saved_ms / self.hits if self.hits > 0 else 0.0


class LRUCache:
    """Thread-safe LRU cache implementation."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[CacheEntry]:
        """Get item from cache and move to end (most recently used)."""
        async with self._lock:
            if key in self.cache:
                entry = self.cache.pop(key)
                if not entry.is_expired():
                    self.cache[key] = entry  # Move to end
                    entry.update_access()
                    return entry
                # Entry expired, don't re-add
                return None
            return None
    
    async def put(self, key: str, entry: CacheEntry) -> int:
        """Put item in cache, return number of evicted items."""
        async with self._lock:
            evicted = 0
            
            # Remove expired entries first
            expired_keys = [
                k for k, v in self.cache.items() 
                if v.is_expired()
            ]
            for k in expired_keys:
                del self.cache[k]
                evicted += 1
            
            # Check if we need to evict for size
            if len(self.cache) >= self.max_size:
                # Remove least recently used
                self.cache.popitem(last=False)
                evicted += 1
            
            self.cache[key] = entry
            return evicted
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self.cache.clear()
    
    async def size(self) -> int:
        """Get current cache size."""
        async with self._lock:
            return len(self.cache)


class ResponseCache:
    """
    Advanced caching system for LLM responses.
    
    Features:
    - Exact match caching with LRU eviction
    - Semantic similarity matching (mock without embeddings API)
    - Provider-specific caching
    - TTL-based expiration
    - Cache warming and preloading
    - Performance statistics
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        default_ttl_seconds: int = 3600,
        similarity_threshold: float = 0.95,
        enable_semantic_matching: bool = True
    ):
        """
        Initialize response cache.
        
        Args:
            max_size: Maximum number of cache entries
            default_ttl_seconds: Default TTL for cache entries
            similarity_threshold: Threshold for semantic similarity matching
            enable_semantic_matching: Enable semantic similarity matching
        """
        self.max_size = max_size
        self.default_ttl = default_ttl_seconds
        self.similarity_threshold = similarity_threshold
        self.enable_semantic = enable_semantic_matching
        
        # Main cache storage
        self.cache = LRUCache(max_size)
        
        # Index for semantic search (mock implementation)
        self.embedding_index: Dict[str, np.ndarray] = {}
        
        # Provider-specific caches
        self.provider_caches: Dict[str, LRUCache] = defaultdict(
            lambda: LRUCache(max_size // 4)
        )
        
        # Cache statistics
        self.stats = CacheStats()
        
        # Configuration for different content types
        self.ttl_config = {
            "documentation": 7200,    # 2 hours
            "code_generation": 3600,   # 1 hour
            "translation": 10800,      # 3 hours
            "summary": 1800,           # 30 minutes
            "default": default_ttl_seconds
        }
        
        self.logger = logging.getLogger(f"{__name__}.ResponseCache")
    
    def _generate_cache_key(self, request: LLMRequest) -> str:
        """Generate deterministic cache key from request."""
        # Create a stable hash from request parameters
        key_data = {
            "messages": request.messages,
            "model": request.model,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "top_p": request.top_p,
            "frequency_penalty": request.frequency_penalty,
            "presence_penalty": request.presence_penalty,
            "system_prompt": request.system_prompt,
            "tools": request.tools,
            "response_format": request.response_format
        }
        
        # Sort keys for deterministic hashing
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def _mock_generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate mock embedding for text (without actual embedding API).
        
        In production, this would call an embedding API like OpenAI's text-embedding-3-small.
        For now, we'll create a deterministic mock embedding based on text features.
        """
        # Mock embedding based on text features
        features = []
        
        # Length feature
        features.append(len(text) / 1000.0)
        
        # Character distribution (simplified)
        char_counts = defaultdict(int)
        for char in text.lower():
            if char.isalpha():
                char_counts[char] += 1
        
        # Add normalized character frequencies for a-z
        for char in 'abcdefghijklmnopqrstuvwxyz':
            features.append(char_counts[char] / (len(text) + 1))
        
        # Word count feature
        features.append(len(text.split()) / 100.0)
        
        # Average word length
        words = text.split()
        avg_word_len = sum(len(w) for w in words) / (len(words) + 1)
        features.append(avg_word_len / 10.0)
        
        # Pad to fixed size (e.g., 384 dimensions like small embeddings)
        while len(features) < 384:
            # Add deterministic padding based on text hash
            hash_val = hashlib.md5(f"{text}{len(features)}".encode()).hexdigest()
            features.append(int(hash_val[:8], 16) / (2**32))
        
        return np.array(features[:384], dtype=np.float32)
    
    def _calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine similarity between two embeddings."""
        # Cosine similarity
        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    async def find_semantic_match(
        self,
        request: LLMRequest,
        provider: Optional[str] = None
    ) -> Optional[CacheEntry]:
        """
        Find semantically similar cached response.
        
        Args:
            request: The request to match
            provider: Optional provider filter
            
        Returns:
            Best matching cache entry if similarity exceeds threshold
        """
        if not self.enable_semantic:
            return None
        
        # Generate embedding for request
        prompt_text = " ".join([msg["content"] for msg in request.messages])
        query_embedding = self._mock_generate_embedding(prompt_text)
        
        # Search through cache entries
        best_match: Optional[Tuple[float, CacheEntry]] = None
        cache_size = await self.cache.size()
        
        # Check main cache
        async with self.cache._lock:
            for key, entry in self.cache.cache.items():
                if entry.is_expired():
                    continue
                
                # Filter by provider if specified
                if provider and entry.provider != provider:
                    continue
                
                # Filter by model if strict matching needed
                if entry.model != request.model:
                    continue
                
                # Calculate similarity
                if entry.prompt_embedding is not None:
                    similarity = self._calculate_similarity(
                        query_embedding, 
                        entry.prompt_embedding
                    )
                    
                    if similarity >= self.similarity_threshold:
                        if best_match is None or similarity > best_match[0]:
                            best_match = (similarity, entry)
        
        if best_match:
            self.stats.semantic_matches += 1
            self.logger.debug(
                f"Found semantic match with similarity {best_match[0]:.3f}"
            )
            best_match[1].update_access()
            return best_match[1]
        
        return None
    
    async def get(
        self,
        request: LLMRequest,
        provider: Optional[str] = None,
        use_semantic: bool = True
    ) -> Optional[LLMResponse]:
        """
        Get cached response for request.
        
        Args:
            request: The request to look up
            provider: Optional provider filter
            use_semantic: Whether to use semantic matching as fallback
            
        Returns:
            Cached response if found, None otherwise
        """
        # Generate cache key
        cache_key = self._generate_cache_key(request)
        
        # Try exact match first
        entry = await self.cache.get(cache_key)
        
        if entry:
            self.stats.hits += 1
            self.stats.exact_matches += 1
            self.stats.total_response_time_saved_ms += entry.response.response_time_ms
            self.logger.debug(f"Cache hit (exact match): {cache_key[:8]}...")
            return entry.response
        
        # Try provider-specific cache
        if provider and provider in self.provider_caches:
            entry = await self.provider_caches[provider].get(cache_key)
            if entry:
                self.stats.hits += 1
                self.stats.exact_matches += 1
                self.stats.total_response_time_saved_ms += entry.response.response_time_ms
                self.logger.debug(
                    f"Cache hit (provider-specific): {cache_key[:8]}... for {provider}"
                )
                return entry.response
        
        # Try semantic matching if enabled
        if use_semantic and self.enable_semantic:
            entry = await self.find_semantic_match(request, provider)
            if entry:
                self.stats.hits += 1
                self.stats.total_response_time_saved_ms += entry.response.response_time_ms
                self.logger.debug(f"Cache hit (semantic match): {cache_key[:8]}...")
                return entry.response
        
        # Cache miss
        self.stats.misses += 1
        self.logger.debug(f"Cache miss: {cache_key[:8]}...")
        return None
    
    async def put(
        self,
        request: LLMRequest,
        response: LLMResponse,
        ttl_seconds: Optional[int] = None,
        content_type: str = "default"
    ) -> None:
        """
        Store response in cache.
        
        Args:
            request: The request that generated this response
            response: The response to cache
            ttl_seconds: Optional TTL override
            content_type: Type of content for TTL configuration
        """
        # Generate cache key
        cache_key = self._generate_cache_key(request)
        
        # Determine TTL
        if ttl_seconds is None:
            ttl_seconds = self.ttl_config.get(content_type, self.default_ttl)
        
        # Generate embedding for semantic search
        prompt_text = " ".join([msg["content"] for msg in request.messages])
        embedding = None
        if self.enable_semantic:
            embedding = self._mock_generate_embedding(prompt_text)
            self.embedding_index[cache_key] = embedding
        
        # Create cache entry
        entry = CacheEntry(
            response=response,
            request_hash=cache_key,
            prompt_embedding=embedding,
            timestamp=time.time(),
            ttl_seconds=ttl_seconds,
            provider=response.provider,
            model=response.model
        )
        
        # Store in main cache
        evicted = await self.cache.put(cache_key, entry)
        self.stats.evictions += evicted
        if evicted > 0:
            self.stats.size_evictions += evicted
        
        # Store in provider-specific cache if applicable
        if response.provider:
            provider_evicted = await self.provider_caches[response.provider].put(
                cache_key, entry
            )
            self.stats.evictions += provider_evicted
        
        self.logger.debug(
            f"Cached response: {cache_key[:8]}... (TTL: {ttl_seconds}s, "
            f"Provider: {response.provider})"
        )
    
    async def invalidate(
        self,
        request: Optional[LLMRequest] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None
    ) -> int:
        """
        Invalidate cache entries.
        
        Args:
            request: Specific request to invalidate
            provider: Invalidate all entries for provider
            model: Invalidate all entries for model
            
        Returns:
            Number of entries invalidated
        """
        invalidated = 0
        
        if request:
            # Invalidate specific request
            cache_key = self._generate_cache_key(request)
            async with self.cache._lock:
                if cache_key in self.cache.cache:
                    del self.cache.cache[cache_key]
                    invalidated += 1
                    if cache_key in self.embedding_index:
                        del self.embedding_index[cache_key]
        
        elif provider or model:
            # Invalidate by provider or model
            async with self.cache._lock:
                keys_to_remove = []
                for key, entry in self.cache.cache.items():
                    if provider and entry.provider == provider:
                        keys_to_remove.append(key)
                    elif model and entry.model == model:
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del self.cache.cache[key]
                    if key in self.embedding_index:
                        del self.embedding_index[key]
                    invalidated += 1
        
        self.logger.info(f"Invalidated {invalidated} cache entries")
        return invalidated
    
    async def warm_cache(
        self,
        common_requests: List[Tuple[LLMRequest, LLMResponse]],
        ttl_seconds: Optional[int] = None
    ) -> None:
        """
        Pre-populate cache with common requests.
        
        Args:
            common_requests: List of (request, response) pairs
            ttl_seconds: Optional TTL for warmed entries
        """
        for request, response in common_requests:
            await self.put(request, response, ttl_seconds)
        
        self.logger.info(f"Warmed cache with {len(common_requests)} entries")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        cache_size = await self.cache.size()
        
        return {
            "size": cache_size,
            "max_size": self.max_size,
            "hit_rate": self.stats.hit_rate,
            "hits": self.stats.hits,
            "misses": self.stats.misses,
            "exact_matches": self.stats.exact_matches,
            "semantic_matches": self.stats.semantic_matches,
            "evictions": self.stats.evictions,
            "expired_evictions": self.stats.expired_evictions,
            "size_evictions": self.stats.size_evictions,
            "avg_time_saved_ms": self.stats.avg_time_saved_ms,
            "total_time_saved_ms": self.stats.total_response_time_saved_ms,
            "semantic_enabled": self.enable_semantic,
            "provider_caches": list(self.provider_caches.keys())
        }
    
    async def clear(self) -> None:
        """Clear all cache entries and reset statistics."""
        await self.cache.clear()
        for provider_cache in self.provider_caches.values():
            await provider_cache.clear()
        self.embedding_index.clear()
        self.stats = CacheStats()
        self.logger.info("Cache cleared")


class CacheManager:
    """
    Manager for multiple cache instances.
    
    Allows for different cache configurations per use case.
    """
    
    def __init__(self):
        """Initialize cache manager."""
        self.caches: Dict[str, ResponseCache] = {}
        self.default_cache: Optional[ResponseCache] = None
        self.logger = logging.getLogger(f"{__name__}.CacheManager")
    
    def create_cache(
        self,
        name: str,
        max_size: int = 1000,
        default_ttl_seconds: int = 3600,
        similarity_threshold: float = 0.95,
        enable_semantic_matching: bool = True,
        is_default: bool = False
    ) -> ResponseCache:
        """
        Create a new cache instance.
        
        Args:
            name: Cache identifier
            max_size: Maximum cache size
            default_ttl_seconds: Default TTL
            similarity_threshold: Semantic similarity threshold
            enable_semantic_matching: Enable semantic matching
            is_default: Set as default cache
            
        Returns:
            Created cache instance
        """
        cache = ResponseCache(
            max_size=max_size,
            default_ttl_seconds=default_ttl_seconds,
            similarity_threshold=similarity_threshold,
            enable_semantic_matching=enable_semantic_matching
        )
        
        self.caches[name] = cache
        
        if is_default or self.default_cache is None:
            self.default_cache = cache
        
        self.logger.info(
            f"Created cache '{name}' (size: {max_size}, TTL: {default_ttl_seconds}s, "
            f"semantic: {enable_semantic_matching})"
        )
        
        return cache
    
    def get_cache(self, name: Optional[str] = None) -> ResponseCache:
        """
        Get cache instance by name.
        
        Args:
            name: Cache name, or None for default
            
        Returns:
            Cache instance
            
        Raises:
            ValueError: If cache not found
        """
        if name is None:
            if self.default_cache is None:
                raise ValueError("No default cache configured")
            return self.default_cache
        
        if name not in self.caches:
            raise ValueError(f"Cache '{name}' not found")
        
        return self.caches[name]
    
    async def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all caches."""
        stats = {}
        for name, cache in self.caches.items():
            stats[name] = await cache.get_stats()
        return stats
    
    async def clear_all(self) -> None:
        """Clear all caches."""
        for cache in self.caches.values():
            await cache.clear()
        self.logger.info("All caches cleared")