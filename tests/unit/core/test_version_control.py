"""
Comprehensive tests for M012 Version Control Integration Module

Tests all components: VersionControlIntegration, CommitManager, 
ChangeTracker, MessageGenerator, and GitOperations.

Coverage target: 85%+
"""

import os
import tempfile
import shutil
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import git

# Import the modules to test
from devdocai.version_control import (
    VersionControlIntegration,
    CommitManager,
    ChangeTracker,
    MessageGenerator,
    GitOperations
)


class TestVersionControlIntegration(unittest.TestCase):
    """Test VersionControlIntegration class."""
    
    def setUp(self):
        """Set up test repository."""
        self.test_dir = tempfile.mkdtemp()
        self.repo = git.Repo.init(self.test_dir)
        
        # Create initial commit
        test_file = Path(self.test_dir) / 'test.txt'
        test_file.write_text('Initial content')
        self.repo.index.add(['test.txt'])
        self.repo.index.commit('Initial commit')
        
        self.vc = VersionControlIntegration(self.test_dir)
    
    def tearDown(self):
        """Clean up test repository."""
        shutil.rmtree(self.test_dir)
    
    def test_initialization(self):
        """Test VersionControlIntegration initialization."""
        self.assertIsNotNone(self.vc)
        self.assertEqual(str(self.vc.repo_path), self.test_dir)
        self.assertIsNotNone(self.vc.commit_manager)
        self.assertIsNotNone(self.vc.change_tracker)
        self.assertIsNotNone(self.vc.message_generator)
        self.assertIsNotNone(self.vc.git_ops)
    
    def test_initialization_non_git_repo(self):
        """Test initialization with non-Git directory."""
        non_git_dir = tempfile.mkdtemp()
        try:
            with self.assertRaises(ValueError):
                VersionControlIntegration(non_git_dir)
        finally:
            shutil.rmtree(non_git_dir)
    
    def test_auto_init_repo(self):
        """Test auto-initialization of Git repository."""
        non_git_dir = tempfile.mkdtemp()
        try:
            config = {'auto_init': True}
            vc = VersionControlIntegration(non_git_dir, config)
            self.assertTrue(Path(non_git_dir, '.git').exists())
        finally:
            shutil.rmtree(non_git_dir)
    
    def test_commit_document(self):
        """Test committing a document."""
        # Create a new file
        doc_path = Path(self.test_dir) / 'document.md'
        doc_path.write_text('# Document\nContent here')
        
        # Commit the document
        commit_hash = self.vc.commit_document(
            str(doc_path),
            message='Add document',
            metadata={'author': 'test'}
        )
        
        self.assertIsNotNone(commit_hash)
        self.assertEqual(len(commit_hash), 40)  # SHA-1 hash length
        
        # Verify commit exists
        commit = self.repo.commit(commit_hash)
        self.assertIn('Add document', commit.message)
    
    def test_commit_document_auto_message(self):
        """Test committing with auto-generated message."""
        doc_path = Path(self.test_dir) / 'new_doc.md'
        doc_path.write_text('# New Document')
        
        commit_hash = self.vc.commit_document(str(doc_path))
        
        self.assertIsNotNone(commit_hash)
        commit = self.repo.commit(commit_hash)
        self.assertIn('new_doc', commit.message.lower())
    
    def test_track_changes(self):
        """Test tracking document changes."""
        doc_path = Path(self.test_dir) / 'test.txt'
        
        # Modify the file
        doc_path.write_text('Modified content\nNew line')
        
        changes = self.vc.track_changes(str(doc_path))
        
        self.assertEqual(changes['status'], 'modified')
        self.assertEqual(changes['change_type'], 'modification')
        self.assertGreater(changes['lines_added'], 0)
        self.assertGreater(changes['total_lines'], 0)
    
    def test_track_changes_new_file(self):
        """Test tracking changes for new file."""
        doc_path = Path(self.test_dir) / 'new.txt'
        doc_path.write_text('New file content')
        
        changes = self.vc.track_changes(str(doc_path))
        
        self.assertEqual(changes['status'], 'untracked')
        self.assertEqual(changes['change_type'], 'addition')
        self.assertEqual(changes['lines_added'], 1)
    
    def test_generate_commit_message(self):
        """Test automatic commit message generation."""
        doc_path = Path(self.test_dir) / 'readme.md'
        doc_path.write_text('# README\nProject documentation')
        
        message = self.vc.generate_commit_message(str(doc_path))
        
        self.assertIsNotNone(message)
        self.assertIn('readme', message.lower())
    
    def test_is_major_version(self):
        """Test major version detection."""
        doc_path = Path(self.test_dir) / 'test.txt'
        
        # Small change - not major
        doc_path.write_text('Initial content\nOne more line')
        is_major = self.vc.is_major_version(str(doc_path))
        self.assertFalse(is_major)
        
        # Large change - major
        large_content = '\n'.join(['Line ' + str(i) for i in range(100)])
        doc_path.write_text(large_content)
        
        # Mock track_changes to return large changes
        with patch.object(self.vc, 'track_changes') as mock_track:
            mock_track.return_value = {
                'lines_added': 100,
                'lines_removed': 2,
                'total_lines': 100,
                'structural_changes': True
            }
            is_major = self.vc.is_major_version(str(doc_path))
            self.assertTrue(is_major)
    
    def test_tag_version(self):
        """Test version tagging."""
        tag_name = self.vc.tag_version('1.0.0', message='Release 1.0.0')
        
        self.assertEqual(tag_name, 'v1.0.0')
        
        # Verify tag exists
        tags = [tag.name for tag in self.repo.tags]
        self.assertIn('v1.0.0', tags)
    
    def test_tag_version_with_document(self):
        """Test document-specific version tagging."""
        doc_path = Path(self.test_dir) / 'document.md'
        doc_path.write_text('Content')
        
        tag_name = self.vc.tag_version('2.0.0', str(doc_path))
        
        self.assertEqual(tag_name, 'v2.0.0-document')
        tags = [tag.name for tag in self.repo.tags]
        self.assertIn('v2.0.0-document', tags)
    
    def test_get_document_history(self):
        """Test getting document history."""
        doc_path = Path(self.test_dir) / 'test.txt'
        
        # Make some commits
        for i in range(3):
            doc_path.write_text(f'Content version {i}')
            self.repo.index.add(['test.txt'])
            self.repo.index.commit(f'Update {i}')
        
        history = self.vc.get_document_history(str(doc_path), limit=5)
        
        self.assertIsInstance(history, list)
        self.assertGreater(len(history), 0)
        self.assertIn('hash', history[0])
        self.assertIn('message', history[0])
        self.assertIn('author', history[0])
    
    def test_get_repository_status(self):
        """Test getting repository status."""
        status = self.vc.get_repository_status()
        
        self.assertIn('branch', status)
        self.assertIn('commit', status)
        self.assertIn('is_dirty', status)
        self.assertIn('untracked_files', status)
        self.assertIn('modified_files', status)
    
    def test_analyze_impact(self):
        """Test impact analysis."""
        doc_path = Path(self.test_dir) / 'test.txt'
        doc_path.write_text('Modified content')
        
        impact = self.vc.analyze_impact(str(doc_path))
        
        self.assertIn('impact_level', impact)
        self.assertIn('changes', impact)
        self.assertIn('is_major_version', impact)
        self.assertIn('timestamp', impact)


