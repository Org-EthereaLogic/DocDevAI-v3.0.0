"""
DevDocAI - AI-powered documentation generation and analysis system.

Privacy-first, offline-capable documentation tools for solo developers.
"""

__version__ = "3.0.0"
__author__ = "DevDocAI Team"

# Re-export core components for easier imports
from devdocai.core.config import ConfigurationManager

__all__ = ["ConfigurationManager"]