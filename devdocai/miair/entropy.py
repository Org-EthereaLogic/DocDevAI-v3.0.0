"""
Shannon entropy calculator for text analysis.

Implements multi-level entropy calculations for measuring information content
in documentation. Uses Shannon's formula: H = -Σ p(x) log₂ p(x)
"""

import math
import re
import string
from collections import Counter
from typing import Dict, List, Tuple, Optional
import numpy as np
from functools import lru_cache


class ShannonEntropyCalculator:
    """
    Calculates Shannon entropy at different text granularities.
    
    Entropy measures the average information content in a message.
    Higher entropy indicates more information/randomness.
    Lower entropy indicates more predictability/redundancy.
    """
    
    def __init__(self, cache_size: int = 128):
        """
        Initialize entropy calculator with caching.
        
        Args:
            cache_size: Size of LRU cache for performance optimization
        """
        self.cache_size = cache_size
        self._setup_caches()
    
    def _setup_caches(self):
        """Setup LRU caches for expensive calculations."""
        # Cache entropy calculations for repeated text segments
        self.calculate_character_entropy = lru_cache(maxsize=self.cache_size)(
            self._calculate_character_entropy_impl
        )
        self.calculate_word_entropy = lru_cache(maxsize=self.cache_size)(
            self._calculate_word_entropy_impl
        )
    
    def calculate_entropy(self, text: str, level: str = 'all') -> Dict[str, float]:
        """
        Calculate entropy at specified level(s).
        
        Args:
            text: Input text to analyze
            level: 'character', 'word', 'sentence', or 'all'
            
        Returns:
            Dictionary with entropy values for each level
        """
        if not text:
            return {'character': 0.0, 'word': 0.0, 'sentence': 0.0}
        
        results = {}
        
        if level in ['character', 'all']:
            results['character'] = self.calculate_character_entropy(text)
        
        if level in ['word', 'all']:
            results['word'] = self.calculate_word_entropy(text)
        
        if level in ['sentence', 'all']:
            results['sentence'] = self.calculate_sentence_entropy(text)
        
        if level == 'all':
            # Calculate aggregate entropy score
            results['aggregate'] = self._calculate_aggregate_entropy(results)
        
        return results
    
    def _calculate_character_entropy_impl(self, text: str) -> float:
        """
        Calculate character-level entropy.
        
        Measures randomness in character distribution.
        English text typically has 4-5 bits of entropy.
        """
        if not text:
            return 0.0
        
        # Count character frequencies
        char_counts = Counter(text)
        total_chars = len(text)
        
        # Calculate probabilities and entropy
        entropy = 0.0
        for count in char_counts.values():
            probability = count / total_chars
            if probability > 0:
                entropy -= probability * math.log2(probability)
        
        return entropy
    
    def _calculate_word_entropy_impl(self, text: str) -> float:
        """
        Calculate word-level entropy.
        
        Measures vocabulary diversity and word distribution.
        Higher values indicate richer vocabulary.
        """
        if not text:
            return 0.0
        
        # Tokenize into words (simple tokenization)
        words = re.findall(r'\b\w+\b', text.lower())
        if not words:
            return 0.0
        
        # Count word frequencies
        word_counts = Counter(words)
        total_words = len(words)
        
        # Calculate entropy
        entropy = 0.0
        for count in word_counts.values():
            probability = count / total_words
            if probability > 0:
                entropy -= probability * math.log2(probability)
        
        return entropy
    
    def calculate_sentence_entropy(self, text: str) -> float:
        """
        Calculate sentence-level entropy.
        
        Measures structural complexity and sentence diversity.
        """
        if not text:
            return 0.0
        
        # Split into sentences (simple approach)
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return 0.0
        
        # Analyze sentence lengths and structures
        lengths = [len(s.split()) for s in sentences]
        if not lengths:
            return 0.0
        
        # Calculate entropy based on sentence length distribution
        length_counts = Counter(lengths)
        total_sentences = len(sentences)
        
        entropy = 0.0
        for count in length_counts.values():
            probability = count / total_sentences
            if probability > 0:
                entropy -= probability * math.log2(probability)
        
        return entropy
    
    def _calculate_aggregate_entropy(self, entropies: Dict[str, float]) -> float:
        """
        Calculate weighted aggregate entropy score.
        
        Combines different entropy levels with weights.
        """
        weights = {
            'character': 0.2,
            'word': 0.5,
            'sentence': 0.3
        }
        
        aggregate = 0.0
        for level, weight in weights.items():
            if level in entropies:
                # Normalize each entropy to 0-1 range
                normalized = self._normalize_entropy(entropies[level], level)
                aggregate += weight * normalized
        
        return aggregate
    
    def _normalize_entropy(self, entropy: float, level: str) -> float:
        """
        Normalize entropy values to 0-1 range based on typical bounds.
        
        Args:
            entropy: Raw entropy value
            level: Entropy level for normalization
            
        Returns:
            Normalized entropy between 0 and 1
        """
        # Typical maximum entropy values for English text
        max_values = {
            'character': 6.0,  # Approximate upper bound for character entropy
            'word': 12.0,      # Approximate upper bound for word entropy
            'sentence': 4.0    # Approximate upper bound for sentence structure
        }
        
        max_val = max_values.get(level, 10.0)
        return min(entropy / max_val, 1.0)
    
    def analyze_information_density(self, text: str) -> Dict[str, any]:
        """
        Analyze information density across text segments.
        
        Identifies areas of high/low information content.
        """
        if not text:
            return {'segments': [], 'density_map': [], 'average_density': 0.0}
        
        # Split text into paragraphs or segments
        segments = text.split('\n\n')
        segments = [s.strip() for s in segments if s.strip()]
        
        if not segments:
            return {'segments': [], 'density_map': [], 'average_density': 0.0}
        
        density_map = []
        total_density = 0.0
        
        for i, segment in enumerate(segments):
            entropy = self.calculate_entropy(segment, 'all')
            density = entropy.get('aggregate', 0.0)
            
            density_map.append({
                'segment_index': i,
                'text_preview': segment[:100] + '...' if len(segment) > 100 else segment,
                'density': density,
                'character_entropy': entropy.get('character', 0.0),
                'word_entropy': entropy.get('word', 0.0),
                'sentence_entropy': entropy.get('sentence', 0.0)
            })
            
            total_density += density
        
        average_density = total_density / len(segments) if segments else 0.0
        
        return {
            'segments': len(segments),
            'density_map': density_map,
            'average_density': average_density,
            'high_density_segments': [d for d in density_map if d['density'] > average_density],
            'low_density_segments': [d for d in density_map if d['density'] < average_density * 0.7]
        }
    
    def calculate_redundancy(self, text: str) -> float:
        """
        Calculate text redundancy (inverse of entropy efficiency).
        
        Returns:
            Redundancy score between 0 (no redundancy) and 1 (high redundancy)
        """
        if not text:
            return 0.0
        
        # Calculate actual entropy
        actual_entropy = self.calculate_character_entropy(text)
        
        # Calculate maximum possible entropy (all characters equally likely)
        unique_chars = len(set(text))
        if unique_chars <= 1:
            return 1.0  # Maximum redundancy
        
        max_entropy = math.log2(unique_chars)
        
        # Redundancy = 1 - (actual_entropy / max_entropy)
        if max_entropy == 0:
            return 0.0
        
        efficiency = actual_entropy / max_entropy
        redundancy = 1.0 - efficiency
        
        return max(0.0, min(1.0, redundancy))
    
    def get_entropy_statistics(self, text: str) -> Dict[str, any]:
        """
        Get comprehensive entropy statistics for text.
        
        Returns detailed analysis including entropy, redundancy, and patterns.
        """
        if not text:
            return {
                'entropy': {'character': 0.0, 'word': 0.0, 'sentence': 0.0},
                'redundancy': 0.0,
                'information_density': 0.0,
                'vocabulary_richness': 0.0,
                'structural_complexity': 0.0
            }
        
        # Calculate all entropy levels
        entropy = self.calculate_entropy(text, 'all')
        
        # Calculate redundancy
        redundancy = self.calculate_redundancy(text)
        
        # Calculate vocabulary richness (unique words / total words)
        words = re.findall(r'\b\w+\b', text.lower())
        vocabulary_richness = len(set(words)) / len(words) if words else 0.0
        
        # Calculate structural complexity based on sentence variation
        structural_complexity = entropy.get('sentence', 0.0) / 4.0  # Normalized
        
        return {
            'entropy': entropy,
            'redundancy': redundancy,
            'information_density': entropy.get('aggregate', 0.0),
            'vocabulary_richness': vocabulary_richness,
            'structural_complexity': structural_complexity,
            'text_length': len(text),
            'word_count': len(words),
            'unique_words': len(set(words)) if words else 0,
            'average_word_length': sum(len(w) for w in words) / len(words) if words else 0.0
        }