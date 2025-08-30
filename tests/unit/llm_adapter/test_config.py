"""
Tests for M008 LLM Adapter configuration models.

Tests configuration validation, cost limits, provider configs,
and usage record functionality.
"""

import pytest
from decimal import Decimal
from datetime import datetime

from devdocai.llm_adapter.config import (
    ProviderType, FallbackStrategy, CostLimits, ProviderConfig,
    SynthesisConfig, LLMConfig, UsageRecord
)


class TestCostLimits:
    """Test cost limits configuration."""
    
    def test_default_cost_limits(self):
        """Test default cost limit values."""
        limits = CostLimits()
        
        assert limits.daily_limit_usd == Decimal("10.00")
        assert limits.monthly_limit_usd == Decimal("200.00")
        assert limits.per_request_limit_usd == Decimal("5.00")
        assert limits.daily_warning_threshold == 0.8
        assert limits.monthly_warning_threshold == 0.9
        assert limits.emergency_stop_enabled is True
        assert limits.emergency_threshold == 0.95
    
    def test_cost_limits_validation(self):
        """Test cost limits validation."""
        # Valid configuration
        limits = CostLimits(
            daily_limit_usd=Decimal("5.00"),
            monthly_limit_usd=Decimal("100.00"),
            per_request_limit_usd=Decimal("2.00")
        )
        assert limits.daily_limit_usd == Decimal("5.00")
        
        # Invalid per-request limit (exceeds daily)
        with pytest.raises(ValueError, match="Per-request limit cannot exceed daily limit"):
            CostLimits(
                daily_limit_usd=Decimal("5.00"),
                per_request_limit_usd=Decimal("10.00")
            )
    
    def test_cost_limits_negative_values(self):
        """Test that negative values are rejected."""
        with pytest.raises(ValueError):
            CostLimits(daily_limit_usd=Decimal("-1.00"))
        
        with pytest.raises(ValueError):
            CostLimits(monthly_limit_usd=Decimal("-10.00"))


class TestProviderConfig:
    """Test provider configuration."""
    
    def test_openai_provider_config(self):
        """Test OpenAI provider configuration."""
        config = ProviderConfig(
            provider_type=ProviderType.OPENAI,
            api_key="test-key"
        )
        
        assert config.provider_type == ProviderType.OPENAI
        assert config.enabled is True
        assert config.default_model == "gpt-3.5-turbo"
        assert "gpt-4" in config.available_models
        assert config.base_url == "https://api.openai.com/v1"
    
    def test_anthropic_provider_config(self):
        """Test Anthropic provider configuration."""
        config = ProviderConfig(
            provider_type=ProviderType.ANTHROPIC,
            api_key="test-key"
        )
        
        assert config.provider_type == ProviderType.ANTHROPIC
        assert config.default_model == "claude-3-sonnet-20240229"
        assert "claude-3-opus-20240229" in config.available_models
        assert config.base_url == "https://api.anthropic.com/v1"
    
    def test_google_provider_config(self):
        """Test Google provider configuration."""
        config = ProviderConfig(
            provider_type=ProviderType.GOOGLE,
            api_key="test-key"
        )
        
        assert config.provider_type == ProviderType.GOOGLE
        assert config.default_model == "gemini-pro"
        assert "gemini-pro-vision" in config.available_models
    
    def test_local_provider_config(self):
        """Test local provider configuration."""
        config = ProviderConfig(
            provider_type=ProviderType.LOCAL
        )
        
        assert config.provider_type == ProviderType.LOCAL
        assert config.base_url == "http://localhost:11434"
        assert "llama2" in config.available_models
    
    def test_api_key_validation(self):
        """Test API key validation."""
        # Valid API key
        config = ProviderConfig(
            provider_type=ProviderType.OPENAI,
            api_key="sk-1234567890abcdef"
        )
        assert config.api_key == "sk-1234567890abcdef"
        
        # Invalid API key (too short)
        with pytest.raises(ValueError, match="API key too short"):
            ProviderConfig(
                provider_type=ProviderType.OPENAI,
                api_key="short"
            )
        
        # Invalid API key (not string)
        with pytest.raises(ValueError, match="API key must be a string"):
            ProviderConfig(
                provider_type=ProviderType.OPENAI,
                api_key=123456
            )
    
    def test_provider_cost_settings(self):
        """Test provider cost configuration."""
        config = ProviderConfig(
            provider_type=ProviderType.OPENAI,
            api_key="test-key",
            input_cost_per_1k=Decimal("0.002"),
            output_cost_per_1k=Decimal("0.004")
        )
        
        assert config.input_cost_per_1k == Decimal("0.002")
        assert config.output_cost_per_1k == Decimal("0.004")
    
    def test_provider_performance_settings(self):
        """Test provider performance configuration."""
        config = ProviderConfig(
            provider_type=ProviderType.OPENAI,
            api_key="test-key",
            timeout_seconds=60,
            max_retries=5,
            retry_delay_seconds=2.0
        )
        
        assert config.timeout_seconds == 60
        assert config.max_retries == 5
        assert config.retry_delay_seconds == 2.0


class TestSynthesisConfig:
    """Test synthesis configuration."""
    
    def test_default_synthesis_config(self):
        """Test default synthesis settings."""
        config = SynthesisConfig()
        
        assert config.enabled is True
        assert config.max_providers == 3
        assert config.quality_improvement_target == 0.2
        assert config.strategy == "consensus"
        assert config.consensus_threshold == 0.7
        assert config.min_agreement == 2
    
    def test_synthesis_validation(self):
        """Test synthesis configuration validation."""
        # Valid configuration
        config = SynthesisConfig(
            max_providers=2,
            min_agreement=2
        )
        assert config.max_providers == 2
        
        # Test different strategies
        config = SynthesisConfig(strategy="best_of_n")
        assert config.strategy == "best_of_n"
        
        config = SynthesisConfig(strategy="weighted_average") 
        assert config.strategy == "weighted_average"


