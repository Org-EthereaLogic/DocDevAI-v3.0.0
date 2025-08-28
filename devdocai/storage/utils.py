"""
Utility functions for M002 Local Storage System.

Provides helper functions for UUID generation, content processing,
path handling, and diff calculation.
"""

import os
import re
import uuid
import json
import hashlib
import difflib
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


def generate_uuid() -> str:
    """Generate a unique UUID string."""
    return str(uuid.uuid4())


def calculate_hash(content: str) -> str:
    """Calculate SHA-256 hash of content."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def sanitize_path(path: str) -> str:
    """
    Sanitize file path to prevent directory traversal attacks.
    
    Args:
        path: Input path
        
    Returns:
        Sanitized path
    """
    # Convert to Path object for normalization
    p = Path(path)
    
    # Remove any parent directory references
    parts = []
    for part in p.parts:
        if part not in ('.', '..', ''):
            # Remove any special characters that could be problematic
            clean_part = re.sub(r'[^\w\-_. ]', '', part)
            if clean_part:
                parts.append(clean_part)
    
    return str(Path(*parts)) if parts else ''


def ensure_directory(path: Path) -> bool:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Directory path
        
    Returns:
        True if directory exists or was created
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {path}: {e}")
        return False


def calculate_diff(old_content: str, new_content: str, 
                  context_lines: int = 3) -> str:
    """
    Calculate diff between two content versions.
    
    Args:
        old_content: Previous content
        new_content: New content
        context_lines: Number of context lines in diff
        
    Returns:
        JSON-encoded diff
    """
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        n=context_lines,
        lineterm=''
    )
    
    # Convert to list for JSON serialization
    diff_lines = list(diff)
    
    # Create a structured diff object
    diff_obj = {
        'type': 'unified',
        'context_lines': context_lines,
        'old_size': len(old_content),
        'new_size': len(new_content),
        'changes': diff_lines[:1000]  # Limit diff size
    }
    
    return json.dumps(diff_obj)


def apply_diff(content: str, diff_json: str) -> str:
    """
    Apply a diff to content to recreate a version.
    
    Args:
        content: Base content
        diff_json: JSON-encoded diff
        
    Returns:
        Reconstructed content
    """
    # This is a simplified implementation
    # In production, you'd want to use a proper patch library
    logger.warning("apply_diff is not fully implemented - returning original content")
    return content


def tokenize_content(content: str, max_tokens: int = 10000) -> str:
    """
    Tokenize content for full-text search.
    
    Args:
        content: Input content
        max_tokens: Maximum number of tokens
        
    Returns:
        Space-separated tokens
    """
    # Basic tokenization - can be enhanced with NLP libraries
    # Remove special characters and normalize
    text = re.sub(r'[^\w\s]', ' ', content.lower())
    
    # Split into words
    words = text.split()
    
    # Remove stop words (basic list)
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 
                  'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was',
                  'are', 'were', 'been', 'be', 'have', 'has', 'had', 'do',
                  'does', 'did', 'will', 'would', 'could', 'should', 'may',
                  'might', 'must', 'can', 'shall', 'if', 'then', 'else'}
    
    tokens = [w for w in words if w not in stop_words and len(w) > 2]
    
    # Limit number of tokens
    if len(tokens) > max_tokens:
        tokens = tokens[:max_tokens]
    
    return ' '.join(tokens)


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def validate_document_content(content: str, max_size: int = 10485760) -> Tuple[bool, Optional[str]]:
    """
    Validate document content.
    
    Args:
        content: Document content
        max_size: Maximum size in bytes (default 10MB)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not content:
        return True, None
    
    # Check size
    size = len(content.encode('utf-8'))
    if size > max_size:
        return False, f"Content size {format_file_size(size)} exceeds maximum {format_file_size(max_size)}"
    
    # Check for binary content
    if '\x00' in content:
        return False, "Content appears to be binary"
    
    # Check encoding
    try:
        content.encode('utf-8')
    except UnicodeEncodeError:
        return False, "Content contains invalid UTF-8 characters"
    
    return True, None


