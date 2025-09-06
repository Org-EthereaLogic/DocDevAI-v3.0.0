"""
M002 Local Storage System - Document Models

Pydantic v2 models for document storage, following M001 patterns:
- Document with metadata validation
- DocumentMetadata with flexible custom fields
- Storage-optimized field definitions
- Privacy-first defaults and validation
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from pathlib import Path
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict, field_validator


class ContentType(str, Enum):
    """Supported document content types."""
    MARKDOWN = "markdown"
    PLAINTEXT = "plaintext"
    HTML = "html"
    JSON = "json"
    YAML = "yaml"
    CODE = "code"


class DocumentStatus(str, Enum):
    """Document status values."""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    DELETED = "deleted"


class DocumentMetadata(BaseModel):
    """
    Document metadata model with flexible custom fields.
    
    Follows M001 patterns for validation and privacy.
    """
    
    model_config = ConfigDict(
        validate_assignment=True,
        extra='forbid',
        str_strip_whitespace=True
    )
    
    # Core metadata fields
    tags: List[str] = Field(
        default_factory=list,
        description="Document tags for categorization"
    )
    
    category: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Document category"
    )
    
    author: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Document author"
    )
    
    version: Optional[str] = Field(
        default=None,
        max_length=50,
        pattern=r"^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9-]+)?$",
        description="Document version (semver format)"
    )
    
    language: Optional[str] = Field(
        default=None,
        max_length=10,
        description="Document language (ISO 639-1 code)"
    )
    
    priority: Optional[str] = Field(
        default="normal",
        pattern="^(low|normal|high|critical)$",
        description="Document priority level"
    )
    
    # Flexible custom fields for extensibility
    custom_fields: Dict[str, Any] = Field(
        default_factory=dict,
        description="Custom metadata fields"
    )
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        """Validate and normalize tags."""
        if not isinstance(v, list):
            raise ValueError("Tags must be a list")
        
        # Normalize tags: lowercase, strip whitespace, remove duplicates
        normalized_tags = []
        seen = set()
        for tag in v:
            if not isinstance(tag, str):
                raise ValueError("All tags must be strings")
            
            normalized_tag = tag.strip().lower()
            if normalized_tag and normalized_tag not in seen:
                normalized_tags.append(normalized_tag)
                seen.add(normalized_tag)
        
        return normalized_tags
    
    @field_validator('custom_fields')
    @classmethod
    def validate_custom_fields(cls, v):
        """Validate custom fields for security and size."""
        if not isinstance(v, dict):
            raise ValueError("Custom fields must be a dictionary")
        
        # Limit number of custom fields
        if len(v) > 50:
            raise ValueError("Maximum 50 custom fields allowed")
        
        # Validate field names and values
        for key, value in v.items():
            if not isinstance(key, str):
                raise ValueError("Custom field keys must be strings")
            
            if len(key) > 100:
                raise ValueError("Custom field keys must be <= 100 characters")
            
            # Convert value to string if not already a basic type
            if not isinstance(value, (str, int, float, bool, type(None))):
                v[key] = str(value)
            
            # Limit string value length
            if isinstance(v[key], str) and len(v[key]) > 1000:
                raise ValueError("Custom field string values must be <= 1000 characters")
        
        return v


class Document(BaseModel):
    """
    Core document model for M002 storage system.
    
    Implements privacy-first defaults and follows M001 validation patterns.
    """
    
    model_config = ConfigDict(
        validate_assignment=True,
        extra='forbid',
        str_strip_whitespace=True
    )
    
    # Core document fields
    id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Unique document identifier"
    )
    
    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Document title"
    )
    
    content: str = Field(
        ...,
        description="Document content"
    )
    
    content_type: ContentType = Field(
        default=ContentType.MARKDOWN,
        description="Document content type"
    )
    
    status: DocumentStatus = Field(
        default=DocumentStatus.DRAFT,
        description="Document status"
    )
    
    # Timestamps (automatically managed)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Document creation timestamp"
    )
    
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Document last update timestamp"
    )
    
    # Optional metadata
    metadata: Optional[DocumentMetadata] = Field(
        default=None,
        description="Document metadata"
    )
    
    # File system related fields (optional)
    source_path: Optional[Path] = Field(
        default=None,
        description="Original file path if document was imported"
    )
    
    checksum: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Content checksum for integrity verification"
    )
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        """Validate document content."""
        if not isinstance(v, str):
            raise ValueError("Content must be a string")
        
        # Check for reasonable size limits (adjustable based on memory mode)
        if len(v) > 10_000_000:  # 10MB limit
            raise ValueError("Content exceeds maximum size limit")
        
        return v
    
    @field_validator('source_path', mode='before')
    @classmethod
    def validate_source_path(cls, v):
        """Convert string paths to Path objects."""
        if v is None:
            return v
        if isinstance(v, str):
            return Path(v)
        if isinstance(v, Path):
            return v
        raise ValueError("Source path must be a string or Path object")
    
    def update_timestamp(self) -> None:
        """Update the document's updated_at timestamp."""
        self.updated_at = datetime.now(timezone.utc)
    
    def calculate_checksum(self) -> str:
        """Calculate SHA-256 checksum of document content."""
        import hashlib
        content_bytes = self.content.encode('utf-8')
        return hashlib.sha256(content_bytes).hexdigest()
    
    def update_checksum(self) -> None:
        """Update the document's checksum."""
        self.checksum = self.calculate_checksum()
    
    def verify_checksum(self) -> bool:
        """Verify document content matches stored checksum."""
        if self.checksum is None:
            return False
        return self.checksum == self.calculate_checksum()
    
    def get_size_bytes(self) -> int:
        """Get document content size in bytes."""
        return len(self.content.encode('utf-8'))
    
    def get_word_count(self) -> int:
        """Get approximate word count of document content."""
        # Simple word count - can be enhanced for different content types
        if self.content_type == ContentType.MARKDOWN:
            # Remove markdown syntax for more accurate count
            import re
            clean_content = re.sub(r'[#*`_\[\]()]+', '', self.content)
            words = clean_content.split()
        else:
            words = self.content.split()
        
        return len([word for word in words if word.strip()])
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to document metadata."""
        if self.metadata is None:
            self.metadata = DocumentMetadata()
        
        tag_normalized = tag.strip().lower()
        if tag_normalized and tag_normalized not in self.metadata.tags:
            self.metadata.tags.append(tag_normalized)
    
    def remove_tag(self, tag: str) -> bool:
        """Remove a tag from document metadata."""
        if self.metadata is None or not self.metadata.tags:
            return False
        
        tag_normalized = tag.strip().lower()
        if tag_normalized in self.metadata.tags:
            self.metadata.tags.remove(tag_normalized)
            return True
        
        return False
    
    def has_tag(self, tag: str) -> bool:
        """Check if document has a specific tag."""
        if self.metadata is None or not self.metadata.tags:
            return False
        
        tag_normalized = tag.strip().lower()
        return tag_normalized in self.metadata.tags


class DocumentSearchResult(BaseModel):
    """
    Search result model for document queries.
    """
    
    model_config = ConfigDict(
        validate_assignment=True,
        extra='forbid'
    )
    
    document: Document = Field(
        ...,
        description="Found document"
    )
    
    relevance_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Search relevance score (0.0-1.0)"
    )
    
    matched_fields: List[str] = Field(
        default_factory=list,
        description="Fields where search terms were matched"
    )
    
    snippet: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Content snippet showing match context"
    )


class StorageStats(BaseModel):
    """
    Storage system statistics model.
    """
    
    model_config = ConfigDict(
        validate_assignment=True,
        extra='forbid'
    )
    
    total_documents: int = Field(
        default=0,
        ge=0,
        description="Total number of documents"
    )
    
    total_size_bytes: int = Field(
        default=0,
        ge=0,
        description="Total storage size in bytes"
    )
    
    documents_by_status: Dict[str, int] = Field(
        default_factory=dict,
        description="Document count by status"
    )
    
    documents_by_type: Dict[str, int] = Field(
        default_factory=dict,
        description="Document count by content type"
    )
    
    average_document_size: float = Field(
        default=0.0,
        ge=0.0,
        description="Average document size in bytes"
    )
    
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When statistics were last calculated"
    )


class DocumentVersion(BaseModel):
    """
    Document version model for version history tracking.
    Prepared for future versioning feature.
    """
    
    model_config = ConfigDict(
        validate_assignment=True,
        extra='forbid'
    )
    
    version_id: str = Field(
        ...,
        description="Unique version identifier"
    )
    
    document_id: str = Field(
        ...,
        description="Associated document ID"
    )
    
    version_number: int = Field(
        ...,
        ge=1,
        description="Version number (incremental)"
    )
    
    content: str = Field(
        ...,
        description="Document content at this version"
    )
    
    title: str = Field(
        ...,
        description="Document title at this version"
    )
    
    metadata: Optional[DocumentMetadata] = Field(
        default=None,
        description="Document metadata at this version"
    )
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Version creation timestamp"
    )
    
    created_by: Optional[str] = Field(
        default=None,
        description="User who created this version"
    )
    
    change_summary: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Summary of changes in this version"
    )
    
    checksum: Optional[str] = Field(
        default=None,
        description="Content checksum for this version"
    )


class SearchIndex(BaseModel):
    """Search index entry for full-text search."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    content: str
    title: str
    indexed_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class AuditLog(BaseModel):
    """Audit log entry for security tracking."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    action: str
    user_role: str
    details: Optional[str] = None
    document_id: Optional[str] = None
    
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )