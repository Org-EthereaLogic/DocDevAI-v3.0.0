"""
M002 Local Storage System - Unified Configuration

Configuration management for the unified storage manager,
supporting mode-based feature activation and seamless integration
with M001 ConfigurationManager.
"""

from enum import Enum
from typing import Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field, validator

from devdocai.core.config import ConfigurationManager, MemoryMode


class StorageMode(Enum):
    """Storage operation modes with progressive feature sets."""
    BASIC = "basic"          # Core functionality only (minimal overhead)
    PERFORMANCE = "performance"  # Optimized with caching, batching, FTS5
    SECURE = "secure"        # Security hardened with PII, RBAC, audit
    ENTERPRISE = "enterprise"    # Full features for production


class StorageConfig(BaseModel):
    """
    Unified storage configuration model.
    
    Provides centralized configuration for all storage modes,
    with automatic feature activation based on selected mode.
    """
    
    # Core configuration
    mode: StorageMode = Field(default=StorageMode.BASIC, description="Storage operation mode")
    db_path: Optional[Path] = Field(default=None, description="Database file path")
    memory_mode: MemoryMode = Field(default=MemoryMode.STANDARD, description="Memory usage mode")
    
    # Performance features (PERFORMANCE, ENTERPRISE modes)
    enable_caching: bool = Field(default=False, description="Enable LRU caching")
    cache_size: int = Field(default=500, ge=10, le=10000, description="Cache size (items)")
    cache_ttl: int = Field(default=600, ge=60, le=3600, description="Cache TTL (seconds)")
    enable_batching: bool = Field(default=False, description="Enable batch operations")
    batch_size: int = Field(default=50, ge=1, le=1000, description="Batch operation size")
    enable_fts5: bool = Field(default=False, description="Enable FTS5 full-text search")
    enable_streaming: bool = Field(default=False, description="Enable document streaming")
    
    # Security features (SECURE, ENTERPRISE modes)
    enable_pii_detection: bool = Field(default=False, description="Enable PII detection")
    enable_audit_logging: bool = Field(default=False, description="Enable audit logging")
    audit_flush_interval: int = Field(default=10, ge=1, le=60, description="Audit flush interval (seconds)")
    enable_rbac: bool = Field(default=False, description="Enable role-based access control")
    enable_secure_deletion: bool = Field(default=False, description="Enable DoD 5220.22-M secure deletion")
    enable_sqlcipher: bool = Field(default=False, description="Enable SQLCipher encryption")
    enable_rate_limiting: bool = Field(default=False, description="Enable rate limiting")
    rate_limit_window: int = Field(default=60, ge=10, le=300, description="Rate limit window (seconds)")
    rate_limit_max_requests: int = Field(default=1000, ge=10, le=10000, description="Max requests in window")
    
    # Encryption (all modes)
    enable_encryption: bool = Field(default=True, description="Enable field-level encryption")
    encryption_algorithm: str = Field(default="AES-256-GCM", description="Encryption algorithm")
    
    # Connection pooling
    max_connections: int = Field(default=4, ge=1, le=100, description="Max database connections")
    pool_timeout: int = Field(default=30, ge=5, le=300, description="Connection pool timeout")
    
    @validator('mode', pre=True)
    def validate_mode(cls, v):
        """Validate and convert storage mode."""
        if isinstance(v, str):
            return StorageMode(v.lower())
        return v
    
    @validator('db_path', pre=True)
    def validate_db_path(cls, v):
        """Validate database path."""
        if v is not None and not isinstance(v, Path):
            return Path(v)
        return v
    
    def apply_mode_defaults(self) -> None:
        """Apply default feature settings based on storage mode."""
        mode_defaults = {
            StorageMode.BASIC: {
                'enable_caching': False,
                'enable_batching': False,
                'enable_fts5': False,
                'enable_streaming': False,
                'enable_pii_detection': False,
                'enable_audit_logging': False,
                'enable_rbac': False,
                'enable_secure_deletion': False,
                'enable_sqlcipher': False,
                'enable_rate_limiting': False
            },
            StorageMode.PERFORMANCE: {
                'enable_caching': True,
                'enable_batching': True,
                'enable_fts5': True,
                'enable_streaming': True,
                'enable_pii_detection': False,
                'enable_audit_logging': False,
                'enable_rbac': False,
                'enable_secure_deletion': False,
                'enable_sqlcipher': False,
                'enable_rate_limiting': False
            },
            StorageMode.SECURE: {
                'enable_caching': False,
                'enable_batching': False,
                'enable_fts5': False,
                'enable_streaming': False,
                'enable_pii_detection': True,
                'enable_audit_logging': True,
                'enable_rbac': True,
                'enable_secure_deletion': True,
                'enable_sqlcipher': True,
                'enable_rate_limiting': True
            },
            StorageMode.ENTERPRISE: {
                'enable_caching': True,
                'enable_batching': True,
                'enable_fts5': True,
                'enable_streaming': True,
                'enable_pii_detection': True,
                'enable_audit_logging': True,
                'enable_rbac': True,
                'enable_secure_deletion': True,
                'enable_sqlcipher': True,
                'enable_rate_limiting': True
            }
        }
        
        # Apply defaults for the selected mode
        defaults = mode_defaults[self.mode]
        for key, value in defaults.items():
            setattr(self, key, value)
    
    def get_memory_config(self) -> Dict[str, int]:
        """Get memory configuration based on memory mode."""
        memory_configs = {
            MemoryMode.BASELINE: {
                'cache_size': 100,
                'batch_size': 10,
                'max_connections': 2
            },
            MemoryMode.STANDARD: {
                'cache_size': 500,
                'batch_size': 50,
                'max_connections': 4
            },
            MemoryMode.ENHANCED: {
                'cache_size': 1000,
                'batch_size': 100,
                'max_connections': 8
            },
            MemoryMode.PERFORMANCE: {
                'cache_size': 5000,
                'batch_size': 500,
                'max_connections': 16
            }
        }
        
        return memory_configs.get(self.memory_mode, memory_configs[MemoryMode.STANDARD])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'mode': self.mode.value,
            'db_path': str(self.db_path) if self.db_path else None,
            'memory_mode': self.memory_mode.value,
            'features': {
                'caching': self.enable_caching,
                'batching': self.enable_batching,
                'fts5': self.enable_fts5,
                'streaming': self.enable_streaming,
                'pii_detection': self.enable_pii_detection,
                'audit_logging': self.enable_audit_logging,
                'rbac': self.enable_rbac,
                'secure_deletion': self.enable_secure_deletion,
                'sqlcipher': self.enable_sqlcipher,
                'rate_limiting': self.enable_rate_limiting,
                'encryption': self.enable_encryption
            },
            'performance': {
                'cache_size': self.cache_size if self.enable_caching else None,
                'cache_ttl': self.cache_ttl if self.enable_caching else None,
                'batch_size': self.batch_size if self.enable_batching else None
            },
            'security': {
                'audit_flush_interval': self.audit_flush_interval if self.enable_audit_logging else None,
                'rate_limit_window': self.rate_limit_window if self.enable_rate_limiting else None,
                'rate_limit_max_requests': self.rate_limit_max_requests if self.enable_rate_limiting else None
            },
            'connection': {
                'max_connections': self.max_connections,
                'pool_timeout': self.pool_timeout
            }
        }
    
    @classmethod
    def from_config_manager(cls, config_manager: ConfigurationManager) -> 'StorageConfig':
        """
        Create StorageConfig from M001 ConfigurationManager.
        
        Args:
            config_manager: M001 configuration manager instance
            
        Returns:
            Configured StorageConfig instance
        """
        # Get storage mode from config or environment
        mode_str = config_manager.get('storage_mode', 'basic')
        mode = StorageMode(mode_str.lower())
        
        # Get memory mode
        memory_mode = config_manager.get('memory_mode', MemoryMode.STANDARD)
        
        # Get database path
        db_path = config_manager.get('storage_db_path')
        if db_path and not isinstance(db_path, Path):
            db_path = Path(db_path)
        
        # Create config with mode and memory settings
        storage_config = cls(
            mode=mode,
            memory_mode=memory_mode,
            db_path=db_path
        )
        
        # Apply mode defaults
        storage_config.apply_mode_defaults()
        
        # Apply memory-based adjustments
        memory_config = storage_config.get_memory_config()
        if storage_config.enable_caching:
            storage_config.cache_size = memory_config['cache_size']
        if storage_config.enable_batching:
            storage_config.batch_size = memory_config['batch_size']
        storage_config.max_connections = memory_config['max_connections']
        
        # Override with any explicit config values
        explicit_overrides = {
            'enable_encryption': config_manager.get('encryption_enabled', True),
            'enable_pii_detection': config_manager.get('pii_detection_enabled'),
            'enable_audit_logging': config_manager.get('audit_logging_enabled'),
            'enable_sqlcipher': config_manager.get('sqlcipher_enabled'),
            'cache_size': config_manager.get('storage_cache_size'),
            'batch_size': config_manager.get('storage_batch_size'),
            'rate_limit_max_requests': config_manager.get('rate_limit_max_requests')
        }
        
        for key, value in explicit_overrides.items():
            if value is not None:
                setattr(storage_config, key, value)
        
        return storage_config


