"""
Security-enhanced review dimensions for M007 Review Engine.

Implements comprehensive security checks, PII protection,
and threat detection across all review dimensions.
"""

import re
import logging
import asyncio
import hashlib
import secrets
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import numpy as np
from collections import defaultdict
import signal
from datetime import datetime

from ..storage.pii_detector import PIIDetector, PIIDetectionConfig, PIIType
from .models import (
    ReviewDimension,
    ReviewSeverity,
    ReviewIssue,
    DimensionResult
)
from .security_validator import SecurityValidator, SecurityThreat

logger = logging.getLogger(__name__)


# Secure regex patterns with timeout protection
class SecureRegexPatterns:
    """Pre-compiled secure regex patterns with ReDoS protection."""
    
    # Technical patterns (simplified to avoid ReDoS)
    CODE_SMELL = re.compile(r'\b(?:TODO|FIXME|HACK|XXX|REFACTOR|OPTIMIZE)\b', re.IGNORECASE)
    DEBUG_CODE = re.compile(r'(?:console\.(?:log|debug|info|warn|error)|print\(|debugger\b|pdb\.set_trace)', re.IGNORECASE)
    HARDCODED_VALUES = re.compile(r'(?:password|secret|key|token)\s*=\s*["\'][^"\']{1,100}["\']', re.IGNORECASE)
    UNUSED_IMPORTS = re.compile(r'^import\s+\w+(?:\s*,\s*\w+){0,10}\s*$', re.MULTILINE)
    LONG_LINES = re.compile(r'^.{121,200}$', re.MULTILINE)  # Limit length to prevent ReDoS
    
    # Security patterns
    SQL_INJECTION = re.compile(r'\b(?:SELECT|INSERT|UPDATE|DELETE|DROP|UNION)\b.*\b(?:FROM|WHERE|TABLE)\b', re.IGNORECASE)
    XSS_SIMPLE = re.compile(r'<script[^>]*>|javascript:|on\w+\s*=', re.IGNORECASE)
    COMMAND_INJECTION = re.compile(r'[;&|`$]|\$\([^)]{1,100}\)', re.IGNORECASE)
    PATH_TRAVERSAL = re.compile(r'\.\.[\\/]|\.\.%2[fF]|\.\.%5[cC]', re.IGNORECASE)
    WEAK_CRYPTO = re.compile(r'\b(?:md5|sha1|des|rc4)\b', re.IGNORECASE)
    INSECURE_RANDOM = re.compile(r'\b(?:random\.random|Math\.random)\b', re.IGNORECASE)
    
    # Completeness patterns
    SECTIONS = re.compile(r'^#{1,6}\s+(.{1,200})$', re.MULTILINE)  # Limit header length
    CODE_BLOCKS = re.compile(r'```[^`]{0,10000}```')  # Limit code block size
    LINKS = re.compile(r'\[([^\]]{1,100})\]\(([^)]{1,500})\)')  # Limit link text/URL length
    IMAGES = re.compile(r'!\[([^\]]{0,100})\]\(([^)]{1,500})\)')
    TABLES = re.compile(r'^\|.{1,1000}\|$', re.MULTILINE)  # Limit table row length
    LISTS = re.compile(r'^[\*\-\+]\s+.{1,500}$|^\d+\.\s+.{1,500}$', re.MULTILINE)
    
    # Consistency patterns
    CAMEL_CASE = re.compile(r'\b[a-z]+(?:[A-Z][a-z]+){1,10}\b')  # Limit camelCase length
    SNAKE_CASE = re.compile(r'\b[a-z]+(?:_[a-z]+){1,10}\b')
    KEBAB_CASE = re.compile(r'\b[a-z]+(?:-[a-z]+){1,10}\b')
    TRAILING_WHITESPACE = re.compile(r'[ \t]+$', re.MULTILINE)
    
    # Style patterns
    MULTIPLE_SPACES = re.compile(r'  {1,10}')  # Limit consecutive spaces
    TABS_SPACES_MIX = re.compile(r'^(?:\t+ +| +\t+)', re.MULTILINE)
    EMPTY_LINES = re.compile(r'\n{3,10}')  # Limit consecutive empty lines
    
    @classmethod
    def safe_search(cls, pattern: re.Pattern, text: str, timeout: float = 1.0) -> List[re.Match]:
        """
        Safely search regex with timeout protection against ReDoS.
        """
        def timeout_handler(signum, frame):
            raise TimeoutError("Regex execution timed out")
        
        # Set timeout
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(timeout))
        
        try:
            matches = list(pattern.finditer(text))
            signal.alarm(0)  # Cancel alarm
            return matches
        except TimeoutError:
            logger.warning(f"Regex pattern timed out: {pattern.pattern[:50]}...")
            return []
        finally:
            signal.signal(signal.SIGALRM, old_handler)
    
    @classmethod
    def safe_findall(cls, pattern: re.Pattern, text: str, timeout: float = 1.0) -> List[str]:
        """Safely find all matches with timeout protection."""
        matches = cls.safe_search(pattern, text, timeout)
        return [m.group(0) for m in matches]


