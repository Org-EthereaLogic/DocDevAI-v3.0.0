#!/usr/bin/env python3
"""
Comprehensive benchmark suite for M002 Local Storage System optimization.

Tests performance improvements from Pass 2 optimization efforts.
Target: 200,000+ queries/second
"""

import time
import sys
import os
import threading
import statistics
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Tuple
import argparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from devdocai.core.config import ConfigurationManager
from devdocai.storage.local_storage import LocalStorageSystem, DocumentData, QueryParams, DocumentType
from devdocai.storage.optimized_storage import OptimizedStorageSystem


class StorageBenchmark:
    """Comprehensive benchmark suite for storage performance."""
    
    def __init__(self, use_optimized: bool = True, num_docs: int = 1000):
        """
        Initialize benchmark suite.
        
        Args:
            use_optimized: Use OptimizedStorageSystem vs original
            num_docs: Number of test documents to create
        """
        self.use_optimized = use_optimized
        self.num_docs = num_docs
        self.config_manager = ConfigurationManager()
        
        # Initialize storage system
        if use_optimized:
            print("Using OptimizedStorageSystem with FastPath")
            self.storage = OptimizedStorageSystem(
                self.config_manager,
                enable_fast_path=True,
                cache_size=10000
            )
            # Warm cache for fair comparison
            if hasattr(self.storage, 'warm_cache'):
                self.storage.warm_cache(limit=min(1000, num_docs))
        else:
            print("Using original LocalStorageSystem")
            self.storage = LocalStorageSystem(self.config_manager)
        
        self.document_ids = []
        self.results = {}
    
    def setup_test_data(self):
        """Create test documents for benchmarking."""
        print(f"\nCreating {self.num_docs} test documents...")
        
        start = time.time()
        for i in range(self.num_docs):
            data = DocumentData(
                title=f"Benchmark Document {i}",
                content=f"This is test content for document {i}. " * 50,  # ~1KB
                type=DocumentType.TECHNICAL if i % 3 == 0 else DocumentType.API,
                metadata={
                    'index': i,
                    'category': f"cat_{i % 10}",
                    'tags': [f"tag_{j}" for j in range(5)],
                    'benchmark': True
                }
            )
            doc = self.storage.create_document(data)
            self.document_ids.append(doc['id'])
            
            if (i + 1) % 100 == 0:
                print(f"  Created {i + 1} documents...")
        
        elapsed = time.time() - start
        print(f"Setup complete: {self.num_docs} documents in {elapsed:.2f}s")
        print(f"Rate: {self.num_docs / elapsed:.1f} docs/second\n")
    
    def benchmark_single_queries(self, num_queries: int = 10000) -> Dict[str, Any]:
        """Benchmark single document queries."""
        print(f"Benchmarking {num_queries} single queries...")
        
        latencies = []
        start = time.time()
        
        for i in range(num_queries):
            # Query random document
            doc_id = self.document_ids[i % len(self.document_ids)]
            
            query_start = time.perf_counter()
            doc = self.storage.get_document(document_id=doc_id)
            query_time = time.perf_counter() - query_start
            
            latencies.append(query_time * 1000)  # Convert to milliseconds
        
        elapsed = time.time() - start
        
        return {
            'total_queries': num_queries,
            'total_time': elapsed,
            'queries_per_second': num_queries / elapsed,
            'avg_latency_ms': statistics.mean(latencies),
            'p50_latency_ms': statistics.median(latencies),
            'p95_latency_ms': statistics.quantiles(latencies, n=20)[18],  # 95th percentile
            'p99_latency_ms': statistics.quantiles(latencies, n=100)[98],  # 99th percentile
            'min_latency_ms': min(latencies),
            'max_latency_ms': max(latencies)
        }
    
    def benchmark_batch_queries(self, num_batches: int = 1000, batch_size: int = 10) -> Dict[str, Any]:
        """Benchmark batch document queries."""
        print(f"Benchmarking {num_batches} batch queries (size={batch_size})...")
        
        if not hasattr(self.storage, 'get_documents_batch'):
            print("  Batch queries not supported, using sequential queries...")
            
        latencies = []
        start = time.time()
        
        for i in range(num_batches):
            # Select batch of documents
            start_idx = (i * batch_size) % len(self.document_ids)
            batch_ids = self.document_ids[start_idx:start_idx + batch_size]
            
            if len(batch_ids) < batch_size:
                # Wrap around
                batch_ids.extend(self.document_ids[:batch_size - len(batch_ids)])
            
            query_start = time.perf_counter()
            
            if hasattr(self.storage, 'get_documents_batch'):
                docs = self.storage.get_documents_batch(batch_ids)
            else:
                # Fallback to sequential queries
                docs = {}
                for doc_id in batch_ids:
                    doc = self.storage.get_document(document_id=doc_id)
                    if doc:
                        docs[doc_id] = doc
            
            query_time = time.perf_counter() - query_start
            latencies.append(query_time * 1000)
        
        elapsed = time.time() - start
        total_docs = num_batches * batch_size
        
        return {
            'total_batches': num_batches,
            'batch_size': batch_size,
            'total_documents': total_docs,
            'total_time': elapsed,
            'docs_per_second': total_docs / elapsed,
            'avg_batch_latency_ms': statistics.mean(latencies),
            'p95_batch_latency_ms': statistics.quantiles(latencies, n=20)[18],
            'p99_batch_latency_ms': statistics.quantiles(latencies, n=100)[98]
        }
    
    def benchmark_concurrent_queries(self, num_threads: int = 10, queries_per_thread: int = 1000) -> Dict[str, Any]:
        """Benchmark concurrent query performance."""
        print(f"Benchmarking concurrent queries ({num_threads} threads, {queries_per_thread} queries each)...")
        
        def worker(thread_id: int) -> Tuple[int, float, List[float]]:
            """Worker thread for concurrent queries."""
            latencies = []
            start = time.time()
            
            for i in range(queries_per_thread):
                doc_id = self.document_ids[(thread_id * queries_per_thread + i) % len(self.document_ids)]
                
                query_start = time.perf_counter()
                doc = self.storage.get_document(document_id=doc_id)
                query_time = time.perf_counter() - query_start
                
                latencies.append(query_time * 1000)
            
            elapsed = time.time() - start
            return queries_per_thread, elapsed, latencies
        
        all_latencies = []
        start = time.time()
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, i) for i in range(num_threads)]
            
            for future in as_completed(futures):
                queries, thread_time, latencies = future.result()
                all_latencies.extend(latencies)
        
        elapsed = time.time() - start
        total_queries = num_threads * queries_per_thread
        
        return {
            'num_threads': num_threads,
            'queries_per_thread': queries_per_thread,
            'total_queries': total_queries,
            'total_time': elapsed,
            'queries_per_second': total_queries / elapsed,
            'avg_latency_ms': statistics.mean(all_latencies),
            'p95_latency_ms': statistics.quantiles(all_latencies, n=20)[18],
            'p99_latency_ms': statistics.quantiles(all_latencies, n=100)[98]
        }
    
    def benchmark_search(self, num_searches: int = 1000) -> Dict[str, Any]:
        """Benchmark full-text search performance."""
        print(f"Benchmarking {num_searches} search queries...")
        
        search_terms = ['document', 'test', 'content', 'benchmark', 'technical', 'api']
        latencies = []
        start = time.time()
        
        for i in range(num_searches):
            term = search_terms[i % len(search_terms)]
            
            query_start = time.perf_counter()
            results = self.storage.search(term, limit=10)
            query_time = time.perf_counter() - query_start
            
            latencies.append(query_time * 1000)
        
        elapsed = time.time() - start
        
        return {
            'total_searches': num_searches,
            'total_time': elapsed,
            'searches_per_second': num_searches / elapsed,
            'avg_latency_ms': statistics.mean(latencies),
            'p95_latency_ms': statistics.quantiles(latencies, n=20)[18],
            'p99_latency_ms': statistics.quantiles(latencies, n=100)[98]
        }
    
    def benchmark_list_operations(self, num_operations: int = 1000) -> Dict[str, Any]:
        """Benchmark list/filter operations."""
        print(f"Benchmarking {num_operations} list operations...")
        
        latencies = []
        start = time.time()
        
        for i in range(num_operations):
            params = QueryParams(
                type=DocumentType.TECHNICAL if i % 2 == 0 else DocumentType.API,
                limit=10,
                offset=(i * 10) % 100
            )
            
            query_start = time.perf_counter()
            results = self.storage.list_documents(params)
            query_time = time.perf_counter() - query_start
            
            latencies.append(query_time * 1000)
        
        elapsed = time.time() - start
        
        return {
            'total_operations': num_operations,
            'total_time': elapsed,
            'operations_per_second': num_operations / elapsed,
            'avg_latency_ms': statistics.mean(latencies),
            'p95_latency_ms': statistics.quantiles(latencies, n=20)[18],
            'p99_latency_ms': statistics.quantiles(latencies, n=100)[98]
        }
    
    def benchmark_cache_effectiveness(self) -> Dict[str, Any]:
        """Benchmark cache hit rates and performance."""
        if not self.use_optimized:
            return {'message': 'Cache not available in original implementation'}
        
        print("Benchmarking cache effectiveness...")
        
        # Clear cache for fair test
        if hasattr(self.storage, 'clear_cache'):
            self.storage.clear_cache()
        
        # Cold cache queries
        cold_latencies = []
        for i in range(100):
            doc_id = self.document_ids[i]
            
            query_start = time.perf_counter()
            doc = self.storage.get_document(document_id=doc_id)
            query_time = time.perf_counter() - query_start
            
            cold_latencies.append(query_time * 1000)
        
        # Warm cache queries (same documents)
        warm_latencies = []
        for i in range(100):
            doc_id = self.document_ids[i]
            
            query_start = time.perf_counter()
            doc = self.storage.get_document(document_id=doc_id)
            query_time = time.perf_counter() - query_start
            
            warm_latencies.append(query_time * 1000)
        
        # Get cache statistics
        stats = self.storage.get_statistics()
        cache_stats = stats.get('cache', {})
        
        return {
            'cold_cache_avg_ms': statistics.mean(cold_latencies),
            'warm_cache_avg_ms': statistics.mean(warm_latencies),
            'speedup_factor': statistics.mean(cold_latencies) / statistics.mean(warm_latencies),
            'cache_hit_rate': cache_stats.get('cache_hit_rate', 0),
            'cache_size': cache_stats.get('cache_stats', {}).get('size', 0)
        }
    
    def run_all_benchmarks(self) -> Dict[str, Any]:
        """Run complete benchmark suite."""
        print(f"\n{'='*60}")
        print(f"Running M002 Storage Benchmarks")
        print(f"Mode: {'Optimized with FastPath' if self.use_optimized else 'Original Implementation'}")
        print(f"{'='*60}\n")
        
        # Setup test data
        self.setup_test_data()
        
        # Run benchmarks
        self.results['single_queries'] = self.benchmark_single_queries(10000)
        self.results['batch_queries'] = self.benchmark_batch_queries(1000, 10)
        self.results['concurrent_queries'] = self.benchmark_concurrent_queries(10, 1000)
        self.results['search'] = self.benchmark_search(1000)
        self.results['list_operations'] = self.benchmark_list_operations(1000)
        self.results['cache_effectiveness'] = self.benchmark_cache_effectiveness()
        
        # Get storage statistics
        self.results['storage_stats'] = self.storage.get_statistics()
        
        return self.results
    
    def print_results(self):
        """Print formatted benchmark results."""
        print(f"\n{'='*60}")
        print(f"BENCHMARK RESULTS")
        print(f"{'='*60}\n")
        
        # Single queries
        sq = self.results['single_queries']
        print("📊 Single Query Performance:")
        print(f"  • Queries/second: {sq['queries_per_second']:,.0f}")
        print(f"  • Avg latency: {sq['avg_latency_ms']:.3f} ms")
        print(f"  • P95 latency: {sq['p95_latency_ms']:.3f} ms")
        print(f"  • P99 latency: {sq['p99_latency_ms']:.3f} ms")
        
        # Batch queries
        bq = self.results['batch_queries']
        print(f"\n📦 Batch Query Performance:")
        print(f"  • Documents/second: {bq['docs_per_second']:,.0f}")
        print(f"  • Avg batch latency: {bq['avg_batch_latency_ms']:.3f} ms")
        print(f"  • P95 batch latency: {bq['p95_batch_latency_ms']:.3f} ms")
        
        # Concurrent queries
        cq = self.results['concurrent_queries']
        print(f"\n🔄 Concurrent Query Performance ({cq['num_threads']} threads):")
        print(f"  • Queries/second: {cq['queries_per_second']:,.0f}")
        print(f"  • Avg latency: {cq['avg_latency_ms']:.3f} ms")
        print(f"  • P95 latency: {cq['p95_latency_ms']:.3f} ms")
        
        # Search
        s = self.results['search']
        print(f"\n🔍 Search Performance:")
        print(f"  • Searches/second: {s['searches_per_second']:,.0f}")
        print(f"  • Avg latency: {s['avg_latency_ms']:.3f} ms")
        
        # List operations
        lo = self.results['list_operations']
        print(f"\n📋 List Operations Performance:")
        print(f"  • Operations/second: {lo['operations_per_second']:,.0f}")
        print(f"  • Avg latency: {lo['avg_latency_ms']:.3f} ms")
        
        # Cache effectiveness (if available)
        if 'cache_effectiveness' in self.results:
            ce = self.results['cache_effectiveness']
            if 'speedup_factor' in ce:
                print(f"\n💾 Cache Effectiveness:")
                print(f"  • Cold cache latency: {ce['cold_cache_avg_ms']:.3f} ms")
                print(f"  • Warm cache latency: {ce['warm_cache_avg_ms']:.3f} ms")
                print(f"  • Speedup factor: {ce['speedup_factor']:.1f}x")
                print(f"  • Cache hit rate: {ce['cache_hit_rate']*100:.1f}%")
        
        # Performance vs target
        print(f"\n🎯 Target Achievement:")
        target_qps = 200000
        achieved_qps = sq['queries_per_second']
        percentage = (achieved_qps / target_qps) * 100
        
        if achieved_qps >= target_qps:
            print(f"  ✅ TARGET ACHIEVED: {achieved_qps:,.0f} queries/sec ({percentage:.1f}% of target)")
        else:
            print(f"  ⚠️  Current: {achieved_qps:,.0f} queries/sec ({percentage:.1f}% of target)")
            print(f"  📈 Need {(target_qps/achieved_qps):.1f}x improvement")
    
    def save_results(self, filename: str):
        """Save results to JSON file."""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"\nResults saved to {filename}")
    
    def cleanup(self):
        """Clean up test data and close connections."""
        print("\nCleaning up...")
        
        # Delete test documents
        for doc_id in self.document_ids:
            self.storage.delete_document(doc_id, hard_delete=True)
        
        # Close storage
        self.storage.close()
        print("Cleanup complete")


