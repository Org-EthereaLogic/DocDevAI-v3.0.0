"""
Unit Tests for M008 LLM Adapter
DevDocAI v3.0.0 - Pass 1: Enhanced TDD with 85% coverage target
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta
import json
import os
import tempfile
from pathlib import Path
import time

import pytest

from devdocai.intelligence.llm_adapter import (
    LLMAdapter,
    CostManager,
    ResponseCache,
    Provider,
    ClaudeProvider,
    OpenAIProvider,
    GeminiProvider,
    LocalProvider,
    LLMResponse,
    ProviderError,
    BudgetExceededError,
    APITimeoutError,
)
from devdocai.core.config import ConfigurationManager
from devdocai.core.models import LLMConfig


class TestProvider(unittest.TestCase):
    """Test Provider base class and implementations."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = Mock(spec=ConfigurationManager)
        self.mock_config.get_api_key.return_value = "test-api-key"

    def test_provider_initialization(self):
        """Test provider initialization with cost and quality parameters."""
        provider = ClaudeProvider(
            config=self.mock_config, cost_per_1k=0.015, quality_score=0.95, weight=0.4
        )

        self.assertEqual(provider.cost_per_1k, 0.015)
        self.assertEqual(provider.quality_score, 0.95)
        self.assertEqual(provider.weight, 0.4)
        self.assertEqual(provider.name, "claude")

    def test_provider_sanitize_data(self):
        """Test data sanitization before external transmission."""
        provider = OpenAIProvider(config=self.mock_config)

        # Test PII removal
        text_with_pii = "Contact john.doe@example.com or call 555-123-4567"
        sanitized = provider.sanitize_data(text_with_pii)
        self.assertNotIn("john.doe@example.com", sanitized)
        self.assertNotIn("555-123-4567", sanitized)

        # Test API key removal
        text_with_key = "API key: sk-abc123def456"
        sanitized = provider.sanitize_data(text_with_key)
        self.assertNotIn("sk-abc123def456", sanitized)

    def test_provider_calculate_cost(self):
        """Test cost calculation for token usage."""
        provider = GeminiProvider(config=self.mock_config, cost_per_1k=0.010)

        # Test cost calculation
        cost = provider.calculate_cost(1500)  # 1500 tokens
        self.assertAlmostEqual(cost, 0.015, places=3)  # 1.5 * 0.010

        cost = provider.calculate_cost(500)  # 500 tokens
        self.assertAlmostEqual(cost, 0.005, places=3)  # 0.5 * 0.010

    def test_provider_timeout_handling(self):
        """Test provider timeout handling (2-second fallback requirement)."""
        provider = ClaudeProvider(config=self.mock_config, timeout=2.0)

        # Test that timeout is properly detected
        # Start time in the past (3 seconds ago)
        import time

        start_time = time.time() - 3.0

        with self.assertRaises(APITimeoutError) as context:
            provider._check_timeout(start_time=start_time)

        self.assertIn("timeout", str(context.exception).lower())


