#!/usr/bin/env python3
"""
Performance validation test for optimized MIAIR Engine
Target: 248,000 documents/minute
"""

import time
import asyncio
import numpy as np
from unittest.mock import Mock
from devdocai.intelligence.miair_optimized import (
    OptimizedMIAIREngine,
    create_optimized_engine,
    OptimizedMetricsCalculator
)
from devdocai.intelligence.llm_adapter import LLMResponse
from devdocai.core.config import ConfigurationManager
from devdocai.core.storage import StorageManager


class FastMockLLM:
    """Mock LLM with minimal latency for performance testing."""
    
    def __init__(self, latency_ms: float = 5):
        self.latency_ms = latency_ms
        self.call_count = 0
    
    def query(self, prompt, **kwargs):
        """Simulate fast LLM response."""
        # Minimal latency to test architecture performance
        time.sleep(self.latency_ms / 1000)
        self.call_count += 1
        
        return LLMResponse(
            content=f"Enhanced content with improved clarity. Random: {np.random.randint(1000)}",
            provider="mock",
            tokens_used=100,
            cost=0.001,
            latency=self.latency_ms / 1000
        )


def generate_test_documents(count: int) -> list:
    """Generate test documents."""
    docs = []
    for i in range(count):
        doc = f"""
        Document {i}: This is a comprehensive technical document covering various aspects
        of software engineering, system architecture, and best practices. The content
        includes detailed analysis of performance optimization techniques, security
        considerations, and architectural patterns. Each section provides in-depth
        coverage of topics with practical examples and implementation guidelines.
        Random content for uniqueness: {np.random.randint(10000)}
        """
        docs.append(doc)
    return docs


async def test_async_performance():
    """Test async optimization performance."""
    print("\n" + "="*60)
    print("ASYNC OPTIMIZATION TEST")
    print("="*60)
    
    # Setup
    config = ConfigurationManager()
    llm = FastMockLLM(latency_ms=5)
    storage = Mock(spec=StorageManager)
    storage.save_document.return_value = "doc_123"
    
    engine = create_optimized_engine(config, llm, storage, "performance")
    documents = generate_test_documents(100)
    
    # Test async batch processing
    start = time.perf_counter()
    results = await engine.batch_optimize_parallel(documents, max_iterations=1)
    elapsed = time.perf_counter() - start
    
    throughput = len(documents) / elapsed
    docs_per_minute = throughput * 60
    
    print(f"Documents processed: {len(documents)}")
    print(f"Time elapsed: {elapsed:.2f}s")
    print(f"Throughput: {throughput:.0f} docs/sec")
    print(f"Throughput: {docs_per_minute:.0f} docs/minute")
    print(f"Target: 248,000 docs/minute")
    print(f"Achievement: {(docs_per_minute / 248000) * 100:.1f}%")
    print(f"LLM calls made: {llm.call_count}")
    
    return docs_per_minute


def test_sync_performance():
    """Test synchronous optimization performance."""
    print("\n" + "="*60)
    print("SYNC OPTIMIZATION TEST")
    print("="*60)
    
    # Setup
    config = ConfigurationManager()
    llm = FastMockLLM(latency_ms=5)
    storage = Mock(spec=StorageManager)
    storage.save_document.return_value = "doc_123"
    
    engine = create_optimized_engine(config, llm, storage, "performance")
    documents = generate_test_documents(100)
    
    # Test sync batch processing
    start = time.perf_counter()
    results = engine.batch_optimize_sync(documents, max_iterations=1)
    elapsed = time.perf_counter() - start
    
    throughput = len(documents) / elapsed
    docs_per_minute = throughput * 60
    
    print(f"Documents processed: {len(documents)}")
    print(f"Time elapsed: {elapsed:.2f}s")
    print(f"Throughput: {throughput:.0f} docs/sec")
    print(f"Throughput: {docs_per_minute:.0f} docs/minute")
    print(f"Target: 248,000 docs/minute")
    print(f"Achievement: {(docs_per_minute / 248000) * 100:.1f}%")
    
    return docs_per_minute


