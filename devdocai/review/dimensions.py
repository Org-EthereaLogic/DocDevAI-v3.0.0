"""
Review dimensions for M007 Review Engine.

Implements multi-dimensional review criteria including technical accuracy,
completeness, consistency, style/formatting, and security/PII detection.
"""

import re
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ..storage.pii_detector import PIIDetector, PIIDetectionConfig, PIIType
from .models import (
    ReviewDimension,
    ReviewSeverity,
    ReviewIssue,
    DimensionResult
)

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    """Result from a single check within a dimension."""
    passed: bool
    issue: Optional[ReviewIssue] = None
    metrics: Dict[str, Any] = None


class BaseDimension(ABC):
    """
    Abstract base class for review dimensions.
    
    Each dimension analyzes a specific aspect of document quality
    and generates issues and scores based on its criteria.
    """
    
    def __init__(self, weight: float = 0.2):
        """Initialize dimension with weight."""
        self.weight = weight
        self.dimension = self._get_dimension()
        self.checks_performed = 0
        self.checks_passed = 0
        self._metrics: Dict[str, Any] = {}
    
    @abstractmethod
    def _get_dimension(self) -> ReviewDimension:
        """Return the dimension type."""
        pass
    
    @abstractmethod
    async def analyze(self, content: str, metadata: Dict[str, Any]) -> DimensionResult:
        """
        Analyze content for this dimension.
        
        Args:
            content: Document content to analyze
            metadata: Additional metadata about the document
            
        Returns:
            DimensionResult with score, issues, and metrics
        """
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
            # Default impact scores by severity
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
    
    def _calculate_score(self, issues: List[ReviewIssue], base_score: float = 100.0) -> float:
        """
        Calculate dimension score based on issues found.
        
        Args:
            issues: List of issues found
            base_score: Starting score
            
        Returns:
            Final score between 0 and 100
        """
        score = base_score
        
        for issue in issues:
            # Deduct points based on severity and impact
            deduction = issue.impact_score * issue.confidence
            
            # Apply severity multiplier
            severity_multipliers = {
                ReviewSeverity.BLOCKER: 3.0,
                ReviewSeverity.CRITICAL: 2.0,
                ReviewSeverity.HIGH: 1.5,
                ReviewSeverity.MEDIUM: 1.0,
                ReviewSeverity.LOW: 0.5,
                ReviewSeverity.INFO: 0.1
            }
            
            multiplier = severity_multipliers.get(issue.severity, 1.0)
            score -= deduction * multiplier
        
        # Ensure score stays within bounds
        return max(0.0, min(100.0, score))