def extract_metadata_from_content(content: str) -> Dict[str, Any]:
    """
    Extract metadata from document content.
    
    Args:
        content: Document content
        
    Returns:
        Extracted metadata dictionary
    """
    metadata = {}
    
    # Extract frontmatter (YAML/TOML style)
    frontmatter_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if frontmatter_match:
        try:
            import yaml
            fm_data = yaml.safe_load(frontmatter_match.group(1))
            if isinstance(fm_data, dict):
                metadata.update(fm_data)
        except:
            pass
    
    # Extract headers (Markdown style)
    headers = re.findall(r'^#{1,6}\s+(.+)$', content, re.MULTILINE)
    if headers:
        metadata['headers'] = headers[:10]  # First 10 headers
    
    # Count various elements
    metadata['word_count'] = len(content.split())
    metadata['line_count'] = len(content.splitlines())
    metadata['char_count'] = len(content)
    
    # Detect code blocks
    code_blocks = re.findall(r'```(\w+)?\n', content)
    if code_blocks:
        languages = [lang for lang in code_blocks if lang]
        if languages:
            metadata['code_languages'] = list(set(languages))
    
    # Detect links
    links = re.findall(r'https?://[^\s\)]+', content)
    if links:
        metadata['external_links'] = len(links)
    
    return metadata


def secure_delete(file_path: Path, passes: int = 3) -> bool:
    """
    Securely delete a file by overwriting it multiple times.
    
    Args:
        file_path: Path to file
        passes: Number of overwrite passes
        
    Returns:
        Success status
    """
    if not file_path.exists():
        return False
    
    try:
        file_size = file_path.stat().st_size
        
        with open(file_path, 'ba+', buffering=0) as f:
            for _ in range(passes):
                # Write random data
                f.seek(0)
                f.write(os.urandom(file_size))
                f.flush()
                os.fsync(f.fileno())
        
        # Finally remove the file
        file_path.unlink()
        return True
        
    except Exception as e:
        logger.error(f"Secure delete failed for {file_path}: {e}")
        return False


def create_backup(source_path: Path, backup_dir: Path, 
                 keep_versions: int = 5) -> Optional[Path]:
    """
    Create a backup of a file.
    
    Args:
        source_path: Source file path
        backup_dir: Backup directory
        keep_versions: Number of backup versions to keep
        
    Returns:
        Path to backup file or None on failure
    """
    if not source_path.exists():
        logger.error(f"Source file {source_path} does not exist")
        return None
    
    ensure_directory(backup_dir)
    
    # Create backup filename with timestamp
    timestamp = uuid.uuid4().hex[:8]
    backup_name = f"{source_path.stem}_{timestamp}{source_path.suffix}"
    backup_path = backup_dir / backup_name
    
    try:
        shutil.copy2(source_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
        
        # Clean old backups
        pattern = f"{source_path.stem}_*{source_path.suffix}"
        backups = sorted(backup_dir.glob(pattern), 
                        key=lambda p: p.stat().st_mtime,
                        reverse=True)
        
        # Keep only the specified number of versions
        for old_backup in backups[keep_versions:]:
            old_backup.unlink()
            logger.info(f"Removed old backup: {old_backup}")
        
        return backup_path
        
    except Exception as e:
        logger.error(f"Backup creation failed: {e}")
        return None


def restore_backup(backup_path: Path, target_path: Path) -> bool:
    """
    Restore a file from backup.
    
    Args:
        backup_path: Backup file path
        target_path: Target restoration path
        
    Returns:
        Success status
    """
    if not backup_path.exists():
        logger.error(f"Backup file {backup_path} does not exist")
        return False
    
    try:
        # Create backup of current file if it exists
        if target_path.exists():
            temp_backup = target_path.with_suffix('.tmp')
            shutil.copy2(target_path, temp_backup)
        
        # Restore from backup
        shutil.copy2(backup_path, target_path)
        logger.info(f"Restored from backup: {backup_path} -> {target_path}")
        
        # Remove temporary backup
        if target_path.exists() and temp_backup.exists():
            temp_backup.unlink()
        
        return True
        
    except Exception as e:
        logger.error(f"Restore failed: {e}")
        return False


def estimate_storage_requirements(num_documents: int, 
                                 avg_doc_size: int = 5000,
                                 versions_per_doc: int = 5) -> Dict[str, int]:
    """
    Estimate storage requirements for documents.
    
    Args:
        num_documents: Number of documents
        avg_doc_size: Average document size in bytes
        versions_per_doc: Average versions per document
        
    Returns:
        Storage estimates
    """
    # Base document storage
    document_storage = num_documents * avg_doc_size
    
    # Version storage (assume 30% size for diffs)
    version_storage = num_documents * versions_per_doc * int(avg_doc_size * 0.3)
    
    # Metadata (assume 10% of document size)
    metadata_storage = num_documents * int(avg_doc_size * 0.1)
    
    # Indexes (assume 20% of total content)
    index_storage = int((document_storage + version_storage) * 0.2)
    
    # Total with 20% overhead
    total = int((document_storage + version_storage + metadata_storage + index_storage) * 1.2)
    
    return {
        'documents': document_storage,
        'versions': version_storage,
        'metadata': metadata_storage,
        'indexes': index_storage,
        'total': total,
        'formatted_total': format_file_size(total)
    }