"""
DevDocAI Command Line Interface

Main entry point for the DevDocAI CLI tool.
"""

import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from devdocai.core.config import ConfigurationManager, ConfigurationError


console = Console()


@click.group()
@click.version_option(version="3.0.0")
@click.option(
    '--config-file',
    type=click.Path(exists=False, path_type=Path),
    help='Path to configuration file'
)
@click.pass_context
def main(ctx, config_file):
    """DevDocAI - AI-powered documentation generation and analysis system"""
    ctx.ensure_object(dict)
    try:
        ctx.obj['config'] = ConfigurationManager(config_file)
    except ConfigurationError as e:
        console.print(f"[red]Configuration Error:[/red] {e}")
        ctx.exit(1)


@main.command()
def generate():
    """Generate documentation using AI"""
    console.print("🚧 [yellow]M004 Document Generator - Coming Soon[/yellow]")


@main.command()
def analyze():
    """Analyze documentation quality"""
    console.print("🚧 [yellow]M005 Quality Analysis - Coming Soon[/yellow]")


@main.group()
@click.pass_context
def config(ctx):
    """Manage configuration"""
    pass


@config.command('show')
@click.pass_context
def show_config(ctx):
    """Show current configuration"""
    config_manager = ctx.obj['config']
    
    # Create configuration table
    table = Table(title="DevDocAI Configuration", show_header=True)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    # Privacy settings
    table.add_row("Privacy Mode", config_manager.get('privacy_mode'))
    table.add_row("Telemetry Enabled", str(config_manager.get('telemetry_enabled')))
    table.add_row("Cloud Features", str(config_manager.get('cloud_features')))
    table.add_row("DSR Enabled", str(config_manager.get('dsr_enabled')))
    
    # Memory settings
    table.add_row("Memory Mode", config_manager.get('memory_mode'))
    table.add_row("Cache Size (MB)", str(config_manager.get('cache_size_mb')))
    table.add_row("Max Concurrent Ops", str(config_manager.get('max_concurrent_operations')))
    
    # Other settings
    table.add_row("Log Level", config_manager.get('log_level'))
    table.add_row("Encryption Enabled", str(config_manager.get('encryption_enabled')))
    table.add_row("API Services", str(len(config_manager.list_api_services())))
    
    console.print(table)


@config.command('set')
@click.argument('key')
@click.argument('value')
@click.pass_context
def set_config(ctx, key, value):
    """Set configuration value"""
    config_manager = ctx.obj['config']
    
    try:
        # Handle boolean values
        if value.lower() in ('true', 'false'):
            value = value.lower() == 'true'
        # Handle integer values
        elif value.isdigit():
            value = int(value)
        
        config_manager.set(key, value)
        console.print(f"✅ Set [cyan]{key}[/cyan] = [green]{value}[/green]")
        
    except ConfigurationError as e:
        console.print(f"[red]Error:[/red] {e}")


@config.command('memory')
@click.pass_context
def memory_info(ctx):
    """Show memory information"""
    config_manager = ctx.obj['config']
    memory_info = config_manager.get_memory_info()
    
    if 'error' in memory_info:
        console.print(f"[red]Memory Error:[/red] {memory_info['error']}")
        return
    
    panel_content = f"""
[cyan]Memory Mode:[/cyan] {memory_info['mode']}
[cyan]Total Memory:[/cyan] {memory_info['total_gb']} GB
[cyan]Available Memory:[/cyan] {memory_info['available_gb']} GB
[cyan]Memory Usage:[/cyan] {memory_info['used_percent']}%
[cyan]Cache Size:[/cyan] {memory_info['cache_size_mb']} MB
[cyan]Max Concurrent Operations:[/cyan] {memory_info['max_concurrent_operations']}
    """
    
    console.print(Panel(panel_content.strip(), title="Memory Information"))


@config.command('privacy')
@click.pass_context
def privacy_status(ctx):
    """Show privacy settings status"""
    config_manager = ctx.obj['config']
    privacy_info = config_manager.get_privacy_status()
    
    panel_content = f"""
[cyan]Privacy Mode:[/cyan] {privacy_info['privacy_mode']}
[cyan]Telemetry:[/cyan] {'✅ Enabled' if privacy_info['telemetry_enabled'] else '❌ Disabled'}
[cyan]Cloud Features:[/cyan] {'✅ Enabled' if privacy_info['cloud_features'] else '❌ Disabled'}
[cyan]DSR Support:[/cyan] {'✅ Enabled' if privacy_info['dsr_enabled'] else '❌ Disabled'}
[cyan]Encryption:[/cyan] {'✅ Enabled' if privacy_info['encryption_enabled'] else '❌ Disabled'}
[cyan]API Services:[/cyan] {privacy_info['api_services_count']} configured
    """
    
    console.print(Panel(panel_content.strip(), title="Privacy Status"))


@config.command('validate')
@click.pass_context
def validate_config(ctx):
    """Validate current configuration"""
    config_manager = ctx.obj['config']
    issues = config_manager.validate_configuration()
    
    if not issues:
        console.print("✅ [green]Configuration is valid[/green]")
    else:
        console.print("[red]Configuration Issues:[/red]")
        for issue in issues:
            console.print(f"  • {issue}")


@config.command('reset')
@click.confirmation_option(prompt='Are you sure you want to reset all settings to defaults?')
@click.pass_context
def reset_config(ctx):
    """Reset configuration to defaults"""
    config_manager = ctx.obj['config']
    config_manager.reset_to_defaults()
    console.print("✅ [green]Configuration reset to privacy-first defaults[/green]")


@config.group('api')
@click.pass_context
def api_config(ctx):
    """Manage API keys"""
    pass


@api_config.command('add')
@click.argument('service')
@click.argument('api_key')
@click.pass_context
def add_api_key(ctx, service, api_key):
    """Add encrypted API key for a service"""
    config_manager = ctx.obj['config']
    
    try:
        config_manager.encrypt_api_key(service, api_key)
        console.print(f"✅ Added encrypted API key for [cyan]{service}[/cyan]")
    except ConfigurationError as e:
        console.print(f"[red]Error:[/red] {e}")


@api_config.command('list')
@click.pass_context
def list_api_keys(ctx):
    """List services with API keys (keys are encrypted)"""
    config_manager = ctx.obj['config']
    services = config_manager.list_api_services()
    
    if not services:
        console.print("No API keys configured")
    else:
        console.print("Services with API keys:")
        for service in services:
            console.print(f"  • {service}")


@api_config.command('remove')
@click.argument('service')
@click.confirmation_option(prompt='Are you sure you want to remove this API key?')
@click.pass_context
def remove_api_key(ctx, service):
    """Remove API key for a service"""
    config_manager = ctx.obj['config']
    
    if config_manager.remove_api_key(service):
        console.print(f"✅ Removed API key for [cyan]{service}[/cyan]")
    else:
        console.print(f"[yellow]No API key found for {service}[/yellow]")


if __name__ == "__main__":
    main()