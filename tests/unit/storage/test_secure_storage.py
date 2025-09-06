"""
Comprehensive test suite for M002 Security Hardened Storage (Pass 3)

Test coverage targets:
- 95% code coverage
- All security features validated
- Performance benchmarks maintained
- OWASP Top 10 compliance verified
"""

import pytest
import json
import time
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil

from devdocai.storage.secure_storage import (
    SecureStorageManager, UserRole, AccessPermission, 
    PIICategory, MaskingStrategy
)
from devdocai.storage.pii_detector import (
    PIIDetector, PIIType, PIIMatch
)
from devdocai.core.config import ConfigurationManager


class TestSecureStorageManager:
    """Test suite for SecureStorageManager."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def config(self, temp_dir):
        """Create test configuration."""
        config = Mock(spec=ConfigurationManager)
        config.get.side_effect = lambda key, default=None: {
            'storage_path': temp_dir / 'storage',
            'config_dir': temp_dir / 'config',
            'cache_dir': temp_dir / 'cache',
            'encryption_enabled': True,
            'pii_detection_enabled': True,
            'audit_logging_enabled': True,
            'secure_deletion_enabled': True,
            'sqlcipher_enabled': False  # Disabled for testing without SQLCipher
        }.get(key, default)
        
        # Create directories
        (temp_dir / 'storage').mkdir(parents=True, exist_ok=True)
        (temp_dir / 'config').mkdir(parents=True, exist_ok=True)
        (temp_dir / 'cache').mkdir(parents=True, exist_ok=True)
        
        return config
    
    @pytest.fixture
    def secure_storage(self, config):
        """Create SecureStorageManager instance."""
        return SecureStorageManager(config, UserRole.ADMIN)
    
    def test_initialization(self, secure_storage):
        """Test secure storage initialization."""
        assert secure_storage.user_role == UserRole.ADMIN
        assert secure_storage.enable_pii_detection is True
        assert secure_storage.enable_audit_logging is True
        assert secure_storage.enable_secure_deletion is True
        assert secure_storage._rate_limit_max_requests == 1000
    
    def test_rbac_permissions(self, secure_storage):
        """Test role-based access control."""
        # Admin has all permissions
        assert secure_storage._check_permission(AccessPermission.READ)
        assert secure_storage._check_permission(AccessPermission.WRITE)
        assert secure_storage._check_permission(AccessPermission.DELETE)
        assert secure_storage._check_permission(AccessPermission.ADMIN)
        assert secure_storage._check_permission(AccessPermission.AUDIT)
        
        # Test viewer role
        secure_storage.user_role = UserRole.VIEWER
        assert secure_storage._check_permission(AccessPermission.READ)
        assert not secure_storage._check_permission(AccessPermission.WRITE)
        assert not secure_storage._check_permission(AccessPermission.DELETE)
    
    def test_permission_enforcement(self, config):
        """Test permission enforcement raises errors."""
        viewer_storage = SecureStorageManager(config, UserRole.VIEWER)
        
        with pytest.raises(PermissionError, match="Permission denied"):
            viewer_storage._enforce_permission(AccessPermission.WRITE)
    
    def test_rate_limiting(self, secure_storage):
        """Test rate limiting functionality."""
        user_id = "test_user"
        
        # Should allow requests up to limit
        for _ in range(100):
            assert secure_storage._check_rate_limit(user_id)
        
        # Set up to exceed limit
        secure_storage._rate_limit_max_requests = 5
        secure_storage._rate_limiter[user_id] = [time.time()] * 5
        
        # Should block when limit exceeded
        assert not secure_storage._check_rate_limit(user_id)
    
    def test_input_sanitization(self, secure_storage):
        """Test input sanitization for injection prevention."""
        # SQL injection attempts
        dangerous_inputs = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "'; UPDATE documents SET deleted=1; --"
        ]
        
        for dangerous in dangerous_inputs:
            sanitized = secure_storage._sanitize_input(dangerous)
            assert "DROP" not in sanitized
            assert "script" not in sanitized
            assert "javascript:" not in sanitized
            assert "--" not in sanitized
            assert len(sanitized) <= 1000
    
    def test_pii_detection(self, secure_storage):
        """Test PII detection in content."""
        content = """
        Contact John Doe at john.doe@example.com or 555-123-4567.
        His SSN is 123-45-6789 and credit card 4111-1111-1111-1111.
        IP address: 192.168.1.100
        """
        
        detected = secure_storage._detect_pii(content)
        
        assert PIICategory.EMAIL in detected
        assert PIICategory.PHONE in detected
        assert PIICategory.SSN in detected
        assert PIICategory.CREDIT_CARD in detected
        assert PIICategory.IP_ADDRESS in detected
    
    def test_pii_masking(self, secure_storage):
        """Test PII masking functionality."""
        content = "Email: test@example.com, Phone: 555-123-4567"
        detected = {
            PIICategory.EMAIL: ["test@example.com"],
            PIICategory.PHONE: ["555-123-4567"]
        }
        
        masked = secure_storage._mask_pii(content, detected)
        
        assert "***@example.com" in masked
        assert "XXXX" in masked
        assert "test@example.com" not in masked
        assert "555-123-4567" not in masked
    
    @patch('os.fsync')
    def test_secure_deletion(self, mock_fsync, secure_storage, temp_dir):
        """Test secure file deletion."""
        # Create test file
        test_file = temp_dir / "test.txt"
        test_file.write_text("sensitive data")
        
        # Perform secure deletion
        secure_storage._secure_delete(test_file, passes=3)
        
        # File should be deleted
        assert not test_file.exists()
        # fsync should be called for each pass
        assert mock_fsync.call_count == 3
    
    def test_audit_logging(self, secure_storage):
        """Test audit logging functionality."""
        # Log an action
        secure_storage._audit_log("test_action", {"key": "value"})
        
        # Check audit cache
        assert len(secure_storage._audit_cache) == 1
        entry = secure_storage._audit_cache[0]
        assert entry['action'] == "test_action"
        assert entry['user_role'] == UserRole.ADMIN.value
        assert entry['details']['key'] == "value"
    
    def test_audit_cache_flush(self, secure_storage):
        """Test audit cache flushing."""
        # Add entries to cache
        for i in range(5):
            secure_storage._audit_log(f"action_{i}", {"index": i})
        
        assert len(secure_storage._audit_cache) == 5
        
        # Flush cache
        secure_storage._flush_audit_cache()
        
        # Cache should be empty after flush
        assert len(secure_storage._audit_cache) == 0
    
    @patch('devdocai.storage.secure_storage.OptimizedStorageManager.create_document')
    def test_create_document_with_security(self, mock_create, secure_storage):
        """Test document creation with security features."""
        mock_create.return_value = "doc123"
        
        document = {
            'id': 'doc123',
            'title': 'Test Document',
            'content': 'Contact: john@example.com, SSN: 123-45-6789'
        }
        
        doc_id = secure_storage.create_document(document)
        
        assert doc_id == "doc123"
        # Check that PII was detected and masked
        call_args = mock_create.call_args[0][0]
        assert "john@example.com" not in call_args['content']
        # Content should be encrypted
        assert secure_storage.encryption.is_encrypted_content(call_args['content'])
    
    @patch('devdocai.storage.secure_storage.OptimizedStorageManager.get_document')
    def test_get_document_with_decryption(self, mock_get, secure_storage):
        """Test document retrieval with decryption."""
        encrypted_content = secure_storage.encryption.encrypt_content(
            "Test content", "doc123"
        )
        
        mock_get.return_value = {
            'id': 'doc123',
            'title': 'Test',
            'content': encrypted_content
        }
        
        document = secure_storage.get_document('doc123')
        
        assert document['content'] == "Test content"
        # Audit log should be created
        assert any(e['action'] == 'document_accessed' 
                  for e in secure_storage._audit_cache)
    
    @patch('devdocai.storage.secure_storage.OptimizedStorageManager.update_document')
    def test_update_document_with_security(self, mock_update, secure_storage):
        """Test document update with security features."""
        mock_update.return_value = True
        
        updates = {
            'content': 'New content with email@example.com'
        }
        
        success = secure_storage.update_document('doc123', updates)
        
        assert success
        # Check that content was encrypted
        call_args = mock_update.call_args[0][1]
        assert secure_storage.encryption.is_encrypted_content(call_args['content'])
    
    @patch('devdocai.storage.secure_storage.OptimizedStorageManager.delete_document')
    def test_delete_document_with_secure_deletion(self, mock_delete, secure_storage, temp_dir):
        """Test document deletion with secure deletion."""
        mock_delete.return_value = True
        
        # Create cache file
        cache_file = temp_dir / 'cache' / 'doc123.cache'
        cache_file.write_text("cached data")
        
        success = secure_storage.delete_document('doc123')
        
        assert success
        # Cache file should be securely deleted
        assert not cache_file.exists()
        # Audit logs should be created
        audit_actions = [e['action'] for e in secure_storage._audit_cache]
        assert 'document_delete_requested' in audit_actions
        assert 'document_deleted' in audit_actions
    
    def test_security_status(self, secure_storage):
        """Test security status reporting."""
        status = secure_storage.get_security_status()
        
        assert status['pii_detection_enabled'] is True
        assert status['audit_logging_enabled'] is True
        assert status['secure_deletion_enabled'] is True
        assert status['current_user_role'] == UserRole.ADMIN.value
        assert AccessPermission.ADMIN.value in status['user_permissions']
        assert 'encryption_info' in status
        assert 'rate_limit_status' in status
    
    def test_security_scan(self, secure_storage):
        """Test security scan functionality."""
        scan_results = secure_storage.perform_security_scan()
        
        assert 'scan_timestamp' in scan_results
        assert 'vulnerabilities' in scan_results
        assert 'warnings' in scan_results
        assert 'info' in scan_results
        
        # Should include current user role in info
        assert any('ADMIN' in info for info in scan_results['info'])


class TestPIIDetector:
    """Test suite for PII detection."""
    
    @pytest.fixture
    def detector(self):
        """Create PII detector instance."""
        return PIIDetector(sensitivity="high")
    
    def test_email_detection(self, detector):
        """Test email address detection."""
        text = "Contact me at john.doe@example.com or admin@company.org"
        matches = detector.detect(text, [PIIType.EMAIL])
        
        assert len(matches) == 2
        assert matches[0].type == PIIType.EMAIL
        assert matches[0].value == "john.doe@example.com"
        assert matches[1].value == "admin@company.org"
    
    def test_phone_detection(self, detector):
        """Test phone number detection."""
        text = "Call me at 555-123-4567 or (555) 987-6543"
        matches = detector.detect(text, [PIIType.PHONE])
        
        assert len(matches) >= 1
        assert matches[0].type == PIIType.PHONE
    
    def test_ssn_detection(self, detector):
        """Test SSN detection."""
        text = "SSN: 123-45-6789"
        matches = detector.detect(text, [PIIType.SSN])
        
        assert len(matches) == 1
        assert matches[0].type == PIIType.SSN
        assert matches[0].value == "123-45-6789"
        assert matches[0].confidence >= 0.8  # High confidence with context
    
    def test_credit_card_detection(self, detector):
        """Test credit card detection with Luhn validation."""
        # Valid test credit card numbers
        text = "Visa: 4111111111111111, MasterCard: 5555555555554444"
        matches = detector.detect(text, [PIIType.CREDIT_CARD])
        
        assert len(matches) == 2
        assert all(m.type == PIIType.CREDIT_CARD for m in matches)
    
    def test_ip_address_detection(self, detector):
        """Test IP address detection."""
        text = "Server IP: 192.168.1.100, Public: 8.8.8.8"
        matches = detector.detect(text, [PIIType.IP_ADDRESS])
        
        assert len(matches) == 2
        assert matches[0].value == "192.168.1.100"
        assert matches[1].value == "8.8.8.8"
    
    def test_name_detection(self, detector):
        """Test name detection with context."""
        text = "Dear John Smith, This email is from Sarah Johnson."
        matches = detector.detect(text, [PIIType.NAME])
        
        assert len(matches) >= 2
        name_values = [m.value for m in matches]
        assert "John Smith" in name_values
        assert "Sarah Johnson" in name_values
    
    def test_api_key_detection(self, detector):
        """Test API key detection."""
        text = 'api_key="sk-1234567890abcdef", aws_access_key_id="AKIAIOSFODNN7EXAMPLE"'
        matches = detector.detect(text, [PIIType.API_KEY, PIIType.AWS_KEY])
        
        assert len(matches) >= 1
        assert any(m.type in [PIIType.API_KEY, PIIType.AWS_KEY] for m in matches)
    
    def test_medical_record_detection(self, detector):
        """Test medical record number detection."""
        text = "Patient MRN: 123456789, Medical Record #987654321"
        matches = detector.detect(text, [PIIType.MEDICAL_RECORD])
        
        assert len(matches) >= 1
        assert matches[0].type == PIIType.MEDICAL_RECORD
    
    def test_false_positive_handling(self, detector):
        """Test false positive reduction."""
        text = "Version 1.2.3.4, Test data: 000-00-0000, Example: test@example.com"
        matches = detector.detect(text)
        
        # Should have low confidence for known test values
        for match in matches:
            if match.value in ["000-00-0000", "test@example.com"]:
                assert match.confidence < 0.5
    
    def test_context_validation(self, detector):
        """Test context-based confidence scoring."""
        # With context keywords
        text1 = "My social security number is 123-45-6789"
        matches1 = detector.detect(text1, [PIIType.SSN])
        
        # Without context keywords
        text2 = "Random numbers: 123-45-6789"
        matches2 = detector.detect(text2, [PIIType.SSN])
        
        # First should have higher confidence due to context
        assert matches1[0].confidence > matches2[0].confidence
    
    def test_masking_strategies(self, detector):
        """Test different masking strategies."""
        text = "Email: john@example.com"
        matches = detector.detect(text, [PIIType.EMAIL])
        
        # Test REDACT strategy
        masked_redact = detector.mask(text, matches, MaskingStrategy.REDACT)
        assert "[EMAIL]" in masked_redact
        
        # Test PARTIAL strategy
        masked_partial = detector.mask(text, matches, MaskingStrategy.PARTIAL)
        assert "j***@example.com" in masked_partial
        
        # Test HASH strategy
        masked_hash = detector.mask(text, matches, MaskingStrategy.HASH)
        assert "[HASH:" in masked_hash
        
        # Test TOKENIZE strategy
        masked_token = detector.mask(text, matches, MaskingStrategy.TOKENIZE)
        assert "[TOKEN:" in masked_token
    
    def test_comprehensive_report(self, detector):
        """Test comprehensive PII report generation."""
        text = """
        John Doe (SSN: 123-45-6789)
        Email: john.doe@example.com
        Phone: 555-123-4567
        Credit Card: 4111-1111-1111-1111
        API Key: sk-1234567890abcdefghijklmnop
        """
        
        report = detector.generate_report(text)
        
        assert report['total_pii_found'] > 0
        assert 'ssn' in report['pii_by_type']
        assert 'email' in report['pii_by_type']
        assert report['risk_score'] > 0
        assert report['risk_level'] in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "MINIMAL"]
        assert len(report['recommendations']) > 0
    
    def test_performance_caching(self, detector):
        """Test performance optimization through caching."""
        text = "Test email: test@example.com" * 100
        
        # First detection (not cached)
        start1 = time.time()
        matches1 = detector.detect(text)
        time1 = time.time() - start1
        
        # Second detection (should be cached)
        start2 = time.time()
        matches2 = detector.detect(text)
        time2 = time.time() - start2
        
        # Cached should be faster
        assert time2 <= time1
        assert matches1 == matches2
    
    def test_sensitivity_levels(self):
        """Test different sensitivity levels."""
        text = "Possible SSN: 123-45-6789"
        
        # High sensitivity
        detector_high = PIIDetector(sensitivity="high")
        matches_high = detector_high.detect(text, [PIIType.SSN])
        
        # Low sensitivity
        detector_low = PIIDetector(sensitivity="low")
        matches_low = detector_low.detect(text, [PIIType.SSN])
        
        # High sensitivity should have higher confidence
        if matches_high and matches_low:
            assert matches_high[0].confidence >= matches_low[0].confidence


class TestIntegrationSecurity:
    """Integration tests for security features."""
    
    @pytest.fixture
    def secure_system(self, tmp_path):
        """Create complete secure storage system."""
        config = ConfigurationManager(str(tmp_path / "config.yml"))
        config.set('storage_path', tmp_path / 'storage')
        config.set('config_dir', tmp_path / 'config')
        config.set('cache_dir', tmp_path / 'cache')
        config.set('encryption_enabled', True)
        config.set('pii_detection_enabled', True)
        config.set('audit_logging_enabled', True)
        config.set('secure_deletion_enabled', True)
        config.set('sqlcipher_enabled', False)
        
        return SecureStorageManager(config, UserRole.ADMIN)
    
    def test_end_to_end_document_lifecycle(self, secure_system):
        """Test complete document lifecycle with security."""
        # Create document with PII
        doc_data = {
            'title': 'Customer Record',
            'content': 'Customer: John Doe, Email: john@example.com, SSN: 123-45-6789',
            'type': 'customer_data'
        }
        
        # Create document
        doc_id = secure_system.create_document(doc_data)
        assert doc_id is not None
        
        # Retrieve document
        retrieved = secure_system.get_document(doc_id)
        assert retrieved is not None
        # PII should be masked
        assert "123-45-6789" not in retrieved.get('content', '')
        
        # Update document
        updates = {'content': 'Updated with new email: newemail@example.com'}
        success = secure_system.update_document(doc_id, updates)
        assert success
        
        # Search for document
        results = secure_system.search_documents('Customer')
        assert len(results) > 0
        
        # Delete document
        deleted = secure_system.delete_document(doc_id)
        assert deleted
        
        # Verify deletion
        retrieved_after = secure_system.get_document(doc_id)
        assert retrieved_after is None
    
    def test_security_under_load(self, secure_system):
        """Test security features under load."""
        documents = []
        
        # Create multiple documents with PII
        for i in range(10):
            doc = {
                'title': f'Document {i}',
                'content': f'User {i}: user{i}@example.com, Phone: 555-000-{i:04d}'
            }
            doc_id = secure_system.create_document(doc)
            documents.append(doc_id)
        
        # Verify all documents created securely
        for doc_id in documents:
            doc = secure_system.get_document(doc_id)
            assert doc is not None
            # Email should be masked
            assert f"user" not in doc.get('content', '')
        
        # Clean up
        for doc_id in documents:
            secure_system.delete_document(doc_id)
    
    def test_audit_trail_completeness(self, secure_system):
        """Test audit trail captures all operations."""
        # Perform various operations
        doc_id = secure_system.create_document({'title': 'Test', 'content': 'Data'})
        secure_system.get_document(doc_id)
        secure_system.update_document(doc_id, {'content': 'Updated'})
        secure_system.search_documents('Test')
        secure_system.delete_document(doc_id)
        
        # Export audit logs
        logs = secure_system.export_audit_logs()
        
        # Verify all operations logged
        actions = [log['action'] for log in logs]
        assert 'document_created' in actions
        assert 'document_accessed' in actions
        assert 'document_updated' in actions
        assert 'documents_searched' in actions
        assert 'document_deleted' in actions


class TestPerformanceWithSecurity:
    """Test performance impact of security features."""
    
    @pytest.fixture
    def baseline_storage(self, tmp_path):
        """Create baseline storage without security."""
        config = ConfigurationManager(str(tmp_path / "config.yml"))
        config.set('storage_path', tmp_path / 'storage')
        config.set('encryption_enabled', False)
        config.set('pii_detection_enabled', False)
        config.set('audit_logging_enabled', False)
        config.set('secure_deletion_enabled', False)
        
        return SecureStorageManager(config, UserRole.ADMIN)
    
    @pytest.fixture
    def secure_storage(self, tmp_path):
        """Create storage with all security features."""
        config = ConfigurationManager(str(tmp_path / "config.yml"))
        config.set('storage_path', tmp_path / 'storage')
        config.set('encryption_enabled', True)
        config.set('pii_detection_enabled', True)
        config.set('audit_logging_enabled', True)
        config.set('secure_deletion_enabled', True)
        
        return SecureStorageManager(config, UserRole.ADMIN)
    
    def test_performance_overhead(self, baseline_storage, secure_storage):
        """Test that security overhead is <10%."""
        test_content = "Test document content " * 100
        
        # Baseline performance
        start = time.time()
        for i in range(10):
            doc_id = baseline_storage.create_document({
                'title': f'Doc {i}',
                'content': test_content
            })
            baseline_storage.get_document(doc_id)
        baseline_time = time.time() - start
        
        # Secure performance
        start = time.time()
        for i in range(10):
            doc_id = secure_storage.create_document({
                'title': f'Doc {i}',
                'content': test_content
            })
            secure_storage.get_document(doc_id)
        secure_time = time.time() - start
        
        # Calculate overhead
        overhead = ((secure_time - baseline_time) / baseline_time) * 100
        
        # Should be less than 10% overhead
        assert overhead < 10, f"Security overhead {overhead:.2f}% exceeds 10% target"