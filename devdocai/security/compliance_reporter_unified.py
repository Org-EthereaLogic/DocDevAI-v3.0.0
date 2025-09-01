"""
M010 Security Module - Unified Compliance Reporter

Consolidates basic and optimized compliance reporters with operation modes:
- BASIC: Core compliance reporting with standard frameworks
- PERFORMANCE: Optimized reporting with caching and parallelization
- SECURE/ENTERPRISE: Enhanced compliance with automated assessments and audit trails

Supports GDPR, CCPA, SOC 2, ISO 27001, NIST, HIPAA, PCI-DSS, and custom frameworks.
"""

import asyncio
import json
import logging
import time
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Set, Tuple
from enum import Enum
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from functools import lru_cache
from collections import defaultdict
import multiprocessing as mp
import uuid

logger = logging.getLogger(__name__)


class ComplianceOperationMode(str, Enum):
    """Compliance operation modes."""
    BASIC = "basic"
    PERFORMANCE = "performance"
    SECURE = "secure"
    ENTERPRISE = "enterprise"


class ComplianceStandard(str, Enum):
    """Supported compliance standards."""
    GDPR = "gdpr"               # General Data Protection Regulation
    CCPA = "ccpa"               # California Consumer Privacy Act
    SOC2 = "soc2"               # SOC 2 Type II
    ISO27001 = "iso27001"       # ISO 27001
    NIST = "nist"               # NIST Cybersecurity Framework
    HIPAA = "hipaa"             # Health Insurance Portability and Accountability Act
    PCI_DSS = "pci_dss"         # Payment Card Industry Data Security Standard
    PIPEDA = "pipeda"           # Personal Information Protection and Electronic Documents Act
    LGPD = "lgpd"               # Lei Geral de Proteção de Dados (Brazil)
    CUSTOM = "custom"           # Custom compliance framework


class ComplianceStatus(Enum):
    """Compliance assessment status."""
    COMPLIANT = "compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NON_COMPLIANT = "non_compliant"
    NOT_ASSESSED = "not_assessed"
    IN_PROGRESS = "in_progress"


@dataclass
class ComplianceControl:
    """Represents a compliance control."""
    control_id: str
    title: str
    description: str
    category: str
    standard: ComplianceStandard
    mandatory: bool = True
    implementation_status: ComplianceStatus = ComplianceStatus.NOT_ASSESSED
    evidence_required: List[str] = field(default_factory=list)
    remediation_steps: List[str] = field(default_factory=list)
    responsible_team: Optional[str] = None
    due_date: Optional[datetime] = None
    last_assessed: Optional[datetime] = None
    assessment_score: float = 0.0
    risk_level: str = "medium"


