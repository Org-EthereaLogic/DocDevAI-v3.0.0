#!/usr/bin/env python3
"""
Production-Ready API Server for DevDocAI v3.0.0
Enterprise-grade reliability with fault tolerance, circuit breakers, and comprehensive monitoring
"""

def safe_error_response(error, status_code=500):
    """Return sanitized error response to prevent information disclosure."""
    import logging
    from flask import jsonify
    
    # Log full error details internally
    logging.error(f"API Error: {error}", exc_info=True)
    
    # Generic error messages for clients
    error_messages = {
        400: "Invalid request",
        401: "Authentication required",
        403: "Access denied",
        404: "Resource not found",
        405: "Method not allowed",
        422: "Validation failed",
        429: "Too many requests",
        500: "Internal server error",
        502: "Service temporarily unavailable",
        503: "Service unavailable"
    }
    
    return jsonify({
        'success': False,
        'error': error_messages.get(status_code, "An error occurred"),
        'status_code': status_code
    }), status_code


import os
import sys
import asyncio
import logging
import time
import threading
import signal
from pathlib import Path
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from datetime import datetime, timedelta
import traceback
import json
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from functools import wraps
import hashlib
import hmac
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
import uuid

# Load environment variables
load_dotenv()

# Add the devdocai directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Configure structured logging with correlation IDs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s'
)

class CorrelationFilter(logging.Filter):
    """Add correlation ID to log records for request tracing"""
    def filter(self, record):
        try:
            from flask import has_request_context
            if has_request_context():
                record.correlation_id = getattr(g, 'correlation_id', 'no-request')
            else:
                record.correlation_id = 'startup'
        except:
            record.correlation_id = 'system'
        return True

logger = logging.getLogger(__name__)
logger.addFilter(CorrelationFilter())

# Import DevDocAI LLM modules with fallback handling
try:
    from devdocai.llm_adapter.adapter_unified import UnifiedLLMAdapter, OperationMode, UnifiedConfig
    from devdocai.llm_adapter.config import LLMConfig, ProviderConfig, ProviderType, CostLimits
    from devdocai.llm_adapter.providers.base import LLMRequest
    from decimal import Decimal
    logger.info("Successfully imported DevDocAI LLM modules")
    LLM_AVAILABLE = True
except ImportError as e:
    logger.warning(f"LLM modules not available: {e}. Running in fallback mode.")
    LLM_AVAILABLE = False

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failures detected, blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5      # Failures before opening
    success_threshold: int = 3      # Successes to close from half-open
    timeout_seconds: int = 60       # Time before moving to half-open
    reset_timeout_seconds: int = 30 # Time before resetting counters

