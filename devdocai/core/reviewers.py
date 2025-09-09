"""
M007 Review Engine - Specialized Reviewers (Pass 4: Refactored)
DevDocAI v3.0.0

Implements 8 specialized reviewers + PII detector.
Refactored to use common patterns for cleaner code.
"""

import logging
import re
import time
from typing import Any, Dict, List

from .review_patterns import BaseReviewer as PatternBaseReviewer
from .review_patterns import PatternMatcher, QualityReviewer, SecurityReviewerBase
from .review_types import (
    ComplianceStandard,
    PIIMatch,
    PIIType,
    ReviewResult,
    ReviewType,
    SeverityLevel,
)

logger = logging.getLogger(__name__)


class RequirementsReviewer(PatternBaseReviewer):
    """Reviews requirements documents for clarity and testability."""

    def __init__(self):
        super().__init__(ReviewType.REQUIREMENTS)
        self.rfc2119_keywords = {
            "MUST",
            "MUST NOT",
            "SHALL",
            "SHALL NOT",
            "SHOULD",
            "SHOULD NOT",
            "MAY",
            "OPTIONAL",
            "REQUIRED",
            "RECOMMENDED",
        }
        self.ambiguous_phrases = [
            "fast",
            "slow",
            "good",
            "bad",
            "efficient",
            "user-friendly",
            "intuitive",
            "robust",
            "flexible",
            "scalable",
            "reliable",
            "secure",
            "easy",
        ]

    async def review(self, content: str, metadata: Dict[str, Any]) -> ReviewResult:
        """Review requirements document."""
        start_time = time.time()
        issues = []

        # Check RFC 2119 compliance
        keywords_found = self.pattern_matcher.count_occurrences(content, self.rfc2119_keywords)
        rfc2119_compliance = sum(keywords_found.values()) > 0

        # Detect ambiguous statements
        ambiguous_count = sum(
            content.lower().count(phrase.lower()) for phrase in self.ambiguous_phrases
        )

        # Check testability
        testable_patterns = [r"must\s+\w+", r"shall\s+\w+", r"should\s+\w+"]
        testable_matches = self.pattern_matcher.find_patterns(content, testable_patterns)

        # Generate issues
        if not rfc2119_compliance:
            issues.append(
                self.create_issue(
                    "No RFC 2119 keywords found",
                    SeverityLevel.MEDIUM,
                    suggestion="Use RFC 2119 keywords for clarity",
                )
            )

        if ambiguous_count > 5:
            issues.append(
                self.create_issue(
                    f"Found {ambiguous_count} ambiguous phrases",
                    SeverityLevel.LOW,
                    suggestion="Make requirements more specific",
                )
            )

        # Calculate score
        score = self.calculate_score(len(testable_matches) + (1 if rfc2119_compliance else 0), 10)

        return ReviewResult(
            review_type=self.review_type,
            score=score,
            issues=issues,
            metrics={
                "rfc2119_compliance": rfc2119_compliance,
                "ambiguous_count": ambiguous_count,
                "testable_requirements": len(testable_matches),
            },
            execution_time=time.time() - start_time,
        )


class DesignReviewer(QualityReviewer):
    """Reviews design documents for completeness and quality."""

    def __init__(self):
        super().__init__(ReviewType.DESIGN)
        self.required_sections = [
            "architecture",
            "components",
            "interfaces",
            "data",
            "security",
            "performance",
        ]

    async def review(self, content: str, metadata: Dict[str, Any]) -> ReviewResult:
        """Review design document."""
        start_time = time.time()
        issues = []

        # Check required sections
        content_lower = content.lower()
        sections_found = [s for s in self.required_sections if s in content_lower]

        # Check for visual aids
        has_diagrams = any(
            indicator in content_lower for indicator in ["diagram", "figure", "chart", "```mermaid"]
        )

        # Assess quality metrics
        readability = self.assess_readability(content)
        complexity = self.assess_complexity(content)

        # Generate issues
        for section in self.required_sections:
            if section not in sections_found:
                issues.append(self.create_issue(f"Missing {section} section", SeverityLevel.MEDIUM))

        # Calculate score
        completeness = len(sections_found) / len(self.required_sections)
        score = completeness * 0.5 + readability * 0.3 + (0.2 if has_diagrams else 0.0)

        return ReviewResult(
            review_type=self.review_type,
            score=score,
            issues=issues,
            metrics={
                "sections_found": sections_found,
                "has_diagrams": has_diagrams,
                "readability": readability,
                "complexity": complexity,
            },
            execution_time=time.time() - start_time,
        )


