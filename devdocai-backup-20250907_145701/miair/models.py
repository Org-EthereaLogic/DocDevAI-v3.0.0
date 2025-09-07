"""
M003 MIAIR Engine - Data Models and Types

Pydantic v2 models for MIAIR processing, following M001/M002 patterns:
- Document model compatible with M002
- Optimization and analysis result models
- Semantic element and quality score models
- Validation and caching models
- Privacy-first design with secure defaults
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, ConfigDict, field_validator


class OperationMode(str, Enum):
    """Operation modes for MIAIR Engine."""
    BASIC = "basic"          # Core functionality only
    PERFORMANCE = "performance"  # Optimized with caching
    SECURE = "secure"        # Security hardened
    ENTERPRISE = "enterprise"   # Full features


class ElementType(str, Enum):
    """Types of semantic elements in documents."""
    HEADER = "header"
    PARAGRAPH = "paragraph"
    CODE_BLOCK = "code_block"
    LIST_ITEM = "list_item"
    LINK = "link"
    EMPHASIS = "emphasis"
    TECHNICAL_TERM = "technical_term"
    REQUIREMENT = "requirement"
    SPECIFICATION = "specification"
    DEFINITION = "definition"
    EXAMPLE = "example"
    WARNING = "warning"


class DocumentType(str, Enum):
    """Document types for optimization."""
    API_DOCUMENTATION = "api_documentation"
    USER_GUIDE = "user_guide"
    TECHNICAL_SPEC = "technical_spec"
    README = "readme"
    CHANGELOG = "changelog"
    TUTORIAL = "tutorial"
    REFERENCE = "reference"
    GENERAL = "general"


@dataclass
class SemanticElement:
    """Represents a semantic element in a document."""
    type: ElementType
    content: str
    position: int
    importance: float = 0.5  # 0.0 to 1.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class Document(BaseModel):
    """
    Document model for MIAIR processing.
    Compatible with M002 storage models.
    """
    
    model_config = ConfigDict(
        validate_assignment=True,
        extra='allow',  # Allow extra fields for compatibility
        str_strip_whitespace=True
    )
    
    id: str = Field(
        ...,
        description="Unique document identifier"
    )
    
    content: str = Field(
        ...,
        min_length=1,
        description="Document content"
    )
    
    type: DocumentType = Field(
        default=DocumentType.GENERAL,
        description="Document type for optimization"
    )
    
    title: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Document title"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Document metadata"
    )
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Document creation timestamp"
    )
    
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Document last update timestamp"
    )
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate document content."""
        if not v or not v.strip():
            raise ValueError("Document content cannot be empty")
        
        # Security check: basic content validation
        if len(v) > 1_000_000:  # 1MB limit for Pass 1
            raise ValueError("Document content too large (>1MB)")
        
        return v.strip()
    
    def copy(self) -> 'Document':
        """Create a deep copy of the document."""
        return Document(
            id=self.id,
            content=self.content,
            type=self.type,
            title=self.title,
            metadata=self.metadata.copy(),
            created_at=self.created_at,
            updated_at=datetime.now(timezone.utc)
        )


class QualityScore(BaseModel):
    """Represents a quality score with breakdown."""
    
    model_config = ConfigDict(validate_assignment=True)
    
    overall: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Overall quality score (0-100)"
    )
    
    completeness: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Content completeness score"
    )
    
    clarity: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Content clarity score"
    )
    
    consistency: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Content consistency score"
    )
    
    structure: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Document structure score"
    )
    
    technical_accuracy: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Technical accuracy score"
    )


class OptimizationResult(BaseModel):
    """Result of MIAIR optimization."""
    
    model_config = ConfigDict(validate_assignment=True)
    
    document: Document = Field(
        ...,
        description="Optimized document"
    )
    
    initial_entropy: float = Field(
        ...,
        description="Initial entropy score"
    )
    
    final_entropy: float = Field(
        ...,
        description="Final entropy score"
    )
    
    improvement: float = Field(
        ...,
        ge=0.0,
        description="Quality improvement percentage"
    )
    
    iterations: int = Field(
        ...,
        ge=0,
        description="Number of optimization iterations"
    )
    
    quality_score: QualityScore = Field(
        ...,
        description="Final quality score breakdown"
    )
    
    execution_time_ms: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Optimization execution time in milliseconds"
    )


