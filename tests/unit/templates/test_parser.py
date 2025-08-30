"""
Tests for M006 Template Registry parser.

This module tests the template parsing engine with variables,
sections, conditionals, loops, and includes.
"""

import pytest
from unittest.mock import Mock, patch

from devdocai.templates.parser import TemplateParser
from devdocai.templates.models import (
    Template,
    TemplateMetadata,
    TemplateVariable,
    TemplateRenderContext,
    TemplateCategory,
    TemplateType
)
from devdocai.templates.exceptions import (
    TemplateParseError,
    TemplateRenderError,
    TemplateIncludeError
)


class TestTemplateParser:
    """Test TemplateParser class."""
    
    @pytest.fixture
    def parser(self):
        """Create template parser instance."""
        return TemplateParser()
    
    @pytest.fixture
    def sample_template(self):
        """Create sample template."""
        metadata = TemplateMetadata(
            id="test_template",
            name="Test Template",
            description="Test template",
            category=TemplateCategory.DOCUMENTATION,
            type=TemplateType.README
        )
        return Template(
            metadata=metadata,
            content="Hello {{name}}, welcome to {{project}}!",
            variables=[
                TemplateVariable(name="name", required=True, type="string"),
                TemplateVariable(name="project", required=True, type="string")
            ]
        )
    
    @pytest.fixture
    def sample_context(self):
        """Create sample render context."""
        return TemplateRenderContext(
            variables={
                "name": "John",
                "project": "DevDocAI",
                "active": True,
                "items": ["item1", "item2", "item3"],
                "user": {"name": "John", "role": "admin"}
            },
            sections={"intro": True, "details": False},
            loops={"items": ["A", "B", "C"]}
        )


