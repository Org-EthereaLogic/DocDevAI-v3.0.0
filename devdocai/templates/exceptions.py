"""
Custom exceptions for M006 Template Registry.

This module defines specific exceptions for template-related errors
to provide clear error messages and better error handling.
"""

from typing import Optional, List, Any


class TemplateError(Exception):
    """Base exception for template-related errors."""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        """Initialize template error."""
        super().__init__(message)
        self.details = details


class TemplateNotFoundError(TemplateError):
    """Exception raised when a template cannot be found."""
    
    def __init__(self, template_id: str, category: Optional[str] = None):
        """Initialize template not found error."""
        message = f"Template not found: {template_id}"
        if category:
            message += f" in category: {category}"
        super().__init__(message, {"template_id": template_id, "category": category})


class TemplateParseError(TemplateError):
    """Exception raised when template parsing fails."""
    
    def __init__(self, message: str, line: Optional[int] = None, column: Optional[int] = None):
        """Initialize template parse error."""
        if line is not None:
            message += f" at line {line}"
            if column is not None:
                message += f", column {column}"
        super().__init__(message, {"line": line, "column": column})


class TemplateSyntaxError(TemplateError):
    """Exception raised when template has syntax errors."""
    
    def __init__(self, message: str, line: Optional[int] = None, column: Optional[int] = None):
        """Initialize template syntax error."""
        if line is not None:
            message += f" at line {line}"
            if column is not None:
                message += f", column {column}"
        super().__init__(message, {"line": line, "column": column})


class TemplateValidationError(TemplateError):
    """Exception raised when template validation fails."""
    
    def __init__(self, errors: List[str], warnings: Optional[List[str]] = None):
        """Initialize template validation error."""
        message = f"Template validation failed with {len(errors)} error(s)"
        super().__init__(message, {"errors": errors, "warnings": warnings or []})


class TemplateRenderError(TemplateError):
    """Exception raised when template rendering fails."""
    
    def __init__(self, message: str, missing_variables: Optional[List[str]] = None):
        """Initialize template render error."""
        if missing_variables:
            message += f". Missing variables: {', '.join(missing_variables)}"
        super().__init__(message, {"missing_variables": missing_variables or []})


class TemplateCategoryError(TemplateError):
    """Exception raised for category-related errors."""
    
    def __init__(self, category: str, message: Optional[str] = None):
        """Initialize category error."""
        error_message = f"Invalid category: {category}"
        if message:
            error_message += f". {message}"
        super().__init__(error_message, {"category": category})


class TemplateVersionError(TemplateError):
    """Exception raised for version-related errors."""
    
    def __init__(self, version: str, message: Optional[str] = None):
        """Initialize version error."""
        error_message = f"Invalid version: {version}"
        if message:
            error_message += f". {message}"
        super().__init__(error_message, {"version": version})


class TemplateStorageError(TemplateError):
    """Exception raised for storage-related errors."""
    
    def __init__(self, operation: str, message: str):
        """Initialize storage error."""
        error_message = f"Storage operation '{operation}' failed: {message}"
        super().__init__(error_message, {"operation": operation})


class TemplatePermissionError(TemplateError):
    """Exception raised for permission-related errors."""
    
    def __init__(self, action: str, resource: str):
        """Initialize permission error."""
        message = f"Permission denied for action '{action}' on resource '{resource}'"
        super().__init__(message, {"action": action, "resource": resource})


class TemplateDuplicateError(TemplateError):
    """Exception raised when attempting to create a duplicate template."""
    
    def __init__(self, template_id: str):
        """Initialize duplicate error."""
        message = f"Template already exists: {template_id}"
        super().__init__(message, {"template_id": template_id})


class TemplateIncludeError(TemplateError):
    """Exception raised when template inclusion fails."""
    
    def __init__(self, include_path: str, reason: str):
        """Initialize include error."""
        message = f"Failed to include template '{include_path}': {reason}"
        super().__init__(message, {"include_path": include_path, "reason": reason})


class TemplateVariableError(TemplateError):
    """Exception raised for variable-related errors."""
    
    def __init__(self, variable_name: str, message: str):
        """Initialize variable error."""
        error_message = f"Variable '{variable_name}' error: {message}"
        super().__init__(error_message, {"variable_name": variable_name})


# Security-related exceptions

class TemplateSecurityError(TemplateError):
    """Base exception for template security violations."""
    
    def __init__(self, message: str, threat_type: Optional[str] = None):
        """Initialize security error."""
        super().__init__(message, {"threat_type": threat_type})


class TemplateSSTIError(TemplateSecurityError):
    """Exception raised when Server-Side Template Injection is detected."""
    
    def __init__(self, message: str, pattern: Optional[str] = None):
        """Initialize SSTI error."""
        error_message = f"SSTI detected: {message}"
        super().__init__(error_message, "SSTI")
        self.pattern = pattern


class TemplatePathTraversalError(TemplateSecurityError):
    """Exception raised when path traversal attempt is detected."""
    
    def __init__(self, path: str):
        """Initialize path traversal error."""
        message = f"Path traversal attempt detected: {path}"
        super().__init__(message, "PathTraversal")
        self.path = path


class TemplateRateLimitError(TemplateSecurityError):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, message: str, limit_type: Optional[str] = None):
        """Initialize rate limit error."""
        super().__init__(message, "RateLimit")
        self.limit_type = limit_type


class TemplateSandboxError(TemplateSecurityError):
    """Exception raised for sandbox violations."""
    
    def __init__(self, message: str):
        """Initialize sandbox error."""
        error_message = f"Sandbox violation: {message}"
        super().__init__(error_message, "Sandbox")


class TemplateTimeoutError(TemplateSandboxError):
    """Exception raised when template execution times out."""
    
    def __init__(self, message: str):
        """Initialize timeout error."""
        super().__init__(f"Timeout: {message}")


class TemplateMemoryError(TemplateSandboxError):
    """Exception raised when memory limit is exceeded."""
    
    def __init__(self, message: str):
        """Initialize memory error."""
        super().__init__(f"Memory limit exceeded: {message}")


class TemplateRecursionError(TemplateSandboxError):
    """Exception raised when recursion limit is exceeded."""
    
    def __init__(self, message: str):
        """Initialize recursion error."""
        super().__init__(f"Recursion limit exceeded: {message}")