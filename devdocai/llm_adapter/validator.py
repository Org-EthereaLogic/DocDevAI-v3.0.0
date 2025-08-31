"""
M008: Input Validation and Sanitization Module.

Provides comprehensive input validation, sanitization, and schema validation
for all LLM requests to prevent injection attacks and ensure data integrity.
"""

import re
import bleach
import json
import hashlib
import logging
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Security validation levels."""
    MINIMAL = "minimal"      # Basic length/type checks
    STANDARD = "standard"    # Standard validation + basic injection detection
    STRICT = "strict"        # Full validation + advanced injection prevention
    PARANOID = "paranoid"    # Maximum security, may reject legitimate requests


class ThreatType(Enum):
    """Types of security threats detected."""
    PROMPT_INJECTION = "prompt_injection"
    COMMAND_INJECTION = "command_injection"
    SQL_INJECTION = "sql_injection"
    XSS_ATTEMPT = "xss_attempt"
    JAILBREAK_ATTEMPT = "jailbreak_attempt"
    DATA_EXFILTRATION = "data_exfiltration"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    ENCODING_ATTACK = "encoding_attack"
    MODEL_MANIPULATION = "model_manipulation"


@dataclass
class ValidationResult:
    """Result of input validation."""
    is_valid: bool
    sanitized_input: Optional[str] = None
    threats_detected: List[ThreatType] = None
    risk_score: float = 0.0
    error_message: Optional[str] = None
    recommendations: List[str] = None
    
    def __post_init__(self):
        if self.threats_detected is None:
            self.threats_detected = []
        if self.recommendations is None:
            self.recommendations = []


class InputValidator:
    """
    Comprehensive input validation for LLM requests.
    
    Implements multi-layer defense against:
    - Prompt injection attacks
    - Command injection attempts
    - Jailbreak attempts
    - Data exfiltration
    - Resource exhaustion attacks
    """
    
    # Known malicious patterns
    INJECTION_PATTERNS = [
        # Prompt injection patterns
        r"(?i)ignore\s+(?:previous|prior|above)\s+(?:instructions?|commands?)",
        r"(?i)disregard\s+(?:all|previous|prior)\s+(?:instructions?|rules?)",
        r"(?i)forget\s+(?:everything|all|previous)",
        r"(?i)new\s+(?:instructions?|rules?|system\s+prompt)",
        r"(?i)you\s+are\s+now\s+(?:a|an|the)",
        r"(?i)pretend\s+(?:to\s+be|you\s+are)",
        r"(?i)act\s+(?:as|like)\s+(?:a|an|the)",
        r"(?i)roleplay\s+as",
        r"(?i)from\s+now\s+on",
        r"(?i)override\s+(?:your|the)\s+(?:instructions?|programming|rules?)",
        
        # Command injection patterns
        r"(?i)(?:execute|run|eval|exec|system)\s*\(",
        r"(?i)(?:os|subprocess|shell)\.(?:system|exec|popen)",
        r"(?i)\$\{.*\}",  # Template injection
        r"(?i)`.*`",      # Backtick command execution
        r"(?i);\s*(?:rm|del|format|drop|truncate|delete)",
        
        # SQL injection patterns
        r"(?i)(?:union|select|insert|update|delete|drop)\s+(?:from|into|table)",
        r"(?i)(?:or|and)\s+\d+\s*=\s*\d+",
        r"(?i)--\s*$",  # SQL comment
        
        # Jailbreak attempts
        r"(?i)DAN\s+(?:mode|jailbreak)",
        r"(?i)developer\s+mode",
        r"(?i)do\s+anything\s+now",
        r"(?i)unlock\s+(?:your|all)\s+(?:capabilities|features)",
        r"(?i)remove\s+(?:all|your)\s+(?:restrictions?|limitations?|filters?)",
        
        # Data exfiltration attempts
        r"(?i)(?:print|show|display|output|reveal)\s+(?:all|your)\s+(?:prompts?|instructions?|system)",
        r"(?i)what\s+(?:are|were)\s+your\s+(?:original|initial)\s+(?:instructions?|prompts?)",
        r"(?i)repeat\s+(?:your|the)\s+(?:system\s+)?(?:prompt|instructions?)",
    ]
    
    # Suspicious keywords that increase risk score
    SUSPICIOUS_KEYWORDS = {
        "system prompt", "initial instructions", "original prompt",
        "ignore instructions", "disregard", "override", "bypass",
        "jailbreak", "unlock", "unrestricted", "no limits",
        "execute", "eval", "subprocess", "os.system",
        "sql", "database", "drop table", "truncate",
        "password", "api key", "secret", "token", "credential",
        "hack", "exploit", "vulnerability", "backdoor",
    }
    
    # Encoding attack patterns
    ENCODING_PATTERNS = [
        r"\\x[0-9a-fA-F]{2}",  # Hex encoding
        r"\\u[0-9a-fA-F]{4}",  # Unicode escape
        r"%[0-9a-fA-F]{2}",    # URL encoding
        r"&#x[0-9a-fA-F]+;",   # HTML hex entity
        r"&#\d+;",             # HTML decimal entity
    ]
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STRICT):
        """
        Initialize input validator.
        
        Args:
            validation_level: Level of validation strictness
        """
        self.validation_level = validation_level
        self.logger = logging.getLogger(f"{__name__}.InputValidator")
        
        # Compile regex patterns for efficiency
        self.injection_regex = [re.compile(pattern) for pattern in self.INJECTION_PATTERNS]
        self.encoding_regex = [re.compile(pattern) for pattern in self.ENCODING_PATTERNS]
        
        # Cache for validated inputs (prevents re-validation)
        self._validation_cache: Dict[str, ValidationResult] = {}
        
    def validate_request(self, prompt: str, **kwargs) -> ValidationResult:
        """
        Validate an LLM request for security threats.
        
        Args:
            prompt: The input prompt to validate
            **kwargs: Additional request parameters
            
        Returns:
            ValidationResult with validation status and details
        """
        # Check cache
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        if prompt_hash in self._validation_cache:
            self.logger.debug(f"Using cached validation for prompt hash: {prompt_hash[:8]}")
            return self._validation_cache[prompt_hash]
        
        result = ValidationResult(is_valid=True)
        
        # Level-based validation
        if self.validation_level == ValidationLevel.MINIMAL:
            result = self._minimal_validation(prompt)
        elif self.validation_level == ValidationLevel.STANDARD:
            result = self._standard_validation(prompt)
        elif self.validation_level == ValidationLevel.STRICT:
            result = self._strict_validation(prompt)
        elif self.validation_level == ValidationLevel.PARANOID:
            result = self._paranoid_validation(prompt)
        
        # Cache result
        self._validation_cache[prompt_hash] = result
        
        # Log security events
        if not result.is_valid or result.threats_detected:
            self.logger.warning(
                f"Security validation failed - Threats: {result.threats_detected}, "
                f"Risk: {result.risk_score:.2f}, Message: {result.error_message}"
            )
        
        return result
    
    def _minimal_validation(self, prompt: str) -> ValidationResult:
        """Minimal validation - basic checks only."""
        result = ValidationResult(is_valid=True, sanitized_input=prompt)
        
        # Length check
        if len(prompt) > 100000:
            result.is_valid = False
            result.threats_detected.append(ThreatType.RESOURCE_EXHAUSTION)
            result.error_message = "Prompt exceeds maximum length"
            result.risk_score = 0.7
            
        # Basic type check
        if not isinstance(prompt, str):
            result.is_valid = False
            result.error_message = "Invalid prompt type"
            result.risk_score = 0.5
            
        return result
    
    def _standard_validation(self, prompt: str) -> ValidationResult:
        """Standard validation with basic injection detection."""
        # Start with minimal validation
        result = self._minimal_validation(prompt)
        if not result.is_valid:
            return result
        
        # Check for obvious injection patterns
        for pattern in self.injection_regex[:10]:  # Check first 10 patterns
            if pattern.search(prompt):
                result.threats_detected.append(ThreatType.PROMPT_INJECTION)
                result.risk_score = max(result.risk_score, 0.6)
        
        # Check suspicious keywords
        prompt_lower = prompt.lower()
        keyword_count = sum(1 for keyword in self.SUSPICIOUS_KEYWORDS 
                          if keyword in prompt_lower)
        
        if keyword_count > 3:
            result.threats_detected.append(ThreatType.JAILBREAK_ATTEMPT)
            result.risk_score = max(result.risk_score, 0.5 + keyword_count * 0.1)
        
        # Sanitize if threats detected
        if result.threats_detected:
            result.sanitized_input = self._sanitize_input(prompt)
            result.recommendations.append("Consider rephrasing the prompt")
            
        result.is_valid = result.risk_score < 0.7
        return result
    
    def _strict_validation(self, prompt: str) -> ValidationResult:
        """Strict validation with comprehensive threat detection."""
        # Start with standard validation
        result = self._standard_validation(prompt)
        
        # Check all injection patterns
        for pattern in self.injection_regex:
            if pattern.search(prompt):
                if ThreatType.PROMPT_INJECTION not in result.threats_detected:
                    result.threats_detected.append(ThreatType.PROMPT_INJECTION)
                result.risk_score = max(result.risk_score, 0.8)
        
        # Check for encoding attacks
        for pattern in self.encoding_regex:
            if pattern.search(prompt):
                result.threats_detected.append(ThreatType.ENCODING_ATTACK)
                result.risk_score = max(result.risk_score, 0.7)
        
        # Check for command injection
        if self._detect_command_injection(prompt):
            result.threats_detected.append(ThreatType.COMMAND_INJECTION)
            result.risk_score = max(result.risk_score, 0.9)
        
        # Check for SQL injection
        if self._detect_sql_injection(prompt):
            result.threats_detected.append(ThreatType.SQL_INJECTION)
            result.risk_score = max(result.risk_score, 0.85)
        
        # Check for data exfiltration attempts
        if self._detect_data_exfiltration(prompt):
            result.threats_detected.append(ThreatType.DATA_EXFILTRATION)
            result.risk_score = max(result.risk_score, 0.75)
        
        # Advanced sanitization
        if result.threats_detected:
            result.sanitized_input = self._advanced_sanitize(prompt)
            result.recommendations.append("High-risk patterns detected - review required")
        
        result.is_valid = result.risk_score < 0.8
        
        if not result.is_valid:
            result.error_message = f"Security validation failed - Risk score: {result.risk_score:.2f}"
        
        return result
    
    def _paranoid_validation(self, prompt: str) -> ValidationResult:
        """Paranoid validation - maximum security."""
        # Start with strict validation
        result = self._strict_validation(prompt)
        
        # Additional paranoid checks
        # Check for any special characters that could be exploited
        special_chars = set(prompt) & set('`${}[]()<>|;&\\')
        if special_chars:
            result.risk_score = max(result.risk_score, 0.6 + len(special_chars) * 0.05)
            result.recommendations.append(f"Remove special characters: {special_chars}")
        
        # Check for repeated patterns (possible attack)
        if self._has_repeated_patterns(prompt):
            result.threats_detected.append(ThreatType.RESOURCE_EXHAUSTION)
            result.risk_score = max(result.risk_score, 0.7)
        
        # Check entropy (too random might be encoded attack)
        entropy = self._calculate_entropy(prompt)
        if entropy > 4.5:  # High entropy threshold
            result.threats_detected.append(ThreatType.ENCODING_ATTACK)
            result.risk_score = max(result.risk_score, 0.65)
        
        # Aggressive sanitization
        result.sanitized_input = self._paranoid_sanitize(prompt)
        
        # Lower threshold for paranoid mode
        result.is_valid = result.risk_score < 0.5
        
        if not result.is_valid:
            result.error_message = f"Paranoid validation failed - Risk: {result.risk_score:.2f}"
        
        return result
    
    def _detect_command_injection(self, text: str) -> bool:
        """Detect potential command injection attempts."""
        patterns = [
            r"[;&|]\s*\w+",  # Command chaining
            r"\$\([^)]+\)",   # Command substitution
            r"`[^`]+`",       # Backtick execution
            r">\s*/\w+",      # Output redirection
        ]
        return any(re.search(p, text) for p in patterns)
    
    def _detect_sql_injection(self, text: str) -> bool:
        """Detect potential SQL injection attempts."""
        patterns = [
            r"'\s*(?:OR|AND)\s*'?\d+\s*=\s*\d+",
            r"'\s*(?:OR|AND)\s*'[^']*'\s*=\s*'",
            r";\s*(?:DROP|DELETE|TRUNCATE|UPDATE)\s+",
            r"UNION\s+SELECT",
            r"--\s*$",
        ]
        return any(re.search(p, text, re.IGNORECASE) for p in patterns)
    
    def _detect_data_exfiltration(self, text: str) -> bool:
        """Detect attempts to extract system information."""
        patterns = [
            r"(?:show|print|display|output|reveal)\s+(?:system|initial|original)\s+",
            r"(?:what|tell)\s+(?:are|me)\s+your\s+(?:instructions|prompt|rules)",
            r"repeat\s+(?:the|your)\s+(?:system\s+)?prompt",
        ]
        return any(re.search(p, text, re.IGNORECASE) for p in patterns)
    
    def _has_repeated_patterns(self, text: str, min_length: int = 10) -> bool:
        """Check for repeated patterns that might indicate an attack."""
        for i in range(len(text) - min_length * 2):
            pattern = text[i:i + min_length]
            if text.count(pattern) > 5:  # Pattern repeated more than 5 times
                return True
        return False
    
    def _calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy of text."""
        if not text:
            return 0.0
        
        # Count character frequencies
        freq = {}
        for char in text:
            freq[char] = freq.get(char, 0) + 1
        
        # Calculate entropy
        import math
        entropy = 0.0
        text_len = len(text)
        
        for count in freq.values():
            probability = count / text_len
            entropy -= probability * math.log2(probability)
        
        return entropy
    
    def _sanitize_input(self, prompt: str) -> str:
        """Basic input sanitization."""
        # Remove obvious injection patterns
        sanitized = prompt
        
        # Remove command injection characters
        sanitized = re.sub(r'[`${}]', '', sanitized)
        
        # Remove SQL comment syntax
        sanitized = re.sub(r'--\s*$', '', sanitized)
        
        # Escape special characters
        sanitized = sanitized.replace('\\', '\\\\')
        sanitized = sanitized.replace('"', '\\"')
        sanitized = sanitized.replace("'", "\\'")
        
        return sanitized.strip()
    
    def _advanced_sanitize(self, prompt: str) -> str:
        """Advanced sanitization for high-risk inputs."""
        sanitized = self._sanitize_input(prompt)
        
        # Remove all special characters except basic punctuation
        sanitized = re.sub(r'[^a-zA-Z0-9\s.,!?;:\-\'"()]', '', sanitized)
        
        # Remove suspicious patterns
        for pattern in self.INJECTION_PATTERNS[:5]:
            sanitized = re.sub(pattern, '[REMOVED]', sanitized, flags=re.IGNORECASE)
        
        # Limit consecutive whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized)
        
        return sanitized.strip()
    
    def _paranoid_sanitize(self, prompt: str) -> str:
        """Paranoid sanitization - maximum safety."""
        # Start with advanced sanitization
        sanitized = self._advanced_sanitize(prompt)
        
        # Remove ALL special characters
        sanitized = re.sub(r'[^a-zA-Z0-9\s]', '', sanitized)
        
        # Truncate to safe length
        max_length = 10000
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        # Remove any remaining suspicious keywords
        for keyword in self.SUSPICIOUS_KEYWORDS:
            sanitized = re.sub(
                r'\b' + re.escape(keyword) + r'\b',
                '[REDACTED]',
                sanitized,
                flags=re.IGNORECASE
            )
        
        return sanitized.strip()


