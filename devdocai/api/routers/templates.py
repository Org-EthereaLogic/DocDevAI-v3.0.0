"""Template marketplace endpoints."""

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from ...core.config import ConfigurationManager
from ...operations.marketplace import TemplateMarketplaceClient
from ..models.templates import (
    TemplateDetailResponse,
    TemplateDownloadResponse,
    TemplateListResponse,
    TemplateMetadata,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/templates", tags=["templates"])

# Singleton instance
_marketplace_client = None


def get_marketplace_client():
    """Get or initialize marketplace client."""
    global _marketplace_client

    if _marketplace_client is None:
        try:
            config = ConfigurationManager()
            _marketplace_client = TemplateMarketplaceClient(config)
            logger.info("Marketplace client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize marketplace client: {e}")
            raise

    return _marketplace_client


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    category: Optional[str] = Query(None, description="Filter by category"),
    language: Optional[str] = Query(None, description="Filter by language"),
    search: Optional[str] = Query(None, description="Search in template names and descriptions"),
    sort_by: str = Query(
        "downloads", description="Sort field", pattern="^(downloads|rating|updated)$"
    ),
    limit: int = Query(50, description="Maximum number of templates", ge=1, le=200),
    offset: int = Query(0, description="Number of templates to skip", ge=0),
) -> TemplateListResponse:
    """
    List available templates from the marketplace.

    Returns a paginated list of templates with filtering and sorting options.
    """
    try:
        marketplace = get_marketplace_client()

        # Get all available templates
        templates = marketplace.list_templates()

        # Apply filters
        filtered = templates

        if category:
            filtered = [t for t in filtered if t.get("category") == category]

        if language:
            filtered = [t for t in filtered if language in t.get("languages", [])]

        if search:
            search_lower = search.lower()
            filtered = [
                t
                for t in filtered
                if search_lower in t.get("name", "").lower()
                or search_lower in t.get("description", "").lower()
            ]

        # Sort templates
        if sort_by == "downloads":
            filtered.sort(key=lambda t: t.get("downloads", 0), reverse=True)
        elif sort_by == "rating":
            filtered.sort(key=lambda t: t.get("rating", 0), reverse=True)
        elif sort_by == "updated":
            filtered.sort(key=lambda t: t.get("updated_at", ""), reverse=True)

        # Apply pagination
        total = len(filtered)
        paginated = filtered[offset : offset + limit]

        # Convert to response models
        template_list = [
            TemplateMetadata(
                id=t.get("id"),
                name=t.get("name"),
                description=t.get("description"),
                category=t.get("category", "general"),
                version=t.get("version", "1.0.0"),
                author=t.get("author", "Unknown"),
                languages=t.get("languages", []),
                downloads=t.get("downloads", 0),
                rating=t.get("rating", 0.0),
                tags=t.get("tags", []),
                preview_url=t.get("preview_url"),
                is_verified=t.get("is_verified", False),
            )
            for t in paginated
        ]

        # Get categories for filter options
        all_categories = list(set(t.get("category", "general") for t in templates))
        all_languages = list(set(lang for t in templates for lang in t.get("languages", [])))

        return TemplateListResponse(
            templates=template_list,
            total=total,
            limit=limit,
            offset=offset,
            categories=sorted(all_categories),
            languages=sorted(all_languages),
        )

    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{template_id}", response_model=TemplateDetailResponse)
