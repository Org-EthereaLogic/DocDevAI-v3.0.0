#!/usr/bin/env python3
"""
Debug hybrid method usage
"""

import sys
sys.path.insert(0, '/workspaces/DocDevAI-v3.0.0')

from devdocai.miair.entropy_optimized import OptimizedShannonEntropyCalculator
import time

def test_hybrid():
    test_text = "Hello world this is a simple test document with some words."
    print(f"Test text length: {len(test_text)} chars (should use basic method)")
    
    calc = OptimizedShannonEntropyCalculator()
    
    # Test direct hybrid method calls
    print("\n🔍 Testing Hybrid Methods Directly:")
    
    # Character entropy - basic
    start = time.perf_counter()
    for _ in range(1000):
        result = calc._calculate_character_entropy_hybrid(test_text, use_basic=True)
    basic_time = time.perf_counter() - start
    basic_rate = 1000 / basic_time
    
    # Character entropy - vectorized  
    start = time.perf_counter()
    for _ in range(1000):
        result_vec = calc._calculate_character_entropy_hybrid(test_text, use_basic=False)
    vec_time = time.perf_counter() - start
    vec_rate = 1000 / vec_time
    
    print(f"Character entropy (basic): {basic_rate:.0f} ops/sec")
    print(f"Character entropy (vectorized): {vec_rate:.0f} ops/sec")
    print(f"Speedup basic vs vectorized: {basic_rate/vec_rate:.1f}x")
    print(f"Results match: {abs(result - result_vec) < 1e-10}")
    
    # Test full calculate_entropy method
    print("\n📊 Testing Full calculate_entropy Method:")
    start = time.perf_counter()
    for _ in range(1000):
        full_result = calc.calculate_entropy(test_text)
    full_time = time.perf_counter() - start
    full_rate = 1000 / full_time
    
    print(f"Full calculate_entropy: {full_rate:.0f} ops/sec")
    print(f"Should be using basic method: {len(test_text) < 5000}")
    print(f"Full result: {full_result}")

if __name__ == "__main__":
    test_hybrid()