"""
M004 Document Generator - Unified Validators (Refactored).

Combines basic and security validation functionality into a single,
configurable component with layered validation levels.

Pass 4 Refactoring: Consolidates validators.py and security_validator.py
to eliminate duplication while preserving all functionality.
"""

import re
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple, Set
from datetime import datetime
from enum import Enum
import json
import urllib.parse

from ...common.logging import get_logger
from ...common.errors import DevDocAIError
from ...common.security import get_audit_logger

logger = get_logger(__name__)


class ValidationLevel(Enum):
    """Validation levels for input/output."""
    NONE = "none"  # No validation (fastest, unsafe)
    BASIC = "basic"  # Basic type and format checking
    STANDARD = "standard"  # Standard validation with sanitization
    STRICT = "strict"  # Maximum validation with security checks


class ValidationError(DevDocAIError):
    """Exception for validation errors."""
    pass


class UnifiedValidator:
    """
    Unified validator with configurable validation levels.
    
    Features:
    - Backward compatible with both basic and security validators
    - Layered validation (none, basic, standard, strict)
    - Performance optimized with caching for repeated validations
    - Comprehensive security checks at higher levels
    - PII detection and sanitization
    """
    
    # Common patterns for validation
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    URL_PATTERN = re.compile(r'^https?://[^\s/$.?#].[^\s]*$', re.IGNORECASE)
    PHONE_PATTERN = re.compile(r'^\+?1?\d{9,15}$')
    
    # PII patterns for detection
    PII_PATTERNS = {
        'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b|\b\d{9}\b'),
        'credit_card': re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'),
        'email': EMAIL_PATTERN,
        'phone': PHONE_PATTERN,
        'ip_address': re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
        'api_key': re.compile(r'\b[A-Za-z0-9]{32,}\b'),
    }
    
    # Dangerous patterns for security validation
    DANGEROUS_PATTERNS = {
        'script_tag': re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
        'javascript_url': re.compile(r'javascript:', re.IGNORECASE),
        'data_url': re.compile(r'data:text/html', re.IGNORECASE),
        'sql_injection': re.compile(r'\b(union|select|insert|update|delete|drop)\b.*\b(from|into|where)\b', re.IGNORECASE),
        'command_injection': re.compile(r'[;&|`$]|\$\(|\bsudo\b|\brm\s+-rf\b', re.IGNORECASE),
        'path_traversal': re.compile(r'\.\./', re.IGNORECASE),
        'xxe_injection': re.compile(r'<!DOCTYPE[^>]*\[.*<!ENTITY', re.IGNORECASE | re.DOTALL),
    }
    
    # File type restrictions
    ALLOWED_FILE_EXTENSIONS = {
        'document': ['.md', '.txt', '.rst', '.adoc'],
        'config': ['.yml', '.yaml', '.json', '.toml', '.ini'],
        'code': ['.py', '.js', '.ts', '.java', '.cpp', '.go'],
        'data': ['.csv', '.tsv', '.xml'],
    }
    
    # Maximum sizes for different content types
    MAX_SIZES = {
        'title': 200,
        'description': 1000,
        'content': 1024 * 1024,  # 1MB
        'metadata': 10 * 1024,  # 10KB
        'filename': 255,
        'url': 2048,
    }
    
    def __init__(
        self,
        validation_level: ValidationLevel = ValidationLevel.STANDARD,
        enable_pii_detection: Optional[bool] = None,
        enable_audit: Optional[bool] = None,
        custom_patterns: Optional[Dict[str, re.Pattern]] = None,
        custom_validators: Optional[Dict[str, callable]] = None,
        max_sizes: Optional[Dict[str, int]] = None,
        **kwargs
    ):
        """
        Initialize unified validator.
        
        Args:
            validation_level: Level of validation to apply
            enable_pii_detection: Enable PII detection (auto-enabled for standard/strict)
            enable_audit: Enable audit logging (auto-enabled for standard/strict)
            custom_patterns: Additional validation patterns
            custom_validators: Custom validation functions
            max_sizes: Custom maximum sizes for content types
            **kwargs: Additional configuration options
        """
        self.validation_level = validation_level
        
        # Auto-enable features based on validation level
        if enable_pii_detection is None:
            self.enable_pii_detection = validation_level in (ValidationLevel.STANDARD, ValidationLevel.STRICT)
        else:
            self.enable_pii_detection = enable_pii_detection
        
        if enable_audit is None:
            self.enable_audit = validation_level in (ValidationLevel.STANDARD, ValidationLevel.STRICT)
        else:
            self.enable_audit = enable_audit
        
        # Initialize audit logger if needed
        if self.enable_audit:
            self._audit_logger = get_audit_logger()
        
        # Merge custom patterns
        self.validation_patterns = self.DANGEROUS_PATTERNS.copy()
        if custom_patterns:
            self.validation_patterns.update(custom_patterns)
        
        # Store custom validators
        self.custom_validators = custom_validators or {}
        
        # Merge max sizes
        self.max_sizes = self.MAX_SIZES.copy()
        if max_sizes:
            self.max_sizes.update(max_sizes)
        
        # Cache for validation results
        self._validation_cache = {}
        
        logger.info(
            f"Initialized UnifiedValidator with level={validation_level.value}, "
            f"pii_detection={self.enable_pii_detection}, audit={self.enable_audit}"
        )
    
    def validate(
        self,
        data: Any,
        data_type: str = "generic",
        context: Optional[Dict[str, Any]] = None,
        sanitize: Optional[bool] = None
    ) -> Tuple[bool, Any, List[str]]:
        """
        Main validation method with configurable levels.
        
        Args:
            data: Data to validate
            data_type: Type of data (title, content, metadata, etc.)
            context: Additional context for validation
            sanitize: Whether to sanitize data (auto-enabled for standard/strict)
            
        Returns:
            Tuple of (is_valid, sanitized_data, errors)
        """
        if self.validation_level == ValidationLevel.NONE:
            return True, data, []
        
        if sanitize is None:
            sanitize = self.validation_level in (ValidationLevel.STANDARD, ValidationLevel.STRICT)
        
        errors = []
        sanitized_data = data
        
        try:
            # Level-based validation
            if self.validation_level >= ValidationLevel.BASIC:
                errors.extend(self._validate_basic(data, data_type))
            
            if self.validation_level >= ValidationLevel.STANDARD:
                errors.extend(self._validate_standard(data, data_type))
                if sanitize:
                    sanitized_data = self._sanitize_data(data, data_type)
            
            if self.validation_level == ValidationLevel.STRICT:
                errors.extend(self._validate_strict(data, data_type))
            
            # Custom validation if provided
            if data_type in self.custom_validators:
                custom_errors = self.custom_validators[data_type](data, context)
                if custom_errors:
                    errors.extend(custom_errors)
            
            # PII detection if enabled
            if self.enable_pii_detection and isinstance(data, str):
                pii_found = self._detect_pii(data)
                if pii_found:
                    errors.append(f"PII detected: {', '.join(pii_found)}")
            
            # Audit logging if enabled
            if self.enable_audit:
                self._audit_logger.log_event(
                    "validation",
                    data_type=data_type,
                    validation_level=self.validation_level.value,
                    errors_found=len(errors) > 0
                )
            
            is_valid = len(errors) == 0
            return is_valid, sanitized_data, errors
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False, data, [str(e)]
    
    def _validate_basic(self, data: Any, data_type: str) -> List[str]:
        """Basic validation for type and format."""
        errors = []
        
        # Type validation
        if data is None:
            errors.append(f"{data_type} cannot be None")
            return errors
        
        # Size validation
        if data_type in self.max_sizes:
            if isinstance(data, str):
                if len(data) > self.max_sizes[data_type]:
                    errors.append(f"{data_type} exceeds maximum size of {self.max_sizes[data_type]}")
            elif isinstance(data, (list, dict)):
                size = len(json.dumps(data))
                if size > self.max_sizes[data_type]:
                    errors.append(f"{data_type} exceeds maximum size of {self.max_sizes[data_type]}")
        
        # Format validation for specific types
        if data_type == "email" and isinstance(data, str):
            if not self.EMAIL_PATTERN.match(data):
                errors.append("Invalid email format")
        
        elif data_type == "url" and isinstance(data, str):
            if not self.URL_PATTERN.match(data):
                errors.append("Invalid URL format")
        
        elif data_type == "filename" and isinstance(data, str):
            if '/' in data or '\\' in data or '..' in data:
                errors.append("Invalid filename: contains path separators")
            if len(data) > 255:
                errors.append("Filename too long")
        
        return errors
    
    def _validate_standard(self, data: Any, data_type: str) -> List[str]:
        """Standard validation with security checks."""
        errors = []
        
        if not isinstance(data, str):
            return errors
        
        # Check for dangerous patterns
        for pattern_name, pattern in self.validation_patterns.items():
            if pattern.search(data):
                if self.validation_level == ValidationLevel.STANDARD:
                    # Warning only in standard mode
                    logger.warning(f"Potentially dangerous pattern detected: {pattern_name}")
                else:
                    # Error in strict mode
                    errors.append(f"Dangerous pattern detected: {pattern_name}")
        
        # Check for common injection attempts
        if data_type in ["content", "metadata"]:
            # SQL injection check
            sql_keywords = ['select', 'union', 'drop', 'insert', 'update', 'delete']
            data_lower = data.lower()
            suspicious_sql = sum(1 for keyword in sql_keywords if keyword in data_lower) >= 3
            if suspicious_sql:
                errors.append("Potential SQL injection detected")
        
        return errors
    
    def _validate_strict(self, data: Any, data_type: str) -> List[str]:
        """Strict validation with maximum security."""
        errors = []
        
        if isinstance(data, str):
            # No HTML/JavaScript at all
            if '<' in data or '>' in data:
                errors.append("HTML tags not allowed in strict mode")
            
            # No URLs except whitelisted protocols
            if 'http://' in data.lower() and data_type != "url":
                errors.append("HTTP URLs not allowed in strict mode (use HTTPS)")
            
            # Character validation
            if '\x00' in data:
                errors.append("Null bytes not allowed")
            
            # Unicode validation
            try:
                data.encode('utf-8').decode('utf-8')
            except UnicodeError:
                errors.append("Invalid Unicode characters detected")
        
        elif isinstance(data, dict):
            # Recursive validation for dictionaries
            for key, value in data.items():
                key_valid, _, key_errors = self.validate(key, "metadata_key")
                if not key_valid:
                    errors.extend([f"Key '{key}': {e}" for e in key_errors])
                
                value_valid, _, value_errors = self.validate(value, "metadata_value")
                if not value_valid:
                    errors.extend([f"Value for '{key}': {e}" for e in value_errors])
        
        return errors
    
    def _sanitize_data(self, data: Any, data_type: str) -> Any:
        """Sanitize data based on type and level."""
        if not isinstance(data, str):
            return data
        
        sanitized = data
        
        # Basic sanitization
        if self.validation_level >= ValidationLevel.STANDARD:
            # Remove null bytes
            sanitized = sanitized.replace('\x00', '')
            
            # Normalize whitespace
            sanitized = ' '.join(sanitized.split())
            
            # Remove control characters (except newline and tab)
            control_chars = ''.join(chr(i) for i in range(32) if i not in (9, 10, 13))
            sanitized = sanitized.translate(str.maketrans('', '', control_chars))
        
        # Strict sanitization
        if self.validation_level == ValidationLevel.STRICT:
            # HTML escape
            import html
            sanitized = html.escape(sanitized)
            
            # URL encode if needed
            if data_type == "url":
                sanitized = urllib.parse.quote(sanitized, safe=':/?#[]@!$&\'()*+,;=')
        
        return sanitized
    
    def _detect_pii(self, data: str) -> List[str]:
        """Detect PII in data."""
        pii_found = []
        
        for pii_type, pattern in self.PII_PATTERNS.items():
            if pattern.search(data):
                pii_found.append(pii_type)
        
        return pii_found
    
    def validate_template_context(
        self,
        context: Dict[str, Any],
        required_vars: List[str],
        optional_vars: Optional[List[str]] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate template context variables.
        
        Args:
            context: Template context dictionary
            required_vars: Required variable names
            optional_vars: Optional variable names
            
        Returns:
            Tuple of (is_valid, errors)
        """
        errors = []
        
        # Check required variables
        missing_vars = set(required_vars) - set(context.keys())
        if missing_vars:
            errors.append(f"Missing required variables: {', '.join(missing_vars)}")
        
        # Validate each variable
        for var_name, var_value in context.items():
            # Skip validation in NONE mode
            if self.validation_level == ValidationLevel.NONE:
                continue
            
            # Type validation
            if var_value is None and var_name in required_vars:
                errors.append(f"Required variable '{var_name}' cannot be None")
            
            # Content validation
            if isinstance(var_value, str):
                is_valid, _, var_errors = self.validate(var_value, "template_variable")
                if not is_valid:
                    errors.extend([f"{var_name}: {e}" for e in var_errors])
        
        return len(errors) == 0, errors
    
    def validate_file_path(
        self,
        path: Union[str, Path],
        must_exist: bool = False,
        allowed_extensions: Optional[List[str]] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate file path.
        
        Args:
            path: File path to validate
            must_exist: Whether file must exist
            allowed_extensions: List of allowed file extensions
            
        Returns:
            Tuple of (is_valid, errors)
        """
        errors = []
        path = Path(path)
        
        # Path traversal check
        try:
            resolved = path.resolve()
            if '..' in str(path):
                errors.append("Path traversal detected")
        except Exception as e:
            errors.append(f"Invalid path: {e}")
            return False, errors
        
        # Existence check
        if must_exist and not path.exists():
            errors.append(f"File does not exist: {path}")
        
        # Extension check
        if allowed_extensions:
            if path.suffix not in allowed_extensions:
                errors.append(f"File extension not allowed: {path.suffix}")
        
        # Security checks in strict mode
        if self.validation_level == ValidationLevel.STRICT:
            # Check for suspicious filenames
            suspicious_names = ['passwd', 'shadow', 'hosts', '.env', '.git']
            if any(name in str(path).lower() for name in suspicious_names):
                errors.append("Suspicious filename detected")
        
        return len(errors) == 0, errors
    
    def validate_metadata(
        self,
        metadata: Dict[str, Any],
        required_fields: Optional[List[str]] = None,
        allowed_fields: Optional[List[str]] = None
    ) -> Tuple[bool, Dict[str, Any], List[str]]:
        """
        Validate and sanitize metadata.
        
        Args:
            metadata: Metadata dictionary
            required_fields: Required field names
            allowed_fields: Allowed field names (None = all allowed)
            
        Returns:
            Tuple of (is_valid, sanitized_metadata, errors)
        """
        errors = []
        sanitized = {}
        
        # Check required fields
        if required_fields:
            missing = set(required_fields) - set(metadata.keys())
            if missing:
                errors.append(f"Missing required fields: {', '.join(missing)}")
        
        # Process each field
        for key, value in metadata.items():
            # Check allowed fields
            if allowed_fields and key not in allowed_fields:
                if self.validation_level == ValidationLevel.STRICT:
                    errors.append(f"Field not allowed: {key}")
                    continue
                else:
                    logger.warning(f"Unknown metadata field: {key}")
            
            # Validate and sanitize
            key_valid, sanitized_key, key_errors = self.validate(key, "metadata_key")
            if not key_valid:
                errors.extend(key_errors)
                continue
            
            value_valid, sanitized_value, value_errors = self.validate(value, "metadata_value")
            if not value_valid:
                errors.extend([f"{key}: {e}" for e in value_errors])
                continue
            
            sanitized[sanitized_key] = sanitized_value
        
        return len(errors) == 0, sanitized, errors
    
    # Backward compatibility methods
    
    def validate_input(self, data: Any, data_type: str = "generic") -> bool:
        """Backward compatible validation method."""
        is_valid, _, _ = self.validate(data, data_type)
        return is_valid
    
    def sanitize(self, data: Any, data_type: str = "generic") -> Any:
        """Backward compatible sanitization method."""
        _, sanitized, _ = self.validate(data, data_type, sanitize=True)
        return sanitized
    
    def check_security(self, data: str) -> List[str]:
        """Backward compatible security check."""
        _, _, errors = self.validate(data, "content")
        return errors


# Backward compatibility aliases
Validator = UnifiedValidator  # Alias for basic validator compatibility
SecurityValidator = UnifiedValidator  # Alias for security validator compatibility


def create_validator(
    validation_level: Union[str, ValidationLevel] = "standard",
    **kwargs
) -> UnifiedValidator:
    """
    Factory function to create a validator with specified level.
    
    Args:
        validation_level: Validation level (none/basic/standard/strict)
        **kwargs: Additional configuration options
        
    Returns:
        Configured UnifiedValidator instance
    """
    if isinstance(validation_level, str):
        validation_level = ValidationLevel(validation_level.lower())
    
    return UnifiedValidator(validation_level=validation_level, **kwargs)