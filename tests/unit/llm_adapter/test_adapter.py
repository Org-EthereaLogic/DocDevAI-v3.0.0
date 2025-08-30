"""
Tests for M008 LLM Adapter main functionality.

Tests the primary LLM adapter interface including generation,
multi-provider synthesis, fallback handling, and cost tracking.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal
from datetime import datetime

from devdocai.llm_adapter.adapter import LLMAdapter
from devdocai.llm_adapter.config import (
    LLMConfig, ProviderConfig, ProviderType, CostLimits, FallbackStrategy
)
from devdocai.llm_adapter.providers.base import LLMRequest, LLMResponse, TokenUsage


class MockProvider:
    """Mock provider for testing."""
    
    def __init__(self, name, config):
        self.provider_name = name
        self.config = config
        self._healthy = True
        self._responses = []
        self._call_count = 0
    
    def is_healthy(self):
        return self._healthy
    
    def set_healthy(self, healthy):
        self._healthy = healthy
    
    def add_mock_response(self, response):
        """Add a mock response to be returned."""
        self._responses.append(response)
    
    async def generate(self, request):
        """Mock generate method."""
        self._call_count += 1
        if self._responses:
            response = self._responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response
        
        # Default mock response
        return LLMResponse(
            content=f"Mock response from {self.provider_name}",
            finish_reason="stop",
            model=request.model,
            provider=self.provider_name,
            usage=TokenUsage(
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                prompt_cost=Decimal("0.01"),
                completion_cost=Decimal("0.02"),
                total_cost=Decimal("0.03")
            ),
            request_id=request.request_id,
            response_time_ms=100.0
        )
    
    async def generate_stream(self, request):
        """Mock streaming generate method."""
        response = await self.generate(request)
        yield response
    
    def estimate_cost(self, request):
        """Mock cost estimation."""
        return Decimal("0.05")
    
    def get_available_models(self):
        """Mock available models."""
        return ["mock-model-1", "mock-model-2"]


class TestLLMAdapter:
    """Test main LLM adapter functionality."""
    
    @pytest.fixture
    def basic_config(self):
        """Create basic test configuration."""
        providers = {
            "openai": ProviderConfig(
                provider_type=ProviderType.OPENAI,
                api_key="test-openai-key"
            ),
            "anthropic": ProviderConfig(
                provider_type=ProviderType.ANTHROPIC,
                api_key="test-anthropic-key"
            )
        }
        
        return LLMConfig(
            providers=providers,
            cost_limits=CostLimits(
                daily_limit_usd=Decimal("10.00"),
                monthly_limit_usd=Decimal("200.00")
            ),
            cost_tracking_enabled=True,
            fallback_enabled=True
        )
    
    @pytest.fixture
    def mock_adapter(self, basic_config):
        """Create LLM adapter with mock providers."""
        with patch('devdocai.llm_adapter.adapter.OpenAIProvider') as mock_openai, \
             patch('devdocai.llm_adapter.adapter.AnthropicProvider') as mock_anthropic:
            
            # Create mock providers
            openai_provider = MockProvider("openai", basic_config.providers["openai"])
            anthropic_provider = MockProvider("anthropic", basic_config.providers["anthropic"])
            
            mock_openai.return_value = openai_provider
            mock_anthropic.return_value = anthropic_provider
            
            adapter = LLMAdapter(basic_config)
            
            # Store references to mock providers for test manipulation
            adapter._mock_openai = openai_provider
            adapter._mock_anthropic = anthropic_provider
            
            return adapter
    
    def test_adapter_initialization(self, mock_adapter):
        """Test adapter initialization."""
        assert len(mock_adapter.providers) == 2
        assert "openai" in mock_adapter.providers
        assert "anthropic" in mock_adapter.providers
        assert mock_adapter.cost_tracker is not None
        assert mock_adapter.fallback_manager is not None
    
    @pytest.mark.asyncio
    async def test_basic_generation(self, mock_adapter):
        """Test basic text generation."""
        response = await mock_adapter.generate("Hello, world!")
        
        assert isinstance(response, LLMResponse)
        assert response.content.startswith("Mock response")
        assert response.provider in ["openai", "anthropic"]
        assert response.usage.total_cost > 0
    
    @pytest.mark.asyncio
    async def test_generation_with_specific_provider(self, mock_adapter):
        """Test generation with specific provider selection."""
        response = await mock_adapter.generate(
            "Hello, world!",
            provider="anthropic"
        )
        
        assert response.provider == "anthropic"
        assert "anthropic" in response.content
    
    @pytest.mark.asyncio
    async def test_generation_with_model_specification(self, mock_adapter):
        """Test generation with specific model."""
        response = await mock_adapter.generate(
            "Hello, world!",
            model="gpt-4",
            provider="openai"
        )
        
        assert response.model == "gpt-4"
    
    @pytest.mark.asyncio
    async def test_generation_with_message_list(self, mock_adapter):
        """Test generation with message list format."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"}
        ]
        
        response = await mock_adapter.generate(messages)
        
        assert isinstance(response, LLMResponse)
        assert response.content.startswith("Mock response")
    
    @pytest.mark.asyncio
    async def test_generation_cost_tracking(self, mock_adapter):
        """Test that generation records usage for cost tracking."""
        initial_records = len(mock_adapter.cost_tracker._usage_records)
        
        response = await mock_adapter.generate("Test cost tracking")
        
        # Should have recorded usage
        assert len(mock_adapter.cost_tracker._usage_records) == initial_records + 1
        
        usage_record = mock_adapter.cost_tracker._usage_records[-1]
        assert usage_record.provider == response.provider
        assert usage_record.total_cost == response.usage.total_cost
        assert usage_record.success is True
    
    @pytest.mark.asyncio
    async def test_budget_enforcement(self, mock_adapter):
        """Test budget limit enforcement."""
        # Set up a high-cost mock response that exceeds budget
        high_cost_response = LLMResponse(
            content="Expensive response",
            finish_reason="stop",
            model="gpt-4",
            provider="openai",
            usage=TokenUsage(
                prompt_tokens=10000,
                completion_tokens=5000,
                total_tokens=15000,
                prompt_cost=Decimal("50.00"),
                completion_cost=Decimal("100.00"),
                total_cost=Decimal("150.00")  # Exceeds daily limit
            ),
            request_id="expensive-request",
            response_time_ms=5000.0
        )
        
        # Mock the cost estimation to return high cost
        with patch.object(mock_adapter, '_estimate_request_cost', return_value=Decimal("150.00")):
            with pytest.raises(ValueError, match="Budget exceeded"):
                await mock_adapter.generate("Expensive request")
    
    @pytest.mark.asyncio
    async def test_fallback_on_provider_failure(self, mock_adapter):
        """Test fallback when primary provider fails."""
        from devdocai.llm_adapter.providers.base import ProviderError
        
        # Make OpenAI provider fail
        mock_adapter._mock_openai.add_mock_response(
            ProviderError("API error", "openai")
        )
        
        # Anthropic should work
        mock_adapter._mock_anthropic.add_mock_response(
            LLMResponse(
                content="Fallback response from Anthropic",
                finish_reason="stop",
                model="claude-3-sonnet",
                provider="anthropic",
                usage=TokenUsage(
                    prompt_tokens=100,
                    completion_tokens=50,
                    total_tokens=150,
                    total_cost=Decimal("0.05")
                ),
                request_id="fallback-test",
                response_time_ms=200.0
            )
        )
        
        response = await mock_adapter.generate(
            "Test fallback",
            provider="openai"  # Request OpenAI but should fallback to Anthropic
        )
        
        assert response.provider == "anthropic"
        assert "Anthropic" in response.content
    
    @pytest.mark.asyncio
    async def test_streaming_generation(self, mock_adapter):
        """Test streaming text generation."""
        chunks = []
        async for chunk in mock_adapter.generate_stream("Stream test"):
            chunks.append(chunk)
            
        assert len(chunks) == 1  # Mock provider returns single chunk
        assert isinstance(chunks[0], LLMResponse)
    
    @pytest.mark.asyncio
    async def test_multi_provider_synthesis(self, mock_adapter):
        """Test multi-provider synthesis."""
        # Set up different responses from each provider
        openai_response = LLMResponse(
            content="OpenAI response",
            finish_reason="stop",
            model="gpt-4",
            provider="openai",
            usage=TokenUsage(
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                total_cost=Decimal("0.10")
            ),
            request_id="synthesis-openai",
            response_time_ms=150.0
        )
        
        anthropic_response = LLMResponse(
            content="Anthropic response with more detail and explanation",
            finish_reason="stop", 
            model="claude-3-sonnet",
            provider="anthropic",
            usage=TokenUsage(
                prompt_tokens=100,
                completion_tokens=80,
                total_tokens=180,
                total_cost=Decimal("0.15")
            ),
            request_id="synthesis-anthropic",
            response_time_ms=200.0
        )
        
        mock_adapter._mock_openai.add_mock_response(openai_response)
        mock_adapter._mock_anthropic.add_mock_response(anthropic_response)
        
        result = await mock_adapter.synthesize(
            "Test synthesis",
            providers=["openai", "anthropic"]
        )
        
        assert "synthesized_response" in result
        assert "individual_responses" in result
        assert len(result["individual_responses"]) == 2
        assert result["total_cost"] == Decimal("0.25")
        assert "providers_used" in result
    
    @pytest.mark.asyncio
    async def test_synthesis_fallback_to_single(self, mock_adapter):
        """Test synthesis fallback when insufficient providers."""
        # Disable synthesis in config
        mock_adapter.config.synthesis.enabled = False
        
        result = await mock_adapter.synthesize("Test single fallback")
        
        assert "synthesized_response" in result
        assert len(result["individual_responses"]) == 1
        assert result["consensus_score"] == 1.0
    
    @pytest.mark.asyncio
    async def test_quality_analysis(self, mock_adapter):
        """Test content quality analysis."""
        # Mock quality analyzer
        mock_quality_result = {
            "readability": 0.8,
            "completeness": 0.7,
            "accuracy": 0.9,
            "structure": 0.8,
            "clarity": 0.75,
            "overall_score": 0.8,
            "word_count": 100,
            "character_count": 500
        }
        
        with patch.object(mock_adapter.quality_analyzer, 'analyze_quality', 
                         return_value=mock_quality_result) as mock_analyze:
            
            result = await mock_adapter.analyze_quality("Test content analysis")
            
            assert result["overall_score"] == 0.8
            assert result["readability"] == 0.8
            assert mock_analyze.called
    
    @pytest.mark.asyncio
    async def test_content_enhancement(self, mock_adapter):
        """Test content enhancement functionality."""
        # Mock quality analysis returning low quality
        mock_quality = {
            "overall_score": 0.5,
            "readability": 0.4,
            "clarity": 0.5
        }
        
        # Mock enhanced response
        enhanced_response = LLMResponse(
            content="This is enhanced content with better clarity and structure.",
            finish_reason="stop",
            model="gpt-4",
            provider="openai", 
            usage=TokenUsage(
                prompt_tokens=200,
                completion_tokens=100,
                total_tokens=300,
                total_cost=Decimal("0.20")
            ),
            request_id="enhancement-test",
            response_time_ms=500.0
        )
        
        mock_adapter._mock_openai.add_mock_response(enhanced_response)
        
        with patch.object(mock_adapter.quality_analyzer, 'analyze_quality',
                         side_effect=[mock_quality, {"overall_score": 0.8}]) as mock_analyze:
            
            result = await mock_adapter.enhance_content(
                "Poor quality content",
                target_quality=0.75
            )
            
            assert result["enhanced_content"] == enhanced_response.content
            assert result["improvement"] > 0
            assert result["iterations"] == 1
    
    @pytest.mark.asyncio
    async def test_usage_statistics(self, mock_adapter):
        """Test usage statistics retrieval."""
        # Generate some usage first
        await mock_adapter.generate("Test stats 1")
        await mock_adapter.generate("Test stats 2", provider="anthropic")
        
        stats = await mock_adapter.get_usage_stats(days=30)
        
        assert "usage_stats" in stats
        assert "provider_health" in stats
        assert "cost_limits" in stats
        
        usage_stats = stats["usage_stats"]
        assert usage_stats["total_requests"] >= 2
        assert "provider_breakdown" in usage_stats
        assert len(usage_stats["provider_breakdown"]) >= 1
    
    def test_request_preparation(self, mock_adapter):
        """Test request preparation from different input formats."""
        # String prompt
        request1 = mock_adapter._prepare_request("Hello")
        assert len(request1.messages) == 1
        assert request1.messages[0]["role"] == "user"
        assert request1.messages[0]["content"] == "Hello"
        
        # Message list
        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "User message"}
        ]
        request2 = mock_adapter._prepare_request(messages)
        assert request2.messages == messages
        
        # With additional parameters
        request3 = mock_adapter._prepare_request(
            "Test",
            model="gpt-4",
            temperature=0.5,
            max_tokens=100
        )
        assert request3.model == "gpt-4"
        assert request3.temperature == 0.5
        assert request3.max_tokens == 100
    
    def test_cost_estimation(self, mock_adapter):
        """Test request cost estimation."""
        request = LLMRequest(
            messages=[{"role": "user", "content": "Test"}],
            model="gpt-3.5-turbo"
        )
        
        cost = mock_adapter._estimate_request_cost(request, "openai")
        assert isinstance(cost, Decimal)
        assert cost > 0
        
        # Test average cost when no provider specified
        avg_cost = mock_adapter._estimate_request_cost(request)
        assert isinstance(avg_cost, Decimal)
        assert avg_cost > 0
    
    @pytest.mark.asyncio 
    async def test_context_manager(self, mock_adapter):
        """Test async context manager functionality."""
        async with mock_adapter as adapter:
            response = await adapter.generate("Context manager test")
            assert isinstance(response, LLMResponse)
    
    def test_provider_initialization_error_handling(self, basic_config):
        """Test graceful handling of provider initialization errors."""
        with patch('devdocai.llm_adapter.adapter.OpenAIProvider', 
                   side_effect=Exception("Provider init failed")):
            
            # Should still initialize but without the failed provider
            adapter = LLMAdapter(basic_config)
            
            # Should have fewer providers due to initialization failure
            assert len(adapter.providers) < len(basic_config.providers)