"""
M004 Document Generator - Enhanced security validation utilities.

Provides comprehensive validation for template inputs, configuration, 
and document generation parameters with security hardening.
"""

import re
import html
import logging
import json
import urllib.parse
from typing import Dict, List, Optional, Any, Union, Set
from datetime import datetime
from pathlib import Path
import hashlib
import unicodedata

from ...common.errors import DevDocAIError
from ...common.logging import get_logger
from ...common.security import InputValidator as BaseValidator, PIIDetector, AuditLogger

logger = get_logger(__name__)


class ValidationError(DevDocAIError):
    """Exception raised for validation errors."""
    pass


class InputValidator:
    """
    Validates inputs for document generation.
    
    Features:
    - Template variable validation
    - Data type validation
    - Format validation (URLs, emails, dates)
    - Content validation (length, characters)
    - Security validation (XSS, injection prevention)
    """
    
    def __init__(self):
        """Initialize the input validator."""
        # Common regex patterns
        self.patterns = {
            'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
            'url': re.compile(r'^https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?$'),
            'version': re.compile(r'^\d+\.\d+\.\d+(?:-[a-zA-Z0-9]+)?$'),
            'slug': re.compile(r'^[a-z0-9-]+$'),
            'identifier': re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$'),
            'safe_text': re.compile(r'^[a-zA-Z0-9\s\-_.(),!?]+$')
        }
        
        # XSS patterns to detect
        self.xss_patterns = [
            re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
            re.compile(r'javascript:', re.IGNORECASE),
            re.compile(r'on\w+\s*=', re.IGNORECASE),
            re.compile(r'<iframe[^>]*>', re.IGNORECASE),
            re.compile(r'<object[^>]*>', re.IGNORECASE),
            re.compile(r'<embed[^>]*>', re.IGNORECASE)
        ]
        
        logger.debug("InputValidator initialized")
    
    def validate_template_inputs(
        self, 
        inputs: Dict[str, Any], 
        required_variables: List[str]
    ) -> List[str]:
        """
        Validate inputs for a template.
        
        Args:
            inputs: Input values to validate
            required_variables: List of required variable names
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        try:
            # Check required variables
            for var in required_variables:
                if var not in inputs:
                    errors.append(f"Required variable '{var}' is missing")
                elif inputs[var] is None:
                    errors.append(f"Required variable '{var}' cannot be None")
                elif isinstance(inputs[var], str) and not inputs[var].strip():
                    errors.append(f"Required variable '{var}' cannot be empty")
            
            # Validate each input
            for key, value in inputs.items():
                field_errors = self.validate_field(key, value)
                errors.extend(field_errors)
            
            logger.debug(f"Template input validation completed with {len(errors)} errors")
            
        except Exception as e:
            logger.error(f"Input validation failed: {e}")
            errors.append(f"Validation error: {str(e)}")
        
        return errors
    
    def validate_field(self, field_name: str, value: Any) -> List[str]:
        """
        Validate a single input field based on its name and value.
        
        Args:
            field_name: Name of the field (used for type inference)
            value: Value to validate
            
        Returns:
            List of validation error messages for this field
        """
        errors = []
        
        if value is None:
            return errors  # None values are handled by required field validation
        
        # Convert to string for text-based validations
        str_value = str(value)
        
        # Field-specific validations based on name patterns
        if any(keyword in field_name.lower() for keyword in ['email', 'mail']):
            errors.extend(self._validate_email(str_value, field_name))
        
        elif any(keyword in field_name.lower() for keyword in ['url', 'link', 'website']):
            errors.extend(self._validate_url(str_value, field_name))
        
        elif any(keyword in field_name.lower() for keyword in ['version']):
            errors.extend(self._validate_version(str_value, field_name))
        
        elif any(keyword in field_name.lower() for keyword in ['date']):
            errors.extend(self._validate_date(str_value, field_name))
        
        elif any(keyword in field_name.lower() for keyword in ['phone', 'tel']):
            errors.extend(self._validate_phone(str_value, field_name))
        
        # General content validation
        errors.extend(self._validate_content_safety(str_value, field_name))
        errors.extend(self._validate_length(str_value, field_name))
        
        return errors
    
    def validate_generation_config(self, config: Dict[str, Any]) -> List[str]:
        """
        Validate document generation configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Validate output format
        output_format = config.get('output_format', 'markdown')
        if output_format not in ['markdown', 'html', 'pdf']:
            errors.append(f"Invalid output format: {output_format}")
        
        # Validate boolean flags
        boolean_fields = ['save_to_storage', 'include_metadata', 'validate_inputs']
        for field in boolean_fields:
            if field in config and not isinstance(config[field], bool):
                errors.append(f"Field '{field}' must be boolean, got {type(config[field]).__name__}")
        
        # Validate version format
        if 'version' in config:
            version_errors = self._validate_version(config['version'], 'version')
            errors.extend(version_errors)
        
        # Validate project name
        if 'project_name' in config:
            project_errors = self._validate_project_name(config['project_name'])
            errors.extend(project_errors)
        
        return errors
    
    def sanitize_input(self, value: str, allow_html: bool = False) -> str:
        """
        Sanitize input value for safe use in templates.
        
        Args:
            value: Input value to sanitize
            allow_html: Whether to allow basic HTML tags
            
        Returns:
            Sanitized value
        """
        if not isinstance(value, str):
            value = str(value)
        
        # Remove or escape potentially dangerous content
        if not allow_html:
            # Escape HTML entities
            value = value.replace('&', '&amp;')
            value = value.replace('<', '&lt;')
            value = value.replace('>', '&gt;')
            value = value.replace('"', '&quot;')
            value = value.replace("'", '&#x27;')
        
        # Remove XSS patterns
        for pattern in self.xss_patterns:
            value = pattern.sub('', value)
        
        # Normalize whitespace
        value = re.sub(r'\s+', ' ', value).strip()
        
        return value
    
    def _validate_email(self, value: str, field_name: str) -> List[str]:
        """Validate email format."""
        if not self.patterns['email'].match(value):
            return [f"Invalid email format for field '{field_name}': {value}"]
        return []
    
    def _validate_url(self, value: str, field_name: str) -> List[str]:
        """Validate URL format."""
        if not self.patterns['url'].match(value):
            return [f"Invalid URL format for field '{field_name}': {value}"]
        return []
    
    def _validate_version(self, value: str, field_name: str) -> List[str]:
        """Validate version format (semantic versioning)."""
        if not self.patterns['version'].match(value):
            return [f"Invalid version format for field '{field_name}': {value}. Expected format: X.Y.Z or X.Y.Z-suffix"]
        return []
    
    def _validate_date(self, value: str, field_name: str) -> List[str]:
        """Validate date format."""
        errors = []
        
        # Try common date formats
        date_formats = ['%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S']
        
        parsed = False
        for fmt in date_formats:
            try:
                datetime.strptime(value, fmt)
                parsed = True
                break
            except ValueError:
                continue
        
        if not parsed:
            errors.append(f"Invalid date format for field '{field_name}': {value}")
        
        return errors
    
    def _validate_phone(self, value: str, field_name: str) -> List[str]:
        """Validate phone number format."""
        # Remove common phone number characters
        cleaned = re.sub(r'[\s\-\(\)\.+]', '', value)
        
        # Check if remaining characters are digits
        if not cleaned.isdigit():
            return [f"Invalid phone number format for field '{field_name}': {value}"]
        
        # Check reasonable length
        if len(cleaned) < 7 or len(cleaned) > 15:
            return [f"Invalid phone number length for field '{field_name}': {value}"]
        
        return []
    
    def _validate_content_safety(self, value: str, field_name: str) -> List[str]:
        """Validate content for security issues."""
        errors = []
        
        # Check for XSS patterns
        for pattern in self.xss_patterns:
            if pattern.search(value):
                errors.append(f"Potentially unsafe content detected in field '{field_name}'")
                break
        
        # Check for SQL injection patterns
        sql_patterns = ['DROP TABLE', 'DELETE FROM', 'INSERT INTO', 'UPDATE SET', '--', ';--', '/*', '*/']
        value_upper = value.upper()
        
        for pattern in sql_patterns:
            if pattern in value_upper:
                errors.append(f"Potentially unsafe SQL content detected in field '{field_name}'")
                break
        
        return errors
    
    def _validate_length(self, value: str, field_name: str) -> List[str]:
        """Validate content length."""
        errors = []
        
        # Maximum length based on field type
        max_lengths = {
            'title': 200,
            'name': 100,
            'author': 100,
            'email': 254,  # RFC 5321 limit
            'url': 2048,
            'phone': 20,
            'version': 20,
            'description': 1000,
            'summary': 500
        }
        
        # Find applicable length limit
        max_length = None
        for key, limit in max_lengths.items():
            if key in field_name.lower():
                max_length = limit
                break
        
        # Default limits
        if max_length is None:
            if len(value) > 10000:  # Very long content
                max_length = 10000
            elif len(value) > 5000:  # Long content
                max_length = 5000
        
        if max_length and len(value) > max_length:
            errors.append(f"Field '{field_name}' exceeds maximum length of {max_length} characters")
        
        return errors
    
    def _validate_project_name(self, project_name: str) -> List[str]:
        """Validate project name format."""
        errors = []
        
        if not project_name or not project_name.strip():
            errors.append("Project name cannot be empty")
            return errors
        
        # Check length
        if len(project_name) > 100:
            errors.append("Project name cannot exceed 100 characters")
        
        # Check for valid characters (letters, numbers, spaces, hyphens, underscores)
        if not re.match(r'^[a-zA-Z0-9\s\-_.]+$', project_name):
            errors.append("Project name contains invalid characters")
        
        return errors