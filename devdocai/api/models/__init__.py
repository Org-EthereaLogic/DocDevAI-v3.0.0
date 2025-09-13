"""API Models."""

from .dashboard import DashboardStatsResponse, ProjectHealthResponse, ProjectListResponse
from .requests import APIDocRequest, ChangelogRequest, ReadmeRequest
from .responses import DocumentResponse
from .review import DocumentQualityResponse, DocumentReviewResponse
from .suites import (
    CreateSuiteRequest,
    DependencyTrackingResponse,
    SuiteDetailResponse,
    SuiteListResponse,
)
from .templates import TemplateDetailResponse, TemplateDownloadResponse, TemplateListResponse

__all__ = [
    # Requests
    "APIDocRequest",
    "ChangelogRequest",
    "ReadmeRequest",
    "CreateSuiteRequest",
    # Responses
    "DocumentResponse",
    "DashboardStatsResponse",
    "ProjectHealthResponse",
    "ProjectListResponse",
    "DocumentQualityResponse",
    "DocumentReviewResponse",
    "SuiteDetailResponse",
    "SuiteListResponse",
    "DependencyTrackingResponse",
    "TemplateDetailResponse",
    "TemplateDownloadResponse",
    "TemplateListResponse",
]