class TestCommitManager(unittest.TestCase):
    """Test CommitManager class."""
    
    def setUp(self):
        """Set up test repository."""
        self.test_dir = tempfile.mkdtemp()
        self.repo = git.Repo.init(self.test_dir)
        
        # Initial commit
        test_file = Path(self.test_dir) / 'init.txt'
        test_file.write_text('Initial')
        self.repo.index.add(['init.txt'])
        self.repo.index.commit('Initial')
        
        self.commit_manager = CommitManager(self.repo)
    
    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.test_dir)
    
    def test_commit_document(self):
        """Test committing a document."""
        doc_path = Path(self.test_dir) / 'doc.txt'
        doc_path.write_text('Document content')
        
        commit_hash = self.commit_manager.commit_document(
            str(doc_path),
            'Test commit',
            {'test': 'metadata'}
        )
        
        self.assertIsNotNone(commit_hash)
        self.assertEqual(len(commit_hash), 40)
    
    def test_stage_documents(self):
        """Test staging multiple documents."""
        # Create multiple files
        files = []
        for i in range(3):
            file_path = Path(self.test_dir) / f'file{i}.txt'
            file_path.write_text(f'Content {i}')
            files.append(str(file_path))
        
        staged = self.commit_manager.stage_documents(files)
        self.assertEqual(staged, 3)
    
    def test_commit_batch(self):
        """Test batch commit."""
        # Create files
        files = []
        for i in range(2):
            file_path = Path(self.test_dir) / f'batch{i}.txt'
            file_path.write_text(f'Batch content {i}')
            files.append(str(file_path))
        
        commit_hash = self.commit_manager.commit_batch(
            files,
            'Batch commit'
        )
        
        self.assertIsNotNone(commit_hash)
        
        # Verify files were committed
        commit = self.repo.commit(commit_hash)
        self.assertIn('Batch commit', commit.message)
    
    def test_get_last_commit_for_document(self):
        """Test getting last commit for a document."""
        doc_path = Path(self.test_dir) / 'tracked.txt'
        doc_path.write_text('Content')
        self.repo.index.add(['tracked.txt'])
        commit = self.repo.index.commit('Add tracked file')
        
        last_commit = self.commit_manager.get_last_commit_for_document(str(doc_path))
        
        self.assertIsNotNone(last_commit)
        self.assertEqual(last_commit['hash'], commit.hexsha)
        self.assertIn('Add tracked file', last_commit['message'])
    
    def test_has_uncommitted_changes(self):
        """Test checking for uncommitted changes."""
        # Initially clean
        self.assertFalse(self.commit_manager.has_uncommitted_changes())
        
        # Create uncommitted change
        doc_path = Path(self.test_dir) / 'init.txt'
        doc_path.write_text('Modified')
        
        self.assertTrue(self.commit_manager.has_uncommitted_changes())
        self.assertTrue(self.commit_manager.has_uncommitted_changes(str(doc_path)))


