"""
DevDocAI Operations Module
M011: Batch Operations Manager
"""

from .batch import (
    BatchConfig,
    BatchError,
    BatchMemoryError,
    BatchOperation,
    BatchOperationsManager,
    BatchResult,
    BatchStatus,
    BatchTimeoutError,
    DocumentBatch,
    ProcessingQueue,
    ProgressTracker,
    estimate_processing_time,
    process_documents_batch,
)

__all__ = [
    # Manager
    "BatchOperationsManager",
    # Configuration
    "BatchConfig",
    # Data Classes
    "BatchResult",
    "DocumentBatch",
    # Enums
    "BatchStatus",
    "BatchOperation",
    # Components
    "ProcessingQueue",
    "ProgressTracker",
    # Exceptions
    "BatchError",
    "BatchTimeoutError",
    "BatchMemoryError",
    # Functions
    "process_documents_batch",
    "estimate_processing_time",
]

__version__ = "3.0.0"