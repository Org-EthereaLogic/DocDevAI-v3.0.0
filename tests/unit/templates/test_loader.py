"""
Unit tests for Template Loader.

Tests template loading from files, directories, and various formats.
"""

import pytest
import json
import yaml
from pathlib import Path
import tempfile
import shutil

from devdocai.templates.loader import TemplateLoader
from devdocai.templates.models import (
    Template,
    TemplateMetadata,
    TemplateVariable,
    TemplateSection,
    TemplateCategory,
    TemplateType
)
from devdocai.templates.exceptions import TemplateStorageError, TemplateParseError


class TestTemplateLoader:
    """Test suite for TemplateLoader class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def loader(self, temp_dir):
        """Create TemplateLoader instance."""
        return TemplateLoader(base_path=temp_dir)
    
    @pytest.fixture
    def json_template_data(self):
        """Sample JSON template data."""
        return {
            "id": "test-template",
            "name": "Test Template",
            "description": "A test template",
            "category": "testing",
            "type": "test_plan",
            "version": "1.0.0",
            "author": "Test Author",
            "tags": ["test", "sample"],
            "template": "# {{PROJECT_NAME}}\n\nThis is a test template.",
            "variables": [
                {
                    "name": "PROJECT_NAME",
                    "description": "Project name",
                    "required": True,
                    "type": "text",
                    "default": "My Project"
                }
            ],
            "sections": [
                {
                    "id": "intro",
                    "title": "Introduction",
                    "required": True,
                    "order": 1
                }
            ]
        }
    
    @pytest.fixture
    def yaml_template_data(self):
        """Sample YAML template data."""
        return {
            "metadata": {
                "id": "yaml-template",
                "name": "YAML Template",
                "description": "A YAML template",
                "category": "documentation",
                "type": "readme"
            },
            "content": "# README\n\n{{DESCRIPTION}}",
            "variables": [
                {
                    "name": "DESCRIPTION",
                    "description": "Project description",
                    "required": True,
                    "type": "text"
                }
            ]
        }
    
    def test_loader_initialization(self, temp_dir):
        """Test loader initialization."""
        loader = TemplateLoader(base_path=temp_dir)
        assert loader.base_path == temp_dir
        assert len(loader._template_cache) == 0
    
    def test_load_json_template(self, loader, temp_dir, json_template_data):
        """Test loading template from JSON file."""
        # Create JSON template file
        json_path = temp_dir / "test_template.json"
        with open(json_path, 'w') as f:
            json.dump(json_template_data, f)
        
        # Load template
        template = loader.load_from_file(json_path)
        
        assert template is not None
        assert template.metadata.id == "test-template"
        assert template.metadata.name == "Test Template"
        assert template.content == "# {{PROJECT_NAME}}\n\nThis is a test template."
        assert len(template.variables) == 1
        assert template.variables[0].name == "PROJECT_NAME"
        assert len(template.sections) == 1
    
    def test_load_yaml_template(self, loader, temp_dir, yaml_template_data):
        """Test loading template from YAML file."""
        # Create YAML template file
        yaml_path = temp_dir / "test_template.yaml"
        with open(yaml_path, 'w') as f:
            yaml.dump(yaml_template_data, f)
        
        # Load template
        template = loader.load_from_file(yaml_path)
        
        assert template is not None
        assert template.metadata.id == "yaml-template"
        assert template.metadata.name == "YAML Template"
        assert template.content == "# README\n\n{{DESCRIPTION}}"
        assert len(template.variables) == 1
    
    def test_load_text_template_with_frontmatter(self, loader, temp_dir):
        """Test loading text template with frontmatter."""
        # Create text template with frontmatter
        text_content = """---
id: text-template
name: Text Template
description: A text template with frontmatter
category: documentation
type: readme
variables:
  - name: TITLE
    description: Document title
    required: true
---

# {{TITLE}}

