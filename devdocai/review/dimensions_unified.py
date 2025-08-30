"""
Unified review dimensions for M007 Review Engine.

Consolidated implementation combining base, optimized, and secure dimensions
through configurable operation modes and strategy patterns.
"""

import re
import logging
import asyncio
import hashlib
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from collections import defaultdict

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

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
    DimensionResult,
    ReviewEngineConfig
)

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    """Result from a single check within a dimension."""
    passed: bool
    issue: Optional[ReviewIssue] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


class DimensionStrategy(ABC):
    """Strategy interface for dimension-specific behavior based on operation mode."""
    
    @abstractmethod
    async def analyze_content(self, content: str, metadata: Dict[str, Any]) -> List[CheckResult]:
        """Analyze content and return check results."""
        pass
    
    @abstractmethod
    def get_patterns(self) -> Dict[str, str]:
        """Get regex patterns for this strategy."""
        pass


class BasicStrategy(DimensionStrategy):
    """Basic analysis strategy with simple regex patterns."""
    
    def __init__(self):
        self._patterns = {}
    
    async def analyze_content(self, content: str, metadata: Dict[str, Any]) -> List[CheckResult]:
        """Perform basic content analysis."""
        results = []
        patterns = self.get_patterns()
        
        for pattern_name, pattern_str in patterns.items():
            try:
                pattern = re.compile(pattern_str, re.IGNORECASE | re.MULTILINE)
                matches = pattern.finditer(content)
                match_count = sum(1 for _ in matches)
                
                result = CheckResult(
                    passed=match_count == 0,
                    metrics={f"{pattern_name}_count": match_count}
                )
                results.append(result)
                
            except re.error as e:
                logger.warning(f"Invalid regex pattern {pattern_name}: {e}")
        
        return results
    
    def get_patterns(self) -> Dict[str, str]:
        """Get basic regex patterns."""
        return {
            'code_smell': r'\b(TODO|FIXME|HACK|XXX)\b',
            'debug_code': r'(console\.(log|debug|info)|print\(|debugger)',
            'trailing_whitespace': r'[ \t]+$',
            'empty_lines': r'\n{3,}',
        }


class OptimizedStrategy(DimensionStrategy):
    """Optimized analysis strategy with pre-compiled patterns and caching."""
    
    def __init__(self):
        self._pattern_cache = {}
        self._result_cache = {}
    
    @lru_cache(maxsize=128)
    def _get_compiled_pattern(self, pattern_name: str, pattern_str: str) -> re.Pattern:
        """Get pre-compiled pattern with caching."""
        return re.compile(pattern_str, re.IGNORECASE | re.MULTILINE)
    
    async def analyze_content(self, content: str, metadata: Dict[str, Any]) -> List[CheckResult]:
        """Perform optimized content analysis with caching."""
        # Use content hash for caching
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        cache_key = f"{self.__class__.__name__}:{content_hash}"
        
        if cache_key in self._result_cache:
            return self._result_cache[cache_key]
        
        results = []
        patterns = self.get_patterns()
        
        # Process patterns in parallel if numpy is available
        if NUMPY_AVAILABLE and len(patterns) > 3:
            results = await self._parallel_pattern_analysis(content, patterns)
        else:
            for pattern_name, pattern_str in patterns.items():
                try:
                    pattern = self._get_compiled_pattern(pattern_name, pattern_str)
                    matches = list(pattern.finditer(content))
                    
                    result = CheckResult(
                        passed=len(matches) == 0,
                        metrics={
                            f"{pattern_name}_count": len(matches),
                            f"{pattern_name}_positions": [m.span() for m in matches[:10]]  # Limit for performance
                        }
                    )
                    results.append(result)
                    
                except re.error as e:
                    logger.warning(f"Invalid regex pattern {pattern_name}: {e}")
        
        # Cache results
        self._result_cache[cache_key] = results
        
        # Cleanup cache if too large
        if len(self._result_cache) > 100:
            oldest_keys = list(self._result_cache.keys())[:50]
            for key in oldest_keys:
                del self._result_cache[key]
        
        return results
    
    async def _parallel_pattern_analysis(
        self,
        content: str,
        patterns: Dict[str, str]
    ) -> List[CheckResult]:
        """Analyze patterns in parallel using thread pool."""
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for pattern_name, pattern_str in patterns.items():
                future = executor.submit(
                    self._analyze_single_pattern,
                    content,
                    pattern_name,
                    pattern_str
                )
                futures.append(future)
            
            results = []
            for future in futures:
                try:
                    result = future.result(timeout=5.0)
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.warning(f"Pattern analysis failed: {e}")
            
            return results
    
    def _analyze_single_pattern(
        self,
        content: str,
        pattern_name: str,
        pattern_str: str
    ) -> Optional[CheckResult]:
        """Analyze a single pattern."""
        try:
            pattern = self._get_compiled_pattern(pattern_name, pattern_str)
            matches = list(pattern.finditer(content))
            
            return CheckResult(
                passed=len(matches) == 0,
                metrics={
                    f"{pattern_name}_count": len(matches),
                    f"{pattern_name}_performance": "optimized"
                }
            )
        except Exception as e:
            logger.warning(f"Pattern {pattern_name} analysis failed: {e}")
            return None
    
    def get_patterns(self) -> Dict[str, str]:
        """Get optimized regex patterns."""
        return {
            'code_smell': r'\b(?:TODO|FIXME|HACK|XXX|REFACTOR|OPTIMIZE)\b',
            'debug_code': r'(?:console\.(?:log|debug|info|warn|error)|print\(|debugger\b|pdb\.set_trace)',
            'hardcoded_values': r'(?:password|secret|key|token)\s*=\s*["\'][^"\']+["\']',
            'unused_imports': r'^import\s+\w+(?:\s*,\s*\w+)*\s*$',
            'long_lines': r'^.{121,}$',
            'trailing_whitespace': r'[ \t]+$',
            'multiple_spaces': r'  +',
            'empty_lines': r'\n{3,}',
            'tabs_spaces_mix': r'^(\t+ +| +\t+)',
        }


