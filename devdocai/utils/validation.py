"""
Validation Utilities - DevDocAI v3.0.0
Pass 4: Simplified validation with essential safety checks
"""

import logging
from typing import Any, Dict
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigValidator:
    """Configuration data validation and sanitization."""

    MAX_DEPTH = 10
    MAX_STRING_LENGTH = 10000
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

    @classmethod
    def sanitize_data(cls, data: Any, depth: int = 0) -> Any:
        """Recursively sanitize configuration data."""
        if depth > cls.MAX_DEPTH:
            logger.warning(f"Data exceeds max depth ({cls.MAX_DEPTH})")
            return {} if isinstance(data, dict) else []

        if isinstance(data, dict):
            return {
                cls._clean_key(k): cls.sanitize_data(v, depth + 1)
                for k, v in data.items()
                if isinstance(k, str) and len(k) <= 256
            }
        elif isinstance(data, list):
            return [cls.sanitize_data(item, depth + 1) for item in data[:1000]]
        elif isinstance(data, str):
            # Limit length and remove null bytes
            clean = data[: cls.MAX_STRING_LENGTH].replace("\x00", "")
            try:
                clean.encode("utf-8")
                return clean
            except UnicodeEncodeError:
                return clean.encode("utf-8", errors="ignore").decode("utf-8")
        else:
            return data  # Numbers, booleans, None are safe

    @classmethod
    def _clean_key(cls, key: str) -> str:
        """Clean configuration key."""
        # Remove control characters
        return "".join(c for c in key if ord(c) >= 32 or c in "\t\n\r")

    @classmethod
    def validate_file_size(cls, file_path: str) -> bool:
        """Check if file size is within limits."""
        try:
            return Path(file_path).stat().st_size <= cls.MAX_FILE_SIZE
        except:
            return False
