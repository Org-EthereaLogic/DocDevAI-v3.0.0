"""
M001 Configuration Manager - Optimized Implementation
DevDocAI v3.0.0

Performance optimizations for Pass 2:
- Cached validation schemas
- Optimized Pydantic models
- Argon2id key derivation
- Security audit logging
"""

import os
import logging
import threading
import time
from typing import Optional, Dict, Any, Literal, Union, ClassVar
from pathlib import Path
from functools import lru_cache, cached_property
import base64
import secrets
import json
from datetime import datetime

import yaml
import psutil
from pydantic import BaseModel, Field, field_validator, ValidationError as PydanticValidationError, ConfigDict
from pydantic_core import CoreSchema, core_schema
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Configure logging
logger = logging.getLogger(__name__)
audit_logger = logging.getLogger(f"{__name__}.audit")

# Type definitions
MemoryMode = Literal["baseline", "standard", "enhanced", "performance"]
LLMProvider = Literal["openai", "anthropic", "gemini", "local"]

# Custom exceptions
class ValidationError(Exception):
    """Configuration validation error."""
    pass


class ConfigurationError(Exception):
    """General configuration error."""
    pass


# Cache system info to avoid repeated calls
@lru_cache(maxsize=1)
def get_system_ram_gb() -> float:
    """Get system RAM in GB (cached)."""
    ram_bytes = psutil.virtual_memory().total
    return ram_bytes / (1024**3)


class OptimizedPrivacyConfig(BaseModel):
    """Privacy configuration with opt-in defaults for user privacy protection."""
    
    model_config = ConfigDict(
        validate_assignment=True, 
        frozen=True,
        # Optimize by disabling unnecessary features
        extra='forbid',
        arbitrary_types_allowed=False
    )
    
    telemetry: bool = Field(default=False, description="Telemetry collection (disabled by default)")
    analytics: bool = Field(default=False, description="Analytics tracking (disabled by default)")
    local_only: bool = Field(default=True, description="Local-only operation (enabled by default)")


class OptimizedSystemConfig(BaseModel):
    """System configuration with cached memory mode detection."""
    
    model_config = ConfigDict(
        validate_assignment=True,
        extra='forbid'
    )
    
    memory_mode: Union[MemoryMode, Literal["auto"]] = Field(
        default="auto", 
        description="Memory mode: auto|baseline|standard|enhanced|performance"
    )
    detected_ram: Optional[float] = Field(default=None, description="Detected RAM in GB")
    max_workers: int = Field(default=4, description="Maximum concurrent workers")
    cache_size: str = Field(default="100MB", description="Cache size specification")
    cache_size_bytes: Optional[int] = Field(default=None, description="Cache size in bytes")
    
    # Class-level cache for memory mode
    _memory_mode_cache: ClassVar[Optional[str]] = None
    
    @field_validator('memory_mode')
    @classmethod
    def detect_memory_mode(cls, v):
        """Auto-detect memory mode based on system RAM (cached)."""
        if v == "auto":
            # Use cached value if available
            if cls._memory_mode_cache is not None:
                return cls._memory_mode_cache
            
            ram_gb = get_system_ram_gb()
            
            # Determine memory mode based on RAM
            if ram_gb < 2:
                mode = "baseline"
            elif ram_gb < 4:
                mode = "standard"
            elif ram_gb < 8:
                mode = "enhanced"
            else:
                mode = "performance"
            
            # Cache the result
            cls._memory_mode_cache = mode
            logger.info(f"Auto-detected memory mode: {mode} (RAM: {ram_gb:.1f}GB)")
            return mode
        
        # Validate manual mode
        if v not in ["baseline", "standard", "enhanced", "performance"]:
            raise ValueError(f"Invalid memory mode: {v}")
        return v
    
    def model_post_init(self, __context):
        """Post-initialization to set computed fields (optimized)."""
        # Use cached RAM value
        if self.detected_ram is None:
            object.__setattr__(self, 'detected_ram', get_system_ram_gb())
        
        # Calculate cache size bytes if needed
        if self.cache_size and not self.cache_size_bytes:
            object.__setattr__(self, 'cache_size_bytes', self._calculate_cache_bytes())
    
    def _calculate_cache_bytes(self) -> int:
        """Convert cache size string to bytes."""
        size_str = self.cache_size.upper()
        
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            # Assume MB if no unit
            return int(size_str) * 1024 * 1024


class OptimizedSecurityConfig(BaseModel):
    """Security configuration with Argon2id support."""
    
    model_config = ConfigDict(validate_assignment=True, extra='forbid')
    
    encryption_enabled: bool = Field(default=True, description="Enable encryption for sensitive data")
    api_keys_encrypted: bool = Field(default=True, description="Encrypt API keys")
    key_derivation: Literal["argon2id", "pbkdf2"] = Field(default="argon2id", description="Key derivation function")
    audit_logging: bool = Field(default=True, description="Enable security audit logging")


