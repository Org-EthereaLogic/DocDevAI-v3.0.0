"""
Unified configuration for Document Generator with mode-based behavior.

This module provides a single configuration system that replaces the scattered
configuration across basic, optimized, and secure implementations.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Optional, Any, List
from pathlib import Path


class GenerationMode(Enum):
    """
    Document generation operation modes.
    
    Each mode enables different features and optimizations:
    - BASIC: Core functionality only, minimal overhead
    - PERFORMANCE: Caching, parallel processing, token optimization
    - SECURE: Security hardening, PII protection, audit logging
    - ENTERPRISE: All features enabled for production use
    """
    BASIC = "basic"
    PERFORMANCE = "performance"
    SECURE = "secure"
    ENTERPRISE = "enterprise"


@dataclass
class CacheConfig:
    """Configuration for caching system."""
    enabled: bool = False
    semantic_cache_size: int = 1000
    fragment_cache_size: int = 5000
    ttl_seconds: int = 3600
    similarity_threshold: float = 0.85
    memory_limit_mb: int = 500
    encryption_enabled: bool = False


@dataclass
class SecurityConfig:
    """Configuration for security features."""
    enabled: bool = False
    
    # Rate limiting
    rate_limiting_enabled: bool = False
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 10
    
    # Prompt security
    prompt_injection_detection: bool = False
    injection_patterns_file: Optional[Path] = None
    threat_threshold: float = 0.7
    
    # PII protection
    pii_detection_enabled: bool = False
    pii_sensitivity_level: str = "medium"  # low, medium, high
    pii_redaction_enabled: bool = False
    
    # Audit logging
    audit_logging_enabled: bool = False
    audit_log_path: Optional[Path] = None
    log_encryption: bool = False
    
    # Access control
    access_control_enabled: bool = False
    require_authentication: bool = False
    role_based_permissions: bool = False


@dataclass
class PerformanceConfig:
    """Configuration for performance optimization."""
    enabled: bool = False
    
    # Parallel processing
    parallel_generation: bool = False
    max_workers: int = 4
    batch_size: int = 10
    
    # Token optimization
    token_optimization_enabled: bool = False
    compression_level: str = "medium"  # low, medium, high
    max_context_reuse: int = 3
    
    # Streaming
    streaming_enabled: bool = False
    chunk_size: int = 100
    buffer_size: int = 1000
    
    # Resource management
    memory_monitoring: bool = False
    cpu_threshold: float = 0.8
    memory_threshold: float = 0.85


@dataclass
class LLMConfig:
    """Configuration for LLM integration."""
    providers: List[str] = field(default_factory=list)
    multi_llm_synthesis: bool = False
    synthesis_strategy: str = "weighted_average"  # weighted_average, majority_vote, best_of
    fallback_enabled: bool = True
    timeout_seconds: int = 60
    max_retries: int = 3
    
    # Cost management
    cost_tracking_enabled: bool = False
    daily_limit_usd: float = 10.0
    monthly_limit_usd: float = 200.0


@dataclass
class UnifiedGenerationConfig:
    """
    Unified configuration for document generation.
    
    This replaces the multiple configuration systems from the three implementations
    and provides a single, mode-driven configuration approach.
    """
    mode: GenerationMode = GenerationMode.BASIC
    
    # Component configurations
    cache: CacheConfig = field(default_factory=CacheConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    
    # General settings
    template_dir: Path = Path("devdocai/templates/prompt_templates/generation")
    output_dir: Path = Path("outputs")
    max_document_size_mb: int = 10
    enable_miair_optimization: bool = True
    enable_quality_checks: bool = True
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    @classmethod
    def from_mode(cls, mode: GenerationMode) -> "UnifiedGenerationConfig":
        """
        Factory method to create configuration based on mode.
        
        This provides sensible defaults for each mode while allowing customization.
        """
        config = cls(mode=mode)
        
        if mode == GenerationMode.BASIC:
            # Minimal configuration for basic operation
            pass
            
        elif mode == GenerationMode.PERFORMANCE:
            # Enable all performance optimizations
            config.cache = CacheConfig(
                enabled=True,
                semantic_cache_size=2000,
                fragment_cache_size=10000,
                ttl_seconds=7200
            )
            config.performance = PerformanceConfig(
                enabled=True,
                parallel_generation=True,
                token_optimization_enabled=True,
                streaming_enabled=True,
                memory_monitoring=True
            )
            config.llm.multi_llm_synthesis = True
            
        elif mode == GenerationMode.SECURE:
            # Enable all security features
            config.security = SecurityConfig(
                enabled=True,
                rate_limiting_enabled=True,
                prompt_injection_detection=True,
                pii_detection_enabled=True,
                pii_redaction_enabled=True,
                audit_logging_enabled=True,
                access_control_enabled=True
            )
            config.cache.encryption_enabled = True
            
        elif mode == GenerationMode.ENTERPRISE:
            # Enable everything for production use
            config.cache = CacheConfig(
                enabled=True,
                semantic_cache_size=5000,
                fragment_cache_size=20000,
                ttl_seconds=14400,
                encryption_enabled=True
            )
            config.security = SecurityConfig(
                enabled=True,
                rate_limiting_enabled=True,
                prompt_injection_detection=True,
                pii_detection_enabled=True,
                pii_redaction_enabled=True,
                audit_logging_enabled=True,
                log_encryption=True,
                access_control_enabled=True,
                require_authentication=True,
                role_based_permissions=True
            )
            config.performance = PerformanceConfig(
                enabled=True,
                parallel_generation=True,
                max_workers=8,
                token_optimization_enabled=True,
                compression_level="high",
                streaming_enabled=True,
                memory_monitoring=True
            )
            config.llm = LLMConfig(
                multi_llm_synthesis=True,
                synthesis_strategy="best_of",
                cost_tracking_enabled=True
            )
            
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        return {
            "mode": self.mode.value,
            "cache": {
                "enabled": self.cache.enabled,
                "semantic_cache_size": self.cache.semantic_cache_size,
                "fragment_cache_size": self.cache.fragment_cache_size,
                "ttl_seconds": self.cache.ttl_seconds,
                "similarity_threshold": self.cache.similarity_threshold,
                "memory_limit_mb": self.cache.memory_limit_mb,
                "encryption_enabled": self.cache.encryption_enabled
            },
            "security": {
                "enabled": self.security.enabled,
                "rate_limiting_enabled": self.security.rate_limiting_enabled,
                "prompt_injection_detection": self.security.prompt_injection_detection,
                "pii_detection_enabled": self.security.pii_detection_enabled,
                "audit_logging_enabled": self.security.audit_logging_enabled
            },
            "performance": {
                "enabled": self.performance.enabled,
                "parallel_generation": self.performance.parallel_generation,
                "token_optimization_enabled": self.performance.token_optimization_enabled,
                "streaming_enabled": self.performance.streaming_enabled
            },
            "llm": {
                "providers": self.llm.providers,
                "multi_llm_synthesis": self.llm.multi_llm_synthesis,
                "cost_tracking_enabled": self.llm.cost_tracking_enabled
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UnifiedGenerationConfig":
        """Create configuration from dictionary."""
        mode = GenerationMode(data.get("mode", "basic"))
        config = cls.from_mode(mode)
        
        # Update with provided values
        if "cache" in data:
            for key, value in data["cache"].items():
                if hasattr(config.cache, key):
                    setattr(config.cache, key, value)
        
        if "security" in data:
            for key, value in data["security"].items():
                if hasattr(config.security, key):
                    setattr(config.security, key, value)
        
        if "performance" in data:
            for key, value in data["performance"].items():
                if hasattr(config.performance, key):
                    setattr(config.performance, key, value)
        
        if "llm" in data:
            for key, value in data["llm"].items():
                if hasattr(config.llm, key):
                    setattr(config.llm, key, value)
        
        return config