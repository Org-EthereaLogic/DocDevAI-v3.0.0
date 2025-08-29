"""
Base dimension framework for M005 Quality Engine.

Provides abstract base classes and common functionality for all quality dimensions.
"""

import re
import time
import hashlib
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Set, Tuple
from functools import lru_cache
from dataclasses import dataclass

from .models import DimensionScore, QualityIssue, SeverityLevel, QualityDimension
from .exceptions import DimensionAnalysisError


@dataclass
class AnalysisContext:
    """Context for dimension analysis."""
    content: str
    content_hash: str
    document_type: str
    metadata: Dict[str, Any]
    cache_enabled: bool = True
    security_enabled: bool = False
    performance_mode: bool = False


class BaseDimensionAnalyzer(ABC):
    """Abstract base class for all dimension analyzers."""
    
    def __init__(self, name: str, dimension: QualityDimension):
        """Initialize base dimension analyzer."""
        self.name = name
        self.dimension = dimension
        self._compiled_patterns: Dict[str, re.Pattern] = {}
        self._cache: Dict[str, Any] = {}
        self._metrics: Dict[str, float] = {}
        
    @abstractmethod
    def analyze(self, context: AnalysisContext) -> DimensionScore:
        """Analyze document for this dimension."""
        pass
    
    @abstractmethod
    def get_check_functions(self) -> Dict[str, callable]:
        """Return dictionary of check functions for this dimension."""
        pass
    
    def _get_cached_result(self, key: str) -> Optional[Any]:
        """Get cached result if available."""
        if key in self._cache:
            return self._cache[key]
        return None
    
    def _cache_result(self, key: str, value: Any) -> None:
        """Cache analysis result."""
        self._cache[key] = value
    
    def _compile_pattern(self, pattern: str, flags: int = 0) -> re.Pattern:
        """Compile and cache regex pattern."""
        cache_key = f"{pattern}:{flags}"
        if cache_key not in self._compiled_patterns:
            self._compiled_patterns[cache_key] = re.compile(pattern, flags)
        return self._compiled_patterns[cache_key]
    
    def _measure_time(self, operation: str) -> callable:
        """Decorator to measure operation time."""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start = time.perf_counter()
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                self._metrics[f"{operation}_time"] = elapsed
                return result
            return wrapper
        return decorator
    
    def _create_issue(
        self,
        message: str,
        severity: SeverityLevel,
        line: Optional[int] = None,
        column: Optional[int] = None,
        suggestion: Optional[str] = None
    ) -> QualityIssue:
        """Create a quality issue."""
        return QualityIssue(
            dimension=self.dimension,
            severity=severity,
            message=message,
            line=line,
            column=column,
            suggestion=suggestion
        )
    
    def _calculate_score(
        self,
        checks_passed: int,
        total_checks: int,
        penalties: float = 0
    ) -> float:
        """Calculate dimension score."""
        if total_checks == 0:
            return 1.0
        
        base_score = checks_passed / total_checks
        final_score = max(0, min(1.0, base_score - penalties))
        return round(final_score, 3)
    
    def get_metrics(self) -> Dict[str, float]:
        """Get performance metrics."""
        return self._metrics.copy()
    
    def clear_cache(self) -> None:
        """Clear internal cache."""
        self._cache.clear()
        
    def validate_input(self, context: AnalysisContext) -> None:
        """Validate input context."""
        if not context.content:
            raise DimensionAnalysisError(f"{self.name}: Empty content")
        
        if context.security_enabled:
            # Additional security validations
            max_size = 50 * 1024 * 1024  # 50MB
            if len(context.content.encode('utf-8')) > max_size:
                raise DimensionAnalysisError(f"{self.name}: Content too large")


