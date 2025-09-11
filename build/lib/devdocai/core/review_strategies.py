"""
M007 Review Engine - Strategy Pattern Implementation
DevDocAI v3.0.0

Extracted strategy components for cleaner separation of concerns.
Implements review strategies and quality calculation logic.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List

from .review_types import ReviewResult, ReviewType, SeverityLevel

logger = logging.getLogger(__name__)


class ReviewStrategy(ABC):
    """Abstract base class for review strategies."""

    @abstractmethod
    def calculate_quality_score(self, reviews: Dict[ReviewType, ReviewResult]) -> "QualityScore":
        """Calculate quality score based on review results."""
        pass

    @abstractmethod
    def evaluate_quality_gate(self, score: float, threshold: float) -> tuple[str, List[str]]:
        """Evaluate if quality gate is met."""
        pass


@dataclass
class QualityScore:
    """Quality score with component breakdown."""

    efficiency_score: float = 0.0
    completeness_score: float = 0.0
    readability_score: float = 0.0
    overall_score: float = 0.0

    # Formula weights
    efficiency_weight: float = 0.35
    completeness_weight: float = 0.35
    readability_weight: float = 0.30

    def calculate_overall(self) -> float:
        """Calculate overall score using formula Q = 0.35×E + 0.35×C + 0.30×R."""
        self.overall_score = (
            self.efficiency_weight * self.efficiency_score
            + self.completeness_weight * self.completeness_score
            + self.readability_weight * self.readability_score
        )
        return self.overall_score


class StandardReviewStrategy(ReviewStrategy):
    """Standard review strategy implementation."""

    def calculate_quality_score(self, reviews: Dict[ReviewType, ReviewResult]) -> QualityScore:
        """Calculate quality score from review results."""
        quality = QualityScore()

        # Efficiency: Based on performance and design reviews
        efficiency_scores = []
        if ReviewType.PERFORMANCE in reviews:
            efficiency_scores.append(reviews[ReviewType.PERFORMANCE].score)
        if ReviewType.DESIGN in reviews:
            efficiency_scores.append(reviews[ReviewType.DESIGN].score)

        quality.efficiency_score = (
            sum(efficiency_scores) / len(efficiency_scores) if efficiency_scores else 0.5
        )

        # Completeness: Based on requirements, coverage, and compliance
        completeness_scores = []
        if ReviewType.REQUIREMENTS in reviews:
            completeness_scores.append(reviews[ReviewType.REQUIREMENTS].score)
        if ReviewType.TEST_COVERAGE in reviews:
            completeness_scores.append(reviews[ReviewType.TEST_COVERAGE].score)
        if ReviewType.COMPLIANCE in reviews:
            completeness_scores.append(reviews[ReviewType.COMPLIANCE].score)

        quality.completeness_score = (
            sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0.5
        )

        # Readability: Based on usability and consistency
        readability_scores = []
        if ReviewType.USABILITY in reviews:
            readability_scores.append(reviews[ReviewType.USABILITY].score)
        if ReviewType.CONSISTENCY in reviews:
            readability_scores.append(reviews[ReviewType.CONSISTENCY].score)

        quality.readability_score = (
            sum(readability_scores) / len(readability_scores) if readability_scores else 0.5
        )

        quality.calculate_overall()
        return quality

    def evaluate_quality_gate(self, score: float, threshold: float) -> tuple[str, List[str]]:
        """Evaluate if quality gate is met."""
        status = "PASS" if score >= threshold else "FAIL"
        issues = []

        if status == "FAIL":
            issues.append(f"Quality score {score:.2f} below threshold {threshold}")

        return status, issues


class IssueCollector:
    """Utility class for collecting and categorizing issues."""

    @staticmethod
    def collect_all_issues(reviews: Dict[ReviewType, ReviewResult]) -> List[Any]:
        """Collect all issues from all reviews."""
        all_issues = []

        for review_type, result in reviews.items():
            for issue in result.issues:
                # Add severity if not present
                if not hasattr(issue, "severity"):
                    severity = IssueCollector._determine_severity(review_type)

                    if isinstance(issue, dict):
                        issue["severity"] = severity
                    else:
                        issue.severity = severity

                all_issues.append(issue)

        return all_issues

    @staticmethod
    def _determine_severity(review_type: ReviewType) -> SeverityLevel:
        """Determine severity based on review type."""
        severity_mapping = {
            ReviewType.SECURITY: SeverityLevel.HIGH,
            ReviewType.REQUIREMENTS: SeverityLevel.MEDIUM,
            ReviewType.COMPLIANCE: SeverityLevel.MEDIUM,
            ReviewType.PERFORMANCE: SeverityLevel.MEDIUM,
            ReviewType.DESIGN: SeverityLevel.MEDIUM,
            ReviewType.TEST_COVERAGE: SeverityLevel.LOW,
            ReviewType.USABILITY: SeverityLevel.LOW,
            ReviewType.CONSISTENCY: SeverityLevel.LOW,
        }
        return severity_mapping.get(review_type, SeverityLevel.LOW)


class ReviewStrategyFactory:
    """Factory for creating review strategies."""

    _strategies = {
        "standard": StandardReviewStrategy,
    }

    @classmethod
    def create(cls, strategy_type: str = "standard") -> ReviewStrategy:
        """Create a review strategy instance."""
        strategy_class = cls._strategies.get(strategy_type, StandardReviewStrategy)
        return strategy_class()

    @classmethod
    def register_strategy(cls, name: str, strategy_class: type):
        """Register a new review strategy."""
        if not issubclass(strategy_class, ReviewStrategy):
            raise ValueError(f"{strategy_class} must be a subclass of ReviewStrategy")
        cls._strategies[name] = strategy_class
