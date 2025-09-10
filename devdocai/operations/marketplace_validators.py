"""
M013 Template Marketplace - Input Validation and Sanitization
DevDocAI v3.0.0 - Pass 4: Refactoring & Integration

This module contains input validation and sanitization utilities extracted
from the security module for clean separation of concerns.
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .marketplace_types import ValidationLevel, ValidationResult

logger = logging.getLogger(__name__)


class InputValidator:
    """Input validation utilities."""

    # Validation patterns
    SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+(-[\w\-\.]+)?(\+[\w\-\.]+)?$")
    TEMPLATE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9\-_]{2,63}$")
    AUTHOR_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9\-_\.]{0,63}$")
    TAG_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9\-_]{0,31}$")

    # Size limits
    MAX_TEMPLATE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_NAME_LENGTH = 128
    MAX_DESCRIPTION_LENGTH = 1024
    MAX_TAGS = 20
    MAX_TAG_LENGTH = 32

    @classmethod
    def validate_template_id(cls, template_id: str) -> Tuple[bool, Optional[str]]:
        """
        Validate template ID format.

        Args:
            template_id: Template ID to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not template_id:
            return False, "Template ID is required"

        if len(template_id) < 3 or len(template_id) > 64:
            return False, "Template ID must be 3-64 characters"

        if not cls.TEMPLATE_ID_PATTERN.match(template_id):
            return False, "Template ID contains invalid characters"

        return True, None

    @classmethod
    def validate_version(cls, version: str) -> Tuple[bool, Optional[str]]:
        """
        Validate semantic version format.

        Args:
            version: Version string to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not version:
            return False, "Version is required"

        if not cls.SEMVER_PATTERN.match(version):
            return False, f"Invalid semantic version format: {version}"

        return True, None

    @classmethod
    def validate_author(cls, author: str) -> Tuple[bool, Optional[str]]:
        """
        Validate author name format.

        Args:
            author: Author name to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not author:
            return False, "Author is required"

        if len(author) > 64:
            return False, "Author name too long (max 64 characters)"

        if not cls.AUTHOR_PATTERN.match(author):
            return False, "Author name contains invalid characters"

        return True, None

    @classmethod
    def validate_tags(cls, tags: List[str]) -> Tuple[bool, List[str]]:
        """
        Validate template tags.

        Args:
            tags: List of tags to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        if len(tags) > cls.MAX_TAGS:
            errors.append(f"Too many tags (max {cls.MAX_TAGS})")

        for tag in tags:
            if len(tag) > cls.MAX_TAG_LENGTH:
                errors.append(f"Tag '{tag}' too long (max {cls.MAX_TAG_LENGTH} characters)")
            elif not cls.TAG_PATTERN.match(tag):
                errors.append(f"Tag '{tag}' contains invalid characters")

        return len(errors) == 0, errors

    @classmethod
    def validate_template_metadata(cls, metadata: Dict[str, Any]) -> ValidationResult:
        """
        Validate complete template metadata.

        Args:
            metadata: Template metadata dictionary

        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []

        # Validate ID
        if "id" in metadata:
            valid, error = cls.validate_template_id(metadata["id"])
            if not valid:
                errors.append(error)
        else:
            errors.append("Template ID is required")

        # Validate name
        name = metadata.get("name", "")
        if not name:
            errors.append("Template name is required")
        elif len(name) > cls.MAX_NAME_LENGTH:
            errors.append(f"Template name too long (max {cls.MAX_NAME_LENGTH} characters)")

        # Validate description
        description = metadata.get("description", "")
        if len(description) > cls.MAX_DESCRIPTION_LENGTH:
            warnings.append(f"Description too long (max {cls.MAX_DESCRIPTION_LENGTH} characters)")

        # Validate version
        if "version" in metadata:
            valid, error = cls.validate_version(metadata["version"])
            if not valid:
                errors.append(error)
        else:
            errors.append("Version is required")

        # Validate author
        if "author" in metadata:
            valid, error = cls.validate_author(metadata["author"])
            if not valid:
                errors.append(error)
        else:
            errors.append("Author is required")

        # Validate tags
        tags = metadata.get("tags", [])
        if tags:
            valid, tag_errors = cls.validate_tags(tags)
            if not valid:
                errors.extend(tag_errors)

        # Validate rating
        rating = metadata.get("rating", 0.0)
        if rating < 0.0 or rating > 5.0:
            warnings.append("Rating should be between 0.0 and 5.0")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            validation_level=ValidationLevel.STANDARD,
        )


