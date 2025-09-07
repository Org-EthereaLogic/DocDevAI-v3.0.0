"""
M001 Configuration Manager - Pass 1: Core Implementation

This module implements the Configuration Manager for DevDocAI v3.0.0,
providing privacy-first configuration management, memory mode detection,
YAML configuration loading, and secure API key storage.

Design Requirements from SDD 5.1:
- Privacy-first defaults (local_only, no telemetry, no cloud)
- Memory mode detection (baseline/standard/enhanced/performance)
- YAML configuration loading with validation
- Secure API key storage with AES-256-GCM encryption
- GDPR/CCPA compliance with DSR support
"""

import os
import platform
import psutil
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from types import SimpleNamespace
from enum import Enum
import yaml
import json
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, HashingError
import secrets
import base64
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from datetime import datetime, timezone


class MemoryMode(str, Enum):
    """Memory operation modes based on available RAM."""
    BASELINE = "baseline"      # <2GB RAM
    STANDARD = "standard"      # 2-4GB RAM
    ENHANCED = "enhanced"      # 4-8GB RAM
    PERFORMANCE = "performance"  # >8GB RAM


class PrivacyMode(str, Enum):
    """Privacy operation modes."""
    LOCAL_ONLY = "local_only"   # No external connections (default)
    SELECTIVE = "selective"     # User-approved external services
    STANDARD = "standard"       # Standard privacy protections


class ConfigurationError(Exception):
    """Configuration-related errors."""
    pass


class ConfigurationSchema(BaseModel):
    """Pydantic schema for configuration validation."""
    
    model_config = ConfigDict(
        validate_assignment=True,
        extra='forbid',
        str_strip_whitespace=True
    )
    
    # Privacy-first defaults (SDD 5.1 requirement)
    privacy_mode: PrivacyMode = Field(
        default=PrivacyMode.LOCAL_ONLY,
        description="Privacy operation mode"
    )
    
    telemetry_enabled: bool = Field(
        default=False,
        description="Telemetry collection (opt-in only)"
    )
    
    cloud_features: bool = Field(
        default=False,
        description="Cloud-based features (opt-in only)"
    )
    
    dsr_enabled: bool = Field(
        default=True,
        description="Data Subject Rights (GDPR/CCPA) support"
    )
    
    # Memory and performance settings
    memory_mode: MemoryMode = Field(
        default=MemoryMode.STANDARD,
        description="Memory operation mode (auto-detected)"
    )
    
    # Operation mode for modules (added for M004 generator)
    operation_mode: str = Field(
        default="basic",
        description="Operation mode for unified modules (basic, performance, secure, enterprise)"
    )
    
    # Quality gate threshold for document generation (added for M004)
    quality_gate_threshold: float = Field(
        default=85.0,
        ge=0.0,
        le=100.0,
        description="Minimum quality score threshold for documents"
    )
    
    # Maximum document size in MB (added for M004)
    max_document_size_mb: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum document size in megabytes"
    )
    
    max_concurrent_operations: int = Field(
        default=4,
        ge=1,
        le=32,
        description="Maximum concurrent operations"
    )
    
    cache_size_mb: int = Field(
        default=128,
        ge=16,
        le=2048,
        description="Cache size in megabytes"
    )
    
    # API Configuration
    api_keys: Dict[str, str] = Field(
        default_factory=dict,
        description="Encrypted API keys for external services"
    )
    
    api_rate_limits: Dict[str, int] = Field(
        default_factory=lambda: {
            "openai": 50,
            "anthropic": 50,
            "google": 50
        },
        description="API rate limits (requests per minute)"
    )
    
    # File and directory settings
    config_dir: Path = Field(
        default_factory=lambda: Path.home() / ".devdocai",
        description="Configuration directory"
    )
    
    cache_dir: Path = Field(
        default_factory=lambda: Path.home() / ".devdocai" / "cache",
        description="Cache directory"
    )
    
    log_level: str = Field(
        default="INFO",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
        description="Logging level"
    )
    
    # Security settings
    encryption_enabled: bool = Field(
        default=True,
        description="Enable encryption for sensitive data"
    )
    
    key_rotation_days: int = Field(
        default=90,
        ge=1,
        le=365,
        description="API key rotation period in days"
    )
    
    # Development settings
    debug_mode: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    
    @field_validator('config_dir', 'cache_dir', mode='before')
    @classmethod
    def validate_paths(cls, v):
        """Convert string paths to Path objects."""
        if isinstance(v, str):
            return Path(v)
        return v
    
    @model_validator(mode='after')
    def validate_cloud_privacy_consistency(self):
        """Ensure cloud features respect privacy mode."""
        if self.privacy_mode == PrivacyMode.LOCAL_ONLY and self.cloud_features:
            raise ValueError(
                "Cloud features cannot be enabled in local_only privacy mode"
            )
        return self


