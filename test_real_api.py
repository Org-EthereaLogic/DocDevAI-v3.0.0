#!/usr/bin/env python3
"""
Test script to use real API key directly, bypassing environment variables
"""

import sys
import logging
import os
sys.path.insert(0, '/Users/etherealogic/Dev/DocDevAI-v3.0.0')

from devdocai.core.config import ConfigurationManager
from devdocai.intelligence.llm_adapter import LLMAdapter, OpenAIProvider
from devdocai.core.generator import DocumentGenerator

# Enable debug logging
logging.basicConfig(level=logging.INFO)

def test_direct_api_call():
    """Test direct OpenAI API call with config file key"""
    print("=== Testing Direct API Call ===")
    
    # Clear environment variables temporarily
    old_openai_key = os.environ.get('OPENAI_API_KEY')
    if 'OPENAI_API_KEY' in os.environ:
        del os.environ['OPENAI_API_KEY']
    
    try:
        config = ConfigurationManager()
        
        # Verify we have the real API key from config file
        llm_config = config.get_llm_config()
        real_api_key = llm_config.api_key
        print(f"Config file API key: {real_api_key[:20]}... (length: {len(real_api_key)})")
        
        # Create a simple provider with the real API key
        from devdocai.intelligence.llm_adapter import openai
        if not openai:
            print("❌ OpenAI library not available")
            return
            
        # Create OpenAI client directly
        client = openai.OpenAI(api_key=real_api_key)
        
        print("Making direct OpenAI API call...")
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": "Respond with exactly: 'Real API call successful!'"}
            ],
            max_tokens=20,
            temperature=0.0
        )
        
        content = response.choices[0].message.content if response.choices else ""
        tokens = response.usage.prompt_tokens + response.usage.completion_tokens
        
        print(f"✅ Response: {content}")
        print(f"✅ Tokens used: {tokens}")
        
        if "Real API call successful" in content:
            print("🎉 SUCCESS: Real OpenAI API call worked!")
        else:
            print(f"⚠️ Got response but content unexpected: {content}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Restore environment variable if it existed
        if old_openai_key:
            os.environ['OPENAI_API_KEY'] = old_openai_key

def test_document_generation():
    """Test actual document generation with real API"""
    print("\n=== Testing Document Generation ===")
    
    # Clear environment variables temporarily
    old_openai_key = os.environ.get('OPENAI_API_KEY')
    if 'OPENAI_API_KEY' in os.environ:
        del os.environ['OPENAI_API_KEY']
    
    try:
        config = ConfigurationManager()
        
        # Force the real API key into the config
        real_api_key = config.get_llm_config().api_key
        
        # Create LLM adapter with forced config
        adapter = LLMAdapter(config)
        
        # Override the OpenAI provider to use the real key
        openai_provider = adapter.providers.get('openai')
        if openai_provider and hasattr(openai_provider, 'config'):
            # Force the provider to use the real key by updating its internal config
            openai_provider.config = config
        
        # Test document generation
        generator = DocumentGenerator(config, adapter)
        
        context = {
            'title': 'Real API Test Project',
            'description': 'Testing real OpenAI API integration',
            'features': ['Real AI generation', 'Proper API integration']
        }
        
        print("Generating README with real AI...")
        content = generator.generate('readme', context)
        
        print(f"Generated content length: {len(content)} characters")
        print("First 200 characters:")
        print(content[:200] + "..." if len(content) > 200 else content)
        
        if "Local fallback response" in content:
            print("❌ Still getting fallback response")
        elif len(content) > 500 and "Real API Test Project" in content:
            print("✅ SUCCESS: Real AI-generated documentation!")
        else:
            print("⚠️ Got response but might not be real AI content")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Restore environment variable if it existed
        if old_openai_key:
            os.environ['OPENAI_API_KEY'] = old_openai_key

if __name__ == "__main__":
    print("DevDocAI Real API Test")
    print("=" * 50)
    
    # Test 1: Direct API call
    test_direct_api_call()
    
    # Test 2: Document generation
    test_document_generation()
    
    print("\n" + "=" * 50)
    print("Real API test complete")