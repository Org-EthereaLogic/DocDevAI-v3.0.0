"""
Unified security module for DevDocAI.

Consolidates encryption, validation, and security features from M001, M002, and M003.
Provides a single source of truth for all security operations across the system.
"""

import os
import secrets
import logging
import hashlib
import json
import base64
import re
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, Union, List
from datetime import datetime, timedelta
from functools import wraps, lru_cache
from contextlib import contextmanager
import threading

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from argon2 import PasswordHasher, Parameters, Type
from argon2.exceptions import VerifyMismatchError

logger = logging.getLogger(__name__)


# ============================================================================
# ENCRYPTION AND KEY MANAGEMENT
# ============================================================================

class EncryptionManager:
    """
    Unified encryption manager for all modules.
    
    Consolidates encryption functionality from M001 and M002,
    providing consistent encryption across the system.
    """
    
    # Argon2id parameters (consistent across all modules)
    ARGON2_TIME_COST = 3
    ARGON2_MEMORY_COST = 65536  # 64MB
    ARGON2_PARALLELISM = 4
    ARGON2_HASH_LEN = 32
    ARGON2_SALT_LEN = 16
    
    # AES-256-GCM parameters
    AES_KEY_SIZE = 32  # 256 bits
    AES_NONCE_SIZE = 12  # 96 bits for GCM
    AES_TAG_SIZE = 16  # 128 bits
    
    # PBKDF2 parameters for consistency
    PBKDF2_ITERATIONS = 256000  # OWASP recommended
    
    def __init__(self, key_file: Optional[Path] = None):
        """Initialize encryption manager."""
        self.key_file = key_file or Path.home() / '.devdocai' / 'master.key'
        self.key_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.password_hasher = PasswordHasher(
            time_cost=self.ARGON2_TIME_COST,
            memory_cost=self.ARGON2_MEMORY_COST,
            parallelism=self.ARGON2_PARALLELISM,
            hash_len=self.ARGON2_HASH_LEN,
            salt_len=self.ARGON2_SALT_LEN,
            type=Type.ID
        )
        
        self._master_key: Optional[bytes] = None
        self._key_cache: Dict[str, Tuple[bytes, datetime]] = {}
        self._cache_ttl = timedelta(minutes=30)
        self._lock = threading.Lock()
    
    def derive_key(self, password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """
        Derive encryption key from password using Argon2id.
        
        Args:
            password: User password
            salt: Optional salt (generated if not provided)
            
        Returns:
            Tuple of (derived_key, salt)
        """
        if salt is None:
            salt = secrets.token_bytes(self.ARGON2_SALT_LEN)
        
        # Use PBKDF2 for key derivation (consistent output)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.AES_KEY_SIZE,
            salt=salt,
            iterations=self.PBKDF2_ITERATIONS,
            backend=default_backend()
        )
        key = kdf.derive(password.encode())
        
        return key, salt
    
    def encrypt(self, plaintext: Union[str, bytes], key: Optional[bytes] = None) -> bytes:
        """
        Encrypt data using AES-256-GCM.
        
        Args:
            plaintext: Data to encrypt
            key: Encryption key (uses master key if not provided)
            
        Returns:
            Encrypted bytes (nonce + ciphertext + tag)
        """
        key = key or self._master_key
        if not key:
            raise ValueError("No encryption key available")
        
        # Convert string to bytes if needed
        if isinstance(plaintext, str):
            plaintext = plaintext.encode('utf-8')
        
        # Generate nonce
        nonce = secrets.token_bytes(self.AES_NONCE_SIZE)
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(nonce),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        # Encrypt
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        
        # Return nonce + ciphertext + tag
        return nonce + ciphertext + encryptor.tag
    
    def decrypt(self, ciphertext: bytes, key: Optional[bytes] = None) -> bytes:
        """
        Decrypt data using AES-256-GCM.
        
        Args:
            ciphertext: Encrypted data (nonce + ciphertext + tag)
            key: Decryption key (uses master key if not provided)
            
        Returns:
            Decrypted bytes
        """
        key = key or self._master_key
        if not key:
            raise ValueError("No decryption key available")
        
        # Extract components
        nonce = ciphertext[:self.AES_NONCE_SIZE]
        tag = ciphertext[-self.AES_TAG_SIZE:]
        actual_ciphertext = ciphertext[self.AES_NONCE_SIZE:-self.AES_TAG_SIZE]
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(nonce, tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        # Decrypt
        plaintext = decryptor.update(actual_ciphertext) + decryptor.finalize()
        return plaintext
    
    def encrypt_field(self, value: Any) -> str:
        """
        Encrypt a field value for storage.
        
        Args:
            value: Value to encrypt
            
        Returns:
            Base64-encoded encrypted string
        """
        json_str = json.dumps(value)
        encrypted = self.encrypt(json_str)
        return base64.b64encode(encrypted).decode('utf-8')
    
    def decrypt_field(self, encrypted_value: str) -> Any:
        """
        Decrypt a field value from storage.
        
        Args:
            encrypted_value: Base64-encoded encrypted string
            
        Returns:
            Decrypted value
        """
        encrypted = base64.b64decode(encrypted_value)
        decrypted = self.decrypt(encrypted)
        return json.loads(decrypted.decode('utf-8'))
    
    def set_master_key(self, password: str) -> bool:
        """Set master key from password."""
        try:
            key, salt = self.derive_key(password)
            self._master_key = key
            return True
        except Exception as e:
            logger.error(f"Failed to set master key: {e}")
            return False
    
    def clear_master_key(self):
        """Clear master key from memory."""
        with self._lock:
            self._master_key = None
            self._key_cache.clear()


# ============================================================================
# INPUT VALIDATION AND SANITIZATION
# ============================================================================

class InputValidator:
    """
    Unified input validation for all modules.
    
    Consolidates validation logic from M003 with enhancements.
    """
    
    # Validation patterns
    PATTERNS = {
        'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
        'url': re.compile(r'^https?://[^\s/$.?#].[^\s]*$'),
        'path': re.compile(r'^[a-zA-Z0-9_\-./\\]+$'),
        'alphanumeric': re.compile(r'^[a-zA-Z0-9]+$'),
        'uuid': re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'),
    }
    
    # Size limits
    MAX_STRING_LENGTH = 10000
    MAX_ARRAY_LENGTH = 1000
    MAX_OBJECT_DEPTH = 10
    
    @classmethod
    def validate_string(cls, value: str, pattern: Optional[str] = None,
                       min_length: int = 0, max_length: Optional[int] = None) -> bool:
        """Validate string input."""
        if not isinstance(value, str):
            return False
        
        # Check length
        if len(value) < min_length:
            return False
        if max_length and len(value) > max_length:
            return False
        if len(value) > cls.MAX_STRING_LENGTH:
            return False
        
        # Check pattern if provided
        if pattern:
            if pattern in cls.PATTERNS:
                return bool(cls.PATTERNS[pattern].match(value))
            else:
                try:
                    return bool(re.match(pattern, value))
                except re.error:
                    return False
        
        return True
    
    @classmethod
    def sanitize_string(cls, value: str, max_length: Optional[int] = None) -> str:
        """Sanitize string input."""
        if not isinstance(value, str):
            value = str(value)
        
        # Remove control characters
        value = ''.join(char for char in value if ord(char) >= 32 or char in '\n\r\t')
        
        # Truncate if needed
        if max_length:
            value = value[:max_length]
        elif len(value) > cls.MAX_STRING_LENGTH:
            value = value[:cls.MAX_STRING_LENGTH]
        
        return value
    
    @classmethod
    def validate_dict(cls, value: Dict, required_keys: Optional[List[str]] = None,
                     allowed_keys: Optional[List[str]] = None) -> bool:
        """Validate dictionary input."""
        if not isinstance(value, dict):
            return False
        
        # Check required keys
        if required_keys:
            for key in required_keys:
                if key not in value:
                    return False
        
        # Check allowed keys
        if allowed_keys:
            for key in value:
                if key not in allowed_keys:
                    return False
        
        return True
    
    @classmethod
    def sanitize_dict(cls, value: Dict, allowed_keys: Optional[List[str]] = None) -> Dict:
        """Sanitize dictionary input."""
        if not isinstance(value, dict):
            return {}
        
        # Filter to allowed keys
        if allowed_keys:
            value = {k: v for k, v in value.items() if k in allowed_keys}
        
        # Recursively sanitize values
        sanitized = {}
        for key, val in value.items():
            if isinstance(val, str):
                sanitized[key] = cls.sanitize_string(val)
            elif isinstance(val, dict):
                sanitized[key] = cls.sanitize_dict(val)
            elif isinstance(val, list):
                sanitized[key] = cls.sanitize_list(val)
            else:
                sanitized[key] = val
        
        return sanitized
    
    @classmethod
    def sanitize_list(cls, value: List, max_length: Optional[int] = None) -> List:
        """Sanitize list input."""
        if not isinstance(value, list):
            return []
        
        # Truncate if needed
        if max_length:
            value = value[:max_length]
        elif len(value) > cls.MAX_ARRAY_LENGTH:
            value = value[:cls.MAX_ARRAY_LENGTH]
        
        # Recursively sanitize items
        sanitized = []
        for item in value:
            if isinstance(item, str):
                sanitized.append(cls.sanitize_string(item))
            elif isinstance(item, dict):
                sanitized.append(cls.sanitize_dict(item))
            elif isinstance(item, list):
                sanitized.append(cls.sanitize_list(item))
            else:
                sanitized.append(item)
        
        return sanitized


# ============================================================================
# PII DETECTION AND MASKING
# ============================================================================

class PIIDetector:
    """
    PII detection and masking utilities.
    
    Extracted from M002 for use across all modules.
    """
    
    # PII patterns
    PII_PATTERNS = {
        'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
        'credit_card': re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'),
        'phone': re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
        'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        'ip_address': re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),
    }
    
    @classmethod
    def detect_pii(cls, text: str) -> Dict[str, List[str]]:
        """
        Detect PII in text.
        
        Args:
            text: Text to scan
            
        Returns:
            Dictionary of PII type to list of found values
        """
        findings = {}
        
        for pii_type, pattern in cls.PII_PATTERNS.items():
            matches = pattern.findall(text)
            if matches:
                findings[pii_type] = matches
        
        return findings
    
    @classmethod
    def mask_pii(cls, text: str, mask_char: str = '*') -> str:
        """
        Mask PII in text.
        
        Args:
            text: Text to mask
            mask_char: Character to use for masking
            
        Returns:
            Text with PII masked
        """
        masked_text = text
        
        for pii_type, pattern in cls.PII_PATTERNS.items():
            def mask_match(match):
                value = match.group()
                if pii_type == 'email':
                    # Keep first letter and domain
                    parts = value.split('@')
                    if len(parts) == 2:
                        return parts[0][0] + mask_char * (len(parts[0]) - 1) + '@' + parts[1]
                elif pii_type in ['ssn', 'credit_card']:
                    # Keep last 4 digits
                    return mask_char * (len(value) - 4) + value[-4:]
                else:
                    # Mask everything
                    return mask_char * len(value)
                return value
            
            masked_text = pattern.sub(mask_match, masked_text)
        
        return masked_text


# ============================================================================
# RATE LIMITING
# ============================================================================

class RateLimiter:
    """
    Rate limiting functionality.
    
    Extracted from M003 for system-wide use.
    """
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[datetime]] = {}
        self.lock = threading.Lock()
    
    def check_rate_limit(self, identifier: str) -> Tuple[bool, Optional[str]]:
        """
        Check if request is within rate limit.
        
        Args:
            identifier: Client/user identifier
            
        Returns:
            Tuple of (allowed, reason if denied)
        """
        with self.lock:
            now = datetime.now()
            
            # Initialize or clean old requests
            if identifier not in self.requests:
                self.requests[identifier] = []
            
            # Remove old requests outside window
            cutoff = now - timedelta(seconds=self.window_seconds)
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier]
                if req_time > cutoff
            ]
            
            # Check limit
            if len(self.requests[identifier]) >= self.max_requests:
                return False, f"Rate limit exceeded: {self.max_requests} requests per {self.window_seconds} seconds"
            
            # Add current request
            self.requests[identifier].append(now)
            return True, None
    
    def reset(self, identifier: Optional[str] = None):
        """Reset rate limit tracking."""
        with self.lock:
            if identifier:
                self.requests.pop(identifier, None)
            else:
                self.requests.clear()


