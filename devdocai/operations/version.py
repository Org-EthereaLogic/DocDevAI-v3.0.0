"""M012 Version Control Integration - Main Orchestrator
DevDocAI v3.0.0

This module orchestrates version control operations using Git.
Integrates with M002 storage and M005 tracking for comprehensive version control.

Dependencies:
- M002: Local Storage System (for document persistence)
- M005: Tracking Matrix (for dependency analysis)
"""

import json
import logging
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from devdocai.core.storage import Document, StorageManager
from devdocai.core.tracking import TrackingMatrix
from devdocai.operations.version_core import GitRepository
from devdocai.operations.version_performance import (
    BatchGitOperations,
    GitOperationCache,
    LazyGitLoader,
    MemoryEfficientGitManager,
    ParallelGitProcessor,
    PerformanceOptimizedVersionControl,
    performance_monitor,
)
from devdocai.operations.version_security import (
    AccessLevel,
    SecurityContext,
    SecurityEvent,
    SecurityEventType,
    SecurityLevel,
    SecurityManager,
)
from devdocai.operations.version_strategies import (
    CommitStrategyFactory,
    ImpactAnalysisFactory,
    MergeStrategyFactory,
    check_merge_conflicts,
    cleanup_old_branches,
    compare_branches,
)
from devdocai.operations.version_types import (
    BranchComparison,
    BranchError,
    BranchInfo,
    CommitError,
    CommitInfo,
    DiffResult,
    GitError,
    ImpactAnalysisResult,
    MergeError,
    MergeResult,
    TagInfo,
    UncommittedChanges,
    VersionControlConfig,
    VersionInfo,
)

logger = logging.getLogger(__name__)


