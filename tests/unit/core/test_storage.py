"""
Test Suite for M002 Local Storage System
Following Enhanced 4-Pass TDD Methodology - PASS 1 (95% Coverage Target)

Tests written BEFORE implementation as per TDD principles.
Comprehensive test coverage for storage operations with SQLCipher encryption.
"""

import pytest
import tempfile
import os
import sqlite3
import hashlib
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta
import base64
import secrets

# Import will fail initially (TDD) - that's expected
from devdocai.core.storage import (
    StorageManager,
    Document,
    DocumentMetadata,
    StorageError,
    EncryptionError,
    IntegrityError,
    TransactionError,
)
from devdocai.core.config import ConfigurationManager


class TestDocument:
    """Test Document model class."""

    def test_document_creation(self):
        """Test creating a document with required fields."""
        doc = Document(
            id="doc_001",
            content="Test content",
            type="markdown",
            metadata={"author": "test", "version": "1.0"},
        )
        assert doc.id == "doc_001"
        assert doc.content == "Test content"
        assert doc.type == "markdown"
        assert doc.metadata.author == "test"
        assert doc.metadata.version == "1.0"
        assert doc.created_at is not None
        assert doc.updated_at is not None

    def test_document_validation(self):
        """Test document field validation."""
        # Test missing required fields
        with pytest.raises(TypeError):
            Document(content="Test")  # Missing id

        with pytest.raises(TypeError):
            Document(id="doc_001")  # Missing content

        # Test invalid types
        with pytest.raises(ValueError):
            Document(id=123, content="Test")  # id must be string

    def test_document_serialization(self):
        """Test document serialization for storage."""
        doc = Document(
            id="doc_001", content="Test content", type="markdown", metadata={"author": "test"}
        )

        serialized = doc.to_dict()
        assert serialized["id"] == "doc_001"
        assert serialized["content"] == "Test content"
        assert serialized["type"] == "markdown"
        assert "created_at" in serialized
        assert "updated_at" in serialized

        # Test deserialization
        doc2 = Document.from_dict(serialized)
        assert doc2.id == doc.id
        assert doc2.content == doc.content
        assert doc2.type == doc.type


