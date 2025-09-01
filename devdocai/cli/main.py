"""
DevDocAI CLI - Main entry point for command-line interface.

Provides a comprehensive CLI for documentation generation, analysis, and management.
"""

import os
import sys
import json
import yaml
from pathlib import Path
from typing import Optional, Dict, Any

import click
from click import Context

# Version information
VERSION = "3.0.0"

# Global context settings
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


class CLIContext:
    """Global context object for passing configuration through commands."""
    
    def __init__(self):
        self.debug = False
        self.json_output = False
        self.yaml_output = False
        self.quiet = False
        self.config_path = None
        self.config = {}
        
    def log(self, message: str, level: str = "info"):
        """Log a message based on verbosity settings."""
        if self.quiet and level != "error":
            return
            
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
        """Output data in the requested format."""
        if self.json_output or format_type == "json":
            click.echo(json.dumps(data, indent=2, default=str))
        elif self.yaml_output or format_type == "yaml":
            click.echo(yaml.dump(data, default_flow_style=False))
        else:
            # Default human-readable output
            if isinstance(data, dict):
                for key, value in data.items():
                    click.echo(f"{key}: {value}")
            elif isinstance(data, list):
                for item in data:
                    click.echo(f"  - {item}")
            else:
                click.echo(str(data))


@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.option('--version', is_flag=True, help='Show version information')
@click.option('--debug', is_flag=True, help='Enable debug output')
@click.option('--json', 'json_output', is_flag=True, help='Output in JSON format')
@click.option('--yaml', 'yaml_output', is_flag=True, help='Output in YAML format')
@click.option('--quiet', '-q', is_flag=True, help='Suppress non-error output')
@click.option('--config', '-c', type=click.Path(exists=True), 
              help='Path to configuration file')
@click.pass_context
def cli(ctx: Context, version: bool, debug: bool, json_output: bool, 
        yaml_output: bool, quiet: bool, config: Optional[str]):
    """
    DevDocAI - AI-Powered Documentation Generation System
    
    A comprehensive CLI for generating, analyzing, and managing documentation
    with AI assistance. Privacy-first, offline-capable, and developer-focused.
    
    Examples:
    
        # Generate documentation for a Python file
        devdocai generate api.py --template api-endpoint
        
        # Analyze documentation quality
        devdocai analyze README.md --dimensions all
        
        # List available templates
        devdocai template list
        
        # Configure settings
        devdocai config set api.key "your-key-here"
    
    Use 'devdocai COMMAND --help' for more information on a command.
    """
    # Initialize context object
    ctx.ensure_object(CLIContext)
    cli_ctx = ctx.obj
    
    # Set context properties
    cli_ctx.debug = debug
    cli_ctx.json_output = json_output
    cli_ctx.yaml_output = yaml_output
    cli_ctx.quiet = quiet
    cli_ctx.config_path = config
    
    # Show version if requested
    if version:
        version_info = {
            "version": VERSION,
            "python": sys.version.split()[0],
            "platform": sys.platform
        }
        cli_ctx.output(version_info)
        ctx.exit()
    
    # Show help if no command provided
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# Import command groups
from .commands import generate, analyze, config, template, enhance, security

# Register command groups
cli.add_command(generate.generate_group)
cli.add_command(analyze.analyze_group)
cli.add_command(config.config_group)
cli.add_command(template.template_group)
cli.add_command(enhance.enhance_group)
cli.add_command(security.security_group)


# Shell completion setup
def get_completion():
    """Get shell completion script."""
    shell = os.environ.get('SHELL', '/bin/bash')
    if 'zsh' in shell:
        return 'eval "$(_DEVDOCAI_COMPLETE=zsh_source devdocai)"'
    elif 'fish' in shell:
        return 'eval "$(_DEVDOCAI_COMPLETE=fish_source devdocai)"'
    else:
        return 'eval "$(_DEVDOCAI_COMPLETE=bash_source devdocai)"'


@cli.command('completion')
@click.pass_obj
def show_completion(cli_ctx: CLIContext):
    """Show shell completion installation instructions."""
    instructions = f"""
To enable shell completion for devdocai, add the following to your shell configuration:

{get_completion()}

For bash, add to ~/.bashrc:
    eval "$(_DEVDOCAI_COMPLETE=bash_source devdocai)"

For zsh, add to ~/.zshrc:
    eval "$(_DEVDOCAI_COMPLETE=zsh_source devdocai)"

For fish, add to ~/.config/fish/config.fish:
    eval "$(_DEVDOCAI_COMPLETE=fish_source devdocai)"

Then reload your shell configuration:
    source ~/.bashrc  # or ~/.zshrc, etc.
"""
    click.echo(instructions)


# Shorthand alias support
@cli.command('init')
@click.option('--template', default='default', help='Initial template to use')
@click.pass_obj
def init_project(cli_ctx: CLIContext, template: str):
    """Initialize a new DevDocAI project in the current directory."""
    cli_ctx.log("Initializing DevDocAI project...", "info")
    
    # Create default configuration file
    config_content = {
        'version': VERSION,
        'project': {
            'name': Path.cwd().name,
            'description': 'AI-powered documentation project'
        },
        'templates': {
            'default': template
        },
        'quality': {
            'threshold': 0.8,
            'dimensions': ['completeness', 'clarity', 'technical_accuracy']
        }
    }
    
    config_path = Path('.devdocai.yml')
    if config_path.exists():
        cli_ctx.log("Configuration file already exists", "warning")
        if not click.confirm("Overwrite existing configuration?"):
            return
    
    with open(config_path, 'w') as f:
        yaml.dump(config_content, f, default_flow_style=False)
    
    cli_ctx.log(f"Project initialized with template '{template}'", "success")
    cli_ctx.log("Configuration saved to .devdocai.yml", "success")


if __name__ == '__main__':
    cli()