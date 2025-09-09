"""
Tests for M005 Tracking Matrix
DevDocAI v3.0.0 - Enhanced 4-Pass TDD

Test Coverage Targets:
- Pass 1: 80% coverage (Core functionality)
- Pass 2: 85% coverage (Performance tests)
- Pass 3: 95% coverage (Security tests)
- Pass 4: 90% coverage (Integration tests)
"""

import pytest
import json
import time
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Set, Tuple

# Import module to test
import sys

sys.path.append(str(Path(__file__).parent.parent))
from devdocai.core.tracking import (
    TrackingMatrix,
    DocumentRelationship,
    OptimizedDependencyGraph,
    ParallelImpactAnalysis,
    CircularReferenceError,
    TrackingError,
    RelationshipType,
    ImpactResult,
    ConsistencyReport,
    SecurityValidator,
    RateLimiter,
    AuditLogger,
    SecurityConfig,
    ResourceLimitError,
    SecurityError,
)


class TestDocumentRelationship:
    """Test the DocumentRelationship data model."""

    def test_create_relationship(self):
        """Test creating a basic document relationship."""
        rel = DocumentRelationship(
            source_id="doc1",
            target_id="doc2",
            relationship_type=RelationshipType.DEPENDS_ON,
            strength=0.8,
            metadata={"reason": "API dependency"},
        )

        assert rel.source_id == "doc1"
        assert rel.target_id == "doc2"
        assert rel.relationship_type == RelationshipType.DEPENDS_ON
        assert rel.strength == 0.8
        assert rel.metadata["reason"] == "API dependency"

    def test_relationship_validation(self):
        """Test relationship validation rules."""
        # Self-reference should raise error
        with pytest.raises(ValueError, match="cannot reference itself"):
            DocumentRelationship(
                source_id="doc1", target_id="doc1", relationship_type=RelationshipType.DEPENDS_ON
            )

        # Invalid strength should raise error
        with pytest.raises(ValueError, match="strength must be between"):
            DocumentRelationship(
                source_id="doc1",
                target_id="doc2",
                relationship_type=RelationshipType.DEPENDS_ON,
                strength=1.5,
            )

    def test_relationship_equality(self):
        """Test relationship equality comparison."""
        rel1 = DocumentRelationship("doc1", "doc2", RelationshipType.DEPENDS_ON)
        rel2 = DocumentRelationship("doc1", "doc2", RelationshipType.DEPENDS_ON)
        rel3 = DocumentRelationship("doc1", "doc3", RelationshipType.DEPENDS_ON)

        assert rel1 == rel2
        assert rel1 != rel3


