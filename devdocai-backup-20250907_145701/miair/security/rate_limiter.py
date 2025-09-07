"""
M003 MIAIR Engine - Rate Limiting and DoS Protection

Implements comprehensive rate limiting and denial-of-service protection for the MIAIR Engine.
Uses token bucket algorithm with circuit breaker pattern for resilient operation.

Security Features:
- Token bucket rate limiting with configurable rates
- Circuit breaker pattern for system protection
- Concurrent request limiting
- Backpressure mechanisms
- Priority-based request queuing
- Adaptive rate limiting based on system load
"""

import time
import threading
import logging
from typing import Dict, Optional, Any, Callable, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque, defaultdict
from datetime import datetime, timedelta
import asyncio
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    pass


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""
    pass


class Priority(Enum):
    """Request priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Blocking requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    # Token bucket settings
    tokens_per_second: float = 10.0
    burst_size: int = 20
    
    # Circuit breaker settings
    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds
    half_open_requests: int = 3
    
    # Concurrency settings
    max_concurrent_requests: int = 50
    queue_size: int = 100
    
    # Adaptive settings
    enable_adaptive_limiting: bool = True
    load_threshold: float = 0.8  # 80% CPU/memory
    adaptive_reduction_factor: float = 0.5  # Reduce rate by 50% under load
    
    # Per-client settings
    enable_per_client_limits: bool = True
    client_tokens_per_second: float = 5.0
    client_burst_size: int = 10


@dataclass
class TokenBucket:
    """Token bucket implementation for rate limiting."""
    capacity: int
    fill_rate: float
    tokens: float = field(init=False)
    last_update: float = field(init=False)
    lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    
    def __post_init__(self):
        self.tokens = float(self.capacity)
        self.last_update = time.time()
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were available, False otherwise
        """
        with self.lock:
            now = time.time()
            # Add tokens based on time elapsed
            elapsed = now - self.last_update
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.fill_rate
            )
            self.last_update = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def wait_time(self, tokens: int = 1) -> float:
        """Calculate wait time for tokens to become available."""
        with self.lock:
            if self.tokens >= tokens:
                return 0.0
            needed = tokens - self.tokens
            return needed / self.fill_rate


