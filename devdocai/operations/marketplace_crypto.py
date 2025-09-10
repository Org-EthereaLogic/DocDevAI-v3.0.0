"""
M013 Template Marketplace - Cryptographic Operations
DevDocAI v3.0.0 - Pass 4: Refactoring & Integration

This module contains all cryptographic operations for template signing and
verification, extracted from the security module for clean separation.
"""

import base64
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# Try to import cryptography library
try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519

    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    ed25519 = None
    InvalidSignature = Exception


class CryptoManager:
    """Manager for cryptographic operations."""

    def __init__(self):
        """Initialize crypto manager."""
        if not CRYPTO_AVAILABLE:
            raise ImportError("cryptography library required for crypto operations")

        self._backend = default_backend()
        self._trusted_keys: Dict[str, Dict[str, Any]] = {}
        self._revoked_keys: Dict[str, Dict[str, Any]] = {}

    def generate_keypair(self) -> Tuple[bytes, bytes]:
        """
        Generate Ed25519 keypair for signing.

        Returns:
            Tuple of (private_key_bytes, public_key_bytes)
        """
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )

        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )

        return private_bytes, public_bytes

    def sign(self, message: bytes, private_key_bytes: bytes) -> bytes:
        """
        Sign a message with private key.

        Args:
            message: Message to sign
            private_key_bytes: Private key bytes

        Returns:
            Signature bytes
        """
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_key_bytes)
        signature = private_key.sign(message)
        return signature

    def verify(self, message: bytes, signature: bytes, public_key: Union[bytes, Any]) -> bool:
        """
        Verify Ed25519 signature.

        Args:
            message: Original message
            signature: Signature to verify
            public_key: Public key (bytes or key object)

        Returns:
            True if valid, False otherwise
        """
        try:
            # Convert bytes to key object if needed
            if isinstance(public_key, bytes):
                public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key)

            # Verify signature
            public_key.verify(signature, message)
            return True

        except (InvalidSignature, Exception) as e:
            logger.debug(f"Signature verification failed: {e}")
            return False

    def add_trusted_key(
        self,
        key_id: str,
        public_key: bytes,
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Add a trusted public key.

        Args:
            key_id: Unique key identifier
            public_key: Ed25519 public key bytes
            expires_at: Optional key expiration time
            metadata: Optional key metadata
        """
        self._trusted_keys[key_id] = {
            "public_key": public_key,
            "added_at": datetime.now(),
            "expires_at": expires_at,
            "metadata": metadata or {},
        }
        logger.info(f"Added trusted key: {key_id}")

    def revoke_key(self, key_id: str, reason: str):
        """
        Revoke a public key.

        Args:
            key_id: Key identifier to revoke
            reason: Reason for revocation
        """
        if key_id in self._trusted_keys:
            key_info = self._trusted_keys.pop(key_id)
            self._revoked_keys[key_id] = {
                **key_info,
                "revoked_at": datetime.now(),
                "revocation_reason": reason,
            }
            logger.warning(f"Revoked key {key_id}: {reason}")

    def is_key_trusted(self, key_id: str) -> bool:
        """
        Check if a key is trusted.

        Args:
            key_id: Key identifier

        Returns:
            True if key is trusted and not expired
        """
        if key_id not in self._trusted_keys:
            return False

        if key_id in self._revoked_keys:
            return False

        key_info = self._trusted_keys[key_id]
        if key_info["expires_at"] and datetime.now() > key_info["expires_at"]:
            return False

        return True

    def get_trusted_key(self, key_id: str) -> Optional[bytes]:
        """
        Get a trusted public key.

        Args:
            key_id: Key identifier

        Returns:
            Public key bytes if trusted, None otherwise
        """
        if self.is_key_trusted(key_id):
            return self._trusted_keys[key_id]["public_key"]
        return None

    def verify_with_trusted_keys(
        self, message: bytes, signature: bytes, key_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify signature using trusted keys.

        Args:
            message: Original message
            signature: Signature to verify
            key_id: Optional specific key to use

        Returns:
            Tuple of (is_valid, key_id_used)
        """
        if key_id:
            # Try specific key
            public_key = self.get_trusted_key(key_id)
            if public_key and self.verify(message, signature, public_key):
                return True, key_id
            return False, None

        # Try all trusted keys
        for kid, key_info in self._trusted_keys.items():
            if self.is_key_trusted(kid):
                if self.verify(message, signature, key_info["public_key"]):
                    return True, kid

        return False, None


class TemplateSignatureManager:
    """Manager for template-specific signature operations."""

    def __init__(self, crypto_manager: Optional[CryptoManager] = None):
        """
        Initialize signature manager.

        Args:
            crypto_manager: Crypto manager instance
        """
        self.crypto = crypto_manager or CryptoManager()

    def sign_template(self, template_data: Dict[str, Any], private_key: bytes) -> Tuple[str, str]:
        """
        Sign a template.

        Args:
            template_data: Template data to sign
            private_key: Private key bytes

        Returns:
            Tuple of (signature_base64, public_key_base64)
        """
        # Generate message from template data
        message = self._create_signing_message(template_data)

        # Sign the message
        signature = self.crypto.sign(message, private_key)

        # Get public key from private key
        private_key_obj = ed25519.Ed25519PrivateKey.from_private_bytes(private_key)
        public_key = private_key_obj.public_key()
        public_key_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )

        # Encode for storage
        signature_b64 = base64.b64encode(signature).decode()
        public_key_b64 = base64.b64encode(public_key_bytes).decode()

        return signature_b64, public_key_b64

    def verify_template(
        self, template_data: Dict[str, Any], signature_b64: str, public_key_b64: str
    ) -> bool:
        """
        Verify a template signature.

        Args:
            template_data: Template data
            signature_b64: Base64 encoded signature
            public_key_b64: Base64 encoded public key

        Returns:
            True if signature is valid
        """
        try:
            # Decode signature and public key
            signature = base64.b64decode(signature_b64)
            public_key = base64.b64decode(public_key_b64)

            # Create message from template data
            message = self._create_signing_message(template_data)

            # Verify signature
            return self.crypto.verify(message, signature, public_key)

        except Exception as e:
            logger.error(f"Template signature verification failed: {e}")
            return False

    def verify_with_trusted_keys(
        self, template_data: Dict[str, Any], signature_b64: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify template using trusted keys.

        Args:
            template_data: Template data
            signature_b64: Base64 encoded signature

        Returns:
            Tuple of (is_valid, key_id_used)
        """
        try:
            signature = base64.b64decode(signature_b64)
            message = self._create_signing_message(template_data)
            return self.crypto.verify_with_trusted_keys(message, signature)
        except Exception as e:
            logger.error(f"Trusted key verification failed: {e}")
            return False, None

    def _create_signing_message(self, template_data: Dict[str, Any]) -> bytes:
        """
        Create a consistent message for signing from template data.

        Args:
            template_data: Template data

        Returns:
            Message bytes for signing
        """
        # Extract critical fields for signing
        signing_data = {
            "id": template_data.get("id", ""),
            "name": template_data.get("name", ""),
            "version": template_data.get("version", ""),
            "author": template_data.get("author", ""),
            "content": template_data.get("content", ""),
        }

        # Create deterministic JSON
        message = json.dumps(signing_data, sort_keys=True).encode()
        return message


class HashManager:
    """Manager for hashing operations."""

    @staticmethod
    def hash_content(content: str, algorithm: str = "sha256") -> str:
        """
        Hash content using specified algorithm.

        Args:
            content: Content to hash
            algorithm: Hash algorithm (sha256, sha512, md5)

        Returns:
            Hex digest of hash
        """
        if algorithm == "sha256":
            hasher = hashlib.sha256()
        elif algorithm == "sha512":
            hasher = hashlib.sha512()
        elif algorithm == "md5":
            hasher = hashlib.md5()
        else:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")

        hasher.update(content.encode())
        return hasher.hexdigest()

    @staticmethod
    def verify_hash(content: str, expected_hash: str, algorithm: str = "sha256") -> bool:
        """
        Verify content hash.

        Args:
            content: Content to verify
            expected_hash: Expected hash value
            algorithm: Hash algorithm

        Returns:
            True if hash matches
        """
        actual_hash = HashManager.hash_content(content, algorithm)
        return actual_hash == expected_hash

    @staticmethod
    def create_integrity_hash(template_data: Dict[str, Any]) -> str:
        """
        Create integrity hash for template data.

        Args:
            template_data: Template data

        Returns:
            SHA256 hash of template data
        """
        # Create deterministic representation
        data_str = json.dumps(template_data, sort_keys=True)
        return HashManager.hash_content(data_str, "sha256")


class KeyRotationManager:
    """Manager for key rotation operations."""

    def __init__(self, crypto_manager: CryptoManager):
        """
        Initialize key rotation manager.

        Args:
            crypto_manager: Crypto manager instance
        """
        self.crypto = crypto_manager
        self.rotation_history: List[Dict[str, Any]] = []

    def rotate_key(
        self, old_key_id: str, new_private_key: bytes, rotation_reason: str
    ) -> Tuple[str, bytes]:
        """
        Rotate a signing key.

        Args:
            old_key_id: ID of key being rotated
            new_private_key: New private key bytes
            rotation_reason: Reason for rotation

        Returns:
            Tuple of (new_key_id, new_public_key)
        """
        # Generate new key ID
        import uuid

        new_key_id = f"key_{uuid.uuid4().hex[:8]}"

        # Get public key from private key
        private_key_obj = ed25519.Ed25519PrivateKey.from_private_bytes(new_private_key)
        public_key = private_key_obj.public_key()
        public_key_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )

        # Add new key as trusted
        self.crypto.add_trusted_key(
            new_key_id,
            public_key_bytes,
            expires_at=datetime.now() + timedelta(days=365),
            metadata={"rotated_from": old_key_id},
        )

        # Revoke old key
        if old_key_id:
            self.crypto.revoke_key(old_key_id, f"Key rotation: {rotation_reason}")

        # Record rotation
        self.rotation_history.append(
            {
                "old_key_id": old_key_id,
                "new_key_id": new_key_id,
                "rotated_at": datetime.now(),
                "reason": rotation_reason,
            }
        )

        logger.info(f"Key rotated from {old_key_id} to {new_key_id}")
        return new_key_id, public_key_bytes

    def get_rotation_history(self) -> List[Dict[str, Any]]:
        """Get key rotation history."""
        return self.rotation_history.copy()


def create_crypto_manager() -> Optional[CryptoManager]:
    """
    Factory function to create crypto manager.

    Returns:
        CryptoManager instance if crypto available, None otherwise
    """
    if not CRYPTO_AVAILABLE:
        logger.warning("Cryptography library not available")
        return None

    try:
        return CryptoManager()
    except Exception as e:
        logger.error(f"Failed to create crypto manager: {e}")
        return None
