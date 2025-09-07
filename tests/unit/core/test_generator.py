"""
M004 Document Generator - Pass 1: Test Suite (TDD Approach)

Comprehensive test suite for UnifiedDocumentGenerator following TDD methodology.
Tests cover all operation modes, document types, output formats, and integrations.
"""

import pytest
import json
import tempfile
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from typing import Dict, Any, Optional

# Import modules to test
from devdocai.core.generator import (
    UnifiedDocumentGenerator,
    DocumentType,
    OutputFormat,
    GenerationMode,
    GeneratorError,
    DocumentMetadata,
    GenerationResult,
    TemplateVariable
)
from devdocai.core.config import ConfigurationManager, MemoryMode
from devdocai.storage.storage_manager_unified import UnifiedStorageManager, OperationMode
from devdocai.miair.engine_unified_final import MIAIREngineUnified
from devdocai.miair.models import QualityScore, AnalysisResult


class TestUnifiedDocumentGenerator:
    """Test suite for UnifiedDocumentGenerator."""
    
    @pytest.fixture
    def mock_config_manager(self):
        """Create mock configuration manager."""
        mock = Mock(spec=ConfigurationManager)
        # Mock the get method to return appropriate values
        def get_side_effect(key, default=None):
            values = {
                'operation_mode': 'basic',
                'quality_gate_threshold': 85.0,
                'max_document_size_mb': 10,
                'enable_caching': False,
                'memory_mode': MemoryMode.STANDARD,
                'template_directory': '/templates'
            }
            return values.get(key, default)
        
        mock.get.side_effect = get_side_effect
        return mock
    
    @pytest.fixture
    def mock_storage_manager(self):
        """Create mock storage manager."""
        mock = Mock()
        
        # Mock document with template data
        template_doc = Mock()
        template_doc.content = '# {{ title }}\n\n{{ description }}'
        template_doc.metadata = {'variables': ['title', 'description']}
        
        # Mock get_document to return template
        mock.get_document.return_value = template_doc
        
        # Mock create_document
        mock.create_document.return_value = Mock(id='doc123')
        
        return mock
    
    @pytest.fixture
    def mock_miair_engine(self):
        """Create mock MIAIR engine."""
        mock = Mock(spec=MIAIREngineUnified)
        
        # Create a proper QualityScore object with all required fields
        quality_score = QualityScore(
            overall=90.0,
            completeness=92.0,
            clarity=88.0,
            consistency=89.0,
            structure=91.0,
            technical_accuracy=90.0,
            grammar=89.0
        )
        
        # Create AnalysisResult with the quality score
        analysis_result = AnalysisResult(
            entropy=4.5,
            quality_score=quality_score,
            semantic_elements=[],
            improvement_potential=10.0,
            meets_quality_gate=True,
            patterns={}
        )
        
        # Make analyze_document return async result
        async def mock_analyze():
            return analysis_result
        
        mock.analyze_document = AsyncMock(return_value=analysis_result)
        return mock
    
    @pytest.fixture
    def generator(self, mock_config_manager, mock_storage_manager, mock_miair_engine):
        """Create document generator instance."""
        return UnifiedDocumentGenerator(
            config_manager=mock_config_manager,
            storage_manager=mock_storage_manager,
            miair_engine=mock_miair_engine
        )
    
    # Test initialization and configuration
    
    def test_initialization_basic_mode(self, mock_config_manager, mock_storage_manager, mock_miair_engine):
        """Test generator initialization in BASIC mode."""
        # Already set to 'basic' in fixture
        
        generator = UnifiedDocumentGenerator(
            mock_config_manager,
            mock_storage_manager,
            mock_miair_engine
        )
        
        assert generator.mode == GenerationMode.BASIC
        assert generator.config_manager == mock_config_manager
        assert generator.storage_manager == mock_storage_manager
        assert generator.miair_engine == mock_miair_engine
        assert generator.jinja_env is not None
        assert generator.jinja_env.autoescape == True  # Security: auto-escaping enabled
    
    def test_initialization_performance_mode(self, mock_config_manager, mock_storage_manager, mock_miair_engine):
        """Test generator initialization in PERFORMANCE mode."""
        # Update mock to return performance mode
        def get_side_effect(key, default=None):
            values = {
                'operation_mode': 'performance',
                'quality_gate_threshold': 85.0,
                'max_document_size_mb': 10,
                'enable_caching': True,
                'memory_mode': MemoryMode.PERFORMANCE,
                'template_directory': '/templates'
            }
            return values.get(key, default)
        
        mock_config_manager.get.side_effect = get_side_effect
        
        generator = UnifiedDocumentGenerator(
            mock_config_manager,
            mock_storage_manager,
            mock_miair_engine
        )
        
        assert generator.mode == GenerationMode.PERFORMANCE
        assert generator.cache is not None  # Cache enabled in performance mode
        assert generator.enable_parallel is True
    
    def test_initialization_secure_mode(self, mock_config_manager, mock_storage_manager, mock_miair_engine):
        """Test generator initialization in SECURE mode."""
        # Update mock to return secure mode
        def get_side_effect(key, default=None):
            values = {
                'operation_mode': 'secure',
                'quality_gate_threshold': 85.0,
                'max_document_size_mb': 10,
                'enable_caching': False,
                'memory_mode': MemoryMode.STANDARD,
                'template_directory': '/templates'
            }
            return values.get(key, default)
        
        mock_config_manager.get.side_effect = get_side_effect
        
        generator = UnifiedDocumentGenerator(
            mock_config_manager,
            mock_storage_manager,
            mock_miair_engine
        )
        
        assert generator.mode == GenerationMode.SECURE
        assert generator.enable_security_validation is True
        assert generator.jinja_env.sandboxed is True  # Sandboxed environment for security
    
    def test_initialization_enterprise_mode(self, mock_config_manager, mock_storage_manager, mock_miair_engine):
        """Test generator initialization in ENTERPRISE mode."""
        # Update mock to return enterprise mode
        def get_side_effect(key, default=None):
            values = {
                'operation_mode': 'enterprise',
                'quality_gate_threshold': 85.0,
                'max_document_size_mb': 10,
                'enable_caching': True,
                'memory_mode': MemoryMode.PERFORMANCE,
                'template_directory': '/templates'
            }
            return values.get(key, default)
        
        mock_config_manager.get.side_effect = get_side_effect
        
        generator = UnifiedDocumentGenerator(
            mock_config_manager,
            mock_storage_manager,
            mock_miair_engine
        )
        
        assert generator.mode == GenerationMode.ENTERPRISE
        assert generator.enable_ai_enhancement is True
        assert generator.cache is not None
        assert generator.enable_parallel is True
        assert generator.enable_security_validation is True
    
    # Test document generation
    
    @pytest.mark.asyncio
    async def test_generate_readme_document(self, generator, mock_storage_manager):
        """Test generating a README document."""
        variables = {
            'title': 'DevDocAI',
            'description': 'AI-powered documentation generator',
            'features': ['Fast', 'Secure', 'Scalable'],
            'installation': 'pip install devdocai',
            'usage': 'devdocai generate README'
        }
        
        result = await generator.generate_document(
            doc_type=DocumentType.README,
            template_id='readme_template',
            variables=variables,
            output_format=OutputFormat.MARKDOWN
        )
        
        assert result.success is True
        assert result.document_id is not None
        assert result.content is not None
        assert '# DevDocAI' in result.content
        assert result.quality_score >= 85.0  # Meets quality gate
        assert result.format == OutputFormat.MARKDOWN
        mock_storage_manager.create_document.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_api_document(self, generator):
        """Test generating an API documentation."""
        variables = {
            'api_title': 'DevDocAI API',
            'version': 'v1.0.0',
            'base_url': 'https://api.devdocai.com',
            'endpoints': [
                {'method': 'GET', 'path': '/generate', 'description': 'Generate document'},
                {'method': 'POST', 'path': '/analyze', 'description': 'Analyze quality'}
            ]
        }
        
        result = await generator.generate_document(
            doc_type=DocumentType.API,
            template_id='api_template',
            variables=variables,
            output_format=OutputFormat.MARKDOWN
        )
        
        assert result.success is True
        assert 'DevDocAI API' in result.content
        assert 'v1.0.0' in result.content
        assert result.metadata['document_type'] == DocumentType.API.value
    
    @pytest.mark.asyncio
    async def test_generate_prd_document(self, generator):
        """Test generating a Product Requirements Document."""
        variables = {
            'product_name': 'DevDocAI',
            'vision': 'Revolutionize documentation',
            'objectives': ['Automate docs', 'Ensure quality', 'Save time'],
            'target_users': 'Developers',
            'requirements': ['Must generate docs', 'Must analyze quality']
        }
        
        result = await generator.generate_document(
            doc_type=DocumentType.PRD,
            template_id='prd_template',
            variables=variables,
            output_format=OutputFormat.MARKDOWN
        )
        
        assert result.success is True
        assert 'Product Requirements' in result.content
        assert 'DevDocAI' in result.content
    
    @pytest.mark.asyncio
    async def test_generate_srs_document(self, generator):
        """Test generating a Software Requirements Specification."""
        variables = {
            'system_name': 'DevDocAI',
            'functional_requirements': ['Generate docs', 'Analyze quality'],
            'non_functional_requirements': ['Performance', 'Security', 'Scalability'],
            'constraints': ['Python 3.8+', 'SQLite database']
        }
        
        result = await generator.generate_document(
            doc_type=DocumentType.SRS,
            template_id='srs_template',
            variables=variables,
            output_format=OutputFormat.MARKDOWN
        )
        
        assert result.success is True
        assert 'Software Requirements' in result.content
    
    @pytest.mark.asyncio
    async def test_generate_sdd_document(self, generator):
        """Test generating a Software Design Document."""
        variables = {
            'system_name': 'DevDocAI',
            'architecture': 'Modular microservices',
            'modules': ['M001', 'M002', 'M003'],
            'design_patterns': ['Strategy', 'Factory', 'Observer'],
            'technology_stack': ['Python', 'SQLite', 'Jinja2']
        }
        
        result = await generator.generate_document(
            doc_type=DocumentType.SDD,
            template_id='sdd_template',
            variables=variables,
            output_format=OutputFormat.MARKDOWN
        )
        
        assert result.success is True
        assert 'Software Design' in result.content
        assert 'Architecture' in result.content
    
    # Test output formats
    
    @pytest.mark.asyncio
    async def test_generate_html_output(self, generator):
        """Test generating HTML output."""
        variables = {'title': 'Test', 'content': 'Test content'}
        
        result = await generator.generate_document(
            doc_type=DocumentType.README,
            template_id='readme_template',
            variables=variables,
            output_format=OutputFormat.HTML
        )
        
        assert result.success is True
        assert result.format == OutputFormat.HTML
        assert '<html>' in result.content or '<!DOCTYPE' in result.content
        assert '<h1>' in result.content  # Markdown converted to HTML
    
    @pytest.mark.asyncio
    async def test_generate_pdf_output(self, generator):
        """Test generating PDF output."""
        variables = {'title': 'Test', 'content': 'Test content'}
        
        result = await generator.generate_document(
            doc_type=DocumentType.README,
            template_id='readme_template',
            variables=variables,
            output_format=OutputFormat.PDF
        )
        
        assert result.success is True
        assert result.format == OutputFormat.PDF
        assert result.content.startswith(b'%PDF')  # PDF header
    
    @pytest.mark.asyncio
    async def test_generate_docx_output(self, generator):
        """Test generating DOCX output."""
        variables = {'title': 'Test', 'content': 'Test content'}
        
        result = await generator.generate_document(
            doc_type=DocumentType.README,
            template_id='readme_template',
            variables=variables,
            output_format=OutputFormat.DOCX
        )
        
        assert result.success is True
        assert result.format == OutputFormat.DOCX
        assert result.content.startswith(b'PK')  # DOCX is a zip file
    
    # Test quality gate enforcement
    
    @pytest.mark.asyncio
    async def test_quality_gate_enforcement(self, generator, mock_miair_engine):
        """Test that documents failing quality gate are rejected."""
        # Mock low quality score
        low_quality = QualityScore(
            overall=70.0,  # Below 85% threshold
            completeness=70.0,
            clarity=70.0,
            consistency=70.0,
            structure=70.0,
            technical_accuracy=70.0,
            grammar=70.0
        )
        
        mock_miair_engine.analyze_document.return_value = AnalysisResult(
            entropy=3.0,
            quality_score=low_quality,
            semantic_elements=[],
            improvement_potential=30.0,
            meets_quality_gate=False,
            patterns={}
        )
        
        variables = {'title': 'Low Quality', 'content': 'Bad'}
        
        with pytest.raises(GeneratorError) as exc_info:
            await generator.generate_document(
                doc_type=DocumentType.README,
                template_id='readme_template',
                variables=variables,
                output_format=OutputFormat.MARKDOWN
            )
        
        assert 'quality gate' in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_quality_gate_bypass_option(self, generator, mock_miair_engine):
        """Test bypassing quality gate when explicitly requested."""
        # Mock low quality score
        low_quality = QualityScore(
            overall=70.0,
            completeness=70.0,
            clarity=70.0,
            consistency=70.0,
            structure=70.0,
            technical_accuracy=70.0,
            grammar=70.0
        )
        
        mock_miair_engine.analyze_document.return_value = AnalysisResult(
            entropy=3.0,
            quality_score=low_quality,
            semantic_elements=[],
            improvement_potential=30.0,
            meets_quality_gate=False,
            patterns={}
        )
        
        variables = {'title': 'Low Quality', 'content': 'Bad'}
        
        result = await generator.generate_document(
            doc_type=DocumentType.README,
            template_id='readme_template',
            variables=variables,
            output_format=OutputFormat.MARKDOWN,
            enforce_quality_gate=False  # Bypass quality gate
        )
        
        assert result.success is True
        assert result.quality_score == 70.0
        assert result.warnings is not None
        assert 'quality gate' in result.warnings[0].lower()
    
    # Test caching in performance mode
    
    @pytest.mark.asyncio
    async def test_caching_in_performance_mode(self, mock_config_manager, mock_storage_manager, mock_miair_engine):
        """Test that caching works in PERFORMANCE mode."""
        # Update mock to return performance mode
        def get_side_effect(key, default=None):
            values = {
                'operation_mode': 'performance',
                'quality_gate_threshold': 85.0,
                'max_document_size_mb': 10,
                'enable_caching': True,
                'memory_mode': MemoryMode.PERFORMANCE,
                'template_directory': '/templates'
            }
            return values.get(key, default)
        
        mock_config_manager.get.side_effect = get_side_effect
        
        generator = UnifiedDocumentGenerator(
            mock_config_manager,
            mock_storage_manager,
            mock_miair_engine
        )
        
        variables = {'title': 'Cached', 'content': 'Test caching'}
        
        # First generation
        result1 = await generator.generate_document(
            doc_type=DocumentType.README,
            template_id='readme_template',
            variables=variables,
            output_format=OutputFormat.MARKDOWN
        )
        
        # Second generation with same parameters (should hit cache)
        result2 = await generator.generate_document(
            doc_type=DocumentType.README,
            template_id='readme_template',
            variables=variables,
            output_format=OutputFormat.MARKDOWN
        )
        
        assert result1.document_id == result2.document_id
        assert result1.content == result2.content
        # Storage should only be called once due to caching
        assert mock_storage_manager.create_document.call_count == 1
    
    # Test security validation in secure mode
    
    @pytest.mark.asyncio
    async def test_security_validation_secure_mode(self, mock_config_manager, mock_storage_manager, mock_miair_engine):
        """Test security validation in SECURE mode."""
        # Update mock to return secure mode
        def get_side_effect(key, default=None):
            values = {
                'operation_mode': 'secure',
                'quality_gate_threshold': 85.0,
                'max_document_size_mb': 10,
                'enable_caching': False,
                'memory_mode': MemoryMode.STANDARD,
                'template_directory': '/templates'
            }
            return values.get(key, default)
        
        mock_config_manager.get.side_effect = get_side_effect
        
        generator = UnifiedDocumentGenerator(
            mock_config_manager,
            mock_storage_manager,
            mock_miair_engine
        )
        
        # Attempt to inject malicious code
        malicious_variables = {
            'title': '{{ __import__("os").system("rm -rf /") }}',  # Attempted code injection
            'content': '<script>alert("XSS")</script>'  # XSS attempt
        }
        
        with pytest.raises(GeneratorError) as exc_info:
            await generator.generate_document(
                doc_type=DocumentType.README,
                template_id='readme_template',
                variables=malicious_variables,
                output_format=OutputFormat.MARKDOWN
            )
        
        assert 'security' in str(exc_info.value).lower()
    
    # Test parallel processing in performance mode
    
    @pytest.mark.asyncio
    async def test_parallel_batch_generation(self, mock_config_manager, mock_storage_manager, mock_miair_engine):
        """Test parallel batch document generation in PERFORMANCE mode."""
        # Update mock to return performance mode
        def get_side_effect(key, default=None):
            values = {
                'operation_mode': 'performance',
                'quality_gate_threshold': 85.0,
                'max_document_size_mb': 10,
                'enable_caching': True,
                'memory_mode': MemoryMode.PERFORMANCE,
                'template_directory': '/templates'
            }
            return values.get(key, default)
        
        mock_config_manager.get.side_effect = get_side_effect
        
        generator = UnifiedDocumentGenerator(
            mock_config_manager,
            mock_storage_manager,
            mock_miair_engine
        )
        
        # Generate multiple documents in batch
        batch_requests = [
            {
                'doc_type': DocumentType.README,
                'template_id': 'readme_template',
                'variables': {'title': f'Doc {i}', 'content': f'Content {i}'},
                'output_format': OutputFormat.MARKDOWN
            }
            for i in range(5)
        ]
        
        results = await generator.generate_batch(batch_requests)
        
        assert len(results) == 5
        assert all(r.success for r in results)
        assert all(r.quality_score >= 85.0 for r in results)
    
    # Test error handling
    
    @pytest.mark.asyncio
    async def test_invalid_template_error(self, generator, mock_storage_manager):
        """Test error handling for invalid template."""
        mock_storage_manager.get_template.side_effect = Exception("Template not found")
        
        with pytest.raises(GeneratorError) as exc_info:
            await generator.generate_document(
                doc_type=DocumentType.README,
                template_id='invalid_template',
                variables={'title': 'Test'},
                output_format=OutputFormat.MARKDOWN
            )
        
        assert 'template' in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_missing_required_variables(self, generator):
        """Test error handling for missing required template variables."""
        # Missing 'description' variable
        incomplete_variables = {'title': 'Test Only'}
        
        with pytest.raises(GeneratorError) as exc_info:
            await generator.generate_document(
                doc_type=DocumentType.README,
                template_id='readme_template',
                variables=incomplete_variables,
                output_format=OutputFormat.MARKDOWN
            )
        
        assert 'variable' in str(exc_info.value).lower()
    
    # Test performance benchmarks
    
    @pytest.mark.asyncio
    async def test_performance_baseline(self, generator):
        """Test that generator meets 10 docs/second baseline performance."""
        import time
        
        variables = {'title': 'Perf Test', 'content': 'Performance testing'}
        
        start_time = time.perf_counter()
        
        # Generate 10 documents
        for i in range(10):
            result = await generator.generate_document(
                doc_type=DocumentType.README,
                template_id='readme_template',
                variables={'title': f'Doc {i}', 'content': f'Content {i}'},
                output_format=OutputFormat.MARKDOWN
            )
            assert result.success is True
        
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        
        # Should generate 10 docs in <= 1 second (10 docs/second)
        assert elapsed <= 1.5  # Allow some margin for test environment
        
        docs_per_second = 10 / elapsed
        assert docs_per_second >= 6.67  # At least 2/3 of target for test environment
    
    # Test template validation
    
    def test_validate_template_variables(self, generator):
        """Test template variable validation."""
        template = '# {{ title }}\n{{ description }}\n{% for item in items %}{{ item }}{% endfor %}'
        
        required_vars = generator._extract_template_variables(template)
        
        assert 'title' in required_vars
        assert 'description' in required_vars
        assert 'items' in required_vars
    
    def test_sanitize_user_input(self, generator):
        """Test user input sanitization."""
        malicious_input = '<script>alert("XSS")</script>'
        
        sanitized = generator._sanitize_input(malicious_input)
        
        assert '<script>' not in sanitized
        assert '&lt;script&gt;' in sanitized or sanitized == ''  # Escaped or removed
    
    # Test integration with M001, M002, M003
    
    @pytest.mark.asyncio
    async def test_m001_integration(self, generator, mock_config_manager):
        """Test integration with M001 Configuration Manager."""
        variables = {'title': 'M001 Test', 'content': 'Integration test'}
        
        result = await generator.generate_document(
            doc_type=DocumentType.README,
            template_id='readme_template',
            variables=variables,
            output_format=OutputFormat.MARKDOWN
        )
        
        assert result.success is True
        # Check that config_manager.get was called
        mock_config_manager.get.assert_called()
    
    @pytest.mark.asyncio
    async def test_m002_integration(self, generator, mock_storage_manager):
        """Test integration with M002 Storage Manager."""
        variables = {'title': 'M002 Test', 'content': 'Storage test'}
        
        result = await generator.generate_document(
            doc_type=DocumentType.README,
            template_id='readme_template',
            variables=variables,
            output_format=OutputFormat.MARKDOWN
        )
        
        assert result.success is True
        mock_storage_manager.get_template.assert_called_with('readme_template')
        mock_storage_manager.create_document.assert_called()
    
    @pytest.mark.asyncio
    async def test_m003_integration(self, generator, mock_miair_engine):
        """Test integration with M003 MIAIR Engine."""
        variables = {'title': 'M003 Test', 'content': 'Quality test'}
        
        result = await generator.generate_document(
            doc_type=DocumentType.README,
            template_id='readme_template',
            variables=variables,
            output_format=OutputFormat.MARKDOWN
        )
        
        assert result.success is True
        assert result.quality_score == 90.0  # From mock
        mock_miair_engine.analyze_document.assert_called()
    
    # Test document metadata
    
    @pytest.mark.asyncio
    async def test_document_metadata_generation(self, generator):
        """Test that proper metadata is generated for documents."""
        variables = {'title': 'Meta Test', 'content': 'Metadata testing'}
        
        result = await generator.generate_document(
            doc_type=DocumentType.README,
            template_id='readme_template',
            variables=variables,
            output_format=OutputFormat.MARKDOWN
        )
        
        assert result.metadata is not None
        assert result.metadata['document_type'] == DocumentType.README.value
        assert result.metadata['format'] == OutputFormat.MARKDOWN.value
        assert 'created_at' in result.metadata
        assert 'version' in result.metadata
        assert result.metadata['quality_score'] == result.quality_score
    
    # Test custom templates
    
    @pytest.mark.asyncio
    async def test_custom_template_registration(self, generator):
        """Test registering and using custom templates."""
        custom_template = """
        # {{ project_name }}
        
        ## Overview
        {{ overview }}
        
        ## Features
        {% for feature in features %}
        - {{ feature }}
        {% endfor %}
        """
        
        # Register custom template
        template_id = await generator.register_template(
            name="Custom Project Template",
            content=custom_template,
            category="custom",
            variables=['project_name', 'overview', 'features']
        )
        
        # Use custom template
        variables = {
            'project_name': 'My Project',
            'overview': 'This is a custom project',
            'features': ['Feature 1', 'Feature 2', 'Feature 3']
        }
        
        result = await generator.generate_document(
            doc_type=DocumentType.README,
            template_id=template_id,
            variables=variables,
            output_format=OutputFormat.MARKDOWN
        )
        
        assert result.success is True
        assert 'My Project' in result.content
        assert 'Feature 1' in result.content


