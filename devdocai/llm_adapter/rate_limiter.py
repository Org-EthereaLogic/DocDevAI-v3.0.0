"""
M008: Rate Limiting and DDoS Protection Module.

Implements multi-level rate limiting with token bucket algorithm,
circuit breakers, and intelligent throttling for DDoS protection.
"""

import asyncio
import time
import logging
from typing import Dict, Optional, Tuple, List, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import hashlib
import json

logger = logging.getLogger(__name__)


class RateLimitLevel(Enum):
    """Rate limiting levels."""
    USER = "user"              # Per-user limits
    PROVIDER = "provider"      # Per-provider limits  
    GLOBAL = "global"          # System-wide limits
    IP = "ip"                  # Per-IP address limits
    API_KEY = "api_key"        # Per-API key limits


class ThrottleStrategy(Enum):
    """Throttling strategies."""
    TOKEN_BUCKET = "token_bucket"      # Classic token bucket algorithm
    SLIDING_WINDOW = "sliding_window"  # Sliding window counter
    LEAKY_BUCKET = "leaky_bucket"      # Leaky bucket algorithm
    ADAPTIVE = "adaptive"              # Adaptive based on load


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    # Token bucket settings
    tokens_per_second: float = 10.0
    burst_size: int = 50
    
    # Per-level limits (requests per minute)
    user_rpm: int = 60
    provider_rpm: int = 500
    global_rpm: int = 1000
    ip_rpm: int = 30
    api_key_rpm: int = 100
    
    # DDoS protection
    max_concurrent_requests: int = 100
    suspicious_activity_threshold: int = 10  # Failed attempts before blocking
    block_duration_minutes: int = 15
    
    # Adaptive throttling
    enable_adaptive: bool = True
    target_latency_ms: float = 1000.0
    min_tokens_per_second: float = 1.0
    max_tokens_per_second: float = 100.0


@dataclass
class RateLimitStatus:
    """Current rate limit status."""
    allowed: bool
    tokens_remaining: float
    reset_time: datetime
    retry_after_seconds: Optional[float] = None
    reason: Optional[str] = None
    level: Optional[RateLimitLevel] = None


@dataclass
class TokenBucket:
    """Token bucket implementation for rate limiting."""
    capacity: float
    tokens: float
    refill_rate: float
    last_refill: float = field(default_factory=time.time)
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Attempt to consume tokens from bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Add tokens based on refill rate
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    @property
    def available_tokens(self) -> float:
        """Get current available tokens."""
        self._refill()
        return self.tokens


class SlidingWindow:
    """Sliding window counter for rate limiting."""
    
    def __init__(self, window_size_seconds: int, max_requests: int):
        """
        Initialize sliding window.
        
        Args:
            window_size_seconds: Size of the window in seconds
            max_requests: Maximum requests allowed in window
        """
        self.window_size = window_size_seconds
        self.max_requests = max_requests
        self.requests: deque = deque()
    
    def allow_request(self) -> bool:
        """Check if request is allowed."""
        now = time.time()
        
        # Remove old requests outside window
        while self.requests and self.requests[0] <= now - self.window_size:
            self.requests.popleft()
        
        # Check if under limit
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        
        return False
    
    @property
    def requests_in_window(self) -> int:
        """Get current number of requests in window."""
        now = time.time()
        
        # Remove old requests
        while self.requests and self.requests[0] <= now - self.window_size:
            self.requests.popleft()
        
        return len(self.requests)


