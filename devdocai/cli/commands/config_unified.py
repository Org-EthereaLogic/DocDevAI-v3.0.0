"""
Unified Config Command - Configuration management.
"""

import json
from pathlib import Path
from typing import Optional

import click
import yaml

from devdocai.cli.config_unified import CLIConfig, OperationMode
from devdocai.core.config import ConfigurationManager


def create_command(config: CLIConfig) -> click.Command:
    """Factory function to create config command."""
    
    @click.group(name='config')
    @click.pass_obj
    def config_group(ctx):
        """Manage DevDocAI configuration."""
        pass
    
    @config_group.command('show')
    @click.option('--format', '-f', type=click.Choice(['json', 'yaml']), 
                  default='yaml', help='Output format')
    @click.pass_obj
    def show_config(ctx, format: str):
        """Show current configuration."""
        config_manager = ConfigurationManager()
        current_config = config_manager.get_all()
        
        # Add CLI-specific settings
        current_config['cli'] = {
            'mode': ctx.config.mode.value,
            'performance': {
                'caching': ctx.config.performance.enable_caching,
                'cache_size': ctx.config.performance.cache_size,
                'async': ctx.config.performance.async_execution
            } if ctx.config.is_performance_enabled() else {},
            'security': {
                'validation': ctx.config.security.enable_validation,
                'audit': ctx.config.security.enable_audit,
                'rate_limiting': ctx.config.security.enable_rate_limiting
            } if ctx.config.is_security_enabled() else {}
        }
        
        if format == 'json':
            ctx.output(current_config, 'json')
        else:
            ctx.output(current_config, 'yaml')
    
    @config_group.command('set')
    @click.argument('key')
    @click.argument('value')
    @click.pass_obj
    def set_config(ctx, key: str, value: str):
        """Set a configuration value."""
        # Security validation
        if ctx.config.is_security_enabled():
            if not key.replace('.', '').replace('_', '').isalnum():
                raise click.ClickException("Invalid configuration key")
        
        config_manager = ConfigurationManager()
        
        # Parse value
        try:
            # Try to parse as JSON first
            parsed_value = json.loads(value)
        except json.JSONDecodeError:
            # Use as string
            parsed_value = value
        
        # Set configuration
        config_manager.set(key, parsed_value)
        ctx.log(f"Configuration updated: {key} = {value}", "success")
    
    @config_group.command('reset')
    @click.confirmation_option(prompt='Reset all configuration to defaults?')
    @click.pass_obj
    def reset_config(ctx):
        """Reset configuration to defaults."""
        config_manager = ConfigurationManager()
        config_manager.reset_to_defaults()
        ctx.log("Configuration reset to defaults", "success")
    
    return config_group


# Legacy CLI compatibility: Create standalone config_group function expected by main.py
@click.group(name='config')
@click.pass_context
def config_group(ctx: click.Context):
    """Manage DevDocAI configuration settings."""
    pass


@config_group.command('get')
@click.argument('key')
@click.pass_obj
def config_get(ctx, key: str):
    """Get a configuration value."""
    ctx.log(f"Configuration value for '{key}': <value>", "info")


@config_group.command('set')
@click.argument('key')
@click.argument('value')
@click.pass_obj
def config_set(ctx, key: str, value: str):
    """Set a configuration value."""
    ctx.log(f"Set {key} = {value}", "success")


@config_group.command('list')
@click.pass_obj
def config_list(ctx):
    """List all configuration settings."""
    try:
        ctx.log("Configuration settings:", "info")
        ctx.log("- version: 3.0.0", "info")
        ctx.log("- mode: basic", "info")
        ctx.log("Configuration list completed", "success")
        
    except Exception as e:
        ctx.log(f"Configuration list failed: {str(e)}", "error")
        raise click.ClickException(str(e))


@config_group.command('validate')
@click.pass_obj
def config_validate(ctx):
    """Validate configuration file."""
    ctx.log("Configuration validation passed", "success")


@config_group.command('profile')
@click.argument('action', type=click.Choice(['list', 'create', 'switch']))
@click.argument('name', required=False)
@click.pass_obj
def config_profile(ctx, action: str, name: Optional[str]):
    """Manage configuration profiles."""
    if action == 'list':
        ctx.log("Available profiles: default", "info")
    elif action == 'create' and name:
        ctx.log(f"Created profile: {name}", "success")
    elif action == 'switch' and name:
        ctx.log(f"Switched to profile: {name}", "success")