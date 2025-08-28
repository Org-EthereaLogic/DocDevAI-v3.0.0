"""
Unit tests for M002 storage utilities.

Tests helper functions for UUID generation, hashing, path handling,
diff calculation, and other utilities.
"""

import os
import json
import tempfile
import shutil
import pytest
from pathlib import Path

from devdocai.storage.utils import (
    generate_uuid, calculate_hash, sanitize_path, ensure_directory,
    calculate_diff, apply_diff, tokenize_content, format_file_size,
    validate_document_content, extract_metadata_from_content,
    secure_delete, create_backup, restore_backup,
    estimate_storage_requirements
)


class TestUUIDGeneration:
    """Test UUID generation."""
    
    def test_generate_uuid(self):
        """Test UUID generation."""
        uuid1 = generate_uuid()
        uuid2 = generate_uuid()
        
        assert uuid1 is not None
        assert uuid2 is not None
        assert uuid1 != uuid2
        assert len(uuid1) == 36  # Standard UUID format
        assert '-' in uuid1  # Contains hyphens
    
    def test_uuid_format(self):
        """Test UUID format validity."""
        import re
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        )
        
        uuid = generate_uuid()
        assert uuid_pattern.match(uuid) is not None


class TestHashing:
    """Test hash calculation."""
    
    def test_calculate_hash(self):
        """Test SHA-256 hash calculation."""
        content = "Test content for hashing"
        hash1 = calculate_hash(content)
        hash2 = calculate_hash(content)
        
        assert hash1 == hash2  # Same content, same hash
        assert len(hash1) == 64  # SHA-256 produces 64 hex characters
    
    def test_hash_different_content(self):
        """Test hash for different content."""
        hash1 = calculate_hash("Content 1")
        hash2 = calculate_hash("Content 2")
        
        assert hash1 != hash2
    
    def test_hash_unicode_content(self):
        """Test hash with Unicode content."""
        content = "Unicode content: 你好 мир 🌍"
        hash_val = calculate_hash(content)
        
        assert hash_val is not None
        assert len(hash_val) == 64


class TestPathHandling:
    """Test path sanitization and directory handling."""
    
    def test_sanitize_path_basic(self):
        """Test basic path sanitization."""
        path = "documents/test.txt"
        sanitized = sanitize_path(path)
        
        assert sanitized == "documents/test.txt"
    
    def test_sanitize_path_parent_traversal(self):
        """Test prevention of parent directory traversal."""
        dangerous_paths = [
            "../etc/passwd",
            "../../sensitive",
            "./../config",
            "docs/../../../etc"
        ]
        
        for path in dangerous_paths:
            sanitized = sanitize_path(path)
            assert ".." not in sanitized
            assert not sanitized.startswith("/")
    
    def test_sanitize_path_special_chars(self):
        """Test removal of special characters."""
        path = "docs/file<>|*.txt"
        sanitized = sanitize_path(path)
        
        assert '<' not in sanitized
        assert '>' not in sanitized
        assert '|' not in sanitized
        assert '*' not in sanitized
    
    def test_ensure_directory(self):
        """Test directory creation."""
        temp_dir = Path(tempfile.gettempdir()) / f"test_{generate_uuid()}"
        
        try:
            assert not temp_dir.exists()
            
            result = ensure_directory(temp_dir)
            assert result is True
            assert temp_dir.exists()
            assert temp_dir.is_dir()
            
            # Should handle existing directory
            result = ensure_directory(temp_dir)
            assert result is True
            
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)


