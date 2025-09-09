#!/usr/bin/env python3
"""
Debug M005 Issues - Focused Testing Script
DevDocAI v3.0.0

This script isolates and tests specific M005 issues:
1. SQLite concurrency problems
2. Security validation gaps
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from devdocai.core.config import ConfigurationManager
from devdocai.core.storage import StorageManager, Document
from devdocai.core.tracking import TrackingMatrix, RelationshipType, TrackingError


def debug_sqlite_issue():
    """Debug the SQLite concurrency issue."""
    print("🔍 DEBUGGING SQLite Concurrency Issue")
    print("=" * 50)
    
    try:
        # Test basic storage initialization
        config = ConfigurationManager()
        storage = StorageManager(config)
        
        print(f"✅ Storage created: {storage.db_path}")
        print(f"✅ Encryption enabled: {storage._encryption_enabled}")
        
        # Test database initialization
        storage._initialize_database()
        print("✅ Database initialization called")
        
        # Test basic document creation
        test_doc = Document(
            id="test_doc_1",
            content="test content",
            type="test",
            metadata={}
        )
        doc_id = storage.save_document(test_doc)
        print(f"✅ Basic document save successful: {doc_id}")
        
        # Test document retrieval
        retrieved = storage.get_document(doc_id)
        print(f"✅ Document retrieval successful: {retrieved.id if retrieved else 'None'}")
        
        # Now test with TrackingMatrix
        tracking = TrackingMatrix(config, storage)
        print("✅ TrackingMatrix initialization successful")
        
        # Test relationship creation
        doc2 = Document(
            id="test_doc_2",
            content="test content 2",
            type="test",
            metadata={}
        )
        doc2_id = storage.save_document(doc2)
        
        tracking.add_relationship(doc_id, doc2_id, RelationshipType.REFERENCES)
        print("✅ Basic relationship creation successful")
        
        print("\n🎯 RESULT: Basic functionality works - issue may be concurrency-specific")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def debug_security_validation():
    """Debug the security validation issues."""
    print("\n🛡️ DEBUGGING Security Validation Issues")
    print("=" * 50)
    
    try:
        config = ConfigurationManager()
        storage = StorageManager(config)
        tracking = TrackingMatrix(config, storage)
        
        print("✅ Components initialized")
        
        # Create normal documents first
        doc1 = Document(id="normal_doc_1", content="content", type="test", metadata={})
        doc2 = Document(id="normal_doc_2", content="content", type="test", metadata={})
        
        doc1_id = storage.save_document(doc1)
        doc2_id = storage.save_document(doc2)
        print("✅ Normal documents created")
        
        # Test 1: Path traversal in add_relationship
        print("\n🔍 Test 1: Path traversal validation")
        try:
            malicious_id = "../../../etc/passwd"
            tracking.add_relationship(malicious_id, doc1_id, RelationshipType.REFERENCES)
            print("❌ Path traversal NOT prevented - relationship created")
        except Exception as e:
            if "path traversal" in str(e).lower() or "invalid" in str(e).lower():
                print("✅ Path traversal prevented")
            else:
                print(f"❓ Unclear: {str(e)}")
        
        # Test 2: XSS in relationship metadata
        print("\n🔍 Test 2: XSS metadata sanitization")
        try:
            xss_metadata = {"note": "<script>alert('xss')</script>"}
            tracking.add_relationship(doc1_id, doc2_id, RelationshipType.REFERENCES, metadata=xss_metadata)
            
            # Check if metadata was sanitized
            relationships = tracking.get_all_relationships()
            xss_found = False
            for rel in relationships:
                if rel.get('metadata') and "<script>" in str(rel['metadata']):
                    xss_found = True
                    break
            
            if xss_found:
                print("❌ XSS NOT sanitized - found in relationship metadata")
            else:
                print("✅ XSS sanitized or prevented")
                
        except Exception as e:
            print(f"❓ XSS test error: {str(e)}")
        
        # Test 3: Check if security validation is actually implemented
        print("\n🔍 Test 3: Validation implementation check")
        
        # Check if tracking has validation attribute
        if hasattr(tracking, 'validation'):
            print("✅ Validation attribute exists")
            
            # Check validation methods
            validation = tracking.validation
            if hasattr(validation, 'validate_document_id'):
                print("✅ validate_document_id method exists")
                
                # Test validation directly
                try:
                    validation.validate_document_id("../../../etc/passwd")
                    print("❌ Direct validation did NOT reject malicious ID")
                except Exception as e:
                    print(f"✅ Direct validation works: {str(e)}")
            else:
                print("❌ validate_document_id method missing")
                
            if hasattr(validation, 'sanitize_metadata'):
                print("✅ sanitize_metadata method exists")
                
                # Test sanitization directly
                test_metadata = {"note": "<script>alert('test')</script>"}
                sanitized = validation.sanitize_metadata(test_metadata)
                if "<script>" in str(sanitized):
                    print("❌ Direct sanitization did NOT work")
                else:
                    print("✅ Direct sanitization works")
            else:
                print("❌ sanitize_metadata method missing")
        else:
            print("❌ Validation attribute missing from TrackingMatrix")
            
        print("\n🎯 RESULT: Security validation implementation check complete")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def debug_concurrent_lite():
    """Debug concurrency with minimal test."""
    print("\n🔄 DEBUGGING Concurrent Access (Lite)")
    print("=" * 50)
    
    try:
        config = ConfigurationManager()
        storage = StorageManager(config)
        tracking = TrackingMatrix(config, storage)
        
        # Test simple sequential operations first
        print("📝 Testing sequential operations...")
        docs = []
        for i in range(5):
            doc = Document(
                id=f"seq_doc_{i}",
                content=f"content {i}",
                type="test",
                metadata={}
            )
            doc_id = storage.save_document(doc)
            docs.append(doc_id)
        
        print(f"✅ Sequential: {len(docs)} documents created")
        
        # Test simple concurrent operations with threading
        print("🔄 Testing basic threading...")
        import threading
        
        def create_single_doc(thread_id):
            try:
                doc = Document(
                    id=f"thread_doc_{thread_id}",
                    content=f"thread content {thread_id}",
                    type="test",
                    metadata={}
                )
                doc_id = storage.save_document(doc)
                print(f"Thread {thread_id}: Created {doc_id}")
                return doc_id
            except Exception as e:
                print(f"Thread {thread_id}: ERROR - {str(e)}")
                return None
        
        # Create just 2 threads
        threads = []
        results = {}
        
        def thread_wrapper(thread_id):
            results[thread_id] = create_single_doc(thread_id)
        
        for i in range(2):
            thread = threading.Thread(target=thread_wrapper, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        successful = sum(1 for r in results.values() if r is not None)
        print(f"✅ Concurrent: {successful}/2 documents created successfully")
        
        if successful == 2:
            print("🎯 RESULT: Basic concurrency works")
        else:
            print("❌ RESULT: Concurrency issues detected")
            
        return successful == 2
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run focused debugging tests."""
    print("🚀 M005 Focused Debugging Session")
    print("=" * 60)
    
    results = {}
    
    # Run debugging tests
    results["SQLite Basic"] = debug_sqlite_issue()
    results["Security Validation"] = debug_security_validation()
    results["Concurrency Lite"] = debug_concurrent_lite()
    
    # Summary
    print("\n" + "=" * 60)
    print("🎯 DEBUGGING SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
    
    all_passed = all(results.values())
    if all_passed:
        print("\n🏆 All debugging tests passed - issues may be verification-script specific")
    else:
        print("\n⚠️ Core issues identified - need implementation fixes")


if __name__ == "__main__":
    main()