"""
Tests for M006 Template Registry validator.

This module tests template validation including syntax checking,
variable validation, security checks, and structural validation.
"""

import pytest
import re

from devdocai.templates.validator import TemplateValidator
from devdocai.templates.models import (
    Template,
    TemplateMetadata,
    TemplateVariable,
    TemplateSection,
    TemplateCategory,
    TemplateType,
    TemplateValidationResult
)


class TestTemplateValidator:
    """Test TemplateValidator class."""
    
    @pytest.fixture
    def validator(self):
        """Create template validator instance."""
        return TemplateValidator()
    
    @pytest.fixture
    def valid_template(self):
        """Create a valid template for testing."""
        metadata = TemplateMetadata(
            id="valid_template",
            name="Valid Template",
            description="A valid template for testing",
            category=TemplateCategory.DOCUMENTATION,
            type=TemplateType.README,
            tags=["test", "valid"]
        )
        variables = [
            TemplateVariable(name="title", description="Document title", required=True),
            TemplateVariable(name="author", description="Document author", required=False, default="Unknown")
        ]
        sections = [
            TemplateSection(name="intro", content="Introduction content"),
            TemplateSection(name="details", content="Details content", optional=True)
        ]
        return Template(
            metadata=metadata,
            content="# {{title}}\n\nBy {{author}}\n\n<!-- SECTION: intro -->{{intro}}<!-- END SECTION: intro -->",
            variables=variables,
            sections=sections
        )


class TestBasicValidation:
    """Test basic template validation."""
    
    @pytest.fixture
    def validator(self):
        return TemplateValidator()
    
    def test_valid_template_validation(self, validator, valid_template):
        """Test validation of a completely valid template."""
        result = validator.validate(valid_template)
        assert isinstance(result, TemplateValidationResult)
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_template_size_limit(self, validator):
        """Test template size validation."""
        metadata = TemplateMetadata(
            id="large_template",
            name="Large Template",
            description="A template that exceeds size limit",
            category=TemplateCategory.MISC,
            type=TemplateType.FAQ
        )
        large_content = "x" * (1024 * 1024 + 1)  # Exceed 1MB limit
        template = Template(metadata=metadata, content=large_content)
        
        result = validator.validate(template)
        assert result.is_valid is False
        assert any("exceeds maximum size" in error for error in result.errors)


class TestMetadataValidation:
    """Test metadata validation."""
    
    @pytest.fixture
    def validator(self):
        return TemplateValidator()
    
    def test_missing_name(self, validator):
        """Test validation with missing template name."""
        metadata = TemplateMetadata(
            id="test",
            name="",  # Empty name
            description="Test description",
            category=TemplateCategory.MISC,
            type=TemplateType.FAQ
        )
        template = Template(metadata=metadata, content="Test content")
        
        result = validator.validate(template)
        assert result.is_valid is False
        assert any("name is required" in error for error in result.errors)
    
    def test_long_name(self, validator):
        """Test validation with excessively long name."""
        metadata = TemplateMetadata(
            id="test",
            name="x" * 101,  # Exceed 100 character limit
            description="Test description",
            category=TemplateCategory.MISC,
            type=TemplateType.FAQ
        )
        template = Template(metadata=metadata, content="Test content")
        
        result = validator.validate(template)
        assert result.is_valid is False
        assert any("name exceeds 100 characters" in error for error in result.errors)
    
    def test_missing_description(self, validator):
        """Test validation with missing description."""
        metadata = TemplateMetadata(
            id="test",
            name="Test Template",
            description="",  # Empty description
            category=TemplateCategory.MISC,
            type=TemplateType.FAQ
        )
        template = Template(metadata=metadata, content="Test content")
        
        result = validator.validate(template)
        assert result.is_valid is False
        assert any("description is required" in error for error in result.errors)
    
    def test_long_description(self, validator):
        """Test validation with excessively long description."""
        metadata = TemplateMetadata(
            id="test",
            name="Test Template",
            description="x" * 501,  # Exceed 500 character limit
            category=TemplateCategory.MISC,
            type=TemplateType.FAQ
        )
        template = Template(metadata=metadata, content="Test content")
        
        result = validator.validate(template)
        assert result.is_valid is False
        assert any("description exceeds 500 characters" in error for error in result.errors)
    
    def test_invalid_id_format(self, validator):
        """Test validation with invalid ID format."""
        metadata = TemplateMetadata(
            id="invalid id!@#",  # Invalid characters
            name="Test Template",
            description="Test description",
            category=TemplateCategory.MISC,
            type=TemplateType.FAQ
        )
        template = Template(metadata=metadata, content="Test content")
        
        result = validator.validate(template)
        assert result.is_valid is False
        assert any("Invalid template ID format" in error for error in result.errors)
    
    def test_too_many_tags(self, validator):
        """Test validation with too many tags."""
        metadata = TemplateMetadata(
            id="test",
            name="Test Template",
            description="Test description",
            category=TemplateCategory.MISC,
            type=TemplateType.FAQ,
            tags=[f"tag{i}" for i in range(21)]  # Exceed 20 tag limit
        )
        template = Template(metadata=metadata, content="Test content")
        
        result = validator.validate(template)
        assert result.is_valid is False
        assert any("Too many tags" in error for error in result.errors)
    
    def test_long_tag(self, validator):
        """Test validation with excessively long tag."""
        metadata = TemplateMetadata(
            id="test",
            name="Test Template",
            description="Test description",
            category=TemplateCategory.MISC,
            type=TemplateType.FAQ,
            tags=["x" * 51]  # Exceed 50 character limit
        )
        template = Template(metadata=metadata, content="Test content")
        
        result = validator.validate(template)
        assert result.is_valid is False
        assert any("exceeds 50 characters" in error for error in result.errors)
    
    def test_invalid_tag_format(self, validator):
        """Test validation with invalid tag format."""
        metadata = TemplateMetadata(
            id="test",
            name="Test Template",
            description="Test description",
            category=TemplateCategory.MISC,
            type=TemplateType.FAQ,
            tags=["invalid tag!@#"]  # Invalid characters
        )
        template = Template(metadata=metadata, content="Test content")
        
        result = validator.validate(template)
        assert result.is_valid is False
        assert any("Invalid tag format" in error for error in result.errors)


