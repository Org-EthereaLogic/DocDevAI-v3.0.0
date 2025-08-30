"""
Comprehensive unit tests for M007 Review Engine.

Tests review engine functionality, dimension analysis, integration with other modules,
and various edge cases to ensure robust document review capabilities.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import json

from devdocai.review.review_engine import (
    ReviewEngine,
    ReviewEngineConfig,
    ReviewCache
)
from devdocai.review.models import (
    ReviewResult,
    ReviewStatus,
    ReviewDimension,
    ReviewSeverity,
    ReviewIssue,
    DimensionResult,
    ReviewMetrics
)
from devdocai.review.dimensions import (
    TechnicalAccuracyDimension,
    CompletenessDimension,
    ConsistencyDimension,
    StyleFormattingDimension,
    SecurityPIIDimension
)


# Sample test documents
SAMPLE_README = """
# Test Project

## Installation
```bash
pip install test-project
```

## Usage
```python
from test_project import main
main()
```

## License
MIT
"""

SAMPLE_API_DOC = """
# API Documentation

## Authentication
Use API key in header: `Authorization: Bearer YOUR_API_KEY`

## Endpoints

### GET /users
Returns list of users.

**Parameters:**
- limit (int): Maximum number of results
- offset (int): Pagination offset

**Response:**
```json
{
  "users": [],
  "total": 0
}
```
"""

SAMPLE_WITH_PII = """
# User Guide

Contact John Doe at john.doe@example.com or call 555-123-4567.
His SSN is 123-45-6789 and credit card is 4111111111111111.
"""

SAMPLE_WITH_ISSUES = """
# incomplete Documentation

TODO: Add installation instructions
FIXME: Update this section

## usage

this is a lowercase header with inconsistent formatting.

```python
def bad_code(
    print("missing closing parenthesis"
```

## Security Issue

Use this command: `rm -rf /`
Password: mysecretpassword123
"""


class TestReviewEngineConfig:
    """Test ReviewEngineConfig functionality."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = ReviewEngineConfig()
        
        assert config.approval_threshold == 85.0
        assert config.conditional_approval_threshold == 70.0
        assert config.enable_caching is True
        assert config.parallel_analysis is True
        assert config.enable_pii_detection is True
        assert ReviewDimension.TECHNICAL_ACCURACY in config.enabled_dimensions
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = ReviewEngineConfig(
            approval_threshold=90.0,
            enable_caching=False,
            max_workers=8,
            strict_mode=True
        )
        
        assert config.approval_threshold == 90.0
        assert config.enable_caching is False
        assert config.max_workers == 8
        assert config.strict_mode is True
    
    def test_threshold_validation(self):
        """Test threshold validation."""
        # This should work
        config = ReviewEngineConfig(
            approval_threshold=80.0,
            conditional_approval_threshold=70.0
        )
        assert config.approval_threshold > config.conditional_approval_threshold
        
        # This should fail validation and auto-adjust
        with pytest.raises(ValueError):
            config = ReviewEngineConfig(
                approval_threshold=70.0,
                conditional_approval_threshold=80.0
            )
    
    def test_dimension_weights_normalization(self):
        """Test dimension weights are normalized."""
        config = ReviewEngineConfig()
        
        # Check that enabled dimension weights sum to approximately 1.0
        total_weight = sum(
            config.dimension_weights[dim] 
            for dim in config.enabled_dimensions
        )
        assert abs(total_weight - 1.0) < 0.01


class TestReviewCache:
    """Test ReviewCache functionality."""
    
    def test_cache_set_get(self):
        """Test cache set and get operations."""
        cache = ReviewCache(ttl_seconds=3600)
        
        # Create mock review result
        result = Mock(spec=ReviewResult)
        result.review_id = "test-123"
        
        # Set and get
        cache.set("key1", result)
        cached = cache.get("key1")
        
        assert cached is not None
        assert cached.review_id == "test-123"
    
    def test_cache_expiry(self):
        """Test cache expiry."""
        cache = ReviewCache(ttl_seconds=1)  # 1 second TTL
        
        result = Mock(spec=ReviewResult)
        cache.set("key1", result)
        
        # Should be available immediately
        assert cache.get("key1") is not None
        
        # Mock time passage
        import time
        time.sleep(1.1)
        
        # Should be expired
        assert cache.get("key1") is None
    
    def test_cache_clear(self):
        """Test cache clearing."""
        cache = ReviewCache()
        
        result = Mock(spec=ReviewResult)
        cache.set("key1", result)
        cache.set("key2", result)
        
        assert cache.get("key1") is not None
        assert cache.get("key2") is not None
        
        cache.clear()
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None