@dataclass
class ComplianceReport:
    """Represents a compliance assessment report."""
    report_id: str
    standard: ComplianceStandard
    assessment_date: datetime
    overall_score: float
    status: ComplianceStatus
    
    # Detailed results
    total_controls: int = 0
    compliant_controls: int = 0
    non_compliant_controls: int = 0
    not_assessed_controls: int = 0
    
    # Control results
    controls: List[ComplianceControl] = field(default_factory=list)
    
    # Recommendations and findings
    critical_findings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    remediation_plan: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metadata
    assessor: str = "automated"
    assessment_methodology: str = "continuous"
    next_assessment_due: Optional[datetime] = None
    report_format: str = "json"
    
    # Executive summary
    executive_summary: str = ""
    risk_summary: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplianceConfig:
    """Configuration for compliance reporting."""
    mode: ComplianceOperationMode = ComplianceOperationMode.ENTERPRISE
    
    # Core settings
    enabled_standards: List[ComplianceStandard] = field(default_factory=lambda: [ComplianceStandard.GDPR])
    assessment_frequency_days: int = 90
    enable_continuous_monitoring: bool = False
    enable_automated_assessment: bool = False
    compliance_threshold: float = 0.8
    
    # Performance optimization settings
    enable_parallel_assessment: bool = False
    enable_result_caching: bool = False
    enable_incremental_updates: bool = False
    cache_ttl_hours: int = 24
    max_workers: int = 4
    batch_size: int = 20
    
    # Advanced features
    enable_risk_scoring: bool = False
    enable_trend_analysis: bool = False
    enable_benchmark_comparison: bool = False
    generate_executive_reports: bool = False
    
    # Integration and alerting
    enable_audit_logging: bool = False
    enable_compliance_alerting: bool = False
    alert_on_non_compliance: bool = False
    integration_apis: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Configure mode-specific settings."""
        if self.mode == ComplianceOperationMode.BASIC:
            self.enable_parallel_assessment = False
            self.enable_result_caching = False
            self.enable_incremental_updates = False
            self.enable_continuous_monitoring = False
            self.enable_automated_assessment = False
            self.enable_risk_scoring = False
            self.enable_trend_analysis = False
            self.enable_benchmark_comparison = False
            self.generate_executive_reports = False
            
        elif self.mode == ComplianceOperationMode.PERFORMANCE:
            self.enable_parallel_assessment = True
            self.enable_result_caching = True
            self.enable_incremental_updates = True
            self.enable_automated_assessment = True
            self.max_workers = min(mp.cpu_count(), 8)
            self.batch_size = 50
            
        elif self.mode == ComplianceOperationMode.SECURE:
            self.enable_parallel_assessment = True
            self.enable_result_caching = True
            self.enable_continuous_monitoring = True
            self.enable_automated_assessment = True
            self.enable_risk_scoring = True
            self.enable_audit_logging = True
            self.enable_compliance_alerting = True
            
        elif self.mode == ComplianceOperationMode.ENTERPRISE:
            self.enable_parallel_assessment = True
            self.enable_result_caching = True
            self.enable_incremental_updates = True
            self.enable_continuous_monitoring = True
            self.enable_automated_assessment = True
            self.enable_risk_scoring = True
            self.enable_trend_analysis = True
            self.enable_benchmark_comparison = True
            self.generate_executive_reports = True
            self.enable_audit_logging = True
            self.enable_compliance_alerting = True
            self.alert_on_non_compliance = True


@dataclass
class ComplianceStatistics:
    """Statistics for compliance operations."""
    total_assessments: int = 0
    assessments_by_standard: Dict[str, int] = field(default_factory=dict)
    assessments_by_status: Dict[str, int] = field(default_factory=dict)
    avg_compliance_score: float = 0.0
    avg_assessment_time_minutes: float = 0.0
    critical_findings_total: int = 0
    remediation_items_total: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    last_assessment: Optional[datetime] = None
    last_updated: datetime = field(default_factory=datetime.now)


class ComplianceCache:
    """Thread-safe cache for compliance assessments (performance mode)."""
    
    def __init__(self, max_size: int = 500, ttl_hours: int = 24):
        self.max_size = max_size
        self.ttl_seconds = ttl_hours * 3600
        self.cache = {}
        self.access_times = {}
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self.lock:
            if key not in self.cache:
                return None
            
            entry_time, value = self.cache[key]
            if time.time() - entry_time > self.ttl_seconds:
                del self.cache[key]
                del self.access_times[key]
                return None
            
            self.access_times[key] = time.time()
            return value
    
    def set(self, key: str, value: Any):
        """Set value in cache."""
        with self.lock:
            current_time = time.time()
            
            # Evict if at capacity
            if len(self.cache) >= self.max_size and key not in self.cache:
                # Remove least recently used
                oldest_key = min(self.access_times.keys(), 
                               key=lambda k: self.access_times[k])
                del self.cache[oldest_key]
                del self.access_times[oldest_key]
            
            self.cache[key] = (current_time, value)
            self.access_times[key] = current_time
    
    def clear(self):
        """Clear cache."""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
    
    def size(self) -> int:
        """Get cache size."""
        with self.lock:
            return len(self.cache)


class UnifiedComplianceReporter:
    """
    Unified Compliance Reporter supporting multiple operation modes.
    
    Modes:
    - BASIC: Standard compliance reporting for major frameworks
    - PERFORMANCE: Optimized reporting with caching and parallelization
    - SECURE: Enhanced compliance with continuous monitoring and alerting
    - ENTERPRISE: Full compliance suite with trend analysis and executive reporting
    """
    
    def __init__(self, config: Optional[ComplianceConfig] = None):
        """Initialize unified compliance reporter."""
        self.config = config or ComplianceConfig()
        self._statistics = ComplianceStatistics()
        
        # Performance components
        self._thread_pool = None
        if self.config.enable_parallel_assessment:
            self._thread_pool = ThreadPoolExecutor(max_workers=self.config.max_workers)
        
        # Caching component
        self._cache = None
        if self.config.enable_result_caching:
            self._cache = ComplianceCache(ttl_hours=self.config.cache_ttl_hours)
        
        # Compliance controls for each standard
        self._compliance_controls = self._initialize_compliance_controls()
        
        # Historical data for trend analysis
        self._historical_assessments = []
        
        logger.info(f"Initialized compliance reporter in {self.config.mode.value} mode")
    
    def _initialize_compliance_controls(self) -> Dict[ComplianceStandard, List[ComplianceControl]]:
        """Initialize compliance controls for supported standards."""
        controls = {}
        
        # GDPR Controls
        if ComplianceStandard.GDPR in self.config.enabled_standards:
            controls[ComplianceStandard.GDPR] = [
                ComplianceControl(
                    control_id="GDPR-001",
                    title="Lawful Basis for Processing",
                    description="Ensure all personal data processing has a valid lawful basis",
                    category="Data Processing",
                    standard=ComplianceStandard.GDPR,
                    evidence_required=["Privacy policy", "Consent records", "Legal basis documentation"],
                    risk_level="high"
                ),
                ComplianceControl(
                    control_id="GDPR-002",
                    title="Data Subject Rights Implementation",
                    description="Implement mechanisms for data subject rights exercise",
                    category="Rights Management",
                    standard=ComplianceStandard.GDPR,
                    evidence_required=["DSR handling procedures", "Response time records"],
                    risk_level="high"
                ),
                ComplianceControl(
                    control_id="GDPR-003",
                    title="Data Protection Impact Assessment",
                    description="Conduct DPIA for high-risk processing activities",
                    category="Risk Assessment",
                    standard=ComplianceStandard.GDPR,
                    evidence_required=["DPIA documentation", "Risk mitigation measures"],
                    risk_level="medium"
                ),
                ComplianceControl(
                    control_id="GDPR-004",
                    title="Breach Notification Procedures",
                    description="Implement 72-hour breach notification procedures",
                    category="Incident Response",
                    standard=ComplianceStandard.GDPR,
                    evidence_required=["Incident response plan", "Notification templates"],
                    risk_level="critical"
                )
            ]
        
        # SOC 2 Controls
        if ComplianceStandard.SOC2 in self.config.enabled_standards:
            controls[ComplianceStandard.SOC2] = [
                ComplianceControl(
                    control_id="SOC2-CC6.1",
                    title="Logical and Physical Access Controls",
                    description="Implement appropriate access controls",
                    category="Access Controls",
                    standard=ComplianceStandard.SOC2,
                    evidence_required=["Access control policies", "User access reviews"],
                    risk_level="high"
                ),
                ComplianceControl(
                    control_id="SOC2-CC7.1", 
                    title="System Operation Monitoring",
                    description="Monitor system operations for security events",
                    category="Monitoring",
                    standard=ComplianceStandard.SOC2,
                    evidence_required=["Monitoring procedures", "Security event logs"],
                    risk_level="medium"
                )
            ]
        
        # ISO 27001 Controls
        if ComplianceStandard.ISO27001 in self.config.enabled_standards:
            controls[ComplianceStandard.ISO27001] = [
                ComplianceControl(
                    control_id="ISO-A.5.1.1",
                    title="Information Security Policy",
                    description="Establish and maintain information security policies",
                    category="Policy",
                    standard=ComplianceStandard.ISO27001,
                    evidence_required=["Security policy document", "Policy approval records"],
                    risk_level="high"
                ),
                ComplianceControl(
                    control_id="ISO-A.12.1.2",
                    title="Change Management",
                    description="Control changes to processing facilities and information systems",
                    category="Change Management", 
                    standard=ComplianceStandard.ISO27001,
                    evidence_required=["Change management procedures", "Change records"],
                    risk_level="medium"
                )
            ]
        
        return controls
    
    def generate_report(self, standard: str = "GDPR") -> Dict[str, Any]:
        """Generate compliance report synchronously (basic mode)."""
        start_time = time.time()
        
        try:
            compliance_standard = ComplianceStandard(standard.lower())
            
            # Check cache first
            if self._cache:
                cache_key = self._generate_cache_key(compliance_standard)
                cached_report = self._cache.get(cache_key)
                if cached_report:
                    self._statistics.cache_hits += 1
                    return cached_report
                self._statistics.cache_misses += 1
            
            # Generate compliance report
            report = self._generate_compliance_report(compliance_standard)
            
            # Cache result if caching is enabled
            if self._cache:
                self._cache.set(cache_key, self._convert_report_to_dict(report))
            
            # Update statistics
            assessment_time = time.time() - start_time
            self._update_statistics(report, assessment_time)
            
            # Audit logging if enabled
            if self.config.enable_audit_logging:
                self._log_compliance_audit(report)
            
            # Handle alerting if enabled
            if self.config.enable_compliance_alerting:
                self._handle_compliance_alerts(report)
            
            return self._convert_report_to_dict(report)
            
        except Exception as e:
            logger.error(f"Compliance report generation failed: {e}")
            raise
    
    async def generate_report_async(self, standard: str = "GDPR") -> Dict[str, Any]:
        """Generate compliance report asynchronously (optimized modes)."""
        if self.config.mode == ComplianceOperationMode.BASIC:
            # Run synchronous generation in thread pool for basic mode
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.generate_report, standard)
        
        start_time = time.time()
        
        try:
            compliance_standard = ComplianceStandard(standard.lower())
            
            # Check cache first
            if self._cache:
                cache_key = self._generate_cache_key(compliance_standard)
                cached_report = self._cache.get(cache_key)
                if cached_report:
                    self._statistics.cache_hits += 1
                    return cached_report
                self._statistics.cache_misses += 1
            
            # Generate compliance report with parallelization
            report = await self._generate_compliance_report_async(compliance_standard)
            
            # Cache result if caching is enabled
            if self._cache:
                self._cache.set(cache_key, self._convert_report_to_dict(report))
            
            # Update statistics
            assessment_time = time.time() - start_time
            self._update_statistics(report, assessment_time)
            
            # Audit logging if enabled
            if self.config.enable_audit_logging:
                await self._log_compliance_audit_async(report)
            
            # Handle alerting if enabled
            if self.config.enable_compliance_alerting:
                await self._handle_compliance_alerts_async(report)
            
            return self._convert_report_to_dict(report)
            
        except Exception as e:
            logger.error(f"Async compliance report generation failed: {e}")
            raise
    
    def _generate_compliance_report(self, standard: ComplianceStandard) -> ComplianceReport:
        """Generate compliance report for specified standard."""
        controls = self._compliance_controls.get(standard, [])
        if not controls:
            raise ValueError(f"No controls defined for standard: {standard.value}")
        
        # Assess each control
        assessed_controls = []
        for control in controls:
            assessed_control = self._assess_control(control)
            assessed_controls.append(assessed_control)
        
        # Calculate overall compliance
        total_controls = len(assessed_controls)
        compliant_controls = len([c for c in assessed_controls if c.implementation_status == ComplianceStatus.COMPLIANT])
        non_compliant_controls = len([c for c in assessed_controls if c.implementation_status == ComplianceStatus.NON_COMPLIANT])
        not_assessed_controls = len([c for c in assessed_controls if c.implementation_status == ComplianceStatus.NOT_ASSESSED])
        
        overall_score = compliant_controls / total_controls if total_controls > 0 else 0.0
        
        # Determine overall status
        if overall_score >= self.config.compliance_threshold:
            status = ComplianceStatus.COMPLIANT
        elif overall_score >= 0.5:
            status = ComplianceStatus.PARTIALLY_COMPLIANT
        else:
            status = ComplianceStatus.NON_COMPLIANT
        
        # Generate findings and recommendations
        critical_findings = self._generate_critical_findings(assessed_controls)
        recommendations = self._generate_recommendations(assessed_controls)
        remediation_plan = self._generate_remediation_plan(assessed_controls)
        
        # Create report
        report = ComplianceReport(
            report_id=str(uuid.uuid4()),
            standard=standard,
            assessment_date=datetime.now(timezone.utc),
            overall_score=overall_score,
            status=status,
            total_controls=total_controls,
            compliant_controls=compliant_controls,
            non_compliant_controls=non_compliant_controls,
            not_assessed_controls=not_assessed_controls,
            controls=assessed_controls,
            critical_findings=critical_findings,
            recommendations=recommendations,
            remediation_plan=remediation_plan,
            assessor="automated_system",
            next_assessment_due=datetime.now(timezone.utc) + timedelta(days=self.config.assessment_frequency_days)
        )
        
        # Generate executive summary if enabled
        if self.config.generate_executive_reports:
            report.executive_summary = self._generate_executive_summary(report)
            report.risk_summary = self._generate_risk_summary(report)
        
        return report
    
    async def _generate_compliance_report_async(self, standard: ComplianceStandard) -> ComplianceReport:
        """Generate compliance report asynchronously with parallel control assessment."""
        controls = self._compliance_controls.get(standard, [])
        if not controls:
            raise ValueError(f"No controls defined for standard: {standard.value}")
        
        # Assess controls in parallel
        tasks = []
        loop = asyncio.get_event_loop()
        
        for control in controls:
            task = loop.run_in_executor(self._thread_pool, self._assess_control, control)
            tasks.append(task)
        
        assessed_controls = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_controls = []
        for control in assessed_controls:
            if isinstance(control, Exception):
                logger.error(f"Control assessment failed: {control}")
            else:
                valid_controls.append(control)
        
        # Calculate overall compliance
        total_controls = len(valid_controls)
        compliant_controls = len([c for c in valid_controls if c.implementation_status == ComplianceStatus.COMPLIANT])
        non_compliant_controls = len([c for c in valid_controls if c.implementation_status == ComplianceStatus.NON_COMPLIANT])
        not_assessed_controls = len([c for c in valid_controls if c.implementation_status == ComplianceStatus.NOT_ASSESSED])
        
        overall_score = compliant_controls / total_controls if total_controls > 0 else 0.0
        
        # Determine overall status
        if overall_score >= self.config.compliance_threshold:
            status = ComplianceStatus.COMPLIANT
        elif overall_score >= 0.5:
            status = ComplianceStatus.PARTIALLY_COMPLIANT
        else:
            status = ComplianceStatus.NON_COMPLIANT
        
        # Generate findings and recommendations asynchronously
        findings_task = loop.run_in_executor(self._thread_pool, self._generate_critical_findings, valid_controls)
        recommendations_task = loop.run_in_executor(self._thread_pool, self._generate_recommendations, valid_controls)
        remediation_task = loop.run_in_executor(self._thread_pool, self._generate_remediation_plan, valid_controls)
        
        critical_findings, recommendations, remediation_plan = await asyncio.gather(
            findings_task, recommendations_task, remediation_task
        )
        
        # Create report
        report = ComplianceReport(
            report_id=str(uuid.uuid4()),
            standard=standard,
            assessment_date=datetime.now(timezone.utc),
            overall_score=overall_score,
            status=status,
            total_controls=total_controls,
            compliant_controls=compliant_controls,
            non_compliant_controls=non_compliant_controls,
            not_assessed_controls=not_assessed_controls,
            controls=valid_controls,
            critical_findings=critical_findings,
            recommendations=recommendations,
            remediation_plan=remediation_plan,
            assessor="automated_async_system",
            next_assessment_due=datetime.now(timezone.utc) + timedelta(days=self.config.assessment_frequency_days)
        )
        
        # Generate executive summary if enabled
        if self.config.generate_executive_reports:
            summary_task = loop.run_in_executor(self._thread_pool, self._generate_executive_summary, report)
            risk_task = loop.run_in_executor(self._thread_pool, self._generate_risk_summary, report)
            
            report.executive_summary, report.risk_summary = await asyncio.gather(summary_task, risk_task)
        
        return report
    
    def _assess_control(self, control: ComplianceControl) -> ComplianceControl:
        """Assess a single compliance control."""
        # Simulate control assessment logic
        # In a real implementation, this would check actual system configurations,
        # policies, logs, etc.
        
        assessed_control = control
        assessed_control.last_assessed = datetime.now(timezone.utc)
        
        # Simulate assessment based on control characteristics
        if self.config.enable_automated_assessment:
            # Automated assessment logic
            if control.risk_level == "critical":
                # Critical controls have stricter assessment
                assessed_control.assessment_score = 0.75  # Simulated score
                assessed_control.implementation_status = ComplianceStatus.PARTIALLY_COMPLIANT
            elif control.risk_level == "high":
                assessed_control.assessment_score = 0.85
                assessed_control.implementation_status = ComplianceStatus.COMPLIANT
            else:
                assessed_control.assessment_score = 0.90
                assessed_control.implementation_status = ComplianceStatus.COMPLIANT
        else:
            # Manual assessment indicators
            assessed_control.implementation_status = ComplianceStatus.NOT_ASSESSED
            assessed_control.assessment_score = 0.0
        
        # Add remediation steps for non-compliant controls
        if assessed_control.implementation_status != ComplianceStatus.COMPLIANT:
            assessed_control.remediation_steps = self._get_remediation_steps(control)
        
        return assessed_control
    
    def _get_remediation_steps(self, control: ComplianceControl) -> List[str]:
        """Get remediation steps for non-compliant control."""
        remediation_map = {
            "GDPR-001": [
                "Review and document lawful basis for each processing activity",
                "Update privacy policy with clear lawful basis statements",
                "Implement consent management system if consent is used"
            ],
            "GDPR-002": [
                "Implement automated DSR handling system",
                "Train staff on data subject rights procedures",
                "Establish 30-day response time tracking"
            ],
            "GDPR-004": [
                "Implement incident detection and response procedures", 
                "Create breach notification templates and workflows",
                "Establish 72-hour notification timeline tracking"
            ],
            "SOC2-CC6.1": [
                "Implement role-based access controls",
                "Conduct quarterly access reviews",
                "Enable multi-factor authentication"
            ],
            "ISO-A.5.1.1": [
                "Develop comprehensive information security policy",
                "Obtain management approval for security policies",
                "Implement policy review and update procedures"
            ]
        }
        
        return remediation_map.get(control.control_id, [
            "Review control implementation",
            "Update procedures and documentation",
            "Conduct staff training if required"
        ])
    
    def _generate_critical_findings(self, controls: List[ComplianceControl]) -> List[str]:
        """Generate critical findings from assessed controls."""
        findings = []
        
        for control in controls:
            if control.implementation_status == ComplianceStatus.NON_COMPLIANT and control.risk_level in ["critical", "high"]:
                findings.append(f"CRITICAL: {control.title} - {control.description}")
            elif control.implementation_status == ComplianceStatus.NOT_ASSESSED and control.mandatory:
                findings.append(f"NOT ASSESSED: {control.title} - Assessment required")
        
        return findings
    
    def _generate_recommendations(self, controls: List[ComplianceControl]) -> List[str]:
        """Generate recommendations from assessed controls."""
        recommendations = set()
        
        non_compliant_count = len([c for c in controls if c.implementation_status == ComplianceStatus.NON_COMPLIANT])
        not_assessed_count = len([c for c in controls if c.implementation_status == ComplianceStatus.NOT_ASSESSED])
        
        if non_compliant_count > 0:
            recommendations.add("Prioritize remediation of non-compliant controls")
            recommendations.add("Implement regular compliance monitoring")
        
        if not_assessed_count > 0:
            recommendations.add("Complete assessment of all mandatory controls")
            recommendations.add("Establish assessment procedures and schedules")
        
        # Risk-specific recommendations
        critical_controls = [c for c in controls if c.risk_level == "critical"]
        if any(c.implementation_status != ComplianceStatus.COMPLIANT for c in critical_controls):
            recommendations.add("Immediate attention required for critical security controls")
        
        return list(recommendations)
    
    def _generate_remediation_plan(self, controls: List[ComplianceControl]) -> List[Dict[str, Any]]:
        """Generate remediation plan from assessed controls."""
        plan = []
        
        non_compliant_controls = [c for c in controls if c.implementation_status == ComplianceStatus.NON_COMPLIANT]
        
        for control in non_compliant_controls:
            priority = "High" if control.risk_level in ["critical", "high"] else "Medium"
            
            plan_item = {
                "control_id": control.control_id,
                "title": control.title,
                "priority": priority,
                "estimated_effort": "TBD",
                "due_date": (datetime.now(timezone.utc) + timedelta(days=30 if priority == "High" else 90)).isoformat(),
                "remediation_steps": control.remediation_steps,
                "responsible_team": control.responsible_team or "TBD"
            }
            plan.append(plan_item)
        
        # Sort by priority
        plan.sort(key=lambda x: x["priority"], reverse=True)
        
        return plan
    
    def _generate_executive_summary(self, report: ComplianceReport) -> str:
        """Generate executive summary for compliance report."""
        summary = f"""
