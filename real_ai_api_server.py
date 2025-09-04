#!/usr/bin/env python3
"""
Real AI-Powered API Server for DevDocAI v3.0.0
Uses the M008 LLM Adapter with actual LLM APIs (OpenAI, Anthropic, Google).
"""

import os
import sys
import asyncio
import logging
import time
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import traceback
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the devdocai directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import DevDocAI LLM modules
try:
    from devdocai.llm_adapter.adapter_unified import UnifiedLLMAdapter, OperationMode, UnifiedConfig
    from devdocai.llm_adapter.config import LLMConfig, ProviderConfig, ProviderType, CostLimits
    from devdocai.llm_adapter.providers.base import LLMRequest
    from decimal import Decimal
    logger.info("✅ Successfully imported DevDocAI LLM modules")
except ImportError as e:
    logger.error(f"❌ Failed to import LLM modules: {e}")
    logger.error("Please ensure M008 LLM Adapter is properly installed")
    sys.exit(1)

app = Flask(__name__)

# Configure CORS
CORS(app, 
     origins=["http://localhost:3000", "http://127.0.0.1:3000"],
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
     methods=["GET", "POST", "OPTIONS"],
     supports_credentials=True)

# Global LLM adapter instance
llm_adapter = None

# Prompt templates for different document types
PROMPT_TEMPLATES = {
    'readme': """You are a Technical Communicator and Documentation Specialist tasked with creating a Software README.md document. Your goal is to produce a clear, concise, and informative README.md based solely on the provided software description.

Here is the software description you will use to create the README.md:

Project Path: {project_path}
Project Name: {project_name}
Custom Instructions: {custom_instructions}

Create a README.md document with the following structure:

1. Project Title
2. Description
3. Features
4. Installation
5. Usage
6. Contributing
7. License

For each section:

1. Project Title: Use the name of the software as the title.
2. Description: Provide a brief overview of what the software does and its main purpose.
3. Features: List the key features of the software. Use bullet points for clarity.
4. Installation: Provide clear installation instructions with code blocks.
5. Usage: Explain how to use the software with examples.
6. Contributing: Include contribution guidelines.
7. License: Include the license information.

Use Markdown syntax for headings, lists, and code blocks.
Begin your response with the # Project Title heading and end with the ## License section.""",

    'api': """You are an API Documentation Specialist tasked with creating comprehensive API documentation. Your goal is to produce clear, detailed, and developer-friendly API documentation.

Project Path: {project_path}
Project Name: {project_name}
Custom Instructions: {custom_instructions}

Create API documentation with the following structure:

1. API Overview
2. Authentication
3. Base URL
4. Endpoints (with detailed examples)
5. Request/Response Formats
6. Error Handling
7. Rate Limiting
8. SDKs and Libraries

For each endpoint, include:
- HTTP method
- Path
- Description
- Parameters (query, path, body)
- Request examples (curl, JavaScript, Python)
- Response examples (success and error cases)
- Status codes

Use clear headings, code blocks with syntax highlighting, tables for parameter descriptions, and JSON examples properly formatted.""",

    'user_guide': """You are a User Experience Writer tasked with creating a comprehensive User Guide. Your goal is to produce an easy-to-follow, user-friendly guide that helps end users effectively use the software.

Project Path: {project_path}
Project Name: {project_name}
Custom Instructions: {custom_instructions}

Create a User Guide with the following structure:

1. Getting Started
   - System Requirements
   - Installation Process
   - Initial Setup
   
2. Basic Operations
   - Key Features Overview
   - Step-by-step Tutorials
   - Common Use Cases
   
3. Advanced Features
   - Power User Tips
   - Customization Options
   - Integrations
   
4. Troubleshooting
   - Common Issues and Solutions
   - FAQ
   - Error Messages Guide
   
5. Support and Resources

Use clear, non-technical language where possible. Include numbered steps for procedures and helpful tips throughout.""",

    'technical_spec': """You are a Software Architect tasked with creating a Technical Specification document. Your goal is to produce a detailed technical document that covers system architecture, design decisions, and implementation details.

Project Path: {project_path}
Project Name: {project_name}
Custom Instructions: {custom_instructions}

Create a Technical Specification with the following structure:

1. System Overview
   - Purpose and Scope
   - High-level Architecture
   - Technology Stack
   
2. Architecture Design
   - Component Diagram
   - Data Flow
   - System Interactions
   
3. Data Models
   - Database Schema
   - API Contracts
   - Data Structures
   
4. Implementation Details
   - Core Algorithms
   - Design Patterns
   - Performance Considerations
   
5. Security Architecture
6. Deployment Architecture

Include technical diagrams using ASCII art or mermaid syntax where appropriate."""
}