class TechnicalAccuracyDimension(BaseDimension):
    """
    Analyzes technical accuracy of documentation.
    
    Checks for:
    - Code correctness and syntax
    - API accuracy
    - Technical terminology usage
    - Version compatibility
    - Command/configuration validity
    """
    
    def _get_dimension(self) -> ReviewDimension:
        return ReviewDimension.TECHNICAL_ACCURACY
    
    async def analyze(self, content: str, metadata: Dict[str, Any]) -> DimensionResult:
        """Analyze technical accuracy of the document."""
        issues = []
        checks = []
        
        # Check for code blocks
        code_check = self._check_code_blocks(content, metadata)
        checks.append(code_check)
        if code_check.issue:
            issues.append(code_check.issue)
        
        # Check API references
        api_check = self._check_api_references(content, metadata)
        checks.append(api_check)
        if api_check.issue:
            issues.append(api_check.issue)
        
        # Check technical terminology
        term_check = self._check_technical_terms(content, metadata)
        checks.append(term_check)
        if term_check.issue:
            issues.append(term_check.issue)
        
        # Check version references
        version_check = self._check_version_compatibility(content, metadata)
        checks.append(version_check)
        if version_check.issue:
            issues.append(version_check.issue)
        
        # Check commands and configurations
        command_check = self._check_commands(content, metadata)
        checks.append(command_check)
        if command_check.issue:
            issues.append(command_check.issue)
        
        # Calculate metrics
        self.checks_performed = len(checks)
        self.checks_passed = sum(1 for check in checks if check.passed)
        
        # Calculate score
        score = self._calculate_score(issues)
        
        # Compile metrics
        metrics = {
            'code_blocks_found': self._metrics.get('code_blocks', 0),
            'api_references': self._metrics.get('api_refs', 0),
            'version_mentions': self._metrics.get('versions', 0),
            'commands_found': self._metrics.get('commands', 0),
            'syntax_errors': sum(1 for issue in issues if 'syntax' in issue.title.lower())
        }
        
        return DimensionResult(
            dimension=self.dimension,
            score=score,
            weight=self.weight,
            issues=issues,
            passed_checks=self.checks_passed,
            total_checks=self.checks_performed,
            metrics=metrics
        )
    
    def _check_code_blocks(self, content: str, metadata: Dict[str, Any]) -> CheckResult:
        """Check code blocks for syntax and correctness."""
        # Find code blocks (markdown style)
        code_pattern = r'```(\w+)?\n(.*?)\n```'
        code_blocks = re.findall(code_pattern, content, re.DOTALL)
        
        self._metrics['code_blocks'] = len(code_blocks)
        
        if not code_blocks:
            return CheckResult(passed=True)
        
        # Check for common syntax issues
        issues_found = []
        for lang, code in code_blocks:
            if lang in ['python', 'py']:
                # Check for basic Python syntax issues
                if 'import' in code and 'from' in code:
                    lines = code.split('\n')
                    for i, line in enumerate(lines):
                        if line.strip().startswith('from') and ' import ' in line:
                            if not re.match(r'^from\s+[\w.]+\s+import\s+[\w,\s*()]+$', line.strip()):
                                issues_found.append(f"Line {i+1}: Malformed import statement")
            
            elif lang in ['javascript', 'js', 'typescript', 'ts']:
                # Check for basic JS/TS syntax issues
                if 'function' in code or '=>' in code:
                    # Check for missing semicolons in key places
                    if 'const ' in code or 'let ' in code or 'var ' in code:
                        lines = code.split('\n')
                        for i, line in enumerate(lines):
                            if re.match(r'^\s*(const|let|var)\s+\w+\s*=.*[^;{]\s*$', line):
                                if not line.strip().endswith((';', '{', ',')):
                                    issues_found.append(f"Line {i+1}: Missing semicolon")
        
        if issues_found:
            return CheckResult(
                passed=False,
                issue=self._create_issue(
                    severity=ReviewSeverity.MEDIUM,
                    title="Code syntax issues detected",
                    description=f"Found {len(issues_found)} potential syntax issues in code blocks",
                    suggestion="Review and fix the syntax errors in code examples",
                    code_snippet='\n'.join(issues_found[:3]),  # Show first 3 issues
                    auto_fixable=True
                )
            )
        
        return CheckResult(passed=True)
    
    def _check_api_references(self, content: str, metadata: Dict[str, Any]) -> CheckResult:
        """Check API references for accuracy."""
        # Look for API-like patterns
        api_patterns = [
            r'`[\w.]+\(\)`',  # Function calls
            r'`[\w.]+\[[\w\s,]*\]`',  # Array/dict access
            r'class\s+(\w+)',  # Class definitions
            r'def\s+(\w+)',  # Function definitions
            r'interface\s+(\w+)',  # Interface definitions
        ]
        
        api_refs = 0
        for pattern in api_patterns:
            matches = re.findall(pattern, content)
            api_refs += len(matches)
        
        self._metrics['api_refs'] = api_refs
        
        # Check for deprecated patterns (example)
        deprecated_patterns = {
            r'\.success\(\)': "Use .then() instead of .success()",
            r'\.error\(\)': "Use .catch() instead of .error()",
            r'React\.PropTypes': "PropTypes has been moved to a separate package",
        }
        
        deprecation_issues = []
        for pattern, message in deprecated_patterns.items():
            if re.search(pattern, content):
                deprecation_issues.append(message)
        
        if deprecation_issues:
            return CheckResult(
                passed=False,
                issue=self._create_issue(
                    severity=ReviewSeverity.HIGH,
                    title="Deprecated API usage detected",
                    description=f"Found {len(deprecation_issues)} deprecated API patterns",
                    suggestion='\n'.join(deprecation_issues),
                    auto_fixable=True
                )
            )
        
        return CheckResult(passed=True)
    
    def _check_technical_terms(self, content: str, metadata: Dict[str, Any]) -> CheckResult:
        """Check technical terminology usage."""
        # Common technical term misspellings/misuses
        term_issues = {
            r'\bjavascript\b': "JavaScript (capital 'S')",
            r'\bpython\s+2\b': "Python 2 is deprecated, consider Python 3",
            r'\bmongodb\b': "MongoDB (capital 'DB')",
            r'\bpostgresql\b': "PostgreSQL (capital 'SQL')",
            r'\bgithub\b': "GitHub (capital 'H')",
        }
        
        found_issues = []
        for pattern, correction in term_issues.items():
            if re.search(pattern, content, re.IGNORECASE):
                # Check if it's not already correctly capitalized
                correct_pattern = correction.split('(')[0].strip()
                if not re.search(r'\b' + re.escape(correct_pattern) + r'\b', content):
                    found_issues.append(correction)
        
        if found_issues:
            return CheckResult(
                passed=False,
                issue=self._create_issue(
                    severity=ReviewSeverity.LOW,
                    title="Technical terminology issues",
                    description=f"Found {len(found_issues)} terminology issues",
                    suggestion="Correct terminology: " + ', '.join(found_issues),
                    auto_fixable=True,
                    confidence=0.8
                )
            )
        
        return CheckResult(passed=True)
    
    def _check_version_compatibility(self, content: str, metadata: Dict[str, Any]) -> CheckResult:
        """Check version references for compatibility."""
        # Find version patterns
        version_pattern = r'(?:version|v)?\s*(\d+\.\d+(?:\.\d+)?)'
        versions = re.findall(version_pattern, content, re.IGNORECASE)
        
        self._metrics['versions'] = len(versions)
        
        # Check for outdated versions (example thresholds)
        outdated = {
            'python': (3, 8),  # Minimum Python 3.8
            'node': (14, 0),   # Minimum Node 14
            'react': (16, 8),  # Minimum React 16.8
        }
        
        issues = []
        for tech, min_version in outdated.items():
            tech_pattern = rf'{tech}.*?(\d+)\.(\d+)'
            matches = re.findall(tech_pattern, content, re.IGNORECASE)
            for major, minor in matches:
                if int(major) < min_version[0] or (int(major) == min_version[0] and int(minor) < min_version[1]):
                    issues.append(f"{tech} {major}.{minor} is outdated (minimum: {min_version[0]}.{min_version[1]})")
        
        if issues:
            return CheckResult(
                passed=False,
                issue=self._create_issue(
                    severity=ReviewSeverity.MEDIUM,
                    title="Outdated version references",
                    description=f"Found {len(issues)} outdated version references",
                    suggestion="Update to supported versions: " + '; '.join(issues[:3]),
                    auto_fixable=False
                )
            )
        
        return CheckResult(passed=True)
    
    def _check_commands(self, content: str, metadata: Dict[str, Any]) -> CheckResult:
        """Check commands and configurations for validity."""
        # Find command patterns
        command_patterns = [
            r'`([a-z]+(?:\s+[a-z\-]+)*)`',  # Inline commands
            r'^\$\s+(.+)$',  # Shell commands
            r'^>\s+(.+)$',  # Command prompts
        ]
        
        commands = []
        for pattern in command_patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            commands.extend(matches)
        
        self._metrics['commands'] = len(commands)
        
        # Check for dangerous commands
        dangerous_commands = [
            (r'rm\s+-rf\s+/', "Dangerous recursive deletion of root"),
            (r'chmod\s+777', "Overly permissive file permissions"),
            (r'sudo\s+rm', "Dangerous sudo deletion"),
            (r'>\s*/dev/sd[a-z]', "Direct write to disk device"),
        ]
        
        security_issues = []
        for pattern, description in dangerous_commands:
            for cmd in commands:
                if re.search(pattern, cmd):
                    security_issues.append(f"{description}: {cmd}")
        
        if security_issues:
            return CheckResult(
                passed=False,
                issue=self._create_issue(
                    severity=ReviewSeverity.CRITICAL,
                    title="Dangerous commands detected",
                    description=f"Found {len(security_issues)} potentially dangerous commands",
                    suggestion="Review and modify dangerous commands",
                    code_snippet='\n'.join(security_issues[:3]),
                    auto_fixable=False
                )
            )
        
        return CheckResult(passed=True)


