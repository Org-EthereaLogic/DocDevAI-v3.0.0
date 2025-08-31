"""
M008: LLM Adapter - Multi-provider AI integration layer for DevDocAI.

REFACTORED (Pass 4): Achieved ~40% code reduction through unified architecture.

This module provides a unified interface for interacting with multiple LLM providers
including OpenAI, Anthropic, Google, and local models. Features include:

- Multi-provider support with provider abstraction
- Cost tracking and budget management ($10 daily/$200 monthly limits)
- Fallback chains for reliability
- Multi-LLM synthesis for quality improvement
- Secure API key management using M001 encryption patterns
- Integration with M003 MIAIR Engine for AI-powered refinement
- Async/await support for performance (<2s simple, <10s complex)
- NEW: Unified adapter with operation modes (BASIC, PERFORMANCE, SECURE, ENTERPRISE)

Performance targets:
- Simple requests: <2 seconds response time
- Complex multi-LLM synthesis: <10 seconds
- Cost tracking accuracy: 99.9%
- Support for concurrent requests

Usage:
    from devdocai.llm_adapter import UnifiedLLMAdapter, OperationMode
    
    # New unified adapter with operation modes
    adapter = UnifiedLLMAdapter(config, OperationMode.ENTERPRISE)
    
    # Or use factory function
    from devdocai.llm_adapter import create_adapter
    adapter = create_adapter(config, mode="performance")
    
    # Simple request
    response = await adapter.query({"messages": [...]})
    
    # Multi-provider synthesis
    response = await adapter.synthesize(
        request, 
        providers=['openai', 'anthropic']
    )
"""

# Unified adapter (NEW - Pass 4 refactoring)
try:
    from .adapter_unified import (
        UnifiedLLMAdapter,
        OperationMode,
        UnifiedConfig,
        create_adapter
    )
    UNIFIED_AVAILABLE = True
except ImportError:
    UNIFIED_AVAILABLE = False

# Legacy adapters (maintained for backward compatibility)
from .adapter import LLMAdapter
try:
    from .adapter_optimized import OptimizedLLMAdapter
except ImportError:
    OptimizedLLMAdapter = None
try:
    from .adapter_secure import SecureLLMAdapter
except ImportError:
    SecureLLMAdapter = None

# Configuration
from .config import LLMConfig, ProviderConfig, ProviderType, CostLimits, FallbackStrategy
from .cost_tracker import CostTracker, UsageStats
from .fallback_manager import FallbackManager
from .integrations import MIAIRIntegration

# Unified providers (NEW - Pass 4 refactoring)
try:
    from .providers.provider_unified import UnifiedProviderBase
    from .providers.openai_unified import OpenAIProviderUnified
    from .providers.anthropic_unified import AnthropicProviderUnified
    UNIFIED_PROVIDERS_AVAILABLE = True
except ImportError:
    UNIFIED_PROVIDERS_AVAILABLE = False

# Legacy providers (maintained for backward compatibility)
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

# Add unified components if available
if UNIFIED_AVAILABLE:
    __all__.extend([
        'UnifiedLLMAdapter',
        'OperationMode',
        'UnifiedConfig',
        'create_adapter',
    ])
    
if UNIFIED_PROVIDERS_AVAILABLE:
    __all__.extend([
        'UnifiedProviderBase',
        'OpenAIProviderUnified',
        'AnthropicProviderUnified',
    ])

# Add optimized/secure adapters if available
if OptimizedLLMAdapter:
    __all__.append('OptimizedLLMAdapter')
if SecureLLMAdapter:
    __all__.append('SecureLLMAdapter')

__version__ = "2.0.0"  # Bumped for unified refactoring