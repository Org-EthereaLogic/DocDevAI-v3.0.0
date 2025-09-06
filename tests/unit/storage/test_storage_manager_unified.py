"""
Test suite for M002 Local Storage System - Unified Storage Manager

Comprehensive tests covering all 4 operation modes:
- BASIC: Core functionality
- PERFORMANCE: Caching, batching, FTS5
- SECURE: PII detection, RBAC, audit logging
- ENTERPRISE: Full feature set
"""

import os
import tempfile
import pytest
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from devdocai.storage.storage_manager_unified import (
    UnifiedStorageManager,
    OperationMode,
    UserRole,
    AccessPermission,
    StorageError,
    create_storage_manager,
    create_basic_storage,
    create_performance_storage,
    create_secure_storage,
    create_enterprise_storage
)
from devdocai.storage.config_unified import (
    StorageConfig,
    StorageMode,
    StorageModeSelector,
    get_preset_config
)
from devdocai.storage.models import Document, DocumentMetadata, DocumentStatus
from devdocai.core.config import ConfigurationManager, MemoryMode


class TestUnifiedStorageManager:
    """Test unified storage manager across all modes."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_storage.db"
        self.config = ConfigurationManager()
    
    def teardown_method(self):
        """Cleanup test environment."""
        # Clean up any open connections
        if hasattr(self, 'storage') and self.storage:
            self.storage.close()
        
        # Remove test files
        if self.db_path.exists():
            self.db_path.unlink()
        
        # Remove temp directory
        for file in Path(self.temp_dir).glob('*'):
            file.unlink()
        os.rmdir(self.temp_dir)
    
    def create_test_document(self, doc_id: str = "test-1") -> Document:
        """Create a test document."""
        return Document(
            id=doc_id,
            title=f"Test Document {doc_id}",
            content=f"This is test content for document {doc_id}",
            content_type="markdown",
            metadata=DocumentMetadata(
                tags=["test", "unit"],
                category="testing",
                author="test_user"
            )
        )
    
    # Test BASIC mode
    
    def test_basic_mode_initialization(self):
        """Test basic mode initialization."""
        self.storage = UnifiedStorageManager(
            db_path=self.db_path,
            config=self.config,
            mode=OperationMode.BASIC
        )
        
        assert self.storage.mode == OperationMode.BASIC
        assert not self.storage._enable_caching
        assert not self.storage._enable_batching
        assert not self.storage._enable_fts5
        assert not self.storage._enable_pii_detection
        assert not self.storage._enable_audit_logging
    
    def test_basic_mode_crud_operations(self):
        """Test CRUD operations in basic mode."""
        self.storage = create_basic_storage(config=self.config, db_path=self.db_path)
        
        # Create
        doc = self.create_test_document("basic-1")
        created = self.storage.create_document(doc)
        assert created.id == "basic-1"
        assert created.title == "Test Document basic-1"
        
        # Read
        retrieved = self.storage.get_document("basic-1")
        assert retrieved is not None
        assert retrieved.id == "basic-1"
        
        # Update
        retrieved.title = "Updated Title"
        updated = self.storage.update_document(retrieved)
        assert updated.title == "Updated Title"
        
        # Delete
        deleted = self.storage.delete_document("basic-1")
        assert deleted is True
        
        # Verify deletion
        not_found = self.storage.get_document("basic-1")
        assert not_found is None
    
    def test_basic_mode_search(self):
        """Test search functionality in basic mode."""
        self.storage = create_basic_storage(config=self.config, db_path=self.db_path)
        
        # Create test documents
        for i in range(5):
            doc = self.create_test_document(f"search-{i}")
            doc.content = f"Document {i} contains searchable content"
            self.storage.create_document(doc)
        
        # Search
        results = self.storage.search_documents("searchable")
        assert len(results) > 0
        assert all("searchable" in r.document.content.lower() for r in results)
    
    # Test PERFORMANCE mode
    
    def test_performance_mode_initialization(self):
        """Test performance mode initialization."""
        self.storage = UnifiedStorageManager(
            db_path=self.db_path,
            config=self.config,
            mode=OperationMode.PERFORMANCE
        )
        
        assert self.storage.mode == OperationMode.PERFORMANCE
        assert self.storage._enable_caching
        assert self.storage._enable_batching
        assert self.storage._enable_fts5
        assert self.storage._enable_streaming
        assert not self.storage._enable_pii_detection
        assert not self.storage._enable_audit_logging
    
    def test_performance_mode_caching(self):
        """Test caching functionality in performance mode."""
        self.storage = create_performance_storage(config=self.config, db_path=self.db_path)
        
        # Create document
        doc = self.create_test_document("cache-1")
        created = self.storage.create_document(doc)
        
        # First retrieval (cache miss)
        cache_stats_before = self.storage.cache.get_stats()
        retrieved1 = self.storage.get_document("cache-1")
        
        # Second retrieval (cache hit)
        retrieved2 = self.storage.get_document("cache-1")
        cache_stats_after = self.storage.cache.get_stats()
        
        assert retrieved1.id == retrieved2.id
        assert cache_stats_after['hits'] > cache_stats_before['hits']
    
    def test_performance_mode_batch_operations(self):
        """Test batch operations in performance mode."""
        self.storage = create_performance_storage(config=self.config, db_path=self.db_path)
        
        # Create batch of documents
        documents = [self.create_test_document(f"batch-{i}") for i in range(10)]
        
        start_time = time.time()
        created_docs = self.storage.create_documents_batch(documents)
        batch_time = time.time() - start_time
        
        assert len(created_docs) == 10
        assert all(doc.id.startswith("batch-") for doc in created_docs)
        
        # Verify batch was faster than individual operations would be
        assert batch_time < 1.0  # Should be fast
    
    def test_performance_mode_streaming(self):
        """Test document streaming in performance mode."""
        self.storage = create_performance_storage(config=self.config, db_path=self.db_path)
        
        # Create documents
        for i in range(20):
            doc = self.create_test_document(f"stream-{i}")
            self.storage.create_document(doc)
        
        # Stream documents
        batches = list(self.storage.stream_documents(batch_size=5))
        
        assert len(batches) >= 4  # 20 docs / 5 per batch
        assert all(len(batch) <= 5 for batch in batches)
    
    # Test SECURE mode
    
    def test_secure_mode_initialization(self):
        """Test secure mode initialization."""
        self.storage = UnifiedStorageManager(
            db_path=self.db_path,
            config=self.config,
            mode=OperationMode.SECURE,
            user_role=UserRole.DEVELOPER
        )
        
        assert self.storage.mode == OperationMode.SECURE
        assert self.storage._enable_pii_detection
        assert self.storage._enable_audit_logging
        assert self.storage._enable_rbac
        assert self.storage._enable_secure_deletion
        assert self.storage._enable_rate_limiting
    
    def test_secure_mode_rbac(self):
        """Test role-based access control in secure mode."""
        # Test with VIEWER role (read-only)
        self.storage = create_secure_storage(
            config=self.config,
            db_path=self.db_path,
            user_role=UserRole.VIEWER
        )
        
        # Create should fail for viewer
        doc = self.create_test_document("rbac-1")
        with pytest.raises(PermissionError):
            self.storage.create_document(doc)
        
        # Test with DEVELOPER role (read-write)
        self.storage.close()
        self.storage = create_secure_storage(
            config=self.config,
            db_path=self.db_path,
            user_role=UserRole.DEVELOPER
        )
        
        # Create should succeed for developer
        created = self.storage.create_document(doc)
        assert created.id == "rbac-1"
        
        # Delete should fail for developer
        with pytest.raises(PermissionError):
            self.storage.delete_document("rbac-1")
    
    def test_secure_mode_pii_detection(self):
        """Test PII detection in secure mode."""
        self.storage = create_secure_storage(
            config=self.config,
            db_path=self.db_path,
            user_role=UserRole.DEVELOPER
        )
        
        # Create document with PII
        doc = self.create_test_document("pii-1")
        doc.content = "Contact John Doe at john.doe@example.com or 555-123-4567"
        
        created = self.storage.create_document(doc)
        
        # PII should be masked
        assert "john.doe@example.com" not in created.content
        assert "555-123-4567" not in created.content
        assert "***@example.com" in created.content or "[REDACTED]" in created.content
    
    def test_secure_mode_rate_limiting(self):
        """Test rate limiting in secure mode."""
        self.storage = create_secure_storage(
            config=self.config,
            db_path=self.db_path,
            user_role=UserRole.DEVELOPER
        )
        
        # Set aggressive rate limit for testing
        self.storage._rate_limit_max_requests = 5
        self.storage._rate_limit_window = 1  # 1 second window
        
        # Make requests up to limit
        for i in range(5):
            doc = self.create_test_document(f"rate-{i}")
            self.storage.create_document(doc)
        
        # Next request should fail
        doc = self.create_test_document("rate-exceed")
        with pytest.raises(StorageError, match="Rate limit"):
            self.storage.create_document(doc)
    
    # Test ENTERPRISE mode
    
    def test_enterprise_mode_all_features(self):
        """Test that enterprise mode has all features enabled."""
        self.storage = create_enterprise_storage(
            config=self.config,
            db_path=self.db_path,
            user_role=UserRole.ADMIN
        )
        
        assert self.storage.mode == OperationMode.ENTERPRISE
        
        # Performance features
        assert self.storage._enable_caching
        assert self.storage._enable_batching
        assert self.storage._enable_fts5
        assert self.storage._enable_streaming
        
        # Security features
        assert self.storage._enable_pii_detection
        assert self.storage._enable_audit_logging
        assert self.storage._enable_rbac
        assert self.storage._enable_secure_deletion
        assert self.storage._enable_rate_limiting
    
    def test_enterprise_mode_combined_features(self):
        """Test combined performance and security features in enterprise mode."""
        self.storage = create_enterprise_storage(
            config=self.config,
            db_path=self.db_path,
            user_role=UserRole.ADMIN
        )
        
        # Create batch with PII detection
        documents = []
        for i in range(5):
            doc = self.create_test_document(f"enterprise-{i}")
            doc.content = f"Document {i} with email test{i}@example.com"
            documents.append(doc)
        
        created_docs = self.storage.create_documents_batch(documents)
        
        # Verify batch creation worked
        assert len(created_docs) == 5
        
        # Verify PII was masked
        for doc in created_docs:
            assert "@example.com" not in doc.content or "***@" in doc.content
        
        # Verify caching works
        cache_stats_before = self.storage.cache.get_stats()
        retrieved = self.storage.get_document("enterprise-0")
        retrieved_again = self.storage.get_document("enterprise-0")
        cache_stats_after = self.storage.cache.get_stats()
        
        assert cache_stats_after['hits'] > cache_stats_before['hits']
    
    # Test configuration system
    
    def test_storage_config_mode_defaults(self):
        """Test that StorageConfig applies correct mode defaults."""
        # Basic mode config
        basic_config = StorageConfig(mode=StorageMode.BASIC)
        basic_config.apply_mode_defaults()
        assert not basic_config.enable_caching
        assert not basic_config.enable_pii_detection
        
        # Performance mode config
        perf_config = StorageConfig(mode=StorageMode.PERFORMANCE)
        perf_config.apply_mode_defaults()
        assert perf_config.enable_caching
        assert perf_config.enable_batching
        assert not perf_config.enable_pii_detection
        
        # Secure mode config
        secure_config = StorageConfig(mode=StorageMode.SECURE)
        secure_config.apply_mode_defaults()
        assert not secure_config.enable_caching
        assert secure_config.enable_pii_detection
        assert secure_config.enable_rbac
        
        # Enterprise mode config
        enterprise_config = StorageConfig(mode=StorageMode.ENTERPRISE)
        enterprise_config.apply_mode_defaults()
        assert enterprise_config.enable_caching
        assert enterprise_config.enable_pii_detection
    
    def test_preset_configurations(self):
        """Test preset configurations."""
        # Development preset
        dev_config = get_preset_config("development")
        assert dev_config.mode == StorageMode.BASIC
        assert not dev_config.enable_encryption
        
        # Production preset
        prod_config = get_preset_config("production")
        assert prod_config.mode == StorageMode.ENTERPRISE
        assert prod_config.enable_sqlcipher
        assert prod_config.enable_secure_deletion
        
        # High security preset
        security_config = get_preset_config("high_security")
        assert security_config.mode == StorageMode.SECURE
        assert security_config.enable_pii_detection
        assert security_config.enable_audit_logging
    
    def test_mode_selector(self):
        """Test intelligent mode selection."""
        # Performance critical
        mode = StorageModeSelector.recommend_mode(
            performance_critical=True,
            security_critical=False
        )
        assert mode == StorageMode.PERFORMANCE
        
        # Security critical
        mode = StorageModeSelector.recommend_mode(
            performance_critical=False,
            security_critical=True
        )
        assert mode == StorageMode.SECURE
        
        # Production environment with security
        mode = StorageModeSelector.recommend_mode(
            production_environment=True,
            security_critical=True
        )
        assert mode == StorageMode.ENTERPRISE
        
        # Resource constrained
        mode = StorageModeSelector.recommend_mode(
            resource_constrained=True,
            data_volume="low"
        )
        assert mode == StorageMode.BASIC
    
    # Test factory functions
    
    def test_factory_functions(self):
        """Test factory functions for creating storage managers."""
        # Basic factory
        basic = create_basic_storage(config=self.config, db_path=self.db_path)
        assert basic.mode == OperationMode.BASIC
        basic.close()
        
        # Performance factory
        perf = create_performance_storage(config=self.config, db_path=self.db_path)
        assert perf.mode == OperationMode.PERFORMANCE
        perf.close()
        
        # Secure factory
        secure = create_secure_storage(config=self.config, db_path=self.db_path)
        assert secure.mode == OperationMode.SECURE
        secure.close()
        
        # Enterprise factory
        enterprise = create_enterprise_storage(config=self.config, db_path=self.db_path)
        assert enterprise.mode == OperationMode.ENTERPRISE
        enterprise.close()
        
        # Generic factory with mode string
        custom = create_storage_manager("performance", config=self.config, db_path=self.db_path)
        assert custom.mode == OperationMode.PERFORMANCE
        custom.close()
    
    # Test system information
    
    def test_system_info_reporting(self):
        """Test system information reporting across modes."""
        for mode in [OperationMode.BASIC, OperationMode.PERFORMANCE, 
                    OperationMode.SECURE, OperationMode.ENTERPRISE]:
            storage = UnifiedStorageManager(
                db_path=self.db_path,
                config=self.config,
                mode=mode,
                user_role=UserRole.ADMIN if mode in [OperationMode.SECURE, OperationMode.ENTERPRISE] else None
            )
            
            info = storage.get_system_info()
            
            assert info['operation_mode'] == mode.value
            assert 'features' in info
            assert 'performance' in info
            
            # Check mode-specific info
            if mode in [OperationMode.PERFORMANCE, OperationMode.ENTERPRISE]:
                assert info['features']['caching'] is True
                if storage._enable_caching:
                    assert 'cache' in info
            
            if mode in [OperationMode.SECURE, OperationMode.ENTERPRISE]:
                assert info['features']['pii_detection'] is True
                assert 'security' in info
            
            storage.close()
    
    # Test performance metrics
    
    def test_performance_metrics(self):
        """Test performance metrics collection."""
        self.storage = create_performance_storage(config=self.config, db_path=self.db_path)
        
        # Perform operations
        for i in range(10):
            doc = self.create_test_document(f"perf-{i}")
            self.storage.create_document(doc)
            self.storage.get_document(f"perf-{i}")
        
        # Get metrics
        metrics = self.storage.get_performance_metrics()
        
        assert metrics['total_operations'] >= 20  # 10 creates + 10 gets
        assert metrics['operations_per_second'] > 0
        assert metrics['memory_mode'] == MemoryMode.STANDARD.value
    
    # Test backward compatibility
    
    def test_backward_compatibility(self):
        """Test that unified manager is backward compatible with existing code."""
        # Test that basic mode behaves like original LocalStorageManager
        self.storage = UnifiedStorageManager(
            db_path=self.db_path,
            config=self.config,
            mode=OperationMode.BASIC
        )
        
        # All standard operations should work
        doc = self.create_test_document("compat-1")
        created = self.storage.create_document(doc)
        retrieved = self.storage.get_document("compat-1")
        
        assert created.id == retrieved.id
        assert hasattr(self.storage, 'repository')
        assert hasattr(self.storage, 'db_manager')
        assert hasattr(self.storage, 'encryption')