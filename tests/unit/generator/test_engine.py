"""
Tests for M004 Document Generator - Core Engine.

Tests the DocumentGenerator class and related functionality.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock

from devdocai.generator.core.engine import (
    DocumentGenerator, 
    GenerationConfig, 
    GenerationResult
)
from devdocai.generator.core.template_loader import TemplateMetadata
from devdocai.generator.utils.validators import ValidationError
from devdocai.common.errors import DevDocAIError


class TestGenerationConfig:
    """Test GenerationConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = GenerationConfig()
        
        assert config.output_format == "markdown"
        assert config.save_to_storage is True
        assert config.include_metadata is True
        assert config.validate_inputs is True
        assert config.project_name is None
        assert config.author is None
        assert config.version == "1.0"
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = GenerationConfig(
            output_format="html",
            save_to_storage=False,
            project_name="Test Project",
            author="Test Author",
            version="2.0"
        )
        
        assert config.output_format == "html"
        assert config.save_to_storage is False
        assert config.project_name == "Test Project"
        assert config.author == "Test Author"
        assert config.version == "2.0"
    
    def test_invalid_output_format(self):
        """Test validation of output format."""
        with pytest.raises(ValidationError):
            GenerationConfig(output_format="invalid")


class TestGenerationResult:
    """Test GenerationResult dataclass."""
    
    def test_success_result(self):
        """Test successful generation result."""
        result = GenerationResult(
            success=True,
            document_id="test-123",
            content="# Test Document",
            format="markdown",
            generation_time=0.123,
            template_name="test"
        )
        
        assert result.success is True
        assert result.document_id == "test-123"
        assert result.content == "# Test Document"
        assert result.format == "markdown"
        assert result.generation_time == 0.123
        assert result.template_name == "test"
        assert result.error_message is None
        assert result.warnings == []  # Default empty list
    
    def test_failure_result(self):
        """Test failed generation result."""
        result = GenerationResult(
            success=False,
            error_message="Template not found",
            template_name="missing"
        )
        
        assert result.success is False
        assert result.error_message == "Template not found"
        assert result.template_name == "missing"
        assert result.document_id is None
        assert result.content is None


class TestDocumentGenerator:
    """Test DocumentGenerator class."""
    
    @pytest.fixture
    def temp_template_dir(self):
        """Create temporary template directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            template_dir = Path(temp_dir)
            
            # Create a simple test template
            test_template = template_dir / "test.j2"
            test_template.write_text("""---
title: "Test Template"
type: "test"
category: "testing"
variables: ["title", "content"]
---
# {{ title }}

