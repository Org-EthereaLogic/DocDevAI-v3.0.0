"""
Unit tests for main MIAIR Engine.

Tests the orchestration of all components and integration with M002 storage.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from devdocai.miair.engine import (
    MIAIREngine, MIAIRConfig, DocumentAnalysis, BatchProcessingResult
)
from devdocai.miair.scorer import QualityMetrics, ScoringWeights


class TestMIAIREngine:
    """Test suite for MIAIR Engine."""
    
    @pytest.fixture
    def engine(self):
        """Create MIAIR Engine instance."""
        config = MIAIRConfig(
            target_quality=0.8,
            max_iterations=5,
            storage_enabled=False  # Disable storage for unit tests
        )
        return MIAIREngine(config=config)
    
    @pytest.fixture
    def engine_with_storage(self):
        """Create engine with mocked storage."""
        config = MIAIRConfig(
            target_quality=0.8,
            storage_enabled=True
        )
        
        # Mock storage system
        with patch('devdocai.miair.engine.STORAGE_AVAILABLE', True):
            with patch('devdocai.miair.engine.LocalStorageSystem') as MockStorage:
                mock_storage = Mock()
                MockStorage.return_value = mock_storage
                engine = MIAIREngine(config=config)
                engine.storage = mock_storage
                return engine
    
    @pytest.fixture
    def sample_document(self):
        """Sample document for testing."""
        return """
        # User Manual
        
        ## Introduction
        
        This manual describes how to use our software application.
        
        ## Installation
        
        To install the software, follow these steps:
        1. Download the installer
        2. Run the setup program
        3. Follow the on-screen instructions
        
        ## Usage
        
        The application provides various features for data processing.
        
        ## Troubleshooting
        
        If you encounter issues, check our support website.
        """
    
    @pytest.fixture
    def poor_document(self):
        """Poor quality document."""
        return """
        manual
        
        TODO: write intro
        
        install: run setup
        
        [placeholder]
        """
    
    def test_initialization(self, engine):
        """Test engine initialization."""
        assert engine.config.target_quality == 0.8
        assert engine.config.max_iterations == 5
        assert engine.entropy_calc is not None
        assert engine.scorer is not None
        assert engine.pattern_recognizer is not None
        assert engine.optimizer is not None
        assert engine.storage is None  # Storage disabled
    
    def test_initialization_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = MIAIRConfig(
            target_quality=0.9,
            min_quality=0.6,
            max_iterations=10,
            enable_learning=False,
            scoring_weights=ScoringWeights(
                completeness=0.4,
                clarity=0.3,
                consistency=0.2,
                accuracy=0.1
            )
        )
        
        engine = MIAIREngine(config=config)
        
        assert engine.config.target_quality == 0.9
        assert engine.config.min_quality == 0.6
        assert engine.pattern_recognizer.learning_enabled is False
        assert engine.scorer.weights.completeness == 0.4
    
    def test_analyze_document(self, engine, sample_document):
        """Test document analysis."""
        analysis = engine.analyze_document(sample_document, document_id="test_doc")
        
        assert isinstance(analysis, DocumentAnalysis)
        assert analysis.document_id == "test_doc"
        assert analysis.content == sample_document
        assert analysis.entropy_stats is not None
        assert analysis.quality_metrics is not None
        assert analysis.patterns is not None
        assert 0.0 <= analysis.improvement_potential <= 1.0
        assert len(analysis.recommendations) > 0
    
    def test_analyze_empty_document(self, engine):
        """Test analysis of empty document."""
        analysis = engine.analyze_document("")
        
        assert analysis.content == ""
        assert analysis.quality_metrics.overall == 0.0
        assert analysis.improvement_potential == 0.0
    
    def test_optimize_document(self, engine, poor_document):
        """Test document optimization."""
        result = engine.optimize_document(poor_document, document_id="poor_doc")
        
        assert result.original_content == poor_document
        assert result.optimized_content != poor_document
        assert result.optimized_score.overall > result.original_score.overall
        assert result.iterations > 0
    
    def test_optimize_good_document(self, engine, sample_document):
        """Test optimization of already good document."""
        # Set high quality threshold
        engine.config.target_quality = 0.3  # Low target
        
        result = engine.optimize_document(sample_document)
        
        # Should recognize good quality
        if result.original_score.overall >= 0.3:
            assert result.iterations == 0
            assert result.success is True
    
    def test_process_batch(self, engine):
        """Test batch processing."""
        documents = [
            "Document 1: Simple content",
            "Document 2: Another document",
            {"content": "Document 3: With metadata", "metadata": {"type": "test"}}
        ]
        
        # Test analysis only
        result = engine.process_batch(documents, optimize=False)
        
        assert isinstance(result, BatchProcessingResult)
        assert result.total_documents == 3
        assert result.processed <= 3
        assert len(result.documents) == 3
        
        # Check document results
        for doc_result in result.documents:
            if 'error' not in doc_result:
                assert 'quality_score' in doc_result or 'success' in doc_result
    
    def test_process_batch_with_optimization(self, engine):
        """Test batch processing with optimization."""
        documents = [
            "Short doc needing improvement",
            "Another brief document"
        ]
        
        result = engine.process_batch(documents, optimize=True)
        
        assert result.total_documents == 2
        assert result.processed > 0
        
        # Check for improvement metrics
        for doc_result in result.documents:
            if 'error' not in doc_result:
                assert 'improvement' in doc_result
                assert 'original_score' in doc_result
                assert 'optimized_score' in doc_result
    
    def test_process_batch_with_errors(self, engine):
        """Test batch processing with error handling."""
        documents = [
            "Valid document",
            None,  # Will cause error
            "Another valid document"
        ]
        
        result = engine.process_batch(documents, optimize=False)
        
        assert result.failed >= 1
        assert result.processed <= 2
        
        # Check error was recorded
        error_found = False
        for doc_result in result.documents:
            if 'error' in doc_result:
                error_found = True
                break
        assert error_found
    
    def test_calculate_improvement_potential(self, engine):
        """Test improvement potential calculation."""
        metrics = QualityMetrics(overall=0.5)
        entropy_stats = {'information_density': 0.6}
        patterns = Mock()
        patterns.patterns = []
        
        potential = engine._calculate_improvement_potential(
            metrics, entropy_stats, patterns
        )
        
        assert 0.0 <= potential <= 1.0
        
        # Low quality should have high potential
        low_metrics = QualityMetrics(overall=0.2)
        high_potential = engine._calculate_improvement_potential(
            low_metrics, entropy_stats, patterns
        )
        assert high_potential > potential
    
    def test_generate_recommendations(self, engine, sample_document):
        """Test recommendation generation."""
        analysis = engine.analyze_document(sample_document)
        
        recommendations = analysis.recommendations
        
        assert isinstance(recommendations, list)
        assert len(recommendations) <= 5  # Limited to top 5
        assert all(isinstance(r, str) for r in recommendations)
        assert all(len(r) > 0 for r in recommendations)
    
    def test_metrics_tracking(self, engine, sample_document):
        """Test metrics tracking."""
        # Reset metrics
        engine.reset_metrics()
        
        # Perform operations
        engine.analyze_document(sample_document)
        engine.optimize_document(sample_document)
        
        metrics = engine.get_metrics()
        
        assert metrics['documents_analyzed'] == 1
        assert metrics['documents_optimized'] == 1
        assert metrics['processing_time'] > 0
        assert 'avg_processing_time' in metrics
        assert 'pattern_statistics' in metrics
    
    def test_reset_metrics(self, engine):
        """Test metrics reset."""
        # Add some metrics
        engine.metrics['documents_analyzed'] = 10
        engine.metrics['documents_optimized'] = 5
        
        engine.reset_metrics()
        
        assert engine.metrics['documents_analyzed'] == 0
        assert engine.metrics['documents_optimized'] == 0
        assert engine.metrics['total_improvement'] == 0.0
    
    def test_document_analysis_to_dict(self, engine, sample_document):
        """Test DocumentAnalysis to_dict conversion."""
        analysis = engine.analyze_document(sample_document, "test_id")
        
        result = analysis.to_dict()
        
        assert 'document_id' in result
        assert 'content_preview' in result
        assert 'entropy_stats' in result
        assert 'quality_metrics' in result
        assert 'patterns_summary' in result
        assert 'improvement_potential' in result
        assert 'recommendations' in result
        assert 'timestamp' in result
    
    def test_storage_integration(self, engine_with_storage, sample_document):
        """Test storage integration."""
        # Analyze document
        analysis = engine_with_storage.analyze_document(
            sample_document, 
            document_id="storage_test"
        )
        
        # Check storage was called if save_improvements is True
        if engine_with_storage.config.save_improvements:
            engine_with_storage.storage.create_document.assert_called()
    
    def test_optimization_with_learning(self, engine):
        """Test optimization with learning enabled."""
        engine.config.enable_learning = True
        
        doc = "Document to optimize with learning"
        result = engine.optimize_document(doc)
        
        # Learning should occur if successful
        if result.success and result.optimized_score.overall > result.original_score.overall:
            # Pattern recognizer should have learned
            assert engine.pattern_recognizer.learning_enabled
    
    def test_optimization_timeout(self, engine):
        """Test optimization timeout handling."""
        engine.config.optimization_timeout = 0.1  # Very short timeout
        
        # Create a document that would take long to optimize
        long_doc = "Complex document " * 1000
        
        result = engine.optimize_document(long_doc)
        
        assert result.elapsed_time < 1.0  # Should stop quickly
    
    def test_metadata_handling(self, engine, sample_document):
        """Test metadata handling in analysis and optimization."""
        metadata = {
            'version': '1.0.0',
            'author': 'Test Author',
            'tags': ['manual', 'user-guide']
        }
        
        # Analyze with metadata
        analysis = engine.analyze_document(sample_document, metadata=metadata)
        assert analysis is not None
        
        # Optimize with metadata
        result = engine.optimize_document(sample_document, metadata=metadata)
        assert result is not None
    
    def test_config_validation(self):
        """Test configuration validation."""
        # Valid config
        config = MIAIRConfig(
            target_quality=0.85,
            entropy_weight=0.3
        )
        assert config.target_quality == 0.85
        
        # Test default values
        assert config.max_iterations == 10
        assert config.enable_caching is True
    
    def test_batch_average_improvement(self, engine):
        """Test average improvement calculation in batch processing."""
        documents = [
            "Doc 1 needs improvement",
            "Doc 2 also needs work"
        ]
        
        result = engine.process_batch(documents, optimize=True)
        
        if result.improved > 0:
            assert result.average_improvement >= 0.0
        else:
            assert result.average_improvement == 0.0
    
    def test_empty_batch_processing(self, engine):
        """Test processing empty batch."""
        result = engine.process_batch([])
        
        assert result.total_documents == 0
        assert result.processed == 0
        assert result.improved == 0
        assert result.failed == 0


class TestMIAIREngineIntegration:
    """Integration tests for MIAIR Engine."""
    
    @pytest.fixture
    def engine(self):
        """Create engine for integration testing."""
        config = MIAIRConfig(
            target_quality=0.7,
            max_iterations=3,
            enable_learning=True,
            storage_enabled=False
        )
        return MIAIREngine(config=config)
    
    def test_full_document_lifecycle(self, engine):
        """Test complete document lifecycle."""
        # Start with poor document
        original = """
        guide
        
        TODO: intro
        
        install stuff
        """
        
        # Analyze
        analysis = engine.analyze_document(original, "lifecycle_test")
        
        assert analysis.quality_metrics.overall < 0.5
        assert analysis.improvement_potential > 0.5
        assert len(analysis.patterns.patterns) > 0
        
        # Optimize
        result = engine.optimize_document(original, "lifecycle_test")
        
        assert result.optimized_score.overall > result.original_score.overall
        assert len(result.optimized_content) > len(original)
        
        # Re-analyze optimized version
        final_analysis = engine.analyze_document(result.optimized_content)
        
        assert final_analysis.quality_metrics.overall > analysis.quality_metrics.overall
        assert final_analysis.improvement_potential < analysis.improvement_potential
    
    def test_iterative_improvement(self, engine):
        """Test iterative document improvement."""
        doc = "Brief document"
        
        # First optimization
        result1 = engine.optimize_document(doc)
        score1 = result1.optimized_score.overall
        
        # Second optimization on already optimized content
        result2 = engine.optimize_document(result1.optimized_content)
        score2 = result2.optimized_score.overall
        
        # Should maintain or improve quality
        assert score2 >= score1
    
    def test_component_interaction(self, engine):
        """Test interaction between all components."""
        doc = """
        # Test Document
        
        This document was written for testing.
        It contains various patterns that need improvement.
        
        TODO: Add more content
        
        Obviously, this is simple.
        """
        
        # Analyze to engage all components
        analysis = engine.analyze_document(doc)
        
        # Check entropy calculation worked
        assert 'character' in analysis.entropy_stats['entropy']
        assert 'word' in analysis.entropy_stats['entropy']
        
        # Check scoring worked
        assert analysis.quality_metrics.completeness >= 0.0
        assert analysis.quality_metrics.clarity >= 0.0
        
        # Check pattern recognition worked
        assert len(analysis.patterns.patterns) > 0
        
        # Check recommendations were generated
        assert len(analysis.recommendations) > 0
    
    def test_performance_with_various_documents(self, engine):
        """Test performance with different document types."""
        import time
        
        documents = [
            "Technical documentation with code examples",
            "User manual with step-by-step instructions" * 10,
            "API reference with endpoint descriptions" * 5,
            "Tutorial with exercises and solutions" * 3
        ]
        
        start = time.time()
        result = engine.process_batch(documents, optimize=False)
        elapsed = time.time() - start
        
        # Should process multiple documents efficiently
        assert elapsed < 5.0  # Less than 5 seconds for 4 documents
        assert result.processed == 4
        
        # Check individual results
        for doc_result in result.documents:
            if 'error' not in doc_result:
                assert 'quality_score' in doc_result