"""
Input validation and sanitization for MIAIR Engine security.

Provides comprehensive validation to prevent injection attacks, resource exhaustion,
and malicious input processing.
"""

import re
import html
import logging
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
import unicodedata
import hashlib
from functools import wraps
import time

logger = logging.getLogger(__name__)


@dataclass
class ValidationConfig:
    """Configuration for input validation."""
    # Size limits
    max_document_size: int = 10 * 1024 * 1024  # 10MB
    max_batch_size: int = 100
    max_string_length: int = 1_000_000
    max_metadata_size: int = 10 * 1024  # 10KB
    
    # Complexity limits
    max_word_count: int = 100_000
    max_line_count: int = 10_000
    min_entropy_threshold: float = 0.1  # Detect non-text data
    max_entropy_threshold: float = 0.95  # Detect random data
    
    # Pattern limits
    max_pattern_count: int = 1000
    max_url_count: int = 100
    max_code_block_size: int = 50_000
    
    # Timeout limits
    validation_timeout: float = 5.0
    
    # Security settings
    allow_html: bool = False
    allow_scripts: bool = False
    allow_urls: bool = True
    strict_mode: bool = True


class ValidationError(Exception):
    """Base exception for validation errors."""
    pass


class InputSizeError(ValidationError):
    """Input exceeds size limits."""
    pass


class MaliciousInputError(ValidationError):
    """Input contains potentially malicious content."""
    pass


class EncodingError(ValidationError):
    """Input has encoding issues."""
    pass


class ComplexityError(ValidationError):
    """Input exceeds complexity limits."""
    pass