{{ content }}""")
            
            yield template_dir
    
    @pytest.fixture
    def mock_config_manager(self):
        """Create mock configuration manager."""
        mock = Mock()
        mock.get_config.return_value = {"test": "value"}
        return mock
    
    @pytest.fixture
    def mock_storage_system(self):
        """Create mock storage system."""
        mock = Mock()
        mock.create_document.return_value = "test-doc-123"
        return mock
    
    def test_initialization_with_defaults(self):
        """Test generator initialization with default values."""
        generator = DocumentGenerator()
        
        assert generator.config_manager is not None
        assert generator.storage_system is not None
        assert generator.template_loader is not None
        assert generator.content_processor is not None
        assert generator.input_validator is not None
        assert len(generator.formatters) == 2  # markdown and html
    
    def test_initialization_with_custom_params(self, temp_template_dir, mock_config_manager, mock_storage_system):
        """Test generator initialization with custom parameters."""
        generator = DocumentGenerator(
            config_manager=mock_config_manager,
            storage_system=mock_storage_system,
            template_dir=temp_template_dir
        )
        
        assert generator.config_manager == mock_config_manager
        assert generator.storage_system == mock_storage_system
        assert generator.template_dir == temp_template_dir
    
    def test_generate_document_success(self, temp_template_dir, mock_config_manager, mock_storage_system):
        """Test successful document generation."""
        generator = DocumentGenerator(
            config_manager=mock_config_manager,
            storage_system=mock_storage_system,
            template_dir=temp_template_dir
        )
        
        inputs = {
            "title": "Test Document",
            "content": "This is test content."
        }
        
        config = GenerationConfig(save_to_storage=True)
        
        result = generator.generate_document("test", inputs, config)
        
        assert result.success is True
        assert result.document_id == "test-doc-123"
        assert "# Test Document" in result.content
        assert "This is test content." in result.content
        assert result.format == "markdown"
        assert result.generation_time > 0
        assert result.template_name == "test"
        
        # Verify storage was called
        mock_storage_system.create_document.assert_called_once()
    
    def test_generate_document_without_storage(self, temp_template_dir, mock_config_manager, mock_storage_system):
        """Test document generation without storage."""
        generator = DocumentGenerator(
            config_manager=mock_config_manager,
            storage_system=mock_storage_system,
            template_dir=temp_template_dir
        )
        
        inputs = {
            "title": "Test Document",
            "content": "This is test content."
        }
        
        config = GenerationConfig(save_to_storage=False)
        
        result = generator.generate_document("test", inputs, config)
        
        assert result.success is True
        assert result.document_id is None  # No storage, no ID
        assert "# Test Document" in result.content
        
        # Verify storage was not called
        mock_storage_system.create_document.assert_not_called()
    
    def test_generate_document_template_not_found(self, temp_template_dir, mock_config_manager, mock_storage_system):
        """Test generation with non-existent template."""
        generator = DocumentGenerator(
            config_manager=mock_config_manager,
            storage_system=mock_storage_system,
            template_dir=temp_template_dir
        )
        
        inputs = {"title": "Test"}
        
        result = generator.generate_document("nonexistent", inputs)
        
        assert result.success is False
        assert result.error_message is not None
        assert "not found" in result.error_message.lower()
        assert result.template_name == "nonexistent"
    
    def test_generate_document_validation_error(self, temp_template_dir, mock_config_manager, mock_storage_system):
        """Test generation with validation errors."""
        generator = DocumentGenerator(
            config_manager=mock_config_manager,
            storage_system=mock_storage_system,
            template_dir=temp_template_dir
        )
        
        # Missing required variable 'content'
        inputs = {"title": "Test Document"}
        
        config = GenerationConfig(validate_inputs=True)
        
        result = generator.generate_document("test", inputs, config)
        
        assert result.success is False
        assert result.error_message is not None
        assert "validation" in result.error_message.lower()
    
    def test_generate_document_unsupported_format(self, temp_template_dir, mock_config_manager, mock_storage_system):
        """Test generation with unsupported output format."""
        generator = DocumentGenerator(
            config_manager=mock_config_manager,
            storage_system=mock_storage_system,
            template_dir=temp_template_dir
        )
        
        inputs = {"title": "Test", "content": "Content"}
        
        # Manually create config to bypass validation
        config = GenerationConfig()
        config.output_format = "pdf"  # Not supported yet
        
        result = generator.generate_document("test", inputs, config)
        
        assert result.success is False
        assert "unsupported" in result.error_message.lower()
    
    def test_generation_timing(self, temp_template_dir, mock_config_manager, mock_storage_system):
        """Test that generation timing is recorded correctly."""
        import time
        # Test actual timing instead of mocking (more reliable)
        
        generator = DocumentGenerator(
            config_manager=mock_config_manager,
            storage_system=mock_storage_system,
            template_dir=temp_template_dir
        )
        
        inputs = {"title": "Test", "content": "Content"}
        
        result = generator.generate_document("test", inputs)
        
        assert result.success is True
        assert result.generation_time is not None
        assert result.generation_time > 0  # Should have taken some time
        assert result.generation_time < 1.0  # Should be reasonably fast
    
    def test_list_templates(self, temp_template_dir):
        """Test listing available templates."""
        generator = DocumentGenerator(template_dir=temp_template_dir)
        
        templates = generator.list_templates()
        
        assert len(templates) == 1
        assert templates[0].name == "test"
        assert templates[0].type == "test"
        assert templates[0].category == "testing"
    
    def test_list_templates_with_category_filter(self, temp_template_dir):
        """Test listing templates with category filter."""
        generator = DocumentGenerator(template_dir=temp_template_dir)
        
        # Should find the test template
        templates = generator.list_templates(category="testing")
        assert len(templates) == 1
        
        # Should find nothing for non-existent category
        templates = generator.list_templates(category="nonexistent")
        assert len(templates) == 0
    
    def test_get_template_info(self, temp_template_dir):
        """Test getting template information."""
        generator = DocumentGenerator(template_dir=temp_template_dir)
        
        template = generator.get_template_info("test")
        
        assert template is not None
        assert template.name == "test"
        assert template.title == "Test Template"
        assert template.variables == ["title", "content"]
    
    def test_get_template_info_not_found(self, temp_template_dir):
        """Test getting info for non-existent template."""
        generator = DocumentGenerator(template_dir=temp_template_dir)
        
        template = generator.get_template_info("nonexistent")
        
        assert template is None
    
    def test_validate_template_inputs_success(self, temp_template_dir):
        """Test successful input validation."""
        generator = DocumentGenerator(template_dir=temp_template_dir)
        
        inputs = {"title": "Test", "content": "Content"}
        
        errors = generator.validate_template_inputs("test", inputs)
        
        assert errors == []
    
    def test_validate_template_inputs_errors(self, temp_template_dir):
        """Test input validation with errors."""
        generator = DocumentGenerator(template_dir=temp_template_dir)
        
        inputs = {"title": "Test"}  # Missing 'content'
        
        errors = generator.validate_template_inputs("test", inputs)
        
        assert len(errors) > 0
        assert any("content" in error for error in errors)
    
    def test_validate_template_inputs_template_not_found(self, temp_template_dir):
        """Test validation with non-existent template."""
        generator = DocumentGenerator(template_dir=temp_template_dir)
        
        inputs = {"title": "Test"}
        
        errors = generator.validate_template_inputs("nonexistent", inputs)
        
        assert len(errors) > 0
        assert any("not found" in error for error in errors)
    
    def test_save_document_integration(self, temp_template_dir, mock_storage_system):
        """Test document saving integration."""
        generator = DocumentGenerator(
            storage_system=mock_storage_system,
            template_dir=temp_template_dir
        )
        
        # Create template metadata
        template_metadata = TemplateMetadata(
            name="test",
            title="Test Template",
            type="test",
            category="testing",
            version="1.0",
            variables=["title", "content"]
        )
        
        config = GenerationConfig(
            output_format="markdown",
            project_name="Test Project",
            author="Test Author"
        )
        
        inputs = {"title": "Test", "content": "Content"}
        
        # Call the private method directly for testing
        document_id = generator._save_document(
            "# Test Content",
            template_metadata,
            config,
            inputs
        )
        
        assert document_id == "test-doc-123"
        
        # Verify storage was called with correct parameters
        mock_storage_system.create_document.assert_called_once()
        call_args = mock_storage_system.create_document.call_args
        
        assert "Test Template" in call_args.kwargs['title']
        assert call_args.kwargs['content'] == "# Test Content"
        assert call_args.kwargs['document_type'] == "generated_markdown"
        assert "template_name" in call_args.kwargs['metadata']