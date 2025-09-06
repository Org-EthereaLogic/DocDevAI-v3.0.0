"""
Comprehensive tests for M011 Batch Operations Manager.

Tests all components: BatchOperationsManager, ProcessingQueue, MemoryOptimizer, ProgressTracker.
"""

import asyncio
import gc
import pytest
import time
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from devdocai.batch import (
    BatchOperationsManager,
    ProcessingQueue,
    MemoryOptimizer,
    ProgressTracker
)
from devdocai.batch.batch_manager import BatchResult, OperationType
from devdocai.batch.processing_queue import Priority, QueueItem
from devdocai.batch.progress_tracker import OperationProgress


class TestBatchOperationsManager:
    """Test the core BatchOperationsManager class."""
    
    def test_initialization_default(self):
        """Test default initialization."""
        manager = BatchOperationsManager()
        
        assert manager.concurrency >= 1
        assert manager.concurrency <= 16
        assert manager.get_memory_mode() in ['baseline', 'standard', 'enhanced', 'performance']
        assert len(manager.operations) > 0
    
    def test_initialization_custom_concurrency(self):
        """Test initialization with custom concurrency."""
        manager = BatchOperationsManager(custom_concurrency=8)
        assert manager.concurrency == 8
        
        # Test bounds
        manager_low = BatchOperationsManager(custom_concurrency=0)
        assert manager_low.concurrency == 1
        
        manager_high = BatchOperationsManager(custom_concurrency=20)
        assert manager_high.concurrency == 16
    
    def test_memory_mode_concurrency_mapping(self):
        """Test memory mode to concurrency mapping."""
        assert BatchOperationsManager.CONCURRENCY_MAP['baseline'] == 1
        assert BatchOperationsManager.CONCURRENCY_MAP['standard'] == 4
        assert BatchOperationsManager.CONCURRENCY_MAP['enhanced'] == 8
        assert BatchOperationsManager.CONCURRENCY_MAP['performance'] == 16
    
    @pytest.mark.asyncio
    async def test_process_batch_simple(self):
        """Test simple batch processing."""
        manager = BatchOperationsManager()
        
        # Create test documents
        documents = ['doc1', 'doc2', 'doc3']
        
        # Simple test handler
        async def test_handler(doc, params):
            return {'processed': doc}
        
        # Process batch
        result = await manager.process_batch(
            documents=documents,
            operation=OperationType.CUSTOM,
            operation_params={'handler': test_handler}
        )
        
        assert isinstance(result, BatchResult)
        assert result.total_documents == 3
        assert result.processed == 3
        assert result.failed == 0
        assert result.success_rate == 100.0
    
    @pytest.mark.asyncio
    async def test_process_batch_with_failures(self):
        """Test batch processing with some failures."""
        manager = BatchOperationsManager()
        
        documents = ['doc1', 'fail', 'doc3']
        
        # Handler that fails for specific document
        async def test_handler(doc, params):
            if doc == 'fail':
                raise ValueError("Test failure")
            return {'processed': doc}
        
        result = await manager.process_batch(
            documents=documents,
            operation=OperationType.CUSTOM,
            operation_params={'handler': test_handler}
        )
        
        assert result.processed == 3  # All attempted
        assert result.failed == 1
        assert result.success_rate < 100.0
    
    @pytest.mark.asyncio
    async def test_process_batch_with_progress(self):
        """Test batch processing with progress callback."""
        manager = BatchOperationsManager()
        
        documents = ['doc1', 'doc2']
        progress_calls = []
        
        def progress_callback(current, total, result):
            progress_calls.append((current, total))
        
        async def test_handler(doc, params):
            return {'processed': doc}
        
        await manager.process_batch(
            documents=documents,
            operation=OperationType.CUSTOM,
            operation_params={'handler': test_handler},
            progress_callback=progress_callback
        )
        
        assert len(progress_calls) == 2
        assert progress_calls[-1] == (2, 2)
    
    def test_register_operation(self):
        """Test registering custom operations."""
        manager = BatchOperationsManager()
        
        def custom_op(doc, params):
            return {'custom': doc}
        
        # Register new operation
        manager.register_operation(OperationType.CUSTOM, custom_op, override=True)
        assert manager.operations[OperationType.CUSTOM] == custom_op
        
        # Test override protection
        with pytest.raises(ValueError):
            manager.register_operation(OperationType.GENERATE, custom_op, override=False)
    
    def test_statistics(self):
        """Test statistics tracking."""
        manager = BatchOperationsManager()
        
        # Initial stats
        stats = manager.get_statistics()
        assert stats['total_batches'] == 0
        assert stats['total_documents'] == 0
        
        # Reset stats
        manager.stats['total_batches'] = 5
        manager.stats['total_documents'] = 50
        manager.reset_statistics()
        
        stats = manager.get_statistics()
        assert stats['total_batches'] == 0
        assert stats['total_documents'] == 0