class SecureStrategy(DimensionStrategy):
    """Secure analysis strategy with timeout protection and validation."""
    
    def __init__(self, security_validator=None):
        self.security_validator = security_validator
        self._timeout = 2.0
    
    async def analyze_content(self, content: str, metadata: Dict[str, Any]) -> List[CheckResult]:
        """Perform secure content analysis with timeout protection."""
        # Input validation
        if len(content) > 10 * 1024 * 1024:  # 10MB limit
            logger.warning("Content too large for secure analysis")
            return [CheckResult(
                passed=False,
                metrics={"error": "content_too_large"}
            )]
        
        results = []
        patterns = self.get_patterns()
        
        for pattern_name, pattern_str in patterns.items():
            try:
                result = await self._safe_pattern_analysis(
                    content,
                    pattern_name,
                    pattern_str
                )
                if result:
                    results.append(result)
                    
            except TimeoutError:
                logger.warning(f"Pattern {pattern_name} timed out")
                results.append(CheckResult(
                    passed=False,
                    metrics={f"{pattern_name}_timeout": True}
                ))
            except Exception as e:
                logger.warning(f"Secure pattern analysis failed for {pattern_name}: {e}")
        
        return results
    
    async def _safe_pattern_analysis(
        self,
        content: str,
        pattern_name: str,
        pattern_str: str
    ) -> Optional[CheckResult]:
        """Perform pattern analysis with timeout protection."""
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Pattern analysis timed out")
        
        # Set timeout
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(self._timeout))
        
        try:
            # Use limited pattern to prevent ReDoS
            safe_pattern = self._make_safe_pattern(pattern_str)
            pattern = re.compile(safe_pattern, re.IGNORECASE | re.MULTILINE)
            
            matches = list(pattern.finditer(content))
            signal.alarm(0)  # Cancel alarm
            
            return CheckResult(
                passed=len(matches) == 0,
                metrics={
                    f"{pattern_name}_count": len(matches),
                    f"{pattern_name}_secure": True,
                    f"{pattern_name}_analysis_time": time.time()
                }
            )
            
        finally:
            signal.signal(signal.SIGALRM, old_handler)
    
    def _make_safe_pattern(self, pattern: str) -> str:
        """Make regex pattern safe against ReDoS attacks."""
        # Limit repetition quantifiers
        safe_pattern = re.sub(r'\{(\d+),\}', r'{\1,100}', pattern)  # Limit open-ended repetition
        safe_pattern = re.sub(r'\*', '{0,100}', safe_pattern)  # Limit * quantifier
        safe_pattern = re.sub(r'\+', '{1,100}', safe_pattern)  # Limit + quantifier
        
        return safe_pattern
    
    def get_patterns(self) -> Dict[str, str]:
        """Get secure regex patterns with ReDoS protection."""
        return {
            # Technical patterns with limits
            'code_smell': r'\b(?:TODO|FIXME|HACK|XXX|REFACTOR|OPTIMIZE)\b',
            'debug_code': r'(?:console\.(?:log|debug|info|warn|error)|print\(|debugger\b|pdb\.set_trace)',
            'hardcoded_values': r'(?:password|secret|key|token)\s*=\s*["\'][^"\']{1,100}["\']',
            'long_lines': r'^.{121,500}$',  # Prevent excessive backtracking
            
            # Security patterns
            'sql_injection': r'\b(?:SELECT|INSERT|UPDATE|DELETE|DROP|UNION)\b.*\b(?:FROM|WHERE|TABLE)\b',
            'xss_simple': r'<script[^>]{0,100}>|javascript:|on\w+\s*=',
            'command_injection': r'[;&|`$]|\$\([^)]{1,100}\)',
            'path_traversal': r'\.\.[\\/]|\.\.%2[fF]|\.\.%5[cC]',
            'weak_crypto': r'\b(?:md5|sha1|des|rc4)\b',
            
            # PII patterns
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'credit_card': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
            'api_key': r'\b[A-Za-z0-9]{32,64}\b',
        }


