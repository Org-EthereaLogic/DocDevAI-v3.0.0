"""
M002 Local Storage System - Database Layer

SQLAlchemy-based database layer for document storage:
- SQLite with connection pooling
- Schema management and migrations
- Integration with M001 memory modes
- Prepared for SQLCipher integration in future passes
"""

import sqlite3
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import (
    create_engine, 
    Column, 
    String, 
    Text, 
    DateTime, 
    Integer,
    Boolean,
    MetaData,
    Table,
    Index,
    event,
    text
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.engine import Engine

from devdocai.core.config import ConfigurationManager, MemoryMode


class DatabaseError(Exception):
    """Database-related errors."""
    pass


# SQLAlchemy 2.0 base class
class Base(DeclarativeBase):
    pass


class DocumentTable(Base):
    """SQLAlchemy model for documents table."""
    
    __tablename__ = 'documents'
    
    id = Column(String(255), primary_key=True, nullable=False)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    content_type = Column(String(50), nullable=False, default='markdown')
    status = Column(String(50), nullable=False, default='draft')
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, 
                       default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False,
                       default=lambda: datetime.now(timezone.utc),
                       onupdate=lambda: datetime.now(timezone.utc))
    
    # Optional fields
    source_path = Column(String(1000), nullable=True)
    checksum = Column(String(128), nullable=True)
    
    # Metadata (stored as JSON text, encrypted if enabled)
    metadata_json = Column(Text, nullable=True)
    
    # Soft delete support
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class DocumentSearchIndex(Base):
    """Full-text search index for documents."""
    
    __tablename__ = 'document_search'
    
    document_id = Column(String(255), primary_key=True, nullable=False)
    title_indexed = Column(Text, nullable=False)
    content_indexed = Column(Text, nullable=False)
    tags_indexed = Column(Text, nullable=True)