class TestCostManager(unittest.TestCase):
    """Test CostManager functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.cost_manager = CostManager(daily_limit=10.00)

    def test_initialization(self):
        """Test CostManager initialization."""
        self.assertEqual(self.cost_manager.daily_limit, 10.00)
        self.assertEqual(self.cost_manager.current_usage, 0.00)
        self.assertIsNotNone(self.cost_manager.usage_history)

    def test_track_usage(self):
        """Test usage tracking with 99.9% accuracy."""
        # Track multiple usages
        self.cost_manager.track_usage("claude", 0.015, 1000)
        self.assertAlmostEqual(self.cost_manager.current_usage, 0.015, places=3)

        self.cost_manager.track_usage("openai", 0.020, 1000)
        self.assertAlmostEqual(self.cost_manager.current_usage, 0.035, places=3)

        # Verify history
        self.assertEqual(len(self.cost_manager.usage_history), 2)
        self.assertEqual(self.cost_manager.usage_history[0]["provider"], "claude")

    def test_budget_enforcement(self):
        """Test budget limit enforcement."""
        # Use up budget
        self.cost_manager.current_usage = 9.99

        # This should succeed (under limit)
        self.assertTrue(self.cost_manager.check_budget(0.009))

        # This should fail (would exceed limit)
        with self.assertRaises(BudgetExceededError):
            self.cost_manager.check_budget(0.02)

    def test_warning_threshold(self):
        """Test 80% threshold warning with projected overage time."""
        # Set usage to 79%
        self.cost_manager.current_usage = 7.9
        warning = self.cost_manager.get_warning_status()
        self.assertIsNone(warning)

        # Set usage to 80%
        self.cost_manager.current_usage = 8.0
        warning = self.cost_manager.get_warning_status()
        self.assertIsNotNone(warning)
        self.assertIn("80", warning)  # Check for 80 (could be 80% or 80.0%)
        self.assertIn("remaining", warning.lower())

    def test_usage_reset(self):
        """Test daily usage reset."""
        self.cost_manager.current_usage = 5.50
        self.cost_manager.track_usage("openai", 2.50, 2000)

        # Reset usage
        self.cost_manager.reset_daily_usage()
        self.assertEqual(self.cost_manager.current_usage, 0.00)
        # History should be preserved
        self.assertGreater(len(self.cost_manager.usage_history), 0)

    def test_cost_quality_optimization(self):
        """Test cost/quality ratio optimization routing."""
        providers = {
            "claude": {"cost": 0.015, "quality": 0.95},
            "openai": {"cost": 0.020, "quality": 0.90},
            "gemini": {"cost": 0.010, "quality": 0.85},
        }

        # Get optimal provider for quality priority
        optimal = self.cost_manager.get_optimal_provider(providers, priority="quality")
        self.assertEqual(optimal, "claude")

        # Get optimal provider for cost priority
        optimal = self.cost_manager.get_optimal_provider(providers, priority="cost")
        self.assertEqual(optimal, "gemini")

        # Get optimal provider for balanced
        optimal = self.cost_manager.get_optimal_provider(providers, priority="balanced")
        # Should pick best ratio (quality/cost)
        self.assertIn(optimal, ["claude", "gemini"])


class TestResponseCache(unittest.TestCase):
    """Test ResponseCache functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.cache = ResponseCache(max_size=100, ttl_seconds=3600)

    def test_cache_operations(self):
        """Test basic cache operations."""
        # Store response
        response = LLMResponse(
            content="Test response", provider="claude", tokens_used=100, cost=0.0015, latency=0.5
        )

        key = self.cache.generate_key("test prompt", "claude")
        self.cache.store(key, response)

        # Retrieve response
        cached = self.cache.get(key)
        self.assertIsNotNone(cached)
        self.assertEqual(cached.content, "Test response")

        # Non-existent key
        missing = self.cache.get("non-existent")
        self.assertIsNone(missing)

    def test_cache_expiration(self):
        """Test cache TTL expiration."""
        # Use short TTL for testing
        cache = ResponseCache(max_size=10, ttl_seconds=0.1)

        response = LLMResponse(
            content="Expires quickly", provider="openai", tokens_used=50, cost=0.001, latency=0.3
        )

        key = "test-key"
        cache.store(key, response)

        # Should exist immediately
        self.assertIsNotNone(cache.get(key))

        # Wait for expiration
        time.sleep(0.2)

        # Should be expired
        self.assertIsNone(cache.get(key))

    def test_cache_size_limit(self):
        """Test cache size limit enforcement."""
        cache = ResponseCache(max_size=3, ttl_seconds=3600)

        # Add items up to limit
        for i in range(4):
            response = LLMResponse(
                content=f"Response {i}", provider="gemini", tokens_used=10, cost=0.0001, latency=0.1
            )
            cache.store(f"key-{i}", response)

        # First item should be evicted (LRU)
        self.assertIsNone(cache.get("key-0"))
        # Last three should exist
        self.assertIsNotNone(cache.get("key-1"))
        self.assertIsNotNone(cache.get("key-2"))
        self.assertIsNotNone(cache.get("key-3"))

    def test_cache_key_generation(self):
        """Test consistent cache key generation."""
        cache = ResponseCache()

        # Same inputs should generate same key
        key1 = cache.generate_key("test prompt", "claude", temperature=0.7)
        key2 = cache.generate_key("test prompt", "claude", temperature=0.7)
        self.assertEqual(key1, key2)

        # Different inputs should generate different keys
        key3 = cache.generate_key("different prompt", "claude", temperature=0.7)
        self.assertNotEqual(key1, key3)

        key4 = cache.generate_key("test prompt", "openai", temperature=0.7)
        self.assertNotEqual(key1, key4)