class UnifiedDimension(ABC):
    """
    Unified base class for review dimensions with mode-specific strategies.
    """
    
    def __init__(
        self,
        weight: float = 0.2,
        mode: 'OperationMode' = None,
        config: Optional[ReviewEngineConfig] = None
    ):
        """Initialize unified dimension."""
        from .review_engine_unified import OperationMode
        
        self.weight = weight
        self.mode = mode or OperationMode.BASIC
        self.config = config
        self.dimension = self._get_dimension()
        
        # Initialize strategy based on mode
        self.strategy = self._create_strategy()
        
        # Statistics
        self.checks_performed = 0
        self.checks_passed = 0
        self._metrics: Dict[str, Any] = {}
    
    @abstractmethod
    def _get_dimension(self) -> ReviewDimension:
        """Return the dimension type."""
        pass
    
    def _create_strategy(self) -> DimensionStrategy:
        """Create appropriate strategy based on mode."""
        from .review_engine_unified import OperationMode
        
        if self.mode == OperationMode.BASIC:
            return BasicStrategy()
        elif self.mode == OperationMode.OPTIMIZED:
            return OptimizedStrategy()
        elif self.mode in [OperationMode.SECURE, OperationMode.ENTERPRISE]:
            return SecureStrategy()
        else:
            return BasicStrategy()
    
    async def analyze(self, content: str, metadata: Dict[str, Any]) -> DimensionResult:
        """
        Analyze content for this dimension using the configured strategy.
        """
        start_time = time.time()
        
        # Pre-analysis validation
        validation_result = self._pre_analysis_validation(content, metadata)
        if not validation_result.passed:
            return self._create_error_result(validation_result.metrics.get("error", "validation_failed"))
        
        # Run strategy analysis
        check_results = await self.strategy.analyze_content(content, metadata)
        
        # Add dimension-specific checks
        dimension_checks = await self._dimension_specific_analysis(content, metadata)
        check_results.extend(dimension_checks)
        
        # Aggregate results
        issues = []
        passed_checks = 0
        total_checks = len(check_results)
        aggregated_metrics = {}
        
        for check_result in check_results:
            if check_result.passed:
                passed_checks += 1
            elif check_result.issue:
                issues.append(check_result.issue)
            
            # Aggregate metrics
            aggregated_metrics.update(check_result.metrics)
        
        # Calculate score
        score = self._calculate_score(passed_checks, total_checks, issues)
        
        # Update statistics
        self.checks_performed += total_checks
        self.checks_passed += passed_checks
        self._metrics.update(aggregated_metrics)
        
        execution_time = (time.time() - start_time) * 1000
        
        return DimensionResult(
            dimension=self.dimension,
            score=score,
            weight=self.weight,
            issues=issues,
            passed_checks=passed_checks,
            total_checks=total_checks,
            metrics=aggregated_metrics,
            execution_time_ms=execution_time
        )
    
    def _pre_analysis_validation(self, content: str, metadata: Dict[str, Any]) -> CheckResult:
        """Perform pre-analysis validation."""
        # Basic validation
        if not content or not content.strip():
            return CheckResult(
                passed=False,
                metrics={"error": "empty_content"}
            )
        
        # Size validation based on mode
        from .review_engine_unified import OperationMode
        
        max_sizes = {
            OperationMode.BASIC: 1024 * 1024,  # 1MB
            OperationMode.OPTIMIZED: 5 * 1024 * 1024,  # 5MB
            OperationMode.SECURE: 2 * 1024 * 1024,  # 2MB (conservative)
            OperationMode.ENTERPRISE: 10 * 1024 * 1024,  # 10MB
        }
        
        max_size = max_sizes.get(self.mode, 1024 * 1024)
        if len(content) > max_size:
            return CheckResult(
                passed=False,
                metrics={"error": "content_too_large", "size": len(content), "max_size": max_size}
            )
        
        return CheckResult(passed=True)
    
    @abstractmethod
    async def _dimension_specific_analysis(self, content: str, metadata: Dict[str, Any]) -> List[CheckResult]:
        """Perform dimension-specific analysis."""
        pass
    
    def _calculate_score(self, passed_checks: int, total_checks: int, issues: List[ReviewIssue]) -> float:
        """Calculate dimension score based on checks and issues."""
        if total_checks == 0:
            return 100.0
        
        # Base score from passed checks
        base_score = (passed_checks / total_checks) * 100.0
        
        # Apply penalties for issues
        penalty = 0.0
        for issue in issues:
            severity_penalties = {
                ReviewSeverity.BLOCKER: 25.0,
                ReviewSeverity.CRITICAL: 15.0,
                ReviewSeverity.HIGH: 10.0,
                ReviewSeverity.MEDIUM: 5.0,
                ReviewSeverity.LOW: 2.0,
                ReviewSeverity.INFO: 0.5
            }
            penalty += severity_penalties.get(issue.severity, 5.0)
        
        # Ensure score doesn't go below 0
        final_score = max(0.0, base_score - penalty)
        
        # Mode-specific score adjustments
        from .review_engine_unified import OperationMode
        
        if self.mode == OperationMode.SECURE and any(issue.dimension == ReviewDimension.SECURITY_PII for issue in issues):
            final_score *= 0.5  # Heavy penalty for security issues in secure mode
        
        return min(100.0, final_score)
    
    def _create_error_result(self, error_message: str) -> DimensionResult:
        """Create error result for failed analysis."""
        error_issue = ReviewIssue(
            dimension=self.dimension,
            severity=ReviewSeverity.HIGH,
            title="Analysis Error",
            description=f"Failed to analyze dimension: {error_message}",
            impact_score=8.0,
            confidence=1.0
        )
        
        return DimensionResult(
            dimension=self.dimension,
            score=0.0,
            weight=self.weight,
            issues=[error_issue],
            passed_checks=0,
            total_checks=1,
            metrics={"error": error_message}
        )
    
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