class TestGeneratorPerformance:
    """Performance-specific tests for document generator."""
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_throughput_10_docs_per_second(self, mock_config_manager, mock_storage_manager, mock_miair_engine):
        """Benchmark test for 10 docs/second throughput."""
        generator = UnifiedDocumentGenerator(
            mock_config_manager,
            mock_storage_manager,
            mock_miair_engine
        )
        
        import time
        
        num_docs = 100
        start_time = time.perf_counter()
        
        tasks = []
        for i in range(num_docs):
            task = generator.generate_document(
                doc_type=DocumentType.README,
                template_id='readme_template',
                variables={'title': f'Doc {i}', 'content': f'Content {i}'},
                output_format=OutputFormat.MARKDOWN
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        
        docs_per_second = num_docs / elapsed
        
        assert all(r.success for r in results)
        assert docs_per_second >= 10.0  # Meet baseline requirement
        
        print(f"Performance: {docs_per_second:.2f} docs/second")
    
    @pytest.mark.asyncio
    async def test_large_document_handling(self, mock_config_manager, mock_storage_manager, mock_miair_engine):
        """Test handling of large documents."""
        generator = UnifiedDocumentGenerator(
            mock_config_manager,
            mock_storage_manager,
            mock_miair_engine
        )
        
        # Create large content (1MB+)
        large_content = 'A' * (1024 * 1024)  # 1MB of text
        
        variables = {
            'title': 'Large Document',
            'content': large_content
        }
        
        result = await generator.generate_document(
            doc_type=DocumentType.README,
            template_id='readme_template',
            variables=variables,
            output_format=OutputFormat.MARKDOWN
        )
        
        assert result.success is True
        assert len(result.content) > 1024 * 1024  # At least 1MB


class TestGeneratorSecurity:
    """Security-specific tests for document generator."""
    
    @pytest.mark.asyncio
    async def test_template_injection_prevention(self, mock_config_manager, mock_storage_manager, mock_miair_engine):
        """Test prevention of template injection attacks."""
        # Update mock to return secure mode
        def get_side_effect(key, default=None):
            values = {
                'operation_mode': 'secure',
                'quality_gate_threshold': 85.0,
                'max_document_size_mb': 10,
                'enable_caching': False,
                'memory_mode': MemoryMode.STANDARD,
                'template_directory': '/templates'
            }
            return values.get(key, default)
        
        mock_config_manager.get.side_effect = get_side_effect
        
        generator = UnifiedDocumentGenerator(
            mock_config_manager,
            mock_storage_manager,
            mock_miair_engine
        )
        
        # Various injection attempts
        injection_attempts = [
            "{{ __import__('os').system('ls') }}",
            "{% for item in __builtins__ %}{{ item }}{% endfor %}",
            "{{ ''.__class__.__mro__[1].__subclasses__() }}",
            "{% include '/etc/passwd' %}"
        ]
        
        for injection in injection_attempts:
            with pytest.raises(GeneratorError) as exc_info:
                await generator.generate_document(
                    doc_type=DocumentType.README,
                    template_id='readme_template',
                    variables={'title': injection, 'content': 'test'},
                    output_format=OutputFormat.MARKDOWN
                )
            
            assert 'security' in str(exc_info.value).lower() or 'invalid' in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_xss_prevention(self, mock_config_manager, mock_storage_manager, mock_miair_engine):
        """Test prevention of XSS attacks in HTML output."""
        generator = UnifiedDocumentGenerator(
            mock_config_manager,
            mock_storage_manager,
            mock_miair_engine
        )
        
        xss_attempts = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror='alert(1)'>",
            "<iframe src='javascript:alert(1)'></iframe>",
            "javascript:alert('XSS')"
        ]
        
        for xss in xss_attempts:
            result = await generator.generate_document(
                doc_type=DocumentType.README,
                template_id='readme_template',
                variables={'title': 'Safe', 'content': xss},
                output_format=OutputFormat.HTML
            )
            
            # XSS should be escaped or removed
            assert '<script>' not in result.content
            assert 'javascript:' not in result.content
            assert 'onerror=' not in result.content