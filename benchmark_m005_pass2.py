#!/usr/bin/env python3
"""
M005 Tracking Matrix - Pass 2 Performance Benchmarking
DevDocAI v3.0.0

This script benchmarks the current performance and identifies bottlenecks
for the Pass 2 performance optimization phase.
"""

import sys
import time
import random
import json
import psutil
import tracemalloc
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from devdocai.core.config import ConfigurationManager
from devdocai.core.storage import StorageManager
from devdocai.core.tracking import TrackingMatrix, RelationshipType


@dataclass
class BenchmarkResult:
    """Result of a benchmark test."""
    operation: str
    document_count: int
    relationship_count: int
    execution_time: float
    operations_per_second: float
    memory_used_mb: float
    success: bool
    notes: str = ""


class TrackingMatrixBenchmark:
    """Comprehensive benchmarking for M005 Tracking Matrix."""
    
    def __init__(self):
        """Initialize benchmark environment."""
        self.config = ConfigurationManager()
        self.storage = StorageManager(self.config)
        self.results: List[BenchmarkResult] = []
        
    def setup_test_matrix(self, num_docs: int, relationship_density: float = 0.1) -> TrackingMatrix:
        """Create a test matrix with specified number of documents and relationships."""
        matrix = TrackingMatrix(self.config, self.storage)
        
        # Add documents
        for i in range(num_docs):
            matrix.add_document(f"doc_{i}", {
                "title": f"Document {i}",
                "complexity": random.randint(1, 5),
                "size": random.randint(50, 500)
            })
        
        # Add relationships based on density
        num_relationships = int(num_docs * num_docs * relationship_density)
        added = 0
        attempts = 0
        max_attempts = num_relationships * 10
        
        while added < num_relationships and attempts < max_attempts:
            attempts += 1
            source = f"doc_{random.randint(0, num_docs-1)}"
            target = f"doc_{random.randint(0, num_docs-1)}"
            
            if source != target and not matrix.has_relationship(source, target):
                try:
                    rel_type = random.choice(list(RelationshipType))
                    matrix.add_relationship(source, target, rel_type, 
                                          strength=random.random(),
                                          metadata={"test": True})
                    added += 1
                except:
                    # Skip if would create cycle
                    pass
        
        return matrix
    
    def benchmark_document_addition(self, doc_counts: List[int]) -> None:
        """Benchmark document addition performance."""
        print("\n📊 Benchmarking Document Addition...")
        
        for count in doc_counts:
            tracemalloc.start()
            matrix = TrackingMatrix(self.config, self.storage)
            
            start_time = time.time()
            for i in range(count):
                matrix.add_document(f"doc_{i}", {"index": i})
            
            elapsed = time.time() - start_time
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            ops_per_sec = count / elapsed if elapsed > 0 else 0
            memory_mb = peak / 1024 / 1024
            
            result = BenchmarkResult(
                operation="document_addition",
                document_count=count,
                relationship_count=0,
                execution_time=elapsed,
                operations_per_second=ops_per_sec,
                memory_used_mb=memory_mb,
                success=True
            )
            self.results.append(result)
            
            print(f"  ✅ {count:,} docs: {elapsed:.3f}s ({ops_per_sec:,.0f} ops/s, {memory_mb:.1f}MB)")
    
    def benchmark_relationship_creation(self, doc_counts: List[int]) -> None:
        """Benchmark relationship creation performance."""
        print("\n📊 Benchmarking Relationship Creation...")
        
        for count in doc_counts:
            matrix = self.setup_test_matrix(count, 0)  # No initial relationships
            
            # Create relationships in a chain pattern
            tracemalloc.start()
            start_time = time.time()
            
            relationships_added = 0
            for i in range(count - 1):
                try:
                    matrix.add_relationship(f"doc_{i}", f"doc_{i+1}", 
                                          RelationshipType.DEPENDS_ON)
                    relationships_added += 1
                except:
                    pass
            
            elapsed = time.time() - start_time
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            ops_per_sec = relationships_added / elapsed if elapsed > 0 else 0
            memory_mb = peak / 1024 / 1024
            
            result = BenchmarkResult(
                operation="relationship_creation",
                document_count=count,
                relationship_count=relationships_added,
                execution_time=elapsed,
                operations_per_second=ops_per_sec,
                memory_used_mb=memory_mb,
                success=True
            )
            self.results.append(result)
            
            print(f"  ✅ {relationships_added:,} relationships: {elapsed:.3f}s ({ops_per_sec:,.0f} ops/s, {memory_mb:.1f}MB)")
    
    def benchmark_impact_analysis(self, doc_counts: List[int]) -> None:
        """Benchmark impact analysis performance."""
        print("\n📊 Benchmarking Impact Analysis...")
        
        for count in doc_counts:
            # Create a more complex graph for impact analysis
            matrix = self.setup_test_matrix(count, 0.05)  # 5% density
            
            # Select random documents for impact analysis
            test_docs = random.sample([f"doc_{i}" for i in range(count)], min(10, count))
            
            tracemalloc.start()
            total_time = 0
            
            for doc_id in test_docs:
                start_time = time.time()
                impact = matrix.analyze_impact(doc_id, max_depth=5)
                elapsed = time.time() - start_time
                total_time += elapsed
            
            avg_time = total_time / len(test_docs)
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            memory_mb = peak / 1024 / 1024
            
            result = BenchmarkResult(
                operation="impact_analysis",
                document_count=count,
                relationship_count=len(matrix.get_all_relationships()),
                execution_time=avg_time,
                operations_per_second=1/avg_time if avg_time > 0 else 0,
                memory_used_mb=memory_mb,
                success=True,
                notes=f"Avg of {len(test_docs)} analyses"
            )
            self.results.append(result)
            
            print(f"  ✅ {count:,} docs: {avg_time:.3f}s avg ({memory_mb:.1f}MB)")
    
    def benchmark_consistency_analysis(self, doc_counts: List[int]) -> None:
        """Benchmark consistency analysis performance."""
        print("\n📊 Benchmarking Consistency Analysis...")
        
        for count in doc_counts:
            matrix = self.setup_test_matrix(count, 0.05)
            
            tracemalloc.start()
            start_time = time.time()
            report = matrix.analyze_suite_consistency()
            elapsed = time.time() - start_time
            
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            memory_mb = peak / 1024 / 1024
            
            result = BenchmarkResult(
                operation="consistency_analysis",
                document_count=count,
                relationship_count=len(matrix.get_all_relationships()),
                execution_time=elapsed,
                operations_per_second=count/elapsed if elapsed > 0 else 0,
                memory_used_mb=memory_mb,
                success=True
            )
            self.results.append(result)
            
            print(f"  ✅ {count:,} docs: {elapsed:.3f}s ({memory_mb:.1f}MB)")
    
    def benchmark_json_export(self, doc_counts: List[int]) -> None:
        """Benchmark JSON export performance."""
        print("\n📊 Benchmarking JSON Export...")
        
        for count in doc_counts:
            matrix = self.setup_test_matrix(count, 0.05)
            
            tracemalloc.start()
            start_time = time.time()
            json_data = matrix.export_to_json()
            elapsed = time.time() - start_time
            
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            memory_mb = peak / 1024 / 1024
            json_size_mb = len(json_data) / 1024 / 1024
            
            result = BenchmarkResult(
                operation="json_export",
                document_count=count,
                relationship_count=len(matrix.get_all_relationships()),
                execution_time=elapsed,
                operations_per_second=count/elapsed if elapsed > 0 else 0,
                memory_used_mb=memory_mb,
                success=True,
                notes=f"JSON size: {json_size_mb:.2f}MB"
            )
            self.results.append(result)
            
            print(f"  ✅ {count:,} docs: {elapsed:.3f}s ({json_size_mb:.2f}MB JSON, {memory_mb:.1f}MB RAM)")
    
    def benchmark_topological_sort(self, doc_counts: List[int]) -> None:
        """Benchmark topological sort performance."""
        print("\n📊 Benchmarking Topological Sort...")
        
        for count in doc_counts:
            matrix = TrackingMatrix(self.config, self.storage)
            
            # Create a DAG (chain pattern to avoid cycles)
            for i in range(count):
                matrix.add_document(f"doc_{i}")
            
            for i in range(count - 1):
                matrix.add_relationship(f"doc_{i}", f"doc_{i+1}", 
                                      RelationshipType.DEPENDS_ON)
            
            tracemalloc.start()
            start_time = time.time()
            sorted_docs = matrix.graph.topological_sort()
            elapsed = time.time() - start_time
            
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            memory_mb = peak / 1024 / 1024
            
            result = BenchmarkResult(
                operation="topological_sort",
                document_count=count,
                relationship_count=count - 1,
                execution_time=elapsed,
                operations_per_second=count/elapsed if elapsed > 0 else 0,
                memory_used_mb=memory_mb,
                success=True
            )
            self.results.append(result)
            
            print(f"  ✅ {count:,} nodes: {elapsed:.3f}s ({memory_mb:.1f}MB)")
    
    def print_summary(self):
        """Print summary of benchmark results."""
        print("\n" + "="*60)
        print("📈 BENCHMARK SUMMARY")
        print("="*60)
        
        # Group results by operation
        by_operation = defaultdict(list)
        for result in self.results:
            by_operation[result.operation].append(result)
        
        for operation, results in by_operation.items():
            print(f"\n{operation.upper().replace('_', ' ')}:")
            print("-" * 40)
            
            for r in results:
                status = "✅" if r.success else "❌"
                print(f"{status} {r.document_count:,} docs: {r.execution_time:.3f}s "
                      f"({r.operations_per_second:,.0f} ops/s, {r.memory_used_mb:.1f}MB)")
                if r.notes:
                    print(f"   Note: {r.notes}")
        
        # Performance targets check
        print("\n" + "="*60)
        print("🎯 PASS 2 TARGET VALIDATION")
        print("="*60)
        
        # Check 10K document handling
        large_tests = [r for r in self.results if r.document_count >= 10000]
        if large_tests:
            print("\n✅ 10,000+ Document Handling:")
            for r in large_tests:
                print(f"  - {r.operation}: {r.execution_time:.3f}s")
        else:
            print("\n⚠️ No 10,000+ document tests performed")
        
        # Check <1s analysis for complex graphs
        impact_results = [r for r in self.results 
                         if r.operation == "impact_analysis" and r.document_count >= 1000]
        if impact_results:
            avg_time = sum(r.execution_time for r in impact_results) / len(impact_results)
            status = "✅" if avg_time < 1.0 else "❌"
            print(f"\n{status} Complex Graph Analysis: {avg_time:.3f}s (target: <1s)")
        
        # Check memory usage
        max_memory = max((r.memory_used_mb for r in self.results if r.document_count >= 10000), 
                        default=0)
        if max_memory > 0:
            status = "✅" if max_memory < 50 else "❌"
            print(f"{status} Memory Usage (10K docs): {max_memory:.1f}MB (target: <50MB)")