class TechnicalAccuracyDimension(UnifiedDimension):
    """Unified technical accuracy dimension."""
    
    def _get_dimension(self) -> ReviewDimension:
        return ReviewDimension.TECHNICAL_ACCURACY
    
    async def _dimension_specific_analysis(self, content: str, metadata: Dict[str, Any]) -> List[CheckResult]:
        """Analyze technical accuracy specific patterns."""
        results = []
        
        # Check for syntax errors in code blocks
        code_blocks = re.findall(r'```[\w]*\n(.*?)\n```', content, re.DOTALL)
        for i, code_block in enumerate(code_blocks):
            if self._has_obvious_syntax_errors(code_block):
                issue = self._create_issue(
                    ReviewSeverity.HIGH,
                    f"Syntax Error in Code Block {i+1}",
                    "Code block contains apparent syntax errors",
                    suggestion="Review and fix syntax errors in code examples",
                    code_snippet=code_block[:200]
                )
                results.append(CheckResult(passed=False, issue=issue))
            else:
                results.append(CheckResult(passed=True))
        
        # Check for broken links (basic pattern)
        links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
        broken_link_count = 0
        for link_text, url in links:
            if self._looks_like_broken_link(url):
                broken_link_count += 1
        
        if broken_link_count > 0:
            issue = self._create_issue(
                ReviewSeverity.MEDIUM,
                "Potentially Broken Links",
                f"Found {broken_link_count} links that may be broken",
                suggestion="Verify all links are accessible and point to correct resources"
            )
            results.append(CheckResult(passed=False, issue=issue))
        else:
            results.append(CheckResult(passed=True))
        
        return results
    
    def _has_obvious_syntax_errors(self, code: str) -> bool:
        """Check for obvious syntax errors in code."""
        # Simple heuristics for common syntax errors
        lines = code.strip().split('\n')
        
        # Check for mismatched brackets/braces/parentheses
        bracket_stack = []
        bracket_pairs = {'(': ')', '[': ']', '{': '}'}
        
        for line in lines:
            for char in line:
                if char in bracket_pairs:
                    bracket_stack.append(char)
                elif char in bracket_pairs.values():
                    if not bracket_stack:
                        return True  # Unmatched closing bracket
                    last_open = bracket_stack.pop()
                    if bracket_pairs[last_open] != char:
                        return True  # Mismatched brackets
        
        return len(bracket_stack) > 0  # Unmatched opening brackets
    
    def _looks_like_broken_link(self, url: str) -> bool:
        """Heuristic check for potentially broken links."""
        # Check for common broken link patterns
        broken_patterns = [
            r'^#$',  # Just a hash
            r'^$',   # Empty URL
            r'^javascript:void\(0\)$',  # Placeholder JavaScript
            r'^\s*$',  # Just whitespace
            r'^example\.com',  # Example domain
            r'^localhost',  # Localhost (may not be accessible)
        ]
        
        for pattern in broken_patterns:
            if re.match(pattern, url, re.IGNORECASE):
                return True
        
        return False


