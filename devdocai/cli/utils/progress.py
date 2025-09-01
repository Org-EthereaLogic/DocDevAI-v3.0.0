"""
Progress tracking utilities for DevDocAI CLI.

Provides progress bars, spinners, and status indicators.
"""

import sys
import time
import threading
from typing import Optional, Iterator, Any, Callable
from contextlib import contextmanager

import click


class ProgressTracker:
    """Tracks progress for long-running operations."""
    
    def __init__(self, total: Optional[int] = None, description: str = '',
                 show_percent: bool = True, show_eta: bool = True):
        """
        Initialize progress tracker.
        
        Args:
            total: Total number of items (None for indeterminate)
            description: Description of operation
            show_percent: Show percentage complete
            show_eta: Show estimated time remaining
        """
        self.total = total
        self.description = description
        self.show_percent = show_percent
        self.show_eta = show_eta
        self.current = 0
        self.start_time = None
        self._bar = None
    
    def start(self):
        """Start progress tracking."""
        self.start_time = time.time()
        self.current = 0
        
        if self.total:
            self._bar = click.progressbar(
                length=self.total,
                label=self.description,
                show_percent=self.show_percent,
                show_eta=self.show_eta
            )
            self._bar.__enter__()
    
    def update(self, amount: int = 1):
        """Update progress by specified amount."""
        self.current += amount
        if self._bar:
            self._bar.update(amount)
    
    def finish(self):
        """Finish progress tracking."""
        if self._bar:
            self._bar.__exit__(None, None, None)
            self._bar = None
        
        if self.start_time:
            elapsed = time.time() - self.start_time
            click.echo(f" Done in {elapsed:.1f}s")
    
    def set_description(self, description: str):
        """Update progress description."""
        self.description = description
        if self._bar:
            self._bar.label = description


@contextmanager
def spinner(message: str = 'Processing...', spinner_type: str = 'dots'):
    """
    Show a spinner for indeterminate progress.
    
    Args:
        message: Message to display
        spinner_type: Type of spinner animation
        
    Example:
        with spinner('Loading data'):
            # Long running operation
            time.sleep(5)
    """
    spinners = {
        'dots': ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'],
        'line': ['-', '\\', '|', '/'],
        'arrow': ['←', '↖', '↑', '↗', '→', '↘', '↓', '↙'],
        'bar': ['▁', '▃', '▄', '▅', '▆', '▇', '█', '▇', '▆', '▅', '▄', '▃'],
        'bounce': ['⠁', '⠂', '⠄', '⡀', '⢀', '⠠', '⠐', '⠈']
    }
    
    frames = spinners.get(spinner_type, spinners['dots'])
    stop_spinner = threading.Event()
    
    def spin():
        idx = 0
        while not stop_spinner.is_set():
            frame = frames[idx % len(frames)]
            sys.stdout.write(f'\r{frame} {message}')
            sys.stdout.flush()
            idx += 1
            time.sleep(0.1)
        sys.stdout.write('\r' + ' ' * (len(message) + 3) + '\r')
        sys.stdout.flush()
    
    spinner_thread = threading.Thread(target=spin)
    spinner_thread.daemon = True
    spinner_thread.start()
    
    try:
        yield
    finally:
        stop_spinner.set()
        spinner_thread.join()
        click.echo(f"✓ {message}")


@contextmanager
def progress_bar(items: Iterator[Any], total: Optional[int] = None,
                 label: str = 'Processing', show_pos: bool = False):
    """
    Show a progress bar for iterating over items.
    
    Args:
        items: Items to iterate over
        total: Total number of items (auto-detected if possible)
        label: Label for progress bar
        show_pos: Show position counter
        
    Example:
        with progress_bar(files, label='Processing files') as bar:
            for file in bar:
                process_file(file)
    """
    # Try to get total if not provided
    if total is None:
        try:
            total = len(items)
        except TypeError:
            pass
    
    with click.progressbar(
        items,
        length=total,
        label=label,
        show_pos=show_pos,
        show_percent=True,
        show_eta=True
    ) as bar:
        yield bar


