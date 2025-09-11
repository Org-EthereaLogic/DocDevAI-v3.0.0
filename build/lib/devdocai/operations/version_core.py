"""M012 Version Control Integration - Core Git Operations
DevDocAI v3.0.0

This module contains core Git operations abstracted from the main module.
Provides low-level Git functionality with clean interfaces.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import git
from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

from devdocai.operations.version_types import (
    BranchError,
    BranchInfo,
    CommitError,
    CommitInfo,
    ConflictResolution,
    ConflictResolutionResult,
    DiffResult,
    GitError,
    MergeConflict,
    MergeError,
    MergeResult,
    TagInfo,
    UncommittedChanges,
    VersionInfo,
)

logger = logging.getLogger(__name__)


class GitRepository:
    """Core Git repository operations wrapper."""

    def __init__(self, repo_path: Path):
        """Initialize Git repository wrapper."""
        self.repo_path = Path(repo_path)
        self.repo = None
        self._init_repository()

    def _init_repository(self):
        """Initialize or open Git repository."""
        try:
            if (self.repo_path / ".git").exists():
                self.repo = Repo(self.repo_path)
            else:
                self.repo = self._create_repository()
        except (InvalidGitRepositoryError, GitCommandError) as e:
            raise GitError(f"Failed to initialize repository: {e}") from e

    def _create_repository(self) -> Repo:
        """Create a new Git repository."""
        self.repo_path.mkdir(parents=True, exist_ok=True)
        repo = Repo.init(self.repo_path)

        # Set default configuration
        with repo.config_writer() as config:
            config.set_value("user", "name", "DevDocAI")
            config.set_value("user", "email", "devdocai@local")

        # Create initial commit
        self._create_initial_commit(repo)
        return repo

    def _create_initial_commit(self, repo: Repo):
        """Create initial commit in new repository."""
        try:
            # Check if repo has any commits
            _ = repo.head.commit
        except Exception:
            # No commits yet, create initial one
            readme_path = self.repo_path / "README.md"
            readme_path.write_text("# Documentation Repository\n\nManaged by DevDocAI")

            # Ensure we're in the right directory
            import os

            cwd = os.getcwd()
            try:
                os.chdir(str(self.repo_path))
                repo.index.add(["README.md"])
                repo.index.commit("Initial commit")
            finally:
                os.chdir(cwd)

            logger.info(f"Created initial commit in repository at {self.repo_path}")

    def commit(
        self,
        files: List[str],
        message: str,
        author: Optional[str] = None,
    ) -> CommitInfo:
        """
        Create a commit with specified files.

        Args:
            files: List of file paths to commit
            message: Commit message
            author: Author name (optional)

        Returns:
            CommitInfo object
        """
        try:
            # Add files to index
            self.repo.index.add(files)

            # Create commit
            if author:
                actor = git.Actor(author, f"{author}@devdocai.local")
                commit = self.repo.index.commit(message, author=actor)
            else:
                commit = self.repo.index.commit(message)

            # Create CommitInfo
            return CommitInfo(
                hash=str(commit.hexsha),
                message=message,
                author=author or "DevDocAI",
                timestamp=datetime.fromtimestamp(commit.committed_date),
                files=files,
                stats={"additions": len(files), "deletions": 0},
                parent_commits=[str(p.hexsha) for p in commit.parents],
            )
        except Exception as e:
            raise CommitError(f"Failed to create commit: {e}") from e

    def create_branch(
        self,
        name: str,
        from_commit: Optional[str] = None,
    ) -> BranchInfo:
        """
        Create a new branch.

        Args:
            name: Branch name
            from_commit: Base commit (optional, defaults to HEAD)

        Returns:
            BranchInfo object
        """
        try:
            # Get base commit
            base = self.repo.commit(from_commit) if from_commit else self.repo.head.commit

            # Create and checkout branch
            new_branch = self.repo.create_head(name, base)
            new_branch.checkout()

            return BranchInfo(
                name=name,
                commit=str(base.hexsha),
                is_active=True,
                created_at=datetime.now(),
            )
        except Exception as e:
            raise BranchError(f"Failed to create branch: {e}") from e

    def switch_branch(self, branch_name: str) -> bool:
        """
        Switch to a different branch.

        Args:
            branch_name: Name of branch to switch to

        Returns:
            True if successful
        """
        try:
            branch = self.repo.heads[branch_name]
            branch.checkout()
            logger.info(f"Switched to branch: {branch_name}")
            return True
        except Exception as e:
            raise BranchError(f"Failed to switch branch: {e}") from e

    def merge_branch(
        self,
        branch_name: str,
        message: Optional[str] = None,
    ) -> MergeResult:
        """
        Merge a branch into current branch.

        Args:
            branch_name: Branch to merge
            message: Merge commit message (optional)

        Returns:
            MergeResult object
        """
        try:
            # Find branch to merge
            merge_branch = None
            for ref in self.repo.heads:
                if ref.name == branch_name:
                    merge_branch = ref
                    break

            if not merge_branch:
                raise MergeError(f"Branch not found: {branch_name}")

            # Attempt merge
            try:
                merge_base = self.repo.merge_base(self.repo.head, merge_branch)
                self.repo.index.merge_tree(merge_branch, base=merge_base[0] if merge_base else None)

                # Check for conflicts
                if self.repo.index.conflicts:
                    conflicts = self._process_conflicts()
                    return MergeResult(success=False, conflicts=conflicts)

                # Commit merge
                merge_message = message or f"Merge branch '{branch_name}'"
                commit = self.repo.index.commit(merge_message)

                return MergeResult(
                    success=True,
                    commit=str(commit.hexsha),
                    message=merge_message,
                    resolved_files=list(self.repo.index.entries.keys()),
                )

            except GitCommandError as e:
                conflicts = self._process_conflicts()
                return MergeResult(success=False, conflicts=conflicts, message=str(e))

        except Exception as e:
            if isinstance(e, MergeError):
                raise
            raise MergeError(f"Failed to merge branch: {e}") from e

    def _process_conflicts(self) -> List[MergeConflict]:
        """Process merge conflicts from repository."""
        conflicts = []

        for item in self.repo.index.conflicts:
            if item[0]:  # Has conflict
                file_path = item[0].path

                # Read conflict markers from file
                conflict_file = self.repo_path / file_path
                if conflict_file.exists():
                    content = conflict_file.read_text()

                    # Parse conflict markers
                    our_content = ""
                    their_content = ""
                    markers = []

                    lines = content.split("\n")
                    in_ours = False
                    in_theirs = False

                    for line in lines:
                        if line.startswith("<<<<<<<"):
                            in_ours = True
                            markers.append(line)
                        elif line.startswith("======="):
                            in_ours = False
                            in_theirs = True
                            markers.append(line)
                        elif line.startswith(">>>>>>>"):
                            in_theirs = False
                            markers.append(line)
                        elif in_ours:
                            our_content += line + "\n"
                        elif in_theirs:
                            their_content += line + "\n"

                    conflicts.append(
                        MergeConflict(
                            file_path=file_path,
                            our_content=our_content.strip(),
                            their_content=their_content.strip(),
                            conflict_markers=markers,
                        )
                    )

        return conflicts

    def resolve_conflict(
        self,
        conflict: MergeConflict,
        strategy: ConflictResolution,
        content: Optional[str] = None,
    ) -> ConflictResolutionResult:
        """
        Resolve a merge conflict.

        Args:
            conflict: MergeConflict to resolve
            strategy: Resolution strategy
            content: Manual resolution content (for MANUAL strategy)

        Returns:
            ConflictResolutionResult object
        """
        try:
            resolved_content = ""

            if strategy == ConflictResolution.OURS:
                resolved_content = conflict.our_content
            elif strategy == ConflictResolution.THEIRS:
                resolved_content = conflict.their_content
            elif strategy == ConflictResolution.MANUAL:
                if not content:
                    raise ValueError("Manual resolution requires content")
                resolved_content = content
            elif strategy == ConflictResolution.AUTO_MERGE:
                # Simple auto-merge: combine both if possible
                resolved_content = f"{conflict.our_content}\n\n{conflict.their_content}"

            # Write resolved content
            conflict_file = self.repo_path / conflict.file_path
            conflict_file.write_text(resolved_content)

            # Add to index
            self.repo.index.add([conflict.file_path])

            return ConflictResolutionResult(
                file_path=conflict.file_path,
                resolved_content=resolved_content,
                strategy=strategy,
            )

        except Exception as e:
            raise MergeError(f"Failed to resolve conflict: {e}") from e

    def get_file_history(
        self,
        file_path: str,
        limit: int = 10,
    ) -> List[VersionInfo]:
        """
        Get version history for a file.

        Args:
            file_path: Path to file
            limit: Maximum number of versions to return

        Returns:
            List of VersionInfo objects
        """
        try:
            history = []
            commits = list(self.repo.iter_commits(paths=file_path, max_count=limit))

            for i, commit in enumerate(commits):
                version_info = VersionInfo(
                    document_id=Path(file_path).stem,
                    version=len(commits) - i,
                    commit=str(commit.hexsha),
                    message=commit.message.strip(),
                    timestamp=datetime.fromtimestamp(commit.committed_date),
                    author=commit.author.name,
                    file_path=file_path,
                )
                history.append(version_info)

            return history

        except Exception as e:
            logger.error(f"Failed to get file history: {e}")
            return []

    def get_diff(
        self,
        file_path: str,
        from_commit: str,
        to_commit: Optional[str] = None,
    ) -> Optional[DiffResult]:
        """
        Get diff for a file between commits.

        Args:
            file_path: Path to file
            from_commit: Starting commit
            to_commit: Ending commit (defaults to HEAD)

        Returns:
            DiffResult object or None
        """
        try:
            # Get commits
            commit_from = self.repo.commit(from_commit)
            commit_to = self.repo.commit(to_commit) if to_commit else self.repo.head.commit

            # Get diff
            diffs = commit_from.diff(commit_to, paths=file_path, create_patch=True)

            if not diffs:
                return None

            diff = diffs[0]

            # Parse diff
            added_lines = []
            removed_lines = []
            modified_lines = []

            if diff.diff:
                lines = diff.diff.decode("utf-8").split("\n")
                for line in lines:
                    if line.startswith("+") and not line.startswith("+++"):
                        added_lines.append(line[1:])
                    elif line.startswith("-") and not line.startswith("---"):
                        removed_lines.append(line[1:])

            return DiffResult(
                file_path=file_path,
                added_lines=added_lines,
                removed_lines=removed_lines,
                modified_lines=modified_lines,
                stats={
                    "additions": len(added_lines),
                    "deletions": len(removed_lines),
                },
            )

        except Exception as e:
            logger.error(f"Failed to get diff: {e}")
            return None

    def tag_version(
        self,
        tag_name: str,
        message: Optional[str] = None,
        commit: Optional[str] = None,
    ) -> TagInfo:
        """
        Create a version tag.

        Args:
            tag_name: Tag name
            message: Tag message (optional)
            commit: Commit to tag (defaults to HEAD)

        Returns:
            TagInfo object
        """
        try:
            # Get commit to tag
            target_commit = self.repo.commit(commit) if commit else self.repo.head.commit

            # Create tag
            if message:
                self.repo.create_tag(tag_name, target_commit, message=message)
            else:
                self.repo.create_tag(tag_name, target_commit)

            return TagInfo(
                name=tag_name,
                commit=str(target_commit.hexsha),
                message=message,
                timestamp=datetime.now(),
            )

        except Exception as e:
            raise GitError(f"Failed to create tag: {e}") from e

    def rollback_to(self, commit_hash: str) -> bool:
        """
        Rollback to a specific commit.

        Args:
            commit_hash: Commit hash to rollback to

        Returns:
            True if successful
        """
        try:
            target_commit = self.repo.commit(commit_hash)
            self.repo.head.reset(target_commit, index=True, working_tree=True)
            logger.info(f"Rolled back to commit: {commit_hash[:8]}")
            return True
        except Exception as e:
            raise GitError(f"Failed to rollback: {e}") from e

    def get_uncommitted_changes(self) -> UncommittedChanges:
        """
        Get list of uncommitted changes.

        Returns:
            UncommittedChanges object
        """
        try:
            # Get diff for staged and unstaged changes
            diff_staged = self.repo.index.diff(self.repo.head.commit)
            diff_unstaged = self.repo.index.diff(None)

            modified = []
            added = []
            deleted = []

            # Process staged changes
            for diff in diff_staged:
                if diff.change_type == "M":
                    modified.append(diff.a_path)
                elif diff.change_type == "A":
                    added.append(diff.a_path)
                elif diff.change_type == "D":
                    deleted.append(diff.a_path)

            # Process unstaged changes
            for diff in diff_unstaged:
                if diff.change_type == "M" and diff.a_path not in modified:
                    modified.append(diff.a_path)

            # Get untracked files
            untracked = self.repo.untracked_files

            has_changes = bool(modified or added or deleted or untracked)

            return UncommittedChanges(
                modified=modified,
                added=added,
                deleted=deleted,
                untracked=untracked,
                has_changes=has_changes,
            )

        except Exception as e:
            logger.error(f"Failed to get uncommitted changes: {e}")
            return UncommittedChanges([], [], [], [])

    def stash_changes(self, message: Optional[str] = None) -> Optional[str]:
        """
        Stash uncommitted changes.

        Args:
            message: Stash message (optional)

        Returns:
            Stash ID if successful
        """
        try:
            stash_message = message or f"Stash at {datetime.now().isoformat()}"
            self.repo.git.stash("save", stash_message)

            # Get stash ID
            stashes = self.repo.git.stash("list").split("\n")
            if stashes and stashes[0]:
                stash_id = stashes[0].split(":")[0]
                logger.info(f"Created stash: {stash_id}")
                return stash_id

            return None

        except Exception as e:
            logger.error(f"Failed to stash changes: {e}")
            return None

    def apply_stash(self, stash_id: str) -> bool:
        """
        Apply a stashed change.

        Args:
            stash_id: Stash identifier

        Returns:
            True if successful
        """
        try:
            self.repo.git.stash("apply", stash_id)
            logger.info(f"Applied stash: {stash_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to apply stash: {e}")
            return False

    def get_current_branch(self) -> BranchInfo:
        """
        Get information about current branch.

        Returns:
            BranchInfo object
        """
        try:
            current = self.repo.active_branch
            return BranchInfo(
                name=current.name,
                commit=str(current.commit.hexsha),
                is_active=True,
                last_commit=datetime.fromtimestamp(current.commit.committed_date),
            )
        except Exception as e:
            logger.error(f"Failed to get current branch: {e}")
            raise BranchError(f"Failed to get current branch: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get repository statistics.

        Returns:
            Dictionary of statistics
        """
        try:
            stats = {
                "total_commits": len(list(self.repo.iter_commits())),
                "total_branches": len(self.repo.heads),
                "total_tags": len(self.repo.tags),
                "current_branch": self.repo.active_branch.name,
                "repository_size": sum(
                    f.stat().st_size for f in self.repo_path.rglob("*") if f.is_file()
                ),
                "uncommitted_changes": self.get_uncommitted_changes().has_changes,
            }

            # Add file statistics
            file_stats = {}
            for file_path in self.repo_path.rglob("*.md"):
                if file_path.is_file():
                    rel_path = file_path.relative_to(self.repo_path)
                    file_stats[str(rel_path)] = {
                        "size": file_path.stat().st_size,
                        "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                    }

            stats["files"] = file_stats
            stats["total_files"] = len(file_stats)

            return stats

        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
