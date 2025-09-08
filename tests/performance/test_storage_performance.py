"""
Performance Test Suite for M002 Local Storage System
Pass 2: Performance Optimization
Target: 200,000+ queries/sec as per design documentation

Tests measure performance under various conditions:
- Single document operations
- Bulk operations
- Concurrent access
- Memory efficiency
- Cache performance
"""

import pytest
import tempfile
import time
import statistics
import threading
import multiprocessing
import os
import json
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import List, Dict, Any, Tuple
from pathlib import Path
import psutil
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from devdocai.core.storage import StorageManager, Document, DocumentMetadata
from devdocai.core.config import ConfigurationManager


class PerformanceMetrics:
    """Track and report performance metrics."""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
        self.end_time = None
        self.operations = []
        self.memory_start = None
        self.memory_end = None
    
    def start(self):
        """Start timing and memory tracking."""
        self.start_time = time.perf_counter()
        process = psutil.Process()
        self.memory_start = process.memory_info().rss / 1024 / 1024  # MB
    
    def end(self):
        """End timing and memory tracking."""
        self.end_time = time.perf_counter()
        process = psutil.Process()
        self.memory_end = process.memory_info().rss / 1024 / 1024  # MB
    
    def record_operation(self, duration: float):
        """Record individual operation duration."""
        self.operations.append(duration)
    
    def get_stats(self) -> Dict[str, Any]:
        """Calculate and return statistics."""
        if not self.operations:
            return {}
        
        total_time = self.end_time - self.start_time
        ops_per_sec = len(self.operations) / total_time if total_time > 0 else 0
        
        return {
            "operation": self.operation_name,
            "total_operations": len(self.operations),
            "total_time": total_time,
            "ops_per_second": ops_per_sec,
            "avg_latency_ms": statistics.mean(self.operations) * 1000,
            "median_latency_ms": statistics.median(self.operations) * 1000,
            "p95_latency_ms": statistics.quantiles(self.operations, n=20)[18] * 1000 if len(self.operations) > 20 else 0,
            "p99_latency_ms": statistics.quantiles(self.operations, n=100)[98] * 1000 if len(self.operations) > 100 else 0,
            "memory_used_mb": self.memory_end - self.memory_start if self.memory_end and self.memory_start else 0
        }
    
    def print_report(self):
        """Print formatted performance report."""
        stats = self.get_stats()
        if not stats:
            print(f"No operations recorded for {self.operation_name}")
            return
        
        print(f"\n{'='*60}")
        print(f"Performance Report: {stats['operation']}")
        print(f"{'='*60}")
        print(f"Total Operations: {stats['total_operations']:,}")
        print(f"Total Time: {stats['total_time']:.2f} seconds")
        print(f"Operations/Second: {stats['ops_per_second']:,.0f}")
        print(f"Average Latency: {stats['avg_latency_ms']:.3f} ms")
        print(f"Median Latency: {stats['median_latency_ms']:.3f} ms")
        print(f"P95 Latency: {stats['p95_latency_ms']:.3f} ms")
        print(f"P99 Latency: {stats['p99_latency_ms']:.3f} ms")
        print(f"Memory Used: {stats['memory_used_mb']:.2f} MB")
        print(f"{'='*60}")
        
        # Check against target
        target = 200_000
        if stats['ops_per_second'] >= target:
            print(f"✅ PASSED: Achieved {stats['ops_per_second']:,.0f} ops/sec (target: {target:,})")
        else:
            print(f"❌ FAILED: Only {stats['ops_per_second']:,.0f} ops/sec (target: {target:,})")