class InputValidator:
    """
    Comprehensive input validation for MIAIR Engine.
    
    Prevents:
    - Injection attacks (SQL, XSS, command injection)
    - Resource exhaustion (size, complexity limits)
    - Malformed input (encoding, format issues)
    - Algorithmic complexity attacks
    """
    
    # Malicious patterns
    INJECTION_PATTERNS = [
        # SQL Injection
        r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION|FROM|WHERE)\b)',
        r'(--|#|\/\*|\*\/|;|\||&&|\|\|)',
        r'(\bOR\b\s+\d+\s*=\s*\d+|\bAND\b\s+\d+\s*=\s*\d+)',
        
        # XSS/Script Injection
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe[^>]*>',
        
        # Command Injection
        r'(\$\(.*?\)|\`.*?\`)',
        r'(;|\||&&|>|<|\$)',
        r'(\/bin\/|\/usr\/bin\/|cmd\.exe|powershell)',
        
        # Path Traversal
        r'(\.\.[\/\\])',
        r'(\/etc\/passwd|\/etc\/shadow|C:\\Windows\\System32)',
    ]
    
    # Suspicious entropy patterns
    HIGH_ENTROPY_THRESHOLD = 7.5  # Bits per character
    LOW_ENTROPY_THRESHOLD = 1.0
    
    def __init__(self, config: Optional[ValidationConfig] = None):
        """Initialize validator with configuration."""
        self.config = config or ValidationConfig()
        self._compile_patterns()
        self._init_metrics()
    
    def _compile_patterns(self):
        """Compile regex patterns for efficiency."""
        flags = re.IGNORECASE | re.MULTILINE | re.DOTALL
        self.injection_regex = [
            re.compile(pattern, flags) for pattern in self.INJECTION_PATTERNS
        ]
    
    def _init_metrics(self):
        """Initialize validation metrics."""
        self.validation_count = 0
        self.rejection_count = 0
        self.validation_times = []
    
    def validate_document(self, 
                         content: Union[str, bytes],
                         metadata: Optional[Dict] = None,
                         document_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate document content and metadata.
        
        Returns:
            Dict with validation results and sanitized content
            
        Raises:
            ValidationError: If content fails validation
        """
        start_time = time.perf_counter()
        self.validation_count += 1
        
        try:
            # Convert bytes to string if needed
            if isinstance(content, bytes):
                content = self._validate_encoding(content)
            
            # Size validation
            self._validate_size(content, metadata)
            
            # Encoding and format validation
            content = self._validate_text_format(content)
            
            # Malicious pattern detection
            self._detect_malicious_patterns(content)
            
            # Complexity validation
            self._validate_complexity(content)
            
            # Entropy validation (detect non-text data)
            self._validate_entropy(content)
            
            # Metadata validation
            if metadata:
                metadata = self._validate_metadata(metadata)
            
            # Sanitize content
            sanitized_content = self._sanitize_content(content)
            
            elapsed = time.perf_counter() - start_time
            self.validation_times.append(elapsed)
            
            return {
                'valid': True,
                'content': sanitized_content,
                'metadata': metadata,
                'document_id': self._sanitize_id(document_id),
                'validation_time': elapsed,
                'checks_passed': [
                    'size', 'encoding', 'malicious_patterns',
                    'complexity', 'entropy', 'metadata'
                ]
            }
            
        except ValidationError as e:
            self.rejection_count += 1
            logger.warning(f"Validation failed for document {document_id}: {e}")
            raise
        except Exception as e:
            self.rejection_count += 1
            logger.error(f"Unexpected validation error: {e}")
            raise ValidationError(f"Validation failed: {str(e)}")
    
    def validate_batch(self, documents: List[Union[str, Dict]]) -> List[Dict[str, Any]]:
        """Validate multiple documents."""
        if len(documents) > self.config.max_batch_size:
            raise InputSizeError(
                f"Batch size {len(documents)} exceeds limit {self.config.max_batch_size}"
            )
        
        results = []
        for i, doc in enumerate(documents):
            try:
                if isinstance(doc, str):
                    result = self.validate_document(doc, document_id=f"batch_{i}")
                else:
                    result = self.validate_document(
                        doc.get('content', ''),
                        doc.get('metadata'),
                        doc.get('id', f"batch_{i}")
                    )
                results.append(result)
            except ValidationError as e:
                results.append({
                    'valid': False,
                    'error': str(e),
                    'document_id': f"batch_{i}"
                })
        
        return results
    
    def _validate_encoding(self, content: bytes) -> str:
        """Validate and decode bytes to UTF-8 string."""
        try:
            # Try UTF-8 first
            decoded = content.decode('utf-8', errors='strict')
            
            # Check for null bytes
            if '\x00' in decoded:
                raise EncodingError("Null bytes detected in content")
            
            # Normalize unicode
            normalized = unicodedata.normalize('NFKC', decoded)
            
            return normalized
            
        except UnicodeDecodeError:
            # Try with error handling
            try:
                decoded = content.decode('utf-8', errors='replace')
                logger.warning("Had to replace invalid UTF-8 characters")
                return decoded
            except Exception as e:
                raise EncodingError(f"Failed to decode content: {e}")
    
    def _validate_size(self, content: str, metadata: Optional[Dict]):
        """Validate content and metadata size."""
        content_size = len(content.encode('utf-8'))
        
        if content_size > self.config.max_document_size:
            raise InputSizeError(
                f"Document size {content_size} bytes exceeds limit "
                f"{self.config.max_document_size} bytes"
            )
        
        if metadata:
            metadata_size = len(str(metadata).encode('utf-8'))
            if metadata_size > self.config.max_metadata_size:
                raise InputSizeError(
                    f"Metadata size {metadata_size} bytes exceeds limit "
                    f"{self.config.max_metadata_size} bytes"
                )
    
    def _validate_text_format(self, content: str) -> str:
        """Validate text format and structure."""
        # Check for binary data indicators
        non_printable_count = sum(1 for c in content if not c.isprintable() and c not in '\n\r\t')
        if non_printable_count > len(content) * 0.1:  # More than 10% non-printable
            raise EncodingError("Content appears to contain binary data")
        
        # Validate line endings
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # Check for extremely long lines (potential attack vector)
        lines = content.split('\n')
        max_line_length = max(len(line) for line in lines) if lines else 0
        if max_line_length > 10000:
            raise ComplexityError(f"Line length {max_line_length} exceeds reasonable limits")
        
        return content
    
    def _detect_malicious_patterns(self, content: str):
        """Detect potentially malicious patterns."""
        if not self.config.strict_mode:
            return
        
        content_lower = content.lower()
        
        # Check against injection patterns
        for pattern in self.injection_regex:
            if pattern.search(content_lower):
                raise MaliciousInputError(
                    f"Potentially malicious pattern detected: {pattern.pattern[:50]}..."
                )
        
        # Check for excessive special characters (potential obfuscation)
        special_char_ratio = len(re.findall(r'[^\w\s]', content)) / max(len(content), 1)
        if special_char_ratio > 0.3:  # More than 30% special characters
            raise MaliciousInputError(
                f"Excessive special characters detected ({special_char_ratio:.1%})"
            )
        
        # Check for HTML/Script content if not allowed
        if not self.config.allow_html:
            if re.search(r'<[^>]+>', content):
                raise MaliciousInputError("HTML content not allowed")
        
        if not self.config.allow_scripts:
            script_patterns = [
                r'<script', r'javascript:', r'eval\s*\(', r'Function\s*\(',
                r'setTimeout\s*\(', r'setInterval\s*\('
            ]
            for pattern in script_patterns:
                if re.search(pattern, content_lower):
                    raise MaliciousInputError(f"Script content not allowed: {pattern}")
    
    def _validate_complexity(self, content: str):
        """Validate document complexity to prevent algorithmic attacks."""
        # Word count
        word_count = len(content.split())
        if word_count > self.config.max_word_count:
            raise ComplexityError(
                f"Word count {word_count} exceeds limit {self.config.max_word_count}"
            )
        
        # Line count
        line_count = content.count('\n') + 1
        if line_count > self.config.max_line_count:
            raise ComplexityError(
                f"Line count {line_count} exceeds limit {self.config.max_line_count}"
            )
        
        # Nesting depth (for structured content)
        max_nesting = self._calculate_nesting_depth(content)
        if max_nesting > 50:
            raise ComplexityError(f"Nesting depth {max_nesting} exceeds safe limits")
        
        # Pattern complexity
        unique_patterns = len(set(re.findall(r'\b\w+\b', content.lower())))
        if unique_patterns > self.config.max_pattern_count:
            logger.warning(f"High pattern complexity: {unique_patterns} unique patterns")
    
    def _validate_entropy(self, content: str):
        """Validate entropy to detect non-text or random data."""
        if len(content) < 100:
            return  # Too short for meaningful entropy calculation
        
        # Calculate character entropy
        char_counts = {}
        for char in content:
            char_counts[char] = char_counts.get(char, 0) + 1
        
        total_chars = len(content)
        entropy = 0.0
        
        for count in char_counts.values():
            if count > 0:
                probability = count / total_chars
                entropy -= probability * (probability and probability * 2 or 0)
        
        # Check entropy bounds
        if entropy < self.config.min_entropy_threshold:
            raise ValidationError(
                f"Content entropy {entropy:.2f} too low - possible non-text data"
            )
        
        if entropy > self.config.max_entropy_threshold:
            raise ValidationError(
                f"Content entropy {entropy:.2f} too high - possible random/encrypted data"
            )
    
    def _validate_metadata(self, metadata: Dict) -> Dict:
        """Validate and sanitize metadata."""
        if not isinstance(metadata, dict):
            raise ValidationError("Metadata must be a dictionary")
        
        sanitized = {}
        
        for key, value in metadata.items():
            # Validate key
            if not isinstance(key, str):
                continue
            if len(key) > 100:
                continue
            if not re.match(r'^[a-zA-Z0-9_.-]+$', key):
                continue
            
            # Validate value
            if value is None:
                sanitized[key] = None
            elif isinstance(value, (str, int, float, bool)):
                if isinstance(value, str) and len(value) > 1000:
                    value = value[:1000] + '...'
                sanitized[key] = value
            elif isinstance(value, (list, tuple)):
                # Limit list size
                sanitized[key] = list(value)[:100]
            elif isinstance(value, dict):
                # Recursive validation with depth limit
                if len(str(value)) < 5000:
                    sanitized[key] = self._validate_metadata(value)
        
        return sanitized
    
    def _sanitize_content(self, content: str) -> str:
        """Sanitize content for safe processing."""
        # HTML escape if needed
        if self.config.strict_mode and not self.config.allow_html:
            content = html.escape(content, quote=False)
        
        # Remove zero-width characters
        zero_width_chars = [
            '\u200b', '\u200c', '\u200d', '\u2060', '\ufeff',
            '\u180e', '\u2000', '\u2001', '\u2002', '\u2003'
        ]
        for char in zero_width_chars:
            content = content.replace(char, '')
        
        # Normalize whitespace
        content = re.sub(r'[ \t]+', ' ', content)
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return content.strip()
    
    def _sanitize_id(self, document_id: Optional[str]) -> Optional[str]:
        """Sanitize document ID."""
        if not document_id:
            return None
        
        # Allow only alphanumeric, underscore, dash
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', str(document_id))
        
        # Limit length
        return sanitized[:100] if sanitized else None
    
    def _calculate_nesting_depth(self, content: str) -> int:
        """Calculate maximum nesting depth of brackets/braces."""
        max_depth = 0
        current_depth = 0
        
        for char in content:
            if char in '([{':
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char in ')]}':
                current_depth = max(0, current_depth - 1)
        
        return max_depth
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        avg_time = sum(self.validation_times) / len(self.validation_times) \
            if self.validation_times else 0
        
        return {
            'total_validated': self.validation_count,
            'total_rejected': self.rejection_count,
            'rejection_rate': self.rejection_count / max(self.validation_count, 1),
            'average_validation_time_ms': avg_time * 1000,
            'max_validation_time_ms': max(self.validation_times, default=0) * 1000,
            'config': {
                'max_document_size_mb': self.config.max_document_size / (1024 * 1024),
                'strict_mode': self.config.strict_mode,
                'allow_html': self.config.allow_html
            }
        }


def validate_with_timeout(timeout: float = 5.0):
    """Decorator to add timeout to validation functions."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import signal
            
            def timeout_handler(signum, frame):
                raise ValidationError(f"Validation timeout after {timeout} seconds")
            
            # Set timeout
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(timeout))
            
            try:
                result = func(*args, **kwargs)
            finally:
                # Reset alarm
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
            
            return result
        return wrapper
    return decorator


# Global validator instance
_default_validator = None


def get_validator(config: Optional[ValidationConfig] = None) -> InputValidator:
    """Get or create default validator instance."""
    global _default_validator
    
    if _default_validator is None or config is not None:
        _default_validator = InputValidator(config)
    
    return _default_validator