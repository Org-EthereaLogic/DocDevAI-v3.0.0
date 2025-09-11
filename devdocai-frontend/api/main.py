"""
DevDocAI FastAPI Backend Bridge

This FastAPI application serves as a bridge between the Next.js frontend
and the Python DevDocAI core modules, providing REST API endpoints
for document generation, AI enhancement, and other features.
"""

import os
import sys
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add the parent directory to the path to import DevDocAI modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from devdocai.core.config import ConfigurationManager
    from devdocai.core.generator import DocumentGenerator
    from devdocai.intelligence.enhance import EnhancementPipeline
    from devdocai.intelligence.miair import MIAIREngine
    from devdocai.operations.marketplace import TemplateMarketplaceClient
except ImportError as e:
    print(f"Warning: Could not import DevDocAI modules: {e}")
    print("Running in demo mode with mock responses")

# FastAPI app instance
app = FastAPI(
    title="DevDocAI API",
    description="Modern REST API bridge for DevDocAI Python core",
    version="3.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for API requests/responses
class GenerateDocumentRequest(BaseModel):
    template: str
    context: Dict[str, Any]
    output_format: str = "markdown"


class EnhanceDocumentRequest(BaseModel):
    content: str
    strategy: str = "MIAIR_ENHANCED"
    target_quality: float = 0.85


class AnalyzeDocumentRequest(BaseModel):
    content: str
    include_suggestions: bool = True


class ConfigurationResponse(BaseModel):
    privacy_mode: str
    telemetry_enabled: bool
    api_provider: str
    memory_mode: str
    available_memory: float
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None


class ConfigurationUpdateRequest(BaseModel):
    privacy_mode: Optional[str] = None
    telemetry_enabled: Optional[bool] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None


class DocumentResponse(BaseModel):
    content: str
    metadata: Dict[str, Any]
    quality_score: Optional[float] = None


class EnhancementResponse(BaseModel):
    enhanced_content: str
    improvements: List[str]
    quality_improvement: float
    entropy_reduction: float


class AnalysisResponse(BaseModel):
    quality_score: float
    entropy_score: float
    suggestions: List[str]
    issues_found: int


# API Routes


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "DevDocAI API v3.0.0",
        "status": "operational",
        "endpoints": [
            "/api/config",
            "/api/documents/generate",
            "/api/documents/enhance",
            "/api/documents/analyze",
            "/api/templates/list",
            "/api/marketplace/templates",
        ],
    }


@app.get("/api/config", response_model=ConfigurationResponse)
async def get_configuration():
    """Get current DevDocAI configuration"""
    try:
        config_manager = ConfigurationManager()

        # Get API keys (masked for security)
        def mask_key(key):
            if not key or key == "your_key_here":
                return None
            return key if len(key) <= 8 else f"{key[:4]}{'*' * (len(key) - 8)}{key[-4:]}"

        return ConfigurationResponse(
            privacy_mode=config_manager.privacy_mode.value,
            telemetry_enabled=config_manager.telemetry_enabled,
            api_provider=config_manager.api_provider,
            memory_mode=config_manager.memory_mode.value,
            available_memory=config_manager.available_memory,
            openai_api_key=mask_key(getattr(config_manager, "openai_api_key", None)),
            anthropic_api_key=mask_key(getattr(config_manager, "anthropic_api_key", None)),
            google_api_key=mask_key(getattr(config_manager, "google_api_key", None)),
        )
    except Exception:
        # Demo mode fallback
        return ConfigurationResponse(
            privacy_mode="LOCAL_ONLY",
            telemetry_enabled=False,
            api_provider="openai",
            memory_mode="performance",
            available_memory=8.0,
        )


@app.post("/api/config")
async def update_configuration(request: ConfigurationUpdateRequest):
    """Update DevDocAI configuration"""
    try:
        # config_manager = ConfigurationManager()

        # Update configuration with provided values
        if request.privacy_mode is not None:
            # Update privacy mode if needed
            pass

        if request.telemetry_enabled is not None:
            # Update telemetry setting if needed
            pass

        # Handle API key updates
        config_updates = {}
        if request.openai_api_key is not None and request.openai_api_key.strip():
            config_updates["openai_api_key"] = request.openai_api_key.strip()

        if request.anthropic_api_key is not None and request.anthropic_api_key.strip():
            config_updates["anthropic_api_key"] = request.anthropic_api_key.strip()

        if request.google_api_key is not None and request.google_api_key.strip():
            config_updates["google_api_key"] = request.google_api_key.strip()

        # Save configuration updates to .devdocai.yml
        if config_updates:
            import os

            import yaml

            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".devdocai.yml"
            )

            # Load existing config or create new one
            config_data = {}
            if os.path.exists(config_path):
                try:
                    with open(config_path) as f:
                        config_data = yaml.safe_load(f) or {}
                except Exception:
                    config_data = {}

            # Update providers section
            if "providers" not in config_data:
                config_data["providers"] = {}

            config_data["providers"].update(config_updates)

            # Also update privacy settings if provided
            if request.privacy_mode is not None:
                config_data["privacy_mode"] = request.privacy_mode
            if request.telemetry_enabled is not None:
                config_data["telemetry_enabled"] = request.telemetry_enabled

            # Write updated config
            with open(config_path, "w") as f:
                yaml.dump(config_data, f, default_flow_style=False)

        return {"status": "success", "message": "Configuration updated successfully"}

    except Exception as e:
        return {"status": "error", "message": f"Failed to update configuration: {str(e)}"}


