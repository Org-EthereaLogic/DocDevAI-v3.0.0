"""
Data models for M007 Review Engine.

Defines Pydantic models for document review, multi-dimensional analysis,
and review reporting with comprehensive validation.
"""

from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator
from typing_extensions import Self


class ReviewDimension(str, Enum):
    """Review dimension types for multi-dimensional analysis."""
    TECHNICAL_ACCURACY = "technical_accuracy"
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    STYLE_FORMATTING = "style_formatting"
    SECURITY_PII = "security_pii"
    CLARITY = "clarity"
    CORRECTNESS = "correctness"
    MAINTAINABILITY = "maintainability"
    PERFORMANCE = "performance"
    ACCESSIBILITY = "accessibility"


class ReviewSeverity(str, Enum):
    """Severity levels for review issues."""
    BLOCKER = "blocker"      # Must fix before approval
    CRITICAL = "critical"    # Serious issues requiring immediate attention
    HIGH = "high"           # Important issues that should be addressed
    MEDIUM = "medium"       # Moderate issues for improvement
    LOW = "low"            # Minor issues or suggestions
    INFO = "info"          # Informational notes


class ReviewStatus(str, Enum):
    """Overall review status."""
    APPROVED = "approved"
    APPROVED_WITH_CONDITIONS = "approved_with_conditions"
    NEEDS_REVISION = "needs_revision"
    REJECTED = "rejected"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"


class ReviewIssue(BaseModel):
    """Represents a single issue found during review."""
    
    dimension: ReviewDimension
    severity: ReviewSeverity
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    location: Optional[str] = Field(
        default=None, 
        description="Location in document (line, section, etc.)"
    )
    suggestion: Optional[str] = Field(
        default=None, 
        description="Suggested improvement or fix"
    )
    code_snippet: Optional[str] = Field(
        default=None,
        description="Relevant code or text snippet"
    )
    impact_score: float = Field(
        ge=0.0, 
        le=10.0, 
        description="Impact on overall document quality"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        default=1.0,
        description="Confidence level of the issue detection"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Additional tags for categorization"
    )
    auto_fixable: bool = Field(
        default=False,
        description="Whether this issue can be automatically fixed"
    )
    
    @field_validator('impact_score')
    @classmethod
    def validate_impact(cls, v: float, info) -> float:
        """Validate impact score based on severity."""
        severity = info.data.get('severity')
        if severity == ReviewSeverity.BLOCKER and v < 8.0:
            return 10.0  # Blocker issues have maximum impact
        elif severity == ReviewSeverity.CRITICAL and v < 7.0:
            return 8.0  # Critical issues have high impact
        elif severity == ReviewSeverity.INFO and v > 3.0:
            return 1.0  # Info issues have minimal impact
        return v
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """Validate and normalize tags."""
        return [tag.lower().strip() for tag in v if tag.strip()]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'dimension': self.dimension.value,
            'severity': self.severity.value,
            'title': self.title,
            'description': self.description,
            'location': self.location,
            'suggestion': self.suggestion,
            'code_snippet': self.code_snippet,
            'impact_score': self.impact_score,
            'confidence': self.confidence,
            'tags': self.tags,
            'auto_fixable': self.auto_fixable
        }


class DimensionResult(BaseModel):
    """Result for a specific review dimension."""
    
    dimension: ReviewDimension
    score: float = Field(ge=0.0, le=100.0)
    weight: float = Field(ge=0.0, le=1.0, default=0.2)
    issues: List[ReviewIssue] = Field(default_factory=list)
    passed_checks: int = Field(ge=0, default=0)
    total_checks: int = Field(ge=0, default=0)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    execution_time_ms: float = Field(ge=0.0, default=0.0)
    
    @property
    def weighted_score(self) -> float:
        """Calculate weighted score for this dimension."""
        return self.score * self.weight
    
    @property
    def pass_rate(self) -> float:
        """Calculate check pass rate."""
        if self.total_checks == 0:
            return 100.0
        return (self.passed_checks / self.total_checks) * 100.0
    
    @property
    def issue_distribution(self) -> Dict[str, int]:
        """Get issue count by severity."""
        distribution = {severity.value: 0 for severity in ReviewSeverity}
        for issue in self.issues:
            distribution[issue.severity.value] += 1
        return distribution
    
    @property
    def has_blockers(self) -> bool:
        """Check if dimension has blocker issues."""
        return any(issue.severity == ReviewSeverity.BLOCKER for issue in self.issues)
    
    @property
    def critical_issue_count(self) -> int:
        """Count critical and blocker issues."""
        return sum(1 for issue in self.issues 
                  if issue.severity in [ReviewSeverity.BLOCKER, ReviewSeverity.CRITICAL])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'dimension': self.dimension.value,
            'score': self.score,
            'weight': self.weight,
            'weighted_score': self.weighted_score,
            'pass_rate': self.pass_rate,
            'passed_checks': self.passed_checks,
            'total_checks': self.total_checks,
            'issues': [issue.to_dict() for issue in self.issues],
            'issue_distribution': self.issue_distribution,
            'has_blockers': self.has_blockers,
            'critical_issue_count': self.critical_issue_count,
            'metrics': self.metrics,
            'execution_time_ms': self.execution_time_ms
        }


