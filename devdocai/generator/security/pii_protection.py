"""
M004 Document Generator - PII detection and protection system.

Comprehensive PII (Personally Identifiable Information) detection, 
masking, and protection for document generation.
"""

import re
import logging
import hashlib
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import json

from ...common.logging import get_logger
from ...common.security import PIIDetector as BasePIIDetector, AuditLogger, get_audit_logger

logger = get_logger(__name__)


class PIISensitivity(Enum):
    """PII sensitivity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PIIAction(Enum):
    """Actions to take when PII is detected."""
    LOG = "log"
    MASK = "mask"
    REDACT = "redact"
    BLOCK = "block"
    ENCRYPT = "encrypt"


@dataclass
class PIIPolicy:
    """PII protection policy configuration."""
    pii_type: str
    sensitivity: PIISensitivity
    action: PIIAction
    mask_char: str = "*"
    preserve_length: bool = True
    preserve_format: bool = False
    require_consent: bool = False


@dataclass
class PIIFinding:
    """PII detection finding."""
    pii_type: str
    value: str
    masked_value: str
    location: str
    sensitivity: PIISensitivity
    confidence: float
    action_taken: PIIAction
    timestamp: datetime


class EnhancedPIIDetector(BasePIIDetector):
    """
    Enhanced PII detector with comprehensive pattern recognition.
    
    Detects:
    - Personal identifiers (SSN, driver's license, passport)
    - Financial information (credit cards, bank accounts, routing numbers)
    - Contact information (emails, phone numbers, addresses)
    - Health information (medical record numbers, insurance IDs)
    - Government IDs (tax IDs, military IDs)
    - Biometric data patterns
    - Custom organizational PII patterns
    """
    
    # Enhanced PII patterns with confidence scoring
    ENHANCED_PII_PATTERNS = {
        # Personal Identifiers
        'ssn': {
            'patterns': [
                re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
                re.compile(r'\b\d{9}\b'),
                re.compile(r'\b\d{3}\s\d{2}\s\d{4}\b')
            ],
            'sensitivity': PIISensitivity.HIGH,
            'confidence': 0.95
        },
        'drivers_license': {
            'patterns': [
                re.compile(r'\b[A-Z]\d{7,8}\b'),  # Common format
                re.compile(r'\b[A-Z]{2}\d{6,7}\b'),
                re.compile(r'\bD\d{8}\b'),
            ],
            'sensitivity': PIISensitivity.MEDIUM,
            'confidence': 0.80
        },
        'passport': {
            'patterns': [
                re.compile(r'\b[A-Z]\d{8}\b'),
                re.compile(r'\b\d{9}[A-Z]\b')
            ],
            'sensitivity': PIISensitivity.HIGH,
            'confidence': 0.85
        },
        
        # Financial Information
        'credit_card': {
            'patterns': [
                re.compile(r'\b4\d{3}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'),  # Visa
                re.compile(r'\b5[1-5]\d{2}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'),  # MasterCard
                re.compile(r'\b3[47]\d{2}[\s-]?\d{6}[\s-]?\d{5}\b'),  # AmEx
                re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b')  # Generic
            ],
            'sensitivity': PIISensitivity.CRITICAL,
            'confidence': 0.90
        },
        'bank_account': {
            'patterns': [
                re.compile(r'\b\d{8,17}\b'),  # Account numbers
                re.compile(r'\bACC\d{6,12}\b', re.IGNORECASE)
            ],
            'sensitivity': PIISensitivity.CRITICAL,
            'confidence': 0.75
        },
        'routing_number': {
            'patterns': [
                re.compile(r'\b\d{9}\b'),  # US routing numbers
                re.compile(r'\bRTN\d{9}\b', re.IGNORECASE)
            ],
            'sensitivity': PIISensitivity.HIGH,
            'confidence': 0.80
        },
        
        # Contact Information
        'email': {
            'patterns': [
                re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
            ],
            'sensitivity': PIISensitivity.MEDIUM,
            'confidence': 0.95
        },
        'phone': {
            'patterns': [
                re.compile(r'\b\+?1?[\s-]?\(?[0-9]{3}\)?[\s-]?[0-9]{3}[\s-]?[0-9]{4}\b'),
                re.compile(r'\b\d{10}\b'),
                re.compile(r'\b\+\d{1,3}[\s-]\d{3,14}\b')
            ],
            'sensitivity': PIISensitivity.MEDIUM,
            'confidence': 0.85
        },
        'address': {
            'patterns': [
                re.compile(r'\b\d+\s+[A-Za-z0-9\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Place|Pl)\b', re.IGNORECASE),
                re.compile(r'\b\d{5}(?:-\d{4})?\b')  # ZIP codes
            ],
            'sensitivity': PIISensitivity.MEDIUM,
            'confidence': 0.70
        },
        
        # Health Information
        'medical_record': {
            'patterns': [
                re.compile(r'\bMRN\d{6,12}\b', re.IGNORECASE),
                re.compile(r'\bMED\d{6,12}\b', re.IGNORECASE),
                re.compile(r'\bPATIENT\d{6,12}\b', re.IGNORECASE)
            ],
            'sensitivity': PIISensitivity.CRITICAL,
            'confidence': 0.85
        },
        'health_insurance': {
            'patterns': [
                re.compile(r'\bINS\d{8,15}\b', re.IGNORECASE),
                re.compile(r'\bPOLICY\d{8,15}\b', re.IGNORECASE)
            ],
            'sensitivity': PIISensitivity.HIGH,
            'confidence': 0.80
        },
        
        # Government IDs
        'tax_id': {
            'patterns': [
                re.compile(r'\b\d{2}-\d{7}\b'),  # EIN format
                re.compile(r'\bTIN\d{9}\b', re.IGNORECASE)
            ],
            'sensitivity': PIISensitivity.HIGH,
            'confidence': 0.85
        },
        'military_id': {
            'patterns': [
                re.compile(r'\b\d{10}\b'),  # DoD ID
                re.compile(r'\bMIL\d{8,12}\b', re.IGNORECASE)
            ],
            'sensitivity': PIISensitivity.HIGH,
            'confidence': 0.75
        },
        
        # IP Addresses (can be PII in some contexts)
        'ip_address': {
            'patterns': [
                re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),
                re.compile(r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b')  # IPv6
            ],
            'sensitivity': PIISensitivity.LOW,
            'confidence': 0.90
        },
        
        # Custom patterns (can be configured)
        'employee_id': {
            'patterns': [
                re.compile(r'\bEMP\d{4,8}\b', re.IGNORECASE),
                re.compile(r'\bE\d{6}\b')
            ],
            'sensitivity': PIISensitivity.MEDIUM,
            'confidence': 0.70
        }
    }
    
    def __init__(self, custom_patterns: Optional[Dict[str, Any]] = None):
        """
        Initialize enhanced PII detector.
        
        Args:
            custom_patterns: Custom PII patterns to add
        """
        super().__init__()
        self.audit_logger = get_audit_logger()
        
        # Add custom patterns if provided
        if custom_patterns:
            for pii_type, pattern_info in custom_patterns.items():
                self.ENHANCED_PII_PATTERNS[pii_type] = pattern_info
        
        logger.info(f"Enhanced PII detector initialized with {len(self.ENHANCED_PII_PATTERNS)} pattern types")
    
    def detect_pii_comprehensive(
        self, 
        text: str, 
        context: str = "general",
        min_confidence: float = 0.7
    ) -> List[PIIFinding]:
        """
        Comprehensive PII detection with confidence scoring.
        
        Args:
            text: Text to analyze
            context: Context of the text (template, input, output)
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of PII findings
        """
        findings = []
        
        for pii_type, pattern_info in self.ENHANCED_PII_PATTERNS.items():
            confidence = pattern_info['confidence']
            
            if confidence < min_confidence:
                continue
            
            sensitivity = pattern_info['sensitivity']
            patterns = pattern_info['patterns']
            
            for pattern in patterns:
                matches = pattern.finditer(text)
                
                for match in matches:
                    value = match.group()
                    
                    # Additional validation for some PII types
                    if pii_type == 'credit_card' and not self._validate_credit_card(value):
                        continue
                    
                    if pii_type == 'ssn' and not self._validate_ssn(value):
                        continue
                    
                    finding = PIIFinding(
                        pii_type=pii_type,
                        value=value,
                        masked_value="",  # Will be set by masking function
                        location=f"{context}:{match.start()}-{match.end()}",
                        sensitivity=sensitivity,
                        confidence=confidence,
                        action_taken=PIIAction.LOG,
                        timestamp=datetime.now()
                    )
                    
                    findings.append(finding)
        
        return findings
    
    def _validate_credit_card(self, number: str) -> bool:
        """Validate credit card using Luhn algorithm."""
        # Remove spaces and hyphens
        cleaned = re.sub(r'[\s-]', '', number)
        
        if not cleaned.isdigit():
            return False
        
        # Luhn algorithm
        def luhn_check(card_num):
            def digits_of(n):
                return [int(d) for d in str(n)]
            
            digits = digits_of(card_num)
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            checksum = sum(odd_digits)
            for d in even_digits:
                checksum += sum(digits_of(d * 2))
            return checksum % 10 == 0
        
        return luhn_check(cleaned)
    
    def _validate_ssn(self, ssn: str) -> bool:
        """Basic SSN validation."""
        # Remove formatting
        cleaned = re.sub(r'[\s-]', '', ssn)
        
        if len(cleaned) != 9 or not cleaned.isdigit():
            return False
        
        # Invalid SSN patterns
        if cleaned in ['000000000', '111111111', '222222222', '333333333',
                      '444444444', '555555555', '666666666', '777777777',
                      '888888888', '999999999']:
            return False
        
        # Area number can't be 000 or 666
        area = cleaned[:3]
        if area in ['000', '666']:
            return False
        
        return True


class PIIProtectionEngine:
    """
    Comprehensive PII protection engine for document generation.
    
    Features:
    - Configurable protection policies
    - Multiple masking strategies
    - Consent management
    - Audit trail generation
    - Context-aware protection
    """
    
    def __init__(self, policies: Optional[Dict[str, PIIPolicy]] = None):
        """
        Initialize PII protection engine.
        
        Args:
            policies: PII protection policies by type
        """
        self.detector = EnhancedPIIDetector()
        self.audit_logger = get_audit_logger()
        
        # Default policies
        self.policies: Dict[str, PIIPolicy] = {
            'ssn': PIIPolicy('ssn', PIISensitivity.HIGH, PIIAction.REDACT),
            'credit_card': PIIPolicy('credit_card', PIISensitivity.CRITICAL, PIIAction.BLOCK),
            'email': PIIPolicy('email', PIISensitivity.MEDIUM, PIIAction.MASK),
            'phone': PIIPolicy('phone', PIISensitivity.MEDIUM, PIIAction.MASK),
            'address': PIIPolicy('address', PIISensitivity.MEDIUM, PIIAction.MASK),
            'medical_record': PIIPolicy('medical_record', PIISensitivity.CRITICAL, PIIAction.BLOCK),
            'bank_account': PIIPolicy('bank_account', PIISensitivity.CRITICAL, PIIAction.BLOCK),
            'ip_address': PIIPolicy('ip_address', PIISensitivity.LOW, PIIAction.LOG),
        }
        
        # Override with custom policies
        if policies:
            self.policies.update(policies)
        
        logger.info(f"PII protection engine initialized with {len(self.policies)} policies")
    
    def scan_and_protect(
        self, 
        content: str, 
        context: str = "general",
        client_id: str = "anonymous",
        require_explicit_consent: bool = False
    ) -> Dict[str, Any]:
        """
        Scan content for PII and apply protection measures.
        
        Args:
            content: Content to scan and protect
            context: Context of content (input, template, output)
            client_id: Client identifier
            require_explicit_consent: Require explicit consent for PII processing
            
        Returns:
            Dictionary with protected content and metadata
        """
        scan_start = datetime.now()
        
        # Detect PII
        findings = self.detector.detect_pii_comprehensive(content, context)
        
        # Apply protection policies
        protected_content = content
        actions_taken = []
        consent_required = []
        blocked_pii_types = set()
        
        for finding in findings:
            policy = self.policies.get(finding.pii_type)
            
            if not policy:
                # Default policy for unknown PII types
                policy = PIIPolicy(finding.pii_type, PIISensitivity.MEDIUM, PIIAction.LOG)
            
            # Check consent requirements
            if policy.require_consent or require_explicit_consent:
                if policy.sensitivity in [PIISensitivity.HIGH, PIISensitivity.CRITICAL]:
                    consent_required.append(finding.pii_type)
                    continue
            
            # Apply protection action
            if policy.action == PIIAction.BLOCK:
                blocked_pii_types.add(finding.pii_type)
                continue
            elif policy.action == PIIAction.REDACT:
                masked_value = self._redact_pii(finding.value, policy)
            elif policy.action == PIIAction.MASK:
                masked_value = self._mask_pii(finding.value, policy)
            elif policy.action == PIIAction.ENCRYPT:
                masked_value = self._encrypt_pii(finding.value)
            else:  # PIIAction.LOG
                masked_value = finding.value
            
            # Replace in content
            if policy.action != PIIAction.LOG:
                protected_content = protected_content.replace(finding.value, masked_value)
                finding.masked_value = masked_value
                finding.action_taken = policy.action
            
            actions_taken.append({
                'pii_type': finding.pii_type,
                'action': policy.action.value,
                'original_value': finding.value,
                'masked_value': finding.masked_value,
                'location': finding.location,
                'sensitivity': finding.sensitivity.value
            })
        
        scan_duration = (datetime.now() - scan_start).total_seconds()
        
        # Log PII scan results
        self._log_pii_scan(client_id, context, findings, actions_taken, scan_duration)
        
        # Check if processing should be blocked
        processing_blocked = bool(blocked_pii_types or consent_required)
        
        result = {
            'protected_content': protected_content,
            'pii_detected': len(findings) > 0,
            'pii_count': len(findings),
            'pii_types_found': list(set(f.pii_type for f in findings)),
            'actions_taken': actions_taken,
            'processing_blocked': processing_blocked,
            'blocked_pii_types': list(blocked_pii_types),
            'consent_required': list(set(consent_required)),
            'scan_metadata': {
                'context': context,
                'client_id': client_id,
                'scan_duration': scan_duration,
                'findings_count': len(findings),
                'timestamp': datetime.now().isoformat()
            }
        }
        
        return result
    
    def _mask_pii(self, value: str, policy: PIIPolicy) -> str:
        """Mask PII value according to policy."""
        if policy.preserve_format:
            # Preserve format (e.g., XXX-XX-1234 for SSN)
            if policy.pii_type == 'ssn':
                return re.sub(r'\d', policy.mask_char, value[:-4]) + value[-4:]
            elif policy.pii_type == 'credit_card':
                return re.sub(r'\d', policy.mask_char, value[:-4]) + value[-4:]
            elif policy.pii_type == 'phone':
                # Keep area code visible
                cleaned = re.sub(r'[\s()-]', '', value)
                if len(cleaned) >= 7:
                    masked = cleaned[:3] + policy.mask_char * (len(cleaned) - 6) + cleaned[-3:]
                    return masked
            elif policy.pii_type == 'email':
                # Keep domain visible
                parts = value.split('@')
                if len(parts) == 2:
                    local = parts[0]
                    if len(local) > 2:
                        masked_local = local[0] + policy.mask_char * (len(local) - 2) + local[-1]
                    else:
                        masked_local = policy.mask_char * len(local)
                    return f"{masked_local}@{parts[1]}"
        
        if policy.preserve_length:
            return policy.mask_char * len(value)
        else:
            return f"[{policy.pii_type.upper()}_REDACTED]"
    
    def _redact_pii(self, value: str, policy: PIIPolicy) -> str:
        """Completely redact PII value."""
        return f"[{policy.pii_type.upper()}_REDACTED]"
    
    def _encrypt_pii(self, value: str) -> str:
        """Encrypt PII value (simplified implementation)."""
        # In production, use proper encryption with key management
        hashed = hashlib.sha256(value.encode()).hexdigest()[:16]
        return f"[ENCRYPTED_{hashed}]"
    
    def _log_pii_scan(
        self, 
        client_id: str, 
        context: str, 
        findings: List[PIIFinding], 
        actions: List[Dict[str, Any]], 
        duration: float
    ):
        """Log PII scan results for audit."""
        self.audit_logger.log_event('pii_scan_completed', {
            'client_id': client_id,
            'context': context,
            'findings_count': len(findings),
            'pii_types': list(set(f.pii_type for f in findings)),
            'actions_count': len(actions),
            'scan_duration': duration,
            'timestamp': datetime.now().isoformat()
        })
        
        # Log individual findings for high/critical sensitivity
        for finding in findings:
            if finding.sensitivity in [PIISensitivity.HIGH, PIISensitivity.CRITICAL]:
                self.audit_logger.log_event('high_sensitivity_pii_detected', {
                    'client_id': client_id,
                    'context': context,
                    'pii_type': finding.pii_type,
                    'sensitivity': finding.sensitivity.value,
                    'location': finding.location,
                    'timestamp': finding.timestamp.isoformat()
                })
    
    def generate_pii_report(
        self, 
        client_id: Optional[str] = None, 
        hours: int = 24
    ) -> Dict[str, Any]:
        """Generate PII detection and protection report."""
        # This would typically query audit logs
        # For now, return a structure showing what the report would contain
        
        report = {
            'report_period': f"{hours} hours",
            'generated_at': datetime.now().isoformat(),
            'client_id': client_id or "all",
            'summary': {
                'total_scans': 0,
                'pii_detections': 0,
                'protection_actions': 0,
                'blocked_operations': 0
            },
            'pii_by_type': {},
            'protection_effectiveness': {
                'scans_with_pii': 0,
                'successful_protections': 0,
                'blocked_due_to_pii': 0
            },
            'recommendations': []
        }
        
        return report
    
    def update_policy(self, pii_type: str, policy: PIIPolicy):
        """Update protection policy for a PII type."""
        self.policies[pii_type] = policy
        
        self.audit_logger.log_event('pii_policy_updated', {
            'pii_type': pii_type,
            'sensitivity': policy.sensitivity.value,
            'action': policy.action.value,
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info(f"PII policy updated for {pii_type}: {policy.action.value}")
    
    def get_protection_statistics(self) -> Dict[str, Any]:
        """Get PII protection statistics."""
        stats = {
            'policies_configured': len(self.policies),
            'patterns_available': len(self.detector.ENHANCED_PII_PATTERNS),
            'policy_summary': {}
        }
        
        # Summarize policies by action
        action_summary = {}
        for pii_type, policy in self.policies.items():
            action = policy.action.value
            if action not in action_summary:
                action_summary[action] = []
            action_summary[action].append(pii_type)
        
        stats['policy_summary'] = action_summary
        
        return stats