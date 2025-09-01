"""
Rate limiting and DoS prevention for CLI.

Implements multiple rate limiting strategies to prevent abuse.
"""

import time
import json
import hashlib
import threading
from pathlib import Path
from collections import defaultdict, deque
from functools import wraps
from typing import Optional, Dict, Any, Callable, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict


class RateLimitExceeded(Exception):
    """Rate limit exceeded error."""
    
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    max_requests: int = 100  # Maximum requests
    time_window: int = 60    # Time window in seconds
    burst_size: int = 10     # Maximum burst requests
    cooldown: int = 300      # Cooldown period after limit exceeded
    enable_persistence: bool = True  # Persist rate limit data
    enable_distributed: bool = False  # Enable distributed rate limiting


class RateLimiter:
    """
    Advanced rate limiting with multiple strategies.
    
    Supports:
    - Token bucket algorithm
    - Sliding window log
    - Fixed window counter
    - Leaky bucket
    - Distributed rate limiting
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None,
                 storage_dir: Optional[Path] = None):
        """
        Initialize rate limiter.
        
        Args:
            config: Rate limit configuration
            storage_dir: Directory for persistent storage
        """
        self.config = config or RateLimitConfig()
        self.storage_dir = storage_dir or (Path.home() / '.devdocai' / 'ratelimit')
        self.storage_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        
        # Thread-safe storage
        self._lock = threading.RLock()
        
        # Token buckets: {identifier: {'tokens': float, 'last_update': float}}
        self._token_buckets: Dict[str, Dict[str, float]] = {}
        
        # Sliding window logs: {identifier: deque of timestamps}
        self._sliding_windows: Dict[str, deque] = defaultdict(deque)
        
        # Fixed window counters: {identifier: {'count': int, 'window_start': float}}
        self._fixed_windows: Dict[str, Dict[str, Any]] = {}
        
        # Blacklist for repeat offenders
        self._blacklist: Dict[str, float] = {}  # {identifier: unblock_time}
        
        # Load persistent data if enabled
        if self.config.enable_persistence:
            self._load_state()
    
    def check_rate_limit(self, identifier: str,
                        cost: int = 1,
                        strategy: str = 'token_bucket') -> bool:
        """
        Check if request is within rate limit.
        
        Args:
            identifier: Unique identifier (user, IP, etc.)
            cost: Cost of the request (default 1)
            strategy: Rate limiting strategy to use
            
        Returns:
            True if request is allowed
            
        Raises:
            RateLimitExceeded: If rate limit exceeded
        """
        with self._lock:
            # Check blacklist first
            if self._is_blacklisted(identifier):
                retry_after = int(self._blacklist[identifier] - time.time())
                raise RateLimitExceeded(
                    f"Rate limit exceeded. Retry after {retry_after} seconds",
                    retry_after=retry_after
                )
            
            # Apply selected strategy
            if strategy == 'token_bucket':
                allowed = self._check_token_bucket(identifier, cost)
            elif strategy == 'sliding_window':
                allowed = self._check_sliding_window(identifier, cost)
            elif strategy == 'fixed_window':
                allowed = self._check_fixed_window(identifier, cost)
            elif strategy == 'leaky_bucket':
                allowed = self._check_leaky_bucket(identifier, cost)
            else:
                # Default to token bucket
                allowed = self._check_token_bucket(identifier, cost)
            
            if not allowed:
                # Add to blacklist if repeatedly hitting limits
                self._add_to_blacklist(identifier)
                retry_after = self.config.time_window
                raise RateLimitExceeded(
                    f"Rate limit exceeded. Max {self.config.max_requests} requests per {self.config.time_window} seconds",
                    retry_after=retry_after
                )
            
            # Persist state if enabled
            if self.config.enable_persistence:
                self._save_state()
            
            return True
    
    def _check_token_bucket(self, identifier: str, cost: int) -> bool:
        """
        Token bucket algorithm.
        
        Allows burst traffic while maintaining average rate.
        """
        now = time.time()
        
        if identifier not in self._token_buckets:
            self._token_buckets[identifier] = {
                'tokens': self.config.burst_size,
                'last_update': now
            }
        
        bucket = self._token_buckets[identifier]
        
        # Calculate tokens to add based on time elapsed
        time_elapsed = now - bucket['last_update']
        tokens_to_add = time_elapsed * (self.config.max_requests / self.config.time_window)
        
        # Update tokens (cap at burst size)
        bucket['tokens'] = min(self.config.burst_size, bucket['tokens'] + tokens_to_add)
        bucket['last_update'] = now
        
        # Check if enough tokens available
        if bucket['tokens'] >= cost:
            bucket['tokens'] -= cost
            return True
        
        return False
    
    def _check_sliding_window(self, identifier: str, cost: int) -> bool:
        """
        Sliding window log algorithm.
        
        Most accurate but memory intensive.
        """
        now = time.time()
        window = self._sliding_windows[identifier]
        
        # Remove old entries outside the window
        cutoff = now - self.config.time_window
        while window and window[0] < cutoff:
            window.popleft()
        
        # Check if adding this request would exceed limit
        if len(window) + cost > self.config.max_requests:
            return False
        
        # Add timestamps for this request
        for _ in range(cost):
            window.append(now)
        
        return True
    
    def _check_fixed_window(self, identifier: str, cost: int) -> bool:
        """
        Fixed window counter algorithm.
        
        Simple and efficient but can allow burst at window boundaries.
        """
        now = time.time()
        
        if identifier not in self._fixed_windows:
            self._fixed_windows[identifier] = {
                'count': 0,
                'window_start': now
            }
        
        window = self._fixed_windows[identifier]
        
        # Check if we're in a new window
        if now - window['window_start'] >= self.config.time_window:
            window['count'] = 0
            window['window_start'] = now
        
        # Check if adding this request would exceed limit
        if window['count'] + cost > self.config.max_requests:
            return False
        
        window['count'] += cost
        return True
    
    def _check_leaky_bucket(self, identifier: str, cost: int) -> bool:
        """
        Leaky bucket algorithm.
        
        Smooth rate limiting without burst capability.
        """
        now = time.time()
        
        if identifier not in self._token_buckets:
            self._token_buckets[identifier] = {
                'tokens': 0,
                'last_update': now
            }
        
        bucket = self._token_buckets[identifier]
        
        # Calculate tokens leaked (requests processed)
        time_elapsed = now - bucket['last_update']
        tokens_leaked = time_elapsed * (self.config.max_requests / self.config.time_window)
        
        # Update bucket (can't go negative)
        bucket['tokens'] = max(0, bucket['tokens'] - tokens_leaked)
        bucket['last_update'] = now
        
        # Check if bucket can accept more
        if bucket['tokens'] + cost <= self.config.max_requests:
            bucket['tokens'] += cost
            return True
        
        return False
    
    def _is_blacklisted(self, identifier: str) -> bool:
        """Check if identifier is blacklisted."""
        if identifier in self._blacklist:
            if time.time() < self._blacklist[identifier]:
                return True
            else:
                # Remove expired blacklist entry
                del self._blacklist[identifier]
        return False
    
    def _add_to_blacklist(self, identifier: str):
        """Add identifier to blacklist."""
        # Count recent violations
        violations_file = self.storage_dir / f"{identifier}.violations"
        
        violations = []
        if violations_file.exists():
            with open(violations_file, 'r') as f:
                violations = json.load(f)
        
        # Add current violation
        violations.append(time.time())
        
        # Keep only recent violations (last hour)
        cutoff = time.time() - 3600
        violations = [v for v in violations if v > cutoff]
        
        # Save violations
        with open(violations_file, 'w') as f:
            json.dump(violations, f)
        
        # Blacklist if too many violations
        if len(violations) >= 3:
            self._blacklist[identifier] = time.time() + self.config.cooldown
    
    def rate_limit(self, identifier_func: Optional[Callable] = None,
                   cost: int = 1,
                   strategy: str = 'token_bucket'):
        """
        Decorator for rate limiting functions.
        
        Args:
            identifier_func: Function to get identifier from arguments
            cost: Cost of the operation
            strategy: Rate limiting strategy
            
        Returns:
            Decorated function
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Get identifier
                if identifier_func:
                    identifier = identifier_func(*args, **kwargs)
                else:
                    # Default to function name
                    identifier = func.__name__
                
                # Check rate limit
                self.check_rate_limit(identifier, cost, strategy)
                
                # Execute function
                return func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def get_remaining_quota(self, identifier: str,
                           strategy: str = 'token_bucket') -> Tuple[int, int]:
        """
        Get remaining quota for identifier.
        
        Args:
            identifier: Unique identifier
            strategy: Rate limiting strategy
            
        Returns:
            Tuple of (remaining_requests, reset_time_seconds)
        """
        with self._lock:
            if strategy == 'token_bucket':
                if identifier in self._token_buckets:
                    bucket = self._token_buckets[identifier]
                    remaining = int(bucket['tokens'])
                    reset_time = self.config.time_window
                else:
                    remaining = self.config.burst_size
                    reset_time = 0
            elif strategy == 'sliding_window':
                window = self._sliding_windows[identifier]
                now = time.time()
                cutoff = now - self.config.time_window
                
                # Count current requests in window
                current = sum(1 for t in window if t > cutoff)
                remaining = self.config.max_requests - current
                
                # Calculate reset time (when oldest request expires)
                if window:
                    reset_time = int(window[0] + self.config.time_window - now)
                else:
                    reset_time = 0
            elif strategy == 'fixed_window':
                if identifier in self._fixed_windows:
                    window = self._fixed_windows[identifier]
                    remaining = self.config.max_requests - window['count']
                    reset_time = int(self.config.time_window - 
                                   (time.time() - window['window_start']))
                else:
                    remaining = self.config.max_requests
                    reset_time = self.config.time_window
            else:
                remaining = 0
                reset_time = 0
            
            return max(0, remaining), max(0, reset_time)
    
    def reset_limits(self, identifier: Optional[str] = None):
        """
        Reset rate limits.
        
        Args:
            identifier: Specific identifier to reset, or None for all
        """
        with self._lock:
            if identifier:
                # Reset specific identifier
                self._token_buckets.pop(identifier, None)
                self._sliding_windows.pop(identifier, None)
                self._fixed_windows.pop(identifier, None)
                self._blacklist.pop(identifier, None)
                
                # Remove violations file
                violations_file = self.storage_dir / f"{identifier}.violations"
                violations_file.unlink(missing_ok=True)
            else:
                # Reset all
                self._token_buckets.clear()
                self._sliding_windows.clear()
                self._fixed_windows.clear()
                self._blacklist.clear()
                
                # Remove all violation files
                for file in self.storage_dir.glob("*.violations"):
                    file.unlink()
            
            if self.config.enable_persistence:
                self._save_state()
    
    def _save_state(self):
        """Save rate limiter state to disk."""
        state = {
            'token_buckets': self._token_buckets,
            'fixed_windows': self._fixed_windows,
            'blacklist': self._blacklist,
            'timestamp': time.time()
        }
        
        state_file = self.storage_dir / 'state.json'
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def _load_state(self):
        """Load rate limiter state from disk."""
        state_file = self.storage_dir / 'state.json'
        
        if not state_file.exists():
            return
        
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
            
            # Check if state is not too old (1 hour)
            if time.time() - state.get('timestamp', 0) < 3600:
                self._token_buckets = state.get('token_buckets', {})
                self._fixed_windows = state.get('fixed_windows', {})
                self._blacklist = state.get('blacklist', {})
        except Exception:
            # Ignore errors loading state
            pass


