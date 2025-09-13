"""API Request Models."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ReadmeRequest(BaseModel):
    """Request model for README generation."""

    project_name: str = Field(
        ..., description="Name of the project", min_length=1, max_length=100, example="DevDocAI"
    )

    description: str = Field(
        ...,
        description="Project description",
        min_length=10,
        max_length=1000,
        example="AI-powered documentation generation system for solo developers",
    )

    tech_stack: List[str] = Field(
        default_factory=list,
        description="List of technologies used",
        example=["Python", "FastAPI", "Vue.js", "OpenAI"],
    )

    features: List[str] = Field(
        default_factory=list,
        description="List of key features",
        example=["AI-powered generation", "Multi-format support", "Privacy-first design"],
    )

    author: str = Field(
        ..., description="Project author", min_length=1, max_length=100, example="John Doe"
    )

    installation_steps: Optional[List[str]] = Field(
        default=None,
        description="Installation instructions",
        example=["pip install devdocai", "devdocai init", "devdocai generate"],
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "project_name": "DevDocAI",
                "description": "AI-powered documentation generation system that helps solo developers create comprehensive, professional documentation with minimal effort",
                "tech_stack": ["Python 3.8+", "FastAPI", "Vue.js 3", "OpenAI GPT-4", "SQLite"],
                "features": [
                    "AI-powered documentation generation",
                    "Multi-format support (README, API, Changelog)",
                    "Privacy-first local storage",
                    "Intelligent dependency tracking",
                    "Real-time preview",
                ],
                "author": "DevDocAI Team",
                "installation_steps": [
                    "Clone the repository",
                    "Install dependencies: pip install -r requirements.txt",
                    "Configure API keys in .env",
                    "Run: python -m devdocai",
                ],
            }
        }


class APIEndpoint(BaseModel):
    """API endpoint information."""

    method: str = Field(..., description="HTTP method", pattern="^(GET|POST|PUT|DELETE|PATCH)$")
    path: str = Field(..., description="Endpoint path", example="/api/v1/documents")
    description: str = Field(..., description="Endpoint description")
    parameters: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list, description="Request parameters"
    )
    responses: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list, description="Response examples"
    )


class APIDocRequest(BaseModel):
    """Request model for API documentation generation."""

    project_name: str = Field(..., description="API project name", min_length=1, max_length=100)
    description: str = Field(..., description="API description", min_length=10, max_length=1000)
    api_base_url: str = Field(
        ..., description="Base URL for the API", example="https://api.devdocai.com"
    )
    version: str = Field(default="1.0.0", description="API version", example="1.0.0")
    endpoints: List[APIEndpoint] = Field(default_factory=list, description="List of API endpoints")
    authentication: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Authentication information"
    )
    examples: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list, description="Usage examples"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "project_name": "DevDocAI API",
                "description": "REST API for AI-powered documentation generation",
                "api_base_url": "https://api.devdocai.com",
                "version": "3.0.0",
                "endpoints": [
                    {
                        "method": "POST",
                        "path": "/api/v1/documents/readme",
                        "description": "Generate README documentation",
                        "parameters": [
                            {
                                "name": "project_name",
                                "type": "string",
                                "required": True,
                                "description": "Name of the project",
                            }
                        ],
                    }
                ],
                "authentication": {
                    "type": "bearer",
                    "description": "API key required in Authorization header",
                },
            }
        }


class ChangelogEntry(BaseModel):
    """Individual changelog entry."""

    type: str = Field(
        ...,
        description="Change type",
        pattern="^(added|changed|deprecated|removed|fixed|security)$",
    )
    description: str = Field(..., description="Change description")
    breaking: bool = Field(default=False, description="Is this a breaking change")


class ChangelogRequest(BaseModel):
    """Request model for changelog generation."""

    project_name: str = Field(..., description="Project name", min_length=1, max_length=100)
    version: str = Field(..., description="Version being released", example="1.2.0")
    release_date: Optional[str] = Field(
        None, description="Release date (YYYY-MM-DD)", example="2025-09-12"
    )
    changes: List[ChangelogEntry] = Field(
        default_factory=list, description="List of changes in this version"
    )
    breaking_changes: Optional[List[str]] = Field(
        default_factory=list, description="Breaking changes summary"
    )
    deprecated: Optional[List[str]] = Field(default_factory=list, description="Deprecated features")
    migration_notes: Optional[str] = Field(
        None, description="Migration instructions for breaking changes"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "project_name": "DevDocAI",
                "version": "3.1.0",
                "release_date": "2025-09-12",
                "changes": [
                    {
                        "type": "added",
                        "description": "New template marketplace with community templates",
                        "breaking": False,
                    },
                    {
                        "type": "improved",
                        "description": "Enhanced AI model performance for document generation",
                        "breaking": False,
                    },
                    {
                        "type": "fixed",
                        "description": "Resolved issue with dependency tracking in large projects",
                        "breaking": False,
                    },
                ],
                "breaking_changes": [],
                "deprecated": ["Legacy template format (use new marketplace templates)"],
            }
        }
