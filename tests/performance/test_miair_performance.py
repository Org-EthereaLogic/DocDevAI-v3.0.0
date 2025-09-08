"""
Performance benchmarks for M003 MIAIR Engine
DevDocAI v3.0.0 - Pass 2: Performance Optimization

Target: 248K documents/minute (4,133 docs/sec)
"""

import time
import pytest
import numpy as np
import asyncio
import concurrent.futures
from typing import List, Dict, Any
import psutil
import gc
from unittest.mock import Mock, MagicMock

from devdocai.intelligence.miair import MIAIREngine, DocumentMetrics, OptimizationResult
from devdocai.core.config import ConfigurationManager
from devdocai.intelligence.llm_adapter import LLMAdapter, LLMResponse
from devdocai.core.storage import StorageManager


class TestMIAIRPerformance:
    """Performance benchmark tests for MIAIR Engine."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for performance testing."""
        config = Mock(spec=ConfigurationManager)
        config.get.side_effect = lambda key, default=None: {
            'quality.entropy_threshold': 0.35,
            'quality.target_entropy': 0.15,
            'quality.coherence_target': 0.94,
            'quality.quality_gate': 85,
            'quality.max_iterations': 7,
            'system.memory_mode': 'standard'
        }.get(key, default)
        return config
    
    @pytest.fixture
    def mock_llm_fast(self):
        """Mock LLM with minimal latency for performance testing."""
        llm = Mock(spec=LLMAdapter)
        llm.query = Mock(return_value=LLMResponse(
            content="Enhanced content with improved clarity.",
            provider="mock",
            tokens_used=50,
            cost=0.0005,
            latency=0.001  # 1ms simulated latency
        ))
        return llm
    
    @pytest.fixture
    def mock_storage(self):
        """Mock storage for performance testing."""
        storage = Mock(spec=StorageManager)
        storage.save_document.return_value = "doc_123"
        return storage
    
    @pytest.fixture
    def engine(self, mock_config, mock_llm_fast, mock_storage):
        """Create engine for performance testing."""
        return MIAIREngine(mock_config, mock_llm_fast, mock_storage)
    
    @pytest.fixture
    def sample_documents(self) -> List[str]:
        """Generate sample documents for testing."""
        docs = []
        for i in range(100):
            doc = f"""
            Document {i}: This is a comprehensive technical document that covers various aspects 
            of software engineering and system architecture. The content includes detailed analysis
            of performance optimization techniques, security considerations, and best practices
            for scalable system design. Each section provides in-depth coverage of specific topics
            with practical examples and implementation guidelines.
            
            The architecture follows established patterns including microservices, event-driven
            design, and cloud-native principles. Performance metrics indicate sub-millisecond
            response times for critical operations with horizontal scalability to handle
            millions of concurrent users.
            """
            docs.append(doc)
        return docs
    
    # ========================================================================
    # Baseline Performance Measurements
    # ========================================================================
    
    def test_baseline_entropy_calculation_speed(self, engine, sample_documents):
        """Measure baseline entropy calculation performance."""
        documents = sample_documents[:10]  # Test with 10 documents
        
        start_time = time.perf_counter()
        for doc in documents:
            entropy = engine.calculate_entropy(doc)
        end_time = time.perf_counter()
        
        duration = end_time - start_time
        avg_time_per_doc = duration / len(documents)
        docs_per_second = 1 / avg_time_per_doc if avg_time_per_doc > 0 else 0
        
        print(f"\n=== Baseline Entropy Calculation ===")
        print(f"Documents processed: {len(documents)}")
        print(f"Total time: {duration:.4f}s")
        print(f"Avg time per doc: {avg_time_per_doc*1000:.2f}ms")
        print(f"Throughput: {docs_per_second:.0f} docs/sec")
        print(f"Target: 4,133 docs/sec (248K/min)")
        
        # Store baseline for comparison
        pytest.benchmark_entropy_baseline = avg_time_per_doc
    
    def test_baseline_quality_measurement_speed(self, engine, sample_documents):
        """Measure baseline quality measurement performance."""
        documents = sample_documents[:10]
        
        start_time = time.perf_counter()
        for doc in documents:
            metrics = engine.measure_quality(doc)
        end_time = time.perf_counter()
        
        duration = end_time - start_time
        avg_time_per_doc = duration / len(documents)
        docs_per_second = 1 / avg_time_per_doc if avg_time_per_doc > 0 else 0
        
        print(f"\n=== Baseline Quality Measurement ===")
        print(f"Documents processed: {len(documents)}")
        print(f"Total time: {duration:.4f}s")
        print(f"Avg time per doc: {avg_time_per_doc*1000:.2f}ms")
        print(f"Throughput: {docs_per_second:.0f} docs/sec")
        
        pytest.benchmark_quality_baseline = avg_time_per_doc
    
    def test_baseline_single_document_optimization(self, engine, sample_documents):
        """Measure baseline single document optimization performance."""
        document = sample_documents[0]
        
        start_time = time.perf_counter()
        result = engine.optimize(document, max_iterations=1)
        end_time = time.perf_counter()
        
        duration = end_time - start_time
        
        print(f"\n=== Baseline Single Document Optimization ===")
        print(f"Optimization time: {duration:.4f}s")
        print(f"Iterations: {result.iterations}")
        print(f"Quality improvement: {result.improvement_percentage:.1f}%")
        print(f"Target: <30s per document")
        
        assert duration < 30, "Single document optimization exceeds 30s target"
    
    # ========================================================================
    # Throughput Tests
    # ========================================================================
    
    def test_sequential_throughput(self, engine, sample_documents):
        """Test sequential document processing throughput."""
        documents = sample_documents[:50]  # Process 50 documents
        
        start_time = time.perf_counter()
        results = []
        for doc in documents:
            result = engine.optimize(doc, max_iterations=1)
            results.append(result)
        end_time = time.perf_counter()
        
        duration = end_time - start_time
        docs_per_minute = (len(documents) / duration) * 60
        
        print(f"\n=== Sequential Throughput Test ===")
        print(f"Documents processed: {len(documents)}")
        print(f"Total time: {duration:.2f}s")
        print(f"Throughput: {docs_per_minute:.0f} docs/minute")
        print(f"Target: 248,000 docs/minute")
        print(f"Performance ratio: {(docs_per_minute / 248000) * 100:.2f}%")
        
        # Store for optimization comparison
        pytest.sequential_throughput = docs_per_minute
    
    def test_memory_usage_under_load(self, engine, sample_documents):
        """Test memory usage when processing many documents."""
        process = psutil.Process()
        
        # Measure initial memory
        gc.collect()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Process documents
        documents = sample_documents
        for doc in documents:
            engine.calculate_entropy(doc)
            engine.measure_quality(doc)
        
        # Measure peak memory
        gc.collect()
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - initial_memory
        
        print(f"\n=== Memory Usage Test ===")
        print(f"Documents processed: {len(documents)}")
        print(f"Initial memory: {initial_memory:.1f} MB")
        print(f"Peak memory: {peak_memory:.1f} MB")
        print(f"Memory increase: {memory_increase:.1f} MB")
        print(f"Memory per doc: {memory_increase / len(documents):.2f} MB")
        
        # Memory should not grow excessively
        assert memory_increase < 100, f"Memory usage too high: {memory_increase:.1f} MB"
    
    # ========================================================================
    # Optimization Target Tests
    # ========================================================================
    
    def test_entropy_calculation_target_performance(self, engine):
        """Test if entropy calculation meets performance targets."""
        # Generate a typical document
        document = " ".join([f"word{i%100}" for i in range(500)])
        
        # Warm up
        for _ in range(10):
            engine.calculate_entropy(document)
        
        # Measure performance
        iterations = 1000
        start_time = time.perf_counter()
        for _ in range(iterations):
            entropy = engine.calculate_entropy(document)
        end_time = time.perf_counter()
        
        duration = end_time - start_time
        avg_time = duration / iterations
        ops_per_second = iterations / duration
        
        print(f"\n=== Entropy Calculation Performance ===")
        print(f"Iterations: {iterations}")
        print(f"Total time: {duration:.4f}s")
        print(f"Avg time: {avg_time*1000:.3f}ms")
        print(f"Throughput: {ops_per_second:.0f} ops/sec")
        print(f"Target: <100ms per calculation")
        
        # Should be fast enough for target
        assert avg_time < 0.1, f"Entropy calculation too slow: {avg_time*1000:.1f}ms"
    
    def test_batch_processing_capability(self, engine, sample_documents):
        """Test potential for batch processing optimization."""
        documents = sample_documents[:10]
        
        # Simulate batch processing
        start_time = time.perf_counter()
        
        # Process all entropy calculations together
        entropies = [engine.calculate_entropy(doc) for doc in documents]
        
        # Process all quality measurements together  
        metrics = [engine.measure_quality(doc) for doc in documents]
        
        end_time = time.perf_counter()
        
        duration = end_time - start_time
        docs_per_second = len(documents) / duration
        docs_per_minute = docs_per_second * 60
        
        print(f"\n=== Batch Processing Simulation ===")
        print(f"Documents: {len(documents)}")
        print(f"Total time: {duration:.4f}s")
        print(f"Throughput: {docs_per_minute:.0f} docs/minute")
        print(f"Speedup potential: {(docs_per_minute / 248000) * 100:.2f}% of target")
    
    # ========================================================================
    # Stress Tests
    # ========================================================================
    
    def test_sustained_load_performance(self, engine, sample_documents):
        """Test performance under sustained load."""
        duration_seconds = 5  # Run for 5 seconds
        documents_processed = 0
        start_time = time.perf_counter()
        
        while time.perf_counter() - start_time < duration_seconds:
            doc = sample_documents[documents_processed % len(sample_documents)]
            engine.calculate_entropy(doc)
            engine.measure_quality(doc)
            documents_processed += 1
        
        actual_duration = time.perf_counter() - start_time
        docs_per_second = documents_processed / actual_duration
        docs_per_minute = docs_per_second * 60
        
        print(f"\n=== Sustained Load Test ===")
        print(f"Duration: {actual_duration:.1f}s")
        print(f"Documents processed: {documents_processed}")
        print(f"Throughput: {docs_per_second:.0f} docs/sec")
        print(f"Throughput: {docs_per_minute:.0f} docs/minute")
        print(f"Target achievement: {(docs_per_minute / 248000) * 100:.2f}%")
    
    def test_large_document_performance(self, engine):
        """Test performance with large documents."""
        # Generate a large document (10,000 words)
        large_doc = " ".join([f"word{i%1000}" for i in range(10000)])
        
        start_time = time.perf_counter()
        entropy = engine.calculate_entropy(large_doc)
        metrics = engine.measure_quality(large_doc)
        end_time = time.perf_counter()
        
        duration = end_time - start_time
        
        print(f"\n=== Large Document Performance ===")
        print(f"Document size: 10,000 words")
        print(f"Processing time: {duration*1000:.2f}ms")
        print(f"Entropy: {entropy:.2f}")
        print(f"Quality score: {metrics.quality_score:.1f}")
        
        # Even large documents should be processed quickly
        assert duration < 1.0, f"Large document processing too slow: {duration:.2f}s"
    
    # ========================================================================
    # Optimization Validation Tests
    # ========================================================================
    
    @pytest.mark.skipif(not hasattr(MIAIREngine, 'batch_optimize'), 
                        reason="Batch optimization not yet implemented")
    def test_batch_optimization_performance(self, engine, sample_documents):
        """Test batch optimization performance (if implemented)."""
        documents = sample_documents[:100]
        
        start_time = time.perf_counter()
        results = engine.batch_optimize(documents, max_iterations=1)
        end_time = time.perf_counter()
        
        duration = end_time - start_time
        docs_per_minute = (len(documents) / duration) * 60
        
        print(f"\n=== Batch Optimization Performance ===")
        print(f"Documents: {len(documents)}")
        print(f"Total time: {duration:.2f}s")
        print(f"Throughput: {docs_per_minute:.0f} docs/minute")
        print(f"Target: 248,000 docs/minute")
        print(f"Achievement: {(docs_per_minute / 248000) * 100:.1f}%")
        
        # Should show significant improvement over sequential
        if hasattr(pytest, 'sequential_throughput'):
            speedup = docs_per_minute / pytest.sequential_throughput
            print(f"Speedup vs sequential: {speedup:.1f}x")
    
    @pytest.mark.skipif(not hasattr(MIAIREngine, 'calculate_entropy_vectorized'),
                        reason="Vectorized entropy not yet implemented")
    def test_vectorized_entropy_performance(self, engine):
        """Test vectorized entropy calculation performance (if implemented)."""
        documents = [" ".join([f"word{i%100}" for i in range(500)]) for _ in range(100)]
        
        start_time = time.perf_counter()
        entropies = engine.calculate_entropy_vectorized(documents)
        end_time = time.perf_counter()
        
        duration = end_time - start_time
        docs_per_second = len(documents) / duration
        
        print(f"\n=== Vectorized Entropy Performance ===")
        print(f"Documents: {len(documents)}")
        print(f"Total time: {duration:.4f}s")
        print(f"Throughput: {docs_per_second:.0f} docs/sec")
        
        # Should be much faster than sequential
        if hasattr(pytest, 'benchmark_entropy_baseline'):
            speedup = (pytest.benchmark_entropy_baseline * len(documents)) / duration
            print(f"Speedup vs baseline: {speedup:.1f}x")
            assert speedup > 5, "Vectorization should provide >5x speedup"


