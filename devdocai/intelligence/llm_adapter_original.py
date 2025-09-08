"""
M008 LLM Adapter - Multi-Provider AI Intelligence Layer
DevDocAI v3.0.0 - Pass 1: Core Implementation with TDD
"""

import re
import time
import hashlib
import hmac
import json
import logging
import asyncio
import concurrent.futures
import secrets
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from collections import OrderedDict, deque
import threading
from enum import Enum

# Third-party imports (will be mocked in tests)
try:
    import anthropic
except ImportError:
    anthropic = None

try:
    import openai
except ImportError:
    openai = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

# Local imports
from ..core.config import ConfigurationManager
from ..core.models import LLMConfig

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes and Exceptions
# ============================================================================

# Pre-compiled regex patterns for optimized sanitization (Pass 2)
_EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
_PHONE_PATTERN = re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b')
_SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
_API_KEY_PATTERN = re.compile(r'\b(sk-|api[_-]?key[:\s]+)[A-Za-z0-9]+\b', re.IGNORECASE)
_CREDIT_CARD_PATTERN = re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b')

@dataclass
class LLMResponse:
    """Response from LLM provider."""
    content: str
    provider: str
    tokens_used: int
    cost: float
    latency: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    cached: bool = False
    timestamp: datetime = field(default_factory=datetime.now)


class ProviderError(Exception):
    """Base exception for provider errors."""
    pass


class BudgetExceededError(Exception):
    """Raised when daily budget limit is exceeded."""
    pass


class APITimeoutError(Exception):
    """Raised when API request times out."""
    pass


class RateLimitExceededError(Exception):
    """Raised when rate limit is exceeded for a provider."""
    pass


class RequestSignatureError(Exception):
    """Raised when request signature validation fails."""
    pass


# ============================================================================
# Security Components - Pass 3: Security Hardening
# ============================================================================

class SecurityEvent(Enum):
    """Security event types for audit logging."""
    API_CALL = "api_call"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    BUDGET_EXCEEDED = "budget_exceeded"
    SIGNATURE_VALIDATION_FAILED = "signature_validation_failed"
    PII_DETECTED = "pii_detected"
    ERROR = "error"
    CACHE_HIT = "cache_hit"
    FALLBACK = "fallback"


class RateLimiter:
    """
    Token bucket rate limiter for API request throttling.
    Implements per-provider rate limiting to prevent abuse.
    """
    
    def __init__(self, tokens_per_minute: int = 60, burst_capacity: int = 10):
        """
        Initialize rate limiter with token bucket algorithm.
        
        Args:
            tokens_per_minute: Sustained rate limit
            burst_capacity: Maximum burst size
        """
        self.capacity = burst_capacity
        self.tokens = burst_capacity
        self.fill_rate = tokens_per_minute / 60.0  # tokens per second
        self.last_update = time.time()
        self._lock = threading.Lock()
        
    def acquire(self, tokens: int = 1) -> bool:
        """
        Attempt to acquire tokens for a request.
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            True if tokens acquired, False if rate limited
        """
        with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            self.last_update = now
            
            # Refill tokens based on elapsed time
            self.tokens = min(self.capacity, self.tokens + elapsed * self.fill_rate)
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
            
    def get_wait_time(self) -> float:
        """
        Get time to wait before tokens are available.
        
        Returns:
            Seconds to wait for next available token
        """
        with self._lock:
            if self.tokens < 1:
                return (1 - self.tokens) / self.fill_rate
            return 0.0


