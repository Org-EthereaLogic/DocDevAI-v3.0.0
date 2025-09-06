#!/usr/bin/env python3
"""
M012 Version Control Integration - CLI Interface

Provides command-line interface for version control operations.
This module allows human verification of all version control functionality.

Usage:
    python -m devdocai.version_control [options]
"""

import sys
import argparse
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from .version_control import VersionControlIntegration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def display_info():
    """Display module information."""
    info = """
╔══════════════════════════════════════════════════════════════════╗
║            M012: Version Control Integration v3.0.0              ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  Native Git integration for document versioning and tracking     ║
║                                                                   ║
║  Features:                                                       ║
║  • Document commit tracking with metadata                        ║
║  • Automatic commit message generation                          ║
║  • Version tagging for major versions                           ║
║  • Change tracking and impact analysis                          ║
║  • Integration with TrackingMatrix (M005)                       ║
║                                                                   ║
║  Author: DevDocAI Team                                          ║
║  Module: M012 (Correctly Restored per SDD 5.7)                  ║
║                                                                   ║
╚══════════════════════════════════════════════════════════════════╝
    """
    print(info)


def display_status(vc: VersionControlIntegration):
    """Display repository status."""
    status = vc.get_repository_status()
    
    print("\n📊 Repository Status")
    print("=" * 50)
    print(f"Branch: {status.get('branch', 'unknown')}")
    print(f"Commit: {status.get('commit', 'none')[:8] if status.get('commit') else 'none'}")
    print(f"Dirty: {'Yes' if status.get('is_dirty') else 'No'}")
    
    if status.get('remote'):
        print(f"Remote: {status['remote']}")
        print(f"Ahead: {status.get('ahead', 0)} commits")
        print(f"Behind: {status.get('behind', 0)} commits")
    
    if status.get('modified_files'):
        print(f"\n📝 Modified Files ({len(status['modified_files'])})")
        for file in status['modified_files'][:10]:
            print(f"  M {file}")
        if len(status['modified_files']) > 10:
            print(f"  ... and {len(status['modified_files']) - 10} more")
    
    if status.get('staged_files'):
        print(f"\n✅ Staged Files ({len(status['staged_files'])})")
        for file in status['staged_files'][:10]:
            print(f"  A {file}")
        if len(status['staged_files']) > 10:
            print(f"  ... and {len(status['staged_files']) - 10} more")
    
    if status.get('untracked_files'):
        print(f"\n❓ Untracked Files ({len(status['untracked_files'])})")
        for file in status['untracked_files'][:10]:
            print(f"  ? {file}")
        if len(status['untracked_files']) > 10:
            print(f"  ... and {len(status['untracked_files']) - 10} more")


def commit_document(vc: VersionControlIntegration, document: str, message: Optional[str] = None, auto: bool = False):
    """Commit a document with tracking."""
    if not Path(document).exists():
        print(f"❌ Error: Document '{document}' not found")
        return
    
    print(f"\n📄 Committing Document: {document}")
    
    # Track changes first
    changes = vc.track_changes(document)
    print(f"Changes: +{changes.get('lines_added', 0)} -{changes.get('lines_removed', 0)}")
    
    if auto and not message:
        message = vc.generate_commit_message(document)
        print(f"Generated Message: {message}")
    
    if not message:
        print("❌ Error: No commit message provided (use --message or --auto-message)")
        return
    
    try:
        # Add metadata
        metadata = {
            'module': 'M012',
            'operation': 'manual_commit',
            'user': 'cli',
        }
        
        commit_hash = vc.commit_document(document, message, metadata)
        print(f"✅ Committed with hash: {commit_hash[:8]}")
        
        # Check if major version
        if vc.is_major_version(document):
            print("⚠️  This appears to be a major version change")
            print("   Consider tagging with: --tag --version X.0.0")
    
    except Exception as e:
        print(f"❌ Error: {e}")