class TestMIAIRCaching:
    """Test caching optimizations for MIAIR Engine."""
    
    @pytest.fixture
    def engine(self):
        """Create engine with caching enabled."""
        config = Mock(spec=ConfigurationManager)
        config.get.return_value = 0.35
        llm = Mock(spec=LLMAdapter)
        storage = Mock(spec=StorageManager)
        return MIAIREngine(config, llm, storage)
    
    @pytest.mark.skipif(not hasattr(MIAIREngine, '_entropy_cache'),
                        reason="Entropy caching not yet implemented")
    def test_entropy_caching_performance(self, engine):
        """Test entropy calculation caching effectiveness."""
        document = "This is a test document with some repeated content."
        
        # First calculation (cache miss)
        start = time.perf_counter()
        entropy1 = engine.calculate_entropy(document)
        first_time = time.perf_counter() - start
        
        # Second calculation (cache hit)
        start = time.perf_counter()
        entropy2 = engine.calculate_entropy(document)
        cached_time = time.perf_counter() - start
        
        print(f"\n=== Entropy Caching Performance ===")
        print(f"First calculation: {first_time*1000:.3f}ms")
        print(f"Cached calculation: {cached_time*1000:.3f}ms")
        print(f"Speedup: {first_time/cached_time:.1f}x")
        
        assert entropy1 == entropy2, "Cached result should be identical"
        assert cached_time < first_time / 10, "Cache should be >10x faster"


