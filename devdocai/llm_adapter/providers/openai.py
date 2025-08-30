"""
M008: OpenAI Provider Implementation.

Provider for OpenAI's GPT models including GPT-3.5, GPT-4, and future models.
Supports both completion and chat completion APIs.
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


class OpenAIProvider(BaseProvider):
    """OpenAI API provider implementation."""
    
    def __init__(self, config: 'ProviderConfig'):
        """Initialize OpenAI provider."""
        super().__init__(config)
        
        if not config.api_key and not config.api_key_encrypted:
            raise ValueError("OpenAI API key is required")
        
        # Set default models if not configured
        if not self.config.available_models:
            self.config.available_models = [
                "gpt-3.5-turbo",
                "gpt-3.5-turbo-16k", 
                "gpt-4",
                "gpt-4-turbo",
                "gpt-4o",
                "gpt-4o-mini"
            ]
        
        # Default cost rates (as of 2024, subject to change)
        self._model_costs = {
            "gpt-3.5-turbo": {
                "input": Decimal("0.0005"), 
                "output": Decimal("0.0015")
            },
            "gpt-3.5-turbo-16k": {
                "input": Decimal("0.003"),
                "output": Decimal("0.004")
            },
            "gpt-4": {
                "input": Decimal("0.03"),
                "output": Decimal("0.06")
            },
            "gpt-4-turbo": {
                "input": Decimal("0.01"),
                "output": Decimal("0.03")
            },
            "gpt-4o": {
                "input": Decimal("0.005"),
                "output": Decimal("0.015")
            },
            "gpt-4o-mini": {
                "input": Decimal("0.00015"),
                "output": Decimal("0.0006")
            },
        }
    
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate completion using OpenAI API."""
        await self.check_rate_limits()
        
        # Prepare request
        api_request = self._prepare_request(request)
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Make API call
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self._get_api_key()}",
                    "Content-Type": "application/json"
                }
                
                if self.config.organization:
                    headers["OpenAI-Organization"] = self.config.organization
                
                url = f"{self.config.base_url}/chat/completions"
                
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
                        if "model" in error_data.get("error", {}).get("message", "").lower():
                            raise ModelNotFoundError(
                                f"Model '{request.model}' not found", 
                                self.provider_name
                            )
                        raise ProviderError(
                            f"Bad request: {error_data}", self.provider_name
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
            
            choice = data["choices"][0]
            usage_data = data.get("usage", {})
            
            # Create usage object
            usage = TokenUsage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0)
            )
            
            # Calculate costs using model-specific rates
            usage = self._calculate_model_cost(request.model, usage)
            
            # Create response
            llm_response = LLMResponse(
                content=choice["message"]["content"],
                finish_reason=choice["finish_reason"],
                model=data["model"],
                provider=self.provider_name,
                usage=usage,
                request_id=request.request_id,
                response_time_ms=response_time,
                tool_calls=choice["message"].get("tool_calls"),
                metadata={
                    "openai_id": data.get("id"),
                    "created": data.get("created"),
                    "system_fingerprint": data.get("system_fingerprint")
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
        """Generate streaming completion using OpenAI API."""
        await self.check_rate_limits()
        
        # Prepare streaming request
        api_request = self._prepare_request(request)
        api_request["stream"] = True
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self._get_api_key()}",
                    "Content-Type": "application/json"
                }
                
                if self.config.organization:
                    headers["OpenAI-Organization"] = self.config.organization
                
                url = f"{self.config.base_url}/chat/completions"
                
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
                        
                        if line == "data: [DONE]":
                            break
                        
                        try:
                            data = json.loads(line[6:])  # Remove "data: " prefix
                        except json.JSONDecodeError:
                            continue
                        
                        choice = data["choices"][0]
                        
                        if choice["finish_reason"]:
                            # Final response with usage info
                            response_time = (asyncio.get_event_loop().time() - start_time) * 1000
                            
                            usage = TokenUsage(
                                prompt_tokens=0,  # Not provided in streaming
                                completion_tokens=0,
                                total_tokens=0
                            )
                            
                            yield LLMResponse(
                                content=accumulated_content,
                                finish_reason=choice["finish_reason"],
                                model=data.get("model", request.model),
                                provider=self.provider_name,
                                usage=usage,
                                request_id=request.request_id,
                                response_time_ms=response_time,
                                metadata={
                                    "openai_id": data.get("id"),
                                    "streaming": True
                                }
                            )
                            break
                        
                        # Partial response
                        delta_content = choice["delta"].get("content", "")
                        if delta_content:
                            accumulated_content += delta_content
                            
                            yield LLMResponse(
                                content=delta_content,
                                finish_reason="",  # Not finished
                                model=data.get("model", request.model),
                                provider=self.provider_name,
                                usage=TokenUsage(
                                    prompt_tokens=0,
                                    completion_tokens=0, 
                                    total_tokens=0
                                ),
                                request_id=request.request_id,
                                response_time_ms=0,
                                metadata={
                                    "openai_id": data.get("id"),
                                    "streaming": True,
                                    "partial": True
                                }
                            )
            
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
        """Validate OpenAI API connection."""
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
        # This is approximate since we don't know exact token count
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
        """Get available OpenAI models."""
        return self.config.available_models
    
    def _get_api_key(self) -> str:
        """Get decrypted API key."""
        if self.config.api_key:
            return self.config.api_key
        
        # TODO: Implement decryption using M001 ConfigurationManager
        # For now, assume key is in environment
        import os
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise AuthenticationError(
                "OpenAI API key not found", self.provider_name
            )
        return key
    
    def _prepare_request(self, request: LLMRequest) -> Dict[str, Any]:
        """Prepare request for OpenAI API."""
        api_request = request.to_openai_format()
        
        # Ensure model is available
        if request.model not in self.config.available_models:
            api_request["model"] = self.config.default_model
            self.logger.warning(
                f"Model {request.model} not available, using {self.config.default_model}"
            )
        
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