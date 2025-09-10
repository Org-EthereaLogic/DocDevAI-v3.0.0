"""
M013 Template Marketplace - Factory and Strategy Patterns
DevDocAI v3.0.0 - Pass 4: Refactoring & Integration

This module implements Factory and Strategy patterns for marketplace operations,
following the successful patterns from M003, M005, M006, M007, and M012.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from .marketplace_types import (
    CacheLevel,
    SecurityContext,
    TemplateMetadata,
    ValidationLevel,
    ValidationResult,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Abstract Strategy Interfaces
# ============================================================================


class DownloadStrategy(ABC):
    """Abstract strategy for template download operations."""

    @abstractmethod
    def download(
        self, template_id: str, context: Optional[SecurityContext] = None
    ) -> Optional[TemplateMetadata]:
        """Download a template using specific strategy."""
        pass

    @abstractmethod
    def supports_batch(self) -> bool:
        """Check if strategy supports batch downloads."""
        pass


class CacheStrategy(ABC):
    """Abstract strategy for caching operations."""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Retrieve item from cache."""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store item in cache."""
        pass

    @abstractmethod
    def remove(self, key: str) -> bool:
        """Remove item from cache."""
        pass

    @abstractmethod
    def get_cache_level(self) -> CacheLevel:
        """Get the cache level of this strategy."""
        pass


class ValidationStrategy(ABC):
    """Abstract strategy for template validation."""

    @abstractmethod
    def validate(self, template: TemplateMetadata) -> ValidationResult:
        """Validate a template."""
        pass

    @abstractmethod
    def get_validation_level(self) -> ValidationLevel:
        """Get the validation level of this strategy."""
        pass


class VerificationStrategy(ABC):
    """Abstract strategy for signature verification."""

    @abstractmethod
    def verify(self, message: bytes, signature: bytes, public_key: bytes) -> bool:
        """Verify a signature."""
        pass

    @abstractmethod
    def sign(self, message: bytes, private_key: bytes) -> bytes:
        """Sign a message."""
        pass

    @abstractmethod
    def generate_keypair(self) -> Tuple[bytes, bytes]:
        """Generate a new keypair."""
        pass


# ============================================================================
# Concrete Strategy Implementations
# ============================================================================


class StandardDownloadStrategy(DownloadStrategy):
    """Standard sequential download strategy."""

    def __init__(self, network_client: Any):
        self.network_client = network_client

    def download(
        self, template_id: str, context: Optional[SecurityContext] = None
    ) -> Optional[TemplateMetadata]:
        """Download template using standard HTTP request."""
        try:
            response = self.network_client.get(f"/templates/{template_id}")
            return TemplateMetadata.from_dict(response)
        except Exception as e:
            logger.error(f"Download failed for {template_id}: {e}")
            return None

    def supports_batch(self) -> bool:
        """Standard strategy doesn't support batch operations."""
        return False


class BatchDownloadStrategy(DownloadStrategy):
    """Optimized batch download strategy."""

    def __init__(self, network_client: Any, max_concurrent: int = 4):
        self.network_client = network_client
        self.max_concurrent = max_concurrent

    def download(
        self, template_id: str, context: Optional[SecurityContext] = None
    ) -> Optional[TemplateMetadata]:
        """Download single template (falls back to standard)."""
        return self.download_batch([template_id], context)[0]

    def download_batch(
        self, template_ids: List[str], context: Optional[SecurityContext] = None
    ) -> List[Optional[TemplateMetadata]]:
        """Download multiple templates concurrently."""
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            futures = {
                executor.submit(self._download_single, tid, context): tid for tid in template_ids
            }

            results = []
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())

            return results

    def _download_single(
        self, template_id: str, context: Optional[SecurityContext] = None
    ) -> Optional[TemplateMetadata]:
        """Download single template."""
        try:
            response = self.network_client.get(f"/templates/{template_id}")
            return TemplateMetadata.from_dict(response)
        except Exception as e:
            logger.error(f"Batch download failed for {template_id}: {e}")
            return None

    def supports_batch(self) -> bool:
        """Batch strategy supports batch operations."""
        return True


