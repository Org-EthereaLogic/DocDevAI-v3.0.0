#!/usr/bin/env python3
"""
Quick test script for the unified MIAIR engine.
Tests all three modes to ensure basic functionality.
"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from devdocai.miair import (
    create_standard_engine,
    create_optimized_engine,
    create_secure_engine,
    EngineMode
)

def test_engine_mode(mode_name: str, engine):
    """Test a specific engine mode."""
    print(f"\n{'='*60}")
    print(f"Testing {mode_name} Mode")
    print('='*60)
    
    # Test document
    test_doc = {
        'content': """
        This is a test document for the unified MIAIR engine.
        It contains multiple sentences to test entropy calculation.
        The quality scoring should work across all modes.
        Pattern recognition will identify common structures.
        This refactoring improves code maintainability significantly.
        """,
        'metadata': {
            'title': 'Test Document',
            'author': 'Test Suite',
            'version': '1.0'
        }
    }
    
    try:
        # Test analysis
        print(f"\n1. Testing analysis...")
        start = time.perf_counter()
        result = engine.analyze(
            content=test_doc['content'],
            document_id='test-001',
            metadata=test_doc['metadata']
        )
        duration = time.perf_counter() - start
        
        print(f"   ✓ Analysis completed in {duration:.4f}s")
        print(f"   - Quality Score: {result.quality_score:.2f}")
        print(f"   - Entropy: {result.entropy:.2f}")
        print(f"   - Patterns Found: {len(result.patterns)}")
        print(f"   - Mode: {result.mode}")
        
        # Test optimization
        print(f"\n2. Testing optimization...")
        start = time.perf_counter()
        opt_result = engine.optimize(
            content=test_doc['content'],
            document_id='test-001',
            target_quality=0.9
        )
        duration = time.perf_counter() - start
        
        print(f"   ✓ Optimization completed in {duration:.4f}s")
        print(f"   - Original Score: {opt_result.original_score:.2f}")
        print(f"   - Optimized Score: {opt_result.optimized_score:.2f}")
        print(f"   - Iterations: {opt_result.iterations}")
        
        # Test batch processing
        print(f"\n3. Testing batch analysis...")
        batch_docs = [
            {'content': f"Test document {i}", 'id': f'batch-{i}'}
            for i in range(5)
        ]
        
        start = time.perf_counter()
        batch_results = engine.batch_analyze(batch_docs)
        duration = time.perf_counter() - start
        
        print(f"   ✓ Batch analysis completed in {duration:.4f}s")
        print(f"   - Documents Processed: {len(batch_results)}")
        print(f"   - Average Time per Doc: {duration/len(batch_results):.4f}s")
        
        # Get statistics
        print(f"\n4. Engine Statistics:")
        stats = engine.get_stats()
        print(f"   - Mode: {stats['mode']}")
        print(f"   - Caching Enabled: {stats['configuration']['caching_enabled']}")
        
        if 'cache' in stats:
            print(f"   - Cache Hit Rate: {stats['cache'].get('hit_rate', 0):.1%}")
        
        if 'security' in stats:
            print(f"   - Security Features: {sum(stats['security'].values())} enabled")
        
        print(f"\n✅ {mode_name} mode tests PASSED")
        
        # Cleanup
        engine.cleanup()
        
        return True
        
    except Exception as e:
        print(f"\n❌ {mode_name} mode tests FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run tests for all engine modes."""
    print("\n" + "="*60)
    print(" UNIFIED MIAIR ENGINE TEST SUITE")
    print("="*60)
    
    results = {}
    
    # Test Standard Mode
    try:
        engine = create_standard_engine()
        results['standard'] = test_engine_mode('Standard', engine)
    except Exception as e:
        print(f"Failed to create standard engine: {e}")
        results['standard'] = False
    
    # Test Optimized Mode
    try:
        engine = create_optimized_engine()
        results['optimized'] = test_engine_mode('Optimized', engine)
    except Exception as e:
        print(f"Failed to create optimized engine: {e}")
        results['optimized'] = False
    
    # Test Secure Mode
    try:
        # Set up minimal security for testing
        engine = create_secure_engine(
            enable_validation=True,
            enable_rate_limiting=False,  # Disable for testing
            enable_audit_logging=False,  # Disable for testing
            enable_encryption=False  # Disable for testing (needs key setup)
        )
        results['secure'] = test_engine_mode('Secure', engine)
    except Exception as e:
        print(f"Failed to create secure engine: {e}")
        results['secure'] = False
    
    # Summary
    print("\n" + "="*60)
    print(" TEST SUMMARY")
    print("="*60)
    
    for mode, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {mode.capitalize():10} : {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 All tests PASSED! The unified engine is working correctly.")
    else:
        print("\n⚠️ Some tests FAILED. Please check the errors above.")
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())