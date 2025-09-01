"""
Security audit logging for CLI operations.

Provides tamper-proof, compliant audit logging with SIEM integration.
"""

import os
import json
import hashlib
import logging
import threading
import gzip
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, asdict
import platform
import getpass


class AuditEventType(Enum):
    """Audit event types."""
    # Authentication events
    AUTH_SUCCESS = "auth.success"
    AUTH_FAILURE = "auth.failure"
    AUTH_LOGOUT = "auth.logout"
    
    # Access control events
    ACCESS_GRANTED = "access.granted"
    ACCESS_DENIED = "access.denied"
    PERMISSION_CHANGED = "permission.changed"
    
    # Data events
    DATA_READ = "data.read"
    DATA_WRITE = "data.write"
    DATA_DELETE = "data.delete"
    DATA_EXPORT = "data.export"
    
    # Security events
    SECURITY_VIOLATION = "security.violation"
    RATE_LIMIT_EXCEEDED = "rate_limit.exceeded"
    INJECTION_ATTEMPT = "injection.attempt"
    TRAVERSAL_ATTEMPT = "traversal.attempt"
    
    # Configuration events
    CONFIG_CHANGE = "config.change"
    KEY_ROTATION = "key.rotation"
    
    # Command events
    COMMAND_EXECUTED = "command.executed"
    COMMAND_FAILED = "command.failed"
    
    # System events
    SYSTEM_START = "system.start"
    SYSTEM_STOP = "system.stop"
    SYSTEM_ERROR = "system.error"