class TestStorageManager:
    """Test StorageManager class with SQLCipher encryption."""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database path."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration manager."""
        config = Mock(spec=ConfigurationManager)
        config.get.side_effect = lambda path, default=None: {
            "storage.database_path": ":memory:",
            "storage.encryption_enabled": True,
            "storage.encryption_key": "test_key_32_bytes_long_for_aes256",
            "security.encryption_enabled": True,
            "security.api_keys_encrypted": True,
            "system.cache_size": "100MB",
        }.get(path, default)

        # Add encryption manager mock
        config._encryptor = Mock()
        config._encryptor.derive_key.return_value = b"0" * 32  # 32 bytes for AES-256
        config._encryptor.encrypt.side_effect = lambda x: base64.b64encode(x.encode()).decode()
        config._encryptor.decrypt.side_effect = lambda x: base64.b64decode(x).decode()

        return config

    @pytest.fixture
    def storage_manager(self, mock_config, temp_db_path):
        """Create StorageManager instance with mock config."""
        mock_config.get.side_effect = lambda path, default=None: {
            "storage.database_path": temp_db_path,
            "storage.encryption_enabled": True,
            "storage.encryption_key": "test_key_32_bytes_long_for_aes256",
            "security.encryption_enabled": True,
            "security.api_keys_encrypted": True,
            "system.cache_size": "100MB",
        }.get(path, default)
        return StorageManager(mock_config)

    def test_initialization(self, mock_config):
        """Test StorageManager initialization."""
        manager = StorageManager(mock_config)
        assert manager.config == mock_config
        assert manager.db_path is not None
        assert manager._encryption_key is not None
        assert manager._conn is not None

    def test_database_creation(self, storage_manager):
        """Test database and table creation."""
        # Check if tables exist
        cursor = storage_manager._conn.cursor()

        # Check documents table
        cursor.execute(
            """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='documents'
        """
        )
        assert cursor.fetchone() is not None

        # Check document_metadata table
        cursor.execute(
            """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='document_metadata'
        """
        )
        assert cursor.fetchone() is not None

        # Check document_versions table
        cursor.execute(
            """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='document_versions'
        """
        )
        assert cursor.fetchone() is not None

    def test_save_document(self, storage_manager):
        """Test saving an encrypted document."""
        doc = Document(
            id="test_doc_001",
            content="This is test content",
            type="markdown",
            metadata={"author": "tester", "tags": ["test", "demo"]},
        )

        # Save document
        result = storage_manager.save_document(doc)
        assert result is True

        # Verify document is in database
        cursor = storage_manager._conn.cursor()
        cursor.execute("SELECT id FROM documents WHERE id = ?", (doc.id,))
        assert cursor.fetchone() is not None

    def test_save_document_duplicate(self, storage_manager):
        """Test saving duplicate document raises error."""
        doc = Document(id="test_doc_001", content="Original content", type="markdown")

        # Save first time
        storage_manager.save_document(doc)

        # Try to save again with same ID
        with pytest.raises(StorageError):
            storage_manager.save_document(doc)

    def test_get_document(self, storage_manager):
        """Test retrieving and decrypting a document."""
        # Save a document first
        original_doc = Document(
            id="test_doc_002",
            content="Secret content to encrypt",
            type="text",
            metadata={"confidential": True},
        )
        storage_manager.save_document(original_doc)

        # Retrieve document
        retrieved_doc = storage_manager.get_document("test_doc_002")

        assert retrieved_doc is not None
        assert retrieved_doc.id == original_doc.id
        assert retrieved_doc.content == original_doc.content
        assert retrieved_doc.type == original_doc.type
        assert retrieved_doc.metadata.custom.get("confidential") is True

    def test_get_nonexistent_document(self, storage_manager):
        """Test retrieving non-existent document returns None."""
        doc = storage_manager.get_document("nonexistent_id")
        assert doc is None

    def test_update_document(self, storage_manager):
        """Test updating an existing document."""
        # Save initial document
        doc = Document(id="test_doc_003", content="Initial content", type="markdown")
        storage_manager.save_document(doc)

        # Update document
        updates = {"content": "Updated content", "metadata": {"updated": True, "version": "2.0"}}
        result = storage_manager.update_document("test_doc_003", updates)
        assert result is True

        # Verify updates
        updated_doc = storage_manager.get_document("test_doc_003")
        assert updated_doc.content == "Updated content"
        assert updated_doc.metadata.custom.get("updated") is True
        assert updated_doc.metadata.version == "2.0"

    def test_update_nonexistent_document(self, storage_manager):
        """Test updating non-existent document returns False."""
        updates = {"content": "New content"}
        result = storage_manager.update_document("nonexistent_id", updates)
        assert result is False

    def test_delete_document(self, storage_manager):
        """Test secure deletion with cryptographic erasure."""
        # Save a document
        doc = Document(id="test_doc_004", content="Content to delete", type="text")
        storage_manager.save_document(doc)

        # Delete document
        result = storage_manager.delete_document("test_doc_004")
        assert result is True

        # Verify deletion
        retrieved = storage_manager.get_document("test_doc_004")
        assert retrieved is None

        # Verify cryptographic erasure (overwritten in database)
        cursor = storage_manager._conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE id = ?", ("test_doc_004",))
        assert cursor.fetchone() is None

    def test_delete_nonexistent_document(self, storage_manager):
        """Test deleting non-existent document returns False."""
        result = storage_manager.delete_document("nonexistent_id")
        assert result is False

    def test_document_exists(self, storage_manager):
        """Test checking document existence."""
        # Save a document
        doc = Document(id="test_doc_005", content="Test content", type="text")
        storage_manager.save_document(doc)

        # Check existence
        assert storage_manager.document_exists("test_doc_005") is True
        assert storage_manager.document_exists("nonexistent_id") is False

    def test_encryption_with_unique_iv(self, storage_manager):
        """Test each document has unique initialization vector."""
        # Save two documents with same content
        doc1 = Document(id="doc1", content="Same content", type="text")
        doc2 = Document(id="doc2", content="Same content", type="text")

        storage_manager.save_document(doc1)
        storage_manager.save_document(doc2)

        # Get encrypted content from database
        cursor = storage_manager._conn.cursor()
        cursor.execute(
            "SELECT encrypted_content, iv FROM documents WHERE id IN (?, ?)", ("doc1", "doc2")
        )
        rows = cursor.fetchall()

        # Verify different IVs and encrypted content
        assert len(rows) == 2
        assert rows[0][1] != rows[1][1]  # Different IVs
        assert rows[0][0] != rows[1][0]  # Different encrypted content

    def test_hmac_integrity_check(self, storage_manager):
        """Test HMAC signature for tamper detection."""
        # Save a document
        doc = Document(id="test_doc_006", content="Content with integrity", type="text")
        storage_manager.save_document(doc)

        # Tamper with encrypted content directly
        cursor = storage_manager._conn.cursor()
        cursor.execute("SELECT encrypted_content FROM documents WHERE id = ?", ("test_doc_006",))
        encrypted = cursor.fetchone()[0]

        # Modify encrypted content
        tampered = encrypted[:-10] + b"tampered!!"
        cursor.execute(
            "UPDATE documents SET encrypted_content = ? WHERE id = ?", (tampered, "test_doc_006")
        )
        storage_manager._conn.commit()

        # Try to retrieve - should raise IntegrityError
        with pytest.raises(IntegrityError):
            storage_manager.get_document("test_doc_006")

    def test_transaction_commit(self, storage_manager):
        """Test transaction commit."""
        with storage_manager.transaction():
            doc = Document(id="tx_doc_001", content="Transaction test", type="text")
            storage_manager.save_document(doc)

        # Document should be saved after transaction
        assert storage_manager.document_exists("tx_doc_001")

    def test_transaction_rollback(self, storage_manager):
        """Test transaction rollback on error."""
        try:
            with storage_manager.transaction():
                doc = Document(id="tx_doc_002", content="Will rollback", type="text")
                storage_manager.save_document(doc)
                raise ValueError("Simulated error")
        except ValueError:
            pass

        # Document should not exist after rollback
        assert not storage_manager.document_exists("tx_doc_002")

    def test_nested_transactions(self, storage_manager):
        """Test nested transaction support."""
        with storage_manager.transaction():
            doc1 = Document(id="nested_001", content="Outer transaction", type="text")
            storage_manager.save_document(doc1)

            with storage_manager.transaction():
                doc2 = Document(id="nested_002", content="Inner transaction", type="text")
                storage_manager.save_document(doc2)

        # Both documents should exist
        assert storage_manager.document_exists("nested_001")
        assert storage_manager.document_exists("nested_002")

    def test_version_history(self, storage_manager):
        """Test document version history tracking."""
        # Create and save initial version
        doc = Document(id="versioned_doc", content="Version 1", type="text")
        storage_manager.save_document(doc)

        # Update document multiple times
        storage_manager.update_document("versioned_doc", {"content": "Version 2"})
        storage_manager.update_document("versioned_doc", {"content": "Version 3"})

        # Get version history
        history = storage_manager.get_version_history("versioned_doc")

        assert len(history) == 3
        assert history[0]["version"] == 1
        assert history[1]["version"] == 2
        assert history[2]["version"] == 3

    def test_search_metadata(self, storage_manager):
        """Test searching documents by metadata."""
        # Save documents with metadata
        doc1 = Document(
            id="search_001",
            content="Content 1",
            type="markdown",
            metadata={"author": "alice", "tags": ["python", "testing"]},
        )
        doc2 = Document(
            id="search_002",
            content="Content 2",
            type="markdown",
            metadata={"author": "bob", "tags": ["python", "development"]},
        )
        doc3 = Document(
            id="search_003",
            content="Content 3",
            type="text",
            metadata={"author": "alice", "tags": ["documentation"]},
        )

        storage_manager.save_document(doc1)
        storage_manager.save_document(doc2)
        storage_manager.save_document(doc3)

        # Search by author
        results = storage_manager.search_by_metadata({"author": "alice"})
        assert len(results) == 2
        assert all(doc.metadata.author == "alice" for doc in results)

        # Search by tag
        results = storage_manager.search_by_metadata({"tags": "python"})
        assert len(results) == 2

        # Search by type
        results = storage_manager.search_by_type("markdown")
        assert len(results) == 2

    def test_bulk_operations(self, storage_manager):
        """Test bulk save and delete operations."""
        # Create multiple documents
        docs = [Document(id=f"bulk_{i}", content=f"Content {i}", type="text") for i in range(10)]

        # Bulk save
        results = storage_manager.bulk_save(docs)
        assert all(results.values())
        assert len(results) == 10

        # Verify all saved
        for doc in docs:
            assert storage_manager.document_exists(doc.id)

        # Bulk delete
        ids = [doc.id for doc in docs[:5]]
        results = storage_manager.bulk_delete(ids)
        assert all(results.values())

        # Verify deletion
        for doc_id in ids:
            assert not storage_manager.document_exists(doc_id)
        for doc in docs[5:]:
            assert storage_manager.document_exists(doc.id)

    def test_storage_statistics(self, storage_manager):
        """Test getting storage statistics."""
        # Save some documents
        for i in range(5):
            doc = Document(
                id=f"stats_{i}",
                content=f"Content {i}" * 100,
                type="text" if i % 2 == 0 else "markdown",
            )
            storage_manager.save_document(doc)

        stats = storage_manager.get_statistics()

        assert stats["total_documents"] == 5
        assert stats["total_size"] > 0
        assert stats["types"]["text"] == 3
        assert stats["types"]["markdown"] == 2
        assert "database_size" in stats

    def test_backup_and_restore(self, storage_manager, temp_db_path):
        """Test database backup and restore functionality."""
        # Save some documents
        doc1 = Document(id="backup_001", content="Backup test 1", type="text")
        doc2 = Document(id="backup_002", content="Backup test 2", type="markdown")
        storage_manager.save_document(doc1)
        storage_manager.save_document(doc2)

        # Create backup
        backup_path = temp_db_path + ".backup"
        storage_manager.backup(backup_path)
        assert os.path.exists(backup_path)

        # Delete a document
        storage_manager.delete_document("backup_001")
        assert not storage_manager.document_exists("backup_001")

        # Restore from backup
        storage_manager.restore(backup_path)

        # Verify restoration
        assert storage_manager.document_exists("backup_001")
        assert storage_manager.document_exists("backup_002")

        # Cleanup
        if os.path.exists(backup_path):
            os.unlink(backup_path)

    def test_connection_pool(self, mock_config):
        """Test connection pooling for concurrent access."""
        manager = StorageManager(mock_config)

        # Get multiple connections
        conns = []
        for _ in range(5):
            conn = manager._get_connection()
            conns.append(conn)

        # All connections should be valid
        for conn in conns:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            assert cursor.fetchone()[0] == 1

        # Return connections to pool
        for conn in conns:
            manager._return_connection(conn)

    def test_thread_safety(self, storage_manager):
        """Test thread-safe operations."""
        import threading
        import time

        results = []
        errors = []

        def save_documents(start_id):
            try:
                for i in range(10):
                    doc = Document(
                        id=f"thread_{start_id}_{i}", content=f"Thread content {i}", type="text"
                    )
                    storage_manager.save_document(doc)
                    time.sleep(0.001)  # Small delay to encourage interleaving
                results.append(True)
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=save_documents, args=(i * 100,))
            threads.append(t)
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # Check results
        assert len(errors) == 0
        assert len(results) == 5

        # Verify all documents saved
        for i in range(5):
            for j in range(10):
                assert storage_manager.document_exists(f"thread_{i * 100}_{j}")

    def test_encryption_key_rotation(self, storage_manager):
        """Test encryption key rotation."""
        # Save document with original key
        doc = Document(id="rotate_001", content="Original encryption", type="text")
        storage_manager.save_document(doc)

        # Rotate encryption key
        new_key = secrets.token_bytes(32)
        storage_manager.rotate_encryption_key(new_key)

        # Verify document can still be retrieved
        retrieved = storage_manager.get_document("rotate_001")
        assert retrieved is not None
        assert retrieved.content == "Original encryption"

        # Save new document with new key
        doc2 = Document(id="rotate_002", content="New encryption", type="text")
        storage_manager.save_document(doc2)

        # Both documents should be retrievable
        assert storage_manager.document_exists("rotate_001")
        assert storage_manager.document_exists("rotate_002")

    @patch("devdocai.core.storage.sqlite3")
    def test_sqlcipher_initialization(self, mock_sqlite, mock_config):
        """Test SQLCipher extension initialization."""
        mock_conn = MagicMock()
        mock_sqlite.connect.return_value = mock_conn

        manager = StorageManager(mock_config)

        # Verify SQLCipher pragmas were set
        expected_calls = [
            call("PRAGMA key = ?", (mock_config.get("storage.encryption_key"),)),
            call("PRAGMA cipher = 'aes-256-gcm'"),
            call("PRAGMA kdf_iter = 256000"),
        ]

        for expected_call in expected_calls:
            assert expected_call in mock_conn.execute.call_args_list

    def test_performance_sub_millisecond_queries(self, storage_manager):
        """Test query performance meets sub-millisecond target."""
        import time

        # Prepare test data
        for i in range(100):
            doc = Document(id=f"perf_{i}", content=f"Performance test content {i}", type="text")
            storage_manager.save_document(doc)

        # Test query performance
        times = []
        for i in range(10):
            start = time.perf_counter()
            doc = storage_manager.get_document(f"perf_{i}")
            end = time.perf_counter()
            times.append((end - start) * 1000)  # Convert to milliseconds

        avg_time = sum(times) / len(times)
        assert avg_time < 1.0, f"Average query time {avg_time}ms exceeds 1ms target"

    def test_close_connection(self, storage_manager):
        """Test proper connection cleanup."""
        # Perform some operations
        doc = Document(id="close_test", content="Test", type="text")
        storage_manager.save_document(doc)

        # Close connection
        storage_manager.close()

        # Verify connection is closed
        with pytest.raises(StorageError):
            storage_manager.get_document("close_test")