class StorageModeSelector:
    """
    Intelligent mode selector based on usage patterns and requirements.
    
    Helps choose the appropriate storage mode based on application
    requirements and available resources.
    """
    
    @staticmethod
    def recommend_mode(
        performance_critical: bool = False,
        security_critical: bool = False,
        resource_constrained: bool = False,
        production_environment: bool = False,
        data_volume: str = "medium"  # low, medium, high
    ) -> StorageMode:
        """
        Recommend storage mode based on requirements.
        
        Args:
            performance_critical: Application requires high performance
            security_critical: Application handles sensitive data
            resource_constrained: Limited memory/CPU available
            production_environment: Deployed in production
            data_volume: Expected data volume (low/medium/high)
            
        Returns:
            Recommended StorageMode
        """
        # Enterprise for production with both performance and security needs
        if production_environment and security_critical:
            return StorageMode.ENTERPRISE
        
        # Secure for security-critical applications
        if security_critical:
            return StorageMode.SECURE
        
        # Performance for high-volume or performance-critical apps
        if performance_critical or data_volume == "high":
            return StorageMode.PERFORMANCE
        
        # Basic for resource-constrained or low-volume scenarios
        if resource_constrained or data_volume == "low":
            return StorageMode.BASIC
        
        # Default to PERFORMANCE for medium scenarios
        return StorageMode.PERFORMANCE
    
    @staticmethod
    def get_mode_comparison() -> Dict[str, Dict[str, Any]]:
        """
        Get detailed comparison of all storage modes.
        
        Returns:
            Dictionary comparing features across modes
        """
        return {
            "BASIC": {
                "description": "Minimal overhead, core functionality only",
                "use_cases": ["Development", "Testing", "Low-volume applications"],
                "performance": "Baseline",
                "memory_usage": "Low (32-64MB)",
                "features": ["CRUD operations", "Basic encryption", "Simple search"],
                "limitations": ["No caching", "No batch operations", "Basic search only"]
            },
            "PERFORMANCE": {
                "description": "Optimized for speed and throughput",
                "use_cases": ["High-volume apps", "Data processing", "Analytics"],
                "performance": "10-100x faster",
                "memory_usage": "Medium (128-256MB)",
                "features": ["LRU caching", "Batch operations", "FTS5 search", "Streaming"],
                "limitations": ["No PII detection", "No audit logging", "Basic security"]
            },
            "SECURE": {
                "description": "Security-hardened for sensitive data",
                "use_cases": ["Healthcare", "Finance", "Government", "PII handling"],
                "performance": "Baseline with overhead",
                "memory_usage": "Medium (64-128MB)",
                "features": ["PII detection", "RBAC", "Audit logging", "Secure deletion", "SQLCipher"],
                "limitations": ["No performance optimizations", "Higher latency"]
            },
            "ENTERPRISE": {
                "description": "Full-featured for production environments",
                "use_cases": ["Enterprise applications", "Regulated industries", "Mission-critical"],
                "performance": "Optimized with security",
                "memory_usage": "High (256-512MB)",
                "features": ["All features enabled", "Best of performance and security"],
                "limitations": ["Higher resource usage", "Complex configuration"]
            }
        }


