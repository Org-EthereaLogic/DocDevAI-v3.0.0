"""
Pydantic models for M006 Template Registry.

This module defines the data models for templates, categories, and metadata
used throughout the template registry system.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, field_validator
import hashlib


class TemplateCategory(str, Enum):
    """Template category enumeration."""
    
    API = "api"
    DOCUMENTATION = "documentation"
    GUIDES = "guides"
    SPECIFICATIONS = "specifications"
    PROJECTS = "projects"
    DEVELOPMENT = "development"
    TESTING = "testing"
    MISC = "miscellaneous"


class TemplateType(str, Enum):
    """Specific template types within categories."""
    
    # API Templates
    API_REFERENCE = "api_reference"
    API_ENDPOINT = "api_endpoint"
    OPENAPI_SPEC = "openapi_spec"
    REST_API = "rest_api"
    GRAPHQL_SCHEMA = "graphql_schema"
    
    # Documentation Templates
    README = "readme"
    USER_MANUAL = "user_manual"
    TECHNICAL_SPEC = "technical_specification"
    ARCHITECTURE_DOC = "architecture_document"
    DATABASE_SCHEMA = "database_schema"
    
    # Guide Templates
    INSTALLATION_GUIDE = "installation_guide"
    CONFIGURATION_GUIDE = "configuration_guide"
    DEPLOYMENT_GUIDE = "deployment_guide"
    MIGRATION_GUIDE = "migration_guide"
    INTEGRATION_GUIDE = "integration_guide"
    QUICK_START = "quick_start_guide"
    TUTORIAL = "tutorial"
    TROUBLESHOOTING = "troubleshooting_guide"
    
    # Specification Templates
    REQUIREMENTS_DOC = "requirements_document"
    DESIGN_DOC = "design_document"
    PROJECT_PROPOSAL = "project_proposal"
    SECURITY_DOC = "security_documentation"
    
    # Project Templates
    CONTRIBUTING = "contributing_guidelines"
    CODE_OF_CONDUCT = "code_of_conduct"
    LICENSE = "license"
    CHANGELOG = "changelog"
    RELEASE_NOTES = "release_notes"
    
    # Development Templates
    DEVELOPMENT_GUIDE = "development_guide"
    STYLE_GUIDE = "style_guide"
    BEST_PRACTICES = "best_practices"
    CODE_REVIEW = "code_review_checklist"
    
    # Testing Templates
    TEST_PLAN = "test_plan"
    TEST_CASES = "test_cases"
    PERFORMANCE_REPORT = "performance_report"
    BUG_REPORT = "bug_report"
    
    # Miscellaneous
    FAQ = "faq"
    REFERENCE_GUIDE = "reference_guide"
    GLOSSARY = "glossary"
    MEETING_NOTES = "meeting_notes"


class TemplateVariable(BaseModel):
    """Model for template variables."""
    
    name: str = Field(..., description="Variable name")
    description: Optional[str] = Field(None, description="Variable description")
    required: bool = Field(True, description="Whether variable is required")
    default: Optional[Any] = Field(None, description="Default value if not provided")
    type: str = Field("string", description="Variable type (string, number, boolean, list, object)")
    validation_pattern: Optional[str] = Field(None, description="Regex pattern for validation")
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate variable name format."""
        if not v or not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(f"Invalid variable name: {v}")
        return v


class TemplateSection(BaseModel):
    """Model for template sections."""
    
    id: Optional[str] = Field(None, description="Section identifier")
    name: str = Field(..., description="Section name")
    content: str = Field("", description="Section content")
    optional: bool = Field(False, description="Whether section is optional")
    repeatable: bool = Field(False, description="Whether section can be repeated")
    order: Optional[int] = Field(None, description="Section order")
    conditions: Optional[Dict[str, Any]] = Field(None, description="Conditions for including section")


class TemplateMetadata(BaseModel):
    """Model for template metadata."""
    
    id: str = Field(..., description="Unique template identifier")
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    category: TemplateCategory = Field(..., description="Template category")
    type: TemplateType = Field(..., description="Specific template type")
    version: str = Field("1.0.0", description="Template version")
    author: str = Field("DevDocAI", description="Template author")
    tags: List[str] = Field(default_factory=list, description="Template tags for searching")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")
    is_custom: bool = Field(False, description="Whether template is custom (user-created)")
    is_active: bool = Field(True, description="Whether template is active")
    usage_count: int = Field(0, description="Number of times template has been used")
    
    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate semantic version format."""
        import re
        pattern = r"^\d+\.\d+\.\d+(-[\w.]+)?(\+[\w.]+)?$"
        if not re.match(pattern, v):
            raise ValueError(f"Invalid version format: {v}")
        return v
    
    def generate_id(self) -> str:
        """Generate unique ID based on name and category."""
        data = f"{self.category.value}_{self.type.value}_{self.name}"
        return hashlib.md5(data.encode()).hexdigest()[:12]


class Template(BaseModel):
    """Complete template model."""
    
    metadata: TemplateMetadata = Field(..., description="Template metadata")
    content: str = Field(..., description="Template content with placeholders")
    variables: List[TemplateVariable] = Field(default_factory=list, description="Template variables")
    sections: List[TemplateSection] = Field(default_factory=list, description="Template sections")
    includes: List[str] = Field(default_factory=list, description="Other templates to include")
    
    def get_required_variables(self) -> List[TemplateVariable]:
        """Get list of required variables."""
        return [var for var in self.variables if var.required]
    
    def get_optional_variables(self) -> List[TemplateVariable]:
        """Get list of optional variables."""
        return [var for var in self.variables if not var.required]
    
    def validate_content(self) -> bool:
        """Validate template content structure."""
        # Check for balanced brackets
        open_count = self.content.count("{{")
        close_count = self.content.count("}}")
        return open_count == close_count


class TemplateSearchCriteria(BaseModel):
    """Model for template search criteria."""
    
    category: Optional[TemplateCategory] = Field(None, description="Filter by category")
    type: Optional[TemplateType] = Field(None, description="Filter by type")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    author: Optional[str] = Field(None, description="Filter by author")
    is_custom: Optional[bool] = Field(None, description="Filter custom templates")
    is_active: Optional[bool] = Field(True, description="Filter active templates")
    search_text: Optional[str] = Field(None, description="Text search in name/description")


class TemplateRenderContext(BaseModel):
    """Model for template rendering context."""
    
    variables: Dict[str, Any] = Field(default_factory=dict, description="Variable values")
    sections: Dict[str, bool] = Field(default_factory=dict, description="Section inclusion flags")
    loops: Dict[str, List[Any]] = Field(default_factory=dict, description="Loop data")
    
    def merge(self, other: "TemplateRenderContext") -> "TemplateRenderContext":
        """Merge with another context."""
        return TemplateRenderContext(
            variables={**self.variables, **other.variables},
            sections={**self.sections, **other.sections},
            loops={**self.loops, **other.loops}
        )


class TemplateValidationResult(BaseModel):
    """Model for template validation results."""
    
    is_valid: bool = Field(..., description="Whether template is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    missing_variables: List[str] = Field(default_factory=list, description="Missing required variables")
    unused_variables: List[str] = Field(default_factory=list, description="Defined but unused variables")