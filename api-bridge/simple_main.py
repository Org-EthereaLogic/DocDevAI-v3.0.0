"""
DevDocAI FastAPI Backend - Simplified for Testing
"""

import random
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# FastAPI app instance
app = FastAPI(
    title="DevDocAI API",
    description="Modern REST API bridge for DevDocAI Python core",
    version="3.0.0",
)

# CORS middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
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


class Template(BaseModel):
    id: str
    name: str
    description: str
    category: Optional[str] = None
    author: Optional[str] = None
    version: Optional[str] = None


class GenerateDocumentRequest(BaseModel):
    template: str
    context: Dict[str, Any]
    output_format: Optional[str] = "markdown"
    source: Optional[str] = "local"


class EnhanceDocumentRequest(BaseModel):
    content: str
    strategy: Optional[str] = "MIAIR_ENHANCED"
    target_quality: Optional[float] = 0.85


class AnalyzeDocumentRequest(BaseModel):
    content: str
    include_suggestions: Optional[bool] = True


# Storage for configuration (in-memory for testing)
config_store = {
    "privacy_mode": "LOCAL_ONLY",
    "telemetry_enabled": False,
    "api_provider": "openai",
    "memory_mode": "performance",
    "openai_api_key": None,
    "anthropic_api_key": None,
    "google_api_key": None,
}

# Default templates for testing
DEFAULT_TEMPLATES = [
    {
        "id": "readme",
        "name": "README",
        "description": "Comprehensive project overview and setup guide",
        "category": "documentation",
        "author": "DevDocAI",
        "version": "1.0.0",
    },
    {
        "id": "api_doc",
        "name": "API Documentation",
        "description": "Detailed API endpoint documentation",
        "category": "api",
        "author": "DevDocAI",
        "version": "1.0.0",
    },
    {
        "id": "user_guide",
        "name": "User Guide",
        "description": "Step-by-step user documentation",
        "category": "documentation",
        "author": "DevDocAI",
        "version": "1.0.0",
    },
    {
        "id": "changelog",
        "name": "Changelog",
        "description": "Version history and release notes",
        "category": "documentation",
        "author": "DevDocAI",
        "version": "1.0.0",
    },
    {
        "id": "contributing",
        "name": "Contributing Guide",
        "description": "Guidelines for project contributors",
        "category": "documentation",
        "author": "DevDocAI",
        "version": "1.0.0",
    },
    {
        "id": "architecture",
        "name": "Architecture Overview",
        "description": "Technical design and system architecture",
        "category": "technical",
        "author": "DevDocAI",
        "version": "1.0.0",
    },
]

# Marketplace templates (simulated)
MARKETPLACE_TEMPLATES = [
    {
        "id": "rest_api_spec",
        "name": "REST API Specification",
        "description": "OpenAPI/Swagger compatible REST API documentation",
        "category": "api",
        "author": "Community",
        "version": "2.0.0",
    },
    {
        "id": "docker_guide",
        "name": "Docker Setup Guide",
        "description": "Container configuration and deployment guide",
        "category": "deployment",
        "author": "Community",
        "version": "1.2.0",
    },
    {
        "id": "security_policy",
        "name": "Security Policy",
        "description": "Security guidelines and vulnerability reporting",
        "category": "security",
        "author": "Community",
        "version": "1.1.0",
    },
    {
        "id": "testing_guide",
        "name": "Testing Documentation",
        "description": "Unit, integration, and E2E testing guide",
        "category": "testing",
        "author": "Community",
        "version": "1.3.0",
    },
]


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
        ],
    }


@app.get("/api/config", response_model=ConfigurationResponse)
async def get_configuration():
    """Get current DevDocAI configuration"""

    def mask_key(key):
        if not key:
            return None
        return key if len(key) <= 8 else f"{key[:4]}{'*' * (len(key) - 8)}{key[-4:]}"

    return ConfigurationResponse(
        privacy_mode=config_store["privacy_mode"],
        telemetry_enabled=config_store["telemetry_enabled"],
        api_provider=config_store["api_provider"],
        memory_mode=config_store["memory_mode"],
        available_memory=8.0,
        openai_api_key=mask_key(config_store.get("openai_api_key")),
        anthropic_api_key=mask_key(config_store.get("anthropic_api_key")),
        google_api_key=mask_key(config_store.get("google_api_key")),
    )