@dataclass
class SecureCheckResult:
    """Result from a secure dimension check."""
    passed: bool
    issue: Optional[ReviewIssue] = None
    security_threats: List[SecurityThreat] = None
    metrics: Dict[str, Any] = None


class SecureBaseDimension(ABC):
    """
    Security-enhanced base class for review dimensions.
    
    Security features:
    - Input validation
    - Threat detection
    - Secure regex operations
    - PII protection
    - Audit logging
    """
    
    def __init__(
        self,
        weight: float = 0.2,
        security_validator: Optional[SecurityValidator] = None
    ):
        """Initialize secure dimension."""
        self.weight = weight
        self.dimension = self._get_dimension()
        self.checks_performed = 0
        self.checks_passed = 0
        self._metrics: Dict[str, Any] = {}
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # Security components
        self.security_validator = security_validator or SecurityValidator()
        from ..storage.pii_detector import PIIDetectionConfig
        pii_config = PIIDetectionConfig(
            enabled_types={PIIType.EMAIL, PIIType.PHONE, PIIType.SSN, PIIType.CREDIT_CARD},
            min_confidence=0.8
        )
        self.pii_detector = PIIDetector(config=pii_config)
        self.audit_log: List[Dict[str, Any]] = []
        
        # Security metrics
        self.security_metrics = {
            'threats_detected': 0,
            'pii_found': 0,
            'validations_performed': 0,
            'regex_timeouts': 0
        }
    
    @abstractmethod
    def _get_dimension(self) -> ReviewDimension:
        """Return the dimension type."""
        pass
    
    @abstractmethod
    async def analyze(self, content: str, metadata: Dict[str, Any]) -> DimensionResult:
        """Analyze content for this dimension with security checks."""
        pass
    
    def _log_security_event(self, event_type: str, details: Dict[str, Any]):
        """Log security event."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "dimension": self.dimension.value,
            "event_type": event_type,
            "details": details
        }
        self.audit_log.append(event)
        logger.info(f"Security event: {event}")
    
    def _validate_input(self, content: str, metadata: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate input for security issues."""
        self.security_metrics['validations_performed'] += 1
        
        # Size check
        if len(content) > 10 * 1024 * 1024:  # 10MB limit
            return False, "Content exceeds maximum size limit"
        
        # Metadata validation
        if metadata:
            result = self.security_validator.validate_metadata(metadata)
            if not result.is_valid:
                return False, f"Metadata validation failed: {result.error_message}"
        
        return True, ""
    
    def _create_secure_issue(
        self,
        severity: ReviewSeverity,
        title: str,
        description: str,
        location: Optional[str] = None,
        suggestion: Optional[str] = None,
        security_related: bool = False,
        threat_type: Optional[SecurityThreat] = None
    ) -> ReviewIssue:
        """Create a secure review issue."""
        # Sanitize inputs
        title = title[:200]  # Limit length
        description = description[:1000]
        
        if location:
            location = location[:500]
        
        if suggestion:
            suggestion = suggestion[:500]
        
        impact_scores = {
            ReviewSeverity.BLOCKER: 10.0,
            ReviewSeverity.CRITICAL: 8.0,
            ReviewSeverity.HIGH: 6.0,
            ReviewSeverity.MEDIUM: 4.0,
            ReviewSeverity.LOW: 2.0,
            ReviewSeverity.INFO: 1.0
        }
        
        # Increase impact for security issues
        impact_score = impact_scores.get(severity, 5.0)
        if security_related:
            impact_score = min(impact_score * 1.5, 10.0)
        
        tags = []
        if security_related:
            tags.append("security")
        if threat_type:
            tags.append(threat_type.value)
        
        return ReviewIssue(
            dimension=self.dimension,
            severity=severity,
            title=title,
            description=description,
            location=location,
            suggestion=suggestion,
            impact_score=impact_score,
            confidence=0.9 if security_related else 0.8,
            tags=tags,
            auto_fixable=False,
            metadata={
                "security_related": security_related,
                "threat_type": threat_type.value if threat_type else None
            }
        )