class TestReviewEngine:
    """Test main ReviewEngine functionality."""
    
    @pytest.fixture
    def engine(self):
        """Create review engine instance."""
        config = ReviewEngineConfig(
            enable_caching=True,
            parallel_analysis=False,  # Disable for predictable testing
            use_quality_engine=False,  # Disable integration for unit tests
            use_miair_optimization=False
        )
        return ReviewEngine(config)
    
    @pytest.mark.asyncio
    async def test_review_simple_document(self, engine):
        """Test reviewing a simple document."""
        result = await engine.review_document(
            content=SAMPLE_README,
            document_id="readme-test",
            document_type="readme"
        )
        
        assert result is not None
        assert result.document_id == "readme-test"
        assert result.document_type == "readme"
        assert result.overall_score >= 0
        assert result.overall_score <= 100
        assert result.status in ReviewStatus
        assert len(result.dimension_results) > 0
    
    @pytest.mark.asyncio
    async def test_review_with_pii(self, engine):
        """Test reviewing document with PII."""
        result = await engine.review_document(
            content=SAMPLE_WITH_PII,
            document_id="pii-test",
            document_type="guide"
        )
        
        # Should detect PII
        pii_issues = [
            issue for issue in result.all_issues 
            if issue.dimension == ReviewDimension.SECURITY_PII
        ]
        assert len(pii_issues) > 0
        
        # Should have lower security score
        security_dim = next(
            (d for d in result.dimension_results 
             if d.dimension == ReviewDimension.SECURITY_PII),
            None
        )
        assert security_dim is not None
        assert security_dim.score < 100
    
    @pytest.mark.asyncio
    async def test_review_with_multiple_issues(self, engine):
        """Test reviewing document with multiple issues."""
        result = await engine.review_document(
            content=SAMPLE_WITH_ISSUES,
            document_id="issues-test",
            document_type="documentation"
        )
        
        # Should find multiple issues
        assert len(result.all_issues) >= 5
        
        # Should have lower score due to issues
        assert result.overall_score < 90
        
        # Should need revision, be rejected, or approved with conditions
        assert result.status in [ReviewStatus.NEEDS_REVISION, ReviewStatus.REJECTED, ReviewStatus.APPROVED_WITH_CONDITIONS]
        
        # Check for specific issue types
        has_todo = any("TODO" in issue.title or "TODO" in issue.description 
                      for issue in result.all_issues)
        has_security = any(issue.dimension == ReviewDimension.SECURITY_PII 
                          for issue in result.all_issues)
        has_formatting = any(issue.dimension == ReviewDimension.STYLE_FORMATTING 
                           for issue in result.all_issues)
        
        assert has_todo
        assert has_security
        assert has_formatting
    
    @pytest.mark.asyncio
    async def test_review_api_documentation(self, engine):
        """Test reviewing API documentation."""
        result = await engine.review_document(
            content=SAMPLE_API_DOC,
            document_id="api-test",
            document_type="api"
        )
        
        assert result is not None
        assert result.document_type == "api"
        
        # API docs should have reasonable score
        assert result.overall_score > 60
    
    @pytest.mark.asyncio
    async def test_caching(self, engine):
        """Test review caching functionality."""
        # First review
        result1 = await engine.review_document(
            content=SAMPLE_README,
            document_id="cache-test",
            document_type="readme"
        )
        
        # Should be cache miss
        assert engine.cache_misses == 1
        assert engine.cache_hits == 0
        
        # Second review with same content
        result2 = await engine.review_document(
            content=SAMPLE_README,
            document_id="cache-test",
            document_type="readme"
        )
        
        # Should be cache hit
        assert engine.cache_hits == 1
        assert result2.review_id == result1.review_id
    
    @pytest.mark.asyncio
    async def test_batch_review(self, engine):
        """Test batch review functionality."""
        documents = [
            {
                'content': SAMPLE_README,
                'id': 'batch-1',
                'type': 'readme'
            },
            {
                'content': SAMPLE_API_DOC,
                'id': 'batch-2',
                'type': 'api'
            }
        ]
        
        results = await engine.batch_review(documents, parallel=False)
        
        assert len(results) == 2
        assert results[0].document_id == 'batch-1'
        assert results[1].document_id == 'batch-2'
    
    @pytest.mark.asyncio
    async def test_auto_fix(self, engine):
        """Test auto-fix functionality."""
        engine.config.auto_fix_enabled = True
        
        content = "Test content   \nwith trailing spaces   \n\n\n\nand excessive blank lines"
        
        # Create issues that can be auto-fixed
        issues = [
            ReviewIssue(
                dimension=ReviewDimension.STYLE_FORMATTING,
                severity=ReviewSeverity.LOW,
                title="Trailing whitespace detected",
                description="Lines have trailing whitespace",
                auto_fixable=True
            ),
            ReviewIssue(
                dimension=ReviewDimension.STYLE_FORMATTING,
                severity=ReviewSeverity.LOW,
                title="Excessive blank lines",
                description="Too many consecutive blank lines",
                auto_fixable=True
            )
        ]
        
        fixed_content, fixed_issues = await engine.auto_fix_issues(content, issues)
        
        # Check fixes were applied
        assert "   " not in fixed_content.split('\n')[0]  # No trailing spaces
        assert "\n\n\n\n" not in fixed_content  # No excessive blank lines
        assert len(fixed_issues) > 0
    
    def test_generate_markdown_report(self, engine):
        """Test markdown report generation."""
        # Create mock review result
        result = ReviewResult(
            document_id="test-doc",
            document_type="readme",
            review_id="review-123",
            overall_score=75.5,
            status=ReviewStatus.APPROVED_WITH_CONDITIONS,
            dimension_results=[
                DimensionResult(
                    dimension=ReviewDimension.TECHNICAL_ACCURACY,
                    score=80.0,
                    weight=0.25,
                    issues=[],
                    passed_checks=8,
                    total_checks=10
                )
            ],
            all_issues=[],
            recommended_actions=["Fix critical issues", "Improve documentation"],
            approval_conditions=["Address all high-priority issues"]
        )
        
        report = engine.generate_report(result, format="markdown")
        
        assert "# Document Review Report" in report
        assert "test-doc" in report
        assert "75.5/100" in report
        assert "APPROVED_WITH_CONDITIONS" in report
        assert "Fix critical issues" in report
    
    def test_generate_json_report(self, engine):
        """Test JSON report generation."""
        result = ReviewResult(
            document_id="test-doc",
            document_type="readme",
            review_id="review-123",
            overall_score=75.5,
            status=ReviewStatus.APPROVED
        )
        
        report = engine.generate_report(result, format="json")
        data = json.loads(report)
        
        assert data['document_id'] == "test-doc"
        assert data['overall_score'] == 75.5
        assert data['status'] == "approved"
    
    def test_statistics(self, engine):
        """Test statistics tracking."""
        initial_stats = engine.get_statistics()
        
        assert initial_stats['reviews_performed'] == 0
        assert initial_stats['total_issues_found'] == 0
        assert initial_stats['cache_hit_rate'] == 0
        
        # Perform a review
        asyncio.run(engine.review_document(SAMPLE_README))
        
        stats = engine.get_statistics()
        assert stats['reviews_performed'] == 1
        assert 'enabled_dimensions' in stats
    
    def test_shutdown(self, engine):
        """Test engine shutdown."""
        engine.shutdown()
        
        # Cache should be cleared if exists
        if engine.cache:
            assert engine.cache.get("any-key") is None


