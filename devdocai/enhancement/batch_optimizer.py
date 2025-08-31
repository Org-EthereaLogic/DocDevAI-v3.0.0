"""
Batch processing optimization for M009 Enhancement Pipeline.

Provides intelligent document batching, similarity grouping, parallel processing,
memory-efficient streaming, and error isolation.
"""

import asyncio
import logging
import time
import mmh3  # For faster hashing
import psutil  # For memory monitoring
from typing import Dict, List, Optional, Any, Tuple, Union, AsyncIterator, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import heapq
import numpy as np
from threading import Semaphore, Lock
import hashlib
from asyncio import Queue, PriorityQueue
import multiprocessing as mp

# Try to import similarity libraries
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.cluster import KMeans
    CLUSTERING_AVAILABLE = True
except ImportError:
    CLUSTERING_AVAILABLE = False
    logging.info("Clustering libraries not available, using simple batching")

logger = logging.getLogger(__name__)


@dataclass
class BatchDocument:
    """Document wrapper for batch processing."""
    
    id: str
    content: str
    metadata: Dict[str, Any]
    priority: int = 0
    group_id: Optional[str] = None
    size_bytes: int = 0
    processing_time_estimate: float = 0.0
    
    def __hash__(self):
        return hash(self.id)
    
    def __lt__(self, other):
        # For priority queue - higher priority first
        return self.priority > other.priority


@dataclass
class BatchGroup:
    """Group of similar documents for batch processing."""
    
    group_id: str
    documents: List[BatchDocument]
    centroid: Optional[np.ndarray] = None
    total_size_bytes: int = 0
    estimated_processing_time: float = 0.0
    
    def add_document(self, doc: BatchDocument) -> None:
        """Add document to group."""
        self.documents.append(doc)
        self.total_size_bytes += doc.size_bytes
        self.estimated_processing_time += doc.processing_time_estimate
    
    def can_add(self, doc: BatchDocument, max_size_mb: int = 10) -> bool:
        """Check if document can be added without exceeding limits."""
        max_bytes = max_size_mb * 1024 * 1024
        return (self.total_size_bytes + doc.size_bytes) <= max_bytes


@dataclass
class BatchResult:
    """Result of batch processing."""
    
    batch_id: str
    documents_processed: int
    documents_failed: int
    total_time: float
    throughput: float  # docs/second
    errors: List[Dict[str, Any]]
    results: Dict[str, Any]
    memory_peak_mb: float


