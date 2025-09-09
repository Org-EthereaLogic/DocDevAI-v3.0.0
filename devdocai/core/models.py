"""
Configuration Models - DevDocAI v3.0.0
Pass 4: Simplified Pydantic models with reduced complexity
"""

import logging
from typing import Literal, Optional, Union

import psutil
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

# Type definitions
MemoryMode = Literal["baseline", "standard", "enhanced", "performance"]
LLMProvider = Literal["openai", "anthropic", "gemini", "local"]


class PrivacyConfig(BaseModel):
    """Privacy configuration with opt-in defaults."""

    model_config = ConfigDict(validate_assignment=True)

    telemetry: bool = Field(default=False)
    analytics: bool = Field(default=False)
    local_only: bool = Field(default=True)


class SystemConfig(BaseModel):
    """System configuration with memory detection."""

    memory_mode: Union[MemoryMode, Literal["auto"]] = Field(default="auto")
    detected_ram: Optional[float] = None
    max_workers: int = Field(default=4)
    cache_size: str = Field(default="100MB")
    cache_size_bytes: Optional[int] = None

    def model_post_init(self, __context):
        """Set computed fields and auto-detect memory mode."""
        # Set detected RAM
        ram_gb = psutil.virtual_memory().total / (1024**3)
        object.__setattr__(self, "detected_ram", ram_gb)

        # Auto-detect memory mode if set to "auto"
        if self.memory_mode == "auto":
            if ram_gb < 2:
                detected_mode = "baseline"
            elif ram_gb < 4:
                detected_mode = "standard"
            elif ram_gb < 8:
                detected_mode = "enhanced"
            else:
                detected_mode = "performance"
            object.__setattr__(self, "memory_mode", detected_mode)

        # Adjust workers based on mode
        if self.max_workers == 4:  # Default only
            worker_map = {"baseline": 1, "standard": 2, "enhanced": 4, "performance": 8}
            if self.memory_mode in worker_map:
                object.__setattr__(self, "max_workers", worker_map[self.memory_mode])

        # Calculate cache bytes
        size_str = self.cache_size.upper()
        multipliers = {"KB": 1024, "MB": 1024**2, "GB": 1024**3}
        for suffix, mult in multipliers.items():
            if size_str.endswith(suffix):
                try:
                    bytes_val = int(size_str[: -len(suffix)]) * mult
                    object.__setattr__(self, "cache_size_bytes", bytes_val)
                    return
                except:
                    pass
        object.__setattr__(self, "cache_size_bytes", 100 * 1024 * 1024)


class SecurityConfig(BaseModel):
    """Security configuration."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    encryption_enabled: bool = Field(default=True)
    api_keys_encrypted: bool = Field(default=True)
    key_derivation: str = Field(default="argon2id")
    encryption_algorithm: str = Field(default="AES-256-GCM")


class LLMConfig(BaseModel):
    """LLM provider configuration."""

    provider: LLMProvider = Field(default="openai")
    api_key: Optional[str] = None
    model: str = Field(default="gpt-4")
    max_tokens: int = Field(default=4000)
    temperature: float = Field(default=0.7, ge=0, le=2)
    timeout: int = Field(default=30)
    retry_attempts: int = Field(default=3)


class QualityConfig(BaseModel):
    """Quality configuration."""

    min_score: int = Field(default=85, ge=0, le=100)
    auto_enhance: bool = Field(default=True)
    max_iterations: int = Field(default=3, ge=1, le=10)
    enable_miair: bool = Field(default=True)
