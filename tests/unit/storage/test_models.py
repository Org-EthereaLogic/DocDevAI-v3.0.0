"""
Unit tests for M002 storage models.

Tests SQLAlchemy models, relationships, and validation.
"""

import pytest
import json
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from devdocai.storage.models import (
    Base, Document, DocumentVersion, Metadata, SearchIndex, AuditLog,
    DocumentStatus, DocumentType
)


@pytest.fixture
def db_engine():
    """Create in-memory SQLite database."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(db_engine):
    """Create database session."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


class TestDocumentModel:
    """Test Document model."""
    
    def test_create_document(self, db_session):
        """Test creating a document."""
        doc = Document(
            uuid="test-uuid-123",
            title="Test Document",
            type=DocumentType.TECHNICAL,
            status=DocumentStatus.DRAFT,
            content="Test content",
            format="markdown",
            language="en"
        )
        
        db_session.add(doc)
        db_session.commit()
        
        assert doc.id is not None
        assert doc.title == "Test Document"
        assert doc.type == DocumentType.TECHNICAL
        assert doc.status == DocumentStatus.DRAFT
        assert doc.content_hash is not None  # Auto-generated
        assert doc.size_bytes == len("Test content")
    
    def test_document_content_hash_update(self, db_session):
        """Test automatic content hash update."""
        doc = Document(
            uuid="test-uuid",
            title="Test",
            content="Original content"
        )
        
        db_session.add(doc)
        db_session.commit()
        
        original_hash = doc.content_hash
        original_size = doc.size_bytes
        
        # Update content
        doc.content = "Updated content"
        db_session.commit()
        
        assert doc.content_hash != original_hash
        assert doc.size_bytes != original_size
        assert doc.size_bytes == len("Updated content")
    
    def test_document_to_dict(self, db_session):
        """Test document dictionary conversion."""
        doc = Document(
            uuid="test-uuid",
            title="Test Document",
            type=DocumentType.API,
            status=DocumentStatus.ACTIVE,
            content="Content",
            quality_score=0.85,
            completeness_score=0.90
        )
        
        db_session.add(doc)
        db_session.commit()
        
        doc_dict = doc.to_dict()
        
        assert doc_dict['uuid'] == "test-uuid"
        assert doc_dict['title'] == "Test Document"
        assert doc_dict['type'] == DocumentType.API
        assert doc_dict['status'] == DocumentStatus.ACTIVE
        assert doc_dict['quality_score'] == 0.85
        assert doc_dict['completeness_score'] == 0.90
        assert 'created_at' in doc_dict
        assert 'version_count' in doc_dict
    
    def test_document_relationships(self, db_session):
        """Test document relationships."""
        doc = Document(
            uuid="test-uuid",
            title="Test Document",
            content="Content"
        )
        
        # Add version
        version = DocumentVersion(
            document=doc,
            version_number=1,
            content="Content",
            content_hash="hash123"
        )
        
        # Add metadata
        meta = Metadata(
            document=doc,
            key="author",
            value="test"
        )
        
        db_session.add_all([doc, version, meta])
        db_session.commit()
        
        # Test relationships
        assert doc.versions.count() == 1
        assert doc.versions.first() == version
        assert doc.metadata_entries.count() == 1
        assert doc.metadata_entries.first() == meta
    
    def test_document_cascade_delete(self, db_session):
        """Test cascade delete of related records."""
        doc = Document(
            uuid="test-uuid",
            title="Test Document",
            content="Content"
        )
        
        version = DocumentVersion(
            document=doc,
            version_number=1,
            content="Content",
            content_hash="hash"
        )
        
        meta = Metadata(
            document=doc,
            key="test",
            value="value"
        )
        
        db_session.add_all([doc, version, meta])
        db_session.commit()
        
        # Delete document
        db_session.delete(doc)
        db_session.commit()
        
        # Related records should be deleted
        assert db_session.query(DocumentVersion).count() == 0
        assert db_session.query(Metadata).count() == 0


