"""
Unit tests for MIAIR optimization engine.

Tests document optimization strategies, refinement techniques,
and iterative improvement processes.
"""

import pytest
import time
from devdocai.miair.optimizer import (
    MIAIROptimizer, OptimizationConfig, OptimizationResult,
    OptimizationStrategy
)
from devdocai.miair.entropy import ShannonEntropyCalculator
from devdocai.miair.scorer import QualityScorer, QualityMetrics


class TestMIAIROptimizer:
    """Test suite for optimization engine."""
    
    @pytest.fixture
    def optimizer(self):
        """Create optimizer instance."""
        config = OptimizationConfig(
            strategy=OptimizationStrategy.HILL_CLIMBING,
            max_iterations=5,
            target_quality=0.8,
            improvement_threshold=0.01
        )
        return MIAIROptimizer(config=config)
    
    @pytest.fixture
    def gradient_optimizer(self):
        """Create gradient-based optimizer."""
        config = OptimizationConfig(
            strategy=OptimizationStrategy.GRADIENT_BASED,
            max_iterations=5,
            target_quality=0.8
        )
        return MIAIROptimizer(config=config)
    
    @pytest.fixture
    def poor_document(self):
        """Document with poor quality."""
        return """
        guide
        
        TODO: add intro
        
        setup:
        install stuff
        
        [placeholder]
        """
    
    @pytest.fixture
    def moderate_document(self):
        """Document with moderate quality."""
        return """
        # User Guide
        
        This guide explains how to use our system.
        
        ## Installation
        
        To install, run the setup script.
        
        ## Usage
        
        Basic usage is simple. Just run the program.
        """
    
    @pytest.fixture
    def good_document(self):
        """High quality document."""
        return """
        # Comprehensive User Guide
        
        ## Introduction
        
        This guide provides detailed instructions for using our advanced system.
        We'll cover installation, configuration, and best practices.
        
        ## Installation
        
        Follow these steps to install:
        
        ```bash
        pip install our-system
        ```
        
        ## Configuration
        
        Configure the system by editing config.yml:
        
        ```yaml
        setting: value
        option: enabled
        ```
        
        ## Examples
        
        Here's a complete example:
        
        ```python
        import our_system
        system = our_system.init()
        system.run()
        ```
        
        ## References
        
        - [Documentation](https://docs.example.com)
        - [Support](https://support.example.com)
        
        ## Conclusion
        
        This guide covered essential features. For advanced usage, see our documentation.
        """
    
    def test_initialization(self, optimizer):
        """Test optimizer initialization."""
        assert optimizer.config.strategy == OptimizationStrategy.HILL_CLIMBING
        assert optimizer.config.max_iterations == 5
        assert optimizer.config.target_quality == 0.8
        assert optimizer.entropy_calc is not None
        assert optimizer.scorer is not None
    
    def test_optimize_poor_document(self, optimizer, poor_document):
        """Test optimizing poor quality document."""
        result = optimizer.optimize_document(poor_document)
        
        assert isinstance(result, OptimizationResult)
        assert result.original_content == poor_document
        assert result.optimized_content != poor_document
        assert result.optimized_score.overall > result.original_score.overall
        assert result.iterations > 0
        assert len(result.improvements) > 0
    
    def test_optimize_good_document(self, optimizer, good_document):
        """Test optimizing already good document."""
        result = optimizer.optimize_document(good_document)
        
        # Should recognize good quality and not over-optimize
        assert result.iterations <= optimizer.config.max_iterations
        
        # Quality might improve slightly or stay same
        assert result.optimized_score.overall >= result.original_score.overall
    
    def test_hill_climbing_strategy(self, optimizer, moderate_document):
        """Test hill climbing optimization strategy."""
        result = optimizer.optimize_document(moderate_document)
        
        # Check improvements were applied
        assert len(result.improvements) > 0
        
        # Each improvement should have required fields
        for improvement in result.improvements:
            assert 'strategy' in improvement
            assert 'dimension' in improvement
            assert 'improvement' in improvement
            assert 'iteration' in improvement
    
    def test_gradient_based_strategy(self, gradient_optimizer, moderate_document):
        """Test gradient-based optimization strategy."""
        result = gradient_optimizer.optimize_document(moderate_document)
        
        assert result.iterations > 0
        
        # Check gradient-specific fields
        if result.improvements:
            for improvement in result.improvements:
                if 'gradients' in improvement:
                    gradients = improvement['gradients']
                    assert 'completeness' in gradients
                    assert 'clarity' in gradients
                    assert 'consistency' in gradients
                    assert 'accuracy' in gradients
    
    def test_optimization_config_validation(self):
        """Test configuration validation."""
        # Invalid target quality
        with pytest.raises(ValueError):
            OptimizationConfig(target_quality=1.5)
        
        with pytest.raises(ValueError):
            OptimizationConfig(target_quality=-0.1)
        
        # Invalid entropy weight
        with pytest.raises(ValueError):
            OptimizationConfig(entropy_balance_weight=1.5)
    
    def test_improvement_percentage_calculation(self):
        """Test improvement percentage calculation."""
        result = OptimizationResult(
            original_content="original",
            optimized_content="optimized",
            original_score=QualityMetrics(overall=0.5),
            optimized_score=QualityMetrics(overall=0.75),
            iterations=1,
            improvements=[],
            success=True,
            elapsed_time=1.0
        )
        
        improvement = result.improvement_percentage()
        assert improvement == 50.0  # 0.5 to 0.75 is 50% improvement
        
        # Test zero original score
        result.original_score.overall = 0.0
        improvement = result.improvement_percentage()
        assert improvement == 0.0
    
    def test_refinement_strategies(self, optimizer):
        """Test individual refinement strategies."""
        # Test add missing sections
        doc = "Some content without sections"
        refined = optimizer._add_missing_sections(doc, None)
        assert "## Introduction" in refined or "## Usage" in refined
        
        # Test expand content
        doc = "# Title\n\nShort content"
        refined = optimizer._expand_content(doc, None)
        assert len(refined) >= len(doc)
        
        # Test simplify sentences
        doc = "This is a very long and complex sentence that contains multiple clauses and subclauses which make it difficult to understand and parse effectively, especially for readers who are not familiar with the subject matter being discussed."
        refined = optimizer._simplify_sentences(doc, None)
        assert refined is not None
        
        # Test standardize terminology
        doc = "Use e-mail to contact us. Send an E-mail today."
        refined = optimizer._standardize_terminology(doc, None)
        assert "email" in refined.lower()
        assert "e-mail" not in refined.lower()
    
    def test_calculate_improvement(self, optimizer):
        """Test improvement calculation."""
        original = QualityMetrics(
            completeness=0.5,
            clarity=0.6,
            consistency=0.7,
            accuracy=0.8,
            overall=0.65
        )
        
        optimized = QualityMetrics(
            completeness=0.7,
            clarity=0.8,
            consistency=0.8,
            accuracy=0.9,
            overall=0.8
        )
        
        improvements = optimizer.calculate_improvement(original, optimized)
        
        assert improvements['completeness'] == 40.0  # 0.5 to 0.7
        assert improvements['clarity'] == pytest.approx(33.33, rel=0.1)
        assert improvements['consistency'] == pytest.approx(14.29, rel=0.1)
        assert improvements['accuracy'] == 12.5
        assert improvements['overall'] == pytest.approx(23.08, rel=0.1)
    
    def test_max_iterations_limit(self, optimizer):
        """Test max iterations limit is respected."""
        config = OptimizationConfig(
            max_iterations=2,
            target_quality=0.99  # Very high target
        )
        limited_optimizer = MIAIROptimizer(config=config)
        
        doc = "Short document"
        result = limited_optimizer.optimize_document(doc)
        
        assert result.iterations <= 2
    
    def test_timeout_limit(self):
        """Test timeout limit is respected."""
        config = OptimizationConfig(
            max_iterations=100,
            timeout_seconds=0.1  # Very short timeout
        )
        timeout_optimizer = MIAIROptimizer(config=config)
        
        doc = "Document to optimize" * 100
        result = timeout_optimizer.optimize_document(doc)
        
        assert result.elapsed_time < 1.0  # Should stop quickly
    
    def test_entropy_balance(self, optimizer):
        """Test entropy balance consideration."""
        # Document with good entropy balance
        balanced_doc = """
        # Title
        
        This document has varied content. Some parts are simple.
        Other parts are more complex with technical details.
        
        ## Section
        
        More varied content here with different sentence structures.
        """
        
        result = optimizer.optimize_document(balanced_doc)
        
        # Should maintain reasonable entropy
        original_entropy = optimizer.entropy_calc.calculate_entropy(
            balanced_doc, 'all'
        )
        optimized_entropy = optimizer.entropy_calc.calculate_entropy(
            result.optimized_content, 'all'
        )
        
        # Entropy shouldn't change drastically
        entropy_change = abs(
            original_entropy.get('aggregate', 0) - 
            optimized_entropy.get('aggregate', 0)
        )
        assert entropy_change < 0.5
    
    def test_caching_functionality(self):
        """Test caching improves performance."""
        config = OptimizationConfig(enable_caching=True)
        cached_optimizer = MIAIROptimizer(config=config)
        
        doc = "Test document"
        
        # First optimization
        start = time.time()
        result1 = cached_optimizer.optimize_document(doc)
        time1 = time.time() - start
        
        # Second optimization of same document
        start = time.time()
        result2 = cached_optimizer.optimize_document(doc)
        time2 = time.time() - start
        
        # Cache might help with repeated analysis
        assert result1.optimized_content == result2.optimized_content
    
    def test_empty_document_optimization(self, optimizer):
        """Test optimization of empty document."""
        result = optimizer.optimize_document("")
        
        assert result.original_content == ""
        # Optimizer should add content to empty document
        assert len(result.optimized_content) > 0
        assert result.optimized_score.overall > 0
    
    def test_refinement_with_metadata(self, optimizer):
        """Test refinement with metadata context."""
        doc = "Simple document"
        metadata = {
            'version': '1.0.0',
            'author': 'Test Author',
            'type': 'technical'
        }
        
        result = optimizer.optimize_document(doc, metadata)
        
        # Metadata should influence optimization
        assert 'version' in result.optimized_content.lower() or \
               'Version' in result.optimized_content
    
    def test_success_flag(self, optimizer):
        """Test success flag is set correctly."""
        # Document that can reach target
        doc = "# Title\n\nContent here."
        optimizer.config.target_quality = 0.3  # Low target
        
        result = optimizer.optimize_document(doc)
        
        if result.optimized_score.overall >= 0.3:
            assert result.success
        else:
            assert not result.success
        
        # Document that can't reach target
        optimizer.config.target_quality = 0.99  # Very high target
        optimizer.config.max_iterations = 1  # Limited iterations
        
        result = optimizer.optimize_document("x")
        assert not result.success  # Unlikely to reach 0.99 in 1 iteration


