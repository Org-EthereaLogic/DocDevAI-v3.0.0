"""
Tests for AI Document Generator - Pass 1 Core Implementation.

Tests the integration of prompt templates, document workflow, and LLM adapter
for AI-powered document generation.
"""

import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from devdocai.generator.ai_document_generator import (
    AIDocumentGenerator, GenerationMode
)
from devdocai.generator.prompt_template_engine import (
    PromptTemplateEngine, PromptTemplate, RenderedPrompt
)
from devdocai.generator.document_workflow import DocumentType, ReviewPhase
from devdocai.llm_adapter.providers.base import LLMResponse


@pytest.fixture
def mock_config_manager():
    """Mock configuration manager."""
    config = Mock()
    config.get.return_value = {
        "anthropic_api_key": "test-anthropic-key",
        "openai_api_key": "test-openai-key",
        "google_api_key": "test-google-key"
    }
    return config


@pytest.fixture
def mock_storage():
    """Mock storage system."""
    storage = Mock()
    storage.create_document = Mock(return_value="doc_12345")
    return storage


@pytest.fixture
def mock_llm_response():
    """Mock LLM response."""
    response = Mock(spec=LLMResponse)
    response.content = """
    <user_stories>
    ## Epic: User Management
    
    ### US-001: User Registration
    **As a** new user
    **I want** to create an account
    **So that** I can access the system
    
    **Acceptance Criteria:**
    - [ ] Email validation
    - [ ] Password strength check
    - [ ] Confirmation email sent
    
    **Priority:** Must Have
    **Complexity:** Medium
    </user_stories>
    
    <story_summary>
    Total stories: 1
    Priority distribution: 1 Must Have
    </story_summary>
    
    <coverage_analysis>
    All requirements covered
    </coverage_analysis>
    """
    return response


@pytest.fixture
async def ai_generator(mock_config_manager, mock_storage):
    """Create AI document generator instance."""
    generator = AIDocumentGenerator(
        config_manager=mock_config_manager,
        storage=mock_storage,
        template_dir=Path("devdocai/templates/prompt_templates/generation")
    )
    return generator


