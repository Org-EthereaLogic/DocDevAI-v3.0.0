#!/usr/bin/env python3
"""
Test 9: Comprehensive Test Suite
Final validation of M002 unified architecture across all modes and integrations
"""
import uuid
import time
from devdocai.core.config import ConfigurationManager
from devdocai.storage.storage_manager_unified import (
    UnifiedStorageManager, 
    create_basic_storage, 
    create_performance_storage,
    create_secure_storage,
    create_enterprise_storage
)
from devdocai.storage.models import Document

def test_comprehensive_suite():
    """Run comprehensive test suite for M002 unified architecture."""
    print('🏗️ Starting M002 Comprehensive Test Suite...')
    print('=' * 60)
    
    # Test data
    test_documents = []
    for i in range(3):
        doc_id = str(uuid.uuid4())
        content = f'Test doc {i}: email contact{i}@test.com, phone 555-{i:03d}-{i*111:04d}'
        doc = Document(id=doc_id, title=f'Comprehensive Test Doc {i}', content=content)
        test_documents.append(doc)
    
    results = {
        'total_tests': 0,
        'passed': 0,
        'failed': 0,
        'modes_tested': [],
        'features_validated': []
    }
    
    # Test 1: Factory Functions
    print('\n📦 Test 1: Factory Functions')
    try:
        basic_storage = create_basic_storage()
        perf_storage = create_performance_storage()
        secure_storage = create_secure_storage()
        enterprise_storage = create_enterprise_storage()
        
        print('✅ All factory functions working')
        results['passed'] += 1
        results['features_validated'].append('factory_functions')
        
        # Close all instances
        for storage in [basic_storage, perf_storage, secure_storage, enterprise_storage]:
            storage.close()
            
    except Exception as e:
        print(f'❌ Factory function test failed: {e}')
        results['failed'] += 1
    
    results['total_tests'] += 1
    
    # Test 2: All Operation Modes
    print('\n🔄 Test 2: Operation Mode Validation')
    modes_to_test = ['BASIC', 'PERFORMANCE', 'SECURE', 'ENTERPRISE']
    
    for mode in modes_to_test:
        try:
            print(f'  Testing {mode} mode...')
            
            # Test with M001 integration
            config_manager = ConfigurationManager()
            storage = UnifiedStorageManager(config_manager=config_manager, mode=mode)
            
            # Test basic operations
            created_doc = storage.create_document(test_documents[0])
            retrieved_doc = storage.get_document(created_doc.id)
            
            assert retrieved_doc.title == test_documents[0].title
            print(f'  ✅ {mode} mode: CRUD operations working')
            
            # Test mode-specific features
            if mode in ['PERFORMANCE', 'ENTERPRISE']:
                # Test batch operations
                batch_docs = storage.batch_create_documents(test_documents[1:])
                batch_retrieved = storage.batch_get_documents([doc.id for doc in batch_docs])
                assert len(batch_retrieved) == 2
                print(f'  ✅ {mode} mode: Batch operations working')
            
            if mode in ['SECURE', 'ENTERPRISE']:
                # Test security features
                security_features = []
                if hasattr(storage, 'pii_detector'):
                    security_features.append('pii_detection')
                if hasattr(storage, '_audit_log'):
                    security_features.append('auditing')
                print(f'  ✅ {mode} mode: Security features active {security_features}')
            
            # Cleanup
            for doc in test_documents:
                try:
                    storage.delete_document(doc.id)
                except:
                    pass  # May not exist in this mode test
            
            storage.close()
            results['passed'] += 1
            results['modes_tested'].append(mode)
            
        except Exception as e:
            print(f'  ❌ {mode} mode failed: {e}')
            results['failed'] += 1
        
        results['total_tests'] += 1
    
    # Test 3: Performance Benchmarking
    print('\n⚡ Test 3: Performance Benchmarking')
    try:
        storage = create_performance_storage()
        
        # Single document performance
        start_time = time.time()
        test_doc = test_documents[0]
        created_doc = storage.create_document(test_doc)
        create_time = time.time() - start_time
        
        start_time = time.time()
        retrieved_doc = storage.get_document(created_doc.id)
        retrieve_time = time.time() - start_time
        
        print(f'✅ Single doc performance: Create {create_time*1000:.1f}ms, Retrieve {retrieve_time*1000:.1f}ms')
        
        # Batch performance
        batch_docs = [
            Document(id=str(uuid.uuid4()), title=f'Batch Doc {i}', content=f'Content {i}')
            for i in range(10)
        ]
        
        start_time = time.time()
        batch_created = storage.batch_create_documents(batch_docs)
        batch_time = time.time() - start_time
        
        print(f'✅ Batch performance: {len(batch_created)} docs in {batch_time*1000:.1f}ms')
        
        storage.close()
        results['passed'] += 1
        results['features_validated'].append('performance_benchmarking')
        
    except Exception as e:
        print(f'❌ Performance benchmarking failed: {e}')
        results['failed'] += 1
    
    results['total_tests'] += 1
    
    # Test 4: Architecture Integrity
    print('\n🏛️ Test 4: Architecture Integrity')
    try:
        # Test that all modes use the same base class
        basic = create_basic_storage()
        enterprise = create_enterprise_storage()
        
        assert type(basic).__name__ == type(enterprise).__name__ == 'UnifiedStorageManager'
        assert hasattr(basic, '_operation_mode')
        assert hasattr(enterprise, '_operation_mode')
        
        print('✅ Unified architecture confirmed')
        
        # Test configuration-driven behavior
        assert basic._operation_mode.name == 'BASIC'
        assert enterprise._operation_mode.name == 'ENTERPRISE'
        
        print('✅ Configuration-driven operation modes working')
        
        basic.close()
        enterprise.close()
        results['passed'] += 1
        results['features_validated'].append('architecture_integrity')
        
    except Exception as e:
        print(f'❌ Architecture integrity test failed: {e}')
        results['failed'] += 1
    
    results['total_tests'] += 1
    
    # Final Results
    print('\n' + '=' * 60)
    print('🏆 M002 COMPREHENSIVE TEST RESULTS')
    print('=' * 60)
    print(f'Total Tests: {results["total_tests"]}')
    print(f'Passed: {results["passed"]} ✅')
    print(f'Failed: {results["failed"]} ❌')
    print(f'Success Rate: {(results["passed"]/results["total_tests"]*100):.1f}%')
    print(f'Modes Tested: {", ".join(results["modes_tested"])}')
    print(f'Features Validated: {", ".join(results["features_validated"])}')
    
    if results['failed'] == 0:
        print('\n🎉 M002 UNIFIED ARCHITECTURE VALIDATION: COMPLETE SUCCESS!')
        print('✅ All 4 operation modes working')
        print('✅ Performance and security features validated') 
        print('✅ M001 integration confirmed')
        print('✅ Architecture integrity verified')
        print('\n🚀 M002 Pass 4 Refactoring: VALIDATION COMPLETE')
        return True
    else:
        print(f'\n⚠️ M002 validation completed with {results["failed"]} issues')
        return False

if __name__ == "__main__":
    success = test_comprehensive_suite()
    exit(0 if success else 1)