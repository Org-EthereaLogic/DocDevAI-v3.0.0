"""
Tests for M006 Template Registry models.

This module tests all Pydantic models used in the template system,
including validation, serialization, and model operations.
"""

import pytest
from datetime import datetime
from typing import List

from devdocai.templates.models import (
    TemplateCategory,
    TemplateType,
    TemplateVariable,
    TemplateSection,
    TemplateMetadata,
    Template,
    TemplateSearchCriteria,
    TemplateRenderContext,
    TemplateValidationResult
)


class TestTemplateCategory:
    """Test TemplateCategory enum."""
    
    def test_category_values(self):
        """Test category enum values."""
        assert TemplateCategory.API == "api"
        assert TemplateCategory.DOCUMENTATION == "documentation"
        assert TemplateCategory.GUIDES == "guides"
        assert TemplateCategory.SPECIFICATIONS == "specifications"
        assert TemplateCategory.PROJECTS == "projects"
        assert TemplateCategory.DEVELOPMENT == "development"
        assert TemplateCategory.TESTING == "testing"
        assert TemplateCategory.MISC == "miscellaneous"
    
    def test_category_count(self):
        """Test total number of categories."""
        assert len(TemplateCategory) == 8


class TestTemplateType:
    """Test TemplateType enum."""
    
    def test_api_types(self):
        """Test API template types."""
        api_types = [
            TemplateType.API_REFERENCE,
            TemplateType.API_ENDPOINT,
            TemplateType.OPENAPI_SPEC,
            TemplateType.REST_API,
            TemplateType.GRAPHQL_SCHEMA
        ]
        assert all(isinstance(t, TemplateType) for t in api_types)
    
    def test_documentation_types(self):
        """Test documentation template types."""
        doc_types = [
            TemplateType.README,
            TemplateType.USER_MANUAL,
            TemplateType.TECHNICAL_SPEC,
            TemplateType.ARCHITECTURE_DOC,
            TemplateType.DATABASE_SCHEMA
        ]
        assert all(isinstance(t, TemplateType) for t in doc_types)
    
    def test_guide_types(self):
        """Test guide template types."""
        guide_types = [
            TemplateType.INSTALLATION_GUIDE,
            TemplateType.CONFIGURATION_GUIDE,
            TemplateType.DEPLOYMENT_GUIDE,
            TemplateType.MIGRATION_GUIDE,
            TemplateType.INTEGRATION_GUIDE,
            TemplateType.QUICK_START,
            TemplateType.TUTORIAL,
            TemplateType.TROUBLESHOOTING
        ]
        assert all(isinstance(t, TemplateType) for t in guide_types)


class TestTemplateVariable:
    """Test TemplateVariable model."""
    
    def test_valid_variable_creation(self):
        """Test creating valid template variables."""
        var = TemplateVariable(
            name="test_var",
            description="Test variable",
            required=True,
            default=None,
            type="string"
        )
        assert var.name == "test_var"
        assert var.description == "Test variable"
        assert var.required is True
        assert var.default is None
        assert var.type == "string"
    
    def test_variable_defaults(self):
        """Test variable default values."""
        var = TemplateVariable(name="test_var")
        assert var.required is True
        assert var.type == "string"
        assert var.validation_pattern is None
    
    def test_invalid_variable_name(self):
        """Test invalid variable names."""
        with pytest.raises(ValueError, match="Invalid variable name"):
            TemplateVariable(name="123invalid")
        
        with pytest.raises(ValueError, match="Invalid variable name"):
            TemplateVariable(name="invalid-name!")
        
        with pytest.raises(ValueError, match="Invalid variable name"):
            TemplateVariable(name="")
    
    def test_valid_variable_names(self):
        """Test valid variable names."""
        valid_names = [
            "valid_name",
            "validName",
            "valid-name",
            "var123",
            "a",
            "A_B_C"
        ]
        for name in valid_names:
            var = TemplateVariable(name=name)
            assert var.name == name


class TestTemplateSection:
    """Test TemplateSection model."""
    
    def test_section_creation(self):
        """Test creating template sections."""
        section = TemplateSection(
            name="intro",
            content="Introduction content",
            optional=True,
            repeatable=False,
            conditions={"var": "value"}
        )
        assert section.name == "intro"
        assert section.content == "Introduction content"
        assert section.optional is True
        assert section.repeatable is False
        assert section.conditions == {"var": "value"}
    
    def test_section_defaults(self):
        """Test section default values."""
        section = TemplateSection(name="test", content="test content")
        assert section.optional is False
        assert section.repeatable is False
        assert section.conditions is None