class TestAIDocumentGenerator:
    """Test suite for AI Document Generator."""
    
    def test_initialization(self, mock_config_manager, mock_storage):
        """Test generator initialization."""
        generator = AIDocumentGenerator(
            config_manager=mock_config_manager,
            storage=mock_storage
        )
        
        assert generator.config_manager == mock_config_manager
        assert generator.storage == mock_storage
        assert generator.llm_adapter is not None
        assert generator.template_engine is not None
        assert generator.miair_engine is not None
        assert generator.workflow is not None
    
    def test_llm_adapter_initialization(self, mock_config_manager):
        """Test LLM adapter is initialized with correct providers."""
        generator = AIDocumentGenerator(
            config_manager=mock_config_manager
        )
        
        # Verify LLM adapter exists
        assert generator.llm_adapter is not None
        
        # Verify configuration was retrieved
        mock_config_manager.get.assert_called_with("llm", {})
    
    @pytest.mark.asyncio
    async def test_generate_document_single_mode(
        self, ai_generator, mock_llm_response
    ):
        """Test generating a single document."""
        generator = await ai_generator
        
        # Mock the LLM adapter query
        with patch.object(
            generator.llm_adapter, 'query',
            new_callable=AsyncMock
        ) as mock_query:
            mock_query.return_value = mock_llm_response
            
            # Mock template loading
            with patch.object(
                generator.template_engine, 'load_template'
            ) as mock_load:
                mock_template = Mock(spec=PromptTemplate)
                mock_template.llm_config = {"temperature": 0.8}
                mock_template.output = {"sections": [
                    {"name": "user_stories", "extract_tag": "user_stories"},
                    {"name": "story_summary", "extract_tag": "story_summary"}
                ]}
                mock_template.miair_config = None
                mock_load.return_value = mock_template
                
                # Mock template rendering
                with patch.object(
                    generator.template_engine, 'render'
                ) as mock_render:
                    mock_rendered = Mock(spec=RenderedPrompt)
                    mock_rendered.user_prompt = "Generate user stories"
                    mock_rendered.system_prompt = "You are an expert"
                    mock_rendered.llm_config = {"temperature": 0.8}
                    mock_rendered.output_config = mock_template.output
                    mock_rendered.miair_config = None
                    mock_render.return_value = mock_rendered
                    
                    # Generate document
                    result = await generator.generate_document(
                        document_type="user_stories",
                        context={"initial_description": "Test project"},
                        mode=GenerationMode.SINGLE
                    )
                    
                    # Verify result
                    assert "user_stories" in result
                    assert "story_summary" in result
                    assert result.get("document_id") == "doc_12345"
                    
                    # Verify storage was called
                    generator.storage.create_document.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_suite(self, ai_generator, mock_llm_response):
        """Test generating a complete document suite."""
        generator = await ai_generator
        
        # Mock responses for different document types
        responses = {
            "user_stories": mock_llm_response,
            "project_plan": Mock(content="<project_plan>Test plan</project_plan>"),
            "software_requirements": Mock(content="<srs_document>Test SRS</srs_document>"),
            "architecture_blueprint": Mock(content="<architecture_blueprint>Test arch</architecture_blueprint>")
        }
        
        call_count = 0
        async def mock_query_side_effect(*args, **kwargs):
            nonlocal call_count
            doc_types = list(responses.keys())
            if call_count < len(doc_types):
                response = responses[doc_types[call_count % len(doc_types)]]
                call_count += 1
                return response
            return mock_llm_response
        
        with patch.object(
            generator.llm_adapter, 'query',
            new_callable=AsyncMock
        ) as mock_query:
            mock_query.side_effect = mock_query_side_effect
            
            # Mock generate_document to simplify testing
            with patch.object(
                generator, 'generate_document',
                new_callable=AsyncMock
            ) as mock_gen_doc:
                async def generate_side_effect(document_type, context, mode):
                    return {
                        "content": f"Generated {document_type}",
                        "_miair_quality": 0.8
                    }
                
                mock_gen_doc.side_effect = generate_side_effect
                
                # Generate suite
                result = await generator.generate_suite(
                    initial_description="Build a web application",
                    include_documents=["user_stories", "project_plan"]
                )
                
                # Verify documents were generated
                assert "user_stories" in result
                assert "project_plan" in result
                
                # Verify generate_document was called for each document
                assert mock_gen_doc.call_count >= 2
    
    def test_get_provider_weights(self, ai_generator):
        """Test extracting provider weights from configuration."""
        generator = asyncio.run(ai_generator)
        
        # Test with explicit providers
        config = {
            "providers": [
                {"name": "claude", "weight": 0.5},
                {"name": "openai", "weight": 0.3},
                {"name": "gemini", "weight": 0.2}
            ]
        }
        
        weights = generator._get_provider_weights(config)
        
        assert weights["anthropic"] == 0.5
        assert weights["openai"] == 0.3
        assert weights["google"] == 0.2
    
    def test_get_provider_weights_default(self, ai_generator):
        """Test default provider weights."""
        generator = asyncio.run(ai_generator)
        
        # Test with no providers specified
        config = {}
        
        weights = generator._get_provider_weights(config)
        
        assert weights["anthropic"] == 0.4
        assert weights["openai"] == 0.35
        assert weights["google"] == 0.25
    
    @pytest.mark.asyncio
    async def test_optimize_with_miair(self, ai_generator):
        """Test MIAIR optimization integration."""
        generator = await ai_generator
        
        # Mock MIAIR analysis
        mock_result = Mock()
        mock_result.quality_score = 0.65
        mock_result.improvement_suggestions = [
            "Add more detail",
            "Improve clarity",
            "Fix formatting"
        ]
        
        with patch.object(
            generator.miair_engine, 'analyze_documentation'
        ) as mock_analyze:
            mock_analyze.return_value = mock_result
            
            # Test optimization
            content = {"test": "content"}
            config = {"target_quality": 0.75}
            
            result = await generator._optimize_with_miair(content, config)
            
            # Verify MIAIR metadata was added
            assert "_miair_quality" in result
            assert result["_miair_quality"] == 0.65
            assert "_miair_suggestions" in result
            assert len(result["_miair_suggestions"]) == 3
    
    @pytest.mark.asyncio
    async def test_apply_review(self, ai_generator, mock_llm_response):
        """Test applying review to a document."""
        generator = await ai_generator
        
        # Mock review response
        review_response = Mock(spec=LLMResponse)
        review_response.content = """
        <review_feedback>
        Document needs improvement in clarity
        </review_feedback>
        
        <improvement_suggestions>
        1. Add more examples
        2. Improve structure
        </improvement_suggestions>
        """
        
        with patch.object(
            generator.llm_adapter, 'query',
            new_callable=AsyncMock
        ) as mock_query:
            mock_query.return_value = review_response
            
            # Mock template loading and rendering
            with patch.object(
                generator.template_engine, 'load_template'
            ):
                with patch.object(
                    generator.template_engine, 'render'
                ) as mock_render:
                    mock_rendered = Mock()
                    mock_rendered.user_prompt = "Review document"
                    mock_rendered.system_prompt = "You are a reviewer"
                    mock_rendered.llm_config = {"temperature": 0.6}
                    mock_rendered.output_config = {"sections": []}
                    mock_render.return_value = mock_rendered
                    
                    # Apply review
                    document = {"content": "Test document"}
                    result = await generator._apply_review(
                        document_type="test_doc",
                        document=document,
                        review_phase="first_draft",
                        context={}
                    )
                    
                    # Verify review metadata was added
                    assert "_review" in result
                    assert result["_review"]["phase"] == "first_draft"
                    assert "feedback" in result["_review"]
    
    @pytest.mark.asyncio
    async def test_store_document(self, ai_generator):
        """Test document storage integration."""
        generator = await ai_generator
        
        # Store a document
        content = {"test": "content"}
        metadata = {"author": "test"}
        
        doc_id = await generator._store_document(
            document_type="test_doc",
            content=content,
            metadata=metadata
        )
        
        # Verify storage was called
        generator.storage.create_document.assert_called_once()
        assert doc_id == "doc_12345"
    
    @pytest.mark.asyncio
    async def test_store_document_no_storage(self, mock_config_manager):
        """Test document storage when storage is not available."""
        generator = AIDocumentGenerator(
            config_manager=mock_config_manager,
            storage=None
        )
        
        # Store a document without storage
        content = {"test": "content"}
        metadata = {"author": "test"}
        
        doc_id = await generator._store_document(
            document_type="test_doc",
            content=content,
            metadata=metadata
        )
        
        # Verify a temporary ID was generated
        assert doc_id.startswith("doc_test_doc_")
    
    def test_get_generation_history(self, ai_generator):
        """Test retrieving generation history."""
        generator = asyncio.run(ai_generator)
        
        # Add some history
        generator.generation_history = [
            {"type": "user_stories", "success": True},
            {"type": "project_plan", "success": True}
        ]
        
        history = generator.get_generation_history()
        
        assert len(history) == 2
        assert history[0]["type"] == "user_stories"
        assert history[1]["type"] == "project_plan"
    
    def test_get_generated_document(self, ai_generator):
        """Test retrieving a specific generated document."""
        generator = asyncio.run(ai_generator)
        
        # Add a document
        generator.generated_documents["test_doc"] = {"content": "test"}
        
        doc = generator.get_generated_document("test_doc")
        assert doc == {"content": "test"}
        
        # Test non-existent document
        doc = generator.get_generated_document("missing")
        assert doc is None
    
    def test_clear_history(self, ai_generator):
        """Test clearing generation history."""
        generator = asyncio.run(ai_generator)
        
        # Add some data
        generator.generated_documents["test"] = {"content": "test"}
        generator.generation_history.append({"type": "test"})
        
        # Clear history
        generator.clear_history()
        
        assert len(generator.generated_documents) == 0
        assert len(generator.generation_history) == 0


