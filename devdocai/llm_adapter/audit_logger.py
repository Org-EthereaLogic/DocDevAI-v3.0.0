"""
M008: GDPR-Compliant Audit Logging Module.

Provides comprehensive audit logging with PII masking, data retention policies,
and compliance with GDPR, CCPA, and other privacy regulations.
"""

import json
import logging
import hashlib
import re
import asyncio
import uuid
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import sqlite3
import hmac
from collections import defaultdict

# Import PII detector from M002 if available
try:
    from devdocai.storage.pii_detector import PIIDetector
    HAS_PII_DETECTOR = True
except ImportError:
    HAS_PII_DETECTOR = False

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of audit events."""
    # Authentication & Authorization
    AUTH_SUCCESS = "auth.success"
    AUTH_FAILURE = "auth.failure"
    PERMISSION_GRANTED = "permission.granted"
    PERMISSION_DENIED = "permission.denied"
    
    # API Operations
    API_REQUEST = "api.request"
    API_RESPONSE = "api.response"
    API_ERROR = "api.error"
    
    # Security Events
    SECURITY_VIOLATION = "security.violation"
    RATE_LIMIT_EXCEEDED = "security.rate_limit"
    INJECTION_ATTEMPT = "security.injection"
    JAILBREAK_ATTEMPT = "security.jailbreak"
    DATA_EXFILTRATION = "security.exfiltration"
    
    # Data Operations
    DATA_ACCESS = "data.access"
    DATA_MODIFICATION = "data.modification"
    DATA_DELETION = "data.deletion"
    DATA_EXPORT = "data.export"
    
    # Compliance Events
    CONSENT_GRANTED = "compliance.consent_granted"
    CONSENT_REVOKED = "compliance.consent_revoked"
    DATA_REQUEST = "compliance.data_request"
    DATA_ERASURE = "compliance.data_erasure"
    
    # System Events
    SYSTEM_START = "system.start"
    SYSTEM_STOP = "system.stop"
    CONFIG_CHANGE = "system.config_change"
    ERROR = "system.error"


class EventSeverity(Enum):
    """Severity levels for audit events."""
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
    PII = "pii"
    SENSITIVE = "sensitive"


@dataclass
class AuditEvent:
    """Represents an audit event."""
    event_id: str
    timestamp: datetime
    event_type: EventType
    severity: EventSeverity
    
    # Actor information (who)
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Target information (what)
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    action: Optional[str] = None
    
    # Context
    provider: Optional[str] = None
    model: Optional[str] = None
    request_id: Optional[str] = None
    
    # Result
    success: bool = True
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    
    # Data
    data: Dict[str, Any] = field(default_factory=dict)
    data_classification: DataClassification = DataClassification.INTERNAL
    
    # Compliance
    gdpr_lawful_basis: Optional[str] = None
    data_retention_days: int = 90
    
    # Security
    threat_indicators: List[str] = field(default_factory=list)
    risk_score: float = 0.0


class PIIMasker:
    """
    Masks PII data in audit logs.
    """
    
    # PII patterns to detect and mask
    PII_PATTERNS = {
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone': r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'credit_card': r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
        'ip_address': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
        'api_key': r'\b[A-Za-z0-9]{32,}\b',
        'jwt': r'eyJ[A-Za-z0-9-_]+\.eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+',
    }
    
    def __init__(self, hash_salt: Optional[str] = None):
        """
        Initialize PII masker.
        
        Args:
            hash_salt: Salt for consistent hashing (optional)
        """
        self.hash_salt = hash_salt or "default_salt_change_in_production"
        self.logger = logging.getLogger(f"{__name__}.PIIMasker")
        
        # Use M002's PII detector if available
        if HAS_PII_DETECTOR:
            self.pii_detector = PIIDetector()
        else:
            self.pii_detector = None
    
    def mask_data(self, data: Any) -> Any:
        """
        Recursively mask PII in data.
        
        Args:
            data: Data to mask (dict, list, str, etc.)
            
        Returns:
            Masked data with PII replaced
        """
        if isinstance(data, dict):
            return {k: self.mask_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.mask_data(item) for item in data]
        elif isinstance(data, str):
            return self._mask_string(data)
        else:
            return data
    
    def _mask_string(self, text: str) -> str:
        """Mask PII in a string."""
        masked = text
        
        # Use M002's PII detector if available
        if self.pii_detector:
            pii_results = self.pii_detector.detect_pii(masked)
            if pii_results['has_pii']:
                for entity in pii_results['entities']:
                    start = entity['start']
                    end = entity['end']
                    pii_text = masked[start:end]
                    masked_value = self._hash_pii(pii_text, entity['type'])
                    masked = masked[:start] + masked_value + masked[end:]
        else:
            # Fallback to regex patterns
            for pii_type, pattern in self.PII_PATTERNS.items():
                masked = re.sub(
                    pattern,
                    lambda m: self._hash_pii(m.group(), pii_type),
                    masked
                )
        
        return masked
    
    def _hash_pii(self, value: str, pii_type: str) -> str:
        """
        Hash PII value for consistent masking.
        
        Args:
            value: PII value to hash
            pii_type: Type of PII
            
        Returns:
            Masked representation
        """
        # Create consistent hash for the same value
        hash_input = f"{pii_type}:{value}:{self.hash_salt}"
        hash_value = hashlib.sha256(hash_input.encode()).hexdigest()[:8]
        
        # Return type-specific mask
        if pii_type == 'email':
            parts = value.split('@')
            if len(parts) == 2:
                return f"***{hash_value}@{parts[1]}"
            return f"[EMAIL_{hash_value}]"
        elif pii_type == 'phone':
            return f"[PHONE_{hash_value}]"
        elif pii_type == 'ssn':
            return f"[SSN_{hash_value}]"
        elif pii_type == 'credit_card':
            return f"[CC_{hash_value}]"
        elif pii_type == 'ip_address':
            # Preserve first two octets for geographic info
            parts = value.split('.')
            if len(parts) == 4:
                return f"{parts[0]}.{parts[1]}.XXX.XXX"
            return f"[IP_{hash_value}]"
        elif pii_type == 'api_key':
            return f"[KEY_{hash_value}]"
        elif pii_type == 'jwt':
            return f"[JWT_{hash_value}]"
        else:
            return f"[{pii_type.upper()}_{hash_value}]"


class AuditLogger:
    """
    GDPR-compliant audit logger with PII protection.
    
    Features:
    - Automatic PII detection and masking
    - GDPR Article 32 compliance (security of processing)
    - Data retention policies
    - Tamper-proof logging with checksums
    - Security event correlation
    - Export capabilities for compliance requests
    """
    
    def __init__(
        self,
        storage_path: Optional[Path] = None,
        retention_days: int = 90,
        mask_pii: bool = True,
        encryption_key: Optional[str] = None
    ):
        """
        Initialize audit logger.
        
        Args:
            storage_path: Path to audit log database
            retention_days: Default retention period in days
            mask_pii: Whether to mask PII in logs
            encryption_key: Key for log integrity verification
        """
        self.storage_path = storage_path or Path("./data/audit.db")
        self.retention_days = retention_days
        self.mask_pii = mask_pii
        self.encryption_key = encryption_key or "change_in_production"
        
        self.logger = logging.getLogger(f"{__name__}.AuditLogger")
        
        # Initialize components
        self.pii_masker = PIIMasker() if mask_pii else None
        
        # Create storage directory
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        # Event buffer for batch writing
        self.event_buffer: List[AuditEvent] = []
        self.buffer_size = 100
        self._lock = asyncio.Lock()
        
        # Metrics
        self.event_counts: Dict[EventType, int] = defaultdict(int)
        self.severity_counts: Dict[EventSeverity, int] = defaultdict(int)
    
    def _init_database(self):
        """Initialize SQLite database for audit logs."""
        conn = sqlite3.connect(str(self.storage_path))
        cursor = conn.cursor()
        
        # Create audit events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                event_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                user_id TEXT,
                session_id TEXT,
                ip_address TEXT,
                user_agent TEXT,
                resource_type TEXT,
                resource_id TEXT,
                action TEXT,
                provider TEXT,
                model TEXT,
                request_id TEXT,
                success INTEGER,
                error_code TEXT,
                error_message TEXT,
                data TEXT,
                data_classification TEXT,
                gdpr_lawful_basis TEXT,
                data_retention_days INTEGER,
                threat_indicators TEXT,
                risk_score REAL,
                checksum TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON audit_events(timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_event_type 
            ON audit_events(event_type)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_id 
            ON audit_events(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_severity 
            ON audit_events(severity)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_risk_score 
            ON audit_events(risk_score)
        """)
        
        # Create compliance tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS compliance_requests (
                request_id TEXT PRIMARY KEY,
                request_type TEXT NOT NULL,
                user_id TEXT NOT NULL,
                requested_at TEXT NOT NULL,
                completed_at TEXT,
                status TEXT,
                details TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def log_event(self, event: AuditEvent):
        """
        Log an audit event.
        
        Args:
            event: Audit event to log
        """
        # Mask PII if enabled
        if self.pii_masker:
            event = self._mask_event(event)
        
        # Add checksum for integrity
        event = self._add_checksum(event)
        
        # Update metrics
        self.event_counts[event.event_type] += 1
        self.severity_counts[event.severity] += 1
        
        # Add to buffer
        async with self._lock:
            self.event_buffer.append(event)
            
            # Flush if buffer is full
            if len(self.event_buffer) >= self.buffer_size:
                await self._flush_buffer()
        
        # Log high-severity events immediately
        if event.severity in [EventSeverity.ERROR, EventSeverity.CRITICAL]:
            self.logger.error(
                f"Security event: {event.event_type.value} - "
                f"User: {event.user_id} - Risk: {event.risk_score}"
            )
            await self._flush_buffer()
    
    async def log_security_event(
        self,
        event_type: EventType,
        user_id: Optional[str] = None,
        threat_indicators: List[str] = None,
        risk_score: float = 0.0,
        **kwargs
    ):
        """
        Log a security-specific event.
        
        Args:
            event_type: Type of security event
            user_id: User identifier
            threat_indicators: List of threat indicators
            risk_score: Risk score (0-1)
            **kwargs: Additional event data
        """
        import uuid
        
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            event_type=event_type,
            severity=EventSeverity.WARNING if risk_score > 0.5 else EventSeverity.INFO,
            user_id=user_id,
            threat_indicators=threat_indicators or [],
            risk_score=risk_score,
            data=kwargs
        )
        
        await self.log_event(event)
    
    def _mask_event(self, event: AuditEvent) -> AuditEvent:
        """Mask PII in audit event."""
        # Create a copy to avoid modifying original
        masked_data = asdict(event)
        
        # Mask specific fields
        if event.user_id:
            masked_data['user_id'] = self.pii_masker._hash_pii(event.user_id, 'user_id')
        
        if event.ip_address:
            masked_data['ip_address'] = self.pii_masker._mask_string(event.ip_address)
        
        if event.data:
            masked_data['data'] = self.pii_masker.mask_data(event.data)
        
        if event.error_message:
            masked_data['error_message'] = self.pii_masker._mask_string(event.error_message)
        
        # Recreate event with masked data
        return AuditEvent(**{
            k: v for k, v in masked_data.items()
            if k in AuditEvent.__dataclass_fields__
        })
    
    def _add_checksum(self, event: AuditEvent) -> AuditEvent:
        """Add integrity checksum to event."""
        # Create checksum of critical fields
        checksum_data = f"{event.event_id}{event.timestamp}{event.event_type.value}"
        checksum = hmac.new(
            self.encryption_key.encode(),
            checksum_data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Add checksum to event data
        event.data['_checksum'] = checksum
        return event
    
    async def _flush_buffer(self):
        """Flush event buffer to database."""
        if not self.event_buffer:
            return
        
        conn = sqlite3.connect(str(self.storage_path))
        cursor = conn.cursor()
        
        try:
            for event in self.event_buffer:
                cursor.execute("""
                    INSERT INTO audit_events (
                        event_id, timestamp, event_type, severity,
                        user_id, session_id, ip_address, user_agent,
                        resource_type, resource_id, action,
                        provider, model, request_id,
                        success, error_code, error_message,
                        data, data_classification, gdpr_lawful_basis,
                        data_retention_days, threat_indicators, risk_score,
                        checksum
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.event_id,
                    event.timestamp.isoformat(),
                    event.event_type.value,
                    event.severity.value,
                    event.user_id,
                    event.session_id,
                    event.ip_address,
                    event.user_agent,
                    event.resource_type,
                    event.resource_id,
                    event.action,
                    event.provider,
                    event.model,
                    event.request_id,
                    int(event.success),
                    event.error_code,
                    event.error_message,
                    json.dumps(event.data),
                    event.data_classification.value,
                    event.gdpr_lawful_basis,
                    event.data_retention_days,
                    json.dumps(event.threat_indicators),
                    event.risk_score,
                    event.data.get('_checksum')
                ))
            
            conn.commit()
            self.event_buffer.clear()
            
        except Exception as e:
            self.logger.error(f"Failed to flush audit buffer: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    async def cleanup_old_events(self):
        """Remove events older than retention period."""
        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
        
        conn = sqlite3.connect(str(self.storage_path))
        cursor = conn.cursor()
        
        try:
            # Delete old events
            cursor.execute("""
                DELETE FROM audit_events 
                WHERE timestamp < ? 
                AND data_retention_days <= ?
            """, (cutoff_date.isoformat(), self.retention_days))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            if deleted_count > 0:
                self.logger.info(f"Cleaned up {deleted_count} old audit events")
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old events: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    async def export_user_data(self, user_id: str) -> Dict[str, Any]:
        """
        Export all data for a user (GDPR compliance).
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary containing all user data
        """
        # Hash the user_id if PII masking is enabled
        if self.pii_masker:
            search_user_id = self.pii_masker._hash_pii(user_id, 'user_id')
        else:
            search_user_id = user_id
        
        conn = sqlite3.connect(str(self.storage_path))
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM audit_events 
                WHERE user_id = ?
                ORDER BY timestamp DESC
            """, (search_user_id,))
            
            columns = [desc[0] for desc in cursor.description]
            events = []
            
            for row in cursor.fetchall():
                event_dict = dict(zip(columns, row))
                # Parse JSON fields
                if event_dict.get('data'):
                    event_dict['data'] = json.loads(event_dict['data'])
                if event_dict.get('threat_indicators'):
                    event_dict['threat_indicators'] = json.loads(event_dict['threat_indicators'])
                events.append(event_dict)
            
            return {
                'user_id': user_id,
                'export_date': datetime.utcnow().isoformat(),
                'event_count': len(events),
                'events': events
            }
            
        finally:
            conn.close()
    
    async def delete_user_data(self, user_id: str) -> int:
        """
        Delete all data for a user (GDPR right to erasure).
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of records deleted
        """
        # Hash the user_id if PII masking is enabled
        if self.pii_masker:
            search_user_id = self.pii_masker._hash_pii(user_id, 'user_id')
        else:
            search_user_id = user_id
        
        conn = sqlite3.connect(str(self.storage_path))
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                DELETE FROM audit_events 
                WHERE user_id = ?
            """, (search_user_id,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            # Log the deletion request
            await self.log_event(AuditEvent(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                event_type=EventType.DATA_ERASURE,
                severity=EventSeverity.INFO,
                user_id=user_id,
                success=True,
                data={'records_deleted': deleted_count}
            ))
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Failed to delete user data: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get audit logger metrics.
        
        Returns:
            Dictionary of metrics
        """
        return {
            'event_counts': dict(self.event_counts),
            'severity_counts': dict(self.severity_counts),
            'buffer_size': len(self.event_buffer),
            'storage_path': str(self.storage_path)
        }
    
    async def correlate_events(
        self,
        time_window_minutes: int = 5,
        min_risk_score: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Correlate security events to detect patterns.
        
        Args:
            time_window_minutes: Time window for correlation
            min_risk_score: Minimum risk score to include
            
        Returns:
            List of correlated event patterns
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        
        conn = sqlite3.connect(str(self.storage_path))
        cursor = conn.cursor()
        
        try:
            # Find high-risk events in time window
            cursor.execute("""
                SELECT user_id, ip_address, event_type, 
                       COUNT(*) as event_count,
                       AVG(risk_score) as avg_risk,
                       GROUP_CONCAT(threat_indicators) as threats
                FROM audit_events
                WHERE timestamp > ?
                AND risk_score >= ?
                GROUP BY user_id, ip_address, event_type
                HAVING event_count > 1
                ORDER BY avg_risk DESC
            """, (cutoff_time.isoformat(), min_risk_score))
            
            patterns = []
            for row in cursor.fetchall():
                patterns.append({
                    'user_id': row[0],
                    'ip_address': row[1],
                    'event_type': row[2],
                    'event_count': row[3],
                    'avg_risk_score': row[4],
                    'threat_indicators': row[5].split(',') if row[5] else []
                })
            
            return patterns
            
        finally:
            conn.close()
    
    async def close(self):
        """Close audit logger and flush remaining events."""
        async with self._lock:
            await self._flush_buffer()
        
        self.logger.info("Audit logger closed")