# Configuration presets for common scenarios

PRESET_CONFIGS = {
    "development": StorageConfig(
        mode=StorageMode.BASIC,
        memory_mode=MemoryMode.BASELINE,
        enable_encryption=False  # Faster development iteration
    ),
    "testing": StorageConfig(
        mode=StorageMode.PERFORMANCE,
        memory_mode=MemoryMode.STANDARD,
        enable_caching=True,
        cache_size=100,
        batch_size=10
    ),
    "staging": StorageConfig(
        mode=StorageMode.ENTERPRISE,
        memory_mode=MemoryMode.ENHANCED,
        enable_audit_logging=True,
        enable_pii_detection=True
    ),
    "production": StorageConfig(
        mode=StorageMode.ENTERPRISE,
        memory_mode=MemoryMode.PERFORMANCE,
        enable_sqlcipher=True,
        enable_secure_deletion=True,
        rate_limit_max_requests=5000
    ),
    "high_security": StorageConfig(
        mode=StorageMode.SECURE,
        memory_mode=MemoryMode.STANDARD,
        enable_sqlcipher=True,
        enable_secure_deletion=True,
        enable_pii_detection=True,
        enable_audit_logging=True,
        audit_flush_interval=5
    ),
    "high_performance": StorageConfig(
        mode=StorageMode.PERFORMANCE,
        memory_mode=MemoryMode.PERFORMANCE,
        cache_size=5000,
        batch_size=500,
        enable_fts5=True,
        enable_streaming=True
    )
}


def get_preset_config(preset: str) -> StorageConfig:
    """
    Get a preset configuration.
    
    Args:
        preset: Preset name (development, testing, staging, production, etc.)
        
    Returns:
        Pre-configured StorageConfig instance
        
    Raises:
        ValueError: If preset not found
    """
    if preset not in PRESET_CONFIGS:
        available = ", ".join(PRESET_CONFIGS.keys())
        raise ValueError(f"Unknown preset '{preset}'. Available: {available}")
    
    config = PRESET_CONFIGS[preset].copy(deep=True)
    config.apply_mode_defaults()
    return config