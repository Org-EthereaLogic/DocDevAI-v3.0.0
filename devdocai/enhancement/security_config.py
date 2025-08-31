"""
M009: Security Configuration Management System.

Centralized security policy management with environment-specific settings,
runtime validation, secure defaults, and compliance mode configurations.
"""

import os
import json
import yaml
import logging
from typing import Dict, List, Optional, Any, Union, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from datetime import datetime, timedelta

# Import security modules for configuration
from .security_validator import ValidationConfig, ValidationType, ThreatLevel
from .rate_limiter import RateLimitConfig, RateLimitLevel
from .secure_cache import CacheConfig, CacheLevel
from .audit_logger import AuditConfig, EventSeverity
from .resource_guard import ResourceLimits, ProtectionLevel

logger = logging.getLogger(__name__)


class SecurityMode(Enum):
    """Security operation modes."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"
    COMPLIANCE = "compliance"


class ComplianceStandard(Enum):
    """Supported compliance standards."""
    GDPR = "gdpr"
    CCPA = "ccpa"
    SOC2 = "soc2"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    OWASP_TOP10 = "owasp_top10"


@dataclass
class SecurityProfile:
    """Security configuration profile."""
    
    name: str
    description: str
    security_mode: SecurityMode
    compliance_standards: List[ComplianceStandard] = field(default_factory=list)
    
    # Component configurations
    validation_config: ValidationConfig = field(default_factory=ValidationConfig)
    rate_limit_config: RateLimitConfig = field(default_factory=RateLimitConfig)
    cache_config: CacheConfig = field(default_factory=CacheConfig)
    audit_config: AuditConfig = field(default_factory=AuditConfig)
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)
    
    # Global security settings
    encryption_required: bool = True
    pii_protection_required: bool = True
    audit_logging_required: bool = True
    rate_limiting_enabled: bool = True
    resource_monitoring_enabled: bool = True
    
    # Feature toggles
    enable_debug_mode: bool = False
    enable_telemetry: bool = False
    allow_external_requests: bool = True
    enforce_https: bool = True
    
    # Network security
    trusted_domains: Set[str] = field(default_factory=set)
    blocked_domains: Set[str] = field(default_factory=set)
    allowed_ip_ranges: List[str] = field(default_factory=list)
    blocked_ip_ranges: List[str] = field(default_factory=list)
    
    # Data handling
    data_retention_days: int = 365
    automatic_pii_masking: bool = True
    secure_deletion_required: bool = False
    
    # Monitoring and alerting
    security_monitoring_enabled: bool = True
    real_time_alerts: bool = True
    anomaly_detection_enabled: bool = False
    
    # Environment overrides
    environment_overrides: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create_development_profile(cls) -> 'SecurityProfile':
        """Create development security profile."""
        return cls(
            name="development",
            description="Development environment with relaxed security for debugging",
            security_mode=SecurityMode.DEVELOPMENT,
            validation_config=ValidationConfig.for_security_level("BASIC"),
            rate_limit_config=RateLimitConfig.for_security_mode("BASIC"),
            cache_config=CacheConfig.for_security_level("BASIC"),
            audit_config=AuditConfig.for_security_level("BASIC"),
            resource_limits=ResourceLimits.for_protection_level("BASIC"),
            encryption_required=False,
            pii_protection_required=False,
            audit_logging_required=False,
            enable_debug_mode=True,
            enable_telemetry=True,
            allow_external_requests=True,
            enforce_https=False,
            security_monitoring_enabled=False,
            real_time_alerts=False
        )
    
    @classmethod
    def create_production_profile(cls) -> 'SecurityProfile':
        """Create production security profile."""
        return cls(
            name="production",
            description="Production environment with maximum security",
            security_mode=SecurityMode.PRODUCTION,
            compliance_standards=[
                ComplianceStandard.GDPR,
                ComplianceStandard.SOC2,
                ComplianceStandard.OWASP_TOP10
            ],
            validation_config=ValidationConfig.for_security_level("STRICT"),
            rate_limit_config=RateLimitConfig.for_security_mode("STRICT"),
            cache_config=CacheConfig.for_security_level("STRICT"),
            audit_config=AuditConfig.for_security_level("STRICT"),
            resource_limits=ResourceLimits.for_protection_level("STRICT"),
            encryption_required=True,
            pii_protection_required=True,
            audit_logging_required=True,
            rate_limiting_enabled=True,
            resource_monitoring_enabled=True,
            enable_debug_mode=False,
            enable_telemetry=False,
            allow_external_requests=False,
            enforce_https=True,
            data_retention_days=730,  # 2 years for compliance
            automatic_pii_masking=True,
            secure_deletion_required=True,
            security_monitoring_enabled=True,
            real_time_alerts=True,
            anomaly_detection_enabled=True
        )
    
    @classmethod
    def create_compliance_profile(cls, standards: List[ComplianceStandard]) -> 'SecurityProfile':
        """Create compliance-specific security profile."""
        # Base strict configuration
        profile = cls.create_production_profile()
        profile.name = "compliance"
        profile.description = f"Compliance profile for {', '.join([s.value for s in standards])}"
        profile.security_mode = SecurityMode.COMPLIANCE
        profile.compliance_standards = standards
        
        # GDPR specific settings
        if ComplianceStandard.GDPR in standards:
            profile.validation_config = ValidationConfig.for_security_level("PARANOID")
            profile.rate_limit_config = RateLimitConfig.for_security_mode("PARANOID")
            profile.cache_config = CacheConfig.for_security_level("PARANOID")
            profile.audit_config = AuditConfig.for_security_level("PARANOID")
            profile.resource_limits = ResourceLimits.for_protection_level("PARANOID")
            profile.data_retention_days = 1095  # 3 years
            profile.automatic_pii_masking = True
            profile.secure_deletion_required = True
            profile.audit_config.gdpr_compliance = True
            profile.audit_config.enable_data_subject_requests = True
        
        # HIPAA specific settings
        if ComplianceStandard.HIPAA in standards:
            profile.encryption_required = True
            profile.pii_protection_required = True
            profile.data_retention_days = 2190  # 6 years
            profile.secure_deletion_required = True
        
        # PCI DSS specific settings
        if ComplianceStandard.PCI_DSS in standards:
            profile.encryption_required = True
            profile.enforce_https = True
            profile.data_retention_days = 365  # 1 year minimum
            profile.security_monitoring_enabled = True
        
        return profile


@dataclass
class SecurityPolicyRule:
    """Individual security policy rule."""
    
    name: str
    description: str
    category: str
    severity: str  # "low", "medium", "high", "critical"
    enabled: bool = True
    conditions: Dict[str, Any] = field(default_factory=dict)
    actions: List[str] = field(default_factory=list)
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate rule against context."""
        if not self.enabled:
            return False
        
        # Simple condition evaluation
        for key, expected_value in self.conditions.items():
            if key not in context:
                return False
            
            context_value = context[key]
            
            if isinstance(expected_value, dict):
                # Handle operators like {"gt": 10}, {"in": ["value1", "value2"]}
                for operator, operand in expected_value.items():
                    if operator == "gt" and context_value <= operand:
                        return False
                    elif operator == "lt" and context_value >= operand:
                        return False
                    elif operator == "in" and context_value not in operand:
                        return False
                    elif operator == "not_in" and context_value in operand:
                        return False
                    elif operator == "eq" and context_value != operand:
                        return False
                    elif operator == "ne" and context_value == operand:
                        return False
            else:
                # Direct comparison
                if context_value != expected_value:
                    return False
        
        return True


