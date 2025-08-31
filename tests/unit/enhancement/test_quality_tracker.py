"""
Tests for quality tracking system.
"""

import pytest
import json
from pathlib import Path
import tempfile
from datetime import datetime

from devdocai.enhancement.quality_tracker import (
    QualityMetrics,
    ImprovementReport,
    QualityTracker
)


class TestQualityMetrics:
    """Test QualityMetrics dataclass."""
    
    def test_initialization(self):
        """Test quality metrics initialization."""
        metrics = QualityMetrics(
            overall_score=0.75,
            clarity_score=0.8,
            completeness_score=0.7,
            consistency_score=0.85,
            accuracy_score=0.75,
            readability_score=0.7,
            word_count=500,
            sentence_count=25,
            paragraph_count=5,
            average_sentence_length=20.0,
            reading_grade_level=10.5,
            has_introduction=True,
            has_conclusion=True,
            has_table_of_contents=False,
            section_count=4,
            jargon_ratio=0.05,
            passive_voice_ratio=0.1,
            complexity_score=0.6
        )
        
        assert metrics.overall_score == 0.75
        assert metrics.clarity_score == 0.8
        assert metrics.word_count == 500
        assert metrics.has_introduction is True
        assert isinstance(metrics.measured_at, datetime)
        
    def test_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = QualityMetrics(
            overall_score=0.75,
            clarity_score=0.8,
            completeness_score=0.7,
            consistency_score=0.85,
            accuracy_score=0.75,
            readability_score=0.7,
            word_count=500,
            sentence_count=25,
            paragraph_count=5,
            average_sentence_length=20.0,
            reading_grade_level=10.5,
            has_introduction=True,
            has_conclusion=True,
            has_table_of_contents=False,
            section_count=4,
            jargon_ratio=0.05,
            passive_voice_ratio=0.1,
            complexity_score=0.6,
            measurement_id="test123"
        )
        
        data = metrics.to_dict()
        
        assert data["overall_score"] == 0.75
        assert data["clarity_score"] == 0.8
        assert data["word_count"] == 500
        assert data["measurement_id"] == "test123"
        assert "measured_at" in data
        
    def test_calculate_overall_score(self):
        """Test overall score calculation."""
        metrics = QualityMetrics(
            overall_score=0,  # Will be recalculated
            clarity_score=0.8,
            completeness_score=0.6,
            consistency_score=0.9,
            accuracy_score=0.7,
            readability_score=0.8,
            word_count=100,
            sentence_count=10,
            paragraph_count=2,
            average_sentence_length=10.0,
            reading_grade_level=8.0,
            has_introduction=True,
            has_conclusion=True,
            has_table_of_contents=False,
            section_count=3,
            jargon_ratio=0.1,
            passive_voice_ratio=0.2,
            complexity_score=0.5
        )
        
        overall = metrics.calculate_overall_score()
        
        assert 0 <= overall <= 1
        # Weighted average should be around 0.75
        assert 0.7 <= overall <= 0.8