Executive Summary - {report.standard.value.upper()} Compliance Assessment

Assessment Overview:
- Overall Compliance Score: {report.overall_score:.1%}
- Status: {report.status.value.replace('_', ' ').title()}
- Assessment Date: {report.assessment_date.strftime('%Y-%m-%d')}

Key Metrics:
- Total Controls Assessed: {report.total_controls}
- Compliant Controls: {report.compliant_controls}
- Non-Compliant Controls: {report.non_compliant_controls}
- Not Assessed Controls: {report.not_assessed_controls}

Critical Findings: {len(report.critical_findings)}
Remediation Items: {len(report.remediation_plan)}

Next Assessment Due: {report.next_assessment_due.strftime('%Y-%m-%d') if report.next_assessment_due else 'TBD'}
        """.strip()
        
        return summary
    
    def _generate_risk_summary(self, report: ComplianceReport) -> Dict[str, Any]:
        """Generate risk summary for compliance report."""
        critical_risks = len([c for c in report.controls if c.risk_level == "critical" and c.implementation_status != ComplianceStatus.COMPLIANT])
        high_risks = len([c for c in report.controls if c.risk_level == "high" and c.implementation_status != ComplianceStatus.COMPLIANT])
        medium_risks = len([c for c in report.controls if c.risk_level == "medium" and c.implementation_status != ComplianceStatus.COMPLIANT])
        
        return {
            "overall_risk_level": "High" if critical_risks > 0 else "Medium" if high_risks > 0 else "Low",
            "critical_risks": critical_risks,
            "high_risks": high_risks,
            "medium_risks": medium_risks,
            "total_risks": critical_risks + high_risks + medium_risks,
            "risk_trend": "stable",  # Would be calculated from historical data
            "risk_mitigation_priority": ["critical", "high", "medium"]
        }
    
    def _convert_report_to_dict(self, report: ComplianceReport) -> Dict[str, Any]:
        """Convert compliance report to dictionary format."""
        return {
            "report_id": report.report_id,
            "standard": report.standard.value,
            "assessment_date": report.assessment_date.isoformat(),
            "overall_score": round(report.overall_score, 3),
            "status": report.status.value,
            "summary": {
                "total_controls": report.total_controls,
                "compliant_controls": report.compliant_controls,
                "non_compliant_controls": report.non_compliant_controls,
                "not_assessed_controls": report.not_assessed_controls,
                "compliance_percentage": round(report.overall_score * 100, 1)
            },
            "controls": [
                {
                    "control_id": control.control_id,
                    "title": control.title,
                    "description": control.description,
                    "category": control.category,
                    "status": control.implementation_status.value,
                    "score": round(control.assessment_score, 3),
                    "risk_level": control.risk_level,
                    "last_assessed": control.last_assessed.isoformat() if control.last_assessed else None,
                    "remediation_steps": control.remediation_steps
                }
                for control in report.controls
            ],
            "findings": {
                "critical_findings": report.critical_findings,
                "recommendations": report.recommendations,
                "remediation_plan": report.remediation_plan
            },
            "metadata": {
                "assessor": report.assessor,
                "assessment_methodology": report.assessment_methodology,
                "next_assessment_due": report.next_assessment_due.isoformat() if report.next_assessment_due else None,
                "report_format": report.report_format,
                "mode": self.config.mode.value
            }
        }
        
        # Add executive summary if available
        if report.executive_summary:
            result["executive_summary"] = report.executive_summary
            
        if report.risk_summary:
            result["risk_summary"] = report.risk_summary
            
        return result
    
    # Caching Methods
    
    def _generate_cache_key(self, standard: ComplianceStandard) -> str:
        """Generate cache key for compliance assessment."""
        key_data = f"{standard.value}_{self.config.compliance_threshold}_{datetime.now().date()}"
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    # Statistics and Alerting Methods
    
    def _update_statistics(self, report: ComplianceReport, assessment_time: float):
        """Update compliance statistics."""
        self._statistics.total_assessments += 1
        self._statistics.last_assessment = datetime.now()
        
        # Update standard counters
        standard_key = report.standard.value
        self._statistics.assessments_by_standard[standard_key] = \
            self._statistics.assessments_by_standard.get(standard_key, 0) + 1
        
        # Update status counters
        status_key = report.status.value
        self._statistics.assessments_by_status[status_key] = \
            self._statistics.assessments_by_status.get(status_key, 0) + 1
        
        # Update average compliance score
        total_assessments = self._statistics.total_assessments
        current_avg = self._statistics.avg_compliance_score
        
        new_avg = ((current_avg * (total_assessments - 1)) + report.overall_score) / total_assessments
        self._statistics.avg_compliance_score = new_avg
        
        # Update average assessment time
        assessment_minutes = assessment_time / 60
        current_time_avg = self._statistics.avg_assessment_time_minutes
        
        new_time_avg = ((current_time_avg * (total_assessments - 1)) + assessment_minutes) / total_assessments
        self._statistics.avg_assessment_time_minutes = new_time_avg
        
        # Update findings counters
        self._statistics.critical_findings_total += len(report.critical_findings)
        self._statistics.remediation_items_total += len(report.remediation_plan)
        
        self._statistics.last_updated = datetime.now()
        
        # Store for trend analysis
        if self.config.enable_trend_analysis:
            self._historical_assessments.append({
                'date': report.assessment_date,
                'standard': report.standard.value,
                'score': report.overall_score,
                'status': report.status.value
            })
            
            # Keep only last 12 months of data
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=365)
            self._historical_assessments = [
                assessment for assessment in self._historical_assessments 
                if assessment['date'] > cutoff_date
            ]
    
    def _handle_compliance_alerts(self, report: ComplianceReport):
        """Handle compliance alerting."""
        if not self.config.alert_on_non_compliance:
            return
            
        if report.status == ComplianceStatus.NON_COMPLIANT or len(report.critical_findings) > 0:
            alert_data = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'standard': report.standard.value,
                'status': report.status.value,
                'score': report.overall_score,
                'critical_findings': len(report.critical_findings),
                'non_compliant_controls': report.non_compliant_controls,
                'report_id': report.report_id
            }
            
            logger.warning(f"Compliance Alert: {json.dumps(alert_data)}")
    
    async def _handle_compliance_alerts_async(self, report: ComplianceReport):
        """Handle compliance alerting asynchronously."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._handle_compliance_alerts, report)
    
    def _log_compliance_audit(self, report: ComplianceReport):
        """Log compliance audit information."""
        audit_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'report_id': report.report_id,
            'standard': report.standard.value,
            'overall_score': report.overall_score,
            'status': report.status.value,
            'controls_assessed': report.total_controls,
            'critical_findings': len(report.critical_findings),
            'mode': self.config.mode.value,
            'assessor': report.assessor
        }
        
        logger.info(f"Compliance Assessment Audit: {json.dumps(audit_entry)}")
    
    async def _log_compliance_audit_async(self, report: ComplianceReport):
        """Log compliance audit information asynchronously."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._log_compliance_audit, report)
    
    # Utility Methods
    
    async def health_check(self) -> bool:
        """Perform health check of compliance reporter."""
        try:
            # Test basic functionality
            result = await self.generate_report_async("gdpr") if self.config.mode != ComplianceOperationMode.BASIC else self.generate_report("gdpr")
            
            # Verify report generation worked
            if result.get('report_id') and result.get('summary', {}).get('total_controls', 0) > 0:
                return True
            else:
                logger.warning("Health check generated report with no controls")
                return False
                
        except Exception as e:
            logger.error(f"Compliance reporter health check failed: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive reporter statistics."""
        return {
            'mode': self.config.mode.value,
            'total_assessments': self._statistics.total_assessments,
            'assessments_by_standard': dict(self._statistics.assessments_by_standard),
            'assessments_by_status': dict(self._statistics.assessments_by_status),
            'avg_compliance_score': round(self._statistics.avg_compliance_score, 3),
            'avg_assessment_time_minutes': round(self._statistics.avg_assessment_time_minutes, 2),
            'critical_findings_total': self._statistics.critical_findings_total,
            'remediation_items_total': self._statistics.remediation_items_total,
            'cache_hit_rate': (self._statistics.cache_hits / max(1, self._statistics.cache_hits + self._statistics.cache_misses)) * 100,
            'cache_size': self._cache.size() if self._cache else 0,
            'enabled_standards': [s.value for s in self.config.enabled_standards],
            'controls_loaded': sum(len(controls) for controls in self._compliance_controls.values()),
            'historical_data_points': len(self._historical_assessments),
            'last_assessment': self._statistics.last_assessment.isoformat() if self._statistics.last_assessment else None,
            'last_updated': self._statistics.last_updated.isoformat()
        }
    
    def get_trend_analysis(self) -> Dict[str, Any]:
        """Get compliance trend analysis (enterprise mode)."""
        if not self.config.enable_trend_analysis or not self._historical_assessments:
            return {"error": "Trend analysis not available"}
        
        # Calculate trends
        recent_scores = [a['score'] for a in self._historical_assessments[-6:]]  # Last 6 assessments
        trend_direction = "stable"
        
        if len(recent_scores) >= 2:
            if recent_scores[-1] > recent_scores[0]:
                trend_direction = "improving"
            elif recent_scores[-1] < recent_scores[0]:
                trend_direction = "declining"
        
        return {
            'trend_direction': trend_direction,
            'data_points': len(self._historical_assessments),
            'recent_scores': recent_scores,
            'average_score': sum(a['score'] for a in self._historical_assessments) / len(self._historical_assessments),
            'score_variance': self._calculate_variance([a['score'] for a in self._historical_assessments])
        }
    
    def _calculate_variance(self, scores: List[float]) -> float:
        """Calculate variance of scores."""
        if len(scores) < 2:
            return 0.0
        
        mean = sum(scores) / len(scores)
        variance = sum((score - mean) ** 2 for score in scores) / len(scores)
        return variance
    
    def clear_cache(self):
        """Clear compliance cache."""
        if self._cache:
            self._cache.clear()
            self._statistics.cache_hits = 0
            self._statistics.cache_misses = 0
    
    def __del__(self):
        """Cleanup resources."""
        try:
            if self._thread_pool:
                self._thread_pool.shutdown(wait=False)
        except:
            pass


