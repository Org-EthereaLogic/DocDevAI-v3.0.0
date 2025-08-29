"""
Tests for M004 Document Generator - Template Loader.

Tests the TemplateLoader class and template parsing functionality.
"""

import pytest
import tempfile
import yaml
from pathlib import Path

from devdocai.generator.core.template_loader import (
    TemplateLoader, 
    TemplateMetadata
)


class TestTemplateMetadata:
    """Test TemplateMetadata dataclass."""
    
    def test_default_metadata(self):
        """Test metadata with default values."""
        metadata = TemplateMetadata(
            name="test",
            title="Test Template",
            type="test",
            category="testing"
        )
        
        assert metadata.name == "test"
        assert metadata.title == "Test Template"
        assert metadata.type == "test"
        assert metadata.category == "testing"
        assert metadata.version == "1.0"
        assert metadata.variables == []
        assert metadata.optional_variables == []
        assert metadata.sections == []
        assert metadata.tags == []
        assert metadata.metadata == {}
    
    def test_custom_metadata(self):
        """Test metadata with custom values."""
        metadata = TemplateMetadata(
            name="custom",
            title="Custom Template",
            type="technical",
            category="requirements",
            version="2.0",
            author="Test Author",
            variables=["title", "description"],
            optional_variables=["version"],
            sections=["intro", "body"],
            tags=["test", "sample"],
            metadata={"custom": "value"}
        )
        
        assert metadata.name == "custom"
        assert metadata.author == "Test Author"
        assert metadata.variables == ["title", "description"]
        assert metadata.optional_variables == ["version"]
        assert metadata.sections == ["intro", "body"]
        assert metadata.tags == ["test", "sample"]
        assert metadata.metadata == {"custom": "value"}