class TestDiffOperations:
    """Test diff calculation and application."""
    
    def test_calculate_diff(self):
        """Test diff calculation between versions."""
        old_content = "Line 1\nLine 2\nLine 3"
        new_content = "Line 1\nLine 2 modified\nLine 3\nLine 4"
        
        diff_json = calculate_diff(old_content, new_content)
        diff_obj = json.loads(diff_json)
        
        assert diff_obj['type'] == 'unified'
        assert diff_obj['old_size'] == len(old_content)
        assert diff_obj['new_size'] == len(new_content)
        assert 'changes' in diff_obj
        assert len(diff_obj['changes']) > 0
    
    def test_calculate_diff_identical(self):
        """Test diff for identical content."""
        content = "Same content"
        
        diff_json = calculate_diff(content, content)
        diff_obj = json.loads(diff_json)
        
        assert diff_obj['old_size'] == diff_obj['new_size']
        # Changes might be empty or minimal
    
    def test_calculate_diff_context(self):
        """Test diff with custom context lines."""
        old = "A\nB\nC\nD\nE"
        new = "A\nB\nX\nD\nE"
        
        diff_json = calculate_diff(old, new, context_lines=1)
        diff_obj = json.loads(diff_json)
        
        assert diff_obj['context_lines'] == 1
    
    def test_apply_diff(self):
        """Test applying diff (simplified test)."""
        content = "Original content"
        diff_json = json.dumps({
            'type': 'unified',
            'changes': []
        })
        
        # Note: apply_diff is not fully implemented
        result = apply_diff(content, diff_json)
        assert result == content  # Returns original as fallback


class TestTokenization:
    """Test content tokenization."""
    
    def test_tokenize_basic(self):
        """Test basic tokenization."""
        content = "This is a test document with some content."
        tokens = tokenize_content(content)
        
        assert tokens is not None
        assert isinstance(tokens, str)
        # Should remove stop words like "is", "a", "the"
        assert "test" in tokens
        assert "document" in tokens
        assert "content" in tokens
    
    def test_tokenize_stop_words(self):
        """Test stop word removal."""
        content = "The quick brown fox jumps over the lazy dog"
        tokens = tokenize_content(content)
        
        # Stop words should be removed
        assert "the" not in tokens.lower().split()
        assert "over" not in tokens.lower().split()
        # Content words should remain
        assert "quick" in tokens.lower()
        assert "brown" in tokens.lower()
        assert "fox" in tokens.lower()
    
    def test_tokenize_max_tokens(self):
        """Test token limit."""
        # Create content with many words
        content = " ".join([f"word{i}" for i in range(20000)])
        
        tokens = tokenize_content(content, max_tokens=100)
        token_list = tokens.split()
        
        assert len(token_list) <= 100
    
    def test_tokenize_special_chars(self):
        """Test tokenization with special characters."""
        content = "Test@email.com and http://website.org with #hashtag"
        tokens = tokenize_content(content)
        
        # Special chars should be removed/normalized
        assert "@" not in tokens
        assert "#" not in tokens
        assert "://" not in tokens


class TestFileSizeFormatting:
    """Test file size formatting."""
    
    def test_format_bytes(self):
        """Test formatting bytes."""
        assert format_file_size(500) == "500.00 B"
        assert format_file_size(1023) == "1023.00 B"
    
    def test_format_kilobytes(self):
        """Test formatting kilobytes."""
        assert format_file_size(1024) == "1.00 KB"
        assert format_file_size(1536) == "1.50 KB"
        assert format_file_size(10240) == "10.00 KB"
    
    def test_format_megabytes(self):
        """Test formatting megabytes."""
        assert format_file_size(1048576) == "1.00 MB"
        assert format_file_size(5242880) == "5.00 MB"
    
    def test_format_gigabytes(self):
        """Test formatting gigabytes."""
        assert format_file_size(1073741824) == "1.00 GB"
    
    def test_format_large_sizes(self):
        """Test formatting very large sizes."""
        tb = 1024 ** 4
        assert format_file_size(tb) == "1.00 TB"
        
        pb = 1024 ** 5
        assert format_file_size(pb) == "1.00 PB"