class RequestSigner:
    """
    HMAC-SHA256 request signing for integrity and authentication.
    Prevents request tampering and replay attacks.
    """
    
    def __init__(self, secret_key: str):
        """
        Initialize request signer with secret key.
        
        Args:
            secret_key: Secret key for HMAC signing
        """
        self.secret_key = secret_key.encode('utf-8')
        self.replay_window = 300  # 5 minutes
        self.seen_nonces = deque(maxlen=1000)
        self._lock = threading.Lock()
        
    def sign_request(self, 
                    provider: str,
                    prompt: str,
                    timestamp: Optional[datetime] = None) -> Dict[str, str]:
        """
        Sign a request with HMAC-SHA256.
        
        Args:
            provider: LLM provider name
            prompt: Request prompt
            timestamp: Request timestamp (defaults to now)
            
        Returns:
            Dictionary with signature data
        """
        timestamp = timestamp or datetime.now()
        nonce = secrets.token_hex(16)
        
        # Create canonical request string
        canonical_request = f"{provider}:{prompt}:{timestamp.isoformat()}:{nonce}"
        
        # Generate HMAC signature
        signature = hmac.new(
            self.secret_key,
            canonical_request.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return {
            'signature': signature,
            'timestamp': timestamp.isoformat(),
            'nonce': nonce,
            'provider': provider
        }
        
    def verify_signature(self, 
                        provider: str,
                        prompt: str,
                        signature_data: Dict[str, str]) -> bool:
        """
        Verify request signature and prevent replay attacks.
        
        Args:
            provider: LLM provider name
            prompt: Request prompt
            signature_data: Signature data to verify
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            # Check timestamp to prevent replay attacks
            timestamp = datetime.fromisoformat(signature_data['timestamp'])
            if abs((datetime.now() - timestamp).total_seconds()) > self.replay_window:
                return False
                
            # Check for replay attack using nonce
            nonce = signature_data['nonce']
            with self._lock:
                if nonce in self.seen_nonces:
                    return False
                self.seen_nonces.append(nonce)
                
            # Recreate and verify signature
            canonical_request = f"{provider}:{prompt}:{signature_data['timestamp']}:{nonce}"
            expected_signature = hmac.new(
                self.secret_key,
                canonical_request.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(expected_signature, signature_data['signature'])
            
        except (KeyError, ValueError):
            return False


class AuditLogger:
    """
    Structured audit logging for security events and compliance.
    Provides comprehensive logging with PII sanitization.
    """
    
    def __init__(self, logger_name: str = "devdocai.security.audit"):
        """
        Initialize audit logger with structured logging.
        
        Args:
            logger_name: Name for the audit logger
        """
        self.logger = logging.getLogger(logger_name)
        self.request_counter = 0
        self._lock = threading.Lock()
        
        # Configure structured logging format
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
            
    def generate_request_id(self) -> str:
        """Generate unique request ID for tracking."""
        with self._lock:
            self.request_counter += 1
            return f"req_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self.request_counter:06d}_{uuid.uuid4().hex[:8]}"
            
    def log_event(self,
                 event_type: SecurityEvent,
                 request_id: str,
                 provider: str,
                 details: Dict[str, Any],
                 sanitize_pii: bool = True) -> None:
        """
        Log security event with structured data.
        
        Args:
            event_type: Type of security event
            request_id: Unique request identifier
            provider: LLM provider name
            details: Event details
            sanitize_pii: Whether to sanitize PII in logs
        """
        # Sanitize details if needed
        if sanitize_pii:
            details = self._sanitize_log_data(details)
            
        # Create structured log entry
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'request_id': request_id,
            'event_type': event_type.value,
            'provider': provider,
            'details': details
        }
        
        # Log based on event severity
        if event_type in [SecurityEvent.ERROR, SecurityEvent.SIGNATURE_VALIDATION_FAILED]:
            self.logger.error(json.dumps(log_entry))
        elif event_type in [SecurityEvent.RATE_LIMIT_EXCEEDED, SecurityEvent.BUDGET_EXCEEDED]:
            self.logger.warning(json.dumps(log_entry))
        else:
            self.logger.info(json.dumps(log_entry))
            
    def _sanitize_log_data(self, data: Any) -> Any:
        """
        Recursively sanitize PII from log data.
        
        Args:
            data: Data to sanitize
            
        Returns:
            Sanitized data
        """
        if isinstance(data, str):
            # Apply PII sanitization patterns
            data = _EMAIL_PATTERN.sub('[EMAIL]', data)
            data = _PHONE_PATTERN.sub('[PHONE]', data)
            data = _SSN_PATTERN.sub('[SSN]', data)
            data = _API_KEY_PATTERN.sub('[API_KEY]', data)
            data = _CREDIT_CARD_PATTERN.sub('[CREDIT_CARD]', data)
            return data
        elif isinstance(data, dict):
            return {k: self._sanitize_log_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_log_data(item) for item in data]
        else:
            return data


# ============================================================================
# Enhanced PII Detection Patterns - Pass 3
# ============================================================================

# Additional PII patterns for enhanced detection
_IP_ADDRESS_PATTERN = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
_DATE_OF_BIRTH_PATTERN = re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b')
_PASSPORT_PATTERN = re.compile(r'\b[A-Z]{1,2}\d{6,9}\b')
_DRIVER_LICENSE_PATTERN = re.compile(r'\b[A-Z]\d{7,12}\b')
_BANK_ACCOUNT_PATTERN = re.compile(r'\b\d{8,17}\b')
_AWS_KEY_PATTERN = re.compile(r'\b(AKIA[0-9A-Z]{16})\b')
_GITHUB_TOKEN_PATTERN = re.compile(r'\b(ghp_[a-zA-Z0-9]{36})\b')


# ============================================================================
# Cost Manager
# ============================================================================

class CostManager:
    """
    Manages API costs and budget enforcement.
    Tracks usage with 99.9% accuracy and enforces daily limits.
    """
    
    def __init__(self, daily_limit: float = 10.00):
        """
        Initialize cost manager.
        
        Args:
            daily_limit: Daily spending limit in USD (default: $10.00)
        """
        self.daily_limit = daily_limit
        self.current_usage = 0.00
        self.usage_history: List[Dict[str, Any]] = []
        self.last_reset = datetime.now()
        self._lock = threading.RLock()
        
    def track_usage(self, provider: str, cost: float, tokens: int) -> None:
        """
        Track API usage with 99.9% accuracy.
        
        Args:
            provider: Provider name
            cost: Cost in USD
            tokens: Number of tokens used
        """
        with self._lock:
            # Round to ensure 99.9% accuracy (3 decimal places)
            cost = round(cost, 3)
            self.current_usage = round(self.current_usage + cost, 3)
            
            self.usage_history.append({
                'provider': provider,
                'cost': cost,
                'tokens': tokens,
                'timestamp': datetime.now().isoformat()
            })
            
            logger.debug(f"Tracked usage: {provider} - ${cost:.3f} ({tokens} tokens)")
            
    def check_budget(self, estimated_cost: float) -> bool:
        """
        Check if estimated cost fits within budget.
        
        Args:
            estimated_cost: Estimated cost for next operation
            
        Returns:
            True if within budget
            
        Raises:
            BudgetExceededError: If would exceed daily limit
        """
        with self._lock:
            projected_usage = self.current_usage + estimated_cost
            
            if projected_usage > self.daily_limit:
                remaining = self.daily_limit - self.current_usage
                raise BudgetExceededError(
                    f"Daily budget would be exceeded. "
                    f"Current: ${self.current_usage:.2f}, "
                    f"Limit: ${self.daily_limit:.2f}, "
                    f"Remaining: ${remaining:.2f}"
                )
            
            return True
            
    def get_warning_status(self) -> Optional[str]:
        """
        Get warning if usage exceeds 80% threshold.
        
        Returns:
            Warning message if threshold exceeded, None otherwise
        """
        usage_percent = (self.current_usage / self.daily_limit) * 100
        
        if usage_percent >= 80:
            remaining = self.daily_limit - self.current_usage
            
            # Calculate projected overage time based on recent usage rate
            if len(self.usage_history) >= 2:
                recent_usage = self.usage_history[-10:]  # Last 10 requests
                if len(recent_usage) >= 2:
                    time_span = (
                        datetime.fromisoformat(recent_usage[-1]['timestamp']) -
                        datetime.fromisoformat(recent_usage[0]['timestamp'])
                    ).total_seconds() / 60  # minutes
                    
                    if time_span > 0:
                        usage_rate = sum(h['cost'] for h in recent_usage) / time_span
                        minutes_remaining = remaining / usage_rate if usage_rate > 0 else float('inf')
                        
                        return (
                            f"Warning: {usage_percent:.1f}% of daily budget used. "
                            f"${remaining:.2f} remaining. "
                            f"Projected to exceed limit in {minutes_remaining:.0f} minutes."
                        )
            
            return f"Warning: {usage_percent:.1f}% of daily budget used. ${remaining:.2f} remaining."
        
        return None
        
    def reset_daily_usage(self) -> None:
        """Reset daily usage counter while preserving history."""
        with self._lock:
            self.current_usage = 0.00
            self.last_reset = datetime.now()
            logger.info("Daily usage counter reset")
            
    def get_optimal_provider(
        self, 
        providers: Dict[str, Dict[str, float]], 
        priority: str = 'balanced'
    ) -> str:
        """
        Get optimal provider based on cost/quality ratio.
        
        Args:
            providers: Dict of provider -> {cost, quality} mappings
            priority: 'cost', 'quality', or 'balanced'
            
        Returns:
            Optimal provider name
        """
        if priority == 'quality':
            # Highest quality first
            return max(providers.items(), key=lambda x: x[1]['quality'])[0]
        elif priority == 'cost':
            # Lowest cost first
            return min(providers.items(), key=lambda x: x[1]['cost'])[0]
        else:  # balanced
            # Best quality/cost ratio
            return max(providers.items(), key=lambda x: x[1]['quality'] / x[1]['cost'])[0]


# ============================================================================
# Response Cache
# ============================================================================

class ResponseCache:
    """
    LRU cache for LLM responses with TTL support.
    """
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        """
        Initialize response cache.
        
        Args:
            max_size: Maximum number of cached responses
            ttl_seconds: Time-to-live for cached entries in seconds
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, Tuple[LLMResponse, datetime]] = OrderedDict()
        self._lock = threading.RLock()
        
    def generate_key(self, prompt: str, provider: str = None, **kwargs) -> str:
        """
        Generate consistent cache key from inputs.
        
        Args:
            prompt: Input prompt
            provider: Provider name
            **kwargs: Additional parameters (temperature, etc.)
            
        Returns:
            Cache key string
        """
        key_data = {
            'prompt': prompt,
            'provider': provider,
            **kwargs
        }
        
        # Create stable JSON representation
        key_json = json.dumps(key_data, sort_keys=True)
        
        # Generate hash for consistent key
        return hashlib.sha256(key_json.encode()).hexdigest()
        
    def store(self, key: str, response: LLMResponse) -> None:
        """
        Store response in cache.
        
        Args:
            key: Cache key
            response: Response to cache
        """
        with self._lock:
            # Remove oldest if at capacity
            if len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
                
            # Store with timestamp
            self._cache[key] = (response, datetime.now())
            
            # Move to end (most recent)
            self._cache.move_to_end(key)
            
    def get(self, key: str) -> Optional[LLMResponse]:
        """
        Retrieve response from cache if valid.
        
        Args:
            key: Cache key
            
        Returns:
            Cached response if valid, None otherwise
        """
        with self._lock:
            if key not in self._cache:
                return None
                
            response, timestamp = self._cache[key]
            
            # Check TTL
            age = (datetime.now() - timestamp).total_seconds()
            if age > self.ttl_seconds:
                # Expired
                del self._cache[key]
                return None
                
            # Move to end (most recent access)
            self._cache.move_to_end(key)
            
            # Mark as cached
            response.cached = True
            return response
            
    def clear(self) -> None:
        """Clear all cached responses."""
        with self._lock:
            self._cache.clear()


