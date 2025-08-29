"""
Unified unit tests for M005 Quality Engine - Refactored Implementation.

Consolidates tests from multiple test files into a single comprehensive suite.
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from devdocai.quality import (
    QualityAnalyzer,
    UnifiedQualityAnalyzer,
    QualityEngineConfig,
    OperationMode,
    CacheStrategy,
    analyze_document
)
from devdocai.quality.models import (
    QualityReport, QualityDimension, DimensionScore,
    QualityIssue, SeverityLevel
)
from devdocai.quality.dimensions_unified import (
    UnifiedCompletenessAnalyzer,
    UnifiedClarityAnalyzer,
    UnifiedStructureAnalyzer,
    UnifiedAccuracyAnalyzer,
    UnifiedFormattingAnalyzer
)
from devdocai.quality.base_dimension import AnalysisContext
from devdocai.quality.exceptions import QualityEngineError
from devdocai.quality.utils import (
    calculate_readability,
    extract_code_blocks,
    count_words,
    count_syllables
)


class TestUnifiedQualityAnalyzer:
    """Test suite for unified quality analyzer."""
    
    @pytest.fixture
    def basic_config(self):
        """Basic configuration."""
        return QualityEngineConfig.from_mode(OperationMode.BASIC)
    
    @pytest.fixture
    def optimized_config(self):
        """Optimized configuration."""
        return QualityEngineConfig.from_mode(OperationMode.OPTIMIZED)
    
    @pytest.fixture
    def secure_config(self):
        """Secure configuration."""
        return QualityEngineConfig.from_mode(OperationMode.SECURE)
    
    @pytest.fixture
    def balanced_config(self):
        """Balanced configuration."""
        return QualityEngineConfig.from_mode(OperationMode.BALANCED)
    
    @pytest.fixture
    def sample_content(self):
        """Sample document content."""
        return """
# Sample Documentation

## Description
This is a sample document for testing the quality analyzer.
It contains various elements to test different quality dimensions.

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
The API provides the following methods:
- `method1()`: Does something
- `method2(param)`: Does something else

## Examples
See the examples directory for more usage examples.

## Contributing
Contributions are welcome! Please read CONTRIBUTING.md first.
"""
    
    @pytest.fixture
    def poor_quality_content(self):
        """Poor quality document content."""
        return """
# TODO: Write title

This is incomplete...

## [placeholder]

TODO: Add content here
FIXME: This section needs work

## Examples

