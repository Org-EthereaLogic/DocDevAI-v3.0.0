"""
M003 MIAIR Engine - Unified Configuration Model

Extended configuration for the unified MIAIR Engine with mode-specific settings.
"""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from .models import MIAIRConfig


class UnifiedMIAIRConfig(MIAIRConfig):
    """
    Extended configuration for unified MIAIR Engine.
    Inherits from base MIAIRConfig and adds mode-specific settings.
    """
    
    model_config = ConfigDict(
        validate_assignment=True,
        extra='allow'  # Allow additional fields for flexibility
    )
    
    # Caching configuration
    enable_caching: bool = Field(
        default=True,
        description="Enable caching for performance"
    )
    
    cache_ttl: int = Field(
        default=3600,
        ge=0,
        description="Cache time-to-live in seconds"
    )
    
    # Parallel processing configuration
    enable_parallel: bool = Field(
        default=False,
        description="Enable parallel processing"
    )
    
    thread_pool_size: int = Field(
        default=4,
        ge=1,
        le=32,
        description="Thread pool size for I/O operations"
    )
    
    process_pool_size: int = Field(
        default=2,
        ge=1,
        le=16,
        description="Process pool size for CPU operations"
    )
    
    batch_size: int = Field(
        default=50,
        ge=1,
        le=1000,
        description="Batch processing size"
    )
    
    chunk_size: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="Content chunk size for parallel processing"
    )
    
    # Security configuration
    enable_validation: bool = Field(
        default=False,
        description="Enable input validation"
    )
    
    enable_audit: bool = Field(
        default=False,
        description="Enable audit logging"
    )
    
    enable_pii_detection: bool = Field(
        default=False,
        description="Enable PII detection and masking"
    )
    
    rate_limit_rpm: int = Field(
        default=1000,
        ge=1,
        le=100000,
        description="Rate limit requests per minute"
    )
    
    rate_limit_burst: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Rate limit burst size"
    )
    
    # Performance metrics
    enable_metrics: bool = Field(
        default=True,
        description="Enable performance metrics collection"
    )
    
    @classmethod
    def for_basic_mode(cls) -> 'UnifiedMIAIRConfig':
        """Create configuration for BASIC mode."""
        return cls(
            enable_caching=False,
            enable_parallel=False,
            thread_pool_size=1,
            process_pool_size=1,
            enable_validation=False,
            enable_audit=False,
            enable_pii_detection=False
        )
    
    @classmethod
    def for_performance_mode(cls) -> 'UnifiedMIAIRConfig':
        """Create configuration for PERFORMANCE mode."""
        return cls(
            enable_caching=True,
            cache_size=1000,
            enable_parallel=True,
            thread_pool_size=8,
            process_pool_size=4,
            batch_size=100,
            enable_validation=False,
            enable_audit=False,
            enable_pii_detection=False
        )
    
    @classmethod
    def for_secure_mode(cls) -> 'UnifiedMIAIRConfig':
        """Create configuration for SECURE mode."""
        return cls(
            enable_caching=True,
            cache_size=1000,
            enable_parallel=False,
            enable_validation=True,
            enable_audit=True,
            enable_pii_detection=True,
            rate_limit_rpm=1000
        )
    
    @classmethod
    def for_enterprise_mode(cls) -> 'UnifiedMIAIRConfig':
        """Create configuration for ENTERPRISE mode."""
        return cls(
            enable_caching=True,
            cache_size=1000,
            enable_parallel=True,
            thread_pool_size=16,
            process_pool_size=8,
            batch_size=200,
            enable_validation=True,
            enable_audit=True,
            enable_pii_detection=True,
            rate_limit_rpm=10000
        )