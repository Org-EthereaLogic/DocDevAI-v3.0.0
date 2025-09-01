"""
DevDocAI CLI - Unified main entry point with mode-based operation.

Consolidates base, optimized, and secure implementations into a single
configurable CLI supporting 4 operation modes:
- BASIC: Core functionality only
- PERFORMANCE: Optimized with caching and lazy loading
- SECURE: Full security features enabled
- ENTERPRISE: All features with maximum security and performance
"""

import os
import sys
import time
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from functools import lru_cache, wraps
from contextlib import contextmanager

import click
from click import Context

from devdocai.cli.config_unified import (
    OperationMode, CLIConfig, get_config, set_config, init_config
)

# Version information
VERSION = "3.0.0"

# Global context settings
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


class UnifiedCLIContext:
    """Unified CLI context with mode-based behavior."""
    
    def __init__(self, config: Optional[CLIConfig] = None):
        """Initialize context with optional configuration."""
        self.config = config or get_config()
        
        # Basic properties
        self.debug = self.config.debug
        self.json_output = self.config.json_output
        self.yaml_output = self.config.yaml_output
        self.quiet = self.config.quiet
        self.config_path = self.config.config_path
        
        # Security properties (conditional)
        if self.config.is_security_enabled():
            self.session_id = None
            self.user_role = None
            self._init_security_components()
        
        # Performance properties (conditional)
        if self.config.is_performance_enabled():
            self._init_performance_components()
    
    def _init_security_components(self):
        """Initialize security components if enabled."""
        if self.config.security.enable_validation:
            from devdocai.cli.utils.security import InputSanitizer
            self.sanitizer = InputSanitizer(strict_mode=True)
        
        if self.config.security.enable_credentials:
            from devdocai.cli.utils.security import SecureCredentialManager
            self.cred_manager = SecureCredentialManager()
        
        if self.config.security.enable_rate_limiting:
            from devdocai.cli.utils.security import CommandRateLimiter
            self.rate_limiter = CommandRateLimiter()
        
        if self.config.security.enable_audit:
            from devdocai.cli.utils.security import SecurityAuditLogger
            self.audit_logger = SecurityAuditLogger()
        
        if self.config.security.enable_session_management:
            from devdocai.cli.utils.security import SecureSessionManager
            self.session_manager = SecureSessionManager()
    
    def _init_performance_components(self):
        """Initialize performance components if enabled."""
        if self.config.performance.enable_caching:
            self._cache = {}
            self._cache_size = self.config.performance.cache_size
        
        if self.config.performance.async_execution:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
    
    def log(self, message: str, level: str = "info"):
        """Log a message with optional security masking."""
        # Apply security masking if enabled
        if (self.config.is_security_enabled() and 
            hasattr(self, 'cred_manager')):
            message = self.cred_manager.mask_sensitive_data(message)
        
        if self.quiet and level != "error":
            return
        
        # Log to audit if enabled
        if (self.config.security.enable_audit and 
            hasattr(self, 'audit_logger') and
            level == "error"):
            self.audit_logger.log_event(
                event_type="SYSTEM_ERROR",
                severity="ERROR",
                details={'message': message}
            )
        
        # Output message
        if level == "error":
            click.echo(click.style(f"ERROR: {message}", fg="red"), err=True)
        elif level == "warning":
            click.echo(click.style(f"WARNING: {message}", fg="yellow"), err=True)
        elif level == "success":
            click.echo(click.style(f"✓ {message}", fg="green"))
        elif self.debug or level == "info":
            click.echo(message)
        elif level == "debug" and self.debug:
            click.echo(click.style(f"DEBUG: {message}", fg="cyan"))
    
    def output(self, data: Any, format_type: Optional[str] = None):
        """Output data with optional formatting and security masking."""
        # Apply security masking if enabled
        if (self.config.is_security_enabled() and 
            hasattr(self, 'cred_manager')):
            if isinstance(data, str):
                data = self.cred_manager.mask_sensitive_data(data)
            elif isinstance(data, dict):
                data = self._mask_dict(data)
        
        # Format output
        if self.json_output or format_type == "json":
            import json
            click.echo(json.dumps(data, indent=2, default=str))
        elif self.yaml_output or format_type == "yaml":
            import yaml
            click.echo(yaml.dump(data, default_flow_style=False))
        else:
            if isinstance(data, dict):
                for key, value in data.items():
                    click.echo(f"{key}: {value}")
            elif isinstance(data, list):
                for item in data:
                    click.echo(f"- {item}")
            else:
                click.echo(str(data))
    
    def _mask_dict(self, data: dict) -> dict:
        """Recursively mask sensitive data in dictionary."""
        masked = {}
        for key, value in data.items():
            if isinstance(value, dict):
                masked[key] = self._mask_dict(value)
            elif isinstance(value, str):
                masked[key] = self.cred_manager.mask_sensitive_data(value)
            else:
                masked[key] = value
        return masked
    
    @contextmanager
    def performance_timer(self, operation: str):
        """Context manager for timing operations in performance mode."""
        if not self.config.is_performance_enabled():
            yield
            return
        
        start_time = time.time()
        yield
        elapsed = time.time() - start_time
        
        if self.debug:
            self.log(f"Operation '{operation}' took {elapsed:.3f}s", "debug")


