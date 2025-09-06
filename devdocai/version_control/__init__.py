"""
M012: Version Control Integration Module

This module provides native Git integration for document versioning,
automatic commit tracking, and impact analysis for the DevDocAI system.

Features:
- Document commit tracking with metadata
- Automatic commit message generation
- Version tagging for major versions
- Change tracking and impact analysis
- Integration with TrackingMatrix (M005)

Author: DevDocAI Team
Version: 3.0.0
"""

from .version_control import VersionControlIntegration
from .commit_manager import CommitManager
from .change_tracker import ChangeTracker
from .message_generator import MessageGenerator
from .git_operations import GitOperations

__all__ = [
    'VersionControlIntegration',
    'CommitManager',
    'ChangeTracker',
    'MessageGenerator',
    'GitOperations',
]

# Module metadata
__version__ = '3.0.0'
__module_id__ = 'M012'
__module_name__ = 'Version Control Integration'