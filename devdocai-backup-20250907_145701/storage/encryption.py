"""
M002 Local Storage System - Encryption Layer

Encryption utilities for document storage, integrating with M001 patterns:
- AES-256-GCM encryption for document content
- Key derivation using same patterns as M001
- Privacy-first encryption defaults
- Integration with ConfigurationManager
"""

import secrets
import base64
import hashlib
import json
from typing import Optional, Dict, Any, Union
from pathlib import Path

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

from devdocai.core.config import ConfigurationManager


class EncryptionError(Exception):
    """Encryption-related errors."""
    pass


class DocumentEncryption:
    """
    Document encryption handler using M001 patterns.
    
    Provides AES-256-GCM encryption for document content with:
    - Key derivation using PBKDF2 (same as M001)
    - Random salt and nonce per encryption
    - Integrity verification with GCM tags
    - Integration with M001 ConfigurationManager
    """
    
    def __init__(self, config: ConfigurationManager):
        """
        Initialize document encryption.
        
        Args:
            config: M001 ConfigurationManager instance
        """
        self.config = config
        self._master_key: Optional[bytes] = None
        
        # Initialize master key if encryption is enabled
        if self.config.get('encryption_enabled', True):
            self._initialize_master_key()
    
    def _initialize_master_key(self) -> None:
        """Initialize or load master encryption key."""
        try:
            # Try to load existing master key
            key_file = self.config.get('config_dir') / ".storage_key"
            
            if key_file.exists():
                self._load_master_key(key_file)
            else:
                self._generate_master_key(key_file)
                
        except Exception as e:
            raise EncryptionError(f"Master key initialization failed: {e}")
    
    def _generate_master_key(self, key_file: Path) -> None:
        """Generate and store new master encryption key."""
        try:
            # Generate random master key material
            master_seed = secrets.token_bytes(32)
            
            # Use machine-specific context for additional entropy
            import platform
            machine_context = f"devdocai_storage_{platform.node()}_{platform.machine()}"
            
            # Derive master key using PBKDF2 (same as M001 pattern)
            salt = secrets.token_bytes(16)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            
            self._master_key = kdf.derive(master_seed + machine_context.encode())
            
            # Store encrypted master key material
            self._store_master_key(key_file, salt, master_seed)
            
        except Exception as e:
            raise EncryptionError(f"Master key generation failed: {e}")
    
    def _store_master_key(self, key_file: Path, salt: bytes, seed: bytes) -> None:
        """Store master key material securely."""
        try:
            # Encrypt seed with a password derived from machine context
            import platform
            machine_password = f"devdocai_master_{platform.node()}_{platform.machine()}"
            
            # Generate key for seed encryption
            seed_salt = secrets.token_bytes(16)
            seed_nonce = secrets.token_bytes(12)
            
            seed_kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=seed_salt,
                iterations=100000,
                backend=default_backend()
            )
            
            seed_key = seed_kdf.derive(machine_password.encode())
            
            # Encrypt seed
            cipher = Cipher(
                algorithms.AES(seed_key),
                modes.GCM(seed_nonce),
                backend=default_backend()
            )
            
            encryptor = cipher.encryptor()
            encrypted_seed = encryptor.update(seed) + encryptor.finalize()
            
            # Store all components
            key_data = {
                'salt': base64.b64encode(salt).decode('ascii'),
                'seed_salt': base64.b64encode(seed_salt).decode('ascii'),
                'seed_nonce': base64.b64encode(seed_nonce).decode('ascii'),
                'seed_tag': base64.b64encode(encryptor.tag).decode('ascii'),
                'encrypted_seed': base64.b64encode(encrypted_seed).decode('ascii'),
                'version': '1.0'
            }
            
            with open(key_file, 'w', encoding='utf-8') as f:
                json.dump(key_data, f)
            
            # Set restrictive permissions
            key_file.chmod(0o600)
            
        except Exception as e:
            raise EncryptionError(f"Master key storage failed: {e}")
    
    def _load_master_key(self, key_file: Path) -> None:
        """Load master key from storage."""
        try:
            with open(key_file, 'r', encoding='utf-8') as f:
                key_data = json.load(f)
            
            # Extract components
            salt = base64.b64decode(key_data['salt'])
            seed_salt = base64.b64decode(key_data['seed_salt'])
            seed_nonce = base64.b64decode(key_data['seed_nonce'])
            seed_tag = base64.b64decode(key_data['seed_tag'])
            encrypted_seed = base64.b64decode(key_data['encrypted_seed'])
            
            # Derive seed decryption key
            import platform
            machine_password = f"devdocai_master_{platform.node()}_{platform.machine()}"
            
            seed_kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=seed_salt,
                iterations=100000,
                backend=default_backend()
            )
            
            seed_key = seed_kdf.derive(machine_password.encode())
            
            # Decrypt seed
            cipher = Cipher(
                algorithms.AES(seed_key),
                modes.GCM(seed_nonce, seed_tag),
                backend=default_backend()
            )
            
            decryptor = cipher.decryptor()
            master_seed = decryptor.update(encrypted_seed) + decryptor.finalize()
            
            # Derive master key
            machine_context = f"devdocai_storage_{platform.node()}_{platform.machine()}"
            
            master_kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            
            self._master_key = master_kdf.derive(master_seed + machine_context.encode())
            
        except Exception as e:
            raise EncryptionError(f"Master key loading failed: {e}")
    
    def encrypt_content(self, content: str, document_id: str) -> str:
        """
        Encrypt document content.
        
        Args:
            content: Document content to encrypt
            document_id: Document identifier for key derivation
            
        Returns:
            Base64-encoded encrypted content
            
        Raises:
            EncryptionError: If encryption fails
        """
        if not self.config.get('encryption_enabled', True):
            # Return plaintext if encryption disabled
            return content
        
        if self._master_key is None:
            raise EncryptionError("Encryption key not initialized")
        
        try:
            # Derive document-specific key
            doc_key = self._derive_document_key(document_id)
            
            # Generate random nonce
            nonce = secrets.token_bytes(12)
            
            # Encrypt content
            cipher = Cipher(
                algorithms.AES(doc_key),
                modes.GCM(nonce),
                backend=default_backend()
            )
            
            encryptor = cipher.encryptor()
            content_bytes = content.encode('utf-8')
            ciphertext = encryptor.update(content_bytes) + encryptor.finalize()
            
            # Combine nonce + tag + ciphertext
            encrypted_data = nonce + encryptor.tag + ciphertext
            
            # Return base64-encoded result
            return base64.b64encode(encrypted_data).decode('ascii')
            
        except Exception as e:
            raise EncryptionError(f"Content encryption failed: {e}")
    
    def decrypt_content(self, encrypted_content: str, document_id: str) -> str:
        """
        Decrypt document content.
        
        Args:
            encrypted_content: Base64-encoded encrypted content
            document_id: Document identifier for key derivation
            
        Returns:
            Decrypted content string
            
        Raises:
            EncryptionError: If decryption fails
        """
        if not self.config.get('encryption_enabled', True):
            # Return as-is if encryption disabled
            return encrypted_content
        
        if self._master_key is None:
            raise EncryptionError("Encryption key not initialized")
        
        try:
            # Derive document-specific key
            doc_key = self._derive_document_key(document_id)
            
            # Decode encrypted data
            encrypted_data = base64.b64decode(encrypted_content)
            
            # Extract components
            nonce = encrypted_data[:12]
            tag = encrypted_data[12:28]
            ciphertext = encrypted_data[28:]
            
            # Decrypt content
            cipher = Cipher(
                algorithms.AES(doc_key),
                modes.GCM(nonce, tag),
                backend=default_backend()
            )
            
            decryptor = cipher.decryptor()
            content_bytes = decryptor.update(ciphertext) + decryptor.finalize()
            
            return content_bytes.decode('utf-8')
            
        except Exception as e:
            raise EncryptionError(f"Content decryption failed: {e}")
    
    def _derive_document_key(self, document_id: str) -> bytes:
        """Derive document-specific encryption key."""
        if self._master_key is None:
            raise EncryptionError("Master key not initialized")
        
        # Use document ID as salt material
        doc_salt = hashlib.sha256(f"devdocai_doc_{document_id}".encode()).digest()[:16]
        
        # Derive document key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=doc_salt,
            iterations=10000,  # Fewer iterations for performance
            backend=default_backend()
        )
        
        return kdf.derive(self._master_key)
    
    def encrypt_metadata(self, metadata: Dict[str, Any]) -> str:
        """
        Encrypt document metadata.
        
        Args:
            metadata: Metadata dictionary to encrypt
            
        Returns:
            Base64-encoded encrypted metadata
        """
        if not self.config.get('encryption_enabled', True):
            return json.dumps(metadata)
        
        try:
            # Serialize metadata to JSON
            metadata_json = json.dumps(metadata, sort_keys=True)
            
            # Use a fixed document ID for metadata encryption
            return self.encrypt_content(metadata_json, "_metadata_")
            
        except Exception as e:
            raise EncryptionError(f"Metadata encryption failed: {e}")
    
    def decrypt_metadata(self, encrypted_metadata: str) -> Dict[str, Any]:
        """
        Decrypt document metadata.
        
        Args:
            encrypted_metadata: Base64-encoded encrypted metadata
            
        Returns:
            Decrypted metadata dictionary
        """
        if not self.config.get('encryption_enabled', True):
            return json.loads(encrypted_metadata)
        
        try:
            # Decrypt metadata JSON
            metadata_json = self.decrypt_content(encrypted_metadata, "_metadata_")
            
            return json.loads(metadata_json)
            
        except Exception as e:
            raise EncryptionError(f"Metadata decryption failed: {e}")
    
    def is_encrypted_content(self, content: str) -> bool:
        """
        Check if content appears to be encrypted.
        
        Args:
            content: Content string to check
            
        Returns:
            True if content appears encrypted, False otherwise
        """
        if not self.config.get('encryption_enabled', True):
            return False
        
        try:
            # Try to decode as base64
            decoded = base64.b64decode(content, validate=True)
            
            # Encrypted content should be at least 28 bytes (12 nonce + 16 tag)
            if len(decoded) < 28:
                return False
            
            # Additional heuristics could be added here
            return True
            
        except Exception:
            return False
    
    def get_encryption_info(self) -> Dict[str, Any]:
        """
        Get encryption status and information.
        
        Returns:
            Dictionary with encryption information
        """
        return {
            'encryption_enabled': self.config.get('encryption_enabled', True),
            'master_key_initialized': self._master_key is not None,
            'encryption_algorithm': 'AES-256-GCM',
            'key_derivation': 'PBKDF2-HMAC-SHA256',
            'key_iterations': 100000,
            'per_document_keys': True
        }
    
    def rotate_master_key(self) -> None:
        """
        Rotate the master encryption key.
        
        Note: This is a placeholder for future implementation.
        Key rotation would require re-encrypting all existing documents.
        """
        # TODO: Implement in future passes
        raise NotImplementedError(
            "Master key rotation will be implemented in future passes"
        )
    
    def verify_encryption_integrity(self) -> bool:
        """
        Verify encryption system integrity.
        
        Returns:
            True if encryption system is working correctly
        """
        if not self.config.get('encryption_enabled', True):
            return True
        
        try:
            # Test encryption/decryption cycle
            test_content = "DevDocAI encryption test content"
            test_doc_id = "test_document_id"
            
            # Encrypt test content
            encrypted = self.encrypt_content(test_content, test_doc_id)
            
            # Decrypt test content
            decrypted = self.decrypt_content(encrypted, test_doc_id)
            
            # Verify round-trip
            return decrypted == test_content
            
        except Exception:
            return False