class TestStorageErrors:
    """Test error handling and exceptions."""

    def test_storage_error_hierarchy(self):
        """Test exception hierarchy."""
        assert issubclass(EncryptionError, StorageError)
        assert issubclass(IntegrityError, StorageError)
        assert issubclass(TransactionError, StorageError)

    def test_encryption_error_messages(self):
        """Test encryption error messages."""
        error = EncryptionError("Failed to encrypt document")
        assert str(error) == "Failed to encrypt document"
        assert error.error_code == "ENCRYPTION_ERROR"

    def test_integrity_error_details(self):
        """Test integrity error with details."""
        error = IntegrityError(
            "HMAC verification failed",
            document_id="doc_001",
            expected_hmac="abc123",
            actual_hmac="def456",
        )
        assert error.document_id == "doc_001"
        assert error.details["expected_hmac"] == "abc123"
        assert error.details["actual_hmac"] == "def456"


class TestIntegrationWithM001:
    """Test integration with M001 Configuration Manager."""

    @pytest.fixture
    def real_config(self, tmp_path):
        """Create real ConfigurationManager instance."""
        config_file = tmp_path / ".devdocai.yml"
        config_data = {
            "storage": {
                "database_path": str(tmp_path / "test.db"),
                "encryption_enabled": True,
                "encryption_key": "integration_test_key_32_bytes___",
            },
            "security": {"encryption_enabled": True, "api_keys_encrypted": True},
        }

        import yaml

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Import real ConfigurationManager
        from devdocai.core.config import ConfigurationManager

        return ConfigurationManager(config_file)

    def test_integration_with_real_config(self, real_config):
        """Test StorageManager with real ConfigurationManager."""
        manager = StorageManager(real_config)

        # Test basic operations
        doc = Document(id="integration_001", content="Integration test", type="markdown")

        assert manager.save_document(doc) is True
        retrieved = manager.get_document("integration_001")
        assert retrieved is not None
        assert retrieved.content == "Integration test"

        # Cleanup
        manager.close()
