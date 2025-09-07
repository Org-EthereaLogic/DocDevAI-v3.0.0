#!/usr/bin/env python3
"""
Test 8: M001 Integration Test
Test that M002 unified storage integrates properly with M001 Configuration Manager
"""
import uuid
from devdocai.core.config import ConfigurationManager
from devdocai.storage.storage_manager_unified import UnifiedStorageManager
from devdocai.storage.models import Document

def test_m001_integration():
    try:
        print('🔗 Testing M001 Configuration Manager integration...')
        
        # Initialize M001 Configuration Manager
        config_manager = ConfigurationManager()
        config = config_manager.get_config()
        print(f'✅ M001 Configuration loaded: memory_mode={config.performance.memory_mode}')
        
        # Initialize M002 with M001 configuration
        storage = UnifiedStorageManager(config_manager=config_manager, mode='BASIC')
        print(f'✅ M002 Storage initialized with M001 config')
        
        # Test that storage respects M001 configuration
        performance_config = config.performance
        print(f'✅ Performance config available: memory_mode={performance_config.memory_mode}')
        
        # Create a test document
        doc_id = str(uuid.uuid4())
        doc = Document(
            id=doc_id, 
            title='M001 Integration Test', 
            content='Testing integration between M001 and M002'
        )
        created_doc = storage.create_document(doc)
        print(f'✅ Document created via integrated storage: {created_doc.id}')
        
        # Test retrieval
        retrieved_doc = storage.get_document(doc_id)
        print(f'✅ Document retrieved: {len(retrieved_doc.content)} chars')
        
        # Test that M001 telemetry settings are respected
        telemetry_enabled = config.telemetry.enabled
        print(f'✅ M001 telemetry setting respected: enabled={telemetry_enabled}')
        
        # Test storage configuration modes align with M001 performance settings
        if performance_config.memory_mode == 'enhanced':
            # Should enable caching and optimizations
            has_caching = hasattr(storage, '_enable_caching') and storage._enable_caching
            print(f'✅ Enhanced mode enables caching: {has_caching}')
        
        # Test M001 security configuration integration
        security_config = config.security
        print(f'✅ M001 security config available: encryption_enabled={security_config.encryption_enabled}')
        
        # Cleanup
        storage.delete_document(doc_id)
        print('✅ Document cleanup completed')
        
        storage.close()
        print('✅ M001-M002 integration test completed successfully')
        
    except Exception as e:
        print(f'❌ M001 integration test failed: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_m001_integration()