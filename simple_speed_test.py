#!/usr/bin/env python3
"""
Simple speed test to isolate the performance issue
"""

import sys
sys.path.insert(0, '/workspaces/DocDevAI-v3.0.0')

from devdocai.miair.entropy import ShannonEntropyCalculator
from devdocai.miair.entropy_optimized import OptimizedShannonEntropyCalculator
import time

def test_simple():
    test_text = "Hello world this is a simple test document with some words."
    
    print("🔍 Simple Speed Test")
    print(f"Test text length: {len(test_text)} chars")
    
    # Basic calculator
    basic = ShannonEntropyCalculator()
    start = time.perf_counter()
    for _ in range(1000):
        result = basic.calculate_entropy(test_text)
    basic_time = time.perf_counter() - start
    basic_rate = 1000 / basic_time
    
    # Optimized calculator  
    opt = OptimizedShannonEntropyCalculator()
    start = time.perf_counter()
    for _ in range(1000):
        result_opt = opt.calculate_entropy(test_text)
    opt_time = time.perf_counter() - start
    opt_rate = 1000 / opt_time
    
    print(f"Basic: {basic_rate:.0f} ops/sec")
    print(f"Optimized: {opt_rate:.0f} ops/sec")
    print(f"Speedup: {opt_rate/basic_rate:.1f}x")
    
    print(f"Basic result: {result}")
    print(f"Optimized result: {result_opt}")

if __name__ == "__main__":
    test_simple()