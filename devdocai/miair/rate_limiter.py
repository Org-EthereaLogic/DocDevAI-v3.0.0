"""
Rate limiting for MIAIR Engine to prevent DoS and resource exhaustion.

Implements token bucket algorithm with per-operation and per-client limits.
"""

import time
import threading
import logging
from typing import Dict, Optional, Tuple, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from functools import wraps
import hashlib
import json

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    # Global limits (requests per minute)
    global_rate_limit: int = 10000
    global_burst_size: int = 100
    
    # Per-operation limits (requests per minute)
    analyze_rate_limit: int = 1000
    optimize_rate_limit: int = 100
    batch_rate_limit: int = 50
    
    # Per-client limits
    per_client_rate_limit: int = 100
    per_client_burst_size: int = 10
    
    # Time windows
    window_size_seconds: int = 60
    cleanup_interval_seconds: int = 300
    
    # Behavior
    block_on_limit: bool = True
    log_violations: bool = True
    adaptive_limits: bool = True
    
    # Resource limits
    max_concurrent_operations: int = 50
    max_queue_size: int = 1000


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""
    capacity: int
    refill_rate: float  # tokens per second
    tokens: float = field(default_factory=float)
    last_refill: float = field(default_factory=time.time)
    lock: threading.Lock = field(default_factory=threading.Lock)
    
    def __post_init__(self):
        """Initialize with full capacity."""
        self.tokens = float(self.capacity)
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from bucket.
        
        Returns:
            True if tokens were available, False otherwise
        """
        with self.lock:
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
    
    def available_tokens(self) -> int:
        """Get current available tokens."""
        with self.lock:
            self._refill()
            return int(self.tokens)
    
    def time_until_available(self, tokens: int = 1) -> float:
        """Calculate time until tokens will be available."""
        with self.lock:
            self._refill()
            
            if self.tokens >= tokens:
                return 0.0
            
            tokens_needed = tokens - self.tokens
            return tokens_needed / self.refill_rate


@dataclass
class RateLimitStats:
    """Statistics for rate limiting."""
    total_requests: int = 0
    allowed_requests: int = 0
    blocked_requests: int = 0
    current_rate: float = 0.0
    peak_rate: float = 0.0
    unique_clients: int = 0
    violations: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'total_requests': self.total_requests,
            'allowed_requests': self.allowed_requests,
            'blocked_requests': self.blocked_requests,
            'block_rate': self.blocked_requests / max(self.total_requests, 1),
            'current_rate_per_min': self.current_rate * 60,
            'peak_rate_per_min': self.peak_rate * 60,
            'unique_clients': self.unique_clients,
            'recent_violations': self.violations[-10:]  # Last 10 violations
        }


class RateLimiter:
    """
    Advanced rate limiter for MIAIR Engine.
    
    Features:
    - Token bucket algorithm for smooth rate limiting
    - Per-operation and per-client limits
    - Adaptive limits based on system load
    - Automatic cleanup of old tracking data
    - Thread-safe concurrent access
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        """Initialize rate limiter."""
        self.config = config or RateLimitConfig()
        
        # Global token bucket
        self.global_bucket = TokenBucket(
            capacity=self.config.global_burst_size,
            refill_rate=self.config.global_rate_limit / 60.0
        )
        
        # Per-operation buckets
        self.operation_buckets = {
            'analyze': TokenBucket(
                capacity=self.config.analyze_rate_limit // 6,  # 10-second burst
                refill_rate=self.config.analyze_rate_limit / 60.0
            ),
            'optimize': TokenBucket(
                capacity=self.config.optimize_rate_limit // 6,
                refill_rate=self.config.optimize_rate_limit / 60.0
            ),
            'batch': TokenBucket(
                capacity=self.config.batch_rate_limit // 6,
                refill_rate=self.config.batch_rate_limit / 60.0
            )
        }
        
        # Per-client tracking
        self.client_buckets: Dict[str, TokenBucket] = {}
        self.client_last_seen: Dict[str, float] = {}
        
        # Request tracking for sliding window
        self.request_windows: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Concurrent operations tracking
        self.active_operations = 0
        self.operation_lock = threading.Lock()
        
        # Statistics
        self.stats = RateLimitStats()
        self.stats_lock = threading.Lock()
        
        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        
        logger.info("Rate limiter initialized with global limit: %d/min", 
                   self.config.global_rate_limit)
    
    def check_rate_limit(self,
                         operation: str = 'analyze',
                         client_id: Optional[str] = None,
                         tokens: int = 1) -> Tuple[bool, Optional[str]]:
        """
        Check if operation is within rate limits.
        
        Args:
            operation: Type of operation (analyze, optimize, batch)
            client_id: Unique client identifier
            tokens: Number of tokens to consume
            
        Returns:
            Tuple of (allowed, reason_if_blocked)
        """
        with self.stats_lock:
            self.stats.total_requests += 1
        
        # Check concurrent operations limit
        if not self._check_concurrent_limit():
            return False, "Maximum concurrent operations exceeded"
        
        # Check global rate limit
        if not self.global_bucket.consume(tokens):
            self._record_violation('global', client_id, operation)
            return False, "Global rate limit exceeded"
        
        # Check operation-specific limit
        if operation in self.operation_buckets:
            if not self.operation_buckets[operation].consume(tokens):
                self._record_violation('operation', client_id, operation)
                # Return tokens to global bucket
                self.global_bucket.tokens += tokens
                return False, f"Operation rate limit exceeded for {operation}"
        
        # Check per-client limit
        if client_id:
            if not self._check_client_limit(client_id, tokens):
                self._record_violation('client', client_id, operation)
                # Return tokens to global and operation buckets
                self.global_bucket.tokens += tokens
                if operation in self.operation_buckets:
                    self.operation_buckets[operation].tokens += tokens
                return False, f"Client rate limit exceeded"
        
        # Update statistics
        with self.stats_lock:
            self.stats.allowed_requests += 1
            self._update_rate_stats(operation, client_id)
        
        return True, None
    
    def _check_concurrent_limit(self) -> bool:
        """Check concurrent operations limit."""
        with self.operation_lock:
            if self.active_operations >= self.config.max_concurrent_operations:
                return False
            self.active_operations += 1
            return True
    
    def release_operation(self):
        """Release an active operation slot."""
        with self.operation_lock:
            self.active_operations = max(0, self.active_operations - 1)
    
    def _check_client_limit(self, client_id: str, tokens: int) -> bool:
        """Check per-client rate limit."""
        # Get or create client bucket
        if client_id not in self.client_buckets:
            self.client_buckets[client_id] = TokenBucket(
                capacity=self.config.per_client_burst_size,
                refill_rate=self.config.per_client_rate_limit / 60.0
            )
        
        # Update last seen time
        self.client_last_seen[client_id] = time.time()
        
        # Check limit
        return self.client_buckets[client_id].consume(tokens)
    
    def _update_rate_stats(self, operation: str, client_id: Optional[str]):
        """Update rate statistics."""
        now = time.time()
        
        # Track request in sliding window
        window_key = f"{operation}_{client_id or 'global'}"
        self.request_windows[window_key].append(now)
        
        # Calculate current rate
        window_start = now - self.config.window_size_seconds
        recent_requests = [t for t in self.request_windows[window_key] if t > window_start]
        current_rate = len(recent_requests) / self.config.window_size_seconds
        
        self.stats.current_rate = current_rate
        self.stats.peak_rate = max(self.stats.peak_rate, current_rate)
        
        if client_id:
            self.stats.unique_clients = len(self.client_buckets)
    
    def _record_violation(self, violation_type: str, client_id: Optional[str], operation: str):
        """Record rate limit violation."""
        with self.stats_lock:
            self.stats.blocked_requests += 1
            
            violation = {
                'timestamp': datetime.now().isoformat(),
                'type': violation_type,
                'client_id': client_id,
                'operation': operation
            }
            
            self.stats.violations.append(violation)
            
            # Keep only recent violations
            if len(self.stats.violations) > 1000:
                self.stats.violations = self.stats.violations[-1000:]
        
        if self.config.log_violations:
            logger.warning(f"Rate limit violation: {violation}")
    
    def _cleanup_loop(self):
        """Periodically clean up old client data."""
        while True:
            time.sleep(self.config.cleanup_interval_seconds)
            self._cleanup_old_clients()
    
    def _cleanup_old_clients(self):
        """Remove old client tracking data."""
        now = time.time()
        cutoff = now - (self.config.window_size_seconds * 10)  # 10 windows
        
        clients_to_remove = [
            client_id for client_id, last_seen in self.client_last_seen.items()
            if last_seen < cutoff
        ]
        
        for client_id in clients_to_remove:
            del self.client_buckets[client_id]
            del self.client_last_seen[client_id]
        
        if clients_to_remove:
            logger.info(f"Cleaned up {len(clients_to_remove)} old client entries")
    
    def wait_if_limited(self,
                       operation: str = 'analyze',
                       client_id: Optional[str] = None,
                       max_wait: float = 5.0) -> bool:
        """
        Wait if rate limited, up to max_wait seconds.
        
        Returns:
            True if proceeded, False if timed out waiting
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            allowed, reason = self.check_rate_limit(operation, client_id)
            if allowed:
                return True
            
            # Calculate wait time
            wait_time = 0.1  # Default wait
            
            # Check how long until tokens available
            if operation in self.operation_buckets:
                wait_time = max(wait_time, 
                               self.operation_buckets[operation].time_until_available())
            
            # Don't wait longer than remaining time
            remaining_time = max_wait - (time.time() - start_time)
            wait_time = min(wait_time, remaining_time)
            
            if wait_time > 0:
                time.sleep(wait_time)
        
        return False
    
    def get_limits_info(self, operation: str = None, client_id: str = None) -> Dict[str, Any]:
        """Get current rate limit information."""
        info = {
            'global': {
                'limit_per_min': self.config.global_rate_limit,
                'available_tokens': self.global_bucket.available_tokens(),
                'capacity': self.config.global_burst_size
            },
            'operations': {},
            'concurrent': {
                'active': self.active_operations,
                'limit': self.config.max_concurrent_operations
            }
        }
        
        # Add operation-specific info
        for op_name, bucket in self.operation_buckets.items():
            if operation is None or op_name == operation:
                info['operations'][op_name] = {
                    'limit_per_min': getattr(self.config, f"{op_name}_rate_limit"),
                    'available_tokens': bucket.available_tokens(),
                    'time_until_available': bucket.time_until_available()
                }
        
        # Add client-specific info
        if client_id and client_id in self.client_buckets:
            bucket = self.client_buckets[client_id]
            info['client'] = {
                'id': client_id,
                'limit_per_min': self.config.per_client_rate_limit,
                'available_tokens': bucket.available_tokens(),
                'time_until_available': bucket.time_until_available()
            }
        
        return info
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiting statistics."""
        with self.stats_lock:
            return self.stats.to_dict()
    
    def reset_client(self, client_id: str):
        """Reset rate limits for specific client."""
        if client_id in self.client_buckets:
            del self.client_buckets[client_id]
            del self.client_last_seen[client_id]
            logger.info(f"Reset rate limits for client: {client_id}")
    
    def adjust_limits(self, factor: float = 1.0):
        """Dynamically adjust rate limits."""
        if not self.config.adaptive_limits:
            return
        
        # Adjust global limit
        new_rate = int(self.config.global_rate_limit * factor)
        self.global_bucket.refill_rate = new_rate / 60.0
        
        # Adjust operation limits
        for operation in self.operation_buckets:
            old_limit = getattr(self.config, f"{operation}_rate_limit")
            new_limit = int(old_limit * factor)
            self.operation_buckets[operation].refill_rate = new_limit / 60.0
        
        logger.info(f"Adjusted rate limits by factor {factor}")