@app.post("/api/config")
async def update_configuration(request: ConfigurationUpdateRequest):
    """Update DevDocAI configuration"""
    # Update configuration with provided values
    if request.privacy_mode is not None:
        config_store["privacy_mode"] = request.privacy_mode

    if request.telemetry_enabled is not None:
        config_store["telemetry_enabled"] = request.telemetry_enabled

    if request.openai_api_key is not None and request.openai_api_key.strip():
        config_store["openai_api_key"] = request.openai_api_key.strip()

    if request.anthropic_api_key is not None and request.anthropic_api_key.strip():
        config_store["anthropic_api_key"] = request.anthropic_api_key.strip()

    if request.google_api_key is not None and request.google_api_key.strip():
        config_store["google_api_key"] = request.google_api_key.strip()

    return {"status": "success", "message": "Configuration updated successfully"}


@app.get("/api/templates/list")
async def list_templates():
    """List available local templates"""
    return {"templates": DEFAULT_TEMPLATES}


@app.get("/api/marketplace/templates")
async def get_marketplace_templates():
    """Get templates from the marketplace"""
    return {"templates": MARKETPLACE_TEMPLATES}


@app.post("/api/documents/generate")
async def generate_document(request: GenerateDocumentRequest):
    """Generate a document using the specified template"""
    # Check if API keys are configured
    if not any(
        [
            config_store.get("openai_api_key"),
            config_store.get("anthropic_api_key"),
            config_store.get("google_api_key"),
        ]
    ):
        # Return demo content if no API keys configured
        demo_content = generate_demo_content(request.template, request.context)
        return {
            "content": demo_content,
            "metadata": {
                "template": request.template,
                "generated_at": datetime.now().isoformat(),
                "mode": "demo",
            },
        }

    # In production, this would call the actual DevDocAI generator
    # For now, return simulated content
    content = generate_simulated_content(request.template, request.context)

    return {
        "content": content,
        "metadata": {
            "template": request.template,
            "generated_at": datetime.now().isoformat(),
            "source": request.source,
        },
    }


@app.post("/api/documents/enhance")
async def enhance_document(request: EnhanceDocumentRequest):
    """Enhance a document using MIAIR AI"""
    # Simulate enhancement by adding improvements
    enhanced = request.content + "\n\n## AI-Enhanced Sections\n\n"
    enhanced += "### Performance Optimizations\n"
    enhanced += "- Implemented lazy loading for improved initial load time\n"
    enhanced += "- Added caching strategies for frequently accessed data\n\n"
    enhanced += "### Security Improvements\n"
    enhanced += "- Enhanced input validation and sanitization\n"
    enhanced += "- Implemented rate limiting for API endpoints\n\n"
    enhanced += "### Documentation Quality\n"
    enhanced += "- Added comprehensive code examples\n"
    enhanced += "- Improved clarity and structure\n"

    return {
        "enhanced_content": enhanced,
        "improvements": [
            "Added performance optimization section",
            "Enhanced security documentation",
            "Improved code examples",
            "Restructured for better clarity",
        ],
        "quality_improvement": 0.35,
        "entropy_reduction": 0.42,
    }


@app.post("/api/documents/analyze")
async def analyze_document(request: AnalyzeDocumentRequest):
    """Analyze document quality"""
    # Simulate quality analysis
    content_length = len(request.content)
    has_sections = "##" in request.content or "#" in request.content
    has_code = "```" in request.content or "    " in request.content

    quality_score = 0.5
    if has_sections:
        quality_score += 0.2
    if has_code:
        quality_score += 0.15
    if content_length > 500:
        quality_score += 0.1
    if content_length > 1000:
        quality_score += 0.05

    entropy_score = random.uniform(0.6, 0.85)

    suggestions = []
    if not has_sections:
        suggestions.append("Add clear section headers for better organization")
    if not has_code:
        suggestions.append("Include code examples to illustrate usage")
    if content_length < 500:
        suggestions.append("Expand documentation with more details")
    suggestions.append("Consider adding a troubleshooting section")
    suggestions.append("Include performance benchmarks or metrics")

    return {
        "quality_score": min(quality_score, 1.0),
        "entropy_score": entropy_score,
        "suggestions": suggestions[:3],  # Return top 3 suggestions
        "issues_found": len(suggestions),
    }


