"""
Change Tracker Module

Tracks document changes for impact analysis.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from difflib import unified_diff

from git import Repo

logger = logging.getLogger(__name__)


class ChangeTracker:
    """
    Tracks and analyzes document changes in Git repository.
    """
    
    def __init__(self, repo: Repo):
        """
        Initialize ChangeTracker.
        
        Args:
            repo: GitPython Repo instance
        """
        self.repo = repo
    
    def track_changes(self, document_path: str) -> Dict[str, Any]:
        """
        Track document changes for impact analysis.
        
        Args:
            document_path: Path to document file
            
        Returns:
            Dictionary containing change analysis
        """
        doc_path = Path(document_path)
        
        # Ensure path is relative to repo
        if doc_path.is_absolute():
            try:
                rel_path = str(doc_path.relative_to(self.repo.working_dir))
            except ValueError:
                raise ValueError(f"Document {document_path} is not in repository")
        else:
            rel_path = str(doc_path)
        
        # Initialize change tracking
        changes = {
            'document': rel_path,
            'status': 'unknown',
            'lines_added': 0,
            'lines_removed': 0,
            'lines_modified': 0,
            'total_lines': 0,
            'sections_affected': [],
            'structural_changes': False,
            'change_type': None,
            'hunks': []
        }
        
        # Check if file exists
        full_path = Path(self.repo.working_dir) / rel_path
        if not full_path.exists():
            changes['status'] = 'deleted'
            changes['change_type'] = 'deletion'
            return changes
        
        # Get file status
        if rel_path in self.repo.untracked_files:
            changes['status'] = 'untracked'
            changes['change_type'] = 'addition'
            changes['lines_added'] = len(full_path.read_text().splitlines())
            changes['total_lines'] = changes['lines_added']
            return changes
        
        # Get diff for tracked files
        try:
            # Check for staged changes
            staged_diff = self.repo.index.diff('HEAD', paths=rel_path)
            # Check for unstaged changes
            unstaged_diff = self.repo.index.diff(None, paths=rel_path)
            
            if staged_diff or unstaged_diff:
                changes['status'] = 'modified'
                changes['change_type'] = 'modification'
                
                # Analyze the diff
                diff_data = self._analyze_diff(rel_path)
                changes.update(diff_data)
                
                # Detect structural changes
                changes['structural_changes'] = self._detect_structural_changes(
                    changes['hunks']
                )
                
                # Extract affected sections
                changes['sections_affected'] = self._extract_affected_sections(
                    full_path, changes['hunks']
                )
            else:
                changes['status'] = 'unchanged'
                changes['change_type'] = None
            
            # Get total lines
            changes['total_lines'] = len(full_path.read_text().splitlines())
            
        except Exception as e:
            logger.error(f"Failed to track changes for {document_path}: {e}")
            changes['status'] = 'error'
            changes['error'] = str(e)
        
        return changes
    
    def _analyze_diff(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze diff for a file.
        
        Args:
            file_path: Relative path to file
            
        Returns:
            Diff analysis
        """
        analysis = {
            'lines_added': 0,
            'lines_removed': 0,
            'lines_modified': 0,
            'hunks': []
        }
        
        try:
            # Get the diff
            diff_index = self.repo.head.commit.diff(None, paths=file_path, create_patch=True)
            
            for diff_item in diff_index:
                if diff_item.a_path == file_path or diff_item.b_path == file_path:
                    diff_text = diff_item.diff.decode('utf-8', errors='ignore')
                    
                    # Parse diff hunks
                    hunks = self._parse_diff_hunks(diff_text)
                    analysis['hunks'] = hunks
                    
                    # Count changes
                    for hunk in hunks:
                        analysis['lines_added'] += hunk['added']
                        analysis['lines_removed'] += hunk['removed']
                    
                    # Estimate modified lines (overlap of adds/removes)
                    analysis['lines_modified'] = min(
                        analysis['lines_added'], 
                        analysis['lines_removed']
                    )
                    
                    break
        
        except Exception as e:
            logger.warning(f"Failed to analyze diff for {file_path}: {e}")
        
        return analysis
    
    def _parse_diff_hunks(self, diff_text: str) -> List[Dict[str, Any]]:
        """
        Parse diff text into hunks.
        
        Args:
            diff_text: Git diff text
            
        Returns:
            List of hunk dictionaries
        """
        hunks = []
        current_hunk = None
        
        for line in diff_text.splitlines():
            # Hunk header
            if line.startswith('@@'):
                if current_hunk:
                    hunks.append(current_hunk)
                
                # Parse hunk header
                match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)', line)
                if match:
                    current_hunk = {
                        'old_start': int(match.group(1)),
                        'old_lines': int(match.group(2) or 1),
                        'new_start': int(match.group(3)),
                        'new_lines': int(match.group(4) or 1),
                        'context': match.group(5).strip(),
                        'added': 0,
                        'removed': 0,
                        'content': []
                    }
            
            elif current_hunk:
                current_hunk['content'].append(line)
                if line.startswith('+') and not line.startswith('+++'):
                    current_hunk['added'] += 1
                elif line.startswith('-') and not line.startswith('---'):
                    current_hunk['removed'] += 1
        
        if current_hunk:
            hunks.append(current_hunk)
        
        return hunks
    
    def _detect_structural_changes(self, hunks: List[Dict[str, Any]]) -> bool:
        """
        Detect if changes are structural (major refactoring).
        
        Args:
            hunks: List of diff hunks
            
        Returns:
            True if structural changes detected
        """
        # Patterns that indicate structural changes
        structural_patterns = [
            r'class\s+\w+',           # Class definitions
            r'def\s+\w+',             # Function definitions
            r'interface\s+\w+',       # Interface definitions
            r'struct\s+\w+',          # Struct definitions
            r'#\s+\w+',              # Markdown headers
            r'##\s+\w+',             # Markdown subheaders
            r'```\w*',               # Code blocks
        ]
        
        for hunk in hunks:
            for line in hunk.get('content', []):
                if line.startswith(('+', '-')):
                    content = line[1:].strip()
                    for pattern in structural_patterns:
                        if re.search(pattern, content):
                            return True
        
        return False
    
    def _extract_affected_sections(self, 
                                  file_path: Path, 
                                  hunks: List[Dict[str, Any]]) -> List[str]:
        """
        Extract affected sections from document.
        
        Args:
            file_path: Path to file
            hunks: List of diff hunks
            
        Returns:
            List of affected section names
        """
        sections = []
        
        try:
            content = file_path.read_text()
            lines = content.splitlines()
            
            # Detect document type
            if file_path.suffix == '.md':
                sections = self._extract_markdown_sections(lines, hunks)
            elif file_path.suffix in ['.py', '.js', '.ts', '.java']:
                sections = self._extract_code_sections(lines, hunks)
            else:
                # Generic section extraction
                for hunk in hunks:
                    if hunk.get('context'):
                        sections.append(hunk['context'])
        
        except Exception as e:
            logger.warning(f"Failed to extract sections: {e}")
        
        return list(set(sections))  # Remove duplicates
    
    def _extract_markdown_sections(self, 
                                  lines: List[str], 
                                  hunks: List[Dict[str, Any]]) -> List[str]:
        """
        Extract affected sections from Markdown document.
        
        Args:
            lines: Document lines
            hunks: Diff hunks
            
        Returns:
            List of section names
        """
        sections = []
        
        # Build section map
        section_map = {}
        current_section = "Introduction"
        
        for i, line in enumerate(lines, 1):
            if line.startswith('#'):
                current_section = line.lstrip('#').strip()
            section_map[i] = current_section
        
        # Find affected sections
        for hunk in hunks:
            start = hunk.get('new_start', 0)
            end = start + hunk.get('new_lines', 0)
            
            for line_num in range(start, min(end + 1, len(lines) + 1)):
                if line_num in section_map:
                    sections.append(section_map[line_num])
        
        return sections
    
    def _extract_code_sections(self, 
                              lines: List[str], 
                              hunks: List[Dict[str, Any]]) -> List[str]:
        """
        Extract affected sections from code file.
        
        Args:
            lines: Document lines
            hunks: Diff hunks
            
        Returns:
            List of function/class names
        """
        sections = []
        
        # Build function/class map
        section_map = {}
        current_section = "global"
        
        for i, line in enumerate(lines, 1):
            # Python
            if match := re.match(r'\s*(class|def)\s+(\w+)', line):
                current_section = f"{match.group(1)} {match.group(2)}"
            # JavaScript/TypeScript
            elif match := re.match(r'\s*(function|class)\s+(\w+)', line):
                current_section = f"{match.group(1)} {match.group(2)}"
            # Java
            elif match := re.match(r'\s*(public|private|protected)?\s*(class|interface)\s+(\w+)', line):
                current_section = f"{match.group(2)} {match.group(3)}"
            
            section_map[i] = current_section
        
        # Find affected sections
        for hunk in hunks:
            start = hunk.get('new_start', 0)
            end = start + hunk.get('new_lines', 0)
            
            for line_num in range(start, min(end + 1, len(lines) + 1)):
                if line_num in section_map:
                    sections.append(section_map[line_num])
        
        return sections
    
    def get_change_summary(self, document_path: str) -> str:
        """
        Get a human-readable change summary.
        
        Args:
            document_path: Path to document
            
        Returns:
            Change summary string
        """
        changes = self.track_changes(document_path)
        
        if changes['status'] == 'unchanged':
            return f"{document_path}: No changes"
        elif changes['status'] == 'untracked':
            return f"{document_path}: New file ({changes['lines_added']} lines)"
        elif changes['status'] == 'deleted':
            return f"{document_path}: Deleted"
        elif changes['status'] == 'modified':
            summary = f"{document_path}: "
            parts = []
            
            if changes['lines_added']:
                parts.append(f"+{changes['lines_added']}")
            if changes['lines_removed']:
                parts.append(f"-{changes['lines_removed']}")
            
            summary += ', '.join(parts)
            
            if changes['structural_changes']:
                summary += " (structural changes)"
            
            if changes['sections_affected']:
                sections = ', '.join(changes['sections_affected'][:3])
                if len(changes['sections_affected']) > 3:
                    sections += f" +{len(changes['sections_affected']) - 3} more"
                summary += f" in {sections}"
            
            return summary
        else:
            return f"{document_path}: {changes['status']}"
    
    def __repr__(self) -> str:
        """String representation."""
        return f"ChangeTracker(repo='{self.repo.working_dir}')"