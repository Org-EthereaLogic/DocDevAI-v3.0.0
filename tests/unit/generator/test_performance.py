"""
Tests for M004 Document Generator - Performance Baseline.

Performance tests and benchmarks for document generation functionality.
"""

import pytest
import time
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from devdocai.generator.core.engine import DocumentGenerator, GenerationConfig
from devdocai.generator.core.template_loader import TemplateLoader
from devdocai.generator.core.content_processor import ContentProcessor


class TestPerformanceBaseline:
    """Performance baseline tests for M004 Document Generator."""
    
    @pytest.fixture
    def large_template_dir(self):
        """Create template directory with templates of various sizes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            template_dir = Path(temp_dir)
            
            # Small template (< 1KB)
            small_template = template_dir / "small.j2"
            small_template.write_text("""---
title: "Small Template"
type: "test"
category: "performance"
variables: ["title", "content"]
---
# {{ title }}
{{ content }}""")
            
            # Medium template (~ 5KB)
            medium_content = "\n".join([f"## Section {i}\n{{ section_{i}_content | default('Default content for section ' + {i}|string) }}" for i in range(20)])
            medium_template = template_dir / "medium.j2"
            medium_template.write_text(f"""---
title: "Medium Template"
type: "test"
category: "performance"
variables: ["title"]
---
# {{ title }}
{medium_content}""")
            
            # Large template (~ 20KB)
            large_sections = []
            for i in range(50):
                section = f"""### Section {i}
{{{{ section_{i}_title | default('Section {i} Title') }}}}

{{{{ section_{i}_content | default('Default content for section {i}. This is a longer piece of content that might be used in a comprehensive document. It includes multiple sentences and provides more realistic content for performance testing.') }}}}

{{% if section_{i}_items %}}
Items for section {i}:
{{% for item in section_{i}_items %}}
- {{ item }}
{{% endfor %}}
{{% endif %}}
"""
                large_sections.append(section)
            
            large_content = "\n\n".join(large_sections)
            large_template = template_dir / "large.j2"
            large_template.write_text(f"""---
title: "Large Template"
type: "test"
category: "performance"
variables: ["title"]
---
# {{ title }}

This is a large template for performance testing.