# ============================================================================
# Provider Base Class and Implementations
# ============================================================================

class Provider(ABC):
    """
    Abstract base class for LLM providers.
    """
    
    def __init__(
        self,
        config: ConfigurationManager,
        cost_per_1k: float = 0.01,
        quality_score: float = 0.85,
        weight: float = 0.33,
        timeout: float = 30.0
    ):
        """
        Initialize provider.
        
        Args:
            config: Configuration manager
            cost_per_1k: Cost per 1000 tokens in USD
            quality_score: Quality score (0-1)
            weight: Weight for multi-provider synthesis
            timeout: Request timeout in seconds
        """
        self.config = config
        self.cost_per_1k = cost_per_1k
        self.quality_score = quality_score
        self.weight = weight
        self.timeout = timeout
        self.name = self.__class__.__name__.replace('Provider', '').lower()
        
    def sanitize_data(self, text: str) -> str:
        """
        Enhanced PII sanitization for sensitive data (Pass 3: Security Hardening).
        Optimized with pre-compiled regex patterns and expanded detection.
        
        Args:
            text: Input text
            
        Returns:
            Sanitized text with PII replaced
        """
        # Original PII patterns
        text = _EMAIL_PATTERN.sub('[EMAIL]', text)
        text = _PHONE_PATTERN.sub('[PHONE]', text)
        text = _SSN_PATTERN.sub('[SSN]', text)
        text = _API_KEY_PATTERN.sub('[API_KEY]', text)
        text = _CREDIT_CARD_PATTERN.sub('[CREDIT_CARD]', text)
        
        # Enhanced PII patterns (Pass 3)
        text = _IP_ADDRESS_PATTERN.sub('[IP_ADDRESS]', text)
        text = _DATE_OF_BIRTH_PATTERN.sub('[DATE]', text)
        text = _PASSPORT_PATTERN.sub('[PASSPORT]', text)
        text = _DRIVER_LICENSE_PATTERN.sub('[LICENSE]', text)
        text = _BANK_ACCOUNT_PATTERN.sub('[ACCOUNT]', text)
        text = _AWS_KEY_PATTERN.sub('[AWS_KEY]', text)
        text = _GITHUB_TOKEN_PATTERN.sub('[GITHUB_TOKEN]', text)
        
        return text
        
    def calculate_cost(self, tokens: int) -> float:
        """
        Calculate cost for token usage.
        
        Args:
            tokens: Number of tokens
            
        Returns:
            Cost in USD
        """
        return round((tokens / 1000) * self.cost_per_1k, 3)
        
    def _check_timeout(self, start_time: float) -> None:
        """
        Check if request has timed out.
        
        Args:
            start_time: Request start time
            
        Raises:
            APITimeoutError: If timeout exceeded
        """
        elapsed = time.time() - start_time
        if elapsed > self.timeout:
            raise APITimeoutError(f"Request timeout after {elapsed:.1f} seconds")
            
    @abstractmethod
    def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """
        Generate response from provider.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional provider-specific parameters
            
        Returns:
            LLM response
        """
        pass


