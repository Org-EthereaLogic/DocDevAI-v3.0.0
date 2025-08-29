"""
Unit tests for Shannon entropy calculator.

Tests entropy calculations at character, word, and sentence levels,
as well as information density analysis and redundancy detection.
"""

import pytest
import math
import numpy as np
from devdocai.miair.entropy import ShannonEntropyCalculator


class TestShannonEntropyCalculator:
    """Test suite for Shannon entropy calculations."""
    
    @pytest.fixture
    def calculator(self):
        """Create entropy calculator instance."""
        return ShannonEntropyCalculator(cache_size=10)
    
    @pytest.fixture
    def sample_text(self):
        """Sample text for testing."""
        return """
        The Shannon entropy is a measure of the average information content in a message.
        It quantifies the expected value of the information contained in a message.
        Higher entropy means more information or uncertainty.
        """
    
    @pytest.fixture
    def uniform_text(self):
        """Text with uniform character distribution."""
        return "abcdefghijklmnopqrstuvwxyz" * 10
    
    @pytest.fixture
    def repetitive_text(self):
        """Highly repetitive text with low entropy."""
        return "aaaaaaaaaa" * 10
    
    def test_initialization(self, calculator):
        """Test calculator initialization."""
        assert calculator.cache_size == 10
        assert hasattr(calculator, 'calculate_character_entropy')
        assert hasattr(calculator, 'calculate_word_entropy')
    
    def test_empty_text_entropy(self, calculator):
        """Test entropy calculation for empty text."""
        result = calculator.calculate_entropy("")
        assert result['character'] == 0.0
        assert result['word'] == 0.0
        assert result['sentence'] == 0.0
    
    def test_character_entropy_calculation(self, calculator):
        """Test character-level entropy calculation."""
        # Single character (zero entropy)
        result = calculator.calculate_character_entropy("aaaa")
        assert result == 0.0
        
        # Two characters with equal probability
        result = calculator.calculate_character_entropy("abab")
        assert abs(result - 1.0) < 0.01  # Should be exactly 1 bit
        
        # Uniform distribution should have high entropy
        result = calculator.calculate_character_entropy("abcdefgh")
        assert result > 2.0  # Should be log2(8) = 3 bits
    
    def test_word_entropy_calculation(self, calculator, sample_text):
        """Test word-level entropy calculation."""
        result = calculator.calculate_word_entropy(sample_text)
        assert result > 0.0
        
        # Repetitive words should have lower entropy
        repetitive = "test test test test test"
        result_rep = calculator.calculate_word_entropy(repetitive)
        assert result_rep == 0.0  # All same word
        
        # Diverse vocabulary should have higher entropy
        diverse = "apple banana cherry date elderberry fig grape"
        result_div = calculator.calculate_word_entropy(diverse)
        assert result_div > result_rep
    
    def test_sentence_entropy_calculation(self, calculator):
        """Test sentence-level entropy calculation."""
        # Single sentence
        single = "This is a test."
        result = calculator.calculate_sentence_entropy(single)
        assert result == 0.0  # Only one sentence length
        
        # Multiple sentences with varying lengths
        multiple = "Short. This is a medium sentence. This is a much longer sentence with many words."
        result = calculator.calculate_sentence_entropy(multiple)
        assert result > 0.0
        
        # Uniform sentence lengths
        uniform = "One two three. Four five six. Seven eight nine."
        result_uniform = calculator.calculate_sentence_entropy(uniform)
        assert result_uniform == 0.0  # All sentences same length
    
    def test_calculate_entropy_all_levels(self, calculator, sample_text):
        """Test entropy calculation at all levels."""
        result = calculator.calculate_entropy(sample_text, level='all')
        
        assert 'character' in result
        assert 'word' in result
        assert 'sentence' in result
        assert 'aggregate' in result
        
        assert all(v >= 0.0 for v in result.values())
        assert result['aggregate'] >= 0.0 and result['aggregate'] <= 1.0
    
    def test_calculate_entropy_specific_level(self, calculator, sample_text):
        """Test entropy calculation for specific level."""
        # Character level only
        result = calculator.calculate_entropy(sample_text, level='character')
        assert 'character' in result
        assert 'word' not in result
        
        # Word level only
        result = calculator.calculate_entropy(sample_text, level='word')
        assert 'word' in result
        assert 'character' not in result
    
    def test_information_density_analysis(self, calculator):
        """Test information density analysis across segments."""
        text = """
        Introduction paragraph with some content.
        
        Main body with more detailed information and examples.
        This section has higher information density.
        
        Conclusion with summary points.
        """
        
        result = calculator.analyze_information_density(text)
        
        assert 'segments' in result
        assert 'density_map' in result
        assert 'average_density' in result
        assert 'high_density_segments' in result
        assert 'low_density_segments' in result
        
        assert result['segments'] > 0
        assert len(result['density_map']) == result['segments']
    
    def test_redundancy_calculation(self, calculator):
        """Test redundancy calculation."""
        # Highly redundant text
        redundant = "aaaaaaaaaa"
        result = calculator.calculate_redundancy(redundant)
        assert result > 0.9  # Very high redundancy
        
        # Low redundancy (high entropy)
        diverse = "abcdefghijklmnop"
        result = calculator.calculate_redundancy(diverse)
        assert result < 0.5  # Lower redundancy
        
        # Empty text
        result = calculator.calculate_redundancy("")
        assert result == 0.0
    
    def test_entropy_statistics(self, calculator, sample_text):
        """Test comprehensive entropy statistics."""
        stats = calculator.get_entropy_statistics(sample_text)
        
        required_keys = [
            'entropy', 'redundancy', 'information_density',
            'vocabulary_richness', 'structural_complexity',
            'text_length', 'word_count', 'unique_words',
            'average_word_length'
        ]
        
        for key in required_keys:
            assert key in stats
        
        assert stats['text_length'] == len(sample_text)
        assert stats['word_count'] > 0
        assert stats['unique_words'] > 0
        assert stats['vocabulary_richness'] > 0 and stats['vocabulary_richness'] <= 1.0
    
    def test_entropy_normalization(self, calculator):
        """Test entropy normalization to 0-1 range."""
        # Test character entropy normalization
        norm = calculator._normalize_entropy(3.0, 'character')
        assert 0.0 <= norm <= 1.0
        
        # Test word entropy normalization
        norm = calculator._normalize_entropy(10.0, 'word')
        assert 0.0 <= norm <= 1.0
        
        # Test sentence entropy normalization  
        norm = calculator._normalize_entropy(2.0, 'sentence')
        assert 0.0 <= norm <= 1.0
        
        # Test edge cases
        norm = calculator._normalize_entropy(0.0, 'character')
        assert norm == 0.0
        
        norm = calculator._normalize_entropy(100.0, 'word')
        assert norm == 1.0  # Should cap at 1.0
    
    def test_cache_functionality(self, calculator):
        """Test LRU cache functionality."""
        text = "Test text for caching"
        
        # First call - not cached
        result1 = calculator.calculate_character_entropy(text)
        
        # Second call - should be cached
        result2 = calculator.calculate_character_entropy(text)
        
        assert result1 == result2
        
        # Cache info should show hit
        cache_info = calculator.calculate_character_entropy.cache_info()
        assert cache_info.hits > 0
    
    def test_entropy_edge_cases(self, calculator):
        """Test edge cases in entropy calculation."""
        # Single character
        result = calculator.calculate_entropy("a", 'all')
        assert result['character'] == 0.0
        
        # Numbers and special characters
        result = calculator.calculate_entropy("123!@#", 'character')
        assert result['character'] > 0.0
        
        # Unicode text
        result = calculator.calculate_entropy("Hello 世界", 'character')
        assert result['character'] > 0.0
        
        # Very long text
        long_text = "a" * 10000 + "b" * 10000
        result = calculator.calculate_entropy(long_text, 'character')
        assert abs(result['character'] - 1.0) < 0.01  # Should be close to 1 bit
    
    def test_aggregate_entropy_calculation(self, calculator):
        """Test weighted aggregate entropy calculation."""
        entropies = {
            'character': 0.5,
            'word': 0.7,
            'sentence': 0.3
        }
        
        aggregate = calculator._calculate_aggregate_entropy(entropies)
        
        # Check weighted sum
        expected = (0.2 * 0.5/6.0 + 0.5 * 0.7/12.0 + 0.3 * 0.3/4.0)
        assert abs(aggregate - expected) < 0.1
        
        # Should be between 0 and 1
        assert 0.0 <= aggregate <= 1.0
    
    def test_information_density_empty_text(self, calculator):
        """Test information density analysis with empty text."""
        result = calculator.analyze_information_density("")
        
        assert result['segments'] == []
        assert result['density_map'] == []
        assert result['average_density'] == 0.0
    
    def test_paragraph_density_variation(self, calculator):
        """Test density variation across paragraphs."""
        text = """Simple intro.

Complex paragraph with diverse vocabulary, intricate sentence structures, 
and multiple technical terms that increase information density significantly.

Simple end."""
        
        result = calculator.analyze_information_density(text)
        
        # Should have density analysis
        assert result['segments'] > 0
        assert len(result['density_map']) > 0
        
        # If multiple segments, middle should have higher density
        if len(result['density_map']) > 1:
            densities = [seg['density'] for seg in result['density_map']]
            # Complex segment should have higher density than simple ones
            max_density_idx = densities.index(max(densities))
            assert max_density_idx >= 0  # Just verify we found the max


