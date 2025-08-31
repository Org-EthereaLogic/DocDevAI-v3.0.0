"""
Tests for enhancement history and version control.
"""

import pytest
import json
from pathlib import Path
import tempfile
from datetime import datetime

from devdocai.enhancement.enhancement_history import (
    EnhancementVersion,
    VersionComparison,
    EnhancementHistory
)


class TestEnhancementVersion:
    """Test EnhancementVersion dataclass."""
    
    def test_initialization(self):
        """Test version initialization."""
        version = EnhancementVersion(
            version_id=1,
            content="Test content",
            quality_score=0.75,
            created_at=datetime.now(),
            metadata={"author": "test"},
            parent_version_id=None,
            strategy_applied="clarity",
            changes_summary="Initial version"
        )
        
        assert version.version_id == 1
        assert version.content == "Test content"
        assert version.quality_score == 0.75
        assert version.strategy_applied == "clarity"
        assert version.content_hash != ""  # Should be calculated
        
    def test_content_hash_calculation(self):
        """Test automatic content hash calculation."""
        version1 = EnhancementVersion(
            version_id=1,
            content="Test content",
            quality_score=0.75,
            created_at=datetime.now()
        )
        
        version2 = EnhancementVersion(
            version_id=2,
            content="Test content",  # Same content
            quality_score=0.80,
            created_at=datetime.now()
        )
        
        # Same content should have same hash
        assert version1.content_hash == version2.content_hash
        
        version3 = EnhancementVersion(
            version_id=3,
            content="Different content",
            quality_score=0.75,
            created_at=datetime.now()
        )
        
        # Different content should have different hash
        assert version1.content_hash != version3.content_hash
        
    def test_to_dict(self):
        """Test converting version to dictionary."""
        version = EnhancementVersion(
            version_id=1,
            content="A" * 300,  # Long content
            quality_score=0.75,
            created_at=datetime.now(),
            metadata={"test": True},
            parent_version_id=0,
            strategy_applied="clarity"
        )
        
        data = version.to_dict()
        
        assert data["version_id"] == 1
        assert len(data["content_preview"]) < 300  # Should be truncated
        assert "..." in data["content_preview"]
        assert data["quality_score"] == 0.75
        assert data["strategy_applied"] == "clarity"
        assert "created_at" in data


class TestVersionComparison:
    """Test VersionComparison dataclass."""
    
    def test_initialization(self):
        """Test comparison initialization."""
        comparison = VersionComparison(
            version1_id=1,
            version2_id=2,
            quality_delta=0.1,
            content_diff=["+ Added line", "- Removed line"],
            added_lines=5,
            removed_lines=3,
            modified_lines=2,
            similarity_ratio=0.85,
            strategies_between=["clarity", "completeness"]
        )
        
        assert comparison.version1_id == 1
        assert comparison.version2_id == 2
        assert comparison.quality_delta == 0.1
        assert len(comparison.content_diff) == 2
        assert comparison.similarity_ratio == 0.85
        
    def test_to_dict(self):
        """Test converting comparison to dictionary."""
        diff_lines = [f"Line {i}" for i in range(20)]
        comparison = VersionComparison(
            version1_id=1,
            version2_id=2,
            quality_delta=0.15,
            content_diff=diff_lines,
            added_lines=10,
            removed_lines=5,
            modified_lines=3,
            similarity_ratio=0.75,
            strategies_between=["clarity"]
        )
        
        data = comparison.to_dict()
        
        assert data["version1_id"] == 1
        assert data["version2_id"] == 2
        assert data["quality_delta"] == 0.15
        assert len(data["diff_preview"]) == 10  # Truncated to 10
        
    def test_generate_diff_report(self):
        """Test generating diff report."""
        comparison = VersionComparison(
            version1_id=1,
            version2_id=3,
            quality_delta=0.2,
            content_diff=["+ Added line", "- Removed line", "  Unchanged"],
            added_lines=10,
            removed_lines=5,
            modified_lines=3,
            similarity_ratio=0.8,
            strategies_between=["clarity", "readability"]
        )
        
        report = comparison.generate_diff_report()
        
        assert "v1 → v3" in report
        assert "+20.0%" in report  # Quality change
        assert "80.0%" in report  # Similarity
        assert "Added: 10 lines" in report
        assert "clarity" in report


