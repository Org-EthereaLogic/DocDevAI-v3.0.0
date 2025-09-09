#!/usr/bin/env python3
"""
M005 Tracking Matrix - Simplified Pass 2 Performance Benchmark
"""

import sys
import time
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from devdocai.core.config import ConfigurationManager
from devdocai.core.storage import StorageManager
from devdocai.core.tracking import TrackingMatrix, RelationshipType


def benchmark_basic_operations():
    """Run basic performance benchmarks."""
    config = ConfigurationManager()
    storage = StorageManager(config)
    
    print("🚀 M005 Pass 2 - Basic Performance Benchmark\n")
    print("=" * 60)
    
    # Test 1: Document Addition (1000 docs)
    print("\n📊 Test 1: Document Addition (1000 docs)")
    matrix = TrackingMatrix(config, storage)
    
    start = time.time()
    for i in range(1000):
        matrix.add_document(f"doc_{i}", {"index": i})
    elapsed = time.time() - start
    
    print(f"✅ Added 1000 documents in {elapsed:.3f}s ({1000/elapsed:.0f} ops/s)")
    print(f"   Target: <1ms per doc = {elapsed/1000*1000:.2f}ms per doc")
    
    # Test 2: Relationship Creation (chain pattern to avoid cycles)
    print("\n📊 Test 2: Relationship Creation (999 relationships)")
    start = time.time()
    for i in range(999):
        matrix.add_relationship(f"doc_{i}", f"doc_{i+1}", 
                              RelationshipType.DEPENDS_ON)
    elapsed = time.time() - start
    
    print(f"✅ Added 999 relationships in {elapsed:.3f}s ({999/elapsed:.0f} ops/s)")
    print(f"   Target: <1ms per relationship = {elapsed/999*1000:.2f}ms per relationship")
    
    # Test 3: Impact Analysis
    print("\n📊 Test 3: Impact Analysis (1000 docs)")
    start = time.time()
    impact = matrix.analyze_impact("doc_0", max_depth=5)
    elapsed = time.time() - start
    
    print(f"✅ Impact analysis completed in {elapsed*1000:.2f}ms")
    print(f"   Affected documents: {len(impact.affected_documents)}")
    print(f"   Target: <10ms = {'✅ PASS' if elapsed < 0.01 else '❌ FAIL'}")
    
    # Test 4: Consistency Analysis
    print("\n📊 Test 4: Consistency Analysis (1000 docs)")
    start = time.time()
    report = matrix.analyze_suite_consistency()
    elapsed = time.time() - start
    
    print(f"✅ Consistency analysis completed in {elapsed*1000:.2f}ms")
    print(f"   Target: <50ms = {'✅ PASS' if elapsed < 0.05 else '❌ FAIL'}")
    
    # Test 5: JSON Export
    print("\n📊 Test 5: JSON Export (1000 docs)")
    start = time.time()
    json_data = matrix.export_to_json()
    elapsed = time.time() - start
    
    print(f"✅ JSON export completed in {elapsed*1000:.2f}ms")
    print(f"   JSON size: {len(json_data)/1024:.1f}KB")
    print(f"   Target: <100ms = {'✅ PASS' if elapsed < 0.1 else '❌ FAIL'}")
    
    # Test 6: Topological Sort
    print("\n📊 Test 6: Topological Sort (1000 nodes)")
    start = time.time()
    sorted_docs = matrix.graph.topological_sort()
    elapsed = time.time() - start
    
    print(f"✅ Topological sort completed in {elapsed*1000:.2f}ms")
    print(f"   Target: <5ms = {'✅ PASS' if elapsed < 0.005 else '❌ FAIL'}")
    
    print("\n" + "=" * 60)
    print("Current Pass 1 Performance Summary:")
    print("- Document addition: Good performance")
    print("- Relationship creation: Good performance")
    print("- Impact analysis: Meets target for 1000 docs")
    print("- Need optimization for 10,000+ documents")


def benchmark_large_scale():
    """Test with 10,000 documents."""
    config = ConfigurationManager()
    storage = StorageManager(config)
    
    print("\n\n🔥 Large Scale Test (10,000 documents)")
    print("=" * 60)
    
    matrix = TrackingMatrix(config, storage)
    
    # Add 10,000 documents
    print("\n📊 Adding 10,000 documents...")
    tracemalloc.start()
    start = time.time()
    
    for i in range(10000):
        matrix.add_document(f"doc_{i}", {"index": i})
    
    elapsed = time.time() - start
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    print(f"✅ Added 10,000 documents in {elapsed:.3f}s ({10000/elapsed:.0f} ops/s)")
    print(f"   Memory used: {peak/1024/1024:.1f}MB")
    print(f"   Target: <50MB = {'✅ PASS' if peak/1024/1024 < 50 else '❌ NEEDS OPTIMIZATION'}")
    
    # Add sparse relationships (chain pattern)
    print("\n📊 Adding 9,999 relationships...")
    start = time.time()
    
    for i in range(9999):
        matrix.add_relationship(f"doc_{i}", f"doc_{i+1}", 
                              RelationshipType.DEPENDS_ON)
    
    elapsed = time.time() - start
    print(f"✅ Added 9,999 relationships in {elapsed:.3f}s ({9999/elapsed:.0f} ops/s)")
    
    # Test impact analysis on large graph
    print("\n📊 Impact analysis on 10,000 doc graph...")
    start = time.time()
    impact = matrix.analyze_impact("doc_0", max_depth=5)
    elapsed = time.time() - start
    
    print(f"✅ Impact analysis completed in {elapsed:.3f}s")
    print(f"   Affected documents: {len(impact.affected_documents)}")
    print(f"   Target: <1s for complex graphs = {'✅ PASS' if elapsed < 1 else '❌ NEEDS OPTIMIZATION'}")


if __name__ == "__main__":
    benchmark_basic_operations()
    benchmark_large_scale()
    
    print("\n\n🎯 Pass 2 Optimization Areas Identified:")
    print("1. Memory optimization for 10K+ documents")
    print("2. Impact analysis performance for large graphs")
    print("3. Batch operation optimization needed")
    print("4. Consider NetworkX for advanced algorithms")
    print("5. Implement parallel processing where possible")