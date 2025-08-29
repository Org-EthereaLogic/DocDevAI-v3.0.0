"""
Unified logging module for DevDocAI.

Provides consistent logging configuration and utilities across all modules.
"""

import logging
import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from functools import wraps
import traceback


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_obj = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                          'levelname', 'levelno', 'lineno', 'module', 'msecs',
                          'pathname', 'process', 'processName', 'relativeCreated',
                          'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info']:
                log_obj[key] = value
        
        return json.dumps(log_obj)


class ColoredFormatter(logging.Formatter):
    """Colored console formatter for better readability."""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        
        # Format message
        message = super().format(record)
        
        # Reset level name
        record.levelname = levelname
        
        return message


def setup_logging(log_level: str = 'INFO',
                  log_file: Optional[Path] = None,
                  use_json: bool = False,
                  use_colors: bool = True) -> None:
    """
    Set up logging configuration.
    
    Args:
        log_level: Logging level
        log_file: Optional log file path
        use_json: Use JSON formatting
        use_colors: Use colored output for console
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    if use_json:
        console_formatter = JSONFormatter()
    elif use_colors and sys.stdout.isatty():
        console_formatter = ColoredFormatter(
            '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        
        if use_json:
            file_formatter = JSONFormatter()
        else:
            file_formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Get logger instance with consistent configuration."""
    return logging.getLogger(name)


def log_execution(level: str = 'DEBUG'):
    """
    Decorator to log function execution.
    
    Args:
        level: Log level to use
    """
    def decorator(func):
        logger = get_logger(func.__module__)
        log_func = getattr(logger, level.lower())
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Log entry
            log_func(f"Entering {func.__name__}")
            
            try:
                result = func(*args, **kwargs)
                
                # Log success
                log_func(f"Exiting {func.__name__} successfully")
                
                return result
                
            except Exception as e:
                # Log error
                logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
                raise
        
        return wrapper
    
    return decorator


def log_performance(func):
    """
    Decorator to log function performance.
    """
    import time
    
    logger = get_logger(func.__module__)
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        
        try:
            result = func(*args, **kwargs)
            duration = time.perf_counter() - start
            
            logger.debug(f"{func.__name__} completed in {duration:.4f}s")
            
            return result
            
        except Exception as e:
            duration = time.perf_counter() - start
            logger.error(f"{func.__name__} failed after {duration:.4f}s: {e}")
            raise
    
    return wrapper


class LogContext:
    """
    Context manager for adding context to logs.
    
    Usage:
        with LogContext(user='john', operation='data_processing'):
            # All logs in this context will have user and operation fields
            logger.info('Processing data')
    """
    
    def __init__(self, **kwargs):
        """Initialize log context."""
        self.context = kwargs
        self.old_factory = None
    
    def __enter__(self):
        """Enter context."""
        self.old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        logging.setLogRecordFactory(self.old_factory)


# Configure default logging
setup_logging()


__all__ = [
    'JSONFormatter',
    'ColoredFormatter',
    'setup_logging',
    'get_logger',
    'log_execution',
    'log_performance',
    'LogContext'
]