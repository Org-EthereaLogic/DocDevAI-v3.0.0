"""
M010 Security Module for DevDocAI v3.0.0

Advanced security features building on the security foundations established
in M001-M009. Provides centralized security management, SBOM generation,
enhanced PII detection, DSR compliance, and comprehensive security monitoring.

Key Components:
- SecurityManager: Central security orchestration
- SBOM Generator: Software Bill of Materials with SPDX/CycloneDX support
- Advanced PII Detection: Enhanced personally identifiable information handling
- DSR Handler: GDPR Articles 15-21 compliance
- Security Monitoring: Real-time threat detection and alerting
- Security Audit: Compliance reporting and assessment
"""

from typing import Dict, Any, Optional, List

from .security_manager import SecurityManager, SecurityConfig, SecurityMode
from .sbom.generator import SBOMGenerator, SBOMFormat
from .pii.detector_advanced import AdvancedPIIDetector, PIIDetectionMode
from .dsr.request_handler import DSRRequestHandler, DSRRequestType
from .monitoring.threat_detector import ThreatDetector, ThreatLevel
from .audit.compliance_reporter import ComplianceReporter, ComplianceStandard

# Version information
__version__ = "1.0.0"
__module__ = "M010"
__status__ = "Implementation Pass 1"

# Default configuration
DEFAULT_SECURITY_CONFIG = {
    "mode": "ENTERPRISE",
    "sbom": {
        "enabled": True,
        "formats": ["spdx-json", "cyclonedx-json"],
        "signature_required": True,
        "performance_target": 100.0  # ms
    },
    "pii": {
        "detection_mode": "ADVANCED", 
        "accuracy_target": 0.98,  # 98% accuracy target
        "languages": ["en", "es", "fr", "de"],
        "real_time_masking": True
    },
    "dsr": {
        "enabled": True,
        "supported_rights": ["access", "rectification", "erasure", "portability"],
        "response_time_hours": 72,
        "secure_deletion": True
    },
    "monitoring": {
        "threat_detection": True,
        "real_time_alerts": True,
        "alert_threshold": "MEDIUM",
        "dashboard_enabled": True
    },
    "audit": {
        "compliance_standards": ["GDPR", "OWASP", "SOC2"],
        "automated_reporting": True,
        "report_frequency": "daily",
        "retention_days": 365
    }
}

# Global security manager instance
_security_manager: Optional[SecurityManager] = None


def get_security_manager(config: Optional[Dict[str, Any]] = None) -> SecurityManager:
    """
    Get global security manager instance.
    
    Args:
        config: Optional security configuration
        
    Returns:
        SecurityManager instance
    """
    global _security_manager
    if _security_manager is None:
        _security_manager = SecurityManager(config or DEFAULT_SECURITY_CONFIG)
    return _security_manager


def initialize_security_module(config: Optional[Dict[str, Any]] = None) -> SecurityManager:
    """
    Initialize M010 Security Module.
    
    Args:
        config: Security configuration
        
    Returns:
        Configured SecurityManager instance
    """
    # Create security manager configuration from flat config
    if config:
        # Extract SecurityConfig parameters from nested config
        security_config = SecurityConfig(
            mode=SecurityMode(config.get('mode', 'ENTERPRISE')),
            sbom_enabled=config.get('sbom', {}).get('enabled', True),
            pii_detection_enabled=config.get('pii', {}).get('enabled', True),
            dsr_enabled=config.get('dsr', {}).get('enabled', True),
            threat_monitoring=config.get('monitoring', {}).get('enabled', True),
            compliance_reporting=config.get('audit', {}).get('enabled', True)
        )
    else:
        security_config = SecurityConfig()
    
    return SecurityManager(security_config)


# Export key components
__all__ = [
    # Core manager
    "SecurityManager",
    "SecurityConfig", 
    "SecurityMode",
    
    # SBOM components
    "SBOMGenerator",
    "SBOMFormat",
    
    # PII components
    "AdvancedPIIDetector",
    "PIIDetectionMode",
    
    # DSR components
    "DSRRequestHandler",
    "DSRRequestType",
    
    # Monitoring components
    "ThreatDetector",
    "ThreatLevel",
    
    # Audit components
    "ComplianceReporter",
    "ComplianceStandard",
    
    # Utility functions
    "get_security_manager",
    "initialize_security_module",
    
    # Configuration
    "DEFAULT_SECURITY_CONFIG",
    "__version__",
    "__module__",
    "__status__"
]