class CompletenessDimension(BaseDimension):
    """
    Analyzes document completeness.
    
    Checks for:
    - Required sections presence
    - Section depth and detail
    - Missing information
    - TODOs and placeholders
    - Examples and use cases
    """
    
    def _get_dimension(self) -> ReviewDimension:
        return ReviewDimension.COMPLETENESS
    
    async def analyze(self, content: str, metadata: Dict[str, Any]) -> DimensionResult:
        """Analyze document completeness."""
        issues = []
        checks = []
        
        # Check required sections
        section_check = self._check_required_sections(content, metadata)
        checks.append(section_check)
        if section_check.issue:
            issues.append(section_check.issue)
        
        # Check for TODOs and placeholders
        todo_check = self._check_todos_placeholders(content)
        checks.append(todo_check)
        if todo_check.issue:
            issues.append(todo_check.issue)
        
        # Check for examples
        example_check = self._check_examples(content, metadata)
        checks.append(example_check)
        if example_check.issue:
            issues.append(example_check.issue)
        
        # Check section depth
        depth_check = self._check_section_depth(content)
        checks.append(depth_check)
        if depth_check.issue:
            issues.append(depth_check.issue)
        
        # Check for empty sections
        empty_check = self._check_empty_sections(content)
        checks.append(empty_check)
        if empty_check.issue:
            issues.append(empty_check.issue)
        
        # Calculate metrics
        self.checks_performed = len(checks)
        self.checks_passed = sum(1 for check in checks if check.passed)
        
        # Calculate score
        score = self._calculate_score(issues)
        
        # Compile metrics
        metrics = {
            'section_count': self._metrics.get('sections', 0),
            'todo_count': self._metrics.get('todos', 0),
            'example_count': self._metrics.get('examples', 0),
            'word_count': len(content.split()),
            'completeness_ratio': self.checks_passed / self.checks_performed if self.checks_performed > 0 else 1.0
        }
        
        return DimensionResult(
            dimension=self.dimension,
            score=score,
            weight=self.weight,
            issues=issues,
            passed_checks=self.checks_passed,
            total_checks=self.checks_performed,
            metrics=metrics
        )
    
    def _check_required_sections(self, content: str, metadata: Dict[str, Any]) -> CheckResult:
        """Check for required documentation sections."""
        doc_type = metadata.get('document_type', 'generic')
        
        # Define required sections by document type
        required_sections = {
            'readme': ['Installation', 'Usage', 'Features', 'License'],
            'api': ['Endpoints', 'Authentication', 'Parameters', 'Responses'],
            'guide': ['Introduction', 'Prerequisites', 'Steps', 'Conclusion'],
            'specification': ['Overview', 'Requirements', 'Architecture', 'Implementation'],
            'generic': ['Introduction', 'Description']
        }
        
        required = required_sections.get(doc_type, required_sections['generic'])
        
        # Find section headers
        headers = re.findall(r'^#+\s+(.+)$', content, re.MULTILINE)
        self._metrics['sections'] = len(headers)
        
        # Check for missing sections
        missing = []
        for section in required:
            if not any(section.lower() in header.lower() for header in headers):
                missing.append(section)
        
        if missing:
            return CheckResult(
                passed=False,
                issue=self._create_issue(
                    severity=ReviewSeverity.HIGH,
                    title="Missing required sections",
                    description=f"Document is missing {len(missing)} required sections",
                    suggestion=f"Add the following sections: {', '.join(missing)}",
                    auto_fixable=False
                )
            )
        
        return CheckResult(passed=True)
    
    def _check_todos_placeholders(self, content: str) -> CheckResult:
        """Check for TODOs and placeholder text."""
        # Patterns for TODOs and placeholders
        todo_patterns = [
            r'TODO:?.*',
            r'FIXME:?.*',
            r'XXX:?.*',
            r'HACK:?.*',
            r'\[TBD\]',
            r'\[TO BE DETERMINED\]',
            r'<placeholder>',
            r'\.\.\.',  # Ellipsis as placeholder
        ]
        
        todos_found = []
        for pattern in todo_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            todos_found.extend(matches)
        
        self._metrics['todos'] = len(todos_found)
        
        if todos_found:
            return CheckResult(
                passed=False,
                issue=self._create_issue(
                    severity=ReviewSeverity.MEDIUM,
                    title="Incomplete content detected",
                    description=f"Found {len(todos_found)} TODOs or placeholders",
                    suggestion="Complete all TODO items and replace placeholder text",
                    code_snippet='\n'.join(todos_found[:5]),  # Show first 5
                    auto_fixable=False
                )
            )
        
        return CheckResult(passed=True)
    
    def _check_examples(self, content: str, metadata: Dict[str, Any]) -> CheckResult:
        """Check for presence of examples."""
        # Look for example indicators
        example_patterns = [
            r'[Ee]xample:',
            r'[Ff]or example',
            r'```',  # Code blocks often contain examples
            r'[Ss]ample:',
            r'[Dd]emo:',
        ]
        
        example_count = 0
        for pattern in example_patterns:
            matches = re.findall(pattern, content)
            example_count += len(matches)
        
        self._metrics['examples'] = example_count
        
        # Check if document should have examples
        doc_type = metadata.get('document_type', 'generic')
        needs_examples = doc_type in ['api', 'guide', 'tutorial', 'documentation']
        
        if needs_examples and example_count < 2:
            return CheckResult(
                passed=False,
                issue=self._create_issue(
                    severity=ReviewSeverity.MEDIUM,
                    title="Insufficient examples",
                    description=f"Document has only {example_count} examples",
                    suggestion="Add more examples to illustrate concepts and usage",
                    auto_fixable=False,
                    confidence=0.8
                )
            )
        
        return CheckResult(passed=True)
    
    def _check_section_depth(self, content: str) -> CheckResult:
        """Check if sections have sufficient depth and detail."""
        # Split content into sections
        sections = re.split(r'^#+\s+', content, flags=re.MULTILINE)
        
        # Check for very short sections
        short_sections = []
        for i, section in enumerate(sections[1:], 1):  # Skip first split (before any header)
            lines = section.strip().split('\n')
            if lines:
                header = lines[0]
                content_lines = [line for line in lines[1:] if line.strip()]
                word_count = sum(len(line.split()) for line in content_lines)
                
                if word_count < 20:  # Section with less than 20 words
                    short_sections.append(f"{header[:30]} ({word_count} words)")
        
        if len(short_sections) > 2:  # More than 2 short sections
            return CheckResult(
                passed=False,
                issue=self._create_issue(
                    severity=ReviewSeverity.MEDIUM,
                    title="Multiple sections lack detail",
                    description=f"Found {len(short_sections)} sections with insufficient content",
                    suggestion="Expand these sections with more detail: " + ', '.join(short_sections[:3]),
                    auto_fixable=False
                )
            )
        
        return CheckResult(passed=True)
    
    def _check_empty_sections(self, content: str) -> CheckResult:
        """Check for empty or near-empty sections."""
        # Find consecutive headers without content between them
        header_pattern = r'^(#+)\s+(.+)$'
        
        empty_sections = []
        lines = content.split('\n')
        
        i = 0
        while i < len(lines):
            if re.match(header_pattern, lines[i]):
                header = lines[i]
                # Check content until next header or end
                j = i + 1
                content_found = False
                
                while j < len(lines):
                    if re.match(header_pattern, lines[j]):
                        break
                    if lines[j].strip() and not lines[j].strip().startswith('#'):
                        content_found = True
                        break
                    j += 1
                
                if not content_found:
                    empty_sections.append(header.strip())
            
            i += 1
        
        if empty_sections:
            return CheckResult(
                passed=False,
                issue=self._create_issue(
                    severity=ReviewSeverity.HIGH,
                    title="Empty sections detected",
                    description=f"Found {len(empty_sections)} empty sections",
                    suggestion=f"Add content to these sections: {', '.join(empty_sections[:3])}",
                    auto_fixable=False
                )
            )
        
        return CheckResult(passed=True)


