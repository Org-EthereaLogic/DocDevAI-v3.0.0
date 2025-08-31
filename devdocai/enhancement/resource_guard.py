"""
M009: Resource Protection Module.

Provides comprehensive resource monitoring and protection including
memory limits, CPU time limits, disk I/O limits, connection pools,
and circuit breaker patterns for the Enhancement Pipeline.
"""

import os
import psutil
import time
import threading
import signal
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from contextlib import contextmanager
import resource
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import asyncio
import gc
import logging

logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """Types of system resources."""
    MEMORY = "memory"
    CPU_TIME = "cpu_time"
    DISK_IO = "disk_io"
    NETWORK_IO = "network_io"
    FILE_DESCRIPTORS = "file_descriptors"
    THREADS = "threads"
    PROCESSES = "processes"


class ProtectionLevel(Enum):
    """Resource protection levels."""
    NONE = "none"           # No protection
    SOFT = "soft"           # Warnings only
    HARD = "hard"           # Enforce limits
    STRICT = "strict"       # Strict enforcement with penalties


class ResourceStatus(Enum):
    """Resource usage status."""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    EXCEEDED = "exceeded"
    THROTTLED = "throttled"


@dataclass
class ResourceLimits:
    """Resource usage limits."""
    
    # Memory limits (in bytes)
    max_memory_per_operation: int = 512 * 1024 * 1024  # 512MB
    max_total_memory: int = 2 * 1024 * 1024 * 1024     # 2GB
    memory_warning_threshold: float = 0.8               # 80% of limit
    
    # CPU limits
    max_cpu_time_per_operation: float = 300.0          # 5 minutes
    max_cpu_percentage: float = 80.0                    # 80% CPU usage
    cpu_warning_threshold: float = 0.7                  # 70% of limit
    
    # I/O limits
    max_disk_read_mb_per_sec: int = 100                # 100MB/s
    max_disk_write_mb_per_sec: int = 50                # 50MB/s
    max_network_mb_per_sec: int = 10                   # 10MB/s
    
    # Concurrency limits
    max_concurrent_operations: int = 10
    max_threads_per_operation: int = 4
    max_processes: int = multiprocessing.cpu_count() * 2
    max_file_descriptors: int = 1000
    
    # Timeout limits
    operation_timeout: float = 600.0                   # 10 minutes
    network_timeout: float = 30.0                     # 30 seconds
    
    # Recovery settings
    recovery_delay: float = 1.0                       # Delay after limit hit
    max_recovery_attempts: int = 3
    
    @classmethod
    def for_protection_level(cls, level: str) -> 'ResourceLimits':
        """Get limits for specific protection level."""
        configs = {
            "BASIC": cls(
                max_memory_per_operation=1024 * 1024 * 1024,  # 1GB
                max_cpu_time_per_operation=600.0,             # 10 minutes
                max_concurrent_operations=20,
                operation_timeout=1200.0                      # 20 minutes
            ),
            "STANDARD": cls(),  # Use defaults
            "STRICT": cls(
                max_memory_per_operation=256 * 1024 * 1024,   # 256MB
                max_total_memory=1024 * 1024 * 1024,          # 1GB
                max_cpu_time_per_operation=180.0,             # 3 minutes
                max_cpu_percentage=60.0,                      # 60% CPU
                max_concurrent_operations=5,
                max_threads_per_operation=2,
                operation_timeout=300.0,                      # 5 minutes
                recovery_delay=2.0,
                max_recovery_attempts=2
            ),
            "PARANOID": cls(
                max_memory_per_operation=128 * 1024 * 1024,   # 128MB
                max_total_memory=512 * 1024 * 1024,           # 512MB
                max_cpu_time_per_operation=60.0,              # 1 minute
                max_cpu_percentage=50.0,                      # 50% CPU
                max_concurrent_operations=3,
                max_threads_per_operation=1,
                operation_timeout=120.0,                      # 2 minutes
                recovery_delay=5.0,
                max_recovery_attempts=1
            )
        }
        return configs.get(level, cls())


