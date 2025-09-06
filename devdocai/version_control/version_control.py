"""
Version Control Integration Module

Provides native Git integration for document versioning and tracking.
"""

import os
import logging
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime
from pathlib import Path

try:
    import git
    from git import Repo, InvalidGitRepositoryError
except ImportError:
    raise ImportError("GitPython is required. Install with: pip install gitpython")

from .commit_manager import CommitManager
from .change_tracker import ChangeTracker
from .message_generator import MessageGenerator
from .git_operations import GitOperations

# Configure logging
logger = logging.getLogger(__name__)


class VersionControlIntegration:
    """
    Main class for version control integration with Git repositories.
    
    This class provides comprehensive Git integration for document versioning,
    including automatic commit tracking, change analysis, and version tagging.
    """
    
    def __init__(self, repo_path: str = '.', config: Optional[Dict[str, Any]] = None):
        """
        Initialize Version Control Integration.
        
        Args:
            repo_path: Path to Git repository (default: current directory)
            config: Optional configuration dictionary
        """
        self.repo_path = Path(repo_path).resolve()
        self.config = config or self._get_default_config()
        
        # Initialize Git repository
        try:
            self.repo = Repo(self.repo_path)
            if self.repo.bare:
                raise ValueError(f"Cannot work with bare repository at {repo_path}")
        except InvalidGitRepositoryError:
            if self.config.get('auto_init', False):
                logger.info(f"Initializing new Git repository at {self.repo_path}")
                self.repo = Repo.init(self.repo_path)
            else:
                raise ValueError(f"Not a Git repository: {repo_path}")
        
        # Initialize components
        self.commit_manager = CommitManager(self.repo)
        self.change_tracker = ChangeTracker(self.repo)
        self.message_generator = MessageGenerator(self.repo)
        self.git_ops = GitOperations(self.repo)
        
        # Integration with M005 TrackingMatrix (if available)
        self.tracking_matrix = self._init_tracking_matrix()
        
        logger.info(f"Version Control Integration initialized for {self.repo_path}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            'auto_init': False,
            'auto_commit': True,
            'commit_prefix': '[DevDocAI]',
            'tag_prefix': 'v',
            'track_metadata': True,
            'major_version_threshold': 0.3,  # 30% change for major version
            'enable_hooks': True,
        }
    
    def _init_tracking_matrix(self) -> Optional[Any]:
        """Initialize TrackingMatrix integration if available."""
        try:
            # Try to import M005 TrackingMatrix
            from devdocai.quality.tracking_matrix import TrackingMatrix
            return TrackingMatrix()
        except ImportError:
            logger.debug("TrackingMatrix (M005) not available, continuing without integration")
            return None
    
    def commit_document(self, 
                       document_path: str, 
                       message: Optional[str] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Commit document changes with metadata.
        
        Args:
            document_path: Path to document file
            message: Optional commit message (auto-generated if not provided)
            metadata: Optional metadata to include in commit
            
        Returns:
            Commit hash
        """
        # Ensure document exists
        doc_path = Path(document_path)
        if not doc_path.exists():
            raise FileNotFoundError(f"Document not found: {document_path}")
        
        # Generate commit message if not provided
        if not message:
            message = self.generate_commit_message(document_path)
        
        # Add DevDocAI prefix if configured
        if self.config.get('commit_prefix'):
            message = f"{self.config['commit_prefix']} {message}"
        
        # Prepare metadata
        full_metadata = {
            'timestamp': datetime.now().isoformat(),
            'document': str(doc_path.relative_to(self.repo_path)),
            'module': 'M012',
        }
        if metadata:
            full_metadata.update(metadata)
        
        # Commit through commit manager
        commit_hash = self.commit_manager.commit_document(
            document_path=str(doc_path),
            message=message,
            metadata=full_metadata
        )
        
        # Update tracking matrix if available
        if self.tracking_matrix:
            try:
                self.tracking_matrix.update_version(
                    document_id=str(doc_path.name),
                    version=commit_hash[:8],
                    metadata=full_metadata
                )
            except Exception as e:
                logger.warning(f"Failed to update tracking matrix: {e}")
        
        logger.info(f"Committed {document_path} with hash {commit_hash}")
        return commit_hash
    
    def track_changes(self, document_path: str) -> Dict[str, Any]:
        """
        Track document changes for impact analysis.
        
        Args:
            document_path: Path to document file
            
        Returns:
            Dictionary containing change analysis
        """
        return self.change_tracker.track_changes(document_path)
    
    def generate_commit_message(self, document_path: str) -> str:
        """
        Auto-generate commit message based on changes.
        
        Args:
            document_path: Path to document file
            
        Returns:
            Generated commit message
        """
        return self.message_generator.generate_message(document_path)
    
    def is_major_version(self, document_path: str) -> bool:
        """
        Determine if changes warrant a major version bump.
        
        Args:
            document_path: Path to document file
            
        Returns:
            True if major version bump is warranted
        """
        changes = self.track_changes(document_path)
        
        # Calculate change ratio
        total_lines = changes.get('total_lines', 1)
        changed_lines = changes.get('lines_added', 0) + changes.get('lines_removed', 0)
        change_ratio = changed_lines / max(total_lines, 1)
        
        # Check against threshold
        threshold = self.config.get('major_version_threshold', 0.3)
        is_major = change_ratio >= threshold
        
        # Also check for structural changes
        if changes.get('structural_changes'):
            is_major = True
        
        return is_major
    
    def tag_version(self, 
                   version: str, 
                   document_path: Optional[str] = None,
                   message: Optional[str] = None) -> str:
        """
        Tag current state with a version.
        
        Args:
            version: Version string (e.g., "2.0.0")
            document_path: Optional document path for document-specific version
            message: Optional tag message
            
        Returns:
            Tag name
        """
        prefix = self.config.get('tag_prefix', 'v')
        tag_name = f"{prefix}{version}"
        
        if document_path:
            # Document-specific tag
            doc_name = Path(document_path).stem
            tag_name = f"{tag_name}-{doc_name}"
        
        if not message:
            message = f"Release {version}"
            if document_path:
                message += f" for {Path(document_path).name}"
        
        # Create tag
        self.repo.create_tag(tag_name, message=message)
        
        logger.info(f"Created tag {tag_name}")
        return tag_name
    
    def get_document_history(self, 
                            document_path: str, 
                            limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get commit history for a specific document.
        
        Args:
            document_path: Path to document file
            limit: Maximum number of commits to return
            
        Returns:
            List of commit information dictionaries
        """
        return self.git_ops.get_file_history(document_path, limit)
    
    def get_repository_status(self) -> Dict[str, Any]:
        """
        Get current repository status.
        
        Returns:
            Dictionary containing repository status information
        """
        return self.git_ops.get_status()
    
    def rollback_document(self, document_path: str, commit_hash: str) -> bool:
        """
        Rollback a document to a specific commit.
        
        Args:
            document_path: Path to document file
            commit_hash: Commit hash to rollback to
            
        Returns:
            True if successful
        """
        return self.git_ops.checkout_file(document_path, commit_hash)
    
    def get_document_diff(self, 
                         document_path: str, 
                         from_commit: Optional[str] = None,
                         to_commit: Optional[str] = None) -> str:
        """
        Get diff for a document between commits.
        
        Args:
            document_path: Path to document file
            from_commit: Starting commit (default: HEAD~1)
            to_commit: Ending commit (default: HEAD)
            
        Returns:
            Diff string
        """
        return self.git_ops.get_diff(document_path, from_commit, to_commit)
    
    def analyze_impact(self, document_path: str) -> Dict[str, Any]:
        """
        Analyze the impact of document changes.
        
        Args:
            document_path: Path to document file
            
        Returns:
            Impact analysis dictionary
        """
        # Get change tracking
        changes = self.track_changes(document_path)
        
        # Determine impact level
        impact_level = 'low'
        if changes.get('lines_added', 0) + changes.get('lines_removed', 0) > 100:
            impact_level = 'high'
        elif changes.get('lines_added', 0) + changes.get('lines_removed', 0) > 20:
            impact_level = 'medium'
        
        # Build impact analysis
        impact = {
            'document': document_path,
            'impact_level': impact_level,
            'changes': changes,
            'is_major_version': self.is_major_version(document_path),
            'affected_sections': changes.get('affected_sections', []),
            'timestamp': datetime.now().isoformat(),
        }
        
        # Add related documents if tracking matrix is available
        if self.tracking_matrix:
            try:
                related = self.tracking_matrix.get_related_documents(
                    Path(document_path).name
                )
                impact['related_documents'] = related
            except Exception as e:
                logger.debug(f"Could not get related documents: {e}")
        
        return impact
    
    def __repr__(self) -> str:
        """String representation."""
        return f"VersionControlIntegration(repo='{self.repo_path}')"