class TestChangeTracker(unittest.TestCase):
    """Test ChangeTracker class."""
    
    def setUp(self):
        """Set up test repository."""
        self.test_dir = tempfile.mkdtemp()
        self.repo = git.Repo.init(self.test_dir)
        
        # Create initial file
        self.test_file = Path(self.test_dir) / 'test.md'
        self.test_file.write_text('# Header\nContent')
        self.repo.index.add(['test.md'])
        self.repo.index.commit('Initial')
        
        self.change_tracker = ChangeTracker(self.repo)
    
    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.test_dir)
    
    def test_track_changes_modified(self):
        """Test tracking changes for modified file."""
        self.test_file.write_text('# Header\nModified content\nNew line')
        
        changes = self.change_tracker.track_changes(str(self.test_file))
        
        self.assertEqual(changes['status'], 'modified')
        self.assertEqual(changes['change_type'], 'modification')
        self.assertGreater(changes['lines_added'], 0)
    
    def test_track_changes_untracked(self):
        """Test tracking untracked file."""
        new_file = Path(self.test_dir) / 'new.txt'
        new_file.write_text('New content')
        
        changes = self.change_tracker.track_changes(str(new_file))
        
        self.assertEqual(changes['status'], 'untracked')
        self.assertEqual(changes['change_type'], 'addition')
        self.assertEqual(changes['lines_added'], 1)
    
    def test_track_changes_deleted(self):
        """Test tracking deleted file."""
        self.test_file.unlink()
        
        changes = self.change_tracker.track_changes(str(self.test_file))
        
        self.assertEqual(changes['status'], 'deleted')
        self.assertEqual(changes['change_type'], 'deletion')
    
    def test_get_change_summary(self):
        """Test getting change summary."""
        self.test_file.write_text('# Header\nCompletely new content')
        
        summary = self.change_tracker.get_change_summary(str(self.test_file))
        
        self.assertIsInstance(summary, str)
        self.assertIn('test.md', summary)


