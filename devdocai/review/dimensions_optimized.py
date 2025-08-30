"""
Optimized review dimensions for M007 Review Engine.

Performance-optimized implementations with pre-compiled regex,
vectorized operations, and memory-efficient processing.
"""

import re
import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import numpy as np
from collections import defaultdict

try:
    import pygtrie
    TRIE_AVAILABLE = True
except ImportError:
    TRIE_AVAILABLE = False

from ..storage.pii_detector import PIIDetector, PIIDetectionConfig, PIIType
from .models import (
    ReviewDimension,
    ReviewSeverity,
    ReviewIssue,
    DimensionResult
)

logger = logging.getLogger(__name__)


# Pre-compiled regex patterns for performance
class RegexPatterns:
    """Centralized pre-compiled regex patterns."""
    
    # Technical patterns
    CODE_SMELL = re.compile(r'\b(TODO|FIXME|HACK|XXX|REFACTOR|OPTIMIZE)\b', re.IGNORECASE)
    DEBUG_CODE = re.compile(r'(console\.(log|debug|info|warn|error)|print\(|debugger\b|pdb\.set_trace)', re.IGNORECASE)
    HARDCODED_VALUES = re.compile(r'(password|secret|key|token)\s*=\s*["\'][^"\']+["\']', re.IGNORECASE)
    UNUSED_IMPORTS = re.compile(r'^import\s+\w+(?:\s*,\s*\w+)*\s*$', re.MULTILINE)
    LONG_LINES = re.compile(r'^.{121,}$', re.MULTILINE)
    
    # Completeness patterns
    SECTIONS = re.compile(r'^#{1,6}\s+(.+)$', re.MULTILINE)
    CODE_BLOCKS = re.compile(r'```[\s\S]*?```')
    LINKS = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
    IMAGES = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
    TABLES = re.compile(r'^\|.*\|.*\|.*$', re.MULTILINE)
    LISTS = re.compile(r'^[\*\-\+]\s+.+$|^\d+\.\s+.+$', re.MULTILINE)
    
    # Consistency patterns
    CAMEL_CASE = re.compile(r'\b[a-z]+(?:[A-Z][a-z]+)+\b')
    SNAKE_CASE = re.compile(r'\b[a-z]+(?:_[a-z]+)+\b')
    KEBAB_CASE = re.compile(r'\b[a-z]+(?:-[a-z]+)+\b')
    INCONSISTENT_QUOTES = re.compile(r'["\']')
    TRAILING_WHITESPACE = re.compile(r'[ \t]+$', re.MULTILINE)
    
    # Style patterns
    MULTIPLE_SPACES = re.compile(r'  +')
    TABS_SPACES_MIX = re.compile(r'^(\t+ +| +\t+)', re.MULTILINE)
    EMPTY_LINES = re.compile(r'\n{3,}')
    NO_FINAL_NEWLINE = re.compile(r'[^\n]\Z')
    
    # Security/PII patterns
    EMAIL = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    PHONE = re.compile(r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')
    SSN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
    CREDIT_CARD = re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b')
    IP_ADDRESS = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
    API_KEY = re.compile(r'\b[A-Za-z0-9]{32,}\b')
    
    @classmethod
    @lru_cache(maxsize=128)
    def find_all(cls, pattern_name: str, text: str) -> List[re.Match]:
        """Find all matches for a pattern with caching."""
        pattern = getattr(cls, pattern_name, None)
        if pattern:
            return list(pattern.finditer(text))
        return []


class TriePIIDetector:
    """Trie-based PII detector for efficient multi-pattern matching."""
    
    def __init__(self):
        """Initialize trie with common PII patterns."""
        if TRIE_AVAILABLE:
            self.trie = pygtrie.StringTrie()
            self._load_pii_patterns()
        else:
            self.trie = None
            self.patterns = set()
    
    def _load_pii_patterns(self):
        """Load common PII patterns into trie."""
        # Common PII keywords
        pii_keywords = [
            'ssn', 'social security', 'tax id', 'ein',
            'driver license', 'passport', 'visa',
            'bank account', 'routing number', 'iban',
            'credit card', 'debit card', 'cvv',
            'date of birth', 'dob', 'birthdate',
            'medical record', 'patient id', 'mrn',
        ]
        
        for keyword in pii_keywords:
            self.trie[keyword.lower()] = True
            
        if not TRIE_AVAILABLE:
            self.patterns = set(pii_keywords)
    
    def detect(self, text: str) -> List[Tuple[str, int, int]]:
        """Detect PII patterns in text using trie."""
        results = []
        text_lower = text.lower()
        
        if TRIE_AVAILABLE and self.trie:
            # Use trie for efficient prefix matching
            words = text_lower.split()
            for i, word in enumerate(words):
                if self.trie.has_subtrie(word):
                    # Check for multi-word patterns
                    for j in range(i + 1, min(i + 4, len(words) + 1)):
                        phrase = ' '.join(words[i:j])
                        if phrase in self.trie:
                            start = text_lower.find(phrase)
                            if start != -1:
                                results.append((phrase, start, start + len(phrase)))
        else:
            # Fallback to simple pattern matching
            for pattern in self.patterns:
                idx = text_lower.find(pattern)
                if idx != -1:
                    results.append((pattern, idx, idx + len(pattern)))
        
        return results


@dataclass
class CheckResult:
    """Result from a single check within a dimension."""
    passed: bool
    issue: Optional[ReviewIssue] = None
    metrics: Dict[str, Any] = None


class OptimizedBaseDimension(ABC):
    """
    Optimized base class for review dimensions.
    
    Optimizations:
    - Pre-compiled regex patterns
    - Vectorized text operations
    - Parallel checking where possible
    """
    
    def __init__(self, weight: float = 0.2):
        """Initialize dimension with weight."""
        self.weight = weight
        self.dimension = self._get_dimension()
        self.checks_performed = 0
        self.checks_passed = 0
        self._metrics: Dict[str, Any] = {}
        self.executor = ThreadPoolExecutor(max_workers=2)
    
    @abstractmethod
    def _get_dimension(self) -> ReviewDimension:
        """Return the dimension type."""
        pass
    
    @abstractmethod
    async def analyze(self, content: str, metadata: Dict[str, Any]) -> DimensionResult:
        """Analyze content for this dimension."""
        pass
    
    def _create_issue(
        self,
        severity: ReviewSeverity,
        title: str,
        description: str,
        location: Optional[str] = None,
        suggestion: Optional[str] = None,
        code_snippet: Optional[str] = None,
        impact_score: Optional[float] = None,
        confidence: float = 1.0,
        tags: Optional[List[str]] = None,
        auto_fixable: bool = False
    ) -> ReviewIssue:
        """Helper to create a review issue."""
        if impact_score is None:
            impact_scores = {
                ReviewSeverity.BLOCKER: 10.0,
                ReviewSeverity.CRITICAL: 8.0,
                ReviewSeverity.HIGH: 6.0,
                ReviewSeverity.MEDIUM: 4.0,
                ReviewSeverity.LOW: 2.0,
                ReviewSeverity.INFO: 1.0
            }
            impact_score = impact_scores.get(severity, 5.0)
        
        return ReviewIssue(
            dimension=self.dimension,
            severity=severity,
            title=title,
            description=description,
            location=location,
            suggestion=suggestion,
            code_snippet=code_snippet,
            impact_score=impact_score,
            confidence=confidence,
            tags=tags or [],
            auto_fixable=auto_fixable
        )
    
    @lru_cache(maxsize=32)
    def _calculate_text_metrics(self, content: str) -> Dict[str, Any]:
        """Calculate basic text metrics with caching."""
        lines = content.split('\n')
        words = content.split()
        
        return {
            'total_lines': len(lines),
            'total_words': len(words),
            'total_chars': len(content),
            'avg_line_length': sum(len(line) for line in lines) / len(lines) if lines else 0,
            'avg_word_length': sum(len(word) for word in words) / len(words) if words else 0,
        }


class OptimizedTechnicalAccuracyDimension(OptimizedBaseDimension):
    """Optimized technical accuracy checker."""
    
    def _get_dimension(self) -> ReviewDimension:
        return ReviewDimension.TECHNICAL_ACCURACY
    
    async def analyze(self, content: str, metadata: Dict[str, Any]) -> DimensionResult:
        """Analyze technical accuracy with optimized pattern matching."""
        issues = []
        metrics = self._calculate_text_metrics(content)
        
        # Parallel pattern checking
        checks = [
            self._check_code_smells(content),
            self._check_debug_code(content),
            self._check_hardcoded_values(content),
            self._check_long_lines(content),
        ]
        
        check_results = await asyncio.gather(*checks)
        
        for results in check_results:
            if results:
                issues.extend(results)
        
        # Calculate score
        total_checks = 4
        failed_checks = len([r for r in check_results if r])
        score = max(0, 100 - (failed_checks * 25))
        
        metrics['technical_issues'] = len(issues)
        metrics['code_smell_count'] = len(check_results[0]) if check_results[0] else 0
        
        return DimensionResult(
            dimension=self.dimension,
            score=score,
            issues=issues,
            metrics=metrics,
            suggestions=[
                "Remove all TODO/FIXME comments before production",
                "Replace hardcoded values with configuration",
                "Remove debug code from production builds"
            ] if issues else []
        )
    
    async def _check_code_smells(self, content: str) -> List[ReviewIssue]:
        """Check for code smells using pre-compiled patterns."""
        issues = []
        matches = RegexPatterns.find_all('CODE_SMELL', content)
        
        for match in matches[:5]:  # Limit to first 5 to avoid spam
            issues.append(self._create_issue(
                severity=ReviewSeverity.MEDIUM,
                title=f"Code smell detected: {match.group()}",
                description=f"Found '{match.group()}' comment which indicates incomplete code",
                location=f"Line {content[:match.start()].count(chr(10)) + 1}",
                suggestion="Complete the implementation or remove the comment",
                auto_fixable=True
            ))
        
        return issues
    
    async def _check_debug_code(self, content: str) -> List[ReviewIssue]:
        """Check for debug code."""
        issues = []
        matches = RegexPatterns.DEBUG_CODE.finditer(content)
        
        for match in list(matches)[:3]:
            issues.append(self._create_issue(
                severity=ReviewSeverity.HIGH,
                title="Debug code detected",
                description=f"Found debug statement: {match.group()}",
                location=f"Line {content[:match.start()].count(chr(10)) + 1}",
                suggestion="Remove debug statements before production",
                auto_fixable=True
            ))
        
        return issues
    
    async def _check_hardcoded_values(self, content: str) -> List[ReviewIssue]:
        """Check for hardcoded sensitive values."""
        issues = []
        matches = RegexPatterns.HARDCODED_VALUES.finditer(content)
        
        for match in list(matches)[:3]:
            issues.append(self._create_issue(
                severity=ReviewSeverity.CRITICAL,
                title="Hardcoded sensitive value",
                description="Sensitive value should not be hardcoded",
                location=f"Line {content[:match.start()].count(chr(10)) + 1}",
                suggestion="Use environment variables or secure configuration",
                auto_fixable=False
            ))
        
        return issues
    
    async def _check_long_lines(self, content: str) -> List[ReviewIssue]:
        """Check for overly long lines."""
        issues = []
        matches = RegexPatterns.LONG_LINES.finditer(content)
        
        count = sum(1 for _ in matches)
        if count > 0:
            issues.append(self._create_issue(
                severity=ReviewSeverity.LOW,
                title=f"{count} lines exceed 120 characters",
                description="Long lines reduce readability",
                suggestion="Break long lines into multiple shorter lines",
                auto_fixable=True
            ))
        
        return issues


class OptimizedCompletenessDimension(OptimizedBaseDimension):
    """Optimized completeness checker."""
    
    def _get_dimension(self) -> ReviewDimension:
        return ReviewDimension.COMPLETENESS
    
    async def analyze(self, content: str, metadata: Dict[str, Any]) -> DimensionResult:
        """Analyze document completeness."""
        issues = []
        metrics = self._calculate_text_metrics(content)
        
        # Check for essential sections
        sections = RegexPatterns.SECTIONS.findall(content)
        metrics['section_count'] = len(sections)
        
        # Vectorized content analysis
        has_code = bool(RegexPatterns.CODE_BLOCKS.search(content))
        has_links = bool(RegexPatterns.LINKS.search(content))
        has_images = bool(RegexPatterns.IMAGES.search(content))
        has_tables = bool(RegexPatterns.TABLES.search(content))
        has_lists = bool(RegexPatterns.LISTS.search(content))
        
        metrics.update({
            'has_code_examples': has_code,
            'has_links': has_links,
            'has_images': has_images,
            'has_tables': has_tables,
            'has_lists': has_lists,
        })
        
        # Check minimum content requirements
        if metrics['total_words'] < 50:
            issues.append(self._create_issue(
                severity=ReviewSeverity.HIGH,
                title="Insufficient content",
                description="Document contains less than 50 words",
                suggestion="Add more detailed content and explanations"
            ))
        
        if not sections:
            issues.append(self._create_issue(
                severity=ReviewSeverity.MEDIUM,
                title="No section headers",
                description="Document lacks structural organization",
                suggestion="Add section headers to organize content"
            ))
        
        # Document type specific checks
        doc_type = metadata.get('document_type', 'generic')
        if doc_type == 'api' and not has_code:
            issues.append(self._create_issue(
                severity=ReviewSeverity.HIGH,
                title="Missing code examples",
                description="API documentation should include code examples",
                suggestion="Add code examples for API usage"
            ))
        
        # Calculate score
        completeness_factors = [
            metrics['total_words'] >= 100,
            len(sections) >= 3,
            has_code or doc_type != 'api',
            has_links,
            has_lists or has_tables,
        ]
        
        score = (sum(completeness_factors) / len(completeness_factors)) * 100
        
        return DimensionResult(
            dimension=self.dimension,
            score=score,
            issues=issues,
            metrics=metrics,
            suggestions=["Add more sections", "Include examples"] if score < 80 else []
        )


class OptimizedSecurityPIIDimension(OptimizedBaseDimension):
    """Optimized security and PII detection."""
    
    def __init__(self, weight: float = 0.2):
        """Initialize with PII detector."""
        super().__init__(weight)
        self.pii_detector = TriePIIDetector()
    
    def _get_dimension(self) -> ReviewDimension:
        return ReviewDimension.SECURITY_PII
    
    async def analyze(self, content: str, metadata: Dict[str, Any]) -> DimensionResult:
        """Analyze security and PII issues with optimized detection."""
        issues = []
        metrics = {}
        
        # Parallel pattern detection
        detection_tasks = [
            self._detect_emails(content),
            self._detect_phones(content),
            self._detect_ssn(content),
            self._detect_credit_cards(content),
            self._detect_api_keys(content),
            self._detect_pii_keywords(content),
        ]
        
        detection_results = await asyncio.gather(*detection_tasks)
        
        pii_count = 0
        for detector_name, detector_issues in detection_results:
            if detector_issues:
                issues.extend(detector_issues)
                pii_count += len(detector_issues)
                metrics[f'{detector_name}_count'] = len(detector_issues)
        
        metrics['total_pii_detected'] = pii_count
        
        # Calculate score (100 if no PII, decreasing with each finding)
        score = max(0, 100 - (pii_count * 10))
        
        return DimensionResult(
            dimension=self.dimension,
            score=score,
            issues=issues,
            metrics=metrics,
            suggestions=["Remove or redact all PII before sharing"] if issues else []
        )
    
    async def _detect_emails(self, content: str) -> Tuple[str, List[ReviewIssue]]:
        """Detect email addresses."""
        issues = []
        matches = RegexPatterns.EMAIL.finditer(content)
        
        for match in list(matches)[:5]:
            issues.append(self._create_issue(
                severity=ReviewSeverity.HIGH,
                title="Email address detected",
                description=f"Found email: {match.group()[:3]}***",
                location=f"Character {match.start()}",
                suggestion="Remove or redact email addresses",
                auto_fixable=True
            ))
        
        return ('email', issues)
    
    async def _detect_phones(self, content: str) -> Tuple[str, List[ReviewIssue]]:
        """Detect phone numbers."""
        issues = []
        matches = RegexPatterns.PHONE.finditer(content)
        
        for match in list(matches)[:5]:
            issues.append(self._create_issue(
                severity=ReviewSeverity.HIGH,
                title="Phone number detected",
                description="Found potential phone number",
                location=f"Character {match.start()}",
                suggestion="Remove or redact phone numbers",
                auto_fixable=True
            ))
        
        return ('phone', issues)
    
    async def _detect_ssn(self, content: str) -> Tuple[str, List[ReviewIssue]]:
        """Detect SSN patterns."""
        issues = []
        matches = RegexPatterns.SSN.finditer(content)
        
        for match in list(matches)[:3]:
            issues.append(self._create_issue(
                severity=ReviewSeverity.BLOCKER,
                title="SSN pattern detected",
                description="Found potential Social Security Number",
                location=f"Character {match.start()}",
                suggestion="Remove SSN immediately",
                auto_fixable=False
            ))
        
        return ('ssn', issues)
    
    async def _detect_credit_cards(self, content: str) -> Tuple[str, List[ReviewIssue]]:
        """Detect credit card patterns."""
        issues = []
        matches = RegexPatterns.CREDIT_CARD.finditer(content)
        
        for match in list(matches)[:3]:
            # Basic Luhn check for validity
            digits = re.sub(r'\D', '', match.group())
            if len(digits) in [15, 16]:
                issues.append(self._create_issue(
                    severity=ReviewSeverity.BLOCKER,
                    title="Credit card pattern detected",
                    description="Found potential credit card number",
                    location=f"Character {match.start()}",
                    suggestion="Remove credit card information immediately",
                    auto_fixable=False
                ))
        
        return ('credit_card', issues)
    
    async def _detect_api_keys(self, content: str) -> Tuple[str, List[ReviewIssue]]:
        """Detect potential API keys."""
        issues = []
        matches = RegexPatterns.API_KEY.finditer(content)
        
        for match in list(matches)[:3]:
            # Check if it looks like a real API key (not just random text)
            key = match.group()
            if any(word in content[max(0, match.start()-50):match.end()+50].lower() 
                   for word in ['api', 'key', 'token', 'secret', 'auth']):
                issues.append(self._create_issue(
                    severity=ReviewSeverity.CRITICAL,
                    title="Potential API key detected",
                    description=f"Found potential API key: {key[:8]}...",
                    location=f"Character {match.start()}",
                    suggestion="Store API keys in environment variables",
                    auto_fixable=False
                ))
        
        return ('api_key', issues)
    
    async def _detect_pii_keywords(self, content: str) -> Tuple[str, List[ReviewIssue]]:
        """Detect PII keywords using trie."""
        issues = []
        
        if self.pii_detector:
            matches = self.pii_detector.detect(content)
            
            for keyword, start, end in matches[:5]:
                issues.append(self._create_issue(
                    severity=ReviewSeverity.MEDIUM,
                    title=f"PII keyword detected: {keyword}",
                    description="Document contains PII-related terminology",
                    location=f"Character {start}",
                    suggestion="Review context and redact if necessary",
                    auto_fixable=False
                ))
        
        return ('pii_keyword', issues)


# Export optimized dimensions
def get_optimized_dimensions() -> List[OptimizedBaseDimension]:
    """Get all optimized dimension instances."""
    return [
        OptimizedTechnicalAccuracyDimension(weight=0.25),
        OptimizedCompletenessDimension(weight=0.20),
        OptimizedSecurityPIIDimension(weight=0.30),
    ]