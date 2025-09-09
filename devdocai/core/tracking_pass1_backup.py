"""
M005 Tracking Matrix - Document Relationship and Dependency Tracking
DevDocAI v3.0.0 - Pass 1: Core Implementation

This module provides relationship mapping, dependency tracking, and impact analysis
for documentation suites. It enables visualization of document relationships,
detection of circular references, and estimation of change propagation.

Key Features:
- Document relationship mapping with graph-based modeling
- Impact analysis with 90% accuracy for direct dependencies
- Circular reference detection using Tarjan's algorithm
- Change propagation estimation with effort calculation
- Performance optimization for 1000+ documents
- Integration with M002 Storage and M004 Generator

Pass 1 Implementation (Core Functionality):
- Basic relationship tracking and storage
- Simple impact analysis algorithm
- Circular reference detection
- JSON export/import for visualization
- 80% test coverage target
"""

import json
import time
import logging
import hashlib
from enum import Enum
from typing import Dict, List, Set, Optional, Tuple, Any, Union
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


# ============================================================================
# Exceptions
# ============================================================================


class TrackingError(Exception):
    """Base exception for tracking matrix errors."""

    def __init__(self, message: str, error_code: str = "TRACKING_ERROR", **kwargs):
        super().__init__(message)
        self.error_code = error_code
        self.details = kwargs


class CircularReferenceError(TrackingError):
    """Exception raised when a circular reference is detected."""

    def __init__(self, cycle: List[str], **kwargs):
        message = f"Circular reference detected: {' -> '.join(cycle)}"
        super().__init__(message, "CIRCULAR_REFERENCE", cycle=cycle, **kwargs)
        self.cycle = cycle


class RelationshipError(TrackingError):
    """Exception for relationship-related errors."""

    def __init__(self, message: str, source: str = None, target: str = None, **kwargs):
        super().__init__(message, "RELATIONSHIP_ERROR", source=source, target=target, **kwargs)
        self.source = source
        self.target = target


# ============================================================================
# Enums and Constants
# ============================================================================


class RelationshipType(Enum):
    """Types of relationships between documents."""

    DEPENDS_ON = "DEPENDS_ON"  # Source depends on target
    REFERENCES = "REFERENCES"  # Source references target
    IMPLEMENTS = "IMPLEMENTS"  # Source implements target (e.g., code implements spec)
    TESTS = "TESTS"  # Source tests target
    EXTENDS = "EXTENDS"  # Source extends target
    REPLACES = "REPLACES"  # Source replaces target (versioning)
    RELATED_TO = "RELATED_TO"  # General relationship
    VALIDATES = "VALIDATES"  # Source validates target
    DOCUMENTS = "DOCUMENTS"  # Source documents target


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class DocumentRelationship:
    """Represents a relationship between two documents."""

    source_id: str
    target_id: str
    relationship_type: RelationshipType
    strength: float = 1.0  # 0.0 to 1.0, indicates relationship strength
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def __post_init__(self):
        """Validate relationship after initialization."""
        if self.source_id == self.target_id:
            raise ValueError(f"Document {self.source_id} cannot reference itself")

        if not 0.0 <= self.strength <= 1.0:
            raise ValueError(
                f"Relationship strength must be between 0.0 and 1.0, got {self.strength}"
            )

    def __eq__(self, other):
        """Check equality based on source, target, and type."""
        if not isinstance(other, DocumentRelationship):
            return False
        return (
            self.source_id == other.source_id
            and self.target_id == other.target_id
            and self.relationship_type == other.relationship_type
        )

    def __hash__(self):
        """Hash for use in sets."""
        return hash((self.source_id, self.target_id, self.relationship_type.value))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship_type": self.relationship_type.value,
            "strength": self.strength,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