class TestTemplateLoader:
    """Test TemplateLoader class."""
    
    @pytest.fixture
    def temp_template_dir(self):
        """Create temporary template directory with test templates."""
        with tempfile.TemporaryDirectory() as temp_dir:
            template_dir = Path(temp_dir)
            
            # Create basic template
            basic_template = template_dir / "basic.j2"
            basic_template.write_text("""---
title: "Basic Template"
type: "test"
category: "basic"
version: "1.0"
variables: ["title", "content"]
optional_variables: ["author"]
sections: ["header", "body"]
tags: ["test", "basic"]
---
# {{ title }}

Author: {{ author | default('Unknown') }}

{{ content }}""")
            
            # Create template without frontmatter
            simple_template = template_dir / "simple.j2"
            simple_template.write_text("# {{ title }}\n\n{{ content }}")
            
            # Create template with invalid YAML
            invalid_template = template_dir / "invalid.j2"
            invalid_template.write_text("""---
title: "Invalid Template
type: test
---
Content here""")
            
            # Create subdirectory template
            subdir = template_dir / "subdir"
            subdir.mkdir()
            sub_template = subdir / "nested.j2"
            sub_template.write_text("""---
title: "Nested Template"
type: "nested"
category: "subdirectory"
---
# {{ title }}""")
            
            yield template_dir
    
    def test_initialization(self, temp_template_dir):
        """Test template loader initialization."""
        loader = TemplateLoader(temp_template_dir)
        
        assert loader.template_dir == temp_template_dir
        assert loader._template_cache == {}
        assert loader._metadata_cache == {}
        assert loader.jinja_env is not None
    
    def test_load_template_with_frontmatter(self, temp_template_dir):
        """Test loading template with YAML frontmatter."""
        loader = TemplateLoader(temp_template_dir)
        
        template = loader.load_template("basic")
        
        assert template is not None
        assert template.name == "basic"
        assert template.title == "Basic Template"
        assert template.type == "test"
        assert template.category == "basic"
        assert template.version == "1.0"
        assert template.variables == ["title", "content"]
        assert template.optional_variables == ["author"]
        assert template.sections == ["header", "body"]
        assert template.tags == ["test", "basic"]
        assert "# {{ title }}" in template.content
        assert template.file_path.name == "basic.j2"
    
    def test_load_template_without_frontmatter(self, temp_template_dir):
        """Test loading template without YAML frontmatter."""
        loader = TemplateLoader(temp_template_dir)
        
        template = loader.load_template("simple")
        
        assert template is not None
        assert template.name == "simple"
        assert template.title == "Simple"  # Generated from name
        assert template.type == "unknown"
        assert template.category == "general"
        assert template.version == "1.0"
        assert template.content == "# {{ title }}\n\n{{ content }}"
    
    def test_load_template_invalid_yaml(self, temp_template_dir):
        """Test loading template with invalid YAML frontmatter."""
        loader = TemplateLoader(temp_template_dir)
        
        template = loader.load_template("invalid")
        
        # Should still load but with empty frontmatter
        assert template is not None
        assert template.name == "invalid"
        assert template.type == "unknown"
        assert "Content here" in template.content
    
    def test_load_template_not_found(self, temp_template_dir):
        """Test loading non-existent template."""
        loader = TemplateLoader(temp_template_dir)
        
        template = loader.load_template("nonexistent")
        
        assert template is None
    
    def test_load_nested_template(self, temp_template_dir):
        """Test loading template from subdirectory."""
        loader = TemplateLoader(temp_template_dir)
        
        template = loader.load_template("subdir/nested")
        
        assert template is not None
        assert template.name == "subdir/nested"
        assert template.title == "Nested Template"
        assert template.type == "nested"
        assert template.category == "subdirectory"
    
    def test_template_caching(self, temp_template_dir):
        """Test that templates are cached after loading."""
        loader = TemplateLoader(temp_template_dir)
        
        # First load
        template1 = loader.load_template("basic")
        assert "basic" in loader._template_cache
        
        # Second load should return cached version
        template2 = loader.load_template("basic")
        assert template1 is template2  # Same object reference
    
    def test_get_template_metadata_cached(self, temp_template_dir):
        """Test getting template metadata (cached after load)."""
        loader = TemplateLoader(temp_template_dir)
        
        # Load template first
        loader.load_template("basic")
        
        # Get metadata should return cached version
        metadata = loader.get_template_metadata("basic")
        
        assert metadata is not None
        assert metadata.name == "basic"
        assert metadata.content is not None  # Content should be included
    
    def test_get_template_metadata_not_cached(self, temp_template_dir):
        """Test getting template metadata when not cached."""
        loader = TemplateLoader(temp_template_dir)
        
        metadata = loader.get_template_metadata("basic")
        
        assert metadata is not None
        assert metadata.name == "basic"
        assert "basic" in loader._metadata_cache
    
    def test_list_templates(self, temp_template_dir):
        """Test listing all available templates."""
        loader = TemplateLoader(temp_template_dir)
        
        templates = loader.list_templates()
        
        # Should find basic, simple, invalid, and nested templates
        assert len(templates) >= 4
        
        template_names = [t.name for t in templates]
        assert "basic" in template_names
        assert "simple" in template_names
        assert "invalid" in template_names
        assert "subdir/nested" in template_names
        
        # Templates should not have content loaded (for efficiency)
        for template in templates:
            assert template.content is None
    
    def test_get_template_categories(self, temp_template_dir):
        """Test getting template categories."""
        loader = TemplateLoader(temp_template_dir)
        
        categories = loader.get_template_categories()
        
        assert "test" in categories
        assert "basic" in categories["test"]
        assert "nested" in categories
        assert "subdirectory" in categories["nested"]
        assert "unknown" in categories
        assert "general" in categories["unknown"]
    
    def test_clear_cache(self, temp_template_dir):
        """Test clearing template cache."""
        loader = TemplateLoader(temp_template_dir)
        
        # Load a template to populate cache
        loader.load_template("basic")
        assert len(loader._template_cache) > 0
        assert len(loader._metadata_cache) > 0
        
        # Clear cache
        loader.clear_cache()
        assert len(loader._template_cache) == 0
        assert len(loader._metadata_cache) == 0
    
    def test_parse_template_file_with_frontmatter(self, temp_template_dir):
        """Test parsing template file content with frontmatter."""
        loader = TemplateLoader(temp_template_dir)
        
        content = """---
title: "Test"
type: "test"
---
# Content here"""
        
        frontmatter, template_content = loader._parse_template_file(content)
        
        assert frontmatter["title"] == "Test"
        assert frontmatter["type"] == "test"
        assert template_content == "# Content here"
    
    def test_parse_template_file_without_frontmatter(self, temp_template_dir):
        """Test parsing template file content without frontmatter."""
        loader = TemplateLoader(temp_template_dir)
        
        content = "# Just content here"
        
        frontmatter, template_content = loader._parse_template_file(content)
        
        assert frontmatter == {}
        assert template_content == "# Just content here"
    
    def test_extract_template_variables(self, temp_template_dir):
        """Test extracting variables from template content."""
        loader = TemplateLoader(temp_template_dir)
        
        content = """
# {{ title }}
Author: {{ author }}
{% for item in items %}
- {{ item.name }}
{% endfor %}
"""
        
        variables = loader._extract_template_variables(content)
        
        # Should find title, author, and items
        assert "title" in variables["required"]
        assert "author" in variables["required"]
        assert "items" in variables["required"]
    
    def test_custom_filters_registration(self, temp_template_dir):
        """Test that custom filters are registered."""
        loader = TemplateLoader(temp_template_dir)
        
        # Check that custom filters are available
        assert "markdown_table" in loader.jinja_env.filters
        assert "format_date" in loader.jinja_env.filters
        assert "slugify" in loader.jinja_env.filters
    
    def test_markdown_table_filter(self, temp_template_dir):
        """Test markdown_table custom filter."""
        loader = TemplateLoader(temp_template_dir)
        
        data = [
            {"name": "John", "age": 30},
            {"name": "Jane", "age": 25}
        ]
        
        template_content = "{{ data | markdown_table }}"
        template = loader.jinja_env.from_string(template_content)
        result = template.render(data=data)
        
        assert "| name | age |" in result
        assert "| John | 30 |" in result
        assert "| Jane | 25 |" in result
        assert "| --- | --- |" in result
    
    def test_slugify_filter(self, temp_template_dir):
        """Test slugify custom filter."""
        loader = TemplateLoader(temp_template_dir)
        
        template_content = "{{ text | slugify }}"
        template = loader.jinja_env.from_string(template_content)
        result = template.render(text="Hello World! Test.")
        
        assert result == "hello-world-test"
    
    def test_format_date_filter(self, temp_template_dir):
        """Test format_date custom filter."""
        loader = TemplateLoader(temp_template_dir)
        
        template_content = "{{ date | format_date('%Y-%m-%d') }}"
        template = loader.jinja_env.from_string(template_content)
        result = template.render(date="2024-01-15T10:30:00")
        
        assert "2024-01-15" in result
    
    def test_template_loading_error_handling(self, temp_template_dir):
        """Test error handling during template loading."""
        loader = TemplateLoader(temp_template_dir)
        
        # Create a template file with permission issues (simulate)
        # This test might be platform-specific
        with pytest.raises(Exception):
            # Try to load from a non-existent directory
            bad_loader = TemplateLoader(Path("/nonexistent/path"))
            bad_loader.load_template("test")