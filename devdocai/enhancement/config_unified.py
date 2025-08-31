"""
Unified Configuration system for M009 Enhancement Pipeline.

Provides mode-based operation with BASIC, PERFORMANCE, SECURE, and ENTERPRISE modes.
Consolidates all configuration management with intelligent defaults and validation.
"""

from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
import json

# Import original enums and basic classes
from .config import OperationMode, EnhancementType


class UnifiedOperationMode(Enum):
    """Unified operation modes for the enhancement pipeline."""
    BASIC = "basic"          # Minimal enhancements, fast processing, no security overhead
    PERFORMANCE = "performance"  # Optimized for speed with caching and parallelization
    SECURE = "secure"        # Security-focused with validation and audit logging
    ENTERPRISE = "enterprise"  # Full feature set: performance + security + monitoring


@dataclass
class UnifiedStrategyConfig:
    """Unified configuration for enhancement strategies across all modes."""
    
    # Core settings
    enabled: bool = True
    priority: int = 1
    max_iterations: int = 3
    quality_threshold: float = 0.8
    llm_provider: Optional[str] = None
    custom_parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Performance settings
    use_caching: bool = True
    parallel_execution: bool = False
    batch_optimization: bool = False
    
    # Security settings
    input_validation: bool = False
    output_sanitization: bool = False
    audit_logging: bool = False
    
    # Strategy-specific settings
    strategy_settings: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def for_mode(cls, mode: UnifiedOperationMode, strategy_type: EnhancementType) -> 'UnifiedStrategyConfig':
        """Create strategy config optimized for specific mode."""
        config = cls()
        
        if mode == UnifiedOperationMode.BASIC:
            config.enabled = strategy_type in [EnhancementType.CLARITY, EnhancementType.READABILITY]
            config.max_iterations = 1
            config.use_caching = False
            config.parallel_execution = False
            
        elif mode == UnifiedOperationMode.PERFORMANCE:
            config.enabled = True
            config.max_iterations = 2
            config.use_caching = True
            config.parallel_execution = True
            config.batch_optimization = True
            
        elif mode == UnifiedOperationMode.SECURE:
            config.enabled = True
            config.max_iterations = 3
            config.input_validation = True
            config.output_sanitization = True
            config.audit_logging = True
            config.use_caching = True  # Secure cache
            
        elif mode == UnifiedOperationMode.ENTERPRISE:
            config.enabled = True
            config.max_iterations = 5
            config.quality_threshold = 0.9
            config.use_caching = True
            config.parallel_execution = True
            config.batch_optimization = True
            config.input_validation = True
            config.output_sanitization = True
            config.audit_logging = True
        
        # Set strategy-specific defaults
        config.strategy_settings = cls._get_strategy_defaults(strategy_type, mode)
        
        return config
    
    @staticmethod
    def _get_strategy_defaults(strategy_type: EnhancementType, mode: UnifiedOperationMode) -> Dict[str, Any]:
        """Get strategy-specific default settings based on mode."""
        defaults = {
            EnhancementType.CLARITY: {
                "simplify_sentences": True,
                "reduce_jargon": True,
                "improve_transitions": True,
                "max_sentence_length": 25 if mode != UnifiedOperationMode.BASIC else 30
            },
            EnhancementType.COMPLETENESS: {
                "fill_gaps": True,
                "add_examples": True,
                "expand_sections": mode != UnifiedOperationMode.BASIC,
                "min_section_length": 100 if mode != UnifiedOperationMode.BASIC else 50
            },
            EnhancementType.CONSISTENCY: {
                "standardize_terminology": True,
                "unify_formatting": True,
                "align_tone": True,
                "enforce_style_guide": mode in [UnifiedOperationMode.SECURE, UnifiedOperationMode.ENTERPRISE]
            },
            EnhancementType.ACCURACY: {
                "fact_checking": mode in [UnifiedOperationMode.SECURE, UnifiedOperationMode.ENTERPRISE],
                "citation_validation": mode == UnifiedOperationMode.ENTERPRISE,
                "technical_review": True,
                "cross_reference": mode != UnifiedOperationMode.BASIC
            },
            EnhancementType.READABILITY: {
                "target_grade_level": 10,
                "optimize_structure": True,
                "improve_flow": True,
                "add_summaries": mode in [UnifiedOperationMode.SECURE, UnifiedOperationMode.ENTERPRISE]
            }
        }
        return defaults.get(strategy_type, {})


