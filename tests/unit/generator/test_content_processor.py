"""
Tests for M004 Document Generator - Content Processor.

Tests the ContentProcessor class and template rendering functionality.
"""

import pytest
from datetime import datetime

from devdocai.generator.core.content_processor import ContentProcessor
from devdocai.common.errors import DevDocAIError


class TestContentProcessor:
    """Test ContentProcessor class."""
    
    @pytest.fixture
    def processor(self):
        """Create ContentProcessor instance."""
        return ContentProcessor()
    
    def test_initialization(self, processor):
        """Test processor initialization."""
        assert processor.jinja_env is not None
        assert processor.jinja_env.trim_blocks is True
        assert processor.jinja_env.lstrip_blocks is True
    
    def test_process_simple_content(self, processor):
        """Test processing simple template content."""
        template_content = "# {{ title }}\n\n{{ description }}"
        inputs = {
            "title": "Test Document",
            "description": "This is a test document."
        }
        
        result = processor.process_content(template_content, inputs)
        
        assert "# Test Document" in result
        assert "This is a test document." in result
    
    def test_process_content_with_loops(self, processor):
        """Test processing content with Jinja2 loops."""
        template_content = """# {{ title }}

{% for item in items %}
- {{ item }}
{% endfor %}"""
        
        inputs = {
            "title": "List Document",
            "items": ["Item 1", "Item 2", "Item 3"]
        }
        
        result = processor.process_content(template_content, inputs)
        
        assert "# List Document" in result
        assert "- Item 1" in result
        assert "- Item 2" in result
        assert "- Item 3" in result
    
    def test_process_content_with_conditionals(self, processor):
        """Test processing content with conditionals."""
        template_content = """# {{ title }}

{% if show_description %}
Description: {{ description }}
{% endif %}

{% if items %}
Items:
{% for item in items %}
- {{ item }}
{% endfor %}
{% else %}
No items available.
{% endif %}"""
        
        inputs = {
            "title": "Conditional Document",
            "show_description": True,
            "description": "Test description",
            "items": []
        }
        
        result = processor.process_content(template_content, inputs)
        
        assert "# Conditional Document" in result
        assert "Description: Test description" in result
        assert "No items available." in result
    
    def test_process_content_with_filters(self, processor):
        """Test processing content with custom filters."""
        template_content = """# {{ title | capitalize_first }}

Date: {{ date | format_date('%Y-%m-%d') }}
Slug: {{ title | slugify }}"""
        
        inputs = {
            "title": "test document title",
            "date": "2024-01-15T10:30:00"
        }
        
        result = processor.process_content(template_content, inputs)
        
        assert "Test document title" in result
        assert "2024-01-15" in result
        assert "test-document-title" in result
    
    def test_process_content_with_default_values(self, processor):
        """Test processing content with Jinja2 default values."""
        template_content = """# {{ title }}

Author: {{ author | default('Anonymous') }}
Version: {{ version | default('1.0') }}"""
        
        inputs = {
            "title": "Test Document"
            # author and version not provided
        }
        
        result = processor.process_content(template_content, inputs)
        
        assert "# Test Document" in result
        assert "Author: Anonymous" in result
        assert "Version: 1.0" in result
    
    def test_process_content_with_undefined_variable(self, processor):
        """Test processing content with undefined variable (strict mode)."""
        template_content = "# {{ title }}\n\n{{ undefined_var }}"
        inputs = {"title": "Test"}
        
        with pytest.raises(DevDocAIError) as excinfo:
            processor.process_content(template_content, inputs)
        
        assert "not defined" in str(excinfo.value).lower()
    
    def test_process_content_with_required_variables_validation(self, processor):
        """Test processing with required variables validation."""
        template_content = "# {{ title }}\n\n{{ content }}"
        inputs = {"title": "Test"}  # Missing 'content'
        required_variables = ["title", "content"]
        
        with pytest.raises(DevDocAIError) as excinfo:
            processor.process_content(template_content, inputs, required_variables)
        
        assert "missing required variables" in str(excinfo.value).lower()
        assert "content" in str(excinfo.value)
    
    def test_process_content_adds_default_context(self, processor):
        """Test that default context values are added."""
        template_content = """Generated: {{ generated_date }}
Time: {{ generated_time }}
Version: {{ version }}"""
        
        inputs = {}
        
        result = processor.process_content(template_content, inputs)
        
        # Should have current date/time
        current_date = datetime.now().strftime('%Y-%m-%d')
        assert current_date in result
        assert "Version: 1.0" in result
    
    def test_process_content_context_override(self, processor):
        """Test that user inputs override default context."""
        template_content = "Version: {{ version }}"
        inputs = {"version": "2.0"}
        
        result = processor.process_content(template_content, inputs)
        
        assert "Version: 2.0" in result  # User value, not default
    
    def test_validate_template_syntax_valid(self, processor):
        """Test validating valid template syntax."""
        template_content = """# {{ title }}
{% for item in items %}
- {{ item }}
{% endfor %}"""
        
        errors = processor.validate_template_syntax(template_content)
        
        assert errors == []
    
    def test_validate_template_syntax_invalid(self, processor):
        """Test validating invalid template syntax."""
        template_content = "# {{ title }\n{% for item in items %}\n- {{ item }}\n{{% endfor %}"
        
        errors = processor.validate_template_syntax(template_content)
        
        assert len(errors) > 0
        assert any("syntax error" in error.lower() for error in errors)
    
    def test_extract_variables(self, processor):
        """Test extracting variables from template."""
        template_content = """# {{ title }}
Author: {{ author }}
{% for item in items %}
- {{ item.name }}
{% endfor %}"""
        
        variables = processor.extract_variables(template_content)
        
        assert "title" in variables
        assert "author" in variables
        assert "items" in variables
    
    def test_post_process_content_cleanup(self, processor):
        """Test post-processing content cleanup."""
        messy_content = """# Title


Some content here.



More content.


End."""
        
        cleaned = processor._post_process_content(messy_content)
        
        # Should remove excessive blank lines
        assert "\n\n\n" not in cleaned
        assert cleaned.endswith("\n")  # Should end with single newline
    
    def test_custom_filters_registration(self, processor):
        """Test that custom filters are registered."""
        filters = processor.jinja_env.filters
        
        expected_filters = [
            'markdown_link',
            'markdown_code',
            'markdown_table',
            'format_list',
            'format_date',
            'slugify',
            'truncate_words',
            'capitalize_first'
        ]
        
        for filter_name in expected_filters:
            assert filter_name in filters
    
    def test_markdown_link_filter(self, processor):
        """Test markdown_link custom filter."""
        template_content = "{{ text | markdown_link(url) }}"
        inputs = {"text": "Example", "url": "https://example.com"}
        
        result = processor.process_content(template_content, inputs)
        
        assert result.strip() == "[Example](https://example.com)"
    
    def test_markdown_code_filter(self, processor):
        """Test markdown_code custom filter."""
        template_content = "{{ code | markdown_code('python') }}"
        inputs = {"code": "print('hello')"}
        
        result = processor.process_content(template_content, inputs)
        
        assert "```python" in result
        # The content may be HTML-escaped, so check for the escaped version
        assert ("print('hello')" in result or "print(&#39;hello&#39;)" in result)
        assert "```" in result
    
    def test_format_list_filter(self, processor):
        """Test format_list custom filter."""
        template_content = "{{ items | format_list('numbered') }}"
        inputs = {"items": ["First", "Second", "Third"]}
        
        result = processor.process_content(template_content, inputs)
        
        assert "1. First" in result
        assert "2. Second" in result
        assert "3. Third" in result
    
    def test_format_list_bullet(self, processor):
        """Test format_list filter with bullet points."""
        template_content = "{{ items | format_list('bullet') }}"
        inputs = {"items": ["First", "Second", "Third"]}
        
        result = processor.process_content(template_content, inputs)
        
        assert "- First" in result
        assert "- Second" in result
        assert "- Third" in result
    
    def test_truncate_words_filter(self, processor):
        """Test truncate_words custom filter."""
        template_content = "{{ text | truncate_words(3) }}"
        inputs = {"text": "This is a very long sentence that should be truncated"}
        
        result = processor.process_content(template_content, inputs)
        
        assert result.strip() == "This is a..."
    
    def test_capitalize_first_filter(self, processor):
        """Test capitalize_first custom filter."""
        template_content = "{{ text | capitalize_first }}"
        inputs = {"text": "hello world. this is a test."}
        
        result = processor.process_content(template_content, inputs)
        
        assert result.strip() == "Hello world. This is a test."
    
    def test_global_functions_registration(self, processor):
        """Test that global functions are registered."""
        globals_dict = processor.jinja_env.globals
        
        expected_globals = [
            'range',
            'enumerate',
            'len',
            'max',
            'min',
            'sum'
        ]
        
        for global_name in expected_globals:
            assert global_name in globals_dict
    
    def test_global_functions_usage(self, processor):
        """Test using global functions in templates."""
        template_content = """Items: {{ len(items) }}
{% for i in range(3) %}
Item {{ i }}: {{ items[i] if i < len(items) else 'N/A' }}
{% endfor %}"""
        
        inputs = {"items": ["A", "B"]}
        
        result = processor.process_content(template_content, inputs)
        
        assert "Items: 2" in result
        assert "Item 0: A" in result
        assert "Item 1: B" in result
        assert "Item 2: N/A" in result
    
    def test_markdown_table_filter_detailed(self, processor):
        """Test markdown_table filter with detailed data."""
        template_content = "{{ data | markdown_table }}"
        
        data = [
            {"name": "John Doe", "role": "Developer", "years": 5},
            {"name": "Jane Smith", "role": "Designer", "years": 3}
        ]
        
        inputs = {"data": data}
        
        result = processor.process_content(template_content, inputs)
        
        lines = result.strip().split('\n')
        
        # Should have header, separator, and data rows
        assert len(lines) == 4
        assert "| name | role | years |" in lines[0]
        assert "| --- | --- | --- |" in lines[1]
        assert "| John Doe | Developer | 5 |" in lines[2]
        assert "| Jane Smith | Designer | 3 |" in lines[3]
    
    def test_template_error_handling(self, processor):
        """Test error handling for template processing errors."""
        # Invalid Jinja2 syntax
        template_content = "{{ title | invalid_filter }}"
        inputs = {"title": "Test"}
        
        with pytest.raises(DevDocAIError) as excinfo:
            processor.process_content(template_content, inputs)
        
        assert "template processing error" in str(excinfo.value).lower()
    
    def test_empty_inputs_handling(self, processor):
        """Test handling of empty inputs."""
        template_content = "Title: {{ title | default('Untitled') }}"
        inputs = {}
        
        result = processor.process_content(template_content, inputs)
        
        assert "Title: Untitled" in result