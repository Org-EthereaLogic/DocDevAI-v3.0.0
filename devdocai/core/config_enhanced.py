"""
M001: Enhanced Configuration Manager with Improved Error Handling

This module extends the original ConfigurationManager with:
- User-friendly error messages
- Recovery mechanisms for common failures
- Better error context and suggestions

Addresses ISS-014: Error message quality improvement
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union
from functools import lru_cache

# Import original configuration components
from devdocai.core.config import (
    SecurityConfig, DatabaseConfig, CacheConfig,
    DocumentationConfig, AdvancedFeaturesConfig,
    DevelopmentConfig, IntegrationConfig, Configuration
)

# Import new error handling and recovery
from devdocai.core.error_handler import (
    UserFriendlyError, ErrorCategory, ErrorContext,
    ErrorHandler, ConfigurationErrorHandler
)
from devdocai.core.recovery_manager import (
    RecoveryManager, RetryConfig, FileSystemRecovery
)

logger = logging.getLogger(__name__)


class EnhancedConfigurationManager:
    """
    Enhanced Configuration Manager with improved error handling and recovery.
    
    This class wraps the original ConfigurationManager with:
    - User-friendly error messages
    - Automatic retry on transient failures
    - Helpful suggestions for configuration issues
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize with enhanced error handling."""
        self.config_path = config_path or self._find_config_file()
        self.config: Optional[Configuration] = None
        self._lock = __import__('threading').Lock()
        self.recovery = RecoveryManager()
        
        # Try to load configuration with recovery
        self._load_configuration()
    
    def _find_config_file(self) -> str:
        """Find configuration file with user-friendly errors."""
        search_paths = [
            Path.cwd() / ".devdocai.yml",
            Path.cwd() / ".devdocai.yaml",
            Path.home() / ".devdocai" / "config.yml",
            Path("/etc/devdocai/config.yml")
        ]
        
        for path in search_paths:
            if path.exists():
                logger.info(f"Found configuration at: {path}")
                return str(path)
        
        # No config found - provide helpful error
        raise ConfigurationErrorHandler.handle_missing_config(".devdocai.yml")
    
    @ErrorHandler.wrap_operation("load_configuration", "M001")
    def _load_configuration(self):
        """Load configuration with enhanced error handling."""
        try:
            # Use recovery manager for retry on file system issues
            @self.recovery.retry_with_backoff(
                RetryConfig(max_attempts=3, retry_on=[IOError, OSError])
            )
            def load_yaml():
                with open(self.config_path, 'r') as f:
                    return yaml.safe_load(f)
            
            raw_config = load_yaml()
            
            if not raw_config:
                raise UserFriendlyError(
                    category=ErrorCategory.CONFIGURATION,
                    user_message="Configuration file is empty",
                    context=ErrorContext(
                        module="M001",
                        operation="load_configuration",
                        details={"file": self.config_path},
                        suggestions=[
                            "Add configuration settings to the file",
                            "Copy from .devdocai.yml.example if available",
                            "Run 'devdocai init' to generate default configuration"
                        ]
                    )
                )
            
            # Validate configuration
            try:
                self.config = Configuration(**raw_config)
            except ValidationError as e:
                # Convert Pydantic validation errors to user-friendly format
                errors = {}
                for error in e.errors():
                    field = '.'.join(str(loc) for loc in error['loc'])
                    if field not in errors:
                        errors[field] = []
                    errors[field].append(error['msg'])
                
                raise ConfigurationErrorHandler.handle_invalid_config(errors)
            
            logger.info("Configuration loaded successfully")
            
        except yaml.YAMLError as e:
            raise UserFriendlyError(
                technical_error=e,
                category=ErrorCategory.CONFIGURATION,
                user_message="Configuration file has invalid YAML syntax",
                context=ErrorContext(
                    module="M001",
                    operation="parse_yaml",
                    details={
                        "file": self.config_path,
                        "line": getattr(e, 'problem_mark', {}).get('line', 'unknown')
                    },
                    suggestions=[
                        "Check for incorrect indentation (YAML uses spaces, not tabs)",
                        "Ensure all strings with special characters are quoted",
                        "Validate YAML syntax at yamllint.com",
                        "Look for missing colons after keys"
                    ]
                )
            )
        except FileNotFoundError:
            raise ConfigurationErrorHandler.handle_missing_config(self.config_path)
        except PermissionError as e:
            raise UserFriendlyError(
                technical_error=e,
                category=ErrorCategory.PERMISSION,
                user_message="Cannot read configuration file due to permissions",
                context=ErrorContext(
                    module="M001",
                    operation="read_config",
                    details={"file": self.config_path},
                    suggestions=[
                        f"Check file permissions: ls -la {self.config_path}",
                        f"Fix permissions: chmod 644 {self.config_path}",
                        "Run with appropriate user privileges"
                    ]
                )
            )
    
    @ErrorHandler.wrap_operation("get_config_value", "M001")
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value with enhanced error handling.
        
        Args:
            key: Dot-notation key (e.g., 'security.privacy_mode')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        if not self.config:
            raise UserFriendlyError(
                category=ErrorCategory.CONFIGURATION,
                user_message="Configuration not loaded",
                context=ErrorContext(
                    module="M001",
                    operation="get_config_value",
                    suggestions=[
                        "Ensure configuration file exists",
                        "Check for initialization errors in logs",
                        "Run 'devdocai init' to create configuration"
                    ]
                )
            )
        
        try:
            # Navigate nested configuration
            keys = key.split('.')
            value = self.config.model_dump()
            
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                    if value is None:
                        return default
                else:
                    return default
            
            return value
            
        except Exception as e:
            logger.debug(f"Error getting config key '{key}': {e}")
            return default
    
    @ErrorHandler.wrap_operation("set_config_value", "M001")
    def set(self, key: str, value: Any) -> bool:
        """
        Set configuration value with validation.
        
        Args:
            key: Dot-notation key
            value: Value to set
            
        Returns:
            True if successful
        """
        if not self.config:
            raise UserFriendlyError(
                category=ErrorCategory.CONFIGURATION,
                user_message="Cannot modify configuration before loading",
                context=ErrorContext(
                    module="M001",
                    operation="set_config_value",
                    suggestions=["Load configuration first"]
                )
            )
        
        try:
            # Navigate to parent and set value
            keys = key.split('.')
            config_dict = self.config.model_dump()
            
            # Navigate to parent
            parent = config_dict
            for k in keys[:-1]:
                if k not in parent:
                    parent[k] = {}
                parent = parent[k]
            
            # Set the value
            parent[keys[-1]] = value
            
            # Validate new configuration
            try:
                self.config = Configuration(**config_dict)
                return True
            except ValidationError as e:
                # Extract first error for user message
                first_error = e.errors()[0]
                field = '.'.join(str(loc) for loc in first_error['loc'])
                
                raise UserFriendlyError(
                    technical_error=e,
                    category=ErrorCategory.VALIDATION,
                    user_message=f"Invalid value for {field}",
                    context=ErrorContext(
                        module="M001",
                        operation="validate_config_value",
                        details={
                            "field": field,
                            "value": value,
                            "error": first_error['msg']
                        },
                        suggestions=[
                            "Check the value type and format",
                            "Refer to configuration documentation",
                            f"Valid values for {field} are listed in the schema"
                        ]
                    )
                )
                
        except Exception as e:
            raise ErrorHandler.handle_error(
                e,
                ErrorContext(
                    module="M001",
                    operation="set_config_value",
                    details={"key": key, "value": value}
                )
            )
    
    @ErrorHandler.wrap_operation("save_configuration", "M001")
    def save(self, backup: bool = True) -> bool:
        """
        Save configuration with automatic backup.
        
        Args:
            backup: Whether to create backup before saving
            
        Returns:
            True if successful
        """
        if not self.config:
            raise UserFriendlyError(
                category=ErrorCategory.CONFIGURATION,
                user_message="No configuration to save",
                context=ErrorContext(
                    module="M001",
                    operation="save_configuration",
                    suggestions=["Load or create configuration first"]
                )
            )
        
        try:
            # Use safe file write from recovery manager
            config_dict = self.config.model_dump(exclude_none=True)
            yaml_content = yaml.dump(config_dict, default_flow_style=False)
            
            FileSystemRecovery.safe_file_write(
                self.config_path,
                yaml_content,
                mode='w'
            )
            
            logger.info(f"Configuration saved to {self.config_path}")
            return True
            
        except PermissionError as e:
            raise UserFriendlyError(
                technical_error=e,
                category=ErrorCategory.PERMISSION,
                user_message="Cannot write configuration file",
                context=ErrorContext(
                    module="M001",
                    operation="save_configuration",
                    details={"file": self.config_path},
                    suggestions=[
                        f"Check directory permissions: ls -la {Path(self.config_path).parent}",
                        f"Fix permissions: chmod 755 {Path(self.config_path).parent}",
                        "Try saving to a different location"
                    ]
                )
            )
        except IOError as e:
            raise UserFriendlyError(
                technical_error=e,
                category=ErrorCategory.FILE_SYSTEM,
                user_message="Failed to save configuration file",
                context=ErrorContext(
                    module="M001",
                    operation="save_configuration",
                    details={"file": self.config_path},
                    suggestions=[
                        "Check available disk space",
                        "Ensure the directory exists",
                        "Try saving to a different location"
                    ]
                )
            )
    
    def validate(self) -> Dict[str, Any]:
        """
        Validate configuration with user-friendly output.
        
        Returns:
            Validation result with any issues found
        """
        result = {
            "valid": True,
            "issues": [],
            "warnings": []
        }
        
        if not self.config:
            result["valid"] = False
            result["issues"].append("Configuration not loaded")
            return result
        
        # Check critical settings
        if self.config.security.privacy_mode == "cloud" and not self.config.security.cloud_features:
            result["warnings"].append(
                "Privacy mode is 'cloud' but cloud features are disabled. "
                "Consider enabling cloud features or switching to 'local_only' mode."
            )
        
        # Check for missing API keys in production
        if self.config.development.debug_mode is False:
            integrations = self.config.integrations.model_dump()
            for service, settings in integrations.items():
                if isinstance(settings, dict) and settings.get('enabled'):
                    if not settings.get('api_key'):
                        result["warnings"].append(
                            f"{service} is enabled but API key is not configured. "
                            f"Set the API key in configuration or environment variables."
                        )
        
        # Check database configuration
        if self.config.database.connection_timeout < 5:
            result["warnings"].append(
                "Database connection timeout is very low (<5s). "
                "This may cause issues under load."
            )
        
        return result
    
    def get_info(self) -> Dict[str, Any]:
        """Get configuration information for display."""
        if not self.config:
            return {"error": "Configuration not loaded"}
        
        return {
            "config_file": self.config_path,
            "privacy_mode": self.config.security.privacy_mode,
            "telemetry": "disabled" if not self.config.security.telemetry_enabled else "enabled",
            "cloud_features": "disabled" if not self.config.security.cloud_features else "enabled",
            "debug_mode": self.config.development.debug_mode,
            "modules_enabled": sum(
                1 for v in self.config.integrations.model_dump().values()
                if isinstance(v, dict) and v.get('enabled')
            ),
            "validation": self.validate()
        }


# Factory function to create enhanced configuration manager
def create_enhanced_config_manager(config_path: Optional[str] = None) -> EnhancedConfigurationManager:
    """
    Create an enhanced configuration manager with improved error handling.
    
    Args:
        config_path: Optional path to configuration file
        
    Returns:
        EnhancedConfigurationManager instance
    """
    try:
        return EnhancedConfigurationManager(config_path)
    except UserFriendlyError:
        # Already user-friendly, re-raise
        raise
    except Exception as e:
        # Wrap any other errors
        raise ErrorHandler.handle_error(
            e,
            ErrorContext(
                module="M001",
                operation="create_config_manager",
                suggestions=[
                    "Check if configuration file exists",
                    "Run 'devdocai init' to create default configuration",
                    "Check file permissions and path"
                ]
            )
        )