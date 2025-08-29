"""
Main security module for MIAIR Engine integrating all security components.

Provides comprehensive security layer with resource monitoring and enforcement.
"""

import os
import time
import psutil
import threading
import signal
import logging
from typing import Any, Dict, Optional, Callable, Union, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
from contextlib import contextmanager
import traceback
import resource
import gc

# Import security components
from .validators import (
    InputValidator, ValidationConfig, ValidationError,
    get_validator
)
from .rate_limiter import (
    RateLimiter, RateLimitConfig, RateLimitExceeded,
    get_limiter
)
from .secure_cache import (
    SecureCache, SecureCacheConfig,
    get_cache
)
from .audit import (
    AuditLogger, AuditConfig, SecurityEventType, SeverityLevel,
    get_audit_logger
)

logger = logging.getLogger(__name__)


@dataclass
class ResourceLimits:
    """Resource usage limits."""
    max_memory_mb: int = 500
    max_cpu_percent: float = 80.0
    max_threads: int = 100
    max_file_descriptors: int = 1000
    max_processing_time: float = 30.0
    max_document_size_mb: int = 10
    
    # Thresholds for warnings
    memory_warning_threshold: float = 0.8
    cpu_warning_threshold: float = 0.7
    
    # Behavior
    enforce_limits: bool = True
    kill_on_violation: bool = False
    graceful_degradation: bool = True


@dataclass
class SecurityConfig:
    """Comprehensive security configuration."""
    # Component configs
    validation_config: ValidationConfig = field(default_factory=ValidationConfig)
    rate_limit_config: RateLimitConfig = field(default_factory=RateLimitConfig)
    cache_config: SecureCacheConfig = field(default_factory=SecureCacheConfig)
    audit_config: AuditConfig = field(default_factory=AuditConfig)
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)
    
    # Security features
    enable_validation: bool = True
    enable_rate_limiting: bool = True
    enable_secure_cache: bool = True
    enable_audit_logging: bool = True
    enable_resource_monitoring: bool = True
    
    # Fail-safe settings
    fail_open: bool = False  # If True, allow operation on security failure
    circuit_breaker_enabled: bool = True
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60
    
    # Monitoring
    monitor_interval_seconds: int = 5
    health_check_enabled: bool = True
    anomaly_detection: bool = True


@dataclass
class SecurityContext:
    """Security context for operations."""
    correlation_id: str
    user_id: Optional[str] = None
    client_id: Optional[str] = None
    operation: Optional[str] = None
    resource: Optional[str] = None
    start_time: float = field(default_factory=time.perf_counter)
    validated: bool = False
    rate_limited: bool = False
    
    def elapsed_time(self) -> float:
        """Get elapsed time since context creation."""
        return time.perf_counter() - self.start_time


@dataclass
class SecurityMetrics:
    """Security metrics and statistics."""
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    validation_failures: int = 0
    rate_limit_violations: int = 0
    resource_violations: int = 0
    security_violations: int = 0
    circuit_breaker_trips: int = 0
    average_processing_time: float = 0.0
    peak_memory_usage_mb: float = 0.0
    peak_cpu_usage_percent: float = 0.0
    
    def update_average_time(self, new_time: float):
        """Update average processing time."""
        if self.total_operations == 0:
            self.average_processing_time = new_time
        else:
            # Running average
            self.average_processing_time = (
                (self.average_processing_time * self.total_operations + new_time) /
                (self.total_operations + 1)
            )


