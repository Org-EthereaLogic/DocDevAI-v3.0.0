"""
Main LocalStorageSystem implementation for M002.

Provides high-performance SQLite storage with document versioning,
metadata management, and transactional integrity.
"""

import os
import uuid
import json
import logging
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Union, Tuple
from contextlib import contextmanager
from functools import lru_cache
import time

from sqlalchemy import (
    create_engine, select, update, delete, and_, or_, func,
    event, pool, text
)
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool
from pydantic import BaseModel, Field, ValidationError

from devdocai.core.config import ConfigurationManager
from .models import (
    Base, Document, DocumentVersion, Metadata, SearchIndex,
    AuditLog, DocumentStatus, DocumentType
)
from .utils import (
    generate_uuid, calculate_diff, tokenize_content,
    sanitize_path, ensure_directory
)

logger = logging.getLogger(__name__)


class StorageConfig(BaseModel):
    """Configuration for storage system."""
    db_path: str = Field(default="./data/devdocai.db")
    pool_size: int = Field(default=20, ge=5, le=100)
    max_overflow: int = Field(default=40, ge=0, le=200)
    pool_timeout: float = Field(default=30.0, ge=1.0, le=300.0)
    pool_recycle: int = Field(default=3600, ge=60, le=7200)
    enable_wal: bool = Field(default=True)
    enable_fts: bool = Field(default=True)
    backup_enabled: bool = Field(default=True)
    backup_interval: int = Field(default=3600, ge=300, le=86400)
    cache_size: int = Field(default=10000, ge=1000, le=100000)
    page_size: int = Field(default=4096, ge=512, le=65536)


class DocumentData(BaseModel):
    """Input data for document operations."""
    title: str = Field(min_length=1, max_length=255)
    content: Optional[str] = None
    type: DocumentType = Field(default=DocumentType.OTHER)
    format: str = Field(default="markdown")
    language: str = Field(default="en", pattern="^[a-z]{2}$")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source_path: Optional[str] = None
    
    
