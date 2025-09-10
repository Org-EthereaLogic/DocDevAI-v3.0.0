"""M012 Version Control Integration - Type Definitions
DevDocAI v3.0.0

This module contains all type definitions, data structures, and enums
for the version control system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# Custom Exceptions
class GitError(Exception):
    """Base exception for Git operations."""

    def __init__(self, message: str, error_code: str = "GIT_ERROR", **kwargs):
        super().__init__(message)
        self.error_code = error_code
        self.details = kwargs


class MergeError(GitError):
    """Exception for merge operations."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, "MERGE_ERROR", **kwargs)


class BranchError(GitError):
    """Exception for branch operations."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, "BRANCH_ERROR", **kwargs)


class CommitError(GitError):
    """Exception for commit operations."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, "COMMIT_ERROR", **kwargs)


class SecurityError(GitError):
    """Exception for security violations."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, "SECURITY_ERROR", **kwargs)


# Enums
class ConflictResolution(Enum):
    """Strategies for resolving merge conflicts."""

    OURS = "ours"
    THEIRS = "theirs"
    MANUAL = "manual"
    AUTO_MERGE = "auto_merge"


class ChangeType(Enum):
    """Types of document changes."""

    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"
    CONFLICT = "conflict"


# Data Classes for Git Operations
@dataclass
class CommitInfo:
    """Information about a Git commit."""

    hash: str
    message: str
    author: str
    timestamp: datetime
    files: List[str]
    stats: Dict[str, int] = field(default_factory=dict)
    parent_commits: List[str] = field(default_factory=list)


@dataclass
class BranchInfo:
    """Information about a Git branch."""

    name: str
    commit: str
    is_active: bool
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    last_commit: Optional[datetime] = None


@dataclass
class MergeConflict:
    """Information about a merge conflict."""

    file_path: str
    our_content: str
    their_content: str
    base_content: Optional[str] = None
    conflict_markers: List[str] = field(default_factory=list)


@dataclass
class ConflictResolutionResult:
    """Result of conflict resolution."""

    file_path: str
    resolved_content: str
    strategy: ConflictResolution
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DocumentChange:
    """Information about a document change."""

    document_id: str
    change_type: ChangeType
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    commit: Optional[str] = None
    timestamp: Optional[datetime] = None


@dataclass
class VersionInfo:
    """Version information for a document."""

    document_id: str
    version: int
    commit: str
    message: str
    timestamp: datetime
    author: str
    file_path: str


@dataclass
class DiffResult:
    """Result of a diff operation."""

    file_path: str
    added_lines: List[str]
    removed_lines: List[str]
    modified_lines: List[Tuple[str, str]]  # (old, new)
    stats: Dict[str, int] = field(default_factory=dict)


@dataclass
class ImpactAnalysisResult:
    """Result of impact analysis."""

    document_id: str
    affected_documents: List[str]
    dependencies: List[str]
    dependents: List[str]
    impact_level: str  # low, medium, high, critical
    recommendations: List[str] = field(default_factory=list)


@dataclass
class MergeResult:
    """Result of a merge operation."""

    success: bool
    commit: Optional[str] = None
    conflicts: Optional[List[MergeConflict]] = None
    resolved_files: List[str] = field(default_factory=list)
    message: Optional[str] = None


@dataclass
class BranchComparison:
    """Comparison between two branches."""

    base_branch: str
    compare_branch: str
    ahead_count: int
    behind_count: int
    different_files: List[str]
    common_ancestor: Optional[str] = None


@dataclass
class UncommittedChanges:
    """Information about uncommitted changes."""

    modified: List[str]
    added: List[str]
    deleted: List[str]
    untracked: List[str]
    has_changes: bool = False


@dataclass
class TagInfo:
    """Information about a Git tag."""

    name: str
    commit: str
    message: Optional[str] = None
    tagger: Optional[str] = None
    timestamp: Optional[datetime] = None


# Configuration and Context Types
@dataclass
class VersionControlConfig:
    """Configuration for version control operations."""

    enabled: bool = True
    auto_commit: bool = False
    branch_prefix: str = "docs/"
    commit_template: str = "docs: {message}"
    merge_strategy: str = "ours"
    track_metadata: bool = True
    enforce_authentication: bool = False
    enforce_rate_limiting: bool = True
    enforce_integrity: bool = True
    max_repository_size: int = 10 * 1024 * 1024 * 1024  # 10GB
    admin_token: Optional[str] = None

    @classmethod
    def from_config(cls, config):
        """Create VersionControlConfig from configuration manager."""
        return cls(
            enabled=config.get("version_control.enabled", True),
            auto_commit=config.get("version_control.auto_commit", False),
            branch_prefix=config.get("version_control.branch_prefix", "docs/"),
            commit_template=config.get("version_control.commit_template", "docs: {message}"),
            merge_strategy=config.get("version_control.merge_strategy", "ours"),
            track_metadata=config.get("version_control.track_metadata", True),
            enforce_authentication=config.get("version_control.enforce_authentication", False),
            enforce_rate_limiting=config.get("version_control.enforce_rate_limiting", True),
            enforce_integrity=config.get("version_control.enforce_integrity", True),
            max_repository_size=config.get(
                "version_control.max_repository_size", 10 * 1024 * 1024 * 1024
            ),
            admin_token=config.get("version_control.admin_token"),
        )


# Operation Result Types
@dataclass
class OperationResult:
    """Generic result for Git operations."""

    success: bool
    message: str
    data: Optional[Any] = None
    error: Optional[Exception] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchOperationResult:
    """Result of batch operations."""

    total_operations: int
    successful: int
    failed: int
    results: List[OperationResult]
    execution_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)
