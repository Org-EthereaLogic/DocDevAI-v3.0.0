#!/usr/bin/env python3
"""
Multi-Provider Backend Validation Script
Tests each LLM provider with its respective configuration file
"""

import asyncio
import os
import shutil
import sys

sys.path.insert(0, os.path.abspath("."))

from devdocai.core.config import ConfigurationManager
from devdocai.core.generator import DocumentGenerator
from devdocai.intelligence.llm_adapter import LLMAdapter


async def test_provider(provider_name, config_file):
    """Test a specific provider with its configuration file"""
    print(f"\n{'='*60}")
    print(f"🔄 Testing {provider_name.upper()} Provider")
    print(f"   Config: {config_file}")
    print(f"{'='*60}")

    try:
        # Backup current config
        current_config = ".devdocai.yml"
        backup_config = ".devdocai.yml.backup"

        if os.path.exists(current_config):
            shutil.copy(current_config, backup_config)

        # Copy provider-specific config
        shutil.copy(config_file, current_config)

        # Test 1: Configuration loading
        print("\n1. Testing Configuration...")
        config = ConfigurationManager()

        print(f"   ✅ Provider: {config.llm.provider}")
        print(f"   ✅ Model: {config.llm.model}")

        # Test 2: API key retrieval
        print("\n2. Testing API Key Retrieval...")
        api_key = config.get_api_key(config.llm.provider)

        if api_key is None:
            print(f"   ❌ No API key found for {config.llm.provider}")
            return False

        if "your_api_key_here" in str(api_key) or "sk-your-" in str(api_key):
            print(f"   ❌ Placeholder API key detected: {api_key[:20]}...")
            return False

        print(f"   ✅ API key loaded: {len(api_key)} chars")

        # Test 3: LLM Adapter initialization
        print("\n3. Testing LLM Adapter...")
        try:
            adapter = LLMAdapter(config)
            print(f"   ✅ LLM Adapter initialized for {config.llm.provider}")
        except Exception as e:
            print(f"   ❌ LLM Adapter failed: {e}")
            return False

        # Test 4: Simple AI generation
        print("\n4. Testing AI Generation...")
        try:
            response = await adapter.generate(
                prompt=f"Write exactly one line: 'DevDocAI {provider_name.title()} Test Successful'",
                max_tokens=50,
            )
            print(f"   ✅ AI Response: {response.strip()}")
        except Exception as e:
            print(f"   ❌ AI Generation failed: {e}")
            return False

        # Test 5: Document Generation
        print("\n5. Testing Document Generation...")
        try:
            generator = DocumentGenerator(config)
            context = {
                "project_name": f"TestProject_{provider_name.title()}",
                "description": f"Backend validation test using {provider_name}",
            }

            document = await generator.generate_document("readme", context)
            print(f"   ✅ Document generated: {len(document.content)} chars")

            # Save provider-specific test document
            test_file = f"test_document_{provider_name}.md"
            with open(test_file, "w") as f:
                f.write(document.content)
            print(f"   📄 Saved: {test_file}")

        except Exception as e:
            print(f"   ❌ Document Generation failed: {e}")
            return False

        print(f"\n🎉 {provider_name.upper()} PROVIDER TEST PASSED!")
        return True

    except Exception as e:
        print(f"\n❌ {provider_name.upper()} PROVIDER TEST FAILED: {e}")
        return False

    finally:
        # Restore original config
        if os.path.exists(backup_config):
            shutil.move(backup_config, current_config)
        elif os.path.exists(current_config):
            os.remove(current_config)


async def main():
    """Run comprehensive multi-provider backend validation"""
    print("🚀 DevDocAI Multi-Provider Backend Validation")
    print("=" * 60)

    # Provider configuration mapping
    providers = [
        ("openai", ".devdocai-openai.yml"),
        ("anthropic", ".devdocai-anthropic.yml"),
        ("gemini", ".devdocai-gemini.yml"),
    ]

    results = {}

    for provider_name, config_file in providers:
        if not os.path.exists(config_file):
            print(f"\n⚠️  Skipping {provider_name}: {config_file} not found")
            results[provider_name] = "SKIPPED"
            continue

        success = await test_provider(provider_name, config_file)
        results[provider_name] = "PASSED" if success else "FAILED"

    # Summary Report
    print("\n" + "=" * 60)
    print("📊 FINAL VALIDATION REPORT")
    print("=" * 60)

    all_passed = True
    for provider, result in results.items():
        status_emoji = "✅" if result == "PASSED" else "❌" if result == "FAILED" else "⚠️ "
        print(f"   {status_emoji} {provider.ljust(12)}: {result}")
        if result == "FAILED":
            all_passed = False

    if all_passed and any(r == "PASSED" for r in results.values()):
        print("\n🎉 BACKEND VALIDATION SUCCESSFUL!")
        print("   At least one provider working correctly")
        print("   Generated test documents saved for inspection")
        print("\n✅ Ready to build v3.6.0 frontend!")
        return 0
    else:
        print("\n⚠️  VALIDATION INCOMPLETE")
        print("   Please fix provider issues before building frontend")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
