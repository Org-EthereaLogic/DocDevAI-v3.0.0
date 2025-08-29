"""
M003 MIAIR Engine - Mathematical Intelligence and AI-Integrated Refinement.

This module provides mathematical optimization for quality improvement using
Shannon entropy and multi-dimensional quality scoring.

Core Components:
- ShannonEntropyCalculator: Measures information content in text
- QualityScorer: Multi-dimensional quality assessment
- MIAIROptimizer: Iterative document refinement engine
- PatternRecognizer: Identifies improvement patterns
- MIAIREngine: Main orchestration class

Author: DevDocAI Team
Version: 3.0.0
"""

from .entropy import ShannonEntropyCalculator
from .scorer import QualityScorer
from .optimizer import MIAIROptimizer
from .patterns import PatternRecognizer
from .engine import MIAIREngine

__all__ = [
    'ShannonEntropyCalculator',
    'QualityScorer',
    'MIAIROptimizer',
    'PatternRecognizer',
    'MIAIREngine'
]

__version__ = '3.0.0'