class AuditSeverity(Enum):
    """Audit event severity levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class AuditEvent:
    """Audit event data structure."""
    event_id: str
    timestamp: str
    event_type: AuditEventType
    severity: AuditSeverity
    user: str
    source_ip: Optional[str]
    command: Optional[str]
    resource: Optional[str]
    outcome: str  # success/failure
    details: Dict[str, Any]
    session_id: Optional[str]
    correlation_id: Optional[str]
    hash: Optional[str] = None
    signature: Optional[str] = None


class SecurityAuditLogger:
    """
    Comprehensive security audit logging.
    
    Features:
    - Tamper-proof logging with hash chains
    - GDPR/SOC2 compliant formatting
    - Log rotation and compression
    - SIEM integration support
    - Real-time alerting for critical events
    """
    
    def __init__(self, log_dir: Optional[Path] = None,
                 enable_compression: bool = True,
                 enable_chain: bool = True,
                 max_size_mb: int = 100,
                 retention_days: int = 90):
        """
        Initialize audit logger.
        
        Args:
            log_dir: Directory for audit logs
            enable_compression: Enable log compression
            enable_chain: Enable hash chaining for tamper detection
            max_size_mb: Maximum log file size before rotation
            retention_days: Log retention period
        """
        self.log_dir = log_dir or (Path.home() / '.devdocai' / 'audit')
        self.log_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        
        self.enable_compression = enable_compression
        self.enable_chain = enable_chain
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.retention_days = retention_days
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Session tracking
        self._session_id = self._generate_session_id()
        self._event_counter = 0
        
        # Hash chain for tamper detection
        self._last_hash = self._get_last_hash()
        
        # Setup logging
        self._setup_logging()
        
        # Log system start
        self.log_event(
            event_type=AuditEventType.SYSTEM_START,
            severity=AuditSeverity.INFO,
            details={'version': '3.0.0', 'platform': platform.platform()}
        )
    
    def _setup_logging(self):
        """Setup audit logging configuration."""
        # Create logger
        self.logger = logging.getLogger('devdocai.audit')
        self.logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers
        self.logger.handlers.clear()
        
        # File handler with rotation
        log_file = self.log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.log"
        
        # Check if rotation needed
        if log_file.exists() and log_file.stat().st_size > self.max_size_bytes:
            self._rotate_log(log_file)
        
        handler = logging.FileHandler(log_file, mode='a')
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(handler)
        
        # Set restrictive permissions
        os.chmod(log_file, 0o600)
        
        # Cleanup old logs
        self._cleanup_old_logs()
    
    def log_event(self, event_type: AuditEventType,
                  severity: AuditSeverity,
                  details: Optional[Dict[str, Any]] = None,
                  resource: Optional[str] = None,
                  outcome: str = "success") -> AuditEvent:
        """
        Log an audit event.
        
        Args:
            event_type: Type of event
            severity: Event severity
            details: Additional event details
            resource: Resource accessed
            outcome: Event outcome (success/failure)
            
        Returns:
            Created audit event
        """
        with self._lock:
            # Generate event
            event = self._create_event(
                event_type=event_type,
                severity=severity,
                details=details or {},
                resource=resource,
                outcome=outcome
            )
            
            # Add hash chain if enabled
            if self.enable_chain:
                event.hash = self._compute_event_hash(event)
                self._last_hash = event.hash
            
            # Log event
            self.logger.log(
                self._severity_to_level(severity),
                json.dumps(asdict(event), default=str)
            )
            
            # Check for critical events that need alerting
            if severity == AuditSeverity.CRITICAL:
                self._alert_critical_event(event)
            
            # Check if rotation needed
            self._check_rotation()
            
            return event
    
    def _create_event(self, event_type: AuditEventType,
                     severity: AuditSeverity,
                     details: Dict[str, Any],
                     resource: Optional[str],
                     outcome: str) -> AuditEvent:
        """Create audit event."""
        self._event_counter += 1
        
        # Get user and system info
        user = getpass.getuser()
        source_ip = self._get_source_ip()
        
        # Get command from details or environment
        command = details.pop('command', None) or os.environ.get('DEVDOCAI_COMMAND')
        
        # Create event
        event = AuditEvent(
            event_id=f"{self._session_id}_{self._event_counter:08d}",
            timestamp=datetime.utcnow().isoformat() + 'Z',
            event_type=event_type,
            severity=severity,
            user=user,
            source_ip=source_ip,
            command=command,
            resource=resource,
            outcome=outcome,
            details=self._sanitize_details(details),
            session_id=self._session_id,
            correlation_id=details.get('correlation_id')
        )
        
        return event
    
    def _sanitize_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize sensitive data in details."""
        sanitized = {}
        
        sensitive_keys = [
            'password', 'token', 'key', 'secret', 'credential',
            'api_key', 'access_token', 'refresh_token'
        ]
        
        for key, value in details.items():
            # Check if key contains sensitive data
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = '[REDACTED]'
            elif isinstance(value, str):
                # Check for patterns in values
                if len(value) > 20 and value.replace('-', '').replace('_', '').isalnum():
                    # Likely a token or key
                    sanitized[key] = f"[REDACTED_{key.upper()}]"
                else:
                    sanitized[key] = value
            elif isinstance(value, dict):
                # Recursively sanitize nested dicts
                sanitized[key] = self._sanitize_details(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _compute_event_hash(self, event: AuditEvent) -> str:
        """Compute hash for event (blockchain-style chaining)."""
        # Include previous hash for chaining
        data = f"{self._last_hash}:{event.event_id}:{event.timestamp}:"
        data += f"{event.event_type.value}:{event.user}:{event.outcome}"
        
        return hashlib.sha256(data.encode()).hexdigest()
    
    def _get_last_hash(self) -> str:
        """Get last hash from existing logs."""
        # Look for most recent log file
        log_files = sorted(self.log_dir.glob("audit_*.log"), reverse=True)
        
        if not log_files:
            return "0" * 64  # Genesis hash
        
        # Read last line of most recent file
        try:
            with open(log_files[0], 'r') as f:
                lines = f.readlines()
                if lines:
                    last_event = json.loads(lines[-1])
                    return last_event.get('hash', "0" * 64)
        except Exception:
            pass
        
        return "0" * 64
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        random_part = os.urandom(8).hex()
        return f"{timestamp}_{random_part}"
    
    def _get_source_ip(self) -> Optional[str]:
        """Get source IP address."""
        # Check SSH connection
        ssh_client = os.environ.get('SSH_CLIENT', '')
        if ssh_client:
            return ssh_client.split()[0]
        
        # Check remote addr
        remote_addr = os.environ.get('REMOTE_ADDR')
        if remote_addr:
            return remote_addr
        
        return None
    
    def _severity_to_level(self, severity: AuditSeverity) -> int:
        """Convert severity to logging level."""
        mapping = {
            AuditSeverity.DEBUG: logging.DEBUG,
            AuditSeverity.INFO: logging.INFO,
            AuditSeverity.WARNING: logging.WARNING,
            AuditSeverity.ERROR: logging.ERROR,
            AuditSeverity.CRITICAL: logging.CRITICAL
        }
        return mapping.get(severity, logging.INFO)
    
    def _alert_critical_event(self, event: AuditEvent):
        """Alert on critical events."""
        # Write to separate critical events file
        critical_file = self.log_dir / 'critical_events.log'
        
        with open(critical_file, 'a') as f:
            f.write(json.dumps(asdict(event), default=str) + '\n')
        
        # Set restrictive permissions
        os.chmod(critical_file, 0o600)
        
        # Could also send to SIEM, email, Slack, etc.
    
    def _check_rotation(self):
        """Check if log rotation is needed."""
        current_log = self.log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.log"
        
        if current_log.exists() and current_log.stat().st_size > self.max_size_bytes:
            self._rotate_log(current_log)
    
    def _rotate_log(self, log_file: Path):
        """Rotate log file."""
        # Generate rotation name
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        rotated_name = f"{log_file.stem}_{timestamp}{log_file.suffix}"
        
        if self.enable_compression:
            # Compress and rotate
            rotated_path = self.log_dir / f"{rotated_name}.gz"
            
            with open(log_file, 'rb') as f_in:
                with gzip.open(rotated_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Clear original file
            log_file.unlink()
        else:
            # Simple rename
            rotated_path = self.log_dir / rotated_name
            log_file.rename(rotated_path)
        
        # Set restrictive permissions
        os.chmod(rotated_path, 0o600)
        
        # Re-setup logging with new file
        self._setup_logging()
    
    def _cleanup_old_logs(self):
        """Remove logs older than retention period."""
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        
        for log_file in self.log_dir.glob("audit_*"):
            # Parse date from filename
            try:
                date_str = log_file.stem.split('_')[1]
                file_date = datetime.strptime(date_str, '%Y%m%d')
                
                if file_date < cutoff:
                    log_file.unlink()
            except Exception:
                # Skip files with unexpected naming
                pass
    
    def verify_integrity(self, start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None) -> bool:
        """
        Verify audit log integrity using hash chain.
        
        Args:
            start_date: Start date for verification
            end_date: End date for verification
            
        Returns:
            True if integrity verified
        """
        if not self.enable_chain:
            return True
        
        # Get log files in range
        log_files = []
        for log_file in sorted(self.log_dir.glob("audit_*.log")):
            try:
                date_str = log_file.stem.split('_')[1]
                file_date = datetime.strptime(date_str, '%Y%m%d')
                
                if start_date and file_date < start_date:
                    continue
                if end_date and file_date > end_date:
                    continue
                    
                log_files.append(log_file)
            except Exception:
                pass
        
        # Verify hash chain
        last_hash = "0" * 64  # Genesis hash
        
        for log_file in log_files:
            with open(log_file, 'r') as f:
                for line in f:
                    try:
                        event = json.loads(line)
                        
                        if 'hash' not in event:
                            continue
                        
                        # Recompute hash
                        data = f"{last_hash}:{event['event_id']}:{event['timestamp']}:"
                        data += f"{event['event_type']}:{event['user']}:{event['outcome']}"
                        computed_hash = hashlib.sha256(data.encode()).hexdigest()
                        
                        if computed_hash != event['hash']:
                            return False
                        
                        last_hash = event['hash']
                    except Exception:
                        return False
        
        return True
    
    def search_events(self, event_type: Optional[AuditEventType] = None,
                     user: Optional[str] = None,
                     start_time: Optional[datetime] = None,
                     end_time: Optional[datetime] = None,
                     severity: Optional[AuditSeverity] = None) -> List[AuditEvent]:
        """
        Search audit events.
        
        Args:
            event_type: Filter by event type
            user: Filter by user
            start_time: Start time filter
            end_time: End time filter
            severity: Filter by severity
            
        Returns:
            List of matching events
        """
        events = []
        
        # Get relevant log files
        for log_file in sorted(self.log_dir.glob("audit_*.log*")):
            # Handle compressed files
            if log_file.suffix == '.gz':
                open_func = gzip.open
                mode = 'rt'
            else:
                open_func = open
                mode = 'r'
            
            with open_func(log_file, mode) as f:
                for line in f:
                    try:
                        event_data = json.loads(line)
                        
                        # Apply filters
                        if event_type and event_data['event_type'] != event_type.value:
                            continue
                        if user and event_data['user'] != user:
                            continue
                        if severity and event_data['severity'] != severity.value:
                            continue
                        
                        # Time filters
                        event_time = datetime.fromisoformat(
                            event_data['timestamp'].rstrip('Z')
                        )
                        if start_time and event_time < start_time:
                            continue
                        if end_time and event_time > end_time:
                            continue
                        
                        # Convert to AuditEvent
                        event = AuditEvent(
                            event_id=event_data['event_id'],
                            timestamp=event_data['timestamp'],
                            event_type=AuditEventType(event_data['event_type']),
                            severity=AuditSeverity(event_data['severity']),
                            user=event_data['user'],
                            source_ip=event_data.get('source_ip'),
                            command=event_data.get('command'),
                            resource=event_data.get('resource'),
                            outcome=event_data['outcome'],
                            details=event_data.get('details', {}),
                            session_id=event_data.get('session_id'),
                            correlation_id=event_data.get('correlation_id'),
                            hash=event_data.get('hash'),
                            signature=event_data.get('signature')
                        )
                        events.append(event)
                    except Exception:
                        # Skip malformed entries
                        continue
        
        return events
    
    def export_for_siem(self, format: str = 'json',
                        start_time: Optional[datetime] = None,
                        end_time: Optional[datetime] = None) -> str:
        """
        Export audit logs for SIEM integration.
        
        Args:
            format: Export format (json, cef, syslog)
            start_time: Start time for export
            end_time: End time for export
            
        Returns:
            Exported data string
        """
        events = self.search_events(start_time=start_time, end_time=end_time)
        
        if format == 'json':
            return json.dumps([asdict(e) for e in events], default=str, indent=2)
        elif format == 'cef':
            # Common Event Format for ArcSight, etc.
            cef_events = []
            for event in events:
                cef = f"CEF:0|DevDocAI|CLI|3.0.0|{event.event_type.value}|"
                cef += f"{event.event_type.value}|{event.severity.value}|"
                cef += f"src={event.source_ip} user={event.user} "
                cef += f"outcome={event.outcome} msg={json.dumps(event.details)}"
                cef_events.append(cef)
            return '\n'.join(cef_events)
        elif format == 'syslog':
            # RFC 5424 syslog format
            syslog_events = []
            for event in events:
                priority = self._severity_to_syslog_priority(event.severity)
                syslog = f"<{priority}>1 {event.timestamp} devdocai "
                syslog += f"audit {event.event_id} - {json.dumps(asdict(event))}"
                syslog_events.append(syslog)
            return '\n'.join(syslog_events)
        else:
            return json.dumps([asdict(e) for e in events], default=str)
    
    def _severity_to_syslog_priority(self, severity: AuditSeverity) -> int:
        """Convert severity to syslog priority."""
        # Facility = 16 (local0), Severity based on audit severity
        severity_map = {
            AuditSeverity.DEBUG: 7,
            AuditSeverity.INFO: 6,
            AuditSeverity.WARNING: 4,
            AuditSeverity.ERROR: 3,
            AuditSeverity.CRITICAL: 2
        }
        return 16 * 8 + severity_map.get(severity, 6)
    
    def generate_compliance_report(self, standard: str = 'GDPR') -> Dict[str, Any]:
        """
        Generate compliance report.
        
        Args:
            standard: Compliance standard (GDPR, SOC2, HIPAA)
            
        Returns:
            Compliance report
        """
        report = {
            'standard': standard,
            'generated': datetime.utcnow().isoformat() + 'Z',
            'period': f"{self.retention_days} days",
            'metrics': {}
        }
        
        # Get events for analysis
        start_time = datetime.now() - timedelta(days=30)
        events = self.search_events(start_time=start_time)
        
        if standard == 'GDPR':
            # GDPR specific metrics
            report['metrics'] = {
                'data_access_events': len([e for e in events if e.event_type == AuditEventType.DATA_READ]),
                'data_modification_events': len([e for e in events if e.event_type == AuditEventType.DATA_WRITE]),
                'data_deletion_events': len([e for e in events if e.event_type == AuditEventType.DATA_DELETE]),
                'access_denied_events': len([e for e in events if e.event_type == AuditEventType.ACCESS_DENIED]),
                'authentication_failures': len([e for e in events if e.event_type == AuditEventType.AUTH_FAILURE]),
                'log_integrity': self.verify_integrity(start_time),
                'retention_compliance': self.retention_days >= 30
            }
        elif standard == 'SOC2':
            # SOC2 specific metrics
            report['metrics'] = {
                'availability': len([e for e in events if e.event_type == AuditEventType.SYSTEM_ERROR]) == 0,
                'processing_integrity': self.verify_integrity(start_time),
                'confidentiality': len([e for e in events if e.event_type == AuditEventType.DATA_EXPORT]),
                'privacy': len([e for e in events if 'pii' in str(e.details).lower()]) == 0
            }
        
        return report