@dataclass 
class HealthMetrics:
    """Health and performance metrics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    last_failure_time: Optional[datetime] = None
    circuit_state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    response_times: deque = field(default_factory=lambda: deque(maxlen=100))
    
class CircuitBreaker:
    """Production-grade circuit breaker implementation"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.metrics = HealthMetrics()
        self._lock = threading.RLock()
        self._last_state_change = datetime.utcnow()
        
    def __call__(self, func):
        """Decorator for circuit breaker protection"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self._execute(func, *args, **kwargs)
        return wrapper
    
    def _execute(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        with self._lock:
            if not self._should_allow_request():
                logger.warning(f"Circuit breaker {self.name} is OPEN - blocking request")
                raise Exception(f"Circuit breaker {self.name} is open - service temporarily unavailable")
        
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            self._record_success(time.time() - start_time)
            return result
        except Exception as e:
            self._record_failure(time.time() - start_time, str(e))
            raise
    
    def _should_allow_request(self) -> bool:
        """Determine if request should be allowed based on circuit state"""
        current_time = datetime.utcnow()
        
        if self.metrics.circuit_state == CircuitState.CLOSED:
            return True
        elif self.metrics.circuit_state == CircuitState.OPEN:
            # Check if timeout period has passed
            if (current_time - self._last_state_change).total_seconds() >= self.config.timeout_seconds:
                self._transition_to_half_open()
                return True
            return False
        elif self.metrics.circuit_state == CircuitState.HALF_OPEN:
            return True
        
        return False
    
    def _record_success(self, response_time: float):
        """Record successful operation"""
        with self._lock:
            self.metrics.total_requests += 1
            self.metrics.successful_requests += 1
            self.metrics.response_times.append(response_time)
            self._update_avg_response_time()
            
            if self.metrics.circuit_state == CircuitState.HALF_OPEN:
                self.metrics.consecutive_successes += 1
                if self.metrics.consecutive_successes >= self.config.success_threshold:
                    self._transition_to_closed()
            elif self.metrics.circuit_state == CircuitState.CLOSED:
                self.metrics.consecutive_failures = 0
                
    def _record_failure(self, response_time: float, error: str):
        """Record failed operation"""
        with self._lock:
            self.metrics.total_requests += 1
            self.metrics.failed_requests += 1
            self.metrics.last_failure_time = datetime.utcnow()
            self.metrics.response_times.append(response_time)
            self._update_avg_response_time()
            
            if self.metrics.circuit_state in [CircuitState.CLOSED, CircuitState.HALF_OPEN]:
                self.metrics.consecutive_failures += 1
                self.metrics.consecutive_successes = 0
                
                if self.metrics.consecutive_failures >= self.config.failure_threshold:
                    self._transition_to_open()
                    
            logger.error(f"Circuit breaker {self.name} recorded failure: {error}")
    
    def _update_avg_response_time(self):
        """Update average response time from recent samples"""
        if self.metrics.response_times:
            self.metrics.avg_response_time = sum(self.metrics.response_times) / len(self.metrics.response_times)
    
    def _transition_to_open(self):
        """Transition circuit breaker to OPEN state"""
        self.metrics.circuit_state = CircuitState.OPEN
        self._last_state_change = datetime.utcnow()
        logger.warning(f"Circuit breaker {self.name} transitioned to OPEN state")
    
    def _transition_to_half_open(self):
        """Transition circuit breaker to HALF_OPEN state"""
        self.metrics.circuit_state = CircuitState.HALF_OPEN
        self._last_state_change = datetime.utcnow()
        self.metrics.consecutive_successes = 0
        logger.info(f"Circuit breaker {self.name} transitioned to HALF_OPEN state")
    
    def _transition_to_closed(self):
        """Transition circuit breaker to CLOSED state"""
        self.metrics.circuit_state = CircuitState.CLOSED
        self._last_state_change = datetime.utcnow()
        self.metrics.consecutive_failures = 0
        self.metrics.consecutive_successes = 0
        logger.info(f"Circuit breaker {self.name} transitioned to CLOSED state")

class RateLimiter:
    """Token bucket rate limiter"""
    
    def __init__(self, requests_per_minute: int = 100):
        self.requests_per_minute = requests_per_minute
        self.bucket_size = requests_per_minute
        self.tokens = requests_per_minute
        self.last_refill = time.time()
        self._lock = threading.RLock()
    
    def is_allowed(self, tokens_requested: int = 1) -> bool:
        """Check if request is allowed under rate limit"""
        with self._lock:
            self._refill_bucket()
            if self.tokens >= tokens_requested:
                self.tokens -= tokens_requested
                return True
            return False
    
    def _refill_bucket(self):
        """Refill token bucket based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_refill
        tokens_to_add = (elapsed / 60.0) * self.requests_per_minute
        self.tokens = min(self.bucket_size, self.tokens + tokens_to_add)
        self.last_refill = now

