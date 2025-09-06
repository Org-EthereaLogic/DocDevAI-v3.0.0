"""
Commit Manager Module

Handles document commit operations with metadata tracking.
"""

import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path

from git import Repo

logger = logging.getLogger(__name__)


class CommitManager:
    """
    Manages Git commit operations for documents with metadata.
    """
    
    def __init__(self, repo: Repo):
        """
        Initialize CommitManager.
        
        Args:
            repo: GitPython Repo instance
        """
        self.repo = repo
        self.metadata_file = Path(self.repo.working_dir) / '.devdocai' / 'commit_metadata.json'
        self._ensure_metadata_file()
    
    def _ensure_metadata_file(self):
        """Ensure metadata file exists."""
        self.metadata_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.metadata_file.exists():
            self.metadata_file.write_text('{}')
    
    def commit_document(self, 
                       document_path: str,
                       message: str,
                       metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Commit a document with metadata.
        
        Args:
            document_path: Path to document
            message: Commit message
            metadata: Optional metadata dictionary
            
        Returns:
            Commit hash
        """
        # Ensure path is relative to repo
        doc_path = Path(document_path)
        if doc_path.is_absolute():
            try:
                rel_path = doc_path.relative_to(self.repo.working_dir)
            except ValueError:
                raise ValueError(f"Document {document_path} is not in repository")
        else:
            rel_path = doc_path
        
        # Stage the document
        self.repo.index.add([str(rel_path)])
        
        # Add metadata if provided
        if metadata:
            self._store_metadata(str(rel_path), metadata)
            # Also stage metadata file
            metadata_rel = self.metadata_file.relative_to(self.repo.working_dir)
            self.repo.index.add([str(metadata_rel)])
        
        # Commit
        commit = self.repo.index.commit(message)
        
        logger.info(f"Committed {rel_path} with hash {commit.hexsha}")
        return commit.hexsha
    
    def _store_metadata(self, document_path: str, metadata: Dict[str, Any]):
        """
        Store metadata for a document commit.
        
        Args:
            document_path: Relative path to document
            metadata: Metadata to store
        """
        # Load existing metadata
        try:
            all_metadata = json.loads(self.metadata_file.read_text())
        except (json.JSONDecodeError, FileNotFoundError):
            all_metadata = {}
        
        # Initialize document metadata if not exists
        if document_path not in all_metadata:
            all_metadata[document_path] = []
        
        # Add new metadata entry
        metadata_entry = {
            'timestamp': datetime.now().isoformat(),
            'commit': self.repo.head.commit.hexsha if self.repo.head.is_valid() else None,
            **metadata
        }
        all_metadata[document_path].append(metadata_entry)
        
        # Limit history to last 100 entries per document
        all_metadata[document_path] = all_metadata[document_path][-100:]
        
        # Save metadata
        self.metadata_file.write_text(json.dumps(all_metadata, indent=2))
    
    def get_document_metadata(self, document_path: str) -> List[Dict[str, Any]]:
        """
        Get metadata history for a document.
        
        Args:
            document_path: Path to document
            
        Returns:
            List of metadata entries
        """
        try:
            all_metadata = json.loads(self.metadata_file.read_text())
            
            # Try both absolute and relative paths
            doc_path = Path(document_path)
            if doc_path.is_absolute():
                try:
                    rel_path = str(doc_path.relative_to(self.repo.working_dir))
                except ValueError:
                    rel_path = str(doc_path)
            else:
                rel_path = str(doc_path)
            
            return all_metadata.get(rel_path, [])
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def stage_documents(self, document_paths: List[str]) -> int:
        """
        Stage multiple documents for commit.
        
        Args:
            document_paths: List of document paths
            
        Returns:
            Number of documents staged
        """
        staged = 0
        for path in document_paths:
            try:
                doc_path = Path(path)
                if doc_path.is_absolute():
                    rel_path = doc_path.relative_to(self.repo.working_dir)
                else:
                    rel_path = doc_path
                
                if Path(self.repo.working_dir, rel_path).exists():
                    self.repo.index.add([str(rel_path)])
                    staged += 1
                else:
                    logger.warning(f"Document not found: {path}")
            except Exception as e:
                logger.error(f"Failed to stage {path}: {e}")
        
        return staged
    
    def commit_batch(self, 
                    document_paths: List[str],
                    message: str,
                    individual_metadata: Optional[Dict[str, Dict[str, Any]]] = None) -> str:
        """
        Commit multiple documents in a single commit.
        
        Args:
            document_paths: List of document paths
            message: Commit message
            individual_metadata: Optional per-document metadata
            
        Returns:
            Commit hash
        """
        # Stage all documents
        staged = self.stage_documents(document_paths)
        
        if staged == 0:
            raise ValueError("No documents staged for commit")
        
        # Store metadata for each document
        if individual_metadata:
            for doc_path, metadata in individual_metadata.items():
                self._store_metadata(doc_path, metadata)
        
        # Stage metadata file if it was updated
        if individual_metadata:
            metadata_rel = self.metadata_file.relative_to(self.repo.working_dir)
            self.repo.index.add([str(metadata_rel)])
        
        # Commit
        commit = self.repo.index.commit(message)
        
        logger.info(f"Batch committed {staged} documents with hash {commit.hexsha}")
        return commit.hexsha
    
    def get_last_commit_for_document(self, document_path: str) -> Optional[Dict[str, Any]]:
        """
        Get the last commit information for a document.
        
        Args:
            document_path: Path to document
            
        Returns:
            Commit information or None
        """
        doc_path = Path(document_path)
        if doc_path.is_absolute():
            try:
                rel_path = str(doc_path.relative_to(self.repo.working_dir))
            except ValueError:
                return None
        else:
            rel_path = str(doc_path)
        
        try:
            # Get commits that touched this file
            commits = list(self.repo.iter_commits(paths=rel_path, max_count=1))
            
            if commits:
                commit = commits[0]
                return {
                    'hash': commit.hexsha,
                    'message': commit.message.strip(),
                    'author': str(commit.author),
                    'timestamp': datetime.fromtimestamp(commit.committed_date).isoformat(),
                    'stats': commit.stats.files.get(rel_path, {})
                }
        except Exception as e:
            logger.error(f"Failed to get last commit for {document_path}: {e}")
        
        return None
    
    def has_uncommitted_changes(self, document_path: Optional[str] = None) -> bool:
        """
        Check if there are uncommitted changes.
        
        Args:
            document_path: Optional specific document to check
            
        Returns:
            True if there are uncommitted changes
        """
        if document_path:
            doc_path = Path(document_path)
            if doc_path.is_absolute():
                try:
                    rel_path = str(doc_path.relative_to(self.repo.working_dir))
                except ValueError:
                    return False
            else:
                rel_path = str(doc_path)
            
            # Check if specific file has changes
            changed_files = [item.a_path for item in self.repo.index.diff(None)]
            staged_files = [item.a_path for item in self.repo.index.diff('HEAD')]
            
            return rel_path in changed_files or rel_path in staged_files
        else:
            # Check if any changes exist
            return self.repo.is_dirty()
    
    def __repr__(self) -> str:
        """String representation."""
        return f"CommitManager(repo='{self.repo.working_dir}')"