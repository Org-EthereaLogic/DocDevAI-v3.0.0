"""
M007 Review Engine - Security Components
DevDocAI v3.0.0

Extracted security components for cleaner separation of concerns.
Implements rate limiting, validation, audit logging, and HMAC signing.
"""

import re
import time
import json
import hmac
import hashlib
import secrets
import logging
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)

# Security constants
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10MB
MAX_CONCURRENT_REQUESTS = 100
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 60  # per window
MAX_PATH_LENGTH = 260
SECURITY_HMAC_KEY = secrets.token_bytes(32)

BLOCKLIST_PATTERNS = [
    r'<script[^>]*>.*?</script>',  # XSS
    r'javascript:',  # JavaScript protocol
    r'<[^>]+on\w+\s*=',  # Event handlers in HTML tags
    r'\.\./',  # Path traversal
    r'\x00',  # Null bytes
    r'[\x01-\x08\x0B\x0C\x0E-\x1F]',  # Control characters
]

BLOCKED_DOCUMENT_TYPES = {'script', 'executable', 'binary', 'dll', 'exe'}


class SecurityError(Exception):
    """Security-related review engine errors."""
    pass


class ValidationError(Exception):
    """Input validation errors."""
    pass


class RateLimitError(Exception):
    """Rate limiting exceeded."""
    pass


class SecurityManager:
    """Manages security aspects of the review engine."""
    
    def __init__(self):
        """Initialize security manager."""
        # Rate limiting
        self._rate_limiter = defaultdict(lambda: {'count': 0, 'window_start': time.time()})
        self._rate_limit_lock = threading.Lock()
        
        # Audit logging
        self._audit_log = []
        self._audit_lock = threading.Lock()
        self._max_audit_entries = 10000
        
        # Resource limits
        self._active_requests = 0
        self._request_lock = threading.Lock()
        
        # HMAC signing
        self._hmac_key = SECURITY_HMAC_KEY
        
        # Compile patterns once for performance
        self._compiled_patterns = [
            re.compile(pattern, re.IGNORECASE | re.DOTALL) 
            for pattern in BLOCKLIST_PATTERNS
        ]
    
    def validate_document(self, document: Any) -> None:
        """Validate document for security issues."""
        if not document:
            raise ValidationError("Document cannot be None")
        
        # Check document size
        if len(document.content) > MAX_DOCUMENT_SIZE:
            raise ValidationError(f"Document size exceeds {MAX_DOCUMENT_SIZE} bytes")
        
        # Check document type
        if document.type and document.type.lower() in BLOCKED_DOCUMENT_TYPES:
            raise ValidationError(f"Blocked document type: {document.type}")
        
        # Check for malicious patterns
        for pattern in self._compiled_patterns:
            if pattern.search(document.content):
                raise SecurityError("Document contains potentially malicious content")
        
        # Validate document ID
        if not self._is_safe_string(document.id):
            raise ValidationError("Invalid document ID")
    
    def _is_safe_string(self, value: str, max_length: int = 255) -> bool:
        """Check if string is safe for use."""
        if not value or len(value) > max_length:
            return False
        # Allow alphanumeric, dash, underscore, dot
        return bool(re.match(r'^[a-zA-Z0-9._-]+$', value))
    
    def check_rate_limit(self, client_id: str) -> bool:
        """Check if client has exceeded rate limit."""
        with self._rate_limit_lock:
            now = time.time()
            client_data = self._rate_limiter[client_id]
            
            # Reset window if needed
            if now - client_data['window_start'] > RATE_LIMIT_WINDOW:
                client_data['count'] = 0
                client_data['window_start'] = now
            
            # Check limit
            if client_data['count'] >= RATE_LIMIT_MAX_REQUESTS:
                return False
            
            client_data['count'] += 1
            return True
    
    def acquire_request_slot(self) -> bool:
        """Acquire a request slot for resource limiting."""
        with self._request_lock:
            if self._active_requests >= MAX_CONCURRENT_REQUESTS:
                return False
            self._active_requests += 1
            return True
    
    def release_request_slot(self) -> None:
        """Release a request slot."""
        with self._request_lock:
            self._active_requests = max(0, self._active_requests - 1)
    
    def sign_data(self, data: str) -> str:
        """Sign data with HMAC for integrity."""
        return hmac.new(
            self._hmac_key,
            data.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def verify_signature(self, data: str, signature: str) -> bool:
        """Verify HMAC signature."""
        expected_signature = self.sign_data(data)
        return hmac.compare_digest(signature, expected_signature)
    
    def log_security_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """Log security-related events."""
        event = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'severity': 'SECURITY',
            'details': details
        }
        
        with self._audit_lock:
            self._audit_log.append(event)
            
            # Trim if too large
            if len(self._audit_log) > self._max_audit_entries:
                self._audit_log = self._audit_log[-self._max_audit_entries:]
        
        logger.warning(f"Security event: {event_type} - {details}")
    
    def log_audit_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """Log audit events."""
        event = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'severity': 'AUDIT',
            'details': details
        }
        
        with self._audit_lock:
            self._audit_log.append(event)
            
            # Trim if too large
            if len(self._audit_log) > self._max_audit_entries:
                self._audit_log = self._audit_log[-self._max_audit_entries:]
    
    def save_audit_log(self, filepath: Optional[Path] = None) -> None:
        """Save audit log to file."""
        try:
            audit_file = filepath or Path('audit_log.json')
            with self._audit_lock:
                with open(audit_file, 'w') as f:
                    json.dump(self._audit_log, f, indent=2, default=str)
            logger.info(f"Audit log saved to {audit_file}")
        except Exception as e:
            logger.error(f"Failed to save audit log: {e}")
    
    def get_audit_log(self, start_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get audit log entries."""
        with self._audit_lock:
            if start_time:
                return [
                    event for event in self._audit_log
                    if datetime.fromisoformat(event['timestamp']) >= start_time
                ]
            return self._audit_log.copy()
    
    def get_active_requests(self) -> int:
        """Get current number of active requests."""
        with self._request_lock:
            return self._active_requests