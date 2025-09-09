"""
Test Suite for M006 Suite Manager
Following Enhanced 4-Pass TDD Methodology - PASS 1 (85% Coverage Target)
DevDocAI v3.0.0

Tests written BEFORE implementation as per TDD principles.
Tests verify:
1. Suite generation with atomic operations
2. Consistency analysis (dependencies, gaps, cross-references)
3. Impact analysis (severity, effort estimation, circular dependencies)
4. Factory and Strategy patterns
5. Integration with M002, M004, M005
"""

import time
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio

# Import dependencies
from devdocai.core.config import ConfigurationManager
from devdocai.core.generator import DocumentGenerator
from devdocai.core.storage import Document, StorageManager

# Import will fail initially (TDD) - that's expected
from devdocai.core.suite import SuiteError, SuiteManager, SuiteManagerFactory
from devdocai.core.suite_strategies import ConsistencyStrategy, ImpactStrategy
from devdocai.core.suite_types import ChangeType, ImpactSeverity, SuiteConfig
from devdocai.core.tracking import DependencyGraph, RelationshipType, TrackingMatrix


class TestSuiteManager:
    """Test core SuiteManager functionality."""

    @pytest_asyncio.fixture
    async def suite_manager(self, tmp_path):
        """Create a SuiteManager instance with mocked dependencies."""
        # Mock dependencies
        config_manager = Mock(spec=ConfigurationManager)
        storage_manager = Mock(spec=StorageManager)
        doc_generator = Mock(spec=DocumentGenerator)
        tracking_matrix = Mock(spec=TrackingMatrix)

        # Configure mock returns
        config_manager.get.return_value = {"suite": {"max_documents": 100}}
        storage_manager.save_document = AsyncMock(return_value=True)
        storage_manager.get_document = AsyncMock(return_value=None)

        # Make generator return different documents based on context
        async def generate_doc(template, context):
            return Document(
                id=context.get("id", "test_doc"),
                content=f"Generated content for {context.get('id', 'test')}",
                type=context.get("type", "markdown"),
            )

        doc_generator.generate = AsyncMock(side_effect=generate_doc)

        # Create suite manager
        manager = SuiteManager(
            config=config_manager,
            storage=storage_manager,
            generator=doc_generator,
            tracking=tracking_matrix,
        )

        return manager

    @pytest.mark.asyncio
    async def test_suite_generation_atomic(self, suite_manager):
        """Test that suite generation is atomic (all or nothing)."""
        # Prepare suite configuration
        suite_config = SuiteConfig(
            suite_id="test_suite",
            documents=[
                {"id": "readme", "type": "readme", "template": "readme.md"},
                {"id": "api_doc", "type": "api", "template": "api.md"},
                {"id": "changelog", "type": "changelog", "template": "changelog.md"},
            ],
            cross_references={"readme": ["api_doc", "changelog"], "api_doc": ["readme"]},
        )

        # Generate suite
        result = await suite_manager.generate_suite(suite_config)

        # Verify atomic operation
        assert result.success is True
        assert result.suite_id == "test_suite"
        assert len(result.documents) == 3
        assert result.generation_time < 5.0  # Performance requirement
        assert result.integrity_check is True

        # Verify cross-references established
        assert "readme" in result.cross_references
        assert "api_doc" in result.cross_references["readme"]

    @pytest.mark.asyncio
    async def test_suite_generation_rollback_on_failure(self, suite_manager):
        """Test that suite generation rolls back on failure."""
        # Configure mock to fail on second document
        suite_manager.generator.generate = AsyncMock(
            side_effect=[
                Document(id="doc1", content="Content 1", type="markdown"),
                Exception("Generation failed"),
                Document(id="doc3", content="Content 3", type="markdown"),
            ]
        )

        suite_config = SuiteConfig(
            suite_id="failing_suite",
            documents=[
                {"id": "doc1", "type": "readme"},
                {"id": "doc2", "type": "api"},  # This will fail
                {"id": "doc3", "type": "changelog"},
            ],
        )

        # Attempt generation
        with pytest.raises(SuiteError) as exc_info:
            await suite_manager.generate_suite(suite_config)

        # Verify rollback occurred
        assert "Generation failed" in str(exc_info.value)
        # Verify no documents were saved (atomic rollback)
        suite_manager.storage.save_document.assert_not_called()

    @pytest.mark.asyncio
    async def test_consistency_analysis_dependencies(self, suite_manager):
        """Test consistency analysis for dependency tracking (AC-007.1)."""
        # Setup mock tracking matrix with dependencies
        suite_manager.tracking.get_dependencies = AsyncMock(
            return_value={
                "readme": ["api_doc", "changelog"],
                "api_doc": ["config_doc"],
                "changelog": [],
            }
        )

        # Mock storage to return specific documents
        suite_manager.storage.list_documents = AsyncMock(
            return_value=["readme", "api_doc", "changelog", "config_doc"]
        )

        async def get_doc(doc_id):
            # Map doc_id to expected types
            type_map = {
                "readme": "readme",
                "api_doc": "api",
                "changelog": "changelog",
                "config_doc": "config",
            }
            return Document(
                id=doc_id, content=f"Content for {doc_id}", type=type_map.get(doc_id, "markdown")
            )

        suite_manager.storage.get_document = AsyncMock(side_effect=get_doc)

        # Run consistency analysis
        report = await suite_manager.analyze_consistency("test_suite")

        # Verify dependency tracking
        assert report.suite_id == "test_suite"
        assert report.total_documents == 4
        assert len(report.dependency_issues) == 0  # No issues if all resolve
        assert report.consistency_score >= 0.95  # High consistency

    @pytest.mark.asyncio
    async def test_consistency_analysis_gap_detection(self, suite_manager):
        """Test consistency analysis for gap detection (AC-007.2)."""
        # Setup mock with missing documents
        suite_manager.storage.list_documents = AsyncMock(
            return_value=["readme", "api_doc"]  # Missing changelog and config_doc
        )

        # Mock get_document to return proper typed documents
        async def get_doc(doc_id):
            type_map = {"readme": "readme", "api_doc": "api"}
            return Document(
                id=doc_id, content=f"Content for {doc_id}", type=type_map.get(doc_id, "markdown")
            )

        suite_manager.storage.get_document = AsyncMock(side_effect=get_doc)

        suite_manager.tracking.get_expected_documents = AsyncMock(
            return_value=["readme", "api_doc", "changelog", "config_doc"]
        )

        # Run analysis
        report = await suite_manager.analyze_consistency("test_suite")

        # Verify gaps detected
        assert len(report.documentation_gaps) == 2
        assert "changelog" in [gap.document_id for gap in report.documentation_gaps]
        assert "config_doc" in [gap.document_id for gap in report.documentation_gaps]
        assert report.coverage_percentage == 50.0  # 2 of 4 documents

    @pytest.mark.asyncio
    async def test_consistency_analysis_cross_references(self, suite_manager):
        """Test cross-reference validation (AC-007.3)."""
        # Setup broken cross-references
        suite_manager.tracking.validate_references = AsyncMock(
            return_value={
                "readme": {"valid": ["api_doc"], "broken": ["deleted_doc", "missing_doc"]},
                "api_doc": {"valid": ["readme"], "broken": []},
            }
        )

        # Run analysis
        report = await suite_manager.analyze_consistency("test_suite")

        # Verify broken references detected
        assert len(report.broken_references) == 2
        assert report.reference_integrity < 1.0
        assert "deleted_doc" in report.broken_references
        assert "missing_doc" in report.broken_references

    @pytest.mark.asyncio
    async def test_consistency_analysis_progressive_disclosure(self, suite_manager):
        """Test progressive disclosure formatting (AC-007.6)."""
        # Run analysis
        report = await suite_manager.analyze_consistency("complex_suite")

        # Verify progressive disclosure structure
        assert hasattr(report, "summary")  # High-level summary
        assert hasattr(report, "details")  # Detailed findings
        assert hasattr(report, "recommendations")  # Actionable items

        # Summary should be concise
        assert len(report.summary) <= 500  # Character limit for summary

        # Details should be comprehensive
        assert report.details.dependencies is not None
        assert report.details.gaps is not None
        assert report.details.references is not None

    @pytest.mark.asyncio
    async def test_impact_analysis_severity_assessment(self, suite_manager):
        """Test impact severity assessment (AC-008.1)."""
        # Setup mock tracking for impact analysis
        suite_manager.tracking.analyze_impact = AsyncMock(
            return_value={
                "direct": ["api_doc", "config_doc"],
                "indirect": ["changelog", "readme"],
                "severity": "high",
            }
        )

        # Analyze impact of change
        impact = await suite_manager.analyze_impact(
            document_id="core_module", change_type=ChangeType.BREAKING_CHANGE
        )

        # Verify severity assessment
        assert impact.severity == ImpactSeverity.HIGH
        assert len(impact.directly_affected) == 2
        assert len(impact.indirectly_affected) == 2
        assert impact.total_affected == 4

    @pytest.mark.asyncio
    async def test_impact_analysis_effort_estimation(self, suite_manager):
        """Test effort estimation within ±20% accuracy (AC-008.2)."""
        # Analyze impact with effort estimation
        impact = await suite_manager.analyze_impact(
            document_id="api_endpoint", change_type=ChangeType.MODIFICATION
        )

        # Verify effort estimation
        assert impact.estimated_effort_hours > 0
        assert impact.effort_confidence >= 0.8  # 80% confidence minimum
        assert impact.effort_range.min_hours <= impact.estimated_effort_hours
        assert impact.effort_range.max_hours >= impact.estimated_effort_hours

        # Verify ±20% accuracy range
        variance = (impact.effort_range.max_hours - impact.effort_range.min_hours) / 2
        assert variance <= impact.estimated_effort_hours * 0.2

    @pytest.mark.asyncio
    async def test_impact_analysis_circular_dependency_detection(self, suite_manager):
        """Test circular dependency detection with resolution paths."""
        # Setup circular dependencies
        suite_manager.tracking.detect_circular_references = AsyncMock(
            return_value=[
                ["doc_a", "doc_b", "doc_c", "doc_a"],
                ["module_1", "module_2", "module_1"],
            ]
        )

        # Analyze impact
        impact = await suite_manager.analyze_impact(
            document_id="doc_a", change_type=ChangeType.REFACTORING
        )

        # Verify circular dependencies detected
        assert len(impact.circular_dependencies) == 2
        assert impact.has_circular_dependencies is True

        # Verify resolution paths provided
        assert len(impact.resolution_suggestions) > 0
        assert "break dependency" in impact.resolution_suggestions[0].lower()

    @pytest.mark.asyncio
    async def test_impact_analysis_accuracy_requirement(self, suite_manager):
        """Test 95% accuracy requirement for direct dependencies."""
        # Run multiple impact analyses to test accuracy
        results = []
        for _ in range(20):  # Statistical sample
            impact = await suite_manager.analyze_impact(
                document_id="test_doc", change_type=ChangeType.UPDATE
            )
            results.append(impact.accuracy_score)

        # Calculate average accuracy
        avg_accuracy = sum(results) / len(results)
        assert avg_accuracy >= 0.95  # 95% accuracy requirement

    @pytest.mark.asyncio
    async def test_performance_suite_generation(self, suite_manager):
        """Test suite generation performance (<5 seconds for 10 documents)."""
        # Create configuration for 10 documents
        suite_config = SuiteConfig(
            suite_id="perf_test",
            documents=[{"id": f"doc_{i}", "type": "markdown"} for i in range(10)],
        )

        # Measure generation time
        start_time = time.time()
        result = await suite_manager.generate_suite(suite_config)
        generation_time = time.time() - start_time

        # Verify performance requirement
        assert generation_time < 5.0  # 5 seconds maximum
        assert result.success is True
        assert len(result.documents) == 10

    @pytest.mark.asyncio
    async def test_performance_consistency_analysis(self, suite_manager):
        """Test consistency analysis performance (<2 seconds for 100 documents)."""
        # Mock 100 documents
        suite_manager.storage.list_documents = AsyncMock(
            return_value=[f"doc_{i}" for i in range(100)]
        )

        # Measure analysis time
        start_time = time.time()
        report = await suite_manager.analyze_consistency("large_suite")
        analysis_time = time.time() - start_time

        # Verify performance requirement
        assert analysis_time < 2.0  # 2 seconds maximum
        assert report.total_documents == 100

    @pytest.mark.asyncio
    async def test_performance_impact_analysis(self, suite_manager):
        """Test impact analysis performance (<1 second response)."""
        # Measure impact analysis time
        start_time = time.time()
        impact = await suite_manager.analyze_impact(
            document_id="critical_doc", change_type=ChangeType.DELETION
        )
        analysis_time = time.time() - start_time

        # Verify performance requirement
        assert analysis_time < 1.0  # 1 second maximum
        assert impact is not None