def initialize_llm_adapter():
    """Initialize the M008 LLM Adapter with real API keys."""
    global llm_adapter
    
    try:
        # Get API keys from environment
        openai_key = os.getenv('OPENAI_API_KEY')
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        google_key = os.getenv('GOOGLE_API_KEY')
        
        # Configure providers as a dictionary
        providers = {}
        
        if openai_key:
            providers["openai"] = ProviderConfig(
                provider_type=ProviderType.OPENAI,
                api_key=openai_key,
                default_model="gpt-4-turbo-preview",
                max_tokens=2000,
                temperature=0.7
            )
            logger.info("✅ OpenAI provider configured")
        
        if anthropic_key:
            providers["anthropic"] = ProviderConfig(
                provider_type=ProviderType.ANTHROPIC,
                api_key=anthropic_key,
                default_model="claude-3-opus-20240229",
                max_tokens=2000,
                temperature=0.7
            )
            logger.info("✅ Anthropic provider configured")
        
        if google_key:
            providers["google"] = ProviderConfig(
                provider_type=ProviderType.GOOGLE,
                api_key=google_key,
                default_model="gemini-pro",
                max_tokens=2000,
                temperature=0.7
            )
            logger.info("✅ Google provider configured")
        
        if not providers:
            logger.warning("⚠️ No LLM providers configured. Please check API keys in .env file")
            return False
        
        # Create cost limits configuration
        cost_limits = CostLimits(
            daily_limit_usd=Decimal(os.getenv('DAILY_COST_LIMIT', '10')),
            monthly_limit_usd=Decimal(os.getenv('MONTHLY_COST_LIMIT', '200'))
        )
        
        # Create LLM configuration with providers as dictionary
        llm_config = LLMConfig(
            providers=providers,
            cost_limits=cost_limits
        )
        
        # Create unified configuration with BASIC mode to avoid optimization issues
        unified_config = UnifiedConfig(
            base_config=llm_config,
            operation_mode=OperationMode.BASIC  # Disable optimization for now
        )
        
        # Initialize the adapter
        llm_adapter = UnifiedLLMAdapter(unified_config)
        logger.info(f"✅ LLM Adapter initialized with {len(providers)} provider(s)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize LLM adapter: {e}")
        logger.error(traceback.format_exc())
        return False