class TestDependencyGraph:
    """Test the OptimizedDependencyGraph implementation."""

    def test_add_node(self):
        """Test adding nodes to the graph."""
        graph = OptimizedDependencyGraph()

        graph.add_node("doc1", {"title": "API Doc"})
        graph.add_node("doc2", {"title": "User Guide"})

        assert "doc1" in graph.nodes
        assert "doc2" in graph.nodes
        assert graph.nodes["doc1"]["title"] == "API Doc"

    def test_add_edge(self):
        """Test adding edges between nodes."""
        graph = OptimizedDependencyGraph()

        graph.add_node("doc1")
        graph.add_node("doc2")
        graph.add_edge("doc1", "doc2", RelationshipType.DEPENDS_ON, 0.9)

        assert graph.has_edge("doc1", "doc2")
        assert not graph.has_edge("doc2", "doc1")

        edge = graph.get_edge("doc1", "doc2")
        assert edge.relationship_type == RelationshipType.DEPENDS_ON
        assert edge.strength == 0.9

    def test_get_neighbors(self):
        """Test getting neighboring nodes."""
        graph = OptimizedDependencyGraph()

        # Create a simple graph: doc1 -> doc2 -> doc3
        graph.add_node("doc1")
        graph.add_node("doc2")
        graph.add_node("doc3")
        graph.add_edge("doc1", "doc2", RelationshipType.DEPENDS_ON)
        graph.add_edge("doc2", "doc3", RelationshipType.REFERENCES)

        # Outgoing neighbors
        neighbors = graph.get_neighbors("doc1", direction="outgoing")
        assert neighbors == {"doc2"}

        neighbors = graph.get_neighbors("doc2", direction="outgoing")
        assert neighbors == {"doc3"}

        # Incoming neighbors
        neighbors = graph.get_neighbors("doc2", direction="incoming")
        assert neighbors == {"doc1"}

        # Both directions
        neighbors = graph.get_neighbors("doc2", direction="both")
        assert neighbors == {"doc1", "doc3"}

    def test_detect_circular_reference(self):
        """Test circular reference detection."""
        graph = OptimizedDependencyGraph()

        # Create circular dependency: doc1 -> doc2 -> doc3 -> doc1
        graph.add_node("doc1")
        graph.add_node("doc2")
        graph.add_node("doc3")

        graph.add_edge("doc1", "doc2", RelationshipType.DEPENDS_ON)
        graph.add_edge("doc2", "doc3", RelationshipType.DEPENDS_ON)

        # This should create a cycle
        with pytest.raises(CircularReferenceError) as exc_info:
            graph.add_edge("doc3", "doc1", RelationshipType.DEPENDS_ON)

        assert "doc1" in str(exc_info.value)
        assert "doc3" in str(exc_info.value)

    def test_topological_sort(self):
        """Test topological sorting of dependencies."""
        graph = OptimizedDependencyGraph()

        # Create DAG: doc1 -> doc2 -> doc4
        #             doc1 -> doc3 -> doc4
        graph.add_node("doc1")
        graph.add_node("doc2")
        graph.add_node("doc3")
        graph.add_node("doc4")

        graph.add_edge("doc1", "doc2", RelationshipType.DEPENDS_ON)
        graph.add_edge("doc1", "doc3", RelationshipType.DEPENDS_ON)
        graph.add_edge("doc2", "doc4", RelationshipType.DEPENDS_ON)
        graph.add_edge("doc3", "doc4", RelationshipType.DEPENDS_ON)

        sorted_nodes = graph.topological_sort()

        # doc1 should come before doc2 and doc3
        assert sorted_nodes.index("doc1") < sorted_nodes.index("doc2")
        assert sorted_nodes.index("doc1") < sorted_nodes.index("doc3")

        # doc2 and doc3 should come before doc4
        assert sorted_nodes.index("doc2") < sorted_nodes.index("doc4")
        assert sorted_nodes.index("doc3") < sorted_nodes.index("doc4")


