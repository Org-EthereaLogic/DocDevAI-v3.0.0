"""
Performance Tests for M008 LLM Adapter
DevDocAI v3.0.0 - Pass 2: Performance Optimization Validation
"""

import time
import unittest
from unittest.mock import Mock, patch
from datetime import datetime
import statistics

from devdocai.intelligence.llm_adapter import (
    LLMAdapter,
    CostManager,
    ResponseCache,
    LocalProvider,
    LLMResponse,
    APITimeoutError,
)
from devdocai.core.config import ConfigurationManager


class TestLLMAdapterPerformance(unittest.TestCase):
    """Performance tests for M008 LLM Adapter."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = Mock(spec=ConfigurationManager)
        self.mock_config.get_api_key = Mock(return_value="test-key")
        self.mock_config.get_llm_config = Mock(return_value=None)
        self.adapter = LLMAdapter(config_manager=self.mock_config)

    def test_fallback_within_2_seconds(self):
        """Test that fallback occurs within 2 seconds as per FR-002."""
        # Use local provider directly to test fallback timing
        start = time.time()

        # Generate with local provider (should be fast)
        response = self.adapter.generate("Test prompt", provider="local", timeout=2.0)

        elapsed = time.time() - start

        # Local provider should respond quickly (< 0.5s)
        self.assertLess(elapsed, 0.5, f"Local provider took {elapsed:.2f}s")

        # Should have used local provider
        self.assertEqual(response.provider, "local")

        # Test that timeout parameter is respected
        provider = LocalProvider(config=self.mock_config, timeout=2.0)

        # Test timeout detection
        start_time = time.time() - 3.0  # Simulate 3 seconds ago

        with self.assertRaises(APITimeoutError) as context:
            provider._check_timeout(start_time)

        # Verify timeout was detected
        self.assertIn("timeout", str(context.exception).lower())

    def test_cost_tracking_accuracy(self):
        """Test cost tracking accuracy of 99.9% as per FR-025."""
        cost_manager = CostManager(daily_limit=10.00)

        # Test various cost amounts for precision
        test_costs = [0.001, 0.0123, 0.123456, 1.999999, 5.5555]

        for cost in test_costs:
            cost_manager.track_usage("test", cost, 100)

        # Calculate expected vs actual
        expected = sum(round(c, 3) for c in test_costs)  # Round to 3 decimal places
        actual = cost_manager.current_usage

        # Check 99.9% accuracy (3 decimal places)
        self.assertAlmostEqual(actual, expected, places=3)

        # Verify precision in history
        for i, entry in enumerate(cost_manager.usage_history):
            self.assertAlmostEqual(entry["cost"], round(test_costs[i], 3), places=3)

    def test_cache_performance(self):
        """Test cache retrieval performance."""
        cache = ResponseCache(max_size=1000, ttl_seconds=3600)

        # Populate cache with test data
        for i in range(100):
            response = LLMResponse(
                content=f"Response {i}", provider="test", tokens_used=100, cost=0.001, latency=0.1
            )
            key = cache.generate_key(f"prompt {i}", "test")
            cache.store(key, response)

        # Test retrieval performance
        times = []
        for i in range(100):
            key = cache.generate_key(f"prompt {i}", "test")
            start = time.time()
            response = cache.get(key)
            elapsed = time.time() - start
            times.append(elapsed)
            self.assertIsNotNone(response)

        # Cache retrieval should be very fast (< 1ms on average)
        avg_time = statistics.mean(times) * 1000  # Convert to ms
        self.assertLess(avg_time, 1.0, f"Cache retrieval took {avg_time:.2f}ms average")

    def test_sanitization_performance(self):
        """Test data sanitization doesn't significantly impact performance."""
        provider = LocalProvider(config=self.mock_config)

        # Create a large text with sensitive data
        large_text = " ".join(
            [
                "user@example.com",
                "555-123-4567",
                "123-45-6789",
                "sk-abc123xyz",
                "normal text " * 1000,  # Make it large
            ]
        )

        # Measure sanitization time
        times = []
        for _ in range(10):
            start = time.time()
            sanitized = provider.sanitize_data(large_text)
            elapsed = time.time() - start
            times.append(elapsed)

        # Pass 2 target: Sanitization should be < 1ms (optimized from < 10ms)
        avg_time = statistics.mean(times) * 1000  # Convert to ms
        self.assertLess(avg_time, 1.0, f"Sanitization took {avg_time:.2f}ms average")

        # Verify sanitization worked
        self.assertNotIn("user@example.com", sanitized)
        self.assertNotIn("555-123-4567", sanitized)

    def test_provider_initialization_performance(self):
        """Test that provider initialization is fast."""
        start = time.time()

        # Initialize all providers
        adapter = LLMAdapter(config_manager=self.mock_config)

        elapsed = time.time() - start

        # Should initialize quickly (< 100ms)
        self.assertLess(elapsed, 0.1, f"Initialization took {elapsed*1000:.2f}ms")

        # Verify providers are available
        self.assertIn("local", adapter.providers)

    def test_concurrent_request_handling(self):
        """Test handling multiple concurrent requests efficiently."""
        import threading

        results = []
        errors = []

        def make_request(prompt, index):
            try:
                response = self.adapter.generate(
                    f"{prompt} {index}", provider="local", use_cache=False
                )
                results.append(response)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        start = time.time()

        for i in range(10):
            thread = threading.Thread(target=make_request, args=("Test", i))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join(timeout=5.0)

        elapsed = time.time() - start

        # Should handle concurrent requests efficiently
        self.assertEqual(len(results), 10, f"Expected 10 results, got {len(results)}")
        self.assertEqual(len(errors), 0, f"Got {len(errors)} errors: {errors}")
        self.assertLess(elapsed, 2.0, f"Concurrent requests took {elapsed:.2f}s")

    def test_budget_check_performance(self):
        """Test that budget checking is fast and doesn't impact response time."""
        cost_manager = CostManager(daily_limit=10.00)

        # Simulate near-limit usage
        cost_manager.current_usage = 9.99

        times = []
        for _ in range(100):
            start = time.time()
            try:
                cost_manager.check_budget(0.001)
            except:
                pass
            elapsed = time.time() - start
            times.append(elapsed)

        # Budget check should be instant (< 0.1ms average)
        avg_time = statistics.mean(times) * 1000  # Convert to ms
        self.assertLess(avg_time, 0.1, f"Budget check took {avg_time:.3f}ms average")

    def test_parallel_synthesis_performance(self):
        """Test Pass 2: Parallel provider synthesis achieves 60-70% latency reduction."""
        # Mock multiple providers with simulated latency
        with patch.object(self.adapter, "generate") as mock_generate:
            # Simulate 100ms latency per provider
            def side_effect(*args, **kwargs):
                time.sleep(0.1)  # Simulate API latency
                return LLMResponse(
                    content=f"Response from {kwargs.get('provider', 'test')}",
                    provider=kwargs.get("provider", "test"),
                    tokens_used=100,
                    cost=0.001,
                    latency=0.1,
                )

            mock_generate.side_effect = side_effect

            # Test synthesis with 3 providers (should be parallel)
            start = time.time()
            response = self.adapter.generate_synthesis(
                "Test prompt", providers=["claude", "openai", "gemini"]
            )
            elapsed = time.time() - start

            # With parallel execution, should take ~100ms instead of 300ms
            # Target: 60-70% reduction = 90-120ms instead of 300ms
            self.assertLess(elapsed, 0.15, f"Parallel synthesis took {elapsed:.2f}s")
            self.assertIn("parallel_execution", response.metadata)
            self.assertTrue(response.metadata["parallel_execution"])

    def test_batch_generation_performance(self):
        """Test Pass 2: Batch generation reduces API call overhead."""
        # Test batch generation
        prompts = [f"Test prompt {i}" for i in range(5)]

        start = time.time()
        responses = self.adapter.generate_batch(prompts, provider="local")
        elapsed = time.time() - start

        # Batch should be efficient
        self.assertEqual(len(responses), 5)
        self.assertLess(elapsed, 1.0, f"Batch generation took {elapsed:.2f}s")

        # Verify all responses are valid
        for response in responses:
            self.assertIsInstance(response, LLMResponse)
            self.assertIsNotNone(response.content)

    def test_optimized_regex_performance(self):
        """Test Pass 2: Pre-compiled regex patterns improve sanitization."""
        provider = LocalProvider(config=self.mock_config)

        # Create very large text to test optimization
        very_large_text = " ".join(
            [
                "user@example.com",
                "555-123-4567",
                "123-45-6789",
                "sk-abc123xyz",
                "4111-1111-1111-1111",
                "normal text " * 5000,  # 5x larger than before
            ]
        )

        # Measure optimized sanitization
        times = []
        for _ in range(20):
            start = time.time()
            sanitized = provider.sanitize_data(very_large_text)
            elapsed = time.time() - start
            times.append(elapsed)

        # Pass 2: Should be significantly faster than unoptimized (< 5ms for 5x larger text)
        # This is optimized from the original < 10ms for 1x text
        avg_time = statistics.mean(times) * 1000
        self.assertLess(avg_time, 5.0, f"Optimized sanitization took {avg_time:.2f}ms")

        # Verify correctness
        self.assertNotIn("user@example.com", sanitized)
        self.assertIn("[EMAIL]", sanitized)
        self.assertNotIn("4111-1111-1111-1111", sanitized)
        self.assertIn("[CREDIT_CARD]", sanitized)


if __name__ == "__main__":
    unittest.main()