class DocumentBatcher:
    """Intelligent document batching system."""
    
    def __init__(
        self,
        batch_size: int = 10,
        max_batch_memory_mb: int = 50,
        similarity_threshold: float = 0.7
    ):
        """
        Initialize document batcher.
        
        Args:
            batch_size: Maximum documents per batch
            max_batch_memory_mb: Maximum memory per batch
            similarity_threshold: Threshold for similarity grouping
        """
        self.batch_size = batch_size
        self.max_batch_memory_mb = max_batch_memory_mb
        self.similarity_threshold = similarity_threshold
        self.vectorizer = None
        
        if CLUSTERING_AVAILABLE:
            self.vectorizer = TfidfVectorizer(
                max_features=100,
                stop_words='english',
                ngram_range=(1, 2)
            )
    
    def create_batches(
        self,
        documents: List[Union[str, Dict[str, Any]]],
        use_similarity: bool = True
    ) -> List[BatchGroup]:
        """
        Create optimized batches from documents.
        
        Args:
            documents: List of documents
            use_similarity: Group by similarity
            
        Returns:
            List of batch groups
        """
        # Convert to BatchDocument objects
        batch_docs = self._prepare_documents(documents)
        
        if use_similarity and CLUSTERING_AVAILABLE and len(batch_docs) > 10:
            return self._create_similarity_batches(batch_docs)
        else:
            return self._create_simple_batches(batch_docs)
    
    def _prepare_documents(
        self,
        documents: List[Union[str, Dict[str, Any]]]
    ) -> List[BatchDocument]:
        """Convert raw documents to BatchDocument objects."""
        batch_docs = []
        
        for i, doc in enumerate(documents):
            if isinstance(doc, str):
                content = doc
                metadata = {}
            else:
                content = doc.get("content", "")
                metadata = doc.get("metadata", {})
            
            # Use faster hashing
            doc_id = str(mmh3.hash128(f"{i}_{content[:100]}", signed=False))[:8]
            size_bytes = len(content.encode('utf-8'))
            
            # Estimate processing time based on size
            processing_time = self._estimate_processing_time(size_bytes)
            
            batch_doc = BatchDocument(
                id=doc_id,
                content=content,
                metadata=metadata,
                priority=metadata.get("priority", 0),
                size_bytes=size_bytes,
                processing_time_estimate=processing_time
            )
            batch_docs.append(batch_doc)
        
        return batch_docs
    
    def _estimate_processing_time(self, size_bytes: int) -> float:
        """Estimate processing time based on document size with better model."""
        # Improved model: logarithmic scaling for better accuracy
        # Base time + size factor with diminishing returns
        base_time = 0.1  # 100ms base
        size_factor = np.log1p(size_bytes / 1024) * 0.05  # Logarithmic scaling
        return base_time + size_factor
    
    def _create_similarity_batches(
        self,
        documents: List[BatchDocument]
    ) -> List[BatchGroup]:
        """Create batches based on document similarity."""
        if not documents:
            return []
        
        try:
            # Extract text for vectorization
            texts = [doc.content[:1000] for doc in documents]  # Limit text length
            
            # Vectorize documents with caching
            if not hasattr(self, '_vector_cache'):
                self._vector_cache = {}
            
            # Check cache for similar texts
            cache_key = mmh3.hash128(''.join(texts[:3]), signed=False)
            if cache_key in self._vector_cache:
                doc_vectors = self._vector_cache[cache_key]
            else:
                doc_vectors = self.vectorizer.fit_transform(texts)
                self._vector_cache[cache_key] = doc_vectors
            
            # Determine optimal number of clusters
            n_clusters = min(len(documents) // self.batch_size + 1, 20)
            
            # Cluster documents
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            cluster_labels = kmeans.fit_predict(doc_vectors)
            
            # Create batch groups
            groups = defaultdict(lambda: BatchGroup(
                group_id=hashlib.md5(str(time.time()).encode()).hexdigest()[:8],
                documents=[]
            ))
            
            for doc, label in zip(documents, cluster_labels):
                group = groups[label]
                
                # Check size limits
                if (len(group.documents) >= self.batch_size or
                    not group.can_add(doc, self.max_batch_memory_mb)):
                    # Create new group
                    new_group_id = f"{label}_{len(groups)}"
                    group = BatchGroup(group_id=new_group_id, documents=[])
                    groups[new_group_id] = group
                
                group.add_document(doc)
                doc.group_id = group.group_id
            
            # Set centroids for groups
            for label, group in groups.items():
                if isinstance(label, int) and label < len(kmeans.cluster_centers_):
                    group.centroid = kmeans.cluster_centers_[label]
            
            return list(groups.values())
            
        except Exception as e:
            logger.warning(f"Similarity batching failed, falling back to simple: {e}")
            return self._create_simple_batches(documents)
    
    def _create_simple_batches(
        self,
        documents: List[BatchDocument]
    ) -> List[BatchGroup]:
        """Create simple size-based batches."""
        # Sort by priority
        sorted_docs = sorted(documents, key=lambda d: d.priority, reverse=True)
        
        batches = []
        current_batch = BatchGroup(
            group_id=hashlib.md5(str(time.time()).encode()).hexdigest()[:8],
            documents=[]
        )
        
        for doc in sorted_docs:
            if (len(current_batch.documents) >= self.batch_size or
                not current_batch.can_add(doc, self.max_batch_memory_mb)):
                # Save current batch and start new one
                if current_batch.documents:
                    batches.append(current_batch)
                current_batch = BatchGroup(
                    group_id=hashlib.md5(str(time.time()).encode()).hexdigest()[:8],
                    documents=[]
                )
            
            current_batch.add_document(doc)
            doc.group_id = current_batch.group_id
        
        # Add last batch
        if current_batch.documents:
            batches.append(current_batch)
        
        return batches


class BatchProcessor:
    """High-performance parallel batch processing engine."""
    
    def __init__(
        self,
        max_workers: int = 8,  # Increased for better parallelism
        max_concurrent_batches: int = 4,  # Increased for better throughput
        memory_limit_mb: int = 500,
        use_process_pool: bool = False  # Option for CPU-bound tasks
    ):
        """
        Initialize batch processor.
        
        Args:
            max_workers: Maximum parallel workers
            max_concurrent_batches: Maximum concurrent batch processing
            memory_limit_mb: Memory limit for processing
        """
        self.max_workers = max_workers
        self.max_concurrent_batches = max_concurrent_batches
        self.memory_limit_mb = memory_limit_mb
        self.use_process_pool = use_process_pool
        
        # Resource management
        self.batch_semaphore = Semaphore(max_concurrent_batches)
        self.memory_tracker = MemoryTracker(memory_limit_mb)
        
        # Progress tracking with thread safety
        self.processed_count = 0
        self.failed_count = 0
        self.start_time = None
        self._stats_lock = Lock()
        
        # Performance optimizations
        self.result_queue: Queue = Queue(maxsize=100)
        self.priority_queue: PriorityQueue = PriorityQueue()
        
        # Connection pooling for external resources
        self.connection_pool = ConnectionPool(max_connections=max_workers * 2)
    
    async def process_batches(
        self,
        batches: List[BatchGroup],
        process_func: Any,
        progress_callback: Optional[Any] = None
    ) -> List[BatchResult]:
        """
        Process batches in parallel.
        
        Args:
            batches: List of batch groups
            process_func: Function to process each document
            progress_callback: Optional progress callback
            
        Returns:
            List of batch results
        """
        self.start_time = time.time()
        self.processed_count = 0
        self.failed_count = 0
        
        # Process batches concurrently
        tasks = []
        for batch in batches:
            task = asyncio.create_task(
                self._process_batch(batch, process_func, progress_callback)
            )
            tasks.append(task)
        
        # Wait for all batches
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        batch_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch {batches[i].group_id} failed: {result}")
                batch_results.append(BatchResult(
                    batch_id=batches[i].group_id,
                    documents_processed=0,
                    documents_failed=len(batches[i].documents),
                    total_time=0,
                    throughput=0,
                    errors=[{"batch_error": str(result)}],
                    results={},
                    memory_peak_mb=0
                ))
            else:
                batch_results.append(result)
        
        return batch_results
    
    async def _process_batch(
        self,
        batch: BatchGroup,
        process_func: Any,
        progress_callback: Optional[Any]
    ) -> BatchResult:
        """Process a single batch."""
        async with self.batch_semaphore:
            batch_start = time.time()
            results = {}
            errors = []
            processed = 0
            failed = 0
            
            # Check memory before processing
            if not self.memory_tracker.can_allocate(batch.total_size_bytes):
                await self._wait_for_memory(batch.total_size_bytes)
            
            # Allocate memory
            self.memory_tracker.allocate(batch.total_size_bytes)
            
            try:
                # Process documents in parallel within batch
                doc_tasks = []
                for doc in batch.documents:
                    task = asyncio.create_task(
                        self._process_document(doc, process_func)
                    )
                    doc_tasks.append((doc.id, task))
                
                # Collect results
                for doc_id, task in doc_tasks:
                    try:
                        result = await task
                        results[doc_id] = result
                        processed += 1
                        self.processed_count += 1
                        
                        # Progress callback
                        if progress_callback:
                            await progress_callback(self.processed_count, len(batch.documents))
                            
                    except Exception as e:
                        logger.error(f"Document {doc_id} failed: {e}")
                        errors.append({"doc_id": doc_id, "error": str(e)})
                        failed += 1
                        self.failed_count += 1
                
                # Calculate metrics
                batch_time = time.time() - batch_start
                throughput = processed / batch_time if batch_time > 0 else 0
                
                return BatchResult(
                    batch_id=batch.group_id,
                    documents_processed=processed,
                    documents_failed=failed,
                    total_time=batch_time,
                    throughput=throughput,
                    errors=errors,
                    results=results,
                    memory_peak_mb=self.memory_tracker.get_peak_usage_mb()
                )
                
            finally:
                # Release memory
                self.memory_tracker.release(batch.total_size_bytes)
    
    async def _process_document(
        self,
        doc: BatchDocument,
        process_func: Any
    ) -> Any:
        """Process a single document with error isolation."""
        try:
            # Call the processing function
            if asyncio.iscoroutinefunction(process_func):
                result = await process_func(doc.content, doc.metadata)
            else:
                # Run in executor if not async
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    process_func,
                    doc.content,
                    doc.metadata
                )
            return result
        except Exception as e:
            # Error isolation - one failure doesn't affect others
            logger.error(f"Document processing failed: {e}")
            raise
    
    async def _wait_for_memory(self, required_bytes: int) -> None:
        """Wait for memory to become available."""
        wait_time = 0.1
        max_wait = 30  # Maximum 30 seconds
        total_wait = 0
        
        while not self.memory_tracker.can_allocate(required_bytes) and total_wait < max_wait:
            await asyncio.sleep(wait_time)
            total_wait += wait_time
            wait_time = min(wait_time * 1.5, 2.0)  # Exponential backoff
        
        if total_wait >= max_wait:
            raise TimeoutError(f"Timeout waiting for {required_bytes / 1024 / 1024:.1f}MB memory")