class APIValidator:
    """Request/Response validation with data integrity checks"""
    
    @staticmethod
    def validate_analyze_request(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate analyze request with comprehensive checks"""
        if not isinstance(data, dict):
            raise ValueError("Request body must be a JSON object")
        
        # Required fields
        content = data.get('content', '').strip()
        if not content:
            raise ValueError("Content field is required and cannot be empty")
        
        if len(content) > 50000:  # 50KB limit
            raise ValueError("Content exceeds maximum length of 50,000 characters")
        
        # Optional fields with validation
        file_name = data.get('file_name', 'document.md')
        if not isinstance(file_name, str) or len(file_name) > 255:
            raise ValueError("File name must be a string with max 255 characters")
        
        # Sanitize file name
        file_name = ''.join(c for c in file_name if c.isalnum() or c in '._-')
        if not file_name:
            file_name = 'document.md'
        
        return {
            'content': content,
            'file_name': file_name,
            'content_hash': hashlib.sha256(content.encode()).hexdigest()
        }
    
    @staticmethod
    def validate_response_integrity(response_data: Dict[str, Any], request_hash: str) -> bool:
        """Validate response data integrity"""
        try:
            # Check required response fields
            required_fields = ['success', 'result']
            for field in required_fields:
                if field not in response_data:
                    logger.error(f"Missing required response field: {field}")
                    return False
            
            # Verify result structure if successful
            if response_data.get('success') and response_data.get('result'):
                result = response_data['result']
                required_result_fields = ['id', 'fileName', 'overallScore', 'scores', 'status']
                for field in required_result_fields:
                    if field not in result:
                        logger.error(f"Missing required result field: {field}")
                        return False
            
            # Add integrity hash to response
            response_data['integrity_hash'] = hashlib.sha256(
                (str(response_data.get('result', '')) + request_hash).encode()
            ).hexdigest()
            
            return True
        except Exception as e:
            logger.error(f"Response validation error: {e}")
            return False

class ProductionAPIServer:
    """Production-ready API server with enterprise reliability features"""
    
    def __init__(self):
        self.app = Flask(__name__)
        self.llm_adapter = None
        self.circuit_breakers = {}
        self.rate_limiters = defaultdict(lambda: RateLimiter())
        self.request_metrics = defaultdict(int)
        self.startup_time = datetime.utcnow()
        
        self._setup_cors()
        self._setup_middleware()
        self._setup_routes()
        self._setup_circuit_breakers()
        self._setup_health_monitoring()
        
        if LLM_AVAILABLE:
            self._initialize_llm_adapter()
    
    def _setup_cors(self):
        """Configure production-ready CORS with comprehensive preflight handling"""
        CORS(self.app, 
             origins=[
                 "http://localhost:3000", 
                 "http://127.0.0.1:3000",
                 "http://localhost:8080",
                 "http://127.0.0.1:8080"
             ],
             allow_headers=[
                 "Content-Type", 
                 "Authorization", 
                 "X-Requested-With",
                 "X-Correlation-ID",
                 "X-API-Key",
                 "Accept",
                 "Origin",
                 "Cache-Control"
             ],
             methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"],
             supports_credentials=True,
             max_age=86400,  # 24 hours for preflight caching
             vary_header=True)
    
    def _setup_middleware(self):
        """Setup middleware for correlation, rate limiting, and monitoring"""
        
        @self.app.before_request
        def before_request():
            # Generate correlation ID for request tracing
            g.correlation_id = request.headers.get('X-Correlation-ID', str(uuid.uuid4())[:8])
            g.start_time = time.time()
            
            # Rate limiting check
            client_ip = request.environ.get('REMOTE_ADDR', 'unknown')
            if not self.rate_limiters[client_ip].is_allowed():
                logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                response = jsonify({
                    'success': False,
                    'error': 'Rate limit exceeded. Please try again later.',
                    'retry_after': 60
                })
                response.status_code = 429
                response.headers['Retry-After'] = '60'
                return response
        
        @self.app.after_request
        def after_request(response):
            # Add security and CORS headers
            response.headers['X-Correlation-ID'] = getattr(g, 'correlation_id', 'unknown')
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            
            # Comprehensive CORS headers for all responses
            response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', 'http://localhost:3000')
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, PUT, DELETE'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, X-Correlation-ID, X-API-Key, Accept, Origin, Cache-Control'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Max-Age'] = '86400'
            response.headers['Vary'] = 'Origin, Access-Control-Request-Headers, Access-Control-Request-Method'
            
            # Log request metrics
            if hasattr(g, 'start_time'):
                duration = (time.time() - g.start_time) * 1000  # milliseconds
                logger.info(f"Request completed: {request.method} {request.path} - {response.status_code} - {duration:.2f}ms")
            
            return response
        
        @self.app.errorhandler(Exception)
        def handle_exception(e):
            """Global exception handler with correlation tracking"""
            correlation_id = getattr(g, 'correlation_id', 'unknown')
            logger.error(f"Unhandled exception: {e}", extra={'correlation_id': correlation_id})
            logger.error(traceback.format_exc())
            
            response = jsonify({
                'success': False,
                'error': 'Internal server error occurred',
                'correlation_id': correlation_id,
                'timestamp': datetime.utcnow().isoformat()
            })
            response.status_code = 500
            return response
    
    def _setup_routes(self):
        """Setup API routes with comprehensive error handling"""
        
        @self.app.route('/api/health', methods=['GET', 'OPTIONS'])
        def health_check():
            """Comprehensive health check endpoint"""
            if request.method == 'OPTIONS':
                return jsonify({'status': 'OK'}), 200
            
            uptime = (datetime.utcnow() - self.startup_time).total_seconds()
            
            # Aggregate circuit breaker states
            circuit_states = {name: cb.metrics.circuit_state.value 
                            for name, cb in self.circuit_breakers.items()}
            
            health_data = {
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'uptime_seconds': uptime,
                'version': '3.0.0',
                'features': {
                    'llm_adapter': self.llm_adapter is not None,
                    'circuit_breakers': circuit_states,
                    'rate_limiting': True,
                    'cors': True,
                    'request_validation': True
                },
                'metrics': {
                    'total_requests': sum(cb.metrics.total_requests for cb in self.circuit_breakers.values()),
                    'success_rate': self._calculate_overall_success_rate(),
                    'avg_response_time': self._calculate_avg_response_time()
                }
            }
            
            # Determine overall health status
            unhealthy_circuits = [name for name, cb in self.circuit_breakers.items() 
                                if cb.metrics.circuit_state == CircuitState.OPEN]
            
            if unhealthy_circuits:
                health_data['status'] = 'degraded'
                health_data['unhealthy_services'] = unhealthy_circuits
                return jsonify(health_data), 503
            
            return jsonify(health_data), 200
        
        @self.app.route('/api/test', methods=['GET', 'OPTIONS'])
        def test_connection():
            """Simple test endpoint for frontend connectivity checks"""
            if request.method == 'OPTIONS':
                return jsonify({'status': 'OK'}), 200
            
            return jsonify({
                'success': True,
                'message': 'API connection successful',
                'timestamp': datetime.utcnow().isoformat(),
                'server': 'DevDocAI Production API Server v3.0.0'
            }), 200
        
        @self.app.route('/api/analyze', methods=['POST', 'OPTIONS'])
        @self.circuit_breakers.get('analyze', CircuitBreaker('analyze'))
        def analyze_quality():
            """Production-ready quality analysis with comprehensive reliability"""
            try:
                if request.method == 'OPTIONS':
                    return jsonify({'status': 'OK'}), 200
                
                # Validate request
                raw_data = request.get_json()
                if not raw_data:
                    return jsonify({
                        'success': False,
                        'error': 'Invalid JSON in request body'
                    }), 400
                
                validated_data = APIValidator.validate_analyze_request(raw_data)
                logger.info(f"Quality analysis request validated: {validated_data['file_name']} ({len(validated_data['content'])} chars)")
                
                # Perform analysis
                start_time = time.time()
                analysis_result = self._perform_quality_analysis(
                    validated_data['content'],
                    validated_data['file_name']
                )
                analysis_time = int((time.time() - start_time) * 1000)
                
                # Build response
                response_data = {
                    'success': True,
                    'result': analysis_result,
                    'metadata': {
                        'analysis_time_ms': analysis_time,
                        'content_hash': validated_data['content_hash'],
                        'timestamp': datetime.utcnow().isoformat(),
                        'correlation_id': g.correlation_id
                    }
                }
                
                # Validate response integrity
                if not APIValidator.validate_response_integrity(response_data, validated_data['content_hash']):
                    raise Exception("Response validation failed")
                
                logger.info(f"Quality analysis completed successfully: {analysis_time}ms")
                return jsonify(response_data), 200
                
            except ValueError as e:
                logger.warning(f"Validation error: {e}")
                return jsonify({
                    'success': False,
                    'error': safe_error_response(e)[0].json['error'],
                    'error_type': 'validation_error'
                }), 400
                
            except Exception as e:
                logger.error(f"Quality analysis failed: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Analysis service temporarily unavailable',
                    'error_type': 'service_error',
                    'correlation_id': getattr(g, 'correlation_id', 'unknown')
                }), 503
        
        @self.app.route('/api/generate', methods=['POST', 'OPTIONS'])
        @self.circuit_breakers.get('generate', CircuitBreaker('generate'))
        def generate_document():
            """Generate AI-powered documentation with template support"""
            try:
                if request.method == 'OPTIONS':
                    return jsonify({'status': 'OK'}), 200
                
                # Get request data
                data = request.get_json()
                if not data:
                    return jsonify({
                        'success': False,
                        'error': 'Invalid JSON in request body'
                    }), 400
                
                # Extract parameters
                frontend_template = data.get('template', 'prd')
                project_path = data.get('project_path', '/tmp/project')
                custom_instructions = data.get('custom_instructions', '')
                output_format = data.get('format', 'markdown')
                
                # Map frontend template IDs to prompt template names
                template_mapping = {
                    'prd': 'prd_generation',
                    'wbs': 'wbs_generation', 
                    'srs': 'software_requirements_generation',
                    'architecture': 'architecture_blueprint_generation',
                    # Legacy mappings for backward compatibility
                    'api-docs': 'api_documentation',
                    'readme': 'readme_generation',
                    'code-docs': 'code_documentation',
                    'user-guide': 'user_guide',
                    'changelog': 'changelog',
                    'technical-spec': 'technical_specification'
                }
                
                template_name = template_mapping.get(frontend_template, 'prd_generation')
                project_name = Path(project_path).name or 'Project'
                
                logger.info(f"Document generation request: template={template_name}, project={project_name}")
                
                # Check if LLM adapter is available
                if not self.llm_adapter:
                    # Return mock content for testing
                    logger.warning("LLM adapter not available, returning mock content")
                    mock_content = f"""# {project_name} - {frontend_template.upper()}
                    
> Generated by DevDocAI v3.0.0

## Project: {project_path}

{custom_instructions if custom_instructions else 'This is a mock document generated for testing purposes.'}

### Note
This is sample content. To generate real AI-powered documentation:
1. Configure your API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, or GOOGLE_API_KEY)
2. Restart the API server
3. Try generating again