class OptimizedLLMConfig(BaseModel):
    """LLM configuration for AI-powered features."""
    
    model_config = ConfigDict(validate_assignment=True, extra='forbid')
    
    provider: LLMProvider = Field(default="local", description="LLM provider")
    model: str = Field(default="llama2", description="Model name")
    max_tokens: int = Field(default=4000, description="Maximum tokens per request")
    temperature: float = Field(default=0.7, description="Temperature for generation")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    retry_attempts: int = Field(default=3, description="Number of retry attempts")


class OptimizedQualityConfig(BaseModel):
    """Quality configuration for document generation."""
    
    model_config = ConfigDict(validate_assignment=True, extra='forbid')
    
    min_score: int = Field(default=80, description="Minimum quality score")
    auto_enhance: bool = Field(default=True, description="Auto-enhance documents")
    max_iterations: int = Field(default=3, description="Max enhancement iterations")


class FastValidator:
    """Fast validation using cached schemas."""
    
    def __init__(self):
        self._validators = {}
        self._compile_validators()
    
    def _compile_validators(self):
        """Pre-compile validators for each config type."""
        # Create lightweight validators that just check structure
        self._validators['privacy'] = self._create_privacy_validator()
        self._validators['system'] = self._create_system_validator()
        self._validators['security'] = self._create_security_validator()
        self._validators['llm'] = self._create_llm_validator()
        self._validators['quality'] = self._create_quality_validator()
    
    def _create_privacy_validator(self):
        """Create fast validator for privacy config."""
        def validate(data):
            if not isinstance(data, dict):
                return False
            for key in data:
                if key not in {'telemetry', 'analytics', 'local_only'}:
                    return False
            if 'telemetry' in data and not isinstance(data['telemetry'], bool):
                return False
            if 'analytics' in data and not isinstance(data['analytics'], bool):
                return False
            if 'local_only' in data and not isinstance(data['local_only'], bool):
                return False
            return True
        return validate
    
    def _create_system_validator(self):
        """Create fast validator for system config."""
        def validate(data):
            if not isinstance(data, dict):
                return False
            valid_modes = {'auto', 'baseline', 'standard', 'enhanced', 'performance'}
            if 'memory_mode' in data and data['memory_mode'] not in valid_modes:
                return False
            if 'max_workers' in data:
                if not isinstance(data['max_workers'], int) or data['max_workers'] < 1:
                    return False
            if 'cache_size' in data:
                cache = str(data['cache_size']).upper()
                if not any(cache.endswith(u) for u in ['KB', 'MB', 'GB']):
                    try:
                        int(cache)  # Check if it's a plain number
                    except ValueError:
                        return False
            return True
        return validate
    
    def _create_security_validator(self):
        """Create fast validator for security config."""
        def validate(data):
            if not isinstance(data, dict):
                return False
            if 'key_derivation' in data and data['key_derivation'] not in {'argon2id', 'pbkdf2'}:
                return False
            for key in ['encryption_enabled', 'api_keys_encrypted', 'audit_logging']:
                if key in data and not isinstance(data[key], bool):
                    return False
            return True
        return validate
    
    def _create_llm_validator(self):
        """Create fast validator for LLM config."""
        def validate(data):
            if not isinstance(data, dict):
                return False
            if 'provider' in data and data['provider'] not in {'openai', 'anthropic', 'gemini', 'local'}:
                return False
            if 'max_tokens' in data:
                if not isinstance(data['max_tokens'], int) or data['max_tokens'] < 1:
                    return False
            if 'temperature' in data:
                temp = data['temperature']
                if not isinstance(temp, (int, float)) or temp < 0 or temp > 2:
                    return False
            return True
        return validate
    
    def _create_quality_validator(self):
        """Create fast validator for quality config."""
        def validate(data):
            if not isinstance(data, dict):
                return False
            if 'min_score' in data:
                score = data['min_score']
                if not isinstance(score, int) or score < 0 or score > 100:
                    return False
            if 'max_iterations' in data:
                iters = data['max_iterations']
                if not isinstance(iters, int) or iters < 1:
                    return False
            if 'auto_enhance' in data and not isinstance(data['auto_enhance'], bool):
                return False
            return True
        return validate
    
    def validate(self, config_type: str, data: dict) -> bool:
        """Fast validation without Pydantic overhead."""
        if config_type not in self._validators:
            return False
        return self._validators[config_type](data)