class TestImpactAnalysis:
    """Test impact analysis functionality."""

    def test_direct_impact(self):
        """Test direct impact calculation."""
        graph = OptimizedDependencyGraph()

        # Create dependency chain
        graph.add_node("api_doc")
        graph.add_node("user_guide")
        graph.add_node("tutorial")

        graph.add_edge("user_guide", "api_doc", RelationshipType.DEPENDS_ON, strength=0.9)
        graph.add_edge("tutorial", "api_doc", RelationshipType.REFERENCES, strength=0.5)

        analyzer = ParallelImpactAnalysis(graph)
        impact = analyzer.analyze_impact("api_doc")

        assert "user_guide" in impact.affected_documents
        assert "tutorial" in impact.affected_documents
        assert impact.direct_impact_count == 2
        assert impact.total_impact_score > 0

    def test_cascading_impact(self):
        """Test cascading impact through dependency chain."""
        graph = OptimizedDependencyGraph()

        # Create chain: doc1 -> doc2 -> doc3 -> doc4
        for i in range(1, 5):
            graph.add_node(f"doc{i}")

        graph.add_edge("doc2", "doc1", RelationshipType.DEPENDS_ON, strength=0.9)
        graph.add_edge("doc3", "doc2", RelationshipType.DEPENDS_ON, strength=0.8)
        graph.add_edge("doc4", "doc3", RelationshipType.DEPENDS_ON, strength=0.7)

        analyzer = ParallelImpactAnalysis(graph)
        impact = analyzer.analyze_impact("doc1", max_depth=3)

        assert len(impact.affected_documents) == 3
        assert "doc2" in impact.affected_documents
        assert "doc3" in impact.affected_documents
        assert "doc4" in impact.affected_documents

        # Check impact scores decrease with distance
        assert impact.impact_scores["doc2"] > impact.impact_scores["doc3"]
        assert impact.impact_scores["doc3"] > impact.impact_scores["doc4"]

    def test_impact_with_max_depth(self):
        """Test impact analysis with depth limit."""
        graph = OptimizedDependencyGraph()

        # Create long chain
        for i in range(1, 6):
            graph.add_node(f"doc{i}")
            if i > 1:
                graph.add_edge(f"doc{i}", f"doc{i-1}", RelationshipType.DEPENDS_ON)

        analyzer = ParallelImpactAnalysis(graph)

        # Analyze with depth limit of 2
        impact = analyzer.analyze_impact("doc1", max_depth=2)

        assert len(impact.affected_documents) == 2  # doc2 and doc3
        assert "doc2" in impact.affected_documents
        assert "doc3" in impact.affected_documents
        assert "doc4" not in impact.affected_documents

    def test_change_effort_estimation(self):
        """Test change effort estimation."""
        graph = OptimizedDependencyGraph()

        # Create documents with complexity metadata
        graph.add_node("doc1", {"complexity": 5, "size": 1000})
        graph.add_node("doc2", {"complexity": 3, "size": 500})
        graph.add_node("doc3", {"complexity": 8, "size": 2000})

        graph.add_edge("doc2", "doc1", RelationshipType.DEPENDS_ON)
        graph.add_edge("doc3", "doc1", RelationshipType.DEPENDS_ON)

        analyzer = ParallelImpactAnalysis(graph)
        impact = analyzer.analyze_impact("doc1")

        assert impact.estimated_effort > 0
        assert impact.risk_level in ["low", "medium", "high"]


