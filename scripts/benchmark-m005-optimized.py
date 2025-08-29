#!/usr/bin/env python3
"""
Performance benchmarking script for M005 Quality Engine - Optimized Version.

Compares original vs optimized implementation performance.
"""

import sys
import time
import os
import json
import random
import string
from pathlib import Path
from typing import Dict, List
import numpy as np
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import both versions
from devdocai.quality.analyzer import QualityAnalyzer
from devdocai.quality.analyzer_optimized import OptimizedQualityAnalyzer
from devdocai.quality.models import QualityConfig


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


class ComparativeBenchmark:
    """Comparative benchmarking between original and optimized versions."""
    
    def __init__(self):
        """Initialize both analyzers."""
        # Configure for fair comparison
        config = QualityConfig(
            quality_gate_threshold=0.0,
            enable_caching=False,  # Disable for fair comparison
            parallel_analysis=False  # Will test both modes
        )
        
        self.original_analyzer = QualityAnalyzer(config=config)
        self.optimized_analyzer = OptimizedQualityAnalyzer(config=config)
        self.doc_generator = DocumentGenerator()
    
    def benchmark_single_document(self, analyzer, size: str, iterations: int = 5) -> Dict:
        """Benchmark single document analysis."""
        times = []
        
        for _ in range(iterations):
            content = self.doc_generator.generate_document(size)
            
            start_time = time.perf_counter()
            analyzer.analyze(
                content=content,
                document_id=f"bench_{size}_{time.time()}",
                document_type='markdown'
            )
            end_time = time.perf_counter()
            
            times.append((end_time - start_time) * 1000)
        
        return {
            'mean_ms': np.mean(times),
            'std_ms': np.std(times),
            'min_ms': np.min(times),
            'max_ms': np.max(times)
        }
    
    def benchmark_batch_processing(self, analyzer, size: str, batch_size: int = 50) -> Dict:
        """Benchmark batch processing."""
        documents = [
            self.doc_generator.generate_document(size)
            for _ in range(batch_size)
        ]
        
        start_time = time.perf_counter()
        
        for i, doc in enumerate(documents):
            analyzer.analyze(
                content=doc,
                document_id=f"batch_{size}_{i}",
                document_type='markdown'
            )
        
        end_time = time.perf_counter()
        
        total_time = end_time - start_time
        throughput = batch_size / total_time if total_time > 0 else 0
        
        return {
            'total_time_s': total_time,
            'throughput_docs_per_sec': throughput,
            'avg_time_per_doc_ms': (total_time / batch_size) * 1000
        }
    
    def benchmark_parallel_processing(self) -> Dict:
        """Test parallel processing capabilities."""
        # Create config with parallel enabled
        parallel_config = QualityConfig(
            quality_gate_threshold=0.0,
            enable_caching=False,
            parallel_analysis=True,
            max_workers=4
        )
        
        optimized_parallel = OptimizedQualityAnalyzer(config=parallel_config)
        
        # Test with medium documents
        content = self.doc_generator.generate_document('medium')
        
        # Sequential timing
        start = time.perf_counter()
        for _ in range(10):
            self.optimized_analyzer.analyze(
                content=content,
                document_id=f"seq_{time.time()}",
                document_type='markdown'
            )
        seq_time = time.perf_counter() - start
        
        # Parallel timing
        start = time.perf_counter()
        for _ in range(10):
            optimized_parallel.analyze(
                content=content,
                document_id=f"par_{time.time()}",
                document_type='markdown'
            )
        par_time = time.perf_counter() - start
        
        return {
            'sequential_time_s': seq_time,
            'parallel_time_s': par_time,
            'speedup': seq_time / par_time if par_time > 0 else 0
        }
    
    def benchmark_caching_effectiveness(self) -> Dict:
        """Test caching effectiveness."""
        # Create config with caching enabled
        cache_config = QualityConfig(
            quality_gate_threshold=0.0,
            enable_caching=True,
            cache_ttl_seconds=3600
        )
        
        cached_analyzer = OptimizedQualityAnalyzer(config=cache_config)
        content = self.doc_generator.generate_document('medium')
        doc_id = "cache_test_doc"
        
        # First analysis (cache miss)
        start = time.perf_counter()
        cached_analyzer.analyze(
            content=content,
            document_id=doc_id,
            document_type='markdown'
        )
        first_time = (time.perf_counter() - start) * 1000
        
        # Second analysis (cache hit)
        start = time.perf_counter()
        cached_analyzer.analyze(
            content=content,
            document_id=doc_id,
            document_type='markdown'
        )
        cached_time = (time.perf_counter() - start) * 1000
        
        return {
            'first_analysis_ms': first_time,
            'cached_analysis_ms': cached_time,
            'cache_speedup': first_time / cached_time if cached_time > 0 else 0
        }
    
    def benchmark_streaming_large_docs(self) -> Dict:
        """Test streaming for large documents."""
        # Generate very large document
        very_large_content = '\n\n'.join([
            self.doc_generator.generate_document('large')
            for _ in range(5)
        ])
        
        print(f"Testing with document size: {len(very_large_content)} characters")
        
        # Standard analysis
        start = time.perf_counter()
        self.optimized_analyzer.analyze(
            content=very_large_content[:50000],  # Non-streaming size
            document_id="standard_large",
            document_type='markdown'
        )
        standard_time = (time.perf_counter() - start) * 1000
        
        # Streaming analysis
        start = time.perf_counter()
        self.optimized_analyzer.analyze(
            content=very_large_content,  # Will trigger streaming
            document_id="streaming_large",
            document_type='markdown'
        )
        streaming_time = (time.perf_counter() - start) * 1000
        
        return {
            'document_size_chars': len(very_large_content),
            'standard_time_ms': standard_time,
            'streaming_time_ms': streaming_time,
            'streaming_efficiency': standard_time / streaming_time if streaming_time > 0 else 0
        }
    
    def run_comprehensive_comparison(self) -> Dict:
        """Run comprehensive comparison between original and optimized."""
        print("=" * 70)
        print("M005 Quality Engine - Performance Optimization Comparison")
        print("=" * 70)
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'single_document': {},
            'batch_processing': {},
            'optimizations': {}
        }
        
        # Test different document sizes
        sizes = ['small', 'medium', 'large', 'very_large']
        
        print("\n1. Single Document Analysis Comparison:")
        print("-" * 50)
        
        for size in sizes:
            print(f"\nTesting {size} documents...")
            
            # Original version
            print("  Original: ", end='', flush=True)
            original = self.benchmark_single_document(
                self.original_analyzer, size,
                iterations=5 if size != 'very_large' else 2
            )
            print(f"{original['mean_ms']:.2f}ms (±{original['std_ms']:.2f}ms)")
            
            # Optimized version
            print("  Optimized: ", end='', flush=True)
            optimized = self.benchmark_single_document(
                self.optimized_analyzer, size,
                iterations=5 if size != 'very_large' else 2
            )
            print(f"{optimized['mean_ms']:.2f}ms (±{optimized['std_ms']:.2f}ms)")
            
            # Calculate improvement
            improvement = (original['mean_ms'] - optimized['mean_ms']) / original['mean_ms'] * 100
            speedup = original['mean_ms'] / optimized['mean_ms']
            
            print(f"  Improvement: {improvement:.1f}% ({speedup:.2f}x faster)")
            
            results['single_document'][size] = {
                'original_ms': original['mean_ms'],
                'optimized_ms': optimized['mean_ms'],
                'improvement_percent': improvement,
                'speedup': speedup
            }
        
        print("\n2. Batch Processing Comparison:")
        print("-" * 50)
        
        for size in ['small', 'medium']:
            print(f"\nBatch of 50 {size} documents:")
            
            # Original
            print("  Original: ", end='', flush=True)
            original_batch = self.benchmark_batch_processing(
                self.original_analyzer, size, batch_size=50
            )
            print(f"{original_batch['throughput_docs_per_sec']:.2f} docs/sec")
            
            # Optimized
            print("  Optimized: ", end='', flush=True)
            optimized_batch = self.benchmark_batch_processing(
                self.optimized_analyzer, size, batch_size=50
            )
            print(f"{optimized_batch['throughput_docs_per_sec']:.2f} docs/sec")
            
            improvement = (
                (optimized_batch['throughput_docs_per_sec'] - 
                 original_batch['throughput_docs_per_sec']) /
                original_batch['throughput_docs_per_sec'] * 100
            )
            
            print(f"  Improvement: {improvement:.1f}%")
            
            results['batch_processing'][size] = {
                'original_throughput': original_batch['throughput_docs_per_sec'],
                'optimized_throughput': optimized_batch['throughput_docs_per_sec'],
                'improvement_percent': improvement
            }
        
        print("\n3. Optimization Features:")
        print("-" * 50)
        
        # Test parallel processing
        print("\nParallel Processing:")
        parallel_results = self.benchmark_parallel_processing()
        print(f"  Sequential: {parallel_results['sequential_time_s']:.2f}s")
        print(f"  Parallel: {parallel_results['parallel_time_s']:.2f}s")
        print(f"  Speedup: {parallel_results['speedup']:.2f}x")
        results['optimizations']['parallel'] = parallel_results
        
        # Test caching
        print("\nCaching Effectiveness:")
        cache_results = self.benchmark_caching_effectiveness()
        print(f"  First analysis: {cache_results['first_analysis_ms']:.2f}ms")
        print(f"  Cached analysis: {cache_results['cached_analysis_ms']:.2f}ms")
        print(f"  Cache speedup: {cache_results['cache_speedup']:.1f}x")
        results['optimizations']['caching'] = cache_results
        
        # Test streaming
        print("\nStreaming for Large Documents:")
        streaming_results = self.benchmark_streaming_large_docs()
        print(f"  Document size: {streaming_results['document_size_chars']:,} chars")
        print(f"  Standard: {streaming_results['standard_time_ms']:.2f}ms")
        print(f"  Streaming: {streaming_results['streaming_time_ms']:.2f}ms")
        results['optimizations']['streaming'] = streaming_results
        
        # Performance targets check
        print("\n4. Performance Targets Achievement:")
        print("-" * 50)
        
        targets = {
            'small': (3, results['single_document']['small']['optimized_ms']),
            'medium': (10, results['single_document']['medium']['optimized_ms']),
            'large': (50, results['single_document']['large']['optimized_ms']),
            'very_large': (100, results['single_document']['very_large']['optimized_ms']),
        }
        
        all_passed = True
        for size, (target, actual) in targets.items():
            status = "✓ PASS" if actual <= target else "✗ FAIL"
            print(f"  {size}: {actual:.2f}ms / {target}ms target - {status}")
            if actual > target:
                all_passed = False
        
        # Batch processing target
        batch_target = 100
        batch_actual = results['batch_processing']['medium']['optimized_throughput']
        batch_status = "✓ PASS" if batch_actual >= batch_target else "✗ FAIL"
        print(f"  Batch: {batch_actual:.2f} docs/sec / {batch_target} target - {batch_status}")
        if batch_actual < batch_target:
            all_passed = False
        
        results['targets_achieved'] = all_passed
        
        # Save results
        output_file = Path(__file__).parent / 'benchmark_comparison_m005.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nResults saved to: {output_file}")
        
        if all_passed:
            print("\n✓ All performance targets achieved!")
        else:
            print("\n✗ Some targets not met. Further optimization needed.")
        
        return results


def main():
    """Main entry point."""
    benchmark = ComparativeBenchmark()
    results = benchmark.run_comprehensive_comparison()
    
    # Return exit code based on targets
    return 0 if results.get('targets_achieved', False) else 1


if __name__ == '__main__':
    sys.exit(main())