class TestMIAIRConcurrency:
    """Test concurrent processing capabilities."""
    
    @pytest.fixture
    def engine(self):
        """Create engine for concurrency testing."""
        config = Mock(spec=ConfigurationManager)
        config.get.return_value = 0.35
        llm = Mock(spec=LLMAdapter)
        llm.query.return_value = LLMResponse(
            content="Enhanced", provider="mock", 
            tokens_used=50, cost=0.001, latency=0.01
        )
        storage = Mock(spec=StorageManager)
        return MIAIREngine(config, llm, storage)
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not hasattr(MIAIREngine, 'optimize_async'),
                        reason="Async optimization not yet implemented")
    async def test_async_optimization_performance(self, engine):
        """Test async document optimization performance."""
        documents = [f"Document {i} content" for i in range(10)]
        
        start_time = time.perf_counter()
        
        # Process documents concurrently
        tasks = [engine.optimize_async(doc, max_iterations=1) for doc in documents]
        results = await asyncio.gather(*tasks)
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        print(f"\n=== Async Optimization Performance ===")
        print(f"Documents: {len(documents)}")
        print(f"Total time: {duration:.2f}s")
        print(f"Avg time per doc: {duration/len(documents):.2f}s")
        
        # Should be faster than sequential
        sequential_time = len(documents) * 0.5  # Assuming 0.5s per doc
        assert duration < sequential_time / 2, "Async should provide >2x speedup"