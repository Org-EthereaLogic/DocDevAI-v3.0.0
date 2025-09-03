"""
Rate Limiting and Cost Control for AI Document Generation.

Implements comprehensive rate limiting, cost controls, and abuse prevention
for LLM-based document generation to prevent financial damage and DoS attacks.

Security Features:
- Multi-level rate limiting (user, global, API)
- Token budget enforcement
- Cost tracking and alerts
- Circuit breakers for runaway requests
- Sliding window and token bucket algorithms
- DDoS protection
"""

import time
import logging
import json
from typing import Dict, Optional, List, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict
from enum import Enum
import threading
import hashlib

logger = logging.getLogger(__name__)


class RateLimitLevel(Enum):
    """Rate limit enforcement levels."""
    USER = "user"
    API = "api"
    GLOBAL = "global"
    IP = "ip"
    ORGANIZATION = "organization"


class LimitType(Enum):
    """Types of limits to enforce."""
    REQUESTS = "requests"
    TOKENS = "tokens"
    COST = "cost"
    DOCUMENTS = "documents"
    BANDWIDTH = "bandwidth"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    # Request limits
    requests_per_minute: int = 10
    requests_per_hour: int = 100
    requests_per_day: int = 500
    
    # Token limits
    tokens_per_minute: int = 10000
    tokens_per_hour: int = 100000
    tokens_per_day: int = 1000000
    
    # Cost limits (in USD)
    cost_per_hour: float = 1.0
    cost_per_day: float = 10.0
    cost_per_month: float = 200.0
    
    # Document limits
    documents_per_hour: int = 20
    documents_per_day: int = 100
    
    # Burst allowance (% over limit for short bursts)
    burst_allowance: float = 0.2  # 20% burst
    
    # Circuit breaker settings
    error_threshold: int = 5  # Errors before circuit break
    circuit_reset_time: int = 300  # Seconds to reset circuit
    
    # DDoS protection
    max_concurrent_requests: int = 5
    blacklist_threshold: int = 10  # Violations before blacklist
    blacklist_duration: int = 3600  # Seconds


@dataclass
class UsageMetrics:
    """Track usage metrics for rate limiting."""
    requests: int = 0
    tokens: int = 0
    cost: float = 0.0
    documents: int = 0
    errors: int = 0
    last_request: Optional[datetime] = None
    violations: int = 0


