"""
DevDocAI Core Module
Configuration management and foundational components.
"""

from .config import ConfigurationManager, ValidationError, ConfigurationError
from .models import PrivacyConfig, SystemConfig, SecurityConfig, LLMConfig, QualityConfig

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
