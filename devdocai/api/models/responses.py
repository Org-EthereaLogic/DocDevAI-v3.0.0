"""API Response Models."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    """Response model for document generation."""

    success: bool = Field(..., description="Whether the generation was successful")

    document_type: str = Field(..., description="Type of document generated", example="readme")

    content: Optional[str] = Field(
        None, description="Generated document content in markdown format"
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Generation metadata",
        example={
            "generation_time": 65.5,
            "model_used": "gpt-4",
            "token_count": 1500,
            "cost": 0.047,
        },
    )

    error: Optional[str] = Field(None, description="Error message if generation failed")

    generated_at: datetime = Field(
        default_factory=datetime.now, description="Timestamp of generation"
    )

    class Config:
        """Pydantic config."""

        json_encoders = {datetime: lambda v: v.isoformat()}
        schema_extra = {
            "example": {
                "success": True,
                "document_type": "readme",
                "content": "# DevDocAI\n\n## Description\nAI-powered documentation...",
                "metadata": {
                    "generation_time": 65.5,
                    "model_used": "gpt-4",
                    "token_count": 1500,
                    "cost": 0.047,
                },
                "error": None,
                "generated_at": "2025-09-12T10:30:00Z",
            }
        }
