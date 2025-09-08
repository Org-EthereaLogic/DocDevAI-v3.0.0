"""
M002 Local Storage System - Core Implementation
DevDocAI v3.0.0 - Pass 1: Core functionality with 95% test coverage target

Provides encrypted local storage using SQLite with SQLCipher extension.
Implements AES-256-GCM encryption with unique IVs and HMAC integrity checks.
"""

import sqlite3
import json
import hashlib
import hmac
import secrets
import base64
import logging
import threading
from typing import Optional, Dict, Any, List, Union
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from queue import Queue

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)


# Custom Exceptions
class StorageError(Exception):
    """Base exception for storage operations."""
    def __init__(self, message: str, error_code: str = "STORAGE_ERROR", **kwargs):
        super().__init__(message)
        self.error_code = error_code
        self.details = kwargs


class EncryptionError(StorageError):
    """Encryption/decryption error."""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, "ENCRYPTION_ERROR", **kwargs)


class IntegrityError(StorageError):
    """Data integrity verification error."""
    def __init__(self, message: str, document_id: Optional[str] = None, **kwargs):
        super().__init__(message, "INTEGRITY_ERROR", document_id=document_id, **kwargs)
        self.document_id = document_id


class TransactionError(StorageError):
    """Transaction management error."""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, "TRANSACTION_ERROR", **kwargs)


@dataclass
class DocumentMetadata:
    """Document metadata structure."""
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    version: str = "1.0"
    custom: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        # Merge custom fields into main dict
        if data.get('custom'):
            data.update(data.pop('custom'))
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocumentMetadata':
        """Create from dictionary."""
        known_fields = {'author', 'tags', 'version'}
        custom = {k: v for k, v in data.items() if k not in known_fields}
        
        return cls(
            author=data.get('author'),
            tags=data.get('tags', []),
            version=data.get('version', '1.0'),
            custom=custom
        )