class TestMessageGenerator(unittest.TestCase):
    """Test MessageGenerator class."""
    
    def setUp(self):
        """Set up test repository."""
        self.test_dir = tempfile.mkdtemp()
        self.repo = git.Repo.init(self.test_dir)
        
        # Initial commit
        test_file = Path(self.test_dir) / 'init.txt'
        test_file.write_text('Initial')
        self.repo.index.add(['init.txt'])
        self.repo.index.commit('Initial')
        
        self.msg_gen = MessageGenerator(self.repo)
    
    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.test_dir)
    
    def test_generate_message_new_file(self):
        """Test message generation for new file."""
        doc_path = Path(self.test_dir) / 'readme.md'
        doc_path.write_text('# README')
        
        message = self.msg_gen.generate_message(str(doc_path))
        
        self.assertIn('Add', message)
        self.assertIn('readme', message.lower())
    
    def test_generate_message_deleted_file(self):
        """Test message generation for deleted file."""
        # Create and commit a file first
        doc_path = Path(self.test_dir) / 'to_delete.txt'
        doc_path.write_text('Content')
        self.repo.index.add(['to_delete.txt'])
        self.repo.index.commit('Add file')
        
        # Delete it
        doc_path.unlink()
        
        message = self.msg_gen.generate_message(str(doc_path))
        
        self.assertIn('Remove', message)
        self.assertIn('to_delete', message)
    
    def test_generate_batch_message(self):
        """Test batch message generation."""
        files = []
        for i in range(3):
            file_path = Path(self.test_dir) / f'file{i}.py'
            file_path.write_text(f'# File {i}')
            files.append(str(file_path))
        
        message = self.msg_gen.generate_batch_message(files)
        
        self.assertIn('3', message)
        self.assertIn('files', message.lower())
    
    def test_get_document_type(self):
        """Test document type detection."""
        test_cases = {
            'test.py': 'Python module',
            'test.md': 'documentation',
            'test.js': 'JavaScript file',
            'test.yml': 'YAML config',
        }
        
        for filename, expected_type in test_cases.items():
            doc_path = Path(self.test_dir) / filename
            doc_type = self.msg_gen._get_document_type(doc_path)
            self.assertEqual(doc_type, expected_type)


class TestGitOperations(unittest.TestCase):
    """Test GitOperations class."""
    
    def setUp(self):
        """Set up test repository."""
        self.test_dir = tempfile.mkdtemp()
        self.repo = git.Repo.init(self.test_dir)
        
        # Create initial commit
        test_file = Path(self.test_dir) / 'test.txt'
        test_file.write_text('Initial')
        self.repo.index.add(['test.txt'])
        self.repo.index.commit('Initial commit')
        
        self.git_ops = GitOperations(self.repo)
    
    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.test_dir)
    
    def test_get_status(self):
        """Test getting repository status."""
        status = self.git_ops.get_status()
        
        self.assertIn('branch', status)
        self.assertIn('commit', status)
        self.assertIn('is_dirty', status)
        self.assertIn('untracked_files', status)
        self.assertIn('modified_files', status)
        self.assertIn('staged_files', status)
    
    def test_get_file_history(self):
        """Test getting file history."""
        test_file = Path(self.test_dir) / 'test.txt'
        
        # Make more commits
        for i in range(2):
            test_file.write_text(f'Version {i}')
            self.repo.index.add(['test.txt'])
            self.repo.index.commit(f'Update {i}')
        
        history = self.git_ops.get_file_history('test.txt', limit=5)
        
        self.assertIsInstance(history, list)
        self.assertGreater(len(history), 0)
        
        # Check first commit has required fields
        first = history[0]
        self.assertIn('hash', first)
        self.assertIn('short_hash', first)
        self.assertIn('message', first)
        self.assertIn('author', first)
        self.assertIn('date', first)
    
    def test_get_branches(self):
        """Test getting branches."""
        # Create a new branch
        self.repo.create_head('feature-branch')
        
        branches = self.git_ops.get_branches()
        
        self.assertIn('master', branches)
        self.assertIn('feature-branch', branches)
    
    def test_get_tags(self):
        """Test getting tags."""
        # Create a tag
        self.repo.create_tag('v1.0.0', message='Version 1.0.0')
        
        tags = self.git_ops.get_tags()
        
        self.assertIsInstance(tags, list)
        self.assertEqual(len(tags), 1)
        self.assertEqual(tags[0]['name'], 'v1.0.0')
    
    def test_get_commit_info(self):
        """Test getting commit information."""
        commit_hash = self.repo.head.commit.hexsha
        
        info = self.git_ops.get_commit_info(commit_hash)
        
        self.assertIsNotNone(info)
        self.assertEqual(info['hash'], commit_hash)
        self.assertIn('message', info)
        self.assertIn('author', info)
        self.assertIn('stats', info)


if __name__ == '__main__':
    unittest.main()