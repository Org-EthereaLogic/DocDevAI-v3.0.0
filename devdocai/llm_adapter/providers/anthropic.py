"""
M008: Anthropic Provider Implementation.

Provider for Anthropic's Claude models including Claude 3 Haiku, Sonnet, and Opus.
Adapts Claude's message format to the standard LLM interface.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, AsyncGenerator
from decimal import Decimal

import aiohttp

from .base import (
    BaseProvider, LLMRequest, LLMResponse, TokenUsage,
    ProviderError, RateLimitError, AuthenticationError, 
    QuotaExceededError, ModelNotFoundError
)

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseProvider):
    """Anthropic Claude API provider implementation."""
    
    def __init__(self, config: 'ProviderConfig'):
        """Initialize Anthropic provider."""
        super().__init__(config)
        
        if not config.api_key and not config.api_key_encrypted:
            raise ValueError("Anthropic API key is required")
        
        # Set default models if not configured
        if not self.config.available_models:
            self.config.available_models = [
                "claude-3-haiku-20240307",
                "claude-3-sonnet-20240229", 
                "claude-3-opus-20240229",
                "claude-3-5-sonnet-20241022"
            ]
        
        # Default cost rates (as of 2024, subject to change)
        self._model_costs = {
            "claude-3-haiku-20240307": {
                "input": Decimal("0.00025"),
                "output": Decimal("0.00125")
            },
            "claude-3-sonnet-20240229": {
                "input": Decimal("0.003"),
                "output": Decimal("0.015")
            },
            "claude-3-opus-20240229": {
                "input": Decimal("0.015"),
                "output": Decimal("0.075")
            },
            "claude-3-5-sonnet-20241022": {
                "input": Decimal("0.003"),
                "output": Decimal("0.015")
            },
        }
    
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate completion using Anthropic API."""
        await self.check_rate_limits()
        
        # Prepare request for Anthropic format
        api_request = self._prepare_request(request)
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Make API call
            async with aiohttp.ClientSession() as session:
                headers = {
                    "x-api-key": self._get_api_key(),
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
                
                url = f"{self.config.base_url}/messages"
                
                async with session.post(
                    url,
                    headers=headers,
                    json=api_request,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
                ) as response:
                    
                    if response.status == 401:
                        self.update_health_status(False)
                        raise AuthenticationError(
                            "Invalid API key", self.provider_name
                        )
                    elif response.status == 429:
                        self.update_health_status(False)
                        raise RateLimitError(
                            "Rate limit exceeded", self.provider_name
                        )
                    elif response.status == 400:
                        error_data = await response.json()
                        error_msg = error_data.get("error", {}).get("message", "")
                        if "model" in error_msg.lower():
                            raise ModelNotFoundError(
                                f"Model '{request.model}' not found", 
                                self.provider_name
                            )
                        raise ProviderError(
                            f"Bad request: {error_msg}", self.provider_name
                        )
                    elif response.status != 200:
                        error_data = await response.text()
                        self.update_health_status(False)
                        raise ProviderError(
                            f"API error {response.status}: {error_data}",
                            self.provider_name
                        )
                    
                    data = await response.json()
            
            # Process response
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            # Extract content from Claude response
            content = ""
            if data.get("content") and len(data["content"]) > 0:
                content = data["content"][0].get("text", "")
            
            usage_data = data.get("usage", {})
            
            # Create usage object
            usage = TokenUsage(
                prompt_tokens=usage_data.get("input_tokens", 0),
                completion_tokens=usage_data.get("output_tokens", 0),
                total_tokens=usage_data.get("input_tokens", 0) + usage_data.get("output_tokens", 0)
            )
            
            # Calculate costs using model-specific rates
            usage = self._calculate_model_cost(request.model, usage)
            
            # Create response
            llm_response = LLMResponse(
                content=content,
                finish_reason=data.get("stop_reason", "stop"),
                model=data.get("model", request.model),
                provider=self.provider_name,
                usage=usage,
                request_id=request.request_id,
                response_time_ms=response_time,
                metadata={
                    "anthropic_id": data.get("id"),
                    "type": data.get("type"),
                    "role": data.get("role")
                }
            )
            
            self.update_health_status(True)
            return llm_response
            
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            self.update_health_status(False, e)
            raise ProviderError(
                f"Network error: {str(e)}", self.provider_name
            ) from e
        except ProviderError:
            raise
        except Exception as e:
            self.update_health_status(False, e)
            raise ProviderError(
                f"Unexpected error: {str(e)}", self.provider_name
            ) from e
    
    async def generate_stream(
        self, 
        request: LLMRequest
    ) -> AsyncGenerator[LLMResponse, None]:
        """Generate streaming completion using Anthropic API."""
        await self.check_rate_limits()
        
        # Prepare streaming request
        api_request = self._prepare_request(request)
        api_request["stream"] = True
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "x-api-key": self._get_api_key(),
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
                
                url = f"{self.config.base_url}/messages"
                
                async with session.post(
                    url,
                    headers=headers,
                    json=api_request,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
                ) as response:
                    
                    if response.status != 200:
                        error_data = await response.text()
                        self.update_health_status(False)
                        raise ProviderError(
                            f"Streaming API error {response.status}: {error_data}",
                            self.provider_name
                        )
                    
                    # Process streaming response
                    accumulated_content = ""
                    
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        
                        if not line or not line.startswith("data: "):
                            continue
                        
                        try:
                            data = json.loads(line[6:])  # Remove "data: " prefix
                        except json.JSONDecodeError:
                            continue
                        
                        if data.get("type") == "content_block_delta":
                            # Partial content
                            delta_text = data.get("delta", {}).get("text", "")
                            if delta_text:
                                accumulated_content += delta_text
                                
                                yield LLMResponse(
                                    content=delta_text,
                                    finish_reason="",  # Not finished
                                    model=request.model,
                                    provider=self.provider_name,
                                    usage=TokenUsage(
                                        prompt_tokens=0,
                                        completion_tokens=0,
                                        total_tokens=0
                                    ),
                                    request_id=request.request_id,
                                    response_time_ms=0,
                                    metadata={
                                        "streaming": True,
                                        "partial": True
                                    }
                                )
                        
                        elif data.get("type") == "message_stop":
                            # Final response
                            response_time = (asyncio.get_event_loop().time() - start_time) * 1000
                            
                            usage = TokenUsage(
                                prompt_tokens=0,  # Not provided in streaming
                                completion_tokens=0,
                                total_tokens=0
                            )
                            
                            yield LLMResponse(
                                content=accumulated_content,
                                finish_reason="stop",
                                model=request.model,
                                provider=self.provider_name,
                                usage=usage,
                                request_id=request.request_id,
                                response_time_ms=response_time,
                                metadata={
                                    "streaming": True
                                }
                            )
                            break
            
            self.update_health_status(True)
            
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            self.update_health_status(False, e)
            raise ProviderError(
                f"Streaming network error: {str(e)}", self.provider_name
            ) from e
        except ProviderError:
            raise
        except Exception as e:
            self.update_health_status(False, e)
            raise ProviderError(
                f"Unexpected streaming error: {str(e)}", self.provider_name
            ) from e
    
    async def validate_connection(self) -> bool:
        """Validate Anthropic API connection."""
        try:
            # Simple API call to validate credentials
            test_request = LLMRequest(
                messages=[{"role": "user", "content": "Hello"}],
                model=self.config.default_model,
                max_tokens=5
            )
            
            await self.generate(test_request)
            return True
            
        except Exception as e:
            self.logger.warning(f"Connection validation failed: {e}")
            return False
    
    def estimate_cost(self, request: LLMRequest) -> Decimal:
        """Estimate cost for a request."""
        # Rough estimation based on prompt length
        estimated_input_tokens = len(str(request.messages)) // 4  # ~4 chars per token
        estimated_output_tokens = min(request.max_tokens or 1000, 1000)
        
        model_cost = self._model_costs.get(request.model, {
            "input": self.config.input_cost_per_1k,
            "output": self.config.output_cost_per_1k
        })
        
        input_cost = Decimal(str(estimated_input_tokens)) / 1000 * model_cost["input"]
        output_cost = Decimal(str(estimated_output_tokens)) / 1000 * model_cost["output"]
        
        return input_cost + output_cost
    
    def get_available_models(self) -> List[str]:
        """Get available Anthropic models."""
        return self.config.available_models
    
    def _get_api_key(self) -> str:
        """Get decrypted API key."""
        if self.config.api_key:
            return self.config.api_key
        
        # TODO: Implement decryption using M001 ConfigurationManager
        # For now, assume key is in environment
        import os
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise AuthenticationError(
                "Anthropic API key not found", self.provider_name
            )
        return key
    
    def _prepare_request(self, request: LLMRequest) -> Dict[str, Any]:
        """Prepare request for Anthropic API format."""
        # Convert OpenAI format to Anthropic format
        messages = request.messages.copy()
        system_prompt = None
        
        # Extract system message if present
        if messages and messages[0]["role"] == "system":
            system_prompt = messages[0]["content"]
            messages = messages[1:]
        elif request.system_prompt:
            system_prompt = request.system_prompt
        
        # Ensure model is available
        model = request.model
        if model not in self.config.available_models:
            model = self.config.default_model
            self.logger.warning(
                f"Model {request.model} not available, using {model}"
            )
        
        api_request = {
            "model": model,
            "messages": messages,
            "max_tokens": request.max_tokens or 1000,
            "temperature": request.temperature,
        }
        
        if system_prompt:
            api_request["system"] = system_prompt
        
        # Add optional parameters
        if request.top_p is not None:
            api_request["top_p"] = request.top_p
            
        return api_request
    
    def _calculate_model_cost(self, model: str, usage: TokenUsage) -> TokenUsage:
        """Calculate cost using model-specific rates."""
        model_cost = self._model_costs.get(model, {
            "input": self.config.input_cost_per_1k,
            "output": self.config.output_cost_per_1k
        })
        
        usage.prompt_cost = (
            Decimal(str(usage.prompt_tokens)) / 1000 * model_cost["input"]
        )
        usage.completion_cost = (
            Decimal(str(usage.completion_tokens)) / 1000 * model_cost["output"]
        )
        usage.total_cost = usage.prompt_cost + usage.completion_cost
        
        return usage