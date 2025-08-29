"""
Performance tests for M005 Quality Engine Pass 2.

Verifies that performance targets are met after optimization.
"""

import time
import pytest
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from devdocai.quality.analyzer import QualityAnalyzer, OptimizedQualityAnalyzer
from devdocai.quality.models import QualityConfig


class TestM005Performance:
    """Performance test suite for M005 Quality Engine."""
    
    @pytest.fixture
    def analyzer(self):
        """Create optimized analyzer instance."""
        config = QualityConfig(
            quality_gate_threshold=0.0,
            enable_caching=True,
            parallel_analysis=True
        )
        return QualityAnalyzer(config=config)
    
    @pytest.fixture
    def small_document(self):
        """Generate small test document."""
        return """
# Test Document

## Introduction
This is a small test document for performance testing.

## Content
The content includes various elements:
- Lists
- Paragraphs
- Code blocks

```python
def hello():
    print("Hello, World!")
```

## Conclusion
This concludes the test document.
""" * 5  # Repeat to get ~500 words
    
    @pytest.fixture
    def medium_document(self):
        """Generate medium test document."""
        return """
# Comprehensive Technical Documentation

## Executive Summary
This document provides a comprehensive overview of the system architecture,
implementation details, and performance characteristics of our advanced
data processing platform.

## System Architecture

### Core Components
The system consists of several interconnected modules:

1. **Data Ingestion Layer**: Handles real-time data streams
2. **Processing Engine**: Performs complex transformations
3. **Storage System**: Manages persistent data storage
4. **API Gateway**: Provides external access points

### Design Principles
- Scalability: Horizontal scaling capabilities
- Reliability: Built-in redundancy and failover
- Performance: Optimized for low-latency operations
- Security: End-to-end encryption

## Implementation Details

### Data Processing Pipeline
```python
class DataProcessor:
    def __init__(self):
        self.pipeline = []
    
    def process(self, data):
        for stage in self.pipeline:
            data = stage.transform(data)
        return data
```

### Performance Optimization
We have implemented several optimization strategies:
- Caching frequently accessed data
- Parallel processing for independent operations
- Lazy evaluation for expensive computations
- Memory pooling for object reuse

## Testing Strategy

### Unit Tests
Comprehensive unit test coverage ensures individual components work correctly.

### Integration Tests
End-to-end testing validates system behavior under various scenarios.

### Performance Tests
Continuous benchmarking tracks system performance over time.

## Deployment

### Environment Setup
The system can be deployed in various environments:
- Development: Local Docker containers
- Staging: Kubernetes cluster
- Production: Multi-region cloud deployment

### Configuration Management
Configuration is managed through environment variables and config files.

## Monitoring and Maintenance

### Metrics Collection
Key performance indicators are continuously monitored:
- Request latency
- Throughput
- Error rates
- Resource utilization

### Alerting
Automated alerts notify the team of any anomalies or issues.

## Conclusion
This documentation provides a foundation for understanding and working with
the system. Regular updates ensure it remains accurate and useful.
""" * 3  # Repeat to get ~3000 words
    
    @pytest.fixture
    def large_document(self, medium_document):
        """Generate large test document."""
        # Use medium document and expand it
        return medium_document * 3  # ~9000 words
    
    def test_small_document_performance(self, analyzer, small_document):
        """Test that small documents meet <3ms target."""
        # Warm up
        analyzer.analyze(small_document, document_id="warmup")
        
        # Measure performance
        times = []
        for i in range(5):
            start = time.perf_counter()
            analyzer.analyze(
                content=small_document,
                document_id=f"small_{i}"
            )
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        
        avg_time = sum(times) / len(times)
        assert avg_time < 3.0, f"Small document took {avg_time:.2f}ms (target: <3ms)"
    
    def test_medium_document_performance(self, analyzer, medium_document):
        """Test that medium documents meet <10ms target."""
        # Warm up
        analyzer.analyze(medium_document, document_id="warmup")
        
        # Measure performance
        times = []
        for i in range(5):
            start = time.perf_counter()
            analyzer.analyze(
                content=medium_document,
                document_id=f"medium_{i}"
            )
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        
        avg_time = sum(times) / len(times)
        assert avg_time < 10.0, f"Medium document took {avg_time:.2f}ms (target: <10ms)"
    
    def test_large_document_performance(self, analyzer, large_document):
        """Test that large documents meet <50ms target."""
        # Measure performance
        times = []
        for i in range(3):
            start = time.perf_counter()
            analyzer.analyze(
                content=large_document,
                document_id=f"large_{i}"
            )
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        
        avg_time = sum(times) / len(times)
        assert avg_time < 50.0, f"Large document took {avg_time:.2f}ms (target: <50ms)"
    
    def test_batch_processing_performance(self, analyzer, medium_document):
        """Test that batch processing meets 100+ docs/sec target."""
        batch_size = 50
        
        start = time.perf_counter()
        for i in range(batch_size):
            analyzer.analyze(
                content=medium_document,
                document_id=f"batch_{i}"
            )
        elapsed = time.perf_counter() - start
        
        throughput = batch_size / elapsed
        assert throughput >= 100, f"Batch throughput {throughput:.2f} docs/sec (target: 100+)"
    
    def test_caching_effectiveness(self, analyzer):
        """Test that caching provides significant speedup."""
        content = "# Test\n\nSimple test document for caching."
        doc_id = "cache_test"
        
        # First analysis (cache miss)
        start = time.perf_counter()
        analyzer.analyze(content, document_id=doc_id)
        first_time = (time.perf_counter() - start) * 1000
        
        # Second analysis (cache hit)
        start = time.perf_counter()
        analyzer.analyze(content, document_id=doc_id)
        cached_time = (time.perf_counter() - start) * 1000
        
        # Cache should be at least 10x faster
        speedup = first_time / cached_time if cached_time > 0 else float('inf')
        assert speedup > 10, f"Cache speedup only {speedup:.1f}x (expected >10x)"
    
    def test_parallel_analysis(self):
        """Test that parallel analysis improves performance."""
        content = "# Test\n" + "Content " * 1000  # Medium-sized content
        
        # Sequential analyzer
        seq_config = QualityConfig(
            quality_gate_threshold=0.0,
            enable_caching=False,
            parallel_analysis=False
        )
        seq_analyzer = OptimizedQualityAnalyzer(config=seq_config)
        
        # Parallel analyzer
        par_config = QualityConfig(
            quality_gate_threshold=0.0,
            enable_caching=False,
            parallel_analysis=True,
            max_workers=4
        )
        par_analyzer = OptimizedQualityAnalyzer(config=par_config)
        
        # Measure sequential
        start = time.perf_counter()
        for i in range(10):
            seq_analyzer.analyze(content, document_id=f"seq_{i}")
        seq_time = time.perf_counter() - start
        
        # Measure parallel
        start = time.perf_counter()
        for i in range(10):
            par_analyzer.analyze(content, document_id=f"par_{i}")
        par_time = time.perf_counter() - start
        
        # Parallel should be faster (allow some overhead)
        assert par_time <= seq_time * 1.1, f"Parallel not faster: {par_time:.2f}s vs {seq_time:.2f}s"
    
    def test_streaming_large_documents(self, analyzer):
        """Test that streaming works for very large documents."""
        # Create a very large document (>50K chars)
        very_large = "# Document\n\n" + ("This is content. " * 100 + "\n\n") * 500
        
        assert len(very_large) > 50000, "Document not large enough for streaming"
        
        # Should complete without memory issues
        start = time.perf_counter()
        report = analyzer.analyze(
            content=very_large,
            document_id="streaming_test"
        )
        elapsed = (time.perf_counter() - start) * 1000
        
        # Should complete in reasonable time (<100ms)
        assert elapsed < 100, f"Streaming took {elapsed:.2f}ms (target: <100ms)"
        assert report.overall_score >= 0, "Analysis should produce valid score"
    
    def test_memory_efficiency(self, analyzer):
        """Test that memory usage is optimized."""
        import tracemalloc
        
        # Generate test document
        content = "# Test\n\n" + "Content paragraph. " * 500
        
        # Measure memory usage
        tracemalloc.start()
        initial = tracemalloc.get_traced_memory()[0]
        
        # Analyze multiple documents
        for i in range(10):
            analyzer.analyze(content, document_id=f"mem_{i}")
        
        peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        
        # Memory usage should be reasonable (<10MB for 10 docs)
        memory_mb = (peak - initial) / (1024 * 1024)
        assert memory_mb < 10, f"Memory usage {memory_mb:.2f}MB exceeds 10MB limit"


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "--tb=short"])