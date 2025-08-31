"""
Enhancement history and version control system.

Tracks document versions through enhancement iterations with rollback capabilities.
"""

import logging
import hashlib
import difflib
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class EnhancementVersion:
    """Represents a version of an enhanced document."""
    
    version_id: int
    content: str
    quality_score: float
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_version_id: Optional[int] = None
    strategy_applied: Optional[str] = None
    changes_summary: Optional[str] = None
    content_hash: str = ""
    
    def __post_init__(self):
        """Calculate content hash after initialization."""
        if not self.content_hash:
            self.content_hash = hashlib.sha256(self.content.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert version to dictionary."""
        return {
            "version_id": self.version_id,
            "content_preview": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "quality_score": self.quality_score,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
            "parent_version_id": self.parent_version_id,
            "strategy_applied": self.strategy_applied,
            "changes_summary": self.changes_summary,
            "content_hash": self.content_hash
        }


@dataclass
class VersionComparison:
    """Comparison between two document versions."""
    
    version1_id: int
    version2_id: int
    quality_delta: float
    content_diff: List[str]
    added_lines: int
    removed_lines: int
    modified_lines: int
    similarity_ratio: float
    strategies_between: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert comparison to dictionary."""
        return {
            "version1_id": self.version1_id,
            "version2_id": self.version2_id,
            "quality_delta": self.quality_delta,
            "diff_preview": self.content_diff[:10] if len(self.content_diff) > 10 else self.content_diff,
            "added_lines": self.added_lines,
            "removed_lines": self.removed_lines,
            "modified_lines": self.modified_lines,
            "similarity_ratio": self.similarity_ratio,
            "strategies_between": self.strategies_between
        }
    
    def generate_diff_report(self) -> str:
        """Generate human-readable diff report."""
        report = f"Version Comparison: v{self.version1_id} → v{self.version2_id}\n"
        report += "=" * 50 + "\n\n"
        
        report += f"Quality Change: {self.quality_delta:+.2%}\n"
        report += f"Similarity: {self.similarity_ratio:.1%}\n\n"
        
        report += "Changes:\n"
        report += f"  Added: {self.added_lines} lines\n"
        report += f"  Removed: {self.removed_lines} lines\n"
        report += f"  Modified: {self.modified_lines} lines\n\n"
        
        if self.strategies_between:
            report += f"Strategies Applied: {', '.join(self.strategies_between)}\n\n"
        
        if self.content_diff:
            report += "Diff Preview:\n"
            report += "-" * 40 + "\n"
            for line in self.content_diff[:20]:
                report += line + "\n"
            if len(self.content_diff) > 20:
                report += f"... ({len(self.content_diff) - 20} more lines)\n"
        
        return report


class EnhancementHistory:
    """
    Manages version history for document enhancements.
    
    Provides version control, rollback capabilities, and diff generation.
    """
    
    def __init__(self, max_versions_per_document: int = 50):
        """
        Initialize enhancement history manager.
        
        Args:
            max_versions_per_document: Maximum versions to keep per document
        """
        self.max_versions = max_versions_per_document
        self.versions: Dict[str, List[EnhancementVersion]] = {}
        self.current_versions: Dict[str, int] = {}
        self.version_counter = 0
        
        logger.info(f"Enhancement History initialized (max {max_versions_per_document} versions)")
    
    def add_version(
        self,
        content: str,
        quality_score: float,
        document_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        strategy_applied: Optional[str] = None
    ) -> EnhancementVersion:
        """
        Add a new version to history.
        
        Args:
            content: Document content
            quality_score: Quality score of this version
            document_id: Optional document identifier
            metadata: Optional metadata
            strategy_applied: Strategy that created this version
            
        Returns:
            Created EnhancementVersion
        """
        # Generate document ID if not provided
        if not document_id:
            document_id = hashlib.md5(content.encode()).hexdigest()[:8]
        
        # Initialize version list for new documents
        if document_id not in self.versions:
            self.versions[document_id] = []
            self.current_versions[document_id] = -1
        
        # Get parent version ID
        parent_id = None
        if self.versions[document_id]:
            parent_id = self.versions[document_id][-1].version_id
        
        # Create new version
        self.version_counter += 1
        version = EnhancementVersion(
            version_id=self.version_counter,
            content=content,
            quality_score=quality_score,
            created_at=datetime.now(),
            metadata=metadata or {},
            parent_version_id=parent_id,
            strategy_applied=strategy_applied,
            changes_summary=self._generate_changes_summary(document_id, content)
        )
        
        # Add to history
        self.versions[document_id].append(version)
        self.current_versions[document_id] = len(self.versions[document_id]) - 1
        
        # Enforce version limit
        if len(self.versions[document_id]) > self.max_versions:
            self.versions[document_id].pop(0)
            self.current_versions[document_id] -= 1
        
        logger.info(f"Added version {version.version_id} for document {document_id}")
        
        return version
    
    def get_version(
        self,
        version_id: int,
        document_id: Optional[str] = None
    ) -> Optional[EnhancementVersion]:
        """
        Get a specific version.
        
        Args:
            version_id: Version ID to retrieve
            document_id: Optional document ID for faster lookup
            
        Returns:
            EnhancementVersion or None if not found
        """
        if document_id and document_id in self.versions:
            for version in self.versions[document_id]:
                if version.version_id == version_id:
                    return version
        else:
            # Search all documents
            for versions in self.versions.values():
                for version in versions:
                    if version.version_id == version_id:
                        return version
        return None
    
    def get_current_version(
        self,
        document_id: str
    ) -> Optional[EnhancementVersion]:
        """
        Get the current version for a document.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Current EnhancementVersion or None
        """
        if document_id not in self.versions or not self.versions[document_id]:
            return None
        
        current_idx = self.current_versions.get(document_id, -1)
        if 0 <= current_idx < len(self.versions[document_id]):
            return self.versions[document_id][current_idx]
        
        return self.versions[document_id][-1]
    
    def get_previous_version(
        self,
        document_id: Optional[str] = None
    ) -> Optional[EnhancementVersion]:
        """
        Get the previous version for rollback.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Previous EnhancementVersion or None
        """
        # If no document_id, use the most recently modified document
        if not document_id:
            if not self.versions:
                return None
            # Find most recent document
            latest_doc = max(
                self.versions.keys(),
                key=lambda d: self.versions[d][-1].created_at if self.versions[d] else datetime.min
            )
            document_id = latest_doc
        
        if document_id not in self.versions or len(self.versions[document_id]) < 2:
            return None
        
        return self.versions[document_id][-2]
    
    def get_versions(
        self,
        document_id: Optional[str] = None
    ) -> List[EnhancementVersion]:
        """
        Get all versions for a document.
        
        Args:
            document_id: Document identifier (None for all)
            
        Returns:
            List of EnhancementVersion objects
        """
        if document_id:
            return self.versions.get(document_id, [])
        else:
            # Return all versions
            all_versions = []
            for versions in self.versions.values():
                all_versions.extend(versions)
            return sorted(all_versions, key=lambda v: v.created_at)
    
    def rollback(
        self,
        document_id: str,
        target_version_id: Optional[int] = None
    ) -> Optional[EnhancementVersion]:
        """
        Rollback to a previous version.
        
        Args:
            document_id: Document identifier
            target_version_id: Specific version to rollback to (None for previous)
            
        Returns:
            Rolled back version or None
        """
        if document_id not in self.versions or not self.versions[document_id]:
            logger.warning(f"No versions found for document {document_id}")
            return None
        
        if target_version_id:
            # Find specific version
            for i, version in enumerate(self.versions[document_id]):
                if version.version_id == target_version_id:
                    self.current_versions[document_id] = i
                    logger.info(f"Rolled back document {document_id} to version {target_version_id}")
                    return version
            logger.warning(f"Version {target_version_id} not found for document {document_id}")
            return None
        else:
            # Rollback to previous version
            if len(self.versions[document_id]) >= 2:
                # Create a new version that's a copy of the previous
                previous = self.versions[document_id][-2]
                rolled_back = self.add_version(
                    content=previous.content,
                    quality_score=previous.quality_score,
                    document_id=document_id,
                    metadata={"rollback_from": self.versions[document_id][-1].version_id},
                    strategy_applied="rollback"
                )
                logger.info(f"Rolled back document {document_id} to previous version")
                return rolled_back
            else:
                logger.warning(f"No previous version to rollback to for document {document_id}")
                return None
    
    def compare_versions(
        self,
        version1_id: int,
        version2_id: int,
        document_id: Optional[str] = None
    ) -> Optional[VersionComparison]:
        """
        Compare two versions.
        
        Args:
            version1_id: First version ID
            version2_id: Second version ID
            document_id: Optional document ID for faster lookup
            
        Returns:
            VersionComparison or None if versions not found
        """
        v1 = self.get_version(version1_id, document_id)
        v2 = self.get_version(version2_id, document_id)
        
        if not v1 or not v2:
            logger.warning(f"Could not find versions {version1_id} and/or {version2_id}")
            return None
        
        # Generate diff
        diff = list(difflib.unified_diff(
            v1.content.splitlines(keepends=True),
            v2.content.splitlines(keepends=True),
            fromfile=f"Version {version1_id}",
            tofile=f"Version {version2_id}",
            lineterm=''
        ))
        
        # Count changes
        added = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
        removed = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))
        
        # Calculate similarity
        similarity = difflib.SequenceMatcher(None, v1.content, v2.content).ratio()
        
        # Find strategies applied between versions
        strategies = self._get_strategies_between(version1_id, version2_id, document_id)
        
        comparison = VersionComparison(
            version1_id=version1_id,
            version2_id=version2_id,
            quality_delta=v2.quality_score - v1.quality_score,
            content_diff=diff,
            added_lines=added,
            removed_lines=removed,
            modified_lines=min(added, removed),
            similarity_ratio=similarity,
            strategies_between=strategies
        )
        
        return comparison
    
    def _generate_changes_summary(
        self,
        document_id: str,
        new_content: str
    ) -> str:
        """Generate summary of changes from previous version."""
        if document_id not in self.versions or not self.versions[document_id]:
            return "Initial version"
        
        previous = self.versions[document_id][-1]
        
        # Calculate basic statistics
        prev_lines = previous.content.count('\n')
        new_lines = new_content.count('\n')
        prev_words = len(previous.content.split())
        new_words = len(new_content.split())
        
        summary_parts = []
        
        if new_lines > prev_lines:
            summary_parts.append(f"+{new_lines - prev_lines} lines")
        elif new_lines < prev_lines:
            summary_parts.append(f"-{prev_lines - new_lines} lines")
        
        if new_words > prev_words:
            summary_parts.append(f"+{new_words - prev_words} words")
        elif new_words < prev_words:
            summary_parts.append(f"-{prev_words - new_words} words")
        
        if not summary_parts:
            summary_parts.append("Content modified")
        
        return ", ".join(summary_parts)
    
    def _get_strategies_between(
        self,
        version1_id: int,
        version2_id: int,
        document_id: Optional[str] = None
    ) -> List[str]:
        """Get list of strategies applied between two versions."""
        strategies = []
        
        # Find document containing these versions
        target_doc = document_id
        if not target_doc:
            for doc_id, versions in self.versions.items():
                version_ids = [v.version_id for v in versions]
                if version1_id in version_ids and version2_id in version_ids:
                    target_doc = doc_id
                    break
        
        if not target_doc or target_doc not in self.versions:
            return strategies
        
        # Collect strategies between versions
        collecting = False
        for version in self.versions[target_doc]:
            if version.version_id == version1_id:
                collecting = True
                continue
            if collecting:
                if version.strategy_applied:
                    strategies.append(version.strategy_applied)
                if version.version_id == version2_id:
                    break
        
        return strategies
    
    def get_version_tree(
        self,
        document_id: str
    ) -> Dict[str, Any]:
        """
        Get version tree structure for visualization.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Tree structure as dictionary
        """
        if document_id not in self.versions:
            return {}
        
        versions = self.versions[document_id]
        tree = {
            "document_id": document_id,
            "total_versions": len(versions),
            "current_version": self.current_versions.get(document_id, -1),
            "versions": []
        }
        
        for i, version in enumerate(versions):
            node = {
                "index": i,
                "version_id": version.version_id,
                "quality_score": version.quality_score,
                "created_at": version.created_at.isoformat(),
                "strategy": version.strategy_applied,
                "is_current": i == self.current_versions.get(document_id, -1)
            }
            tree["versions"].append(node)
        
        return tree
    
    def export_history(
        self,
        output_path: Path,
        document_id: Optional[str] = None
    ) -> None:
        """
        Export history to JSON file.
        
        Args:
            output_path: Path to output file
            document_id: Optional specific document to export
        """
        if document_id:
            data = {
                "document_id": document_id,
                "versions": [v.to_dict() for v in self.versions.get(document_id, [])]
            }
        else:
            data = {
                doc_id: [v.to_dict() for v in versions]
                for doc_id, versions in self.versions.items()
            }
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Exported history to {output_path}")
    
    def import_history(
        self,
        input_path: Path
    ) -> None:
        """
        Import history from JSON file.
        
        Args:
            input_path: Path to input file
        """
        with open(input_path, 'r') as f:
            data = json.load(f)
        
        # Clear existing history
        self.versions.clear()
        self.current_versions.clear()
        
        # Import versions
        if "document_id" in data:
            # Single document format
            doc_id = data["document_id"]
            self.versions[doc_id] = []
            for v_data in data["versions"]:
                version = EnhancementVersion(
                    version_id=v_data["version_id"],
                    content=v_data.get("content_preview", ""),
                    quality_score=v_data["quality_score"],
                    created_at=datetime.fromisoformat(v_data["created_at"]),
                    metadata=v_data.get("metadata", {}),
                    parent_version_id=v_data.get("parent_version_id"),
                    strategy_applied=v_data.get("strategy_applied"),
                    changes_summary=v_data.get("changes_summary")
                )
                self.versions[doc_id].append(version)
            self.current_versions[doc_id] = len(self.versions[doc_id]) - 1
        else:
            # Multiple document format
            for doc_id, versions_data in data.items():
                self.versions[doc_id] = []
                for v_data in versions_data:
                    version = EnhancementVersion(
                        version_id=v_data["version_id"],
                        content=v_data.get("content_preview", ""),
                        quality_score=v_data["quality_score"],
                        created_at=datetime.fromisoformat(v_data["created_at"]),
                        metadata=v_data.get("metadata", {}),
                        parent_version_id=v_data.get("parent_version_id"),
                        strategy_applied=v_data.get("strategy_applied"),
                        changes_summary=v_data.get("changes_summary")
                    )
                    self.versions[doc_id].append(version)
                self.current_versions[doc_id] = len(self.versions[doc_id]) - 1
        
        # Update version counter
        all_version_ids = [
            v.version_id
            for versions in self.versions.values()
            for v in versions
        ]
        self.version_counter = max(all_version_ids) if all_version_ids else 0
        
        logger.info(f"Imported history from {input_path}")
    
    def clear_history(
        self,
        document_id: Optional[str] = None
    ) -> None:
        """
        Clear version history.
        
        Args:
            document_id: Optional specific document to clear
        """
        if document_id:
            if document_id in self.versions:
                del self.versions[document_id]
            if document_id in self.current_versions:
                del self.current_versions[document_id]
            logger.info(f"Cleared history for document {document_id}")
        else:
            self.versions.clear()
            self.current_versions.clear()
            self.version_counter = 0
            logger.info("Cleared all history")