class TestVariableValidation:
    """Test variable validation."""
    
    @pytest.fixture
    def validator(self):
        return TemplateValidator()
    
    def test_too_many_variables(self, validator):
        """Test validation with too many variables."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        # Create 101 variables (exceed limit of 100)
        variables = [
            TemplateVariable(name=f"var{i}", description=f"Variable {i}")
            for i in range(101)
        ]
        template = Template(metadata=metadata, content="Test", variables=variables)
        
        result = validator.validate(template)
        assert result.is_valid is False
        assert any("Too many variables" in error for error in result.errors)
    
    def test_duplicate_variable_names(self, validator):
        """Test validation with duplicate variable names."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        variables = [
            TemplateVariable(name="duplicate", description="First"),
            TemplateVariable(name="duplicate", description="Second")
        ]
        template = Template(metadata=metadata, content="Test", variables=variables)
        
        result = validator.validate(template)
        assert result.is_valid is False
        assert any("Duplicate variable name: duplicate" in error for error in result.errors)
    
    def test_invalid_variable_name(self, validator):
        """Test validation with invalid variable name."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        variables = [
            TemplateVariable(name="123invalid", description="Invalid name")  # Starts with number
        ]
        template = Template(metadata=metadata, content="Test", variables=variables)
        
        result = validator.validate(template)
        assert result.is_valid is False
        assert any("Invalid variable name format" in error for error in result.errors)
    
    def test_invalid_regex_pattern(self, validator):
        """Test validation with invalid regex pattern."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        variables = [
            TemplateVariable(name="test_var", validation_pattern="[invalid")  # Broken regex
        ]
        template = Template(metadata=metadata, content="Test", variables=variables)
        
        result = validator.validate(template)
        assert result.is_valid is False
        assert any("Invalid regex pattern" in error for error in result.errors)
    
    def test_optional_variable_no_default_warning(self, validator):
        """Test warning for optional variable without default."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        variables = [
            TemplateVariable(name="optional_var", required=False)  # No default
        ]
        template = Template(metadata=metadata, content="Test", variables=variables)
        
        result = validator.validate(template)
        assert any("has no default value" in warning for warning in result.warnings)
    
    def test_invalid_variable_type(self, validator):
        """Test validation with invalid variable type."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        variables = [
            TemplateVariable(name="test_var", type="invalid_type")
        ]
        template = Template(metadata=metadata, content="Test", variables=variables)
        
        result = validator.validate(template)
        assert result.is_valid is False
        assert any("Invalid variable type" in error for error in result.errors)


