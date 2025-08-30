#!/usr/bin/env python3
"""
Performance comparison between original and optimized M007 Review Engine.

Measures improvement metrics and validates optimization effectiveness.
"""

import asyncio
import json
import os
import psutil
import random
import string
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from devdocai.review.review_engine import ReviewEngine
from devdocai.review.review_engine_optimized import OptimizedReviewEngine
from devdocai.review.models import ReviewEngineConfig


class PerformanceComparison:
    """Compare performance between original and optimized engines."""
    
    def __init__(self):
        """Initialize both engines for comparison."""
        self.config = ReviewEngineConfig(
            enable_cache=True,
            cache_ttl_seconds=3600,
            parallel_workers=4,
            batch_size=10,
            enable_all_dimensions=True
        )
        
        self.original_engine = ReviewEngine(self.config)
        self.optimized_engine = OptimizedReviewEngine(self.config)
        self.results = {}
    
    def generate_test_document(self, size: str = 'medium') -> Tuple[str, Dict]:
        """Generate test document for benchmarking."""
        sizes = {
            'small': 500,
            'medium': 5000,
            'large': 50000,
            'huge': 500000
        }
        
        char_count = sizes.get(size, 5000)
        
        # Generate realistic content
        words = ['function', 'method', 'class', 'variable', 'return', 'parameter',
                 'implementation', 'optimization', 'performance', 'security',
                 'documentation', 'testing', 'deployment', 'configuration']
        
        paragraphs = []
        while len(''.join(paragraphs)) < char_count:
            paragraph = ' '.join(random.choices(words, k=random.randint(20, 50)))
            paragraphs.append(paragraph + '\\n\\n')
        
        content = ''.join(paragraphs)[:char_count]
        
        # Add patterns to test optimizations
        content += '\\n\\n## Code Example\\n'
        content += '```python\\n'
        content += 'def example_function(param1: str, param2: int) -> Dict:\\n'
        content += '    """Example function."""\\n'
        content += '    # TODO: Optimize this later\\n'
        content += '    console.log("debug")  # Debug code\\n'
        content += '    password = "hardcoded123"  # Bad practice\\n'
        content += '    return {"result": param1 * param2}\\n'
        content += '```\\n'
        
        # Add PII for security testing
        if random.random() > 0.5:
            content += f'\\nContact: user{random.randint(1,100)}@example.com\\n'
        if random.random() > 0.5:
            content += f'Phone: {random.randint(100,999)}-{random.randint(100,999)}-{random.randint(1000,9999)}\\n'
        
        metadata = {
            'filename': f'test_{size}.md',
            'size': len(content),
            'type': 'markdown',
            'created': datetime.now().isoformat()
        }
        
        return content, metadata
    
    async def compare_single_document(self, size: str) -> Dict:
        """Compare single document review performance."""
        content, metadata = self.generate_test_document(size)
        doc_id = f'compare_{size}'
        
        # Warm up both engines
        await self.original_engine.review_document(content, document_id=f'{doc_id}_warmup', metadata=metadata)
        await self.optimized_engine.review_document(content, document_id=f'{doc_id}_warmup', metadata=metadata)
        
        # Measure original engine (multiple runs)
        original_times = []
        for i in range(5):
            start = time.perf_counter()
            await self.original_engine.review_document(
                content, 
                document_id=f'{doc_id}_orig_{i}',
                metadata=metadata
            )
            end = time.perf_counter()
            original_times.append((end - start) * 1000)
        
        # Clear cache between tests
        self.original_engine._cache.clear()
        self.optimized_engine._cache.clear()
        
        # Measure optimized engine (multiple runs)
        optimized_times = []
        for i in range(5):
            start = time.perf_counter()
            await self.optimized_engine.review_document(
                content,
                document_id=f'{doc_id}_opt_{i}',
                metadata=metadata
            )
            end = time.perf_counter()
            optimized_times.append((end - start) * 1000)
        
        avg_original = sum(original_times) / len(original_times)
        avg_optimized = sum(optimized_times) / len(optimized_times)
        improvement = ((avg_original - avg_optimized) / avg_original * 100) if avg_original > 0 else 0
        speedup = avg_original / avg_optimized if avg_optimized > 0 else 0
        
        return {
            'size': size,
            'doc_size_bytes': len(content),
            'original_avg_ms': avg_original,
            'optimized_avg_ms': avg_optimized,
            'improvement_pct': improvement,
            'speedup_factor': speedup,
            'original_min_ms': min(original_times),
            'optimized_min_ms': min(optimized_times),
        }
    
    async def compare_batch_processing(self, batch_size: int = 50) -> Dict:
        """Compare batch processing performance."""
        documents = []
        for i in range(batch_size):
            size = random.choice(['small', 'medium'])
            content, metadata = self.generate_test_document(size)
            documents.append({
                'content': content,
                'id': f'batch_{i}',
                'type': 'markdown',
                'metadata': metadata
            })
        
        # Measure original batch processing
        start = time.perf_counter()
        original_results = await self.original_engine.batch_review(documents)
        original_time = time.perf_counter() - start
        
        # Measure optimized batch processing
        start = time.perf_counter()
        optimized_results = await self.optimized_engine.batch_review(documents)
        optimized_time = time.perf_counter() - start
        
        improvement = ((original_time - optimized_time) / original_time * 100) if original_time > 0 else 0
        speedup = original_time / optimized_time if optimized_time > 0 else 0
        
        return {
            'batch_size': batch_size,
            'original_time_sec': original_time,
            'optimized_time_sec': optimized_time,
            'original_docs_per_sec': batch_size / original_time if original_time > 0 else 0,
            'optimized_docs_per_sec': batch_size / optimized_time if optimized_time > 0 else 0,
            'improvement_pct': improvement,
            'speedup_factor': speedup,
        }
    
    async def compare_cache_performance(self) -> Dict:
        """Compare cache performance between implementations."""
        documents = []
        for i in range(10):
            content, metadata = self.generate_test_document('small')
            documents.append((content, metadata, f'cache_{i}'))
        
        # Original engine - cold cache
        self.original_engine._cache.clear()
        orig_cold_times = []
        for content, metadata, doc_id in documents:
            start = time.perf_counter()
            await self.original_engine.review_document(content, document_id=doc_id, metadata=metadata)
            orig_cold_times.append((time.perf_counter() - start) * 1000)
        
        # Original engine - warm cache
        orig_warm_times = []
        for content, metadata, doc_id in documents:
            start = time.perf_counter()
            await self.original_engine.review_document(content, document_id=doc_id, metadata=metadata)
            orig_warm_times.append((time.perf_counter() - start) * 1000)
        
        # Optimized engine - cold cache
        await self.optimized_engine._cache.clear()
        opt_cold_times = []
        for content, metadata, doc_id in documents:
            start = time.perf_counter()
            await self.optimized_engine.review_document(content, document_id=doc_id, metadata=metadata)
            opt_cold_times.append((time.perf_counter() - start) * 1000)
        
        # Optimized engine - warm cache
        opt_warm_times = []
        for content, metadata, doc_id in documents:
            start = time.perf_counter()
            await self.optimized_engine.review_document(content, document_id=doc_id, metadata=metadata)
            opt_warm_times.append((time.perf_counter() - start) * 1000)
        
        return {
            'original_cold_avg_ms': sum(orig_cold_times) / len(orig_cold_times),
            'original_warm_avg_ms': sum(orig_warm_times) / len(orig_warm_times),
            'optimized_cold_avg_ms': sum(opt_cold_times) / len(opt_cold_times),
            'optimized_warm_avg_ms': sum(opt_warm_times) / len(opt_warm_times),
            'original_cache_speedup': sum(orig_cold_times) / sum(orig_warm_times) if sum(orig_warm_times) > 0 else 0,
            'optimized_cache_speedup': sum(opt_cold_times) / sum(opt_warm_times) if sum(opt_warm_times) > 0 else 0,
            'optimized_cache_hit_rate': self.optimized_engine._cache.hit_rate,
        }
    
    async def compare_memory_usage(self) -> Dict:
        """Compare memory usage between implementations."""
        process = psutil.Process(os.getpid())
        
        # Generate test documents
        documents = []
        for _ in range(100):
            content, metadata = self.generate_test_document('medium')
            documents.append({
                'content': content,
                'id': f'mem_test_{_}',
                'type': 'markdown',
                'metadata': metadata
            })
        
        # Test original engine
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        await self.original_engine.batch_review(documents[:50])
        original_peak = process.memory_info().rss / 1024 / 1024  # MB
        
        # Clear and test optimized engine
        self.original_engine._cache.clear()
        mid_memory = process.memory_info().rss / 1024 / 1024  # MB
        await self.optimized_engine.batch_review(documents[50:])
        optimized_peak = process.memory_info().rss / 1024 / 1024  # MB
        
        return {
            'original_memory_delta_mb': original_peak - initial_memory,
            'optimized_memory_delta_mb': optimized_peak - mid_memory,
            'memory_improvement_pct': ((original_peak - initial_memory) - (optimized_peak - mid_memory)) / (original_peak - initial_memory) * 100 if (original_peak - initial_memory) > 0 else 0,
        }
    
    async def run_comparison(self) -> Dict:
        """Run all comparison benchmarks."""
        print("=" * 60)
        print("M007 REVIEW ENGINE PERFORMANCE COMPARISON")
        print("Original vs Optimized Implementation")
        print("=" * 60)
        
        # Single document comparison
        print("\\n1. Single Document Review Performance:")
        print("-" * 40)
        single_results = {}
        for size in ['small', 'medium', 'large']:
            result = await self.compare_single_document(size)
            print(f"  {size.upper()} documents (~{result['doc_size_bytes']} bytes):")
            print(f"    Original: {result['original_avg_ms']:.2f}ms")
            print(f"    Optimized: {result['optimized_avg_ms']:.2f}ms")
            print(f"    Improvement: {result['improvement_pct']:.1f}%")
            print(f"    Speedup: {result['speedup_factor']:.2f}x")
            single_results[size] = result
        
        # Batch processing comparison
        print("\\n2. Batch Processing Performance:")
        print("-" * 40)
        batch_result = await self.compare_batch_processing(50)
        print(f"  Batch size: {batch_result['batch_size']} documents")
        print(f"  Original: {batch_result['original_time_sec']:.2f}s ({batch_result['original_docs_per_sec']:.1f} docs/sec)")
        print(f"  Optimized: {batch_result['optimized_time_sec']:.2f}s ({batch_result['optimized_docs_per_sec']:.1f} docs/sec)")
        print(f"  Improvement: {batch_result['improvement_pct']:.1f}%")
        print(f"  Speedup: {batch_result['speedup_factor']:.2f}x")
        
        # Cache comparison
        print("\\n3. Cache Performance:")
        print("-" * 40)
        cache_result = await self.compare_cache_performance()
        print(f"  Original cache speedup: {cache_result['original_cache_speedup']:.2f}x")
        print(f"  Optimized cache speedup: {cache_result['optimized_cache_speedup']:.2f}x")
        print(f"  Optimized hit rate: {cache_result['optimized_cache_hit_rate']:.1%}")
        
        # Memory comparison
        print("\\n4. Memory Usage:")
        print("-" * 40)
        memory_result = await self.compare_memory_usage()
        print(f"  Original delta: {memory_result['original_memory_delta_mb']:.1f}MB")
        print(f"  Optimized delta: {memory_result['optimized_memory_delta_mb']:.1f}MB")
        print(f"  Memory improvement: {memory_result['memory_improvement_pct']:.1f}%")
        
        # Overall summary
        print("\\n" + "=" * 60)
        print("OPTIMIZATION SUMMARY")
        print("=" * 60)
        
        avg_improvement = (
            single_results['small']['improvement_pct'] +
            single_results['medium']['improvement_pct'] +
            single_results['large']['improvement_pct'] +
            batch_result['improvement_pct']
        ) / 4
        
        avg_speedup = (
            single_results['small']['speedup_factor'] +
            single_results['medium']['speedup_factor'] +
            single_results['large']['speedup_factor'] +
            batch_result['speedup_factor']
        ) / 4
        
        print(f"\\nAverage Performance Improvement: {avg_improvement:.1f}%")
        print(f"Average Speedup Factor: {avg_speedup:.2f}x")
        
        # Check against targets
        print("\\nTarget Achievement:")
        targets_met = []
        
        if single_results['small']['optimized_avg_ms'] < 10:
            targets_met.append(f"✅ Small docs: {single_results['small']['optimized_avg_ms']:.2f}ms < 10ms target")
        else:
            targets_met.append(f"❌ Small docs: {single_results['small']['optimized_avg_ms']:.2f}ms > 10ms target")
        
        if single_results['medium']['optimized_avg_ms'] < 50:
            targets_met.append(f"✅ Medium docs: {single_results['medium']['optimized_avg_ms']:.2f}ms < 50ms target")
        else:
            targets_met.append(f"❌ Medium docs: {single_results['medium']['optimized_avg_ms']:.2f}ms > 50ms target")
        
        if single_results['large']['optimized_avg_ms'] < 100:
            targets_met.append(f"✅ Large docs: {single_results['large']['optimized_avg_ms']:.2f}ms < 100ms target")
        else:
            targets_met.append(f"❌ Large docs: {single_results['large']['optimized_avg_ms']:.2f}ms > 100ms target")
        
        if batch_result['optimized_docs_per_sec'] > 100:
            targets_met.append(f"✅ Batch processing: {batch_result['optimized_docs_per_sec']:.1f} docs/sec > 100 target")
        else:
            targets_met.append(f"❌ Batch processing: {batch_result['optimized_docs_per_sec']:.1f} docs/sec < 100 target")
        
        for target in targets_met:
            print(target)
        
        # Save results
        results_file = Path(__file__).parent.parent / 'benchmark_results' / 'm007_comparison.json'
        results_file.parent.mkdir(exist_ok=True)
        
        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'single_document': single_results,
                'batch_processing': batch_result,
                'cache_performance': cache_result,
                'memory_usage': memory_result,
                'average_improvement_pct': avg_improvement,
                'average_speedup_factor': avg_speedup,
                'targets_met': len([t for t in targets_met if '✅' in t]),
                'targets_total': len(targets_met),
            }, f, indent=2)
        
        print(f"\\nResults saved to: {results_file}")
        
        return {
            'single': single_results,
            'batch': batch_result,
            'cache': cache_result,
            'memory': memory_result,
            'summary': {
                'avg_improvement': avg_improvement,
                'avg_speedup': avg_speedup
            }
        }


async def main():
    """Run performance comparison."""
    comparison = PerformanceComparison()
    results = await comparison.run_comparison()
    return results


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())