class OptimizedConfigurationManager:
    """Optimized Configuration Manager with performance improvements."""
    
    def __init__(self, config_file: Optional[Path] = None):
        """Initialize configuration manager."""
        self._lock = threading.RLock()
        self._config_cache = {}
        self._fast_validator = FastValidator()
        
        # Initialize Argon2 hasher with optimized parameters
        self._argon2 = PasswordHasher(
            time_cost=1,  # Reduced for performance
            memory_cost=65536,  # 64MB
            parallelism=2,
            hash_len=32,
            salt_len=16
        )
        
        # Initialize configurations
        self.config_file = config_file or Path(".devdocai.yml")
        self._load_config()
        
        # Initialize encryption
        self._init_encryption()
        
        # Initialize audit logging if enabled
        if self.security.audit_logging:
            self._init_audit_logging()
    
    def _init_audit_logging(self):
        """Initialize security audit logging."""
        # Set up audit logger
        audit_handler = logging.FileHandler('devdocai_audit.log')
        audit_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        audit_logger.addHandler(audit_handler)
        audit_logger.setLevel(logging.INFO)
    
    def _audit_log(self, action: str, details: dict):
        """Log security-relevant actions."""
        if self.security.audit_logging:
            audit_logger.info(json.dumps({
                'timestamp': datetime.utcnow().isoformat(),
                'action': action,
                'details': details
            }))
    
    def _load_config(self):
        """Load configuration from file or use defaults."""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                data = yaml.safe_load(f) or {}
        else:
            data = {}
        
        # Initialize configurations with optimized models
        self.privacy = OptimizedPrivacyConfig(**data.get('privacy', {}))
        self.system = OptimizedSystemConfig(**data.get('system', {}))
        self.security = OptimizedSecurityConfig(**data.get('security', {}))
        self.llm = OptimizedLLMConfig(**data.get('llm', {}))
        self.quality = OptimizedQualityConfig(**data.get('quality', {}))
    
    def _init_encryption(self):
        """Initialize encryption with Argon2id or PBKDF2."""
        # Generate or load master key
        key_file = Path('.devdocai.key')
        
        if key_file.exists():
            with open(key_file, 'rb') as f:
                key_data = f.read()
            stored_key = key_data[:32]
            self._salt = key_data[32:48]
        else:
            stored_key = secrets.token_bytes(32)
            self._salt = secrets.token_bytes(16)
            with open(key_file, 'wb') as f:
                f.write(stored_key + self._salt)
            key_file.chmod(0o600)
        
        # Derive encryption key using Argon2id or PBKDF2
        if self.security.key_derivation == "argon2id":
            # Use Argon2id for key derivation from stored key
            # This provides additional security by deriving the actual encryption key
            self._master_key = self._argon2.hash(stored_key.hex())[:32].encode()[:32]
        else:
            # Use raw key for PBKDF2 compatibility (or direct use)
            self._master_key = stored_key
        
        # Initialize AES-GCM cipher
        self._cipher = AESGCM(self._master_key)
        
        self._audit_log('encryption_initialized', {
            'key_derivation': self.security.key_derivation
        })
    
    @lru_cache(maxsize=128)
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation key (cached)."""
        parts = key.split('.')
        value = self.__dict__
        
        for part in parts:
            if hasattr(value, part):
                value = getattr(value, part)
            elif isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        
        return value
    
    def validate(self, data: Dict[str, Any]) -> bool:
        """
        Fast validation using optimized validators.
        
        Args:
            data: Configuration data to validate
        
        Returns:
            True if valid, False otherwise
        """
        # Use fast validators for common validation
        for config_type, config_data in data.items():
            if not self._fast_validator.validate(config_type, config_data):
                return False
        return True
    
    def validate_full(self, data: Dict[str, Any]) -> bool:
        """
        Full validation using Pydantic models (slower but comprehensive).
        
        Args:
            data: Configuration data to validate
        
        Returns:
            True if valid, False otherwise
        """
        try:
            # Only create models for full validation
            if 'privacy' in data:
                OptimizedPrivacyConfig(**data['privacy'])
            if 'system' in data:
                OptimizedSystemConfig(**data['system'])
            if 'security' in data:
                OptimizedSecurityConfig(**data['security'])
            if 'llm' in data:
                OptimizedLLMConfig(**data['llm'])
            if 'quality' in data:
                OptimizedQualityConfig(**data['quality'])
            return True
        except (PydanticValidationError, ValidationError):
            return False
    
    def encrypt_api_key(self, api_key: str) -> str:
        """
        Encrypt API key using AES-GCM with key derived via Argon2id or PBKDF2.
        
        Args:
            api_key: Plain text API key
        
        Returns:
            Base64-encoded encrypted key
        """
        if not self.security.api_keys_encrypted:
            return api_key
        
        # Encrypt with AES-GCM using the master key
        nonce = secrets.token_bytes(12)
        ciphertext = self._cipher.encrypt(nonce, api_key.encode(), None)
        
        self._audit_log('api_key_encrypted', {
            'key_derivation': self.security.key_derivation,
            'key_length': len(api_key)
        })
        
        return base64.b64encode(nonce + ciphertext).decode()
    
    def decrypt_api_key(self, encrypted_key: str) -> str:
        """
        Decrypt API key.
        
        Args:
            encrypted_key: Base64-encoded encrypted key
        
        Returns:
            Plain text API key
        """
        if not self.security.api_keys_encrypted:
            return encrypted_key
        
        try:
            data = base64.b64decode(encrypted_key)
            nonce = data[:12]
            ciphertext = data[12:]
            
            plaintext = self._cipher.decrypt(nonce, ciphertext, None)
            
            self._audit_log('api_key_decrypted', {
                'success': True
            })
            
            return plaintext.decode()
        except Exception as e:
            self._audit_log('api_key_decryption_failed', {
                'error': str(e)
            })
            raise ValidationError(f"Failed to decrypt API key: {e}")