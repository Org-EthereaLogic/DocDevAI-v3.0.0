"""
M004 Document Generator - Security-enhanced validator for Pass 3.

Comprehensive security validation for document generation with advanced threat detection.
"""

import re
import html
import logging
import json
import urllib.parse
from typing import Dict, List, Optional, Any, Union, Set
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import unicodedata
import threading

from ...common.errors import DevDocAIError
from ...common.logging import get_logger
from ...common.security import InputValidator as BaseValidator, PIIDetector, AuditLogger, get_audit_logger

logger = get_logger(__name__)


class SecurityValidationError(DevDocAIError):
    """Exception raised for security validation failures."""
    pass


class EnhancedSecurityValidator(BaseValidator):
    """
    Advanced security validator for M004 Document Generator Pass 3.
    
    Provides comprehensive protection against:
    - Template injection attacks
    - XSS and script injection
    - SQL injection attempts
    - Path traversal attacks
    - Command injection
    - Unicode normalization attacks
    - PII exposure
    - DoS through resource exhaustion
    """
    
    # Security threat patterns
    TEMPLATE_INJECTION_PATTERNS = [
        re.compile(r'{{.*?}}', re.IGNORECASE | re.DOTALL),  # Jinja2/Django templates
        re.compile(r'{%.*?%}', re.IGNORECASE | re.DOTALL),  # Template tags
        re.compile(r'<%.*?%>', re.IGNORECASE | re.DOTALL),  # ASP/JSP templates
        re.compile(r'\$\{.*?\}', re.IGNORECASE | re.DOTALL),  # Expression Language
        re.compile(r'\#\{.*?\}', re.IGNORECASE | re.DOTALL),  # SpEL expressions
        re.compile(r'\[\[.*?\]\]', re.IGNORECASE | re.DOTALL),  # Thymeleaf
        re.compile(r'\{\{.*?\}\}', re.IGNORECASE | re.DOTALL),  # Handlebars
    ]
    
    XSS_PATTERNS = [
        re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
        re.compile(r'<iframe[^>]*>.*?</iframe>', re.IGNORECASE | re.DOTALL),
        re.compile(r'<object[^>]*>.*?</object>', re.IGNORECASE | re.DOTALL),
        re.compile(r'<embed[^>]*>', re.IGNORECASE),
        re.compile(r'<link[^>]*>', re.IGNORECASE),
        re.compile(r'<meta[^>]*>', re.IGNORECASE),
        re.compile(r'<base[^>]*>', re.IGNORECASE),
        re.compile(r'<form[^>]*>', re.IGNORECASE),
        re.compile(r'javascript:', re.IGNORECASE),
        re.compile(r'vbscript:', re.IGNORECASE),
        re.compile(r'data:', re.IGNORECASE),
        re.compile(r'on\w+\s*=', re.IGNORECASE),  # Event handlers
        re.compile(r'style\s*=.*?expression\s*\(', re.IGNORECASE),  # CSS expressions
        re.compile(r'@import\s*["\']', re.IGNORECASE),  # CSS imports
    ]
    
    SQL_INJECTION_PATTERNS = [
        re.compile(r'\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b', re.IGNORECASE),
        re.compile(r'(\-\-|\/\*|\*\/|;)', re.IGNORECASE),
        re.compile(r"('|(\\\x27)|(\\\x2D))", re.IGNORECASE),
        re.compile(r'\b(or|and)\s+\d+\s*=\s*\d+', re.IGNORECASE),
        re.compile(r'\b(or|and)\s+[\'\"]?\w+[\'\"]?\s*=\s*[\'\"]?\w+[\'\"]?', re.IGNORECASE),
        re.compile(r'benchmark\s*\(', re.IGNORECASE),
        re.compile(r'sleep\s*\(', re.IGNORECASE),
        re.compile(r'waitfor\s+delay', re.IGNORECASE),
    ]
    
    PATH_TRAVERSAL_PATTERNS = [
        re.compile(r'\.\./|\.\\\\', re.IGNORECASE),
        re.compile(r'%2e%2e%2f|%2e%2e\\', re.IGNORECASE),
        re.compile(r'\.\.%2f|\.\.%5c', re.IGNORECASE),
        re.compile(r'%c0%af|%c1%9c', re.IGNORECASE),  # Unicode bypass attempts
        re.compile(r'\.\.\/|\.\.\\', re.IGNORECASE),
        re.compile(r'%2e%2e\/', re.IGNORECASE),
    ]
    
    COMMAND_INJECTION_PATTERNS = [
        re.compile(r'[;&|`$\(\)\{\}\[\]<>]', re.IGNORECASE),
        re.compile(r'\b(cat|ls|pwd|whoami|id|uname|wget|curl|nc|netcat|rm|cp|mv)\b', re.IGNORECASE),
        re.compile(r'\b(eval|exec|system|shell_exec|passthru|popen|proc_open)\b', re.IGNORECASE),
        re.compile(r'\b(python|perl|ruby|php|bash|sh|cmd|powershell)\b', re.IGNORECASE),
    ]
    
    SUSPICIOUS_CODE_PATTERNS = [
        re.compile(r'\b(eval|exec|setTimeout|setInterval|Function)\b', re.IGNORECASE),
        re.compile(r'\$\{.*?\}'),  # Template literals
        re.compile(r'\bimport\s+os\b', re.IGNORECASE),
        re.compile(r'\b__import__\b'),
        re.compile(r'\bfile_get_contents\b', re.IGNORECASE),
        re.compile(r'\brequire\s*\(', re.IGNORECASE),
        re.compile(r'\binclude\s*\(', re.IGNORECASE),
    ]
    
    # Security limits
    MAX_TEMPLATE_DEPTH = 10
    MAX_VARIABLE_COUNT = 100
    MAX_INPUT_SIZE = 1024 * 1024  # 1MB
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_LINE_LENGTH = 10000
    MAX_TEXT_SIZE = 100000  # 100KB per field
    RATE_LIMIT_REQUESTS = 100  # per hour
    
    def __init__(self):
        """Initialize enhanced security validator."""
        super().__init__()
        self.audit_logger = get_audit_logger()
        self.pii_detector = PIIDetector()
        
        # Rate limiting tracking
        self.validation_attempts: Dict[str, List[datetime]] = {}
        self._lock = threading.Lock()
        
        # Security context tracking
        self.security_context = {
            'high_risk_patterns': set(),
            'blocked_clients': set(),
            'threat_counts': {}
        }
        
        logger.info("Enhanced SecurityValidator initialized with comprehensive threat detection")
    
    def validate_template_inputs_secure(
        self, 
        inputs: Dict[str, Any], 
        required_variables: List[str],
        client_id: str = 'anonymous',
        template_name: str = 'unknown'
    ) -> Dict[str, Any]:
        """
        Comprehensive secure validation for template inputs.
        
        Args:
            inputs: Input values to validate
            required_variables: List of required variable names
            client_id: Client identifier for audit logging
            template_name: Template name for context
            
        Returns:
            Validation result dictionary with errors, warnings, and metadata
        """
        result = {
            'valid': False,
            'errors': [],
            'warnings': [],
            'security_score': 0,
            'pii_detected': False,
            'sanitized_inputs': {},
            'validation_metadata': {
                'timestamp': datetime.now().isoformat(),
                'client_id': client_id,
                'template_name': template_name,
                'input_count': len(inputs),
                'total_size': len(json.dumps(inputs, default=str))
            }
        }
        
        try:
            # Rate limiting check
            if not self._check_rate_limit(client_id, 'validation'):
                result['errors'].append("Validation rate limit exceeded")
                self._log_security_event('rate_limit_exceeded', client_id, template_name)
                return result
            
            # Pre-validation security checks
            pre_check_errors = self._pre_validation_security_checks(inputs, client_id)
            result['errors'].extend(pre_check_errors)
            
            if pre_check_errors:
                self._log_security_event('pre_validation_failed', client_id, template_name, {'errors': pre_check_errors})
                return result
            
            # Comprehensive security scanning
            security_scan = self._comprehensive_security_scan(inputs)
            result['errors'].extend(security_scan['errors'])
            result['warnings'].extend(security_scan['warnings'])
            result['security_score'] = security_scan['score']
            
            # PII detection
            pii_scan = self._scan_for_pii(inputs)
            result['pii_detected'] = pii_scan['detected']
            if pii_scan['detected']:
                result['warnings'].append(f"PII detected: {', '.join(pii_scan['types'])}")
                self._log_security_event('pii_detected', client_id, template_name, pii_scan)
            
            # Required field validation
            required_errors = self._validate_required_fields(inputs, required_variables)
            result['errors'].extend(required_errors)
            
            # Enhanced field validation
            for key, value in inputs.items():
                field_result = self._validate_field_comprehensive(key, value, client_id)
                result['errors'].extend(field_result['errors'])
                result['warnings'].extend(field_result['warnings'])
                result['sanitized_inputs'][key] = field_result['sanitized_value']
            
            # Final validation
            result['valid'] = len(result['errors']) == 0
            
            # Log validation result
            self._log_validation_result(result, client_id, template_name)
            
            logger.info(f"Security validation completed for {template_name}: "
                       f"valid={result['valid']}, errors={len(result['errors'])}, "
                       f"security_score={result['security_score']}")
            
        except Exception as e:
            logger.error(f"Security validation failed: {e}")
            result['errors'].append(f"Validation system error: {str(e)}")
            self._log_security_event('validation_exception', client_id, template_name, {'error': str(e)})
        
        return result
    
    def _pre_validation_security_checks(self, inputs: Dict[str, Any], client_id: str) -> List[str]:
        """Pre-validation security checks."""
        errors = []
        
        # Check input size limits
        input_size = len(json.dumps(inputs, default=str))
        if input_size > self.MAX_INPUT_SIZE:
            errors.append(f"Input data too large: {input_size} bytes (max {self.MAX_INPUT_SIZE})")
            return errors
        
        # Check variable count limit
        if len(inputs) > self.MAX_VARIABLE_COUNT:
            errors.append(f"Too many variables: {len(inputs)} (max {self.MAX_VARIABLE_COUNT})")
            return errors
        
        # Check for blocked clients
        if client_id in self.security_context['blocked_clients']:
            errors.append("Client has been blocked due to security violations")
            return errors
        
        return errors
    
    def _comprehensive_security_scan(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive security threat scanning."""
        scan_result = {
            'errors': [],
            'warnings': [],
            'score': 100,  # Start with perfect score, deduct for issues
            'threats_detected': []
        }
        
        for key, value in inputs.items():
            if isinstance(value, str):
                # Template injection check
                if self._check_template_injection(value):
                    scan_result['errors'].append(f"Template injection detected in field '{key}'")
                    scan_result['threats_detected'].append('template_injection')
                    scan_result['score'] -= 50
                
                # XSS check
                if self._check_xss_patterns(value):
                    scan_result['errors'].append(f"XSS pattern detected in field '{key}'")
                    scan_result['threats_detected'].append('xss')
                    scan_result['score'] -= 30
                
                # SQL injection check
                if self._check_sql_injection(value):
                    scan_result['errors'].append(f"SQL injection pattern detected in field '{key}'")
                    scan_result['threats_detected'].append('sql_injection')
                    scan_result['score'] -= 40
                
                # Path traversal check
                if self._check_path_traversal(value):
                    scan_result['errors'].append(f"Path traversal attempt detected in field '{key}'")
                    scan_result['threats_detected'].append('path_traversal')
                    scan_result['score'] -= 35
                
                # Command injection check
                if self._check_command_injection(value):
                    scan_result['errors'].append(f"Command injection pattern detected in field '{key}'")
                    scan_result['threats_detected'].append('command_injection')
                    scan_result['score'] -= 45
                
                # Suspicious code patterns
                if self._check_suspicious_code(value):
                    scan_result['warnings'].append(f"Suspicious code pattern in field '{key}'")
                    scan_result['threats_detected'].append('suspicious_code')
                    scan_result['score'] -= 10
                
                # Check for encoded attacks
                if self._check_encoded_attacks(value, key):
                    scan_result['errors'].append(f"Encoded attack detected in field '{key}'")
                    scan_result['threats_detected'].append('encoded_attack')
                    scan_result['score'] -= 25
        
        # Ensure score doesn't go below 0
        scan_result['score'] = max(0, scan_result['score'])
        
        return scan_result
    
    def _scan_for_pii(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Scan inputs for PII data."""
        all_findings = {}
        
        for key, value in inputs.items():
            if isinstance(value, str):
                findings = self.pii_detector.detect_pii(value)
                if findings:
                    for pii_type, matches in findings.items():
                        if pii_type not in all_findings:
                            all_findings[pii_type] = []
                        all_findings[pii_type].extend(matches)
        
        return {
            'detected': bool(all_findings),
            'types': list(all_findings.keys()),
            'details': all_findings
        }
    
    def _validate_field_comprehensive(self, field_name: str, value: Any, client_id: str) -> Dict[str, Any]:
        """Comprehensive field validation with security focus."""
        field_result = {
            'errors': [],
            'warnings': [],
            'sanitized_value': value
        }
        
        if value is None:
            return field_result
        
        # Handle complex types
        if isinstance(value, (list, dict, tuple)):
            complexity_errors = self._validate_complex_type(field_name, value)
            field_result['errors'].extend(complexity_errors)
            return field_result
        
        # Convert to string for validation
        str_value = str(value)
        
        # Unicode normalization attack check
        normalized_value = self._normalize_unicode(str_value)
        if normalized_value != str_value:
            field_result['errors'].append(f"Unicode normalization attack detected in field '{field_name}'")
            return field_result
        
        # Context-aware validation
        context = self._determine_field_context(field_name)
        context_errors = self._validate_by_context(str_value, field_name, context)
        field_result['errors'].extend(context_errors)
        
        # Length and complexity validation
        length_errors = self._validate_length_secure(str_value, field_name)
        field_result['errors'].extend(length_errors)
        
        # Sanitization
        if not field_result['errors']:
            field_result['sanitized_value'] = self._sanitize_by_context(str_value, context)
        
        return field_result
    
    def _determine_field_context(self, field_name: str) -> str:
        """Determine the security context for a field based on its name."""
        field_lower = field_name.lower()
        
        if any(keyword in field_lower for keyword in ['email', 'mail']):
            return 'email'
        elif any(keyword in field_lower for keyword in ['url', 'link', 'website']):
            return 'url'
        elif any(keyword in field_lower for keyword in ['file', 'path', 'filename']):
            return 'filepath'
        elif any(keyword in field_lower for keyword in ['html', 'content', 'description']):
            return 'html'
        elif any(keyword in field_lower for keyword in ['title', 'name', 'label']):
            return 'text'
        else:
            return 'general'
    
    def _validate_by_context(self, value: str, field_name: str, context: str) -> List[str]:
        """Context-aware validation."""
        errors = []
        
        if context == 'email':
            if not super().validate_string(value, 'email'):
                errors.append(f"Invalid email format in field '{field_name}'")
        elif context == 'url':
            if not self._is_safe_url(value):
                errors.append(f"Invalid or unsafe URL in field '{field_name}'")
        elif context == 'filepath':
            if self._check_path_traversal(value):
                errors.append(f"Path traversal attempt in field '{field_name}'")
        elif context == 'html':
            if self._check_xss_patterns(value):
                errors.append(f"XSS pattern detected in HTML field '{field_name}'")
        
        return errors
    
    def _sanitize_by_context(self, value: str, context: str) -> str:
        """Context-aware sanitization."""
        if context == 'html':
            return html.escape(value)
        elif context == 'url':
            return urllib.parse.quote(value, safe='')
        elif context == 'filepath':
            # Remove dangerous path characters
            return re.sub(r'[<>:"|?*]', '_', value)
        else:
            # Default sanitization
            return html.escape(value)
    
    # Security check methods
    def _check_template_injection(self, value: str) -> bool:
        """Check for template injection patterns."""
        return any(pattern.search(value) for pattern in self.TEMPLATE_INJECTION_PATTERNS)
    
    def _check_xss_patterns(self, value: str) -> bool:
        """Check for XSS patterns."""
        return any(pattern.search(value) for pattern in self.XSS_PATTERNS)
    
    def _check_sql_injection(self, value: str) -> bool:
        """Check for SQL injection patterns."""
        return any(pattern.search(value) for pattern in self.SQL_INJECTION_PATTERNS)
    
    def _check_path_traversal(self, value: str) -> bool:
        """Check for path traversal patterns."""
        return any(pattern.search(value) for pattern in self.PATH_TRAVERSAL_PATTERNS)
    
    def _check_command_injection(self, value: str) -> bool:
        """Check for command injection patterns."""
        return any(pattern.search(value) for pattern in self.COMMAND_INJECTION_PATTERNS)
    
    def _check_suspicious_code(self, value: str) -> bool:
        """Check for suspicious code patterns."""
        return any(pattern.search(value) for pattern in self.SUSPICIOUS_CODE_PATTERNS)
    
    def _check_encoded_attacks(self, value: str, field_name: str) -> bool:
        """Check for encoded attack attempts."""
        try:
            decoded_attempts = [
                urllib.parse.unquote(value),
                urllib.parse.unquote_plus(value),
                html.unescape(value)
            ]
            
            for attempt in decoded_attempts:
                if attempt != value:
                    # Check if decoded version has threats
                    if (self._check_template_injection(attempt) or 
                        self._check_xss_patterns(attempt) or 
                        self._check_sql_injection(attempt)):
                        return True
        except Exception:
            # If decoding fails, treat as suspicious
            return True
        
        return False
    
    def _is_safe_url(self, url: str) -> bool:
        """Check if URL is safe."""
        dangerous_schemes = ['javascript:', 'data:', 'vbscript:', 'file:', 'ftp:']
        url_lower = url.lower()
        
        for scheme in dangerous_schemes:
            if url_lower.startswith(scheme):
                return False
        
        return re.match(r'^https?://[a-zA-Z0-9.-]+', url) is not None
    
    def _normalize_unicode(self, value: str) -> str:
        """Normalize unicode to prevent normalization attacks."""
        return unicodedata.normalize('NFKC', value)
    
    def _validate_complex_type(self, field_name: str, value: Union[list, dict, tuple]) -> List[str]:
        """Validate complex data types."""
        errors = []
        
        if isinstance(value, dict):
            if len(value) > 50:  # Prevent dictionary bombs
                errors.append(f"Dictionary too large in field '{field_name}' (max 50 keys)")
        elif isinstance(value, (list, tuple)):
            if len(value) > 100:  # Prevent array bombs
                errors.append(f"Array too large in field '{field_name}' (max 100 items)")
        
        return errors
    
    def _validate_length_secure(self, value: str, field_name: str) -> List[str]:
        """Secure length validation."""
        errors = []
        
        # Check overall length
        if len(value) > self.MAX_TEXT_SIZE:
            errors.append(f"Text too large in field '{field_name}' (max {self.MAX_TEXT_SIZE} chars)")
        
        # Check for extremely long lines
        lines = value.split('\n')
        for i, line in enumerate(lines):
            if len(line) > self.MAX_LINE_LENGTH:
                errors.append(f"Line too long in field '{field_name}' at line {i+1}")
                break
        
        return errors
    
    def _validate_required_fields(self, inputs: Dict[str, Any], required_variables: List[str]) -> List[str]:
        """Validate required fields."""
        errors = []
        
        for var in required_variables:
            if var not in inputs:
                errors.append(f"Required variable '{var}' is missing")
            elif inputs[var] is None:
                errors.append(f"Required variable '{var}' cannot be None")
            elif isinstance(inputs[var], str) and not inputs[var].strip():
                errors.append(f"Required variable '{var}' cannot be empty")
        
        return errors
    
    def _check_rate_limit(self, client_id: str, operation: str) -> bool:
        """Rate limiting for validation operations."""
        with self._lock:
            now = datetime.now()
            key = f"{client_id}:{operation}"
            
            if key not in self.validation_attempts:
                self.validation_attempts[key] = []
            
            # Remove old attempts (last hour)
            cutoff = now - timedelta(hours=1)
            self.validation_attempts[key] = [
                attempt for attempt in self.validation_attempts[key]
                if attempt > cutoff
            ]
            
            # Check limit
            if len(self.validation_attempts[key]) >= self.RATE_LIMIT_REQUESTS:
                return False
            
            self.validation_attempts[key].append(now)
            return True
    
    def _log_security_event(self, event_type: str, client_id: str, template_name: str, details: Optional[Dict] = None):
        """Log security events for audit."""
        event_details = {
            'client_id': client_id,
            'template_name': template_name,
            'timestamp': datetime.now().isoformat()
        }
        
        if details:
            event_details.update(details)
        
        self.audit_logger.log_event(f'security_{event_type}', event_details)
    
    def _log_validation_result(self, result: Dict[str, Any], client_id: str, template_name: str):
        """Log validation results."""
        self.audit_logger.log_event('validation_completed', {
            'client_id': client_id,
            'template_name': template_name,
            'valid': result['valid'],
            'error_count': len(result['errors']),
            'warning_count': len(result['warnings']),
            'security_score': result['security_score'],
            'pii_detected': result['pii_detected'],
            'timestamp': datetime.now().isoformat()
        })
    
    def create_security_report(self, inputs: Dict[str, Any], client_id: str = 'anonymous') -> Dict[str, Any]:
        """Create comprehensive security report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'client_id': client_id,
            'input_analysis': {
                'field_count': len(inputs),
                'total_size': len(json.dumps(inputs, default=str)),
                'complexity_score': self._calculate_complexity_score(inputs)
            },
            'security_analysis': self._comprehensive_security_scan(inputs),
            'pii_analysis': self._scan_for_pii(inputs),
            'recommendations': self._generate_security_recommendations(inputs)
        }
        
        return report
    
    def _calculate_complexity_score(self, inputs: Dict[str, Any]) -> int:
        """Calculate complexity score for inputs."""
        score = 0
        
        for key, value in inputs.items():
            if isinstance(value, str):
                score += min(len(value) // 100, 10)  # Length factor
                score += value.count('\n')  # Line count factor
            elif isinstance(value, (list, tuple)):
                score += len(value)
            elif isinstance(value, dict):
                score += len(value) * 2
        
        return min(score, 100)
    
    def _generate_security_recommendations(self, inputs: Dict[str, Any]) -> List[str]:
        """Generate security recommendations."""
        recommendations = []
        
        # Check for common issues
        has_large_text = any(isinstance(v, str) and len(v) > 1000 for v in inputs.values())
        has_html = any(isinstance(v, str) and '<' in v and '>' in v for v in inputs.values())
        has_urls = any('url' in str(k).lower() or 'link' in str(k).lower() for k in inputs.keys())
        
        if has_large_text:
            recommendations.append("Consider splitting large text fields into smaller chunks")
        
        if has_html:
            recommendations.append("HTML content detected - ensure proper sanitization")
        
        if has_urls:
            recommendations.append("URLs detected - validate against allowed domains")
        
        return recommendations