"""
M008: Unified Anthropic Provider Implementation (Pass 4 - Refactored).

Simplified Anthropic provider using unified base, reducing code by ~70%.
"""

from typing import Dict, Any, Optional, Tuple
from decimal import Decimal

from .provider_unified import UnifiedProviderBase
from .base import LLMRequest

class AnthropicProviderUnified(UnifiedProviderBase):
    """Simplified Anthropic provider using unified base."""
    
    def __init__(self, config: 'ProviderConfig'):
        """Initialize Anthropic provider."""
        super().__init__(config)
        
        if not config.api_key and not config.api_key_encrypted:
            raise ValueError("Anthropic API key is required")
        
        # Set default models if not configured
        if not self.config.available_models:
            self.config.available_models = [
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307",
                "claude-2.1",
                "claude-2.0",
                "claude-instant-1.2"
            ]
        
        # Model costs (as of 2024)
        self._model_costs = {
            "claude-3-opus-20240229": {
                "input": Decimal("0.015"),
                "output": Decimal("0.075")
            },
            "claude-3-sonnet-20240229": {
                "input": Decimal("0.003"),
                "output": Decimal("0.015")
            },
            "claude-3-haiku-20240307": {
                "input": Decimal("0.00025"),
                "output": Decimal("0.00125")
            },
            "claude-2.1": {
                "input": Decimal("0.008"),
                "output": Decimal("0.024")
            },
            "claude-2.0": {
                "input": Decimal("0.008"),
                "output": Decimal("0.024")
            },
            "claude-instant-1.2": {
                "input": Decimal("0.0008"),
                "output": Decimal("0.0024")
            }
        }
    
    def _get_api_endpoint(self, request: LLMRequest) -> str:
        """Get Anthropic API endpoint."""
        return f"{self.config.base_url}/messages"
    
    async def _get_api_headers(self) -> Dict[str, str]:
        """Get Anthropic API headers."""
        return {
            "x-api-key": self._get_api_key(),
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
    
    async def _prepare_api_request(
        self,
        request: LLMRequest
    ) -> Dict[str, Any]:
        """Prepare Anthropic API request."""
        # Convert OpenAI format to Anthropic format
        messages = []
        system_message = None
        
        for msg in request.messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        api_request = {
            "model": request.model,
            "messages": messages,
            "max_tokens": request.max_tokens or 4096,
            "stream": request.stream
        }
        
        if system_message:
            api_request["system"] = system_message
        
        if request.temperature is not None:
            api_request["temperature"] = request.temperature
        if request.top_p is not None:
            api_request["top_p"] = request.top_p
        
        return api_request
    
    async def _parse_api_response(
        self,
        data: Dict[str, Any],
        request: LLMRequest
    ) -> Tuple[str, Dict[str, int], Dict[str, Any]]:
        """Parse Anthropic API response."""
        content = data["content"][0]["text"]
        
        usage_data = data.get("usage", {})
        # Anthropic uses different field names
        usage_data = {
            "prompt_tokens": usage_data.get("input_tokens", 0),
            "completion_tokens": usage_data.get("output_tokens", 0),
            "total_tokens": usage_data.get("input_tokens", 0) + usage_data.get("output_tokens", 0)
        }
        
        metadata = {
            "stop_reason": data.get("stop_reason"),
            "model": data.get("model"),
            "id": data.get("id")
        }
        
        return content, usage_data, metadata
    
    async def _parse_stream_chunk(
        self,
        chunk_data: Dict[str, Any]
    ) -> Optional[str]:
        """Parse Anthropic streaming chunk."""
        chunk_type = chunk_data.get("type")
        
        if chunk_type == "content_block_delta":
            delta = chunk_data.get("delta", {})
            return delta.get("text", "")
        
        return None