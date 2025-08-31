"""
Performance monitoring and tracking for M009 Enhancement Pipeline.

Provides real-time metrics collection, bottleneck identification,
resource usage tracking, and adaptive tuning.
"""

import asyncio
import logging
import time
import psutil
import threading
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict
import statistics
import json
from pathlib import Path
import tracemalloc
import cProfile
import pstats
import io
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Single performance metric measurement."""
    
    name: str
    value: float
    unit: str
    timestamp: datetime
    tags: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags
        }


@dataclass
class PerformanceSnapshot:
    """Snapshot of system performance at a point in time."""
    
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_sent_mb: float
    network_recv_mb: float
    active_threads: int
    open_files: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_mb": self.memory_mb,
            "disk_io_read_mb": self.disk_io_read_mb,
            "disk_io_write_mb": self.disk_io_write_mb,
            "network_sent_mb": self.network_sent_mb,
            "network_recv_mb": self.network_recv_mb,
            "active_threads": self.active_threads,
            "open_files": self.open_files
        }


@dataclass
class Bottleneck:
    """Identified performance bottleneck."""
    
    component: str
    severity: str  # "low", "medium", "high", "critical"
    description: str
    impact: str
    recommendation: str
    metrics: Dict[str, float]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "component": self.component,
            "severity": self.severity,
            "description": self.description,
            "impact": self.impact,
            "recommendation": self.recommendation,
            "metrics": self.metrics,
            "timestamp": self.timestamp.isoformat()
        }


class MetricsCollector:
    """Collect and aggregate performance metrics."""
    
    def __init__(self, window_size: int = 100):
        """
        Initialize metrics collector.
        
        Args:
            window_size: Size of sliding window for metrics
        """
        self.window_size = window_size
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self.counters: Dict[str, int] = defaultdict(int)
        self.timers: Dict[str, List[float]] = defaultdict(list)
        self.lock = threading.RLock()
    
    def record_metric(
        self,
        name: str,
        value: float,
        unit: str = "",
        tags: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a performance metric."""
        with self.lock:
            metric = PerformanceMetric(
                name=name,
                value=value,
                unit=unit,
                timestamp=datetime.now(),
                tags=tags or {}
            )
            self.metrics[name].append(metric)
    
    def increment_counter(self, name: str, value: int = 1) -> None:
        """Increment a counter metric."""
        with self.lock:
            self.counters[name] += value
    
    def record_time(self, name: str, duration: float) -> None:
        """Record a timing measurement."""
        with self.lock:
            self.timers[name].append(duration)
            # Keep only recent timings
            if len(self.timers[name]) > self.window_size:
                self.timers[name] = self.timers[name][-self.window_size:]
    
    @contextmanager
    def timer(self, name: str):
        """Context manager for timing operations."""
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            self.record_time(name, duration)
    
    def get_statistics(self, metric_name: str) -> Dict[str, float]:
        """Get statistics for a metric."""
        with self.lock:
            if metric_name in self.metrics:
                values = [m.value for m in self.metrics[metric_name]]
                if values:
                    return {
                        "mean": statistics.mean(values),
                        "median": statistics.median(values),
                        "stdev": statistics.stdev(values) if len(values) > 1 else 0,
                        "min": min(values),
                        "max": max(values),
                        "count": len(values)
                    }
            elif metric_name in self.timers:
                values = self.timers[metric_name]
                if values:
                    return {
                        "mean": statistics.mean(values),
                        "median": statistics.median(values),
                        "stdev": statistics.stdev(values) if len(values) > 1 else 0,
                        "min": min(values),
                        "max": max(values),
                        "p95": sorted(values)[int(len(values) * 0.95)] if values else 0,
                        "p99": sorted(values)[int(len(values) * 0.99)] if values else 0,
                        "count": len(values)
                    }
            return {}
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics."""
        with self.lock:
            return {
                "metrics": {
                    name: [m.to_dict() for m in metrics]
                    for name, metrics in self.metrics.items()
                },
                "counters": dict(self.counters),
                "timers": {
                    name: self.get_statistics(name)
                    for name in self.timers
                }
            }


class ResourceMonitor:
    """Monitor system resource usage."""
    
    def __init__(self, interval: float = 1.0):
        """
        Initialize resource monitor.
        
        Args:
            interval: Monitoring interval in seconds
        """
        self.interval = interval
        self.snapshots: deque = deque(maxlen=1000)
        self.process = psutil.Process()
        self.monitoring = False
        self.monitor_thread = None
        
        # Baseline measurements
        self.baseline_cpu = 0
        self.baseline_memory = 0
        self.baseline_disk_io = None
        self.baseline_network = None
    
    def start_monitoring(self) -> None:
        """Start resource monitoring."""
        if not self.monitoring:
            self.monitoring = True
            self.baseline_disk_io = psutil.disk_io_counters()
            self.baseline_network = psutil.net_io_counters()
            self.monitor_thread = threading.Thread(target=self._monitor_loop)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            logger.info("Resource monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop resource monitoring."""
        if self.monitoring:
            self.monitoring = False
            if self.monitor_thread:
                self.monitor_thread.join(timeout=2)
            logger.info("Resource monitoring stopped")
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self.monitoring:
            try:
                snapshot = self._take_snapshot()
                self.snapshots.append(snapshot)
            except Exception as e:
                logger.error(f"Error taking resource snapshot: {e}")
            
            time.sleep(self.interval)
    
    def _take_snapshot(self) -> PerformanceSnapshot:
        """Take a resource usage snapshot."""
        # CPU usage
        cpu_percent = self.process.cpu_percent()
        
        # Memory usage
        memory_info = self.process.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)
        memory_percent = self.process.memory_percent()
        
        # Disk I/O
        disk_io = psutil.disk_io_counters()
        disk_read_mb = (disk_io.read_bytes - self.baseline_disk_io.read_bytes) / (1024 * 1024) if self.baseline_disk_io else 0
        disk_write_mb = (disk_io.write_bytes - self.baseline_disk_io.write_bytes) / (1024 * 1024) if self.baseline_disk_io else 0
        
        # Network I/O
        net_io = psutil.net_io_counters()
        net_sent_mb = (net_io.bytes_sent - self.baseline_network.bytes_sent) / (1024 * 1024) if self.baseline_network else 0
        net_recv_mb = (net_io.bytes_recv - self.baseline_network.bytes_recv) / (1024 * 1024) if self.baseline_network else 0
        
        # Thread and file info
        active_threads = self.process.num_threads()
        try:
            open_files = len(self.process.open_files())
        except:
            open_files = 0
        
        return PerformanceSnapshot(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_mb=memory_mb,
            disk_io_read_mb=disk_read_mb,
            disk_io_write_mb=disk_write_mb,
            network_sent_mb=net_sent_mb,
            network_recv_mb=net_recv_mb,
            active_threads=active_threads,
            open_files=open_files
        )
    
    def get_current_usage(self) -> Dict[str, float]:
        """Get current resource usage."""
        if self.snapshots:
            latest = self.snapshots[-1]
            return {
                "cpu_percent": latest.cpu_percent,
                "memory_mb": latest.memory_mb,
                "memory_percent": latest.memory_percent,
                "threads": latest.active_threads
            }
        return {}
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get resource usage statistics."""
        if not self.snapshots:
            return {}
        
        cpu_values = [s.cpu_percent for s in self.snapshots]
        memory_values = [s.memory_mb for s in self.snapshots]
        
        return {
            "cpu": {
                "mean": statistics.mean(cpu_values),
                "max": max(cpu_values),
                "min": min(cpu_values)
            },
            "memory_mb": {
                "mean": statistics.mean(memory_values),
                "max": max(memory_values),
                "min": min(memory_values)
            },
            "samples": len(self.snapshots)
        }


class BottleneckDetector:
    """Detect and identify performance bottlenecks."""
    
    def __init__(
        self,
        cpu_threshold: float = 80.0,
        memory_threshold: float = 80.0,
        response_time_threshold: float = 2.0
    ):
        """
        Initialize bottleneck detector.
        
        Args:
            cpu_threshold: CPU usage threshold (%)
            memory_threshold: Memory usage threshold (%)
            response_time_threshold: Response time threshold (seconds)
        """
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.response_time_threshold = response_time_threshold
        self.bottlenecks: List[Bottleneck] = []
    
    def analyze(
        self,
        metrics: Dict[str, Any],
        resource_stats: Dict[str, Any]
    ) -> List[Bottleneck]:
        """
        Analyze metrics for bottlenecks.
        
        Args:
            metrics: Performance metrics
            resource_stats: Resource usage statistics
            
        Returns:
            List of identified bottlenecks
        """
        bottlenecks = []
        
        # Check CPU bottleneck
        if resource_stats.get("cpu", {}).get("mean", 0) > self.cpu_threshold:
            bottlenecks.append(Bottleneck(
                component="CPU",
                severity="high" if resource_stats["cpu"]["mean"] > 90 else "medium",
                description=f"High CPU usage: {resource_stats['cpu']['mean']:.1f}%",
                impact="Slow processing, increased latency",
                recommendation="Consider increasing workers or optimizing algorithms",
                metrics={"cpu_mean": resource_stats["cpu"]["mean"]},
                timestamp=datetime.now()
            ))
        
        # Check memory bottleneck
        if resource_stats.get("memory_mb", {}).get("max", 0) > 400:  # Near 500MB limit
            bottlenecks.append(Bottleneck(
                component="Memory",
                severity="high" if resource_stats["memory_mb"]["max"] > 450 else "medium",
                description=f"High memory usage: {resource_stats['memory_mb']['max']:.1f}MB",
                impact="Risk of out-of-memory errors, reduced cache efficiency",
                recommendation="Implement streaming processing or reduce batch sizes",
                metrics={"memory_max_mb": resource_stats["memory_mb"]["max"]},
                timestamp=datetime.now()
            ))
        
        # Check response time bottleneck
        timer_stats = metrics.get("timers", {})
        for timer_name, stats in timer_stats.items():
            if stats.get("p95", 0) > self.response_time_threshold:
                bottlenecks.append(Bottleneck(
                    component=timer_name,
                    severity="high" if stats["p95"] > self.response_time_threshold * 2 else "medium",
                    description=f"Slow response time for {timer_name}: p95={stats['p95']:.2f}s",
                    impact="Poor user experience, timeout risks",
                    recommendation="Optimize algorithm or add caching",
                    metrics={"p95": stats["p95"], "p99": stats.get("p99", 0)},
                    timestamp=datetime.now()
                ))
        
        # Check cache performance
        cache_hit_ratio = metrics.get("counters", {}).get("cache_hits", 0) / (
            metrics.get("counters", {}).get("cache_hits", 0) + 
            metrics.get("counters", {}).get("cache_misses", 1)
        )
        if cache_hit_ratio < 0.3:  # Below 30% target
            bottlenecks.append(Bottleneck(
                component="Cache",
                severity="medium",
                description=f"Low cache hit ratio: {cache_hit_ratio:.1%}",
                impact="Increased processing time, redundant computations",
                recommendation="Increase cache size or improve cache key strategy",
                metrics={"hit_ratio": cache_hit_ratio},
                timestamp=datetime.now()
            ))
        
        self.bottlenecks.extend(bottlenecks)
        return bottlenecks


class AdaptiveTuner:
    """Adaptive performance tuning based on metrics."""
    
    def __init__(self):
        """Initialize adaptive tuner."""
        self.tuning_history: List[Dict[str, Any]] = []
        self.current_settings = {
            "batch_size": 10,
            "max_workers": 4,
            "cache_size": 1000,
            "timeout": 30
        }
    
    def recommend_tuning(
        self,
        bottlenecks: List[Bottleneck],
        metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Recommend tuning adjustments.
        
        Args:
            bottlenecks: Identified bottlenecks
            metrics: Current performance metrics
            
        Returns:
            Recommended settings adjustments
        """
        recommendations = {}
        
        for bottleneck in bottlenecks:
            if bottleneck.component == "CPU" and bottleneck.severity in ["high", "critical"]:
                # Reduce parallelism if CPU-bound
                recommendations["max_workers"] = max(2, self.current_settings["max_workers"] - 1)
            
            elif bottleneck.component == "Memory" and bottleneck.severity in ["high", "critical"]:
                # Reduce batch size if memory-bound
                recommendations["batch_size"] = max(5, self.current_settings["batch_size"] - 2)
                recommendations["cache_size"] = max(500, self.current_settings["cache_size"] - 200)
            
            elif bottleneck.component == "Cache":
                # Increase cache size if hit ratio is low
                recommendations["cache_size"] = min(2000, self.current_settings["cache_size"] + 500)
            
            elif "response_time" in bottleneck.component.lower():
                # Increase timeout for slow operations
                recommendations["timeout"] = min(60, self.current_settings["timeout"] + 10)
        
        # Record tuning decision
        self.tuning_history.append({
            "timestamp": datetime.now().isoformat(),
            "bottlenecks": [b.to_dict() for b in bottlenecks],
            "current_settings": self.current_settings.copy(),
            "recommendations": recommendations
        })
        
        return recommendations
    
    def apply_tuning(self, settings: Dict[str, Any]) -> None:
        """Apply tuning recommendations."""
        self.current_settings.update(settings)
        logger.info(f"Applied tuning: {settings}")


