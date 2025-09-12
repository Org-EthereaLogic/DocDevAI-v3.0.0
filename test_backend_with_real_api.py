#!/usr/bin/env python3
"""
Backend API Testing Script with Real API Keys
Tests the core DevDocAI backend functionality with real LLM integration.
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from devdocai.core.config import ConfigurationManager
from devdocai.intelligence.llm_adapter import LLMAdapter
from devdocai.core.generator import DocumentGenerator
from devdocai.intelligence.miair import MIAIREngine
from devdocai.intelligence.enhance import EnhancementPipeline


async def test_configuration():
    """Test configuration loading and API key setup."""
    print("🔧 Testing Configuration...")
    
    config = ConfigurationManager()
    
    # Check if API key is configured
    api_key = config.llm.api_key
    if api_key == "your_api_key_here":
        print("❌ API key not configured. Please update .devdocai.yml with your real API key.")
        return False
    
    print(f"✅ Configuration loaded successfully")
    print(f"   - Provider: {config.llm.provider}")
    print(f"   - Model: {config.llm.model}")
    print(f"   - API key configured: {'Yes' if len(api_key) > 10 else 'No'}")
    print(f"   - Privacy mode: {config.privacy_mode}")
    
    return True


async def test_llm_adapter():
    """Test LLM Adapter with real API calls."""
    print("\n🤖 Testing LLM Adapter...")
    
    config = ConfigurationManager()
    adapter = LLMAdapter(config)
    
    try:
        # Simple test prompt
        response = await adapter.generate(
            prompt="Write a simple 2-line README description for a Python documentation tool called DevDocAI.",
            max_tokens=100
        )
        
        print("✅ LLM Adapter working correctly")
        print(f"   - Response length: {len(response)} characters")
        print(f"   - Sample response: {response[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ LLM Adapter failed: {e}")
        return False


async def test_document_generator():
    """Test Document Generator with AI-powered generation."""
    print("\n📄 Testing Document Generator...")
    
    config = ConfigurationManager()
    generator = DocumentGenerator(config)
    
    try:
        # Test document generation
        context = {
            "project_name": "TestProject",
            "description": "A test project for backend validation",
            "author": "DevDocAI Test Suite"
        }
        
        document = await generator.generate_document(
            template_name="readme",
            context=context
        )
        
        print("✅ Document Generator working correctly")
        print(f"   - Generated document length: {len(document.content)} characters")
        print(f"   - Document type: {document.type}")
        print(f"   - Has AI-generated content: {'Yes' if 'TestProject' in document.content else 'No'}")
        
        # Save test document for visual inspection
        with open("test_generated_readme.md", "w") as f:
            f.write(document.content)
        print("   - Test document saved as: test_generated_readme.md")
        
        return True
        
    except Exception as e:
        print(f"❌ Document Generator failed: {e}")
        return False


async def test_miair_engine():
    """Test MIAIR Engine for document optimization."""
    print("\n🧠 Testing MIAIR Engine...")
    
    config = ConfigurationManager()
    engine = MIAIREngine(config)
    
    try:
        # Test document optimization
        test_content = """
        # Test Document
        
        This is a test document with some content.
        It has multiple sentences and paragraphs.
        
        ## Section 1
        Some information here.
        
        ## Section 2  
        More information here.
        """
        
        optimized = await engine.optimize_document(test_content)
        
        print("✅ MIAIR Engine working correctly")
        print(f"   - Original length: {len(test_content)} characters")
        print(f"   - Optimized length: {len(optimized.content)} characters")
        print(f"   - Quality score: {optimized.quality_score:.2f}")
        print(f"   - Entropy reduction: {optimized.entropy_reduction:.2f}%")
        
        return True
        
    except Exception as e:
        print(f"❌ MIAIR Engine failed: {e}")
        return False


async def test_enhancement_pipeline():
    """Test Enhancement Pipeline for AI-powered improvements."""
    print("\n✨ Testing Enhancement Pipeline...")
    
    config = ConfigurationManager()
    pipeline = EnhancementPipeline(config)
    
    try:
        # Test document enhancement
        test_content = "# Simple Test\n\nThis is a basic document that needs enhancement."
        
        enhanced = await pipeline.enhance_document(test_content)
        
        print("✅ Enhancement Pipeline working correctly")
        print(f"   - Original length: {len(test_content)} characters")
        print(f"   - Enhanced length: {len(enhanced.content)} characters")
        print(f"   - Quality improvement: {enhanced.quality_improvement:.1f}%")
        print(f"   - Strategy used: {enhanced.strategy}")
        
        return True
        
    except Exception as e:
        print(f"❌ Enhancement Pipeline failed: {e}")
        return False


async def main():
    """Run comprehensive backend tests."""
    print("🚀 DevDocAI Backend Testing with Real API Keys")
    print("=" * 60)
    
    tests = [
        ("Configuration", test_configuration),
        ("LLM Adapter", test_llm_adapter),
        ("Document Generator", test_document_generator),
        ("MIAIR Engine", test_miair_engine),
        ("Enhancement Pipeline", test_enhancement_pipeline)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All backend tests passed! The system is ready for frontend integration.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please check the configuration and API keys.")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)