class TestOptimizerEdgeCases:
    """Test edge cases for optimizer."""
    
    @pytest.fixture
    def optimizer(self):
        """Create optimizer for edge case testing."""
        return MIAIROptimizer()
    
    def test_unicode_content(self, optimizer):
        """Test optimization with unicode content."""
        doc = "文档 with mixed 内容 and émojis 😀"
        result = optimizer.optimize_document(doc)
        
        assert result is not None
        assert result.iterations >= 0
    
    def test_code_heavy_document(self, optimizer):
        """Test optimization of code-heavy document."""
        doc = """
        ```python
        def function():
            return True
        ```
        
        ```javascript
        console.log('test');
        ```
        
        Small text between code blocks.
        
        ```bash
        echo "test"
        ```
        """
        
        result = optimizer.optimize_document(doc)
        
        # Should preserve code blocks
        assert "```" in result.optimized_content
        assert "def function" in result.optimized_content
    
    def test_very_long_document(self, optimizer):
        """Test optimization of very long document."""
        # Create a long document
        sections = []
        for i in range(100):
            sections.append(f"## Section {i}\n\nContent for section {i}.")
        
        long_doc = "\n\n".join(sections)
        
        # Use short timeout to ensure it completes
        optimizer.config.timeout_seconds = 5.0
        optimizer.config.max_iterations = 2
        
        result = optimizer.optimize_document(long_doc)
        
        assert result is not None
        assert result.elapsed_time < 10.0  # Should complete reasonably quickly