"""
M007 Review Engine - Common Review Patterns
DevDocAI v3.0.0

Extracted common patterns from reviewers for code reuse.
Provides base classes and utilities for all reviewers.
"""

import asyncio
import logging
import re
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import Any, Dict, List, Optional, Pattern, Set

from .review_types import ReviewResult, ReviewType, SeverityLevel

logger = logging.getLogger(__name__)


class PatternMatcher:
    """Utility class for pattern matching operations."""

    def __init__(self):
        """Initialize pattern matcher."""
        self._pattern_cache = {}
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="pattern")

    @lru_cache(maxsize=128)
    def compile_pattern(self, pattern: str, flags: int = 0) -> Pattern:
        """Compile and cache regex patterns for performance."""
        return re.compile(pattern, flags)

    def find_patterns(
        self, content: str, patterns: List[str], flags: int = 0
    ) -> List[Dict[str, Any]]:
        """Find all occurrences of patterns in content."""
        matches = []
        for pattern_str in patterns:
            pattern = self.compile_pattern(pattern_str, flags)
            for match in pattern.finditer(content):
                matches.append(
                    {
                        "pattern": pattern_str,
                        "match": match.group(),
                        "start": match.start(),
                        "end": match.end(),
                        "line": content[: match.start()].count("\n") + 1,
                    }
                )
        return matches

    def count_occurrences(self, content: str, keywords: Set[str]) -> Dict[str, int]:
        """Count occurrences of keywords in content."""
        counts = {}
        content_lower = content.lower()
        for keyword in keywords:
            counts[keyword] = content_lower.count(keyword.lower())
        return counts

    async def process_chunks(
        self, content: str, processor_func, chunk_size: int = 10000
    ) -> List[Any]:
        """Process document in chunks for better performance."""
        chunks = self._create_chunks(content, chunk_size)

        loop = asyncio.get_event_loop()
        tasks = []
        for chunk in chunks:
            task = loop.run_in_executor(self._executor, processor_func, chunk)
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        # Flatten results
        return [item for sublist in results for item in sublist]

    def _create_chunks(self, content: str, chunk_size: int) -> List[str]:
        """Create content chunks preserving sentence boundaries."""
        if len(content) <= chunk_size:
            return [content]

        chunks = []
        current_chunk = ""
        sentences = content.split(". ")

        for sentence in sentences:
            if len(current_chunk) + len(sentence) > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence
            else:
                current_chunk += sentence + ". "

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def shutdown(self):
        """Shutdown the executor."""
        self._executor.shutdown(wait=True)