class ContentValidator:
    """Content validation and security checking."""

    # Dangerous patterns for different content types
    HTML_DANGEROUS_PATTERNS = [
        (re.compile(r"<script[^>]*>", re.IGNORECASE), "Script tags not allowed"),
        (re.compile(r"javascript:", re.IGNORECASE), "JavaScript URLs not allowed"),
        (re.compile(r"on\w+\s*=", re.IGNORECASE), "Event handlers not allowed"),
        (re.compile(r"<iframe[^>]*>", re.IGNORECASE), "Iframe tags not allowed"),
        (re.compile(r"<object[^>]*>", re.IGNORECASE), "Object tags not allowed"),
        (re.compile(r"<embed[^>]*>", re.IGNORECASE), "Embed tags not allowed"),
    ]

    CODE_DANGEROUS_PATTERNS = [
        (re.compile(r"\beval\s*\(", re.IGNORECASE), "eval() not allowed"),
        (re.compile(r"\bexec\s*\(", re.IGNORECASE), "exec() not allowed"),
        (re.compile(r"__import__\s*\(", re.IGNORECASE), "__import__() not allowed"),
        (re.compile(r"\bcompile\s*\(", re.IGNORECASE), "compile() not allowed"),
        (re.compile(r"subprocess\.\w+", re.IGNORECASE), "Subprocess calls not allowed"),
        (re.compile(r"os\.\w+", re.IGNORECASE), "OS module calls not allowed"),
    ]

    SQL_INJECTION_PATTERNS = [
        (
            re.compile(r"('\s*(OR|AND)\s*'?1'?\s*=\s*'?1)", re.IGNORECASE),
            "SQL injection pattern detected",
        ),
        (
            re.compile(r"(DROP\s+TABLE|DELETE\s+FROM|TRUNCATE\s+TABLE)", re.IGNORECASE),
            "Dangerous SQL command detected",
        ),
        (
            re.compile(r"(UNION\s+SELECT|SELECT\s+.*\s+FROM\s+information_schema)", re.IGNORECASE),
            "SQL injection attempt detected",
        ),
    ]

    @classmethod
    def validate_content(cls, content: str, content_type: str = "template") -> ValidationResult:
        """
        Validate content for security issues.

        Args:
            content: Content to validate
            content_type: Type of content (template, html, code)

        Returns:
            ValidationResult with security findings
        """
        errors = []
        warnings = []

        if not content:
            warnings.append("Content is empty")
            return ValidationResult(
                is_valid=True, warnings=warnings, validation_level=ValidationLevel.STRICT
            )

        # Check size
        if len(content) > InputValidator.MAX_TEMPLATE_SIZE:
            errors.append(
                f"Content exceeds maximum size ({InputValidator.MAX_TEMPLATE_SIZE} bytes)"
            )

        # Check for dangerous patterns based on content type
        if content_type in ["template", "html"]:
            patterns = cls.HTML_DANGEROUS_PATTERNS
        elif content_type == "code":
            patterns = cls.CODE_DANGEROUS_PATTERNS
        else:
            patterns = cls.HTML_DANGEROUS_PATTERNS + cls.CODE_DANGEROUS_PATTERNS

        for pattern, message in patterns:
            if pattern.search(content):
                errors.append(message)

        # Check for SQL injection patterns
        for pattern, message in cls.SQL_INJECTION_PATTERNS:
            if pattern.search(content):
                warnings.append(message)

        # Calculate security score
        security_score = 1.0
        security_score -= len(errors) * 0.2
        security_score -= len(warnings) * 0.1
        security_score = max(0.0, security_score)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            security_score=security_score,
            validation_level=ValidationLevel.STRICT,
        )