This is the template content.
"""
        
        text_path = temp_dir / "test_template.md"
        with open(text_path, 'w') as f:
            f.write(text_content)
        
        # Load template
        template = loader.load_from_file(text_path)
        
        assert template is not None
        assert template.metadata.id == "text-template"
        assert template.metadata.name == "Text Template"
        assert "{{TITLE}}" in template.content
        assert len(template.variables) == 1
    
    def test_load_text_template_without_frontmatter(self, loader, temp_dir):
        """Test loading plain text template without frontmatter."""
        # Create plain text template
        text_content = "# Simple Template\n\nThis is a simple template."
        
        text_path = temp_dir / "simple_template.md"
        with open(text_path, 'w') as f:
            f.write(text_content)
        
        # Load template
        template = loader.load_from_file(text_path)
        
        assert template is not None
        assert template.metadata.id == "simple_template"  # Inferred from filename
        assert template.content == text_content
    
    def test_load_nonexistent_file(self, loader, temp_dir):
        """Test loading non-existent file raises error."""
        nonexistent_path = temp_dir / "nonexistent.json"
        
        with pytest.raises(TemplateStorageError) as exc_info:
            loader.load_from_file(nonexistent_path)
        
        assert "File not found" in str(exc_info.value)
    
    def test_load_unsupported_format(self, loader, temp_dir):
        """Test loading unsupported file format raises error."""
        # Create file with unsupported extension
        unsupported_path = temp_dir / "template.xyz"
        with open(unsupported_path, 'w') as f:
            f.write("content")
        
        with pytest.raises(TemplateStorageError) as exc_info:
            loader.load_from_file(unsupported_path)
        
        assert "Unsupported format" in str(exc_info.value)
    
    def test_template_caching(self, loader, temp_dir, json_template_data):
        """Test template caching mechanism."""
        # Create template file
        json_path = temp_dir / "cached_template.json"
        with open(json_path, 'w') as f:
            json.dump(json_template_data, f)
        
        # Load template first time
        template1 = loader.load_from_file(json_path)
        
        # Load template second time (should be cached)
        template2 = loader.load_from_file(json_path)
        
        # Should be the same object due to caching
        assert template1 is template2
        assert len(loader._template_cache) == 1
    
    def test_clear_cache(self, loader, temp_dir, json_template_data):
        """Test clearing template cache."""
        # Create and load template
        json_path = temp_dir / "cached_template.json"
        with open(json_path, 'w') as f:
            json.dump(json_template_data, f)
        
        loader.load_from_file(json_path)
        assert len(loader._template_cache) == 1
        
        # Clear cache
        loader.clear_cache()
        assert len(loader._template_cache) == 0
    
    def test_load_from_directory(self, loader, temp_dir, json_template_data):
        """Test loading all templates from a directory."""
        # Create multiple template files
        for i in range(3):
            template_data = json_template_data.copy()
            template_data['id'] = f"template-{i}"
            template_data['name'] = f"Template {i}"
            
            json_path = temp_dir / f"template_{i}.json"
            with open(json_path, 'w') as f:
                json.dump(template_data, f)
        
        # Load all templates from directory
        templates = loader.load_from_directory(temp_dir, recursive=False)
        
        assert len(templates) == 3
        assert all(t.metadata.id == f"template-{i}" for i, t in enumerate(templates))
    
    def test_load_from_directory_recursive(self, loader, temp_dir, json_template_data):
        """Test loading templates recursively from subdirectories."""
        # Create subdirectories with templates
        subdirs = ['api', 'docs', 'tests']
        
        for subdir in subdirs:
            subdir_path = temp_dir / subdir
            subdir_path.mkdir()
            
            template_data = json_template_data.copy()
            template_data['id'] = f"{subdir}-template"
            
            json_path = subdir_path / f"{subdir}_template.json"
            with open(json_path, 'w') as f:
                json.dump(template_data, f)
        
        # Load templates recursively
        templates = loader.load_from_directory(temp_dir, recursive=True)
        
        assert len(templates) == 3
        template_ids = [t.metadata.id for t in templates]
        assert all(f"{subdir}-template" in template_ids for subdir in subdirs)
    
    def test_load_defaults(self, loader, temp_dir, json_template_data):
        """Test loading default templates."""
        # Create default templates in base path
        defaults_dir = temp_dir / "api"
        defaults_dir.mkdir()
        
        template_data = json_template_data.copy()
        template_data['id'] = "default-template"
        
        json_path = defaults_dir / "default.json"
        with open(json_path, 'w') as f:
            json.dump(template_data, f)
        
        # Load defaults
        templates = loader.load_defaults()
        
        assert len(templates) > 0
        assert any(t.metadata.id == "default-template" for t in templates)
    
    def test_save_json_template(self, loader, temp_dir):
        """Test saving template to JSON file."""
        # Create template
        metadata = TemplateMetadata(
            id="save-test",
            name="Save Test",
            description="Test saving",
            category=TemplateCategory.TESTING,
            type=TemplateType.TEST_PLAN
        )
        
        template = Template(
            metadata=metadata,
            content="Test content",
            variables=[],
            sections=[]
        )
        
        # Save template
        save_path = temp_dir / "saved_template.json"
        loader.save_to_file(template, save_path, format='json')
        
        assert save_path.exists()
        
        # Verify saved content
        with open(save_path, 'r') as f:
            saved_data = json.load(f)
        
        assert saved_data['metadata']['id'] == "save-test"
        assert saved_data['content'] == "Test content"
    
    def test_save_yaml_template(self, loader, temp_dir):
        """Test saving template to YAML file."""
        # Create template
        metadata = TemplateMetadata(
            id="yaml-save",
            name="YAML Save",
            description="Test YAML saving",
            category=TemplateCategory.DOCUMENTATION,
            type=TemplateType.README
        )
        
        template = Template(
            metadata=metadata,
            content="YAML content",
            variables=[],
            sections=[]
        )
        
        # Save template
        save_path = temp_dir / "saved_template.yaml"
        loader.save_to_file(template, save_path, format='yaml')
        
        assert save_path.exists()
        
        # Verify saved content
        with open(save_path, 'r') as f:
            saved_data = yaml.safe_load(f)
        
        assert saved_data['metadata']['id'] == "yaml-save"
        assert saved_data['content'] == "YAML content"
    
    def test_save_text_template(self, loader, temp_dir):
        """Test saving template to text file with frontmatter."""
        # Create template
        metadata = TemplateMetadata(
            id="text-save",
            name="Text Save",
            description="Test text saving",
            category=TemplateCategory.GUIDES,
            type=TemplateType.TUTORIAL
        )
        
        template = Template(
            metadata=metadata,
            content="# Tutorial\n\nText content here.",
            variables=[
                TemplateVariable(name="VAR1", description="Variable 1")
            ],
            sections=[]
        )
        
        # Save template
        save_path = temp_dir / "saved_template.md"
        loader.save_to_file(template, save_path, format='text')
        
        assert save_path.exists()
        
        # Verify saved content
        with open(save_path, 'r') as f:
            saved_content = f.read()
        
        assert "---" in saved_content  # Frontmatter delimiters
        assert "id: text-save" in saved_content
        assert "# Tutorial" in saved_content
    
    def test_infer_template_type(self, loader, temp_dir):
        """Test inferring template type from file path."""
        # Test various file names
        test_cases = [
            ("readme.md", TemplateType.README),
            ("api_reference.json", TemplateType.API_REFERENCE),
            ("test_plan.yaml", TemplateType.TEST_PLAN),
            ("installation_guide.md", TemplateType.INSTALLATION_GUIDE),
            ("changelog.txt", TemplateType.CHANGELOG),
            ("unknown.md", TemplateType.REFERENCE_GUIDE)  # Default
        ]
        
        for filename, expected_type in test_cases:
            file_path = temp_dir / filename
            inferred_type = loader._infer_template_type(file_path)
            assert inferred_type == expected_type
    
    def test_infer_category(self, loader, temp_dir):
        """Test inferring category from file path."""
        # Test with parent directory names
        test_cases = [
            ("api/template.json", TemplateCategory.API),
            ("documentation/readme.md", TemplateCategory.DOCUMENTATION),
            ("testing/test_plan.yaml", TemplateCategory.TESTING),
            ("guides/tutorial.md", TemplateCategory.GUIDES),
            ("unknown/file.txt", TemplateCategory.MISC)  # Default
        ]
        
        for path_str, expected_category in test_cases:
            file_path = temp_dir / path_str
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            inferred_category = loader._infer_category(file_path)
            
            # For paths with known parent directories
            if file_path.parent.name in [cat.value for cat in TemplateCategory]:
                assert inferred_category.value == file_path.parent.name
    
    def test_parse_template_with_includes(self, loader, temp_dir):
        """Test parsing template with includes."""
        template_data = {
            "id": "include-template",
            "name": "Include Template",
            "description": "Template with includes",
            "category": "documentation",
            "type": "readme",
            "template": "# Main\n\n{{INCLUDE:header}}\n\nContent\n\n{{INCLUDE:footer}}",
            "includes": ["header.md", "footer.md"]
        }
        
        # Create template file
        json_path = temp_dir / "include_template.json"
        with open(json_path, 'w') as f:
            json.dump(template_data, f)
        
        # Load template
        template = loader.load_from_file(json_path)
        
        assert template is not None
        assert len(template.includes) == 2
        assert "header.md" in template.includes
        assert "footer.md" in template.includes
    
    def test_handle_corrupt_json(self, loader, temp_dir):
        """Test handling of corrupt JSON file."""
        # Create corrupt JSON file
        corrupt_path = temp_dir / "corrupt.json"
        with open(corrupt_path, 'w') as f:
            f.write("{ invalid json content")
        
        # Attempt to load
        with pytest.raises(TemplateStorageError):
            loader.load_from_file(corrupt_path)
    
    def test_handle_corrupt_yaml(self, loader, temp_dir):
        """Test handling of corrupt YAML file."""
        # Create corrupt YAML file
        corrupt_path = temp_dir / "corrupt.yaml"
        with open(corrupt_path, 'w') as f:
            f.write("invalid:\n  - yaml\n  content:\n    improper indentation")
        
        # Attempt to load
        with pytest.raises(TemplateStorageError):
            loader.load_from_file(corrupt_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])