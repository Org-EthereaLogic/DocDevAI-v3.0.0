"""
DevDocAI Common Utilities Module.

Provides shared functionality across all DevDocAI modules including:
- Security and encryption
- Performance optimization
- Logging configuration
- Error handling
- Testing utilities
"""

# Security exports
from .security import (
    EncryptionManager,
    InputValidator,
    PIIDetector,
    RateLimiter,
    AuditLogger,
    secure_operation,
    security_context,
    get_encryption_manager,
    get_rate_limiter,
    get_audit_logger
)

# Performance exports
from .performance import (
    LRUCache,
    ContentCache,
    cached,
    ConnectionPool,
    BatchProcessor,
    ResourceMonitor,
    profile_performance,
    ParallelExecutor,
    LazyLoader,
    lazy_property
)

# Logging exports
from .logging import (
    JSONFormatter,
    ColoredFormatter,
    setup_logging,
    get_logger,
    log_execution,
    log_performance,
    LogContext
)

# Error exports
from .errors import (
    DevDocAIError,
    ConfigurationError,
    StorageError,
    SecurityError,
    ProcessingError,
    MIAIRError,
    OptimizationError,
    QualityThresholdError,
    ValidationError,
    RateLimitError,
    TimeoutError,
    ErrorHandler,
    safe_execute,
    retry_on_error
)

# Testing exports (only import when testing)
try:
    from .testing import (
        TestDataGenerator,
        temp_directory,
        temp_database,
        PerformanceTester,
        MockBuilder,
        AssertionHelpers,
        BaseTestCase
    )
except ImportError:
    # Testing dependencies not available in production
    pass

__version__ = '1.0.0'

__all__ = [
    # Security
    'EncryptionManager',
    'InputValidator',
    'PIIDetector',
    'RateLimiter',
    'AuditLogger',
    'secure_operation',
    'security_context',
    'get_encryption_manager',
    'get_rate_limiter',
    'get_audit_logger',
    
    # Performance
    'LRUCache',
    'ContentCache',
    'cached',
    'ConnectionPool',
    'BatchProcessor',
    'ResourceMonitor',
    'profile_performance',
    'ParallelExecutor',
    'LazyLoader',
    'lazy_property',
    
    # Logging
    'JSONFormatter',
    'ColoredFormatter',
    'setup_logging',
    'get_logger',
    'log_execution',
    'log_performance',
    'LogContext',
    
    # Errors
    'DevDocAIError',
    'ConfigurationError',
    'StorageError',
    'SecurityError',
    'ProcessingError',
    'MIAIRError',
    'OptimizationError',
    'QualityThresholdError',
    'ValidationError',
    'RateLimitError',
    'TimeoutError',
    'ErrorHandler',
    'safe_execute',
    'retry_on_error'
]