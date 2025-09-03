"""
M002: Enhanced Local Storage with Recovery Scenarios

This module extends the local storage system with:
- Automatic recovery from database locks
- Connection recovery after failures
- Graceful degradation when resources are limited
- User-friendly error messages

Addresses ISS-015: Recovery scenarios enhancement
"""

import time
import logging
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

# Import original storage components
try:
    from devdocai.storage.local_storage import DocumentData, ListParams
except ImportError:
    # Fallback definitions if original not available
    from pydantic import BaseModel
    
    class DocumentData(BaseModel):
        title: str
        content: str
        metadata: Optional[Dict[str, Any]] = None
    
    class ListParams(BaseModel):
        limit: int = 100
        offset: int = 0

# Import error handling and recovery
from devdocai.core.error_handler import (
    UserFriendlyError, ErrorCategory, ErrorContext,
    ErrorHandler, DatabaseErrorHandler
)
from devdocai.core.recovery_manager import (
    RecoveryManager, RetryConfig, CircuitBreakerConfig,
    DatabaseRecovery, RecoveryContext
)

logger = logging.getLogger(__name__)


class EnhancedLocalStorageSystem:
    """
    Enhanced Local Storage with comprehensive recovery mechanisms.
    
    Features:
    - Automatic retry on database locks
    - Connection pool recovery
    - Graceful degradation to read-only mode
    - User-friendly error messages
    """
    
    def __init__(self, config_manager=None):
        """Initialize with recovery capabilities."""
        self.config_manager = config_manager
        self.recovery = RecoveryManager()
        self._connection = None
        self._read_only_mode = False
        
        # Get database path from config
        self.db_path = self._get_db_path()
        
        # Initialize database with recovery
        self._initialize_database()
    
    def _get_db_path(self) -> str:
        """Get database path with fallback locations."""
        if self.config_manager:
            try:
                db_path = self.config_manager.get('database.path', './data/devdocai.db')
            except:
                db_path = './data/devdocai.db'
        else:
            db_path = './data/devdocai.db'
        
        # Ensure directory exists
        db_dir = Path(db_path).parent
        try:
            db_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            # Fall back to temp directory
            import tempfile
            temp_dir = Path(tempfile.gettempdir()) / 'devdocai'
            temp_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(temp_dir / 'devdocai.db')
            
            logger.warning(f"Using temporary database location: {db_path}")
        
        return db_path
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with automatic recovery."""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                if not self._connection:
                    self._connection = sqlite3.connect(
                        self.db_path,
                        timeout=30.0,
                        isolation_level=None
                    )
                    self._connection.row_factory = sqlite3.Row
                
                # Test connection
                self._connection.execute("SELECT 1")
                yield self._connection
                return
                
            except sqlite3.OperationalError as e:
                retry_count += 1
                
                if "locked" in str(e).lower():
                    # Handle locked database
                    wait_time = min(1.0 * (2 ** retry_count), 10.0)
                    logger.warning(f"Database locked, retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    
                elif "corrupt" in str(e).lower():
                    # Attempt recovery
                    logger.error("Database corruption detected, attempting recovery...")
                    self._recover_database()
                    
                else:
                    # Connection issue
                    logger.warning(f"Connection error: {e}, attempting reconnection...")
                    self._connection = None
                    
                if retry_count >= max_retries:
                    # Switch to read-only mode as fallback
                    self._enable_read_only_mode()
                    raise DatabaseErrorHandler.handle_connection_error(
                        self.db_path, e
                    )
            
            except Exception as e:
                raise DatabaseErrorHandler.handle_connection_error(
                    self.db_path, e
                )
    
    def _initialize_database(self):
        """Initialize database with recovery on failure."""
        try:
            with self._get_connection() as conn:
                # Create tables if they don't exist
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        uuid TEXT UNIQUE NOT NULL,
                        title TEXT NOT NULL,
                        content TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        deleted_at TIMESTAMP
                    )
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_documents_uuid 
                    ON documents(uuid)
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS document_metadata (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        document_id INTEGER NOT NULL,
                        key TEXT NOT NULL,
                        value TEXT,
                        FOREIGN KEY (document_id) REFERENCES documents(id),
                        UNIQUE(document_id, key)
                    )
                """)
                
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            self._enable_read_only_mode()
    
    def _recover_database(self):
        """Attempt to recover corrupted database."""
        logger.info("Attempting database recovery...")
        
        try:
            # Backup corrupted database
            import shutil
            backup_path = f"{self.db_path}.corrupted.{int(time.time())}"
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Backed up corrupted database to {backup_path}")
            
            # Try to dump and recreate
            try:
                conn = sqlite3.connect(self.db_path)
                
                # Dump what we can
                with open(f"{self.db_path}.recovery.sql", 'w') as f:
                    for line in conn.iterdump():
                        f.write(f"{line}\n")
                
                conn.close()
                
                # Remove corrupted database
                Path(self.db_path).unlink()
                
                # Recreate from dump
                new_conn = sqlite3.connect(self.db_path)
                with open(f"{self.db_path}.recovery.sql", 'r') as f:
                    new_conn.executescript(f.read())
                new_conn.close()
                
                logger.info("Database recovery successful")
                self._connection = None  # Force reconnection
                
            except Exception as recovery_error:
                logger.error(f"Recovery failed: {recovery_error}")
                
                # Create fresh database
                Path(self.db_path).unlink(missing_ok=True)
                self._connection = None
                self._initialize_database()
                
                raise UserFriendlyError(
                    technical_error=recovery_error,
                    category=ErrorCategory.DATABASE,
                    user_message="Database was corrupted and had to be reset",
                    context=ErrorContext(
                        module="M002",
                        operation="recover_database",
                        details={
                            "backup_location": backup_path,
                            "data_loss": "Previous data backed up but not recovered"
                        },
                        suggestions=[
                            f"Check backup at {backup_path}",
                            "Contact support for data recovery assistance",
                            "Restore from your latest backup if available"
                        ]
                    )
                )
                
        except Exception as e:
            logger.error(f"Database recovery failed: {e}")
            self._enable_read_only_mode()
    
    def _enable_read_only_mode(self):
        """Enable read-only mode when write operations fail."""
        self._read_only_mode = True
        logger.warning("Switching to READ-ONLY mode due to database issues")
    
    @ErrorHandler.wrap_operation("create_document", "M002")
    def create_document(self, data: DocumentData) -> Dict[str, Any]:
        """
        Create document with automatic retry and recovery.
        
        Args:
            data: Document data to create
            
        Returns:
            Created document with ID
        """
        if self._read_only_mode:
            raise UserFriendlyError(
                category=ErrorCategory.DATABASE,
                user_message="Cannot create documents in read-only mode",
                context=ErrorContext(
                    module="M002",
                    operation="create_document",
                    suggestions=[
                        "Restart the application to attempt recovery",
                        "Check database file permissions",
                        "Ensure sufficient disk space"
                    ]
                )
            )
        
        # Use recovery context for cleanup on failure
        with RecoveryContext() as recovery:
            import uuid
            doc_uuid = str(uuid.uuid4())
            
            # Retry on lock with exponential backoff
            @self.recovery.retry_with_backoff(
                RetryConfig(
                    max_attempts=3,
                    retry_on=[sqlite3.OperationalError]
                )
            )
            def insert_document():
                with self._get_connection() as conn:
                    cursor = conn.execute(
                        """
                        INSERT INTO documents (uuid, title, content)
                        VALUES (?, ?, ?)
                        """,
                        (doc_uuid, data.title, data.content)
                    )
                    return cursor.lastrowid
            
            try:
                doc_id = insert_document()
                
                # Insert metadata if provided
                if hasattr(data, 'metadata') and data.metadata:
                    self._save_metadata(doc_id, data.metadata)
                
                logger.info(f"Document created: {doc_uuid}")
                
                return {
                    'id': doc_id,
                    'uuid': doc_uuid,
                    'title': data.title
                }
                
            except sqlite3.IntegrityError as e:
                if "UNIQUE" in str(e):
                    raise UserFriendlyError(
                        technical_error=e,
                        category=ErrorCategory.DATABASE,
                        user_message="A document with this ID already exists",
                        context=ErrorContext(
                            module="M002",
                            operation="create_document",
                            suggestions=[
                                "Use update_document to modify existing documents",
                                "Generate a new unique ID"
                            ]
                        )
                    )
                raise DatabaseErrorHandler.handle_query_error("INSERT", e)
    
    @ErrorHandler.wrap_operation("get_document", "M002")
    def get_document(self, doc_id: Any) -> Optional[Dict[str, Any]]:
        """
        Get document with connection recovery.
        
        Args:
            doc_id: Document ID or UUID
            
        Returns:
            Document data or None
        """
        # Try cache first (if available)
        cache_key = f"doc_{doc_id}"
        
        @self.recovery.cache_on_failure(cache_key=cache_key, ttl=300)
        def fetch_document():
            with self._get_connection() as conn:
                # Determine query based on ID type
                if isinstance(doc_id, int):
                    query = "SELECT * FROM documents WHERE id = ? AND deleted_at IS NULL"
                else:
                    query = "SELECT * FROM documents WHERE uuid = ? AND deleted_at IS NULL"
                
                cursor = conn.execute(query, (doc_id,))
                row = cursor.fetchone()
                
                if row:
                    return dict(row)
                return None
        
        try:
            return fetch_document()
        except Exception as e:
            # Graceful degradation - return cached version if available
            if cache_key in self.recovery.cached_results:
                logger.warning(f"Returning cached document due to: {e}")
                return self.recovery.cached_results[cache_key]['value']
            
            raise DatabaseErrorHandler.handle_query_error("SELECT", e)
    
    @ErrorHandler.wrap_operation("update_document", "M002")
    def update_document(self, doc_id: int, data: DocumentData) -> bool:
        """
        Update document with retry on lock.
        
        Args:
            doc_id: Document ID
            data: Updated document data
            
        Returns:
            True if successful
        """
        if self._read_only_mode:
            raise UserFriendlyError(
                category=ErrorCategory.DATABASE,
                user_message="Cannot update documents in read-only mode",
                context=ErrorContext(
                    module="M002",
                    operation="update_document",
                    suggestions=["Restart application to attempt recovery"]
                )
            )
        
        @self.recovery.retry_with_backoff(
            RetryConfig(max_attempts=3)
        )
        def update():
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    UPDATE documents
                    SET title = ?, content = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND deleted_at IS NULL
                    """,
                    (data.title, data.content, doc_id)
                )
                return cursor.rowcount > 0
        
        try:
            success = update()
            if success:
                logger.info(f"Document {doc_id} updated")
            else:
                logger.warning(f"Document {doc_id} not found for update")
            return success
            
        except Exception as e:
            raise DatabaseErrorHandler.handle_query_error("UPDATE", e)
    
    @ErrorHandler.wrap_operation("delete_document", "M002") 
    def delete_document(self, doc_id: int) -> bool:
        """
        Soft delete document with recovery.
        
        Args:
            doc_id: Document ID
            
        Returns:
            True if successful
        """
        if self._read_only_mode:
            raise UserFriendlyError(
                category=ErrorCategory.DATABASE,
                user_message="Cannot delete documents in read-only mode",
                context=ErrorContext(
                    module="M002",
                    operation="delete_document",
                    suggestions=["Restart application to attempt recovery"]
                )
            )
        
        @self.recovery.retry_with_backoff()
        def soft_delete():
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    UPDATE documents
                    SET deleted_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND deleted_at IS NULL
                    """,
                    (doc_id,)
                )
                return cursor.rowcount > 0
        
        try:
            return soft_delete()
        except Exception as e:
            raise DatabaseErrorHandler.handle_query_error("DELETE", e)
    
    @ErrorHandler.wrap_operation("list_documents", "M002")
    def list_documents(self, params: Optional[ListParams] = None) -> List[Dict[str, Any]]:
        """
        List documents with graceful degradation.
        
        Args:
            params: List parameters
            
        Returns:
            List of documents
        """
        if params is None:
            params = ListParams()
        
        @self.recovery.cache_on_failure(
            cache_key=f"list_{params.limit}_{params.offset}",
            ttl=60
        )
        def fetch_list():
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, uuid, title, created_at, updated_at
                    FROM documents
                    WHERE deleted_at IS NULL
                    ORDER BY updated_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (params.limit, params.offset)
                )
                return [dict(row) for row in cursor.fetchall()]
        
        try:
            return fetch_list()
        except Exception as e:
            # Return empty list on failure (graceful degradation)
            logger.error(f"Failed to list documents: {e}")
            return []
    
    def _save_metadata(self, doc_id: int, metadata: Dict[str, Any]):
        """Save document metadata with error handling."""
        try:
            with self._get_connection() as conn:
                for key, value in metadata.items():
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO document_metadata
                        (document_id, key, value)
                        VALUES (?, ?, ?)
                        """,
                        (doc_id, key, str(value))
                    )
        except Exception as e:
            # Log but don't fail document creation
            logger.error(f"Failed to save metadata: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics with error handling."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) as count FROM documents WHERE deleted_at IS NULL"
                )
                count = cursor.fetchone()['count']
                
                # Get database size
                db_size = Path(self.db_path).stat().st_size if Path(self.db_path).exists() else 0
                
                return {
                    'document_count': count,
                    'database_size': db_size,
                    'database_path': self.db_path,
                    'read_only_mode': self._read_only_mode,
                    'status': 'degraded' if self._read_only_mode else 'healthy'
                }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                'error': str(e),
                'status': 'error',
                'read_only_mode': self._read_only_mode
            }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on storage system."""
        health = {
            'healthy': True,
            'checks': {}
        }
        
        # Check database connection
        try:
            with self._get_connection() as conn:
                conn.execute("SELECT 1")
            health['checks']['connection'] = 'OK'
        except Exception as e:
            health['checks']['connection'] = f'FAILED: {e}'
            health['healthy'] = False
        
        # Check write capability
        if self._read_only_mode:
            health['checks']['write_capability'] = 'DEGRADED: Read-only mode'
            health['healthy'] = False
        else:
            health['checks']['write_capability'] = 'OK'
        
        # Check disk space
        try:
            import shutil
            db_dir = Path(self.db_path).parent
            stat = shutil.disk_usage(db_dir)
            free_gb = stat.free / (1024**3)
            
            if free_gb < 0.1:  # Less than 100MB
                health['checks']['disk_space'] = f'CRITICAL: {free_gb:.2f}GB free'
                health['healthy'] = False
            elif free_gb < 1.0:  # Less than 1GB
                health['checks']['disk_space'] = f'WARNING: {free_gb:.2f}GB free'
            else:
                health['checks']['disk_space'] = f'OK: {free_gb:.1f}GB free'
        except Exception as e:
            health['checks']['disk_space'] = f'UNKNOWN: {e}'
        
        return health
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        if self._connection:
            try:
                self._connection.close()
            except:
                pass
            self._connection = None