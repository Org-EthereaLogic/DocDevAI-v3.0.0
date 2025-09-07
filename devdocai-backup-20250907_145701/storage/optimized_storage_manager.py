"""
M002 Local Storage System - Pass 2: Performance Optimized Storage Manager

Advanced performance-optimized storage manager with:
- LRU caching with memory mode adaptation
- Connection pooling and query optimization
- Batch operations for high-throughput scenarios
- FTS5 integration for fast full-text search
- Memory-efficient streaming for large datasets
"""

import time
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any, Generator, Tuple
from datetime import datetime, timezone
from functools import lru_cache
from collections import OrderedDict
import hashlib
import json

from sqlalchemy import text, and_, or_
from sqlalchemy.orm import Session

from devdocai.storage.storage_manager import LocalStorageManager, StorageError
from devdocai.storage.database import DatabaseManager
from devdocai.storage.repositories import DocumentRepository
from devdocai.storage.models import (
    Document,
    DocumentMetadata,
    DocumentSearchResult,
    StorageStats,
    ContentType,
    DocumentStatus
)
from devdocai.core.config import ConfigurationManager, MemoryMode


class CacheManager:
    """
    Advanced caching system with memory mode adaptation.
    """
    
    def __init__(self, config: ConfigurationManager):
        """Initialize cache manager with memory mode adaptation."""
        self.config = config
        self.memory_mode = config.get('memory_mode', MemoryMode.STANDARD)
        
        # Set cache sizes based on memory mode
        cache_configs = {
            MemoryMode.BASELINE: {'size': 100, 'ttl': 300},    # 100 items, 5 min TTL
            MemoryMode.STANDARD: {'size': 500, 'ttl': 600},    # 500 items, 10 min TTL  
            MemoryMode.ENHANCED: {'size': 1000, 'ttl': 1800},  # 1000 items, 30 min TTL
            MemoryMode.PERFORMANCE: {'size': 5000, 'ttl': 3600} # 5000 items, 1 hour TTL
        }
        
        cache_config = cache_configs.get(self.memory_mode, cache_configs[MemoryMode.STANDARD])
        self.max_size = cache_config['size']
        self.default_ttl = cache_config['ttl']
        
        # LRU cache implementation
        self._cache = OrderedDict()
        self._timestamps = {}
        self._lock = threading.RLock()
        
        # Cache statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache with TTL check."""
        with self._lock:
            if key in self._cache:
                # Check TTL
                if time.time() - self._timestamps[key] > self.default_ttl:
                    # Expired
                    del self._cache[key]
                    del self._timestamps[key]
                    self.misses += 1
                    return None
                    
                # Move to end (most recently used)
                self._cache.move_to_end(key)
                self.hits += 1
                return self._cache[key]
            
            self.misses += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set item in cache with optional TTL override."""
        with self._lock:
            # Evict if at capacity
            if key not in self._cache and len(self._cache) >= self.max_size:
                # Remove least recently used
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                del self._timestamps[oldest_key]
                self.evictions += 1
            
            # Add/update item
            self._cache[key] = value
            self._cache.move_to_end(key)
            self._timestamps[key] = time.time()
    
    def invalidate(self, key: str) -> None:
        """Invalidate cache entry."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                del self._timestamps[key]
    
    def clear(self) -> None:
        """Clear entire cache."""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'size': len(self._cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'evictions': self.evictions,
            'hit_rate': round(hit_rate, 2),
            'memory_mode': self.memory_mode.value
        }


