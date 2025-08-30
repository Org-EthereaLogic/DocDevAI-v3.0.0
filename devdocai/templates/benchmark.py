#!/usr/bin/env python3
"""
Performance benchmark suite for M006 Template Registry.

This module provides comprehensive performance benchmarks to measure
and validate optimization improvements for Pass 2.
"""

import time
import random
import string
import statistics
import gc
import tracemalloc
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime
import json
import tempfile
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..core.config import ConfigurationManager
from .registry import TemplateRegistry
from .models import (
    TemplateMetadata,
    TemplateCategory,
    TemplateType,
    TemplateSearchCriteria
)


class TemplateBenchmark:
    """Performance benchmark suite for Template Registry."""
    
    def __init__(self, verbose: bool = True):
        """Initialize benchmark suite."""
        self.verbose = verbose
        self.results: Dict[str, Any] = {}
        self.temp_dir = None
        
    def setup(self):
        """Setup benchmark environment."""
        # Create temporary directory for test templates
        self.temp_dir = tempfile.mkdtemp(prefix="template_bench_")
        
        # Initialize registry without auto-loading defaults
        self.registry = TemplateRegistry(auto_load_defaults=False)
        
        # Generate test templates
        self._generate_test_templates()
        
    def teardown(self):
        """Cleanup benchmark environment."""
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
        
        if hasattr(self, 'registry'):
            self.registry.shutdown()
    
    def _generate_test_templates(self):
        """Generate test templates for benchmarking."""
        # Create various sizes of templates
        self.test_templates = {
            'small': self._create_template_content(100),     # 100 lines
            'medium': self._create_template_content(500),    # 500 lines
            'large': self._create_template_content(2000),    # 2000 lines
            'complex': self._create_complex_template()       # With loops and conditions
        }
        
        # Create template files
        for name, content in self.test_templates.items():
            file_path = Path(self.temp_dir) / f"{name}_template.json"
            template_data = {
                "id": f"{name}_template",
                "name": f"{name.capitalize()} Template",
                "description": f"Test {name} template for benchmarking",
                "category": "documentation",
                "type": "reference_guide",
                "version": "1.0.0",
                "template": content,
                "variables": [
                    {"name": f"var_{i}", "description": f"Variable {i}", "required": False, "default": f"default_{i}"}
                    for i in range(10)
                ]
            }
            with open(file_path, 'w') as f:
                json.dump(template_data, f)
    
    def _create_template_content(self, lines: int) -> str:
        """Create template content with specified number of lines."""
        content = []
        for i in range(lines):
            if i % 10 == 0:
                content.append(f"## Section {i//10}")
            elif i % 5 == 0:
                content.append(f"Variable {{{{var_{i%10}}}}}")
            else:
                content.append(f"Line {i}: " + " ".join(random.choices(string.ascii_lowercase, k=10)))
        return "\n".join(content)
    
    def _create_complex_template(self) -> str:
        """Create a complex template with various features."""
        return """
# Complex Template

## Introduction
This is a {{project_name}} documentation.

<!-- IF has_api -->
## API Documentation
The API provides {{api_count}} endpoints.

<!-- FOR endpoint IN endpoints -->
### {{endpoint.name}}
Method: {{endpoint.method}}
Path: {{endpoint.path}}
<!-- END FOR -->
<!-- END IF -->

<!-- SECTION: optional_section -->
## Optional Content
This section is {{section_status}}.
<!-- END SECTION: optional_section -->

## Variables Test
- Simple: {{simple_var}}
- Nested: {{user.name}} ({{user.email}})
- Default: {{optional_var}}

<!-- FOR item IN items -->
- Item: {{item}}
<!-- END FOR -->

## Conclusion
Generated on {{date}} by {{author}}.
"""
    
    def benchmark_single_template_loading(self, iterations: int = 100) -> Dict[str, float]:
        """Benchmark single template loading performance."""
        self._print("Benchmarking single template loading...")
        
        file_path = Path(self.temp_dir) / "small_template.json"
        times = []
        
        for _ in range(iterations):
            # Clear any caches
            if hasattr(self.registry.loader, 'clear_cache'):
                self.registry.loader.clear_cache()
            
            start = time.perf_counter()
            self.registry.import_template(file_path)
            end = time.perf_counter()
            
            times.append((end - start) * 1000)  # Convert to ms
        
        return {
            'min_ms': min(times),
            'max_ms': max(times),
            'mean_ms': statistics.mean(times),
            'median_ms': statistics.median(times),
            'stddev_ms': statistics.stdev(times) if len(times) > 1 else 0
        }
    
    def benchmark_batch_loading(self, template_count: int = 100) -> Dict[str, Any]:
        """Benchmark batch template loading."""
        self._print(f"Benchmarking batch loading of {template_count} templates...")
        
        # Create multiple template files
        template_files = []
        for i in range(template_count):
            file_path = Path(self.temp_dir) / f"batch_template_{i}.json"
            template_data = {
                "id": f"batch_template_{i}",
                "name": f"Batch Template {i}",
                "description": f"Test batch template {i}",
                "category": "documentation",
                "type": "reference_guide",
                "template": f"Template content for batch {i}\nVariable: {{{{var_{i}}}}}",
                "variables": [{"name": f"var_{i}", "required": False}]
            }
            with open(file_path, 'w') as f:
                json.dump(template_data, f)
            template_files.append(file_path)
        
        # Measure batch loading
        start = time.perf_counter()
        for file_path in template_files:
            self.registry.import_template(file_path)
        end = time.perf_counter()
        
        total_time = end - start
        templates_per_second = template_count / total_time
        
        return {
            'total_templates': template_count,
            'total_time_sec': total_time,
            'templates_per_second': templates_per_second,
            'avg_ms_per_template': (total_time * 1000) / template_count
        }
    
    def benchmark_variable_substitution(self, iterations: int = 1000) -> Dict[str, Any]:
        """Benchmark variable substitution performance."""
        self._print("Benchmarking variable substitution...")
        
        # Create template with many variables
        template_id = "var_test_template"
        content = "\n".join([f"Line {{{{var_{i}}}}}" for i in range(50)])
        
        metadata = TemplateMetadata(
            id=template_id,
            name="Variable Test",
            description="Template for variable substitution benchmark",
            category=TemplateCategory.DOCUMENTATION,
            type=TemplateType.REFERENCE_GUIDE
        )
        
        variables = [{"name": f"var_{i}", "required": False, "default": f"value_{i}"} 
                    for i in range(50)]
        
        template = self.registry.create_template(
            metadata=metadata,
            content=content,
            variables=variables,
            validate=False
        )
        
        # Create context with all variables
        context = {f"var_{i}": f"substituted_{i}" for i in range(50)}
        
        times = []
        for _ in range(iterations):
            # Clear cache to measure actual substitution
            template.clear_cache()
            
            start = time.perf_counter()
            result = self.registry.render_template(template_id, context, validate_context=False)
            end = time.perf_counter()
            
            times.append((end - start) * 1000)  # Convert to ms
        
        return {
            'iterations': iterations,
            'variables_per_template': 50,
            'min_ms': min(times),
            'max_ms': max(times),
            'mean_ms': statistics.mean(times),
            'median_ms': statistics.median(times)
        }
    
    def benchmark_template_rendering(self, iterations: int = 100) -> Dict[str, Any]:
        """Benchmark template rendering performance."""
        self._print("Benchmarking template rendering...")
        
        # Create complex template
        template_id = "complex_render"
        metadata = TemplateMetadata(
            id=template_id,
            name="Complex Render Test",
            description="Complex template for rendering benchmark",
            category=TemplateCategory.DOCUMENTATION,
            type=TemplateType.REFERENCE_GUIDE
        )
        
        template = self.registry.create_template(
            metadata=metadata,
            content=self._create_complex_template(),
            validate=False
        )
        
        # Create complex context
        context = {
            'project_name': 'BenchmarkProject',
            'has_api': True,
            'api_count': 25,
            'loop_endpoints': [  # Changed to loop_endpoints to match the FOR loop syntax
                {'name': f'Endpoint{i}', 'method': 'GET', 'path': f'/api/v1/endpoint{i}'}
                for i in range(10)
            ],
            'section_optional_section': True,
            'section_status': 'enabled',
            'simple_var': 'Simple Value',
            'user': {'name': 'Test User', 'email': 'test@example.com'},
            'optional_var': 'Optional Value',
            'loop_items': [f'Item {i}' for i in range(20)],
            'date': datetime.now().isoformat(),
            'author': 'Benchmark Suite'
        }
        
        times = []
        for _ in range(iterations):
            template.clear_cache()
            
            start = time.perf_counter()
            result = self.registry.render_template(template_id, context, validate_context=False)
            end = time.perf_counter()
            
            times.append((end - start) * 1000)
        
        # Calculate documents per second
        avg_time_sec = statistics.mean(times) / 1000
        docs_per_second = 1 / avg_time_sec if avg_time_sec > 0 else 0
        
        return {
            'iterations': iterations,
            'min_ms': min(times),
            'max_ms': max(times),
            'mean_ms': statistics.mean(times),
            'median_ms': statistics.median(times),
            'docs_per_second': docs_per_second
        }
    
    def benchmark_memory_usage(self, template_count: int = 1000) -> Dict[str, Any]:
        """Benchmark memory usage for template caching."""
        self._print(f"Benchmarking memory usage with {template_count} templates...")
        
        # Start memory tracking
        tracemalloc.start()
        gc.collect()
        
        # Get baseline memory
        baseline = tracemalloc.get_traced_memory()[0]
        
        # Create and load many templates
        for i in range(template_count):
            metadata = TemplateMetadata(
                id=f"mem_template_{i}",
                name=f"Memory Template {i}",
                description=f"Template {i} for memory benchmark",
                category=TemplateCategory.DOCUMENTATION,
                type=TemplateType.REFERENCE_GUIDE
            )
            
            content = self._create_template_content(100)  # Small templates
            
            self.registry.create_template(
                metadata=metadata,
                content=content,
                validate=False
            )
        
        # Get peak memory
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        memory_used_mb = (current - baseline) / (1024 * 1024)
        peak_memory_mb = peak / (1024 * 1024)
        avg_per_template_kb = (current - baseline) / (1024 * template_count)
        
        return {
            'template_count': template_count,
            'memory_used_mb': memory_used_mb,
            'peak_memory_mb': peak_memory_mb,
            'avg_per_template_kb': avg_per_template_kb,
            'within_limit': memory_used_mb < 100  # Target: < 100MB for 1000 templates
        }
    
    def benchmark_search_operations(self, template_count: int = 1000) -> Dict[str, Any]:
        """Benchmark search and filter operations."""
        self._print(f"Benchmarking search with {template_count} templates...")
        
        # Create templates with various categories and tags
        categories = list(TemplateCategory)
        for i in range(template_count):
            metadata = TemplateMetadata(
                id=f"search_template_{i}",
                name=f"Search Template {i}",
                description=f"Template {i} with searchable content and tags",
                category=random.choice(categories),
                type=TemplateType.REFERENCE_GUIDE,
                tags=[f"tag_{i%10}", f"group_{i%5}", "searchable"]
            )
            
            self.registry.create_template(
                metadata=metadata,
                content=f"Content for search template {i}",
                validate=False
            )
        
        # Benchmark different search operations
        search_times = []
        
        # Search by category
        for _ in range(100):
            start = time.perf_counter()
            results = self.registry.list_templates(category=TemplateCategory.DOCUMENTATION)
            end = time.perf_counter()
            search_times.append((end - start) * 1000)
        
        # Search by criteria
        criteria = TemplateSearchCriteria(
            category=TemplateCategory.DOCUMENTATION,
            tags=["searchable"],
            search_text="Template"
        )
        
        criteria_times = []
        for _ in range(100):
            start = time.perf_counter()
            results = self.registry.search_templates(criteria)
            end = time.perf_counter()
            criteria_times.append((end - start) * 1000)
        
        return {
            'template_count': template_count,
            'category_search': {
                'min_ms': min(search_times),
                'mean_ms': statistics.mean(search_times),
                'max_ms': max(search_times),
                'under_1ms': statistics.mean(search_times) < 1
            },
            'criteria_search': {
                'min_ms': min(criteria_times),
                'mean_ms': statistics.mean(criteria_times),
                'max_ms': max(criteria_times),
                'under_1ms': statistics.mean(criteria_times) < 1
            }
        }
    
    def benchmark_parallel_rendering(self, threads: int = 10, templates_per_thread: int = 10) -> Dict[str, Any]:
        """Benchmark parallel template rendering."""
        self._print(f"Benchmarking parallel rendering with {threads} threads...")
        
        # Create templates for parallel rendering
        template_ids = []
        for i in range(threads):
            metadata = TemplateMetadata(
                id=f"parallel_template_{i}",
                name=f"Parallel Template {i}",
                description=f"Template {i} for parallel rendering",
                category=TemplateCategory.DOCUMENTATION,
                type=TemplateType.REFERENCE_GUIDE
            )
            
            template = self.registry.create_template(
                metadata=metadata,
                content="Parallel content: {{var1}} {{var2}} {{var3}}",
                validate=False
            )
            template_ids.append(metadata.id)
        
        def render_templates(template_id: str, count: int) -> float:
            """Render template multiple times."""
            context = {'var1': 'value1', 'var2': 'value2', 'var3': 'value3'}
            start = time.perf_counter()
            for _ in range(count):
                self.registry.render_template(template_id, context, validate_context=False)
            return time.perf_counter() - start
        
        # Sequential rendering
        seq_start = time.perf_counter()
        for template_id in template_ids:
            render_templates(template_id, templates_per_thread)
        seq_time = time.perf_counter() - seq_start
        
        # Parallel rendering
        par_start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [
                executor.submit(render_templates, template_id, templates_per_thread)
                for template_id in template_ids
            ]
            results = [f.result() for f in as_completed(futures)]
        par_time = time.perf_counter() - par_start
        
        speedup = seq_time / par_time if par_time > 0 else 0
        
        return {
            'threads': threads,
            'templates_per_thread': templates_per_thread,
            'total_renders': threads * templates_per_thread,
            'sequential_time_sec': seq_time,
            'parallel_time_sec': par_time,
            'speedup': speedup,
            'efficiency': speedup / threads * 100
        }
    
    def run_all_benchmarks(self) -> Dict[str, Any]:
        """Run all benchmarks and return results."""
        self._print("=" * 60)
        self._print("M006 Template Registry Performance Benchmark Suite")
        self._print("=" * 60)
        
        self.setup()
        
        try:
            results = {
                'timestamp': datetime.now().isoformat(),
                'benchmarks': {}
            }
            
            # Run individual benchmarks
            results['benchmarks']['single_loading'] = self.benchmark_single_template_loading()
            self._print_results("Single Template Loading", results['benchmarks']['single_loading'])
            
            results['benchmarks']['batch_loading'] = self.benchmark_batch_loading()
            self._print_results("Batch Loading", results['benchmarks']['batch_loading'])
            
            results['benchmarks']['variable_substitution'] = self.benchmark_variable_substitution()
            self._print_results("Variable Substitution", results['benchmarks']['variable_substitution'])
            
            results['benchmarks']['rendering'] = self.benchmark_template_rendering()
            self._print_results("Template Rendering", results['benchmarks']['rendering'])
            
            results['benchmarks']['memory_usage'] = self.benchmark_memory_usage()
            self._print_results("Memory Usage", results['benchmarks']['memory_usage'])
            
            results['benchmarks']['search'] = self.benchmark_search_operations()
            self._print_results("Search Operations", results['benchmarks']['search'])
            
            results['benchmarks']['parallel'] = self.benchmark_parallel_rendering()
            self._print_results("Parallel Rendering", results['benchmarks']['parallel'])
            
            # Check against targets
            results['targets_met'] = self._check_targets(results['benchmarks'])
            self._print_targets(results['targets_met'])
            
            return results
            
        finally:
            self.teardown()
    
    def _check_targets(self, benchmarks: Dict[str, Any]) -> Dict[str, bool]:
        """Check if performance targets are met."""
        return {
            'single_loading': benchmarks['single_loading']['mean_ms'] < 10,
            'batch_loading': benchmarks['batch_loading']['templates_per_second'] > 100,
            'variable_substitution': benchmarks['variable_substitution']['mean_ms'] < 5,
            'rendering': benchmarks['rendering']['docs_per_second'] > 50,
            'memory_usage': benchmarks['memory_usage']['within_limit'],
            'search': benchmarks['search']['category_search']['under_1ms']
        }
    
    def _print(self, message: str):
        """Print message if verbose."""
        if self.verbose:
            print(message)
    
    def _print_results(self, title: str, results: Dict[str, Any]):
        """Print benchmark results."""
        if not self.verbose:
            return
        
        print(f"\n{title}:")
        print("-" * 40)
        for key, value in results.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.3f}")
            elif isinstance(value, dict):
                print(f"  {key}:")
                for k, v in value.items():
                    if isinstance(v, float):
                        print(f"    {k}: {v:.3f}")
                    else:
                        print(f"    {k}: {v}")
            else:
                print(f"  {key}: {value}")
    
    def _print_targets(self, targets: Dict[str, bool]):
        """Print target achievement status."""
        if not self.verbose:
            return
        
        print("\n" + "=" * 60)
        print("Performance Targets Status:")
        print("-" * 40)
        
        target_names = {
            'single_loading': 'Single template < 10ms',
            'batch_loading': 'Batch > 100 templates/sec',
            'variable_substitution': 'Substitution < 5ms',
            'rendering': 'Rendering > 50 docs/sec',
            'memory_usage': 'Memory < 100MB for 1000',
            'search': 'Search < 1ms'
        }
        
        for key, met in targets.items():
            status = "✅ PASS" if met else "❌ FAIL"
            print(f"  {target_names[key]}: {status}")
        
        all_met = all(targets.values())
        print("-" * 40)
        if all_met:
            print("🎉 All performance targets met!")
        else:
            failed = [k for k, v in targets.items() if not v]
            print(f"⚠️  Failed targets: {', '.join(failed)}")


def main():
    """Run benchmarks from command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run M006 Template Registry benchmarks")
    parser.add_argument('--quiet', '-q', action='store_true', help='Suppress output')
    parser.add_argument('--output', '-o', help='Save results to JSON file')
    
    args = parser.parse_args()
    
    benchmark = TemplateBenchmark(verbose=not args.quiet)
    results = benchmark.run_all_benchmarks()
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults saved to {args.output}")
    
    # Return exit code based on targets
    return 0 if results['targets_met'].values() else 1


if __name__ == "__main__":
    exit(main())