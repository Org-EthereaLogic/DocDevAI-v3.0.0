"""
Test Suite for M009 Enhancement Pipeline - Pass 1: Core Implementation
DevDocAI v3.0.0 - Enhanced 4-Pass TDD Methodology

Test Coverage Target: 80%+ for Pass 1
Dependencies: M003 (MIAIR Engine), M008 (LLM Adapter)
Requirements: FR-011 (MIAIR methodology), FR-012 (Multi-LLM synthesis)
"""

import time
from unittest.mock import Mock, patch

import pytest

# Import dependencies for mocking
from devdocai.core.config import ConfigurationManager

# Import the module under test
from devdocai.intelligence.enhance import (
    EnhancementConfig,
    EnhancementPipeline,
    EnhancementResult,
    EnhancementStrategy,
)
from devdocai.intelligence.llm_adapter import LLMResponse
from devdocai.intelligence.miair_batch import OptimizationResult
from devdocai.intelligence.miair_strategies import DocumentMetrics


class TestEnhancementPipeline:
    """Test suite for M009 Enhancement Pipeline core functionality."""

    @pytest.fixture
    def mock_config_manager(self):
        """Mock configuration manager."""
        mock_config = Mock(spec=ConfigurationManager)
        mock_config.get.return_value = True
        return mock_config

    @pytest.fixture
    def mock_miair_result(self):
        """Mock MIAIR optimization result."""
        final_metrics = DocumentMetrics(
            entropy=0.75, coherence=0.85, quality_score=0.85, word_count=50, unique_words=35
        )
        return OptimizationResult(
            initial_content="Original content",
            final_content="MIAIR optimized content here",
            iterations=3,
            initial_quality=0.6,
            final_quality=0.85,
            improvement_percentage=45.5,
            initial_metrics=None,
            final_metrics=final_metrics,
            optimization_time=0.15,
        )

    @pytest.fixture
    def mock_llm_result(self):
        """Mock LLM response."""
        return LLMResponse(
            content="LLM enhanced content here",
            provider="claude",
            tokens_used=100,
            cost=0.05,
            latency=1.2,
        )

    @pytest.fixture
    def enhancement_pipeline(self, mock_config_manager):
        """Create enhancement pipeline instance with mocked dependencies."""
        with patch("devdocai.intelligence.enhance.StorageManager"), patch(
            "devdocai.intelligence.enhance.MIAIREngine"
        ), patch("devdocai.intelligence.enhance.LLMAdapter"):
            pipeline = EnhancementPipeline(mock_config_manager)
            return pipeline

    def test_initialization(self, enhancement_pipeline):
        """Test M009 Enhancement Pipeline initialization."""
        assert enhancement_pipeline.config_manager is not None
        assert enhancement_pipeline.storage_manager is not None
        assert enhancement_pipeline.miair_engine is not None
        assert enhancement_pipeline.llm_adapter is not None
        assert isinstance(enhancement_pipeline.enhancement_config, EnhancementConfig)

    def test_default_configuration(self, enhancement_pipeline):
        """Test default enhancement configuration."""
        config = enhancement_pipeline.enhancement_config
        assert config.strategy == EnhancementStrategy.COMBINED
        assert config.miair_weight == 0.4
        assert config.llm_weight == 0.6
        assert config.quality_threshold == 85.0
        assert config.max_iterations == 3
        assert config.enable_diff_view is True
        assert config.enable_consensus is True

    def test_configuration_update(self, enhancement_pipeline):
        """Test enhancement pipeline configuration updates."""
        new_config = EnhancementConfig(
            strategy=EnhancementStrategy.MIAIR_ONLY,
            miair_weight=1.0,
            llm_weight=0.0,
            quality_threshold=90.0,
        )

        enhancement_pipeline.configure(new_config)

        assert enhancement_pipeline.enhancement_config.strategy == EnhancementStrategy.MIAIR_ONLY
        assert enhancement_pipeline.enhancement_config.miair_weight == 1.0
        assert enhancement_pipeline.enhancement_config.quality_threshold == 90.0

    def test_enhance_document_empty_content(self, enhancement_pipeline):
        """Test enhancement with empty content."""
        result = enhancement_pipeline.enhance_document("")

        assert result.success is False
        assert result.error_message == "Empty content provided"
        assert result.original_content == ""
        assert result.enhanced_content == ""

    def test_enhance_document_whitespace_only(self, enhancement_pipeline):
        """Test enhancement with whitespace-only content."""
        result = enhancement_pipeline.enhance_document("   \n\t  ")

        assert result.success is False
        assert result.error_message == "Empty content provided"

    def test_miair_only_enhancement_success(self, enhancement_pipeline, mock_miair_result):
        """Test MIAIR-only enhancement strategy (FR-011)."""
        enhancement_pipeline.miair_engine.optimize.return_value = mock_miair_result
        enhancement_pipeline.configure(EnhancementConfig(strategy=EnhancementStrategy.MIAIR_ONLY))

        content = "Original document content for MIAIR optimization"
        result = enhancement_pipeline.enhance_document(content)

        assert result.success is True
        assert result.strategy_used == EnhancementStrategy.MIAIR_ONLY
        assert result.enhanced_content == "MIAIR optimized content here"
        assert result.quality_improvement == 45.5
        assert result.entropy_reduction == 0.25
        assert result.iterations_used == 3
        assert result.miair_result == mock_miair_result

    def test_miair_only_enhancement_failure(self, enhancement_pipeline):
        """Test MIAIR-only enhancement with MIAIR failure."""
        mock_failed_result = OptimizationResult(
            initial_content="Original content",
            final_content="Original content",  # No improvement
            iterations=0,
            initial_quality=0.6,
            final_quality=0.6,
            improvement_percentage=0.0,
            initial_metrics=None,
            final_metrics=DocumentMetrics(
                entropy=0.6, coherence=0.6, quality_score=0.6, word_count=10, unique_words=10
            ),
            optimization_time=0.1,
        )

        enhancement_pipeline.miair_engine.optimize.return_value = mock_failed_result
        enhancement_pipeline.configure(EnhancementConfig(strategy=EnhancementStrategy.MIAIR_ONLY))

        content = "Content to enhance"
        result = enhancement_pipeline.enhance_document(content)

        assert result.success is False  # 0% improvement = no success
        assert result.enhanced_content == "Original content"  # MIAIR result final_content
        assert result.quality_improvement == 0.0

    def test_llm_only_enhancement_success(self, enhancement_pipeline, mock_llm_result):
        """Test LLM-only enhancement strategy (FR-012)."""
        enhancement_pipeline.llm_adapter.generate.return_value = mock_llm_result
        enhancement_pipeline.configure(EnhancementConfig(strategy=EnhancementStrategy.LLM_ONLY))

        content = "Original document content for LLM enhancement"
        result = enhancement_pipeline.enhance_document(content, document_type="technical")

        assert result.success is True
        assert result.strategy_used == EnhancementStrategy.LLM_ONLY
        assert result.enhanced_content == "LLM enhanced content here"
        assert result.quality_improvement > 0
        assert result.iterations_used == 1
        assert result.llm_result.enhanced_content == mock_llm_result.content
        assert result.llm_result.provider_used == mock_llm_result.provider

    def test_llm_only_enhancement_failure(self, enhancement_pipeline):
        """Test LLM-only enhancement with LLM failure."""
        enhancement_pipeline.llm_adapter.generate.side_effect = Exception("LLM enhancement failed")
        enhancement_pipeline.configure(EnhancementConfig(strategy=EnhancementStrategy.LLM_ONLY))

        content = "Content to enhance"
        result = enhancement_pipeline.enhance_document(content)

        assert result.success is False
        assert "LLM enhancement failed" in result.error_message

    def test_combined_enhancement_success(
        self, enhancement_pipeline, mock_miair_result, mock_llm_result
    ):
        """Test combined MIAIR + LLM enhancement strategy (FR-011 + FR-012)."""
        enhancement_pipeline.miair_engine.optimize.return_value = mock_miair_result
        enhancement_pipeline.llm_adapter.generate.return_value = mock_llm_result
        enhancement_pipeline.configure(EnhancementConfig(strategy=EnhancementStrategy.COMBINED))

        content = "Original document content for combined enhancement"
        result = enhancement_pipeline.enhance_document(content, document_type="documentation")

        assert result.success is True
        assert result.strategy_used == EnhancementStrategy.COMBINED
        assert result.enhanced_content == "LLM enhanced content here"  # Final LLM result

        # Test weighted combination
        expected_improvement = (45.5 * 0.4) + (25.0 * 0.6)  # MIAIR * weight + LLM * weight
        assert abs(result.quality_improvement - expected_improvement) < 1.0

        assert result.entropy_reduction == 0.25
        assert result.miair_result == mock_miair_result
        assert result.llm_result.enhanced_content == mock_llm_result.content
        assert result.llm_result.provider_used == mock_llm_result.provider

    def test_combined_enhancement_miair_fails_llm_succeeds(
        self, enhancement_pipeline, mock_llm_result
    ):
        """Test combined enhancement when MIAIR fails but LLM succeeds."""
        mock_failed_miair = OptimizationResult(
            initial_content="Original content",
            final_content="Original content",  # No improvement
            iterations=0,
            initial_quality=0.6,
            final_quality=0.6,
            improvement_percentage=0.0,
            initial_metrics=None,
            final_metrics=DocumentMetrics(
                entropy=0.6, coherence=0.6, quality_score=0.6, word_count=10, unique_words=10
            ),
            optimization_time=0.1,
        )

        enhancement_pipeline.miair_engine.optimize.return_value = mock_failed_miair
        enhancement_pipeline.llm_adapter.generate.return_value = mock_llm_result
        enhancement_pipeline.configure(EnhancementConfig(strategy=EnhancementStrategy.COMBINED))

        content = "Content to enhance"
        result = enhancement_pipeline.enhance_document(content)

        assert result.success is True
        assert result.enhanced_content == "LLM enhanced content here"
        assert result.miair_result is None  # Failed MIAIR not included

    def test_combined_enhancement_llm_fails_miair_succeeds(
        self, enhancement_pipeline, mock_miair_result
    ):
        """Test combined enhancement when LLM fails but MIAIR succeeds."""
        enhancement_pipeline.miair_engine.optimize.return_value = mock_miair_result
        enhancement_pipeline.llm_adapter.generate.side_effect = Exception("LLM failed")
        enhancement_pipeline.configure(EnhancementConfig(strategy=EnhancementStrategy.COMBINED))

        content = "Content to enhance"
        result = enhancement_pipeline.enhance_document(content)

        assert result.success is True
        assert result.enhanced_content == "MIAIR optimized content here"
        assert result.llm_result is None  # Failed LLM not included

    def test_combined_enhancement_both_fail(self, enhancement_pipeline):
        """Test combined enhancement when both MIAIR and LLM fail."""
        mock_failed_miair = OptimizationResult(
            initial_content="Original content",
            final_content="Original content",  # No improvement
            iterations=0,
            initial_quality=0.6,
            final_quality=0.6,
            improvement_percentage=0.0,
            initial_metrics=None,
            final_metrics=DocumentMetrics(
                entropy=0.6, coherence=0.6, quality_score=0.6, word_count=10, unique_words=10
            ),
            optimization_time=0.1,
        )
        enhancement_pipeline.miair_engine.optimize.return_value = mock_failed_miair
        enhancement_pipeline.llm_adapter.generate.side_effect = Exception("LLM failed")
        enhancement_pipeline.configure(EnhancementConfig(strategy=EnhancementStrategy.COMBINED))

        content = "Content to enhance"
        result = enhancement_pipeline.enhance_document(content)

        assert result.success is False
        assert result.enhanced_content == content  # Original content returned

    def test_weighted_consensus_enhancement(self, enhancement_pipeline, mock_llm_result):
        """Test weighted consensus enhancement strategy (FR-012)."""
        enhancement_pipeline.llm_adapter.generate.return_value = mock_llm_result
        enhancement_pipeline.configure(
            EnhancementConfig(strategy=EnhancementStrategy.WEIGHTED_CONSENSUS)
        )

        content = "Original document content for consensus enhancement"
        result = enhancement_pipeline.enhance_document(content, document_type="guide")

        assert result.success is True
        assert result.strategy_used == EnhancementStrategy.WEIGHTED_CONSENSUS
        assert result.enhanced_content == "LLM enhanced content here"
        assert result.quality_improvement == 35.0  # Placeholder value for Pass 1

    def test_diff_view_generation(self, enhancement_pipeline, mock_miair_result):
        """Test diff view generation for before/after comparison."""
        enhancement_pipeline.miair_engine.optimize.return_value = mock_miair_result
        enhancement_pipeline.configure(
            EnhancementConfig(strategy=EnhancementStrategy.MIAIR_ONLY, enable_diff_view=True)
        )

        content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\nLine 6"
        result = enhancement_pipeline.enhance_document(content)

        assert result.success is True
        assert result.diff_view is not None
        assert "ENHANCEMENT DIFF VIEW" in result.diff_view
        assert "Original:" in result.diff_view
        assert "Enhanced:" in result.diff_view

    def test_diff_view_disabled(self, enhancement_pipeline, mock_miair_result):
        """Test diff view disabled configuration."""
        enhancement_pipeline.miair_engine.optimize.return_value = mock_miair_result
        enhancement_pipeline.configure(
            EnhancementConfig(strategy=EnhancementStrategy.MIAIR_ONLY, enable_diff_view=False)
        )

        content = "Test content"
        result = enhancement_pipeline.enhance_document(content)

        assert result.success is True
        assert result.diff_view is None

    def test_processing_time_tracking(self, enhancement_pipeline, mock_miair_result):
        """Test processing time tracking."""
        enhancement_pipeline.miair_engine.optimize.return_value = mock_miair_result
        enhancement_pipeline.configure(EnhancementConfig(strategy=EnhancementStrategy.MIAIR_ONLY))

        content = "Content to time"
        start_time = time.time()
        result = enhancement_pipeline.enhance_document(content)
        end_time = time.time()

        assert result.success is True
        assert result.processing_time > 0
        assert result.processing_time <= (end_time - start_time + 0.1)  # Allow small margin

    def test_unknown_strategy_error(self, enhancement_pipeline):
        """Test handling of unknown enhancement strategy."""
        # Manually set invalid strategy
        enhancement_pipeline.enhancement_config.strategy = "invalid_strategy"

        content = "Test content"
        result = enhancement_pipeline.enhance_document(content)

        assert result.success is False
        assert "Unknown enhancement strategy" in result.error_message

    def test_exception_handling(self, enhancement_pipeline):
        """Test exception handling in enhancement pipeline."""
        # Mock MIAIR engine to raise exception
        enhancement_pipeline.miair_engine.optimize.side_effect = Exception("MIAIR crashed")
        enhancement_pipeline.configure(EnhancementConfig(strategy=EnhancementStrategy.MIAIR_ONLY))

        content = "Test content"
        result = enhancement_pipeline.enhance_document(content)

        assert result.success is False
        assert "MIAIR enhancement error" in result.error_message
        assert result.processing_time > 0

    def test_get_enhancement_statistics(self, enhancement_pipeline):
        """Test enhancement statistics retrieval."""
        stats = enhancement_pipeline.get_enhancement_statistics()

        assert "pipeline_version" in stats
        assert stats["pipeline_version"] == "M009 Pass 1"
        assert stats["strategy"] == "combined"  # Default strategy
        assert stats["miair_weight"] == 0.4
        assert stats["llm_weight"] == 0.6
        assert stats["quality_threshold"] == 85.0

        assert "dependencies" in stats
        dependencies = stats["dependencies"]
        assert "miair_engine" in dependencies
        assert "llm_adapter" in dependencies
        assert "storage_manager" in dependencies