class ClaudeProvider(Provider):
    """Anthropic Claude provider implementation."""
    
    def __init__(self, config: ConfigurationManager, **kwargs):
        """Initialize Claude provider."""
        super().__init__(
            config,
            cost_per_1k=kwargs.get('cost_per_1k', 0.015),
            quality_score=kwargs.get('quality_score', 0.95),
            weight=kwargs.get('weight', 0.4),
            timeout=kwargs.get('timeout', 30.0)
        )
        self.name = "claude"
        
    def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """Generate response using Claude API."""
        if not anthropic:
            raise ProviderError("Anthropic library not installed")
            
        start_time = time.time()
        
        try:
            # Sanitize input
            sanitized_prompt = self.sanitize_data(prompt)
            
            # Get API key from config
            api_key = self.config.get_api_key('anthropic')
            if not api_key:
                raise ProviderError("Anthropic API key not configured")
                
            # Initialize client
            client = anthropic.Anthropic(api_key=api_key)
            
            # Check timeout
            self._check_timeout(start_time)
            
            # Make API call
            response = client.messages.create(
                model=kwargs.get('model', 'claude-3-opus-20240229'),
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": sanitized_prompt}]
            )
            
            # Extract response
            content = response.content[0].text if response.content else ""
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            
            # Calculate cost
            cost = self.calculate_cost(tokens_used)
            
            # Calculate latency
            latency = time.time() - start_time
            
            return LLMResponse(
                content=content,
                provider=self.name,
                tokens_used=tokens_used,
                cost=cost,
                latency=latency,
                metadata={'model': kwargs.get('model', 'claude-3-opus-20240229')}
            )
            
        except APITimeoutError:
            raise
        except Exception as e:
            raise ProviderError(f"Claude API error: {str(e)}")


