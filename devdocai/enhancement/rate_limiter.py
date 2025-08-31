"""
M009: Multi-Level Rate Limiting System.

Implements comprehensive rate limiting with token bucket algorithm,
circuit breaker pattern, and multi-level protection (user, IP, cost, global).
Provides DDoS protection and resource exhaustion prevention.
"""

import time
import asyncio
import logging
import threading
from typing import Dict, List, Optional, Any, Tuple, Set, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque
import json
import hashlib
import secrets

logger = logging.getLogger(__name__)


class RateLimitLevel(Enum):
    """Rate limiting levels."""
    USER = "user"           # Per-user limits
    IP = "ip"               # Per-IP address limits
    COST = "cost"           # Cost-based limits
    GLOBAL = "global"       # Global system limits
    OPERATION = "operation" # Per-operation type limits


class RateLimitStatus(Enum):
    """Rate limit check results."""
    ALLOWED = "allowed"
    RATE_LIMITED = "rate_limited"
    CIRCUIT_OPEN = "circuit_open"
    QUOTA_EXCEEDED = "quota_exceeded"
    BLOCKED = "blocked"


class LimitType(Enum):
    """Types of rate limits."""
    REQUESTS_PER_MINUTE = "requests_per_minute"
    REQUESTS_PER_HOUR = "requests_per_hour"
    REQUESTS_PER_DAY = "requests_per_day"
    COST_PER_HOUR = "cost_per_hour"
    COST_PER_DAY = "cost_per_day"
    CONCURRENT_REQUESTS = "concurrent_requests"
    BANDWIDTH_PER_MINUTE = "bandwidth_per_minute"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    
    # User-level limits
    user_requests_per_minute: int = 100
    user_requests_per_hour: int = 1000
    user_requests_per_day: int = 10000
    user_cost_per_hour: float = 5.0
    user_cost_per_day: float = 50.0
    user_concurrent_requests: int = 10
    
    # IP-level limits (more restrictive)
    ip_requests_per_minute: int = 200
    ip_requests_per_hour: int = 2000
    ip_requests_per_day: int = 20000
    ip_concurrent_requests: int = 20
    ip_bandwidth_per_minute: int = 10485760  # 10MB
    
    # Global system limits
    global_requests_per_minute: int = 10000
    global_requests_per_hour: int = 100000
    global_concurrent_requests: int = 500
    global_cost_per_hour: float = 1000.0
    
    # Operation-specific limits
    operation_limits: Dict[str, Dict[str, int]] = field(default_factory=lambda: {
        "enhance_document": {
            "requests_per_minute": 50,
            "requests_per_hour": 500
        },
        "enhance_batch": {
            "requests_per_minute": 10,
            "requests_per_hour": 100
        },
        "enhance_stream": {
            "requests_per_minute": 20,
            "requests_per_hour": 200
        }
    })
    
    # Token bucket parameters
    bucket_size: int = 100
    refill_rate: float = 10.0  # tokens per second
    
    # Circuit breaker parameters
    circuit_failure_threshold: int = 10
    circuit_timeout_seconds: int = 60
    circuit_half_open_timeout: int = 30
    
    # Sliding window parameters
    sliding_window_size: int = 60  # seconds
    
    # Burst protection
    enable_burst_protection: bool = True
    burst_threshold_multiplier: float = 1.5
    burst_penalty_seconds: int = 300
    
    # Advanced features
    enable_adaptive_limits: bool = False
    enable_whitelist: bool = True
    enable_blacklist: bool = True
    
    # Monitoring
    enable_rate_limit_logging: bool = True
    log_violations: bool = True
    
    @classmethod
    def for_security_mode(cls, mode: str) -> 'RateLimitConfig':
        """Get configuration for specific security mode."""
        configs = {
            "BASIC": cls(
                user_requests_per_minute=200,
                ip_requests_per_minute=500,
                global_requests_per_minute=20000,
                enable_burst_protection=False
            ),
            "STANDARD": cls(),  # Use defaults
            "STRICT": cls(
                user_requests_per_minute=50,
                user_requests_per_hour=500,
                user_concurrent_requests=5,
                ip_requests_per_minute=100,
                ip_requests_per_hour=1000,
                global_requests_per_minute=5000,
                enable_burst_protection=True,
                burst_penalty_seconds=600
            ),
            "PARANOID": cls(
                user_requests_per_minute=20,
                user_requests_per_hour=200,
                user_requests_per_day=2000,
                user_concurrent_requests=3,
                ip_requests_per_minute=50,
                ip_requests_per_hour=500,
                ip_requests_per_day=5000,
                global_requests_per_minute=2000,
                enable_burst_protection=True,
                burst_penalty_seconds=900,
                circuit_failure_threshold=5
            )
        }
        return configs.get(mode, cls())


