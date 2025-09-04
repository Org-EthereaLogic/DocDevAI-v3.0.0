"""
Secure Logging Module for DocDevAI v3.0.0

Provides automatic PII masking in logs to ensure GDPR/CCPA compliance.
Integrates with existing PIIDetector for comprehensive sensitive data protection.
"""

import logging
import re
import json
from typing import Any, Dict, Optional, Union, List
from functools import lru_cache
from copy import deepcopy
import traceback

# Import the existing PII detector from M002
from devdocai.storage.pii_detector import PIIDetector, PIIDetectionConfig, PIIType


class SecureLogFilter(logging.Filter):
    """
    Logging filter that masks PII in log messages.
    
    This filter intercepts all log records and masks sensitive information
    before they are written to any handler (console, file, etc.).
    """
    
    def __init__(self, pii_detector: Optional[PIIDetector] = None, 
                 mask_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the secure log filter.
        
        Args:
            pii_detector: PIIDetector instance to use for detection
            mask_config: Configuration for masking behavior
        """
        super().__init__()
        
        # Initialize PII detector with comprehensive configuration
        if pii_detector is None:
            config = PIIDetectionConfig(
                enabled_types=set(PIIType),  # Enable all PII types
                min_confidence=0.7,
                mask_character="*",
                preserve_length=True,
                preserve_partial=4  # Show last 4 chars for debugging
            )
            self.pii_detector = PIIDetector(config)
        else:
            self.pii_detector = pii_detector
        
        # Masking configuration
        self.mask_config = mask_config or {
            'mask_emails': True,
            'mask_ssn': True,
            'mask_credit_cards': True,
            'mask_api_keys': True,
            'mask_passwords': True,
            'mask_phone': True,
            'preserve_domain': True,  # Show email domain for debugging
            'show_type': True  # Show what type of PII was masked
        }
        
        # Additional patterns for common sensitive data
        self.additional_patterns = self._compile_additional_patterns()
        
    def _compile_additional_patterns(self) -> Dict[str, re.Pattern]:
        """Compile additional regex patterns for sensitive data."""
        return {
            # API Keys and Tokens
            'api_key': re.compile(
                r'(api[_\-]?key|apikey|api_secret|secret[_\-]?key|access[_\-]?token|'
                r'auth[_\-]?token|bearer)\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{20,})["\']?',
                re.IGNORECASE
            ),
            # Password patterns
            'password': re.compile(
                r'(password|passwd|pwd|pass)\s*[:=]\s*["\']?([^\s"\']+)["\']?',
                re.IGNORECASE
            ),
            # Environment variables with secrets
            'env_secret': re.compile(
                r'(SECRET|KEY|TOKEN|PASSWORD|PASSWD|CRED|CREDENTIAL|AUTH)[_A-Z]*\s*=\s*["\']?([^\s"\']+)["\']?',
                re.IGNORECASE
            ),
            # Database connection strings
            'db_connection': re.compile(
                r'(mongodb|postgresql|mysql|redis|mssql|oracle):\/\/[^:]+:([^@]+)@',
                re.IGNORECASE
            ),
            # JWT tokens
            'jwt': re.compile(r'eyJ[a-zA-Z0-9_\-]+\.eyJ[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+'),
            # AWS keys
            'aws_access': re.compile(r'AKIA[0-9A-Z]{16}'),
            'aws_secret': re.compile(r'[a-zA-Z0-9/+=]{40}'),
            # Private keys
            'private_key': re.compile(
                r'-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----.*?-----END (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----',
                re.DOTALL
            )
        }
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter and mask PII in log records.
        
        Args:
            record: The log record to filter
            
        Returns:
            True to allow the record through (always True, we just modify it)
        """
        try:
            # Handle messages with format arguments
            # Convert message and args to string early to ensure masking happens
            if hasattr(record, 'msg') and hasattr(record, 'args'):
                # Format the message with args first if args exist
                if record.args:
                    try:
                        # Format message with args
                        if isinstance(record.args, dict):
                            formatted_msg = str(record.msg) % self._mask_dict(record.args)
                        else:
                            masked_args = tuple(
                                self._mask_sensitive_data(str(arg)) if isinstance(arg, str)
                                else self._mask_dict(arg) if isinstance(arg, dict)
                                else str(arg)
                                for arg in record.args
                            )
                            formatted_msg = str(record.msg) % masked_args
                        # Set the formatted and masked message
                        record.msg = self._mask_sensitive_data(formatted_msg)
                        record.args = None  # Clear args since we've already formatted
                    except (TypeError, ValueError):
                        # If formatting fails, mask separately
                        record.msg = self._mask_sensitive_data(str(record.msg))
                        if isinstance(record.args, dict):
                            record.args = self._mask_dict(record.args)
                        elif isinstance(record.args, (list, tuple)):
                            record.args = tuple(self._mask_sensitive_data(str(arg)) for arg in record.args)
                else:
                    # No args, just mask the message
                    record.msg = self._mask_sensitive_data(str(record.msg))
            elif hasattr(record, 'msg'):
                # Just mask the message if no args
                record.msg = self._mask_sensitive_data(str(record.msg))
            
            # Mask extra fields
            for key in record.__dict__:
                if key not in ('name', 'msg', 'args', 'created', 'filename', 'funcName', 
                              'levelname', 'levelno', 'lineno', 'module', 'msecs', 
                              'pathname', 'process', 'processName', 'relativeCreated', 
                              'thread', 'threadName'):
                    value = getattr(record, key)
                    if isinstance(value, str):
                        setattr(record, key, self._mask_sensitive_data(value))
                    elif isinstance(value, dict):
                        setattr(record, key, self._mask_dict(value))
            
            # Mask exception info if present
            if record.exc_info:
                record.exc_text = self._mask_sensitive_data(
                    traceback.format_exception(*record.exc_info) if isinstance(record.exc_info, tuple) 
                    else str(record.exc_info)
                )
                record.exc_info = None  # Clear original to prevent double processing
                
        except Exception as e:
            # If masking fails, log the error but don't block the log
            # This ensures logging continues even if masking has issues
            record.msg = f"[MASKING ERROR: {e}] {record.msg}"
        
        return True
    
    def _mask_sensitive_data(self, text: str) -> str:
        """
        Mask sensitive data in text.
        
        Args:
            text: Text to mask
            
        Returns:
            Text with PII masked
        """
        if not text:
            return text
        
        # First check if this looks like a dictionary string representation
        # This handles f-string formatted dictionaries
        if '{' in text and '}' in text and ':' in text:
            # Try to mask dictionary-like content in strings
            # Pattern for key-value pairs in string representation of dicts
            dict_pattern = re.compile(r"'(password|passwd|pwd|secret|token|api_key|apikey|auth|credential|private_key|access_token|refresh_token|client_secret)':\s*'([^']+)'", re.IGNORECASE)
            text = dict_pattern.sub(lambda m: f"'{m.group(1)}': '<MASKED_SENSITIVE_VALUE>'", text)
        
        # First, use PIIDetector for comprehensive detection
        try:
            detection_result = self.pii_detector.detect(text)
            if detection_result and detection_result.get('has_pii'):
                # Use the masked text from PIIDetector
                text = detection_result.get('masked_text', text)
        except Exception:
            # Continue with additional patterns if PIIDetector fails
            pass
        
        # Apply additional patterns for extra security
        for pattern_name, pattern in self.additional_patterns.items():
            if pattern_name == 'api_key' and self.mask_config.get('mask_api_keys', True):
                text = pattern.sub(lambda m: f"{m.group(1)}=<MASKED_API_KEY>", text)
            elif pattern_name == 'password' and self.mask_config.get('mask_passwords', True):
                text = pattern.sub(lambda m: f"{m.group(1)}=<MASKED_PASSWORD>", text)
            elif pattern_name == 'env_secret':
                text = pattern.sub(lambda m: f"{m.group(1)}=<MASKED_SECRET>", text)
            elif pattern_name == 'db_connection':
                text = pattern.sub(lambda m: f"{m.group(1)}://***:***@", text)
            elif pattern_name == 'jwt':
                text = pattern.sub("<MASKED_JWT_TOKEN>", text)
            elif pattern_name == 'aws_access':
                text = pattern.sub("AKIA<MASKED_AWS_KEY>", text)
            elif pattern_name == 'private_key':
                text = pattern.sub("-----BEGIN PRIVATE KEY-----<MASKED>-----END PRIVATE KEY-----", text)
        
        # Quick patterns for common sensitive data
        if self.mask_config.get('mask_emails', True) and '@' in text:
            # Preserve domain for debugging but mask local part
            text = re.sub(
                r'\b([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',
                lambda m: f"***@{m.group(2)}" if self.mask_config.get('preserve_domain', True) 
                else "<MASKED_EMAIL>",
                text
            )
        
        # Mask SSNs with pattern
        if self.mask_config.get('mask_ssn', True):
            text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', 'XXX-XX-<MASKED_SSN>', text)
            text = re.sub(r'\b\d{3}\s\d{2}\s\d{4}\b', 'XXX XX <MASKED_SSN>', text)
        
        # Mask credit card patterns
        if self.mask_config.get('mask_credit_cards', True):
            text = re.sub(
                r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b',
                lambda m: f"****-****-****-{m.group()[-4:]}" if len(m.group()) >= 4 
                else "<MASKED_CARD>",
                text
            )
        
        # Mask phone numbers
        if self.mask_config.get('mask_phone', True):
            text = re.sub(
                r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
                '<MASKED_PHONE>',
                text
            )
        
        return text
    
    def _mask_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively mask sensitive data in dictionaries.
        
        Args:
            data: Dictionary to mask
            
        Returns:
            Dictionary with masked values
        """
        masked = {}
        sensitive_keys = {
            'password', 'passwd', 'pwd', 'secret', 'token', 'api_key', 'apikey',
            'auth', 'authorization', 'credential', 'private_key', 'access_token',
            'refresh_token', 'client_secret', 'aws_secret_access_key', 'stripe_key'
        }
        
        for key, value in data.items():
            # Check if key name indicates sensitive data
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                masked[key] = '<MASKED_SENSITIVE_VALUE>'
            elif isinstance(value, str):
                masked[key] = self._mask_sensitive_data(value)
            elif isinstance(value, dict):
                masked[key] = self._mask_dict(value)
            elif isinstance(value, (list, tuple)):
                masked[key] = [
                    self._mask_sensitive_data(str(item)) if isinstance(item, str) 
                    else self._mask_dict(item) if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                masked[key] = value
        
        return masked


class SecureLogger:
    """
    A secure logger that automatically masks PII in all log messages.
    
    This is a drop-in replacement for standard Python loggers with automatic
    PII masking to ensure GDPR/CCPA compliance.
    """
    
    _filter = None  # Shared filter instance
    _initialized = False
    
    @classmethod
    def setup_secure_logging(cls, 
                            root_logger: bool = True,
                            pii_detector: Optional[PIIDetector] = None,
                            mask_config: Optional[Dict[str, Any]] = None) -> None:
        """
        Setup secure logging for the entire application.
        
        Args:
            root_logger: If True, apply to root logger (affects all loggers)
            pii_detector: Custom PIIDetector instance
            mask_config: Custom masking configuration
        """
        if cls._initialized:
            return
        
        # Create the secure filter
        cls._filter = SecureLogFilter(pii_detector, mask_config)
        
        # Apply to root logger or specific loggers
        if root_logger:
            # Apply to root logger - affects all loggers
            root = logging.getLogger()
            root.addFilter(cls._filter)
        
        # Also apply to common DocDevAI loggers
        for logger_name in ['devdocai', 'devdocai.core', 'devdocai.storage', 
                           'devdocai.security', 'devdocai.llm_adapter']:
            logger = logging.getLogger(logger_name)
            logger.addFilter(cls._filter)
        
        cls._initialized = True
        
        # Log that secure logging is enabled (this will also be masked!)
        logger = logging.getLogger('devdocai.security')
        logger.info("Secure logging initialized - PII masking enabled")
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get a logger with automatic PII masking.
        
        Args:
            name: Logger name
            
        Returns:
            Logger instance with PII masking filter
        """
        # Ensure secure logging is setup
        if not cls._initialized:
            cls.setup_secure_logging()
        
        logger = logging.getLogger(name)
        
        # Ensure our filter is attached
        if cls._filter and cls._filter not in logger.filters:
            logger.addFilter(cls._filter)
        
        return logger
    
    @classmethod
    def mask_value(cls, value: Any) -> str:
        """
        Manually mask a value for logging.
        
        Args:
            value: Value to mask
            
        Returns:
            Masked string representation
        """
        if not cls._filter:
            cls._filter = SecureLogFilter()
        
        if isinstance(value, str):
            return cls._filter._mask_sensitive_data(value)
        elif isinstance(value, dict):
            return str(cls._filter._mask_dict(value))
        else:
            return cls._filter._mask_sensitive_data(str(value))


# Convenience function for getting secure loggers
def get_secure_logger(name: str) -> logging.Logger:
    """
    Get a logger with automatic PII masking.
    
    Args:
        name: Logger name
        
    Returns:
        Secure logger instance
    """
    return SecureLogger.get_logger(name)


# Auto-initialize secure logging when module is imported
SecureLogger.setup_secure_logging()