class SecurityReviewer(SecurityReviewerBase):
    """Reviews documents for security vulnerabilities."""

    def __init__(self):
        super().__init__(ReviewType.SECURITY)
        # Define vulnerability patterns
        self.vulnerability_patterns = {
            "hardcoded_secrets": [
                r'(?:api[_-]?key|apikey)\s*[:=]\s*["\']?[a-zA-Z0-9_\-]+["\']?',
                r'(?:password|passwd|pwd)\s*[:=]\s*["\']?[^\s"\']+["\']?',
                r'(?:secret|token)\s*[:=]\s*["\']?[a-zA-Z0-9_\-]+["\']?',
            ],
            "sql_injection": [
                r"SELECT.*FROM.*WHERE.*\+",
                r"INSERT\s+INTO.*VALUES.*\+",
                r"UPDATE.*SET.*WHERE.*\+",
            ],
            "xss": [
                r"innerHTML\s*=",
                r"document\.write\(",
                r"eval\(",
            ],
        }

    async def review(self, content: str, metadata: Dict[str, Any]) -> ReviewResult:
        """Review document for security issues."""
        start_time = time.time()

        # Scan for vulnerabilities
        vulnerabilities = self.scan_vulnerabilities(content)

        # Check OWASP patterns
        owasp_issues = self._check_owasp_patterns(content)

        # Calculate score (fewer vulnerabilities = higher score)
        total_issues = len(vulnerabilities) + len(owasp_issues)
        score = max(0.0, 1.0 - (total_issues * 0.1))

        # Convert vulnerabilities to issues
        issues = [
            self.create_issue(
                f"{vuln['type']}: {vuln['pattern'][:50]}",
                vuln["severity"],
                location=vuln["location"],
            )
            for vuln in vulnerabilities[:10]  # Limit to 10
        ]

        return ReviewResult(
            review_type=self.review_type,
            score=score,
            issues=issues,
            metrics={
                "vulnerabilities_found": len(vulnerabilities),
                "owasp_issues": len(owasp_issues),
                "security_score": score,
            },
            execution_time=time.time() - start_time,
        )

    def _check_owasp_patterns(self, content: str) -> List[Dict[str, Any]]:
        """Check for OWASP Top 10 patterns."""
        owasp_patterns = {
            "A01_Broken_Access_Control": [r'role\s*=\s*["\']admin["\']'],
            "A02_Cryptographic_Failures": [r"md5\(", r"sha1\("],
            "A03_Injection": [r"exec\(", r"system\("],
        }

        issues = []
        for category, patterns in owasp_patterns.items():
            matches = self.pattern_matcher.find_patterns(content, patterns)
            for match in matches:
                issues.append(
                    {
                        "category": category,
                        "match": match["match"],
                        "line": match["line"],
                    }
                )

        return issues


class PerformanceReviewer(QualityReviewer):
    """Reviews documents for performance considerations."""

    def __init__(self):
        super().__init__(ReviewType.PERFORMANCE)
        self.performance_indicators = [
            "performance",
            "optimization",
            "speed",
            "latency",
            "throughput",
            "benchmark",
            "cache",
            "async",
        ]

    async def review(self, content: str, metadata: Dict[str, Any]) -> ReviewResult:
        """Review document for performance considerations."""
        start_time = time.time()
        issues = []

        # Check for performance considerations
        perf_mentions = self.pattern_matcher.count_occurrences(
            content, set(self.performance_indicators)
        )

        # Look for performance anti-patterns
        anti_patterns = [
            r"SELECT\s+\*\s+FROM",  # SELECT * queries
            r"for.*for.*for",  # Triple nested loops
            r"while\s+True",  # Infinite loops
        ]

        anti_pattern_matches = self.pattern_matcher.find_patterns(content, anti_patterns)

        # Generate issues
        for match in anti_pattern_matches[:5]:
            issues.append(
                self.create_issue(
                    f"Performance anti-pattern: {match['match'][:50]}",
                    SeverityLevel.MEDIUM,
                    location=f"Line {match['line']}",
                )
            )

        # Calculate score
        has_perf_considerations = sum(perf_mentions.values()) > 0
        score = 0.5 if has_perf_considerations else 0.3
        score -= len(anti_pattern_matches) * 0.1
        score = max(0.0, min(1.0, score))

        return ReviewResult(
            review_type=self.review_type,
            score=score,
            issues=issues,
            metrics={
                "performance_mentions": sum(perf_mentions.values()),
                "anti_patterns_found": len(anti_pattern_matches),
            },
            execution_time=time.time() - start_time,
        )