class TestDocumentVersionModel:
    """Test DocumentVersion model."""
    
    def test_create_version(self, db_session):
        """Test creating a document version."""
        doc = Document(
            uuid="test-uuid",
            title="Test",
            content="Content"
        )
        
        version = DocumentVersion(
            document=doc,
            version_number=1,
            content="Version 1 content",
            content_hash="hash123",
            created_by="user1",
            comment="Initial version",
            is_major=False
        )
        
        db_session.add_all([doc, version])
        db_session.commit()
        
        assert version.id is not None
        assert version.document_id == doc.id
        assert version.version_number == 1
        assert version.created_by == "user1"
        assert version.comment == "Initial version"
        assert version.is_major is False
    
    def test_version_with_diff(self, db_session):
        """Test version with diff from previous."""
        doc = Document(uuid="test-uuid", title="Test")
        
        diff_data = {
            'type': 'unified',
            'context_lines': 3,
            'old_size': 100,
            'new_size': 150,
            'changes': ['+Added line', '-Removed line']
        }
        
        version = DocumentVersion(
            document=doc,
            version_number=2,
            content="Updated content",
            content_hash="hash456",
            diff_from_previous=json.dumps(diff_data)
        )
        
        db_session.add_all([doc, version])
        db_session.commit()
        
        assert version.diff_from_previous is not None
        diff = json.loads(version.diff_from_previous)
        assert diff['type'] == 'unified'
        assert diff['old_size'] == 100
        assert diff['new_size'] == 150
    
    def test_version_to_dict(self, db_session):
        """Test version dictionary conversion."""
        doc = Document(uuid="test-uuid", title="Test")
        
        version = DocumentVersion(
            document=doc,
            version_number=1,
            content="Content",
            content_hash="hash123",
            created_by="user1",
            comment="Test version",
            is_major=True
        )
        
        db_session.add_all([doc, version])
        db_session.commit()
        
        version_dict = version.to_dict()
        
        assert version_dict['document_id'] == doc.id
        assert version_dict['version_number'] == 1
        assert version_dict['content_hash'] == "hash123"
        assert version_dict['created_by'] == "user1"
        assert version_dict['comment'] == "Test version"
        assert version_dict['is_major'] is True
        assert 'created_at' in version_dict
    
    def test_unique_version_constraint(self, db_session):
        """Test unique constraint on document-version pairs."""
        doc = Document(uuid="test-uuid", title="Test")
        
        v1 = DocumentVersion(
            document=doc,
            version_number=1,
            content="Content",
            content_hash="hash1"
        )
        
        db_session.add_all([doc, v1])
        db_session.commit()
        
        # Try to create duplicate version number
        v2 = DocumentVersion(
            document=doc,
            version_number=1,  # Duplicate
            content="Different",
            content_hash="hash2"
        )
        
        db_session.add(v2)
        
        with pytest.raises(Exception):  # Should violate unique constraint
            db_session.commit()


class TestMetadataModel:
    """Test Metadata model."""
    
    def test_create_metadata(self, db_session):
        """Test creating metadata."""
        doc = Document(uuid="test-uuid", title="Test")
        
        meta = Metadata(
            document=doc,
            key="author",
            value="John Doe",
            value_type="string",
            category="authorship",
            is_searchable=True,
            is_public=True
        )
        
        db_session.add_all([doc, meta])
        db_session.commit()
        
        assert meta.id is not None
        assert meta.key == "author"
        assert meta.value == "John Doe"
        assert meta.value_type == "string"
        assert meta.category == "authorship"
    
    def test_typed_values_string(self, db_session):
        """Test string value type."""
        doc = Document(uuid="test-uuid", title="Test")
        meta = Metadata(document=doc, key="test")
        
        meta.set_typed_value("test string")
        
        assert meta.value == "test string"
        assert meta.value_type == "string"
        assert meta.get_typed_value() == "test string"
    
    def test_typed_values_number(self, db_session):
        """Test number value type."""
        doc = Document(uuid="test-uuid", title="Test")
        meta = Metadata(document=doc, key="test")
        
        meta.set_typed_value(42.5)
        
        assert meta.value == "42.5"
        assert meta.value_type == "number"
        assert meta.get_typed_value() == 42.5
    
    def test_typed_values_boolean(self, db_session):
        """Test boolean value type."""
        doc = Document(uuid="test-uuid", title="Test")
        meta = Metadata(document=doc, key="test")
        
        meta.set_typed_value(True)
        
        assert meta.value == "True"
        assert meta.value_type == "boolean"
        assert meta.get_typed_value() is True
        
        meta.set_typed_value(False)
        assert meta.value == "False"
        assert meta.get_typed_value() is False
    
    def test_typed_values_json(self, db_session):
        """Test JSON value type."""
        doc = Document(uuid="test-uuid", title="Test")
        meta = Metadata(document=doc, key="test")
        
        data = {"nested": {"key": "value"}, "list": [1, 2, 3]}
        meta.set_typed_value(data)
        
        assert meta.value_type == "json"
        assert json.loads(meta.value) == data
        assert meta.get_typed_value() == data
    
    def test_unique_metadata_constraint(self, db_session):
        """Test unique constraint on document-key pairs."""
        doc = Document(uuid="test-uuid", title="Test")
        
        m1 = Metadata(document=doc, key="author", value="John")
        db_session.add_all([doc, m1])
        db_session.commit()
        
        # Try to create duplicate key
        m2 = Metadata(document=doc, key="author", value="Jane")
        db_session.add(m2)
        
        with pytest.raises(Exception):  # Should violate unique constraint
            db_session.commit()