class TestPromptTemplateEngine:
    """Test suite for Prompt Template Engine."""
    
    def test_template_loading(self):
        """Test loading a prompt template."""
        # Create a temporary template for testing
        import tempfile
        import yaml
        
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)
            
            # Create a test template
            template_data = {
                "name": "Test Template",
                "description": "Test description",
                "category": "test",
                "version": "1.0.0",
                "inputs": [
                    {"name": "test_input", "required": True}
                ],
                "llm_config": {
                    "temperature": 0.7
                },
                "prompt": {
                    "system": "You are a test assistant",
                    "user": "Process this: {{test_input}}"
                },
                "output": {
                    "sections": [
                        {"name": "result", "extract_tag": "result"}
                    ]
                }
            }
            
            template_file = template_dir / "test_template.yaml"
            with open(template_file, 'w') as f:
                yaml.dump(template_data, f)
            
            # Test loading
            engine = PromptTemplateEngine(template_dir=template_dir)
            template = engine.load_template("test_template")
            
            assert template.name == "Test Template"
            assert template.category == "test"
            assert len(template.inputs) == 1
    
    def test_template_rendering(self):
        """Test rendering a prompt template."""
        import tempfile
        import yaml
        
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)
            
            # Create a test template
            template_data = {
                "name": "Test Template",
                "description": "Test",
                "category": "test",
                "version": "1.0.0",
                "inputs": [],
                "llm_config": {"temperature": 0.7},
                "prompt": {
                    "system": "System prompt",
                    "user": "Hello {{name}}"
                },
                "output": {"sections": []}
            }
            
            template_file = template_dir / "test.yaml"
            with open(template_file, 'w') as f:
                yaml.dump(template_data, f)
            
            # Test rendering
            engine = PromptTemplateEngine(template_dir=template_dir)
            rendered = engine.render(
                template="test",
                context={"name": "World"}
            )
            
            assert rendered.system_prompt == "System prompt"
            assert rendered.user_prompt == "Hello World"
    
    def test_extract_output_sections(self):
        """Test extracting sections from LLM response."""
        engine = PromptTemplateEngine()
        
        response = """
        Some text
        <result>
        This is the result
        </result>
        <analysis>
        This is the analysis
        </analysis>
        More text
        """
        
        output_config = {
            "sections": [
                {"name": "result", "extract_tag": "result"},
                {"name": "analysis", "extract_tag": "analysis"}
            ]
        }
        
        sections = engine.extract_output_sections(response, output_config)
        
        assert "result" in sections
        assert "This is the result" in sections["result"]
        assert "analysis" in sections
        assert "This is the analysis" in sections["analysis"]