class TestLLMConfig:
    """Test main LLM configuration."""
    
    def test_minimal_config(self):
        """Test minimal valid configuration."""
        providers = {
            "openai": ProviderConfig(
                provider_type=ProviderType.OPENAI,
                api_key="test-key"
            )
        }
        
        config = LLMConfig(providers=providers)
        
        assert len(config.providers) == 1
        assert config.cost_tracking_enabled is True
        assert config.fallback_enabled is True
        assert config.synthesis.enabled is True
    
    def test_provider_validation(self):
        """Test provider configuration validation."""
        # No providers
        with pytest.raises(ValueError, match="At least one provider must be configured"):
            LLMConfig(providers={})
        
        # All providers disabled
        providers = {
            "openai": ProviderConfig(
                provider_type=ProviderType.OPENAI,
                api_key="test-key",
                enabled=False
            )
        }
        
        with pytest.raises(ValueError, match="At least one provider must be enabled"):
            LLMConfig(providers=providers)
    
    def test_get_enabled_providers(self):
        """Test getting enabled providers."""
        providers = {
            "openai": ProviderConfig(
                provider_type=ProviderType.OPENAI,
                api_key="test-key",
                enabled=True
            ),
            "anthropic": ProviderConfig(
                provider_type=ProviderType.ANTHROPIC,
                api_key="test-key",
                enabled=False
            ),
            "google": ProviderConfig(
                provider_type=ProviderType.GOOGLE,
                api_key="test-key",
                enabled=True
            )
        }
        
        config = LLMConfig(providers=providers)
        enabled = config.get_enabled_providers()
        
        assert len(enabled) == 2
        assert "openai" in enabled
        assert "google" in enabled
        assert "anthropic" not in enabled
    
    def test_get_provider_by_priority(self):
        """Test getting providers ordered by priority."""
        providers = {
            "openai": ProviderConfig(
                provider_type=ProviderType.OPENAI,
                api_key="test-key",
                priority=5
            ),
            "anthropic": ProviderConfig(
                provider_type=ProviderType.ANTHROPIC,
                api_key="test-key",
                priority=8
            ),
            "google": ProviderConfig(
                provider_type=ProviderType.GOOGLE,
                api_key="test-key",
                priority=3
            )
        }
        
        config = LLMConfig(providers=providers)
        ordered = config.get_provider_by_priority()
        
        # Should be ordered by priority (highest first)
        assert ordered == ["anthropic", "openai", "google"]
    
    def test_synthesis_config_validation(self):
        """Test synthesis configuration validation."""
        # Single provider but synthesis enabled
        providers = {
            "openai": ProviderConfig(
                provider_type=ProviderType.OPENAI,
                api_key="test-key"
            )
        }
        
        config = LLMConfig(
            providers=providers,
            synthesis=SynthesisConfig(enabled=True)
        )
        
        # Should automatically disable synthesis with warning
        assert config.synthesis.enabled is False


class TestUsageRecord:
    """Test usage record functionality."""
    
    def test_usage_record_creation(self):
        """Test creating usage records."""
        record = UsageRecord(
            timestamp=datetime.utcnow(),
            provider="openai",
            model="gpt-3.5-turbo",
            input_tokens=100,
            output_tokens=50,
            input_cost=Decimal("0.0001"),
            output_cost=Decimal("0.0001"),
            total_cost=Decimal("0.0002"),
            request_id="test-123",
            response_time_seconds=1.5,
            success=True
        )
        
        assert record.provider == "openai"
        assert record.model == "gpt-3.5-turbo"
        assert record.input_tokens == 100
        assert record.output_tokens == 50
        assert record.total_cost == Decimal("0.0002")
        assert record.response_time_seconds == 1.5
        assert record.success is True
    
    def test_usage_record_validation(self):
        """Test usage record validation."""
        # Test cost mismatch warning
        record = UsageRecord(
            timestamp=datetime.utcnow(),
            provider="openai",
            model="gpt-3.5-turbo",
            input_tokens=100,
            output_tokens=50,
            input_cost=Decimal("0.0001"),
            output_cost=Decimal("0.0001"),
            total_cost=Decimal("0.0010"),  # Mismatch
            request_id="test-123",
            response_time_seconds=1.5
        )
        
        # Should create record but may log warning
        assert record.total_cost == Decimal("0.0010")
    
    def test_usage_record_negative_values(self):
        """Test that negative values are rejected."""
        with pytest.raises(ValueError):
            UsageRecord(
                timestamp=datetime.utcnow(),
                provider="openai",
                model="gpt-3.5-turbo",
                input_tokens=-1,  # Invalid
                output_tokens=50,
                input_cost=Decimal("0.0001"),
                output_cost=Decimal("0.0001"),
                total_cost=Decimal("0.0002"),
                request_id="test-123",
                response_time_seconds=1.5
            )
        
        with pytest.raises(ValueError):
            UsageRecord(
                timestamp=datetime.utcnow(),
                provider="openai",
                model="gpt-3.5-turbo",
                input_tokens=100,
                output_tokens=50,
                input_cost=Decimal("-0.0001"),  # Invalid
                output_cost=Decimal("0.0001"),
                total_cost=Decimal("0.0002"),
                request_id="test-123",
                response_time_seconds=-1.0  # Invalid
            )