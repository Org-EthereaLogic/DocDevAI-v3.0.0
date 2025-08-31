"""
Tests for the main enhancement pipeline.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from devdocai.enhancement.enhancement_pipeline import (
    EnhancementPipeline,
    DocumentContent,
    EnhancementResult,
    EnhancementConfig
)
from devdocai.enhancement.config import (
    EnhancementSettings,
    OperationMode,
    EnhancementType
)


class TestDocumentContent:
    """Test DocumentContent dataclass."""
    
    def test_default_initialization(self):
        """Test default document content initialization."""
        doc = DocumentContent(content="Test content")
        
        assert doc.content == "Test content"
        assert doc.doc_type == "markdown"
        assert doc.language == "en"
        assert doc.version == 0
        assert isinstance(doc.created_at, datetime)
        assert isinstance(doc.metadata, dict)
        
    def test_custom_initialization(self):
        """Test custom document content initialization."""
        metadata = {"author": "test", "category": "technical"}
        doc = DocumentContent(
            content="Custom content",
            metadata=metadata,
            doc_type="text",
            language="fr",
            version=2
        )
        
        assert doc.content == "Custom content"
        assert doc.doc_type == "text"
        assert doc.language == "fr"
        assert doc.version == 2
        assert doc.metadata == metadata
        
    def test_to_dict(self):
        """Test converting document to dictionary."""
        doc = DocumentContent(content="Test")
        data = doc.to_dict()
        
        assert data["content"] == "Test"
        assert data["doc_type"] == "markdown"
        assert data["language"] == "en"
        assert data["version"] == 0
        assert "created_at" in data


class TestEnhancementResult:
    """Test EnhancementResult dataclass."""
    
    def test_initialization(self):
        """Test enhancement result initialization."""
        result = EnhancementResult(
            original_content="Original",
            enhanced_content="Enhanced",
            improvements=[{"strategy": "clarity", "description": "Simplified"}],
            quality_before=0.6,
            quality_after=0.8,
            improvement_percentage=33.3,
            strategies_applied=["clarity"],
            total_cost=0.05,
            processing_time=2.5,
            enhancement_passes=3,
            success=True
        )
        
        assert result.original_content == "Original"
        assert result.enhanced_content == "Enhanced"
        assert len(result.improvements) == 1
        assert result.quality_before == 0.6
        assert result.quality_after == 0.8
        assert result.improvement_percentage == 33.3
        assert result.strategies_applied == ["clarity"]
        assert result.total_cost == 0.05
        assert result.processing_time == 2.5
        assert result.enhancement_passes == 3
        assert result.success is True
        assert result.errors == []
        
    def test_to_dict(self):
        """Test converting result to dictionary."""
        result = EnhancementResult(
            original_content="A" * 600,
            enhanced_content="B" * 600,
            improvements=[],
            quality_before=0.5,
            quality_after=0.7,
            improvement_percentage=40.0,
            strategies_applied=["clarity"],
            total_cost=0.10,
            processing_time=5.0,
            enhancement_passes=2,
            success=True
        )
        
        data = result.to_dict()
        
        # Check content truncation
        assert len(data["original_content"]) < 600
        assert "..." in data["original_content"]
        assert len(data["enhanced_content"]) < 600
        assert "..." in data["enhanced_content"]
        
        assert data["quality_before"] == 0.5
        assert data["quality_after"] == 0.7
        assert data["success"] is True


class TestEnhancementConfig:
    """Test EnhancementConfig dataclass."""
    
    def test_default_initialization(self):
        """Test default enhancement configuration."""
        config = EnhancementConfig()
        
        assert len(config.strategies) == 3
        assert EnhancementType.CLARITY in config.strategies
        assert EnhancementType.COMPLETENESS in config.strategies
        assert EnhancementType.READABILITY in config.strategies
        assert config.max_passes == 5
        assert config.quality_threshold == 0.8
        assert config.improvement_threshold == 0.05
        assert config.cost_limit == 0.50
        assert config.timeout == 300
        assert config.parallel is True
        assert config.preserve_style is True
        assert config.selective_enhancement is None
        
    def test_from_settings(self):
        """Test creating config from settings."""
        settings = EnhancementSettings.from_mode(OperationMode.BASIC)
        config = EnhancementConfig.from_settings(settings)
        
        assert config.max_passes == 2
        assert config.parallel is False
        assert config.cost_limit == 0.10
        
        # Check enabled strategies only
        assert EnhancementType.CLARITY in config.strategies
        assert EnhancementType.READABILITY in config.strategies
        assert EnhancementType.COMPLETENESS not in config.strategies


class TestEnhancementPipeline:
    """Test the main enhancement pipeline."""
    
    @pytest.fixture
    def pipeline(self):
        """Create pipeline instance for testing."""
        settings = EnhancementSettings()
        return EnhancementPipeline(settings)
        
    @pytest.fixture
    def mock_llm_adapter(self):
        """Create mock LLM adapter."""
        adapter = Mock()
        adapter.generate = AsyncMock(return_value={"content": "Enhanced text"})
        return adapter
        
    @pytest.fixture
    def mock_quality_analyzer(self):
        """Create mock quality analyzer."""
        analyzer = Mock()
        analyzer.analyze = AsyncMock(return_value={"overall_score": 0.75})
        return analyzer
        
    def test_initialization(self, pipeline):
        """Test pipeline initialization."""
        assert isinstance(pipeline.settings, EnhancementSettings)
        assert pipeline.strategy_factory is not None
        assert pipeline.quality_tracker is not None
        assert pipeline.history is not None
        assert pipeline.cost_optimizer is not None
        
    def test_initialization_with_integrations(self):
        """Test pipeline initialization with module integrations."""
        mock_llm = Mock()
        mock_quality = Mock()
        mock_miair = Mock()
        
        pipeline = EnhancementPipeline(
            llm_adapter=mock_llm,
            quality_analyzer=mock_quality,
            miair_engine=mock_miair
        )
        
        assert pipeline.llm_adapter == mock_llm
        assert pipeline.quality_analyzer == mock_quality
        assert pipeline.miair_engine == mock_miair
        
    @pytest.mark.asyncio
    async def test_enhance_document_string(self, pipeline):
        """Test enhancing a document from string."""
        content = "This is test content."
        
        # Mock quality measurement
        pipeline._measure_quality = AsyncMock(return_value=0.7)
        
        # Mock strategy application
        pipeline._apply_strategy = AsyncMock(return_value={
            "success": True,
            "enhanced_content": "This is improved test content.",
            "improvement": {"strategy": "clarity", "description": "Improved"},
            "quality": 0.8,
            "cost": 0.01
        })
        
        result = await pipeline.enhance_document(content)
        
        assert isinstance(result, EnhancementResult)
        assert result.original_content == content
        assert result.success is True
        assert result.quality_before == 0.7
        
    @pytest.mark.asyncio
    async def test_enhance_document_object(self, pipeline):
        """Test enhancing a DocumentContent object."""
        doc = DocumentContent(content="Test content", metadata={"type": "test"})
        
        # Mock quality measurement
        pipeline._measure_quality = AsyncMock(return_value=0.6)
        
        # Mock strategy application
        pipeline._apply_strategy = AsyncMock(return_value={
            "success": True,
            "enhanced_content": "Improved test content",
            "improvement": {"strategy": "clarity", "description": "Improved"},
            "quality": 0.75,
            "cost": 0.02
        })
        
        config = EnhancementConfig(max_passes=1)
        result = await pipeline.enhance_document(doc, config)
        
        assert isinstance(result, EnhancementResult)
        assert result.original_content == doc.content
        assert result.success is True
        assert result.metadata["document_type"] == "markdown"
        
    @pytest.mark.asyncio
    async def test_enhance_batch(self, pipeline):
        """Test batch enhancement."""
        documents = [
            "Document 1",
            "Document 2",
            DocumentContent(content="Document 3")
        ]
        
        # Mock quality measurement
        pipeline._measure_quality = AsyncMock(return_value=0.7)
        
        # Mock strategy application
        pipeline._apply_strategy = AsyncMock(return_value={
            "success": True,
            "enhanced_content": "Enhanced",
            "improvement": {"strategy": "clarity", "description": "Improved"},
            "quality": 0.8,
            "cost": 0.01
        })
        
        config = EnhancementConfig(max_passes=1, parallel=True)
        results = await pipeline.enhance_batch(documents, config)
        
        assert len(results) == 3
        for result in results:
            assert isinstance(result, EnhancementResult)
            
    @pytest.mark.asyncio
    async def test_enhance_batch_sequential(self, pipeline):
        """Test sequential batch enhancement."""
        documents = ["Doc 1", "Doc 2"]
        
        # Mock quality measurement
        pipeline._measure_quality = AsyncMock(return_value=0.7)
        
        # Mock strategy application
        pipeline._apply_strategy = AsyncMock(return_value={
            "success": True,
            "enhanced_content": "Enhanced",
            "improvement": {"strategy": "clarity", "description": "Improved"},
            "quality": 0.8,
            "cost": 0.01
        })
        
        config = EnhancementConfig(max_passes=1, parallel=False)
        results = await pipeline.enhance_batch(documents, config)
        
        assert len(results) == 2
        
    @pytest.mark.asyncio
    async def test_quality_threshold_reached(self, pipeline):
        """Test stopping when quality threshold is reached."""
        # Mock quality measurements
        quality_values = [0.6, 0.85]  # Second value exceeds threshold
        pipeline._measure_quality = AsyncMock(side_effect=quality_values)
        
        # Mock strategy application
        pipeline._apply_strategy = AsyncMock(return_value={
            "success": True,
            "enhanced_content": "Enhanced",
            "improvement": {"strategy": "clarity", "description": "Improved"},
            "quality": 0.85,
            "cost": 0.01
        })
        
        config = EnhancementConfig(quality_threshold=0.8, max_passes=5)
        result = await pipeline.enhance_document("Test", config)
        
        assert result.success is True
        assert result.enhancement_passes == 1  # Should stop after first pass
        
    @pytest.mark.asyncio
    async def test_cost_limit_reached(self, pipeline):
        """Test stopping when cost limit is reached."""
        # Mock quality measurement
        pipeline._measure_quality = AsyncMock(return_value=0.6)
        
        # Mock strategy application with high cost
        pipeline._apply_strategy = AsyncMock(return_value={
            "success": True,
            "enhanced_content": "Enhanced",
            "improvement": {"strategy": "clarity", "description": "Improved"},
            "quality": 0.65,
            "cost": 0.60  # Exceeds default limit
        })
        
        config = EnhancementConfig(cost_limit=0.50, max_passes=5)
        result = await pipeline.enhance_document("Test", config)
        
        assert result.success is True
        assert result.total_cost <= 0.60
        
    @pytest.mark.asyncio
    async def test_rollback_on_degradation(self, pipeline):
        """Test rollback when quality degrades."""
        settings = EnhancementSettings()
        settings.pipeline.rollback_on_degradation = True
        pipeline = EnhancementPipeline(settings)
        
        # Mock quality measurements (degradation)
        quality_values = [0.7, 0.6, 0.5]
        pipeline._measure_quality = AsyncMock(side_effect=quality_values)
        
        # Mock strategy application
        pipeline._apply_strategy = AsyncMock(return_value={
            "success": True,
            "enhanced_content": "Worse content",
            "improvement": {"strategy": "clarity", "description": "Failed"},
            "quality": 0.5,
            "cost": 0.01
        })
        
        config = EnhancementConfig(improvement_threshold=0.05)
        result = await pipeline.enhance_document("Original", config)
        
        assert result.success is True
        # Should rollback to original due to degradation
        
    @pytest.mark.asyncio
    async def test_cache_functionality(self, pipeline):
        """Test caching of enhancement results."""
        content = "Test content for caching"
        
        # Mock quality measurement
        pipeline._measure_quality = AsyncMock(return_value=0.7)
        
        # Mock strategy application
        pipeline._apply_strategy = AsyncMock(return_value={
            "success": True,
            "enhanced_content": "Enhanced",
            "improvement": {"strategy": "clarity", "description": "Improved"},
            "quality": 0.8,
            "cost": 0.01
        })
        
        config = EnhancementConfig(max_passes=1)
        
        # First call
        result1 = await pipeline.enhance_document(content, config)
        
        # Second call (should use cache)
        result2 = await pipeline.enhance_document(content, config)
        
        # Results should be the same (from cache)
        assert result1.enhanced_content == result2.enhanced_content
        assert result1.total_cost == result2.total_cost
        
    def test_simple_quality_score(self, pipeline):
        """Test fallback quality scoring."""
        # Short content
        score1 = pipeline._simple_quality_score("Short")
        assert 0 <= score1 <= 1
        
        # Medium content with structure
        content2 = "# Header\n\nParagraph one.\n\nParagraph two.\n\nConclusion."
        score2 = pipeline._simple_quality_score(content2)
        assert score2 > score1  # Should be higher due to structure
        
        # Long structured content
        content3 = "# Title\n\n" + ("This is a sentence. " * 20) + "\n\n" + ("Another paragraph. " * 10)
        score3 = pipeline._simple_quality_score(content3)
        assert score3 > 0.5
        
    def test_get_enhancement_history(self, pipeline):
        """Test getting enhancement history."""
        # Add some versions to history
        pipeline.history.add_version("Content 1", 0.5, "doc1")
        pipeline.history.add_version("Content 2", 0.6, "doc1")
        
        versions = pipeline.get_enhancement_history("doc1")
        assert len(versions) == 2
        
    def test_compare_versions(self, pipeline):
        """Test comparing enhancement versions."""
        # Add versions
        v1 = pipeline.history.add_version("Content 1", 0.5, "doc1")
        v2 = pipeline.history.add_version("Content 2", 0.6, "doc1")
        
        comparison = pipeline.compare_versions(v1.version_id, v2.version_id, "doc1")
        assert comparison is not None
        assert comparison.quality_delta == 0.1
        
    def test_get_metrics_summary(self, pipeline):
        """Test getting metrics summary."""
        summary = pipeline.get_metrics_summary()
        
        assert "total_documents" in summary
        assert "average_improvement" in summary
        assert "total_cost" in summary
        assert "strategies_usage" in summary
        assert "cache_hit_rate" in summary
        
    @pytest.mark.asyncio
    async def test_cleanup(self, pipeline):
        """Test pipeline cleanup."""
        await pipeline.cleanup()
        
        assert len(pipeline._cache) == 0
        
    @pytest.mark.asyncio
    async def test_enhancement_with_miair(self, pipeline):
        """Test enhancement with MIAIR optimization."""
        # Mock MIAIR engine
        mock_miair = Mock()
        mock_miair.optimize_document = AsyncMock(return_value={
            "optimized_content": "MIAIR optimized content"
        })
        pipeline.miair_engine = mock_miair
        pipeline.settings.pipeline.use_miair_optimization = True
        
        # Mock quality measurement
        pipeline._measure_quality = AsyncMock(return_value=0.7)
        
        # Mock strategy application
        pipeline._apply_strategy = AsyncMock(return_value={
            "success": True,
            "enhanced_content": "Enhanced",
            "improvement": {"strategy": "clarity", "description": "Improved"},
            "quality": 0.75,
            "cost": 0.01
        })
        
        config = EnhancementConfig(max_passes=1)
        result = await pipeline.enhance_document("Test", config)
        
        # MIAIR optimization should have been called
        mock_miair.optimize_document.assert_called()
        
    @pytest.mark.asyncio
    async def test_error_handling(self, pipeline):
        """Test error handling in enhancement."""
        # Mock quality measurement to raise error
        pipeline._measure_quality = AsyncMock(side_effect=Exception("Test error"))
        
        result = await pipeline.enhance_document("Test content")
        
        assert result.success is False
        assert len(result.errors) > 0
        assert "Test error" in result.errors[0]