def generate_demo_content(template_id: str, context: Dict[str, Any]) -> str:
    """Generate demo content when no API keys are configured"""
    title = context.get("title", "Project")
    description = context.get("description", "A project description")
    project_type = context.get("type", "application")
    features = context.get("features", "").split("\n") if context.get("features") else []

    if template_id == "readme":
        content = f"""# {title}

{description}

## Overview

This {project_type} provides a comprehensive solution for modern development needs.

## Features
"""
        for feature in features[:5]:
            if feature.strip():
                content += f"- {feature.strip()}\n"

        content += f"""
## Installation

```bash
npm install {title.lower().replace(' ', '-')}
# or
yarn add {title.lower().replace(' ', '-')}
```

## Quick Start

1. Clone the repository
2. Install dependencies
3. Run the development server

```bash
git clone https://github.com/yourusername/{title.lower().replace(' ', '-')}.git
cd {title.lower().replace(' ', '-')}
npm install
npm run dev
```

## Documentation

For detailed documentation, please visit our [documentation site](https://docs.example.com).

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## License

MIT License - see the [LICENSE](LICENSE) file for details.
"""

    elif template_id == "api_doc":
        content = f"""# {title} API Documentation

{description}

## Base URL

```
https://api.example.com/v1
```

## Authentication

All API requests require authentication using an API key:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" https://api.example.com/v1/endpoint
```

## Endpoints

### GET /api/users
Retrieve a list of users.

**Response:**
```json
{{
  "users": [
    {{
      "id": "123",
      "name": "John Doe",
      "email": "john@example.com"
    }}
  ]
}}
```

### POST /api/users
Create a new user.

**Request Body:**
```json
{{
  "name": "Jane Doe",
  "email": "jane@example.com"
}}
```

## Error Handling

The API uses standard HTTP status codes to indicate success or failure.

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 400 | Bad Request |
| 401 | Unauthorized |
| 404 | Not Found |
| 500 | Internal Server Error |
"""

    elif template_id == "user_guide":
        content = f"""# {title} User Guide

{description}

## Getting Started

Welcome to {title}! This guide will help you get up and running quickly.

## System Requirements

- Operating System: Windows 10+, macOS 10.14+, or Linux
- Memory: 4GB RAM minimum (8GB recommended)
- Storage: 500MB available space

## Installation

### Step 1: Download the Application
Visit our download page and select the appropriate version for your operating system.

### Step 2: Install the Application
Follow the installation wizard instructions for your platform.

### Step 3: Initial Setup
Launch the application and complete the initial setup wizard.

## Key Features
"""
        for feature in features[:3]:
            if feature.strip():
                content += f"\n### {feature.strip()}\n"
                content += f"Description of how to use {feature.strip().lower()}.\n"

        content += """
## Troubleshooting

### Common Issues

**Issue:** Application won't start
**Solution:** Check that all system requirements are met and try reinstalling.

**Issue:** Performance is slow
**Solution:** Close unnecessary applications and check available memory.

## Support

For additional help, please contact support@example.com or visit our support forum.
"""

    else:
        # Generic template
        content = f"""# {title}

{description}

## Overview

This document provides information about {title}.

## Features
"""
        for feature in features[:5]:
            if feature.strip():
                content += f"- {feature.strip()}\n"

        content += """

## Getting Started

1. Review the documentation
2. Follow the setup instructions
3. Begin using the system

## Additional Information

For more details, please refer to the complete documentation.

---
*Generated by DevDocAI v3.0.0*
"""

    return content


def generate_simulated_content(template_id: str, context: Dict[str, Any]) -> str:
    """Generate simulated AI-powered content"""
    # This would normally call the actual AI generator
    # For testing, we'll enhance the demo content slightly
    demo = generate_demo_content(template_id, context)

    # Add AI-enhanced tag
    enhanced = demo.replace(
        "*Generated by DevDocAI v3.0.0*", "*Generated by DevDocAI v3.0.0 with AI Enhancement*"
    )

    return enhanced


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
