"""
Suite Manager Type Definitions and Data Classes
DevDocAI v3.0.0

Extracted from suite.py for improved modularity and separation of concerns.
"""

import re
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# Security constants
MAX_SUITE_SIZE = 1000
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10MB
MAX_CROSS_REFS = 10000
MAX_ID_LENGTH = 256
MIN_ID_LENGTH = 3

# ============================================================================
# ENUMS
# ============================================================================

class ImpactSeverity(Enum):
    """Impact severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ChangeType(Enum):
    """Document change types."""
    CREATION = "creation"
    UPDATE = "update"
    MODIFICATION = "modification"
    DELETION = "deletion"
    REFACTORING = "refactoring"
    BREAKING_CHANGE = "breaking_change"


# ============================================================================
# EXCEPTIONS
# ============================================================================

class SuiteError(Exception):
    """Base suite exception with error type."""
    def __init__(self, message: str, error_type: str = "general"):
        super().__init__(message)
        self.error_type = error_type


# Specialized exceptions using the base class
class ConsistencyError(SuiteError):
    def __init__(self, message: str):
        super().__init__(message, "consistency")


class ImpactAnalysisError(SuiteError):
    def __init__(self, message: str):
        super().__init__(message, "impact")


class ValidationError(SuiteError):
    def __init__(self, message: str):
        super().__init__(message, "validation")


class SecurityError(SuiteError):
    def __init__(self, message: str):
        super().__init__(message, "security")


class RateLimitError(SuiteError):
    def __init__(self, message: str):
        super().__init__(message, "rate_limit")


class ResourceLimitError(SuiteError):
    def __init__(self, message: str):
        super().__init__(message, "resource_limit")


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class SuiteConfig:
    """Suite generation configuration."""
    suite_id: str
    documents: List[Dict[str, Any]]
    cross_references: Optional[Dict[str, List[str]]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate configuration."""
        if not self._is_valid_id(self.suite_id):
            raise ValidationError(f"Invalid suite_id: {self.suite_id}")
        
        if len(self.documents) > MAX_SUITE_SIZE:
            raise ResourceLimitError(f"Suite size {len(self.documents)} exceeds maximum {MAX_SUITE_SIZE}")
        
        for doc in self.documents:
            if "id" in doc and not self._is_valid_id(doc["id"]):
                raise ValidationError(f"Invalid document id: {doc['id']}")
            
            if "content" in doc:
                content_size = len(str(doc["content"]).encode('utf-8'))
                if content_size > MAX_DOCUMENT_SIZE:
                    raise ResourceLimitError(f"Document size exceeds maximum")
        
        if self.cross_references:
            total_refs = sum(len(refs) for refs in self.cross_references.values())
            if total_refs > MAX_CROSS_REFS:
                raise ResourceLimitError(f"Cross-references exceed maximum")
    
    def _is_valid_id(self, id_str: str) -> bool:
        """Validate ID string."""
        if not id_str or len(id_str) < MIN_ID_LENGTH or len(id_str) > MAX_ID_LENGTH:
            return False
        
        if not re.match(r'^[a-zA-Z0-9_\-\.]+$', id_str):
            return False
        
        dangerous_patterns = [r'\.\.', r'<.*?>', r'[;&|`$]', r'[\x00-\x1f]']
        for pattern in dangerous_patterns:
            if re.search(pattern, id_str, re.IGNORECASE):
                return False
        
        return True


@dataclass
class DocumentSuite:
    """Collection of related documents."""
    suite_id: str
    documents: List[Any]  # List[Document]
    cross_references: Dict[str, List[str]]
    metadata: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def document_count(self) -> int:
        return len(self.documents)


@dataclass
class SuiteResult:
    """Suite generation result."""
    success: bool
    suite_id: str
    documents: List[Any]  # List[Document]
    cross_references: Dict[str, List[str]]
    generation_time: float
    integrity_check: bool
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class DocumentGap:
    """Missing document in suite."""
    document_id: str
    expected_type: str
    severity: str
    description: str


@dataclass
class CrossReference:
    """Cross-reference between documents."""
    source_id: str
    target_id: str
    reference_type: str
    is_valid: bool


@dataclass
class DependencyIssue:
    """Dependency issue in suite."""
    document_id: str
    issue_type: str
    affected_documents: List[str]
    severity: ImpactSeverity
    resolution_suggestion: str


@dataclass
class ConsistencyReport:
    """Consistency analysis report."""
    suite_id: str
    total_documents: int
    dependency_issues: List[DependencyIssue]
    documentation_gaps: List[DocumentGap]
    broken_references: List[str]
    consistency_score: float
    coverage_percentage: float
    reference_integrity: float
    summary: str
    details: Dict[str, Any]
    recommendations: List[str]
    strategy_type: str = "basic"
    semantic_similarity: Optional[float] = None
    topic_clustering: Optional[Dict[str, List[str]]] = None


@dataclass
class EffortRange:
    """Effort estimation range."""
    min_hours: float
    max_hours: float
    confidence: float


@dataclass
class ImpactAnalysis:
    """Impact analysis result."""
    document_id: str
    change_type: ChangeType
    severity: ImpactSeverity
    directly_affected: List[str]
    indirectly_affected: List[str]
    total_affected: int
    estimated_effort_hours: float
    effort_confidence: float
    effort_range: EffortRange
    circular_dependencies: List[List[str]]
    has_circular_dependencies: bool
    resolution_suggestions: List[str]
    accuracy_score: float
    impact_scores: Dict[str, float] = field(default_factory=dict)