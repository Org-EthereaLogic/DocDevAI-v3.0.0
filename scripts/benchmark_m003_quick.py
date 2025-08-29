#!/usr/bin/env python3
"""
Quick performance benchmark for M003 Unified MIAIR Engine.

Tests basic performance to validate no major regressions after refactoring.
"""

import time
import statistics
import random
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from devdocai.miair.engine_unified import (
    UnifiedMIAIREngine, 
    UnifiedMIAIRConfig, 
    EngineMode,
    create_standard_engine,
    create_optimized_engine,
    create_secure_engine
)


def generate_test_document(size: str = "medium") -> str:
    """Generate test document of specified size."""
    if size == "small":
        word_count = 100
    elif size == "medium":
        word_count = 500
    elif size == "large":
        word_count = 1000
    else:
        word_count = 500
    
    sections = [
        "# Document Title\n\n",
        "## Introduction\n\n",
        "This document provides information about the system. ",
        "It covers various aspects and features. ",
        "\n\n## Main Content\n\n"
    ]
    
    words = ['system', 'process', 'data', 'user', 'interface', 'module', 
             'function', 'parameter', 'configuration', 'implementation']
    
    for _ in range(word_count // 10):
        sentence = ' '.join(random.choices(words, k=10)) + '. '
        sections.append(sentence)
    
    sections.append("\n\n## Conclusion\n\nThis concludes the documentation.")
    
    return ''.join(sections)


def quick_benchmark_mode(mode: EngineMode, num_docs: int = 20) -> dict:
    """Quick benchmark of a specific mode."""
    print(f"\nTesting {mode.value.upper()} mode...")
    
    # Create engine
    if mode == EngineMode.STANDARD:
        engine = create_standard_engine()
    elif mode == EngineMode.OPTIMIZED:
        engine = create_optimized_engine()
    else:
        engine = create_secure_engine()
    
    # Generate test documents
    documents = []
    for i in range(num_docs):
        documents.append({
            'content': generate_test_document("medium"),
            'document_id': f"test_{i}",
            'metadata': {'title': f"Test {i}"}
        })
    
    # Benchmark analysis
    analysis_times = []
    for doc in documents:
        start = time.perf_counter()
        result = engine.analyze(
            content=doc['content'],
            document_id=doc['document_id'],
            metadata=doc['metadata']
        )
        elapsed = time.perf_counter() - start
        analysis_times.append(elapsed * 1000)  # ms
    
    avg_time = statistics.mean(analysis_times)
    throughput = 1000 / avg_time  # docs/sec
    throughput_per_min = throughput * 60
    
    print(f"  Documents: {num_docs}")
    print(f"  Avg time: {avg_time:.1f}ms")
    print(f"  Throughput: {throughput:.1f} docs/sec")
    print(f"  Per minute: {throughput_per_min:.0f} docs/min")
    
    # Test optimization (just 2 docs)
    opt_times = []
    for doc in documents[:2]:
        start = time.perf_counter()
        opt_result = engine.optimize(
            content=doc['content'],
            document_id=doc['document_id']
        )
        elapsed = time.perf_counter() - start
        opt_times.append(elapsed)
    
    avg_opt_time = statistics.mean(opt_times)
    opt_throughput_per_min = (1 / avg_opt_time) * 60
    
    print(f"  Optimization: {avg_opt_time:.2f}s avg, {opt_throughput_per_min:.0f} docs/min")
    
    engine.cleanup()
    
    return {
        'mode': mode.value,
        'analysis_throughput_per_min': throughput_per_min,
        'optimization_throughput_per_min': opt_throughput_per_min,
        'avg_analysis_time_ms': avg_time
    }


def main():
    """Run quick benchmark."""
    print("="*60)
    print("M003 UNIFIED MIAIR ENGINE - QUICK BENCHMARK")
    print("="*60)
    print("Testing post-refactoring performance...")
    
    # Test all modes
    modes = [EngineMode.STANDARD, EngineMode.OPTIMIZED, EngineMode.SECURE]
    results = {}
    
    for mode in modes:
        results[mode.value] = quick_benchmark_mode(mode, num_docs=20)
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    print(f"\n{'Mode':<12} {'Analysis (docs/min)':<18} {'Optimization (docs/min)':<22}")
    print("-" * 52)
    for mode_name, data in results.items():
        analysis = data['analysis_throughput_per_min']
        optimization = data['optimization_throughput_per_min']
        print(f"{mode_name.upper():<12} {analysis:<18.0f} {optimization:<22.0f}")
    
    # Compare against baseline
    baseline = 361431  # Previous baseline
    best_analysis = max(r['analysis_throughput_per_min'] for r in results.values())
    
    print(f"\nBaseline Comparison:")
    print(f"  Previous baseline: {baseline:,} docs/min")
    print(f"  Current best: {best_analysis:,.0f} docs/min")
    
    ratio = best_analysis / baseline
    if ratio >= 1.0:
        print(f"  ✅ IMPROVEMENT: {((ratio - 1) * 100):+.1f}%")
    elif ratio >= 0.8:
        print(f"  ✅ ACCEPTABLE: {((ratio - 1) * 100):+.1f}% (within 20%)")
    else:
        print(f"  ⚠️ REGRESSION: {((1 - ratio) * 100):.1f}% decrease")
    
    print(f"\n✅ Quick benchmark completed!")


if __name__ == "__main__":
    main()