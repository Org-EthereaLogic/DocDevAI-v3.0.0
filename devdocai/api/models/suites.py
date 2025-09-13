"""Document suite API models."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CreateSuiteRequest(BaseModel):
    """Request to create or update a document suite."""

    name: str = Field(..., description="Suite name", min_length=1, max_length=100)
    description: str = Field(..., description="Suite description", max_length=500)
    project_id: Optional[str] = Field(None, description="Associated project ID")
    document_ids: Optional[List[str]] = Field(
        default_factory=list, description="Document IDs in suite"
    )
    consistency_rules: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Rules for maintaining consistency"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "API Documentation Suite",
                "description": "Complete API documentation including endpoints, guides, and examples",
                "project_id": "devdocai",
                "document_ids": ["api_doc_1", "api_guide_1", "api_examples_1"],
                "consistency_rules": {
                    "terminology": {
                        "api_key": "API key",  # pragma: allowlist secret
                        "endpoint": "endpoint",
                    },
                    "style": {"headers": "title_case", "code_blocks": "python"},
                },
                "metadata": {"category": "technical", "priority": "high"},
            }
        }


class SuiteMetadata(BaseModel):
    """Suite metadata for list view."""

    id: str = Field(..., description="Suite identifier")
    name: str = Field(..., description="Suite name")
    description: str = Field(..., description="Suite description")
    status: str = Field(..., description="Suite status", pattern="^(active|archived|draft)$")
    project_id: Optional[str] = Field(None, description="Associated project")
    document_count: int = Field(..., description="Number of documents in suite")
    document_types: Dict[str, int] = Field(..., description="Document count by type")
    completion_percentage: float = Field(..., description="Completion percentage (0-100)")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class SuiteListResponse(BaseModel):
    """Response for listing suites."""

    suites: List[SuiteMetadata] = Field(..., description="List of suites")
    total: int = Field(..., description="Total number of suites")
    limit: int = Field(..., description="Items per page")
    offset: int = Field(..., description="Items skipped")

    class Config:
        json_schema_extra = {
            "example": {
                "suites": [
                    {
                        "id": "suite_123",
                        "name": "API Documentation Suite",
                        "description": "Complete API documentation set",
                        "status": "active",
                        "project_id": "devdocai",
                        "document_count": 5,
                        "document_types": {"api_doc": 3, "guide": 2},
                        "completion_percentage": 80.0,
                        "created_at": "2025-09-12T10:00:00Z",
                        "updated_at": "2025-09-12T15:30:00Z",
                    }
                ],
                "total": 15,
                "limit": 50,
                "offset": 0,
            }
        }


class SuiteDocument(BaseModel):
    """Document information within a suite."""

    id: str = Field(..., description="Document ID")
    title: str = Field(..., description="Document title")
    type: str = Field(..., description="Document type")
    status: str = Field(..., description="Document status")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")
    quality_score: Optional[float] = Field(None, description="Quality score (0-100)")


class SuiteDetailResponse(BaseModel):
    """Detailed suite information."""

    id: str = Field(..., description="Suite identifier")
    name: str = Field(..., description="Suite name")
    description: str = Field(..., description="Suite description")
    status: str = Field(..., description="Suite status")
    project_id: Optional[str] = Field(None, description="Associated project")
    documents: List[SuiteDocument] = Field(..., description="Documents in suite")
    consistency_rules: Dict[str, Any] = Field(..., description="Consistency rules")
    consistency_score: float = Field(..., description="Consistency score (0-100)")
    metadata: Dict[str, Any] = Field(..., description="Additional metadata")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "suite_123",
                "name": "API Documentation Suite",
                "description": "Complete API documentation including endpoints and guides",
                "status": "active",
                "project_id": "devdocai",
                "documents": [
                    {
                        "id": "api_doc_1",
                        "title": "REST API Reference",
                        "type": "api_doc",
                        "status": "completed",
                        "updated_at": "2025-09-12T15:30:00Z",
                        "quality_score": 85.5,
                    }
                ],
                "consistency_rules": {
                    "terminology": {"api_key": "API key"},
                    "style": {"headers": "title_case"},
                },
                "consistency_score": 92.5,
                "metadata": {"category": "technical"},
                "created_at": "2025-09-12T10:00:00Z",
                "updated_at": "2025-09-12T15:30:00Z",
            }
        }


class DependencyInfo(BaseModel):
    """Dependency relationship information."""

    source: str = Field(..., description="Source document ID")
    target: str = Field(..., description="Target document ID")
    type: str = Field(..., description="Dependency type")


class ImpactAnalysis(BaseModel):
    """Impact analysis for a document."""

    affected_documents: List[str] = Field(..., description="Documents affected by changes")
    impact_score: float = Field(..., description="Impact score (0-100)")
    critical_path: bool = Field(..., description="Is on critical path")


class DependencyTrackingResponse(BaseModel):
    """Dependency tracking information for a suite."""

    suite_id: str = Field(..., description="Suite identifier")
    dependencies: List[DependencyInfo] = Field(..., description="Dependency relationships")
    impact_analysis: Dict[str, ImpactAnalysis] = Field(
        ..., description="Impact analysis by document"
    )
    circular_references: List[List[str]] = Field(..., description="Circular dependency chains")
    orphaned_documents: List[str] = Field(..., description="Documents with no dependencies")
    statistics: Dict[str, Any] = Field(..., description="Dependency statistics")

    class Config:
        json_schema_extra = {
            "example": {
                "suite_id": "suite_123",
                "dependencies": [
                    {"source": "api_doc_1", "target": "api_guide_1", "type": "references"}
                ],
                "impact_analysis": {
                    "api_doc_1": {
                        "affected_documents": ["api_guide_1", "api_examples_1"],
                        "impact_score": 75.0,
                        "critical_path": True,
                    }
                },
                "circular_references": [],
                "orphaned_documents": [],
                "statistics": {
                    "total_documents": 5,
                    "total_dependencies": 8,
                    "max_depth": 3,
                    "average_dependencies": 1.6,
                },
            }
        }
