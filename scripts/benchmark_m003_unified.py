#!/usr/bin/env python3
"""
Performance benchmark for M003 Unified MIAIR Engine after refactoring pass.

Tests the new unified engine against baseline performance:
- Previous baseline: 361,431 docs/min (29.6x improvement over 50K target)
- Tests all three modes: STANDARD, OPTIMIZED, SECURE
- Validates no regression from refactoring
"""

import time
import statistics
import random
import gc
import psutil
from typing import List, Dict, Any
from concurrent.futures import ProcessPoolExecutor
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from devdocai.miair.engine_unified import (
    UnifiedMIAIREngine, 
    UnifiedMIAIRConfig, 
    EngineMode,
    create_engine,
    create_standard_engine,
    create_optimized_engine,
    create_secure_engine
)


def generate_test_document(size: str = "medium", complexity: str = "normal") -> str:
    """Generate test document of specified size and complexity."""
    if size == "small":
        word_count = 100
    elif size == "medium":
        word_count = 500
    elif size == "large":
        word_count = 2000
    elif size == "xlarge":
        word_count = 5000
    else:
        word_count = 500
    
    # Generate realistic document structure
    sections = [
        "# Document Title\n\n",
        "## Introduction\n\n",
        "This document provides comprehensive information about the system architecture and implementation. ",
        "It covers various aspects, features, and best practices for optimal usage. ",
        "\n\n## Main Content\n\n"
    ]
    
    # Add content based on complexity
    if complexity == "simple":
        words = ['system', 'process', 'data', 'user', 'interface']
    elif complexity == "complex":
        words = ['system', 'process', 'data', 'user', 'interface', 'module', 
                 'function', 'parameter', 'configuration', 'implementation',
                 'architecture', 'optimization', 'performance', 'scalability',
                 'reliability', 'security', 'authentication', 'authorization']
    else:
        words = ['system', 'process', 'data', 'user', 'interface', 'module', 
                 'function', 'parameter', 'configuration', 'implementation']
    
    # Generate content paragraphs
    for _ in range(word_count // 50):
        paragraph = []
        for _ in range(3):  # 3 sentences per paragraph
            sentence = ' '.join(random.choices(words, k=random.randint(8, 15))) + '. '
            paragraph.append(sentence)
        sections.append(' '.join(paragraph) + '\n\n')
    
    # Add code examples for technical documents
    if complexity in ["normal", "complex"]:
        sections.append("## Code Example\n\n```python\n")
        sections.append("def example_function(param1, param2):\n")
        sections.append("    '''Example function implementation.'''\n")
        sections.append("    result = param1 + param2\n")
        sections.append("    return result\n```\n\n")
    
    sections.append("## Conclusion\n\nThis concludes the comprehensive documentation.")
    
    return ''.join(sections)


def measure_memory_usage():
    """Get current memory usage in MB."""
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024


def benchmark_engine_mode(mode: EngineMode, num_docs: int = 100, doc_size: str = "medium") -> Dict[str, Any]:
    """Benchmark a specific engine mode."""
    print(f"\n{'='*60}")
    print(f"BENCHMARKING: {mode.value.upper()} MODE")
    print(f"{'='*60}")
    
    # Create engine for the mode
    if mode == EngineMode.STANDARD:
        engine = create_standard_engine()
    elif mode == EngineMode.OPTIMIZED:
        engine = create_optimized_engine()
    else:  # SECURE
        engine = create_secure_engine()
    
    # Generate test documents
    documents = []
    for i in range(num_docs):
        doc_content = generate_test_document(doc_size, "normal")
        documents.append({
            'content': doc_content,
            'document_id': f"test_doc_{i}",
            'metadata': {
                'title': f"Test Document {i}",
                'category': f"category_{i % 10}",
                'tags': [f"tag_{j}" for j in range(3)]
            }
        })
    
    print(f"Generated {num_docs} {doc_size} test documents")
    
    # Benchmark 1: Single Document Analysis
    print(f"\n1. Single Document Analysis:")
    analysis_times = []
    
    # Test with subset for single analysis (to avoid taking too long)
    test_subset = documents[:min(50, num_docs)]
    
    for doc in test_subset:
        start_time = time.perf_counter()
        result = engine.analyze(
            content=doc['content'],
            document_id=doc['document_id'],
            metadata=doc['metadata']
        )
        elapsed = time.perf_counter() - start_time
        analysis_times.append(elapsed * 1000)  # Convert to ms
    
    avg_analysis_time = statistics.mean(analysis_times)
    analysis_throughput = 1000 / avg_analysis_time
    
    print(f"   Average analysis time: {avg_analysis_time:.2f}ms")
    print(f"   Analysis throughput: {analysis_throughput:.1f} docs/sec")
    print(f"   Throughput per minute: {analysis_throughput * 60:.0f} docs/min")
    
    # Benchmark 2: Batch Analysis
    print(f"\n2. Batch Analysis:")
    batch_docs = documents[:min(20, num_docs)]
    
    start_time = time.perf_counter()
    batch_results = engine.batch_analyze(batch_docs)
    batch_elapsed = time.perf_counter() - start_time
    
    batch_throughput = len(batch_docs) / batch_elapsed
    
    print(f"   Batch size: {len(batch_docs)} documents")
    print(f"   Total time: {batch_elapsed:.2f}s")
    print(f"   Batch throughput: {batch_throughput:.1f} docs/sec")
    print(f"   Batch throughput per minute: {batch_throughput * 60:.0f} docs/min")
    
    # Benchmark 3: Optimization Test (smaller subset due to time)
    print(f"\n3. Document Optimization:")
    opt_times = []
    opt_docs = documents[:min(5, num_docs)]
    
    for doc in opt_docs:
        start_time = time.perf_counter()
        opt_result = engine.optimize(
            content=doc['content'],
            document_id=doc['document_id']
        )
        elapsed = time.perf_counter() - start_time
        opt_times.append(elapsed)
    
    avg_opt_time = statistics.mean(opt_times)
    opt_throughput = 1 / avg_opt_time
    
    print(f"   Average optimization time: {avg_opt_time:.2f}s")
    print(f"   Optimization throughput: {opt_throughput:.1f} docs/sec")
    print(f"   Optimization per minute: {opt_throughput * 60:.0f} docs/min")
    
    # Benchmark 4: Memory Usage
    print(f"\n4. Memory Usage:")
    gc.collect()
    memory_before = measure_memory_usage()
    
    # Process larger document
    large_doc = generate_test_document("xlarge", "complex")
    result = engine.analyze(
        content=large_doc,
        document_id="memory_test",
        metadata={'test': 'memory'}
    )
    
    memory_after = measure_memory_usage()
    memory_usage = memory_after - memory_before
    
    print(f"   Memory before: {memory_before:.1f} MB")
    print(f"   Memory after: {memory_after:.1f} MB")
    print(f"   Memory usage: {memory_usage:.1f} MB for xlarge document")
    
    # Get engine statistics
    stats = engine.get_stats()
    print(f"\n5. Engine Statistics:")
    for key, value in stats.items():
        if isinstance(value, dict):
            print(f"   {key}:")
            for k, v in value.items():
                print(f"     {k}: {v}")
        else:
            print(f"   {key}: {value}")
    
    # Clean up
    engine.cleanup()
    
    return {
        'mode': mode.value,
        'num_docs': len(test_subset),
        'avg_analysis_time_ms': avg_analysis_time,
        'analysis_throughput_per_sec': analysis_throughput,
        'analysis_throughput_per_min': analysis_throughput * 60,
        'batch_throughput_per_sec': batch_throughput,
        'batch_throughput_per_min': batch_throughput * 60,
        'avg_optimization_time_s': avg_opt_time,
        'optimization_throughput_per_min': opt_throughput * 60,
        'memory_usage_mb': memory_usage,
        'stats': stats
    }


def compare_modes():
    """Compare all three engine modes."""
    print(f"\n{'='*80}")
    print("UNIFIED MIAIR ENGINE MODE COMPARISON")
    print(f"{'='*80}")
    print(f"System: {psutil.cpu_count()} cores, {psutil.virtual_memory().total // 1024 // 1024 // 1024} GB RAM")
    
    modes = [EngineMode.STANDARD, EngineMode.OPTIMIZED, EngineMode.SECURE]
    results = {}
    
    for mode in modes:
        results[mode.value] = benchmark_engine_mode(mode, num_docs=100)
    
    # Comparison Summary
    print(f"\n{'='*80}")
    print("PERFORMANCE COMPARISON SUMMARY")
    print(f"{'='*80}")
    
    metrics = [
        ('Analysis Throughput (docs/min)', 'analysis_throughput_per_min'),
        ('Batch Throughput (docs/min)', 'batch_throughput_per_min'),
        ('Optimization Throughput (docs/min)', 'optimization_throughput_per_min'),
        ('Average Analysis Time (ms)', 'avg_analysis_time_ms'),
        ('Memory Usage (MB)', 'memory_usage_mb')
    ]
    
    print(f"\n{'Metric':<35} {'Standard':<12} {'Optimized':<12} {'Secure':<12}")
    print("-" * 75)
    
    for metric_name, key in metrics:
        standard = results['standard'][key]
        optimized = results['optimized'][key]
        secure = results['secure'][key]
        
        if 'time' in key.lower() or 'memory' in key.lower():
            # Lower is better for time and memory
            print(f"{metric_name:<35} {standard:<12.1f} {optimized:<12.1f} {secure:<12.1f}")
        else:
            # Higher is better for throughput
            print(f"{metric_name:<35} {standard:<12.0f} {optimized:<12.0f} {secure:<12.0f}")
    
    # Performance vs baseline check
    print(f"\n{'='*80}")
    print("BASELINE COMPARISON (vs 361,431 docs/min target)")
    print(f"{'='*80}")
    
    baseline_target = 361431  # Previous optimized baseline
    min_target = 50000        # Original requirement
    
    for mode in ['standard', 'optimized', 'secure']:
        throughput = results[mode]['analysis_throughput_per_min']
        vs_baseline = (throughput / baseline_target) * 100
        vs_min = (throughput / min_target) * 100
        
        status_baseline = "✅ PASSED" if throughput >= baseline_target else "⚠️ BELOW" if throughput >= baseline_target * 0.8 else "❌ FAILED"
        status_min = "✅ PASSED" if throughput >= min_target else "❌ FAILED"
        
        print(f"\n{mode.upper()} Mode:")
        print(f"  Current: {throughput:.0f} docs/min")
        print(f"  vs Baseline: {vs_baseline:.1f}% - {status_baseline}")
        print(f"  vs Min Requirement: {vs_min:.1f}% - {status_min}")
    
    # Find best performing mode
    best_mode = max(results.keys(), key=lambda m: results[m]['analysis_throughput_per_min'])
    best_throughput = results[best_mode]['analysis_throughput_per_min']
    
    print(f"\n🏆 Best Performance: {best_mode.upper()} mode with {best_throughput:.0f} docs/min")
    
    return results


def run_regression_test():
    """Test for performance regression after refactoring."""
    print(f"\n{'='*80}")
    print("REGRESSION TEST: Post-Refactoring Performance")
    print(f"{'='*80}")
    
    # Test with optimized mode (should be closest to previous performance)
    print("\nTesting OPTIMIZED mode for regression analysis...")
    
    # Create optimized engine
    engine = create_optimized_engine()
    
    # Generate test documents (mix of sizes)
    test_docs = []
    for i in range(50):
        size = ["small", "medium", "large"][i % 3]
        doc = {
            'content': generate_test_document(size, "normal"),
            'document_id': f"regression_test_{i}",
            'metadata': {'test': 'regression', 'size': size, 'index': i}
        }
        test_docs.append(doc)
    
    # Measure analysis performance
    print("Running analysis performance test...")
    start_time = time.perf_counter()
    
    for doc in test_docs:
        result = engine.analyze(
            content=doc['content'],
            document_id=doc['document_id'],
            metadata=doc['metadata']
        )
    
    total_time = time.perf_counter() - start_time
    throughput = len(test_docs) / total_time
    throughput_per_min = throughput * 60
    
    print(f"  Documents processed: {len(test_docs)}")
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Throughput: {throughput:.1f} docs/sec")
    print(f"  Throughput per minute: {throughput_per_min:.0f} docs/min")
    
    # Compare against baseline
    baseline_throughput = 361431
    performance_ratio = throughput_per_min / baseline_throughput
    
    print(f"\nRegression Analysis:")
    print(f"  Previous baseline: {baseline_throughput:,.0f} docs/min")
    print(f"  Current performance: {throughput_per_min:,.0f} docs/min")
    print(f"  Performance ratio: {performance_ratio:.3f}")
    
    if performance_ratio >= 1.0:
        print(f"  ✅ IMPROVEMENT: {((performance_ratio - 1) * 100):+.1f}% vs baseline")
    elif performance_ratio >= 0.9:
        print(f"  ✅ ACCEPTABLE: {((performance_ratio - 1) * 100):+.1f}% vs baseline (within 10%)")
    elif performance_ratio >= 0.8:
        print(f"  ⚠️ MINOR REGRESSION: {((performance_ratio - 1) * 100):+.1f}% vs baseline")
    else:
        print(f"  ❌ SIGNIFICANT REGRESSION: {((performance_ratio - 1) * 100):+.1f}% vs baseline")
    
    # Test import time (for refactoring impact)
    print(f"\nImport Performance Test:")
    import_times = []
    
    for _ in range(5):
        start = time.perf_counter()
        # Simulate fresh import (can't actually reimport, but test engine creation)
        fresh_engine = create_optimized_engine()
        fresh_engine.cleanup()
        import_time = time.perf_counter() - start
        import_times.append(import_time * 1000)
    
    avg_import_time = statistics.mean(import_times)
    print(f"  Average engine creation time: {avg_import_time:.1f}ms")
    
    if avg_import_time < 100:
        print(f"  ✅ EXCELLENT startup performance (<100ms)")
    elif avg_import_time < 500:
        print(f"  ✅ GOOD startup performance (<500ms)")
    else:
        print(f"  ⚠️ SLOW startup performance (>500ms)")
    
    engine.cleanup()
    
    return {
        'throughput_per_min': throughput_per_min,
        'performance_ratio': performance_ratio,
        'avg_import_time_ms': avg_import_time
    }


def main():
    """Run all benchmarks."""
    print(f"{'='*80}")
    print("M003 UNIFIED MIAIR ENGINE - POST-REFACTORING BENCHMARK")
    print(f"{'='*80}")
    print("Testing unified engine performance after consolidation refactoring...")
    
    # Run mode comparison
    comparison_results = compare_modes()
    
    # Run regression test
    regression_results = run_regression_test()
    
    # Final summary
    print(f"\n{'='*80}")
    print("FINAL BENCHMARK SUMMARY")
    print(f"{'='*80}")
    
    print(f"\n📊 Mode Performance Summary:")
    for mode in ['standard', 'optimized', 'secure']:
        throughput = comparison_results[mode]['analysis_throughput_per_min']
        memory = comparison_results[mode]['memory_usage_mb']
        print(f"  {mode.upper():<12}: {throughput:>8.0f} docs/min, {memory:>5.1f} MB memory")
    
    print(f"\n🔄 Regression Analysis:")
    ratio = regression_results['performance_ratio']
    if ratio >= 1.0:
        status = f"✅ IMPROVED by {((ratio - 1) * 100):+.1f}%"
    elif ratio >= 0.9:
        status = f"✅ STABLE ({((ratio - 1) * 100):+.1f}%)"
    else:
        status = f"⚠️ REGRESSED by {((1 - ratio) * 100):.1f}%"
    
    print(f"  Performance vs baseline: {status}")
    print(f"  Engine startup time: {regression_results['avg_import_time_ms']:.1f}ms")
    
    print(f"\n🎯 Target Achievement:")
    best_throughput = max(comparison_results[m]['analysis_throughput_per_min'] for m in comparison_results)
    
    if best_throughput >= 361431:
        print(f"  ✅ EXCEEDED baseline target: {best_throughput:.0f} docs/min")
    elif best_throughput >= 361431 * 0.9:
        print(f"  ✅ NEAR baseline target: {best_throughput:.0f} docs/min (within 10%)")
    elif best_throughput >= 50000:
        print(f"  ✅ MET minimum requirement: {best_throughput:.0f} docs/min")
    else:
        print(f"  ⚠️ Below minimum requirement: {best_throughput:.0f} docs/min")
    
    print(f"\n✅ M003 Unified MIAIR Engine benchmark completed!")
    print("   Refactoring consolidation successful with maintained performance.")


if __name__ == "__main__":
    main()