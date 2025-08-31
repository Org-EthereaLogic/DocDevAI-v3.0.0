"""
M008: Streaming Support for LLM Adapter.

Implements efficient streaming with:
- Async generators for all providers
- Stream processing pipelines
- Chunk buffering and optimization
- Stream multiplexing for multiple consumers
- Progress tracking and metrics
"""

import asyncio
import time
import logging
from typing import AsyncGenerator, Optional, List, Dict, Any, Callable, Set
from dataclasses import dataclass, field
from collections import deque
from enum import Enum

from .providers.base import LLMRequest, LLMResponse

logger = logging.getLogger(__name__)


class StreamState(Enum):
    """Stream processing states."""
    IDLE = "idle"
    STREAMING = "streaming"
    BUFFERING = "buffering"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class StreamMetrics:
    """Metrics for stream performance."""
    time_to_first_token_ms: float = 0
    total_tokens: int = 0
    total_chunks: int = 0
    average_chunk_size: float = 0
    average_chunk_delay_ms: float = 0
    total_stream_time_ms: float = 0
    tokens_per_second: float = 0
    
    def update_chunk(self, chunk_size: int, delay_ms: float):
        """Update metrics with new chunk."""
        self.total_chunks += 1
        self.total_tokens += chunk_size
        
        # Update averages
        self.average_chunk_size = (
            (self.average_chunk_size * (self.total_chunks - 1) + chunk_size)
            / self.total_chunks
        )
        self.average_chunk_delay_ms = (
            (self.average_chunk_delay_ms * (self.total_chunks - 1) + delay_ms)
            / self.total_chunks
        )
    
    def finalize(self, total_time_ms: float):
        """Finalize metrics at stream completion."""
        self.total_stream_time_ms = total_time_ms
        if total_time_ms > 0:
            self.tokens_per_second = (self.total_tokens / total_time_ms) * 1000


@dataclass
class StreamChunk:
    """Individual stream chunk."""
    content: str
    token_count: int
    timestamp: float = field(default_factory=time.time)
    is_final: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class StreamBuffer:
    """
    Buffer for stream chunks with optimization.
    
    Features:
    - Configurable buffer size
    - Automatic flushing
    - Chunk aggregation for efficiency
    """
    
    def __init__(
        self,
        max_size: int = 100,
        flush_interval_ms: float = 50,
        aggregate_small_chunks: bool = True,
        min_chunk_size: int = 10
    ):
        """
        Initialize stream buffer.
        
        Args:
            max_size: Maximum buffer size
            flush_interval_ms: Auto-flush interval
            aggregate_small_chunks: Combine small chunks
            min_chunk_size: Minimum chunk size for aggregation
        """
        self.max_size = max_size
        self.flush_interval_ms = flush_interval_ms
        self.aggregate_small_chunks = aggregate_small_chunks
        self.min_chunk_size = min_chunk_size
        
        self.buffer: deque = deque(maxlen=max_size)
        self.pending_chunk: Optional[StreamChunk] = None
        self.last_flush_time = time.time()
        self._lock = asyncio.Lock()
    
    async def add(self, chunk: StreamChunk) -> Optional[StreamChunk]:
        """
        Add chunk to buffer.
        
        Args:
            chunk: Stream chunk to add
            
        Returns:
            Chunk to emit if buffer needs flushing
        """
        async with self._lock:
            # Check if we should aggregate
            if (
                self.aggregate_small_chunks and
                len(chunk.content) < self.min_chunk_size and
                not chunk.is_final
            ):
                # Aggregate with pending chunk
                if self.pending_chunk:
                    self.pending_chunk.content += chunk.content
                    self.pending_chunk.token_count += chunk.token_count
                else:
                    self.pending_chunk = chunk
                
                # Check if aggregated chunk is large enough
                if self.pending_chunk and len(self.pending_chunk.content) >= self.min_chunk_size:
                    to_emit = self.pending_chunk
                    self.pending_chunk = None
                    return to_emit
                
                return None
            
            # Flush pending if exists
            if self.pending_chunk:
                self.buffer.append(self.pending_chunk)
                self.pending_chunk = None
            
            # Add current chunk
            self.buffer.append(chunk)
            
            # Check if we need to flush
            if self._should_flush():
                return await self.flush_one()
            
            return None
    
    async def flush_one(self) -> Optional[StreamChunk]:
        """Flush one chunk from buffer."""
        async with self._lock:
            if self.buffer:
                self.last_flush_time = time.time()
                return self.buffer.popleft()
            elif self.pending_chunk:
                chunk = self.pending_chunk
                self.pending_chunk = None
                return chunk
            return None
    
    async def flush_all(self) -> List[StreamChunk]:
        """Flush all chunks from buffer."""
        async with self._lock:
            chunks = list(self.buffer)
            self.buffer.clear()
            
            if self.pending_chunk:
                chunks.append(self.pending_chunk)
                self.pending_chunk = None
            
            self.last_flush_time = time.time()
            return chunks
    
    def _should_flush(self) -> bool:
        """Check if buffer should be flushed."""
        # Flush if buffer is full
        if len(self.buffer) >= self.max_size:
            return True
        
        # Flush if interval exceeded
        if (time.time() - self.last_flush_time) * 1000 > self.flush_interval_ms:
            return True
        
        return False