async def get_template_details(template_id: str) -> TemplateDetailResponse:
    """
    Get detailed information about a specific template.

    Returns full template metadata including examples and documentation.
    """
    try:
        marketplace = get_marketplace_client()

        # Get template details
        template = marketplace.get_template(template_id)

        if not template:
            raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

        # Check if template is installed locally
        is_installed = marketplace.is_template_installed(template_id)

        # Get file list if available
        files = []
        if template.get("files"):
            files = [
                {
                    "name": f.get("name"),
                    "type": f.get("type", "template"),
                    "size": f.get("size", 0),
                    "description": f.get("description"),
                }
                for f in template.get("files", [])
            ]

        return TemplateDetailResponse(
            id=template.get("id"),
            name=template.get("name"),
            description=template.get("description"),
            long_description=template.get("long_description", template.get("description")),
            category=template.get("category", "general"),
            version=template.get("version", "1.0.0"),
            author=template.get("author", "Unknown"),
            author_url=template.get("author_url"),
            languages=template.get("languages", []),
            downloads=template.get("downloads", 0),
            rating=template.get("rating", 0.0),
            tags=template.get("tags", []),
            preview_url=template.get("preview_url"),
            documentation_url=template.get("documentation_url"),
            repository_url=template.get("repository_url"),
            is_verified=template.get("is_verified", False),
            is_installed=is_installed,
            files=files,
            dependencies=template.get("dependencies", []),
            examples=template.get("examples", []),
            changelog=template.get("changelog"),
            license=template.get("license", "MIT"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{template_id}/download", response_model=TemplateDownloadResponse)
async def download_template(
    template_id: str, install: bool = Query(True, description="Install template after download")
) -> TemplateDownloadResponse:
    """
    Download and optionally install a template from the marketplace.

    This endpoint downloads the template files and can automatically
    install them to the local template directory.
    """
    try:
        marketplace = get_marketplace_client()

        # Check if template exists
        template = marketplace.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

        # Check if already installed
        if marketplace.is_template_installed(template_id):
            return TemplateDownloadResponse(
                success=True,
                template_id=template_id,
                message="Template already installed",
                installed=True,
                install_path=str(marketplace.get_template_path(template_id)),
                version=template.get("version", "1.0.0"),
            )

        # Download template
        logger.info(f"Downloading template: {template_id}")
        download_result = marketplace.download_template(template_id)

        if not download_result.get("success"):
            raise HTTPException(
                status_code=500, detail=download_result.get("error", "Failed to download template")
            )

        # Install if requested
        installed = False
        install_path = None

        if install:
            logger.info(f"Installing template: {template_id}")
            install_result = marketplace.install_template(template_id)

            if install_result.get("success"):
                installed = True
                install_path = install_result.get("install_path")
            else:
                logger.warning(f"Failed to install template: {install_result.get('error')}")

        return TemplateDownloadResponse(
            success=True,
            template_id=template_id,
            message="Template downloaded successfully" + (" and installed" if installed else ""),
            installed=installed,
            install_path=str(install_path) if install_path else None,
            version=template.get("version", "1.0.0"),
            size_bytes=download_result.get("size_bytes", 0),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{template_id}/preview")
async def preview_template(template_id: str) -> FileResponse:
    """
    Get a preview file for the template.

    Returns a sample output or preview image for the template.
    """
    try:
        marketplace = get_marketplace_client()

        # Get template
        template = marketplace.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

        # Check for preview file
        preview_path = marketplace.get_template_preview(template_id)
        if not preview_path or not Path(preview_path).exists():
            raise HTTPException(status_code=404, detail="Preview not available for this template")

        # Return preview file
        return FileResponse(
            path=preview_path, media_type="text/markdown", filename=f"{template_id}_preview.md"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{template_id}")
async def uninstall_template(template_id: str) -> dict:
    """
    Uninstall a locally installed template.

    Removes the template from the local template directory.
    """
    try:
        marketplace = get_marketplace_client()

        # Check if installed
        if not marketplace.is_template_installed(template_id):
            raise HTTPException(
                status_code=404, detail=f"Template '{template_id}' is not installed"
            )

        # Uninstall template
        result = marketplace.uninstall_template(template_id)

        if not result.get("success"):
            raise HTTPException(
                status_code=500, detail=result.get("error", "Failed to uninstall template")
            )

        return {"success": True, "message": f"Template '{template_id}' uninstalled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uninstalling template: {e}")
        raise HTTPException(status_code=500, detail=str(e))
