"""
Memory Optimizer for Batch Operations

Manages memory usage for efficient batch processing.
"""

import gc
import logging
import os
import psutil
import sys
from dataclasses import dataclass
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class MemoryStatus:
    """Memory usage status."""
    total: int  # Total memory in bytes
    available: int  # Available memory in bytes
    used: int  # Used memory in bytes
    percent: float  # Percentage used
    process_memory: int  # Current process memory usage
    
    @property
    def total_gb(self) -> float:
        """Total memory in GB."""
        return self.total / (1024 ** 3)
    
    @property
    def available_gb(self) -> float:
        """Available memory in GB."""
        return self.available / (1024 ** 3)
    
    @property
    def used_gb(self) -> float:
        """Used memory in GB."""
        return self.used / (1024 ** 3)
    
    @property
    def process_memory_mb(self) -> float:
        """Process memory in MB."""
        return self.process_memory / (1024 ** 2)


class MemoryOptimizer:
    """
    Memory optimization for batch processing.
    
    Features:
    - Memory usage monitoring
    - Automatic garbage collection
    - Memory mode detection
    - Adaptive optimization strategies
    """
    
    # Memory thresholds for different modes (in GB)
    MEMORY_THRESHOLDS = {
        'baseline': 2.0,    # <2GB
        'standard': 4.0,    # 2-4GB
        'enhanced': 8.0,    # 4-8GB
        'performance': None  # >8GB (no upper limit)
    }
    
    def __init__(self):
        """Initialize memory optimizer."""
        self.process = psutil.Process()
        self._last_gc_memory = 0
        self._gc_threshold = 100 * 1024 * 1024  # 100MB increase triggers GC
        
        # Detect initial memory mode
        self.memory_mode = self.detect_memory_mode()
        logger.info(f"Memory optimizer initialized. Mode: {self.memory_mode}")
    
    def get_memory_status(self) -> Dict[str, any]:
        """
        Get current memory status.
        
        Returns:
            Dictionary with memory information
        """
        # System memory
        mem = psutil.virtual_memory()
        
        # Process memory
        process_info = self.process.memory_info()
        
        status = MemoryStatus(
            total=mem.total,
            available=mem.available,
            used=mem.used,
            percent=mem.percent,
            process_memory=process_info.rss
        )
        
        return {
            'total': status.total,
            'available': status.available,
            'used': status.used,
            'percent': status.percent,
            'process_memory': status.process_memory,
            'total_gb': status.total_gb,
            'available_gb': status.available_gb,
            'used_gb': status.used_gb,
            'process_memory_mb': status.process_memory_mb
        }
    
    def detect_memory_mode(self) -> str:
        """
        Detect memory mode based on system RAM.
        
        Returns:
            Memory mode: 'baseline', 'standard', 'enhanced', or 'performance'
        """
        total_gb = psutil.virtual_memory().total / (1024 ** 3)
        
        if total_gb < self.MEMORY_THRESHOLDS['baseline']:
            return 'baseline'
        elif total_gb < self.MEMORY_THRESHOLDS['standard']:
            return 'standard'
        elif total_gb < self.MEMORY_THRESHOLDS['enhanced']:
            return 'enhanced'
        else:
            return 'performance'
    
    def optimize_memory(self, force: bool = False) -> bool:
        """
        Optimize memory usage.
        
        Args:
            force: Force garbage collection regardless of thresholds
            
        Returns:
            True if optimization was performed
        """
        current_memory = self.process.memory_info().rss
        memory_increase = current_memory - self._last_gc_memory
        
        # Check if optimization is needed
        should_optimize = force or (
            memory_increase > self._gc_threshold or
            psutil.virtual_memory().percent > 80
        )
        
        if should_optimize:
            logger.debug(f"Optimizing memory (current: {current_memory / 1024 / 1024:.1f}MB)")
            
            # Perform garbage collection
            gc.collect()
            
            # Full collection for high memory usage
            if psutil.virtual_memory().percent > 90:
                gc.collect(2)
            
            # Update last GC memory
            self._last_gc_memory = self.process.memory_info().rss
            
            # Log results
            new_memory = self.process.memory_info().rss
            freed = current_memory - new_memory
            if freed > 0:
                logger.info(f"Freed {freed / 1024 / 1024:.1f}MB of memory")
            
            return True
        
        return False
    
    def get_recommended_batch_size(self) -> int:
        """
        Get recommended batch size based on available memory.
        
        Returns:
            Recommended batch size
        """
        available_gb = psutil.virtual_memory().available / (1024 ** 3)
        
        # Recommendations based on available memory
        if available_gb < 0.5:
            return 10
        elif available_gb < 1:
            return 50
        elif available_gb < 2:
            return 100
        elif available_gb < 4:
            return 500
        else:
            return 1000
    
    def get_memory_pressure(self) -> str:
        """
        Get current memory pressure level.
        
        Returns:
            'low', 'medium', 'high', or 'critical'
        """
        percent = psutil.virtual_memory().percent
        
        if percent < 50:
            return 'low'
        elif percent < 70:
            return 'medium'
        elif percent < 85:
            return 'high'
        else:
            return 'critical'
    
    def should_throttle(self) -> bool:
        """
        Check if processing should be throttled due to memory pressure.
        
        Returns:
            True if processing should be slowed down
        """
        return self.get_memory_pressure() in ['high', 'critical']
    
    def get_optimization_strategy(self) -> Dict[str, any]:
        """
        Get optimization strategy based on current conditions.
        
        Returns:
            Dictionary with optimization recommendations
        """
        memory_mode = self.memory_mode
        memory_pressure = self.get_memory_pressure()
        
        strategy = {
            'mode': memory_mode,
            'pressure': memory_pressure,
            'batch_size': self.get_recommended_batch_size(),
            'gc_frequency': 'normal',
            'throttle': False,
            'cache_size': 'normal'
        }
        
        # Adjust based on memory mode
        if memory_mode == 'baseline':
            strategy['gc_frequency'] = 'aggressive'
            strategy['cache_size'] = 'minimal'
            if memory_pressure in ['high', 'critical']:
                strategy['throttle'] = True
                strategy['batch_size'] = min(10, strategy['batch_size'])
        
        elif memory_mode == 'standard':
            if memory_pressure == 'critical':
                strategy['gc_frequency'] = 'aggressive'
                strategy['throttle'] = True
                strategy['cache_size'] = 'small'
        
        elif memory_mode == 'enhanced':
            if memory_pressure == 'critical':
                strategy['gc_frequency'] = 'moderate'
                strategy['cache_size'] = 'medium'
        
        # Performance mode - minimal restrictions
        else:
            strategy['cache_size'] = 'large'
            if memory_pressure == 'critical':
                strategy['gc_frequency'] = 'moderate'
        
        return strategy
    
    def cleanup(self):
        """Perform memory cleanup."""
        # Clear caches
        gc.collect()
        
        # Clear interned strings (Python 3.8+)
        if hasattr(sys, 'intern'):
            try:
                # This is a best-effort cleanup
                gc.collect(2)
            except Exception:
                pass
        
        logger.debug("Memory cleanup completed")