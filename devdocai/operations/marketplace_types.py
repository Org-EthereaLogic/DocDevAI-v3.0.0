"""
M013 Template Marketplace - Type Definitions and Data Structures
DevDocAI v3.0.0 - Pass 4: Refactoring & Integration

This module contains all type definitions, data classes, and enums for the
marketplace system, following the clean architecture pattern from other modules.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional

# ============================================================================
# Enums
# ============================================================================


class MarketplaceOperation(Enum):
    """Marketplace operation types for tracking and validation."""

    DISCOVER = "discover"
    DOWNLOAD = "download"
    UPLOAD = "upload"
    UPDATE = "update"
    DELETE = "delete"
    VERIFY = "verify"
    CACHE = "cache"


class CacheLevel(Enum):
    """Cache levels for multi-tier caching."""

    MEMORY = auto()
    DISK = auto()
    COMPRESSED = auto()
    NETWORK = auto()


class ValidationLevel(Enum):
    """Validation strictness levels."""

    MINIMAL = auto()
    STANDARD = auto()
    STRICT = auto()


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class TemplateMetadata:
    """Template metadata structure with complete information."""

    id: str
    name: str
    description: str
    version: str
    author: str
    content: str = ""
    tags: List[str] = field(default_factory=list)
    downloads: int = 0
    rating: float = 0.0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    signature: Optional[str] = None
    public_key: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "content": self.content,
            "tags": self.tags,
            "downloads": self.downloads,
            "rating": self.rating,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "signature": self.signature,
            "public_key": self.public_key,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TemplateMetadata":
        """Create from dictionary representation."""
        # Handle datetime fields
        if "created_at" in data and data["created_at"]:
            if isinstance(data["created_at"], str):
                data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data and data["updated_at"]:
            if isinstance(data["updated_at"], str):
                data["updated_at"] = datetime.fromisoformat(data["updated_at"])

        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class CacheEntry:
    """Cache entry with metadata."""

    key: str
    value: Any
    cached_at: datetime
    expires_at: datetime
    hit_count: int = 0
    size_bytes: int = 0
    compression_ratio: float = 1.0
    cache_level: CacheLevel = CacheLevel.MEMORY


@dataclass
class ValidationResult:
    """Result of template validation."""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    security_score: float = 0.0
    validation_level: ValidationLevel = ValidationLevel.STANDARD
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Performance metrics for marketplace operations."""

    operation: MarketplaceOperation
    duration_ms: float
    cache_hits: int = 0
    cache_misses: int = 0
    network_calls: int = 0
    bytes_transferred: int = 0
    error_count: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SecurityContext:
    """Security context for marketplace operations."""

    client_id: str
    operation: MarketplaceOperation
    rate_limit_remaining: int
    requires_signature: bool
    validation_level: ValidationLevel
    trusted_keys: List[str] = field(default_factory=list)
    audit_enabled: bool = True


# ============================================================================
# Exceptions
# ============================================================================


class MarketplaceError(Exception):
    """Base exception for marketplace errors."""

    pass


class TemplateVerificationError(MarketplaceError):
    """Template signature verification failed."""

    pass


class NetworkError(MarketplaceError):
    """Network communication error."""

    pass


class CacheError(MarketplaceError):
    """Cache operation error."""

    pass


class ValidationError(MarketplaceError):
    """Template validation error."""

    pass


class RateLimitError(MarketplaceError):
    """Rate limit exceeded error."""

    pass


class SecurityError(MarketplaceError):
    """Security validation error."""

    pass


# ============================================================================
# Type Aliases
# ============================================================================

TemplateDict = Dict[str, Any]
MetricsDict = Dict[str, Any]
ConfigDict = Dict[str, Any]
