"""
M008: Base Provider Interface.

Abstract base class defining the interface that all LLM providers must implement.
Provides consistent API across different LLM services.
"""

import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union, AsyncGenerator
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ProviderError(Exception):
    """Base exception for provider-related errors."""
    
    def __init__(self, message: str, provider: str, error_code: Optional[str] = None):
        self.message = message
        self.provider = provider
        self.error_code = error_code
        super().__init__(f"[{provider}] {message}")


class RateLimitError(ProviderError):
    """Raised when provider rate limits are exceeded."""
    pass


class AuthenticationError(ProviderError):
    """Raised when API authentication fails."""
    pass


class QuotaExceededError(ProviderError):
    """Raised when provider quota is exceeded."""
    pass


class ModelNotFoundError(ProviderError):
    """Raised when requested model is not available."""
    pass


class LLMRequest(BaseModel):
    """Standardized LLM request format."""
    
    # Core request data
    messages: List[Dict[str, str]] = Field(
        description="List of messages in OpenAI format"
    )
    model: str = Field(description="Model name to use")
    
    # Generation parameters
    max_tokens: Optional[int] = Field(default=None, ge=1, le=128000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    frequency_penalty: Optional[float] = Field(default=None, ge=-2.0, le=2.0)
    presence_penalty: Optional[float] = Field(default=None, ge=-2.0, le=2.0)
    
    # Request metadata
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    stream: bool = Field(default=False)
    
    # System settings (provider-specific)
    system_prompt: Optional[str] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    
    # Response format
    response_format: Optional[Dict[str, Any]] = None
    
    # Safety and filtering
    content_filter_enabled: bool = Field(default=True)
    
    def to_openai_format(self) -> Dict[str, Any]:
        """Convert to OpenAI API format."""
        data = {
            "messages": self.messages,
            "model": self.model,
            "temperature": self.temperature,
        }
        
        if self.max_tokens:
            data["max_tokens"] = self.max_tokens
        if self.top_p is not None:
            data["top_p"] = self.top_p
        if self.frequency_penalty is not None:
            data["frequency_penalty"] = self.frequency_penalty
        if self.presence_penalty is not None:
            data["presence_penalty"] = self.presence_penalty
        if self.stream:
            data["stream"] = self.stream
        if self.tools:
            data["tools"] = self.tools
        if self.tool_choice:
            data["tool_choice"] = self.tool_choice
        if self.response_format:
            data["response_format"] = self.response_format
            
        return data


class TokenUsage(BaseModel):
    """Token usage information."""
    
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    
    # Cost information (USD)
    prompt_cost: Decimal = Field(default=Decimal("0"))
    completion_cost: Decimal = Field(default=Decimal("0"))
    total_cost: Decimal = Field(default=Decimal("0"))


class LLMResponse(BaseModel):
    """Standardized LLM response format."""
    
    # Response content
    content: str = Field(description="Generated text content")
    finish_reason: str = Field(description="Why generation stopped")
    
    # Model information
    model: str = Field(description="Model that generated this response")
    provider: str = Field(description="Provider name")
    
    # Usage and cost
    usage: TokenUsage = Field(description="Token usage and cost information")
    
    # Request tracking
    request_id: str = Field(description="Original request ID")
    response_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Timing information
    response_time_ms: float = Field(ge=0, description="Response time in milliseconds")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Quality metrics (optional, set by quality analysis)
    quality_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    
    # Tool usage (if applicable)
    tool_calls: Optional[List[Dict[str, Any]]] = None
    
    # Provider-specific metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    All provider implementations must inherit from this class and implement
    the required methods for consistent API access across different LLM services.
    """
    
    def __init__(self, config: 'ProviderConfig'):
        """
        Initialize provider with configuration.
        
        Args:
            config: Provider-specific configuration
        """
        self.config = config
        self.provider_name = config.provider_type.value
        self.logger = logging.getLogger(f"{__name__}.{self.provider_name}")
        
        # Rate limiting state
        self._request_times: List[float] = []
        self._daily_requests = 0
        self._last_request_date: Optional[datetime] = None
        
        # Health monitoring
        self._consecutive_failures = 0
        self._last_failure_time: Optional[datetime] = None
        self._is_healthy = True
        
    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate text completion from the LLM.
        
        Args:
            request: Standardized LLM request
            
        Returns:
            LLM response with generated content
            
        Raises:
            ProviderError: When generation fails
        """
        pass
    
    @abstractmethod
    async def generate_stream(
        self, 
        request: LLMRequest
    ) -> AsyncGenerator[LLMResponse, None]:
        """
        Generate streaming text completion.
        
        Args:
            request: Standardized LLM request with stream=True
            
        Yields:
            Partial LLM responses as they arrive
            
        Raises:
            ProviderError: When streaming fails
        """
        pass
    
    @abstractmethod
    async def validate_connection(self) -> bool:
        """
        Validate that the provider connection is working.
        
        Returns:
            True if connection is valid, False otherwise
        """
        pass
    
    @abstractmethod
    def estimate_cost(self, request: LLMRequest) -> Decimal:
        """
        Estimate the cost of a request before sending.
        
        Args:
            request: LLM request to estimate
            
        Returns:
            Estimated cost in USD
        """
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """
        Get list of available models for this provider.
        
        Returns:
            List of model names
        """
        pass
    
    def calculate_cost(self, usage: TokenUsage) -> TokenUsage:
        """
        Calculate cost for token usage.
        
        Args:
            usage: Token usage information
            
        Returns:
            Updated usage with cost information
        """
        # Calculate costs per 1K tokens
        prompt_cost = (
            Decimal(str(usage.prompt_tokens)) / 1000 * 
            self.config.input_cost_per_1k
        )
        completion_cost = (
            Decimal(str(usage.completion_tokens)) / 1000 *
            self.config.output_cost_per_1k
        )
        
        usage.prompt_cost = prompt_cost
        usage.completion_cost = completion_cost
        usage.total_cost = prompt_cost + completion_cost
        
        return usage
    
    async def check_rate_limits(self) -> None:
        """
        Check and enforce rate limits.
        
        Raises:
            RateLimitError: When rate limits are exceeded
        """
        now = time.time()
        current_date = datetime.now().date()
        
        # Reset daily counter if new day
        if (self._last_request_date is None or 
            self._last_request_date != current_date):
            self._daily_requests = 0
            self._last_request_date = current_date
        
        # Check daily limit
        if (self.config.requests_per_day and 
            self._daily_requests >= self.config.requests_per_day):
            raise RateLimitError(
                f"Daily request limit exceeded ({self.config.requests_per_day})",
                self.provider_name
            )
        
        # Check per-minute limit
        minute_ago = now - 60
        recent_requests = [t for t in self._request_times if t > minute_ago]
        
        if len(recent_requests) >= self.config.requests_per_minute:
            wait_time = 60 - (now - recent_requests[0])
            raise RateLimitError(
                f"Rate limit exceeded. Wait {wait_time:.1f}s",
                self.provider_name
            )
        
        # Track this request
        self._request_times = recent_requests + [now]
        self._daily_requests += 1
    
    def update_health_status(self, success: bool, error: Optional[Exception] = None):
        """
        Update provider health status based on request outcome.
        
        Args:
            success: Whether the request succeeded
            error: Exception if request failed
        """
        if success:
            self._consecutive_failures = 0
            self._is_healthy = True
        else:
            self._consecutive_failures += 1
            self._last_failure_time = datetime.utcnow()
            
            # Mark unhealthy after 3 consecutive failures
            if self._consecutive_failures >= 3:
                self._is_healthy = False
                self.logger.warning(
                    f"Provider {self.provider_name} marked unhealthy "
                    f"after {self._consecutive_failures} failures"
                )
    
    def is_healthy(self) -> bool:
        """
        Check if provider is currently healthy.
        
        Returns:
            True if provider is healthy and available
        """
        # Auto-recover after 5 minutes
        if (not self._is_healthy and 
            self._last_failure_time and
            (datetime.utcnow() - self._last_failure_time).seconds > 300):
            self.logger.info(f"Auto-recovering provider {self.provider_name}")
            self._is_healthy = True
            self._consecutive_failures = 0
            
        return self._is_healthy and self.config.enabled
    
    def get_provider_info(self) -> Dict[str, Any]:
        """
        Get provider information and status.
        
        Returns:
            Dictionary with provider details
        """
        return {
            "name": self.provider_name,
            "type": self.config.provider_type.value,
            "enabled": self.config.enabled,
            "healthy": self.is_healthy(),
            "default_model": self.config.default_model,
            "available_models": self.get_available_models(),
            "requests_per_minute": self.config.requests_per_minute,
            "requests_per_day": self.config.requests_per_day,
            "consecutive_failures": self._consecutive_failures,
            "daily_requests": self._daily_requests,
            "quality_score": self.config.quality_score,
            "priority": self.config.priority,
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass