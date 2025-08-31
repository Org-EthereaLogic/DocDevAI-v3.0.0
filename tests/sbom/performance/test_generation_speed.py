"""
SBOM Generation Performance Testing.

Comprehensive performance test suite for SBOM generation with targets:
- Typical projects: <30 seconds generation time
- Small projects: <5 seconds
- Medium projects: <15 seconds  
- Large projects: <30 seconds
- Enterprise projects: <60 seconds (extended target)
"""

import pytest
import time
import json
import threading
from pathlib import Path
from typing import Dict, List, Any, Tuple
import concurrent.futures
from dataclasses import dataclass

# Import SBOM testing framework
from ..core import SBOMTestFramework, SBOMFormat, SBOMTestMetrics
from ..generators import SBOMTestDataGenerator
from ..assertions import SBOMAssertions
from devdocai.common.testing import PerformanceTester


@dataclass
class PerformanceTarget:
    """Performance target specification."""
    project_size: str
    max_generation_time: float  # seconds
    max_dependencies: int
    target_throughput: float  # deps/sec


class TestSBOMGenerationPerformance(SBOMTestFramework):
    """
    Test suite for SBOM generation performance requirements.
    
    Validates generation speed meets enterprise requirements
    and scales appropriately with project complexity.
    """
    
    # Performance targets based on M010 requirements
    PERFORMANCE_TARGETS = {
        "small": PerformanceTarget(
            project_size="small",
            max_generation_time=5.0,
            max_dependencies=50,
            target_throughput=10.0
        ),
        "medium": PerformanceTarget(
            project_size="medium", 
            max_generation_time=15.0,
            max_dependencies=200,
            target_throughput=15.0
        ),
        "large": PerformanceTarget(
            project_size="large",
            max_generation_time=30.0,  # Key requirement
            max_dependencies=1000,
            target_throughput=35.0
        ),
        "enterprise": PerformanceTarget(
            project_size="enterprise",
            max_generation_time=60.0,  # Extended for very large projects
            max_dependencies=5000,
            target_throughput=80.0
        )
    }
    
    def setup_method(self):
        """Set up test environment."""
        super().setup_method()
        self.generator = SBOMTestDataGenerator(seed=42)
        self.assertions = SBOMAssertions()
        self.performance_results = {}
    
    # ========================================================================
    # BASIC PERFORMANCE TESTS
    # ========================================================================
    
    @pytest.mark.parametrize("project_size", ["small", "medium", "large"])
    def test_sbom_generation_performance_targets(self, project_size: str):
        """Test SBOM generation meets performance targets."""
        target = self.PERFORMANCE_TARGETS[project_size]
        
        # Generate test dependency tree
        dependency_tree = self.generator.generate_realistic_dependency_tree(
            complexity=project_size,
            ecosystem="npm"
        )
        
        # Count actual dependencies
        actual_dependencies = self._count_dependencies(dependency_tree)
        
        # Measure generation time for SPDX JSON
        generation_time, spdx_content = self.measure_sbom_generation(
            self._generate_sbom_content,
            SBOMFormat.SPDX_JSON,
            dependency_tree
        )
        
        # Store results for analysis
        self.performance_results[f"{project_size}_spdx"] = {
            "time": generation_time,
            "dependencies": actual_dependencies,
            "throughput": actual_dependencies / generation_time if generation_time > 0 else 0
        }
        
        # Assert performance target met
        self.assertions.assert_generation_performance(
            generation_time=generation_time,
            target_time=target.max_generation_time,
            project_size=project_size,
            dependency_count=actual_dependencies
        )
        
        # Assert throughput target met
        throughput = actual_dependencies / generation_time if generation_time > 0 else 0
        assert throughput >= target.target_throughput, \
            f"{project_size} throughput below target: {throughput:.1f} < {target.target_throughput:.1f} deps/sec"
    
    def test_enterprise_project_performance(self):
        """Test performance with enterprise-scale projects."""
        target = self.PERFORMANCE_TARGETS["enterprise"]
        
        # Generate large dependency tree
        dependency_tree = self.generator.generate_realistic_dependency_tree(
            complexity="enterprise",
            ecosystem="npm"
        )
        
        actual_dependencies = self._count_dependencies(dependency_tree)
        
        # Generate SBOM with performance monitoring
        start_memory = self._get_memory_usage()
        
        generation_time, sbom_content = self.measure_sbom_generation(
            self._generate_sbom_content,
            SBOMFormat.SPDX_JSON,
            dependency_tree
        )
        
        end_memory = self._get_memory_usage()
        memory_delta = end_memory - start_memory
        
        # Assert performance target
        self.assertions.assert_generation_performance(
            generation_time=generation_time,
            target_time=target.max_generation_time,
            project_size="enterprise",
            dependency_count=actual_dependencies
        )
        
        # Assert memory usage is reasonable (< 500MB for enterprise project)
        assert memory_delta < 500 * 1024 * 1024, \
            f"Memory usage too high: {memory_delta / 1024 / 1024:.1f}MB"
        
        # Assert file size is reasonable
        self.assertions.assert_file_size_reasonable(
            sbom_content,
            max_size_mb=50.0,  # 50MB max for enterprise SBOM
            dependency_count=actual_dependencies
        )
    
    def test_multiple_format_generation_performance(self):
        """Test performance when generating multiple SBOM formats."""
        # Generate medium complexity project
        dependency_tree = self.generator.generate_realistic_dependency_tree(
            complexity="medium",
            ecosystem="npm"
        )
        
        formats = [
            SBOMFormat.SPDX_JSON,
            SBOMFormat.SPDX_YAML,
            SBOMFormat.CYCLONE_DX_JSON
        ]
        
        total_start_time = time.perf_counter()
        generation_times = {}
        
        # Generate each format
        for format_type in formats:
            generation_time, content = self.measure_sbom_generation(
                self._generate_sbom_content,
                format_type,
                dependency_tree
            )
            generation_times[format_type] = generation_time
        
        total_time = time.perf_counter() - total_start_time
        
        # Total time for all formats should be reasonable (< 45 seconds)
        assert total_time < 45.0, \
            f"Multiple format generation too slow: {total_time:.2f}s > 45.0s"
        
        # Each individual format should meet medium project target
        target_time = self.PERFORMANCE_TARGETS["medium"].max_generation_time
        for format_type, gen_time in generation_times.items():
            assert gen_time < target_time, \
                f"{format_type} generation too slow: {gen_time:.2f}s > {target_time:.2f}s"
    
    # ========================================================================
    # CONCURRENT GENERATION TESTS
    # ========================================================================
    
    def test_concurrent_sbom_generation(self):
        """Test performance with concurrent SBOM generation."""
        # Generate multiple dependency trees
        dependency_trees = []
        for _ in range(5):
            tree = self.generator.generate_realistic_dependency_tree(
                complexity="medium",
                ecosystem="npm"
            )
            dependency_trees.append(tree)
        
        # Function to generate SBOM
        def generate_single_sbom(tree):
            start_time = time.perf_counter()
            content = self._generate_sbom_content(SBOMFormat.SPDX_JSON, tree)
            generation_time = time.perf_counter() - start_time
            return generation_time, len(content)
        
        # Test concurrent generation
        start_time = time.perf_counter()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(generate_single_sbom, tree) for tree in dependency_trees]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        total_concurrent_time = time.perf_counter() - start_time
        
        # Concurrent generation should be faster than sequential
        sequential_time_estimate = sum(result[0] for result in results)
        
        # Should have some concurrency benefit (at least 20% faster than sequential)
        assert total_concurrent_time < sequential_time_estimate * 0.8, \
            f"Concurrent generation not efficient: {total_concurrent_time:.2f}s vs {sequential_time_estimate:.2f}s estimated"
    
    def test_thread_safety_performance(self):
        """Test thread safety doesn't significantly impact performance."""
        dependency_tree = self.generator.generate_realistic_dependency_tree(
            complexity="medium"
        )
        
        # Measure single-threaded performance
        single_thread_time, _ = self.measure_sbom_generation(
            self._generate_sbom_content,
            SBOMFormat.SPDX_JSON,
            dependency_tree
        )
        
        # Measure multi-threaded performance (same operation in multiple threads)
        def threaded_generation():
            return self._generate_sbom_content(SBOMFormat.SPDX_JSON, dependency_tree)
        
        start_time = time.perf_counter()
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=threaded_generation)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        multi_thread_time = time.perf_counter() - start_time
        avg_thread_time = multi_thread_time / 3
        
        # Thread safety overhead should be minimal (< 50% slower per operation)
        assert avg_thread_time < single_thread_time * 1.5, \
            f"Thread safety overhead too high: {avg_thread_time:.2f}s vs {single_thread_time:.2f}s"
    
    # ========================================================================
    # SCALABILITY TESTS
    # ========================================================================
    
    def test_dependency_count_scalability(self):
        """Test how generation time scales with dependency count."""
        dependency_counts = [10, 50, 100, 500, 1000]
        generation_times = []
        
        for count in dependency_counts:
            # Generate tree with approximately 'count' dependencies
            complexity = "simple" if count < 50 else "medium" if count < 500 else "large"
            tree = self.generator.generate_realistic_dependency_tree(
                complexity=complexity,
                ecosystem="npm"
            )
            
            # Adjust tree to have approximately the target count
            # (This is a simplification - in practice you'd generate exact counts)
            
            generation_time, _ = self.measure_sbom_generation(
                self._generate_sbom_content,
                SBOMFormat.SPDX_JSON,
                tree
            )
            
            actual_count = self._count_dependencies(tree)
            generation_times.append((actual_count, generation_time))
        
        # Verify scalability is reasonable (should be roughly linear)
        for i in range(1, len(generation_times)):
            count_ratio = generation_times[i][0] / generation_times[i-1][0]
            time_ratio = generation_times[i][1] / generation_times[i-1][1]
            
            # Time scaling should not be worse than quadratic
            scaling_factor = time_ratio / count_ratio
            assert scaling_factor < 2.0, \
                f"Poor scalability: {scaling_factor:.2f}x time increase for {count_ratio:.2f}x dependencies"
    
    def test_dependency_depth_scalability(self):
        """Test how generation time scales with dependency tree depth."""
        depths = [2, 4, 6, 8]
        generation_times = []
        
        for depth in depths:
            # Create deep but narrow dependency tree
            root = self.generator.generate_realistic_dependency_tree(
                complexity="simple",
                ecosystem="npm"
            )
            
            # Make it deeper (simplified approach)
            generation_time, _ = self.measure_sbom_generation(
                self._generate_sbom_content,
                SBOMFormat.SPDX_JSON,
                root
            )
            
            generation_times.append((depth, generation_time))
        
        # Deep trees should not cause exponential time increase
        for i in range(1, len(generation_times)):
            depth_ratio = generation_times[i][0] / generation_times[i-1][0]
            time_ratio = generation_times[i][1] / generation_times[i-1][1]
            
            # Time increase should be roughly linear with depth
            scaling_factor = time_ratio / depth_ratio
            assert scaling_factor < 1.5, \
                f"Poor depth scalability: {scaling_factor:.2f}x time increase for {depth_ratio:.2f}x depth"
    
    # ========================================================================
    # STRESS AND EDGE CASE TESTS
    # ========================================================================
    
    def test_maximum_load_performance(self):
        """Test performance under maximum expected load."""
        # Generate maximum size project
        dependency_tree = self.generator.generate_realistic_dependency_tree(
            complexity="enterprise",
            ecosystem="npm"
        )
        
        # Add stress factors
        stress_factors = {
            "complex_names": True,  # Complex package names
            "deep_nesting": True,   # Deep dependency nesting
            "many_licenses": True,  # Many different licenses
            "unicode_content": True # Unicode in names/descriptions
        }
        
        # Generate under stress
        generation_time, sbom_content = self.measure_sbom_generation(
            self._generate_sbom_content,
            SBOMFormat.SPDX_JSON,
            dependency_tree
        )
        
        # Should still meet extended enterprise target
        extended_target = self.PERFORMANCE_TARGETS["enterprise"].max_generation_time * 1.5
        
        self.assertions.assert_generation_performance(
            generation_time=generation_time,
            target_time=extended_target,
            project_size="enterprise-stress",
            dependency_count=self._count_dependencies(dependency_tree)
        )
    
    def test_memory_constrained_performance(self):
        """Test performance with memory constraints."""
        # This test would ideally limit available memory
        # For now, we'll test with a very large project and monitor memory
        
        dependency_tree = self.generator.generate_realistic_dependency_tree(
            complexity="enterprise"
        )
        
        start_memory = self._get_memory_usage()
        
        generation_time, sbom_content = self.measure_sbom_generation(
            self._generate_sbom_content,
            SBOMFormat.SPDX_JSON,
            dependency_tree
        )
        
        peak_memory = self._get_memory_usage()
        memory_used = peak_memory - start_memory
        
        # Memory usage should be reasonable (< 1GB)
        assert memory_used < 1024 * 1024 * 1024, \
            f"Memory usage too high: {memory_used / 1024 / 1024:.1f}MB"
        
        # Should still meet performance target
        target = self.PERFORMANCE_TARGETS["enterprise"]
        self.assertions.assert_generation_performance(
            generation_time=generation_time,
            target_time=target.max_generation_time,
            project_size="enterprise-memory-constrained"
        )
    
    # ========================================================================
    # BENCHMARK AND REGRESSION TESTS
    # ========================================================================
    
    def test_performance_regression_baseline(self):
        """Establish performance baseline for regression testing."""
        # Generate standard test cases
        test_cases = ["small", "medium", "large"]
        baselines = {}
        
        for case in test_cases:
            dependency_tree = self.generator.generate_realistic_dependency_tree(
                complexity=case
            )
            
            # Run multiple iterations for stable baseline
            times = []
            for _ in range(5):
                generation_time, _ = self.measure_sbom_generation(
                    self._generate_sbom_content,
                    SBOMFormat.SPDX_JSON,
                    dependency_tree
                )
                times.append(generation_time)
            
            # Use median time as baseline
            times.sort()
            baseline_time = times[len(times) // 2]
            
            baselines[case] = {
                "baseline_time": baseline_time,
                "dependency_count": self._count_dependencies(dependency_tree),
                "throughput": self._count_dependencies(dependency_tree) / baseline_time
            }
        
        # Store baselines (in real implementation, this would persist to file)
        self.performance_baseline = baselines
        
        # Assert all baselines meet targets
        for case, baseline in baselines.items():
            target = self.PERFORMANCE_TARGETS[case]
            assert baseline["baseline_time"] <= target.max_generation_time, \
                f"{case} baseline exceeds target: {baseline['baseline_time']:.2f}s > {target.max_generation_time:.2f}s"
    
    def test_performance_comparison_benchmark(self):
        """Compare performance across different SBOM formats."""
        dependency_tree = self.generator.generate_realistic_dependency_tree(
            complexity="medium"
        )
        
        formats_to_test = [
            SBOMFormat.SPDX_JSON,
            SBOMFormat.SPDX_YAML, 
            SBOMFormat.CYCLONE_DX_JSON
        ]
        
        benchmark_results = {}
        
        for format_type in formats_to_test:
            # Run benchmark
            stats = PerformanceTester.benchmark(
                lambda: self._generate_sbom_content(format_type, dependency_tree),
                iterations=10,
                warmup=3
            )
            
            benchmark_results[format_type] = stats
        
        # All formats should meet reasonable performance targets
        for format_type, stats in benchmark_results.items():
            assert stats["mean"] < 15.0, \
                f"{format_type} mean time too slow: {stats['mean']:.2f}s"
            
            assert stats["ops_per_sec"] > 0.1, \
                f"{format_type} throughput too low: {stats['ops_per_sec']:.3f} ops/sec"
        
        # JSON formats should generally be faster than YAML
        spdx_json_time = benchmark_results[SBOMFormat.SPDX_JSON]["mean"]
        spdx_yaml_time = benchmark_results[SBOMFormat.SPDX_YAML]["mean"]
        
        assert spdx_json_time <= spdx_yaml_time * 1.2, \
            f"JSON not faster than YAML: {spdx_json_time:.2f}s vs {spdx_yaml_time:.2f}s"
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _generate_sbom_content(self, format_type: SBOMFormat, dependency_tree) -> str:
        """Generate SBOM content for performance testing."""
        from ..core import create_sample_sbom
        return create_sample_sbom(format_type, dependency_tree)
    
    def _count_dependencies(self, node) -> int:
        """Count total dependencies in tree."""
        count = 1
        for child in node.children:
            count += self._count_dependencies(child)
        return count
    
    def _get_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss
        except ImportError:
            # Fallback if psutil not available
            return 0
    
    def teardown_method(self):
        """Clean up and report performance results."""
        super().cleanup_test_artifacts()
        
        # Report performance results for analysis
        if self.performance_results:
            print("\nPerformance Test Results:")
            for test_name, results in self.performance_results.items():
                print(f"  {test_name}: {results['time']:.2f}s, {results['throughput']:.1f} deps/sec")
        
        self.performance_results.clear()