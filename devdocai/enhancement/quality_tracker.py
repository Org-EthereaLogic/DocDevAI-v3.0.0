"""
Quality tracking system for document enhancements.

Tracks and measures quality improvements across enhancement iterations.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import statistics
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class QualityMetrics:
    """Quality metrics for a document."""
    
    # Core quality scores
    overall_score: float
    clarity_score: float
    completeness_score: float
    consistency_score: float
    accuracy_score: float
    readability_score: float
    
    # Detailed metrics
    word_count: int
    sentence_count: int
    paragraph_count: int
    average_sentence_length: float
    reading_grade_level: float
    
    # Structure metrics
    has_introduction: bool
    has_conclusion: bool
    has_table_of_contents: bool
    section_count: int
    
    # Quality indicators
    jargon_ratio: float
    passive_voice_ratio: float
    complexity_score: float
    
    # Metadata
    measured_at: datetime = field(default_factory=datetime.now)
    measurement_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "overall_score": self.overall_score,
            "clarity_score": self.clarity_score,
            "completeness_score": self.completeness_score,
            "consistency_score": self.consistency_score,
            "accuracy_score": self.accuracy_score,
            "readability_score": self.readability_score,
            "word_count": self.word_count,
            "sentence_count": self.sentence_count,
            "paragraph_count": self.paragraph_count,
            "average_sentence_length": self.average_sentence_length,
            "reading_grade_level": self.reading_grade_level,
            "has_introduction": self.has_introduction,
            "has_conclusion": self.has_conclusion,
            "has_table_of_contents": self.has_table_of_contents,
            "section_count": self.section_count,
            "jargon_ratio": self.jargon_ratio,
            "passive_voice_ratio": self.passive_voice_ratio,
            "complexity_score": self.complexity_score,
            "measured_at": self.measured_at.isoformat(),
            "measurement_id": self.measurement_id
        }
    
    def calculate_overall_score(self) -> float:
        """Calculate weighted overall score."""
        weights = {
            "clarity": 0.25,
            "completeness": 0.20,
            "consistency": 0.15,
            "accuracy": 0.20,
            "readability": 0.20
        }
        
        total = (
            self.clarity_score * weights["clarity"] +
            self.completeness_score * weights["completeness"] +
            self.consistency_score * weights["consistency"] +
            self.accuracy_score * weights["accuracy"] +
            self.readability_score * weights["readability"]
        )
        
        return min(max(total, 0.0), 1.0)


@dataclass
class ImprovementReport:
    """Report on quality improvements."""
    
    document_id: str
    initial_metrics: QualityMetrics
    final_metrics: QualityMetrics
    improvement_passes: int
    strategies_applied: List[str]
    
    # Improvement deltas
    overall_improvement: float
    clarity_improvement: float
    completeness_improvement: float
    consistency_improvement: float
    accuracy_improvement: float
    readability_improvement: float
    
    # Performance metrics
    processing_time: float
    total_cost: float
    
    # Success indicators
    met_quality_threshold: bool
    significant_improvement: bool
    
    # Detailed improvements
    improvements_by_pass: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "document_id": self.document_id,
            "initial_metrics": self.initial_metrics.to_dict(),
            "final_metrics": self.final_metrics.to_dict(),
            "improvement_passes": self.improvement_passes,
            "strategies_applied": self.strategies_applied,
            "overall_improvement": self.overall_improvement,
            "clarity_improvement": self.clarity_improvement,
            "completeness_improvement": self.completeness_improvement,
            "consistency_improvement": self.consistency_improvement,
            "accuracy_improvement": self.accuracy_improvement,
            "readability_improvement": self.readability_improvement,
            "processing_time": self.processing_time,
            "total_cost": self.total_cost,
            "met_quality_threshold": self.met_quality_threshold,
            "significant_improvement": self.significant_improvement,
            "improvements_by_pass": self.improvements_by_pass
        }
    
    def generate_summary(self) -> str:
        """Generate human-readable summary."""
        summary = f"Enhancement Report for Document {self.document_id}\n"
        summary += "=" * 50 + "\n\n"
        
        summary += f"Overall Improvement: {self.overall_improvement:.1%}\n"
        summary += f"Passes: {self.improvement_passes}\n"
        summary += f"Strategies: {', '.join(self.strategies_applied)}\n"
        summary += f"Processing Time: {self.processing_time:.2f}s\n"
        summary += f"Cost: ${self.total_cost:.2f}\n\n"
        
        summary += "Quality Improvements:\n"
        summary += f"  Clarity: {self.clarity_improvement:+.1%}\n"
        summary += f"  Completeness: {self.completeness_improvement:+.1%}\n"
        summary += f"  Consistency: {self.consistency_improvement:+.1%}\n"
        summary += f"  Accuracy: {self.accuracy_improvement:+.1%}\n"
        summary += f"  Readability: {self.readability_improvement:+.1%}\n\n"
        
        summary += f"Success: {'✓' if self.met_quality_threshold else '✗'} "
        summary += f"({'Significant' if self.significant_improvement else 'Minor'} improvement)\n"
        
        return summary


class QualityTracker:
    """
    Tracks quality metrics and improvements across enhancement iterations.
    """
    
    def __init__(self):
        """Initialize quality tracker."""
        self.metrics_history: Dict[str, List[QualityMetrics]] = {}
        self.reports: Dict[str, ImprovementReport] = {}
        self.current_document_id: Optional[str] = None
        
        # Aggregate statistics
        self.total_documents_processed = 0
        self.total_improvement_sum = 0.0
        self.successful_enhancements = 0
        
        logger.info("Quality Tracker initialized")
    
    def measure_quality(self, content: str, document_id: Optional[str] = None) -> QualityMetrics:
        """
        Measure quality metrics for content.
        
        Args:
            content: Document content to measure
            document_id: Optional document identifier
            
        Returns:
            QualityMetrics object
        """
        import hashlib
        import re
        
        # Generate document ID if not provided
        if not document_id:
            document_id = hashlib.md5(content.encode()).hexdigest()[:8]
        
        # Basic text statistics
        words = content.split()
        word_count = len(words)
        sentences = re.split(r'[.!?]+', content)
        sentence_count = len([s for s in sentences if s.strip()])
        paragraphs = content.split('\n\n')
        paragraph_count = len([p for p in paragraphs if p.strip()])
        
        avg_sentence_length = word_count / max(sentence_count, 1)
        
        # Calculate reading grade level (simplified Flesch-Kincaid)
        try:
            from textstat import flesch_kincaid_grade
            reading_grade = flesch_kincaid_grade(content) if len(content) > 100 else 10
        except ImportError:
            reading_grade = 10.0
        
        # Structure analysis
        has_intro = bool(re.search(r'(?i)(introduction|intro|overview)', content))
        has_conclusion = bool(re.search(r'(?i)(conclusion|summary|final)', content))
        has_toc = bool(re.search(r'(?i)(table of contents|contents|toc)', content))
        sections = re.findall(r'^#+\s+', content, re.MULTILINE)
        section_count = len(sections)
        
        # Quality scoring (simplified)
        clarity_score = self._calculate_clarity_score(content, avg_sentence_length)
        completeness_score = self._calculate_completeness_score(
            content, has_intro, has_conclusion, section_count
        )
        consistency_score = self._calculate_consistency_score(content)
        accuracy_score = self._calculate_accuracy_score(content)
        readability_score = self._calculate_readability_score(reading_grade, avg_sentence_length)
        
        # Additional metrics
        jargon_ratio = self._calculate_jargon_ratio(content)
        passive_voice_ratio = self._calculate_passive_voice_ratio(content)
        complexity_score = self._calculate_complexity_score(content)
        
        metrics = QualityMetrics(
            overall_score=0,  # Will be calculated
            clarity_score=clarity_score,
            completeness_score=completeness_score,
            consistency_score=consistency_score,
            accuracy_score=accuracy_score,
            readability_score=readability_score,
            word_count=word_count,
            sentence_count=sentence_count,
            paragraph_count=paragraph_count,
            average_sentence_length=avg_sentence_length,
            reading_grade_level=reading_grade,
            has_introduction=has_intro,
            has_conclusion=has_conclusion,
            has_table_of_contents=has_toc,
            section_count=section_count,
            jargon_ratio=jargon_ratio,
            passive_voice_ratio=passive_voice_ratio,
            complexity_score=complexity_score,
            measurement_id=document_id
        )
        
        # Calculate overall score
        metrics.overall_score = metrics.calculate_overall_score()
        
        # Store in history
        if document_id not in self.metrics_history:
            self.metrics_history[document_id] = []
        self.metrics_history[document_id].append(metrics)
        
        return metrics
    
    def _calculate_clarity_score(self, content: str, avg_sentence_length: float) -> float:
        """Calculate clarity score based on sentence structure."""
        score = 1.0
        
        # Penalize very long sentences
        if avg_sentence_length > 25:
            score -= 0.2
        elif avg_sentence_length > 20:
            score -= 0.1
        
        # Check for complex sentence structures
        complex_patterns = [
            r'\b(however|nevertheless|furthermore|moreover)\b',
            r';',  # Semicolons indicate complex sentences
            r'\([^)]{50,}\)',  # Long parenthetical expressions
        ]
        
        import re
        complexity_count = sum(
            len(re.findall(pattern, content, re.IGNORECASE))
            for pattern in complex_patterns
        )
        
        if complexity_count > len(content.split('.')) * 0.3:
            score -= 0.15
        
        return max(score, 0.3)
    
    def _calculate_completeness_score(
        self,
        content: str,
        has_intro: bool,
        has_conclusion: bool,
        section_count: int
    ) -> float:
        """Calculate completeness score."""
        score = 0.5  # Base score
        
        if has_intro:
            score += 0.15
        if has_conclusion:
            score += 0.15
        
        # Check for appropriate section count
        word_count = len(content.split())
        expected_sections = word_count // 500  # Roughly one section per 500 words
        
        if section_count >= expected_sections:
            score += 0.2
        elif section_count >= expected_sections * 0.5:
            score += 0.1
        
        # Check for examples
        if 'example' in content.lower() or 'e.g.' in content:
            score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_consistency_score(self, content: str) -> float:
        """Calculate consistency score."""
        import re
        score = 1.0
        
        # Check for inconsistent capitalization of common terms
        terms = ['API', 'URL', 'HTTP', 'JSON', 'XML']
        for term in terms:
            variations = [
                len(re.findall(rf'\b{term}\b', content)),
                len(re.findall(rf'\b{term.lower()}\b', content)),
                len(re.findall(rf'\b{term.title()}\b', content))
            ]
            if sum(v > 0 for v in variations) > 1:
                score -= 0.05
        
        # Check for mixed formatting styles
        if '**' in content and '__' in content:
            score -= 0.1
        if '*' in content and '_' in content:
            score -= 0.05
        
        return max(score, 0.4)
    
    def _calculate_accuracy_score(self, content: str) -> float:
        """Calculate accuracy score (simplified)."""
        import re
        score = 0.8  # Start with good score, deduct for issues
        
        # Check for hedge words indicating uncertainty
        hedge_words = ['might', 'possibly', 'perhaps', 'maybe', 'could be']
        hedge_count = sum(content.lower().count(word) for word in hedge_words)
        
        if hedge_count > 5:
            score -= 0.15
        elif hedge_count > 2:
            score -= 0.05
        
        # Check for missing citations on claims
        claim_patterns = [
            r'studies show',
            r'research indicates',
            r'experts say',
            r'according to'
        ]
        
        claims_without_citations = 0
        for pattern in claim_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                # Check if followed by citation within 50 characters
                idx = content.find(match)
                if idx != -1:
                    following_text = content[idx:idx+50]
                    if not re.search(r'\[[\d,\s]+\]|\([^)]+\d{4}\)', following_text):
                        claims_without_citations += 1
        
        if claims_without_citations > 0:
            score -= min(claims_without_citations * 0.05, 0.2)
        
        return max(score, 0.3)
    
    def _calculate_readability_score(self, grade_level: float, avg_sentence_length: float) -> float:
        """Calculate readability score."""
        score = 1.0
        
        # Ideal grade level is around 8-12
        if 8 <= grade_level <= 12:
            score = 1.0
        elif grade_level < 6:
            score = 0.7  # Too simple
        elif grade_level > 15:
            score = 0.6  # Too complex
        else:
            score = 0.85
        
        # Adjust for sentence length
        if 15 <= avg_sentence_length <= 20:
            score *= 1.0
        elif avg_sentence_length < 10:
            score *= 0.9  # Too choppy
        elif avg_sentence_length > 25:
            score *= 0.85  # Too long
        else:
            score *= 0.95
        
        return score
    
    def _calculate_jargon_ratio(self, content: str) -> float:
        """Calculate ratio of jargon/complex terms."""
        # Simplified jargon detection
        jargon_patterns = [
            r'\b\w{15,}\b',  # Very long words
            r'\b\w+ization\b',  # -ization words
            r'\b\w+ological\b',  # -ological words
        ]
        
        import re
        word_count = len(content.split())
        jargon_count = sum(
            len(re.findall(pattern, content, re.IGNORECASE))
            for pattern in jargon_patterns
        )
        
        return jargon_count / max(word_count, 1)
    
    def _calculate_passive_voice_ratio(self, content: str) -> float:
        """Calculate ratio of passive voice usage."""
        import re
        
        # Simplified passive voice detection
        passive_patterns = [
            r'\b(was|were|been|being|is|are|am)\s+\w+ed\b',
            r'\b(was|were|been|being|is|are|am)\s+\w+en\b',
        ]
        
        sentence_count = len(re.split(r'[.!?]+', content))
        passive_count = sum(
            len(re.findall(pattern, content, re.IGNORECASE))
            for pattern in passive_patterns
        )
        
        return passive_count / max(sentence_count, 1)
    
    def _calculate_complexity_score(self, content: str) -> float:
        """Calculate overall complexity score."""
        try:
            from textstat import flesch_reading_ease
            reading_ease = flesch_reading_ease(content) if len(content) > 100 else 50
            # Convert to 0-1 scale (0=easy, 1=complex)
            complexity = 1.0 - (reading_ease / 100.0)
            return max(min(complexity, 1.0), 0.0)
        except ImportError:
            return 0.5  # Default medium complexity
    
    def create_improvement_report(
        self,
        document_id: str,
        strategies_applied: List[str],
        processing_time: float,
        total_cost: float,
        improvement_passes: int
    ) -> ImprovementReport:
        """
        Create an improvement report for a document.
        
        Args:
            document_id: Document identifier
            strategies_applied: List of applied strategies
            processing_time: Total processing time
            total_cost: Total cost of enhancements
            improvement_passes: Number of enhancement passes
            
        Returns:
            ImprovementReport object
        """
        if document_id not in self.metrics_history or len(self.metrics_history[document_id]) < 2:
            logger.warning(f"Insufficient metrics history for document {document_id}")
            # Create dummy report
            dummy_metrics = QualityMetrics(
                overall_score=0.5,
                clarity_score=0.5,
                completeness_score=0.5,
                consistency_score=0.5,
                accuracy_score=0.5,
                readability_score=0.5,
                word_count=0,
                sentence_count=0,
                paragraph_count=0,
                average_sentence_length=0,
                reading_grade_level=10,
                has_introduction=False,
                has_conclusion=False,
                has_table_of_contents=False,
                section_count=0,
                jargon_ratio=0,
                passive_voice_ratio=0,
                complexity_score=0.5
            )
            initial_metrics = dummy_metrics
            final_metrics = dummy_metrics
        else:
            initial_metrics = self.metrics_history[document_id][0]
            final_metrics = self.metrics_history[document_id][-1]
        
        # Calculate improvements
        overall_improvement = final_metrics.overall_score - initial_metrics.overall_score
        clarity_improvement = final_metrics.clarity_score - initial_metrics.clarity_score
        completeness_improvement = final_metrics.completeness_score - initial_metrics.completeness_score
        consistency_improvement = final_metrics.consistency_score - initial_metrics.consistency_score
        accuracy_improvement = final_metrics.accuracy_score - initial_metrics.accuracy_score
        readability_improvement = final_metrics.readability_score - initial_metrics.readability_score
        
        # Determine success
        met_quality_threshold = final_metrics.overall_score >= 0.8
        significant_improvement = overall_improvement >= 0.05
        
        # Track improvements by pass
        improvements_by_pass = []
        for i in range(1, min(len(self.metrics_history[document_id]), improvement_passes + 1)):
            if i < len(self.metrics_history[document_id]):
                prev = self.metrics_history[document_id][i-1]
                curr = self.metrics_history[document_id][i]
                improvements_by_pass.append({
                    "pass": i,
                    "overall_delta": curr.overall_score - prev.overall_score,
                    "clarity_delta": curr.clarity_score - prev.clarity_score,
                    "completeness_delta": curr.completeness_score - prev.completeness_score
                })
        
        report = ImprovementReport(
            document_id=document_id,
            initial_metrics=initial_metrics,
            final_metrics=final_metrics,
            improvement_passes=improvement_passes,
            strategies_applied=strategies_applied,
            overall_improvement=overall_improvement,
            clarity_improvement=clarity_improvement,
            completeness_improvement=completeness_improvement,
            consistency_improvement=consistency_improvement,
            accuracy_improvement=accuracy_improvement,
            readability_improvement=readability_improvement,
            processing_time=processing_time,
            total_cost=total_cost,
            met_quality_threshold=met_quality_threshold,
            significant_improvement=significant_improvement,
            improvements_by_pass=improvements_by_pass
        )
        
        # Store report
        self.reports[document_id] = report
        
        # Update aggregate statistics
        self.total_documents_processed += 1
        self.total_improvement_sum += overall_improvement
        if significant_improvement:
            self.successful_enhancements += 1
        
        return report
    
    def get_average_improvement(self) -> float:
        """Get average improvement across all documents."""
        if self.total_documents_processed == 0:
            return 0.0
        return self.total_improvement_sum / self.total_documents_processed
    
    def get_success_rate(self) -> float:
        """Get success rate of enhancements."""
        if self.total_documents_processed == 0:
            return 0.0
        return self.successful_enhancements / self.total_documents_processed
    
    def get_metrics_history(self, document_id: str) -> List[QualityMetrics]:
        """Get metrics history for a document."""
        return self.metrics_history.get(document_id, [])
    
    def get_report(self, document_id: str) -> Optional[ImprovementReport]:
        """Get improvement report for a document."""
        return self.reports.get(document_id)
    
    def export_reports(self, output_path: Path) -> None:
        """Export all reports to JSON file."""
        data = {
            "summary": {
                "total_documents": self.total_documents_processed,
                "average_improvement": self.get_average_improvement(),
                "success_rate": self.get_success_rate()
            },
            "reports": {
                doc_id: report.to_dict()
                for doc_id, report in self.reports.items()
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Exported {len(self.reports)} reports to {output_path}")
    
    def clear_history(self, document_id: Optional[str] = None) -> None:
        """Clear metrics history."""
        if document_id:
            if document_id in self.metrics_history:
                del self.metrics_history[document_id]
            if document_id in self.reports:
                del self.reports[document_id]
        else:
            self.metrics_history.clear()
            self.reports.clear()
            self.total_documents_processed = 0
            self.total_improvement_sum = 0.0
            self.successful_enhancements = 0