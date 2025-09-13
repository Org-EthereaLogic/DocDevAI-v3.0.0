"""Template marketplace API models."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class TemplateMetadata(BaseModel):
    """Template metadata for list view."""

    id: str = Field(..., description="Unique template identifier")
    name: str = Field(..., description="Template display name")
    description: str = Field(..., description="Short template description")
    category: str = Field(..., description="Template category")
    version: str = Field(..., description="Template version")
    author: str = Field(..., description="Template author")
    languages: List[str] = Field(default_factory=list, description="Supported languages")
    downloads: int = Field(0, description="Number of downloads")
    rating: float = Field(0.0, description="User rating (0-5)")
    tags: List[str] = Field(default_factory=list, description="Template tags")
    preview_url: Optional[HttpUrl] = Field(None, description="Preview URL")
    is_verified: bool = Field(False, description="Verified by maintainers")


class TemplateListResponse(BaseModel):
    """Template list response with metadata."""

    templates: List[TemplateMetadata] = Field(..., description="List of templates")
    total: int = Field(..., description="Total number of templates")
    limit: int = Field(..., description="Items per page")
    offset: int = Field(..., description="Items skipped")
    categories: List[str] = Field(default_factory=list, description="Available categories")
    languages: List[str] = Field(default_factory=list, description="Available languages")

    class Config:
        json_schema_extra = {
            "example": {
                "templates": [
                    {
                        "id": "python-api",
                        "name": "Python API Documentation",
                        "description": "Professional API documentation template for Python projects",
                        "category": "api",
                        "version": "2.1.0",
                        "author": "DevDocAI Community",
                        "languages": ["python", "english"],
                        "downloads": 1250,
                        "rating": 4.8,
                        "tags": ["api", "python", "fastapi", "rest"],
                        "preview_url": "https://templates.devdocai.com/python-api/preview",
                        "is_verified": True,
                    }
                ],
                "total": 45,
                "limit": 50,
                "offset": 0,
                "categories": ["api", "readme", "changelog", "guide"],
                "languages": ["python", "javascript", "english", "spanish"],
            }
        }


class TemplateFile(BaseModel):
    """Template file information."""

    name: str = Field(..., description="File name")
    type: str = Field(..., description="File type (template, asset, config)")
    size: int = Field(..., description="File size in bytes")
    description: Optional[str] = Field(None, description="File description")


class TemplateDetailResponse(BaseModel):
    """Detailed template information."""

    id: str = Field(..., description="Template identifier")
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Short description")
    long_description: str = Field(..., description="Detailed description")
    category: str = Field(..., description="Template category")
    version: str = Field(..., description="Version")
    author: str = Field(..., description="Author name")
    author_url: Optional[HttpUrl] = Field(None, description="Author website")
    languages: List[str] = Field(default_factory=list, description="Supported languages")
    downloads: int = Field(0, description="Download count")
    rating: float = Field(0.0, description="User rating")
    tags: List[str] = Field(default_factory=list, description="Tags")
    preview_url: Optional[HttpUrl] = Field(None, description="Preview URL")
    documentation_url: Optional[HttpUrl] = Field(None, description="Documentation URL")
    repository_url: Optional[HttpUrl] = Field(None, description="Source repository")
    is_verified: bool = Field(False, description="Verified template")
    is_installed: bool = Field(False, description="Installed locally")
    files: List[TemplateFile] = Field(default_factory=list, description="Template files")
    dependencies: List[str] = Field(default_factory=list, description="Required dependencies")
    examples: List[Dict] = Field(default_factory=list, description="Usage examples")
    changelog: Optional[str] = Field(None, description="Version changelog")
    license: str = Field("MIT", description="License")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "python-api",
                "name": "Python API Documentation",
                "description": "Professional API documentation template",
                "long_description": "A comprehensive template for generating professional API documentation for Python projects. Includes FastAPI, Flask, and Django patterns with OpenAPI integration.",
                "category": "api",
                "version": "2.1.0",
                "author": "DevDocAI Community",
                "author_url": "https://devdocai.com",
                "languages": ["python", "english"],
                "downloads": 1250,
                "rating": 4.8,
                "tags": ["api", "python", "fastapi", "openapi"],
                "is_verified": True,
                "is_installed": False,
                "files": [
                    {
                        "name": "api_template.md",
                        "type": "template",
                        "size": 4500,
                        "description": "Main API documentation template",
                    }
                ],
                "dependencies": ["python>=3.8"],
                "license": "MIT",
            }
        }


class TemplateDownloadResponse(BaseModel):
    """Template download response."""

    success: bool = Field(..., description="Download success")
    template_id: str = Field(..., description="Template identifier")
    message: str = Field(..., description="Status message")
    installed: bool = Field(False, description="Successfully installed")
    install_path: Optional[str] = Field(None, description="Installation path")
    version: str = Field(..., description="Downloaded version")
    size_bytes: int = Field(0, description="Downloaded size in bytes")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "template_id": "python-api",
                "message": "Template downloaded and installed successfully",
                "installed": True,
                "install_path": "/home/user/.devdocai/templates/python-api",
                "version": "2.1.0",
                "size_bytes": 15420,
            }
        }