class TestSearchIndexModel:
    """Test SearchIndex model."""
    
    def test_create_search_index(self, db_session):
        """Test creating search index."""
        doc = Document(uuid="test-uuid", title="Test", content="Content")
        db_session.add(doc)
        db_session.commit()  # Commit to get the document ID
        
        index = SearchIndex(
            document_id=doc.id,
            content_tokens="content test document",
            title_tokens="test",
            metadata_tokens="author:john category:tech",
            token_count=5,
            index_version=1
        )
        
        db_session.add(index)
        db_session.commit()
        
        assert index.id is not None
        assert index.document_id == doc.id
        assert index.content_tokens == "content test document"
        assert index.token_count == 5
        assert index.last_indexed is not None


class TestAuditLogModel:
    """Test AuditLog model."""
    
    def test_create_audit_log(self, db_session):
        """Test creating audit log entry."""
        audit = AuditLog(
            operation="CREATE",
            entity_type="document",
            entity_id=1,
            user="testuser",
            session_id="session-123",
            ip_address="127.0.0.1",
            old_value=None,
            new_value={"title": "New Document"},
            status="success",
            duration_ms=150
        )
        
        db_session.add(audit)
        db_session.commit()
        
        assert audit.id is not None
        assert audit.operation == "CREATE"
        assert audit.entity_type == "document"
        assert audit.user == "testuser"
        assert audit.status == "success"
        assert audit.duration_ms == 150
        assert audit.timestamp is not None
    
    def test_audit_log_with_error(self, db_session):
        """Test audit log with error."""
        audit = AuditLog(
            operation="UPDATE",
            entity_type="document",
            entity_id=1,
            status="error",
            error_message="Permission denied"
        )
        
        db_session.add(audit)
        db_session.commit()
        
        assert audit.status == "error"
        assert audit.error_message == "Permission denied"
    
    def test_audit_log_to_dict(self, db_session):
        """Test audit log dictionary conversion."""
        audit = AuditLog(
            operation="DELETE",
            entity_type="document",
            entity_id=5,
            user="admin",
            session_id="sess-456",
            status="success",
            duration_ms=50
        )
        
        db_session.add(audit)
        db_session.commit()
        
        audit_dict = audit.to_dict()
        
        assert audit_dict['operation'] == "DELETE"
        assert audit_dict['entity_type'] == "document"
        assert audit_dict['entity_id'] == 5
        assert audit_dict['user'] == "admin"
        assert audit_dict['status'] == "success"
        assert audit_dict['duration_ms'] == 50
        assert 'timestamp' in audit_dict


class TestEnums:
    """Test enum types."""
    
    def test_document_status_enum(self):
        """Test DocumentStatus enum."""
        assert DocumentStatus.DRAFT == "draft"
        assert DocumentStatus.ACTIVE == "active"
        assert DocumentStatus.ARCHIVED == "archived"
        assert DocumentStatus.DELETED == "deleted"
    
    def test_document_type_enum(self):
        """Test DocumentType enum."""
        assert DocumentType.TECHNICAL == "technical"
        assert DocumentType.API == "api"
        assert DocumentType.USER_GUIDE == "user_guide"
        assert DocumentType.TUTORIAL == "tutorial"
        assert DocumentType.REFERENCE == "reference"
        assert DocumentType.DESIGN == "design"
        assert DocumentType.README == "readme"
        assert DocumentType.CHANGELOG == "changelog"
        assert DocumentType.OTHER == "other"