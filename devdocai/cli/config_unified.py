"""
Unified CLI Configuration - Mode-based operation configuration.

Provides configuration for 4 operation modes:
- BASIC: Core functionality only
- PERFORMANCE: Optimized with caching and lazy loading
- SECURE: Full security features enabled
- ENTERPRISE: All features with maximum security and performance
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from pathlib import Path


class OperationMode(Enum):
    """CLI operation modes."""
    BASIC = "basic"
    PERFORMANCE = "performance"
    SECURE = "secure"
    ENTERPRISE = "enterprise"


@dataclass
class PerformanceConfig:
    """Performance optimization settings."""
    enable_caching: bool = False
    cache_size: int = 128
    lazy_loading: bool = False
    async_execution: bool = False
    batch_size: int = 10
    connection_pooling: bool = False
    max_workers: int = 4
    startup_optimization: bool = False
    memory_optimization: bool = False
    profile_guided: bool = False


@dataclass
class SecurityConfig:
    """Security feature settings."""
    enable_validation: bool = True
    enable_sanitization: bool = False
    enable_audit: bool = False
    enable_rate_limiting: bool = False
    enable_credentials: bool = False
    enable_session_management: bool = False
    enable_rbac: bool = False
    encryption_enabled: bool = False
    max_input_size: int = 10_000_000  # 10MB
    allowed_file_types: List[str] = field(default_factory=lambda: ['.py', '.md', '.txt', '.json', '.yaml', '.yml'])
    audit_file: str = "cli_audit.log"
    session_timeout: int = 3600  # 1 hour


@dataclass
class CLIConfig:
    """Unified CLI configuration."""
    mode: OperationMode = OperationMode.BASIC
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    
    # Global settings
    debug: bool = False
    quiet: bool = False
    json_output: bool = False
    yaml_output: bool = False
    config_path: Optional[Path] = None
    
    # Feature flags
    enable_progress_bars: bool = True
    enable_colors: bool = True
    enable_interactive: bool = True
    enable_completion: bool = True
    
    @classmethod
    def create_for_mode(cls, mode: OperationMode, **kwargs) -> 'CLIConfig':
        """Factory method to create configuration for specific mode."""
        config = cls(mode=mode, **kwargs)
        
        if mode == OperationMode.BASIC:
            # Minimal features for basic mode
            config.performance = PerformanceConfig()
            config.security = SecurityConfig(enable_validation=True)
            
        elif mode == OperationMode.PERFORMANCE:
            # Enable all performance optimizations
            config.performance = PerformanceConfig(
                enable_caching=True,
                cache_size=256,
                lazy_loading=True,
                async_execution=True,
                batch_size=50,
                connection_pooling=True,
                max_workers=8,
                startup_optimization=True,
                memory_optimization=True,
                profile_guided=True
            )
            config.security = SecurityConfig(enable_validation=True)
            
        elif mode == OperationMode.SECURE:
            # Enable all security features
            config.performance = PerformanceConfig(enable_caching=True)
            config.security = SecurityConfig(
                enable_validation=True,
                enable_sanitization=True,
                enable_audit=True,
                enable_rate_limiting=True,
                enable_credentials=True,
                enable_session_management=True,
                enable_rbac=False,  # Not in basic secure mode
                encryption_enabled=True,
                max_input_size=5_000_000  # 5MB limit
            )
            
        elif mode == OperationMode.ENTERPRISE:
            # Maximum features for enterprise
            config.performance = PerformanceConfig(
                enable_caching=True,
                cache_size=512,
                lazy_loading=True,
                async_execution=True,
                batch_size=100,
                connection_pooling=True,
                max_workers=16,
                startup_optimization=True,
                memory_optimization=True,
                profile_guided=True
            )
            config.security = SecurityConfig(
                enable_validation=True,
                enable_sanitization=True,
                enable_audit=True,
                enable_rate_limiting=True,
                enable_credentials=True,
                enable_session_management=True,
                enable_rbac=True,
                encryption_enabled=True,
                max_input_size=50_000_000,  # 50MB limit
                session_timeout=7200  # 2 hours
            )
            
        return config
    
    def is_performance_enabled(self) -> bool:
        """Check if performance features are enabled."""
        return self.mode in (OperationMode.PERFORMANCE, OperationMode.ENTERPRISE)
    
    def is_security_enabled(self) -> bool:
        """Check if security features are enabled."""
        return self.mode in (OperationMode.SECURE, OperationMode.ENTERPRISE)
    
    def get_cache_size(self) -> int:
        """Get appropriate cache size for mode."""
        if self.mode == OperationMode.ENTERPRISE:
            return 512
        elif self.mode == OperationMode.PERFORMANCE:
            return 256
        elif self.mode == OperationMode.SECURE:
            return 128
        return 0
    
    def should_validate_input(self) -> bool:
        """Determine if input validation is needed."""
        return self.security.enable_validation
    
    def should_audit(self) -> bool:
        """Determine if audit logging is needed."""
        return self.security.enable_audit and self.is_security_enabled()


# Global configuration instance
_config: Optional[CLIConfig] = None


def get_config() -> CLIConfig:
    """Get global CLI configuration."""
    global _config
    if _config is None:
        # Default to BASIC mode if not initialized
        _config = CLIConfig.create_for_mode(OperationMode.BASIC)
    return _config


def set_config(config: CLIConfig) -> None:
    """Set global CLI configuration."""
    global _config
    _config = config


def init_config(mode: str = "basic", **kwargs) -> CLIConfig:
    """Initialize configuration with specified mode."""
    try:
        operation_mode = OperationMode(mode.lower())
    except ValueError:
        operation_mode = OperationMode.BASIC
    
    config = CLIConfig.create_for_mode(operation_mode, **kwargs)
    set_config(config)
    return config