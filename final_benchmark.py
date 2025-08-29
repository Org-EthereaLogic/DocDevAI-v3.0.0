#!/usr/bin/env python3
"""
Final benchmark to measure M003 performance fix
"""

import sys
import time
sys.path.insert(0, '/workspaces/DocDevAI-v3.0.0')

from devdocai.miair.engine_unified import create_engine, EngineMode

def final_benchmark():
    """Final benchmark to confirm M003 performance restoration."""
    
    test_doc = """
    # Software Architecture Document
    
    ## Overview
    This document provides comprehensive architectural guidelines for modern software development.
    The system consists of several interconnected modules that work together to provide
    a scalable and maintainable solution for document processing and analysis.
    
    ### Data Processing Layer
    - Input validation and sanitization
    - Data transformation and normalization
    - Error handling and recovery mechanisms
    
    ### Business Logic Layer
    - Core business rules implementation
    - Workflow orchestration
    - Decision making algorithms
    
    ### Performance Considerations
    The architecture is designed to handle high throughput scenarios with:
    - Asynchronous processing capabilities
    - Caching mechanisms for frequently accessed data
    - Load balancing across multiple instances
    - Database query optimization
    
    ## Security Features
    - Authentication and authorization
    - Data encryption at rest and in transit
    - Input validation and output sanitization
    - Audit logging and monitoring
    """
    
    print("🚀 DevDocAI M003 MIAIR Engine - Final Performance Benchmark")
    print("="*80)
    
    # Test OPTIMIZED mode performance
    print("\n📊 Testing OPTIMIZED Mode Performance...")
    engine = create_engine(EngineMode.OPTIMIZED)
    
    # Quick 10-second benchmark
    start_time = time.perf_counter()
    docs_processed = 0
    
    print("  ⏱️  Processing documents for 10 seconds...")
    while time.perf_counter() - start_time < 10.0:
        result = engine.analyze(test_doc, f"doc_{docs_processed}")
        docs_processed += 1
        
        # Print progress every 100 docs
        if docs_processed % 100 == 0:
            elapsed = time.perf_counter() - start_time
            current_rate = docs_processed / elapsed
            print(f"      • {docs_processed} docs processed ({current_rate:.0f} docs/sec)")
    
    total_time = time.perf_counter() - start_time
    final_rate_per_sec = docs_processed / total_time
    final_rate_per_min = final_rate_per_sec * 60
    
    print("\n📈 FINAL RESULTS:")
    print(f"  ✅ Total Documents Processed: {docs_processed:,}")
    print(f"  ✅ Total Time: {total_time:.2f} seconds")
    print(f"  ✅ Processing Rate: {final_rate_per_sec:,.0f} docs/sec")
    print(f"  ✅ Processing Rate: {final_rate_per_min:,.0f} docs/min")
    
    # Compare against targets
    baseline_target = 361431  # Original baseline
    min_target = 50000       # Minimum target
    
    print("\n🎯 TARGET COMPARISON:")
    if final_rate_per_min >= baseline_target:
        performance_vs_baseline = ((final_rate_per_min / baseline_target) - 1) * 100
        print(f"  🏆 EXCEEDS BASELINE: {performance_vs_baseline:+.1f}% vs {baseline_target:,} docs/min")
    elif final_rate_per_min >= baseline_target * 0.8:
        performance_vs_baseline = ((final_rate_per_min / baseline_target) - 1) * 100
        print(f"  ✅ NEAR BASELINE: {performance_vs_baseline:+.1f}% vs {baseline_target:,} docs/min")
    else:
        print(f"  ⚠️  BELOW BASELINE: {final_rate_per_min:,} vs {baseline_target:,} docs/min")
    
    if final_rate_per_min >= min_target:
        performance_vs_min = ((final_rate_per_min / min_target) - 1) * 100
        print(f"  ✅ EXCEEDS MIN TARGET: {performance_vs_min:+.1f}% vs {min_target:,} docs/min")
    else:
        print(f"  ❌ BELOW MIN TARGET: {final_rate_per_min:,} vs {min_target:,} docs/min")
    
    # Test batch processing
    print("\n🔀 Testing Batch Processing...")
    batch_docs = [{"content": test_doc, "id": f"batch_doc_{i}"} for i in range(50)]
    
    start_time = time.perf_counter()
    batch_results = engine.batch_analyze(batch_docs)
    batch_time = time.perf_counter() - start_time
    
    batch_rate_per_sec = len(batch_results) / batch_time
    batch_rate_per_min = batch_rate_per_sec * 60
    
    print(f"  ✅ Batch Size: {len(batch_docs)} documents")
    print(f"  ✅ Batch Time: {batch_time:.3f} seconds")
    print(f"  ✅ Batch Rate: {batch_rate_per_sec:.0f} docs/sec ({batch_rate_per_min:,.0f} docs/min)")
    
    print("\n" + "="*80)
    print("🎉 M003 MIAIR Engine Performance Fix Complete!")
    
    if final_rate_per_min >= min_target:
        print("✅ PRODUCTION READY: Performance restored and exceeds requirements")
    else:
        print("❌ PERFORMANCE ISSUE: Still below minimum requirements")
    
    return final_rate_per_min >= min_target

if __name__ == "__main__":
    success = final_benchmark()
    sys.exit(0 if success else 1)