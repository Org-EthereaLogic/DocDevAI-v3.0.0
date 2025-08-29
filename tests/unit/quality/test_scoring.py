"""
Unit tests for Quality Scoring.
"""

import pytest
from devdocai.quality.scoring import QualityScorer, ScoringMetrics
from devdocai.quality.models import (
    QualityDimension, DimensionScore, QualityIssue, 
    SeverityLevel, QualityConfig
)


class TestScoringMetrics:
    """Test suite for ScoringMetrics."""
    
    def test_metrics_initialization(self):
        """Test metrics initialization."""
        metrics = ScoringMetrics()
        
        assert metrics.word_count == 0
        assert metrics.sentence_count == 0
        assert metrics.paragraph_count == 0
        assert metrics.avg_sentence_length == 0.0
    
    def test_content_diversity(self):
        """Test content diversity calculation."""
        metrics = ScoringMetrics(
            code_block_count=2,
            heading_count=3,
            link_count=5,
            image_count=0,
            list_count=2,
            table_count=1
        )
        
        diversity = metrics.content_diversity
        assert 0 <= diversity <= 1
        assert diversity == 5/6  # 5 out of 6 element types present


class TestQualityScorer:
    """Test suite for QualityScorer."""
    
    @pytest.fixture
    def scorer(self):
        """Create scorer instance."""
        return QualityScorer()
    
    @pytest.fixture
    def dimension_scores(self):
        """Create sample dimension scores."""
        return [
            DimensionScore(
                dimension=QualityDimension.COMPLETENESS,
                score=80.0,
                weight=0.25,
                issues=[]
            ),
            DimensionScore(
                dimension=QualityDimension.CLARITY,
                score=90.0,
                weight=0.20,
                issues=[]
            ),
            DimensionScore(
                dimension=QualityDimension.STRUCTURE,
                score=85.0,
                weight=0.20,
                issues=[]
            ),
            DimensionScore(
                dimension=QualityDimension.ACCURACY,
                score=95.0,
                weight=0.25,
                issues=[]
            ),
            DimensionScore(
                dimension=QualityDimension.FORMATTING,
                score=70.0,
                weight=0.10,
                issues=[]
            )
        ]
    
    def test_scorer_initialization(self):
        """Test scorer initialization."""
        config = QualityConfig(quality_gate_threshold=90.0)
        scorer = QualityScorer(config)
        
        assert scorer.config.quality_gate_threshold == 90.0
        assert isinstance(scorer._cache, dict)
    
    def test_calculate_overall_score(self, scorer, dimension_scores):
        """Test overall score calculation."""
        score = scorer.calculate_overall_score(dimension_scores)
        
        # Manual calculation
        expected = (80*0.25 + 90*0.20 + 85*0.20 + 95*0.25 + 70*0.10) / 1.0
        
        assert abs(score - expected) < 0.1
        assert 0 <= score <= 100
    
    def test_calculate_overall_score_with_critical_issues(self, scorer):
        """Test score calculation with critical issues."""
        dimension_scores = [
            DimensionScore(
                dimension=QualityDimension.COMPLETENESS,
                score=90.0,
                issues=[
                    QualityIssue(
                        dimension=QualityDimension.COMPLETENESS,
                        severity=SeverityLevel.CRITICAL,
                        description="Critical issue",
                        impact_score=10.0
                    )
                ]
            )
        ]
        
        score = scorer.calculate_overall_score(dimension_scores)
        
        # Should apply penalty for critical issue
        assert score < 90.0
    
    def test_score_completeness(self, scorer):
        """Test completeness scoring."""
        metrics = ScoringMetrics(
            word_count=500,
            code_block_count=2,
            technical_density=0.4
        )
        
        score, issues = scorer.score_completeness(
            metrics,
            expected_sections=['intro', 'usage', 'api'],
            found_sections=['intro', 'usage']
        )
        
        assert 0 <= score <= 100
        assert len(issues) > 0  # Should have issue for missing 'api' section
        
        # Check issue details
        missing_section_issue = next(
            (i for i in issues if 'Missing required section' in i.description),
            None
        )
        assert missing_section_issue is not None
        assert missing_section_issue.severity == SeverityLevel.HIGH
    
    def test_score_clarity(self, scorer):
        """Test clarity scoring."""
        metrics = ScoringMetrics(
            word_count=500,
            sentence_count=20,
            avg_sentence_length=25,
            readability_score=45
        )
        
        score, issues = scorer.score_clarity(
            metrics,
            complex_sentences=8,
            jargon_count=30
        )
        
        assert 0 <= score <= 100
        
        # Should have issues for high complexity and jargon
        if metrics.avg_sentence_length > 25:
            assert any('sentence' in i.description.lower() for i in issues)
    
    def test_score_structure(self, scorer):
        """Test structure scoring."""
        metrics = ScoringMetrics(
            heading_count=5,
            paragraph_count=10,
            content_diversity=0.5
        )
        
        score, issues = scorer.score_structure(
            metrics,
            heading_hierarchy=[1, 2, 2, 3, 2],
            section_balance=0.7
        )
        
        assert 0 <= score <= 100
        
        # Good structure should have high score
        assert score > 70
    
    def test_score_structure_no_headings(self, scorer):
        """Test structure scoring with no headings."""
        metrics = ScoringMetrics(heading_count=0)
        
        score, issues = scorer.score_structure(
            metrics,
            heading_hierarchy=[],
            section_balance=0.0
        )
        
        assert score < 100
        assert any('No headings found' in i.description for i in issues)
    
    def test_score_accuracy(self, scorer):
        """Test accuracy scoring."""
        score, issues = scorer.score_accuracy(
            outdated_refs=2,
            broken_links=3,
            code_errors=1
        )
        
        assert 0 <= score <= 100
        assert len(issues) == 3  # One for each type of issue
        
        # Check for critical issue for code errors
        code_error_issue = next(
            (i for i in issues if 'code error' in i.description.lower()),
            None
        )
        assert code_error_issue is not None
        assert code_error_issue.severity == SeverityLevel.CRITICAL
    
    def test_score_formatting(self, scorer):
        """Test formatting scoring."""
        metrics = ScoringMetrics(
            paragraph_count=5,
            avg_paragraph_length=600
        )
        
        formatting_errors = [
            "Inconsistent indentation",
            "Missing blank line"
        ]
        
        score, issues = scorer.score_formatting(metrics, formatting_errors)
        
        assert 0 <= score <= 100
        assert len(issues) >= 2  # At least the formatting errors
        
        # Should have issue for long paragraphs
        paragraph_issue = next(
            (i for i in issues if 'Paragraphs are too long' in i.description),
            None
        )
        assert paragraph_issue is not None
    
    def test_calculate_readability(self, scorer):
        """Test readability calculation."""
        text = """
        This is a simple sentence. It has easy words.
        The readability should be high for this text.
        Short sentences help readability scores improve significantly.
        """
        
        readability = scorer.calculate_readability(text)
        
        assert 0 <= readability <= 100
        # Simple text should have decent readability
        assert readability > 30
    
    def test_calculate_readability_empty(self, scorer):
        """Test readability calculation with empty text."""
        readability = scorer.calculate_readability("")
        assert readability == 0.0
    
    def test_custom_weights(self):
        """Test scorer with custom dimension weights."""
        config = QualityConfig(
            dimension_weights={
                QualityDimension.COMPLETENESS: 0.5,
                QualityDimension.CLARITY: 0.2,
                QualityDimension.STRUCTURE: 0.1,
                QualityDimension.ACCURACY: 0.1,
                QualityDimension.FORMATTING: 0.1
            }
        )
        scorer = QualityScorer(config)
        
        dimension_scores = [
            DimensionScore(
                dimension=QualityDimension.COMPLETENESS,
                score=100.0,
                issues=[]
            ),
            DimensionScore(
                dimension=QualityDimension.CLARITY,
                score=50.0,
                issues=[]
            )
        ]
        
        score = scorer.calculate_overall_score(dimension_scores)
        
        # Completeness has high weight and perfect score
        assert score > 70
    
    def test_critical_penalty_calculation(self, scorer):
        """Test critical penalty calculation."""
        dimension_scores = [
            DimensionScore(
                dimension=QualityDimension.ACCURACY,
                score=100.0,
                issues=[
                    QualityIssue(
                        dimension=QualityDimension.ACCURACY,
                        severity=SeverityLevel.CRITICAL,
                        description="Critical",
                        impact_score=10.0
                    ),
                    QualityIssue(
                        dimension=QualityDimension.ACCURACY,
                        severity=SeverityLevel.HIGH,
                        description="High",
                        impact_score=7.0
                    )
                ]
            )
        ]
        
        score = scorer.calculate_overall_score(dimension_scores)
        
        # Should apply penalties: 1 critical (10) + 1 high (3) = 13
        assert score < 100 - 13
    
    def test_score_completeness_short_document(self, scorer):
        """Test completeness scoring for very short document."""
        metrics = ScoringMetrics(word_count=50)
        
        score, issues = scorer.score_completeness(
            metrics,
            expected_sections=[],
            found_sections=[]
        )
        
        assert score < 100
        assert any('too short' in i.description.lower() for i in issues)
    
    def test_score_clarity_high_jargon(self, scorer):
        """Test clarity scoring with high jargon density."""
        metrics = ScoringMetrics(
            word_count=100,
            sentence_count=5,
            readability_score=60
        )
        
        score, issues = scorer.score_clarity(
            metrics,
            complex_sentences=0,
            jargon_count=15  # 15% jargon density
        )
        
        assert score < 100
        assert any('jargon' in i.description.lower() for i in issues)