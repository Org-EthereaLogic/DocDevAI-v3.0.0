"""
DevDocAI Core Components

Foundation layer modules that provide essential functionality.
"""

from typing import TYPE_CHECKING

# Lazy imports to avoid circular dependencies
if TYPE_CHECKING:
    from .config import ConfigurationManager

__all__ = ["ConfigurationManager"]