class TestEnhancementConfig:
    """Test suite for EnhancementConfig data class."""

    def test_default_config(self):
        """Test default enhancement configuration values."""
        config = EnhancementConfig()

        assert config.strategy == EnhancementStrategy.COMBINED
        assert config.miair_weight == 0.4
        assert config.llm_weight == 0.6
        assert config.quality_threshold == 85.0
        assert config.max_iterations == 3
        assert config.enable_diff_view is True
        assert config.enable_consensus is True
        assert "claude" in config.consensus_providers
        assert "chatgpt" in config.consensus_providers
        assert "gemini" in config.consensus_providers
        assert config.timeout_seconds == 30.0

    def test_custom_config(self):
        """Test custom enhancement configuration."""
        config = EnhancementConfig(
            strategy=EnhancementStrategy.LLM_ONLY,
            miair_weight=0.2,
            llm_weight=0.8,
            quality_threshold=95.0,
            max_iterations=5,
            enable_diff_view=False,
            consensus_providers=["claude", "chatgpt"],
            timeout_seconds=60.0,
        )

        assert config.strategy == EnhancementStrategy.LLM_ONLY
        assert config.miair_weight == 0.2
        assert config.llm_weight == 0.8
        assert config.quality_threshold == 95.0
        assert config.max_iterations == 5
        assert config.enable_diff_view is False
        assert len(config.consensus_providers) == 2


