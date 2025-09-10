"""
Test Suite for M011 Batch Operations Manager
DevDocAI v3.0.0 - Pass 1: Core Implementation
Enhanced 4-Pass TDD - Test-First Development
"""

import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Module under test
from devdocai.operations.batch import (
    BatchConfig,
    BatchError,
    BatchOperation,
    BatchOperationsManager,
    BatchResult,
    BatchStatus,
    DocumentBatch,
    ProcessingQueue,
    ProgressTracker,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_config():
    """Mock configuration manager."""
    config = MagicMock()
    config.system.memory_mode = "standard"
    config.system.max_workers = 4
    config.get.return_value = "standard"
    return config


@pytest.fixture
def mock_storage():
    """Mock storage manager."""
    storage = MagicMock()
    storage.save_document = AsyncMock(return_value=True)
    storage.get_document = AsyncMock(return_value={"id": "test", "content": "test content"})
    return storage


@pytest.fixture
def mock_enhancement_pipeline():
    """Mock enhancement pipeline."""
    from devdocai.intelligence.enhance import EnhancementResult

    pipeline = MagicMock()
    result = EnhancementResult(
        success=True,
        original_content="original",
        enhanced_content="enhanced",
        strategy_used="combined",
        quality_improvement=65.0,
    )
    pipeline.enhance_document = AsyncMock(return_value=result)
    return pipeline


@pytest.fixture
def sample_documents():
    """Sample documents for testing."""
    return [
        {"id": f"doc_{i}", "content": f"Test content {i}", "type": "readme"}
        for i in range(10)
    ]


@pytest.fixture
async def batch_manager(mock_config):
    """Initialize batch operations manager."""
    with patch("devdocai.operations.batch.ConfigurationManager", return_value=mock_config):
        manager = BatchOperationsManager()
        yield manager
        # Cleanup
        await manager.shutdown()


# ============================================================================
# Test BatchConfig
# ============================================================================


class TestBatchConfig:
    """Test batch configuration."""

    def test_default_config(self):
        """Test default batch configuration."""
        config = BatchConfig()
        assert config.memory_mode == "auto"
        assert config.max_concurrent == 4
        assert config.batch_size == 10
        assert config.enable_progress is True
        assert config.timeout_seconds == 300
        assert config.retry_attempts == 3

    def test_memory_mode_concurrency(self):
        """Test memory mode based concurrency."""
        # Baseline mode
        config = BatchConfig(memory_mode="baseline")
        assert config.get_concurrency() == 1

        # Standard mode
        config = BatchConfig(memory_mode="standard")
        assert config.get_concurrency() == 4

        # Enhanced mode
        config = BatchConfig(memory_mode="enhanced")
        assert config.get_concurrency() == 8

        # Performance mode
        config = BatchConfig(memory_mode="performance")
        assert config.get_concurrency() == 16

    def test_custom_config(self):
        """Test custom batch configuration."""
        config = BatchConfig(
            memory_mode="enhanced",
            max_concurrent=12,
            batch_size=20,
            enable_progress=False,
        )
        assert config.memory_mode == "enhanced"
        assert config.max_concurrent == 12
        assert config.batch_size == 20
        assert config.enable_progress is False


# ============================================================================
# Test ProcessingQueue
# ============================================================================


class TestProcessingQueue:
    """Test document processing queue."""

    @pytest.mark.asyncio
    async def test_queue_operations(self):
        """Test queue add/get operations."""
        queue = ProcessingQueue()

        # Add documents
        docs = [{"id": f"doc_{i}"} for i in range(5)]
        for doc in docs:
            await queue.add(doc)

        assert queue.size() == 5
        assert not queue.is_empty()

        # Get documents
        retrieved = []
        while not queue.is_empty():
            doc = await queue.get()
            retrieved.append(doc)

        assert len(retrieved) == 5
        assert queue.is_empty()

    @pytest.mark.asyncio
    async def test_batch_operations(self):
        """Test batch queue operations."""
        queue = ProcessingQueue()

        # Add batch
        docs = [{"id": f"doc_{i}"} for i in range(10)]
        await queue.add_batch(docs)
        assert queue.size() == 10

        # Get batch
        batch = await queue.get_batch(5)
        assert len(batch) == 5
        assert queue.size() == 5

        # Get remaining
        batch = await queue.get_batch(10)
        assert len(batch) == 5
        assert queue.is_empty()

    @pytest.mark.asyncio
    async def test_priority_queue(self):
        """Test priority queue operations."""
        queue = ProcessingQueue()

        # Add documents with priority
        await queue.add({"id": "low", "priority": 3})
        await queue.add({"id": "high", "priority": 1})
        await queue.add({"id": "medium", "priority": 2})

        # Should get in priority order
        doc1 = await queue.get()
        doc2 = await queue.get()
        doc3 = await queue.get()

        assert doc1["id"] == "high"
        assert doc2["id"] == "medium"
        assert doc3["id"] == "low"

    @pytest.mark.asyncio
    async def test_queue_clear(self):
        """Test queue clearing."""
        queue = ProcessingQueue()

        # Add documents
        docs = [{"id": f"doc_{i}"} for i in range(5)]
        await queue.add_batch(docs)
        assert queue.size() == 5

        # Clear queue
        await queue.clear()
        assert queue.is_empty()


# ============================================================================
# Test ProgressTracker
# ============================================================================


class TestProgressTracker:
    """Test progress tracking."""

    def test_progress_initialization(self):
        """Test progress tracker initialization."""
        tracker = ProgressTracker(total=100)
        assert tracker.total == 100
        assert tracker.completed == 0
        assert tracker.failed == 0
        assert tracker.get_percentage() == 0.0

    def test_progress_updates(self):
        """Test progress update operations."""
        tracker = ProgressTracker(total=10)

        # Update progress
        tracker.update(3)
        assert tracker.completed == 3
        assert tracker.get_percentage() == 30.0

        # Update with failures
        tracker.update(2, failed=1)
        assert tracker.completed == 5
        assert tracker.failed == 1
        assert tracker.get_percentage() == 50.0

    def test_progress_status(self):
        """Test progress status reporting."""
        tracker = ProgressTracker(total=10)
        tracker.update(5, failed=1)

        status = tracker.get_status()
        assert status["total"] == 10
        assert status["completed"] == 5
        assert status["failed"] == 1
        assert status["percentage"] == 50.0
        assert status["success_rate"] == 80.0  # 4 successful out of 5

    def test_progress_eta(self):
        """Test estimated time remaining."""
        tracker = ProgressTracker(total=100)

        # Simulate progress over time
        tracker.update(10)
        time.sleep(0.1)  # Simulate processing time

        eta = tracker.get_eta()
        assert eta is not None
        assert eta > 0  # Should have positive ETA

    def test_progress_reset(self):
        """Test progress reset."""
        tracker = ProgressTracker(total=10)
        tracker.update(5, failed=2)

        tracker.reset(total=20)
        assert tracker.total == 20
        assert tracker.completed == 0
        assert tracker.failed == 0


# ============================================================================
# Test BatchOperationsManager
# ============================================================================


class TestBatchOperationsManager:
    """Test batch operations manager."""

    @pytest.mark.asyncio
    async def test_manager_initialization(self, mock_config):
        """Test manager initialization."""
        with patch("devdocai.operations.batch.ConfigurationManager", return_value=mock_config):
            manager = BatchOperationsManager()

            assert manager.memory_mode == "standard"
            assert manager.max_concurrent == 4
            assert manager.queue is not None
            assert manager.progress is not None

            await manager.shutdown()

    @pytest.mark.asyncio
    async def test_memory_mode_detection(self, mock_config):
        """Test memory mode auto-detection."""
        # Test different memory modes
        memory_modes = ["baseline", "standard", "enhanced", "performance"]
        expected_concurrency = [1, 4, 8, 16]

        for mode, expected in zip(memory_modes, expected_concurrency):
            mock_config.system.memory_mode = mode
            with patch("devdocai.operations.batch.ConfigurationManager", return_value=mock_config):
                manager = BatchOperationsManager()
                assert manager.memory_mode == mode
                assert manager.max_concurrent == expected
                await manager.shutdown()

    @pytest.mark.asyncio
    async def test_process_single_document(self, batch_manager, mock_enhancement_pipeline):
        """Test processing single document."""
        document = {"id": "test_doc", "content": "Test content"}

        with patch.object(batch_manager, "_get_operation", return_value=mock_enhancement_pipeline.enhance_document):
            result = await batch_manager.process_document(document, "enhance")

            assert result.success is True
            assert result.document_id == "test_doc"
            assert result.operation == "enhance"

    @pytest.mark.asyncio
    async def test_process_batch_simple(self, batch_manager, sample_documents):
        """Test simple batch processing."""
        # Mock operation
        async def mock_operation(doc):
            return {"success": True, "processed": doc["id"]}

        results = await batch_manager.process_batch(
            documents=sample_documents,
            operation=mock_operation,
        )

        assert len(results) == 10
        assert all(r.success for r in results)
        assert batch_manager.progress.completed == 10

    @pytest.mark.asyncio
    async def test_process_batch_with_failures(self, batch_manager, sample_documents):
        """Test batch processing with failures."""
        # Mock operation that fails for some documents
        async def mock_operation(doc):
            if int(doc["id"].split("_")[1]) % 3 == 0:
                raise ValueError("Test error")
            return {"success": True, "processed": doc["id"]}

        results = await batch_manager.process_batch(
            documents=sample_documents,
            operation=mock_operation,
        )

        assert len(results) == 10
        success_count = sum(1 for r in results if r.success)
        failure_count = sum(1 for r in results if not r.success)
        assert success_count == 6  # 10 - 4 failures (0, 3, 6, 9 % 3 == 0)
        assert failure_count == 4

    @pytest.mark.asyncio
    async def test_concurrent_processing(self, batch_manager, sample_documents):
        """Test concurrent batch processing."""
        processing_times = []

        async def mock_operation(doc):
            start = time.time()
            await asyncio.sleep(0.1)  # Simulate processing
            processing_times.append(time.time() - start)
            return {"success": True, "processed": doc["id"]}

        start_time = time.time()
        results = await batch_manager.process_batch(
            documents=sample_documents,
            operation=mock_operation,
        )
        total_time = time.time() - start_time

        assert len(results) == 10
        # With concurrency=4, should take ~0.3s not 1.0s
        assert total_time < 0.5  # Allow some overhead

    @pytest.mark.asyncio
    async def test_memory_aware_batching(self, batch_manager):
        """Test memory-aware document batching."""
        # Create large document set
        large_docs = [{"id": f"doc_{i}", "content": "x" * 1000} for i in range(100)]

        batch_manager.config.batch_size = 10
        batches = batch_manager._create_batches(large_docs)

        # Should create 10 batches of 10 documents
        assert len(batches) == 10
        assert all(len(batch.documents) == 10 for batch in batches)

    @pytest.mark.asyncio
    async def test_progress_tracking(self, batch_manager, sample_documents):
        """Test real-time progress tracking."""
        progress_updates = []

        async def mock_operation(doc):
            await asyncio.sleep(0.01)
            # Capture progress
            progress_updates.append(batch_manager.progress.get_percentage())
            return {"success": True}

        await batch_manager.process_batch(
            documents=sample_documents,
            operation=mock_operation,
        )

        # Should have progress updates
        assert len(progress_updates) > 0
        assert batch_manager.progress.completed == 10
        assert batch_manager.progress.get_percentage() == 100.0

    @pytest.mark.asyncio
    async def test_batch_with_timeout(self, batch_manager):
        """Test batch processing with timeout."""
        async def slow_operation(doc):
            await asyncio.sleep(10)  # Very slow
            return {"success": True}

        batch_manager.config.timeout_seconds = 0.5

        results = await batch_manager.process_batch(
            documents=[{"id": "test"}],
            operation=slow_operation,
        )

        assert len(results) == 1
        assert results[0].success is False
        assert "timeout" in results[0].error.lower()

    @pytest.mark.asyncio
    async def test_retry_mechanism(self, batch_manager):
        """Test retry mechanism for failed operations."""
        attempt_count = {}

        async def flaky_operation(doc):
            doc_id = doc["id"]
            attempt_count[doc_id] = attempt_count.get(doc_id, 0) + 1

            # Fail first attempt, succeed on retry
            if attempt_count[doc_id] == 1:
                raise ValueError("Temporary error")
            return {"success": True}

        batch_manager.config.retry_attempts = 3

        results = await batch_manager.process_batch(
            documents=[{"id": "test"}],
            operation=flaky_operation,
        )

        assert results[0].success is True
        assert attempt_count["test"] == 2  # Failed once, succeeded on retry

    @pytest.mark.asyncio
    async def test_batch_result_aggregation(self, batch_manager, sample_documents):
        """Test batch result aggregation."""
        async def mock_operation(doc):
            return {"success": True, "tokens": 100}

        results = await batch_manager.process_batch(
            documents=sample_documents,
            operation=mock_operation,
        )

        # Get aggregated metrics
        metrics = batch_manager.get_batch_metrics(results)

        assert metrics["total_documents"] == 10
        assert metrics["successful"] == 10
        assert metrics["failed"] == 0
        assert metrics["success_rate"] == 100.0

    @pytest.mark.asyncio
    async def test_pipeline_integration(self, batch_manager, mock_enhancement_pipeline):
        """Test integration with enhancement pipeline."""
        documents = [{"id": f"doc_{i}", "content": f"Content {i}"} for i in range(5)]

        with patch("devdocai.operations.batch.EnhancementPipeline", return_value=mock_enhancement_pipeline):
            results = await batch_manager.enhance_batch(documents)

            assert len(results) == 5
            assert all(r.success for r in results)
            assert all(r.operation == "enhance" for r in results)

    @pytest.mark.asyncio
    async def test_shutdown_cleanup(self, batch_manager):
        """Test proper shutdown and cleanup."""
        # Add documents to queue
        await batch_manager.queue.add_batch([{"id": f"doc_{i}"} for i in range(5)])

        # Shutdown should clear queue
        await batch_manager.shutdown()

        assert batch_manager.queue.is_empty()
        assert batch_manager._executor is None

    @pytest.mark.asyncio
    async def test_performance_targets(self, batch_manager):
        """Test performance targets for different memory modes."""
        performance_targets = {
            "baseline": 50,  # docs/hr
            "standard": 100,
            "enhanced": 200,
            "performance": 500,
        }

        for mode, target_per_hour in performance_targets.items():
            batch_manager.memory_mode = mode
            batch_manager.max_concurrent = batch_manager.config.get_concurrency_for_mode(mode)

            # Simulate processing
            docs_per_second = target_per_hour / 3600
            processing_time = 1 / docs_per_second  # Time per document

            # Verify concurrency allows target throughput
            theoretical_throughput = batch_manager.max_concurrent / processing_time
            hourly_throughput = theoretical_throughput * 3600

            assert hourly_throughput >= target_per_hour


# ============================================================================
# Test Error Handling
# ============================================================================


class TestErrorHandling:
    """Test error handling in batch operations."""

    @pytest.mark.asyncio
    async def test_invalid_operation(self, batch_manager):
        """Test handling of invalid operations."""
        with pytest.raises(BatchError) as exc_info:
            await batch_manager.process_batch(
                documents=[{"id": "test"}],
                operation="invalid_operation",  # String instead of callable
            )
        assert "Invalid operation" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_empty_batch(self, batch_manager):
        """Test handling of empty batch."""
        results = await batch_manager.process_batch(
            documents=[],
            operation=lambda doc: {"success": True},
        )
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_malformed_documents(self, batch_manager):
        """Test handling of malformed documents."""
        malformed_docs = [
            {"id": "valid", "content": "test"},
            {"missing_id": "test"},  # Missing 'id' field
            None,  # None document
            {"id": ""},  # Empty ID
        ]

        async def mock_operation(doc):
            return {"success": True}

        results = await batch_manager.process_batch(
            documents=malformed_docs,
            operation=mock_operation,
        )

        # Should handle gracefully
        assert len(results) == 4
        success_count = sum(1 for r in results if r.success)
        assert success_count == 1  # Only the valid document

    @pytest.mark.asyncio
    async def test_memory_limit_exceeded(self, batch_manager):
        """Test handling of memory limit exceeded."""
        # Create documents that exceed memory limit
        huge_docs = [{"id": f"doc_{i}", "content": "x" * 10_000_000} for i in range(100)]

        batch_manager.config.memory_limit_mb = 10  # Very low limit

        with pytest.raises(BatchError) as exc_info:
            await batch_manager.process_batch(
                documents=huge_docs,
                operation=lambda doc: {"success": True},
            )
        assert "Memory limit" in str(exc_info.value)


# ============================================================================
# Test Convenience Functions
# ============================================================================


class TestConvenienceFunctions:
    """Test convenience functions."""

    @pytest.mark.asyncio
    async def test_process_documents_batch(self, sample_documents):
        """Test convenience batch processing function."""
        from devdocai.operations.batch import process_documents_batch

        async def mock_operation(doc):
            return {"processed": doc["id"]}

        results = await process_documents_batch(
            documents=sample_documents,
            operation=mock_operation,
        )

        assert len(results) == 10
        assert all(r.success for r in results)

    def test_estimate_processing_time(self):
        """Test processing time estimation."""
        from devdocai.operations.batch import estimate_processing_time

        # Test for different memory modes
        time_baseline = estimate_processing_time(100, "baseline")
        time_standard = estimate_processing_time(100, "standard")
        time_enhanced = estimate_processing_time(100, "enhanced")
        time_performance = estimate_processing_time(100, "performance")

        # Baseline should take longest
        assert time_baseline > time_standard > time_enhanced > time_performance

        # Verify specific targets
        assert abs(time_baseline - 7200) < 1  # 100 docs at 50/hr = 2 hours
        assert abs(time_standard - 3600) < 1  # 100 docs at 100/hr = 1 hour
        assert abs(time_enhanced - 1800) < 1  # 100 docs at 200/hr = 0.5 hour
        assert abs(time_performance - 720) < 1  # 100 docs at 500/hr = 0.2 hour


# ============================================================================
# Test Data Classes
# ============================================================================


class TestDataClasses:
    """Test data classes and enums."""

    def test_batch_status_enum(self):
        """Test BatchStatus enum."""
        from devdocai.operations.batch import BatchStatus

        assert BatchStatus.PENDING.value == "pending"
        assert BatchStatus.PROCESSING.value == "processing"
        assert BatchStatus.COMPLETED.value == "completed"
        assert BatchStatus.FAILED.value == "failed"
        assert BatchStatus.PARTIAL.value == "partial"

    def test_batch_operation_enum(self):
        """Test BatchOperation enum."""
        from devdocai.operations.batch import BatchOperation

        assert BatchOperation.ENHANCE.value == "enhance"
        assert BatchOperation.GENERATE.value == "generate"
        assert BatchOperation.REVIEW.value == "review"
        assert BatchOperation.VALIDATE.value == "validate"
        assert BatchOperation.CUSTOM.value == "custom"

    def test_batch_result(self):
        """Test BatchResult dataclass."""
        from devdocai.operations.batch import BatchResult

        result = BatchResult(
            success=True,
            document_id="test_doc",
            operation="enhance",
            result={"enhanced": "content"},
            processing_time=1.5,
        )

        assert result.success is True
        assert result.document_id == "test_doc"
        assert result.operation == "enhance"
        assert result.processing_time == 1.5

    def test_document_batch(self):
        """Test DocumentBatch dataclass."""
        from devdocai.operations.batch import DocumentBatch

        batch = DocumentBatch(
            batch_id="batch_001",
            documents=[{"id": "doc1"}, {"id": "doc2"}],
            priority=1,
        )

        assert batch.batch_id == "batch_001"
        assert batch.size() == 2
        assert batch.priority == 1


# ============================================================================
# Test Integration Methods
# ============================================================================


class TestIntegrationMethods:
    """Test integration-ready methods."""

    @pytest.mark.asyncio
    async def test_enhance_batch_shortcut(self, batch_manager):
        """Test enhance_batch convenience method."""
        documents = [{"id": f"doc_{i}", "content": f"Content {i}"} for i in range(3)]

        # Mock the enhancement pipeline
        with patch.object(batch_manager, "_enhance_document") as mock_enhance:
            mock_enhance.return_value = {"enhanced": "content", "improvement": 65.0}

            results = await batch_manager.enhance_batch(documents)

            assert len(results) == 3
            assert all(r.operation == "enhance" for r in results)

    @pytest.mark.asyncio
    async def test_builtin_operations(self, batch_manager):
        """Test built-in operation functions."""
        # Test validate operation
        valid_doc = {"id": "test", "content": "test content"}
        result = await batch_manager._validate_document(valid_doc)
        assert result["valid"] is True

        invalid_doc = {"id": "test"}  # Missing content
        result = await batch_manager._validate_document(invalid_doc)
        assert result["valid"] is False

        # Test generate operation (placeholder)
        doc = {"id": "test"}
        result = await batch_manager._generate_document(doc)
        assert "generated" in result

        # Test review operation (placeholder)
        result = await batch_manager._review_document(doc)
        assert "review" in result


# ============================================================================
# Test Performance Characteristics
# ============================================================================


class TestPerformanceCharacteristics:
    """Test performance characteristics for different modes."""

    @pytest.mark.asyncio
    async def test_concurrency_scaling(self):
        """Test that concurrency scales with memory mode."""
        from devdocai.operations.batch import CONCURRENCY_MAP

        # Verify concurrency mapping
        assert CONCURRENCY_MAP["baseline"] == 1
        assert CONCURRENCY_MAP["standard"] == 4
        assert CONCURRENCY_MAP["enhanced"] == 8
        assert CONCURRENCY_MAP["performance"] == 16

        # Each level should be 2x or 4x the previous
        assert CONCURRENCY_MAP["standard"] == 4 * CONCURRENCY_MAP["baseline"]
        assert CONCURRENCY_MAP["enhanced"] == 2 * CONCURRENCY_MAP["standard"]
        assert CONCURRENCY_MAP["performance"] == 2 * CONCURRENCY_MAP["enhanced"]

    @pytest.mark.asyncio
    async def test_performance_targets(self):
        """Test performance targets are achievable."""
        from devdocai.operations.batch import PERFORMANCE_TARGETS

        # Verify target mapping
        assert PERFORMANCE_TARGETS["baseline"] == 50
        assert PERFORMANCE_TARGETS["standard"] == 100
        assert PERFORMANCE_TARGETS["enhanced"] == 200
        assert PERFORMANCE_TARGETS["performance"] == 500

        # Each level should approximately double
        assert PERFORMANCE_TARGETS["standard"] == 2 * PERFORMANCE_TARGETS["baseline"]
        assert PERFORMANCE_TARGETS["enhanced"] == 2 * PERFORMANCE_TARGETS["standard"]


# ============================================================================
# Run Tests
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])