class TestVariableUsageCheck:
    """Test variable usage checking."""
    
    @pytest.fixture
    def validator(self):
        return TemplateValidator()
    
    def test_missing_variable_warning(self, validator):
        """Test warning for referenced but undefined variable."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        template = Template(
            metadata=metadata,
            content="Hello {{undefined_var}}!",
            variables=[]  # No variables defined
        )
        
        result = validator.validate(template)
        assert any("referenced but not defined" in warning for warning in result.warnings)
        assert "undefined_var" in result.missing_variables
    
    def test_unused_variable_warning(self, validator):
        """Test warning for defined but unused variable."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        variables = [
            TemplateVariable(name="unused_var", description="Not used anywhere")
        ]
        template = Template(
            metadata=metadata,
            content="Hello world!",  # Doesn't use the variable
            variables=variables
        )
        
        result = validator.validate(template)
        assert any("defined but not used" in warning for warning in result.warnings)
        assert "unused_var" in result.unused_variables


class TestSectionValidation:
    """Test section validation."""
    
    @pytest.fixture
    def validator(self):
        return TemplateValidator()
    
    def test_duplicate_section_names(self, validator):
        """Test validation with duplicate section names."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        sections = [
            TemplateSection(name="duplicate", content="First"),
            TemplateSection(name="duplicate", content="Second")
        ]
        template = Template(metadata=metadata, content="Test", sections=sections)
        
        result = validator.validate(template)
        assert result.is_valid is False
        assert any("Duplicate section name: duplicate" in error for error in result.errors)
    
    def test_invalid_section_name(self, validator):
        """Test validation with invalid section name."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        sections = [
            TemplateSection(name="123invalid", content="Invalid name")  # Starts with number
        ]
        template = Template(metadata=metadata, content="Test", sections=sections)
        
        result = validator.validate(template)
        assert result.is_valid is False
        assert any("Invalid section name format" in error for error in result.errors)
    
    def test_unused_section(self, validator):
        """Test validation with defined but unused section."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        sections = [
            TemplateSection(name="unused_section", content="Not used")
        ]
        template = Template(
            metadata=metadata,
            content="Content without section",
            sections=sections
        )
        
        result = validator.validate(template)
        assert result.is_valid is False
        assert any("defined but not used in template" in error for error in result.errors)


class TestIncludeValidation:
    """Test include validation."""
    
    @pytest.fixture
    def validator(self):
        return TemplateValidator()
    
    def test_too_many_includes(self, validator):
        """Test validation with too many includes."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        # Create 21 includes (exceed limit of 20)
        includes = [f"include{i}.md" for i in range(21)]
        template = Template(metadata=metadata, content="Test", includes=includes)
        
        result = validator.validate(template)
        assert result.is_valid is False
        assert any("Too many includes" in error for error in result.errors)
    
    def test_empty_include_path(self, validator):
        """Test validation with empty include path."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        template = Template(metadata=metadata, content="Test", includes=[""])
        
        result = validator.validate(template)
        assert result.is_valid is False
        assert any("Empty include path" in error for error in result.errors)
    
    def test_parent_directory_include(self, validator):
        """Test validation with parent directory reference in include."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        template = Template(metadata=metadata, content="Test", includes=["../parent/file.md"])
        
        result = validator.validate(template)
        assert result.is_valid is False
        assert any("parent directory reference" in error for error in result.errors)
    
    def test_absolute_include_path(self, validator):
        """Test validation with absolute include path."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        template = Template(metadata=metadata, content="Test", includes=["/absolute/path.md"])
        
        result = validator.validate(template)
        assert result.is_valid is False
        assert any("Include path is absolute" in error for error in result.errors)
    
    def test_self_include(self, validator):
        """Test validation with self-referential include."""
        metadata = TemplateMetadata(
            id="test_template", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        template = Template(
            metadata=metadata, 
            content="Test", 
            includes=["test_template"]  # Include itself
        )
        
        result = validator.validate(template)
        assert result.is_valid is False
        assert any("Template includes itself" in error for error in result.errors)


class TestSecurityValidation:
    """Test security validation."""
    
    @pytest.fixture
    def validator(self):
        return TemplateValidator()
    
    def test_script_injection_warning(self, validator):
        """Test warning for potential script injection."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        template = Template(
            metadata=metadata,
            content="<script>alert('xss')</script>"
        )
        
        result = validator.validate(template)
        assert any("Potential security risk" in warning for warning in result.warnings)
    
    def test_event_handler_warning(self, validator):
        """Test warning for event handler attributes."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        template = Template(
            metadata=metadata,
            content="<div onclick='malicious()'>Click me</div>"
        )
        
        result = validator.validate(template)
        assert any("Potential security risk" in warning for warning in result.warnings)
    
    def test_javascript_protocol_warning(self, validator):
        """Test warning for javascript: protocol."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        template = Template(
            metadata=metadata,
            content="<a href='javascript:alert(1)'>Click</a>"
        )
        
        result = validator.validate(template)
        assert any("Potential security risk" in warning for warning in result.warnings)
    
    def test_sql_pattern_warning(self, validator):
        """Test warning for SQL-like patterns."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        template = Template(
            metadata=metadata,
            content="DROP TABLE users; DELETE FROM accounts;"
        )
        
        result = validator.validate(template)
        assert any("Potential SQL pattern" in warning for warning in result.warnings)
    
    def test_high_special_char_concentration_warning(self, validator):
        """Test warning for high concentration of special characters."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        # Create content with >10% special characters
        template = Template(
            metadata=metadata,
            content="<>\"'`<>\"'`<>\"'`<>\"'`<>\"'`"  # 25 chars, all special
        )
        
        result = validator.validate(template)
        assert any("High concentration of special characters" in warning for warning in result.warnings)


