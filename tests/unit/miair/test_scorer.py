"""
Unit tests for quality scoring system.

Tests multi-dimensional quality assessment including completeness,
clarity, consistency, and accuracy scoring.
"""

import pytest
import numpy as np
from devdocai.miair.scorer import (
    QualityScorer, QualityMetrics, ScoringWeights, QualityDimension
)


class TestQualityScorer:
    """Test suite for quality scoring."""
    
    @pytest.fixture
    def scorer(self):
        """Create quality scorer instance."""
        return QualityScorer()
    
    @pytest.fixture
    def custom_scorer(self):
        """Create scorer with custom weights."""
        weights = ScoringWeights(
            completeness=0.4,
            clarity=0.3,
            consistency=0.2,
            accuracy=0.1
        )
        return QualityScorer(weights=weights)
    
    @pytest.fixture
    def complete_document(self):
        """Well-structured, complete document."""
        return """
        # Introduction
        
        This document provides a comprehensive guide to using our API.
        We'll cover authentication, endpoints, and best practices.
        
        ## Authentication
        
        To authenticate with our API, you need an API key:
        
        ```python
        import requests
        
        headers = {'Authorization': 'Bearer YOUR_API_KEY'}
        response = requests.get('https://api.example.com/data', headers=headers)
        ```
        
        ## Endpoints
        
        Our API provides the following endpoints:
        
        - GET /users - List all users
        - GET /users/:id - Get specific user
        - POST /users - Create new user
        
        ## Examples
        
        Here's a complete example:
        
        ```python
        # Create a new user
        user_data = {'name': 'John Doe', 'email': 'john@example.com'}
        response = requests.post('https://api.example.com/users', json=user_data)
        ```
        
        ## Best Practices
        
        1. Always use HTTPS
        2. Store API keys securely
        3. Implement rate limiting
        
        ## Reference
        
        For more information, see:
        - [API Documentation](https://docs.example.com)
        - [Support](https://support.example.com)
        
        ## Conclusion
        
        This guide covered the basics of using our API. 
        For advanced features, consult the full documentation.
        """
    
    @pytest.fixture
    def incomplete_document(self):
        """Document with quality issues."""
        return """
        API Guide
        
        TODO: Add introduction
        
        Authentication is done with keys.
        
        [placeholder for examples]
        
        FIXME: Add endpoint documentation
        """
    
    def test_initialization(self, scorer):
        """Test scorer initialization."""
        assert scorer.weights is not None
        assert scorer.weights.completeness == 0.25
        assert scorer.weights.clarity == 0.25
        assert scorer.weights.consistency == 0.25
        assert scorer.weights.accuracy == 0.25
    
    def test_custom_weights_initialization(self, custom_scorer):
        """Test initialization with custom weights."""
        assert custom_scorer.weights.completeness == 0.4
        assert custom_scorer.weights.clarity == 0.3
        assert custom_scorer.weights.consistency == 0.2
        assert custom_scorer.weights.accuracy == 0.1
        
        # Weights should sum to 1.0
        total = (custom_scorer.weights.completeness + 
                 custom_scorer.weights.clarity +
                 custom_scorer.weights.consistency +
                 custom_scorer.weights.accuracy)
        assert abs(total - 1.0) < 0.001
    
    def test_score_empty_document(self, scorer):
        """Test scoring empty document."""
        metrics = scorer.score_document("")
        
        assert metrics.completeness == 0.0
        assert metrics.clarity == 0.0
        assert metrics.consistency == 0.0
        assert metrics.accuracy == 0.0
        assert metrics.overall == 0.0
    
    def test_score_complete_document(self, scorer, complete_document):
        """Test scoring well-structured document."""
        metrics = scorer.score_document(complete_document)
        
        # Should have high scores
        assert metrics.completeness > 0.7
        assert metrics.clarity > 0.6
        assert metrics.consistency > 0.6
        assert metrics.accuracy > 0.5
        assert metrics.overall > 0.6
    
    def test_score_incomplete_document(self, scorer, incomplete_document):
        """Test scoring document with issues."""
        metrics = scorer.score_document(incomplete_document)
        
        # Should have low scores
        assert metrics.completeness < 0.4  # Has TODOs and placeholders
        assert metrics.overall < 0.5
    
    def test_completeness_scoring(self, scorer):
        """Test completeness dimension scoring."""
        # Document with sections but no examples
        doc_no_examples = """
        # Introduction
        This is an introduction.
        
        ## Main Content
        Main content here.
        
        ## Conclusion
        Conclusion here.
        """
        score = scorer.score_completeness(doc_no_examples)
        assert score < 0.7  # Missing examples
        
        # Document with TODOs
        doc_with_todos = """
        # Guide
        TODO: Write introduction
        FIXME: Add examples
        Content here.
        """
        score = scorer.score_completeness(doc_with_todos)
        assert score < 0.5  # Penalized for TODOs
        
        # Short document
        short_doc = "This is a very short document."
        score = scorer.score_completeness(short_doc)
        assert score < 0.3  # Too short
    
    def test_clarity_scoring(self, scorer):
        """Test clarity dimension scoring."""
        # Clear, well-structured text
        clear_text = """
        # Clear Documentation
        
        This document explains our system. Each section covers one topic.
        
        ## First Topic
        
        We start with basics. Simple sentences work best. Users understand easily.
        
        ## Second Topic
        
        Next, we cover advanced features. Again, we keep it simple. Examples help understanding.
        """
        score = scorer.score_clarity(clear_text)
        assert score > 0.6
        
        # Complex, unclear text
        complex_text = """
        The utilization of this particular system necessitates a comprehensive understanding of the underlying architectural paradigms and their corresponding implementation methodologies which, when properly comprehended and subsequently applied in accordance with the prescribed operational parameters, will facilitate the achievement of the desired functional outcomes as specified in the requirements documentation that was previously distributed to all stakeholders.
        """
        score = scorer.score_clarity(complex_text)
        assert score < 0.5  # Very complex sentence
        
        # Passive voice heavy
        passive_text = """
        The system was designed by our team. The code was written in Python.
        The tests were created to ensure quality. The documentation was prepared by writers.
        """
        score = scorer.score_clarity(passive_text)
        assert score < 0.7  # Penalized for passive voice
    
    def test_consistency_scoring(self, scorer):
        """Test consistency dimension scoring."""
        # Consistent formatting
        consistent_doc = """
        # Main Title
        
        ## First Section
        Content here.
        
        ## Second Section
        More content.
        
        - Item one
        - Item two
        - Item three
        """
        score = scorer.score_consistency(consistent_doc)
        assert score > 0.6
        
        # Inconsistent formatting
        inconsistent_doc = """
        # main title
        
        ## First Section
        
        ### second section
        
        - Item one
        * Item two
        + item three
        
        email vs e-mail vs Email
        setup vs set-up vs set up
        """
        score = scorer.score_consistency(inconsistent_doc)
        assert score < 0.7  # Inconsistent formatting
    
    def test_accuracy_scoring(self, scorer):
        """Test accuracy dimension scoring."""
        # Document with version info
        accurate_doc = """
        # API Documentation v2.1.0
        
        Last Updated: 2024-01-15
        
        ## Installation
        
        ```python
        pip install api-client==2.1.0
        ```
        
        **Note**: Version 1.0 is deprecated.
        
        ## References
        - [Official Docs](https://docs.example.com)
        - [GitHub](https://github.com/example/api)
        """
        score = scorer.score_accuracy(accurate_doc)
        assert score > 0.6  # Has versions and dates
        
        # Document without version info
        no_version_doc = """
        # Documentation
        
        How to use the API.
        
        ```
        code example
        ```
        """
        score = scorer.score_accuracy(no_version_doc)
        assert score < 0.7
    
    def test_quality_metrics_to_dict(self):
        """Test QualityMetrics to_dict conversion."""
        metrics = QualityMetrics(
            completeness=0.8,
            clarity=0.7,
            consistency=0.9,
            accuracy=0.6,
            overall=0.75
        )
        
        result = metrics.to_dict()
        assert result['completeness'] == 0.8
        assert result['clarity'] == 0.7
        assert result['consistency'] == 0.9
        assert result['accuracy'] == 0.6
        assert result['overall'] == 0.75
    
    def test_weighted_overall_score(self, custom_scorer):
        """Test weighted overall score calculation."""
        doc = "Test document content"
        
        # Mock individual scores for testing
        metrics = custom_scorer.score_document(doc)
        
        # Overall should be weighted combination
        expected = (
            custom_scorer.weights.completeness * metrics.completeness +
            custom_scorer.weights.clarity * metrics.clarity +
            custom_scorer.weights.consistency * metrics.consistency +
            custom_scorer.weights.accuracy * metrics.accuracy
        )
        
        assert abs(metrics.overall - expected) < 0.01
    
    def test_analyze_quality_issues(self, scorer, incomplete_document):
        """Test quality issue analysis."""
        issues = scorer.analyze_quality_issues(incomplete_document)
        
        assert 'completeness' in issues
        assert 'clarity' in issues
        assert 'consistency' in issues
        assert 'accuracy' in issues
        
        # Should identify TODOs and placeholders
        completeness_issues = issues['completeness']
        assert any('TODO' in issue for issue in completeness_issues)
        assert any('placeholder' in issue for issue in completeness_issues)
    
    def test_get_improvement_suggestions(self, scorer):
        """Test improvement suggestion generation."""
        # Low quality metrics
        low_metrics = QualityMetrics(
            completeness=0.3,
            clarity=0.4,
            consistency=0.5,
            accuracy=0.6,
            overall=0.45
        )
        
        suggestions = scorer.get_improvement_suggestions(low_metrics)
        
        assert len(suggestions) > 0
        assert any('completeness' in s.lower() or 'sections' in s.lower() 
                  for s in suggestions)
        
        # High quality metrics
        high_metrics = QualityMetrics(
            completeness=0.9,
            clarity=0.9,
            consistency=0.9,
            accuracy=0.9,
            overall=0.9
        )
        
        suggestions = scorer.get_improvement_suggestions(high_metrics)
        assert any('excellent' in s.lower() for s in suggestions)
    
    def test_scoring_weights_normalization(self):
        """Test automatic weight normalization."""
        # Weights don't sum to 1.0
        weights = ScoringWeights(
            completeness=1.0,
            clarity=1.0,
            consistency=1.0,
            accuracy=1.0
        )
        
        # Should be normalized
        assert abs(weights.completeness - 0.25) < 0.001
        assert abs(weights.clarity - 0.25) < 0.001
        assert abs(weights.consistency - 0.25) < 0.001
        assert abs(weights.accuracy - 0.25) < 0.001
    
    def test_metadata_scoring(self, scorer):
        """Test scoring with metadata context."""
        doc = "Test document"
        metadata = {
            'last_updated': '2024-01-01',
            'version': '1.0.0',
            'author': 'Test Author'
        }
        
        metrics_with_meta = scorer.score_document(doc, metadata)
        metrics_without = scorer.score_document(doc)
        
        # Metadata should potentially affect accuracy score
        assert metrics_with_meta.accuracy >= metrics_without.accuracy
    
    def test_edge_cases(self, scorer):
        """Test edge cases in scoring."""
        # Single word document
        metrics = scorer.score_document("Hello")
        assert metrics.overall >= 0.0
        
        # Only whitespace
        metrics = scorer.score_document("   \n\n   ")
        assert metrics.overall == 0.0
        
        # Very long document
        long_doc = "word " * 10000
        metrics = scorer.score_document(long_doc)
        assert metrics.overall > 0.0
        
        # Document with only code
        code_only = """
        ```python
        def hello():
            return "world"
        ```
        """
        metrics = scorer.score_document(code_only)
        assert metrics.overall > 0.0


class TestScorerPerformance:
    """Performance tests for quality scorer."""
    
    @pytest.fixture
    def scorer(self):
        """Create scorer for performance testing."""
        return QualityScorer()
    
    @pytest.fixture
    def large_document(self):
        """Generate large document for testing."""
        sections = []
        for i in range(50):
            sections.append(f"""
            ## Section {i}
            
            This is content for section {i}. It contains multiple paragraphs
            with various information. We include examples and explanations.
            
            ```python
            def function_{i}():
                return {i}
            ```
            
            More content here with links and references.
            """)
        
        return "\n\n".join(sections)
    
    def test_scoring_performance(self, scorer, large_document):
        """Test scoring performance with large document."""
        import time
        
        start = time.time()
        metrics = scorer.score_document(large_document)
        elapsed = time.time() - start
        
        # Should complete quickly even for large docs
        assert elapsed < 0.5  # Less than 500ms
        assert metrics.overall > 0.0
    
    def test_issue_analysis_performance(self, scorer, large_document):
        """Test issue analysis performance."""
        import time
        
        start = time.time()
        issues = scorer.analyze_quality_issues(large_document)
        elapsed = time.time() - start
        
        assert elapsed < 1.0  # Less than 1 second
        assert len(issues) > 0