{large_content}""")
            
            yield template_dir
    
    @pytest.fixture
    def performance_inputs(self):
        """Create inputs for performance testing."""
        inputs = {
            "title": "Performance Test Document",
            "content": "This is content for performance testing.",
        }
        
        # Add content for medium/large templates
        for i in range(50):
            inputs[f"section_{i}_title"] = f"Performance Section {i}"
            inputs[f"section_{i}_content"] = f"Content for performance section {i} with additional text for realistic testing."
            inputs[f"section_{i}_items"] = [f"Item {j}" for j in range(5)]
        
        return inputs
    
    def test_template_loading_performance(self, large_template_dir):
        """Test template loading performance (Pass 2 target: <100ms)."""
        loader = TemplateLoader(large_template_dir)
        
        # Test small template loading
        start_time = time.time()
        template = loader.load_template("small")
        small_load_time = time.time() - start_time
        
        assert template is not None
        assert small_load_time < 0.1  # Should be < 100ms
        
        # Test medium template loading
        start_time = time.time()
        template = loader.load_template("medium")
        medium_load_time = time.time() - start_time
        
        assert template is not None
        assert medium_load_time < 0.1  # Should be < 100ms
        
        # Test large template loading
        start_time = time.time()
        template = loader.load_template("large")
        large_load_time = time.time() - start_time
        
        assert template is not None
        assert large_load_time < 0.1  # Should be < 100ms
        
        print(f"\nTemplate Loading Performance:")
        print(f"Small template: {small_load_time:.3f}s")
        print(f"Medium template: {medium_load_time:.3f}s")
        print(f"Large template: {large_load_time:.3f}s")
    
    def test_content_processing_performance(self, large_template_dir, performance_inputs):
        """Test content processing performance."""
        processor = ContentProcessor()
        loader = TemplateLoader(large_template_dir)
        
        # Test processing small template
        small_template = loader.load_template("small")
        start_time = time.time()
        result = processor.process_content(small_template.content, performance_inputs)
        small_process_time = time.time() - start_time
        
        assert len(result) > 0
        assert small_process_time < 0.1  # Should be fast
        
        # Test processing medium template
        medium_template = loader.load_template("medium")
        start_time = time.time()
        result = processor.process_content(medium_template.content, performance_inputs)
        medium_process_time = time.time() - start_time
        
        assert len(result) > 0
        assert medium_process_time < 0.5  # Should be reasonable
        
        # Test processing large template
        large_template = loader.load_template("large")
        start_time = time.time()
        result = processor.process_content(large_template.content, performance_inputs)
        large_process_time = time.time() - start_time
        
        assert len(result) > 0
        assert large_process_time < 2.0  # Pass 2 target: <2s for <50KB
        
        print(f"\nContent Processing Performance:")
        print(f"Small template: {small_process_time:.3f}s")
        print(f"Medium template: {medium_process_time:.3f}s")
        print(f"Large template: {large_process_time:.3f}s")
    
    def test_document_generation_performance(self, large_template_dir, performance_inputs):
        """Test end-to-end document generation performance (Pass 2 target: <2s for <50KB)."""
        generator = DocumentGenerator(template_dir=large_template_dir)
        config = GenerationConfig(save_to_storage=False)  # Skip storage for pure generation perf
        
        # Test small template generation
        start_time = time.time()
        result = generator.generate_document("small", performance_inputs, config)
        small_gen_time = time.time() - start_time
        
        assert result.success is True
        assert small_gen_time < 0.2  # Should be very fast
        
        # Test medium template generation  
        start_time = time.time()
        result = generator.generate_document("medium", performance_inputs, config)
        medium_gen_time = time.time() - start_time
        
        assert result.success is True
        assert medium_gen_time < 1.0  # Should be reasonable
        
        # Test large template generation
        start_time = time.time()
        result = generator.generate_document("large", performance_inputs, config)
        large_gen_time = time.time() - start_time
        
        assert result.success is True
        assert large_gen_time < 2.0  # Pass 2 target: <2s for <50KB templates
        assert len(result.content) > 1000  # Should generate substantial content
        
        print(f"\nDocument Generation Performance:")
        print(f"Small template: {small_gen_time:.3f}s ({len(result.content)} chars)")
        print(f"Medium template: {medium_gen_time:.3f}s")
        print(f"Large template: {large_gen_time:.3f}s ({len(result.content)} chars)")
    
    def test_concurrent_generation_performance(self, large_template_dir, performance_inputs):
        """Test concurrent document generation (Pass 2 target: 100 concurrent generations)."""
        generator = DocumentGenerator(template_dir=large_template_dir)
        config = GenerationConfig(save_to_storage=False)
        
        def generate_document():
            """Helper function for concurrent generation."""
            result = generator.generate_document("small", performance_inputs, config)
            return result.success, result.generation_time
        
        # Test concurrent generations
        num_concurrent = 10  # Start with smaller number for Pass 1
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [executor.submit(generate_document) for _ in range(num_concurrent)]
            results = [future.result() for future in futures]
        
        total_time = time.time() - start_time
        
        # All generations should succeed
        successes = [r[0] for r in results]
        generation_times = [r[1] for r in results]
        
        assert all(successes)
        assert total_time < 5.0  # Should complete reasonably quickly
        
        avg_generation_time = sum(generation_times) / len(generation_times)
        max_generation_time = max(generation_times)
        
        print(f"\nConcurrent Generation Performance ({num_concurrent} concurrent):")
        print(f"Total time: {total_time:.3f}s")
        print(f"Average generation time: {avg_generation_time:.3f}s")
        print(f"Max generation time: {max_generation_time:.3f}s")
        print(f"Throughput: {num_concurrent / total_time:.1f} docs/sec")
    
    def test_template_caching_performance(self, large_template_dir, performance_inputs):
        """Test template caching improves performance."""
        loader = TemplateLoader(large_template_dir)
        
        # First load (cold cache)
        start_time = time.time()
        template1 = loader.load_template("large")
        cold_load_time = time.time() - start_time
        
        # Second load (warm cache)
        start_time = time.time()
        template2 = loader.load_template("large")
        warm_load_time = time.time() - start_time
        
        assert template1 is not None
        assert template2 is not None
        assert template1 is template2  # Should be same cached object
        
        # Warm cache should be significantly faster
        assert warm_load_time < cold_load_time
        assert warm_load_time < 0.01  # Should be very fast from cache
        
        print(f"\nTemplate Caching Performance:")
        print(f"Cold load: {cold_load_time:.3f}s")
        print(f"Warm load: {warm_load_time:.3f}s")
        print(f"Cache speedup: {cold_load_time / warm_load_time:.1f}x")
    
    def test_memory_usage_baseline(self, large_template_dir, performance_inputs):
        """Test memory usage baseline for future optimization."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Measure baseline memory
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create generator and generate documents
        generator = DocumentGenerator(template_dir=large_template_dir)
        config = GenerationConfig(save_to_storage=False)
        
        # Generate multiple documents
        for i in range(10):
            result = generator.generate_document("large", performance_inputs, config)
            assert result.success is True
        
        # Measure memory after generation
        after_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = after_memory - baseline_memory
        
        print(f"\nMemory Usage Baseline:")
        print(f"Baseline memory: {baseline_memory:.1f} MB")
        print(f"After generation: {after_memory:.1f} MB")
        print(f"Memory increase: {memory_increase:.1f} MB")
        
        # Memory increase should be reasonable (< 50MB for 10 large documents)
        assert memory_increase < 50.0
    
    def test_validation_performance(self, large_template_dir, performance_inputs):
        """Test input validation performance impact."""
        generator = DocumentGenerator(template_dir=large_template_dir)
        
        # Generate with validation enabled
        config_with_validation = GenerationConfig(save_to_storage=False, validate_inputs=True)
        start_time = time.time()
        result1 = generator.generate_document("medium", performance_inputs, config_with_validation)
        time_with_validation = time.time() - start_time
        
        # Generate with validation disabled
        config_without_validation = GenerationConfig(save_to_storage=False, validate_inputs=False)
        start_time = time.time()
        result2 = generator.generate_document("medium", performance_inputs, config_without_validation)
        time_without_validation = time.time() - start_time
        
        assert result1.success is True
        assert result2.success is True
        
        validation_overhead = time_with_validation - time_without_validation
        
        print(f"\nValidation Performance Impact:")
        print(f"With validation: {time_with_validation:.3f}s")
        print(f"Without validation: {time_without_validation:.3f}s")
        print(f"Validation overhead: {validation_overhead:.3f}s ({validation_overhead/time_without_validation*100:.1f}%)")
        
        # Validation overhead should be minimal (< 20% of generation time)
        assert validation_overhead / time_without_validation < 0.2
    
    def test_output_format_performance(self, large_template_dir, performance_inputs):
        """Test performance difference between output formats."""
        generator = DocumentGenerator(template_dir=large_template_dir)
        
        # Test markdown generation
        markdown_config = GenerationConfig(output_format="markdown", save_to_storage=False)
        start_time = time.time()
        markdown_result = generator.generate_document("medium", performance_inputs, markdown_config)
        markdown_time = time.time() - start_time
        
        # Test HTML generation
        html_config = GenerationConfig(output_format="html", save_to_storage=False)
        start_time = time.time()
        html_result = generator.generate_document("medium", performance_inputs, html_config)
        html_time = time.time() - start_time
        
        assert markdown_result.success is True
        assert html_result.success is True
        
        print(f"\nOutput Format Performance:")
        print(f"Markdown generation: {markdown_time:.3f}s")
        print(f"HTML generation: {html_time:.3f}s")
        print(f"HTML overhead: {html_time - markdown_time:.3f}s")
        
        # Both formats should be reasonably fast
        assert markdown_time < 1.0
        assert html_time < 2.0  # HTML might be slower due to conversion