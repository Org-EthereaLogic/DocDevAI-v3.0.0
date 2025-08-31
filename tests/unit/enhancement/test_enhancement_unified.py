"""
Test suite for M009 Enhancement Pipeline unified implementation.

Tests the consolidated pipeline with all operation modes and validates
that functionality from all three passes is preserved.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from devdocai.enhancement import (
    UnifiedEnhancementPipeline,
    UnifiedEnhancementSettings,
    UnifiedOperationMode,
    UnifiedCache,
    UnifiedCacheMode,
    create_unified_pipeline,
    create_basic_pipeline,
    create_performance_pipeline,
    create_secure_pipeline,
    create_enterprise_pipeline,
    DocumentContent,
    EnhancementResult,
    EnhancementConfig
)

from devdocai.enhancement.config import EnhancementType


class TestUnifiedEnhancementPipeline:
    """Test the unified enhancement pipeline."""
    
    @pytest.fixture
    def sample_document(self):
        """Sample document for testing."""
        return DocumentContent(
            content="This is a test document that needs enhancement. It has some basic content.",
            doc_type="markdown",
            language="en"
        )
    
    @pytest.fixture
    def basic_config(self):
        """Basic enhancement configuration."""
        return EnhancementConfig(
            strategies=[EnhancementType.CLARITY, EnhancementType.READABILITY],
            max_passes=2,
            quality_threshold=0.7,
            cost_limit=0.20
        )
    
    def test_basic_mode_initialization(self):
        """Test BASIC mode pipeline initialization."""
        pipeline = create_basic_pipeline()
        
        assert pipeline.mode == UnifiedOperationMode.BASIC
        assert pipeline.settings.operation_mode == UnifiedOperationMode.BASIC
        assert not pipeline.settings.pipeline.use_cache
        assert not pipeline.settings.pipeline.enable_performance_optimization
        assert not pipeline.settings.pipeline.enable_security_validation
        
        # Check that basic components are initialized
        assert pipeline.strategy_factory is not None
        assert pipeline.quality_tracker is not None
        assert pipeline.history is not None
        assert pipeline.cost_optimizer is not None
        
        # Check that advanced components are not initialized
        assert not hasattr(pipeline, 'cache') or pipeline.cache is None
        assert not hasattr(pipeline, 'validator') or pipeline.validator is None
    
    def test_performance_mode_initialization(self):
        """Test PERFORMANCE mode pipeline initialization."""
        pipeline = create_performance_pipeline()
        
        assert pipeline.mode == UnifiedOperationMode.PERFORMANCE
        assert pipeline.settings.pipeline.use_cache
        assert pipeline.settings.pipeline.enable_performance_optimization
        assert pipeline.settings.pipeline.parallel_processing
        
        # Performance features should be available (if dependencies installed)
        features = pipeline._get_enabled_features()
        assert len(features) > 0
    
    def test_secure_mode_initialization(self):
        """Test SECURE mode pipeline initialization."""
        pipeline = create_secure_pipeline()
        
        assert pipeline.mode == UnifiedOperationMode.SECURE
        assert pipeline.settings.pipeline.enable_security_validation
        assert pipeline.settings.pipeline.enable_audit_logging
        assert pipeline.settings.pipeline.use_secure_cache
    
    def test_enterprise_mode_initialization(self):
        """Test ENTERPRISE mode pipeline initialization."""
        pipeline = create_enterprise_pipeline()
        
        assert pipeline.mode == UnifiedOperationMode.ENTERPRISE
        assert pipeline.settings.pipeline.enable_performance_optimization
        assert pipeline.settings.pipeline.enable_security_validation
        assert pipeline.settings.pipeline.enable_monitoring
        
        # Should have the most features enabled
        features = pipeline._get_enabled_features()
        basic_features = create_basic_pipeline()._get_enabled_features()
        assert len(features) >= len(basic_features)
    
    @pytest.mark.asyncio
    async def test_basic_document_enhancement(self, sample_document, basic_config):
        """Test basic document enhancement."""
        pipeline = create_basic_pipeline()
        
        with patch.object(pipeline, '_measure_quality', return_value=0.8), \
             patch.object(pipeline, '_apply_strategy') as mock_apply:
            
            mock_apply.return_value = {
                "success": True,
                "enhanced_content": "Enhanced: " + sample_document.content,
                "improvement": {"strategy": "clarity", "description": "Test improvement"},
                "quality": 0.9,
                "cost": 0.05
            }
            
            result = await pipeline.enhance_document(sample_document, basic_config)
            
            assert isinstance(result, EnhancementResult)
            assert result.success
            assert result.enhanced_content.startswith("Enhanced:")
            assert result.quality_after > result.quality_before
            assert len(result.strategies_applied) > 0
    
    @pytest.mark.asyncio
    async def test_performance_mode_caching(self, sample_document):
        """Test performance mode caching functionality."""
        pipeline = create_performance_pipeline(max_size=100, use_cache=True)
        
        with patch.object(pipeline, '_measure_quality', return_value=0.8), \
             patch.object(pipeline, '_apply_strategy') as mock_apply:
            
            mock_apply.return_value = {
                "success": True,
                "enhanced_content": "Enhanced content",
                "improvement": {"strategy": "clarity", "description": "Test"},
                "quality": 0.9,
                "cost": 0.05
            }
            
            # First call should miss cache
            result1 = await pipeline.enhance_document(sample_document)
            assert result1.success
            
            # Second call with same document should potentially hit cache
            result2 = await pipeline.enhance_document(sample_document)
            assert result2.success
            
            # Check metrics
            metrics = pipeline.get_metrics_summary()
            assert metrics["operations"]["total"] == 2
            assert metrics["operations"]["successful"] >= 1
    
    @pytest.mark.asyncio
    async def test_fast_path_optimization(self):
        """Test fast path optimization for small documents."""
        pipeline = create_performance_pipeline(fast_path_threshold=100)
        
        # Small document should use fast path
        small_doc = DocumentContent(content="Short content", doc_type="text")
        
        with patch.object(pipeline, '_fast_path_enhancement') as mock_fast_path, \
             patch.object(pipeline, '_enhance_basic') as mock_basic:
            
            mock_fast_path.return_value = EnhancementResult(
                original_content=small_doc.content,
                enhanced_content="Enhanced short",
                improvements=[],
                quality_before=0.5,
                quality_after=0.8,
                improvement_percentage=60.0,
                strategies_applied=["clarity"],
                total_cost=0.01,
                processing_time=0.1,
                enhancement_passes=1,
                success=True
            )
            
            result = await pipeline.enhance_document(small_doc)
            
            mock_fast_path.assert_called_once()
            mock_basic.assert_not_called()
            assert result.success
            assert pipeline.metrics.fast_path_operations == 1
    
    @pytest.mark.asyncio
    async def test_batch_enhancement(self, sample_document):
        """Test batch document enhancement."""
        pipeline = create_performance_pipeline()
        
        documents = [
            DocumentContent(content=f"Document {i} content") 
            for i in range(3)
        ]
        
        with patch.object(pipeline, 'enhance_document') as mock_enhance:
            mock_enhance.return_value = EnhancementResult(
                original_content="test",
                enhanced_content="enhanced test",
                improvements=[],
                quality_before=0.5,
                quality_after=0.8,
                improvement_percentage=60.0,
                strategies_applied=["clarity"],
                total_cost=0.05,
                processing_time=0.2,
                enhancement_passes=1,
                success=True
            )
            
            results = await pipeline.enhance_batch(documents)
            
            assert len(results) == 3
            assert all(result.success for result in results)
            assert pipeline.metrics.batch_operations == 1
    
    @pytest.mark.asyncio
    async def test_streaming_enhancement(self):
        """Test streaming document enhancement."""
        pipeline = create_performance_pipeline()
        
        async def document_stream():
            for i in range(3):
                yield DocumentContent(content=f"Stream doc {i}")
        
        with patch.object(pipeline, 'enhance_document') as mock_enhance:
            mock_enhance.return_value = EnhancementResult(
                original_content="test",
                enhanced_content="enhanced",
                improvements=[],
                quality_before=0.5,
                quality_after=0.8,
                improvement_percentage=60.0,
                strategies_applied=["clarity"],
                total_cost=0.05,
                processing_time=0.1,
                enhancement_passes=1,
                success=True
            )
            
            results = []
            async for result in pipeline.enhance_stream(document_stream()):
                results.append(result)
            
            assert len(results) == 3
            assert all(result.success for result in results)
    
    def test_metrics_tracking(self):
        """Test comprehensive metrics tracking."""
        pipeline = create_enterprise_pipeline()
        
        # Simulate some operations
        pipeline.metrics.total_operations = 100
        pipeline.metrics.successful_operations = 95
        pipeline.metrics.failed_operations = 5
        pipeline.metrics.cache_hits = 30
        pipeline.metrics.cache_misses = 70
        pipeline.metrics.parallel_operations = 20
        pipeline.metrics.fast_path_operations = 15
        
        metrics = pipeline.get_metrics_summary()
        
        assert metrics["operations"]["total"] == 100
        assert metrics["operations"]["successful"] == 95
        assert metrics["operations"]["success_rate"] == 0.95
        assert metrics["performance"]["cache_hit_ratio"] == 0.3
        assert metrics["performance"]["parallel_operations"] == 20
        assert metrics["performance"]["fast_path_usage"] == 0.15
    
    def test_performance_report(self):
        """Test performance report generation."""
        pipeline = create_enterprise_pipeline()
        
        report = pipeline.get_performance_report()
        
        assert "mode" in report
        assert report["mode"] == "enterprise"
        assert "metrics" in report
        assert "settings" in report
        assert "components" in report
        
        # Check component status
        components = report["components"]
        assert "cache" in components
        assert "parallel_executor" in components
        assert "security_validator" in components
    
    @pytest.mark.asyncio
    async def test_error_handling(self, sample_document):
        """Test error handling in enhancement process."""
        pipeline = create_basic_pipeline()
        
        # Mock a failure in strategy application
        with patch.object(pipeline, '_apply_strategy', side_effect=Exception("Test error")):
            
            result = await pipeline.enhance_document(sample_document)
            
            # Should return failure result, not raise exception
            assert not result.success
            assert "Test error" in result.errors
            assert pipeline.metrics.failed_operations == 1
    
    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test pipeline cleanup."""
        pipeline = create_enterprise_pipeline()
        
        # Add some data to clean up
        pipeline._basic_cache["test"] = "data"
        pipeline.metrics.total_operations = 10
        
        await pipeline.cleanup()
        
        # Cache should be cleared
        assert len(pipeline._basic_cache) == 0
        
        # Should generate a final report
        assert pipeline.metrics.total_operations == 10  # Metrics preserved for final report