class QueryParams(BaseModel):
    """Parameters for document queries."""
    type: Optional[DocumentType] = None
    status: Optional[DocumentStatus] = None
    search_text: Optional[str] = None
    metadata_filters: Dict[str, Any] = Field(default_factory=dict)
    order_by: str = Field(default="updated_at")
    order_desc: bool = Field(default=True)
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class LocalStorageSystem:
    """
    Main storage system for DevDocAI with SQLite backend.
    
    Provides CRUD operations, versioning, metadata management,
    and full-text search capabilities.
    """
    
    def __init__(self, config_manager: Optional[ConfigurationManager] = None):
        """Initialize storage system with configuration."""
        self.config_manager = config_manager or ConfigurationManager()
        self._load_config()
        self._init_database()
        self._init_session()
        self._operation_count = 0
        self._start_time = time.time()
        
    def _load_config(self):
        """Load storage configuration from config manager."""
        config_dict = self.config_manager.get('storage', None) or {}
        if not config_dict:
            # Use defaults
            data_path = self.config_manager.get('paths.data', None) or './data'
            config_dict = {
                'db_path': str(Path(data_path) / 'devdocai.db')
            }
        
        try:
            self.config = StorageConfig(**config_dict)
        except ValidationError as e:
            logger.error(f"Invalid storage configuration: {e}")
            self.config = StorageConfig()
        
        # Ensure database directory exists
        db_dir = Path(self.config.db_path).parent
        ensure_directory(db_dir)
        
    def _init_database(self):
        """Initialize SQLite database with optimizations."""
        # Build connection URL
        db_url = f"sqlite:///{self.config.db_path}"
        
        # Create engine with connection pooling
        self.engine = create_engine(
            db_url,
            poolclass=QueuePool,
            pool_size=self.config.pool_size,
            max_overflow=self.config.max_overflow,
            pool_timeout=self.config.pool_timeout,
            pool_recycle=self.config.pool_recycle,
            echo=False,
            connect_args={
                'check_same_thread': False,
                'timeout': 30.0
            }
        )
        
        # Apply SQLite optimizations
        @event.listens_for(Engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            
            # Performance optimizations
            if self.config.enable_wal:
                cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute(f"PRAGMA cache_size={self.config.cache_size}")
            cursor.execute(f"PRAGMA page_size={self.config.page_size}")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA temp_store=MEMORY")
            cursor.execute("PRAGMA mmap_size=268435456")  # 256MB memory map
            
            # Enable foreign keys
            cursor.execute("PRAGMA foreign_keys=ON")
            
            cursor.close()
        
        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)
        
        # Create FTS virtual table if enabled
        if self.config.enable_fts:
            self._init_fts()
    
    def _init_fts(self):
        """Initialize full-text search virtual table."""
        with self.engine.connect() as conn:
            # Check if FTS table exists
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='documents_fts'"
            )).fetchone()
            
            if not result:
                # Create FTS5 virtual table
                conn.execute(text("""
                    CREATE VIRTUAL TABLE documents_fts USING fts5(
                        document_id UNINDEXED,
                        title,
                        content,
                        metadata,
                        tokenize='porter unicode61'
                    )
                """))
                conn.commit()
                logger.info("Created FTS5 virtual table for full-text search")
    
    def _init_session(self):
        """Initialize SQLAlchemy session factory."""
        session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.Session = scoped_session(session_factory)
    
    @contextmanager
    def get_session(self) -> Session:
        """Get a database session with automatic cleanup."""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    @contextmanager
    def transaction(self) -> Session:
        """Execute operations within a transaction."""
        with self.get_session() as session:
            yield session
    
    # ==================== DOCUMENT OPERATIONS ====================
    
    def create_document(self, data: DocumentData, user: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new document with initial version.
        
        Args:
            data: Document data
            user: Optional user identifier
            
        Returns:
            Created document dictionary
        """
        start_time = time.time()
        
        with self.transaction() as session:
            # Create document
            doc = Document(
                uuid=generate_uuid(),
                title=data.title,
                content=data.content,
                type=data.type.value if isinstance(data.type, DocumentType) else data.type,
                format=data.format,
                language=data.language,
                source_path=data.source_path,
                status=DocumentStatus.DRAFT
            )
            
            session.add(doc)
            session.flush()  # Get the document ID
            
            # Create initial version
            if data.content:
                version = DocumentVersion(
                    document_id=doc.id,
                    version_number=1,
                    content=data.content,
                    content_hash=doc.content_hash,
                    created_by=user,
                    comment="Initial version"
                )
                session.add(version)
            
            # Add metadata
            for key, value in data.metadata.items():
                meta = Metadata(
                    document_id=doc.id,
                    key=key
                )
                meta.set_typed_value(value)
                session.add(meta)
            
            # Update search index
            if self.config.enable_fts:
                self._update_search_index(session, doc)
            
            # Audit log
            self._audit_log(
                session,
                operation="CREATE",
                entity_type="document",
                entity_id=doc.id,
                new_value={'uuid': doc.uuid, 'title': doc.title},
                user=user,
                duration_ms=int((time.time() - start_time) * 1000)
            )
            
            self._operation_count += 1
            return doc.to_dict()
    
    def get_document(self, document_id: Optional[int] = None, 
                    uuid: Optional[str] = None,
                    include_content: bool = True) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document by ID or UUID.
        
        Args:
            document_id: Document database ID
            uuid: Document UUID
            include_content: Whether to include full content
            
        Returns:
            Document dictionary or None if not found
        """
        if not document_id and not uuid:
            raise ValueError("Either document_id or uuid must be provided")
        
        with self.get_session() as session:
            query = session.query(Document)
            
            if document_id:
                query = query.filter(Document.id == document_id)
            else:
                query = query.filter(Document.uuid == uuid)
            
            doc = query.first()
            
            if doc:
                # Update access tracking
                doc.last_accessed = datetime.utcnow()
                doc.access_count += 1
                session.commit()
                
                result = doc.to_dict()
                if include_content:
                    result['content'] = doc.content
                
                # Include metadata
                result['metadata'] = {
                    m.key: m.get_typed_value() 
                    for m in doc.metadata_entries
                }
                
                self._operation_count += 1
                return result
            
            return None
    
    def update_document(self, document_id: int, data: DocumentData,
                       user: Optional[str] = None,
                       version_comment: Optional[str] = None) -> Dict[str, Any]:
        """
        Update a document and create a new version.
        
        Args:
            document_id: Document ID
            data: Updated document data
            user: User making the update
            version_comment: Optional version comment
            
        Returns:
            Updated document dictionary
        """
        start_time = time.time()
        
        with self.transaction() as session:
            doc = session.query(Document).filter(Document.id == document_id).first()
            
            if not doc:
                raise ValueError(f"Document {document_id} not found")
            
            # Store old values for audit
            old_values = {
                'title': doc.title,
                'type': doc.type,
                'content_hash': doc.content_hash
            }
            
            # Get current version number
            current_version = session.query(func.max(DocumentVersion.version_number))\
                .filter(DocumentVersion.document_id == document_id).scalar() or 0
            
            # Update document fields
            doc.title = data.title
            doc.type = data.type.value if isinstance(data.type, DocumentType) else data.type
            doc.format = data.format
            doc.language = data.language
            
            # Update content if changed
            if data.content and data.content != doc.content:
                # Create new version
                version = DocumentVersion(
                    document_id=doc.id,
                    version_number=current_version + 1,
                    content=data.content,
                    content_hash=hashlib.sha256(data.content.encode()).hexdigest(),
                    created_by=user,
                    comment=version_comment or "Updated content",
                    is_major=current_version > 0 and (current_version + 1) % 10 == 0
                )
                
                # Calculate diff if previous version exists
                if current_version > 0:
                    prev_version = session.query(DocumentVersion)\
                        .filter(DocumentVersion.document_id == document_id,
                               DocumentVersion.version_number == current_version).first()
                    if prev_version:
                        version.diff_from_previous = calculate_diff(
                            prev_version.content, data.content
                        )
                
                session.add(version)
                
                # Update document content
                doc.content = data.content
            
            # Update metadata
            if data.metadata:
                # Remove existing metadata
                session.query(Metadata).filter(Metadata.document_id == document_id).delete()
                
                # Add new metadata
                for key, value in data.metadata.items():
                    meta = Metadata(document_id=doc.id, key=key)
                    meta.set_typed_value(value)
                    session.add(meta)
            
            # Update search index
            if self.config.enable_fts:
                self._update_search_index(session, doc)
            
            # Audit log
            self._audit_log(
                session,
                operation="UPDATE",
                entity_type="document",
                entity_id=doc.id,
                old_value=old_values,
                new_value={'title': doc.title, 'type': doc.type, 'content_hash': doc.content_hash},
                user=user,
                duration_ms=int((time.time() - start_time) * 1000)
            )
            
            self._operation_count += 1
            return doc.to_dict()
    
    def delete_document(self, document_id: int, user: Optional[str] = None,
                       hard_delete: bool = False) -> bool:
        """
        Delete a document (soft or hard delete).
        
        Args:
            document_id: Document ID
            user: User performing deletion
            hard_delete: If True, permanently delete; otherwise soft delete
            
        Returns:
            Success status
        """
        start_time = time.time()
        
        with self.transaction() as session:
            doc = session.query(Document).filter(Document.id == document_id).first()
            
            if not doc:
                return False
            
            if hard_delete:
                # Permanently delete document and all related data
                session.delete(doc)
                operation = "DELETE_HARD"
            else:
                # Soft delete - just change status
                doc.status = DocumentStatus.DELETED
                operation = "DELETE_SOFT"
            
            # Audit log
            self._audit_log(
                session,
                operation=operation,
                entity_type="document",
                entity_id=document_id,
                old_value={'uuid': doc.uuid, 'title': doc.title},
                user=user,
                duration_ms=int((time.time() - start_time) * 1000)
            )
            
            self._operation_count += 1
            return True
    
    def list_documents(self, params: Optional[QueryParams] = None) -> Dict[str, Any]:
        """
        List documents with filtering and pagination.
        
        Args:
            params: Query parameters
            
        Returns:
            Dictionary with documents and pagination info
        """
        params = params or QueryParams()
        
        with self.get_session() as session:
            query = session.query(Document)
            
            # Apply filters
            if params.type:
                query = query.filter(Document.type == params.type.value)
            
            if params.status:
                query = query.filter(Document.status == params.status.value)
            else:
                # Default: exclude deleted documents
                query = query.filter(Document.status != DocumentStatus.DELETED)
            
            # Full-text search
            if params.search_text and self.config.enable_fts:
                # Use FTS for search
                fts_results = session.execute(text("""
                    SELECT document_id FROM documents_fts
                    WHERE documents_fts MATCH :search_text
                    ORDER BY rank
                """), {'search_text': params.search_text}).fetchall()
                
                doc_ids = [r[0] for r in fts_results]
                if doc_ids:
                    query = query.filter(Document.id.in_(doc_ids))
                else:
                    # No matches
                    return {'documents': [], 'total': 0, 'page': 1, 'pages': 0}
            
            # Metadata filters
            if params.metadata_filters:
                for key, value in params.metadata_filters.items():
                    subquery = session.query(Metadata.document_id)\
                        .filter(Metadata.key == key, Metadata.value == str(value))
                    query = query.filter(Document.id.in_(subquery))
            
            # Get total count
            total = query.count()
            
            # Apply ordering
            order_column = getattr(Document, params.order_by, Document.updated_at)
            if params.order_desc:
                query = query.order_by(order_column.desc())
            else:
                query = query.order_by(order_column)
            
            # Apply pagination
            query = query.limit(params.limit).offset(params.offset)
            
            # Execute query
            documents = [doc.to_dict() for doc in query.all()]
            
            self._operation_count += 1
            
            return {
                'documents': documents,
                'total': total,
                'page': (params.offset // params.limit) + 1,
                'pages': (total + params.limit - 1) // params.limit
            }
    
    # ==================== VERSION OPERATIONS ====================
    
    def get_versions(self, document_id: int) -> List[Dict[str, Any]]:
        """Get all versions of a document."""
        with self.get_session() as session:
            versions = session.query(DocumentVersion)\
                .filter(DocumentVersion.document_id == document_id)\
                .order_by(DocumentVersion.version_number.desc()).all()
            
            self._operation_count += 1
            return [v.to_dict() for v in versions]
    
    def get_version(self, document_id: int, version_number: int) -> Optional[Dict[str, Any]]:
        """Get a specific version of a document."""
        with self.get_session() as session:
            version = session.query(DocumentVersion)\
                .filter(DocumentVersion.document_id == document_id,
                       DocumentVersion.version_number == version_number).first()
            
            if version:
                result = version.to_dict()
                result['content'] = version.content
                self._operation_count += 1
                return result
            
            return None
    
    def restore_version(self, document_id: int, version_number: int,
                       user: Optional[str] = None) -> Dict[str, Any]:
        """Restore a document to a specific version."""
        with self.transaction() as session:
            # Get the version to restore
            version = session.query(DocumentVersion)\
                .filter(DocumentVersion.document_id == document_id,
                       DocumentVersion.version_number == version_number).first()
            
            if not version:
                raise ValueError(f"Version {version_number} not found for document {document_id}")
            
            # Get the document
            doc = session.query(Document).filter(Document.id == document_id).first()
            if not doc:
                raise ValueError(f"Document {document_id} not found")
            
            # Create a new version with restored content
            current_version = session.query(func.max(DocumentVersion.version_number))\
                .filter(DocumentVersion.document_id == document_id).scalar()
            
            new_version = DocumentVersion(
                document_id=document_id,
                version_number=current_version + 1,
                content=version.content,
                content_hash=version.content_hash,
                created_by=user,
                comment=f"Restored from version {version_number}"
            )
            session.add(new_version)
            
            # Update document content
            doc.content = version.content
            
            self._operation_count += 1
            return doc.to_dict()
    
    # ==================== SEARCH OPERATIONS ====================
    
    def search(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Perform full-text search across documents.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of matching documents
        """
        if not self.config.enable_fts:
            logger.warning("Full-text search is disabled")
            return []
        
        with self.get_session() as session:
            # Execute FTS query
            results = session.execute(text("""
                SELECT d.*, 
                       highlight(documents_fts, 1, '<mark>', '</mark>') as title_highlight,
                       highlight(documents_fts, 2, '<mark>', '</mark>') as content_highlight,
                       rank
                FROM documents_fts f
                JOIN documents d ON f.document_id = d.id
                WHERE documents_fts MATCH :query
                AND d.status != :deleted_status
                ORDER BY rank
                LIMIT :limit
            """), {
                'query': query,
                'deleted_status': DocumentStatus.DELETED,
                'limit': limit
            }).fetchall()
            
            documents = []
            for row in results:
                doc_dict = {
                    'id': row.id,
                    'uuid': row.uuid,
                    'title': row.title,
                    'type': row.type,
                    'title_highlight': row.title_highlight,
                    'content_highlight': row.content_highlight[:200] + '...' if len(row.content_highlight) > 200 else row.content_highlight,
                    'score': abs(row.rank)  # FTS5 rank is negative
                }
                documents.append(doc_dict)
            
            self._operation_count += 1
            return documents
    
    # ==================== UTILITY OPERATIONS ====================
    
    def _update_search_index(self, session: Session, document: Document):
        """Update FTS index for a document."""
        if not self.config.enable_fts:
            return
        
        # Get metadata as text
        metadata_text = ' '.join([
            f"{m.key}:{m.value}" for m in document.metadata_entries
        ])
        
        # Delete existing FTS entry
        session.execute(text("""
            DELETE FROM documents_fts WHERE document_id = :doc_id
        """), {'doc_id': document.id})
        
        # Insert new FTS entry
        session.execute(text("""
            INSERT INTO documents_fts (document_id, title, content, metadata)
            VALUES (:doc_id, :title, :content, :metadata)
        """), {
            'doc_id': document.id,
            'title': document.title,
            'content': document.content or '',
            'metadata': metadata_text
        })
    
    def _audit_log(self, session: Session, operation: str, entity_type: str,
                  entity_id: Optional[int] = None, old_value: Any = None,
                  new_value: Any = None, user: Optional[str] = None,
                  duration_ms: Optional[int] = None):
        """Create an audit log entry."""
        audit = AuditLog(
            operation=operation,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value,
            user=user,
            session_id=str(uuid.uuid4()),
            duration_ms=duration_ms,
            status='success'
        )
        session.add(audit)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get storage system statistics."""
        with self.get_session() as session:
            stats = {
                'total_documents': session.query(Document).count(),
                'active_documents': session.query(Document)\
                    .filter(Document.status == DocumentStatus.ACTIVE).count(),
                'total_versions': session.query(DocumentVersion).count(),
                'total_metadata': session.query(Metadata).count(),
                'database_size': os.path.getsize(self.config.db_path) if os.path.exists(self.config.db_path) else 0,
                'operations_count': self._operation_count,
                'uptime_seconds': int(time.time() - self._start_time),
                'operations_per_second': self._operation_count / max(1, time.time() - self._start_time)
            }
            
            # Get document type distribution
            type_dist = session.query(Document.type, func.count(Document.id))\
                .group_by(Document.type).all()
            stats['document_types'] = {t: c for t, c in type_dist}
            
            return stats
    
    def optimize(self):
        """Optimize database performance."""
        with self.engine.connect() as conn:
            conn.execute(text("VACUUM"))
            conn.execute(text("ANALYZE"))
            conn.commit()
            logger.info("Database optimization completed")
    
    def close(self):
        """Close storage system and cleanup resources."""
        self.Session.remove()
        self.engine.dispose()
        logger.info("Storage system closed")