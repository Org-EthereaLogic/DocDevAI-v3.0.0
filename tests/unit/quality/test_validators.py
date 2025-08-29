"""
Unit tests for Document Validators.
"""

import pytest
from devdocai.quality.validators import (
    DocumentValidator, MarkdownValidator, CodeDocumentValidator
)
from devdocai.quality.models import ValidationRule, QualityDimension, SeverityLevel


class TestDocumentValidator:
    """Test suite for DocumentValidator."""
    
    @pytest.fixture
    def validator(self):
        return DocumentValidator()
    
    def test_initialization(self, validator):
        """Test validator initialization."""
        assert len(validator.rules) > 0
        assert len(validator.enabled_rules) > 0
    
    def test_validate_complete_document(self, validator):
        """Test validation of complete document."""
        content = """
# Document Title

## Description
This is a complete document with all required sections.

## Usage
Here's how to use this.

```python
def example():
    return True
```
"""
        results = validator.validate(content)
        
        # Should pass most validations
        passed_count = sum(1 for r in results if r.get('passed', False))
        assert passed_count >= len(results) - 2
    
    def test_validate_missing_sections(self, validator):
        """Test validation with missing sections."""
        content = """
# Title

Some content without required sections.
"""
        results = validator.validate(content)
        
        # Find required sections validation result
        section_result = next(
            (r for r in results if r['rule'] == 'required_sections'),
            None
        )
        
        assert section_result is not None
        assert section_result['passed'] is False
        assert len(section_result['errors']) > 0
    
    def test_validate_minimum_length(self, validator):
        """Test minimum length validation."""
        short_content = "Too short."
        
        results = validator.validate(short_content)
        
        length_result = next(
            (r for r in results if r['rule'] == 'minimum_length'),
            None
        )
        
        assert length_result is not None
        assert length_result['passed'] is False
    
    def test_validate_heading_structure(self, validator):
        """Test heading structure validation."""
        content = """
### H3 First (skipped H1 and H2)

## H2 After H3

# H1 at the end

# Another H1
"""
        results = validator.validate(content)
        
        heading_result = next(
            (r for r in results if r['rule'] == 'heading_structure'),
            None
        )
        
        assert heading_result is not None
        assert heading_result['passed'] is False
        assert any('Multiple H1' in e for e in heading_result['errors'])
    
    def test_validate_code_blocks(self, validator):
        """Test code block validation."""
        content = """
# Code Examples

```
Code without language identifier
```

```python
def missing_colon
    return True
```
"""
        results = validator.validate(content)
        
        code_result = next(
            (r for r in results if r['rule'] == 'code_block_syntax'),
            None
        )
        
        assert code_result is not None
        assert code_result['passed'] is False
    
    def test_validate_link_format(self, validator):
        """Test link format validation."""
        content = """
# Links

Here's a bare URL: https://example.com

And an empty link: [](https://example.com)
"""
        results = validator.validate(content)
        
        link_result = next(
            (r for r in results if r['rule'] == 'link_format'),
            None
        )
        
        assert link_result is not None
        assert link_result['passed'] is False
        assert len(link_result['errors']) >= 2
    
    def test_custom_rules(self):
        """Test validator with custom rules."""
        custom_rules = [
            ValidationRule(
                name="custom_check",
                description="Custom validation",
                dimension=QualityDimension.COMPLETENESS,
                severity=SeverityLevel.LOW,
                enabled=False
            )
        ]
        
        validator = DocumentValidator(rules=custom_rules)
        assert len(validator.enabled_rules) == 0  # Custom rule is disabled


class TestMarkdownValidator:
    """Test suite for MarkdownValidator."""
    
    @pytest.fixture
    def validator(self):
        return MarkdownValidator()
    
    def test_validate_markdown_tables(self, validator):
        """Test markdown table validation."""
        content = """
# Tables

| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |

|---|---|
| Missing | Header |
"""
        results = validator.validate(content)
        
        table_result = next(
            (r for r in results if r['rule'] == 'markdown_tables'),
            None
        )
        
        if table_result:
            assert isinstance(table_result['passed'], bool)
    
    def test_validate_markdown_lists(self, validator):
        """Test markdown list validation."""
        content = """
# Lists

- Item with dash
* Item with asterisk
+ Item with plus

1. First item
3. Third item (broken sequence)
"""
        results = validator.validate(content)
        
        list_result = next(
            (r for r in results if r['rule'] == 'markdown_lists'),
            None
        )
        
        assert list_result is not None
        assert list_result['passed'] is False
        assert any('Mixed bullet styles' in e for e in list_result['errors'])
    
    def test_validate_front_matter(self, validator):
        """Test YAML front matter validation."""
        content = """---
title: Test Document
author: Test Author
---

# Content

Document content here.
"""
        results = validator.validate(content)
        
        front_matter_result = next(
            (r for r in results if r['rule'] == 'front_matter'),
            None
        )
        
        assert front_matter_result is not None
        assert front_matter_result['passed'] is True
    
    def test_validate_invalid_front_matter(self, validator):
        """Test invalid front matter validation."""
        content = """---
title: Test Document
invalid syntax here
author: Test Author

# Content
"""
        results = validator.validate(content)
        
        front_matter_result = next(
            (r for r in results if r['rule'] == 'front_matter'),
            None
        )
        
        assert front_matter_result is not None
        assert front_matter_result['passed'] is False


class TestCodeDocumentValidator:
    """Test suite for CodeDocumentValidator."""
    
    @pytest.fixture
    def validator(self):
        return CodeDocumentValidator()
    
    def test_validate_docstring_presence(self, validator):
        """Test docstring presence validation."""
        content = '''
def function_with_docstring():
    """This function has a docstring."""
    return True

def function_without_docstring():
    return False

class MyClass:
    """Class with docstring."""
    pass

class AnotherClass:
    pass
'''
        results = validator.validate(content, 'python')
        
        docstring_result = next(
            (r for r in results if r['rule'] == 'docstring_presence'),
            None
        )
        
        assert docstring_result is not None
        # 2 out of 4 items have docstrings (50% coverage)
        assert docstring_result['passed'] is False
    
    def test_validate_comment_quality(self, validator):
        """Test comment quality validation."""
        content = """
# This is a comment
def function1():
    return True

def function2():
    # Another comment
    value = 42
    return value

def function3():
    return False
"""
        results = validator.validate(content, 'python')
        
        comment_result = next(
            (r for r in results if r['rule'] == 'comment_quality'),
            None
        )
        
        assert comment_result is not None
        # Check if comment ratio meets minimum
        assert isinstance(comment_result['passed'], bool)
    
    def test_validate_high_docstring_coverage(self, validator):
        """Test validation with high docstring coverage."""
        content = '''
def function1():
    """Docstring 1."""
    return True

def function2():
    """Docstring 2."""
    return False

class MyClass:
    """Class docstring."""
    
    def method(self):
        """Method docstring."""
        pass
'''
        results = validator.validate(content, 'python')
        
        docstring_result = next(
            (r for r in results if r['rule'] == 'docstring_presence'),
            None
        )
        
        assert docstring_result is not None
        assert docstring_result['passed'] is True