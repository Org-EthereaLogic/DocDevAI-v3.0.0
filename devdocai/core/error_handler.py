"""
User-Friendly Error Handling System for DocDevAI v3.0.0

This module provides comprehensive error handling with:
- User-friendly error messages
- Contextual help and suggestions
- Error categorization
- Consistent error formatting across all modules

Addresses ISS-014: Poor error message quality
"""

import traceback
import logging
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Categories of errors for better user understanding."""
    CONFIGURATION = "Configuration Error"
    FILE_SYSTEM = "File System Error"
    DATABASE = "Database Error"
    NETWORK = "Network Error"
    VALIDATION = "Validation Error"
    PERMISSION = "Permission Error"
    RESOURCE = "Resource Error"
    DEPENDENCY = "Dependency Error"
    USER_INPUT = "User Input Error"
    SYSTEM = "System Error"


@dataclass
class ErrorContext:
    """Context information for better error messages."""
    module: str
    operation: str
    details: Optional[Dict[str, Any]] = None
    suggestions: Optional[List[str]] = None


class UserFriendlyError(Exception):
    """
    Base exception class that provides user-friendly error messages.
    
    Example:
        raise UserFriendlyError(
            technical_error=e,
            category=ErrorCategory.DATABASE,
            user_message="Unable to save your document",
            context=ErrorContext(
                module="M002",
                operation="save_document",
                suggestions=["Check disk space", "Try again later"]
            )
        )
    """
    
    def __init__(
        self,
        technical_error: Optional[Exception] = None,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        user_message: str = "An unexpected error occurred",
        context: Optional[ErrorContext] = None,
        error_code: Optional[str] = None
    ):
        self.technical_error = technical_error
        self.category = category
        self.user_message = user_message
        self.context = context
        self.error_code = error_code or self._generate_error_code()
        
        super().__init__(self.format_message())
    
    def _generate_error_code(self) -> str:
        """Generate a unique error code for tracking."""
        import hashlib
        import time
        
        # Create error code from category and timestamp
        error_string = f"{self.category.value}_{time.time()}"
        return f"ERR_{hashlib.md5(error_string.encode()).hexdigest()[:8].upper()}"
    
    def format_message(self) -> str:
        """Format the error message for users."""
        lines = [
            f"\n{'='*60}",
            f"❌ {self.category.value}",
            f"{'='*60}",
            "",
            f"What happened:",
            f"  {self.user_message}",
        ]
        
        if self.context:
            if self.context.module:
                lines.append(f"\nWhere:")
                lines.append(f"  Module: {self.context.module}")
                lines.append(f"  Operation: {self.context.operation}")
            
            if self.context.details:
                lines.append(f"\nDetails:")
                for key, value in self.context.details.items():
                    lines.append(f"  {key}: {value}")
            
            if self.context.suggestions:
                lines.append(f"\nWhat you can do:")
                for i, suggestion in enumerate(self.context.suggestions, 1):
                    lines.append(f"  {i}. {suggestion}")
        
        lines.extend([
            "",
            f"Error Code: {self.error_code}",
            f"{'='*60}"
        ])
        
        return "\n".join(lines)
    
    def get_technical_details(self) -> str:
        """Get technical details for logging/debugging."""
        if self.technical_error:
            return f"{type(self.technical_error).__name__}: {str(self.technical_error)}"
        return "No technical details available"


class ErrorHandler:
    """
    Central error handler with common error mappings.
    """
    
    # Common error message mappings
    ERROR_MAPPINGS = {
        # File System Errors
        "FileNotFoundError": {
            "category": ErrorCategory.FILE_SYSTEM,
            "message": "The requested file could not be found",
            "suggestions": [
                "Check if the file path is correct",
                "Ensure the file hasn't been moved or deleted",
                "Verify you have the right permissions"
            ]
        },
        "PermissionError": {
            "category": ErrorCategory.PERMISSION,
            "message": "You don't have permission to access this resource",
            "suggestions": [
                "Check file/folder permissions",
                "Run with appropriate privileges",
                "Contact your system administrator"
            ]
        },
        "IsADirectoryError": {
            "category": ErrorCategory.FILE_SYSTEM,
            "message": "Expected a file but found a directory",
            "suggestions": [
                "Verify the file path is correct",
                "Check if you meant to specify a file inside the directory"
            ]
        },
        
        # Database Errors
        "OperationalError": {
            "category": ErrorCategory.DATABASE,
            "message": "Database operation failed",
            "suggestions": [
                "Check if the database is accessible",
                "Verify database connection settings",
                "Ensure the database isn't locked by another process"
            ]
        },
        "IntegrityError": {
            "category": ErrorCategory.DATABASE,
            "message": "Data integrity constraint violated",
            "suggestions": [
                "Check for duplicate entries",
                "Ensure all required fields are provided",
                "Verify data types match expected formats"
            ]
        },
        
        # Network Errors
        "ConnectionError": {
            "category": ErrorCategory.NETWORK,
            "message": "Unable to establish network connection",
            "suggestions": [
                "Check your internet connection",
                "Verify the service URL is correct",
                "Check if a firewall is blocking the connection"
            ]
        },
        "TimeoutError": {
            "category": ErrorCategory.NETWORK,
            "message": "The operation took too long to complete",
            "suggestions": [
                "Try again with a smaller request",
                "Check your network connection speed",
                "Consider increasing the timeout setting"
            ]
        },
        
        # Validation Errors
        "ValidationError": {
            "category": ErrorCategory.VALIDATION,
            "message": "The provided data didn't pass validation",
            "suggestions": [
                "Check the input format",
                "Ensure all required fields are filled",
                "Verify data types are correct"
            ]
        },
        "ValueError": {
            "category": ErrorCategory.USER_INPUT,
            "message": "Invalid value provided",
            "suggestions": [
                "Check the input format and type",
                "Refer to the documentation for valid values",
                "Use the --help flag for usage examples"
            ]
        },
        
        # Configuration Errors
        "ConfigurationError": {
            "category": ErrorCategory.CONFIGURATION,
            "message": "Configuration is invalid or missing",
            "suggestions": [
                "Check your .devdocai.yml file",
                "Run 'devdocai init' to create default configuration",
                "Verify all required settings are present"
            ]
        },
        
        # Resource Errors
        "MemoryError": {
            "category": ErrorCategory.RESOURCE,
            "message": "Insufficient memory to complete operation",
            "suggestions": [
                "Close other applications to free memory",
                "Process smaller batches of data",
                "Consider upgrading system memory"
            ]
        },
        "OSError": {
            "category": ErrorCategory.SYSTEM,
            "message": "Operating system error occurred",
            "suggestions": [
                "Check system resources (disk space, memory)",
                "Verify file system integrity",
                "Review system logs for more details"
            ]
        }
    }
    
    @classmethod
    def handle_error(
        cls,
        error: Exception,
        context: Optional[ErrorContext] = None,
        custom_message: Optional[str] = None
    ) -> UserFriendlyError:
        """
        Convert a technical error to a user-friendly error.
        
        Args:
            error: The original exception
            context: Additional context about where/how the error occurred
            custom_message: Override the default user message
            
        Returns:
            UserFriendlyError with appropriate messaging
        """
        error_type = type(error).__name__
        
        # Look up error mapping
        mapping = cls.ERROR_MAPPINGS.get(error_type, {
            "category": ErrorCategory.SYSTEM,
            "message": "An unexpected error occurred",
            "suggestions": ["Try again", "Check the logs for more details"]
        })
        
        # Create user-friendly error
        return UserFriendlyError(
            technical_error=error,
            category=mapping["category"],
            user_message=custom_message or mapping["message"],
            context=context or ErrorContext(
                module="Unknown",
                operation="Unknown",
                suggestions=mapping.get("suggestions", [])
            )
        )
    
    @classmethod
    def wrap_operation(
        cls,
        operation_name: str,
        module: str,
        error_message: Optional[str] = None
    ):
        """
        Decorator to wrap operations with user-friendly error handling.
        
        Example:
            @ErrorHandler.wrap_operation("save_document", "M002")
            def save_document(doc):
                # ... implementation
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except UserFriendlyError:
                    # Already user-friendly, just re-raise
                    raise
                except Exception as e:
                    # Convert to user-friendly error
                    context = ErrorContext(
                        module=module,
                        operation=operation_name
                    )
                    
                    # Log technical details
                    logger.error(f"Error in {module}.{operation_name}: {e}", exc_info=True)
                    
                    # Raise user-friendly version
                    raise cls.handle_error(e, context, error_message)
            
            return wrapper
        return decorator