class TokenBucket:
    """Thread-safe token bucket implementation."""
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.
        
        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_update = time.time()
        self._lock = threading.Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Attempt to consume tokens.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        with self._lock:
            current_time = time.time()
            time_delta = current_time - self.last_update
            
            # Add tokens based on refill rate
            self.tokens = min(
                self.capacity,
                self.tokens + (time_delta * self.refill_rate)
            )
            self.last_update = current_time
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False
    
    def get_available_tokens(self) -> int:
        """Get current number of available tokens."""
        with self._lock:
            current_time = time.time()
            time_delta = current_time - self.last_update
            
            self.tokens = min(
                self.capacity,
                self.tokens + (time_delta * self.refill_rate)
            )
            self.last_update = current_time
            
            return int(self.tokens)
    
    def reset(self) -> None:
        """Reset bucket to full capacity."""
        with self._lock:
            self.tokens = float(self.capacity)
            self.last_update = time.time()


class SlidingWindow:
    """Sliding window rate limiter."""
    
    def __init__(self, window_size: int, max_requests: int):
        """
        Initialize sliding window.
        
        Args:
            window_size: Window size in seconds
            max_requests: Maximum requests in window
        """
        self.window_size = window_size
        self.max_requests = max_requests
        self.requests = deque()
        self._lock = threading.Lock()
    
    def is_allowed(self, current_time: Optional[float] = None) -> bool:
        """
        Check if request is allowed.
        
        Args:
            current_time: Current timestamp (uses time.time() if None)
            
        Returns:
            True if allowed, False if rate limited
        """
        current_time = current_time or time.time()
        
        with self._lock:
            # Remove old requests outside window
            cutoff_time = current_time - self.window_size
            while self.requests and self.requests[0] <= cutoff_time:
                self.requests.popleft()
            
            # Check if under limit
            if len(self.requests) < self.max_requests:
                self.requests.append(current_time)
                return True
            
            return False
    
    def get_request_count(self, current_time: Optional[float] = None) -> int:
        """Get current request count in window."""
        current_time = current_time or time.time()
        
        with self._lock:
            cutoff_time = current_time - self.window_size
            while self.requests and self.requests[0] <= cutoff_time:
                self.requests.popleft()
            
            return len(self.requests)


