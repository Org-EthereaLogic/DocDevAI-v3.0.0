"""
M002 Local Storage System - Repository Layer

Repository pattern implementation for document operations:
- Document CRUD operations with encryption
- Full-text search and filtering
- Metadata management
- Integration with M001 ConfigurationManager
"""

import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text
from sqlalchemy.exc import IntegrityError

from devdocai.storage.database import DatabaseManager, DocumentTable
from devdocai.storage.models import (
    Document, 
    DocumentMetadata, 
    DocumentSearchResult,
    StorageStats,
    ContentType,
    DocumentStatus
)
from devdocai.storage.encryption import DocumentEncryption, EncryptionError
from devdocai.core.config import ConfigurationManager


class RepositoryError(Exception):
    """Repository operation errors."""
    pass


class DocumentRepository:
    """
    Document repository implementing CRUD operations.
    
    Features:
    - Encrypted document storage
    - Full-text search with SQLite FTS5
    - Metadata filtering and search
    - Soft delete support
    - Performance optimizations for different memory modes
    """
    
    def __init__(self, db_manager: DatabaseManager, config: ConfigurationManager):
        """
        Initialize document repository.
        
        Args:
            db_manager: Database manager instance
            config: M001 ConfigurationManager instance
        """
        self.db_manager = db_manager
        self.config = config
        self.encryption = DocumentEncryption(config)
        
        # Cache for performance
        self._metadata_cache: Dict[str, DocumentMetadata] = {}
        self._cache_enabled = config.get('memory_mode').value in ['enhanced', 'performance']
    
    def create_document(self, document: Document) -> Document:
        """
        Create a new document.
        
        Args:
            document: Document model to create
            
        Returns:
            Created document with timestamps
            
        Raises:
            RepositoryError: If creation fails
        """
        try:
            with self.db_manager.get_session() as session:
                return self.create_document_with_session(document, session)
        except Exception as e:
            raise RepositoryError(f"Document creation failed: {e}")
    
    def create_document_with_session(self, document: Document, session: Session) -> Document:
        """
        Create a document within an existing session (for batch operations).
        
        Args:
            document: Document model to create
            session: Database session to use
            
        Returns:
            Created document with timestamps
        """
        # Check for existing document (including soft-deleted)
        existing = session.query(DocumentTable).filter_by(
            id=document.id
        ).first()

        if existing:
            if existing.is_deleted:
                # Revive soft-deleted document by updating fields
                document.update_timestamp()
                encrypted_content = self.encryption.encrypt_content(
                    document.content,
                    document.id
                )
                encrypted_metadata = None
                if document.metadata:
                    metadata_dict = document.metadata.model_dump()
                    encrypted_metadata = self.encryption.encrypt_metadata(metadata_dict)

                existing.title = document.title
                existing.content = encrypted_content
                existing.content_type = document.content_type.value
                existing.status = document.status.value
                existing.source_path = str(document.source_path) if document.source_path else None
                existing.checksum = document.checksum
                existing.metadata_json = encrypted_metadata
                existing.created_at = existing.created_at or document.created_at
                existing.updated_at = document.updated_at
                existing.is_deleted = False
                existing.deleted_at = None

                session.commit()

                # Update cache
                if self._cache_enabled and document.metadata:
                    self._metadata_cache[document.id] = document.metadata

                return document
            else:
                raise RepositoryError(f"Document with ID '{document.id}' already exists")
        
        # Encrypt content if encryption enabled
        encrypted_content = self.encryption.encrypt_content(
            document.content, 
            document.id
        )
        
        # Encrypt metadata if present
        encrypted_metadata = None
        if document.metadata:
            metadata_dict = document.metadata.model_dump()
            encrypted_metadata = self.encryption.encrypt_metadata(metadata_dict)
        
        # Create database record
        db_document = DocumentTable(
            id=document.id,
            title=document.title,
            content=encrypted_content,
            content_type=document.content_type.value,
            status=document.status.value,
            source_path=str(document.source_path) if document.source_path else None,
            checksum=document.checksum,
            metadata_json=encrypted_metadata,
            created_at=document.created_at,
            updated_at=document.updated_at,
            is_deleted=False
        )
        
        session.add(db_document)
        session.commit()
        
        # Update cache
        if self._cache_enabled and document.metadata:
            self._metadata_cache[document.id] = document.metadata
        
        # Return document with updated timestamps (ensure timezone aware)
        if db_document.created_at.tzinfo is None:
            document.created_at = db_document.created_at.replace(tzinfo=timezone.utc)
        else:
            document.created_at = db_document.created_at
        
        if db_document.updated_at.tzinfo is None:
            document.updated_at = db_document.updated_at.replace(tzinfo=timezone.utc)
        else:
            document.updated_at = db_document.updated_at
        
        return document
    
    def get_document(self, document_id: str) -> Optional[Document]:
        """
        Retrieve a document by ID.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Document model or None if not found
        """
        try:
            with self.db_manager.get_session() as session:
                db_document = session.query(DocumentTable).filter_by(
                    id=document_id,
                    is_deleted=False
                ).first()
                
                if not db_document:
                    return None
                
                return self._convert_db_to_model(db_document)
                
        except Exception as e:
            raise RepositoryError(f"Document retrieval failed: {e}")

    def get_documents_by_ids(self, document_ids: List[str]) -> List[Optional[Document]]:
        """
        Retrieve multiple documents by their IDs.

        Args:
            document_ids: A list of document identifiers.

        Returns:
            A list of Document models. If a document ID is not found, the
            corresponding item in the list is None.
        """
        try:
            with self.db_manager.get_session() as session:
                db_documents = session.query(DocumentTable).filter(
                    DocumentTable.id.in_(document_ids),
                    DocumentTable.is_deleted == False
                ).all()

                docs_map = {doc.id: self._convert_db_to_model(doc) for doc in db_documents}
                
                # Return documents in the same order as requested IDs
                return [docs_map.get(doc_id) for doc_id in document_ids]

        except Exception as e:
            raise RepositoryError(f"Batch document retrieval failed: {e}")
    
    def update_document(self, document: Document) -> Optional[Document]:
        """
        Update an existing document.
        
        Args:
            document: Updated document model
            
        Returns:
            Updated document or None if not found
        """
        try:
            with self.db_manager.get_session() as session:
                db_document = session.query(DocumentTable).filter_by(
                    id=document.id,
                    is_deleted=False
                ).first()
                
                if not db_document:
                    return None
                
                # Update document fields
                document.update_timestamp()
                
                # Encrypt content
                encrypted_content = self.encryption.encrypt_content(
                    document.content,
                    document.id
                )
                
                # Encrypt metadata if present
                encrypted_metadata = None
                if document.metadata:
                    metadata_dict = document.metadata.model_dump()
                    encrypted_metadata = self.encryption.encrypt_metadata(metadata_dict)
                
                # Update database record
                db_document.title = document.title
                db_document.content = encrypted_content
                db_document.content_type = document.content_type.value
                db_document.status = document.status.value
                db_document.source_path = str(document.source_path) if document.source_path else None
                db_document.checksum = document.checksum
                db_document.metadata_json = encrypted_metadata
                db_document.updated_at = document.updated_at
                
                session.commit()
                
                # Update cache
                if self._cache_enabled:
                    if document.metadata:
                        self._metadata_cache[document.id] = document.metadata
                    else:
                        self._metadata_cache.pop(document.id, None)
                
                return document
                
        except EncryptionError as e:
            raise RepositoryError(f"Document encryption failed: {e}")
        except Exception as e:
            raise RepositoryError(f"Document update failed: {e}")
    
    def delete_document(self, document_id: str, soft_delete: bool = True) -> bool:
        """
        Delete a document.
        
        Args:
            document_id: Document identifier
            soft_delete: If True, mark as deleted; if False, physically remove
            
        Returns:
            True if document was deleted, False if not found
        """
        try:
            with self.db_manager.get_session() as session:
                db_document = session.query(DocumentTable).filter_by(
                    id=document_id,
                    is_deleted=False
                ).first()
                
                if not db_document:
                    return False
                
                if soft_delete:
                    # Soft delete - mark as deleted
                    db_document.is_deleted = True
                    db_document.deleted_at = datetime.now(timezone.utc)
                else:
                    # Hard delete - physically remove
                    session.delete(db_document)
                
                session.commit()
                
                # Clear from cache
                if self._cache_enabled:
                    self._metadata_cache.pop(document_id, None)
                
                return True
                
        except Exception as e:
            raise RepositoryError(f"Document deletion failed: {e}")
    
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
            List of document models
        """
        try:
            with self.db_manager.get_session() as session:
                query = session.query(DocumentTable).filter_by(is_deleted=False)
                
                # Apply filters
                if status:
                    query = query.filter(DocumentTable.status == status.value)
                
                if content_type:
                    query = query.filter(DocumentTable.content_type == content_type.value)
                
                # Apply sorting
                if hasattr(DocumentTable, sort_by):
                    sort_column = getattr(DocumentTable, sort_by)
                    if sort_desc:
                        query = query.order_by(sort_column.desc())
                    else:
                        query = query.order_by(sort_column.asc())
                
                # Apply pagination
                if offset > 0:
                    query = query.offset(offset)
                
                if limit:
                    query = query.limit(limit)
                
                db_documents = query.all()
                
                # Convert to models
                return [self._convert_db_to_model(db_doc) for db_doc in db_documents]
                
        except Exception as e:
            raise RepositoryError(f"Document listing failed: {e}")
    
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
        try:
            with self.db_manager.get_session() as session:
                # Try FTS5 search first
                if hasattr(self.db_manager, '_has_fts') and self.db_manager._has_fts:
                    return self._fts_search(session, query, limit, offset)
                else:
                    return self._basic_search(session, query, limit, offset)
                    
        except Exception as e:
            raise RepositoryError(f"Document search failed: {e}")
    
    def _fts_search(
        self,
        session: Session,
        query: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[DocumentSearchResult]:
        """Full-text search using SQLite FTS5."""
        # Escape query for FTS5
        escaped_query = query.replace('"', '""')
        fts_query = f'"{escaped_query}"'
        
        # Build FTS query - note that we need to match the actual table column names
        sql_query = text("""
            SELECT d.*, -1.0 as rank
            FROM documents d
            WHERE d.id IN (
                SELECT document_id 
                FROM documents_fts 
                WHERE documents_fts MATCH :query
            )
            AND d.is_deleted = 0
            ORDER BY d.updated_at DESC
            LIMIT :limit OFFSET :offset
        """)
        
        result = session.execute(
            sql_query,
            {
                'query': fts_query,
                'limit': limit or 100,
                'offset': offset
            }
        )
        
        search_results = []
        for row in result:
            # Convert row to DocumentTable-like object
            db_document = DocumentTable()
            for column in DocumentTable.__table__.columns:
                if hasattr(row, column.name):
                    setattr(db_document, column.name, getattr(row, column.name))
            
            document = self._convert_db_to_model(db_document)
            
            # Calculate relevance score (FTS rank is negative, convert to 0-1 range)
            relevance = max(0.0, min(1.0, -row.rank / 10.0))
            
            search_result = DocumentSearchResult(
                document=document,
                relevance_score=relevance,
                matched_fields=['title', 'content'],
                snippet=self._generate_snippet(document.content, query)
            )
            
            search_results.append(search_result)
        
        return search_results
    
    def _basic_search(
        self,
        session: Session,
        query: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[DocumentSearchResult]:
        """Basic search using LIKE queries - searches in decrypted content."""
        search_pattern = f"%{query}%"
        
        # Get all active documents
        db_documents = session.query(DocumentTable).filter(
            DocumentTable.is_deleted == False
        ).order_by(DocumentTable.updated_at.desc())
        
        search_results = []
        for db_document in db_documents:
            document = self._convert_db_to_model(db_document)
            
            # Search in both title and content (decrypted)
            query_lower = query.lower()
            title_match = query_lower in document.title.lower()
            content_match = query_lower in document.content.lower()
            
            if title_match or content_match:
                # Calculate relevance score
                relevance = 0.5  # Base relevance
                matched_fields = []
                
                if title_match:
                    relevance = 0.8
                    matched_fields.append('title')
                
                if content_match:
                    if not title_match:
                        relevance = 0.6
                    matched_fields.append('content')
                
                search_result = DocumentSearchResult(
                    document=document,
                    relevance_score=relevance,
                    matched_fields=matched_fields,
                    snippet=self._generate_snippet(document.content, query)
                )
                
                search_results.append(search_result)
                
                # Apply limit (offset applied later)
                if limit and len(search_results) >= (offset + limit):
                    break
        
        # Apply offset to results
        return search_results[offset:offset + (limit or len(search_results))]
    
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
            tags: Filter by tags (documents must have any of these tags)
            category: Filter by category
            author: Filter by author
            custom_fields: Filter by custom field values
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of matching documents
        """
        try:
            with self.db_manager.get_session() as session:
                db_documents = session.query(DocumentTable).filter_by(
                    is_deleted=False
                ).order_by(DocumentTable.updated_at.desc()).offset(offset)
                
                if limit:
                    db_documents = db_documents.limit(limit)
                
                results = []
                for db_document in db_documents:
                    # Convert to model to access decrypted metadata
                    document = self._convert_db_to_model(db_document)
                    
                    if not document.metadata:
                        continue
                    
                    # Check metadata criteria
                    matches = True
                    
                    if tags:
                        # Document must have at least one of the specified tags
                        if not any(tag.lower() in document.metadata.tags for tag in tags):
                            matches = False
                    
                    if category and document.metadata.category != category:
                        matches = False
                    
                    if author and document.metadata.author != author:
                        matches = False
                    
                    if custom_fields:
                        for key, value in custom_fields.items():
                            if document.metadata.custom_fields.get(key) != value:
                                matches = False
                                break
                    
                    if matches:
                        results.append(document)
                
                return results
                
        except Exception as e:
            raise RepositoryError(f"Metadata search failed: {e}")
    
    def _convert_db_to_model(self, db_document: DocumentTable) -> Document:
        """Convert database model to Pydantic model."""
        try:
            # Decrypt content
            decrypted_content = self.encryption.decrypt_content(
                db_document.content,
                db_document.id
            )
            
            # Decrypt metadata if present
            metadata = None
            if db_document.metadata_json:
                try:
                    metadata_dict = self.encryption.decrypt_metadata(
                        db_document.metadata_json
                    )
                    metadata = DocumentMetadata(**metadata_dict)
                except Exception as e:
                    print(f"Warning: Failed to decrypt metadata for document {db_document.id}: {e}")
            
            # Convert source_path back to Path if present
            source_path = None
            if db_document.source_path:
                source_path = Path(db_document.source_path)
            
            # Ensure datetimes are timezone-aware
            created_at = db_document.created_at
            if created_at and hasattr(created_at, 'tzinfo') and created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            
            updated_at = db_document.updated_at
            if updated_at and hasattr(updated_at, 'tzinfo') and updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)
            
            return Document(
                id=db_document.id,
                title=db_document.title,
                content=decrypted_content,
                content_type=ContentType(db_document.content_type),
                status=DocumentStatus(db_document.status),
                created_at=created_at,
                updated_at=updated_at,
                metadata=metadata,
                source_path=source_path,
                checksum=db_document.checksum
            )
            
        except EncryptionError as e:
            raise RepositoryError(f"Failed to decrypt document {db_document.id}: {e}")
    
    def _generate_snippet(self, content: str, query: str, max_length: int = 200) -> str:
        """Generate content snippet showing search context."""
        query_lower = query.lower()
        content_lower = content.lower()
        
        # Find first occurrence of query
        index = content_lower.find(query_lower)
        if index == -1:
            # Query not found, return beginning of content
            return content[:max_length] + ("..." if len(content) > max_length else "")
        
        # Calculate snippet bounds
        start = max(0, index - max_length // 3)
        end = min(len(content), index + len(query) + max_length * 2 // 3)
        
        snippet = content[start:end]
        
        # Add ellipsis if needed
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."
        
        return snippet
    
    def get_storage_stats(self) -> StorageStats:
        """
        Get storage system statistics.
        
        Returns:
            StorageStats model with system information
        """
        try:
            with self.db_manager.get_session() as session:
                # Count total documents
                total_docs = session.query(func.count(DocumentTable.id)).filter_by(
                    is_deleted=False
                ).scalar()
                
                # Count by status
                status_counts = {}
                for status in DocumentStatus:
                    count = session.query(func.count(DocumentTable.id)).filter_by(
                        is_deleted=False,
                        status=status.value
                    ).scalar()
                    status_counts[status.value] = count
                
                # Count by content type
                type_counts = {}
                for content_type in ContentType:
                    count = session.query(func.count(DocumentTable.id)).filter_by(
                        is_deleted=False,
                        content_type=content_type.value
                    ).scalar()
                    if count > 0:
                        type_counts[content_type.value] = count
                
                # Calculate total size (approximate)
                # Note: This is the encrypted size, not actual content size
                db_stats = self.db_manager.get_database_stats()
                total_size = db_stats.get('database_size_bytes', 0)
                
                # Calculate average document size
                avg_size = total_size / total_docs if total_docs > 0 else 0
                
                return StorageStats(
                    total_documents=total_docs,
                    total_size_bytes=total_size,
                    documents_by_status=status_counts,
                    documents_by_type=type_counts,
                    average_document_size=avg_size,
                    last_updated=datetime.now(timezone.utc)
                )
                
        except Exception as e:
            raise RepositoryError(f"Failed to get storage stats: {e}")
    
    def clear_cache(self) -> None:
        """Clear repository cache."""
        if self._cache_enabled:
            self._metadata_cache.clear()