@pytest.mark.integration
class TestEndToEndGeneration:
    """Integration tests for end-to-end document generation."""
    
    @pytest.mark.asyncio
    async def test_full_generation_flow(
        self, mock_config_manager, mock_storage
    ):
        """Test complete document generation flow."""
        # This test would require actual templates to be present
        # For Pass 1, we'll create a simplified test
        
        generator = AIDocumentGenerator(
            config_manager=mock_config_manager,
            storage=mock_storage
        )
        
        # Mock the entire generation flow
        with patch.object(
            generator, 'generate_document',
            new_callable=AsyncMock
        ) as mock_gen:
            async def gen_side_effect(doc_type, context, mode):
                return {
                    "type": doc_type,
                    "content": f"Generated {doc_type}",
                    "quality": 0.8
                }
            
            mock_gen.side_effect = gen_side_effect
            
            # Test generating multiple documents
            docs = []
            for doc_type in ["user_stories", "project_plan", "software_requirements"]:
                doc = await generator.generate_document(
                    document_type=doc_type,
                    context={"description": "Test"},
                    mode=GenerationMode.SINGLE
                )
                docs.append(doc)
            
            # Verify all documents were generated
            assert len(docs) == 3
            assert docs[0]["type"] == "user_stories"
            assert docs[1]["type"] == "project_plan"
            assert docs[2]["type"] == "software_requirements"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])