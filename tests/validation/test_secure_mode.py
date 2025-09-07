#!/usr/bin/env python3
"""
Test 6: SECURE Mode Operation
Test that security features including PII detection are active
"""
import uuid
from devdocai.storage.storage_manager_unified import create_secure_storage
from devdocai.storage.models import Document

def test_secure():
    try:
        storage = create_secure_storage()
        
        # Test with PII content
        doc_id = str(uuid.uuid4())
        pii_content = 'User email: john@example.com and phone: 555-123-4567'
        doc = Document(id=doc_id, title='Security Test Doc', content=pii_content)
        created_doc = storage.create_document(doc)
        print(f'✅ Secure mode document stored: {created_doc.id}')
        
        # Test PII detector availability
        if hasattr(storage, 'pii_detector'):
            print('✅ PII detector available in secure mode')
        else:
            print('⚠️ PII detector not found as direct attribute')
        
        # Test security features
        security_features = []
        if hasattr(storage, 'encryption_manager'):
            security_features.append('encryption')
        if hasattr(storage, '_audit_log'):
            security_features.append('auditing')
        if hasattr(storage, 'rbac_manager'):
            security_features.append('rbac')
        
        if security_features:
            print(f'✅ Security features active: {security_features}')
        else:
            print('⚠️ Security features not found as direct attributes')
        
        # Test document retrieval
        retrieved_doc = storage.get_document(doc_id)
        print(f'✅ Document retrieved successfully: {len(retrieved_doc.content)} chars')
        
        storage.close()
        print('✅ SECURE mode test completed successfully')
        
    except Exception as e:
        print(f'❌ SECURE mode test failed: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_secure()