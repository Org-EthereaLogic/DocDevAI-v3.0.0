#!/usr/bin/env python3
"""
Performance benchmarking script for M005 Quality Engine.

Tests performance with documents of various sizes and measures:
- Processing time per document
- Memory usage
- Batch processing throughput
- Cache effectiveness
"""

import sys
import time
import os
import json
import random
import string
import tracemalloc
import cProfile
import pstats
import io
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import numpy as np
from dataclasses import dataclass, asdict
import asyncio
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from devdocai.quality.analyzer import QualityAnalyzer
from devdocai.quality.models import QualityConfig


@dataclass
class BenchmarkResult:
    """Stores benchmark results for a single test."""
    doc_size: str
    word_count: int
    processing_time_ms: float
    memory_used_mb: float
    score: float
    cache_hits: int
    cache_misses: int
    throughput_docs_per_sec: float


class DocumentGenerator:
    """Generates test documents of various sizes."""
    
    TEMPLATES = {
        'small': (100, 1000),      # 100-1000 words
        'medium': (1000, 5000),     # 1K-5K words
        'large': (5000, 10000),     # 5K-10K words
        'very_large': (10000, 50000)  # 10K-50K words
    }
    
    @staticmethod
    def generate_document(size: str = 'medium') -> str:
        """Generate a test document of specified size."""
        min_words, max_words = DocumentGenerator.TEMPLATES[size]
        word_count = random.randint(min_words, max_words)
        
        # Generate realistic document structure
        sections = []
        
        # Title
        sections.append(f"# {DocumentGenerator._generate_title()}")
        sections.append("")
        
        # Abstract/Summary
        sections.append("## Summary")
        sections.append(DocumentGenerator._generate_paragraph(50, 100))
        sections.append("")
        
        # Main content
        remaining_words = word_count - 100
        num_sections = random.randint(3, 8)
        words_per_section = remaining_words // num_sections
        
        for i in range(num_sections):
            sections.append(f"## Section {i+1}: {DocumentGenerator._generate_title()}")
            sections.append("")
            
            # Add subsections
            num_subsections = random.randint(2, 4)
            words_per_subsection = words_per_section // num_subsections
            
            for j in range(num_subsections):
                sections.append(f"### {DocumentGenerator._generate_title()}")
                sections.append(DocumentGenerator._generate_paragraph(
                    words_per_subsection - 20, 
                    words_per_subsection + 20
                ))
                sections.append("")
                
                # Add code blocks occasionally
                if random.random() > 0.5:
                    sections.append("```python")
                    sections.append(DocumentGenerator._generate_code())
                    sections.append("```")
                    sections.append("")
        
        # Add conclusion
        sections.append("## Conclusion")
        sections.append(DocumentGenerator._generate_paragraph(50, 100))
        
        return "\n".join(sections)
    
    @staticmethod
    def _generate_title() -> str:
        """Generate a random title."""
        words = ['Advanced', 'Modern', 'Efficient', 'Scalable', 'Robust',
                'Innovative', 'Comprehensive', 'Strategic', 'Dynamic']
        nouns = ['System', 'Architecture', 'Framework', 'Platform', 'Solution',
                'Implementation', 'Design', 'Approach', 'Strategy']
        return f"{random.choice(words)} {random.choice(nouns)}"
    
    @staticmethod
    def _generate_paragraph(min_words: int, max_words: int) -> str:
        """Generate a paragraph with specified word count."""
        word_count = random.randint(min_words, max_words)
        words = []
        
        # Use common technical words for more realistic content
        tech_words = [
            'system', 'architecture', 'performance', 'optimization', 'algorithm',
            'data', 'processing', 'efficient', 'scalable', 'robust', 'implementation',
            'design', 'pattern', 'framework', 'module', 'component', 'interface',
            'method', 'function', 'class', 'object', 'structure', 'database',
            'network', 'security', 'authentication', 'authorization', 'encryption'
        ]
        
        for _ in range(word_count):
            if random.random() > 0.3:
                words.append(random.choice(tech_words))
            else:
                words.append(''.join(random.choices(string.ascii_lowercase, k=random.randint(3, 10))))
        
        # Form sentences
        sentences = []
        sentence_words = []
        for i, word in enumerate(words):
            sentence_words.append(word)
            if len(sentence_words) > random.randint(8, 15) or i == len(words) - 1:
                sentence = ' '.join(sentence_words)
                sentences.append(sentence.capitalize() + '.')
                sentence_words = []
        
        return ' '.join(sentences)
    
    @staticmethod
    def _generate_code() -> str:
        """Generate sample code block."""
        lines = []
        lines.append("def process_data(input_data):")
        lines.append("    # Process the input data")
        lines.append("    result = []")
        lines.append("    for item in input_data:")
        lines.append("        processed = transform(item)")
        lines.append("        result.append(processed)")
        lines.append("    return result")
        return '\n'.join(lines)


