"""API Request Models."""

from typing import List, Optional

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

        schema_extra = {
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
