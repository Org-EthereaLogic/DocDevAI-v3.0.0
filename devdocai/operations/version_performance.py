"""M012 Version Control Integration - Pass 2: Performance Optimization
DevDocAI v3.0.0

Performance optimization module for large repository operations with:
- Intelligent caching for expensive Git operations
- Lazy loading of repository data
- Parallel processing for concurrent operations
- Memory-efficient object management
- Batch operation optimization

Performance Targets:
- Repository initialization: <2s for large repositories
- Commit operations: <5s for 1,000+ files
- Branch switching: <1s regardless of repository size
- History retrieval: <3s for 1,000+ commits
- Impact analysis: <10s for complex dependency graphs
- Memory usage: <500MB for repositories with 10,000+ files
"""

import functools
import logging
import multiprocessing as mp
import threading
import time
from collections import OrderedDict, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from weakref import WeakValueDictionary

from git import Repo

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Entry in the performance cache."""

    key: str
    value: Any
    timestamp: datetime
    ttl: int  # Time to live in seconds
    access_count: int = 0
    size_bytes: int = 0

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return datetime.now() > self.timestamp + timedelta(seconds=self.ttl)

    def access(self):
        """Record access to cache entry."""
        self.access_count += 1


@dataclass
class PerformanceMetrics:
    """Performance metrics for repository operations."""

    operation: str
    start_time: float
    end_time: float = 0
    file_count: int = 0
    commit_count: int = 0
    memory_used: int = 0
    cache_hits: int = 0
    cache_misses: int = 0

    @property
    def duration(self) -> float:
        """Get operation duration in seconds."""
        return self.end_time - self.start_time if self.end_time else time.time() - self.start_time

    @property
    def throughput(self) -> float:
        """Get throughput (operations per second)."""
        if self.duration == 0:
            return 0
        return (self.file_count + self.commit_count) / self.duration


class LRUCache:
    """Least Recently Used cache with TTL and size limits."""

    def __init__(self, max_size: int = 1000, max_memory_mb: int = 100):
        """
        Initialize LRU cache.

        Args:
            max_size: Maximum number of entries
            max_memory_mb: Maximum memory usage in MB
        """
        self.max_size = max_size
        self.max_memory = max_memory_mb * 1024 * 1024  # Convert to bytes
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.total_memory = 0
        self.lock = threading.RLock()
        self.stats = defaultdict(int)

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self.lock:
            if key not in self.cache:
                self.stats["misses"] += 1
                return None

            entry = self.cache[key]

            # Check expiration
            if entry.is_expired():
                self._remove(key)
                self.stats["expired"] += 1
                return None

            # Move to end (most recently used)
            self.cache.move_to_end(key)
            entry.access()
            self.stats["hits"] += 1

            return entry.value

    def set(self, key: str, value: Any, ttl: int = 300, size_bytes: int = 0):
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            size_bytes: Estimated size in bytes
        """
        with self.lock:
            # Remove if exists
            if key in self.cache:
                self._remove(key)

            # Create entry
            entry = CacheEntry(
                key=key, value=value, timestamp=datetime.now(), ttl=ttl, size_bytes=size_bytes
            )

            # Check memory limit
            while self.total_memory + size_bytes > self.max_memory and self.cache:
                self._evict_lru()

            # Check size limit
            while len(self.cache) >= self.max_size:
                self._evict_lru()

            # Add to cache
            self.cache[key] = entry
            self.total_memory += size_bytes
            self.stats["sets"] += 1

    def _remove(self, key: str):
        """Remove entry from cache."""
        if key in self.cache:
            entry = self.cache.pop(key)
            self.total_memory -= entry.size_bytes
            self.stats["removals"] += 1

    def _evict_lru(self):
        """Evict least recently used entry."""
        if self.cache:
            key = next(iter(self.cache))
            self._remove(key)
            self.stats["evictions"] += 1

    def clear(self):
        """Clear all cache entries."""
        with self.lock:
            self.cache.clear()
            self.total_memory = 0
            self.stats["clears"] += 1

    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        with self.lock:
            return dict(self.stats)


