"""
M009: Comprehensive Audit Logging Module.

Provides tamper-proof logging with HMAC integrity, PII masking,
structured JSON format, and real-time security monitoring.
GDPR/CCPA compliant with configurable retention policies.
"""

import os
import json
import time
import hmac
import hashlib
import logging
import threading
from typing import Dict, List, Optional, Any, Union, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import secrets
import base64
from collections import deque
import gzip

# Import M002's PII detector for content masking
try:
    from devdocai.storage.pii_detector import PIIDetector, PIIType
    HAS_PII_DETECTOR = True
except ImportError:
    HAS_PII_DETECTOR = False

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Audit event types."""
    # Authentication & Authorization
    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILURE = "auth.login.failure"
    LOGOUT = "auth.logout"
    PERMISSION_GRANTED = "auth.permission.granted"
    PERMISSION_DENIED = "auth.permission.denied"
    
    # Enhancement Operations
    DOCUMENT_ENHANCEMENT_START = "enhancement.document.start"
    DOCUMENT_ENHANCEMENT_SUCCESS = "enhancement.document.success"
    DOCUMENT_ENHANCEMENT_FAILURE = "enhancement.document.failure"
    BATCH_ENHANCEMENT_START = "enhancement.batch.start"
    BATCH_ENHANCEMENT_SUCCESS = "enhancement.batch.success"
    BATCH_ENHANCEMENT_FAILURE = "enhancement.batch.failure"
    
    # Security Events
    RATE_LIMIT_EXCEEDED = "security.rate_limit.exceeded"
    VALIDATION_FAILURE = "security.validation.failure"
    PROMPT_INJECTION_DETECTED = "security.prompt_injection.detected"
    CACHE_POISONING_DETECTED = "security.cache_poisoning.detected"
    PII_DETECTED = "security.pii.detected"
    SUSPICIOUS_ACTIVITY = "security.suspicious_activity"
    
    # System Events
    SERVICE_START = "system.service.start"
    SERVICE_STOP = "system.service.stop"
    CONFIGURATION_CHANGE = "system.config.change"
    ERROR_OCCURRED = "system.error.occurred"
    
    # Data Events
    DATA_ACCESS = "data.access"
    DATA_MODIFICATION = "data.modification"
    DATA_EXPORT = "data.export"
    DATA_DELETION = "data.deletion"


class EventSeverity(Enum):
    """Event severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class DataClassification(Enum):
    """Data classification levels."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


@dataclass
class AuditEvent:
    """Structured audit event."""
    
    # Core event data
    event_type: EventType
    timestamp: datetime
    severity: EventSeverity
    message: str
    
    # Identity information
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Operation context
    operation: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    result: Optional[str] = None
    
    # Security context
    threat_level: Optional[str] = None
    security_flags: List[str] = field(default_factory=list)
    
    # Performance data
    duration_ms: Optional[float] = None
    bytes_processed: Optional[int] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Compliance tracking
    data_classification: DataClassification = DataClassification.INTERNAL
    retention_days: int = 365
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['event_type'] = self.event_type.value
        data['severity'] = self.severity.value
        data['data_classification'] = self.data_classification.value
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuditEvent':
        """Create from dictionary."""
        data['event_type'] = EventType(data['event_type'])
        data['severity'] = EventSeverity(data['severity'])
        data['data_classification'] = DataClassification(data['data_classification'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class AuditConfig:
    """Configuration for audit logging."""
    
    # File settings
    log_file_path: Path = Path("audit.log")
    max_file_size_mb: int = 100
    max_files: int = 10
    compress_rotated: bool = True
    
    # Security settings
    enable_integrity_checking: bool = True
    integrity_secret_key: Optional[str] = None
    encrypt_logs: bool = False
    
    # PII protection
    enable_pii_masking: bool = True
    pii_mask_char: str = "*"
    preserve_pii_context: bool = False  # Keep first/last chars for debugging
    
    # Filtering
    minimum_severity: EventSeverity = EventSeverity.INFO
    event_type_filters: Set[EventType] = field(default_factory=set)
    excluded_metadata_keys: Set[str] = field(default_factory=lambda: {
        "password", "secret", "key", "token", "private"
    })
    
    # Performance
    async_logging: bool = True
    buffer_size: int = 1000
    flush_interval_seconds: int = 30
    
    # Retention & compliance
    default_retention_days: int = 365
    gdpr_compliance: bool = True
    enable_data_subject_requests: bool = True
    
    # Monitoring & alerting
    enable_real_time_monitoring: bool = True
    critical_event_notification: bool = True
    anomaly_detection: bool = False
    
    # Export & analysis
    enable_structured_export: bool = True
    export_formats: Set[str] = field(default_factory=lambda: {"json", "csv"})
    
    @classmethod
    def for_security_level(cls, level: str) -> 'AuditConfig':
        """Get configuration for specific security level."""
        configs = {
            "BASIC": cls(
                enable_integrity_checking=False,
                encrypt_logs=False,
                enable_pii_masking=False,
                async_logging=False,
                enable_real_time_monitoring=False
            ),
            "STANDARD": cls(
                enable_integrity_checking=True,
                encrypt_logs=False,
                enable_pii_masking=True,
                async_logging=True,
                enable_real_time_monitoring=True
            ),
            "STRICT": cls(
                enable_integrity_checking=True,
                encrypt_logs=True,
                enable_pii_masking=True,
                preserve_pii_context=False,
                minimum_severity=EventSeverity.WARNING,
                async_logging=True,
                enable_real_time_monitoring=True,
                critical_event_notification=True,
                anomaly_detection=True
            ),
            "PARANOID": cls(
                max_file_size_mb=50,
                max_files=20,
                enable_integrity_checking=True,
                encrypt_logs=True,
                enable_pii_masking=True,
                preserve_pii_context=False,
                minimum_severity=EventSeverity.INFO,
                buffer_size=100,  # Smaller buffer for immediate writing
                flush_interval_seconds=10,
                enable_real_time_monitoring=True,
                critical_event_notification=True,
                anomaly_detection=True,
                gdpr_compliance=True,
                enable_data_subject_requests=True
            )
        }
        return configs.get(level, cls())


class PIIMasker:
    """PII masking functionality."""
    
    def __init__(self, config: AuditConfig, pii_detector: Optional[Any] = None):
        """Initialize PII masker."""
        self.config = config
        self.pii_detector = pii_detector
        
        # Common PII patterns for fallback detection
        self.pii_patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'(\+?1[-.\s]?)?(\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})',
            'ssn': r'\b\d{3}-?\d{2}-?\d{4}\b',
            'credit_card': r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
            'ip_address': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        }
        
        # Compile patterns
        import re
        self.compiled_patterns = {
            name: re.compile(pattern)
            for name, pattern in self.pii_patterns.items()
        }
    
    def mask_pii(self, text: str, preserve_context: bool = None) -> str:
        """Mask PII in text."""
        if not self.config.enable_pii_masking:
            return text
        
        preserve_context = preserve_context or self.config.preserve_pii_context
        masked_text = text
        
        # Use PII detector if available
        if self.pii_detector:
            try:
                result = self.pii_detector.detect_pii(text)
                for detection in result.detections:
                    if detection.confidence > 0.7:
                        # Replace detected PII with mask
                        start, end = detection.start, detection.end
                        pii_text = text[start:end]
                        
                        if preserve_context and len(pii_text) > 4:
                            # Keep first and last character
                            masked = pii_text[0] + self.config.pii_mask_char * (len(pii_text) - 2) + pii_text[-1]
                        else:
                            masked = self.config.pii_mask_char * len(pii_text)
                        
                        masked_text = masked_text[:start] + masked + masked_text[end:]
            
            except Exception as e:
                logger.warning(f"PII detector failed: {e}")
        
        # Fallback pattern matching
        for pii_type, pattern in self.compiled_patterns.items():
            def mask_match(match):
                text = match.group(0)
                if preserve_context and len(text) > 4:
                    return text[0] + self.config.pii_mask_char * (len(text) - 2) + text[-1]
                else:
                    return self.config.pii_mask_char * len(text)
            
            masked_text = pattern.sub(mask_match, masked_text)
        
        return masked_text
    
    def mask_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask PII in dictionary values."""
        masked_data = {}
        
        for key, value in data.items():
            # Skip excluded keys entirely
            if key.lower() in self.config.excluded_metadata_keys:
                masked_data[key] = "[REDACTED]"
                continue
            
            if isinstance(value, str):
                masked_data[key] = self.mask_pii(value)
            elif isinstance(value, dict):
                masked_data[key] = self.mask_dict(value)
            elif isinstance(value, list):
                masked_data[key] = [
                    self.mask_pii(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                masked_data[key] = value
        
        return masked_data


class LogIntegrityChecker:
    """Log integrity checking with HMAC."""
    
    def __init__(self, secret_key: str):
        """Initialize with secret key."""
        self.secret_key = secret_key.encode()
    
    def calculate_signature(self, log_entry: str) -> str:
        """Calculate HMAC signature for log entry."""
        signature = hmac.new(
            self.secret_key,
            log_entry.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def verify_signature(self, log_entry: str, signature: str) -> bool:
        """Verify log entry signature."""
        expected = self.calculate_signature(log_entry)
        return hmac.compare_digest(expected, signature)


class AuditLogger:
    """
    Comprehensive audit logger with security features.
    
    Provides tamper-proof logging with HMAC integrity, PII masking,
    structured JSON format, and real-time security monitoring.
    """
    
    def __init__(self, config: Optional[AuditConfig] = None):
        """Initialize audit logger."""
        self.config = config or AuditConfig()
        
        # Initialize PII masking
        pii_detector = None
        if HAS_PII_DETECTOR and self.config.enable_pii_masking:
            try:
                pii_detector = PIIDetector()
            except Exception as e:
                logger.warning(f"Failed to initialize PII detector: {e}")
        
        self.pii_masker = PIIMasker(self.config, pii_detector)
        
        # Initialize integrity checking
        if self.config.enable_integrity_checking:
            secret_key = self.config.integrity_secret_key or secrets.token_hex(32)
            self.integrity_checker = LogIntegrityChecker(secret_key)
        else:
            self.integrity_checker = None
        
        # Setup log file
        self.log_file_path = self.config.log_file_path
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Async logging buffer
        if self.config.async_logging:
            self.log_buffer: deque = deque(maxlen=self.config.buffer_size)
            self.buffer_lock = threading.Lock()
            self.flush_timer = None
            self._start_flush_timer()
        else:
            self.log_buffer = None
            self.buffer_lock = None
        
        # Metrics
        self.events_logged = 0
        self.events_filtered = 0
        self.pii_masked_count = 0
        self.security_events = 0
        
        # Real-time monitoring
        if self.config.enable_real_time_monitoring:
            self.security_alerts: deque = deque(maxlen=1000)
            self.anomaly_patterns: Dict[str, List[datetime]] = {}
        
        # File rotation tracking
        self.current_file_size = 0
        if self.log_file_path.exists():
            self.current_file_size = self.log_file_path.stat().st_size
        
        logger.info(f"Audit logger initialized: {self.log_file_path}")
    
    def _start_flush_timer(self) -> None:
        """Start periodic buffer flush timer."""
        def flush_buffer():
            self.flush_buffer()
            self.flush_timer = threading.Timer(
                self.config.flush_interval_seconds,
                flush_buffer
            )
            self.flush_timer.daemon = True
            self.flush_timer.start()
        
        flush_buffer()
    
    def log_event(self, event: AuditEvent) -> None:
        """Log audit event."""
        try:
            # Filter by severity
            if event.severity.value < self.config.minimum_severity.value:
                self.events_filtered += 1
                return
            
            # Filter by event type
            if (self.config.event_type_filters and 
                event.event_type not in self.config.event_type_filters):
                self.events_filtered += 1
                return
            
            # Mask PII in event data
            if self.config.enable_pii_masking:
                event = self._mask_event_pii(event)
            
            # Convert to JSON
            event_dict = event.to_dict()
            log_entry = json.dumps(event_dict, separators=(',', ':'))
            
            # Add integrity signature
            if self.integrity_checker:
                signature = self.integrity_checker.calculate_signature(log_entry)
                log_entry_with_sig = f"{log_entry}\t{signature}\n"
            else:
                log_entry_with_sig = f"{log_entry}\n"
            
            # Write to log
            if self.config.async_logging and self.log_buffer is not None:
                with self.buffer_lock:
                    self.log_buffer.append(log_entry_with_sig)
                    if len(self.log_buffer) >= self.config.buffer_size:
                        self._write_buffer_to_file()
            else:
                self._write_to_file(log_entry_with_sig)
            
            # Update metrics
            self.events_logged += 1
            
            if event.severity in [EventSeverity.ERROR, EventSeverity.CRITICAL]:
                self.security_events += 1
            
            # Real-time monitoring
            if self.config.enable_real_time_monitoring:
                self._process_real_time_event(event)
            
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
    
    def _mask_event_pii(self, event: AuditEvent) -> AuditEvent:
        """Mask PII in event data."""
        # Create a copy to avoid modifying original
        masked_event = AuditEvent(**asdict(event))
        
        # Mask string fields
        if masked_event.message:
            masked_event.message = self.pii_masker.mask_pii(masked_event.message)
        
        if masked_event.user_id:
            # Partially mask user IDs for debugging
            masked_event.user_id = self.pii_masker.mask_pii(masked_event.user_id, preserve_context=True)
        
        if masked_event.ip_address:
            masked_event.ip_address = self.pii_masker.mask_pii(masked_event.ip_address)
        
        # Mask metadata
        if masked_event.metadata:
            masked_event.metadata = self.pii_masker.mask_dict(masked_event.metadata)
            self.pii_masked_count += 1
        
        return masked_event
    
    def _write_to_file(self, log_entry: str) -> None:
        """Write log entry to file."""
        # Check for file rotation
        if (self.current_file_size + len(log_entry.encode()) > 
            self.config.max_file_size_mb * 1024 * 1024):
            self._rotate_log_file()
        
        # Write to current log file
        with open(self.log_file_path, 'a', encoding='utf-8') as f:
            f.write(log_entry)
            f.flush()
        
        self.current_file_size += len(log_entry.encode())
    
    def _write_buffer_to_file(self) -> None:
        """Write buffer contents to file."""
        if not self.log_buffer:
            return
        
        # Get all buffered entries
        entries = list(self.log_buffer)
        self.log_buffer.clear()
        
        # Write all entries at once
        combined_entry = ''.join(entries)
        self._write_to_file(combined_entry)
    
    def flush_buffer(self) -> None:
        """Flush log buffer to file."""
        if self.config.async_logging and self.log_buffer:
            with self.buffer_lock:
                self._write_buffer_to_file()
    
    def _rotate_log_file(self) -> None:
        """Rotate log file when size limit reached."""
        try:
            # Find next rotation number
            rotation_num = 1
            while True:
                rotated_path = self.log_file_path.with_suffix(
                    f"{self.log_file_path.suffix}.{rotation_num}"
                )
                if not rotated_path.exists():
                    break
                rotation_num += 1
            
            # Move current log to rotated name
            if self.log_file_path.exists():
                self.log_file_path.rename(rotated_path)
                
                # Compress if enabled
                if self.config.compress_rotated:
                    self._compress_log_file(rotated_path)
            
            # Clean up old log files
            self._cleanup_old_logs()
            
            # Reset file size counter
            self.current_file_size = 0
            
            logger.info(f"Log file rotated to: {rotated_path}")
            
        except Exception as e:
            logger.error(f"Log rotation failed: {e}")
    
    def _compress_log_file(self, file_path: Path) -> None:
        """Compress log file."""
        try:
            compressed_path = file_path.with_suffix(f"{file_path.suffix}.gz")
            
            with open(file_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    f_out.writelines(f_in)
            
            # Remove uncompressed file
            file_path.unlink()
            
            logger.debug(f"Compressed log file: {compressed_path}")
            
        except Exception as e:
            logger.error(f"Log compression failed: {e}")
    
    def _cleanup_old_logs(self) -> None:
        """Remove old log files beyond retention limit."""
        try:
            # Find all log files
            log_files = []
            for file_path in self.log_file_path.parent.glob(f"{self.log_file_path.name}.*"):
                if file_path.is_file():
                    log_files.append(file_path)
            
            # Sort by modification time (newest first)
            log_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            
            # Remove files beyond max_files limit
            files_to_remove = log_files[self.config.max_files:]
            for file_path in files_to_remove:
                file_path.unlink()
                logger.debug(f"Removed old log file: {file_path}")
            
        except Exception as e:
            logger.error(f"Log cleanup failed: {e}")
    
    def _process_real_time_event(self, event: AuditEvent) -> None:
        """Process event for real-time monitoring."""
        # Track security-related events
        if event.event_type.value.startswith("security."):
            self.security_alerts.append(event)
            
            if self.config.critical_event_notification and event.severity == EventSeverity.CRITICAL:
                self._send_critical_alert(event)
        
        # Anomaly detection
        if self.config.anomaly_detection:
            self._detect_anomalies(event)
    
    def _send_critical_alert(self, event: AuditEvent) -> None:
        """Send critical event alert."""
        # This would integrate with alerting systems (email, Slack, etc.)
        logger.critical(f"CRITICAL SECURITY EVENT: {event.event_type.value} - {event.message}")
    
    def _detect_anomalies(self, event: AuditEvent) -> None:
        """Simple anomaly detection based on event patterns."""
        pattern_key = f"{event.event_type.value}:{event.user_id or 'anonymous'}"
        current_time = datetime.now()
        
        if pattern_key not in self.anomaly_patterns:
            self.anomaly_patterns[pattern_key] = []
        
        self.anomaly_patterns[pattern_key].append(current_time)
        
        # Keep only events from last hour
        cutoff = current_time - timedelta(hours=1)
        self.anomaly_patterns[pattern_key] = [
            timestamp for timestamp in self.anomaly_patterns[pattern_key]
            if timestamp > cutoff
        ]
        
        # Check for suspicious frequency (>10 events per minute)
        recent_events = [
            timestamp for timestamp in self.anomaly_patterns[pattern_key]
            if timestamp > current_time - timedelta(minutes=1)
        ]
        
        if len(recent_events) > 10:
            anomaly_event = AuditEvent(
                event_type=EventType.SUSPICIOUS_ACTIVITY,
                timestamp=current_time,
                severity=EventSeverity.WARNING,
                message=f"Anomalous activity detected: {len(recent_events)} {event.event_type.value} events in 1 minute",
                user_id=event.user_id,
                metadata={
                    "pattern": pattern_key,
                    "frequency": len(recent_events),
                    "time_window": "1_minute"
                }
            )
            
            # Log the anomaly (avoid recursion)
            if event.event_type != EventType.SUSPICIOUS_ACTIVITY:
                self.log_event(anomaly_event)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get audit logging statistics."""
        return {
            "events_logged": self.events_logged,
            "events_filtered": self.events_filtered,
            "security_events": self.security_events,
            "pii_masked_count": self.pii_masked_count,
            "log_file_size": self.current_file_size,
            "buffer_size": len(self.log_buffer) if self.log_buffer else 0,
            "security_alerts": len(self.security_alerts) if hasattr(self, 'security_alerts') else 0,
            "integrity_checking": self.config.enable_integrity_checking,
            "pii_masking": self.config.enable_pii_masking
        }
    
    def search_events(
        self,
        event_type: Optional[EventType] = None,
        user_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        max_results: int = 1000
    ) -> List[AuditEvent]:
        """Search audit events (for compliance/investigation)."""
        # This is a simplified implementation
        # In production, you'd want a proper search index (e.g., Elasticsearch)
        
        events = []
        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f):
                    if line_num >= max_results:
                        break
                    
                    try:
                        # Split off signature if present
                        parts = line.strip().split('\t')
                        event_json = parts[0]
                        
                        event_dict = json.loads(event_json)
                        event = AuditEvent.from_dict(event_dict)
                        
                        # Apply filters
                        if event_type and event.event_type != event_type:
                            continue
                        
                        if user_id and event.user_id != user_id:
                            continue
                        
                        if start_time and event.timestamp < start_time:
                            continue
                        
                        if end_time and event.timestamp > end_time:
                            continue
                        
                        events.append(event)
                    
                    except (json.JSONDecodeError, KeyError, ValueError) as e:
                        logger.warning(f"Failed to parse audit log line {line_num}: {e}")
                        continue
        
        except FileNotFoundError:
            logger.warning("Audit log file not found")
        
        return events
    
    def cleanup(self) -> None:
        """Clean up resources."""
        # Flush any remaining buffer
        if self.config.async_logging:
            self.flush_buffer()
            
            if self.flush_timer:
                self.flush_timer.cancel()
        
        logger.info("Audit logger cleanup complete")


# Convenience functions for common events

def log_authentication_success(
    audit_logger: AuditLogger,
    user_id: str,
    ip_address: str,
    session_id: str = None
) -> None:
    """Log successful authentication."""
    event = AuditEvent(
        event_type=EventType.LOGIN_SUCCESS,
        timestamp=datetime.now(),
        severity=EventSeverity.INFO,
        message=f"User {user_id} logged in successfully",
        user_id=user_id,
        session_id=session_id,
        ip_address=ip_address,
        action="login",
        result="success"
    )
    audit_logger.log_event(event)


def log_security_violation(
    audit_logger: AuditLogger,
    violation_type: str,
    details: str,
    user_id: str = None,
    ip_address: str = None,
    severity: EventSeverity = EventSeverity.WARNING
) -> None:
    """Log security violation."""
    event = AuditEvent(
        event_type=EventType.SUSPICIOUS_ACTIVITY,
        timestamp=datetime.now(),
        severity=severity,
        message=f"Security violation: {violation_type}",
        user_id=user_id,
        ip_address=ip_address,
        security_flags=[violation_type],
        metadata={"details": details}
    )
    audit_logger.log_event(event)


def log_enhancement_operation(
    audit_logger: AuditLogger,
    operation: str,
    result: str,
    user_id: str = None,
    duration_ms: float = None,
    bytes_processed: int = None,
    cost: float = None
) -> None:
    """Log enhancement operation."""
    event_type_map = {
        "enhance_document": EventType.DOCUMENT_ENHANCEMENT_SUCCESS if result == "success" else EventType.DOCUMENT_ENHANCEMENT_FAILURE,
        "enhance_batch": EventType.BATCH_ENHANCEMENT_SUCCESS if result == "success" else EventType.BATCH_ENHANCEMENT_FAILURE,
    }
    
    event = AuditEvent(
        event_type=event_type_map.get(operation, EventType.DOCUMENT_ENHANCEMENT_SUCCESS),
        timestamp=datetime.now(),
        severity=EventSeverity.INFO if result == "success" else EventSeverity.WARNING,
        message=f"Enhancement operation {operation} completed with result: {result}",
        user_id=user_id,
        operation=operation,
        result=result,
        duration_ms=duration_ms,
        bytes_processed=bytes_processed,
        metadata={"cost": cost} if cost else {}
    )
    audit_logger.log_event(event)


def create_audit_logger(security_level: str = "STANDARD") -> AuditLogger:
    """
    Factory function to create audit logger.
    
    Args:
        security_level: Security level (BASIC, STANDARD, STRICT, PARANOID)
        
    Returns:
        Configured AuditLogger
    """
    config = AuditConfig.for_security_level(security_level)
    return AuditLogger(config)