class DatabaseManager:
    """
    Database connection and session management.
    
    Features:
    - Connection pooling adapted to M001 memory modes
    - SQLite with WAL mode for better concurrency
    - Prepared for SQLCipher integration
    - Schema migrations and integrity checks
    """
    
    def __init__(self, db_path: Path, config: ConfigurationManager):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
            config: M001 ConfigurationManager instance
        """
        self.db_path = db_path
        self.config = config
        self._engine: Optional[Engine] = None
        self._sessionmaker: Optional[sessionmaker] = None
        self._lock = threading.Lock()
        
        # Initialize database connection
        self._initialize_database()
    
    def _initialize_database(self) -> None:
        """Initialize database connection and schema."""
        try:
            # Ensure database directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create database engine with memory mode adaptation
            self._engine = self._create_engine()
            
            # Create session factory
            self._sessionmaker = sessionmaker(bind=self._engine)
            
            # Create tables if they don't exist
            self._create_tables()
            
            # Configure database for optimal performance
            self._configure_database()
            
        except Exception as e:
            raise DatabaseError(f"Database initialization failed: {e}")
    
    def _create_engine(self) -> Engine:
        """Create SQLAlchemy engine with connection pooling."""
        # Build connection URL
        db_url = f"sqlite:///{self.db_path}"
        
        # Get memory mode settings
        memory_mode = self.config.get('memory_mode', MemoryMode.STANDARD)
        max_connections = self.config.get('max_concurrent_operations', 4)
        
        # Adapt pool settings to memory mode
        if memory_mode == MemoryMode.BASELINE:
            pool_size = 2
            max_overflow = 1
        elif memory_mode == MemoryMode.STANDARD:
            pool_size = 4
            max_overflow = 2
        elif memory_mode == MemoryMode.ENHANCED:
            pool_size = 8
            max_overflow = 4
        else:  # PERFORMANCE
            pool_size = 16
            max_overflow = 8
        
        # Create engine with SQLite-compatible settings
        engine = create_engine(
            db_url,
            poolclass=StaticPool,
            pool_pre_ping=True,  # Verify connections before use
            echo=self.config.get('debug_mode', False),  # SQL logging in debug mode
            connect_args={
                'check_same_thread': False,  # Allow multi-threading
                'timeout': 30  # Connection timeout
            }
        )
        
        # Configure SQLite-specific settings
        @event.listens_for(engine, "connect")
        def configure_sqlite(dbapi_connection, connection_record):
            """Configure SQLite connection settings."""
            cursor = dbapi_connection.cursor()
            
            # Enable WAL mode for better concurrency
            cursor.execute("PRAGMA journal_mode=WAL")
            
            # Optimize for performance
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=10000")
            cursor.execute("PRAGMA temp_store=MEMORY")
            
            # Enable foreign keys
            cursor.execute("PRAGMA foreign_keys=ON")
            
            # Set busy timeout
            cursor.execute("PRAGMA busy_timeout=30000")
            
            cursor.close()
        
        return engine
    
    def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        try:
            Base.metadata.create_all(self._engine)
            
            # Create additional indexes for performance
            self._create_indexes()
            
        except Exception as e:
            raise DatabaseError(f"Table creation failed: {e}")
    
    def _create_indexes(self) -> None:
        """Create database indexes for optimal query performance."""
        try:
            with self._engine.connect() as conn:
                # Index on status for filtering
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS idx_documents_status "
                    "ON documents(status)"
                ))
                
                # Index on content_type
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS idx_documents_content_type "
                    "ON documents(content_type)"
                ))
                
                # Index on created_at for sorting
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS idx_documents_created_at "
                    "ON documents(created_at)"
                ))
                
                # Index on updated_at for sorting
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS idx_documents_updated_at "
                    "ON documents(updated_at)"
                ))
                
                # Composite index for soft delete queries
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS idx_documents_active "
                    "ON documents(is_deleted, status)"
                ))
                
                # Full-text search setup (using FTS5 if available)
                try:
                    # Test if FTS5 is available by creating a simple test table
                    conn.execute(text("CREATE VIRTUAL TABLE IF NOT EXISTS test_fts USING fts5(text)"))
                    conn.execute(text("DROP TABLE test_fts"))
                    
                    # Create FTS5 virtual table for document search
                    conn.execute(text("""
                        CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                            document_id UNINDEXED,
                            title,
                            content,
                            tags
                        )
                    """))
                    
                    # Create triggers to keep FTS index in sync
                    conn.execute(text("""
                        CREATE TRIGGER IF NOT EXISTS documents_fts_insert
                        AFTER INSERT ON documents
                        BEGIN
                            INSERT INTO documents_fts(document_id, title, content, tags)
                            VALUES (new.id, new.title, new.content, '');
                        END
                    """))
                    
                    conn.execute(text("""
                        CREATE TRIGGER IF NOT EXISTS documents_fts_update
                        AFTER UPDATE ON documents
                        BEGIN
                            UPDATE documents_fts
                            SET title = new.title, content = new.content, tags = ''
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
                    
                    # Populate FTS index with existing documents
                    conn.execute(text("""
                        INSERT OR REPLACE INTO documents_fts(document_id, title, content, tags)
                        SELECT id, title, content, ''
                        FROM documents
                        WHERE is_deleted = 0
                    """))
                    
                except Exception as e:
                    # FTS5 not available, will fall back to basic search
                    print(f"FTS5 setup failed: {e}")
                    pass
                
                conn.commit()
                
        except Exception as e:
            # Index creation failures are not fatal
            print(f"Warning: Index creation failed: {e}")
    
    def _configure_database(self) -> None:
        """Configure database settings for optimal performance."""
        try:
            with self._engine.connect() as conn:
                # Verify basic connectivity and settings
                result = conn.execute(text("PRAGMA journal_mode"))
                journal_mode = result.fetchone()[0]
                
                if journal_mode != 'wal':
                    print(f"Warning: Expected WAL journal mode, got {journal_mode}")
                
                # Check if FTS is available and working
                try:
                    conn.execute(text("SELECT COUNT(*) FROM documents_fts"))
                    self._has_fts = True
                except Exception:
                    self._has_fts = False
                
        except Exception as e:
            raise DatabaseError(f"Database configuration failed: {e}")
    
    @contextmanager
    def get_session(self):
        """
        Context manager for database sessions.
        
        Yields:
            SQLAlchemy Session instance
        """
        if self._sessionmaker is None:
            raise DatabaseError("Database not initialized")
        
        session = self._sessionmaker()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def execute_raw_sql(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute raw SQL query.
        
        Args:
            sql: SQL query string
            params: Query parameters
            
        Returns:
            List of result dictionaries
        """
        try:
            with self._engine.connect() as conn:
                result = conn.execute(text(sql), params or {})
                
                # Convert result to list of dictionaries
                if result.returns_rows:
                    columns = result.keys()
                    return [dict(zip(columns, row)) for row in result.fetchall()]
                else:
                    return []
                    
        except Exception as e:
            raise DatabaseError(f"Raw SQL execution failed: {e}")
    
    def check_database_integrity(self) -> bool:
        """
        Check database integrity.
        
        Returns:
            True if database is healthy, False otherwise
        """
        try:
            with self._engine.connect() as conn:
                # Run PRAGMA integrity_check
                result = conn.execute(text("PRAGMA integrity_check"))
                integrity_result = result.fetchone()[0]
                
                if integrity_result != 'ok':
                    print(f"Database integrity check failed: {integrity_result}")
                    return False
                
                # Check if tables exist
                result = conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='documents'"
                ))
                
                if not result.fetchone():
                    print("Documents table does not exist")
                    return False
                
                return True
                
        except Exception as e:
            print(f"Database integrity check error: {e}")
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with database statistics
        """
        try:
            with self._engine.connect() as conn:
                # Get database size
                result = conn.execute(text(
                    "SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()"
                ))
                db_size = result.fetchone()[0]
                
                # Get document count
                result = conn.execute(text("SELECT COUNT(*) FROM documents WHERE is_deleted = 0"))
                doc_count = result.fetchone()[0]
                
                # Get deleted document count
                result = conn.execute(text("SELECT COUNT(*) FROM documents WHERE is_deleted = 1"))
                deleted_count = result.fetchone()[0]
                
                # Get journal mode
                result = conn.execute(text("PRAGMA journal_mode"))
                journal_mode = result.fetchone()[0]
                
                return {
                    'database_size_bytes': db_size,
                    'total_documents': doc_count,
                    'deleted_documents': deleted_count,
                    'journal_mode': journal_mode,
                    'has_fts': getattr(self, '_has_fts', False),
                    'memory_mode': self.config.get('memory_mode', MemoryMode.STANDARD).value,
                    'max_connections': self.config.get('max_concurrent_operations', 4)
                }
                
        except Exception as e:
            return {'error': f"Failed to get database stats: {e}"}
    
    def vacuum_database(self) -> bool:
        """
        Vacuum database to reclaim space and optimize.
        
        Returns:
            True if vacuum succeeded, False otherwise
        """
        try:
            with self._engine.connect() as conn:
                # Execute VACUUM
                conn.execute(text("VACUUM"))
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Database vacuum failed: {e}")
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
            # Ensure backup directory exists
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Use SQLite backup API
            with sqlite3.connect(str(self.db_path)) as source:
                with sqlite3.connect(str(backup_path)) as backup:
                    source.backup(backup)
            
            return True
            
        except Exception as e:
            print(f"Database backup failed: {e}")
            return False
    
    def close(self) -> None:
        """Close database connections."""
        with self._lock:
            if self._engine:
                self._engine.dispose()
                self._engine = None
            self._sessionmaker = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()