"""API Routers."""

from .documents import router as documents_router
from .health import router as health_router

__all__ = ["documents_router", "health_router"]