class GitOperationCache:
    """Specialized cache for Git operations."""

    def __init__(self):
        """Initialize Git operation cache."""
        self.commit_cache = LRUCache(max_size=5000, max_memory_mb=50)
        self.branch_cache = LRUCache(max_size=100, max_memory_mb=10)
        self.diff_cache = LRUCache(max_size=1000, max_memory_mb=30)
        self.history_cache = LRUCache(max_size=500, max_memory_mb=20)
        self.status_cache = LRUCache(max_size=10, max_memory_mb=5)

        # Weak reference cache for large objects
        self.weak_cache: WeakValueDictionary = WeakValueDictionary()

    def cache_commit(self, commit_hash: str, commit_data: Any, ttl: int = 3600):
        """Cache commit data."""
        size = len(str(commit_data)) if commit_data else 0
        self.commit_cache.set(commit_hash, commit_data, ttl, size)

    def get_commit(self, commit_hash: str) -> Optional[Any]:
        """Get cached commit data."""
        return self.commit_cache.get(commit_hash)

    def cache_branch_info(self, branch_name: str, info: Any, ttl: int = 300):
        """Cache branch information."""
        size = len(str(info)) if info else 0
        self.branch_cache.set(branch_name, info, ttl, size)

    def get_branch_info(self, branch_name: str) -> Optional[Any]:
        """Get cached branch information."""
        return self.branch_cache.get(branch_name)

    def cache_diff(self, diff_key: str, diff_data: Any, ttl: int = 600):
        """Cache diff data."""
        size = len(str(diff_data)) if diff_data else 0
        self.diff_cache.set(diff_key, diff_data, ttl, size)

    def get_diff(self, diff_key: str) -> Optional[Any]:
        """Get cached diff data."""
        return self.diff_cache.get(diff_key)

    def cache_history(self, file_path: str, history: List[Any], ttl: int = 600):
        """Cache file history."""
        size = sum(len(str(item)) for item in history)
        self.history_cache.set(file_path, history, ttl, size)

    def get_history(self, file_path: str) -> Optional[List[Any]]:
        """Get cached file history."""
        return self.history_cache.get(file_path)

    def cache_status(self, status_key: str, status: Any, ttl: int = 30):
        """Cache repository status."""
        size = len(str(status)) if status else 0
        self.status_cache.set(status_key, status, ttl, size)

    def get_status(self, status_key: str) -> Optional[Any]:
        """Get cached repository status."""
        return self.status_cache.get(status_key)

    def invalidate_branch_cache(self):
        """Invalidate branch-related caches."""
        self.branch_cache.clear()
        self.status_cache.clear()

    def invalidate_commit_cache(self):
        """Invalidate commit-related caches."""
        self.commit_cache.clear()
        self.history_cache.clear()
        self.diff_cache.clear()

    def get_stats(self) -> Dict[str, Dict[str, int]]:
        """Get cache statistics."""
        return {
            "commit": self.commit_cache.get_stats(),
            "branch": self.branch_cache.get_stats(),
            "diff": self.diff_cache.get_stats(),
            "history": self.history_cache.get_stats(),
            "status": self.status_cache.get_stats(),
        }