class TestSuiteManagerFactory:
    """Test Factory pattern implementation."""

    def test_factory_creates_suite_manager(self):
        """Test that factory creates appropriate suite manager."""
        factory = SuiteManagerFactory()

        # Create with default strategy
        manager = factory.create_suite_manager()
        assert isinstance(manager, SuiteManager)

        # Create with custom strategies
        manager = factory.create_suite_manager(
            consistency_strategy="advanced", impact_strategy="ml_based"
        )
        assert manager is not None

    def test_factory_strategy_selection(self):
        """Test strategy selection in factory."""
        factory = SuiteManagerFactory()

        # Test consistency strategy selection
        strategy = factory.get_consistency_strategy("basic")
        assert isinstance(strategy, ConsistencyStrategy)

        # Test impact strategy selection
        strategy = factory.get_impact_strategy("graph_based")
        assert isinstance(strategy, ImpactStrategy)

    def test_factory_invalid_strategy(self):
        """Test factory handles invalid strategies gracefully."""
        factory = SuiteManagerFactory()

        with pytest.raises(ValueError) as exc_info:
            factory.create_suite_manager(consistency_strategy="invalid")

        assert "Unknown consistency strategy" in str(exc_info.value)


class TestConsistencyStrategies:
    """Test different consistency analysis strategies."""

    @pytest.fixture
    def basic_strategy(self):
        """Create basic consistency strategy."""
        from devdocai.core.suite import BasicConsistencyStrategy

        return BasicConsistencyStrategy()

    @pytest.fixture
    def advanced_strategy(self):
        """Create advanced consistency strategy."""
        from devdocai.core.suite import AdvancedConsistencyStrategy

        return AdvancedConsistencyStrategy()

    @pytest.mark.asyncio
    async def test_basic_consistency_strategy(self, basic_strategy):
        """Test basic consistency strategy implementation."""
        # Mock document data
        documents = [
            Document(id="doc1", content="Content 1", type="markdown"),
            Document(id="doc2", content="Content 2", type="markdown"),
        ]

        # Analyze consistency
        report = await basic_strategy.analyze(documents)

        # Verify basic analysis
        assert report is not None
        assert report.strategy_type == "basic"
        assert report.total_documents == 2

    @pytest.mark.asyncio
    async def test_advanced_consistency_strategy(self, advanced_strategy):
        """Test advanced consistency strategy with ML features."""
        # Mock document data with complex relationships
        documents = [
            Document(id="doc1", content="References doc2 and doc3", type="markdown"),
            Document(id="doc2", content="Depends on doc1", type="markdown"),
            Document(id="doc3", content="Standalone document", type="markdown"),
        ]

        # Analyze consistency
        report = await advanced_strategy.analyze(documents)

        # Verify advanced analysis
        assert report is not None
        assert report.strategy_type == "advanced"
        assert hasattr(report, "semantic_similarity")
        assert hasattr(report, "topic_clustering")


