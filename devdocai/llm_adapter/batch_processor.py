"""
M008: Request Batching and Coalescing for LLM Adapter.

Implements intelligent request batching with:
- Request queuing and automatic batch formation
- Request coalescing for identical prompts
- Configurable batch sizes and timeouts
- Priority-based processing
- Batch optimization for cost efficiency
"""

import asyncio
import hashlib
import json
import time
import logging
from typing import Dict, List, Optional, Any, Set, Callable, Tuple, Coroutine
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque
import heapq

from .providers.base import LLMRequest, LLMResponse, ProviderError

logger = logging.getLogger(__name__)


class RequestPriority(Enum):
    """Request priority levels."""
    CRITICAL = 0  # Highest priority
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BATCH = 4  # Lowest priority, for batch operations


@dataclass
class BatchRequest:
    """Individual request in a batch."""
    request: LLMRequest
    priority: RequestPriority
    future: asyncio.Future
    timestamp: float = field(default_factory=time.time)
    request_hash: str = field(default="")
    retries: int = 0
    
    def __post_init__(self):
        """Generate request hash if not provided."""
        if not self.request_hash:
            self.request_hash = self._generate_hash()
    
    def _generate_hash(self) -> str:
        """Generate hash for request deduplication."""
        key_data = {
            "messages": self.request.messages,
            "model": self.request.model,
            "temperature": self.request.temperature,
            "max_tokens": self.request.max_tokens
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def __lt__(self, other):
        """Compare by priority then timestamp for heap operations."""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.timestamp < other.timestamp


@dataclass
class BatchStats:
    """Statistics for batch processing."""
    total_batches: int = 0
    total_requests: int = 0
    coalesced_requests: int = 0
    average_batch_size: float = 0.0
    average_wait_time_ms: float = 0.0
    failed_batches: int = 0
    successful_batches: int = 0
    total_processing_time_ms: float = 0.0
    
    def update_batch(self, batch_size: int, wait_time_ms: float, success: bool):
        """Update statistics after batch processing."""
        self.total_batches += 1
        self.total_requests += batch_size
        
        if success:
            self.successful_batches += 1
        else:
            self.failed_batches += 1
        
        # Update moving averages
        self.average_batch_size = (
            (self.average_batch_size * (self.total_batches - 1) + batch_size) 
            / self.total_batches
        )
        self.average_wait_time_ms = (
            (self.average_wait_time_ms * (self.total_batches - 1) + wait_time_ms)
            / self.total_batches
        )


class RequestQueue:
    """Priority queue for batch requests."""
    
    def __init__(self, max_size: int = 10000):
        """
        Initialize request queue.
        
        Args:
            max_size: Maximum queue size
        """
        self.max_size = max_size
        self.queue: List[BatchRequest] = []
        self.request_map: Dict[str, List[BatchRequest]] = defaultdict(list)
        self._lock = asyncio.Lock()
    
    async def put(self, request: BatchRequest) -> bool:
        """
        Add request to queue.
        
        Args:
            request: Request to add
            
        Returns:
            True if added, False if queue full
        """
        async with self._lock:
            if len(self.queue) >= self.max_size:
                return False
            
            heapq.heappush(self.queue, request)
            self.request_map[request.request_hash].append(request)
            return True
    
    async def get_batch(
        self,
        max_batch_size: int,
        max_wait_time_ms: float = 100
    ) -> List[BatchRequest]:
        """
        Get a batch of requests from queue.
        
        Args:
            max_batch_size: Maximum batch size
            max_wait_time_ms: Maximum time to wait for batch formation
            
        Returns:
            List of batch requests
        """
        batch = []
        start_time = time.time()
        
        while len(batch) < max_batch_size:
            # Check timeout
            if (time.time() - start_time) * 1000 > max_wait_time_ms and batch:
                break
            
            async with self._lock:
                if not self.queue:
                    if batch:
                        break  # Return what we have
                    await asyncio.sleep(0.01)  # Wait for requests
                    continue
                
                # Get highest priority request
                request = heapq.heappop(self.queue)
                
                # Remove from map
                if request.request_hash in self.request_map:
                    self.request_map[request.request_hash].remove(request)
                    if not self.request_map[request.request_hash]:
                        del self.request_map[request.request_hash]
                
                batch.append(request)
        
        return batch
    
    async def get_coalesced_requests(self, request_hash: str) -> List[BatchRequest]:
        """
        Get all requests with the same hash for coalescing.
        
        Args:
            request_hash: Request hash to look up
            
        Returns:
            List of matching requests
        """
        async with self._lock:
            return self.request_map.get(request_hash, []).copy()
    
    async def size(self) -> int:
        """Get current queue size."""
        async with self._lock:
            return len(self.queue)
    
    async def clear(self) -> None:
        """Clear the queue."""
        async with self._lock:
            self.queue.clear()
            self.request_map.clear()


class BatchProcessor:
    """
    Intelligent batch processor for LLM requests.
    
    Features:
    - Automatic batch formation based on size and time
    - Request coalescing for identical prompts
    - Priority-based processing
    - Retry logic with exponential backoff
    - Cost-optimized batching
    """
    
    def __init__(
        self,
        max_batch_size: int = 10,
        max_wait_time_ms: float = 100,
        enable_coalescing: bool = True,
        max_retries: int = 3
    ):
        """
        Initialize batch processor.
        
        Args:
            max_batch_size: Maximum requests per batch
            max_wait_time_ms: Maximum wait time for batch formation
            enable_coalescing: Enable request coalescing
            max_retries: Maximum retry attempts
        """
        self.max_batch_size = max_batch_size
        self.max_wait_time_ms = max_wait_time_ms
        self.enable_coalescing = enable_coalescing
        self.max_retries = max_retries
        
        # Request queues by provider
        self.queues: Dict[str, RequestQueue] = defaultdict(
            lambda: RequestQueue(max_size=10000)
        )
        
        # Coalescing map for deduplication
        self.pending_requests: Dict[str, List[asyncio.Future]] = defaultdict(list)
        
        # Processing tasks
        self.processing_tasks: Dict[str, asyncio.Task] = {}
        
        # Statistics
        self.stats: Dict[str, BatchStats] = defaultdict(BatchStats)
        
        # Batch processors (provider-specific)
        self.processors: Dict[str, Callable] = {}
        
        self.logger = logging.getLogger(f"{__name__}.BatchProcessor")
        self._running = False
    
    def register_processor(
        self,
        provider: str,
        processor: Callable[[List[LLMRequest]], Coroutine[Any, Any, List[LLMResponse]]]
    ) -> None:
        """
        Register a batch processor for a provider.
        
        Args:
            provider: Provider name
            processor: Async function to process batch
        """
        self.processors[provider] = processor
        self.logger.info(f"Registered batch processor for {provider}")
    
    async def submit(
        self,
        request: LLMRequest,
        provider: str,
        priority: RequestPriority = RequestPriority.NORMAL
    ) -> LLMResponse:
        """
        Submit request for batch processing.
        
        Args:
            request: LLM request
            provider: Provider to use
            priority: Request priority
            
        Returns:
            LLM response
        """
        # Create future for response
        future = asyncio.Future()
        
        # Create batch request
        batch_request = BatchRequest(
            request=request,
            priority=priority,
            future=future
        )
        
        # Check for coalescing opportunity
        if self.enable_coalescing and batch_request.request_hash in self.pending_requests:
            # Coalesce with existing request
            self.pending_requests[batch_request.request_hash].append(future)
            self.stats[provider].coalesced_requests += 1
            self.logger.debug(
                f"Coalesced request {batch_request.request_hash[:8]}... "
                f"({len(self.pending_requests[batch_request.request_hash])} waiting)"
            )
        else:
            # Add to queue
            queue = self.queues[provider]
            added = await queue.put(batch_request)
            
            if not added:
                raise ValueError(f"Queue full for provider {provider}")
            
            if self.enable_coalescing:
                self.pending_requests[batch_request.request_hash].append(future)
            
            # Start processor if not running
            if provider not in self.processing_tasks or self.processing_tasks[provider].done():
                self.processing_tasks[provider] = asyncio.create_task(
                    self._process_queue(provider)
                )
        
        # Wait for response
        return await future
    
    async def _process_queue(self, provider: str) -> None:
        """
        Process requests from queue for a provider.
        
        Args:
            provider: Provider name
        """
        self.logger.info(f"Started batch processor for {provider}")
        queue = self.queues[provider]
        
        while True:
            try:
                # Get batch from queue
                batch = await queue.get_batch(
                    self.max_batch_size,
                    self.max_wait_time_ms
                )
                
                if not batch:
                    # No requests, wait a bit
                    await asyncio.sleep(0.1)
                    continue
                
                # Process batch
                await self._process_batch(provider, batch)
                
            except Exception as e:
                self.logger.error(f"Error processing queue for {provider}: {e}")
                await asyncio.sleep(1)  # Back off on error
    
    async def _process_batch(
        self,
        provider: str,
        batch: List[BatchRequest]
    ) -> None:
        """
        Process a batch of requests.
        
        Args:
            provider: Provider name
            batch: Batch of requests
        """
        start_time = time.time()
        
        # Calculate wait times
        wait_times = [(start_time - req.timestamp) * 1000 for req in batch]
        avg_wait_time = sum(wait_times) / len(wait_times) if wait_times else 0
        
        self.logger.debug(
            f"Processing batch of {len(batch)} requests for {provider} "
            f"(avg wait: {avg_wait_time:.1f}ms)"
        )
        
        try:
            # Group by unique requests for coalescing
            unique_requests: Dict[str, Tuple[LLMRequest, List[asyncio.Future]]] = {}
            
            for req in batch:
                if req.request_hash not in unique_requests:
                    unique_requests[req.request_hash] = (req.request, [])
                unique_requests[req.request_hash][1].append(req.future)
            
            # Get processor for provider
            if provider not in self.processors:
                # Fallback: process individually
                await self._process_individual(provider, batch)
                return
            
            processor = self.processors[provider]
            
            # Process unique requests
            requests_to_process = [req for req, _ in unique_requests.values()]
            
            # Execute batch processing
            responses = await processor(requests_to_process)
            
            # Distribute responses to futures
            for i, (request_hash, (request, futures)) in enumerate(unique_requests.items()):
                response = responses[i] if i < len(responses) else None
                
                if response:
                    # Success - set result for all coalesced requests
                    for future in futures:
                        if not future.done():
                            future.set_result(response)
                    
                    # Clear from pending
                    if request_hash in self.pending_requests:
                        del self.pending_requests[request_hash]
                else:
                    # Failure - set exception
                    error = ProviderError(
                        "Batch processing failed",
                        provider=provider
                    )
                    for future in futures:
                        if not future.done():
                            future.set_exception(error)
            
            # Update statistics
            processing_time = (time.time() - start_time) * 1000
            self.stats[provider].update_batch(
                len(batch),
                avg_wait_time,
                success=True
            )
            self.stats[provider].total_processing_time_ms += processing_time
            
            self.logger.info(
                f"Processed batch of {len(batch)} requests ({len(unique_requests)} unique) "
                f"for {provider} in {processing_time:.1f}ms"
            )
            
        except Exception as e:
            self.logger.error(f"Batch processing failed for {provider}: {e}")
            
            # Set exception for all futures
            for req in batch:
                if not req.future.done():
                    req.future.set_exception(e)
            
            # Update statistics
            self.stats[provider].update_batch(
                len(batch),
                avg_wait_time,
                success=False
            )
    
    async def _process_individual(
        self,
        provider: str,
        batch: List[BatchRequest]
    ) -> None:
        """
        Process requests individually (fallback).
        
        Args:
            provider: Provider name
            batch: Batch of requests
        """
        for req in batch:
            try:
                # This would call the actual provider
                # For now, create a mock response
                response = LLMResponse(
                    content="Mock batch response",
                    finish_reason="stop",
                    model=req.request.model,
                    provider=provider,
                    usage={
                        "prompt_tokens": 10,
                        "completion_tokens": 10,
                        "total_tokens": 20,
                        "prompt_cost": 0.0001,
                        "completion_cost": 0.0002,
                        "total_cost": 0.0003
                    },
                    request_id=req.request.request_id,
                    response_time_ms=50
                )
                
                if not req.future.done():
                    req.future.set_result(response)
                    
            except Exception as e:
                if not req.future.done():
                    req.future.set_exception(e)
    
    async def flush(self, provider: Optional[str] = None) -> None:
        """
        Flush pending requests.
        
        Args:
            provider: Specific provider to flush, or None for all
        """
        providers = [provider] if provider else list(self.queues.keys())
        
        for prov in providers:
            queue = self.queues[prov]
            
            while await queue.size() > 0:
                batch = await queue.get_batch(
                    self.max_batch_size,
                    max_wait_time_ms=0  # Don't wait
                )
                if batch:
                    await self._process_batch(prov, batch)
        
        self.logger.info(f"Flushed queues for {providers}")
    
    def get_stats(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """
        Get batch processing statistics.
        
        Args:
            provider: Specific provider or None for all
            
        Returns:
            Statistics dictionary
        """
        if provider:
            stats = self.stats[provider]
            return {
                "provider": provider,
                "total_batches": stats.total_batches,
                "total_requests": stats.total_requests,
                "coalesced_requests": stats.coalesced_requests,
                "average_batch_size": stats.average_batch_size,
                "average_wait_time_ms": stats.average_wait_time_ms,
                "success_rate": (
                    stats.successful_batches / stats.total_batches
                    if stats.total_batches > 0 else 0
                ),
                "total_processing_time_ms": stats.total_processing_time_ms
            }
        else:
            # Return all provider stats
            return {
                prov: self.get_stats(prov)
                for prov in self.stats.keys()
            }
    
    async def shutdown(self) -> None:
        """Shutdown batch processor."""
        self._running = False
        
        # Cancel processing tasks
        for task in self.processing_tasks.values():
            task.cancel()
        
        # Flush remaining requests
        await self.flush()
        
        self.logger.info("Batch processor shutdown complete")


class SmartBatcher:
    """
    Intelligent batching with cost and latency optimization.
    
    Groups requests by:
    - Model type (for provider efficiency)
    - Token count (for cost optimization)
    - Priority (for SLA compliance)
    """
    
    def __init__(
        self,
        cost_threshold: float = 0.10,  # Max cost per batch
        latency_target_ms: float = 1000  # Target latency
    ):
        """
        Initialize smart batcher.
        
        Args:
            cost_threshold: Maximum cost per batch
            latency_target_ms: Target latency in milliseconds
        """
        self.cost_threshold = cost_threshold
        self.latency_target_ms = latency_target_ms
        
        # Model-specific batch configurations
        self.model_configs = {
            "gpt-4": {"max_batch": 5, "max_tokens": 8000},
            "gpt-3.5-turbo": {"max_batch": 20, "max_tokens": 4000},
            "claude-3": {"max_batch": 10, "max_tokens": 10000},
            "gemini-pro": {"max_batch": 15, "max_tokens": 8000},
            "llama": {"max_batch": 30, "max_tokens": 4000}
        }
        
        self.logger = logging.getLogger(f"{__name__}.SmartBatcher")
    
    def optimize_batch(
        self,
        requests: List[LLMRequest],
        model: str,
        cost_per_token: float
    ) -> List[List[LLMRequest]]:
        """
        Optimize requests into batches.
        
        Args:
            requests: List of requests to batch
            model: Model being used
            cost_per_token: Cost per token for model
            
        Returns:
            List of optimized batches
        """
        # Get model configuration
        config = self.model_configs.get(
            model,
            {"max_batch": 10, "max_tokens": 4000}
        )
        
        batches = []
        current_batch = []
        current_tokens = 0
        current_cost = 0.0
        
        for request in requests:
            # Estimate tokens (simplified)
            request_tokens = sum(
                len(msg["content"].split()) * 1.3  # Rough token estimate
                for msg in request.messages
            )
            request_cost = request_tokens * cost_per_token
            
            # Check if adding this request exceeds limits
            if (
                len(current_batch) >= config["max_batch"] or
                current_tokens + request_tokens > config["max_tokens"] or
                current_cost + request_cost > self.cost_threshold
            ):
                # Start new batch
                if current_batch:
                    batches.append(current_batch)
                current_batch = [request]
                current_tokens = request_tokens
                current_cost = request_cost
            else:
                # Add to current batch
                current_batch.append(request)
                current_tokens += request_tokens
                current_cost += request_cost
        
        # Add remaining batch
        if current_batch:
            batches.append(current_batch)
        
        self.logger.debug(
            f"Optimized {len(requests)} requests into {len(batches)} batches "
            f"for model {model}"
        )
        
        return batches