@dataclass
class ResourceUsage:
    """Current resource usage metrics."""
    
    memory_bytes: int = 0
    cpu_percent: float = 0.0
    cpu_time: float = 0.0
    disk_read_mb: float = 0.0
    disk_write_mb: float = 0.0
    network_mb: float = 0.0
    file_descriptors: int = 0
    active_threads: int = 0
    active_processes: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "memory_mb": self.memory_bytes / (1024 * 1024),
            "cpu_percent": self.cpu_percent,
            "cpu_time": self.cpu_time,
            "disk_read_mb": self.disk_read_mb,
            "disk_write_mb": self.disk_write_mb,
            "network_mb": self.network_mb,
            "file_descriptors": self.file_descriptors,
            "active_threads": self.active_threads,
            "active_processes": self.active_processes,
            "timestamp": self.timestamp.isoformat()
        }


class ResourceMonitor:
    """Monitor system resource usage."""
    
    def __init__(self, update_interval: float = 1.0):
        """Initialize resource monitor."""
        self.update_interval = update_interval
        self.running = False
        self.monitor_thread = None
        self.usage_history: List[ResourceUsage] = []
        self.max_history_size = 3600  # Keep 1 hour of history
        self._lock = threading.Lock()
        
        # Process tracking
        self.process = psutil.Process()
        self.start_time = time.time()
        
    def start_monitoring(self) -> None:
        """Start resource monitoring."""
        if not self.running:
            self.running = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("Resource monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop resource monitoring."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Resource monitoring stopped")
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self.running:
            try:
                usage = self.get_current_usage()
                
                with self._lock:
                    self.usage_history.append(usage)
                    # Trim history
                    if len(self.usage_history) > self.max_history_size:
                        self.usage_history = self.usage_history[-self.max_history_size:]
                
                time.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Resource monitoring error: {e}")
                time.sleep(self.update_interval)
    
    def get_current_usage(self) -> ResourceUsage:
        """Get current resource usage."""
        try:
            # Memory usage
            memory_info = self.process.memory_info()
            memory_bytes = memory_info.rss  # Resident Set Size
            
            # CPU usage
            cpu_percent = self.process.cpu_percent()
            cpu_times = self.process.cpu_times()
            cpu_time = cpu_times.user + cpu_times.system
            
            # I/O stats
            try:
                io_counters = self.process.io_counters()
                disk_read_mb = io_counters.read_bytes / (1024 * 1024)
                disk_write_mb = io_counters.write_bytes / (1024 * 1024)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                disk_read_mb = disk_write_mb = 0.0
            
            # File descriptors
            try:
                file_descriptors = self.process.num_fds()
            except (psutil.NoSuchProcess, AttributeError, psutil.AccessDenied):
                file_descriptors = 0
            
            # Threads
            active_threads = self.process.num_threads()
            
            # Child processes
            try:
                children = self.process.children(recursive=True)
                active_processes = len(children)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                active_processes = 0
            
            return ResourceUsage(
                memory_bytes=memory_bytes,
                cpu_percent=cpu_percent,
                cpu_time=cpu_time,
                disk_read_mb=disk_read_mb,
                disk_write_mb=disk_write_mb,
                file_descriptors=file_descriptors,
                active_threads=active_threads,
                active_processes=active_processes,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to get resource usage: {e}")
            return ResourceUsage()
    
    def get_usage_stats(self, duration_minutes: int = 5) -> Dict[str, Any]:
        """Get usage statistics over specified duration."""
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        
        with self._lock:
            recent_usage = [
                usage for usage in self.usage_history
                if usage.timestamp > cutoff_time
            ]
        
        if not recent_usage:
            return {}
        
        # Calculate statistics
        memory_values = [u.memory_bytes for u in recent_usage]
        cpu_values = [u.cpu_percent for u in recent_usage]
        
        return {
            "memory_avg_mb": sum(memory_values) / len(memory_values) / (1024 * 1024),
            "memory_max_mb": max(memory_values) / (1024 * 1024),
            "cpu_avg_percent": sum(cpu_values) / len(cpu_values),
            "cpu_max_percent": max(cpu_values),
            "samples": len(recent_usage),
            "duration_minutes": duration_minutes
        }


class ResourceGuard:
    """Guard against resource exhaustion."""
    
    def __init__(
        self,
        limits: Optional[ResourceLimits] = None,
        protection_level: ProtectionLevel = ProtectionLevel.HARD
    ):
        """Initialize resource guard."""
        self.limits = limits or ResourceLimits()
        self.protection_level = protection_level
        
        # Initialize monitor
        self.monitor = ResourceMonitor()
        
        # Active operations tracking
        self.active_operations: Dict[str, Dict[str, Any]] = {}
        self.operation_counter = 0
        self._lock = threading.Lock()
        
        # Circuit breaker state
        self.circuit_breaker_active = False
        self.circuit_breaker_until = None
        
        # Violation tracking
        self.violation_count = 0
        self.last_violation = None
        
        # Start monitoring
        self.monitor.start_monitoring()
        
        logger.info(f"Resource guard initialized with {protection_level.value} protection")
    
    @contextmanager
    def protect_operation(
        self,
        operation_id: Optional[str] = None,
        memory_limit: Optional[int] = None,
        cpu_time_limit: Optional[float] = None,
        timeout: Optional[float] = None
    ):
        """Context manager for protecting operations."""
        # Generate operation ID if not provided
        if operation_id is None:
            with self._lock:
                self.operation_counter += 1
                operation_id = f"op_{self.operation_counter}"
        
        # Check circuit breaker
        if self._is_circuit_breaker_active():
            raise ResourceExhaustionError("Resource guard circuit breaker is active")
        
        # Check concurrent operation limit
        if len(self.active_operations) >= self.limits.max_concurrent_operations:
            if self.protection_level in [ProtectionLevel.HARD, ProtectionLevel.STRICT]:
                raise ResourceExhaustionError(
                    f"Too many concurrent operations: {len(self.active_operations)}"
                )
        
        # Initialize operation tracking
        operation_info = {
            "id": operation_id,
            "start_time": time.time(),
            "start_memory": self.monitor.get_current_usage().memory_bytes,
            "memory_limit": memory_limit or self.limits.max_memory_per_operation,
            "cpu_time_limit": cpu_time_limit or self.limits.max_cpu_time_per_operation,
            "timeout": timeout or self.limits.operation_timeout,
            "initial_cpu_time": time.process_time(),
            "process": psutil.Process(),
            "violations": []
        }
        
        with self._lock:
            self.active_operations[operation_id] = operation_info
        
        # Set up signal handler for timeout (Unix only)
        old_handler = None
        if hasattr(signal, 'SIGALRM'):
            def timeout_handler(signum, frame):
                raise TimeoutError(f"Operation {operation_id} timed out after {operation_info['timeout']} seconds")
            
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(operation_info['timeout']))
        
        try:
            # Monitor thread
            monitor_thread = threading.Thread(
                target=self._monitor_operation,
                args=(operation_id,),
                daemon=True
            )
            monitor_thread.start()
            
            yield operation_id
            
        except Exception as e:
            # Record violation
            self._record_violation(operation_id, str(e))
            raise
        
        finally:
            # Clean up
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)  # Cancel alarm
                if old_handler:
                    signal.signal(signal.SIGALRM, old_handler)
            
            with self._lock:
                if operation_id in self.active_operations:
                    # Log final stats
                    op_info = self.active_operations[operation_id]
                    duration = time.time() - op_info['start_time']
                    memory_used = self.monitor.get_current_usage().memory_bytes - op_info['start_memory']
                    
                    logger.debug(
                        f"Operation {operation_id} completed: "
                        f"duration={duration:.2f}s, memory_delta={memory_used / (1024*1024):.2f}MB"
                    )
                    
                    del self.active_operations[operation_id]
    
    def _monitor_operation(self, operation_id: str) -> None:
        """Monitor a specific operation for resource violations."""
        check_interval = 1.0  # Check every second
        
        while operation_id in self.active_operations:
            try:
                operation_info = self.active_operations[operation_id]
                current_usage = self.monitor.get_current_usage()
                current_time = time.time()
                current_cpu_time = time.process_time()
                
                # Check memory limit
                memory_used = current_usage.memory_bytes - operation_info['start_memory']
                if memory_used > operation_info['memory_limit']:
                    violation = f"Memory limit exceeded: {memory_used / (1024*1024):.2f}MB > {operation_info['memory_limit'] / (1024*1024):.2f}MB"
                    self._handle_violation(operation_id, ResourceType.MEMORY, violation)
                
                # Check CPU time limit
                cpu_time_used = current_cpu_time - operation_info['initial_cpu_time']
                if cpu_time_used > operation_info['cpu_time_limit']:
                    violation = f"CPU time limit exceeded: {cpu_time_used:.2f}s > {operation_info['cpu_time_limit']:.2f}s"
                    self._handle_violation(operation_id, ResourceType.CPU_TIME, violation)
                
                # Check operation timeout
                duration = current_time - operation_info['start_time']
                if duration > operation_info['timeout']:
                    violation = f"Operation timeout: {duration:.2f}s > {operation_info['timeout']:.2f}s"
                    self._handle_violation(operation_id, ResourceType.CPU_TIME, violation)
                    break  # Stop monitoring
                
                # Check system-wide limits
                if current_usage.memory_bytes > self.limits.max_total_memory:
                    violation = f"Total memory limit exceeded: {current_usage.memory_bytes / (1024*1024):.2f}MB"
                    self._handle_violation(operation_id, ResourceType.MEMORY, violation)
                
                if current_usage.cpu_percent > self.limits.max_cpu_percentage:
                    violation = f"CPU percentage limit exceeded: {current_usage.cpu_percent:.1f}% > {self.limits.max_cpu_percentage:.1f}%"
                    self._handle_violation(operation_id, ResourceType.CPU_TIME, violation)
                
                time.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"Operation monitoring error for {operation_id}: {e}")
                time.sleep(check_interval)
    
    def _handle_violation(self, operation_id: str, resource_type: ResourceType, violation: str) -> None:
        """Handle resource violation."""
        self.violation_count += 1
        self.last_violation = datetime.now()
        
        logger.warning(f"Resource violation in operation {operation_id}: {violation}")
        
        # Record in operation info
        if operation_id in self.active_operations:
            self.active_operations[operation_id]['violations'].append({
                'type': resource_type.value,
                'message': violation,
                'timestamp': datetime.now()
            })
        
        # Handle based on protection level
        if self.protection_level == ProtectionLevel.SOFT:
            # Just log warning
            pass
        elif self.protection_level == ProtectionLevel.HARD:
            # Terminate operation
            self._terminate_operation(operation_id)
        elif self.protection_level == ProtectionLevel.STRICT:
            # Terminate and activate circuit breaker
            self._terminate_operation(operation_id)
            self._activate_circuit_breaker()
    
    def _terminate_operation(self, operation_id: str) -> None:
        """Terminate operation due to resource violation."""
        try:
            if operation_id in self.active_operations:
                operation_info = self.active_operations[operation_id]
                process = operation_info.get('process')
                
                if process and process.is_running():
                    logger.warning(f"Terminating operation {operation_id} due to resource violation")
                    
                    # Try graceful termination first
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except psutil.TimeoutExpired:
                        # Force kill if graceful termination fails
                        process.kill()
                        process.wait(timeout=5)
                    
                    logger.info(f"Operation {operation_id} terminated")
        
        except Exception as e:
            logger.error(f"Failed to terminate operation {operation_id}: {e}")
    
    def _activate_circuit_breaker(self) -> None:
        """Activate circuit breaker to prevent new operations."""
        self.circuit_breaker_active = True
        self.circuit_breaker_until = datetime.now() + timedelta(seconds=60)  # 1 minute
        logger.warning("Resource guard circuit breaker activated")
    
    def _is_circuit_breaker_active(self) -> bool:
        """Check if circuit breaker is active."""
        if not self.circuit_breaker_active:
            return False
        
        if self.circuit_breaker_until and datetime.now() > self.circuit_breaker_until:
            self.circuit_breaker_active = False
            self.circuit_breaker_until = None
            logger.info("Resource guard circuit breaker deactivated")
            return False
        
        return True
    
    def _record_violation(self, operation_id: str, error: str) -> None:
        """Record violation for statistics."""
        self.violation_count += 1
        self.last_violation = datetime.now()
        logger.warning(f"Resource violation in {operation_id}: {error}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get resource guard status."""
        current_usage = self.monitor.get_current_usage()
        usage_stats = self.monitor.get_usage_stats()
        
        return {
            "active_operations": len(self.active_operations),
            "max_concurrent": self.limits.max_concurrent_operations,
            "violation_count": self.violation_count,
            "last_violation": self.last_violation.isoformat() if self.last_violation else None,
            "circuit_breaker_active": self.circuit_breaker_active,
            "circuit_breaker_until": self.circuit_breaker_until.isoformat() if self.circuit_breaker_until else None,
            "protection_level": self.protection_level.value,
            "current_usage": current_usage.to_dict(),
            "usage_stats": usage_stats,
            "limits": {
                "memory_per_operation_mb": self.limits.max_memory_per_operation / (1024 * 1024),
                "total_memory_mb": self.limits.max_total_memory / (1024 * 1024),
                "cpu_time_per_operation": self.limits.max_cpu_time_per_operation,
                "cpu_percentage": self.limits.max_cpu_percentage,
                "operation_timeout": self.limits.operation_timeout
            }
        }
    
    def get_active_operations(self) -> List[Dict[str, Any]]:
        """Get information about active operations."""
        operations = []
        current_time = time.time()
        
        with self._lock:
            for operation_id, info in self.active_operations.items():
                operations.append({
                    "id": operation_id,
                    "duration": current_time - info['start_time'],
                    "memory_limit_mb": info['memory_limit'] / (1024 * 1024),
                    "cpu_time_limit": info['cpu_time_limit'],
                    "timeout": info['timeout'],
                    "violations": len(info['violations'])
                })
        
        return operations
    
    def force_cleanup(self) -> int:
        """Force cleanup of stale operations."""
        cleaned_count = 0
        current_time = time.time()
        
        with self._lock:
            stale_operations = []
            for operation_id, info in self.active_operations.items():
                # Consider operations stale after 2x timeout
                if current_time - info['start_time'] > info['timeout'] * 2:
                    stale_operations.append(operation_id)
            
            for operation_id in stale_operations:
                self._terminate_operation(operation_id)
                del self.active_operations[operation_id]
                cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"Force cleaned {cleaned_count} stale operations")
        
        return cleaned_count
    
    def cleanup(self) -> None:
        """Clean up resources."""
        # Stop monitoring
        self.monitor.stop_monitoring()
        
        # Terminate all active operations
        with self._lock:
            for operation_id in list(self.active_operations.keys()):
                self._terminate_operation(operation_id)
            self.active_operations.clear()
        
        logger.info("Resource guard cleanup complete")


class ResourceExhaustionError(Exception):
    """Exception raised when resource limits are exceeded."""
    pass


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is active."""
    pass


def create_resource_guard(protection_level: str = "STANDARD") -> ResourceGuard:
    """
    Factory function to create resource guard.
    
    Args:
        protection_level: Protection level (BASIC, STANDARD, STRICT, PARANOID)
        
    Returns:
        Configured ResourceGuard
    """
    limits = ResourceLimits.for_protection_level(protection_level)
    protection_enum = ProtectionLevel.HARD
    
    if protection_level == "BASIC":
        protection_enum = ProtectionLevel.SOFT
    elif protection_level in ["STRICT", "PARANOID"]:
        protection_enum = ProtectionLevel.STRICT
    
    return ResourceGuard(limits, protection_enum)