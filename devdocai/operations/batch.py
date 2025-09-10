"""
M011 Batch Operations Manager - Core Implementation
DevDocAI v3.0.0 - Pass 1: Core Implementation

Purpose: Memory-aware batch document processing with concurrent execution
Requirements: Support for large documentation suites with progress tracking
Dependencies: M001 (Configuration), M002 (Storage), M009 (Enhancement Pipeline)
Performance Targets: 50-500 docs/hr based on memory mode

Enhanced 4-Pass TDD Development - Pass 1: Core Implementation
Focus: Memory-aware processing, async operations, progress tracking
"""

import asyncio
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# Local imports - foundation modules
from ..core.config import ConfigurationManager
from ..core.storage import StorageManager

# Expose EnhancementPipeline for test patching and integration
# Import lazily-safe: if the dependency is unavailable during import,
# provide a placeholder that tests can patch.
try:  # pragma: no cover - simple availability shim
    from ..intelligence.enhance import EnhancementPipeline  # type: ignore
except Exception:  # pragma: no cover
    EnhancementPipeline = None  # Will be patched in tests

logger = logging.getLogger(__name__)


# ============================================================================
# Exceptions
# ============================================================================


class BatchError(Exception):
    """Base exception for batch operations."""

    pass


class BatchTimeoutError(BatchError):
    """Raised when batch operation times out."""

    pass


class BatchMemoryError(BatchError):
    """Raised when memory limit is exceeded."""

    pass


# ============================================================================
# Enums and Constants
# ============================================================================


