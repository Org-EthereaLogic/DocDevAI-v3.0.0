"""
M008: LLM Adapter Configuration Models.

Configuration management for multi-provider LLM integration with secure
API key storage and cost management.
"""

import os
import logging
from typing import Dict, List, Optional, Any, Literal
from decimal import Decimal
from datetime import datetime, timedelta
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator
from typing_extensions import Self

logger = logging.getLogger(__name__)


class ProviderType(str, Enum):
    """Supported LLM provider types."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic" 
    GOOGLE = "google"
    LOCAL = "local"


class FallbackStrategy(str, Enum):
    """Fallback strategy options."""
    SEQUENTIAL = "sequential"  # Try providers in order
    COST_OPTIMIZED = "cost_optimized"  # Prefer cheaper providers
    QUALITY_OPTIMIZED = "quality_optimized"  # Prefer higher quality
    PARALLEL = "parallel"  # Try multiple providers simultaneously


class CostLimits(BaseModel):
    """Cost management configuration."""
    
    daily_limit_usd: Decimal = Field(default=Decimal("10.00"), ge=0)
    monthly_limit_usd: Decimal = Field(default=Decimal("200.00"), ge=0)
    per_request_limit_usd: Decimal = Field(default=Decimal("5.00"), ge=0)
    
    # Warning thresholds (percentages)
    daily_warning_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    monthly_warning_threshold: float = Field(default=0.9, ge=0.0, le=1.0)
    
    # Emergency brake settings
    emergency_stop_enabled: bool = Field(default=True)
    emergency_threshold: float = Field(default=0.95, ge=0.0, le=1.0)
    
    @model_validator(mode='after')
    def validate_limits(self) -> Self:
        """Ensure cost limits are logical."""
        if self.daily_limit_usd * 31 < self.monthly_limit_usd:
            # Monthly limit should be reasonable vs daily
            logger.warning(
                f"Monthly limit ({self.monthly_limit_usd}) may be too high "
                f"compared to daily limit ({self.daily_limit_usd})"
            )
        
        if self.per_request_limit_usd > self.daily_limit_usd:
            raise ValueError(
                "Per-request limit cannot exceed daily limit"
            )
        
        return self


class ProviderConfig(BaseModel):
    """Configuration for a single LLM provider."""
    
    provider_type: ProviderType
    enabled: bool = Field(default=True)
    
    # API configuration
    api_key: Optional[str] = Field(default=None, exclude=True)  # Will be encrypted
    api_key_encrypted: Optional[Dict[str, str]] = Field(default=None)
    base_url: Optional[str] = None
    organization: Optional[str] = None
    
    # Model settings
    default_model: Optional[str] = None
    available_models: List[str] = Field(default_factory=list)
    max_tokens: int = Field(default=4096, ge=1, le=128000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    
    # Cost settings (per 1K tokens)
    input_cost_per_1k: Decimal = Field(default=Decimal("0.003"))
    output_cost_per_1k: Decimal = Field(default=Decimal("0.006"))
    
    # Performance settings
    timeout_seconds: int = Field(default=30, ge=5, le=300)
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay_seconds: float = Field(default=1.0, ge=0.1, le=10.0)
    
    # Rate limiting
    requests_per_minute: int = Field(default=60, ge=1)
    requests_per_day: Optional[int] = None
    
    # Quality metrics
    quality_score: float = Field(default=0.8, ge=0.0, le=1.0)
    priority: int = Field(default=1, ge=1, le=10)  # Higher = more preferred
    
    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v):
        """Validate API key format if provided."""
        if v is not None:
            if len(v) < 10:
                raise ValueError("API key too short")
            if not isinstance(v, str):
                raise ValueError("API key must be a string")
        return v
    
    @model_validator(mode='after') 
    def validate_provider_config(self) -> Self:
        """Validate provider-specific configurations."""
        
        # Set provider-specific defaults
        if self.provider_type == ProviderType.OPENAI:
            if not self.default_model:
                self.default_model = "gpt-3.5-turbo"
            if not self.available_models:
                self.available_models = [
                    "gpt-3.5-turbo", "gpt-4", "gpt-4-turbo", "gpt-4o"
                ]
            if not self.base_url:
                self.base_url = "https://api.openai.com/v1"
                
        elif self.provider_type == ProviderType.ANTHROPIC:
            if not self.default_model:
                self.default_model = "claude-3-sonnet-20240229" 
            if not self.available_models:
                self.available_models = [
                    "claude-3-haiku-20240307",
                    "claude-3-sonnet-20240229",
                    "claude-3-opus-20240229"
                ]
            if not self.base_url:
                self.base_url = "https://api.anthropic.com/v1"
                
        elif self.provider_type == ProviderType.GOOGLE:
            if not self.default_model:
                self.default_model = "gemini-pro"
            if not self.available_models:
                self.available_models = ["gemini-pro", "gemini-pro-vision"]
                
        elif self.provider_type == ProviderType.LOCAL:
            if not self.base_url:
                self.base_url = "http://localhost:11434"  # Ollama default
                
        return self


class SynthesisConfig(BaseModel):
    """Configuration for multi-LLM synthesis."""
    
    enabled: bool = Field(default=True)
    max_providers: int = Field(default=3, ge=1, le=5)
    quality_improvement_target: float = Field(default=0.2, ge=0.0, le=1.0)
    
    # Synthesis strategies
    strategy: Literal["consensus", "best_of_n", "weighted_average"] = "consensus"
    
    # Consensus parameters
    consensus_threshold: float = Field(default=0.7, ge=0.5, le=1.0)
    min_agreement: int = Field(default=2, ge=2)
    
    # Cost controls
    max_cost_multiplier: float = Field(default=2.5, ge=1.0, le=10.0)
    cost_vs_quality_weight: float = Field(default=0.3, ge=0.0, le=1.0)


class LLMConfig(BaseModel):
    """Main configuration for LLM Adapter."""
    
    # Provider configurations
    providers: Dict[str, ProviderConfig] = Field(default_factory=dict)
    
    # Cost management
    cost_limits: CostLimits = Field(default_factory=CostLimits)
    cost_tracking_enabled: bool = Field(default=True)
    
    # Fallback configuration
    fallback_strategy: FallbackStrategy = Field(default=FallbackStrategy.SEQUENTIAL)
    fallback_enabled: bool = Field(default=True)
    
    # Multi-LLM synthesis
    synthesis: SynthesisConfig = Field(default_factory=SynthesisConfig)
    
    # Performance settings
    default_timeout: int = Field(default=30, ge=5, le=300)
    max_concurrent_requests: int = Field(default=10, ge=1, le=100)
    cache_enabled: bool = Field(default=True)
    cache_ttl_seconds: int = Field(default=3600, ge=0)  # 1 hour
    
    # Security settings
    encryption_enabled: bool = Field(default=True)
    input_validation_enabled: bool = Field(default=True)
    sanitize_outputs: bool = Field(default=True)
    
    # Integration settings  
    miair_integration_enabled: bool = Field(default=True)
    quality_analysis_enabled: bool = Field(default=True)
    
    # Logging and monitoring
    audit_enabled: bool = Field(default=True)
    performance_monitoring_enabled: bool = Field(default=True)
    cost_alerts_enabled: bool = Field(default=True)
    
    @field_validator('providers')
    @classmethod
    def validate_providers(cls, v):
        """Ensure at least one provider is configured."""
        if not v:
            raise ValueError("At least one provider must be configured")
        
        enabled_providers = [p for p in v.values() if p.enabled]
        if not enabled_providers:
            raise ValueError("At least one provider must be enabled")
            
        return v
    
    @model_validator(mode='after')
    def validate_config(self) -> Self:
        """Validate overall configuration consistency."""
        
        # Ensure synthesis config makes sense
        if self.synthesis.enabled:
            enabled_providers = [p for p in self.providers.values() if p.enabled]
            if len(enabled_providers) < 2:
                logger.warning(
                    "Multi-LLM synthesis enabled but less than 2 providers available"
                )
                self.synthesis.enabled = False
        
        return self
    
    def get_enabled_providers(self) -> List[str]:
        """Get list of enabled provider names."""
        return [
            name for name, config in self.providers.items() 
            if config.enabled
        ]
    
    def get_provider_by_priority(self) -> List[str]:
        """Get providers ordered by priority (highest first)."""
        enabled = [
            (name, config) for name, config in self.providers.items()
            if config.enabled
        ]
        enabled.sort(key=lambda x: x[1].priority, reverse=True)
        return [name for name, _ in enabled]


class UsageRecord(BaseModel):
    """Record of LLM usage for cost tracking."""
    
    timestamp: datetime
    provider: str
    model: str
    
    # Token counts
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    
    # Costs (in USD)
    input_cost: Decimal = Field(ge=0)
    output_cost: Decimal = Field(ge=0)
    total_cost: Decimal = Field(ge=0)
    
    # Request metadata
    request_id: str
    user_id: Optional[str] = None
    request_type: Optional[str] = None  # e.g., "generation", "synthesis"
    
    # Performance metrics
    response_time_seconds: float = Field(ge=0)
    success: bool = Field(default=True)
    error_message: Optional[str] = None
    
    @model_validator(mode='after')
    def validate_usage(self) -> Self:
        """Validate usage record consistency."""
        # Ensure total cost matches input + output
        expected_total = self.input_cost + self.output_cost
        if abs(self.total_cost - expected_total) > Decimal("0.001"):
            logger.warning(
                f"Total cost mismatch: {self.total_cost} vs {expected_total}"
            )
        
        return self