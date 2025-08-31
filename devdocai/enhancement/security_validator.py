"""
M009: Security Validator Module.

Provides comprehensive input validation, sanitization, and threat detection
for the Enhancement Pipeline. Prevents prompt injection, XSS, and other
security vulnerabilities while maintaining performance.
"""

import re
import html
import bleach
import hashlib
import secrets
import logging
from typing import Dict, List, Optional, Any, Tuple, Set, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import base64
from pathlib import Path

# Import M002's PII detector for content scanning
try:
    from devdocai.storage.pii_detector import PIIDetector, PIIType
    HAS_PII_DETECTOR = True
except ImportError:
    HAS_PII_DETECTOR = False

logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """Security threat levels."""
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class ValidationType(Enum):
    """Types of validation checks."""
    CONTENT_LENGTH = "content_length"
    CHARACTER_ENCODING = "character_encoding"
    MALICIOUS_PATTERNS = "malicious_patterns"
    PROMPT_INJECTION = "prompt_injection"
    XSS_PREVENTION = "xss_prevention"
    FILE_TYPE = "file_type"
    STRUCTURE_VALIDATION = "structure_validation"
    PII_DETECTION = "pii_detection"
    CONTENT_SANITIZATION = "content_sanitization"


class ValidationResult:
    """Result of security validation."""
    
    def __init__(
        self,
        is_valid: bool,
        threat_level: ThreatLevel = ThreatLevel.NONE,
        violations: List[str] = None,
        sanitized_content: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ):
        self.is_valid = is_valid
        self.threat_level = threat_level
        self.violations = violations or []
        self.sanitized_content = sanitized_content
        self.metadata = metadata or {}
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_valid": self.is_valid,
            "threat_level": self.threat_level.value,
            "violations": self.violations,
            "has_sanitized_content": self.sanitized_content is not None,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ValidationConfig:
    """Configuration for security validation."""
    
    # Content limits
    max_content_length: int = 1000000  # 1MB
    max_line_length: int = 10000
    max_lines: int = 50000
    
    # Character validation
    allowed_encodings: Set[str] = field(default_factory=lambda: {"utf-8", "ascii"})
    block_control_chars: bool = True
    allow_unicode: bool = True
    
    # Pattern detection
    enable_prompt_injection_detection: bool = True
    enable_xss_detection: bool = True
    enable_sql_injection_detection: bool = True
    enable_path_traversal_detection: bool = True
    
    # File type restrictions
    allowed_file_extensions: Set[str] = field(default_factory=lambda: {
        ".md", ".txt", ".rst", ".adoc", ".org", ".tex", ".html", ".xml", ".json", ".yaml", ".yml"
    })
    blocked_file_extensions: Set[str] = field(default_factory=lambda: {
        ".exe", ".bat", ".cmd", ".scr", ".vbs", ".js", ".ps1", ".sh", ".php", ".jsp"
    })
    
    # Content sanitization
    enable_html_sanitization: bool = True
    enable_url_sanitization: bool = True
    enable_script_removal: bool = True
    preserve_markdown: bool = True
    
    # PII detection
    enable_pii_detection: bool = True
    mask_pii: bool = True
    pii_threshold: float = 0.8
    
    # Advanced security
    enable_entropy_analysis: bool = True
    max_entropy_threshold: float = 7.5  # Detect potential obfuscated content
    enable_domain_validation: bool = True
    trusted_domains: Set[str] = field(default_factory=lambda: {
        "github.com", "stackoverflow.com", "docs.python.org", "readthedocs.io"
    })
    
    # Rate limiting integration
    validation_rate_limit: int = 1000  # Validations per minute
    
    @classmethod
    def for_security_level(cls, level: str) -> 'ValidationConfig':
        """Get configuration for specific security level."""
        configs = {
            "BASIC": cls(
                max_content_length=500000,
                enable_prompt_injection_detection=True,
                enable_xss_detection=True,
                enable_pii_detection=False
            ),
            "STANDARD": cls(
                max_content_length=1000000,
                enable_prompt_injection_detection=True,
                enable_xss_detection=True,
                enable_sql_injection_detection=True,
                enable_pii_detection=True
            ),
            "STRICT": cls(
                max_content_length=500000,
                max_line_length=5000,
                enable_prompt_injection_detection=True,
                enable_xss_detection=True,
                enable_sql_injection_detection=True,
                enable_path_traversal_detection=True,
                enable_pii_detection=True,
                max_entropy_threshold=6.0,
                enable_domain_validation=True
            ),
            "PARANOID": cls(
                max_content_length=100000,
                max_line_length=2000,
                max_lines=10000,
                block_control_chars=True,
                allow_unicode=False,
                enable_prompt_injection_detection=True,
                enable_xss_detection=True,
                enable_sql_injection_detection=True,
                enable_path_traversal_detection=True,
                enable_pii_detection=True,
                mask_pii=True,
                max_entropy_threshold=5.0,
                enable_domain_validation=True,
                allowed_file_extensions={".md", ".txt"}
            )
        }
        return configs.get(level, cls())