class ReviewMetrics(BaseModel):
    """Aggregated metrics from review analysis."""
    
    total_issues: int = Field(ge=0, default=0)
    issues_by_severity: Dict[str, int] = Field(default_factory=dict)
    issues_by_dimension: Dict[str, int] = Field(default_factory=dict)
    auto_fixable_count: int = Field(ge=0, default=0)
    average_confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    total_checks_performed: int = Field(ge=0, default=0)
    checks_passed: int = Field(ge=0, default=0)
    execution_time_ms: float = Field(ge=0.0, default=0.0)
    pii_detected: bool = Field(default=False)
    pii_count: int = Field(ge=0, default=0)
    security_issues: int = Field(ge=0, default=0)
    
    @property
    def overall_pass_rate(self) -> float:
        """Calculate overall pass rate."""
        if self.total_checks_performed == 0:
            return 100.0
        return (self.checks_passed / self.total_checks_performed) * 100.0
    
    @property
    def auto_fix_rate(self) -> float:
        """Calculate auto-fixable issue rate."""
        if self.total_issues == 0:
            return 0.0
        return (self.auto_fixable_count / self.total_issues) * 100.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'total_issues': self.total_issues,
            'issues_by_severity': self.issues_by_severity,
            'issues_by_dimension': self.issues_by_dimension,
            'auto_fixable_count': self.auto_fixable_count,
            'auto_fix_rate': self.auto_fix_rate,
            'average_confidence': self.average_confidence,
            'overall_pass_rate': self.overall_pass_rate,
            'total_checks_performed': self.total_checks_performed,
            'checks_passed': self.checks_passed,
            'execution_time_ms': self.execution_time_ms,
            'pii_detected': self.pii_detected,
            'pii_count': self.pii_count,
            'security_issues': self.security_issues
        }