class CircuitBreaker:
    """Circuit breaker for handling failures."""
    
    def __init__(
        self,
        failure_threshold: int = 10,
        timeout: int = 60,
        half_open_timeout: int = 30
    ):
        """Initialize circuit breaker."""
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.half_open_timeout = half_open_timeout
        
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()
    
    def call_allowed(self) -> bool:
        """Check if calls are allowed through circuit."""
        current_time = time.time()
        
        with self._lock:
            if self.state == "CLOSED":
                return True
            elif self.state == "OPEN":
                if current_time - self.last_failure_time > self.timeout:
                    self.state = "HALF_OPEN"
                    return True
                return False
            else:  # HALF_OPEN
                return True
    
    def record_success(self) -> None:
        """Record successful operation."""
        with self._lock:
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
    
    def record_failure(self) -> None:
        """Record failed operation."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"


@dataclass
class RateLimitResult:
    """Result of rate limit check."""
    
    status: RateLimitStatus
    allowed: bool
    limit_level: Optional[RateLimitLevel] = None
    remaining: Optional[int] = None
    reset_time: Optional[datetime] = None
    retry_after: Optional[int] = None
    violated_limits: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MultiLevelRateLimiter:
    """
    Multi-level rate limiter with comprehensive protection.
    
    Implements user, IP, cost, and global rate limiting with
    token bucket algorithm, sliding windows, and circuit breakers.
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        """Initialize multi-level rate limiter."""
        self.config = config or RateLimitConfig()
        
        # Token buckets by level and identifier
        self.user_buckets: Dict[str, TokenBucket] = {}
        self.ip_buckets: Dict[str, TokenBucket] = {}
        self.global_bucket = TokenBucket(
            self.config.bucket_size * 10,  # Larger global bucket
            self.config.refill_rate * 5    # Faster refill
        )
        
        # Sliding windows for different time periods
        self.user_windows: Dict[str, Dict[str, SlidingWindow]] = defaultdict(dict)
        self.ip_windows: Dict[str, Dict[str, SlidingWindow]] = defaultdict(dict)
        self.global_windows: Dict[str, SlidingWindow] = {}
        
        # Circuit breakers by user/IP
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # Cost tracking
        self.user_costs: Dict[str, Dict[str, float]] = defaultdict(dict)  # user -> {period -> cost}
        self.global_costs: Dict[str, float] = {}  # period -> cost
        
        # Concurrent request tracking
        self.concurrent_requests: Dict[str, int] = defaultdict(int)
        self.global_concurrent = 0
        
        # Whitelist/blacklist
        self.whitelisted_ips: Set[str] = set()
        self.blacklisted_ips: Set[str] = set()
        self.whitelisted_users: Set[str] = set()
        self.blacklisted_users: Set[str] = set()
        
        # Burst protection
        self.burst_penalties: Dict[str, datetime] = {}  # identifier -> penalty_end_time
        
        # Metrics
        self.request_count = 0
        self.blocked_count = 0
        self.limit_violations: Dict[str, int] = defaultdict(int)
        
        # Threading
        self._lock = threading.Lock()
        
        # Initialize global windows
        self._init_global_windows()
        
        logger.info("Multi-level rate limiter initialized")
    
    def _init_global_windows(self) -> None:
        """Initialize global sliding windows."""
        self.global_windows = {
            "minute": SlidingWindow(60, self.config.global_requests_per_minute),
            "hour": SlidingWindow(3600, self.config.global_requests_per_hour),
        }
    
    async def check_limits(
        self,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        operation: str = "default",
        cost: float = 0.0,
        content_size: int = 0
    ) -> RateLimitResult:
        """
        Check rate limits across all levels.
        
        Args:
            user_id: User identifier
            ip_address: IP address
            operation: Operation type
            cost: Operation cost
            content_size: Content size in bytes
            
        Returns:
            RateLimitResult with decision and metadata
        """
        current_time = time.time()
        violated_limits = []
        metadata = {}
        
        try:
            # Increment request count
            self.request_count += 1
            
            # Check blacklists first
            if ip_address and ip_address in self.blacklisted_ips:
                return RateLimitResult(
                    status=RateLimitStatus.BLOCKED,
                    allowed=False,
                    violated_limits=["ip_blacklisted"],
                    metadata={"reason": "IP blacklisted"}
                )
            
            if user_id and user_id in self.blacklisted_users:
                return RateLimitResult(
                    status=RateLimitStatus.BLOCKED,
                    allowed=False,
                    violated_limits=["user_blacklisted"],
                    metadata={"reason": "User blacklisted"}
                )
            
            # Check whitelists (bypass other limits)
            if ((ip_address and ip_address in self.whitelisted_ips) or
                (user_id and user_id in self.whitelisted_users)):
                return RateLimitResult(
                    status=RateLimitStatus.ALLOWED,
                    allowed=True,
                    metadata={"reason": "Whitelisted"}
                )
            
            # Check burst penalties
            penalty_key = user_id or ip_address
            if penalty_key and penalty_key in self.burst_penalties:
                if datetime.now() < self.burst_penalties[penalty_key]:
                    return RateLimitResult(
                        status=RateLimitStatus.BLOCKED,
                        allowed=False,
                        violated_limits=["burst_penalty"],
                        metadata={"reason": "Burst penalty active"}
                    )
                else:
                    # Penalty expired
                    del self.burst_penalties[penalty_key]
            
            # Check circuit breakers
            circuit_key = user_id or ip_address or "global"
            if circuit_key in self.circuit_breakers:
                if not self.circuit_breakers[circuit_key].call_allowed():
                    return RateLimitResult(
                        status=RateLimitStatus.CIRCUIT_OPEN,
                        allowed=False,
                        violated_limits=["circuit_breaker"],
                        metadata={"reason": "Circuit breaker open"}
                    )
            
            # 1. Global limits check
            global_result = self._check_global_limits(current_time)
            if not global_result["allowed"]:
                violated_limits.extend(global_result["violations"])
                metadata.update(global_result["metadata"])
            
            # 2. User limits check
            if user_id:
                user_result = self._check_user_limits(user_id, current_time, cost, operation)
                if not user_result["allowed"]:
                    violated_limits.extend(user_result["violations"])
                    metadata.update(user_result["metadata"])
            
            # 3. IP limits check
            if ip_address:
                ip_result = self._check_ip_limits(ip_address, current_time, content_size)
                if not ip_result["allowed"]:
                    violated_limits.extend(ip_result["violations"])
                    metadata.update(ip_result["metadata"])
            
            # 4. Concurrent requests check
            concurrent_result = self._check_concurrent_limits(user_id, ip_address)
            if not concurrent_result["allowed"]:
                violated_limits.extend(concurrent_result["violations"])
                metadata.update(concurrent_result["metadata"])
            
            # Determine final result
            if violated_limits:
                self.blocked_count += 1
                
                # Update violation counts
                for violation in violated_limits:
                    self.limit_violations[violation] += 1
                
                # Apply burst penalties if enabled
                if (self.config.enable_burst_protection and 
                    penalty_key and len(violated_limits) >= 2):
                    penalty_end = datetime.now() + timedelta(seconds=self.config.burst_penalty_seconds)
                    self.burst_penalties[penalty_key] = penalty_end
                    violated_limits.append("burst_penalty_applied")
                
                # Record failure in circuit breaker
                if circuit_key in self.circuit_breakers:
                    self.circuit_breakers[circuit_key].record_failure()
                elif penalty_key:
                    self.circuit_breakers[penalty_key] = CircuitBreaker(
                        self.config.circuit_failure_threshold,
                        self.config.circuit_timeout_seconds,
                        self.config.circuit_half_open_timeout
                    )
                    self.circuit_breakers[penalty_key].record_failure()
                
                if self.config.log_violations:
                    logger.warning(f"Rate limit violations: {violated_limits} for user={user_id}, ip={ip_address}")
                
                return RateLimitResult(
                    status=RateLimitStatus.RATE_LIMITED,
                    allowed=False,
                    violated_limits=violated_limits,
                    metadata=metadata
                )
            else:
                # Request allowed - record success
                if circuit_key in self.circuit_breakers:
                    self.circuit_breakers[circuit_key].record_success()
                
                # Track concurrent requests
                if user_id:
                    self.concurrent_requests[f"user:{user_id}"] += 1
                if ip_address:
                    self.concurrent_requests[f"ip:{ip_address}"] += 1
                self.global_concurrent += 1
                
                return RateLimitResult(
                    status=RateLimitStatus.ALLOWED,
                    allowed=True,
                    metadata=metadata
                )
        
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Fail secure - deny request
            return RateLimitResult(
                status=RateLimitStatus.BLOCKED,
                allowed=False,
                violated_limits=["internal_error"],
                metadata={"error": str(e)}
            )
    
    def _check_global_limits(self, current_time: float) -> Dict[str, Any]:
        """Check global system limits."""
        violations = []
        metadata = {}
        
        # Global token bucket
        if not self.global_bucket.consume(1):
            violations.append("global_token_bucket")
        
        # Global sliding windows
        for period, window in self.global_windows.items():
            if not window.is_allowed(current_time):
                violations.append(f"global_{period}")
                metadata[f"global_{period}_requests"] = window.get_request_count(current_time)
        
        return {
            "allowed": len(violations) == 0,
            "violations": violations,
            "metadata": metadata
        }
    
    def _check_user_limits(
        self,
        user_id: str,
        current_time: float,
        cost: float,
        operation: str
    ) -> Dict[str, Any]:
        """Check user-specific limits."""
        violations = []
        metadata = {}
        
        # User token bucket
        if user_id not in self.user_buckets:
            self.user_buckets[user_id] = TokenBucket(
                self.config.bucket_size,
                self.config.refill_rate
            )
        
        if not self.user_buckets[user_id].consume(1):
            violations.append("user_token_bucket")
        
        # User sliding windows
        if user_id not in self.user_windows:
            self.user_windows[user_id] = {
                "minute": SlidingWindow(60, self.config.user_requests_per_minute),
                "hour": SlidingWindow(3600, self.config.user_requests_per_hour),
                "day": SlidingWindow(86400, self.config.user_requests_per_day),
            }
        
        for period, window in self.user_windows[user_id].items():
            if not window.is_allowed(current_time):
                violations.append(f"user_{period}")
                metadata[f"user_{period}_requests"] = window.get_request_count(current_time)
        
        # Cost limits
        if cost > 0:
            current_hour = int(current_time // 3600)
            current_day = int(current_time // 86400)
            
            # Initialize cost tracking
            if f"hour_{current_hour}" not in self.user_costs[user_id]:
                self.user_costs[user_id][f"hour_{current_hour}"] = 0.0
            if f"day_{current_day}" not in self.user_costs[user_id]:
                self.user_costs[user_id][f"day_{current_day}"] = 0.0
            
            # Check limits
            hourly_cost = self.user_costs[user_id][f"hour_{current_hour}"] + cost
            daily_cost = self.user_costs[user_id][f"day_{current_day}"] + cost
            
            if hourly_cost > self.config.user_cost_per_hour:
                violations.append("user_cost_hourly")
                metadata["user_hourly_cost"] = hourly_cost
            
            if daily_cost > self.config.user_cost_per_day:
                violations.append("user_cost_daily")
                metadata["user_daily_cost"] = daily_cost
            
            # Update costs if allowed
            if not violations:
                self.user_costs[user_id][f"hour_{current_hour}"] = hourly_cost
                self.user_costs[user_id][f"day_{current_day}"] = daily_cost
        
        # Operation-specific limits
        if operation in self.config.operation_limits:
            op_limits = self.config.operation_limits[operation]
            
            if user_id not in self.user_windows:
                self.user_windows[user_id] = {}
            
            for limit_type, limit_value in op_limits.items():
                if limit_type == "requests_per_minute":
                    op_key = f"{operation}_minute"
                    if op_key not in self.user_windows[user_id]:
                        self.user_windows[user_id][op_key] = SlidingWindow(60, limit_value)
                    
                    if not self.user_windows[user_id][op_key].is_allowed(current_time):
                        violations.append(f"user_operation_{operation}_minute")
                
                elif limit_type == "requests_per_hour":
                    op_key = f"{operation}_hour"
                    if op_key not in self.user_windows[user_id]:
                        self.user_windows[user_id][op_key] = SlidingWindow(3600, limit_value)
                    
                    if not self.user_windows[user_id][op_key].is_allowed(current_time):
                        violations.append(f"user_operation_{operation}_hour")
        
        return {
            "allowed": len(violations) == 0,
            "violations": violations,
            "metadata": metadata
        }
    
    def _check_ip_limits(
        self,
        ip_address: str,
        current_time: float,
        content_size: int
    ) -> Dict[str, Any]:
        """Check IP-specific limits."""
        violations = []
        metadata = {}
        
        # IP token bucket
        if ip_address not in self.ip_buckets:
            self.ip_buckets[ip_address] = TokenBucket(
                self.config.bucket_size,
                self.config.refill_rate
            )
        
        if not self.ip_buckets[ip_address].consume(1):
            violations.append("ip_token_bucket")
        
        # IP sliding windows
        if ip_address not in self.ip_windows:
            self.ip_windows[ip_address] = {
                "minute": SlidingWindow(60, self.config.ip_requests_per_minute),
                "hour": SlidingWindow(3600, self.config.ip_requests_per_hour),
                "day": SlidingWindow(86400, self.config.ip_requests_per_day),
            }
        
        for period, window in self.ip_windows[ip_address].items():
            if not window.is_allowed(current_time):
                violations.append(f"ip_{period}")
                metadata[f"ip_{period}_requests"] = window.get_request_count(current_time)
        
        # Bandwidth limits (simplified)
        if content_size > 0:
            bandwidth_key = f"bandwidth_{int(current_time // 60)}"  # Per minute
            if bandwidth_key not in metadata:
                metadata[bandwidth_key] = content_size
            else:
                metadata[bandwidth_key] += content_size
            
            if metadata[bandwidth_key] > self.config.ip_bandwidth_per_minute:
                violations.append("ip_bandwidth")
        
        return {
            "allowed": len(violations) == 0,
            "violations": violations,
            "metadata": metadata
        }
    
    def _check_concurrent_limits(
        self,
        user_id: Optional[str],
        ip_address: Optional[str]
    ) -> Dict[str, Any]:
        """Check concurrent request limits."""
        violations = []
        metadata = {}
        
        # Global concurrent limit
        if self.global_concurrent >= self.config.global_concurrent_requests:
            violations.append("global_concurrent")
            metadata["global_concurrent"] = self.global_concurrent
        
        # User concurrent limit
        if user_id:
            user_concurrent = self.concurrent_requests.get(f"user:{user_id}", 0)
            if user_concurrent >= self.config.user_concurrent_requests:
                violations.append("user_concurrent")
                metadata["user_concurrent"] = user_concurrent
        
        # IP concurrent limit
        if ip_address:
            ip_concurrent = self.concurrent_requests.get(f"ip:{ip_address}", 0)
            if ip_concurrent >= self.config.ip_concurrent_requests:
                violations.append("ip_concurrent")
                metadata["ip_concurrent"] = ip_concurrent
        
        return {
            "allowed": len(violations) == 0,
            "violations": violations,
            "metadata": metadata
        }
    
    def release_request(
        self,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> None:
        """Release a request from concurrent tracking."""
        with self._lock:
            if user_id and f"user:{user_id}" in self.concurrent_requests:
                self.concurrent_requests[f"user:{user_id}"] -= 1
                if self.concurrent_requests[f"user:{user_id}"] <= 0:
                    del self.concurrent_requests[f"user:{user_id}"]
            
            if ip_address and f"ip:{ip_address}" in self.concurrent_requests:
                self.concurrent_requests[f"ip:{ip_address}"] -= 1
                if self.concurrent_requests[f"ip:{ip_address}"] <= 0:
                    del self.concurrent_requests[f"ip:{ip_address}"]
            
            if self.global_concurrent > 0:
                self.global_concurrent -= 1
    
    def add_to_whitelist(self, identifier: str, type_: str = "ip") -> None:
        """Add identifier to whitelist."""
        if type_ == "ip":
            self.whitelisted_ips.add(identifier)
        elif type_ == "user":
            self.whitelisted_users.add(identifier)
        
        logger.info(f"Added {identifier} to {type_} whitelist")
    
    def add_to_blacklist(self, identifier: str, type_: str = "ip") -> None:
        """Add identifier to blacklist."""
        if type_ == "ip":
            self.blacklisted_ips.add(identifier)
        elif type_ == "user":
            self.blacklisted_users.add(identifier)
        
        logger.warning(f"Added {identifier} to {type_} blacklist")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiting statistics."""
        return {
            "request_count": self.request_count,
            "blocked_count": self.blocked_count,
            "block_rate": self.blocked_count / max(self.request_count, 1),
            "active_users": len(self.user_buckets),
            "active_ips": len(self.ip_buckets),
            "active_circuits": len(self.circuit_breakers),
            "concurrent_requests": self.global_concurrent,
            "limit_violations": dict(self.limit_violations),
            "whitelisted_ips": len(self.whitelisted_ips),
            "blacklisted_ips": len(self.blacklisted_ips),
            "burst_penalties": len(self.burst_penalties)
        }
    
    def reset_stats(self) -> None:
        """Reset statistics."""
        self.request_count = 0
        self.blocked_count = 0
        self.limit_violations.clear()
        logger.info("Rate limiter statistics reset")


def create_rate_limiter(security_mode: str = "STANDARD") -> MultiLevelRateLimiter:
    """
    Factory function to create rate limiter.
    
    Args:
        security_mode: Security mode (BASIC, STANDARD, STRICT, PARANOID)
        
    Returns:
        Configured MultiLevelRateLimiter
    """
    config = RateLimitConfig.for_security_mode(security_mode)
    return MultiLevelRateLimiter(config)