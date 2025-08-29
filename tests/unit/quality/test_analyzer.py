"""
Unit tests for Quality Analyzer.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from devdocai.quality.analyzer import QualityAnalyzer
from devdocai.quality.models import (
    QualityConfig, QualityReport, QualityDimension,
    DimensionScore, QualityIssue, SeverityLevel
)
from devdocai.quality.exceptions import (
    QualityGateFailure, QualityEngineError, IntegrationError
)


class TestQualityAnalyzer:
    """Test suite for QualityAnalyzer."""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        config = QualityConfig(quality_gate_threshold=85.0)
        return QualityAnalyzer(config)
    
    @pytest.fixture
    def sample_content(self):
        """Sample document content."""
        return """
# Sample Documentation

## Description
This is a sample document for testing the quality analyzer.

## Installation
```bash
pip install sample-package
```

## Usage
Here's how to use this package:

```python
from sample import SampleClass

# Create instance
sample = SampleClass()
sample.do_something()
```

## API Reference
The API provides the following endpoints:
- GET /api/items - List all items
- POST /api/items - Create new item

## License
MIT License
"""
    
    def test_initialization(self):
        """Test analyzer initialization."""
        config = QualityConfig(quality_gate_threshold=90.0)
        analyzer = QualityAnalyzer(config)
        
        assert analyzer.config.quality_gate_threshold == 90.0
        assert len(analyzer.analyzers) == 5  # 5 dimensions
        assert len(analyzer.validators) >= 3  # At least 3 validators
    
    def test_analyze_basic(self, analyzer, sample_content):
        """Test basic analysis functionality."""
        report = analyzer.analyze(sample_content, document_id="test-doc")
        
        assert isinstance(report, QualityReport)
        assert report.document_id == "test-doc"
        assert 0 <= report.overall_score <= 100
        assert len(report.dimension_scores) > 0
        assert isinstance(report.gate_passed, bool)
    
    def test_quality_gate_pass(self, analyzer):
        """Test document passing quality gate."""
        good_content = """
# Comprehensive Documentation

## Overview
This is a well-structured document with comprehensive content that provides
detailed information about the system and its usage.

## Installation
Detailed installation instructions:

```bash
# Install dependencies
npm install

# Configure environment
cp .env.example .env
```

## Usage Examples
Multiple usage examples with explanations:

```javascript
const app = require('./app');

// Initialize application
app.initialize({
    config: './config.json'
});

// Start server
app.listen(3000, () => {
    console.log('Server running');
});
```

## API Documentation
### Authentication
All API requests require authentication using JWT tokens.

### Endpoints
- GET /api/users - List users
- POST /api/users - Create user
- PUT /api/users/:id - Update user
- DELETE /api/users/:id - Delete user

## Configuration
Configuration options are documented here with examples.

## Troubleshooting
Common issues and their solutions.

## Contributing
Guidelines for contributing to the project.

## License
MIT License - see LICENSE file for details.
"""
        report = analyzer.analyze(good_content)
        assert report.gate_passed is True
        assert report.overall_score >= 85.0
    
    def test_quality_gate_fail(self, analyzer):
        """Test document failing quality gate."""
        poor_content = "This is too short."
        
        with pytest.raises(QualityGateFailure) as exc_info:
            analyzer.analyze(poor_content)
        
        assert exc_info.value.score < 85.0
        assert exc_info.value.threshold == 85.0
    
    def test_dimension_analysis(self, analyzer, sample_content):
        """Test individual dimension analysis."""
        report = analyzer.analyze(sample_content)
        
        dimensions_found = {ds.dimension for ds in report.dimension_scores}
        expected_dimensions = {
            QualityDimension.COMPLETENESS,
            QualityDimension.CLARITY,
            QualityDimension.STRUCTURE,
            QualityDimension.ACCURACY,
            QualityDimension.FORMATTING
        }
        
        assert dimensions_found == expected_dimensions
        
        for dim_score in report.dimension_scores:
            assert 0 <= dim_score.score <= 100
            assert isinstance(dim_score.issues, list)
    
    def test_caching(self, analyzer, sample_content):
        """Test report caching."""
        # First analysis
        report1 = analyzer.analyze(sample_content, document_id="cached-doc")
        
        # Second analysis (should use cache)
        with patch.object(analyzer, '_analyze_dimension') as mock_analyze:
            report2 = analyzer.analyze(sample_content, document_id="cached-doc")
            mock_analyze.assert_not_called()  # Should not re-analyze
        
        assert report1.overall_score == report2.overall_score
        assert report1.document_id == report2.document_id
    
    def test_parallel_analysis(self):
        """Test parallel dimension analysis."""
        config = QualityConfig(parallel_analysis=True, max_workers=4)
        analyzer = QualityAnalyzer(config)
        
        content = "# Test\n\nThis is a test document with some content."
        report = analyzer.analyze(content)
        
        assert isinstance(report, QualityReport)
        assert len(report.dimension_scores) > 0
    
    def test_validation_integration(self, analyzer):
        """Test document validation integration."""
        invalid_content = """
## Missing H1 Header

