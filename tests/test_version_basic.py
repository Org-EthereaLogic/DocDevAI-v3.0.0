"""Basic tests for M012 Version Control Integration"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from devdocai.core.storage import Document
from devdocai.operations.version import VersionControlManager


class TestVersionControlBasic(unittest.TestCase):
    """Basic tests for Version Control Manager."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary directory
        self.test_dir = tempfile.mkdtemp(prefix="vcm_test_")
        self.repo_path = Path(self.test_dir)

        # Mock configuration
        self.config = MagicMock()
        self.config.get.side_effect = lambda k, d=None: {
            "version_control.enabled": True,
            "version_control.auto_commit": False,
            "version_control.branch_prefix": "docs/",
            "version_control.commit_template": "docs: {message}",
            "version_control.merge_strategy": "ours",
            "version_control.track_metadata": True,
        }.get(k, d)

        # Mock storage and tracking
        self.storage = MagicMock()
        self.tracking = MagicMock()

    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_initialization(self):
        """Test basic initialization."""
        vcm = VersionControlManager(self.config, self.storage, self.tracking, self.repo_path)
        self.assertIsNotNone(vcm)
        self.assertTrue((self.repo_path / ".git").exists())

    def test_commit_document(self):
        """Test committing a document."""
        vcm = VersionControlManager(self.config, self.storage, self.tracking, self.repo_path)

        # Create a document
        doc = Document(id="test-doc", content="Test content", type="markdown")

        # Commit it
        commit_info = vcm.commit_document(doc, "Test commit")

        self.assertIsNotNone(commit_info)
        self.assertEqual(commit_info.message, "docs: Test commit")
        self.assertIn("test-doc.md", commit_info.files)

    def test_create_branch(self):
        """Test creating a branch."""
        vcm = VersionControlManager(self.config, self.storage, self.tracking, self.repo_path)

        # Create a branch
        branch_info = vcm.create_branch("feature", "Feature branch")

        self.assertIsNotNone(branch_info)
        self.assertEqual(branch_info.name, "docs/feature")
        self.assertTrue(branch_info.is_active)

    def test_get_statistics(self):
        """Test getting repository statistics."""
        vcm = VersionControlManager(self.config, self.storage, self.tracking, self.repo_path)

        # Get stats
        stats = vcm.get_statistics()

        self.assertIsNotNone(stats)
        self.assertIn("total_commits", stats)
        self.assertIn("total_branches", stats)
        self.assertGreater(stats["total_commits"], 0)  # Should have initial commit


if __name__ == "__main__":
    unittest.main()