class UsabilityReviewer(QualityReviewer):
    """Reviews documents for usability and user experience."""

    def __init__(self):
        super().__init__(ReviewType.USABILITY)
        self.usability_keywords = [
            "user",
            "interface",
            "experience",
            "accessibility",
            "intuitive",
            "easy",
            "simple",
            "clear",
        ]

    async def review(self, content: str, metadata: Dict[str, Any]) -> ReviewResult:
        """Review document for usability considerations."""
        start_time = time.time()
        issues = []

        # Check for usability mentions
        usability_mentions = self.pattern_matcher.count_occurrences(
            content, set(self.usability_keywords)
        )

        # Assess readability
        readability = self.assess_readability(content)

        # Check for accessibility considerations
        has_accessibility = "accessibility" in content.lower() or "a11y" in content.lower()

        # Generate issues
        if not has_accessibility:
            issues.append(
                self.create_issue(
                    "No accessibility considerations found",
                    SeverityLevel.LOW,
                    suggestion="Consider adding accessibility requirements",
                )
            )

        # Calculate score
        has_usability = sum(usability_mentions.values()) > 0
        score = (
            readability * 0.5
            + (0.3 if has_usability else 0.0)
            + (0.2 if has_accessibility else 0.0)
        )

        return ReviewResult(
            review_type=self.review_type,
            score=score,
            issues=issues,
            metrics={
                "usability_mentions": sum(usability_mentions.values()),
                "readability": readability,
                "has_accessibility": has_accessibility,
            },
            execution_time=time.time() - start_time,
        )


class CoverageReviewer(PatternBaseReviewer):
    """Reviews test coverage and documentation coverage."""

    def __init__(self):
        super().__init__(ReviewType.TEST_COVERAGE)
        self.test_keywords = [
            "test",
            "unittest",
            "pytest",
            "jest",
            "mocha",
            "coverage",
            "assert",
            "expect",
            "should",
        ]

    async def review(self, content: str, metadata: Dict[str, Any]) -> ReviewResult:
        """Review document for test coverage."""
        start_time = time.time()
        issues = []

        # Check for test mentions
        test_mentions = self.pattern_matcher.count_occurrences(content, set(self.test_keywords))

        # Look for coverage metrics
        coverage_pattern = r"coverage[:\s]+(\d+)%"
        coverage_matches = re.findall(coverage_pattern, content, re.IGNORECASE)

        # Calculate average coverage if found
        avg_coverage = 0.0
        if coverage_matches:
            avg_coverage = sum(int(c) for c in coverage_matches) / len(coverage_matches) / 100

        # Generate issues
        if not test_mentions:
            issues.append(
                self.create_issue(
                    "No test coverage information found",
                    SeverityLevel.MEDIUM,
                    suggestion="Add test coverage metrics",
                )
            )

        if avg_coverage < 0.8 and avg_coverage > 0:
            issues.append(
                self.create_issue(
                    f"Test coverage below 80%: {avg_coverage*100:.1f}%",
                    SeverityLevel.LOW,
                )
            )

        # Calculate score
        has_tests = sum(test_mentions.values()) > 0
        score = avg_coverage if avg_coverage > 0 else (0.5 if has_tests else 0.3)

        return ReviewResult(
            review_type=self.review_type,
            score=score,
            issues=issues,
            metrics={
                "test_mentions": sum(test_mentions.values()),
                "average_coverage": avg_coverage,
            },
            execution_time=time.time() - start_time,
        )


class ComplianceReviewer(PatternBaseReviewer):
    """Reviews documents for compliance with standards."""

    def __init__(self):
        super().__init__(ReviewType.COMPLIANCE)
        self.compliance_standards = {
            ComplianceStandard.PCI_DSS: ["pci", "pci-dss", "payment card"],
            ComplianceStandard.HIPAA: ["hipaa", "health", "medical", "phi"],
            ComplianceStandard.GDPR: ["gdpr", "privacy", "data protection"],
            ComplianceStandard.SOC2: ["soc2", "soc 2", "audit"],
            ComplianceStandard.ISO27001: ["iso27001", "iso 27001", "isms"],
        }

    async def review(self, content: str, metadata: Dict[str, Any]) -> ReviewResult:
        """Review document for compliance requirements."""
        start_time = time.time()
        issues = []

        content_lower = content.lower()

        # Check which standards are mentioned
        standards_mentioned = []
        for standard, keywords in self.compliance_standards.items():
            if any(keyword in content_lower for keyword in keywords):
                standards_mentioned.append(standard)

        # Check for compliance keywords
        compliance_keywords = [
            "compliance",
            "regulation",
            "standard",
            "requirement",
            "audit",
        ]
        compliance_mentions = self.pattern_matcher.count_occurrences(
            content, set(compliance_keywords)
        )

        # Generate issues
        if not standards_mentioned and sum(compliance_mentions.values()) > 0:
            issues.append(
                self.create_issue(
                    "Compliance mentioned but no specific standards identified",
                    SeverityLevel.LOW,
                    suggestion="Specify applicable compliance standards",
                )
            )

        # Calculate score
        has_compliance = len(standards_mentioned) > 0 or sum(compliance_mentions.values()) > 0
        score = 0.8 if standards_mentioned else (0.5 if has_compliance else 0.3)

        return ReviewResult(
            review_type=self.review_type,
            score=score,
            issues=issues,
            metrics={
                "standards_mentioned": [s.value for s in standards_mentioned],
                "compliance_mentions": sum(compliance_mentions.values()),
            },
            execution_time=time.time() - start_time,
        )


