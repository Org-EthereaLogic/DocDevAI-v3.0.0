"""
Unit tests for M006 Template Registry.

Tests the main registry class functionality including CRUD operations,
template loading, parsing, and integration with other modules.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import json
import tempfile
import shutil
from datetime import datetime

from devdocai.templates.registry import TemplateRegistry
from devdocai.templates.models import (
    Template as TemplateModel,
    TemplateMetadata,
    TemplateCategory,
    TemplateType,
    TemplateVariable,
    TemplateSection,
    TemplateSearchCriteria,
    TemplateRenderContext,
    TemplateValidationResult
)
from devdocai.templates.template import Template
from devdocai.templates.exceptions import (
    TemplateNotFoundError,
    TemplateDuplicateError,
    TemplateStorageError,
    TemplateValidationError
)
from devdocai.core.config import ConfigurationManager
from devdocai.storage.secure_storage import SecureStorageLayer


class TestTemplateRegistry:
    """Test suite for TemplateRegistry class."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration manager."""
        config = Mock(spec=ConfigurationManager)
        config.get.return_value = {}
        return config
    
    @pytest.fixture
    def mock_storage(self):
        """Create mock storage system."""
        storage = Mock(spec=SecureStorageLayer)
        return storage
    
    @pytest.fixture
    def sample_template_data(self):
        """Create sample template data."""
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
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def registry(self, mock_config, mock_storage):
        """Create TemplateRegistry instance."""
        return TemplateRegistry(
            config_manager=mock_config,
            storage=mock_storage,
            auto_load_defaults=False
        )
    
    def test_registry_initialization(self, mock_config, mock_storage):
        """Test registry initialization."""
        registry = TemplateRegistry(
            config_manager=mock_config,
            storage=mock_storage,
            auto_load_defaults=False
        )
        
        assert registry.config_manager == mock_config
        assert registry.storage == mock_storage
        assert registry.loader is not None
        assert registry.validator is not None
        assert registry.category_manager is not None
        assert len(registry._templates) == 0
        assert registry._metrics['templates_loaded'] == 0
    
    def test_registry_auto_load_defaults(self, mock_config, mock_storage):
        """Test registry with auto-loading defaults."""
        with patch.object(TemplateRegistry, '_load_default_templates') as mock_load:
            registry = TemplateRegistry(
                config_manager=mock_config,
                storage=mock_storage,
                auto_load_defaults=True
            )
            mock_load.assert_called_once()
    
    def test_create_template(self, registry, sample_template_data):
        """Test creating a new template."""
        # Create template model
        metadata = TemplateMetadata(
            id=sample_template_data['id'],
            name=sample_template_data['name'],
            description=sample_template_data['description'],
            category=TemplateCategory.TESTING,
            type=TemplateType.TEST_PLAN
        )
        
        template_model = TemplateModel(
            metadata=metadata,
            content=sample_template_data['template'],
            variables=[],
            sections=[]
        )
        
        # Create template
        template_id = registry.create(template_model)
        
        assert template_id == sample_template_data['id']
        assert sample_template_data['id'] in registry._templates
        assert registry._metrics['templates_loaded'] == 1
    
    def test_create_duplicate_template(self, registry, sample_template_data):
        """Test creating duplicate template raises error."""
        metadata = TemplateMetadata(
            id=sample_template_data['id'],
            name=sample_template_data['name'],
            description=sample_template_data['description'],
            category=TemplateCategory.TESTING,
            type=TemplateType.TEST_PLAN
        )
        
        template_model = TemplateModel(
            metadata=metadata,
            content=sample_template_data['template']
        )
        
        # Create first template
        registry.create(template_model)
        
        # Attempt to create duplicate
        with pytest.raises(TemplateDuplicateError):
            registry.create(template_model)
    
    def test_get_template(self, registry, sample_template_data):
        """Test retrieving a template."""
        # Create template
        metadata = TemplateMetadata(
            id=sample_template_data['id'],
            name=sample_template_data['name'],
            description=sample_template_data['description'],
            category=TemplateCategory.TESTING,
            type=TemplateType.TEST_PLAN
        )
        
        template_model = TemplateModel(
            metadata=metadata,
            content=sample_template_data['template']
        )
        
        registry.create(template_model)
        
        # Get template
        template = registry.get(sample_template_data['id'])
        
        assert template is not None
        assert template.metadata.id == sample_template_data['id']
        assert template.metadata.name == sample_template_data['name']
    
    def test_get_nonexistent_template(self, registry):
        """Test getting non-existent template raises error."""
        with pytest.raises(TemplateNotFoundError):
            registry.get("nonexistent-template")
    
    def test_update_template(self, registry, sample_template_data):
        """Test updating an existing template."""
        # Create initial template
        metadata = TemplateMetadata(
            id=sample_template_data['id'],
            name=sample_template_data['name'],
            description=sample_template_data['description'],
            category=TemplateCategory.TESTING,
            type=TemplateType.TEST_PLAN
        )
        
        template_model = TemplateModel(
            metadata=metadata,
            content=sample_template_data['template']
        )
        
        registry.create(template_model)
        
        # Update template
        updated_metadata = TemplateMetadata(
            id=sample_template_data['id'],
            name="Updated Template",
            description="Updated description",
            category=TemplateCategory.TESTING,
            type=TemplateType.TEST_PLAN
        )
        
        updated_model = TemplateModel(
            metadata=updated_metadata,
            content="Updated content"
        )
        
        registry.update(sample_template_data['id'], updated_model)
        
        # Verify update
        template = registry.get(sample_template_data['id'])
        assert template.metadata.name == "Updated Template"
        assert template.content == "Updated content"
    
    def test_update_nonexistent_template(self, registry):
        """Test updating non-existent template raises error."""
        metadata = TemplateMetadata(
            id="nonexistent",
            name="Test",
            description="Test",
            category=TemplateCategory.TESTING,
            type=TemplateType.TEST_PLAN
        )
        
        template_model = TemplateModel(
            metadata=metadata,
            content="Content"
        )
        
        with pytest.raises(TemplateNotFoundError):
            registry.update("nonexistent", template_model)
    
    def test_delete_template(self, registry, sample_template_data):
        """Test deleting a template."""
        # Create template
        metadata = TemplateMetadata(
            id=sample_template_data['id'],
            name=sample_template_data['name'],
            description=sample_template_data['description'],
            category=TemplateCategory.TESTING,
            type=TemplateType.TEST_PLAN
        )
        
        template_model = TemplateModel(
            metadata=metadata,
            content=sample_template_data['template']
        )
        
        registry.create(template_model)
        
        # Delete template
        registry.delete(sample_template_data['id'])
        
        # Verify deletion
        assert sample_template_data['id'] not in registry._templates
        
        with pytest.raises(TemplateNotFoundError):
            registry.get(sample_template_data['id'])
    
    def test_delete_nonexistent_template(self, registry):
        """Test deleting non-existent template raises error."""
        with pytest.raises(TemplateNotFoundError):
            registry.delete("nonexistent-template")
    
    def test_list_templates(self, registry):
        """Test listing all templates."""
        # Create multiple templates
        for i in range(3):
            metadata = TemplateMetadata(
                id=f"template-{i}",
                name=f"Template {i}",
                description=f"Description {i}",
                category=TemplateCategory.TESTING,
                type=TemplateType.TEST_PLAN
            )
            
            template_model = TemplateModel(
                metadata=metadata,
                content=f"Content {i}"
            )
            
            registry.create(template_model)
        
        # List templates
        templates = registry.list()
        
        assert len(templates) == 3
        assert all(f"template-{i}" in [t.metadata.id for t in templates] for i in range(3))
    
    def test_search_templates(self, registry):
        """Test searching templates."""
        # Create templates with different categories
        categories = [TemplateCategory.API, TemplateCategory.TESTING, TemplateCategory.DOCUMENTATION]
        
        for i, category in enumerate(categories):
            metadata = TemplateMetadata(
                id=f"template-{i}",
                name=f"Template {i}",
                description=f"Description for {category.value}",
                category=category,
                type=TemplateType.TEST_PLAN,
                tags=[category.value, "test"]
            )
            
            template_model = TemplateModel(
                metadata=metadata,
                content=f"Content {i}"
            )
            
            registry.create(template_model)
        
        # Search by category
        criteria = TemplateSearchCriteria(
            category=TemplateCategory.API
        )
        
        results = registry.search(criteria)
        
        assert len(results) == 1
        assert results[0].metadata.category == TemplateCategory.API
    
    def test_search_by_tags(self, registry):
        """Test searching templates by tags."""
        # Create templates with different tags
        tags_list = [
            ["python", "api"],
            ["javascript", "frontend"],
            ["python", "testing"]
        ]
        
        for i, tags in enumerate(tags_list):
            metadata = TemplateMetadata(
                id=f"template-{i}",
                name=f"Template {i}",
                description=f"Description {i}",
                category=TemplateCategory.TESTING,
                type=TemplateType.TEST_PLAN,
                tags=tags
            )
            
            template_model = TemplateModel(
                metadata=metadata,
                content=f"Content {i}"
            )
            
            registry.create(template_model)
        
        # Search by tag
        criteria = TemplateSearchCriteria(
            tags=["python"]
        )
        
        results = registry.search(criteria)
        
        assert len(results) == 2
        assert all("python" in t.metadata.tags for t in results)
    
    def test_render_template(self, registry, sample_template_data):
        """Test rendering a template with variables."""
        # Create template with variables
        metadata = TemplateMetadata(
            id=sample_template_data['id'],
            name=sample_template_data['name'],
            description=sample_template_data['description'],
            category=TemplateCategory.TESTING,
            type=TemplateType.TEST_PLAN
        )
        
        variables = [
            TemplateVariable(
                name="PROJECT_NAME",
                description="Project name",
                required=True,
                type="text"
            )
        ]
        
        template_model = TemplateModel(
            metadata=metadata,
            content="# {{PROJECT_NAME}}\n\nThis is a test for {{PROJECT_NAME}}.",
            variables=variables
        )
        
        registry.create(template_model)
        
        # Render template
        context = TemplateRenderContext(
            variables={"PROJECT_NAME": "My Awesome Project"}
        )
        
        rendered = registry.render(sample_template_data['id'], context)
        
        assert "My Awesome Project" in rendered
        assert "{{PROJECT_NAME}}" not in rendered
        assert registry._metrics['templates_rendered'] == 1
    
    def test_render_template_with_missing_variables(self, registry):
        """Test rendering template with missing required variables."""
        # Create template with required variable
        metadata = TemplateMetadata(
            id="test-template",
            name="Test Template",
            description="Test",
            category=TemplateCategory.TESTING,
            type=TemplateType.TEST_PLAN
        )
        
        variables = [
            TemplateVariable(
                name="REQUIRED_VAR",
                description="Required variable",
                required=True,
                type="text"
            )
        ]
        
        template_model = TemplateModel(
            metadata=metadata,
            content="Value: {{REQUIRED_VAR}}",
            variables=variables
        )
        
        registry.create(template_model)
        
        # Attempt to render without required variable
        context = TemplateRenderContext(
            variables={}
        )
        
        with pytest.raises(TemplateValidationError):
            registry.render("test-template", context)
    
    def test_validate_template(self, registry):
        """Test template validation."""
        # Create valid template
        metadata = TemplateMetadata(
            id="valid-template",
            name="Valid Template",
            description="A valid template",
            category=TemplateCategory.TESTING,
            type=TemplateType.TEST_PLAN
        )
        
        template_model = TemplateModel(
            metadata=metadata,
            content="Valid content"
        )
        
        registry.create(template_model)
        
        # Validate template
        result = registry.validate("valid-template")
        
        assert isinstance(result, TemplateValidationResult)
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_export_template(self, registry, temp_dir):
        """Test exporting a template to file."""
        # Create template
        metadata = TemplateMetadata(
            id="export-template",
            name="Export Template",
            description="Template for export",
            category=TemplateCategory.TESTING,
            type=TemplateType.TEST_PLAN
        )
        
        template_model = TemplateModel(
            metadata=metadata,
            content="Export content"
        )
        
        registry.create(template_model)
        
        # Export to JSON
        export_path = temp_dir / "exported_template.json"
        registry.export("export-template", export_path, format="json")
        
        assert export_path.exists()
        
        # Verify exported content
        with open(export_path, 'r') as f:
            exported_data = json.load(f)
        
        assert exported_data['metadata']['id'] == "export-template"
        assert exported_data['content'] == "Export content"
    
    def test_import_template(self, registry, temp_dir, sample_template_data):
        """Test importing a template from file."""
        # Create template file
        import_path = temp_dir / "import_template.json"
        
        with open(import_path, 'w') as f:
            json.dump(sample_template_data, f)
        
        # Import template
        template_id = registry.import_template(import_path)
        
        assert template_id == sample_template_data['id']
        assert sample_template_data['id'] in registry._templates
        
        # Verify imported template
        template = registry.get(sample_template_data['id'])
        assert template.metadata.name == sample_template_data['name']
    
    def test_clone_template(self, registry):
        """Test cloning an existing template."""
        # Create original template
        metadata = TemplateMetadata(
            id="original-template",
            name="Original Template",
            description="Original description",
            category=TemplateCategory.TESTING,
            type=TemplateType.TEST_PLAN
        )
        
        template_model = TemplateModel(
            metadata=metadata,
            content="Original content"
        )
        
        registry.create(template_model)
        
        # Clone template
        new_id = registry.clone("original-template", "cloned-template", "Cloned Template")
        
        assert new_id == "cloned-template"
        assert "cloned-template" in registry._templates
        
        # Verify cloned template
        cloned = registry.get("cloned-template")
        assert cloned.metadata.name == "Cloned Template"
        assert cloned.content == "Original content"
        assert cloned.metadata.id != "original-template"
    
    def test_event_handlers(self, registry):
        """Test event handler registration and triggering."""
        # Track events
        events = []
        
        def on_created(template_id):
            events.append(('created', template_id))
        
        def on_updated(template_id):
            events.append(('updated', template_id))
        
        def on_deleted(template_id):
            events.append(('deleted', template_id))
        
        # Register handlers
        registry.on('template_created', on_created)
        registry.on('template_updated', on_updated)
        registry.on('template_deleted', on_deleted)
        
        # Create template
        metadata = TemplateMetadata(
            id="event-template",
            name="Event Template",
            description="Test events",
            category=TemplateCategory.TESTING,
            type=TemplateType.TEST_PLAN
        )
        
        template_model = TemplateModel(
            metadata=metadata,
            content="Content"
        )
        
        registry.create(template_model)
        
        # Update template
        registry.update("event-template", template_model)
        
        # Delete template
        registry.delete("event-template")
        
        # Verify events
        assert ('created', 'event-template') in events
        assert ('updated', 'event-template') in events
        assert ('deleted', 'event-template') in events
    
    def test_thread_safety(self, registry):
        """Test thread safety of registry operations."""
        import threading
        
        def create_template(i):
            metadata = TemplateMetadata(
                id=f"thread-template-{i}",
                name=f"Thread Template {i}",
                description=f"Created by thread {i}",
                category=TemplateCategory.TESTING,
                type=TemplateType.TEST_PLAN
            )
            
            template_model = TemplateModel(
                metadata=metadata,
                content=f"Content {i}"
            )
            
            registry.create(template_model)
        
        # Create templates in parallel
        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_template, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify all templates created
        templates = registry.list()
        assert len(templates) == 10
        assert all(f"thread-template-{i}" in [t.metadata.id for t in templates] for i in range(10))
    
    def test_metrics_tracking(self, registry):
        """Test metrics tracking."""
        # Initial metrics
        assert registry._metrics['templates_loaded'] == 0
        assert registry._metrics['templates_rendered'] == 0
        
        # Create template
        metadata = TemplateMetadata(
            id="metrics-template",
            name="Metrics Template",
            description="Test metrics",
            category=TemplateCategory.TESTING,
            type=TemplateType.TEST_PLAN
        )
        
        template_model = TemplateModel(
            metadata=metadata,
            content="{{VAR}}"
        )
        
        registry.create(template_model)
        assert registry._metrics['templates_loaded'] == 1
        
        # Render template
        context = TemplateRenderContext(
            variables={"VAR": "value"}
        )
        
        registry.render("metrics-template", context)
        assert registry._metrics['templates_rendered'] == 1
        
        # Get template (cache hit/miss tracking)
        registry.get("metrics-template")
        registry.get("metrics-template")  # Should be cached
        
        metrics = registry.get_metrics()
        assert metrics['templates_loaded'] == 1
        assert metrics['templates_rendered'] == 1
    
    def test_storage_integration(self, registry, mock_storage):
        """Test integration with storage system."""
        # Configure storage to be used
        registry.storage = mock_storage
        mock_storage.create.return_value = "doc-123"
        mock_storage.read.return_value = {"data": "stored"}
        
        # Create template with storage
        metadata = TemplateMetadata(
            id="storage-template",
            name="Storage Template",
            description="Test storage",
            category=TemplateCategory.TESTING,
            type=TemplateType.TEST_PLAN
        )
        
        template_model = TemplateModel(
            metadata=metadata,
            content="Content"
        )
        
        # Test persistence option
        with patch.object(registry, '_persist_to_storage') as mock_persist:
            registry.create(template_model, persist=True)
            mock_persist.assert_called_once()
    
    def test_default_templates_loading(self):
        """Test loading default templates from defaults directory."""
        with patch('devdocai.templates.registry.TemplateLoader') as MockLoader:
            mock_loader = MockLoader.return_value
            
            # Mock default templates
            default_templates = [
                TemplateModel(
                    metadata=TemplateMetadata(
                        id=f"default-{i}",
                        name=f"Default {i}",
                        description=f"Default template {i}",
                        category=TemplateCategory.TESTING,
                        type=TemplateType.TEST_PLAN
                    ),
                    content=f"Default content {i}"
                )
                for i in range(5)
            ]
            
            mock_loader.load_defaults.return_value = default_templates
            
            # Create registry with auto-load
            registry = TemplateRegistry(auto_load_defaults=True)
            
            # Verify defaults loaded
            mock_loader.load_defaults.assert_called_once()


