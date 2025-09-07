#!/usr/bin/env python3
"""
M003 MIAIR Engine Performance Benchmarking Tool

Measures performance across different document sizes and operations.
Validates against performance targets:
- Small documents (<1KB): <100ms
- Medium documents (1-10KB): <500ms  
- Large documents (>10KB): <1000ms
- Batch processing: 100,000+ documents/hour (361K+ docs/min target)
- Memory efficiency: <50MB per 1000 documents
"""

import os
import sys
import time
import json
import random
import string
import psutil
import asyncio
import statistics
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, asdict

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from devdocai.miair.engine_unified import MIAIREngineUnified
from devdocai.miair.models import Document, DocumentType, OperationMode


@dataclass
class BenchmarkResult:
    """Stores benchmark results for a single test."""
    operation: str
    document_size: str
    document_count: int
    total_time: float
    avg_time: float
    min_time: float
    max_time: float
    std_dev: float
    throughput: float  # docs/sec
    memory_used: float  # MB
    passed: bool
    target_time: float


class DocumentGenerator:
    """Generates test documents of various sizes and complexities."""
    
    LOREM_IPSUM = """Lorem ipsum dolor sit amet, consectetur adipiscing elit. 
    Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. 
    Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris."""
    
    CODE_SAMPLE = """
    def calculate_entropy(data: List[float]) -> float:
        '''Calculate Shannon entropy of data distribution.'''
        if not data:
            return 0.0
        total = sum(data)
        probabilities = [x / total for x in data if x > 0]
        return -sum(p * math.log2(p) for p in probabilities)
    """
    
    MARKDOWN_SAMPLE = """
    # Documentation Title
    
    ## Introduction
    This is a sample documentation with **bold** and *italic* text.
    
    ### Features
    - Feature 1: Description
    - Feature 2: Description
    
    ```python
    # Code example
    print("Hello, World!")
    ```
    """
    
    @classmethod
    def generate_document(cls, size_bytes: int, doc_type: str = "mixed") -> str:
        """Generate a document of approximately the specified size."""
        content_generators = {
            "text": cls.LOREM_IPSUM,
            "code": cls.CODE_SAMPLE,
            "markdown": cls.MARKDOWN_SAMPLE,
            "mixed": cls.LOREM_IPSUM + cls.CODE_SAMPLE + cls.MARKDOWN_SAMPLE
        }
        
        base_content = content_generators.get(doc_type, content_generators["mixed"])
        
        # Repeat content to reach target size
        result = []
        current_size = 0
        while current_size < size_bytes:
            result.append(base_content)
            current_size += len(base_content)
        
        return ''.join(result)[:size_bytes]
    
    @classmethod
    def generate_batch(cls, count: int, size_bytes: int) -> List[Document]:
        """Generate a batch of test documents."""
        docs = []
        for i in range(count):
            content = cls.generate_document(size_bytes)
            doc = Document(
                id=f"bench_{i}",
                content=content,
                type=DocumentType.GENERAL
            )
            docs.append(doc)
        return docs


