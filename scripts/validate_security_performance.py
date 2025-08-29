#!/usr/bin/env python3
"""
Performance validation script for M003 MIAIR Engine security overhead.

Measures the performance impact of security features and validates
that overhead stays under 10% while maintaining 350,000+ docs/min throughput.
"""

import time
import psutil
import statistics
import json
import argparse
from typing import List, Dict, Any, Tuple
import multiprocessing as mp
from dataclasses import dataclass
import matplotlib.pyplot as plt
import numpy as np

# Import engines
from devdocai.miair.engine_optimized import (
    OptimizedMIAIREngine,
    OptimizedMIAIRConfig
)
from devdocai.miair.engine_secure import (
    SecureMIAIREngine,
    SecureMIAIRConfig
)


@dataclass
class PerformanceResult:
    """Performance measurement result."""
    operation: str
    document_size: int
    optimized_time: float
    secure_time: float
    overhead_percent: float
    optimized_throughput: float
    secure_throughput: float
    memory_usage_mb: float
    passed: bool


class SecurityPerformanceValidator:
    """Validate security performance overhead."""
    
    def __init__(self, verbose: bool = False):
        """Initialize validator."""
        self.verbose = verbose
        self.results: List[PerformanceResult] = []
        
        # Initialize engines
        self._setup_engines()
        
        # Generate test documents
        self._generate_test_documents()
    
    def _setup_engines(self):
        """Set up optimized and secure engines."""
        # Optimized engine configuration
        opt_config = OptimizedMIAIRConfig()
        opt_config.enable_parallel = True
        opt_config.num_workers = mp.cpu_count()
        opt_config.enable_caching = True
        opt_config.batch_size = 50
        
        self.optimized_engine = OptimizedMIAIREngine(opt_config)
        
        # Secure engine configuration
        sec_config = SecureMIAIRConfig()
        sec_config.enable_parallel = True
        sec_config.num_workers = mp.cpu_count()
        sec_config.enable_caching = True
        sec_config.batch_size = 50
        sec_config.require_validation = True
        sec_config.enforce_rate_limits = True
        sec_config.secure_cache_keys = True
        sec_config.audit_all_operations = True
        
        # Relax rate limits for performance testing
        sec_config.security_config.rate_limit_config.analyze_rate_limit = 100000
        sec_config.security_config.rate_limit_config.optimize_rate_limit = 10000
        sec_config.security_config.rate_limit_config.batch_rate_limit = 5000
        
        self.secure_engine = SecureMIAIREngine(sec_config)
        
        if self.verbose:
            print(f"Engines initialized with {mp.cpu_count()} workers")
    
    def _generate_test_documents(self):
        """Generate test documents of various sizes."""
        self.test_documents = {
            'small': self._generate_document(100),      # ~100 words
            'medium': self._generate_document(1000),    # ~1000 words
            'large': self._generate_document(10000),    # ~10000 words
            'xlarge': self._generate_document(50000)    # ~50000 words
        }
        
        if self.verbose:
            print(f"Generated test documents: {list(self.test_documents.keys())}")
    
    def _generate_document(self, word_count: int) -> str:
        """Generate a test document with specified word count."""
        words = [
            "The", "quick", "brown", "fox", "jumps", "over", "lazy", "dog",
            "Document", "analysis", "quality", "improvement", "optimization",
            "security", "performance", "testing", "validation", "benchmark"
        ]
        
        doc_words = []
        for i in range(word_count):
            doc_words.append(words[i % len(words)])
            if i % 10 == 9:
                doc_words.append(".")
            if i % 50 == 49:
                doc_words.append("\n")
        
        return " ".join(doc_words)
    
    def measure_analysis_performance(self) -> Dict[str, PerformanceResult]:
        """Measure document analysis performance."""
        results = {}
        
        for size_name, document in self.test_documents.items():
            if self.verbose:
                print(f"\nTesting analysis for {size_name} document...")
            
            # Warm up caches
            self.optimized_engine.analyze_document(document)
            self.secure_engine.analyze_document(document)
            
            # Measure optimized engine
            opt_times = []
            for _ in range(10):
                start = time.perf_counter()
                self.optimized_engine.analyze_document(document, f"test_{size_name}")
                opt_times.append(time.perf_counter() - start)
            
            opt_avg = statistics.mean(opt_times)
            opt_throughput = 60 / opt_avg  # docs/min
            
            # Measure secure engine
            sec_times = []
            for _ in range(10):
                start = time.perf_counter()
                self.secure_engine.analyze_document(document, f"test_{size_name}")
                sec_times.append(time.perf_counter() - start)
            
            sec_avg = statistics.mean(sec_times)
            sec_throughput = 60 / sec_avg  # docs/min
            
            # Calculate overhead
            overhead = ((sec_avg - opt_avg) / opt_avg) * 100
            
            # Get memory usage
            process = psutil.Process()
            memory_mb = process.memory_info().rss / (1024 * 1024)
            
            result = PerformanceResult(
                operation="analyze",
                document_size=len(document),
                optimized_time=opt_avg * 1000,  # Convert to ms
                secure_time=sec_avg * 1000,
                overhead_percent=overhead,
                optimized_throughput=opt_throughput,
                secure_throughput=sec_throughput,
                memory_usage_mb=memory_mb,
                passed=overhead < 10.0
            )
            
            results[size_name] = result
            self.results.append(result)
            
            if self.verbose:
                self._print_result(result)
        
        return results
    
    def measure_optimization_performance(self) -> Dict[str, PerformanceResult]:
        """Measure document optimization performance."""
        results = {}
        
        # Only test with smaller documents for optimization (it's slower)
        test_sizes = ['small', 'medium']
        
        for size_name in test_sizes:
            document = self.test_documents[size_name]
            
            if self.verbose:
                print(f"\nTesting optimization for {size_name} document...")
            
            # Measure optimized engine
            opt_times = []
            for _ in range(3):  # Fewer iterations for slow operation
                start = time.perf_counter()
                self.optimized_engine.optimize_document(document, f"opt_{size_name}")
                opt_times.append(time.perf_counter() - start)
            
            opt_avg = statistics.mean(opt_times)
            opt_throughput = 60 / opt_avg
            
            # Measure secure engine
            sec_times = []
            for _ in range(3):
                start = time.perf_counter()
                self.secure_engine.optimize_document(document, f"opt_{size_name}")
                sec_times.append(time.perf_counter() - start)
            
            sec_avg = statistics.mean(sec_times)
            sec_throughput = 60 / sec_avg
            
            # Calculate overhead
            overhead = ((sec_avg - opt_avg) / opt_avg) * 100
            
            # Get memory usage
            process = psutil.Process()
            memory_mb = process.memory_info().rss / (1024 * 1024)
            
            result = PerformanceResult(
                operation="optimize",
                document_size=len(document),
                optimized_time=opt_avg * 1000,
                secure_time=sec_avg * 1000,
                overhead_percent=overhead,
                optimized_throughput=opt_throughput,
                secure_throughput=sec_throughput,
                memory_usage_mb=memory_mb,
                passed=overhead < 10.0
            )
            
            results[size_name] = result
            self.results.append(result)
            
            if self.verbose:
                self._print_result(result)
        
        return results
    
    def measure_batch_performance(self) -> PerformanceResult:
        """Measure batch processing performance."""
        if self.verbose:
            print("\nTesting batch processing performance...")
        
        # Create batch of medium documents
        batch_size = 100
        documents = [self.test_documents['medium'] for _ in range(batch_size)]
        
        # Measure optimized engine
        start = time.perf_counter()
        opt_result = self.optimized_engine.process_batch_optimized(documents, optimize=False)
        opt_time = time.perf_counter() - start
        opt_throughput = opt_result.throughput_docs_per_min
        
        # Measure secure engine
        start = time.perf_counter()
        sec_result = self.secure_engine.process_batch_optimized(documents, optimize=False)
        sec_time = time.perf_counter() - start
        sec_throughput = sec_result.throughput_docs_per_min
        
        # Calculate overhead
        overhead = ((sec_time - opt_time) / opt_time) * 100
        
        # Get memory usage
        process = psutil.Process()
        memory_mb = process.memory_info().rss / (1024 * 1024)
        
        result = PerformanceResult(
            operation="batch",
            document_size=batch_size,
            optimized_time=opt_time * 1000,
            secure_time=sec_time * 1000,
            overhead_percent=overhead,
            optimized_throughput=opt_throughput,
            secure_throughput=sec_throughput,
            memory_usage_mb=memory_mb,
            passed=overhead < 10.0 and sec_throughput > 350000
        )
        
        self.results.append(result)
        
        if self.verbose:
            self._print_result(result)
            print(f"  Secure throughput: {sec_throughput:,.0f} docs/min")
            print(f"  Target: 350,000 docs/min - {'✓ PASSED' if sec_throughput > 350000 else '✗ FAILED'}")
        
        return result
    
    def measure_security_features_overhead(self) -> Dict[str, float]:
        """Measure overhead of individual security features."""
        if self.verbose:
            print("\nMeasuring individual security feature overhead...")
        
        document = self.test_documents['medium']
        overheads = {}
        
        # Baseline - no security
        config = SecureMIAIRConfig()
        config.require_validation = False
        config.enforce_rate_limits = False
        config.secure_cache_keys = False
        config.audit_all_operations = False
        config.security_config.enable_validation = False
        config.security_config.enable_rate_limiting = False
        config.security_config.enable_audit_logging = False
        
        baseline_engine = SecureMIAIREngine(config)
        
        # Measure baseline
        baseline_times = []
        for _ in range(10):
            start = time.perf_counter()
            baseline_engine.analyze_document(document)
            baseline_times.append(time.perf_counter() - start)
        baseline_avg = statistics.mean(baseline_times)
        
        # Test each feature
        features = [
            ('validation', {'require_validation': True, 'security_config.enable_validation': True}),
            ('rate_limiting', {'enforce_rate_limits': True, 'security_config.enable_rate_limiting': True}),
            ('secure_cache', {'secure_cache_keys': True}),
            ('audit_logging', {'audit_all_operations': True, 'security_config.enable_audit_logging': True})
        ]
        
        for feature_name, settings in features:
            config = SecureMIAIRConfig()
            # Disable all security
            config.require_validation = False
            config.enforce_rate_limits = False
            config.secure_cache_keys = False
            config.audit_all_operations = False
            
            # Enable specific feature
            for key, value in settings.items():
                if '.' in key:
                    parts = key.split('.')
                    setattr(getattr(config, parts[0]), parts[1], value)
                else:
                    setattr(config, key, value)
            
            engine = SecureMIAIREngine(config)
            
            # Measure with feature
            feature_times = []
            for _ in range(10):
                start = time.perf_counter()
                engine.analyze_document(document)
                feature_times.append(time.perf_counter() - start)
            feature_avg = statistics.mean(feature_times)
            
            # Calculate overhead
            overhead = ((feature_avg - baseline_avg) / baseline_avg) * 100
            overheads[feature_name] = overhead
            
            if self.verbose:
                print(f"  {feature_name}: {overhead:.2f}% overhead")
        
        return overheads
    
    def _print_result(self, result: PerformanceResult):
        """Print a single result."""
        print(f"  Operation: {result.operation}")
        print(f"  Optimized: {result.optimized_time:.2f}ms")
        print(f"  Secure: {result.secure_time:.2f}ms")
        print(f"  Overhead: {result.overhead_percent:.2f}%")
        print(f"  Status: {'✓ PASSED' if result.passed else '✗ FAILED'}")
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        # Calculate summary statistics
        all_overheads = [r.overhead_percent for r in self.results]
        avg_overhead = statistics.mean(all_overheads)
        max_overhead = max(all_overheads)
        
        # Check throughput target
        batch_results = [r for r in self.results if r.operation == "batch"]
        meets_throughput = all(r.secure_throughput > 350000 for r in batch_results)
        
        # Overall pass/fail
        all_passed = all(r.passed for r in self.results)
        
        report = {
            'summary': {
                'total_tests': len(self.results),
                'passed': sum(1 for r in self.results if r.passed),
                'failed': sum(1 for r in self.results if not r.passed),
                'average_overhead': avg_overhead,
                'max_overhead': max_overhead,
                'meets_throughput_target': meets_throughput,
                'overall_status': 'PASSED' if all_passed and meets_throughput else 'FAILED'
            },
            'detailed_results': [
                {
                    'operation': r.operation,
                    'document_size': r.document_size,
                    'optimized_time_ms': r.optimized_time,
                    'secure_time_ms': r.secure_time,
                    'overhead_percent': r.overhead_percent,
                    'secure_throughput_docs_per_min': r.secure_throughput,
                    'passed': r.passed
                }
                for r in self.results
            ],
            'requirements': {
                'max_overhead_target': 10.0,
                'throughput_target': 350000,
                'max_overhead_achieved': max_overhead,
                'min_throughput_achieved': min(r.secure_throughput for r in batch_results) if batch_results else 0
            }
        }
        
        return report
    
    def plot_results(self, output_file: str = "security_performance.png"):
        """Plot performance results."""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
        
        # Plot 1: Overhead by operation
        operations = {}
        for r in self.results:
            if r.operation not in operations:
                operations[r.operation] = []
            operations[r.operation].append(r.overhead_percent)
        
        ax1.bar(operations.keys(), [statistics.mean(v) for v in operations.values()])
        ax1.axhline(y=10, color='r', linestyle='--', label='10% Target')
        ax1.set_ylabel('Overhead (%)')
        ax1.set_title('Security Overhead by Operation')
        ax1.legend()
        
        # Plot 2: Processing time comparison
        sizes = ['small', 'medium', 'large']
        opt_times = []
        sec_times = []
        
        for size in sizes:
            size_results = [r for r in self.results if r.operation == 'analyze' and size in str(r.document_size)]
            if size_results:
                opt_times.append(size_results[0].optimized_time)
                sec_times.append(size_results[0].secure_time)
        
        if opt_times and sec_times:
            x = np.arange(len(sizes))
            width = 0.35
            ax2.bar(x - width/2, opt_times, width, label='Optimized')
            ax2.bar(x + width/2, sec_times, width, label='Secure')
            ax2.set_xlabel('Document Size')
            ax2.set_ylabel('Time (ms)')
            ax2.set_title('Processing Time Comparison')
            ax2.set_xticks(x)
            ax2.set_xticklabels(sizes)
            ax2.legend()
        
        # Plot 3: Throughput comparison
        batch_result = next((r for r in self.results if r.operation == 'batch'), None)
        if batch_result:
            throughputs = [batch_result.optimized_throughput, batch_result.secure_throughput, 350000]
            labels = ['Optimized', 'Secure', 'Target']
            colors = ['blue', 'green', 'red']
            ax3.bar(labels, throughputs, color=colors)
            ax3.set_ylabel('Throughput (docs/min)')
            ax3.set_title('Batch Processing Throughput')
            ax3.ticklabel_format(style='plain', axis='y')
        
        # Plot 4: Memory usage
        memory_by_op = {}
        for r in self.results:
            if r.operation not in memory_by_op:
                memory_by_op[r.operation] = []
            memory_by_op[r.operation].append(r.memory_usage_mb)
        
        if memory_by_op:
            ax4.bar(memory_by_op.keys(), [max(v) for v in memory_by_op.values()])
            ax4.set_ylabel('Memory (MB)')
            ax4.set_title('Peak Memory Usage')
        
        plt.tight_layout()
        plt.savefig(output_file)
        print(f"\nPerformance plots saved to {output_file}")
    
    def run_validation(self) -> bool:
        """Run complete validation suite."""
        print("=" * 60)
        print("M003 MIAIR Engine Security Performance Validation")
        print("=" * 60)
        
        # Run tests
        print("\n1. Document Analysis Performance")
        self.measure_analysis_performance()
        
        print("\n2. Document Optimization Performance")
        self.measure_optimization_performance()
        
        print("\n3. Batch Processing Performance")
        batch_result = self.measure_batch_performance()
        
        print("\n4. Individual Security Features Overhead")
        feature_overheads = self.measure_security_features_overhead()
        
        # Generate report
        report = self.generate_report()
        
        # Print summary
        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {report['summary']['total_tests']}")
        print(f"Passed: {report['summary']['passed']}")
        print(f"Failed: {report['summary']['failed']}")
        print(f"Average Overhead: {report['summary']['average_overhead']:.2f}%")
        print(f"Maximum Overhead: {report['summary']['max_overhead']:.2f}%")
        print(f"Meets Throughput Target (350k docs/min): {report['summary']['meets_throughput_target']}")
        print(f"\nOVERALL STATUS: {report['summary']['overall_status']}")
        
        # Save report
        with open('security_performance_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        print("\nDetailed report saved to security_performance_report.json")
        
        # Generate plots
        self.plot_results()
        
        return report['summary']['overall_status'] == 'PASSED'


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Validate M003 security performance')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--plot', action='store_true', help='Generate performance plots')
    args = parser.parse_args()
    
    validator = SecurityPerformanceValidator(verbose=args.verbose)
    passed = validator.run_validation()
    
    exit(0 if passed else 1)


if __name__ == '__main__':
    main()