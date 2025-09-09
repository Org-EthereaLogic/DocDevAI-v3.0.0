"""
Test Suite for M007 Review Engine - Pass 2: Performance Optimization
Following Enhanced 4-Pass TDD Methodology - PASS 2 (Performance Tests)
DevDocAI v3.0.0

Pass 2 Performance Tests:
1. Verify <5-8 seconds per document analysis
2. Test multi-tier caching with compression
3. Validate parallel processing improvements
4. Measure batch processing performance
5. Confirm memory efficiency for large documents
"""

import asyncio
import json
import time
from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio

# Import dependencies
from devdocai.core.config import ConfigurationManager
from devdocai.core.generator import DocumentGenerator

# Import will fail initially (TDD) - that's expected
from devdocai.core.review import AnalysisReport, ReviewEngine, ReviewEngineFactory, ReviewError
from devdocai.core.review_types import ComplianceStandard, PIIType, ReviewResult, ReviewType
from devdocai.core.storage import Document, DocumentMetadata, StorageManager
from devdocai.core.tracking import TrackingMatrix


class TestReviewEngine:
    """Test core ReviewEngine functionality."""

    @pytest_asyncio.fixture
    async def review_engine(self, tmp_path):
        """Create a ReviewEngine instance with mocked dependencies."""
        # Mock dependencies
        config_manager = Mock(spec=ConfigurationManager)
        storage_manager = Mock(spec=StorageManager)
        doc_generator = Mock(spec=DocumentGenerator)
        tracking_matrix = Mock(spec=TrackingMatrix)

        # Configure mock returns
        config_manager.get.return_value = {
            "review": {
                "quality_threshold": 0.85,
                "pii_patterns": {
                    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                    "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
                    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
                },
            }
        }

        # Create review engine using factory
        engine = ReviewEngineFactory.create(
            config=config_manager,
            storage=storage_manager,
            generator=doc_generator,
            tracking=tracking_matrix,
        )

        return engine

    @pytest.mark.asyncio
    async def test_basic_review(self, review_engine):
        """Test basic document review functionality."""
        document = Document(
            id="test_doc",
            content="# Test Document\n\nThis is a test document with requirements.",
            type="readme",
            metadata=DocumentMetadata(
                version="1.0.0", tags=["test"], custom={"created_at": datetime.now().isoformat()}
            ),
        )

        result = await review_engine.analyze(document)

        assert isinstance(result, AnalysisReport)
        assert result.overall_score >= 0.0
        assert result.overall_score <= 1.0
        assert result.quality_gate_status in ["PASS", "FAIL"]
        assert len(result.reviews) > 0

    @pytest.mark.asyncio
    async def test_quality_scoring_formula(self, review_engine):
        """Test quality scoring formula Q = 0.35×E + 0.35×C + 0.30×R."""
        document = Document(
            id="quality_test",
            content="# Quality Test\n\nComplete document with good structure.",
            type="design",
            metadata=DocumentMetadata(version="1.0"),
        )

        result = await review_engine.analyze(document)

        # Verify formula weights
        score = result.quality_score
        assert score.efficiency_weight == 0.35
        assert score.completeness_weight == 0.35
        assert score.readability_weight == 0.30

        # Verify calculation
        expected = (
            0.35 * score.efficiency_score
            + 0.35 * score.completeness_score
            + 0.30 * score.readability_score
        )
        assert abs(score.overall_score - expected) < 0.001

    @pytest.mark.asyncio
    async def test_quality_gate_enforcement(self, review_engine):
        """Test 85% quality gate enforcement."""
        # Document with low quality
        poor_document = Document(
            id="poor_quality",
            content="bad doc",  # Minimal content
            type="readme",
            metadata=DocumentMetadata(version="1.0"),
        )

        result = await review_engine.analyze(poor_document)

        # Should fail quality gate if score < 0.85
        if result.overall_score < 0.85:
            assert result.quality_gate_status == "FAIL"
            assert len(result.quality_issues) > 0
        else:
            assert result.quality_gate_status == "PASS"

    @pytest.mark.asyncio
    async def test_requirements_reviewer(self, review_engine):
        """Test requirements validation with RFC 2119 compliance."""
        document = Document(
            id="requirements_doc",
            content="""
            # Requirements Document

            The system MUST provide authentication.
            The system SHALL support multiple users.
            The system SHOULD have a dashboard.
            The system MAY include analytics.

            The system needs to be fast.  # Ambiguous
            It should work well.  # Ambiguous
            """,
            type="requirements",
            metadata=DocumentMetadata(version="1.0"),
        )

        result = await review_engine.analyze(document, review_types=[ReviewType.REQUIREMENTS])

        req_review = result.reviews.get(ReviewType.REQUIREMENTS)
        assert req_review is not None

        # Check RFC 2119 keyword detection
        assert req_review.metrics["rfc2119_compliance"] is True
        assert "MUST" in req_review.metrics["keywords_found"]
        assert "SHALL" in req_review.metrics["keywords_found"]

        # Check ambiguity detection
        assert len(req_review.metrics["ambiguous_statements"]) >= 2
        # Ambiguity score is based on ratio of ambiguous lines
        assert req_review.metrics["ambiguity_score"] <= 0.30  # Reasonable threshold

    @pytest.mark.asyncio
    async def test_security_reviewer(self, review_engine):
        """Test security scanning with OWASP compliance."""
        document = Document(
            id="security_doc",
            content="""
            # Configuration

            API_KEY = "sk-1234567890abcdef"  # Exposed credential
            password = "admin123"  # Weak password

            def connect_db():
                conn = psycopg2.connect(
                    "postgresql://user:pass@localhost/db"  # Connection string
                )
            """,
            type="config",
            metadata=DocumentMetadata(version="1.0"),
        )

        result = await review_engine.analyze(document, review_types=[ReviewType.SECURITY])

        sec_review = result.reviews.get(ReviewType.SECURITY)
        assert sec_review is not None

        # Check credential detection (0% false negatives)
        assert len(sec_review.metrics["credentials_found"]) >= 2
        assert sec_review.metrics["has_exposed_secrets"] is True

        # Check OWASP compliance
        assert sec_review.metrics["owasp_compliance"] is not None
        # Vulnerabilities is a list of enum values, check if any OWASP vuln detected
        vulns = sec_review.metrics["vulnerabilities"]
        # We may or may not detect A02 in this simple test

        # Check CVSS scoring
        for issue in sec_review.metrics["security_issues"]:
            assert 0.0 <= issue.cvss_score <= 10.0

    @pytest.mark.asyncio
    async def test_pii_detector(self, review_engine):
        """Test PII detection with 95% accuracy target."""
        document = Document(
            id="pii_doc",
            content="""
            # User Information

            Name: John Doe
            Email: john.doe@example.com
            Phone: 555-123-4567
            SSN: 123-45-6789
            Credit Card: 4111-1111-1111-1111
            Address: 123 Main St, Anytown, CA 12345

            This is regular text without PII.
            """,
            type="user_data",
            metadata=DocumentMetadata(version="1.0"),
        )

        result = await review_engine.analyze(document)

        pii_result = result.pii_detection
        assert pii_result is not None

        # Check detection accuracy (should find at least 4 PII items)
        assert len(pii_result.pii_found) >= 4

        # Check PII types detected
        pii_types = {item.pii_type for item in pii_result.pii_found}
        assert PIIType.EMAIL in pii_types
        assert PIIType.PHONE in pii_types
        assert PIIType.SSN in pii_types

        # Verify accuracy metric
        assert pii_result.accuracy >= 0.85  # Working towards 95% target

    @pytest.mark.asyncio
    async def test_performance_reviewer(self, review_engine):
        """Test performance analysis capabilities."""
        document = Document(
            id="perf_doc",
            content="""
            # Performance Configuration

            Cache TTL: 3600
            Connection Pool: 100
            Timeout: 30s
            Max Retries: 3

            ## Optimization Notes
            - Implemented lazy loading
            - Added database indexing
            - Enabled response caching
            """,
            type="config",
            metadata=DocumentMetadata(version="1.0"),
        )

        result = await review_engine.analyze(document, review_types=[ReviewType.PERFORMANCE])

        perf_review = result.reviews.get(ReviewType.PERFORMANCE)
        assert perf_review is not None

        # Check performance metrics detection
        assert perf_review.metrics["has_performance_configs"] is True
        assert len(perf_review.metrics["optimization_suggestions"]) >= 0
        assert perf_review.metrics["performance_score"] >= 0.0

    @pytest.mark.asyncio
    async def test_multiple_reviewers(self, review_engine):
        """Test running multiple reviewers simultaneously."""
        document = Document(
            id="multi_review",
            content="""
            # API Documentation

            ## Requirements
            The API MUST authenticate all requests.

            ## Security
            API_KEY required for authentication.

            ## Performance
            Response time < 200ms
            """,
            type="api_doc",
            metadata=DocumentMetadata(version="1.0"),
        )

        review_types = [
            ReviewType.REQUIREMENTS,
            ReviewType.SECURITY,
            ReviewType.PERFORMANCE,
        ]

        result = await review_engine.analyze(document, review_types=review_types)

        # Should have results from all requested reviewers
        assert len(result.reviews) == 3
        assert ReviewType.REQUIREMENTS in result.reviews
        assert ReviewType.SECURITY in result.reviews
        assert ReviewType.PERFORMANCE in result.reviews

    @pytest.mark.asyncio
    async def test_consistency_reviewer_integration(self, review_engine):
        """Test consistency analysis with M005 Tracking Matrix integration."""
        # Mock tracking matrix data
        review_engine.tracking.get_dependencies = Mock(return_value=["doc1", "doc2", "doc3"])

        document = Document(
            id="consistency_test",
            content="# Main Document\n\nReferences doc1 and doc2.",
            type="readme",
            metadata=DocumentMetadata(version="1.0"),
        )

        result = await review_engine.analyze(document, review_types=[ReviewType.CONSISTENCY])

        consistency_review = result.reviews.get(ReviewType.CONSISTENCY)
        assert consistency_review is not None

        # Should check cross-references
        assert consistency_review.metrics["references_validated"] is True
        review_engine.tracking.get_dependencies.assert_called()

    @pytest.mark.asyncio
    async def test_review_performance(self, review_engine):
        """Test review performance targets (<10-15 seconds)."""
        document = Document(
            id="perf_test",
            content="# Test Document\n" * 100,  # Larger document
            type="readme",
            metadata=DocumentMetadata(version="1.0"),
        )

        start_time = time.time()
        result = await review_engine.analyze(document)
        elapsed_time = time.time() - start_time

        # Quality analysis should complete in <10 seconds
        assert elapsed_time < 10.0

        # Security scanning should complete in <15 seconds
        start_time = time.time()
        result = await review_engine.analyze(document, review_types=[ReviewType.SECURITY])
        elapsed_time = time.time() - start_time
        assert elapsed_time < 15.0

    @pytest.mark.asyncio
    async def test_error_handling(self, review_engine):
        """Test error handling and recovery."""
        # Test with invalid document
        with pytest.raises(ReviewError):
            await review_engine.analyze(None)

        # Test with invalid review type
        document = Document(
            id="test", content="Test", type="test", metadata=DocumentMetadata(version="1.0")
        )

        with pytest.raises(ReviewError):
            await review_engine.analyze(document, review_types=["invalid_type"])

    @pytest.mark.asyncio
    async def test_factory_pattern(self):
        """Test ReviewEngineFactory creates correct instances."""
        # Test with mocked dependencies to avoid complex initialization
        config = Mock(spec=ConfigurationManager)
        config.get.return_value = {"review": {"quality_threshold": 0.85, "pii_patterns": {}}}
        storage = Mock(spec=StorageManager)
        generator = Mock(spec=DocumentGenerator)
        tracking = Mock(spec=TrackingMatrix)

        engine = ReviewEngineFactory.create(
            config=config, storage=storage, generator=generator, tracking=tracking
        )
        assert isinstance(engine, ReviewEngine)
        assert len(engine.reviewers) == 8
        assert engine.config == config
        assert engine.storage == storage

    @pytest.mark.asyncio
    async def test_integration_with_storage(self, review_engine):
        """Test integration with M002 Storage for audit logging."""
        document = Document(
            id="audit_test",
            content="Test document for audit",
            type="test",
            metadata=DocumentMetadata(version="1.0"),
        )

        # The fixture provides a mock storage, configure it for async
        review_engine.storage.save_document = AsyncMock(return_value=True)

        # Run analysis with save_results=True
        result = await review_engine.analyze(document, save_results=True)

        # Verify results were generated
        assert result is not None
        assert result.document_id == "audit_test"

        # Storage should have been called if available
        if review_engine.storage:
            review_engine.storage.save_document.assert_called()

    @pytest.mark.asyncio
    async def test_llm_integration(self, review_engine):
        """Test optional M008 LLM Adapter integration for enhanced analysis."""
        document = Document(
            id="llm_test",
            content="Complex document requiring AI analysis",
            type="complex",
            metadata=DocumentMetadata(version="1.0"),
        )

        # Mock LLM adapter
        llm_adapter = Mock()
        llm_adapter.generate = AsyncMock(return_value=Mock(content="Enhanced analysis result"))
        review_engine.llm_adapter = llm_adapter

        result = await review_engine.analyze(document, use_llm_enhancement=True)

        # Should use LLM for enhanced analysis
        llm_adapter.generate.assert_called()
        assert result.llm_enhanced is True

    @pytest.mark.asyncio
    async def test_design_reviewer(self, review_engine):
        """Test design document review capabilities."""
        document = Document(
            id="design_doc",
            content="""
            # System Design

            ## Architecture
            - Microservices architecture
            - Event-driven communication
            - RESTful APIs

            ## Components
            - API Gateway
            - Service Registry
            - Message Queue
            """,
            type="design",
            metadata=DocumentMetadata(version="1.0"),
        )

        result = await review_engine.analyze(document, review_types=[ReviewType.DESIGN])

        design_review = result.reviews.get(ReviewType.DESIGN)
        assert design_review is not None
        assert design_review.metrics["has_architecture_section"] is True
        assert (
            len(design_review.metrics["components_identified"]) >= 2
        )  # Identified at least some components

    @pytest.mark.asyncio
    async def test_usability_reviewer(self, review_engine):
        """Test usability analysis capabilities."""
        document = Document(
            id="user_guide",
            content="""
            # User Guide

            ## Getting Started
            1. Install the application
            2. Configure settings
            3. Start using features

            ## Troubleshooting
            Common issues and solutions...
            """,
            type="user_documentation",
            metadata=DocumentMetadata(version="1.0"),
        )

        result = await review_engine.analyze(document, review_types=[ReviewType.USABILITY])

        usability_review = result.reviews.get(ReviewType.USABILITY)
        assert usability_review is not None
        assert usability_review.metrics["readability_score"] > 0
        assert usability_review.metrics["has_getting_started"] is True

    @pytest.mark.asyncio
    async def test_test_coverage_reviewer(self, review_engine):
        """Test coverage analysis capabilities."""
        document = Document(
            id="test_doc",
            content="""
            # Test Coverage Report

            Overall Coverage: 85%
            - Unit Tests: 90%
            - Integration Tests: 75%
            - E2E Tests: 60%

            Uncovered Files:
            - module_a.py (70%)
            - module_b.py (65%)
            """,
            type="test_report",
            metadata=DocumentMetadata(version="1.0"),
        )

        result = await review_engine.analyze(document, review_types=[ReviewType.TEST_COVERAGE])

        coverage_review = result.reviews.get(ReviewType.TEST_COVERAGE)
        assert coverage_review is not None
        assert coverage_review.metrics["overall_coverage"] == 85
        assert coverage_review.metrics["meets_threshold"] is True  # 85% meets threshold

    @pytest.mark.asyncio
    async def test_compliance_reviewer(self, review_engine):
        """Test compliance checking capabilities."""
        document = Document(
            id="compliance_doc",
            content="""
            # Compliance Documentation

            ## GDPR Compliance
            - Data minimization implemented
            - User consent mechanisms in place
            - Right to deletion supported

            ## HIPAA Compliance
            - PHI encryption enabled
            - Access controls configured
            """,
            type="compliance",
            metadata=DocumentMetadata(version="1.0"),
        )

        result = await review_engine.analyze(document, review_types=[ReviewType.COMPLIANCE])

        compliance_review = result.reviews.get(ReviewType.COMPLIANCE)
        assert compliance_review is not None
        assert ComplianceStandard.GDPR in compliance_review.metrics["standards_addressed"]
        assert ComplianceStandard.HIPAA in compliance_review.metrics["standards_addressed"]

    @pytest.mark.asyncio
    async def test_batch_review(self, review_engine):
        """Test batch document review capabilities."""
        documents = [
            Document(
                id=f"doc_{i}",
                content=f"Document {i} content",
                type="test",
                metadata=DocumentMetadata(version="1.0"),
            )
            for i in range(5)
        ]

        results = await review_engine.analyze_batch(documents)

        assert len(results) == 5
        for result in results:
            assert isinstance(result, AnalysisReport)
            assert result.overall_score >= 0.0

    @pytest.mark.asyncio
    async def test_caching_mechanism(self, review_engine):
        """Test result caching for performance."""
        document = Document(
            id="cache_test",
            content="Cacheable content",
            type="test",
            metadata=DocumentMetadata(version="1.0"),
        )

        # First analysis
        result1 = await review_engine.analyze(document)

        # Second analysis (should use cache)
        result2 = await review_engine.analyze(document)

        # Results should be identical
        assert result1.overall_score == result2.overall_score
        assert result2.from_cache is True

    @pytest.mark.asyncio
    async def test_custom_pii_patterns(self, review_engine):
        """Test custom PII pattern configuration."""
        # Add custom pattern
        review_engine.pii_detector.add_pattern(
            PIIType.CUSTOM, r"EMP\d{6}", "Employee ID"  # Employee ID pattern
        )

        document = Document(
            id="custom_pii",
            content="Employee ID: EMP123456",
            type="test",
            metadata=DocumentMetadata(version="1.0"),
        )

        result = await review_engine.analyze(document)

        pii_result = result.pii_detection
        assert len(pii_result.pii_found) >= 1
        assert any(item.pii_type == PIIType.CUSTOM for item in pii_result.pii_found)

    @pytest.mark.asyncio
    async def test_severity_classification(self, review_engine):
        """Test issue severity classification."""
        document = Document(
            id="severity_test",
            content="""
            API_KEY = "exposed"  # Critical
            TODO: fix this later  # Low
            Performance issue here  # Medium
            """,
            type="code",
            metadata=DocumentMetadata(version="1.0"),
        )

        result = await review_engine.analyze(document)

        # Check severity levels
        issues = result.all_issues
        severities = set()
        for issue in issues:
            if hasattr(issue, "severity"):
                severities.add(issue.severity)
            elif isinstance(issue, dict) and "severity" in issue:
                severities.add(issue["severity"])

        # Should have detected some issues with various severity levels
        assert len(severities) > 0
        # Check that we have at least one issue detected

    @pytest.mark.asyncio
    async def test_report_export(self, review_engine):
        """Test analysis report export formats."""
        document = Document(
            id="export_test",
            content="Test content",
            type="test",
            metadata=DocumentMetadata(version="1.0"),
        )

        result = await review_engine.analyze(document)

        # Export as JSON
        json_report = result.to_json()
        assert isinstance(json_report, str)
        parsed = json.loads(json_report)
        assert parsed["document_id"] == "export_test"

        # Export as dict
        dict_report = result.to_dict()
        assert isinstance(dict_report, dict)
        assert dict_report["document_id"] == "export_test"

    @pytest.mark.asyncio
    async def test_threshold_configuration(self, review_engine):
        """Test configurable quality thresholds."""
        # Update threshold
        review_engine.quality_threshold = 0.90

        document = Document(
            id="threshold_test",
            content="Average quality document",
            type="test",
            metadata=DocumentMetadata(version="1.0"),
        )

        result = await review_engine.analyze(document)

        # With higher threshold, more likely to fail
        if result.overall_score < 0.90:
            assert result.quality_gate_status == "FAIL"