class StreamingBatchProcessor:
    """Memory-efficient streaming batch processor."""
    
    def __init__(
        self,
        batch_size: int = 10,
        buffer_size: int = 100
    ):
        """
        Initialize streaming processor.
        
        Args:
            batch_size: Documents per batch
            buffer_size: Buffer size for streaming
        """
        self.batch_size = batch_size
        self.buffer_size = buffer_size
    
    async def process_stream(
        self,
        document_stream: AsyncIterator[Union[str, Dict[str, Any]]],
        process_func: Any,
        result_callback: Optional[Any] = None
    ) -> AsyncIterator[BatchResult]:
        """
        Process documents from a stream.
        
        Args:
            document_stream: Async iterator of documents
            process_func: Processing function
            result_callback: Optional result callback
            
        Yields:
            Batch results as they complete
        """
        buffer = []
        batcher = DocumentBatcher(batch_size=self.batch_size)
        processor = BatchProcessor()
        
        async for doc in document_stream:
            buffer.append(doc)
            
            # Process when buffer is full
            if len(buffer) >= self.buffer_size:
                batches = batcher.create_batches(buffer)
                results = await processor.process_batches(batches, process_func)
                
                for result in results:
                    if result_callback:
                        await result_callback(result)
                    yield result
                
                buffer.clear()
        
        # Process remaining documents
        if buffer:
            batches = batcher.create_batches(buffer)
            results = await processor.process_batches(batches, process_func)
            
            for result in results:
                if result_callback:
                    await result_callback(result)
                yield result


