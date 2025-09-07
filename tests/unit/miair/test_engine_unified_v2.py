"""
Unit tests for unified MIAIR Engine v2 (Pass 4 Refactoring).

Tests all operation modes and validates consolidation of functionality.
"""

import asyncio
import pytest
import time
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch, AsyncMock

from devdocai.miair.engine_unified_v2 import (
    MIAIREngineUnified,
    UnifiedCacheManager,
    UnifiedCacheConfig,
    CacheStrategy,
    create_basic_engine,
    create_performance_engine,
    create_secure_engine,
    create_enterprise_engine
)
from devdocai.miair.models import (
    Document,
    DocumentType,
    OperationMode,
    QualityScore
)
from devdocai.miair.config_unified import UnifiedMIAIRConfig


class TestUnifiedCacheManager:
    """Test unified cache manager functionality."""
    
    def test_cache_strategy_none(self):
        """Test cache with NONE strategy."""
        config = UnifiedCacheConfig(strategy=CacheStrategy.NONE)
        cache = UnifiedCacheManager(config)
        
        # Should not store or retrieve
        cache.set("key", "value")
        assert cache.get("key") is None
    
    def test_cache_strategy_simple(self):
        """Test cache with SIMPLE strategy."""
        config = UnifiedCacheConfig(
            strategy=CacheStrategy.SIMPLE,
            max_size=10
        )
        cache = UnifiedCacheManager(config)
        
        # Should store and retrieve
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Test cache hit rate
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss
        assert cache.hit_rate == 0.5
    
    def test_cache_eviction(self):
        """Test LRU eviction when cache is full."""
        config = UnifiedCacheConfig(
            strategy=CacheStrategy.SIMPLE,
            max_size=3
        )
        cache = UnifiedCacheManager(config)
        
        # Fill cache
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # Add one more (should evict key1)
        cache.set("key4", "value4")
        
        assert cache.get("key1") is None  # Evicted
        assert cache.get("key4") == "value4"  # Present
    
    def test_cache_clear(self):
        """Test cache clearing."""
        config = UnifiedCacheConfig(
            strategy=CacheStrategy.SIMPLE,
            max_size=10
        )
        cache = UnifiedCacheManager(config)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        cache.clear()
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.hit_rate == 0.0