@dataclass
class ImpactResult:
    """Result of impact analysis."""

    source_document: str
    affected_documents: Set[str]
    impact_scores: Dict[str, float]  # Document ID -> impact score
    direct_impact_count: int
    indirect_impact_count: int
    total_impact_score: float
    estimated_effort: float = 0.0  # Hours
    risk_level: str = "low"  # low, medium, high
    analysis_time: float = 0.0  # Seconds
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_affected(self) -> int:
        """Total number of affected documents."""
        return len(self.affected_documents)

    @property
    def direct_impact(self) -> List[str]:
        """List of directly impacted documents."""
        return list(self.affected_documents)[: self.direct_impact_count]

    @property
    def indirect_impact(self) -> List[str]:
        """List of indirectly impacted documents."""
        return list(self.affected_documents)[self.direct_impact_count :]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source_document": self.source_document,
            "affected_documents": list(self.affected_documents),
            "impact_scores": self.impact_scores,
            "direct_impact_count": self.direct_impact_count,
            "indirect_impact_count": self.indirect_impact_count,
            "total_impact_score": self.total_impact_score,
            "estimated_effort": self.estimated_effort,
            "risk_level": self.risk_level,
            "analysis_time": self.analysis_time,
            "metadata": self.metadata,
        }


@dataclass
class ConsistencyReport:
    """Report of suite consistency analysis."""

    total_documents: int
    total_relationships: int
    consistency_score: float  # 0.0 to 1.0
    orphaned_documents: Set[str]
    strongly_connected_components: List[Set[str]]
    issues: List[str]
    suggestions: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_documents": self.total_documents,
            "total_relationships": self.total_relationships,
            "consistency_score": self.consistency_score,
            "orphaned_documents": list(self.orphaned_documents),
            "strongly_connected_components": [
                list(comp) for comp in self.strongly_connected_components
            ],
            "issues": self.issues,
            "suggestions": self.suggestions,
            "metadata": self.metadata,
        }


# ============================================================================
# Dependency Graph Implementation
# ============================================================================