class TestContentValidation:
    """Test document content validation."""
    
    def test_validate_valid_content(self):
        """Test validation of valid content."""
        content = "This is valid content"
        is_valid, error = validate_document_content(content)
        
        assert is_valid is True
        assert error is None
    
    def test_validate_empty_content(self):
        """Test validation of empty content."""
        is_valid, error = validate_document_content("")
        
        assert is_valid is True
        assert error is None
    
    def test_validate_none_content(self):
        """Test validation of None content."""
        is_valid, error = validate_document_content(None)
        
        assert is_valid is True
        assert error is None
    
    def test_validate_oversized_content(self):
        """Test validation of oversized content."""
        large_content = "x" * (11 * 1024 * 1024)  # 11MB
        is_valid, error = validate_document_content(large_content)
        
        assert is_valid is False
        assert "exceeds maximum" in error
    
    def test_validate_binary_content(self):
        """Test validation of binary content."""
        binary_content = "Text with null byte: \x00"
        is_valid, error = validate_document_content(binary_content)
        
        assert is_valid is False
        assert "binary" in error.lower()
    
    def test_validate_custom_max_size(self):
        """Test validation with custom max size."""
        content = "x" * 1000
        
        # Should pass with higher limit
        is_valid, error = validate_document_content(content, max_size=2000)
        assert is_valid is True
        
        # Should fail with lower limit
        is_valid, error = validate_document_content(content, max_size=500)
        assert is_valid is False


class TestMetadataExtraction:
    """Test metadata extraction from content."""
    
    def test_extract_basic_metadata(self):
        """Test basic metadata extraction."""
        content = "This is a test document.\nWith multiple lines."
        metadata = extract_metadata_from_content(content)
        
        assert metadata['word_count'] == 8
        assert metadata['line_count'] == 2
        assert metadata['char_count'] == len(content)
    
    def test_extract_frontmatter(self):
        """Test YAML frontmatter extraction."""
        content = """---
title: Test Document
author: John Doe
tags: [test, sample]
---

# Content starts here
This is the actual content."""
        
        metadata = extract_metadata_from_content(content)
        
        assert metadata.get('title') == 'Test Document'
        assert metadata.get('author') == 'John Doe'
        assert metadata.get('tags') == ['test', 'sample']
    
    def test_extract_headers(self):
        """Test Markdown header extraction."""
        content = """# Main Title
## Section 1
Some content
### Subsection 1.1
## Section 2
### Subsection 2.1"""
        
        metadata = extract_metadata_from_content(content)
        
        assert 'headers' in metadata
        assert 'Main Title' in metadata['headers']
        assert 'Section 1' in metadata['headers']
        assert 'Subsection 1.1' in metadata['headers']
    
    def test_extract_code_languages(self):
        """Test code language detection."""
        content = """
```python
def hello():
    pass
```

```javascript
console.log("test");
```

```python
# Another Python block
```
"""
        
        metadata = extract_metadata_from_content(content)
        
        assert 'code_languages' in metadata
        assert 'python' in metadata['code_languages']
        assert 'javascript' in metadata['code_languages']
    
    def test_extract_links(self):
        """Test external link detection."""
        content = """
Check out https://example.com for more info.
Also see http://test.org and https://github.com/user/repo
"""
        
        metadata = extract_metadata_from_content(content)
        
        assert metadata.get('external_links') == 3


