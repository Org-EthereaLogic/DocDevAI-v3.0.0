#!/usr/bin/env python3
"""
Quick performance analysis of M003 MIAIR Engine
"""

import time
import numpy as np
from devdocai.intelligence.miair import MIAIREngine, MetricsCalculator
from devdocai.core.config import ConfigurationManager
from devdocai.intelligence.llm_adapter import LLMAdapter, LLMResponse
from devdocai.core.storage import StorageManager
from unittest.mock import Mock


# Mock LLM for testing
class MockLLM:
    def query(self, prompt, **kwargs):
        # Simulate 50ms API latency
        time.sleep(0.05)
        return LLMResponse(
            content="Enhanced content",
            provider="mock",
            tokens_used=100,
            cost=0.001,
            latency=0.05
        )


def analyze_current_performance():
    """Analyze current MIAIR performance characteristics."""
    
    print("="*60)
    print("M003 MIAIR ENGINE - PERFORMANCE ANALYSIS")
    print("Target: 248,000 documents/minute (4,133 docs/sec)")
    print("="*60)
    
    # Initialize components
    config = ConfigurationManager()
    llm = MockLLM()
    storage = Mock(spec=StorageManager)
    storage.save_document.return_value = "doc_123"
    
    engine = MIAIREngine(config, llm, storage)
    calculator = MetricsCalculator(config)
    
    # Test documents
    test_docs = [
        f"Document {i}: This is a test document with various content for performance testing. " * 10
        for i in range(100)
    ]
    
    print("\n1. SHANNON ENTROPY CALCULATION")
    print("-" * 40)
    
    # Test single entropy calculation
    doc = test_docs[0]
    
    # First call (no cache)
    start = time.perf_counter()
    entropy1 = engine.calculate_entropy(doc)
    time1 = time.perf_counter() - start
    
    # Second call (cached)
    start = time.perf_counter()
    entropy2 = engine.calculate_entropy(doc)
    time2 = time.perf_counter() - start
    
    print(f"First call: {time1*1000:.2f}ms (entropy: {entropy1:.4f})")
    print(f"Cached call: {time2*1000:.2f}ms (entropy: {entropy2:.4f})")
    print(f"Cache speedup: {time1/time2:.1f}x")
    
    # Batch processing
    start = time.perf_counter()
    entropies = engine.calculate_entropy_batch(test_docs[:50])
    batch_time = time.perf_counter() - start
    
    throughput = len(test_docs[:50]) / batch_time
    print(f"\nBatch processing (50 docs):")
    print(f"  Time: {batch_time:.2f}s")
    print(f"  Throughput: {throughput:.0f} docs/sec")
    print(f"  Projected: {throughput*60:.0f} docs/minute")
    
    print("\n2. QUALITY MEASUREMENT")
    print("-" * 40)
    
    # Measure quality calculation time
    times = []
    for doc in test_docs[:10]:
        start = time.perf_counter()
        metrics = engine.measure_quality(doc)
        elapsed = time.perf_counter() - start
        times.append(elapsed)
    
    avg_time = np.mean(times)
    print(f"Average quality measurement: {avg_time*1000:.2f}ms")
    print(f"Throughput: {1/avg_time:.0f} docs/sec")
    
    # Component breakdown
    doc = test_docs[0]
    words = calculator.tokenize(doc)
    
    start = time.perf_counter()
    calculator.calculate_entropy(words)
    entropy_time = time.perf_counter() - start
    
    start = time.perf_counter()
    calculator.calculate_coherence(doc, words)
    coherence_time = time.perf_counter() - start
    
    print(f"\nComponent breakdown:")
    print(f"  Tokenization: ~{(avg_time - entropy_time - coherence_time)*1000:.2f}ms")
    print(f"  Entropy calc: {entropy_time*1000:.2f}ms")
    print(f"  Coherence calc: {coherence_time*1000:.2f}ms")
    
    print("\n3. OPTIMIZATION PIPELINE")
    print("-" * 40)
    
    # Single document optimization
    start = time.perf_counter()
    result = engine.optimize(test_docs[0], max_iterations=1)
    single_time = time.perf_counter() - start
    
    print(f"Single doc optimization: {single_time:.2f}s")
    print(f"  Initial quality: {result.initial_quality:.1f}")
    print(f"  Final quality: {result.final_quality:.1f}")
    print(f"  Improvement: {result.improvement_percentage:.1f}%")
    
    # Batch optimization
    batch_size = 10
    start = time.perf_counter()
    results = engine.batch_optimize(test_docs[:batch_size], max_iterations=1)
    batch_time = time.perf_counter() - start
    
    throughput = batch_size / batch_time
    print(f"\nBatch optimization ({batch_size} docs):")
    print(f"  Time: {batch_time:.2f}s")
    print(f"  Throughput: {throughput:.1f} docs/sec")
    print(f"  Projected: {throughput*60:.0f} docs/minute")
    
    # Calculate speedup
    sequential_estimate = single_time * batch_size
    speedup = sequential_estimate / batch_time
    print(f"  Parallel speedup: {speedup:.1f}x")
    
    print("\n4. BOTTLENECK ANALYSIS")
    print("-" * 40)
    
    # The main bottleneck is the LLM call
    print("Identified bottlenecks:")
    print(f"1. LLM API calls: ~50ms per call (mock)")
    print(f"2. Quality measurement: ~{avg_time*1000:.1f}ms per doc")
    print(f"3. Tokenization: Regex-based, not optimized")
    print(f"4. Sequential processing in some areas")
    
    print("\n5. PERFORMANCE PROJECTIONS")
    print("-" * 40)
    
    # Current performance
    current_throughput = throughput * 60  # docs/minute
    target = 248000
    gap = target - current_throughput
    required_speedup = target / current_throughput
    
    print(f"Current throughput: {current_throughput:.0f} docs/minute")
    print(f"Target: {target:,} docs/minute")
    print(f"Gap: {gap:,.0f} docs/minute")
    print(f"Required speedup: {required_speedup:.1f}x")
    
    print("\n6. OPTIMIZATION RECOMMENDATIONS")
    print("-" * 40)
    
    recommendations = [
        "1. **Batch Processing**: Increase batch size to 500-1000 documents",
        "2. **Caching**: Implement multi-level caching (LRU + Redis)",
        "3. **Vectorization**: Use NumPy for all array operations",
        "4. **Tokenization**: Replace regex with faster tokenizer (spaCy)",
        "5. **Async Processing**: Use asyncio for I/O operations",
        "6. **Worker Scaling**: Increase to 16-32 workers",
        "7. **Memory Pool**: Pre-allocate memory for batch operations",
        "8. **JIT Compilation**: Use Numba for hot paths",
    ]
    
    for rec in recommendations:
        print(rec)
    
    # Cache statistics
    stats = engine.get_statistics()
    print(f"\n7. CACHE STATISTICS")
    print("-" * 40)
    print(f"Cache hits: {stats.get('cache_hits', 0)}")
    print(f"Cache misses: {stats.get('cache_misses', 0)}")
    print(f"Cache size: {stats.get('cache_size', 0)}")
    
    print("\n" + "="*60)
    print("ANALYSIS COMPLETE")
    print("="*60)


if __name__ == "__main__":
    analyze_current_performance()