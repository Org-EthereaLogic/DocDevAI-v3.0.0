#!/usr/bin/env python3
"""
M005 Tracking Matrix - Real-World Verification Script
DevDocAI v3.0.0 - Human-Verifiable Test Suite

This script provides step-by-step verification of M005 functionality
with clear outputs for human validation.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import json
import time
from devdocai.core.tracking import TrackingMatrix, RelationshipType, TrackingError
from devdocai.core.config import ConfigurationManager
from devdocai.core.storage import StorageManager, Document


def print_header(test_name: str):
    """Print a clear test header."""
    print(f"\n{'='*60}")
    print(f"🧪 TEST: {test_name}")
    print(f"{'='*60}")


def print_result(success: bool, message: str):
    """Print test result with clear formatting."""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status}: {message}")


def test_1_basic_initialization():
    """Test 1: Basic Initialization and Setup"""
    print_header("Basic Initialization and Setup")
    
    try:
        # Initialize configuration
        config = ConfigurationManager()
        print("✅ Configuration Manager initialized")
        
        # Initialize storage
        storage = StorageManager(config)
        print("✅ Storage Manager initialized")
        
        # Initialize tracking matrix
        tracking = TrackingMatrix(config, storage)
        print("✅ Tracking Matrix initialized")
        
        # Verify core components
        assert hasattr(tracking, 'graph')
        assert hasattr(tracking, 'config')
        assert hasattr(tracking, 'storage')
        print("✅ Core components verified")
        
        print_result(True, "Basic initialization completed successfully")
        return tracking, storage
        
    except Exception as e:
        import traceback
        print_result(False, f"Initialization failed: {str(e)}")
        traceback.print_exc() # Print the full traceback
        return None, None


def test_2_document_creation_and_relationships(tracking, storage):
    """Test 2: Document Creation and Relationship Management"""
    print_header("Document Creation and Relationship Management")
    
    if not tracking or not storage:
        print_result(False, "Skipping - previous test failed")
        return []
    
    try:
        # Create test documents
        docs = []
        doc_data = [
            {"title": "Project Requirements", "type": "requirements", "content": "Project requirements document"},
            {"title": "Software Design", "type": "design", "content": "Software design document"},
            {"title": "Implementation Guide", "type": "implementation", "content": "Implementation guide"},
            {"title": "Test Plan", "type": "test", "content": "Test plan document"},
            {"title": "User Manual", "type": "user_guide", "content": "User manual"}
        ]
        
        for data in doc_data:
            doc = Document(
                id=data["title"],
                content=data["content"],
                type=data["type"],
                metadata={"category": "test_doc"}
            )
            doc_id = storage.save_document(doc)
            docs.append((doc_id, data["title"]))
            print(f"✅ Created document: {data['title']} (ID: {doc_id})")
        
        # Add relationships
        relationships = [
            (docs[0][0], docs[1][0], RelationshipType.REFERENCES, "Design references requirements"),
            (docs[1][0], docs[2][0], RelationshipType.IMPLEMENTS, "Implementation follows design"),
            (docs[0][0], docs[3][0], RelationshipType.VALIDATES, "Tests validate requirements"),
            (docs[2][0], docs[4][0], RelationshipType.DOCUMENTS, "Manual documents implementation"),
            (docs[3][0], docs[1][0], RelationshipType.VALIDATES, "Tests validate design")
        ]
        
        for source, target, rel_type, description in relationships:
            tracking.add_relationship(source, target, rel_type, metadata={"description": description})
            print(f"✅ Added relationship: {rel_type.value} ({description})")
        
        print_result(True, f"Created {len(docs)} documents with {len(relationships)} relationships")
        return docs
        
    except Exception as e:
        print_result(False, f"Document creation failed: {str(e)}")
        return []


def test_3_relationship_queries(tracking, docs):
    """Test 3: Relationship Queries and Analysis"""
    print_header("Relationship Queries and Analysis")
    
    if not tracking or not docs:
        print_result(False, "Skipping - previous test failed")
        return
    
    try:
        # Test direct dependencies
        doc_id = docs[0][0]  # Requirements doc
        dependencies = tracking.get_dependencies(doc_id)
        print(f"✅ Dependencies for '{docs[0][1]}': {len(dependencies)} found")
        for dep in dependencies:
            print(f"   - {dep['target_id']} ({dep['relationship_type']})")
        
        # Test dependents
        dependents = tracking.get_dependents(doc_id)
        print(f"✅ Dependents for '{docs[0][1]}': {len(dependents)} found")
        for dep in dependents:
            print(f"   - {dep['source_id']} ({dep['relationship_type']})")
        
        # Test relationship existence
        exists = tracking.has_relationship(docs[0][0], docs[1][0])
        print(f"✅ Relationship exists check: {exists}")
        
        # Test all relationships
        all_rels = tracking.get_all_relationships()
        print(f"✅ Total relationships in matrix: {len(all_rels)}")
        
        print_result(True, "Relationship queries completed successfully")
        
    except Exception as e:
        print_result(False, f"Relationship queries failed: {str(e)}")


def test_4_impact_analysis(tracking, docs):
    """Test 4: Impact Analysis and Change Propagation"""
    print_header("Impact Analysis and Change Propagation")
    
    if not tracking or not docs:
        print_result(False, "Skipping - previous test failed")
        return
    
    try:
        # Analyze impact of changing requirements document
        doc_id = docs[0][0]
        impact = tracking.analyze_impact(doc_id)
        
        print(f"✅ Impact analysis for '{docs[0][1]}':")
        print(f"   - Directly affected documents: {impact.direct_impact_count}")
        print(f"   - Indirectly affected documents: {impact.indirect_impact_count}")
        print(f"   - Total affected documents: {impact.total_affected}")
        print(f"   - Estimated effort (hours): {impact.estimated_effort}")
        
        # Show affected documents
        if impact.direct_impact:
            print("   Direct impacts:")
            for doc in impact.direct_impact:
                print(f"     - {doc}")
        
        if impact.indirect_impact:
            print("   Indirect impacts:")
            for doc in impact.indirect_impact:
                print(f"     - {doc}")
        
        # Test with different document
        impact2 = tracking.analyze_impact(docs[1][0])  # Design doc
        print(f"✅ Impact analysis for '{docs[1][1]}': {impact2.total_affected} documents affected")
        
        print_result(True, "Impact analysis completed successfully")
        
    except Exception as e:
        print_result(False, f"Impact analysis failed: {str(e)}")


def test_5_circular_reference_detection(tracking, docs):
    """Test 5: Circular Reference Detection"""
    print_header("Circular Reference Detection")
    
    if not tracking or not docs:
        print_result(False, "Skipping - previous test failed")
        return
    
    try:
        # Check for existing cycles
        cycles = tracking.detect_circular_references()
        print(f"✅ Initial circular references detected: {len(cycles)}")
        
        # Create a circular reference intentionally
        if len(docs) >= 3:
            # Enable testing mode to allow cycles
            tracking._allow_cycles = True
            
            # Add a cycle: docs[1] -> docs[2] -> docs[1]
            tracking.add_relationship(
                docs[2][0], docs[1][0], 
                RelationshipType.REFERENCES, 
                metadata={"description": "Test circular reference"}
            )
            print("✅ Added potential circular reference")
            
            # Detect cycles again
            cycles = tracking.detect_circular_references()
            print(f"✅ Circular references after addition: {len(cycles)}")
            
            if cycles:
                print("   Detected cycles:")
                for i, cycle in enumerate(cycles):
                    print(f"     Cycle {i+1}: {' -> '.join(cycle)} -> {cycle[0]}")
            
            # Remove the circular reference
            tracking.remove_relationship(docs[2][0], docs[1][0])
            print("✅ Removed circular reference")
            
            cycles = tracking.detect_circular_references()
            print(f"✅ Circular references after removal: {len(cycles)}")
            
            # Disable testing mode
            tracking._allow_cycles = False
        
        print_result(True, "Circular reference detection completed successfully")
        
    except Exception as e:
        print_result(False, f"Circular reference detection failed: {str(e)}")


def test_6_performance_verification(tracking):
    """Test 6: Performance Verification"""
    print_header("Performance Verification")
    
    if not tracking:
        print_result(False, "Skipping - previous test failed")
        return
    
    try:
        # Test performance with timing
        start_time = time.time()
        
        # Get all relationships (should be fast)
        all_rels = tracking.get_all_relationships()
        relationships_time = time.time() - start_time
        
        # Test impact analysis timing
        if all_rels:
            start_time = time.time()
            # Use first available document for impact analysis
            first_doc = list(tracking.graph.nodes)[0] if tracking.graph.nodes else None
            if first_doc:
                impact = tracking.analyze_impact(first_doc)
                impact_time = time.time() - start_time
                
                print(f"✅ Performance metrics:")
                print(f"   - Get all relationships: {relationships_time*1000:.2f}ms")
                print(f"   - Impact analysis: {impact_time*1000:.2f}ms")
                print(f"   - Documents in graph: {len(tracking.graph.nodes)}")
                print(f"   - Relationships in graph: {len(tracking.graph.edges)}")
                
                # Verify performance targets (<10 seconds for this small dataset)
                if impact_time < 10.0:
                    print_result(True, f"Performance targets met (analysis: {impact_time:.3f}s)")
                else:
                    print_result(False, f"Performance target missed (analysis: {impact_time:.3f}s)")
            else:
                print_result(True, "No documents available for performance testing")
        else:
            print_result(True, "No relationships available for performance testing")
            
    except Exception as e:
        print_result(False, f"Performance verification failed: {str(e)}")


def test_7_export_import_functionality(tracking):
    """Test 7: Export/Import Functionality"""
    print_header("Export/Import Functionality")
    
    if not tracking:
        print_result(False, "Skipping - previous test failed")
        return
    
    try:
        # Export to JSON
        export_data_str = tracking.export_to_json()
        export_data = json.loads(export_data_str)
        print(f"✅ Exported data keys: {list(export_data.keys())}")
        print(f"✅ Exported nodes: {len(export_data.get('nodes', []))}")
        print(f"✅ Exported edges: {len(export_data.get('edges', []))}")
        
        # Save to file
        export_file = "test_tracking_export.json"
        with open(export_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        print(f"✅ Exported to file: {export_file}")
        
        # Verify file contents
        with open(export_file, 'r') as f:
            imported_data = json.load(f)
        print(f"✅ File verification: {len(imported_data)} top-level keys")
        
        # Clean up
        os.remove(export_file)
        print(f"✅ Cleaned up test file: {export_file}")
        
        print_result(True, "Export/import functionality completed successfully")
        
    except Exception as e:
        print_result(False, f"Export/import functionality failed: {str(e)}")


def main():
    """Run all verification tests."""
    print("🚀 M005 Tracking Matrix - Real-World Verification")
    print("=" * 60)
    print("This script will run comprehensive tests to verify M005 functionality.")
    print("Each test will show clear pass/fail results with detailed output.")
    print()
    
    # Run tests in sequence
    tracking, storage = test_1_basic_initialization()
    docs = test_2_document_creation_and_relationships(tracking, storage)
    test_3_relationship_queries(tracking, docs)
    test_4_impact_analysis(tracking, docs)
    test_5_circular_reference_detection(tracking, docs)
    test_6_performance_verification(tracking)
    test_7_export_import_functionality(tracking)
    
    print("\n" + "="*60)
    print("🎉 M005 Verification Tests Complete!")
    print("="*60)
    print("Review the results above to confirm all functionality is working.")
    print("Any failures should be investigated and resolved.")


if __name__ == "__main__":
    main()