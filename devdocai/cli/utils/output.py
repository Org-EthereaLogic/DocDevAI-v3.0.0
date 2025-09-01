"""
Output formatting utilities for DevDocAI CLI.

Provides formatters for different output types (JSON, YAML, table, etc.).
"""

import json
import yaml
from typing import Any, Dict, List, Optional
from pathlib import Path

import click


class OutputFormatter:
    """Handles output formatting for different formats."""
    
    def __init__(self, format_type: str = 'text', colors: bool = True):
        """
        Initialize output formatter.
        
        Args:
            format_type: Output format (text, json, yaml, table)
            colors: Whether to use colors in output
        """
        self.format_type = format_type
        self.colors = colors
    
    def format(self, data: Any) -> str:
        """
        Format data according to specified format.
        
        Args:
            data: Data to format
            
        Returns:
            Formatted string
        """
        if self.format_type == 'json':
            return format_json(data)
        elif self.format_type == 'yaml':
            return format_yaml(data)
        elif self.format_type == 'table':
            return format_table(data)
        else:
            return self._format_text(data)
    
    def _format_text(self, data: Any) -> str:
        """Format data as human-readable text."""
        if isinstance(data, dict):
            lines = []
            for key, value in data.items():
                if isinstance(value, (list, dict)):
                    lines.append(f"{key}:")
                    sub_formatted = self._format_text(value)
                    for line in sub_formatted.split('\n'):
                        lines.append(f"  {line}")
                else:
                    lines.append(f"{key}: {value}")
            return '\n'.join(lines)
        elif isinstance(data, list):
            lines = []
            for item in data:
                if isinstance(item, (dict, list)):
                    sub_formatted = self._format_text(item)
                    lines.append(f"- {sub_formatted.split(chr(10))[0]}")
                    for line in sub_formatted.split('\n')[1:]:
                        lines.append(f"  {line}")
                else:
                    lines.append(f"- {item}")
            return '\n'.join(lines)
        else:
            return str(data)
    
    def success(self, message: str):
        """Output success message."""
        if self.colors:
            click.echo(click.style(f"✓ {message}", fg='green'))
        else:
            click.echo(f"✓ {message}")
    
    def error(self, message: str):
        """Output error message."""
        if self.colors:
            click.echo(click.style(f"✗ {message}", fg='red'), err=True)
        else:
            click.echo(f"✗ {message}", err=True)
    
    def warning(self, message: str):
        """Output warning message."""
        if self.colors:
            click.echo(click.style(f"⚠ {message}", fg='yellow'))
        else:
            click.echo(f"⚠ {message}")
    
    def info(self, message: str):
        """Output info message."""
        click.echo(f"ℹ {message}")
    
    def debug(self, message: str):
        """Output debug message."""
        if self.colors:
            click.echo(click.style(f"[DEBUG] {message}", fg='cyan'))
        else:
            click.echo(f"[DEBUG] {message}")


def format_json(data: Any, indent: int = 2) -> str:
    """
    Format data as JSON.
    
    Args:
        data: Data to format
        indent: Indentation level
        
    Returns:
        JSON formatted string
    """
    return json.dumps(data, indent=indent, default=str, ensure_ascii=False)


def format_yaml(data: Any) -> str:
    """
    Format data as YAML.
    
    Args:
        data: Data to format
        
    Returns:
        YAML formatted string
    """
    return yaml.dump(data, default_flow_style=False, allow_unicode=True)


