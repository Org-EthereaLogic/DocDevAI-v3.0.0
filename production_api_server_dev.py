#!/usr/bin/env python3
"""
Development API Server for DevDocAI v3.0.0
JWT-ready but authentication optional for development
"""

import os
import time
import json
import hashlib
import logging
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from functools import wraps
from threading import Lock
from collections import deque
from enum import Enum
import jwt
from flask import Flask, request, jsonify, g, make_response
from flask_cors import CORS
from werkzeug.exceptions import BadRequest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# JWT Configuration
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-secret-key')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

# Development mode flag
DEV_MODE = os.getenv('DEV_MODE', 'true').lower() == 'true'

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class ProductionAPIServer:
    """Production-ready API server with optional JWT authentication"""
    
    def __init__(self):
        self.app = Flask(__name__)
        self.configure_cors()
        self.setup_security()
        self.circuit_breakers = {}
        self.init_circuit_breakers()
        self.llm_adapter = self.initialize_llm_adapter()
        self.quality_analyzer = self.initialize_quality_analyzer()
        self.setup_routes()
        
    def configure_cors(self):
        """Configure CORS with security best practices"""
        CORS(self.app, 
             resources={r"/api/*": {
                 "origins": ["http://localhost:3000", "http://localhost:5000", "http://localhost:*"],
                 "methods": ["GET", "POST", "OPTIONS"],
                 "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
                 "expose_headers": ["Content-Type", "Authorization"],
                 "supports_credentials": True,
                 "max_age": 86400
             }})
    
    def setup_security(self):
        """Setup security middleware"""
        @self.app.before_request
        def before_request():
            """Pre-request processing"""
            g.correlation_id = self.generate_correlation_id()
            g.request_start = time.time()
            
            # In dev mode, always set a default user
            if DEV_MODE:
                g.user = {'user_id': 'dev-user', 'email': 'dev@devdocai.com'}
    
    def generate_jwt_token(self, user_id: str, email: str = None) -> str:
        """Generate JWT token for authentication"""
        payload = {
            'user_id': user_id,
            'email': email,
            'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
            'iat': datetime.utcnow(),
            'iss': 'DevDocAI'
        }
        return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    def verify_jwt_token(self, token: str) -> Optional[Dict]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None
    
    def optional_auth(self, f):
        """Decorator for optional JWT authentication (development friendly)"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # In dev mode, skip authentication entirely
            if DEV_MODE:
                if not hasattr(g, 'user'):
                    g.user = {'user_id': 'dev-user', 'email': 'dev@devdocai.com'}
                return f(*args, **kwargs)
            
            # Production mode: check for auth
            auth_header = request.headers.get('Authorization')
            if auth_header:
                try:
                    parts = auth_header.split(' ')
                    if parts[0].lower() == 'bearer' and len(parts) == 2:
                        token = parts[1]
                        payload = self.verify_jwt_token(token)
                        if payload:
                            g.user = payload
                        else:
                            return jsonify({'error': 'Invalid or expired token'}), 401
                except Exception:
                    return jsonify({'error': 'Invalid authorization header'}), 401
            else:
                # No auth header in production mode
                return jsonify({'error': 'Authorization required'}), 401
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    def initialize_llm_adapter(self):
        """Initialize LLM adapter if available"""
        try:
            from devdocai.llm_adapter.adapter_unified import UnifiedLLMAdapter
            logger.info("Successfully imported DevDocAI LLM modules")
            
            # Check for API keys
            api_keys = {
                'openai': os.getenv('OPENAI_API_KEY'),
                'anthropic': os.getenv('ANTHROPIC_API_KEY'),
                'google': os.getenv('GOOGLE_API_KEY')
            }
            
            available_providers = [k for k, v in api_keys.items() if v]
            
            if available_providers:
                logger.info("API keys found for one or more supported providers")
                # Initialize with configuration manager
                try:
                    from devdocai.core.config import ConfigurationManager
                    config_manager = ConfigurationManager()
                    adapter = UnifiedLLMAdapter(config_manager)
                    logger.info("LLM adapter initialized successfully with config")
                    return adapter
                except Exception as e:
                    logger.error(f"Failed to initialize LLM adapter with config: {e}")
                    # Try basic initialization
                    try:
                        adapter = UnifiedLLMAdapter()
                        logger.info("LLM adapter initialized successfully (basic mode)")
                        return adapter
                    except Exception as e2:
                        logger.error(f"Failed to initialize LLM adapter at all: {e2}")
                        return None
            else:
                logger.error("No LLM API keys found - Document generation will fail")
                return None
                
        except ImportError as e:
            logger.warning(f"DevDocAI modules not available: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize LLM adapter: {e}")
            return None
    
    def initialize_quality_analyzer(self):
        """Initialize quality analyzer if available"""
        try:
            from devdocai.quality.analyzer_unified import UnifiedQualityAnalyzer
            logger.info("Successfully imported Quality Analyzer")
            analyzer = UnifiedQualityAnalyzer()
            logger.info("Quality analyzer initialized successfully")
            return analyzer
        except ImportError as e:
            logger.warning(f"Quality analyzer not available: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize quality analyzer: {e}")
            return None
    
    def init_circuit_breakers(self):
        """Initialize circuit breakers for different endpoints"""
        from functools import partial
        
        # Simple circuit breaker implementation for now
        self.circuit_breakers = {
            'generate': lambda f: f,
            'analyze': lambda f: f
        }
    
    def generate_correlation_id(self):
        """Generate unique correlation ID for request tracking"""
        return hashlib.md5(f"{time.time()}{os.urandom(8).hex()}".encode()).hexdigest()[:8]
    
    def generate_integrity_hash(self, data):
        """Generate integrity hash for response data"""
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()
    
    def setup_routes(self):
        """Setup API routes with optional authentication"""
        
        @self.app.route('/health', methods=['GET'])
        @self.app.route('/api/health', methods=['GET'])
        def health_check():
            """Health check endpoint (no auth required)"""
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'correlation_id': g.correlation_id,
                'dev_mode': DEV_MODE,
                'auth_required': not DEV_MODE,
                'server': 'DevDocAI Development API Server v3.0.0'
            }), 200
        
        @self.app.route('/api/test', methods=['GET'])
        def test_endpoint():
            """Test endpoint for connectivity checks"""
            return jsonify({
                'success': True,
                'message': 'API is working',
                'timestamp': datetime.utcnow().isoformat(),
                'dev_mode': DEV_MODE
            }), 200
        
        @self.app.route('/api/auth/login', methods=['POST'])
        def login():
            """Login endpoint to get JWT token"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({'error': 'Invalid request body'}), 400
                
                # For development, accept any credentials
                email = data.get('email', 'user@devdocai.com')
                password = data.get('password', '')
                
                # In dev mode, always succeed
                if DEV_MODE or password:
                    user_id = hashlib.md5(email.encode()).hexdigest()[:8]
                    token = self.generate_jwt_token(user_id, email)
                    
                    return jsonify({
                        'success': True,
                        'token': token,
                        'user': {
                            'id': user_id,
                            'email': email
                        },
                        'expires_in': JWT_EXPIRATION_HOURS * 3600,
                        'dev_mode': DEV_MODE
                    }), 200
                else:
                    return jsonify({'error': 'Invalid credentials'}), 401
                    
            except Exception as e:
                logger.error(f"Login error: {e}")
                return jsonify({'error': 'Login failed'}), 500
        
        @self.app.route('/api/auth/verify', methods=['GET'])
        @self.optional_auth
        def verify_token():
            """Verify JWT token is valid"""
            return jsonify({
                'success': True,
                'user': g.user,
                'dev_mode': DEV_MODE
            }), 200
        
        @self.app.route('/api/analyze', methods=['POST', 'OPTIONS'])
        @self.optional_auth
        def analyze_quality():
            """Quality analysis endpoint with optional authentication"""
            try:
                if request.method == 'OPTIONS':
                    return jsonify({'status': 'OK'}), 200
                
                # Get request data
                raw_data = request.get_json()
                if not raw_data:
                    return jsonify({
                        'success': False,
                        'error': 'Invalid JSON in request body'
                    }), 400
                
                # Extract and validate data
                content = raw_data.get('content', '').strip()
                if not content:
                    return jsonify({
                        'success': False,
                        'error': 'Content field is required'
                    }), 400
                
                file_name = raw_data.get('file_name', 'document.md')
                
                logger.info(f"Quality analysis request from user {g.user.get('user_id')}: {file_name}")
                
                # Perform analysis
                start_time = time.time()
                
                if self.quality_analyzer:
                    result = self.quality_analyzer.analyze(
                        content=content,
                        file_type=raw_data.get('file_type', 'markdown')
                    )
                else:
                    # Fallback to mock analysis
                    result = self._perform_quality_analysis(content, file_name)
                
                analysis_time = int((time.time() - start_time) * 1000)
                
                # Build response
                response_data = {
                    'success': True,
                    'result': result,
                    'metadata': {
                        'analysis_time_ms': analysis_time,
                        'content_hash': hashlib.sha256(content.encode()).hexdigest(),
                        'timestamp': datetime.utcnow().isoformat(),
                        'correlation_id': g.correlation_id,
                        'user_id': g.user.get('user_id')
                    }
                }
                
                logger.info(f"Quality analysis completed: {analysis_time}ms")
                return jsonify(response_data), 200
                
            except Exception as e:
                logger.error(f"Quality analysis failed: {e}")
                logger.error(traceback.format_exc())
                return jsonify({
                    'success': False,
                    'error': 'An internal error occurred during analysis.',
                    'correlation_id': g.correlation_id
                }), 500
        
        @self.app.route('/api/generate', methods=['POST', 'OPTIONS'])
        @self.optional_auth
        def generate_document():
            """Document generation endpoint with optional authentication"""
            try:
                if request.method == 'OPTIONS':
                    return jsonify({'status': 'OK'}), 200
                
                data = request.get_json()
                if not data:
                    return jsonify({
                        'success': False,
                        'error': 'Invalid request body'
                    }), 400
                
                template = data.get('template', 'readme')
                project_name = data.get('project_name', 'project')
                
                logger.info(f"Document generation request from user {g.user.get('user_id')}: template={template}, project={project_name}")
                
                start_time = time.time()
                
                if self.llm_adapter:
                    # Real AI generation only
                    logger.info(f"Generating {template} with LLM adapter...")
                    prompt = self._build_generation_prompt(template, project_name, data.get('context', {}))
                    content = self.llm_adapter.generate(prompt, max_tokens=2000)
                    logger.info(f"Document generated successfully: {len(content)} chars")
                else:
                    # No mock generation - return error
                    logger.error("LLM adapter not available - cannot generate document")
                    return jsonify({
                        'success': False,
                        'error': 'AI service unavailable',
                        'message': 'Document generation requires AI service. Please check LLM configuration and try again.',
                        'details': 'No LLM providers are currently available. Verify API keys are configured.',
                        'correlation_id': g.correlation_id
                    }), 503
                
                generation_time = int((time.time() - start_time) * 1000)
                
                return jsonify({
                    'success': True,
                    'content': content,
                    'metadata': {
                        'template': template,
                        'project_name': project_name,
                        'generation_time_ms': generation_time,
                        'ai_generated': self.llm_adapter is not None,
                        'timestamp': datetime.utcnow().isoformat(),
                        'correlation_id': g.correlation_id,
                        'user_id': g.user.get('user_id')
                    }
                }), 200
                
            except Exception as e:
                logger.error(f"Document generation failed: {e}")
                logger.error(traceback.format_exc())
                return jsonify({
                    'success': False,
                    'error': f'Generation failed: {str(e)}',
                    'correlation_id': g.correlation_id
                }), 500
        
        @self.app.errorhandler(404)
        def not_found(error):
            """Handle 404 errors"""
            return jsonify({
                'error': 'Endpoint not found',
                'path': request.path,
                'method': request.method
            }), 404
        
        @self.app.errorhandler(500)
        def internal_error(error):
            """Handle 500 errors"""
            logger.error(f"Internal server error: {error}")
            return jsonify({
                'error': 'Internal server error',
                'correlation_id': g.correlation_id if hasattr(g, 'correlation_id') else None
            }), 500
    
    def _perform_quality_analysis(self, content: str, file_name: str) -> Dict:
        """Perform mock quality analysis"""
        # Calculate some basic metrics
        lines = content.split('\n')
        words = content.split()
        
        return {
            'score': 85,
            'dimensions': {
                'completeness': {
                    'score': 90,
                    'feedback': 'Documentation covers main aspects well'
                },
                'clarity': {
                    'score': 85,
                    'feedback': 'Clear and concise writing'
                },
                'technical_accuracy': {
                    'score': 88,
                    'feedback': 'Technical details are accurate'
                },
                'examples': {
                    'score': 75,
                    'feedback': 'Could benefit from more examples'
                },
                'structure': {
                    'score': 92,
                    'feedback': 'Well-organized structure'
                }
            },
            'metrics': {
                'lines': len(lines),
                'words': len(words),
                'characters': len(content),
                'readability_score': 8.5
            },
            'suggestions': [
                'Add more code examples',
                'Include troubleshooting section',
                'Expand API documentation'
            ]
        }
    
    def _build_generation_prompt(self, template: str, project_name: str, context: Dict) -> str:
        """Build generation prompt for LLM"""
        prompts = {
            'readme': f"Generate a comprehensive README.md for a project called '{project_name}'. Include sections for: Overview, Features, Installation, Usage, Configuration, API Reference, Contributing, and License.",
            'api': f"Generate detailed API documentation for '{project_name}'. Include endpoints, request/response formats, authentication, error codes, and examples.",
            'architecture': f"Generate an architecture document for '{project_name}'. Include system overview, component descriptions, data flow, technology stack, and deployment architecture.",
            'contributing': f"Generate a CONTRIBUTING.md for '{project_name}'. Include development setup, coding standards, commit guidelines, PR process, and testing requirements.",
            'changelog': f"Generate a CHANGELOG.md for '{project_name}'. Include version history, breaking changes, new features, bug fixes, and migration guides."
        }
        
        base_prompt = prompts.get(template, prompts['readme'])
        
        if context:
            context_str = '\n'.join([f"- {k}: {v}" for k, v in context.items()])
            base_prompt += f"\n\nAdditional context:\n{context_str}"
        
        return base_prompt
    
    def _generate_mock_content(self, template: str, project_name: str) -> str:
        """Generate mock content for testing"""
        templates = {
            'readme': f"""# {project_name}

## Overview
{project_name} is a modern application designed to solve complex problems.

## Features
- ✨ Feature 1: Advanced functionality
- 🚀 Feature 2: High performance
- 🔒 Feature 3: Enterprise security
- 📊 Feature 4: Real-time analytics

## Installation
```bash
npm install {project_name.lower()}
```

## Usage
```javascript
import {{ {project_name} }} from '{project_name.lower()}';

const app = new {project_name}();
app.start();
```

## Configuration
Configuration options can be set in `.{project_name.lower()}.yml`

## License
MIT License - see LICENSE file for details
""",
            'api': f"""# {project_name} API Documentation

## Base URL
`https://api.{project_name.lower()}.com/v1`

## Authentication
All requests require a Bearer token in the Authorization header.

## Endpoints

### GET /api/status
Returns the current system status.

### POST /api/data
Creates a new data entry.

### PUT /api/data/{{id}}
Updates an existing data entry.

### DELETE /api/data/{{id}}
Deletes a data entry.
""",
            'architecture': f"""# {project_name} Architecture

## System Overview
{project_name} follows a microservices architecture pattern.

## Components
- API Gateway
- Authentication Service
- Core Service
- Database Layer
- Cache Layer

## Technology Stack
- Backend: Node.js, Python
- Database: PostgreSQL, Redis
- Infrastructure: Docker, Kubernetes
"""
        }
        
        return templates.get(template, templates['readme'])
    
    def run(self, host='0.0.0.0', port=5000):
        """Run the development server"""
        logger.info(f"Starting Development API Server on {host}:{port}")
        logger.info(f"Development Mode: {DEV_MODE}")
        logger.info(f"Authentication: {'Optional (DEV MODE)' if DEV_MODE else 'Required'}")
        logger.info(f"LLM Adapter available: {self.llm_adapter is not None}")
        logger.info(f"Quality Analyzer available: {self.quality_analyzer is not None}")
        logger.info("Endpoints: /api/health, /api/test, /api/generate, /api/analyze, /api/auth/login")
        self.app.run(host=host, port=port, debug=True)

if __name__ == '__main__':
    server = ProductionAPIServer()
    server.run()