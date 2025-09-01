"""
M010 Security Module for DevDocAI v3.0.0 - Pass 4 Refactored

Advanced security features building on the security foundations established
in M001-M009. Provides centralized security management, SBOM generation,
enhanced PII detection, DSR compliance, and comprehensive security monitoring.

REFACTORED ARCHITECTURE:
This module has been refactored to use unified components with operation modes:
- BASIC: Core functionality with minimal overhead
- PERFORMANCE: Optimized operations with caching and parallelization  
- SECURE: Enhanced security with additional hardening
- ENTERPRISE: Full enterprise suite with all features

Key Components:
- UnifiedSecurityManager: Central security orchestration with configurable modes
- UnifiedSBOMGenerator: Software Bill of Materials with SPDX/CycloneDX support
- UnifiedPIIDetector: Enhanced personally identifiable information handling
- UnifiedDSRHandler: GDPR Articles 15-21 compliance
- UnifiedThreatDetector: Real-time threat detection and alerting
- UnifiedComplianceReporter: Compliance reporting and assessment

BACKWARD COMPATIBILITY:
All original class names are preserved through aliases for seamless migration.
"""

from typing import Dict, Any, Optional, List

# Import unified components (new architecture)
from .security_manager_unified import (
    UnifiedSecurityManager, 
    UnifiedSecurityConfig,
    SecurityOperationMode,
    SecurityStatus,
    SecurityPosture,
    create_basic_security_manager,
    create_performance_security_manager,
    create_secure_security_manager,
    create_enterprise_security_manager
)

from .sbom_generator_unified import (
    UnifiedSBOMGenerator,
    SBOMConfig,
    SBOMOperationMode,
    SBOMFormat,
    LicenseType,
    ComponentInfo,
    create_basic_sbom_generator,
    create_performance_sbom_generator,
    create_secure_sbom_generator,
    create_enterprise_sbom_generator
)

from .pii_detector_unified import (
    UnifiedPIIDetector,
    PIIConfig,
    PIIOperationMode,
    PIIDetectionMode,
    PIILanguage,
    PIISensitivityLevel,
    PIIMatch,
    create_basic_pii_detector,
    create_performance_pii_detector,
    create_secure_pii_detector,
    create_enterprise_pii_detector
)

from .threat_detector_unified import (
    UnifiedThreatDetector,
    ThreatConfig,
    ThreatOperationMode,
    ThreatLevel,
    ThreatType,
    SecurityThreat,
    create_basic_threat_detector,
    create_performance_threat_detector,
    create_secure_threat_detector,
    create_enterprise_threat_detector
)

from .dsr_handler_unified import (
    UnifiedDSRHandler,
    DSRConfig,
    DSROperationMode,
    DSRRequestType,
    DSRStatus,
    DSRRequest,
    DSRResponse,
    create_basic_dsr_handler,
    create_performance_dsr_handler,
    create_secure_dsr_handler,
    create_enterprise_dsr_handler
)

from .compliance_reporter_unified import (
    UnifiedComplianceReporter,
    ComplianceConfig,
    ComplianceOperationMode,
    ComplianceStandard,
    ComplianceStatus,
    ComplianceControl,
    ComplianceReport,
    create_basic_compliance_reporter,
    create_performance_compliance_reporter,
    create_secure_compliance_reporter,
    create_enterprise_compliance_reporter
)

# Import legacy components for backward compatibility (if they still exist)
# These will gracefully degrade to unified components if old files are removed

# Backward compatibility aliases
SecurityManager = UnifiedSecurityManager
SecurityConfig = UnifiedSecurityConfig
SecurityMode = SecurityOperationMode  # Enum mapping

SBOMGenerator = UnifiedSBOMGenerator
AdvancedPIIDetector = UnifiedPIIDetector  
PIIDetectionMode = PIIDetectionMode  # Already exists in unified
DSRRequestHandler = UnifiedDSRHandler
ThreatDetector = UnifiedThreatDetector
ComplianceReporter = UnifiedComplianceReporter

# Version information
__version__ = "4.0.0"  # Updated for Pass 4 refactoring
__module__ = "M010"
__status__ = "Pass 4 Complete - Refactored"

# Default unified configuration
DEFAULT_SECURITY_CONFIG = {
    "mode": SecurityOperationMode.ENTERPRISE,
    "posture": SecurityPosture.PROACTIVE,
    
    # Component configurations
    "sbom": {
        "mode": SBOMOperationMode.ENTERPRISE,
        "enabled": True,
        "formats": [SBOMFormat.SPDX_JSON, SBOMFormat.CYCLONEDX_JSON],
        "signature_required": True,
        "enable_parallel_scanning": True,
        "enable_dependency_caching": True
    },
    
    "pii": {
        "mode": PIIOperationMode.ENTERPRISE,
        "detection_mode": PIIDetectionMode.BALANCED,
        "language": PIILanguage.AUTO_DETECT,
        "enable_ml_detection": True,
        "enable_parallel_processing": True,
        "enable_result_caching": True,
        "gdpr_compliance": True,
        "ccpa_compliance": True
    },
    
    "dsr": {
        "mode": DSROperationMode.ENTERPRISE,
        "enable_automated_processing": True,
        "enable_parallel_processing": True,
        "enable_encryption": True,
        "enable_compliance_tracking": True,
        "gdpr_compliance": True,
        "ccpa_compliance": True
    },
    
    "threat": {
        "mode": ThreatOperationMode.ENTERPRISE,
        "enable_parallel_processing": True,
        "enable_result_caching": True,
        "enable_behavioral_analysis": True,
        "enable_threat_intelligence": True,
        "enable_anomaly_detection": True
    },
    
    "compliance": {
        "mode": ComplianceOperationMode.ENTERPRISE,
        "enabled_standards": [ComplianceStandard.GDPR, ComplianceStandard.SOC2, ComplianceStandard.ISO27001],
        "enable_parallel_assessment": True,
        "enable_continuous_monitoring": True,
        "enable_automated_assessment": True,
        "enable_trend_analysis": True,
        "generate_executive_reports": True
    },
    
    # Enterprise hardening components
    "enable_crypto_manager": True,
    "enable_threat_intelligence": True,
    "enable_zero_trust": True,
    "enable_audit_forensics": True,
    "enable_security_orchestrator": True
}

