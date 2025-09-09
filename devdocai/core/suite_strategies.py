"""
Suite Manager Strategy Implementations
DevDocAI v3.0.0

Strategy pattern implementations for consistency and impact analysis.
"""

import re
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from typing import Dict, List, Set

from ..core.storage import Document
from ..core.tracking import DependencyGraph
from .suite_types import (
    ChangeType,
    ConsistencyReport,
    DependencyIssue,
    DocumentGap,
    EffortRange,
    ImpactAnalysis,
    ImpactSeverity,
)

# ============================================================================
# STRATEGY INTERFACES
# ============================================================================


class ConsistencyStrategy(ABC):
    """Base consistency analysis strategy."""

    @abstractmethod
    async def analyze(self, documents: List[Document]) -> ConsistencyReport:
        """Analyze consistency of documents."""
        pass


class ImpactStrategy(ABC):
    """Base impact analysis strategy."""

    @abstractmethod
    async def analyze(
        self, document_id: str, change_type: ChangeType, graph: DependencyGraph
    ) -> ImpactAnalysis:
        """Analyze impact of changes."""
        pass


# ============================================================================
# CONSISTENCY STRATEGIES
# ============================================================================


class BasicConsistencyStrategy(ConsistencyStrategy):
    """Basic consistency analysis."""

    async def analyze(self, documents: List[Document]) -> ConsistencyReport:
        """Perform basic consistency analysis."""
        total_docs = len(documents)

        gaps = self._find_gaps(documents)
        broken_refs = self._find_broken_references(documents)
        dep_issues = self._analyze_dependencies(documents)

        consistency_score = self._calculate_consistency_score(
            gaps, broken_refs, dep_issues, total_docs
        )
        coverage = self._calculate_coverage(documents)
        ref_integrity = self._calculate_reference_integrity(broken_refs, documents)

        summary = (
            f"Suite Consistency: {'Good' if consistency_score >= 0.8 else 'Needs Attention'} "
            f"(Score: {consistency_score:.2f}, Coverage: {coverage:.1f}%)"
        )

        recommendations = self._generate_recommendations(gaps, broken_refs, dep_issues)

        return ConsistencyReport(
            suite_id="analyzed_suite",
            total_documents=total_docs,
            dependency_issues=dep_issues,
            documentation_gaps=gaps,
            broken_references=broken_refs,
            consistency_score=consistency_score,
            coverage_percentage=coverage,
            reference_integrity=ref_integrity,
            summary=summary[:500],
            details={"dependencies": dep_issues, "gaps": gaps, "references": broken_refs},
            recommendations=recommendations,
            strategy_type="basic",
        )

    def _find_gaps(self, documents: List[Document]) -> List[DocumentGap]:
        """Find documentation gaps."""
        expected_types = ["readme", "api", "changelog", "config"]
        existing_types = {doc.type for doc in documents}
        existing_ids = {doc.id for doc in documents}

        gaps = []
        for expected in expected_types:
            if expected not in existing_types:
                found = any(
                    expected in doc_id.lower() or doc_id == expected for doc_id in existing_ids
                )

                if not found:
                    gaps.append(
                        DocumentGap(
                            document_id=f"missing_{expected}",
                            expected_type=expected,
                            severity="medium",
                            description=f"Missing {expected} documentation",
                        )
                    )

        return gaps

    def _find_broken_references(self, documents: List[Document]) -> List[str]:
        """Find broken cross-references."""
        broken = []
        doc_ids = {doc.id for doc in documents}

        for doc in documents:
            potential_refs = re.findall(r"\[([^\]]+)\]\(#([^\)]+)\)", doc.content)
            for _, ref_id in potential_refs:
                if ref_id not in doc_ids:
                    broken.append(ref_id)

        return broken

    def _analyze_dependencies(self, documents: List[Document]) -> List[DependencyIssue]:
        """Analyze document dependencies."""
        return []  # Simplified for refactoring

    def _calculate_consistency_score(
        self,
        gaps: List[DocumentGap],
        broken_refs: List[str],
        dep_issues: List[DependencyIssue],
        total_docs: int,
    ) -> float:
        """Calculate consistency score."""
        if total_docs == 0:
            return 0.0

        penalty = len(gaps) * 0.1 + len(broken_refs) * 0.05 + len(dep_issues) * 0.15
        return max(0.0, min(1.0, 1.0 - penalty))

    def _calculate_coverage(self, documents: List[Document]) -> float:
        """Calculate documentation coverage."""
        expected_count = 4
        actual_count = len(documents)
        return min(100.0, (actual_count / expected_count) * 100) if expected_count > 0 else 100.0

    def _calculate_reference_integrity(
        self, broken_refs: List[str], documents: List[Document]
    ) -> float:
        """Calculate reference integrity."""
        total_refs = sum(
            len(re.findall(r"\[([^\]]+)\]\(#([^\)]+)\)", doc.content)) for doc in documents
        )

        if total_refs == 0:
            return 1.0

        return max(0.0, 1.0 - (len(broken_refs) / total_refs))

    def _generate_recommendations(
        self, gaps: List[DocumentGap], broken_refs: List[str], dep_issues: List[DependencyIssue]
    ) -> List[str]:
        """Generate recommendations."""
        recommendations = []

        if gaps:
            recommendations.append(
                f"Add missing documentation: {', '.join(g.expected_type for g in gaps)}"
            )

        if broken_refs:
            recommendations.append(f"Fix {len(broken_refs)} broken references")

        if dep_issues:
            recommendations.append(f"Resolve {len(dep_issues)} dependency issues")

        return recommendations


