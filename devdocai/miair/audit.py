"""
Audit logging system for MIAIR Engine security monitoring.

Provides tamper-proof logging with PII redaction and structured output.
"""

import json
import logging
import hashlib
import hmac
import time
import uuid
import re
import threading
import os
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from collections import deque
from functools import wraps
from enum import Enum
import traceback

logger = logging.getLogger(__name__)


class SecurityEventType(Enum):
    """Types of security events."""
    # Access events
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    
    # Authentication/Authorization
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    PERMISSION_CHECK = "permission_check"
    
    # Data operations
    DATA_READ = "data_read"
    DATA_WRITE = "data_write"
    DATA_DELETE = "data_delete"
    DATA_EXPORT = "data_export"
    
    # Security violations
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    VALIDATION_FAILURE = "validation_failure"
    MALICIOUS_INPUT = "malicious_input"
    CACHE_POISONING = "cache_poisoning"
    
    # System events
    CONFIG_CHANGE = "config_change"
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    ERROR = "error"
    WARNING = "warning"
    
    # Performance/Resource
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    TIMEOUT = "timeout"
    THRESHOLD_EXCEEDED = "threshold_exceeded"


class SeverityLevel(Enum):
    """Event severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditConfig:
    """Configuration for audit logging."""
    # Logging destinations
    log_to_file: bool = True
    log_file_path: str = "audit.log"
    log_to_console: bool = False
    log_to_syslog: bool = False
    
    # Rotation settings
    max_file_size_mb: int = 100
    max_file_count: int = 10
    rotation_interval_hours: int = 24
    
    # Security settings
    sign_logs: bool = True
    redact_pii: bool = True
    mask_sensitive_data: bool = True
    include_stack_trace: bool = False
    
    # Rate limiting
    max_events_per_second: int = 100
    burst_size: int = 500
    
    # Buffering
    buffer_size: int = 1000
    flush_interval_seconds: int = 5
    
    # Formatting
    use_json: bool = True
    include_correlation_id: bool = True
    include_hostname: bool = True
    
    # Retention
    retention_days: int = 90
    compress_old_logs: bool = True


@dataclass
class AuditEvent:
    """Structured audit event."""
    # Required fields
    timestamp: str
    event_type: SecurityEventType
    severity: SeverityLevel
    message: str
    
    # Optional fields
    correlation_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    client_id: Optional[str] = None
    ip_address: Optional[str] = None
    
    # Event details
    operation: Optional[str] = None
    resource: Optional[str] = None
    result: Optional[str] = None
    duration_ms: Optional[float] = None
    
    # Additional context
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    # Security
    signature: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        # Convert enums to strings
        data['event_type'] = self.event_type.value
        data['severity'] = self.severity.value
        return data
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class PIIRedactor:
    """Redact personally identifiable information from logs."""
    
    # PII patterns
    PATTERNS = {
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone': r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'credit_card': r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
        'ip_address': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
        'api_key': r'\b[A-Za-z0-9]{32,}\b',
        'password': r'(?i)(password|passwd|pwd)[\s:=]+\S+',
    }
    
    def __init__(self, enabled: bool = True):
        """Initialize redactor."""
        self.enabled = enabled
        self.compiled_patterns = {
            name: re.compile(pattern) 
            for name, pattern in self.PATTERNS.items()
        } if enabled else {}
    
    def redact(self, text: str) -> str:
        """Redact PII from text."""
        if not self.enabled or not text:
            return text
        
        redacted = text
        
        for name, pattern in self.compiled_patterns.items():
            if name == 'email':
                redacted = pattern.sub('[EMAIL_REDACTED]', redacted)
            elif name == 'phone':
                redacted = pattern.sub('[PHONE_REDACTED]', redacted)
            elif name == 'ssn':
                redacted = pattern.sub('[SSN_REDACTED]', redacted)
            elif name == 'credit_card':
                redacted = pattern.sub('[CC_REDACTED]', redacted)
            elif name == 'ip_address':
                # Keep first two octets for debugging
                def mask_ip(match):
                    parts = match.group().split('.')
                    if len(parts) == 4:
                        return f"{parts[0]}.{parts[1]}.XXX.XXX"
                    return '[IP_REDACTED]'
                redacted = pattern.sub(mask_ip, redacted)
            elif name == 'api_key':
                redacted = pattern.sub('[API_KEY_REDACTED]', redacted)
            elif name == 'password':
                redacted = pattern.sub(r'\1=[PASSWORD_REDACTED]', redacted)
        
        return redacted
    
    def redact_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Redact PII from dictionary."""
        if not self.enabled:
            return data
        
        redacted = {}
        sensitive_keys = {'password', 'token', 'secret', 'key', 'auth', 'credential'}
        
        for key, value in data.items():
            # Check if key contains sensitive terms
            if any(term in key.lower() for term in sensitive_keys):
                redacted[key] = '[REDACTED]'
            elif isinstance(value, str):
                redacted[key] = self.redact(value)
            elif isinstance(value, dict):
                redacted[key] = self.redact_dict(value)
            elif isinstance(value, list):
                redacted[key] = [
                    self.redact(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                redacted[key] = value
        
        return redacted


class AuditLogger:
    """
    Comprehensive audit logging system for security monitoring.
    
    Features:
    - Tamper-proof logging with HMAC signatures
    - PII redaction and data masking
    - Structured JSON logging
    - Rate limiting to prevent log flooding
    - Buffered writing for performance
    - Log rotation and compression
    - Correlation ID tracking
    """
    
    def __init__(self, config: Optional[AuditConfig] = None):
        """Initialize audit logger."""
        self.config = config or AuditConfig()
        
        # Generate signing key
        self.signing_key = os.urandom(32) if self.config.sign_logs else None
        
        # Initialize components
        self.redactor = PIIRedactor(self.config.redact_pii)
        self.buffer = deque(maxlen=self.config.buffer_size)
        self.lock = threading.RLock()
        
        # Rate limiting
        self.event_times = deque(maxlen=self.config.burst_size)
        self.last_rate_check = time.time()
        
        # Session tracking
        self.session_id = str(uuid.uuid4())
        self.hostname = os.uname().nodename if self.config.include_hostname else None
        
        # Statistics
        self.event_counts = {event_type: 0 for event_type in SecurityEventType}
        self.total_events = 0
        self.dropped_events = 0
        
        # Initialize file handler
        if self.config.log_to_file:
            self._init_file_handler()
        
        # Start flush thread
        self.flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self.flush_thread.start()
        
        # Log system start
        self.log_event(
            SecurityEventType.SYSTEM_START,
            SeverityLevel.INFO,
            "Audit logging system initialized"
        )
    
    def log_event(self,
                 event_type: SecurityEventType,
                 severity: SeverityLevel,
                 message: str,
                 **kwargs) -> Optional[str]:
        """
        Log security event.
        
        Args:
            event_type: Type of security event
            severity: Event severity level
            message: Event message
            **kwargs: Additional event fields
            
        Returns:
            Event correlation ID if logged, None if dropped
        """
        # Check rate limit
        if not self._check_rate_limit():
            self.dropped_events += 1
            return None
        
        # Generate correlation ID
        correlation_id = kwargs.get('correlation_id') or str(uuid.uuid4())
        
        # Create event
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat() + 'Z',
            event_type=event_type,
            severity=severity,
            message=self.redactor.redact(message),
            correlation_id=correlation_id if self.config.include_correlation_id else None,
            session_id=self.session_id,
            user_id=kwargs.get('user_id'),
            client_id=kwargs.get('client_id'),
            ip_address=kwargs.get('ip_address'),
            operation=kwargs.get('operation'),
            resource=kwargs.get('resource'),
            result=kwargs.get('result'),
            duration_ms=kwargs.get('duration_ms'),
            metadata=self.redactor.redact_dict(kwargs.get('metadata', {})),
            tags=kwargs.get('tags', [])
        )
        
        # Add hostname if configured
        if self.hostname:
            event.metadata['hostname'] = self.hostname
        
        # Sign event if configured
        if self.config.sign_logs:
            event.signature = self._sign_event(event)
        
        # Add to buffer
        with self.lock:
            self.buffer.append(event)
            self.event_counts[event_type] += 1
            self.total_events += 1
        
        # Flush if buffer is full
        if len(self.buffer) >= self.config.buffer_size:
            self._flush_buffer()
        
        return correlation_id
    
    def log_access(self,
                  resource: str,
                  operation: str,
                  granted: bool,
                  user_id: Optional[str] = None,
                  **kwargs):
        """Log access attempt."""
        event_type = SecurityEventType.ACCESS_GRANTED if granted else SecurityEventType.ACCESS_DENIED
        severity = SeverityLevel.INFO if granted else SeverityLevel.WARNING
        
        self.log_event(
            event_type,
            severity,
            f"Access {'granted' if granted else 'denied'} for {operation} on {resource}",
            resource=resource,
            operation=operation,
            result="granted" if granted else "denied",
            user_id=user_id,
            **kwargs
        )
    
    def log_security_violation(self,
                              violation_type: str,
                              details: str,
                              severity: SeverityLevel = SeverityLevel.WARNING,
                              **kwargs):
        """Log security violation."""
        event_type = SecurityEventType.VALIDATION_FAILURE
        
        if "malicious" in violation_type.lower():
            event_type = SecurityEventType.MALICIOUS_INPUT
        elif "rate" in violation_type.lower():
            event_type = SecurityEventType.RATE_LIMIT_EXCEEDED
        elif "cache" in violation_type.lower():
            event_type = SecurityEventType.CACHE_POISONING
        
        self.log_event(
            event_type,
            severity,
            f"Security violation: {violation_type} - {details}",
            metadata={'violation_type': violation_type},
            **kwargs
        )
    
    def log_error(self,
                 error: Exception,
                 operation: str,
                 **kwargs):
        """Log error with optional stack trace."""
        message = f"Error in {operation}: {str(error)}"
        
        metadata = kwargs.get('metadata', {})
        if self.config.include_stack_trace:
            metadata['stack_trace'] = traceback.format_exc()
        
        self.log_event(
            SecurityEventType.ERROR,
            SeverityLevel.ERROR,
            message,
            operation=operation,
            metadata=metadata,
            **kwargs
        )
    
    def _check_rate_limit(self) -> bool:
        """Check if event can be logged within rate limits."""
        now = time.time()
        
        # Clean old events
        cutoff = now - 1.0  # 1 second window
        while self.event_times and self.event_times[0] < cutoff:
            self.event_times.popleft()
        
        # Check rate
        if len(self.event_times) >= self.config.max_events_per_second:
            return False
        
        self.event_times.append(now)
        return True
    
    def _sign_event(self, event: AuditEvent) -> str:
        """Generate HMAC signature for event."""
        if not self.signing_key:
            return ""
        
        # Create canonical representation
        canonical = json.dumps(event.to_dict(), sort_keys=True)
        
        # Generate HMAC
        signature = hmac.new(
            self.signing_key,
            canonical.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _init_file_handler(self):
        """Initialize file logging handler."""
        log_path = Path(self.config.log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Configure file handler
        self.file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=self.config.max_file_size_mb * 1024 * 1024,
            backupCount=self.config.max_file_count
        )
        
        # Set formatter
        if self.config.use_json:
            formatter = logging.Formatter('%(message)s')
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
        
        self.file_handler.setFormatter(formatter)
    
    def _flush_buffer(self):
        """Flush buffered events to log."""
        with self.lock:
            if not self.buffer:
                return
            
            events_to_write = list(self.buffer)
            self.buffer.clear()
        
        # Write events
        for event in events_to_write:
            self._write_event(event)
    
    def _write_event(self, event: AuditEvent):
        """Write event to configured destinations."""
        if self.config.log_to_file and hasattr(self, 'file_handler'):
            # Create log record
            record = logging.LogRecord(
                name="audit",
                level=self._severity_to_level(event.severity),
                pathname="",
                lineno=0,
                msg=event.to_json() if self.config.use_json else event.message,
                args=(),
                exc_info=None
            )
            
            self.file_handler.emit(record)
        
        if self.config.log_to_console:
            print(event.to_json() if self.config.use_json else event.message)
    
    def _severity_to_level(self, severity: SeverityLevel) -> int:
        """Convert severity to logging level."""
        mapping = {
            SeverityLevel.DEBUG: logging.DEBUG,
            SeverityLevel.INFO: logging.INFO,
            SeverityLevel.WARNING: logging.WARNING,
            SeverityLevel.ERROR: logging.ERROR,
            SeverityLevel.CRITICAL: logging.CRITICAL
        }
        return mapping.get(severity, logging.INFO)
    
    def _flush_loop(self):
        """Periodically flush buffer."""
        while True:
            time.sleep(self.config.flush_interval_seconds)
            self._flush_buffer()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get audit logging statistics."""
        with self.lock:
            return {
                'session_id': self.session_id,
                'total_events': self.total_events,
                'dropped_events': self.dropped_events,
                'drop_rate': self.dropped_events / max(self.total_events, 1),
                'event_counts': dict(self.event_counts),
                'buffer_size': len(self.buffer),
                'config': {
                    'redact_pii': self.config.redact_pii,
                    'sign_logs': self.config.sign_logs,
                    'rate_limit': self.config.max_events_per_second
                }
            }
    
    def verify_event(self, event: AuditEvent) -> bool:
        """Verify event signature."""
        if not self.config.sign_logs or not event.signature:
            return True
        
        expected_signature = self._sign_event(event)
        return hmac.compare_digest(event.signature, expected_signature)
    
    def search_events(self,
                     start_time: Optional[datetime] = None,
                     end_time: Optional[datetime] = None,
                     event_types: Optional[List[SecurityEventType]] = None,
                     severity_min: Optional[SeverityLevel] = None,
                     correlation_id: Optional[str] = None) -> List[AuditEvent]:
        """Search audit logs (simplified implementation)."""
        # This would typically query from persistent storage
        # For now, return events from buffer
        with self.lock:
            events = list(self.buffer)
        
        # Filter events
        filtered = []
        for event in events:
            # Time filter
            if start_time and event.timestamp < start_time.isoformat():
                continue
            if end_time and event.timestamp > end_time.isoformat():
                continue
            
            # Type filter
            if event_types and event.event_type not in event_types:
                continue
            
            # Severity filter
            if severity_min and event.severity.value < severity_min.value:
                continue
            
            # Correlation ID filter
            if correlation_id and event.correlation_id != correlation_id:
                continue
            
            filtered.append(event)
        
        return filtered
    
    def close(self):
        """Clean up resources."""
        self._flush_buffer()
        
        if hasattr(self, 'file_handler'):
            self.file_handler.close()
        
        self.log_event(
            SecurityEventType.SYSTEM_STOP,
            SeverityLevel.INFO,
            "Audit logging system shutting down"
        )


def audit_operation(operation_name: str,
                   resource_type: str = None,
                   log_result: bool = True):
    """
    Decorator for auditing function execution.
    
    Args:
        operation_name: Name of the operation
        resource_type: Type of resource being accessed
        log_result: Whether to log the result
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get audit logger from self if available
            audit_logger = getattr(args[0], 'audit_logger', None) if args else None
            
            if not audit_logger:
                # No audit logger, proceed without auditing
                return func(*args, **kwargs)
            
            # Generate correlation ID
            correlation_id = str(uuid.uuid4())
            
            # Log operation start
            start_time = time.perf_counter()
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Log success
                duration_ms = (time.perf_counter() - start_time) * 1000
                
                audit_logger.log_event(
                    SecurityEventType.DATA_READ if 'read' in operation_name.lower()
                    else SecurityEventType.DATA_WRITE,
                    SeverityLevel.INFO,
                    f"Operation {operation_name} completed successfully",
                    operation=operation_name,
                    resource=resource_type,
                    result="success" if log_result else None,
                    duration_ms=duration_ms,
                    correlation_id=correlation_id
                )
                
                return result
                
            except Exception as e:
                # Log failure
                duration_ms = (time.perf_counter() - start_time) * 1000
                
                audit_logger.log_error(
                    e,
                    operation_name,
                    resource=resource_type,
                    duration_ms=duration_ms,
                    correlation_id=correlation_id
                )
                
                raise
        
        return wrapper
    return decorator


# Global audit logger instance
_default_logger = None


def get_audit_logger(config: Optional[AuditConfig] = None) -> AuditLogger:
    """Get or create default audit logger instance."""
    global _default_logger
    
    if _default_logger is None or config is not None:
        _default_logger = AuditLogger(config)
    
    return _default_logger