class TestImpactStrategies:
    """Test different impact analysis strategies."""

    @pytest.fixture
    def bfs_strategy(self):
        """Create BFS-based impact strategy."""
        from devdocai.core.suite import BFSImpactStrategy

        return BFSImpactStrategy()

    @pytest.fixture
    def graph_strategy(self):
        """Create graph-based impact strategy."""
        from devdocai.core.suite import GraphImpactStrategy

        return GraphImpactStrategy()

    @pytest.mark.asyncio
    async def test_bfs_impact_strategy(self, bfs_strategy):
        """Test BFS-based impact analysis."""
        # Setup dependency graph
        graph = DependencyGraph()
        graph.add_node("doc1")
        graph.add_node("doc2")
        graph.add_node("doc3")
        graph.add_edge("doc1", "doc2", RelationshipType.DEPENDS_ON)
        graph.add_edge("doc2", "doc3", RelationshipType.REFERENCES)

        # Analyze impact
        impact = await bfs_strategy.analyze(
            document_id="doc1", change_type=ChangeType.MODIFICATION, graph=graph
        )

        # Verify BFS traversal
        assert "doc2" in impact.directly_affected
        assert "doc3" in impact.indirectly_affected

    @pytest.mark.asyncio
    async def test_graph_impact_strategy_with_weights(self, graph_strategy):
        """Test graph-based impact analysis with weighted edges."""
        # Setup weighted dependency graph
        graph = DependencyGraph()
        graph.add_weighted_edge("doc1", "doc2", weight=0.9)  # Strong dependency
        graph.add_weighted_edge("doc1", "doc3", weight=0.3)  # Weak dependency
        graph.add_weighted_edge("doc2", "doc4", weight=0.7)  # Medium dependency

        # Analyze impact
        impact = await graph_strategy.analyze(
            document_id="doc1", change_type=ChangeType.BREAKING_CHANGE, graph=graph
        )

        # Verify weighted impact analysis
        assert impact.impact_scores["doc2"] > impact.impact_scores["doc3"]
        assert impact.severity == ImpactSeverity.HIGH  # Due to breaking change


