"""
M004 Document Generator - Security monitoring and audit system.

Comprehensive security monitoring, incident detection, and audit logging
for document generation operations.
"""

import logging
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import hashlib
import time

from ...common.logging import get_logger
from ...common.security import AuditLogger, get_audit_logger

logger = get_logger(__name__)


@dataclass
class SecurityIncident:
    """Security incident data structure."""
    incident_id: str
    timestamp: datetime
    severity: str  # low, medium, high, critical
    category: str  # xss, injection, traversal, dos, etc.
    client_id: str
    template_name: str
    description: str
    details: Dict[str, Any]
    resolved: bool = False
    resolution_timestamp: Optional[datetime] = None
    resolution_notes: str = ""


@dataclass
class SecurityMetric:
    """Security metric data structure."""
    metric_name: str
    timestamp: datetime
    value: float
    tags: Dict[str, str]


class SecurityMonitor:
    """
    Comprehensive security monitoring system for M004.
    
    Features:
    - Real-time threat detection
    - Incident management and escalation
    - Security metrics collection
    - Anomaly detection
    - Rate limiting monitoring
    - PII exposure tracking
    - Performance impact monitoring
    - Compliance reporting
    """
    
    # Severity levels
    SEVERITY_CRITICAL = "critical"
    SEVERITY_HIGH = "high"
    SEVERITY_MEDIUM = "medium"
    SEVERITY_LOW = "low"
    
    # Incident categories
    CATEGORY_XSS = "xss"
    CATEGORY_INJECTION = "injection"
    CATEGORY_TRAVERSAL = "traversal"
    CATEGORY_DOS = "dos"
    CATEGORY_PII = "pii"
    CATEGORY_TEMPLATE = "template"
    CATEGORY_ACCESS = "access"
    CATEGORY_VALIDATION = "validation"
    
    # Thresholds for anomaly detection
    RATE_LIMIT_THRESHOLD = 100  # requests per hour
    ERROR_RATE_THRESHOLD = 0.1  # 10% error rate
    RESPONSE_TIME_THRESHOLD = 5.0  # 5 seconds
    
    def __init__(self, log_dir: Optional[Path] = None):
        """
        Initialize security monitor.
        
        Args:
            log_dir: Directory for security logs
        """
        self.log_dir = log_dir or Path.home() / '.devdocai' / 'security'
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.audit_logger = get_audit_logger()
        self._lock = threading.Lock()
        
        # Active incidents tracking
        self.active_incidents: Dict[str, SecurityIncident] = {}
        self.resolved_incidents: List[SecurityIncident] = []
        
        # Security metrics storage
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Client behavior tracking
        self.client_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'requests': deque(maxlen=100),
            'errors': deque(maxlen=100),
            'response_times': deque(maxlen=100),
            'security_violations': deque(maxlen=50),
            'blocked': False,
            'blocked_until': None
        })
        
        # Template usage tracking
        self.template_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'usage_count': 0,
            'error_count': 0,
            'security_incidents': 0,
            'last_used': None
        })
        
        # Anomaly detection state
        self.anomaly_baselines: Dict[str, float] = {}
        self.anomaly_windows: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        logger.info(f"SecurityMonitor initialized with log directory: {self.log_dir}")
    
    def report_security_event(
        self,
        event_type: str,
        severity: str,
        client_id: str,
        template_name: str,
        description: str,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Report a security event and potentially create an incident.
        
        Args:
            event_type: Type of security event
            severity: Event severity level
            client_id: Client identifier
            template_name: Template involved
            description: Event description
            details: Additional event details
            
        Returns:
            Incident ID if incident created, empty string otherwise
        """
        with self._lock:
            timestamp = datetime.now()
            details = details or {}
            
            # Log the security event
            self.audit_logger.log_event(f'security_{event_type}', {
                'severity': severity,
                'client_id': client_id,
                'template_name': template_name,
                'description': description,
                'details': details,
                'timestamp': timestamp.isoformat()
            })
            
            # Update client statistics
            self._update_client_stats(client_id, event_type, timestamp)
            
            # Update template statistics
            self._update_template_stats(template_name, event_type)
            
            # Determine if incident should be created
            incident_id = ""
            if self._should_create_incident(event_type, severity, client_id):
                incident_id = self._create_incident(
                    event_type, severity, client_id, template_name, 
                    description, details, timestamp
                )
            
            # Check for anomalies
            self._check_anomalies(event_type, client_id, template_name, timestamp)
            
            # Update security metrics
            self._update_security_metrics(event_type, severity, timestamp)
            
            return incident_id
    
    def report_validation_failure(
        self,
        client_id: str,
        template_name: str,
        failure_type: str,
        details: Dict[str, Any]
    ):
        """Report input validation failure."""
        self.report_security_event(
            event_type=self.CATEGORY_VALIDATION,
            severity=self.SEVERITY_MEDIUM,
            client_id=client_id,
            template_name=template_name,
            description=f"Validation failure: {failure_type}",
            details=details
        )
    
    def report_xss_attempt(
        self,
        client_id: str,
        template_name: str,
        pattern_detected: str,
        input_field: str
    ):
        """Report XSS attempt."""
        self.report_security_event(
            event_type=self.CATEGORY_XSS,
            severity=self.SEVERITY_HIGH,
            client_id=client_id,
            template_name=template_name,
            description=f"XSS attempt detected in field: {input_field}",
            details={
                'pattern': pattern_detected,
                'field': input_field
            }
        )
    
    def report_injection_attempt(
        self,
        client_id: str,
        template_name: str,
        injection_type: str,
        pattern_detected: str
    ):
        """Report injection attempt."""
        severity = self.SEVERITY_CRITICAL if injection_type in ['sql', 'template'] else self.SEVERITY_HIGH
        
        self.report_security_event(
            event_type=self.CATEGORY_INJECTION,
            severity=severity,
            client_id=client_id,
            template_name=template_name,
            description=f"{injection_type.upper()} injection attempt",
            details={
                'injection_type': injection_type,
                'pattern': pattern_detected
            }
        )
    
    def report_pii_exposure(
        self,
        client_id: str,
        template_name: str,
        pii_types: List[str],
        exposure_context: str
    ):
        """Report PII exposure."""
        self.report_security_event(
            event_type=self.CATEGORY_PII,
            severity=self.SEVERITY_HIGH,
            client_id=client_id,
            template_name=template_name,
            description=f"PII exposure detected: {', '.join(pii_types)}",
            details={
                'pii_types': pii_types,
                'context': exposure_context
            }
        )
    
    def report_rate_limit_exceeded(
        self,
        client_id: str,
        operation: str,
        current_rate: int,
        limit: int
    ):
        """Report rate limit exceeded."""
        self.report_security_event(
            event_type=self.CATEGORY_ACCESS,
            severity=self.SEVERITY_MEDIUM,
            client_id=client_id,
            template_name="system",
            description=f"Rate limit exceeded for {operation}",
            details={
                'operation': operation,
                'current_rate': current_rate,
                'limit': limit
            }
        )
    
    def report_dos_attempt(
        self,
        client_id: str,
        template_name: str,
        dos_type: str,
        details: Dict[str, Any]
    ):
        """Report potential DoS attempt."""
        self.report_security_event(
            event_type=self.CATEGORY_DOS,
            severity=self.SEVERITY_HIGH,
            client_id=client_id,
            template_name=template_name,
            description=f"Potential DoS attempt: {dos_type}",
            details=details
        )
    
    def record_request_metrics(
        self,
        client_id: str,
        template_name: str,
        response_time: float,
        success: bool,
        operation: str
    ):
        """Record request metrics for monitoring."""
        with self._lock:
            timestamp = datetime.now()
            
            # Update client stats
            client_stat = self.client_stats[client_id]
            client_stat['requests'].append(timestamp)
            client_stat['response_times'].append(response_time)
            
            if not success:
                client_stat['errors'].append(timestamp)
            
            # Update template stats
            template_stat = self.template_stats[template_name]
            template_stat['usage_count'] += 1
            template_stat['last_used'] = timestamp
            
            if not success:
                template_stat['error_count'] += 1
            
            # Record metrics for anomaly detection
            self._record_anomaly_metric(f'response_time_{operation}', response_time, timestamp)
            self._record_anomaly_metric(f'request_rate_{client_id}', 1.0, timestamp)
    
    def is_client_blocked(self, client_id: str) -> bool:
        """Check if client is currently blocked."""
        with self._lock:
            client_stat = self.client_stats[client_id]
            
            if not client_stat['blocked']:
                return False
            
            blocked_until = client_stat.get('blocked_until')
            if blocked_until and datetime.now() > blocked_until:
                # Unblock expired blocks
                client_stat['blocked'] = False
                client_stat['blocked_until'] = None
                return False
            
            return True
    
    def block_client(self, client_id: str, duration_minutes: int = 60, reason: str = ""):
        """Block a client for specified duration."""
        with self._lock:
            client_stat = self.client_stats[client_id]
            client_stat['blocked'] = True
            client_stat['blocked_until'] = datetime.now() + timedelta(minutes=duration_minutes)
            
            self.audit_logger.log_event('client_blocked', {
                'client_id': client_id,
                'duration_minutes': duration_minutes,
                'reason': reason,
                'timestamp': datetime.now().isoformat()
            })
            
            logger.warning(f"Client {client_id} blocked for {duration_minutes} minutes: {reason}")
    
    def get_security_dashboard(self) -> Dict[str, Any]:
        """Get security dashboard data."""
        with self._lock:
            now = datetime.now()
            last_hour = now - timedelta(hours=1)
            last_24h = now - timedelta(hours=24)
            
            # Count recent incidents
            recent_incidents = {
                'hour': 0,
                'day': 0,
                'by_severity': defaultdict(int),
                'by_category': defaultdict(int)
            }
            
            for incident in self.active_incidents.values():
                if incident.timestamp > last_hour:
                    recent_incidents['hour'] += 1
                if incident.timestamp > last_24h:
                    recent_incidents['day'] += 1
                
                recent_incidents['by_severity'][incident.severity] += 1
                recent_incidents['by_category'][incident.category] += 1
            
            # Client statistics
            active_clients = len([
                client_id for client_id, stats in self.client_stats.items()
                if stats['requests'] and list(stats['requests'])[-1] > last_hour
            ])
            
            blocked_clients = len([
                client_id for client_id, stats in self.client_stats.items()
                if stats['blocked']
            ])
            
            # Template statistics
            active_templates = len([
                template for template, stats in self.template_stats.items()
                if stats['last_used'] and stats['last_used'] > last_hour
            ])
            
            # Recent metrics
            recent_metrics = {}
            for metric_name, values in self.metrics.items():
                recent_values = [v for v in values if v.timestamp > last_hour]
                if recent_values:
                    recent_metrics[metric_name] = {
                        'count': len(recent_values),
                        'avg_value': sum(v.value for v in recent_values) / len(recent_values)
                    }
            
            dashboard = {
                'timestamp': now.isoformat(),
                'incidents': {
                    'active': len(self.active_incidents),
                    'recent_hour': recent_incidents['hour'],
                    'recent_day': recent_incidents['day'],
                    'by_severity': dict(recent_incidents['by_severity']),
                    'by_category': dict(recent_incidents['by_category'])
                },
                'clients': {
                    'active': active_clients,
                    'blocked': blocked_clients,
                    'total_tracked': len(self.client_stats)
                },
                'templates': {
                    'active': active_templates,
                    'total_tracked': len(self.template_stats)
                },
                'metrics': recent_metrics
            }
            
            return dashboard
    
    def get_client_risk_score(self, client_id: str) -> Dict[str, Any]:
        """Calculate risk score for a client."""
        with self._lock:
            if client_id not in self.client_stats:
                return {'risk_score': 0, 'factors': [], 'recommendation': 'allow'}
            
            client_stat = self.client_stats[client_id]
            now = datetime.now()
            last_hour = now - timedelta(hours=1)
            
            risk_factors = []
            risk_score = 0
            
            # Recent request volume
            recent_requests = [r for r in client_stat['requests'] if r > last_hour]
            if len(recent_requests) > 50:
                risk_score += 20
                risk_factors.append(f"High request volume: {len(recent_requests)} requests/hour")
            
            # Error rate
            recent_errors = [e for e in client_stat['errors'] if e > last_hour]
            if recent_requests:
                error_rate = len(recent_errors) / len(recent_requests)
                if error_rate > 0.2:  # 20% error rate
                    risk_score += 30
                    risk_factors.append(f"High error rate: {error_rate:.1%}")
            
            # Security violations
            recent_violations = [v for v in client_stat['security_violations'] if v > last_hour]
            if recent_violations:
                risk_score += len(recent_violations) * 15
                risk_factors.append(f"Security violations: {len(recent_violations)}")
            
            # Response time anomalies
            if client_stat['response_times']:
                avg_response_time = sum(client_stat['response_times']) / len(client_stat['response_times'])
                if avg_response_time > 10.0:  # 10 seconds
                    risk_score += 10
                    risk_factors.append(f"Slow response times: {avg_response_time:.1f}s avg")
            
            # Current block status
            if client_stat['blocked']:
                risk_score += 50
                risk_factors.append("Currently blocked")
            
            # Determine recommendation
            if risk_score >= 80:
                recommendation = 'block'
            elif risk_score >= 50:
                recommendation = 'monitor'
            elif risk_score >= 20:
                recommendation = 'watch'
            else:
                recommendation = 'allow'
            
            return {
                'risk_score': min(risk_score, 100),
                'factors': risk_factors,
                'recommendation': recommendation,
                'client_id': client_id,
                'timestamp': now.isoformat()
            }
    
    def generate_security_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate comprehensive security report."""
        with self._lock:
            now = datetime.now()
            cutoff = now - timedelta(hours=hours)
            
            # Filter incidents by time period
            period_incidents = [
                incident for incident in list(self.active_incidents.values()) + self.resolved_incidents
                if incident.timestamp > cutoff
            ]
            
            # Incident analysis
            incident_analysis = {
                'total': len(period_incidents),
                'by_severity': defaultdict(int),
                'by_category': defaultdict(int),
                'by_client': defaultdict(int),
                'by_template': defaultdict(int),
                'resolution_rate': 0
            }
            
            resolved_count = 0
            for incident in period_incidents:
                incident_analysis['by_severity'][incident.severity] += 1
                incident_analysis['by_category'][incident.category] += 1
                incident_analysis['by_client'][incident.client_id] += 1
                incident_analysis['by_template'][incident.template_name] += 1
                
                if incident.resolved:
                    resolved_count += 1
            
            if period_incidents:
                incident_analysis['resolution_rate'] = resolved_count / len(period_incidents)
            
            # Client analysis
            client_analysis = {}
            for client_id, stats in self.client_stats.items():
                recent_requests = [r for r in stats['requests'] if r > cutoff]
                recent_errors = [e for e in stats['errors'] if e > cutoff]
                recent_violations = [v for v in stats['security_violations'] if v > cutoff]
                
                if recent_requests or recent_errors or recent_violations:
                    client_analysis[client_id] = {
                        'requests': len(recent_requests),
                        'errors': len(recent_errors),
                        'violations': len(recent_violations),
                        'blocked': stats['blocked'],
                        'risk_score': self.get_client_risk_score(client_id)['risk_score']
                    }
            
            # Template analysis
            template_analysis = {}
            for template_name, stats in self.template_stats.items():
                if stats['last_used'] and stats['last_used'] > cutoff:
                    template_analysis[template_name] = {
                        'usage_count': stats['usage_count'],
                        'error_count': stats['error_count'],
                        'security_incidents': stats['security_incidents'],
                        'last_used': stats['last_used'].isoformat()
                    }
            
            report = {
                'report_period': f"{hours} hours",
                'generated_at': now.isoformat(),
                'summary': {
                    'total_incidents': len(period_incidents),
                    'active_incidents': len(self.active_incidents),
                    'resolution_rate': incident_analysis['resolution_rate'],
                    'unique_clients': len(client_analysis),
                    'active_templates': len(template_analysis)
                },
                'incidents': {
                    'analysis': dict(incident_analysis),
                    'details': [asdict(incident) for incident in period_incidents[-10:]]  # Last 10
                },
                'clients': client_analysis,
                'templates': template_analysis,
                'top_threats': self._get_top_threats(period_incidents),
                'recommendations': self._generate_recommendations(incident_analysis, client_analysis)
            }
            
            return report
    
    def _should_create_incident(self, event_type: str, severity: str, client_id: str) -> bool:
        """Determine if an incident should be created."""
        # Always create incidents for critical and high severity events
        if severity in [self.SEVERITY_CRITICAL, self.SEVERITY_HIGH]:
            return True
        
        # Create incidents for medium severity if client has history
        if severity == self.SEVERITY_MEDIUM:
            client_stat = self.client_stats[client_id]
            recent_violations = [
                v for v in client_stat['security_violations']
                if v > datetime.now() - timedelta(hours=1)
            ]
            return len(recent_violations) >= 3  # 3 violations in an hour
        
        return False
    
    def _create_incident(
        self,
        event_type: str,
        severity: str,
        client_id: str,
        template_name: str,
        description: str,
        details: Dict[str, Any],
        timestamp: datetime
    ) -> str:
        """Create a new security incident."""
        incident_id = hashlib.sha256(
            f"{timestamp.isoformat()}-{client_id}-{event_type}".encode()
        ).hexdigest()[:16]
        
        incident = SecurityIncident(
            incident_id=incident_id,
            timestamp=timestamp,
            severity=severity,
            category=event_type,
            client_id=client_id,
            template_name=template_name,
            description=description,
            details=details
        )
        
        self.active_incidents[incident_id] = incident
        
        logger.warning(f"Security incident created: {incident_id} - {description}")
        
        return incident_id
    
    def _update_client_stats(self, client_id: str, event_type: str, timestamp: datetime):
        """Update client statistics."""
        client_stat = self.client_stats[client_id]
        
        if event_type in [self.CATEGORY_XSS, self.CATEGORY_INJECTION, 
                         self.CATEGORY_TRAVERSAL, self.CATEGORY_PII]:
            client_stat['security_violations'].append(timestamp)
    
    def _update_template_stats(self, template_name: str, event_type: str):
        """Update template statistics."""
        template_stat = self.template_stats[template_name]
        
        if event_type in [self.CATEGORY_XSS, self.CATEGORY_INJECTION, 
                         self.CATEGORY_TRAVERSAL, self.CATEGORY_PII]:
            template_stat['security_incidents'] += 1
    
    def _check_anomalies(self, event_type: str, client_id: str, template_name: str, timestamp: datetime):
        """Check for anomalous patterns."""
        # Check for burst of events from same client
        client_stat = self.client_stats[client_id]
        recent_violations = [
            v for v in client_stat['security_violations']
            if v > timestamp - timedelta(minutes=5)
        ]
        
        if len(recent_violations) >= 5:  # 5 violations in 5 minutes
            self.report_security_event(
                event_type=self.CATEGORY_DOS,
                severity=self.SEVERITY_HIGH,
                client_id=client_id,
                template_name="system",
                description="Anomalous burst of security violations",
                details={'violation_count': len(recent_violations)}
            )
    
    def _update_security_metrics(self, event_type: str, severity: str, timestamp: datetime):
        """Update security metrics."""
        # Event count metric
        metric = SecurityMetric(
            metric_name=f'security_events_{event_type}',
            timestamp=timestamp,
            value=1.0,
            tags={'severity': severity}
        )
        self.metrics[metric.metric_name].append(metric)
        
        # Severity metric
        severity_score = {
            self.SEVERITY_LOW: 1,
            self.SEVERITY_MEDIUM: 2,
            self.SEVERITY_HIGH: 3,
            self.SEVERITY_CRITICAL: 4
        }.get(severity, 1)
        
        severity_metric = SecurityMetric(
            metric_name='security_severity_score',
            timestamp=timestamp,
            value=severity_score,
            tags={'event_type': event_type}
        )
        self.metrics['security_severity_score'].append(severity_metric)
    
    def _record_anomaly_metric(self, metric_name: str, value: float, timestamp: datetime):
        """Record metric for anomaly detection."""
        window = self.anomaly_windows[metric_name]
        window.append((timestamp, value))
        
        # Calculate baseline if we have enough data
        if len(window) >= 50:
            values = [v for _, v in window]
            baseline = sum(values) / len(values)
            self.anomaly_baselines[metric_name] = baseline
            
            # Check for anomaly
            if abs(value - baseline) > baseline * 2:  # 200% deviation
                logger.warning(f"Anomaly detected in {metric_name}: {value} vs baseline {baseline}")
    
    def _get_top_threats(self, incidents: List[SecurityIncident]) -> List[Dict[str, Any]]:
        """Get top security threats from incidents."""
        threat_counts = defaultdict(int)
        threat_details = defaultdict(lambda: {'count': 0, 'severity': 'low', 'examples': []})
        
        for incident in incidents:
            key = f"{incident.category}_{incident.severity}"
            threat_counts[key] += 1
            
            detail = threat_details[incident.category]
            detail['count'] += 1
            if incident.severity == self.SEVERITY_CRITICAL or (
                detail['severity'] != self.SEVERITY_CRITICAL and 
                incident.severity == self.SEVERITY_HIGH
            ):
                detail['severity'] = incident.severity
            
            if len(detail['examples']) < 3:
                detail['examples'].append({
                    'description': incident.description,
                    'client_id': incident.client_id,
                    'template': incident.template_name
                })
        
        # Sort by count and return top 5
        sorted_threats = sorted(threat_details.items(), key=lambda x: x[1]['count'], reverse=True)
        return [{'category': cat, **details} for cat, details in sorted_threats[:5]]
    
    def _generate_recommendations(
        self, 
        incident_analysis: Dict[str, Any], 
        client_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate security recommendations."""
        recommendations = []
        
        # Check incident patterns
        if incident_analysis['by_category'].get(self.CATEGORY_XSS, 0) > 5:
            recommendations.append("Consider implementing stricter input validation for XSS prevention")
        
        if incident_analysis['by_category'].get(self.CATEGORY_INJECTION, 0) > 3:
            recommendations.append("Review template security and implement additional injection protection")
        
        if incident_analysis['by_category'].get(self.CATEGORY_PII, 0) > 2:
            recommendations.append("Enhance PII detection and implement automatic redaction")
        
        # Check client patterns
        high_risk_clients = [
            client_id for client_id, data in client_analysis.items()
            if data.get('risk_score', 0) > 70
        ]
        
        if len(high_risk_clients) > 5:
            recommendations.append("Consider implementing additional authentication for high-risk clients")
        
        # Check resolution rate
        if incident_analysis['resolution_rate'] < 0.8:
            recommendations.append("Improve incident response procedures to increase resolution rate")
        
        if not recommendations:
            recommendations.append("Current security posture appears stable - continue monitoring")
        
        return recommendations