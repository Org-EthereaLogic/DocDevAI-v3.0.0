#!/usr/bin/env python3
"""
Quick test to verify M003 performance fix
"""

import time
import sys
import os

# Add project root to path
sys.path.insert(0, '/workspaces/DocDevAI-v3.0.0')

from devdocai.miair.engine_unified import create_engine, EngineMode

def test_m003_performance():
    """Test M003 performance after fix."""
    print("🚀 Testing M003 MIAIR Engine Performance Fix...")
    
    # Test document
    test_doc = """
    # Software Architecture Document
    
    ## Overview
    This document provides comprehensive architectural guidelines for modern software development.
    
    ## Core Components
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
    
    ### Presentation Layer
    - User interface components
    - API endpoints
    - Response formatting
    
    ## Performance Considerations
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
    
    # Test STANDARD mode (baseline)
    print("\n📊 Testing STANDARD mode (baseline)...")
    engine_standard = create_engine(EngineMode.STANDARD)
    
    start_time = time.perf_counter()
    docs_processed = 0
    
    # Process for 3 seconds
    while time.perf_counter() - start_time < 3.0:
        result = engine_standard.analyze(test_doc, f"doc_{docs_processed}")
        docs_processed += 1
    
    standard_time = time.perf_counter() - start_time
    standard_rate = docs_processed / standard_time
    standard_per_min = standard_rate * 60
    
    print(f"  ✓ Processed {docs_processed} docs in {standard_time:.2f}s")
    print(f"  ✓ Rate: {standard_rate:.1f} docs/sec ({standard_per_min:.0f} docs/min)")
    
    # Test OPTIMIZED mode (should be much faster)
    print("\n🚀 Testing OPTIMIZED mode (with fix)...")
    engine_optimized = create_engine(EngineMode.OPTIMIZED)
    
    start_time = time.perf_counter()
    docs_processed = 0
    
    # Process for 3 seconds
    while time.perf_counter() - start_time < 3.0:
        result = engine_optimized.analyze(test_doc, f"doc_{docs_processed}")
        docs_processed += 1
    
    optimized_time = time.perf_counter() - start_time
    optimized_rate = docs_processed / optimized_time
    optimized_per_min = optimized_rate * 60
    
    print(f"  ✓ Processed {docs_processed} docs in {optimized_time:.2f}s")
    print(f"  ✓ Rate: {optimized_rate:.1f} docs/sec ({optimized_per_min:.0f} docs/min)")
    
    # Calculate improvement
    if standard_rate > 0:
        improvement = ((optimized_rate - standard_rate) / standard_rate) * 100
        print(f"\n📈 Performance Analysis:")
        print(f"  • STANDARD:  {standard_per_min:,.0f} docs/min")
        print(f"  • OPTIMIZED: {optimized_per_min:,.0f} docs/min")
        print(f"  • Improvement: {improvement:+.1f}%")
        
        # Check against targets
        target_rate = 50000  # 50K docs/min target
        baseline_target = 361431  # Previous baseline performance
        
        if optimized_per_min >= target_rate:
            print(f"  ✅ PASS: Exceeds target ({target_rate:,} docs/min)")
        else:
            print(f"  ⚠️  BELOW TARGET: {optimized_per_min:,.0f} < {target_rate:,} docs/min")
            
        if optimized_per_min >= baseline_target * 0.8:  # 80% of baseline
            print(f"  ✅ PERFORMANCE RESTORED: Near baseline ({baseline_target:,} docs/min)")
        else:
            print(f"  ❌ PERFORMANCE ISSUE: Still below baseline")
    
    # Test batch processing
    print("\n🔀 Testing batch processing...")
    batch_docs = [{"content": test_doc, "id": f"batch_doc_{i}"} for i in range(10)]
    
    start_time = time.perf_counter()
    batch_results = engine_optimized.batch_analyze(batch_docs)
    batch_time = time.perf_counter() - start_time
    
    batch_rate = len(batch_results) / batch_time
    print(f"  ✓ Batch processed {len(batch_results)} docs in {batch_time:.3f}s")
    print(f"  ✓ Batch rate: {batch_rate:.1f} docs/sec ({batch_rate * 60:.0f} docs/min)")

if __name__ == "__main__":
    test_m003_performance()