def create_cli(mode: str = "basic") -> click.Group:
    """Factory function to create CLI with specified mode."""
    # Initialize configuration
    config = init_config(mode)
    
    @click.group(context_settings=CONTEXT_SETTINGS)
    @click.version_option(VERSION, '--version', '-v')
    @click.option('--debug', is_flag=True, help='Enable debug output')
    @click.option('--quiet', '-q', is_flag=True, help='Suppress non-error output')
    @click.option('--json', 'json_output', is_flag=True, help='Output in JSON format')
    @click.option('--yaml', 'yaml_output', is_flag=True, help='Output in YAML format')
    @click.option('--config', '-c', type=click.Path(exists=True), help='Config file path')
    @click.option('--mode', type=click.Choice(['basic', 'performance', 'secure', 'enterprise']),
                  default=mode, help='Operation mode')
    @click.pass_context
    def cli(ctx: Context, debug: bool, quiet: bool, json_output: bool, 
            yaml_output: bool, config: Optional[str], mode: str):
        """DevDocAI - AI-powered documentation generation and analysis."""
        # Reinitialize config if mode changed
        if mode != config.mode.value:
            config = init_config(mode)
        
        # Update config with command line options
        config.debug = debug
        config.quiet = quiet
        config.json_output = json_output
        config.yaml_output = yaml_output
        if config:
            config.config_path = Path(config)
        
        # Create and attach context
        ctx.obj = UnifiedCLIContext(config)
        
        # Log mode if debug enabled
        if debug:
            ctx.obj.log(f"Running in {mode.upper()} mode", "debug")
    
    # Import and register commands based on mode
    _register_commands(cli, config)
    
    return cli


def _register_commands(cli: click.Group, config: CLIConfig):
    """Register commands based on configuration mode."""
    # Import unified command modules
    from devdocai.cli.commands import (
        generate_unified,
        analyze_unified,
        config_unified,
        enhance_unified,
        template_unified,
        security_unified
    )
    
    # Register core commands (always available)
    cli.add_command(generate_unified.create_command(config))
    cli.add_command(analyze_unified.create_command(config))
    cli.add_command(config_unified.create_command(config))
    
    # Register optional commands based on mode
    if config.mode != OperationMode.BASIC:
        cli.add_command(enhance_unified.create_command(config))
        cli.add_command(template_unified.create_command(config))
    
    # Register security command in secure/enterprise modes
    if config.is_security_enabled():
        cli.add_command(security_unified.create_command(config))


def performance_optimized_startup():
    """Optimized startup for performance mode."""
    # Lazy imports
    import importlib
    
    # Pre-compile regex patterns
    import re
    patterns = {
        'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        'url': re.compile(r'https?://(?:[-\w.])+(?::\d+)?(?:[/\w._-]*)'),
        'path': re.compile(r'^(/[^/ ]*)+/?$')
    }
    
    # Pre-warm caches
    get_config()
    
    return patterns


def main():
    """Main entry point with mode detection."""
    # Detect mode from environment or arguments
    mode = os.environ.get('DEVDOCAI_MODE', 'basic')
    
    # Check for mode in sys.argv
    for i, arg in enumerate(sys.argv):
        if arg == '--mode' and i + 1 < len(sys.argv):
            mode = sys.argv[i + 1]
            break
    
    # Apply startup optimizations for performance mode
    if mode in ('performance', 'enterprise'):
        performance_optimized_startup()
    
    # Create and run CLI
    cli = create_cli(mode)
    
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled by user.", err=True)
        sys.exit(1)
    except Exception as e:
        if '--debug' in sys.argv or os.environ.get('DEVDOCAI_DEBUG'):
            import traceback
            traceback.print_exc()
        else:
            click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()