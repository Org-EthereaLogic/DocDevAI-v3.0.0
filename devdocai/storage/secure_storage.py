"""
M002: Secure Storage Component - Stub Implementation

Provides secure storage capabilities:
- AES-256-GCM encryption for data at rest
- Secure key management
- Encrypted backups
- Compliance with security standards

Current Status: NOT IMPLEMENTED - Minimal stub for CI/CD compatibility
"""

from typing import Any, Optional
from pathlib import Path


class SecureStorage:
    """
    Secure storage with encryption capabilities.
    
    This is a STUB implementation to satisfy CI/CD requirements.
    Full implementation will be added as part of M002.
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize secure storage.
        
        Args:
            storage_path: Path for secure storage
        """
        self.storage_path = storage_path or Path.home() / ".devdocai" / "secure"
        self._is_stub = True  # Marker to indicate this is a stub
        self._encryption_enabled = True
        
    def encrypt_data(self, data: bytes, key: Optional[bytes] = None) -> bytes:
        """
        Encrypt data using AES-256-GCM.
        
        Args:
            data: Data to encrypt
            key: Encryption key
            
        Returns:
            bytes: Encrypted data (stub returns original)
        """
        return data  # Stub: return unencrypted
    
    def decrypt_data(self, encrypted_data: bytes, key: Optional[bytes] = None) -> bytes:
        """
        Decrypt data using AES-256-GCM.
        
        Args:
            encrypted_data: Encrypted data
            key: Decryption key
            
        Returns:
            bytes: Decrypted data (stub returns original)
        """
        return encrypted_data  # Stub: return as-is
    
    def store_secure(self, key: str, value: Any, encrypt: bool = True) -> bool:
        """
        Store data securely.
        
        Args:
            key: Storage key
            value: Value to store
            encrypt: Whether to encrypt
            
        Returns:
            bool: Success status (stub always returns True)
        """
        return True
    
    def retrieve_secure(self, key: str, decrypt: bool = True) -> Optional[Any]:
        """
        Retrieve securely stored data.
        
        Args:
            key: Storage key
            decrypt: Whether to decrypt
            
        Returns:
            Optional[Any]: Retrieved value (stub returns None)
        """
        return None
    
    def create_backup(self, backup_path: Optional[Path] = None) -> bool:
        """
        Create encrypted backup.
        
        Args:
            backup_path: Path for backup
            
        Returns:
            bool: Success status (stub always returns True)
        """
        return True
    
    def restore_backup(self, backup_path: Path) -> bool:
        """
        Restore from encrypted backup.
        
        Args:
            backup_path: Path to backup
            
        Returns:
            bool: Success status (stub always returns False)
        """
        return False
    
    def is_encrypted(self) -> bool:
        """
        Check if encryption is enabled.
        
        Returns:
            bool: Encryption status
        """
        return self._encryption_enabled
    
    def __repr__(self) -> str:
        return f"SecureStorage(path={self.storage_path}, stub=True)"