class TestVariableSubstitution:
    """Test variable substitution functionality."""
    
    @pytest.fixture
    def parser(self):
        return TemplateParser()
    
    def test_simple_variable_substitution(self, parser, sample_template, sample_context):
        """Test basic variable substitution."""
        result = parser.parse(sample_template, sample_context)
        assert result == "Hello John, welcome to DevDocAI!"
    
    def test_nested_property_access(self, parser, sample_context):
        """Test nested property access in variables."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        template = Template(
            metadata=metadata,
            content="User: {{user.name}} ({{user.role}})",
            variables=[
                TemplateVariable(name="user", required=True, type="object")
            ]
        )
        
        result = parser.parse(template, sample_context)
        assert result == "User: John (admin)"
    
    def test_missing_required_variable(self, parser, sample_template):
        """Test error on missing required variable."""
        context = TemplateRenderContext(variables={"name": "John"})  # Missing 'project'
        
        with pytest.raises(TemplateRenderError, match="Missing required variables"):
            parser.parse(sample_template, context)
    
    def test_default_value_substitution(self, parser, sample_context):
        """Test substitution with default values."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        template = Template(
            metadata=metadata,
            content="Hello {{name}}, version: {{version}}",
            variables=[
                TemplateVariable(name="name", required=True, type="string"),
                TemplateVariable(name="version", required=False, type="string", default="1.0.0")
            ]
        )
        
        context = TemplateRenderContext(variables={"name": "John"})
        result = parser.parse(template, context)
        assert result == "Hello John, version: 1.0.0"
    
    def test_missing_optional_variable(self, parser, sample_context):
        """Test behavior with missing optional variable."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        template = Template(
            metadata=metadata,
            content="Hello {{name}}, optional: {{optional_var}}",
            variables=[
                TemplateVariable(name="name", required=True, type="string"),
                TemplateVariable(name="optional_var", required=False, type="string")
            ]
        )
        
        context = TemplateRenderContext(variables={"name": "John"})
        result = parser.parse(template, context)
        assert result == "Hello John, optional: {{optional_var}}"  # Placeholder remains


class TestConditionals:
    """Test conditional processing."""
    
    @pytest.fixture
    def parser(self):
        return TemplateParser()
    
    def test_simple_conditional(self, parser, sample_context):
        """Test simple IF conditional."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        template = Template(
            metadata=metadata,
            content="<!-- IF active -->User is active<!-- END IF -->",
            variables=[
                TemplateVariable(name="active", required=True, type="boolean")
            ]
        )
        
        result = parser.parse(template, sample_context)
        assert result == "User is active"
    
    def test_false_conditional(self, parser, sample_context):
        """Test conditional with false condition."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        template = Template(
            metadata=metadata,
            content="<!-- IF inactive -->User is inactive<!-- END IF -->Content after",
            variables=[
                TemplateVariable(name="inactive", required=False, type="boolean", default=False)
            ]
        )
        
        context = TemplateRenderContext(variables={})
        result = parser.parse(template, context)
        assert result == "Content after"
    
    def test_not_conditional(self, parser, sample_context):
        """Test NOT conditional."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        template = Template(
            metadata=metadata,
            content="<!-- IF NOT inactive -->User is active<!-- END IF -->",
            variables=[]
        )
        
        result = parser.parse(template, sample_context)
        assert result == "User is active"
    
    def test_equality_conditional(self, parser, sample_context):
        """Test equality conditional."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        template = Template(
            metadata=metadata,
            content="<!-- IF name == \"John\" -->Hello John!<!-- END IF -->",
            variables=[
                TemplateVariable(name="name", required=True, type="string")
            ]
        )
        
        result = parser.parse(template, sample_context)
        assert result == "Hello John!"


class TestLoops:
    """Test loop processing."""
    
    @pytest.fixture
    def parser(self):
        return TemplateParser()
    
    def test_simple_loop(self, parser, sample_context):
        """Test simple FOR loop."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        template = Template(
            metadata=metadata,
            content="<!-- FOR item IN items -->{{item}}\n<!-- END FOR -->",
            variables=[
                TemplateVariable(name="items", required=True, type="list")
            ]
        )
        
        result = parser.parse(template, sample_context)
        expected = "A\nB\nC\n"
        assert result.strip() == expected.strip()
    
    def test_loop_with_variables(self, parser, sample_context):
        """Test loop with variable substitution inside."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        template = Template(
            metadata=metadata,
            content="User {{name}}:\n<!-- FOR item IN items -->- {{item}}\n<!-- END FOR -->",
            variables=[
                TemplateVariable(name="name", required=True, type="string"),
                TemplateVariable(name="items", required=True, type="list")
            ]
        )
        
        result = parser.parse(template, sample_context)
        expected = "User John:\n- A\n- B\n- C\n"
        assert result.strip() == expected.strip()
    
    def test_missing_loop_variable(self, parser):
        """Test loop with missing collection variable."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        template = Template(
            metadata=metadata,
            content="<!-- FOR item IN missing_items -->{{item}}<!-- END FOR -->",
            variables=[]
        )
        
        context = TemplateRenderContext()
        result = parser.parse(template, context)
        assert result == ""  # Empty result for missing loop variable
    
    def test_invalid_loop_collection(self, parser):
        """Test loop with non-iterable collection."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        template = Template(
            metadata=metadata,
            content="<!-- FOR item IN not_iterable -->{{item}}<!-- END FOR -->",
            variables=[
                TemplateVariable(name="not_iterable", required=True, type="string")
            ]
        )
        
        context = TemplateRenderContext(
            variables={},
            loops={"not_iterable": "string_value"}
        )
        
        with pytest.raises(TemplateParseError, match="not iterable"):
            parser.parse(template, context)


class TestSections:
    """Test section processing."""
    
    @pytest.fixture
    def parser(self):
        return TemplateParser()
    
    def test_included_section(self, parser, sample_context):
        """Test section that should be included."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        template = Template(
            metadata=metadata,
            content="<!-- SECTION: intro -->This is the intro section<!-- END SECTION: intro -->",
            variables=[]
        )
        
        result = parser.parse(template, sample_context)
        assert result == "This is the intro section"
    
    def test_excluded_section(self, parser, sample_context):
        """Test section that should be excluded."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        template = Template(
            metadata=metadata,
            content="Before<!-- SECTION: details -->This is details<!-- END SECTION: details -->After",
            variables=[]
        )
        
        result = parser.parse(template, sample_context)
        assert result == "BeforeAfter"
    
    def test_default_section_inclusion(self, parser):
        """Test that sections are included by default when not specified."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        template = Template(
            metadata=metadata,
            content="<!-- SECTION: unknown -->Default content<!-- END SECTION: unknown -->",
            variables=[]
        )
        
        context = TemplateRenderContext()  # No section flags
        result = parser.parse(template, context)
        assert result == "Default content"


class TestIncludes:
    """Test include processing."""
    
    @pytest.fixture
    def parser(self):
        return TemplateParser()
    
    def test_simple_include(self, parser, sample_context):
        """Test simple include processing."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        template = Template(
            metadata=metadata,
            content="Header\n<!-- INCLUDE header.md -->\nFooter",
            variables=[]
        )
        
        result = parser.parse(template, sample_context)
        assert "<!-- Included: header.md -->" in result
    
    def test_max_include_depth(self, parser):
        """Test maximum include depth protection."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        template = Template(
            metadata=metadata,
            content="<!-- INCLUDE self.md -->",
            variables=[]
        )
        
        context = TemplateRenderContext()
        
        # Mock _load_include to return content that includes itself
        with patch.object(parser, '_load_include', return_value="<!-- INCLUDE self.md -->"):
            with pytest.raises(TemplateIncludeError, match="Maximum include depth"):
                parser.parse(template, context)