class ConsistencyDimension(BaseDimension):
    """
    Analyzes document consistency.
    
    Checks for:
    - Terminology consistency
    - Formatting consistency
    - Style consistency
    - Reference consistency
    - Naming conventions
    """
    
    def _get_dimension(self) -> ReviewDimension:
        return ReviewDimension.CONSISTENCY
    
    async def analyze(self, content: str, metadata: Dict[str, Any]) -> DimensionResult:
        """Analyze document consistency."""
        issues = []
        checks = []
        
        # Check terminology consistency
        term_check = self._check_terminology_consistency(content)
        checks.append(term_check)
        if term_check.issue:
            issues.append(term_check.issue)
        
        # Check formatting consistency
        format_check = self._check_formatting_consistency(content)
        checks.append(format_check)
        if format_check.issue:
            issues.append(format_check.issue)
        
        # Check reference consistency
        ref_check = self._check_reference_consistency(content)
        checks.append(ref_check)
        if ref_check.issue:
            issues.append(ref_check.issue)
        
        # Check naming conventions
        naming_check = self._check_naming_conventions(content)
        checks.append(naming_check)
        if naming_check.issue:
            issues.append(naming_check.issue)
        
        # Check header consistency
        header_check = self._check_header_consistency(content)
        checks.append(header_check)
        if header_check.issue:
            issues.append(header_check.issue)
        
        # Calculate metrics
        self.checks_performed = len(checks)
        self.checks_passed = sum(1 for check in checks if check.passed)
        
        # Calculate score
        score = self._calculate_score(issues)
        
        # Compile metrics
        metrics = {
            'terminology_variants': self._metrics.get('term_variants', 0),
            'formatting_issues': self._metrics.get('format_issues', 0),
            'broken_references': self._metrics.get('broken_refs', 0),
            'naming_violations': self._metrics.get('naming_issues', 0),
            'consistency_score': score
        }
        
        return DimensionResult(
            dimension=self.dimension,
            score=score,
            weight=self.weight,
            issues=issues,
            passed_checks=self.checks_passed,
            total_checks=self.checks_performed,
            metrics=metrics
        )
    
    def _check_terminology_consistency(self, content: str) -> CheckResult:
        """Check for consistent terminology usage."""
        # Common terminology variations
        term_variations = [
            ['API', 'api', 'Api'],
            ['URL', 'url', 'Url'],
            ['ID', 'id', 'Id'],
            ['JSON', 'json', 'Json'],
            ['XML', 'xml', 'Xml'],
            ['HTTP', 'http', 'Http'],
            ['HTTPS', 'https', 'Https'],
            ['REST', 'rest', 'Rest', 'ReST'],
            ['GraphQL', 'graphql', 'Graphql'],
            ['SQL', 'sql', 'Sql'],
        ]
        
        inconsistencies = []
        for variations in term_variations:
            found = []
            for term in variations:
                if re.search(r'\b' + re.escape(term) + r'\b', content):
                    found.append(term)
            
            if len(found) > 1:
                inconsistencies.append(f"Inconsistent usage: {', '.join(found)}")
        
        self._metrics['term_variants'] = len(inconsistencies)
        
        if inconsistencies:
            return CheckResult(
                passed=False,
                issue=self._create_issue(
                    severity=ReviewSeverity.LOW,
                    title="Terminology inconsistencies",
                    description=f"Found {len(inconsistencies)} terminology inconsistencies",
                    suggestion="Use consistent terminology: " + '; '.join(inconsistencies[:3]),
                    auto_fixable=True,
                    confidence=0.9
                )
            )
        
        return CheckResult(passed=True)
    
    def _check_formatting_consistency(self, content: str) -> CheckResult:
        """Check for consistent formatting."""
        issues = []
        
        # Check list formatting
        bullet_styles = set()
        for line in content.split('\n'):
            if re.match(r'^\s*[-*+]\s+', line):
                bullet = re.match(r'^\s*([-*+])\s+', line).group(1)
                bullet_styles.add(bullet)
        
        if len(bullet_styles) > 1:
            issues.append(f"Mixed bullet styles: {', '.join(bullet_styles)}")
        
        # Check header formatting
        headers = re.findall(r'^(#+)\s+(.+)$', content, re.MULTILINE)
        header_issues = []
        
        for level, text in headers:
            # Check for inconsistent capitalization
            if text[0].islower() and len(text) > 1:
                header_issues.append(f"Lowercase header: {text[:30]}")
        
        if header_issues:
            issues.extend(header_issues[:2])
        
        # Check code block formatting
        code_blocks = re.findall(r'```(\w*)\n', content)
        if code_blocks:
            # Check for inconsistent language specifications
            specified = [cb for cb in code_blocks if cb]
            unspecified = [cb for cb in code_blocks if not cb]
            
            if specified and unspecified:
                issues.append(f"Inconsistent code block language specifications")
        
        self._metrics['format_issues'] = len(issues)
        
        if issues:
            return CheckResult(
                passed=False,
                issue=self._create_issue(
                    severity=ReviewSeverity.LOW,
                    title="Formatting inconsistencies",
                    description=f"Found {len(issues)} formatting inconsistencies",
                    suggestion="Fix formatting issues: " + '; '.join(issues[:3]),
                    auto_fixable=True
                )
            )
        
        return CheckResult(passed=True)
    
    def _check_reference_consistency(self, content: str) -> CheckResult:
        """Check for consistent and valid references."""
        # Find all links and references
        link_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
        links = re.findall(link_pattern, content)
        
        # Find all headers for internal references
        headers = re.findall(r'^#+\s+(.+)$', content, re.MULTILINE)
        header_anchors = [h.lower().replace(' ', '-').replace('.', '') for h in headers]
        
        broken_refs = []
        for text, url in links:
            if url.startswith('#'):
                # Internal reference
                anchor = url[1:]
                if anchor not in header_anchors:
                    broken_refs.append(f"Broken internal link: [{text}]({url})")
            elif url.startswith('http'):
                # External reference - just check format
                if not re.match(r'https?://[^\s]+', url):
                    broken_refs.append(f"Malformed URL: {url}")
        
        self._metrics['broken_refs'] = len(broken_refs)
        
        if broken_refs:
            return CheckResult(
                passed=False,
                issue=self._create_issue(
                    severity=ReviewSeverity.MEDIUM,
                    title="Broken or invalid references",
                    description=f"Found {len(broken_refs)} broken references",
                    suggestion="Fix these references: " + '; '.join(broken_refs[:3]),
                    auto_fixable=False
                )
            )
        
        return CheckResult(passed=True)
    
    def _check_naming_conventions(self, content: str) -> CheckResult:
        """Check for consistent naming conventions."""
        # Extract variable/function names from code blocks
        code_pattern = r'```(?:\w+)?\n(.*?)\n```'
        code_blocks = re.findall(code_pattern, content, re.DOTALL)
        
        naming_issues = []
        
        for code in code_blocks:
            # Check for mixed naming conventions
            camelCase = re.findall(r'\b[a-z][a-zA-Z]*(?=[(\[]|\s*=)', code)
            snake_case = re.findall(r'\b[a-z]+(?:_[a-z]+)+\b', code)
            PascalCase = re.findall(r'\b[A-Z][a-zA-Z]*\b', code)
            
            # Detect mixed conventions (excluding common patterns)
            if camelCase and snake_case:
                # Filter out common exceptions
                snake_case_filtered = [s for s in snake_case if not s.startswith('test_')]
                if snake_case_filtered and len(camelCase) > 2 and len(snake_case_filtered) > 2:
                    naming_issues.append("Mixed camelCase and snake_case")
        
        self._metrics['naming_issues'] = len(naming_issues)
        
        if naming_issues:
            return CheckResult(
                passed=False,
                issue=self._create_issue(
                    severity=ReviewSeverity.LOW,
                    title="Inconsistent naming conventions",
                    description=f"Found {len(naming_issues)} naming convention issues",
                    suggestion="Use consistent naming: " + '; '.join(set(naming_issues)),
                    auto_fixable=False,
                    confidence=0.7
                )
            )
        
        return CheckResult(passed=True)
    
    def _check_header_consistency(self, content: str) -> CheckResult:
        """Check for consistent header hierarchy."""
        headers = re.findall(r'^(#+)\s+(.+)$', content, re.MULTILINE)
        
        if not headers:
            return CheckResult(passed=True)
        
        issues = []
        
        # Check for skipped levels
        levels = [len(h[0]) for h in headers]
        for i in range(1, len(levels)):
            if levels[i] > levels[i-1] + 1:
                issues.append(f"Skipped header level at '{headers[i][1][:30]}'")
        
        # Check for inconsistent top-level headers
        top_level = min(levels)
        if top_level > 1:
            issues.append(f"Document starts with level {top_level} header instead of level 1")
        
        if issues:
            return CheckResult(
                passed=False,
                issue=self._create_issue(
                    severity=ReviewSeverity.MEDIUM,
                    title="Header hierarchy issues",
                    description=f"Found {len(issues)} header structure issues",
                    suggestion="Fix header hierarchy: " + '; '.join(issues[:2]),
                    auto_fixable=True
                )
            )
        
        return CheckResult(passed=True)