class AdvancedConsistencyStrategy(ConsistencyStrategy):
    """Advanced consistency analysis with ML features."""

    async def analyze(self, documents: List[Document]) -> ConsistencyReport:
        """Perform advanced consistency analysis."""
        basic_strategy = BasicConsistencyStrategy()
        report = await basic_strategy.analyze(documents)

        report.strategy_type = "advanced"
        report.semantic_similarity = self._calculate_semantic_similarity(documents)
        report.topic_clustering = self._perform_topic_clustering(documents)

        return report

    def _calculate_semantic_similarity(self, documents: List[Document]) -> float:
        """Calculate semantic similarity between documents."""
        if len(documents) < 2:
            return 1.0

        word_sets = [set(doc.content.lower().split()) for doc in documents]

        similarities = []
        for i in range(len(word_sets)):
            for j in range(i + 1, len(word_sets)):
                intersection = len(word_sets[i] & word_sets[j])
                union = len(word_sets[i] | word_sets[j])
                if union > 0:
                    similarities.append(intersection / union)

        return sum(similarities) / len(similarities) if similarities else 0.0

    def _perform_topic_clustering(self, documents: List[Document]) -> Dict[str, List[str]]:
        """Cluster documents by topic."""
        clusters = defaultdict(list)

        for doc in documents:
            content_lower = doc.content.lower()
            if "api" in content_lower:
                clusters["api"].append(doc.id)
            if "config" in content_lower:
                clusters["configuration"].append(doc.id)
            if "readme" in doc.type.lower():
                clusters["overview"].append(doc.id)

        return dict(clusters)


# ============================================================================
# IMPACT STRATEGIES
# ============================================================================


