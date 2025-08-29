#!/usr/bin/env python3
"""
Debug M003 performance issue
"""

import sys
sys.path.insert(0, '/workspaces/DocDevAI-v3.0.0')

from devdocai.miair.engine_unified import create_engine, EngineMode
from devdocai.miair.entropy import ShannonEntropyCalculator
from devdocai.miair.entropy_optimized import OptimizedShannonEntropyCalculator
import time

def debug_component_performance():
    """Debug individual components."""
    test_text = """
    This is a comprehensive test document that contains multiple sections
    and various types of content to properly evaluate the entropy calculation
    performance. It includes technical terminology, structured content,
    and sufficient length to measure meaningful performance differences.
    The document structure includes headers, paragraphs, and various
    linguistic patterns that should trigger different entropy calculations
    across character, word, and sentence levels.
    """
    
    print("🔍 Debugging M003 Component Performance...\n")
    
    # Test basic vs optimized entropy calculators
    print("📊 Testing Entropy Calculators:")
    
    # Basic entropy calculator
    basic_calc = ShannonEntropyCalculator()
    start = time.perf_counter()
    for _ in range(100):
        result = basic_calc.calculate_entropy(test_text)
    basic_time = time.perf_counter() - start
    basic_rate = 100 / basic_time
    
    print(f"  • Basic Entropy: {basic_rate:.1f} ops/sec")
    print(f"    Result sample: {result}")
    
    # Optimized entropy calculator
    opt_calc = OptimizedShannonEntropyCalculator()
    start = time.perf_counter()
    for _ in range(100):
        result_opt = opt_calc.calculate_entropy(test_text)
    opt_time = time.perf_counter() - start
    opt_rate = 100 / opt_time
    
    print(f"  • Optimized Entropy: {opt_rate:.1f} ops/sec")
    print(f"    Result sample: {result_opt}")
    print(f"    Speedup: {opt_rate/basic_rate:.1f}x\n")
    
    # Test engines
    print("🚀 Testing Engine Configurations:")
    
    # Standard engine
    engine_std = create_engine(EngineMode.STANDARD)
    print(f"  • Standard engine components:")
    print(f"    - Entropy: {type(engine_std.entropy_calculator).__name__}")
    print(f"    - Quality: {type(engine_std.quality_scorer).__name__}")
    print(f"    - Pattern: {type(engine_std.pattern_recognizer).__name__}")
    print(f"    - Executor: {engine_std.executor}")
    
    # Optimized engine  
    engine_opt = create_engine(EngineMode.OPTIMIZED)
    print(f"  • Optimized engine components:")
    print(f"    - Entropy: {type(engine_opt.entropy_calculator).__name__}")
    print(f"    - Quality: {type(engine_opt.quality_scorer).__name__}")
    print(f"    - Pattern: {type(engine_opt.pattern_recognizer).__name__}")
    print(f"    - Executor: {engine_opt.executor}")
    print(f"    - Max workers: {engine_opt.config.max_workers}")
    print(f"    - Use processes: {engine_opt.config.use_processes}")
    
    # Test single analysis performance
    print("\n⏱️  Single Analysis Performance:")
    
    start = time.perf_counter()
    result_std = engine_std.analyze(test_text)
    std_time = time.perf_counter() - start
    
    start = time.perf_counter()
    result_opt = engine_opt.analyze(test_text)
    opt_time = time.perf_counter() - start
    
    print(f"  • Standard: {std_time*1000:.1f}ms per doc")
    print(f"  • Optimized: {opt_time*1000:.1f}ms per doc")
    
    if opt_time > 0:
        speedup = std_time / opt_time
        print(f"  • Speedup: {speedup:.1f}x")
    
    print(f"\n📋 Analysis Results:")
    print(f"  • Standard quality: {result_std.quality_score:.3f}")
    print(f"  • Optimized quality: {result_opt.quality_score:.3f}")

if __name__ == "__main__":
    debug_component_performance()