class TestComments:
    """Test comment processing."""
    
    @pytest.fixture
    def parser(self):
        return TemplateParser()
    
    def test_comment_removal(self, parser, sample_context):
        """Test that comments are removed."""
        metadata = TemplateMetadata(
            id="test", name="Test", description="Test",
            category=TemplateCategory.MISC, type=TemplateType.FAQ
        )
        template = Template(
            metadata=metadata,
            content="Before<!-- COMMENT: This is a comment -->After",
            variables=[]
        )
        
        result = parser.parse(template, sample_context)
        assert result == "BeforeAfter"


class TestVariableExtraction:
    """Test variable extraction functionality."""
    
    @pytest.fixture
    def parser(self):
        return TemplateParser()
    
    def test_extract_simple_variables(self, parser):
        """Test extracting simple variables."""
        content = "Hello {{name}}, welcome to {{project}}!"
        variables = parser.extract_variables(content)
        assert set(variables) == {"name", "project"}
    
    def test_extract_nested_variables(self, parser):
        """Test extracting nested property variables."""
        content = "User: {{user.name}} ({{user.email}})"
        variables = parser.extract_variables(content)
        assert "user" in variables
    
    def test_extract_conditional_variables(self, parser):
        """Test extracting variables from conditionals."""
        content = "<!-- IF active -->Active user<!-- END IF -->"
        variables = parser.extract_variables(content)
        assert "active" in variables
    
    def test_extract_loop_variables(self, parser):
        """Test extracting variables from loops."""
        content = "<!-- FOR item IN items -->{{item}}<!-- END FOR -->"
        variables = parser.extract_variables(content)
        assert "items" in variables
    
    def test_extract_complex_content(self, parser):
        """Test extracting variables from complex content."""
        content = """
        # {{title}}
        
        By {{author.name}} ({{author.email}})
        
        <!-- IF has_intro -->
        ## Introduction
        {{intro_text}}
        <!-- END IF -->
        
        ## Items
        <!-- FOR item IN item_list -->
        - {{item}}
        <!-- END FOR -->
        """
        variables = parser.extract_variables(content)
        expected = {"title", "author", "has_intro", "intro_text", "item_list"}
        assert set(variables) == expected


class TestSyntaxValidation:
    """Test syntax validation functionality."""
    
    @pytest.fixture
    def parser(self):
        return TemplateParser()
    
    def test_valid_syntax(self, parser):
        """Test validation of correct syntax."""
        content = "Hello {{name}}, welcome to {{project}}!"
        is_valid, errors = parser.validate_syntax(content)
        assert is_valid is True
        assert len(errors) == 0
    
    def test_unbalanced_variables(self, parser):
        """Test detection of unbalanced variable brackets."""
        content = "Hello {{name}, welcome to {{project}}!"
        is_valid, errors = parser.validate_syntax(content)
        assert is_valid is False
        assert any("Unbalanced variable brackets" in error for error in errors)
    
    def test_unclosed_section(self, parser):
        """Test detection of unclosed sections."""
        content = "<!-- SECTION: intro -->Content here"
        is_valid, errors = parser.validate_syntax(content)
        assert is_valid is False
        assert any("Unclosed section: intro" in error for error in errors)
    
    def test_unmatched_section_end(self, parser):
        """Test detection of unmatched section ends."""
        content = "Content here<!-- END SECTION: intro -->"
        is_valid, errors = parser.validate_syntax(content)
        assert is_valid is False
        assert any("Section end without start: intro" in error for error in errors)
    
    def test_unbalanced_conditionals(self, parser):
        """Test detection of unbalanced conditionals."""
        content = "<!-- IF active -->Content here"
        is_valid, errors = parser.validate_syntax(content)
        assert is_valid is False
        assert any("Unbalanced conditionals" in error for error in errors)
    
    def test_unbalanced_loops(self, parser):
        """Test detection of unbalanced loops."""
        content = "<!-- FOR item IN items -->{{item}}"
        is_valid, errors = parser.validate_syntax(content)
        assert is_valid is False
        assert any("Unbalanced loops" in error for error in errors)
    
    def test_complex_valid_syntax(self, parser):
        """Test validation of complex but valid syntax."""
        content = """
        # {{title}}
        
        <!-- IF has_intro -->
        <!-- SECTION: intro -->
        ## Introduction
        {{intro_text}}
        <!-- END SECTION: intro -->
        <!-- END IF -->
        
        <!-- FOR item IN items -->
        - {{item}}
        <!-- END FOR -->
        """
        is_valid, errors = parser.validate_syntax(content)
        assert is_valid is True
        assert len(errors) == 0


if __name__ == "__main__":
    pytest.main([__file__])