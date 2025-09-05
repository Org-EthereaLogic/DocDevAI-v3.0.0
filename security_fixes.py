#!/usr/bin/env python3
"""
Security Remediation Script for DevDocAI v3.0.0
Implements critical security fixes identified in audit
"""

import os
import secrets
import hashlib
import hmac
import re
from pathlib import Path
from functools import wraps
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from flask import Flask, request, jsonify, g, session
from flask_cors import CORS
from jose import jwt, JWTError
from cryptography.fernet import Fernet
from werkzeug.security import generate_password_hash, check_password_hash
import redis

# Security configuration
class SecurityConfig:
    """Security configuration constants"""
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_urlsafe(32))
    JWT_ALGORITHM = 'HS256'
    JWT_EXPIRATION_HOURS = 24
    MAX_CONTENT_LENGTH = 50 * 1024  # 50KB
    ALLOWED_ORIGINS = ['https://app.devdocai.com']
    RATE_LIMIT_PER_MINUTE = 60
    BCRYPT_ROUNDS = 12
    SESSION_TIMEOUT_MINUTES = 30
    
    # Path traversal prevention
    ALLOWED_PROJECT_PATHS = ['/tmp/projects', '/workspace/projects']
    
    # Prompt injection patterns to block
    DANGEROUS_PROMPT_PATTERNS = [
        r'ignore previous instructions',
        r'disregard all prior',
        r'system:',
        r'</system>',
        r'<function>',
        r'reveal api key',
        r'show credentials',
        r'bypass security',
        r'\bexec\b',
        r'\beval\b',
        r'__import__',
    ]

# Initialize Redis for distributed rate limiting
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

class SecurityMiddleware:
    """Core security middleware implementations"""
    
    @staticmethod
    def require_auth(f):
        """JWT authentication decorator"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = None
            auth_header = request.headers.get('Authorization')
            
            if auth_header:
                try:
                    token = auth_header.split(' ')[1]  # Bearer <token>
                except IndexError:
                    return jsonify({'error': 'Invalid token format'}), 401
            
            if not token:
                return jsonify({'error': 'Authentication required'}), 401
            
            try:
                payload = jwt.decode(
                    token, 
                    SecurityConfig.SECRET_KEY, 
                    algorithms=[SecurityConfig.JWT_ALGORITHM]
                )
                g.user_id = payload['user_id']
                g.user_role = payload.get('role', 'user')
                
                # Check token expiration
                exp_timestamp = payload.get('exp', 0)
                if datetime.utcnow().timestamp() > exp_timestamp:
                    return jsonify({'error': 'Token expired'}), 401
                    
            except JWTError as e:
                return jsonify({'error': f'Invalid token: {str(e)}'}), 401
                
            return f(*args, **kwargs)
        return decorated_function
    
    @staticmethod
    def rate_limit(requests_per_minute=60):
        """Rate limiting decorator with Redis backend"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # Get client identifier (user ID if authenticated, IP otherwise)
                client_id = getattr(g, 'user_id', request.remote_addr)
                key = f"rate_limit:{client_id}:{f.__name__}"
                
                try:
                    # Get current count
                    current = redis_client.get(key)
                    if current is None:
                        # First request
                        redis_client.setex(key, 60, 1)
                    else:
                        current_count = int(current)
                        if current_count >= requests_per_minute:
                            return jsonify({
                                'error': 'Rate limit exceeded',
                                'retry_after': redis_client.ttl(key)
                            }), 429
                        # Increment counter
                        redis_client.incr(key)
                except redis.RedisError:
                    # Fall back to allowing request if Redis is down
                    pass
                    
                return f(*args, **kwargs)
            return decorated_function
        return decorator
    
    @staticmethod
    def validate_csrf(f):
        """CSRF protection decorator"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.method in ['POST', 'PUT', 'DELETE']:
                csrf_token = request.headers.get('X-CSRF-Token')
                session_token = session.get('csrf_token')
                
                if not csrf_token or not session_token:
                    return jsonify({'error': 'CSRF token missing'}), 403
                    
                if not hmac.compare_digest(csrf_token, session_token):
                    return jsonify({'error': 'Invalid CSRF token'}), 403
                    
            return f(*args, **kwargs)
        return decorated_function

class InputValidator:
    """Input validation and sanitization"""
    
    @staticmethod
    def validate_project_path(path: str) -> str:
        """Prevent path traversal attacks"""
        if not path:
            raise ValueError("Project path is required")
            
        # Resolve to absolute path
        try:
            safe_path = Path(path).resolve()
        except Exception:
            raise ValueError("Invalid path format")
        
        # Check if path is within allowed directories
        allowed = False
        for allowed_base in SecurityConfig.ALLOWED_PROJECT_PATHS:
            allowed_base_path = Path(allowed_base).resolve()
            # Properly check if safe_path is within allowed_base_path
            try:
                # Use is_relative_to if available (Python 3.9+)
                if hasattr(safe_path, "is_relative_to"):
                    if safe_path.is_relative_to(allowed_base_path):
                        allowed = True
                        break
                else:
                    # Fallback for older Python: does not raise if descendant
                    safe_path.relative_to(allowed_base_path)
                    allowed = True
                    break
            except ValueError:
                continue
        
        if not allowed:
            raise ValueError("Project path outside allowed directories")
            
        # Additional checks
        if '..' in path or path.startswith('/etc') or path.startswith('/root'):
            raise ValueError("Suspicious path pattern detected")
            
        return str(safe_path)
    
    @staticmethod
    def sanitize_prompt(prompt: str) -> str:
        """Prevent prompt injection attacks"""
        if not prompt:
            return ""
            
        # Check length
        if len(prompt) > 5000:
            raise ValueError("Prompt exceeds maximum length")
            
        # Check for dangerous patterns
        for pattern in SecurityConfig.DANGEROUS_PROMPT_PATTERNS:
            if re.search(pattern, prompt, re.IGNORECASE):
                raise ValueError(f"Potentially malicious prompt detected")
                
        # Remove special characters that could be used for injection
        prompt = re.sub(r'[<>{}]', '', prompt)
        
        # HTML encode to prevent XSS
        prompt = (prompt
                 .replace('&', '&amp;')
                 .replace('<', '&lt;')
                 .replace('>', '&gt;')
                 .replace('"', '&quot;')
                 .replace("'", '&#x27;'))
        
        return prompt
    
    @staticmethod
    def validate_template(template: str) -> str:
        """Validate template selection"""
        allowed_templates = [
            'prd', 'wbs', 'srs', 'architecture',
            'api-docs', 'readme', 'user-guide'
        ]
        
        if template not in allowed_templates:
            raise ValueError("Invalid template selection")
            
        return template

class SecureKeyManager:
    """Secure API key management"""
    
    def __init__(self):
        self.master_key = self._get_or_create_master_key()
        self.cipher = Fernet(self.master_key)
    
    def _get_or_create_master_key(self) -> bytes:
        """Get or create master encryption key"""
        key_file = Path('.master_key')
        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            # Set restrictive permissions
            os.chmod(key_file, 0o600)
            return key
    
    def encrypt_api_key(self, provider: str, api_key: str) -> str:
        """Encrypt API key for storage"""
        encrypted = self.cipher.encrypt(api_key.encode())
        return encrypted.decode()
    
    def decrypt_api_key(self, provider: str, encrypted_key: str) -> str:
        """Decrypt API key for use"""
        decrypted = self.cipher.decrypt(encrypted_key.encode())
        return decrypted.decode()

class RequestSigner:
    """Request signing and verification"""
    
    @staticmethod
    def sign_request(data: Dict[str, Any], secret: str) -> str:
        """Create HMAC signature for request"""
        message = json.dumps(data, sort_keys=True)
        signature = hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    @staticmethod
    def verify_signature(data: Dict[str, Any], signature: str, secret: str) -> bool:
        """Verify request signature"""
        expected_signature = RequestSigner.sign_request(data, secret)
        return hmac.compare_digest(signature, expected_signature)

def apply_security_headers(response):
    """Apply comprehensive security headers"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self';"
    )
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    return response

