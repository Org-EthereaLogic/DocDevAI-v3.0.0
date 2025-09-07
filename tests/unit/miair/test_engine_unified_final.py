"""
Unit tests for final unified MIAIR Engine (Pass 4 Refactoring).
"""

import asyncio
import pytest
import time
from datetime import datetime, timezone

from devdocai.miair.engine_unified_final import (
    MIAIREngineUnified,
    create_basic_engine,
    create_performance_engine,
    create_secure_engine,
    create_enterprise_engine
)
from devdocai.miair.models import (
    Document,
    DocumentType,
    OperationMode
)


class TestMIAIREngineUnified:
    """Test unified MIAIR Engine."""
    
    @pytest.fixture
    def sample_document(self):
        """Create sample document for testing."""
        return Document(
            id="test-doc-1",
            content="This is a test document with some content for analysis. " * 10,
            type=DocumentType.TECHNICAL_SPEC,
            metadata={
                'created_at': datetime.now(timezone.utc),
                'author': 'Test Author'
            }
        )
    
    @pytest.mark.asyncio
    async def test_basic_mode_initialization(self):
        """Test engine initialization in BASIC mode."""
        engine = MIAIREngineUnified(mode=OperationMode.BASIC)
        
        assert engine.mode == OperationMode.BASIC
        assert engine.cache is None  # No caching in BASIC mode
        assert engine.config.enable_caching is False
        
        await engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_performance_mode_initialization(self):
        """Test engine initialization in PERFORMANCE mode."""
        engine = MIAIREngineUnified(mode=OperationMode.PERFORMANCE)
        
        assert engine.mode == OperationMode.PERFORMANCE
        assert engine.cache is not None  # Caching enabled
        assert engine.config.enable_caching is True
        assert engine.config.enable_parallel is True
        
        await engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_analyze_document(self, sample_document):
        """Test document analysis."""
        engine = create_basic_engine()
        
        result = await engine.analyze_document(sample_document)
        
        assert 0 <= result.entropy <= 1.0
        assert result.quality_score is not None
        assert 0 <= result.quality_score.overall <= 100.0
        assert isinstance(result.meets_quality_gate, bool)
        assert result.improvement_potential >= 0
        
        await engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_analyze_document_with_caching(self, sample_document):
        """Test document analysis with caching."""
        engine = create_performance_engine()
        
        # First call - cache miss
        result1 = await engine.analyze_document(sample_document)
        
        # Second call - should be cache hit
        result2 = await engine.analyze_document(sample_document)
        
        # Results should be identical (same object from cache)
        assert result1.entropy == result2.entropy
        assert result1.quality_score.overall == result2.quality_score.overall
        
        # Check cache size
        metrics = engine.get_metrics()
        assert metrics['cache_size'] > 0
        
        await engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_optimize_document(self, sample_document):
        """Test document optimization."""
        engine = create_basic_engine()
        
        result = await engine.optimize_document(
            sample_document,
            target_quality=85.0,
            max_iterations=3
        )
        
        assert result.document is not None
        assert result.initial_entropy >= 0
        assert result.final_entropy >= 0
        assert result.iterations >= 0
        assert result.quality_score is not None
        assert result.execution_time_ms > 0
        
        await engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_batch_processing_sequential(self):
        """Test batch processing in BASIC mode (sequential)."""
        engine = create_basic_engine()
        
        documents = [
            Document(
                id=f"doc-{i}",
                content=f"Test content {i} for batch processing. " * 5,
                type=DocumentType.GENERAL
            )
            for i in range(3)
        ]
        
        results = await engine.batch_process(documents, operation='analyze')
        
        assert len(results) == 3
        for result in results:
            assert result.entropy >= 0
            assert result.quality_score is not None
        
        await engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_batch_processing_parallel(self):
        """Test batch processing in PERFORMANCE mode (parallel)."""
        engine = create_performance_engine()
        
        documents = [
            Document(
                id=f"doc-{i}",
                content=f"Test content {i} for parallel processing. " * 5,
                type=DocumentType.API_DOCUMENTATION
            )
            for i in range(5)
        ]
        
        start = time.perf_counter()
        results = await engine.batch_process(documents, operation='analyze')
        duration = time.perf_counter() - start
        
        assert len(results) == 5
        
        # Parallel should be faster than sequential (rough check)
        # Each document analysis should take some time, parallel should reduce total
        print(f"Parallel batch processing took {duration:.3f}s for 5 documents")
        
        await engine.shutdown()
    
    def test_metrics_tracking(self):
        """Test metrics tracking functionality."""
        engine = create_basic_engine()
        
        # Initial metrics
        metrics = engine.get_metrics()
        assert metrics['total_documents'] == 0
        assert metrics['total_time'] == 0
        
        # Simulate processing
        engine.total_documents_processed = 10
        engine.total_processing_time = 5.0
        
        metrics = engine.get_metrics()
        assert metrics['total_documents'] == 10
        assert metrics['total_time'] == 5.0
        assert metrics['avg_time_per_doc'] == 0.5
        assert metrics['throughput_per_minute'] == 120  # (10/5)*60
        
        # Reset metrics
        engine.reset_metrics()
        metrics = engine.get_metrics()
        assert metrics['total_documents'] == 0
        assert metrics['total_time'] == 0
    
    def test_cache_key_generation(self):
        """Test cache key generation."""
        engine = create_performance_engine()
        
        doc1 = Document(
            id="doc1",
            content="Content 1",
            type=DocumentType.README
        )
        
        doc2 = Document(
            id="doc2",
            content="Content 1",  # Same content
            type=DocumentType.README
        )
        
        doc3 = Document(
            id="doc3",
            content="Content 2",  # Different content
            type=DocumentType.README
        )
        
        key1 = engine._generate_cache_key(doc1)
        key2 = engine._generate_cache_key(doc2)
        key3 = engine._generate_cache_key(doc3)
        
        # Same content should generate same key
        assert key1 == key2
        
        # Different content should generate different key
        assert key1 != key3