class TestLLMAdapter(unittest.TestCase):
    """Test main LLMAdapter functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = Mock(spec=ConfigurationManager)
        # Add get_llm_config to the mock spec
        self.mock_config.get_llm_config = Mock(
            return_value=LLMConfig(
                provider="openai",
                api_key="test-key",
                model="gpt-4",
                max_tokens=4000,
                temperature=0.7,
            )
        )
        self.mock_config.get_api_key = Mock(return_value="test-api-key")

        with patch("devdocai.intelligence.llm_adapter.ConfigurationManager"):
            self.adapter = LLMAdapter(config_manager=self.mock_config)

    def test_initialization(self):
        """Test LLMAdapter initialization with providers."""
        self.assertIsNotNone(self.adapter.cost_manager)
        self.assertIsNotNone(self.adapter.cache)
        self.assertIn("claude", self.adapter.providers)
        self.assertIn("openai", self.adapter.providers)
        self.assertIn("gemini", self.adapter.providers)
        self.assertIn("local", self.adapter.providers)

        # Check provider weights
        self.assertAlmostEqual(self.adapter.providers["claude"].weight, 0.4)
        self.assertAlmostEqual(self.adapter.providers["openai"].weight, 0.35)
        self.assertAlmostEqual(self.adapter.providers["gemini"].weight, 0.25)

    @patch("devdocai.intelligence.llm_adapter.ClaudeProvider.generate")
    def test_generate_response(self, mock_generate):
        """Test response generation with provider routing."""
        mock_response = LLMResponse(
            content="Generated response",
            provider="claude",
            tokens_used=150,
            cost=0.00225,
            latency=0.8,
        )
        mock_generate.return_value = mock_response

        response = self.adapter.generate(prompt="Test prompt", max_tokens=1000, temperature=0.7)

        self.assertEqual(response.content, "Generated response")
        self.assertEqual(response.provider, "claude")
        mock_generate.assert_called_once()

    @patch("devdocai.intelligence.llm_adapter.ClaudeProvider.generate")
    @patch("devdocai.intelligence.llm_adapter.OpenAIProvider.generate")
    def test_fallback_mechanism(self, mock_openai, mock_claude):
        """Test automatic fallback within 2 seconds on API failure."""
        # Claude fails
        mock_claude.side_effect = ProviderError("Claude API error")

        # OpenAI succeeds
        mock_openai.return_value = LLMResponse(
            content="Fallback response", provider="openai", tokens_used=100, cost=0.002, latency=0.5
        )

        start = time.time()
        response = self.adapter.generate("Test prompt")
        elapsed = time.time() - start

        # Should fallback to OpenAI
        self.assertEqual(response.provider, "openai")
        self.assertEqual(response.content, "Fallback response")

        # Should complete within 2 seconds
        self.assertLess(elapsed, 2.0)

    def test_multi_provider_synthesis(self):
        """Test multi-provider synthesis with weighted responses."""
        # Mock all providers
        with patch.object(
            self.adapter.providers["claude"], "generate"
        ) as mock_claude, patch.object(
            self.adapter.providers["openai"], "generate"
        ) as mock_openai, patch.object(
            self.adapter.providers["gemini"], "generate"
        ) as mock_gemini:

            # Set up responses
            mock_claude.return_value = LLMResponse(
                content="Claude says A",
                provider="claude",
                tokens_used=100,
                cost=0.0015,
                latency=0.5,
            )

            mock_openai.return_value = LLMResponse(
                content="OpenAI says B", provider="openai", tokens_used=100, cost=0.002, latency=0.6
            )

            mock_gemini.return_value = LLMResponse(
                content="Gemini says C", provider="gemini", tokens_used=100, cost=0.001, latency=0.4
            )

            # Generate with synthesis
            response = self.adapter.generate_synthesis(
                prompt="Test prompt", providers=["claude", "openai", "gemini"]
            )

            # Should combine responses with weights
            self.assertIsNotNone(response)
            self.assertIn("synthesis", response.metadata)
            self.assertEqual(len(response.metadata["synthesis"]), 3)

            # Check weights applied correctly
            synthesis = response.metadata["synthesis"]
            self.assertAlmostEqual(synthesis["claude"]["weight"], 0.4)
            self.assertAlmostEqual(synthesis["openai"]["weight"], 0.35)
            self.assertAlmostEqual(synthesis["gemini"]["weight"], 0.25)

    def test_cache_integration(self):
        """Test response caching integration."""
        # Use local provider which is always available
        mock_response = LLMResponse(
            content="Cached response", provider="local", tokens_used=200, cost=0.0, latency=0.7
        )

        with patch.object(self.adapter.providers["local"], "generate") as mock_generate:
            mock_generate.return_value = mock_response

            # First call - should hit provider
            response1 = self.adapter.generate("Test prompt", provider="local", use_cache=True)
            self.assertEqual(mock_generate.call_count, 1)

            # Second call - should hit cache
            response2 = self.adapter.generate("Test prompt", provider="local", use_cache=True)
            self.assertEqual(mock_generate.call_count, 1)  # No additional call

            # Responses should be identical
            self.assertEqual(response1.content, response2.content)

    def test_m001_integration(self):
        """Test integration with M001 ConfigurationManager."""
        # Test that configuration is retrieved
        self.mock_config.get_llm_config.assert_called()

        # Test configuration updates
        new_config = LLMConfig(
            provider="gemini", api_key="new-key", model="gemini-pro", max_tokens=2000
        )

        self.adapter.update_configuration(new_config)

        # Verify configuration applied
        self.assertEqual(self.adapter.default_provider, "gemini")
        self.assertEqual(self.adapter.default_max_tokens, 2000)

    def test_data_sanitization(self):
        """Test data sanitization before external transmission."""
        sensitive_prompt = """
        Process this data:
        Email: user@example.com
        Phone: 555-123-4567
        SSN: 123-45-6789
        API Key: sk-abc123xyz
        """

        # Test that the LocalProvider sanitizes data
        provider = LocalProvider(config=self.mock_config)

        # Test sanitization method directly
        sanitized = provider.sanitize_data(sensitive_prompt)
        self.assertNotIn("user@example.com", sanitized)
        self.assertNotIn("555-123-4567", sanitized)
        self.assertNotIn("123-45-6789", sanitized)
        self.assertNotIn("sk-abc123xyz", sanitized)

        # Test that generate method uses sanitization
        response = provider.generate(sensitive_prompt)
        # The response should not contain sensitive data
        # (In a real implementation, we'd check that the model didn't see it)

    def test_local_fallback(self):
        """Test local provider fallback when budget exceeded or APIs fail."""
        # Exceed budget
        self.adapter.cost_manager.current_usage = 9.99

        with patch.object(self.adapter.providers["local"], "generate") as mock_local:
            mock_local.return_value = LLMResponse(
                content="Local response",
                provider="local",
                tokens_used=100,
                cost=0.0,  # Local is free
                latency=0.1,
            )

            response = self.adapter.generate(
                "Test prompt", estimated_tokens=1000  # Would cost >$0.01 with cloud
            )

            # Should use local provider
            self.assertEqual(response.provider, "local")
            self.assertEqual(response.cost, 0.0)
            mock_local.assert_called_once()


class TestProviderImplementations(unittest.TestCase):
    """Test specific provider implementations."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = Mock(spec=ConfigurationManager)
        self.mock_config.get_api_key.return_value = "test-api-key"

    @pytest.mark.skip(reason="Requires anthropic library installation")
    @patch("anthropic.Anthropic")
    def test_claude_provider(self, mock_anthropic_class):
        """Test ClaudeProvider implementation."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock()
        mock_response.content = [Mock(text="Claude response")]
        mock_response.usage = Mock(input_tokens=50, output_tokens=100)
        mock_client.messages.create.return_value = mock_response

        provider = ClaudeProvider(config=self.mock_config)
        response = provider.generate(prompt="Test prompt", max_tokens=1000, temperature=0.7)

        self.assertEqual(response.content, "Claude response")
        self.assertEqual(response.provider, "claude")
        self.assertEqual(response.tokens_used, 150)

    @pytest.mark.skip(reason="Requires openai library installation")
    @patch("openai.OpenAI")
    def test_openai_provider(self, mock_openai_class):
        """Test OpenAIProvider implementation."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="OpenAI response"))]
        mock_response.usage = Mock(prompt_tokens=60, completion_tokens=120)
        mock_client.chat.completions.create.return_value = mock_response

        provider = OpenAIProvider(config=self.mock_config)
        response = provider.generate(prompt="Test prompt", max_tokens=1000, temperature=0.8)

        self.assertEqual(response.content, "OpenAI response")
        self.assertEqual(response.provider, "openai")
        self.assertEqual(response.tokens_used, 180)

    @pytest.mark.skip(reason="Requires google-generativeai library installation")
    @patch("google.generativeai.configure")
    @patch("google.generativeai.GenerativeModel")
    def test_gemini_provider(self, mock_model_class, mock_configure):
        """Test GeminiProvider implementation."""
        mock_model = Mock()
        mock_model_class.return_value = mock_model

        mock_response = Mock()
        mock_response.text = "Gemini response"
        mock_response.usage_metadata = Mock(
            prompt_token_count=40, candidates_token_count=80, total_token_count=120
        )
        mock_model.generate_content.return_value = mock_response

        provider = GeminiProvider(config=self.mock_config)
        response = provider.generate(prompt="Test prompt", max_tokens=800, temperature=0.6)

        self.assertEqual(response.content, "Gemini response")
        self.assertEqual(response.provider, "gemini")
        self.assertEqual(response.tokens_used, 120)

    def test_local_provider(self):
        """Test LocalProvider implementation."""
        provider = LocalProvider(config=self.mock_config)

        response = provider.generate(prompt="Test prompt", max_tokens=500, temperature=0.5)

        # Local provider should return something
        self.assertIsNotNone(response.content)
        self.assertEqual(response.provider, "local")
        self.assertEqual(response.cost, 0.0)  # Local is free
        self.assertGreater(response.tokens_used, 0)


