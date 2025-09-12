"""
M011 Batch Operations Manager - Strategy Pattern Implementation
DevDocAI v3.0.0 - Pass 4: Refactoring & Integration

Purpose: Extract batch processing strategies for clean architecture
Dependencies: None (pure strategy implementations)
Performance: Maintains all Pass 2/3 achievements

Strategy Pattern for different batch processing approaches:
- StreamingStrategy: Memory-efficient large document processing
- ConcurrentStrategy: High-throughput parallel processing
- PriorityStrategy: Priority-based queue management
- SecureStrategy: Security-hardened processing
"""

import asyncio
import hashlib
import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Callable, Dict, List

logger = logging.getLogger(__name__)


# ============================================================================
# Strategy Interface
# ============================================================================


class BatchStrategy(ABC):
    """Abstract base class for batch processing strategies."""

    @abstractmethod
    async def process(
        self, documents: List[Dict[str, Any]], operation: Callable, **kwargs
    ) -> List[Dict[str, Any]]:
        """Process documents using specific strategy."""
        pass

    @abstractmethod
    def get_optimal_batch_size(self, total_docs: int) -> int:
        """Calculate optimal batch size for strategy."""
        pass

    @abstractmethod
    def supports_streaming(self) -> bool:
        """Check if strategy supports streaming."""
        pass


# ============================================================================
# Streaming Strategy
# ============================================================================


class StreamingStrategy(BatchStrategy):
    """Memory-efficient streaming strategy for large documents."""

    def __init__(self, chunk_size_kb: int = 1024, max_concurrent: int = 8, **_: Any):
        self.chunk_size = chunk_size_kb * 1024

    async def process(
        self, documents: List[Dict[str, Any]], operation: Callable, **kwargs
    ) -> List[Dict[str, Any]]:
        """Process documents in streaming chunks."""
        results = []

        for doc in documents:
            if self._is_large_document(doc):
                result = await self._process_streaming(doc, operation, **kwargs)
            else:
                result = await self._process_standard(doc, operation, **kwargs)
            results.append(result)

        return results

    async def _process_streaming(
        self, document: Dict[str, Any], operation: Callable, **kwargs
    ) -> Dict[str, Any]:
        """Process large document in chunks."""
        content = document.get("content", "")
        chunks = self._chunk_content(content)
        chunk_results = []

        async for chunk in self._stream_chunks(chunks):
            chunk_doc = {**document, "content": chunk}
            if asyncio.iscoroutinefunction(operation):
                result = await operation(chunk_doc, **kwargs)
            else:
                result = operation(chunk_doc, **kwargs)
            chunk_results.append(result)

        return self._merge_chunk_results(chunk_results)

    async def _process_standard(
        self, document: Dict[str, Any], operation: Callable, **kwargs
    ) -> Dict[str, Any]:
        """Process standard document."""
        if asyncio.iscoroutinefunction(operation):
            return await operation(document, **kwargs)
        return operation(document, **kwargs)

    def _is_large_document(self, document: Dict[str, Any]) -> bool:
        """Check if document is large enough for streaming."""
        content = document.get("content", "")
        return len(content.encode()) > self.chunk_size

    def _chunk_content(self, content: str) -> List[str]:
        """Split content into chunks."""
        chunks = []
        for i in range(0, len(content), self.chunk_size):
            chunks.append(content[i : i + self.chunk_size])
        return chunks

    async def _stream_chunks(self, chunks: List[str]) -> AsyncIterator[str]:
        """Stream chunks asynchronously."""
        for chunk in chunks:
            yield chunk
            await asyncio.sleep(0)  # Yield control

    def _merge_chunk_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge results from multiple chunks."""
        if not results:
            return {}

        merged = results[0].copy()
        if "content" in merged:
            merged["content"] = "".join(r.get("content", "") for r in results)
        return merged

    def get_optimal_batch_size(self, total_docs: int) -> int:
        """Calculate optimal batch size for streaming."""
        # Smaller batches for streaming to manage memory
        return min(10, total_docs)

    def supports_streaming(self) -> bool:
        """Streaming strategy supports streaming."""
        return True


# ============================================================================
# Concurrent Strategy
# ============================================================================


class ConcurrentStrategy(BatchStrategy):
    """High-throughput concurrent processing strategy."""

    def __init__(self, max_concurrent: int = 8):
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def process(
        self, documents: List[Dict[str, Any]], operation: Callable, **kwargs
    ) -> List[Dict[str, Any]]:
        """Process documents concurrently."""
        tasks = []

        for doc in documents:
            task = asyncio.create_task(self._process_with_semaphore(doc, operation, **kwargs))
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Document {i} failed: {result}")
                processed_results.append(
                    {"error": str(result), "document_id": documents[i].get("id", "unknown")}
                )
            else:
                processed_results.append(result)

        return processed_results

    async def _process_with_semaphore(
        self, document: Dict[str, Any], operation: Callable, **kwargs
    ) -> Dict[str, Any]:
        """Process document with semaphore control."""
        async with self._semaphore:
            if asyncio.iscoroutinefunction(operation):
                return await operation(document, **kwargs)
            else:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, operation, document, **kwargs)

    def get_optimal_batch_size(self, total_docs: int) -> int:
        """Calculate optimal batch size for concurrent processing."""
        # Larger batches for concurrent processing
        return min(self.max_concurrent * 2, total_docs, 50)

    def supports_streaming(self) -> bool:
        """Concurrent strategy doesn't stream."""
        return False