class TestUnifiedCache:
    """Test the unified cache system."""
    
    def test_basic_cache_mode(self):
        """Test basic cache mode."""
        cache = UnifiedCache(mode=UnifiedCacheMode.BASIC)
        
        assert cache.mode == UnifiedCacheMode.BASIC
        assert not cache.config.enable_encryption
        assert not cache.config.enable_semantic_similarity
        assert not cache.config.enable_compression
    
    def test_performance_cache_mode(self):
        """Test performance cache mode."""
        cache = UnifiedCache(mode=UnifiedCacheMode.PERFORMANCE)
        
        assert cache.mode == UnifiedCacheMode.PERFORMANCE
        assert cache.config.max_size >= 1000  # Should have larger size
        # Compression/semantic features depend on available libraries
    
    def test_secure_cache_mode(self):
        """Test secure cache mode."""
        cache = UnifiedCache(mode=UnifiedCacheMode.SECURE)
        
        assert cache.mode == UnifiedCacheMode.SECURE
        assert cache.config.enable_isolation
        # Encryption depends on availability of encryption manager
    
    def test_cache_basic_operations(self):
        """Test basic cache operations."""
        cache = UnifiedCache(mode=UnifiedCacheMode.BASIC)
        
        # Test put and get
        success = cache.put("test_key", "test_value")
        assert success
        
        value, status = cache.get("test_key")
        assert value == "test_value"
        assert status.value == "hit"
        
        # Test miss
        value, status = cache.get("nonexistent_key")
        assert value is None
        assert status.value == "miss"
    
    def test_cache_ttl_expiration(self):
        """Test TTL-based cache expiration."""
        cache = UnifiedCache(mode=UnifiedCacheMode.BASIC)
        
        # Put with very short TTL
        cache.put("expire_key", "expire_value", ttl=1)
        
        # Should be available immediately
        value, status = cache.get("expire_key")
        assert value == "expire_value"
        assert status.value == "hit"
        
        # Wait for expiration and test
        time.sleep(1.1)
        value, status = cache.get("expire_key")
        assert value is None
        assert status.value in ["expired", "miss"]
    
    def test_cache_size_limits(self):
        """Test cache size limits and eviction."""
        cache = UnifiedCache(
            mode=UnifiedCacheMode.BASIC,
            config=UnifiedCache._create_config_for_mode(
                UnifiedCacheMode.BASIC,
                max_size=2
            )
        )
        
        # Fill cache to capacity
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        
        # Both should be present
        assert cache.get("key1")[1].value == "hit"
        assert cache.get("key2")[1].value == "hit"
        
        # Adding third should evict first (LRU)
        cache.put("key3", "value3")
        
        assert cache.get("key1")[1].value == "miss"  # Evicted
        assert cache.get("key2")[1].value == "hit"   # Still present
        assert cache.get("key3")[1].value == "hit"   # Newly added
    
    def test_cache_stats(self):
        """Test cache statistics tracking."""
        cache = UnifiedCache(mode=UnifiedCacheMode.PERFORMANCE)
        
        # Perform some operations
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        
        cache.get("key1")  # Hit
        cache.get("key1")  # Hit
        cache.get("missing")  # Miss
        
        stats = cache.get_stats()
        
        assert stats["performance"]["hits"] == 2
        assert stats["performance"]["misses"] == 1
        assert stats["performance"]["hit_ratio"] > 0
        assert stats["performance"]["entry_count"] == 2
    
    def test_cache_health_status(self):
        """Test cache health status monitoring."""
        cache = UnifiedCache(mode=UnifiedCacheMode.SECURE)
        
        health = cache.get_health_status()
        
        assert "status" in health
        assert "score" in health
        assert "issues" in health
        assert health["status"] in ["healthy", "warning", "degraded", "critical"]
        assert 0 <= health["score"] <= 100