class CircuitBreaker:
    """Circuit breaker for failing operations."""
    
    def __init__(self, threshold: int = 5, timeout: int = 60):
        """Initialize circuit breaker."""
        self.threshold = threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
        self.lock = threading.Lock()
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Call function with circuit breaker protection."""
        with self.lock:
            if self.state == "open":
                # Check if timeout has passed
                if self.last_failure_time and \
                   time.time() - self.last_failure_time > self.timeout:
                    self.state = "half-open"
                else:
                    raise Exception("Circuit breaker is open")
        
        try:
            result = func(*args, **kwargs)
            
            with self.lock:
                if self.state == "half-open":
                    # Success in half-open state, close the circuit
                    self.state = "closed"
                    self.failure_count = 0
            
            return result
            
        except Exception as e:
            with self.lock:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.failure_count >= self.threshold:
                    self.state = "open"
                    logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
            
            raise
    
    def reset(self):
        """Reset circuit breaker."""
        with self.lock:
            self.state = "closed"
            self.failure_count = 0
            self.last_failure_time = None


class ResourceMonitor:
    """Monitor and enforce resource usage limits."""
    
    def __init__(self, limits: ResourceLimits):
        """Initialize resource monitor."""
        self.limits = limits
        self.process = psutil.Process()
        self.start_time = time.time()
        self.violations = []
        self.lock = threading.Lock()
    
    def check_resources(self) -> Tuple[bool, Optional[str]]:
        """
        Check current resource usage against limits.
        
        Returns:
            Tuple of (within_limits, violation_message)
        """
        violations = []
        
        # Check memory
        memory_mb = self.process.memory_info().rss / (1024 * 1024)
        if memory_mb > self.limits.max_memory_mb:
            violations.append(f"Memory usage {memory_mb:.1f}MB exceeds limit {self.limits.max_memory_mb}MB")
        
        # Check CPU
        cpu_percent = self.process.cpu_percent()
        if cpu_percent > self.limits.max_cpu_percent:
            violations.append(f"CPU usage {cpu_percent:.1f}% exceeds limit {self.limits.max_cpu_percent}%")
        
        # Check threads
        thread_count = self.process.num_threads()
        if thread_count > self.limits.max_threads:
            violations.append(f"Thread count {thread_count} exceeds limit {self.limits.max_threads}")
        
        # Check file descriptors
        try:
            fd_count = self.process.num_fds()
            if fd_count > self.limits.max_file_descriptors:
                violations.append(f"File descriptors {fd_count} exceeds limit {self.limits.max_file_descriptors}")
        except:
            pass  # Not available on all platforms
        
        if violations:
            with self.lock:
                self.violations.extend(violations)
            return False, "; ".join(violations)
        
        return True, None
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current resource usage statistics."""
        memory_info = self.process.memory_info()
        
        return {
            'memory_mb': memory_info.rss / (1024 * 1024),
            'memory_percent': self.process.memory_percent(),
            'cpu_percent': self.process.cpu_percent(),
            'thread_count': self.process.num_threads(),
            'uptime_seconds': time.time() - self.start_time,
            'violations': len(self.violations)
        }
    
    def enforce_limits(self):
        """Enforce resource limits (platform-specific)."""
        if not self.limits.enforce_limits:
            return
        
        try:
            # Set memory limit
            memory_bytes = self.limits.max_memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
            
            # Set CPU time limit
            resource.setrlimit(resource.RLIMIT_CPU, 
                             (int(self.limits.max_processing_time), 
                              int(self.limits.max_processing_time)))
        except:
            logger.warning("Could not enforce resource limits on this platform")


