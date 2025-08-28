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
from argon2 import PasswordHasher
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
            
        # Get raw config path (from argument or env variable)
        raw_config_path = config_path or os.getenv("DEVDOCAI_CONFIG", ".devdocai.yml")
        config_path_obj = Path(raw_config_path)
        # Normalize and resolve
        resolved_config_path = config_path_obj.resolve()
        # Define safe config root (application config directory in user's home)
        safe_root = (Path.home() / ".devdocai").resolve()
        safe_root.mkdir(parents=True, exist_ok=True)
        try:
            # Ensure config file is inside safe root
            # This will raise ValueError if resolved_config_path is not within safe_root
            _ = resolved_config_path.relative_to(safe_root)
            # Extra check: Avoid symlink pointing outside safe_root
            if resolved_config_path.is_symlink():
                target_path = resolved_config_path.resolve()
                if not str(target_path).startswith(str(safe_root)):
                    raise ValueError("Symlink points outside safe config root.")
            # Extra check: Must be a file or not exist (and not a directory)
            if resolved_config_path.exists() and resolved_config_path.is_dir():
                raise ValueError("Config path is a directory, which is not allowed.")
            self.config_path = resolved_config_path
        except ValueError:
            logger.warning(f"Unsafe config path specified: {resolved_config_path}. Falling back to safe config directory ({safe_root}).")
            self.config_path = safe_root / ".devdocai.yml"
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
        config_path = Path(path) if path else self.config_path
        # Normalize and resolve config path
        resolved_config_path = config_path.resolve()
        # Define safe config root (must match the logic in __init__)
        safe_root = (Path.home() / ".devdocai").resolve()
        try:
            # Ensure config_path is inside safe_root
            _ = resolved_config_path.relative_to(safe_root)
            # Extra check: Avoid symlink pointing outside safe_root
            if resolved_config_path.is_symlink():
                target_path = resolved_config_path.resolve()
                if not str(target_path).startswith(str(safe_root)):
                    raise ValueError("Symlink points outside safe config root.")
            # Extra check: Must be a file or not exist (and not a directory)
            if resolved_config_path.exists() and resolved_config_path.is_dir():
                raise ValueError("Config path is a directory, which is not allowed.")
            config_path_to_use = resolved_config_path
        except ValueError:
            logger.warning(f"Unsafe config path specified: {resolved_config_path}. Falling back to safe config directory ({safe_root}).")
            config_path_to_use = safe_root / ".devdocai.yml"

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
            # Generate or retrieve encryption key
            if not self._cipher_key:
                self._cipher_key = self._derive_key()
            
            encrypted = {}
            for name, key in keys.items():
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
                
                # Store with nonce and tag
                encrypted[name] = {
                    'ciphertext': ciphertext.hex(),
                    'nonce': nonce.hex(),
                    'tag': encryptor.tag.hex()
                }
            
            return encrypted
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
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
            if not self._cipher_key:
                self._cipher_key = self._derive_key()
            
            decrypted = {}
            for name, key_data in encrypted_keys.items():
                # Extract components
                ciphertext = bytes.fromhex(key_data['ciphertext'])
                nonce = bytes.fromhex(key_data['nonce'])
                tag = bytes.fromhex(key_data['tag'])
                
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
            
            return decrypted
            
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def _derive_key(self) -> bytes:
        """
        Derive encryption key using Argon2id.
        
        Returns:
            32-byte encryption key
        """
        # Get or create master password
        master_password = os.getenv("DEVDOCAI_MASTER_KEY", "")
        if not master_password:
            # Generate and save a random key
            master_password = secrets.token_hex(32)
            logger.warning("Generated random master key - save DEVDOCAI_MASTER_KEY env var")
        
        # Use Argon2id for key derivation
        salt = hashlib.sha256(b"DevDocAI-M001-Salt").digest()[:16]
        
        # Derive key
        ph = PasswordHasher()
        hash_result = ph.hash(master_password)
        
        # Extract key material from hash
        key_material = hashlib.sha256(hash_result.encode()).digest()
        
        return key_material
    
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