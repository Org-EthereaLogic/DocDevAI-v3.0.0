"""
PII Detection module for M002 Local Storage System.

Provides regex-based detection and protection for personally identifiable information
including SSN, credit cards, emails, phone numbers, and other sensitive data patterns.
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Set, Any
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class PIIType(str, Enum):
    """Types of PII that can be detected."""
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    EMAIL = "email"
    PHONE = "phone"
    IP_ADDRESS = "ip_address"
    DATE_OF_BIRTH = "date_of_birth"
    PASSPORT = "passport"
    DRIVER_LICENSE = "driver_license"
    BANK_ACCOUNT = "bank_account"
    API_KEY = "api_key"
    AWS_KEY = "aws_key"
    PRIVATE_KEY = "private_key"
    PASSWORD = "password"
    MEDICAL_RECORD = "medical_record"
    PERSON_NAME = "person_name"
    ADDRESS = "address"
    IBAN = "iban"
    BITCOIN_ADDRESS = "bitcoin_address"
    ETHEREUM_ADDRESS = "ethereum_address"


@dataclass
class PIIMatch:
    """Represents a detected PII match."""
    pii_type: PIIType
    value: str
    start: int
    end: int
    confidence: float
    context: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'type': self.pii_type.value,
            'value': self.value,
            'position': {'start': self.start, 'end': self.end},
            'confidence': self.confidence,
            'context': self.context
        }


@dataclass
class PIIDetectionConfig:
    """Configuration for PII detection."""
    enabled_types: Set[PIIType] = field(default_factory=lambda: set(PIIType))
    min_confidence: float = 0.7
    mask_character: str = "*"
    preserve_length: bool = True
    preserve_partial: int = 4  # Number of characters to preserve at end
    context_window: int = 20  # Characters around PII to include in context
    custom_patterns: Dict[str, str] = field(default_factory=dict)


class PIIDetector:
    """
    High-performance PII detection and masking.
    
    Uses compiled regex patterns for efficient detection of various PII types
    with configurable confidence thresholds and masking options.
    """
    
    def __init__(self, config: Optional[PIIDetectionConfig] = None):
        """Initialize PII detector with configuration."""
        self.config = config or PIIDetectionConfig()
        self.patterns = self._compile_patterns()
        self.detection_count = 0
        self.mask_count = 0
    
    def _compile_patterns(self) -> Dict[PIIType, List[Tuple[re.Pattern, float]]]:
        """Compile regex patterns for each PII type with confidence scores."""
        patterns = {}
        
        # Social Security Number (US)
        patterns[PIIType.SSN] = [
            (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), 0.95),  # Format: 123-45-6789
            (re.compile(r'\b\d{3}\s\d{2}\s\d{4}\b'), 0.90),  # Format: 123 45 6789
            (re.compile(r'\b\d{9}\b'), 0.60),  # Format: 123456789 (lower confidence)
        ]
        
        # Credit Card Numbers
        patterns[PIIType.CREDIT_CARD] = [
            # Visa (starts with 4)
            (re.compile(r'\b4[0-9]{3}[\s-]?[0-9]{4}[\s-]?[0-9]{4}[\s-]?[0-9]{4}\b'), 0.95),
            # Mastercard (starts with 51-55 or 2221-2720)
            (re.compile(r'\b5[1-5][0-9]{2}[\s-]?[0-9]{4}[\s-]?[0-9]{4}[\s-]?[0-9]{4}\b'), 0.95),
            # American Express (starts with 34 or 37)
            (re.compile(r'\b3[47][0-9]{2}[\s-]?[0-9]{6}[\s-]?[0-9]{5}\b'), 0.95),
            # Generic 16-digit pattern
            (re.compile(r'\b[0-9]{4}[\s-]?[0-9]{4}[\s-]?[0-9]{4}[\s-]?[0-9]{4}\b'), 0.70),
        ]
        
        # Email Addresses
        patterns[PIIType.EMAIL] = [
            (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), 0.95),
        ]
        
        # Phone Numbers (US and International)
        patterns[PIIType.PHONE] = [
            # US format with country code
            (re.compile(r'\b\+?1?[\s-]?\(?[0-9]{3}\)?[\s-]?[0-9]{3}[\s-]?[0-9]{4}\b'), 0.90),
            # International format
            (re.compile(r'\b\+[0-9]{1,3}[\s-]?[0-9]{4,14}\b'), 0.85),
            # Generic 10-digit
            (re.compile(r'\b[0-9]{3}[\s-]?[0-9]{3}[\s-]?[0-9]{4}\b'), 0.80),
        ]
        
        # IP Addresses
        patterns[PIIType.IP_ADDRESS] = [
            # IPv4
            (re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'), 0.90),
            # IPv6
            (re.compile(r'\b(?:[A-Fa-f0-9]{1,4}:){7}[A-Fa-f0-9]{1,4}\b'), 0.95),
        ]
        
        # Date of Birth patterns
        patterns[PIIType.DATE_OF_BIRTH] = [
            # MM/DD/YYYY or MM-DD-YYYY
            (re.compile(r'\b(?:0[1-9]|1[0-2])[-/](?:0[1-9]|[12][0-9]|3[01])[-/](?:19|20)\d{2}\b'), 0.85),
            # YYYY-MM-DD (ISO format)
            (re.compile(r'\b(?:19|20)\d{2}[-/](?:0[1-9]|1[0-2])[-/](?:0[1-9]|[12][0-9]|3[01])\b'), 0.85),
        ]
        
        # Passport Numbers (various formats)
        patterns[PIIType.PASSPORT] = [
            # US Passport (9 digits)
            (re.compile(r'\b[0-9]{9}\b'), 0.50),
            # UK Passport
            (re.compile(r'\b[0-9]{9}[A-Z]{3}[0-9]{7}\b'), 0.90),
            # Generic alphanumeric 6-9 characters
            (re.compile(r'\b[A-Z][0-9]{6,8}\b'), 0.60),
        ]
        
        # Bank Account Numbers (IBAN)
        patterns[PIIType.IBAN] = [
            (re.compile(r'\b[A-Z]{2}[0-9]{2}[A-Z0-9]{4}[0-9]{7}([A-Z0-9]?){0,16}\b'), 0.95),
        ]
        
        # API Keys and Secrets
        patterns[PIIType.API_KEY] = [
            # Generic API key patterns
            (re.compile(r'\b[A-Za-z0-9]{32,}\b'), 0.60),
            # With prefix
            (re.compile(r'(?:api[_-]?key|apikey|api[_-]?secret)[\s=:]+[\'"]?([A-Za-z0-9+/]{20,})[\'"]?', re.IGNORECASE), 0.90),
        ]
        
        # AWS Keys
        patterns[PIIType.AWS_KEY] = [
            # AWS Access Key ID
            (re.compile(r'\bAKIA[0-9A-Z]{16}\b'), 0.95),
            # AWS Secret Access Key
            (re.compile(r'\b[A-Za-z0-9+/]{40}\b'), 0.50),
        ]
        
        # Private Keys
        patterns[PIIType.PRIVATE_KEY] = [
            # RSA Private Key Header
            (re.compile(r'-----BEGIN (?:RSA )?PRIVATE KEY-----'), 0.99),
            # SSH Private Key
            (re.compile(r'-----BEGIN OPENSSH PRIVATE KEY-----'), 0.99),
        ]
        
        # Password patterns (in configuration files or logs)
        patterns[PIIType.PASSWORD] = [
            (re.compile(r'(?:password|passwd|pwd)[\s=:]+[\'"]?([^\s\'"]+)[\'"]?', re.IGNORECASE), 0.80),
        ]
        
        # Bitcoin Address
        patterns[PIIType.BITCOIN_ADDRESS] = [
            # Legacy (P2PKH)
            (re.compile(r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b'), 0.90),
            # SegWit (Bech32)
            (re.compile(r'\bbc1[a-z0-9]{39,59}\b'), 0.95),
        ]
        
        # Ethereum Address
        patterns[PIIType.ETHEREUM_ADDRESS] = [
            (re.compile(r'\b0x[a-fA-F0-9]{40}\b'), 0.95),
        ]
        
        # Add custom patterns from config
        for name, pattern in self.config.custom_patterns.items():
            custom_type = PIIType.OTHER  # Map to OTHER or create custom type
            if custom_type not in patterns:
                patterns[custom_type] = []
            patterns[custom_type].append((re.compile(pattern), 0.75))
        
        # Filter patterns based on enabled types
        if self.config.enabled_types:
            patterns = {k: v for k, v in patterns.items() if k in self.config.enabled_types}
        
        return patterns
    
    def detect(self, text: str) -> List[PIIMatch]:
        """
        Detect PII in text.
        
        Args:
            text: Text to scan for PII
            
        Returns:
            List of PII matches found
        """
        if not text:
            return []
        
        matches = []
        seen_positions = set()  # Avoid duplicate detections
        
        for pii_type, pattern_list in self.patterns.items():
            for pattern, confidence in pattern_list:
                for match in pattern.finditer(text):
                    # Skip if already detected at this position
                    pos_key = (match.start(), match.end())
                    if pos_key in seen_positions:
                        continue
                    
                    # Check confidence threshold
                    if confidence < self.config.min_confidence:
                        continue
                    
                    # Extract context
                    context_start = max(0, match.start() - self.config.context_window)
                    context_end = min(len(text), match.end() + self.config.context_window)
                    context = text[context_start:context_end]
                    
                    # Additional validation for specific types
                    if pii_type == PIIType.CREDIT_CARD:
                        if not self._validate_credit_card(match.group()):
                            continue
                    
                    pii_match = PIIMatch(
                        pii_type=pii_type,
                        value=match.group(),
                        start=match.start(),
                        end=match.end(),
                        confidence=confidence,
                        context=context
                    )
                    
                    matches.append(pii_match)
                    seen_positions.add(pos_key)
        
        self.detection_count += len(matches)
        return sorted(matches, key=lambda x: x.start)
    
    def mask(self, text: str, matches: Optional[List[PIIMatch]] = None) -> str:
        """
        Mask PII in text.
        
        Args:
            text: Text containing PII
            matches: Pre-detected matches (if None, will detect)
            
        Returns:
            Text with PII masked
        """
        if not text:
            return text
        
        # Detect PII if not provided
        if matches is None:
            matches = self.detect(text)
        
        if not matches:
            return text
        
        # Sort matches by position (reverse order for replacement)
        matches = sorted(matches, key=lambda x: x.start, reverse=True)
        
        masked_text = text
        for match in matches:
            masked_value = self._create_mask(match.value, match.pii_type)
            masked_text = masked_text[:match.start] + masked_value + masked_text[match.end:]
            self.mask_count += 1
        
        return masked_text
    
    def _create_mask(self, value: str, pii_type: PIIType) -> str:
        """Create masked version of PII value."""
        if not self.config.preserve_length:
            # Fixed length mask
            return self.config.mask_character * 8
        
        length = len(value)
        
        if self.config.preserve_partial > 0 and length > self.config.preserve_partial:
            # Preserve last N characters
            mask_length = length - self.config.preserve_partial
            return self.config.mask_character * mask_length + value[-self.config.preserve_partial:]
        else:
            # Full mask
            return self.config.mask_character * length
    
    def _validate_credit_card(self, number: str) -> bool:
        """Validate credit card number using Luhn algorithm."""
        # Remove spaces and dashes
        number = re.sub(r'[\s-]', '', number)
        
        if not number.isdigit():
            return False
        
        # Luhn algorithm
        total = 0
        reverse_digits = number[::-1]
        
        for i, digit in enumerate(reverse_digits):
            n = int(digit)
            if i % 2 == 1:
                n *= 2
                if n > 9:
                    n -= 9
            total += n
        
        return total % 10 == 0
    
    def scan_document(self, document: Dict[str, Any]) -> Dict[str, List[PIIMatch]]:
        """
        Scan document fields for PII.
        
        Args:
            document: Document dictionary
            
        Returns:
            Dictionary mapping field names to PII matches
        """
        results = {}
        
        # Fields to scan
        text_fields = ['content', 'title', 'description', 'summary']
        
        for field in text_fields:
            if field in document and document[field]:
                matches = self.detect(str(document[field]))
                if matches:
                    results[field] = matches
        
        # Scan metadata if present
        if 'metadata' in document and isinstance(document['metadata'], dict):
            for key, value in document['metadata'].items():
                if value:
                    matches = self.detect(str(value))
                    if matches:
                        results[f'metadata.{key}'] = matches
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get detection statistics."""
        return {
            'detection_count': self.detection_count,
            'mask_count': self.mask_count,
            'enabled_types': [t.value for t in self.config.enabled_types] if self.config.enabled_types else 'all',
            'min_confidence': self.config.min_confidence
        }
    
    def create_audit_record(self, document_id: int, matches: List[PIIMatch]) -> Dict[str, Any]:
        """Create audit record for PII detection."""
        return {
            'document_id': document_id,
            'timestamp': __import__('datetime').datetime.utcnow().isoformat(),
            'pii_detected': len(matches) > 0,
            'pii_count': len(matches),
            'pii_types': list(set(m.pii_type.value for m in matches)),
            'matches': [m.to_dict() for m in matches]
        }