class TokenBucket:
    """
    Token bucket algorithm for smooth rate limiting.
    
    Allows controlled bursts while maintaining average rate.
    """
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.
        
        Args:
            capacity: Maximum tokens in bucket
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self._lock = threading.Lock()
        
    def consume(self, tokens: int = 1) -> bool:
        """
        Attempt to consume tokens from bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens available, False otherwise
        """
        with self._lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
            
    def _refill(self):
        """Refill bucket based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Add tokens based on refill rate
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
        
    def available_tokens(self) -> int:
        """Get current available tokens."""
        with self._lock:
            self._refill()
            return int(self.tokens)


class SlidingWindowCounter:
    """
    Sliding window counter for precise rate limiting.
    
    Tracks events in a sliding time window for accurate rate enforcement.
    """
    
    def __init__(self, window_size: int):
        """
        Initialize sliding window counter.
        
        Args:
            window_size: Window size in seconds
        """
        self.window_size = window_size
        self.events = deque()
        self._lock = threading.Lock()
        
    def add_event(self, count: int = 1) -> int:
        """
        Add event to window.
        
        Args:
            count: Event count to add
            
        Returns:
            Current count in window
        """
        with self._lock:
            now = time.time()
            self._cleanup(now)
            self.events.append((now, count))
            return self.get_count()
            
    def get_count(self) -> int:
        """Get current count in window."""
        with self._lock:
            self._cleanup(time.time())
            return sum(count for _, count in self.events)
            
    def _cleanup(self, now: float):
        """Remove events outside window."""
        cutoff = now - self.window_size
        while self.events and self.events[0][0] < cutoff:
            self.events.popleft()


class GenerationRateLimiter:
    """
    Comprehensive rate limiter for AI document generation.
    
    Features:
    - Multi-level rate limiting
    - Cost and token budget enforcement
    - Circuit breaker pattern
    - DDoS protection
    - Audit logging
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        """
        Initialize rate limiter.
        
        Args:
            config: Rate limit configuration
        """
        self.config = config or RateLimitConfig()
        
        # Initialize tracking structures
        self.user_metrics: Dict[str, UsageMetrics] = defaultdict(UsageMetrics)
        self.ip_metrics: Dict[str, UsageMetrics] = defaultdict(UsageMetrics)
        
        # Token buckets for different resources
        self._init_token_buckets()
        
        # Sliding windows for precise tracking
        self._init_sliding_windows()
        
        # Circuit breaker state
        self.circuit_breaker_state: Dict[str, Dict] = {}
        
        # Blacklist for repeat offenders
        self.blacklist: Dict[str, datetime] = {}
        
        # Global metrics
        self.global_metrics = UsageMetrics()
        
        # Lock for thread safety
        self._lock = threading.Lock()
        
    def _init_token_buckets(self):
        """Initialize token buckets for different rate limits."""
        self.buckets = {
            "requests_minute": TokenBucket(
                self.config.requests_per_minute,
                self.config.requests_per_minute / 60
            ),
            "tokens_minute": TokenBucket(
                self.config.tokens_per_minute,
                self.config.tokens_per_minute / 60
            ),
            "global_requests": TokenBucket(
                self.config.requests_per_hour,
                self.config.requests_per_hour / 3600
            ),
        }
        
    def _init_sliding_windows(self):
        """Initialize sliding window counters."""
        self.windows = {
            "requests_hour": defaultdict(lambda: SlidingWindowCounter(3600)),
            "requests_day": defaultdict(lambda: SlidingWindowCounter(86400)),
            "tokens_hour": defaultdict(lambda: SlidingWindowCounter(3600)),
            "tokens_day": defaultdict(lambda: SlidingWindowCounter(86400)),
            "cost_hour": defaultdict(lambda: SlidingWindowCounter(3600)),
            "cost_day": defaultdict(lambda: SlidingWindowCounter(86400)),
        }
        
    def check_limits(
        self,
        user_id: str,
        request_type: str = "document",
        estimated_tokens: int = 1000,
        estimated_cost: float = 0.1,
        ip_address: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        Check if request is within rate limits.
        
        Args:
            user_id: User identifier
            request_type: Type of request
            estimated_tokens: Estimated token usage
            estimated_cost: Estimated cost in USD
            ip_address: Client IP address
            
        Returns:
            Tuple of (allowed, reason, details)
        """
        with self._lock:
            # Check blacklist
            if self._is_blacklisted(user_id, ip_address):
                return False, "User or IP blacklisted", {"blacklisted": True}
                
            # Check circuit breaker
            if self._is_circuit_broken(user_id):
                return False, "Circuit breaker active", {"circuit_broken": True}
                
            # Check concurrent request limit
            if not self._check_concurrent_limit(user_id):
                return False, "Concurrent request limit exceeded", {
                    "max_concurrent": self.config.max_concurrent_requests
                }
                
            # Check various rate limits
            checks = [
                self._check_request_limits(user_id),
                self._check_token_limits(user_id, estimated_tokens),
                self._check_cost_limits(user_id, estimated_cost),
                self._check_document_limits(user_id, request_type),
            ]
            
            # Check IP-based limits if provided
            if ip_address:
                checks.append(self._check_ip_limits(ip_address))
                
            # Aggregate check results
            for allowed, reason, details in checks:
                if not allowed:
                    # Record violation
                    self._record_violation(user_id, ip_address)
                    return False, reason, details
                    
            # All checks passed
            return True, None, {"limits_remaining": self._get_remaining_limits(user_id)}
            
    def _check_request_limits(self, user_id: str) -> Tuple[bool, Optional[str], Dict]:
        """Check request-based rate limits."""
        # Per-minute limit (token bucket)
        if not self.buckets["requests_minute"].consume():
            return False, "Requests per minute limit exceeded", {
                "limit": self.config.requests_per_minute,
                "window": "minute"
            }
            
        # Per-hour limit (sliding window)
        hour_count = self.windows["requests_hour"][user_id].add_event()
        if hour_count > self.config.requests_per_hour:
            return False, "Requests per hour limit exceeded", {
                "limit": self.config.requests_per_hour,
                "current": hour_count,
                "window": "hour"
            }
            
        # Per-day limit (sliding window)
        day_count = self.windows["requests_day"][user_id].add_event()
        if day_count > self.config.requests_per_day:
            return False, "Requests per day limit exceeded", {
                "limit": self.config.requests_per_day,
                "current": day_count,
                "window": "day"
            }
            
        return True, None, {}
        
    def _check_token_limits(self, user_id: str, tokens: int) -> Tuple[bool, Optional[str], Dict]:
        """Check token-based rate limits."""
        # Per-minute token limit
        if not self.buckets["tokens_minute"].consume(tokens):
            return False, "Tokens per minute limit exceeded", {
                "limit": self.config.tokens_per_minute,
                "requested": tokens,
                "window": "minute"
            }
            
        # Per-hour token limit
        hour_tokens = self.windows["tokens_hour"][user_id].add_event(tokens)
        if hour_tokens > self.config.tokens_per_hour:
            return False, "Tokens per hour limit exceeded", {
                "limit": self.config.tokens_per_hour,
                "current": hour_tokens,
                "window": "hour"
            }
            
        # Per-day token limit
        day_tokens = self.windows["tokens_day"][user_id].add_event(tokens)
        if day_tokens > self.config.tokens_per_day:
            return False, "Tokens per day limit exceeded", {
                "limit": self.config.tokens_per_day,
                "current": day_tokens,
                "window": "day"
            }
            
        return True, None, {}
        
    def _check_cost_limits(self, user_id: str, cost: float) -> Tuple[bool, Optional[str], Dict]:
        """Check cost-based rate limits."""
        # Per-hour cost limit
        hour_cost = self.windows["cost_hour"][user_id].get_count() + cost
        if hour_cost > self.config.cost_per_hour:
            return False, "Cost per hour limit exceeded", {
                "limit": self.config.cost_per_hour,
                "current": hour_cost,
                "window": "hour"
            }
            
        # Per-day cost limit
        day_cost = self.windows["cost_day"][user_id].get_count() + cost
        if day_cost > self.config.cost_per_day:
            return False, "Cost per day limit exceeded", {
                "limit": self.config.cost_per_day,
                "current": day_cost,
                "window": "day"
            }
            
        # Add to cost tracking
        self.windows["cost_hour"][user_id].add_event(int(cost * 100))  # Store as cents
        self.windows["cost_day"][user_id].add_event(int(cost * 100))
        
        return True, None, {}
        
    def _check_document_limits(self, user_id: str, request_type: str) -> Tuple[bool, Optional[str], Dict]:
        """Check document generation limits."""
        if request_type != "document":
            return True, None, {}
            
        metrics = self.user_metrics[user_id]
        
        # Reset hourly counter if needed
        if metrics.last_request:
            if datetime.now() - metrics.last_request > timedelta(hours=1):
                metrics.documents = 0
                
        if metrics.documents >= self.config.documents_per_hour:
            return False, "Documents per hour limit exceeded", {
                "limit": self.config.documents_per_hour,
                "current": metrics.documents
            }
            
        return True, None, {}
        
    def _check_ip_limits(self, ip_address: str) -> Tuple[bool, Optional[str], Dict]:
        """Check IP-based rate limits for DDoS protection."""
        ip_hash = hashlib.md5(ip_address.encode()).hexdigest()
        
        # Simple IP rate limit (more aggressive than user limits)
        ip_metrics = self.ip_metrics[ip_hash]
        
        # 5 requests per minute per IP
        if ip_metrics.last_request:
            elapsed = (datetime.now() - ip_metrics.last_request).total_seconds()
            if elapsed < 12:  # 5 per minute = 1 per 12 seconds
                return False, "IP rate limit exceeded", {
                    "ip_hash": ip_hash[:8],  # Partial hash for privacy
                    "retry_after": int(12 - elapsed)
                }
                
        ip_metrics.last_request = datetime.now()
        return True, None, {}
        
    def _check_concurrent_limit(self, user_id: str) -> bool:
        """Check concurrent request limit."""
        # This would need integration with request tracking
        # For now, return True (simplified)
        return True
        
    def _is_blacklisted(self, user_id: str, ip_address: Optional[str]) -> bool:
        """Check if user or IP is blacklisted."""
        # Check user blacklist
        if user_id in self.blacklist:
            if datetime.now() < self.blacklist[user_id]:
                return True
            else:
                # Remove expired blacklist entry
                del self.blacklist[user_id]
                
        # Check IP blacklist
        if ip_address:
            ip_hash = hashlib.md5(ip_address.encode()).hexdigest()
            if ip_hash in self.blacklist:
                if datetime.now() < self.blacklist[ip_hash]:
                    return True
                else:
                    del self.blacklist[ip_hash]
                    
        return False
        
    def _is_circuit_broken(self, user_id: str) -> bool:
        """Check if circuit breaker is active for user."""
        if user_id not in self.circuit_breaker_state:
            return False
            
        state = self.circuit_breaker_state[user_id]
        if state["status"] == "open":
            # Check if reset time has passed
            if time.time() - state["opened_at"] > self.config.circuit_reset_time:
                state["status"] = "half-open"
                state["errors"] = 0
                return False
            return True
            
        return False
        
    def _record_violation(self, user_id: str, ip_address: Optional[str]):
        """Record rate limit violation."""
        metrics = self.user_metrics[user_id]
        metrics.violations += 1
        
        # Check if user should be blacklisted
        if metrics.violations >= self.config.blacklist_threshold:
            self.blacklist[user_id] = datetime.now() + timedelta(
                seconds=self.config.blacklist_duration
            )
            logger.warning(f"User {user_id} blacklisted for repeated violations")
            
        # Record IP violation
        if ip_address:
            ip_hash = hashlib.md5(ip_address.encode()).hexdigest()
            ip_metrics = self.ip_metrics[ip_hash]
            ip_metrics.violations += 1
            
            if ip_metrics.violations >= self.config.blacklist_threshold:
                self.blacklist[ip_hash] = datetime.now() + timedelta(
                    seconds=self.config.blacklist_duration
                )
                logger.warning(f"IP {ip_hash[:8]} blacklisted for repeated violations")
                
    def record_success(self, user_id: str, tokens_used: int, cost: float, document_generated: bool = False):
        """
        Record successful request completion.
        
        Args:
            user_id: User identifier
            tokens_used: Actual tokens used
            cost: Actual cost incurred
            document_generated: Whether a document was generated
        """
        with self._lock:
            metrics = self.user_metrics[user_id]
            metrics.requests += 1
            metrics.tokens += tokens_used
            metrics.cost += cost
            if document_generated:
                metrics.documents += 1
            metrics.last_request = datetime.now()
            
            # Update global metrics
            self.global_metrics.requests += 1
            self.global_metrics.tokens += tokens_used
            self.global_metrics.cost += cost
            if document_generated:
                self.global_metrics.documents += 1
                
            # Reset circuit breaker on success
            if user_id in self.circuit_breaker_state:
                state = self.circuit_breaker_state[user_id]
                if state["status"] == "half-open":
                    state["status"] = "closed"
                    state["errors"] = 0
                    
    def record_error(self, user_id: str, error_type: str = "general"):
        """
        Record request error for circuit breaker.
        
        Args:
            user_id: User identifier
            error_type: Type of error encountered
        """
        with self._lock:
            metrics = self.user_metrics[user_id]
            metrics.errors += 1
            
            # Update circuit breaker
            if user_id not in self.circuit_breaker_state:
                self.circuit_breaker_state[user_id] = {
                    "status": "closed",
                    "errors": 0,
                    "opened_at": 0
                }
                
            state = self.circuit_breaker_state[user_id]
            state["errors"] += 1
            
            # Open circuit if error threshold exceeded
            if state["errors"] >= self.config.error_threshold:
                state["status"] = "open"
                state["opened_at"] = time.time()
                logger.warning(f"Circuit breaker opened for user {user_id}")
                
    def _get_remaining_limits(self, user_id: str) -> Dict[str, Any]:
        """Get remaining limits for user."""
        return {
            "requests": {
                "minute": self.buckets["requests_minute"].available_tokens(),
                "hour": max(0, self.config.requests_per_hour - self.windows["requests_hour"][user_id].get_count()),
                "day": max(0, self.config.requests_per_day - self.windows["requests_day"][user_id].get_count()),
            },
            "tokens": {
                "minute": self.buckets["tokens_minute"].available_tokens(),
                "hour": max(0, self.config.tokens_per_hour - self.windows["tokens_hour"][user_id].get_count()),
                "day": max(0, self.config.tokens_per_day - self.windows["tokens_day"][user_id].get_count()),
            },
            "cost": {
                "hour": max(0, self.config.cost_per_hour - self.windows["cost_hour"][user_id].get_count() / 100),
                "day": max(0, self.config.cost_per_day - self.windows["cost_day"][user_id].get_count() / 100),
            }
        }
        
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get usage statistics for a user."""
        with self._lock:
            metrics = self.user_metrics[user_id]
            return {
                "total_requests": metrics.requests,
                "total_tokens": metrics.tokens,
                "total_cost": metrics.cost,
                "total_documents": metrics.documents,
                "errors": metrics.errors,
                "violations": metrics.violations,
                "last_request": metrics.last_request.isoformat() if metrics.last_request else None,
                "remaining_limits": self._get_remaining_limits(user_id),
                "blacklisted": user_id in self.blacklist,
                "circuit_breaker": self.circuit_breaker_state.get(user_id, {}).get("status", "closed")
            }
            
    def reset_user_limits(self, user_id: str):
        """Reset limits for a specific user (admin function)."""
        with self._lock:
            if user_id in self.user_metrics:
                del self.user_metrics[user_id]
            if user_id in self.blacklist:
                del self.blacklist[user_id]
            if user_id in self.circuit_breaker_state:
                del self.circuit_breaker_state[user_id]
                
            # Clear sliding windows
            for window_type in self.windows:
                if user_id in self.windows[window_type]:
                    del self.windows[window_type][user_id]
                    
            logger.info(f"Reset limits for user {user_id}")
            
    def get_global_stats(self) -> Dict[str, Any]:
        """Get global usage statistics."""
        with self._lock:
            return {
                "total_requests": self.global_metrics.requests,
                "total_tokens": self.global_metrics.tokens,
                "total_cost": self.global_metrics.cost,
                "total_documents": self.global_metrics.documents,
                "total_errors": self.global_metrics.errors,
                "active_users": len(self.user_metrics),
                "blacklisted_users": len([u for u in self.blacklist if not u.startswith("ip_")]),
                "blacklisted_ips": len([u for u in self.blacklist if u.startswith("ip_")]),
                "open_circuits": len([u for u, s in self.circuit_breaker_state.items() if s["status"] == "open"])
            }