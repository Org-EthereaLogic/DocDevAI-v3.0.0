"""
Test Suite for M011 Batch Operations Manager - Pass 4 Refactored Architecture
DevDocAI v3.0.0

Tests the clean, modular architecture with design patterns.
Verifies all functionality is preserved with improved code organization.
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from devdocai.operations.batch_refactored import (
    BatchOperationsManager,
    BatchConfig,
    BatchConfigBuilder,
    BatchResult,
    create_batch_manager,
    process_documents_batch,
)
from devdocai.operations.batch_strategies import (
    BatchStrategyFactory,
    StreamingStrategy,
    ConcurrentStrategy,
    PriorityStrategy,
    SecureStrategy,
)
from devdocai.operations.batch_processors import (
    DocumentProcessorFactory,
    EnhanceProcessor,
    ValidateProcessor,
)
from devdocai.operations.batch_monitoring import (
    BatchMonitor,
    BatchEvent,
    ProgressTracker,
    MetricsCollector,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def sample_documents():
    """Create sample documents for testing."""
    return [
        {"id": f"doc_{i}", "content": f"Content for document {i}", "priority": i % 3}
        for i in range(10)
    ]


@pytest.fixture
def batch_config():
    """Create test batch configuration."""
    return BatchConfig(
        strategy_type="concurrent",
        processor_type="validate",
        max_concurrent=4,
        batch_size=5,
        enable_monitoring=True,
    )


@pytest.fixture
async def batch_manager(batch_config):
    """Create batch operations manager."""
    manager = BatchOperationsManager(batch_config)
    yield manager
    await manager.shutdown()


# ============================================================================
# Strategy Pattern Tests
# ============================================================================


class TestBatchStrategies:
    """Test batch processing strategies."""

    def test_strategy_factory_creation(self):
        """Test strategy factory creates correct types."""
        strategies = ["streaming", "concurrent", "priority", "secure"]
        
        for strategy_type in strategies:
            strategy = BatchStrategyFactory.create(strategy_type)
            assert strategy is not None
            assert hasattr(strategy, "process")
            assert hasattr(strategy, "get_optimal_batch_size")

    def test_strategy_factory_registration(self):
        """Test registering custom strategy."""
        class CustomStrategy(StreamingStrategy):
            pass
        
        BatchStrategyFactory.register("custom", CustomStrategy)
        assert "custom" in BatchStrategyFactory.list_strategies()
        
        strategy = BatchStrategyFactory.create("custom")
        assert isinstance(strategy, CustomStrategy)

    @pytest.mark.asyncio
    async def test_streaming_strategy(self):
        """Test streaming strategy for large documents."""
        strategy = StreamingStrategy(chunk_size_kb=1)  # Small chunk for testing
        
        # Create large document
        large_doc = {
            "id": "large_doc",
            "content": "x" * 2048  # 2KB content
        }
        
        # Mock processor
        async def processor(doc, **kwargs):
            return {"processed": doc.get("id")}
        
        results = await strategy.process([large_doc], processor)
        assert len(results) == 1
        assert results[0]["processed"] == "large_doc"

    @pytest.mark.asyncio
    async def test_concurrent_strategy(self):
        """Test concurrent processing strategy."""
        strategy = ConcurrentStrategy(max_concurrent=2)
        
        docs = [{"id": f"doc_{i}"} for i in range(5)]
        process_times = []
        
        async def processor(doc, **kwargs):
            start = time.time()
            await asyncio.sleep(0.1)  # Simulate processing
            process_times.append(time.time() - start)
            return {"processed": doc["id"]}
        
        start = time.time()
        results = await strategy.process(docs, processor)
        total_time = time.time() - start
        
        # Should be faster than sequential (0.5s)
        assert total_time < 0.4  # Allow some overhead
        assert len(results) == 5

    def test_priority_strategy(self):
        """Test priority-based processing."""
        strategy = PriorityStrategy()
        
        docs = [
            {"id": "doc_1", "priority": 2},
            {"id": "doc_2", "priority": 0},  # Highest priority
            {"id": "doc_3", "priority": 1},
        ]
        
        # Track processing order
        process_order = []
        
        async def processor(doc, **kwargs):
            process_order.append(doc["id"])
            return {"processed": doc["id"]}
        
        asyncio.run(strategy.process(docs, processor))
        
        # Should process in priority order
        assert process_order == ["doc_2", "doc_3", "doc_1"]

    @pytest.mark.asyncio
    async def test_secure_strategy(self):
        """Test security-hardened strategy."""
        strategy = SecureStrategy(enable_validation=True)
        
        docs = [
            {"id": "valid_doc", "content": "Safe content"},
            {"id": "invalid_doc", "content": "<script>alert('XSS')</script>"},
        ]
        
        async def processor(doc, **kwargs):
            return {"processed": doc["id"], "content": doc.get("content", "")}
        
        results = await strategy.process(docs, processor)
        
        # Should sanitize dangerous content
        assert len(results) == 2
        assert "<script>" not in results[1].get("content", "")


# ============================================================================
# Processor Factory Tests
# ============================================================================


class TestDocumentProcessors:
    """Test document processor factory."""

    def test_processor_factory_creation(self):
        """Test processor factory creates correct types."""
        processors = ["enhance", "generate", "review", "validate"]
        
        for processor_type in processors:
            with patch("devdocai.intelligence.enhance.EnhancementPipeline"):
                with patch("devdocai.core.generator.DocumentGenerator"):
                    with patch("devdocai.core.review.ReviewEngine"):
                        processor = DocumentProcessorFactory.create(processor_type)
                        assert processor is not None
                        assert hasattr(processor, "process")
                        assert processor.processor_type == processor_type

    def test_custom_processor_creation(self):
        """Test creating custom processor."""
        async def custom_func(doc, **kwargs):
            return {"custom": True, "id": doc.get("id")}
        
        processor = DocumentProcessorFactory.create(
            "custom",
            process_func=custom_func
        )
        
        assert processor.processor_type == "custom"

    @pytest.mark.asyncio
    async def test_validate_processor(self):
        """Test document validation processor."""
        processor = ValidateProcessor()
        
        # Valid document
        valid_doc = {
            "id": "doc_1",
            "type": "readme",
            "content": "# Title\n\n## Description\n\n## Installation\n\n## Usage"
        }
        
        result = await processor.process(valid_doc)
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        
        # Invalid document
        invalid_doc = {"id": "doc_2"}  # Missing content
        
        result = await processor.process(invalid_doc)
        assert result["valid"] is False
        assert len(result["errors"]) > 0


# ============================================================================
# Monitoring Tests
# ============================================================================


class TestBatchMonitoring:
    """Test batch monitoring and metrics."""

    @pytest.mark.asyncio
    async def test_progress_tracker(self):
        """Test progress tracking functionality."""
        tracker = ProgressTracker(total=100)
        
        # Update progress
        await tracker.update(completed=25)
        status = tracker.get_status()
        
        assert status["completed"] == 25
        assert status["percentage"] == 25.0
        
        # Update with failures
        await tracker.update(completed=25, failed=5)
        status = tracker.get_status()
        
        assert status["completed"] == 50
        assert status["failed"] == 5

    @pytest.mark.asyncio
    async def test_metrics_collector(self):
        """Test metrics collection."""
        collector = MetricsCollector()
        
        # Start monitoring
        await collector.start_monitoring(interval=0.1)
        
        # Record some metrics
        collector.record_document_time(0.5)
        collector.record_cache_hit()
        collector.record_cache_miss()
        collector.record_retry(successful=True)
        
        # Wait for resource sampling
        await asyncio.sleep(0.2)
        
        # Stop and finalize
        await collector.stop_monitoring()
        collector.finalize()
        
        metrics = collector.get_metrics()
        assert metrics.cache_hits == 1
        assert metrics.cache_misses == 1
        assert metrics.retry_success == 1

    @pytest.mark.asyncio
    async def test_batch_monitor_events(self):
        """Test batch monitor event system."""
        monitor = BatchMonitor()
        
        # Track events
        events_received = []
        
        def event_handler(event, data):
            events_received.append((event, data))
        
        # Subscribe to events
        monitor.subscribe(BatchEvent.BATCH_STARTED, event_handler)
        monitor.subscribe(BatchEvent.DOCUMENT_COMPLETED, event_handler)
        
        # Start batch
        await monitor.start_batch(10)
        
        # Process document
        await monitor.record_document_start("doc_1")
        await monitor.record_document_complete("doc_1", success=True, processing_time=0.1)
        
        # Check events
        assert len(events_received) >= 2
        assert events_received[0][0] == BatchEvent.BATCH_STARTED
        assert events_received[1][0] == BatchEvent.DOCUMENT_COMPLETED


# ============================================================================
# Integration Tests
# ============================================================================


class TestBatchOperationsManager:
    """Test integrated batch operations manager."""

    @pytest.mark.asyncio
    async def test_basic_batch_processing(self, batch_manager, sample_documents):
        """Test basic batch processing workflow."""
        result = await batch_manager.process_batch(sample_documents)
        
        assert isinstance(result, BatchResult)
        assert result.total_documents == 10
        assert result.successful > 0

    @pytest.mark.asyncio
    async def test_builder_pattern(self):
        """Test configuration builder pattern."""
        config = (
            BatchConfigBuilder()
            .with_strategy("concurrent")
            .with_processor("validate")
            .with_concurrency(8)
            .with_batch_size(20)
            .with_cache(enabled=True, ttl=7200)
            .with_monitoring(enabled=True)
            .build()
        )
        
        assert config.strategy_type == "concurrent"
        assert config.processor_type == "validate"
        assert config.max_concurrent == 8
        assert config.batch_size == 20
        assert config.cache_ttl_seconds == 7200

    @pytest.mark.asyncio
    async def test_strategy_switching(self, batch_manager):
        """Test switching strategies at runtime."""
        # Start with concurrent
        assert batch_manager.config.strategy_type == "concurrent"
        
        # Switch to streaming
        batch_manager.set_strategy("streaming", chunk_size_kb=512)
        assert batch_manager.config.strategy_type == "streaming"
        assert isinstance(batch_manager.strategy, StreamingStrategy)

    @pytest.mark.asyncio
    async def test_processor_switching(self, batch_manager):
        """Test switching processors at runtime."""
        # Start with validate
        assert batch_manager.config.processor_type == "validate"
        
        # Switch to custom
        async def custom_processor(doc, **kwargs):
            return {"custom": True}
        
        batch_manager.set_processor("custom", process_func=custom_processor)
        assert batch_manager.config.processor_type == "custom"

    @pytest.mark.asyncio
    async def test_convenience_function(self, sample_documents):
        """Test convenience processing function."""
        result = await process_documents_batch(
            sample_documents,
            strategy="priority",
            processor="validate"
        )
        
        assert isinstance(result, BatchResult)
        assert result.total_documents == 10

    def test_factory_function(self):
        """Test batch manager factory function."""
        manager = create_batch_manager(
            strategy="secure",
            processor="enhance",
            max_concurrent=16,
            enable_cache=True,
            enable_monitoring=True
        )
        
        assert isinstance(manager, BatchOperationsManager)
        assert manager.config.strategy_type == "secure"
        assert manager.config.processor_type == "enhance"
        assert manager.config.max_concurrent == 16

    @pytest.mark.asyncio
    async def test_empty_batch_handling(self, batch_manager):
        """Test handling empty document list."""
        result = await batch_manager.process_batch([])
        
        assert result.success is True
        assert result.total_documents == 0
        assert result.successful == 0
        assert result.failed == 0

    @pytest.mark.asyncio
    async def test_error_handling(self, batch_manager):
        """Test error handling in batch processing."""
        # Create documents that will fail validation
        bad_docs = [
            {},  # No id or content
            {"id": "bad_1"},  # No content
        ]
        
        result = await batch_manager.process_batch(bad_docs)
        
        assert result.total_documents == 2
        assert result.failed > 0

    @pytest.mark.asyncio
    async def test_progress_monitoring(self, batch_manager, sample_documents):
        """Test progress monitoring during processing."""
        # Start processing
        task = asyncio.create_task(
            batch_manager.process_batch(sample_documents)
        )
        
        # Check progress while processing
        await asyncio.sleep(0.01)  # Let processing start
        
        progress = batch_manager.get_progress()
        if progress:  # May be None if processing is very fast
            assert "total" in progress
            assert "completed" in progress
        
        # Wait for completion
        result = await task
        assert result.successful > 0


# ============================================================================
# Performance Tests
# ============================================================================


class TestPerformance:
    """Test performance characteristics of refactored architecture."""

    @pytest.mark.asyncio
    async def test_concurrent_performance(self):
        """Test concurrent processing performance."""
        # Create many documents
        docs = [{"id": f"doc_{i}", "content": f"content_{i}"} for i in range(100)]
        
        # Configure for high concurrency
        config = (
            BatchConfigBuilder()
            .with_strategy("concurrent")
            .with_processor("validate")
            .with_concurrency(16)
            .build()
        )
        
        manager = BatchOperationsManager(config)
        
        start = time.time()
        result = await manager.process_batch(docs)
        elapsed = time.time() - start
        
        # Should process 100 docs quickly
        assert result.successful == 100
        assert elapsed < 2.0  # Should be fast with concurrency
        
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_memory_efficiency(self):
        """Test memory-efficient streaming."""
        # Create large document
        large_content = "x" * (10 * 1024 * 1024)  # 10MB
        docs = [{"id": "large", "content": large_content}]
        
        config = (
            BatchConfigBuilder()
            .with_strategy("streaming")
            .with_processor("validate")
            .build()
        )
        
        manager = BatchOperationsManager(config)
        
        # Should handle large document without memory issues
        result = await manager.process_batch(docs)
        assert result.successful == 1
        
        await manager.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])