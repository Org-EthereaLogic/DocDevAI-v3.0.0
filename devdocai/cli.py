#!/usr/bin/env python3
"""
DevDocAI Command Line Interface (CLI) - Minimal Stub

This is a minimal implementation to satisfy CI/CD requirements.
Full CLI implementation will be added when needed.

This stub provides:
- Basic entry point for `devdocai` command
- Config show command for CI/CD validation
- Forward-compatible structure for future expansion
"""

import sys

import click
from rich.console import Console
from rich.table import Table

# Import our existing M001 Configuration Manager
from devdocai.core.config import ConfigurationManager

console = Console()


@click.group()
@click.version_option(version="3.0.0", prog_name="DevDocAI")
def cli() -> None:
    """DevDocAI - AI-powered documentation generation and analysis system."""
    pass


@cli.group()
def config() -> None:
    """Configuration management commands."""
    pass


@config.command()
def show() -> None:
    """Show current configuration settings."""
    try:
        # Use our existing M001 Configuration Manager
        config_manager = ConfigurationManager()

        # Create a nice table for display
        table = Table(title="DevDocAI Configuration", show_header=True)
        table.add_column("Setting", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")
        table.add_column("Source", style="yellow")

        # Show some basic settings
        # Import MemoryDetector to show system memory
        import psutil

        from devdocai.core.memory import MemoryDetector

        memory_gb = psutil.virtual_memory().total / (1024**3)
        memory_mode = MemoryDetector.detect_memory_mode()

        settings = [
            ("privacy_mode", config_manager.get("privacy.mode", "LOCAL_ONLY"), "default"),
            (
                "telemetry_enabled",
                str(config_manager.get("privacy.telemetry_enabled", False)),
                "default",
            ),
            ("api_provider", config_manager.get("llm.default_provider", "openai"), "default"),
            ("available_memory", f"{memory_gb:.1f} GB", "system"),
            ("memory_mode", memory_mode, "detected"),
            ("config_file", str(config_manager.config_file), "path"),
        ]

        for setting, value, source in settings:
            table.add_row(setting, str(value), source)

        console.print(table)
        console.print("\n✅ Configuration loaded successfully", style="green")

    except Exception as e:
        console.print(f"❌ Error loading configuration: {e}", style="red")
        sys.exit(1)


@cli.command()
def version() -> None:
    """Show DevDocAI version information."""
    console.print("DevDocAI v3.0.0", style="bold cyan")
    console.print("Python-based AI documentation system", style="dim")
    console.print("Implementation Progress: M001 Complete (7.7%)", style="yellow")


@cli.group()
def generate() -> None:
    """Document generation commands (NOT IMPLEMENTED)."""
    pass


@generate.command()
@click.argument("doc_type")
def doc(doc_type: str) -> None:
    """Generate a specific document type (NOT IMPLEMENTED)."""
    console.print(f"⚠️  Document generation for '{doc_type}' not yet implemented.", style="yellow")
    console.print("M004 Document Generator and M008 LLM Adapter are required.", style="dim")
    sys.exit(1)


@cli.group()
def analyze() -> None:
    """Code analysis commands (NOT IMPLEMENTED)."""
    pass


@analyze.command()
@click.argument("path", required=False, default=".")
def project(path: str) -> None:
    """Analyze project documentation (NOT IMPLEMENTED)."""
    console.print(f"⚠️  Project analysis for '{path}' not yet implemented.", style="yellow")
    console.print("M003 MIAIR Engine and M007 Review Engine are required.", style="dim")
    sys.exit(1)


def main() -> int:
    """Main entry point for the CLI."""
    try:
        cli()
        return 0
    except KeyboardInterrupt:
        console.print("\n⚠️  Operation cancelled by user", style="yellow")
        return 130
    except Exception as e:
        console.print(f"❌ Unexpected error: {e}", style="red")
        return 1


if __name__ == "__main__":
    sys.exit(main())
