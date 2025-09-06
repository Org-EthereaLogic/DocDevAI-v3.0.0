"""
Message Generator Module

Auto-generates commit messages based on document changes.
"""

import re
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

from git import Repo

logger = logging.getLogger(__name__)


class MessageGenerator:
    """
    Generates meaningful commit messages based on document changes.
    """
    
    def __init__(self, repo: Repo):
        """
        Initialize MessageGenerator.
        
        Args:
            repo: GitPython Repo instance
        """
        self.repo = repo
        
        # Message templates based on change patterns
        self.templates = {
            'addition': 'Add {document_type} {document_name}',
            'deletion': 'Remove {document_type} {document_name}',
            'minor_update': 'Update {document_name}: minor changes',
            'major_update': 'Refactor {document_name}: major changes',
            'structural': 'Restructure {document_name}',
            'documentation': 'Update documentation in {document_name}',
            'typo': 'Fix typos in {document_name}',
            'formatting': 'Format {document_name}',
            'security': 'Security update in {document_name}',
            'performance': 'Optimize {document_name}',
            'bugfix': 'Fix issue in {document_name}',
            'feature': 'Add feature to {document_name}',
        }
        
        # Keywords for categorization
        self.keywords = {
            'security': ['security', 'vulnerability', 'auth', 'encrypt', 'password'],
            'performance': ['optimize', 'performance', 'speed', 'cache', 'efficient'],
            'bugfix': ['fix', 'bug', 'issue', 'error', 'problem', 'resolve'],
            'feature': ['add', 'new', 'feature', 'implement', 'introduce'],
            'documentation': ['doc', 'readme', 'comment', 'description', 'explain'],
            'formatting': ['format', 'style', 'lint', 'prettier', 'black'],
        }
    
    def generate_message(self, document_path: str) -> str:
        """
        Generate commit message for a document.
        
        Args:
            document_path: Path to document
            
        Returns:
            Generated commit message
        """
        doc_path = Path(document_path)
        
        # Get relative path
        if doc_path.is_absolute():
            try:
                rel_path = str(doc_path.relative_to(self.repo.working_dir))
            except ValueError:
                rel_path = str(doc_path)
        else:
            rel_path = str(doc_path)
        
        # Check file status
        if rel_path in self.repo.untracked_files:
            return self._generate_addition_message(doc_path)
        
        # Check if file was deleted
        if not (Path(self.repo.working_dir) / rel_path).exists():
            return self._generate_deletion_message(doc_path)
        
        # Analyze changes for existing file
        change_analysis = self._analyze_changes(rel_path)
        
        # Generate message based on analysis
        return self._generate_update_message(doc_path, change_analysis)
    
    def _generate_addition_message(self, doc_path: Path) -> str:
        """
        Generate message for new file.
        
        Args:
            doc_path: Path to document
            
        Returns:
            Commit message
        """
        doc_type = self._get_document_type(doc_path)
        doc_name = doc_path.stem
        
        return self.templates['addition'].format(
            document_type=doc_type,
            document_name=doc_name
        )
    
    def _generate_deletion_message(self, doc_path: Path) -> str:
        """
        Generate message for deleted file.
        
        Args:
            doc_path: Path to document
            
        Returns:
            Commit message
        """
        doc_type = self._get_document_type(doc_path)
        doc_name = doc_path.stem
        
        return self.templates['deletion'].format(
            document_type=doc_type,
            document_name=doc_name
        )
    
    def _generate_update_message(self, 
                                doc_path: Path, 
                                analysis: Dict[str, Any]) -> str:
        """
        Generate message for updated file.
        
        Args:
            doc_path: Path to document
            analysis: Change analysis
            
        Returns:
            Commit message
        """
        doc_name = doc_path.name
        
        # Determine message type based on analysis
        message_type = self._determine_message_type(analysis)
        
        # Get template
        template = self.templates.get(message_type, 'Update {document_name}')
        
        # Generate message
        message = template.format(document_name=doc_name)
        
        # Add details if significant changes
        if analysis.get('lines_changed', 0) > 50:
            details = self._generate_change_details(analysis)
            if details:
                message += f": {details}"
        
        return message
    
    def _analyze_changes(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze changes in a file.
        
        Args:
            file_path: Relative path to file
            
        Returns:
            Change analysis
        """
        analysis = {
            'lines_added': 0,
            'lines_removed': 0,
            'lines_changed': 0,
            'is_structural': False,
            'categories': [],
            'change_ratio': 0.0,
        }
        
        try:
            # Get diff
            diff_index = self.repo.head.commit.diff(None, paths=file_path, create_patch=True)
            
            for diff_item in diff_index:
                if diff_item.a_path == file_path or diff_item.b_path == file_path:
                    diff_text = diff_item.diff.decode('utf-8', errors='ignore')
                    
                    # Analyze diff content
                    for line in diff_text.splitlines():
                        if line.startswith('+') and not line.startswith('+++'):
                            analysis['lines_added'] += 1
                            # Check for keywords
                            self._check_keywords(line[1:], analysis)
                        elif line.startswith('-') and not line.startswith('---'):
                            analysis['lines_removed'] += 1
                        
                        # Check for structural changes
                        if self._is_structural_change(line):
                            analysis['is_structural'] = True
                    
                    # Calculate total changes
                    analysis['lines_changed'] = (
                        analysis['lines_added'] + analysis['lines_removed']
                    )
                    
                    # Calculate change ratio
                    try:
                        total_lines = len(
                            Path(self.repo.working_dir, file_path).read_text().splitlines()
                        )
                        analysis['change_ratio'] = analysis['lines_changed'] / max(total_lines, 1)
                    except:
                        pass
                    
                    break
        
        except Exception as e:
            logger.warning(f"Failed to analyze changes: {e}")
        
        return analysis
    
    def _check_keywords(self, line: str, analysis: Dict[str, Any]):
        """
        Check line for categorization keywords.
        
        Args:
            line: Line content
            analysis: Analysis dictionary to update
        """
        line_lower = line.lower()
        
        for category, keywords in self.keywords.items():
            if any(keyword in line_lower for keyword in keywords):
                if category not in analysis['categories']:
                    analysis['categories'].append(category)
    
    def _is_structural_change(self, line: str) -> bool:
        """
        Check if line represents a structural change.
        
        Args:
            line: Diff line
            
        Returns:
            True if structural change
        """
        if not line.startswith(('+', '-')):
            return False
        
        content = line[1:].strip()
        
        # Patterns indicating structural changes
        patterns = [
            r'^(class|def|function|interface|struct)\s+\w+',
            r'^#\s+\w+',  # Markdown headers
            r'^##\s+\w+',
            r'^```',  # Code blocks
        ]
        
        return any(re.match(pattern, content) for pattern in patterns)
    
    def _determine_message_type(self, analysis: Dict[str, Any]) -> str:
        """
        Determine the type of commit message based on analysis.
        
        Args:
            analysis: Change analysis
            
        Returns:
            Message type key
        """
        # Check categories first
        if 'security' in analysis['categories']:
            return 'security'
        elif 'performance' in analysis['categories']:
            return 'performance'
        elif 'bugfix' in analysis['categories']:
            return 'bugfix'
        elif 'feature' in analysis['categories']:
            return 'feature'
        elif 'documentation' in analysis['categories']:
            return 'documentation'
        elif 'formatting' in analysis['categories']:
            return 'formatting'
        
        # Check structural changes
        if analysis['is_structural']:
            return 'structural'
        
        # Check change ratio
        if analysis['change_ratio'] > 0.3:
            return 'major_update'
        elif analysis['lines_changed'] < 10:
            # Check if mostly typos
            return 'typo' if analysis['lines_changed'] < 5 else 'minor_update'
        else:
            return 'minor_update'
    
    def _generate_change_details(self, analysis: Dict[str, Any]) -> str:
        """
        Generate change details for commit message.
        
        Args:
            analysis: Change analysis
            
        Returns:
            Details string
        """
        details = []
        
        if analysis['lines_added']:
            details.append(f"+{analysis['lines_added']} lines")
        if analysis['lines_removed']:
            details.append(f"-{analysis['lines_removed']} lines")
        
        if analysis['categories']:
            categories = ', '.join(analysis['categories'][:2])
            details.append(categories)
        
        return ', '.join(details)
    
    def _get_document_type(self, doc_path: Path) -> str:
        """
        Determine document type from file extension.
        
        Args:
            doc_path: Path to document
            
        Returns:
            Document type string
        """
        extension_map = {
            '.md': 'documentation',
            '.rst': 'documentation',
            '.txt': 'text file',
            '.py': 'Python module',
            '.js': 'JavaScript file',
            '.ts': 'TypeScript file',
            '.java': 'Java class',
            '.cpp': 'C++ file',
            '.c': 'C file',
            '.h': 'header file',
            '.yml': 'YAML config',
            '.yaml': 'YAML config',
            '.json': 'JSON file',
            '.xml': 'XML file',
            '.html': 'HTML file',
            '.css': 'stylesheet',
            '.scss': 'SCSS stylesheet',
            '.sh': 'shell script',
            '.bat': 'batch file',
            '.sql': 'SQL file',
            '.dockerfile': 'Dockerfile',
            '.gitignore': 'gitignore',
        }
        
        suffix = doc_path.suffix.lower()
        return extension_map.get(suffix, 'file')
    
    def generate_batch_message(self, document_paths: List[str]) -> str:
        """
        Generate commit message for multiple documents.
        
        Args:
            document_paths: List of document paths
            
        Returns:
            Batch commit message
        """
        if not document_paths:
            return "Empty commit"
        
        if len(document_paths) == 1:
            return self.generate_message(document_paths[0])
        
        # Analyze all changes
        categories = set()
        total_added = 0
        total_removed = 0
        file_types = set()
        
        for doc_path in document_paths:
            doc = Path(doc_path)
            file_types.add(self._get_document_type(doc))
            
            if doc.exists():
                analysis = self._analyze_changes(str(doc))
                total_added += analysis['lines_added']
                total_removed += analysis['lines_removed']
                categories.update(analysis['categories'])
        
        # Generate message
        if len(file_types) == 1:
            file_type = list(file_types)[0]
            message = f"Update {len(document_paths)} {file_type}s"
        else:
            message = f"Update {len(document_paths)} files"
        
        # Add category if consistent
        if len(categories) == 1:
            category = list(categories)[0]
            message = f"{category.capitalize()}: {message}"
        
        # Add statistics
        if total_added or total_removed:
            stats = []
            if total_added:
                stats.append(f"+{total_added}")
            if total_removed:
                stats.append(f"-{total_removed}")
            message += f" ({', '.join(stats)})"
        
        return message
    
    def __repr__(self) -> str:
        """String representation."""
        return f"MessageGenerator(repo='{self.repo.working_dir}')"