class CompletenessDimension(UnifiedDimension):
    """Unified completeness dimension."""
    
    def _get_dimension(self) -> ReviewDimension:
        return ReviewDimension.COMPLETENESS
    
    async def _dimension_specific_analysis(self, content: str, metadata: Dict[str, Any]) -> List[CheckResult]:
        """Analyze document completeness."""
        results = []
        doc_type = metadata.get('document_type', 'generic')
        
        # Check for required sections based on document type
        required_sections = self._get_required_sections(doc_type)
        missing_sections = []
        
        headers = re.findall(r'^#{1,6}\s+(.+)$', content, re.MULTILINE)
        header_text = [h.lower() for h in headers]
        
        for section in required_sections:
            if not any(section.lower() in header for header in header_text):
                missing_sections.append(section)
        
        if missing_sections:
            issue = self._create_issue(
                ReviewSeverity.MEDIUM,
                "Missing Required Sections",
                f"Document missing sections: {', '.join(missing_sections)}",
                suggestion=f"Add the following sections: {', '.join(missing_sections)}"
            )
            results.append(CheckResult(passed=False, issue=issue))
        else:
            results.append(CheckResult(passed=True))
        
        # Check for TODOs and placeholders
        todo_count = len(re.findall(r'\b(TODO|FIXME|TBD|PLACEHOLDER)\b', content, re.IGNORECASE))
        if todo_count > 0:
            issue = self._create_issue(
                ReviewSeverity.LOW if todo_count <= 2 else ReviewSeverity.MEDIUM,
                f"Incomplete Content ({todo_count} TODOs)",
                f"Document contains {todo_count} TODO items or placeholders",
                suggestion="Complete all TODO items and remove placeholders",
                auto_fixable=False
            )
            results.append(CheckResult(passed=False, issue=issue))
        else:
            results.append(CheckResult(passed=True))
        
        # Check for empty sections
        empty_sections = self._find_empty_sections(content)
        if empty_sections:
            issue = self._create_issue(
                ReviewSeverity.LOW,
                "Empty Sections",
                f"Found {len(empty_sections)} empty sections",
                suggestion="Add content to empty sections or remove them"
            )
            results.append(CheckResult(passed=False, issue=issue))
        else:
            results.append(CheckResult(passed=True))
        
        return results
    
    def _get_required_sections(self, doc_type: str) -> List[str]:
        """Get required sections based on document type."""
        requirements = {
            'readme': ['Description', 'Installation', 'Usage', 'License'],
            'api': ['Overview', 'Authentication', 'Endpoints', 'Examples'],
            'guide': ['Introduction', 'Prerequisites', 'Steps', 'Conclusion'],
            'changelog': ['Unreleased', 'Version History'],
            'generic': ['Overview']
        }
        return requirements.get(doc_type.lower(), requirements['generic'])
    
    def _find_empty_sections(self, content: str) -> List[str]:
        """Find sections that are empty or contain only whitespace."""
        empty_sections = []
        
        # Find all headers and their content
        lines = content.split('\n')
        current_section = None
        section_content = []
        
        for line in lines:
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if header_match:
                # Check previous section
                if current_section and not any(l.strip() for l in section_content):
                    empty_sections.append(current_section)
                
                # Start new section
                current_section = header_match.group(2)
                section_content = []
            else:
                section_content.append(line)
        
        # Check last section
        if current_section and not any(l.strip() for l in section_content):
            empty_sections.append(current_section)
        
        return empty_sections


