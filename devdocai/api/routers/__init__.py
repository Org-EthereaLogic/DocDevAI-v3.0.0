"""API Routers."""

from .dashboard import router as dashboard_router
from .documents import router as documents_router
from .health import router as health_router
from .review import router as review_router
from .suites import router as suites_router
from .templates import router as templates_router

__all__ = [
    "dashboard_router",
    "documents_router",
    "health_router",
    "review_router",
    "suites_router",
    "templates_router",
]
