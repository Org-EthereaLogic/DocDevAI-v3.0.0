#!/usr/bin/env python3
"""
M004 Document Generator Performance Benchmark Script

Measures baseline performance and identifies bottlenecks for Pass 2 optimization.
Targets: 10 documents/second, <100ms latency, <100MB memory for 1000 docs
"""

import asyncio
import json
import os
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Dict, Any, List
import cProfile
import pstats
import io
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from devdocai.core.config import ConfigurationManager, MemoryMode
from devdocai.storage.storage_manager_unified import UnifiedStorageManager, OperationMode
from devdocai.miair.engine_unified_final import MIAIREngineUnified
from devdocai.core.generator import (
    UnifiedDocumentGenerator, DocumentType, OutputFormat, GenerationMode
)


class GeneratorBenchmark:
    """Performance benchmark for M004 Document Generator."""
    
    def __init__(self):
        """Initialize benchmark components."""
        self.results = {
            'baseline': {},
            'optimized': {},
            'memory': {},
            'profiling': {}
        }
        
    async def setup_generator(self, mode: str = 'basic') -> UnifiedDocumentGenerator:
        """Setup generator with specified mode."""
        # Create config manager
        config_manager = ConfigurationManager()
        config_manager.set('operation_mode', mode)
        config_manager.set('quality_gate_threshold', 85.0)
        
        # Set memory mode based on operation mode
        memory_modes = {
            'basic': MemoryMode.BASELINE,
            'performance': MemoryMode.PERFORMANCE,
            'secure': MemoryMode.STANDARD,
            'enterprise': MemoryMode.ENHANCED
        }
        config_manager.set('memory_mode', memory_modes.get(mode, MemoryMode.STANDARD))
        
        # Create storage manager
        storage_manager = UnifiedStorageManager(
            config_manager=config_manager,
            mode=OperationMode(mode.lower())  # Use lowercase for enum
        )
        
        # Create MIAIR engine
        miair_engine = MIAIREngineUnified(
            config_manager=config_manager,
            storage_manager=storage_manager,
            mode=OperationMode(mode.lower())  # Use lowercase for enum
        )
        
        # Create generator
        generator = UnifiedDocumentGenerator(
            config_manager=config_manager,
            storage_manager=storage_manager,
            miair_engine=miair_engine
        )
        
        # Register test templates
        await self._register_test_templates(generator)
        
        return generator
    
    async def _register_test_templates(self, generator: UnifiedDocumentGenerator):
        """Register test templates for benchmarking."""
        templates = {
            'simple': """# {{ title }}

{{ description }}

## Features
{% for feature in features %}
- {{ feature }}
{% endfor %}

## Installation
```bash
{{ installation_command }}
```

## Usage
{{ usage_example }}

## License
{{ license }}
""",
            'complex': """# {{ project_name }} - {{ version }}

[![Build Status]({{ build_badge }})]({{ build_url }})
[![Coverage]({{ coverage_badge }})]({{ coverage_url }})
[![License]({{ license_badge }})]({{ license_url }})

{{ description }}

## Table of Contents
{% for section in sections %}
- [{{ section.title }}](#{{ section.anchor }})
{% endfor %}

## Requirements
{% for req in requirements %}
- {{ req.name }} {{ req.version }}
  - {{ req.description }}
{% endfor %}

## Architecture
```mermaid
{{ architecture_diagram }}
```

## API Reference
{% for endpoint in api_endpoints %}
### {{ endpoint.method }} {{ endpoint.path }}

{{ endpoint.description }}

**Parameters:**
{% for param in endpoint.parameters %}
- `{{ param.name }}` ({{ param.type }}): {{ param.description }}
{% endfor %}

**Response:**
```json
{{ endpoint.response_example }}
```
{% endfor %}

## Contributing
{{ contributing_guidelines }}

## Changelog
{% for release in changelog %}
### {{ release.version }} - {{ release.date }}
{% for change in release.changes %}
- {{ change.type }}: {{ change.description }}
{% endfor %}
{% endfor %}

## License
{{ license_text }}
"""
        }
        
        for name, content in templates.items():
            try:
                await generator.register_template(
                    name=f"benchmark_{name}",
                    content=content,
                    category="benchmark"
                )
            except Exception:
                pass  # Template might already exist
    
    def get_simple_variables(self) -> Dict[str, Any]:
        """Get simple template variables."""
        return {
            'title': 'Test Document',
            'description': 'This is a test document for benchmarking purposes.',
            'features': ['Feature 1', 'Feature 2', 'Feature 3'],
            'installation_command': 'pip install test-package',
            'usage_example': 'import test_package\ntest_package.run()',
            'license': 'MIT'
        }
    
    def get_complex_variables(self) -> Dict[str, Any]:
        """Get complex template variables."""
        return {
            'project_name': 'BenchmarkProject',
            'version': '1.0.0',
            'build_badge': 'https://img.shields.io/badge/build-passing-green',
            'build_url': 'https://ci.example.com',
            'coverage_badge': 'https://img.shields.io/badge/coverage-95%25-green',
            'coverage_url': 'https://coverage.example.com',
            'license_badge': 'https://img.shields.io/badge/license-MIT-blue',
            'license_url': 'https://opensource.org/licenses/MIT',
            'description': 'A comprehensive project for performance benchmarking.',
            'sections': [
                {'title': 'Installation', 'anchor': 'installation'},
                {'title': 'Usage', 'anchor': 'usage'},
                {'title': 'API', 'anchor': 'api'},
                {'title': 'Contributing', 'anchor': 'contributing'}
            ],
            'requirements': [
                {'name': 'Python', 'version': '>=3.8', 'description': 'Core runtime'},
                {'name': 'SQLite', 'version': '>=3.0', 'description': 'Database backend'},
                {'name': 'Jinja2', 'version': '>=3.0', 'description': 'Template engine'}
            ],
            'architecture_diagram': 'graph TD\n  A[Client] --> B[API]\n  B --> C[Core]\n  C --> D[Database]',
            'api_endpoints': [
                {
                    'method': 'POST',
                    'path': '/api/documents',
                    'description': 'Create a new document',
                    'parameters': [
                        {'name': 'type', 'type': 'string', 'description': 'Document type'},
                        {'name': 'content', 'type': 'string', 'description': 'Document content'}
                    ],
                    'response_example': '{"id": "doc_123", "status": "created"}'
                }
            ],
            'contributing_guidelines': 'Please read CONTRIBUTING.md for details.',
            'changelog': [
                {
                    'version': 'v1.0.0',
                    'date': '2024-01-01',
                    'changes': [
                        {'type': 'Added', 'description': 'Initial release'},
                        {'type': 'Fixed', 'description': 'Performance improvements'}
                    ]
                }
            ],
            'license_text': 'MIT License\n\nCopyright (c) 2024'
        }
    
    async def benchmark_single_generation(
        self,
        generator: UnifiedDocumentGenerator,
        iterations: int = 100
    ) -> Dict[str, Any]:
        """Benchmark single document generation."""
        print(f"\n📊 Benchmarking single document generation ({iterations} iterations)...")
        
        results = {
            'simple_template': {'times': [], 'cache_hits': 0},
            'complex_template': {'times': [], 'cache_hits': 0}
        }
        
        # Test simple template
        for i in range(iterations):
            start = time.perf_counter()
            
            result = await generator.generate_document(
                doc_type=DocumentType.README,
                template_id='template_benchmark_simple',
                variables=self.get_simple_variables(),
                output_format=OutputFormat.MARKDOWN,
                enforce_quality_gate=False  # Disable for pure generation testing
            )
            
            elapsed = time.perf_counter() - start
            results['simple_template']['times'].append(elapsed)
            
            if i > 0 and elapsed < 0.001:  # Likely a cache hit
                results['simple_template']['cache_hits'] += 1
        
        # Test complex template
        for i in range(iterations // 2):  # Fewer iterations for complex
            start = time.perf_counter()
            
            result = await generator.generate_document(
                doc_type=DocumentType.API,
                template_id='template_benchmark_complex',
                variables=self.get_complex_variables(),
                output_format=OutputFormat.MARKDOWN,
                enforce_quality_gate=False
            )
            
            elapsed = time.perf_counter() - start
            results['complex_template']['times'].append(elapsed)
            
            if i > 0 and elapsed < 0.001:
                results['complex_template']['cache_hits'] += 1
        
        # Calculate statistics
        for template_type in results:
            times = results[template_type]['times']
            if times:
                results[template_type]['avg_time'] = sum(times) / len(times)
                results[template_type]['min_time'] = min(times)
                results[template_type]['max_time'] = max(times)
                results[template_type]['docs_per_second'] = 1 / results[template_type]['avg_time']
                results[template_type]['cache_hit_rate'] = (
                    results[template_type]['cache_hits'] / len(times) * 100
                )
        
        return results
    
    async def benchmark_batch_generation(
        self,
        generator: UnifiedDocumentGenerator,
        batch_sizes: List[int] = [10, 25, 50]
    ) -> Dict[str, Any]:
        """Benchmark batch document generation."""
        print(f"\n📊 Benchmarking batch generation (sizes: {batch_sizes})...")
        
        results = {}
        
        for batch_size in batch_sizes:
            print(f"  Testing batch size {batch_size}...")
            
            # Create batch requests
            requests = []
            for i in range(batch_size):
                requests.append({
                    'doc_type': DocumentType.README if i % 2 == 0 else DocumentType.API,
                    'template_id': 'template_benchmark_simple' if i % 2 == 0 else 'template_benchmark_complex',
                    'variables': self.get_simple_variables() if i % 2 == 0 else self.get_complex_variables(),
                    'output_format': OutputFormat.MARKDOWN,
                    'enforce_quality_gate': False
                })
            
            start = time.perf_counter()
            batch_results = await generator.generate_batch(requests)
            elapsed = time.perf_counter() - start
            
            results[f'batch_{batch_size}'] = {
                'total_time': elapsed,
                'docs_per_second': batch_size / elapsed,
                'avg_time_per_doc': elapsed / batch_size,
                'successful': sum(1 for r in batch_results if r.success),
                'failed': sum(1 for r in batch_results if not r.success)
            }
        
        return results
    
    async def benchmark_format_conversion(
        self,
        generator: UnifiedDocumentGenerator
    ) -> Dict[str, Any]:
        """Benchmark format conversion performance."""
        print("\n📊 Benchmarking format conversion...")
        
        results = {}
        formats = [OutputFormat.HTML, OutputFormat.JSON]
        
        if generator._markdown_to_pdf.__code__.co_code != b'd\x00S\x00':  # Check if PDF is implemented
            formats.append(OutputFormat.PDF)
        
        for output_format in formats:
            times = []
            
            for _ in range(20):
                start = time.perf_counter()
                
                result = await generator.generate_document(
                    doc_type=DocumentType.README,
                    template_id='template_benchmark_simple',
                    variables=self.get_simple_variables(),
                    output_format=output_format,
                    enforce_quality_gate=False
                )
                
                elapsed = time.perf_counter() - start
                times.append(elapsed)
            
            results[output_format.value] = {
                'avg_time': sum(times) / len(times),
                'min_time': min(times),
                'max_time': max(times)
            }
        
        return results
    
    async def measure_memory_usage(
        self,
        generator: UnifiedDocumentGenerator,
        num_documents: int = 100
    ) -> Dict[str, Any]:
        """Measure memory usage during generation."""
        print(f"\n📊 Measuring memory usage for {num_documents} documents...")
        
        tracemalloc.start()
        initial_memory = tracemalloc.get_traced_memory()[0]
        
        # Generate documents
        for i in range(num_documents):
            await generator.generate_document(
                doc_type=DocumentType.README,
                template_id='template_benchmark_simple',
                variables={**self.get_simple_variables(), 'title': f'Document {i}'},
                output_format=OutputFormat.MARKDOWN,
                enforce_quality_gate=False
            )
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        return {
            'initial_memory_mb': initial_memory / 1024 / 1024,
            'current_memory_mb': current / 1024 / 1024,
            'peak_memory_mb': peak / 1024 / 1024,
            'memory_per_doc_kb': (current - initial_memory) / num_documents / 1024,
            'documents_generated': num_documents
        }
    
    async def profile_generation(
        self,
        generator: UnifiedDocumentGenerator
    ) -> str:
        """Profile document generation to identify bottlenecks."""
        print("\n📊 Profiling document generation...")
        
        profiler = cProfile.Profile()
        
        async def generate_docs():
            for _ in range(10):
                await generator.generate_document(
                    doc_type=DocumentType.API,
                    template_id='template_benchmark_complex',
                    variables=self.get_complex_variables(),
                    output_format=OutputFormat.HTML,
                    enforce_quality_gate=False
                )
        
        profiler.enable()
        await generate_docs()
        profiler.disable()
        
        # Get profiling results
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
        ps.print_stats(20)  # Top 20 functions
        
        return s.getvalue()
    
    async def run_full_benchmark(self):
        """Run complete benchmark suite."""
        print("=" * 60)
        print("M004 DOCUMENT GENERATOR PERFORMANCE BENCHMARK")
        print("=" * 60)
        
        modes = ['basic', 'performance', 'secure', 'enterprise']
        
        for mode in modes:
            print(f"\n\n🔧 Testing {mode.upper()} mode")
            print("-" * 40)
            
            try:
                # Setup generator
                generator = await self.setup_generator(mode)
                
                # Run benchmarks
                single_results = await self.benchmark_single_generation(generator)
                batch_results = await self.benchmark_batch_generation(generator)
                format_results = await self.benchmark_format_conversion(generator)
                memory_results = await self.measure_memory_usage(generator)
                
                # Store results
                self.results['baseline'][mode] = {
                    'single_generation': single_results,
                    'batch_generation': batch_results,
                    'format_conversion': format_results,
                    'memory_usage': memory_results,
                    'statistics': generator.get_statistics()
                }
                
                # Print summary
                self._print_mode_summary(mode, self.results['baseline'][mode])
                
                # Profile only performance mode
                if mode == 'performance':
                    profile_output = await self.profile_generation(generator)
                    self.results['profiling']['performance_mode'] = profile_output
                
            except Exception as e:
                print(f"❌ Error testing {mode} mode: {str(e)}")
                import traceback
                traceback.print_exc()
        
        # Generate final report
        self._generate_report()
    
    def _print_mode_summary(self, mode: str, results: Dict[str, Any]):
        """Print summary for a mode."""
        print(f"\n📈 {mode.upper()} Mode Results:")
        
        # Single generation
        if 'single_generation' in results:
            simple = results['single_generation'].get('simple_template', {})
            complex = results['single_generation'].get('complex_template', {})
            
            print(f"  Single Generation:")
            if 'docs_per_second' in simple:
                print(f"    Simple Template: {simple['docs_per_second']:.2f} docs/sec")
                print(f"      Avg Time: {simple['avg_time']*1000:.2f}ms")
                print(f"      Cache Hit Rate: {simple.get('cache_hit_rate', 0):.1f}%")
            
            if 'docs_per_second' in complex:
                print(f"    Complex Template: {complex['docs_per_second']:.2f} docs/sec")
                print(f"      Avg Time: {complex['avg_time']*1000:.2f}ms")
                print(f"      Cache Hit Rate: {complex.get('cache_hit_rate', 0):.1f}%")
        
        # Batch generation
        if 'batch_generation' in results:
            print(f"  Batch Generation:")
            for batch_key, batch_data in results['batch_generation'].items():
                size = batch_key.split('_')[1]
                print(f"    Batch Size {size}: {batch_data['docs_per_second']:.2f} docs/sec")
        
        # Memory usage
        if 'memory_usage' in results:
            mem = results['memory_usage']
            print(f"  Memory Usage:")
            print(f"    Peak: {mem['peak_memory_mb']:.2f} MB")
            print(f"    Per Document: {mem['memory_per_doc_kb']:.2f} KB")
        
        # Statistics
        if 'statistics' in results:
            stats = results['statistics']
            print(f"  Generator Statistics:")
            print(f"    Documents Generated: {stats['documents_generated']}")
            print(f"    Overall Rate: {stats.get('docs_per_second', 0):.2f} docs/sec")
    
    def _generate_report(self):
        """Generate final benchmark report."""
        print("\n" + "=" * 60)
        print("BENCHMARK SUMMARY")
        print("=" * 60)
        
        # Performance comparison
        print("\n🎯 Performance vs Target (10 docs/sec):")
        for mode in ['basic', 'performance', 'secure', 'enterprise']:
            if mode in self.results['baseline']:
                mode_data = self.results['baseline'][mode]
                if 'single_generation' in mode_data:
                    simple = mode_data['single_generation'].get('simple_template', {})
                    rate = simple.get('docs_per_second', 0)
                    status = "✅" if rate >= 10 else "❌"
                    print(f"  {mode.upper():12} {rate:8.2f} docs/sec {status}")
        
        # Memory efficiency
        print("\n💾 Memory Efficiency (<100MB for 1000 docs):")
        for mode in ['basic', 'performance', 'secure', 'enterprise']:
            if mode in self.results['baseline']:
                mode_data = self.results['baseline'][mode]
                if 'memory_usage' in mode_data:
                    mem = mode_data['memory_usage']
                    projected = mem['memory_per_doc_kb'] * 1000 / 1024  # MB for 1000 docs
                    status = "✅" if projected < 100 else "❌"
                    print(f"  {mode.upper():12} {projected:8.2f} MB {status}")
        
        # Save results to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = f'benchmark_results/m004_generator_{timestamp}.json'
        os.makedirs('benchmark_results', exist_ok=True)
        
        with open(results_file, 'w') as f:
            # Convert results to JSON-serializable format
            json_results = {
                'timestamp': timestamp,
                'baseline': self.results['baseline'],
                'memory': self.results.get('memory', {}),
                'profiling_available': 'profiling' in self.results
            }
            json.dump(json_results, f, indent=2)
        
        print(f"\n📁 Results saved to: {results_file}")
        
        # Print profiling info if available
        if 'profiling' in self.results and 'performance_mode' in self.results['profiling']:
            print("\n🔍 Performance Profiling (Top Bottlenecks):")
            print("-" * 40)
            # Print first 30 lines of profiling output
            lines = self.results['profiling']['performance_mode'].split('\n')[:30]
            for line in lines:
                print(line)


async def main():
    """Main benchmark entry point."""
    benchmark = GeneratorBenchmark()
    await benchmark.run_full_benchmark()


if __name__ == '__main__':
    asyncio.run(main())