#!/usr/bin/env python3
"""
M004 Document Generator - Pass 2 Performance Benchmarks

Comprehensive performance testing suite for M004 Pass 2 optimization.
Tests baseline performance and identifies optimization opportunities.
"""

import sys
import time
import statistics
import concurrent.futures
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import logging
import asyncio
from dataclasses import dataclass, asdict

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from devdocai.generator.core.engine import DocumentGenerator, GenerationConfig
from devdocai.generator.core.template_loader import TemplateLoader
from devdocai.generator.core.content_processor import ContentProcessor
from devdocai.core.config import ConfigurationManager
from devdocai.storage import LocalStorageSystem
from devdocai.common.performance import ResourceMonitor


@dataclass
class BenchmarkResult:
    """Results from a benchmark test."""
    test_name: str
    operation_type: str
    iterations: int
    total_time: float
    average_time: float
    min_time: float
    max_time: float
    operations_per_second: float
    median_time: float
    std_dev: float
    memory_usage_mb: Optional[float] = None
    success_rate: float = 100.0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class M004PerformanceBenchmark:
    """Comprehensive M004 performance benchmark suite."""
    
    def __init__(self):
        """Initialize benchmark suite."""
        self.config_manager = ConfigurationManager()
        self.storage_system = LocalStorageSystem()
        self.generator = DocumentGenerator(self.config_manager, self.storage_system)
        self.results: List[BenchmarkResult] = []
        
        # Test data
        self.test_inputs = {
            "simple": {
                "title": "Test Document",
                "project_name": "Test Project",
                "author": "DevDocAI Test",
                "overview": "This is a test document for performance benchmarking.",
                "version": "1.0.0"
            },
            "medium": {
                "title": "Complex Software Requirements Specification",
                "project_name": "Advanced E-commerce Platform",
                "author": "DevDocAI Engineering Team",
                "overview": "A comprehensive requirements document for a large-scale e-commerce platform with advanced features.",
                "requirements": [
                    {
                        "id": "REQ-001",
                        "title": "User Authentication System",
                        "description": "Multi-factor authentication with OAuth2 support",
                        "priority": "High",
                        "status": "Active"
                    },
                    {
                        "id": "REQ-002", 
                        "title": "Payment Processing",
                        "description": "Secure payment processing with multiple payment methods",
                        "priority": "Critical",
                        "status": "Active"
                    },
                    {
                        "id": "REQ-003",
                        "title": "Inventory Management",
                        "description": "Real-time inventory tracking and management system",
                        "priority": "High", 
                        "status": "Active"
                    }
                ],
                "version": "2.1.0",
                "features": ["Authentication", "Payment", "Inventory", "Analytics", "Mobile Support"],
                "technologies": ["React", "Node.js", "PostgreSQL", "Redis", "Docker"]
            },
            "large": {
                "title": "Enterprise System Documentation",
                "project_name": "Global Manufacturing ERP System",
                "author": "Enterprise Architecture Team",
                "overview": "Complete documentation for a global manufacturing ERP system with hundreds of modules and integrations.",
                "modules": [f"Module {i:03d}" for i in range(1, 101)],
                "requirements": [
                    {
                        "id": f"REQ-{i:04d}",
                        "title": f"Requirement {i}",
                        "description": f"Detailed description for requirement {i} with comprehensive acceptance criteria and implementation notes.",
                        "priority": ["Critical", "High", "Medium", "Low"][i % 4],
                        "status": "Active"
                    }
                    for i in range(1, 201)
                ],
                "version": "5.2.1",
                "detailed_content": "Lorem ipsum " * 1000  # ~11KB of text
            }
        }
        
        # Available templates
        self.templates = [
            "technical/srs",
            "technical/prd", 
            "project/readme",
            "user/user_manual"
        ]
    
    def run_all_benchmarks(self) -> Dict[str, Any]:
        """Run complete benchmark suite."""
        print("🚀 Starting M004 Document Generator Pass 2 Performance Benchmarks")
        print("=" * 80)
        
        start_time = datetime.now()
        
        # Core performance benchmarks
        self._benchmark_template_loading()
        self._benchmark_content_processing()
        self._benchmark_document_generation()
        self._benchmark_output_formatting()
        
        # Advanced performance benchmarks  
        self._benchmark_concurrent_generation()
        self._benchmark_batch_operations()
        self._benchmark_memory_usage()
        self._benchmark_cache_performance()
        
        # End-to-end benchmarks
        self._benchmark_full_workflow()
        
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        
        # Compile results
        results_summary = {
            "benchmark_info": {
                "version": "M004 Pass 2",
                "timestamp": start_time.isoformat(),
                "duration_seconds": total_duration,
                "total_tests": len(self.results)
            },
            "results": [asdict(r) for r in self.results],
            "summary": self._generate_summary()
        }
        
        self._save_results(results_summary)
        self._print_summary(results_summary)
        
        return results_summary
    
    def _benchmark_template_loading(self):
        """Benchmark template loading performance."""
        print("\n📁 Template Loading Performance")
        print("-" * 40)
        
        # Test template loading speed
        for template in self.templates:
            times = []
            errors = []
            
            for i in range(50):  # 50 iterations
                try:
                    start_time = time.perf_counter()
                    self.generator.template_loader.load_template(template)
                    end_time = time.perf_counter()
                    times.append(end_time - start_time)
                except Exception as e:
                    errors.append(str(e))
            
            if times:
                result = BenchmarkResult(
                    test_name=f"template_load_{template.replace('/', '_')}",
                    operation_type="template_loading",
                    iterations=len(times),
                    total_time=sum(times),
                    average_time=statistics.mean(times),
                    min_time=min(times),
                    max_time=max(times),
                    operations_per_second=len(times) / sum(times),
                    median_time=statistics.median(times),
                    std_dev=statistics.stdev(times) if len(times) > 1 else 0.0,
                    success_rate=(len(times) / 50) * 100,
                    errors=errors
                )
                self.results.append(result)
                print(f"  {template}: {result.average_time*1000:.1f}ms avg, {result.operations_per_second:.0f} ops/sec")
        
        # Test cache effectiveness
        times_cached = []
        for i in range(100):
            start_time = time.perf_counter()
            self.generator.template_loader.load_template("technical/srs")  # Should hit cache
            end_time = time.perf_counter()
            times_cached.append(end_time - start_time)
        
        result = BenchmarkResult(
            test_name="template_cache_effectiveness",
            operation_type="template_loading",
            iterations=len(times_cached),
            total_time=sum(times_cached),
            average_time=statistics.mean(times_cached),
            min_time=min(times_cached),
            max_time=max(times_cached),
            operations_per_second=len(times_cached) / sum(times_cached),
            median_time=statistics.median(times_cached),
            std_dev=statistics.stdev(times_cached)
        )
        self.results.append(result)
        print(f"  Cache effectiveness: {result.average_time*1000:.1f}ms avg, {result.operations_per_second:.0f} ops/sec")
    
    def _benchmark_content_processing(self):
        """Benchmark content processing performance.""" 
        print("\n⚙️  Content Processing Performance")
        print("-" * 40)
        
        processor = ContentProcessor()
        
        # Test different complexity levels
        for complexity, inputs in self.test_inputs.items():
            times = []
            errors = []
            
            # Simple template for testing
            template_content = """
# {{ title }}

Author: {{ author }}
Version: {{ version }}

## Overview
{{ overview }}

{% if requirements %}
## Requirements
{% for req in requirements %}
- **{{ req.id }}**: {{ req.title }} ({{ req.priority }})
  {{ req.description }}
{% endfor %}
{% endif %}

{% if features %}
## Features
{% for feature in features %}
- {{ feature }}
{% endfor %}
{% endif %}
"""
            
            for i in range(30):  # 30 iterations per complexity
                try:
                    start_time = time.perf_counter()
                    processor.process_content(template_content, inputs)
                    end_time = time.perf_counter()
                    times.append(end_time - start_time)
                except Exception as e:
                    errors.append(str(e))
            
            if times:
                result = BenchmarkResult(
                    test_name=f"content_processing_{complexity}",
                    operation_type="content_processing",
                    iterations=len(times),
                    total_time=sum(times),
                    average_time=statistics.mean(times),
                    min_time=min(times),
                    max_time=max(times),
                    operations_per_second=len(times) / sum(times),
                    median_time=statistics.median(times),
                    std_dev=statistics.stdev(times) if len(times) > 1 else 0.0,
                    success_rate=(len(times) / 30) * 100,
                    errors=errors
                )
                self.results.append(result)
                print(f"  {complexity} complexity: {result.average_time*1000:.1f}ms avg, {result.operations_per_second:.0f} ops/sec")
    
    def _benchmark_document_generation(self):
        """Benchmark end-to-end document generation."""
        print("\n📄 Document Generation Performance")
        print("-" * 40)
        
        config = GenerationConfig(save_to_storage=False)  # Skip storage for pure generation speed
        
        for template in self.templates:
            for complexity, inputs in self.test_inputs.items():
                times = []
                errors = []
                
                for i in range(20):  # 20 iterations per combination
                    try:
                        start_time = time.perf_counter()
                        result = self.generator.generate_document(template, inputs, config)
                        end_time = time.perf_counter()
                        
                        if result.success:
                            times.append(end_time - start_time)
                        else:
                            errors.append(result.error_message or "Unknown error")
                    except Exception as e:
                        errors.append(str(e))
                
                if times:
                    bench_result = BenchmarkResult(
                        test_name=f"generation_{template.replace('/', '_')}_{complexity}",
                        operation_type="document_generation",
                        iterations=len(times),
                        total_time=sum(times),
                        average_time=statistics.mean(times),
                        min_time=min(times),
                        max_time=max(times),
                        operations_per_second=len(times) / sum(times),
                        median_time=statistics.median(times),
                        std_dev=statistics.stdev(times) if len(times) > 1 else 0.0,
                        success_rate=(len(times) / 20) * 100,
                        errors=errors
                    )
                    self.results.append(bench_result)
                    print(f"  {template} ({complexity}): {bench_result.average_time*1000:.1f}ms avg, {bench_result.operations_per_second:.1f} docs/sec")
    
    def _benchmark_output_formatting(self):
        """Benchmark output formatting performance."""
        print("\n🎨 Output Formatting Performance") 
        print("-" * 40)
        
        # Test markdown and HTML formatting
        sample_content = """# Test Document

This is a test document with various **formatting** elements.

## Features
- Bullet point 1
- Bullet point 2
- Bullet point 3

## Code Example
```python
def hello_world():
    print("Hello, World!")
```

## Table
| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Value 1  | Value 2  | Value 3  |
| Value 4  | Value 5  | Value 6  |
"""
        
        # Test Markdown formatting
        from devdocai.generator.outputs.markdown import MarkdownOutput
        from devdocai.generator.core.template_loader import TemplateMetadata
        
        markdown_formatter = MarkdownOutput()
        html_formatter = self.generator.formatters["html"]
        
        test_metadata = TemplateMetadata(
            name="test",
            title="Test Document", 
            type="technical",
            category="test"
        )
        
        # Markdown formatting benchmark
        times = []
        for i in range(100):
            start_time = time.perf_counter()
            markdown_formatter.format_content(sample_content, test_metadata)
            end_time = time.perf_counter()
            times.append(end_time - start_time)
        
        result = BenchmarkResult(
            test_name="markdown_formatting",
            operation_type="output_formatting",
            iterations=len(times),
            total_time=sum(times),
            average_time=statistics.mean(times),
            min_time=min(times),
            max_time=max(times),
            operations_per_second=len(times) / sum(times),
            median_time=statistics.median(times),
            std_dev=statistics.stdev(times)
        )
        self.results.append(result)
        print(f"  Markdown: {result.average_time*1000:.1f}ms avg, {result.operations_per_second:.0f} ops/sec")
        
        # HTML formatting benchmark
        times = []
        for i in range(100):
            start_time = time.perf_counter()
            html_formatter.format_content(sample_content, test_metadata)
            end_time = time.perf_counter()
            times.append(end_time - start_time)
        
        result = BenchmarkResult(
            test_name="html_formatting",
            operation_type="output_formatting",
            iterations=len(times),
            total_time=sum(times),
            average_time=statistics.mean(times),
            min_time=min(times),
            max_time=max(times),
            operations_per_second=len(times) / sum(times),
            median_time=statistics.median(times),
            std_dev=statistics.stdev(times)
        )
        self.results.append(result)
        print(f"  HTML: {result.average_time*1000:.1f}ms avg, {result.operations_per_second:.0f} ops/sec")
    
    def _benchmark_concurrent_generation(self):
        """Benchmark concurrent document generation."""
        print("\n🔄 Concurrent Generation Performance")
        print("-" * 40)
        
        config = GenerationConfig(save_to_storage=False)
        
        # Test different concurrency levels
        for num_workers in [1, 2, 4, 8, 16]:
            times = []
            
            def generate_document():
                start_time = time.perf_counter()
                result = self.generator.generate_document("technical/srs", self.test_inputs["medium"], config)
                end_time = time.perf_counter()
                return end_time - start_time, result.success
            
            # Run concurrent generations
            start_time = time.perf_counter()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
                futures = [executor.submit(generate_document) for _ in range(num_workers * 2)]  # 2x workers for testing
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            end_time = time.perf_counter()
            
            individual_times = [r[0] for r in results]
            successes = [r[1] for r in results]
            total_time = end_time - start_time
            
            result = BenchmarkResult(
                test_name=f"concurrent_generation_{num_workers}_workers",
                operation_type="concurrent_generation",
                iterations=len(results),
                total_time=total_time,
                average_time=statistics.mean(individual_times),
                min_time=min(individual_times),
                max_time=max(individual_times),
                operations_per_second=len(results) / total_time,
                median_time=statistics.median(individual_times),
                std_dev=statistics.stdev(individual_times) if len(individual_times) > 1 else 0.0,
                success_rate=(sum(successes) / len(successes)) * 100
            )
            self.results.append(result)
            print(f"  {num_workers} workers: {result.operations_per_second:.1f} docs/sec, {result.average_time*1000:.1f}ms avg latency")
    
    def _benchmark_batch_operations(self):
        """Benchmark batch operation capabilities (current baseline)."""
        print("\n📦 Batch Operations Baseline")
        print("-" * 40)
        
        # Current implementation doesn't have batch operations
        # This establishes baseline for individual operations
        
        config = GenerationConfig(save_to_storage=False)
        
        # Generate multiple documents sequentially
        num_docs = 10
        start_time = time.perf_counter()
        
        successful = 0
        for i in range(num_docs):
            result = self.generator.generate_document("project/readme", self.test_inputs["simple"], config)
            if result.success:
                successful += 1
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        result = BenchmarkResult(
            test_name="sequential_batch_baseline",
            operation_type="batch_operations",
            iterations=num_docs,
            total_time=total_time,
            average_time=total_time / num_docs,
            min_time=total_time / num_docs,  # Approximation
            max_time=total_time / num_docs,  # Approximation 
            operations_per_second=successful / total_time,
            median_time=total_time / num_docs,
            std_dev=0.0,
            success_rate=(successful / num_docs) * 100
        )
        self.results.append(result)
        print(f"  Sequential ({num_docs} docs): {result.operations_per_second:.1f} docs/sec")
    
    def _benchmark_memory_usage(self):
        """Benchmark memory usage patterns."""
        print("\n💾 Memory Usage Analysis")
        print("-" * 40)
        
        import psutil
        import gc
        
        process = psutil.Process()
        
        # Baseline memory
        gc.collect()
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Generate multiple large documents
        config = GenerationConfig(save_to_storage=False)
        
        start_time = time.perf_counter()
        for i in range(5):  # 5 large documents
            self.generator.generate_document("technical/srs", self.test_inputs["large"], config)
        end_time = time.perf_counter()
        
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - baseline_memory
        
        # Clean up and measure final memory
        gc.collect()
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_retained = final_memory - baseline_memory
        
        result = BenchmarkResult(
            test_name="memory_usage_analysis",
            operation_type="memory_usage",
            iterations=5,
            total_time=end_time - start_time,
            average_time=(end_time - start_time) / 5,
            min_time=0,
            max_time=0,
            operations_per_second=5 / (end_time - start_time),
            median_time=(end_time - start_time) / 5,
            std_dev=0.0,
            memory_usage_mb=peak_memory,
            success_rate=100.0
        )
        self.results.append(result)
        
        print(f"  Baseline memory: {baseline_memory:.1f} MB")
        print(f"  Peak memory: {peak_memory:.1f} MB")
        print(f"  Memory increase: {memory_increase:.1f} MB")
        print(f"  Memory retained: {memory_retained:.1f} MB")
    
    def _benchmark_cache_performance(self):
        """Benchmark caching effectiveness."""
        print("\n🗄️  Cache Performance Analysis")
        print("-" * 40)
        
        # Clear cache and measure cold performance
        self.generator.template_loader.clear_cache()
        
        cold_times = []
        for i in range(10):
            start_time = time.perf_counter()
            self.generator.template_loader.load_template("technical/srs")
            end_time = time.perf_counter()
            cold_times.append(end_time - start_time)
            # Clear cache after each to ensure cold load
            self.generator.template_loader.clear_cache()
        
        # Measure warm performance (cache hits)
        warm_times = []
        for i in range(50):
            start_time = time.perf_counter()
            self.generator.template_loader.load_template("technical/srs")
            end_time = time.perf_counter()
            warm_times.append(end_time - start_time)
        
        cache_improvement = statistics.mean(cold_times) / statistics.mean(warm_times)
        
        cold_result = BenchmarkResult(
            test_name="cache_cold_performance",
            operation_type="caching",
            iterations=len(cold_times),
            total_time=sum(cold_times),
            average_time=statistics.mean(cold_times),
            min_time=min(cold_times),
            max_time=max(cold_times),
            operations_per_second=len(cold_times) / sum(cold_times),
            median_time=statistics.median(cold_times),
            std_dev=statistics.stdev(cold_times)
        )
        self.results.append(cold_result)
        
        warm_result = BenchmarkResult(
            test_name="cache_warm_performance",
            operation_type="caching",
            iterations=len(warm_times),
            total_time=sum(warm_times),
            average_time=statistics.mean(warm_times),
            min_time=min(warm_times),
            max_time=max(warm_times),
            operations_per_second=len(warm_times) / sum(warm_times),
            median_time=statistics.median(warm_times),
            std_dev=statistics.stdev(warm_times)
        )
        self.results.append(warm_result)
        
        print(f"  Cold cache: {cold_result.average_time*1000:.1f}ms avg")
        print(f"  Warm cache: {warm_result.average_time*1000:.1f}ms avg")
        print(f"  Cache improvement: {cache_improvement:.1f}x faster")
    
    def _benchmark_full_workflow(self):
        """Benchmark complete end-to-end workflow."""
        print("\n🔄 Full Workflow Performance")
        print("-" * 40)
        
        config = GenerationConfig(
            save_to_storage=True,
            include_metadata=True,
            validate_inputs=True
        )
        
        times = []
        errors = []
        
        for i in range(10):  # 10 full workflows
            try:
                start_time = time.perf_counter()
                result = self.generator.generate_document("technical/prd", self.test_inputs["medium"], config)
                end_time = time.perf_counter()
                
                if result.success:
                    times.append(end_time - start_time)
                else:
                    errors.append(result.error_message or "Unknown error")
            except Exception as e:
                errors.append(str(e))
        
        if times:
            result = BenchmarkResult(
                test_name="full_workflow_e2e",
                operation_type="end_to_end",
                iterations=len(times),
                total_time=sum(times),
                average_time=statistics.mean(times),
                min_time=min(times),
                max_time=max(times),
                operations_per_second=len(times) / sum(times),
                median_time=statistics.median(times),
                std_dev=statistics.stdev(times) if len(times) > 1 else 0.0,
                success_rate=(len(times) / 10) * 100,
                errors=errors
            )
            self.results.append(result)
            print(f"  End-to-end: {result.average_time*1000:.1f}ms avg, {result.operations_per_second:.1f} docs/sec")
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate performance summary."""
        summary = {}
        
        # Group results by operation type
        by_operation = {}
        for result in self.results:
            if result.operation_type not in by_operation:
                by_operation[result.operation_type] = []
            by_operation[result.operation_type].append(result)
        
        # Calculate summaries for each operation type
        for operation_type, results in by_operation.items():
            avg_times = [r.average_time for r in results]
            ops_per_sec = [r.operations_per_second for r in results]
            success_rates = [r.success_rate for r in results]
            
            summary[operation_type] = {
                "count": len(results),
                "avg_time_ms": statistics.mean(avg_times) * 1000,
                "min_time_ms": min(avg_times) * 1000,
                "max_time_ms": max(avg_times) * 1000,
                "avg_ops_per_sec": statistics.mean(ops_per_sec),
                "max_ops_per_sec": max(ops_per_sec),
                "avg_success_rate": statistics.mean(success_rates),
                "total_errors": sum(len(r.errors) for r in results)
            }
        
        # Overall statistics
        all_avg_times = [r.average_time for r in self.results]
        all_ops_per_sec = [r.operations_per_second for r in self.results]
        
        summary["overall"] = {
            "total_tests": len(self.results),
            "avg_time_ms": statistics.mean(all_avg_times) * 1000,
            "fastest_test_ms": min(all_avg_times) * 1000,
            "slowest_test_ms": max(all_avg_times) * 1000,
            "max_throughput": max(all_ops_per_sec),
            "total_errors": sum(len(r.errors) for r in self.results)
        }
        
        return summary
    
    def _save_results(self, results: Dict[str, Any]):
        """Save benchmark results to file."""
        results_dir = Path("claudedocs/benchmarks")
        results_dir.mkdir(exist_ok=True, parents=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = results_dir / f"m004_pass2_baseline_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Results saved to: {results_file}")
    
    def _print_summary(self, results: Dict[str, Any]):
        """Print benchmark summary."""
        summary = results["summary"]
        
        print("\n" + "=" * 80)
        print("📊 M004 PASS 2 BASELINE PERFORMANCE SUMMARY")
        print("=" * 80)
        
        print(f"\n📈 Overall Statistics:")
        print(f"  Total Tests: {summary['overall']['total_tests']}")
        print(f"  Average Time: {summary['overall']['avg_time_ms']:.1f}ms")
        print(f"  Fastest Test: {summary['overall']['fastest_test_ms']:.1f}ms")
        print(f"  Slowest Test: {summary['overall']['slowest_test_ms']:.1f}ms")
        print(f"  Max Throughput: {summary['overall']['max_throughput']:.1f} ops/sec")
        print(f"  Total Errors: {summary['overall']['total_errors']}")
        
        print(f"\n🎯 Performance Targets Analysis:")
        
        # Template loading analysis
        if "template_loading" in summary:
            tl = summary["template_loading"]
            target_met = "✅" if tl["avg_time_ms"] < 50 else "❌"
            print(f"  Template Loading: {tl['avg_time_ms']:.1f}ms avg {target_met} (Target: <50ms)")
        
        # Document generation analysis
        if "document_generation" in summary:
            dg = summary["document_generation"]
            target_met = "✅" if dg["avg_ops_per_sec"] > 50 else "❌"
            print(f"  Document Generation: {dg['avg_ops_per_sec']:.1f} docs/sec {target_met} (Target: >50 docs/sec)")
        
        # Concurrent generation analysis
        if "concurrent_generation" in summary:
            cg = summary["concurrent_generation"]
            target_met = "✅" if cg["max_ops_per_sec"] > 100 else "❌"
            print(f"  Concurrent Generation: {cg['max_ops_per_sec']:.1f} docs/sec {target_met} (Target: >100 docs/sec)")
        
        print(f"\n🔍 Key Optimization Opportunities:")
        optimization_opportunities = []
        
        if "template_loading" in summary and summary["template_loading"]["avg_time_ms"] > 50:
            optimization_opportunities.append("Template loading needs optimization (>50ms)")
        
        if "document_generation" in summary and summary["document_generation"]["avg_ops_per_sec"] < 50:
            optimization_opportunities.append("Document generation throughput needs improvement (<50 docs/sec)")
        
        if "concurrent_generation" in summary and summary["concurrent_generation"]["max_ops_per_sec"] < 100:
            optimization_opportunities.append("Concurrent generation needs improvement (<100 docs/sec)")
        
        if not optimization_opportunities:
            optimization_opportunities.append("Current performance meets Pass 2 targets!")
        
        for i, opportunity in enumerate(optimization_opportunities, 1):
            print(f"  {i}. {opportunity}")


if __name__ == "__main__":
    benchmark = M004PerformanceBenchmark()
    results = benchmark.run_all_benchmarks()
    
    # Exit with appropriate code
    if results["summary"]["overall"]["total_errors"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)