class StreamProcessor:
    """
    Stream processing pipeline with transformations.
    
    Allows chaining of stream transformations for:
    - Content filtering
    - Token counting
    - Format conversion
    - Progress tracking
    """
    
    def __init__(self):
        """Initialize stream processor."""
        self.transformers: List[Callable] = []
        self.logger = logging.getLogger(f"{__name__}.StreamProcessor")
    
    def add_transformer(
        self,
        transformer: Callable[[StreamChunk], AsyncGenerator[StreamChunk, None]]
    ) -> "StreamProcessor":
        """
        Add transformer to pipeline.
        
        Args:
            transformer: Async generator transformer function
            
        Returns:
            Self for chaining
        """
        self.transformers.append(transformer)
        return self
    
    async def process(
        self,
        stream: AsyncGenerator[StreamChunk, None]
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Process stream through transformation pipeline.
        
        Args:
            stream: Input stream
            
        Yields:
            Transformed chunks
        """
        # Apply transformers in sequence
        current_stream = stream
        
        for transformer in self.transformers:
            current_stream = self._apply_transformer(current_stream, transformer)
        
        # Yield final transformed stream
        async for chunk in current_stream:
            yield chunk
    
    async def _apply_transformer(
        self,
        stream: AsyncGenerator[StreamChunk, None],
        transformer: Callable
    ) -> AsyncGenerator[StreamChunk, None]:
        """Apply single transformer to stream."""
        async for chunk in stream:
            async for transformed in transformer(chunk):
                yield transformed


class StreamMultiplexer:
    """
    Multiplexer for broadcasting streams to multiple consumers.
    
    Features:
    - Single source, multiple consumers
    - Independent consumer progress
    - Backpressure handling
    - Consumer lifecycle management
    """
    
    def __init__(
        self,
        buffer_size: int = 100,
        slow_consumer_timeout_ms: float = 5000
    ):
        """
        Initialize stream multiplexer.
        
        Args:
            buffer_size: Buffer size per consumer
            slow_consumer_timeout_ms: Timeout for slow consumers
        """
        self.buffer_size = buffer_size
        self.slow_consumer_timeout_ms = slow_consumer_timeout_ms
        
        self.consumers: Dict[str, asyncio.Queue] = {}
        self.consumer_tasks: Dict[str, asyncio.Task] = {}
        self.state = StreamState.IDLE
        self._consumer_id = 0
        self._lock = asyncio.Lock()
        
        self.logger = logging.getLogger(f"{__name__}.StreamMultiplexer")
    
    async def add_consumer(self) -> str:
        """
        Add new consumer.
        
        Returns:
            Consumer ID
        """
        async with self._lock:
            consumer_id = f"consumer_{self._consumer_id}"
            self._consumer_id += 1
            
            self.consumers[consumer_id] = asyncio.Queue(maxsize=self.buffer_size)
            
            self.logger.debug(f"Added consumer {consumer_id}")
            return consumer_id
    
    async def remove_consumer(self, consumer_id: str) -> None:
        """
        Remove consumer.
        
        Args:
            consumer_id: Consumer to remove
        """
        async with self._lock:
            if consumer_id in self.consumers:
                del self.consumers[consumer_id]
                
                if consumer_id in self.consumer_tasks:
                    self.consumer_tasks[consumer_id].cancel()
                    del self.consumer_tasks[consumer_id]
                
                self.logger.debug(f"Removed consumer {consumer_id}")
    
    async def broadcast(
        self,
        stream: AsyncGenerator[StreamChunk, None]
    ) -> None:
        """
        Broadcast stream to all consumers.
        
        Args:
            stream: Source stream to broadcast
        """
        self.state = StreamState.STREAMING
        
        try:
            async for chunk in stream:
                # Send to all consumers
                async with self._lock:
                    dead_consumers = []
                    
                    for consumer_id, queue in self.consumers.items():
                        try:
                            # Try to put with timeout
                            await asyncio.wait_for(
                                queue.put(chunk),
                                timeout=self.slow_consumer_timeout_ms / 1000
                            )
                        except asyncio.TimeoutError:
                            self.logger.warning(
                                f"Consumer {consumer_id} is too slow, marking for removal"
                            )
                            dead_consumers.append(consumer_id)
                        except Exception as e:
                            self.logger.error(f"Error sending to consumer {consumer_id}: {e}")
                            dead_consumers.append(consumer_id)
                    
                    # Remove dead consumers
                    for consumer_id in dead_consumers:
                        await self.remove_consumer(consumer_id)
            
            # Send final chunk
            final_chunk = StreamChunk(
                content="",
                token_count=0,
                is_final=True
            )
            
            async with self._lock:
                for queue in self.consumers.values():
                    await queue.put(final_chunk)
            
            self.state = StreamState.COMPLETED
            
        except Exception as e:
            self.logger.error(f"Broadcast error: {e}")
            self.state = StreamState.ERROR
            raise
    
    async def consume(
        self,
        consumer_id: str
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Consume stream for specific consumer.
        
        Args:
            consumer_id: Consumer ID
            
        Yields:
            Stream chunks
        """
        if consumer_id not in self.consumers:
            raise ValueError(f"Unknown consumer: {consumer_id}")
        
        queue = self.consumers[consumer_id]
        
        while True:
            try:
                chunk = await queue.get()
                yield chunk
                
                if chunk.is_final:
                    break
                    
            except Exception as e:
                self.logger.error(f"Consumer {consumer_id} error: {e}")
                break


class StreamingManager:
    """
    Manager for all streaming operations.
    
    Coordinates:
    - Provider-specific streaming
    - Stream optimization
    - Metrics collection
    - Error handling
    """
    
    def __init__(
        self,
        enable_buffering: bool = True,
        enable_multiplexing: bool = True,
        target_time_to_first_token_ms: float = 200
    ):
        """
        Initialize streaming manager.
        
        Args:
            enable_buffering: Enable stream buffering
            enable_multiplexing: Enable stream multiplexing
            target_time_to_first_token_ms: Target TTFT
        """
        self.enable_buffering = enable_buffering
        self.enable_multiplexing = enable_multiplexing
        self.target_ttft = target_time_to_first_token_ms
        
        # Active streams
        self.active_streams: Dict[str, StreamMetrics] = {}
        
        # Stream processors by provider
        self.processors: Dict[str, StreamProcessor] = {}
        
        # Multiplexers for shared streams
        self.multiplexers: Dict[str, StreamMultiplexer] = {}
        
        self.logger = logging.getLogger(f"{__name__}.StreamingManager")
    
    async def create_stream(
        self,
        request_id: str,
        provider: str,
        source: AsyncGenerator[LLMResponse, None]
    ) -> AsyncGenerator[LLMResponse, None]:
        """
        Create optimized stream from provider source.
        
        Args:
            request_id: Request identifier
            provider: Provider name
            source: Source stream from provider
            
        Yields:
            Optimized response chunks
        """
        # Initialize metrics
        metrics = StreamMetrics()
        self.active_streams[request_id] = metrics
        
        start_time = time.time()
        first_token = True
        last_chunk_time = start_time
        
        # Create buffer if enabled
        buffer = StreamBuffer() if self.enable_buffering else None
        
        try:
            async for response in source:
                current_time = time.time()
                
                # Record time to first token
                if first_token:
                    metrics.time_to_first_token_ms = (current_time - start_time) * 1000
                    first_token = False
                    
                    if metrics.time_to_first_token_ms > self.target_ttft:
                        self.logger.warning(
                            f"TTFT {metrics.time_to_first_token_ms:.1f}ms exceeds "
                            f"target {self.target_ttft}ms for {request_id}"
                        )
                
                # Create chunk
                chunk = StreamChunk(
                    content=response.content,
                    token_count=response.usage.completion_tokens if response.usage else 0,
                    metadata={
                        "provider": provider,
                        "model": response.model
                    }
                )
                
                # Update metrics
                chunk_delay = (current_time - last_chunk_time) * 1000
                metrics.update_chunk(chunk.token_count, chunk_delay)
                last_chunk_time = current_time
                
                # Process through buffer if enabled
                if buffer:
                    buffered_chunk = await buffer.add(chunk)
                    if buffered_chunk:
                        # Convert back to LLMResponse
                        yield self._chunk_to_response(buffered_chunk, response)
                else:
                    yield response
            
            # Flush remaining buffered chunks
            if buffer:
                remaining = await buffer.flush_all()
                for chunk in remaining:
                    yield self._chunk_to_response(chunk, response)
            
            # Finalize metrics
            total_time = (time.time() - start_time) * 1000
            metrics.finalize(total_time)
            
            self.logger.info(
                f"Stream {request_id} completed: "
                f"TTFT={metrics.time_to_first_token_ms:.1f}ms, "
                f"Total={total_time:.1f}ms, "
                f"Tokens={metrics.total_tokens}, "
                f"TPS={metrics.tokens_per_second:.1f}"
            )
            
        except Exception as e:
            self.logger.error(f"Stream {request_id} error: {e}")
            raise
        finally:
            # Clean up
            if request_id in self.active_streams:
                del self.active_streams[request_id]
    
    def _chunk_to_response(
        self,
        chunk: StreamChunk,
        template: LLMResponse
    ) -> LLMResponse:
        """Convert stream chunk back to LLM response."""
        return LLMResponse(
            content=chunk.content,
            finish_reason="length" if not chunk.is_final else "stop",
            model=template.model,
            provider=template.provider,
            usage=template.usage,
            request_id=template.request_id,
            response_time_ms=0,  # Not relevant for streaming
            metadata=chunk.metadata
        )
    
    async def create_multiplexed_stream(
        self,
        request_id: str,
        provider: str,
        source: AsyncGenerator[LLMResponse, None],
        num_consumers: int = 1
    ) -> List[str]:
        """
        Create multiplexed stream for multiple consumers.
        
        Args:
            request_id: Request identifier
            provider: Provider name
            source: Source stream
            num_consumers: Number of initial consumers
            
        Returns:
            List of consumer IDs
        """
        # Create multiplexer
        multiplexer = StreamMultiplexer()
        self.multiplexers[request_id] = multiplexer
        
        # Add consumers
        consumer_ids = []
        for _ in range(num_consumers):
            consumer_id = await multiplexer.add_consumer()
            consumer_ids.append(consumer_id)
        
        # Start broadcasting in background
        asyncio.create_task(
            self._broadcast_stream(request_id, provider, source, multiplexer)
        )
        
        return consumer_ids
    
    async def _broadcast_stream(
        self,
        request_id: str,
        provider: str,
        source: AsyncGenerator[LLMResponse, None],
        multiplexer: StreamMultiplexer
    ) -> None:
        """Broadcast stream to multiplexer."""
        try:
            # Convert LLMResponse to StreamChunk
            async def response_to_chunks():
                async for response in source:
                    yield StreamChunk(
                        content=response.content,
                        token_count=response.usage.completion_tokens if response.usage else 0,
                        metadata={
                            "provider": provider,
                            "model": response.model
                        }
                    )
            
            await multiplexer.broadcast(response_to_chunks())
            
        except Exception as e:
            self.logger.error(f"Broadcast error for {request_id}: {e}")
        finally:
            # Clean up
            if request_id in self.multiplexers:
                del self.multiplexers[request_id]
    
    def get_metrics(self, request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get streaming metrics.
        
        Args:
            request_id: Specific request or None for all
            
        Returns:
            Metrics dictionary
        """
        if request_id:
            if request_id in self.active_streams:
                metrics = self.active_streams[request_id]
                return {
                    "request_id": request_id,
                    "time_to_first_token_ms": metrics.time_to_first_token_ms,
                    "total_tokens": metrics.total_tokens,
                    "total_chunks": metrics.total_chunks,
                    "average_chunk_size": metrics.average_chunk_size,
                    "average_chunk_delay_ms": metrics.average_chunk_delay_ms,
                    "tokens_per_second": metrics.tokens_per_second,
                    "status": "active"
                }
            else:
                return {"request_id": request_id, "status": "not_found"}
        else:
            # Return all active streams
            return {
                req_id: self.get_metrics(req_id)
                for req_id in self.active_streams.keys()
            }