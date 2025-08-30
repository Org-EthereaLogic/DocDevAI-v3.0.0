"""
M008: Local Provider Implementation.

Provider for local LLM models running via Ollama or similar local inference servers.
Supports local models for privacy-focused deployments.
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


class LocalProvider(BaseProvider):
    """Local model provider implementation (Ollama compatible)."""
    
    def __init__(self, config: 'ProviderConfig'):
        """Initialize Local provider."""
        super().__init__(config)
        
        # Set default models if not configured
        if not self.config.available_models:
            self.config.available_models = [
                "llama2",
                "llama2:13b",
                "codellama", 
                "mistral",
                "neural-chat"
            ]
        
        # Local models are free, but we track compute cost
        self._model_costs = {
            "llama2": {"input": Decimal("0"), "output": Decimal("0")},
            "llama2:13b": {"input": Decimal("0"), "output": Decimal("0")},
            "codellama": {"input": Decimal("0"), "output": Decimal("0")},
            "mistral": {"input": Decimal("0"), "output": Decimal("0")},
            "neural-chat": {"input": Decimal("0"), "output": Decimal("0")},
        }
        
        # Set default base URL for Ollama
        if not self.config.base_url:
            self.config.base_url = "http://localhost:11434"
    
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate completion using local model API."""
        await self.check_rate_limits()
        
        # Prepare request for Ollama format
        api_request = self._prepare_request(request)
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Make API call
            async with aiohttp.ClientSession() as session:
                url = f"{self.config.base_url}/api/generate"
                
                async with session.post(
                    url,
                    json=api_request,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
                ) as response:
                    
                    if response.status == 404:
                        raise ModelNotFoundError(
                            f"Model '{request.model}' not found locally", 
                            self.provider_name
                        )
                    elif response.status != 200:
                        error_data = await response.text()
                        self.update_health_status(False)
                        raise ProviderError(
                            f"Local API error {response.status}: {error_data}",
                            self.provider_name
                        )
                    
                    data = await response.json()
            
            # Process response
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            content = data.get("response", "")
            
            # Estimate token usage (local APIs may not provide exact counts)
            estimated_input_tokens = len(str(request.messages)) // 4
            estimated_output_tokens = len(content) // 4
            
            usage = TokenUsage(
                prompt_tokens=estimated_input_tokens,
                completion_tokens=estimated_output_tokens,
                total_tokens=estimated_input_tokens + estimated_output_tokens,
                prompt_cost=Decimal("0"),  # Local models are free
                completion_cost=Decimal("0"),
                total_cost=Decimal("0")
            )
            
            # Create response
            llm_response = LLMResponse(
                content=content,
                finish_reason="stop" if data.get("done", True) else "length",
                model=data.get("model", request.model),
                provider=self.provider_name,
                usage=usage,
                request_id=request.request_id,
                response_time_ms=response_time,
                metadata={
                    "local_response": data,
                    "eval_count": data.get("eval_count"),
                    "eval_duration": data.get("eval_duration"),
                    "prompt_eval_count": data.get("prompt_eval_count"),
                    "prompt_eval_duration": data.get("prompt_eval_duration"),
                }
            )
            
            self.update_health_status(True)
            return llm_response
            
        except aiohttp.ClientConnectorError as e:
            self.update_health_status(False, e)
            raise ProviderError(
                f"Cannot connect to local model server at {self.config.base_url}: {str(e)}",
                self.provider_name
            ) from e
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
        """Generate streaming completion using local model API."""
        await self.check_rate_limits()
        
        # Prepare streaming request
        api_request = self._prepare_request(request)
        api_request["stream"] = True
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.config.base_url}/api/generate"
                
                async with session.post(
                    url,
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
                        try:
                            data = json.loads(line.decode('utf-8'))
                        except json.JSONDecodeError:
                            continue
                        
                        content_chunk = data.get("response", "")
                        is_done = data.get("done", False)
                        
                        if content_chunk:
                            accumulated_content += content_chunk
                            
                            usage = TokenUsage(
                                prompt_tokens=0,
                                completion_tokens=0,
                                total_tokens=0,
                                total_cost=Decimal("0")
                            )
                            
                            yield LLMResponse(
                                content=content_chunk,
                                finish_reason="stop" if is_done else "",
                                model=data.get("model", request.model),
                                provider=self.provider_name,
                                usage=usage,
                                request_id=request.request_id,
                                response_time_ms=0 if not is_done else (
                                    (asyncio.get_event_loop().time() - start_time) * 1000
                                ),
                                metadata={
                                    "streaming": True,
                                    "partial": not is_done,
                                    "eval_count": data.get("eval_count") if is_done else None,
                                }
                            )
                        
                        if is_done:
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
        """Validate local model server connection."""
        try:
            # Check if server is running
            async with aiohttp.ClientSession() as session:
                url = f"{self.config.base_url}/api/tags"
                async with session.get(
                    url, 
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status == 200
                    
        except Exception as e:
            self.logger.warning(f"Connection validation failed: {e}")
            return False
    
    def estimate_cost(self, request: LLMRequest) -> Decimal:
        """Estimate cost for a request (free for local models)."""
        return Decimal("0")
    
    def get_available_models(self) -> List[str]:
        """Get available local models."""
        return self.config.available_models
    
    async def get_local_models(self) -> List[str]:
        """Get list of models available on the local server."""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.config.base_url}/api/tags"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [model["name"] for model in data.get("models", [])]
            return []
        except Exception as e:
            self.logger.warning(f"Failed to get local models: {e}")
            return []
    
    def _prepare_request(self, request: LLMRequest) -> Dict[str, Any]:
        """Prepare request for Ollama API format."""
        # Convert messages to prompt
        prompt = self._messages_to_prompt(request.messages)
        
        # Ensure model is available
        model = request.model
        if model not in self.config.available_models:
            model = self.config.default_model
            self.logger.warning(
                f"Model {request.model} not available, using {model}"
            )
        
        api_request = {
            "model": model,
            "prompt": prompt,
            "stream": False,  # Set to True for streaming
            "options": {
                "temperature": request.temperature,
            }
        }
        
        if request.max_tokens:
            api_request["options"]["num_predict"] = request.max_tokens
        
        if request.top_p is not None:
            api_request["options"]["top_p"] = request.top_p
            
        return api_request
    
    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Convert OpenAI message format to simple prompt."""
        prompt_parts = []
        
        for message in messages:
            role = message["role"]
            content = message["content"]
            
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"Human: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        prompt_parts.append("Assistant:")
        return "\n\n".join(prompt_parts)
    
    def _calculate_model_cost(self, model: str, usage: TokenUsage) -> TokenUsage:
        """Calculate cost (always $0 for local models)."""
        usage.prompt_cost = Decimal("0")
        usage.completion_cost = Decimal("0") 
        usage.total_cost = Decimal("0")
        return usage