class TestIntegration:
    """Test integration with other modules."""

    @pytest.mark.asyncio
    async def test_integration_with_storage(self, tmp_path):
        """Test integration with M002 StorageManager."""
        # Create real storage manager
        storage = StorageManager(str(tmp_path / "test.db"))
        await storage.initialize()

        # Create suite manager with real storage
        suite_manager = SuiteManager(
            config=Mock(spec=ConfigurationManager),
            storage=storage,
            generator=Mock(spec=DocumentGenerator),
            tracking=Mock(spec=TrackingMatrix),
        )

        # Test document persistence
        doc = Document(id="test_doc", content="Test content", type="markdown")
        await suite_manager.save_document(doc)

        # Verify document saved
        retrieved = await storage.get_document("test_doc")
        assert retrieved is not None
        assert retrieved.content == "Test content"

    @pytest.mark.asyncio
    async def test_integration_with_generator(self):
        """Test integration with M004 DocumentGenerator."""
        # Create mock generator with realistic behavior
        generator = Mock(spec=DocumentGenerator)
        generator.generate = AsyncMock(
            side_effect=lambda template, context: Document(
                id=context.get("id", "generated"),
                content=f"Generated from {template}",
                type="markdown",
            )
        )

        # Create suite manager
        suite_manager = SuiteManager(
            config=Mock(spec=ConfigurationManager),
            storage=Mock(spec=StorageManager),
            generator=generator,
            tracking=Mock(spec=TrackingMatrix),
        )

        # Test generation integration
        suite_config = SuiteConfig(
            suite_id="test", documents=[{"id": "readme", "template": "readme.md"}]
        )

        result = await suite_manager.generate_suite(suite_config)
        assert result.documents[0].content == "Generated from readme.md"

    @pytest.mark.asyncio
    async def test_integration_with_tracking_matrix(self):
        """Test integration with M005 TrackingMatrix."""
        # Create mock tracking matrix
        tracking = Mock(spec=TrackingMatrix)
        tracking.analyze_impact = AsyncMock(
            return_value={"affected": ["doc1", "doc2"], "severity": "medium"}
        )

        # Create suite manager
        suite_manager = SuiteManager(
            config=Mock(spec=ConfigurationManager),
            storage=Mock(spec=StorageManager),
            generator=Mock(spec=DocumentGenerator),
            tracking=tracking,
        )

        # Test tracking integration
        impact = await suite_manager.analyze_impact(
            document_id="source", change_type=ChangeType.UPDATE
        )

        # Verify tracking matrix was used
        tracking.analyze_impact.assert_called_once()
        assert len(impact.directly_affected) > 0


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_handles_storage_errors(self, suite_manager):
        """Test graceful handling of storage errors."""
        # Configure storage to fail
        suite_manager.storage.save_document = AsyncMock(
            side_effect=Exception("Storage unavailable")
        )

        # Attempt operation
        with pytest.raises(SuiteError) as exc_info:
            await suite_manager.save_document(
                Document(id="test", content="content", type="markdown")
            )

        assert "Storage unavailable" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handles_circular_dependencies(self, suite_manager):
        """Test handling of circular dependencies."""
        # Setup circular dependency
        suite_manager.tracking.detect_circular_references = AsyncMock(
            return_value=[["a", "b", "c", "a"]]
        )

        # Should not raise, but report in analysis
        impact = await suite_manager.analyze_impact(document_id="a", change_type=ChangeType.UPDATE)

        assert impact.has_circular_dependencies is True
        assert len(impact.circular_dependencies) > 0

    @pytest.mark.asyncio
    async def test_handles_empty_suite(self, suite_manager):
        """Test handling of empty suite configuration."""
        # Empty suite config
        suite_config = SuiteConfig(suite_id="empty", documents=[])

        # Should handle gracefully
        result = await suite_manager.generate_suite(suite_config)
        assert result.success is True
        assert len(result.documents) == 0

    @pytest.mark.asyncio
    async def test_handles_malformed_cross_references(self, suite_manager):
        """Test handling of malformed cross-references."""
        suite_config = SuiteConfig(
            suite_id="test",
            documents=[{"id": "doc1"}],
            cross_references={
                "doc1": ["non_existent_doc"],  # Reference to non-existent
                "also_non_existent": ["doc1"],  # Source doesn't exist
            },
        )

        # Should handle gracefully with warnings
        result = await suite_manager.generate_suite(suite_config)
        assert result.success is True
        assert len(result.warnings) > 0
        assert "non_existent_doc" in str(result.warnings)


