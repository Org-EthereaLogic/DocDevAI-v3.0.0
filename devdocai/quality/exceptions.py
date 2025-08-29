"""
Custom exceptions for M005 Quality Engine.

This module defines specific exception types for quality analysis operations.
"""


class QualityEngineError(Exception):
    """Base exception for all quality engine errors."""
    pass


class QualityGateFailure(QualityEngineError):
    """Raised when document fails to meet quality gate threshold."""
    
    def __init__(self, score: float, threshold: float, dimensions: dict = None):
        self.score = score
        self.threshold = threshold
        self.dimensions = dimensions or {}
        super().__init__(
            f"Quality gate failed: score {score:.1f}% below threshold {threshold:.1f}%"
        )


class DimensionAnalysisError(QualityEngineError):
    """Raised when quality dimension analysis fails."""
    
    def __init__(self, dimension: str, reason: str):
        self.dimension = dimension
        self.reason = reason
        super().__init__(f"Failed to analyze {dimension}: {reason}")


class ValidationError(QualityEngineError):
    """Raised when document validation fails."""
    
    def __init__(self, validator: str, errors: list):
        self.validator = validator
        self.errors = errors
        super().__init__(f"Validation failed in {validator}: {', '.join(errors)}")


class IntegrationError(QualityEngineError):
    """Raised when module integration fails."""
    
    def __init__(self, module: str, reason: str):
        self.module = module
        self.reason = reason
        super().__init__(f"Integration with {module} failed: {reason}")


class ScoringError(QualityEngineError):
    """Raised when scoring calculation fails."""
    
    def __init__(self, metric: str, reason: str):
        self.metric = metric
        self.reason = reason
        super().__init__(f"Scoring failed for {metric}: {reason}")


class ConfigurationError(QualityEngineError):
    """Raised when quality engine configuration is invalid."""
    
    def __init__(self, parameter: str, value: any, reason: str):
        self.parameter = parameter
        self.value = value
        self.reason = reason
        super().__init__(f"Invalid configuration {parameter}={value}: {reason}")