---
*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"""
                    
                    return jsonify({
                        'success': True,
                        'content': mock_content,
                        'metadata': {
                            'template': frontend_template,
                            'generation_time_ms': 100,
                            'ai_powered': False,
                            'word_count': len(mock_content.split()),
                            'timestamp': datetime.utcnow().isoformat()
                        }
                    }), 200
                
                # Generate real AI content
                start_time = time.time()
                
                # Create the prompt for AI generation
                system_prompt = """You are an expert technical documentation specialist. 
                Generate comprehensive, professional documentation that follows industry best practices.
                Focus on clarity, completeness, and practical value for developers."""
                
                user_prompt = f"""Generate a {template_name.replace('_', ' ').title()} for the following project:

Project Name: {project_name}
Project Path: {project_path}
Document Type: {frontend_template.upper()}

{f"Additional Requirements: {custom_instructions}" if custom_instructions else "Follow standard best practices for this document type."}

Generate a complete, professional document with all appropriate sections."""
                
                # Create LLM request
                llm_request = LLMRequest(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    model="gpt-4-turbo",  # Default model, adapter will handle provider selection
                    max_tokens=4000,  # Reduced to work with both OpenAI and Claude
                    temperature=0.7,
                    metadata={
                        'template': template_name,
                        'project': project_name,
                        'source': 'devdocai_generate'
                    }
                )
                
                # Generate with LLM adapter
                logger.info(f"Generating {template_name} with LLM adapter...")
                result = asyncio.run(self.llm_adapter.query(llm_request))
                
                # Extract content from response
                content = ""
                if result:
                    if isinstance(result, tuple):
                        response = result[0] if result else None
                    else:
                        response = result
                    
                    if response:
                        if hasattr(response, 'content'):
                            content = response.content
                        elif isinstance(response, dict) and 'content' in response:
                            content = response['content']
                        elif isinstance(response, str):
                            content = response
                        else:
                            content = str(response)
                
                if not content:
                    raise Exception("LLM generation returned empty content")
                
                generation_time = int((time.time() - start_time) * 1000)
                logger.info(f"Document generated successfully: {len(content)} chars in {generation_time}ms")
                
                return jsonify({
                    'success': True,
                    'content': content,
                    'metadata': {
                        'template': frontend_template,
                        'generation_time_ms': generation_time,
                        'ai_powered': True,
                        'word_count': len(content.split()),
                        'quality_score': min(95, 85 + len(custom_instructions) / 20),
                        'timestamp': datetime.utcnow().isoformat(),
                        'correlation_id': g.correlation_id
                    }
                }), 200
                
            except Exception as e:
                logger.error(f"Document generation failed: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Generation service temporarily unavailable',
                    'error_type': 'generation_error',
                    'correlation_id': getattr(g, 'correlation_id', 'unknown')
                }), 503
    
    def _setup_circuit_breakers(self):
        """Initialize circuit breakers for different services"""
        self.circuit_breakers['analyze'] = CircuitBreaker('analyze')
        self.circuit_breakers['generate'] = CircuitBreaker('generate')
        self.circuit_breakers['llm'] = CircuitBreaker('llm', 
            CircuitBreakerConfig(failure_threshold=3, timeout_seconds=120))
    
    def _setup_health_monitoring(self):
        """Setup background health monitoring"""
        def monitor_health():
            while True:
                try:
                    time.sleep(30)  # Check every 30 seconds
                    self._log_health_metrics()
                except Exception as e:
                    logger.error(f"Health monitoring error: {e}")
        
        monitor_thread = threading.Thread(target=monitor_health, daemon=True)
        monitor_thread.start()
    
    def _initialize_llm_adapter(self):
        """Initialize LLM adapter with fault tolerance"""
        try:
            # Get API keys from environment
            providers = {}
            
            openai_key = os.getenv('OPENAI_API_KEY')
            if openai_key:
                providers["openai"] = ProviderConfig(
                    provider_type=ProviderType.OPENAI,
                    api_key=openai_key,
                    default_model="gpt-4-turbo",
                    max_tokens=4000,
                    temperature=0.7
                )
            
            anthropic_key = os.getenv('ANTHROPIC_API_KEY')
            if anthropic_key:
                providers["anthropic"] = ProviderConfig(
                    provider_type=ProviderType.ANTHROPIC,
                    api_key=anthropic_key,
                    default_model="claude-3-opus-20240229",
                    max_tokens=4000,
                    temperature=0.7
                )
            
            if providers:
                cost_limits = CostLimits(
                    daily_limit_usd=Decimal('10'),
                    monthly_limit_usd=Decimal('200')
                )
                
                llm_config = LLMConfig(providers=providers, cost_limits=cost_limits)
                unified_config = UnifiedConfig(base_config=llm_config, operation_mode=OperationMode.BASIC)
                
                self.llm_adapter = UnifiedLLMAdapter(unified_config)
                logger.info(f"LLM Adapter initialized with {len(providers)} provider(s)")
                return True
            else:
                logger.warning("No LLM providers configured")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize LLM adapter: {e}")
            return False
    
    @CircuitBreaker('quality_analysis')
    def _perform_quality_analysis(self, content: str, file_name: str) -> Dict[str, Any]:
        """Perform quality analysis with circuit breaker protection"""
        # Quality dimensions for analysis
        dimensions = ['Completeness', 'Clarity', 'Structure', 'Examples', 'Accessibility']
        
        analysis_result = {
            'id': str(int(time.time() * 1000)),
            'fileName': file_name,
            'analysisDate': datetime.utcnow().isoformat(),
            'status': 'complete',
            'scores': [],
            'overallScore': 0
        }
        
        scores = []
        for dimension in dimensions:
            # Simple scoring based on content characteristics
            base_score = self._calculate_dimension_score(content, dimension)
            
            # Generate AI suggestions if available
            suggestions = []
            if self.llm_adapter:
                try:
                    suggestions = asyncio.run(self._generate_ai_suggestions(content, dimension, base_score))
                except Exception as e:
                    logger.warning(f"AI suggestion generation failed for {dimension}: {e}")
                    suggestions = [f"Consider improving {dimension.lower()} aspects", 
                                 f"Review {dimension.lower()} best practices"]
            
            scores.append({
                'dimension': dimension,
                'score': base_score,
                'maxScore': 100,
                'issues': [],
                'suggestions': suggestions[:3]  # Limit to top 3 suggestions
            })
        
        # Calculate overall score
        overall_score = sum(score['score'] for score in scores) / len(scores)
        
        analysis_result['scores'] = scores
        analysis_result['overallScore'] = round(overall_score, 2)
        
        return analysis_result
    
    def _calculate_dimension_score(self, content: str, dimension: str) -> float:
        """Calculate dimension score based on content analysis"""
        base_score = 60  # Minimum base score
        
        # Content length factor (up to +20 points)
        length_bonus = min(20, len(content) / 100)
        
        # Dimension-specific scoring
        if dimension == 'Structure':
            # Check for headers, lists, paragraphs
            headers = content.count('#')
            lists = content.count('-') + content.count('*')
            structure_bonus = min(15, (headers * 3) + (lists * 0.5))
        elif dimension == 'Examples':
            # Check for code blocks, examples
            code_blocks = content.count('```') + content.count('`')
            examples_bonus = min(15, code_blocks * 2)
        elif dimension == 'Completeness':
            # Based on content depth
            sentences = content.count('.') + content.count('!') + content.count('?')
            completeness_bonus = min(15, sentences * 0.5)
        else:
            # Default scoring
            words = len(content.split())
            default_bonus = min(15, words / 20)
        
        dimension_bonus = locals().get(f'{dimension.lower()}_bonus', 10)
        
        return min(100, base_score + length_bonus + dimension_bonus)
    
    async def _generate_ai_suggestions(self, content: str, dimension: str, score: float) -> List[str]:
        """Generate AI-powered suggestions with circuit breaker protection"""
        if not self.llm_adapter:
            return []
        
        try:
            prompt = f"""Analyze this documentation and provide 2-3 specific, actionable suggestions to improve {dimension}.