class DependencyGraph:
    """Graph structure for managing document dependencies."""

    def __init__(self):
        """Initialize empty graph."""
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: Dict[str, Dict[str, DocumentRelationship]] = defaultdict(dict)
        self.reverse_edges: Dict[str, Dict[str, DocumentRelationship]] = defaultdict(dict)
        self._topological_cache: Optional[List[str]] = None
        self._scc_cache: Optional[List[Set[str]]] = None

    def add_node(self, node_id: str, metadata: Dict[str, Any] = None):
        """Add a node to the graph."""
        if node_id not in self.nodes:
            self.nodes[node_id] = metadata or {}
            self._invalidate_cache()

    def add_edge(
        self,
        source: str,
        target: str,
        relationship_type: RelationshipType,
        strength: float = 1.0,
        metadata: Dict[str, Any] = None,
    ):
        """Add an edge between nodes."""
        # Ensure nodes exist
        if source not in self.nodes:
            self.add_node(source)
        if target not in self.nodes:
            self.add_node(target)

        # Create relationship
        relationship = DocumentRelationship(
            source_id=source,
            target_id=target,
            relationship_type=relationship_type,
            strength=strength,
            metadata=metadata or {},
        )

        # Check for circular reference before adding
        if self._would_create_cycle(source, target):
            cycle = self._find_cycle_path(target, source)
            cycle.append(target)
            raise CircularReferenceError(cycle)

        # Add to both edge dictionaries
        self.edges[source][target] = relationship
        self.reverse_edges[target][source] = relationship
        self._invalidate_cache()

    def has_edge(self, source: str, target: str) -> bool:
        """Check if an edge exists between two nodes."""
        return source in self.edges and target in self.edges[source]

    def get_edge(self, source: str, target: str) -> Optional[DocumentRelationship]:
        """Get the edge between two nodes."""
        if self.has_edge(source, target):
            return self.edges[source][target]
        return None

    def get_neighbors(self, node: str, direction: str = "outgoing") -> Set[str]:
        """Get neighboring nodes."""
        neighbors = set()

        if direction in ["outgoing", "both"]:
            if node in self.edges:
                neighbors.update(self.edges[node].keys())

        if direction in ["incoming", "both"]:
            if node in self.reverse_edges:
                neighbors.update(self.reverse_edges[node].keys())

        return neighbors

    def _would_create_cycle(self, source: str, target: str) -> bool:
        """Check if adding an edge would create a cycle."""
        # Use DFS to check if target can reach source
        visited = set()
        stack = [target]

        while stack:
            current = stack.pop()
            if current == source:
                return True

            if current in visited:
                continue

            visited.add(current)
            if current in self.edges:
                stack.extend(self.edges[current].keys())

        return False

    def _find_cycle_path(self, start: str, end: str) -> List[str]:
        """Find the path from start to end (for cycle reporting)."""
        visited = set()
        parent = {}
        queue = deque([start])

        while queue:
            current = queue.popleft()
            if current == end:
                # Reconstruct path
                path = []
                while current != start:
                    path.append(current)
                    current = parent[current]
                path.append(start)
                path.reverse()
                return path

            if current in visited:
                continue

            visited.add(current)
            if current in self.edges:
                for neighbor in self.edges[current]:
                    if neighbor not in visited:
                        parent[neighbor] = current
                        queue.append(neighbor)

        return []

    def topological_sort(self) -> List[str]:
        """Perform topological sort on the DAG."""
        if self._topological_cache is not None:
            return self._topological_cache

        # Kahn's algorithm
        in_degree = defaultdict(int)
        for node in self.nodes:
            for target in self.edges.get(node, {}):
                in_degree[target] += 1

        queue = deque([node for node in self.nodes if in_degree[node] == 0])
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)

            for neighbor in self.edges.get(node, {}):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(self.nodes):
            raise CircularReferenceError(["Cycle detected in graph"])

        self._topological_cache = result
        return result

    def find_strongly_connected_components(self) -> List[Set[str]]:
        """Find strongly connected components using Tarjan's algorithm."""
        if self._scc_cache is not None:
            return self._scc_cache

        index_counter = [0]
        stack = []
        lowlinks = {}
        index = {}
        on_stack = defaultdict(bool)
        components = []

        def strongconnect(node):
            index[node] = index_counter[0]
            lowlinks[node] = index_counter[0]
            index_counter[0] += 1
            stack.append(node)
            on_stack[node] = True

            for neighbor in self.edges.get(node, {}):
                if neighbor not in index:
                    strongconnect(neighbor)
                    lowlinks[node] = min(lowlinks[node], lowlinks[neighbor])
                elif on_stack[neighbor]:
                    lowlinks[node] = min(lowlinks[node], index[neighbor])

            if lowlinks[node] == index[node]:
                component = set()
                while True:
                    w = stack.pop()
                    on_stack[w] = False
                    component.add(w)
                    if w == node:
                        break
                components.append(component)

        for node in self.nodes:
            if node not in index:
                strongconnect(node)

        self._scc_cache = components
        return components

    def _invalidate_cache(self):
        """Invalidate cached computations."""
        self._topological_cache = None
        self._scc_cache = None


# ============================================================================
# Impact Analysis
# ============================================================================


