"""
MIAIR Batch Operations - Parallel Processing Module
DevDocAI v3.0.0

Provides efficient batch processing capabilities for the MIAIR Engine.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Callable, Any
from dataclasses import dataclass

from .miair_strategies import DocumentMetrics

logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """Result of MIAIR optimization process."""

    initial_content: str
    final_content: str
    iterations: int
    initial_quality: float
    final_quality: float
    improvement_percentage: float
    initial_metrics: Optional[DocumentMetrics]
    final_metrics: DocumentMetrics
    optimization_time: float
    storage_id: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert result to dictionary."""
        return {
            "iterations": self.iterations,
            "initial_quality": self.initial_quality,
            "final_quality": self.final_quality,
            "improvement_percentage": self.improvement_percentage,
            "optimization_time": self.optimization_time,
            "storage_id": self.storage_id,
            "initial_metrics": (
                self.initial_metrics.to_dict() if self.initial_metrics else None
            ),
            "final_metrics": self.final_metrics.to_dict(),
        }


class BatchOptimizer:
    """Handles batch optimization operations for MIAIR Engine."""

    def __init__(
        self,
        optimize_func: Callable,
        max_workers: int = 4,
        batch_size: int = 100,
    ):
        """
        Initialize batch optimizer.

        Args:
            optimize_func: Single document optimization function
            max_workers: Maximum parallel workers
            batch_size: Documents per batch
        """
        self.optimize_func = optimize_func
        self.max_workers = max_workers
        self.batch_size = batch_size
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def process_batch(
        self,
        documents: List[str],
        max_iterations: Optional[int] = None,
        save_to_storage: bool = False,
    ) -> List[OptimizationResult]:
        """
        Optimize multiple documents in parallel batches.

        Args:
            documents: List of documents to optimize
            max_iterations: Maximum iterations per document
            save_to_storage: Whether to save results

        Returns:
            List of optimization results
        """
        results = []
        total_docs = len(documents)

        for batch_start in range(0, total_docs, self.batch_size):
            batch_end = min(batch_start + self.batch_size, total_docs)
            batch = documents[batch_start:batch_end]

            logger.info(
                f"Processing batch {batch_start//self.batch_size + 1} "
                f"({len(batch)} documents)"
            )

            batch_results = self._process_single_batch(
                batch, max_iterations, save_to_storage
            )
            results.extend(batch_results)

        return results

    def _process_single_batch(
        self,
        batch: List[str],
        max_iterations: Optional[int],
        save_to_storage: bool,
    ) -> List[OptimizationResult]:
        """Process a single batch of documents."""
        futures = []

        for doc in batch:
            future = self._executor.submit(
                self.optimize_func, doc, max_iterations, save_to_storage
            )
            futures.append(future)

        results = []
        for future in as_completed(futures, timeout=30):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"Batch optimization failed: {e}")
                # Add error placeholder
                results.append(self._create_error_result(str(e)))

        return results

    async def process_batch_async(
        self,
        documents: List[str],
        max_iterations: Optional[int] = None,
        save_to_storage: bool = False,
    ) -> List[OptimizationResult]:
        """
        Asynchronously optimize multiple documents.

        Args:
            documents: List of documents
            max_iterations: Maximum iterations
            save_to_storage: Whether to save

        Returns:
            List of optimization results
        """
        loop = asyncio.get_event_loop()

        # Create tasks for all documents
        tasks = []
        for doc in documents:
            task = loop.run_in_executor(
                self._executor, self.optimize_func, doc, max_iterations, save_to_storage
            )
            tasks.append(task)

        # Gather results with exception handling
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        clean_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Async optimization failed: {result}")
                clean_results.append(
                    self._create_error_result(str(result), documents[i])
                )
            else:
                clean_results.append(result)

        return clean_results

    def _create_error_result(
        self, error_msg: str, document: str = ""
    ) -> OptimizationResult:
        """Create placeholder result for failed optimization."""
        return OptimizationResult(
            initial_content=document[:100] if document else "",
            final_content=document[:100] if document else "",
            iterations=0,
            initial_quality=0.0,
            final_quality=0.0,
            improvement_percentage=0.0,
            initial_metrics=None,
            final_metrics=DocumentMetrics(0, 0, 0, 0, 0),
            optimization_time=0.0,
            storage_id=None,
        )

    def shutdown(self, wait: bool = True):
        """Shutdown the executor."""
        self._executor.shutdown(wait=wait)

    def __del__(self):
        """Cleanup on deletion."""
        self.shutdown(wait=False)


class StreamingOptimizer:
    """Handles streaming optimization for large document sets."""

    def __init__(self, batch_optimizer: BatchOptimizer):
        """
        Initialize streaming optimizer.

        Args:
            batch_optimizer: Batch optimizer instance
        """
        self.batch_optimizer = batch_optimizer
        self.buffer = []
        self.buffer_size = batch_optimizer.batch_size

    async def process_stream(
        self,
        document_stream: Any,  # AsyncIterator in real implementation
        max_iterations: Optional[int] = None,
        save_to_storage: bool = False,
    ):
        """
        Process documents from a stream.

        Args:
            document_stream: Async iterator of documents
            max_iterations: Maximum iterations
            save_to_storage: Whether to save

        Yields:
            Optimization results as they complete
        """
        async for document in document_stream:
            self.buffer.append(document)

            if len(self.buffer) >= self.buffer_size:
                # Process full buffer
                results = await self.batch_optimizer.process_batch_async(
                    self.buffer, max_iterations, save_to_storage
                )
                for result in results:
                    yield result
                self.buffer.clear()

        # Process remaining documents
        if self.buffer:
            results = await self.batch_optimizer.process_batch_async(
                self.buffer, max_iterations, save_to_storage
            )
            for result in results:
                yield result