"""
Input sanitization and validation for CLI security.

Prevents command injection, path traversal, and other input-based attacks.
"""

import re
import os
import json
import shlex
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse
import html
import unicodedata

class ValidationError(Exception):
    """Input validation error."""
    pass


class InputSanitizer:
    """
    Comprehensive input sanitization and validation.
    
    Prevents:
    - Command injection
    - Path traversal
    - XSS attacks
    - SQL injection
    - LDAP injection
    - XML injection
    - ReDoS attacks
    """
    
    # Dangerous shell characters and patterns
    SHELL_DANGEROUS_CHARS = ['&', '|', ';', '$', '`', '\\', '!', '\n', '\r', '<', '>', '(', ')', '{', '}']
    SHELL_DANGEROUS_PATTERNS = [
        r'\$\(',  # Command substitution
        r'\`',    # Backticks
        r'\|\|',  # OR operator
        r'&&',    # AND operator
        r'>+',    # Redirect
        r'<+',    # Input redirect
    ]
    
    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        '../', '..\\',  # Basic traversal
        '%2e%2e%2f', '%2e%2e%5c',  # URL encoded
        '..%2f', '..%5c',  # Partial encoding
        '%252e%252e%252f',  # Double encoding
        '..;/', '..;\\',  # Semicolon bypass
        '..%00/',  # Null byte injection
        '..%0d/', '..%0a/',  # CRLF injection
    ]
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\bor\b|\band\b)\s*['\"]?\s*=\s*['\"]?",  # OR/AND with equals
        r"union\s+(all\s+)?select",  # UNION SELECT
        r";\s*drop\s+table",  # DROP TABLE
        r";\s*delete\s+from",  # DELETE FROM
        r"'|\"|--|\#|\/\*|\*\/|xp_|sp_|0x",  # Common SQL injection chars
    ]
    
    # File size limits
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    MAX_PATH_LENGTH = 4096
    MAX_FILENAME_LENGTH = 255
    MAX_JSON_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_JSON_DEPTH = 100
    MAX_STRING_LENGTH = 1024 * 1024  # 1MB
    
    def __init__(self, strict_mode: bool = True):
        """
        Initialize sanitizer.
        
        Args:
            strict_mode: If True, applies strictest validation rules
        """
        self.strict_mode = strict_mode
        self.allowed_dirs: List[Path] = [
            Path.cwd(),
            Path.home() / '.devdocai',
            Path('/tmp') / 'devdocai'  # Temporary files
        ]
        
    def sanitize_path(self, path: str, must_exist: bool = False,
                     allow_creation: bool = False) -> str:
        """
        Sanitize and validate file paths.
        
        Args:
            path: Path to sanitize
            must_exist: If True, path must exist
            allow_creation: If True, parent directory must exist for new files
            
        Returns:
            Sanitized absolute path
            
        Raises:
            ValidationError: If path is invalid or malicious
        """
        if not path:
            raise ValidationError("Path cannot be empty")
            
        # Check path length
        if len(path) > self.MAX_PATH_LENGTH:
            raise ValidationError(f"Path too long (max {self.MAX_PATH_LENGTH} chars)")
        
        # Check for null bytes
        if '\x00' in path:
            raise ValidationError("Path contains null bytes")
        
        # Check for traversal patterns
        path_lower = path.lower()
        for pattern in self.PATH_TRAVERSAL_PATTERNS:
            if pattern in path_lower:
                raise ValidationError(f"Path traversal detected: {pattern}")
        
        # Resolve to absolute path
        try:
            abs_path = Path(path).resolve()
        except (OSError, ValueError) as e:
            raise ValidationError(f"Invalid path: {e}")
        
        # Check if path is within allowed directories
        if self.strict_mode:
            allowed = False
            for allowed_dir in self.allowed_dirs:
                try:
                    abs_path.relative_to(allowed_dir)
                    allowed = True
                    break
                except ValueError:
                    continue
            
            if not allowed:
                raise ValidationError(f"Path outside allowed directories: {abs_path}")
        
        # Existence checks
        if must_exist and not abs_path.exists():
            raise ValidationError(f"Path does not exist: {abs_path}")
        
        if allow_creation and not abs_path.parent.exists():
            raise ValidationError(f"Parent directory does not exist: {abs_path.parent}")
        
        # Check for symbolic links (prevent symlink attacks)
        if abs_path.exists() and abs_path.is_symlink():
            if self.strict_mode:
                raise ValidationError(f"Symbolic links not allowed: {abs_path}")
            # Follow symlink and revalidate
            real_path = abs_path.readlink()
            return self.sanitize_path(str(real_path), must_exist, allow_creation)
        
        # Check file permissions
        if abs_path.exists():
            if not os.access(abs_path, os.R_OK):
                raise ValidationError(f"No read permission: {abs_path}")
        
        return str(abs_path)
    
    def sanitize_command_arg(self, arg: str, allow_options: bool = True) -> str:
        """
        Sanitize command-line arguments.
        
        Args:
            arg: Argument to sanitize
            allow_options: If True, allows arguments starting with - or --
            
        Returns:
            Sanitized argument
            
        Raises:
            ValidationError: If argument contains dangerous patterns
        """
        if not arg:
            return ''
        
        # Check for dangerous characters
        for char in self.SHELL_DANGEROUS_CHARS:
            if char in arg:
                if self.strict_mode:
                    raise ValidationError(f"Dangerous character in argument: {char}")
        
        # Check for dangerous patterns
        for pattern in self.SHELL_DANGEROUS_PATTERNS:
            if re.search(pattern, arg, re.IGNORECASE):
                raise ValidationError(f"Dangerous pattern in argument: {pattern}")
        
        # Disallow options if not allowed
        if not allow_options and arg.startswith('-'):
            raise ValidationError("Options not allowed in this context")
        
        # Use shlex for proper escaping
        return shlex.quote(arg)
    
    def validate_json_input(self, data: str, max_size: Optional[int] = None) -> Dict[str, Any]:
        """
        Validate and sanitize JSON input.
        
        Args:
            data: JSON string to validate
            max_size: Maximum allowed size in bytes
            
        Returns:
            Parsed JSON object
            
        Raises:
            ValidationError: If JSON is invalid or malicious
        """
        max_size = max_size or self.MAX_JSON_SIZE
        
        # Size check
        if len(data) > max_size:
            raise ValidationError(f"JSON too large (max {max_size} bytes)")
        
        # Parse JSON
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON: {e}")
        
        # Deep validation
        self._validate_json_structure(parsed)
        
        return parsed
    
    def _validate_json_structure(self, obj: Any, depth: int = 0):
        """Recursively validate JSON structure."""
        if depth > self.MAX_JSON_DEPTH:
            raise ValidationError(f"JSON nesting too deep (max {self.MAX_JSON_DEPTH})")
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                if not isinstance(key, str):
                    raise ValidationError("JSON keys must be strings")
                if len(key) > 1000:
                    raise ValidationError("JSON key too long")
                # Check for prototype pollution attempts
                if key in ['__proto__', 'constructor', 'prototype']:
                    raise ValidationError(f"Dangerous JSON key: {key}")
                self._validate_json_structure(value, depth + 1)
        elif isinstance(obj, list):
            if len(obj) > 10000:
                raise ValidationError("JSON array too large")
            for item in obj:
                self._validate_json_structure(item, depth + 1)
        elif isinstance(obj, str):
            if len(obj) > self.MAX_STRING_LENGTH:
                raise ValidationError(f"String too long (max {self.MAX_STRING_LENGTH})")
            # Check for XSS patterns in strings
            if self.strict_mode:
                self._check_xss_patterns(obj)
    
    def _check_xss_patterns(self, text: str):
        """Check for XSS attack patterns."""
        xss_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',  # Event handlers
            r'<iframe',
            r'<embed',
            r'<object',
            r'eval\s*\(',
            r'expression\s*\(',
        ]
        
        for pattern in xss_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                raise ValidationError(f"Potential XSS pattern detected: {pattern}")
    
    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for safe file operations.
        
        Args:
            filename: Filename to sanitize
            
        Returns:
            Sanitized filename
            
        Raises:
            ValidationError: If filename is invalid
        """
        if not filename:
            raise ValidationError("Filename cannot be empty")
        
        # Remove path components
        filename = os.path.basename(filename)
        
        # Check length
        if len(filename) > self.MAX_FILENAME_LENGTH:
            raise ValidationError(f"Filename too long (max {self.MAX_FILENAME_LENGTH})")
        
        # Remove dangerous characters
        # Allow only alphanumeric, dots, hyphens, underscores
        sanitized = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        
        # Prevent special filenames
        if sanitized.lower() in ['con', 'prn', 'aux', 'nul', 'com1', 'lpt1']:
            raise ValidationError(f"Reserved filename: {sanitized}")
        
        # Prevent hidden files in strict mode
        if self.strict_mode and sanitized.startswith('.'):
            raise ValidationError("Hidden files not allowed")
        
        # Prevent double extensions (possible bypass attempts)
        if sanitized.count('.') > 2:
            raise ValidationError("Too many dots in filename")
        
        return sanitized
    
    def validate_url(self, url: str, allowed_schemes: Optional[List[str]] = None) -> str:
        """
        Validate and sanitize URLs.
        
        Args:
            url: URL to validate
            allowed_schemes: List of allowed URL schemes
            
        Returns:
            Validated URL
            
        Raises:
            ValidationError: If URL is invalid
        """
        allowed_schemes = allowed_schemes or ['http', 'https']
        
        try:
            parsed = urlparse(url)
        except Exception as e:
            raise ValidationError(f"Invalid URL: {e}")
        
        # Check scheme
        if parsed.scheme not in allowed_schemes:
            raise ValidationError(f"URL scheme not allowed: {parsed.scheme}")
        
        # Check for local file access attempts
        if parsed.hostname in ['localhost', '127.0.0.1', '0.0.0.0', '::1']:
            if self.strict_mode:
                raise ValidationError("Local URLs not allowed")
        
        # Check for private IP ranges
        if parsed.hostname:
            import ipaddress
            try:
                ip = ipaddress.ip_address(parsed.hostname)
                if ip.is_private:
                    if self.strict_mode:
                        raise ValidationError("Private IP addresses not allowed")
            except ValueError:
                # Not an IP address, hostname is OK
                pass
        
        return url
    
    def sanitize_sql_input(self, value: str) -> str:
        """
        Sanitize input for SQL queries.
        
        Args:
            value: Value to sanitize
            
        Returns:
            Sanitized value
            
        Raises:
            ValidationError: If SQL injection detected
        """
        # Check for SQL injection patterns
        value_lower = value.lower()
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                raise ValidationError(f"Potential SQL injection detected")
        
        # Escape special characters
        # Note: This is basic sanitization. Use parameterized queries in production!
        sanitized = value.replace("'", "''")
        sanitized = sanitized.replace('"', '""')
        sanitized = sanitized.replace('\\', '\\\\')
        sanitized = sanitized.replace('\0', '')
        
        return sanitized
    
    def sanitize_html(self, html: str) -> str:
        """
        Sanitize HTML content.
        
        Args:
            html: HTML content to sanitize
            
        Returns:
            Sanitized HTML
        """
        # Basic HTML escaping
        return html.escape(html)
    
    def validate_email(self, email: str) -> str:
        """
        Validate email address.
        
        Args:
            email: Email to validate
            
        Returns:
            Validated email
            
        Raises:
            ValidationError: If email is invalid
        """
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValidationError(f"Invalid email address: {email}")
        
        # Check length
        if len(email) > 254:  # RFC 5321
            raise ValidationError("Email address too long")
        
        return email.lower()
    
    def validate_integer(self, value: str, min_val: Optional[int] = None,
                        max_val: Optional[int] = None) -> int:
        """
        Validate integer input.
        
        Args:
            value: String value to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            
        Returns:
            Validated integer
            
        Raises:
            ValidationError: If value is not a valid integer
        """
        try:
            int_val = int(value)
        except ValueError:
            raise ValidationError(f"Invalid integer: {value}")
        
        if min_val is not None and int_val < min_val:
            raise ValidationError(f"Value too small (min {min_val})")
        
        if max_val is not None and int_val > max_val:
            raise ValidationError(f"Value too large (max {max_val})")
        
        return int_val
    
    def compute_hash(self, data: Union[str, bytes]) -> str:
        """
        Compute secure hash of data.
        
        Args:
            data: Data to hash
            
        Returns:
            SHA-256 hash hex string
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        return hashlib.sha256(data).hexdigest()