class BaseReviewer(ABC):
    """Enhanced base class for all document reviewers."""

    def __init__(self, review_type: ReviewType):
        """Initialize base reviewer."""
        self.review_type = review_type
        self.metrics = {}
        self.pattern_matcher = PatternMatcher()

    @abstractmethod
    async def review(self, content: str, metadata: Dict[str, Any]) -> ReviewResult:
        """Perform document review."""
        pass

    def calculate_score(self, positive_signals: int, total_signals: int) -> float:
        """Calculate a normalized score."""
        if total_signals == 0:
            return 0.5  # Neutral score when no signals
        return min(1.0, positive_signals / total_signals)

    def create_issue(
        self,
        description: str,
        severity: SeverityLevel,
        location: Optional[str] = None,
        suggestion: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a standardized issue."""
        issue = {
            "description": description,
            "severity": severity,
            "review_type": self.review_type.value,
        }

        if location:
            issue["location"] = location
        if suggestion:
            issue["suggestion"] = suggestion

        return issue

    def analyze_structure(self, content: str) -> Dict[str, Any]:
        """Analyze document structure."""
        lines = content.split("\n")

        return {
            "total_lines": len(lines),
            "blank_lines": sum(1 for line in lines if not line.strip()),
            "code_lines": sum(
                1 for line in lines if line.strip() and not line.strip().startswith("#")
            ),
            "comment_lines": sum(1 for line in lines if line.strip().startswith("#")),
            "sections": self._identify_sections(content),
            "avg_line_length": (sum(len(line) for line in lines) / len(lines) if lines else 0),
        }

    def _identify_sections(self, content: str) -> List[str]:
        """Identify major sections in document."""
        section_patterns = [
            r"^#{1,6}\s+(.+)$",  # Markdown headers
            r"^class\s+(\w+)",  # Python classes
            r"^def\s+(\w+)",  # Python functions
            r"^function\s+(\w+)",  # JavaScript functions
            r"^\/\*\*\s*\n\s*\*\s+(.+)",  # JSDoc comments
        ]

        sections = []
        for pattern_str in section_patterns:
            pattern = self.pattern_matcher.compile_pattern(pattern_str, re.MULTILINE)
            for match in pattern.finditer(content):
                sections.append(match.group(1))

        return sections

    def shutdown(self):
        """Cleanup resources."""
        self.pattern_matcher.shutdown()


class QualityReviewer(BaseReviewer):
    """Base class for quality-focused reviewers."""

    def __init__(self, review_type: ReviewType):
        """Initialize quality reviewer."""
        super().__init__(review_type)
        self.quality_metrics = {
            "readability": 0.0,
            "maintainability": 0.0,
            "complexity": 0.0,
            "documentation": 0.0,
        }

    def assess_readability(self, content: str) -> float:
        """Assess document readability."""
        structure = self.analyze_structure(content)

        # Factors that improve readability
        positive_factors = 0
        total_factors = 5

        # Good comment ratio
        if structure["comment_lines"] > 0:
            comment_ratio = structure["comment_lines"] / max(structure["total_lines"], 1)
            if 0.1 <= comment_ratio <= 0.3:
                positive_factors += 1

        # Reasonable line length
        if structure["avg_line_length"] <= 80:
            positive_factors += 1

        # Has sections/structure
        if len(structure["sections"]) > 0:
            positive_factors += 1

        # Good blank line usage
        blank_ratio = structure["blank_lines"] / max(structure["total_lines"], 1)
        if 0.1 <= blank_ratio <= 0.2:
            positive_factors += 1

        # Not too long
        if structure["total_lines"] <= 500:
            positive_factors += 1

        return positive_factors / total_factors

    def assess_complexity(self, content: str) -> float:
        """Assess document complexity."""
        # Look for complexity indicators
        complexity_patterns = [
            r"if\s+.*?:",
            r"elif\s+.*?:",
            r"else\s*:",
            r"for\s+.*?:",
            r"while\s+.*?:",
            r"try\s*:",
            r"except\s+.*?:",
        ]

        matches = self.pattern_matcher.find_patterns(content, complexity_patterns)
        complexity_count = len(matches)

        # Lower complexity is better
        if complexity_count < 10:
            return 1.0
        elif complexity_count < 20:
            return 0.8
        elif complexity_count < 30:
            return 0.6
        elif complexity_count < 50:
            return 0.4
        else:
            return 0.2


class SecurityReviewerBase(BaseReviewer):
    """Base class for security-focused reviewers."""

    def __init__(self, review_type: ReviewType):
        """Initialize security reviewer."""
        super().__init__(review_type)
        self.vulnerability_patterns = {}
        self.security_keywords = set()

    def scan_vulnerabilities(self, content: str) -> List[Dict[str, Any]]:
        """Scan for common security vulnerabilities."""
        vulnerabilities = []

        for vuln_type, patterns in self.vulnerability_patterns.items():
            matches = self.pattern_matcher.find_patterns(content, patterns, re.IGNORECASE)
            for match in matches:
                vulnerabilities.append(
                    {
                        "type": vuln_type,
                        "pattern": match["pattern"],
                        "location": f"Line {match['line']}",
                        "severity": self._determine_severity(vuln_type),
                    }
                )

        return vulnerabilities

    def _determine_severity(self, vuln_type: str) -> SeverityLevel:
        """Determine severity based on vulnerability type."""
        high_severity = {"sql_injection", "xss", "command_injection", "path_traversal"}
        medium_severity = {"weak_crypto", "hardcoded_secrets", "insecure_random"}

        if vuln_type in high_severity:
            return SeverityLevel.HIGH
        elif vuln_type in medium_severity:
            return SeverityLevel.MEDIUM
        else:
            return SeverityLevel.LOW