class LazyGitLoader:
    """Lazy loader for Git repository data."""

    def __init__(self, repo: Repo):
        """
        Initialize lazy loader.

        Args:
            repo: Git repository
        """
        self.repo = repo
        self._commits = None
        self._branches = None
        self._tags = None
        self._remotes = None
        self._config = None

    @property
    def commits(self):
        """Lazy load commits."""
        if self._commits is None:
            self._commits = {}
        return self._commits

    @property
    def branches(self):
        """Lazy load branches."""
        if self._branches is None:
            self._branches = {ref.name: ref for ref in self.repo.heads}
        return self._branches

    @property
    def tags(self):
        """Lazy load tags."""
        if self._tags is None:
            self._tags = {tag.name: tag for tag in self.repo.tags}
        return self._tags

    @property
    def remotes(self):
        """Lazy load remotes."""
        if self._remotes is None:
            self._remotes = {remote.name: remote for remote in self.repo.remotes}
        return self._remotes

    @property
    def config(self):
        """Lazy load configuration."""
        if self._config is None:
            self._config = self.repo.config_reader()
        return self._config

    def get_commit_batch(self, commit_hashes: List[str], max_workers: int = 4) -> Dict[str, Any]:
        """
        Get multiple commits in parallel.

        Args:
            commit_hashes: List of commit hashes
            max_workers: Maximum parallel workers

        Returns:
            Dictionary of commit hash to commit object
        """
        results = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self._get_commit, hash_): hash_ for hash_ in commit_hashes}

            for future in as_completed(futures):
                hash_ = futures[future]
                try:
                    results[hash_] = future.result()
                except Exception as e:
                    logger.error(f"Failed to load commit {hash_}: {e}")
                    results[hash_] = None

        return results

    def _get_commit(self, commit_hash: str):
        """Get single commit."""
        if commit_hash not in self.commits:
            self.commits[commit_hash] = self.repo.commit(commit_hash)
        return self.commits[commit_hash]

    def clear(self):
        """Clear lazy loaded data."""
        self._commits = None
        self._branches = None
        self._tags = None
        self._remotes = None
        self._config = None


class BatchGitOperations:
    """Batch operations for Git repositories."""

    def __init__(self, repo: Repo, max_batch_size: int = 100):
        """
        Initialize batch operations.

        Args:
            repo: Git repository
            max_batch_size: Maximum batch size
        """
        self.repo = repo
        self.max_batch_size = max_batch_size
        self.pending_adds: Set[str] = set()
        self.pending_removes: Set[str] = set()
        self.lock = threading.RLock()

    def add_file(self, file_path: str):
        """Add file to pending batch."""
        with self.lock:
            self.pending_adds.add(file_path)
            if file_path in self.pending_removes:
                self.pending_removes.remove(file_path)

            if len(self.pending_adds) >= self.max_batch_size:
                self.flush_adds()

    def remove_file(self, file_path: str):
        """Remove file from pending batch."""
        with self.lock:
            self.pending_removes.add(file_path)
            if file_path in self.pending_adds:
                self.pending_adds.remove(file_path)

            if len(self.pending_removes) >= self.max_batch_size:
                self.flush_removes()

    def flush_adds(self):
        """Flush pending adds to repository."""
        with self.lock:
            if self.pending_adds:
                self.repo.index.add(list(self.pending_adds))
                self.pending_adds.clear()

    def flush_removes(self):
        """Flush pending removes from repository."""
        with self.lock:
            if self.pending_removes:
                self.repo.index.remove(list(self.pending_removes))
                self.pending_removes.clear()

    def flush_all(self):
        """Flush all pending operations."""
        self.flush_adds()
        self.flush_removes()

    def batch_commit(self, files: List[str], message: str, chunk_size: int = 500) -> List[str]:
        """
        Commit files in batches.

        Args:
            files: List of files to commit
            message: Commit message
            chunk_size: Files per commit chunk

        Returns:
            List of commit hashes
        """
        commits = []

        for i in range(0, len(files), chunk_size):
            chunk = files[i : i + chunk_size]
            self.repo.index.add(chunk)
            commit = self.repo.index.commit(f"{message} (batch {i//chunk_size + 1})")
            commits.append(str(commit.hexsha))

        return commits


