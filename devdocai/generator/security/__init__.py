"""
M004 Document Generator - Security module initialization.

Exports key security components for easy access.
"""

from .security_monitor import SecurityMonitor, SecurityIncident, SecurityMetric
from .pii_protection import PIIProtectionEngine, PIIDetector, PIISensitivity, PIIAction, PIIPolicy, PIIFinding
from .access_control import AccessController, AccessLevel, ResourceType, Permission, AccessPolicy, ClientProfile

__all__ = [
    # Security Monitor
    'SecurityMonitor',
    'SecurityIncident', 
    'SecurityMetric',
    
    # PII Protection
    'PIIProtectionEngine',
    'PIIDetector',
    'PIISensitivity',
    'PIIAction', 
    'PIIPolicy',
    'PIIFinding',
    
    # Access Control
    'AccessController',
    'AccessLevel',
    'ResourceType',
    'Permission',
    'AccessPolicy', 
    'ClientProfile',
]