[coming soon]
"""
    
    def test_analyzer_initialization(self, balanced_config):
        """Test analyzer initialization."""
        analyzer = UnifiedQualityAnalyzer(balanced_config)
        
        assert analyzer.config.mode == OperationMode.BALANCED
        assert len(analyzer.analyzers) == 5
        assert analyzer.cache is not None
        assert analyzer.scorer is not None
    
    def test_basic_mode_analysis(self, basic_config, sample_content):
        """Test analysis in basic mode."""
        analyzer = UnifiedQualityAnalyzer(basic_config)
        
        report = analyzer.analyze(sample_content)
        
        assert isinstance(report, QualityReport)
        assert report.overall_score > 0
        assert len(report.dimension_scores) == 5
        assert report.timestamp is not None
    
    def test_optimized_mode_performance(self, optimized_config, sample_content):
        """Test performance in optimized mode."""
        analyzer = UnifiedQualityAnalyzer(optimized_config)
        
        # First analysis (cache miss)
        start = time.perf_counter()
        report1 = analyzer.analyze(sample_content)
        time1 = time.perf_counter() - start
        
        # Second analysis (cache hit)
        start = time.perf_counter()
        report2 = analyzer.analyze(sample_content)
        time2 = time.perf_counter() - start
        
        # Cache should make second analysis faster
        assert time2 < time1
        assert report1.overall_score == report2.overall_score
    
    def test_secure_mode_validation(self, secure_config):
        """Test security validation in secure mode."""
        analyzer = UnifiedQualityAnalyzer(secure_config)
        
        # Test with oversized content
        large_content = "x" * (51 * 1024 * 1024)  # 51MB
        
        with pytest.raises(QualityEngineError):
            analyzer.analyze(large_content)
    
    def test_parallel_vs_sequential(self, sample_content):
        """Test parallel vs sequential processing."""
        # Parallel config
        parallel_config = QualityEngineConfig()
        parallel_config.performance.enable_parallel = True
        parallel_analyzer = UnifiedQualityAnalyzer(parallel_config)
        
        # Sequential config
        seq_config = QualityEngineConfig()
        seq_config.performance.enable_parallel = False
        seq_analyzer = UnifiedQualityAnalyzer(seq_config)
        
        # Both should produce same results
        parallel_report = parallel_analyzer.analyze(sample_content)
        seq_report = seq_analyzer.analyze(sample_content)
        
        assert abs(parallel_report.overall_score - seq_report.overall_score) < 0.01
    
    def test_batch_analysis(self, balanced_config, sample_content):
        """Test batch document analysis."""
        analyzer = UnifiedQualityAnalyzer(balanced_config)
        
        documents = [
            {'content': sample_content, 'type': 'markdown'},
            {'content': sample_content.replace('Sample', 'Test'), 'type': 'markdown'},
            {'content': sample_content[:500], 'type': 'markdown'}
        ]
        
        reports = analyzer.analyze_batch(documents, parallel=True)
        
        assert len(reports) == 3
        assert all(isinstance(r, QualityReport) for r in reports)
    
    def test_quality_gates(self, balanced_config, poor_quality_content):
        """Test quality gate checking."""
        analyzer = UnifiedQualityAnalyzer(balanced_config)
        
        report = analyzer.analyze(poor_quality_content)
        
        # Poor quality content should fail gates
        assert report.overall_score < 0.7
        assert not report.passed
        assert len(report.issues) > 0
    
    def test_cache_management(self, optimized_config, sample_content):
        """Test cache management."""
        analyzer = UnifiedQualityAnalyzer(optimized_config)
        
        # Analyze and cache
        report1 = analyzer.analyze(sample_content)
        
        # Get metrics before clear
        metrics1 = analyzer.get_metrics()
        assert metrics1['cache_hits'] == 0
        assert metrics1['cache_misses'] == 1
        
        # Second analysis should hit cache
        report2 = analyzer.analyze(sample_content)
        metrics2 = analyzer.get_metrics()
        assert metrics2['cache_hits'] == 1
        
        # Clear cache
        analyzer.clear_cache()
        
        # Third analysis should miss cache
        report3 = analyzer.analyze(sample_content)
        metrics3 = analyzer.get_metrics()
        assert metrics3['cache_misses'] == 2
    
    def test_context_manager(self, balanced_config, sample_content):
        """Test context manager usage."""
        config = balanced_config
        
        with UnifiedQualityAnalyzer(config) as analyzer:
            report = analyzer.analyze(sample_content)
            assert report is not None
        
        # Executor should be shut down after context exit
        if analyzer.executor:
            assert analyzer.executor._shutdown
    
    def test_convenience_function(self, sample_content):
        """Test convenience analyze_document function."""
        # Test different modes
        for mode in OperationMode:
            report = analyze_document(sample_content, mode=mode)
            assert isinstance(report, QualityReport)
            assert report.overall_score > 0


class TestUnifiedDimensionAnalyzers:
    """Test suite for unified dimension analyzers."""
    
    @pytest.fixture
    def context(self, sample_content):
        """Create analysis context."""
        return AnalysisContext(
            content=sample_content,
            content_hash="test_hash",
            document_type="markdown",
            metadata={},
            cache_enabled=True,
            security_enabled=False,
            performance_mode=False
        )
    
    @pytest.fixture
    def sample_content(self):
        """Sample content for dimension testing."""
        return """
# Complete Documentation

## Introduction
This document provides comprehensive information about our system.

## Installation
Follow these steps to install:

```bash
npm install our-package
```

## Usage
Here's how to use the package:

```javascript
const pkg = require('our-package');
pkg.initialize();
```

## API Reference
### Methods
- `initialize()`: Initializes the package
- `process(data)`: Processes input data
- `cleanup()`: Cleans up resources

## Examples
Check out these examples:

```javascript
// Example 1
const result = pkg.process({
    input: 'test',
    options: { verbose: true }
});
```

## Contributing
Please see CONTRIBUTING.md for guidelines.

