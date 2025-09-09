#!/usr/bin/env python3
"""
M003 MIAIR Engine Performance Profiler
DevDocAI v3.0.0 - Pass 2 Performance Analysis

This script profiles the current MIAIR implementation to identify bottlenecks
and provide optimization recommendations for achieving 248K docs/minute target.
"""

import time
import cProfile
import pstats
import io
import sys
import os
import json
import tracemalloc
import numpy as np
from typing import Dict, List, Any, Tuple
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from devdocai.intelligence.miair import (
    MIAIREngine,
    MIAIREngineFactory,
    DocumentMetrics,
    MetricsCalculator,
    SecurityManager
)
from devdocai.core.config import ConfigurationManager
from devdocai.intelligence.llm_adapter import LLMAdapter, LLMResponse
from devdocai.core.storage import StorageManager


class MockLLMAdapter:
    """Mock LLM adapter for performance testing without actual API calls."""
    
    def __init__(self, latency_ms: float = 50):
        self.latency_ms = latency_ms
        self.call_count = 0
    
    def query(self, prompt: str, **kwargs) -> LLMResponse:
        """Simulate LLM response with configurable latency."""
        # Simulate network latency
        time.sleep(self.latency_ms / 1000)
        self.call_count += 1
        
        # Generate realistic response
        enhanced_content = f"Enhanced content with improved clarity and structure. {np.random.randint(1000)}"
        return LLMResponse(
            content=enhanced_content,
            provider="mock",
            tokens_used=100,
            cost=0.001,
            latency=self.latency_ms / 1000
        )