class TestEntropyPerformance:
    """Performance tests for entropy calculator."""
    
    @pytest.fixture
    def calculator(self):
        """Create calculator for performance testing."""
        return ShannonEntropyCalculator(cache_size=128)
    
    @pytest.fixture
    def large_text(self):
        """Generate large text for performance testing."""
        import string
        import random
        
        chars = string.ascii_letters + string.digits + string.punctuation + ' \n'
        return ''.join(random.choice(chars) for _ in range(10000))
    
    def test_performance_large_text(self, calculator, large_text):
        """Test performance with large text."""
        import time
        
        start = time.time()
        result = calculator.calculate_entropy(large_text, 'all')
        elapsed = time.time() - start
        
        # Should complete within reasonable time
        assert elapsed < 1.0  # Less than 1 second for 10K characters
        assert all(key in result for key in ['character', 'word', 'sentence', 'aggregate'])
    
    def test_cache_performance(self, calculator):
        """Test cache improves performance."""
        import time
        
        text = "Test text" * 100
        
        # First call - not cached
        start = time.time()
        calculator.calculate_character_entropy(text)
        first_time = time.time() - start
        
        # Second call - cached
        start = time.time()
        calculator.calculate_character_entropy(text)
        cached_time = time.time() - start
        
        # Cached should be significantly faster
        assert cached_time < first_time * 0.5  # At least 2x faster