class ImpactAnalysis:
    """Analyzes the impact of changes to documents."""

    def __init__(self, graph: DependencyGraph):
        """Initialize with dependency graph."""
        self.graph = graph

    def analyze_impact(self, source_document: str, max_depth: int = 5) -> ImpactResult:
        """Analyze the impact of changes to a document."""
        start_time = time.time()

        if source_document not in self.graph.nodes:
            raise ValueError(f"Document {source_document} not found in tracking matrix")

        # Track affected documents and their impact scores
        affected = set()
        impact_scores = {}
        direct_count = 0
        indirect_count = 0

        # BFS to find all affected documents
        queue = deque([(source_document, 0, 1.0)])  # (doc, depth, impact_score)
        visited = set()

        while queue:
            current_doc, depth, current_impact = queue.popleft()

            if current_doc in visited:
                continue

            visited.add(current_doc)

            # Get documents that depend on current document
            dependents = self.graph.reverse_edges.get(current_doc, {})

            for dependent_doc, relationship in dependents.items():
                # Check depth limit for adding new documents
                if depth < max_depth and dependent_doc not in affected:
                    affected.add(dependent_doc)

                    # Calculate impact score based on relationship strength and depth
                    impact_score = current_impact * relationship.strength * (1.0 / (depth + 1))
                    impact_scores[dependent_doc] = max(
                        impact_scores.get(dependent_doc, 0), impact_score
                    )

                    if depth == 0:
                        direct_count += 1
                    else:
                        indirect_count += 1

                    # Only add to queue if we haven't exceeded depth
                    if depth + 1 <= max_depth:
                        queue.append((dependent_doc, depth + 1, impact_score))

        # Calculate total impact score
        total_impact = sum(impact_scores.values())

        # Estimate effort and risk
        effort = self._estimate_effort(affected, impact_scores)
        risk = self._calculate_risk_level(len(affected), total_impact)

        analysis_time = time.time() - start_time

        return ImpactResult(
            source_document=source_document,
            affected_documents=affected,
            impact_scores=impact_scores,
            direct_impact_count=direct_count,
            indirect_impact_count=indirect_count,
            total_impact_score=total_impact,
            estimated_effort=effort,
            risk_level=risk,
            analysis_time=analysis_time,
        )

    def _estimate_effort(self, affected_docs: Set[str], impact_scores: Dict[str, float]) -> float:
        """Estimate effort in hours based on affected documents."""
        base_effort = 0.5  # Base effort per document
        effort = 0.0

        for doc in affected_docs:
            doc_metadata = self.graph.nodes.get(doc, {})
            complexity = doc_metadata.get("complexity", 1)
            size = doc_metadata.get("size", 100)
            impact = impact_scores.get(doc, 0.5)

            # Calculate effort based on complexity, size, and impact
            doc_effort = base_effort * complexity * (size / 100) * impact
            effort += doc_effort

        return round(effort, 2)

    def _calculate_risk_level(self, affected_count: int, total_impact: float) -> str:
        """Calculate risk level based on impact analysis."""
        if affected_count > 10 or total_impact > 5.0:
            return "high"
        elif affected_count > 5 or total_impact > 2.0:
            return "medium"
        else:
            return "low"


# ============================================================================
# Main Tracking Matrix Class
# ============================================================================