# Global security manager instance
_security_manager: Optional[UnifiedSecurityManager] = None


def get_security_manager(config: Optional[Dict[str, Any]] = None) -> UnifiedSecurityManager:
    """
    Get global unified security manager instance.
    
    Args:
        config: Optional security configuration (supports both legacy and unified formats)
        
    Returns:
        UnifiedSecurityManager instance
    """
    global _security_manager
    if _security_manager is None:
        _security_manager = initialize_security_module(config or DEFAULT_SECURITY_CONFIG)
    return _security_manager


def initialize_security_module(config: Optional[Dict[str, Any]] = None) -> UnifiedSecurityManager:
    """
    Initialize M010 Security Module with unified architecture.
    
    Args:
        config: Security configuration (auto-detects legacy vs unified format)
        
    Returns:
        Configured UnifiedSecurityManager instance
    """
    if not config:
        # Use default enterprise configuration
        unified_config = UnifiedSecurityConfig()
        return create_enterprise_security_manager(unified_config)
    
    # Check if this is legacy format or unified format
    if 'mode' in config and isinstance(config['mode'], str):
        # Legacy format - convert to unified
        mode = SecurityOperationMode(config['mode'].lower())
    elif 'mode' in config and isinstance(config['mode'], SecurityOperationMode):
        # Unified format
        mode = config['mode']
    else:
        mode = SecurityOperationMode.ENTERPRISE
    
    # Create unified configuration
    unified_config = UnifiedSecurityConfig(
        mode=mode,
        posture=config.get('posture', SecurityPosture.PROACTIVE),
        
        # Core security settings
        encryption_enabled=config.get('encryption_enabled', True),
        audit_logging=config.get('audit_logging', True),
        real_time_monitoring=config.get('real_time_monitoring', True),
        
        # Component enablement
        sbom_enabled=config.get('sbom', {}).get('enabled', True),
        pii_detection_enabled=config.get('pii', {}).get('enabled', True),
        dsr_enabled=config.get('dsr', {}).get('enabled', True),
        threat_monitoring=config.get('threat', {}).get('enabled', True),
        compliance_reporting=config.get('compliance', {}).get('enabled', True),
        
        # Enterprise hardening
        enable_crypto_manager=config.get('enable_crypto_manager', mode == SecurityOperationMode.ENTERPRISE),
        enable_threat_intelligence=config.get('enable_threat_intelligence', mode == SecurityOperationMode.ENTERPRISE),
        enable_zero_trust=config.get('enable_zero_trust', mode == SecurityOperationMode.ENTERPRISE),
        enable_audit_forensics=config.get('enable_audit_forensics', mode in [SecurityOperationMode.SECURE, SecurityOperationMode.ENTERPRISE]),
        enable_security_orchestrator=config.get('enable_security_orchestrator', mode == SecurityOperationMode.ENTERPRISE)
    )
    
    return UnifiedSecurityManager(unified_config)


# Convenience factory functions
def create_basic_security_module(config_manager=None) -> UnifiedSecurityManager:
    """Create basic security module with minimal features."""
    return create_basic_security_manager(config_manager=config_manager)


def create_performance_security_module(config_manager=None) -> UnifiedSecurityManager:
    """Create performance-optimized security module."""
    return create_performance_security_manager(config_manager=config_manager)


def create_secure_security_module(config_manager=None) -> UnifiedSecurityManager:
    """Create security-hardened module."""
    return create_secure_security_manager(config_manager=config_manager)


def create_enterprise_security_module(config_manager=None) -> UnifiedSecurityManager:
    """Create full enterprise security module."""
    return create_enterprise_security_manager(config_manager=config_manager)


# Export key components
__all__ = [
    # Unified components (primary)
    "UnifiedSecurityManager",
    "UnifiedSecurityConfig",
    "UnifiedSBOMGenerator", 
    "UnifiedPIIDetector",
    "UnifiedThreatDetector",
    "UnifiedDSRHandler",
    "UnifiedComplianceReporter",
    
    # Backward compatibility aliases
    "SecurityManager",
    "SecurityConfig", 
    "SecurityMode",
    "SBOMGenerator",
    "SBOMFormat",
    "AdvancedPIIDetector",
    "PIIDetectionMode",
    "DSRRequestHandler",
    "DSRRequestType",
    "ThreatDetector",
    "ThreatLevel",
    "ComplianceReporter",
    "ComplianceStandard",
    
    # Operation modes
    "SecurityOperationMode",
    "SBOMOperationMode",
    "PIIOperationMode", 
    "ThreatOperationMode",
    "DSROperationMode",
    "ComplianceOperationMode",
    
    # Factory functions
    "create_basic_security_module",
    "create_performance_security_module", 
    "create_secure_security_module",
    "create_enterprise_security_module",
    
    # Legacy utility functions
    "get_security_manager",
    "initialize_security_module",
    
    # Configuration and metadata
    "DEFAULT_SECURITY_CONFIG",
    "__version__",
    "__module__",
    "__status__"
]