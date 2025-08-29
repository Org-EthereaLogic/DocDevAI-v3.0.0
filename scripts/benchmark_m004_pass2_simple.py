#!/usr/bin/env python3
"""
M004 Document Generator - Pass 2 Simple Performance Benchmark

Streamlined benchmark focusing on core performance metrics with correct template inputs.
"""

import sys
import time
import statistics
import concurrent.futures
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import json
import psutil
import gc

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from devdocai.generator.core.engine import DocumentGenerator, GenerationConfig
from devdocai.core.config import ConfigurationManager
from devdocai.storage import LocalStorageSystem


class SimpleM004Benchmark:
    """Streamlined M004 performance benchmark."""
    
    def __init__(self):
        """Initialize benchmark."""
        self.config_manager = ConfigurationManager()
        self.storage_system = LocalStorageSystem()
        self.generator = DocumentGenerator(self.config_manager, self.storage_system)
        
        # Correct test inputs matching actual templates
        self.test_inputs = {
            "srs": {
                "project_name": "DocDevAI System",
                "system_name": "Document Generation Engine",
                "purpose": "Automated generation of technical documentation for software projects",
                "scope": "Core document generation functionality including templates, content processing, and output formatting",
                "functional_requirements": [
                    {"id": "FR-001", "title": "Template Loading", "description": "System shall load Jinja2 templates with metadata"},
                    {"id": "FR-002", "title": "Content Processing", "description": "System shall process template variables and generate output"},
                    {"id": "FR-003", "title": "Format Support", "description": "System shall support markdown and HTML output formats"}
                ]
            },
            "readme": {
                "project_name": "DevDocAI v3.0.0",
                "description": "AI-powered documentation generation and analysis system for software developers",
                "installation": "pip install devdocai",
                "usage": "Use DevDocAI CLI or integrate into your development workflow",
                "features": ["Document Generation", "Template System", "Multi-format Output", "Performance Optimized"]
            }
        }
    
    def run_benchmark(self) -> Dict[str, Any]:
        """Run performance benchmark."""
        print("🚀 M004 Document Generator - Pass 2 Baseline Performance")
        print("=" * 60)
        
        results = {}
        start_time = time.time()
        
        # 1. Template Loading Performance
        print("\n📁 Template Loading Performance")
        results["template_loading"] = self._benchmark_template_loading()
        
        # 2. Document Generation Performance
        print("\n📄 Document Generation Performance")
        results["document_generation"] = self._benchmark_document_generation()
        
        # 3. Concurrent Performance
        print("\n🔄 Concurrent Performance")
        results["concurrent_performance"] = self._benchmark_concurrent_generation()
        
        # 4. Memory Usage
        print("\n💾 Memory Usage")
        results["memory_usage"] = self._benchmark_memory_usage()
        
        # 5. Output Formatting
        print("\n🎨 Output Formatting")
        results["output_formatting"] = self._benchmark_output_formatting()
        
        total_time = time.time() - start_time
        
        # Compile final results
        final_results = {
            "benchmark_info": {
                "version": "M004 Pass 2 Baseline",
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": total_time
            },
            "results": results,
            "performance_analysis": self._analyze_performance(results)
        }
        
        self._print_summary(final_results)
        self._save_results(final_results)
        
        return final_results
    
    def _benchmark_template_loading(self) -> Dict[str, float]:
        """Benchmark template loading speed."""
        templates = ["technical/srs", "project/readme"]
        results = {}
        
        for template in templates:
            # Clear cache first
            self.generator.template_loader.clear_cache()
            
            # Cold loading times
            cold_times = []
            for _ in range(10):
                start = time.perf_counter()
                self.generator.template_loader.load_template(template)
                end = time.perf_counter()
                cold_times.append(end - start)
                self.generator.template_loader.clear_cache()
            
            # Warm loading times (cached)
            warm_times = []
            for _ in range(50):
                start = time.perf_counter()
                self.generator.template_loader.load_template(template)
                end = time.perf_counter()
                warm_times.append(end - start)
            
            template_key = template.replace('/', '_')
            cold_avg = statistics.mean(cold_times) * 1000  # Convert to ms
            warm_avg = statistics.mean(warm_times) * 1000  # Convert to ms
            
            results[f"{template_key}_cold_ms"] = cold_avg
            results[f"{template_key}_warm_ms"] = warm_avg
            results[f"{template_key}_cache_improvement"] = cold_avg / warm_avg if warm_avg > 0 else 1.0
            
            print(f"  {template}: Cold={cold_avg:.1f}ms, Warm={warm_avg:.1f}ms, Improvement={cold_avg/warm_avg:.1f}x")
        
        return results
    
    def _benchmark_document_generation(self) -> Dict[str, float]:
        """Benchmark document generation performance."""
        config = GenerationConfig(save_to_storage=False, validate_inputs=False)
        results = {}
        
        test_cases = [
            ("technical/srs", self.test_inputs["srs"]),
            ("project/readme", self.test_inputs["readme"])
        ]
        
        for template, inputs in test_cases:
            times = []
            
            for _ in range(25):  # 25 iterations
                start = time.perf_counter()
                result = self.generator.generate_document(template, inputs, config)
                end = time.perf_counter()
                
                if result.success:
                    times.append(end - start)
            
            if times:
                template_key = template.replace('/', '_')
                avg_time_ms = statistics.mean(times) * 1000
                ops_per_sec = 1.0 / statistics.mean(times)
                
                results[f"{template_key}_avg_ms"] = avg_time_ms
                results[f"{template_key}_ops_per_sec"] = ops_per_sec
                results[f"{template_key}_min_ms"] = min(times) * 1000
                results[f"{template_key}_max_ms"] = max(times) * 1000
                
                print(f"  {template}: {avg_time_ms:.1f}ms avg, {ops_per_sec:.1f} docs/sec")
        
        return results
    
    def _benchmark_concurrent_generation(self) -> Dict[str, float]:
        """Benchmark concurrent document generation."""
        config = GenerationConfig(save_to_storage=False, validate_inputs=False)
        results = {}
        
        def generate_doc():
            start = time.perf_counter()
            result = self.generator.generate_document("project/readme", self.test_inputs["readme"], config)
            end = time.perf_counter()
            return (end - start, result.success)
        
        # Test different concurrency levels
        for workers in [1, 2, 4, 8]:
            num_tasks = workers * 3  # 3x workers for testing
            
            start_time = time.perf_counter()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [executor.submit(generate_doc) for _ in range(num_tasks)]
                task_results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            end_time = time.perf_counter()
            
            # Calculate metrics
            individual_times = [r[0] for r in task_results if r[1]]  # Only successful
            total_time = end_time - start_time
            throughput = len(individual_times) / total_time
            avg_latency_ms = statistics.mean(individual_times) * 1000 if individual_times else 0
            
            results[f"workers_{workers}_throughput"] = throughput
            results[f"workers_{workers}_avg_latency_ms"] = avg_latency_ms
            results[f"workers_{workers}_total_time"] = total_time
            
            print(f"  {workers} workers: {throughput:.1f} docs/sec, {avg_latency_ms:.1f}ms avg latency")
        
        return results
    
    def _benchmark_memory_usage(self) -> Dict[str, float]:
        """Benchmark memory usage patterns."""
        process = psutil.Process()
        config = GenerationConfig(save_to_storage=False, validate_inputs=False)
        
        # Baseline memory
        gc.collect()
        baseline_mb = process.memory_info().rss / (1024 * 1024)
        
        # Generate several documents
        for i in range(10):
            self.generator.generate_document("technical/srs", self.test_inputs["srs"], config)
        
        # Peak memory
        peak_mb = process.memory_info().rss / (1024 * 1024)
        
        # Clear caches and collect garbage
        self.generator.template_loader.clear_cache()
        gc.collect()
        
        # Final memory
        final_mb = process.memory_info().rss / (1024 * 1024)
        
        results = {
            "baseline_mb": baseline_mb,
            "peak_mb": peak_mb,
            "final_mb": final_mb,
            "memory_increase_mb": peak_mb - baseline_mb,
            "memory_retained_mb": final_mb - baseline_mb
        }
        
        print(f"  Baseline: {baseline_mb:.1f}MB")
        print(f"  Peak: {peak_mb:.1f}MB (+{peak_mb-baseline_mb:.1f}MB)")
        print(f"  Final: {final_mb:.1f}MB (+{final_mb-baseline_mb:.1f}MB retained)")
        
        return results
    
    def _benchmark_output_formatting(self) -> Dict[str, float]:
        """Benchmark output formatting performance."""
        from devdocai.generator.outputs.markdown import MarkdownOutput
        from devdocai.generator.core.template_loader import TemplateMetadata
        
        # Sample content for formatting
        content = """# Test Document

This is a test document with various **formatting** elements and [links](http://example.com).

## Features
- Feature 1
- Feature 2  
- Feature 3

## Code
```python
def test():
    return "hello world"
```

## Table
| Column 1 | Column 2 |
|----------|----------|
| Value 1  | Value 2  |
"""
        
        test_metadata = TemplateMetadata(
            name="test",
            title="Test Document",
            type="technical", 
            category="test"
        )
        
        # Markdown formatting
        markdown_formatter = MarkdownOutput()
        times = []
        
        for _ in range(100):
            start = time.perf_counter()
            markdown_formatter.format_content(content, test_metadata)
            end = time.perf_counter()
            times.append(end - start)
        
        markdown_avg_ms = statistics.mean(times) * 1000
        markdown_ops_per_sec = 1.0 / statistics.mean(times)
        
        # HTML formatting  
        html_formatter = self.generator.formatters["html"]
        times = []
        
        for _ in range(100):
            start = time.perf_counter()
            html_formatter.format_content(content, test_metadata)
            end = time.perf_counter()
            times.append(end - start)
        
        html_avg_ms = statistics.mean(times) * 1000
        html_ops_per_sec = 1.0 / statistics.mean(times)
        
        results = {
            "markdown_avg_ms": markdown_avg_ms,
            "markdown_ops_per_sec": markdown_ops_per_sec,
            "html_avg_ms": html_avg_ms, 
            "html_ops_per_sec": html_ops_per_sec
        }
        
        print(f"  Markdown: {markdown_avg_ms:.1f}ms avg, {markdown_ops_per_sec:.0f} ops/sec")
        print(f"  HTML: {html_avg_ms:.1f}ms avg, {html_ops_per_sec:.0f} ops/sec")
        
        return results
    
    def _analyze_performance(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze performance against Pass 2 targets."""
        analysis = {
            "pass_2_targets": {
                "template_loading_target_ms": 50,
                "document_generation_target_ops_sec": 50,
                "concurrent_generation_target_ops_sec": 100
            },
            "current_performance": {},
            "target_status": {},
            "optimization_opportunities": []
        }
        
        # Template loading analysis
        tl = results.get("template_loading", {})
        avg_cold_ms = (tl.get("technical_srs_cold_ms", 0) + tl.get("project_readme_cold_ms", 0)) / 2
        avg_warm_ms = (tl.get("technical_srs_warm_ms", 0) + tl.get("project_readme_warm_ms", 0)) / 2
        
        analysis["current_performance"]["template_loading_cold_ms"] = avg_cold_ms
        analysis["current_performance"]["template_loading_warm_ms"] = avg_warm_ms
        analysis["target_status"]["template_loading"] = "✅" if avg_cold_ms < 50 else "❌"
        
        if avg_cold_ms >= 50:
            analysis["optimization_opportunities"].append("Template loading optimization needed")
        
        # Document generation analysis
        dg = results.get("document_generation", {})
        avg_ops_per_sec = (dg.get("technical_srs_ops_per_sec", 0) + dg.get("project_readme_ops_per_sec", 0)) / 2
        
        analysis["current_performance"]["document_generation_ops_sec"] = avg_ops_per_sec
        analysis["target_status"]["document_generation"] = "✅" if avg_ops_per_sec > 50 else "❌"
        
        if avg_ops_per_sec <= 50:
            analysis["optimization_opportunities"].append("Document generation throughput needs improvement")
        
        # Concurrent performance analysis
        cp = results.get("concurrent_performance", {})
        max_throughput = max([cp.get(f"workers_{w}_throughput", 0) for w in [1, 2, 4, 8]])
        
        analysis["current_performance"]["max_concurrent_throughput"] = max_throughput
        analysis["target_status"]["concurrent_performance"] = "✅" if max_throughput > 100 else "❌"
        
        if max_throughput <= 100:
            analysis["optimization_opportunities"].append("Concurrent processing optimization needed")
        
        # Memory analysis
        mem = results.get("memory_usage", {})
        memory_per_doc_mb = mem.get("memory_increase_mb", 0) / 10  # 10 docs generated
        
        analysis["current_performance"]["memory_per_document_mb"] = memory_per_doc_mb
        analysis["target_status"]["memory_usage"] = "✅" if memory_per_doc_mb < 5 else "❌"
        
        if memory_per_doc_mb >= 5:
            analysis["optimization_opportunities"].append("Memory usage optimization recommended")
        
        return analysis
    
    def _print_summary(self, results: Dict[str, Any]):
        """Print performance summary."""
        analysis = results["performance_analysis"]
        
        print("\n" + "=" * 60)
        print("📊 M004 PASS 2 BASELINE PERFORMANCE SUMMARY")
        print("=" * 60)
        
        print("\n🎯 Performance Targets vs Current Performance:")
        
        current = analysis["current_performance"]
        targets = analysis["pass_2_targets"]
        status = analysis["target_status"]
        
        print(f"  Template Loading: {current.get('template_loading_cold_ms', 0):.1f}ms {status.get('template_loading', '❓')} (Target: <{targets['template_loading_target_ms']}ms)")
        print(f"  Document Generation: {current.get('document_generation_ops_sec', 0):.1f} docs/sec {status.get('document_generation', '❓')} (Target: >{targets['document_generation_target_ops_sec']} docs/sec)")
        print(f"  Max Concurrent: {current.get('max_concurrent_throughput', 0):.1f} docs/sec {status.get('concurrent_performance', '❓')} (Target: >{targets['concurrent_generation_target_ops_sec']} docs/sec)")
        print(f"  Memory per Doc: {current.get('memory_per_document_mb', 0):.2f}MB {status.get('memory_usage', '❓')} (Target: <5MB)")
        
        print("\n🔍 Optimization Opportunities:")
        opportunities = analysis["optimization_opportunities"]
        if not opportunities:
            print("  ✅ All performance targets met!")
        else:
            for i, opportunity in enumerate(opportunities, 1):
                print(f"  {i}. {opportunity}")
        
        print(f"\n⏱️  Total Benchmark Time: {results['benchmark_info']['duration_seconds']:.1f}s")
    
    def _save_results(self, results: Dict[str, Any]):
        """Save results to file."""
        results_dir = Path("claudedocs/benchmarks")
        results_dir.mkdir(exist_ok=True, parents=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = results_dir / f"m004_pass2_baseline_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Results saved to: {filename}")


if __name__ == "__main__":
    benchmark = SimpleM004Benchmark()
    results = benchmark.run_benchmark()
    
    # Exit code based on performance
    analysis = results["performance_analysis"]
    failed_targets = [k for k, v in analysis["target_status"].items() if v == "❌"]
    
    if failed_targets:
        print(f"\n⚠️  {len(failed_targets)} performance targets not met - optimization needed for Pass 2")
        sys.exit(0)  # Still success - this is baseline measurement
    else:
        print("\n✅ All performance targets exceeded - ready for advanced optimizations!")
        sys.exit(0)