@dataclass
class UnifiedPipelineConfig:
    """Unified pipeline configuration with mode-specific optimizations."""
    
    # Core behavior
    max_enhancement_passes: int = 3
    parallel_processing: bool = False
    batch_size: int = 5
    timeout_seconds: int = 300
    
    # Quality control
    min_improvement_threshold: float = 0.05
    quality_check_interval: int = 1
    rollback_on_degradation: bool = True
    
    # Cost management
    max_cost_per_document: float = 0.30
    cost_optimization: bool = True
    
    # Caching configuration
    use_cache: bool = False
    cache_size: int = 500
    cache_ttl_seconds: int = 3600
    use_secure_cache: bool = False
    use_semantic_cache: bool = False
    cache_encryption: bool = False
    
    # Performance configuration
    enable_performance_optimization: bool = False
    max_workers: int = 2
    max_concurrent: int = 5
    use_connection_pooling: bool = False
    enable_streaming: bool = False
    fast_path_threshold: int = 500
    
    # Security configuration
    enable_security_validation: bool = False
    enable_rate_limiting: bool = False
    enable_audit_logging: bool = False
    enable_resource_protection: bool = False
    security_profile: str = "standard"
    
    # Integration settings
    use_miair_optimization: bool = True
    use_quality_engine: bool = True
    use_review_feedback: bool = True
    
    # Monitoring and reporting
    enable_monitoring: bool = False
    enable_performance_tracking: bool = False
    detailed_reporting: bool = False
    preserve_originals: bool = True
    
    # Resource limits
    max_memory_mb: int = 256
    max_concurrent_enhancements: int = 3
    rate_limit_per_minute: int = 30
    
    @classmethod
    def for_mode(cls, mode: UnifiedOperationMode) -> 'UnifiedPipelineConfig':
        """Create pipeline config optimized for specific mode."""
        if mode == UnifiedOperationMode.BASIC:
            return cls(
                max_enhancement_passes=2,
                parallel_processing=False,
                batch_size=3,
                timeout_seconds=120,
                max_cost_per_document=0.10,
                use_cache=False,
                max_workers=1,
                max_concurrent=1,
                max_memory_mb=128,
                max_concurrent_enhancements=1,
                rate_limit_per_minute=15
            )
        
        elif mode == UnifiedOperationMode.PERFORMANCE:
            return cls(
                max_enhancement_passes=3,
                parallel_processing=True,
                batch_size=20,
                timeout_seconds=200,
                max_cost_per_document=0.30,
                use_cache=True,
                cache_size=2000,
                use_semantic_cache=True,
                enable_performance_optimization=True,
                max_workers=8,
                max_concurrent=15,
                use_connection_pooling=True,
                enable_streaming=True,
                fast_path_threshold=300,
                enable_monitoring=True,
                enable_performance_tracking=True,
                max_memory_mb=512,
                max_concurrent_enhancements=10,
                rate_limit_per_minute=120
            )
        
        elif mode == UnifiedOperationMode.SECURE:
            return cls(
                max_enhancement_passes=3,
                parallel_processing=True,
                batch_size=10,
                timeout_seconds=300,
                max_cost_per_document=0.40,
                use_cache=True,
                cache_size=1000,
                use_secure_cache=True,
                cache_encryption=True,
                enable_security_validation=True,
                enable_rate_limiting=True,
                enable_audit_logging=True,
                enable_resource_protection=True,
                security_profile="strict",
                enable_monitoring=True,
                detailed_reporting=True,
                max_workers=4,
                max_concurrent=8,
                max_memory_mb=384,
                max_concurrent_enhancements=5,
                rate_limit_per_minute=60
            )
        
        elif mode == UnifiedOperationMode.ENTERPRISE:
            return cls(
                max_enhancement_passes=5,
                parallel_processing=True,
                batch_size=25,
                timeout_seconds=600,
                max_cost_per_document=1.00,
                cost_optimization=False,
                use_cache=True,
                cache_size=5000,
                use_secure_cache=True,
                use_semantic_cache=True,
                cache_encryption=True,
                enable_performance_optimization=True,
                enable_security_validation=True,
                enable_rate_limiting=True,
                enable_audit_logging=True,
                enable_resource_protection=True,
                security_profile="paranoid",
                enable_monitoring=True,
                enable_performance_tracking=True,
                detailed_reporting=True,
                max_workers=16,
                max_concurrent=25,
                use_connection_pooling=True,
                enable_streaming=True,
                fast_path_threshold=200,
                max_memory_mb=1024,
                max_concurrent_enhancements=15,
                rate_limit_per_minute=200
            )
        
        else:
            return cls()  # Default settings


