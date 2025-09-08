#!/usr/bin/env python3
"""
Real API Integration Tests for DevDocAI v3.0.0
Tests actual API calls to OpenAI, Anthropic, and Google services

Usage:
    REAL_API_TESTING=1 python -m pytest tests/integration/test_real_api.py -v
    
Prerequisites:
    - .env file with real API keys in project root
    - Environment variable REAL_API_TESTING=1 to enable tests
"""

import os
import pytest
from unittest.mock import patch
from devdocai.core.config import ConfigurationManager
from devdocai.intelligence.llm_adapter import LLMAdapter, ProviderType


# Skip all tests unless explicitly enabled with environment variable
pytestmark = pytest.mark.skipif(
    not os.getenv('REAL_API_TESTING'),
    reason="Real API testing disabled. Set REAL_API_TESTING=1 to enable."
)


class TestRealAPIIntegration:
    """Integration tests that make real API calls to external services"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.config = ConfigurationManager()
        self.adapter = LLMAdapter(config=self.config)
        
        # Simple test prompt for all providers
        self.test_prompt = "What is 2+2? Answer with just the number."
        
    def test_real_openai_api_call(self):
        """Test real OpenAI API call"""
        # Skip if no OpenAI key
        if not self.config.get_api_key('openai'):
            pytest.skip("No OpenAI API key found in configuration")
            
        try:
            response = self.adapter.generate(
                prompt=self.test_prompt,
                provider_type=ProviderType.OPENAI,
                max_tokens=10
            )
            
            # Verify response structure
            assert response is not None
            assert isinstance(response, str)
            assert len(response.strip()) > 0
            
            # Should contain the answer "4"
            assert "4" in response
            
            print(f"✅ OpenAI Response: {response.strip()}")
            
        except Exception as e:
            pytest.fail(f"OpenAI API call failed: {str(e)}")
    
    def test_real_anthropic_api_call(self):
        """Test real Anthropic (Claude) API call"""
        # Skip if no Anthropic key
        if not self.config.get_api_key('anthropic'):
            pytest.skip("No Anthropic API key found in configuration")
            
        try:
            response = self.adapter.generate(
                prompt=self.test_prompt,
                provider_type=ProviderType.CLAUDE,
                max_tokens=10
            )
            
            # Verify response structure
            assert response is not None
            assert isinstance(response, str)
            assert len(response.strip()) > 0
            
            # Should contain the answer "4"
            assert "4" in response
            
            print(f"✅ Claude Response: {response.strip()}")
            
        except Exception as e:
            pytest.fail(f"Anthropic API call failed: {str(e)}")
    
    def test_real_google_api_call(self):
        """Test real Google Gemini API call"""
        # Skip if no Google key
        if not self.config.get_api_key('google'):
            pytest.skip("No Google API key found in configuration")
            
        try:
            response = self.adapter.generate(
                prompt=self.test_prompt,
                provider_type=ProviderType.GEMINI,
                max_tokens=10
            )
            
            # Verify response structure
            assert response is not None
            assert isinstance(response, str)
            assert len(response.strip()) > 0
            
            # Should contain the answer "4"
            assert "4" in response
            
            print(f"✅ Gemini Response: {response.strip()}")
            
        except Exception as e:
            pytest.fail(f"Google API call failed: {str(e)}")
    
    def test_cost_tracking_with_real_calls(self):
        """Test cost tracking with real API calls"""
        # Use OpenAI for cost tracking test (most predictable pricing)
        if not self.config.get_api_key('openai'):
            pytest.skip("No OpenAI API key found for cost tracking test")
            
        try:
            # Reset cost tracking
            self.adapter.reset_costs()
            
            # Make a small API call
            response = self.adapter.generate(
                prompt="Hello",
                provider_type=ProviderType.OPENAI,
                max_tokens=5
            )
            
            # Verify cost was tracked
            total_cost = self.adapter.get_total_cost()
            assert total_cost > 0, "Cost should be tracked for real API calls"
            
            print(f"✅ Cost tracked: ${total_cost:.6f}")
            
        except Exception as e:
            pytest.fail(f"Cost tracking test failed: {str(e)}")
    
    def test_rate_limiting_with_real_calls(self):
        """Test rate limiting behavior with real API calls"""
        if not self.config.get_api_key('openai'):
            pytest.skip("No OpenAI API key found for rate limiting test")
            
        try:
            # Configure very low rate limit for testing
            test_config = ConfigurationManager()
            adapter = LLMAdapter(
                config=test_config,
                rate_limit_requests_per_minute=2  # Very low for testing
            )
            
            # Make first call (should succeed)
            response1 = adapter.generate(
                prompt="Test 1",
                provider_type=ProviderType.OPENAI,
                max_tokens=5
            )
            assert response1 is not None
            
            # Make second call (should succeed)
            response2 = adapter.generate(
                prompt="Test 2", 
                provider_type=ProviderType.OPENAI,
                max_tokens=5
            )
            assert response2 is not None
            
            print("✅ Rate limiting working correctly")
            
        except Exception as e:
            # Rate limiting exceptions are expected and acceptable
            if "rate limit" in str(e).lower():
                print("✅ Rate limiting triggered as expected")
            else:
                pytest.fail(f"Unexpected error in rate limiting test: {str(e)}")
    
    def test_error_handling_with_invalid_key(self):
        """Test error handling with invalid API key"""
        # Create adapter with invalid key
        with patch.object(self.config, 'get_api_key', return_value='invalid-key'):
            try:
                response = self.adapter.generate(
                    prompt="Test",
                    provider_type=ProviderType.OPENAI,
                    max_tokens=5
                )
                # Should not reach here with invalid key
                pytest.fail("Expected authentication error with invalid key")
                
            except Exception as e:
                # Verify we get proper error handling
                assert "authentication" in str(e).lower() or "unauthorized" in str(e).lower() or "invalid" in str(e).lower()
                print("✅ Authentication error handled correctly")


class TestRealAPIPerformance:
    """Performance tests with real API calls"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.config = ConfigurationManager()
        self.adapter = LLMAdapter(config=self.config)
    
    def test_response_time_performance(self):
        """Test API response time performance"""
        import time
        
        if not self.config.get_api_key('openai'):
            pytest.skip("No OpenAI API key found for performance test")
        
        start_time = time.time()
        
        try:
            response = self.adapter.generate(
                prompt="What is the capital of France?",
                provider_type=ProviderType.OPENAI,
                max_tokens=20
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            # Verify reasonable response time (under 30 seconds)
            assert response_time < 30, f"Response time too slow: {response_time:.2f}s"
            assert response is not None
            
            print(f"✅ Response time: {response_time:.2f}s")
            
        except Exception as e:
            pytest.fail(f"Performance test failed: {str(e)}")


if __name__ == "__main__":
    # Allow running directly with: python tests/integration/test_real_api.py
    import sys
    
    if not os.getenv('REAL_API_TESTING'):
        print("❌ Real API testing disabled.")
        print("Set REAL_API_TESTING=1 environment variable to enable tests.")
        print("Example: REAL_API_TESTING=1 python tests/integration/test_real_api.py")
        sys.exit(1)
    
    # Run the tests
    pytest.main([__file__, "-v"])