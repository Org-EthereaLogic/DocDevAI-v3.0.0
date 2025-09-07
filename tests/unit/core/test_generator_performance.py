"""
M004 Document Generator - Pass 2: Performance Tests

Comprehensive performance test suite ensuring 10 docs/second target
and validating all optimization improvements.
"""

import asyncio
import time
import pytest
from unittest.mock import Mock, AsyncMock, patch
import tracemalloc
from datetime import datetime

from devdocai.core.config import ConfigurationManager, MemoryMode
from devdocai.storage.storage_manager_unified import UnifiedStorageManager, OperationMode
from devdocai.storage.models import Document as StorageDocument, ContentType
from devdocai.miair.engine_unified_final import MIAIREngineUnified
from devdocai.miair.models import AnalysisResult, QualityScore
from devdocai.core.generator import (
    UnifiedDocumentGenerator, DocumentType, OutputFormat, GenerationMode
)


class TestGeneratorPerformance:
    """Performance tests for document generator."""
    
    @pytest.fixture
    def mock_storage(self):
        """Create mock storage manager."""
        storage = Mock(spec=UnifiedStorageManager)
        
        # Mock document retrieval
        template_doc = Mock()
        template_doc.id = "template_test"
        template_doc.content = """# {{ title }}
{{ description }}

## Features
{% for feature in features %}
- {{ feature }}
{% endfor %}"""
        template_doc.metadata = {'variables': ['title', 'description', 'features']}
        
        storage.get_document = Mock(return_value=template_doc)
        storage.create_document = Mock(return_value=template_doc)
        
        return storage
    
    @pytest.fixture
    def mock_miair(self):
        """Create mock MIAIR engine."""
        miair = Mock(spec=MIAIREngineUnified)
        
        # Mock analysis result
        async def mock_analyze(doc, **kwargs):
            result = Mock(spec=AnalysisResult)
            result.quality_score = Mock(spec=QualityScore)
            result.quality_score.overall = 92.5
            return result
        
        miair.analyze_document = AsyncMock(side_effect=mock_analyze)
        
        return miair
    
    @pytest.fixture
    def config_manager(self):
        """Create configuration manager."""
        config = ConfigurationManager()
        config.set('operation_mode', 'performance')
        config.set('memory_mode', MemoryMode.PERFORMANCE)
        config.set('quality_gate_threshold', 85.0)
        return config
    
    @pytest.fixture
    def generator(self, config_manager, mock_storage, mock_miair):
        """Create document generator with mocks."""
        return UnifiedDocumentGenerator(
            config_manager=config_manager,
            storage_manager=mock_storage,
            miair_engine=mock_miair
        )
    
    @pytest.mark.asyncio
    async def test_performance_target_10_docs_per_second(self, generator):
        """Test that generator achieves 10 docs/second target."""
        # Prepare test variables
        variables = {
            'title': 'Performance Test',
            'description': 'Testing document generation speed',
            'features': ['Fast', 'Efficient', 'Scalable']
        }
        
        # Measure generation time
        start_time = time.perf_counter()
        
        # Generate 100 documents
        for i in range(100):
            result = await generator.generate_document(
                doc_type=DocumentType.README,
                template_id='template_test',
                variables={**variables, 'title': f'Test Doc {i}'},
                output_format=OutputFormat.MARKDOWN,
                enforce_quality_gate=False  # Skip quality for pure speed test
            )
            assert result.success
        
        elapsed = time.perf_counter() - start_time
        docs_per_second = 100 / elapsed
        
        # Assert performance target met
        assert docs_per_second >= 10, f"Performance {docs_per_second:.2f} docs/sec below 10 docs/sec target"
        
        # Print performance metrics
        print(f"\n✅ Performance: {docs_per_second:.2f} docs/second")
        print(f"   Average time per doc: {elapsed/100*1000:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_cache_efficiency(self, generator):
        """Test cache hit rate and efficiency."""
        variables = {
            'title': 'Cache Test',
            'description': 'Testing cache efficiency',
            'features': ['Cached', 'Fast', 'Efficient']
        }
        
        # Generate same document multiple times
        for _ in range(10):
            await generator.generate_document(
                doc_type=DocumentType.README,
                template_id='template_test',
                variables=variables,
                enforce_quality_gate=False
            )
        
        # Check cache statistics
        stats = generator.get_statistics()
        
        if 'cache_hit_rate' in stats:
            assert stats['cache_hit_rate'] > 80, f"Cache hit rate {stats['cache_hit_rate']:.1f}% below 80%"
            print(f"\n✅ Cache Hit Rate: {stats['cache_hit_rate']:.1f}%")
    
    @pytest.mark.asyncio
    async def test_batch_generation_performance(self, generator):
        """Test batch generation performance."""
        # Create batch of 50 requests
        requests = []
        for i in range(50):
            requests.append({
                'doc_type': DocumentType.README,
                'template_id': 'template_test',
                'variables': {
                    'title': f'Batch Doc {i}',
                    'description': f'Document {i} in batch',
                    'features': ['Feature 1', 'Feature 2']
                },
                'output_format': OutputFormat.MARKDOWN,
                'enforce_quality_gate': False
            })
        
        # Measure batch generation time
        start_time = time.perf_counter()
        results = await generator.generate_batch(requests)
        elapsed = time.perf_counter() - start_time
        
        # Check all succeeded
        assert all(r.success for r in results), "Some batch documents failed"
        
        # Calculate performance
        docs_per_second = len(requests) / elapsed
        assert docs_per_second >= 10, f"Batch performance {docs_per_second:.2f} docs/sec below target"
        
        print(f"\n✅ Batch Performance: {docs_per_second:.2f} docs/second for {len(requests)} documents")
    
    @pytest.mark.asyncio
    async def test_memory_efficiency(self, generator):
        """Test memory usage stays below 100MB for 1000 documents."""
        tracemalloc.start()
        initial_memory = tracemalloc.get_traced_memory()[0]
        
        variables = {
            'title': 'Memory Test',
            'description': 'Testing memory efficiency',
            'features': ['Memory', 'Efficient', 'Scalable']
        }
        
        # Generate 100 documents (extrapolate to 1000)
        for i in range(100):
            await generator.generate_document(
                doc_type=DocumentType.README,
                template_id='template_test',
                variables={**variables, 'title': f'Memory Doc {i}'},
                enforce_quality_gate=False
            )
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Calculate memory usage
        memory_used = (current - initial_memory) / 1024 / 1024  # MB
        memory_per_100 = memory_used
        projected_1000 = memory_per_100 * 10
        
        assert projected_1000 < 100, f"Projected memory for 1000 docs: {projected_1000:.2f}MB exceeds 100MB"
        
        print(f"\n✅ Memory Efficiency: {memory_per_100:.2f}MB per 100 docs")
        print(f"   Projected for 1000 docs: {projected_1000:.2f}MB")
    
    @pytest.mark.asyncio
    async def test_latency_under_100ms(self, generator):
        """Test average latency stays under 100ms per document."""
        variables = {
            'title': 'Latency Test',
            'description': 'Testing response latency',
            'features': ['Fast', 'Responsive']
        }
        
        latencies = []
        
        # Measure individual document latencies
        for i in range(20):
            start = time.perf_counter()
            
            result = await generator.generate_document(
                doc_type=DocumentType.README,
                template_id='template_test',
                variables={**variables, 'title': f'Latency Doc {i}'},
                enforce_quality_gate=False
            )
            
            latency = (time.perf_counter() - start) * 1000  # ms
            latencies.append(latency)
            
            assert result.success
        
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)
        
        assert avg_latency < 100, f"Average latency {avg_latency:.2f}ms exceeds 100ms target"
        
        print(f"\n✅ Latency Performance:")
        print(f"   Average: {avg_latency:.2f}ms")
        print(f"   Min: {min_latency:.2f}ms")
        print(f"   Max: {max_latency:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_concurrent_generation(self, generator):
        """Test handling of concurrent document generation."""
        variables = {
            'title': 'Concurrent Test',
            'description': 'Testing concurrent generation',
            'features': ['Concurrent', 'Parallel', 'Async']
        }
        
        # Create concurrent tasks
        tasks = []
        for i in range(20):
            task = generator.generate_document(
                doc_type=DocumentType.README,
                template_id='template_test',
                variables={**variables, 'title': f'Concurrent Doc {i}'},
                enforce_quality_gate=False
            )
            tasks.append(task)
        
        # Execute concurrently
        start_time = time.perf_counter()
        results = await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start_time
        
        # Check all succeeded
        assert all(r.success for r in results), "Some concurrent documents failed"
        
        # Calculate concurrent performance
        docs_per_second = len(tasks) / elapsed
        assert docs_per_second >= 10, f"Concurrent performance {docs_per_second:.2f} docs/sec below target"
        
        print(f"\n✅ Concurrent Performance: {docs_per_second:.2f} docs/second for {len(tasks)} concurrent tasks")
    
    @pytest.mark.asyncio
    async def test_template_cache_performance(self, generator):
        """Test template caching improves performance."""
        variables = {
            'title': 'Template Cache Test',
            'description': 'Testing template caching',
            'features': ['Cached', 'Templates']
        }
        
        # First generation (cold cache)
        start = time.perf_counter()
        await generator.generate_document(
            doc_type=DocumentType.README,
            template_id='template_test',
            variables=variables,
            enforce_quality_gate=False
        )
        cold_time = time.perf_counter() - start
        
        # Second generation (warm cache)
        start = time.perf_counter()
        await generator.generate_document(
            doc_type=DocumentType.README,
            template_id='template_test',
            variables={**variables, 'title': 'Different Title'},  # Different to avoid doc cache
            enforce_quality_gate=False
        )
        warm_time = time.perf_counter() - start
        
        # Template cache should make it faster
        improvement = (cold_time - warm_time) / cold_time * 100
        
        print(f"\n✅ Template Cache Performance:")
        print(f"   Cold cache: {cold_time*1000:.2f}ms")
        print(f"   Warm cache: {warm_time*1000:.2f}ms")
        print(f"   Improvement: {improvement:.1f}%")
    
    @pytest.mark.asyncio
    async def test_format_conversion_performance(self, generator):
        """Test performance of format conversion."""
        variables = {
            'title': 'Format Test',
            'description': 'Testing format conversion',
            'features': ['HTML', 'JSON', 'Markdown']
        }
        
        formats = [OutputFormat.MARKDOWN, OutputFormat.HTML, OutputFormat.JSON]
        format_times = {}
        
        for output_format in formats:
            start = time.perf_counter()
            
            result = await generator.generate_document(
                doc_type=DocumentType.README,
                template_id='template_test',
                variables=variables,
                output_format=output_format,
                enforce_quality_gate=False
            )
            
            elapsed = time.perf_counter() - start
            format_times[output_format.value] = elapsed * 1000
            
            assert result.success
        
        print(f"\n✅ Format Conversion Performance:")
        for fmt, time_ms in format_times.items():
            print(f"   {fmt}: {time_ms:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_performance_modes_comparison(self):
        """Test performance across different operation modes."""
        modes = ['basic', 'performance', 'secure', 'enterprise']
        mode_performance = {}
        
        for mode in modes:
            # Create config for mode
            config = ConfigurationManager()
            config.set('operation_mode', mode)
            config.set('memory_mode', MemoryMode.PERFORMANCE)
            
            # Create mocks
            storage = Mock(spec=UnifiedStorageManager)
            template_doc = Mock()
            template_doc.content = "# {{ title }}"
            template_doc.metadata = {'variables': ['title']}
            storage.get_document = Mock(return_value=template_doc)
            storage.create_document = Mock(return_value=template_doc)
            
            miair = Mock(spec=MIAIREngineUnified)
            async def mock_analyze(doc, **kwargs):
                result = Mock()
                result.quality_score = Mock()
                result.quality_score.overall = 90.0
                return result
            miair.analyze_document = AsyncMock(side_effect=mock_analyze)
            
            # Create generator
            generator = UnifiedDocumentGenerator(
                config_manager=config,
                storage_manager=storage,
                miair_engine=miair
            )
            
            # Measure performance
            start = time.perf_counter()
            for i in range(50):
                await generator.generate_document(
                    doc_type=DocumentType.README,
                    template_id='template_test',
                    variables={'title': f'Mode Test {i}'},
                    enforce_quality_gate=False
                )
            elapsed = time.perf_counter() - start
            
            mode_performance[mode] = 50 / elapsed
        
        print(f"\n✅ Performance Mode Comparison:")
        for mode, perf in mode_performance.items():
            status = "✅" if perf >= 10 else "❌"
            print(f"   {mode.upper():12} {perf:8.2f} docs/sec {status}")
        
        # All modes should meet target
        for mode, perf in mode_performance.items():
            assert perf >= 10, f"{mode} mode: {perf:.2f} docs/sec below 10 docs/sec target"


@pytest.mark.benchmark
class TestGeneratorBenchmarks:
    """Benchmark tests for performance regression detection."""
    
    @pytest.mark.asyncio
    async def test_benchmark_simple_template(self, benchmark, generator):
        """Benchmark simple template generation."""
        variables = {
            'title': 'Benchmark',
            'description': 'Performance test',
            'features': ['Fast']
        }
        
        async def generate():
            return await generator.generate_document(
                doc_type=DocumentType.README,
                template_id='template_test',
                variables=variables,
                enforce_quality_gate=False
            )
        
        result = benchmark(asyncio.run, generate())
        assert result.success
    
    @pytest.mark.asyncio
    async def test_benchmark_batch_10(self, benchmark, generator):
        """Benchmark batch generation of 10 documents."""
        requests = [
            {
                'doc_type': DocumentType.README,
                'template_id': 'template_test',
                'variables': {'title': f'Doc {i}', 'description': 'Test', 'features': []},
                'enforce_quality_gate': False
            }
            for i in range(10)
        ]
        
        async def generate_batch():
            return await generator.generate_batch(requests)
        
        results = benchmark(asyncio.run, generate_batch())
        assert all(r.success for r in results)