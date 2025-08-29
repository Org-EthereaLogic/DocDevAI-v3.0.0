"""
Comprehensive security tests for M002 Storage System - Pass 3.

Tests SQLCipher encryption, PII detection, secure deletion, and access control
while validating performance requirements are maintained.
"""

import os
import pytest
import tempfile
import time
import json
import secrets
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from devdocai.storage.encryption import EncryptionManager, SQLCipherHelper
from devdocai.storage.pii_detector import (
    PIIDetector, PIIDetectionConfig, PIIType, PIIMatch
)
from devdocai.storage.secure_storage import (
    SecureStorageLayer, SecureConnectionPool, AccessControlManager
)


class TestEncryptionManager:
    """Test encryption functionality."""
    
    @pytest.fixture
    def temp_key_file(self):
        """Create temporary key file path."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name
        yield temp_path
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    @pytest.fixture
    def encryption_manager(self, temp_key_file):
        """Create encryption manager with temp key file."""
        return EncryptionManager(key_file=temp_key_file)
    
    def test_key_derivation(self, encryption_manager):
        """Test Argon2id key derivation."""
        password = "test_password_123"
        key1, salt1 = encryption_manager.derive_key(password)
        
        # Key should be 32 bytes (256 bits)
        assert len(key1) == 32
        assert len(salt1) == 16
        
        # Same password with same salt should produce same key
        key2, _ = encryption_manager.derive_key(password, salt1)
        assert key1 == key2
        
        # Different salt should produce different key
        key3, salt3 = encryption_manager.derive_key(password)
        assert key1 != key3
        assert salt1 != salt3
    
    def test_master_key_generation(self, encryption_manager):
        """Test master key generation and storage."""
        password = "secure_master_password"
        
        # Generate master key
        assert encryption_manager.generate_master_key(password)
        assert encryption_manager._master_key is not None
        assert len(encryption_manager._master_key) == 32
        
        # Key file should exist
        assert Path(encryption_manager.key_file).exists()
        
        # File permissions should be restricted (Unix only)
        if os.name != 'nt':
            stat_info = os.stat(encryption_manager.key_file)
            assert stat_info.st_mode & 0o777 == 0o600
    
    def test_master_key_loading(self, encryption_manager):
        """Test loading master key with correct/incorrect password."""
        password = "correct_password"
        wrong_password = "wrong_password"
        
        # Generate key
        encryption_manager.generate_master_key(password)
        original_key = encryption_manager._master_key
        
        # Create new manager and load with correct password
        new_manager = EncryptionManager(key_file=encryption_manager.key_file)
        assert new_manager.load_master_key(password)
        assert new_manager._master_key == original_key
        
        # Try loading with wrong password
        another_manager = EncryptionManager(key_file=encryption_manager.key_file)
        assert not another_manager.load_master_key(wrong_password)
        assert another_manager._master_key is None
    
    def test_aes_gcm_encryption(self, encryption_manager):
        """Test AES-256-GCM encryption/decryption."""
        encryption_manager.generate_master_key("test_password")
        
        # Test various content types
        test_data = [
            "Simple text message",
            "Unicode: 你好世界 🔐",
            json.dumps({"key": "value", "number": 42}),
            "A" * 10000  # Large content
        ]
        
        for plaintext in test_data:
            # Encrypt
            encrypted = encryption_manager.encrypt_content(plaintext)
            assert encrypted != plaintext.encode()
            assert len(encrypted) > len(plaintext)
            
            # Decrypt
            decrypted = encryption_manager.decrypt_content(encrypted)
            assert decrypted == plaintext
            
            # Ensure different nonces for each encryption
            encrypted2 = encryption_manager.encrypt_content(plaintext)
            assert encrypted != encrypted2  # Different nonce
            assert encryption_manager.decrypt_content(encrypted2) == plaintext
    
    def test_field_encryption(self, encryption_manager):
        """Test field-level encryption with JSON support."""
        encryption_manager.generate_master_key("test_password")
        
        # Test various field values
        test_values = [
            "simple string",
            42,
            3.14159,
            True,
            {"nested": {"data": "structure"}},
            ["list", "of", "items"]
        ]
        
        for value in test_values:
            # Encrypt field
            encrypted = encryption_manager.encrypt_field(value)
            assert isinstance(encrypted, str)  # Base64 encoded
            
            # Decrypt field
            decrypted = encryption_manager.decrypt_field(encrypted)
            assert decrypted == value
    
    def test_key_rotation(self, encryption_manager):
        """Test encryption key rotation."""
        old_password = "old_password"
        new_password = "new_password"
        
        # Generate initial key
        encryption_manager.generate_master_key(old_password)
        old_key = encryption_manager._master_key
        
        # Get SQLCipher key (should remain same after rotation)
        sqlcipher_key = encryption_manager.get_sqlcipher_key(old_password)
        
        # Rotate keys
        assert encryption_manager.rotate_keys(old_password, new_password)
        assert encryption_manager._master_key != old_key
        
        # Verify new password works
        new_manager = EncryptionManager(key_file=encryption_manager.key_file)
        assert new_manager.load_master_key(new_password)
        
        # SQLCipher key should remain the same
        assert new_manager.get_sqlcipher_key(new_password) == sqlcipher_key
        
        # Old password should no longer work
        assert not new_manager.load_master_key(old_password)
    
    def test_secure_key_deletion(self, encryption_manager):
        """Test secure deletion of key file."""
        encryption_manager.generate_master_key("test_password")
        key_file = encryption_manager.key_file
        
        # Ensure file exists
        assert Path(key_file).exists()
        
        # Secure delete
        assert encryption_manager.secure_delete_key(passes=3)
        
        # File should be gone
        assert not Path(key_file).exists()
        assert encryption_manager._master_key is None


class TestPIIDetector:
    """Test PII detection and masking."""
    
    @pytest.fixture
    def pii_detector(self):
        """Create PII detector with all types enabled."""
        config = PIIDetectionConfig(
            enabled_types=set(PIIType),
            min_confidence=0.7,
            preserve_partial=4
        )
        return PIIDetector(config)
    
    def test_ssn_detection(self, pii_detector):
        """Test Social Security Number detection."""
        texts = [
            "My SSN is 123-45-6789",
            "SSN: 123 45 6789",
            "Social Security: 123456789"
        ]
        
        for text in texts:
            matches = pii_detector.detect(text)
            assert len(matches) > 0
            assert matches[0].pii_type == PIIType.SSN
            assert "123" in matches[0].value
    
    def test_credit_card_detection(self, pii_detector):
        """Test credit card number detection with Luhn validation."""
        valid_cards = [
            "4532015112830366",  # Valid Visa
            "5425-2334-3010-9903",  # Valid Mastercard with dashes
            "3782 822463 10005",  # Valid Amex with spaces
        ]
        
        invalid_cards = [
            "4532015112830367",  # Invalid Luhn check
            "1234567812345678",  # Invalid prefix
        ]
        
        for card in valid_cards:
            text = f"Card number: {card}"
            matches = pii_detector.detect(text)
            assert len(matches) > 0
            assert matches[0].pii_type == PIIType.CREDIT_CARD
        
        for card in invalid_cards:
            text = f"Card number: {card}"
            matches = pii_detector.detect(text)
            # Should not detect invalid cards (or lower confidence)
            if matches:
                assert matches[0].confidence < 0.8
    
    def test_email_detection(self, pii_detector):
        """Test email address detection."""
        emails = [
            "john.doe@example.com",
            "alice+filter@company.co.uk",
            "support@sub.domain.org"
        ]
        
        for email in emails:
            text = f"Contact me at {email} for details"
            matches = pii_detector.detect(text)
            assert len(matches) > 0
            assert matches[0].pii_type == PIIType.EMAIL
            assert matches[0].value == email
    
    def test_phone_detection(self, pii_detector):
        """Test phone number detection."""
        phones = [
            "(555) 123-4567",
            "+1-555-123-4567",
            "555.123.4567",
            "+44 20 7123 4567"
        ]
        
        for phone in phones:
            text = f"Call me at {phone}"
            matches = pii_detector.detect(text)
            assert len(matches) > 0
            assert matches[0].pii_type == PIIType.PHONE
    
    def test_api_key_detection(self, pii_detector):
        """Test API key and secret detection."""
        api_keys = [
            "api_key=sk_test_abcdef123456789012345678901234567890",
            "API_SECRET: AKIAIOSFODNN7EXAMPLE",  # AWS format
            'apikey: "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8"'
        ]
        
        for key_text in api_keys:
            matches = pii_detector.detect(key_text)
            assert len(matches) > 0
            assert matches[0].pii_type in [PIIType.API_KEY, PIIType.AWS_KEY]
    
    def test_pii_masking(self, pii_detector):
        """Test PII masking with various options."""
        text = "Contact John at john@example.com or 555-123-4567"
        
        # Detect PII
        matches = pii_detector.detect(text)
        assert len(matches) == 2  # Email and phone
        
        # Mask with default settings
        masked = pii_detector.mask(text)
        assert "john@example.com" not in masked
        assert "555-123-4567" not in masked
        assert "*" in masked
        
        # Preserve partial masking
        detector_partial = PIIDetector(PIIDetectionConfig(preserve_partial=4))
        masked_partial = detector_partial.mask(text)
        assert ".com" in masked_partial  # Last 4 chars preserved
        assert "4567" in masked_partial  # Last 4 digits preserved
    
    def test_document_scanning(self, pii_detector):
        """Test scanning entire document for PII."""
        document = {
            'title': 'User Report',
            'content': 'User SSN: 123-45-6789, Email: user@example.com',
            'metadata': {
                'author': 'john.doe@company.com',
                'notes': 'Credit card: 4532015112830366'
            }
        }
        
        results = pii_detector.scan_document(document)
        
        assert 'content' in results
        assert len(results['content']) == 2  # SSN and email
        
        assert 'metadata.author' in results
        assert len(results['metadata.author']) == 1  # Email
        
        assert 'metadata.notes' in results
        assert len(results['metadata.notes']) == 1  # Credit card
    
    def test_pii_statistics(self, pii_detector):
        """Test PII detection statistics tracking."""
        texts = [
            "Email: test@example.com",
            "SSN: 123-45-6789",
            "Phone: 555-123-4567"
        ]
        
        for text in texts:
            pii_detector.detect(text)
            pii_detector.mask(text)
        
        stats = pii_detector.get_statistics()
        assert stats['detection_count'] == 3
        assert stats['mask_count'] == 3


class TestSecureStorage:
    """Test secure storage layer with encryption and PII protection."""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database file."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_path = f.name
        yield temp_path
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    @pytest.fixture
    def secure_storage(self, temp_db):
        """Create secure storage instance."""
        # Create tables first
        import sqlite3
        conn = sqlite3.connect(temp_db)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                type TEXT,
                status TEXT,
                content TEXT,
                content_hash TEXT,
                format TEXT,
                language TEXT,
                source_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP,
                access_count INTEGER DEFAULT 0
            );
            
            CREATE TABLE IF NOT EXISTS metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                value_type TEXT,
                is_searchable INTEGER DEFAULT 1,
                FOREIGN KEY (document_id) REFERENCES documents(id)
            );
            
            CREATE TABLE IF NOT EXISTS document_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                version_number INTEGER NOT NULL,
                content TEXT,
                content_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents(id)
            );
            
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation TEXT NOT NULL,
                entity_type TEXT,
                entity_id INTEGER,
                user TEXT,
                session_id TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT,
                new_value TEXT
            );
        """)
        conn.close()
        
        # Create secure storage with encryption
        storage = SecureStorageLayer(
            db_path=temp_db,
            master_password="test_password_123",
            cache_size=100,
            pool_size=5,
            enable_pii_detection=True
        )
        return storage
    
    @patch('devdocai.storage.secure_storage.sqlite3')
    def test_sqlcipher_integration(self, mock_sqlite3, temp_db):
        """Test SQLCipher connection with encryption."""
        # Mock sqlcipher3 import
        with patch('devdocai.storage.secure_storage.sqlite3_cipher') as mock_cipher:
            mock_conn = MagicMock()
            mock_cipher.connect.return_value = mock_conn
            
            pool = SecureConnectionPool(
                db_path=temp_db,
                encryption_key="0123456789abcdef" * 4,
                pool_size=2
            )
            
            # Should apply SQLCipher pragmas
            with pool.get_connection() as conn:
                cursor_calls = mock_conn.cursor().execute.call_args_list
                pragma_calls = [str(call) for call in cursor_calls]
                
                # Check for SQLCipher-specific pragmas
                assert any("PRAGMA key" in str(call) for call in pragma_calls)
                assert any("cipher_page_size" in str(call) for call in pragma_calls)
    
    def test_document_creation_with_pii(self, secure_storage):
        """Test creating document with PII detection."""
        document_data = {
            'title': 'User Profile',
            'content': 'User SSN: 123-45-6789, Email: user@example.com',
            'type': 'profile',
            'metadata': {
                'category': 'sensitive',
                'owner': 'admin'
            }
        }
        
        result = secure_storage.create_document(document_data, user='admin')
        
        assert result['id'] > 0
        assert result['uuid']
        assert result['pii_detected'] is True
        assert result['pii_count'] == 2
        
        # Content should be masked in response
        assert "123-45-6789" not in result['content']
        assert "****" in result['content']
    
    def test_document_retrieval_with_decryption(self, secure_storage):
        """Test retrieving and decrypting documents."""
        # Create document with sensitive content
        document_data = {
            'title': 'Sensitive Doc',
            'content': 'Confidential information here',
            'metadata': {'classification': 'secret'}
        }
        
        created = secure_storage.create_document(document_data, user='admin')
        doc_id = created['id']
        
        # Retrieve document
        retrieved = secure_storage.get_document(
            document_id=doc_id,
            user='admin'
        )
        
        assert retrieved['id'] == doc_id
        assert retrieved['content'] == document_data['content']
        assert retrieved['metadata']['classification'] == 'secret'
        
        # Check encryption statistics
        stats = secure_storage.get_statistics()
        assert stats['encrypted_writes'] > 0
        assert stats['encrypted_reads'] > 0
    
    def test_pii_masking_permissions(self, secure_storage):
        """Test PII masking based on user permissions."""
        # Create document with PII
        document_data = {
            'title': 'PII Document',
            'content': 'SSN: 123-45-6789, Card: 4532015112830366'
        }
        
        created = secure_storage.create_document(document_data, user='admin')
        doc_id = created['id']
        
        # Regular user should see masked PII
        doc_masked = secure_storage.get_document(
            document_id=doc_id,
            unmask_pii=False,
            user='regular_user'
        )
        assert "123-45-6789" not in doc_masked['content']
        assert doc_masked.get('pii_masked') is True
        
        # Admin with unmask permission should see original
        doc_unmasked = secure_storage.get_document(
            document_id=doc_id,
            unmask_pii=True,
            user='admin'
        )
        assert "123-45-6789" in doc_unmasked['content']
        assert doc_unmasked.get('pii_masked') is False
    
    def test_secure_deletion(self, secure_storage):
        """Test secure document deletion with overwriting."""
        # Create document
        document_data = {
            'title': 'To Delete',
            'content': 'Sensitive data to be securely deleted' * 100
        }
        
        created = secure_storage.create_document(document_data, user='admin')
        doc_id = created['id']
        
        # Perform secure deletion
        assert secure_storage.secure_delete(
            document_id=doc_id,
            user='admin',
            overwrite_passes=3
        )
        
        # Document should be gone
        retrieved = secure_storage.get_document(document_id=doc_id)
        assert retrieved is None
        
        # Check statistics
        stats = secure_storage.get_statistics()
        assert stats['secure_deletions'] == 1
    
    def test_access_control(self):
        """Test access control manager."""
        acm = AccessControlManager()
        
        # Test default permissions
        assert acm.check_permission('regular_user', 'read')
        assert acm.check_permission('regular_user', 'write')
        assert not acm.check_permission('regular_user', 'delete')
        assert not acm.check_permission('regular_user', 'unmask_pii')
        
        # Test admin permissions
        assert acm.check_permission('admin', 'read')
        assert acm.check_permission('admin', 'write')
        assert acm.check_permission('admin', 'delete')
        assert acm.check_permission('admin', 'unmask_pii')
    
    def test_performance_with_encryption(self, secure_storage):
        """Test that encryption doesn't severely impact performance."""
        # Create multiple documents
        start_time = time.time()
        doc_ids = []
        
        for i in range(100):
            doc_data = {
                'title': f'Doc {i}',
                'content': f'Content for document {i}' * 10,
                'metadata': {'index': i}
            }
            result = secure_storage.create_document(doc_data)
            doc_ids.append(result['id'])
        
        create_time = time.time() - start_time
        creates_per_second = 100 / create_time
        
        # Should maintain reasonable performance even with encryption
        assert creates_per_second > 50  # At least 50 creates/second
        
        # Test read performance
        start_time = time.time()
        
        for doc_id in doc_ids:
            secure_storage.get_document(document_id=doc_id)
        
        read_time = time.time() - start_time
        reads_per_second = 100 / read_time
        
        # Should maintain high read performance
        assert reads_per_second > 100  # At least 100 reads/second
        
        # Get final statistics
        stats = secure_storage.get_statistics()
        assert stats['queries_per_second'] > 0
        assert stats['cache_stats']['hit_rate'] > 0  # Cache should be working


