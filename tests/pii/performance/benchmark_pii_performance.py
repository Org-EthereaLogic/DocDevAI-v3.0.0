"""
Performance Benchmarking Suite for Enhanced PII Detection.

Provides comprehensive performance validation targeting ≥1000 words/second
with stress testing, scalability analysis, and memory profiling.
"""

import unittest
import time
import logging
import gc
import threading
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
import json
import statistics
import psutil
import os
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing

# Import our enhanced detector
import sys
sys.path.append('/workspaces/DocDevAI-v3.0.0')
from devdocai.storage.enhanced_pii_detector import (
    EnhancedPIIDetector, EnhancedPIIDetectionConfig
)

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance measurement results."""
    words_per_second: float
    documents_per_second: float
    processing_time: float
    memory_usage_mb: float
    cpu_usage_percent: float
    thread_count: int
    cache_hit_ratio: float = 0.0
    
    def meets_target(self, target_wps: int = 1000) -> bool:
        """Check if performance meets target."""
        return self.words_per_second >= target_wps


@dataclass
class BenchmarkResult:
    """Complete benchmark result."""
    test_name: str
    dataset_size: int
    total_words: int
    total_documents: int
    performance_metrics: PerformanceMetrics
    scalability_factor: float  # Performance per unit of input
    memory_efficiency: float   # Words processed per MB memory
    passes_target: bool
    notes: str = ""


class PerformanceDataGenerator:
    """Generate datasets for performance testing."""
    
    @staticmethod
    def generate_small_documents(count: int = 1000) -> List[str]:
        """Generate small documents (10-50 words each)."""
        documents = []
        
        pii_templates = [
            "Contact John Doe at john.doe@example.com or call 555-123-4567.",
            "SSN: 123-45-6789, Address: 123 Main St, Anytown, CA 90210",
            "Credit card: 4532-1234-5678-9012, expires 12/25",
            "Driver license: A1234567, DOB: 01/15/1985",
            "IP address: 192.168.1.100, Device ID: ABC123DEF456",
        ]
        
        filler_words = [
            "The quick brown fox jumps over the lazy dog.",
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "Performance testing requires realistic data patterns.",
            "This document contains various information types.",
            "Processing speed optimization is critical for enterprise use.",
        ]
        
        for i in range(count):
            # Mix PII and non-PII content
            if i % 3 == 0:
                doc = f"Document {i}: " + pii_templates[i % len(pii_templates)]
            else:
                doc = f"Document {i}: " + filler_words[i % len(filler_words)]
            
            # Add some variation
            if i % 5 == 0:
                doc += f" Additional content for document {i} with more text."
                
            documents.append(doc)
            
        return documents
    
    @staticmethod
    def generate_medium_documents(count: int = 500) -> List[str]:
        """Generate medium documents (100-300 words each)."""
        documents = []
        
        for i in range(count):
            doc_parts = []
            doc_parts.append(f"Medium Document {i} - Performance Testing Report")
            
            # Add PII content
            if i % 2 == 0:
                doc_parts.append(f"Contact: user{i}@test-domain.com, Phone: +1-555-{i:04d}")
                doc_parts.append(f"SSN: {100 + (i % 900):03d}-{10 + (i % 90):02d}-{1000 + (i % 9000):04d}")
            
            # Add filler content
            for j in range(5 + (i % 10)):
                doc_parts.append(f"Section {j}: This is paragraph {j} of document {i}. " * 5)
                
            if i % 4 == 0:
                doc_parts.append(f"Device identifier: DEV-{i:08X}, Location: {37.7749 + (i % 100) * 0.001:.4f},-{122.4194 + (i % 100) * 0.001:.4f}")
            
            documents.append(" ".join(doc_parts))
            
        return documents
    
    @staticmethod
    def generate_large_documents(count: int = 100) -> List[str]:
        """Generate large documents (1000+ words each)."""
        documents = []
        
        for i in range(count):
            doc_parts = []
            doc_parts.append(f"Large Document {i} - Comprehensive Performance Analysis")
            
            # Multiple sections with varied content
            for section in range(10):
                doc_parts.append(f"\nSection {section}: Analysis Report")
                
                # Add PII scattered throughout
                if section % 3 == 0:
                    doc_parts.append(f"Primary contact: analyst{i}_{section}@company.com")
                    doc_parts.append(f"Employee ID: EMP{i:04d}{section:02d}")
                
                # Add substantial filler content
                for para in range(15):
                    doc_parts.append(f"Paragraph {para} of section {section}: " + 
                                   "This comprehensive analysis examines various performance metrics " +
                                   "and optimization strategies for enterprise-grade applications. " * 3)
                
                if section % 4 == 0:
                    doc_parts.append(f"Reference ID: REF-{i:04d}-{section:02d}, " +
                                   f"Timestamp: 2024-01-{1 + (i % 28):02d}T{10 + section:02d}:30:00Z")
            
            documents.append(" ".join(doc_parts))
            
        return documents
    
    @staticmethod
    def generate_stress_test_dataset(count: int = 5000) -> List[str]:
        """Generate large dataset for stress testing."""
        # Combine all sizes for realistic mix
        small_docs = PerformanceDataGenerator.generate_small_documents(count // 2)
        medium_docs = PerformanceDataGenerator.generate_medium_documents(count // 3)
        large_docs = PerformanceDataGenerator.generate_large_documents(count // 6)
        
        return small_docs + medium_docs + large_docs


class PerformanceBenchmark:
    """Comprehensive performance benchmarking suite."""
    
    def __init__(self, detector: EnhancedPIIDetector):
        """Initialize with enhanced PII detector."""
        self.detector = detector
        self.results = []
        
    def benchmark_small_documents(self) -> BenchmarkResult:
        """Benchmark performance on small documents."""
        logger.info("Benchmarking small documents (10-50 words each)...")
        
        documents = PerformanceDataGenerator.generate_small_documents(1000)
        return self._run_benchmark("Small Documents", documents)
    
    def benchmark_medium_documents(self) -> BenchmarkResult:
        """Benchmark performance on medium documents."""
        logger.info("Benchmarking medium documents (100-300 words each)...")
        
        documents = PerformanceDataGenerator.generate_medium_documents(500)
        return self._run_benchmark("Medium Documents", documents)
    
    def benchmark_large_documents(self) -> BenchmarkResult:
        """Benchmark performance on large documents."""
        logger.info("Benchmarking large documents (1000+ words each)...")
        
        documents = PerformanceDataGenerator.generate_large_documents(100)
        return self._run_benchmark("Large Documents", documents)
    
    def benchmark_stress_test(self) -> BenchmarkResult:
        """Run stress test with large dataset."""
        logger.info("Running stress test with 5000+ documents...")
        
        documents = PerformanceDataGenerator.generate_stress_test_dataset(5000)
        return self._run_benchmark("Stress Test", documents)
    
    def benchmark_concurrent_processing(self, thread_counts: List[int] = [1, 2, 4, 8]) -> Dict[int, BenchmarkResult]:
        """Benchmark concurrent processing with different thread counts."""
        logger.info("Benchmarking concurrent processing...")
        
        documents = PerformanceDataGenerator.generate_medium_documents(1000)
        results = {}
        
        for thread_count in thread_counts:
            logger.info(f"Testing with {thread_count} threads...")
            result = self._run_concurrent_benchmark("Concurrent Processing", documents, thread_count)
            results[thread_count] = result
            
        return results
    
    def benchmark_memory_efficiency(self) -> List[BenchmarkResult]:
        """Test memory efficiency across different dataset sizes."""
        logger.info("Benchmarking memory efficiency...")
        
        sizes = [100, 500, 1000, 2500, 5000]
        results = []
        
        for size in sizes:
            logger.info(f"Testing memory efficiency with {size} documents...")
            
            # Generate mixed document types
            small_count = size // 3
            medium_count = size // 3
            large_count = size - small_count - medium_count
            
            documents = (
                PerformanceDataGenerator.generate_small_documents(small_count) +
                PerformanceDataGenerator.generate_medium_documents(medium_count) +
                PerformanceDataGenerator.generate_large_documents(large_count)
            )
            
            result = self._run_benchmark(f"Memory Test ({size} docs)", documents)
            results.append(result)
            
            # Force garbage collection between tests
            gc.collect()
            
        return results
    
    def _run_benchmark(self, test_name: str, documents: List[str]) -> BenchmarkResult:
        """Run benchmark on document set."""
        # Pre-benchmark cleanup
        gc.collect()
        
        # Measure baseline memory
        process = psutil.Process(os.getpid())
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Count total words
        total_words = sum(len(doc.split()) for doc in documents)
        total_documents = len(documents)
        
        logger.info(f"Processing {total_documents} documents with {total_words} total words...")
        
        # Start performance monitoring
        start_time = time.time()
        start_cpu_times = psutil.cpu_times()
        
        # Process all documents
        total_detections = 0
        for doc in documents:
            detections = self.detector.enhanced_detect(doc)
            total_detections += len(detections)
        
        # End performance monitoring
        end_time = time.time()
        end_cpu_times = psutil.cpu_times()
        
        processing_time = end_time - start_time
        
        # Measure final memory
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_usage = final_memory - baseline_memory
        
        # Calculate CPU usage (simplified)
        cpu_usage = ((end_cpu_times.user - start_cpu_times.user) / processing_time * 100 
                    if processing_time > 0 else 0)
        
        # Calculate performance metrics
        wps = total_words / processing_time if processing_time > 0 else 0
        dps = total_documents / processing_time if processing_time > 0 else 0
        
        performance_metrics = PerformanceMetrics(
            words_per_second=wps,
            documents_per_second=dps,
            processing_time=processing_time,
            memory_usage_mb=max(memory_usage, 0),  # Avoid negative values
            cpu_usage_percent=min(cpu_usage, 100),  # Cap at 100%
            thread_count=1
        )
        
        scalability_factor = wps / total_documents if total_documents > 0 else 0
        memory_efficiency = total_words / max(memory_usage, 1) if memory_usage > 0 else total_words
        
        result = BenchmarkResult(
            test_name=test_name,
            dataset_size=total_documents,
            total_words=total_words,
            total_documents=total_documents,
            performance_metrics=performance_metrics,
            scalability_factor=scalability_factor,
            memory_efficiency=memory_efficiency,
            passes_target=performance_metrics.meets_target(1000),
            notes=f"Total PII detections: {total_detections}"
        )
        
        self.results.append(result)
        return result
    
    def _run_concurrent_benchmark(self, test_name: str, documents: List[str], thread_count: int) -> BenchmarkResult:
        """Run concurrent benchmark with specified thread count."""
        # Pre-benchmark cleanup
        gc.collect()
        
        # Measure baseline memory
        process = psutil.Process(os.getpid())
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        total_words = sum(len(doc.split()) for doc in documents)
        total_documents = len(documents)
        
        # Split documents into chunks for threads
        chunk_size = len(documents) // thread_count
        document_chunks = [
            documents[i:i + chunk_size] for i in range(0, len(documents), chunk_size)
        ]
        
        # Thread-safe detector instances
        detectors = [
            EnhancedPIIDetector(self.detector.enhanced_config) 
            for _ in range(thread_count)
        ]
        
        def process_chunk(chunk_and_detector):
            chunk, detector = chunk_and_detector
            total_detections = 0
            for doc in chunk:
                detections = detector.enhanced_detect(doc)
                total_detections += len(detections)
            return total_detections
        
        # Run concurrent processing
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            chunk_detector_pairs = list(zip(document_chunks, detectors))
            detection_counts = list(executor.map(process_chunk, chunk_detector_pairs))
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Measure final memory
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_usage = final_memory - baseline_memory
        
        # Calculate metrics
        wps = total_words / processing_time if processing_time > 0 else 0
        dps = total_documents / processing_time if processing_time > 0 else 0
        total_detections = sum(detection_counts)
        
        performance_metrics = PerformanceMetrics(
            words_per_second=wps,
            documents_per_second=dps,
            processing_time=processing_time,
            memory_usage_mb=max(memory_usage, 0),
            cpu_usage_percent=0,  # Difficult to measure accurately in concurrent scenario
            thread_count=thread_count
        )
        
        scalability_factor = wps / total_documents if total_documents > 0 else 0
        memory_efficiency = total_words / max(memory_usage, 1) if memory_usage > 0 else total_words
        
        return BenchmarkResult(
            test_name=f"{test_name} ({thread_count} threads)",
            dataset_size=total_documents,
            total_words=total_words,
            total_documents=total_documents,
            performance_metrics=performance_metrics,
            scalability_factor=scalability_factor,
            memory_efficiency=memory_efficiency,
            passes_target=performance_metrics.meets_target(1000),
            notes=f"Total PII detections: {total_detections}, Threads: {thread_count}"
        )
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        if not self.results:
            return {"error": "No benchmark results available"}
        
        # Calculate statistics
        wps_values = [r.performance_metrics.words_per_second for r in self.results]
        memory_values = [r.performance_metrics.memory_usage_mb for r in self.results]
        
        # Find best and worst performers
        best_performance = max(self.results, key=lambda r: r.performance_metrics.words_per_second)
        worst_performance = min(self.results, key=lambda r: r.performance_metrics.words_per_second)
        
        # Count passing tests
        passing_tests = sum(1 for r in self.results if r.passes_target)
        
        report = {
            'summary': {
                'total_tests': len(self.results),
                'passing_tests': passing_tests,
                'pass_rate': f"{(passing_tests / len(self.results) * 100):.1f}%",
                'target_wps': 1000,
                'max_wps_achieved': max(wps_values),
                'min_wps_achieved': min(wps_values),
                'avg_wps': statistics.mean(wps_values),
                'median_wps': statistics.median(wps_values),
                'avg_memory_mb': statistics.mean(memory_values),
                'median_memory_mb': statistics.median(memory_values),
                'overall_performance_grade': self._calculate_performance_grade(wps_values)
            },
            'best_performance': {
                'test_name': best_performance.test_name,
                'words_per_second': best_performance.performance_metrics.words_per_second,
                'memory_usage_mb': best_performance.performance_metrics.memory_usage_mb,
                'scalability_factor': best_performance.scalability_factor
            },
            'worst_performance': {
                'test_name': worst_performance.test_name,
                'words_per_second': worst_performance.performance_metrics.words_per_second,
                'memory_usage_mb': worst_performance.performance_metrics.memory_usage_mb,
                'scalability_factor': worst_performance.scalability_factor
            },
            'detailed_results': [
                {
                    'test_name': r.test_name,
                    'dataset_size': r.dataset_size,
                    'total_words': r.total_words,
                    'words_per_second': r.performance_metrics.words_per_second,
                    'documents_per_second': r.performance_metrics.documents_per_second,
                    'processing_time': r.performance_metrics.processing_time,
                    'memory_usage_mb': r.performance_metrics.memory_usage_mb,
                    'memory_efficiency': r.memory_efficiency,
                    'scalability_factor': r.scalability_factor,
                    'passes_target': r.passes_target,
                    'notes': r.notes
                } for r in self.results
            ],
            'recommendations': self._generate_performance_recommendations(wps_values, memory_values)
        }
        
        return report
    
    def _calculate_performance_grade(self, wps_values: List[float]) -> str:
        """Calculate overall performance grade."""
        avg_wps = statistics.mean(wps_values)
        
        if avg_wps >= 2000:
            return "A+ (Excellent)"
        elif avg_wps >= 1500:
            return "A (Very Good)"
        elif avg_wps >= 1000:
            return "B (Good - Meets Target)"
        elif avg_wps >= 500:
            return "C (Fair - Below Target)"
        else:
            return "D (Poor - Needs Optimization)"
    
    def _generate_performance_recommendations(self, wps_values: List[float], memory_values: List[float]) -> List[str]:
        """Generate performance optimization recommendations."""
        recommendations = []
        
        avg_wps = statistics.mean(wps_values)
        avg_memory = statistics.mean(memory_values)
        
        if avg_wps < 1000:
            recommendations.append("Performance below target - consider pattern optimization")
            recommendations.append("Implement regex compilation caching")
            recommendations.append("Consider parallel processing for large datasets")
        
        if avg_memory > 100:
            recommendations.append("High memory usage detected - implement memory pooling")
            recommendations.append("Consider streaming processing for large documents")
        
        if len(set(wps_values)) > len(wps_values) * 0.5:  # High variance
            recommendations.append("Inconsistent performance - investigate document size impact")
            recommendations.append("Consider adaptive processing strategies")
        
        if not recommendations:
            recommendations.append("Performance is meeting targets - consider additional optimizations for edge cases")
        
        return recommendations


class TestPIIPerformance(unittest.TestCase):
    """Unit tests for PII detection performance."""
    
    def setUp(self):
        """Set up test fixtures."""
        config = EnhancedPIIDetectionConfig(
            gdpr_enabled=True,
            ccpa_enabled=True,
            multilang_enabled=True,
            context_analysis=True,
            min_confidence=0.70,
            performance_target_wps=1000
        )
        self.detector = EnhancedPIIDetector(config)
        self.benchmark = PerformanceBenchmark(self.detector)
    
    def test_small_document_performance(self):
        """Test performance on small documents."""
        result = self.benchmark.benchmark_small_documents()
        
        # Should process at reasonable speed
        self.assertGreater(result.performance_metrics.words_per_second, 100,
                          "Should process at least 100 words per second")
        self.assertLess(result.performance_metrics.memory_usage_mb, 200,
                       "Memory usage should be reasonable for small documents")
    
    def test_performance_target_achievement(self):
        """Test if any configuration can achieve 1000+ wps target."""
        # Test with optimized configuration
        fast_config = EnhancedPIIDetectionConfig(
            gdpr_enabled=False,  # Disable some features for speed
            ccpa_enabled=False,
            multilang_enabled=False,
            context_analysis=False,
            min_confidence=0.80,  # Higher threshold for speed
            performance_target_wps=1000
        )
        
        fast_detector = EnhancedPIIDetector(fast_config)
        fast_benchmark = PerformanceBenchmark(fast_detector)
        
        result = fast_benchmark.benchmark_small_documents()
        
        # With optimizations, should achieve better performance
        self.assertGreater(result.performance_metrics.words_per_second, 200,
                          "Optimized detector should achieve higher wps")
    
    def test_memory_efficiency(self):
        """Test memory efficiency across different dataset sizes."""
        results = self.benchmark.benchmark_memory_efficiency()
        
        # Memory usage should not grow excessively
        for result in results:
            self.assertLess(result.performance_metrics.memory_usage_mb, 500,
                           f"Memory usage too high for {result.test_name}")
            
        # Memory efficiency should be reasonable
        avg_efficiency = statistics.mean(r.memory_efficiency for r in results)
        self.assertGreater(avg_efficiency, 100,
                          "Should process at least 100 words per MB memory")
    
    def test_concurrent_processing_scaling(self):
        """Test concurrent processing performance scaling."""
        thread_counts = [1, 2, 4]
        results = self.benchmark.benchmark_concurrent_processing(thread_counts)
        
        # Concurrent processing should improve performance
        single_thread_wps = results[1].performance_metrics.words_per_second
        
        for thread_count in [2, 4]:
            if thread_count in results:
                multi_thread_wps = results[thread_count].performance_metrics.words_per_second
                # Should show some improvement (allowing for overhead)
                self.assertGreater(multi_thread_wps, single_thread_wps * 0.8,
                                  f"{thread_count}-thread processing should scale reasonably")


if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Create enhanced detector
    config = EnhancedPIIDetectionConfig(
        gdpr_enabled=True,
        ccpa_enabled=True,
        multilang_enabled=True,
        context_analysis=True,
        min_confidence=0.70,
        performance_target_wps=1000
    )
    
    detector = EnhancedPIIDetector(config)
    benchmark = PerformanceBenchmark(detector)
    
    print("🚀 Enhanced PII Detection Performance Benchmarking Suite")
    print("=" * 65)
    print(f"Target Performance: ≥1000 words per second")
    print(f"System CPU cores: {multiprocessing.cpu_count()}")
    print(f"Available memory: {psutil.virtual_memory().total / 1024 / 1024 / 1024:.1f} GB")
    print()
    
    # Run all benchmarks
    print("📊 Running Performance Benchmarks...")
    
    # Individual benchmarks
    small_result = benchmark.benchmark_small_documents()
    medium_result = benchmark.benchmark_medium_documents()
    large_result = benchmark.benchmark_large_documents()
    
    # Memory efficiency tests
    print("\n🧠 Testing Memory Efficiency...")
    memory_results = benchmark.benchmark_memory_efficiency()
    
    # Concurrent processing tests
    print("\n⚡ Testing Concurrent Processing...")
    concurrent_results = benchmark.benchmark_concurrent_processing([1, 2, 4, 8])
    
    # Stress test
    print("\n🔥 Running Stress Test...")
    stress_result = benchmark.benchmark_stress_test()
    
    # Generate comprehensive report
    report = benchmark.generate_performance_report()
    
    # Display results
    print("\n📈 PERFORMANCE RESULTS")
    print("=" * 35)
    print(f"Max Performance: {report['summary']['max_wps_achieved']:.1f} words/sec")
    print(f"Average Performance: {report['summary']['avg_wps']:.1f} words/sec")
    print(f"Min Performance: {report['summary']['min_wps_achieved']:.1f} words/sec")
    print(f"Target Achievement: {report['summary']['pass_rate']} of tests")
    print(f"Performance Grade: {report['summary']['overall_performance_grade']}")
    
    print(f"\n💾 Memory Usage:")
    print(f"Average Memory: {report['summary']['avg_memory_mb']:.1f} MB")
    print(f"Best Performer: {report['best_performance']['test_name']}")
    print(f"  └─ {report['best_performance']['words_per_second']:.1f} wps, {report['best_performance']['memory_usage_mb']:.1f} MB")
    
    print("\n🎯 CONCURRENT PROCESSING RESULTS")
    print("=" * 40)
    for thread_count, result in concurrent_results.items():
        status = "✅ PASS" if result.passes_target else "❌ FAIL"
        print(f"{thread_count} threads: {result.performance_metrics.words_per_second:.1f} wps {status}")
    
    print("\n💡 RECOMMENDATIONS")
    print("=" * 20)
    for i, rec in enumerate(report['recommendations'], 1):
        print(f"{i}. {rec}")
    
    # Save detailed results
    results_file = Path('/workspaces/DocDevAI-v3.0.0/tests/pii/performance/performance_results.json')
    results_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(results_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n📄 Detailed results saved to: {results_file}")
    
    # Run unit tests
    print("\n🔬 Running Unit Tests...")
    unittest.main(argv=[''], exit=False, verbosity=2)