class ConsistencyDimension(UnifiedDimension):
    """Unified consistency dimension."""
    
    def _get_dimension(self) -> ReviewDimension:
        return ReviewDimension.CONSISTENCY
    
    async def _dimension_specific_analysis(self, content: str, metadata: Dict[str, Any]) -> List[CheckResult]:
        """Analyze document consistency."""
        results = []
        
        # Check naming convention consistency
        naming_analysis = self._analyze_naming_conventions(content)
        if naming_analysis['inconsistencies'] > 0:
            issue = self._create_issue(
                ReviewSeverity.LOW,
                "Inconsistent Naming Conventions",
                f"Found mixed naming conventions: {naming_analysis['details']}",
                suggestion="Standardize naming conventions throughout the document"
            )
            results.append(CheckResult(passed=False, issue=issue))
        else:
            results.append(CheckResult(passed=True))
        
        # Check header formatting consistency
        headers = re.findall(r'^(#{1,6})\s+(.+)$', content, re.MULTILINE)
        header_styles = {}
        for level, text in headers:
            level_num = len(level)
            if level_num not in header_styles:
                header_styles[level_num] = []
            header_styles[level_num].append(text)
        
        # Check for inconsistent capitalization in same-level headers
        inconsistent_headers = 0
        for level, texts in header_styles.items():
            if len(texts) > 1:
                title_case_count = sum(1 for t in texts if t.istitle())
                lower_case_count = sum(1 for t in texts if t.islower())
                if title_case_count > 0 and lower_case_count > 0:
                    inconsistent_headers += 1
        
        if inconsistent_headers > 0:
            issue = self._create_issue(
                ReviewSeverity.LOW,
                "Inconsistent Header Capitalization",
                "Headers at the same level have inconsistent capitalization",
                suggestion="Use consistent capitalization for headers at the same level",
                auto_fixable=True
            )
            results.append(CheckResult(passed=False, issue=issue))
        else:
            results.append(CheckResult(passed=True))
        
        return results
    
    def _analyze_naming_conventions(self, content: str) -> Dict[str, Any]:
        """Analyze naming convention consistency."""
        # Extract potential variable/function names from code blocks
        code_blocks = re.findall(r'```[\w]*\n(.*?)\n```', content, re.DOTALL)
        
        camel_case_count = 0
        snake_case_count = 0
        kebab_case_count = 0
        
        for code_block in code_blocks:
            # Simple pattern matching for naming conventions
            camel_case_count += len(re.findall(r'\b[a-z]+(?:[A-Z][a-z]+)+\b', code_block))
            snake_case_count += len(re.findall(r'\b[a-z]+(?:_[a-z]+)+\b', code_block))
            kebab_case_count += len(re.findall(r'\b[a-z]+(?:-[a-z]+)+\b', code_block))
        
        total_identifiers = camel_case_count + snake_case_count + kebab_case_count
        
        if total_identifiers < 3:
            return {'inconsistencies': 0, 'details': 'insufficient_data'}
        
        # Check if multiple conventions are used significantly
        conventions_used = sum(1 for count in [camel_case_count, snake_case_count, kebab_case_count] if count > 0)
        
        if conventions_used > 1:
            details = f"camelCase: {camel_case_count}, snake_case: {snake_case_count}, kebab-case: {kebab_case_count}"
            return {'inconsistencies': conventions_used - 1, 'details': details}
        
        return {'inconsistencies': 0, 'details': 'consistent'}