class ParallelGitProcessor:
    """Parallel processor for Git operations."""

    def __init__(self, repo: Repo, max_workers: int = None):
        """
        Initialize parallel processor.

        Args:
            repo: Git repository
            max_workers: Maximum parallel workers (defaults to CPU count)
        """
        self.repo = repo
        self.max_workers = max_workers or mp.cpu_count()

    def process_files_parallel(
        self, files: List[str], operation: callable, chunk_size: int = 100
    ) -> List[Any]:
        """
        Process files in parallel.

        Args:
            files: List of files to process
            operation: Operation to perform on each file
            chunk_size: Files per worker chunk

        Returns:
            List of operation results
        """
        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Split files into chunks
            chunks = [files[i : i + chunk_size] for i in range(0, len(files), chunk_size)]

            # Submit chunks for processing
            futures = {
                executor.submit(self._process_chunk, chunk, operation): chunk for chunk in chunks
            }

            # Collect results
            for future in as_completed(futures):
                try:
                    chunk_results = future.result()
                    results.extend(chunk_results)
                except Exception as e:
                    logger.error(f"Failed to process chunk: {e}")

        return results

    def _process_chunk(self, chunk: List[str], operation: callable) -> List[Any]:
        """Process a chunk of files."""
        results = []
        for file in chunk:
            try:
                result = operation(file)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process file {file}: {e}")
                results.append(None)
        return results

    def analyze_commits_parallel(
        self, commit_range: str, analyzer: callable, max_commits: int = 1000
    ) -> List[Any]:
        """
        Analyze commits in parallel.

        Args:
            commit_range: Git commit range
            analyzer: Function to analyze each commit
            max_commits: Maximum commits to analyze

        Returns:
            List of analysis results
        """
        # Get commits
        commits = list(self.repo.iter_commits(commit_range, max_count=max_commits))

        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(analyzer, commit): commit for commit in commits}

            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to analyze commit: {e}")
                    results.append(None)

        return results