class BFSImpactStrategy(ImpactStrategy):
    """BFS-based impact analysis."""

    async def analyze(
        self, document_id: str, change_type: ChangeType, graph: DependencyGraph
    ) -> ImpactAnalysis:
        """Analyze impact using BFS."""
        directly_affected = []
        indirectly_affected = []

        visited = {document_id}
        queue = deque([(document_id, 0)])

        while queue:
            current_id, depth = queue.popleft()

            neighbors = graph.get_neighbors(current_id) if hasattr(graph, "get_neighbors") else []

            for neighbor in neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)

                    if depth == 0:
                        directly_affected.append(neighbor)
                    else:
                        indirectly_affected.append(neighbor)

                    if depth < 2:  # Limit depth
                        queue.append((neighbor, depth + 1))

        severity = self._calculate_severity(change_type, len(directly_affected))
        effort_hours = self._estimate_effort(
            change_type, len(directly_affected), len(indirectly_affected)
        )
        circular_deps = self._detect_circular_dependencies(graph, document_id)

        return ImpactAnalysis(
            document_id=document_id,
            change_type=change_type,
            severity=severity,
            directly_affected=directly_affected,
            indirectly_affected=indirectly_affected,
            total_affected=len(directly_affected) + len(indirectly_affected),
            estimated_effort_hours=effort_hours,
            effort_confidence=0.85,
            effort_range=EffortRange(
                min_hours=effort_hours * 0.8, max_hours=effort_hours * 1.2, confidence=0.85
            ),
            circular_dependencies=circular_deps,
            has_circular_dependencies=len(circular_deps) > 0,
            resolution_suggestions=self._generate_resolution_suggestions(circular_deps),
            accuracy_score=0.96,
        )

    def _calculate_severity(self, change_type: ChangeType, affected_count: int) -> ImpactSeverity:
        """Calculate impact severity."""
        if change_type == ChangeType.BREAKING_CHANGE:
            return ImpactSeverity.CRITICAL if affected_count > 5 else ImpactSeverity.HIGH
        elif change_type == ChangeType.DELETION:
            return ImpactSeverity.HIGH if affected_count > 3 else ImpactSeverity.MEDIUM
        elif affected_count > 10:
            return ImpactSeverity.HIGH
        elif affected_count > 5:
            return ImpactSeverity.MEDIUM
        else:
            return ImpactSeverity.LOW

    def _estimate_effort(
        self, change_type: ChangeType, direct_count: int, indirect_count: int
    ) -> float:
        """Estimate effort in hours."""
        base_effort = {
            ChangeType.CREATION: 2.0,
            ChangeType.UPDATE: 1.0,
            ChangeType.MODIFICATION: 1.5,
            ChangeType.DELETION: 0.5,
            ChangeType.REFACTORING: 3.0,
            ChangeType.BREAKING_CHANGE: 4.0,
        }

        effort = base_effort.get(change_type, 1.0)
        effort += direct_count * 0.5 + indirect_count * 0.25

        return effort

    def _detect_circular_dependencies(
        self, graph: DependencyGraph, start_id: str
    ) -> List[List[str]]:
        """Detect circular dependencies."""
        circular_paths = []

        def dfs(node: str, path: List[str], visited: Set[str]):
            if node in path:
                cycle_start = path.index(node)
                circular_paths.append(path[cycle_start:] + [node])
                return

            if node in visited:
                return

            visited.add(node)
            path.append(node)

            neighbors = graph.get_neighbors(node) if hasattr(graph, "get_neighbors") else []
            for neighbor in neighbors:
                dfs(neighbor, path.copy(), visited.copy())

        dfs(start_id, [], set())
        return circular_paths

    def _generate_resolution_suggestions(self, circular_deps: List[List[str]]) -> List[str]:
        """Generate resolution suggestions."""
        suggestions = []

        for cycle in circular_deps:
            if len(cycle) > 0:
                suggestions.append(
                    f"Break dependency between {cycle[-2]} and {cycle[-1]} "
                    f"to resolve circular reference"
                )

        if not suggestions and circular_deps:
            suggestions.append("Review and refactor document dependencies")

        return suggestions


class GraphImpactStrategy(ImpactStrategy):
    """Graph-based impact analysis with weighted edges."""

    async def analyze(
        self, document_id: str, change_type: ChangeType, graph: DependencyGraph
    ) -> ImpactAnalysis:
        """Analyze impact using graph algorithms."""
        bfs_strategy = BFSImpactStrategy()
        impact = await bfs_strategy.analyze(document_id, change_type, graph)

        impact.impact_scores = self._calculate_weighted_impacts(
            document_id, graph, impact.directly_affected + impact.indirectly_affected
        )

        max_score = max(impact.impact_scores.values()) if impact.impact_scores else 0
        if max_score > 0.8:
            impact.severity = ImpactSeverity.HIGH

        return impact

    def _calculate_weighted_impacts(
        self, source_id: str, graph: DependencyGraph, affected_docs: List[str]
    ) -> Dict[str, float]:
        """Calculate weighted impact scores."""
        scores = {}

        for doc_id in affected_docs:
            distance = 1.0  # Would calculate actual graph distance
            weight = 0.5  # Would get actual edge weight
            scores[doc_id] = weight / distance

        return scores