class TestUnifiedConfiguration:
    """Test unified configuration system."""
    
    def test_mode_based_configuration(self):
        """Test configuration generation for different modes."""
        basic_settings = UnifiedEnhancementSettings.create(UnifiedOperationMode.BASIC)
        perf_settings = UnifiedEnhancementSettings.create(UnifiedOperationMode.PERFORMANCE)
        secure_settings = UnifiedEnhancementSettings.create(UnifiedOperationMode.SECURE)
        enterprise_settings = UnifiedEnhancementSettings.create(UnifiedOperationMode.ENTERPRISE)
        
        # Basic should have minimal features
        assert not basic_settings.pipeline.use_cache
        assert not basic_settings.pipeline.enable_performance_optimization
        assert basic_settings.pipeline.max_workers == 1
        
        # Performance should have optimization features
        assert perf_settings.pipeline.use_cache
        assert perf_settings.pipeline.enable_performance_optimization
        assert perf_settings.pipeline.max_workers > 1
        
        # Secure should have security features
        assert secure_settings.pipeline.enable_security_validation
        assert secure_settings.pipeline.enable_audit_logging
        assert secure_settings.pipeline.use_secure_cache
        
        # Enterprise should have everything
        assert enterprise_settings.pipeline.enable_performance_optimization
        assert enterprise_settings.pipeline.enable_security_validation
        assert enterprise_settings.pipeline.enable_monitoring
    
    def test_configuration_overrides(self):
        """Test configuration overrides."""
        settings = UnifiedEnhancementSettings.create(
            UnifiedOperationMode.BASIC,
            max_workers=4,  # Override default
            use_cache=True  # Override default
        )
        
        assert settings.pipeline.max_workers == 4
        assert settings.pipeline.use_cache == True
    
    def test_feature_summary(self):
        """Test feature summary generation."""
        settings = UnifiedEnhancementSettings.create(UnifiedOperationMode.ENTERPRISE)
        
        summary = settings.get_feature_summary()
        
        assert summary["mode"] == "enterprise"
        assert "features" in summary
        assert "performance" in summary
        assert "strategies" in summary
        
        features = summary["features"]
        assert isinstance(features["caching"], bool)
        assert isinstance(features["parallel_processing"], bool)