# ============================================================================
# SECURE OPERATIONS DECORATORS
# ============================================================================

def secure_operation(validate_input: bool = True,
                    encrypt_output: bool = False,
                    rate_limit: Optional[RateLimiter] = None):
    """
    Decorator for securing operations.
    
    Args:
        validate_input: Whether to validate input
        encrypt_output: Whether to encrypt output
        rate_limit: Rate limiter instance
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Rate limiting
            if rate_limit:
                identifier = kwargs.get('client_id', 'default')
                allowed, reason = rate_limit.check_rate_limit(identifier)
                if not allowed:
                    raise PermissionError(reason)
            
            # Input validation
            if validate_input:
                # Validate string arguments
                for i, arg in enumerate(args):
                    if isinstance(arg, str):
                        args = list(args)
                        args[i] = InputValidator.sanitize_string(arg)
                        args = tuple(args)
                
                # Validate keyword arguments
                for key, value in kwargs.items():
                    if isinstance(value, str):
                        kwargs[key] = InputValidator.sanitize_string(value)
                    elif isinstance(value, dict):
                        kwargs[key] = InputValidator.sanitize_dict(value)
                    elif isinstance(value, list):
                        kwargs[key] = InputValidator.sanitize_list(value)
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Encrypt output if requested
            if encrypt_output and result:
                encryption_manager = EncryptionManager()
                if isinstance(result, (str, bytes)):
                    result = encryption_manager.encrypt(result)
                elif isinstance(result, dict):
                    result = encryption_manager.encrypt_field(result)
            
            return result
        
        return wrapper
    return decorator


# ============================================================================
# AUDIT LOGGING
# ============================================================================

class AuditLogger:
    """
    Centralized audit logging.
    
    Provides consistent security event logging across all modules.
    """
    
    def __init__(self, log_file: Optional[Path] = None):
        """Initialize audit logger."""
        self.log_file = log_file or Path.home() / '.devdocai' / 'audit.log'
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Configure logger
        self.logger = logging.getLogger('devdocai.audit')
        self.logger.setLevel(logging.INFO)
        
        # File handler
        handler = logging.FileHandler(self.log_file)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)
    
    def log_event(self, event_type: str, details: Dict[str, Any]):
        """Log security event."""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'details': details
        }
        self.logger.info(json.dumps(entry))
    
    def log_access(self, user: str, resource: str, action: str, success: bool):
        """Log access attempt."""
        self.log_event('access', {
            'user': user,
            'resource': resource,
            'action': action,
            'success': success
        })
    
    def log_encryption(self, operation: str, data_type: str):
        """Log encryption operation."""
        self.log_event('encryption', {
            'operation': operation,
            'data_type': data_type
        })
    
    def log_validation_failure(self, data_type: str, reason: str):
        """Log validation failure."""
        self.log_event('validation_failure', {
            'data_type': data_type,
            'reason': reason
        })


# ============================================================================
# GLOBAL INSTANCES AND HELPERS
# ============================================================================

# Global instances for convenience
_encryption_manager = None
_rate_limiter = None
_audit_logger = None


def get_encryption_manager() -> EncryptionManager:
    """Get global encryption manager instance."""
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()
    return _encryption_manager


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def get_audit_logger() -> AuditLogger:
    """Get global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


# ============================================================================
# SECURITY CONTEXT MANAGER
# ============================================================================

@contextmanager
def security_context(operation: str, user: Optional[str] = None):
    """
    Context manager for secure operations.
    
    Usage:
        with security_context('data_processing', user='john'):
            # Perform secure operations
            pass
    """
    audit_logger = get_audit_logger()
    
    # Log operation start
    audit_logger.log_event('operation_start', {
        'operation': operation,
        'user': user or 'system'
    })
    
    try:
        yield
        
        # Log success
        audit_logger.log_event('operation_success', {
            'operation': operation,
            'user': user or 'system'
        })
        
    except Exception as e:
        # Log failure
        audit_logger.log_event('operation_failure', {
            'operation': operation,
            'user': user or 'system',
            'error': str(e)
        })
        raise
    
    finally:
        # Clean up sensitive data
        import gc
        gc.collect()


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'EncryptionManager',
    'InputValidator',
    'PIIDetector',
    'RateLimiter',
    'AuditLogger',
    'secure_operation',
    'security_context',
    'get_encryption_manager',
    'get_rate_limiter',
    'get_audit_logger'
]