class PerformanceProfiler:
    """Profile code execution for optimization."""
    
    def __init__(self):
        """Initialize profiler."""
        self.profiler = cProfile.Profile()
        self.profiling = False
    
    def start_profiling(self) -> None:
        """Start profiling."""
        if not self.profiling:
            self.profiler.enable()
            self.profiling = True
            tracemalloc.start()
    
    def stop_profiling(self) -> Dict[str, Any]:
        """Stop profiling and get results."""
        if self.profiling:
            self.profiler.disable()
            self.profiling = False
            
            # Get profiling stats
            s = io.StringIO()
            ps = pstats.Stats(self.profiler, stream=s).sort_stats('cumulative')
            ps.print_stats(20)  # Top 20 functions
            
            # Get memory stats
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            return {
                "profile": s.getvalue(),
                "memory_current_mb": current / (1024 * 1024),
                "memory_peak_mb": peak / (1024 * 1024)
            }
        return {}


class PerformanceMonitor:
    """
    Comprehensive performance monitoring system.
    
    Integrates metrics collection, resource monitoring,
    bottleneck detection, and adaptive tuning.
    """
    
    def __init__(
        self,
        enable_resource_monitoring: bool = True,
        enable_bottleneck_detection: bool = True,
        enable_adaptive_tuning: bool = False,
        monitoring_interval: float = 1.0
    ):
        """
        Initialize performance monitor.
        
        Args:
            enable_resource_monitoring: Enable system resource monitoring
            enable_bottleneck_detection: Enable bottleneck detection
            enable_adaptive_tuning: Enable adaptive tuning
            monitoring_interval: Monitoring interval in seconds
        """
        # Components
        self.metrics_collector = MetricsCollector()
        self.resource_monitor = ResourceMonitor(monitoring_interval) if enable_resource_monitoring else None
        self.bottleneck_detector = BottleneckDetector() if enable_bottleneck_detection else None
        self.adaptive_tuner = AdaptiveTuner() if enable_adaptive_tuning else None
        self.profiler = PerformanceProfiler()
        
        # Configuration
        self.monitoring_interval = monitoring_interval
        self.report_interval = 60  # Generate report every 60 seconds
        self.last_report_time = time.time()
        
        # Start monitoring
        if self.resource_monitor:
            self.resource_monitor.start_monitoring()
        
        logger.info(
            f"Performance monitor initialized: resource={enable_resource_monitoring}, "
            f"bottleneck={enable_bottleneck_detection}, adaptive={enable_adaptive_tuning}"
        )
    
    def record_operation(
        self,
        operation: str,
        duration: float,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record an operation's performance."""
        self.metrics_collector.record_time(f"{operation}_duration", duration)
        
        if success:
            self.metrics_collector.increment_counter(f"{operation}_success")
        else:
            self.metrics_collector.increment_counter(f"{operation}_failure")
        
        if metadata:
            for key, value in metadata.items():
                if isinstance(value, (int, float)):
                    self.metrics_collector.record_metric(f"{operation}_{key}", value)
    
    @contextmanager
    def measure(self, operation: str):
        """Context manager to measure operation performance."""
        start = time.time()
        success = True
        try:
            yield
        except Exception as e:
            success = False
            raise
        finally:
            duration = time.time() - start
            self.record_operation(operation, duration, success)
    
    def check_bottlenecks(self) -> List[Bottleneck]:
        """Check for performance bottlenecks."""
        if not self.bottleneck_detector:
            return []
        
        metrics = self.metrics_collector.get_all_metrics()
        resource_stats = self.resource_monitor.get_statistics() if self.resource_monitor else {}
        
        return self.bottleneck_detector.analyze(metrics, resource_stats)
    
    def get_tuning_recommendations(self) -> Dict[str, Any]:
        """Get adaptive tuning recommendations."""
        if not self.adaptive_tuner:
            return {}
        
        bottlenecks = self.check_bottlenecks()
        metrics = self.metrics_collector.get_all_metrics()
        
        return self.adaptive_tuner.recommend_tuning(bottlenecks, metrics)
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "metrics": self.metrics_collector.get_all_metrics(),
            "resource_usage": self.resource_monitor.get_statistics() if self.resource_monitor else {},
            "current_usage": self.resource_monitor.get_current_usage() if self.resource_monitor else {},
            "bottlenecks": [b.to_dict() for b in self.check_bottlenecks()],
            "tuning_recommendations": self.get_tuning_recommendations() if self.adaptive_tuner else {}
        }
        
        # Auto-generate report at intervals
        current_time = time.time()
        if current_time - self.last_report_time > self.report_interval:
            self.last_report_time = current_time
            self.save_report(report)
        
        return report
    
    def save_report(self, report: Dict[str, Any], path: Optional[Path] = None) -> None:
        """Save performance report to file."""
        if path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = Path(f"performance_report_{timestamp}.json")
        
        with open(path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Performance report saved to {path}")
    
    def shutdown(self) -> None:
        """Shutdown performance monitor."""
        if self.resource_monitor:
            self.resource_monitor.stop_monitoring()
        
        # Generate final report
        final_report = self.generate_report()
        self.save_report(final_report)
        
        logger.info("Performance monitor shutdown complete")