class SecurityPolicyEngine:
    """Security policy evaluation engine."""
    
    def __init__(self):
        """Initialize policy engine."""
        self.rules: List[SecurityPolicyRule] = []
        self.rule_violations: List[Dict[str, Any]] = []
    
    def add_rule(self, rule: SecurityPolicyRule) -> None:
        """Add security rule."""
        self.rules.append(rule)
        logger.debug(f"Added security rule: {rule.name}")
    
    def evaluate_rules(self, context: Dict[str, Any]) -> List[SecurityPolicyRule]:
        """Evaluate all rules against context."""
        triggered_rules = []
        
        for rule in self.rules:
            if rule.evaluate(context):
                triggered_rules.append(rule)
                
                # Record violation
                self.rule_violations.append({
                    "rule": rule.name,
                    "category": rule.category,
                    "severity": rule.severity,
                    "timestamp": datetime.now(),
                    "context": context.copy()
                })
                
                logger.warning(f"Security policy violation: {rule.name}")
        
        return triggered_rules
    
    def get_default_rules(self) -> List[SecurityPolicyRule]:
        """Get default security policy rules."""
        return [
            SecurityPolicyRule(
                name="excessive_memory_usage",
                description="Alert when memory usage exceeds threshold",
                category="resource_protection",
                severity="high",
                conditions={"memory_mb": {"gt": 1000}},
                actions=["log_violation", "throttle_operation"]
            ),
            SecurityPolicyRule(
                name="high_rate_limit_violations",
                description="Alert when rate limit violations are frequent",
                category="rate_limiting",
                severity="medium",
                conditions={"rate_limit_violations": {"gt": 10}},
                actions=["log_violation", "temporary_block"]
            ),
            SecurityPolicyRule(
                name="pii_in_logs",
                description="Alert when PII is detected in logs",
                category="data_protection",
                severity="critical",
                conditions={"pii_detected": True},
                actions=["log_violation", "mask_data", "alert_security_team"]
            ),
            SecurityPolicyRule(
                name="failed_authentication_attempts",
                description="Alert on multiple failed authentication attempts",
                category="authentication",
                severity="high",
                conditions={"failed_auth_attempts": {"gt": 5}},
                actions=["log_violation", "temporary_block", "alert_security_team"]
            ),
            SecurityPolicyRule(
                name="suspicious_user_agent",
                description="Alert on suspicious user agents",
                category="request_validation",
                severity="medium",
                conditions={"suspicious_user_agent": True},
                actions=["log_violation", "additional_validation"]
            )
        ]