class PatternBasedAnalyzer(BaseDimensionAnalyzer):
    """Base class for pattern-based analyzers."""
    
    def __init__(self, name: str, dimension: QualityDimension):
        """Initialize pattern-based analyzer."""
        super().__init__(name, dimension)
        self._patterns = self._initialize_patterns()
    
    @abstractmethod
    def _initialize_patterns(self) -> Dict[str, str]:
        """Initialize regex patterns for analysis."""
        pass
    
    def find_matches(self, text: str, pattern_name: str) -> List[re.Match]:
        """Find all matches for a named pattern."""
        if pattern_name not in self._patterns:
            raise ValueError(f"Unknown pattern: {pattern_name}")
        
        pattern = self._compile_pattern(self._patterns[pattern_name])
        return list(pattern.finditer(text))
    
    def count_matches(self, text: str, pattern_name: str) -> int:
        """Count matches for a named pattern."""
        return len(self.find_matches(text, pattern_name))


class StructuralAnalyzer(BaseDimensionAnalyzer):
    """Base class for structural analyzers."""
    
    def __init__(self, name: str, dimension: QualityDimension):
        """Initialize structural analyzer."""
        super().__init__(name, dimension)
        self._structure_cache: Dict[str, Any] = {}
    
    def analyze_structure(self, content: str) -> Dict[str, Any]:
        """Analyze document structure."""
        lines = content.split('\n')
        
        structure = {
            'total_lines': len(lines),
            'blank_lines': sum(1 for line in lines if not line.strip()),
            'sections': self._identify_sections(lines),
            'nesting_levels': self._calculate_nesting(lines),
            'consistency': self._check_consistency(lines)
        }
        
        return structure
    
    @abstractmethod
    def _identify_sections(self, lines: List[str]) -> List[Dict[str, Any]]:
        """Identify document sections."""
        pass
    
    @abstractmethod
    def _calculate_nesting(self, lines: List[str]) -> Dict[str, int]:
        """Calculate nesting levels."""
        pass
    
    @abstractmethod
    def _check_consistency(self, lines: List[str]) -> float:
        """Check structural consistency."""
        pass


class MetricsBasedAnalyzer(BaseDimensionAnalyzer):
    """Base class for metrics-based analyzers."""
    
    def __init__(self, name: str, dimension: QualityDimension):
        """Initialize metrics-based analyzer."""
        super().__init__(name, dimension)
        self._thresholds = self._initialize_thresholds()
    
    @abstractmethod
    def _initialize_thresholds(self) -> Dict[str, Tuple[float, float]]:
        """Initialize metric thresholds (min, max)."""
        pass
    
    def calculate_metrics(self, content: str) -> Dict[str, float]:
        """Calculate all metrics for content."""
        metrics = {}
        
        # Common metrics
        metrics['word_count'] = len(content.split())
        metrics['char_count'] = len(content)
        metrics['line_count'] = len(content.split('\n'))
        metrics['avg_line_length'] = (
            metrics['char_count'] / max(1, metrics['line_count'])
        )
        
        # Subclass-specific metrics
        metrics.update(self._calculate_specific_metrics(content))
        
        return metrics
    
    @abstractmethod
    def _calculate_specific_metrics(self, content: str) -> Dict[str, float]:
        """Calculate dimension-specific metrics."""
        pass
    
    def evaluate_metrics(self, metrics: Dict[str, float]) -> Tuple[float, List[QualityIssue]]:
        """Evaluate metrics against thresholds."""
        issues = []
        violations = 0
        
        for metric_name, value in metrics.items():
            if metric_name in self._thresholds:
                min_val, max_val = self._thresholds[metric_name]
                
                if value < min_val:
                    issues.append(self._create_issue(
                        f"{metric_name} too low: {value:.2f} (min: {min_val})",
                        SeverityLevel.MINOR
                    ))
                    violations += 1
                    
                elif value > max_val:
                    issues.append(self._create_issue(
                        f"{metric_name} too high: {value:.2f} (max: {max_val})",
                        SeverityLevel.MINOR
                    ))
                    violations += 1
        
        score = 1.0 - (violations / max(1, len(self._thresholds)))
        return score, issues