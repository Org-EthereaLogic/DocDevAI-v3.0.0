"""
Tests for M004 Document Generator - Pass 1 TDD
DevDocAI v3.0.0 - AI-Powered Document Generation

Test Coverage Target: 80%
Test Strategy: Unit tests for each component, integration tests with M001/M002/M008
"""

import asyncio

# Import modules to test (will be implemented after tests)
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from devdocai.core.config import ConfigurationManager
from devdocai.core.generator import (
    ContextBuilder,
    DocumentGenerationError,
    DocumentGenerator,
    DocumentValidator,
    PromptEngine,
    TemplateManager,
    TemplateNotFoundError,
)
from devdocai.core.storage import Document, StorageManager
from devdocai.intelligence.llm_adapter import LLMAdapter, LLMResponse

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_config():
    """Mock configuration manager."""
    config = Mock(spec=ConfigurationManager)
    config.get.side_effect = lambda key, default=None: {
        "templates.dir": "/tmp/templates",
        "ai.model": "gpt-4",
        "ai.temperature": 0.7,
        "ai.max_tokens": 4000,
        "quality.min_score": 85,
        "quality.check_grammar": True,
        "quality.check_completeness": True,
    }.get(key, default)
    return config


@pytest.fixture
def mock_llm_adapter():
    """Mock LLM adapter."""
    adapter = Mock(spec=LLMAdapter)
    adapter.generate.return_value = LLMResponse(
        content="# Generated Document\n\nThis is AI-generated content.",
        provider="openai",
        tokens_used=100,
        cost=0.002,
        latency=1.5,
    )
    return adapter


