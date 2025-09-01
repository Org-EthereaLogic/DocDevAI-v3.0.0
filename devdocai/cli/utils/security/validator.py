"""
Security validation and policy enforcement for CLI.

Provides comprehensive security validation and policy checks.
"""

import re
import json
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from enum import Enum


class PolicyViolation(Exception):
    """Security policy violation."""
    pass


class SecurityPolicy(Enum):
    """Security policy types."""
    INPUT_VALIDATION = "input_validation"
    ACCESS_CONTROL = "access_control"
    DATA_PROTECTION = "data_protection"
    AUDIT_LOGGING = "audit_logging"
    RATE_LIMITING = "rate_limiting"
    ENCRYPTION = "encryption"


@dataclass
class ValidationRule:
    """Validation rule definition."""
    name: str
    description: str
    validator: Callable
    severity: str  # low, medium, high, critical
    policy: SecurityPolicy


class SecurityValidator:
    """
    Comprehensive security validation.
    
    Features:
    - Multi-layer validation
    - Policy enforcement
    - Custom rule support
    - Compliance checking
    """
    
    def __init__(self, policy_file: Optional[Path] = None):
        """
        Initialize security validator.
        
        Args:
            policy_file: Path to security policy configuration
        """
        self.policy_file = policy_file
        self.rules: List[ValidationRule] = []
        self.policies: Dict[str, Any] = {}
        
        # Load default rules
        self._load_default_rules()
        
        # Load custom policies if provided
        if policy_file and policy_file.exists():
            self._load_policies(policy_file)
    
    def _load_default_rules(self):
        """Load default validation rules."""
        # Input validation rules
        self.add_rule(ValidationRule(
            name="no_command_injection",
            description="Prevent command injection attacks",
            validator=self._validate_no_command_injection,
            severity="critical",
            policy=SecurityPolicy.INPUT_VALIDATION
        ))
        
        self.add_rule(ValidationRule(
            name="no_path_traversal",
            description="Prevent path traversal attacks",
            validator=self._validate_no_path_traversal,
            severity="critical",
            policy=SecurityPolicy.INPUT_VALIDATION
        ))
        
        self.add_rule(ValidationRule(
            name="no_sql_injection",
            description="Prevent SQL injection attacks",
            validator=self._validate_no_sql_injection,
            severity="critical",
            policy=SecurityPolicy.INPUT_VALIDATION
        ))
        
        # Access control rules
        self.add_rule(ValidationRule(
            name="file_permissions",
            description="Validate file permissions",
            validator=self._validate_file_permissions,
            severity="high",
            policy=SecurityPolicy.ACCESS_CONTROL
        ))
        
        self.add_rule(ValidationRule(
            name="allowed_directories",
            description="Validate directory access",
            validator=self._validate_allowed_directories,
            severity="high",
            policy=SecurityPolicy.ACCESS_CONTROL
        ))
        
        # Data protection rules
        self.add_rule(ValidationRule(
            name="no_sensitive_data",
            description="Prevent sensitive data exposure",
            validator=self._validate_no_sensitive_data,
            severity="high",
            policy=SecurityPolicy.DATA_PROTECTION
        ))
        
        self.add_rule(ValidationRule(
            name="encrypted_storage",
            description="Ensure encrypted storage",
            validator=self._validate_encrypted_storage,
            severity="medium",
            policy=SecurityPolicy.ENCRYPTION
        ))
    
    def add_rule(self, rule: ValidationRule):
        """Add validation rule."""
        self.rules.append(rule)
    
    def validate(self, data: Any, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Validate data against all rules.
        
        Args:
            data: Data to validate
            context: Additional context for validation
            
        Returns:
            List of violations
        """
        violations = []
        context = context or {}
        
        for rule in self.rules:
            try:
                if not rule.validator(data, context):
                    violations.append({
                        'rule': rule.name,
                        'description': rule.description,
                        'severity': rule.severity,
                        'policy': rule.policy.value
                    })
            except Exception as e:
                # Rule validation error
                violations.append({
                    'rule': rule.name,
                    'error': str(e),
                    'severity': 'critical',
                    'policy': rule.policy.value
                })
        
        return violations
    
    def validate_strict(self, data: Any, context: Optional[Dict[str, Any]] = None):
        """
        Strict validation that raises on first violation.
        
        Args:
            data: Data to validate
            context: Additional context
            
        Raises:
            PolicyViolation: On first violation
        """
        violations = self.validate(data, context)
        
        if violations:
            # Find highest severity violation
            critical = [v for v in violations if v['severity'] == 'critical']
            if critical:
                raise PolicyViolation(f"Critical security violation: {critical[0]['description']}")
            
            high = [v for v in violations if v['severity'] == 'high']
            if high:
                raise PolicyViolation(f"High security violation: {high[0]['description']}")
            
            raise PolicyViolation(f"Security violation: {violations[0]['description']}")
    
    def _validate_no_command_injection(self, data: Any, context: Dict[str, Any]) -> bool:
        """Validate no command injection patterns."""
        if not isinstance(data, str):
            return True
        
        dangerous_patterns = [
            r'\$\(',  # Command substitution
            r'`',     # Backticks
            r';\s*\w+',  # Command chaining
            r'\|\s*\w+',  # Pipe
            r'&&',    # AND operator
            r'\|\|',  # OR operator
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, data):
                return False
        
        return True
    
    def _validate_no_path_traversal(self, data: Any, context: Dict[str, Any]) -> bool:
        """Validate no path traversal patterns."""
        if not isinstance(data, str):
            return True
        
        traversal_patterns = [
            r'\.\.[/\\]',  # Basic traversal
            r'%2e%2e',     # URL encoded
            r'\.\.%2f',    # Partial encoding
        ]
        
        for pattern in traversal_patterns:
            if re.search(pattern, data.lower()):
                return False
        
        return True
    
    def _validate_no_sql_injection(self, data: Any, context: Dict[str, Any]) -> bool:
        """Validate no SQL injection patterns."""
        if not isinstance(data, str):
            return True
        
        sql_patterns = [
            r"'\s*or\s*'",  # OR injection
            r";\s*drop\s+",  # DROP statement
            r"union\s+select",  # UNION SELECT
            r"--\s*$",  # SQL comment
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, data.lower()):
                return False
        
        return True
    
    def _validate_file_permissions(self, data: Any, context: Dict[str, Any]) -> bool:
        """Validate file has secure permissions."""
        if 'file_path' not in context:
            return True
        
        file_path = Path(context['file_path'])
        if not file_path.exists():
            return True
        
        # Check permissions (Unix-like systems)
        import os
        import stat
        
        file_stat = os.stat(file_path)
        mode = file_stat.st_mode
        
        # Check for world-writable files
        if mode & stat.S_IWOTH:
            return False
        
        # Check for group-writable sensitive files
        if file_path.suffix in ['.key', '.pem', '.p12'] and mode & stat.S_IWGRP:
            return False
        
        return True
    
    def _validate_allowed_directories(self, data: Any, context: Dict[str, Any]) -> bool:
        """Validate access to allowed directories only."""
        if 'file_path' not in context:
            return True
        
        file_path = Path(context['file_path']).resolve()
        
        # Default allowed directories
        allowed = [
            Path.cwd(),
            Path.home() / '.devdocai',
            Path('/tmp') / 'devdocai'
        ]
        
        # Add custom allowed directories from context
        if 'allowed_dirs' in context:
            allowed.extend(context['allowed_dirs'])
        
        # Check if path is within allowed directories
        for allowed_dir in allowed:
            try:
                file_path.relative_to(allowed_dir)
                return True
            except ValueError:
                continue
        
        return False
    
    def _validate_no_sensitive_data(self, data: Any, context: Dict[str, Any]) -> bool:
        """Validate no sensitive data in output."""
        if not isinstance(data, str):
            return True
        
        # Patterns for sensitive data
        sensitive_patterns = [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
            r'\b(?:\d{4}[-\s]?){3}\d{4}\b',  # Credit card
            r'(?i)(api[_-]?key|password|secret|token)[\s:=]["\']\S+',  # Credentials
        ]
        
        for pattern in sensitive_patterns:
            if re.search(pattern, data):
                return False
        
        return True
    
    def _validate_encrypted_storage(self, data: Any, context: Dict[str, Any]) -> bool:
        """Validate encrypted storage is used."""
        # Check if dealing with sensitive data
        if 'data_type' in context and context['data_type'] in ['credential', 'key', 'secret']:
            # Check if encryption is enabled
            return context.get('encrypted', False)
        
        return True
    
    def _load_policies(self, policy_file: Path):
        """Load security policies from file."""
        with open(policy_file, 'r') as f:
            self.policies = json.load(f)
        
        # Add custom rules from policies
        if 'custom_rules' in self.policies:
            for rule_def in self.policies['custom_rules']:
                # Create validator function from rule definition
                validator = self._create_validator_from_definition(rule_def)
                
                rule = ValidationRule(
                    name=rule_def['name'],
                    description=rule_def.get('description', ''),
                    validator=validator,
                    severity=rule_def.get('severity', 'medium'),
                    policy=SecurityPolicy(rule_def.get('policy', 'INPUT_VALIDATION'))
                )
                
                self.add_rule(rule)
    
    def _create_validator_from_definition(self, rule_def: Dict[str, Any]) -> Callable:
        """Create validator function from rule definition."""
        def validator(data: Any, context: Dict[str, Any]) -> bool:
            # Pattern-based validation
            if 'pattern' in rule_def:
                if isinstance(data, str):
                    if re.search(rule_def['pattern'], data):
                        return rule_def.get('match_means_valid', False)
                    return not rule_def.get('match_means_valid', False)
            
            # Range validation
            if 'min' in rule_def or 'max' in rule_def:
                if isinstance(data, (int, float)):
                    if 'min' in rule_def and data < rule_def['min']:
                        return False
                    if 'max' in rule_def and data > rule_def['max']:
                        return False
            
            # List validation
            if 'allowed_values' in rule_def:
                return data in rule_def['allowed_values']
            
            return True
        
        return validator
    
    def check_compliance(self, standard: str = 'OWASP') -> Dict[str, Any]:
        """
        Check compliance with security standards.
        
        Args:
            standard: Compliance standard (OWASP, CWE, NIST)
            
        Returns:
            Compliance report
        """
        report = {
            'standard': standard,
            'compliant': True,
            'violations': [],
            'recommendations': []
        }
        
        if standard == 'OWASP':
            # OWASP Top 10 checks
            required_rules = [
                'no_command_injection',  # A03: Injection
                'no_path_traversal',     # A01: Broken Access Control
                'no_sensitive_data',     # A02: Cryptographic Failures
                'file_permissions',      # A01: Broken Access Control
            ]
            
            existing_rules = [rule.name for rule in self.rules]
            
            for required in required_rules:
                if required not in existing_rules:
                    report['compliant'] = False
                    report['violations'].append(f"Missing rule: {required}")
            
            # Recommendations
            if 'encrypted_storage' not in existing_rules:
                report['recommendations'].append("Add encrypted storage validation")
            
        elif standard == 'CWE':
            # CWE/SANS Top 25 checks
            cwe_mappings = {
                'CWE-78': 'no_command_injection',
                'CWE-22': 'no_path_traversal',
                'CWE-89': 'no_sql_injection',
                'CWE-200': 'no_sensitive_data',
            }
            
            existing_rules = [rule.name for rule in self.rules]
            
            for cwe, rule_name in cwe_mappings.items():
                if rule_name not in existing_rules:
                    report['compliant'] = False
                    report['violations'].append(f"{cwe}: Missing {rule_name}")
        
        return report