class TestProcessingQueue:
    """Test the ProcessingQueue class."""
    
    @pytest.mark.asyncio
    async def test_queue_initialization(self):
        """Test queue initialization."""
        queue = ProcessingQueue(max_concurrent=4, max_size=100)
        
        assert queue.max_concurrent == 4
        assert queue.max_size == 100
        assert queue.is_empty()
        assert queue.size() == 0
    
    @pytest.mark.asyncio
    async def test_add_and_get_document(self):
        """Test adding and getting documents."""
        queue = ProcessingQueue()
        
        # Add document
        doc_id = await queue.add_document("test_doc", Priority.NORMAL)
        assert doc_id is not None
        assert queue.size() == 1
        
        # Get document
        doc = await queue.get_next()
        assert doc == "test_doc"
        assert queue.size() == 0
    
    @pytest.mark.asyncio
    async def test_priority_ordering(self):
        """Test priority-based document ordering."""
        queue = ProcessingQueue()
        
        # Add documents with different priorities
        await queue.add_document("low", Priority.LOW)
        await queue.add_document("critical", Priority.CRITICAL)
        await queue.add_document("normal", Priority.NORMAL)
        await queue.add_document("high", Priority.HIGH)
        
        # Should get in priority order
        assert await queue.get_next() == "critical"
        assert await queue.get_next() == "high"
        assert await queue.get_next() == "normal"
        assert await queue.get_next() == "low"
    
    @pytest.mark.asyncio
    async def test_queue_overflow(self):
        """Test queue overflow protection."""
        queue = ProcessingQueue(max_size=2)
        
        await queue.add_document("doc1")
        await queue.add_document("doc2")
        
        with pytest.raises(OverflowError):
            await queue.add_document("doc3")
    
    @pytest.mark.asyncio
    async def test_mark_completed_and_failed(self):
        """Test marking documents as completed or failed."""
        queue = ProcessingQueue()
        
        doc_id = await queue.add_document("test_doc")
        
        # Mark as completed
        await queue.mark_completed(doc_id)
        assert doc_id in queue.completed
        
        # Mark another as failed
        doc_id2 = await queue.add_document("fail_doc")
        await queue.mark_failed(doc_id2, retry=False)
        assert doc_id2 in queue.failed
    
    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test queue statistics."""
        queue = ProcessingQueue()
        
        await queue.add_document("doc1", Priority.HIGH)
        await queue.add_document("doc2", Priority.NORMAL)
        
        stats = queue.get_stats()
        assert stats['queue_size'] == 2
        assert stats['by_priority']['HIGH'] == 1
        assert stats['by_priority']['NORMAL'] == 1
    
    @pytest.mark.asyncio
    async def test_clear_queue(self):
        """Test clearing the queue."""
        queue = ProcessingQueue()
        
        await queue.add_document("doc1")
        await queue.add_document("doc2")
        assert queue.size() == 2
        
        await queue.clear()
        assert queue.size() == 0
        assert queue.is_empty()


class TestMemoryOptimizer:
    """Test the MemoryOptimizer class."""
    
    def test_initialization(self):
        """Test memory optimizer initialization."""
        optimizer = MemoryOptimizer()
        
        assert optimizer.memory_mode in ['baseline', 'standard', 'enhanced', 'performance']
        assert optimizer._gc_threshold == 100 * 1024 * 1024
    
    def test_get_memory_status(self):
        """Test getting memory status."""
        optimizer = MemoryOptimizer()
        status = optimizer.get_memory_status()
        
        assert 'total' in status
        assert 'available' in status
        assert 'used' in status
        assert 'percent' in status
        assert 'process_memory' in status
        assert status['percent'] >= 0
        assert status['percent'] <= 100
    
    def test_detect_memory_mode(self):
        """Test memory mode detection."""
        optimizer = MemoryOptimizer()
        mode = optimizer.detect_memory_mode()
        
        assert mode in ['baseline', 'standard', 'enhanced', 'performance']
    
    def test_get_recommended_batch_size(self):
        """Test batch size recommendations."""
        optimizer = MemoryOptimizer()
        batch_size = optimizer.get_recommended_batch_size()
        
        assert batch_size > 0
        assert batch_size <= 1000
    
    def test_get_memory_pressure(self):
        """Test memory pressure detection."""
        optimizer = MemoryOptimizer()
        pressure = optimizer.get_memory_pressure()
        
        assert pressure in ['low', 'medium', 'high', 'critical']
    
    def test_should_throttle(self):
        """Test throttling decision."""
        optimizer = MemoryOptimizer()
        should_throttle = optimizer.should_throttle()
        
        assert isinstance(should_throttle, bool)
    
    def test_get_optimization_strategy(self):
        """Test optimization strategy generation."""
        optimizer = MemoryOptimizer()
        strategy = optimizer.get_optimization_strategy()
        
        assert 'mode' in strategy
        assert 'pressure' in strategy
        assert 'batch_size' in strategy
        assert 'gc_frequency' in strategy
        assert 'throttle' in strategy
        assert 'cache_size' in strategy
    
    def test_optimize_memory(self):
        """Test memory optimization."""
        optimizer = MemoryOptimizer()
        
        # Force optimization
        optimized = optimizer.optimize_memory(force=True)
        assert optimized is True
        
        # Non-forced optimization (may or may not trigger)
        optimized = optimizer.optimize_memory(force=False)
        assert isinstance(optimized, bool)
    
    def test_cleanup(self):
        """Test memory cleanup."""
        optimizer = MemoryOptimizer()
        
        # Should not raise any errors
        optimizer.cleanup()


class TestProgressTracker:
    """Test the ProgressTracker class."""
    
    def test_initialization(self):
        """Test progress tracker initialization."""
        tracker = ProgressTracker()
        
        assert len(tracker.operations) == 0
        assert len(tracker.completed_operations) == 0
    
    def test_start_operation(self):
        """Test starting an operation."""
        tracker = ProgressTracker()
        
        progress = tracker.start_operation("op1", 100)
        
        assert progress.operation_id == "op1"
        assert progress.total_items == 100
        assert progress.processed_items == 0
        assert progress.status == "running"
    
    def test_update_progress(self):
        """Test updating progress."""
        tracker = ProgressTracker()
        
        tracker.start_operation("op1", 100)
        
        # Update with absolute value
        progress = tracker.update_progress("op1", processed=50)
        assert progress.processed_items == 50
        
        # Update with increment
        progress = tracker.update_progress("op1", increment=10)
        assert progress.processed_items == 60
        
        # Update with error
        tracker.update_progress("op1", error="Test error")
        progress = tracker.get_progress("op1")
        assert len(progress.errors) == 1
    
    def test_complete_operation(self):
        """Test completing an operation."""
        tracker = ProgressTracker()
        
        tracker.start_operation("op1", 100)
        tracker.update_progress("op1", processed=100)
        
        progress = tracker.complete_operation("op1")
        
        assert progress.status == "completed"
        assert progress.end_time is not None
        assert "op1" not in tracker.operations
        assert len(tracker.completed_operations) == 1
    
    def test_operation_progress_properties(self):
        """Test OperationProgress properties."""
        progress = OperationProgress("op1", 100)
        progress.processed_items = 50
        
        assert progress.progress_percent == 50.0
        assert progress.elapsed_time > 0
        assert progress.throughput > 0
        
        # Test progress bar
        bar = progress.format_progress_bar(width=10)
        assert '█' in bar
        assert '░' in bar
    
    def test_get_summary(self):
        """Test getting summary statistics."""
        tracker = ProgressTracker()
        
        tracker.start_operation("op1", 100)
        tracker.update_progress("op1", processed=50)
        
        summary = tracker.get_summary()
        
        assert summary['active_operations'] == 1
        assert summary['completed_operations'] == 0
        assert 'average_progress' in summary
        assert 'total_throughput' in summary
    
    def test_format_report(self):
        """Test formatting progress report."""
        tracker = ProgressTracker()
        
        tracker.start_operation("op1", 100)
        tracker.update_progress("op1", processed=50)
        
        # Report for specific operation
        report = tracker.format_report("op1")
        assert "op1" in report
        assert "50/100" in report
        
        # Report for all operations
        report = tracker.format_report()
        assert "Active Operations" in report
    
    def test_clear_completed(self):
        """Test clearing completed operations."""
        tracker = ProgressTracker()
        
        tracker.start_operation("op1", 100)
        tracker.complete_operation("op1")
        
        assert len(tracker.completed_operations) == 1
        
        tracker.clear_completed()
        assert len(tracker.completed_operations) == 0


class TestIntegration:
    """Integration tests for the batch operations system."""
    
    @pytest.mark.asyncio
    async def test_full_batch_workflow(self):
        """Test complete batch processing workflow."""
        manager = BatchOperationsManager(custom_concurrency=2)
        
        # Create test documents
        documents = [f"doc_{i}" for i in range(5)]
        
        # Handler with artificial delay
        async def slow_handler(doc, params):
            await asyncio.sleep(0.01)
            return {'result': f"Processed {doc}"}
        
        # Process batch with progress tracking
        result = await manager.process_batch(
            documents=documents,
            operation=OperationType.CUSTOM,
            operation_params={'handler': slow_handler}
        )
        
        # Verify results
        assert result.total_documents == 5
        assert result.processed == 5
        assert result.failed == 0
        assert result.elapsed_time > 0
        assert result.throughput > 0
        
        # Check statistics
        stats = manager.get_statistics()
        assert stats['total_batches'] == 1
        assert stats['total_documents'] == 5
    
    @pytest.mark.asyncio
    async def test_memory_management_during_batch(self):
        """Test memory management during batch processing."""
        # Mock config for baseline mode
        mock_config = Mock()
        mock_config.get.return_value = 'baseline'
        
        manager = BatchOperationsManager(config_manager=mock_config)
        assert manager.concurrency == 1  # Baseline mode
        
        # Process batch
        documents = [f"doc_{i}" for i in range(15)]
        
        async def handler(doc, params):
            return {'processed': doc}
        
        with patch.object(manager, '_manage_memory') as mock_manage:
            result = await manager.process_batch(
                documents=documents,
                operation=OperationType.CUSTOM,
                operation_params={'handler': handler}
            )
            
            # Memory management should have been called
            assert mock_manage.called
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test running multiple batch operations concurrently."""
        manager = BatchOperationsManager(custom_concurrency=4)
        
        async def handler(doc, params):
            await asyncio.sleep(0.01)
            return {'processed': doc}
        
        # Start multiple batch operations
        tasks = []
        for batch_id in range(3):
            documents = [f"batch{batch_id}_doc{i}" for i in range(3)]
            task = manager.process_batch(
                documents=documents,
                operation=OperationType.CUSTOM,
                operation_params={'handler': handler}
            )
            tasks.append(task)
        
        # Wait for all to complete
        results = await asyncio.gather(*tasks)
        
        # Verify all completed successfully
        for result in results:
            assert result.processed == 3
            assert result.failed == 0
        
        # Check cumulative statistics
        stats = manager.get_statistics()
        assert stats['total_batches'] == 3
        assert stats['total_documents'] == 9


if __name__ == '__main__':
    pytest.main([__file__, '-v'])