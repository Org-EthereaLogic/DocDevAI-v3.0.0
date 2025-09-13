"""
DevDocAI FastAPI Application
Main API entry point with CORS configuration for frontend development.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .routers import (
    dashboard_router,
    documents_router,
    health_router,
    review_router,
    suites_router,
    templates_router,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle.
    Initialize resources on startup, cleanup on shutdown.
    """
    # Startup
    logger.info("Starting DevDocAI API v3.0.0...")
    logger.info("Initializing LLM connections...")

    # Import and initialize components
    from ..core.config import ConfigurationManager
    from ..intelligence.llm_adapter import LLMAdapter

    try:
        config = ConfigurationManager()
        llm = LLMAdapter(config)
        logger.info("✅ Components initialized successfully")
    except Exception as e:
        logger.warning(f"⚠️  Component initialization warning: {e}")
        logger.info("API will start but some features may be limited")

    yield

    # Shutdown
    logger.info("Shutting down DevDocAI API...")


# Create FastAPI app
app = FastAPI(
    title="DevDocAI API",
    description="AI-powered documentation generation API for solo developers",
    version="3.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Configure CORS for frontend development
# In production, replace with specific origins
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,  # Vue dev server default port
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods in dev
    allow_headers=["*"],  # Allow all headers in dev
    expose_headers=["*"],  # Expose all headers in dev
)


# Custom exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed messages."""
    errors = []
    for error in exc.errors():
        errors.append(
            {
                "field": ".".join(str(loc) for loc in error["loc"][1:]),
                "message": error["msg"],
                "type": error["type"],
            }
        )

    return JSONResponse(
        status_code=422, content={"success": False, "error": "Validation failed", "details": errors}
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with consistent format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.detail, "status_code": exc.status_code},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.exception(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "message": str(exc) if os.getenv("DEBUG") else "An unexpected error occurred",
        },
    )


# Include routers
app.include_router(health_router)
app.include_router(documents_router)
app.include_router(dashboard_router)
app.include_router(templates_router)
app.include_router(suites_router)
app.include_router(review_router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "DevDocAI API",
        "version": "3.0.0",
        "status": "operational",
        "documentation": "/api/docs",
        "health": "/api/v1/health",
    }


# API Info endpoint
@app.get("/api/v1/info")
async def api_info():
    """Get API information and capabilities."""
    return {
        "name": "DevDocAI API",
        "version": "3.0.0",
        "description": "AI-powered documentation generation for solo developers",
        "capabilities": [
            "README generation",
            "API documentation",
            "Changelog generation",
            "Document validation",
            "Template management",
            "Quality review and analysis",
            "Document suite management",
            "Dependency tracking",
            "Dashboard analytics",
        ],
        "endpoints": {
            "health": "/api/v1/health",
            "documents": "/api/v1/documents",
            "dashboard": "/api/v1/dashboard",
            "templates": "/api/v1/templates",
            "suites": "/api/v1/suites",
            "review": "/api/v1/documents/{id}/review",
            "quality": "/api/v1/documents/{id}/quality",
        },
        "models": {
            "available": ["gpt-4", "gpt-3.5-turbo", "claude-3", "gemini-pro"],
            "default": "gpt-4",
        },
    }


if __name__ == "__main__":
    import uvicorn

    # Development server configuration
    uvicorn.run("devdocai.api.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
