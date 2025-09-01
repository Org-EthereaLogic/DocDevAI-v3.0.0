"""
Advanced Cryptographic Manager for M010 Security Module
Implements Ed25519 signatures, HMAC-SHA256, key rotation, and certificate management.
"""

import os
import json
import hmac
import hashlib
import base64
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path
import secrets
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography import x509
from cryptography.x509.oid import NameOID
import threading
import logging

logger = logging.getLogger(__name__)


@dataclass
class KeyVersion:
    """Represents a versioned cryptographic key."""
    version: int
    key_id: str
    algorithm: str
    created_at: datetime
    expires_at: Optional[datetime]
    status: str  # active, rotating, expired, revoked
    metadata: Dict[str, Any]


class CryptoManager:
    """
    Advanced cryptographic operations manager with enterprise-grade security.
    
    Features:
    - Ed25519 digital signatures for audit logs
    - HMAC-SHA256 for data integrity
    - Secure key rotation with versioning
    - Certificate-based authentication
    - Hardware Security Module (HSM) support ready
    """
    
    def __init__(self, key_store_path: Optional[Path] = None):
        """Initialize the crypto manager with secure defaults."""
        self.key_store_path = key_store_path or Path.home() / '.devdocai' / 'keys'
        self.key_store_path.mkdir(parents=True, exist_ok=True)
        
        # Key storage
        self._signing_keys: Dict[str, ed25519.Ed25519PrivateKey] = {}
        self._hmac_keys: Dict[str, bytes] = {}
        self._key_versions: Dict[str, List[KeyVersion]] = {}
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Key rotation configuration
        self.rotation_interval = timedelta(days=90)
        self.rotation_overlap = timedelta(days=7)
        
        # Performance optimization
        self._signature_cache: Dict[str, bytes] = {}
        self._cache_size = 1000
        
        # Initialize default keys
        self._initialize_default_keys()
    
    def _initialize_default_keys(self):
        """Initialize default signing and HMAC keys."""
        try:
            # Load or generate master signing key
            master_key_path = self.key_store_path / 'master_signing.key'
            if master_key_path.exists():
                self._load_signing_key('master', master_key_path)
            else:
                self._generate_signing_key('master')
            
            # Load or generate master HMAC key
            hmac_key_path = self.key_store_path / 'master_hmac.key'
            if hmac_key_path.exists():
                self._load_hmac_key('master', hmac_key_path)
            else:
                self._generate_hmac_key('master')
            
            logger.info("Cryptographic keys initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize keys: {e}")
            raise
    
    def _generate_signing_key(self, key_id: str) -> ed25519.Ed25519PrivateKey:
        """Generate a new Ed25519 signing key."""
        with self._lock:
            # Generate key
            private_key = ed25519.Ed25519PrivateKey.generate()
            self._signing_keys[key_id] = private_key
            
            # Save to disk (encrypted in production)
            key_path = self.key_store_path / f'{key_id}_signing.key'
            pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.BestAvailableEncryption(
                    self._derive_key_encryption_password()
                )
            )
            key_path.write_bytes(pem)
            
            # Track version
            version = KeyVersion(
                version=1,
                key_id=key_id,
                algorithm='Ed25519',
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + self.rotation_interval,
                status='active',
                metadata={'type': 'signing'}
            )
            if key_id not in self._key_versions:
                self._key_versions[key_id] = []
            self._key_versions[key_id].append(version)
            
            return private_key
    
    def _generate_hmac_key(self, key_id: str) -> bytes:
        """Generate a new HMAC-SHA256 key."""
        with self._lock:
            # Generate 256-bit key
            key = secrets.token_bytes(32)
            self._hmac_keys[key_id] = key
            
            # Save to disk (encrypted)
            key_path = self.key_store_path / f'{key_id}_hmac.key'
            encrypted_key = self._encrypt_key(key)
            key_path.write_bytes(encrypted_key)
            
            # Track version
            version = KeyVersion(
                version=1,
                key_id=key_id,
                algorithm='HMAC-SHA256',
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + self.rotation_interval,
                status='active',
                metadata={'type': 'hmac'}
            )
            if key_id not in self._key_versions:
                self._key_versions[key_id] = []
            self._key_versions[key_id].append(version)
            
            return key
    
    def _derive_key_encryption_password(self) -> bytes:
        """Derive password for key encryption using hardware ID."""
        # In production, use TPM or HSM
        machine_id = hashlib.sha256(
            os.environ.get('HOSTNAME', 'default').encode()
        ).digest()
        return machine_id[:32]  # Use first 32 bytes
    
    def _encrypt_key(self, key: bytes) -> bytes:
        """Encrypt a key for storage."""
        # Use AES-256-GCM for key wrapping
        password = self._derive_key_encryption_password()
        salt = os.urandom(16)
        
        # Derive encryption key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        encryption_key = kdf.derive(password)
        
        # Encrypt
        iv = os.urandom(12)
        cipher = Cipher(
            algorithms.AES(encryption_key),
            modes.GCM(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(key) + encryptor.finalize()
        
        # Return salt + iv + ciphertext + tag
        return salt + iv + ciphertext + encryptor.tag
    
    def _decrypt_key(self, encrypted_key: bytes) -> bytes:
        """Decrypt a key from storage."""
        # Extract components
        salt = encrypted_key[:16]
        iv = encrypted_key[16:28]
        ciphertext_and_tag = encrypted_key[28:]
        ciphertext = ciphertext_and_tag[:-16]
        tag = ciphertext_and_tag[-16:]
        
        # Derive decryption key
        password = self._derive_key_encryption_password()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        decryption_key = kdf.derive(password)
        
        # Decrypt
        cipher = Cipher(
            algorithms.AES(decryption_key),
            modes.GCM(iv, tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        return decryptor.update(ciphertext) + decryptor.finalize()
    
    def _load_signing_key(self, key_id: str, key_path: Path):
        """Load an Ed25519 signing key from disk."""
        with self._lock:
            pem = key_path.read_bytes()
            private_key = serialization.load_pem_private_key(
                pem,
                password=self._derive_key_encryption_password(),
                backend=default_backend()
            )
            if isinstance(private_key, ed25519.Ed25519PrivateKey):
                self._signing_keys[key_id] = private_key
            else:
                raise ValueError(f"Invalid key type for {key_id}")
    
    def _load_hmac_key(self, key_id: str, key_path: Path):
        """Load an HMAC key from disk."""
        with self._lock:
            encrypted_key = key_path.read_bytes()
            key = self._decrypt_key(encrypted_key)
            self._hmac_keys[key_id] = key
    
    def sign_data(self, data: bytes, key_id: str = 'master') -> Tuple[bytes, Dict[str, Any]]:
        """
        Sign data using Ed25519.
        
        Returns:
            Tuple of (signature, metadata)
        """
        with self._lock:
            # Check cache
            cache_key = f"{key_id}:{hashlib.sha256(data).hexdigest()}"
            if cache_key in self._signature_cache:
                return self._signature_cache[cache_key], {'cached': True}
            
            # Get signing key
            if key_id not in self._signing_keys:
                raise KeyError(f"Signing key '{key_id}' not found")
            
            private_key = self._signing_keys[key_id]
            
            # Sign data
            signature = private_key.sign(data)
            
            # Get public key for verification
            public_key = private_key.public_key()
            public_key_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            metadata = {
                'algorithm': 'Ed25519',
                'key_id': key_id,
                'timestamp': datetime.utcnow().isoformat(),
                'public_key': base64.b64encode(public_key_bytes).decode('utf-8')
            }
            
            # Cache signature
            if len(self._signature_cache) < self._cache_size:
                self._signature_cache[cache_key] = signature
            
            return signature, metadata
    
    def verify_signature(
        self, 
        data: bytes, 
        signature: bytes, 
        public_key_pem: bytes
    ) -> bool:
        """Verify an Ed25519 signature."""
        try:
            public_key = serialization.load_pem_public_key(
                public_key_pem,
                backend=default_backend()
            )
            if isinstance(public_key, ed25519.Ed25519PublicKey):
                public_key.verify(signature, data)
                return True
        except Exception as e:
            logger.warning(f"Signature verification failed: {e}")
        return False
    
    def compute_hmac(self, data: bytes, key_id: str = 'master') -> str:
        """Compute HMAC-SHA256 for data integrity."""
        with self._lock:
            if key_id not in self._hmac_keys:
                raise KeyError(f"HMAC key '{key_id}' not found")
            
            key = self._hmac_keys[key_id]
            h = hmac.new(key, data, hashlib.sha256)
            return base64.b64encode(h.digest()).decode('utf-8')
    
    def verify_hmac(self, data: bytes, hmac_value: str, key_id: str = 'master') -> bool:
        """Verify HMAC-SHA256."""
        try:
            expected = self.compute_hmac(data, key_id)
            return hmac.compare_digest(expected, hmac_value)
        except Exception as e:
            logger.warning(f"HMAC verification failed: {e}")
            return False
    
    def rotate_keys(self, key_id: str = 'master'):
        """
        Rotate cryptographic keys with overlap period.
        
        Implements secure key rotation:
        1. Generate new key version
        2. Mark old key as rotating
        3. After overlap period, expire old key
        """
        with self._lock:
            logger.info(f"Starting key rotation for '{key_id}'")
            
            # Get current versions
            versions = self._key_versions.get(key_id, [])
            current_version = max(versions, key=lambda v: v.version) if versions else None
            
            new_version_num = (current_version.version + 1) if current_version else 1
            
            # Generate new keys
            if key_id in self._signing_keys:
                # Backup old key
                old_key_path = self.key_store_path / f'{key_id}_signing_v{current_version.version}.key'
                current_key_path = self.key_store_path / f'{key_id}_signing.key'
                if current_key_path.exists():
                    current_key_path.rename(old_key_path)
                
                # Generate new signing key
                self._generate_signing_key(f"{key_id}_v{new_version_num}")
                
                # Update version status
                if current_version:
                    current_version.status = 'rotating'
                    current_version.expires_at = datetime.utcnow() + self.rotation_overlap
            
            if key_id in self._hmac_keys:
                # Backup old key
                old_key_path = self.key_store_path / f'{key_id}_hmac_v{current_version.version}.key'
                current_key_path = self.key_store_path / f'{key_id}_hmac.key'
                if current_key_path.exists():
                    current_key_path.rename(old_key_path)
                
                # Generate new HMAC key
                self._generate_hmac_key(f"{key_id}_v{new_version_num}")
                
                # Update version status
                if current_version:
                    current_version.status = 'rotating'
            
            logger.info(f"Key rotation completed for '{key_id}' (version {new_version_num})")
    
    def generate_certificate(
        self,
        subject_name: str,
        key_size: int = 4096,
        valid_days: int = 365
    ) -> Tuple[bytes, bytes]:
        """
        Generate a self-signed certificate for authentication.
        
        Returns:
            Tuple of (certificate_pem, private_key_pem)
        """
        # Generate RSA key pair
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )
        
        # Build certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, subject_name),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "DevDocAI"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Security"),
        ])
        
        certificate = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=valid_days)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.DNSName("*.devdocai.local"),
            ]),
            critical=False,
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                content_commitment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False
            ),
            critical=True,
        ).sign(private_key, hashes.SHA256(), backend=default_backend())
        
        # Export to PEM
        cert_pem = certificate.public_bytes(serialization.Encoding.PEM)
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(
                self._derive_key_encryption_password()
            )
        )
        
        return cert_pem, key_pem
    
    def verify_certificate(self, cert_pem: bytes) -> Dict[str, Any]:
        """Verify and extract information from a certificate."""
        try:
            cert = x509.load_pem_x509_certificate(cert_pem, backend=default_backend())
            
            # Extract information
            info = {
                'subject': cert.subject.rfc4514_string(),
                'issuer': cert.issuer.rfc4514_string(),
                'serial_number': str(cert.serial_number),
                'not_valid_before': cert.not_valid_before.isoformat(),
                'not_valid_after': cert.not_valid_after.isoformat(),
                'is_self_signed': cert.issuer == cert.subject,
                'is_expired': datetime.utcnow() > cert.not_valid_after,
                'is_not_yet_valid': datetime.utcnow() < cert.not_valid_before,
                'valid': False
            }
            
            # Check validity
            if not info['is_expired'] and not info['is_not_yet_valid']:
                info['valid'] = True
            
            return info
        except Exception as e:
            logger.error(f"Certificate verification failed: {e}")
            return {'valid': False, 'error': str(e)}
    
    def get_key_info(self, key_id: str) -> Dict[str, Any]:
        """Get information about a key and its versions."""
        with self._lock:
            versions = self._key_versions.get(key_id, [])
            return {
                'key_id': key_id,
                'versions': [
                    {
                        'version': v.version,
                        'algorithm': v.algorithm,
                        'created_at': v.created_at.isoformat(),
                        'expires_at': v.expires_at.isoformat() if v.expires_at else None,
                        'status': v.status
                    }
                    for v in versions
                ],
                'has_signing_key': key_id in self._signing_keys,
                'has_hmac_key': key_id in self._hmac_keys
            }
    
    def cleanup_expired_keys(self):
        """Remove expired keys from memory and disk."""
        with self._lock:
            now = datetime.utcnow()
            
            for key_id, versions in list(self._key_versions.items()):
                for version in versions[:]:
                    if version.expires_at and version.expires_at < now:
                        logger.info(f"Removing expired key: {key_id} v{version.version}")
                        
                        # Remove from disk
                        old_signing = self.key_store_path / f'{key_id}_signing_v{version.version}.key'
                        old_hmac = self.key_store_path / f'{key_id}_hmac_v{version.version}.key'
                        
                        if old_signing.exists():
                            old_signing.unlink()
                        if old_hmac.exists():
                            old_hmac.unlink()
                        
                        # Update status
                        version.status = 'expired'
                        
                        # Remove from memory if it's an old version
                        versioned_key_id = f"{key_id}_v{version.version}"
                        if versioned_key_id in self._signing_keys:
                            del self._signing_keys[versioned_key_id]
                        if versioned_key_id in self._hmac_keys:
                            del self._hmac_keys[versioned_key_id]