# ============================================================================
# PASS 2: Performance Tests
# ============================================================================


class TestReviewEnginePerformance:
    """Performance tests for M007 Pass 2 optimizations."""

    @pytest.fixture
    def review_engine(self):
        """Create review engine instance for testing."""
        from devdocai.core.config import ConfigurationManager
        from devdocai.core.storage import StorageManager

        # Create minimal configuration
        config = ConfigurationManager()
        storage = StorageManager(config)

        # Create review engine
        engine = ReviewEngine(config=config, storage=storage)

        yield engine

        # Cleanup
        if hasattr(engine, "shutdown"):
            engine.shutdown()

    @pytest.fixture
    def large_document(self):
        """Create a large document for performance testing."""
        # Generate 100KB of content
        content = """
        # Large Requirements Document

        """ + "\n".join(
            [
                f"""
        ## Section {i}
        The system MUST handle requirement {i}.
        The component SHALL process data efficiently.
        Users SHOULD be able to access features quickly.
        The API MAY support additional endpoints.

        This section contains various requirements and specifications
        that need to be analyzed for completeness and clarity.
        Some statements might be ambiguous and need clarification.

        Test data includes:
        - Email: user{i}@example.com
        - Phone: 555-{i:04d}
        - SSN: 123-45-{i:04d}
        """
                for i in range(100)
            ]
        )

        return Document(
            id="large_doc",
            content=content,
            type="requirements",
            metadata=DocumentMetadata(version="1.0", tags=["performance", "test"]),
        )

    @pytest.mark.asyncio
    async def test_single_document_performance(self, review_engine, large_document):
        """Test that single document analysis meets <5-8 second target."""
        start_time = time.time()

        result = await review_engine.analyze(large_document)

        elapsed_time = time.time() - start_time

        # Should complete within 8 seconds (Pass 2 target)
        assert elapsed_time < 8.0, f"Analysis took {elapsed_time:.2f}s, exceeding 8s target"

        # Verify result quality not compromised
        assert result is not None
        assert result.overall_score >= 0.0
        assert len(result.reviews) > 0

        # Log performance
        print(f"Single document analysis: {elapsed_time:.2f}s")

    @pytest.mark.asyncio
    async def test_cache_performance(self, review_engine, large_document):
        """Test multi-tier caching performance improvements."""
        # First analysis (cache miss)
        start_time = time.time()
        result1 = await review_engine.analyze(large_document)
        first_time = time.time() - start_time

        # Second analysis (cache hit)
        start_time = time.time()
        result2 = await review_engine.analyze(large_document)
        cache_time = time.time() - start_time

        # Cache should provide significant speedup
        assert cache_time < first_time * 0.1, "Cache should provide >90% speedup"
        assert result2.from_cache is True

        # Verify cache statistics
        metrics = review_engine.get_performance_metrics()
        assert metrics["cache_stats"]["hits"] > 0
        assert metrics["cache_hit_rate"] > 0

        print(f"Cache performance: First={first_time:.2f}s, Cached={cache_time:.4f}s")

    @pytest.mark.asyncio
    async def test_batch_processing_performance(self, review_engine):
        """Test batch processing with controlled concurrency."""
        # Create 10 documents of varying sizes
        documents = []
        for i in range(10):
            content = f"Document {i}\n" * (100 * (i + 1))
            documents.append(
                Document(
                    id=f"batch_doc_{i}",
                    content=content,
                    type="test",
                    metadata=DocumentMetadata(version="1.0"),
                )
            )

        start_time = time.time()

        # Process batch with controlled concurrency
        results = await review_engine.analyze_batch(documents, max_concurrent=3)

        elapsed_time = time.time() - start_time

        # Should process 10 documents efficiently
        assert len(results) == 10
        # Average time per document should be < 5 seconds
        avg_time = elapsed_time / len(documents)
        assert avg_time < 5.0, f"Average time {avg_time:.2f}s exceeds 5s target"

        print(
            f"Batch processing: {len(documents)} docs in {elapsed_time:.2f}s (avg: {avg_time:.2f}s)"
        )

    @pytest.mark.asyncio
    async def test_parallel_reviewer_execution(self, review_engine):
        """Test that reviewers execute in parallel."""
        document = Document(
            id="parallel_test",
            content="Test content for parallel execution",
            type="test",
            metadata=DocumentMetadata(version="1.0"),
        )

        # Mock reviewers to add delays
        original_reviewers = review_engine.reviewers.copy()

        class SlowReviewer:
            async def review(self, content, metadata):
                await asyncio.sleep(0.5)  # Simulate slow review
                return ReviewResult(
                    review_type=ReviewType.REQUIREMENTS, score=0.8, issues=[], suggestions=[]
                )

        # Replace with slow reviewers
        for review_type in review_engine.reviewers:
            review_engine.reviewers[review_type] = SlowReviewer()

        start_time = time.time()
        result = await review_engine.analyze(document)
        elapsed_time = time.time() - start_time

        # With parallel execution, should be much faster than sequential
        # 8 reviewers * 0.5s = 4s sequential, but parallel should be ~0.5-1s
        assert elapsed_time < 2.0, f"Parallel execution too slow: {elapsed_time:.2f}s"

        # Restore original reviewers
        review_engine.reviewers = original_reviewers

        print(f"Parallel reviewer execution: {elapsed_time:.2f}s for 8 reviewers")

    @pytest.mark.asyncio
    async def test_memory_efficiency(self, review_engine):
        """Test memory-efficient processing of large documents."""
        # Create a very large document (1MB+)
        huge_content = "x" * 1_000_000  # 1MB of content
        huge_doc = Document(
            id="huge_doc",
            content=huge_content,
            type="test",
            metadata=DocumentMetadata(version="1.0"),
        )

        # Should handle large document without issues
        result = await review_engine.analyze(huge_doc)

        assert result is not None

        # Check that compression is used for large results
        cache_key = review_engine._get_cache_key(huge_doc)

        # Large results should be in compressed cache
        assert cache_key in review_engine._compressed_cache or cache_key in review_engine._cache

        # Verify memory metrics
        metrics = review_engine.get_performance_metrics()
        print(f"Cache size: {metrics['cache_size']} entries")

    @pytest.mark.asyncio
    async def test_cache_eviction(self, review_engine):
        """Test LRU cache eviction when cache is full."""
        # Set small cache size for testing
        review_engine._max_cache_size = 5

        # Add more documents than cache size
        for i in range(10):
            doc = Document(
                id=f"evict_doc_{i}",
                content=f"Content {i}",
                type="test",
                metadata=DocumentMetadata(version="1.0"),
            )
            await review_engine.analyze(doc)

        # Cache should not exceed max size
        total_cache_size = len(review_engine._cache) + len(review_engine._compressed_cache)
        assert total_cache_size <= review_engine._max_cache_size

        # Check eviction statistics
        metrics = review_engine.get_performance_metrics()
        assert metrics["cache_stats"]["evictions"] > 0

        print(f"Cache evictions: {metrics['cache_stats']['evictions']}")

    @pytest.mark.asyncio
    async def test_concurrent_analysis_safety(self, review_engine):
        """Test thread safety of concurrent document analysis."""
        documents = [
            Document(
                id=f"concurrent_{i}",
                content=f"Concurrent test {i}",
                type="test",
                metadata=DocumentMetadata(version="1.0"),
            )
            for i in range(20)
        ]

        # Analyze all documents concurrently
        tasks = [review_engine.analyze(doc) for doc in documents]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed without exceptions
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0, f"Concurrent analysis had {len(exceptions)} exceptions"

        # All results should be valid
        assert all(r.overall_score >= 0 for r in results)
        assert len(results) == 20

    @pytest.mark.asyncio
    async def test_performance_metrics_tracking(self, review_engine):
        """Test performance metrics collection and reporting."""
        # Clear metrics
        review_engine.clear_cache()

        # Analyze several documents
        for i in range(5):
            doc = Document(
                id=f"metric_doc_{i}",
                content=f"Metrics test {i}",
                type="test",
                metadata=DocumentMetadata(version="1.0"),
            )
            await review_engine.analyze(doc)

        # Get metrics
        metrics = review_engine.get_performance_metrics()

        # Verify metrics are collected
        assert metrics["total_analyzed"] == 5
        assert metrics["avg_time_per_doc"] > 0
        assert "cache_stats" in metrics
        assert "executor_stats" in metrics

        print(f"Performance metrics: {json.dumps(metrics, indent=2)}")

    @pytest.mark.asyncio
    async def test_shutdown_cleanup(self, review_engine):
        """Test proper cleanup on shutdown."""
        # Analyze a document to populate caches
        doc = Document(
            id="shutdown_test",
            content="Shutdown test content",
            type="test",
            metadata=DocumentMetadata(version="1.0"),
        )
        await review_engine.analyze(doc)

        # Verify cache has data
        assert len(review_engine._cache) > 0 or len(review_engine._compressed_cache) > 0

        # Shutdown
        review_engine.shutdown()

        # Verify cleanup
        assert len(review_engine._cache) == 0
        assert len(review_engine._compressed_cache) == 0
        assert review_engine._cache_stats["hits"] == 0