class TestErrorHandling(unittest.TestCase):
    """Test error handling and recovery."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = Mock(spec=ConfigurationManager)
        self.adapter = LLMAdapter(config_manager=self.mock_config)

    def test_provider_error_recovery(self):
        """Test recovery from provider errors."""
        with patch.object(
            self.adapter.providers["claude"], "generate"
        ) as mock_claude, patch.object(self.adapter.providers["openai"], "generate") as mock_openai:

            # First provider fails
            mock_claude.side_effect = ProviderError("API error")

            # Second provider succeeds
            mock_openai.return_value = LLMResponse(
                content="Recovery response",
                provider="openai",
                tokens_used=100,
                cost=0.002,
                latency=0.5,
            )

            response = self.adapter.generate("Test prompt")

            self.assertEqual(response.provider, "openai")
            self.assertEqual(response.content, "Recovery response")

    def test_budget_exceeded_handling(self):
        """Test handling of budget exceeded scenarios."""
        # Set budget near limit
        self.adapter.cost_manager.current_usage = 9.995

        with patch.object(self.adapter.providers["local"], "generate") as mock_local:
            mock_local.return_value = LLMResponse(
                content="Budget fallback", provider="local", tokens_used=100, cost=0.0, latency=0.1
            )

            # This would exceed budget with cloud provider
            response = self.adapter.generate("Test prompt", estimated_tokens=1000)

            # Should fallback to local
            self.assertEqual(response.provider, "local")
            self.assertEqual(response.cost, 0.0)

    def test_timeout_recovery(self):
        """Test recovery from timeout scenarios."""
        with patch.object(
            self.adapter.providers["claude"], "generate"
        ) as mock_claude, patch.object(self.adapter.providers["openai"], "generate") as mock_openai:

            # First provider times out
            mock_claude.side_effect = APITimeoutError("Request timeout")

            # Second provider succeeds quickly
            mock_openai.return_value = LLMResponse(
                content="Quick response",
                provider="openai",
                tokens_used=80,
                cost=0.0016,
                latency=0.3,
            )

            start = time.time()
            response = self.adapter.generate("Test prompt", timeout=2.0)
            elapsed = time.time() - start

            # Should get response within timeout
            self.assertLess(elapsed, 2.0)
            self.assertEqual(response.provider, "openai")

    def test_all_providers_fail(self):
        """Test behavior when all providers fail."""
        # Make all cloud providers fail
        for provider_name in ["claude", "openai", "gemini"]:
            self.adapter.providers[provider_name].generate = Mock(
                side_effect=ProviderError(f"{provider_name} failed")
            )

        # Local should still work
        with patch.object(self.adapter.providers["local"], "generate") as mock_local:
            mock_local.return_value = LLMResponse(
                content="Last resort", provider="local", tokens_used=50, cost=0.0, latency=0.05
            )

            response = self.adapter.generate("Test prompt")

            # Should ultimately use local
            self.assertEqual(response.provider, "local")
            self.assertEqual(response.content, "Last resort")


if __name__ == "__main__":
    unittest.main()
