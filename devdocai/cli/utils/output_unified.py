"""
Unified Output Utilities - Mode-based output formatting and display.

Consolidates base and optimized output utilities with configurable behavior.
"""

import json
import sys
from typing import Any, Dict, List, Optional
from functools import lru_cache

import click
import yaml
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn

from devdocai.cli.config_unified import get_config


class UnifiedOutputFormatter:
    """Unified output formatter with mode-based behavior."""
    
    def __init__(self):
        """Initialize formatter."""
        self.config = get_config()
        self.console = Console() if self.config.enable_colors else None
        
        # Performance optimizations
        if self.config.is_performance_enabled():
            self._init_performance_features()
    
    def _init_performance_features(self):
        """Initialize performance features."""
        # Cache formatted outputs
        self._format_cache = lru_cache(maxsize=128)(self._format_impl)
        # Pre-compile format templates
        self._templates = {
            'json': json.dumps,
            'yaml': yaml.dump
        }
    
    def format(self, data: Any, format_type: str = 'text') -> str:
        """Format data for output."""
        if self.config.is_performance_enabled() and hasattr(self, '_format_cache'):
            # Use cached formatting for immutable data
            if isinstance(data, (str, int, float, tuple)):
                return self._format_cache(data, format_type)
        
        return self._format_impl(data, format_type)
    
    def _format_impl(self, data: Any, format_type: str) -> str:
        """Core formatting implementation."""
        if format_type == 'json':
            return json.dumps(data, indent=2, default=str)
        elif format_type == 'yaml':
            return yaml.dump(data, default_flow_style=False)
        elif format_type == 'table' and isinstance(data, (list, dict)):
            return self._format_table(data)
        else:
            return str(data)
    
    def _format_table(self, data: Any) -> str:
        """Format data as a table."""
        if not self.console:
            # Fallback to simple formatting
            return self._simple_table(data)
        
        table = Table(show_header=True, header_style="bold cyan")
        
        if isinstance(data, dict):
            table.add_column("Key", style="green")
            table.add_column("Value")
            for key, value in data.items():
                table.add_row(str(key), str(value))
        
        elif isinstance(data, list) and data:
            if isinstance(data[0], dict):
                # List of dicts
                columns = list(data[0].keys())
                for col in columns:
                    table.add_column(col.title())
                for row in data:
                    table.add_row(*[str(row.get(col, '')) for col in columns])
            else:
                # Simple list
                table.add_column("Item")
                for item in data:
                    table.add_row(str(item))
        
        # Return rendered table
        from io import StringIO
        string_io = StringIO()
        temp_console = Console(file=string_io, force_terminal=True)
        temp_console.print(table)
        return string_io.getvalue()
    
    def _simple_table(self, data: Any) -> str:
        """Simple table formatting without rich."""
        lines = []
        
        if isinstance(data, dict):
            max_key_len = max(len(str(k)) for k in data.keys()) if data else 0
            for key, value in data.items():
                lines.append(f"{str(key).ljust(max_key_len)} : {value}")
        
        elif isinstance(data, list):
            for i, item in enumerate(data, 1):
                lines.append(f"{i}. {item}")
        
        return '\n'.join(lines)
    
    def print_success(self, message: str):
        """Print success message."""
        if self.console and self.config.enable_colors:
            self.console.print(f"✓ {message}", style="green")
        else:
            click.echo(f"✓ {message}")
    
    def print_error(self, message: str):
        """Print error message."""
        if self.console and self.config.enable_colors:
            self.console.print(f"✗ {message}", style="red", stderr=True)
        else:
            click.echo(f"✗ {message}", err=True)
    
    def print_warning(self, message: str):
        """Print warning message."""
        if self.console and self.config.enable_colors:
            self.console.print(f"⚠ {message}", style="yellow")
        else:
            click.echo(f"⚠ {message}")
    
    def print_info(self, message: str):
        """Print info message."""
        click.echo(message)
    
    def print_code(self, code: str, language: str = 'python'):
        """Print syntax-highlighted code."""
        if self.console and self.config.enable_colors:
            syntax = Syntax(code, language, theme="monokai", line_numbers=True)
            self.console.print(syntax)
        else:
            click.echo(code)


class UnifiedProgressBar:
    """Unified progress bar with mode-based behavior."""
    
    def __init__(self, total: Optional[int] = None, description: str = "Processing"):
        """Initialize progress bar."""
        self.config = get_config()
        self.total = total
        self.description = description
        self.current = 0
        
        if self.config.enable_progress_bars and self.config.enable_colors:
            self._init_rich_progress()
        else:
            self._progress = None
    
    def _init_rich_progress(self):
        """Initialize rich progress bar."""
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=Console()
        )
        self._task = self._progress.add_task(self.description, total=self.total)
    
    def __enter__(self):
        """Enter context manager."""
        if self._progress:
            self._progress.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        if self._progress:
            self._progress.stop()
    
    def update(self, advance: int = 1):
        """Update progress."""
        self.current += advance
        
        if self._progress:
            self._progress.update(self._task, advance=advance)
        elif not self.config.quiet:
            # Simple progress indicator
            if self.total:
                pct = (self.current / self.total) * 100
                click.echo(f"\r{self.description}: {pct:.0f}%", nl=False)
            else:
                click.echo(".", nl=False)
    
    def set_description(self, description: str):
        """Update progress description."""
        self.description = description
        if self._progress:
            self._progress.update(self._task, description=description)


# Global formatter instance
_formatter: Optional[UnifiedOutputFormatter] = None


def get_formatter() -> UnifiedOutputFormatter:
    """Get global output formatter."""
    global _formatter
    if _formatter is None:
        _formatter = UnifiedOutputFormatter()
    return _formatter


def format_output(data: Any, format_type: str = 'text') -> str:
    """Format data for output."""
    return get_formatter().format(data, format_type)


def print_success(message: str):
    """Print success message."""
    get_formatter().print_success(message)


def print_error(message: str):
    """Print error message."""
    get_formatter().print_error(message)


def print_warning(message: str):
    """Print warning message."""
    get_formatter().print_warning(message)


def print_info(message: str):
    """Print info message."""
    get_formatter().print_info(message)


def print_code(code: str, language: str = 'python'):
    """Print syntax-highlighted code."""
    get_formatter().print_code(code, language)


def create_progress(total: Optional[int] = None, description: str = "Processing") -> UnifiedProgressBar:
    """Create a progress bar."""
    return UnifiedProgressBar(total, description)