@pytest.mark.integration
class TestUnifiedIntegration:
    """Integration tests for the unified system."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_enhancement(self):
        """Test end-to-end document enhancement."""
        pipeline = create_performance_pipeline()
        
        document = DocumentContent(
            content="This document needs significant improvement in clarity and structure.",
            doc_type="markdown"
        )
        
        with patch('devdocai.enhancement.enhancement_unified.INTEGRATIONS_AVAILABLE', False):
            # Run without external integrations for predictable testing
            result = await pipeline.enhance_document(document)
            
            assert isinstance(result, EnhancementResult)
            # Result success depends on mock setup, but should not crash
            assert hasattr(result, 'success')
            assert hasattr(result, 'processing_time')
    
    def test_backward_compatibility(self):
        """Test backward compatibility with original interfaces."""
        # Should be able to import and use original classes
        from devdocai.enhancement import EnhancementPipeline, EnhancementSettings
        
        # Original classes should still work
        settings = EnhancementSettings()
        pipeline = EnhancementPipeline(settings)
        
        assert pipeline is not None
        assert hasattr(pipeline, 'enhance_document')
    
    def test_factory_functions(self):
        """Test all factory functions."""
        pipelines = [
            create_basic_pipeline(),
            create_performance_pipeline(),
            create_secure_pipeline(),
            create_enterprise_pipeline()
        ]
        
        for pipeline in pipelines:
            assert isinstance(pipeline, UnifiedEnhancementPipeline)
            assert pipeline.mode in UnifiedOperationMode
            assert pipeline.settings is not None


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])