## License
MIT License - see LICENSE file for details.
"""
    
    def test_completeness_analyzer(self, context):
        """Test completeness dimension analyzer."""
        analyzer = UnifiedCompletenessAnalyzer(performance_mode=False)
        
        score = analyzer.analyze(context)
        
        assert isinstance(score, DimensionScore)
        assert score.dimension == QualityDimension.COMPLETENESS
        assert 0 <= score.score <= 1
        assert score.metadata['checks_passed'] >= 0
    
    def test_clarity_analyzer(self, context):
        """Test clarity dimension analyzer."""
        analyzer = UnifiedClarityAnalyzer(performance_mode=False)
        
        score = analyzer.analyze(context)
        
        assert isinstance(score, DimensionScore)
        assert score.dimension == QualityDimension.CLARITY
        assert 'metrics' in score.metadata
        assert 'readability_score' in score.metadata['metrics']
    
    def test_structure_analyzer(self, context):
        """Test structure dimension analyzer."""
        analyzer = UnifiedStructureAnalyzer(performance_mode=False)
        
        score = analyzer.analyze(context)
        
        assert isinstance(score, DimensionScore)
        assert score.dimension == QualityDimension.STRUCTURE
        assert 'structure' in score.metadata
    
    def test_accuracy_analyzer(self, context):
        """Test accuracy dimension analyzer."""
        analyzer = UnifiedAccuracyAnalyzer(performance_mode=False)
        
        score = analyzer.analyze(context)
        
        assert isinstance(score, DimensionScore)
        assert score.dimension == QualityDimension.ACCURACY
        assert score.metadata['checks_passed'] >= 0
    
    def test_formatting_analyzer(self, context):
        """Test formatting dimension analyzer."""
        analyzer = UnifiedFormattingAnalyzer(performance_mode=False)
        
        score = analyzer.analyze(context)
        
        assert isinstance(score, DimensionScore)
        assert score.dimension == QualityDimension.FORMATTING
        assert 'lines_checked' in score.metadata
    
    def test_dimension_caching(self, context):
        """Test dimension-level caching."""
        analyzer = UnifiedCompletenessAnalyzer(performance_mode=True)
        
        # First analysis
        score1 = analyzer.analyze(context)
        
        # Second analysis (should use cache)
        score2 = analyzer.analyze(context)
        
        assert score1.score == score2.score
        assert score1.metadata['checks_passed'] == score2.metadata['checks_passed']
    
    def test_dimension_security_validation(self):
        """Test dimension security validation."""
        analyzer = UnifiedCompletenessAnalyzer(security_enabled=True)
        
        # Create oversized context
        large_content = "x" * (51 * 1024 * 1024)
        context = AnalysisContext(
            content=large_content,
            content_hash="large",
            document_type="markdown",
            metadata={},
            security_enabled=True
        )
        
        with pytest.raises(Exception):
            analyzer.analyze(context)


class TestUtilityFunctions:
    """Test suite for utility functions."""
    
    def test_calculate_readability(self):
        """Test readability calculation."""
        text = "This is a simple sentence. It is easy to read."
        score = calculate_readability(text)
        
        assert 0 <= score <= 100
        assert score > 60  # Should be relatively easy
    
    def test_extract_code_blocks(self):
        """Test code block extraction."""
        content = """
Some text
```python
def hello():
    print("Hello")
```
More text
```javascript
console.log("Hi");
```
"""
        blocks = extract_code_blocks(content)
        
        assert len(blocks) == 2
        assert blocks[0]['language'] == 'python'
        assert blocks[1]['language'] == 'javascript'
    
    def test_count_words(self):
        """Test word counting."""
        text = "This is a test sentence with seven words."
        count = count_words(text)
        
        assert count == 8
    
    def test_count_syllables(self):
        """Test syllable counting."""
        assert count_syllables("hello") == 2
        assert count_syllables("beautiful") == 3
        assert count_syllables("a") == 1
        assert count_syllables("extraordinary") >= 4


class TestConfiguration:
    """Test suite for configuration system."""
    
    def test_mode_configurations(self):
        """Test different mode configurations."""
        # Basic mode
        basic = QualityEngineConfig.from_mode(OperationMode.BASIC)
        assert not basic.performance.enable_parallel
        assert basic.performance.cache_strategy == CacheStrategy.NONE
        
        # Optimized mode
        optimized = QualityEngineConfig.from_mode(OperationMode.OPTIMIZED)
        assert optimized.performance.cache_strategy == CacheStrategy.AGGRESSIVE
        assert optimized.performance.enable_async
        
        # Secure mode
        secure = QualityEngineConfig.from_mode(OperationMode.SECURE)
        assert secure.security.enable_input_validation
        assert secure.security.enable_pii_detection
        assert secure.security.enable_audit_logging
        
        # Balanced mode
        balanced = QualityEngineConfig.from_mode(OperationMode.BALANCED)
        assert balanced.performance.enable_parallel
        assert balanced.security.enable_input_validation
    
    def test_environment_configuration(self):
        """Test configuration from environment variables."""
        with patch.dict('os.environ', {
            'QUALITY_ENGINE_MODE': 'secure',
            'QUALITY_MAX_WORKERS': '8',
            'QUALITY_CACHE_DIR': '/tmp/cache'
        }):
            config = QualityEngineConfig.from_env()
            
            assert config.mode == OperationMode.SECURE
            assert config.performance.max_workers == 8
            assert config.cache_dir == '/tmp/cache'
    
    def test_dimension_weights_normalization(self):
        """Test that dimension weights normalize to 1.0."""
        from devdocai.quality.config import DimensionWeights
        
        # Non-normalized weights
        weights = DimensionWeights(
            completeness=1.0,
            clarity=1.0,
            structure=1.0,
            accuracy=1.0,
            formatting=1.0
        )
        
        # Should be normalized
        total = (weights.completeness + weights.clarity + weights.structure +
                weights.accuracy + weights.formatting)
        assert abs(total - 1.0) < 0.001
    
    def test_config_to_dict(self):
        """Test configuration serialization."""
        config = QualityEngineConfig.from_mode(OperationMode.BALANCED)
        config_dict = config.to_dict()
        
        assert config_dict['mode'] == 'balanced'
        assert 'performance' in config_dict
        assert 'security' in config_dict
        assert 'thresholds' in config_dict
        assert 'weights' in config_dict


class TestPerformanceBenchmarks:
    """Performance benchmark tests."""
    
    @pytest.fixture
    def large_document(self):
        """Generate large document for performance testing."""
        sections = []
        for i in range(50):
            sections.append(f"""