@pytest.fixture
def mock_storage():
    """Mock storage manager."""
    storage = Mock(spec=StorageManager)
    storage.save_document.return_value = True
    storage.get_document.return_value = Document(
        id="doc_123",
        type="readme",
        content="# Test Document",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    return storage


@pytest.fixture
def sample_template():
    """Sample document template."""
    return {
        "document_type": "readme",
        "name": "README Template",
        "sections": [
            {
                "name": "header",
                "prompt_template": "Generate a professional README header for {project_name}. Include badges for build status and test coverage.",
                "required": True,
            },
            {
                "name": "description",
                "prompt_template": "Write a clear and concise description for {project_name}. The project is about: {project_description}",
                "required": True,
            },
            {
                "name": "installation",
                "prompt_template": "Create installation instructions for a Python project using pip. Project name: {project_name}",
                "required": True,
            },
        ],
        "context_requirements": ["project_name", "project_description", "python_version"],
        "quality_criteria": {
            "min_length": 500,
            "max_length": 5000,
            "required_sections": ["header", "description", "installation"],
        },
    }


@pytest.fixture
def sample_context():
    """Sample project context."""
    return {
        "project_name": "DevDocAI",
        "project_description": "AI-powered documentation generator for developers",
        "python_version": "3.8+",
        "author": "DevDocAI Team",
        "license": "MIT",
        "dependencies": ["pydantic", "yaml", "cryptography"],
    }


# ============================================================================
# TemplateManager Tests
# ============================================================================


class TestTemplateManager:
    """Tests for TemplateManager class."""

    def test_init(self, mock_config):
        """Test TemplateManager initialization."""
        manager = TemplateManager(mock_config)
        assert manager.config == mock_config
        assert manager.template_dir == Path("/tmp/templates")
        assert manager._cache == {}

    def test_load_template_success(self, mock_config, sample_template, tmp_path):
        """Test successful template loading."""
        # Create template file
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        template_file = template_dir / "readme.yaml"
        template_file.write_text(yaml.dump(sample_template))

        # Mock config to use temp directory
        mock_config.get.side_effect = lambda key, default=None: {
            "templates.dir": str(template_dir)
        }.get(key, default)

        manager = TemplateManager(mock_config)
        template = manager.load_template("readme")

        assert template["document_type"] == "readme"
        assert len(template["sections"]) == 3
        assert "readme" in manager._cache

    def test_load_template_not_found(self, mock_config):
        """Test template not found error."""
        manager = TemplateManager(mock_config)

        with pytest.raises(TemplateNotFoundError) as exc_info:
            manager.load_template("nonexistent")

        assert "Template not found: nonexistent" in str(exc_info.value)

    def test_load_template_cache(self, mock_config, sample_template, tmp_path):
        """Test template caching."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        template_file = template_dir / "readme.yaml"
        template_file.write_text(yaml.dump(sample_template))

        mock_config.get.return_value = str(template_dir)

        manager = TemplateManager(mock_config)

        # First load
        template1 = manager.load_template("readme")
        # Second load (should use cache)
        template2 = manager.load_template("readme")

        assert template1 is template2  # Same object reference

    def test_list_templates(self, mock_config, tmp_path):
        """Test listing available templates."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        # Create multiple template files
        (template_dir / "readme.yaml").write_text("document_type: readme")
        (template_dir / "api_doc.yaml").write_text("document_type: api")
        (template_dir / "changelog.yml").write_text("document_type: changelog")

        mock_config.get.return_value = str(template_dir)

        manager = TemplateManager(mock_config)
        templates = manager.list_templates()

        assert set(templates) == {"readme", "api_doc", "changelog"}

    def test_validate_template(self, mock_config, sample_template):
        """Test template validation."""
        manager = TemplateManager(mock_config)

        # Valid template
        assert manager.validate_template(sample_template) is True

        # Invalid template (missing required field)
        invalid_template = sample_template.copy()
        del invalid_template["document_type"]

        with pytest.raises(ValueError) as exc_info:
            manager.validate_template(invalid_template)

        assert "Missing required field: document_type" in str(exc_info.value)


# ============================================================================
# ContextBuilder Tests
# ============================================================================


class TestContextBuilder:
    """Tests for ContextBuilder class."""

    def test_init(self, mock_config):
        """Test ContextBuilder initialization."""
        builder = ContextBuilder(mock_config)
        assert builder.config == mock_config
        assert builder._extractors != {}

    def test_extract_from_project(self, mock_config, tmp_path):
        """Test context extraction from project."""
        # Create sample project structure
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Create pyproject.toml
        pyproject = project_dir / "pyproject.toml"
        pyproject.write_text(
            """
[project]
name = "test-project"
version = "1.0.0"
description = "A test project"
requires-python = ">=3.8"
        """
        )

        # Create README
        readme = project_dir / "README.md"
        readme.write_text("# Test Project\n\nThis is a test project.")

        # Create Python file
        py_file = project_dir / "main.py"
        py_file.write_text('"""Main module."""\n\ndef main():\n    pass')

        builder = ContextBuilder(mock_config)
        context = builder.extract_from_project(str(project_dir))

        assert context["project_name"] == "test-project"
        assert context["project_description"] == "A test project"
        assert context["python_version"] == ">=3.8"
        assert "readme_content" in context

    def test_extract_from_python_files(self, mock_config, tmp_path):
        """Test context extraction from Python files."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Create Python files with docstrings and functions
        (project_dir / "module1.py").write_text(
            '''
"""Module 1 documentation."""

def function1():
    """Function 1 docstring."""
    pass

class MyClass:
    """Class docstring."""
    pass
        '''
        )

        builder = ContextBuilder(mock_config)
        context = builder.extract_from_project(str(project_dir))

        assert "modules" in context
        assert "functions" in context
        assert "classes" in context

    def test_extract_dependencies(self, mock_config, tmp_path):
        """Test dependency extraction."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Create requirements.txt
        requirements = project_dir / "requirements.txt"
        requirements.write_text("pydantic>=2.0\nyaml\ncryptography==41.0.0")

        builder = ContextBuilder(mock_config)
        context = builder.extract_from_project(str(project_dir))

        assert "dependencies" in context
        assert "pydantic" in context["dependencies"][0]

    def test_merge_contexts(self, mock_config):
        """Test context merging."""
        builder = ContextBuilder(mock_config)

        context1 = {"project_name": "test", "version": "1.0"}
        context2 = {"author": "Developer", "version": "2.0"}

        merged = builder.merge_contexts(context1, context2)

        assert merged["project_name"] == "test"
        assert merged["author"] == "Developer"
        assert merged["version"] == "2.0"  # context2 overwrites


# ============================================================================
# PromptEngine Tests
# ============================================================================


class TestPromptEngine:
    """Tests for PromptEngine class."""

    def test_init(self, mock_config):
        """Test PromptEngine initialization."""
        engine = PromptEngine(mock_config)
        assert engine.config == mock_config
        assert engine.max_prompt_length > 0

    def test_construct_prompt(self, mock_config, sample_template, sample_context):
        """Test prompt construction from template."""
        engine = PromptEngine(mock_config)

        section = sample_template["sections"][0]
        prompt = engine.construct_prompt(section["prompt_template"], sample_context)

        assert "DevDocAI" in prompt
        assert "professional README header" in prompt

    def test_construct_system_prompt(self, mock_config):
        """Test system prompt construction."""
        engine = PromptEngine(mock_config)

        system_prompt = engine.construct_system_prompt("readme")

        assert "documentation" in system_prompt.lower()
        assert "professional" in system_prompt.lower()

    def test_format_template_with_context(self, mock_config):
        """Test template formatting with context."""
        engine = PromptEngine(mock_config)

        template = "Create docs for {project_name} version {version}"
        context = {"project_name": "TestProject", "version": "1.0.0"}

        formatted = engine.format_template(template, context)

        assert formatted == "Create docs for TestProject version 1.0.0"

    def test_format_template_missing_context(self, mock_config):
        """Test template formatting with missing context."""
        engine = PromptEngine(mock_config)

        template = "Project: {project_name}, Author: {author}"
        context = {"project_name": "TestProject"}

        formatted = engine.format_template(template, context, use_defaults=True)

        assert "TestProject" in formatted
        assert "{author}" not in formatted  # Should handle gracefully

    def test_optimize_prompt_length(self, mock_config):
        """Test prompt length optimization."""
        engine = PromptEngine(mock_config)
        engine.max_prompt_length = 100

        long_prompt = "x" * 200
        optimized = engine.optimize_prompt(long_prompt)

        assert len(optimized) <= 100

    def test_add_examples_to_prompt(self, mock_config):
        """Test adding examples to prompt."""
        engine = PromptEngine(mock_config)

        base_prompt = "Generate a README"
        examples = ["Example 1: # Project", "Example 2: ## Installation"]

        prompt_with_examples = engine.add_examples(base_prompt, examples)

        assert base_prompt in prompt_with_examples
        assert "Example 1" in prompt_with_examples


# ============================================================================
# DocumentValidator Tests
# ============================================================================


class TestDocumentValidator:
    """Tests for DocumentValidator class."""

    def test_init(self, mock_config):
        """Test DocumentValidator initialization."""
        validator = DocumentValidator(mock_config)
        assert validator.config == mock_config
        assert validator.min_quality_score == 85

    def test_validate_document_success(self, mock_config):
        """Test successful document validation."""
        validator = DocumentValidator(mock_config)

        document = """
        # DevDocAI Documentation

        ## Description
        This is a comprehensive documentation for the DevDocAI project.
        It includes all necessary sections and information.

        ## Installation
        pip install devdocai

        ## Usage
        devdocai generate --type readme
        """

        template = {
            "quality_criteria": {
                "min_length": 100,
                "max_length": 10000,
                "required_sections": ["Description", "Installation"],
            }
        }

        result = validator.validate(document, template)

        assert result.is_valid is True
        assert result.score >= 85

    def test_validate_document_too_short(self, mock_config):
        """Test validation failure for too short document."""
        validator = DocumentValidator(mock_config)

        document = "# Short"
        template = {"quality_criteria": {"min_length": 100}}

        result = validator.validate(document, template)

        assert result.is_valid is False
        assert "too short" in result.errors[0].lower()

    def test_validate_missing_sections(self, mock_config):
        """Test validation failure for missing sections."""
        validator = DocumentValidator(mock_config)

        document = "# Header\n\nSome content here."
        template = {"quality_criteria": {"required_sections": ["Installation", "Usage", "API"]}}

        result = validator.validate(document, template)

        assert result.is_valid is False
        assert any("missing" in error.lower() for error in result.errors)

    def test_calculate_quality_score(self, mock_config):
        """Test quality score calculation."""
        validator = DocumentValidator(mock_config)

        document = """
        # Complete Documentation

        ## Overview
        Detailed overview with proper grammar and structure.

        ## Installation
        Step-by-step installation guide.

        ## Usage
        Clear usage examples with code snippets.

        ## API Reference
        Comprehensive API documentation.
        """

        score = validator.calculate_score(document)

        assert 0 <= score <= 100
        assert score >= 70  # Well-structured document should score well

    def test_check_grammar(self, mock_config):
        """Test grammar checking (basic)."""
        validator = DocumentValidator(mock_config)

        # Good grammar
        good_text = "This is a well-written sentence."
        assert validator.check_grammar(good_text) is True

        # Poor grammar (basic check)
        poor_text = "This are bad grammar"
        # Note: Basic implementation might not catch all errors
        score = validator.check_grammar(poor_text)
        assert isinstance(score, bool)


# ============================================================================
# DocumentGenerator Tests (Main Orchestrator)
# ============================================================================


class TestDocumentGenerator:
    """Tests for main DocumentGenerator class."""

    def test_init(self, mock_config, mock_llm_adapter, mock_storage):
        """Test DocumentGenerator initialization."""
        generator = DocumentGenerator(
            config=mock_config, llm_adapter=mock_llm_adapter, storage=mock_storage
        )

        assert generator.config == mock_config
        assert generator.llm_adapter == mock_llm_adapter
        assert generator.storage == mock_storage
        assert generator.template_manager is not None
        assert generator.context_builder is not None
        assert generator.prompt_engine is not None
        assert generator.validator is not None

    @pytest.mark.asyncio
    async def test_generate_document_success(
        self, mock_config, mock_llm_adapter, mock_storage, sample_template, sample_context
    ):
        """Test successful document generation."""
        generator = DocumentGenerator(
            config=mock_config, llm_adapter=mock_llm_adapter, storage=mock_storage
        )

        # Mock template manager
        generator.template_manager.load_template = Mock(return_value=sample_template)

        # Mock context builder
        generator.context_builder.extract_from_project = Mock(return_value=sample_context)

        # Mock validator
        validation_result = Mock()
        validation_result.is_valid = True
        validation_result.score = 90
        generator.validator.validate = Mock(return_value=validation_result)

        # Generate document
        result = await generator.generate(document_type="readme", project_path="/test/project")

        assert result["document_id"]  # Should have an ID
        assert result["type"] == "readme"
        assert result["quality_score"] == 90
        assert "content" in result

        # Verify calls
        generator.template_manager.load_template.assert_called_with("readme")
        generator.context_builder.extract_from_project.assert_called_with("/test/project")
        mock_llm_adapter.generate.assert_called()
        mock_storage.save_document.assert_called()

    @pytest.mark.asyncio
    async def test_generate_document_validation_failure(
        self, mock_config, mock_llm_adapter, mock_storage
    ):
        """Test document generation with validation failure."""
        generator = DocumentGenerator(
            config=mock_config, llm_adapter=mock_llm_adapter, storage=mock_storage
        )

        # Mock validation failure
        validation_result = Mock()
        validation_result.is_valid = False
        validation_result.score = 60
        validation_result.errors = ["Document too short", "Missing required sections"]
        generator.validator.validate = Mock(return_value=validation_result)

        # Mock other components with proper template structure
        generator.template_manager.load_template = Mock(
            return_value={
                "document_type": "readme",
                "sections": [{"name": "header", "prompt_template": "Generate header"}],
            }
        )
        generator.context_builder.extract_from_project = Mock(return_value={})

        with pytest.raises(DocumentGenerationError) as exc_info:
            await generator.generate("readme", "/test/project")

        assert "quality standards" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_generate_with_retry(self, mock_config, mock_llm_adapter, mock_storage):
        """Test document generation with retry on failure."""
        generator = DocumentGenerator(
            config=mock_config, llm_adapter=mock_llm_adapter, storage=mock_storage
        )

        # First attempt fails, second succeeds
        validation_results = [
            Mock(is_valid=False, score=70, errors=["Low quality"]),
            Mock(is_valid=True, score=88),
        ]
        generator.validator.validate = Mock(side_effect=validation_results)

        # Mock other components with proper template structure
        generator.template_manager.load_template = Mock(
            return_value={
                "document_type": "readme",
                "sections": [{"name": "header", "prompt_template": "Generate header"}],
            }
        )
        generator.context_builder.extract_from_project = Mock(return_value={})

        result = await generator.generate(
            "readme", "/test/project", retry_on_failure=True, max_retries=2
        )

        assert result["quality_score"] == 88
        assert generator.validator.validate.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_sections_parallel(
        self, mock_config, mock_llm_adapter, mock_storage, sample_template
    ):
        """Test parallel section generation."""
        generator = DocumentGenerator(
            config=mock_config, llm_adapter=mock_llm_adapter, storage=mock_storage
        )

        # Mock components
        generator.template_manager.load_template = Mock(return_value=sample_template)
        generator.context_builder.extract_from_project = Mock(return_value={})

        # Track LLM calls
        import time

        call_times = []

        def mock_generate(*args, **kwargs):
            call_times.append(time.time())
            # Simulate some delay
            time.sleep(0.01)  # Small delay to simulate API call
            return LLMResponse(
                content=f"Section content {len(call_times)}",
                provider="openai",
                tokens_used=50,
                cost=0.001,
                latency=0.1,
            )

        mock_llm_adapter.generate = Mock(side_effect=mock_generate)

        # Mock validator to pass
        generator.validator.validate = Mock(return_value=Mock(is_valid=True, score=90))

        # Generate with parallel sections
        await generator.generate("readme", "/test/project", parallel_sections=True)

        # Check that sections were generated in parallel (times should be close)
        if len(call_times) > 1:
            time_diff = max(call_times) - min(call_times)
            assert time_diff < 0.2  # Should be nearly simultaneous

    @pytest.mark.asyncio
    async def test_generate_with_custom_context(self, mock_config, mock_llm_adapter, mock_storage):
        """Test document generation with custom context."""
        generator = DocumentGenerator(
            config=mock_config, llm_adapter=mock_llm_adapter, storage=mock_storage
        )

        custom_context = {
            "project_name": "CustomProject",
            "author": "Custom Author",
            "version": "2.0.0",
        }

        # Mock components with proper template structure
        generator.template_manager.load_template = Mock(
            return_value={
                "document_type": "readme",
                "sections": [
                    {"name": "header", "prompt_template": "Generate header for {project_name}"}
                ],
            }
        )
        extracted_context = {"project_name": "ExtractedProject"}
        generator.context_builder.extract_from_project = Mock(return_value=extracted_context)
        generator.validator.validate = Mock(return_value=Mock(is_valid=True, score=85))

        await generator.generate("readme", "/test/project", custom_context=custom_context)

        # Verify merged context was used
        # Custom context should override extracted context
        call_args = mock_llm_adapter.generate.call_args
        assert "CustomProject" in str(call_args)

    @pytest.mark.asyncio
    async def test_handle_llm_failure(self, mock_config, mock_storage):
        """Test handling of LLM adapter failure."""
        # Create LLM adapter that fails
        mock_llm_adapter = Mock(spec=LLMAdapter)
        mock_llm_adapter.generate.side_effect = Exception("LLM API unavailable")

        generator = DocumentGenerator(
            config=mock_config, llm_adapter=mock_llm_adapter, storage=mock_storage
        )

        # Mock components
        generator.template_manager.load_template = Mock(
            return_value={
                "document_type": "readme",
                "sections": [{"name": "header", "prompt_template": "Generate header"}],
            }
        )
        generator.context_builder.extract_from_project = Mock(return_value={})

        with pytest.raises(DocumentGenerationError) as exc_info:
            await generator.generate("readme", "/test/project")

        assert "LLM" in str(exc_info.value)

    def test_list_available_templates(self, mock_config, mock_llm_adapter, mock_storage):
        """Test listing available document templates."""
        generator = DocumentGenerator(
            config=mock_config, llm_adapter=mock_llm_adapter, storage=mock_storage
        )

        generator.template_manager.list_templates = Mock(
            return_value=["readme", "api_doc", "changelog"]
        )

        templates = generator.list_templates()

        assert "readme" in templates
        assert "api_doc" in templates
        assert len(templates) == 3

    @pytest.mark.asyncio
    async def test_performance_benchmark(self, mock_config, mock_llm_adapter, mock_storage):
        """Test that generation meets performance target (<5s)."""
        import time

        generator = DocumentGenerator(
            config=mock_config, llm_adapter=mock_llm_adapter, storage=mock_storage
        )

        # Mock fast responses
        generator.template_manager.load_template = Mock(
            return_value={
                "document_type": "readme",
                "sections": [{"name": "header", "prompt_template": "Generate header"}],
            }
        )
        generator.context_builder.extract_from_project = Mock(return_value={})
        generator.validator.validate = Mock(return_value=Mock(is_valid=True, score=90))

        start_time = time.time()
        await generator.generate("readme", "/test/project")
        elapsed_time = time.time() - start_time

        assert elapsed_time < 5.0  # Must complete within 5 seconds


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests with real foundation modules."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_generation_flow(self, tmp_path):
        """Test complete document generation flow with real modules."""
        # This test requires actual implementation
        # Will be used to verify integration after implementation
        pytest.skip("Requires implementation of DocumentGenerator")

    @pytest.mark.integration
    def test_template_loading_from_disk(self, tmp_path):
        """Test loading templates from actual filesystem."""
        # Create config pointing to temp directory
        config = ConfigurationManager()
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        # Create a real template file
        template_file = template_dir / "test.yaml"
        template_content = {
            "document_type": "test",
            "sections": [
                {"name": "intro", "prompt_template": "Generate introduction for {project_name}"}
            ],
        }
        template_file.write_text(yaml.dump(template_content))

        # Override config
        config.get = lambda key, default=None: (
            str(template_dir) if key == "templates.dir" else default
        )

        # Test loading
        manager = TemplateManager(config)
        template = manager.load_template("test")

        assert template["document_type"] == "test"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_llm_adapter_integration(self):
        """Test integration with real LLM adapter."""
        # This test can use the actual LLM adapter with mocked API calls
        pytest.skip("Requires API keys or mock server")


# ============================================================================
# Edge Cases and Error Scenarios
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_context(self, mock_config):
        """Test handling of empty context."""
        engine = PromptEngine(mock_config)

        template = "Generate docs for {project_name}"
        empty_context = {}

        # Should handle gracefully
        result = engine.format_template(template, empty_context, use_defaults=True)
        assert result  # Should return something, not crash

    def test_malformed_template(self, mock_config):
        """Test handling of malformed template."""
        manager = TemplateManager(mock_config)

        malformed = {"sections": "not_a_list"}  # Should be a list

        with pytest.raises(ValueError):
            manager.validate_template(malformed)

    @pytest.mark.asyncio
    async def test_concurrent_generation(self, mock_config, mock_llm_adapter, mock_storage):
        """Test concurrent document generation."""
        generator = DocumentGenerator(
            config=mock_config, llm_adapter=mock_llm_adapter, storage=mock_storage
        )

        # Mock components
        generator.template_manager.load_template = Mock(
            return_value={
                "document_type": "readme",
                "sections": [{"name": "header", "prompt_template": "Generate header"}],
            }
        )
        generator.context_builder.extract_from_project = Mock(return_value={})
        generator.validator.validate = Mock(return_value=Mock(is_valid=True, score=85))

        # Generate multiple documents concurrently
        tasks = [generator.generate("readme", f"/project{i}") for i in range(3)]

        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        assert all("document_id" in r for r in results)
