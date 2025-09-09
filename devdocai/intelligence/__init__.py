"""
Intelligence Module - DevDocAI v3.0.0
M008: LLM Adapter and M009: Enhancement Pipeline AI Intelligence Components
"""

# M009: Enhancement Pipeline exports (Pass 2: Performance Optimized)
from .enhance import (
    ConsensusResult,
    EnhancementConfig,
    EnhancementPipeline,
    EnhancementRequest,
    EnhancementResponse,
    EnhancementResult,
    EnhancementStrategy,
    PerformanceMetrics,
)
from .llm_adapter import (
    APITimeoutError,
    BudgetExceededError,
    ClaudeProvider,
    CostManager,
    GeminiProvider,
    LLMAdapter,
    LLMResponse,
    LocalProvider,
    OpenAIProvider,
    Provider,
    ProviderError,
    ResponseCache,
)

__all__ = [
    # M008: LLM Adapter
    "LLMAdapter",
    "CostManager",
    "ResponseCache",
    "Provider",
    "ClaudeProvider",
    "OpenAIProvider",
    "GeminiProvider",
    "LocalProvider",
    "LLMResponse",
    "ProviderError",
    "BudgetExceededError",
    "APITimeoutError",
    # M009: Enhancement Pipeline (Pass 2)
    "EnhancementPipeline",
    "EnhancementStrategy",
    "EnhancementConfig",
    "EnhancementResult",
    "EnhancementRequest",
    "EnhancementResponse",
    "ConsensusResult",
    "PerformanceMetrics",
]
