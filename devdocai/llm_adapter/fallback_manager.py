"""
M008: Fallback Manager for Error Handling and Provider Chaining.

Implements intelligent fallback strategies when providers fail, including
retry logic, circuit breaker patterns, and cost-optimized provider selection.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

from .config import FallbackStrategy
from .providers.base import (
    BaseProvider, LLMRequest, LLMResponse,
    ProviderError, RateLimitError, AuthenticationError,
    QuotaExceededError, ModelNotFoundError
)

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"         # Circuit breaker active (not calling provider)
    HALF_OPEN = "half_open"  # Testing if provider has recovered


@dataclass
class FallbackAttempt:
    """Record of a fallback attempt."""
    provider_name: str
    attempt_number: int
    error: Optional[Exception]
    success: bool
    response_time_ms: Optional[float]
    cost: Optional[str]  # Decimal as string
    timestamp: datetime


@dataclass
class CircuitBreakerState:
    """State of a circuit breaker for a provider."""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    next_attempt_time: Optional[datetime] = None


class FallbackManager:
    """
    Manages fallback strategies and circuit breaker patterns for LLM providers.
    
    Implements intelligent error handling with:
    - Circuit breaker pattern to avoid hammering failed providers
    - Configurable retry strategies with exponential backoff  
    - Cost-optimized and quality-optimized provider selection
    - Detailed fallback attempt logging for analytics
    """
    
    def __init__(
        self,
        providers: Dict[str, BaseProvider],
        fallback_strategy: FallbackStrategy = FallbackStrategy.SEQUENTIAL,
        max_retries: int = 3,
        base_retry_delay: float = 1.0,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 60
    ):
        """
        Initialize fallback manager.
        
        Args:
            providers: Dictionary of available providers
            fallback_strategy: Strategy for provider selection
            max_retries: Maximum retry attempts per provider
            base_retry_delay: Base delay between retries (seconds)
            circuit_breaker_threshold: Failures before opening circuit
            circuit_breaker_timeout: Seconds to wait before trying again
        """
        self.providers = providers
        self.fallback_strategy = fallback_strategy
        self.max_retries = max_retries
        self.base_retry_delay = base_retry_delay
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout = circuit_breaker_timeout
        
        # Circuit breaker state for each provider
        self.circuit_breakers: Dict[str, CircuitBreakerState] = {
            name: CircuitBreakerState() for name in providers.keys()
        }
        
        # Fallback attempt history
        self.fallback_attempts: List[FallbackAttempt] = []
        
    async def execute_with_fallback(
        self,
        request: LLMRequest,
        preferred_provider: Optional[str] = None,
        cost_estimator: Optional[Callable[[str, LLMRequest], float]] = None
    ) -> Tuple[LLMResponse, List[FallbackAttempt]]:
        """
        Execute LLM request with fallback support.
        
        Args:
            request: LLM request to execute
            preferred_provider: Preferred provider to try first
            cost_estimator: Function to estimate request cost per provider
            
        Returns:
            Tuple of (response, fallback_attempts)
            
        Raises:
            ProviderError: When all providers fail
        """
        # Get provider order based on strategy
        provider_order = self._get_provider_order(
            request, preferred_provider, cost_estimator
        )
        
        attempts = []
        last_error = None
        
        # Try providers in order
        for provider_name in provider_order:
            provider = self.providers.get(provider_name)
            if not provider:
                continue
            
            # Check circuit breaker
            if not self._can_attempt_provider(provider_name):
                logger.debug(f"Skipping {provider_name} - circuit breaker open")
                continue
            
            # Check provider health
            if not provider.is_healthy():
                logger.debug(f"Skipping {provider_name} - provider unhealthy")
                continue
            
            # Attempt request with retries
            for attempt_num in range(1, self.max_retries + 1):
                attempt_start = datetime.utcnow()
                
                try:
                    # Execute request
                    start_time = asyncio.get_event_loop().time()
                    response = await provider.generate(request)
                    response_time = (asyncio.get_event_loop().time() - start_time) * 1000
                    
                    # Record successful attempt
                    attempt = FallbackAttempt(
                        provider_name=provider_name,
                        attempt_number=attempt_num,
                        error=None,
                        success=True,
                        response_time_ms=response_time,
                        cost=str(response.usage.total_cost),
                        timestamp=attempt_start
                    )
                    attempts.append(attempt)
                    self.fallback_attempts.append(attempt)
                    
                    # Update circuit breaker
                    self._record_success(provider_name)
                    
                    return response, attempts
                    
                except (RateLimitError, QuotaExceededError) as e:
                    # Don't retry rate limit errors, try next provider
                    attempt = FallbackAttempt(
                        provider_name=provider_name,
                        attempt_number=attempt_num,
                        error=e,
                        success=False,
                        response_time_ms=None,
                        cost=None,
                        timestamp=attempt_start
                    )
                    attempts.append(attempt)
                    self.fallback_attempts.append(attempt)
                    
                    logger.warning(f"Rate limit hit for {provider_name}: {e}")
                    self._record_failure(provider_name, e)
                    last_error = e
                    break  # Try next provider
                    
                except AuthenticationError as e:
                    # Don't retry auth errors, try next provider
                    attempt = FallbackAttempt(
                        provider_name=provider_name,
                        attempt_number=attempt_num,
                        error=e,
                        success=False,
                        response_time_ms=None,
                        cost=None,
                        timestamp=attempt_start
                    )
                    attempts.append(attempt)
                    self.fallback_attempts.append(attempt)
                    
                    logger.error(f"Authentication failed for {provider_name}: {e}")
                    self._record_failure(provider_name, e)
                    last_error = e
                    break  # Try next provider
                    
                except ModelNotFoundError as e:
                    # Try with default model or next provider
                    if request.model != provider.config.default_model:
                        logger.warning(f"Model {request.model} not found, trying default")
                        request.model = provider.config.default_model
                        continue  # Retry with default model
                    
                    attempt = FallbackAttempt(
                        provider_name=provider_name,
                        attempt_number=attempt_num,
                        error=e,
                        success=False,
                        response_time_ms=None,
                        cost=None,
                        timestamp=attempt_start
                    )
                    attempts.append(attempt)
                    self.fallback_attempts.append(attempt)
                    
                    last_error = e
                    break  # Try next provider
                    
                except ProviderError as e:
                    # Retry provider errors with backoff
                    attempt = FallbackAttempt(
                        provider_name=provider_name,
                        attempt_number=attempt_num,
                        error=e,
                        success=False,
                        response_time_ms=None,
                        cost=None,
                        timestamp=attempt_start
                    )
                    attempts.append(attempt)
                    self.fallback_attempts.append(attempt)
                    
                    logger.warning(f"Provider {provider_name} error (attempt {attempt_num}): {e}")
                    self._record_failure(provider_name, e)
                    last_error = e
                    
                    # Wait before retrying (exponential backoff)
                    if attempt_num < self.max_retries:
                        delay = self.base_retry_delay * (2 ** (attempt_num - 1))
                        await asyncio.sleep(delay)
                    
                except Exception as e:
                    # Unexpected error
                    attempt = FallbackAttempt(
                        provider_name=provider_name,
                        attempt_number=attempt_num,
                        error=e,
                        success=False,
                        response_time_ms=None,
                        cost=None,
                        timestamp=attempt_start
                    )
                    attempts.append(attempt)
                    self.fallback_attempts.append(attempt)
                    
                    logger.error(f"Unexpected error with {provider_name}: {e}")
                    self._record_failure(provider_name, e)
                    last_error = e
                    break  # Try next provider
        
        # All providers failed
        error_msg = f"All providers failed. Last error: {last_error}"
        logger.error(error_msg)
        
        raise ProviderError(
            error_msg,
            "fallback_manager",
            error_code="all_providers_failed"
        )
    
    def _get_provider_order(
        self,
        request: LLMRequest,
        preferred_provider: Optional[str],
        cost_estimator: Optional[Callable[[str, LLMRequest], float]]
    ) -> List[str]:
        """Get ordered list of providers based on fallback strategy."""
        
        available_providers = [
            name for name, provider in self.providers.items()
            if provider.is_healthy() and self._can_attempt_provider(name)
        ]
        
        if not available_providers:
            # Include all providers even if unhealthy as last resort
            available_providers = list(self.providers.keys())
        
        # Apply preferred provider first
        if preferred_provider and preferred_provider in available_providers:
            available_providers.remove(preferred_provider)
            available_providers.insert(0, preferred_provider)
        
        # Apply strategy-specific ordering to remaining providers
        if self.fallback_strategy == FallbackStrategy.COST_OPTIMIZED and cost_estimator:
            # Sort by estimated cost (lowest first)
            remaining = available_providers[1:] if preferred_provider else available_providers
            remaining.sort(key=lambda name: cost_estimator(name, request))
            
            if preferred_provider:
                return [preferred_provider] + remaining
            else:
                return remaining
                
        elif self.fallback_strategy == FallbackStrategy.QUALITY_OPTIMIZED:
            # Sort by quality score (highest first)
            remaining = available_providers[1:] if preferred_provider else available_providers
            remaining.sort(key=lambda name: self.providers[name].config.quality_score, reverse=True)
            
            if preferred_provider:
                return [preferred_provider] + remaining
            else:
                return remaining
                
        elif self.fallback_strategy == FallbackStrategy.PARALLEL:
            # For parallel strategy, return all providers (will be handled differently)
            return available_providers
            
        else:  # SEQUENTIAL (default)
            # Use providers in priority order
            remaining = available_providers[1:] if preferred_provider else available_providers
            remaining.sort(key=lambda name: self.providers[name].config.priority, reverse=True)
            
            if preferred_provider:
                return [preferred_provider] + remaining
            else:
                return remaining
    
    def _can_attempt_provider(self, provider_name: str) -> bool:
        """Check if provider can be attempted (circuit breaker check)."""
        circuit = self.circuit_breakers.get(provider_name)
        if not circuit:
            return True
        
        now = datetime.utcnow()
        
        if circuit.state == CircuitState.CLOSED:
            return True
        elif circuit.state == CircuitState.OPEN:
            # Check if we should try again
            if (circuit.next_attempt_time and 
                now >= circuit.next_attempt_time):
                # Switch to half-open
                circuit.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker for {provider_name} switching to half-open")
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def _record_success(self, provider_name: str) -> None:
        """Record successful provider call."""
        circuit = self.circuit_breakers.get(provider_name)
        if circuit:
            circuit.state = CircuitState.CLOSED
            circuit.failure_count = 0
            circuit.last_success_time = datetime.utcnow()
            circuit.next_attempt_time = None
            
            if circuit.state == CircuitState.HALF_OPEN:
                logger.info(f"Circuit breaker for {provider_name} closed after recovery")
    
    def _record_failure(self, provider_name: str, error: Exception) -> None:
        """Record provider failure and update circuit breaker."""
        circuit = self.circuit_breakers.get(provider_name)
        if not circuit:
            return
        
        circuit.failure_count += 1
        circuit.last_failure_time = datetime.utcnow()
        
        # Open circuit if threshold exceeded
        if circuit.failure_count >= self.circuit_breaker_threshold:
            circuit.state = CircuitState.OPEN
            circuit.next_attempt_time = (
                datetime.utcnow() + timedelta(seconds=self.circuit_breaker_timeout)
            )
            logger.warning(
                f"Circuit breaker opened for {provider_name} "
                f"after {circuit.failure_count} failures"
            )
    
    def get_provider_health_status(self) -> Dict[str, Any]:
        """Get health status of all providers."""
        status = {}
        
        for name, provider in self.providers.items():
            circuit = self.circuit_breakers.get(name, CircuitBreakerState())
            
            # Get recent attempt statistics
            recent_attempts = [
                attempt for attempt in self.fallback_attempts
                if (attempt.provider_name == name and
                    (datetime.utcnow() - attempt.timestamp).seconds < 3600)  # Last hour
            ]
            
            success_count = sum(1 for a in recent_attempts if a.success)
            total_attempts = len(recent_attempts)
            success_rate = (success_count / total_attempts) if total_attempts > 0 else 0
            
            status[name] = {
                "healthy": provider.is_healthy(),
                "circuit_state": circuit.state.value,
                "failure_count": circuit.failure_count,
                "last_failure": circuit.last_failure_time.isoformat() if circuit.last_failure_time else None,
                "last_success": circuit.last_success_time.isoformat() if circuit.last_success_time else None,
                "recent_success_rate": success_rate,
                "recent_attempts": total_attempts,
                "priority": provider.config.priority,
                "quality_score": provider.config.quality_score
            }
        
        return status
    
    def reset_circuit_breaker(self, provider_name: str) -> bool:
        """
        Manually reset circuit breaker for a provider.
        
        Args:
            provider_name: Name of provider to reset
            
        Returns:
            True if reset successful, False if provider not found
        """
        circuit = self.circuit_breakers.get(provider_name)
        if not circuit:
            return False
        
        circuit.state = CircuitState.CLOSED
        circuit.failure_count = 0
        circuit.next_attempt_time = None
        
        logger.info(f"Manually reset circuit breaker for {provider_name}")
        return True
    
    def get_recent_attempts(self, hours: int = 24) -> List[FallbackAttempt]:
        """Get recent fallback attempts for analysis."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return [
            attempt for attempt in self.fallback_attempts
            if attempt.timestamp >= cutoff_time
        ]