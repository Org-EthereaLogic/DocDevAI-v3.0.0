"""M012 Version Control Integration - Operation Strategies
DevDocAI v3.0.0

This module implements Factory and Strategy patterns for version control operations.
Provides modular strategies for different operation types.
"""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from devdocai.core.storage import Document
from devdocai.core.tracking import TrackingMatrix
from devdocai.operations.version_core import GitRepository
from devdocai.operations.version_types import (
    BranchComparison,
    ConflictResolution,
    ConflictResolutionResult,
    ImpactAnalysisResult,
    MergeConflict,
    MergeResult,
    VersionControlConfig,
)

logger = logging.getLogger(__name__)


# Strategy Interfaces
class CommitStrategy(ABC):
    """Abstract base class for commit strategies."""

    @abstractmethod
    def prepare_commit(
        self,
        document: Document,
        config: VersionControlConfig,
    ) -> Dict[str, Any]:
        """Prepare commit data based on strategy."""
        pass

    @abstractmethod
    def format_message(
        self,
        message: str,
        config: VersionControlConfig,
    ) -> str:
        """Format commit message based on strategy."""
        pass


class MergeStrategy(ABC):
    """Abstract base class for merge strategies."""

    @abstractmethod
    def execute_merge(
        self,
        repo: GitRepository,
        branch_name: str,
        config: VersionControlConfig,
    ) -> MergeResult:
        """Execute merge based on strategy."""
        pass

    @abstractmethod
    def resolve_conflicts(
        self,
        conflicts: List[MergeConflict],
        config: VersionControlConfig,
    ) -> List[ConflictResolutionResult]:
        """Resolve conflicts based on strategy."""
        pass


class ImpactAnalysisStrategy(ABC):
    """Abstract base class for impact analysis strategies."""

    @abstractmethod
    def analyze(
        self,
        document_id: str,
        tracking: TrackingMatrix,
    ) -> ImpactAnalysisResult:
        """Analyze impact based on strategy."""
        pass

    @abstractmethod
    def generate_recommendations(
        self,
        impact_result: ImpactAnalysisResult,
    ) -> List[str]:
        """Generate recommendations based on impact."""
        pass


# Concrete Strategy Implementations
class StandardCommitStrategy(CommitStrategy):
    """Standard commit strategy with metadata tracking."""

    def prepare_commit(
        self,
        document: Document,
        config: VersionControlConfig,
    ) -> Dict[str, Any]:
        """Prepare standard commit with document and metadata."""
        commit_data = {
            "files": [f"{document.id}.md"],
            "content": {f"{document.id}.md": document.content},
        }

        if config.track_metadata and document.metadata:
            meta_filename = f"{document.id}.meta.json"
            commit_data["files"].append(meta_filename)
            commit_data["content"][meta_filename] = json.dumps(
                document.metadata.to_dict(), indent=2
            )

        return commit_data

    def format_message(
        self,
        message: str,
        config: VersionControlConfig,
    ) -> str:
        """Format message using template."""
        return config.commit_template.format(message=message)