class TestRenderContextValidation:
    """Test render context validation."""
    
    @pytest.fixture
    def validator(self):
        return TemplateValidator()
    
    @pytest.fixture
    def template_with_variables(self):
        """Create template with various variable types."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        variables = [
            TemplateVariable(name="required_str", type="string", required=True),
            TemplateVariable(name="optional_str", type="string", required=False),
            TemplateVariable(name="number_var", type="number", required=True),
            TemplateVariable(name="bool_var", type="boolean", required=True),
            TemplateVariable(name="list_var", type="list", required=True),
            TemplateVariable(name="obj_var", type="object", required=True),
            TemplateVariable(name="pattern_var", type="string", validation_pattern=r"^\d{3}$", required=True)
        ]
        return Template(metadata=metadata, content="Test", variables=variables)
    
    def test_missing_required_variable(self, validator, template_with_variables):
        """Test validation with missing required variable."""
        context = {
            "number_var": 42,
            "bool_var": True,
            "list_var": [1, 2, 3],
            "obj_var": {"key": "value"},
            "pattern_var": "123"
            # Missing required_str
        }
        
        errors = validator.validate_render_context(template_with_variables, context)
        assert any("Required variable 'required_str' not provided" in error for error in errors)
    
    def test_invalid_type_validation(self, validator, template_with_variables):
        """Test validation with incorrect variable types."""
        context = {
            "required_str": "hello",
            "number_var": "not_a_number",  # Should be number
            "bool_var": "not_a_boolean",   # Should be boolean
            "list_var": "not_a_list",      # Should be list
            "obj_var": "not_an_object",    # Should be object
            "pattern_var": "123"
        }
        
        errors = validator.validate_render_context(template_with_variables, context)
        assert any("should be a number" in error for error in errors)
        assert any("should be a boolean" in error for error in errors)
        assert any("should be a list" in error for error in errors)
        assert any("should be an object" in error for error in errors)
    
    def test_pattern_validation_failure(self, validator, template_with_variables):
        """Test validation with pattern mismatch."""
        context = {
            "required_str": "hello",
            "number_var": 42,
            "bool_var": True,
            "list_var": [1, 2, 3],
            "obj_var": {"key": "value"},
            "pattern_var": "invalid_pattern"  # Doesn't match ^\d{3}$
        }
        
        errors = validator.validate_render_context(template_with_variables, context)
        assert any("does not match validation pattern" in error for error in errors)
    
    def test_valid_context(self, validator, template_with_variables):
        """Test validation with valid context."""
        context = {
            "required_str": "hello",
            "optional_str": "world",
            "number_var": 42,
            "bool_var": True,
            "list_var": [1, 2, 3],
            "obj_var": {"key": "value"},
            "pattern_var": "123"
        }
        
        errors = validator.validate_render_context(template_with_variables, context)
        assert len(errors) == 0


if __name__ == "__main__":
    pytest.main([__file__])