Current {dimension} score: {score}/100

Document content (first 500 chars):
{content[:500]}...

Provide exactly 2-3 specific suggestions. Each should:
1. Reference a specific section or aspect
2. Describe exactly what to add or change
3. Be actionable and clear

Format as a simple list with dashes (-).
Focus specifically on {dimension.lower()}."""

            request = LLMRequest(
                messages=[
                    {"role": "system", "content": "You are a technical documentation expert."},
                    {"role": "user", "content": prompt}
                ],
                model="gpt-4-turbo-preview",
                max_tokens=200,
                temperature=0.3
            )
            
            result = await self.llm_adapter.query(request)
            
            if result:
                response = result[0] if isinstance(result, tuple) else result
                content_text = response.content if hasattr(response, 'content') else str(response)
                
                # Parse suggestions
                suggestions = []
                for line in content_text.split('\n'):
                    line = line.strip()
                    if line and line.startswith(('-', '•', '*')):
                        suggestion = line.lstrip('-•* ').strip()
                        if suggestion:
                            suggestions.append(suggestion)
                
                return suggestions[:3]
            
        except Exception as e:
            logger.error(f"AI suggestion generation error: {e}")
            # Circuit breaker will handle this failure
            raise
        
        return []
    
    def _calculate_overall_success_rate(self) -> float:
        """Calculate overall success rate across all circuit breakers"""
        total_requests = sum(cb.metrics.total_requests for cb in self.circuit_breakers.values())
        successful_requests = sum(cb.metrics.successful_requests for cb in self.circuit_breakers.values())
        
        if total_requests == 0:
            return 100.0
        
        return round((successful_requests / total_requests) * 100, 2)
    
    def _calculate_avg_response_time(self) -> float:
        """Calculate average response time across all services"""
        all_times = []
        for cb in self.circuit_breakers.values():
            all_times.extend(cb.metrics.response_times)
        
        if not all_times:
            return 0.0
        
        return round(sum(all_times) / len(all_times) * 1000, 2)  # Convert to ms
    
    def _log_health_metrics(self):
        """Log health metrics for monitoring"""
        metrics = {
            'circuit_breakers': {name: {
                'state': cb.metrics.circuit_state.value,
                'total_requests': cb.metrics.total_requests,
                'success_rate': round((cb.metrics.successful_requests / max(1, cb.metrics.total_requests)) * 100, 2),
                'avg_response_time': round(cb.metrics.avg_response_time * 1000, 2)
            } for name, cb in self.circuit_breakers.items()},
            'overall_success_rate': self._calculate_overall_success_rate(),
            'avg_response_time_ms': self._calculate_avg_response_time()
        }
        
        logger.info(f"Health metrics: {json.dumps(metrics)}")
    
    def run(self, host='0.0.0.0', port=5000, debug=False):
        """Run the production server"""
        logger.info(f"Starting Production API Server on {host}:{port}")
        logger.info(f"LLM Adapter available: {self.llm_adapter is not None}")
        logger.info(f"Circuit breakers configured: {list(self.circuit_breakers.keys())}")
        
        # Setup graceful shutdown
        def signal_handler(sig, frame):
            logger.info("Gracefully shutting down server...")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        self.app.run(
            host=host,
            port=port,
            debug=debug,
            threaded=True
        )

# Global server instance
server = None

if __name__ == '__main__':
    server = ProductionAPIServer()
    server.run(debug=os.getenv("FLASK_ENV") == "development")