def track_changes(vc: VersionControlIntegration, document: str):
    """Track and display document changes."""
    if not Path(document).exists():
        print(f"❌ Error: Document '{document}' not found")
        return
    
    print(f"\n🔍 Tracking Changes: {document}")
    print("=" * 50)
    
    changes = vc.track_changes(document)
    
    print(f"Status: {changes.get('status', 'unknown')}")
    print(f"Change Type: {changes.get('change_type', 'none')}")
    print(f"Lines Added: {changes.get('lines_added', 0)}")
    print(f"Lines Removed: {changes.get('lines_removed', 0)}")
    print(f"Total Lines: {changes.get('total_lines', 0)}")
    
    if changes.get('structural_changes'):
        print("⚠️  Structural Changes Detected")
    
    if changes.get('sections_affected'):
        print(f"\n📍 Affected Sections:")
        for section in changes['sections_affected']:
            print(f"  • {section}")
    
    # Analyze impact
    impact = vc.analyze_impact(document)
    print(f"\n💥 Impact Analysis:")
    print(f"  Level: {impact.get('impact_level', 'unknown')}")
    print(f"  Major Version: {'Yes' if impact.get('is_major_version') else 'No'}")
    
    if impact.get('related_documents'):
        print(f"\n🔗 Related Documents:")
        for doc in impact['related_documents'][:5]:
            print(f"  • {doc}")


def show_history(vc: VersionControlIntegration, document: str, limit: int = 10):
    """Show document commit history."""
    if not Path(document).exists():
        print(f"❌ Error: Document '{document}' not found")
        return
    
    print(f"\n📜 History: {document}")
    print("=" * 50)
    
    history = vc.get_document_history(document, limit)
    
    if not history:
        print("No history found")
        return
    
    for i, commit in enumerate(history, 1):
        print(f"\n{i}. {commit['short_hash']} - {commit['author']}")
        print(f"   Date: {commit['date']}")
        print(f"   Message: {commit['message']}")
        
        if commit.get('stats'):
            stats = commit['stats']
            if 'insertions' in stats or 'deletions' in stats:
                print(f"   Changes: +{stats.get('insertions', 0)} -{stats.get('deletions', 0)}")


def tag_version(vc: VersionControlIntegration, version: str, document: Optional[str] = None):
    """Tag a version."""
    print(f"\n🏷️  Tagging Version: {version}")
    
    if document:
        print(f"   For document: {document}")
    
    try:
        tag_name = vc.tag_version(version, document)
        print(f"✅ Created tag: {tag_name}")
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='M012 Version Control Integration - CLI Interface',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Commands
    parser.add_argument('--info', action='store_true',
                       help='Display module information')
    parser.add_argument('--status', action='store_true',
                       help='Show repository status')
    parser.add_argument('--commit', action='store_true',
                       help='Commit a document')
    parser.add_argument('--track', action='store_true',
                       help='Track changes for a document')
    parser.add_argument('--history', action='store_true',
                       help='Show document history')
    parser.add_argument('--tag', action='store_true',
                       help='Tag a version')
    
    # Options
    parser.add_argument('--document', type=str,
                       help='Document path')
    parser.add_argument('--message', type=str,
                       help='Commit message')
    parser.add_argument('--auto-message', action='store_true',
                       help='Generate commit message automatically')
    parser.add_argument('--version', type=str,
                       help='Version string for tagging')
    parser.add_argument('--limit', type=int, default=10,
                       help='Limit for history (default: 10)')
    parser.add_argument('--repo', type=str, default='.',
                       help='Repository path (default: current directory)')
    
    # Debugging
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Set debug level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Show info if requested or no command given
    if args.info or not any([args.status, args.commit, args.track, args.history, args.tag]):
        display_info()
        return 0
    
    try:
        # Initialize Version Control Integration
        vc = VersionControlIntegration(args.repo)
        
        # Execute commands
        if args.status:
            display_status(vc)
        
        elif args.commit:
            if not args.document:
                print("❌ Error: --document required for commit")
                return 1
            commit_document(vc, args.document, args.message, args.auto_message)
        
        elif args.track:
            if not args.document:
                print("❌ Error: --document required for tracking")
                return 1
            track_changes(vc, args.document)
        
        elif args.history:
            if not args.document:
                print("❌ Error: --document required for history")
                return 1
            show_history(vc, args.document, args.limit)
        
        elif args.tag:
            if not args.version:
                print("❌ Error: --version required for tagging")
                return 1
            tag_version(vc, args.version, args.document)
        
        return 0
    
    except ValueError as e:
        print(f"❌ Error: {e}")
        print("   Hint: Make sure you're in a Git repository or use --repo")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())