class TestMemoryAdaptation:
    """Test memory-aware behavior based on M001 memory modes."""

    @pytest.mark.asyncio
    async def test_adapts_to_memory_mode(self, suite_manager):
        """Test that suite manager adapts to system memory mode."""
        # Test different memory modes
        memory_modes = ["minimal", "balanced", "performance", "maximum"]

        for mode in memory_modes:
            suite_manager.config.get_memory_mode = Mock(return_value=mode)

            # Verify behavior adapts
            batch_size = suite_manager.get_batch_size()
            cache_size = suite_manager.get_cache_size()

            if mode == "minimal":
                assert batch_size <= 10
                assert cache_size <= 100
            elif mode == "maximum":
                assert batch_size >= 100
                assert cache_size >= 1000


class TestSecurity:
    """Test security features."""

    @pytest.mark.asyncio
    async def test_input_validation(self, suite_manager):
        """Test input validation and sanitization."""
        # Test dangerous input
        dangerous_config = SuiteConfig(
            suite_id="../../../etc/passwd",  # Path traversal attempt
            documents=[{"id": "<script>alert('xss')</script>"}],  # XSS attempt
        )

        with pytest.raises(ValidationError) as exc_info:
            await suite_manager.generate_suite(dangerous_config)

        assert "Invalid suite_id" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_audit_logging(self, suite_manager):
        """Test that sensitive operations are logged."""
        # Enable audit logging
        suite_manager.enable_audit_logging()

        # Perform sensitive operation
        await suite_manager.delete_suite("important_suite")

        # Verify audit log created
        audit_logs = suite_manager.get_audit_logs()
        assert len(audit_logs) > 0
        assert "delete_suite" in audit_logs[-1]["action"]
        assert "important_suite" in audit_logs[-1]["target"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=devdocai.core.suite", "--cov-report=html"])