class OptimizedLocalStorageManager(LocalStorageManager):
    """
    Performance-optimized storage manager with advanced caching and batch operations.
    """
    
    def __init__(
        self,
        db_path: Optional[Path] = None,
        config: Optional[ConfigurationManager] = None
    ):
        """Initialize optimized storage manager."""
        super().__init__(db_path, config)
        
        # Initialize advanced caching
        self.cache = CacheManager(self.config)
        
        # Batch operation buffers
        self._batch_buffer = []
        self._batch_lock = threading.Lock()
        self._batch_size = self._get_batch_size()
        
        # Performance monitoring
        self._query_times = []
        self._query_lock = threading.Lock()
        
        # Ensure FTS5 indexing is properly set up
        self._setup_fts_indexing()
    
    def _get_batch_size(self) -> int:
        """Get batch size based on memory mode."""
        batch_sizes = {
            MemoryMode.BASELINE: 10,
            MemoryMode.STANDARD: 50,
            MemoryMode.ENHANCED: 100,
            MemoryMode.PERFORMANCE: 500
        }
        return batch_sizes.get(
            self.config.get('memory_mode', MemoryMode.STANDARD),
            50
        )
    
    def _setup_fts_indexing(self) -> None:
        """Set up FTS5 indexing with triggers for automatic updates."""
        try:
            with self.db_manager._engine.connect() as conn:
                # Create FTS5 table if not exists
                conn.execute(text("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                        document_id UNINDEXED,
                        title,
                        content,
                        tags,
                        content=documents,
                        content_rowid=rowid
                    )
                """))
                
                # Create triggers for automatic FTS index updates
                conn.execute(text("""
                    CREATE TRIGGER IF NOT EXISTS documents_fts_insert
                    AFTER INSERT ON documents
                    BEGIN
                        INSERT INTO documents_fts(document_id, title, content, tags)
                        VALUES (new.id, new.title, new.encrypted_content, '');
                    END
                """))
                
                conn.execute(text("""
                    CREATE TRIGGER IF NOT EXISTS documents_fts_update
                    AFTER UPDATE ON documents
                    BEGIN
                        UPDATE documents_fts
                        SET title = new.title,
                            content = new.encrypted_content,
                            tags = ''
                        WHERE document_id = new.id;
                    END
                """))
                
                conn.execute(text("""
                    CREATE TRIGGER IF NOT EXISTS documents_fts_delete
                    AFTER DELETE ON documents
                    BEGIN
                        DELETE FROM documents_fts WHERE document_id = old.id;
                    END
                """))
                
                # Rebuild FTS index for existing documents
                conn.execute(text("""
                    INSERT OR REPLACE INTO documents_fts(document_id, title, content, tags)
                    SELECT id, title, encrypted_content, ''
                    FROM documents
                    WHERE is_deleted = 0
                """))
                
                conn.commit()
                
                # Mark FTS as available
                self.db_manager._has_fts = True
                
        except Exception as e:
            print(f"Warning: FTS5 setup failed, falling back to basic search: {e}")
            self.db_manager._has_fts = False
    
    def create_document(self, document: Document) -> Document:
        """
        Create document with caching.
        """
        # Track query time
        start_time = time.time()
        
        # Create document
        created_doc = super().create_document(document)
        
        # Cache the created document
        cache_key = f"doc:{created_doc.id}"
        self.cache.set(cache_key, created_doc)
        
        # Track performance
        self._track_query_time(time.time() - start_time)
        
        return created_doc
    
    def get_document(self, document_id: str) -> Optional[Document]:
        """
        Get document with caching.
        """
        # Check cache first
        cache_key = f"doc:{document_id}"
        cached_doc = self.cache.get(cache_key)
        if cached_doc is not None:
            return cached_doc
        
        # Track query time
        start_time = time.time()
        
        # Fetch from database
        document = super().get_document(document_id)
        
        # Cache if found
        if document:
            self.cache.set(cache_key, document)
        
        # Track performance
        self._track_query_time(time.time() - start_time)
        
        return document
    
    def update_document(self, document: Document) -> Optional[Document]:
        """
        Update document with cache invalidation.
        """
        # Invalidate cache
        cache_key = f"doc:{document.id}"
        self.cache.invalidate(cache_key)
        
        # Track query time
        start_time = time.time()
        
        # Update document - ensure timezone-aware datetime
        if hasattr(document, 'updated_at'):
            if document.updated_at.tzinfo is None:
                document.updated_at = document.updated_at.replace(tzinfo=timezone.utc)
        
        updated_doc = super().update_document(document)
        
        # Cache updated document
        if updated_doc:
            self.cache.set(cache_key, updated_doc)
        
        # Track performance
        self._track_query_time(time.time() - start_time)
        
        return updated_doc
    
    def delete_document(self, document_id: str, hard_delete: bool = False) -> bool:
        """
        Delete document with cache invalidation.
        """
        # Invalidate cache
        cache_key = f"doc:{document_id}"
        self.cache.invalidate(cache_key)
        
        return super().delete_document(document_id, hard_delete)
    
    def create_documents_batch(self, documents: List[Document]) -> List[Document]:
        """
        Create multiple documents in a batch for high performance.
        """
        created_docs = []
        start_time = time.time()
        
        try:
            # Use a single transaction for all documents
            with self.db_manager.get_session() as session:
                for doc in documents:
                    # Update checksums if needed
                    if doc.checksum is None:
                        doc.update_checksum()
                    
                    # Create through repository with same session
                    created_doc = self.repository.create_document_with_session(doc, session)
                    created_docs.append(created_doc)
                    
                    # Cache each document
                    cache_key = f"doc:{created_doc.id}"
                    self.cache.set(cache_key, created_doc)
                
                # Commit all at once
                session.commit()
                
                # Update FTS index in batch
                self._update_fts_batch(created_docs, session)
        
        except Exception as e:
            raise StorageError(f"Batch document creation failed: {e}")
        
        # Track performance
        elapsed = time.time() - start_time
        docs_per_sec = len(documents) / elapsed if elapsed > 0 else 0
        
        self._track_operation()
        
        return created_docs
    
    def _update_fts_batch(self, documents: List[Document], session: Session) -> None:
        """Update FTS index for batch of documents."""
        if not self.db_manager._has_fts:
            return
            
        try:
            # Batch insert into FTS index
            fts_data = [
                {
                    'document_id': doc.id,
                    'title': doc.title,
                    'content': doc.content,
                    'tags': ' '.join(doc.metadata.tags) if doc.metadata and doc.metadata.tags else ''
                }
                for doc in documents
            ]
            
            # Use executemany for batch insert
            session.execute(
                text("""
                    INSERT OR REPLACE INTO documents_fts(document_id, title, content, tags)
                    VALUES (:document_id, :title, :content, :tags)
                """),
                fts_data
            )
            
        except Exception as e:
            print(f"Warning: Batch FTS update failed: {e}")
    
    def search_documents_optimized(
        self,
        query: str,
        limit: Optional[int] = None,
        offset: int = 0,
        use_cache: bool = True
    ) -> List[DocumentSearchResult]:
        """
        Optimized search with caching and proper FTS5 usage.
        """
        # Generate cache key for search results
        cache_key = f"search:{hashlib.md5(f'{query}:{limit}:{offset}'.encode()).hexdigest()}"
        
        # Check cache if enabled
        if use_cache:
            cached_results = self.cache.get(cache_key)
            if cached_results is not None:
                return cached_results
        
        start_time = time.time()
        results = []
        
        try:
            with self.db_manager.get_session() as session:
                if self.db_manager._has_fts:
                    # Use FTS5 search with proper syntax
                    escaped_query = query.replace('"', '""')
                    
                    # Execute FTS5 search
                    sql_query = text("""
                        SELECT 
                            d.id, d.title, d.encrypted_content, d.content_type,
                            d.status, d.created_at, d.updated_at, d.checksum,
                            d.is_deleted, d.file_size,
                            bm25(documents_fts) as rank
                        FROM documents_fts fts
                        JOIN documents d ON d.id = fts.document_id
                        WHERE documents_fts MATCH :query
                        AND d.is_deleted = 0
                        ORDER BY rank
                        LIMIT :limit OFFSET :offset
                    """)
                    
                    result_set = session.execute(
                        sql_query,
                        {
                            'query': escaped_query,
                            'limit': limit or 100,
                            'offset': offset
                        }
                    )
                    
                    # Convert results to DocumentSearchResult objects
                    for row in result_set:
                        # Decrypt content if needed
                        content = self.repository.encryption.decrypt_field(
                            row.encrypted_content,
                            'content'
                        ) if row.encrypted_content else ''
                        
                        doc = Document(
                            id=row.id,
                            title=row.title,
                            content=content,
                            content_type=row.content_type,
                            status=row.status,
                            created_at=row.created_at,
                            updated_at=row.updated_at,
                            checksum=row.checksum,
                            file_size=row.file_size
                        )
                        
                        # Calculate relevance score from BM25 rank
                        relevance = min(1.0, max(0.0, abs(row.rank) / 10.0))
                        
                        search_result = DocumentSearchResult(
                            document=doc,
                            relevance_score=relevance,
                            matched_fields=['title', 'content'],
                            snippet=self._generate_snippet(content, query)
                        )
                        
                        results.append(search_result)
                
                else:
                    # Fall back to basic search
                    results = self.repository.search_documents(query, limit, offset)
        
        except Exception as e:
            raise StorageError(f"Optimized search failed: {e}")
        
        # Cache results
        if use_cache and results:
            self.cache.set(cache_key, results, ttl=300)  # 5 min TTL for search results
        
        # Track performance
        self._track_query_time(time.time() - start_time)
        
        return results
    
    def _generate_snippet(self, content: str, query: str, context_length: int = 150) -> str:
        """Generate a snippet showing the query in context."""
        if not content or not query:
            return ""
        
        # Find query position (case-insensitive)
        query_lower = query.lower()
        content_lower = content.lower()
        
        pos = content_lower.find(query_lower)
        if pos == -1:
            # Query not found, return beginning of content
            return content[:context_length] + "..." if len(content) > context_length else content
        
        # Calculate snippet boundaries
        start = max(0, pos - context_length // 2)
        end = min(len(content), pos + len(query) + context_length // 2)
        
        # Build snippet
        snippet = ""
        if start > 0:
            snippet = "..."
        snippet += content[start:end]
        if end < len(content):
            snippet += "..."
        
        return snippet
    
    def _track_query_time(self, query_time: float) -> None:
        """Track query execution time for performance monitoring."""
        with self._query_lock:
            self._query_times.append(query_time)
            # Keep only last 1000 queries
            if len(self._query_times) > 1000:
                self._query_times = self._query_times[-1000:]
    
    def get_performance_metrics_detailed(self) -> Dict[str, Any]:
        """Get detailed performance metrics."""
        base_metrics = self.get_performance_metrics()
        
        # Add cache statistics
        cache_stats = self.cache.get_stats()
        
        # Calculate query statistics
        query_stats = {}
        if self._query_times:
            query_stats = {
                'avg_query_time_ms': round(sum(self._query_times) / len(self._query_times) * 1000, 2),
                'min_query_time_ms': round(min(self._query_times) * 1000, 2),
                'max_query_time_ms': round(max(self._query_times) * 1000, 2),
                'total_queries': len(self._query_times)
            }
        
        return {
            **base_metrics,
            'cache': cache_stats,
            'queries': query_stats,
            'batch_size': self._batch_size,
            'fts_enabled': self.db_manager._has_fts
        }
    
    def optimize_database_advanced(self) -> bool:
        """
        Advanced database optimization with statistics update.
        """
        try:
            with self.db_manager._engine.connect() as conn:
                # Update SQLite statistics
                conn.execute(text("ANALYZE"))
                
                # Optimize FTS index
                if self.db_manager._has_fts:
                    conn.execute(text("INSERT INTO documents_fts(documents_fts) VALUES('optimize')"))
                
                # Run VACUUM
                conn.execute(text("VACUUM"))
                
                conn.commit()
            
            # Clear cache after optimization
            self.cache.clear()
            
            return True
            
        except Exception as e:
            print(f"Advanced optimization failed: {e}")
            return False
    
    def stream_documents(
        self,
        batch_size: Optional[int] = None,
        status: Optional[DocumentStatus] = None,
        content_type: Optional[ContentType] = None
    ) -> Generator[List[Document], None, None]:
        """
        Stream documents in batches for memory-efficient processing.
        """
        if batch_size is None:
            batch_size = self._batch_size
        
        offset = 0
        while True:
            batch = self.list_documents(
                status=status,
                content_type=content_type,
                limit=batch_size,
                offset=offset,
                sort_by='created_at',
                sort_desc=False
            )
            
            if not batch:
                break
            
            yield batch
            
            offset += batch_size
            
            # If we got less than batch_size, we're done
            if len(batch) < batch_size:
                break