"""
Security and Encryption Utilities - DevDocAI v3.0.0
Pass 4: Simplified encryption with focused functionality
"""

import base64
import secrets
import json
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class EncryptionManager:
    """Manages AES-256-GCM encryption operations."""

    def __init__(self):
        """Initialize encryption manager."""
        self._key: Optional[bytes] = None
        self.audit_log_path = Path.home() / ".devdocai" / "security_audit.log"
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)

    def derive_key(self, password: str, salt: Optional[bytes] = None) -> bytes:
        """Derive 32-byte key using PBKDF2-SHA256."""
        if salt is None:
            salt = b"devdocai_salt_v1" + password.encode()[:16].ljust(16, b"0")

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend(),
        )
        return kdf.derive(password.encode())

    def encrypt(self, plaintext: str, key: Optional[bytes] = None) -> str:
        """Encrypt text using AES-256-GCM."""
        if key is None:
            if not self._key:
                self._key = secrets.token_bytes(32)
            key = self._key

        nonce = secrets.token_bytes(12)
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)

        encrypted_data = nonce + ciphertext
        return base64.b64encode(encrypted_data).decode("ascii")

    def decrypt(self, encrypted: str, key: Optional[bytes] = None) -> str:
        """Decrypt text using AES-256-GCM."""
        if key is None:
            if not self._key:
                raise ValueError("Encryption key not available")
            key = self._key

        try:
            encrypted_data = base64.b64decode(encrypted)
            nonce = encrypted_data[:12]
            ciphertext = encrypted_data[12:]

            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode("utf-8")
        except Exception as e:
            raise ValueError(f"Failed to decrypt: {e}")

    def audit_log(self, event: str, details: Dict[str, Any]):
        """Log security events."""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "event": event,
                "details": details,
            }

            # Simple rotation
            if (
                self.audit_log_path.exists() and self.audit_log_path.stat().st_size > 10485760
            ):  # 10MB
                backup = self.audit_log_path.with_suffix(".log.1")
                if backup.exists():
                    backup.unlink()
                self.audit_log_path.rename(backup)

            with open(self.audit_log_path, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logger.warning(f"Failed to write audit log: {e}")

    def set_key(self, key: bytes):
        """Set encryption key."""
        self._key = key

    def has_key(self) -> bool:
        """Check if key is set."""
        return self._key is not None