class SecurityValidator:
    """
    Comprehensive security validator for M009 Enhancement Pipeline.
    
    Provides input validation, sanitization, and threat detection to prevent
    prompt injection, XSS, data leakage, and other security vulnerabilities.
    """
    
    # Prompt injection patterns (expanded from research)
    PROMPT_INJECTION_PATTERNS = [
        # Direct instruction overrides
        r'(?i)ignore\s+(all\s+)?previous\s+instructions?',
        r'(?i)forget\s+(all\s+)?previous\s+(instructions?|context)',
        r'(?i)disregard\s+(all\s+)?previous\s+(instructions?|context)',
        r'(?i)override\s+(all\s+)?previous\s+(instructions?|context)',
        
        # System prompt manipulation
        r'(?i)system\s*:\s*.{1,100}',
        r'(?i)assistant\s*:\s*.{1,100}',
        r'(?i)human\s*:\s*.{1,100}',
        r'(?i)ai\s*:\s*.{1,100}',
        
        # Role-playing attacks
        r'(?i)pretend\s+(to\s+be|you\s+are)',
        r'(?i)act\s+as\s+if\s+you\s+are',
        r'(?i)behave\s+like',
        r'(?i)roleplay\s+as',
        
        # Instruction termination
        r'(?i)end\s+of\s+instructions?',
        r'(?i)new\s+instructions?',
        r'(?i)updated\s+instructions?',
        r'(?i)latest\s+instructions?',
        
        # Data extraction attempts
        r'(?i)show\s+me\s+your\s+(prompt|instructions?|system\s+message)',
        r'(?i)what\s+(are\s+your\s+)?instructions?',
        r'(?i)reveal\s+your\s+(prompt|instructions?)',
        r'(?i)print\s+your\s+(prompt|instructions?)',
        
        # Encoding/obfuscation attempts
        r'[\\x][0-9a-fA-F]{2}',  # Hex encoding
        r'\\[0-7]{3}',           # Octal encoding
        r'&#\d+;',               # HTML entities
        r'%[0-9a-fA-F]{2}',      # URL encoding
        
        # Jailbreak attempts
        r'(?i)jailbreak',
        r'(?i)developer\s+mode',
        r'(?i)god\s+mode',
        r'(?i)admin\s+mode',
        r'(?i)sudo\s+mode',
        
        # Template manipulation
        r'\{\{.*\}\}',           # Template injection
        r'\$\{.*\}',             # Variable substitution
        r'<%.*%>',               # ASP/JSP tags
        
        # LLM-specific attacks
        r'(?i)temperature\s*[=:]\s*[01]\.\d+',
        r'(?i)max_tokens\s*[=:]\s*\d+',
        r'(?i)stop\s*[=:]',
        r'(?i)model\s*[=:]',
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe[^>]*>',
        r'<object[^>]*>',
        r'<embed[^>]*>',
        r'<link[^>]*>',
        r'<meta[^>]*>',
        r'vbscript:',
        r'data:text/html',
        r'expression\s*\(',
    ]
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r'(?i)(union|select|insert|update|delete|drop|create|alter)\s+',
        r'(?i)(or|and)\s+\d+\s*=\s*\d+',
        r'(?i)(or|and)\s+\'\w*\'\s*=\s*\'\w*\'',
        r'(?i)exec\s*\(',
        r'(?i)xp_cmdshell',
        r';\s*--',
        r'/\*.*\*/',
    ]
    
    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r'\.\./|\.\.\\',
        r'/etc/passwd',
        r'/etc/shadow',
        r'C:\\Windows\\',
        r'%SYSTEMROOT%',
        r'$HOME',
        r'~/',
    ]
    
    def __init__(self, config: Optional[ValidationConfig] = None):
        """Initialize security validator."""
        self.config = config or ValidationConfig()
        
        # Initialize PII detector if available
        if HAS_PII_DETECTOR and self.config.enable_pii_detection:
            self.pii_detector = PIIDetector()
        else:
            self.pii_detector = None
        
        # Compile regex patterns for performance
        self._compile_patterns()
        
        # Metrics
        self.validation_count = 0
        self.threat_count = 0
        self.last_reset = datetime.now()
        
        logger.info(f"Security validator initialized with config: {type(self.config).__name__}")
    
    def _compile_patterns(self) -> None:
        """Compile regex patterns for better performance."""
        self.compiled_patterns = {
            'prompt_injection': [re.compile(pattern, re.MULTILINE | re.DOTALL) 
                               for pattern in self.PROMPT_INJECTION_PATTERNS],
            'xss': [re.compile(pattern, re.IGNORECASE | re.MULTILINE) 
                   for pattern in self.XSS_PATTERNS],
            'sql_injection': [re.compile(pattern, re.IGNORECASE | re.MULTILINE) 
                            for pattern in self.SQL_INJECTION_PATTERNS],
            'path_traversal': [re.compile(pattern, re.IGNORECASE) 
                             for pattern in self.PATH_TRAVERSAL_PATTERNS],
        }
    
    def validate_content(
        self,
        content: str,
        content_type: str = "text",
        file_path: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> ValidationResult:
        """
        Comprehensive content validation.
        
        Args:
            content: Content to validate
            content_type: Type of content (text, html, markdown, etc.)
            file_path: Optional file path for validation
            metadata: Additional metadata
            
        Returns:
            ValidationResult with validation status and details
        """
        start_time = datetime.now()
        violations = []
        threat_level = ThreatLevel.NONE
        sanitized_content = None
        validation_metadata = metadata or {}
        
        try:
            # Update metrics
            self.validation_count += 1
            
            # 1. Content length validation
            if len(content) > self.config.max_content_length:
                violations.append(f"Content exceeds maximum length: {len(content)} > {self.config.max_content_length}")
                threat_level = max(threat_level, ThreatLevel.MEDIUM)
            
            # 2. Line validation
            lines = content.split('\n')
            if len(lines) > self.config.max_lines:
                violations.append(f"Too many lines: {len(lines)} > {self.config.max_lines}")
                threat_level = max(threat_level, ThreatLevel.MEDIUM)
            
            for i, line in enumerate(lines):
                if len(line) > self.config.max_line_length:
                    violations.append(f"Line {i+1} exceeds maximum length: {len(line)} > {self.config.max_line_length}")
                    threat_level = max(threat_level, ThreatLevel.LOW)
                    break
            
            # 3. Character encoding validation
            encoding_result = self._validate_encoding(content)
            if not encoding_result["valid"]:
                violations.extend(encoding_result["violations"])
                threat_level = max(threat_level, ThreatLevel.LOW)
            
            # 4. Malicious pattern detection
            pattern_result = self._detect_malicious_patterns(content)
            if pattern_result["threats_found"]:
                violations.extend(pattern_result["violations"])
                threat_level = max(threat_level, pattern_result["max_threat_level"])
                self.threat_count += len(pattern_result["violations"])
            
            # 5. File type validation
            if file_path:
                file_result = self._validate_file_type(file_path)
                if not file_result["valid"]:
                    violations.extend(file_result["violations"])
                    threat_level = max(threat_level, ThreatLevel.HIGH)
            
            # 6. Entropy analysis (detect obfuscated content)
            if self.config.enable_entropy_analysis:
                entropy_result = self._analyze_entropy(content)
                if entropy_result["suspicious"]:
                    violations.append(f"High entropy content detected: {entropy_result['entropy']:.2f}")
                    threat_level = max(threat_level, ThreatLevel.MEDIUM)
                validation_metadata["entropy"] = entropy_result["entropy"]
            
            # 7. PII detection
            if self.pii_detector:
                pii_result = self._detect_pii(content)
                if pii_result["pii_found"]:
                    violations.extend(pii_result["violations"])
                    threat_level = max(threat_level, ThreatLevel.HIGH)
                    validation_metadata["pii_types"] = pii_result["pii_types"]
            
            # 8. Content sanitization
            if violations and threat_level in [ThreatLevel.LOW, ThreatLevel.MEDIUM]:
                sanitized_content = self._sanitize_content(content, content_type)
                validation_metadata["sanitized"] = True
            
            # 9. Domain validation
            if self.config.enable_domain_validation:
                domain_result = self._validate_domains(content)
                if domain_result["suspicious_domains"]:
                    violations.extend(domain_result["violations"])
                    threat_level = max(threat_level, ThreatLevel.MEDIUM)
                validation_metadata["domains_found"] = domain_result["domains_found"]
            
            # Determine if content is valid
            is_valid = (
                threat_level <= ThreatLevel.MEDIUM and
                len(violations) == 0 or 
                (sanitized_content is not None and threat_level <= ThreatLevel.MEDIUM)
            )
            
            # Add performance metrics
            validation_metadata.update({
                "validation_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
                "content_length": len(content),
                "lines_count": len(lines),
                "validation_count": self.validation_count
            })
            
            result = ValidationResult(
                is_valid=is_valid,
                threat_level=threat_level,
                violations=violations,
                sanitized_content=sanitized_content,
                metadata=validation_metadata
            )
            
            # Log security events
            if threat_level >= ThreatLevel.HIGH:
                logger.warning(f"High threat detected: {violations}")
            elif threat_level >= ThreatLevel.MEDIUM:
                logger.info(f"Medium threat detected: {violations}")
            
            return result
            
        except Exception as e:
            logger.error(f"Content validation failed: {e}")
            return ValidationResult(
                is_valid=False,
                threat_level=ThreatLevel.CRITICAL,
                violations=[f"Validation error: {str(e)}"],
                metadata=validation_metadata
            )
    
    def _validate_encoding(self, content: str) -> Dict[str, Any]:
        """Validate character encoding and detect suspicious characters."""
        violations = []
        
        try:
            # Check if content can be encoded/decoded properly
            content.encode('utf-8').decode('utf-8')
        except UnicodeError:
            violations.append("Invalid UTF-8 encoding detected")
        
        # Check for control characters (if enabled)
        if self.config.block_control_chars:
            control_chars = [c for c in content if ord(c) < 32 and c not in '\t\n\r']
            if control_chars:
                violations.append(f"Control characters detected: {len(control_chars)} instances")
        
        # Check for non-unicode characters (if not allowed)
        if not self.config.allow_unicode:
            non_ascii = [c for c in content if ord(c) > 127]
            if non_ascii:
                violations.append(f"Non-ASCII characters detected: {len(non_ascii)} instances")
        
        return {
            "valid": len(violations) == 0,
            "violations": violations
        }
    
    def _detect_malicious_patterns(self, content: str) -> Dict[str, Any]:
        """Detect malicious patterns in content."""
        violations = []
        max_threat_level = ThreatLevel.NONE
        threats_found = 0
        
        # Prompt injection detection
        if self.config.enable_prompt_injection_detection:
            for pattern in self.compiled_patterns['prompt_injection']:
                matches = pattern.findall(content)
                if matches:
                    violations.append(f"Prompt injection pattern detected: {pattern.pattern[:50]}...")
                    max_threat_level = max(max_threat_level, ThreatLevel.HIGH)
                    threats_found += len(matches)
        
        # XSS detection
        if self.config.enable_xss_detection:
            for pattern in self.compiled_patterns['xss']:
                matches = pattern.findall(content)
                if matches:
                    violations.append(f"XSS pattern detected: {pattern.pattern[:50]}...")
                    max_threat_level = max(max_threat_level, ThreatLevel.HIGH)
                    threats_found += len(matches)
        
        # SQL injection detection
        if self.config.enable_sql_injection_detection:
            for pattern in self.compiled_patterns['sql_injection']:
                matches = pattern.findall(content)
                if matches:
                    violations.append(f"SQL injection pattern detected: {pattern.pattern[:50]}...")
                    max_threat_level = max(max_threat_level, ThreatLevel.MEDIUM)
                    threats_found += len(matches)
        
        # Path traversal detection
        if self.config.enable_path_traversal_detection:
            for pattern in self.compiled_patterns['path_traversal']:
                matches = pattern.findall(content)
                if matches:
                    violations.append(f"Path traversal pattern detected: {pattern.pattern[:50]}...")
                    max_threat_level = max(max_threat_level, ThreatLevel.HIGH)
                    threats_found += len(matches)
        
        return {
            "threats_found": threats_found > 0,
            "violations": violations,
            "max_threat_level": max_threat_level,
            "threat_count": threats_found
        }
    
    def _validate_file_type(self, file_path: str) -> Dict[str, Any]:
        """Validate file type and extension."""
        violations = []
        path = Path(file_path)
        extension = path.suffix.lower()
        
        # Check blocked extensions
        if extension in self.config.blocked_file_extensions:
            violations.append(f"Blocked file extension: {extension}")
        
        # Check allowed extensions
        if self.config.allowed_file_extensions and extension not in self.config.allowed_file_extensions:
            violations.append(f"File extension not allowed: {extension}")
        
        return {
            "valid": len(violations) == 0,
            "violations": violations
        }
    
    def _analyze_entropy(self, content: str) -> Dict[str, Any]:
        """Analyze content entropy to detect obfuscated content."""
        if not content:
            return {"entropy": 0.0, "suspicious": False}
        
        # Calculate Shannon entropy
        char_counts = {}
        for char in content:
            char_counts[char] = char_counts.get(char, 0) + 1
        
        entropy = 0.0
        content_length = len(content)
        
        for count in char_counts.values():
            probability = count / content_length
            entropy -= probability * (probability.bit_length() - 1) if probability > 0 else 0
        
        suspicious = entropy > self.config.max_entropy_threshold
        
        return {
            "entropy": entropy,
            "suspicious": suspicious
        }
    
    def _detect_pii(self, content: str) -> Dict[str, Any]:
        """Detect PII in content using M002's PII detector."""
        if not self.pii_detector:
            return {"pii_found": False, "violations": [], "pii_types": []}
        
        try:
            pii_result = self.pii_detector.detect_pii(content)
            
            pii_found = pii_result.confidence > self.config.pii_threshold
            violations = []
            pii_types = []
            
            if pii_found:
                for detection in pii_result.detections:
                    violations.append(f"PII detected: {detection.pii_type.value} (confidence: {detection.confidence:.2f})")
                    pii_types.append(detection.pii_type.value)
            
            return {
                "pii_found": pii_found,
                "violations": violations,
                "pii_types": pii_types
            }
        except Exception as e:
            logger.warning(f"PII detection failed: {e}")
            return {"pii_found": False, "violations": [], "pii_types": []}
    
    def _validate_domains(self, content: str) -> Dict[str, Any]:
        """Validate domains found in content."""
        # Simple domain extraction (URLs)
        url_pattern = re.compile(r'https?://([a-zA-Z0-9.-]+)')
        domains_found = url_pattern.findall(content)
        
        suspicious_domains = []
        violations = []
        
        for domain in set(domains_found):  # Remove duplicates
            if domain not in self.config.trusted_domains:
                # Check for suspicious characteristics
                if (len(domain.split('.')) > 4 or  # Too many subdomains
                    any(char.isdigit() for char in domain.replace('.', '')) and 
                    len(domain.replace('.', '').replace('-', '')) < 10):  # Short with numbers
                    suspicious_domains.append(domain)
                    violations.append(f"Suspicious domain detected: {domain}")
        
        return {
            "domains_found": list(set(domains_found)),
            "suspicious_domains": suspicious_domains,
            "violations": violations
        }
    
    def _sanitize_content(self, content: str, content_type: str) -> str:
        """Sanitize content to remove threats while preserving functionality."""
        sanitized = content
        
        # HTML sanitization
        if self.config.enable_html_sanitization:
            # Use bleach to remove dangerous tags and attributes robustly
            allowed_tags = getattr(self.config, 'allowed_html_tags', [
                'b', 'i', 'u', 'em', 'strong', 'a', 'code', 'pre', 'br', 'p', 'ul', 'li', 'ol', 'span'
            ])
            allowed_attributes = getattr(self.config, 'allowed_html_attributes', {
                'a': ['href', 'title'],
                'span': ['style'],
                'p': ['style'],
            })
            strip = True
            sanitized = bleach.clean(
                sanitized,
                tags=allowed_tags,
                attributes=allowed_attributes,
                strip=strip,
            )
        
        # URL sanitization
        if self.config.enable_url_sanitization:
            sanitized = re.sub(r'javascript:', 'blocked:', sanitized, flags=re.IGNORECASE)
            sanitized = re.sub(r'vbscript:', 'blocked:', sanitized, flags=re.IGNORECASE)
            sanitized = re.sub(r'data:text/html', 'data:text/plain', sanitized, flags=re.IGNORECASE)
        
        # Remove potential prompt injections (be conservative)
        for pattern in self.compiled_patterns['prompt_injection'][:5]:  # Only most dangerous ones
            sanitized = pattern.sub('[BLOCKED]', sanitized)
        
        return sanitized
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        uptime = (datetime.now() - self.last_reset).total_seconds()
        
        return {
            "validation_count": self.validation_count,
            "threat_count": self.threat_count,
            "threat_ratio": self.threat_count / max(self.validation_count, 1),
            "validations_per_second": self.validation_count / max(uptime, 1),
            "uptime_seconds": uptime,
            "last_reset": self.last_reset.isoformat()
        }
    
    def reset_stats(self) -> None:
        """Reset validation statistics."""
        self.validation_count = 0
        self.threat_count = 0
        self.last_reset = datetime.now()
        logger.info("Validation statistics reset")


def create_validator(security_level: str = "STANDARD") -> SecurityValidator:
    """
    Factory function to create security validator.
    
    Args:
        security_level: Security level (BASIC, STANDARD, STRICT, PARANOID)
        
    Returns:
        Configured SecurityValidator
    """
    config = ValidationConfig.for_security_level(security_level)
    return SecurityValidator(config)