class TestStoragePerformance:
    """Performance test suite for StorageManager."""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    @pytest.fixture
    def storage_manager(self, temp_db_path):
        """Create StorageManager instance."""
        config = ConfigurationManager()
        config.config = {
            "storage": {
                "database_path": temp_db_path,
                "encryption_enabled": True,
                "encryption_key": "test_key_for_performance"
            }
        }
        return StorageManager(config)
    
    @pytest.fixture
    def in_memory_storage(self):
        """Create in-memory StorageManager for max performance testing."""
        config = ConfigurationManager()
        config.config = {
            "storage": {
                "database_path": ":memory:",
                "encryption_enabled": False  # Disable encryption for baseline
            }
        }
        return StorageManager(config)
    
    def generate_document(self, doc_id: int, size: str = "small") -> Document:
        """Generate test document of specified size."""
        content_sizes = {
            "small": "x" * 100,  # 100 bytes
            "medium": "x" * 1000,  # 1KB
            "large": "x" * 10000,  # 10KB
            "xlarge": "x" * 100000  # 100KB
        }
        
        return Document(
            id=f"doc_{doc_id:06d}",
            content=content_sizes.get(size, content_sizes["small"]),
            type="test",
            metadata={
                "author": f"author_{doc_id % 10}",
                "tags": [f"tag_{doc_id % 5}", f"tag_{doc_id % 3}"],
                "size": size
            }
        )
    
    def test_baseline_write_performance(self, in_memory_storage):
        """Test baseline write performance without encryption."""
        storage = in_memory_storage
        metrics = PerformanceMetrics("Baseline Write (No Encryption)")
        
        num_docs = 10000
        metrics.start()
        
        for i in range(num_docs):
            doc = self.generate_document(i)
            
            op_start = time.perf_counter()
            storage.save_document(doc)
            op_end = time.perf_counter()
            
            metrics.record_operation(op_end - op_start)
        
        metrics.end()
        metrics.print_report()
        
        # Assert minimum performance
        stats = metrics.get_stats()
        assert stats['ops_per_second'] > 1000, f"Baseline write too slow: {stats['ops_per_second']:.0f} ops/sec"
    
    def test_baseline_read_performance(self, in_memory_storage):
        """Test baseline read performance without encryption."""
        storage = in_memory_storage
        
        # Prepare data
        num_docs = 10000
        for i in range(num_docs):
            doc = self.generate_document(i)
            storage.save_document(doc)
        
        metrics = PerformanceMetrics("Baseline Read (No Encryption)")
        metrics.start()
        
        for i in range(num_docs):
            doc_id = f"doc_{i:06d}"
            
            op_start = time.perf_counter()
            doc = storage.get_document(doc_id)
            op_end = time.perf_counter()
            
            metrics.record_operation(op_end - op_start)
            assert doc is not None
        
        metrics.end()
        metrics.print_report()
        
        # Check if we're close to target
        stats = metrics.get_stats()
        print(f"\n📊 Baseline read performance: {stats['ops_per_second']:,.0f} ops/sec")
        print(f"   Distance to target: {200_000 - stats['ops_per_second']:,.0f} ops/sec")
    
    def test_encrypted_write_performance(self, storage_manager):
        """Test write performance with encryption enabled."""
        storage = storage_manager
        metrics = PerformanceMetrics("Encrypted Write")
        
        num_docs = 1000
        metrics.start()
        
        for i in range(num_docs):
            doc = self.generate_document(i)
            
            op_start = time.perf_counter()
            storage.save_document(doc)
            op_end = time.perf_counter()
            
            metrics.record_operation(op_end - op_start)
        
        metrics.end()
        metrics.print_report()
        
        stats = metrics.get_stats()
        assert stats['ops_per_second'] > 100, f"Encrypted write too slow: {stats['ops_per_second']:.0f} ops/sec"
    
    def test_encrypted_read_performance(self, storage_manager):
        """Test read performance with encryption enabled."""
        storage = storage_manager
        
        # Prepare data
        num_docs = 1000
        for i in range(num_docs):
            doc = self.generate_document(i)
            storage.save_document(doc)
        
        metrics = PerformanceMetrics("Encrypted Read")
        metrics.start()
        
        for i in range(num_docs):
            doc_id = f"doc_{i:06d}"
            
            op_start = time.perf_counter()
            doc = storage.get_document(doc_id)
            op_end = time.perf_counter()
            
            metrics.record_operation(op_end - op_start)
            assert doc is not None
        
        metrics.end()
        metrics.print_report()
        
        stats = metrics.get_stats()
        assert stats['ops_per_second'] > 100, f"Encrypted read too slow: {stats['ops_per_second']:.0f} ops/sec"
    
    def test_bulk_write_performance(self, storage_manager):
        """Test bulk write operations performance."""
        storage = storage_manager
        metrics = PerformanceMetrics("Bulk Write (100 docs/batch)")
        
        num_batches = 10
        batch_size = 100
        
        metrics.start()
        
        for batch in range(num_batches):
            docs = [self.generate_document(batch * batch_size + i) for i in range(batch_size)]
            
            op_start = time.perf_counter()
            results = storage.bulk_save(docs)
            op_end = time.perf_counter()
            
            # Record each document as an operation
            for _ in range(batch_size):
                metrics.record_operation((op_end - op_start) / batch_size)
            
            assert all(results.values()), "Some documents failed to save"
        
        metrics.end()
        metrics.print_report()
    
    def test_concurrent_read_performance(self, storage_manager):
        """Test concurrent read operations."""
        storage = storage_manager
        
        # Prepare data
        num_docs = 1000
        for i in range(num_docs):
            doc = self.generate_document(i)
            storage.save_document(doc)
        
        metrics = PerformanceMetrics("Concurrent Read (10 threads)")
        
        def read_documents(start_idx, count):
            """Read documents in a thread."""
            timings = []
            for i in range(start_idx, start_idx + count):
                doc_id = f"doc_{i:06d}"
                
                op_start = time.perf_counter()
                doc = storage.get_document(doc_id)
                op_end = time.perf_counter()
                
                timings.append(op_end - op_start)
                assert doc is not None
            return timings
        
        metrics.start()
        
        # Use ThreadPoolExecutor for concurrent reads
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            docs_per_thread = 100
            
            for i in range(10):
                future = executor.submit(read_documents, i * docs_per_thread, docs_per_thread)
                futures.append(future)
            
            # Collect all timings
            for future in futures:
                timings = future.result()
                for timing in timings:
                    metrics.record_operation(timing)
        
        metrics.end()
        metrics.print_report()
    
    def test_mixed_workload_performance(self, storage_manager):
        """Test mixed read/write workload performance."""
        storage = storage_manager
        metrics = PerformanceMetrics("Mixed Workload (70% read, 30% write)")
        
        total_ops = 1000
        read_ratio = 0.7
        
        # Pre-populate some documents
        for i in range(500):
            doc = self.generate_document(i)
            storage.save_document(doc)
        
        metrics.start()
        
        import random
        next_doc_id = 500
        
        for _ in range(total_ops):
            if random.random() < read_ratio:
                # Read operation
                doc_id = f"doc_{random.randint(0, next_doc_id-1):06d}"
                
                op_start = time.perf_counter()
                doc = storage.get_document(doc_id)
                op_end = time.perf_counter()
            else:
                # Write operation
                doc = self.generate_document(next_doc_id)
                next_doc_id += 1
                
                op_start = time.perf_counter()
                storage.save_document(doc)
                op_end = time.perf_counter()
            
            metrics.record_operation(op_end - op_start)
        
        metrics.end()
        metrics.print_report()
    
    def test_document_size_impact(self, storage_manager):
        """Test performance impact of different document sizes."""
        storage = storage_manager
        
        sizes = ["small", "medium", "large", "xlarge"]
        
        for size in sizes:
            metrics = PerformanceMetrics(f"Document Size: {size}")
            num_docs = 100 if size != "xlarge" else 10
            
            metrics.start()
            
            for i in range(num_docs):
                doc = self.generate_document(i + 1000 * sizes.index(size), size)
                
                op_start = time.perf_counter()
                storage.save_document(doc)
                op_end = time.perf_counter()
                
                metrics.record_operation(op_end - op_start)
            
            metrics.end()
            metrics.print_report()
    
    def test_query_performance(self, storage_manager):
        """Test query and search performance."""
        storage = storage_manager
        
        # Prepare diverse data
        num_docs = 1000
        for i in range(num_docs):
            doc = self.generate_document(i)
            storage.save_document(doc)
        
        # Test different query types
        query_tests = [
            ("Document Exists Check", lambda i: storage.document_exists(f"doc_{i:06d}")),
            ("Search by Type", lambda i: storage.search_by_type("test")),
            ("Search by Author", lambda i: storage.search_by_metadata({"author": f"author_{i % 10}"})),
            ("Search by Tags", lambda i: storage.search_by_metadata({"tags": f"tag_{i % 5}"}))
        ]
        
        for query_name, query_func in query_tests:
            metrics = PerformanceMetrics(query_name)
            num_queries = 100
            
            metrics.start()
            
            for i in range(num_queries):
                op_start = time.perf_counter()
                result = query_func(i)
                op_end = time.perf_counter()
                
                metrics.record_operation(op_end - op_start)
            
            metrics.end()
            metrics.print_report()
    
    def test_transaction_performance(self, storage_manager):
        """Test transaction overhead and performance."""
        storage = storage_manager
        
        # Test without transactions
        metrics_no_tx = PerformanceMetrics("No Transaction (100 docs)")
        metrics_no_tx.start()
        
        for i in range(100):
            doc = self.generate_document(i + 10000)
            op_start = time.perf_counter()
            storage.save_document(doc)
            op_end = time.perf_counter()
            metrics_no_tx.record_operation(op_end - op_start)
        
        metrics_no_tx.end()
        metrics_no_tx.print_report()
        
        # Test with transaction
        metrics_tx = PerformanceMetrics("With Transaction (100 docs)")
        metrics_tx.start()
        
        with storage.transaction():
            for i in range(100):
                doc = self.generate_document(i + 20000)
                op_start = time.perf_counter()
                storage.save_document(doc)
                op_end = time.perf_counter()
                metrics_tx.record_operation(op_end - op_start)
        
        metrics_tx.end()
        metrics_tx.print_report()
        
        # Compare performance
        stats_no_tx = metrics_no_tx.get_stats()
        stats_tx = metrics_tx.get_stats()
        
        print(f"\n📊 Transaction Performance Comparison:")
        print(f"   Without Transaction: {stats_no_tx['ops_per_second']:,.0f} ops/sec")
        print(f"   With Transaction: {stats_tx['ops_per_second']:,.0f} ops/sec")
        print(f"   Speedup: {stats_tx['ops_per_second'] / stats_no_tx['ops_per_second']:.2f}x")


def run_performance_suite():
    """Run the complete performance test suite."""
    print("\n" + "="*80)
    print("M002 LOCAL STORAGE SYSTEM - PERFORMANCE TEST SUITE")
    print("Pass 2: Performance Optimization")
    print("Target: 200,000+ queries/sec")
    print("="*80)
    
    # Run pytest with performance tests
    import subprocess
    result = subprocess.run(
        ["python", "-m", "pytest", __file__, "-v", "-s"],
        capture_output=False,
        text=True
    )
    
    return result.returncode == 0


if __name__ == "__main__":
    success = run_performance_suite()
    exit(0 if success else 1)