class AnalysisResult(BaseModel):
    """Result of MIAIR analysis."""
    
    model_config = ConfigDict(validate_assignment=True)
    
    entropy: float = Field(
        ...,
        description="Document entropy score"
    )
    
    quality_score: QualityScore = Field(
        ...,
        description="Quality score breakdown"
    )
    
    semantic_elements: List[SemanticElement] = Field(
        default_factory=list,
        description="Extracted semantic elements"
    )
    
    improvement_potential: float = Field(
        ...,
        ge=0.0,
        description="Estimated improvement potential percentage"
    )
    
    meets_quality_gate: bool = Field(
        ...,
        description="Whether document meets quality gate (85%)"
    )
    
    patterns: Dict[str, Any] = Field(
        default_factory=dict,
        description="Identified patterns and issues"
    )


class ValidationResult(BaseModel):
    """Result of security validation."""
    
    model_config = ConfigDict(validate_assignment=True)
    
    valid: bool = Field(
        ...,
        description="Whether validation passed"
    )
    
    issues: List[str] = Field(
        default_factory=list,
        description="List of validation issues"
    )
    
    risk_level: str = Field(
        default="low",
        pattern="^(low|medium|high|critical)$",
        description="Risk level assessment"
    )
    
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed validation results"
    )


class CachedResult(BaseModel):
    """Cached optimization result."""
    
    model_config = ConfigDict(validate_assignment=True)
    
    document: Document = Field(
        ...,
        description="Cached document"
    )
    
    entropy: float = Field(
        ...,
        description="Cached entropy score"
    )
    
    quality_score: QualityScore = Field(
        ...,
        description="Cached quality score"
    )
    
    timestamp: datetime = Field(
        ...,
        description="Cache timestamp"
    )
    
    hit_count: int = Field(
        default=0,
        ge=0,
        description="Cache hit counter"
    )
    
    cache_key: str = Field(
        ...,
        description="Cache key for retrieval"
    )


class MIAIRConfig(BaseModel):
    """Configuration model for MIAIR Engine."""
    
    model_config = ConfigDict(validate_assignment=True)
    
    # Core optimization parameters
    entropy_threshold: float = Field(
        default=0.35,
        description="Maximum acceptable entropy"
    )
    
    target_entropy: float = Field(
        default=0.15,
        description="Target entropy for optimization"
    )
    
    coherence_target: float = Field(
        default=0.94,
        ge=0.0,
        le=1.0,
        description="Target coherence score"
    )
    
    quality_gate: float = Field(
        default=85.0,
        ge=0.0,
        le=100.0,
        description="Minimum quality percentage"
    )
    
    max_iterations: int = Field(
        default=7,
        ge=1,
        le=20,
        description="Maximum optimization iterations"
    )
    
    # Performance settings
    cache_size: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="Optimization cache size"
    )
    
    parallel_workers: int = Field(
        default=4,
        ge=1,
        le=16,
        description="Number of parallel workers"
    )
    
    # Security settings
    input_size_limit: int = Field(
        default=1_000_000,  # 1MB
        ge=1000,
        le=10_000_000,
        description="Maximum input size in bytes"
    )
    
    rate_limit_per_minute: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Rate limit per minute"
    )
    
    


# Type aliases for better readability
DocumentID = str
EntropyScore = float
QualityPercentage = float
ImprovementPercentage = float

# Export all models
__all__ = [
    'OperationMode',
    'ElementType', 
    'DocumentType',
    'SemanticElement',
    'Document',
    'QualityScore',
    'OptimizationResult',
    'AnalysisResult',
    'ValidationResult',
    'CachedResult',
    'MIAIRConfig',
    'DocumentID',
    'EntropyScore',
    'QualityPercentage',
    'ImprovementPercentage'
]