class ReviewResult(BaseModel):
    """Complete review result for a document."""
    
    document_id: str = Field(..., min_length=1)
    document_type: str = Field(..., min_length=1)
    review_id: str = Field(..., min_length=1)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    overall_score: float = Field(ge=0.0, le=100.0)
    status: ReviewStatus
    
    dimension_results: List[DimensionResult] = Field(default_factory=list)
    all_issues: List[ReviewIssue] = Field(default_factory=list)
    metrics: ReviewMetrics = Field(default_factory=ReviewMetrics)
    
    reviewer_notes: Optional[str] = Field(default=None)
    recommended_actions: List[str] = Field(default_factory=list)
    approval_conditions: List[str] = Field(default_factory=list)
    
    configuration: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @model_validator(mode='after')
    def validate_consistency(self) -> Self:
        """Validate data consistency across the model."""
        # Aggregate all issues from dimensions
        all_dimension_issues = []
        for dim_result in self.dimension_results:
            all_dimension_issues.extend(dim_result.issues)
        
        # Update all_issues if not set
        if not self.all_issues and all_dimension_issues:
            self.all_issues = all_dimension_issues
        
        # Update metrics
        self.metrics.total_issues = len(self.all_issues)
        
        # Calculate issues by severity
        severity_counts = {severity.value: 0 for severity in ReviewSeverity}
        dimension_counts = {dim.value: 0 for dim in ReviewDimension}
        auto_fixable = 0
        total_confidence = 0.0
        
        for issue in self.all_issues:
            severity_counts[issue.severity.value] += 1
            dimension_counts[issue.dimension.value] += 1
            if issue.auto_fixable:
                auto_fixable += 1
            total_confidence += issue.confidence
        
        self.metrics.issues_by_severity = severity_counts
        self.metrics.issues_by_dimension = dimension_counts
        self.metrics.auto_fixable_count = auto_fixable
        
        if self.all_issues:
            self.metrics.average_confidence = total_confidence / len(self.all_issues)
        
        # Aggregate check counts
        total_checks = sum(dim.total_checks for dim in self.dimension_results)
        passed_checks = sum(dim.passed_checks for dim in self.dimension_results)
        self.metrics.total_checks_performed = total_checks
        self.metrics.checks_passed = passed_checks
        
        # Calculate total execution time
        total_time = sum(dim.execution_time_ms for dim in self.dimension_results)
        self.metrics.execution_time_ms = total_time
        
        return self
    
    @property
    def has_blockers(self) -> bool:
        """Check if review has any blocker issues."""
        return any(issue.severity == ReviewSeverity.BLOCKER for issue in self.all_issues)
    
    @property
    def critical_count(self) -> int:
        """Count critical and blocker issues."""
        return sum(1 for issue in self.all_issues 
                  if issue.severity in [ReviewSeverity.BLOCKER, ReviewSeverity.CRITICAL])
    
    @property
    def is_approved(self) -> bool:
        """Check if document is approved."""
        return self.status in [ReviewStatus.APPROVED, ReviewStatus.APPROVED_WITH_CONDITIONS]
    
    @property
    def needs_immediate_attention(self) -> bool:
        """Check if document needs immediate attention."""
        return self.has_blockers or self.status == ReviewStatus.REJECTED
    
    def get_dimension_score(self, dimension: ReviewDimension) -> Optional[float]:
        """Get score for a specific dimension."""
        for dim_result in self.dimension_results:
            if dim_result.dimension == dimension:
                return dim_result.score
        return None
    
    def get_issues_by_severity(self, severity: ReviewSeverity) -> List[ReviewIssue]:
        """Get all issues of a specific severity."""
        return [issue for issue in self.all_issues if issue.severity == severity]
    
    def get_issues_by_dimension(self, dimension: ReviewDimension) -> List[ReviewIssue]:
        """Get all issues for a specific dimension."""
        return [issue for issue in self.all_issues if issue.dimension == dimension]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'document_id': self.document_id,
            'document_type': self.document_type,
            'review_id': self.review_id,
            'timestamp': self.timestamp.isoformat(),
            'overall_score': self.overall_score,
            'status': self.status.value,
            'dimension_results': [dim.to_dict() for dim in self.dimension_results],
            'all_issues': [issue.to_dict() for issue in self.all_issues],
            'metrics': self.metrics.to_dict(),
            'has_blockers': self.has_blockers,
            'critical_count': self.critical_count,
            'is_approved': self.is_approved,
            'needs_immediate_attention': self.needs_immediate_attention,
            'reviewer_notes': self.reviewer_notes,
            'recommended_actions': self.recommended_actions,
            'approval_conditions': self.approval_conditions,
            'configuration': self.configuration,
            'metadata': self.metadata
        }
    
    def to_summary(self) -> str:
        """Generate a text summary of the review."""
        lines = [
            f"Review Summary for {self.document_id}",
            "=" * 50,
            f"Status: {self.status.value.upper()}",
            f"Overall Score: {self.overall_score:.1f}/100",
            f"Review ID: {self.review_id}",
            f"Timestamp: {self.timestamp.isoformat()}",
            "",
            "Issue Summary:",
            f"  Total Issues: {self.metrics.total_issues}",
            f"  Blockers: {self.metrics.issues_by_severity.get('blocker', 0)}",
            f"  Critical: {self.metrics.issues_by_severity.get('critical', 0)}",
            f"  High: {self.metrics.issues_by_severity.get('high', 0)}",
            f"  Medium: {self.metrics.issues_by_severity.get('medium', 0)}",
            f"  Low: {self.metrics.issues_by_severity.get('low', 0)}",
            f"  Info: {self.metrics.issues_by_severity.get('info', 0)}",
            "",
            "Dimension Scores:"
        ]
        
        for dim_result in self.dimension_results:
            lines.append(f"  {dim_result.dimension.value}: {dim_result.score:.1f}/100 "
                        f"(weight: {dim_result.weight:.2f})")
        
        if self.recommended_actions:
            lines.extend(["", "Recommended Actions:"])
            for i, action in enumerate(self.recommended_actions, 1):
                lines.append(f"  {i}. {action}")
        
        if self.approval_conditions:
            lines.extend(["", "Approval Conditions:"])
            for i, condition in enumerate(self.approval_conditions, 1):
                lines.append(f"  {i}. {condition}")
        
        if self.reviewer_notes:
            lines.extend(["", "Reviewer Notes:", self.reviewer_notes])
        
        return "\n".join(lines)