class StyleFormattingDimension(BaseDimension):
    """
    Analyzes style and formatting quality.
    
    Checks for:
    - Markdown formatting
    - Code formatting
    - Readability
    - Grammar and spelling
    - Document structure
    """
    
    def _get_dimension(self) -> ReviewDimension:
        return ReviewDimension.STYLE_FORMATTING
    
    async def analyze(self, content: str, metadata: Dict[str, Any]) -> DimensionResult:
        """Analyze style and formatting."""
        issues = []
        checks = []
        
        # Check markdown formatting
        md_check = self._check_markdown_formatting(content)
        checks.append(md_check)
        if md_check.issue:
            issues.append(md_check.issue)
        
        # Check code formatting
        code_check = self._check_code_formatting(content)
        checks.append(code_check)
        if code_check.issue:
            issues.append(code_check.issue)
        
        # Check readability
        read_check = self._check_readability(content)
        checks.append(read_check)
        if read_check.issue:
            issues.append(read_check.issue)
        
        # Check line length
        line_check = self._check_line_length(content)
        checks.append(line_check)
        if line_check.issue:
            issues.append(line_check.issue)
        
        # Check whitespace issues
        space_check = self._check_whitespace(content)
        checks.append(space_check)
        if space_check.issue:
            issues.append(space_check.issue)
        
        # Calculate metrics
        self.checks_performed = len(checks)
        self.checks_passed = sum(1 for check in checks if check.passed)
        
        # Calculate score
        score = self._calculate_score(issues)
        
        # Compile metrics
        metrics = {
            'markdown_issues': self._metrics.get('md_issues', 0),
            'code_formatting_issues': self._metrics.get('code_issues', 0),
            'readability_score': self._metrics.get('readability', 100),
            'long_lines': self._metrics.get('long_lines', 0),
            'whitespace_issues': self._metrics.get('whitespace', 0)
        }
        
        return DimensionResult(
            dimension=self.dimension,
            score=score,
            weight=self.weight,
            issues=issues,
            passed_checks=self.checks_passed,
            total_checks=self.checks_performed,
            metrics=metrics
        )
    
    def _check_markdown_formatting(self, content: str) -> CheckResult:
        """Check markdown formatting issues."""
        issues = []
        
        # Check for missing blank lines around headers
        lines = content.split('\n')
        for i in range(len(lines)):
            if re.match(r'^#+\s+', lines[i]):
                if i > 0 and lines[i-1].strip() != '':
                    issues.append(f"Missing blank line before header at line {i+1}")
                if i < len(lines)-1 and lines[i+1].strip() != '' and not re.match(r'^#+\s+', lines[i+1]):
                    issues.append(f"Missing blank line after header at line {i+1}")
        
        # Check for improper list formatting
        for i, line in enumerate(lines):
            if re.match(r'^\s*[-*+]\s+', line):
                # Check for proper spacing after bullet
                if not re.match(r'^\s*[-*+]\s{1}[^\s]', line):
                    issues.append(f"Improper list spacing at line {i+1}")
        
        # Check for broken bold/italic formatting
        if re.search(r'\*{3,}', content) or re.search(r'_{3,}', content):
            issues.append("Excessive asterisks or underscores detected")
        
        self._metrics['md_issues'] = len(issues)
        
        if issues:
            return CheckResult(
                passed=False,
                issue=self._create_issue(
                    severity=ReviewSeverity.LOW,
                    title="Markdown formatting issues",
                    description=f"Found {len(issues)} markdown formatting issues",
                    suggestion="Fix formatting: " + '; '.join(issues[:3]),
                    auto_fixable=True
                )
            )
        
        return CheckResult(passed=True)
    
    def _check_code_formatting(self, content: str) -> CheckResult:
        """Check code block formatting."""
        code_pattern = r'```(\w*)\n(.*?)\n```'
        code_blocks = re.findall(code_pattern, content, re.DOTALL)
        
        issues = []
        
        for lang, code in code_blocks:
            lines = code.split('\n')
            
            # Check indentation consistency
            indents = []
            for line in lines:
                if line.strip():
                    leading_spaces = len(line) - len(line.lstrip())
                    if leading_spaces > 0:
                        indents.append(leading_spaces)
            
            if indents:
                # Check if indentation is consistent (multiples of 2 or 4)
                base_indent = min(indents)
                if base_indent > 0:
                    inconsistent = [i for i in indents if i % base_indent != 0]
                    if inconsistent:
                        issues.append("Inconsistent indentation in code block")
            
            # Check for trailing whitespace
            trailing_ws = sum(1 for line in lines if line.rstrip() != line)
            if trailing_ws > 0:
                issues.append(f"{trailing_ws} lines with trailing whitespace")
        
        self._metrics['code_issues'] = len(issues)
        
        if issues:
            return CheckResult(
                passed=False,
                issue=self._create_issue(
                    severity=ReviewSeverity.LOW,
                    title="Code formatting issues",
                    description=f"Found {len(issues)} code formatting issues",
                    suggestion="Fix code formatting: " + '; '.join(set(issues)[:3]),
                    auto_fixable=True
                )
            )
        
        return CheckResult(passed=True)
    
    def _check_readability(self, content: str) -> CheckResult:
        """Check document readability."""
        # Simple readability checks
        sentences = re.split(r'[.!?]+', content)
        
        # Check for overly long sentences
        long_sentences = []
        for sentence in sentences:
            words = sentence.split()
            if len(words) > 50:  # More than 50 words
                long_sentences.append(f"{' '.join(words[:10])}... ({len(words)} words)")
        
        # Check for complex words (very simple heuristic)
        complex_word_count = 0
        words = content.split()
        for word in words:
            if len(word) > 12 and word.isalpha():  # Words longer than 12 characters
                complex_word_count += 1
        
        readability_score = 100
        if long_sentences:
            readability_score -= len(long_sentences) * 5
        if complex_word_count > 20:
            readability_score -= 10
        
        self._metrics['readability'] = max(0, readability_score)
        
        if long_sentences:
            return CheckResult(
                passed=False,
                issue=self._create_issue(
                    severity=ReviewSeverity.LOW,
                    title="Readability issues",
                    description=f"Found {len(long_sentences)} overly long sentences",
                    suggestion="Break up long sentences for better readability",
                    code_snippet='\n'.join(long_sentences[:3]),
                    auto_fixable=False,
                    confidence=0.7
                )
            )
        
        return CheckResult(passed=True)
    
    def _check_line_length(self, content: str) -> CheckResult:
        """Check for overly long lines."""
        lines = content.split('\n')
        long_lines = []
        
        for i, line in enumerate(lines):
            # Skip code blocks and URLs
            if '```' in line or 'http' in line:
                continue
            
            if len(line) > 120:  # Lines longer than 120 characters
                long_lines.append(f"Line {i+1}: {len(line)} characters")
        
        self._metrics['long_lines'] = len(long_lines)
        
        if len(long_lines) > 5:  # More than 5 long lines
            return CheckResult(
                passed=False,
                issue=self._create_issue(
                    severity=ReviewSeverity.LOW,
                    title="Long lines detected",
                    description=f"Found {len(long_lines)} lines exceeding 120 characters",
                    suggestion="Break long lines for better readability",
                    code_snippet='\n'.join(long_lines[:5]),
                    auto_fixable=False
                )
            )
        
        return CheckResult(passed=True)
    
    def _check_whitespace(self, content: str) -> CheckResult:
        """Check for whitespace issues."""
        issues = []
        
        # Check for trailing whitespace
        lines = content.split('\n')
        trailing_ws = sum(1 for line in lines if line.rstrip() != line)
        if trailing_ws > 0:
            issues.append(f"{trailing_ws} lines with trailing whitespace")
        
        # Check for multiple consecutive blank lines
        blank_runs = re.findall(r'\n{3,}', content)
        if blank_runs:
            issues.append(f"{len(blank_runs)} instances of excessive blank lines")
        
        # Check for tabs vs spaces mixing
        has_tabs = '\t' in content
        has_spaces = '    ' in content  # 4 spaces for indentation
        if has_tabs and has_spaces:
            issues.append("Mixed tabs and spaces for indentation")
        
        self._metrics['whitespace'] = len(issues)
        
        if issues:
            return CheckResult(
                passed=False,
                issue=self._create_issue(
                    severity=ReviewSeverity.LOW,
                    title="Whitespace issues",
                    description=f"Found {len(issues)} whitespace issues",
                    suggestion="Clean up whitespace: " + '; '.join(issues),
                    auto_fixable=True
                )
            )
        
        return CheckResult(passed=True)


