"""
M008: Google Provider Implementation.

Provider for Google's Gemini models including Gemini Pro and Gemini Pro Vision.
Adapts Google's AI Platform API to the standard LLM interface.
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


class GoogleProvider(BaseProvider):
    """Google Gemini API provider implementation."""
    
    def __init__(self, config: 'ProviderConfig'):
        """Initialize Google provider."""
        super().__init__(config)
        
        if not config.api_key and not config.api_key_encrypted:
            raise ValueError("Google API key is required")
        
        # Set default models if not configured
        if not self.config.available_models:
            self.config.available_models = [
                "gemini-pro",
                "gemini-pro-vision",
                "gemini-1.5-pro",
                "gemini-1.5-flash"
            ]
        
        # Default cost rates (as of 2024, subject to change)
        self._model_costs = {
            "gemini-pro": {
                "input": Decimal("0.0005"),
                "output": Decimal("0.0015")
            },
            "gemini-pro-vision": {
                "input": Decimal("0.0005"),
                "output": Decimal("0.0015")
            },
            "gemini-1.5-pro": {
                "input": Decimal("0.0035"),
                "output": Decimal("0.0105")
            },
            "gemini-1.5-flash": {
                "input": Decimal("0.00035"),
                "output": Decimal("0.0014")
            },
        }
        
        # Set base URL if not provided
        if not self.config.base_url:
            self.config.base_url = "https://generativelanguage.googleapis.com/v1beta"
    
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate completion using Google Gemini API."""
        await self.check_rate_limits()
        
        # Prepare request for Google format
        api_request = self._prepare_request(request)
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Make API call
            async with aiohttp.ClientSession() as session:
                model = request.model if request.model in self.config.available_models else self.config.default_model
                url = f"{self.config.base_url}/models/{model}:generateContent"
                
                params = {"key": self._get_api_key()}
                
                async with session.post(
                    url,
                    params=params,
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
            
            # Extract content from Google response
            content = ""
            candidates = data.get("candidates", [])
            if candidates and len(candidates) > 0:
                candidate = candidates[0]
                content_parts = candidate.get("content", {}).get("parts", [])
                if content_parts:
                    content = content_parts[0].get("text", "")
            
            # Google doesn't provide token counts in basic response
            # Estimate based on content length
            estimated_input_tokens = len(str(request.messages)) // 4
            estimated_output_tokens = len(content) // 4
            
            usage = TokenUsage(
                prompt_tokens=estimated_input_tokens,
                completion_tokens=estimated_output_tokens,
                total_tokens=estimated_input_tokens + estimated_output_tokens
            )
            
            # Calculate costs using model-specific rates
            usage = self._calculate_model_cost(request.model, usage)
            
            # Determine finish reason
            finish_reason = "stop"
            if candidates:
                finish_reason = candidates[0].get("finishReason", "stop").lower()
            
            # Create response
            llm_response = LLMResponse(
                content=content,
                finish_reason=finish_reason,
                model=request.model,
                provider=self.provider_name,
                usage=usage,
                request_id=request.request_id,
                response_time_ms=response_time,
                metadata={
                    "google_response": data
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
        """Generate streaming completion using Google Gemini API."""
        # Note: Google Gemini streaming implementation would go here
        # For Pass 1, we'll implement a simple version that chunks the response
        
        response = await self.generate(request)
        
        # Simple chunking for streaming simulation
        content = response.content
        chunk_size = 50  # Characters per chunk
        
        for i in range(0, len(content), chunk_size):
            chunk = content[i:i + chunk_size]
            is_final = i + chunk_size >= len(content)
            
            yield LLMResponse(
                content=chunk,
                finish_reason="stop" if is_final else "",
                model=response.model,
                provider=self.provider_name,
                usage=response.usage if is_final else TokenUsage(
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0
                ),
                request_id=request.request_id,
                response_time_ms=response.response_time_ms if is_final else 0,
                metadata={
                    "streaming": True,
                    "partial": not is_final
                }
            )
            
            if not is_final:
                await asyncio.sleep(0.01)  # Small delay between chunks
    
    async def validate_connection(self) -> bool:
        """Validate Google API connection."""
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
        estimated_input_tokens = len(str(request.messages)) // 4
        estimated_output_tokens = min(request.max_tokens or 1000, 1000)
        
        model_cost = self._model_costs.get(request.model, {
            "input": self.config.input_cost_per_1k,
            "output": self.config.output_cost_per_1k
        })
        
        input_cost = Decimal(str(estimated_input_tokens)) / 1000 * model_cost["input"]
        output_cost = Decimal(str(estimated_output_tokens)) / 1000 * model_cost["output"]
        
        return input_cost + output_cost
    
    def get_available_models(self) -> List[str]:
        """Get available Google models."""
        return self.config.available_models
    
    def _get_api_key(self) -> str:
        """Get decrypted API key."""
        if self.config.api_key:
            return self.config.api_key
        
        # TODO: Implement decryption using M001 ConfigurationManager
        # For now, assume key is in environment
        import os
        key = os.getenv("GOOGLE_API_KEY")
        if not key:
            raise AuthenticationError(
                "Google API key not found", self.provider_name
            )
        return key
    
    def _prepare_request(self, request: LLMRequest) -> Dict[str, Any]:
        """Prepare request for Google Gemini API format."""
        # Convert OpenAI format to Google format
        contents = []
        
        for message in request.messages:
            role = "user" if message["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": message["content"]}]
            })
        
        api_request = {
            "contents": contents,
            "generationConfig": {
                "temperature": request.temperature,
                "candidateCount": 1,
            }
        }
        
        if request.max_tokens:
            api_request["generationConfig"]["maxOutputTokens"] = request.max_tokens
        
        if request.top_p is not None:
            api_request["generationConfig"]["topP"] = request.top_p
            
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