class TestTemplateMetadata:
    """Test TemplateMetadata model."""
    
    def test_metadata_creation(self):
        """Test creating template metadata."""
        metadata = TemplateMetadata(
            id="test_template",
            name="Test Template",
            description="A test template",
            category=TemplateCategory.DOCUMENTATION,
            type=TemplateType.README
        )
        assert metadata.id == "test_template"
        assert metadata.name == "Test Template"
        assert metadata.description == "A test template"
        assert metadata.category == TemplateCategory.DOCUMENTATION
        assert metadata.type == TemplateType.README
    
    def test_metadata_defaults(self):
        """Test metadata default values."""
        metadata = TemplateMetadata(
            id="test",
            name="Test",
            description="Test description",
            category=TemplateCategory.MISC,
            type=TemplateType.FAQ
        )
        assert metadata.version == "1.0.0"
        assert metadata.author == "DevDocAI"
        assert metadata.tags == []
        assert metadata.is_custom is False
        assert metadata.is_active is True
        assert metadata.usage_count == 0
        assert isinstance(metadata.created_at, datetime)
        assert isinstance(metadata.updated_at, datetime)
    
    def test_version_validation(self):
        """Test semantic version validation."""
        valid_versions = ["1.0.0", "2.1.3", "1.0.0-alpha", "1.0.0+build"]
        for version in valid_versions:
            metadata = TemplateMetadata(
                id="test",
                name="Test",
                description="Test",
                category=TemplateCategory.MISC,
                type=TemplateType.FAQ,
                version=version
            )
            assert metadata.version == version
    
    def test_invalid_version(self):
        """Test invalid version formats."""
        invalid_versions = ["1.0", "v1.0.0", "1.0.0.0", "invalid"]
        for version in invalid_versions:
            with pytest.raises(ValueError, match="Invalid version format"):
                TemplateMetadata(
                    id="test",
                    name="Test",
                    description="Test",
                    category=TemplateCategory.MISC,
                    type=TemplateType.FAQ,
                    version=version
                )
    
    def test_id_generation(self):
        """Test automatic ID generation."""
        metadata = TemplateMetadata(
            id="",  # Will trigger generation
            name="Test Template",
            description="Test",
            category=TemplateCategory.API,
            type=TemplateType.API_REFERENCE
        )
        generated_id = metadata.generate_id()
        assert len(generated_id) == 12
        assert generated_id.isalnum()


class TestTemplate:
    """Test Template model."""
    
    @pytest.fixture
    def sample_metadata(self):
        """Create sample metadata."""
        return TemplateMetadata(
            id="test_template",
            name="Test Template",
            description="A test template",
            category=TemplateCategory.DOCUMENTATION,
            type=TemplateType.README
        )
    
    @pytest.fixture
    def sample_variables(self):
        """Create sample variables."""
        return [
            TemplateVariable(name="title", description="Document title", required=True),
            TemplateVariable(name="author", description="Document author", required=False, default="Unknown")
        ]
    
    @pytest.fixture
    def sample_sections(self):
        """Create sample sections."""
        return [
            TemplateSection(name="intro", content="Introduction section"),
            TemplateSection(name="details", content="Details section", optional=True)
        ]
    
    def test_template_creation(self, sample_metadata, sample_variables, sample_sections):
        """Test creating a complete template."""
        template = Template(
            metadata=sample_metadata,
            content="# {{title}}\n\nBy {{author}}",
            variables=sample_variables,
            sections=sample_sections,
            includes=["common/header.md"]
        )
        assert template.metadata.id == "test_template"
        assert "{{title}}" in template.content
        assert len(template.variables) == 2
        assert len(template.sections) == 2
        assert template.includes == ["common/header.md"]
    
    def test_template_defaults(self, sample_metadata):
        """Test template default values."""
        template = Template(
            metadata=sample_metadata,
            content="Basic content"
        )
        assert template.variables == []
        assert template.sections == []
        assert template.includes == []
    
    def test_get_required_variables(self, sample_metadata, sample_variables):
        """Test getting required variables."""
        template = Template(
            metadata=sample_metadata,
            content="Test content",
            variables=sample_variables
        )
        required = template.get_required_variables()
        assert len(required) == 1
        assert required[0].name == "title"
    
    def test_get_optional_variables(self, sample_metadata, sample_variables):
        """Test getting optional variables."""
        template = Template(
            metadata=sample_metadata,
            content="Test content",
            variables=sample_variables
        )
        optional = template.get_optional_variables()
        assert len(optional) == 1
        assert optional[0].name == "author"
    
    def test_validate_content(self, sample_metadata):
        """Test content validation."""
        # Valid content
        template1 = Template(
            metadata=sample_metadata,
            content="Hello {{name}}, welcome to {{project}}!"
        )
        assert template1.validate_content() is True
        
        # Invalid content (unbalanced brackets)
        template2 = Template(
            metadata=sample_metadata,
            content="Hello {{name}, welcome to {{project}}!"
        )
        assert template2.validate_content() is False


