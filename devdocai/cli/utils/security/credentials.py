"""
Secure credential management for CLI.

Provides encryption, secure storage, and masking of sensitive data.
"""

import os
import re
import json
import base64
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import secrets

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class CredentialError(Exception):
    """Credential management error."""
    pass


class SecureCredentialManager:
    """
    Secure credential storage and management.
    
    Features:
    - AES-256-GCM encryption
    - System keyring integration
    - Secure memory handling
    - Credential rotation
    - PII masking
    """
    
    SERVICE_NAME = "devdocai"
    MASTER_KEY_NAME = "master_key"
    SALT_SIZE = 32
    KEY_ROTATION_DAYS = 90
    
    # Sensitive data patterns for masking
    SENSITIVE_PATTERNS = [
        # API Keys and Tokens
        (r'(api[_-]?key|apikey|api_secret|api[_-]?token)[\s:=]+(["\']?)([A-Za-z0-9_\-]{20,})(\2)',
         r'\1\2[REDACTED_API_KEY]\4'),
        (r'(bearer|token)[\s:]+([A-Za-z0-9_\-\.]{20,})',
         r'\1 [REDACTED_TOKEN]'),
        
        # AWS Credentials
        (r'(AKIA|A3T|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}',
         '[REDACTED_AWS_ACCESS_KEY]'),
        (r'[A-Za-z0-9/+=]{40}',
         '[REDACTED_AWS_SECRET_KEY]'),
        
        # Database URLs
        (r'(mongodb\+srv|postgres|postgresql|mysql|redis)://[^:]+:([^@]+)@',
         r'\1://[REDACTED_USER]:[REDACTED_PASS]@'),
        
        # Email Addresses
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
         '[REDACTED_EMAIL]'),
        
        # Credit Card Numbers
        (r'\b(?:\d[ -]*?){13,19}\b',
         '[REDACTED_CARD_NUMBER]'),
        
        # Social Security Numbers
        (r'\b\d{3}-\d{2}-\d{4}\b',
         '[REDACTED_SSN]'),
        
        # JWT Tokens
        (r'eyJ[A-Za-z0-9_\-]+\.eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+',
         '[REDACTED_JWT]'),
        
        # Private Keys
        (r'-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----[\s\S]+?-----END (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----',
         '[REDACTED_PRIVATE_KEY]'),
    ]
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize credential manager.
        
        Args:
            config_dir: Directory for storing encrypted credentials
        """
        self.config_dir = config_dir or (Path.home() / '.devdocai' / 'credentials')
        self.config_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        
        self.credentials_file = self.config_dir / 'credentials.enc'
        self.metadata_file = self.config_dir / 'metadata.json'
        
        self._init_encryption()
        self._credentials_cache: Dict[str, Any] = {}
        
    def _init_encryption(self):
        """Initialize encryption keys."""
        # Try to get master key from system keyring
        if KEYRING_AVAILABLE:
            try:
                master_key = keyring.get_password(self.SERVICE_NAME, self.MASTER_KEY_NAME)
                if not master_key:
                    master_key = self._generate_master_key()
                    keyring.set_password(self.SERVICE_NAME, self.MASTER_KEY_NAME, master_key)
            except Exception:
                # Fallback to file-based key storage
                master_key = self._get_file_based_key()
        else:
            master_key = self._get_file_based_key()
        
        # Initialize AES-GCM cipher
        self.cipher = AESGCM(base64.b64decode(master_key))
        
        # Check if key rotation is needed
        self._check_key_rotation()
    
    def _generate_master_key(self) -> str:
        """Generate a new master encryption key."""
        key = AESGCM.generate_key(bit_length=256)
        return base64.b64encode(key).decode('utf-8')
    
    def _get_file_based_key(self) -> str:
        """Get or create file-based encryption key."""
        key_file = self.config_dir / '.key'
        
        if key_file.exists():
            # Set restrictive permissions
            os.chmod(key_file, 0o600)
            with open(key_file, 'r') as f:
                return f.read().strip()
        else:
            # Generate new key
            key = self._generate_master_key()
            with open(key_file, 'w') as f:
                f.write(key)
            os.chmod(key_file, 0o600)
            return key
    
    def _check_key_rotation(self):
        """Check if encryption key needs rotation."""
        if not self.metadata_file.exists():
            self._save_metadata({'key_created': datetime.now().isoformat()})
            return
        
        metadata = self._load_metadata()
        key_created = datetime.fromisoformat(metadata.get('key_created', datetime.now().isoformat()))
        
        if datetime.now() - key_created > timedelta(days=self.KEY_ROTATION_DAYS):
            # Key rotation needed
            self._rotate_keys()
    
    def _rotate_keys(self):
        """Rotate encryption keys."""
        # Load existing credentials with old key
        credentials = self._load_all_credentials()
        
        # Generate new key
        new_key = self._generate_master_key()
        old_cipher = self.cipher
        self.cipher = AESGCM(base64.b64decode(new_key))
        
        # Re-encrypt all credentials with new key
        for service, creds in credentials.items():
            self._save_credential_internal(service, creds)
        
        # Update master key
        if KEYRING_AVAILABLE:
            try:
                keyring.set_password(self.SERVICE_NAME, self.MASTER_KEY_NAME, new_key)
            except Exception:
                pass
        
        # Update file-based key
        key_file = self.config_dir / '.key'
        with open(key_file, 'w') as f:
            f.write(new_key)
        os.chmod(key_file, 0o600)
        
        # Update metadata
        self._save_metadata({'key_created': datetime.now().isoformat()})
    
    def store_credential(self, service: str, username: str, password: str,
                        metadata: Optional[Dict[str, Any]] = None):
        """
        Store encrypted credentials.
        
        Args:
            service: Service name (e.g., 'github', 'openai')
            username: Username or identifier
            password: Password or API key
            metadata: Additional metadata
        """
        credential_data = {
            'username': username,
            'password': password,
            'metadata': metadata or {},
            'created': datetime.now().isoformat(),
            'accessed': datetime.now().isoformat()
        }
        
        self._save_credential_internal(service, credential_data)
        
        # Update cache
        self._credentials_cache[service] = credential_data
    
    def _save_credential_internal(self, service: str, data: Dict[str, Any]):
        """Internal method to save encrypted credentials."""
        # Load all credentials
        all_credentials = self._load_all_credentials()
        all_credentials[service] = data
        
        # Serialize and encrypt
        plaintext = json.dumps(all_credentials).encode('utf-8')
        nonce = os.urandom(12)
        ciphertext = self.cipher.encrypt(nonce, plaintext, None)
        
        # Save encrypted data
        encrypted_data = nonce + ciphertext
        with open(self.credentials_file, 'wb') as f:
            f.write(encrypted_data)
        
        # Set restrictive permissions
        os.chmod(self.credentials_file, 0o600)
    
    def get_credential(self, service: str, username: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieve decrypted credentials.
        
        Args:
            service: Service name
            username: Optional username filter
            
        Returns:
            Credential data or None if not found
        """
        # Check cache first
        if service in self._credentials_cache:
            cred = self._credentials_cache[service]
            if not username or cred.get('username') == username:
                # Update access time
                cred['accessed'] = datetime.now().isoformat()
                return cred
        
        # Load from file
        all_credentials = self._load_all_credentials()
        
        if service in all_credentials:
            cred = all_credentials[service]
            if not username or cred.get('username') == username:
                # Update access time
                cred['accessed'] = datetime.now().isoformat()
                self._save_credential_internal(service, cred)
                
                # Update cache
                self._credentials_cache[service] = cred
                return cred
        
        return None
    
    def _load_all_credentials(self) -> Dict[str, Any]:
        """Load all encrypted credentials."""
        if not self.credentials_file.exists():
            return {}
        
        try:
            with open(self.credentials_file, 'rb') as f:
                encrypted_data = f.read()
            
            if len(encrypted_data) < 12:
                return {}
            
            nonce = encrypted_data[:12]
            ciphertext = encrypted_data[12:]
            
            plaintext = self.cipher.decrypt(nonce, ciphertext, None)
            return json.loads(plaintext.decode('utf-8'))
        except Exception as e:
            raise CredentialError(f"Failed to decrypt credentials: {e}")
    
    def delete_credential(self, service: str):
        """
        Delete stored credentials.
        
        Args:
            service: Service name
        """
        all_credentials = self._load_all_credentials()
        
        if service in all_credentials:
            del all_credentials[service]
            
            # Save updated credentials
            if all_credentials:
                plaintext = json.dumps(all_credentials).encode('utf-8')
                nonce = os.urandom(12)
                ciphertext = self.cipher.encrypt(nonce, plaintext, None)
                
                encrypted_data = nonce + ciphertext
                with open(self.credentials_file, 'wb') as f:
                    f.write(encrypted_data)
            else:
                # No credentials left, remove file
                self.credentials_file.unlink(missing_ok=True)
        
        # Clear from cache
        self._credentials_cache.pop(service, None)
    
    def list_services(self) -> List[str]:
        """List all stored service names."""
        all_credentials = self._load_all_credentials()
        return list(all_credentials.keys())
    
    def mask_sensitive_data(self, text: str, custom_patterns: Optional[List[tuple]] = None) -> str:
        """
        Mask sensitive data in text.
        
        Args:
            text: Text containing potential sensitive data
            custom_patterns: Additional patterns to mask
            
        Returns:
            Text with sensitive data masked
        """
        masked = text
        
        # Apply standard patterns
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            masked = re.sub(pattern, replacement, masked, flags=re.IGNORECASE | re.MULTILINE)
        
        # Apply custom patterns
        if custom_patterns:
            for pattern, replacement in custom_patterns:
                masked = re.sub(pattern, replacement, masked, flags=re.IGNORECASE | re.MULTILINE)
        
        return masked
    
    def validate_api_key(self, api_key: str, service: str) -> bool:
        """
        Validate API key format for known services.
        
        Args:
            api_key: API key to validate
            service: Service name
            
        Returns:
            True if valid format
        """
        validators = {
            'openai': r'^sk-[A-Za-z0-9]{48}$',
            'anthropic': r'^sk-ant-[A-Za-z0-9]{95}$',
            'github': r'^gh[pousr]_[A-Za-z0-9]{36}$',
            'aws': r'^AKIA[A-Z0-9]{16}$',
            'google': r'^AIza[A-Za-z0-9_\-]{35}$',
        }
        
        if service.lower() in validators:
            pattern = validators[service.lower()]
            return bool(re.match(pattern, api_key))
        
        # Generic validation for unknown services
        return len(api_key) >= 16 and not api_key.isspace()
    
    def _save_metadata(self, metadata: Dict[str, Any]):
        """Save metadata file."""
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        os.chmod(self.metadata_file, 0o600)
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load metadata file."""
        if not self.metadata_file.exists():
            return {}
        
        with open(self.metadata_file, 'r') as f:
            return json.load(f)
    
    def export_credentials(self, password: str) -> str:
        """
        Export credentials with password protection.
        
        Args:
            password: Password for export encryption
            
        Returns:
            Base64 encoded encrypted export
        """
        # Derive key from password
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        
        # Encrypt credentials
        cipher = Fernet(key)
        all_credentials = self._load_all_credentials()
        plaintext = json.dumps(all_credentials).encode('utf-8')
        encrypted = cipher.encrypt(plaintext)
        
        # Combine salt and encrypted data
        export_data = salt + encrypted
        
        return base64.b64encode(export_data).decode('utf-8')
    
    def import_credentials(self, export_data: str, password: str):
        """
        Import credentials from encrypted export.
        
        Args:
            export_data: Base64 encoded encrypted export
            password: Password for decryption
        """
        # Derive key from password
        encrypted = base64.b64decode(export_data)
        
        # Try to decrypt (will fail if wrong password)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=encrypted[:16],  # Extract salt
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        
        cipher = Fernet(key)
        plaintext = cipher.decrypt(encrypted[16:])
        credentials = json.loads(plaintext.decode('utf-8'))
        
        # Import each credential
        for service, cred_data in credentials.items():
            self._save_credential_internal(service, cred_data)