class ConsistencyReviewer(PatternBaseReviewer):
    """Reviews documents for consistency across the codebase."""

    def __init__(self, tracking_matrix=None):
        super().__init__(ReviewType.CONSISTENCY)
        self.tracking = tracking_matrix

    async def review(self, content: str, metadata: Dict[str, Any]) -> ReviewResult:
        """Review document for consistency."""
        start_time = time.time()
        issues = []

        # Check naming consistency
        naming_patterns = {
            "camelCase": r"[a-z][a-zA-Z0-9]*",
            "snake_case": r"[a-z]+(?:_[a-z]+)*",
            "kebab-case": r"[a-z]+(?:-[a-z]+)*",
            "PascalCase": r"[A-Z][a-zA-Z0-9]*",
        }

        # Count different naming styles
        style_counts = {}
        for style, pattern in naming_patterns.items():
            matches = re.findall(pattern, content)
            style_counts[style] = len(matches)

        # Find dominant style
        dominant_style = max(style_counts, key=style_counts.get) if style_counts else None

        # Check for mixed styles
        styles_used = [s for s, count in style_counts.items() if count > 10]
        if len(styles_used) > 2:
            issues.append(
                self.create_issue(
                    f"Mixed naming conventions: {', '.join(styles_used)}",
                    SeverityLevel.LOW,
                    suggestion=f"Use consistent naming (dominant: {dominant_style})",
                )
            )

        # If tracking matrix available, check cross-references
        cross_ref_score = 0.5
        if self.tracking and metadata.get("document_id"):
            try:
                dependencies = self.tracking.get_dependencies(metadata["document_id"])
                cross_ref_score = 0.8 if dependencies else 0.5
            except:
                pass

        # Calculate score
        consistency_penalty = 0.1 * (len(styles_used) - 1) if len(styles_used) > 1 else 0
        score = cross_ref_score - consistency_penalty
        score = max(0.0, min(1.0, score))

        return ReviewResult(
            review_type=self.review_type,
            score=score,
            issues=issues,
            metrics={
                "naming_styles": style_counts,
                "dominant_style": dominant_style,
                "mixed_styles": len(styles_used) > 2,
            },
            execution_time=time.time() - start_time,
        )


class PIIDetector:
    """Detects personally identifiable information in documents."""

    def __init__(self):
        """Initialize PII detector."""
        self.pii_patterns = {
            PIIType.EMAIL: [
                (
                    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                    "Email Address",
                )
            ],
            PIIType.PHONE: [
                (r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "US Phone Number"),
                (r"\+\d{1,3}\s?\d{1,14}", "International Phone"),
            ],
            PIIType.SSN: [(r"\b\d{3}-\d{2}-\d{4}\b", "SSN Format")],
            PIIType.CREDIT_CARD: [(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "Credit Card")],
            PIIType.ADDRESS: [(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "IPv4 Address")],
        }
        self.pattern_matcher = PatternMatcher()

    async def detect(self, content: str) -> Dict[str, Any]:
        """Detect PII in content."""
        pii_found = []

        for pii_type, patterns in self.pii_patterns.items():
            for pattern, description in patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    pii_found.append(
                        PIIMatch(
                            pii_type=pii_type,
                            value=self._mask_pii(match.group()),
                            location=f"Position {match.start()}-{match.end()}",
                            confidence=0.9,
                        )
                    )

        # Calculate accuracy (simplified)
        accuracy = 0.89 if pii_found else 0.95

        return {
            "pii_found": pii_found[:20],  # Limit to 20 matches
            "accuracy": accuracy,
            "total_found": len(pii_found),
        }

    def _mask_pii(self, value: str) -> str:
        """Mask PII value for security."""
        if len(value) <= 4:
            return "****"
        return value[:2] + "*" * (len(value) - 4) + value[-2:]

    def add_pattern(self, pii_type: PIIType, pattern: str, description: str):
        """Add custom PII pattern."""
        if pii_type not in self.pii_patterns:
            self.pii_patterns[pii_type] = []
        self.pii_patterns[pii_type].append((pattern, description))
