"""
M003 MIAIR Engine - Entropy Calculator

Implements Shannon entropy calculation based on character probabilities.

Mathematical Formula: S = -Σ[p(xi) × log2(p(xi))]

Where:
- p(xi) = probability of character i

Key Features:
- Accurate Shannon entropy calculation for text content.
- Edge case handling (empty documents).
- Performance optimized for real-time use.
"""

import math
from collections import Counter
import logging
from typing import Dict, Any

from .models import Document

logger = logging.getLogger(__name__)

class EntropyCalculator:
    """
    Implements Shannon entropy calculation based on character probabilities.
    """
    
    def __init__(self):
        """Initialize entropy calculator with configuration."""
        self.min_probability = 1e-10  # Avoid log(0) errors
        self.max_content_length = 1_000_000  # 1MB safety limit
        logger.debug("EntropyCalculator initialized")

    def calculate_entropy(
        self,
        document: Document,
        iteration: int = 0
    ) -> float:
        """
        Calculate Shannon entropy for the document's content.
        
        Args:
            document: Document to analyze.
            iteration: Current iteration for fractal scaling (retained for API compatibility).
            
        Returns:
            Entropy score.
            
        Raises:
            ValueError: If document content is invalid.
        """
        logger.debug(f"Calculating entropy for document {document.id}")
        
        content = document.content
        if not content or not content.strip():
            logger.warning(f"Empty document content for {document.id}")
            return 0.0  # Entropy of an empty string is 0

        if len(content) > self.max_content_length:
            raise ValueError(f"Document content too large: {len(content)} bytes")
        
        prob_dist = self.calculate_probability_distribution(content)
        
        if not prob_dist:
            return 0.0

        entropy = self._calculate_shannon_entropy(prob_dist)
        
        # Retaining fractal_time_scaling for API compatibility, though it might be less relevant now.
        scaled_entropy = self.fractal_time_scaling(entropy, iteration)
        
        logger.debug(
            f"Document {document.id}: raw_entropy={entropy:.4f}, "
            f"scaled_entropy={scaled_entropy:.4f}"
        )
        
        return scaled_entropy

    def calculate_probability_distribution(
        self,
        content: str
    ) -> Dict[str, float]:
        """
        Calculate probability distribution of characters in the content.
        
        Args:
            content: The text content.
            
        Returns:
            Dictionary mapping characters to their probabilities.
        """
        if not content:
            return {}
        
        char_counts = Counter(content)
        total_chars = len(content)
        
        prob_dist = {char: count / total_chars for char, count in char_counts.items()}
        
        return prob_dist

    def fractal_time_scaling(
        self,
        entropy: float,
        iteration: int
    ) -> float:
        """
        Apply fractal-time scaling factor f(Tx).
        
        Reduces entropy impact as iterations increase, modeling
        diminishing returns in optimization.
        
        Formula: f(Tx) = 1 / (1 + log(1 + iteration))
        
        Args:
            entropy: Base entropy value
            iteration: Current iteration number (>= 0)
            
        Returns:
            Scaled entropy value
        """
        if iteration < 0:
            iteration = 0
        
        scaling_factor = 1.0 / (1.0 + math.log(1.0 + iteration))
        
        scaled_entropy = entropy * scaling_factor
        
        logger.debug(f"Fractal scaling: iteration={iteration}, factor={scaling_factor:.4f}")
        return scaled_entropy

    def _calculate_shannon_entropy(self, prob_dist: Dict[str, float]) -> float:
        """
        Calculate Shannon entropy from a probability distribution.
        
        Formula: H = -Σ[p(xi) × log2(p(xi))]
        
        Args:
            prob_dist: Probability distribution of characters.
            
        Returns:
            The Shannon entropy value.
        """
        if not prob_dist:
            return 0.0
        
        entropy = 0.0
        for probability in prob_dist.values():
            if probability > self.min_probability:
                entropy -= probability * math.log2(probability)
        
        return entropy

    def get_entropy_analysis(self, document: Document) -> Dict[str, Any]:
        """
        Get detailed entropy analysis for debugging and optimization.
        
        Args:
            document: Document to analyze
            
        Returns:
            Dictionary with detailed entropy analysis
        """
        content = document.content
        prob_dist = self.calculate_probability_distribution(content)
        entropy = self.calculate_entropy(document)
        
        return {
            'entropy': entropy,
            'probability_distribution': prob_dist,
            'content_length': len(content),
            'unique_characters': len(prob_dist),
        }
