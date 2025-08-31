"""
M008: Unified OpenAI Provider Implementation (Pass 4 - Refactored).

Simplified OpenAI provider using unified base, reducing code by ~70%.
Only implements provider-specific differences.
"""

from typing import Dict, Any, Optional, Tuple
from decimal import Decimal

from .provider_unified import UnifiedProviderBase
from .base import LLMRequest

class OpenAIProviderUnified(UnifiedProviderBase):
    """Simplified OpenAI provider using unified base."""
    
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
        
        # Model costs (as of 2024)
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
    
    def _get_api_endpoint(self, request: LLMRequest) -> str:
        """Get OpenAI API endpoint."""
        return f"{self.config.base_url}/chat/completions"
    
    async def _get_api_headers(self) -> Dict[str, str]:
        """Get OpenAI API headers."""
        headers = {
            "Authorization": f"Bearer {self._get_api_key()}",
            "Content-Type": "application/json"
        }
        
        if self.config.organization:
            headers["OpenAI-Organization"] = self.config.organization
        
        return headers
    
    async def _prepare_api_request(
        self,
        request: LLMRequest
    ) -> Dict[str, Any]:
        """Prepare OpenAI API request."""
        api_request = {
            "model": request.model,
            "messages": request.messages,
            "stream": request.stream
        }
        
        # Add optional parameters
        if request.max_tokens:
            api_request["max_tokens"] = request.max_tokens
        if request.temperature is not None:
            api_request["temperature"] = request.temperature
        if request.top_p is not None:
            api_request["top_p"] = request.top_p
        if request.frequency_penalty is not None:
            api_request["frequency_penalty"] = request.frequency_penalty
        if request.presence_penalty is not None:
            api_request["presence_penalty"] = request.presence_penalty
        if request.tools:
            api_request["tools"] = request.tools
        if request.tool_choice:
            api_request["tool_choice"] = request.tool_choice
        if request.response_format:
            api_request["response_format"] = request.response_format
        if request.user_id:
            api_request["user"] = request.user_id
        
        return api_request
    
    async def _parse_api_response(
        self,
        data: Dict[str, Any],
        request: LLMRequest
    ) -> Tuple[str, Dict[str, int], Dict[str, Any]]:
        """Parse OpenAI API response."""
        choice = data["choices"][0]
        content = choice["message"]["content"]
        
        usage_data = data.get("usage", {})
        
        metadata = {
            "finish_reason": choice.get("finish_reason"),
            "model": data.get("model"),
            "system_fingerprint": data.get("system_fingerprint")
        }
        
        return content, usage_data, metadata
    
    async def _parse_stream_chunk(
        self,
        chunk_data: Dict[str, Any]
    ) -> Optional[str]:
        """Parse OpenAI streaming chunk."""
        choices = chunk_data.get("choices", [])
        if not choices:
            return None
        
        delta = choices[0].get("delta", {})
        return delta.get("content", "")