def compare_implementations():
    """Compare original vs optimized implementation."""
    print("\n" + "="*70)
    print("COMPARATIVE BENCHMARK: Original vs Optimized")
    print("="*70)
    
    # Benchmark original
    print("\n1. Testing ORIGINAL Implementation...")
    original = StorageBenchmark(use_optimized=False, num_docs=500)
    original_results = original.run_all_benchmarks()
    original.cleanup()
    
    # Benchmark optimized
    print("\n2. Testing OPTIMIZED Implementation...")
    optimized = StorageBenchmark(use_optimized=True, num_docs=500)
    optimized_results = optimized.run_all_benchmarks()
    optimized.cleanup()
    
    # Compare results
    print("\n" + "="*70)
    print("PERFORMANCE COMPARISON")
    print("="*70)
    
    metrics = [
        ('Single Queries/sec', 'single_queries', 'queries_per_second'),
        ('Concurrent Queries/sec', 'concurrent_queries', 'queries_per_second'),
        ('Search/sec', 'search', 'searches_per_second'),
        ('List Ops/sec', 'list_operations', 'operations_per_second')
    ]
    
    for name, category, metric in metrics:
        original_val = original_results[category][metric]
        optimized_val = optimized_results[category][metric]
        improvement = (optimized_val / original_val - 1) * 100
        
        print(f"\n{name}:")
        print(f"  Original:  {original_val:>10,.0f}")
        print(f"  Optimized: {optimized_val:>10,.0f}")
        print(f"  Improvement: {improvement:>7.1f}%")
    
    # Save comparison
    comparison = {
        'original': original_results,
        'optimized': optimized_results,
        'improvements': {
            'single_queries': optimized_results['single_queries']['queries_per_second'] / 
                            original_results['single_queries']['queries_per_second'],
            'concurrent': optimized_results['concurrent_queries']['queries_per_second'] / 
                         original_results['concurrent_queries']['queries_per_second'],
            'search': optimized_results['search']['searches_per_second'] / 
                     original_results['search']['searches_per_second']
        }
    }
    
    with open('benchmark_comparison.json', 'w') as f:
        json.dump(comparison, f, indent=2, default=str)
    
    print("\n✅ Comparison saved to benchmark_comparison.json")


def main():
    """Main benchmark entry point."""
    parser = argparse.ArgumentParser(description='Benchmark M002 Storage System')
    parser.add_argument('--mode', choices=['original', 'optimized', 'compare'],
                       default='optimized', help='Benchmark mode')
    parser.add_argument('--num-docs', type=int, default=1000,
                       help='Number of test documents')
    parser.add_argument('--output', help='Output file for results')
    
    args = parser.parse_args()
    
    if args.mode == 'compare':
        compare_implementations()
    else:
        benchmark = StorageBenchmark(
            use_optimized=(args.mode == 'optimized'),
            num_docs=args.num_docs
        )
        
        try:
            benchmark.run_all_benchmarks()
            benchmark.print_results()
            
            if args.output:
                benchmark.save_results(args.output)
        finally:
            benchmark.cleanup()


if __name__ == '__main__':
    main()