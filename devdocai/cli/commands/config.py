"""
Configuration management commands for DevDocAI CLI.

Integrates with M001 Configuration Manager module.
"""

import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
import json
import yaml

import click
from click import Context

# Import M001 Configuration Manager
try:
    from devdocai.core.config import ConfigurationManager
    CONFIG_AVAILABLE = True
except ImportError as e:
    CONFIG_AVAILABLE = False
    IMPORT_ERROR = str(e)


# Default configuration file locations
CONFIG_LOCATIONS = [
    Path.home() / '.devdocai' / 'config.yml',
    Path.cwd() / '.devdocai.yml',
    Path.cwd() / 'devdocai.yml'
]


@click.group('config', invoke_without_command=True)
@click.pass_context
def config_group(ctx: Context):
    """Manage DevDocAI configuration settings."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@config_group.command('get')
@click.argument('key')
@click.option('--profile', '-p', default='default',
              help='Configuration profile to use')
@click.pass_obj
def config_get(cli_ctx, key: str, profile: str):
    """
    Get a configuration value.
    
    Examples:
    
        # Get a specific setting
        devdocai config get api.key
        
        # Get from specific profile
        devdocai config get quality.threshold --profile production
    """
    if not CONFIG_AVAILABLE:
        cli_ctx.log(f"Configuration manager not available: {IMPORT_ERROR}", "error")
        sys.exit(1)
    
    try:
        # Initialize configuration manager
        config_manager = ConfigurationManager()
        
        # Load configuration
        config_file = _find_config_file()
        if config_file:
            config_manager.load_from_file(str(config_file))
            cli_ctx.log(f"Loaded configuration from {config_file}", "debug")
        
        # Switch to profile if specified
        if profile != 'default':
            config_manager.set_profile(profile)
        
        # Get value
        value = config_manager.get(key)
        
        if value is None:
            cli_ctx.log(f"Configuration key '{key}' not found", "warning")
            sys.exit(1)
        
        # Check if value is encrypted
        if isinstance(value, str) and value.startswith('encrypted:'):
            cli_ctx.log("Value is encrypted. Use --decrypt flag to show actual value", "info")
            value = "<encrypted>"
        
        # Output value
        if isinstance(value, (dict, list)):
            cli_ctx.output(value)
        else:
            click.echo(value)
            
    except Exception as e:
        cli_ctx.log(f"Failed to get configuration: {str(e)}", "error")
        if cli_ctx.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@config_group.command('set')
@click.argument('key')
@click.argument('value')
@click.option('--profile', '-p', default='default',
              help='Configuration profile to use')
@click.option('--encrypt', is_flag=True,
              help='Encrypt the value before storing')
@click.option('--type', '-t', 
              type=click.Choice(['string', 'int', 'float', 'bool', 'json']),
              default='string', help='Value type')
@click.pass_obj
def config_set(cli_ctx, key: str, value: str, profile: str, encrypt: bool, type: str):
    """
    Set a configuration value.
    
    Examples:
    
        # Set a simple value
        devdocai config set api.key "sk-abc123"
        
        # Set an encrypted value
        devdocai config set api.key "sk-abc123" --encrypt
        
        # Set a boolean value
        devdocai config set telemetry.enabled false --type bool
        
        # Set a JSON value
        devdocai config set quality.dimensions '["clarity", "completeness"]' --type json
    """
    if not CONFIG_AVAILABLE:
        cli_ctx.log(f"Configuration manager not available: {IMPORT_ERROR}", "error")
        sys.exit(1)
    
    try:
        # Initialize configuration manager
        config_manager = ConfigurationManager()
        
        # Load existing configuration
        config_file = _find_config_file()
        if config_file:
            config_manager.load_from_file(str(config_file))
        else:
            # Create new configuration file
            config_file = CONFIG_LOCATIONS[0]
            config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Switch to profile if specified
        if profile != 'default':
            config_manager.set_profile(profile)
        
        # Parse value based on type
        if type == 'int':
            parsed_value = int(value)
        elif type == 'float':
            parsed_value = float(value)
        elif type == 'bool':
            parsed_value = value.lower() in ('true', 'yes', '1', 'on')
        elif type == 'json':
            parsed_value = json.loads(value)
        else:
            parsed_value = value
        
        # Encrypt if requested
        if encrypt:
            parsed_value = config_manager.encrypt_value(parsed_value)
        
        # Set value
        config_manager.set(key, parsed_value)
        
        # Save configuration
        config_manager.save_to_file(str(config_file))
        
        cli_ctx.log(f"Configuration updated: {key} = {'<encrypted>' if encrypt else value}", "success")
        cli_ctx.log(f"Saved to {config_file}", "info")
        
    except ValueError as e:
        cli_ctx.log(f"Invalid value format: {str(e)}", "error")
        sys.exit(1)
    except Exception as e:
        cli_ctx.log(f"Failed to set configuration: {str(e)}", "error")
        if cli_ctx.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@config_group.command('list')
@click.option('--profile', '-p', default='default',
              help='Configuration profile to use')
@click.option('--show-encrypted', is_flag=True,
              help='Show encrypted values')
@click.pass_obj
def config_list(cli_ctx, profile: str, show_encrypted: bool):
    """
    List all configuration settings.
    
    Examples:
    
        # List all settings
        devdocai config list
        
        # List settings for specific profile
        devdocai config list --profile production
    """
    if not CONFIG_AVAILABLE:
        cli_ctx.log(f"Configuration manager not available: {IMPORT_ERROR}", "error")
        sys.exit(1)
    
    try:
        # Initialize configuration manager
        config_manager = ConfigurationManager()
        
        # Load configuration
        config_file = _find_config_file()
        if config_file:
            config_manager.load_from_file(str(config_file))
            cli_ctx.log(f"Configuration from: {config_file}", "info")
        else:
            cli_ctx.log("No configuration file found, using defaults", "warning")
        
        # Switch to profile if specified
        if profile != 'default':
            config_manager.set_profile(profile)
        
        # Get all configuration
        config_dict = config_manager.to_dict()
        
        # Hide encrypted values unless requested
        if not show_encrypted:
            config_dict = _mask_encrypted_values(config_dict)
        
        # Output configuration
        cli_ctx.output(config_dict)
        
    except Exception as e:
        cli_ctx.log(f"Failed to list configuration: {str(e)}", "error")
        if cli_ctx.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@config_group.command('profile')
@click.argument('action', type=click.Choice(['list', 'create', 'delete', 'switch']))
@click.argument('name', required=False)
@click.option('--copy-from', help='Profile to copy settings from')
@click.pass_obj
def config_profile(cli_ctx, action: str, name: Optional[str], copy_from: Optional[str]):
    """
    Manage configuration profiles.
    
    Examples:
    
        # List all profiles
        devdocai config profile list
        
        # Create new profile
        devdocai config profile create production
        
        # Create profile from existing
        devdocai config profile create staging --copy-from production
        
        # Switch to profile
        devdocai config profile switch production
        
        # Delete profile
        devdocai config profile delete staging
    """
    if not CONFIG_AVAILABLE:
        cli_ctx.log(f"Configuration manager not available: {IMPORT_ERROR}", "error")
        sys.exit(1)
    
    try:
        # Initialize configuration manager
        config_manager = ConfigurationManager()
        
        # Load configuration
        config_file = _find_config_file()
        if config_file:
            config_manager.load_from_file(str(config_file))
        else:
            config_file = CONFIG_LOCATIONS[0]
            config_file.parent.mkdir(parents=True, exist_ok=True)
        
        if action == 'list':
            # List all profiles
            profiles = config_manager.list_profiles()
            current = config_manager.current_profile
            
            cli_ctx.log("Available profiles:", "info")
            for profile in profiles:
                marker = " (current)" if profile == current else ""
                click.echo(f"  - {profile}{marker}")
                
        elif action == 'create':
            if not name:
                cli_ctx.log("Profile name required for create action", "error")
                sys.exit(1)
            
            # Create new profile
            if copy_from:
                # Copy from existing profile
                config_manager.copy_profile(copy_from, name)
                cli_ctx.log(f"Created profile '{name}' from '{copy_from}'", "success")
            else:
                # Create empty profile
                config_manager.create_profile(name)
                cli_ctx.log(f"Created profile '{name}'", "success")
            
            # Save configuration
            config_manager.save_to_file(str(config_file))
            
        elif action == 'switch':
            if not name:
                cli_ctx.log("Profile name required for switch action", "error")
                sys.exit(1)
            
            # Switch to profile
            config_manager.set_profile(name)
            config_manager.save_to_file(str(config_file))
            cli_ctx.log(f"Switched to profile '{name}'", "success")
            
        elif action == 'delete':
            if not name:
                cli_ctx.log("Profile name required for delete action", "error")
                sys.exit(1)
            
            if name == 'default':
                cli_ctx.log("Cannot delete default profile", "error")
                sys.exit(1)
            
            # Delete profile
            config_manager.delete_profile(name)
            config_manager.save_to_file(str(config_file))
            cli_ctx.log(f"Deleted profile '{name}'", "success")
            
    except Exception as e:
        cli_ctx.log(f"Profile operation failed: {str(e)}", "error")
        if cli_ctx.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@config_group.command('validate')
@click.option('--file', '-f', type=click.Path(exists=True),
              help='Configuration file to validate')
@click.option('--strict', is_flag=True,
              help='Enable strict validation')
@click.pass_obj
def config_validate(cli_ctx, file: Optional[str], strict: bool):
    """
    Validate configuration file.
    
    Examples:
    
        # Validate current configuration
        devdocai config validate
        
        # Validate specific file
        devdocai config validate --file config.yml
        
        # Strict validation
        devdocai config validate --strict
    """
    if not CONFIG_AVAILABLE:
        cli_ctx.log(f"Configuration manager not available: {IMPORT_ERROR}", "error")
        sys.exit(1)
    
    try:
        # Initialize configuration manager
        config_manager = ConfigurationManager()
        
        # Determine file to validate
        if file:
            config_file = Path(file)
        else:
            config_file = _find_config_file()
            if not config_file:
                cli_ctx.log("No configuration file found", "warning")
                return
        
        cli_ctx.log(f"Validating: {config_file}", "info")
        
        # Load and validate
        try:
            config_manager.load_from_file(str(config_file))
            
            # Perform validation
            validation_errors = config_manager.validate(strict=strict)
            
            if validation_errors:
                cli_ctx.log("Validation errors found:", "error")
                for error in validation_errors:
                    click.echo(f"  - {error}")
                sys.exit(1)
            else:
                cli_ctx.log("Configuration is valid", "success")
                
        except Exception as e:
            cli_ctx.log(f"Invalid configuration: {str(e)}", "error")
            sys.exit(1)
            
    except Exception as e:
        cli_ctx.log(f"Validation failed: {str(e)}", "error")
        if cli_ctx.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def _find_config_file() -> Optional[Path]:
    """Find configuration file in standard locations."""
    for location in CONFIG_LOCATIONS:
        if location.exists():
            return location
    return None


def _mask_encrypted_values(config: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively mask encrypted values in configuration."""
    result = {}
    for key, value in config.items():
        if isinstance(value, dict):
            result[key] = _mask_encrypted_values(value)
        elif isinstance(value, str) and value.startswith('encrypted:'):
            result[key] = "<encrypted>"
        else:
            result[key] = value
    return result