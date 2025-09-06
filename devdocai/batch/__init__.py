"""
M011: Batch Operations Manager

Efficient processing of multiple documents with memory-aware concurrency control.
Per SDD Section 5.6 specifications.
"""

from .batch_manager import BatchOperationsManager
from .processing_queue import ProcessingQueue
from .memory_optimizer import MemoryOptimizer
from .progress_tracker import ProgressTracker

__version__ = "3.0.0"
__module_id__ = "M011"

__all__ = [
    "BatchOperationsManager",
    "ProcessingQueue", 
    "MemoryOptimizer",
    "ProgressTracker",
]