class TestTemplateRegistryAdvanced:
    """Advanced test cases for TemplateRegistry."""
    
    @pytest.fixture
    def registry_with_templates(self, mock_config, mock_storage):
        """Create registry with pre-loaded templates."""
        registry = TemplateRegistry(
            config_manager=mock_config,
            storage=mock_storage,
            auto_load_defaults=False
        )
        
        # Add various templates
        categories = [
            TemplateCategory.API,
            TemplateCategory.DOCUMENTATION,
            TemplateCategory.TESTING,
            TemplateCategory.GUIDES
        ]
        
        for i, category in enumerate(categories):
            for j in range(3):
                metadata = TemplateMetadata(
                    id=f"{category.value}-template-{j}",
                    name=f"{category.value.title()} Template {j}",
                    description=f"Template for {category.value}",
                    category=category,
                    type=TemplateType.TEST_PLAN,
                    tags=[category.value, f"tag-{j}"]
                )
                
                template_model = TemplateModel(
                    metadata=metadata,
                    content=f"Content for {category.value} template {j}"
                )
                
                registry.create(template_model)
        
        return registry
    
    def test_bulk_operations(self, registry_with_templates):
        """Test bulk operations on templates."""
        # Bulk update
        updates = []
        for template in registry_with_templates.list():
            if template.metadata.category == TemplateCategory.API:
                template.metadata.tags.append("bulk-updated")
                updates.append((template.metadata.id, template))
        
        # Apply updates
        for template_id, template in updates:
            registry_with_templates.update(template_id, template)
        
        # Verify updates
        api_templates = registry_with_templates.search(
            TemplateSearchCriteria(category=TemplateCategory.API)
        )
        
        assert all("bulk-updated" in t.metadata.tags for t in api_templates)
    
    def test_category_statistics(self, registry_with_templates):
        """Test getting statistics by category."""
        stats = {}
        
        for template in registry_with_templates.list():
            category = template.metadata.category.value
            stats[category] = stats.get(category, 0) + 1
        
        # Verify counts
        assert stats['api'] == 3
        assert stats['documentation'] == 3
        assert stats['testing'] == 3
        assert stats['guides'] == 3
    
    def test_template_versioning(self, registry_with_templates):
        """Test template version management."""
        # Get a template
        template = registry_with_templates.list()[0]
        original_version = template.metadata.version
        
        # Update version
        template.metadata.version = "2.0.0"
        registry_with_templates.update(template.metadata.id, template)
        
        # Verify version updated
        updated = registry_with_templates.get(template.metadata.id)
        assert updated.metadata.version == "2.0.0"
        assert updated.metadata.version != original_version
    
    def test_template_activation(self, registry_with_templates):
        """Test template activation/deactivation."""
        # Deactivate a template
        template = registry_with_templates.list()[0]
        template.metadata.is_active = False
        registry_with_templates.update(template.metadata.id, template)
        
        # Search only active templates
        criteria = TemplateSearchCriteria(is_active=True)
        active_templates = registry_with_templates.search(criteria)
        
        # Verify deactivated template not in results
        assert template.metadata.id not in [t.metadata.id for t in active_templates]
    
    def test_usage_tracking(self, registry_with_templates):
        """Test template usage count tracking."""
        template_id = registry_with_templates.list()[0].metadata.id
        
        # Render template multiple times
        context = TemplateRenderContext(variables={})
        
        for _ in range(5):
            registry_with_templates.render(template_id, context)
        
        # Check usage count
        template = registry_with_templates.get(template_id)
        assert template.metadata.usage_count >= 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])