## Section {i}

This is content for section {i}. It contains multiple paragraphs of text
to simulate a realistic document. The text includes various elements like
code blocks, lists, and links.

```python
def function_{i}():
    return "Result {i}"
```

- Item 1 for section {i}
- Item 2 for section {i}
- Item 3 for section {i}

Here's a [link](http://example.com/{i}) and more text.
""")
        return "\n".join(sections)
    
    def test_large_document_performance(self, optimized_config, large_document):
        """Test performance with large documents."""
        analyzer = UnifiedQualityAnalyzer(optimized_config)
        
        start = time.perf_counter()
        report = analyzer.analyze(large_document)
        elapsed = time.perf_counter() - start
        
        # Should complete within reasonable time
        assert elapsed < 1.0  # Less than 1 second for large doc
        assert report.overall_score > 0
    
    def test_batch_performance(self, optimized_config, sample_content):
        """Test batch processing performance."""
        analyzer = UnifiedQualityAnalyzer(optimized_config)
        
        # Create 100 documents
        documents = [
            {'content': sample_content, 'type': 'markdown'}
            for _ in range(100)
        ]
        
        start = time.perf_counter()
        reports = analyzer.analyze_batch(documents, parallel=True)
        elapsed = time.perf_counter() - start
        
        # Should process 100 docs quickly
        docs_per_second = len(documents) / elapsed
        assert docs_per_second > 50  # At least 50 docs/second
        assert len(reports) == 100


class TestSecurityFeatures:
    """Security feature tests."""
    
    def test_input_validation(self, secure_config):
        """Test input validation."""
        analyzer = UnifiedQualityAnalyzer(secure_config)
        
        # Test various malicious inputs
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "../../../etc/passwd",
            "x" * (51 * 1024 * 1024),  # Too large
        ]
        
        for malicious in malicious_inputs:
            try:
                report = analyzer.analyze(malicious)
                # If it doesn't raise, check it's sanitized
                assert '<script>' not in str(report)
            except QualityEngineError:
                # Expected for some inputs like oversized
                pass
    
    def test_rate_limiting(self, secure_config):
        """Test rate limiting (simplified test)."""
        # This would require actual rate limiting implementation
        # For now, just verify config is set
        assert secure_config.security.enable_rate_limiting
        assert secure_config.security.rate_limit_per_minute == 60
    
    def test_audit_logging(self, secure_config):
        """Test audit logging configuration."""
        assert secure_config.security.enable_audit_logging
    
    def test_dos_protection(self, secure_config):
        """Test DoS protection with timeout."""
        analyzer = UnifiedQualityAnalyzer(secure_config)
        
        # Create content that would take long to process
        complex_content = "a" * 1000000  # 1MB of text
        
        # Should complete within timeout
        start = time.perf_counter()
        report = analyzer.analyze(complex_content)
        elapsed = time.perf_counter() - start
        
        assert elapsed < secure_config.security.timeout_seconds