def generate_jwt_token(user_id: str, role: str = 'user') -> str:
    """Generate JWT token for authenticated user"""
    expiration = datetime.utcnow() + timedelta(hours=SecurityConfig.JWT_EXPIRATION_HOURS)
    payload = {
        'user_id': user_id,
        'role': role,
        'exp': expiration.timestamp(),
        'iat': datetime.utcnow().timestamp(),
        'jti': secrets.token_urlsafe(16)  # JWT ID for revocation
    }
    
    token = jwt.encode(
        payload,
        SecurityConfig.SECRET_KEY,
        algorithm=SecurityConfig.JWT_ALGORITHM
    )
    return token

def create_secure_session(user_id: str) -> Dict[str, str]:
    """Create secure session with CSRF token"""
    session.permanent = True
    session['user_id'] = user_id
    session['login_time'] = datetime.utcnow().isoformat()
    session['csrf_token'] = secrets.token_urlsafe(32)
    
    return {
        'csrf_token': session['csrf_token'],
        'session_id': session.sid if hasattr(session, 'sid') else None
    }

# Example secure endpoint implementation
def secure_generate_endpoint():
    """Example of secured generate endpoint"""
    from flask import request, jsonify
    
    # Applied decorators: @require_auth, @rate_limit, @validate_csrf
    try:
        data = request.get_json()
        
        # Validate inputs
        project_path = InputValidator.validate_project_path(data.get('project_path', ''))
        template = InputValidator.validate_template(data.get('template', ''))
        custom_instructions = InputValidator.sanitize_prompt(data.get('custom_instructions', ''))
        
        # Sign the request for integrity
        request_signature = RequestSigner.sign_request(
            {'path': project_path, 'template': template},
            SecurityConfig.SECRET_KEY
        )
        
        # Process request (actual generation logic here)
        result = {
            'success': True,
            'content': 'Generated content',
            'signature': request_signature
        }
        
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        # Log error securely without exposing details
        app.logger.error(f"Generation failed for user {g.user_id}: {str(e)}")
        return jsonify({'error': 'Generation failed'}), 500

if __name__ == "__main__":
    print("Security Remediation Script for DevDocAI v3.0.0")
    print("=" * 50)
    print("\nThis script provides security implementations for:")
    print("1. JWT Authentication")
    print("2. Rate Limiting with Redis")
    print("3. CSRF Protection")
    print("4. Input Validation & Sanitization")
    print("5. Secure API Key Management")
    print("6. Request Signing")
    print("7. Security Headers")
    print("\nIntegrate these components into production_api_server.py")
    print("to address critical security vulnerabilities.")
    
    # Generate initial configuration
    print("\nGenerating secure configuration...")
    print(f"SECRET_KEY={secrets.token_urlsafe(32)}")
    print(f"MASTER_KEY={Fernet.generate_key().decode()}")
    print("\nAdd these to your .env file (DO NOT COMMIT!)")