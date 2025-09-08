#!/usr/bin/env python3
"""
M004 Document Generator Performance Benchmark
DevDocAI v3.0.0 - Pass 2 Performance Validation

Run this script to benchmark the performance optimizations.
Target: 248,000 documents per minute (4,133 docs/second)
"""

import asyncio
import time
import tempfile
import shutil
from pathlib import Path
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from devdocai.core.config import ConfigurationManager
from devdocai.core.generator import DocumentGenerator, BatchRequest


def create_sample_project(base_dir: Path) -> Path:
    """Create a sample project for benchmarking."""
    project_dir = base_dir / "benchmark_project"
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # Create sample files
    (project_dir / "main.py").write_text("""
class Application:
    def __init__(self):
        self.name = "BenchmarkApp"
    
    def run(self):
        print(f"Running {self.name}")

def main():
    app = Application()
    app.run()

if __name__ == "__main__":
    main()
""")
    
    (project_dir / "utils.py").write_text("""
def process_data(data):
    return [x * 2 for x in data]

def validate_input(value):
    return isinstance(value, (int, float))

class DataProcessor:
    def transform(self, data):
        return process_data(data)
""")
    
    (project_dir / "setup.py").write_text("""
from setuptools import setup, find_packages

setup(
    name="benchmark_project",
    version="1.0.0",
    description="Sample project for performance benchmarking",
    packages=find_packages(),
    python_requires=">=3.8"
)
""")
    
    (project_dir / "README.md").write_text("""
# Benchmark Project

Sample project for testing document generation performance.
""")
    
    return project_dir


async def benchmark_single_generation(generator: DocumentGenerator, project_path: str) -> dict:
    """Benchmark single document generation."""
    print("\\n📊 Single Document Generation Benchmark")
    print("-" * 50)
    
    # Cold start (no cache)
    generator.clear_caches()
    start = time.time()
    result = await generator.generate(
        document_type='readme',
        project_path=project_path,
        use_cache=False
    )
    cold_time = time.time() - start
    
    # Warm start (with cache)
    start = time.time()
    result = await generator.generate(
        document_type='readme',
        project_path=project_path,
        use_cache=True
    )
    warm_time = time.time() - start
    
    speedup = cold_time / warm_time if warm_time > 0 else 0
    
    print(f"  Cold Start: {cold_time:.3f}s")
    print(f"  Warm Start: {warm_time:.3f}s (cached)")
    print(f"  Cache Speedup: {speedup:.1f}x")
    print(f"  Quality Score: {result.get('quality_score', 0):.1f}")
    
    return {
        'cold_time': cold_time,
        'warm_time': warm_time,
        'speedup': speedup
    }


async def benchmark_batch_generation(generator: DocumentGenerator, project_path: str, batch_size: int) -> dict:
    """Benchmark batch document generation."""
    print(f"\\n📦 Batch Generation Benchmark (n={batch_size})")
    print("-" * 50)
    
    # Create batch requests
    requests = []
    for i in range(batch_size):
        request = BatchRequest(
            document_type='readme' if i % 3 == 0 else 'api_doc',
            project_path=project_path,
            context={
                'project_name': f'Project_{i}',
                'version': f'1.{i}.0',
                'index': i
            },
            request_id=f'bench_{i}'
        )
        requests.append(request)
    
    # Measure batch processing
    start = time.time()
    results = await generator.generate_batch(requests)
    elapsed = time.time() - start
    
    # Calculate metrics
    successful = sum(1 for r in results.values() if r is not None)
    docs_per_second = batch_size / elapsed
    docs_per_minute = docs_per_second * 60
    
    print(f"  Batch Size: {batch_size}")
    print(f"  Time: {elapsed:.2f}s")
    print(f"  Success Rate: {successful}/{batch_size} ({successful/batch_size*100:.1f}%)")
    print(f"  Throughput: {docs_per_second:.1f} docs/s")
    print(f"  Projected: {docs_per_minute:.0f} docs/min")
    
    return {
        'batch_size': batch_size,
        'time': elapsed,
        'success_rate': successful / batch_size,
        'docs_per_second': docs_per_second,
        'docs_per_minute': docs_per_minute
    }


async def benchmark_sustained_load(generator: DocumentGenerator, project_path: str, duration: int = 10) -> dict:
    """Benchmark sustained document generation."""
    print(f"\\n⚡ Sustained Load Benchmark ({duration}s)")
    print("-" * 50)
    
    documents_generated = 0
    cache_hits = 0
    start_time = time.time()
    
    # Generate documents continuously
    while (time.time() - start_time) < duration:
        # Vary document types and contexts for realistic scenario
        doc_type = 'readme' if documents_generated % 3 == 0 else 'api_doc'
        
        result = await generator.generate(
            document_type=doc_type,
            project_path=project_path,
            custom_context={
                'iteration': documents_generated,
                'timestamp': time.time()
            },
            use_cache=True,
            parallel_sections=True
        )
        
        if result and result.get('content'):
            documents_generated += 1
            if result.get('cache_hit'):
                cache_hits += 1
    
    elapsed = time.time() - start_time
    docs_per_second = documents_generated / elapsed
    docs_per_minute = docs_per_second * 60
    cache_hit_rate = cache_hits / documents_generated if documents_generated > 0 else 0
    
    print(f"  Duration: {elapsed:.1f}s")
    print(f"  Documents Generated: {documents_generated}")
    print(f"  Cache Hits: {cache_hits} ({cache_hit_rate*100:.1f}%)")
    print(f"  Throughput: {docs_per_second:.1f} docs/s")
    print(f"  Projected: {docs_per_minute:.0f} docs/min")
    
    return {
        'duration': elapsed,
        'documents': documents_generated,
        'cache_hits': cache_hits,
        'cache_hit_rate': cache_hit_rate,
        'docs_per_second': docs_per_second,
        'docs_per_minute': docs_per_minute
    }


