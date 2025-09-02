"""
DevDocAI CLI Module - Command-line interface for documentation generation and analysis.

This module provides a comprehensive CLI for all DevDocAI operations including:
- Document generation with templates
- Quality analysis and scoring
- Configuration management
- Template operations
- Enhancement pipelines
- Security scanning
"""

__version__ = "3.0.0"
__author__ = "DevDocAI Team"

from .main import cli, main

__all__ = ["cli", "main"]