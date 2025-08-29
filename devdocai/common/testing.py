"""
Unified testing utilities for DevDocAI.

Provides consistent testing helpers and fixtures across all modules.
"""

import time
import tempfile
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, List, Callable
from contextlib import contextmanager
from unittest.mock import Mock, MagicMock, patch
import json
import sqlite3
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# TEST DATA GENERATORS
# ============================================================================

class TestDataGenerator:
    """Generate test data for various scenarios."""
    
    @staticmethod
    def generate_document(doc_id: Optional[str] = None, size: int = 1000) -> Dict[str, Any]:
        """
        Generate test document.
        
        Args:
            doc_id: Document ID (generated if not provided)
            size: Approximate document size in characters
            
        Returns:
            Test document dictionary
        """
        import uuid
        import random
        from datetime import datetime
        
        if doc_id is None:
            doc_id = str(uuid.uuid4())
        
        # Generate content
        words = ['lorem', 'ipsum', 'dolor', 'sit', 'amet', 'consectetur', 
                 'adipiscing', 'elit', 'sed', 'do', 'eiusmod', 'tempor']
        content = ' '.join(random.choices(words, k=size // 6))[:size]
        
        return {
            'id': doc_id,
            'title': f"Test Document {doc_id[:8]}",
            'content': content,
            'metadata': {
                'author': 'Test Author',
                'created_at': datetime.utcnow().isoformat(),
                'tags': ['test', 'sample', 'generated'],
                'version': '1.0.0'
            },
            'quality_score': random.uniform(0.5, 1.0)
        }
    
    @staticmethod
    def generate_config(mode: str = 'test') -> Dict[str, Any]:
        """Generate test configuration."""
        return {
            'version': '3.0.0',
            'mode': mode,
            'security': {
                'privacy_mode': 'local_only',
                'telemetry_enabled': False,
                'encryption_enabled': True
            },
            'memory': {
                'mode': 'baseline',
                'cache_size': 100,
                'max_file_size': 1048576
            },
            'paths': {
                'data': '/tmp/test_data',
                'templates': '/tmp/test_templates',
                'output': '/tmp/test_output'
            }
        }
    
    @staticmethod
    def generate_batch(count: int = 10, **kwargs) -> List[Dict[str, Any]]:
        """Generate batch of test documents."""
        return [
            TestDataGenerator.generate_document(**kwargs)
            for _ in range(count)
        ]


# ============================================================================
# TEST FIXTURES
# ============================================================================

@contextmanager
def temp_directory():
    """
    Context manager for temporary directory.
    
    Usage:
        with temp_directory() as temp_dir:
            # Use temp_dir Path object
            pass
    """
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        yield temp_dir
    finally:
        # Clean up
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


@contextmanager
def temp_database():
    """
    Context manager for temporary SQLite database.
    
    Usage:
        with temp_database() as db_path:
            # Use db_path for database operations
            pass
    """
    with temp_directory() as temp_dir:
        db_path = temp_dir / 'test.db'
        
        # Create database
        conn = sqlite3.connect(str(db_path))
        conn.close()
        
        yield db_path


@contextmanager
def mock_time(fixed_time: float = None):
    """
    Context manager to mock time functions.
    
    Args:
        fixed_time: Fixed time value (uses current time if None)
    """
    if fixed_time is None:
        fixed_time = time.time()
    
    with patch('time.time', return_value=fixed_time):
        with patch('time.perf_counter', return_value=fixed_time):
            yield fixed_time


@contextmanager
def capture_logs(logger_name: str = None, level: str = 'INFO'):
    """
    Context manager to capture log messages.
    
    Usage:
        with capture_logs() as logs:
            # Perform operations
            pass
        # Check logs list
    """
    import io
    
    # Get logger
    if logger_name:
        test_logger = logging.getLogger(logger_name)
    else:
        test_logger = logging.getLogger()
    
    # Create handler
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(getattr(logging, level))
    
    # Add handler
    test_logger.addHandler(handler)
    old_level = test_logger.level
    test_logger.setLevel(getattr(logging, level))
    
    logs = []
    
    try:
        yield logs
        
        # Parse captured logs
        log_capture.seek(0)
        logs.extend(log_capture.getvalue().splitlines())
        
    finally:
        # Remove handler
        test_logger.removeHandler(handler)
        test_logger.setLevel(old_level)


# ============================================================================
# PERFORMANCE TESTING
# ============================================================================

class PerformanceTester:
    """Utilities for performance testing."""
    
    @staticmethod
    def measure_time(func: Callable, *args, **kwargs) -> tuple[float, Any]:
        """
        Measure function execution time.
        
        Returns:
            Tuple of (execution_time, result)
        """
        start = time.perf_counter()
        result = func(*args, **kwargs)
        duration = time.perf_counter() - start
        return duration, result
    
    @staticmethod
    def benchmark(func: Callable, iterations: int = 100, warmup: int = 10) -> Dict[str, float]:
        """
        Benchmark function performance.
        
        Args:
            func: Function to benchmark
            iterations: Number of iterations
            warmup: Number of warmup iterations
            
        Returns:
            Performance statistics
        """
        import statistics
        
        # Warmup
        for _ in range(warmup):
            func()
        
        # Measure
        times = []
        for _ in range(iterations):
            duration, _ = PerformanceTester.measure_time(func)
            times.append(duration)
        
        return {
            'min': min(times),
            'max': max(times),
            'mean': statistics.mean(times),
            'median': statistics.median(times),
            'stdev': statistics.stdev(times) if len(times) > 1 else 0,
            'ops_per_sec': 1 / statistics.mean(times) if statistics.mean(times) > 0 else 0
        }
    
    @staticmethod
    def assert_performance(func: Callable, max_time: float, iterations: int = 10):
        """
        Assert function meets performance requirements.
        
        Args:
            func: Function to test
            max_time: Maximum allowed time in seconds
            iterations: Number of iterations to average
            
        Raises:
            AssertionError: If performance requirement not met
        """
        stats = PerformanceTester.benchmark(func, iterations=iterations, warmup=5)
        
        if stats['mean'] > max_time:
            raise AssertionError(
                f"Performance requirement not met: {stats['mean']:.4f}s > {max_time:.4f}s"
            )


# ============================================================================
# MOCK BUILDERS
# ============================================================================

class MockBuilder:
    """Build mock objects for testing."""
    
    @staticmethod
    def mock_storage() -> Mock:
        """Create mock storage system."""
        mock = MagicMock()
        mock.store_document.return_value = {'id': 'test-id', 'status': 'stored'}
        mock.retrieve_document.return_value = TestDataGenerator.generate_document()
        mock.query_documents.return_value = TestDataGenerator.generate_batch(5)
        mock.delete_document.return_value = True
        return mock
    
    @staticmethod
    def mock_encryption_manager() -> Mock:
        """Create mock encryption manager."""
        mock = MagicMock()
        mock.encrypt.return_value = b'encrypted_data'
        mock.decrypt.return_value = b'decrypted_data'
        mock.derive_key.return_value = (b'key', b'salt')
        return mock
    
    @staticmethod
    def mock_miair_engine() -> Mock:
        """Create mock MIAIR engine."""
        mock = MagicMock()
        mock.analyze.return_value = {
            'quality_score': 0.85,
            'entropy': 4.5,
            'patterns': ['pattern1', 'pattern2']
        }
        mock.optimize.return_value = {
            'optimized_content': 'Optimized content',
            'improvement': 0.15
        }
        return mock


# ============================================================================
# ASSERTION HELPERS
# ============================================================================

class AssertionHelpers:
    """Custom assertion helpers for testing."""
    
    @staticmethod
    def assert_valid_uuid(value: str):
        """Assert value is valid UUID."""
        import uuid
        try:
            uuid.UUID(value)
        except ValueError:
            raise AssertionError(f"Invalid UUID: {value}")
    
    @staticmethod
    def assert_json_equal(actual: Any, expected: Any, ignore_keys: Optional[List[str]] = None):
        """
        Assert JSON objects are equal, optionally ignoring keys.
        
        Args:
            actual: Actual JSON object
            expected: Expected JSON object
            ignore_keys: Keys to ignore in comparison
        """
        if ignore_keys:
            # Remove ignored keys
            if isinstance(actual, dict):
                actual = {k: v for k, v in actual.items() if k not in ignore_keys}
            if isinstance(expected, dict):
                expected = {k: v for k, v in expected.items() if k not in ignore_keys}
        
        # Compare
        if actual != expected:
            import json
            raise AssertionError(
                f"JSON objects not equal:\n"
                f"Actual: {json.dumps(actual, indent=2)}\n"
                f"Expected: {json.dumps(expected, indent=2)}"
            )
    
    @staticmethod
    def assert_performance_improved(baseline: float, current: float, min_improvement: float = 0.1):
        """
        Assert performance has improved.
        
        Args:
            baseline: Baseline performance metric
            current: Current performance metric
            min_improvement: Minimum required improvement (0.1 = 10%)
        """
        improvement = (baseline - current) / baseline
        
        if improvement < min_improvement:
            raise AssertionError(
                f"Performance not improved enough: {improvement:.1%} < {min_improvement:.1%}"
            )


# ============================================================================
# TEST DECORATORS
# ============================================================================

def requires_database(func):
    """Decorator for tests requiring database."""
    def wrapper(*args, **kwargs):
        with temp_database() as db_path:
            return func(*args, db_path=db_path, **kwargs)
    return wrapper


def requires_encryption(func):
    """Decorator for tests requiring encryption."""
    def wrapper(*args, **kwargs):
        mock_encryption = MockBuilder.mock_encryption_manager()
        with patch('devdocai.common.security.get_encryption_manager', return_value=mock_encryption):
            return func(*args, encryption_manager=mock_encryption, **kwargs)
    return wrapper


def slow_test(func):
    """Mark test as slow (for optional skipping)."""
    func._slow_test = True
    return func


def integration_test(func):
    """Mark test as integration test."""
    func._integration_test = True
    return func


# ============================================================================
# TEST BASE CLASSES
# ============================================================================

class BaseTestCase:
    """Base class for test cases with common functionality."""
    
    def setup_method(self):
        """Set up test method."""
        self.test_data = TestDataGenerator()
        self.temp_dirs = []
    
    def teardown_method(self):
        """Tear down test method."""
        # Clean up temp directories
        for temp_dir in self.temp_dirs:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
    
    def create_temp_dir(self) -> Path:
        """Create temporary directory (auto-cleaned)."""
        temp_dir = Path(tempfile.mkdtemp())
        self.temp_dirs.append(temp_dir)
        return temp_dir
    
    def assert_no_errors(self, func: Callable, *args, **kwargs):
        """Assert function executes without errors."""
        try:
            func(*args, **kwargs)
        except Exception as e:
            raise AssertionError(f"Function raised unexpected error: {e}")


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Generators
    'TestDataGenerator',
    
    # Fixtures
    'temp_directory',
    'temp_database',
    'mock_time',
    'capture_logs',
    
    # Performance
    'PerformanceTester',
    
    # Mocks
    'MockBuilder',
    
    # Assertions
    'AssertionHelpers',
    
    # Decorators
    'requires_database',
    'requires_encryption',
    'slow_test',
    'integration_test',
    
    # Base classes
    'BaseTestCase'
]