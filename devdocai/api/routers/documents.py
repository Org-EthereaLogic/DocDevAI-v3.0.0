"""Document generation endpoints."""

import logging
import time
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from ...core.config import ConfigurationManager
from ...core.generator import DocumentGenerator
from ...core.storage import StorageManager
from ...intelligence.llm_adapter import LLMAdapter
from ..models.requests import ReadmeRequest
from ..models.responses import DocumentResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

# Initialize components (singleton pattern for API)
_config_manager = None
_storage_manager = None
_llm_adapter = None
_document_generator = None


def get_document_generator():
    """Get or create document generator instance."""
    global _config_manager, _storage_manager, _llm_adapter, _document_generator

    if _document_generator is None:
        try:
            # Initialize configuration
            _config_manager = ConfigurationManager()

            # Initialize storage manager
            _storage_manager = StorageManager(_config_manager)

            # Initialize LLM adapter
            _llm_adapter = LLMAdapter(_config_manager)

            # Initialize document generator with correct parameters
            _document_generator = DocumentGenerator(
                config=_config_manager, storage_manager=_storage_manager, llm_adapter=_llm_adapter
            )

            logger.info("Document generator initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize document generator: {e}")
            raise

    return _document_generator


@router.post("/readme", response_model=DocumentResponse)
async def generate_readme(request: ReadmeRequest) -> DocumentResponse:
    """
    Generate a README document using AI.

    This endpoint uses the real LLM integration to generate
    professional README documentation based on the provided
    project information.

    Args:
        request: ReadmeRequest with project details

    Returns:
        DocumentResponse with generated content or error
    """
    start_time = time.time()

    try:
        # Get document generator
        generator = get_document_generator()

        # Prepare context for generation
        context = {
            "project_name": request.project_name,
            "description": request.description,
            "tech_stack": request.tech_stack,
            "features": request.features,
            "author": request.author,
            "installation_steps": request.installation_steps or [],
            "year": time.strftime("%Y"),
            "date": time.strftime("%Y-%m-%d"),
        }

        logger.info(f"Generating README for project: {request.project_name}")

        # Generate document using AI
        result = await generator.generate_document(
            template_name="readme",
            context=context,
            use_cache=True,  # Use cache if available
            validate=True,  # Validate generated content
        )

        generation_time = time.time() - start_time

        if result.success:
            logger.info(f"README generated successfully in {generation_time:.2f}s")

            return DocumentResponse(
                success=True,
                document_type="readme",
                content=result.document,
                metadata={
                    "generation_time": generation_time,
                    "model_used": result.model_used or "unknown",
                    "cached": result.cached,
                    "project_name": request.project_name,
                },
            )
        else:
            logger.error(f"Generation failed: {result.error}")

            return DocumentResponse(
                success=False,
                document_type="readme",
                content=None,
                error=result.error or "Unknown generation error",
                metadata={"generation_time": generation_time, "project_name": request.project_name},
            )

    except Exception as e:
        logger.exception(f"Unexpected error during README generation: {e}")

        return DocumentResponse(
            success=False,
            document_type="readme",
            content=None,
            error=f"Internal server error: {str(e)}",
            metadata={
                "generation_time": time.time() - start_time,
                "project_name": request.project_name,
            },
        )


@router.get("/templates")
async def list_templates() -> Dict[str, Any]:
    """
    List available document templates.

    Returns:
        Dict with available template names and descriptions.
    """
    templates = {
        "readme": {
            "name": "README",
            "description": "Comprehensive project README with features, installation, and usage",
            "required_fields": ["project_name", "description", "author"],
            "optional_fields": ["tech_stack", "features", "installation_steps"],
        },
        "api_doc": {
            "name": "API Documentation",
            "description": "REST API documentation with endpoints and examples",
            "required_fields": ["project_name", "api_base_url"],
            "optional_fields": ["endpoints", "authentication", "examples"],
        },
        "changelog": {
            "name": "Changelog",
            "description": "Version history and release notes",
            "required_fields": ["project_name", "version"],
            "optional_fields": ["changes", "breaking_changes", "deprecated"],
        },
    }

    return {"templates": templates, "total": len(templates)}


@router.post("/validate")
async def validate_document(content: str, document_type: str = "readme") -> Dict[str, Any]:
    """
    Validate a document for quality and completeness.

    Args:
        content: Document content to validate
        document_type: Type of document (readme, api_doc, etc.)

    Returns:
        Validation results with score and suggestions.
    """
    try:
        generator = get_document_generator()

        # Use the generator's validation method
        validation = generator.validator.validate_document(content, document_type)

        return {
            "valid": validation.is_valid,
            "score": validation.score,
            "issues": validation.issues,
            "suggestions": validation.suggestions,
            "metadata": validation.metadata,
        }

    except Exception as e:
        logger.exception(f"Validation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
