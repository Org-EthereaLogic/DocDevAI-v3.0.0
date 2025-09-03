"""
Smart caching system for AI Document Generator performance optimization.

Implements semantic similarity matching, LRU caching, and document fragment caching
to achieve 30%+ cache hit rates and significant performance improvements.
"""

import hashlib
import json
import logging
import time
from typing import Dict, Any, Optional, Tuple, List
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pickle
from pathlib import Path
import asyncio
from functools import lru_cache

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a cached response."""
    key: str
    prompt_hash: str
    response: Dict[str, Any]
    prompt_embedding: Optional[np.ndarray] = None
    timestamp: float = field(default_factory=time.time)
    hit_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self, ttl_seconds: int = 3600) -> bool:
        """Check if cache entry has expired."""
        return time.time() - self.timestamp > ttl_seconds
    
    def update_access(self):
        """Update access statistics."""
        self.hit_count += 1
        self.last_accessed = time.time()


class SemanticCache:
    """
    Advanced caching system with semantic similarity matching.
    
    Features:
    - Semantic similarity matching for fuzzy cache hits
    - LRU eviction policy
    - Document fragment caching
    - Template compilation caching
    - Performance metrics tracking
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        similarity_threshold: float = 0.85,
        ttl_seconds: int = 3600,
        enable_persistence: bool = True,
        cache_dir: Optional[Path] = None
    ):
        """
        Initialize semantic cache.
        
        Args:
            max_size: Maximum cache entries
            similarity_threshold: Minimum similarity for cache hit (0-1)
            ttl_seconds: Time-to-live for cache entries
            enable_persistence: Whether to persist cache to disk
            cache_dir: Directory for cache persistence
        """
        self.max_size = max_size
        self.similarity_threshold = similarity_threshold
        self.ttl_seconds = ttl_seconds
        self.enable_persistence = enable_persistence
        
        # Cache storage
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.prompt_embeddings: Dict[str, np.ndarray] = {}
        
        # Vectorizer for semantic similarity
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.is_fitted = False
        
        # Cache statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "semantic_hits": 0,
            "evictions": 0,
            "total_requests": 0
        }
        
        # Persistence
        if enable_persistence:
            self.cache_dir = cache_dir or Path.home() / ".devdocai" / "cache"
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.cache_file = self.cache_dir / "semantic_cache.pkl"
            self._load_cache()
        
        logger.info(f"Initialized SemanticCache with max_size={max_size}, threshold={similarity_threshold}")
    
    def _compute_hash(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Compute hash for exact matching."""
        content = prompt
        if context:
            content += json.dumps(context, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _compute_embedding(self, text: str) -> Optional[np.ndarray]:
        """Compute text embedding for semantic similarity."""
        try:
            if not self.is_fitted:
                # Fit on first use with current prompt
                self.vectorizer.fit([text])
                self.is_fitted = True
                return self.vectorizer.transform([text]).toarray()[0]
            else:
                # Transform using fitted vectorizer
                return self.vectorizer.transform([text]).toarray()[0]
        except Exception as e:
            logger.warning(f"Failed to compute embedding: {e}")
            return None
    
    def _find_semantic_match(
        self,
        prompt: str,
        embedding: Optional[np.ndarray] = None
    ) -> Optional[Tuple[str, float]]:
        """
        Find semantically similar cached entry.
        
        Returns:
            Tuple of (cache_key, similarity_score) or None
        """
        if not embedding or not self.prompt_embeddings:
            return None
        
        try:
            # Compute similarities
            embeddings_matrix = np.array(list(self.prompt_embeddings.values()))
            similarities = cosine_similarity([embedding], embeddings_matrix)[0]
            
            # Find best match above threshold
            max_idx = np.argmax(similarities)
            max_similarity = similarities[max_idx]
            
            if max_similarity >= self.similarity_threshold:
                keys = list(self.prompt_embeddings.keys())
                return keys[max_idx], max_similarity
                
        except Exception as e:
            logger.warning(f"Semantic matching failed: {e}")
        
        return None
    
    def _evict_lru(self):
        """Evict least recently used entry."""
        if self.cache:
            # Remove oldest entry (first in OrderedDict)
            evicted_key, evicted_entry = self.cache.popitem(last=False)
            if evicted_key in self.prompt_embeddings:
                del self.prompt_embeddings[evicted_key]
            self.stats["evictions"] += 1
            logger.debug(f"Evicted cache entry: {evicted_key[:8]}...")
    
    async def get(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        use_semantic: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached response.
        
        Args:
            prompt: The prompt to look up
            context: Additional context
            use_semantic: Whether to use semantic similarity matching
            
        Returns:
            Cached response or None
        """
        self.stats["total_requests"] += 1
        
        # Try exact match first
        prompt_hash = self._compute_hash(prompt, context)
        
        if prompt_hash in self.cache:
            entry = self.cache[prompt_hash]
            
            # Check expiration
            if not entry.is_expired(self.ttl_seconds):
                entry.update_access()
                # Move to end (most recent)
                self.cache.move_to_end(prompt_hash)
                self.stats["hits"] += 1
                
                logger.info(f"Cache hit (exact): {prompt_hash[:8]}... (hits: {entry.hit_count})")
                return entry.response
            else:
                # Remove expired entry
                del self.cache[prompt_hash]
                if prompt_hash in self.prompt_embeddings:
                    del self.prompt_embeddings[prompt_hash]
        
        # Try semantic matching if enabled
        if use_semantic:
            embedding = self._compute_embedding(prompt)
            match = self._find_semantic_match(prompt, embedding)
            
            if match:
                match_key, similarity = match
                if match_key in self.cache:
                    entry = self.cache[match_key]
                    
                    if not entry.is_expired(self.ttl_seconds):
                        entry.update_access()
                        self.cache.move_to_end(match_key)
                        self.stats["semantic_hits"] += 1
                        
                        logger.info(
                            f"Cache hit (semantic): similarity={similarity:.3f}, "
                            f"key={match_key[:8]}... (hits: {entry.hit_count})"
                        )
                        return entry.response
        
        self.stats["misses"] += 1
        logger.debug(f"Cache miss for prompt hash: {prompt_hash[:8]}...")
        return None
    
    async def set(
        self,
        prompt: str,
        response: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Store response in cache.
        
        Args:
            prompt: The prompt that generated the response
            response: The response to cache
            context: Additional context
            metadata: Optional metadata to store with entry
        """
        # Compute identifiers
        prompt_hash = self._compute_hash(prompt, context)
        embedding = self._compute_embedding(prompt)
        
        # Check size limit
        if len(self.cache) >= self.max_size:
            self._evict_lru()
        
        # Create and store entry
        entry = CacheEntry(
            key=prompt_hash,
            prompt_hash=prompt_hash,
            response=response,
            prompt_embedding=embedding,
            metadata=metadata or {}
        )
        
        self.cache[prompt_hash] = entry
        if embedding is not None:
            self.prompt_embeddings[prompt_hash] = embedding
        
        # Move to end (most recent)
        self.cache.move_to_end(prompt_hash)
        
        logger.debug(f"Cached response: {prompt_hash[:8]}... (cache size: {len(self.cache)})")
        
        # Persist if enabled
        if self.enable_persistence:
            await self._save_cache_async()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total = self.stats["total_requests"]
        if total > 0:
            hit_rate = (self.stats["hits"] + self.stats["semantic_hits"]) / total
            exact_hit_rate = self.stats["hits"] / total
            semantic_hit_rate = self.stats["semantic_hits"] / total
        else:
            hit_rate = exact_hit_rate = semantic_hit_rate = 0
        
        return {
            **self.stats,
            "cache_size": len(self.cache),
            "hit_rate": hit_rate,
            "exact_hit_rate": exact_hit_rate,
            "semantic_hit_rate": semantic_hit_rate,
            "avg_hit_count": (
                sum(e.hit_count for e in self.cache.values()) / len(self.cache)
                if self.cache else 0
            )
        }
    
    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()
        self.prompt_embeddings.clear()
        logger.info("Cache cleared")
    
    async def _save_cache_async(self):
        """Save cache to disk asynchronously."""
        if not self.enable_persistence:
            return
        
        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._save_cache)
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")
    
    def _save_cache(self):
        """Save cache to disk."""
        if not self.enable_persistence:
            return
        
        try:
            cache_data = {
                "cache": dict(self.cache),
                "embeddings": self.prompt_embeddings,
                "stats": self.stats,
                "is_fitted": self.is_fitted
            }
            
            with open(self.cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
            
            logger.debug(f"Saved cache to {self.cache_file}")
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")
    
    def _load_cache(self):
        """Load cache from disk."""
        if not self.enable_persistence or not self.cache_file.exists():
            return
        
        try:
            with open(self.cache_file, 'rb') as f:
                cache_data = pickle.load(f)
            
            self.cache = OrderedDict(cache_data.get("cache", {}))
            self.prompt_embeddings = cache_data.get("embeddings", {})
            self.stats = cache_data.get("stats", self.stats)
            self.is_fitted = cache_data.get("is_fitted", False)
            
            # Remove expired entries
            expired_keys = [
                key for key, entry in self.cache.items()
                if entry.is_expired(self.ttl_seconds)
            ]
            for key in expired_keys:
                del self.cache[key]
                if key in self.prompt_embeddings:
                    del self.prompt_embeddings[key]
            
            logger.info(f"Loaded cache from {self.cache_file} ({len(self.cache)} entries)")
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")


class FragmentCache:
    """
    Cache for document fragments and reusable components.
    
    Caches common document sections like headers, footers, and standard paragraphs
    to avoid regenerating identical content.
    """
    
    def __init__(self, max_fragments: int = 500):
        """
        Initialize fragment cache.
        
        Args:
            max_fragments: Maximum number of fragments to cache
        """
        self.max_fragments = max_fragments
        self.fragments: OrderedDict[str, str] = OrderedDict()
        self.fragment_stats: Dict[str, int] = {}
        
        logger.info(f"Initialized FragmentCache with max_fragments={max_fragments}")
    
    @lru_cache(maxsize=128)
    def _compute_fragment_key(self, fragment_type: str, context: str) -> str:
        """Compute cache key for fragment."""
        content = f"{fragment_type}:{context}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, fragment_type: str, context: str) -> Optional[str]:
        """Get cached fragment."""
        key = self._compute_fragment_key(fragment_type, context)
        
        if key in self.fragments:
            # Update stats and move to end
            self.fragment_stats[key] = self.fragment_stats.get(key, 0) + 1
            self.fragments.move_to_end(key)
            return self.fragments[key]
        
        return None
    
    def set(self, fragment_type: str, context: str, content: str):
        """Store fragment in cache."""
        key = self._compute_fragment_key(fragment_type, context)
        
        # Check size limit
        if len(self.fragments) >= self.max_fragments:
            # Remove least recently used
            self.fragments.popitem(last=False)
        
        self.fragments[key] = content
        self.fragments.move_to_end(key)
        self.fragment_stats[key] = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get fragment cache statistics."""
        return {
            "fragment_count": len(self.fragments),
            "total_hits": sum(self.fragment_stats.values()),
            "most_used": (
                max(self.fragment_stats.items(), key=lambda x: x[1])
                if self.fragment_stats else None
            )
        }


class CacheManager:
    """
    Unified cache management for AI Document Generator.
    
    Combines semantic caching, fragment caching, and template caching
    for comprehensive performance optimization.
    """
    
    def __init__(
        self,
        enable_semantic: bool = True,
        enable_fragments: bool = True,
        enable_persistence: bool = True,
        cache_dir: Optional[Path] = None
    ):
        """
        Initialize cache manager.
        
        Args:
            enable_semantic: Enable semantic similarity caching
            enable_fragments: Enable fragment caching
            enable_persistence: Enable disk persistence
            cache_dir: Cache directory
        """
        self.enable_semantic = enable_semantic
        self.enable_fragments = enable_fragments
        
        # Initialize caches
        self.semantic_cache = SemanticCache(
            enable_persistence=enable_persistence,
            cache_dir=cache_dir
        ) if enable_semantic else None
        
        self.fragment_cache = FragmentCache() if enable_fragments else None
        
        # Template compilation cache
        self.template_cache: Dict[str, Any] = {}
        
        logger.info(
            f"Initialized CacheManager (semantic={enable_semantic}, "
            f"fragments={enable_fragments}, persistence={enable_persistence})"
        )
    
    async def get_response(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Get cached LLM response."""
        if self.semantic_cache:
            return await self.semantic_cache.get(prompt, context)
        return None
    
    async def cache_response(
        self,
        prompt: str,
        response: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Cache LLM response."""
        if self.semantic_cache:
            await self.semantic_cache.set(prompt, response, context, metadata)
    
    def get_fragment(self, fragment_type: str, context: str) -> Optional[str]:
        """Get cached document fragment."""
        if self.fragment_cache:
            return self.fragment_cache.get(fragment_type, context)
        return None
    
    def cache_fragment(self, fragment_type: str, context: str, content: str):
        """Cache document fragment."""
        if self.fragment_cache:
            self.fragment_cache.set(fragment_type, context, content)
    
    def get_compiled_template(self, template_name: str) -> Optional[Any]:
        """Get cached compiled template."""
        return self.template_cache.get(template_name)
    
    def cache_compiled_template(self, template_name: str, compiled_template: Any):
        """Cache compiled template."""
        self.template_cache[template_name] = compiled_template
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        stats = {
            "template_cache_size": len(self.template_cache)
        }
        
        if self.semantic_cache:
            stats["semantic"] = self.semantic_cache.get_stats()
        
        if self.fragment_cache:
            stats["fragments"] = self.fragment_cache.get_stats()
        
        return stats
    
    def clear_all(self):
        """Clear all caches."""
        if self.semantic_cache:
            self.semantic_cache.clear()
        if self.fragment_cache:
            self.fragment_cache.fragments.clear()
        self.template_cache.clear()
        logger.info("All caches cleared")


# Singleton instance for global access
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get or create singleton cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager