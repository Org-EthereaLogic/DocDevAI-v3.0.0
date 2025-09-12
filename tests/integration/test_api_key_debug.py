#!/usr/bin/env python3
"""
Debug script to test API key retrieval and OpenAI API calls
"""

import logging
import os
import sys

# Add devdocai to path
sys.path.insert(0, "/Users/etherealogic/Dev/DocDevAI-v3.0.0")

from devdocai.core.config import ConfigurationManager
from devdocai.intelligence.llm_adapter import LLMAdapter

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)


def test_config_retrieval():
    """Test configuration API key retrieval"""
    print("=== Testing Configuration Manager ===")

    config = ConfigurationManager()

    print(f"Config file exists: {config.config_file.exists()}")
    print(f"Config file path: {config.config_file}")

    # Test LLM config
    llm_config = config.get_llm_config()
    print(f"LLM provider: {llm_config.provider}")
    print(f"LLM model: {llm_config.model}")
    print(f"LLM max_tokens: {llm_config.max_tokens}")

    # Test API key retrieval for openai
    api_key = config.get_api_key("openai")
    print(f"API key for 'openai': {api_key[:20]}... (length: {len(api_key) if api_key else 0})")

    # Test environment variables
    env_key = os.getenv("OPENAI_API_KEY")
    print(
        f"OPENAI_API_KEY env var: {env_key[:20] if env_key else None}... (length: {len(env_key) if env_key else 0})"
    )

    return api_key


def test_llm_adapter():
    """Test LLM Adapter initialization and API key retrieval"""
    print("\n=== Testing LLM Adapter ===")

    try:
        adapter = LLMAdapter()
        print(f"Available providers: {list(adapter.providers.keys())}")
        print(f"Default provider: {adapter.default_provider}")

        # Test OpenAI provider specifically
        openai_provider = adapter.providers.get("openai")
        if openai_provider:
            print(f"OpenAI provider initialized: {type(openai_provider)}")
            print(f"OpenAI provider API key name: {openai_provider.api_key_name}")

            # Test API key retrieval
            try:
                api_key = openai_provider._get_api_key()
                print(f"OpenAI provider API key: {api_key[:20]}... (length: {len(api_key)})")
            except Exception as e:
                print(f"Error getting API key: {e}")
        else:
            print("OpenAI provider not found!")

    except Exception as e:
        print(f"Error initializing LLM Adapter: {e}")
        import traceback

        traceback.print_exc()


def test_actual_api_call():
    """Test actual OpenAI API call"""
    print("\n=== Testing Actual OpenAI API Call ===")

    try:
        adapter = LLMAdapter()

        # Force use openai provider with explicit timeout
        response = adapter.generate(
            prompt="Hello, please respond with exactly: 'API test successful'",
            provider="openai",
            max_tokens=50,
            temperature=0.0,
            timeout=30.0,
        )

        print(f"Response provider: {response.provider}")
        print(f"Response content: {response.content}")
        print(f"Response tokens: {response.tokens_used}")
        print(f"Response cost: ${response.cost}")
        print(f"Response cached: {response.cached}")

        # Check if it's a real response or fallback
        if "Local fallback response" in response.content:
            print("❌ Got fallback response instead of real API call!")
        elif "API test successful" in response.content:
            print("✅ Real OpenAI API call successful!")
        else:
            print("⚠️ Got response but content unexpected")

    except Exception as e:
        print(f"Error making API call: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    print("DevDocAI API Key Debug Test")
    print("=" * 50)

    # Test 1: Configuration retrieval
    api_key = test_config_retrieval()

    # Test 2: LLM Adapter
    test_llm_adapter()

    # Test 3: Actual API call
    if api_key:
        test_actual_api_call()
    else:
        print("\n❌ Skipping API call test - no API key found")

    print("\n" + "=" * 50)
    print("Debug test complete")