class ContentSanitizer:
    """Content sanitization utilities."""

    @staticmethod
    def sanitize_html(content: str) -> str:
        """
        Sanitize HTML content by removing dangerous elements.

        Args:
            content: HTML content to sanitize

        Returns:
            Sanitized content
        """
        # Remove script tags and content
        content = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.IGNORECASE | re.DOTALL)

        # Remove event handlers
        content = re.sub(r'\son\w+\s*=\s*["\'][^"\']*["\']', "", content, flags=re.IGNORECASE)

        # Remove javascript: URLs
        content = re.sub(r"javascript:", "", content, flags=re.IGNORECASE)

        # Remove dangerous tags
        dangerous_tags = ["iframe", "object", "embed", "applet", "form"]
        for tag in dangerous_tags:
            content = re.sub(
                f"<{tag}[^>]*>.*?</{tag}>", "", content, flags=re.IGNORECASE | re.DOTALL
            )
            content = re.sub(f"<{tag}[^>]*/>", "", content, flags=re.IGNORECASE)

        return content.strip()

    @staticmethod
    def sanitize_code(content: str) -> str:
        """
        Sanitize code content by removing dangerous functions.

        Args:
            content: Code content to sanitize

        Returns:
            Sanitized content
        """
        # Remove eval and exec calls
        content = re.sub(
            r"\b(eval|exec)\s*\([^)]*\)",
            "# REMOVED_DANGEROUS_FUNCTION",
            content,
            flags=re.IGNORECASE,
        )

        # Remove __import__ calls
        content = re.sub(
            r"__import__\s*\([^)]*\)", "# REMOVED_IMPORT", content, flags=re.IGNORECASE
        )

        # Remove subprocess calls
        content = re.sub(
            r"subprocess\.\w+\([^)]*\)", "# REMOVED_SUBPROCESS", content, flags=re.IGNORECASE
        )

        # Remove os module calls
        content = re.sub(r"os\.\w+\([^)]*\)", "# REMOVED_OS_CALL", content, flags=re.IGNORECASE)

        return content

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to prevent path traversal.

        Args:
            filename: Filename to sanitize

        Returns:
            Sanitized filename
        """
        # Remove path separators
        filename = filename.replace("/", "_").replace("\\", "_")

        # Remove parent directory references
        filename = filename.replace("..", "_")

        # Remove null bytes
        filename = filename.replace("\x00", "")

        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
            max_name_len = 255 - len(ext) - 1 if ext else 255
            filename = name[:max_name_len] + ("." + ext if ext else "")

        # Remove special characters
        filename = re.sub(r"[^\w\-_\.]", "_", filename)

        return filename


class RateLimitValidator:
    """Rate limiting validation."""

    def __init__(self, limits: Optional[Dict[str, Dict[str, int]]] = None):
        """
        Initialize rate limit validator.

        Args:
            limits: Rate limits by operation and time window
        """
        self.limits = limits or {
            "download": {"hour": 100, "day": 500},
            "upload": {"hour": 10, "day": 50},
            "discover": {"hour": 200, "day": 1000},
        }
        self.requests: Dict[str, List[datetime]] = {}

    def check_rate_limit(self, client_id: str, operation: str) -> Tuple[bool, Optional[int]]:
        """
        Check if request is within rate limits.

        Args:
            client_id: Client identifier
            operation: Operation type

        Returns:
            Tuple of (allowed, retry_after_seconds)
        """
        if operation not in self.limits:
            return True, None

        now = datetime.now()
        key = f"{client_id}:{operation}"

        # Initialize request list if needed
        if key not in self.requests:
            self.requests[key] = []

        # Clean old requests
        hour_ago = now - datetime.timedelta(hours=1)
        day_ago = now - datetime.timedelta(days=1)

        self.requests[key] = [req_time for req_time in self.requests[key] if req_time > day_ago]

        # Check limits
        hour_requests = sum(1 for t in self.requests[key] if t > hour_ago)
        day_requests = len(self.requests[key])

        hour_limit = self.limits[operation].get("hour", float("inf"))
        day_limit = self.limits[operation].get("day", float("inf"))

        if hour_requests >= hour_limit:
            retry_after = 3600  # Retry in 1 hour
            return False, retry_after

        if day_requests >= day_limit:
            retry_after = 86400  # Retry in 1 day
            return False, retry_after

        # Record request
        self.requests[key].append(now)

        return True, None

    def get_remaining_quota(self, client_id: str, operation: str) -> Dict[str, int]:
        """
        Get remaining quota for client and operation.

        Args:
            client_id: Client identifier
            operation: Operation type

        Returns:
            Dictionary with remaining quotas
        """
        if operation not in self.limits:
            return {"hour": -1, "day": -1}  # Unlimited

        now = datetime.now()
        key = f"{client_id}:{operation}"

        if key not in self.requests:
            return self.limits[operation].copy()

        hour_ago = now - datetime.timedelta(hours=1)
        day_ago = now - datetime.timedelta(days=1)

        hour_requests = sum(1 for t in self.requests[key] if t > hour_ago)
        day_requests = sum(1 for t in self.requests[key] if t > day_ago)

        hour_limit = self.limits[operation].get("hour", float("inf"))
        day_limit = self.limits[operation].get("day", float("inf"))

        return {"hour": max(0, hour_limit - hour_requests), "day": max(0, day_limit - day_requests)}


def create_validator(
    validation_level: ValidationLevel = ValidationLevel.STANDARD,
) -> InputValidator:
    """
    Factory function to create validator.

    Args:
        validation_level: Validation strictness level

    Returns:
        Validator instance
    """
    # For now, return standard validator
    # Could be extended to return different validators based on level
    return InputValidator()