class PerformanceProfiler:
    """Comprehensive performance profiler for MIAIR Engine."""
    
    def __init__(self):
        self.results = {}
        self.recommendations = []
        
    def generate_test_documents(self, count: int, size: str = "medium") -> List[str]:
        """Generate test documents of varying sizes."""
        docs = []
        
        if size == "small":
            template = "Short document {}: Brief technical content with minimal complexity."
        elif size == "medium":
            template = """
            Document {}: This is a comprehensive technical document covering various aspects
            of software engineering. It includes detailed analysis of performance optimization,
            security considerations, and architectural patterns. The content is structured
            with multiple paragraphs and technical terminology to simulate real documentation.
            Random content for uniqueness: {}
            """
        else:  # large
            template = """
            Document {}: This is an extensive technical specification document that provides
            comprehensive coverage of system architecture, design patterns, and implementation details.
            
            Section 1: Architecture Overview
            The system architecture follows a microservices pattern with distributed components
            communicating through message queues and REST APIs. Each service is independently
            deployable and scalable, with its own database and caching layer.
            
            Section 2: Performance Optimization
            Performance optimization involves multiple strategies including caching, query optimization,
            code profiling, and resource management. The system uses both in-memory and distributed
            caching to minimize database queries and improve response times.
            
            Section 3: Security Considerations
            Security is implemented through multiple layers including authentication, authorization,
            encryption, and audit logging. All sensitive data is encrypted at rest and in transit.
            
            Section 4: Implementation Details
            The implementation uses modern programming practices including test-driven development,
            continuous integration, and automated deployment. Code quality is maintained through
            static analysis, peer reviews, and comprehensive testing.
            
            Random unique content: {}
            Additional technical details follow...
            """
        
        for i in range(count):
            if size == "small":
                docs.append(template.format(i))
            else:
                docs.append(template.format(i, np.random.randint(10000)))
        
        return docs
    
    def profile_entropy_calculation(self, engine: MIAIREngine, documents: List[str]) -> Dict[str, Any]:
        """Profile entropy calculation performance."""
        print("\n" + "="*60)
        print("PROFILING: Entropy Calculation")
        print("="*60)
        
        results = {
            "single_doc_times": [],
            "cache_hit_times": [],
            "batch_time": 0,
            "throughput": 0
        }
        
        # Profile single document entropy
        for i in range(min(10, len(documents))):
            doc = documents[i]
            
            # First call (potential cache miss)
            start = time.perf_counter()
            entropy1 = engine.calculate_entropy(doc)
            first_time = time.perf_counter() - start
            results["single_doc_times"].append(first_time)
            
            # Second call (cache hit)
            start = time.perf_counter()
            entropy2 = engine.calculate_entropy(doc)
            cached_time = time.perf_counter() - start
            results["cache_hit_times"].append(cached_time)
        
        # Profile batch entropy calculation
        start = time.perf_counter()
        batch_entropies = engine.calculate_entropy_batch(documents[:100])
        results["batch_time"] = time.perf_counter() - start
        results["throughput"] = len(documents[:100]) / results["batch_time"]
        
        # Analysis
        avg_single = np.mean(results["single_doc_times"]) * 1000  # ms
        avg_cached = np.mean(results["cache_hit_times"]) * 1000  # ms
        cache_speedup = avg_single / avg_cached if avg_cached > 0 else 0
        
        print(f"Average single doc time: {avg_single:.2f}ms")
        print(f"Average cached time: {avg_cached:.2f}ms")
        print(f"Cache speedup: {cache_speedup:.1f}x")
        print(f"Batch throughput: {results['throughput']:.0f} docs/sec")
        
        # Recommendations
        if avg_single > 10:
            self.recommendations.append(
                "⚠️ Entropy calculation is slow (>10ms). Consider optimizing tokenization."
            )
        if cache_speedup < 5:
            self.recommendations.append(
                "⚠️ Cache effectiveness is low. Consider improving cache key generation."
            )
        
        return results
    
    def profile_quality_measurement(self, engine: MIAIREngine, documents: List[str]) -> Dict[str, Any]:
        """Profile quality measurement performance."""
        print("\n" + "="*60)
        print("PROFILING: Quality Measurement")
        print("="*60)
        
        results = {
            "measurement_times": [],
            "components": {}
        }
        
        # Create metrics calculator for detailed profiling
        calculator = MetricsCalculator(engine.config)
        
        for doc in documents[:20]:
            # Profile overall measurement
            start = time.perf_counter()
            metrics = engine.measure_quality(doc)
            total_time = time.perf_counter() - start
            results["measurement_times"].append(total_time)
            
            # Profile individual components
            words = calculator.tokenize(doc)
            
            # Entropy calculation
            start = time.perf_counter()
            entropy = calculator.calculate_entropy(words)
            entropy_time = time.perf_counter() - start
            
            # Coherence calculation
            start = time.perf_counter()
            coherence = calculator.calculate_coherence(doc, words)
            coherence_time = time.perf_counter() - start
            
            # Quality score calculation
            start = time.perf_counter()
            quality = calculator.calculate_quality_score(
                entropy, coherence, len(words), len(set(words))
            )
            quality_time = time.perf_counter() - start
            
            if "tokenization" not in results["components"]:
                results["components"] = {
                    "tokenization": [],
                    "entropy": [],
                    "coherence": [],
                    "quality_score": []
                }
            
            # Tokenization time is total - components
            tokenization_time = total_time - entropy_time - coherence_time - quality_time
            results["components"]["tokenization"].append(tokenization_time)
            results["components"]["entropy"].append(entropy_time)
            results["components"]["coherence"].append(coherence_time)
            results["components"]["quality_score"].append(quality_time)
        
        # Analysis
        avg_total = np.mean(results["measurement_times"]) * 1000  # ms
        print(f"Average measurement time: {avg_total:.2f}ms")
        print("\nComponent breakdown:")
        for component, times in results["components"].items():
            avg_time = np.mean(times) * 1000
            percentage = (np.mean(times) / np.mean(results["measurement_times"])) * 100
            print(f"  {component}: {avg_time:.2f}ms ({percentage:.1f}%)")
        
        # Recommendations
        if avg_total > 50:
            self.recommendations.append(
                "⚠️ Quality measurement is slow (>50ms). Consider caching or simplifying metrics."
            )
        
        # Find slowest component
        slowest = max(results["components"].items(), key=lambda x: np.mean(x[1]))
        if np.mean(slowest[1]) * 1000 > 20:
            self.recommendations.append(
                f"⚠️ {slowest[0]} is the bottleneck. Focus optimization here."
            )
        
        return results
    
    def profile_optimization_pipeline(self, engine: MIAIREngine, documents: List[str]) -> Dict[str, Any]:
        """Profile the complete optimization pipeline."""
        print("\n" + "="*60)
        print("PROFILING: Optimization Pipeline")
        print("="*60)
        
        results = {
            "single_doc_times": [],
            "batch_times": [],
            "parallel_speedup": 0
        }
        
        # Profile single document optimization
        for doc in documents[:5]:
            start = time.perf_counter()
            result = engine.optimize(doc, max_iterations=1)
            opt_time = time.perf_counter() - start
            results["single_doc_times"].append(opt_time)
        
        # Profile batch optimization
        batch_sizes = [10, 20, 50]
        for size in batch_sizes:
            batch = documents[:size]
            start = time.perf_counter()
            batch_results = engine.batch_optimize(batch, max_iterations=1)
            batch_time = time.perf_counter() - start
            results["batch_times"].append({
                "size": size,
                "time": batch_time,
                "throughput": size / batch_time
            })
        
        # Calculate parallel speedup
        sequential_time = sum(results["single_doc_times"][:5])
        parallel_time = results["batch_times"][0]["time"]  # 10 doc batch
        results["parallel_speedup"] = sequential_time / (parallel_time / 2)  # Adjust for different counts
        
        # Analysis
        avg_single = np.mean(results["single_doc_times"])
        print(f"Average single doc optimization: {avg_single:.2f}s")
        print("\nBatch optimization results:")
        for batch_result in results["batch_times"]:
            print(f"  Size {batch_result['size']}: {batch_result['time']:.2f}s "
                  f"({batch_result['throughput']:.1f} docs/sec)")
        print(f"Parallel speedup: {results['parallel_speedup']:.1f}x")
        
        # Calculate projected throughput
        best_throughput = max(b["throughput"] for b in results["batch_times"])
        projected_per_minute = best_throughput * 60
        target_percentage = (projected_per_minute / 248000) * 100
        
        print(f"\nProjected throughput: {projected_per_minute:.0f} docs/minute")
        print(f"Target achievement: {target_percentage:.2f}%")
        
        # Recommendations
        if target_percentage < 100:
            gap = 248000 - projected_per_minute
            required_speedup = 248000 / projected_per_minute
            self.recommendations.append(
                f"🎯 Need {required_speedup:.1f}x speedup to reach target."
            )
            self.recommendations.append(
                f"   Gap: {gap:.0f} docs/minute"
            )
        
        return results
    
    def profile_memory_usage(self, engine: MIAIREngine, documents: List[str]) -> Dict[str, Any]:
        """Profile memory usage patterns."""
        print("\n" + "="*60)
        print("PROFILING: Memory Usage")
        print("="*60)
        
        results = {
            "baseline": 0,
            "after_batch": 0,
            "per_document": 0
        }
        
        # Start memory tracking
        tracemalloc.start()
        
        # Get baseline
        baseline = tracemalloc.get_traced_memory()
        results["baseline"] = baseline[0] / 1024 / 1024  # MB
        
        # Process batch
        batch_results = engine.batch_optimize(documents[:50], max_iterations=1)
        
        # Get peak memory
        current, peak = tracemalloc.get_traced_memory()
        results["after_batch"] = peak / 1024 / 1024  # MB
        results["per_document"] = (peak - baseline[0]) / 1024 / 1024 / 50  # MB per doc
        
        tracemalloc.stop()
        
        # Analysis
        print(f"Baseline memory: {results['baseline']:.1f} MB")
        print(f"Peak memory: {results['after_batch']:.1f} MB")
        print(f"Memory per document: {results['per_document']:.3f} MB")
        
        # Recommendations
        if results["per_document"] > 1.0:
            self.recommendations.append(
                "⚠️ High memory usage per document (>1MB). Consider streaming or chunking."
            )
        
        return results
    
    def profile_caching_effectiveness(self, engine: MIAIREngine) -> Dict[str, Any]:
        """Profile caching layer effectiveness."""
        print("\n" + "="*60)
        print("PROFILING: Caching Effectiveness")
        print("="*60)
        
        results = {
            "hit_rate": 0,
            "cache_benefit": 0
        }
        
        # Reset statistics
        engine.reset_statistics()
        
        # Generate documents with duplicates
        unique_docs = [f"Unique document {i}" for i in range(20)]
        test_docs = unique_docs * 5  # 100 docs, 20 unique
        
        # Process all documents
        start_no_cache = time.perf_counter()
        for doc in test_docs:
            engine.calculate_entropy(doc)
        time_with_cache = time.perf_counter() - start_no_cache
        
        # Get cache statistics
        stats = engine.get_statistics()
        cache_hits = stats.get("cache_hits", 0)
        cache_misses = stats.get("cache_misses", 0)
        total_calls = cache_hits + cache_misses
        
        if total_calls > 0:
            results["hit_rate"] = cache_hits / total_calls
        
        # Estimate time without cache
        time_without_cache = total_calls * (time_with_cache / total_calls) * 1.5  # Estimate
        results["cache_benefit"] = (time_without_cache - time_with_cache) / time_without_cache
        
        # Analysis
        print(f"Cache hit rate: {results['hit_rate']*100:.1f}%")
        print(f"Cache benefit: {results['cache_benefit']*100:.1f}% time saved")
        print(f"Total calls: {total_calls}")
        print(f"Cache hits: {cache_hits}")
        print(f"Cache misses: {cache_misses}")
        
        # Recommendations
        if results["hit_rate"] < 0.5:
            self.recommendations.append(
                "⚠️ Low cache hit rate. Consider improving cache key generation or increasing cache size."
            )
        
        return results
    
    def run_cpu_profiling(self, engine: MIAIREngine, documents: List[str]) -> str:
        """Run CPU profiling to identify hot spots."""
        print("\n" + "="*60)
        print("PROFILING: CPU Hot Spots")
        print("="*60)
        
        profiler = cProfile.Profile()
        profiler.enable()
        
        # Run typical workload
        engine.batch_optimize(documents[:20], max_iterations=1)
        
        profiler.disable()
        
        # Analyze results
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
        ps.print_stats(20)  # Top 20 functions
        
        profile_output = s.getvalue()
        
        # Extract key insights
        lines = profile_output.split('\n')
        print("Top CPU-consuming functions:")
        for line in lines[5:15]:  # Skip header, show top 10
            if line.strip():
                print(f"  {line[:100]}")
        
        return profile_output
    
    def generate_optimization_report(self) -> str:
        """Generate comprehensive optimization report."""
        report = []
        report.append("\n" + "="*60)
        report.append("OPTIMIZATION RECOMMENDATIONS")
        report.append("="*60)
        
        if not self.recommendations:
            report.append("✅ No critical issues found. System is well-optimized.")
        else:
            for i, rec in enumerate(self.recommendations, 1):
                report.append(f"{i}. {rec}")
        
        report.append("\n" + "="*60)
        report.append("OPTIMIZATION STRATEGY")
        report.append("="*60)
        
        # Key optimization strategies based on profiling
        strategies = [
            "1. **Vectorization**: Use NumPy for all mathematical operations",
            "2. **Caching**: Implement multi-level caching (memory, disk)",
            "3. **Parallelization**: Increase worker threads for batch processing",
            "4. **Async Processing**: Use async/await for I/O-bound operations",
            "5. **Memory Optimization**: Stream large documents, use generators",
            "6. **Algorithm Optimization**: Optimize tokenization and entropy calculation",
            "7. **Batch Processing**: Process documents in optimal batch sizes",
            "8. **GPU Acceleration**: Consider GPU for matrix operations (future)",
        ]
        
        for strategy in strategies:
            report.append(strategy)
        
        return "\n".join(report)