@dataclass
class UnifiedEnhancementSettings:
    """Unified settings for the Enhancement Pipeline with mode-based configuration."""
    
    operation_mode: UnifiedOperationMode = UnifiedOperationMode.PERFORMANCE
    
    # Strategy configurations - auto-configured based on mode
    strategies: Dict[EnhancementType, UnifiedStrategyConfig] = field(default_factory=dict)
    
    # Pipeline configuration - auto-configured based on mode
    pipeline: UnifiedPipelineConfig = field(default_factory=UnifiedPipelineConfig)
    
    # LLM settings
    llm_settings: Dict[str, Any] = field(default_factory=lambda: {
        "primary_provider": "openai",
        "fallback_providers": ["anthropic", "local"],
        "temperature": 0.7,
        "max_tokens": 2000,
        "streaming": True,
        "multi_provider_synthesis": False
    })
    
    # Logging and monitoring
    logging_config: Dict[str, Any] = field(default_factory=lambda: {
        "level": "INFO",
        "file": "enhancement_unified.log",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "enable_metrics": True,
        "enable_audit": False
    })
    
    def __post_init__(self):
        """Initialize strategies and pipeline based on operation mode."""
        # Auto-configure strategies for the selected mode
        if not self.strategies:
            self.strategies = {
                strategy_type: UnifiedStrategyConfig.for_mode(self.operation_mode, strategy_type)
                for strategy_type in EnhancementType if strategy_type != EnhancementType.ALL
            }
        
        # Auto-configure pipeline for the selected mode
        if self.pipeline.__dict__ == UnifiedPipelineConfig().__dict__:
            self.pipeline = UnifiedPipelineConfig.for_mode(self.operation_mode)
        
        # Adjust LLM settings based on mode
        if self.operation_mode == UnifiedOperationMode.BASIC:
            self.llm_settings["multi_provider_synthesis"] = False
            self.llm_settings["temperature"] = 0.8  # More creative for speed
        elif self.operation_mode == UnifiedOperationMode.ENTERPRISE:
            self.llm_settings["multi_provider_synthesis"] = True
            self.llm_settings["temperature"] = 0.5  # More focused
        
        # Adjust logging based on mode
        if self.operation_mode in [UnifiedOperationMode.SECURE, UnifiedOperationMode.ENTERPRISE]:
            self.logging_config["enable_audit"] = True
            self.logging_config["level"] = "DEBUG" if self.operation_mode == UnifiedOperationMode.ENTERPRISE else "INFO"
    
    @classmethod
    def create(
        cls, 
        mode: Union[str, UnifiedOperationMode] = UnifiedOperationMode.PERFORMANCE,
        **overrides
    ) -> 'UnifiedEnhancementSettings':
        """
        Create settings for specified mode with optional overrides.
        
        Args:
            mode: Operation mode (string or enum)
            **overrides: Override any default settings
            
        Returns:
            Configured UnifiedEnhancementSettings
        """
        if isinstance(mode, str):
            mode = UnifiedOperationMode(mode.lower())
        
        settings = cls(operation_mode=mode)
        
        # Apply overrides
        for key, value in overrides.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
            elif hasattr(settings.pipeline, key):
                setattr(settings.pipeline, key, value)
            elif key.startswith('llm_'):
                settings.llm_settings[key[4:]] = value
            elif key.startswith('logging_'):
                settings.logging_config[key[8:]] = value
        
        return settings
    
    def get_feature_summary(self) -> Dict[str, Any]:
        """Get a summary of enabled features based on current configuration."""
        return {
            "mode": self.operation_mode.value,
            "features": {
                "caching": self.pipeline.use_cache,
                "secure_cache": self.pipeline.use_secure_cache,
                "semantic_cache": self.pipeline.use_semantic_cache,
                "encryption": self.pipeline.cache_encryption,
                "parallel_processing": self.pipeline.parallel_processing,
                "performance_optimization": self.pipeline.enable_performance_optimization,
                "security_validation": self.pipeline.enable_security_validation,
                "rate_limiting": self.pipeline.enable_rate_limiting,
                "audit_logging": self.pipeline.enable_audit_logging,
                "resource_protection": self.pipeline.enable_resource_protection,
                "monitoring": self.pipeline.enable_monitoring,
                "streaming": self.pipeline.enable_streaming,
                "miair_integration": self.pipeline.use_miair_optimization,
                "quality_integration": self.pipeline.use_quality_engine
            },
            "performance": {
                "max_workers": self.pipeline.max_workers,
                "max_concurrent": self.pipeline.max_concurrent,
                "batch_size": self.pipeline.batch_size,
                "cache_size": self.pipeline.cache_size,
                "timeout": self.pipeline.timeout_seconds,
                "memory_limit": self.pipeline.max_memory_mb
            },
            "strategies": {
                strategy.value: {
                    "enabled": config.enabled,
                    "priority": config.priority,
                    "caching": config.use_caching,
                    "parallel": config.parallel_execution,
                    "validation": config.input_validation
                }
                for strategy, config in self.strategies.items()
            }
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary for serialization."""
        return {
            "operation_mode": self.operation_mode.value,
            "strategies": {
                k.value: {
                    "enabled": v.enabled,
                    "priority": v.priority,
                    "max_iterations": v.max_iterations,
                    "quality_threshold": v.quality_threshold,
                    "use_caching": v.use_caching,
                    "parallel_execution": v.parallel_execution,
                    "input_validation": v.input_validation,
                    "output_sanitization": v.output_sanitization,
                    "audit_logging": v.audit_logging,
                    "strategy_settings": v.strategy_settings
                }
                for k, v in self.strategies.items()
            },
            "pipeline": {
                "max_enhancement_passes": self.pipeline.max_enhancement_passes,
                "parallel_processing": self.pipeline.parallel_processing,
                "batch_size": self.pipeline.batch_size,
                "timeout_seconds": self.pipeline.timeout_seconds,
                "use_cache": self.pipeline.use_cache,
                "cache_size": self.pipeline.cache_size,
                "use_secure_cache": self.pipeline.use_secure_cache,
                "cache_encryption": self.pipeline.cache_encryption,
                "enable_performance_optimization": self.pipeline.enable_performance_optimization,
                "enable_security_validation": self.pipeline.enable_security_validation,
                "max_workers": self.pipeline.max_workers,
                "max_concurrent": self.pipeline.max_concurrent,
                "cost_optimization": self.pipeline.cost_optimization,
                "max_cost_per_document": self.pipeline.max_cost_per_document
            },
            "llm_settings": self.llm_settings,
            "logging_config": self.logging_config
        }
    
    def save(self, path: Path) -> None:
        """Save settings to JSON file."""
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, path: Path) -> 'UnifiedEnhancementSettings':
        """Load settings from JSON file."""
        with open(path, 'r') as f:
            data = json.load(f)
        
        mode = UnifiedOperationMode(data.get("operation_mode", "performance"))
        settings = cls(operation_mode=mode)
        
        # Override with loaded data
        if "strategies" in data:
            for strategy_name, config in data["strategies"].items():
                strategy_type = EnhancementType(strategy_name)
                if strategy_type in settings.strategies:
                    strategy_config = settings.strategies[strategy_type]
                    for key, value in config.items():
                        if hasattr(strategy_config, key):
                            setattr(strategy_config, key, value)
        
        if "pipeline" in data:
            for key, value in data["pipeline"].items():
                if hasattr(settings.pipeline, key):
                    setattr(settings.pipeline, key, value)
        
        if "llm_settings" in data:
            settings.llm_settings.update(data["llm_settings"])
        
        if "logging_config" in data:
            settings.logging_config.update(data["logging_config"])
        
        return settings


# Factory functions for easy creation
def create_basic_settings(**overrides) -> UnifiedEnhancementSettings:
    """Create BASIC mode settings - minimal features, maximum speed."""
    return UnifiedEnhancementSettings.create(UnifiedOperationMode.BASIC, **overrides)


def create_performance_settings(**overrides) -> UnifiedEnhancementSettings:
    """Create PERFORMANCE mode settings - optimized for speed and throughput."""
    return UnifiedEnhancementSettings.create(UnifiedOperationMode.PERFORMANCE, **overrides)


def create_secure_settings(**overrides) -> UnifiedEnhancementSettings:
    """Create SECURE mode settings - security-focused with validation."""
    return UnifiedEnhancementSettings.create(UnifiedOperationMode.SECURE, **overrides)


def create_enterprise_settings(**overrides) -> UnifiedEnhancementSettings:
    """Create ENTERPRISE mode settings - full feature set."""
    return UnifiedEnhancementSettings.create(UnifiedOperationMode.ENTERPRISE, **overrides)