def rate_limited(operation: str = 'analyze', 
                 wait: bool = True,
                 max_wait: float = 5.0):
    """
    Decorator for rate limiting functions.
    
    Args:
        operation: Type of operation
        wait: Whether to wait if rate limited
        max_wait: Maximum time to wait
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Get client_id from kwargs or args
            client_id = kwargs.get('document_id') or kwargs.get('client_id')
            
            # Get rate limiter from self if available
            limiter = getattr(self, 'rate_limiter', None)
            if not limiter:
                # No rate limiter, proceed without limiting
                return func(self, *args, **kwargs)
            
            # Check rate limit
            if wait:
                if not limiter.wait_if_limited(operation, client_id, max_wait):
                    raise RateLimitExceeded(
                        f"Rate limit exceeded for {operation} after waiting {max_wait}s"
                    )
            else:
                allowed, reason = limiter.check_rate_limit(operation, client_id)
                if not allowed:
                    raise RateLimitExceeded(reason)
            
            try:
                # Execute function
                return func(self, *args, **kwargs)
            finally:
                # Release operation slot
                limiter.release_operation()
        
        return wrapper
    return decorator


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    pass


# Global rate limiter instance
_default_limiter = None


def get_limiter(config: Optional[RateLimitConfig] = None) -> RateLimiter:
    """Get or create default rate limiter instance."""
    global _default_limiter
    
    if _default_limiter is None or config is not None:
        _default_limiter = RateLimiter(config)
    
    return _default_limiter