"""Document review and quality API models."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ReviewFinding(BaseModel):
    """Individual review finding."""

    reviewer: str = Field(..., description="Name of the reviewer that found this issue")
    type: str = Field(..., description="Type of finding (error, warning, suggestion)")
    severity: str = Field(..., description="Severity level", pattern="^(critical|high|medium|low)$")
    message: str = Field(..., description="Finding description")
    location: Optional[Dict[str, Any]] = Field(None, description="Location in document")
    suggestion: Optional[str] = Field(None, description="Suggested improvement")


class ReviewRecommendation(BaseModel):
    """Review recommendation for improvement."""

    reviewer: str = Field(..., description="Reviewer that made this recommendation")
    category: str = Field(..., description="Recommendation category")
    priority: str = Field(..., description="Priority level", pattern="^(critical|high|medium|low)$")
    action: str = Field(..., description="Recommended action")
    rationale: Optional[str] = Field(None, description="Why this is recommended")


class PIIDetection(BaseModel):
    """PII detection result."""

    type: str = Field(..., description="Type of PII detected")
    location: Optional[Dict[str, Any]] = Field(None, description="Location in document")
    confidence: float = Field(..., description="Detection confidence (0-1)")
    masked_value: Optional[str] = Field(None, description="Masked version of detected PII")


class DocumentReviewResponse(BaseModel):
    """Comprehensive document review response."""

    document_id: str = Field(..., description="Document identifier")
    overall_score: float = Field(..., description="Overall review score (0-100)")
    quality_gate_passed: bool = Field(..., description="Whether document passes quality gate")
    category_scores: Dict[str, float] = Field(..., description="Scores by review category")
    findings: List[ReviewFinding] = Field(..., description="All review findings")
    recommendations: List[ReviewRecommendation] = Field(
        ..., description="Improvement recommendations"
    )
    pii_detected: List[PIIDetection] = Field(..., description="PII detection results")
    review_metadata: Dict[str, Any] = Field(..., description="Review execution metadata")
    reviewed_at: Optional[str] = Field(None, description="Review timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "doc_123",
                "overall_score": 82.5,
                "quality_gate_passed": True,
                "category_scores": {
                    "content_reviewer": 85.0,
                    "structure_reviewer": 80.0,
                    "technical_reviewer": 82.0,
                    "completeness_reviewer": 85.0,
                },
                "findings": [
                    {
                        "reviewer": "structure_reviewer",
                        "type": "warning",
                        "severity": "medium",
                        "message": "Missing table of contents for long document",
                        "location": {"section": "header"},
                        "suggestion": "Add table of contents at the beginning",
                    }
                ],
                "recommendations": [
                    {
                        "reviewer": "content_reviewer",
                        "category": "clarity",
                        "priority": "medium",
                        "action": "Simplify technical jargon in introduction",
                        "rationale": "Improve accessibility for broader audience",
                    }
                ],
                "pii_detected": [],
                "review_metadata": {
                    "reviewers_used": ["content_reviewer", "structure_reviewer"],
                    "review_duration": 2.5,
                    "word_count": 1250,
                    "readability_score": 78.5,
                },
                "reviewed_at": "2025-09-12T15:30:00Z",
            }
        }


class ImprovementArea(BaseModel):
    """Area for quality improvement."""

    area: str = Field(..., description="Area name")
    current_score: float = Field(..., description="Current score for this area")
    target_score: float = Field(..., description="Target score to achieve")
    suggestions: List[str] = Field(..., description="Specific improvement suggestions")


class QualityTrend(BaseModel):
    """Quality trend data point."""

    timestamp: str = Field(..., description="Timestamp of measurement")
    score: float = Field(..., description="Quality score at this point")
    version: str = Field(..., description="Document version")


class DocumentQualityResponse(BaseModel):
    """Document quality analysis response."""

    document_id: str = Field(..., description="Document identifier")
    overall_score: float = Field(..., description="Overall quality score (0-100)")
    status: str = Field(
        ...,
        description="Quality status",
        pattern="^(excellent|good|acceptable|needs_improvement|poor)$",
    )
    metrics: Dict[str, float] = Field(..., description="Individual quality metrics")
    improvement_areas: List[ImprovementArea] = Field(..., description="Areas needing improvement")
    target_scores: Dict[str, float] = Field(..., description="Target scores for each metric")
    quality_trends: List[QualityTrend] = Field(
        default_factory=list, description="Quality over time"
    )
    benchmark_comparison: Dict[str, float] = Field(..., description="Comparison with benchmarks")
    last_review_date: Optional[str] = Field(None, description="Last review timestamp")
    estimated_improvement_time: int = Field(..., description="Estimated time to improve (minutes)")

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "doc_123",
                "overall_score": 78.5,
                "status": "good",
                "metrics": {
                    "readability_score": 75.0,
                    "completeness_score": 82.0,
                    "accuracy_score": 85.0,
                    "consistency_score": 70.0,
                    "structure_score": 80.0,
                },
                "improvement_areas": [
                    {
                        "area": "consistency",
                        "current_score": 70.0,
                        "target_score": 85.0,
                        "suggestions": [
                            "Standardize terminology usage",
                            "Apply consistent formatting",
                            "Use uniform style for code examples",
                        ],
                    }
                ],
                "target_scores": {
                    "readability_score": 85.0,
                    "completeness_score": 90.0,
                    "accuracy_score": 90.0,
                    "consistency_score": 85.0,
                    "structure_score": 90.0,
                },
                "quality_trends": [
                    {"timestamp": "2025-09-12T10:00:00Z", "score": 75.0, "version": "1.0"},
                    {"timestamp": "2025-09-12T15:30:00Z", "score": 78.5, "version": "1.1"},
                ],
                "benchmark_comparison": {
                    "industry_average": 75.0,
                    "project_average": 72.0,
                    "best_in_project": 88.0,
                },
                "last_review_date": "2025-09-12T15:30:00Z",
                "estimated_improvement_time": 60,
            }
        }
