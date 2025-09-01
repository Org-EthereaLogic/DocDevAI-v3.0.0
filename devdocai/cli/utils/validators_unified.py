"""
Unified Validators - Input validation with mode-based security.

Consolidates validation logic with configurable security levels.
"""

import re
import os
from pathlib import Path
from typing import Any, List, Optional, Union
from functools import lru_cache

from devdocai.cli.config_unified import get_config


class UnifiedValidator:
    """Unified validator with mode-based behavior."""
    
    def __init__(self):
        """Initialize validator."""
        self.config = get_config()
        
        # Compile regex patterns
        self._patterns = {
            'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
            'url': re.compile(r'^https?://(?:[-\w.])+(?::\d+)?(?:[/\w._-]*)$'),
            'path_traversal': re.compile(r'\.\.[\\/]'),
            'command_injection': re.compile(r'[;&|`$]'),
            'sql_injection': re.compile(r"('|(--)|;|\*|union|select|drop|insert|delete|update)", re.IGNORECASE)
        }
        
        # Performance optimization
        if self.config.is_performance_enabled():
            self._init_performance_features()
    
    def _init_performance_features(self):
        """Initialize performance features."""
        # Cache validation results for immutable inputs
        self.validate_path = lru_cache(maxsize=256)(self._validate_path_impl)
        self.validate_string = lru_cache(maxsize=256)(self._validate_string_impl)
    
    def validate_path(self, path: Union[str, Path], 
                     must_exist: bool = False,
                     allowed_extensions: Optional[List[str]] = None) -> Path:
        """Validate file/directory path."""
        if not self.config.is_performance_enabled():
            return self._validate_path_impl(path, must_exist, allowed_extensions)
        
        # Convert to string for caching
        path_str = str(path)
        ext_tuple = tuple(allowed_extensions) if allowed_extensions else None
        return self._validate_path_impl(path_str, must_exist, ext_tuple)
    
    def _validate_path_impl(self, path: Union[str, Path], 
                           must_exist: bool = False,
                           allowed_extensions: Optional[Union[List[str], tuple]] = None) -> Path:
        """Core path validation implementation."""
        path_obj = Path(path) if isinstance(path, str) else path
        
        # Security checks if enabled
        if self.config.security.enable_validation:
            # Check for path traversal
            if self._patterns['path_traversal'].search(str(path_obj)):
                raise ValueError(f"Path traversal detected in: {path}")
            
            # Check absolute path restrictions
            if self.config.is_security_enabled():
                # Restrict to current directory and subdirectories
                try:
                    path_obj.resolve().relative_to(Path.cwd())
                except ValueError:
                    if not path_obj.is_absolute():
                        # Allow relative paths within current directory
                        path_obj = Path.cwd() / path_obj
                    else:
                        raise ValueError(f"Path outside allowed directory: {path}")
        
        # Existence check
        if must_exist and not path_obj.exists():
            raise ValueError(f"Path does not exist: {path}")
        
        # Extension check
        if allowed_extensions and path_obj.is_file():
            if isinstance(allowed_extensions, tuple):
                allowed_extensions = list(allowed_extensions)
            if path_obj.suffix not in allowed_extensions:
                raise ValueError(f"Invalid file extension: {path_obj.suffix}")
        
        # Size check for security mode
        if (self.config.is_security_enabled() and 
            path_obj.is_file() and path_obj.exists()):
            max_size = self.config.security.max_input_size
            if path_obj.stat().st_size > max_size:
                raise ValueError(f"File too large: {path_obj.stat().st_size} > {max_size}")
        
        return path_obj
    
    def validate_string(self, value: str, 
                       max_length: Optional[int] = None,
                       pattern: Optional[str] = None,
                       allow_empty: bool = False) -> str:
        """Validate string input."""
        if not self.config.is_performance_enabled():
            return self._validate_string_impl(value, max_length, pattern, allow_empty)
        
        # Call cached version
        return self._validate_string_impl(value, max_length, pattern, allow_empty)
    
    def _validate_string_impl(self, value: str, 
                             max_length: Optional[int] = None,
                             pattern: Optional[str] = None,
                             allow_empty: bool = False) -> str:
        """Core string validation implementation."""
        # Empty check
        if not value and not allow_empty:
            raise ValueError("Empty value not allowed")
        
        # Length check
        if max_length and len(value) > max_length:
            raise ValueError(f"String too long: {len(value)} > {max_length}")
        
        # Pattern check
        if pattern:
            if not re.match(pattern, value):
                raise ValueError(f"Value does not match pattern: {pattern}")
        
        # Security checks if enabled
        if self.config.security.enable_validation:
            # Check for command injection
            if self._patterns['command_injection'].search(value):
                raise ValueError("Potential command injection detected")
            
            # Check for SQL injection in secure mode
            if (self.config.is_security_enabled() and 
                self._patterns['sql_injection'].search(value)):
                raise ValueError("Potential SQL injection detected")
        
        return value
    
    def validate_email(self, email: str) -> str:
        """Validate email address."""
        if not self._patterns['email'].match(email):
            raise ValueError(f"Invalid email address: {email}")
        return email
    
    def validate_url(self, url: str) -> str:
        """Validate URL."""
        if not self._patterns['url'].match(url):
            raise ValueError(f"Invalid URL: {url}")
        
        # Additional security checks
        if self.config.is_security_enabled():
            # Block local URLs in production
            if any(blocked in url.lower() for blocked in ['localhost', '127.0.0.1', '0.0.0.0']):
                raise ValueError("Local URLs not allowed")
        
        return url
    
    def validate_integer(self, value: Any, 
                        min_value: Optional[int] = None,
                        max_value: Optional[int] = None) -> int:
        """Validate integer value."""
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid integer: {value}")
        
        if min_value is not None and int_value < min_value:
            raise ValueError(f"Value too small: {int_value} < {min_value}")
        
        if max_value is not None and int_value > max_value:
            raise ValueError(f"Value too large: {int_value} > {max_value}")
        
        return int_value
    
    def validate_choice(self, value: str, choices: List[str], 
                       case_sensitive: bool = False) -> str:
        """Validate choice from list."""
        if not case_sensitive:
            value = value.lower()
            choices = [c.lower() for c in choices]
        
        if value not in choices:
            raise ValueError(f"Invalid choice: {value}. Must be one of: {', '.join(choices)}")
        
        return value
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe file operations."""
        # Remove path separators
        filename = filename.replace('/', '_').replace('\\', '_')
        
        # Remove special characters
        if self.config.is_security_enabled():
            # Strict sanitization in secure mode
            filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        else:
            # Basic sanitization
            filename = re.sub(r'[<>:"|?*]', '_', filename)
        
        # Limit length
        max_length = 255
        if len(filename) > max_length:
            name, ext = os.path.splitext(filename)
            filename = name[:max_length - len(ext)] + ext
        
        return filename


# Global validator instance
_validator: Optional[UnifiedValidator] = None


def get_validator() -> UnifiedValidator:
    """Get global validator instance."""
    global _validator
    if _validator is None:
        _validator = UnifiedValidator()
    return _validator


# Convenience functions
def validate_path(path: Union[str, Path], **kwargs) -> Path:
    """Validate file/directory path."""
    return get_validator().validate_path(path, **kwargs)


def validate_string(value: str, **kwargs) -> str:
    """Validate string input."""
    return get_validator().validate_string(value, **kwargs)


def validate_email(email: str) -> str:
    """Validate email address."""
    return get_validator().validate_email(email)


def validate_url(url: str) -> str:
    """Validate URL."""
    return get_validator().validate_url(url)


def validate_integer(value: Any, **kwargs) -> int:
    """Validate integer value."""
    return get_validator().validate_integer(value, **kwargs)


def validate_choice(value: str, choices: List[str], **kwargs) -> str:
    """Validate choice from list."""
    return get_validator().validate_choice(value, choices, **kwargs)


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file operations."""
    return get_validator().sanitize_filename(filename)