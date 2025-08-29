"""
Unified error handling module for DevDocAI.

Provides consistent exception classes and error handling across all modules.
"""

from typing import Optional, Dict, Any
import traceback
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# BASE EXCEPTIONS
# ============================================================================

class DevDocAIError(Exception):
    """Base exception for all DevDocAI errors."""
    
    def __init__(self, message: str, code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """
        Initialize DevDocAI error.
        
        Args:
            message: Error message
            code: Error code for programmatic handling
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary representation."""
        return {
            'error': self.code,
            'message': self.message,
            'details': self.details
        }


# ============================================================================
# CONFIGURATION ERRORS
# ============================================================================

class ConfigurationError(DevDocAIError):
    """Configuration-related errors."""
    pass


class InvalidConfigError(ConfigurationError):
    """Invalid configuration values."""
    pass


class MissingConfigError(ConfigurationError):
    """Missing required configuration."""
    pass


# ============================================================================
# STORAGE ERRORS
# ============================================================================

class StorageError(DevDocAIError):
    """Storage-related errors."""
    pass


class DocumentNotFoundError(StorageError):
    """Document not found in storage."""
    
    def __init__(self, document_id: str):
        super().__init__(
            f"Document not found: {document_id}",
            code="DOCUMENT_NOT_FOUND",
            details={'document_id': document_id}
        )


class StorageConnectionError(StorageError):
    """Failed to connect to storage."""
    pass


class StorageIntegrityError(StorageError):
    """Data integrity violation in storage."""
    pass


class StorageQuotaExceededError(StorageError):
    """Storage quota exceeded."""
    
    def __init__(self, used: int, quota: int):
        super().__init__(
            f"Storage quota exceeded: {used}/{quota}",
            code="QUOTA_EXCEEDED",
            details={'used': used, 'quota': quota}
        )


# ============================================================================
# SECURITY ERRORS
# ============================================================================

class SecurityError(DevDocAIError):
    """Security-related errors."""
    pass


class AuthenticationError(SecurityError):
    """Authentication failed."""
    pass


class AuthorizationError(SecurityError):
    """Authorization failed."""
    pass


class EncryptionError(SecurityError):
    """Encryption/decryption failed."""
    pass


class ValidationError(SecurityError):
    """Input validation failed."""
    
    def __init__(self, field: str, reason: str):
        super().__init__(
            f"Validation failed for {field}: {reason}",
            code="VALIDATION_ERROR",
            details={'field': field, 'reason': reason}
        )


class RateLimitError(SecurityError):
    """Rate limit exceeded."""
    
    def __init__(self, limit: int, window: int):
        super().__init__(
            f"Rate limit exceeded: {limit} requests per {window} seconds",
            code="RATE_LIMIT_EXCEEDED",
            details={'limit': limit, 'window': window}
        )


# ============================================================================
# PROCESSING ERRORS
# ============================================================================

class ProcessingError(DevDocAIError):
    """Processing-related errors."""
    pass


class TimeoutError(ProcessingError):
    """Operation timed out."""
    
    def __init__(self, operation: str, timeout: float):
        super().__init__(
            f"Operation '{operation}' timed out after {timeout}s",
            code="TIMEOUT",
            details={'operation': operation, 'timeout': timeout}
        )


class ResourceExhaustedError(ProcessingError):
    """System resources exhausted."""
    
    def __init__(self, resource: str, limit: Any):
        super().__init__(
            f"Resource exhausted: {resource} (limit: {limit})",
            code="RESOURCE_EXHAUSTED",
            details={'resource': resource, 'limit': limit}
        )


class InvalidInputError(ProcessingError):
    """Invalid input provided."""
    pass


# ============================================================================
# MIAIR ENGINE ERRORS
# ============================================================================

class MIAIRError(DevDocAIError):
    """MIAIR engine-related errors."""
    pass


class OptimizationError(MIAIRError):
    """Optimization failed."""
    pass


class QualityThresholdError(MIAIRError):
    """Quality threshold not met."""
    
    def __init__(self, current_quality: float, required_quality: float):
        super().__init__(
            f"Quality threshold not met: {current_quality:.2f} < {required_quality:.2f}",
            code="QUALITY_THRESHOLD_NOT_MET",
            details={'current': current_quality, 'required': required_quality}
        )


class PatternRecognitionError(MIAIRError):
    """Pattern recognition failed."""
    pass


# ============================================================================
# ERROR HANDLING UTILITIES
# ============================================================================

class ErrorHandler:
    """Centralized error handling utilities."""
    
    @staticmethod
    def handle_error(error: Exception, operation: str, reraise: bool = True) -> Optional[Dict[str, Any]]:
        """
        Handle and log error consistently.
        
        Args:
            error: Exception to handle
            operation: Operation that failed
            reraise: Whether to re-raise the error
            
        Returns:
            Error details dictionary if not re-raising
        """
        # Create error details
        error_details = {
            'operation': operation,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc()
        }
        
        # Add DevDocAI error details if available
        if isinstance(error, DevDocAIError):
            error_details.update(error.to_dict())
        
        # Log error
        logger.error(f"Error in {operation}: {error}", extra=error_details)
        
        # Re-raise or return details
        if reraise:
            raise
        else:
            return error_details
    
    @staticmethod
    def wrap_error(error: Exception, message: str, error_class: type = ProcessingError) -> DevDocAIError:
        """
        Wrap generic exception in DevDocAI error.
        
        Args:
            error: Original exception
            message: Error message
            error_class: DevDocAI error class to use
            
        Returns:
            DevDocAI error instance
        """
        return error_class(
            message=f"{message}: {str(error)}",
            details={
                'original_error': type(error).__name__,
                'original_message': str(error)
            }
        )


def safe_execute(operation: str, default: Any = None):
    """
    Decorator for safe function execution with error handling.
    
    Args:
        operation: Operation name for logging
        default: Default value to return on error
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_details = ErrorHandler.handle_error(e, operation, reraise=False)
                
                # Log and return default
                logger.warning(f"Returning default value for {operation} after error")
                return default
        
        return wrapper
    
    return decorator


def retry_on_error(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator for retrying operations on failure.
    
    Args:
        max_retries: Maximum number of retries
        delay: Initial delay between retries
        backoff: Backoff multiplier for delay
    """
    import time
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_error = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    
                    if attempt < max_retries:
                        logger.warning(f"Attempt {attempt + 1} failed, retrying in {current_delay}s: {e}")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All {max_retries} retries failed")
            
            # All retries failed
            raise last_error
        
        return wrapper
    
    return decorator


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Base
    'DevDocAIError',
    
    # Configuration
    'ConfigurationError',
    'InvalidConfigError',
    'MissingConfigError',
    
    # Storage
    'StorageError',
    'DocumentNotFoundError',
    'StorageConnectionError',
    'StorageIntegrityError',
    'StorageQuotaExceededError',
    
    # Security
    'SecurityError',
    'AuthenticationError',
    'AuthorizationError',
    'EncryptionError',
    'ValidationError',
    'RateLimitError',
    
    # Processing
    'ProcessingError',
    'TimeoutError',
    'ResourceExhaustedError',
    'InvalidInputError',
    
    # MIAIR
    'MIAIRError',
    'OptimizationError',
    'QualityThresholdError',
    'PatternRecognitionError',
    
    # Utilities
    'ErrorHandler',
    'safe_execute',
    'retry_on_error'
]