class TestFactoryFunctions:
    """Test factory functions for creating engines."""
    
    @pytest.mark.asyncio
    async def test_create_basic_engine(self):
        """Test basic engine factory."""
        engine = create_basic_engine()
        assert engine.mode == OperationMode.BASIC
        assert engine.config.enable_caching is False
        await engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_create_performance_engine(self):
        """Test performance engine factory."""
        engine = create_performance_engine()
        assert engine.mode == OperationMode.PERFORMANCE
        assert engine.config.enable_caching is True
        assert engine.config.enable_parallel is True
        await engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_create_secure_engine(self):
        """Test secure engine factory."""
        engine = create_secure_engine()
        assert engine.mode == OperationMode.SECURE
        assert engine.config.enable_validation is True
        assert engine.config.enable_audit is True
        await engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_create_enterprise_engine(self):
        """Test enterprise engine factory."""
        engine = create_enterprise_engine()
        assert engine.mode == OperationMode.ENTERPRISE
        assert engine.config.enable_caching is True
        assert engine.config.enable_parallel is True
        assert engine.config.enable_validation is True
        await engine.shutdown()


class TestPerformanceBenchmarks:
    """Performance benchmarks to validate optimization targets."""
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_throughput_basic_vs_performance(self):
        """Compare throughput between BASIC and PERFORMANCE modes."""
        documents = [
            Document(
                id=f"perf-doc-{i}",
                content=f"Performance test content {i} " * 50,
                type=DocumentType.TECHNICAL_SPEC
            )
            for i in range(20)
        ]
        
        # Test BASIC mode
        basic_engine = create_basic_engine()
        start = time.perf_counter()
        basic_results = await basic_engine.batch_process(documents, operation='analyze')
        basic_time = time.perf_counter() - start
        basic_throughput = len(basic_results) / basic_time
        await basic_engine.shutdown()
        
        # Test PERFORMANCE mode
        perf_engine = create_performance_engine()
        start = time.perf_counter()
        perf_results = await perf_engine.batch_process(documents, operation='analyze')
        perf_time = time.perf_counter() - start
        perf_throughput = len(perf_results) / perf_time
        await perf_engine.shutdown()
        
        print(f"\nBASIC mode: {basic_throughput:.1f} docs/sec")
        print(f"PERFORMANCE mode: {perf_throughput:.1f} docs/sec")
        print(f"Speedup: {perf_throughput/basic_throughput:.1f}x")
        
        # Performance mode should be faster
        assert perf_throughput > basic_throughput


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])