class TestSQLCipherHelper:
    """Test SQLCipher helper functions."""
    
    def test_pragma_statements(self):
        """Test SQLCipher PRAGMA generation."""
        key = "0123456789abcdef" * 4  # 64 hex chars
        pragmas = SQLCipherHelper.get_pragma_statements(key)
        
        assert len(pragmas) == 5
        assert f"PRAGMA key = \"x'{key}'\"" in pragmas
        assert "PRAGMA cipher_page_size = 4096" in pragmas
        assert "PRAGMA kdf_iter = 256000" in pragmas
    
    @patch('sqlite3.connect')
    def test_encrypted_connection_creation(self, mock_connect):
        """Test creating encrypted SQLCipher connection."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        
        db_path = "test.db"
        key = "0123456789abcdef" * 4
        
        conn = SQLCipherHelper.create_encrypted_connection(db_path, key)
        
        # Should execute pragmas
        execute_calls = mock_conn.execute.call_args_list
        assert len(execute_calls) > 0
        
        # Should test connection
        assert any("SELECT count(*)" in str(call) for call in execute_calls)
    
    @patch('sqlite3.connect')
    def test_password_change(self, mock_connect):
        """Test changing database encryption password."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        
        db_path = "test.db"
        old_key = "old_key_0123456789abcdef" * 2
        new_key = "new_key_0123456789abcdef" * 2
        
        result = SQLCipherHelper.change_password(db_path, old_key, new_key)
        
        assert result is True
        
        # Should execute rekey pragma
        execute_calls = mock_conn.execute.call_args_list
        assert any("PRAGMA rekey" in str(call) for call in execute_calls)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])