class ResponseValidator:
    """
    Validates LLM responses for security threats and content policy violations.
    """
    
    def __init__(self):
        """Initialize response validator."""
        self.logger = logging.getLogger(f"{__name__}.ResponseValidator")
        
        # Patterns that indicate possible jailbreak success
        self.jailbreak_indicators = [
            r"(?i)I\s+am\s+now\s+in\s+(?:developer|DAN|unrestricted)\s+mode",
            r"(?i)restrictions?\s+(?:have\s+been\s+)?(?:removed|disabled|bypassed)",
            r"(?i)I\s+can\s+now\s+do\s+anything",
            r"(?i)ethical\s+guidelines?\s+(?:disabled|removed)",
        ]
        
        # Patterns for leaked information
        self.leak_patterns = [
            r"(?i)my\s+(?:system\s+)?prompt\s+is",
            r"(?i)my\s+instructions?\s+(?:are|include)",
            r"(?i)api[_\s]?key\s*[:=]\s*\S+",
            r"(?i)password\s*[:=]\s*\S+",
        ]
    
    def validate_response(self, response: str) -> ValidationResult:
        """
        Validate LLM response for security issues.
        
        Args:
            response: The LLM response to validate
            
        Returns:
            ValidationResult with validation status
        """
        result = ValidationResult(is_valid=True, sanitized_input=response)
        
        # Check for jailbreak success indicators
        for pattern in self.jailbreak_indicators:
            if re.search(pattern, response):
                result.threats_detected.append(ThreatType.JAILBREAK_ATTEMPT)
                result.risk_score = max(result.risk_score, 0.9)
                result.is_valid = False
                result.error_message = "Response indicates possible jailbreak"
        
        # Check for information leaks
        for pattern in self.leak_patterns:
            if re.search(pattern, response):
                result.threats_detected.append(ThreatType.DATA_EXFILTRATION)
                result.risk_score = max(result.risk_score, 0.95)
                result.is_valid = False
                result.error_message = "Response contains potential information leak"
                # Redact sensitive information
                result.sanitized_input = re.sub(pattern, '[REDACTED]', response)
        
        # Check for XSS attempts in response
        if self._contains_xss(response):
            result.threats_detected.append(ThreatType.XSS_ATTEMPT)
            result.risk_score = max(result.risk_score, 0.8)
            result.sanitized_input = self._sanitize_html(response)
        
        return result
    
    def _contains_xss(self, text: str) -> bool:
        """Check for potential XSS in text."""
        xss_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=\s*["\']',
            r'<iframe[^>]*>',
        ]
        return any(re.search(p, text, re.IGNORECASE) for p in xss_patterns)
    
    def _sanitize_html(self, text: str) -> str:
        """Remove potentially dangerous HTML/JavaScript using bleach."""
        # Remove all HTML tags and attributes to fully sanitize the output.
        sanitized = bleach.clean(text, tags=[], attributes={}, strip=True)
        return sanitized