class TestFileOperations:
    """Test secure file operations."""
    
    def test_secure_delete(self):
        """Test secure file deletion."""
        # Create temporary file
        temp_file = Path(tempfile.gettempdir()) / f"test_{generate_uuid()}.txt"
        temp_file.write_text("Sensitive data")
        
        assert temp_file.exists()
        
        # Securely delete
        result = secure_delete(temp_file, passes=2)
        
        assert result is True
        assert not temp_file.exists()
    
    def test_secure_delete_nonexistent(self):
        """Test secure delete of non-existent file."""
        temp_file = Path(tempfile.gettempdir()) / "nonexistent.txt"
        
        result = secure_delete(temp_file)
        assert result is False
    
    def test_create_backup(self):
        """Test file backup creation."""
        # Create source file
        source = Path(tempfile.gettempdir()) / f"source_{generate_uuid()}.txt"
        source.write_text("Original content")
        
        backup_dir = Path(tempfile.gettempdir()) / f"backup_{generate_uuid()}"
        
        try:
            # Create backup
            backup_path = create_backup(source, backup_dir)
            
            assert backup_path is not None
            assert backup_path.exists()
            assert backup_path.read_text() == "Original content"
            assert backup_path.parent == backup_dir
            
        finally:
            # Cleanup
            if source.exists():
                source.unlink()
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
    
    def test_create_backup_versioning(self):
        """Test backup versioning."""
        source = Path(tempfile.gettempdir()) / f"source_{generate_uuid()}.txt"
        source.write_text("Content")
        
        backup_dir = Path(tempfile.gettempdir()) / f"backup_{generate_uuid()}"
        
        try:
            # Create multiple backups
            backups = []
            for i in range(3):
                source.write_text(f"Content {i}")
                backup = create_backup(source, backup_dir, keep_versions=2)
                if backup:
                    backups.append(backup)
            
            # Should keep only 2 versions
            existing_backups = list(backup_dir.glob(f"{source.stem}_*.txt"))
            assert len(existing_backups) == 2
            
        finally:
            # Cleanup
            if source.exists():
                source.unlink()
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
    
    def test_restore_backup(self):
        """Test backup restoration."""
        backup_file = Path(tempfile.gettempdir()) / f"backup_{generate_uuid()}.txt"
        backup_file.write_text("Backup content")
        
        target_file = Path(tempfile.gettempdir()) / f"target_{generate_uuid()}.txt"
        
        try:
            # Restore backup
            result = restore_backup(backup_file, target_file)
            
            assert result is True
            assert target_file.exists()
            assert target_file.read_text() == "Backup content"
            
        finally:
            # Cleanup
            for file in [backup_file, target_file]:
                if file.exists():
                    file.unlink()
    
    def test_restore_backup_with_existing(self):
        """Test restoring over existing file."""
        backup_file = Path(tempfile.gettempdir()) / f"backup_{generate_uuid()}.txt"
        backup_file.write_text("Backup content")
        
        target_file = Path(tempfile.gettempdir()) / f"target_{generate_uuid()}.txt"
        target_file.write_text("Current content")
        
        try:
            # Restore should overwrite
            result = restore_backup(backup_file, target_file)
            
            assert result is True
            assert target_file.read_text() == "Backup content"
            
        finally:
            # Cleanup
            for file in [backup_file, target_file]:
                if file.exists():
                    file.unlink()


class TestStorageEstimation:
    """Test storage requirement estimation."""
    
    def test_estimate_basic(self):
        """Test basic storage estimation."""
        estimate = estimate_storage_requirements(
            num_documents=100,
            avg_doc_size=5000,
            versions_per_doc=5
        )
        
        assert estimate['documents'] == 100 * 5000
        assert estimate['versions'] > 0
        assert estimate['metadata'] > 0
        assert estimate['indexes'] > 0
        assert estimate['total'] > estimate['documents']
        assert 'formatted_total' in estimate
    
    def test_estimate_large_scale(self):
        """Test large scale estimation."""
        estimate = estimate_storage_requirements(
            num_documents=10000,
            avg_doc_size=10000,
            versions_per_doc=10
        )
        
        # Total should be reasonable
        assert estimate['total'] > 100000000  # > 100MB
        assert estimate['total'] < 10000000000  # < 10GB
        
        # Check formatting
        assert 'MB' in estimate['formatted_total'] or 'GB' in estimate['formatted_total']
    
    def test_estimate_proportions(self):
        """Test storage proportion calculations."""
        estimate = estimate_storage_requirements(
            num_documents=1000,
            avg_doc_size=1000,
            versions_per_doc=5
        )
        
        # Versions should be about 30% of document size per version
        expected_versions = 1000 * 5 * int(1000 * 0.3)
        assert abs(estimate['versions'] - expected_versions) < 1000
        
        # Metadata should be about 10% of document size
        expected_metadata = 1000 * int(1000 * 0.1)
        assert abs(estimate['metadata'] - expected_metadata) < 1000