class TestTemplateSearchCriteria:
    """Test TemplateSearchCriteria model."""
    
    def test_search_criteria_creation(self):
        """Test creating search criteria."""
        criteria = TemplateSearchCriteria(
            category=TemplateCategory.API,
            type=TemplateType.API_REFERENCE,
            tags=["rest", "api"],
            author="DevDocAI",
            is_custom=False,
            is_active=True,
            search_text="documentation"
        )
        assert criteria.category == TemplateCategory.API
        assert criteria.type == TemplateType.API_REFERENCE
        assert criteria.tags == ["rest", "api"]
        assert criteria.author == "DevDocAI"
        assert criteria.is_custom is False
        assert criteria.is_active is True
        assert criteria.search_text == "documentation"
    
    def test_search_criteria_defaults(self):
        """Test search criteria default values."""
        criteria = TemplateSearchCriteria()
        assert criteria.category is None
        assert criteria.type is None
        assert criteria.tags is None
        assert criteria.author is None
        assert criteria.is_custom is None
        assert criteria.is_active is True
        assert criteria.search_text is None


class TestTemplateRenderContext:
    """Test TemplateRenderContext model."""
    
    def test_render_context_creation(self):
        """Test creating render context."""
        context = TemplateRenderContext(
            variables={"name": "John", "age": 30},
            sections={"intro": True, "details": False},
            loops={"items": [1, 2, 3]}
        )
        assert context.variables == {"name": "John", "age": 30}
        assert context.sections == {"intro": True, "details": False}
        assert context.loops == {"items": [1, 2, 3]}
    
    def test_render_context_defaults(self):
        """Test render context default values."""
        context = TemplateRenderContext()
        assert context.variables == {}
        assert context.sections == {}
        assert context.loops == {}
    
    def test_context_merge(self):
        """Test merging render contexts."""
        context1 = TemplateRenderContext(
            variables={"a": 1, "b": 2},
            sections={"s1": True},
            loops={"l1": [1, 2]}
        )
        context2 = TemplateRenderContext(
            variables={"b": 3, "c": 4},
            sections={"s2": False},
            loops={"l2": [3, 4]}
        )
        
        merged = context1.merge(context2)
        assert merged.variables == {"a": 1, "b": 3, "c": 4}  # context2 overwrites
        assert merged.sections == {"s1": True, "s2": False}
        assert merged.loops == {"l1": [1, 2], "l2": [3, 4]}


class TestTemplateValidationResult:
    """Test TemplateValidationResult model."""
    
    def test_validation_result_creation(self):
        """Test creating validation results."""
        result = TemplateValidationResult(
            is_valid=False,
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"],
            missing_variables=["var1"],
            unused_variables=["var2"]
        )
        assert result.is_valid is False
        assert result.errors == ["Error 1", "Error 2"]
        assert result.warnings == ["Warning 1"]
        assert result.missing_variables == ["var1"]
        assert result.unused_variables == ["var2"]
    
    def test_validation_result_defaults(self):
        """Test validation result default values."""
        result = TemplateValidationResult(is_valid=True)
        assert result.errors == []
        assert result.warnings == []
        assert result.missing_variables == []
        assert result.unused_variables == []
    
    def test_valid_result(self):
        """Test valid validation result."""
        result = TemplateValidationResult(
            is_valid=True,
            errors=[],
            warnings=["Minor warning"]
        )
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 1


if __name__ == "__main__":
    pytest.main([__file__])