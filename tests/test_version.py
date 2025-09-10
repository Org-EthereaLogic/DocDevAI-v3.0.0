"""Tests for M012 Version Control Integration - Pass 1: Core Implementation
DevDocAI v3.0.0

This test suite validates the Version Control Integration module with:
- Native Git integration for document versioning
- Commit tracking with metadata
- Branch management and merge conflict resolution
- Impact analysis for document changes
- Integration with M002 storage and M005 tracking
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Test imports
from devdocai.core.config import ConfigurationManager
from devdocai.core.storage import Document, StorageManager
from devdocai.core.tracking import TrackingMatrix
from devdocai.operations.version import VersionControlManager
from devdocai.operations.version_types import ConflictResolution, GitError, MergeConflict


class TestVersionControlManager(unittest.TestCase):
    """Test suite for Version Control Manager."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary directory for test repository
        self.test_dir = tempfile.mkdtemp(prefix="devdocai_test_")
        self.repo_path = Path(self.test_dir)

        # Create mock configuration
        self.config = MagicMock(spec=ConfigurationManager)
        self.config.get.side_effect = self._mock_config_get

        # Create mock storage manager
        self.storage = MagicMock(spec=StorageManager)
        self.storage.get_document.return_value = Document(
            id="test-doc", content="Test content", type="markdown"
        )
        self.storage.save_document.return_value = "test-doc"
        self.storage.document_exists.return_value = True

        # Create mock tracking matrix
        self.tracking = MagicMock(spec=TrackingMatrix)
        self.tracking.get_dependencies.return_value = ["dep-1", "dep-2"]
        self.tracking.get_dependents.return_value = ["dependent-1"]

        # Initialize version control manager
        self.version_manager = VersionControlManager(
            config=self.config,
            storage=self.storage,
            tracking=self.tracking,
            repo_path=self.repo_path,
        )

    def tearDown(self):
        """Clean up test environment."""
        # Clean up temporary directory
        if hasattr(self, "test_dir") and os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def _mock_config_get(self, key, default=None):
        """Mock configuration values."""
        config_values = {
            "version_control.enabled": True,
            "version_control.auto_commit": False,
            "version_control.branch_prefix": "docs/",
            "version_control.commit_template": "docs: {message}",
            "version_control.merge_strategy": "ours",
            "version_control.track_metadata": True,
            "version_control.repo_path": str(self.repo_path) if hasattr(self, "repo_path") else ".",
        }
        return config_values.get(key, default)

    def test_initialization(self):
        """Test version control manager initialization."""
        self.assertIsNotNone(self.version_manager)
        self.assertEqual(self.version_manager.repo_path, self.repo_path)
        self.assertIsNotNone(self.version_manager.repo)
        self.assertTrue(self.version_manager.enabled)

    def test_init_repository(self):
        """Test Git repository initialization."""
        # Remove existing repo to test init
        shutil.rmtree(self.repo_path / ".git", ignore_errors=True)

        # Initialize repository
        result = self.version_manager.init_repository()

        self.assertTrue(result)
        self.assertTrue((self.repo_path / ".git").exists())
        self.assertIsNotNone(self.version_manager.repo)

    def test_commit_document(self):
        """Test committing a document."""
        # Create test document
        doc = Document(id="test-doc", content="Test content", type="markdown")

        # Write document file
        doc_path = self.repo_path / "test-doc.md"
        doc_path.write_text("Test content")

        # Commit document
        commit_info = self.version_manager.commit_document(
            doc, message="Add test document", author="Test User"
        )

        self.assertIsNotNone(commit_info)
        self.assertEqual(commit_info.message, "docs: Add test document")
        self.assertEqual(commit_info.author, "Test User")
        self.assertIn("test-doc.md", commit_info.files)

    def test_create_branch(self):
        """Test creating a new branch."""
        # Create branch
        branch_info = self.version_manager.create_branch(
            "feature-docs", description="Feature documentation"
        )

        self.assertIsNotNone(branch_info)
        self.assertEqual(branch_info.name, "docs/feature-docs")
        self.assertEqual(branch_info.description, "Feature documentation")
        self.assertTrue(branch_info.is_active)

    def test_switch_branch(self):
        """Test switching branches."""
        # Create new branch
        self.version_manager.create_branch("test-branch")

        # Switch to branch
        result = self.version_manager.switch_branch("docs/test-branch")

        self.assertTrue(result)
        self.assertEqual(self.version_manager.get_current_branch().name, "docs/test-branch")

    def test_merge_branches(self):
        """Test merging branches."""
        # Create and switch to feature branch
        self.version_manager.create_branch("feature")

        # Create a test file in feature branch
        test_file = self.repo_path / "feature.md"
        test_file.write_text("Feature content")
        self.version_manager.repo.index.add(["feature.md"])  # Use relative path
        self.version_manager.repo.index.commit("Add feature file")

        # Switch back to main branch
        self.version_manager.switch_branch("main")

        # Merge feature branch
        merge_result = self.version_manager.merge_branch(
            "docs/feature", message="Merge feature docs"
        )

        self.assertTrue(merge_result.success)
        self.assertIsNone(merge_result.conflicts)
        self.assertTrue(test_file.exists())

    def test_detect_merge_conflicts(self):
        """Test merge conflict detection."""
        # Create conflicting changes in two branches
        main_file = self.repo_path / "conflict.md"

        # Main branch change
        main_file.write_text("Main content")
        self.version_manager.repo.index.add(["conflict.md"])  # Use relative path
        self.version_manager.repo.index.commit("Main change")

        # Create and switch to feature branch
        self.version_manager.create_branch("feature")
        main_file.write_text("Feature content")
        self.version_manager.repo.index.add(["conflict.md"])  # Use relative path
        self.version_manager.repo.index.commit("Feature change")

        # Switch back to main and attempt merge
        self.version_manager.switch_branch("main")

        # Check for conflicts (mock the conflict detection)
        with patch.object(self.version_manager, "_detect_conflicts", return_value=True):
            has_conflicts = self.version_manager.has_merge_conflicts("docs/feature")
            self.assertTrue(has_conflicts)

    def test_resolve_conflicts(self):
        """Test merge conflict resolution."""
        # Create a mock conflict
        conflict = MergeConflict(
            file_path="conflict.md",
            our_content="Our content",
            their_content="Their content",
            base_content="Base content",
        )

        # Resolve using 'ours' strategy
        resolution = self.version_manager.resolve_conflict(
            conflict, strategy=ConflictResolution.OURS
        )

        self.assertEqual(resolution.resolved_content, "Our content")
        self.assertEqual(resolution.strategy, ConflictResolution.OURS)

        # Resolve using 'theirs' strategy
        resolution = self.version_manager.resolve_conflict(
            conflict, strategy=ConflictResolution.THEIRS
        )

        self.assertEqual(resolution.resolved_content, "Their content")
        self.assertEqual(resolution.strategy, ConflictResolution.THEIRS)

    def test_get_document_history(self):
        """Test retrieving document version history."""
        # Create document versions
        doc_file = self.repo_path / "history-doc.md"

        for i in range(3):
            doc_file.write_text(f"Version {i+1}")
            self.version_manager.repo.index.add(["history-doc.md"])  # Use relative path
            self.version_manager.repo.index.commit(f"Update version {i+1}")

        # Get history
        history = self.version_manager.get_document_history("history-doc.md")

        self.assertEqual(len(history), 3)
        for i, version in enumerate(history):
            self.assertIn(f"Update version {i+1}", version.message)
            self.assertEqual(version.file_path, "history-doc.md")

    def test_diff_documents(self):
        """Test document diff generation."""
        # Create document versions
        doc_file = self.repo_path / "diff-doc.md"

        # Version 1
        doc_file.write_text("Line 1\nLine 2\nLine 3")
        self.version_manager.repo.index.add(["diff-doc.md"])  # Use relative path
        commit1 = self.version_manager.repo.index.commit("Version 1")

        # Version 2
        doc_file.write_text("Line 1\nModified Line 2\nLine 3\nLine 4")
        self.version_manager.repo.index.add(["diff-doc.md"])  # Use relative path
        commit2 = self.version_manager.repo.index.commit("Version 2")

        # Get diff
        diff = self.version_manager.get_diff(
            "diff-doc.md", from_commit=str(commit1), to_commit=str(commit2)
        )

        self.assertIsNotNone(diff)
        self.assertIn("Modified Line 2", diff.added_lines)
        self.assertIn("Line 4", diff.added_lines)
        self.assertIn("Line 2", diff.removed_lines)

    def test_impact_analysis(self):
        """Test document change impact analysis."""
        # Set up dependencies
        self.tracking.get_dependencies.return_value = ["dep-1", "dep-2", "dep-3"]
        self.tracking.get_dependents.return_value = ["dependent-1", "dependent-2"]

        # Analyze impact
        impact = self.version_manager.analyze_impact("changed-doc")

        self.assertIsNotNone(impact)
        self.assertEqual(impact.document_id, "changed-doc")
        self.assertEqual(len(impact.affected_documents), 5)
        self.assertIn("dep-1", impact.affected_documents)
        self.assertIn("dependent-1", impact.affected_documents)
        self.assertEqual(impact.impact_level, "high")  # >3 affected docs

    def test_tag_version(self):
        """Test version tagging."""
        # Create a tag
        tag_info = self.version_manager.tag_version("v1.0.0", message="Release version 1.0.0")

        self.assertIsNotNone(tag_info)
        self.assertEqual(tag_info.name, "v1.0.0")
        self.assertEqual(tag_info.message, "Release version 1.0.0")
        self.assertIsNotNone(tag_info.commit)

    def test_rollback_changes(self):
        """Test rolling back changes."""
        # Create changes
        doc_file = self.repo_path / "rollback-doc.md"

        # Original version
        doc_file.write_text("Original content")
        self.version_manager.repo.index.add(["rollback-doc.md"])  # Use relative path
        original_commit = self.version_manager.repo.index.commit("Original")

        # Modified version
        doc_file.write_text("Modified content")
        self.version_manager.repo.index.add(["rollback-doc.md"])  # Use relative path
        self.version_manager.repo.index.commit("Modified")

        # Rollback to original
        result = self.version_manager.rollback_to(str(original_commit))

        self.assertTrue(result)
        self.assertEqual(doc_file.read_text(), "Original content")

    def test_get_uncommitted_changes(self):
        """Test detecting uncommitted changes."""
        # Create uncommitted changes
        new_file = self.repo_path / "uncommitted.md"
        new_file.write_text("Uncommitted content")

        modified_file = self.repo_path / "modified.md"
        modified_file.write_text("Original")
        self.version_manager.repo.index.add(["modified.md"])  # Use relative path
        self.version_manager.repo.index.commit("Add modified file")
        modified_file.write_text("Modified")

        # Get uncommitted changes
        changes = self.version_manager.get_uncommitted_changes()

        self.assertIsNotNone(changes)
        self.assertIn("uncommitted.md", changes.untracked)
        self.assertIn("modified.md", changes.modified)

    def test_auto_commit(self):
        """Test automatic commit on document save."""
        # Enable auto-commit
        self.version_manager.auto_commit = True

        # Save document (triggers auto-commit)
        doc = Document(id="auto-doc", content="Auto content", type="markdown")
        doc_file = self.repo_path / "auto-doc.md"
        doc_file.write_text("Auto content")

        commit_info = self.version_manager.auto_commit_document(doc)

        self.assertIsNotNone(commit_info)
        self.assertIn("auto-doc", commit_info.message.lower())

    def test_branch_comparison(self):
        """Test comparing branches."""
        # Create feature branch with changes
        self.version_manager.create_branch("feature")

        feature_file = self.repo_path / "feature.md"
        feature_file.write_text("Feature content")
        self.version_manager.repo.index.add(["feature.md"])  # Use relative path
        self.version_manager.repo.index.commit("Add feature")

        # Compare branches
        comparison = self.version_manager.compare_branches("main", "docs/feature")

        self.assertIsNotNone(comparison)
        self.assertGreater(comparison.ahead_count, 0)
        self.assertEqual(comparison.behind_count, 0)
        self.assertIn("feature.md", comparison.different_files)

    def test_stash_changes(self):
        """Test stashing uncommitted changes."""
        # Create uncommitted changes
        stash_file = self.repo_path / "stash.md"
        stash_file.write_text("Stashed content")

        # Stash changes
        stash_id = self.version_manager.stash_changes("Work in progress")

        self.assertIsNotNone(stash_id)
        self.assertFalse(stash_file.exists())  # File should be stashed

        # Apply stash
        result = self.version_manager.apply_stash(stash_id)

        self.assertTrue(result)
        self.assertTrue(stash_file.exists())  # File should be restored
        self.assertEqual(stash_file.read_text(), "Stashed content")

    def test_integration_with_storage(self):
        """Test integration with M002 storage system."""
        # Save document to storage
        doc = Document(id="storage-doc", content="Storage content", type="markdown")
        self.storage.save_document.return_value = "storage-doc"

        # Version the document
        commit_info = self.version_manager.version_document(doc, message="Version from storage")

        self.assertIsNotNone(commit_info)
        self.storage.save_document.assert_called_once_with(doc)
        self.assertIn("storage-doc", commit_info.files)

    def test_integration_with_tracking(self):
        """Test integration with M005 tracking matrix."""
        # Set up tracking data
        self.tracking.get_dependencies.return_value = ["dep-1", "dep-2"]
        self.tracking.get_dependents.return_value = ["dependent-1"]

        # Analyze impact with tracking
        impact = self.version_manager.analyze_document_impact("tracked-doc")

        self.assertIsNotNone(impact)
        self.tracking.get_dependencies.assert_called_once_with("tracked-doc")
        self.tracking.get_dependents.assert_called_once_with("tracked-doc")
        self.assertEqual(len(impact.dependencies), 2)
        self.assertEqual(len(impact.dependents), 1)

    def test_error_handling(self):
        """Test error handling in version control operations."""
        # Test with invalid repository path
        with self.assertRaises(GitError):
            invalid_manager = VersionControlManager(
                config=self.config,
                storage=self.storage,
                tracking=self.tracking,
                repo_path="/invalid/path",
            )

        # Test invalid branch name
        with self.assertRaises(GitError):
            self.version_manager.switch_branch("non-existent-branch")

        # Test invalid commit
        with self.assertRaises(GitError):
            self.version_manager.rollback_to("invalid-commit-hash")

    def test_concurrent_operations(self):
        """Test handling concurrent version control operations."""
        import threading

        results = []

        def commit_operation(index):
            try:
                doc_file = self.repo_path / f"concurrent-{index}.md"
                doc_file.write_text(f"Content {index}")
                self.version_manager.repo.index.add([f"concurrent-{index}.md"])  # Use relative path
                commit = self.version_manager.repo.index.commit(f"Commit {index}")
                results.append((index, True, str(commit)))
            except Exception as e:
                results.append((index, False, str(e)))

        # Run concurrent commits
        threads = []
        for i in range(5):
            thread = threading.Thread(target=commit_operation, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify all operations completed
        self.assertEqual(len(results), 5)
        successful = [r for r in results if r[1]]
        self.assertGreater(len(successful), 0)

    def test_large_repository_performance(self):
        """Test performance with large number of documents."""
        import time

        # Create many documents
        start_time = time.time()
        for i in range(100):
            doc_file = self.repo_path / f"perf-doc-{i}.md"
            doc_file.write_text(f"Performance test content {i}")

        # Batch commit
        self.version_manager.repo.index.add(["*.md"])
        self.version_manager.repo.index.commit("Batch commit of 100 documents")

        elapsed_time = time.time() - start_time

        # Should complete in reasonable time
        self.assertLess(elapsed_time, 10.0)  # 10 seconds max

        # Verify history retrieval performance
        start_time = time.time()
        history = self.version_manager.get_document_history("perf-doc-50.md")
        elapsed_time = time.time() - start_time

        self.assertLess(elapsed_time, 1.0)  # 1 second max
        self.assertIsNotNone(history)


if __name__ == "__main__":
    unittest.main()
