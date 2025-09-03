"""
Security initialization module for DocDevAI.

This module initializes security features like secure logging
without causing circular imports.
"""

import logging
from typing import Optional


def initialize_secure_logging():
    """
    Initialize secure logging for the entire application.
    
    This function should be called early in the application startup
    to ensure all logs are properly masked for PII.
    """
    try:
        # Import here to avoid circular imports
        from devdocai.core.secure_logger import SecureLogger
        
        # Setup secure logging for the entire application
        SecureLogger.setup_secure_logging(root_logger=True)
        
        # Log initialization
        logger = logging.getLogger('devdocai.security')
        logger.info("Secure logging initialized successfully")
        
        return True
        
    except ImportError as e:
        # If secure_logger is not available, log warning but continue
        logger = logging.getLogger('devdocai.security')
        logger.warning(f"Could not initialize secure logging: {e}")
        return False
    except Exception as e:
        logger = logging.getLogger('devdocai.security')
        logger.error(f"Error initializing secure logging: {e}")
        return False


def setup_encryption(master_key: Optional[str] = None):
    """
    Setup encryption with optional master key.
    
    Args:
        master_key: Optional master key for encryption.
                   If not provided, will use DEVDOCAI_MASTER_KEY env var.
    """
    import os
    
    if master_key:
        os.environ['DEVDOCAI_MASTER_KEY'] = master_key
    
    # Verify master key is set
    if not os.environ.get('DEVDOCAI_MASTER_KEY'):
        logger = logging.getLogger('devdocai.security')
        logger.warning(
            "No master key set for encryption. "
            "Set DEVDOCAI_MASTER_KEY environment variable for secure encryption."
        )


def initialize_security(master_key: Optional[str] = None):
    """
    Initialize all security features.
    
    Args:
        master_key: Optional master key for encryption.
        
    Returns:
        dict: Status of each security feature initialization
    """
    results = {
        'secure_logging': False,
        'encryption': False
    }
    
    # Initialize secure logging
    results['secure_logging'] = initialize_secure_logging()
    
    # Setup encryption
    setup_encryption(master_key)
    results['encryption'] = True
    
    return results