class TestDimensions:
    """Test individual dimension implementations."""
    
    @pytest.mark.asyncio
    async def test_technical_accuracy_dimension(self):
        """Test TechnicalAccuracyDimension."""
        dimension = TechnicalAccuracyDimension()
        
        content = """
        # Test
        ```python
        def test(:  # Syntax error
            print("test"
        ```
        
        Use deprecated API: React.PropTypes
        """
        
        result = await dimension.analyze(content, {})
        
        assert result.dimension == ReviewDimension.TECHNICAL_ACCURACY
        assert len(result.issues) > 0
        assert result.score < 100
    
    @pytest.mark.asyncio
    async def test_completeness_dimension(self):
        """Test CompletenessDimension."""
        dimension = CompletenessDimension()
        
        content = """
        # Documentation
        
        ## Installation
        TODO: Add installation steps
        
        ## Usage
        
        ## License
        TBD
        """
        
        result = await dimension.analyze(content, {'document_type': 'readme'})
        
        assert result.dimension == ReviewDimension.COMPLETENESS
        assert len(result.issues) > 0  # Should find TODOs
        assert any("TODO" in issue.description or "TODO" in issue.title 
                  for issue in result.issues)
    
    @pytest.mark.asyncio
    async def test_consistency_dimension(self):
        """Test ConsistencyDimension."""
        dimension = ConsistencyDimension()
        
        content = """
        # API Documentation
        
        Use the API key for authentication.
        The api endpoint is /users.
        Send requests to the Api server.
        """
        
        result = await dimension.analyze(content, {})
        
        assert result.dimension == ReviewDimension.CONSISTENCY
        # Should find inconsistent API capitalization
        assert any("terminology" in issue.title.lower() for issue in result.issues)
    
    @pytest.mark.asyncio
    async def test_style_formatting_dimension(self):
        """Test StyleFormattingDimension."""
        dimension = StyleFormattingDimension()
        
        content = """
        #Missing space before header
        
        
        
        Too many blank lines above.
        
        This line has trailing whitespace    
        """
        
        result = await dimension.analyze(content, {})
        
        assert result.dimension == ReviewDimension.STYLE_FORMATTING
        assert len(result.issues) > 0
        assert result.score < 100
    
    @pytest.mark.asyncio
    async def test_security_pii_dimension(self):
        """Test SecurityPIIDimension."""
        dimension = SecurityPIIDimension()
        
        content = """
        Contact: john@example.com
        Phone: 555-123-4567
        SSN: 123-45-6789
        API_KEY=sk_live_abcdef123456
        Password: mysecret123
        """
        
        result = await dimension.analyze(content, {})
        
        assert result.dimension == ReviewDimension.SECURITY_PII
        assert len(result.issues) > 0
        assert result.score < 50  # Should have low score due to PII
        
        # Should find critical/blocker issues
        assert any(issue.severity in [ReviewSeverity.CRITICAL, ReviewSeverity.BLOCKER] 
                  for issue in result.issues)


