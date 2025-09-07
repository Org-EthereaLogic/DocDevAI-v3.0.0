"""
M003 MIAIR Engine - PII Detection Integration

Integrates M002's PII detection capabilities into the MIAIR Engine for
comprehensive data privacy protection during document analysis.

Security Features:
- PII detection and masking in document content
- Compliance with GDPR/CCPA regulations
- Audit trail for PII handling
- Configurable sensitivity levels
- Secure deletion of temporary data containing PII
"""

import logging
import hashlib
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import json

# Import M002's PII detector
try:
    from ...storage.pii_detector import PIIDetector, PIIType, MaskingStrategy
except ImportError:
    # Fallback for development
    PIIDetector = None
    PIIType = None
    MaskingStrategy = None
    logger = logging.getLogger(__name__)
    logger.warning("M002 PII detector not available, using stub implementation")

logger = logging.getLogger(__name__)


class PIISensitivity(Enum):
    """PII detection sensitivity levels."""
    LOW = "low"  # Only high-confidence matches
    MEDIUM = "medium"  # Balanced detection
    HIGH = "high"  # Include potential matches
    PARANOID = "paranoid"  # Maximum sensitivity


@dataclass
class PIIHandlingConfig:
    """Configuration for PII handling in MIAIR."""
    # Detection settings
    enabled: bool = True
    sensitivity: PIISensitivity = PIISensitivity.MEDIUM
    detect_in_metadata: bool = True
    detect_in_content: bool = True
    
    # Masking settings
    masking_strategy: str = "hash"  # hash, redact, partial, tokenize
    preserve_format: bool = True
    reversible: bool = False
    
    # Compliance settings
    gdpr_mode: bool = True
    ccpa_mode: bool = True
    audit_pii_access: bool = True
    
    # Performance settings
    batch_size: int = 100
    cache_results: bool = True
    parallel_processing: bool = False
    
    # Allowed PII types (if empty, all types are checked)
    allowed_types: Set[str] = field(default_factory=set)
    blocked_types: Set[str] = field(default_factory=set)


