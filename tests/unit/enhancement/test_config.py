"""
Tests for enhancement configuration system.
"""

import pytest
import json
from pathlib import Path
import tempfile

from devdocai.enhancement.config import (
    OperationMode,
    EnhancementType,
    StrategyConfig,
    PipelineConfig,
    EnhancementSettings
)


class TestOperationMode:
    """Test OperationMode enum."""
    
    def test_operation_modes(self):
        """Test all operation modes are defined."""
        assert OperationMode.BASIC.value == "basic"
        assert OperationMode.STANDARD.value == "standard"
        assert OperationMode.ADVANCED.value == "advanced"
        assert OperationMode.CUSTOM.value == "custom"


class TestEnhancementType:
    """Test EnhancementType enum."""
    
    def test_enhancement_types(self):
        """Test all enhancement types are defined."""
        assert EnhancementType.CLARITY.value == "clarity"
        assert EnhancementType.COMPLETENESS.value == "completeness"
        assert EnhancementType.CONSISTENCY.value == "consistency"
        assert EnhancementType.ACCURACY.value == "accuracy"
        assert EnhancementType.READABILITY.value == "readability"
        assert EnhancementType.ALL.value == "all"


class TestStrategyConfig:
    """Test StrategyConfig dataclass."""
    
    def test_default_initialization(self):
        """Test default strategy configuration."""
        config = StrategyConfig()
        
        assert config.enabled is True
        assert config.priority == 1
        assert config.max_iterations == 3
        assert config.quality_threshold == 0.8
        assert config.llm_provider is None
        assert isinstance(config.custom_parameters, dict)
        
    def test_custom_initialization(self):
        """Test custom strategy configuration."""
        config = StrategyConfig(
            enabled=False,
            priority=5,
            max_iterations=10,
            quality_threshold=0.95,
            llm_provider="openai"
        )
        
        assert config.enabled is False
        assert config.priority == 5
        assert config.max_iterations == 10
        assert config.quality_threshold == 0.95
        assert config.llm_provider == "openai"
    
    def test_strategy_specific_settings(self):
        """Test strategy-specific settings."""
        config = StrategyConfig()
        
        # Clarity settings
        assert config.clarity_settings["simplify_sentences"] is True
        assert config.clarity_settings["max_sentence_length"] == 25
        
        # Completeness settings
        assert config.completeness_settings["fill_gaps"] is True
        assert config.completeness_settings["min_section_length"] == 100
        
        # Consistency settings
        assert config.consistency_settings["standardize_terminology"] is True
        
        # Accuracy settings
        assert config.accuracy_settings["fact_checking"] is True
        
        # Readability settings
        assert config.readability_settings["target_grade_level"] == 10


class TestPipelineConfig:
    """Test PipelineConfig dataclass."""
    
    def test_default_initialization(self):
        """Test default pipeline configuration."""
        config = PipelineConfig()
        
        assert config.max_enhancement_passes == 5
        assert config.parallel_processing is True
        assert config.batch_size == 10
        assert config.timeout_seconds == 300
        assert config.min_improvement_threshold == 0.05
        assert config.quality_check_interval == 1
        assert config.rollback_on_degradation is True
        
    def test_cost_settings(self):
        """Test cost management settings."""
        config = PipelineConfig()
        
        assert config.max_cost_per_document == 0.50
        assert config.cost_optimization is True
        assert config.use_cache is True
        assert config.cache_ttl_seconds == 3600
        
    def test_integration_settings(self):
        """Test integration settings."""
        config = PipelineConfig()
        
        assert config.use_miair_optimization is True
        assert config.use_quality_engine is True
        assert config.use_review_feedback is True
        
    def test_resource_limits(self):
        """Test resource limit settings."""
        config = PipelineConfig()
        
        assert config.max_memory_mb == 512
        assert config.max_concurrent_enhancements == 5
        assert config.rate_limit_per_minute == 60