class TestImprovementReport:
    """Test ImprovementReport dataclass."""
    
    @pytest.fixture
    def sample_metrics(self):
        """Create sample metrics for testing."""
        initial = QualityMetrics(
            overall_score=0.6,
            clarity_score=0.5,
            completeness_score=0.6,
            consistency_score=0.7,
            accuracy_score=0.6,
            readability_score=0.5,
            word_count=300,
            sentence_count=20,
            paragraph_count=3,
            average_sentence_length=15.0,
            reading_grade_level=12.0,
            has_introduction=False,
            has_conclusion=False,
            has_table_of_contents=False,
            section_count=2,
            jargon_ratio=0.15,
            passive_voice_ratio=0.25,
            complexity_score=0.7
        )
        
        final = QualityMetrics(
            overall_score=0.85,
            clarity_score=0.9,
            completeness_score=0.85,
            consistency_score=0.9,
            accuracy_score=0.8,
            readability_score=0.8,
            word_count=450,
            sentence_count=25,
            paragraph_count=5,
            average_sentence_length=18.0,
            reading_grade_level=10.0,
            has_introduction=True,
            has_conclusion=True,
            has_table_of_contents=True,
            section_count=5,
            jargon_ratio=0.05,
            passive_voice_ratio=0.1,
            complexity_score=0.5
        )
        
        return initial, final
        
    def test_initialization(self, sample_metrics):
        """Test improvement report initialization."""
        initial, final = sample_metrics
        
        report = ImprovementReport(
            document_id="doc123",
            initial_metrics=initial,
            final_metrics=final,
            improvement_passes=3,
            strategies_applied=["clarity", "completeness", "readability"],
            overall_improvement=0.25,
            clarity_improvement=0.4,
            completeness_improvement=0.25,
            consistency_improvement=0.2,
            accuracy_improvement=0.2,
            readability_improvement=0.3,
            processing_time=10.5,
            total_cost=0.15,
            met_quality_threshold=True,
            significant_improvement=True
        )
        
        assert report.document_id == "doc123"
        assert report.improvement_passes == 3
        assert len(report.strategies_applied) == 3
        assert report.overall_improvement == 0.25
        assert report.met_quality_threshold is True
        
    def test_to_dict(self, sample_metrics):
        """Test converting report to dictionary."""
        initial, final = sample_metrics
        
        report = ImprovementReport(
            document_id="doc123",
            initial_metrics=initial,
            final_metrics=final,
            improvement_passes=3,
            strategies_applied=["clarity"],
            overall_improvement=0.25,
            clarity_improvement=0.4,
            completeness_improvement=0.25,
            consistency_improvement=0.2,
            accuracy_improvement=0.2,
            readability_improvement=0.3,
            processing_time=10.5,
            total_cost=0.15,
            met_quality_threshold=True,
            significant_improvement=True
        )
        
        data = report.to_dict()
        
        assert data["document_id"] == "doc123"
        assert data["improvement_passes"] == 3
        assert data["overall_improvement"] == 0.25
        assert "initial_metrics" in data
        assert "final_metrics" in data
        
    def test_generate_summary(self, sample_metrics):
        """Test generating human-readable summary."""
        initial, final = sample_metrics
        
        report = ImprovementReport(
            document_id="doc123",
            initial_metrics=initial,
            final_metrics=final,
            improvement_passes=3,
            strategies_applied=["clarity", "completeness"],
            overall_improvement=0.25,
            clarity_improvement=0.4,
            completeness_improvement=0.25,
            consistency_improvement=0.2,
            accuracy_improvement=0.2,
            readability_improvement=0.3,
            processing_time=10.5,
            total_cost=0.15,
            met_quality_threshold=True,
            significant_improvement=True
        )
        
        summary = report.generate_summary()
        
        assert "doc123" in summary
        assert "25.0%" in summary  # Overall improvement
        assert "clarity" in summary.lower()
        assert "Success: ✓" in summary