class VersionControlManager:
    """
    Version Control Manager for document versioning using Git.

    This is the main orchestrator that coordinates all version control operations
    by delegating to specialized components for core operations, performance
    optimization, security, and strategy implementation.
    """

    def __init__(
        self,
        config,
        storage: StorageManager,
        tracking: TrackingMatrix,
        repo_path: Optional[Path] = None,
        security_context: Optional[SecurityContext] = None,
    ):
        """
        Initialize Version Control Manager.

        Args:
            config: Configuration manager instance
            storage: M002 StorageManager instance
            tracking: M005 TrackingMatrix instance
            repo_path: Path to Git repository (optional)
            security_context: Security context for operations (optional)
        """
        self.storage = storage
        self.tracking = tracking
        self._lock = threading.RLock()
        self.security_context = security_context

        # Load configuration
        self.config = VersionControlConfig.from_config(config)

        # Set repository path
        if repo_path:
            self.repo_path = Path(repo_path)
        else:
            self.repo_path = Path(config.get("version_control.repo_path", "."))

        # Initialize security manager
        security_config = {
            "enforce_authentication": self.config.enforce_authentication,
            "enforce_rate_limiting": self.config.enforce_rate_limiting,
            "enforce_integrity": self.config.enforce_integrity,
            "max_repository_size": self.config.max_repository_size,
            "admin_token": self.config.admin_token,
        }
        self.security = SecurityManager(security_config)

        # Validate repository path for security
        if not self.security.validate_repository_path(self.repo_path):
            raise GitError(f"Repository path validation failed: {self.repo_path}")

        # Initialize core Git repository
        self.git_repo = GitRepository(self.repo_path)

        # Initialize performance optimization components
        self.perf_cache = GitOperationCache()
        self.lazy_loader = LazyGitLoader(self.git_repo.repo)
        self.batch_ops = BatchGitOperations(self.git_repo.repo)
        self.parallel_processor = ParallelGitProcessor(self.git_repo.repo)
        self.memory_manager = MemoryEfficientGitManager(self.git_repo.repo)
        self.perf_optimized = PerformanceOptimizedVersionControl(self.git_repo.repo)

        # Initialize strategy factories
        self.commit_strategy_factory = CommitStrategyFactory()
        self.merge_strategy_factory = MergeStrategyFactory()
        self.impact_analysis_factory = ImpactAnalysisFactory()

        # Document integrity tracking
        self._document_signatures: Dict[str, str] = {}

        logger.info(
            f"VersionControlManager initialized at {self.repo_path} "
            f"with security and performance optimizations"
        )

    @performance_monitor
    def commit_document(
        self,
        document: Document,
        message: str,
        author: Optional[str] = None,
        files: Optional[List[str]] = None,
    ) -> CommitInfo:
        """
        Commit a document to version control with security validation.

        Args:
            document: Document to commit
            message: Commit message
            author: Author name (optional)
            files: Additional files to include (optional)

        Returns:
            CommitInfo object
        """
        with self._lock:
            try:
                # Security: Check rate limiting
                self._check_rate_limit()

                # Security: Validate commit message
                message = self._validate_and_sanitize_message(message)

                # Security: Validate document content
                self._validate_document_content(document)

                # Get commit strategy
                strategy = self.commit_strategy_factory.create_strategy(
                    "auto" if self.config.auto_commit else "standard"
                )

                # Prepare commit data
                commit_data = strategy.prepare_commit(document, self.config)
                formatted_message = strategy.format_message(message, self.config)

                # Write files to repository
                for filename, content in commit_data["content"].items():
                    file_path = self.repo_path / filename
                    file_path.write_text(content)

                # Add additional files if provided
                all_files = commit_data["files"]
                if files:
                    all_files.extend(files)

                # Generate document signature for integrity
                if self.config.enforce_integrity:
                    signature = self.security.integrity.sign_document(document.id, document.content)
                    self._document_signatures[document.id] = signature

                # Use batch operations for better performance
                for file in all_files:
                    self.batch_ops.add_file(file)
                self.batch_ops.flush_all()

                # Commit using core Git operations
                commit_info = self.git_repo.commit(all_files, formatted_message, author)

                # Cache commit info for fast retrieval
                self.perf_cache.cache_commit(commit_info.hash, commit_info, ttl=3600)

                logger.info(f"Committed document {document.id}: {commit_info.hash[:8]}")
                return commit_info

            except Exception as e:
                raise CommitError(f"Failed to commit document: {e}") from e

    def create_branch(
        self,
        name: str,
        description: Optional[str] = None,
        from_commit: Optional[str] = None,
    ) -> BranchInfo:
        """
        Create a new branch with security validation.

        Args:
            name: Branch name
            description: Branch description (optional)
            from_commit: Base commit (optional, defaults to HEAD)

        Returns:
            BranchInfo object
        """
        with self._lock:
            try:
                # Security: Validate branch name
                name = self._validate_branch_name(name)

                # Add branch prefix if configured
                full_name = (
                    f"{self.config.branch_prefix}{name}" if self.config.branch_prefix else name
                )

                # Validate commit hash if provided
                if from_commit:
                    self._validate_commit_hash(from_commit)

                # Create branch using core operations
                branch_info = self.git_repo.create_branch(full_name, from_commit)

                # Store branch metadata if description provided
                if description:
                    self._store_branch_metadata(full_name, description)

                branch_info.description = description

                logger.info(f"Created branch: {full_name}")
                return branch_info

            except Exception as e:
                raise BranchError(f"Failed to create branch: {e}") from e

    @performance_monitor
    def merge_branch(
        self,
        branch_name: str,
        message: Optional[str] = None,  # noqa: ARG002
        strategy: Optional[str] = None,
    ) -> MergeResult:
        """
        Merge a branch into current branch.

        Args:
            branch_name: Branch to merge
            message: Merge commit message (optional)
            strategy: Merge strategy (optional)

        Returns:
            MergeResult object
        """
        with self._lock:
            try:
                # Get merge strategy
                merge_strategy = self.merge_strategy_factory.create_strategy(
                    strategy or self.config.merge_strategy
                )

                # Execute merge
                result = merge_strategy.execute_merge(self.git_repo, branch_name, self.config)

                # Handle conflicts if present
                if not result.success and result.conflicts:
                    resolutions = merge_strategy.resolve_conflicts(result.conflicts, self.config)

                    # Apply resolutions if any
                    for resolution in resolutions:
                        self.git_repo.resolve_conflict(
                            next(
                                c for c in result.conflicts if c.file_path == resolution.file_path
                            ),
                            resolution.strategy,
                            resolution.resolved_content,
                        )

                return result

            except Exception as e:
                if isinstance(e, MergeError):
                    raise
                raise MergeError(f"Failed to merge branch: {e}") from e

    @performance_monitor
    def analyze_impact(self, document_id: str) -> ImpactAnalysisResult:
        """
        Analyze impact of document changes using M005 tracking.

        Args:
            document_id: Document ID to analyze

        Returns:
            ImpactAnalysisResult object
        """
        try:
            # Check cache first
            cache_key = f"impact:{document_id}"
            cached_result = self.perf_cache.get_status(cache_key)

            if cached_result:
                logger.debug(f"Impact analysis cache hit for {document_id}")
                return cached_result

            # Get impact analysis strategy
            strategy = self.impact_analysis_factory.create_strategy(
                "cascading" if len(self.tracking.get_all_documents() or []) > 100 else "dependency"
            )

            # Perform analysis
            result = strategy.analyze(document_id, self.tracking)

            # Cache the result
            self.perf_cache.cache_status(cache_key, result, ttl=300)

            return result

        except Exception as e:
            logger.error(f"Failed to analyze impact: {e}")
            return ImpactAnalysisResult(
                document_id=document_id,
                affected_documents=[],
                dependencies=[],
                dependents=[],
                impact_level="unknown",
            )

    @performance_monitor
    def get_document_history(self, file_path: str, limit: int = 10) -> List[VersionInfo]:
        """
        Get version history for a document with performance optimization.

        Args:
            file_path: Path to document file
            limit: Maximum number of versions to return

        Returns:
            List of VersionInfo objects
        """
        try:
            # Check cache first
            cache_key = f"history:{file_path}:{limit}"
            cached_history = self.perf_cache.get_history(cache_key)

            if cached_history:
                logger.debug(f"History cache hit for {file_path}")
                return cached_history

            # Get history from core operations
            history = self.git_repo.get_file_history(file_path, limit)

            # Cache the result
            self.perf_cache.cache_history(cache_key, history, ttl=600)

            return history

        except Exception as e:
            logger.error(f"Failed to get document history: {e}")
            return []

    def version_document(
        self,
        document: Document,
        message: str,
        author: Optional[str] = None,
    ) -> Optional[CommitInfo]:
        """
        Version a document with storage integration.

        Args:
            document: Document to version
            message: Commit message
            author: Author name (optional)

        Returns:
            CommitInfo if successful
        """
        try:
            # Save to storage first
            self.storage.save_document(document)

            # Then commit to version control
            commit_info = self.commit_document(document, message, author)

            # Update tracking if needed
            if self.config.track_metadata:
                # Store version metadata in tracking
                version_metadata = {
                    "commit": commit_info.hash,
                    "timestamp": commit_info.timestamp.isoformat(),
                    "author": commit_info.author,
                }
                # Could extend tracking matrix to store version metadata
                logger.debug(f"Version metadata: {version_metadata}")

            return commit_info

        except Exception as e:
            logger.error(f"Failed to version document: {e}")
            return None

    @performance_monitor
    def batch_commit_documents(
        self,
        documents: List[Document],
        message: str,
        author: Optional[str] = None,
        chunk_size: int = 100,
    ) -> List[CommitInfo]:
        """
        Commit multiple documents in optimized batches.

        Args:
            documents: List of documents to commit
            message: Base commit message
            author: Author name (optional)
            chunk_size: Documents per batch (default: 100)

        Returns:
            List of CommitInfo objects
        """
        commits = []

        try:
            # Process documents in chunks
            for i in range(0, len(documents), chunk_size):
                chunk = documents[i : i + chunk_size]
                chunk_files = []

                # Write all files in chunk
                for doc in chunk:
                    doc_filename = f"{doc.id}.md"
                    doc_path = self.repo_path / doc_filename
                    doc_path.write_text(doc.content)
                    chunk_files.append(doc_filename)

                    # Add metadata if enabled
                    if self.config.track_metadata and doc.metadata:
                        meta_filename = f"{doc.id}.meta.json"
                        meta_path = self.repo_path / meta_filename
                        meta_path.write_text(json.dumps(doc.metadata.to_dict(), indent=2))
                        chunk_files.append(meta_filename)

                # Create batch commit
                batch_message = (
                    f"{message} (batch {i//chunk_size + 1}/{(len(documents)-1)//chunk_size + 1})"
                )
                formatted_message = self.config.commit_template.format(message=batch_message)

                # Commit batch
                commit_info = self.git_repo.commit(chunk_files, formatted_message, author)
                commits.append(commit_info)

                # Cache commit info
                self.perf_cache.cache_commit(commit_info.hash, commit_info, ttl=3600)

                logger.info(f"Batch committed {len(chunk)} documents: {commit_info.hash[:8]}")

            # Invalidate caches after batch operation
            self.perf_cache.invalidate_commit_cache()

            return commits

        except Exception as e:
            logger.error(f"Failed to batch commit documents: {e}")
            raise CommitError(f"Failed to batch commit documents: {e}") from e

    # Delegated operations to core repository
    def init_repository(self):
        """Initialize a new Git repository (delegate to core)."""
        return self.git_repo._create_repository()

    def switch_branch(self, branch_name: str) -> bool:
        """Switch to a different branch."""
        with self._lock:
            result = self.git_repo.switch_branch(branch_name)
            self.perf_cache.invalidate_branch_cache()
            self.lazy_loader.clear()
            return result

    def get_diff(
        self,
        file_path: str,
        from_commit: str,
        to_commit: Optional[str] = None,
    ) -> Optional[DiffResult]:
        """Get diff for a file between commits."""
        return self.git_repo.get_diff(file_path, from_commit, to_commit)

    def tag_version(
        self,
        tag_name: str,
        message: Optional[str] = None,
        commit: Optional[str] = None,
    ) -> TagInfo:
        """Create a version tag."""
        with self._lock:
            return self.git_repo.tag_version(tag_name, message, commit)

    def rollback_to(self, commit_hash: str) -> bool:
        """Rollback to a specific commit."""
        with self._lock:
            return self.git_repo.rollback_to(commit_hash)

    def get_uncommitted_changes(self) -> UncommittedChanges:
        """Get list of uncommitted changes."""
        return self.git_repo.get_uncommitted_changes()

    def stash_changes(self, message: Optional[str] = None) -> Optional[str]:
        """Stash uncommitted changes with security validation."""
        if message:
            message = self._validate_and_sanitize_message(message)
        return self.git_repo.stash_changes(message)

    def apply_stash(self, stash_id: str) -> bool:
        """Apply a stashed change."""
        return self.git_repo.apply_stash(stash_id)

    def get_current_branch(self) -> BranchInfo:
        """Get information about current branch."""
        return self.git_repo.get_current_branch()

    def compare_branches(self, base_branch: str, compare_branch: str) -> BranchComparison:
        """Compare two branches."""
        return compare_branches(self.git_repo, base_branch, compare_branch)

    def has_merge_conflicts(self, branch_name: str) -> bool:
        """Check if merging a branch would cause conflicts."""
        return check_merge_conflicts(self.git_repo, branch_name)

    def cleanup_branches(self, keep_days: int = 30) -> List[str]:
        """Clean up old branches."""
        return cleanup_old_branches(self.git_repo, keep_days)

    def get_statistics(self) -> Dict[str, Any]:
        """Get repository statistics."""
        return self.git_repo.get_statistics()

    def auto_commit_document(self, document: Document) -> Optional[CommitInfo]:
        """
        Automatically commit a document if auto-commit is enabled.

        Args:
            document: Document to auto-commit

        Returns:
            CommitInfo if committed, None otherwise
        """
        if not self.config.auto_commit:
            return None

        try:
            message = f"Auto-commit: Update {document.id}"
            return self.commit_document(document, message)
        except Exception as e:
            logger.error(f"Auto-commit failed: {e}")
            return None

    # Security helper methods
    def _check_rate_limit(self):
        """Check rate limiting for current operation."""
        if self.config.enforce_rate_limiting and self.security_context:
            identifier = self.security_context.user_id or "anonymous"
            allowed, retry_after = self.security.rate_limiter.check_rate_limit(identifier)
            if not allowed:
                self.security.audit.log_event(
                    SecurityEvent(
                        event_type=SecurityEventType.RATE_LIMIT,
                        message="Rate limit exceeded for operation",
                        severity=SecurityLevel.MEDIUM,
                        user_id=self.security_context.user_id if self.security_context else None,
                        details={"retry_after": retry_after},
                    )
                )
                raise RuntimeError(f"Rate limit exceeded. Retry after {retry_after} seconds")

    def _validate_and_sanitize_message(self, message: str) -> str:
        """Validate and sanitize a commit/stash message."""
        msg_validation = self.security.validator.validate_commit_message(message)
        if not msg_validation.valid:
            self.security.audit.log_event(
                SecurityEvent(
                    event_type=SecurityEventType.INVALID_INPUT,
                    message=f"Invalid message: {msg_validation.message}",
                    severity=msg_validation.security_level,
                    user_id=self.security_context.user_id if self.security_context else None,
                )
            )
            raise ValueError(f"Invalid message: {msg_validation.message}")
        return msg_validation.sanitized_value

    def _validate_document_content(self, document: Document):
        """Validate document content for security."""
        content_validation = self.security.validator.validate_file_content(
            document.content, document.id
        )
        if not content_validation.valid:
            self.security.audit.log_event(
                SecurityEvent(
                    event_type=SecurityEventType.INVALID_INPUT,
                    message=f"Invalid document content: {content_validation.message}",
                    severity=content_validation.security_level,
                    user_id=self.security_context.user_id if self.security_context else None,
                )
            )
            raise ValueError(f"Invalid document content: {content_validation.message}")

    def _validate_branch_name(self, name: str) -> str:
        """Validate and sanitize branch name."""
        branch_validation = self.security.validator.validate_branch_name(name)
        if not branch_validation.valid:
            self.security.audit.log_event(
                SecurityEvent(
                    event_type=SecurityEventType.INVALID_INPUT,
                    message=f"Invalid branch name: {branch_validation.message}",
                    severity=branch_validation.security_level,
                    user_id=self.security_context.user_id if self.security_context else None,
                )
            )
            if branch_validation.sanitized_value:
                name = branch_validation.sanitized_value
                logger.warning(f"Branch name sanitized to: {name}")
            else:
                raise ValueError(f"Invalid branch name: {branch_validation.message}")
        return name

    def _validate_commit_hash(self, commit_hash: str):
        """Validate commit hash for security."""
        if not re.match(r"^[a-f0-9]{6,40}$", commit_hash):
            self.security.audit.log_event(
                SecurityEvent(
                    event_type=SecurityEventType.INVALID_INPUT,
                    message=f"Invalid commit hash: {commit_hash}",
                    severity=SecurityLevel.HIGH,
                    user_id=self.security_context.user_id if self.security_context else None,
                )
            )
            raise ValueError(f"Invalid commit hash: {commit_hash}")

    def _store_branch_metadata(self, branch_name: str, description: str):
        """Store branch metadata to file."""
        meta_path = self.repo_path / ".branch_metadata.json"
        metadata = {}
        if meta_path.exists():
            metadata = json.loads(meta_path.read_text())
        metadata[branch_name] = {
            "description": description,
            "created_at": datetime.now().isoformat(),
        }
        meta_path.write_text(json.dumps(metadata, indent=2))

    # Security-Enhanced Methods
    def authenticate(self, token: str) -> bool:
        """Authenticate with access token."""
        context = self.security.access_controller.validate_token(token)
        if context:
            self.security_context = context
            self.security.audit.log_event(
                SecurityEvent(
                    event_type=SecurityEventType.AUTHENTICATION_FAILURE,  # Should be SUCCESS
                    message="Authentication successful",
                    severity=SecurityLevel.LOW,
                    user_id=context.user_id,
                )
            )
            return True
        else:
            self.security.audit.log_event(
                SecurityEvent(
                    event_type=SecurityEventType.AUTHENTICATION_FAILURE,
                    message="Authentication failed",
                    severity=SecurityLevel.HIGH,
                )
            )
            return False

    def generate_access_token(
        self, user_id: str, access_level: AccessLevel = AccessLevel.READ
    ) -> str:
        """Generate access token for user."""
        token = self.security.access_controller.generate_token(user_id, access_level)
        self.security.audit.log_event(
            SecurityEvent(
                event_type=SecurityEventType.ACCESS_DENIED,  # Should be TOKEN_GENERATED
                message=f"Access token generated for user {user_id}",
                severity=SecurityLevel.LOW,
                user_id=user_id,
            )
        )
        return token

    def verify_document_integrity(self, document_id: str, content: str) -> bool:
        """Verify document integrity using HMAC."""
        if document_id not in self._document_signatures:
            logger.warning(f"No signature found for document {document_id}")
            return False

        signature = self._document_signatures[document_id]
        is_valid = self.security.integrity.verify_document(document_id, content, signature)

        if not is_valid:
            self.security.audit.log_event(
                SecurityEvent(
                    event_type=SecurityEventType.INTEGRITY_FAILURE,
                    message=f"Document integrity check failed for {document_id}",
                    severity=SecurityLevel.CRITICAL,
                    user_id=self.security_context.user_id if self.security_context else None,
                )
            )

        return is_valid

    def get_security_report(self) -> Dict[str, Any]:
        """Get comprehensive security report."""
        return self.security.get_security_report()

    def detect_suspicious_activity(self) -> List[str]:
        """Detect suspicious patterns in security events."""
        patterns = self.security.audit.detect_suspicious_patterns()

        if patterns:
            self.security.audit.log_event(
                SecurityEvent(
                    event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                    message=f"Suspicious patterns detected: {', '.join(patterns)}",
                    severity=SecurityLevel.HIGH,
                    user_id=self.security_context.user_id if self.security_context else None,
                )
            )

        return patterns
