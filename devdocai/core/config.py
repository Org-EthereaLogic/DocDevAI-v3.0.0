"""
M001: Configuration Manager - Privacy-first configuration management for DevDocAI.

This module provides centralized configuration with privacy defaults, memory detection,
and secure API key management using AES-256-GCM encryption.

Performance targets:
- Retrieval: 19M ops/sec
- Validation: 4M ops/sec
- Coverage: 95% minimum
"""

import os
import psutil
import yaml
import hashlib
import secrets
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union
from functools import lru_cache
from threading import Lock
from datetime import datetime

from pydantic import BaseModel, Field, ValidationError, validator
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from argon2 import PasswordHasher, Parameters, Type
import gc
from argon2.exceptions import VerifyMismatchError
import dotenv

logger = logging.getLogger(__name__)


class SecurityConfig(BaseModel):
    """Security configuration with privacy-first defaults."""
    
    privacy_mode: str = Field(default="local_only", pattern="^(local_only|hybrid|cloud)$")
    telemetry_enabled: bool = Field(default=False)
    cloud_features: bool = Field(default=False)
    dsr_enabled: bool = Field(default=True, description="GDPR/CCPA Data Subject Rights")
    encryption_enabled: bool = Field(default=True)
    secure_delete_passes: int = Field(default=3, ge=1, le=7)
    
    @validator("cloud_features")
    def validate_cloud_features(cls, v, values):
        """Ensure cloud features align with privacy mode."""
        if v and values.get("privacy_mode", "local_only") == "local_only":
            raise ValueError("Cloud features cannot be enabled in local_only mode")
        return v


class MemoryConfig(BaseModel):
    """Memory configuration based on system resources."""
    
    mode: str = Field(pattern="^(baseline|standard|enhanced|performance)$")
    cache_size: int = Field(ge=100, le=100000)
    max_file_size: int = Field(ge=1048576, le=1073741824)  # 1MB to 1GB
    optimization_level: int = Field(ge=0, le=3)
    
    @validator("cache_size")
    def validate_cache_size(cls, v, values):
        """Ensure cache size matches mode."""
        mode_limits = {
            "baseline": 1000,
            "standard": 5000,
            "enhanced": 10000,
            "performance": 50000
        }
        mode = values.get("mode", "baseline")
        if mode in mode_limits and v > mode_limits[mode]:
            return mode_limits[mode]
        return v


class DevDocAIConfig(BaseModel):
    """Main configuration schema for DevDocAI."""
    
    version: str = Field(default="3.0.0")
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    memory: Optional[MemoryConfig] = None
    paths: Dict[str, str] = Field(default_factory=lambda: {
        "data": "./data",
        "templates": "./templates",
        "output": "./output",
        "logs": "./logs"
    })
    api_providers: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    features: Dict[str, bool] = Field(default_factory=lambda: {
        "auto_save": True,
        "hot_reload": True,
        "validation_strict": True
    })


