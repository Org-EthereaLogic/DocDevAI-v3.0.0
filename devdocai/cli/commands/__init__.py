"""
DevDocAI CLI Commands Module.

Contains all command implementations for the CLI with unified mode-based behavior.
"""

# Import unified commands for mode-based operation
# NOTE: Commented out unified imports as they are not used by main.py
# and were causing import errors
# from . import generate_unified
# from . import analyze_unified
# from . import config_unified
# from . import template_unified
# from . import enhance_unified
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