def format_validation_errors(errors: Dict[str, List[str]]) -> str:
    """
    Format validation errors in a user-friendly way.
    
    Args:
        errors: Dictionary of field names to error messages
        
    Returns:
        Formatted error message
    """
    lines = ["The following validation errors were found:"]
    
    for field, field_errors in errors.items():
        lines.append(f"\n  📍 {field}:")
        for error in field_errors:
            lines.append(f"      • {error}")
    
    lines.append("\nPlease correct these issues and try again.")
    
    return "\n".join(lines)


def create_error_report(
    error: Exception,
    include_technical: bool = False
) -> Dict[str, Any]:
    """
    Create a structured error report for logging/monitoring.
    
    Args:
        error: The exception to report
        include_technical: Whether to include technical details
        
    Returns:
        Dictionary with error information
    """
    report = {
        "error_type": type(error).__name__,
        "message": str(error),
        "timestamp": __import__('datetime').datetime.now().isoformat()
    }
    
    if isinstance(error, UserFriendlyError):
        report.update({
            "category": error.category.value,
            "error_code": error.error_code,
            "user_message": error.user_message,
            "module": error.context.module if error.context else None,
            "operation": error.context.operation if error.context else None
        })
        
        if include_technical and error.technical_error:
            report["technical_details"] = {
                "type": type(error.technical_error).__name__,
                "message": str(error.technical_error),
                "traceback": traceback.format_exc()
            }
    else:
        report["traceback"] = traceback.format_exc() if include_technical else None
    
    return report


