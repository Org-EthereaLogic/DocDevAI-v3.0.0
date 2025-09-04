"""
Recovery Manager for DocDevAI v3.0.0

This module provides resilient recovery mechanisms:
- Retry logic with exponential backoff
- Circuit breaker pattern for failure prevention
- Fallback strategies for degraded operation
- Resource management and cleanup

Addresses ISS-015: Recovery scenarios failing
"""

import time
import logging
import functools
from typing import Optional, Callable, Any, Dict, List, TypeVar, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import threading
import random

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RecoveryStrategy(Enum):
    """Recovery strategies for different failure types."""
    RETRY = "retry"
    CIRCUIT_BREAKER = "circuit_breaker"
    FALLBACK = "fallback"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    CACHE = "cache"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on: Optional[List[type]] = None  # Exception types to retry on
    
    def __post_init__(self):
        if self.retry_on is None:
            # Default retryable exceptions
            self.retry_on = [
                ConnectionError,
                TimeoutError,
                OSError,
                IOError
            ]


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds
    expected_exception: Optional[type] = None
    
    
@dataclass
class CircuitBreakerState:
    """State tracking for circuit breaker."""
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    state: str = "closed"  # closed, open, half_open
    lock: threading.Lock = field(default_factory=threading.Lock)


class RecoveryManager:
    """
    Central recovery manager for handling failures gracefully.
    """
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreakerState] = {}
        self.fallback_handlers: Dict[str, Callable] = {}
        self.cached_results: Dict[str, Any] = {}
        
    def retry_with_backoff(
        self,
        func: Callable[..., T],
        config: Optional[RetryConfig] = None,
        on_retry: Optional[Callable[[Exception, int], None]] = None
    ) -> Callable[..., T]:
        """
        Decorator for retry logic with exponential backoff.
        
        Example:
            @recovery_manager.retry_with_backoff(
                RetryConfig(max_attempts=3, initial_delay=1.0)
            )
            def fetch_data():
                return api_call()
        """
        if config is None:
            config = RetryConfig()
            
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(1, config.max_attempts + 1):
                try:
                    result = func(*args, **kwargs)
                    
                    # Reset circuit breaker on success if applicable
                    func_name = func.__name__
                    if func_name in self.circuit_breakers:
                        self._reset_circuit_breaker(func_name)
                        
                    return result
                    
                except Exception as e:
                    last_exception = e
                    
                    # Check if we should retry this exception
                    should_retry = any(
                        isinstance(e, exc_type) 
                        for exc_type in config.retry_on
                    )
                    
                    if not should_retry or attempt == config.max_attempts:
                        logger.error(
                            f"Failed after {attempt} attempts: {e}"
                        )
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        config.initial_delay * (config.exponential_base ** (attempt - 1)),
                        config.max_delay
                    )
                    
                    # Add jitter to prevent thundering herd
                    if config.jitter:
                        delay *= (0.5 + random.random())
                    
                    logger.warning(
                        f"Attempt {attempt}/{config.max_attempts} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    
                    # Call retry callback if provided
                    if on_retry:
                        on_retry(e, attempt)
                    
                    time.sleep(delay)
            
            raise last_exception
            
        return wrapper
    
    def circuit_breaker(
        self,
        config: Optional[CircuitBreakerConfig] = None,
        fallback: Optional[Callable[..., T]] = None
    ) -> Callable:
        """
        Decorator for circuit breaker pattern.
        
        Example:
            @recovery_manager.circuit_breaker(
                CircuitBreakerConfig(failure_threshold=5),
                fallback=lambda: "default_value"
            )
            def external_service_call():
                return make_api_call()
        """
        if config is None:
            config = CircuitBreakerConfig()
            
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            func_name = func.__name__
            
            # Initialize circuit breaker state
            if func_name not in self.circuit_breakers:
                self.circuit_breakers[func_name] = CircuitBreakerState()
            
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> T:
                state = self.circuit_breakers[func_name]
                
                with state.lock:
                    # Check circuit breaker state
                    if state.state == "open":
                        # Check if recovery timeout has passed
                        if (state.last_failure_time and 
                            datetime.now() - state.last_failure_time > 
                            timedelta(seconds=config.recovery_timeout)):
                            state.state = "half_open"
                            logger.info(f"Circuit breaker for {func_name} entering half-open state")
                        else:
                            logger.warning(f"Circuit breaker for {func_name} is OPEN")
                            if fallback:
                                return fallback(*args, **kwargs)
                            raise Exception(f"Circuit breaker is open for {func_name}")
                
                try:
                    result = func(*args, **kwargs)
                    
                    with state.lock:
                        if state.state == "half_open":
                            # Success in half-open state, close the circuit
                            state.state = "closed"
                            state.failure_count = 0
                            logger.info(f"Circuit breaker for {func_name} is now CLOSED")
                    
                    return result
                    
                except Exception as e:
                    with state.lock:
                        state.failure_count += 1
                        state.last_failure_time = datetime.now()
                        
                        if state.failure_count >= config.failure_threshold:
                            state.state = "open"
                            logger.error(
                                f"Circuit breaker for {func_name} is now OPEN "
                                f"after {state.failure_count} failures"
                            )
                    
                    if fallback and state.state == "open":
                        return fallback(*args, **kwargs)
                    raise
            
            return wrapper
        return decorator
    
    def _reset_circuit_breaker(self, func_name: str):
        """Reset circuit breaker state after successful call."""
        if func_name in self.circuit_breakers:
            state = self.circuit_breakers[func_name]
            with state.lock:
                state.failure_count = 0
                state.state = "closed"
    
    def with_fallback(
        self,
        primary: Callable[..., T],
        fallback: Callable[..., T],
        log_fallback: bool = True
    ) -> Callable[..., T]:
        """
        Execute with fallback on failure.
        
        Example:
            result = recovery_manager.with_fallback(
                primary=lambda: fetch_from_api(),
                fallback=lambda: fetch_from_cache()
            )()
        """
        @functools.wraps(primary)
        def wrapper(*args, **kwargs) -> T:
            try:
                return primary(*args, **kwargs)
            except Exception as e:
                if log_fallback:
                    logger.warning(f"Primary failed, using fallback: {e}")
                return fallback(*args, **kwargs)
        
        return wrapper
    
    def graceful_degradation(
        self,
        levels: List[Callable[..., T]],
        stop_on_success: bool = True
    ) -> Callable[..., T]:
        """
        Try multiple service levels in order of preference.
        
        Example:
            @recovery_manager.graceful_degradation([
                full_service,
                reduced_service,
                minimal_service
            ])
            def get_data():
                pass
        """
        def wrapper(*args, **kwargs) -> Optional[T]:
            last_exception = None
            
            for i, level_func in enumerate(levels):
                try:
                    result = level_func(*args, **kwargs)
                    if stop_on_success:
                        logger.info(f"Succeeded at degradation level {i+1}")
                        return result
                except Exception as e:
                    last_exception = e
                    logger.warning(
                        f"Degradation level {i+1} failed: {e}"
                    )
            
            if last_exception:
                raise last_exception
            return None
        
        return wrapper
    
    def with_timeout(
        self,
        timeout: float,
        default: Optional[T] = None
    ) -> Callable:
        """
        Decorator to add timeout to operations.
        
        Example:
            @recovery_manager.with_timeout(timeout=5.0, default=None)
            def slow_operation():
                time.sleep(10)
                return "done"
        """
        def decorator(func: Callable[..., T]) -> Callable[..., Optional[T]]:
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> Optional[T]:
                import concurrent.futures
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(func, *args, **kwargs)
                    try:
                        return future.result(timeout=timeout)
                    except concurrent.futures.TimeoutError:
                        logger.warning(f"{func.__name__} timed out after {timeout}s")
                        return default
            
            return wrapper
        return decorator
    
    def cache_on_failure(
        self,
        cache_key: Optional[str] = None,
        ttl: Optional[float] = None
    ) -> Callable:
        """
        Return cached result if operation fails.
        
        Example:
            @recovery_manager.cache_on_failure(cache_key="api_data", ttl=3600)
            def fetch_data():
                return api_call()
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> T:
                key = cache_key or f"{func.__name__}_{args}_{kwargs}"
                
                try:
                    result = func(*args, **kwargs)
                    # Update cache on success
                    self.cached_results[key] = {
                        'value': result,
                        'timestamp': time.time()
                    }
                    return result
                except Exception as e:
                    # Check cache on failure
                    if key in self.cached_results:
                        cached = self.cached_results[key]
                        
                        # Check TTL if specified
                        if ttl is None or (time.time() - cached['timestamp'] < ttl):
                            logger.warning(
                                f"Using cached result for {func.__name__} due to: {e}"
                            )
                            return cached['value']
                    
                    raise
            
            return wrapper
        return decorator


class ResourceManager:
    """
    Manage resources and ensure cleanup on failure.
    """
    
    def __init__(self):
        self.resources: List[Any] = []
        self.cleanup_handlers: List[Callable] = []
    
    def register_resource(
        self,
        resource: Any,
        cleanup: Optional[Callable] = None
    ):
        """Register a resource for cleanup."""
        self.resources.append(resource)
        if cleanup:
            self.cleanup_handlers.append(cleanup)
    
    def cleanup_all(self):
        """Clean up all registered resources."""
        for handler in self.cleanup_handlers:
            try:
                handler()
            except Exception as e:
                logger.error(f"Cleanup failed: {e}")
        
        self.resources.clear()
        self.cleanup_handlers.clear()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup_all()


class RecoveryContext:
    """
    Context manager for recovery operations.
    
    Example:
        with RecoveryContext() as recovery:
            recovery.add_cleanup(lambda: file.close())
            # ... operations that might fail
    """
    
    def __init__(self):
        self.cleanup_tasks: List[Callable] = []
        self.checkpoints: Dict[str, Any] = {}
    
    def add_cleanup(self, task: Callable):
        """Add a cleanup task to run on exit."""
        self.cleanup_tasks.append(task)
    
    def save_checkpoint(self, name: str, data: Any):
        """Save a checkpoint for potential rollback."""
        self.checkpoints[name] = data
    
    def get_checkpoint(self, name: str) -> Optional[Any]:
        """Retrieve a saved checkpoint."""
        return self.checkpoints.get(name)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Run cleanup in reverse order
        for task in reversed(self.cleanup_tasks):
            try:
                task()
            except Exception as e:
                logger.error(f"Cleanup task failed: {e}")


# Global recovery manager instance
recovery_manager = RecoveryManager()


# Specific recovery strategies for different modules
class DatabaseRecovery:
    """Recovery strategies for M002 database operations."""
    
    @staticmethod
    def handle_locked_database(
        operation: Callable,
        max_wait: float = 30.0
    ) -> Any:
        """Handle database lock with progressive backoff."""
        import sqlite3
        
        start_time = time.time()
        attempt = 0
        
        while time.time() - start_time < max_wait:
            try:
                return operation()
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower():
                    attempt += 1
                    wait_time = min(0.1 * (2 ** attempt), 5.0)
                    logger.debug(f"Database locked, waiting {wait_time:.1f}s")
                    time.sleep(wait_time)
                else:
                    raise
        
        raise TimeoutError(f"Database remained locked for {max_wait}s")
    
    @staticmethod
    def recover_corrupted_connection(connection_factory: Callable) -> Any:
        """Recover from corrupted database connection."""
        logger.info("Attempting to recover database connection")
        
        try:
            # Close existing connection if possible
            try:
                connection_factory().close()
            except:
                pass
            
            # Create new connection
            new_conn = connection_factory()
            
            # Verify connection works
            new_conn.execute("SELECT 1")
            
            logger.info("Database connection recovered successfully")
            return new_conn
            
        except Exception as e:
            logger.error(f"Failed to recover database connection: {e}")
            raise


class NetworkRecovery:
    """Recovery strategies for network operations."""
    
    @staticmethod
    def adaptive_retry(
        operation: Callable,
        initial_timeout: float = 5.0,
        max_timeout: float = 30.0
    ) -> Any:
        """Retry with adaptive timeout based on network conditions."""
        timeout = initial_timeout
        
        for attempt in range(3):
            try:
                # Measure response time
                start = time.time()
                result = operation(timeout=timeout)
                response_time = time.time() - start
                
                # Adapt timeout based on response time
                if response_time > timeout * 0.8:
                    timeout = min(timeout * 1.5, max_timeout)
                    logger.debug(f"Increasing timeout to {timeout:.1f}s")
                
                return result
                
            except TimeoutError:
                timeout = min(timeout * 2, max_timeout)
                logger.warning(f"Timeout, increasing to {timeout:.1f}s")
                
                if attempt == 2:
                    raise
    
    @staticmethod
    def connection_pool_recovery(
        pool,
        create_connection: Callable
    ):
        """Recover connection pool after failures."""
        logger.info("Recovering connection pool")
        
        # Clear bad connections
        while not pool.empty():
            try:
                conn = pool.get_nowait()
                conn.close()
            except:
                pass
        
        # Repopulate with fresh connections
        for _ in range(pool.maxsize):
            try:
                pool.put(create_connection())
            except Exception as e:
                logger.error(f"Failed to create connection: {e}")


class FileSystemRecovery:
    """Recovery strategies for file system operations."""
    
    @staticmethod
    def ensure_directory_exists(path: str):
        """Ensure directory exists, creating if necessary."""
        import os
        
        try:
            os.makedirs(path, exist_ok=True)
        except PermissionError:
            # Try alternative location
            import tempfile
            alt_path = os.path.join(tempfile.gettempdir(), 'devdocai', path)
            os.makedirs(alt_path, exist_ok=True)
            logger.warning(f"Using alternative path: {alt_path}")
            return alt_path
        
        return path
    
    @staticmethod
    def safe_file_write(
        filepath: str,
        content: Union[str, bytes],
        mode: str = 'w'
    ):
        """Write file with atomic operation and backup."""
        import os
        import shutil
        
        # Create backup if file exists
        if os.path.exists(filepath):
            backup_path = f"{filepath}.backup"
            shutil.copy2(filepath, backup_path)
        
        # Write to temporary file first
        temp_path = f"{filepath}.tmp"
        
        try:
            with open(temp_path, mode) as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            
            # Atomic rename
            os.replace(temp_path, filepath)
            
        except Exception as e:
            # Restore from backup if available
            if os.path.exists(f"{filepath}.backup"):
                shutil.copy2(f"{filepath}.backup", filepath)
            raise e
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)