This document has invalid structure.
"""
        report = analyzer.analyze(invalid_content)
        
        # Should have validation issues in formatting dimension
        formatting_score = next(
            ds for ds in report.dimension_scores 
            if ds.dimension == QualityDimension.FORMATTING
        )
        
        assert len(formatting_score.issues) > 0
    
    @patch('devdocai.quality.analyzer.MIAIR_AVAILABLE', True)
    def test_miair_integration(self, analyzer):
        """Test MIAIR engine integration."""
        mock_miair = MagicMock()
        mock_miair.analyze_document.return_value = {
            'entropy': 0.8,
            'pattern_score': 0.9,
            'quality_metrics': {'complexity': 0.5},
            'recommendations': ['Improve code examples']
        }
        
        analyzer.miair_engine = mock_miair
        
        content = "# Test\n\nContent for MIAIR analysis."
        report = analyzer.analyze_with_miair(content)
        
        assert isinstance(report, QualityReport)
        assert 'Improve code examples' in report.recommendations
        mock_miair.analyze_document.assert_called_once()
    
    @patch('devdocai.quality.analyzer.STORAGE_AVAILABLE', True)
    def test_storage_integration(self, analyzer):
        """Test storage system integration."""
        mock_storage = MagicMock()
        analyzer.storage_system = mock_storage
        
        content = "# Test\n\nContent for storage test."
        report = analyzer.analyze(content)
        
        mock_storage.create_document.assert_called_once()
        call_args = mock_storage.create_document.call_args[0][0]
        assert 'quality_report_' in call_args['id']
        assert call_args['type'] == 'quality_report'
    
    def test_batch_analysis(self, analyzer):
        """Test batch document analysis."""
        documents = [
            {'content': '# Doc 1\n\nFirst document.', 'id': 'doc1'},
            {'content': '# Doc 2\n\nSecond document.', 'id': 'doc2'},
            {'content': '# Doc 3\n\nThird document.', 'id': 'doc3'}
        ]
        
        reports = analyzer.batch_analyze(documents, parallel=False)
        
        assert len(reports) == 3
        for i, report in enumerate(reports):
            assert isinstance(report, QualityReport)
            assert report.document_id == f'doc{i+1}'
    
    def test_strict_mode(self):
        """Test strict mode with critical issues."""
        config = QualityConfig(
            quality_gate_threshold=50.0,  # Low threshold
            strict_mode=True  # But strict on critical issues
        )
        analyzer = QualityAnalyzer(config)
        
        # Content with critical issue (simulated)
        content = "```python\nif True  # Missing colon\n```"
        
        with pytest.raises(QualityGateFailure):
            analyzer.analyze(content)
    
    def test_recommendations_generation(self, analyzer, sample_content):
        """Test recommendation generation."""
        report = analyzer.analyze(sample_content)
        
        assert isinstance(report.recommendations, list)
        assert len(report.recommendations) > 0
        
        # Check for specific recommendation patterns
        for rec in report.recommendations:
            assert isinstance(rec, str)
            assert len(rec) > 0
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = QualityConfig(
            quality_gate_threshold=95.0,
            dimension_weights={
                QualityDimension.COMPLETENESS: 0.4,
                QualityDimension.CLARITY: 0.2,
                QualityDimension.STRUCTURE: 0.2,
                QualityDimension.ACCURACY: 0.1,
                QualityDimension.FORMATTING: 0.1
            },
            enable_caching=False,
            parallel_analysis=False
        )
        
        analyzer = QualityAnalyzer(config)
        assert analyzer.config.quality_gate_threshold == 95.0
        assert analyzer.config.dimension_weights[QualityDimension.COMPLETENESS] == 0.4
        assert analyzer.config.enable_caching is False
    
    @pytest.mark.asyncio
    async def test_async_analysis(self, analyzer, sample_content):
        """Test async analysis."""
        report = await analyzer.analyze_async(sample_content)
        
        assert isinstance(report, QualityReport)
        assert 0 <= report.overall_score <= 100
    
    def test_error_handling(self, analyzer):
        """Test error handling."""
        # Test with None content
        with pytest.raises(QualityEngineError):
            analyzer.analyze(None)
        
        # Test with invalid content type
        with pytest.raises(QualityEngineError):
            analyzer.analyze(12345)  # Not a string
    
    def test_statistics(self, analyzer, sample_content):
        """Test statistics retrieval."""
        # Analyze some documents
        analyzer.analyze(sample_content, document_id="stats-test")
        
        stats = analyzer.get_statistics()
        
        assert 'cache_size' in stats
        assert 'quality_threshold' in stats
        assert 'dimensions' in stats
        assert 'integrations' in stats
        
        assert stats['quality_threshold'] == 85.0
        assert stats['cache_size'] >= 0
    
    def test_context_manager(self, sample_content):
        """Test context manager usage."""
        config = QualityConfig()
        
        with QualityAnalyzer(config) as analyzer:
            report = analyzer.analyze(sample_content)
            assert isinstance(report, QualityReport)
        
        # Executor should be shut down after context exit
        assert analyzer.executor._shutdown is True