class TestEnhancementResult:
    """Test suite for EnhancementResult data class."""

    def test_result_creation(self):
        """Test enhancement result creation."""
        result = EnhancementResult(
            success=True,
            original_content="Original",
            enhanced_content="Enhanced",
            strategy_used=EnhancementStrategy.COMBINED,
            quality_improvement=45.2,
            entropy_reduction=0.15,
            processing_time=1.5,
            iterations_used=2,
        )

        assert result.success is True
        assert result.original_content == "Original"
        assert result.enhanced_content == "Enhanced"
        assert result.strategy_used == EnhancementStrategy.COMBINED
        assert result.quality_improvement == 45.2
        assert result.entropy_reduction == 0.15
        assert result.processing_time == 1.5
        assert result.iterations_used == 2

    def test_result_with_error(self):
        """Test enhancement result with error."""
        result = EnhancementResult(
            success=False,
            original_content="Original",
            enhanced_content="Original",
            strategy_used=EnhancementStrategy.MIAIR_ONLY,
            error_message="Enhancement failed",
        )

        assert result.success is False
        assert result.error_message == "Enhancement failed"
        assert result.quality_improvement == 0.0  # Default value
        assert result.entropy_reduction == 0.0  # Default value


# Performance and Integration Tests for Pass 1


class TestEnhancementPerformance:
    """Basic performance tests for M009 Enhancement Pipeline."""

    @pytest.fixture
    def enhancement_pipeline(self):
        """Create pipeline with mocked dependencies for performance testing."""
        with patch("devdocai.intelligence.enhance.ConfigurationManager"), patch(
            "devdocai.intelligence.enhance.StorageManager"
        ), patch("devdocai.intelligence.enhance.MIAIREngine"), patch(
            "devdocai.intelligence.enhance.LLMAdapter"
        ):
            pipeline = EnhancementPipeline()

            # Mock fast responses
            mock_miair_result = OptimizationResult(
                initial_content="Test content",
                final_content="Quick MIAIR result",
                iterations=1,
                initial_quality=0.5,
                final_quality=1.0,
                improvement_percentage=50.0,
                initial_metrics=None,
                final_metrics=DocumentMetrics(
                    entropy=0.8, coherence=0.9, quality_score=1.0, word_count=20, unique_words=15
                ),
                optimization_time=0.01,
            )
            pipeline.miair_engine.optimize.return_value = mock_miair_result

            mock_llm_result = LLMResponse(
                content="Quick LLM result",
                provider="claude",
                tokens_used=10,
                cost=0.001,
                latency=0.005,
            )
            pipeline.llm_adapter.generate.return_value = mock_llm_result

            return pipeline

    def test_basic_performance_timing(self, enhancement_pipeline):
        """Test basic performance timing for enhancement operations."""
        content = "Short document content for performance test"

        # Test MIAIR-only performance
        enhancement_pipeline.configure(EnhancementConfig(strategy=EnhancementStrategy.MIAIR_ONLY))
        start_time = time.time()
        result = enhancement_pipeline.enhance_document(content)
        duration = time.time() - start_time

        assert result.success is True
        assert duration < 1.0  # Should be fast with mocked dependencies
        assert result.processing_time < duration

    def test_multiple_enhancements_performance(self, enhancement_pipeline):
        """Test performance with multiple enhancement operations."""
        contents = [f"Document content {i}" for i in range(10)]

        start_time = time.time()
        results = []
        for content in contents:
            result = enhancement_pipeline.enhance_document(content)
            results.append(result)
        total_time = time.time() - start_time

        assert len(results) == 10
        assert all(r.success for r in results)
        assert total_time < 5.0  # Should complete 10 enhancements in under 5 seconds