class BatchStatus(Enum):
    """Status of batch operation."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some documents succeeded, some failed


class BatchOperation(Enum):
    """Types of batch operations."""

    ENHANCE = "enhance"
    GENERATE = "generate"
    REVIEW = "review"
    VALIDATE = "validate"
    CUSTOM = "custom"


# Memory mode concurrency mapping
CONCURRENCY_MAP = {
    "baseline": 1,  # <2GB RAM - sequential processing
    "standard": 4,  # 2-4GB RAM - limited concurrency
    "enhanced": 8,  # 4-8GB RAM - moderate concurrency
    "performance": 16,  # >8GB RAM - high concurrency
}

# Performance targets (docs/hour)
PERFORMANCE_TARGETS = {
    "baseline": 50,
    "standard": 100,
    "enhanced": 200,
    "performance": 500,
}


# ============================================================================
# Configuration
# ============================================================================


@dataclass
class BatchConfig:
    """Configuration for batch operations."""

    memory_mode: str = "auto"  # Memory mode (auto-detect or manual)
    max_concurrent: int = 4  # Maximum concurrent operations
    batch_size: int = 10  # Documents per batch
    enable_progress: bool = True  # Enable progress tracking
    timeout_seconds: float = 300.0  # Operation timeout (5 minutes)
    retry_attempts: int = 3  # Retry attempts for failed operations
    memory_limit_mb: int = 512  # Memory limit for processing
    save_partial_results: bool = True  # Save results even if some fail

    def get_concurrency(self) -> int:
        """Get concurrency level based on memory mode."""
        if self.memory_mode in CONCURRENCY_MAP:
            return CONCURRENCY_MAP[self.memory_mode]
        return self.max_concurrent

    def get_concurrency_for_mode(self, mode: str) -> int:
        """Get concurrency for specific memory mode."""
        return CONCURRENCY_MAP.get(mode, 4)


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class BatchResult:
    """Result of processing a single document in batch."""

    success: bool
    document_id: str
    operation: str
    result: Optional[Any] = None
    error: Optional[str] = None
    processing_time: float = 0.0
    retry_count: int = 0


@dataclass
class BatchMetrics:
    """Metrics for batch processing."""

    total_documents: int = 0
    successful: int = 0
    failed: int = 0
    total_time: float = 0.0
    average_time_per_doc: float = 0.0
    success_rate: float = 0.0
    throughput_per_hour: float = 0.0
    memory_peak_mb: float = 0.0
    retry_count: int = 0


@dataclass
class DocumentBatch:
    """A batch of documents for processing."""

    batch_id: str
    documents: List[Dict[str, Any]]
    priority: int = 0  # Lower number = higher priority
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def size(self) -> int:
        """Get number of documents in batch."""
        return len(self.documents)


# ============================================================================
# Progress Tracking
# ============================================================================


class ProgressTracker:
    """Track progress of batch operations."""

    def __init__(self, total: int = 0):
        """Initialize progress tracker."""
        self.total = total
        self.completed = 0
        self.failed = 0
        self.start_time = time.time()
        self._lock = asyncio.Lock()

    def update(self, completed: int = 1, failed: int = 0):
        """Update progress counts."""
        self.completed += completed
        self.failed += failed

    def get_percentage(self) -> float:
        """Get completion percentage."""
        if self.total == 0:
            return 0.0
        return (self.completed / self.total) * 100

    def get_status(self) -> Dict[str, Any]:
        """Get current progress status."""
        elapsed = time.time() - self.start_time
        success_count = self.completed - self.failed

        return {
            "total": self.total,
            "completed": self.completed,
            "failed": self.failed,
            "percentage": self.get_percentage(),
            "elapsed_seconds": elapsed,
            "success_rate": (success_count / self.completed * 100) if self.completed > 0 else 0.0,
        }

    def get_eta(self) -> Optional[float]:
        """Get estimated time remaining in seconds."""
        if self.completed == 0:
            return None

        elapsed = time.time() - self.start_time
        rate = self.completed / elapsed
        remaining = self.total - self.completed

        if rate > 0:
            return remaining / rate
        return None

    def reset(self, total: int = 0):
        """Reset progress tracker."""
        self.total = total
        self.completed = 0
        self.failed = 0
        self.start_time = time.time()


# ============================================================================
# Processing Queue
# ============================================================================


class ProcessingQueue:
    """Queue for managing documents to be processed."""

    def __init__(self):
        """Initialize processing queue."""
        self._queue: asyncio.Queue = asyncio.Queue()
        self._priority_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._use_priority = False

    async def add(self, document: Dict[str, Any], priority: int = 0):
        """Add document to queue."""
        if "priority" in document or priority != 0:
            self._use_priority = True
            item_priority = document.get("priority", priority)
            await self._priority_queue.put((item_priority, document))
        else:
            await self._queue.put(document)

    async def add_batch(self, documents: List[Dict[str, Any]]):
        """Add multiple documents to queue."""
        for doc in documents:
            await self.add(doc)

    async def get(self) -> Optional[Dict[str, Any]]:
        """Get next document from queue."""
        if self._use_priority and not self._priority_queue.empty():
            _, document = await self._priority_queue.get()
            return document
        elif not self._queue.empty():
            return await self._queue.get()
        return None

    async def get_batch(self, size: int) -> List[Dict[str, Any]]:
        """Get batch of documents from queue."""
        batch = []
        for _ in range(size):
            doc = await self.get()
            if doc is None:
                break
            batch.append(doc)
        return batch

    def size(self) -> int:
        """Get queue size."""
        return self._queue.qsize() + self._priority_queue.qsize()

    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self._queue.empty() and self._priority_queue.empty()

    async def clear(self):
        """Clear all documents from queue."""
        while not self.is_empty():
            await self.get()


# ============================================================================
# Batch Operations Manager
# ============================================================================


class BatchOperationsManager:
    """
    Manages batch processing of documents with memory awareness.

    Features:
    - Memory-aware concurrency control
    - Async batch processing with progress tracking
    - Integration with enhancement pipeline
    - Error handling and retry mechanism
    """

    def __init__(self, config: Optional[BatchConfig] = None):
        """Initialize batch operations manager."""
        # Configuration
        self._config_manager = ConfigurationManager()
        self.config = config or BatchConfig()

        # Auto-detect memory mode if set to "auto"
        if self.config.memory_mode == "auto":
            self.memory_mode = self._config_manager.system.memory_mode
        else:
            self.memory_mode = self.config.memory_mode

        # Set concurrency based on memory mode
        self.max_concurrent = self.config.get_concurrency()
        if self.memory_mode in CONCURRENCY_MAP:
            self.max_concurrent = CONCURRENCY_MAP[self.memory_mode]

        # Initialize components
        self.queue = ProcessingQueue()
        self.progress = ProgressTracker()
        self._executor = ThreadPoolExecutor(max_workers=self.max_concurrent)
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        self._storage = None  # Lazy initialization
        self._enhancement_pipeline = None  # Lazy initialization

        logger.info(
            f"BatchOperationsManager initialized: "
            f"memory_mode={self.memory_mode}, "
            f"max_concurrent={self.max_concurrent}"
        )

    async def process_document(
        self,
        document: Dict[str, Any],
        operation: Union[str, Callable],
        **kwargs,
    ) -> BatchResult:
        """
        Process a single document.

        Args:
            document: Document to process
            operation: Operation to perform (string or callable)
            **kwargs: Additional arguments for operation

        Returns:
            BatchResult with processing outcome
        """
        start_time = time.time()
        doc_id = document.get("id", "unknown")

        try:
            # Get operation function
            if isinstance(operation, str):
                op_func = self._get_operation(operation)
            else:
                op_func = operation

            # Validate operation
            if not callable(op_func):
                raise BatchError(f"Invalid operation: {operation}")

            # Execute operation with retry
            result = await self._execute_with_retry(
                op_func,
                document,
                **kwargs,
            )

            return BatchResult(
                success=True,
                document_id=doc_id,
                operation=str(operation),
                result=result,
                processing_time=time.time() - start_time,
            )

        except Exception as e:
            logger.error(f"Failed to process document {doc_id}: {e}")
            return BatchResult(
                success=False,
                document_id=doc_id,
                operation=str(operation),
                error=str(e),
                processing_time=time.time() - start_time,
            )

    async def process_batch(
        self,
        documents: List[Dict[str, Any]],
        operation: Union[str, Callable],
        **kwargs,
    ) -> List[BatchResult]:
        """
        Process multiple documents in batch.

        Args:
            documents: List of documents to process
            operation: Operation to perform
            **kwargs: Additional arguments

        Returns:
            List of BatchResult objects
        """
        if not documents:
            return []

        # Validate operation early if provided as a string so invalid
        # operations raise BatchError as expected by tests/contract.
        if isinstance(operation, str):
            self._get_operation(operation)

        # Check memory limit
        self._check_memory_limit(documents)

        # Reset progress tracker
        self.progress.reset(total=len(documents))

        # Validate documents up-front; produce failure results for malformed
        # entries rather than attempting to process them.
        pre_results: List[BatchResult] = []
        valid_documents: List[Dict[str, Any]] = []
        for doc in documents:
            if not isinstance(doc, dict) or not doc.get("id"):
                pre_results.append(
                    BatchResult(
                        success=False,
                        document_id=(doc.get("id") if isinstance(doc, dict) else "unknown")
                        or "unknown",
                        operation=str(operation),
                        error="Invalid document",
                    )
                )
                # Track as failed progress
                self.progress.update(failed=1)
            else:
                valid_documents.append(doc)

        # Create batches based on configuration
        batches = self._create_batches(valid_documents)

        # Process batches concurrently
        results = []
        for batch in batches:
            batch_results = await self._process_batch_concurrent(
                batch,
                operation,
                **kwargs,
            )
            results.extend(batch_results)

        logger.info(
            f"Batch processing complete: "
            f"{len(results)} documents, "
            f"{self.progress.completed - self.progress.failed} successful"
        )

        return pre_results + results

    async def _process_batch_concurrent(
        self,
        batch: DocumentBatch,
        operation: Union[str, Callable],
        **kwargs,
    ) -> List[BatchResult]:
        """Process batch with concurrent execution."""
        tasks = []

        async with self._semaphore:
            for document in batch.documents:
                task = asyncio.create_task(
                    self._process_with_timeout(
                        document,
                        operation,
                        **kwargs,
                    )
                )
                tasks.append(task)

        # Wait for all tasks with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.config.timeout_seconds,
            )
        except asyncio.TimeoutError:
            # Cancel remaining tasks
            for task in tasks:
                if not task.done():
                    task.cancel()

            # Return timeout error for all documents
            return [
                BatchResult(
                    success=False,
                    document_id=doc.get("id", "unknown"),
                    operation=str(operation),
                    error="Batch operation timeout",
                )
                for doc in batch.documents
            ]

        # Process results
        batch_results = []
        for result in results:
            if isinstance(result, Exception):
                # Handle exception
                batch_results.append(
                    BatchResult(
                        success=False,
                        document_id="unknown",
                        operation=str(operation),
                        error=str(result),
                    )
                )
                self.progress.update(failed=1)
            else:
                batch_results.append(result)
                if result.success:
                    self.progress.update(completed=1)
                else:
                    self.progress.update(failed=1)

        return batch_results

    async def _process_with_timeout(
        self,
        document: Dict[str, Any],
        operation: Union[str, Callable],
        **kwargs,
    ) -> BatchResult:
        """Process document with timeout."""
        try:
            return await asyncio.wait_for(
                self.process_document(document, operation, **kwargs),
                timeout=self.config.timeout_seconds,
            )
        except asyncio.TimeoutError:
            return BatchResult(
                success=False,
                document_id=document.get("id", "unknown"),
                operation=str(operation),
                error=f"Operation timeout after {self.config.timeout_seconds}s",
            )

    async def _execute_with_retry(
        self,
        operation: Callable,
        document: Dict[str, Any],
        **kwargs,
    ) -> Any:
        """Execute operation with retry mechanism."""
        last_error = None

        for attempt in range(self.config.retry_attempts):
            try:
                # Execute operation
                if asyncio.iscoroutinefunction(operation):
                    result = await operation(document, **kwargs)
                else:
                    # Run sync operation in executor
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        self._executor,
                        operation,
                        document,
                        **kwargs,
                    )
                return result

            except Exception as e:
                last_error = e
                if attempt < self.config.retry_attempts - 1:
                    # Wait before retry (exponential backoff)
                    await asyncio.sleep(2**attempt)
                    logger.debug(f"Retrying operation (attempt {attempt + 2})")

        # All retries failed
        raise last_error

    def _create_batches(self, documents: List[Dict[str, Any]]) -> List[DocumentBatch]:
        """Create document batches based on configuration."""
        batches = []
        batch_size = self.config.batch_size

        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i : i + batch_size]
            batch = DocumentBatch(
                batch_id=f"batch_{i // batch_size}",
                documents=batch_docs,
            )
            batches.append(batch)

        return batches

    def _check_memory_limit(self, documents: List[Dict[str, Any]]):
        """Check if documents exceed memory limit."""
        # Estimate memory usage (rough calculation)
        total_size = 0
        for doc in documents:
            # Estimate document size
            doc_str = str(doc)
            total_size += sys.getsizeof(doc_str)

        total_size_mb = total_size / (1024 * 1024)

        if total_size_mb > self.config.memory_limit_mb:
            raise BatchMemoryError(
                f"Memory limit exceeded: {total_size_mb:.2f}MB > {self.config.memory_limit_mb}MB"
            )

    def _get_operation(self, operation_name: str) -> Callable:
        """Get operation function by name."""
        # Map operation names to functions
        operations = {
            "enhance": self._enhance_document,
            "generate": self._generate_document,
            "review": self._review_document,
            "validate": self._validate_document,
        }

        if operation_name not in operations:
            raise BatchError(f"Invalid operation: {operation_name}")

        return operations[operation_name]

    async def _enhance_document(self, document: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Enhance document using enhancement pipeline."""
        # Lazy load enhancement pipeline
        if self._enhancement_pipeline is None:
            # Prefer module-level EnhancementPipeline so tests can patch it
            if EnhancementPipeline is None:  # Fallback import if not available
                from ..intelligence.enhance import EnhancementPipeline as _EnhancementPipeline

                self._enhancement_pipeline = _EnhancementPipeline()
            else:
                self._enhancement_pipeline = EnhancementPipeline()

        result = await self._enhancement_pipeline.enhance_document(
            content=document.get("content", ""),
            document_type=document.get("type", "general"),
        )

        return {
            "enhanced": result.enhanced_content,
            "improvement": result.quality_improvement,
        }

    async def _generate_document(self, document: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Generate document content."""
        # Placeholder for document generation
        return {"generated": f"Generated content for {document.get('id')}"}

    async def _review_document(self, document: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Review document for quality."""
        # Placeholder for document review
        return {"review": f"Review complete for {document.get('id')}"}

    async def _validate_document(self, document: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Validate document structure and content."""
        # Basic validation
        is_valid = bool(document.get("id") and document.get("content"))
        return {"valid": is_valid}

    async def enhance_batch(self, documents: List[Dict[str, Any]]) -> List[BatchResult]:
        """
        Enhance a batch of documents using enhancement pipeline.

        Args:
            documents: Documents to enhance

        Returns:
            List of enhancement results
        """
        return await self.process_batch(documents, "enhance")

    def get_batch_metrics(self, results: List[BatchResult]) -> Dict[str, Any]:
        """
        Get aggregated metrics from batch results.

        Args:
            results: List of batch results

        Returns:
            Dictionary of metrics
        """
        if not results:
            return BatchMetrics().__dict__

        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        total_time = sum(r.processing_time for r in results)
        avg_time = total_time / len(results) if results else 0

        return {
            "total_documents": len(results),
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / len(results) * 100) if results else 0.0,
            "total_time": total_time,
            "average_time_per_doc": avg_time,
            "throughput_per_hour": (len(results) / total_time * 3600) if total_time > 0 else 0.0,
        }

    async def shutdown(self):
        """Shutdown batch operations manager."""
        # Clear queue
        await self.queue.clear()

        # Shutdown executor
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None

        logger.info("BatchOperationsManager shutdown complete")


# ============================================================================
# Convenience Functions
# ============================================================================


async def process_documents_batch(
    documents: List[Dict[str, Any]],
    operation: Union[str, Callable],
    config: Optional[BatchConfig] = None,
    **kwargs,
) -> List[BatchResult]:
    """
    Convenience function to process documents in batch.

    Args:
        documents: Documents to process
        operation: Operation to perform
        config: Batch configuration
        **kwargs: Additional arguments

    Returns:
        List of batch results
    """
    manager = BatchOperationsManager(config=config)
    try:
        results = await manager.process_batch(documents, operation, **kwargs)
        return results
    finally:
        await manager.shutdown()


def estimate_processing_time(
    document_count: int,
    memory_mode: str = "standard",
) -> float:
    """
    Estimate processing time for given number of documents.

    Args:
        document_count: Number of documents
        memory_mode: Memory mode for processing

    Returns:
        Estimated time in seconds
    """
    target_per_hour = PERFORMANCE_TARGETS.get(memory_mode, 100)
    docs_per_second = target_per_hour / 3600
    return document_count / docs_per_second
