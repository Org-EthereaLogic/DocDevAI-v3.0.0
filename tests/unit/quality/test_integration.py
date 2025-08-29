"""
Integration tests for M005 Quality Engine with other modules.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import tempfile
import os

from devdocai.quality.analyzer import QualityAnalyzer
from devdocai.quality.models import QualityConfig, QualityReport, QualityDimension
from devdocai.quality.exceptions import IntegrationError, QualityGateFailure


class TestModuleIntegration:
    """Test integration with other DevDocAI modules."""
    
    @pytest.fixture
    def sample_document(self):
        """Sample document for testing."""
        return """
# API Documentation

## Overview
This is a comprehensive API documentation for testing integration.

## Authentication
All endpoints require JWT authentication tokens.

### Getting a Token
```python
import requests

response = requests.post('/auth/token', json={
    'username': 'user',
    'password': 'pass'
})
token = response.json()['token']
```

## Endpoints

### GET /api/users
Retrieve list of users.

**Parameters:**
- `page` (int): Page number
- `limit` (int): Items per page

**Response:**
```json
{
    "users": [
        {"id": 1, "name": "John Doe"}
    ],
    "total": 100
}
```

### POST /api/users
Create a new user.

## Error Handling
All errors return appropriate HTTP status codes.

## Rate Limiting
API is limited to 100 requests per minute.
"""
    
    @patch('devdocai.quality.analyzer.CONFIG_AVAILABLE', True)
    def test_config_manager_integration(self, sample_document):
        """Test integration with M001 Configuration Manager."""
        # Mock Configuration Manager
        mock_config_manager = MagicMock()
        mock_config_manager.get_quality_config.return_value = {
            'quality_gate_threshold': 90.0,
            'enable_caching': True,
            'parallel_analysis': True
        }
        
        # Create analyzer with config manager
        analyzer = QualityAnalyzer(config_manager=mock_config_manager)
        
        # Analyze document
        report = analyzer.analyze(sample_document)
        
        assert isinstance(report, QualityReport)
        assert report.overall_score >= 0
    
    @patch('devdocai.quality.analyzer.STORAGE_AVAILABLE', True)
    def test_storage_system_integration(self, sample_document):
        """Test integration with M002 Storage System."""
        # Mock Storage System
        mock_storage = MagicMock()
        mock_storage.create_document.return_value = {
            'id': 'doc-123',
            'status': 'stored'
        }
        
        # Create analyzer with storage system
        analyzer = QualityAnalyzer(storage_system=mock_storage)
        
        # Analyze document
        report = analyzer.analyze(sample_document, document_id='test-doc')
        
        # Verify storage was called
        mock_storage.create_document.assert_called_once()
        call_args = mock_storage.create_document.call_args[0][0]
        
        assert 'quality_report_' in call_args['id']
        assert call_args['type'] == 'quality_report'
        assert 'content' in call_args
    
    @patch('devdocai.quality.analyzer.MIAIR_AVAILABLE', True)
    def test_miair_engine_integration(self, sample_document):
        """Test integration with M003 MIAIR Engine."""
        # Mock MIAIR Engine
        mock_miair = MagicMock()
        mock_miair.analyze_document.return_value = {
            'entropy': 0.85,
            'pattern_score': 0.92,
            'quality_metrics': {
                'complexity': 0.6,
                'redundancy': 0.2
            },
            'recommendations': [
                'Add more code examples',
                'Improve error handling documentation'
            ]
        }
        mock_miair.set_mode = MagicMock()
        
        # Create analyzer with MIAIR engine
        analyzer = QualityAnalyzer(miair_engine=mock_miair)
        
        # Analyze with MIAIR
        report = analyzer.analyze_with_miair(
            sample_document,
            document_id='miair-test',
            use_optimization=True
        )
        
        # Verify MIAIR was called
        mock_miair.analyze_document.assert_called_once_with(sample_document)
        mock_miair.set_mode.assert_called_once()
        
        # Check recommendations were added
        assert 'Add more code examples' in report.recommendations
        assert 'Improve error handling documentation' in report.recommendations
    
    def test_full_integration(self, sample_document):
        """Test full integration with all modules mocked."""
        with patch('devdocai.quality.analyzer.CONFIG_AVAILABLE', True), \
             patch('devdocai.quality.analyzer.STORAGE_AVAILABLE', True), \
             patch('devdocai.quality.analyzer.MIAIR_AVAILABLE', True):
            
            # Mock all modules
            mock_config = MagicMock()
            mock_storage = MagicMock()
            mock_miair = MagicMock()
            
            mock_miair.analyze_document.return_value = {
                'entropy': 0.8,
                'pattern_score': 0.9,
                'quality_metrics': {},
                'recommendations': []
            }
            
            # Create fully integrated analyzer
            analyzer = QualityAnalyzer(
                config_manager=mock_config,
                storage_system=mock_storage,
                miair_engine=mock_miair
            )
            
            # Test standard analysis
            report = analyzer.analyze(sample_document)
            assert isinstance(report, QualityReport)
            
            # Test MIAIR-enhanced analysis
            report_miair = analyzer.analyze_with_miair(sample_document)
            assert isinstance(report_miair, QualityReport)
            
            # Test batch analysis
            documents = [
                {'content': sample_document, 'id': 'doc1'},
                {'content': '# Short\n\nContent', 'id': 'doc2'}
            ]
            reports = analyzer.batch_analyze(documents, parallel=False)
            assert len(reports) == 2


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""
    
    def test_readme_quality_check(self):
        """Test quality check for README file."""
        readme_content = """
