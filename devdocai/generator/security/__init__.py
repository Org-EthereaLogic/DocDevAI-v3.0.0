"""
M004 Document Generator - Security module initialization.

Exports key security components for easy access.
Includes Pass 3 security hardening components.
"""

# Existing components
from .security_monitor import SecurityMonitor, SecurityIncident, SecurityMetric
from .pii_protection import PIIProtectionEngine, PIIDetector, PIISensitivity, PIIAction, PIIPolicy, PIIFinding
from .access_control import AccessController, AccessLevel, ResourceType, Permission, AccessPolicy, ClientProfile

# Pass 3 Security Hardening components
from .prompt_guard import (
    PromptGuard,
    SecurityException,
    ThreatLevel,
    InjectionDetection
)

from .rate_limiter import (
    GenerationRateLimiter,
    RateLimitConfig,
    RateLimitLevel,
    LimitType,
    UsageMetrics
)

from .data_protection import (
    DataProtectionManager,
    DataClassification,
    ComplianceMode,
    PIIMatch,
    ProtectedData
)

from .audit_logger import (
    SecurityAuditLogger,
    EventCategory,
    EventSeverity,
    SecurityEvent
)

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
    
    # Prompt Guard (Pass 3)
    'PromptGuard',
    'SecurityException',
    'ThreatLevel',
    'InjectionDetection',
    
    # Rate Limiting (Pass 3)
    'GenerationRateLimiter',
    'RateLimitConfig',
    'RateLimitLevel',
    'LimitType',
    'UsageMetrics',
    
    # Data Protection (Pass 3)
    'DataProtectionManager',
    'DataClassification',
    'ComplianceMode',
    'PIIMatch',
    'ProtectedData',
    
    # Audit Logging (Pass 3)
    'SecurityAuditLogger',
    'EventCategory',
    'EventSeverity',
    'SecurityEvent',
]