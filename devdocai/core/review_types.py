"""
M007 Review Engine Types
DevDocAI v3.0.0

Type definitions for the Review Engine module.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
from datetime import datetime


class ReviewType(Enum):
    """Types of document reviews available."""
    REQUIREMENTS = "requirements"
    DESIGN = "design"
    SECURITY = "security"
    PERFORMANCE = "performance"
    USABILITY = "usability"
    TEST_COVERAGE = "test_coverage"
    COMPLIANCE = "compliance"
    CONSISTENCY = "consistency"


class SeverityLevel(Enum):
    """Severity levels for issues found during review."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ComplianceStandard(Enum):
    """Compliance standards for checking."""
    GDPR = "gdpr"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    SOC2 = "soc2"
    ISO27001 = "iso27001"
    OWASP = "owasp"


class PIIType(Enum):
    """Types of PII that can be detected."""
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    ADDRESS = "address"
    NAME = "name"
    DATE_OF_BIRTH = "dob"
    PASSPORT = "passport"
    DRIVER_LICENSE = "driver_license"
    CUSTOM = "custom"


class SecurityVulnerability(Enum):
    """Types of security vulnerabilities."""
    EXPOSED_CREDENTIAL = "exposed_credential"
    WEAK_PASSWORD = "weak_password"
    HARDCODED_SECRET = "hardcoded_secret"
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    INSECURE_PROTOCOL = "insecure_protocol"
    MISSING_ENCRYPTION = "missing_encryption"
    OWASP_A01 = "A01_broken_access_control"
    OWASP_A02 = "A02_cryptographic_failures"
    OWASP_A03 = "A03_injection"
    OWASP_A04 = "A04_insecure_design"
    OWASP_A05 = "A05_security_misconfiguration"
    OWASP_A06 = "A06_vulnerable_components"
    OWASP_A07 = "A07_identification_failures"
    OWASP_A08 = "A08_data_integrity_failures"
    OWASP_A09 = "A09_logging_failures"
    OWASP_A10 = "A10_server_side_request_forgery"


@dataclass
class ReviewConfig:
    """Configuration for document review."""
    review_types: List[ReviewType] = field(default_factory=lambda: list(ReviewType))
    quality_threshold: float = 0.85
    pii_detection_enabled: bool = True
    security_scanning_enabled: bool = True
    use_llm_enhancement: bool = False
    save_results: bool = False
    cache_results: bool = True
    max_issues_per_type: int = 100
    timeout_seconds: int = 30


@dataclass
class PIIPattern:
    """Pattern definition for PII detection."""
    pii_type: PIIType
    pattern: str
    description: str
    confidence: float = 1.0


@dataclass
class PIIMatch:
    """A matched PII item in document."""
    pii_type: PIIType
    value: str
    # Use string location for flexibility (e.g., "Position 10-20" or "Line 12")
    location: str
    confidence: float
    # Line number is optional; not all detections track it
    line_number: int = 0
    context: str = ""


@dataclass
class SecurityIssue:
    """Security issue found during review."""
    vulnerability_type: SecurityVulnerability
    severity: SeverityLevel
    description: str
    location: str
    cvss_score: float = 0.0
    remediation: str = ""
    owasp_category: Optional[str] = None


@dataclass
class RequirementIssue:
    """Issue found in requirements review."""
    issue_type: str  # "ambiguous", "incomplete", "conflicting", etc.
    description: str
    location: str
    suggestion: str
    rfc2119_violation: bool = False


@dataclass
class PerformanceMetric:
    """Performance metric found in document."""
    metric_name: str
    value: Any
    unit: str
    threshold: Optional[float] = None
    meets_threshold: Optional[bool] = None


@dataclass
class QualityMetrics:
    """Quality metrics for document analysis."""
    efficiency_score: float = 0.0
    completeness_score: float = 0.0
    readability_score: float = 0.0
    overall_score: float = 0.0
    
    # Weights for quality formula
    efficiency_weight: float = 0.35
    completeness_weight: float = 0.35
    readability_weight: float = 0.30
    
    def calculate_overall(self) -> float:
        """Calculate overall score using formula Q = 0.35×E + 0.35×C + 0.30×R."""
        self.overall_score = (
            self.efficiency_weight * self.efficiency_score +
            self.completeness_weight * self.completeness_score +
            self.readability_weight * self.readability_score
        )
        return self.overall_score


@dataclass
class ReviewResult:
    """Result from a specific reviewer."""
    review_type: ReviewType
    score: float
    issues: List[Any] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
