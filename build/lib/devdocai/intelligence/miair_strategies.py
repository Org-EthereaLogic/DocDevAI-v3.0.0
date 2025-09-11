"""
MIAIR Optimization Strategies - Modular Strategy Pattern Implementation
DevDocAI v3.0.0

Provides pluggable optimization strategies for the MIAIR Engine.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class DocumentMetrics:
    """Metrics for document quality assessment."""

    entropy: float
    coherence: float
    quality_score: float
    word_count: int
    unique_words: int
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "entropy": self.entropy,
            "coherence": self.coherence,
            "quality_score": self.quality_score,
            "word_count": self.word_count,
            "unique_words": self.unique_words,
            "timestamp": (
                self.timestamp.isoformat()
                if isinstance(self.timestamp, datetime)
                else str(self.timestamp)
            ),
        }


class OptimizationStrategy(ABC):
    """Abstract base class for optimization strategies."""

    @abstractmethod
    def build_refinement_prompt(self, document: str, metrics: Optional[DocumentMetrics]) -> str:
        """Build refinement prompt for LLM."""
        pass

    @abstractmethod
    def should_continue(
        self, metrics: DocumentMetrics, iteration: int, config: Dict[str, Any]
    ) -> bool:
        """Determine if optimization should continue."""
        pass

    @abstractmethod
    def is_improvement(self, current: DocumentMetrics, refined: DocumentMetrics) -> bool:
        """Check if refinement is an improvement."""
        pass


class EntropyOptimizationStrategy(OptimizationStrategy):
    """Strategy focused on entropy reduction."""

    def build_refinement_prompt(self, document: str, metrics: Optional[DocumentMetrics]) -> str:
        """Build entropy-focused refinement prompt."""
        prompt_parts = [
            "Improve this document by reducing information entropy while maintaining meaning.",
            f"Current entropy: {metrics.entropy:.2f}" if metrics else "",
            "Focus on: clarity, consistency, structured information flow.",
            f"\n{document}\n",
            "Return only the improved content.",
        ]
        return "\n".join(filter(None, prompt_parts))

    def should_continue(
        self, metrics: DocumentMetrics, iteration: int, config: Dict[str, Any]
    ) -> bool:
        """Continue if entropy is above target."""
        max_iterations = config.get("max_iterations", 7)
        target_entropy = config.get("target_entropy", 0.15)
        return iteration < max_iterations and metrics.entropy > target_entropy

    def is_improvement(self, current: DocumentMetrics, refined: DocumentMetrics) -> bool:
        """Improvement if entropy decreases."""
        return refined.entropy < current.entropy


class QualityOptimizationStrategy(OptimizationStrategy):
    """Strategy focused on overall quality improvement."""

    def build_refinement_prompt(self, document: str, metrics: Optional[DocumentMetrics]) -> str:
        """Build quality-focused refinement prompt."""
        prompt_parts = [
            "Enhance this document for professional quality and clarity.",
            f"Current quality: {metrics.quality_score:.1f}%" if metrics else "",
            "Focus on: readability, structure, professional tone, accuracy.",
            f"\n{document}\n",
            "Return only the improved content.",
        ]
        return "\n".join(filter(None, prompt_parts))

    def should_continue(
        self, metrics: DocumentMetrics, iteration: int, config: Dict[str, Any]
    ) -> bool:
        """Continue if quality gate not reached."""
        max_iterations = config.get("max_iterations", 7)
        quality_gate = config.get("quality_gate", 85)
        return iteration < max_iterations and metrics.quality_score < quality_gate

    def is_improvement(self, current: DocumentMetrics, refined: DocumentMetrics) -> bool:
        """Improvement if quality increases."""
        return refined.quality_score > current.quality_score


class PerformanceOptimizationStrategy(OptimizationStrategy):
    """Strategy optimized for speed with acceptable quality."""

    def build_refinement_prompt(self, document: str, metrics: Optional[DocumentMetrics]) -> str:
        """Build minimal refinement prompt for speed."""
        # Truncate document for faster processing
        truncated = document[:2000] if len(document) > 2000 else document
        return f"Quickly improve clarity and structure:\n{truncated}\n\nReturn improved content."

    def should_continue(
        self, metrics: DocumentMetrics, iteration: int, config: Dict[str, Any]
    ) -> bool:
        """Limited iterations for performance."""
        max_iterations = min(3, config.get("max_iterations", 7))
        return iteration < max_iterations

    def is_improvement(self, current: DocumentMetrics, refined: DocumentMetrics) -> bool:
        """Any positive change is improvement."""
        return (
            refined.quality_score > current.quality_score
            or refined.entropy < current.entropy
            or refined.coherence > current.coherence
        )


class AdaptiveStrategy(OptimizationStrategy):
    """Adaptive strategy that switches based on document characteristics."""

    def __init__(self):
        """Initialize with sub-strategies."""
        self.entropy_strategy = EntropyOptimizationStrategy()
        self.quality_strategy = QualityOptimizationStrategy()
        self.performance_strategy = PerformanceOptimizationStrategy()

    def _select_strategy(self, metrics: Optional[DocumentMetrics]) -> OptimizationStrategy:
        """Select appropriate strategy based on metrics."""
        if not metrics:
            return self.quality_strategy

        # High entropy - focus on entropy reduction
        if metrics.entropy > 3.0:
            return self.entropy_strategy

        # Low quality - focus on quality improvement
        if metrics.quality_score < 60:
            return self.quality_strategy

        # Default to performance for good documents
        return self.performance_strategy

    def build_refinement_prompt(self, document: str, metrics: Optional[DocumentMetrics]) -> str:
        """Build prompt using selected strategy."""
        strategy = self._select_strategy(metrics)
        return strategy.build_refinement_prompt(document, metrics)

    def should_continue(
        self, metrics: DocumentMetrics, iteration: int, config: Dict[str, Any]
    ) -> bool:
        """Continue based on selected strategy."""
        strategy = self._select_strategy(metrics)
        return strategy.should_continue(metrics, iteration, config)

    def is_improvement(self, current: DocumentMetrics, refined: DocumentMetrics) -> bool:
        """Check improvement using selected strategy."""
        strategy = self._select_strategy(current)
        return strategy.is_improvement(current, refined)


# Strategy registry for easy access
STRATEGY_REGISTRY = {
    "entropy": EntropyOptimizationStrategy,
    "quality": QualityOptimizationStrategy,
    "performance": PerformanceOptimizationStrategy,
    "adaptive": AdaptiveStrategy,
}


def get_strategy(name: str = "quality") -> OptimizationStrategy:
    """
    Get optimization strategy by name.

    Args:
        name: Strategy name (entropy, quality, performance, adaptive)

    Returns:
        Strategy instance

    Raises:
        ValueError: If strategy name not found
    """
    strategy_class = STRATEGY_REGISTRY.get(name)
    if not strategy_class:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(STRATEGY_REGISTRY.keys())}")
    return strategy_class()
