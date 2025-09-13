"""Dashboard API models."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class DashboardStatsResponse(BaseModel):
    """Overall dashboard statistics response."""

    total_documents: int = Field(..., description="Total number of documents in the system")
    recent_documents: int = Field(..., description="Documents generated in the time period")
    average_quality_score: float = Field(..., description="Average quality score (0-100)")
    document_types: Dict[str, int] = Field(..., description="Count by document type")
    total_dependencies: int = Field(..., description="Total dependency relationships tracked")
    time_period_days: int = Field(..., description="Time period for statistics in days")
    generated_today: int = Field(..., description="Documents generated today")
    active_projects: int = Field(..., description="Number of active projects")

    class Config:
        json_schema_extra = {
            "example": {
                "total_documents": 150,
                "recent_documents": 45,
                "average_quality_score": 82.5,
                "document_types": {"readme": 50, "api_doc": 45, "changelog": 30, "guide": 25},
                "total_dependencies": 230,
                "time_period_days": 30,
                "generated_today": 5,
                "active_projects": 12,
            }
        }


class ProjectSummary(BaseModel):
    """Summary information for a project."""

    project_id: str = Field(..., description="Unique project identifier")
    name: str = Field(..., description="Project display name")
    document_count: int = Field(..., description="Number of documents in project")
    document_types: Dict[str, int] = Field(..., description="Document count by type")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")
    health_score: float = Field(..., description="Project health score (0-100)")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ProjectListResponse(BaseModel):
    """List of projects response."""

    projects: List[ProjectSummary] = Field(..., description="List of project summaries")
    total: int = Field(..., description="Total number of projects")
    limit: int = Field(..., description="Maximum items per page")
    offset: int = Field(..., description="Number of items skipped")

    class Config:
        json_schema_extra = {
            "example": {
                "projects": [
                    {
                        "project_id": "devdocai",
                        "name": "DevDocAI",
                        "document_count": 15,
                        "document_types": {"readme": 1, "api_doc": 5, "changelog": 2, "guide": 7},
                        "last_updated": "2025-09-12T10:30:00Z",
                        "health_score": 85.5,
                    }
                ],
                "total": 10,
                "limit": 100,
                "offset": 0,
            }
        }


class ProjectHealthResponse(BaseModel):
    """Detailed project health information."""

    project_id: str = Field(..., description="Project identifier")
    health_score: float = Field(..., description="Overall health score (0-100)")
    status: str = Field(
        ..., description="Health status", pattern="^(healthy|needs_attention|critical)$"
    )
    metrics: Dict[str, float] = Field(..., description="Individual metric scores")
    document_count: int = Field(..., description="Total documents in project")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")
    missing_documents: List[str] = Field(
        default_factory=list, description="Missing essential documents"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Health improvement recommendations"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
        json_schema_extra = {
            "example": {
                "project_id": "devdocai",
                "health_score": 82.3,
                "status": "healthy",
                "metrics": {
                    "completeness_score": 66.7,
                    "quality_score": 85.0,
                    "freshness_score": 90.0,
                    "dependency_score": 100.0,
                },
                "document_count": 15,
                "last_updated": "2025-09-12T10:30:00Z",
                "missing_documents": ["changelog"],
                "recommendations": [
                    "Add missing documentation: changelog",
                    "Consider updating older documents",
                ],
            }
        }