class TestQualityTracker:
    """Test QualityTracker class."""
    
    @pytest.fixture
    def tracker(self):
        """Create quality tracker instance."""
        return QualityTracker()
        
    def test_initialization(self, tracker):
        """Test tracker initialization."""
        assert tracker.metrics_history == {}
        assert tracker.reports == {}
        assert tracker.total_documents_processed == 0
        assert tracker.total_improvement_sum == 0.0
        assert tracker.successful_enhancements == 0
        
    def test_measure_quality(self, tracker):
        """Test measuring quality metrics."""
        content = """# Introduction
        
This is a test document with multiple paragraphs.

## Section 1
This section contains some content.

## Section 2
Another section with more content.

## Conclusion
Final thoughts."""
        
        metrics = tracker.measure_quality(content, "doc1")
        
        assert isinstance(metrics, QualityMetrics)
        assert metrics.word_count > 0
        assert metrics.sentence_count > 0
        assert metrics.has_introduction is True
        assert metrics.has_conclusion is True
        assert metrics.section_count > 0
        assert 0 <= metrics.overall_score <= 1
        
        # Check it was stored in history
        assert "doc1" in tracker.metrics_history
        assert len(tracker.metrics_history["doc1"]) == 1
        
    def test_measure_quality_auto_id(self, tracker):
        """Test measuring quality with auto-generated ID."""
        content = "Simple test content."
        
        metrics = tracker.measure_quality(content)
        
        assert isinstance(metrics, QualityMetrics)
        assert metrics.measurement_id != ""
        
    def test_clarity_score_calculation(self, tracker):
        """Test clarity score calculation."""
        # Short sentences - good clarity
        good_clarity = tracker._calculate_clarity_score("Short. Simple. Clear.", 5.0)
        assert good_clarity > 0.7
        
        # Long sentences - poor clarity
        poor_clarity = tracker._calculate_clarity_score("Very long sentence " * 20, 50.0)
        assert poor_clarity < 0.7
        
    def test_completeness_score_calculation(self, tracker):
        """Test completeness score calculation."""
        # Complete document
        complete = tracker._calculate_completeness_score(
            "Long content " * 100,
            has_intro=True,
            has_conclusion=True,
            section_count=5
        )
        assert complete > 0.7
        
        # Incomplete document
        incomplete = tracker._calculate_completeness_score(
            "Short",
            has_intro=False,
            has_conclusion=False,
            section_count=0
        )
        assert incomplete < 0.7
        
    def test_consistency_score_calculation(self, tracker):
        """Test consistency score calculation."""
        # Consistent formatting
        consistent = tracker._calculate_consistency_score("Using **bold** consistently.")
        assert consistent > 0.8
        
        # Mixed formatting
        inconsistent = tracker._calculate_consistency_score(
            "Using **bold** and __underline__ and API and api and Api."
        )
        assert inconsistent < 0.8
        
    def test_accuracy_score_calculation(self, tracker):
        """Test accuracy score calculation."""
        # Confident claims
        confident = tracker._calculate_accuracy_score("This is definitely true.")
        assert confident > 0.7
        
        # Uncertain claims
        uncertain = tracker._calculate_accuracy_score(
            "This might possibly perhaps maybe could be true."
        )
        assert uncertain < 0.7
        
    def test_readability_score_calculation(self, tracker):
        """Test readability score calculation."""
        # Good readability
        good = tracker._calculate_readability_score(10.0, 18.0)
        assert good > 0.8
        
        # Poor readability (too complex)
        poor = tracker._calculate_readability_score(20.0, 35.0)
        assert poor < 0.7
        
    def test_create_improvement_report(self, tracker):
        """Test creating improvement report."""
        # Add metrics history
        content1 = "Initial content."
        content2 = "Improved content with more details."
        
        tracker.measure_quality(content1, "doc1")
        tracker.measure_quality(content2, "doc1")
        
        report = tracker.create_improvement_report(
            document_id="doc1",
            strategies_applied=["clarity", "completeness"],
            processing_time=5.0,
            total_cost=0.10,
            improvement_passes=2
        )
        
        assert isinstance(report, ImprovementReport)
        assert report.document_id == "doc1"
        assert len(report.strategies_applied) == 2
        assert report.processing_time == 5.0
        assert report.total_cost == 0.10
        
        # Check aggregate statistics updated
        assert tracker.total_documents_processed == 1
        
    def test_create_improvement_report_insufficient_history(self, tracker):
        """Test creating report with insufficient history."""
        report = tracker.create_improvement_report(
            document_id="unknown",
            strategies_applied=["clarity"],
            processing_time=1.0,
            total_cost=0.05,
            improvement_passes=1
        )
        
        assert isinstance(report, ImprovementReport)
        # Should use dummy metrics
        assert report.initial_metrics.overall_score == 0.5
        assert report.final_metrics.overall_score == 0.5
        
    def test_get_average_improvement(self, tracker):
        """Test getting average improvement."""
        # No documents
        assert tracker.get_average_improvement() == 0.0
        
        # Add some improvements
        tracker.total_documents_processed = 3
        tracker.total_improvement_sum = 0.45  # 0.15 average
        
        assert tracker.get_average_improvement() == 0.15
        
    def test_get_success_rate(self, tracker):
        """Test getting success rate."""
        # No documents
        assert tracker.get_success_rate() == 0.0
        
        # Add some successes
        tracker.total_documents_processed = 10
        tracker.successful_enhancements = 8
        
        assert tracker.get_success_rate() == 0.8
        
    def test_get_metrics_history(self, tracker):
        """Test getting metrics history."""
        # Add some metrics
        tracker.measure_quality("Content 1", "doc1")
        tracker.measure_quality("Content 2", "doc1")
        
        history = tracker.get_metrics_history("doc1")
        assert len(history) == 2
        
        # Unknown document
        unknown_history = tracker.get_metrics_history("unknown")
        assert unknown_history == []
        
    def test_get_report(self, tracker):
        """Test getting improvement report."""
        # Create a report
        tracker.measure_quality("Initial", "doc1")
        tracker.measure_quality("Final", "doc1")
        
        report = tracker.create_improvement_report(
            "doc1", ["clarity"], 1.0, 0.05, 1
        )
        
        # Get the report
        retrieved = tracker.get_report("doc1")
        assert retrieved == report
        
        # Unknown document
        assert tracker.get_report("unknown") is None
        
    def test_export_reports(self, tracker):
        """Test exporting reports to file."""
        # Create some reports
        tracker.measure_quality("Content 1", "doc1")
        tracker.measure_quality("Content 2", "doc1")
        tracker.create_improvement_report("doc1", ["clarity"], 1.0, 0.05, 1)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "reports.json"
            tracker.export_reports(output_path)
            
            assert output_path.exists()
            
            # Load and verify
            with open(output_path) as f:
                data = json.load(f)
                
            assert "summary" in data
            assert "reports" in data
            assert "doc1" in data["reports"]
            
    def test_clear_history(self, tracker):
        """Test clearing history."""
        # Add some data
        tracker.measure_quality("Content", "doc1")
        tracker.create_improvement_report("doc1", ["clarity"], 1.0, 0.05, 1)
        
        # Clear specific document
        tracker.clear_history("doc1")
        assert "doc1" not in tracker.metrics_history
        assert "doc1" not in tracker.reports
        
        # Add more data
        tracker.measure_quality("Content", "doc2")
        tracker.total_documents_processed = 5
        
        # Clear all
        tracker.clear_history()
        assert len(tracker.metrics_history) == 0
        assert len(tracker.reports) == 0
        assert tracker.total_documents_processed == 0
        
    def test_jargon_ratio_calculation(self, tracker):
        """Test jargon ratio calculation."""
        # Simple text
        simple = tracker._calculate_jargon_ratio("Simple text with short words.")
        assert simple < 0.1
        
        # Complex text
        complex_text = "Utilization optimization standardization " * 5
        complex_ratio = tracker._calculate_jargon_ratio(complex_text)
        assert complex_ratio > 0.1
        
    def test_passive_voice_ratio(self, tracker):
        """Test passive voice ratio calculation."""
        # Active voice
        active = tracker._calculate_passive_voice_ratio("I wrote the code.")
        assert active < 0.5
        
        # Passive voice
        passive = tracker._calculate_passive_voice_ratio(
            "The code was written. The test was executed."
        )
        assert passive > 0
        
    def test_complexity_score(self, tracker):
        """Test complexity score calculation."""
        # Simple text
        simple = tracker._calculate_complexity_score("Simple. Clear. Easy.")
        assert 0 <= simple <= 1
        
        # Complex text
        complex_text = "Furthermore, notwithstanding the aforementioned considerations..."
        complex_score = tracker._calculate_complexity_score(complex_text)
        assert 0 <= complex_score <= 1