"""
Threat Detector - Real-time security monitoring and threat detection.

Monitors system activities, detects suspicious patterns, and generates
security alerts for potential threats and vulnerabilities.
"""

import logging
import time
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Set, Callable
from enum import Enum
from dataclasses import dataclass, field
from collections import deque, defaultdict
import asyncio
import threading

logger = logging.getLogger(__name__)


class ThreatLevel(str, Enum):
    """Threat severity levels."""
    LOW = "low"           # Informational, no immediate action needed
    MEDIUM = "medium"     # Attention required, monitor closely
    HIGH = "high"         # Action required, potential security risk
    CRITICAL = "critical" # Immediate action required, active threat


class ThreatType(str, Enum):
    """Types of security threats."""
    AUTHENTICATION_FAILURE = "auth_failure"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    MALWARE_DETECTION = "malware"
    INJECTION_ATTEMPT = "injection"
    RATE_LIMIT_EXCEEDED = "rate_limit"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_INTEGRITY = "data_integrity"
    CONFIGURATION_CHANGE = "config_change"


@dataclass
class SecurityThreat:
    """Security threat information."""
    threat_id: str
    threat_type: ThreatType
    level: ThreatLevel
    title: str
    description: str
    
    # Context information
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    resource: Optional[str] = None
    
    # Timing
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    
    # Evidence and metrics
    confidence_score: float = 0.0
    evidence: Dict[str, Any] = field(default_factory=dict)
    affected_systems: List[str] = field(default_factory=list)
    
    # Response status
    status: str = "active"  # active, investigating, resolved, false_positive
    assigned_to: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'threat_id': self.threat_id,
            'threat_type': self.threat_type.value,
            'level': self.level.value,
            'title': self.title,
            'description': self.description,
            'user_id': self.user_id,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'resource': self.resource,
            'detected_at': self.detected_at.isoformat(),
            'first_seen': self.first_seen.isoformat() if self.first_seen else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'confidence_score': self.confidence_score,
            'evidence': self.evidence,
            'affected_systems': self.affected_systems,
            'status': self.status,
            'assigned_to': self.assigned_to,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolution_notes': self.resolution_notes
        }