class TrackingMatrix:
    """Main class for document relationship tracking and analysis."""

    def __init__(self, config_manager, storage_manager):
        """Initialize tracking matrix with configuration and storage."""
        self.config = config_manager
        self.storage = storage_manager
        self.graph = DependencyGraph()
        self.impact_analyzer = ImpactAnalysis(self.graph)

        # Caching
        self._cache_enabled = False
        self._cache = {}
        self._cache_ttl = 3600
        self._cache_timestamps = {}

        # Testing mode - allows circular references for testing
        self._allow_cycles = False

        # Load configuration
        self._load_configuration()

        # Initialize from storage if available
        self._load_from_storage()

        logger.info("TrackingMatrix initialized successfully")

    def get_all_relationships(self) -> List[DocumentRelationship]:
        """Get all relationships in the matrix."""
        all_relationships = []
        for source_id in self.graph.edges:
            for target_id, relationship in self.graph.edges[source_id].items():
                all_relationships.append(relationship)
        return all_relationships

    def get_dependencies(self, doc_id: str) -> List[Dict[str, Any]]:
        """Get documents that the given document depends on (outgoing relationships)."""
        dependencies = []
        for target_id, relationship in self.graph.edges.get(doc_id, {}).items():
            dependencies.append(
                {
                    "target_id": target_id,
                    "relationship_type": relationship.relationship_type.value,
                    "description": relationship.metadata.get("description"),
                }
            )
        return dependencies

    def get_dependents(self, doc_id: str) -> List[Dict[str, Any]]:
        """Get documents that depend on the given document (incoming relationships)."""
        dependents = []
        for source_id, relationship in self.graph.reverse_edges.get(doc_id, {}).items():
            dependents.append(
                {
                    "source_id": source_id,
                    "relationship_type": relationship.relationship_type.value,
                    "description": relationship.metadata.get("description"),
                }
            )
        return dependents

    def detect_circular_references(self) -> List[List[str]]:
        """Detect circular references in the tracking matrix."""
        sccs = self.graph.find_strongly_connected_components()
        cycles = []
        for scc in sccs:
            if len(scc) > 1:  # A cycle exists if SCC has more than one node
                # For simplicity, just return the nodes in the SCC as a cycle
                # More sophisticated cycle detection within SCCs can be added if needed
                cycles.append(list(scc))
            elif len(scc) == 1:
                # Check for self-loops
                node = list(scc)[0]
                if self.graph.has_edge(node, node):
                    cycles.append([node, node])
        return cycles

    def has_relationship(self, source_id: str, target_id: str) -> bool:
        """Check if a relationship exists between two documents."""
        return self.graph.has_edge(source_id, target_id)

    def _load_configuration(self):
        """Load configuration settings."""
        try:
            tracking_config = self.config.get("tracking_matrix", {})
            self._max_documents = tracking_config.get("max_documents", 10000)
            self._impact_config = tracking_config.get("impact_analysis", {})
            self._performance_config = tracking_config.get("performance", {})

            # Apply performance settings
            if self._performance_config.get("cache_enabled", False):
                self.enable_caching(self._performance_config.get("cache_ttl", 3600))
        except Exception as e:
            logger.warning(f"Error loading configuration: {e}. Using defaults.")

    def _load_from_storage(self):
        """Load existing tracking data from storage."""
        try:
            # This would load persisted tracking data
            # For now, we start with empty graph
            pass
        except Exception as e:
            logger.warning(f"Could not load tracking data from storage: {e}")

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: RelationshipType,
        strength: float = 1.0,
        metadata: Dict[str, Any] = None,
    ):
        """Add a relationship between documents."""
        try:
            if self._allow_cycles:
                # In testing mode, bypass cycle detection
                self.graph.add_node(source_id)
                self.graph.add_node(target_id)
                relationship = DocumentRelationship(
                    source_id=source_id,
                    target_id=target_id,
                    relationship_type=relationship_type,
                    strength=strength,
                    metadata=metadata or {},
                )
                self.graph.edges[source_id][target_id] = relationship
                self.graph.reverse_edges[target_id][source_id] = relationship
                self.graph._invalidate_cache()
            else:
                self.graph.add_edge(source_id, target_id, relationship_type, strength, metadata)

            self._invalidate_cache()
            logger.debug(
                f"Added relationship {source_id} -> {target_id} ({relationship_type.value})"
            )
        except CircularReferenceError:
            logger.error(f"Circular reference detected: {source_id} -> {target_id}")
            raise

    def remove_relationship(self, source_id: str, target_id: str) -> bool:
        """Remove a relationship between documents."""
        if not self.has_relationship(source_id, target_id):
            return False

        # Remove from both edge dictionaries
        if source_id in self.graph.edges and target_id in self.graph.edges[source_id]:
            del self.graph.edges[source_id][target_id]

        if (
            target_id in self.graph.reverse_edges
            and source_id in self.graph.reverse_edges[target_id]
        ):
            del self.graph.reverse_edges[target_id][source_id]

        self.graph._invalidate_cache()
        self._invalidate_cache()
        logger.debug(f"Removed relationship {source_id} -> {target_id}")
        return True

    def add_document(self, doc_id: str, metadata: Dict[str, Any] = None):
        """Add a document to the tracking matrix."""
        self.graph.add_node(doc_id, metadata or {})
        logger.debug(f"Added document {doc_id} to tracking matrix")

    def has_document(self, doc_id: str) -> bool:
        """Check if a document exists in the matrix."""
        return doc_id in self.graph.nodes

    def get_document_info(self, doc_id: str) -> Dict[str, Any]:
        """Get document metadata."""
        if doc_id not in self.graph.nodes:
            raise ValueError(f"Document {doc_id} not found")
        return self.graph.nodes[doc_id]

    def get_relationships(
        self, doc_id: str, direction: str = "outgoing"
    ) -> List[DocumentRelationship]:
        """Get relationships for a document."""
        relationships = []

        if direction in ["outgoing", "both"]:
            for target, rel in self.graph.edges.get(doc_id, {}).items():
                relationships.append(rel)

        if direction in ["incoming", "both"]:
            for source, rel in self.graph.reverse_edges.get(doc_id, {}).items():
                relationships.append(rel)

        return relationships

    def analyze_impact(self, doc_id: str, max_depth: int = None) -> ImpactResult:
        """Analyze the impact of changes to a document."""
        # Check cache
        cache_key = f"impact_{doc_id}_{max_depth}"
        if self._cache_enabled and self._is_cache_valid(cache_key):
            logger.debug(f"Using cached impact analysis for {doc_id}")
            return self._cache[cache_key]

        # Perform analysis
        if max_depth is None:
            max_depth = self._impact_config.get("max_depth", 5)

        result = self.impact_analyzer.analyze_impact(doc_id, max_depth)

        # Cache result
        if self._cache_enabled:
            self._cache[cache_key] = result
            self._cache_timestamps[cache_key] = time.time()

        return result

    def analyze_suite_consistency(self) -> ConsistencyReport:
        """Analyze consistency of the entire documentation suite."""
        issues = []
        suggestions = []

        # Find orphaned documents
        orphaned = self.find_orphaned_documents()
        if orphaned:
            issues.append(f"Found {len(orphaned)} orphaned documents")
            suggestions.append("Consider adding relationships for orphaned documents")

        # Find strongly connected components
        sccs = self.graph.find_strongly_connected_components()
        large_sccs = [scc for scc in sccs if len(scc) > 1]
        if large_sccs:
            issues.append(f"Found {len(large_sccs)} groups of tightly coupled documents")
            suggestions.append("Review tightly coupled document groups for potential refactoring")

        # Calculate consistency score
        total_docs = len(self.graph.nodes)
        total_rels = sum(len(edges) for edges in self.graph.edges.values())

        if total_docs == 0:
            consistency_score = 1.0
        else:
            # Score based on connectivity and balance
            connectivity = 1.0 - (len(orphaned) / total_docs)
            balance = min(1.0, total_rels / (total_docs * 2))  # Ideal: 2 relationships per doc
            consistency_score = (connectivity + balance) / 2

        return ConsistencyReport(
            total_documents=total_docs,
            total_relationships=total_rels,
            consistency_score=consistency_score,
            orphaned_documents=orphaned,
            strongly_connected_components=large_sccs,
            issues=issues,
            suggestions=suggestions,
        )

    def find_orphaned_documents(self) -> Set[str]:
        """Find documents with no relationships."""
        orphaned = set()

        for doc_id in self.graph.nodes:
            has_outgoing = doc_id in self.graph.edges and len(self.graph.edges[doc_id]) > 0
            has_incoming = (
                doc_id in self.graph.reverse_edges and len(self.graph.reverse_edges[doc_id]) > 0
            )

            if not has_outgoing and not has_incoming:
                orphaned.add(doc_id)

        return orphaned

    def get_dependency_chain(self, doc_id: str) -> List[str]:
        """Get the full dependency chain for a document."""
        if doc_id not in self.graph.nodes:
            raise ValueError(f"Document {doc_id} not found")

        chain = []
        visited = set()
        queue = deque([doc_id])

        while queue:
            current = queue.popleft()
            if current in visited:
                continue

            visited.add(current)
            chain.append(current)

            # Add dependencies to queue
            for target in self.graph.edges.get(current, {}):
                if target not in visited:
                    queue.append(target)

        return chain

    def export_to_json(self) -> str:
        """Export tracking matrix to JSON format."""
        nodes = []
        edges = []

        # Export nodes
        for node_id, metadata in self.graph.nodes.items():
            nodes.append({"id": node_id, "metadata": metadata})

        # Export edges
        for source, targets in self.graph.edges.items():
            for target, relationship in targets.items():
                edges.append(
                    {
                        "source": source,
                        "target": target,
                        "type": relationship.relationship_type.value,
                        "strength": relationship.strength,
                        "metadata": relationship.metadata,
                    }
                )

        data = {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "total_documents": len(self.graph.nodes),
                "total_relationships": len(edges),
                "export_time": datetime.now().isoformat(),
            },
        }

        return json.dumps(data, indent=2)

    def import_from_json(self, json_data: str):
        """Import tracking matrix from JSON format."""
        data = json.loads(json_data)

        # Clear existing graph
        self.graph = DependencyGraph()
        self.impact_analyzer = ImpactAnalysis(self.graph)

        # Import nodes
        for node_data in data.get("nodes", []):
            self.add_document(node_data["id"], node_data.get("metadata", {}))

        # Import edges
        for edge_data in data.get("edges", []):
            self.add_relationship(
                edge_data["source"],
                edge_data["target"],
                RelationshipType[edge_data["type"]],
                edge_data.get("strength", 1.0),
                edge_data.get("metadata", {}),
            )

        logger.info(
            f"Imported {len(data['nodes'])} documents and {len(data['edges'])} relationships"
        )

    def enable_caching(self, ttl: int = 3600):
        """Enable caching for performance optimization."""
        self._cache_enabled = True
        self._cache_ttl = ttl
        logger.info(f"Caching enabled with TTL of {ttl} seconds")

    def disable_caching(self):
        """Disable caching."""
        self._cache_enabled = False
        self._cache.clear()
        self._cache_timestamps.clear()
        logger.info("Caching disabled")

    def _is_cache_valid(self, key: str) -> bool:
        """Check if a cache entry is still valid."""
        if key not in self._cache:
            return False

        timestamp = self._cache_timestamps.get(key, 0)
        return (time.time() - timestamp) < self._cache_ttl

    def _invalidate_cache(self):
        """Invalidate all cache entries."""
        self._cache.clear()
        self._cache_timestamps.clear()

    def get_visualization_data(self) -> Dict[str, Any]:
        """Get data formatted for visualization (e.g., D3.js)."""
        nodes = []
        links = []

        # Format nodes for D3.js
        for node_id, metadata in self.graph.nodes.items():
            nodes.append(
                {
                    "id": node_id,
                    "group": metadata.get("type", "default"),
                    "title": metadata.get("title", node_id),
                    **metadata,
                }
            )

        # Format links for D3.js
        for source, targets in self.graph.edges.items():
            for target, relationship in targets.items():
                links.append(
                    {
                        "source": source,
                        "target": target,
                        "value": relationship.strength,
                        "type": relationship.relationship_type.value,
                        "metadata": relationship.metadata,
                    }
                )

        return {
            "nodes": nodes,
            "links": links,
            "metadata": {
                "total_nodes": len(nodes),
                "total_links": len(links),
                "generated_at": datetime.now().isoformat(),
            },
        }

    def save_to_storage(self):
        """Persist tracking matrix to storage."""
        try:
            # Convert to JSON and store
            json_data = self.export_to_json()

            # Import Document class from storage module
            from ..core.storage import Document, DocumentMetadata

            # Create Document object for storage
            doc = Document(
                id="tracking_matrix",
                content=json_data,
                type="system",
                metadata=DocumentMetadata(
                    custom={
                        "title": "Tracking Matrix Data",
                        "module": "M005",
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
            )

            # Store in M002 storage
            self.storage.save_document(doc)

            logger.info("Tracking matrix saved to storage")
        except Exception as e:
            logger.error(f"Failed to save tracking matrix: {e}")
            raise TrackingError(f"Storage save failed: {e}")

    def load_from_storage(self):
        """Load tracking matrix from storage."""
        try:
            # Load from M002 storage
            doc = self.storage.get_document("tracking_matrix")
            if doc:
                self.import_from_json(doc.get("content", "{}"))
                logger.info("Tracking matrix loaded from storage")
        except Exception as e:
            logger.warning(f"Could not load tracking matrix from storage: {e}")
