"""
SQLAlchemy models for M002 Local Storage System.

Defines the database schema for documents, versions, metadata, and indexes.
"""

import json
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from sqlalchemy import (
    Column, String, Integer, Text, DateTime, Boolean, 
    ForeignKey, Index, JSON, Float, LargeBinary, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship, validates
from sqlalchemy.sql import func

Base = declarative_base()


class DocumentStatus(str, Enum):
    """Document lifecycle states."""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class DocumentType(str, Enum):
    """Supported document types."""
    TECHNICAL = "technical"
    API = "api"
    USER_GUIDE = "user_guide"
    TUTORIAL = "tutorial"
    REFERENCE = "reference"
    DESIGN = "design"
    README = "readme"
    CHANGELOG = "changelog"
    OTHER = "other"


class Document(Base):
    """Main document entity with versioning support."""
    __tablename__ = 'documents'
    
    # Primary identifiers
    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(36), unique=True, nullable=False, index=True)
    
    # Document metadata
    title = Column(String(255), nullable=False, index=True)
    type = Column(String(50), nullable=False, default=DocumentType.OTHER)
    status = Column(String(20), nullable=False, default=DocumentStatus.DRAFT)
    
    # Content and structure
    content = Column(Text, nullable=True)
    content_hash = Column(String(64), nullable=True, index=True)
    format = Column(String(20), default='markdown')
    language = Column(String(10), default='en')
    
    # File system references
    file_path = Column(String(500), nullable=True)
    source_path = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_accessed = Column(DateTime, nullable=True)
    
    # Relationships
    versions = relationship("DocumentVersion", back_populates="document", 
                          cascade="all, delete-orphan", lazy='dynamic')
    metadata_entries = relationship("Metadata", back_populates="document",
                                  cascade="all, delete-orphan", lazy='dynamic')
    
    # Performance tracking
    access_count = Column(Integer, default=0)
    size_bytes = Column(Integer, nullable=True)
    
    # Quality metrics
    quality_score = Column(Float, nullable=True)
    completeness_score = Column(Float, nullable=True)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_document_type_status', 'type', 'status'),
        Index('idx_document_created', 'created_at'),
        Index('idx_document_updated', 'updated_at'),
    )
    
    @validates('content')
    def update_content_hash(self, key, content):
        """Automatically update content hash when content changes."""
        if content:
            self.content_hash = hashlib.sha256(content.encode()).hexdigest()
            self.size_bytes = len(content.encode())
        return content
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert document to dictionary representation."""
        return {
            'id': self.id,
            'uuid': self.uuid,
            'title': self.title,
            'type': self.type,
            'status': self.status,
            'format': self.format,
            'language': self.language,
            'file_path': self.file_path,
            'source_path': self.source_path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'access_count': self.access_count,
            'size_bytes': self.size_bytes,
            'quality_score': self.quality_score,
            'completeness_score': self.completeness_score,
            'version_count': self.versions.count() if self.versions else 0
        }


class DocumentVersion(Base):
    """Document version tracking for history and rollback."""
    __tablename__ = 'document_versions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey('documents.id'), nullable=False)
    version_number = Column(Integer, nullable=False)
    
    # Version content
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)
    diff_from_previous = Column(Text, nullable=True)  # JSON diff for efficiency
    
    # Version metadata
    created_at = Column(DateTime, default=func.now(), nullable=False)
    created_by = Column(String(100), nullable=True)
    comment = Column(String(500), nullable=True)
    is_major = Column(Boolean, default=False)
    
    # Relationships
    document = relationship("Document", back_populates="versions")
    
    # Unique constraint for document version pairs
    __table_args__ = (
        UniqueConstraint('document_id', 'version_number'),
        Index('idx_version_created', 'created_at'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert version to dictionary representation."""
        return {
            'id': self.id,
            'document_id': self.document_id,
            'version_number': self.version_number,
            'content_hash': self.content_hash,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
            'comment': self.comment,
            'is_major': self.is_major
        }


class Metadata(Base):
    """Flexible metadata storage for documents."""
    __tablename__ = 'metadata'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey('documents.id'), nullable=False)
    
    # Key-value storage with type tracking
    key = Column(String(100), nullable=False, index=True)
    value = Column(Text, nullable=False)
    value_type = Column(String(20), default='string')  # string, number, boolean, json
    
    # Metadata categorization
    category = Column(String(50), nullable=True, index=True)
    is_searchable = Column(Boolean, default=True)
    is_public = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="metadata_entries")
    
    # Indexes
    __table_args__ = (
        UniqueConstraint('document_id', 'key'),
        Index('idx_metadata_key_value', 'key', 'value'),
        Index('idx_metadata_category', 'category'),
    )
    
    def get_typed_value(self) -> Any:
        """Return value with appropriate type conversion."""
        if self.value_type == 'number':
            return float(self.value)
        elif self.value_type == 'boolean':
            return self.value.lower() == 'true'
        elif self.value_type == 'json':
            return json.loads(self.value)
        return self.value
    
    def set_typed_value(self, value: Any):
        """Set value with automatic type detection."""
        if isinstance(value, bool):
            self.value = str(value)
            self.value_type = 'boolean'
        elif isinstance(value, (int, float)):
            self.value = str(value)
            self.value_type = 'number'
        elif isinstance(value, (dict, list)):
            self.value = json.dumps(value)
            self.value_type = 'json'
        else:
            self.value = str(value)
            self.value_type = 'string'


class SearchIndex(Base):
    """Full-text search index for documents."""
    __tablename__ = 'search_index'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey('documents.id'), nullable=False)
    
    # Search fields
    content_tokens = Column(Text, nullable=False)  # Tokenized content for FTS
    title_tokens = Column(Text, nullable=False)
    metadata_tokens = Column(Text, nullable=True)
    
    # Search metadata
    last_indexed = Column(DateTime, default=func.now())
    index_version = Column(Integer, default=1)
    
    # Performance optimization
    token_count = Column(Integer, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_search_document', 'document_id'),
        Index('idx_search_indexed', 'last_indexed'),
    )


class AuditLog(Base):
    """Audit trail for all storage operations."""
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Operation details
    operation = Column(String(50), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=True)
    
    # User and session tracking
    user = Column(String(100), nullable=True)
    session_id = Column(String(36), nullable=True)
    ip_address = Column(String(45), nullable=True)
    
    # Operation data
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    
    # Status and timing
    status = Column(String(20), nullable=False, default='success')
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    duration_ms = Column(Integer, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_audit_timestamp', 'timestamp'),
        Index('idx_audit_operation', 'operation'),
        Index('idx_audit_entity', 'entity_type', 'entity_id'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert audit log to dictionary representation."""
        return {
            'id': self.id,
            'operation': self.operation,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'user': self.user,
            'session_id': self.session_id,
            'status': self.status,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'duration_ms': self.duration_ms
        }