class ConfigurationManager:
    """
    M001: Central configuration management with privacy-first defaults.
    
    Provides secure, high-performance configuration management with:
    - Privacy-first defaults (local-only, no telemetry)
    - Automatic memory mode detection
    - AES-256-GCM encryption for sensitive data
    - Hot-reload capability
    - Thread-safe operations
    """
    
    _instance = None
    _lock = Lock()
    _config_cache = {}
    _cache_timestamp = {}
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern for global configuration access."""
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize Configuration Manager.
        
        Args:
            config_path: Path to configuration file (default: .devdocai.yml)
        """
        if hasattr(self, '_initialized'):
            return
            
        # Define safe config root (application config directory in user's home)
        safe_root = (Path.home() / ".devdocai").resolve()
        safe_root.mkdir(parents=True, exist_ok=True)
        # Get raw config path (from argument or env variable)
        raw_config_path = config_path or os.getenv("DEVDOCAI_CONFIG", ".devdocai.yml")
        self.config_path = self._validate_config_path(raw_config_path, safe_root)
        self.env_file = safe_root / ".env"
        
        # Load environment variables
        if self.env_file.exists():
            dotenv.load_dotenv(self.env_file)
        
        # Initialize security components
        self._hasher = PasswordHasher()
        self._cipher_key = None
        
        # Initialize configuration
        self._config = DevDocAIConfig()
        self._detect_memory_mode()
        
        # Load configuration file if exists
        if self.config_path.exists():
            self.load_config()
        
        # Mark as initialized
        self._initialized = True
        logger.info(f"ConfigurationManager initialized with memory mode: {self._config.memory.mode}")
    
    @staticmethod
    def _validate_config_path(raw_path: Union[str, Path], safe_root: Path) -> Path:
        """
        Validate config file path and resolve to absolute path.
        For testing and development, allows paths outside safe_root.
        """
        candidate_path = Path(raw_path).expanduser().resolve()
        
        # Must be a file or not exist (not a directory)
        if candidate_path.exists() and candidate_path.is_dir():
            logger.warning(f"Config path is a directory: {candidate_path}")
            return safe_root / ".devdocai.yml"
        
        # For production, warn if outside safe root but still allow it
        try:
            _ = candidate_path.relative_to(safe_root)
        except ValueError:
            # Path is outside safe root - log but allow for testing/dev
            if os.getenv("DEVDOCAI_TESTING") != "true":
                logger.info(f"Config file outside safe root: {candidate_path}")
        
        return candidate_path
    
    def _detect_memory_mode(self) -> str:
        """
        Detect appropriate memory mode based on available RAM.
        
        Returns:
            Memory mode: baseline, standard, enhanced, or performance
        """
        try:
            available_ram = psutil.virtual_memory().available / (1024 * 1024 * 1024)  # GB
            
            if available_ram < 2:
                mode = "baseline"
                cache_size = 1000
                optimization = 0
            elif available_ram < 4:
                mode = "standard"
                cache_size = 5000
                optimization = 1
            elif available_ram < 8:
                mode = "enhanced"
                cache_size = 10000
                optimization = 2
            else:
                mode = "performance"
                cache_size = 50000
                optimization = 3
            
            self._config.memory = MemoryConfig(
                mode=mode,
                cache_size=cache_size,
                max_file_size=104857600,  # 100MB default
                optimization_level=optimization
            )
            
            return mode
            
        except Exception as e:
            logger.warning(f"Memory detection failed, using baseline: {e}")
            self._config.memory = MemoryConfig(
                mode="baseline",
                cache_size=1000,
                max_file_size=10485760,
                optimization_level=0
            )
            return "baseline"
    
    @lru_cache(maxsize=10000)
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value with caching for performance.
        
        Args:
            key: Dot-notation key (e.g., 'security.privacy_mode')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        try:
            # First check dynamic config
            if hasattr(self, '_dynamic_config') and key in self._dynamic_config:
                return self._dynamic_config[key]
            
            # Then check main config
            parts = key.split('.')
            value = self._config.dict()
            
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    # If not found in main config, check dynamic config with nested keys
                    if hasattr(self, '_dynamic_config'):
                        return self._dynamic_config.get(key, default)
                    return default
                    
                if value is None:
                    # If not found in main config, check dynamic config
                    if hasattr(self, '_dynamic_config'):
                        return self._dynamic_config.get(key, default)
                    return default
                    
            return value
            
        except Exception as e:
            logger.error(f"Error getting config key '{key}': {e}")
            return default
    
    def set(self, key: str, value: Any) -> bool:
        """
        Set configuration value with validation.
        
        Args:
            key: Dot-notation key
            value: Value to set
            
        Returns:
            Success status
        """
        try:
            # Clear cache for this key
            self.get.cache_clear()
            
            with self._lock:
                parts = key.split('.')
                config_dict = self._config.dict()
                
                # Navigate to parent
                current = config_dict
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    elif not isinstance(current[part], dict):
                        current[part] = {}
                    current = current[part]
                
                # Set value
                current[parts[-1]] = value
                
                # Update the configuration with the new dictionary
                # For dynamic keys, we need to create a new config that includes existing + new values
                existing_dict = {
                    'version': self._config.version,
                    'security': self._config.security.dict() if self._config.security else {},
                    'memory': self._config.memory.dict() if self._config.memory else None,
                    'paths': self._config.paths,
                    'api_providers': self._config.api_providers,
                    'features': self._config.features
                }
                
                # Merge the new values
                for key_path, val in self._flatten_dict(config_dict).items():
                    self._set_nested_dict(existing_dict, key_path, val)
                
                # Create new config instance
                self._config = DevDocAIConfig(**existing_dict)
                
                # Also store dynamic values that don't fit the schema
                if not hasattr(self, '_dynamic_config'):
                    self._dynamic_config = {}
                self._dynamic_config[key] = value
            
            return True
            
        except ValidationError as e:
            logger.error(f"Validation error setting '{key}': {e}")
            return False
        except Exception as e:
            logger.error(f"Error setting config key '{key}': {e}")
            return False
    
    def _flatten_dict(self, d, parent_key='', sep='.'):
        """Flatten nested dictionary."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    def _set_nested_dict(self, d, key_path, value):
        """Set value in nested dictionary using dot notation."""
        parts = key_path.split('.')
        current = d
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value
    
    def load_config(self, path: Optional[str] = None) -> bool:
        """
        Load configuration from YAML file with validation.
        
        Args:
            path: Configuration file path
            
        Returns:
            Success status
        """
        safe_root = (Path.home() / ".devdocai").resolve()
        raw_config_path = path if path is not None else self.config_path
        config_path_to_use = self._validate_config_path(raw_config_path, safe_root)

        try:
            if not config_path_to_use.exists():
                logger.warning(f"Configuration file not found: {config_path_to_use}")
                return False

            with open(config_path_to_use, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Handle empty file
            if not config_data:
                config_data = {}
            
            # Validate and update configuration
            self._config = DevDocAIConfig(**config_data)
            
            # Clear cache
            self.get.cache_clear()
            
            logger.info(f"Configuration loaded from {config_path_to_use}")
            return True
            
        except ValidationError as e:
            logger.error(f"Invalid configuration: {e}")
            return False
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return False
    
    def save_config(self, path: Optional[str] = None) -> bool:
        """
        Save current configuration to YAML file.
        
        Args:
            path: Output file path
            
        Returns:
            Success status
        """
        config_path = Path(path) if path else self.config_path
        
        try:
            config_dict = self._config.dict(exclude_defaults=False)
            
            with open(config_path, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
            
            logger.info(f"Configuration saved to {config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            return False
    
    def encrypt_api_keys(self, keys: Dict[str, str]) -> Dict[str, str]:
        """
        Encrypt API keys using AES-256-GCM.
        
        Args:
            keys: Dictionary of API keys to encrypt
            
        Returns:
            Dictionary with encrypted keys
        """
        if not self._config.security.encryption_enabled:
            return keys
        
        try:
            encrypted = {}
            for name, key in keys.items():
                # Validate input
                if not isinstance(name, str) or not isinstance(key, str):
                    raise ValueError(f"Invalid key format for {name}")
                
                # Generate random salt for this encryption
                salt = os.urandom(32)
                
                # Derive key with random salt
                self._cipher_key = self._derive_key(salt=salt)
                
                # Generate nonce for this encryption
                nonce = os.urandom(12)
                
                # Create cipher
                cipher = Cipher(
                    algorithms.AES(self._cipher_key),
                    modes.GCM(nonce),
                    backend=default_backend()
                )
                encryptor = cipher.encryptor()
                
                # Encrypt the key
                ciphertext = encryptor.update(key.encode()) + encryptor.finalize()
                
                # Store with salt, nonce, tag, and version
                encrypted[name] = {
                    'ciphertext': ciphertext.hex(),
                    'nonce': nonce.hex(),
                    'tag': encryptor.tag.hex(),
                    'salt': salt.hex(),
                    'version': 2  # Version 2 uses random salts
                }
                
                # Secure memory cleanup
                self._secure_wipe()
            
            return encrypted
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            # Secure cleanup on error
            self._secure_wipe()
            raise
    
    def decrypt_api_keys(self, encrypted_keys: Dict[str, Dict]) -> Dict[str, str]:
        """
        Decrypt API keys.
        
        Args:
            encrypted_keys: Dictionary with encrypted key data
            
        Returns:
            Dictionary with decrypted keys
        """
        if not self._config.security.encryption_enabled:
            return encrypted_keys
        
        try:
            decrypted = {}
            for name, key_data in encrypted_keys.items():
                # Validate encrypted structure
                if not self._validate_encrypted_structure(key_data):
                    raise ValueError(f"Invalid encrypted data structure for {name}")
                
                # Extract components
                ciphertext = bytes.fromhex(key_data['ciphertext'])
                nonce = bytes.fromhex(key_data['nonce'])
                tag = bytes.fromhex(key_data['tag'])
                
                # Handle version-specific decryption
                version = key_data.get('version', 1)
                
                if version == 2 and 'salt' in key_data:
                    # Version 2: Use provided salt
                    salt = bytes.fromhex(key_data['salt'])
                    self._cipher_key = self._derive_key(salt=salt)
                else:
                    # Version 1 (legacy): Use fixed salt for backward compatibility
                    self._cipher_key = self._derive_key_legacy()
                
                # Create cipher
                cipher = Cipher(
                    algorithms.AES(self._cipher_key),
                    modes.GCM(nonce, tag),
                    backend=default_backend()
                )
                decryptor = cipher.decryptor()
                
                # Decrypt
                plaintext = decryptor.update(ciphertext) + decryptor.finalize()
                decrypted[name] = plaintext.decode()
                
                # Secure memory cleanup after each key
                self._secure_wipe()
            
            return decrypted
            
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            # Secure cleanup on error
            self._secure_wipe()
            raise
    
    def _derive_key(self, salt: bytes = None) -> bytes:
        """
        Derive encryption key using Argon2id with secure parameters.
        
        Args:
            salt: Random salt for key derivation (32 bytes)
            
        Returns:
            32-byte encryption key
        """
        # Get or create master password - but store it in the instance to ensure consistency
        if not hasattr(self, '_master_password'):
            self._master_password = os.getenv("DEVDOCAI_MASTER_KEY", "")
            if not self._master_password:
                # Generate and save a random key
                self._master_password = secrets.token_hex(32)
                logger.warning("Generated random master key - save DEVDOCAI_MASTER_KEY env var")
        
        # Use provided salt or generate new one
        if salt is None:
            salt = os.urandom(32)
        
        # Configure Argon2id with recommended security parameters
        params = Parameters(
            type=Type.ID,  # Argon2id variant
            version=19,  # Latest Argon2 version
            memory_cost=65536,  # 64 MB memory
            time_cost=3,  # 3 iterations
            parallelism=4,  # 4 parallel threads
            salt_len=32,  # 32-byte salt
            hash_len=32  # 32-byte output for AES-256
        )
        
        # Create hasher with secure parameters
        ph = PasswordHasher.from_parameters(params)
        
        # Derive key using provided salt
        hash_result = ph.hash(self._master_password, salt=salt)
        
        # Extract key material (Argon2 hash includes metadata, extract the hash portion)
        # The hash format is: $argon2id$v=19$m=65536,t=3,p=4$<salt>$<hash>
        hash_parts = hash_result.split('$')
        if len(hash_parts) >= 6:
            # The hash is base64 encoded, decode it
            import base64
            key_material = base64.b64decode(hash_parts[-1] + '==')[:32]
        else:
            # Fallback to SHA256 if parsing fails
            key_material = hashlib.sha256(hash_result.encode()).digest()
        
        return key_material
    
    def _derive_key_legacy(self) -> bytes:
        """
        Legacy key derivation for backward compatibility.
        Uses fixed salt (insecure, only for decrypting old data).
        
        Returns:
            32-byte encryption key
        """
        # Get master password - use same as in _derive_key for consistency
        if not hasattr(self, '_master_password'):
            self._master_password = os.getenv("DEVDOCAI_MASTER_KEY", "")
            if not self._master_password:
                self._master_password = secrets.token_hex(32)
                logger.warning("Generated random master key for legacy decryption")
        
        # Use legacy fixed salt (for backward compatibility only)
        # This is deterministic and matches the original insecure implementation
        salt = hashlib.sha256(b"DevDocAI-M001-Salt").digest()[:16]
        
        # Use PBKDF2-HMAC-SHA256 for legacy compatibility (still insecure due to fixed salt, but better than raw SHA256)
        # WARNING: This method is insecure and only provided for decrypting old data!
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=10000,
            backend=default_backend()
        )
        key_material = kdf.derive(self._master_password.encode())
        
        return key_material
    
    def _validate_encrypted_structure(self, data: Dict) -> bool:
        """
        Validate encrypted data structure to prevent injection attacks.
        
        Args:
            data: Encrypted data dictionary
            
        Returns:
            True if structure is valid, False otherwise
        """
        required_fields = ['ciphertext', 'nonce', 'tag']
        
        # Check required fields
        for field in required_fields:
            if field not in data:
                logger.error(f"Missing required field: {field}")
                return False
            
            # Validate hex format
            try:
                bytes.fromhex(data[field])
            except (ValueError, TypeError):
                logger.error(f"Invalid hex format for field: {field}")
                return False
        
        # Validate optional fields
        if 'salt' in data:
            try:
                bytes.fromhex(data['salt'])
            except (ValueError, TypeError):
                logger.error("Invalid hex format for salt")
                return False
        
        if 'version' in data:
            if not isinstance(data['version'], int) or data['version'] not in [1, 2]:
                logger.error(f"Invalid version: {data.get('version')}")
                return False
        
        # Check for unexpected fields (potential injection)
        allowed_fields = {'ciphertext', 'nonce', 'tag', 'salt', 'version'}
        unexpected = set(data.keys()) - allowed_fields
        if unexpected:
            logger.warning(f"Unexpected fields in encrypted data: {unexpected}")
        
        return True
    
    def _secure_wipe(self) -> None:
        """
        Securely wipe sensitive data from memory.
        """
        if self._cipher_key:
            # Overwrite the key with random data
            self._cipher_key = os.urandom(32)
            self._cipher_key = None
            
            # Force garbage collection
            gc.collect()
    
    @property
    def config(self) -> DevDocAIConfig:
        """Get current configuration object."""
        return self._config
    
    def validate(self) -> bool:
        """
        Validate current configuration.
        
        Returns:
            Validation status
        """
        try:
            # Quick validation check - just verify structure
            return isinstance(self._config, DevDocAIConfig)
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False