@dataclass
class Document:
    """Document model with required fields."""
    id: str
    content: str
    type: str = "text"
    metadata: Optional[Union[Dict[str, Any], DocumentMetadata]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate and initialize fields."""
        if not isinstance(self.id, str):
            raise ValueError("Document id must be a string")
        if not self.content:
            raise ValueError("Document content cannot be empty")
        
        # Initialize timestamps
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        
        # Convert metadata dict to DocumentMetadata
        if isinstance(self.metadata, dict):
            self.metadata = DocumentMetadata.from_dict(self.metadata)
        elif self.metadata is None:
            self.metadata = DocumentMetadata()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert document to dictionary for storage."""
        return {
            'id': self.id,
            'content': self.content,
            'type': self.type,
            'metadata': self.metadata.to_dict() if self.metadata else {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Document':
        """Create document from dictionary."""
        created_at = None
        updated_at = None
        
        if data.get('created_at'):
            created_at = datetime.fromisoformat(data['created_at'])
        if data.get('updated_at'):
            updated_at = datetime.fromisoformat(data['updated_at'])
        
        return cls(
            id=data['id'],
            content=data['content'],
            type=data.get('type', 'text'),
            metadata=data.get('metadata', {}),
            created_at=created_at,
            updated_at=updated_at
        )


class StorageManager:
    """
    Manages encrypted document storage with SQLCipher.
    Integrates with M001 ConfigurationManager for settings.
    """
    
    def __init__(self, config):
        """
        Initialize storage manager with configuration.
        
        Args:
            config: ConfigurationManager instance from M001
        """
        self.config = config
        self._lock = threading.RLock()
        self._transaction_level = 0
        self._connection_pool = Queue(maxsize=5)
        
        # Get storage configuration
        self.db_path = config.get("storage.database_path", ":memory:")
        self._encryption_enabled = config.get("storage.encryption_enabled", True)
        
        # Setup encryption
        self._setup_encryption()
        
        # Initialize database
        self._conn = self._create_connection()
        self._initialize_database()
        
        logger.info(f"StorageManager initialized with database: {self.db_path}")
    
    def _setup_encryption(self):
        """Setup encryption keys and cipher."""
        if self._encryption_enabled:
            # Get or generate encryption key
            key_str = self.config.get("storage.encryption_key")
            if key_str:
                # Derive key from string
                self._encryption_key = hashlib.pbkdf2_hmac(
                    'sha256',
                    key_str.encode(),
                    b'devdocai_storage_salt',
                    100000,
                    dklen=32
                )
            else:
                # Generate new key
                self._encryption_key = secrets.token_bytes(32)
            
            # Initialize AES-GCM cipher
            self._cipher = AESGCM(self._encryption_key)
            
            # HMAC key for integrity
            self._hmac_key = hashlib.pbkdf2_hmac(
                'sha256',
                self._encryption_key,
                b'devdocai_hmac_salt',
                100000,
                dklen=32
            )
        else:
            self._encryption_key = None
            self._cipher = None
            self._hmac_key = None
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create SQLite connection with SQLCipher if available."""
        try:
            # Try to use SQLCipher
            # Set isolation_level to None for manual transaction control
            conn = sqlite3.connect(self.db_path, check_same_thread=False, isolation_level=None)
            
            if self._encryption_enabled and self.db_path != ":memory:":
                # Set SQLCipher pragmas - note: standard SQLite doesn't support key pragma
                try:
                    key = self.config.get("storage.encryption_key", "default_key")
                    conn.execute(f"PRAGMA key = '{key}'")
                    conn.execute("PRAGMA cipher = 'aes-256-gcm'")
                    conn.execute("PRAGMA kdf_iter = 256000")
                except:
                    # SQLCipher not available, continue with standard SQLite
                    pass
            
            # Enable foreign keys and WAL mode for better concurrency
            conn.execute("PRAGMA foreign_keys = ON")
            if self.db_path != ":memory:":
                try:
                    conn.execute("PRAGMA journal_mode = WAL")
                except:
                    pass  # WAL mode might not be available
            
            return conn
            
        except Exception as e:
            logger.warning(f"SQLCipher not available, using standard SQLite: {e}")
            # Fallback to standard SQLite with manual transaction control
            conn = sqlite3.connect(self.db_path, check_same_thread=False, isolation_level=None)
            conn.execute("PRAGMA foreign_keys = ON")
            return conn
    
    def _initialize_database(self):
        """Create database tables if they don't exist."""
        with self._lock:
            cursor = self._conn.cursor()
            
            # Documents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    encrypted_content BLOB NOT NULL,
                    iv BLOB NOT NULL,
                    hmac TEXT NOT NULL,
                    type TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    version INTEGER DEFAULT 1
                )
            """)
            
            # Document metadata table (searchable)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS document_metadata (
                    document_id TEXT PRIMARY KEY,
                    metadata_json TEXT NOT NULL,
                    author TEXT,
                    tags TEXT,
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                )
            """)
            
            # Document versions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS document_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    encrypted_content BLOB NOT NULL,
                    iv BLOB NOT NULL,
                    hmac TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_type 
                ON documents(type)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_created 
                ON documents(created_at)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_metadata_author 
                ON document_metadata(author)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_versions_document 
                ON document_versions(document_id, version)
            """)
            
            self._conn.commit()
    
    def _encrypt_content(self, content: str) -> tuple[bytes, bytes, str]:
        """
        Encrypt content with AES-256-GCM.
        
        Returns:
            Tuple of (encrypted_content, iv, hmac)
        """
        if not self._encryption_enabled:
            # No encryption, return content as-is
            content_bytes = content.encode('utf-8')
            return content_bytes, b'', ''
        
        # Generate unique IV for this document
        iv = secrets.token_bytes(12)
        
        # Encrypt content
        content_bytes = content.encode('utf-8')
        encrypted = self._cipher.encrypt(iv, content_bytes, None)
        
        # Calculate HMAC for integrity
        h = hmac.new(self._hmac_key, digestmod=hashlib.sha256)
        h.update(iv)
        h.update(encrypted)
        hmac_digest = h.hexdigest()
        
        return encrypted, iv, hmac_digest
    
    def _decrypt_content(self, encrypted: bytes, iv: bytes, hmac_str: str) -> str:
        """
        Decrypt content and verify integrity.
        
        Raises:
            IntegrityError: If HMAC verification fails
            EncryptionError: If decryption fails
        """
        if not self._encryption_enabled:
            # No encryption, return as-is
            return encrypted.decode('utf-8')
        
        # Verify HMAC first
        h = hmac.new(self._hmac_key, digestmod=hashlib.sha256)
        h.update(iv)
        h.update(encrypted)
        expected_hmac = h.hexdigest()
        
        if not hmac.compare_digest(hmac_str, expected_hmac):
            raise IntegrityError(
                "HMAC verification failed - data may be tampered",
                expected_hmac=expected_hmac,
                actual_hmac=hmac_str
            )
        
        # Decrypt content
        try:
            decrypted = self._cipher.decrypt(iv, encrypted, None)
            return decrypted.decode('utf-8')
        except Exception as e:
            raise EncryptionError(f"Failed to decrypt content: {e}")
    
    def save_document(self, document: Document) -> bool:
        """
        Save encrypted document to storage.
        
        Args:
            document: Document to save
            
        Returns:
            True if saved successfully
            
        Raises:
            StorageError: If document already exists
        """
        with self._lock:
            cursor = self._conn.cursor()
            try:
                # Start transaction if not in one
                if self._transaction_level == 0:
                    cursor.execute("BEGIN")
                
                # Check if document already exists
                if self.document_exists(document.id):
                    raise StorageError(f"Document with id '{document.id}' already exists")
                
                # Encrypt content
                encrypted, iv, hmac_str = self._encrypt_content(document.content)
                
                # Save to database
                cursor.execute("""
                    INSERT INTO documents (id, encrypted_content, iv, hmac, type, created_at, updated_at, version)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    document.id,
                    encrypted,
                    iv,
                    hmac_str,
                    document.type,
                    document.created_at,
                    document.updated_at,
                    1
                ))
                
                # Save metadata
                if document.metadata:
                    metadata_json = json.dumps(document.metadata.to_dict())
                    author = document.metadata.author
                    tags = json.dumps(document.metadata.tags) if document.metadata.tags else None
                    
                    cursor.execute("""
                        INSERT INTO document_metadata (document_id, metadata_json, author, tags)
                        VALUES (?, ?, ?, ?)
                    """, (document.id, metadata_json, author, tags))
                
                # Only commit if not in a transaction
                if self._transaction_level == 0:
                    cursor.execute("COMMIT")
                
                logger.debug(f"Document '{document.id}' saved successfully")
                return True
                
            except Exception as e:
                # Only rollback if not in a transaction
                if self._transaction_level == 0:
                    cursor.execute("ROLLBACK")
                logger.error(f"Failed to save document: {e}")
                if isinstance(e, StorageError):
                    raise
                raise StorageError(f"Failed to save document: {e}")
            finally:
                cursor.close()
    
    def get_document(self, document_id: str) -> Optional[Document]:
        """
        Retrieve and decrypt document.
        
        Args:
            document_id: Document ID to retrieve
            
        Returns:
            Document if found, None otherwise
        """
        with self._lock:
            cursor = self._conn.cursor()
            
            # Get document
            cursor.execute("""
                SELECT encrypted_content, iv, hmac, type, created_at, updated_at
                FROM documents WHERE id = ?
            """, (document_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            encrypted, iv, hmac_str, doc_type, created_at, updated_at = row
            
            # Decrypt content
            try:
                content = self._decrypt_content(encrypted, iv, hmac_str)
            except (IntegrityError, EncryptionError) as e:
                logger.error(f"Failed to decrypt document '{document_id}': {e}")
                raise
            
            # Get metadata
            cursor.execute("""
                SELECT metadata_json FROM document_metadata WHERE document_id = ?
            """, (document_id,))
            
            metadata_row = cursor.fetchone()
            metadata = {}
            if metadata_row:
                metadata = json.loads(metadata_row[0])
            
            # Create document
            return Document(
                id=document_id,
                content=content,
                type=doc_type,
                metadata=metadata,
                created_at=created_at,
                updated_at=updated_at
            )
    
    def update_document(self, document_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update existing document.
        
        Args:
            document_id: Document ID to update
            updates: Dictionary of fields to update
            
        Returns:
            True if updated, False if document not found
        """
        with self._lock:
            # Check if document exists
            if not self.document_exists(document_id):
                return False
            
            try:
                cursor = self._conn.cursor()
                
                # Get current document for versioning
                current = self.get_document(document_id)
                
                # Save current version to history
                cursor.execute("""
                    SELECT encrypted_content, iv, hmac, version FROM documents WHERE id = ?
                """, (document_id,))
                current_data = cursor.fetchone()
                
                if current_data:
                    cursor.execute("""
                        INSERT INTO document_versions (document_id, version, encrypted_content, iv, hmac, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (document_id, current_data[3], current_data[0], current_data[1], current_data[2], datetime.now()))
                
                # Apply updates
                if 'content' in updates:
                    encrypted, iv, hmac_str = self._encrypt_content(updates['content'])
                    cursor.execute("""
                        UPDATE documents 
                        SET encrypted_content = ?, iv = ?, hmac = ?, updated_at = ?, version = version + 1
                        WHERE id = ?
                    """, (encrypted, iv, hmac_str, datetime.now(), document_id))
                
                if 'metadata' in updates:
                    metadata = updates['metadata']
                    if isinstance(metadata, dict):
                        metadata_json = json.dumps(metadata)
                        author = metadata.get('author')
                        tags = json.dumps(metadata.get('tags', []))
                        
                        cursor.execute("""
                            UPDATE document_metadata
                            SET metadata_json = ?, author = ?, tags = ?
                            WHERE document_id = ?
                        """, (metadata_json, author, tags, document_id))
                
                self._conn.commit()
                logger.debug(f"Document '{document_id}' updated successfully")
                return True
                
            except Exception as e:
                self._conn.rollback()
                logger.error(f"Failed to update document: {e}")
                return False
    
    def delete_document(self, document_id: str) -> bool:
        """
        Securely delete document with cryptographic erasure.
        
        Args:
            document_id: Document ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            if not self.document_exists(document_id):
                return False
            
            try:
                cursor = self._conn.cursor()
                
                # Overwrite encrypted content with random data (cryptographic erasure)
                random_data = secrets.token_bytes(1024)
                cursor.execute("""
                    UPDATE documents SET encrypted_content = ? WHERE id = ?
                """, (random_data, document_id))
                
                # Delete document (cascade will delete metadata and versions)
                cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))
                
                self._conn.commit()
                logger.debug(f"Document '{document_id}' securely deleted")
                return True
                
            except Exception as e:
                self._conn.rollback()
                logger.error(f"Failed to delete document: {e}")
                return False
    
    def document_exists(self, document_id: str) -> bool:
        """Check if document exists."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("SELECT 1 FROM documents WHERE id = ? LIMIT 1", (document_id,))
            return cursor.fetchone() is not None
    
    @contextmanager
    def transaction(self):
        """
        Transaction context manager with automatic rollback on error.
        Supports nested transactions using savepoints.
        """
        with self._lock:
            self._transaction_level += 1
            savepoint_name = f"sp_{self._transaction_level}"
            
            cursor = self._conn.cursor()
            
            if self._transaction_level == 1:
                # Start main transaction explicitly (we're in manual transaction mode)
                cursor.execute("BEGIN")
            else:
                # Create savepoint for nested transaction
                cursor.execute(f"SAVEPOINT {savepoint_name}")
            
            try:
                yield
                
                if self._transaction_level == 1:
                    cursor.execute("COMMIT")
                else:
                    cursor.execute(f"RELEASE SAVEPOINT {savepoint_name}")
                    
            except Exception as e:
                if self._transaction_level == 1:
                    cursor.execute("ROLLBACK")
                else:
                    cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
                raise
                
            finally:
                self._transaction_level -= 1
                cursor.close()
    
    def get_version_history(self, document_id: str) -> List[Dict[str, Any]]:
        """Get version history for a document."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("""
                SELECT version, created_at FROM document_versions
                WHERE document_id = ?
                ORDER BY version ASC
            """, (document_id,))
            
            history = []
            
            # Add initial version
            history.append({"version": 1, "created_at": None})
            
            # Add subsequent versions
            for row in cursor.fetchall():
                history.append({
                    "version": row[0],
                    "created_at": row[1]
                })
            
            # Add current version
            cursor.execute("""
                SELECT version, updated_at FROM documents WHERE id = ?
            """, (document_id,))
            current = cursor.fetchone()
            if current:
                history.append({
                    "version": current[0],
                    "created_at": current[1]
                })
            
            return history
    
    def search_by_metadata(self, criteria: Dict[str, Any]) -> List[Document]:
        """Search documents by metadata criteria."""
        with self._lock:
            results = []
            cursor = self._conn.cursor()
            
            # Build query based on criteria
            if 'author' in criteria:
                cursor.execute("""
                    SELECT document_id FROM document_metadata WHERE author = ?
                """, (criteria['author'],))
                
                for row in cursor.fetchall():
                    doc = self.get_document(row[0])
                    if doc:
                        results.append(doc)
            
            elif 'tags' in criteria:
                tag = criteria['tags']
                cursor.execute("""
                    SELECT document_id, tags FROM document_metadata WHERE tags IS NOT NULL
                """)
                
                for row in cursor.fetchall():
                    doc_id, tags_json = row
                    tags = json.loads(tags_json) if tags_json else []
                    if tag in tags:
                        doc = self.get_document(doc_id)
                        if doc:
                            results.append(doc)
            
            return results
    
    def search_by_type(self, doc_type: str) -> List[Document]:
        """Search documents by type."""
        with self._lock:
            results = []
            cursor = self._conn.cursor()
            cursor.execute("SELECT id FROM documents WHERE type = ?", (doc_type,))
            
            for row in cursor.fetchall():
                doc = self.get_document(row[0])
                if doc:
                    results.append(doc)
            
            return results
    
    def bulk_save(self, documents: List[Document]) -> Dict[str, bool]:
        """Save multiple documents in a single transaction."""
        results = {}
        
        with self.transaction():
            for doc in documents:
                try:
                    results[doc.id] = self.save_document(doc)
                except Exception as e:
                    logger.error(f"Failed to save document '{doc.id}': {e}")
                    results[doc.id] = False
        
        return results
    
    def bulk_delete(self, document_ids: List[str]) -> Dict[str, bool]:
        """Delete multiple documents in a single transaction."""
        results = {}
        
        with self.transaction():
            for doc_id in document_ids:
                results[doc_id] = self.delete_document(doc_id)
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get storage statistics."""
        with self._lock:
            cursor = self._conn.cursor()
            
            # Total documents
            cursor.execute("SELECT COUNT(*) FROM documents")
            total_docs = cursor.fetchone()[0]
            
            # Documents by type
            cursor.execute("""
                SELECT type, COUNT(*) FROM documents GROUP BY type
            """)
            types = {}
            for row in cursor.fetchall():
                types[row[0]] = row[1]
            
            # Calculate total size
            cursor.execute("SELECT SUM(LENGTH(encrypted_content)) FROM documents")
            total_size = cursor.fetchone()[0] or 0
            
            # Database file size
            db_size = 0
            if self.db_path != ":memory:" and Path(self.db_path).exists():
                db_size = Path(self.db_path).stat().st_size
            
            return {
                "total_documents": total_docs,
                "total_size": total_size,
                "types": types,
                "database_size": db_size
            }
    
    def backup(self, backup_path: str):
        """Create database backup."""
        if self.db_path == ":memory:":
            raise StorageError("Cannot backup in-memory database")
        
        with self._lock:
            backup_conn = sqlite3.connect(backup_path)
            with backup_conn:
                self._conn.backup(backup_conn)
            backup_conn.close()
            
            logger.info(f"Database backed up to: {backup_path}")
    
    def restore(self, backup_path: str):
        """Restore database from backup."""
        if self.db_path == ":memory:":
            raise StorageError("Cannot restore to in-memory database")
        
        with self._lock:
            # Close current connection
            self._conn.close()
            
            # Copy backup to database path
            backup_conn = sqlite3.connect(backup_path)
            new_conn = sqlite3.connect(self.db_path)
            
            with new_conn:
                backup_conn.backup(new_conn)
            
            backup_conn.close()
            new_conn.close()
            
            # Reopen connection
            self._conn = self._create_connection()
            
            logger.info(f"Database restored from: {backup_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get connection from pool or create new one."""
        try:
            return self._connection_pool.get_nowait()
        except:
            return self._create_connection()
    
    def _return_connection(self, conn: sqlite3.Connection):
        """Return connection to pool."""
        try:
            self._connection_pool.put_nowait(conn)
        except:
            conn.close()
    
    def rotate_encryption_key(self, new_key: bytes):
        """
        Rotate encryption key for all documents.
        
        Args:
            new_key: New 32-byte encryption key
        """
        if len(new_key) != 32:
            raise ValueError("Encryption key must be 32 bytes")
        
        with self._lock:
            # Get all documents with current key
            cursor = self._conn.cursor()
            cursor.execute("SELECT id FROM documents")
            document_ids = [row[0] for row in cursor.fetchall()]
            
            # Decrypt with old key, encrypt with new key
            old_cipher = self._cipher
            old_hmac_key = self._hmac_key
            
            # Setup new keys
            self._encryption_key = new_key
            self._cipher = AESGCM(new_key)
            self._hmac_key = hashlib.pbkdf2_hmac(
                'sha256',
                new_key,
                b'devdocai_hmac_salt',
                100000,
                dklen=32
            )
            
            # Re-encrypt all documents
            with self.transaction():
                for doc_id in document_ids:
                    # Get document with old encryption
                    cursor.execute("""
                        SELECT encrypted_content, iv, hmac FROM documents WHERE id = ?
                    """, (doc_id,))
                    encrypted, iv, hmac_str = cursor.fetchone()
                    
                    # Decrypt with old key
                    self._cipher = old_cipher
                    self._hmac_key = old_hmac_key
                    content = self._decrypt_content(encrypted, iv, hmac_str)
                    
                    # Encrypt with new key
                    self._cipher = AESGCM(new_key)
                    self._hmac_key = hashlib.pbkdf2_hmac(
                        'sha256',
                        new_key,
                        b'devdocai_hmac_salt',
                        100000,
                        dklen=32
                    )
                    new_encrypted, new_iv, new_hmac = self._encrypt_content(content)
                    
                    # Update document
                    cursor.execute("""
                        UPDATE documents 
                        SET encrypted_content = ?, iv = ?, hmac = ?
                        WHERE id = ?
                    """, (new_encrypted, new_iv, new_hmac, doc_id))
            
            logger.info("Encryption key rotated successfully")
    
    def close(self):
        """Close database connection."""
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None
                logger.debug("Database connection closed")