class RateLimiter:
    """
    Multi-level rate limiter with DDoS protection.
    
    Implements:
    - Token bucket algorithm for smooth rate limiting
    - Per-user, per-provider, and global limits
    - DDoS detection and mitigation
    - Adaptive throttling based on system load
    - Circuit breaker pattern for cascading failure prevention
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        """
        Initialize rate limiter.
        
        Args:
            config: Rate limiting configuration
        """
        self.config = config or RateLimitConfig()
        self.logger = logging.getLogger(f"{__name__}.RateLimiter")
        
        # Token buckets for different levels
        self.buckets: Dict[str, TokenBucket] = {}
        self._init_buckets()
        
        # Sliding windows for additional protection
        self.windows: Dict[str, SlidingWindow] = {}
        self._init_windows()
        
        # Blocked entities (IPs, users, etc.)
        self.blocked: Dict[str, datetime] = {}
        
        # Failed attempt tracking for DDoS detection
        self.failed_attempts: Dict[str, List[datetime]] = defaultdict(list)
        
        # Concurrent request tracking
        self.concurrent_requests: Dict[str, int] = defaultdict(int)
        
        # Metrics for adaptive throttling
        self.request_latencies: deque = deque(maxlen=100)
        self.last_adjustment = time.time()
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
        
    def _init_buckets(self):
        """Initialize token buckets for each level."""
        # Global bucket
        self.buckets['global'] = TokenBucket(
            capacity=self.config.burst_size,
            tokens=self.config.burst_size,
            refill_rate=self.config.tokens_per_second
        )
        
        # Provider buckets (initialized on demand)
        # User buckets (initialized on demand)
        
    def _init_windows(self):
        """Initialize sliding windows."""
        # Global sliding window
        self.windows['global'] = SlidingWindow(
            window_size_seconds=60,
            max_requests=self.config.global_rpm
        )
    
    async def check_rate_limit(
        self,
        identifier: str,
        level: RateLimitLevel = RateLimitLevel.USER,
        tokens: int = 1,
        provider: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> RateLimitStatus:
        """
        Check if request is allowed under rate limits.
        
        Args:
            identifier: Unique identifier (user_id, api_key, etc.)
            level: Rate limit level to check
            tokens: Number of tokens to consume
            provider: LLM provider name
            ip_address: Client IP address
            
        Returns:
            RateLimitStatus with allow/deny decision
        """
        async with self._lock:
            # Check if blocked
            if self._is_blocked(identifier):
                block_until = self.blocked.get(identifier)
                retry_after = (block_until - datetime.utcnow()).total_seconds()
                return RateLimitStatus(
                    allowed=False,
                    tokens_remaining=0,
                    reset_time=block_until,
                    retry_after_seconds=retry_after,
                    reason=f"Blocked due to suspicious activity until {block_until}",
                    level=level
                )
            
            # Check concurrent request limit
            if not self._check_concurrent_limit(identifier):
                return RateLimitStatus(
                    allowed=False,
                    tokens_remaining=0,
                    reset_time=datetime.utcnow() + timedelta(seconds=1),
                    retry_after_seconds=1.0,
                    reason="Concurrent request limit exceeded",
                    level=level
                )
            
            # Get or create bucket for identifier
            bucket_key = f"{level.value}:{identifier}"
            if bucket_key not in self.buckets:
                self._create_bucket(bucket_key, level)
            
            bucket = self.buckets[bucket_key]
            
            # Check token bucket
            if not bucket.consume(tokens):
                # Calculate retry time
                tokens_needed = tokens - bucket.available_tokens
                retry_after = tokens_needed / bucket.refill_rate
                
                # Track failed attempt
                self._track_failed_attempt(identifier)
                
                return RateLimitStatus(
                    allowed=False,
                    tokens_remaining=bucket.available_tokens,
                    reset_time=datetime.utcnow() + timedelta(seconds=retry_after),
                    retry_after_seconds=retry_after,
                    reason=f"Rate limit exceeded for {level.value}",
                    level=level
                )
            
            # Check sliding window (additional protection)
            window_key = f"{level.value}:{identifier}"
            if window_key not in self.windows:
                self._create_window(window_key, level)
            
            window = self.windows[window_key]
            if not window.allow_request():
                # Track failed attempt
                self._track_failed_attempt(identifier)
                
                return RateLimitStatus(
                    allowed=False,
                    tokens_remaining=bucket.available_tokens,
                    reset_time=datetime.utcnow() + timedelta(seconds=60),
                    retry_after_seconds=60.0,
                    reason=f"Request rate too high for {level.value}",
                    level=level
                )
            
            # Check global limits
            if level != RateLimitLevel.GLOBAL:
                global_status = await self.check_rate_limit(
                    'global',
                    RateLimitLevel.GLOBAL,
                    tokens
                )
                if not global_status.allowed:
                    return global_status
            
            # Adaptive throttling
            if self.config.enable_adaptive:
                await self._adaptive_throttle()
            
            # Increment concurrent requests
            self.concurrent_requests[identifier] += 1
            
            return RateLimitStatus(
                allowed=True,
                tokens_remaining=bucket.available_tokens,
                reset_time=datetime.utcnow() + timedelta(seconds=1/bucket.refill_rate),
                level=level
            )
    
    async def release_request(self, identifier: str):
        """
        Release a concurrent request slot.
        
        Args:
            identifier: Request identifier
        """
        async with self._lock:
            if identifier in self.concurrent_requests:
                self.concurrent_requests[identifier] = max(
                    0, 
                    self.concurrent_requests[identifier] - 1
                )
    
    def _create_bucket(self, key: str, level: RateLimitLevel):
        """Create a new token bucket for the given key."""
        # Determine capacity and rate based on level
        if level == RateLimitLevel.USER:
            rate = self.config.user_rpm / 60.0
            capacity = self.config.user_rpm
        elif level == RateLimitLevel.PROVIDER:
            rate = self.config.provider_rpm / 60.0
            capacity = self.config.provider_rpm
        elif level == RateLimitLevel.IP:
            rate = self.config.ip_rpm / 60.0
            capacity = self.config.ip_rpm
        elif level == RateLimitLevel.API_KEY:
            rate = self.config.api_key_rpm / 60.0
            capacity = self.config.api_key_rpm
        else:
            rate = self.config.tokens_per_second
            capacity = self.config.burst_size
        
        self.buckets[key] = TokenBucket(
            capacity=capacity,
            tokens=capacity,
            refill_rate=rate
        )
    
    def _create_window(self, key: str, level: RateLimitLevel):
        """Create a new sliding window for the given key."""
        # Determine window size and max requests based on level
        if level == RateLimitLevel.USER:
            max_requests = self.config.user_rpm
        elif level == RateLimitLevel.PROVIDER:
            max_requests = self.config.provider_rpm
        elif level == RateLimitLevel.IP:
            max_requests = self.config.ip_rpm
        elif level == RateLimitLevel.API_KEY:
            max_requests = self.config.api_key_rpm
        else:
            max_requests = self.config.global_rpm
        
        self.windows[key] = SlidingWindow(
            window_size_seconds=60,
            max_requests=max_requests
        )
    
    def _is_blocked(self, identifier: str) -> bool:
        """Check if identifier is blocked."""
        if identifier in self.blocked:
            block_until = self.blocked[identifier]
            if datetime.utcnow() < block_until:
                return True
            else:
                # Unblock if time has passed
                del self.blocked[identifier]
                if identifier in self.failed_attempts:
                    del self.failed_attempts[identifier]
        return False
    
    def _check_concurrent_limit(self, identifier: str) -> bool:
        """Check if under concurrent request limit."""
        return self.concurrent_requests[identifier] < self.config.max_concurrent_requests
    
    def _track_failed_attempt(self, identifier: str):
        """Track failed attempt for DDoS detection."""
        now = datetime.utcnow()
        
        # Add to failed attempts
        self.failed_attempts[identifier].append(now)
        
        # Clean old attempts (outside 1 minute window)
        cutoff = now - timedelta(minutes=1)
        self.failed_attempts[identifier] = [
            attempt for attempt in self.failed_attempts[identifier]
            if attempt > cutoff
        ]
        
        # Check if should block
        if len(self.failed_attempts[identifier]) >= self.config.suspicious_activity_threshold:
            # Block the identifier
            self.blocked[identifier] = now + timedelta(
                minutes=self.config.block_duration_minutes
            )
            self.logger.warning(
                f"Blocked {identifier} due to {len(self.failed_attempts[identifier])} "
                f"failed attempts in 1 minute"
            )
    
    async def _adaptive_throttle(self):
        """Adaptive throttling based on system load."""
        now = time.time()
        
        # Only adjust every 10 seconds
        if now - self.last_adjustment < 10:
            return
        
        if not self.request_latencies:
            return
        
        # Calculate average latency
        avg_latency = sum(self.request_latencies) / len(self.request_latencies)
        
        # Adjust token rate based on latency
        if avg_latency > self.config.target_latency_ms * 1.5:
            # System under stress - reduce rate
            for bucket in self.buckets.values():
                bucket.refill_rate = max(
                    self.config.min_tokens_per_second,
                    bucket.refill_rate * 0.9
                )
            self.logger.info(f"Reduced rate limit due to high latency: {avg_latency:.0f}ms")
            
        elif avg_latency < self.config.target_latency_ms * 0.5:
            # System has capacity - increase rate
            for bucket in self.buckets.values():
                bucket.refill_rate = min(
                    self.config.max_tokens_per_second,
                    bucket.refill_rate * 1.1
                )
            self.logger.debug(f"Increased rate limit due to low latency: {avg_latency:.0f}ms")
        
        self.last_adjustment = now
    
    def record_latency(self, latency_ms: float):
        """
        Record request latency for adaptive throttling.
        
        Args:
            latency_ms: Request latency in milliseconds
        """
        self.request_latencies.append(latency_ms)
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current rate limiter metrics.
        
        Returns:
            Dictionary of metrics
        """
        metrics = {
            'blocked_count': len(self.blocked),
            'concurrent_requests': sum(self.concurrent_requests.values()),
            'buckets': {},
            'windows': {},
            'avg_latency_ms': None
        }
        
        # Bucket metrics
        for key, bucket in self.buckets.items():
            metrics['buckets'][key] = {
                'available_tokens': bucket.available_tokens,
                'capacity': bucket.capacity,
                'refill_rate': bucket.refill_rate
            }
        
        # Window metrics
        for key, window in self.windows.items():
            metrics['windows'][key] = {
                'requests_in_window': window.requests_in_window,
                'max_requests': window.max_requests
            }
        
        # Average latency
        if self.request_latencies:
            metrics['avg_latency_ms'] = sum(self.request_latencies) / len(self.request_latencies)
        
        return metrics
    
    async def reset_limits(self, identifier: Optional[str] = None):
        """
        Reset rate limits.
        
        Args:
            identifier: Specific identifier to reset, or None for all
        """
        async with self._lock:
            if identifier:
                # Reset specific identifier
                keys_to_remove = [
                    k for k in self.buckets.keys() 
                    if identifier in k
                ]
                for key in keys_to_remove:
                    del self.buckets[key]
                
                keys_to_remove = [
                    k for k in self.windows.keys()
                    if identifier in k
                ]
                for key in keys_to_remove:
                    del self.windows[key]
                
                if identifier in self.blocked:
                    del self.blocked[identifier]
                if identifier in self.failed_attempts:
                    del self.failed_attempts[identifier]
                if identifier in self.concurrent_requests:
                    del self.concurrent_requests[identifier]
            else:
                # Reset everything
                self._init_buckets()
                self._init_windows()
                self.blocked.clear()
                self.failed_attempts.clear()
                self.concurrent_requests.clear()
                self.request_latencies.clear()
            
            self.logger.info(f"Reset rate limits for: {identifier or 'all'}")


class CircuitBreaker:
    """
    Circuit breaker pattern for cascading failure prevention.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds before attempting recovery
            expected_exception: Exception type to catch
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open
        
        self.logger = logging.getLogger(f"{__name__}.CircuitBreaker")
    
    async def call(self, func, *args, **kwargs):
        """
        Call function through circuit breaker.
        
        Args:
            func: Async function to call
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half_open"
                self.logger.info("Circuit breaker entering half-open state")
            else:
                raise Exception(f"Circuit breaker is open (failures: {self.failure_count})")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if should attempt to reset circuit."""
        if self.last_failure_time is None:
            return False
        
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful call."""
        if self.state == "half_open":
            self.logger.info("Circuit breaker reset to closed state")
        
        self.failure_count = 0
        self.state = "closed"
        self.last_failure_time = None
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            self.logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures"
            )
        elif self.state == "half_open":
            self.state = "open"
            self.logger.warning("Circuit breaker reopened from half-open state")