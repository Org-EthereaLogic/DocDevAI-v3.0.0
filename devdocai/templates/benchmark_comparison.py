#!/usr/bin/env python3
"""
Performance comparison between baseline and optimized Template Registry.

This script runs benchmarks on both implementations to measure improvements.
"""

import time
import statistics
import json
from datetime import datetime
from typing import Dict, Any
import tempfile
import shutil
from pathlib import Path

# Import both implementations
from .registry import TemplateRegistry as BaselineRegistry
from .registry_optimized import OptimizedTemplateRegistry
from .models import (
    TemplateMetadata,
    TemplateCategory,
    TemplateType,
    TemplateSearchCriteria
)


class PerformanceComparison:
    """Compare performance between baseline and optimized implementations."""
    
    def __init__(self, verbose: bool = True):
        """Initialize comparison suite."""
        self.verbose = verbose
        self.results = {
            'baseline': {},
            'optimized': {},
            'improvements': {}
        }
        self.temp_dir = None
    
    def setup(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp(prefix="template_compare_")
        
        # Initialize both registries
        self.baseline_registry = BaselineRegistry(auto_load_defaults=False)
        self.optimized_registry = OptimizedTemplateRegistry(
            auto_load_defaults=False,
            lazy_load=True,
            max_cache_size=1000,
            max_workers=4
        )
        
        # Create test templates
        self._create_test_templates()
    
    def teardown(self):
        """Cleanup test environment."""
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
        
        if hasattr(self, 'baseline_registry'):
            self.baseline_registry.shutdown()
        if hasattr(self, 'optimized_registry'):
            self.optimized_registry.shutdown()
    
    def _create_test_templates(self):
        """Create test templates for benchmarking."""
        # Create 100 test templates
        for i in range(100):
            metadata = TemplateMetadata(
                id=f"test_template_{i}",
                name=f"Test Template {i}",
                description=f"Test template {i} for performance comparison",
                category=TemplateCategory.DOCUMENTATION,
                type=TemplateType.REFERENCE_GUIDE,
                tags=[f"tag_{i%10}", f"group_{i%5}", "test"]
            )
            
            content = f"""
# Template {i}

## Section 1
Variable test: {{{{var_1}}}} {{{{var_2}}}} {{{{var_3}}}}

<!-- IF condition_{i%2} -->
Conditional content for {i}
<!-- END IF -->

<!-- FOR item IN items -->
- Item: {{{{item}}}}
<!-- END FOR -->

## Section 2
More content with {{{{var_4}}}} and {{{{var_5}}}}
""" * 10  # Make it larger
            
            variables = [
                {"name": f"var_{j}", "required": False, "default": f"default_{j}"}
                for j in range(5)
            ]
            
            # Add to both registries
            self.baseline_registry.create_template(
                metadata=metadata.model_copy(),
                content=content,
                variables=variables,
                validate=False
            )
            
            self.optimized_registry.create_template(
                metadata=metadata.model_copy(),
                content=content,
                variables=variables,
                validate=False
            )
    
    def benchmark_single_render(self, iterations: int = 100) -> Dict[str, Any]:
        """Compare single template rendering performance."""
        self._print("\n=== Single Template Rendering ===")
        
        template_id = "test_template_0"
        context = {
            'var_1': 'value1',
            'var_2': 'value2',
            'var_3': 'value3',
            'var_4': 'value4',
            'var_5': 'value5',
            'condition_0': True,
            'loop_items': ['item1', 'item2', 'item3']
        }
        
        # Baseline timing
        baseline_times = []
        for _ in range(iterations):
            # Clear cache for fair comparison
            if hasattr(self.baseline_registry._templates.get(template_id), 'clear_cache'):
                self.baseline_registry._templates[template_id].clear_cache()
            
            start = time.perf_counter()
            self.baseline_registry.render_template(template_id, context, validate_context=False)
            end = time.perf_counter()
            baseline_times.append((end - start) * 1000)
        
        # Optimized timing (without cache)
        optimized_times_nocache = []
        for _ in range(iterations):
            # Clear cache
            self.optimized_registry._render_cache.clear()
            
            start = time.perf_counter()
            self.optimized_registry.render_template(template_id, context, validate_context=False, use_compiled=False)
            end = time.perf_counter()
            optimized_times_nocache.append((end - start) * 1000)
        
        # Optimized timing (with compilation)
        optimized_times_compiled = []
        for _ in range(iterations):
            # Clear render cache but keep compiled template
            self.optimized_registry._render_cache.clear()
            
            start = time.perf_counter()
            self.optimized_registry.render_template(template_id, context, validate_context=False, use_compiled=True)
            end = time.perf_counter()
            optimized_times_compiled.append((end - start) * 1000)
        
        # Optimized timing (with full cache)
        optimized_times_cached = []
        # Warm up cache
        self.optimized_registry.render_template(template_id, context, validate_context=False, use_compiled=True)
        
        for _ in range(iterations):
            start = time.perf_counter()
            self.optimized_registry.render_template(template_id, context, validate_context=False, use_compiled=True)
            end = time.perf_counter()
            optimized_times_cached.append((end - start) * 1000)
        
        results = {
            'baseline_ms': statistics.mean(baseline_times),
            'optimized_nocache_ms': statistics.mean(optimized_times_nocache),
            'optimized_compiled_ms': statistics.mean(optimized_times_compiled),
            'optimized_cached_ms': statistics.mean(optimized_times_cached),
            'improvement_nocache': (statistics.mean(baseline_times) / statistics.mean(optimized_times_nocache) - 1) * 100,
            'improvement_compiled': (statistics.mean(baseline_times) / statistics.mean(optimized_times_compiled) - 1) * 100,
            'improvement_cached': (statistics.mean(baseline_times) / statistics.mean(optimized_times_cached) - 1) * 100
        }
        
        self._print_comparison("Single Render", results)
        return results
    
    def benchmark_batch_render(self, batch_size: int = 50) -> Dict[str, Any]:
        """Compare batch rendering performance."""
        self._print("\n=== Batch Rendering ===")
        
        # Prepare batch requests
        render_requests = [
            (f"test_template_{i}", {
                'var_1': f'value1_{i}',
                'var_2': f'value2_{i}',
                'var_3': f'value3_{i}',
                'var_4': f'value4_{i}',
                'var_5': f'value5_{i}',
                f'condition_{i%2}': True,
                'loop_items': [f'item_{j}' for j in range(3)]
            })
            for i in range(batch_size)
        ]
        
        # Baseline - sequential
        start = time.perf_counter()
        for template_id, context in render_requests:
            self.baseline_registry.render_template(template_id, context, validate_context=False)
        baseline_time = time.perf_counter() - start
        
        # Optimized - sequential
        start = time.perf_counter()
        for template_id, context in render_requests:
            self.optimized_registry.render_template(template_id, context, validate_context=False)
        optimized_seq_time = time.perf_counter() - start
        
        # Optimized - parallel
        start = time.perf_counter()
        self.optimized_registry.render_batch(render_requests, parallel=True)
        optimized_par_time = time.perf_counter() - start
        
        results = {
            'batch_size': batch_size,
            'baseline_sec': baseline_time,
            'optimized_sequential_sec': optimized_seq_time,
            'optimized_parallel_sec': optimized_par_time,
            'sequential_improvement': (baseline_time / optimized_seq_time - 1) * 100,
            'parallel_improvement': (baseline_time / optimized_par_time - 1) * 100,
            'parallel_speedup': optimized_seq_time / optimized_par_time
        }
        
        self._print_comparison("Batch Render", results)
        return results
    
    def benchmark_search(self, iterations: int = 100) -> Dict[str, Any]:
        """Compare search performance."""
        self._print("\n=== Search Performance ===")
        
        # Test different search criteria
        criteria = TemplateSearchCriteria(
            category=TemplateCategory.DOCUMENTATION,
            tags=["test", "tag_5"],
            search_text="Template"
        )
        
        # Baseline search
        baseline_times = []
        for _ in range(iterations):
            start = time.perf_counter()
            results = self.baseline_registry.search_templates(criteria)
            end = time.perf_counter()
            baseline_times.append((end - start) * 1000)
        
        # Optimized search (with index)
        optimized_times = []
        for _ in range(iterations):
            start = time.perf_counter()
            results = self.optimized_registry.search_templates(criteria)
            end = time.perf_counter()
            optimized_times.append((end - start) * 1000)
        
        results = {
            'baseline_ms': statistics.mean(baseline_times),
            'optimized_ms': statistics.mean(optimized_times),
            'improvement': (statistics.mean(baseline_times) / statistics.mean(optimized_times) - 1) * 100,
            'baseline_under_1ms': statistics.mean(baseline_times) < 1,
            'optimized_under_1ms': statistics.mean(optimized_times) < 1
        }
        
        self._print_comparison("Search", results)
        return results
    
    def benchmark_memory(self) -> Dict[str, Any]:
        """Compare memory usage."""
        self._print("\n=== Memory Usage ===")
        
        import sys
        
        # Get size of registries
        baseline_size = sys.getsizeof(self.baseline_registry._templates)
        optimized_size = sys.getsizeof(self.optimized_registry._templates)
        
        # Get cache stats from optimized version
        cache_stats = self.optimized_registry._render_cache.get_stats()
        
        results = {
            'baseline_templates_kb': baseline_size / 1024,
            'optimized_templates_kb': optimized_size / 1024,
            'cache_memory_mb': cache_stats['memory_mb'],
            'cache_size': cache_stats['size'],
            'memory_reduction': (baseline_size - optimized_size) / baseline_size * 100 if baseline_size > 0 else 0
        }
        
        self._print_comparison("Memory", results)
        return results
    
    def benchmark_lazy_loading(self) -> Dict[str, Any]:
        """Test lazy loading performance."""
        self._print("\n=== Lazy Loading ===")
        
        # Create a new optimized registry with lazy loading
        lazy_registry = OptimizedTemplateRegistry(
            auto_load_defaults=False,
            lazy_load=True
        )
        
        # Register metadata for 1000 templates without loading
        for i in range(1000):
            lazy_registry._template_metadata[f"lazy_{i}"] = {
                'id': f"lazy_{i}",
                'name': f"Lazy Template {i}",
                'category': 'documentation',
                'type': 'reference_guide'
            }
        
        # Time first access (lazy load)
        start = time.perf_counter()
        try:
            template = lazy_registry.get_template("lazy_0")
        except:
            pass  # Expected to fail since template doesn't exist
        first_access_time = (time.perf_counter() - start) * 1000
        
        # Time metadata access
        start = time.perf_counter()
        metadata_count = len(lazy_registry._template_metadata)
        metadata_time = (time.perf_counter() - start) * 1000
        
        results = {
            'registered_templates': metadata_count,
            'loaded_templates': len(lazy_registry._templates),
            'first_access_ms': first_access_time,
            'metadata_access_ms': metadata_time,
            'memory_saved': metadata_count > len(lazy_registry._templates)
        }
        
        lazy_registry.shutdown()
        
        self._print_comparison("Lazy Loading", results)
        return results
    
    def run_all_comparisons(self) -> Dict[str, Any]:
        """Run all performance comparisons."""
        self._print("=" * 60)
        self._print("Template Registry Performance Comparison")
        self._print("Baseline vs Optimized Implementation")
        self._print("=" * 60)
        
        self.setup()
        
        try:
            all_results = {
                'timestamp': datetime.now().isoformat(),
                'comparisons': {}
            }
            
            # Run comparisons
            all_results['comparisons']['single_render'] = self.benchmark_single_render()
            all_results['comparisons']['batch_render'] = self.benchmark_batch_render()
            all_results['comparisons']['search'] = self.benchmark_search()
            all_results['comparisons']['memory'] = self.benchmark_memory()
            all_results['comparisons']['lazy_loading'] = self.benchmark_lazy_loading()
            
            # Calculate overall improvement
            improvements = []
            for name, comparison in all_results['comparisons'].items():
                for key, value in comparison.items():
                    if 'improvement' in key and isinstance(value, (int, float)):
                        improvements.append(value)
            
            if improvements:
                all_results['overall_improvement'] = statistics.mean(improvements)
                
                self._print("\n" + "=" * 60)
                self._print(f"OVERALL AVERAGE IMPROVEMENT: {all_results['overall_improvement']:.1f}%")
                self._print("=" * 60)
            
            # Get metrics from optimized registry
            all_results['optimized_metrics'] = self.optimized_registry.get_metrics()
            
            return all_results
            
        finally:
            self.teardown()
    
    def _print(self, message: str):
        """Print if verbose."""
        if self.verbose:
            print(message)
    
    def _print_comparison(self, title: str, results: Dict[str, Any]):
        """Print comparison results."""
        if not self.verbose:
            return
        
        print(f"\n{title} Results:")
        print("-" * 40)
        for key, value in results.items():
            if isinstance(value, float):
                if 'improvement' in key or 'speedup' in key:
                    if value > 0:
                        print(f"  {key}: +{value:.1f}%")
                    else:
                        print(f"  {key}: {value:.1f}%")
                else:
                    print(f"  {key}: {value:.3f}")
            else:
                print(f"  {key}: {value}")


def main():
    """Run performance comparison."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Compare template registry performance")
    parser.add_argument('--quiet', '-q', action='store_true', help='Suppress output')
    parser.add_argument('--output', '-o', help='Save results to JSON file')
    
    args = parser.parse_args()
    
    comparison = PerformanceComparison(verbose=not args.quiet)
    results = comparison.run_all_comparisons()
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults saved to {args.output}")
    
    return 0


if __name__ == "__main__":
    exit(main())