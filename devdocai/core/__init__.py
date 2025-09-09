"""
DevDocAI Core Module
Configuration management and foundational components.
"""

from .config import ConfigurationError, ConfigurationManager, ValidationError
from .models import LLMConfig, PrivacyConfig, QualityConfig, SecurityConfig, SystemConfig

__all__ = [
    "ConfigurationManager",
    "PrivacyConfig",
    "SystemConfig",
    "SecurityConfig",
    "LLMConfig",
    "QualityConfig",
    "ValidationError",
    "ConfigurationError",
]

__version__ = "3.0.0"