class MIAIRBenchmark:
    """Performance benchmarking suite for M003 MIAIR Engine."""
    
    # Performance targets (in seconds)
    TARGETS = {
        "small": 0.100,    # 100ms for <1KB
        "medium": 0.500,   # 500ms for 1-10KB  
        "large": 1.000,    # 1000ms for >10KB
        "batch_throughput": 1667,  # 100K docs/hour = 1667 docs/min minimum
        "target_throughput": 6016  # 361K docs/min target (from specs)
    }
    
    # Document size definitions
    SIZES = {
        "small": 512,       # 512 bytes
        "medium": 5 * 1024, # 5 KB
        "large": 20 * 1024, # 20 KB
        "huge": 100 * 1024  # 100 KB (stress test)
    }
    
    def __init__(self, mode: OperationMode = OperationMode.BASIC):
        """Initialize benchmark suite."""
        self.mode = mode
        self.engine = MIAIREngineUnified(mode=mode)
        self.results: List[BenchmarkResult] = []
        self.doc_generator = DocumentGenerator()
        
    def measure_memory(self) -> float:
        """Measure current memory usage in MB."""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    
    def benchmark_single_document(
        self, 
        doc: Document, 
        size_name: str,
        iterations: int = 10
    ) -> BenchmarkResult:
        """Benchmark single document processing."""
        times = []
        memory_start = self.measure_memory()
        
        # Warmup
        self.engine.analyze(doc)
        
        # Actual benchmark
        for _ in range(iterations):
            start = time.perf_counter()
            result = self.engine.analyze(doc)
            end = time.perf_counter()
            times.append(end - start)
        
        memory_end = self.measure_memory()
        memory_used = memory_end - memory_start
        
        avg_time = statistics.mean(times)
        target_time = self.TARGETS.get(size_name, 1.0)
        
        return BenchmarkResult(
            operation="analyze",
            document_size=size_name,
            document_count=1,
            total_time=sum(times),
            avg_time=avg_time,
            min_time=min(times),
            max_time=max(times),
            std_dev=statistics.stdev(times) if len(times) > 1 else 0,
            throughput=1 / avg_time if avg_time > 0 else 0,
            memory_used=memory_used,
            passed=avg_time <= target_time,
            target_time=target_time
        )
    
    def benchmark_batch_processing(
        self, 
        batch_size: int = 100
    ) -> BenchmarkResult:
        """Benchmark batch document processing."""
        # Generate batch of medium-sized documents
        docs = self.doc_generator.generate_batch(batch_size, self.SIZES["medium"])
        
        memory_start = self.measure_memory()
        start = time.perf_counter()
        
        # Process batch
        results = []
        for doc in docs:
            result = self.engine.analyze(doc)
            results.append(result)
        
        end = time.perf_counter()
        memory_end = self.measure_memory()
        
        total_time = end - start
        avg_time = total_time / batch_size
        throughput = batch_size / total_time if total_time > 0 else 0
        docs_per_minute = throughput * 60
        memory_used = memory_end - memory_start
        
        return BenchmarkResult(
            operation="batch_analyze",
            document_size="medium",
            document_count=batch_size,
            total_time=total_time,
            avg_time=avg_time,
            min_time=avg_time,
            max_time=avg_time,
            std_dev=0,
            throughput=throughput,
            memory_used=memory_used,
            passed=docs_per_minute >= self.TARGETS["batch_throughput"],
            target_time=self.TARGETS["batch_throughput"] / 60  # Convert to docs/sec
        )
    
    async def benchmark_async_batch(
        self, 
        batch_size: int = 100
    ) -> BenchmarkResult:
        """Benchmark asynchronous batch processing (if implemented)."""
        # Generate batch
        docs = self.doc_generator.generate_batch(batch_size, self.SIZES["medium"])
        
        memory_start = self.measure_memory()
        start = time.perf_counter()
        
        # Try async processing if available
        try:
            if hasattr(self.engine, 'analyze_batch_async'):
                results = await self.engine.analyze_batch_async(docs)
            else:
                # Fallback to sync
                results = [self.engine.analyze(doc) for doc in docs]
        except Exception as e:
            print(f"Async processing not available: {e}")
            results = [self.engine.analyze(doc) for doc in docs]
        
        end = time.perf_counter()
        memory_end = self.measure_memory()
        
        total_time = end - start
        avg_time = total_time / batch_size
        throughput = batch_size / total_time if total_time > 0 else 0
        docs_per_minute = throughput * 60
        memory_used = memory_end - memory_start
        
        return BenchmarkResult(
            operation="async_batch",
            document_size="medium",
            document_count=batch_size,
            total_time=total_time,
            avg_time=avg_time,
            min_time=avg_time,
            max_time=avg_time,
            std_dev=0,
            throughput=throughput,
            memory_used=memory_used,
            passed=docs_per_minute >= self.TARGETS["target_throughput"],
            target_time=self.TARGETS["target_throughput"] / 60
        )
    
    def run_all_benchmarks(self) -> List[BenchmarkResult]:
        """Run complete benchmark suite."""
        print("\n" + "="*80)
        print("M003 MIAIR ENGINE PERFORMANCE BENCHMARK")
        print(f"Operation Mode: {self.mode.value}")
        print(f"Started: {datetime.now().isoformat()}")
        print("="*80 + "\n")
        
        results = []
        
        # 1. Single document benchmarks
        print("1. SINGLE DOCUMENT ANALYSIS")
        print("-" * 40)
        
        for size_name, size_bytes in self.SIZES.items():
            print(f"Testing {size_name} documents ({size_bytes} bytes)...", end=" ")
            doc = Document(
                id=f"bench_{size_name}",
                content=self.doc_generator.generate_document(size_bytes),
                type=DocumentType.GENERAL
            )
            result = self.benchmark_single_document(doc, size_name)
            results.append(result)
            
            status = "✓ PASS" if result.passed else "✗ FAIL"
            print(f"{status} ({result.avg_time*1000:.2f}ms avg, target: {result.target_time*1000:.0f}ms)")
        
        # 2. Batch processing benchmark
        print("\n2. BATCH PROCESSING")
        print("-" * 40)
        
        for batch_size in [100, 500, 1000]:
            print(f"Testing batch of {batch_size} documents...", end=" ")
            result = self.benchmark_batch_processing(batch_size)
            results.append(result)
            
            docs_per_min = result.throughput * 60
            status = "✓ PASS" if result.passed else "✗ FAIL"
            print(f"{status} ({docs_per_min:.0f} docs/min, target: {self.TARGETS['batch_throughput']} docs/min)")
        
        # 3. Memory efficiency test
        print("\n3. MEMORY EFFICIENCY")
        print("-" * 40)
        
        print("Testing memory usage for 1000 documents...", end=" ")
        memory_start = self.measure_memory()
        docs = self.doc_generator.generate_batch(1000, self.SIZES["small"])
        for doc in docs:
            self.engine.analyze(doc)
        memory_end = self.measure_memory()
        memory_per_1000 = memory_end - memory_start
        
        memory_passed = memory_per_1000 < 50  # <50MB per 1000 docs
        status = "✓ PASS" if memory_passed else "✗ FAIL"
        print(f"{status} ({memory_per_1000:.2f}MB for 1000 docs, target: <50MB)")
        
        # 4. Summary
        print("\n" + "="*80)
        print("BENCHMARK SUMMARY")
        print("="*80)
        
        passed_count = sum(1 for r in results if r.passed)
        total_count = len(results)
        
        print(f"\nTests Passed: {passed_count}/{total_count}")
        
        # Calculate overall throughput
        total_docs = sum(r.document_count for r in results)
        total_time = sum(r.total_time for r in results)
        overall_throughput = total_docs / total_time if total_time > 0 else 0
        overall_docs_per_min = overall_throughput * 60
        
        print(f"Overall Throughput: {overall_docs_per_min:.0f} docs/min")
        print(f"Target Throughput: {self.TARGETS['target_throughput']} docs/min (361K/min)")
        print(f"Performance Ratio: {overall_docs_per_min / self.TARGETS['target_throughput'] * 100:.1f}%")
        
        # Save results to file
        self.save_results(results)
        
        return results
    
    def save_results(self, results: List[BenchmarkResult]):
        """Save benchmark results to JSON file."""
        output_dir = Path("benchmark_results")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = output_dir / f"m003_benchmark_{self.mode.value}_{timestamp}.json"
        
        data = {
            "timestamp": datetime.now().isoformat(),
            "mode": self.mode.value,
            "results": [asdict(r) for r in results],
            "summary": {
                "passed": sum(1 for r in results if r.passed),
                "total": len(results),
                "avg_throughput": statistics.mean(r.throughput for r in results)
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"\nResults saved to: {filename}")


def main():
    """Run benchmarks for all operation modes."""
    modes_to_test = [
        OperationMode.BASIC,
        OperationMode.PERFORMANCE,  # Test optimized version
    ]
    
    all_results = {}
    
    for mode in modes_to_test:
        print(f"\n{'='*80}")
        print(f"TESTING MODE: {mode.value}")
        print(f"{'='*80}")
        
        benchmark = MIAIRBenchmark(mode=mode)
        results = benchmark.run_all_benchmarks()
        all_results[mode.value] = results
    
    # Compare results
    if len(all_results) > 1:
        print("\n" + "="*80)
        print("MODE COMPARISON")
        print("="*80)
        
        for mode_name, results in all_results.items():
            passed = sum(1 for r in results if r.passed)
            total = len(results)
            avg_throughput = statistics.mean(r.throughput for r in results)
            print(f"{mode_name}: {passed}/{total} passed, {avg_throughput:.2f} docs/sec avg")


if __name__ == "__main__":
    main()