def format_table(data: Any, headers: Optional[List[str]] = None) -> str:
    """
    Format data as a table.
    
    Args:
        data: Data to format (list of dicts or list of lists)
        headers: Optional header row
        
    Returns:
        Table formatted string
    """
    if not data:
        return "No data to display"
    
    # Handle list of dicts
    if isinstance(data, list) and isinstance(data[0], dict):
        if not headers:
            headers = list(data[0].keys())
        
        # Calculate column widths
        widths = {h: len(str(h)) for h in headers}
        for row in data:
            for header in headers:
                value = str(row.get(header, ''))
                widths[header] = max(widths[header], len(value))
        
        # Build table
        lines = []
        
        # Header row
        header_row = ' | '.join(str(h).ljust(widths[h]) for h in headers)
        lines.append(header_row)
        lines.append('-' * len(header_row))
        
        # Data rows
        for row in data:
            row_str = ' | '.join(
                str(row.get(h, '')).ljust(widths[h]) for h in headers
            )
            lines.append(row_str)
        
        return '\n'.join(lines)
    
    # Handle list of lists
    elif isinstance(data, list) and isinstance(data[0], list):
        if headers:
            data = [headers] + data
        
        # Calculate column widths
        widths = []
        for col_idx in range(len(data[0])):
            max_width = max(len(str(row[col_idx])) for row in data)
            widths.append(max_width)
        
        # Build table
        lines = []
        for idx, row in enumerate(data):
            row_str = ' | '.join(
                str(cell).ljust(widths[i]) for i, cell in enumerate(row)
            )
            lines.append(row_str)
            
            # Add separator after header
            if idx == 0 and headers:
                lines.append('-' * len(row_str))
        
        return '\n'.join(lines)
    
    # Fallback to text format
    formatter = OutputFormatter('text')
    return formatter.format(data)


def print_tree(data: Dict, indent: int = 0, prefix: str = ''):
    """
    Print data as a tree structure.
    
    Args:
        data: Dictionary data to print as tree
        indent: Current indentation level
        prefix: Prefix for tree branches
    """
    items = list(data.items())
    for idx, (key, value) in enumerate(items):
        is_last = idx == len(items) - 1
        
        # Print current node
        connector = '└── ' if is_last else '├── '
        click.echo(f"{prefix}{connector}{key}")
        
        # Recursively print children
        if isinstance(value, dict):
            extension = '    ' if is_last else '│   '
            print_tree(value, indent + 1, prefix + extension)
        elif isinstance(value, list) and value:
            extension = '    ' if is_last else '│   '
            for item_idx, item in enumerate(value):
                is_last_item = item_idx == len(value) - 1
                item_connector = '└── ' if is_last_item else '├── '
                
                if isinstance(item, dict):
                    # Show first key-value pair as preview
                    preview = next(iter(item.items())) if item else ('', '')
                    click.echo(f"{prefix}{extension}{item_connector}{preview[0]}: {preview[1]}")
                else:
                    click.echo(f"{prefix}{extension}{item_connector}{item}")


def highlight_code(code: str, language: str = 'python') -> str:
    """
    Highlight code with syntax coloring.
    
    Args:
        code: Code to highlight
        language: Programming language
        
    Returns:
        Highlighted code string
    """
    try:
        from pygments import highlight
        from pygments.lexers import get_lexer_by_name
        from pygments.formatters import TerminalFormatter
        
        lexer = get_lexer_by_name(language, stripall=True)
        formatter = TerminalFormatter()
        return highlight(code, lexer, formatter)
    except ImportError:
        # Pygments not available, return plain code
        return code


def format_diff(old: str, new: str, context: int = 3) -> str:
    """
    Format a diff between two strings.
    
    Args:
        old: Original content
        new: New content
        context: Number of context lines
        
    Returns:
        Formatted diff string
    """
    import difflib
    
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile='original',
        tofile='enhanced',
        n=context
    )
    
    # Colorize diff
    colored_lines = []
    for line in diff:
        if line.startswith('+'):
            colored_lines.append(click.style(line, fg='green'))
        elif line.startswith('-'):
            colored_lines.append(click.style(line, fg='red'))
        elif line.startswith('@'):
            colored_lines.append(click.style(line, fg='cyan'))
        else:
            colored_lines.append(line)
    
    return ''.join(colored_lines)


def format_size(size: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size: Size in bytes
        
    Returns:
        Formatted size string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}h {minutes}m"