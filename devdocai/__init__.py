"""
DevDocAI v3.0.0 - AI-powered documentation generation and analysis system

A privacy-first, offline-capable documentation platform designed for solo developers.
"""

__version__ = "3.0.0"
__author__ = "DevDocAI Team"
__license__ = "Apache-2.0"

# Version information
VERSION_INFO = {
    "major": 3,
    "minor": 0,
    "patch": 0,
    "stage": "alpha",  # alpha, beta, rc, stable
    "build": None,
}


def get_version() -> str:
    """Get the full version string including stage."""
    version = f"{VERSION_INFO['major']}.{VERSION_INFO['minor']}.{VERSION_INFO['patch']}"
    if VERSION_INFO["stage"] != "stable":
        version = f"{version}-{VERSION_INFO['stage']}"
    if VERSION_INFO["build"]:
        version = f"{version}+{VERSION_INFO['build']}"
    return version


# Module availability flags
FEATURES = {
    "encryption": True,  # AES-256-GCM encryption available
    "local_ai": False,  # Will be True when AI modules installed
    "compliance": False,  # Will be True when compliance modules installed
}

# Memory mode detection (will be set by ConfigurationManager)
MEMORY_MODE = None

__all__ = ["__version__", "get_version", "FEATURES", "MEMORY_MODE"]