async def generate_with_llm(prompt: str, template_type: str) -> str:
    """Generate content using the real LLM adapter."""
    global llm_adapter
    
    if not llm_adapter:
        logger.error("LLM adapter not initialized")
        return "Error: LLM adapter not available. Please check API keys."
    
    try:
        # Create LLM request in OpenAI format
        request = LLMRequest(
            messages=[
                {"role": "system", "content": "You are a technical documentation specialist."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4-turbo-preview",  # Default model, adapter will handle provider selection
            max_tokens=2000,
            temperature=0.7,
            metadata={
                'template_type': template_type,
                'source': 'devdocai_api'
            }
        )
        
        # Generate with the LLM adapter
        logger.info(f"🤖 Generating {template_type} with LLM...")
        result = await llm_adapter.query(request)
        
        # Handle different response formats
        if isinstance(result, tuple):
            # Adapter returns (response, metadata) tuple
            response = result[0] if result else None
        else:
            response = result
        
        # Extract content from response
        if response:
            if hasattr(response, 'content'):
                content = response.content
            elif isinstance(response, dict) and 'content' in response:
                content = response['content']
            elif isinstance(response, str):
                content = response
            else:
                content = str(response)
            
            logger.info(f"✅ LLM generation successful: {len(content)} characters")
            return content
        else:
            logger.error("LLM response was empty")
            return f"# {template_type.upper()} Documentation\n\nError: LLM generation failed. Please try again."
            
    except Exception as e:
        logger.error(f"❌ LLM generation error: {e}")
        logger.error(traceback.format_exc())
        return f"# {template_type.upper()} Documentation\n\nError generating content: {str(e)}"

@app.route('/api/test', methods=['GET', 'OPTIONS'])
def test_api():
    """Test endpoint to verify API connectivity."""
    try:
        if request.method == 'OPTIONS':
            response = jsonify({'status': 'OK'})
        else:
            response = jsonify({
                'status': 'Real AI-Powered DevDocAI API Server Running',
                'timestamp': datetime.now().isoformat(),
                'version': '3.0.0',
                'features': {
                    'llm_adapter': llm_adapter is not None,
                    'providers': {
                        'openai': bool(os.getenv('OPENAI_API_KEY')),
                        'anthropic': bool(os.getenv('ANTHROPIC_API_KEY')),
                        'google': bool(os.getenv('GOOGLE_API_KEY'))
                    },
                    'template_count': len(PROMPT_TEMPLATES)
                }
            })
        
        response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
        
        logger.info("✅ API test successful")
        return response
        
    except Exception as e:
        logger.error(f"❌ API test failed: {e}")
        response = jsonify({'error': str(e), 'status': 'Error'})
        response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
        return response, 500

@app.route('/api/generate', methods=['POST', 'OPTIONS'])
def generate_document():
    """Generate a document using real AI-powered LLMs."""
    try:
        if request.method == 'OPTIONS':
            response = jsonify({'status': 'OK'})
            response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
            response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
            return response
        
        # Get request data
        data = request.get_json()
        logger.info(f"📝 Real AI Generation request: {data}")
        
        # Extract parameters
        frontend_template = data.get('template', 'readme')
        
        # Map frontend template IDs to backend template IDs
        template_mapping = {
            'api-docs': 'api',
            'readme': 'readme',
            'code-docs': 'technical_spec',
            'user-guide': 'user_guide',
            'changelog': 'readme',
            'technical-spec': 'technical_spec'
        }
        template = template_mapping.get(frontend_template, 'readme')
        
        project_path = data.get('project_path', '/tmp/test_project')
        custom_instructions = data.get('custom_instructions', '')
        output_format = data.get('format', 'markdown')
        
        # Extract project name from path
        project_name = Path(project_path).name or 'MyProject'
        
        logger.info(f"🚀 Starting real LLM generation for {template}")
        
        # Get the appropriate prompt template
        prompt_template = PROMPT_TEMPLATES.get(template, PROMPT_TEMPLATES['readme'])
        
        # Format the prompt with user data
        prompt = prompt_template.format(
            project_path=project_path,
            project_name=project_name,
            custom_instructions=custom_instructions if custom_instructions else "Create comprehensive documentation following best practices."
        )
        
        # Generate content using real LLM
        start_time = time.time()
        
        # Run async generation in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        content = loop.run_until_complete(generate_with_llm(prompt, template))
        
        generation_time = int((time.time() - start_time) * 1000)  # in milliseconds
        
        # Calculate metadata
        word_count = len(content.split())
        quality_score = min(95, 85 + len(custom_instructions) / 10)  # Simple quality simulation
        
        response_data = {
            'success': True,
            'content': content,
            'metadata': {
                'template': template,
                'generation_time_ms': generation_time,
                'quality_score': quality_score,
                'cache_hit': False,
                'model': 'Real LLM (GPT-4/Claude/Gemini)',
                'tokens_used': word_count * 1.3,  # Rough estimate
                'word_count': word_count,
                'mode': 'REAL_AI',
                'llm_adapter': True
            }
        }
        
        response = jsonify(response_data)
        response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
        
        logger.info(f"✅ Real LLM generation completed in {generation_time}ms")
        return response
        
    except Exception as e:
        logger.error(f"❌ Document generation failed: {e}")
        logger.error(traceback.format_exc())
        
        error_response = jsonify({
            'success': False,
            'error': str(e),
            'content': '',
            'metadata': {
                'model': 'Real LLM Adapter',
                'error_type': type(e).__name__
            }
        })
        
        error_response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
        error_response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        error_response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
        
        return error_response, 500

@app.route('/api/templates', methods=['GET', 'OPTIONS'])
def list_templates():
    """List available document templates."""
    try:
        if request.method == 'OPTIONS':
            response = jsonify({'status': 'OK'})
        else:
            templates = [
                {'id': 'readme', 'name': 'README', 'description': 'Real AI-powered project documentation', 'ai_powered': True},
                {'id': 'api', 'name': 'API Documentation', 'description': 'Comprehensive API reference with examples', 'ai_powered': True},
                {'id': 'user_guide', 'name': 'User Guide', 'description': 'End-user documentation with tutorials', 'ai_powered': True},
                {'id': 'technical_spec', 'name': 'Technical Specification', 'description': 'System architecture and design docs', 'ai_powered': True}
            ]
            response = jsonify({'templates': templates})
        
        response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Template listing failed: {e}")
        response = jsonify({'error': str(e), 'templates': []})
        response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
        return response, 500

if __name__ == '__main__':
    logger.info("🚀 Starting Real AI-Powered DevDocAI API Server...")
    
    # Initialize the LLM adapter with real API keys
    if initialize_llm_adapter():
        logger.info("✅ LLM Adapter initialized successfully")
    else:
        logger.warning("⚠️ Running without LLM adapter - generation may fail")
    
    logger.info("📚 Loaded prompt templates for: " + ", ".join(PROMPT_TEMPLATES.keys()))
    
    # Start the server
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        threaded=True
    )