class TestTrackingMatrix:
    """Test the main TrackingMatrix class."""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for testing."""
        temp_dir = tempfile.mkdtemp()
        storage_path = Path(temp_dir) / "test.db"

        # Mock storage manager
        storage = Mock()
        storage.db_path = storage_path

        yield storage

        # Cleanup
        if storage_path.exists():
            storage_path.unlink()

    @pytest.fixture
    def config_manager(self):
        """Create mock configuration manager."""
        config = Mock()
        config.get.return_value = {
            "max_documents": 1000,
            "impact_analysis": {"max_depth": 5, "accuracy_target": 0.9},
            "performance": {"cache_enabled": True, "cache_ttl": 3600},
        }
        return config

    def test_initialization(self, config_manager, temp_storage):
        """Test TrackingMatrix initialization."""
        matrix = TrackingMatrix(config_manager, temp_storage)

        assert matrix.config == config_manager
        assert matrix.storage == temp_storage
        assert matrix.graph is not None
        assert len(matrix.graph.nodes) == 0

    def test_add_document(self, config_manager, temp_storage):
        """Test adding documents to tracking matrix."""
        matrix = TrackingMatrix(config_manager, temp_storage)

        # Add document
        matrix.add_document(
            "doc1", {"title": "API Documentation", "type": "api_doc", "version": "1.0"}
        )

        assert matrix.has_document("doc1")
        doc_info = matrix.get_document_info("doc1")
        assert doc_info["title"] == "API Documentation"

    def test_add_relationship(self, config_manager, temp_storage):
        """Test adding relationships between documents."""
        matrix = TrackingMatrix(config_manager, temp_storage)

        # Add documents
        matrix.add_document("readme", {"title": "README"})
        matrix.add_document("api_doc", {"title": "API Doc"})

        # Add relationship
        matrix.add_relationship("readme", "api_doc", RelationshipType.REFERENCES, strength=0.7)

        relationships = matrix.get_relationships("readme")
        assert len(relationships) == 1
        assert relationships[0].target_id == "api_doc"

    def test_analyze_suite_consistency(self, config_manager, temp_storage):
        """Test suite consistency analysis."""
        matrix = TrackingMatrix(config_manager, temp_storage)

        # Build a documentation suite
        docs = ["readme", "api_doc", "user_guide", "changelog"]
        for doc in docs:
            matrix.add_document(doc, {"title": doc.upper()})

        # Add relationships
        matrix.add_relationship("readme", "api_doc", RelationshipType.REFERENCES)
        matrix.add_relationship("user_guide", "api_doc", RelationshipType.DEPENDS_ON)
        matrix.add_relationship("readme", "changelog", RelationshipType.REFERENCES)

        # Analyze consistency
        consistency = matrix.analyze_suite_consistency()

        assert consistency.total_documents == 4
        assert consistency.total_relationships == 3
        assert consistency.consistency_score >= 0
        assert consistency.consistency_score <= 1
        assert len(consistency.orphaned_documents) == 0
        assert len(consistency.issues) >= 0

    def test_find_orphaned_documents(self, config_manager, temp_storage):
        """Test finding orphaned documents."""
        matrix = TrackingMatrix(config_manager, temp_storage)

        # Add connected documents
        matrix.add_document("doc1", {})
        matrix.add_document("doc2", {})
        matrix.add_relationship("doc1", "doc2", RelationshipType.DEPENDS_ON)

        # Add orphaned document
        matrix.add_document("orphan", {})

        orphans = matrix.find_orphaned_documents()
        assert "orphan" in orphans
        assert "doc1" not in orphans
        assert "doc2" not in orphans

    def test_get_dependency_chain(self, config_manager, temp_storage):
        """Test getting dependency chain for a document."""
        matrix = TrackingMatrix(config_manager, temp_storage)

        # Create chain: doc1 <- doc2 <- doc3
        for i in range(1, 4):
            matrix.add_document(f"doc{i}", {})

        matrix.add_relationship("doc2", "doc1", RelationshipType.DEPENDS_ON)
        matrix.add_relationship("doc3", "doc2", RelationshipType.DEPENDS_ON)

        # Get chain from doc3
        chain = matrix.get_dependency_chain("doc3")

        assert len(chain) == 3
        assert chain == ["doc3", "doc2", "doc1"]

    def test_export_to_json(self, config_manager, temp_storage):
        """Test exporting tracking matrix to JSON."""
        matrix = TrackingMatrix(config_manager, temp_storage)

        # Build simple matrix
        matrix.add_document("doc1", {"title": "Document 1"})
        matrix.add_document("doc2", {"title": "Document 2"})
        matrix.add_relationship("doc1", "doc2", RelationshipType.REFERENCES)

        # Export to JSON
        json_data = matrix.export_to_json()
        data = json.loads(json_data)

        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1
        assert data["metadata"]["total_documents"] == 2

    def test_import_from_json(self, config_manager, temp_storage):
        """Test importing tracking matrix from JSON."""
        matrix = TrackingMatrix(config_manager, temp_storage)

        # Create JSON data
        json_data = json.dumps(
            {
                "nodes": [
                    {"id": "doc1", "metadata": {"title": "Doc 1"}},
                    {"id": "doc2", "metadata": {"title": "Doc 2"}},
                ],
                "edges": [
                    {"source": "doc1", "target": "doc2", "type": "DEPENDS_ON", "strength": 0.8}
                ],
            }
        )

        # Import
        matrix.import_from_json(json_data)

        assert matrix.has_document("doc1")
        assert matrix.has_document("doc2")
        relationships = matrix.get_relationships("doc1")
        assert len(relationships) == 1

    def test_performance_with_many_documents(self, config_manager, temp_storage):
        """Test performance with 1000+ documents."""
        matrix = TrackingMatrix(config_manager, temp_storage)

        # Add 1000 documents
        start_time = time.time()
        for i in range(1000):
            matrix.add_document(f"doc_{i}", {"index": i})

        # Add relationships (sparse graph)
        for i in range(0, 1000, 10):
            if i + 1 < 1000:
                matrix.add_relationship(f"doc_{i}", f"doc_{i+1}", RelationshipType.DEPENDS_ON)

        # Perform impact analysis (should complete in <10 seconds)
        analysis_start = time.time()
        impact = matrix.analyze_impact("doc_0")
        analysis_time = time.time() - analysis_start

        assert analysis_time < 10  # Must complete within 10 seconds
        assert len(matrix.graph.nodes) == 1000

    def test_circular_reference_prevention(self, config_manager, temp_storage):
        """Test that circular references are prevented."""
        matrix = TrackingMatrix(config_manager, temp_storage)

        # Create documents
        matrix.add_document("A", {})
        matrix.add_document("B", {})
        matrix.add_document("C", {})

        # Create chain A -> B -> C
        matrix.add_relationship("A", "B", RelationshipType.DEPENDS_ON)
        matrix.add_relationship("B", "C", RelationshipType.DEPENDS_ON)

        # Try to create cycle C -> A (should fail)
        with pytest.raises(CircularReferenceError):
            matrix.add_relationship("C", "A", RelationshipType.DEPENDS_ON)

    def test_cache_functionality(self, config_manager, temp_storage):
        """Test caching for performance optimization."""
        matrix = TrackingMatrix(config_manager, temp_storage)

        # Enable caching
        matrix.enable_caching(ttl=60)

        # Add documents and relationships
        for i in range(10):
            matrix.add_document(f"doc{i}", {})
            if i > 0:
                matrix.add_relationship(f"doc{i}", f"doc{i-1}", RelationshipType.DEPENDS_ON)

        # First impact analysis (not cached)
        start = time.time()
        impact1 = matrix.analyze_impact("doc0")
        time1 = time.time() - start

        # Second impact analysis (should be cached)
        start = time.time()
        impact2 = matrix.analyze_impact("doc0")
        time2 = time.time() - start

        assert impact1.affected_documents == impact2.affected_documents
        assert time2 < time1  # Cached should be faster


class TestIntegration:
    """Integration tests with other modules."""

    @pytest.fixture
    def full_system(self):
        """Create full system with all dependencies."""
        from devdocai.core.config import ConfigurationManager
        from devdocai.core.storage import StorageManager

        config = ConfigurationManager()
        storage = StorageManager(config)
        matrix = TrackingMatrix(config, storage)

        return config, storage, matrix

    def test_integration_with_storage(self, full_system):
        """Test integration with M002 Storage System."""
        config, storage, matrix = full_system

        # Create and store document
        from devdocai.core.storage import Document, DocumentMetadata

        doc_id = "test_doc"
        doc = Document(
            id=doc_id,
            content="Test content",
            type="document",
            metadata=DocumentMetadata(custom={"title": "Test Document"}),
        )
        storage.save_document(doc)

        # Add to tracking matrix
        matrix.add_document(doc_id, {"stored": True})

        # Verify integration
        assert matrix.has_document(doc_id)

    def test_integration_with_generator(self, full_system):
        """Test integration with M004 Document Generator."""
        config, storage, matrix = full_system

        # Simulate document generation
        generated_docs = [
            {"id": "readme", "type": "readme"},
            {"id": "api_doc", "type": "api"},
            {"id": "changelog", "type": "changelog"},
        ]

        # Add generated documents to matrix
        for doc in generated_docs:
            matrix.add_document(doc["id"], doc)

        # Add relationships based on document types
        matrix.add_relationship("readme", "api_doc", RelationshipType.REFERENCES)
        matrix.add_relationship("readme", "changelog", RelationshipType.REFERENCES)

        # Verify tracking
        relationships = matrix.get_relationships("readme")
        assert len(relationships) == 2