# Integration Tests


class TestEnhancementIntegration:
    """Integration tests with actual dependencies (where possible)."""

    def test_integration_with_real_config(self):
        """Test integration with real ConfigurationManager."""
        # This test uses real ConfigurationManager but mocked other dependencies
        with patch("devdocai.intelligence.enhance.StorageManager"), patch(
            "devdocai.intelligence.enhance.MIAIREngine"
        ), patch("devdocai.intelligence.enhance.LLMAdapter"):

            pipeline = EnhancementPipeline()  # Uses real ConfigurationManager

            assert pipeline.config_manager is not None
            assert hasattr(pipeline.config_manager, "get")

            # Test that pipeline can access configuration
            stats = pipeline.get_enhancement_statistics()
            assert "dependencies" in stats

    def test_error_propagation(self):
        """Test error propagation from dependencies."""
        with patch("devdocai.intelligence.enhance.ConfigurationManager") as mock_config, patch(
            "devdocai.intelligence.enhance.StorageManager"
        ) as mock_storage, patch("devdocai.intelligence.enhance.MIAIREngine") as mock_miair, patch(
            "devdocai.intelligence.enhance.LLMAdapter"
        ) as mock_llm:

            # Setup mocks to raise exceptions during initialization
            mock_storage.side_effect = Exception("Storage initialization failed")

            with pytest.raises(Exception):
                EnhancementPipeline(mock_config)


if __name__ == "__main__":
    # Run tests with coverage
    pytest.main(
        [__file__, "-v", "--cov=devdocai.intelligence.enhance", "--cov-report=term-missing"]
    )