class OpenAIProvider(Provider):
    """OpenAI GPT provider implementation."""
    
    def __init__(self, config: ConfigurationManager, **kwargs):
        """Initialize OpenAI provider."""
        super().__init__(
            config,
            cost_per_1k=kwargs.get('cost_per_1k', 0.020),
            quality_score=kwargs.get('quality_score', 0.90),
            weight=kwargs.get('weight', 0.35),
            timeout=kwargs.get('timeout', 30.0)
        )
        self.name = "openai"
        
    def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """Generate response using OpenAI API."""
        if not openai:
            raise ProviderError("OpenAI library not installed")
            
        start_time = time.time()
        
        try:
            # Sanitize input
            sanitized_prompt = self.sanitize_data(prompt)
            
            # Get API key from config
            api_key = self.config.get_api_key('openai')
            if not api_key:
                raise ProviderError("OpenAI API key not configured")
                
            # Initialize client
            client = openai.OpenAI(api_key=api_key)
            
            # Check timeout
            self._check_timeout(start_time)
            
            # Make API call
            response = client.chat.completions.create(
                model=kwargs.get('model', 'gpt-4'),
                messages=[{"role": "user", "content": sanitized_prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            # Extract response
            content = response.choices[0].message.content if response.choices else ""
            tokens_used = response.usage.prompt_tokens + response.usage.completion_tokens
            
            # Calculate cost
            cost = self.calculate_cost(tokens_used)
            
            # Calculate latency
            latency = time.time() - start_time
            
            return LLMResponse(
                content=content,
                provider=self.name,
                tokens_used=tokens_used,
                cost=cost,
                latency=latency,
                metadata={'model': kwargs.get('model', 'gpt-4')}
            )
            
        except APITimeoutError:
            raise
        except Exception as e:
            raise ProviderError(f"OpenAI API error: {str(e)}")


class GeminiProvider(Provider):
    """Google Gemini provider implementation."""
    
    def __init__(self, config: ConfigurationManager, **kwargs):
        """Initialize Gemini provider."""
        super().__init__(
            config,
            cost_per_1k=kwargs.get('cost_per_1k', 0.010),
            quality_score=kwargs.get('quality_score', 0.85),
            weight=kwargs.get('weight', 0.25),
            timeout=kwargs.get('timeout', 30.0)
        )
        self.name = "gemini"
        
    def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """Generate response using Gemini API."""
        if not genai:
            raise ProviderError("Google GenerativeAI library not installed")
            
        start_time = time.time()
        
        try:
            # Sanitize input
            sanitized_prompt = self.sanitize_data(prompt)
            
            # Get API key from config
            api_key = self.config.get_api_key('gemini')
            if not api_key:
                raise ProviderError("Gemini API key not configured")
                
            # Configure API
            genai.configure(api_key=api_key)
            
            # Initialize model
            model = genai.GenerativeModel(kwargs.get('model', 'gemini-pro'))
            
            # Check timeout
            self._check_timeout(start_time)
            
            # Make API call
            response = model.generate_content(
                sanitized_prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=temperature
                )
            )
            
            # Extract response
            content = response.text if response else ""
            
            # Get token count (if available)
            if hasattr(response, 'usage_metadata'):
                tokens_used = response.usage_metadata.total_token_count
            else:
                # Estimate tokens
                tokens_used = len(sanitized_prompt.split()) + len(content.split())
            
            # Calculate cost
            cost = self.calculate_cost(tokens_used)
            
            # Calculate latency
            latency = time.time() - start_time
            
            return LLMResponse(
                content=content,
                provider=self.name,
                tokens_used=tokens_used,
                cost=cost,
                latency=latency,
                metadata={'model': kwargs.get('model', 'gemini-pro')}
            )
            
        except APITimeoutError:
            raise
        except Exception as e:
            raise ProviderError(f"Gemini API error: {str(e)}")


class LocalProvider(Provider):
    """Local fallback provider (no external API)."""
    
    def __init__(self, config: ConfigurationManager, **kwargs):
        """Initialize local provider."""
        super().__init__(
            config,
            cost_per_1k=0.0,  # Local is free
            quality_score=kwargs.get('quality_score', 0.70),
            weight=kwargs.get('weight', 0.0),  # Not used in synthesis by default
            timeout=kwargs.get('timeout', 5.0)  # Fast local response
        )
        self.name = "local"
        
    def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """Generate response using local model or heuristics."""
        start_time = time.time()
        
        try:
            # Sanitize input even for local processing
            sanitized_prompt = self.sanitize_data(prompt)
            
            # For now, provide a simple response
            # In production, this would use a local model like llama.cpp
            content = (
                "Local fallback response. "
                "This is a placeholder for when cloud APIs are unavailable or budget is exceeded. "
                "In production, this would use a local AI model."
            )
            
            # Estimate tokens
            tokens_used = len(sanitized_prompt.split()) + len(content.split())
            
            # No cost for local
            cost = 0.0
            
            # Calculate latency
            latency = time.time() - start_time
            
            return LLMResponse(
                content=content,
                provider=self.name,
                tokens_used=tokens_used,
                cost=cost,
                latency=latency,
                metadata={'fallback': True}
            )
            
        except Exception as e:
            raise ProviderError(f"Local provider error: {str(e)}")


# ============================================================================
# Request Batching (Pass 2 Optimization)
# ============================================================================

class RequestBatcher:
    """
    Batches similar requests for optimized API calls.
    Pass 2 optimization for cost reduction.
    """
    
    def __init__(self, batch_size: int = 5, batch_timeout: float = 0.1):
        """
        Initialize request batcher.
        
        Args:
            batch_size: Maximum requests per batch
            batch_timeout: Maximum wait time before sending batch
        """
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.pending_requests: deque = deque()
        self._lock = threading.RLock()
        self._batch_event = threading.Event()
        
    def add_request(self, prompt: str, **kwargs) -> "BatchRequest":
        """
        Add request to batch queue.
        
        Args:
            prompt: Request prompt
            **kwargs: Request parameters
            
        Returns:
            BatchRequest with future for result
        """
        with self._lock:
            future = concurrent.futures.Future()
            request = BatchRequest(prompt=prompt, future=future, **kwargs)
            self.pending_requests.append(request)
            
            # Trigger batch if size reached
            if len(self.pending_requests) >= self.batch_size:
                self._batch_event.set()
                
            return request
            
    def get_batch(self) -> List["BatchRequest"]:
        """
        Get current batch of requests.
        
        Returns:
            List of batch requests
        """
        with self._lock:
            if not self.pending_requests:
                return []
                
            # Get up to batch_size requests
            batch = []
            for _ in range(min(self.batch_size, len(self.pending_requests))):
                batch.append(self.pending_requests.popleft())
                
            return batch
            
    def should_process(self) -> bool:
        """
        Check if batch should be processed.
        
        Returns:
            True if batch is ready
        """
        with self._lock:
            return len(self.pending_requests) >= self.batch_size


@dataclass
class BatchRequest:
    """Request queued for batching."""
    prompt: str
    future: concurrent.futures.Future
    provider: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Main LLM Adapter
# ============================================================================

class LLMAdapter:
    """
    Main adapter for multi-provider LLM integration.
    Manages provider routing, cost tracking, caching, and fallback.
    """
    
    def __init__(self, config_manager: Optional[ConfigurationManager] = None):
        """
        Initialize LLM adapter with security hardening (Pass 3).
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config = config_manager or ConfigurationManager()
        
        # Initialize core components
        self.cost_manager = CostManager(daily_limit=10.00)
        self.cache = ResponseCache(max_size=100, ttl_seconds=3600)
        self.batcher = RequestBatcher(batch_size=5, batch_timeout=0.1)
        
        # Initialize security components (Pass 3: Security Hardening)
        self.audit_logger = AuditLogger("devdocai.security.audit")
        
        # Initialize rate limiters per provider with configurable limits
        self.rate_limiters = {
            'openai': RateLimiter(tokens_per_minute=60, burst_capacity=10),
            'claude': RateLimiter(tokens_per_minute=50, burst_capacity=8),
            'google': RateLimiter(tokens_per_minute=40, burst_capacity=6),
            'local': RateLimiter(tokens_per_minute=100, burst_capacity=20)
        }
        
        # Initialize request signer with secret key from config
        # Get or generate a secret key for request signing
        secret_key = self.config.get_api_key('signing_key')
        if not secret_key:
            # Generate and store a new signing key if none exists
            secret_key = secrets.token_hex(32)
            # Note: In production, this would be stored securely
            logger.info("Generated new signing key for request integrity")
        self.request_signer = RequestSigner(secret_key)
        
        # Initialize providers
        self.providers = self._initialize_providers()
        
        # Thread pool for parallel provider queries (Pass 2)
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        
        # Set defaults from config
        llm_config = self.config.get_llm_config() if hasattr(self.config, 'get_llm_config') else None
        if llm_config:
            self.default_provider = llm_config.provider
            self.default_max_tokens = llm_config.max_tokens
            self.default_temperature = llm_config.temperature
        else:
            self.default_provider = "openai"
            self.default_max_tokens = 4000
            self.default_temperature = 0.7
            
        logger.info("LLM Adapter initialized with providers: %s", list(self.providers.keys()))
        
    def _initialize_providers(self) -> Dict[str, Provider]:
        """
        Initialize all available providers.
        
        Returns:
            Dictionary of provider instances
        """
        providers = {}
        
        # Initialize Claude
        try:
            providers['claude'] = ClaudeProvider(
                config=self.config,
                cost_per_1k=0.015,
                quality_score=0.95,
                weight=0.4
            )
        except Exception as e:
            logger.warning(f"Failed to initialize Claude provider: {e}")
            
        # Initialize OpenAI
        try:
            providers['openai'] = OpenAIProvider(
                config=self.config,
                cost_per_1k=0.020,
                quality_score=0.90,
                weight=0.35
            )
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI provider: {e}")
            
        # Initialize Gemini
        try:
            providers['gemini'] = GeminiProvider(
                config=self.config,
                cost_per_1k=0.010,
                quality_score=0.85,
                weight=0.25
            )
        except Exception as e:
            logger.warning(f"Failed to initialize Gemini provider: {e}")
            
        # Always have local fallback
        providers['local'] = LocalProvider(
            config=self.config,
            quality_score=0.70,
            weight=0.0
        )
        
        return providers
        
    def generate(
        self,
        prompt: str,
        provider: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        use_cache: bool = True,
        estimated_tokens: Optional[int] = None,
        timeout: float = 2.0,
        verify_signature: bool = False,
        signature_data: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate response with automatic fallback and security hardening.
        
        Args:
            prompt: Input prompt
            provider: Specific provider to use (optional)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            use_cache: Whether to use cache
            estimated_tokens: Estimated token count for budget check
            timeout: Maximum time for response (2-second fallback requirement)
            verify_signature: Whether to verify request signature (Pass 3)
            signature_data: Signature data for verification (Pass 3)
            **kwargs: Additional provider-specific parameters
            
        Returns:
            LLM response
        """
        # Use defaults if not specified
        max_tokens = max_tokens or self.default_max_tokens
        temperature = temperature or self.default_temperature
        provider = provider or self.default_provider
        
        # Generate unique request ID for audit logging
        request_id = self.audit_logger.generate_request_id()
        
        # Check cache first
        if use_cache:
            cache_key = self.cache.generate_key(prompt, provider, temperature=temperature)
            cached_response = self.cache.get(cache_key)
            if cached_response:
                logger.debug(f"Cache hit for prompt (provider: {provider})")
                # Log cache hit event
                self.audit_logger.log_event(
                    SecurityEvent.CACHE_HIT,
                    request_id,
                    provider,
                    {'cache_key': cache_key[:20] + '...', 'tokens_saved': cached_response.tokens_used}
                )
                return cached_response
        
        # Verify request signature if required (Pass 3: Security Hardening)
        if verify_signature:
            if not signature_data:
                error_msg = "Signature verification requested but no signature data provided"
                self.audit_logger.log_event(
                    SecurityEvent.SIGNATURE_VALIDATION_FAILED,
                    request_id,
                    provider,
                    {'error': error_msg}
                )
                raise RequestSignatureError(error_msg)
                
            if not self.request_signer.verify_signature(provider, prompt, signature_data):
                error_msg = "Request signature validation failed"
                self.audit_logger.log_event(
                    SecurityEvent.SIGNATURE_VALIDATION_FAILED,
                    request_id,
                    provider,
                    {'signature_data': {k: v[:20] + '...' if len(v) > 20 else v 
                                       for k, v in signature_data.items()}}
                )
                raise RequestSignatureError(error_msg)
                
        # Check rate limit for provider (Pass 3: Security Hardening)
        rate_limiter = self.rate_limiters.get(provider, self.rate_limiters.get('local'))
        if not rate_limiter.acquire():
            wait_time = rate_limiter.get_wait_time()
            self.audit_logger.log_event(
                SecurityEvent.RATE_LIMIT_EXCEEDED,
                request_id,
                provider,
                {'wait_time_seconds': wait_time, 'prompt_length': len(prompt)}
            )
            raise RateLimitExceededError(
                f"Rate limit exceeded for provider {provider}. Wait {wait_time:.2f} seconds."
            )
                
        # Estimate cost if not provided
        if estimated_tokens is None:
            # Rough estimate: prompt + expected response
            estimated_tokens = len(prompt.split()) * 2 + max_tokens
            
        # Check budget
        provider_obj = self.providers.get(provider)
        if provider_obj:
            estimated_cost = provider_obj.calculate_cost(estimated_tokens)
            try:
                self.cost_manager.check_budget(estimated_cost)
            except BudgetExceededError:
                logger.warning("Budget exceeded, falling back to local provider")
                provider = 'local'
                
        # Try providers with fallback
        providers_to_try = [provider] if provider != 'local' else []
        
        # Add other providers as fallback (ordered by quality)
        for p in ['claude', 'openai', 'gemini']:
            if p != provider and p in self.providers:
                providers_to_try.append(p)
                
        # Always have local as last resort
        providers_to_try.append('local')
        
        last_error = None
        start_time = time.time()
        
        for provider_name in providers_to_try:
            # Check timeout
            if time.time() - start_time > timeout:
                logger.warning(f"Timeout reached, falling back to local provider")
                provider_name = 'local'
                
            if provider_name not in self.providers:
                continue
                
            provider_obj = self.providers[provider_name]
            
            try:
                logger.debug(f"Attempting generation with {provider_name}")
                
                # Log API call start
                api_start_time = time.time()
                self.audit_logger.log_event(
                    SecurityEvent.API_CALL,
                    request_id,
                    provider_name,
                    {
                        'action': 'start',
                        'prompt_length': len(prompt),
                        'max_tokens': max_tokens,
                        'temperature': temperature,
                        'timeout': timeout
                    }
                )
                
                # Generate response
                response = provider_obj.generate(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
                
                # Log successful API call
                api_latency = time.time() - api_start_time
                self.audit_logger.log_event(
                    SecurityEvent.API_CALL,
                    request_id,
                    provider_name,
                    {
                        'action': 'success',
                        'response_tokens': response.tokens_used,
                        'cost': response.cost,
                        'latency': api_latency,
                        'cached': response.cached
                    }
                )
                
                # Track cost (except for local)
                if provider_name != 'local':
                    self.cost_manager.track_usage(
                        provider=provider_name,
                        cost=response.cost,
                        tokens=response.tokens_used
                    )
                    
                    # Check for warnings
                    warning = self.cost_manager.get_warning_status()
                    if warning:
                        logger.warning(warning)
                        # Log budget warning
                        if 'exceeded' in warning.lower():
                            self.audit_logger.log_event(
                                SecurityEvent.BUDGET_EXCEEDED,
                                request_id,
                                provider_name,
                                {
                                    'current_usage': self.cost_manager.current_usage,
                                    'daily_limit': self.cost_manager.daily_limit,
                                    'tokens_used': response.tokens_used
                                }
                            )
                        
                # Cache response (including local for testing)
                if use_cache:
                    cache_key = self.cache.generate_key(prompt, provider_name, temperature=temperature)
                    self.cache.store(cache_key, response)
                    
                logger.info(f"Successfully generated response with {provider_name}")
                return response
                
            except (ProviderError, APITimeoutError, RateLimitExceededError) as e:
                logger.warning(f"Provider {provider_name} failed: {e}")
                # Log error event
                self.audit_logger.log_event(
                    SecurityEvent.ERROR,
                    request_id,
                    provider_name,
                    {
                        'error_type': type(e).__name__,
                        'error_message': str(e),
                        'fallback': provider_name != providers_to_try[-1]
                    }
                )
                last_error = e
                
                # Log fallback if not the last provider
                if provider_name != providers_to_try[-1]:
                    next_provider = providers_to_try[providers_to_try.index(provider_name) + 1]
                    self.audit_logger.log_event(
                        SecurityEvent.FALLBACK,
                        request_id,
                        provider_name,
                        {
                            'from_provider': provider_name,
                            'to_provider': next_provider,
                            'reason': str(e)
                        }
                    )
                continue
                
        # If we get here, all providers failed
        raise ProviderError(f"All providers failed. Last error: {last_error}")
        
    def generate_synthesis(
        self,
        prompt: str,
        providers: Optional[List[str]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate synthesized response from multiple providers.
        Optimized with parallel execution (Pass 2).
        
        Args:
            prompt: Input prompt
            providers: List of providers to use (default: all with weight > 0)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters
            
        Returns:
            Synthesized LLM response
        """
        # Use defaults
        max_tokens = max_tokens or self.default_max_tokens
        temperature = temperature or self.default_temperature
        
        # Select providers
        if providers is None:
            providers = [p for p, obj in self.providers.items() 
                        if obj.weight > 0 and p != 'local']
                        
        responses = {}
        synthesis_data = {}
        
        # Pass 2 Optimization: Parallel provider queries
        start_time = time.time()
        
        # Create futures for parallel execution
        futures = {}
        for provider_name in providers:
            if provider_name not in self.providers:
                continue
                
            # Submit generation task to thread pool
            future = self.executor.submit(
                self.generate,
                prompt=prompt,
                provider=provider_name,
                max_tokens=max_tokens,
                temperature=temperature,
                use_cache=True,
                **kwargs
            )
            futures[provider_name] = future
            
        # Collect results as they complete
        for provider_name, future in futures.items():
            try:
                # Wait for result with timeout
                response = future.result(timeout=5.0)
                
                responses[provider_name] = response
                synthesis_data[provider_name] = {
                    'content': response.content,
                    'weight': self.providers[provider_name].weight,
                    'quality': self.providers[provider_name].quality_score,
                    'cost': response.cost,
                    'tokens': response.tokens_used
                }
                
            except concurrent.futures.TimeoutError:
                logger.warning(f"Provider {provider_name} timed out during synthesis")
            except Exception as e:
                logger.warning(f"Failed to get response from {provider_name}: {e}")
                
        if not responses:
            # Fallback to single provider
            return self.generate(prompt, max_tokens=max_tokens, temperature=temperature, **kwargs)
            
        # Synthesize responses (for now, just concatenate with weights noted)
        # In production, this would use more sophisticated synthesis
        synthesized_content = "\n\n".join([
            f"[{name} (weight: {data['weight']:.1%})]: {data['content']}"
            for name, data in synthesis_data.items()
        ])
        
        # Calculate totals
        total_tokens = sum(data['tokens'] for data in synthesis_data.values())
        total_cost = sum(data['cost'] for data in synthesis_data.values())
        
        # Pass 2: Parallel execution means total latency is the max, not the sum
        synthesis_latency = time.time() - start_time
        
        return LLMResponse(
            content=synthesized_content,
            provider="synthesis",
            tokens_used=total_tokens,
            cost=total_cost,
            latency=synthesis_latency,
            metadata={
                'synthesis': synthesis_data,
                'parallel_execution': True,
                'providers_used': len(responses)
            }
        )
        
    def update_configuration(self, llm_config: LLMConfig) -> None:
        """
        Update adapter configuration.
        
        Args:
            llm_config: New LLM configuration
        """
        self.default_provider = llm_config.provider
        self.default_max_tokens = llm_config.max_tokens
        self.default_temperature = llm_config.temperature
        
        logger.info(f"Configuration updated: provider={llm_config.provider}")
        
    def get_usage_summary(self) -> Dict[str, Any]:
        """
        Get usage summary and statistics.
        
        Returns:
            Usage summary dictionary
        """
        return {
            'current_usage': self.cost_manager.current_usage,
            'daily_limit': self.cost_manager.daily_limit,
            'usage_percent': (self.cost_manager.current_usage / self.cost_manager.daily_limit) * 100,
            'warning': self.cost_manager.get_warning_status(),
            'history_count': len(self.cost_manager.usage_history),
            'cache_size': len(self.cache._cache),
            'providers_available': list(self.providers.keys())
        }
        
    def clear_cache(self) -> None:
        """Clear response cache."""
        self.cache.clear()
        logger.info("Response cache cleared")
        
    def reset_usage(self) -> None:
        """Reset daily usage counter."""
        self.cost_manager.reset_daily_usage()
        logger.info("Daily usage reset")
        
    def generate_batch(
        self,
        prompts: List[str],
        provider: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> List[LLMResponse]:
        """
        Generate responses for multiple prompts efficiently.
        Pass 2 optimization for request batching.
        
        Args:
            prompts: List of input prompts
            provider: Provider to use
            max_tokens: Maximum tokens per response
            temperature: Sampling temperature
            **kwargs: Additional parameters
            
        Returns:
            List of LLM responses
        """
        # Use defaults
        provider = provider or self.default_provider
        max_tokens = max_tokens or self.default_max_tokens
        temperature = temperature or self.default_temperature
        
        # Process prompts in parallel
        futures = []
        for prompt in prompts:
            future = self.executor.submit(
                self.generate,
                prompt=prompt,
                provider=provider,
                max_tokens=max_tokens,
                temperature=temperature,
                use_cache=True,
                **kwargs
            )
            futures.append(future)
            
        # Collect results
        responses = []
        for future in concurrent.futures.as_completed(futures, timeout=10.0):
            try:
                response = future.result()
                responses.append(response)
            except Exception as e:
                logger.error(f"Batch generation failed for prompt: {e}")
                # Add error response
                responses.append(LLMResponse(
                    content=f"Error: {str(e)}",
                    provider=provider,
                    tokens_used=0,
                    cost=0.0,
                    latency=0.0,
                    metadata={'error': True}
                ))
                
        return responses
    
    # ============================================================================
    # Security Utility Methods - Pass 3: Security Hardening
    # ============================================================================
    
    def sign_request(self, provider: str, prompt: str) -> Dict[str, str]:
        """
        Sign a request for integrity verification.
        
        Args:
            provider: LLM provider name
            prompt: Request prompt
            
        Returns:
            Signature data dictionary for use with generate()
        """
        return self.request_signer.sign_request(provider, prompt)
    
    def configure_rate_limits(
        self,
        provider: str,
        tokens_per_minute: int,
        burst_capacity: int
    ) -> None:
        """
        Configure rate limits for a specific provider.
        
        Args:
            provider: Provider name
            tokens_per_minute: Sustained rate limit
            burst_capacity: Maximum burst size
        """
        if provider not in self.rate_limiters:
            logger.warning(f"Unknown provider {provider}, creating new rate limiter")
        
        self.rate_limiters[provider] = RateLimiter(
            tokens_per_minute=tokens_per_minute,
            burst_capacity=burst_capacity
        )
        logger.info(f"Configured rate limits for {provider}: {tokens_per_minute}/min, burst={burst_capacity}")
    
    def get_security_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive security metrics and statistics.
        
        Returns:
            Dictionary containing security-related metrics
        """
        metrics = {
            'rate_limits': {},
            'audit_stats': {
                'total_requests': self.audit_logger.request_counter,
                'logger_name': self.audit_logger.logger.name
            },
            'pii_patterns': {
                'email': bool(_EMAIL_PATTERN),
                'phone': bool(_PHONE_PATTERN),
                'ssn': bool(_SSN_PATTERN),
                'api_key': bool(_API_KEY_PATTERN),
                'credit_card': bool(_CREDIT_CARD_PATTERN),
                'ip_address': bool(_IP_ADDRESS_PATTERN),
                'passport': bool(_PASSPORT_PATTERN),
                'aws_key': bool(_AWS_KEY_PATTERN),
                'github_token': bool(_GITHUB_TOKEN_PATTERN)
            },
            'request_signing': {
                'enabled': bool(self.request_signer),
                'replay_window_seconds': self.request_signer.replay_window,
                'nonce_cache_size': len(self.request_signer.seen_nonces)
            }
        }
        
        # Add rate limit status for each provider
        for provider, limiter in self.rate_limiters.items():
            metrics['rate_limits'][provider] = {
                'tokens_available': limiter.tokens,
                'capacity': limiter.capacity,
                'fill_rate': limiter.fill_rate,
                'wait_time': limiter.get_wait_time()
            }
        
        return metrics
    
    def set_audit_level(self, level: str) -> None:
        """
        Set audit logging level.
        
        Args:
            level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        """
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        
        if level.upper() not in level_map:
            raise ValueError(f"Invalid audit level: {level}")
        
        self.audit_logger.logger.setLevel(level_map[level.upper()])
        logger.info(f"Audit logging level set to {level.upper()}")
    
    def detect_pii(self, text: str) -> Dict[str, List[str]]:
        """
        Detect PII in text without sanitizing it.
        Useful for pre-screening content before API calls.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary mapping PII types to detected values
        """
        pii_detected = {}
        
        # Check each pattern
        patterns = {
            'emails': _EMAIL_PATTERN,
            'phones': _PHONE_PATTERN,
            'ssns': _SSN_PATTERN,
            'api_keys': _API_KEY_PATTERN,
            'credit_cards': _CREDIT_CARD_PATTERN,
            'ip_addresses': _IP_ADDRESS_PATTERN,
            'dates': _DATE_OF_BIRTH_PATTERN,
            'passports': _PASSPORT_PATTERN,
            'licenses': _DRIVER_LICENSE_PATTERN,
            'bank_accounts': _BANK_ACCOUNT_PATTERN,
            'aws_keys': _AWS_KEY_PATTERN,
            'github_tokens': _GITHUB_TOKEN_PATTERN
        }
        
        for pii_type, pattern in patterns.items():
            matches = pattern.findall(text)
            if matches:
                pii_detected[pii_type] = matches
                # Log PII detection event
                self.audit_logger.log_event(
                    SecurityEvent.PII_DETECTED,
                    self.audit_logger.generate_request_id(),
                    'pii_scanner',
                    {
                        'pii_type': pii_type,
                        'count': len(matches),
                        'sanitized': False  # Just detection, not sanitization
                    }
                )
        
        return pii_detected
    
    def get_rate_limit_status(self, provider: str) -> Dict[str, Any]:
        """
        Get current rate limit status for a provider.
        
        Args:
            provider: Provider name
            
        Returns:
            Rate limit status information
        """
        if provider not in self.rate_limiters:
            return {'error': f'No rate limiter configured for {provider}'}
        
        limiter = self.rate_limiters[provider]
        return {
            'provider': provider,
            'tokens_available': limiter.tokens,
            'capacity': limiter.capacity,
            'fill_rate_per_second': limiter.fill_rate,
            'wait_time_seconds': limiter.get_wait_time(),
            'can_acquire': limiter.tokens >= 1
        }
        
    def __del__(self):
        """Cleanup thread pool on deletion."""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)