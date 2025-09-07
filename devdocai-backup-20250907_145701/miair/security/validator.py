"""
M003 MIAIR Engine - Security Input Validator

Comprehensive input validation and sanitization for the MIAIR Engine.
Protects against malicious document payloads, injection attacks, and resource exhaustion.

Security Features:
- Document content validation and sanitization
- Size and complexity limits
- Pattern-based threat detection
- Schema validation for all inputs
- XSS and injection prevention
- Resource usage monitoring
"""

import re
import logging
import hashlib
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import html
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """Threat severity levels for security events."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ValidationError(Exception):
    """Raised when input validation fails."""
    def __init__(self, message: str, threat_level: ThreatLevel = ThreatLevel.MEDIUM):
        super().__init__(message)
        self.threat_level = threat_level


@dataclass
class ValidationConfig:
    """Configuration for input validation."""
    max_document_size: int = 10 * 1024 * 1024  # 10MB
    max_document_lines: int = 100000  # 100k lines
    max_line_length: int = 10000  # 10k chars per line
    max_entropy_iterations: int = 1000
    max_batch_size: int = 100
    enable_html_sanitization: bool = True
    enable_pattern_detection: bool = True
    enable_size_limits: bool = True
    enable_schema_validation: bool = True
    blocked_patterns: List[str] = None
    allowed_mime_types: List[str] = None
    
    def __post_init__(self):
        if self.blocked_patterns is None:
            # Default malicious patterns to block
            self.blocked_patterns = [
                r'<script[^>]*>.*?</script>',  # Script tags
                r'javascript:',  # JavaScript protocol
                r'on\w+\s*=',  # Event handlers
                r'<iframe[^>]*>',  # Iframes
                r'<object[^>]*>',  # Object tags
                r'<embed[^>]*>',  # Embed tags
                r'eval\s*\(',  # Eval function
                r'document\.write',  # Document write
                r'window\.location',  # Location manipulation
                r'\x00',  # Null bytes
                r'\.\./',  # Path traversal
                r'%2e%2e/',  # URL encoded path traversal
            ]
        
        if self.allowed_mime_types is None:
            self.allowed_mime_types = [
                'text/plain',
                'text/markdown',
                'text/html',
                'text/xml',
                'application/json',
                'application/xml',
            ]


class InputValidator:
    """
    Comprehensive input validator for MIAIR Engine security.
    
    Provides multi-layer validation:
    1. Size and complexity limits
    2. Content sanitization
    3. Pattern-based threat detection
    4. Schema validation
    5. Resource monitoring
    """
    
    def __init__(self, config: Optional[ValidationConfig] = None):
        """Initialize validator with configuration."""
        self.config = config or ValidationConfig()
        self.validation_stats = {
            'total_validations': 0,
            'passed': 0,
            'failed': 0,
            'threats_detected': 0,
            'bytes_processed': 0
        }
        self._compiled_patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> List[re.Pattern]:
        """Pre-compile regex patterns for performance."""
        compiled = []
        for pattern in self.config.blocked_patterns:
            try:
                compiled.append(re.compile(pattern, re.IGNORECASE | re.DOTALL))
            except re.error as e:
                logger.warning(f"Failed to compile pattern {pattern}: {e}")
        return compiled
    
    def validate_document(self, content: str, metadata: Optional[Dict] = None) -> Tuple[str, Dict]:
        """
        Validate and sanitize document content.
        
        Args:
            content: Document content to validate
            metadata: Optional document metadata
            
        Returns:
            Tuple of (sanitized_content, validation_report)
            
        Raises:
            ValidationError: If validation fails
        """
        self.validation_stats['total_validations'] += 1
        validation_report = {
            'threats_detected': [],
            'sanitizations_applied': [],
            'size_metrics': {},
            'passed': True
        }
        
        try:
            # Step 1: Size validation
            if self.config.enable_size_limits:
                self._validate_size(content, validation_report)
            
            # Step 2: Complexity validation
            self._validate_complexity(content, validation_report)
            
            # Step 3: Pattern-based threat detection
            if self.config.enable_pattern_detection:
                threats = self._detect_threats(content)
                if threats:
                    validation_report['threats_detected'] = threats
                    if any(t['level'] in [ThreatLevel.HIGH, ThreatLevel.CRITICAL] for t in threats):
                        raise ValidationError(
                            f"Critical threats detected: {threats[0]['description']}",
                            ThreatLevel.CRITICAL
                        )
            
            # Step 4: Content sanitization
            if self.config.enable_html_sanitization:
                sanitized = self._sanitize_content(content)
                if sanitized != content:
                    validation_report['sanitizations_applied'].append('html_escape')
                    content = sanitized
            
            # Step 5: Schema validation (if metadata provided)
            if self.config.enable_schema_validation and metadata:
                self._validate_schema(metadata, validation_report)
            
            self.validation_stats['passed'] += 1
            self.validation_stats['bytes_processed'] += len(content)
            
            return content, validation_report
            
        except ValidationError:
            self.validation_stats['failed'] += 1
            validation_report['passed'] = False
            raise
        except Exception as e:
            self.validation_stats['failed'] += 1
            validation_report['passed'] = False
            raise ValidationError(f"Unexpected validation error: {e}", ThreatLevel.HIGH)
    
    def _validate_size(self, content: str, report: Dict) -> None:
        """Validate document size constraints."""
        size_bytes = len(content.encode('utf-8'))
        lines = content.count('\n') + 1
        max_line_len = max((len(line) for line in content.split('\n')), default=0)
        
        report['size_metrics'] = {
            'bytes': size_bytes,
            'lines': lines,
            'max_line_length': max_line_len
        }
        
        if size_bytes > self.config.max_document_size:
            raise ValidationError(
                f"Document too large: {size_bytes} bytes (max: {self.config.max_document_size})",
                ThreatLevel.MEDIUM
            )
        
        if lines > self.config.max_document_lines:
            raise ValidationError(
                f"Document has too many lines: {lines} (max: {self.config.max_document_lines})",
                ThreatLevel.LOW
            )
        
        if max_line_len > self.config.max_line_length:
            raise ValidationError(
                f"Line too long: {max_line_len} chars (max: {self.config.max_line_length})",
                ThreatLevel.LOW
            )
    
    def _validate_complexity(self, content: str, report: Dict) -> None:
        """Check for complexity-based attacks (e.g., zip bombs, nested structures)."""
        # Check for excessive repetition (potential compression bomb)
        if len(content) > 1000:
            compressed_size = len(content.encode('utf-8'))
            uncompressed_estimate = self._estimate_uncompressed_size(content)
            compression_ratio = uncompressed_estimate / compressed_size if compressed_size > 0 else 1
            
            if compression_ratio > 100:  # Suspicious compression ratio
                raise ValidationError(
                    f"Suspicious compression ratio: {compression_ratio:.2f}",
                    ThreatLevel.HIGH
                )
        
        # Check for excessive nesting (potential parser DoS)
        nesting_depth = self._calculate_nesting_depth(content)
        if nesting_depth > 50:
            raise ValidationError(
                f"Excessive nesting depth: {nesting_depth}",
                ThreatLevel.MEDIUM
            )
    
    def _detect_threats(self, content: str) -> List[Dict]:
        """Detect potential threats using pattern matching."""
        threats = []
        
        for pattern in self._compiled_patterns:
            matches = pattern.findall(content)
            if matches:
                threat = {
                    'pattern': pattern.pattern,
                    'matches': len(matches),
                    'description': self._get_threat_description(pattern.pattern),
                    'level': self._get_threat_level(pattern.pattern)
                }
                threats.append(threat)
                self.validation_stats['threats_detected'] += 1
        
        return threats
    
    def _sanitize_content(self, content: str) -> str:
        """Sanitize content to prevent XSS and injection attacks."""
        # HTML escape dangerous characters
        sanitized = html.escape(content, quote=True)
        
        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')
        
        # Normalize Unicode to prevent homograph attacks
        import unicodedata
        sanitized = unicodedata.normalize('NFKC', sanitized)
        
        return sanitized
    
    def _validate_schema(self, metadata: Dict, report: Dict) -> None:
        """Validate metadata against expected schema."""
        required_fields = ['document_id', 'source', 'timestamp']
        allowed_fields = required_fields + ['author', 'version', 'tags', 'format']
        
        # Check required fields
        for field in required_fields:
            if field not in metadata:
                raise ValidationError(
                    f"Missing required metadata field: {field}",
                    ThreatLevel.LOW
                )
        
        # Check for unexpected fields (potential injection)
        unexpected = set(metadata.keys()) - set(allowed_fields)
        if unexpected:
            report['sanitizations_applied'].append(f"removed_fields: {unexpected}")
            for field in unexpected:
                del metadata[field]
    
    def _estimate_uncompressed_size(self, content: str) -> int:
        """Estimate uncompressed size to detect compression bombs."""
        # Simple heuristic: count unique vs repeated segments
        chunk_size = 100
        chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
        unique_chunks = len(set(chunks))
        total_chunks = len(chunks)
        
        if total_chunks > 0:
            uniqueness_ratio = unique_chunks / total_chunks
            # If very low uniqueness, likely compressed/repeated
            if uniqueness_ratio < 0.1:
                return len(content) * 10  # Estimate 10x expansion
        
        return len(content)
    
    def _calculate_nesting_depth(self, content: str) -> int:
        """Calculate maximum nesting depth in structured content."""
        max_depth = 0
        current_depth = 0
        
        # Simple bracket/brace counting for JSON/XML-like structures
        for char in content:
            if char in '{[<':
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char in '}]>':
                current_depth = max(0, current_depth - 1)
        
        return max_depth
    
    def _get_threat_description(self, pattern: str) -> str:
        """Get human-readable description for threat pattern."""
        descriptions = {
            r'<script[^>]*>.*?</script>': 'Script injection attempt',
            r'javascript:': 'JavaScript protocol handler',
            r'on\w+\s*=': 'Event handler injection',
            r'<iframe[^>]*>': 'IFrame injection',
            r'eval\s*\(': 'Eval function usage',
            r'\.\./' : 'Path traversal attempt',
            r'\x00': 'Null byte injection'
        }
        
        for p, desc in descriptions.items():
            if p in pattern:
                return desc
        return 'Suspicious pattern detected'
    
    def _get_threat_level(self, pattern: str) -> ThreatLevel:
        """Determine threat level for pattern."""
        critical_patterns = [r'eval\s*\(', r'<script', r'javascript:']
        high_patterns = [r'on\w+\s*=', r'<iframe', r'\.\./', r'\x00']
        
        for p in critical_patterns:
            if p in pattern:
                return ThreatLevel.CRITICAL
        
        for p in high_patterns:
            if p in pattern:
                return ThreatLevel.HIGH
        
        return ThreatLevel.MEDIUM
    
    def validate_batch(self, documents: List[Dict]) -> List[Tuple[Dict, Dict]]:
        """
        Validate a batch of documents.
        
        Args:
            documents: List of documents with 'content' and optional 'metadata'
            
        Returns:
            List of (sanitized_document, validation_report) tuples
        """
        if len(documents) > self.config.max_batch_size:
            raise ValidationError(
                f"Batch too large: {len(documents)} (max: {self.config.max_batch_size})",
                ThreatLevel.LOW
            )
        
        results = []
        for doc in documents:
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})
            
            try:
                sanitized, report = self.validate_document(content, metadata)
                doc_copy = doc.copy()
                doc_copy['content'] = sanitized
                results.append((doc_copy, report))
            except ValidationError as e:
                # Include failed validations with error info
                report = {
                    'passed': False,
                    'error': str(e),
                    'threat_level': e.threat_level.value
                }
                results.append((doc, report))
        
        return results
    
    def get_stats(self) -> Dict:
        """Get validation statistics."""
        return self.validation_stats.copy()
    
    def reset_stats(self) -> None:
        """Reset validation statistics."""
        self.validation_stats = {
            'total_validations': 0,
            'passed': 0,
            'failed': 0,
            'threats_detected': 0,
            'bytes_processed': 0
        }