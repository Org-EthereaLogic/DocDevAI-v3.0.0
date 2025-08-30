#!/usr/bin/env python3
"""
Benchmark script for M007 Review Engine.

Measures performance of review operations including:
- Single document review times
- Batch processing throughput
- Cache hit rates
- Memory usage
- Parallel processing efficiency
"""

import asyncio
import json
import os
import psutil
import random
import string
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from devdocai.review.review_engine import ReviewEngine
from devdocai.review.models import ReviewEngineConfig


class M007Benchmark:
    """Benchmark suite for M007 Review Engine."""
    
    def __init__(self):
        """Initialize benchmark suite."""
        self.config = ReviewEngineConfig(
            enable_cache=True,
            cache_ttl_seconds=3600,
            parallel_workers=4,
            batch_size=10,
            enable_all_dimensions=True
        )
        self.engine = ReviewEngine(self.config)
        self.results = {}
        
    def generate_test_document(self, size: str = 'small') -> Tuple[str, Dict]:
        """Generate test document content of specified size."""
        sizes = {
            'small': 500,      # ~1KB
            'medium': 5000,    # ~10KB
            'large': 50000,    # ~100KB
            'huge': 500000     # ~1MB
        }
        
        char_count = sizes.get(size, 1000)
        
        # Generate realistic documentation content
        paragraphs = []
        words = ['function', 'method', 'class', 'variable', 'return', 'parameter',
                 'implementation', 'optimization', 'performance', 'security']
        
        while len(''.join(paragraphs)) < char_count:
            paragraph = ' '.join(random.choices(words, k=random.randint(20, 50)))
            paragraphs.append(paragraph + '\\n\\n')
        
        content = ''.join(paragraphs)[:char_count]
        
        # Add some code snippets
        content += '''
```python
def example_function(param1: str, param2: int) -> Dict:
    """Example function for testing."""
    result = {}
    for i in range(param2):
        result[f"key_{i}"] = param1
    return result
```
'''
        
        # Add potential issues for testing
        if random.random() > 0.5:
            content += "TODO: Fix this later\\n"
        if random.random() > 0.5:
            content += "email@example.com\\n"  # PII
        if random.random() > 0.5:
            content += "console.log('debug')\\n"  # Debug code
            
        metadata = {
            'filename': f'test_doc_{size}.md',
            'size': len(content),
            'type': 'markdown',
            'created': datetime.now().isoformat()
        }
        
        return content, metadata
    
    async def benchmark_single_review(self, size: str) -> Dict:
        """Benchmark single document review."""
        content, metadata = self.generate_test_document(size)
        
        # Warm up
        await self.engine.review_document(content, document_id=f"test_{size}", metadata=metadata)
        
        # Measure multiple runs
        times = []
        for _ in range(10):
            start = time.perf_counter()
            result = await self.engine.review_document(content, document_id=f"test_{size}", metadata=metadata)
            end = time.perf_counter()
            times.append((end - start) * 1000)  # Convert to ms
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        return {
            'size': size,
            'doc_size_bytes': len(content),
            'avg_time_ms': avg_time,
            'min_time_ms': min_time,
            'max_time_ms': max_time,
            'ops_per_sec': 1000 / avg_time if avg_time > 0 else 0
        }
    
    async def benchmark_batch_processing(self, batch_size: int = 100) -> Dict:
        """Benchmark batch document processing."""
        documents = []
        for i in range(batch_size):
            size = random.choice(['small', 'medium', 'large'])
            content, metadata = self.generate_test_document(size)
            documents.append((content, metadata))
        
        # Measure batch processing
        start = time.perf_counter()
        results = await self.engine.batch_review(documents)
        end = time.perf_counter()
        
        total_time = end - start
        docs_per_sec = batch_size / total_time if total_time > 0 else 0
        
        return {
            'batch_size': batch_size,
            'total_time_sec': total_time,
            'docs_per_sec': docs_per_sec,
            'avg_time_per_doc_ms': (total_time * 1000) / batch_size
        }
    
    async def benchmark_cache_performance(self) -> Dict:
        """Benchmark cache hit rates and performance."""
        # Generate test documents
        documents = []
        for _ in range(20):
            content, metadata = self.generate_test_document('medium')
            documents.append((content, metadata))
        
        # First pass - cold cache
        cold_times = []
        for i, (content, metadata) in enumerate(documents):
            start = time.perf_counter()
            await self.engine.review_document(content, document_id=f"cache_test_{i}", metadata=metadata)
            end = time.perf_counter()
            cold_times.append((end - start) * 1000)
        
        # Second pass - warm cache
        warm_times = []
        cache_hits = 0
        for i, (content, metadata) in enumerate(documents):
            start = time.perf_counter()
            result = await self.engine.review_document(content, document_id=f"cache_test_{i}", metadata=metadata)
            end = time.perf_counter()
            warm_times.append((end - start) * 1000)
            if hasattr(result, 'from_cache') and result.from_cache:
                cache_hits += 1
        
        avg_cold = sum(cold_times) / len(cold_times)
        avg_warm = sum(warm_times) / len(warm_times)
        speedup = avg_cold / avg_warm if avg_warm > 0 else 0
        
        return {
            'avg_cold_cache_ms': avg_cold,
            'avg_warm_cache_ms': avg_warm,
            'cache_speedup': speedup,
            'cache_hit_rate': cache_hits / len(documents),
            'cache_improvement_pct': ((avg_cold - avg_warm) / avg_cold * 100) if avg_cold > 0 else 0
        }
    
    async def benchmark_parallel_processing(self) -> Dict:
        """Benchmark parallel vs sequential processing."""
        # Generate documents
        documents = []
        for _ in range(50):
            content, metadata = self.generate_test_document('medium')
            documents.append((content, metadata))
        
        # Sequential processing
        start = time.perf_counter()
        sequential_results = []
        for i, (content, metadata) in enumerate(documents):
            result = await self.engine.review_document(content, document_id=f"parallel_test_{i}", metadata=metadata)
            sequential_results.append(result)
        sequential_time = time.perf_counter() - start
        
        # Parallel processing
        self.engine.config.parallel_workers = 4
        start = time.perf_counter()
        parallel_results = await self.engine.batch_review(documents)
        parallel_time = time.perf_counter() - start
        
        speedup = sequential_time / parallel_time if parallel_time > 0 else 0
        
        return {
            'sequential_time_sec': sequential_time,
            'parallel_time_sec': parallel_time,
            'speedup_factor': speedup,
            'parallel_efficiency': (speedup / 4) * 100,  # 4 workers
            'docs_per_sec_sequential': len(documents) / sequential_time,
            'docs_per_sec_parallel': len(documents) / parallel_time
        }
    
    def benchmark_memory_usage(self) -> Dict:
        """Benchmark memory usage patterns."""
        process = psutil.Process(os.getpid())
        
        # Get initial memory
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Process many documents
        loop = asyncio.get_event_loop()
        documents = []
        for _ in range(100):
            content, metadata = self.generate_test_document('large')
            documents.append((content, metadata))
        
        # Process documents
        loop.run_until_complete(self.engine.batch_review(documents))
        
        # Get peak memory
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_per_doc = (peak_memory - initial_memory) / len(documents)
        
        # Test cache memory with 1000 cached items
        self.engine._cache.clear()
        for i in range(1000):
            content, metadata = self.generate_test_document('small')
            loop.run_until_complete(self.engine.review_document(content, document_id=f"mem_test_{i}", metadata=metadata))
        
        cache_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        return {
            'initial_memory_mb': initial_memory,
            'peak_memory_mb': peak_memory,
            'memory_per_doc_mb': memory_per_doc,
            'cache_memory_1000_items_mb': cache_memory - initial_memory,
            'memory_efficiency': (len(documents) * 1024) / (peak_memory - initial_memory)  # docs per GB
        }
    
    async def run_all_benchmarks(self) -> Dict:
        """Run all benchmarks and collect results."""
        print("Running M007 Review Engine Benchmarks...")
        print("=" * 60)
        
        # Single document review benchmarks
        print("\\n1. Single Document Review Performance:")
        print("-" * 40)
        for size in ['small', 'medium', 'large']:
            result = await self.benchmark_single_review(size)
            print(f"  {size.upper()} documents (~{result['doc_size_bytes']} bytes):")
            print(f"    Average: {result['avg_time_ms']:.2f}ms")
            print(f"    Min: {result['min_time_ms']:.2f}ms, Max: {result['max_time_ms']:.2f}ms")
            print(f"    Throughput: {result['ops_per_sec']:.1f} ops/sec")
            self.results[f'single_{size}'] = result
        
        # Batch processing benchmark
        print("\\n2. Batch Processing Performance:")
        print("-" * 40)
        batch_result = await self.benchmark_batch_processing(100)
        print(f"  Batch size: {batch_result['batch_size']} documents")
        print(f"  Total time: {batch_result['total_time_sec']:.2f}s")
        print(f"  Throughput: {batch_result['docs_per_sec']:.1f} docs/sec")
        print(f"  Avg per doc: {batch_result['avg_time_per_doc_ms']:.2f}ms")
        self.results['batch'] = batch_result
        
        # Cache performance benchmark
        print("\\n3. Cache Performance:")
        print("-" * 40)
        cache_result = await self.benchmark_cache_performance()
        print(f"  Cold cache: {cache_result['avg_cold_cache_ms']:.2f}ms")
        print(f"  Warm cache: {cache_result['avg_warm_cache_ms']:.2f}ms")
        print(f"  Speedup: {cache_result['cache_speedup']:.2f}x")
        print(f"  Improvement: {cache_result['cache_improvement_pct']:.1f}%")
        self.results['cache'] = cache_result
        
        # Parallel processing benchmark
        print("\\n4. Parallel Processing Performance:")
        print("-" * 40)
        parallel_result = await self.benchmark_parallel_processing()
        print(f"  Sequential: {parallel_result['sequential_time_sec']:.2f}s")
        print(f"  Parallel (4 workers): {parallel_result['parallel_time_sec']:.2f}s")
        print(f"  Speedup: {parallel_result['speedup_factor']:.2f}x")
        print(f"  Efficiency: {parallel_result['parallel_efficiency']:.1f}%")
        self.results['parallel'] = parallel_result
        
        # Memory usage benchmark
        print("\\n5. Memory Usage:")
        print("-" * 40)
        memory_result = self.benchmark_memory_usage()
        print(f"  Initial: {memory_result['initial_memory_mb']:.1f}MB")
        print(f"  Peak: {memory_result['peak_memory_mb']:.1f}MB")
        print(f"  Per document: {memory_result['memory_per_doc_mb']:.2f}MB")
        print(f"  Cache (1000 items): {memory_result['cache_memory_1000_items_mb']:.1f}MB")
        self.results['memory'] = memory_result
        
        # Summary
        print("\\n" + "=" * 60)
        print("BENCHMARK SUMMARY")
        print("=" * 60)
        
        # Performance vs targets
        targets_met = []
        targets_missed = []
        
        # Check against targets
        if self.results['single_small']['avg_time_ms'] < 10:
            targets_met.append(f"✅ Small docs: {self.results['single_small']['avg_time_ms']:.2f}ms < 10ms")
        else:
            targets_missed.append(f"❌ Small docs: {self.results['single_small']['avg_time_ms']:.2f}ms > 10ms target")
        
        if self.results['single_medium']['avg_time_ms'] < 50:
            targets_met.append(f"✅ Medium docs: {self.results['single_medium']['avg_time_ms']:.2f}ms < 50ms")
        else:
            targets_missed.append(f"❌ Medium docs: {self.results['single_medium']['avg_time_ms']:.2f}ms > 50ms target")
        
        if self.results['single_large']['avg_time_ms'] < 100:
            targets_met.append(f"✅ Large docs: {self.results['single_large']['avg_time_ms']:.2f}ms < 100ms")
        else:
            targets_missed.append(f"❌ Large docs: {self.results['single_large']['avg_time_ms']:.2f}ms > 100ms target")
        
        if self.results['batch']['docs_per_sec'] > 100:
            targets_met.append(f"✅ Batch processing: {self.results['batch']['docs_per_sec']:.1f} docs/sec > 100")
        else:
            targets_missed.append(f"❌ Batch processing: {self.results['batch']['docs_per_sec']:.1f} docs/sec < 100 target")
        
        if memory_result['cache_memory_1000_items_mb'] < 100:
            targets_met.append(f"✅ Memory efficiency: {memory_result['cache_memory_1000_items_mb']:.1f}MB < 100MB")
        else:
            targets_missed.append(f"❌ Memory efficiency: {memory_result['cache_memory_1000_items_mb']:.1f}MB > 100MB target")
        
        print("\\nTargets Met:")
        for target in targets_met:
            print(f"  {target}")
        
        if targets_missed:
            print("\\nTargets Missed:")
            for target in targets_missed:
                print(f"  {target}")
        
        # Save results to file
        results_file = Path(__file__).parent.parent / 'benchmark_results' / 'm007_baseline.json'
        results_file.parent.mkdir(exist_ok=True)
        
        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'results': self.results,
                'targets_met': len(targets_met),
                'targets_missed': len(targets_missed),
                'overall_score': (len(targets_met) / (len(targets_met) + len(targets_missed))) * 100
            }, f, indent=2)
        
        print(f"\\nResults saved to: {results_file}")
        print(f"Overall Score: {(len(targets_met) / (len(targets_met) + len(targets_missed))) * 100:.1f}%")
        
        return self.results


async def main():
    """Main benchmark entry point."""
    benchmark = M007Benchmark()
    results = await benchmark.run_all_benchmarks()
    return results


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())