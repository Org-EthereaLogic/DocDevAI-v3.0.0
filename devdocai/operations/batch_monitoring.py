"""
M011 Batch Operations Manager - Monitoring & Metrics Module
DevDocAI v3.0.0 - Pass 4: Refactoring & Integration

Purpose: Extract monitoring, metrics, and progress tracking
Dependencies: None (pure monitoring implementation)
Performance: Lightweight with minimal overhead

Observer Pattern for batch operation monitoring:
- ProgressTracker: Real-time progress tracking
- MetricsCollector: Performance metrics collection
- BatchMonitor: Comprehensive monitoring
- EventPublisher: Event-driven notifications
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import psutil

logger = logging.getLogger(__name__)


# ============================================================================
# Event Types
# ============================================================================


class BatchEvent(Enum):
    """Batch operation events."""

    BATCH_STARTED = "batch_started"
    BATCH_COMPLETED = "batch_completed"
    BATCH_FAILED = "batch_failed"
    DOCUMENT_STARTED = "document_started"
    DOCUMENT_COMPLETED = "document_completed"
    DOCUMENT_FAILED = "document_failed"
    PROGRESS_UPDATE = "progress_update"
    PERFORMANCE_WARNING = "performance_warning"
    MEMORY_WARNING = "memory_warning"
    RATE_LIMIT_HIT = "rate_limit_hit"


# ============================================================================
# Metrics Data Classes
# ============================================================================


@dataclass
class BatchMetrics:
    """Comprehensive batch processing metrics."""

    # Document counts
    total_documents: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0

    # Timing metrics
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    total_time: float = 0.0
    average_time_per_doc: float = 0.0

    # Performance metrics
    throughput_per_hour: float = 0.0
    throughput_per_minute: float = 0.0
    success_rate: float = 0.0

    # Resource metrics
    peak_memory_mb: float = 0.0
    average_memory_mb: float = 0.0
    peak_cpu_percent: float = 0.0
    average_cpu_percent: float = 0.0

    # Cache metrics
    cache_hits: int = 0
    cache_misses: int = 0
    cache_hit_rate: float = 0.0

    # Retry metrics
    retry_count: int = 0
    retry_success: int = 0

    def calculate_derived_metrics(self):
        """Calculate derived metrics from raw data."""
        if self.end_time and self.start_time:
            self.total_time = self.end_time - self.start_time

        if self.total_documents > 0:
            self.success_rate = (self.successful / self.total_documents) * 100

            if self.total_time > 0:
                self.average_time_per_doc = self.total_time / self.total_documents
                self.throughput_per_hour = (self.total_documents / self.total_time) * 3600
                self.throughput_per_minute = (self.total_documents / self.total_time) * 60

        total_cache_requests = self.cache_hits + self.cache_misses
        if total_cache_requests > 0:
            self.cache_hit_rate = (self.cache_hits / total_cache_requests) * 100


# ============================================================================
# Progress Tracker
# ============================================================================


class ProgressTracker:
    """Real-time progress tracking for batch operations."""

    def __init__(self, total: int = 0):
        """Initialize progress tracker."""
        self.total = total
        self.completed = 0
        self.failed = 0
        self.current_document: Optional[str] = None
        self.start_time = time.time()
        self.last_update_time = time.time()
        self._lock = asyncio.Lock()
        self._update_callbacks: List[Callable] = []

    async def update(self, completed: int = 0, failed: int = 0, current: Optional[str] = None):
        """Update progress with thread safety."""
        async with self._lock:
            self.completed += completed
            self.failed += failed
            if current:
                self.current_document = current
            self.last_update_time = time.time()

            # Trigger callbacks
            for callback in self._update_callbacks:
                if asyncio.iscoroutinefunction(callback):
                    await callback(self.get_status())
                else:
                    callback(self.get_status())

    def get_percentage(self) -> float:
        """Get completion percentage."""
        if self.total == 0:
            return 0.0
        return (self.completed / self.total) * 100

    def get_eta(self) -> Optional[timedelta]:
        """Get estimated time remaining."""
        if self.completed == 0:
            return None

        elapsed = time.time() - self.start_time
        rate = self.completed / elapsed
        remaining = self.total - self.completed

        if rate > 0:
            seconds_remaining = remaining / rate
            return timedelta(seconds=seconds_remaining)
        return None

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status."""
        elapsed = time.time() - self.start_time
        eta = self.get_eta()

        return {
            "total": self.total,
            "completed": self.completed,
            "failed": self.failed,
            "percentage": self.get_percentage(),
            "current_document": self.current_document,
            "elapsed_seconds": elapsed,
            "eta_seconds": eta.total_seconds() if eta else None,
            "rate_per_minute": (self.completed / elapsed * 60) if elapsed > 0 else 0,
        }

    def add_callback(self, callback: Callable):
        """Add progress update callback."""
        self._update_callbacks.append(callback)

    def reset(self, total: int = 0):
        """Reset tracker for new batch."""
        self.total = total
        self.completed = 0
        self.failed = 0
        self.current_document = None
        self.start_time = time.time()
        self.last_update_time = time.time()


