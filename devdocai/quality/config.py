"""
Configuration system for M005 Quality Engine.

Provides centralized configuration management with environment support,
operational modes, and feature flags.
"""

import os
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


class OperationMode(Enum):
    """Operation modes for the quality engine."""
    BASIC = "basic"          # Basic functionality, minimal overhead
    OPTIMIZED = "optimized"  # Performance optimizations enabled
    SECURE = "secure"        # Full security features enabled
    BALANCED = "balanced"    # Balance between performance and security


class CacheStrategy(Enum):
    """Cache strategies for performance optimization."""
    NONE = "none"           # No caching
    MEMORY = "memory"       # In-memory caching only
    MULTI_LEVEL = "multi"   # Multi-level caching with disk fallback
    AGGRESSIVE = "aggressive"  # Aggressive caching with pre-warming


@dataclass
class PerformanceConfig:
    """Performance optimization configuration."""
    enable_parallel: bool = True
    max_workers: int = field(default_factory=lambda: os.cpu_count() or 4)
    enable_streaming: bool = True
    chunk_size: int = 8192
    cache_strategy: CacheStrategy = CacheStrategy.MEMORY
    cache_ttl_seconds: int = 3600
    enable_lazy_loading: bool = True
    enable_object_pooling: bool = True
    batch_size: int = 100
    enable_async: bool = False


@dataclass
class SecurityConfig:
    """Security configuration."""
    enable_input_validation: bool = True
    enable_pii_detection: bool = True
    enable_rate_limiting: bool = True
    rate_limit_per_minute: int = 60
    enable_audit_logging: bool = True
    enable_secure_regex: bool = True
    max_regex_complexity: int = 100
    enable_content_sanitization: bool = True
    max_document_size_mb: int = 50
    enable_dos_protection: bool = True
    timeout_seconds: int = 30
    pii_types_to_detect: list = field(default_factory=lambda: ['email', 'phone', 'ssn', 'credit_card'])
    audit_log_format: str = 'json'
    audit_log_path: str = '/tmp/quality_audit.log'  # Path for audit logs
    max_document_size_bytes: int = field(default_factory=lambda: 50 * 1024 * 1024)
    regex_timeout: int = 5  # Timeout for regex operations in seconds


@dataclass
class QualityThresholds:
    """Quality gate thresholds."""
    min_overall_score: float = 0.7
    min_dimension_score: float = 0.5
    max_critical_issues: int = 0
    max_major_issues: int = 5
    max_minor_issues: int = 20
    fail_on_error: bool = True


@dataclass
class DimensionWeights:
    """Weights for quality dimensions."""
    completeness: float = 0.25
    clarity: float = 0.20
    structure: float = 0.20
    accuracy: float = 0.20
    formatting: float = 0.15

    def __post_init__(self):
        """Validate weights sum to 1.0."""
        total = sum([
            self.completeness, self.clarity, self.structure,
            self.accuracy, self.formatting
        ])
        if abs(total - 1.0) > 0.001:
            # Normalize weights
            self.completeness /= total
            self.clarity /= total
            self.structure /= total
            self.accuracy /= total
            self.formatting /= total


@dataclass
class QualityEngineConfig:
    """Main configuration for the Quality Engine."""
    
    # Operation mode
    mode: OperationMode = OperationMode.BALANCED
    
    # Sub-configurations
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    thresholds: QualityThresholds = field(default_factory=QualityThresholds)
    weights: DimensionWeights = field(default_factory=DimensionWeights)
    
    # Feature flags
    enable_integration: bool = True
    enable_telemetry: bool = False
    enable_experimental: bool = False
    
    # Paths
    cache_dir: Optional[str] = None
    log_dir: Optional[str] = None
    
    @classmethod
    def from_mode(cls, mode: OperationMode) -> "QualityEngineConfig":
        """Create configuration from operation mode."""
        config = cls(mode=mode)
        
        if mode == OperationMode.BASIC:
            # Minimal features for basic mode
            config.performance.enable_parallel = False
            config.performance.cache_strategy = CacheStrategy.NONE
            config.security.enable_input_validation = True
            config.security.enable_rate_limiting = False
            
        elif mode == OperationMode.OPTIMIZED:
            # Maximum performance
            config.performance.cache_strategy = CacheStrategy.AGGRESSIVE
            config.performance.enable_async = True
            config.security.enable_rate_limiting = False
            config.security.enable_audit_logging = False
            
        elif mode == OperationMode.SECURE:
            # Maximum security
            config.security = SecurityConfig(
                enable_input_validation=True,
                enable_pii_detection=True,
                enable_rate_limiting=True,
                enable_audit_logging=True,
                enable_secure_regex=True,
                enable_content_sanitization=True,
                enable_dos_protection=True
            )
            config.performance.enable_async = False  # Sync for better control
            
        elif mode == OperationMode.BALANCED:
            # Balanced defaults (already set)
            pass
            
        return config
    
    @classmethod
    def from_env(cls) -> "QualityEngineConfig":
        """Create configuration from environment variables."""
        mode_str = os.getenv("QUALITY_ENGINE_MODE", "balanced").lower()
        mode = OperationMode(mode_str)
        
        config = cls.from_mode(mode)
        
        # Override from environment
        if os.getenv("QUALITY_CACHE_DIR"):
            config.cache_dir = os.getenv("QUALITY_CACHE_DIR")
        
        if os.getenv("QUALITY_MAX_WORKERS"):
            config.performance.max_workers = int(os.getenv("QUALITY_MAX_WORKERS"))
        
        if os.getenv("QUALITY_ENABLE_TELEMETRY"):
            config.enable_telemetry = os.getenv("QUALITY_ENABLE_TELEMETRY").lower() == "true"
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "mode": self.mode.value,
            "performance": {
                "enable_parallel": self.performance.enable_parallel,
                "max_workers": self.performance.max_workers,
                "cache_strategy": self.performance.cache_strategy.value,
                "batch_size": self.performance.batch_size,
            },
            "security": {
                "enable_input_validation": self.security.enable_input_validation,
                "enable_pii_detection": self.security.enable_pii_detection,
                "enable_rate_limiting": self.security.enable_rate_limiting,
            },
            "thresholds": {
                "min_overall_score": self.thresholds.min_overall_score,
                "max_critical_issues": self.thresholds.max_critical_issues,
            },
            "weights": {
                "completeness": self.weights.completeness,
                "clarity": self.weights.clarity,
                "structure": self.weights.structure,
                "accuracy": self.weights.accuracy,
                "formatting": self.weights.formatting,
            }
        }


# Default configurations for common use cases
PRESETS = {
    "development": QualityEngineConfig.from_mode(OperationMode.BASIC),
    "production": QualityEngineConfig.from_mode(OperationMode.BALANCED),
    "performance": QualityEngineConfig.from_mode(OperationMode.OPTIMIZED),
    "security": QualityEngineConfig.from_mode(OperationMode.SECURE),
}