# Project Name

## Description
A brief description of the project.

## Installation
```bash
npm install project-name
```

## Usage
```javascript
const project = require('project-name');
project.run();
```

## Contributing
Please read CONTRIBUTING.md for details.

## License
MIT License - see LICENSE file.
"""
        
        analyzer = QualityAnalyzer(
            config=QualityConfig(quality_gate_threshold=80.0)
        )
        
        report = analyzer.analyze(
            readme_content,
            document_id='readme',
            document_type='markdown',
            metadata={'document_type': 'readme'}
        )
        
        assert report.gate_passed is True
        assert report.overall_score >= 80.0
    
    def test_api_documentation_check(self):
        """Test quality check for API documentation."""
        api_doc = """
# API Documentation

## Overview
REST API for user management.

## Authentication
Bearer token required.

## Endpoints

### GET /users
List all users.

### POST /users
Create user.

### GET /users/{id}
Get user by ID.

### PUT /users/{id}
Update user.

### DELETE /users/{id}
Delete user.

## Errors
Standard HTTP status codes.

## Rate Limiting
1000 requests per hour.
"""
        
        analyzer = QualityAnalyzer()
        report = analyzer.analyze(
            api_doc,
            document_type='markdown',
            metadata={'document_type': 'api'}
        )
        
        # API docs should score reasonably well
        assert report.overall_score >= 70.0
    
    def test_poor_quality_detection(self):
        """Test detection of poor quality documentation."""
        poor_doc = """
stuff

this does things

use it somehow
"""
        
        analyzer = QualityAnalyzer()
        
        with pytest.raises(QualityGateFailure) as exc_info:
            analyzer.analyze(poor_doc)
        
        assert exc_info.value.score < 85.0
        
        # Get detailed report without raising exception
        analyzer.config.quality_gate_threshold = 0.0
        report = analyzer.analyze(poor_doc)
        
        # Should have many issues
        total_issues = sum(
            len(ds.issues) for ds in report.dimension_scores
        )
        assert total_issues > 5
        
        # Should have low scores across dimensions
        for dim_score in report.dimension_scores:
            assert dim_score.score < 80.0
    
    def test_performance_benchmark(self):
        """Test analysis performance."""
        import time
        
        # Create a reasonably sized document
        content = """
# Large Document

## Section 1
""" + "\n".join([f"Paragraph {i} content." for i in range(100)])
        
        analyzer = QualityAnalyzer(
            config=QualityConfig(
                parallel_analysis=True,
                enable_caching=True
            )
        )
        
        # First analysis (no cache)
        start = time.time()
        report1 = analyzer.analyze(content, document_id='perf-test')
        time1 = time.time() - start
        
        # Second analysis (should use cache)
        start = time.time()
        report2 = analyzer.analyze(content, document_id='perf-test')
        time2 = time.time() - start
        
        # Cache should make second analysis faster
        assert time2 < time1
        assert report1.overall_score == report2.overall_score
        
        # Check performance target (< 500ms per document)
        assert report1.analysis_time_ms < 500
    
    def test_custom_quality_gates(self):
        """Test custom quality gate configurations."""
        content = """
# Documentation

Basic documentation content that might score around 70-80%.

## Usage
Some usage information here.

## Examples
A few examples provided.
"""
        
        # Test with strict gate (95%)
        strict_analyzer = QualityAnalyzer(
            config=QualityConfig(quality_gate_threshold=95.0)
        )
        
        with pytest.raises(QualityGateFailure):
            strict_analyzer.analyze(content)
        
        # Test with lenient gate (60%)
        lenient_analyzer = QualityAnalyzer(
            config=QualityConfig(quality_gate_threshold=60.0)
        )
        
        report = lenient_analyzer.analyze(content)
        assert report.gate_passed is True
    
    def test_dimension_weight_customization(self):
        """Test custom dimension weight configurations."""
        content = """
# Technical Documentation

```python
def complex_function():
    # Lots of code
    pass
```

More code examples follow...
"""
        
        # Emphasize completeness and accuracy
        config = QualityConfig(
            dimension_weights={
                QualityDimension.COMPLETENESS: 0.4,
                QualityDimension.CLARITY: 0.1,
                QualityDimension.STRUCTURE: 0.1,
                QualityDimension.ACCURACY: 0.3,
                QualityDimension.FORMATTING: 0.1
            },
            quality_gate_threshold=70.0
        )
        
        analyzer = QualityAnalyzer(config)
        report = analyzer.analyze(content)
        
        # Score should reflect weighted dimensions
        assert isinstance(report.overall_score, float)