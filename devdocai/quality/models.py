"""
Data models for M005 Quality Engine.

Defines Pydantic models for quality analysis, scoring, and reporting.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator
from typing_extensions import Self


class QualityDimension(str, Enum):
    """Quality dimension types for analysis."""
    COMPLETENESS = "completeness"
    CLARITY = "clarity"
    STRUCTURE = "structure"
    ACCURACY = "accuracy"
    FORMATTING = "formatting"


class SeverityLevel(str, Enum):
    """Severity levels for quality issues."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class QualityIssue(BaseModel):
    """Represents a quality issue found during analysis."""
    
    dimension: QualityDimension
    severity: SeverityLevel
    description: str
    location: Optional[str] = Field(default=None, description="Location in document")
    suggestion: Optional[str] = Field(default=None, description="Improvement suggestion")
    impact_score: float = Field(ge=0.0, le=10.0, description="Impact on overall quality")
    
    @field_validator('impact_score')
    @classmethod
    def validate_impact(cls, v: float, info) -> float:
        """Validate impact score based on severity."""
        severity = info.data.get('severity')
        if severity == SeverityLevel.CRITICAL and v < 7.0:
            return 10.0  # Critical issues have high impact
        elif severity == SeverityLevel.INFO and v > 3.0:
            return 1.0  # Info issues have low impact
        return v


class DimensionScore(BaseModel):
    """Score for a specific quality dimension."""
    
    dimension: QualityDimension
    score: float = Field(ge=0.0, le=100.0)
    weight: float = Field(ge=0.0, le=1.0, default=0.2)
    issues: List[QualityIssue] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    
    @property
    def weighted_score(self) -> float:
        """Calculate weighted score for this dimension."""
        return self.score * self.weight
    
    @property
    def issue_count(self) -> Dict[str, int]:
        """Count issues by severity."""
        counts = {level.value: 0 for level in SeverityLevel}
        for issue in self.issues:
            counts[issue.severity.value] += 1
        return counts


class QualityConfig(BaseModel):
    """Configuration for quality analysis."""
    
    quality_gate_threshold: float = Field(
        default=85.0, 
        ge=0.0, 
        le=100.0,
        description="Minimum quality score to pass gate"
    )
    dimension_weights: Dict[QualityDimension, float] = Field(
        default_factory=lambda: {
            QualityDimension.COMPLETENESS: 0.25,
            QualityDimension.CLARITY: 0.20,
            QualityDimension.STRUCTURE: 0.20,
            QualityDimension.ACCURACY: 0.25,
            QualityDimension.FORMATTING: 0.10,
        }
    )
    enable_caching: bool = Field(default=True)
    cache_ttl_seconds: int = Field(default=3600, ge=0)
    parallel_analysis: bool = Field(default=True)
    max_workers: int = Field(default=4, ge=1, le=16)
    strict_mode: bool = Field(default=False, description="Fail on any critical issue")
    
    @model_validator(mode='after')
    def validate_weights(self) -> Self:
        """Ensure dimension weights sum to 1.0."""
        total_weight = sum(self.dimension_weights.values())
        if abs(total_weight - 1.0) > 0.001:  # Allow small floating point errors
            # Normalize weights
            for dim in self.dimension_weights:
                self.dimension_weights[dim] /= total_weight
        return self


class QualityReport(BaseModel):
    """Complete quality analysis report."""
    
    document_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    overall_score: float = Field(ge=0.0, le=100.0)
    gate_passed: bool
    dimension_scores: List[DimensionScore]
    total_issues: int = Field(default=0, ge=0)
    critical_issues: int = Field(default=0, ge=0)
    recommendations: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    analysis_time_ms: float = Field(ge=0.0)
    
    @model_validator(mode='before')
    def calculate_totals(cls, values) -> Dict:
        """Calculate total issue counts."""
        if 'dimension_scores' in values and values.get('total_issues') is None:
            total = 0
            critical = 0
            for dim_score in values['dimension_scores']:
                if hasattr(dim_score, 'issues'):
                    issues = dim_score.issues
                elif isinstance(dim_score, dict) and 'issues' in dim_score:
                    issues = dim_score['issues']
                else:
                    continue
                    
                for issue in issues:
                    total += 1
                    if hasattr(issue, 'severity'):
                        severity = issue.severity
                    elif isinstance(issue, dict) and 'severity' in issue:
                        severity = issue['severity']
                    else:
                        continue
                    
                    if severity == SeverityLevel.CRITICAL or severity == 'critical':
                        critical += 1
            
            values['total_issues'] = total
            values['critical_issues'] = critical
        return values
    
    @property
    def summary(self) -> Dict[str, Any]:
        """Generate summary of the report."""
        return {
            "document_id": self.document_id,
            "overall_score": self.overall_score,
            "gate_passed": self.gate_passed,
            "total_issues": self.total_issues,
            "critical_issues": self.critical_issues,
            "dimension_breakdown": {
                ds.dimension.value: {
                    "score": ds.score,
                    "issues": ds.issue_count
                }
                for ds in self.dimension_scores
            }
        }


class ValidationRule(BaseModel):
    """Defines a validation rule for document quality."""
    
    name: str
    description: str
    dimension: QualityDimension
    severity: SeverityLevel = Field(default=SeverityLevel.MEDIUM)
    enabled: bool = Field(default=True)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure rule name is valid."""
        if not v or not v.strip():
            raise ValueError("Rule name cannot be empty")
        return v.strip()


class AnalysisRequest(BaseModel):
    """Request model for quality analysis."""
    
    document_id: str
    content: str
    document_type: Optional[str] = Field(default="markdown")
    config_overrides: Optional[Dict[str, Any]] = Field(default=None)
    skip_dimensions: List[QualityDimension] = Field(default_factory=list)
    include_suggestions: bool = Field(default=True)
    fast_mode: bool = Field(default=False, description="Skip expensive checks")