class MemoryCacheStrategy(CacheStrategy):
    """In-memory caching strategy."""

    def __init__(self, max_size_mb: float = 100):
        self.cache: Dict[str, Any] = {}
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.current_size = 0

    def get(self, key: str) -> Optional[Any]:
        """Get from memory cache."""
        return self.cache.get(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store in memory cache."""
        # Simple implementation - real version would handle TTL and size limits
        self.cache[key] = value
        return True

    def remove(self, key: str) -> bool:
        """Remove from memory cache."""
        if key in self.cache:
            del self.cache[key]
            return True
        return False

    def get_cache_level(self) -> CacheLevel:
        """Memory cache level."""
        return CacheLevel.MEMORY


class DiskCacheStrategy(CacheStrategy):
    """Disk-based caching strategy."""

    def __init__(self, cache_dir: str, max_size_mb: float = 500):
        from pathlib import Path

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = max_size_mb * 1024 * 1024

    def get(self, key: str) -> Optional[Any]:
        """Get from disk cache."""
        import pickle

        cache_file = self.cache_dir / f"{key}.cache"

        if cache_file.exists():
            try:
                with open(cache_file, "rb") as f:
                    return pickle.load(f)
            except Exception as e:
                logger.error(f"Failed to load from disk cache: {e}")

        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store in disk cache."""
        import pickle

        cache_file = self.cache_dir / f"{key}.cache"

        try:
            with open(cache_file, "wb") as f:
                pickle.dump(value, f)
            return True
        except Exception as e:
            logger.error(f"Failed to save to disk cache: {e}")
            return False

    def remove(self, key: str) -> bool:
        """Remove from disk cache."""
        cache_file = self.cache_dir / f"{key}.cache"
        if cache_file.exists():
            cache_file.unlink()
            return True
        return False

    def get_cache_level(self) -> CacheLevel:
        """Disk cache level."""
        return CacheLevel.DISK


class MinimalValidationStrategy(ValidationStrategy):
    """Minimal validation - basic field checks only."""

    def validate(self, template: TemplateMetadata) -> ValidationResult:
        """Perform minimal validation."""
        errors = []

        # Check required fields
        if not template.id:
            errors.append("Template ID is required")
        if not template.name:
            errors.append("Template name is required")
        if not template.version:
            errors.append("Template version is required")

        return ValidationResult(
            is_valid=len(errors) == 0, errors=errors, validation_level=ValidationLevel.MINIMAL
        )

    def get_validation_level(self) -> ValidationLevel:
        """Minimal validation level."""
        return ValidationLevel.MINIMAL


class StandardValidationStrategy(ValidationStrategy):
    """Standard validation - field checks plus format validation."""

    def validate(self, template: TemplateMetadata) -> ValidationResult:
        """Perform standard validation."""
        errors = []
        warnings = []

        # Basic field validation
        if not template.id:
            errors.append("Template ID is required")
        if not template.name:
            errors.append("Template name is required")
        if not template.version:
            errors.append("Template version is required")
        if not template.content:
            warnings.append("Template content is empty")

        # Version format validation (semver)
        import re

        if template.version and not re.match(r"^\d+\.\d+\.\d+(-\w+)?$", template.version):
            errors.append(f"Invalid version format: {template.version}")

        # Content size check
        if template.content and len(template.content) > 10 * 1024 * 1024:  # 10MB
            warnings.append("Template content exceeds recommended size")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            validation_level=ValidationLevel.STANDARD,
        )

    def get_validation_level(self) -> ValidationLevel:
        """Standard validation level."""
        return ValidationLevel.STANDARD