class CommandRateLimiter(RateLimiter):
    """
    Specialized rate limiter for CLI commands.
    
    Implements command-specific limits and user/IP tracking.
    """
    
    # Command-specific configurations
    COMMAND_LIMITS = {
        'generate': RateLimitConfig(max_requests=50, time_window=60, burst_size=5),
        'analyze': RateLimitConfig(max_requests=100, time_window=60, burst_size=10),
        'enhance': RateLimitConfig(max_requests=30, time_window=60, burst_size=3),
        'security': RateLimitConfig(max_requests=20, time_window=60, burst_size=2),
        'config': RateLimitConfig(max_requests=100, time_window=60, burst_size=20),
        'template': RateLimitConfig(max_requests=100, time_window=60, burst_size=20),
    }
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """Initialize command rate limiter."""
        super().__init__(
            config=RateLimitConfig(max_requests=200, time_window=60, burst_size=20),
            storage_dir=storage_dir
        )
        
        # Command-specific limiters
        self._command_limiters: Dict[str, RateLimiter] = {}
        
        for command, config in self.COMMAND_LIMITS.items():
            self._command_limiters[command] = RateLimiter(
                config=config,
                storage_dir=self.storage_dir / command
            )
    
    def check_command_limit(self, command: str, user: str,
                           cost: int = 1) -> bool:
        """
        Check rate limit for specific command.
        
        Args:
            command: Command name
            user: User identifier
            cost: Cost of the operation
            
        Returns:
            True if allowed
            
        Raises:
            RateLimitExceeded: If rate limit exceeded
        """
        # Check global limit first
        identifier = f"user:{user}"
        self.check_rate_limit(identifier, cost)
        
        # Check command-specific limit
        if command in self._command_limiters:
            command_identifier = f"{command}:{user}"
            self._command_limiters[command].check_rate_limit(
                command_identifier, cost
            )
        
        return True
    
    def get_command_quota(self, command: str, user: str) -> Dict[str, Any]:
        """
        Get quota information for command.
        
        Args:
            command: Command name
            user: User identifier
            
        Returns:
            Quota information
        """
        # Global quota
        global_identifier = f"user:{user}"
        global_remaining, global_reset = self.get_remaining_quota(global_identifier)
        
        # Command quota
        command_quota = None
        if command in self._command_limiters:
            command_identifier = f"{command}:{user}"
            cmd_remaining, cmd_reset = self._command_limiters[command].get_remaining_quota(
                command_identifier
            )
            command_quota = {
                'remaining': cmd_remaining,
                'reset_in': cmd_reset,
                'limit': self.COMMAND_LIMITS[command].max_requests
            }
        
        return {
            'global': {
                'remaining': global_remaining,
                'reset_in': global_reset,
                'limit': self.config.max_requests
            },
            'command': command_quota
        }