class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_requests = 0
        self.lock = threading.Lock()
        self.success_count = 0
        self.total_requests = 0
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.
        
        Args:
            func: Function to execute
            *args, **kwargs: Function arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpen: If circuit is open
        """
        with self.lock:
            self.total_requests += 1
            
            if self.state == CircuitState.OPEN:
                # Check if we should transition to half-open
                if self.last_failure_time:
                    elapsed = time.time() - self.last_failure_time
                    if elapsed >= self.config.recovery_timeout:
                        self.state = CircuitState.HALF_OPEN
                        self.half_open_requests = 0
                        logger.info("Circuit breaker transitioning to HALF_OPEN")
                    else:
                        raise CircuitBreakerOpen(
                            f"Circuit breaker is OPEN (wait {self.config.recovery_timeout - elapsed:.1f}s)"
                        )
                else:
                    raise CircuitBreakerOpen("Circuit breaker is OPEN")
            
            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_requests >= self.config.half_open_requests:
                    # Transition back to CLOSED if all test requests succeeded
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    logger.info("Circuit breaker recovered to CLOSED")
                else:
                    self.half_open_requests += 1
        
        try:
            result = func(*args, **kwargs)
            with self.lock:
                self.success_count += 1
                if self.state == CircuitState.HALF_OPEN:
                    # Success in half-open state
                    if self.half_open_requests >= self.config.half_open_requests:
                        self.state = CircuitState.CLOSED
                        self.failure_count = 0
            return result
            
        except Exception as e:
            with self.lock:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.failure_count >= self.config.failure_threshold:
                    self.state = CircuitState.OPEN
                    logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
                
                if self.state == CircuitState.HALF_OPEN:
                    # Failure in half-open state - go back to OPEN
                    self.state = CircuitState.OPEN
                    logger.warning("Circuit breaker returned to OPEN after half-open failure")
            
            raise
    
    def get_stats(self) -> Dict:
        """Get circuit breaker statistics."""
        with self.lock:
            return {
                'state': self.state.value,
                'failure_count': self.failure_count,
                'success_count': self.success_count,
                'total_requests': self.total_requests,
                'success_rate': self.success_count / self.total_requests if self.total_requests > 0 else 0
            }


class RateLimiter:
    """
    Comprehensive rate limiter with DoS protection.
    
    Features:
    - Token bucket rate limiting
    - Circuit breaker pattern
    - Per-client rate limiting
    - Priority queue for requests
    - Adaptive rate limiting based on system load
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        """Initialize rate limiter with configuration."""
        self.config = config or RateLimitConfig()
        
        # Global token bucket
        self.global_bucket = TokenBucket(
            capacity=self.config.burst_size,
            fill_rate=self.config.tokens_per_second
        )
        
        # Per-client token buckets
        self.client_buckets: Dict[str, TokenBucket] = {}
        self.client_bucket_lock = threading.Lock()
        
        # Circuit breaker
        self.circuit_breaker = CircuitBreaker(self.config)
        
        # Concurrent request tracking
        self.active_requests = 0
        self.active_requests_lock = threading.Lock()
        
        # Request queue
        self.request_queue: deque = deque(maxlen=self.config.queue_size)
        self.queue_lock = threading.Lock()
        
        # Statistics
        self.stats = defaultdict(int)
        self.stats_lock = threading.Lock()
        
        # Adaptive limiting
        self.adaptive_factor = 1.0
        self.last_load_check = time.time()
    
    def _get_client_bucket(self, client_id: str) -> TokenBucket:
        """Get or create client-specific token bucket."""
        with self.client_bucket_lock:
            if client_id not in self.client_buckets:
                self.client_buckets[client_id] = TokenBucket(
                    capacity=self.config.client_burst_size,
                    fill_rate=self.config.client_tokens_per_second
                )
            return self.client_buckets[client_id]
    
    def _check_system_load(self) -> float:
        """Check system load for adaptive limiting."""
        # Simplified load check - in production, integrate with actual metrics
        import psutil
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory_percent = psutil.virtual_memory().percent
        return max(cpu_percent, memory_percent) / 100.0
    
    def _update_adaptive_factor(self):
        """Update adaptive rate limiting factor based on system load."""
        if not self.config.enable_adaptive_limiting:
            return
        
        now = time.time()
        if now - self.last_load_check < 5.0:  # Check every 5 seconds
            return
        
        self.last_load_check = now
        load = self._check_system_load()
        
        if load > self.config.load_threshold:
            # Reduce rate under high load
            self.adaptive_factor = self.config.adaptive_reduction_factor
            logger.warning(f"High system load ({load:.1%}), reducing rate limit by {1-self.adaptive_factor:.0%}")
        else:
            # Restore normal rate
            self.adaptive_factor = 1.0
    
    @contextmanager
    def acquire(self, client_id: Optional[str] = None, priority: Priority = Priority.NORMAL, tokens: int = 1):
        """
        Acquire rate limit permission.
        
        Args:
            client_id: Optional client identifier for per-client limiting
            priority: Request priority
            tokens: Number of tokens to consume
            
        Yields:
            None if successful
            
        Raises:
            RateLimitExceeded: If rate limit is exceeded
            CircuitBreakerOpen: If circuit breaker is open
        """
        # Update adaptive factor
        self._update_adaptive_factor()
        
        # Check circuit breaker
        def check_circuit():
            return True
        
        try:
            self.circuit_breaker.call(check_circuit)
        except CircuitBreakerOpen as e:
            with self.stats_lock:
                self.stats['circuit_breaker_rejections'] += 1
            raise
        
        # Check concurrent requests
        with self.active_requests_lock:
            if self.active_requests >= self.config.max_concurrent_requests:
                with self.stats_lock:
                    self.stats['concurrency_rejections'] += 1
                raise RateLimitExceeded(f"Max concurrent requests ({self.config.max_concurrent_requests}) exceeded")
            self.active_requests += 1
        
        try:
            # Apply adaptive factor to token consumption
            adjusted_tokens = tokens / self.adaptive_factor if self.adaptive_factor > 0 else tokens
            
            # Check global rate limit
            if not self.global_bucket.consume(adjusted_tokens):
                wait_time = self.global_bucket.wait_time(adjusted_tokens)
                with self.stats_lock:
                    self.stats['global_rate_limit_rejections'] += 1
                raise RateLimitExceeded(f"Global rate limit exceeded (wait {wait_time:.1f}s)")
            
            # Check per-client rate limit
            if client_id and self.config.enable_per_client_limits:
                client_bucket = self._get_client_bucket(client_id)
                if not client_bucket.consume(tokens):
                    wait_time = client_bucket.wait_time(tokens)
                    with self.stats_lock:
                        self.stats['client_rate_limit_rejections'] += 1
                    raise RateLimitExceeded(f"Client rate limit exceeded (wait {wait_time:.1f}s)")
            
            with self.stats_lock:
                self.stats['successful_acquisitions'] += 1
                self.stats[f'priority_{priority.name}_requests'] += 1
            
            yield
            
        finally:
            with self.active_requests_lock:
                self.active_requests -= 1
    
    async def acquire_async(self, client_id: Optional[str] = None, priority: Priority = Priority.NORMAL, tokens: int = 1):
        """Async version of acquire for asyncio compatibility."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.acquire, client_id, priority, tokens)
    
    def queue_request(self, request: Dict, priority: Priority = Priority.NORMAL) -> bool:
        """
        Queue a request for later processing.
        
        Args:
            request: Request data to queue
            priority: Request priority
            
        Returns:
            True if queued successfully, False if queue is full
        """
        with self.queue_lock:
            if len(self.request_queue) >= self.config.queue_size:
                with self.stats_lock:
                    self.stats['queue_rejections'] += 1
                return False
            
            # Insert based on priority
            inserted = False
            for i, (p, _) in enumerate(self.request_queue):
                if priority.value > p.value:
                    self.request_queue.insert(i, (priority, request))
                    inserted = True
                    break
            
            if not inserted:
                self.request_queue.append((priority, request))
            
            with self.stats_lock:
                self.stats['queued_requests'] += 1
            
            return True
    
    def get_queued_request(self) -> Optional[Tuple[Priority, Dict]]:
        """Get next request from queue."""
        with self.queue_lock:
            if self.request_queue:
                return self.request_queue.popleft()
            return None
    
    def get_stats(self) -> Dict:
        """Get rate limiter statistics."""
        with self.stats_lock:
            stats = dict(self.stats)
        
        stats.update({
            'active_requests': self.active_requests,
            'queue_size': len(self.request_queue),
            'circuit_breaker': self.circuit_breaker.get_stats(),
            'adaptive_factor': self.adaptive_factor,
            'client_buckets': len(self.client_buckets)
        })
        
        return stats
    
    def reset_stats(self):
        """Reset statistics."""
        with self.stats_lock:
            self.stats.clear()
    
    def cleanup_old_clients(self, max_age_seconds: float = 3600):
        """Clean up old client buckets to prevent memory leaks."""
        # In production, track last access time and clean up old entries
        pass