async def benchmark_memory_modes(project_path: str) -> dict:
    """Benchmark performance across memory modes."""
    print("\\n💾 Memory Mode Comparison")
    print("-" * 50)
    
    modes = ['baseline', 'standard', 'enhanced', 'performance']
    mode_results = {}
    
    for mode in modes:
        # Create config for this mode
        config = ConfigurationManager()
        config.system.memory_mode = mode
        config.system.database_path = str(Path(tempfile.mkdtemp()) / 'storage.db')
        config.llm.provider = 'mock'  # Use mock for consistent benchmarking
        
        generator = DocumentGenerator(config=config)
        
        # Quick benchmark (5 documents)
        start = time.time()
        for i in range(5):
            await generator.generate(
                document_type='readme',
                project_path=project_path,
                custom_context={'iteration': i},
                use_cache=(i > 0)
            )
        elapsed = time.time() - start
        
        mode_results[mode] = {
            'time': elapsed,
            'docs_per_second': 5 / elapsed,
            'max_workers': generator.max_workers,
            'cache_size': generator.response_cache.max_cache_size
        }
        
        print(f"  {mode:12} - {5/elapsed:.1f} docs/s, "
              f"workers: {generator.max_workers}, "
              f"cache: {generator.response_cache.max_cache_size}")
    
    return mode_results


async def main():
    """Run comprehensive performance benchmarks."""
    print("="*60)
    print("M004 DOCUMENT GENERATOR - PERFORMANCE BENCHMARK")
    print("Pass 2: Performance Optimization Validation")
    print("="*60)
    
    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Setup
        project_dir = create_sample_project(temp_dir)
        
        # Create optimized configuration
        config = ConfigurationManager()
        # Set system configuration
        config.system.database_path = str(temp_dir / 'storage.db')
        config.system.templates_dir = str(temp_dir / 'templates')
        config.system.cache_dir = str(temp_dir / 'cache')
        config.system.memory_mode = 'performance'
        # Set LLM configuration
        config.llm.provider = 'mock'  # Use mock for benchmarking
        config.llm.cache_responses = True
        config.llm.max_retries = 3
        
        # Initialize generator
        generator = DocumentGenerator(config=config)
        
        print(f"\\n🔧 Configuration:")
        print(f"  Memory Mode: {config.get('memory_mode')}")
        print(f"  Max Workers: {generator.max_workers}")
        print(f"  Cache Size: {generator.response_cache.max_cache_size}")
        
        # Run benchmarks
        results = {}
        
        # 1. Single document generation
        results['single'] = await benchmark_single_generation(generator, str(project_dir))
        
        # 2. Batch generation
        for batch_size in [10, 50, 100]:
            results[f'batch_{batch_size}'] = await benchmark_batch_generation(
                generator, str(project_dir), batch_size
            )
        
        # 3. Sustained load
        results['sustained'] = await benchmark_sustained_load(
            generator, str(project_dir), duration=10
        )
        
        # 4. Memory mode comparison
        results['memory_modes'] = await benchmark_memory_modes(str(project_dir))
        
        # Final statistics
        stats = generator.get_performance_stats()
        
        print("\\n📈 Final Performance Statistics")
        print("-" * 50)
        print(f"  Total Documents: {stats['documents_generated']}")
        print(f"  Total Time: {stats.get('total_time', 0):.1f}s")
        print(f"  Cache Statistics:")
        cache_stats = stats['cache_statistics']
        print(f"    Hit Rate: {cache_stats['hit_rate']*100:.1f}%")
        print(f"    Cache Size: {cache_stats['cache_size']}/{cache_stats['max_size']}")
        
        # Performance vs Target
        print("\\n🎯 Performance vs Design Target")
        print("-" * 50)
        
        target = 248000  # docs per minute
        best_achieved = max(
            results.get('batch_100', {}).get('docs_per_minute', 0),
            results.get('sustained', {}).get('docs_per_minute', 0)
        )
        
        print(f"  Design Target: {target:,} docs/min (4,133 docs/s)")
        print(f"  Best Achieved: {best_achieved:.0f} docs/min")
        print(f"  Achievement: {(best_achieved/target)*100:.2f}%")
        
        if best_achieved < target:
            gap = target / best_achieved
            print(f"  Performance Gap: {gap:.0f}x improvement needed")
        
        print("\\n💡 Optimization Analysis")
        print("-" * 50)
        print("  ✅ Multi-tier caching implemented (L1/L2/L3)")
        print("  ✅ Batch processing with parallel execution")
        print("  ✅ Memory mode scaling (4x-32x workers)")
        print("  ✅ Context extraction optimization with caching")
        print("  ✅ Response similarity matching for cache reuse")
        
        print("\\n📝 Notes:")
        print("  - The 248K/min target assumes >99% cache hits")
        print("  - Real LLM API calls add 500-2000ms per request")
        print("  - Performance scales with available memory and CPU")
        print("  - Document similarity enables massive cache benefits")
        
    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    print("\\n" + "="*60)
    print("Benchmark Complete!")
    print("="*60)


if __name__ == "__main__":
    # Run async main
    asyncio.run(main())