class SecurityConfigManager:
    """
    Centralized security configuration management.
    
    Manages security policies, profiles, and runtime configuration
    with environment-specific overrides and compliance support.
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize security configuration manager."""
        self.config_path = config_path or Path("security_config.yaml")
        self.profiles: Dict[str, SecurityProfile] = {}
        self.active_profile: Optional[SecurityProfile] = None
        self.policy_engine = SecurityPolicyEngine()
        
        # Load default profiles
        self._load_default_profiles()
        
        # Load configuration file if exists
        if self.config_path.exists():
            self._load_configuration_file()
        else:
            self._create_default_configuration()
        
        # Set up policy engine with default rules
        for rule in self.policy_engine.get_default_rules():
            self.policy_engine.add_rule(rule)
        
        logger.info(f"Security configuration manager initialized with {len(self.profiles)} profiles")
    
    def _load_default_profiles(self) -> None:
        """Load default security profiles."""
        profiles = [
            SecurityProfile.create_development_profile(),
            SecurityProfile.create_production_profile(),
            SecurityProfile.create_compliance_profile([ComplianceStandard.GDPR]),
            SecurityProfile.create_compliance_profile([ComplianceStandard.SOC2]),
            SecurityProfile.create_compliance_profile([
                ComplianceStandard.GDPR,
                ComplianceStandard.SOC2,
                ComplianceStandard.OWASP_TOP10
            ])
        ]
        
        for profile in profiles:
            self.profiles[profile.name] = profile
    
    def _load_configuration_file(self) -> None:
        """Load configuration from file."""
        try:
            with open(self.config_path, 'r') as f:
                if self.config_path.suffix.lower() in ['.yaml', '.yml']:
                    config_data = yaml.safe_load(f)
                else:
                    config_data = json.load(f)
            
            # Load custom profiles
            if "profiles" in config_data:
                for profile_data in config_data["profiles"]:
                    profile = self._profile_from_dict(profile_data)
                    self.profiles[profile.name] = profile
            
            # Set active profile
            if "active_profile" in config_data:
                self.set_active_profile(config_data["active_profile"])
            
            logger.info(f"Loaded security configuration from {self.config_path}")
            
        except Exception as e:
            logger.error(f"Failed to load security configuration: {e}")
            self._create_default_configuration()
    
    def _create_default_configuration(self) -> None:
        """Create default configuration file."""
        try:
            # Determine environment
            env = os.getenv("ENVIRONMENT", "development").lower()
            
            if env == "production":
                self.set_active_profile("production")
            elif env in ["staging", "test", "testing"]:
                # Create staging profile similar to production but with more logging
                staging_profile = SecurityProfile.create_production_profile()
                staging_profile.name = "staging"
                staging_profile.description = "Staging environment with production-like security"
                staging_profile.security_mode = SecurityMode.STAGING
                staging_profile.enable_debug_mode = True
                staging_profile.audit_config.minimum_severity = EventSeverity.DEBUG
                self.profiles["staging"] = staging_profile
                self.set_active_profile("staging")
            else:
                self.set_active_profile("development")
            
            self._save_configuration_file()
            
        except Exception as e:
            logger.error(f"Failed to create default configuration: {e}")
    
    def _save_configuration_file(self) -> None:
        """Save current configuration to file."""
        try:
            config_data = {
                "active_profile": self.active_profile.name if self.active_profile else None,
                "profiles": [self._profile_to_dict(profile) for profile in self.profiles.values()],
                "last_updated": datetime.now().isoformat()
            }
            
            with open(self.config_path, 'w') as f:
                if self.config_path.suffix.lower() in ['.yaml', '.yml']:
                    yaml.safe_dump(config_data, f, default_flow_style=False, indent=2)
                else:
                    json.dump(config_data, f, indent=2, default=str)
            
            logger.debug(f"Saved security configuration to {self.config_path}")
            
        except Exception as e:
            logger.error(f"Failed to save security configuration: {e}")
    
    def _profile_to_dict(self, profile: SecurityProfile) -> Dict[str, Any]:
        """Convert profile to dictionary."""
        data = asdict(profile)
        
        # Convert enums to strings
        data['security_mode'] = profile.security_mode.value
        data['compliance_standards'] = [std.value for std in profile.compliance_standards]
        
        # Convert sets to lists for JSON serialization
        data['trusted_domains'] = list(profile.trusted_domains)
        data['blocked_domains'] = list(profile.blocked_domains)
        
        return data
    
    def _profile_from_dict(self, data: Dict[str, Any]) -> SecurityProfile:
        """Create profile from dictionary."""
        # Handle enum conversions
        data['security_mode'] = SecurityMode(data.get('security_mode', 'development'))
        data['compliance_standards'] = [
            ComplianceStandard(std) for std in data.get('compliance_standards', [])
        ]
        
        # Convert lists back to sets
        data['trusted_domains'] = set(data.get('trusted_domains', []))
        data['blocked_domains'] = set(data.get('blocked_domains', []))
        
        # Create sub-configs
        data['validation_config'] = ValidationConfig(**data.get('validation_config', {}))
        data['rate_limit_config'] = RateLimitConfig(**data.get('rate_limit_config', {}))
        data['cache_config'] = CacheConfig(**data.get('cache_config', {}))
        data['audit_config'] = AuditConfig(**data.get('audit_config', {}))
        data['resource_limits'] = ResourceLimits(**data.get('resource_limits', {}))
        
        return SecurityProfile(**data)
    
    def get_profile(self, name: str) -> Optional[SecurityProfile]:
        """Get security profile by name."""
        return self.profiles.get(name)
    
    def list_profiles(self) -> List[str]:
        """List available security profiles."""
        return list(self.profiles.keys())
    
    def set_active_profile(self, profile_name: str) -> bool:
        """Set active security profile."""
        if profile_name not in self.profiles:
            logger.error(f"Security profile '{profile_name}' not found")
            return False
        
        self.active_profile = self.profiles[profile_name]
        
        # Apply environment overrides
        self._apply_environment_overrides()
        
        logger.info(f"Activated security profile: {profile_name}")
        return True
    
    def _apply_environment_overrides(self) -> None:
        """Apply environment variable overrides."""
        if not self.active_profile:
            return
        
        # Apply environment-specific overrides from profile
        env_name = os.getenv("ENVIRONMENT", "").lower()
        if env_name in self.active_profile.environment_overrides:
            overrides = self.active_profile.environment_overrides[env_name]
            for key, value in overrides.items():
                if hasattr(self.active_profile, key):
                    setattr(self.active_profile, key, value)
        
        # Apply direct environment variable overrides
        env_overrides = {
            "SECURITY_ENCRYPTION_REQUIRED": "encryption_required",
            "SECURITY_PII_PROTECTION": "pii_protection_required",
            "SECURITY_AUDIT_LOGGING": "audit_logging_required",
            "SECURITY_RATE_LIMITING": "rate_limiting_enabled",
            "SECURITY_DEBUG_MODE": "enable_debug_mode",
            "SECURITY_TELEMETRY": "enable_telemetry",
            "SECURITY_HTTPS_ENFORCE": "enforce_https",
        }
        
        for env_var, profile_attr in env_overrides.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                # Convert string to boolean
                bool_value = env_value.lower() in ("true", "1", "yes", "on")
                setattr(self.active_profile, profile_attr, bool_value)
                logger.debug(f"Applied environment override: {profile_attr} = {bool_value}")
    
    def get_active_profile(self) -> Optional[SecurityProfile]:
        """Get currently active security profile."""
        return self.active_profile
    
    def validate_configuration(self) -> List[str]:
        """Validate current configuration and return list of issues."""
        issues = []
        
        if not self.active_profile:
            issues.append("No active security profile set")
            return issues
        
        profile = self.active_profile
        
        # Check required security features for production
        if profile.security_mode == SecurityMode.PRODUCTION:
            if not profile.encryption_required:
                issues.append("Encryption is not required in production mode")
            if not profile.audit_logging_required:
                issues.append("Audit logging is not required in production mode")
            if not profile.pii_protection_required:
                issues.append("PII protection is not required in production mode")
            if profile.enable_debug_mode:
                issues.append("Debug mode should not be enabled in production")
            if profile.enable_telemetry:
                issues.append("Telemetry should be disabled in production")
        
        # Check compliance requirements
        for standard in profile.compliance_standards:
            if standard == ComplianceStandard.GDPR:
                if not profile.automatic_pii_masking:
                    issues.append("GDPR compliance requires automatic PII masking")
                if not profile.secure_deletion_required:
                    issues.append("GDPR compliance requires secure deletion capability")
                if profile.data_retention_days < 365:
                    issues.append("GDPR compliance typically requires at least 1 year retention")
            
            elif standard == ComplianceStandard.SOC2:
                if not profile.security_monitoring_enabled:
                    issues.append("SOC 2 compliance requires security monitoring")
                if not profile.audit_logging_required:
                    issues.append("SOC 2 compliance requires comprehensive audit logging")
        
        return issues
    
    def evaluate_security_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate security context against active policies."""
        if not self.active_profile:
            return {"allowed": False, "reason": "No active security profile"}
        
        # Evaluate policy rules
        triggered_rules = self.policy_engine.evaluate_rules(context)
        
        # Determine if operation should be allowed
        critical_violations = [rule for rule in triggered_rules if rule.severity == "critical"]
        high_violations = [rule for rule in triggered_rules if rule.severity == "high"]
        
        if critical_violations:
            return {
                "allowed": False,
                "reason": f"Critical security policy violations: {[r.name for r in critical_violations]}",
                "violations": [r.name for r in triggered_rules],
                "actions": []
            }
        elif len(high_violations) > 2:
            return {
                "allowed": False,
                "reason": f"Too many high-severity violations: {[r.name for r in high_violations]}",
                "violations": [r.name for r in triggered_rules],
                "actions": []
            }
        else:
            # Collect all actions
            actions = []
            for rule in triggered_rules:
                actions.extend(rule.actions)
            
            return {
                "allowed": True,
                "violations": [r.name for r in triggered_rules],
                "actions": list(set(actions))  # Remove duplicates
            }
    
    def get_security_summary(self) -> Dict[str, Any]:
        """Get summary of current security configuration."""
        if not self.active_profile:
            return {"error": "No active security profile"}
        
        profile = self.active_profile
        validation_issues = self.validate_configuration()
        
        return {
            "active_profile": profile.name,
            "security_mode": profile.security_mode.value,
            "compliance_standards": [std.value for std in profile.compliance_standards],
            "encryption_required": profile.encryption_required,
            "pii_protection_required": profile.pii_protection_required,
            "audit_logging_required": profile.audit_logging_required,
            "rate_limiting_enabled": profile.rate_limiting_enabled,
            "resource_monitoring_enabled": profile.resource_monitoring_enabled,
            "debug_mode": profile.enable_debug_mode,
            "validation_issues": validation_issues,
            "is_production_ready": len(validation_issues) == 0 and profile.security_mode != SecurityMode.DEVELOPMENT,
            "policy_violations": len(self.policy_engine.rule_violations),
            "last_violation": max([v["timestamp"] for v in self.policy_engine.rule_violations], default=None)
        }
    
    def export_configuration(self) -> Dict[str, Any]:
        """Export complete security configuration."""
        return {
            "active_profile": self.active_profile.name if self.active_profile else None,
            "profiles": {name: self._profile_to_dict(profile) for name, profile in self.profiles.items()},
            "policy_violations": self.policy_engine.rule_violations,
            "configuration_valid": len(self.validate_configuration()) == 0,
            "exported_at": datetime.now().isoformat()
        }
    
    def cleanup(self) -> None:
        """Clean up resources and save configuration."""
        self._save_configuration_file()
        logger.info("Security configuration manager cleanup complete")


def create_security_config_manager(
    environment: Optional[str] = None,
    config_path: Optional[Path] = None
) -> SecurityConfigManager:
    """
    Factory function to create security configuration manager.
    
    Args:
        environment: Environment name (development, staging, production)
        config_path: Path to configuration file
        
    Returns:
        Configured SecurityConfigManager
    """
    manager = SecurityConfigManager(config_path)
    
    if environment:
        # Try to set environment-specific profile
        env_profiles = {
            "development": "development",
            "dev": "development",
            "staging": "production",  # Use production profile for staging
            "stage": "production",
            "production": "production",
            "prod": "production",
            "compliance": "compliance"
        }
        
        profile_name = env_profiles.get(environment.lower(), "development")
        if not manager.set_active_profile(profile_name):
            logger.warning(f"Failed to set profile for environment '{environment}', using development profile")
            manager.set_active_profile("development")
    
    return manager