class ReviewEngineConfig(BaseModel):
    """Configuration for the Review Engine."""
    
    # Review thresholds
    approval_threshold: float = Field(
        default=85.0,
        ge=0.0,
        le=100.0,
        description="Minimum score for approval"
    )
    conditional_approval_threshold: float = Field(
        default=70.0,
        ge=0.0,
        le=100.0,
        description="Minimum score for conditional approval"
    )
    
    # Dimension weights
    dimension_weights: Dict[ReviewDimension, float] = Field(
        default_factory=lambda: {
            ReviewDimension.TECHNICAL_ACCURACY: 0.25,
            ReviewDimension.COMPLETENESS: 0.20,
            ReviewDimension.CONSISTENCY: 0.20,
            ReviewDimension.STYLE_FORMATTING: 0.15,
            ReviewDimension.SECURITY_PII: 0.20,
        }
    )
    
    # Enabled dimensions
    enabled_dimensions: Set[ReviewDimension] = Field(
        default_factory=lambda: {
            ReviewDimension.TECHNICAL_ACCURACY,
            ReviewDimension.COMPLETENESS,
            ReviewDimension.CONSISTENCY,
            ReviewDimension.STYLE_FORMATTING,
            ReviewDimension.SECURITY_PII,
        }
    )
    
    # Performance settings
    enable_caching: bool = Field(default=True)
    cache_ttl_seconds: int = Field(default=3600, ge=0)
    parallel_analysis: bool = Field(default=True)
    max_workers: int = Field(default=4, ge=1, le=16)
    timeout_seconds: int = Field(default=300, ge=10)
    
    # Security settings
    enable_pii_detection: bool = Field(default=True)
    pii_detection_confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    mask_pii_in_reports: bool = Field(default=True)
    
    # Behavior settings
    strict_mode: bool = Field(
        default=False,
        description="Fail on any blocker issue"
    )
    auto_fix_enabled: bool = Field(
        default=False,
        description="Enable automatic issue fixing where possible"
    )
    generate_suggestions: bool = Field(
        default=True,
        description="Generate improvement suggestions"
    )
    include_code_snippets: bool = Field(
        default=True,
        description="Include code snippets in issues"
    )
    
    # Integration settings
    use_quality_engine: bool = Field(
        default=True,
        description="Use M005 Quality Engine for additional analysis"
    )
    use_miair_optimization: bool = Field(
        default=True,
        description="Use M003 MIAIR for document optimization"
    )
    
    @model_validator(mode='after')
    def validate_thresholds(self) -> Self:
        """Validate threshold values."""
        if self.conditional_approval_threshold >= self.approval_threshold:
            raise ValueError(
                "Conditional approval threshold must be less than approval threshold"
            )
        
        # Validate dimension weights sum to 1.0
        if self.enabled_dimensions:
            enabled_weights = {
                dim: weight 
                for dim, weight in self.dimension_weights.items() 
                if dim in self.enabled_dimensions
            }
            total_weight = sum(enabled_weights.values())
            if abs(total_weight - 1.0) > 0.01:  # Allow small floating point error
                # Normalize weights
                for dim in enabled_weights:
                    self.dimension_weights[dim] = enabled_weights[dim] / total_weight
        
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'approval_threshold': self.approval_threshold,
            'conditional_approval_threshold': self.conditional_approval_threshold,
            'dimension_weights': {
                dim.value: weight 
                for dim, weight in self.dimension_weights.items()
            },
            'enabled_dimensions': [dim.value for dim in self.enabled_dimensions],
            'enable_caching': self.enable_caching,
            'cache_ttl_seconds': self.cache_ttl_seconds,
            'parallel_analysis': self.parallel_analysis,
            'max_workers': self.max_workers,
            'timeout_seconds': self.timeout_seconds,
            'enable_pii_detection': self.enable_pii_detection,
            'pii_detection_confidence': self.pii_detection_confidence,
            'mask_pii_in_reports': self.mask_pii_in_reports,
            'strict_mode': self.strict_mode,
            'auto_fix_enabled': self.auto_fix_enabled,
            'generate_suggestions': self.generate_suggestions,
            'include_code_snippets': self.include_code_snippets,
            'use_quality_engine': self.use_quality_engine,
            'use_miair_optimization': self.use_miair_optimization
        }