# ============================================================================
# Priority Strategy
# ============================================================================


class PriorityStrategy(BatchStrategy):
    """Priority-based processing strategy."""

    def __init__(self, max_concurrent: int = 8, **_: Any):
        # max_concurrent accepted for interface parity; not used here
        self._priority_queue = asyncio.PriorityQueue()

    async def process(
        self, documents: List[Dict[str, Any]], operation: Callable, **kwargs
    ) -> List[Dict[str, Any]]:
        """Process documents by priority."""
        # Sort documents by priority
        sorted_docs = self._sort_by_priority(documents)

        results = []
        for doc in sorted_docs:
            if asyncio.iscoroutinefunction(operation):
                result = await operation(doc, **kwargs)
            else:
                result = operation(doc, **kwargs)
            results.append(result)

        return results

    def _sort_by_priority(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort documents by priority (lower number = higher priority)."""
        return sorted(documents, key=lambda d: d.get("priority", float("inf")))

    def get_optimal_batch_size(self, total_docs: int) -> int:
        """Calculate optimal batch size for priority processing."""
        # Moderate batch size for priority processing
        return min(25, total_docs)

    def supports_streaming(self) -> bool:
        """Priority strategy doesn't stream."""
        return False


# ============================================================================
# Secure Strategy
# ============================================================================


class SecureStrategy(BatchStrategy):
    """Security-hardened processing strategy."""

    def __init__(self, enable_validation: bool = True, max_concurrent: int = 8, **_: Any):
        self.enable_validation = enable_validation
        self._validation_cache = {}

    async def process(
        self, documents: List[Dict[str, Any]], operation: Callable, **kwargs
    ) -> List[Dict[str, Any]]:
        """Process documents with security validation."""
        results = []

        for doc in documents:
            # Validate document
            if self.enable_validation:
                is_valid, sanitized_doc = await self._validate_document(doc)
                if not is_valid:
                    results.append(
                        {
                            "error": "Security validation failed",
                            "document_id": doc.get("id", "unknown"),
                        }
                    )
                    continue
                doc = sanitized_doc

            # Generate secure hash for caching
            doc_hash = self._generate_secure_hash(doc)

            # Check cache
            if doc_hash in self._validation_cache:
                results.append(self._validation_cache[doc_hash])
                continue

            # Process document
            if asyncio.iscoroutinefunction(operation):
                result = await operation(doc, **kwargs)
            else:
                result = operation(doc, **kwargs)

            # Cache result
            self._validation_cache[doc_hash] = result
            results.append(result)

        return results

    async def _validate_document(self, document: Dict[str, Any]) -> tuple[bool, Dict[str, Any]]:
        """Validate and sanitize document."""
        # Basic validation
        if not document.get("id"):
            return False, document

        # Size check
        content = document.get("content", "")
        if len(content) > 10_000_000:  # 10MB limit
            return False, document

        # Sanitize content (remove potential XSS)
        sanitized = document.copy()
        if "content" in sanitized:
            sanitized["content"] = self._sanitize_content(content)

        return True, sanitized

    def _sanitize_content(self, content: str) -> str:
        """Remove potentially dangerous content."""
        # Simple sanitization - remove script tags
        import re

        content = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.DOTALL)
        content = re.sub(r"javascript:", "", content, flags=re.IGNORECASE)
        return content

    def _generate_secure_hash(self, document: Dict[str, Any]) -> str:
        """Generate secure hash for document."""
        doc_str = f"{document.get('id', '')}:{document.get('content', '')[:100]}"
        return hashlib.sha256(doc_str.encode()).hexdigest()

    def get_optimal_batch_size(self, total_docs: int) -> int:
        """Calculate optimal batch size for secure processing."""
        # Smaller batches for thorough validation
        return min(20, total_docs)

    def supports_streaming(self) -> bool:
        """Secure strategy doesn't stream."""
        return False


# ============================================================================
# Strategy Factory
# ============================================================================


class BatchStrategyFactory:
    """Factory for creating batch processing strategies."""

    _strategies = {
        "streaming": StreamingStrategy,
        "concurrent": ConcurrentStrategy,
        "priority": PriorityStrategy,
        "secure": SecureStrategy,
    }

    @classmethod
    def create(cls, strategy_type: str, **kwargs) -> BatchStrategy:
        """
        Create a batch processing strategy.

        Args:
            strategy_type: Type of strategy to create
            **kwargs: Strategy-specific configuration

        Returns:
            BatchStrategy instance
        """
        if strategy_type not in cls._strategies:
            raise ValueError(f"Unknown strategy type: {strategy_type}")

        strategy_class = cls._strategies[strategy_type]
        return strategy_class(**kwargs)

    @classmethod
    def register(cls, name: str, strategy_class: type):
        """Register a new strategy type."""
        if not issubclass(strategy_class, BatchStrategy):
            raise TypeError("Strategy must inherit from BatchStrategy")
        cls._strategies[name] = strategy_class

    @classmethod
    def list_strategies(cls) -> List[str]:
        """List available strategy types."""
        return list(cls._strategies.keys())