class AutoCommitStrategy(CommitStrategy):
    """Auto-commit strategy for automatic versioning."""

    def prepare_commit(
        self,
        document: Document,
        config: VersionControlConfig,
    ) -> Dict[str, Any]:
        """Prepare minimal auto-commit."""
        return {
            "files": [f"{document.id}.md"],
            "content": {f"{document.id}.md": document.content},
        }

    def format_message(
        self,
        message: str,
        config: VersionControlConfig,
    ) -> str:
        """Format auto-commit message."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"Auto-commit [{timestamp}]: {message}"


class OursMergeStrategy(MergeStrategy):
    """Merge strategy that favors our changes."""

    def execute_merge(
        self,
        repo: GitRepository,
        branch_name: str,
        config: VersionControlConfig,
    ) -> MergeResult:
        """Execute merge favoring our changes."""
        return repo.merge_branch(branch_name)

    def resolve_conflicts(
        self,
        conflicts: List[MergeConflict],
        config: VersionControlConfig,
    ) -> List[ConflictResolutionResult]:
        """Resolve conflicts by keeping our version."""
        resolutions = []
        for conflict in conflicts:
            resolution = ConflictResolutionResult(
                file_path=conflict.file_path,
                resolved_content=conflict.our_content,
                strategy=ConflictResolution.OURS,
            )
            resolutions.append(resolution)
        return resolutions


class TheirsMergeStrategy(MergeStrategy):
    """Merge strategy that favors their changes."""

    def execute_merge(
        self,
        repo: GitRepository,
        branch_name: str,
        config: VersionControlConfig,
    ) -> MergeResult:
        """Execute merge favoring their changes."""
        return repo.merge_branch(branch_name)

    def resolve_conflicts(
        self,
        conflicts: List[MergeConflict],
        config: VersionControlConfig,
    ) -> List[ConflictResolutionResult]:
        """Resolve conflicts by keeping their version."""
        resolutions = []
        for conflict in conflicts:
            resolution = ConflictResolutionResult(
                file_path=conflict.file_path,
                resolved_content=conflict.their_content,
                strategy=ConflictResolution.THEIRS,
            )
            resolutions.append(resolution)
        return resolutions


class ManualMergeStrategy(MergeStrategy):
    """Merge strategy requiring manual conflict resolution."""

    def execute_merge(
        self,
        repo: GitRepository,
        branch_name: str,
        config: VersionControlConfig,
    ) -> MergeResult:
        """Execute merge and report conflicts."""
        result = repo.merge_branch(branch_name)
        if not result.success and result.conflicts:
            # Don't auto-resolve, return conflicts for manual resolution
            logger.info(
                f"Manual merge strategy: {len(result.conflicts)} conflicts require resolution"
            )
        return result

    def resolve_conflicts(
        self,
        conflicts: List[MergeConflict],
        config: VersionControlConfig,
    ) -> List[ConflictResolutionResult]:
        """Mark conflicts for manual resolution."""
        # This strategy doesn't auto-resolve
        return []


class DependencyImpactStrategy(ImpactAnalysisStrategy):
    """Impact analysis based on dependency graph."""

    def analyze(
        self,
        document_id: str,
        tracking: TrackingMatrix,
    ) -> ImpactAnalysisResult:
        """Analyze impact through dependency tracking."""
        # Get dependencies and dependents
        dependencies = tracking.get_dependencies(document_id) or []
        dependents = tracking.get_dependents(document_id) or []

        # Combine for affected documents
        affected = list(set(dependencies + dependents))

        # Determine impact level
        impact_level = self._calculate_impact_level(len(affected))

        # Generate recommendations
        recommendations = self.generate_recommendations(
            ImpactAnalysisResult(
                document_id=document_id,
                affected_documents=affected,
                dependencies=dependencies,
                dependents=dependents,
                impact_level=impact_level,
            )
        )

        return ImpactAnalysisResult(
            document_id=document_id,
            affected_documents=affected,
            dependencies=dependencies,
            dependents=dependents,
            impact_level=impact_level,
            recommendations=recommendations,
        )

    def generate_recommendations(
        self,
        impact_result: ImpactAnalysisResult,
    ) -> List[str]:
        """Generate recommendations based on impact."""
        recommendations = []

        if impact_result.impact_level in ["high", "critical"]:
            recommendations.append("Review all dependent documents for consistency")
            recommendations.append("Consider creating a backup branch before changes")
            recommendations.append("Use batch operations for better performance")

        if impact_result.dependencies:
            recommendations.append(
                f"Verify {len(impact_result.dependencies)} dependencies are up-to-date"
            )

        if impact_result.dependents:
            recommendations.append(
                f"Update {len(impact_result.dependents)} dependent documents if needed"
            )

        return recommendations

    def _calculate_impact_level(self, affected_count: int) -> str:
        """Calculate impact level based on affected document count."""
        if affected_count > 50:
            return "critical"
        elif affected_count > 20:
            return "high"
        elif affected_count > 5:
            return "medium"
        else:
            return "low"


class CascadingImpactStrategy(ImpactAnalysisStrategy):
    """Impact analysis with cascading dependency analysis."""

    def __init__(self, max_depth: int = 3):
        """Initialize with maximum cascade depth."""
        self.max_depth = max_depth

    def analyze(
        self,
        document_id: str,
        tracking: TrackingMatrix,
    ) -> ImpactAnalysisResult:
        """Analyze cascading impact through dependency levels."""
        affected = set()
        dependencies = set()
        dependents = set()

        # Analyze cascading dependencies
        self._cascade_dependencies(document_id, tracking, dependencies, 0)

        # Analyze cascading dependents
        self._cascade_dependents(document_id, tracking, dependents, 0)

        affected = dependencies | dependents
        impact_level = self._calculate_impact_level(len(affected))

        return ImpactAnalysisResult(
            document_id=document_id,
            affected_documents=list(affected),
            dependencies=list(dependencies),
            dependents=list(dependents),
            impact_level=impact_level,
            recommendations=self.generate_recommendations(
                ImpactAnalysisResult(
                    document_id=document_id,
                    affected_documents=list(affected),
                    dependencies=list(dependencies),
                    dependents=list(dependents),
                    impact_level=impact_level,
                )
            ),
        )

    def _cascade_dependencies(
        self,
        doc_id: str,
        tracking: TrackingMatrix,
        visited: set,
        depth: int,
    ):
        """Recursively analyze cascading dependencies."""
        if depth >= self.max_depth or doc_id in visited:
            return

        deps = tracking.get_dependencies(doc_id) or []
        for dep in deps:
            if dep not in visited:
                visited.add(dep)
                self._cascade_dependencies(dep, tracking, visited, depth + 1)

    def _cascade_dependents(
        self,
        doc_id: str,
        tracking: TrackingMatrix,
        visited: set,
        depth: int,
    ):
        """Recursively analyze cascading dependents."""
        if depth >= self.max_depth or doc_id in visited:
            return

        deps = tracking.get_dependents(doc_id) or []
        for dep in deps:
            if dep not in visited:
                visited.add(dep)
                self._cascade_dependents(dep, tracking, visited, depth + 1)

    def generate_recommendations(
        self,
        impact_result: ImpactAnalysisResult,
    ) -> List[str]:
        """Generate recommendations for cascading impact."""
        recommendations = []

        if impact_result.impact_level == "critical":
            recommendations.append(
                "CRITICAL: Cascading impact affects large portion of documentation"
            )
            recommendations.append("Perform comprehensive review before proceeding")
            recommendations.append("Consider phased rollout of changes")
        elif impact_result.impact_level == "high":
            recommendations.append("HIGH: Significant cascading impact detected")
            recommendations.append("Review and test all affected documents")

        recommendations.append(
            f"Cascading analysis found {len(impact_result.affected_documents)} affected documents"
        )

        return recommendations

    def _calculate_impact_level(self, affected_count: int) -> str:
        """Calculate impact level for cascading analysis."""
        if affected_count > 100:
            return "critical"
        elif affected_count > 40:
            return "high"
        elif affected_count > 10:
            return "medium"
        else:
            return "low"


# Factory Classes
class CommitStrategyFactory:
    """Factory for creating commit strategies."""

    _strategies = {
        "standard": StandardCommitStrategy,
        "auto": AutoCommitStrategy,
    }

    @classmethod
    def create_strategy(
        cls,
        strategy_type: str = "standard",
    ) -> CommitStrategy:
        """Create a commit strategy based on type."""
        strategy_class = cls._strategies.get(strategy_type, StandardCommitStrategy)
        return strategy_class()

    @classmethod
    def register_strategy(
        cls,
        name: str,
        strategy_class: type[CommitStrategy],
    ):
        """Register a new commit strategy."""
        cls._strategies[name] = strategy_class


class MergeStrategyFactory:
    """Factory for creating merge strategies."""

    _strategies = {
        "ours": OursMergeStrategy,
        "theirs": TheirsMergeStrategy,
        "manual": ManualMergeStrategy,
    }

    @classmethod
    def create_strategy(
        cls,
        strategy_type: str = "ours",
    ) -> MergeStrategy:
        """Create a merge strategy based on type."""
        strategy_class = cls._strategies.get(strategy_type, OursMergeStrategy)
        return strategy_class()

    @classmethod
    def register_strategy(
        cls,
        name: str,
        strategy_class: type[MergeStrategy],
    ):
        """Register a new merge strategy."""
        cls._strategies[name] = strategy_class


class ImpactAnalysisFactory:
    """Factory for creating impact analysis strategies."""

    _strategies = {
        "dependency": DependencyImpactStrategy,
        "cascading": CascadingImpactStrategy,
    }

    @classmethod
    def create_strategy(
        cls,
        strategy_type: str = "dependency",
        **kwargs,
    ) -> ImpactAnalysisStrategy:
        """Create an impact analysis strategy based on type."""
        strategy_class = cls._strategies.get(strategy_type, DependencyImpactStrategy)
        return strategy_class(**kwargs)

    @classmethod
    def register_strategy(
        cls,
        name: str,
        strategy_class: type[ImpactAnalysisStrategy],
    ):
        """Register a new impact analysis strategy."""
        cls._strategies[name] = strategy_class


# Utility Functions
def compare_branches(
    repo: GitRepository,
    base_branch: str,
    compare_branch: str,
) -> BranchComparison:
    """
    Compare two branches.

    Args:
        repo: Git repository
        base_branch: Base branch name
        compare_branch: Branch to compare

    Returns:
        BranchComparison object
    """
    try:
        # Get branch references
        base = None
        compare = None

        for ref in repo.repo.heads:
            if ref.name == base_branch:
                base = ref
            elif ref.name == compare_branch:
                compare = ref

        if not base or not compare:
            raise ValueError("Branch not found")

        # Get commits ahead/behind
        ahead = list(repo.repo.iter_commits(f"{base}..{compare}"))
        behind = list(repo.repo.iter_commits(f"{compare}..{base}"))

        # Get different files
        diffs = base.commit.diff(compare.commit)
        different_files = [diff.a_path for diff in diffs]

        # Find common ancestor
        merge_base = repo.repo.merge_base(base, compare)
        common_ancestor = str(merge_base[0].hexsha) if merge_base else None

        return BranchComparison(
            base_branch=base_branch,
            compare_branch=compare_branch,
            ahead_count=len(ahead),
            behind_count=len(behind),
            different_files=different_files,
            common_ancestor=common_ancestor,
        )

    except Exception as e:
        logger.error(f"Failed to compare branches: {e}")
        raise


def check_merge_conflicts(
    repo: GitRepository,
    branch_name: str,
) -> bool:
    """
    Check if merging a branch would cause conflicts.

    Args:
        repo: Git repository
        branch_name: Branch to check

    Returns:
        True if conflicts would occur
    """
    try:
        # Save current state
        current_branch = repo.repo.active_branch

        # Try merge in memory
        merge_branch = None
        for ref in repo.repo.heads:
            if ref.name == branch_name:
                merge_branch = ref
                break

        if not merge_branch:
            return False

        # Check for conflicts without actually merging
        merge_base = repo.repo.merge_base(current_branch, merge_branch)
        if not merge_base:
            return True  # No common ancestor means likely conflicts

        # Simple heuristic: check if same files modified
        current_changes = current_branch.commit.diff(merge_base[0])
        branch_changes = merge_branch.commit.diff(merge_base[0])

        current_files = {diff.a_path for diff in current_changes}
        branch_files = {diff.a_path for diff in branch_changes}

        # If same files modified, potential conflicts
        return bool(current_files & branch_files)

    except Exception as e:
        logger.error(f"Failed to check for conflicts: {e}")
        return False


def cleanup_old_branches(
    repo: GitRepository,
    keep_days: int = 30,
    protected_branches: Optional[List[str]] = None,
) -> List[str]:
    """
    Clean up old branches.

    Args:
        repo: Git repository
        keep_days: Number of days to keep branches
        protected_branches: Branches to never delete

    Returns:
        List of deleted branch names
    """
    deleted = []
    cutoff_date = datetime.now().timestamp() - (keep_days * 86400)

    if protected_branches is None:
        protected_branches = ["main", "master", "develop", "staging", "production"]

    try:
        for branch in repo.repo.heads:
            # Skip protected and current branch
            if branch.name in protected_branches or branch == repo.repo.active_branch:
                continue

            # Check last commit date
            if branch.commit.committed_date < cutoff_date:
                branch_name = branch.name
                repo.repo.delete_head(branch, force=True)
                deleted.append(branch_name)
                logger.info(f"Deleted old branch: {branch_name}")

    except Exception as e:
        logger.error(f"Failed to cleanup branches: {e}")

    return deleted
