"""
DevDocAI CLI Commands Module.

Contains all command implementations for the CLI with unified mode-based behavior.
"""

# Import unified commands for mode-based operation
# NOTE: Now enabled since main.py has been updated to use unified modules
from . import generate_unified
from . import analyze_unified  
from . import config_unified
from . import template_unified
from . import enhance_unified
# Temporarily disabled due to pyahocorasick dependency issue
# from . import security_unified

# Legacy imports (for backward compatibility during transition)
try:
    from . import generate
    from . import analyze
    from . import config
    from . import template
    from . import enhance
    from . import security
except ImportError:
    # Legacy modules may not exist after cleanup
    pass

__all__ = [
    # Unified modules (primary)
    'generate_unified',
    'analyze_unified',
    'config_unified',
    'template_unified',
    'enhance_unified',
    'security_unified',
    # Legacy modules (if available)
    'generate',
    'analyze',
    'config',
    'template',
    'enhance',
    'security'
]