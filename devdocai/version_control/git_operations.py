"""
Git Operations Module

Low-level Git operations for repository management.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path

from git import Repo

logger = logging.getLogger(__name__)


class GitOperations:
    """
    Provides low-level Git operations for repository management.
    """
    
    def __init__(self, repo: Repo):
        """
        Initialize GitOperations.
        
        Args:
            repo: GitPython Repo instance
        """
        self.repo = repo
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current repository status.
        
        Returns:
            Dictionary containing repository status
        """
        status = {
            'branch': self.repo.active_branch.name if not self.repo.head.is_detached else 'detached',
            'commit': self.repo.head.commit.hexsha if self.repo.head.is_valid() else None,
            'is_dirty': self.repo.is_dirty(),
            'untracked_files': self.repo.untracked_files,
            'modified_files': [],
            'staged_files': [],
            'remote': None,
            'ahead': 0,
            'behind': 0,
        }
        
        # Get modified files
        for item in self.repo.index.diff(None):
            status['modified_files'].append(item.a_path)
        
        # Get staged files
        if self.repo.head.is_valid():
            for item in self.repo.index.diff('HEAD'):
                status['staged_files'].append(item.a_path)
        
        # Get remote information
        try:
            if self.repo.remotes:
                remote = self.repo.remotes.origin
                status['remote'] = remote.url
                
                # Get ahead/behind counts
                if not self.repo.head.is_detached:
                    branch = self.repo.active_branch
                    tracking = branch.tracking_branch()
                    if tracking:
                        commits_ahead = list(self.repo.iter_commits(f'{tracking}..{branch}'))
                        commits_behind = list(self.repo.iter_commits(f'{branch}..{tracking}'))
                        status['ahead'] = len(commits_ahead)
                        status['behind'] = len(commits_behind)
        except Exception as e:
            logger.warning(f"Failed to get remote information: {e}")
        
        return status
    
    def get_file_history(self, 
                        file_path: str, 
                        limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get commit history for a specific file.
        
        Args:
            file_path: Path to file
            limit: Maximum number of commits to return
            
        Returns:
            List of commit information
        """
        history = []
        
        # Get relative path
        doc_path = Path(file_path)
        if doc_path.is_absolute():
            try:
                rel_path = str(doc_path.relative_to(self.repo.working_dir))
            except ValueError:
                logger.error(f"File {file_path} is not in repository")
                return history
        else:
            rel_path = str(doc_path)
        
        try:
            # Get commits for this file
            commits = list(self.repo.iter_commits(paths=rel_path, max_count=limit))
            
            for commit in commits:
                commit_info = {
                    'hash': commit.hexsha,
                    'short_hash': commit.hexsha[:8],
                    'message': commit.message.strip(),
                    'author': str(commit.author),
                    'author_email': commit.author.email,
                    'date': datetime.fromtimestamp(commit.committed_date).isoformat(),
                    'stats': {},
                }
                
                # Get file stats for this commit
                if rel_path in commit.stats.files:
                    commit_info['stats'] = commit.stats.files[rel_path]
                
                history.append(commit_info)
        
        except Exception as e:
            logger.error(f"Failed to get history for {file_path}: {e}")
        
        return history
    
    def get_diff(self, 
                file_path: str,
                from_commit: Optional[str] = None,
                to_commit: Optional[str] = None) -> str:
        """
        Get diff for a file between commits.
        
        Args:
            file_path: Path to file
            from_commit: Starting commit (default: HEAD~1)
            to_commit: Ending commit (default: HEAD)
            
        Returns:
            Diff string
        """
        # Get relative path
        doc_path = Path(file_path)
        if doc_path.is_absolute():
            try:
                rel_path = str(doc_path.relative_to(self.repo.working_dir))
            except ValueError:
                return f"Error: File {file_path} is not in repository"
        else:
            rel_path = str(doc_path)
        
        try:
            # Set default commits
            if not from_commit:
                from_commit = 'HEAD~1' if self.repo.head.is_valid() else None
            if not to_commit:
                to_commit = 'HEAD' if self.repo.head.is_valid() else None
            
            if not from_commit or not to_commit:
                return "Error: Repository has no commits"
            
            # Get diff
            from_commit_obj = self.repo.commit(from_commit)
            to_commit_obj = self.repo.commit(to_commit)
            
            diffs = from_commit_obj.diff(to_commit_obj, paths=rel_path, create_patch=True)
            
            if diffs:
                return diffs[0].diff.decode('utf-8', errors='ignore')
            else:
                return f"No changes in {rel_path} between {from_commit} and {to_commit}"
        
        except Exception as e:
            return f"Error getting diff: {e}"
    
    def checkout_file(self, file_path: str, commit_hash: str) -> bool:
        """
        Checkout a file from a specific commit.
        
        Args:
            file_path: Path to file
            commit_hash: Commit to checkout from
            
        Returns:
            True if successful
        """
        # Get relative path
        doc_path = Path(file_path)
        if doc_path.is_absolute():
            try:
                rel_path = str(doc_path.relative_to(self.repo.working_dir))
            except ValueError:
                logger.error(f"File {file_path} is not in repository")
                return False
        else:
            rel_path = str(doc_path)
        
        try:
            # Get commit
            commit = self.repo.commit(commit_hash)
            
            # Checkout file from commit
            self.repo.odb.stream(commit.tree[rel_path].binsha).read()
            self.repo.index.checkout([rel_path], force=True)
            
            logger.info(f"Checked out {rel_path} from {commit_hash}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to checkout {file_path} from {commit_hash}: {e}")
            return False
    
    def get_branches(self) -> List[str]:
        """
        Get list of all branches.
        
        Returns:
            List of branch names
        """
        return [branch.name for branch in self.repo.branches]
    
    def get_tags(self) -> List[Dict[str, Any]]:
        """
        Get list of all tags.
        
        Returns:
            List of tag information
        """
        tags = []
        
        for tag in self.repo.tags:
            tag_info = {
                'name': tag.name,
                'commit': tag.commit.hexsha,
                'message': tag.tag.message if hasattr(tag.tag, 'message') else None,
                'tagger': str(tag.tag.tagger) if hasattr(tag.tag, 'tagger') else None,
                'date': None,
            }
            
            if hasattr(tag.tag, 'tagged_date'):
                tag_info['date'] = datetime.fromtimestamp(tag.tag.tagged_date).isoformat()
            
            tags.append(tag_info)
        
        return tags
    
    def get_remote_branches(self) -> List[str]:
        """
        Get list of remote branches.
        
        Returns:
            List of remote branch names
        """
        remote_branches = []
        
        try:
            for remote in self.repo.remotes:
                for ref in remote.refs:
                    remote_branches.append(f"{remote.name}/{ref.remote_head}")
        except Exception as e:
            logger.warning(f"Failed to get remote branches: {e}")
        
        return remote_branches
    
    def fetch(self, remote: str = 'origin') -> bool:
        """
        Fetch from remote repository.
        
        Args:
            remote: Remote name
            
        Returns:
            True if successful
        """
        try:
            if remote in [r.name for r in self.repo.remotes]:
                self.repo.remotes[remote].fetch()
                logger.info(f"Fetched from {remote}")
                return True
            else:
                logger.error(f"Remote {remote} not found")
                return False
        except Exception as e:
            logger.error(f"Failed to fetch from {remote}: {e}")
            return False
    
    def get_commit_info(self, commit_hash: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a commit.
        
        Args:
            commit_hash: Commit hash
            
        Returns:
            Commit information or None
        """
        try:
            commit = self.repo.commit(commit_hash)
            
            return {
                'hash': commit.hexsha,
                'short_hash': commit.hexsha[:8],
                'message': commit.message.strip(),
                'author': str(commit.author),
                'author_email': commit.author.email,
                'committer': str(commit.committer),
                'committer_email': commit.committer.email,
                'authored_date': datetime.fromtimestamp(commit.authored_date).isoformat(),
                'committed_date': datetime.fromtimestamp(commit.committed_date).isoformat(),
                'parents': [p.hexsha for p in commit.parents],
                'files_changed': list(commit.stats.files.keys()),
                'stats': {
                    'total': commit.stats.total,
                    'files': len(commit.stats.files),
                },
            }
        except Exception as e:
            logger.error(f"Failed to get commit info for {commit_hash}: {e}")
            return None
    
    def __repr__(self) -> str:
        """String representation."""
        return f"GitOperations(repo='{self.repo.working_dir}')"