class ConnectionPool:
    """Connection pool for external resources."""
    
    def __init__(self, max_connections: int = 10):
        """Initialize connection pool."""
        self.max_connections = max_connections
        self.connections = deque(maxlen=max_connections)
        self.lock = Lock()
        self.available = Semaphore(max_connections)
    
    async def acquire(self):
        """Acquire a connection from the pool."""
        await asyncio.get_event_loop().run_in_executor(None, self.available.acquire)
        with self.lock:
            if self.connections:
                return self.connections.popleft()
            # Create new connection if needed
            return self._create_connection()
    
    async def release(self, conn):
        """Release connection back to pool."""
        with self.lock:
            self.connections.append(conn)
        self.available.release()
    
    def _create_connection(self):
        """Create a new connection (placeholder)."""
        return {"id": mmh3.hash128(str(time.time()), signed=False)}


class MemoryTracker:
    """Enhanced memory tracker with real-time monitoring."""
    
    def __init__(self, limit_mb: int):
        """
        Initialize memory tracker with system monitoring.
        
        Args:
            limit_mb: Memory limit in MB
        """
        self.limit_bytes = limit_mb * 1024 * 1024
        self.current_usage = 0
        self.peak_usage = 0
        self.lock = asyncio.Lock()
        
        # System memory monitoring
        self.process = psutil.Process()
        self.system_memory = psutil.virtual_memory()
    
    async def allocate(self, size_bytes: int) -> bool:
        """Allocate memory if available."""
        async with self.lock:
            if self.current_usage + size_bytes <= self.limit_bytes:
                self.current_usage += size_bytes
                self.peak_usage = max(self.peak_usage, self.current_usage)
                return True
            return False
    
    async def release(self, size_bytes: int) -> None:
        """Release allocated memory."""
        async with self.lock:
            self.current_usage = max(0, self.current_usage - size_bytes)
    
    def can_allocate(self, size_bytes: int) -> bool:
        """Check if memory can be allocated."""
        return self.current_usage + size_bytes <= self.limit_bytes
    
    def get_usage_mb(self) -> float:
        """Get current usage in MB."""
        return self.current_usage / (1024 * 1024)
    
    def get_peak_usage_mb(self) -> float:
        """Get peak usage in MB."""
        return self.peak_usage / (1024 * 1024)