class TestMIAIREngineUnified:
    """Test unified MIAIR Engine."""
    
    @pytest.fixture
    def sample_document(self):
        """Create sample document for testing."""
        return Document(
            id="test-doc-1",
            content="This is a test document with some content for analysis.",
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
        assert engine.cache_manager.strategy == CacheStrategy.NONE
        assert engine.thread_executor is None
        assert engine.process_executor is None
        
        await engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_performance_mode_initialization(self):
        """Test engine initialization in PERFORMANCE mode."""
        engine = MIAIREngineUnified(mode=OperationMode.PERFORMANCE)
        
        assert engine.mode == OperationMode.PERFORMANCE
        assert engine.cache_manager.strategy == CacheStrategy.SIMPLE
        assert engine.thread_executor is not None
        assert engine.process_executor is not None
        
        await engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_secure_mode_initialization(self):
        """Test engine initialization in SECURE mode."""
        with patch('devdocai.miair.engine_unified_v2.SECURITY_AVAILABLE', True):
            engine = MIAIREngineUnified(mode=OperationMode.SECURE)
            
            assert engine.mode == OperationMode.SECURE
            assert engine.cache_manager.strategy == CacheStrategy.ENCRYPTED
            
            await engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_enterprise_mode_initialization(self):
        """Test engine initialization in ENTERPRISE mode."""
        with patch('devdocai.miair.engine_unified_v2.SECURITY_AVAILABLE', True):
            engine = MIAIREngineUnified(mode=OperationMode.ENTERPRISE)
            
            assert engine.mode == OperationMode.ENTERPRISE
            assert engine.cache_manager.strategy == CacheStrategy.HYBRID
            assert engine.thread_executor is not None
            assert engine.process_executor is not None
            
            await engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_analyze_document_basic(self, sample_document):
        """Test document analysis in BASIC mode."""
        engine = create_basic_engine()
        
        result = await engine.analyze_document(sample_document)
        
        assert result.document_id == sample_document.id
        assert 0 <= result.entropy <= 1.0
        assert result.quality_score is not None
        assert isinstance(result.suggestions, list)
        assert result.processing_time > 0
        
        await engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_analyze_document_with_caching(self, sample_document):
        """Test document analysis with caching in PERFORMANCE mode."""
        engine = create_performance_engine()
        
        # First call - cache miss
        result1 = await engine.analyze_document(sample_document)
        
        # Second call - should be cache hit
        result2 = await engine.analyze_document(sample_document)
        
        # Results should be the same
        assert result1.document_id == result2.document_id
        assert result1.entropy == result2.entropy
        assert result1.quality_score.overall == result2.quality_score.overall
        
        # Check cache hit rate
        assert engine.cache_manager.hit_rate > 0
        
        await engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_optimize_document(self, sample_document):
        """Test document optimization."""
        engine = create_basic_engine()
        
        result = await engine.optimize_document(
            sample_document,
            target_quality=0.85,
            max_iterations=3
        )
        
        assert result.document_id == sample_document.id
        assert result.original_quality >= 0
        assert result.optimized_quality >= result.original_quality
        assert result.iterations >= 0
        assert result.optimized_content is not None
        assert result.processing_time > 0
        
        await engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_batch_processing_performance_mode(self):
        """Test batch processing in PERFORMANCE mode."""
        engine = create_performance_engine()
        
        # Create multiple documents
        documents = [
            Document(
                id=f"doc-{i}",
                content=f"Test content {i} for batch processing.",
                type=DocumentType.TECHNICAL_SPEC
            )
            for i in range(5)
        ]
        
        results = await engine.batch_process(documents, operation='analyze')
        
        assert len(results) == 5
        for result in results:
            assert result.entropy >= 0
            assert result.quality_score is not None
        
        await engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_batch_processing_basic_mode(self):
        """Test batch processing in BASIC mode (sequential)."""
        engine = create_basic_engine()
        
        # Create multiple documents
        documents = [
            Document(
                id=f"doc-{i}",
                content=f"Test content {i} for sequential processing.",
                type=DocumentType.TECHNICAL_SPEC
            )
            for i in range(3)
        ]
        
        results = await engine.batch_process(documents, operation='analyze')
        
        assert len(results) == 3
        
        await engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_security_validation(self, sample_document):
        """Test security validation in SECURE mode."""
        with patch('devdocai.miair.engine_unified_v2.SECURITY_AVAILABLE', True):
            # Mock security components
            mock_validator = AsyncMock()
            mock_validator.validate_document.return_value = Mock(
                is_valid=True,
                errors=[]
            )
            
            mock_rate_limiter = AsyncMock()
            mock_rate_limiter.check_limit.return_value = True
            
            engine = create_secure_engine()
            engine.input_validator = mock_validator
            engine.rate_limiter = mock_rate_limiter
            
            result = await engine.analyze_document(sample_document)
            
            # Verify security checks were called
            mock_validator.validate_document.assert_called_once()
            mock_rate_limiter.check_limit.assert_called_once_with(sample_document.id)
            
            assert result is not None
            
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
    
    @pytest.mark.asyncio
    async def test_calculate_entropy_optimized(self):
        """Test optimized entropy calculation."""
        engine = create_performance_engine()
        
        document = Document(
            id="test",
            content="Hello world! This is a test.",
            type=DocumentType.TECHNICAL_SPEC
        )
        
        entropy = await engine._calculate_entropy_optimized(document)
        
        assert 0 <= entropy <= 1.0
        
        await engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_semantic_analysis_optimized(self):
        """Test optimized semantic analysis."""
        engine = create_performance_engine()
        
        document = Document(
            id="test",
            content="""
            Here is some text with a URL: https://example.com
            And a code block:
            ```python
            def hello():
                print("Hello")
            ```
            """,
            type=DocumentType.TECHNICAL_SPEC
        )
        
        elements = await engine._analyze_semantic_optimized(document)
        
        assert len(elements) > 0
        
        # Check for URL extraction
        urls = [e for e in elements if e.content.startswith('http')]
        assert len(urls) > 0
        
        # Check for code block extraction
        code_blocks = [e for e in elements if '```' in e.content]
        assert len(code_blocks) > 0
        
        await engine.shutdown()
    
    def test_content_splitting(self):
        """Test content splitting for parallel processing."""
        engine = create_performance_engine()
        
        content = "\n\n".join([f"Paragraph {i}" for i in range(10)])
        
        chunks = engine._split_content(content, chunk_size=50)
        
        assert len(chunks) > 1
        
        # Verify all content is preserved
        reconstructed = "\n\n".join(chunks)
        assert all(f"Paragraph {i}" in reconstructed for i in range(10))
    
    def test_cache_key_generation(self):
        """Test cache key generation."""
        engine = create_basic_engine()
        
        doc1 = Document(
            id="doc1",
            content="Content 1",
            type=DocumentType.TECHNICAL_SPEC
        )
        
        doc2 = Document(
            id="doc2",
            content="Content 1",  # Same content
            type=DocumentType.TECHNICAL_SPEC
        )
        
        doc3 = Document(
            id="doc3",
            content="Content 2",  # Different content
            type=DocumentType.TECHNICAL_SPEC
        )
        
        key1 = engine._generate_cache_key(doc1, 'analyze')
        key2 = engine._generate_cache_key(doc2, 'analyze')
        key3 = engine._generate_cache_key(doc3, 'analyze')
        
        # Same content should generate same key
        assert key1 == key2
        
        # Different content should generate different key
        assert key1 != key3
    
    def test_time_factor_calculation(self):
        """Test fractal-time scaling factor calculation."""
        engine = create_basic_engine()
        
        # New document
        doc_new = Document(
            id="new",
            content="Content",
            type=DocumentType.TECHNICAL_SPEC,
            metadata={'created_at': datetime.now(timezone.utc)}
        )
        
        factor_new = engine._calculate_time_factor(doc_new)
        assert 0.9 <= factor_new <= 1.0
        
        # Old document
        from datetime import timedelta
        old_date = datetime.now(timezone.utc) - timedelta(days=365)
        doc_old = Document(
            id="old",
            content="Content",
            type=DocumentType.TECHNICAL_SPEC,
            metadata={'created_at': old_date}
        )
        
        factor_old = engine._calculate_time_factor(doc_old)
        assert factor_old < factor_new
        assert 0.1 <= factor_old <= 1.0
    
    def test_suggestion_generation(self):
        """Test improvement suggestion generation."""
        engine = create_basic_engine()
        
        document = Document(
            id="test",
            content="Test content",
            type=DocumentType.TECHNICAL_SPEC
        )
        
        quality_score = QualityScore(
            overall=60.0,
            completeness=60.0,
            clarity=50.0,
            consistency=70.0,
            structure=70.0,
            technical_accuracy=80.0
        )
        
        suggestions = engine._generate_suggestions(
            document,
            entropy=0.4,  # Above threshold
            quality_score=quality_score,
            semantic_elements=[]
        )
        
        assert len(suggestions) > 0
        
        # Should have entropy suggestion
        assert any('entropy' in s.lower() for s in suggestions)
        
        # Should have readability suggestion
        assert any('readability' in s.lower() for s in suggestions)


class TestFactoryFunctions:
    """Test factory functions for creating engines."""
    
    @pytest.mark.asyncio
    async def test_create_basic_engine(self):
        """Test basic engine factory."""
        engine = create_basic_engine()
        assert engine.mode == OperationMode.BASIC
        await engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_create_performance_engine(self):
        """Test performance engine factory."""
        engine = create_performance_engine()
        assert engine.mode == OperationMode.PERFORMANCE
        await engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_create_secure_engine(self):
        """Test secure engine factory."""
        engine = create_secure_engine()
        assert engine.mode == OperationMode.SECURE
        await engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_create_enterprise_engine(self):
        """Test enterprise engine factory."""
        engine = create_enterprise_engine()
        assert engine.mode == OperationMode.ENTERPRISE
        await engine.shutdown()


class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""
    
    def test_miair_engine_alias(self):
        """Test MIAIREngine alias works."""
        from devdocai.miair.engine_unified_v2 import MIAIREngine
        
        engine = MIAIREngine(mode=OperationMode.BASIC)
        assert isinstance(engine, MIAIREngineUnified)
    
    def test_performance_engine_alias(self):
        """Test PerformanceOptimizedEngine alias works."""
        from devdocai.miair.engine_unified_v2 import PerformanceOptimizedEngine
        
        engine = PerformanceOptimizedEngine()
        assert engine.mode == OperationMode.PERFORMANCE
    
    def test_secure_engine_alias(self):
        """Test SecureMIAIREngine alias works."""
        from devdocai.miair.engine_unified_v2 import SecureMIAIREngine
        
        engine = SecureMIAIREngine()
        assert engine.mode == OperationMode.SECURE


class TestPerformanceBenchmarks:
    """Performance benchmarks to validate optimization targets."""
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_throughput_performance_mode(self):
        """Benchmark throughput in PERFORMANCE mode."""
        engine = create_performance_engine()
        
        # Create test documents
        documents = [
            Document(
                id=f"perf-doc-{i}",
                content=f"Performance test content {i} " * 100,
                type=DocumentType.TECHNICAL_SPEC
            )
            for i in range(100)
        ]
        
        start_time = time.perf_counter()
        
        # Process documents
        results = await engine.batch_process(documents, operation='analyze')
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        # Calculate throughput
        docs_per_second = len(results) / duration
        docs_per_minute = docs_per_second * 60
        
        print(f"\nPerformance Mode Throughput: {docs_per_minute:.0f} docs/min")
        
        # Should achieve significant throughput
        assert docs_per_minute > 1000  # Conservative target for tests
        
        await engine.shutdown()
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_cache_effectiveness(self):
        """Benchmark cache effectiveness."""
        engine = create_performance_engine()
        
        document = Document(
            id="cache-test",
            content="Cache test content " * 500,
            type=DocumentType.TECHNICAL_SPEC
        )
        
        # First analysis (cache miss)
        start1 = time.perf_counter()
        result1 = await engine.analyze_document(document)
        time1 = time.perf_counter() - start1
        
        # Second analysis (cache hit)
        start2 = time.perf_counter()
        result2 = await engine.analyze_document(document)
        time2 = time.perf_counter() - start2
        
        # Cache hit should be much faster
        speedup = time1 / time2
        print(f"\nCache Speedup: {speedup:.1f}x")
        
        assert speedup > 10  # At least 10x faster from cache
        assert engine.cache_manager.hit_rate > 0
        
        await engine.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])