class SecurityPIIDimension(BaseDimension):
    """
    Analyzes security and PII concerns.
    
    Checks for:
    - PII exposure using PIIDetector from M002
    - Sensitive information leaks
    - Security vulnerabilities in examples
    - API keys and credentials
    - Unsafe practices in documentation
    """
    
    def __init__(self, weight: float = 0.2):
        """Initialize with PIIDetector."""
        super().__init__(weight)
        self.pii_detector = PIIDetector()
    
    def _get_dimension(self) -> ReviewDimension:
        return ReviewDimension.SECURITY_PII
    
    async def analyze(self, content: str, metadata: Dict[str, Any]) -> DimensionResult:
        """Analyze security and PII concerns."""
        issues = []
        checks = []
        
        # Check for PII
        pii_check = self._check_pii(content)
        checks.append(pii_check)
        if pii_check.issue:
            issues.append(pii_check.issue)
        
        # Check for credentials
        cred_check = self._check_credentials(content)
        checks.append(cred_check)
        if cred_check.issue:
            issues.append(cred_check.issue)
        
        # Check for security vulnerabilities
        vuln_check = self._check_security_vulnerabilities(content)
        checks.append(vuln_check)
        if vuln_check.issue:
            issues.append(vuln_check.issue)
        
        # Check for unsafe practices
        unsafe_check = self._check_unsafe_practices(content)
        checks.append(unsafe_check)
        if unsafe_check.issue:
            issues.append(unsafe_check.issue)
        
        # Check for sensitive paths
        path_check = self._check_sensitive_paths(content)
        checks.append(path_check)
        if path_check.issue:
            issues.append(path_check.issue)
        
        # Calculate metrics
        self.checks_performed = len(checks)
        self.checks_passed = sum(1 for check in checks if check.passed)
        
        # Calculate score (security issues have higher impact)
        score = self._calculate_score(issues, base_score=100.0)
        
        # Compile metrics
        metrics = {
            'pii_found': self._metrics.get('pii_count', 0),
            'credentials_found': self._metrics.get('creds', 0),
            'vulnerabilities': self._metrics.get('vulns', 0),
            'unsafe_practices': self._metrics.get('unsafe', 0),
            'security_score': score
        }
        
        return DimensionResult(
            dimension=self.dimension,
            score=score,
            weight=self.weight,
            issues=issues,
            passed_checks=self.checks_passed,
            total_checks=self.checks_performed,
            metrics=metrics
        )
    
    def _check_pii(self, content: str) -> CheckResult:
        """Check for PII using PIIDetector."""
        # Detect PII
        pii_matches = self.pii_detector.detect(content)
        
        self._metrics['pii_count'] = len(pii_matches)
        
        if pii_matches:
            # Group by PII type
            pii_by_type = {}
            for match in pii_matches:
                pii_type = match.pii_type.value
                if pii_type not in pii_by_type:
                    pii_by_type[pii_type] = []
                pii_by_type[pii_type].append(match.value[:20] + '...' if len(match.value) > 20 else match.value)
            
            description = f"Found {len(pii_matches)} instances of PII: "
            description += ', '.join(f"{type_}: {len(items)}" for type_, items in pii_by_type.items())
            
            return CheckResult(
                passed=False,
                issue=self._create_issue(
                    severity=ReviewSeverity.CRITICAL,
                    title="PII detected in document",
                    description=description,
                    suggestion="Remove or mask all PII before publishing",
                    code_snippet='\n'.join(f"{k}: {v[0]}" for k, v in list(pii_by_type.items())[:3]),
                    auto_fixable=True
                )
            )
        
        return CheckResult(passed=True)
    
    def _check_credentials(self, content: str) -> CheckResult:
        """Check for exposed credentials and API keys."""
        # Patterns for common credentials
        credential_patterns = [
            (r'[Aa][Pp][Ii][_-]?[Kk][Ee][Yy]\s*[:=]\s*["\']?[\w\-]{20,}', "API Key"),
            (r'[Ss][Ee][Cc][Rr][Ee][Tt]\s*[:=]\s*["\']?[\w\-]{20,}', "Secret"),
            (r'[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]\s*[:=]\s*["\']?[^\s"\']+', "Password"),
            (r'[Tt][Oo][Kk][Ee][Nn]\s*[:=]\s*["\']?[\w\-]{20,}', "Token"),
            (r'Bearer\s+[\w\-\.]+', "Bearer Token"),
            (r'[Aa][Ww][Ss][_-]?[Aa][Cc][Cc][Ee][Ss][Ss][_-]?[Kk][Ee][Yy][_-]?[Ii][Dd]\s*[:=]\s*["\']?[A-Z0-9]{20}', "AWS Access Key"),
            (r'[Aa][Ww][Ss][_-]?[Ss][Ee][Cc][Rr][Ee][Tt][_-]?[Aa][Cc][Cc][Ee][Ss][Ss][_-]?[Kk][Ee][Yy]\s*[:=]\s*["\']?[\w\+/]{40}', "AWS Secret Key"),
        ]
        
        found_credentials = []
        for pattern, cred_type in credential_patterns:
            matches = re.findall(pattern, content)
            if matches:
                # Filter out obvious placeholders
                real_creds = [m for m in matches if not any(placeholder in m.lower() for placeholder in 
                             ['example', 'placeholder', 'your-', 'xxx', '...', '<', '>'])]
                if real_creds:
                    found_credentials.append((cred_type, len(real_creds)))
        
        self._metrics['creds'] = sum(count for _, count in found_credentials)
        
        if found_credentials:
            description = "Found potential credentials: " + ', '.join(f"{type_}: {count}" for type_, count in found_credentials)
            
            return CheckResult(
                passed=False,
                issue=self._create_issue(
                    severity=ReviewSeverity.BLOCKER,
                    title="Exposed credentials detected",
                    description=description,
                    suggestion="Replace all real credentials with placeholders or environment variables",
                    auto_fixable=False
                )
            )
        
        return CheckResult(passed=True)
    
    def _check_security_vulnerabilities(self, content: str) -> CheckResult:
        """Check for security vulnerabilities in code examples."""
        vulnerabilities = []
        
        # SQL injection vulnerabilities
        sql_patterns = [
            r'query\s*\(\s*["\']SELECT.*\+.*["\']',  # String concatenation in SQL
            r'execute\s*\(\s*["\'].*%s.*["\'].*%',  # Unsafe string formatting
            r'f["\']SELECT.*{.*}',  # F-string in SQL
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                vulnerabilities.append("Potential SQL injection vulnerability")
                break
        
        # XSS vulnerabilities
        xss_patterns = [
            r'innerHTML\s*=',  # Direct innerHTML assignment
            r'document\.write\(',  # document.write usage
            r'eval\s*\(',  # eval usage
        ]
        
        for pattern in xss_patterns:
            if re.search(pattern, content):
                vulnerabilities.append("Potential XSS vulnerability")
                break
        
        # Command injection
        cmd_patterns = [
            r'os\.system\s*\(',  # os.system usage
            r'subprocess\.call\s*\([^,\]]*\+',  # String concatenation in subprocess
            r'exec\s*\(',  # exec usage
        ]
        
        for pattern in cmd_patterns:
            if re.search(pattern, content):
                vulnerabilities.append("Potential command injection vulnerability")
                break
        
        self._metrics['vulns'] = len(vulnerabilities)
        
        if vulnerabilities:
            return CheckResult(
                passed=False,
                issue=self._create_issue(
                    severity=ReviewSeverity.HIGH,
                    title="Security vulnerabilities in examples",
                    description=f"Found {len(vulnerabilities)} potential security issues",
                    suggestion="Use secure coding practices: " + '; '.join(vulnerabilities),
                    auto_fixable=False
                )
            )
        
        return CheckResult(passed=True)
    
    def _check_unsafe_practices(self, content: str) -> CheckResult:
        """Check for unsafe practices in documentation."""
        unsafe_practices = []
        
        # Check for unsafe recommendations
        unsafe_patterns = [
            (r'disable.*security', "Disabling security features"),
            (r'skip.*verif', "Skipping verification"),
            (r'ignore.*cert', "Ignoring certificates"),
            (r'trust.*all', "Trusting all sources"),
            (r'allow.*any', "Allowing any input"),
            (r'chmod\s+777', "Overly permissive file permissions"),
            (r'CORS.*\*', "Overly permissive CORS"),
            (r'Access-Control-Allow-Origin.*\*', "Wildcard CORS origin"),
        ]
        
        for pattern, description in unsafe_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                unsafe_practices.append(description)
        
        self._metrics['unsafe'] = len(unsafe_practices)
        
        if unsafe_practices:
            return CheckResult(
                passed=False,
                issue=self._create_issue(
                    severity=ReviewSeverity.HIGH,
                    title="Unsafe practices documented",
                    description=f"Found {len(unsafe_practices)} unsafe practice recommendations",
                    suggestion="Replace with secure alternatives: " + '; '.join(unsafe_practices),
                    auto_fixable=False
                )
            )
        
        return CheckResult(passed=True)
    
    def _check_sensitive_paths(self, content: str) -> CheckResult:
        """Check for sensitive file paths and system information."""
        sensitive_patterns = [
            (r'/home/[\w]+/', "User home directory path"),
            (r'/Users/[\w]+/', "macOS user path"),
            (r'C:\\Users\\[\w]+\\', "Windows user path"),
            (r'/etc/passwd', "System password file"),
            (r'/etc/shadow', "System shadow file"),
            (r'\.ssh/', "SSH directory"),
            (r'\.aws/', "AWS credentials directory"),
            (r'\.env', "Environment file"),
        ]
        
        found_paths = []
        for pattern, description in sensitive_patterns:
            if re.search(pattern, content):
                found_paths.append(description)
        
        if found_paths:
            return CheckResult(
                passed=False,
                issue=self._create_issue(
                    severity=ReviewSeverity.MEDIUM,
                    title="Sensitive paths exposed",
                    description=f"Found {len(found_paths)} sensitive path references",
                    suggestion="Replace with generic paths: " + '; '.join(found_paths),
                    auto_fixable=True,
                    confidence=0.8
                )
            )
        
        return CheckResult(passed=True)


def get_default_dimensions(weights: Optional[Dict[ReviewDimension, float]] = None) -> List[BaseDimension]:
    """
    Get default set of review dimensions with optional custom weights.
    
    Args:
        weights: Optional dictionary of dimension weights
        
    Returns:
        List of dimension instances
    """
    default_weights = {
        ReviewDimension.TECHNICAL_ACCURACY: 0.25,
        ReviewDimension.COMPLETENESS: 0.20,
        ReviewDimension.CONSISTENCY: 0.20,
        ReviewDimension.STYLE_FORMATTING: 0.15,
        ReviewDimension.SECURITY_PII: 0.20,
    }
    
    if weights:
        default_weights.update(weights)
    
    return [
        TechnicalAccuracyDimension(weight=default_weights[ReviewDimension.TECHNICAL_ACCURACY]),
        CompletenessDimension(weight=default_weights[ReviewDimension.COMPLETENESS]),
        ConsistencyDimension(weight=default_weights[ReviewDimension.CONSISTENCY]),
        StyleFormattingDimension(weight=default_weights[ReviewDimension.STYLE_FORMATTING]),
        SecurityPIIDimension(weight=default_weights[ReviewDimension.SECURITY_PII]),
    ]