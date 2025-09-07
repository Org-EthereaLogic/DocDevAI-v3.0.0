"""
M002 Local Storage System - Main Storage Manager

Main storage manager implementing the public API for document operations:
- Document CRUD operations with encryption
- Full-text search and metadata filtering
- Performance monitoring and statistics
- Integration with M001 ConfigurationManager
- Connection pooling and memory mode adaptation
"""

import threading
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import time

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


class StorageError(Exception):
    """Storage system errors."""
    pass


class LocalStorageManager:
    """
    M002 Local Storage System - Main API
    
    Provides centralized document storage management with:
    - Privacy-first encrypted storage using M001 patterns
    - Memory mode adaptation from M001 ConfigurationManager
    - Full-text search and metadata filtering
    - Performance monitoring and statistics
    - Connection pooling and resource management
    """
    
    def __init__(
        self,
        db_path: Optional[Path] = None,
        config: Optional[ConfigurationManager] = None
    ):
        """
        Initialize Local Storage Manager.
        
        Args:
            db_path: Path to SQLite database file (optional)
            config: M001 ConfigurationManager instance (optional)
        """
        # Use provided config or create new one
        self.config = config or ConfigurationManager()
        
        # Determine database path
        if db_path is None:
            storage_dir = self.config.get('config_dir') / "storage"
            storage_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = storage_dir / "documents.db"
        else:
            self.db_path = db_path
        
        # Initialize components
        self._initialize_components()
        
        # Performance monitoring
        self._start_time = time.time()
        self._operation_count = 0
        self._lock = threading.Lock()
        
        # Verify system health
        self._verify_system_health()
    
    def _initialize_components(self) -> None:
        """Initialize storage system components."""
        try:
            # Initialize database manager
            self.db_manager = DatabaseManager(
                db_path=self.db_path,
                config=self.config
            )
            
            # Initialize repository
            self.repository = DocumentRepository(
                db_manager=self.db_manager,
                config=self.config
            )
            
            # Create connection pool based on memory mode
            self._connection_pool = self._create_connection_pool()
            
        except Exception as e:
            raise StorageError(f"Storage system initialization failed: {e}")
    
    def _create_connection_pool(self) -> Dict[str, Any]:
        """Create connection pool configuration based on memory mode."""
        memory_mode = self.config.get('memory_mode', MemoryMode.STANDARD)
        
        if memory_mode == MemoryMode.BASELINE:
            return {
                'max_connections': 2,
                'pool_timeout': 30,
                'cache_size': self.config.get('cache_size_mb', 32)
            }
        elif memory_mode == MemoryMode.STANDARD:
            return {
                'max_connections': 4,
                'pool_timeout': 30,
                'cache_size': self.config.get('cache_size_mb', 64)
            }
        elif memory_mode == MemoryMode.ENHANCED:
            return {
                'max_connections': 8,
                'pool_timeout': 20,
                'cache_size': self.config.get('cache_size_mb', 128)
            }
        else:  # PERFORMANCE
            return {
                'max_connections': 16,
                'pool_timeout': 10,
                'cache_size': self.config.get('cache_size_mb', 256)
            }
    
    def _verify_system_health(self) -> None:
        """Verify storage system is healthy and operational."""
        try:
            # Check database integrity
            if not self.db_manager.check_database_integrity():
                raise StorageError("Database integrity check failed")
            
            # Verify encryption system
            encryption_info = self.repository.encryption.get_encryption_info()
            if encryption_info['encryption_enabled'] and not encryption_info['master_key_initialized']:
                raise StorageError("Encryption system not properly initialized")
            
        except Exception as e:
            raise StorageError(f"System health verification failed: {e}")
    
    def _track_operation(self) -> None:
        """Track operation for performance monitoring."""
        with self._lock:
            self._operation_count += 1
    
    # Document CRUD Operations
    
    def create_document(self, document: Document) -> Document:
        """
        Create a new document.
        
        Args:
            document: Document to create
            
        Returns:
            Created document with timestamps
            
        Raises:
            StorageError: If creation fails
        """
        self._track_operation()
        
        try:
            # Update checksums if needed
            if document.checksum is None:
                document.update_checksum()
            
            # Create document
            created_doc = self.repository.create_document(document)
            
            return created_doc
            
        except Exception as e:
            raise StorageError(f"Document creation failed: {e}")
    
    def get_document(self, document_id: str) -> Optional[Document]:
        """
        Retrieve a document by ID.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Document or None if not found
        """
        self._track_operation()
        
        try:
            return self.repository.get_document(document_id)
            
        except Exception as e:
            raise StorageError(f"Document retrieval failed: {e}")
    
    def update_document(self, document: Document) -> Optional[Document]:
        """
        Update an existing document.
        
        Args:
            document: Updated document
            
        Returns:
            Updated document or None if not found
        """
        self._track_operation()
        
        try:
            # Update checksum
            document.update_checksum()
            
            return self.repository.update_document(document)
            
        except Exception as e:
            raise StorageError(f"Document update failed: {e}")
    
    def delete_document(self, document_id: str, hard_delete: bool = False) -> bool:
        """
        Delete a document.
        
        Args:
            document_id: Document identifier
            hard_delete: If True, permanently delete; if False, soft delete
            
        Returns:
            True if document was deleted, False if not found
        """
        self._track_operation()
        
        try:
            return self.repository.delete_document(
                document_id,
                soft_delete=not hard_delete
            )
            
        except Exception as e:
            raise StorageError(f"Document deletion failed: {e}")
    
    def list_documents(
        self,
        status: Optional[DocumentStatus] = None,
        content_type: Optional[ContentType] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        sort_by: str = 'updated_at',
        sort_desc: bool = True
    ) -> List[Document]:
        """
        List documents with filtering and pagination.
        
        Args:
            status: Filter by document status
            content_type: Filter by content type
            limit: Maximum number of results
            offset: Number of results to skip
            sort_by: Field to sort by
            sort_desc: Sort in descending order
            
        Returns:
            List of documents
        """
        self._track_operation()
        
        try:
            return self.repository.list_documents(
                status=status,
                content_type=content_type,
                limit=limit,
                offset=offset,
                sort_by=sort_by,
                sort_desc=sort_desc
            )
            
        except Exception as e:
            raise StorageError(f"Document listing failed: {e}")
    
    # Search Operations
    
    def search_documents(
        self,
        query: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[DocumentSearchResult]:
        """
        Search documents using full-text search.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of search results with relevance scores
        """
        self._track_operation()
        
        try:
            return self.repository.search_documents(
                query=query,
                limit=limit,
                offset=offset
            )
            
        except Exception as e:
            raise StorageError(f"Document search failed: {e}")
    
    def search_by_metadata(
        self,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
        author: Optional[str] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Document]:
        """
        Search documents by metadata criteria.
        
        Args:
            tags: Filter by tags
            category: Filter by category
            author: Filter by author
            custom_fields: Filter by custom field values
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of matching documents
        """
        self._track_operation()
        
        try:
            return self.repository.search_by_metadata(
                tags=tags,
                category=category,
                author=author,
                custom_fields=custom_fields,
                limit=limit,
                offset=offset
            )
            
        except Exception as e:
            raise StorageError(f"Metadata search failed: {e}")
    
    # System Information and Statistics
    
    def get_storage_stats(self) -> StorageStats:
        """
        Get storage system statistics.
        
        Returns:
            Storage statistics
        """
        try:
            return self.repository.get_storage_stats()
            
        except Exception as e:
            raise StorageError(f"Failed to get storage statistics: {e}")
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Get comprehensive system information.
        
        Returns:
            Dictionary with system information
        """
        try:
            # Get database stats
            db_stats = self.db_manager.get_database_stats()
            
            # Get encryption info
            encryption_info = self.repository.encryption.get_encryption_info()
            
            # Get memory info from M001
            memory_info = self.config.get_memory_info()
            
            # Calculate uptime and operation rate
            uptime = time.time() - self._start_time
            operations_per_second = self._operation_count / uptime if uptime > 0 else 0
            
            return {
                'database': db_stats,
                'encryption': encryption_info,
                'memory': memory_info,
                'performance': {
                    'uptime_seconds': uptime,
                    'total_operations': self._operation_count,
                    'operations_per_second': round(operations_per_second, 2),
                    'connection_pool': self._connection_pool
                },
                'storage': {
                    'database_path': str(self.db_path),
                    'privacy_mode': self.config.get('privacy_mode').value,
                    'encryption_enabled': self.config.get('encryption_enabled', True)
                }
            }
            
        except Exception as e:
            return {'error': f"Failed to get system info: {e}"}
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics and baseline measurements.
        
        Returns:
            Dictionary with performance metrics
        """
        try:
            # Measure database response time
            start_time = time.time()
            self.db_manager.check_database_integrity()
            db_response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Get current operation rate
            uptime = time.time() - self._start_time
            current_ops_per_sec = self._operation_count / uptime if uptime > 0 else 0
            
            # Get memory usage info
            memory_info = self.config.get_memory_info()
            
            return {
                'database_response_ms': round(db_response_time, 2),
                'operations_per_second': round(current_ops_per_sec, 2),
                'total_operations': self._operation_count,
                'uptime_seconds': round(uptime, 2),
                'memory_mode': memory_info['mode'],
                'cache_size_mb': memory_info['cache_size_mb'],
                'max_concurrent_ops': memory_info['max_concurrent_operations'],
                'connection_pool_size': self._connection_pool['max_connections']
            }
            
        except Exception as e:
            return {'error': f"Failed to get performance metrics: {e}"}
    
    # System Maintenance
    
    def optimize_database(self) -> bool:
        """
        Optimize database performance.
        
        Returns:
            True if optimization succeeded, False otherwise
        """
        try:
            success = self.db_manager.vacuum_database()
            if success:
                # Clear repository cache to force refresh
                self.repository.clear_cache()
            
            return success
            
        except Exception as e:
            print(f"Database optimization failed: {e}")
            return False
    
    def backup_database(self, backup_path: Path) -> bool:
        """
        Create database backup.
        
        Args:
            backup_path: Path for backup file
            
        Returns:
            True if backup succeeded, False otherwise
        """
        try:
            return self.db_manager.backup_database(backup_path)
            
        except Exception as e:
            print(f"Database backup failed: {e}")
            return False
    
    def verify_system_integrity(self) -> Dict[str, bool]:
        """
        Verify system integrity and health.
        
        Returns:
            Dictionary with integrity check results
        """
        results = {}
        
        try:
            # Check database integrity
            results['database_integrity'] = self.db_manager.check_database_integrity()
            
            # Check encryption system
            results['encryption_integrity'] = self.repository.encryption.verify_encryption_integrity()
            
            # Check configuration validity
            config_issues = self.config.validate_configuration()
            results['configuration_valid'] = len(config_issues) == 0
            
            # Overall system health
            results['system_healthy'] = all(results.values())
            
        except Exception as e:
            results['error'] = f"Integrity check failed: {e}"
            results['system_healthy'] = False
        
        return results
    
    # Connection Management
    
    def is_connected(self) -> bool:
        """
        Check if storage system is connected and operational.
        
        Returns:
            True if connected and healthy, False otherwise
        """
        try:
            return self.db_manager.check_database_integrity()
        except Exception:
            return False
    
    def close(self) -> None:
        """Close storage system and cleanup resources."""
        try:
            if hasattr(self, 'repository'):
                self.repository.clear_cache()
            
            if hasattr(self, 'db_manager'):
                self.db_manager.close()
                
        except Exception as e:
            print(f"Warning: Error during storage system cleanup: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def __repr__(self) -> str:
        """String representation of storage manager."""
        try:
            stats = self.get_storage_stats()
            return (
                f"LocalStorageManager("
                f"documents={stats.total_documents}, "
                f"memory_mode={self.config.get('memory_mode').value}, "
                f"encryption={self.config.get('encryption_enabled', True)}, "
                f"db_path={self.db_path})"
            )
        except Exception:
            return (
                f"LocalStorageManager("
                f"memory_mode={self.config.get('memory_mode').value}, "
                f"db_path={self.db_path})"
            )