class SecurityManager:
    """
    Central security manager integrating all security components.
    
    Provides:
    - Input validation
    - Rate limiting
    - Secure caching
    - Audit logging
    - Resource monitoring
    - Circuit breaker protection
    - Security context management
    """
    
    def __init__(self, config: Optional[SecurityConfig] = None):
        """Initialize security manager."""
        self.config = config or SecurityConfig()
        
        # Initialize components
        self.validator = get_validator(self.config.validation_config) \
            if self.config.enable_validation else None
        
        self.rate_limiter = get_limiter(self.config.rate_limit_config) \
            if self.config.enable_rate_limiting else None
        
        self.cache = get_cache(self.config.cache_config) \
            if self.config.enable_secure_cache else None
        
        self.audit_logger = get_audit_logger(self.config.audit_config) \
            if self.config.enable_audit_logging else None
        
        self.resource_monitor = ResourceMonitor(self.config.resource_limits) \
            if self.config.enable_resource_monitoring else None
        
        # Circuit breakers for different operations
        self.circuit_breakers = {}
        if self.config.circuit_breaker_enabled:
            self.circuit_breakers['validation'] = CircuitBreaker(
                self.config.circuit_breaker_threshold,
                self.config.circuit_breaker_timeout
            )
            self.circuit_breakers['processing'] = CircuitBreaker(
                self.config.circuit_breaker_threshold,
                self.config.circuit_breaker_timeout
            )
        
        # Metrics
        self.metrics = SecurityMetrics()
        self.lock = threading.Lock()
        
        # Start monitoring thread
        if self.config.enable_resource_monitoring:
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
        
        # Log initialization
        if self.audit_logger:
            self.audit_logger.log_event(
                SecurityEventType.SYSTEM_START,
                SeverityLevel.INFO,
                "Security manager initialized"
            )
        
        logger.info("Security manager initialized with %s mode", 
                   "fail-open" if self.config.fail_open else "fail-closed")
    
    @contextmanager
    def security_context(self,
                        operation: str,
                        resource: Optional[str] = None,
                        user_id: Optional[str] = None,
                        client_id: Optional[str] = None):
        """
        Create security context for operation.
        
        Usage:
            with security_manager.security_context('analyze', 'document') as context:
                # Perform secure operation
                pass
        """
        import uuid
        
        # Create context
        context = SecurityContext(
            correlation_id=str(uuid.uuid4()),
            operation=operation,
            resource=resource,
            user_id=user_id,
            client_id=client_id
        )
        
        # Log operation start
        if self.audit_logger:
            self.audit_logger.log_event(
                SecurityEventType.ACCESS_GRANTED,
                SeverityLevel.INFO,
                f"Starting operation: {operation}",
                operation=operation,
                resource=resource,
                user_id=user_id,
                client_id=client_id,
                correlation_id=context.correlation_id
            )
        
        try:
            # Update metrics
            with self.lock:
                self.metrics.total_operations += 1
            
            yield context
            
            # Success
            with self.lock:
                self.metrics.successful_operations += 1
                self.metrics.update_average_time(context.elapsed_time())
            
            # Log success
            if self.audit_logger:
                self.audit_logger.log_event(
                    SecurityEventType.DATA_READ if 'read' in operation.lower() 
                    else SecurityEventType.DATA_WRITE,
                    SeverityLevel.INFO,
                    f"Operation completed: {operation}",
                    operation=operation,
                    resource=resource,
                    duration_ms=context.elapsed_time() * 1000,
                    correlation_id=context.correlation_id
                )
                
        except Exception as e:
            # Failure
            with self.lock:
                self.metrics.failed_operations += 1
            
            # Log failure
            if self.audit_logger:
                self.audit_logger.log_error(
                    e,
                    operation,
                    resource=resource,
                    correlation_id=context.correlation_id
                )
            
            raise
    
    def validate_input(self,
                      content: Union[str, bytes],
                      metadata: Optional[Dict] = None,
                      document_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate input with circuit breaker protection.
        
        Returns:
            Validation result dictionary
        """
        if not self.validator:
            return {'valid': True, 'content': content, 'metadata': metadata}
        
        try:
            # Use circuit breaker if enabled
            if 'validation' in self.circuit_breakers:
                return self.circuit_breakers['validation'].call(
                    self.validator.validate_document,
                    content, metadata, document_id
                )
            else:
                return self.validator.validate_document(content, metadata, document_id)
                
        except ValidationError as e:
            with self.lock:
                self.metrics.validation_failures += 1
            
            if self.audit_logger:
                self.audit_logger.log_security_violation(
                    "validation_failure",
                    str(e),
                    document_id=document_id
                )
            
            if not self.config.fail_open:
                raise
            
            # Fail open - allow but log
            logger.warning(f"Validation failed but proceeding (fail-open): {e}")
            return {'valid': False, 'content': content, 'metadata': metadata}
    
    def check_rate_limit(self,
                        operation: str = 'analyze',
                        client_id: Optional[str] = None) -> bool:
        """
        Check rate limit.
        
        Returns:
            True if within limits
        """
        if not self.rate_limiter:
            return True
        
        allowed, reason = self.rate_limiter.check_rate_limit(operation, client_id)
        
        if not allowed:
            with self.lock:
                self.metrics.rate_limit_violations += 1
            
            if self.audit_logger:
                self.audit_logger.log_security_violation(
                    "rate_limit_exceeded",
                    reason or "Rate limit exceeded",
                    client_id=client_id,
                    operation=operation
                )
            
            if not self.config.fail_open:
                raise RateLimitExceeded(reason)
        
        return allowed
    
    def check_resources(self) -> bool:
        """
        Check resource usage.
        
        Returns:
            True if within limits
        """
        if not self.resource_monitor:
            return True
        
        within_limits, violation = self.resource_monitor.check_resources()
        
        if not within_limits:
            with self.lock:
                self.metrics.resource_violations += 1
            
            if self.audit_logger:
                self.audit_logger.log_security_violation(
                    "resource_exhaustion",
                    violation or "Resource limits exceeded",
                    severity=SeverityLevel.WARNING
                )
            
            if self.config.resource_limits.kill_on_violation:
                logger.critical(f"Resource violation, terminating: {violation}")
                os._exit(1)
            
            if not self.config.fail_open:
                raise Exception(f"Resource limits exceeded: {violation}")
        
        # Update peak usage
        if self.resource_monitor:
            stats = self.resource_monitor.get_usage_stats()
            with self.lock:
                self.metrics.peak_memory_usage_mb = max(
                    self.metrics.peak_memory_usage_mb,
                    stats.get('memory_mb', 0)
                )
                self.metrics.peak_cpu_usage_percent = max(
                    self.metrics.peak_cpu_usage_percent,
                    stats.get('cpu_percent', 0)
                )
        
        return within_limits
    
    def _monitor_loop(self):
        """Continuous resource monitoring loop."""
        while True:
            time.sleep(self.config.monitor_interval_seconds)
            
            try:
                # Check resources
                self.check_resources()
                
                # Check for anomalies
                if self.config.anomaly_detection:
                    self._detect_anomalies()
                
                # Perform health check
                if self.config.health_check_enabled:
                    self._health_check()
                    
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
    
    def _detect_anomalies(self):
        """Detect anomalous behavior patterns."""
        with self.lock:
            # Check for high failure rate
            if self.metrics.total_operations > 100:
                failure_rate = self.metrics.failed_operations / self.metrics.total_operations
                if failure_rate > 0.5:
                    if self.audit_logger:
                        self.audit_logger.log_security_violation(
                            "anomaly_detected",
                            f"High failure rate: {failure_rate:.1%}",
                            severity=SeverityLevel.WARNING
                        )
            
            # Check for spike in violations
            total_violations = (self.metrics.validation_failures +
                              self.metrics.rate_limit_violations +
                              self.metrics.resource_violations)
            
            if total_violations > 100:
                if self.audit_logger:
                    self.audit_logger.log_security_violation(
                        "anomaly_detected",
                        f"High violation count: {total_violations}",
                        severity=SeverityLevel.WARNING
                    )
    
    def _health_check(self):
        """Perform health check on security components."""
        health = {
            'validator': self.validator is not None,
            'rate_limiter': self.rate_limiter is not None,
            'cache': self.cache is not None,
            'audit_logger': self.audit_logger is not None,
            'resource_monitor': self.resource_monitor is not None
        }
        
        # Check circuit breaker states
        for name, breaker in self.circuit_breakers.items():
            health[f'circuit_{name}'] = breaker.state == 'closed'
        
        # Log if any component is unhealthy
        unhealthy = [k for k, v in health.items() if not v]
        if unhealthy and self.audit_logger:
            self.audit_logger.log_event(
                SecurityEventType.WARNING,
                SeverityLevel.WARNING,
                f"Health check failed for: {', '.join(unhealthy)}",
                metadata={'health': health}
            )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get security metrics."""
        with self.lock:
            metrics = {
                'operations': {
                    'total': self.metrics.total_operations,
                    'successful': self.metrics.successful_operations,
                    'failed': self.metrics.failed_operations,
                    'success_rate': self.metrics.successful_operations / 
                                   max(self.metrics.total_operations, 1)
                },
                'violations': {
                    'validation': self.metrics.validation_failures,
                    'rate_limit': self.metrics.rate_limit_violations,
                    'resource': self.metrics.resource_violations,
                    'security': self.metrics.security_violations,
                    'circuit_breaker': self.metrics.circuit_breaker_trips
                },
                'performance': {
                    'average_time_ms': self.metrics.average_processing_time * 1000,
                    'peak_memory_mb': self.metrics.peak_memory_usage_mb,
                    'peak_cpu_percent': self.metrics.peak_cpu_usage_percent
                }
            }
        
        # Add component metrics
        if self.validator:
            metrics['validator'] = self.validator.get_validation_stats()
        
        if self.rate_limiter:
            metrics['rate_limiter'] = self.rate_limiter.get_stats()
        
        if self.cache:
            metrics['cache'] = self.cache.get_stats()
        
        if self.audit_logger:
            metrics['audit'] = self.audit_logger.get_stats()
        
        if self.resource_monitor:
            metrics['resources'] = self.resource_monitor.get_usage_stats()
        
        return metrics
    
    def cleanup(self):
        """Clean up resources."""
        if self.audit_logger:
            self.audit_logger.log_event(
                SecurityEventType.SYSTEM_STOP,
                SeverityLevel.INFO,
                "Security manager shutting down"
            )
            self.audit_logger.close()
        
        logger.info("Security manager shut down")


def secure_operation(operation_name: str,
                    resource_type: Optional[str] = None,
                    validate_input: bool = True,
                    check_rate_limit: bool = True,
                    check_resources: bool = True,
                    timeout: Optional[float] = None):
    """
    Decorator for securing operations.
    
    Args:
        operation_name: Name of operation
        resource_type: Type of resource
        validate_input: Whether to validate input
        check_rate_limit: Whether to check rate limits
        check_resources: Whether to check resource limits
        timeout: Operation timeout in seconds
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Get security manager from self
            security_manager = getattr(self, 'security_manager', None)
            
            if not security_manager:
                # No security manager, proceed without security
                return func(self, *args, **kwargs)
            
            # Extract relevant parameters
            content = args[0] if args else kwargs.get('content')
            document_id = kwargs.get('document_id')
            client_id = kwargs.get('client_id') or document_id
            
            # Create security context
            with security_manager.security_context(
                operation_name,
                resource_type,
                client_id=client_id
            ) as context:
                
                # Validate input if requested
                if validate_input and content:
                    validation_result = security_manager.validate_input(
                        content,
                        kwargs.get('metadata'),
                        document_id
                    )
                    
                    # Replace content with sanitized version
                    if validation_result['valid']:
                        if args:
                            args = (validation_result['content'],) + args[1:]
                        else:
                            kwargs['content'] = validation_result['content']
                
                # Check rate limit
                if check_rate_limit:
                    security_manager.check_rate_limit(operation_name, client_id)
                
                # Check resources
                if check_resources:
                    security_manager.check_resources()
                
                # Set timeout if specified
                if timeout:
                    def timeout_handler(signum, frame):
                        raise TimeoutError(f"Operation {operation_name} timed out after {timeout}s")
                    
                    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(int(timeout))
                
                try:
                    # Execute function
                    result = func(self, *args, **kwargs)
                    return result
                    
                finally:
                    # Reset timeout
                    if timeout:
                        signal.alarm(0)
                        signal.signal(signal.SIGALRM, old_handler)
        
        return wrapper
    return decorator


# Global security manager instance
_default_manager = None


def get_security_manager(config: Optional[SecurityConfig] = None) -> SecurityManager:
    """Get or create default security manager instance."""
    global _default_manager
    
    if _default_manager is None or config is not None:
        _default_manager = SecurityManager(config)
    
    return _default_manager