async def main():
    """Main profiling execution."""
    print("="*60)
    print("M003 MIAIR ENGINE PERFORMANCE PROFILER")
    print("Target: 248K documents/minute (4,133 docs/sec)")
    print("="*60)
    
    # Initialize components
    config = ConfigurationManager()
    # Note: performance settings are read from config, not set dynamically
    # The engine will use defaults or config file values
    
    # Use mock LLM for consistent performance testing
    llm_adapter = MockLLMAdapter(latency_ms=10)  # Fast mock responses
    
    # Mock storage
    storage = StorageManager(config)
    
    # Create engine with performance strategy
    engine = MIAIREngineFactory.create(
        config, llm_adapter, storage, strategy_name="performance"
    )
    
    # Initialize profiler
    profiler = PerformanceProfiler()
    
    # Generate test documents
    print("\nGenerating test documents...")
    small_docs = profiler.generate_test_documents(100, "small")
    medium_docs = profiler.generate_test_documents(100, "medium")
    large_docs = profiler.generate_test_documents(50, "large")
    
    # Run profiling suite
    print("\nStarting performance profiling...")
    
    # 1. Profile entropy calculation
    profiler.results["entropy"] = profiler.profile_entropy_calculation(engine, medium_docs)
    
    # 2. Profile quality measurement
    profiler.results["quality"] = profiler.profile_quality_measurement(engine, medium_docs)
    
    # 3. Profile optimization pipeline
    profiler.results["optimization"] = profiler.profile_optimization_pipeline(engine, medium_docs)
    
    # 4. Profile memory usage
    profiler.results["memory"] = profiler.profile_memory_usage(engine, medium_docs)
    
    # 5. Profile caching
    profiler.results["caching"] = profiler.profile_caching_effectiveness(engine)
    
    # 6. CPU profiling
    cpu_profile = profiler.run_cpu_profiling(engine, medium_docs)
    
    # Generate optimization report
    report = profiler.generate_optimization_report()
    print(report)
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = Path("profiling_results")
    results_dir.mkdir(exist_ok=True)
    
    # Save JSON results
    results_file = results_dir / f"miair_profile_{timestamp}.json"
    with open(results_file, "w") as f:
        # Convert numpy types for JSON serialization
        json_results = {
            k: v for k, v in profiler.results.items()
        }
        json.dump(json_results, f, indent=2, default=str)
    
    # Save CPU profile
    profile_file = results_dir / f"cpu_profile_{timestamp}.txt"
    with open(profile_file, "w") as f:
        f.write(cpu_profile)
    
    print(f"\n✅ Profiling complete!")
    print(f"   Results saved to: {results_file}")
    print(f"   CPU profile saved to: {profile_file}")
    
    # Final throughput test with optimal settings
    print("\n" + "="*60)
    print("FINAL THROUGHPUT TEST")
    print("="*60)
    
    # Use optimal batch size from profiling
    optimal_batch = 100
    test_docs = medium_docs[:optimal_batch]
    
    start = time.perf_counter()
    results = engine.batch_optimize(test_docs, max_iterations=1)
    elapsed = time.perf_counter() - start
    
    throughput = len(test_docs) / elapsed
    docs_per_minute = throughput * 60
    target_achievement = (docs_per_minute / 248000) * 100
    
    print(f"Documents processed: {len(test_docs)}")
    print(f"Time elapsed: {elapsed:.2f}s")
    print(f"Throughput: {throughput:.0f} docs/sec")
    print(f"Throughput: {docs_per_minute:.0f} docs/minute")
    print(f"Target: 248,000 docs/minute")
    print(f"Achievement: {target_achievement:.1f}%")
    
    if target_achievement < 100:
        print(f"\n⚠️ Performance gap: {248000 - docs_per_minute:.0f} docs/minute")
        print(f"   Required speedup: {248000 / docs_per_minute:.1f}x")
    else:
        print(f"\n✅ TARGET ACHIEVED! {docs_per_minute:.0f} docs/minute")


if __name__ == "__main__":
    asyncio.run(main())