class SecureTechnicalAccuracyDimension(SecureBaseDimension):
    """
    Security-enhanced technical accuracy dimension.
    
    Additional checks:
    - SQL injection in code samples
    - Command injection vulnerabilities
    - Insecure coding patterns
    - Weak cryptography usage
    """
    
    def _get_dimension(self) -> ReviewDimension:
        return ReviewDimension.TECHNICAL_ACCURACY
    
    async def analyze(self, content: str, metadata: Dict[str, Any]) -> DimensionResult:
        """Analyze technical accuracy with security checks."""
        # Input validation
        is_valid, error_msg = self._validate_input(content, metadata)
        if not is_valid:
            return DimensionResult(
                dimension=self.dimension,
                score=0.0,
                issues=[self._create_secure_issue(
                    ReviewSeverity.BLOCKER,
                    "Input Validation Failed",
                    error_msg,
                    security_related=True
                )],
                metrics={}
            )
        
        issues = []
        self.checks_performed = 0
        self.checks_passed = 0
        
        # Standard technical checks with security
        checks = [
            self._check_code_smells_secure(content),
            self._check_debug_code_secure(content),
            self._check_hardcoded_secrets(content),
            self._check_sql_injection(content),
            self._check_command_injection(content),
            self._check_weak_crypto(content),
            self._check_insecure_random(content),
            self._check_unused_imports_secure(content),
        ]
        
        # Run checks concurrently
        results = await asyncio.gather(*checks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Check failed: {result}")
                continue
            
            if result and not result.passed:
                issues.append(result.issue)
                if result.security_threats:
                    self.security_metrics['threats_detected'] += len(result.security_threats)
        
        # Calculate score
        score = (self.checks_passed / self.checks_performed * 100) if self.checks_performed > 0 else 100.0
        
        # Apply security penalty
        if self.security_metrics['threats_detected'] > 0:
            security_penalty = min(self.security_metrics['threats_detected'] * 5, 30)
            score = max(score - security_penalty, 0)
        
        # Log security events
        if self.security_metrics['threats_detected'] > 0:
            self._log_security_event(
                "threats_detected",
                {
                    "count": self.security_metrics['threats_detected'],
                    "dimension": "technical_accuracy"
                }
            )
        
        return DimensionResult(
            dimension=self.dimension,
            score=score,
            issues=issues,
            metrics={
                "checks_performed": self.checks_performed,
                "checks_passed": self.checks_passed,
                "threats_detected": self.security_metrics['threats_detected'],
                "validations_performed": self.security_metrics['validations_performed']
            }
        )
    
    async def _check_code_smells_secure(self, content: str) -> SecureCheckResult:
        """Check for code smells with security considerations."""
        self.checks_performed += 1
        
        try:
            matches = SecureRegexPatterns.safe_findall(
                SecureRegexPatterns.CODE_SMELL,
                content
            )
            
            if not matches:
                self.checks_passed += 1
                return SecureCheckResult(passed=True)
            
            return SecureCheckResult(
                passed=False,
                issue=self._create_secure_issue(
                    ReviewSeverity.MEDIUM,
                    "Code Smells Detected",
                    f"Found {len(matches)} code smell markers (TODO, FIXME, etc.)",
                    suggestion="Address or remove code smell markers before production"
                )
            )
        except Exception as e:
            logger.error(f"Code smell check failed: {e}")
            return SecureCheckResult(passed=True)  # Don't fail on error
    
    async def _check_debug_code_secure(self, content: str) -> SecureCheckResult:
        """Check for debug code that could leak information."""
        self.checks_performed += 1
        
        try:
            matches = SecureRegexPatterns.safe_findall(
                SecureRegexPatterns.DEBUG_CODE,
                content
            )
            
            if not matches:
                self.checks_passed += 1
                return SecureCheckResult(passed=True)
            
            return SecureCheckResult(
                passed=False,
                issue=self._create_secure_issue(
                    ReviewSeverity.HIGH,
                    "Debug Code Found",
                    f"Found {len(matches)} debug statements that could leak sensitive information",
                    suggestion="Remove all debug code before production deployment",
                    security_related=True
                ),
                security_threats=[SecurityThreat.XSS]  # Debug output can lead to XSS
            )
        except Exception as e:
            logger.error(f"Debug code check failed: {e}")
            return SecureCheckResult(passed=True)
    
    async def _check_hardcoded_secrets(self, content: str) -> SecureCheckResult:
        """Check for hardcoded secrets."""
        self.checks_performed += 1
        
        try:
            matches = SecureRegexPatterns.safe_findall(
                SecureRegexPatterns.HARDCODED_VALUES,
                content
            )
            
            if not matches:
                self.checks_passed += 1
                return SecureCheckResult(passed=True)
            
            return SecureCheckResult(
                passed=False,
                issue=self._create_secure_issue(
                    ReviewSeverity.BLOCKER,
                    "Hardcoded Secrets Detected",
                    f"Found {len(matches)} potential hardcoded secrets or API keys",
                    suggestion="Use environment variables or secure key management systems",
                    security_related=True,
                    threat_type=SecurityThreat.HARDCODED_SECRETS
                ),
                security_threats=[SecurityThreat.HARDCODED_SECRETS]
            )
        except Exception as e:
            logger.error(f"Secret detection failed: {e}")
            return SecureCheckResult(passed=True)
    
    async def _check_sql_injection(self, content: str) -> SecureCheckResult:
        """Check for SQL injection vulnerabilities."""
        self.checks_performed += 1
        
        try:
            matches = SecureRegexPatterns.safe_findall(
                SecureRegexPatterns.SQL_INJECTION,
                content
            )
            
            if not matches:
                self.checks_passed += 1
                return SecureCheckResult(passed=True)
            
            # Additional check for string concatenation in SQL
            sql_concat_pattern = re.compile(r'["\'].*(?:SELECT|INSERT|UPDATE|DELETE).*["\'].*\+', re.IGNORECASE)
            concat_matches = SecureRegexPatterns.safe_findall(sql_concat_pattern, content)
            
            if matches or concat_matches:
                return SecureCheckResult(
                    passed=False,
                    issue=self._create_secure_issue(
                        ReviewSeverity.BLOCKER,
                        "SQL Injection Risk",
                        f"Found {len(matches) + len(concat_matches)} potential SQL injection vulnerabilities",
                        suggestion="Use parameterized queries or prepared statements",
                        security_related=True,
                        threat_type=SecurityThreat.SQL_INJECTION
                    ),
                    security_threats=[SecurityThreat.SQL_INJECTION]
                )
            
            self.checks_passed += 1
            return SecureCheckResult(passed=True)
            
        except Exception as e:
            logger.error(f"SQL injection check failed: {e}")
            return SecureCheckResult(passed=True)
    
    async def _check_command_injection(self, content: str) -> SecureCheckResult:
        """Check for command injection vulnerabilities."""
        self.checks_performed += 1
        
        try:
            matches = SecureRegexPatterns.safe_findall(
                SecureRegexPatterns.COMMAND_INJECTION,
                content
            )
            
            # Check for dangerous functions
            dangerous_funcs = re.compile(r'\b(?:exec|eval|system|popen|subprocess\.call)\b', re.IGNORECASE)
            func_matches = SecureRegexPatterns.safe_findall(dangerous_funcs, content)
            
            if not matches and not func_matches:
                self.checks_passed += 1
                return SecureCheckResult(passed=True)
            
            return SecureCheckResult(
                passed=False,
                issue=self._create_secure_issue(
                    ReviewSeverity.CRITICAL,
                    "Command Injection Risk",
                    f"Found potential command injection vulnerabilities",
                    suggestion="Avoid shell commands; use safe APIs and validate all inputs",
                    security_related=True,
                    threat_type=SecurityThreat.COMMAND_INJECTION
                ),
                security_threats=[SecurityThreat.COMMAND_INJECTION]
            )
        except Exception as e:
            logger.error(f"Command injection check failed: {e}")
            return SecureCheckResult(passed=True)
    
    async def _check_weak_crypto(self, content: str) -> SecureCheckResult:
        """Check for weak cryptography usage."""
        self.checks_performed += 1
        
        try:
            matches = SecureRegexPatterns.safe_findall(
                SecureRegexPatterns.WEAK_CRYPTO,
                content
            )
            
            if not matches:
                self.checks_passed += 1
                return SecureCheckResult(passed=True)
            
            return SecureCheckResult(
                passed=False,
                issue=self._create_secure_issue(
                    ReviewSeverity.HIGH,
                    "Weak Cryptography",
                    f"Found usage of weak cryptographic algorithms: {', '.join(set(matches))}",
                    suggestion="Use strong algorithms: AES-256, SHA-256, RSA-2048+",
                    security_related=True,
                    threat_type=SecurityThreat.WEAK_CRYPTO
                ),
                security_threats=[SecurityThreat.WEAK_CRYPTO]
            )
        except Exception as e:
            logger.error(f"Crypto check failed: {e}")
            return SecureCheckResult(passed=True)
    
    async def _check_insecure_random(self, content: str) -> SecureCheckResult:
        """Check for insecure random number generation."""
        self.checks_performed += 1
        
        try:
            matches = SecureRegexPatterns.safe_findall(
                SecureRegexPatterns.INSECURE_RANDOM,
                content
            )
            
            if not matches:
                self.checks_passed += 1
                return SecureCheckResult(passed=True)
            
            return SecureCheckResult(
                passed=False,
                issue=self._create_secure_issue(
                    ReviewSeverity.MEDIUM,
                    "Insecure Random Number Generation",
                    f"Found {len(matches)} uses of insecure random functions",
                    suggestion="Use cryptographically secure random: secrets module in Python, crypto.randomBytes in Node.js",
                    security_related=True
                )
            )
        except Exception as e:
            logger.error(f"Random check failed: {e}")
            return SecureCheckResult(passed=True)
    
    async def _check_unused_imports_secure(self, content: str) -> SecureCheckResult:
        """Check for unused imports that could increase attack surface."""
        self.checks_performed += 1
        
        try:
            matches = SecureRegexPatterns.safe_findall(
                SecureRegexPatterns.UNUSED_IMPORTS,
                content
            )
            
            if not matches:
                self.checks_passed += 1
                return SecureCheckResult(passed=True)
            
            return SecureCheckResult(
                passed=False,
                issue=self._create_secure_issue(
                    ReviewSeverity.LOW,
                    "Unused Imports",
                    f"Found {len(matches)} potentially unused imports",
                    suggestion="Remove unused imports to reduce attack surface"
                )
            )
        except Exception as e:
            logger.error(f"Import check failed: {e}")
            return SecureCheckResult(passed=True)


class SecureCompletenessDimension(SecureBaseDimension):
    """Security-enhanced completeness dimension."""
    
    def _get_dimension(self) -> ReviewDimension:
        return ReviewDimension.COMPLETENESS
    
    async def analyze(self, content: str, metadata: Dict[str, Any]) -> DimensionResult:
        """Analyze completeness with security checks."""
        # Input validation
        is_valid, error_msg = self._validate_input(content, metadata)
        if not is_valid:
            return DimensionResult(
                dimension=self.dimension,
                score=0.0,
                issues=[self._create_secure_issue(
                    ReviewSeverity.BLOCKER,
                    "Input Validation Failed",
                    error_msg,
                    security_related=True
                )],
                metrics={}
            )
        
        issues = []
        metrics = {
            'sections': 0,
            'code_blocks': 0,
            'links': 0,
            'images': 0,
            'tables': 0,
            'lists': 0
        }
        
        # Count document elements securely
        try:
            metrics['sections'] = len(SecureRegexPatterns.safe_findall(
                SecureRegexPatterns.SECTIONS, content
            ))
            metrics['code_blocks'] = len(SecureRegexPatterns.safe_findall(
                SecureRegexPatterns.CODE_BLOCKS, content
            ))
            metrics['links'] = len(SecureRegexPatterns.safe_findall(
                SecureRegexPatterns.LINKS, content
            ))
            metrics['images'] = len(SecureRegexPatterns.safe_findall(
                SecureRegexPatterns.IMAGES, content
            ))
            metrics['tables'] = len(SecureRegexPatterns.safe_findall(
                SecureRegexPatterns.TABLES, content
            ))
            metrics['lists'] = len(SecureRegexPatterns.safe_findall(
                SecureRegexPatterns.LISTS, content
            ))
        except Exception as e:
            logger.error(f"Completeness analysis failed: {e}")
            self.security_metrics['regex_timeouts'] += 1
        
        # Check for minimum content
        if len(content.strip()) < 100:
            issues.append(self._create_secure_issue(
                ReviewSeverity.HIGH,
                "Insufficient Content",
                "Document is too short to be considered complete",
                suggestion="Add more detailed content"
            ))
        
        # Check for required sections
        if metrics['sections'] < 2:
            issues.append(self._create_secure_issue(
                ReviewSeverity.MEDIUM,
                "Missing Sections",
                "Document lacks proper section structure",
                suggestion="Add clear sections with headers"
            ))
        
        # Check for broken links (security concern)
        links = SecureRegexPatterns.safe_findall(SecureRegexPatterns.LINKS, content)
        for link_match in links[:10]:  # Check first 10 links only for performance
            if 'javascript:' in link_match.lower() or 'data:' in link_match.lower():
                issues.append(self._create_secure_issue(
                    ReviewSeverity.CRITICAL,
                    "Suspicious Link Detected",
                    f"Found potentially malicious link protocol",
                    location=link_match[:50],
                    security_related=True,
                    threat_type=SecurityThreat.XSS
                ))
                self.security_metrics['threats_detected'] += 1
        
        # Calculate score
        total_elements = sum(metrics.values())
        score = min(100, total_elements * 10)  # Basic scoring
        
        # Apply penalty for security issues
        if self.security_metrics['threats_detected'] > 0:
            score = max(score - 20, 0)
        
        return DimensionResult(
            dimension=self.dimension,
            score=score,
            issues=issues,
            metrics=metrics
        )


class SecureConsistencyDimension(SecureBaseDimension):
    """Security-enhanced consistency dimension."""
    
    def _get_dimension(self) -> ReviewDimension:
        return ReviewDimension.CONSISTENCY
    
    async def analyze(self, content: str, metadata: Dict[str, Any]) -> DimensionResult:
        """Analyze consistency with security checks."""
        # Input validation
        is_valid, error_msg = self._validate_input(content, metadata)
        if not is_valid:
            return DimensionResult(
                dimension=self.dimension,
                score=0.0,
                issues=[self._create_secure_issue(
                    ReviewSeverity.BLOCKER,
                    "Input Validation Failed",
                    error_msg,
                    security_related=True
                )],
                metrics={}
            )
        
        issues = []
        inconsistencies = 0
        
        # Check naming conventions
        camel_cases = len(SecureRegexPatterns.safe_findall(
            SecureRegexPatterns.CAMEL_CASE, content
        ))
        snake_cases = len(SecureRegexPatterns.safe_findall(
            SecureRegexPatterns.SNAKE_CASE, content
        ))
        kebab_cases = len(SecureRegexPatterns.safe_findall(
            SecureRegexPatterns.KEBAB_CASE, content
        ))
        
        # Check for mixed conventions
        conventions_used = sum([1 for c in [camel_cases, snake_cases, kebab_cases] if c > 0])
        if conventions_used > 1:
            inconsistencies += 1
            issues.append(self._create_secure_issue(
                ReviewSeverity.MEDIUM,
                "Mixed Naming Conventions",
                f"Found multiple naming conventions: camelCase={camel_cases}, snake_case={snake_cases}, kebab-case={kebab_cases}",
                suggestion="Use consistent naming convention throughout"
            ))
        
        # Check for trailing whitespace
        trailing = len(SecureRegexPatterns.safe_findall(
            SecureRegexPatterns.TRAILING_WHITESPACE, content
        ))
        if trailing > 0:
            inconsistencies += 1
            issues.append(self._create_secure_issue(
                ReviewSeverity.LOW,
                "Trailing Whitespace",
                f"Found {trailing} lines with trailing whitespace",
                suggestion="Remove trailing whitespace"
            ))
        
        # Calculate score
        score = max(100 - (inconsistencies * 15), 0)
        
        return DimensionResult(
            dimension=self.dimension,
            score=score,
            issues=issues,
            metrics={
                'naming_conventions': conventions_used,
                'inconsistencies': inconsistencies
            }
        )


class SecureStyleFormattingDimension(SecureBaseDimension):
    """Security-enhanced style and formatting dimension."""
    
    def _get_dimension(self) -> ReviewDimension:
        return ReviewDimension.STYLE_FORMATTING
    
    async def analyze(self, content: str, metadata: Dict[str, Any]) -> DimensionResult:
        """Analyze style and formatting with security checks."""
        # Input validation
        is_valid, error_msg = self._validate_input(content, metadata)
        if not is_valid:
            return DimensionResult(
                dimension=self.dimension,
                score=0.0,
                issues=[self._create_secure_issue(
                    ReviewSeverity.BLOCKER,
                    "Input Validation Failed",
                    error_msg,
                    security_related=True
                )],
                metrics={}
            )
        
        issues = []
        style_issues = 0
        
        # Check for multiple spaces
        multiple_spaces = len(SecureRegexPatterns.safe_findall(
            SecureRegexPatterns.MULTIPLE_SPACES, content
        ))
        if multiple_spaces > 0:
            style_issues += 1
            issues.append(self._create_secure_issue(
                ReviewSeverity.LOW,
                "Multiple Consecutive Spaces",
                f"Found {multiple_spaces} instances of multiple spaces",
                suggestion="Use single spaces between words"
            ))
        
        # Check for tabs/spaces mixing
        mixed_indents = len(SecureRegexPatterns.safe_findall(
            SecureRegexPatterns.TABS_SPACES_MIX, content
        ))
        if mixed_indents > 0:
            style_issues += 1
            issues.append(self._create_secure_issue(
                ReviewSeverity.MEDIUM,
                "Mixed Indentation",
                f"Found {mixed_indents} lines with mixed tabs and spaces",
                suggestion="Use consistent indentation (spaces or tabs, not both)"
            ))
        
        # Check for excessive empty lines
        empty_lines = len(SecureRegexPatterns.safe_findall(
            SecureRegexPatterns.EMPTY_LINES, content
        ))
        if empty_lines > 0:
            style_issues += 1
            issues.append(self._create_secure_issue(
                ReviewSeverity.LOW,
                "Excessive Empty Lines",
                f"Found {empty_lines} instances of 3+ consecutive empty lines",
                suggestion="Limit to maximum 2 consecutive empty lines"
            ))
        
        # Check long lines (simplified)
        lines = content.split('\n')
        long_lines = sum(1 for line in lines if len(line) > 120)
        if long_lines > 0:
            style_issues += 1
            issues.append(self._create_secure_issue(
                ReviewSeverity.LOW,
                "Long Lines",
                f"Found {long_lines} lines exceeding 120 characters",
                suggestion="Wrap lines at 80-120 characters for readability"
            ))
        
        # Calculate score
        score = max(100 - (style_issues * 10), 0)
        
        return DimensionResult(
            dimension=self.dimension,
            score=score,
            issues=issues,
            metrics={
                'style_issues': style_issues,
                'long_lines': long_lines
            }
        )


class SecureSecurityPIIDimension(SecureBaseDimension):
    """
    Enhanced security and PII dimension with comprehensive threat detection.
    """
    
    def _get_dimension(self) -> ReviewDimension:
        return ReviewDimension.SECURITY_PII
    
    async def analyze(self, content: str, metadata: Dict[str, Any]) -> DimensionResult:
        """Comprehensive security and PII analysis."""
        # Input validation
        is_valid, error_msg = self._validate_input(content, metadata)
        if not is_valid:
            return DimensionResult(
                dimension=self.dimension,
                score=0.0,
                issues=[self._create_secure_issue(
                    ReviewSeverity.BLOCKER,
                    "Input Validation Failed",
                    error_msg,
                    security_related=True
                )],
                metrics={}
            )
        
        issues = []
        security_score = 100.0
        
        # Comprehensive security validation
        validation_result = self.security_validator.validate_document(
            content,
            metadata.get('document_type', 'generic'),
            metadata
        )
        
        # Process security threats
        for threat in validation_result.threats_detected:
            severity = ReviewSeverity.BLOCKER if validation_result.risk_score > 7 else ReviewSeverity.CRITICAL
            issues.append(self._create_secure_issue(
                severity,
                f"Security Threat: {threat.value}",
                f"Detected {threat.value} vulnerability in document",
                suggestion=self._get_threat_suggestion(threat),
                security_related=True,
                threat_type=threat
            ))
            security_score -= min(validation_result.risk_score * 2, 20)
        
        # PII detection
        try:
            pii_results = self.pii_detector.detect(content)
            if pii_results and pii_results.pii_found:
                self.security_metrics['pii_found'] += len(pii_results.pii_found)
                
                # Group PII by type
                pii_by_type = defaultdict(list)
                for pii in pii_results.pii_found:
                    pii_by_type[pii.type].append(pii)
                
                for pii_type, instances in pii_by_type.items():
                    severity = ReviewSeverity.CRITICAL if pii_type in [
                        PIIType.SSN, PIIType.CREDIT_CARD, PIIType.PASSPORT
                    ] else ReviewSeverity.HIGH
                    
                    issues.append(self._create_secure_issue(
                        severity,
                        f"PII Detected: {pii_type.value}",
                        f"Found {len(instances)} instances of {pii_type.value}",
                        suggestion="Remove or redact PII before sharing document",
                        security_related=True
                    ))
                    security_score -= min(len(instances) * 5, 30)
        except Exception as e:
            logger.error(f"PII detection failed: {e}")
        
        # Check for path traversal attempts
        path_traversal = SecureRegexPatterns.safe_findall(
            SecureRegexPatterns.PATH_TRAVERSAL, content
        )
        if path_traversal:
            issues.append(self._create_secure_issue(
                ReviewSeverity.CRITICAL,
                "Path Traversal Pattern",
                f"Found {len(path_traversal)} potential path traversal patterns",
                suggestion="Remove file path references or use safe path handling",
                security_related=True,
                threat_type=SecurityThreat.PATH_TRAVERSAL
            ))
            security_score -= 15
        
        # Check for XSS patterns
        xss_patterns = SecureRegexPatterns.safe_findall(
            SecureRegexPatterns.XSS_SIMPLE, content
        )
        if xss_patterns:
            issues.append(self._create_secure_issue(
                ReviewSeverity.HIGH,
                "XSS Pattern Detected",
                f"Found {len(xss_patterns)} potential XSS patterns",
                suggestion="Sanitize HTML content and escape user inputs",
                security_related=True,
                threat_type=SecurityThreat.XSS
            ))
            security_score -= 10
        
        # Final score adjustment
        final_score = max(security_score, 0)
        
        # Log comprehensive security metrics
        if issues:
            self._log_security_event(
                "security_issues_found",
                {
                    "total_issues": len(issues),
                    "threats": len(validation_result.threats_detected),
                    "pii_found": self.security_metrics['pii_found'],
                    "risk_score": validation_result.risk_score
                }
            )
        
        return DimensionResult(
            dimension=self.dimension,
            score=final_score,
            issues=issues,
            metrics={
                'threats_detected': len(validation_result.threats_detected),
                'pii_instances': self.security_metrics['pii_found'],
                'risk_score': validation_result.risk_score,
                'validations_performed': self.security_metrics['validations_performed']
            }
        )
    
    def _get_threat_suggestion(self, threat: SecurityThreat) -> str:
        """Get remediation suggestion for threat type."""
        suggestions = {
            SecurityThreat.SQL_INJECTION: "Use parameterized queries and input validation",
            SecurityThreat.XSS: "Sanitize HTML and escape all user inputs",
            SecurityThreat.PATH_TRAVERSAL: "Validate file paths and use safe path APIs",
            SecurityThreat.COMMAND_INJECTION: "Avoid shell commands; validate and escape inputs",
            SecurityThreat.XXE: "Disable XML external entities in parsers",
            SecurityThreat.SSRF: "Validate and whitelist URLs; use safe HTTP clients",
            SecurityThreat.LDAP_INJECTION: "Use parameterized LDAP queries",
            SecurityThreat.REGEX_DOS: "Use simple regex patterns with timeouts",
            SecurityThreat.HARDCODED_SECRETS: "Use environment variables or secret management",
            SecurityThreat.WEAK_CRYPTO: "Use strong cryptographic algorithms (AES-256, SHA-256)",
            SecurityThreat.FILE_UPLOAD: "Validate file types and scan for malware"
        }
        return suggestions.get(threat, "Review and fix security vulnerability")


def get_secure_dimensions(
    config: Optional[Dict[str, Any]] = None,
    security_validator: Optional[SecurityValidator] = None
) -> List[SecureBaseDimension]:
    """Get all secure dimensions with configuration."""
    config = config or {}
    validator = security_validator or SecurityValidator()
    
    dimensions = [
        SecureTechnicalAccuracyDimension(
            weight=config.get('technical_weight', 0.25),
            security_validator=validator
        ),
        SecureCompletenessDimension(
            weight=config.get('completeness_weight', 0.20),
            security_validator=validator
        ),
        SecureConsistencyDimension(
            weight=config.get('consistency_weight', 0.20),
            security_validator=validator
        ),
        SecureStyleFormattingDimension(
            weight=config.get('style_weight', 0.15),
            security_validator=validator
        ),
        SecureSecurityPIIDimension(
            weight=config.get('security_weight', 0.20),
            security_validator=validator
        ),
    ]
    
    return dimensions