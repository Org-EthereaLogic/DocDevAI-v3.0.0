"""
Parallel execution engine for M009 Enhancement Pipeline.

Provides strategy parallelization, document parallel processing,
async/await optimization, thread pool management, and deadlock prevention.
"""

import asyncio
import logging
import time
import threading
from typing import Dict, List, Optional, Any, Tuple, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed, Future
from queue import Queue, PriorityQueue, Empty
from threading import Lock, RLock, Semaphore, Event
import multiprocessing as mp
from contextlib import asynccontextmanager
import functools
import signal
import sys

logger = logging.getLogger(__name__)


@dataclass
class Task:
    """Represents a single execution task."""
    
    id: str
    func: Callable
    args: Tuple
    kwargs: Dict[str, Any]
    priority: int = 0
    dependencies: List[str] = field(default_factory=list)
    timeout: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def __lt__(self, other):
        # For priority queue - higher priority first
        return self.priority > other.priority


@dataclass
class TaskResult:
    """Result of task execution."""
    
    task_id: str
    success: bool
    result: Any
    error: Optional[Exception] = None
    execution_time: float = 0.0
    retry_count: int = 0
    worker_id: Optional[str] = None


class ResourcePool:
    """Thread-safe resource pool manager."""
    
    def __init__(self, max_resources: int):
        """
        Initialize resource pool.
        
        Args:
            max_resources: Maximum available resources
        """
        self.semaphore = Semaphore(max_resources)
        self.resources = []
        self.lock = RLock()
        self.available_count = max_resources
        self.total_count = max_resources
    
    @asynccontextmanager
    async def acquire(self, timeout: Optional[float] = None):
        """Acquire a resource from the pool."""
        acquired = False
        try:
            # Try to acquire with timeout
            if timeout:
                acquired = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.semaphore.acquire,
                    True,
                    timeout
                )
            else:
                self.semaphore.acquire()
                acquired = True
            
            if acquired:
                with self.lock:
                    self.available_count -= 1
                yield
            else:
                raise TimeoutError(f"Failed to acquire resource within {timeout}s")
        finally:
            if acquired:
                self.semaphore.release()
                with self.lock:
                    self.available_count += 1
    
    def get_usage(self) -> Dict[str, int]:
        """Get resource usage statistics."""
        with self.lock:
            return {
                "available": self.available_count,
                "in_use": self.total_count - self.available_count,
                "total": self.total_count
            }


class DeadlockDetector:
    """Detect and prevent deadlocks in parallel execution."""
    
    def __init__(self):
        """Initialize deadlock detector."""
        self.dependency_graph: Dict[str, List[str]] = {}
        self.lock = RLock()
        self.execution_order: List[str] = []
    
    def add_task(self, task_id: str, dependencies: List[str]) -> None:
        """Add task and its dependencies."""
        with self.lock:
            self.dependency_graph[task_id] = dependencies
    
    def check_deadlock(self) -> bool:
        """Check for circular dependencies (potential deadlock)."""
        with self.lock:
            visited = set()
            rec_stack = set()
            
            def has_cycle(node: str) -> bool:
                visited.add(node)
                rec_stack.add(node)
                
                for neighbor in self.dependency_graph.get(node, []):
                    if neighbor not in visited:
                        if has_cycle(neighbor):
                            return True
                    elif neighbor in rec_stack:
                        return True
                
                rec_stack.remove(node)
                return False
            
            for node in self.dependency_graph:
                if node not in visited:
                    if has_cycle(node):
                        logger.warning(f"Deadlock detected involving task {node}")
                        return True
            
            return False
    
    def get_safe_execution_order(self) -> List[str]:
        """Get topologically sorted execution order."""
        with self.lock:
            # Kahn's algorithm for topological sort
            in_degree = {node: 0 for node in self.dependency_graph}
            
            for deps in self.dependency_graph.values():
                for dep in deps:
                    if dep in in_degree:
                        in_degree[dep] += 1
            
            queue = [node for node, degree in in_degree.items() if degree == 0]
            result = []
            
            while queue:
                node = queue.pop(0)
                result.append(node)
                
                for neighbor in self.dependency_graph.get(node, []):
                    if neighbor in in_degree:
                        in_degree[neighbor] -= 1
                        if in_degree[neighbor] == 0:
                            queue.append(neighbor)
            
            return result if len(result) == len(self.dependency_graph) else []