class ThreatDetector:
    """
    Real-time security threat detection system.
    
    Monitors system activities, analyzes patterns, and detects potential
    security threats using rule-based detection and anomaly analysis.
    """
    
    def __init__(self, security_manager=None, real_time_monitoring: bool = True):
        """
        Initialize threat detector.
        
        Args:
            security_manager: Security manager instance
            real_time_monitoring: Enable real-time monitoring
        """
        self.security_manager = security_manager
        self.real_time_monitoring = real_time_monitoring
        
        # Threat storage
        self.active_threats = {}  # threat_id -> SecurityThreat
        self.threat_history = deque(maxlen=10000)  # Keep last 10K threats
        
        # Pattern tracking
        self.failed_attempts = defaultdict(list)  # IP -> list of attempt times
        self.user_activity = defaultdict(list)    # user_id -> list of activities
        self.resource_access = defaultdict(int)   # resource -> access count
        
        # Configuration
        self.detection_rules = self._initialize_detection_rules()
        self.thresholds = {
            'failed_login_attempts': 5,      # per 15 minutes
            'rate_limit_requests': 100,      # per minute  
            'unusual_activity_score': 0.8,   # confidence threshold
            'data_access_volume': 1000000,   # bytes per hour
        }
        
        # Alert handlers
        self.alert_handlers: List[Callable] = []
        
        # Monitoring thread
        self._monitoring_active = False
        self._monitoring_thread = None
        
        if real_time_monitoring:
            self.start_monitoring()
        
        logger.info("ThreatDetector initialized")
    
    def start_monitoring(self):
        """Start real-time monitoring."""
        if self._monitoring_active:
            return
        
        self._monitoring_active = True
        self._monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitoring_thread.start()
        logger.info("Real-time threat monitoring started")
    
    def stop_monitoring(self):
        """Stop real-time monitoring."""
        self._monitoring_active = False
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=5)
        logger.info("Real-time threat monitoring stopped")
    
    async def scan_for_threats(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scan data for potential threats.
        
        Args:
            data: Data to analyze for threats
            
        Returns:
            Threat analysis results
        """
        start_time = time.perf_counter()
        scan_id = f"scan_{int(time.time() * 1000)}"
        
        threats_detected = []
        
        try:
            # Apply detection rules
            for rule_name, rule_func in self.detection_rules.items():
                try:
                    rule_threats = rule_func(data)
                    if rule_threats:
                        threats_detected.extend(rule_threats)
                        logger.info(f"Rule {rule_name} detected {len(rule_threats)} threat(s)")
                        
                except Exception as e:
                    logger.error(f"Error in detection rule {rule_name}: {e}")
            
            # Process detected threats
            processed_threats = []
            for threat in threats_detected:
                processed_threat = self._process_threat(threat)
                processed_threats.append(processed_threat)
                
                # Trigger alerts for high/critical threats
                if threat.level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
                    await self._trigger_alert(threat)
            
            scan_time = (time.perf_counter() - start_time) * 1000
            
            return {
                'scan_id': scan_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'threats_detected': len(processed_threats),
                'threats': [t.to_dict() for t in processed_threats],
                'scan_time_ms': scan_time,
                'highest_threat_level': max([t.level.value for t in processed_threats], default='none')
            }
            
        except Exception as e:
            logger.error(f"Threat scanning failed: {e}")
            return {
                'scan_id': scan_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e),
                'threats_detected': 0,
                'threats': [],
                'scan_time_ms': (time.perf_counter() - start_time) * 1000
            }
    
    def _initialize_detection_rules(self) -> Dict[str, Callable]:
        """Initialize threat detection rules."""
        return {
            'failed_authentication': self._detect_failed_authentication,
            'rate_limiting': self._detect_rate_limiting_violations,
            'suspicious_user_activity': self._detect_suspicious_activity,
            'data_access_anomalies': self._detect_data_access_anomalies,
            'injection_attempts': self._detect_injection_attempts,
            'privilege_escalation': self._detect_privilege_escalation,
            'configuration_tampering': self._detect_config_tampering,
            'malicious_patterns': self._detect_malicious_patterns
        }
    
    def _detect_failed_authentication(self, data: Dict[str, Any]) -> List[SecurityThreat]:
        """Detect authentication failure patterns."""
        threats = []
        
        # Check for repeated failed login attempts
        if data.get('event_type') == 'authentication_failure':
            ip_address = data.get('ip_address')
            user_id = data.get('user_id')
            
            if ip_address:
                now = datetime.now(timezone.utc)
                self.failed_attempts[ip_address].append(now)
                
                # Clean old attempts (older than 15 minutes)
                cutoff = now - timedelta(minutes=15)
                self.failed_attempts[ip_address] = [
                    t for t in self.failed_attempts[ip_address] if t > cutoff
                ]
                
                # Check threshold
                if len(self.failed_attempts[ip_address]) >= self.thresholds['failed_login_attempts']:
                    threat = SecurityThreat(
                        threat_id=f"auth_failure_{ip_address}_{int(now.timestamp())}",
                        threat_type=ThreatType.AUTHENTICATION_FAILURE,
                        level=ThreatLevel.MEDIUM,
                        title=f"Multiple authentication failures from {ip_address}",
                        description=f"Detected {len(self.failed_attempts[ip_address])} failed login attempts in 15 minutes",
                        ip_address=ip_address,
                        user_id=user_id,
                        confidence_score=0.8,
                        evidence={
                            'failed_attempts': len(self.failed_attempts[ip_address]),
                            'time_window': '15 minutes',
                            'threshold': self.thresholds['failed_login_attempts']
                        }
                    )
                    threats.append(threat)
        
        return threats
    
    def _detect_rate_limiting_violations(self, data: Dict[str, Any]) -> List[SecurityThreat]:
        """Detect rate limiting violations.""" 
        threats = []
        
        # Check for excessive API requests
        if data.get('event_type') == 'api_request':
            user_id = data.get('user_id')
            ip_address = data.get('ip_address')
            
            # Track request counts (simplified - in production use time-based windows)
            request_count = data.get('request_count', 0)
            
            if request_count > self.thresholds['rate_limit_requests']:
                threat = SecurityThreat(
                    threat_id=f"rate_limit_{user_id or ip_address}_{int(time.time())}",
                    threat_type=ThreatType.RATE_LIMIT_EXCEEDED,
                    level=ThreatLevel.MEDIUM,
                    title="Rate limit exceeded",
                    description=f"Excessive API requests detected: {request_count}/minute",
                    user_id=user_id,
                    ip_address=ip_address,
                    confidence_score=0.9,
                    evidence={
                        'request_count': request_count,
                        'threshold': self.thresholds['rate_limit_requests'],
                        'time_window': '1 minute'
                    }
                )
                threats.append(threat)
        
        return threats
    
    def _detect_suspicious_activity(self, data: Dict[str, Any]) -> List[SecurityThreat]:
        """Detect suspicious user activity patterns."""
        threats = []
        
        # Analyze user behavior patterns
        user_id = data.get('user_id')
        if user_id:
            activity = data.get('activity_type')
            if activity:
                self.user_activity[user_id].append({
                    'activity': activity,
                    'timestamp': datetime.now(timezone.utc),
                    'resource': data.get('resource'),
                    'ip_address': data.get('ip_address')
                })
                
                # Analyze recent activity for anomalies
                recent_activities = self.user_activity[user_id][-50:]  # Last 50 activities
                
                # Check for unusual patterns
                if self._is_activity_suspicious(recent_activities):
                    threat = SecurityThreat(
                        threat_id=f"suspicious_activity_{user_id}_{int(time.time())}",
                        threat_type=ThreatType.SUSPICIOUS_ACTIVITY,
                        level=ThreatLevel.MEDIUM,
                        title=f"Suspicious activity pattern for user {user_id}",
                        description="Detected unusual user behavior patterns",
                        user_id=user_id,
                        confidence_score=0.7,
                        evidence={
                            'recent_activities_count': len(recent_activities),
                            'pattern_indicators': self._get_suspicious_indicators(recent_activities)
                        }
                    )
                    threats.append(threat)
        
        return threats
    
    def _detect_data_access_anomalies(self, data: Dict[str, Any]) -> List[SecurityThreat]:
        """Detect unusual data access patterns."""
        threats = []
        
        if data.get('event_type') == 'data_access':
            user_id = data.get('user_id')
            resource = data.get('resource')
            data_size = data.get('data_size', 0)
            
            # Track data access volume
            if data_size > self.thresholds['data_access_volume']:
                threat = SecurityThreat(
                    threat_id=f"data_access_{user_id}_{int(time.time())}",
                    threat_type=ThreatType.DATA_EXFILTRATION,
                    level=ThreatLevel.HIGH,
                    title="Large data access detected",
                    description=f"User accessed {data_size} bytes of data",
                    user_id=user_id,
                    resource=resource,
                    confidence_score=0.8,
                    evidence={
                        'data_size': data_size,
                        'threshold': self.thresholds['data_access_volume'],
                        'resource': resource
                    }
                )
                threats.append(threat)
        
        return threats
    
    def _detect_injection_attempts(self, data: Dict[str, Any]) -> List[SecurityThreat]:
        """Detect code injection attempts."""
        threats = []
        
        # Check for malicious input patterns
        input_data = data.get('input_data', '')
        if isinstance(input_data, str):
            # SQL injection patterns
            sql_patterns = [
                r"(?i)(union\s+select|select\s+.*\s+from|drop\s+table)",
                r"(?i)(or\s+1\s*=\s*1|and\s+1\s*=\s*1)",
                r"(?i)(exec\s*\(|execute\s*\()"
            ]
            
            # XSS patterns
            xss_patterns = [
                r"<script[^>]*>",
                r"javascript:",
                r"on\w+\s*="
            ]
            
            # Check patterns
            import re
            for pattern in sql_patterns + xss_patterns:
                if re.search(pattern, input_data):
                    threat = SecurityThreat(
                        threat_id=f"injection_{int(time.time())}",
                        threat_type=ThreatType.INJECTION_ATTEMPT,
                        level=ThreatLevel.HIGH,
                        title="Code injection attempt detected",
                        description=f"Malicious pattern found in input: {pattern}",
                        user_id=data.get('user_id'),
                        ip_address=data.get('ip_address'),
                        confidence_score=0.9,
                        evidence={
                            'pattern_matched': pattern,
                            'input_sample': input_data[:100],
                            'injection_type': 'SQL' if 'select' in pattern.lower() else 'XSS'
                        }
                    )
                    threats.append(threat)
                    break
        
        return threats
    
    def _detect_privilege_escalation(self, data: Dict[str, Any]) -> List[SecurityThreat]:
        """Detect privilege escalation attempts."""
        threats = []
        
        if data.get('event_type') == 'permission_change':
            user_id = data.get('user_id')
            old_role = data.get('old_role')
            new_role = data.get('new_role')
            
            # Check for suspicious privilege changes
            if old_role and new_role:
                privilege_levels = {'user': 1, 'moderator': 2, 'admin': 3, 'superuser': 4}
                old_level = privilege_levels.get(old_role, 0)
                new_level = privilege_levels.get(new_role, 0)
                
                if new_level > old_level:
                    threat = SecurityThreat(
                        threat_id=f"privilege_escalation_{user_id}_{int(time.time())}",
                        threat_type=ThreatType.PRIVILEGE_ESCALATION,
                        level=ThreatLevel.HIGH,
                        title=f"Privilege escalation for user {user_id}",
                        description=f"User role changed from {old_role} to {new_role}",
                        user_id=user_id,
                        confidence_score=0.7,
                        evidence={
                            'old_role': old_role,
                            'new_role': new_role,
                            'privilege_increase': new_level - old_level
                        }
                    )
                    threats.append(threat)
        
        return threats
    
    def _detect_config_tampering(self, data: Dict[str, Any]) -> List[SecurityThreat]:
        """Detect configuration tampering."""
        threats = []
        
        if data.get('event_type') == 'configuration_change':
            changed_settings = data.get('changed_settings', [])
            user_id = data.get('user_id')
            
            # Check for critical security settings
            critical_settings = ['security_mode', 'encryption_enabled', 'audit_logging']
            
            for setting in changed_settings:
                if setting in critical_settings:
                    threat = SecurityThreat(
                        threat_id=f"config_tampering_{int(time.time())}",
                        threat_type=ThreatType.CONFIGURATION_CHANGE,
                        level=ThreatLevel.HIGH,
                        title="Critical security configuration changed",
                        description=f"Security setting '{setting}' was modified",
                        user_id=user_id,
                        confidence_score=0.8,
                        evidence={
                            'changed_setting': setting,
                            'all_changes': changed_settings,
                            'criticality': 'high'
                        }
                    )
                    threats.append(threat)
        
        return threats
    
    def _detect_malicious_patterns(self, data: Dict[str, Any]) -> List[SecurityThreat]:
        """Detect known malicious patterns."""
        threats = []
        
        # Check for malware signatures or suspicious file patterns
        if data.get('event_type') == 'file_operation':
            filename = data.get('filename', '')
            file_content = data.get('file_content', '')
            
            # Check for suspicious file extensions
            suspicious_extensions = ['.exe', '.bat', '.cmd', '.scr', '.vbs']
            if any(filename.lower().endswith(ext) for ext in suspicious_extensions):
                threat = SecurityThreat(
                    threat_id=f"malware_{int(time.time())}",
                    threat_type=ThreatType.MALWARE_DETECTION,
                    level=ThreatLevel.HIGH,
                    title="Suspicious file detected",
                    description=f"File with suspicious extension: {filename}",
                    user_id=data.get('user_id'),
                    confidence_score=0.6,
                    evidence={
                        'filename': filename,
                        'file_extension': filename.split('.')[-1],
                        'detection_reason': 'suspicious_extension'
                    }
                )
                threats.append(threat)
        
        return threats
    
    def _is_activity_suspicious(self, activities: List[Dict[str, Any]]) -> bool:
        """Analyze if activity pattern is suspicious."""
        if len(activities) < 10:
            return False
        
        # Check for rapid consecutive actions
        timestamps = [act['timestamp'] for act in activities[-10:]]
        time_diffs = [(timestamps[i+1] - timestamps[i]).total_seconds() for i in range(len(timestamps)-1)]
        
        # If average time between actions is less than 1 second, it's suspicious
        avg_time_diff = sum(time_diffs) / len(time_diffs)
        if avg_time_diff < 1.0:
            return True
        
        # Check for unusual resource access patterns
        resources = [act.get('resource') for act in activities[-20:] if act.get('resource')]
        unique_resources = len(set(resources))
        
        # If accessing many different resources rapidly, it's suspicious
        if unique_resources > 10:
            return True
        
        return False
    
    def _get_suspicious_indicators(self, activities: List[Dict[str, Any]]) -> List[str]:
        """Get indicators of suspicious activity."""
        indicators = []
        
        if len(activities) >= 10:
            # Check rapid actions
            timestamps = [act['timestamp'] for act in activities[-10:]]
            time_diffs = [(timestamps[i+1] - timestamps[i]).total_seconds() for i in range(len(timestamps)-1)]
            avg_time_diff = sum(time_diffs) / len(time_diffs)
            
            if avg_time_diff < 1.0:
                indicators.append("Rapid consecutive actions")
            
            # Check resource diversity
            resources = [act.get('resource') for act in activities[-20:] if act.get('resource')]
            unique_resources = len(set(resources))
            
            if unique_resources > 10:
                indicators.append("High resource access diversity")
        
        return indicators
    
    def _process_threat(self, threat: SecurityThreat) -> SecurityThreat:
        """Process and enrich threat information."""
        # Store threat
        self.active_threats[threat.threat_id] = threat
        self.threat_history.append(threat)
        
        # Enrich with additional context
        threat.affected_systems = ['M010-Security']
        
        # Check for related threats
        similar_threats = self._find_similar_threats(threat)
        if similar_threats:
            threat.evidence['related_threats'] = [t.threat_id for t in similar_threats]
            
            # Update confidence based on pattern
            threat.confidence_score = min(1.0, threat.confidence_score + 0.1 * len(similar_threats))
        
        return threat
    
    def _find_similar_threats(self, threat: SecurityThreat) -> List[SecurityThreat]:
        """Find similar recent threats."""
        similar = []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)  # Last hour
        
        for existing_threat in self.active_threats.values():
            if (existing_threat.threat_type == threat.threat_type and
                existing_threat.detected_at > cutoff and
                existing_threat.threat_id != threat.threat_id):
                
                # Check for same IP or user
                if (existing_threat.ip_address == threat.ip_address or
                    existing_threat.user_id == threat.user_id):
                    similar.append(existing_threat)
        
        return similar
    
    async def _trigger_alert(self, threat: SecurityThreat):
        """Trigger alert for threat."""
        alert_data = {
            'threat': threat.to_dict(),
            'alert_time': datetime.now(timezone.utc).isoformat(),
            'alert_level': threat.level.value
        }
        
        # Call registered alert handlers
        for handler in self.alert_handlers:
            try:
                await handler(alert_data)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")
        
        # Log alert
        logger.warning(f"SECURITY ALERT [{threat.level.value.upper()}]: {threat.title}")
        
        # Audit log
        if self.security_manager and self.security_manager.audit_logger:
            self.security_manager.audit_logger.log_event('security_threat_detected', alert_data)
    
    def _monitoring_loop(self):
        """Background monitoring loop."""
        logger.info("Starting threat monitoring loop")
        
        while self._monitoring_active:
            try:
                # Cleanup old threats
                self._cleanup_old_threats()
                
                # Update threat levels based on patterns
                self._update_threat_levels()
                
                # Sleep before next check
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(30)  # Shorter sleep on error
    
    def _cleanup_old_threats(self):
        """Clean up old resolved threats."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)  # Keep for 7 days
        
        resolved_threats = [
            tid for tid, threat in self.active_threats.items()
            if threat.status == 'resolved' and threat.resolved_at and threat.resolved_at < cutoff
        ]
        
        for threat_id in resolved_threats:
            del self.active_threats[threat_id]
    
    def _update_threat_levels(self):
        """Update threat levels based on evolution.""" 
        # Escalate persistent threats
        for threat in self.active_threats.values():
            if threat.status == 'active':
                age = datetime.now(timezone.utc) - threat.detected_at
                
                # Escalate threats that persist
                if age > timedelta(hours=2) and threat.level == ThreatLevel.MEDIUM:
                    threat.level = ThreatLevel.HIGH
                    logger.info(f"Escalated threat {threat.threat_id} to HIGH level")
    
    def add_alert_handler(self, handler: Callable):
        """Add alert handler function."""
        self.alert_handlers.append(handler)
    
    def get_threat_statistics(self) -> Dict[str, Any]:
        """Get threat detection statistics."""
        total_threats = len(self.threat_history)
        active_threats = len([t for t in self.active_threats.values() if t.status == 'active'])
        
        # Count by type and level
        type_counts = defaultdict(int)
        level_counts = defaultdict(int)
        
        for threat in self.threat_history:
            type_counts[threat.threat_type.value] += 1
            level_counts[threat.level.value] += 1
        
        return {
            'total_threats_detected': total_threats,
            'active_threats': active_threats,
            'threats_by_type': dict(type_counts),
            'threats_by_level': dict(level_counts),
            'detection_rate': len(self.threat_history) / max(1, (time.time() - 86400)) * 86400,  # per day
            'average_confidence': sum(t.confidence_score for t in self.threat_history) / max(1, total_threats)
        }
    
    def shutdown(self):
        """Shutdown threat detector."""
        self.stop_monitoring()
        logger.info("ThreatDetector shutdown complete")