class ConfigurationManager:
    """
    M001 Configuration Manager - Core Implementation
    
    Provides centralized configuration management with:
    - Privacy-first defaults
    - Memory mode auto-detection
    - Secure API key storage
    - YAML configuration loading
    - GDPR/CCPA compliance
    """
    
    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize Configuration Manager.
        
        Args:
            config_file: Optional path to configuration file
        """
        self._config_file = config_file or Path.cwd() / ".devdocai.yml"
        self._schema = ConfigurationSchema()
        self._encrypted_store: Dict[str, str] = {}
        self._ph = PasswordHasher(
            time_cost=3,
            memory_cost=65536,
            parallelism=1,
            hash_len=32,
            salt_len=16
        )
        
        # Auto-detect memory mode
        self._detect_memory_mode()
        
        # Load configuration if file exists
        if self._config_file.exists():
            self.load_configuration()
        else:
            self._ensure_directories()
        
        # Load encrypted API keys
        self._load_encrypted_keys()
    
    def _detect_memory_mode(self) -> None:
        """
        Detect and set appropriate memory mode based on available RAM.
        
        Memory modes (SDD 5.1 requirement):
        - <2GB: baseline
        - 2-4GB: standard  
        - 4-8GB: enhanced
        - >8GB: performance
        """
        try:
            # Get total system memory in bytes
            total_memory = psutil.virtual_memory().total
            total_gb = total_memory / (1024**3)
            
            if total_gb < 2:
                mode = MemoryMode.BASELINE
                cache_size = 32
                max_ops = 2
            elif total_gb < 4:
                mode = MemoryMode.STANDARD
                cache_size = 64
                max_ops = 4
            elif total_gb < 8:
                mode = MemoryMode.ENHANCED
                cache_size = 128
                max_ops = 8
            else:
                mode = MemoryMode.PERFORMANCE
                cache_size = 256
                max_ops = 16
            
            # Update schema with detected values
            self._schema.memory_mode = mode
            self._schema.cache_size_mb = cache_size
            self._schema.max_concurrent_operations = max_ops
            
        except Exception as e:
            # Fallback to standard mode if detection fails
            self._schema.memory_mode = MemoryMode.STANDARD
            print(f"Warning: Memory detection failed, using standard mode: {e}")
    
    def _ensure_directories(self) -> None:
        """Ensure configuration and cache directories exist."""
        self._schema.config_dir.mkdir(parents=True, exist_ok=True)
        self._schema.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def load_configuration(self) -> None:
        """
        Load configuration from YAML file with validation.
        
        Raises:
            ConfigurationError: If configuration file is invalid
        """
        try:
            if not self._config_file.exists():
                return
            
            with open(self._config_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f) or {}
            
            # Validate and update schema
            if config_data:
                # Handle path conversion for directories
                if 'config_dir' in config_data:
                    config_data['config_dir'] = Path(config_data['config_dir'])
                if 'cache_dir' in config_data:
                    config_data['cache_dir'] = Path(config_data['cache_dir'])
                
                # Create new schema instance with all data to avoid dependency order issues
                try:
                    # Get current schema data and update with loaded data
                    current_data = self._schema.model_dump()
                    current_data.update(config_data)
                    
                    # Create new validated schema instance
                    self._schema = ConfigurationSchema(**current_data)
                except Exception:
                    # Fall back to field-by-field update if bulk update fails
                    # Set privacy_mode first to handle dependencies correctly
                    if 'privacy_mode' in config_data:
                        self._schema.privacy_mode = PrivacyMode(config_data['privacy_mode'])
                    
                    # Then update other fields
                    for key, value in config_data.items():
                        if key != 'privacy_mode' and hasattr(self._schema, key):
                            setattr(self._schema, key, value)
            
            self._ensure_directories()
            
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML configuration: {e}")
        except Exception as e:
            raise ConfigurationError(f"Configuration loading failed: {e}")
    
    def save_configuration(self) -> None:
        """Save current configuration to YAML file."""
        try:
            # Convert schema to dict, handling Path objects
            config_dict = self._schema.model_dump()
            
            # Convert Path objects and enums to strings for YAML serialization
            for key, value in config_dict.items():
                if isinstance(value, Path):
                    config_dict[key] = str(value)
                elif hasattr(value, 'value'):  # Handle enum values
                    config_dict[key] = value.value if hasattr(value, 'value') else str(value)
            
            # Remove API keys from saved config (stored encrypted separately)
            config_dict.pop('api_keys', None)
            
            with open(self._config_file, 'w', encoding='utf-8') as f:
                yaml.dump(
                    config_dict,
                    f,
                    default_flow_style=False,
                    sort_keys=True,
                    indent=2
                )
            
            # Save encrypted API keys to separate file
            self._save_encrypted_keys()
                
        except Exception as e:
            raise ConfigurationError(f"Configuration saving failed: {e}")
    
    def _save_encrypted_keys(self) -> None:
        """Save encrypted API keys to secure storage file."""
        if not self._encrypted_store:
            return
            
        try:
            keys_file = self._schema.config_dir / ".api_keys.enc"
            with open(keys_file, 'w', encoding='utf-8') as f:
                json.dump(self._encrypted_store, f)
            
            # Set restrictive permissions (owner read/write only)
            keys_file.chmod(0o600)
            
        except Exception as e:
            # Log error but don't fail the whole save operation
            print(f"Warning: Could not save encrypted keys: {e}")
    
    def _load_encrypted_keys(self) -> None:
        """Load encrypted API keys from secure storage file."""
        try:
            keys_file = self._schema.config_dir / ".api_keys.enc"
            if keys_file.exists():
                with open(keys_file, 'r', encoding='utf-8') as f:
                    self._encrypted_store = json.load(f)
        except Exception as e:
            # Log error but don't fail initialization
            print(f"Warning: Could not load encrypted keys: {e}")
            self._encrypted_store = {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        return getattr(self._schema, key, default)

    def get_config(self) -> Any:
        """
        Compatibility view for integration with M002.

        Provides a simple, read-only namespaced object so callers can access:
        - config.performance.memory_mode -> str (e.g., 'enhanced')
        - config.telemetry.enabled -> bool
        - config.security.encryption_enabled -> bool

        This aligns with SDD 5.1 (M001 Configuration Manager) where
        performance, telemetry, and security settings must be consumable by
        other modules.
        """
        # Ensure memory_mode is exposed as a lowercase string for simple equality checks
        memory_mode = (
            self._schema.memory_mode.value
            if hasattr(self._schema.memory_mode, 'value') else str(self._schema.memory_mode)
        )
        memory_mode = memory_mode.lower()

        return SimpleNamespace(
            performance=SimpleNamespace(memory_mode=memory_mode),
            telemetry=SimpleNamespace(enabled=self._schema.telemetry_enabled),
            security=SimpleNamespace(encryption_enabled=self._schema.encryption_enabled)
        )
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value with validation.
        
        Args:
            key: Configuration key
            value: Configuration value
            
        Raises:
            ConfigurationError: If validation fails
        """
        try:
            if hasattr(self._schema, key):
                setattr(self._schema, key, value)
            else:
                raise ConfigurationError(f"Unknown configuration key: {key}")
        except Exception as e:
            raise ConfigurationError(f"Configuration validation failed: {e}")
    
    def _generate_key(self, password: str, salt: bytes) -> bytes:
        """Generate encryption key using PBKDF2 (simplified for reliability)."""
        try:
            # Use PBKDF2 for key derivation (reliable and well-tested)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            
            return kdf.derive(password.encode())
            
        except Exception as e:
            raise ConfigurationError(f"Key generation failed: {e}")
    
    def encrypt_api_key(self, service: str, api_key: str) -> None:
        """
        Encrypt and store API key for a service.
        
        Args:
            service: Service name (e.g., 'openai', 'anthropic')
            api_key: API key to encrypt
            
        Raises:
            ConfigurationError: If encryption fails
        """
        try:
            # Validate input
            if not service or not api_key:
                raise ValueError("Service name and API key cannot be empty")
                
            if not self._schema.encryption_enabled:
                # Store plaintext if encryption disabled (development only)
                self._schema.api_keys[service] = api_key
                return
            
            # Generate random salt and nonce
            salt = secrets.token_bytes(16)
            nonce = secrets.token_bytes(12)
            
            # Derive encryption key
            key = self._generate_key(f"devdocai_{service}", salt)
            
            # Encrypt using AES-256-GCM
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(nonce),
                backend=default_backend()
            )
            
            encryptor = cipher.encryptor()
            ciphertext = encryptor.update(api_key.encode()) + encryptor.finalize()
            
            # Combine salt + nonce + tag + ciphertext for storage
            encrypted_data = salt + nonce + encryptor.tag + ciphertext
            encoded_data = base64.b64encode(encrypted_data).decode('ascii')
            
            # Store encrypted key
            self._encrypted_store[service] = encoded_data
            
        except Exception as e:
            raise ConfigurationError(f"API key encryption failed: {e}")
    
    def decrypt_api_key(self, service: str) -> Optional[str]:
        """
        Decrypt and retrieve API key for a service.
        
        Args:
            service: Service name
            
        Returns:
            Decrypted API key or None if not found
            
        Raises:
            ConfigurationError: If decryption fails
        """
        try:
            if not self._schema.encryption_enabled:
                # Return plaintext if encryption disabled
                return self._schema.api_keys.get(service)
            
            if service not in self._encrypted_store:
                return None
            
            # Decode stored data
            encrypted_data = base64.b64decode(
                self._encrypted_store[service].encode('ascii')
            )
            
            # Extract components
            salt = encrypted_data[:16]
            nonce = encrypted_data[16:28]
            tag = encrypted_data[28:44]
            ciphertext = encrypted_data[44:]
            
            # Derive decryption key
            key = self._generate_key(f"devdocai_{service}", salt)
            
            # Decrypt using AES-256-GCM
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(nonce, tag),
                backend=default_backend()
            )
            
            decryptor = cipher.decryptor()
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            return plaintext.decode()
            
        except Exception as e:
            raise ConfigurationError(f"API key decryption failed: {e}")
    
    def remove_api_key(self, service: str) -> bool:
        """
        Remove API key for a service.
        
        Args:
            service: Service name
            
        Returns:
            True if key was removed, False if not found
        """
        removed = False
        
        if service in self._encrypted_store:
            del self._encrypted_store[service]
            removed = True
        
        if service in self._schema.api_keys:
            del self._schema.api_keys[service]
            removed = True
        
        return removed
    
    def list_api_services(self) -> List[str]:
        """
        List services with stored API keys.
        
        Returns:
            List of service names
        """
        services = set()
        services.update(self._encrypted_store.keys())
        services.update(self._schema.api_keys.keys())
        return sorted(list(services))
    
    def get_memory_info(self) -> Dict[str, Any]:
        """
        Get current memory information and mode.
        
        Returns:
            Dictionary with memory information
        """
        try:
            memory = psutil.virtual_memory()
            return {
                'mode': self._schema.memory_mode.value,
                'total_gb': round(memory.total / (1024**3), 2),
                'available_gb': round(memory.available / (1024**3), 2),
                'used_percent': memory.percent,
                'cache_size_mb': self._schema.cache_size_mb,
                'max_concurrent_operations': self._schema.max_concurrent_operations
            }
        except Exception:
            return {
                'mode': self._schema.memory_mode.value,
                'error': 'Unable to retrieve memory information'
            }
    
    def get_privacy_status(self) -> Dict[str, Any]:
        """
        Get current privacy settings status.
        
        Returns:
            Dictionary with privacy information
        """
        return {
            'privacy_mode': self._schema.privacy_mode.value,
            'telemetry_enabled': self._schema.telemetry_enabled,
            'cloud_features': self._schema.cloud_features,
            'dsr_enabled': self._schema.dsr_enabled,
            'encryption_enabled': self._schema.encryption_enabled,
            'api_services_count': len(self.list_api_services())
        }
    
    def validate_configuration(self) -> List[str]:
        """
        Validate current configuration and return any issues.
        
        Returns:
            List of validation issues (empty if valid)
        """
        issues = []
        
        try:
            # Test schema validation
            self._schema.model_dump()
        except Exception as e:
            issues.append(f"Schema validation failed: {e}")
        
        # Check directory permissions
        try:
            if not self._schema.config_dir.exists():
                self._schema.config_dir.mkdir(parents=True, exist_ok=True)
            
            # Test write permission
            test_file = self._schema.config_dir / ".test"
            test_file.write_text("test")
            test_file.unlink()
            
        except Exception as e:
            issues.append(f"Config directory not writable: {e}")
        
        # Validate privacy mode consistency
        if (self._schema.privacy_mode == PrivacyMode.LOCAL_ONLY and 
            self._schema.cloud_features):
            issues.append(
                "Cloud features enabled in local_only privacy mode"
            )
        
        return issues
    
    def reset_to_defaults(self) -> None:
        """Reset configuration to privacy-first defaults."""
        self._schema = ConfigurationSchema()
        self._encrypted_store.clear()
        self._detect_memory_mode()
    
    def export_configuration(self, include_api_keys: bool = False) -> Dict[str, Any]:
        """
        Export configuration for backup or migration.
        
        Args:
            include_api_keys: Whether to include encrypted API keys
            
        Returns:
            Configuration dictionary
        """
        config = self._schema.model_dump()
        
        # Convert Path objects and enums to strings
        for key, value in config.items():
            if isinstance(value, Path):
                config[key] = str(value)
            elif hasattr(value, 'value'):  # Handle enum values
                config[key] = value.value if hasattr(value, 'value') else str(value)
        
        # Add metadata
        config['_metadata'] = {
            'version': '3.0.0',
            'exported_at': datetime.now(timezone.utc).isoformat(),
            'platform': platform.system(),
            'python_version': platform.python_version()
        }
        
        # Optionally include encrypted API keys
        if include_api_keys:
            config['_encrypted_api_keys'] = self._encrypted_store.copy()
        
        return config
    
    def __repr__(self) -> str:
        """String representation of configuration manager."""
        return (
            f"ConfigurationManager("
            f"memory_mode={self._schema.memory_mode.value}, "
            f"privacy_mode={self._schema.privacy_mode.value}, "
            f"api_services={len(self.list_api_services())})"
        )