class PerformanceBenchmark:
    """Main benchmarking class for M005 Quality Engine."""
    
    def __init__(self):
        """Initialize benchmark suite."""
        # Create config with lower quality threshold for testing
        config = QualityConfig(
            quality_gate_threshold=0.0,  # Disable quality gate for performance testing
            enable_caching=False,  # Disable caching to measure raw performance
            parallel_analysis=False  # Start with sequential to get baseline
        )
        self.analyzer = QualityAnalyzer(config=config)
        self.results: List[BenchmarkResult] = []
        self.doc_generator = DocumentGenerator()
        
    def run_single_document_benchmark(self, size: str) -> BenchmarkResult:
        """Benchmark a single document analysis."""
        # Generate document
        content = self.doc_generator.generate_document(size)
        word_count = len(content.split())
        
        # Start memory tracking
        tracemalloc.start()
        memory_before = tracemalloc.get_traced_memory()[0]
        
        # Measure processing time
        start_time = time.perf_counter()
        
        report = self.analyzer.analyze(
            content=content,
            document_id=f"benchmark_{size}_{time.time()}",
            document_type='markdown'
        )
        
        end_time = time.perf_counter()
        
        # Get memory usage
        memory_after = tracemalloc.get_traced_memory()[0]
        tracemalloc.stop()
        
        memory_used_mb = (memory_after - memory_before) / (1024 * 1024)
        processing_time_ms = (end_time - start_time) * 1000
        
        return BenchmarkResult(
            doc_size=size,
            word_count=word_count,
            processing_time_ms=processing_time_ms,
            memory_used_mb=memory_used_mb,
            score=report.overall_score,
            cache_hits=0,  # Will be populated later
            cache_misses=0,
            throughput_docs_per_sec=1000 / processing_time_ms if processing_time_ms > 0 else 0
        )
    
    def run_batch_benchmark(self, size: str, batch_size: int = 100) -> Tuple[float, float]:
        """Benchmark batch processing."""
        documents = [
            self.doc_generator.generate_document(size) 
            for _ in range(batch_size)
        ]
        
        start_time = time.perf_counter()
        
        for i, doc in enumerate(documents):
            self.analyzer.analyze(
                content=doc,
                document_id=f"batch_{size}_{i}",
                document_type='markdown'
            )
        
        end_time = time.perf_counter()
        
        total_time = end_time - start_time
        throughput = batch_size / total_time if total_time > 0 else 0
        
        return total_time, throughput
    
    def profile_analysis(self, size: str = 'medium') -> str:
        """Profile the analysis to identify bottlenecks."""
        content = self.doc_generator.generate_document(size)
        
        profiler = cProfile.Profile()
        profiler.enable()
        
        self.analyzer.analyze(
            content=content,
            document_id=f"profile_{size}",
            document_type='markdown'
        )
        
        profiler.disable()
        
        # Get profile stats
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
        ps.print_stats(20)  # Top 20 functions
        
        return s.getvalue()
    
    def run_comprehensive_benchmark(self) -> Dict:
        """Run comprehensive benchmark suite."""
        print("Starting M005 Quality Engine Performance Benchmark...")
        print("=" * 60)
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'single_document': {},
            'batch_processing': {},
            'profile': {}
        }
        
        # Test different document sizes
        sizes = ['small', 'medium', 'large', 'very_large']
        
        print("\n1. Single Document Analysis:")
        print("-" * 40)
        for size in sizes:
            print(f"Testing {size} documents...")
            
            # Run multiple iterations for average
            iterations = 10 if size != 'very_large' else 3
            times = []
            memory = []
            
            for _ in range(iterations):
                result = self.run_single_document_benchmark(size)
                times.append(result.processing_time_ms)
                memory.append(result.memory_used_mb)
            
            avg_time = np.mean(times)
            avg_memory = np.mean(memory)
            
            results['single_document'][size] = {
                'avg_time_ms': avg_time,
                'min_time_ms': np.min(times),
                'max_time_ms': np.max(times),
                'std_time_ms': np.std(times),
                'avg_memory_mb': avg_memory,
                'word_count_range': DocumentGenerator.TEMPLATES[size]
            }
            
            print(f"  {size}: {avg_time:.2f}ms (±{np.std(times):.2f}ms), "
                  f"Memory: {avg_memory:.2f}MB")
        
        print("\n2. Batch Processing Performance:")
        print("-" * 40)
        for size in ['small', 'medium']:
            print(f"Testing batch of 100 {size} documents...")
            total_time, throughput = self.run_batch_benchmark(size, 100)
            
            results['batch_processing'][size] = {
                'batch_size': 100,
                'total_time_seconds': total_time,
                'throughput_docs_per_sec': throughput
            }
            
            print(f"  {size}: {throughput:.2f} docs/sec "
                  f"(total: {total_time:.2f}s)")
        
        print("\n3. Profiling Analysis (Medium Document):")
        print("-" * 40)
        profile_output = self.profile_analysis('medium')
        results['profile']['medium'] = profile_output
        
        # Print top bottlenecks
        lines = profile_output.split('\n')
        for line in lines[:10]:
            if line.strip():
                print(f"  {line}")
        
        # Performance targets check
        print("\n4. Performance Targets Check:")
        print("-" * 40)
        
        targets = {
            'small': 3,      # Target: 2-3ms
            'medium': 10,    # Target: <10ms
            'large': 50,     # Target: <50ms
            'very_large': 100  # Target: <100ms
        }
        
        for size, target in targets.items():
            actual = results['single_document'][size]['avg_time_ms']
            status = "✓ PASS" if actual <= target else "✗ FAIL"
            print(f"  {size}: {actual:.2f}ms / {target}ms target - {status}")
        
        # Batch processing target
        batch_throughput = results['batch_processing']['medium']['throughput_docs_per_sec']
        batch_status = "✓ PASS" if batch_throughput >= 100 else "✗ FAIL"
        print(f"  Batch: {batch_throughput:.2f} docs/sec / 100 target - {batch_status}")
        
        # Save results to file
        output_file = Path(__file__).parent / 'benchmark_results_m005.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nResults saved to: {output_file}")
        
        return results


def main():
    """Main entry point."""
    benchmark = PerformanceBenchmark()
    results = benchmark.run_comprehensive_benchmark()
    
    # Return exit code based on targets
    small_pass = results['single_document']['small']['avg_time_ms'] <= 3
    medium_pass = results['single_document']['medium']['avg_time_ms'] <= 10
    large_pass = results['single_document']['large']['avg_time_ms'] <= 50
    very_large_pass = results['single_document']['very_large']['avg_time_ms'] <= 100
    batch_pass = results['batch_processing']['medium']['throughput_docs_per_sec'] >= 100
    
    if all([small_pass, medium_pass, large_pass, very_large_pass, batch_pass]):
        print("\n✓ All performance targets achieved!")
        return 0
    else:
        print("\n✗ Some performance targets not met. Optimization needed.")
        return 1


if __name__ == '__main__':
    sys.exit(main())