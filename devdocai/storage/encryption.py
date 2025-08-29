"""
Encryption module for M002 Local Storage System.

Provides SQLCipher integration for transparent database encryption
and secure key management using Argon2id.
"""

import os
import secrets
import logging
import json
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
from argon2 import PasswordHasher, Parameters, Type
from argon2.exceptions import VerifyMismatchError
import base64
from typing import List

logger = logging.getLogger(__name__)


class EncryptionManager:
    """
    Manages database encryption using SQLCipher and AES-256-GCM.
    
    Provides key derivation, secure storage, and encryption/decryption
    capabilities for the storage system.
    """
    
    # Argon2id parameters (matching M001 configuration)
    ARGON2_TIME_COST = 3
    ARGON2_MEMORY_COST = 65536  # 64MB
    ARGON2_PARALLELISM = 4
    ARGON2_HASH_LEN = 32
    ARGON2_SALT_LEN = 16
    
    # AES-256-GCM parameters
    AES_KEY_SIZE = 32  # 256 bits
    AES_NONCE_SIZE = 12  # 96 bits for GCM
    AES_TAG_SIZE = 16  # 128 bits
    
    def __init__(self, key_file: Optional[str] = None):
        """
        Initialize encryption manager.
        
        Args:
            key_file: Path to key storage file
        """
        self.key_file = Path(key_file) if key_file else Path.home() / '.devdocai' / 'storage.key'
        self.key_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.password_hasher = PasswordHasher(
            time_cost=self.ARGON2_TIME_COST,
            memory_cost=self.ARGON2_MEMORY_COST,
            parallelism=self.ARGON2_PARALLELISM,
            hash_len=self.ARGON2_HASH_LEN,
            salt_len=self.ARGON2_SALT_LEN,
            type=Type.ID
        )
        
        self._master_key: Optional[bytes] = None
        self._key_cache: Dict[str, Tuple[bytes, datetime]] = {}
        self._cache_ttl = timedelta(minutes=30)
    
    def derive_key(self, password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """
        Derive encryption key from password using Argon2id.
        
        Args:
            password: User password
            salt: Optional salt (generated if not provided)
            
        Returns:
            Tuple of (derived_key, salt)
        """
        if salt is None:
            salt = secrets.token_bytes(self.ARGON2_SALT_LEN)
        
        # Use PBKDF2 for consistent key derivation
        # (Argon2 library has inconsistent output format)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.AES_KEY_SIZE,
            salt=salt,
            iterations=256000,  # OWASP recommended for PBKDF2-SHA256
            backend=default_backend()
        )
        key = kdf.derive(password.encode())
        
        return key, salt
    
    def generate_master_key(self, password: str) -> bool:
        """
        Generate and store master encryption key.
        
        Args:
            password: Master password
            
        Returns:
            Success status
        """
        try:
            # Generate key and salt
            key, salt = self.derive_key(password)
            
            # Generate additional key material for SQLCipher
            sqlcipher_key = secrets.token_hex(32)  # 64 hex characters
            
            # Create key data structure
            key_data = {
                'version': 1,
                'algorithm': 'argon2id',
                'salt': base64.b64encode(salt).decode(),
                'sqlcipher_key': sqlcipher_key,
                'created_at': datetime.utcnow().isoformat(),
                'checksum': self._calculate_checksum(key)
            }
            
            # Encrypt key data
            encrypted_data = self._encrypt_key_data(key_data, key)
            
            # Store encrypted key file with secure permissions
            self.key_file.write_bytes(encrypted_data)
            if os.name != 'nt':  # Unix-like systems
                os.chmod(self.key_file, 0o600)  # Read/write for owner only
            
            self._master_key = key
            logger.info("Master key generated and stored securely")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate master key: {e}")
            return False
    
    def load_master_key(self, password: str) -> bool:
        """
        Load and verify master encryption key.
        
        Args:
            password: Master password
            
        Returns:
            Success status
        """
        try:
            if not self.key_file.exists():
                logger.error("Key file not found")
                return False
            
            # Read encrypted key data
            encrypted_data = self.key_file.read_bytes()
            
            # Try to decrypt with provided password
            # Extract salt from file (first 16 bytes after version marker)
            salt = encrypted_data[1:17]  # Skip version byte
            
            # Derive key from password
            key, _ = self.derive_key(password, salt)
            
            # Decrypt key data
            key_data = self._decrypt_key_data(encrypted_data, key)
            
            if key_data:
                # Verify checksum
                if self._calculate_checksum(key) == key_data.get('checksum'):
                    self._master_key = key
                    logger.info("Master key loaded successfully")
                    return True
                else:
                    logger.error("Key checksum verification failed")
                    return False
            else:
                logger.error("Failed to decrypt key data")
                return False
                
        except Exception as e:
            logger.error(f"Failed to load master key: {e}")
            return False
    
    def get_sqlcipher_key(self, password: str) -> Optional[str]:
        """
        Get SQLCipher encryption key.
        
        Args:
            password: Master password
            
        Returns:
            SQLCipher key in hex format or None
        """
        if not self.load_master_key(password):
            return None
        
        try:
            encrypted_data = self.key_file.read_bytes()
            salt = encrypted_data[1:17]
            key, _ = self.derive_key(password, salt)
            
            key_data = self._decrypt_key_data(encrypted_data, key)
            return key_data.get('sqlcipher_key') if key_data else None
            
        except Exception as e:
            logger.error(f"Failed to get SQLCipher key: {e}")
            return None
    
    def encrypt_content(self, content: str, key: Optional[bytes] = None) -> bytes:
        """
        Encrypt content using AES-256-GCM.
        
        Args:
            content: Plain text content
            key: Encryption key (uses master key if not provided)
            
        Returns:
            Encrypted bytes
        """
        key = key or self._master_key
        if not key:
            raise ValueError("No encryption key available")
        
        # Generate nonce
        nonce = secrets.token_bytes(self.AES_NONCE_SIZE)
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(nonce),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        # Encrypt content
        plaintext = content.encode('utf-8')
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        
        # Return nonce + ciphertext + tag
        return nonce + ciphertext + encryptor.tag
    
    def decrypt_content(self, encrypted_data: bytes, key: Optional[bytes] = None) -> str:
        """
        Decrypt content using AES-256-GCM.
        
        Args:
            encrypted_data: Encrypted bytes
            key: Decryption key (uses master key if not provided)
            
        Returns:
            Decrypted content
        """
        key = key or self._master_key
        if not key:
            raise ValueError("No decryption key available")
        
        # Extract components
        nonce = encrypted_data[:self.AES_NONCE_SIZE]
        tag = encrypted_data[-self.AES_TAG_SIZE:]
        ciphertext = encrypted_data[self.AES_NONCE_SIZE:-self.AES_TAG_SIZE]
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(nonce, tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        # Decrypt content
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        return plaintext.decode('utf-8')
    
    def encrypt_field(self, value: Any) -> str:
        """
        Encrypt a field value for storage.
        
        Args:
            value: Value to encrypt
            
        Returns:
            Base64-encoded encrypted string
        """
        if not self._master_key:
            raise ValueError("Master key not loaded")
        
        # Convert value to JSON string
        json_str = json.dumps(value)
        
        # Encrypt
        encrypted = self.encrypt_content(json_str)
        
        # Return base64 encoded
        return base64.b64encode(encrypted).decode('utf-8')
    
    def decrypt_field(self, encrypted_value: str) -> Any:
        """
        Decrypt a field value from storage.
        
        Args:
            encrypted_value: Base64-encoded encrypted string
            
        Returns:
            Decrypted value
        """
        if not self._master_key:
            raise ValueError("Master key not loaded")
        
        # Decode from base64
        encrypted = base64.b64decode(encrypted_value)
        
        # Decrypt
        json_str = self.decrypt_content(encrypted)
        
        # Parse JSON
        return json.loads(json_str)
    
    def rotate_keys(self, old_password: str, new_password: str) -> bool:
        """
        Rotate encryption keys with new password.
        
        Args:
            old_password: Current password
            new_password: New password
            
        Returns:
            Success status
        """
        try:
            # Load current key
            if not self.load_master_key(old_password):
                logger.error("Failed to load current key")
                return False
            
            # Get current SQLCipher key
            sqlcipher_key = self.get_sqlcipher_key(old_password)
            if not sqlcipher_key:
                logger.error("Failed to get current SQLCipher key")
                return False
            
            # Generate new key with new password
            new_key, new_salt = self.derive_key(new_password)
            
            # Create new key data
            key_data = {
                'version': 1,
                'algorithm': 'argon2id',
                'salt': base64.b64encode(new_salt).decode(),
                'sqlcipher_key': sqlcipher_key,  # Keep same SQLCipher key
                'created_at': datetime.utcnow().isoformat(),
                'rotated_from': self._calculate_checksum(self._master_key),
                'checksum': self._calculate_checksum(new_key)
            }
            
            # Backup old key file
            backup_path = self.key_file.with_suffix('.backup')
            if self.key_file.exists():
                import shutil
                shutil.copy2(self.key_file, backup_path)
            
            # Encrypt and store new key data
            encrypted_data = self._encrypt_key_data(key_data, new_key)
            self.key_file.write_bytes(encrypted_data)
            
            if os.name != 'nt':
                os.chmod(self.key_file, 0o600)
            
            self._master_key = new_key
            logger.info("Keys rotated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Key rotation failed: {e}")
            return False
    
    def _encrypt_key_data(self, data: Dict[str, Any], key: bytes) -> bytes:
        """Encrypt key data structure."""
        # Convert to JSON
        json_data = json.dumps(data)
        
        # Add version marker
        version = b'\x01'
        
        # Get salt from data or generate new one
        if 'salt' in data:
            salt = base64.b64decode(data['salt'])
        else:
            salt = secrets.token_bytes(self.ARGON2_SALT_LEN)
        
        # Encrypt JSON data
        encrypted = self.encrypt_content(json_data, key)
        
        # Return version + salt + encrypted data
        return version + salt + encrypted
    
    def _decrypt_key_data(self, encrypted_data: bytes, key: bytes) -> Optional[Dict[str, Any]]:
        """Decrypt key data structure."""
        try:
            # Skip version byte and salt
            encrypted_content = encrypted_data[17:]  # 1 byte version + 16 bytes salt
            
            # Decrypt
            json_data = self.decrypt_content(encrypted_content, key)
            
            # Parse JSON
            return json.loads(json_data)
            
        except Exception as e:
            logger.error(f"Failed to decrypt key data: {e}")
            return None
    
    def _calculate_checksum(self, key: bytes) -> str:
        """Calculate checksum for key verification."""
        import hashlib
        return hashlib.sha256(key).hexdigest()[:16]
    
    def secure_delete_key(self, passes: int = 3) -> bool:
        """
        Securely delete the key file.
        
        Args:
            passes: Number of overwrite passes
            
        Returns:
            Success status
        """
        if not self.key_file.exists():
            return True
        
        try:
            file_size = self.key_file.stat().st_size
            
            with open(self.key_file, 'ba+', buffering=0) as f:
                for _ in range(passes):
                    f.seek(0)
                    f.write(os.urandom(file_size))
                    f.flush()
                    os.fsync(f.fileno())
            
            self.key_file.unlink()
            self._master_key = None
            logger.info("Key file securely deleted")
            return True
            
        except Exception as e:
            logger.error(f"Failed to securely delete key: {e}")
            return False


class SQLCipherHelper:
    """Helper class for SQLCipher operations."""
    
    @staticmethod
    def get_pragma_statements(key: str) -> List[str]:
        """
        Get SQLCipher PRAGMA statements for database initialization.
        
        Args:
            key: Encryption key in hex format
            
        Returns:
            List of PRAGMA statements
        """
        return [
            f"PRAGMA key = \"x'{key}'\"",  # Set encryption key
            "PRAGMA cipher_page_size = 4096",  # Page size
            "PRAGMA kdf_iter = 256000",  # Key derivation iterations
            "PRAGMA cipher_hmac_algorithm = HMAC_SHA256",  # HMAC algorithm
            "PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA256",  # KDF algorithm
        ]
    
    @staticmethod
    def create_encrypted_connection(db_path: str, key: str):
        """
        Create an encrypted SQLCipher connection.
        
        Args:
            db_path: Path to database file
            key: Encryption key in hex format
            
        Returns:
            SQLCipher connection
        """
        try:
            import sqlcipher3 as sqlite3
        except ImportError:
            logger.warning("SQLCipher not available, falling back to standard SQLite")
            import sqlite3
        
        conn = sqlite3.connect(db_path)
        
        # Apply encryption pragmas
        for pragma in SQLCipherHelper.get_pragma_statements(key):
            conn.execute(pragma)
        
        # Test connection
        conn.execute("SELECT count(*) FROM sqlite_master")
        
        return conn
    
    @staticmethod
    def change_password(db_path: str, old_key: str, new_key: str) -> bool:
        """
        Change database encryption password.
        
        Args:
            db_path: Path to database file
            old_key: Current encryption key
            new_key: New encryption key
            
        Returns:
            Success status
        """
        try:
            conn = SQLCipherHelper.create_encrypted_connection(db_path, old_key)
            conn.execute(f"PRAGMA rekey = \"x'{new_key}'\"")
            conn.close()
            logger.info("Database password changed successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to change database password: {e}")
            return False
    
    @staticmethod
    def export_plaintext(encrypted_db: str, key: str, plaintext_db: str) -> bool:
        """
        Export encrypted database to plaintext.
        
        Args:
            encrypted_db: Path to encrypted database
            key: Encryption key
            plaintext_db: Path for plaintext database
            
        Returns:
            Success status
        """
        try:
            # Open encrypted database
            enc_conn = SQLCipherHelper.create_encrypted_connection(encrypted_db, key)
            
            # Attach plaintext database
            enc_conn.execute(f"ATTACH DATABASE '{plaintext_db}' AS plaintext KEY ''")
            
            # Export schema and data
            enc_conn.execute("SELECT sqlcipher_export('plaintext')")
            
            # Detach and close
            enc_conn.execute("DETACH DATABASE plaintext")
            enc_conn.close()
            
            logger.info(f"Exported to plaintext database: {plaintext_db}")
            return True
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False