class PIIIntegration:
    """
    Integrates PII detection into MIAIR Engine operations.
    
    Provides:
    - Document content scanning for PII
    - Metadata PII detection
    - Configurable masking strategies
    - Compliance reporting
    - Performance optimization for large documents
    """
    
    def __init__(self, config: Optional[PIIHandlingConfig] = None):
        """Initialize PII integration with configuration."""
        self.config = config or PIIHandlingConfig()
        self._detector = None
        self._cache = {}
        self._stats = {
            'documents_scanned': 0,
            'pii_found': 0,
            'pii_masked': 0,
            'false_positives': 0,
            'processing_time': 0.0
        }
        
        # Initialize M002 PII detector if available
        if PIIDetector:
            try:
                self._detector = PIIDetector()
                logger.info("M002 PII detector initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize M002 PII detector: {e}")
                self._detector = None
        else:
            logger.warning("Using fallback PII detection implementation")
    
    def scan_document(self, content: str, metadata: Optional[Dict] = None) -> Tuple[str, Dict]:
        """
        Scan document for PII and optionally mask it.
        
        Args:
            content: Document content to scan
            metadata: Optional document metadata
            
        Returns:
            Tuple of (processed_content, pii_report)
        """
        if not self.config.enabled:
            return content, {'pii_detected': False}
        
        import time
        start_time = time.time()
        
        pii_report = {
            'pii_detected': False,
            'types_found': [],
            'locations': [],
            'masked_count': 0,
            'compliance': {
                'gdpr': self.config.gdpr_mode,
                'ccpa': self.config.ccpa_mode
            }
        }
        
        try:
            # Scan content if enabled
            if self.config.detect_in_content:
                content, content_pii = self._scan_and_mask_content(content)
                if content_pii:
                    pii_report['pii_detected'] = True
                    pii_report['types_found'].extend(content_pii['types'])
                    pii_report['locations'].extend(content_pii['locations'])
                    pii_report['masked_count'] += content_pii['masked_count']
            
            # Scan metadata if enabled
            if self.config.detect_in_metadata and metadata:
                metadata, meta_pii = self._scan_and_mask_metadata(metadata)
                if meta_pii['detected']:
                    pii_report['pii_detected'] = True
                    pii_report['types_found'].extend(meta_pii['types'])
                    pii_report['masked_count'] += meta_pii['masked_count']
            
            # Update statistics
            self._stats['documents_scanned'] += 1
            if pii_report['pii_detected']:
                self._stats['pii_found'] += 1
                self._stats['pii_masked'] += pii_report['masked_count']
            
            processing_time = time.time() - start_time
            self._stats['processing_time'] += processing_time
            pii_report['processing_time'] = processing_time
            
            # Audit if required
            if self.config.audit_pii_access and pii_report['pii_detected']:
                self._audit_pii_access(pii_report)
            
            return content, pii_report
            
        except Exception as e:
            logger.error(f"PII scanning failed: {e}")
            return content, {'error': str(e), 'pii_detected': False}
    
    def _scan_and_mask_content(self, content: str) -> Tuple[str, Dict]:
        """Scan and mask PII in content."""
        if self._detector:
            # Use M002's PII detector
            try:
                result = self._detector.detect(content)
                if result['has_pii']:
                    # Mask PII based on strategy
                    masked_content = self._apply_masking(content, result['findings'])
                    
                    return masked_content, {
                        'types': [f['type'] for f in result['findings']],
                        'locations': [(f['start'], f['end']) for f in result['findings']],
                        'masked_count': len(result['findings'])
                    }
                
                return content, None
                
            except Exception as e:
                logger.error(f"M002 PII detector failed: {e}")
                # Fall back to basic detection
        
        # Fallback: Basic PII detection
        return self._basic_pii_detection(content)
    
    def _basic_pii_detection(self, content: str) -> Tuple[str, Dict]:
        """Basic PII detection when M002 detector is not available."""
        import re
        
        pii_patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b(?:\+?1[-.]?)?\(?[0-9]{3}\)?[-.]?[0-9]{3}[-.]?[0-9]{4}\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'credit_card': r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
            'ip_address': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        }
        
        findings = []
        masked_content = content
        
        for pii_type, pattern in pii_patterns.items():
            # Check if this type should be detected
            if self.config.blocked_types and pii_type in self.config.blocked_types:
                continue
            if self.config.allowed_types and pii_type not in self.config.allowed_types:
                continue
            
            # Find matches
            matches = list(re.finditer(pattern, content))
            for match in matches:
                findings.append({
                    'type': pii_type,
                    'start': match.start(),
                    'end': match.end(),
                    'value': match.group()
                })
        
        if findings:
            # Apply masking
            for finding in sorted(findings, key=lambda x: x['start'], reverse=True):
                mask = self._get_mask(finding['value'], finding['type'])
                masked_content = (
                    masked_content[:finding['start']] +
                    mask +
                    masked_content[finding['end']:]
                )
            
            return masked_content, {
                'types': [f['type'] for f in findings],
                'locations': [(f['start'], f['end']) for f in findings],
                'masked_count': len(findings)
            }
        
        return content, None
    
    def _scan_and_mask_metadata(self, metadata: Dict) -> Tuple[Dict, Dict]:
        """Scan and mask PII in metadata."""
        pii_found = {
            'detected': False,
            'types': [],
            'masked_count': 0
        }
        
        def scan_value(value: Any, path: str = "") -> Any:
            """Recursively scan values for PII."""
            if isinstance(value, str):
                masked, pii_info = self._basic_pii_detection(value)
                if pii_info:
                    pii_found['detected'] = True
                    pii_found['types'].extend(pii_info['types'])
                    pii_found['masked_count'] += pii_info['masked_count']
                    return masked
                return value
            elif isinstance(value, dict):
                return {k: scan_value(v, f"{path}.{k}") for k, v in value.items()}
            elif isinstance(value, list):
                return [scan_value(item, f"{path}[{i}]") for i, item in enumerate(value)]
            return value
        
        masked_metadata = scan_value(metadata)
        return masked_metadata, pii_found
    
    def _apply_masking(self, content: str, findings: List[Dict]) -> str:
        """Apply masking strategy to PII findings."""
        if not findings:
            return content
        
        # Sort findings by position (reverse to maintain positions)
        sorted_findings = sorted(findings, key=lambda x: x.get('start', 0), reverse=True)
        
        masked_content = content
        for finding in sorted_findings:
            start = finding.get('start', 0)
            end = finding.get('end', len(content))
            value = content[start:end]
            
            mask = self._get_mask(value, finding.get('type', 'unknown'))
            masked_content = masked_content[:start] + mask + masked_content[end:]
        
        return masked_content
    
    def _get_mask(self, value: str, pii_type: str) -> str:
        """Get appropriate mask for PII value based on strategy."""
        strategy = self.config.masking_strategy
        
        if strategy == "hash":
            # Hash the value (irreversible)
            hash_value = hashlib.sha256(value.encode()).hexdigest()[:8]
            return f"[{pii_type.upper()}:{hash_value}]"
        
        elif strategy == "redact":
            # Complete redaction
            return f"[{pii_type.upper()}_REDACTED]"
        
        elif strategy == "partial":
            # Partial masking (preserve format)
            if self.config.preserve_format:
                if pii_type == "email":
                    parts = value.split('@')
                    if len(parts) == 2:
                        return f"{parts[0][:2]}***@{parts[1]}"
                elif pii_type == "phone":
                    return f"***-***-{value[-4:]}" if len(value) >= 4 else "***"
                elif pii_type == "credit_card":
                    return f"****-****-****-{value[-4:]}" if len(value) >= 4 else "****"
                elif pii_type == "ssn":
                    return f"***-**-{value[-4:]}" if len(value) >= 4 else "***"
            
            # Default partial masking
            if len(value) > 4:
                return value[:2] + "*" * (len(value) - 4) + value[-2:]
            return "*" * len(value)
        
        elif strategy == "tokenize":
            # Tokenization (potentially reversible)
            token = hashlib.md5(f"{pii_type}:{value}".encode()).hexdigest()[:12]
            if self.config.reversible:
                # Store mapping for reversal (in production, use secure storage)
                self._cache[token] = value
            return f"[TOKEN:{token}]"
        
        # Default: hash
        hash_value = hashlib.sha256(value.encode()).hexdigest()[:8]
        return f"[{pii_type.upper()}:{hash_value}]"
    
    def _audit_pii_access(self, pii_report: Dict):
        """Audit PII access for compliance."""
        # In production, this would integrate with the audit logger
        logger.info(f"PII accessed: {json.dumps(pii_report, default=str)}")
    
    def validate_compliance(self, document: Dict) -> Dict:
        """
        Validate document compliance with privacy regulations.
        
        Args:
            document: Document to validate
            
        Returns:
            Compliance report
        """
        report = {
            'gdpr_compliant': True,
            'ccpa_compliant': True,
            'issues': [],
            'recommendations': []
        }
        
        # Check for unmasked PII
        content = document.get('content', '')
        _, pii_report = self.scan_document(content)
        
        if pii_report['pii_detected'] and pii_report['masked_count'] == 0:
            report['gdpr_compliant'] = False
            report['ccpa_compliant'] = False
            report['issues'].append("Unmasked PII detected in document")
            report['recommendations'].append("Enable PII masking for compliance")
        
        # Check retention policies
        if self.config.gdpr_mode:
            if 'retention_period' not in document:
                report['gdpr_compliant'] = False
                report['issues'].append("No retention period specified (GDPR requirement)")
                report['recommendations'].append("Set appropriate retention period")
        
        # Check consent tracking
        if self.config.ccpa_mode:
            if 'user_consent' not in document:
                report['ccpa_compliant'] = False
                report['issues'].append("No user consent tracked (CCPA requirement)")
                report['recommendations'].append("Implement consent tracking")
        
        return report
    
    def get_stats(self) -> Dict:
        """Get PII detection statistics."""
        stats = self._stats.copy()
        if self._stats['documents_scanned'] > 0:
            stats['detection_rate'] = self._stats['pii_found'] / self._stats['documents_scanned']
            stats['avg_processing_time'] = self._stats['processing_time'] / self._stats['documents_scanned']
        return stats
    
    def reset_stats(self):
        """Reset statistics."""
        self._stats = {
            'documents_scanned': 0,
            'pii_found': 0,
            'pii_masked': 0,
            'false_positives': 0,
            'processing_time': 0.0
        }
    
    def clear_cache(self):
        """Clear any cached PII data (for security)."""
        self._cache.clear()
        logger.info("PII cache cleared")