"""
M008: Main LLM Adapter Implementation.

Unified interface for multi-provider LLM access with cost tracking,
fallback support, and integration with other DevDocAI modules.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union, AsyncGenerator
from decimal import Decimal

from .config import LLMConfig, ProviderConfig, ProviderType
from .providers.base import BaseProvider, LLMRequest, LLMResponse
from .providers.openai import OpenAIProvider
from .providers.anthropic import AnthropicProvider
from .providers.google import GoogleProvider
from .providers.local import LocalProvider
from .cost_tracker import CostTracker, UsageRecord, CostAlert
from .fallback_manager import FallbackManager, FallbackAttempt
from .integrations import MIAIRIntegration, ConfigIntegration, QualityAnalyzer

logger = logging.getLogger(__name__)


class LLMAdapter:
    """
    Main LLM Adapter for DevDocAI.
    
    Provides unified access to multiple LLM providers with:
    - Multi-provider support (OpenAI, Anthropic, Google, Local)
    - Cost tracking and budget management
    - Intelligent fallback handling
    - Multi-LLM synthesis for quality improvement
    - Integration with MIAIR Engine and other modules
    - Performance optimization with caching and async support
    """
    
    def __init__(self, config: LLMConfig):
        """
        Initialize LLM Adapter.
        
        Args:
            config: LLM adapter configuration
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.LLMAdapter")
        
        # Initialize integrations
        self.config_integration = ConfigIntegration()
        
        # Decrypt API keys if needed
        if self.config.encryption_enabled:
            self.config.providers = self.config_integration.decrypt_provider_keys(
                self.config.providers
            )
        
        # Initialize providers
        self.providers: Dict[str, BaseProvider] = {}
        self._initialize_providers()
        
        # Initialize cost tracking
        if self.config.cost_tracking_enabled:
            self.cost_tracker = CostTracker(self.config.cost_limits)
        else:
            self.cost_tracker = None
        
        # Initialize fallback manager
        self.fallback_manager = FallbackManager(
            providers=self.providers,
            fallback_strategy=self.config.fallback_strategy
        )
        
        # Initialize MIAIR integration
        self.miair_integration = None
        if self.config.miair_integration_enabled:
            self.miair_integration = MIAIRIntegration(self)
        
        # Initialize quality analyzer (fallback for MIAIR)
        self.quality_analyzer = QualityAnalyzer(self)
        
        # Request cache (simple in-memory cache)
        self._response_cache: Dict[str, LLMResponse] = {}
        
        self.logger.info(
            f"LLM Adapter initialized with {len(self.providers)} providers: "
            f"{', '.join(self.providers.keys())}"
        )
    
    def _initialize_providers(self) -> None:
        """Initialize all configured providers."""
        provider_classes = {
            ProviderType.OPENAI: OpenAIProvider,
            ProviderType.ANTHROPIC: AnthropicProvider,
            ProviderType.GOOGLE: GoogleProvider,
            ProviderType.LOCAL: LocalProvider,
        }
        
        for name, config in self.config.providers.items():
            if not config.enabled:
                continue
            
            try:
                provider_class = provider_classes.get(config.provider_type)
                if not provider_class:
                    self.logger.error(f"Unknown provider type: {config.provider_type}")
                    continue
                
                provider = provider_class(config)
                self.providers[name] = provider
                self.logger.info(f"Initialized {config.provider_type.value} provider: {name}")
                
            except Exception as e:
                self.logger.error(f"Failed to initialize provider {name}: {e}")
    
    async def generate(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        model: Optional[str] = None,
        provider: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate text completion using the best available provider.
        
        Args:
            prompt: Text prompt or message list
            model: Specific model to use
            provider: Preferred provider name
            **kwargs: Additional generation parameters
            
        Returns:
            LLM response
            
        Raises:
            ValueError: Invalid parameters
            ProviderError: All providers failed
        """
        # Prepare request
        request = self._prepare_request(prompt, model, **kwargs)
        
        # Check budget if cost tracking enabled
        if self.cost_tracker:
            estimated_cost = self._estimate_request_cost(request, provider)
            can_afford, reason = self.cost_tracker.can_afford_request(estimated_cost)
            
            if not can_afford:
                raise ValueError(f"Budget exceeded: {reason}")
        
        # Execute with fallback support
        response, attempts = await self.fallback_manager.execute_with_fallback(
            request, provider, self._estimate_provider_cost
        )
        
        # Record usage for cost tracking
        if self.cost_tracker:
            usage_record = UsageRecord(
                timestamp=response.created_at,
                provider=response.provider,
                model=response.model,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                input_cost=response.usage.prompt_cost,
                output_cost=response.usage.completion_cost,
                total_cost=response.usage.total_cost,
                request_id=response.request_id,
                response_time_seconds=response.response_time_ms / 1000,
                success=True
            )
            
            alerts = await self.cost_tracker.record_usage(usage_record)
            if alerts:
                self._handle_cost_alerts(alerts)
        
        return response
    
    async def generate_stream(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        model: Optional[str] = None,
        provider: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[LLMResponse, None]:
        """
        Generate streaming text completion.
        
        Args:
            prompt: Text prompt or message list
            model: Specific model to use
            provider: Preferred provider name
            **kwargs: Additional generation parameters
            
        Yields:
            Partial LLM responses
        """
        # Prepare request
        request = self._prepare_request(prompt, model, stream=True, **kwargs)
        
        # Get provider (use first available if not specified)
        provider_name = provider or self.config.get_provider_by_priority()[0]
        llm_provider = self.providers.get(provider_name)
        
        if not llm_provider:
            raise ValueError(f"Provider '{provider_name}' not available")
        
        # Check budget
        if self.cost_tracker:
            estimated_cost = self._estimate_request_cost(request, provider_name)
            can_afford, reason = self.cost_tracker.can_afford_request(estimated_cost)
            
            if not can_afford:
                raise ValueError(f"Budget exceeded: {reason}")
        
        # Generate streaming response
        async for chunk in llm_provider.generate_stream(request):
            yield chunk
    
    async def synthesize(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        providers: Optional[List[str]] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate content using multiple providers for quality synthesis.
        
        Args:
            prompt: Text prompt or message list
            providers: List of providers to use (max 3)
            model: Model to use across providers
            **kwargs: Additional generation parameters
            
        Returns:
            Dictionary with synthesized response and individual results
        """
        if not self.config.synthesis.enabled:
            # Fall back to single provider
            response = await self.generate(prompt, model, **kwargs)
            return {
                "synthesized_response": response,
                "individual_responses": [response],
                "consensus_score": 1.0,
                "quality_improvement": 0.0,
                "total_cost": response.usage.total_cost
            }
        
        # Select providers for synthesis
        synthesis_providers = providers or self.config.get_provider_by_priority()
        synthesis_providers = synthesis_providers[:self.config.synthesis.max_providers]
        
        if len(synthesis_providers) < 2:
            self.logger.warning("Need at least 2 providers for synthesis, falling back to single")
            response = await self.generate(prompt, model, **kwargs)
            return {
                "synthesized_response": response,
                "individual_responses": [response],
                "consensus_score": 1.0,
                "quality_improvement": 0.0,
                "total_cost": response.usage.total_cost
            }
        
        # Generate responses from multiple providers
        tasks = []
        for provider_name in synthesis_providers:
            task = self._generate_with_provider(prompt, model, provider_name, **kwargs)
            tasks.append(task)
        
        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful responses
        successful_responses = []
        total_cost = Decimal("0")
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.warning(f"Provider {synthesis_providers[i]} failed: {result}")
            else:
                successful_responses.append(result)
                total_cost += result.usage.total_cost
        
        if not successful_responses:
            raise ValueError("All providers failed during synthesis")
        
        # Synthesize responses based on strategy
        if self.config.synthesis.strategy == "consensus":
            synthesized = await self._synthesize_consensus(successful_responses)
        elif self.config.synthesis.strategy == "best_of_n":
            synthesized = await self._synthesize_best_of_n(successful_responses)
        else:  # weighted_average
            synthesized = await self._synthesize_weighted_average(successful_responses)
        
        return {
            "synthesized_response": synthesized,
            "individual_responses": successful_responses,
            "consensus_score": self._calculate_consensus_score(successful_responses),
            "quality_improvement": 0.2,  # Placeholder - would be calculated
            "total_cost": total_cost,
            "providers_used": [r.provider for r in successful_responses]
        }
    
    async def analyze_quality(
        self,
        content: str,
        content_type: str = "documentation"
    ) -> Dict[str, Any]:
        """
        Analyze content quality using MIAIR or LLM-based analysis.
        
        Args:
            content: Content to analyze
            content_type: Type of content
            
        Returns:
            Quality analysis results
        """
        if self.miair_integration:
            return await self.miair_integration.analyze_content_quality(content)
        else:
            return await self.quality_analyzer.analyze_quality(content, content_type)
    
    async def enhance_content(
        self,
        content: str,
        target_quality: float = 0.85,
        max_iterations: int = 3
    ) -> Dict[str, Any]:
        """
        Enhance content quality using MIAIR optimization.
        
        Args:
            content: Content to enhance
            target_quality: Target quality score
            max_iterations: Maximum enhancement iterations
            
        Returns:
            Enhancement results with improved content
        """
        if self.miair_integration:
            return await self.miair_integration.enhance_document(
                content, target_quality, max_iterations
            )
        else:
            # Basic enhancement using quality analyzer
            quality = await self.quality_analyzer.analyze_quality(content)
            
            if quality.get("overall_score", 0) >= target_quality:
                return {
                    "enhanced_content": content,
                    "quality_score": quality.get("overall_score", 0),
                    "improvement": 0,
                    "message": "Content already meets target quality"
                }
            
            # Single enhancement pass
            enhanced = await self._enhance_content_basic(content, quality)
            new_quality = await self.quality_analyzer.analyze_quality(enhanced)
            
            return {
                "enhanced_content": enhanced,
                "quality_score": new_quality.get("overall_score", 0),
                "initial_quality": quality.get("overall_score", 0),
                "improvement": new_quality.get("overall_score", 0) - quality.get("overall_score", 0),
                "iterations": 1
            }
    
    async def get_usage_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get usage statistics and cost information."""
        if not self.cost_tracker:
            return {"error": "Cost tracking not enabled"}
        
        stats = self.cost_tracker.get_usage_stats(days)
        provider_health = self.fallback_manager.get_provider_health_status()
        
        return {
            "usage_stats": {
                "total_requests": stats.total_requests,
                "total_tokens": stats.total_tokens,
                "total_cost": str(stats.total_cost),
                "daily_costs": {k: str(v) for k, v in stats.daily_costs.items()},
                "provider_breakdown": {
                    k: {
                        "requests": v["requests"],
                        "tokens": v["tokens"],
                        "cost": str(v["cost"])
                    } for k, v in stats.provider_breakdown.items()
                }
            },
            "provider_health": provider_health,
            "cost_limits": {
                "daily_limit": str(self.config.cost_limits.daily_limit_usd),
                "monthly_limit": str(self.config.cost_limits.monthly_limit_usd),
                "daily_spent": str(self.cost_tracker.get_daily_cost()),
                "monthly_spent": str(self.cost_tracker.get_monthly_cost())
            },
            "period_days": days
        }
    
    def _prepare_request(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        model: Optional[str] = None,
        **kwargs
    ) -> LLMRequest:
        """Prepare standardized LLM request."""
        # Convert prompt to message format
        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        else:
            messages = prompt
        
        # Get default model from first provider if not specified
        if not model:
            first_provider = list(self.providers.values())[0]
            model = first_provider.config.default_model
        
        return LLMRequest(
            messages=messages,
            model=model,
            **kwargs
        )
    
    def _estimate_request_cost(
        self,
        request: LLMRequest,
        provider_name: Optional[str] = None
    ) -> Decimal:
        """Estimate cost for a request."""
        if provider_name and provider_name in self.providers:
            return self.providers[provider_name].estimate_cost(request)
        
        # Use average cost across all providers
        costs = []
        for provider in self.providers.values():
            costs.append(provider.estimate_cost(request))
        
        return sum(costs) / len(costs) if costs else Decimal("0.01")
    
    def _estimate_provider_cost(self, provider_name: str, request: LLMRequest) -> float:
        """Estimate cost for specific provider (for fallback manager)."""
        if provider_name in self.providers:
            return float(self.providers[provider_name].estimate_cost(request))
        return 0.01
    
    async def _generate_with_provider(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        model: Optional[str],
        provider_name: str,
        **kwargs
    ) -> LLMResponse:
        """Generate response using specific provider."""
        request = self._prepare_request(prompt, model, **kwargs)
        provider = self.providers[provider_name]
        return await provider.generate(request)
    
    async def _synthesize_consensus(self, responses: List[LLMResponse]) -> LLMResponse:
        """Synthesize responses using consensus strategy."""
        # For now, return the longest response as a simple consensus
        # In a full implementation, this would analyze content similarity
        longest_response = max(responses, key=lambda r: len(r.content))
        
        # Create new response with consensus metadata
        consensus_response = LLMResponse(
            content=longest_response.content,
            finish_reason=longest_response.finish_reason,
            model=f"consensus-{longest_response.model}",
            provider="consensus",
            usage=longest_response.usage,
            request_id=longest_response.request_id,
            response_time_ms=sum(r.response_time_ms for r in responses) / len(responses),
            metadata={
                "synthesis_strategy": "consensus",
                "source_responses": len(responses),
                "providers_used": [r.provider for r in responses]
            }
        )
        
        return consensus_response
    
    async def _synthesize_best_of_n(self, responses: List[LLMResponse]) -> LLMResponse:
        """Synthesize responses using best-of-n strategy."""
        # Analyze quality of each response and pick the best
        best_response = responses[0]
        best_quality = 0.0
        
        for response in responses:
            try:
                quality = await self.quality_analyzer.analyze_quality(
                    response.content, "generated_text"
                )
                if quality.get("overall_score", 0) > best_quality:
                    best_quality = quality.get("overall_score", 0)
                    best_response = response
            except Exception as e:
                self.logger.warning(f"Quality analysis failed for response: {e}")
        
        # Create new response with best-of-n metadata
        return LLMResponse(
            content=best_response.content,
            finish_reason=best_response.finish_reason,
            model=f"best-of-{len(responses)}-{best_response.model}",
            provider="best_of_n",
            usage=best_response.usage,
            request_id=best_response.request_id,
            response_time_ms=best_response.response_time_ms,
            quality_score=best_quality,
            metadata={
                "synthesis_strategy": "best_of_n",
                "candidates": len(responses),
                "selected_provider": best_response.provider,
                "quality_score": best_quality
            }
        )
    
    async def _synthesize_weighted_average(self, responses: List[LLMResponse]) -> LLMResponse:
        """Synthesize responses using weighted average (placeholder implementation)."""
        # For now, just return consensus - full implementation would weight by quality
        return await self._synthesize_consensus(responses)
    
    def _calculate_consensus_score(self, responses: List[LLMResponse]) -> float:
        """Calculate consensus score between responses."""
        # Simplified implementation - would use semantic similarity in practice
        if len(responses) < 2:
            return 1.0
        
        # Basic length-based similarity (placeholder)
        lengths = [len(r.content) for r in responses]
        avg_length = sum(lengths) / len(lengths)
        variance = sum((l - avg_length) ** 2 for l in lengths) / len(lengths)
        
        # Convert variance to similarity score (0-1)
        return max(0.0, 1.0 - (variance / (avg_length ** 2)) if avg_length > 0 else 0.0)
    
    async def _enhance_content_basic(self, content: str, quality: Dict[str, Any]) -> str:
        """Basic content enhancement using single LLM."""
        prompt = f"""Please improve the following content based on the quality analysis:

Quality Scores:
- Readability: {quality.get('readability', 0.5):.2f}
- Completeness: {quality.get('completeness', 0.5):.2f}
- Clarity: {quality.get('clarity', 0.5):.2f}
- Structure: {quality.get('structure', 0.5):.2f}

Content to improve:
{content}

Please return an improved version that addresses the lowest-scoring areas while maintaining the core message."""
        
        try:
            response = await self.generate(prompt, temperature=0.2)
            return response.content
        except Exception as e:
            self.logger.error(f"Basic enhancement failed: {e}")
            return content  # Return original if enhancement fails
    
    def _handle_cost_alerts(self, alerts: List[CostAlert]) -> None:
        """Handle cost alerts (log warnings, could send notifications)."""
        for alert in alerts:
            if alert.alert_type == "emergency":
                self.logger.error(f"COST EMERGENCY: {alert.message}")
            else:
                self.logger.warning(f"Cost Alert: {alert.message}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Close provider connections if needed
        for provider in self.providers.values():
            try:
                await provider.__aexit__(exc_type, exc_val, exc_tb)
            except Exception as e:
                self.logger.warning(f"Error closing provider: {e}")