class TestEnhancementSettings:
    """Test EnhancementSettings dataclass."""
    
    def test_default_initialization(self):
        """Test default enhancement settings."""
        settings = EnhancementSettings()
        
        assert settings.operation_mode == OperationMode.STANDARD
        assert len(settings.strategies) == 5
        assert isinstance(settings.pipeline, PipelineConfig)
        
    def test_from_mode_basic(self):
        """Test creating settings from basic mode."""
        settings = EnhancementSettings.from_mode(OperationMode.BASIC)
        
        assert settings.operation_mode == OperationMode.BASIC
        assert settings.pipeline.max_enhancement_passes == 2
        assert settings.pipeline.parallel_processing is False
        assert settings.pipeline.max_cost_per_document == 0.10
        
        # Check enabled strategies
        assert settings.strategies[EnhancementType.CLARITY].enabled is True
        assert settings.strategies[EnhancementType.COMPLETENESS].enabled is False
        assert settings.strategies[EnhancementType.READABILITY].enabled is True
        
    def test_from_mode_advanced(self):
        """Test creating settings from advanced mode."""
        settings = EnhancementSettings.from_mode(OperationMode.ADVANCED)
        
        assert settings.operation_mode == OperationMode.ADVANCED
        assert settings.pipeline.max_enhancement_passes == 10
        assert settings.pipeline.parallel_processing is True
        assert settings.pipeline.max_cost_per_document == 2.00
        
        # Check all strategies enabled
        for strategy in settings.strategies.values():
            assert strategy.enabled is True
            assert strategy.max_iterations == 5
            assert strategy.quality_threshold == 0.9
            
    def test_from_mode_standard(self):
        """Test creating settings from standard mode."""
        settings = EnhancementSettings.from_mode(OperationMode.STANDARD)
        
        assert settings.operation_mode == OperationMode.STANDARD
        # Should use defaults
        assert settings.pipeline.max_enhancement_passes == 5
        
    def test_from_mode_custom(self):
        """Test creating settings from custom mode."""
        settings = EnhancementSettings.from_mode(OperationMode.CUSTOM)
        
        assert settings.operation_mode == OperationMode.CUSTOM
        
    def test_to_dict(self):
        """Test converting settings to dictionary."""
        settings = EnhancementSettings()
        data = settings.to_dict()
        
        assert data["operation_mode"] == "standard"
        assert "strategies" in data
        assert "pipeline" in data
        assert "llm_settings" in data
        assert "logging_config" in data
        
        # Check strategy data
        for strategy_name, strategy_data in data["strategies"].items():
            assert "enabled" in strategy_data
            assert "priority" in strategy_data
            assert "max_iterations" in strategy_data
            assert "quality_threshold" in strategy_data
            
    def test_save_and_load(self):
        """Test saving and loading settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            
            # Create and save settings
            original_settings = EnhancementSettings.from_mode(OperationMode.ADVANCED)
            original_settings.save(settings_path)
            
            assert settings_path.exists()
            
            # Load settings
            loaded_settings = EnhancementSettings.load(settings_path)
            
            assert loaded_settings.operation_mode == OperationMode.ADVANCED
            assert loaded_settings.pipeline.max_enhancement_passes == 10
            
    def test_strategy_priorities(self):
        """Test strategy priority configuration."""
        settings = EnhancementSettings()
        
        # Default priorities
        assert settings.strategies[EnhancementType.CLARITY].priority == 1
        assert settings.strategies[EnhancementType.COMPLETENESS].priority == 2
        assert settings.strategies[EnhancementType.CONSISTENCY].priority == 3
        assert settings.strategies[EnhancementType.ACCURACY].priority == 4
        assert settings.strategies[EnhancementType.READABILITY].priority == 5
        
    def test_llm_settings(self):
        """Test LLM configuration settings."""
        settings = EnhancementSettings()
        
        assert settings.llm_settings["primary_provider"] == "openai"
        assert "anthropic" in settings.llm_settings["fallback_providers"]
        assert settings.llm_settings["temperature"] == 0.7
        assert settings.llm_settings["max_tokens"] == 2000
        assert settings.llm_settings["streaming"] is True
        assert settings.llm_settings["multi_provider_synthesis"] is True
        
    def test_logging_config(self):
        """Test logging configuration."""
        settings = EnhancementSettings()
        
        assert settings.logging_config["level"] == "INFO"
        assert settings.logging_config["file"] == "enhancement.log"
        assert settings.logging_config["enable_metrics"] is True
        assert settings.logging_config["enable_audit"] is True