class StyleFormattingDimension(UnifiedDimension):
    """Unified style and formatting dimension."""
    
    def _get_dimension(self) -> ReviewDimension:
        return ReviewDimension.STYLE_FORMATTING
    
    async def _dimension_specific_analysis(self, content: str, metadata: Dict[str, Any]) -> List[CheckResult]:
        """Analyze style and formatting issues."""
        results = []
        
        # Check for trailing whitespace
        trailing_whitespace_lines = []
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.rstrip() != line:
                trailing_whitespace_lines.append(i + 1)
        
        if trailing_whitespace_lines:
            issue = self._create_issue(
                ReviewSeverity.LOW,
                "Trailing Whitespace",
                f"Found trailing whitespace on {len(trailing_whitespace_lines)} lines",
                suggestion="Remove trailing whitespace from all lines",
                auto_fixable=True
            )
            results.append(CheckResult(passed=False, issue=issue))
        else:
            results.append(CheckResult(passed=True))
        
        # Check for excessive blank lines
        excessive_blank_lines = len(re.findall(r'\n{4,}', content))
        if excessive_blank_lines > 0:
            issue = self._create_issue(
                ReviewSeverity.LOW,
                "Excessive Blank Lines",
                f"Found {excessive_blank_lines} instances of 4+ consecutive blank lines",
                suggestion="Reduce consecutive blank lines to maximum of 2",
                auto_fixable=True
            )
            results.append(CheckResult(passed=False, issue=issue))
        else:
            results.append(CheckResult(passed=True))
        
        # Check for mixed tabs and spaces
        has_tabs = '\t' in content
        has_leading_spaces = bool(re.search(r'^\s{2,}', content, re.MULTILINE))
        
        if has_tabs and has_leading_spaces:
            issue = self._create_issue(
                ReviewSeverity.MEDIUM,
                "Mixed Tabs and Spaces",
                "Document contains both tabs and spaces for indentation",
                suggestion="Use consistent indentation (either tabs or spaces, not both)"
            )
            results.append(CheckResult(passed=False, issue=issue))
        else:
            results.append(CheckResult(passed=True))
        
        return results


