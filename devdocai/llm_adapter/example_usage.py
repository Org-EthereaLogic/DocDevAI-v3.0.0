"""
M008 LLM Adapter Usage Examples.

Demonstrates how to use the LLM Adapter for various scenarios including
basic generation, multi-provider synthesis, cost tracking, and content enhancement.
"""

import asyncio
import logging
from decimal import Decimal
from pathlib import Path

from devdocai.llm_adapter import (
    LLMAdapter, LLMConfig, ProviderConfig, ProviderType,
    CostLimits, FallbackStrategy
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def basic_usage_example():
    """Example of basic LLM Adapter usage."""
    print("\n=== Basic Usage Example ===")
    
    # Configure providers
    providers = {
        "openai": ProviderConfig(
            provider_type=ProviderType.OPENAI,
            api_key="your-openai-api-key",  # Replace with actual key
            enabled=True,
            priority=8
        ),
        "anthropic": ProviderConfig(
            provider_type=ProviderType.ANTHROPIC,
            api_key="your-anthropic-api-key",  # Replace with actual key
            enabled=True,
            priority=7
        ),
        "local": ProviderConfig(
            provider_type=ProviderType.LOCAL,
            enabled=False,  # Disabled for this example
            base_url="http://localhost:11434"
        )
    }
    
    # Configure cost limits
    cost_limits = CostLimits(
        daily_limit_usd=Decimal("10.00"),
        monthly_limit_usd=Decimal("200.00"),
        per_request_limit_usd=Decimal("5.00")
    )
    
    # Create configuration
    config = LLMConfig(
        providers=providers,
        cost_limits=cost_limits,
        cost_tracking_enabled=True,
        fallback_enabled=True,
        fallback_strategy=FallbackStrategy.QUALITY_OPTIMIZED
    )
    
    # Initialize adapter
    async with LLMAdapter(config) as adapter:
        
        # Basic text generation
        response = await adapter.generate(
            "Write a brief introduction to artificial intelligence."
        )
        
        print(f"Response from {response.provider}:")
        print(f"Content: {response.content[:200]}...")
        print(f"Tokens: {response.usage.total_tokens}")
        print(f"Cost: ${response.usage.total_cost}")
        
        return adapter


async def multi_provider_synthesis_example():
    """Example of multi-provider synthesis for improved quality."""
    print("\n=== Multi-Provider Synthesis Example ===")
    
    # Use configuration from basic example
    providers = {
        "openai": ProviderConfig(
            provider_type=ProviderType.OPENAI,
            api_key="your-openai-api-key",
            priority=8,
            quality_score=0.85
        ),
        "anthropic": ProviderConfig(
            provider_type=ProviderType.ANTHROPIC,
            api_key="your-anthropic-api-key",
            priority=7,
            quality_score=0.90
        )
    }
    
    config = LLMConfig(
        providers=providers,
        synthesis={"enabled": True, "strategy": "best_of_n", "max_providers": 2}
    )
    
    async with LLMAdapter(config) as adapter:
        
        # Multi-provider synthesis
        result = await adapter.synthesize(
            "Explain the benefits and risks of artificial intelligence in healthcare.",
            providers=["openai", "anthropic"]
        )
        
        print(f"Synthesized response ({result['consensus_score']:.2f} consensus):")
        print(f"Content: {result['synthesized_response'].content[:300]}...")
        print(f"Providers used: {result['providers_used']}")
        print(f"Total cost: ${result['total_cost']}")
        print(f"Quality improvement: {result['quality_improvement']:.1%}")


async def cost_tracking_example():
    """Example of cost tracking and budget management."""
    print("\n=== Cost Tracking Example ===")
    
    # Set strict budget limits for demonstration
    cost_limits = CostLimits(
        daily_limit_usd=Decimal("1.00"),  # Low limit for demo
        monthly_limit_usd=Decimal("20.00"),
        per_request_limit_usd=Decimal("0.50"),
        daily_warning_threshold=0.7,
        emergency_stop_enabled=True
    )
    
    providers = {
        "openai": ProviderConfig(
            provider_type=ProviderType.OPENAI,
            api_key="your-openai-api-key"
        )
    }
    
    config = LLMConfig(
        providers=providers,
        cost_limits=cost_limits,
        cost_tracking_enabled=True
    )
    
    async with LLMAdapter(config) as adapter:
        
        # Generate multiple requests to demonstrate cost tracking
        requests = [
            "What is machine learning?",
            "Explain neural networks briefly.",
            "What are the types of AI algorithms?"
        ]
        
        for i, prompt in enumerate(requests, 1):
            try:
                print(f"\nRequest {i}: {prompt}")
                response = await adapter.generate(prompt)
                
                print(f"Response cost: ${response.usage.total_cost}")
                
                # Get current usage stats
                stats = await adapter.get_usage_stats(days=1)
                daily_spent = Decimal(stats["cost_limits"]["daily_spent"])
                daily_limit = Decimal(stats["cost_limits"]["daily_limit"])
                
                print(f"Daily usage: ${daily_spent} / ${daily_limit} ({daily_spent/daily_limit:.1%})")
                
            except ValueError as e:
                print(f"Budget limit reached: {e}")
                break
        
        # Show final usage statistics
        final_stats = await adapter.get_usage_stats(days=1)
        print(f"\nFinal daily usage: {final_stats['usage_stats']['total_requests']} requests")
        print(f"Total cost: ${final_stats['usage_stats']['total_cost']}")


async def content_enhancement_example():
    """Example of AI-powered content enhancement."""
    print("\n=== Content Enhancement Example ===")
    
    config = LLMConfig(
        providers={
            "openai": ProviderConfig(
                provider_type=ProviderType.OPENAI,
                api_key="your-openai-api-key"
            )
        },
        miair_integration_enabled=True,  # Enable MIAIR if available
        quality_analysis_enabled=True
    )
    
    async with LLMAdapter(config) as adapter:
        
        # Original content (deliberately poor quality)
        original_content = """
        AI is good. It helps with things. Companies use it for stuff. 
        It can be bad too. People worry about jobs.
        """
        
        print("Original content:")
        print(original_content)
        
        # Analyze quality
        quality_analysis = await adapter.analyze_quality(original_content)
        print(f"\nOriginal quality score: {quality_analysis['overall_score']:.2f}")
        print(f"- Readability: {quality_analysis['readability']:.2f}")
        print(f"- Completeness: {quality_analysis['completeness']:.2f}")
        print(f"- Clarity: {quality_analysis['clarity']:.2f}")
        
        # Enhance content
        enhancement_result = await adapter.enhance_content(
            original_content,
            target_quality=0.8,
            max_iterations=2
        )
        
        print(f"\nEnhanced content (quality: {enhancement_result['quality_score']:.2f}):")
        print(enhancement_result['enhanced_content'])
        print(f"\nQuality improvement: {enhancement_result['improvement']:+.2f}")
        print(f"Iterations: {enhancement_result['iterations']}")


async def fallback_handling_example():
    """Example of fallback handling when providers fail."""
    print("\n=== Fallback Handling Example ===")
    
    providers = {
        "primary": ProviderConfig(
            provider_type=ProviderType.OPENAI,
            api_key="invalid-key",  # Intentionally invalid
            priority=10,
            enabled=True
        ),
        "fallback": ProviderConfig(
            provider_type=ProviderType.ANTHROPIC,
            api_key="your-anthropic-api-key",
            priority=5,
            enabled=True
        ),
        "local": ProviderConfig(
            provider_type=ProviderType.LOCAL,
            priority=1,
            enabled=True  # Will be used as last resort
        )
    }
    
    config = LLMConfig(
        providers=providers,
        fallback_enabled=True,
        fallback_strategy=FallbackStrategy.SEQUENTIAL
    )
    
    async with LLMAdapter(config) as adapter:
        
        try:
            # This should fail with primary but succeed with fallback
            response = await adapter.generate(
                "What is the future of AI?",
                provider="primary"  # Request specific provider that will fail
            )
            
            print(f"Successful response from fallback provider: {response.provider}")
            print(f"Content: {response.content[:200]}...")
            
        except Exception as e:
            print(f"All providers failed: {e}")
        
        # Check provider health status
        stats = await adapter.get_usage_stats()
        health_status = stats["provider_health"]
        
        print("\nProvider Health Status:")
        for provider_name, status in health_status.items():
            health_indicator = "✅" if status["healthy"] else "❌"
            print(f"{health_indicator} {provider_name}: {status['circuit_state']}")


async def streaming_example():
    """Example of streaming text generation."""
    print("\n=== Streaming Example ===")
    
    config = LLMConfig(
        providers={
            "openai": ProviderConfig(
                provider_type=ProviderType.OPENAI,
                api_key="your-openai-api-key"
            )
        }
    )
    
    async with LLMAdapter(config) as adapter:
        
        print("Streaming response:")
        
        async for chunk in adapter.generate_stream(
            "Write a step-by-step guide to getting started with machine learning."
        ):
            if chunk.content:  # Only print non-empty chunks
                print(chunk.content, end="", flush=True)
        
        print("\n\nStreaming complete!")


def configuration_examples():
    """Examples of different configuration patterns."""
    print("\n=== Configuration Examples ===")
    
    # Cost-optimized configuration
    cost_optimized = LLMConfig(
        providers={
            "openai": ProviderConfig(
                provider_type=ProviderType.OPENAI,
                api_key="key",
                input_cost_per_1k=Decimal("0.0005"),
                output_cost_per_1k=Decimal("0.0015")
            )
        },
        fallback_strategy=FallbackStrategy.COST_OPTIMIZED,
        cost_limits=CostLimits(daily_limit_usd=Decimal("5.00"))
    )
    print("✅ Cost-optimized configuration created")
    
    # Quality-focused configuration
    quality_focused = LLMConfig(
        providers={
            "openai": ProviderConfig(
                provider_type=ProviderType.OPENAI,
                api_key="key",
                quality_score=0.85,
                priority=5
            ),
            "anthropic": ProviderConfig(
                provider_type=ProviderType.ANTHROPIC,
                api_key="key",
                quality_score=0.90,
                priority=8
            )
        },
        fallback_strategy=FallbackStrategy.QUALITY_OPTIMIZED,
        synthesis={"enabled": True, "strategy": "best_of_n"}
    )
    print("✅ Quality-focused configuration created")
    
    # Local-first configuration (privacy-focused)
    local_first = LLMConfig(
        providers={
            "local": ProviderConfig(
                provider_type=ProviderType.LOCAL,
                priority=10,
                base_url="http://localhost:11434"
            ),
            "openai": ProviderConfig(
                provider_type=ProviderType.OPENAI,
                api_key="key",
                priority=1  # Only as fallback
            )
        },
        cost_tracking_enabled=False,  # Local models are free
        encryption_enabled=True
    )
    print("✅ Local-first (privacy-focused) configuration created")


async def main():
    """Run all examples."""
    print("🤖 M008 LLM Adapter Usage Examples")
    print("=" * 50)
    
    # Configuration examples (no API calls)
    configuration_examples()
    
    # Note: The following examples require valid API keys
    # Uncomment and add your API keys to test
    
    print("\n📝 Note: The following examples require valid API keys.")
    print("Replace 'your-openai-api-key' and 'your-anthropic-api-key' with actual keys.\n")
    
    # await basic_usage_example()
    # await cost_tracking_example()
    # await fallback_handling_example()
    # await streaming_example()
    # await multi_provider_synthesis_example()
    # await content_enhancement_example()
    
    print("\n✅ Examples completed!")
    print("\nTo test with real API keys:")
    print("1. Replace placeholder API keys in the examples")
    print("2. Uncomment the example function calls")
    print("3. Run this script again")


if __name__ == "__main__":
    asyncio.run(main())