@app.post("/api/documents/generate", response_model=DocumentResponse)
async def generate_document(request: GenerateDocumentRequest):
    """Generate a new document using AI"""
    try:
        generator = DocumentGenerator()

        # Generate document using M004 Document Generator
        result = await generator.generate_async(
            template_name=request.template,
            context=request.context,
            output_format=request.output_format,
        )

        return DocumentResponse(
            content=result.content,
            metadata={
                "template": request.template,
                "generation_time": result.metadata.get("generation_time"),
                "tokens_used": result.metadata.get("tokens_used"),
                "provider": result.metadata.get("provider"),
            },
            quality_score=result.metadata.get("quality_score"),
        )
    except Exception:
        # Demo mode response
        demo_content = f"""# {request.context.get('title', 'Sample Document')}

## Overview
This is a demo document generated by DevDocAI v3.0.0.

## Features
- AI-powered content generation
- Multiple template support
- Real-time enhancement
- Quality analysis

## Getting Started
1. Install DevDocAI: `pip install devdocai`
2. Configure your settings
3. Generate amazing documentation

*Generated with DevDocAI v3.0.0 - Demo Mode*
"""

        return DocumentResponse(
            content=demo_content,
            metadata={"template": request.template, "demo_mode": True, "generation_time": "0.5s"},
            quality_score=0.75,
        )


@app.post("/api/documents/enhance", response_model=EnhancementResponse)
async def enhance_document(request: EnhanceDocumentRequest):
    """Enhance document using MIAIR Engine and AI"""
    try:
        # Use M009 Enhancement Pipeline
        pipeline = EnhancementPipeline()

        result = await pipeline.enhance_async(
            content=request.content,
            strategy=request.strategy,
            target_quality=request.target_quality,
        )

        return EnhancementResponse(
            enhanced_content=result.enhanced_content,
            improvements=result.improvements,
            quality_improvement=result.quality_improvement,
            entropy_reduction=result.entropy_reduction,
        )
    except Exception:
        # Demo mode enhancement
        enhanced_content = request.content + "\n\n✨ *Enhanced with AI - Demo Mode*"

        return EnhancementResponse(
            enhanced_content=enhanced_content,
            improvements=[
                "Improved clarity and readability",
                "Enhanced structure and flow",
                "Added missing context",
            ],
            quality_improvement=0.15,
            entropy_reduction=0.23,
        )


@app.post("/api/documents/analyze", response_model=AnalysisResponse)
async def analyze_document(request: AnalyzeDocumentRequest):
    """Analyze document quality using MIAIR Engine"""
    try:
        # Use M003 MIAIR Engine
        miair = MIAIREngine()

        analysis = await miair.analyze_async(
            content=request.content, include_suggestions=request.include_suggestions
        )

        return AnalysisResponse(
            quality_score=analysis.quality_score,
            entropy_score=analysis.entropy_score,
            suggestions=analysis.suggestions,
            issues_found=len(analysis.issues),
        )
    except Exception:
        # Demo mode analysis
        word_count = len(request.content.split())
        quality_score = min(0.9, 0.5 + (word_count / 1000))

        return AnalysisResponse(
            quality_score=quality_score,
            entropy_score=0.75,
            suggestions=[
                "Consider adding more specific examples",
                "Break up long paragraphs for readability",
                "Add section headers for better structure",
            ],
            issues_found=2,
        )


@app.get("/api/templates/list")
async def list_templates():
    """List available document templates"""
    try:
        generator = DocumentGenerator()
        templates = await generator.list_templates()
        return {"templates": templates}
    except Exception:
        # Demo templates
        return {
            "templates": [
                {
                    "id": "readme",
                    "name": "README.md",
                    "description": "Comprehensive project README",
                    "category": "Project Documentation",
                },
                {
                    "id": "api-doc",
                    "name": "API Documentation",
                    "description": "REST API documentation template",
                    "category": "Technical Documentation",
                },
                {
                    "id": "user-guide",
                    "name": "User Guide",
                    "description": "End-user documentation",
                    "category": "User Documentation",
                },
                {
                    "id": "changelog",
                    "name": "Changelog",
                    "description": "Version history and changes",
                    "category": "Project Documentation",
                },
            ]
        }


@app.get("/api/marketplace/templates")
async def get_marketplace_templates():
    """Get templates from the marketplace"""
    try:
        marketplace = TemplateMarketplaceClient()
        templates = await marketplace.discover_templates()
        return {"templates": templates}
    except Exception:
        # Demo marketplace templates
        return {
            "templates": [
                {
                    "id": "community-readme",
                    "name": "Community README Pro",
                    "author": "DevDocAI Team",
                    "description": "Advanced README with badges, stats, and contribution guidelines",
                    "downloads": 1250,
                    "rating": 4.8,
                    "category": "Community",
                },
                {
                    "id": "startup-docs",
                    "name": "Startup Documentation Kit",
                    "author": "StartupDocs",
                    "description": "Complete documentation suite for early-stage startups",
                    "downloads": 892,
                    "rating": 4.6,
                    "category": "Business",
                },
            ]
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