class TestIntegration:
    """Test integration with other modules."""
    
    @pytest.mark.asyncio
    async def test_with_mock_storage(self):
        """Test integration with mocked M002 storage."""
        with patch('devdocai.review.review_engine.LocalStorageSystem') as mock_storage_class:
            mock_storage = AsyncMock()
            mock_storage_class.return_value = mock_storage
            
            engine = ReviewEngine()
            result = await engine.review_document(SAMPLE_README)
            
            # Should attempt to store result
            if engine.storage:
                mock_storage.create.assert_called()
    
    @pytest.mark.asyncio
    async def test_with_mock_quality_engine(self):
        """Test integration with mocked M005 quality engine."""
        with patch('devdocai.review.review_engine.UnifiedQualityAnalyzer') as mock_quality_class:
            mock_quality = AsyncMock()
            mock_quality.analyze.return_value = Mock(
                overall_score=85.0,
                issues=[]
            )
            mock_quality_class.return_value = mock_quality
            
            config = ReviewEngineConfig(use_quality_engine=True)
            engine = ReviewEngine(config)
            
            result = await engine.review_document(SAMPLE_README)
            
            # Check quality insights in metadata
            if engine.quality_analyzer:
                assert 'quality_insights' in result.metadata
    
    @pytest.mark.asyncio
    async def test_with_mock_miair(self):
        """Test integration with mocked M003 MIAIR engine."""
        with patch('devdocai.review.review_engine.UnifiedMIAIREngine') as mock_miair_class:
            mock_miair = Mock()
            mock_miair.analyze.return_value = {
                'entropy': 0.75,
                'quality_score': 82.0,
                'patterns': ['pattern1', 'pattern2']
            }
            mock_miair_class.return_value = mock_miair
            
            config = ReviewEngineConfig(use_miair_optimization=True)
            engine = ReviewEngine(config)
            
            result = await engine.review_document(SAMPLE_README)
            
            # Check optimization suggestions in metadata
            if engine.miair_engine:
                assert 'optimization_suggestions' in result.metadata


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_empty_document(self):
        """Test reviewing empty document."""
        engine = ReviewEngine()
        result = await engine.review_document("")
        
        assert result is not None
        assert result.overall_score == 0 or len(result.all_issues) > 0
    
    @pytest.mark.asyncio
    async def test_very_long_document(self):
        """Test reviewing very long document."""
        engine = ReviewEngine()
        
        # Create a very long document
        long_content = "# Title\n\n" + ("This is a paragraph. " * 1000 + "\n\n") * 100
        
        result = await engine.review_document(long_content)
        
        assert result is not None
        assert result.metrics.execution_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_dimension_failure(self):
        """Test handling of dimension analysis failure."""
        engine = ReviewEngine()
        
        # Mock a dimension to fail
        with patch.object(TechnicalAccuracyDimension, 'analyze', side_effect=Exception("Test error")):
            result = await engine.review_document(SAMPLE_README)
            
            # Should still complete review
            assert result is not None
            
            # Should have error issue
            error_issues = [
                issue for issue in result.all_issues 
                if "analysis failed" in issue.title.lower()
            ]
            assert len(error_issues) > 0
    
    @pytest.mark.asyncio
    async def test_invalid_document_type(self):
        """Test with invalid document type."""
        engine = ReviewEngine()
        
        result = await engine.review_document(
            content=SAMPLE_README,
            document_type="unknown_type_xyz"
        )
        
        assert result is not None
        assert result.document_type == "unknown_type_xyz"
    
    @pytest.mark.asyncio
    async def test_concurrent_reviews(self):
        """Test concurrent review operations."""
        engine = ReviewEngine(ReviewEngineConfig(parallel_analysis=True))
        
        # Run multiple reviews concurrently
        tasks = [
            engine.review_document(SAMPLE_README, document_id=f"concurrent-{i}")
            for i in range(5)
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5
        assert all(r.document_id.startswith("concurrent-") for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])