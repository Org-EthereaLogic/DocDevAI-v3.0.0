"""
Additional tests to raise coverage for M009 Enhancement Pipeline.

Targets unhit paths and helpers:
- Consensus failure branch
- LLM-only quality cap behavior
- Combined strategy weighting math with custom weights
- Private helper methods (_create_enhancement_prompt, _llm_response_to_enhancement_response, _handle_llm_error)
"""

from unittest.mock import patch

import pytest

from devdocai.intelligence.enhance import (
    EnhancementConfig,
    EnhancementPipeline,
    EnhancementStrategy,
)
from devdocai.intelligence.llm_adapter import LLMResponse
from devdocai.intelligence.miair_batch import OptimizationResult
from devdocai.intelligence.miair_strategies import DocumentMetrics


@pytest.fixture
def pipeline_with_mocks():
    """Create a pipeline instance with internal dependencies patched."""
    with patch("devdocai.intelligence.enhance.ConfigurationManager"), patch(
        "devdocai.intelligence.enhance.StorageManager"
    ), patch("devdocai.intelligence.enhance.MIAIREngine") as mock_miair, patch(
        "devdocai.intelligence.enhance.LLMAdapter"
    ) as mock_llm:
        p = EnhancementPipeline()
        yield p, mock_miair, mock_llm


def make_miair_result(
    improvement: float, final_content: str = "MIAIR optimized"
) -> OptimizationResult:
    """Helper to build a fake OptimizationResult with a desired improvement."""
    final_metrics = DocumentMetrics(
        entropy=0.7,
        coherence=0.9,
        quality_score=0.9,
        word_count=100,
        unique_words=60,
    )
    return OptimizationResult(
        initial_content="orig",
        final_content=final_content,
        iterations=2,
        initial_quality=0.5,
        final_quality=0.5 + (improvement / 100.0),
        improvement_percentage=improvement,
        initial_metrics=None,
        final_metrics=final_metrics,
        optimization_time=0.02,
    )


def test_consensus_failure_branch(pipeline_with_mocks):
    """WEIGHTED_CONSENSUS: ensure failure path is exercised when LLM fails."""
    pipeline, _mock_miair, mock_llm = pipeline_with_mocks
    pipeline.configure(EnhancementConfig(strategy=EnhancementStrategy.WEIGHTED_CONSENSUS))

    # Make LLM raise to trigger _handle_llm_error and failure return
    instance = mock_llm.return_value
    instance.generate.side_effect = Exception("provider error")

    result = pipeline.enhance_document("content", document_type="guide")

    assert result.success is False
    assert result.strategy_used == EnhancementStrategy.WEIGHTED_CONSENSUS
    assert result.error_message == "Consensus enhancement failed"


def test_llm_only_quality_cap_behavior(pipeline_with_mocks):
    """LLM_ONLY: quality_improvement is capped at 50.0 via min()."""
    pipeline, _mock_miair, mock_llm = pipeline_with_mocks
    pipeline.configure(EnhancementConfig(strategy=EnhancementStrategy.LLM_ONLY))

    # content length = 1; enhanced length = 200 -> raw score 200*25 = 5000 -> capped at 50
    instance = mock_llm.return_value
    instance.generate.return_value = LLMResponse(
        content="A" * 200,
        provider="claude",
        tokens_used=10,
        cost=0.001,
        latency=0.01,
    )

    result = pipeline.enhance_document("A", document_type="short")
    assert result.success is True
    assert result.quality_improvement == 50.0


def test_combined_weighting_with_custom_weights(pipeline_with_mocks):
    """COMBINED: only MIAIR succeeds; check weighted math with custom weights."""
    pipeline, mock_miair, mock_llm = pipeline_with_mocks
    # LLM fails; MIAIR succeeds with 40% improvement
    mock_miair.return_value.optimize.return_value = make_miair_result(
        40.0, final_content="after-miair"
    )
    mock_llm.return_value.generate.side_effect = Exception("llm down")

    pipeline.configure(
        EnhancementConfig(
            strategy=EnhancementStrategy.COMBINED,
            miair_weight=0.8,
            llm_weight=0.2,
        )
    )

    result = pipeline.enhance_document("Original text")
    assert result.success is True
    assert result.enhanced_content == "after-miair"
    # Expected combined improvement = 40 * 0.8 + 0 * 0.2
    assert abs(result.quality_improvement - 32.0) < 1e-6


def test_private_helpers_direct_calls(pipeline_with_mocks):
    """Directly exercise helper methods to raise line coverage."""
    pipeline, _mock_miair, _mock_llm = pipeline_with_mocks

    # _create_enhancement_prompt
    prompt = pipeline._create_enhancement_prompt("Body text", "doc")
    assert "Enhance the following doc" in prompt
    assert "Original Document:" in prompt
    assert "Enhanced Document:" in prompt

    # _llm_response_to_enhancement_response
    resp = pipeline._llm_response_to_enhancement_response(
        LLMResponse(content="out", provider="openai", tokens_used=5, cost=0.001, latency=0.02),
        "orig",
    )
    assert resp.success is True
    assert resp.enhanced_content == "out"
    assert resp.provider_used == "openai"

    # _handle_llm_error
    err = pipeline._handle_llm_error(RuntimeError("boom"), "orig")
    assert err.success is False
    assert err.error_message == "boom"
