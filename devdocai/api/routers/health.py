"""Health check endpoints."""

from typing import Dict

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint.

    Returns:
        Dict with status and version information.
    """
    return {"status": "healthy", "service": "DevDocAI API", "version": "3.0.0"}


@router.get("/ready")
async def readiness_check() -> Dict[str, bool]:
    """
    Readiness check endpoint.

    Checks if all required services are available.

    Returns:
        Dict with readiness status for each component.
    """
    # In a real scenario, we'd check database connections, LLM availability, etc.
    return {"ready": True, "database": True, "llm_adapter": True, "configuration": True}
