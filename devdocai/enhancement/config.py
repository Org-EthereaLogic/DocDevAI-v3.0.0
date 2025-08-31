"""
Configuration management for M009 Enhancement Pipeline.

Provides flexible configuration for enhancement strategies, pipeline settings,
and operation modes.
"""

from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
import json


class OperationMode(Enum):
    """Operation modes for the enhancement pipeline."""
    BASIC = "basic"          # Minimal enhancements, fast processing
    STANDARD = "standard"    # Balanced quality and performance
    ADVANCED = "advanced"    # Maximum quality, all strategies
    CUSTOM = "custom"        # User-defined configuration


class EnhancementType(Enum):
    """Types of document enhancements."""
    CLARITY = "clarity"
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    ACCURACY = "accuracy"
    READABILITY = "readability"
    ALL = "all"


@dataclass
class StrategyConfig:
    """Configuration for individual enhancement strategies."""
    
    enabled: bool = True
    priority: int = 1  # Higher priority strategies run first
    max_iterations: int = 3
    quality_threshold: float = 0.8  # Minimum quality score to accept enhancement
    llm_provider: Optional[str] = None  # Specific LLM for this strategy
    custom_parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Strategy-specific settings
    clarity_settings: Dict[str, Any] = field(default_factory=lambda: {
        "simplify_sentences": True,
        "reduce_jargon": True,
        "improve_transitions": True,
        "max_sentence_length": 25
    })
    
    completeness_settings: Dict[str, Any] = field(default_factory=lambda: {
        "fill_gaps": True,
        "add_examples": True,
        "expand_sections": True,
        "min_section_length": 100
    })
    
    consistency_settings: Dict[str, Any] = field(default_factory=lambda: {
        "standardize_terminology": True,
        "unify_formatting": True,
        "align_tone": True,
        "enforce_style_guide": False
    })
    
    accuracy_settings: Dict[str, Any] = field(default_factory=lambda: {
        "fact_checking": True,
        "citation_validation": True,
        "technical_review": True,
        "cross_reference": True
    })
    
    readability_settings: Dict[str, Any] = field(default_factory=lambda: {
        "target_grade_level": 10,
        "optimize_structure": True,
        "improve_flow": True,
        "add_summaries": True
    })


@dataclass
class PipelineConfig:
    """Configuration for the enhancement pipeline."""
    
    # Pipeline behavior
    max_enhancement_passes: int = 5
    parallel_processing: bool = True
    batch_size: int = 10
    timeout_seconds: int = 300
    
    # Quality control
    min_improvement_threshold: float = 0.05  # Minimum improvement to accept
    quality_check_interval: int = 1  # Check quality every N passes
    rollback_on_degradation: bool = True
    
    # Cost management
    max_cost_per_document: float = 0.50  # Maximum LLM cost per document
    cost_optimization: bool = True
    use_cache: bool = True
    cache_ttl_seconds: int = 3600
    
    # Integration settings
    use_miair_optimization: bool = True
    use_quality_engine: bool = True
    use_review_feedback: bool = True
    
    # Output settings
    preserve_originals: bool = True
    generate_comparison: bool = True
    detailed_reporting: bool = True
    
    # Resource limits
    max_memory_mb: int = 512
    max_concurrent_enhancements: int = 5
    rate_limit_per_minute: int = 60


