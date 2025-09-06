#!/usr/bin/env python3
"""
M002 Local Storage System - Performance Benchmark Suite

Comprehensive performance benchmarks for Pass 2 optimization validation.
"""

import time
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Any
import random
import string
import statistics
from datetime import datetime, timezone

from devdocai.storage.storage_manager import LocalStorageManager
from devdocai.storage.optimized_storage_manager import OptimizedLocalStorageManager
from devdocai.storage.models import Document, DocumentMetadata, ContentType, DocumentStatus
from devdocai.core.config import ConfigurationManager, MemoryMode


class StorageBenchmark:
    """Performance benchmark suite for M002 storage system."""
    
    def __init__(self):
        """Initialize benchmark suite."""
        self.results = {}
        self.temp_dirs = []
    
    def cleanup(self):
        """Clean up temporary directories."""
        for temp_dir in self.temp_dirs:
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
    
    def generate_document(self, doc_id: str, size: str = "medium") -> Document:
        """Generate a test document of specified size."""
        sizes = {
            "small": 100,      # 100 chars
            "medium": 1000,    # 1KB
            "large": 10000,    # 10KB
            "xlarge": 100000   # 100KB
        }
        
        content_size = sizes.get(size, 1000)
        content = ''.join(random.choices(string.ascii_letters + string.digits + ' \n', k=content_size))
        
        metadata = DocumentMetadata(
            tags=["test", "benchmark", size],
            category="benchmark",
            author="benchmark_suite",
            version="1.0.0",
            custom_fields={"size": size, "test_id": doc_id}
        )
        
        return Document(
            id=doc_id,
            title=f"Benchmark Document {doc_id}",
            content=content,
            content_type=ContentType.MARKDOWN,
            status=DocumentStatus.PUBLISHED,
            metadata=metadata
        )
    
    def benchmark_single_operations(self, storage: LocalStorageManager, num_docs: int = 100) -> Dict[str, Any]:
        """Benchmark single document operations."""
        print(f"  Running single operation benchmarks with {num_docs} documents...")
        
        # Create timing lists
        create_times = []
        read_times = []
        update_times = []
        delete_times = []
        
        # Create documents
        for i in range(num_docs):
            doc = self.generate_document(f"single-{i}", "medium")
            
            # Benchmark create
            start = time.perf_counter()
            created_doc = storage.create_document(doc)
            create_times.append(time.perf_counter() - start)
            
            # Benchmark read
            start = time.perf_counter()
            retrieved_doc = storage.get_document(created_doc.id)
            read_times.append(time.perf_counter() - start)
            
            # Benchmark update
            retrieved_doc.content += "\nUpdated content"
            start = time.perf_counter()
            updated_doc = storage.update_document(retrieved_doc)
            update_times.append(time.perf_counter() - start)
            
            # Benchmark delete (soft delete)
            start = time.perf_counter()
            storage.delete_document(created_doc.id, hard_delete=False)
            delete_times.append(time.perf_counter() - start)
        
        return {
            "create": {
                "avg_ms": statistics.mean(create_times) * 1000,
                "min_ms": min(create_times) * 1000,
                "max_ms": max(create_times) * 1000,
                "ops_per_sec": 1 / statistics.mean(create_times) if create_times else 0
            },
            "read": {
                "avg_ms": statistics.mean(read_times) * 1000,
                "min_ms": min(read_times) * 1000,
                "max_ms": max(read_times) * 1000,
                "ops_per_sec": 1 / statistics.mean(read_times) if read_times else 0
            },
            "update": {
                "avg_ms": statistics.mean(update_times) * 1000,
                "min_ms": min(update_times) * 1000,
                "max_ms": max(update_times) * 1000,
                "ops_per_sec": 1 / statistics.mean(update_times) if update_times else 0
            },
            "delete": {
                "avg_ms": statistics.mean(delete_times) * 1000,
                "min_ms": min(delete_times) * 1000,
                "max_ms": max(delete_times) * 1000,
                "ops_per_sec": 1 / statistics.mean(delete_times) if delete_times else 0
            }
        }
    
    def benchmark_batch_operations(self, storage: OptimizedLocalStorageManager, batch_size: int = 100) -> Dict[str, Any]:
        """Benchmark batch operations (optimized storage only)."""
        print(f"  Running batch operation benchmarks with batch size {batch_size}...")
        
        # Generate batch of documents
        docs = [self.generate_document(f"batch-{i}", "medium") for i in range(batch_size)]
        
        # Benchmark batch create
        start = time.perf_counter()
        created_docs = storage.create_documents_batch(docs)
        batch_create_time = time.perf_counter() - start
        
        # Benchmark batch read (list operation)
        start = time.perf_counter()
        retrieved_docs = storage.list_documents(limit=batch_size)
        batch_read_time = time.perf_counter() - start
        
        # Clean up
        for doc in created_docs:
            storage.delete_document(doc.id, hard_delete=True)
        
        return {
            "batch_create": {
                "total_time_ms": batch_create_time * 1000,
                "docs_per_sec": batch_size / batch_create_time if batch_create_time > 0 else 0,
                "avg_per_doc_ms": (batch_create_time / batch_size) * 1000
            },
            "batch_read": {
                "total_time_ms": batch_read_time * 1000,
                "docs_per_sec": batch_size / batch_read_time if batch_read_time > 0 else 0,
                "avg_per_doc_ms": (batch_read_time / batch_size) * 1000
            }
        }
    
    def benchmark_search_operations(self, storage: LocalStorageManager, num_docs: int = 50) -> Dict[str, Any]:
        """Benchmark search operations."""
        print(f"  Running search benchmarks with {num_docs} documents...")
        
        # Create searchable documents
        search_terms = ["API", "database", "authentication", "performance", "security"]
        for i in range(num_docs):
            term = random.choice(search_terms)
            doc = Document(
                id=f"search-{i}",
                title=f"Document about {term}",
                content=f"This document contains information about {term} and related topics. " * 10,
                content_type=ContentType.MARKDOWN
            )
            storage.create_document(doc)
        
        # Benchmark searches
        search_times = []
        for term in search_terms:
            start = time.perf_counter()
            results = storage.search_documents(term, limit=20)
            search_times.append(time.perf_counter() - start)
        
        # Benchmark metadata search
        metadata_search_times = []
        for _ in range(5):
            start = time.perf_counter()
            results = storage.search_by_metadata(category="benchmark", limit=20)
            metadata_search_times.append(time.perf_counter() - start)
        
        return {
            "full_text_search": {
                "avg_ms": statistics.mean(search_times) * 1000 if search_times else 0,
                "min_ms": min(search_times) * 1000 if search_times else 0,
                "max_ms": max(search_times) * 1000 if search_times else 0
            },
            "metadata_search": {
                "avg_ms": statistics.mean(metadata_search_times) * 1000 if metadata_search_times else 0,
                "min_ms": min(metadata_search_times) * 1000 if metadata_search_times else 0,
                "max_ms": max(metadata_search_times) * 1000 if metadata_search_times else 0
            }
        }
    
    def benchmark_cache_performance(self, storage: OptimizedLocalStorageManager, num_ops: int = 100) -> Dict[str, Any]:
        """Benchmark cache effectiveness."""
        print(f"  Running cache benchmarks with {num_ops} operations...")
        
        # Create a document
        doc = self.generate_document("cache-test", "large")
        created_doc = storage.create_document(doc)
        
        # First read (cache miss)
        start = time.perf_counter()
        storage.get_document(created_doc.id)
        first_read_time = time.perf_counter() - start
        
        # Subsequent reads (cache hits)
        cached_read_times = []
        for _ in range(num_ops):
            start = time.perf_counter()
            storage.get_document(created_doc.id)
            cached_read_times.append(time.perf_counter() - start)
        
        # Get cache stats
        cache_stats = storage.cache.get_stats()
        
        return {
            "first_read_ms": first_read_time * 1000,
            "cached_read_avg_ms": statistics.mean(cached_read_times) * 1000,
            "cache_speedup": first_read_time / statistics.mean(cached_read_times) if cached_read_times else 0,
            "cache_stats": cache_stats
        }
    
    def run_benchmarks(self) -> Dict[str, Any]:
        """Run all benchmarks for both baseline and optimized storage."""
        print("\n" + "="*60)
        print("M002 LOCAL STORAGE PERFORMANCE BENCHMARKS")
        print("="*60)
        
        results = {}
        
        # Test different memory modes
        memory_modes = [MemoryMode.BASELINE, MemoryMode.STANDARD, MemoryMode.ENHANCED, MemoryMode.PERFORMANCE]
        
        for mode in memory_modes:
            print(f"\nTesting Memory Mode: {mode.value}")
            print("-" * 40)
            
            # Create temp directory
            temp_dir = tempfile.mkdtemp()
            self.temp_dirs.append(temp_dir)
            db_path = Path(temp_dir) / "benchmark.db"
            
            # Configure for memory mode
            config = ConfigurationManager()
            config.set('memory_mode', mode)
            config.set('encryption_enabled', True)
            
            # Test baseline storage
            print("\n  Baseline Storage:")
            baseline_storage = LocalStorageManager(db_path=db_path, config=config)
            baseline_results = {
                "single_ops": self.benchmark_single_operations(baseline_storage, num_docs=50),
                "search": self.benchmark_search_operations(baseline_storage, num_docs=30)
            }
            baseline_storage.close()
            
            # Clean database for optimized test
            db_path.unlink()
            
            # Test optimized storage
            print("\n  Optimized Storage:")
            optimized_storage = OptimizedLocalStorageManager(db_path=db_path, config=config)
            optimized_results = {
                "single_ops": self.benchmark_single_operations(optimized_storage, num_docs=50),
                "batch_ops": self.benchmark_batch_operations(optimized_storage, batch_size=100),
                "search": self.benchmark_search_operations(optimized_storage, num_docs=30),
                "cache": self.benchmark_cache_performance(optimized_storage, num_ops=50)
            }
            
            # Get detailed performance metrics
            perf_metrics = optimized_storage.get_performance_metrics_detailed()
            optimized_results["metrics"] = perf_metrics
            
            optimized_storage.close()
            
            # Store results
            results[mode.value] = {
                "baseline": baseline_results,
                "optimized": optimized_results
            }
        
        return results
    
    def print_results(self, results: Dict[str, Any]):
        """Print benchmark results in a formatted table."""
        print("\n" + "="*60)
        print("BENCHMARK RESULTS SUMMARY")
        print("="*60)
        
        for mode, mode_results in results.items():
            print(f"\n{'='*60}")
            print(f"MEMORY MODE: {mode.upper()}")
            print(f"{'='*60}")
            
            baseline = mode_results["baseline"]
            optimized = mode_results["optimized"]
            
            # Single operations comparison
            print("\nSingle Operations (ops/sec):")
            print(f"{'Operation':<15} {'Baseline':>12} {'Optimized':>12} {'Improvement':>12}")
            print("-" * 52)
            
            for op in ["create", "read", "update", "delete"]:
                baseline_ops = baseline["single_ops"][op]["ops_per_sec"]
                optimized_ops = optimized["single_ops"][op]["ops_per_sec"]
                improvement = ((optimized_ops - baseline_ops) / baseline_ops * 100) if baseline_ops > 0 else 0
                print(f"{op.capitalize():<15} {baseline_ops:>12.1f} {optimized_ops:>12.1f} {improvement:>11.1f}%")
            
            # Batch operations (optimized only)
            if "batch_ops" in optimized:
                print("\nBatch Operations (optimized only):")
                print(f"  Batch Create: {optimized['batch_ops']['batch_create']['docs_per_sec']:.1f} docs/sec")
                print(f"  Batch Read:   {optimized['batch_ops']['batch_read']['docs_per_sec']:.1f} docs/sec")
            
            # Search performance
            print("\nSearch Performance (ms):")
            baseline_search = baseline["search"]["full_text_search"]["avg_ms"]
            optimized_search = optimized["search"]["full_text_search"]["avg_ms"]
            improvement = ((baseline_search - optimized_search) / baseline_search * 100) if baseline_search > 0 else 0
            print(f"  Baseline:  {baseline_search:.2f} ms")
            print(f"  Optimized: {optimized_search:.2f} ms")
            print(f"  Improvement: {improvement:.1f}%")
            
            # Cache performance (optimized only)
            if "cache" in optimized:
                cache = optimized["cache"]
                print("\nCache Performance:")
                print(f"  First Read:    {cache['first_read_ms']:.2f} ms")
                print(f"  Cached Read:   {cache['cached_read_avg_ms']:.2f} ms")
                print(f"  Cache Speedup: {cache['cache_speedup']:.1f}x")
                print(f"  Hit Rate:      {cache['cache_stats']['hit_rate']:.1f}%")
    
    def check_targets(self, results: Dict[str, Any]) -> bool:
        """Check if performance targets are met."""
        print("\n" + "="*60)
        print("PERFORMANCE TARGETS VALIDATION")
        print("="*60)
        
        # Get PERFORMANCE mode results (highest performance)
        perf_results = results.get("performance", {}).get("optimized", {})
        
        targets_met = []
        
        # Target: >1000 docs/sec for document operations
        doc_ops = perf_results.get("single_ops", {}).get("create", {}).get("ops_per_sec", 0)
        target_met = doc_ops > 1000
        targets_met.append(target_met)
        print(f"Document Operations: {doc_ops:.1f} ops/sec (Target: >1000) {'✅' if target_met else '❌'}")
        
        # Target: Sub-millisecond for indexed operations
        read_time = perf_results.get("single_ops", {}).get("read", {}).get("avg_ms", float('inf'))
        target_met = read_time < 1.0
        targets_met.append(target_met)
        print(f"Read Operations: {read_time:.2f} ms (Target: <1ms) {'✅' if target_met else '❌'}")
        
        # Target: >5000 docs/sec for batch operations
        batch_ops = perf_results.get("batch_ops", {}).get("batch_create", {}).get("docs_per_sec", 0)
        target_met = batch_ops > 5000
        targets_met.append(target_met)
        print(f"Batch Operations: {batch_ops:.1f} docs/sec (Target: >5000) {'✅' if target_met else '❌'}")
        
        # Target: <50ms for complex queries
        search_time = perf_results.get("search", {}).get("full_text_search", {}).get("avg_ms", float('inf'))
        target_met = search_time < 50
        targets_met.append(target_met)
        print(f"Search Operations: {search_time:.2f} ms (Target: <50ms) {'✅' if target_met else '❌'}")
        
        # Target: >90% cache hit rate
        cache_hit_rate = perf_results.get("cache", {}).get("cache_stats", {}).get("hit_rate", 0)
        target_met = cache_hit_rate > 90
        targets_met.append(target_met)
        print(f"Cache Hit Rate: {cache_hit_rate:.1f}% (Target: >90%) {'✅' if target_met else '❌'}")
        
        all_met = all(targets_met)
        print(f"\n{'✅ ALL TARGETS MET!' if all_met else '❌ Some targets not met'}")
        
        return all_met


if __name__ == "__main__":
    benchmark = StorageBenchmark()
    
    try:
        # Run benchmarks
        results = benchmark.run_benchmarks()
        
        # Print results
        benchmark.print_results(results)
        
        # Check targets
        targets_met = benchmark.check_targets(results)
        
        # Exit code based on targets
        exit(0 if targets_met else 1)
        
    finally:
        # Clean up
        benchmark.cleanup()