class BatchOptimizer:
    """
    Main batch optimization coordinator.
    
    Combines intelligent batching, parallel processing,
    and memory-efficient streaming.
    """
    
    def __init__(
        self,
        batch_size: int = 10,
        max_workers: int = 4,
        max_memory_mb: int = 500,
        use_similarity_grouping: bool = True
    ):
        """
        Initialize batch optimizer.
        
        Args:
            batch_size: Documents per batch
            max_workers: Maximum parallel workers
            max_memory_mb: Maximum memory usage
            use_similarity_grouping: Enable similarity-based grouping
        """
        self.batcher = DocumentBatcher(
            batch_size=batch_size,
            max_batch_memory_mb=max_memory_mb // 10  # Allocate 10% per batch
        )
        self.processor = BatchProcessor(
            max_workers=max_workers,
            memory_limit_mb=max_memory_mb
        )
        self.streaming_processor = StreamingBatchProcessor(
            batch_size=batch_size
        )
        self.use_similarity_grouping = use_similarity_grouping
        
        # Metrics
        self.total_processed = 0
        self.total_failed = 0
        self.total_time = 0
        
        logger.info(
            f"Batch optimizer initialized: batch_size={batch_size}, "
            f"workers={max_workers}, memory_limit={max_memory_mb}MB"
        )
    
    async def optimize_and_process(
        self,
        documents: List[Union[str, Dict[str, Any]]],
        process_func: Any,
        progress_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Optimize and process documents in batches.
        
        Args:
            documents: List of documents
            process_func: Processing function
            progress_callback: Optional progress callback
            
        Returns:
            Processing results and metrics
        """
        start_time = time.time()
        
        # Create optimized batches
        batches = self.batcher.create_batches(
            documents,
            use_similarity=self.use_similarity_grouping
        )
        
        logger.info(f"Created {len(batches)} batches from {len(documents)} documents")
        
        # Process batches
        batch_results = await self.processor.process_batches(
            batches,
            process_func,
            progress_callback
        )
        
        # Aggregate results
        all_results = {}
        total_processed = 0
        total_failed = 0
        
        for batch_result in batch_results:
            all_results.update(batch_result.results)
            total_processed += batch_result.documents_processed
            total_failed += batch_result.documents_failed
        
        # Calculate metrics
        total_time = time.time() - start_time
        throughput = total_processed / total_time if total_time > 0 else 0
        
        # Update global metrics
        self.total_processed += total_processed
        self.total_failed += total_failed
        self.total_time += total_time
        
        return {
            "results": all_results,
            "metrics": {
                "documents_processed": total_processed,
                "documents_failed": total_failed,
                "total_time": total_time,
                "throughput_docs_per_sec": throughput,
                "throughput_docs_per_min": throughput * 60,
                "batches": len(batches),
                "average_batch_size": total_processed / len(batches) if batches else 0,
                "memory_peak_mb": self.processor.memory_tracker.get_peak_usage_mb()
            },
            "batch_details": [
                {
                    "batch_id": br.batch_id,
                    "processed": br.documents_processed,
                    "failed": br.documents_failed,
                    "time": br.total_time,
                    "throughput": br.throughput
                }
                for br in batch_results
            ]
        }
    
    def get_global_metrics(self) -> Dict[str, Any]:
        """Get global optimization metrics."""
        return {
            "total_processed": self.total_processed,
            "total_failed": self.total_failed,
            "total_time": self.total_time,
            "average_throughput": self.total_processed / self.total_time if self.total_time > 0 else 0,
            "success_rate": self.total_processed / (self.total_processed + self.total_failed) if (self.total_processed + self.total_failed) > 0 else 0
        }