"""
Unit tests for M002 LocalStorageSystem.

Tests CRUD operations, versioning, metadata management, search,
and transaction integrity.
"""

import os
import tempfile
import shutil
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import time

from devdocai.storage.local_storage import (
    LocalStorageSystem, DocumentData, QueryParams,
    StorageConfig
)
from devdocai.storage.models import DocumentType, DocumentStatus
from devdocai.core.config import ConfigurationManager


@pytest.fixture
def temp_db_dir():
    """Create temporary database directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def config_manager(temp_db_dir):
    """Create mock configuration manager."""
    config = ConfigurationManager()
    config._config = {
        'storage': {
            'db_path': str(Path(temp_db_dir) / 'test.db'),
            'enable_fts': True,
            'enable_wal': True,
            'pool_size': 5
        },
        'paths': {
            'data': temp_db_dir
        }
    }
    return config


@pytest.fixture
def storage_system(config_manager):
    """Create LocalStorageSystem instance."""
    system = LocalStorageSystem(config_manager)
    yield system
    system.close()


class TestLocalStorageSystem:
    """Test LocalStorageSystem functionality."""
    
    def test_initialization(self, storage_system):
        """Test system initialization."""
        assert storage_system is not None
        assert storage_system.config is not None
        assert storage_system.engine is not None
        assert storage_system.Session is not None
    
    def test_configuration_loading(self, config_manager):
        """Test configuration loading."""
        system = LocalStorageSystem(config_manager)
        assert system.config.db_path.endswith('test.db')
        assert system.config.enable_fts is True
        assert system.config.pool_size == 5
        system.close()
    
    def test_default_configuration(self):
        """Test initialization with default configuration."""
        system = LocalStorageSystem()
        assert system.config is not None
        assert system.config.pool_size == 20  # Default value
        system.close()


class TestDocumentOperations:
    """Test document CRUD operations."""
    
    def test_create_document(self, storage_system):
        """Test document creation."""
        data = DocumentData(
            title="Test Document",
            content="This is test content",
            type=DocumentType.TECHNICAL,
            metadata={"author": "test", "version": "1.0"}
        )
        
        doc = storage_system.create_document(data, user="testuser")
        
        assert doc is not None
        assert doc['title'] == "Test Document"
        assert doc['type'] == DocumentType.TECHNICAL.value
        assert doc['uuid'] is not None
        assert doc['id'] is not None
    
    def test_create_document_without_content(self, storage_system):
        """Test creating document without initial content."""
        data = DocumentData(
            title="Empty Document",
            type=DocumentType.API
        )
        
        doc = storage_system.create_document(data)
        
        assert doc is not None
        assert doc['title'] == "Empty Document"
        assert doc['type'] == DocumentType.API.value
    
    def test_get_document_by_id(self, storage_system):
        """Test retrieving document by ID."""
        # Create document
        data = DocumentData(title="Test Get", content="Content")
        created = storage_system.create_document(data)
        
        # Get document
        doc = storage_system.get_document(document_id=created['id'])
        
        assert doc is not None
        assert doc['id'] == created['id']
        assert doc['title'] == "Test Get"
        assert doc['content'] == "Content"
        assert doc['access_count'] == 1
    
    def test_get_document_by_uuid(self, storage_system):
        """Test retrieving document by UUID."""
        # Create document
        data = DocumentData(title="Test UUID", content="UUID Content")
        created = storage_system.create_document(data)
        
        # Get document by UUID
        doc = storage_system.get_document(uuid=created['uuid'])
        
        assert doc is not None
        assert doc['uuid'] == created['uuid']
        assert doc['title'] == "Test UUID"
    
    def test_get_document_not_found(self, storage_system):
        """Test retrieving non-existent document."""
        doc = storage_system.get_document(document_id=99999)
        assert doc is None
        
        doc = storage_system.get_document(uuid="non-existent-uuid")
        assert doc is None
    
    def test_get_document_without_content(self, storage_system):
        """Test retrieving document without content."""
        # Create document
        data = DocumentData(title="Test", content="Secret content")
        created = storage_system.create_document(data)
        
        # Get without content
        doc = storage_system.get_document(
            document_id=created['id'],
            include_content=False
        )
        
        assert doc is not None
        assert 'content' not in doc or doc['content'] is None
    
    def test_update_document(self, storage_system):
        """Test document update."""
        # Create document
        data = DocumentData(title="Original", content="Original content")
        created = storage_system.create_document(data)
        
        # Update document
        updated_data = DocumentData(
            title="Updated",
            content="Updated content",
            type=DocumentType.REFERENCE,
            metadata={"status": "reviewed"}
        )
        
        updated = storage_system.update_document(
            created['id'],
            updated_data,
            user="updater",
            version_comment="First update"
        )
        
        assert updated['title'] == "Updated"
        assert updated['type'] == DocumentType.REFERENCE.value
        
        # Verify new version was created
        versions = storage_system.get_versions(created['id'])
        assert len(versions) == 1
        assert versions[0]['version_number'] == 1
        assert versions[0]['comment'] == "First update"
    
    def test_update_document_metadata_only(self, storage_system):
        """Test updating only document metadata."""
        # Create document
        data = DocumentData(
            title="Test",
            content="Content",
            metadata={"v": "1"}
        )
        created = storage_system.create_document(data)
        
        # Update only metadata
        updated_data = DocumentData(
            title="Test",
            content="Content",  # Same content
            metadata={"v": "2", "reviewed": True}
        )
        
        updated = storage_system.update_document(created['id'], updated_data)
        
        # Get document with metadata
        doc = storage_system.get_document(document_id=created['id'])
        assert doc['metadata']['v'] == "2"
        assert doc['metadata']['reviewed'] is True
    
    def test_delete_document_soft(self, storage_system):
        """Test soft delete of document."""
        # Create document
        data = DocumentData(title="To Delete", content="Content")
        created = storage_system.create_document(data)
        
        # Soft delete
        result = storage_system.delete_document(
            created['id'],
            user="deleter",
            hard_delete=False
        )
        
        assert result is True
        
        # Document should still exist but with deleted status
        with storage_system.get_session() as session:
            from devdocai.storage.models import Document
            doc = session.query(Document).filter(
                Document.id == created['id']
            ).first()
            assert doc is not None
            assert doc.status == DocumentStatus.DELETED
    
    def test_delete_document_hard(self, storage_system):
        """Test hard delete of document."""
        # Create document
        data = DocumentData(title="To Delete", content="Content")
        created = storage_system.create_document(data)
        
        # Hard delete
        result = storage_system.delete_document(
            created['id'],
            hard_delete=True
        )
        
        assert result is True
        
        # Document should not exist
        doc = storage_system.get_document(document_id=created['id'])
        assert doc is None
    
    def test_delete_nonexistent_document(self, storage_system):
        """Test deleting non-existent document."""
        result = storage_system.delete_document(99999)
        assert result is False


class TestDocumentListing:
    """Test document listing and filtering."""
    
    def setup_documents(self, storage_system):
        """Create test documents."""
        docs = [
            DocumentData(
                title="Technical Doc 1",
                content="Content 1",
                type=DocumentType.TECHNICAL,
                metadata={"category": "backend"}
            ),
            DocumentData(
                title="API Doc 1",
                content="API content",
                type=DocumentType.API,
                metadata={"category": "rest"}
            ),
            DocumentData(
                title="Technical Doc 2",
                content="Content 2",
                type=DocumentType.TECHNICAL,
                metadata={"category": "frontend"}
            ),
            DocumentData(
                title="User Guide",
                content="Guide content",
                type=DocumentType.USER_GUIDE,
                metadata={"category": "enduser"}
            )
        ]
        
        created = []
        for doc in docs:
            created.append(storage_system.create_document(doc))
        
        return created
    
    def test_list_all_documents(self, storage_system):
        """Test listing all documents."""
        self.setup_documents(storage_system)
        
        result = storage_system.list_documents()
        
        assert result['total'] == 4
        assert len(result['documents']) == 4
        assert result['page'] == 1
    
    def test_list_documents_with_type_filter(self, storage_system):
        """Test listing documents with type filter."""
        self.setup_documents(storage_system)
        
        params = QueryParams(type=DocumentType.TECHNICAL)
        result = storage_system.list_documents(params)
        
        assert result['total'] == 2
        assert all(d['type'] == DocumentType.TECHNICAL.value 
                  for d in result['documents'])
    
    def test_list_documents_with_metadata_filter(self, storage_system):
        """Test listing documents with metadata filter."""
        self.setup_documents(storage_system)
        
        params = QueryParams(metadata_filters={"category": "backend"})
        result = storage_system.list_documents(params)
        
        assert result['total'] == 1
        assert result['documents'][0]['title'] == "Technical Doc 1"
    
    def test_list_documents_with_pagination(self, storage_system):
        """Test document pagination."""
        self.setup_documents(storage_system)
        
        # First page
        params = QueryParams(limit=2, offset=0)
        result = storage_system.list_documents(params)
        
        assert len(result['documents']) == 2
        assert result['page'] == 1
        assert result['pages'] == 2
        
        # Second page
        params = QueryParams(limit=2, offset=2)
        result = storage_system.list_documents(params)
        
        assert len(result['documents']) == 2
        assert result['page'] == 2
    
    def test_list_documents_with_ordering(self, storage_system):
        """Test document ordering."""
        docs = self.setup_documents(storage_system)
        
        # Order by title ascending
        params = QueryParams(order_by='title', order_desc=False)
        result = storage_system.list_documents(params)
        
        titles = [d['title'] for d in result['documents']]
        assert titles == sorted(titles)
    
    def test_list_excludes_deleted(self, storage_system):
        """Test that deleted documents are excluded by default."""
        self.setup_documents(storage_system)
        
        # Delete one document
        all_docs = storage_system.list_documents()
        storage_system.delete_document(
            all_docs['documents'][0]['id'],
            hard_delete=False
        )
        
        # List should exclude deleted
        result = storage_system.list_documents()
        assert result['total'] == 3


class TestVersioning:
    """Test document versioning functionality."""
    
    def test_create_versions(self, storage_system):
        """Test creating multiple versions."""
        # Create document
        data = DocumentData(title="Versioned", content="Version 1")
        doc = storage_system.create_document(data)
        
        # Create multiple versions
        for i in range(2, 5):
            updated_data = DocumentData(
                title="Versioned",
                content=f"Version {i}"
            )
            storage_system.update_document(
                doc['id'],
                updated_data,
                version_comment=f"Update to version {i}"
            )
        
        # Check versions
        versions = storage_system.get_versions(doc['id'])
        assert len(versions) == 4
        assert versions[0]['version_number'] == 4  # Latest first
        assert versions[-1]['version_number'] == 1  # Oldest last
    
    def test_get_specific_version(self, storage_system):
        """Test retrieving specific version."""
        # Create document with versions
        data = DocumentData(title="Test", content="Original")
        doc = storage_system.create_document(data)
        
        updated_data = DocumentData(title="Test", content="Updated")
        storage_system.update_document(doc['id'], updated_data)
        
        # Get specific version
        version = storage_system.get_version(doc['id'], version_number=1)
        
        assert version is not None
        assert version['content'] == "Updated"
        assert version['version_number'] == 1
    
    def test_restore_version(self, storage_system):
        """Test restoring previous version."""
        # Create document with versions
        data = DocumentData(title="Test", content="Version 1")
        doc = storage_system.create_document(data)
        
        # Update to version 2
        updated_data = DocumentData(title="Test", content="Version 2")
        storage_system.update_document(doc['id'], updated_data)
        
        # Update to version 3
        updated_data = DocumentData(title="Test", content="Version 3")
        storage_system.update_document(doc['id'], updated_data)
        
        # Restore version 1
        restored = storage_system.restore_version(
            doc['id'],
            version_number=1,
            user="restorer"
        )
        
        # Check current content
        current = storage_system.get_document(document_id=doc['id'])
        assert current['content'] == "Version 2"  # Restored to version 1 content
        
        # Check new version was created
        versions = storage_system.get_versions(doc['id'])
        assert len(versions) == 4  # Original + 2 updates + restore
        assert "Restored from version 1" in versions[0]['comment']


class TestSearch:
    """Test full-text search functionality."""
    
    def test_search_content(self, storage_system):
        """Test searching document content."""
        # Create documents
        docs = [
            DocumentData(title="Python Guide", content="Python programming tutorial"),
            DocumentData(title="Java Guide", content="Java programming tutorial"),
            DocumentData(title="API Reference", content="REST API documentation")
        ]
        
        for doc in docs:
            storage_system.create_document(doc)
        
        # Search for "programming"
        results = storage_system.search("programming")
        
        assert len(results) == 2
        assert all("programming" in r['content_highlight'].lower() 
                  for r in results)
    
    def test_search_title(self, storage_system):
        """Test searching document titles."""
        # Create documents
        docs = [
            DocumentData(title="Installation Guide", content="How to install"),
            DocumentData(title="User Guide", content="How to use"),
            DocumentData(title="Developer Reference", content="API docs")
        ]
        
        for doc in docs:
            storage_system.create_document(doc)
        
        # Search for "Guide"
        results = storage_system.search("Guide")
        
        assert len(results) == 2
        assert all("Guide" in r['title'] for r in results)
    
    def test_search_excludes_deleted(self, storage_system):
        """Test that search excludes deleted documents."""
        # Create documents
        data = DocumentData(title="To Delete", content="Searchable content")
        doc = storage_system.create_document(data)
        
        # Verify searchable
        results = storage_system.search("Searchable")
        assert len(results) == 1
        
        # Delete document
        storage_system.delete_document(doc['id'], hard_delete=False)
        
        # Should not appear in search
        results = storage_system.search("Searchable")
        assert len(results) == 0
    
    @pytest.mark.skipif(
        not os.environ.get('FTS_ENABLED', 'true').lower() == 'true',
        reason="FTS disabled"
    )
    def test_search_ranking(self, storage_system):
        """Test search result ranking."""
        # Create documents with different relevance
        docs = [
            DocumentData(
                title="Python",
                content="Python Python Python"  # Most relevant
            ),
            DocumentData(
                title="Guide",
                content="Python programming"  # Medium relevant
            ),
            DocumentData(
                title="Tutorial",
                content="Learn Python basics"  # Least relevant
            )
        ]
        
        for doc in docs:
            storage_system.create_document(doc)
        
        # Search for "Python"
        results = storage_system.search("Python")
        
        assert len(results) == 3
        # First result should have highest relevance
        assert results[0]['score'] >= results[1]['score']
        assert results[1]['score'] >= results[2]['score']


class TestTransactions:
    """Test transaction integrity."""
    
    def test_transaction_commit(self, storage_system):
        """Test successful transaction commit."""
        with storage_system.transaction() as session:
            from devdocai.storage.models import Document
            
            doc = Document(
                uuid="test-uuid",
                title="Transaction Test",
                content="Content"
            )
            session.add(doc)
        
        # Document should be persisted
        doc = storage_system.get_document(uuid="test-uuid")
        assert doc is not None
        assert doc['title'] == "Transaction Test"
    
    def test_transaction_rollback(self, storage_system):
        """Test transaction rollback on error."""
        try:
            with storage_system.transaction() as session:
                from devdocai.storage.models import Document
                
                doc = Document(
                    uuid="rollback-test",
                    title="Should Rollback",
                    content="Content"
                )
                session.add(doc)
                
                # Force an error
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Document should not be persisted
        doc = storage_system.get_document(uuid="rollback-test")
        assert doc is None
    
    def test_session_isolation(self, storage_system):
        """Test session isolation."""
        # Create document in one session
        with storage_system.get_session() as session1:
            from devdocai.storage.models import Document
            
            doc = Document(
                uuid="session-test",
                title="Session Test",
                content="Content"
            )
            session1.add(doc)
            session1.commit()
            doc_id = doc.id
        
        # Access in another session
        with storage_system.get_session() as session2:
            from devdocai.storage.models import Document
            
            doc = session2.query(Document).filter(
                Document.id == doc_id
            ).first()
            assert doc is not None
            assert doc.title == "Session Test"


class TestStatistics:
    """Test statistics and monitoring."""
    
    def test_get_statistics(self, storage_system):
        """Test getting storage statistics."""
        # Create some documents
        for i in range(3):
            data = DocumentData(
                title=f"Doc {i}",
                content=f"Content {i}",
                type=DocumentType.TECHNICAL if i < 2 else DocumentType.API
            )
            storage_system.create_document(data)
        
        stats = storage_system.get_statistics()
        
        assert stats['total_documents'] == 3
        assert stats['document_types'][DocumentType.TECHNICAL.value] == 2
        assert stats['document_types'][DocumentType.API.value] == 1
        assert stats['operations_count'] > 0
        assert stats['operations_per_second'] > 0
    
    def test_operation_counting(self, storage_system):
        """Test operation counting."""
        initial_count = storage_system._operation_count
        
        # Perform operations
        data = DocumentData(title="Test", content="Content")
        doc = storage_system.create_document(data)  # +1
        storage_system.get_document(document_id=doc['id'])  # +1
        storage_system.list_documents()  # +1
        
        assert storage_system._operation_count == initial_count + 3


class TestOptimization:
    """Test database optimization."""
    
    def test_optimize_database(self, storage_system):
        """Test database optimization."""
        # Create and delete documents to create fragmentation
        for i in range(10):
            data = DocumentData(title=f"Doc {i}", content=f"Content {i}")
            doc = storage_system.create_document(data)
            if i % 2 == 0:
                storage_system.delete_document(doc['id'], hard_delete=True)
        
        # Optimize
        storage_system.optimize()
        
        # Database should still be functional
        data = DocumentData(title="Post-optimize", content="Content")
        doc = storage_system.create_document(data)
        assert doc is not None


class TestErrorHandling:
    """Test error handling."""
    
    def test_invalid_document_data(self, storage_system):
        """Test handling invalid document data."""
        with pytest.raises(Exception):
            # Title is required
            data = DocumentData(title="", content="Content")
    
    def test_update_nonexistent_document(self, storage_system):
        """Test updating non-existent document."""
        data = DocumentData(title="Test", content="Content")
        
        with pytest.raises(ValueError) as exc:
            storage_system.update_document(99999, data)
        
        assert "not found" in str(exc.value)
    
    def test_restore_nonexistent_version(self, storage_system):
        """Test restoring non-existent version."""
        data = DocumentData(title="Test", content="Content")
        doc = storage_system.create_document(data)
        
        with pytest.raises(ValueError) as exc:
            storage_system.restore_version(doc['id'], version_number=99)
        
        assert "not found" in str(exc.value)
    
    def test_get_document_missing_params(self, storage_system):
        """Test get_document with missing parameters."""
        with pytest.raises(ValueError) as exc:
            storage_system.get_document()  # No ID or UUID
        
        assert "must be provided" in str(exc.value)


class TestPerformance:
    """Test performance characteristics."""
    
    @pytest.mark.performance
    def test_bulk_insert_performance(self, storage_system):
        """Test bulk insert performance."""
        start_time = time.time()
        num_docs = 100
        
        for i in range(num_docs):
            data = DocumentData(
                title=f"Bulk Doc {i}",
                content=f"Content {i}" * 100,  # ~1KB per doc
                metadata={"index": i, "bulk": True}
            )
            storage_system.create_document(data)
        
        elapsed = time.time() - start_time
        docs_per_second = num_docs / elapsed
        
        print(f"\nBulk insert: {docs_per_second:.2f} docs/sec")
        
        # Should handle at least 50 docs/sec
        assert docs_per_second > 50
    
    @pytest.mark.performance
    def test_query_performance(self, storage_system):
        """Test query performance."""
        # Create test documents
        for i in range(100):
            data = DocumentData(
                title=f"Query Test {i}",
                content=f"Content {i}",
                type=DocumentType.TECHNICAL if i % 2 == 0 else DocumentType.API
            )
            storage_system.create_document(data)
        
        # Test query performance
        start_time = time.time()
        iterations = 100
        
        for _ in range(iterations):
            params = QueryParams(type=DocumentType.TECHNICAL, limit=10)
            storage_system.list_documents(params)
        
        elapsed = time.time() - start_time
        queries_per_second = iterations / elapsed
        
        print(f"\nQuery performance: {queries_per_second:.2f} queries/sec")
        
        # Should handle at least 100 queries/sec
        assert queries_per_second > 100
    
    @pytest.mark.performance
    def test_search_performance(self, storage_system):
        """Test search performance."""
        # Create searchable documents
        for i in range(50):
            data = DocumentData(
                title=f"Search Doc {i}",
                content=f"Python programming tutorial number {i}"
            )
            storage_system.create_document(data)
        
        # Test search performance
        start_time = time.time()
        iterations = 50
        
        for _ in range(iterations):
            storage_system.search("Python")
        
        elapsed = time.time() - start_time
        searches_per_second = iterations / elapsed
        
        print(f"\nSearch performance: {searches_per_second:.2f} searches/sec")
        
        # Should handle at least 50 searches/sec
        assert searches_per_second > 50