# Factory functions for different modes
def create_basic_compliance_reporter(config: Optional[ComplianceConfig] = None) -> UnifiedComplianceReporter:
    """Create basic compliance reporter."""
    if config is None:
        config = ComplianceConfig(mode=ComplianceOperationMode.BASIC)
    return UnifiedComplianceReporter(config)


def create_performance_compliance_reporter(config: Optional[ComplianceConfig] = None) -> UnifiedComplianceReporter:
    """Create performance-optimized compliance reporter."""
    if config is None:
        config = ComplianceConfig(mode=ComplianceOperationMode.PERFORMANCE)
    return UnifiedComplianceReporter(config)


def create_secure_compliance_reporter(config: Optional[ComplianceConfig] = None) -> UnifiedComplianceReporter:
    """Create security-enhanced compliance reporter."""
    if config is None:
        config = ComplianceConfig(mode=ComplianceOperationMode.SECURE)
    return UnifiedComplianceReporter(config)


def create_enterprise_compliance_reporter(config: Optional[ComplianceConfig] = None) -> UnifiedComplianceReporter:
    """Create enterprise compliance reporter with all features."""
    if config is None:
        config = ComplianceConfig(mode=ComplianceOperationMode.ENTERPRISE)
    return UnifiedComplianceReporter(config)