def test_entropy_performance():
    """Test entropy calculation performance."""
    print("\n" + "="*60)
    print("ENTROPY CALCULATION TEST")
    print("="*60)
    
    config = ConfigurationManager()
    calculator = OptimizedMetricsCalculator(config)
    documents = generate_test_documents(1000)
    
    # Test tokenization speed
    start = time.perf_counter()
    for doc in documents[:100]:
        words = calculator.tokenize(doc)
    tokenize_time = time.perf_counter() - start
    
    print(f"Tokenization (100 docs): {tokenize_time:.3f}s")
    print(f"Throughput: {100/tokenize_time:.0f} docs/sec")
    
    # Test vectorized entropy
    words_list = [list(calculator.tokenize(doc)) for doc in documents[:100]]
    
    start = time.perf_counter()
    entropies = calculator.calculate_entropy_vectorized(words_list)
    entropy_time = time.perf_counter() - start
    
    print(f"\nEntropy calculation (100 docs): {entropy_time:.3f}s")
    print(f"Throughput: {100/entropy_time:.0f} docs/sec")
    print(f"Projected: {(100/entropy_time)*60:.0f} docs/minute")
    
    # Test quality measurement
    start = time.perf_counter()
    metrics = calculator.calculate_quality_batch(documents[:100])
    quality_time = time.perf_counter() - start
    
    print(f"\nQuality measurement (100 docs): {quality_time:.3f}s")
    print(f"Throughput: {100/quality_time:.0f} docs/sec")
    print(f"Projected: {(100/quality_time)*60:.0f} docs/minute")


def test_cache_performance():
    """Test caching effectiveness."""
    print("\n" + "="*60)
    print("CACHE PERFORMANCE TEST")
    print("="*60)
    
    config = ConfigurationManager()
    llm = FastMockLLM(latency_ms=5)
    storage = Mock(spec=StorageManager)
    
    engine = create_optimized_engine(config, llm, storage, "performance")
    
    # Generate documents with duplicates
    unique_docs = generate_test_documents(20)
    test_docs = unique_docs * 5  # 100 docs, 20 unique
    
    # Process all documents
    start = time.perf_counter()
    entropies = engine.calculate_entropy_batch(test_docs)
    elapsed = time.perf_counter() - start
    
    # Get statistics
    stats = engine.get_statistics()
    
    print(f"Documents processed: {len(test_docs)}")
    print(f"Unique documents: {len(unique_docs)}")
    print(f"Time elapsed: {elapsed:.3f}s")
    print(f"Cache hits: {stats['cache_hits']}")
    print(f"Cache misses: {stats['cache_misses']}")
    print(f"Cache hit rate: {stats['cache_hit_rate']*100:.1f}%")
    print(f"Throughput: {len(test_docs)/elapsed:.0f} docs/sec")


async def test_streaming():
    """Test streaming optimization."""
    print("\n" + "="*60)
    print("STREAMING OPTIMIZATION TEST")
    print("="*60)
    
    config = ConfigurationManager()
    llm = FastMockLLM(latency_ms=5)
    storage = Mock(spec=StorageManager)
    
    engine = create_optimized_engine(config, llm, storage, "performance")
    
    # Create document stream
    async def document_generator():
        for i in range(50):
            yield f"Streaming document {i}: Technical content with various topics."
            await asyncio.sleep(0.001)  # Simulate document arrival
    
    # Process stream
    start = time.perf_counter()
    results = []
    
    async for result in engine.stream_optimize(document_generator()):
        results.append(result)
    
    elapsed = time.perf_counter() - start
    
    print(f"Documents processed: {len(results)}")
    print(f"Time elapsed: {elapsed:.2f}s")
    print(f"Throughput: {len(results)/elapsed:.1f} docs/sec")


def main():
    """Run all performance tests."""
    print("="*60)
    print("OPTIMIZED MIAIR ENGINE - PERFORMANCE VALIDATION")
    print("Target: 248,000 documents/minute (4,133 docs/sec)")
    print("="*60)
    
    # Run sync tests
    test_entropy_performance()
    test_cache_performance()
    sync_throughput = test_sync_performance()
    
    # Run async tests
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async_throughput = loop.run_until_complete(test_async_performance())
    loop.run_until_complete(test_streaming())
    
    # Summary
    print("\n" + "="*60)
    print("PERFORMANCE SUMMARY")
    print("="*60)
    
    print(f"Sync throughput: {sync_throughput:.0f} docs/minute")
    print(f"Async throughput: {async_throughput:.0f} docs/minute")
    print(f"Target: 248,000 docs/minute")
    
    best_throughput = max(sync_throughput, async_throughput)
    achievement = (best_throughput / 248000) * 100
    
    print(f"\nBest throughput: {best_throughput:.0f} docs/minute")
    print(f"Target achievement: {achievement:.1f}%")
    
    if achievement >= 100:
        print("\n✅ TARGET ACHIEVED!")
    else:
        gap = 248000 - best_throughput
        required_speedup = 248000 / best_throughput
        print(f"\n⚠️ Gap: {gap:.0f} docs/minute")
        print(f"Required speedup: {required_speedup:.1f}x")
        
        print("\nRecommendations for reaching target:")
        print("1. Reduce LLM latency (use local models or caching)")
        print("2. Increase batch size to 2000-5000 documents")
        print("3. Use process pool for CPU-bound operations")
        print("4. Implement GPU acceleration for vectorized operations")
        print("5. Use Redis for distributed caching")


if __name__ == "__main__":
    main()