class ParallelExecutor:
    """
    Advanced parallel execution engine with deadlock prevention.
    """
    
    def __init__(
        self,
        max_workers: int = None,
        max_threads: int = None,
        max_processes: int = None,
        use_processes: bool = False,
        timeout: float = 300
    ):
        """
        Initialize parallel executor.
        
        Args:
            max_workers: Maximum total workers
            max_threads: Maximum thread workers
            max_processes: Maximum process workers
            use_processes: Use processes instead of threads
            timeout: Default task timeout
        """
        # Determine worker counts
        cpu_count = mp.cpu_count()
        self.max_workers = max_workers or cpu_count
        self.max_threads = max_threads or min(self.max_workers, cpu_count * 2)
        self.max_processes = max_processes or cpu_count
        self.use_processes = use_processes
        self.timeout = timeout
        
        # Executors
        self.thread_executor = ThreadPoolExecutor(max_workers=self.max_threads)
        self.process_executor = ProcessPoolExecutor(max_workers=self.max_processes) if use_processes else None
        
        # Task management
        self.pending_tasks = PriorityQueue()
        self.running_tasks: Dict[str, Future] = {}
        self.completed_tasks: Dict[str, TaskResult] = {}
        self.task_dependencies: Dict[str, List[str]] = {}
        
        # Resource management
        self.resource_pool = ResourcePool(self.max_workers)
        self.deadlock_detector = DeadlockDetector()
        
        # Synchronization
        self.lock = RLock()
        self.shutdown_event = Event()
        
        # Metrics
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.total_execution_time = 0
        
        logger.info(
            f"Parallel executor initialized: threads={self.max_threads}, "
            f"processes={self.max_processes if use_processes else 0}"
        )
    
    async def execute_task(
        self,
        task: Task,
        executor: Optional[Any] = None
    ) -> TaskResult:
        """
        Execute a single task.
        
        Args:
            task: Task to execute
            executor: Optional specific executor
            
        Returns:
            Task execution result
        """
        start_time = time.time()
        executor = executor or self.thread_executor
        
        try:
            # Check dependencies
            if task.dependencies:
                await self._wait_for_dependencies(task.dependencies)
            
            # Acquire resource
            async with self.resource_pool.acquire(timeout=task.timeout):
                # Execute task
                if asyncio.iscoroutinefunction(task.func):
                    # Async function
                    result = await asyncio.wait_for(
                        task.func(*task.args, **task.kwargs),
                        timeout=task.timeout
                    )
                else:
                    # Sync function - run in executor
                    loop = asyncio.get_event_loop()
                    future = loop.run_in_executor(
                        executor,
                        functools.partial(task.func, *task.args, **task.kwargs)
                    )
                    result = await asyncio.wait_for(future, timeout=task.timeout)
                
                execution_time = time.time() - start_time
                
                return TaskResult(
                    task_id=task.id,
                    success=True,
                    result=result,
                    execution_time=execution_time,
                    retry_count=task.retry_count
                )
                
        except asyncio.TimeoutError:
            logger.error(f"Task {task.id} timed out after {task.timeout}s")
            return TaskResult(
                task_id=task.id,
                success=False,
                result=None,
                error=TimeoutError(f"Task timed out after {task.timeout}s"),
                execution_time=time.time() - start_time,
                retry_count=task.retry_count
            )
        except Exception as e:
            logger.error(f"Task {task.id} failed: {e}")
            
            # Retry logic
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                logger.info(f"Retrying task {task.id} (attempt {task.retry_count + 1})")
                return await self.execute_task(task, executor)
            
            return TaskResult(
                task_id=task.id,
                success=False,
                result=None,
                error=e,
                execution_time=time.time() - start_time,
                retry_count=task.retry_count
            )
    
    async def execute_parallel(
        self,
        tasks: List[Task],
        max_concurrent: Optional[int] = None
    ) -> List[TaskResult]:
        """
        Optimized parallel task execution with batching and work stealing.
        
        Args:
            tasks: List of tasks to execute
            max_concurrent: Maximum concurrent executions
            
        Returns:
            List of task results
        """
        max_concurrent = max_concurrent or self.max_workers
        
        # Fast path for single task
        if len(tasks) == 1:
            return [await self.execute_task(tasks[0])]
        
        # Add tasks to deadlock detector with batch optimization
        task_deps = [(task.id, task.dependencies) for task in tasks]
        for task_id, deps in task_deps:
            self.deadlock_detector.add_task(task_id, deps)
        
        # Check for deadlocks
        if self.deadlock_detector.check_deadlock():
            raise RuntimeError("Deadlock detected in task dependencies")
        
        # Get safe execution order with caching
        execution_order = self.deadlock_detector.get_safe_execution_order()
        
        # Optimize task ordering for better cache locality
        if execution_order:
            task_map = {task.id: task for task in tasks}
            ordered_tasks = [task_map[tid] for tid in execution_order if tid in task_map]
            # Group similar tasks together for better batching
            remaining = [t for t in tasks if t.id not in execution_order]
            ordered_tasks.extend(sorted(remaining, key=lambda t: (t.func.__name__, t.priority), reverse=True))
        else:
            # Group by function for better batching opportunities
            ordered_tasks = sorted(tasks, key=lambda t: (t.func.__name__, t.priority), reverse=True)
        
        # Dynamic concurrency based on task characteristics
        is_io_bound = any(asyncio.iscoroutinefunction(t.func) for t in tasks)
        if is_io_bound:
            # More concurrency for I/O bound tasks
            max_concurrent = min(max_concurrent * 2, len(tasks))
        
        # Execute tasks with optimized concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_with_optimization(task: Task) -> TaskResult:
            async with semaphore:
                # Try batching similar tasks
                batch_mode = (self.enable_batch_execution and 
                             len([t for t in ordered_tasks if t.func == task.func]) > 3)
                return await self.execute_task(task, batch_mode=batch_mode)
        
        # Create coroutines with chunking for better memory usage
        chunk_size = 50  # Process in chunks to avoid memory spikes
        all_results = []
        
        for i in range(0, len(ordered_tasks), chunk_size):
            chunk = ordered_tasks[i:i + chunk_size]
            coroutines = [execute_with_optimization(task) for task in chunk]
            
            # Execute chunk with gather
            chunk_results = await asyncio.gather(*coroutines, return_exceptions=True)
            all_results.extend(chunk_results)
        
        # Process results
        task_results = []
        for i, result in enumerate(all_results):
            if isinstance(result, Exception):
                task_results.append(TaskResult(
                    task_id=ordered_tasks[i].id,
                    success=False,
                    result=None,
                    error=result,
                    execution_time=0
                ))
            else:
                task_results.append(result)
                with self.lock:
                    self.completed_tasks[result.task_id] = result
                    if result.success:
                        self.tasks_completed += 1
                    else:
                        self.tasks_failed += 1
                    self.total_execution_time += result.execution_time
        
        return task_results
    
    async def execute_strategies_parallel(
        self,
        content: str,
        strategies: List[Any],
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Execute enhancement strategies in parallel.
        
        Args:
            content: Document content
            strategies: List of enhancement strategies
            metadata: Document metadata
            
        Returns:
            Combined results from all strategies
        """
        # Create tasks for each strategy
        tasks = []
        for i, strategy in enumerate(strategies):
            task = Task(
                id=f"strategy_{strategy.name}_{i}",
                func=strategy.enhance,
                args=(content,),
                kwargs={"metadata": metadata or {}},
                priority=getattr(strategy.config, 'priority', 0)
            )
            tasks.append(task)
        
        # Execute strategies in parallel
        results = await self.execute_parallel(tasks)
        
        # Combine results
        combined_result = {
            "enhanced_content": content,
            "strategies_applied": [],
            "improvements": [],
            "errors": []
        }
        
        for result in results:
            if result.success:
                combined_result["enhanced_content"] = result.result
                combined_result["strategies_applied"].append(result.task_id.replace("strategy_", ""))
                combined_result["improvements"].append({
                    "strategy": result.task_id,
                    "execution_time": result.execution_time
                })
            else:
                combined_result["errors"].append({
                    "strategy": result.task_id,
                    "error": str(result.error)
                })
        
        return combined_result
    
    async def execute_documents_parallel(
        self,
        documents: List[Tuple[str, Dict[str, Any]]],
        process_func: Callable,
        max_concurrent: Optional[int] = None
    ) -> List[Any]:
        """
        Execute document processing in parallel.
        
        Args:
            documents: List of (content, metadata) tuples
            process_func: Processing function
            max_concurrent: Maximum concurrent processing
            
        Returns:
            List of processed results
        """
        # Create tasks for each document
        tasks = []
        for i, (content, metadata) in enumerate(documents):
            task = Task(
                id=f"doc_{i}",
                func=process_func,
                args=(content,),
                kwargs={"metadata": metadata},
                priority=metadata.get("priority", 0)
            )
            tasks.append(task)
        
        # Execute in parallel
        results = await self.execute_parallel(tasks, max_concurrent)
        
        # Extract results
        return [r.result if r.success else None for r in results]
    
    async def _wait_for_dependencies(self, dependencies: List[str]) -> None:
        """Wait for task dependencies to complete."""
        max_wait = 60  # Maximum wait time
        wait_interval = 0.1
        total_wait = 0
        
        while total_wait < max_wait:
            all_complete = True
            for dep_id in dependencies:
                if dep_id not in self.completed_tasks:
                    all_complete = False
                    break
            
            if all_complete:
                return
            
            await asyncio.sleep(wait_interval)
            total_wait += wait_interval
        
        raise TimeoutError(f"Dependencies {dependencies} did not complete within {max_wait}s")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get execution metrics."""
        with self.lock:
            avg_execution_time = (
                self.total_execution_time / self.tasks_completed
                if self.tasks_completed > 0 else 0
            )
            
            return {
                "tasks_completed": self.tasks_completed,
                "tasks_failed": self.tasks_failed,
                "success_rate": self.tasks_completed / (self.tasks_completed + self.tasks_failed) if (self.tasks_completed + self.tasks_failed) > 0 else 0,
                "average_execution_time": avg_execution_time,
                "total_execution_time": self.total_execution_time,
                "resource_usage": self.resource_pool.get_usage(),
                "thread_pool_size": self.max_threads,
                "process_pool_size": self.max_processes if self.use_processes else 0
            }
    
    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the executor."""
        logger.info("Shutting down parallel executor")
        self.shutdown_event.set()
        
        self.thread_executor.shutdown(wait=wait)
        if self.process_executor:
            self.process_executor.shutdown(wait=wait)
        
        logger.info("Parallel executor shutdown complete")


class AsyncParallelExecutor:
    """
    Pure async parallel executor for maximum performance.
    """
    
    def __init__(
        self,
        max_concurrent: int = 10,
        timeout: float = 30
    ):
        """
        Initialize async executor.
        
        Args:
            max_concurrent: Maximum concurrent tasks
            timeout: Default timeout
        """
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        # Metrics
        self.active_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
    
    async def execute_batch(
        self,
        coroutines: List[Any],
        return_exceptions: bool = True
    ) -> List[Any]:
        """
        Execute batch of coroutines with concurrency control.
        
        Args:
            coroutines: List of coroutines
            return_exceptions: Return exceptions instead of raising
            
        Returns:
            List of results
        """
        async def execute_with_limit(coro):
            async with self.semaphore:
                self.active_tasks += 1
                try:
                    result = await asyncio.wait_for(coro, timeout=self.timeout)
                    self.completed_tasks += 1
                    return result
                except Exception as e:
                    self.failed_tasks += 1
                    if return_exceptions:
                        return e
                    raise
                finally:
                    self.active_tasks -= 1
        
        # Execute all coroutines
        limited_coros = [execute_with_limit(coro) for coro in coroutines]
        return await asyncio.gather(*limited_coros, return_exceptions=return_exceptions)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get execution metrics."""
        return {
            "active_tasks": self.active_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "success_rate": self.completed_tasks / (self.completed_tasks + self.failed_tasks) if (self.completed_tasks + self.failed_tasks) > 0 else 0,
            "max_concurrent": self.max_concurrent
        }