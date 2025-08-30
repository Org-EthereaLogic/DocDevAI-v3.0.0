"""
M008: LLM Adapter - Multi-provider AI integration layer for DevDocAI.

This module provides a unified interface for interacting with multiple LLM providers
including OpenAI, Anthropic, Google, and local models. Features include:

- Multi-provider support with provider abstraction
- Cost tracking and budget management ($10 daily/$200 monthly limits)
- Fallback chains for reliability
- Multi-LLM synthesis for quality improvement
- Secure API key management using M001 encryption patterns
- Integration with M003 MIAIR Engine for AI-powered refinement
- Async/await support for performance (<2s simple, <10s complex)

Performance targets:
- Simple requests: <2 seconds response time
- Complex multi-LLM synthesis: <10 seconds
- Cost tracking accuracy: 99.9%
- Support for concurrent requests

Usage:
    from devdocai.llm_adapter import LLMAdapter, LLMConfig
    
    config = LLMConfig(
        providers={'openai': {'api_key': 'sk-...'}}
    )
    adapter = LLMAdapter(config)
    
    # Simple request
    response = await adapter.generate("Write a README file")
    
    # Multi-provider synthesis
    response = await adapter.synthesize(
        prompt="Analyze this code", 
        providers=['openai', 'anthropic']
    )
"""

from .adapter import LLMAdapter
from .config import LLMConfig, ProviderConfig, ProviderType, CostLimits, FallbackStrategy
from .cost_tracker import CostTracker, UsageStats
from .fallback_manager import FallbackManager
from .integrations import MIAIRIntegration

# Provider imports
from .providers.base import BaseProvider, LLMRequest, LLMResponse
from .providers.openai import OpenAIProvider
from .providers.anthropic import AnthropicProvider
from .providers.google import GoogleProvider
from .providers.local import LocalProvider

__all__ = [
    # Core components
    'LLMAdapter',
    'LLMConfig', 
    'ProviderConfig',
    'CostLimits',
    'CostTracker',
    'UsageStats',
    'FallbackManager',
    'FallbackStrategy',
    'MIAIRIntegration',
    
    # Providers
    'BaseProvider',
    'LLMRequest',
    'LLMResponse', 
    'OpenAIProvider',
    'AnthropicProvider',
    'GoogleProvider',
    'LocalProvider',
]

__version__ = "1.0.0"