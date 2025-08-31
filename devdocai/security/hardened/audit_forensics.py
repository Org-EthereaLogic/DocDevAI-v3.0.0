"""
Advanced Audit and Forensics System for M010 Security Module
Implements tamper-proof logging, blockchain-style chaining, and forensic analysis.
"""

import json
import hashlib
import gzip
import mmap
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum
import threading
import logging
import struct
import pickle
from collections import defaultdict, deque
import sqlite3

logger = logging.getLogger(__name__)


class AuditLevel(Enum):
    """Audit event severity levels."""
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4
    FORENSIC = 5  # Highest level for security incidents


class EventCategory(Enum):
    """Categories of audit events."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    CONFIGURATION = "configuration"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    SYSTEM = "system"


@dataclass
class AuditEvent:
    """Represents an audit event with blockchain-style chaining."""
    event_id: str
    timestamp: datetime
    level: AuditLevel
    category: EventCategory
    action: str
    actor: str  # Who performed the action
    target: str  # What was affected
    result: str  # success, failure, partial
    
    # Blockchain fields
    previous_hash: str
    event_hash: str
    block_number: int
    
    # Forensic data
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    evidence: List[str] = field(default_factory=list)  # File paths, screenshots, etc.
    
    def to_bytes(self) -> bytes:
        """Serialize event to bytes for hashing."""
        data = {
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat(),
            'level': self.level.value,
            'category': self.category.value,
            'action': self.action,
            'actor': self.actor,
            'target': self.target,
            'result': self.result,
            'previous_hash': self.previous_hash,
            'block_number': self.block_number,
            'metadata': self.metadata
        }
        return json.dumps(data, sort_keys=True).encode()
    
    def calculate_hash(self) -> str:
        """Calculate SHA-256 hash of the event."""
        return hashlib.sha256(self.to_bytes()).hexdigest()


@dataclass
class ForensicArtifact:
    """Represents a forensic artifact collected during investigation."""
    artifact_id: str
    collected_at: datetime
    artifact_type: str  # memory_dump, network_capture, file_snapshot, etc.
    source: str
    size_bytes: int
    hash_sha256: str
    storage_path: Path
    metadata: Dict[str, Any] = field(default_factory=dict)
    chain_of_custody: List[Dict[str, Any]] = field(default_factory=list)


class AuditForensics:
    """
    Advanced audit and forensics system with tamper-proof logging.
    
    Features:
    - Blockchain-style event chaining
    - Tamper detection and prevention
    - Forensic artifact collection
    - Log correlation and analysis
    - SIEM integration support
    - Compliance evidence automation
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize the audit forensics system."""
        self.storage_path = storage_path or Path.home() / '.devdocai' / 'audit'
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Blockchain state
        self._chain: List[AuditEvent] = []
        self._current_block = 0
        self._genesis_hash = self._create_genesis_block()
        
        # Storage backends
        self._db_path = self.storage_path / 'audit.db'
        self._archive_path = self.storage_path / 'archive'
        self._archive_path.mkdir(exist_ok=True)
        
        # Memory-mapped file for performance
        self._mmap_file = None
        self._mmap_size = 100 * 1024 * 1024  # 100MB
        
        # Forensic artifacts
        self._artifacts: Dict[str, ForensicArtifact] = {}
        self._artifact_storage = self.storage_path / 'artifacts'
        self._artifact_storage.mkdir(exist_ok=True)
        
        # Correlation engine
        self._correlation_window = timedelta(minutes=10)
        self._correlation_cache: Dict[str, List[AuditEvent]] = defaultdict(list)
        
        # Integrity verification
        self._checkpoints: List[Dict[str, Any]] = []
        self._checkpoint_interval = 1000  # Every 1000 events
        
        # Performance optimization
        self._buffer: deque = deque(maxlen=100)
        self._flush_interval = 10  # Flush every 10 events
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Initialize database
        self._initialize_database()
        
        # Initialize memory-mapped file
        self._initialize_mmap()
    
    def _create_genesis_block(self) -> str:
        """Create the genesis block hash."""
        genesis_data = {
            'type': 'genesis',
            'timestamp': datetime.utcnow().isoformat(),
            'system': 'DevDocAI Security Module',
            'version': '3.0.0'
        }
        return hashlib.sha256(
            json.dumps(genesis_data, sort_keys=True).encode()
        ).hexdigest()
    
    def _initialize_database(self):
        """Initialize SQLite database for audit storage."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id TEXT PRIMARY KEY,
                    timestamp TIMESTAMP,
                    level INTEGER,
                    category TEXT,
                    action TEXT,
                    actor TEXT,
                    target TEXT,
                    result TEXT,
                    previous_hash TEXT,
                    event_hash TEXT UNIQUE,
                    block_number INTEGER,
                    source_ip TEXT,
                    session_id TEXT,
                    correlation_id TEXT,
                    metadata TEXT,
                    evidence TEXT
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON audit_events(timestamp)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_actor 
                ON audit_events(actor)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_correlation 
                ON audit_events(correlation_id)
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS checkpoints (
                    checkpoint_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    block_number INTEGER,
                    chain_hash TEXT,
                    timestamp TIMESTAMP,
                    event_count INTEGER,
                    signature TEXT
                )
            ''')
            
            conn.commit()
    
    def _initialize_mmap(self):
        """Initialize memory-mapped file for fast access."""
        try:
            mmap_path = self.storage_path / 'audit.mmap'
            
            # Create or open file
            if not mmap_path.exists():
                with open(mmap_path, 'wb') as f:
                    f.write(b'\x00' * self._mmap_size)
            
            # Memory map the file
            with open(mmap_path, 'r+b') as f:
                self._mmap_file = mmap.mmap(
                    f.fileno(), 
                    self._mmap_size,
                    access=mmap.ACCESS_WRITE
                )
        except Exception as e:
            logger.error(f"Failed to initialize memory-mapped file: {e}")
    
    def log_event(
        self,
        level: AuditLevel,
        category: EventCategory,
        action: str,
        actor: str,
        target: str,
        result: str,
        metadata: Optional[Dict[str, Any]] = None,
        evidence: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """
        Log an audit event with blockchain chaining.
        
        Returns:
            Event ID
        """
        with self._lock:
            # Generate event ID
            event_id = hashlib.sha256(
                f"{datetime.utcnow()}{actor}{action}{target}".encode()
            ).hexdigest()[:16]
            
            # Get previous hash
            previous_hash = self._chain[-1].event_hash if self._chain else self._genesis_hash
            
            # Create event
            event = AuditEvent(
                event_id=event_id,
                timestamp=datetime.utcnow(),
                level=level,
                category=category,
                action=action,
                actor=actor,
                target=target,
                result=result,
                previous_hash=previous_hash,
                event_hash="",  # Will be calculated
                block_number=self._current_block,
                source_ip=kwargs.get('source_ip'),
                user_agent=kwargs.get('user_agent'),
                session_id=kwargs.get('session_id'),
                correlation_id=kwargs.get('correlation_id'),
                metadata=metadata or {},
                evidence=evidence or []
            )
            
            # Calculate hash
            event.event_hash = event.calculate_hash()
            
            # Add to chain
            self._chain.append(event)
            self._current_block += 1
            
            # Add to buffer
            self._buffer.append(event)
            
            # Flush if needed
            if len(self._buffer) >= self._flush_interval:
                self._flush_buffer()
            
            # Create checkpoint if needed
            if self._current_block % self._checkpoint_interval == 0:
                self._create_checkpoint()
            
            # Update correlation cache
            if event.correlation_id:
                self._correlation_cache[event.correlation_id].append(event)
            
            return event_id
    
    def _flush_buffer(self):
        """Flush buffered events to database."""
        if not self._buffer:
            return
        
        try:
            with sqlite3.connect(self._db_path) as conn:
                for event in self._buffer:
                    conn.execute('''
                        INSERT INTO audit_events VALUES (
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                        )
                    ''', (
                        event.event_id,
                        event.timestamp,
                        event.level.value,
                        event.category.value,
                        event.action,
                        event.actor,
                        event.target,
                        event.result,
                        event.previous_hash,
                        event.event_hash,
                        event.block_number,
                        event.source_ip,
                        event.session_id,
                        event.correlation_id,
                        json.dumps(event.metadata),
                        json.dumps(event.evidence)
                    ))
                conn.commit()
            
            self._buffer.clear()
        except Exception as e:
            logger.error(f"Failed to flush buffer: {e}")
    
    def _create_checkpoint(self):
        """Create a checkpoint for integrity verification."""
        with self._lock:
            # Calculate chain hash
            chain_data = ''.join(e.event_hash for e in self._chain[-self._checkpoint_interval:])
            chain_hash = hashlib.sha256(chain_data.encode()).hexdigest()
            
            checkpoint = {
                'block_number': self._current_block,
                'chain_hash': chain_hash,
                'timestamp': datetime.utcnow(),
                'event_count': len(self._chain),
                'signature': self._sign_checkpoint(chain_hash)
            }
            
            self._checkpoints.append(checkpoint)
            
            # Store in database
            try:
                with sqlite3.connect(self._db_path) as conn:
                    conn.execute('''
                        INSERT INTO checkpoints 
                        (block_number, chain_hash, timestamp, event_count, signature)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        checkpoint['block_number'],
                        checkpoint['chain_hash'],
                        checkpoint['timestamp'],
                        checkpoint['event_count'],
                        checkpoint['signature']
                    ))
                    conn.commit()
            except Exception as e:
                logger.error(f"Failed to store checkpoint: {e}")
    
    def _sign_checkpoint(self, data: str) -> str:
        """Sign checkpoint data (placeholder for real signing)."""
        # In production, use proper digital signatures
        return hashlib.sha512(f"{data}:secret_key".encode()).hexdigest()
    
    def verify_integrity(
        self, 
        start_block: int = 0, 
        end_block: Optional[int] = None
    ) -> Tuple[bool, List[str]]:
        """
        Verify blockchain integrity.
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        with self._lock:
            issues = []
            end_block = end_block or self._current_block
            
            # Verify chain continuity
            for i in range(start_block + 1, min(end_block, len(self._chain))):
                event = self._chain[i]
                prev_event = self._chain[i - 1]
                
                # Check previous hash
                if event.previous_hash != prev_event.event_hash:
                    issues.append(
                        f"Chain broken at block {i}: "
                        f"expected {prev_event.event_hash}, got {event.previous_hash}"
                    )
                
                # Verify event hash
                calculated_hash = event.calculate_hash()
                if calculated_hash != event.event_hash:
                    issues.append(
                        f"Event {event.event_id} has been tampered: "
                        f"expected {calculated_hash}, got {event.event_hash}"
                    )
            
            # Verify checkpoints
            for checkpoint in self._checkpoints:
                if start_block <= checkpoint['block_number'] <= end_block:
                    # Verify signature
                    expected_sig = self._sign_checkpoint(checkpoint['chain_hash'])
                    if checkpoint['signature'] != expected_sig:
                        issues.append(
                            f"Checkpoint at block {checkpoint['block_number']} "
                            f"has invalid signature"
                        )
            
            return len(issues) == 0, issues
    
    def collect_artifact(
        self,
        artifact_type: str,
        source: str,
        data: bytes,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Collect and store a forensic artifact.
        
        Returns:
            Artifact ID
        """
        with self._lock:
            # Generate artifact ID
            artifact_id = hashlib.sha256(
                f"{datetime.utcnow()}{artifact_type}{source}".encode()
            ).hexdigest()[:16]
            
            # Calculate hash
            data_hash = hashlib.sha256(data).hexdigest()
            
            # Store artifact
            storage_path = self._artifact_storage / f"{artifact_id}.gz"
            with gzip.open(storage_path, 'wb') as f:
                f.write(data)
            
            # Create artifact record
            artifact = ForensicArtifact(
                artifact_id=artifact_id,
                collected_at=datetime.utcnow(),
                artifact_type=artifact_type,
                source=source,
                size_bytes=len(data),
                hash_sha256=data_hash,
                storage_path=storage_path,
                metadata=metadata or {},
                chain_of_custody=[
                    {
                        'action': 'collected',
                        'timestamp': datetime.utcnow().isoformat(),
                        'actor': 'system'
                    }
                ]
            )
            
            self._artifacts[artifact_id] = artifact
            
            # Log collection
            self.log_event(
                level=AuditLevel.FORENSIC,
                category=EventCategory.SECURITY,
                action='artifact_collected',
                actor='forensics_system',
                target=source,
                result='success',
                metadata={
                    'artifact_id': artifact_id,
                    'type': artifact_type,
                    'size': len(data),
                    'hash': data_hash
                }
            )
            
            return artifact_id
    
    def analyze_correlation(
        self, 
        correlation_id: str,
        time_window: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """
        Analyze correlated events for patterns.
        
        Returns:
            Analysis results
        """
        with self._lock:
            events = self._correlation_cache.get(correlation_id, [])
            
            if not events:
                # Query from database
                events = self._query_correlated_events(correlation_id, time_window)
            
            if not events:
                return {'status': 'no_events'}
            
            # Analyze patterns
            analysis = {
                'correlation_id': correlation_id,
                'event_count': len(events),
                'time_span': (events[-1].timestamp - events[0].timestamp).total_seconds(),
                'actors': list(set(e.actor for e in events)),
                'targets': list(set(e.target for e in events)),
                'categories': defaultdict(int),
                'levels': defaultdict(int),
                'timeline': [],
                'anomalies': []
            }
            
            for event in events:
                analysis['categories'][event.category.value] += 1
                analysis['levels'][event.level.name] += 1
                analysis['timeline'].append({
                    'timestamp': event.timestamp.isoformat(),
                    'action': event.action,
                    'result': event.result
                })
            
            # Detect anomalies
            analysis['anomalies'] = self._detect_anomalies(events)
            
            return analysis
    
    def _query_correlated_events(
        self, 
        correlation_id: str,
        time_window: Optional[timedelta] = None
    ) -> List[AuditEvent]:
        """Query correlated events from database."""
        events = []
        
        try:
            with sqlite3.connect(self._db_path) as conn:
                query = 'SELECT * FROM audit_events WHERE correlation_id = ?'
                params = [correlation_id]
                
                if time_window:
                    cutoff = datetime.utcnow() - time_window
                    query += ' AND timestamp > ?'
                    params.append(cutoff)
                
                cursor = conn.execute(query, params)
                
                for row in cursor:
                    # Reconstruct AuditEvent from row
                    event = self._row_to_event(row)
                    events.append(event)
        except Exception as e:
            logger.error(f"Failed to query events: {e}")
        
        return events
    
    def _row_to_event(self, row: tuple) -> AuditEvent:
        """Convert database row to AuditEvent."""
        return AuditEvent(
            event_id=row[0],
            timestamp=datetime.fromisoformat(row[1]),
            level=AuditLevel(row[2]),
            category=EventCategory(row[3]),
            action=row[4],
            actor=row[5],
            target=row[6],
            result=row[7],
            previous_hash=row[8],
            event_hash=row[9],
            block_number=row[10],
            source_ip=row[11],
            session_id=row[12],
            correlation_id=row[13],
            metadata=json.loads(row[14]) if row[14] else {},
            evidence=json.loads(row[15]) if row[15] else []
        )
    
    def _detect_anomalies(self, events: List[AuditEvent]) -> List[str]:
        """Detect anomalies in event sequence."""
        anomalies = []
        
        # Check for rapid succession of failures
        failure_count = 0
        failure_window = []
        
        for event in events:
            if event.result == 'failure':
                failure_count += 1
                failure_window.append(event.timestamp)
                
                # Check if too many failures in short time
                if len(failure_window) >= 5:
                    time_span = (failure_window[-1] - failure_window[0]).total_seconds()
                    if time_span < 60:  # 5 failures in 1 minute
                        anomalies.append(
                            f"Rapid failure pattern detected: "
                            f"{len(failure_window)} failures in {time_span}s"
                        )
        
        # Check for privilege escalation patterns
        privilege_actions = ['grant_permission', 'add_role', 'elevate_privilege']
        privilege_events = [e for e in events if any(p in e.action for p in privilege_actions)]
        
        if len(privilege_events) >= 3:
            anomalies.append(
                f"Multiple privilege changes detected: {len(privilege_events)} events"
            )
        
        return anomalies
    
    def generate_compliance_report(
        self,
        start_date: datetime,
        end_date: datetime,
        compliance_framework: str = 'SOC2'
    ) -> Dict[str, Any]:
        """
        Generate compliance evidence report.
        
        Args:
            start_date: Report start date
            end_date: Report end date
            compliance_framework: Framework (SOC2, GDPR, HIPAA, etc.)
        
        Returns:
            Compliance report data
        """
        with self._lock:
            report = {
                'framework': compliance_framework,
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'evidence': [],
                'statistics': {},
                'integrity_status': 'verified',
                'generated_at': datetime.utcnow().isoformat()
            }
            
            # Query events in time range
            try:
                with sqlite3.connect(self._db_path) as conn:
                    cursor = conn.execute('''
                        SELECT * FROM audit_events 
                        WHERE timestamp BETWEEN ? AND ?
                        ORDER BY timestamp
                    ''', (start_date, end_date))
                    
                    events = [self._row_to_event(row) for row in cursor]
            except Exception as e:
                logger.error(f"Failed to query events for report: {e}")
                events = []
            
            # Collect evidence based on framework
            if compliance_framework == 'SOC2':
                report['evidence'] = self._collect_soc2_evidence(events)
            elif compliance_framework == 'GDPR':
                report['evidence'] = self._collect_gdpr_evidence(events)
            elif compliance_framework == 'HIPAA':
                report['evidence'] = self._collect_hipaa_evidence(events)
            
            # Calculate statistics
            report['statistics'] = {
                'total_events': len(events),
                'security_events': sum(1 for e in events if e.category == EventCategory.SECURITY),
                'failed_authentications': sum(
                    1 for e in events 
                    if e.category == EventCategory.AUTHENTICATION and e.result == 'failure'
                ),
                'configuration_changes': sum(
                    1 for e in events if e.category == EventCategory.CONFIGURATION
                ),
                'data_access_events': sum(
                    1 for e in events if e.category == EventCategory.DATA_ACCESS
                )
            }
            
            # Verify integrity for the period
            is_valid, issues = self.verify_integrity()
            if not is_valid:
                report['integrity_status'] = 'compromised'
                report['integrity_issues'] = issues
            
            return report
    
    def _collect_soc2_evidence(self, events: List[AuditEvent]) -> List[Dict[str, Any]]:
        """Collect SOC 2 compliance evidence."""
        evidence = []
        
        # Security principle evidence
        security_events = [e for e in events if e.category == EventCategory.SECURITY]
        evidence.append({
            'principle': 'Security',
            'control': 'Access Control',
            'evidence_count': len(security_events),
            'samples': [asdict(e) for e in security_events[:10]]
        })
        
        # Availability principle evidence
        system_events = [e for e in events if e.category == EventCategory.SYSTEM]
        evidence.append({
            'principle': 'Availability',
            'control': 'System Monitoring',
            'evidence_count': len(system_events),
            'samples': [asdict(e) for e in system_events[:10]]
        })
        
        return evidence
    
    def _collect_gdpr_evidence(self, events: List[AuditEvent]) -> List[Dict[str, Any]]:
        """Collect GDPR compliance evidence."""
        evidence = []
        
        # Data access evidence
        data_events = [e for e in events if e.category == EventCategory.DATA_ACCESS]
        evidence.append({
            'requirement': 'Data Access Logging',
            'article': 'Article 32',
            'evidence_count': len(data_events),
            'samples': [asdict(e) for e in data_events[:10]]
        })
        
        return evidence
    
    def _collect_hipaa_evidence(self, events: List[AuditEvent]) -> List[Dict[str, Any]]:
        """Collect HIPAA compliance evidence."""
        evidence = []
        
        # Access control evidence
        auth_events = [e for e in events if e.category == EventCategory.AUTHENTICATION]
        evidence.append({
            'safeguard': 'Access Control',
            'section': '164.312(a)',
            'evidence_count': len(auth_events),
            'samples': [asdict(e) for e in auth_events[:10]]
        })
        
        return evidence
    
    def export_for_siem(
        self, 
        format: str = 'json',
        last_n_events: int = 1000
    ) -> str:
        """
        Export events for SIEM integration.
        
        Args:
            format: Export format (json, cef, leef)
            last_n_events: Number of recent events to export
        
        Returns:
            Exported data string
        """
        with self._lock:
            # Get recent events
            events = self._chain[-last_n_events:] if len(self._chain) > last_n_events else self._chain
            
            if format == 'json':
                return json.dumps([asdict(e) for e in events], default=str)
            elif format == 'cef':
                return self._export_cef(events)
            elif format == 'leef':
                return self._export_leef(events)
            else:
                raise ValueError(f"Unsupported format: {format}")
    
    def _export_cef(self, events: List[AuditEvent]) -> str:
        """Export events in CEF (Common Event Format)."""
        cef_events = []
        
        for event in events:
            cef = (
                f"CEF:0|DevDocAI|SecurityModule|3.0.0|{event.event_id}|"
                f"{event.action}|{event.level.value}|"
                f"cat={event.category.value} "
                f"act={event.action} "
                f"src={event.source_ip or 'unknown'} "
                f"suser={event.actor} "
                f"dst={event.target} "
                f"outcome={event.result}"
            )
            cef_events.append(cef)
        
        return '\n'.join(cef_events)
    
    def _export_leef(self, events: List[AuditEvent]) -> str:
        """Export events in LEEF (Log Event Extended Format)."""
        leef_events = []
        
        for event in events:
            leef = (
                f"LEEF:1.0|DevDocAI|SecurityModule|3.0.0|{event.event_id}|"
                f"cat={event.category.value}|"
                f"devTime={event.timestamp.isoformat()}|"
                f"sev={event.level.value}|"
                f"usrName={event.actor}|"
                f"action={event.action}|"
                f"dst={event.target}"
            )
            leef_events.append(leef)
        
        return '\n'.join(leef_events)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get audit and forensics statistics."""
        with self._lock:
            self._flush_buffer()  # Ensure all events are persisted
            
            return {
                'total_events': len(self._chain),
                'current_block': self._current_block,
                'checkpoints': len(self._checkpoints),
                'artifacts_collected': len(self._artifacts),
                'correlation_groups': len(self._correlation_cache),
                'buffer_size': len(self._buffer),
                'database_size': self._db_path.stat().st_size if self._db_path.exists() else 0,
                'archive_size': sum(
                    f.stat().st_size for f in self._archive_path.glob('*')
                ) if self._archive_path.exists() else 0
            }