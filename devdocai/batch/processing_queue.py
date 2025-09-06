"""
Processing Queue for Batch Operations

Manages document queue with priority and concurrency control.
"""

import asyncio
import logging
from collections import deque
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Deque, Optional, Set
from uuid import uuid4

logger = logging.getLogger(__name__)


class Priority(IntEnum):
    """Document processing priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class QueueItem:
    """Item in the processing queue."""
    id: str
    document: Any
    priority: Priority
    retries: int = 0
    max_retries: int = 3
    
    def __lt__(self, other):
        """Compare by priority for heap operations."""
        return self.priority > other.priority


class ProcessingQueue:
    """
    Thread-safe processing queue with priority support.
    
    Features:
    - Priority-based processing
    - Concurrent access control
    - Retry mechanism
    - Queue statistics
    """
    
    def __init__(self, max_concurrent: int = 4, max_size: int = 10000):
        """
        Initialize processing queue.
        
        Args:
            max_concurrent: Maximum concurrent processing tasks
            max_size: Maximum queue size
        """
        self.max_concurrent = max_concurrent
        self.max_size = max_size
        
        # Priority queues for different priority levels
        self.queues: dict[Priority, Deque[QueueItem]] = {
            Priority.CRITICAL: deque(),
            Priority.HIGH: deque(),
            Priority.NORMAL: deque(),
            Priority.LOW: deque()
        }
        
        # Processing state
        self.processing: Set[str] = set()
        self.completed: Set[str] = set()
        self.failed: Set[str] = set()
        
        # Thread safety
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Condition()
        
        # Statistics
        self.stats = {
            'total_added': 0,
            'total_processed': 0,
            'total_failed': 0,
            'total_retried': 0
        }
    
    async def add_document(
        self,
        document: Any,
        priority: Priority = Priority.NORMAL
    ) -> str:
        """
        Add a document to the processing queue.
        
        Args:
            document: Document to process
            priority: Processing priority
            
        Returns:
            Document ID for tracking
        """
        async with self._lock:
            # Check queue size
            total_size = sum(len(q) for q in self.queues.values())
            if total_size >= self.max_size:
                raise OverflowError(f"Queue is full (max size: {self.max_size})")
            
            # Create queue item
            item_id = str(uuid4())
            item = QueueItem(
                id=item_id,
                document=document,
                priority=priority
            )
            
            # Add to appropriate queue
            self.queues[priority].append(item)
            self.stats['total_added'] += 1
            
            # Notify waiting consumers
            async with self._not_empty:
                self._not_empty.notify()
            
            logger.debug(f"Added document {item_id} with priority {priority.name}")
            return item_id
    
    async def get_next(self, timeout: Optional[float] = None) -> Optional[Any]:
        """
        Get the next document to process.
        
        Args:
            timeout: Maximum time to wait for a document
            
        Returns:
            Next document to process or None if timeout
        """
        deadline = asyncio.get_event_loop().time() + timeout if timeout else None
        
        while True:
            async with self._lock:
                # Check queues in priority order
                for priority in [Priority.CRITICAL, Priority.HIGH, Priority.NORMAL, Priority.LOW]:
                    if self.queues[priority]:
                        item = self.queues[priority].popleft()
                        
                        # Check if already processing
                        if item.id not in self.processing:
                            self.processing.add(item.id)
                            logger.debug(f"Processing document {item.id}")
                            return item.document
                
                # If no documents available
                if self.is_empty():
                    return None
                
                # Wait for new documents
                if deadline:
                    remaining = deadline - asyncio.get_event_loop().time()
                    if remaining <= 0:
                        return None
                    
                    try:
                        async with self._not_empty:
                            await asyncio.wait_for(
                                self._not_empty.wait(),
                                timeout=remaining
                            )
                    except asyncio.TimeoutError:
                        return None
                else:
                    async with self._not_empty:
                        await self._not_empty.wait()
    
    async def mark_completed(self, document_id: str):
        """Mark a document as completed."""
        async with self._lock:
            if document_id in self.processing:
                self.processing.remove(document_id)
                self.completed.add(document_id)
                self.stats['total_processed'] += 1
                logger.debug(f"Completed document {document_id}")
    
    async def mark_failed(self, document_id: str, retry: bool = True) -> bool:
        """
        Mark a document as failed.
        
        Args:
            document_id: Document ID
            retry: Whether to retry processing
            
        Returns:
            True if document will be retried
        """
        async with self._lock:
            if document_id not in self.processing:
                return False
            
            self.processing.remove(document_id)
            
            # Find the item in queues (if it was re-queued)
            item = None
            for priority_queue in self.queues.values():
                for queue_item in priority_queue:
                    if queue_item.id == document_id:
                        item = queue_item
                        break
                if item:
                    break
            
            if retry and item and item.retries < item.max_retries:
                # Re-queue with increased retry count
                item.retries += 1
                self.queues[item.priority].append(item)
                self.stats['total_retried'] += 1
                logger.info(f"Retrying document {document_id} (attempt {item.retries})")
                
                # Notify waiting consumers
                async with self._not_empty:
                    self._not_empty.notify()
                
                return True
            else:
                # Mark as permanently failed
                self.failed.add(document_id)
                self.stats['total_failed'] += 1
                logger.error(f"Document {document_id} permanently failed")
                return False
    
    def is_empty(self) -> bool:
        """Check if all queues are empty."""
        return all(len(q) == 0 for q in self.queues.values())
    
    def size(self) -> int:
        """Get total number of documents in queue."""
        return sum(len(q) for q in self.queues.values())
    
    def get_stats(self) -> dict:
        """Get queue statistics."""
        stats = self.stats.copy()
        stats.update({
            'queue_size': self.size(),
            'processing': len(self.processing),
            'completed': len(self.completed),
            'failed': len(self.failed),
            'by_priority': {
                priority.name: len(queue)
                for priority, queue in self.queues.items()
            }
        })
        return stats
    
    async def clear(self):
        """Clear all queues."""
        async with self._lock:
            for queue in self.queues.values():
                queue.clear()
            self.processing.clear()
            self.completed.clear()
            self.failed.clear()
            logger.info("Processing queue cleared")
    
    async def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for all documents to be processed.
        
        Args:
            timeout: Maximum time to wait
            
        Returns:
            True if all documents processed, False if timeout
        """
        deadline = asyncio.get_event_loop().time() + timeout if timeout else None
        
        while True:
            async with self._lock:
                if self.is_empty() and len(self.processing) == 0:
                    return True
            
            if deadline:
                remaining = deadline - asyncio.get_event_loop().time()
                if remaining <= 0:
                    return False
                await asyncio.sleep(min(0.1, remaining))
            else:
                await asyncio.sleep(0.1)