def main():
    """Run comprehensive benchmarks."""
    print("🚀 M005 Tracking Matrix - Pass 2 Performance Benchmarking")
    print("=" * 60)
    
    benchmark = TrackingMatrixBenchmark()
    
    # Test with increasing document counts
    small_counts = [10, 100, 500, 1000]
    large_counts = [5000, 10000]
    
    # Run benchmarks
    benchmark.benchmark_document_addition(small_counts + large_counts)
    benchmark.benchmark_relationship_creation(small_counts + large_counts)
    benchmark.benchmark_impact_analysis(small_counts)  # Skip large for now
    benchmark.benchmark_consistency_analysis(small_counts)
    benchmark.benchmark_json_export(small_counts)
    benchmark.benchmark_topological_sort(small_counts + large_counts)
    
    # Print summary
    benchmark.print_summary()
    
    print("\n✅ Benchmarking complete!")
    print("\nNext steps for Pass 2 optimization:")
    print("1. Implement NetworkX for advanced graph algorithms")
    print("2. Add parallel processing for impact analysis")
    print("3. Implement incremental analysis to avoid full recalculation")
    print("4. Add memory-mapped storage for large graphs")
    print("5. Optimize batch operations for bulk updates")
    print("6. Add query optimization with indexing")
    print("7. Enhance caching beyond current LRU implementation")


if __name__ == "__main__":
    main()