# ============================================================================
# Metrics Collector
# ============================================================================


class MetricsCollector:
    """Collect and aggregate batch processing metrics."""

    def __init__(self):
        """Initialize metrics collector."""
        self.metrics = BatchMetrics()
        self._memory_samples: List[float] = []
        self._cpu_samples: List[float] = []
        self._document_times: List[float] = []
        self._monitoring_task: Optional[asyncio.Task] = None

    async def start_monitoring(self, interval: float = 1.0):
        """Start resource monitoring."""
        if self._monitoring_task:
            return

        self._monitoring_task = asyncio.create_task(self._monitor_resources(interval))

    async def stop_monitoring(self):
        """Stop resource monitoring."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None

    async def _monitor_resources(self, interval: float):
        """Monitor system resources periodically."""
        process = psutil.Process()

        while True:
            try:
                # Sample memory
                memory_mb = process.memory_info().rss / (1024 * 1024)
                self._memory_samples.append(memory_mb)

                # Sample CPU
                cpu_percent = process.cpu_percent()
                self._cpu_samples.append(cpu_percent)

                # Update peaks
                self.metrics.peak_memory_mb = max(self.metrics.peak_memory_mb, memory_mb)
                self.metrics.peak_cpu_percent = max(self.metrics.peak_cpu_percent, cpu_percent)

                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Resource monitoring error: {e}")
                await asyncio.sleep(interval)

    def record_document_time(self, processing_time: float):
        """Record individual document processing time."""
        self._document_times.append(processing_time)

    def record_cache_hit(self):
        """Record cache hit."""
        self.metrics.cache_hits += 1

    def record_cache_miss(self):
        """Record cache miss."""
        self.metrics.cache_misses += 1

    def record_retry(self, successful: bool = False):
        """Record retry attempt."""
        self.metrics.retry_count += 1
        if successful:
            self.metrics.retry_success += 1

    def finalize(self):
        """Finalize metrics calculation."""
        self.metrics.end_time = time.time()

        # Calculate averages
        if self._memory_samples:
            self.metrics.average_memory_mb = sum(self._memory_samples) / len(self._memory_samples)

        if self._cpu_samples:
            self.metrics.average_cpu_percent = sum(self._cpu_samples) / len(self._cpu_samples)

        # Calculate derived metrics
        self.metrics.calculate_derived_metrics()

    def get_metrics(self) -> BatchMetrics:
        """Get current metrics."""
        return self.metrics

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        return {
            "documents": {
                "total": self.metrics.total_documents,
                "successful": self.metrics.successful,
                "failed": self.metrics.failed,
                "success_rate": f"{self.metrics.success_rate:.1f}%",
            },
            "performance": {
                "total_time": f"{self.metrics.total_time:.2f}s",
                "throughput": f"{self.metrics.throughput_per_minute:.1f} docs/min",
                "avg_time_per_doc": f"{self.metrics.average_time_per_doc:.3f}s",
            },
            "resources": {
                "peak_memory": f"{self.metrics.peak_memory_mb:.1f} MB",
                "avg_memory": f"{self.metrics.average_memory_mb:.1f} MB",
                "peak_cpu": f"{self.metrics.peak_cpu_percent:.1f}%",
                "avg_cpu": f"{self.metrics.average_cpu_percent:.1f}%",
            },
            "cache": {
                "hits": self.metrics.cache_hits,
                "misses": self.metrics.cache_misses,
                "hit_rate": f"{self.metrics.cache_hit_rate:.1f}%",
            },
        }


# ============================================================================
# Batch Monitor
# ============================================================================


class BatchMonitor:
    """Comprehensive batch operation monitoring."""

    def __init__(self):
        """Initialize batch monitor."""
        self.progress_tracker = ProgressTracker()
        self.metrics_collector = MetricsCollector()
        self._event_listeners: Dict[BatchEvent, List[Callable]] = {}
        self._active = False

    async def start_batch(self, total_documents: int):
        """Start monitoring a new batch."""
        self._active = True
        self.progress_tracker.reset(total_documents)
        self.metrics_collector = MetricsCollector()
        self.metrics_collector.metrics.total_documents = total_documents

        await self.metrics_collector.start_monitoring()
        await self._publish_event(
            BatchEvent.BATCH_STARTED,
            {
                "total_documents": total_documents,
                "start_time": datetime.now().isoformat(),
            },
        )

    async def end_batch(self, success: bool = True):
        """End batch monitoring."""
        self._active = False
        await self.metrics_collector.stop_monitoring()
        self.metrics_collector.finalize()

        event = BatchEvent.BATCH_COMPLETED if success else BatchEvent.BATCH_FAILED
        await self._publish_event(
            event,
            {
                "metrics": self.metrics_collector.get_summary(),
                "end_time": datetime.now().isoformat(),
            },
        )

    async def record_document_start(self, document_id: str):
        """Record document processing start."""
        await self.progress_tracker.update(current=document_id)
        await self._publish_event(
            BatchEvent.DOCUMENT_STARTED,
            {
                "document_id": document_id,
            },
        )

    async def record_document_complete(
        self, document_id: str, success: bool, processing_time: float
    ):
        """Record document processing completion."""
        if success:
            await self.progress_tracker.update(completed=1)
            self.metrics_collector.metrics.successful += 1
            event = BatchEvent.DOCUMENT_COMPLETED
        else:
            await self.progress_tracker.update(failed=1)
            self.metrics_collector.metrics.failed += 1
            event = BatchEvent.DOCUMENT_FAILED

        self.metrics_collector.record_document_time(processing_time)

        await self._publish_event(
            event,
            {
                "document_id": document_id,
                "processing_time": processing_time,
            },
        )

    def subscribe(self, event: BatchEvent, callback: Callable):
        """Subscribe to batch events."""
        if event not in self._event_listeners:
            self._event_listeners[event] = []
        self._event_listeners[event].append(callback)

    async def _publish_event(self, event: BatchEvent, data: Dict[str, Any]):
        """Publish event to listeners."""
        if event in self._event_listeners:
            for callback in self._event_listeners[event]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event, data)
                    else:
                        callback(event, data)
                except Exception as e:
                    logger.error(f"Event listener error: {e}")

    def get_progress(self) -> Dict[str, Any]:
        """Get current progress status."""
        return self.progress_tracker.get_status()

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        return self.metrics_collector.get_summary()

    def is_active(self) -> bool:
        """Check if monitoring is active."""
        return self._active
