"""
Scoring algorithms for M005 Quality Engine.

Implements various scoring methods and aggregation strategies.
"""

import math
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from functools import lru_cache

from .models import (
    QualityDimension, DimensionScore, QualityIssue, 
    SeverityLevel, QualityConfig
)
from .exceptions import ScoringError

logger = logging.getLogger(__name__)


@dataclass
class ScoringMetrics:
    """Metrics used for scoring calculations."""
    
    word_count: int = 0
    sentence_count: int = 0
    paragraph_count: int = 0
    code_block_count: int = 0
    heading_count: int = 0
    link_count: int = 0
    image_count: int = 0
    list_count: int = 0
    table_count: int = 0
    
    # Quality indicators
    avg_sentence_length: float = 0.0
    avg_paragraph_length: float = 0.0
    readability_score: float = 0.0
    technical_density: float = 0.0
    structure_depth: int = 0
    
    @property
    def content_diversity(self) -> float:
        """Calculate content diversity score (0-1)."""
        element_types = [
            self.code_block_count > 0,
            self.heading_count > 0,
            self.link_count > 0,
            self.image_count > 0,
            self.list_count > 0,
            self.table_count > 0
        ]
        return sum(element_types) / len(element_types)


class QualityScorer:
    """Handles scoring calculations for quality analysis."""
    
    def __init__(self, config: Optional[QualityConfig] = None):
        """Initialize scorer with configuration."""
        self.config = config or QualityConfig()
        self._cache = {}
    
    def calculate_overall_score(
        self, 
        dimension_scores: List[DimensionScore]
    ) -> float:
        """
        Calculate overall quality score from dimension scores.
        
        Args:
            dimension_scores: List of dimension scores
            
        Returns:
            Overall quality score (0-100)
        """
        try:
            if not dimension_scores:
                raise ScoringError("overall", "No dimension scores provided")
            
            # Apply configured weights
            weighted_sum = 0.0
            total_weight = 0.0
            
            for dim_score in dimension_scores:
                weight = self.config.dimension_weights.get(
                    dim_score.dimension, 
                    0.2  # Default weight
                )
                weighted_sum += dim_score.score * weight
                total_weight += weight
            
            if total_weight == 0:
                raise ScoringError("overall", "Total weight is zero")
            
            overall = weighted_sum / total_weight
            
            # Apply penalties for critical issues
            critical_penalty = self._calculate_critical_penalty(dimension_scores)
            overall = max(0.0, overall - critical_penalty)
            
            return round(overall, 2)
            
        except Exception as e:
            logger.error(f"Failed to calculate overall score: {e}")
            raise ScoringError("overall", str(e))
    
    def score_completeness(
        self, 
        metrics: ScoringMetrics,
        expected_sections: List[str],
        found_sections: List[str]
    ) -> Tuple[float, List[QualityIssue]]:
        """
        Score document completeness.
        
        Args:
            metrics: Document metrics
            expected_sections: Expected section names
            found_sections: Actually found sections
            
        Returns:
            Tuple of (score, issues)
        """
        issues = []
        score = 100.0
        
        # Check for missing sections
        missing_sections = set(expected_sections) - set(found_sections)
        if missing_sections:
            penalty = len(missing_sections) * 10
            score -= penalty
            for section in missing_sections:
                issues.append(QualityIssue(
                    dimension=QualityDimension.COMPLETENESS,
                    severity=SeverityLevel.HIGH,
                    description=f"Missing required section: {section}",
                    suggestion=f"Add a '{section}' section to the document",
                    impact_score=8.0
                ))
        
        # Check content depth
        if metrics.word_count < 100:
            score -= 20
            issues.append(QualityIssue(
                dimension=QualityDimension.COMPLETENESS,
                severity=SeverityLevel.MEDIUM,
                description="Document is too short",
                suggestion="Expand content with more details",
                impact_score=5.0
            ))
        elif metrics.word_count < 300:
            score -= 10
            issues.append(QualityIssue(
                dimension=QualityDimension.COMPLETENESS,
                severity=SeverityLevel.LOW,
                description="Document could be more detailed",
                suggestion="Consider adding more examples or explanations",
                impact_score=3.0
            ))
        
        # Check for code examples if technical doc
        if metrics.technical_density > 0.3 and metrics.code_block_count == 0:
            score -= 15
            issues.append(QualityIssue(
                dimension=QualityDimension.COMPLETENESS,
                severity=SeverityLevel.MEDIUM,
                description="Technical document lacks code examples",
                suggestion="Add code examples to illustrate concepts",
                impact_score=6.0
            ))
        
        return max(0.0, score), issues
    
    def score_clarity(
        self,
        metrics: ScoringMetrics,
        complex_sentences: int,
        jargon_count: int
    ) -> Tuple[float, List[QualityIssue]]:
        """
        Score document clarity and readability.
        
        Args:
            metrics: Document metrics
            complex_sentences: Number of complex sentences
            jargon_count: Count of technical jargon
            
        Returns:
            Tuple of (score, issues)
        """
        issues = []
        score = 100.0
        
        # Readability check
        if metrics.readability_score < 30:
            score -= 25
            issues.append(QualityIssue(
                dimension=QualityDimension.CLARITY,
                severity=SeverityLevel.HIGH,
                description="Poor readability score",
                suggestion="Simplify language and sentence structure",
                impact_score=8.0
            ))
        elif metrics.readability_score < 50:
            score -= 10
            issues.append(QualityIssue(
                dimension=QualityDimension.CLARITY,
                severity=SeverityLevel.LOW,
                description="Readability could be improved",
                suggestion="Consider breaking up complex sentences",
                impact_score=3.0
            ))
        
        # Sentence complexity
        if metrics.avg_sentence_length > 25:
            score -= 15
            issues.append(QualityIssue(
                dimension=QualityDimension.CLARITY,
                severity=SeverityLevel.MEDIUM,
                description="Sentences are too long on average",
                suggestion="Break long sentences into shorter ones",
                impact_score=5.0
            ))
        
        # Technical jargon density
        jargon_density = jargon_count / max(metrics.word_count, 1) * 100
        if jargon_density > 10:
            score -= 20
            issues.append(QualityIssue(
                dimension=QualityDimension.CLARITY,
                severity=SeverityLevel.MEDIUM,
                description="High density of technical jargon",
                suggestion="Define technical terms or provide glossary",
                impact_score=6.0
            ))
        
        # Complex sentence ratio
        if metrics.sentence_count > 0:
            complex_ratio = complex_sentences / metrics.sentence_count
            if complex_ratio > 0.3:
                score -= 10
                issues.append(QualityIssue(
                    dimension=QualityDimension.CLARITY,
                    severity=SeverityLevel.LOW,
                    description="Too many complex sentences",
                    suggestion="Simplify sentence structure where possible",
                    impact_score=4.0
                ))
        
        return max(0.0, score), issues
    
    def score_structure(
        self,
        metrics: ScoringMetrics,
        heading_hierarchy: List[int],
        section_balance: float
    ) -> Tuple[float, List[QualityIssue]]:
        """
        Score document structure and organization.
        
        Args:
            metrics: Document metrics
            heading_hierarchy: List of heading levels
            section_balance: Balance score (0-1)
            
        Returns:
            Tuple of (score, issues)
        """
        issues = []
        score = 100.0
        
        # Check heading presence
        if metrics.heading_count == 0:
            score -= 30
            issues.append(QualityIssue(
                dimension=QualityDimension.STRUCTURE,
                severity=SeverityLevel.HIGH,
                description="No headings found",
                suggestion="Add headings to structure the document",
                impact_score=9.0
            ))
        elif metrics.heading_count < 3:
            score -= 15
            issues.append(QualityIssue(
                dimension=QualityDimension.STRUCTURE,
                severity=SeverityLevel.MEDIUM,
                description="Insufficient headings",
                suggestion="Add more headings to improve structure",
                impact_score=5.0
            ))
        
        # Check heading hierarchy
        if heading_hierarchy:
            # Check for skipped levels
            prev_level = 0
            for level in heading_hierarchy:
                if level > prev_level + 1 and prev_level > 0:
                    score -= 10
                    issues.append(QualityIssue(
                        dimension=QualityDimension.STRUCTURE,
                        severity=SeverityLevel.MEDIUM,
                        description=f"Skipped heading level (H{prev_level} to H{level})",
                        suggestion="Use sequential heading levels",
                        impact_score=4.0
                    ))
                    break
                prev_level = level
        
        # Check section balance
        if section_balance < 0.3:
            score -= 15
            issues.append(QualityIssue(
                dimension=QualityDimension.STRUCTURE,
                severity=SeverityLevel.MEDIUM,
                description="Unbalanced section sizes",
                suggestion="Balance content across sections",
                impact_score=5.0
            ))
        
        # Check content diversity
        if metrics.content_diversity < 0.3:
            score -= 10
            issues.append(QualityIssue(
                dimension=QualityDimension.STRUCTURE,
                severity=SeverityLevel.LOW,
                description="Limited content variety",
                suggestion="Add lists, tables, or diagrams for better structure",
                impact_score=3.0
            ))
        
        return max(0.0, score), issues
    
    def score_accuracy(
        self,
        outdated_refs: int,
        broken_links: int,
        code_errors: int
    ) -> Tuple[float, List[QualityIssue]]:
        """
        Score document accuracy and correctness.
        
        Args:
            outdated_refs: Number of outdated references
            broken_links: Number of broken links
            code_errors: Number of code errors
            
        Returns:
            Tuple of (score, issues)
        """
        issues = []
        score = 100.0
        
        # Check for outdated references
        if outdated_refs > 0:
            penalty = min(outdated_refs * 10, 30)
            score -= penalty
            issues.append(QualityIssue(
                dimension=QualityDimension.ACCURACY,
                severity=SeverityLevel.HIGH,
                description=f"Found {outdated_refs} outdated reference(s)",
                suggestion="Update references to current versions",
                impact_score=7.0
            ))
        
        # Check for broken links
        if broken_links > 0:
            penalty = min(broken_links * 5, 20)
            score -= penalty
            issues.append(QualityIssue(
                dimension=QualityDimension.ACCURACY,
                severity=SeverityLevel.MEDIUM,
                description=f"Found {broken_links} broken link(s)",
                suggestion="Fix or remove broken links",
                impact_score=5.0
            ))
        
        # Check for code errors
        if code_errors > 0:
            penalty = min(code_errors * 15, 40)
            score -= penalty
            issues.append(QualityIssue(
                dimension=QualityDimension.ACCURACY,
                severity=SeverityLevel.CRITICAL,
                description=f"Found {code_errors} code error(s)",
                suggestion="Fix code examples to be syntactically correct",
                impact_score=9.0
            ))
        
        return max(0.0, score), issues
    
    def score_formatting(
        self,
        metrics: ScoringMetrics,
        formatting_errors: List[str]
    ) -> Tuple[float, List[QualityIssue]]:
        """
        Score document formatting and style.
        
        Args:
            metrics: Document metrics
            formatting_errors: List of formatting error descriptions
            
        Returns:
            Tuple of (score, issues)
        """
        issues = []
        score = 100.0
        
        # Check for formatting errors
        if formatting_errors:
            penalty = min(len(formatting_errors) * 5, 30)
            score -= penalty
            for error in formatting_errors[:5]:  # Limit to first 5
                issues.append(QualityIssue(
                    dimension=QualityDimension.FORMATTING,
                    severity=SeverityLevel.LOW,
                    description=error,
                    suggestion="Fix formatting to match style guide",
                    impact_score=2.0
                ))
        
        # Check for consistency indicators
        if metrics.paragraph_count > 0 and metrics.avg_paragraph_length > 500:
            score -= 10
            issues.append(QualityIssue(
                dimension=QualityDimension.FORMATTING,
                severity=SeverityLevel.LOW,
                description="Paragraphs are too long",
                suggestion="Break up long paragraphs for better readability",
                impact_score=3.0
            ))
        
        return max(0.0, score), issues
    
    def _calculate_critical_penalty(
        self, 
        dimension_scores: List[DimensionScore]
    ) -> float:
        """Calculate penalty based on critical issues."""
        critical_count = 0
        high_count = 0
        
        for dim_score in dimension_scores:
            for issue in dim_score.issues:
                if issue.severity == SeverityLevel.CRITICAL:
                    critical_count += 1
                elif issue.severity == SeverityLevel.HIGH:
                    high_count += 1
        
        # Critical issues have severe impact
        penalty = critical_count * 10 + high_count * 3
        return min(penalty, 50)  # Cap at 50% penalty
    
    @lru_cache(maxsize=128)
    def calculate_readability(self, text: str) -> float:
        """
        Calculate Flesch Reading Ease score.
        
        Args:
            text: Text to analyze
            
        Returns:
            Readability score (0-100)
        """
        try:
            sentences = text.count('.') + text.count('!') + text.count('?')
            words = len(text.split())
            syllables = self._count_syllables(text)
            
            if sentences == 0 or words == 0:
                return 0.0
            
            # Flesch Reading Ease formula
            score = 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)
            return max(0.0, min(100.0, score))
            
        except Exception as e:
            logger.warning(f"Failed to calculate readability: {e}")
            return 50.0  # Default middle score
    
    def _count_syllables(self, text: str) -> int:
        """Count syllables in text (simplified)."""
        vowels = "aeiouAEIOU"
        syllable_count = 0
        
        for word in text.split():
            word_syllables = 0
            prev_was_vowel = False
            
            for char in word:
                is_vowel = char in vowels
                if is_vowel and not prev_was_vowel:
                    word_syllables += 1
                prev_was_vowel = is_vowel
            
            # Ensure at least one syllable per word
            syllable_count += max(1, word_syllables)
        
        return syllable_count