# Example usage patterns for different modules
class ConfigurationErrorHandler:
    """Specialized error handler for M001 Configuration Manager."""
    
    @staticmethod
    def handle_missing_config(config_file: str) -> UserFriendlyError:
        """Handle missing configuration file."""
        return UserFriendlyError(
            category=ErrorCategory.CONFIGURATION,
            user_message=f"Configuration file '{config_file}' not found",
            context=ErrorContext(
                module="M001",
                operation="load_configuration",
                details={"file": config_file},
                suggestions=[
                    f"Run 'devdocai init' to create {config_file}",
                    "Check if the file path is correct",
                    "Copy from .devdocai.yml.example if available"
                ]
            )
        )
    
    @staticmethod
    def handle_invalid_config(errors: Dict[str, Any]) -> UserFriendlyError:
        """Handle invalid configuration."""
        return UserFriendlyError(
            category=ErrorCategory.CONFIGURATION,
            user_message="Configuration validation failed",
            context=ErrorContext(
                module="M001",
                operation="validate_configuration",
                details={"validation_errors": format_validation_errors(errors)},
                suggestions=[
                    "Review the configuration file for syntax errors",
                    "Check that all required fields are present",
                    "Refer to the configuration documentation"
                ]
            )
        )


class DatabaseErrorHandler:
    """Specialized error handler for M002 Local Storage."""
    
    @staticmethod
    def handle_connection_error(db_path: str, error: Exception) -> UserFriendlyError:
        """Handle database connection errors."""
        return UserFriendlyError(
            technical_error=error,
            category=ErrorCategory.DATABASE,
            user_message="Unable to connect to the database",
            context=ErrorContext(
                module="M002",
                operation="connect_database",
                details={"database": db_path},
                suggestions=[
                    "Check if the database file exists and is accessible",
                    "Verify you have write permissions to the database directory",
                    "Ensure no other process is locking the database"
                ]
            )
        )
    
    @staticmethod
    def handle_query_error(query: str, error: Exception) -> UserFriendlyError:
        """Handle database query errors."""
        return UserFriendlyError(
            technical_error=error,
            category=ErrorCategory.DATABASE,
            user_message="Database query failed",
            context=ErrorContext(
                module="M002",
                operation="execute_query",
                details={"query_type": query.split()[0].upper()},
                suggestions=[
                    "Check if the database schema is up to date",
                    "Run database migrations if available",
                    "Verify the data being saved is valid"
                ]
            )
        )