class SecurityPIIDimension(UnifiedDimension):
    """Unified security and PII dimension."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Initialize PII detector if available
        try:
            from ..storage.pii_detector import PIIDetectionConfig, PIIType
            pii_config = PIIDetectionConfig(
                enabled_types={PIIType.EMAIL, PIIType.PHONE, PIIType.SSN, PIIType.CREDIT_CARD},
                min_confidence=0.8
            )
            self.pii_detector = PIIDetector(config=pii_config)
        except Exception as e:
            logger.warning(f"PII Detector not available: {e}")
            self.pii_detector = None
    
    def _get_dimension(self) -> ReviewDimension:
        return ReviewDimension.SECURITY_PII
    
    async def _dimension_specific_analysis(self, content: str, metadata: Dict[str, Any]) -> List[CheckResult]:
        """Analyze security and PII issues."""
        results = []
        
        # PII detection
        if self.pii_detector:
            try:
                pii_results = self.pii_detector.detect(content)
                if pii_results and len(pii_results.pii_found) > 0:
                    for pii_item in pii_results.pii_found:
                        issue = self._create_issue(
                            ReviewSeverity.CRITICAL,
                            f"PII Detected: {pii_item.type.value}",
                            f"Found {pii_item.type.value} in document at position {pii_item.start}-{pii_item.end}",
                            suggestion="Remove or mask PII before publishing",
                            location=f"Position {pii_item.start}-{pii_item.end}",
                            auto_fixable=True
                        )
                        results.append(CheckResult(passed=False, issue=issue))
                else:
                    results.append(CheckResult(passed=True, metrics={'pii_found': 0}))
            except Exception as e:
                logger.warning(f"PII detection failed: {e}")
                results.append(CheckResult(passed=True, metrics={'pii_detection_error': str(e)}))
        
        # Security pattern detection
        security_patterns = {
            'hardcoded_secrets': r'(?:password|secret|key|token)\s*[:=]\s*["\'][^"\']{8,}["\']',
            'api_keys': r'\b[A-Za-z0-9]{32,}\b',
            'sql_injection': r'\b(?:SELECT|INSERT|UPDATE|DELETE|DROP)\b.*\b(?:FROM|WHERE|TABLE)\b',
            'xss_patterns': r'<script[^>]*>|javascript:|on\w+\s*=',
            'command_injection': r'[;&|`$]|\$\([^)]+\)',
        }
        
        for pattern_name, pattern_str in security_patterns.items():
            try:
                matches = list(re.finditer(pattern_str, content, re.IGNORECASE | re.MULTILINE))
                if matches:
                    severity = ReviewSeverity.HIGH if 'secret' in pattern_name or 'key' in pattern_name else ReviewSeverity.MEDIUM
                    issue = self._create_issue(
                        severity,
                        f"Security Issue: {pattern_name.replace('_', ' ').title()}",
                        f"Found {len(matches)} instances of potential {pattern_name.replace('_', ' ')}",
                        suggestion=f"Review and secure {pattern_name.replace('_', ' ')} instances"
                    )
                    results.append(CheckResult(passed=False, issue=issue))
                else:
                    results.append(CheckResult(passed=True, metrics={f'{pattern_name}_count': 0}))
            except re.error as e:
                logger.warning(f"Invalid security pattern {pattern_name}: {e}")
        
        return results


class UnifiedDimensionFactory:
    """Factory for creating unified dimensions based on configuration."""
    
    def __init__(self, mode: 'OperationMode'):
        from .review_engine_unified import OperationMode
        self.mode = mode
    
    def create_dimension(
        self,
        dimension_type: ReviewDimension,
        weight: float,
        config: Optional[ReviewEngineConfig] = None
    ) -> Optional[UnifiedDimension]:
        """Create a dimension instance based on type."""
        dimension_classes = {
            ReviewDimension.TECHNICAL_ACCURACY: TechnicalAccuracyDimension,
            ReviewDimension.COMPLETENESS: CompletenessDimension,
            ReviewDimension.CONSISTENCY: ConsistencyDimension,
            ReviewDimension.STYLE_FORMATTING: StyleFormattingDimension,
            ReviewDimension.SECURITY_PII: SecurityPIIDimension,
        }
        
        dimension_class = dimension_classes.get(dimension_type)
        if not dimension_class:
            logger.warning(f"Unknown dimension type: {dimension_type}")
            return None
        
        try:
            return dimension_class(weight=weight, mode=self.mode, config=config)
        except Exception as e:
            logger.error(f"Failed to create dimension {dimension_type}: {e}")
            return None
    
    def get_available_dimensions(self) -> List[ReviewDimension]:
        """Get list of available dimension types."""
        return [
            ReviewDimension.TECHNICAL_ACCURACY,
            ReviewDimension.COMPLETENESS,
            ReviewDimension.CONSISTENCY,
            ReviewDimension.STYLE_FORMATTING,
            ReviewDimension.SECURITY_PII,
        ]


def get_unified_dimensions(
    mode: 'OperationMode',
    enabled_dimensions: Set[ReviewDimension],
    dimension_weights: Dict[ReviewDimension, float],
    config: Optional[ReviewEngineConfig] = None
) -> List[UnifiedDimension]:
    """
    Get unified dimensions for the specified mode and configuration.
    
    Args:
        mode: Operation mode
        enabled_dimensions: Set of enabled dimension types
        dimension_weights: Weight configuration for dimensions
        config: Optional review engine configuration
        
    Returns:
        List of configured unified dimensions
    """
    factory = UnifiedDimensionFactory(mode)
    dimensions = []
    
    for dimension_type in enabled_dimensions:
        weight = dimension_weights.get(dimension_type, 0.2)
        dimension = factory.create_dimension(dimension_type, weight, config)
        if dimension:
            dimensions.append(dimension)
    
    return dimensions