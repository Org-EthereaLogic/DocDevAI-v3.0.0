"""
M002: Local Storage System - Secure, high-performance local storage for DevDocAI.

This module provides SQLite-based storage with SQLCipher encryption, document versioning,
metadata indexing, and full-text search capabilities.

Performance targets:
- Read: 200,000+ queries/second
- Write: 50,000+ transactions/second
- Latency: Sub-millisecond for indexed queries
- Capacity: Support databases up to 100GB
"""

from .local_storage import LocalStorageSystem
from .models import Document, DocumentVersion, Metadata
from .migrations import MigrationManager

__all__ = [
    'LocalStorageSystem',
    'Document',
    'DocumentVersion',
    'Metadata',
    'MigrationManager'
]

__version__ = '3.0.0'