@dataclass
class EnhancementSettings:
    """Main configuration for the Enhancement Pipeline."""
    
    operation_mode: OperationMode = OperationMode.STANDARD
    
    # Strategy configurations
    strategies: Dict[EnhancementType, StrategyConfig] = field(default_factory=lambda: {
        EnhancementType.CLARITY: StrategyConfig(priority=1),
        EnhancementType.COMPLETENESS: StrategyConfig(priority=2),
        EnhancementType.CONSISTENCY: StrategyConfig(priority=3),
        EnhancementType.ACCURACY: StrategyConfig(priority=4),
        EnhancementType.READABILITY: StrategyConfig(priority=5)
    })
    
    # Pipeline configuration
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    
    # LLM settings
    llm_settings: Dict[str, Any] = field(default_factory=lambda: {
        "primary_provider": "openai",
        "fallback_providers": ["anthropic", "local"],
        "temperature": 0.7,
        "max_tokens": 2000,
        "streaming": True,
        "multi_provider_synthesis": True
    })
    
    # Logging and monitoring
    logging_config: Dict[str, Any] = field(default_factory=lambda: {
        "level": "INFO",
        "file": "enhancement.log",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "enable_metrics": True,
        "enable_audit": True
    })
    
    @classmethod
    def from_mode(cls, mode: OperationMode) -> 'EnhancementSettings':
        """Create settings based on operation mode."""
        if mode == OperationMode.BASIC:
            return cls._create_basic_settings()
        elif mode == OperationMode.ADVANCED:
            return cls._create_advanced_settings()
        elif mode == OperationMode.STANDARD:
            return cls()  # Use defaults
        else:
            return cls(operation_mode=OperationMode.CUSTOM)
    
    @classmethod
    def _create_basic_settings(cls) -> 'EnhancementSettings':
        """Create basic mode settings - fast, minimal enhancements."""
        settings = cls(operation_mode=OperationMode.BASIC)
        settings.pipeline.max_enhancement_passes = 2
        settings.pipeline.parallel_processing = False
        settings.pipeline.cost_optimization = True
        settings.pipeline.max_cost_per_document = 0.10
        
        # Enable only essential strategies
        settings.strategies[EnhancementType.CLARITY].enabled = True
        settings.strategies[EnhancementType.COMPLETENESS].enabled = False
        settings.strategies[EnhancementType.CONSISTENCY].enabled = False
        settings.strategies[EnhancementType.ACCURACY].enabled = False
        settings.strategies[EnhancementType.READABILITY].enabled = True
        
        return settings
    
    @classmethod
    def _create_advanced_settings(cls) -> 'EnhancementSettings':
        """Create advanced mode settings - maximum quality."""
        settings = cls(operation_mode=OperationMode.ADVANCED)
        settings.pipeline.max_enhancement_passes = 10
        settings.pipeline.parallel_processing = True
        settings.pipeline.cost_optimization = False
        settings.pipeline.max_cost_per_document = 2.00
        settings.pipeline.detailed_reporting = True
        
        # Enable all strategies with high quality thresholds
        for strategy in settings.strategies.values():
            strategy.enabled = True
            strategy.max_iterations = 5
            strategy.quality_threshold = 0.9
        
        # Use multi-provider synthesis
        settings.llm_settings["multi_provider_synthesis"] = True
        settings.llm_settings["temperature"] = 0.5  # More focused outputs
        
        return settings
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return {
            "operation_mode": self.operation_mode.value,
            "strategies": {
                k.value: {
                    "enabled": v.enabled,
                    "priority": v.priority,
                    "max_iterations": v.max_iterations,
                    "quality_threshold": v.quality_threshold
                }
                for k, v in self.strategies.items()
            },
            "pipeline": {
                "max_enhancement_passes": self.pipeline.max_enhancement_passes,
                "parallel_processing": self.pipeline.parallel_processing,
                "batch_size": self.pipeline.batch_size,
                "timeout_seconds": self.pipeline.timeout_seconds,
                "cost_optimization": self.pipeline.cost_optimization
            },
            "llm_settings": self.llm_settings,
            "logging_config": self.logging_config
        }
    
    def save(self, path: Path) -> None:
        """Save settings to JSON file."""
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, path: Path) -> 'EnhancementSettings':
        """Load settings from JSON file."""
        with open(path, 'r') as f:
            data = json.load(f)
        
        settings = cls()
        # Parse and apply loaded settings
        if "operation_mode" in data:
            settings.operation_mode = OperationMode(data["operation_mode"])
        
        # Update strategies
        if "strategies" in data:
            for strategy_name, config in data["strategies"].items():
                strategy_type = EnhancementType(strategy_name)
                if strategy_type in settings.strategies:
                    strategy = settings.strategies[strategy_type]
                    strategy.enabled = config.get("enabled", True)
                    strategy.priority = config.get("priority", 1)
                    strategy.max_iterations = config.get("max_iterations", 3)
                    strategy.quality_threshold = config.get("quality_threshold", 0.8)
        
        # Update pipeline config
        if "pipeline" in data:
            for key, value in data["pipeline"].items():
                if hasattr(settings.pipeline, key):
                    setattr(settings.pipeline, key, value)
        
        # Update LLM settings
        if "llm_settings" in data:
            settings.llm_settings.update(data["llm_settings"])
        
        # Update logging config
        if "logging_config" in data:
            settings.logging_config.update(data["logging_config"])
        
        return settings