class TestEnhancementHistory:
    """Test EnhancementHistory class."""
    
    @pytest.fixture
    def history(self):
        """Create history instance."""
        return EnhancementHistory(max_versions_per_document=10)
        
    def test_initialization(self, history):
        """Test history initialization."""
        assert history.max_versions == 10
        assert history.versions == {}
        assert history.current_versions == {}
        assert history.version_counter == 0
        
    def test_add_version(self, history):
        """Test adding a version."""
        version = history.add_version(
            content="Test content",
            quality_score=0.75,
            document_id="doc1",
            metadata={"test": True},
            strategy_applied="clarity"
        )
        
        assert isinstance(version, EnhancementVersion)
        assert version.version_id == 1
        assert version.content == "Test content"
        assert version.quality_score == 0.75
        assert version.parent_version_id is None  # First version
        
        # Check it was stored
        assert "doc1" in history.versions
        assert len(history.versions["doc1"]) == 1
        assert history.current_versions["doc1"] == 0
        
    def test_add_version_with_parent(self, history):
        """Test adding versions with parent relationships."""
        v1 = history.add_version("Content 1", 0.5, "doc1")
        v2 = history.add_version("Content 2", 0.6, "doc1")
        v3 = history.add_version("Content 3", 0.7, "doc1")
        
        assert v1.parent_version_id is None
        assert v2.parent_version_id == v1.version_id
        assert v3.parent_version_id == v2.version_id
        
    def test_add_version_auto_id(self, history):
        """Test adding version with auto-generated ID."""
        version = history.add_version(
            content="Test",
            quality_score=0.5
        )
        
        assert version.version_id == 1
        # Document ID should be generated from content hash
        assert len(history.versions) == 1
        
    def test_version_limit_enforcement(self, history):
        """Test that version limit is enforced."""
        history.max_versions = 3
        
        # Add more than max versions
        for i in range(5):
            history.add_version(f"Content {i}", 0.5 + i*0.1, "doc1")
        
        # Should only keep last 3 versions
        assert len(history.versions["doc1"]) == 3
        # First version should be v3 (0 and 1 were removed)
        assert history.versions["doc1"][0].content == "Content 2"
        
    def test_get_version(self, history):
        """Test getting a specific version."""
        v1 = history.add_version("Content 1", 0.5, "doc1")
        v2 = history.add_version("Content 2", 0.6, "doc1")
        v3 = history.add_version("Content 3", 0.7, "doc2")
        
        # Get with document ID (faster)
        retrieved = history.get_version(v1.version_id, "doc1")
        assert retrieved == v1
        
        # Get without document ID (searches all)
        retrieved = history.get_version(v3.version_id)
        assert retrieved == v3
        
        # Non-existent version
        assert history.get_version(999) is None
        
    def test_get_current_version(self, history):
        """Test getting current version."""
        v1 = history.add_version("Content 1", 0.5, "doc1")
        v2 = history.add_version("Content 2", 0.6, "doc1")
        
        current = history.get_current_version("doc1")
        assert current == v2
        
        # Non-existent document
        assert history.get_current_version("unknown") is None
        
    def test_get_previous_version(self, history):
        """Test getting previous version."""
        v1 = history.add_version("Content 1", 0.5, "doc1")
        v2 = history.add_version("Content 2", 0.6, "doc1")
        v3 = history.add_version("Content 3", 0.7, "doc1")
        
        previous = history.get_previous_version("doc1")
        assert previous == v2
        
        # Document with only one version
        history.add_version("Only", 0.5, "doc2")
        assert history.get_previous_version("doc2") is None
        
    def test_get_previous_version_auto(self, history):
        """Test getting previous version without document ID."""
        v1 = history.add_version("Content 1", 0.5, "doc1")
        v2 = history.add_version("Content 2", 0.6, "doc1")
        
        previous = history.get_previous_version()
        assert previous == v1
        
    def test_get_versions(self, history):
        """Test getting all versions."""
        v1 = history.add_version("Content 1", 0.5, "doc1")
        v2 = history.add_version("Content 2", 0.6, "doc1")
        v3 = history.add_version("Content 3", 0.7, "doc2")
        
        # Get for specific document
        doc1_versions = history.get_versions("doc1")
        assert len(doc1_versions) == 2
        
        # Get all versions
        all_versions = history.get_versions()
        assert len(all_versions) == 3
        
    def test_rollback_to_previous(self, history):
        """Test rolling back to previous version."""
        v1 = history.add_version("Content 1", 0.5, "doc1")
        v2 = history.add_version("Content 2", 0.6, "doc1")
        v3 = history.add_version("Content 3", 0.4, "doc1")  # Quality degraded
        
        rolled_back = history.rollback("doc1")
        
        assert rolled_back is not None
        assert rolled_back.content == "Content 2"  # Previous content
        assert rolled_back.quality_score == 0.6
        assert "rollback" in rolled_back.metadata
        
    def test_rollback_to_specific(self, history):
        """Test rolling back to specific version."""
        v1 = history.add_version("Content 1", 0.5, "doc1")
        v2 = history.add_version("Content 2", 0.6, "doc1")
        v3 = history.add_version("Content 3", 0.7, "doc1")
        
        rolled_back = history.rollback("doc1", v1.version_id)
        
        assert rolled_back == v1
        assert history.current_versions["doc1"] == 0  # Index of v1
        
    def test_rollback_nonexistent(self, history):
        """Test rollback with non-existent document."""
        result = history.rollback("unknown")
        assert result is None
        
    def test_compare_versions(self, history):
        """Test comparing two versions."""
        v1 = history.add_version("Line 1\nLine 2\nLine 3", 0.5, "doc1")
        v2 = history.add_version("Line 1\nModified 2\nLine 3\nLine 4", 0.7, "doc1", 
                                strategy_applied="clarity")
        
        comparison = history.compare_versions(v1.version_id, v2.version_id, "doc1")
        
        assert isinstance(comparison, VersionComparison)
        assert comparison.version1_id == v1.version_id
        assert comparison.version2_id == v2.version_id
        assert comparison.quality_delta == 0.2
        assert comparison.added_lines > 0
        assert comparison.similarity_ratio > 0.5
        assert "clarity" in comparison.strategies_between
        
    def test_compare_versions_not_found(self, history):
        """Test comparing non-existent versions."""
        comparison = history.compare_versions(999, 1000)
        assert comparison is None
        
    def test_generate_changes_summary(self, history):
        """Test generating changes summary."""
        v1 = history.add_version("Short", 0.5, "doc1")
        
        # Longer content
        summary = history._generate_changes_summary("doc1", "Much longer content with more words")
        assert "words" in summary
        
        # No previous version
        summary = history._generate_changes_summary("new_doc", "Content")
        assert summary == "Initial version"
        
    def test_get_strategies_between(self, history):
        """Test getting strategies between versions."""
        v1 = history.add_version("Content 1", 0.5, "doc1")
        v2 = history.add_version("Content 2", 0.6, "doc1", strategy_applied="clarity")
        v3 = history.add_version("Content 3", 0.7, "doc1", strategy_applied="completeness")
        v4 = history.add_version("Content 4", 0.8, "doc1", strategy_applied="readability")
        
        strategies = history._get_strategies_between(v1.version_id, v4.version_id, "doc1")
        
        assert len(strategies) == 3
        assert "clarity" in strategies
        assert "completeness" in strategies
        assert "readability" in strategies
        
    def test_get_version_tree(self, history):
        """Test getting version tree structure."""
        v1 = history.add_version("Content 1", 0.5, "doc1", strategy_applied="clarity")
        v2 = history.add_version("Content 2", 0.6, "doc1", strategy_applied="completeness")
        
        tree = history.get_version_tree("doc1")
        
        assert tree["document_id"] == "doc1"
        assert tree["total_versions"] == 2
        assert len(tree["versions"]) == 2
        assert tree["versions"][0]["strategy"] == "clarity"
        
        # Non-existent document
        empty_tree = history.get_version_tree("unknown")
        assert empty_tree == {}
        
    def test_export_import_history(self, history):
        """Test exporting and importing history."""
        # Add some versions
        v1 = history.add_version("Content 1", 0.5, "doc1")
        v2 = history.add_version("Content 2", 0.6, "doc1")
        v3 = history.add_version("Content A", 0.7, "doc2")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = Path(tmpdir) / "history.json"
            
            # Export
            history.export_history(export_path)
            assert export_path.exists()
            
            # Create new history and import
            new_history = EnhancementHistory()
            new_history.import_history(export_path)
            
            # Verify imported data
            assert len(new_history.versions) == 2
            assert "doc1" in new_history.versions
            assert "doc2" in new_history.versions
            assert len(new_history.versions["doc1"]) == 2
            assert new_history.version_counter >= 3
            
    def test_export_single_document(self, history):
        """Test exporting single document history."""
        v1 = history.add_version("Content 1", 0.5, "doc1")
        v2 = history.add_version("Content 2", 0.6, "doc2")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = Path(tmpdir) / "doc1_history.json"
            
            history.export_history(export_path, "doc1")
            
            with open(export_path) as f:
                data = json.load(f)
            
            assert data["document_id"] == "doc1"
            assert len(data["versions"]) == 1
            
    def test_clear_history(self, history):
        """Test clearing history."""
        v1 = history.add_version("Content 1", 0.5, "doc1")
        v2 = history.add_version("Content 2", 0.6, "doc2")
        
        # Clear specific document
        history.clear_history("doc1")
        assert "doc1" not in history.versions
        assert "doc2" in history.versions
        
        # Clear all
        history.clear_history()
        assert len(history.versions) == 0
        assert history.version_counter == 0