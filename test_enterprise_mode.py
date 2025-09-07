#!/usr/bin/env python3
"""
Test 7: ENTERPRISE Mode Operation
Test the combined performance + security features
"""
import uuid
import time
from devdocai.storage.storage_manager_unified import create_enterprise_storage
from devdocai.storage.models import Document

def test_enterprise():
    try:
        storage = create_enterprise_storage()
        
        # Test batch operations with security features
        print('🚀 Testing ENTERPRISE mode (Performance + Security)...')
        
        # Create multiple documents with PII content
        docs = []
        for i in range(5):
            doc_id = str(uuid.uuid4())
            content = f'Document {i}: User email: user{i}@example.com, phone: 555-{i:03d}-{i*100:04d}'
            doc = Document(id=doc_id, title=f'Enterprise Test Doc {i}', content=content)
            docs.append(doc)
        
        # Test batch creation (performance feature)
        start_time = time.time()
        created_docs = storage.batch_create_documents(docs)
        creation_time = time.time() - start_time
        print(f'✅ Batch created {len(created_docs)} documents in {creation_time:.3f}s')
        
        # Test security features are active
        security_features = []
        if hasattr(storage, 'pii_detector'):
            security_features.append('pii_detection')
        if hasattr(storage, '_audit_log'):
            security_features.append('auditing')
        if hasattr(storage, 'encryption_manager'):
            security_features.append('encryption')
        
        print(f'✅ Security features active: {security_features}')
        
        # Test performance features
        performance_features = []
        if hasattr(storage, '_cache'):
            performance_features.append('caching')
        if hasattr(storage, '_connection_pool'):
            performance_features.append('connection_pooling')
        if hasattr(storage, '_batch_size'):
            performance_features.append('batch_operations')
        
        print(f'✅ Performance features active: {performance_features}')
        
        # Test batch retrieval (performance)
        doc_ids = [doc.id for doc in created_docs]
        start_time = time.time()
        retrieved_docs = storage.batch_get_documents(doc_ids)
        retrieval_time = time.time() - start_time
        print(f'✅ Batch retrieved {len(retrieved_docs)} documents in {retrieval_time:.3f}s')
        
        # Test search functionality
        search_results = storage.search_documents("email", limit=10)
        print(f'✅ Search returned {len(search_results)} results')
        
        # Test that PII was detected and handled
        sample_doc = retrieved_docs[0]
        if '@example.com' not in sample_doc.content:
            print('✅ PII masking appears to be working (emails masked)')
        else:
            print('⚠️ PII still visible - masking may be disabled')
        
        storage.close()
        print('✅ ENTERPRISE mode test completed successfully')
        
    except Exception as e:
        print(f'❌ ENTERPRISE mode test failed: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_enterprise()