class StrictValidationStrategy(ValidationStrategy):
    """Strict validation - comprehensive checks including security."""

    def validate(self, template: TemplateMetadata) -> ValidationResult:
        """Perform strict validation."""
        # Start with standard validation
        standard_strategy = StandardValidationStrategy()
        result = standard_strategy.validate(template)

        # Add security checks
        if template.content:
            security_issues = self._check_security(template.content)
            result.errors.extend(security_issues)

        # Signature validation
        if not template.signature or not template.public_key:
            result.warnings.append("Template is not signed")

        result.validation_level = ValidationLevel.STRICT
        result.is_valid = len(result.errors) == 0

        return result

    def _check_security(self, content: str) -> List[str]:
        """Check for security issues in content."""
        import re

        errors = []

        # Check for dangerous patterns
        dangerous_patterns = [
            (r"<script[^>]*>", "Script tags not allowed"),
            (r"javascript:", "JavaScript URLs not allowed"),
            (r"on\w+\s*=", "Event handlers not allowed"),
            (r"eval\s*\(", "eval() not allowed"),
            (r"exec\s*\(", "exec() not allowed"),
        ]

        for pattern, message in dangerous_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                errors.append(message)

        return errors

    def get_validation_level(self) -> ValidationLevel:
        """Strict validation level."""
        return ValidationLevel.STRICT


# ============================================================================
# Factory Classes
# ============================================================================


class DownloadStrategyFactory:
    """Factory for creating download strategies."""

    @staticmethod
    def create(strategy_type: str, network_client: Any, **kwargs) -> DownloadStrategy:
        """Create a download strategy based on type."""
        if strategy_type == "standard":
            return StandardDownloadStrategy(network_client)
        elif strategy_type == "batch":
            max_concurrent = kwargs.get("max_concurrent", 4)
            return BatchDownloadStrategy(network_client, max_concurrent)
        else:
            raise ValueError(f"Unknown download strategy: {strategy_type}")


class CacheStrategyFactory:
    """Factory for creating cache strategies."""

    @staticmethod
    def create(cache_level: CacheLevel, **kwargs) -> CacheStrategy:
        """Create a cache strategy based on level."""
        if cache_level == CacheLevel.MEMORY:
            max_size_mb = kwargs.get("max_size_mb", 100)
            return MemoryCacheStrategy(max_size_mb)
        elif cache_level == CacheLevel.DISK:
            cache_dir = kwargs.get("cache_dir", ".cache")
            max_size_mb = kwargs.get("max_size_mb", 500)
            return DiskCacheStrategy(cache_dir, max_size_mb)
        else:
            raise ValueError(f"Unknown cache level: {cache_level}")


class ValidationStrategyFactory:
    """Factory for creating validation strategies."""

    @staticmethod
    def create(validation_level: ValidationLevel) -> ValidationStrategy:
        """Create a validation strategy based on level."""
        if validation_level == ValidationLevel.MINIMAL:
            return MinimalValidationStrategy()
        elif validation_level == ValidationLevel.STANDARD:
            return StandardValidationStrategy()
        elif validation_level == ValidationLevel.STRICT:
            return StrictValidationStrategy()
        else:
            raise ValueError(f"Unknown validation level: {validation_level}")


class MarketplaceStrategyManager:
    """Manager for coordinating multiple strategies."""

    def __init__(self):
        self.download_strategies: Dict[str, DownloadStrategy] = {}
        self.cache_strategies: Dict[CacheLevel, CacheStrategy] = {}
        self.validation_strategies: Dict[ValidationLevel, ValidationStrategy] = {}

    def register_download_strategy(self, name: str, strategy: DownloadStrategy):
        """Register a download strategy."""
        self.download_strategies[name] = strategy

    def register_cache_strategy(self, level: CacheLevel, strategy: CacheStrategy):
        """Register a cache strategy."""
        self.cache_strategies[level] = strategy

    def register_validation_strategy(self, level: ValidationLevel, strategy: ValidationStrategy):
        """Register a validation strategy."""
        self.validation_strategies[level] = strategy

    def get_download_strategy(self, name: str) -> Optional[DownloadStrategy]:
        """Get a registered download strategy."""
        return self.download_strategies.get(name)

    def get_cache_strategy(self, level: CacheLevel) -> Optional[CacheStrategy]:
        """Get a registered cache strategy."""
        return self.cache_strategies.get(level)

    def get_validation_strategy(self, level: ValidationLevel) -> Optional[ValidationStrategy]:
        """Get a registered validation strategy."""
        return self.validation_strategies.get(level)
