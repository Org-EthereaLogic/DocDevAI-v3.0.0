"""
Progress Tracker for Batch Operations

Provides real-time progress tracking and reporting.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class OperationProgress:
    """Progress information for a single operation."""
    operation_id: str
    total_items: int
    processed_items: int = 0
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    status: str = "running"
    errors: List[str] = field(default_factory=list)
    
    @property
    def progress_percent(self) -> float:
        """Get progress percentage."""
        if self.total_items == 0:
            return 0.0
        return (self.processed_items / self.total_items) * 100
    
    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        end = self.end_time or time.time()
        return end - self.start_time
    
    @property
    def estimated_remaining(self) -> Optional[float]:
        """Estimate remaining time in seconds."""
        if self.processed_items == 0:
            return None
        
        rate = self.processed_items / self.elapsed_time
        remaining_items = self.total_items - self.processed_items
        
        if rate > 0:
            return remaining_items / rate
        return None
    
    @property
    def throughput(self) -> float:
        """Calculate items per second."""
        if self.elapsed_time == 0:
            return 0.0
        return self.processed_items / self.elapsed_time
    
    def format_eta(self) -> str:
        """Format estimated time of arrival."""
        remaining = self.estimated_remaining
        if remaining is None:
            return "Unknown"
        
        eta = datetime.now() + timedelta(seconds=remaining)
        return eta.strftime("%H:%M:%S")
    
    def format_progress_bar(self, width: int = 30) -> str:
        """Generate a text progress bar."""
        percent = self.progress_percent / 100
        filled = int(width * percent)
        bar = '█' * filled + '░' * (width - filled)
        return f"[{bar}] {self.progress_percent:.1f}%"


class ProgressTracker:
    """
    Track and report progress for batch operations.
    
    Features:
    - Multiple concurrent operation tracking
    - Real-time progress updates
    - ETA calculation
    - Progress bar generation
    - Performance metrics
    """
    
    def __init__(self):
        """Initialize progress tracker."""
        self.operations: Dict[str, OperationProgress] = {}
        self.completed_operations: List[OperationProgress] = []
    
    def start_operation(self, operation_id: str, total_items: int) -> OperationProgress:
        """
        Start tracking a new operation.
        
        Args:
            operation_id: Unique operation identifier
            total_items: Total number of items to process
            
        Returns:
            OperationProgress object
        """
        progress = OperationProgress(
            operation_id=operation_id,
            total_items=total_items
        )
        
        self.operations[operation_id] = progress
        logger.info(f"Started tracking operation {operation_id} with {total_items} items")
        
        return progress
    
    def update_progress(
        self,
        operation_id: str,
        processed: Optional[int] = None,
        increment: int = 1,
        error: Optional[str] = None
    ) -> Optional[OperationProgress]:
        """
        Update progress for an operation.
        
        Args:
            operation_id: Operation identifier
            processed: Absolute number of processed items
            increment: Number of items to increment by
            error: Error message to record
            
        Returns:
            Updated OperationProgress or None if not found
        """
        if operation_id not in self.operations:
            logger.warning(f"Operation {operation_id} not found")
            return None
        
        progress = self.operations[operation_id]
        
        # Update processed count
        if processed is not None:
            progress.processed_items = min(processed, progress.total_items)
        else:
            progress.processed_items = min(
                progress.processed_items + increment,
                progress.total_items
            )
        
        # Record error if provided
        if error:
            progress.errors.append(error)
        
        # Check if completed
        if progress.processed_items >= progress.total_items:
            progress.status = "completed"
        
        return progress
    
    def complete_operation(
        self,
        operation_id: str,
        status: str = "completed"
    ) -> Optional[OperationProgress]:
        """
        Mark an operation as complete.
        
        Args:
            operation_id: Operation identifier
            status: Final status ('completed', 'failed', 'cancelled')
            
        Returns:
            Final OperationProgress or None if not found
        """
        if operation_id not in self.operations:
            logger.warning(f"Operation {operation_id} not found")
            return None
        
        progress = self.operations[operation_id]
        progress.end_time = time.time()
        progress.status = status
        
        # Move to completed list
        self.completed_operations.append(progress)
        del self.operations[operation_id]
        
        logger.info(
            f"Completed operation {operation_id}: "
            f"{progress.processed_items}/{progress.total_items} items in "
            f"{progress.elapsed_time:.1f}s ({progress.throughput:.1f} items/s)"
        )
        
        return progress
    
    def get_progress(self, operation_id: str) -> Optional[OperationProgress]:
        """Get progress for a specific operation."""
        return self.operations.get(operation_id)
    
    def get_all_active(self) -> Dict[str, OperationProgress]:
        """Get all active operations."""
        return self.operations.copy()
    
    def get_summary(self) -> Dict[str, any]:
        """
        Get summary of all operations.
        
        Returns:
            Dictionary with summary statistics
        """
        active_ops = list(self.operations.values())
        completed_ops = self.completed_operations
        
        total_active = len(active_ops)
        total_completed = len(completed_ops)
        
        # Calculate aggregate statistics
        if active_ops:
            avg_progress = sum(op.progress_percent for op in active_ops) / total_active
            total_throughput = sum(op.throughput for op in active_ops)
        else:
            avg_progress = 0.0
            total_throughput = 0.0
        
        # Completed operation stats
        if completed_ops:
            avg_completion_time = sum(op.elapsed_time for op in completed_ops) / total_completed
            success_rate = sum(1 for op in completed_ops if op.status == "completed") / total_completed * 100
        else:
            avg_completion_time = 0.0
            success_rate = 0.0
        
        return {
            'active_operations': total_active,
            'completed_operations': total_completed,
            'average_progress': avg_progress,
            'total_throughput': total_throughput,
            'average_completion_time': avg_completion_time,
            'success_rate': success_rate,
            'operations': {
                op_id: {
                    'progress': op.progress_percent,
                    'throughput': op.throughput,
                    'eta': op.format_eta(),
                    'status': op.status
                }
                for op_id, op in self.operations.items()
            }
        }
    
    def format_report(self, operation_id: Optional[str] = None) -> str:
        """
        Generate a formatted progress report.
        
        Args:
            operation_id: Specific operation or None for all
            
        Returns:
            Formatted progress report string
        """
        lines = []
        
        if operation_id:
            # Report for specific operation
            progress = self.get_progress(operation_id)
            if not progress:
                return f"Operation {operation_id} not found"
            
            lines.append(f"Operation: {operation_id}")
            lines.append(f"Status: {progress.status}")
            lines.append(f"Progress: {progress.format_progress_bar()}")
            lines.append(f"Items: {progress.processed_items}/{progress.total_items}")
            lines.append(f"Throughput: {progress.throughput:.1f} items/s")
            lines.append(f"Elapsed: {progress.elapsed_time:.1f}s")
            
            if progress.estimated_remaining:
                lines.append(f"ETA: {progress.format_eta()}")
            
            if progress.errors:
                lines.append(f"Errors: {len(progress.errors)}")
        
        else:
            # Report for all operations
            lines.append("Batch Operations Progress Report")
            lines.append("=" * 50)
            
            if self.operations:
                lines.append("\nActive Operations:")
                for op_id, progress in self.operations.items():
                    lines.append(f"\n  {op_id}:")
                    lines.append(f"    {progress.format_progress_bar()}")
                    lines.append(f"    {progress.processed_items}/{progress.total_items} items")
                    lines.append(f"    {progress.throughput:.1f} items/s")
                    lines.append(f"    ETA: {progress.format_eta()}")
            else:
                lines.append("\nNo active operations")
            
            if self.completed_operations:
                lines.append(f"\nCompleted Operations: {len(self.completed_operations)}")
                success = sum(1 for op in self.completed_operations if op.status == "completed")
                lines.append(f"  Success Rate: {success}/{len(self.completed_operations)}")
        
        return "\n".join(lines)
    
    def clear_completed(self):
        """Clear completed operations history."""
        self.completed_operations.clear()
        logger.info("Cleared completed operations history")