class MemoryEfficientGitManager:
    """Memory-efficient manager for large Git operations."""

    def __init__(self, repo: Repo, memory_limit_mb: int = 500):
        """
        Initialize memory-efficient manager.

        Args:
            repo: Git repository
            memory_limit_mb: Memory limit in MB
        """
        self.repo = repo
        self.memory_limit = memory_limit_mb * 1024 * 1024
        self.current_memory = 0

    def iter_commits_efficient(
        self, rev: str = "HEAD", paths: Optional[List[str]] = None, batch_size: int = 100
    ):
        """
        Iterate commits memory-efficiently.

        Args:
            rev: Revision specification
            paths: Paths to filter commits
            batch_size: Commits per batch

        Yields:
            Commit objects
        """
        kwargs = {"rev": rev}
        if paths:
            kwargs["paths"] = paths

        batch = []
        for commit in self.repo.iter_commits(**kwargs):
            batch.append(commit)

            if len(batch) >= batch_size:
                yield from batch
                batch.clear()

        if batch:
            yield from batch

    def get_file_history_efficient(
        self, file_path: str, max_commits: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get file history memory-efficiently.

        Args:
            file_path: Path to file
            max_commits: Maximum commits to retrieve

        Returns:
            List of commit information
        """
        history = []

        for i, commit in enumerate(self.iter_commits_efficient(paths=[file_path])):
            if i >= max_commits:
                break

            # Extract only essential information
            history.append(
                {
                    "hash": commit.hexsha[:8],
                    "message": commit.message[:100],  # Truncate message
                    "author": commit.author.name,
                    "date": commit.committed_date,
                }
            )

        return history

    def diff_large_files(
        self, from_commit: str, to_commit: str, file_path: str, context_lines: int = 3
    ) -> Dict[str, Any]:
        """
        Diff large files memory-efficiently.

        Args:
            from_commit: Starting commit
            to_commit: Ending commit
            file_path: Path to file
            context_lines: Context lines in diff

        Returns:
            Diff information
        """
        # Use git command directly for memory efficiency
        diff_output = self.repo.git.diff(
            from_commit, to_commit, file_path, unified=context_lines, no_prefix=True
        )

        # Parse diff efficiently
        added = 0
        removed = 0

        for line in diff_output.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                added += 1
            elif line.startswith("-") and not line.startswith("---"):
                removed += 1

        return {
            "file": file_path,
            "added": added,
            "removed": removed,
            "total_changes": added + removed,
        }


def performance_monitor(func):
    """Decorator to monitor function performance."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        metrics = PerformanceMetrics(operation=func.__name__, start_time=time.time())

        try:
            result = func(*args, **kwargs)
            metrics.end_time = time.time()

            # Log performance
            logger.debug(
                f"{func.__name__} completed in {metrics.duration:.3f}s "
                f"(throughput: {metrics.throughput:.1f} ops/s)"
            )

            return result

        except Exception as e:
            metrics.end_time = time.time()
            logger.error(f"{func.__name__} failed after {metrics.duration:.3f}s: {e}")
            raise

    return wrapper


class PerformanceOptimizedVersionControl:
    """Performance-optimized version control operations."""

    def __init__(self, repo: Repo):
        """
        Initialize performance-optimized version control.

        Args:
            repo: Git repository
        """
        self.repo = repo
        self.cache = GitOperationCache()
        self.lazy_loader = LazyGitLoader(repo)
        self.batch_ops = BatchGitOperations(repo)
        self.parallel_processor = ParallelGitProcessor(repo)
        self.memory_manager = MemoryEfficientGitManager(repo)

    @performance_monitor
    def fast_commit(self, files: List[str], message: str) -> str:
        """
        Fast commit for large number of files.

        Args:
            files: Files to commit
            message: Commit message

        Returns:
            Commit hash
        """
        # Use batch operations
        for file in files:
            self.batch_ops.add_file(file)

        self.batch_ops.flush_all()
        commit = self.repo.index.commit(message)

        # Invalidate relevant caches
        self.cache.invalidate_commit_cache()

        return str(commit.hexsha)

    @performance_monitor
    def fast_branch_switch(self, branch_name: str) -> bool:
        """
        Fast branch switching with caching.

        Args:
            branch_name: Branch to switch to

        Returns:
            True if successful
        """
        # Check cache first
        branch_info = self.cache.get_branch_info(branch_name)

        if not branch_info:
            # Use lazy loader
            if branch_name in self.lazy_loader.branches:
                branch = self.lazy_loader.branches[branch_name]
                branch_info = {
                    "name": branch.name,
                    "commit": str(branch.commit.hexsha),
                }
                self.cache.cache_branch_info(branch_name, branch_info)
            else:
                return False

        # Switch branch
        branch = self.repo.heads[branch_name]
        branch.checkout()

        # Invalidate status cache
        self.cache.invalidate_branch_cache()

        return True

    @performance_monitor
    def fast_history(self, file_path: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fast file history retrieval with caching.

        Args:
            file_path: Path to file
            limit: Maximum commits

        Returns:
            List of commit information
        """
        # Check cache
        cache_key = f"{file_path}:{limit}"
        history = self.cache.get_history(cache_key)

        if history is None:
            # Use memory-efficient retrieval
            history = self.memory_manager.get_file_history_efficient(file_path, limit)
            self.cache.cache_history(cache_key, history)

        return history

    @performance_monitor
    def fast_diff(self, from_commit: str, to_commit: str, file_path: str) -> Dict[str, Any]:
        """
        Fast diff with caching.

        Args:
            from_commit: Starting commit
            to_commit: Ending commit
            file_path: Path to file

        Returns:
            Diff information
        """
        # Generate cache key
        cache_key = f"{from_commit}:{to_commit}:{file_path}"
        diff = self.cache.get_diff(cache_key)

        if diff is None:
            # Use memory-efficient diff
            diff = self.memory_manager.diff_large_files(from_commit, to_commit, file_path)
            self.cache.cache_diff(cache_key, diff)

        return diff

    @performance_monitor
    def parallel_file_analysis(self, files: List[str], analyzer: callable) -> List[Any]:
        """
        Analyze files in parallel.

        Args:
            files: Files to analyze
            analyzer: Analysis function

        Returns:
            Analysis results
        """
        return self.parallel_processor.process_files_parallel(files, analyzer)

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return {
            "cache_stats": self.cache.get_stats(),
            "batch_pending": {
                "adds": len(self.batch_ops.pending_adds),
                "removes": len(self.batch_ops.pending_removes),
            },
        }