class MultiProgress:
    """Handle multiple progress bars simultaneously."""
    
    def __init__(self):
        """Initialize multi-progress manager."""
        self.bars = {}
        self.lock = threading.Lock()
    
    def add_bar(self, name: str, total: int, description: str = ''):
        """
        Add a new progress bar.
        
        Args:
            name: Unique name for the bar
            total: Total items for this bar
            description: Bar description
        """
        with self.lock:
            self.bars[name] = {
                'total': total,
                'current': 0,
                'description': description,
                'start_time': time.time()
            }
    
    def update(self, name: str, amount: int = 1):
        """
        Update a specific progress bar.
        
        Args:
            name: Bar name
            amount: Amount to increment
        """
        with self.lock:
            if name in self.bars:
                self.bars[name]['current'] += amount
                self._render()
    
    def finish(self, name: str):
        """
        Mark a progress bar as finished.
        
        Args:
            name: Bar name
        """
        with self.lock:
            if name in self.bars:
                self.bars[name]['current'] = self.bars[name]['total']
                self._render()
    
    def _render(self):
        """Render all progress bars."""
        # Clear previous output
        sys.stdout.write('\033[K' * len(self.bars))
        sys.stdout.write('\033[F' * len(self.bars))
        
        # Render each bar
        for name, bar in self.bars.items():
            percent = (bar['current'] / bar['total']) * 100 if bar['total'] > 0 else 0
            filled = int(percent / 2)
            bar_str = '█' * filled + '░' * (50 - filled)
            
            elapsed = time.time() - bar['start_time']
            if bar['current'] > 0 and bar['current'] < bar['total']:
                eta = (elapsed / bar['current']) * (bar['total'] - bar['current'])
                eta_str = f"ETA: {eta:.1f}s"
            else:
                eta_str = ""
            
            line = f"{bar['description']}: [{bar_str}] {percent:.1f}% {eta_str}"
            sys.stdout.write(line + '\n')
        
        sys.stdout.flush()


def show_status(message: str, status: str = 'info'):
    """
    Show a status message with appropriate icon.
    
    Args:
        message: Status message
        status: Status type (info, success, warning, error, working)
    """
    icons = {
        'info': 'ℹ',
        'success': '✓',
        'warning': '⚠',
        'error': '✗',
        'working': '⚙'
    }
    
    colors = {
        'info': 'blue',
        'success': 'green',
        'warning': 'yellow',
        'error': 'red',
        'working': 'cyan'
    }
    
    icon = icons.get(status, 'ℹ')
    color = colors.get(status, 'white')
    
    click.echo(click.style(f"{icon} {message}", fg=color))


def create_step_progress(steps: list) -> Callable:
    """
    Create a step-based progress tracker.
    
    Args:
        steps: List of step descriptions
        
    Returns:
        Function to update step progress
        
    Example:
        update_step = create_step_progress([
            'Loading data',
            'Processing',
            'Saving results'
        ])
        
        update_step(0)  # Start step 0
        # ... do work ...
        update_step(1)  # Start step 1
    """
    total_steps = len(steps)
    current_step = [0]
    
    def update(step: int, done: bool = False):
        """Update to specified step."""
        current_step[0] = step
        
        # Clear line
        sys.stdout.write('\r' + ' ' * 80 + '\r')
        
        # Build progress indicator
        if done:
            status = click.style('✓', fg='green')
            message = click.style('Complete', fg='green')
        else:
            status = f"[{step + 1}/{total_steps}]"
            message = steps[step]
        
        # Show progress
        progress = f"{status} {message}"
        
        # Add mini progress bar
        if not done:
            filled = int((step / total_steps) * 20)
            bar = '█' * filled + '░' * (20 - filled)
            progress += f" [{bar}]"
        
        sys.stdout.write(progress)
        sys.stdout.flush()
        
        if done:
            sys.stdout.write('\n')
    
    return update


def animated_message(message: str, animation_time: float = 2.0):
    """
    Show an animated message that fades in.
    
    Args:
        message: Message to display
        animation_time: Time for animation
    """
    steps = 10
    delay = animation_time / steps
    
    for i in range(steps + 1):
        opacity = i / steps
        # Simulate opacity with color brightness
        if opacity < 0.33:
            color = 'bright_black'
        elif opacity < 0.66:
            color = 'white'
        else:
            color = 'bright_white'
        
        sys.stdout.write('\r' + click.style(message, fg=color))
        sys.stdout.flush()
        time.sleep(delay)
    
    sys.stdout.write('\n')