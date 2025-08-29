"""
Optimized quality dimension analyzers for M005 Quality Engine - Performance Pass 2.

Implements performance-optimized analyzers for each quality dimension:
- Completeness: Content coverage and missing elements
- Clarity: Readability and understandability
- Structure: Organization and hierarchy
- Accuracy: Technical correctness and consistency
- Formatting: Style and presentation
"""

import re
from typing import List, Dict, Any, Optional, Set, Tuple
from functools import lru_cache
from collections import Counter
import math

from .models import DimensionScore, QualityDimension, QualityIssue, SeverityLevel


# ============================================================================
# Optimized Pattern Cache
# ============================================================================

class PatternCache:
    """Centralized pattern cache for dimension analyzers."""
    
    # Pre-compiled patterns for all dimensions
    PATTERNS = {
        # Structure patterns
        'headers': re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE),
        'code_blocks': re.compile(r'```[\s\S]*?```'),
        'lists': re.compile(r'^\s*[-*+]\s+', re.MULTILINE),
        'numbered_lists': re.compile(r'^\s*\d+\.\s+', re.MULTILINE),
        'links': re.compile(r'\[([^\]]+)\]\(([^)]+)\)'),
        'images': re.compile(r'!\[([^\]]*)\]\(([^)]+)\)'),
        'tables': re.compile(r'\|[^\n]+\|'),
        
        # Content patterns
        'paragraphs': re.compile(r'\n\n+'),
        'sentences': re.compile(r'[.!?]+'),
        'words': re.compile(r'\b\w+\b'),
        'technical_terms': re.compile(r'\b[A-Z][a-z]+[A-Z]\w*\b|\b[A-Z]{2,}\b'),
        
        # Quality patterns
        'todo_markers': re.compile(r'\b(TODO|FIXME|XXX|HACK)\b', re.IGNORECASE),
        'placeholder_text': re.compile(r'lorem ipsum|placeholder|tbd|coming soon', re.IGNORECASE),
        'broken_links': re.compile(r'\[([^\]]+)\]\(\s*\)'),
        'empty_sections': re.compile(r'^#{1,6}\s+.+\n+(?=^#{1,6}\s+|\Z)', re.MULTILINE),
        
        # Formatting patterns
        'whitespace_issues': re.compile(r'[ \t]+$', re.MULTILINE),
        'multiple_blanks': re.compile(r'\n{3,}'),
        'inconsistent_bullets': re.compile(r'^(\s*)[-*+]\s+', re.MULTILINE),
    }
    
    @classmethod
    def findall(cls, pattern_name: str, text: str) -> List:
        """Find all matches using cached pattern."""
        if pattern_name in cls.PATTERNS:
            return cls.PATTERNS[pattern_name].findall(text)
        return []
    
    @classmethod
    def search(cls, pattern_name: str, text: str) -> Optional[re.Match]:
        """Search using cached pattern."""
        if pattern_name in cls.PATTERNS:
            return cls.PATTERNS[pattern_name].search(text)
        return None
    
    @classmethod
    def count(cls, pattern_name: str, text: str) -> int:
        """Count matches using cached pattern."""
        if pattern_name in cls.PATTERNS:
            return len(cls.PATTERNS[pattern_name].findall(text))
        return 0


# ============================================================================
# Base Optimized Analyzer
# ============================================================================

class OptimizedDimensionAnalyzer:
    """Base class for optimized dimension analyzers."""
    
    def __init__(self, dimension: QualityDimension):
        """Initialize analyzer with dimension."""
        self.dimension = dimension
        self.pattern_cache = PatternCache()
    
    @lru_cache(maxsize=128)
    def _calculate_word_stats(self, text: str) -> Tuple[int, int, int]:
        """Calculate word, sentence, and paragraph counts with caching."""
        words = self.pattern_cache.count('words', text)
        sentences = self.pattern_cache.count('sentences', text)
        paragraphs = self.pattern_cache.count('paragraphs', text) + 1
        return words, sentences, paragraphs
    
    def analyze(self, content: str) -> DimensionScore:
        """Analyze content for this dimension."""
        raise NotImplementedError


# ============================================================================
# Optimized Completeness Analyzer
# ============================================================================

class OptimizedCompletenessAnalyzer(OptimizedDimensionAnalyzer):
    """Optimized analyzer for content completeness."""
    
    def __init__(self):
        """Initialize completeness analyzer."""
        super().__init__(QualityDimension.COMPLETENESS)
        self.min_word_count = 100
        self.required_sections = {'introduction', 'conclusion', 'summary'}
    
    def analyze(self, content: str) -> DimensionScore:
        """Analyze document completeness with optimizations."""
        issues = []
        score = 100.0
        
        # Quick length check
        word_count, _, _ = self._calculate_word_stats(content)
        
        if word_count < self.min_word_count:
            score -= 30
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity=SeverityLevel.HIGH,
                description=f"Document too short ({word_count} words)",
                suggestion=f"Add more content (minimum {self.min_word_count} words)",
                impact_score=8.0
            ))
        
        # Check for headers (fast pattern matching)
        headers = self.pattern_cache.findall('headers', content)
        if len(headers) < 2:
            score -= 20
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity=SeverityLevel.MEDIUM,
                description="Missing document structure",
                suggestion="Add headers to organize content",
                impact_score=5.0
            ))
        
        # Check for TODOs and placeholders (optimized)
        todos = self.pattern_cache.count('todo_markers', content)
        placeholders = self.pattern_cache.count('placeholder_text', content)
        
        if todos > 0:
            score -= todos * 5
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity=SeverityLevel.MEDIUM,
                description=f"Found {todos} TODO markers",
                suggestion="Complete all TODO items",
                impact_score=4.0
            ))
        
        if placeholders > 0:
            score -= 15
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity=SeverityLevel.HIGH,
                description="Contains placeholder text",
                suggestion="Replace placeholder text with actual content",
                impact_score=7.0
            ))
        
        # Check for empty sections (optimized regex)
        empty_sections = self._find_empty_sections_optimized(content)
        if empty_sections:
            score -= len(empty_sections) * 10
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity=SeverityLevel.MEDIUM,
                description=f"Found {len(empty_sections)} empty sections",
                suggestion="Add content to empty sections",
                impact_score=5.0
            ))
        
        # Check for code examples if technical document
        if self._is_technical_document(content):
            code_blocks = self.pattern_cache.count('code_blocks', content)
            if code_blocks == 0:
                score -= 10
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity=SeverityLevel.LOW,
                    description="No code examples in technical document",
                    suggestion="Add code examples to illustrate concepts",
                    impact_score=3.0
                ))
        
        return DimensionScore(
            dimension=self.dimension,
            score=max(0.0, min(100.0, score)),
            weight=0.25,
            issues=issues
        )
    
    @lru_cache(maxsize=32)
    def _find_empty_sections_optimized(self, content: str) -> List[str]:
        """Find empty sections using optimized pattern matching."""
        empty = []
        headers = self.pattern_cache.findall('headers', content)
        
        for i, (level, title) in enumerate(headers[:-1]):
            # Get content between this header and next
            start_idx = content.find(f"{level} {title}")
            if i + 1 < len(headers):
                end_idx = content.find(f"{headers[i+1][0]} {headers[i+1][1]}")
            else:
                end_idx = len(content)
            
            section_content = content[start_idx:end_idx]
            # Remove header line and check if empty
            section_body = section_content.split('\n', 1)[1] if '\n' in section_content else ''
            
            if len(section_body.strip()) < 20:
                empty.append(title)
        
        return empty
    
    @lru_cache(maxsize=32)
    def _is_technical_document(self, content: str) -> bool:
        """Detect if document is technical based on content."""
        tech_indicators = [
            'function', 'class', 'method', 'api', 'algorithm',
            'implementation', 'architecture', 'database', 'framework'
        ]
        content_lower = content.lower()
        return sum(1 for term in tech_indicators if term in content_lower) >= 3


# ============================================================================
# Optimized Clarity Analyzer
# ============================================================================

class OptimizedClarityAnalyzer(OptimizedDimensionAnalyzer):
    """Optimized analyzer for content clarity and readability."""
    
    def __init__(self):
        """Initialize clarity analyzer."""
        super().__init__(QualityDimension.CLARITY)
        self.max_sentence_length = 30
        self.complex_word_threshold = 0.15
    
    def analyze(self, content: str) -> DimensionScore:
        """Analyze document clarity with optimizations."""
        issues = []
        score = 100.0
        
        # Get basic stats
        words, sentences, _ = self._calculate_word_stats(content)
        
        if sentences == 0:
            return DimensionScore(
                dimension=self.dimension,
                score=50.0,
                weight=0.20,
                issues=[QualityIssue(
                    dimension=self.dimension,
                    severity=SeverityLevel.HIGH,
                    description="No sentences found",
                    impact_score=8.0
                )]
            )
        
        # Calculate readability metrics (optimized)
        avg_sentence_length = words / sentences
        
        if avg_sentence_length > self.max_sentence_length:
            score -= 20
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity=SeverityLevel.MEDIUM,
                description=f"Long sentences (avg: {avg_sentence_length:.1f} words)",
                suggestion="Break long sentences into shorter ones",
                impact_score=5.0
            ))
        
        # Check for passive voice (simplified check)
        passive_indicators = self._count_passive_voice_optimized(content)
        if passive_indicators > sentences * 0.3:
            score -= 15
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity=SeverityLevel.LOW,
                description="Excessive passive voice usage",
                suggestion="Use more active voice",
                impact_score=3.0
            ))
        
        # Check for jargon and complex terms (optimized)
        complex_ratio = self._calculate_complex_word_ratio_optimized(content)
        if complex_ratio > self.complex_word_threshold:
            score -= 15
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity=SeverityLevel.MEDIUM,
                description=f"High complexity ({complex_ratio:.1%} complex words)",
                suggestion="Simplify language and explain technical terms",
                impact_score=4.0
            ))
        
        # Check for unclear pronouns
        unclear_pronouns = self._check_unclear_pronouns_optimized(content)
        if unclear_pronouns > 5:
            score -= 10
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity=SeverityLevel.LOW,
                description="Unclear pronoun references",
                suggestion="Replace pronouns with specific nouns where unclear",
                impact_score=2.0
            ))
        
        return DimensionScore(
            dimension=self.dimension,
            score=max(0.0, min(100.0, score)),
            weight=0.20,
            issues=issues
        )
    
    @lru_cache(maxsize=32)
    def _count_passive_voice_optimized(self, text: str) -> int:
        """Count passive voice occurrences (simplified)."""
        # Simplified passive voice detection
        passive_patterns = [
            r'\b(was|were|been|being|is|are|am)\s+\w+ed\b',
            r'\b(was|were|been|being|is|are|am)\s+\w+en\b',
        ]
        count = 0
        for pattern in passive_patterns:
            count += len(re.findall(pattern, text, re.IGNORECASE))
        return count
    
    @lru_cache(maxsize=32)
    def _calculate_complex_word_ratio_optimized(self, text: str) -> float:
        """Calculate ratio of complex words (optimized)."""
        words = self.pattern_cache.findall('words', text)
        if not words:
            return 0.0
        
        # Simple heuristic: words > 3 syllables or > 10 characters
        complex_count = sum(1 for word in words if len(word) > 10)
        return complex_count / len(words)
    
    @lru_cache(maxsize=32)
    def _check_unclear_pronouns_optimized(self, text: str) -> int:
        """Check for unclear pronoun usage (optimized)."""
        pronouns = ['it', 'this', 'that', 'these', 'those', 'they']
        count = 0
        sentences = text.split('.')
        
        for sentence in sentences[:20]:  # Check first 20 sentences for performance
            sentence_lower = sentence.lower()
            # Check if sentence starts with pronoun
            for pronoun in pronouns:
                if sentence_lower.strip().startswith(pronoun + ' '):
                    count += 1
                    break
        
        return count


# ============================================================================
# Optimized Structure Analyzer
# ============================================================================

class OptimizedStructureAnalyzer(OptimizedDimensionAnalyzer):
    """Optimized analyzer for document structure and organization."""
    
    def __init__(self):
        """Initialize structure analyzer."""
        super().__init__(QualityDimension.STRUCTURE)
        self.min_sections = 2
        self.max_heading_depth = 4
    
    def analyze(self, content: str) -> DimensionScore:
        """Analyze document structure with optimizations."""
        issues = []
        score = 100.0
        
        # Check headers hierarchy (optimized)
        headers = self.pattern_cache.findall('headers', content)
        
        if len(headers) < self.min_sections:
            score -= 25
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity=SeverityLevel.HIGH,
                description=f"Insufficient structure ({len(headers)} sections)",
                suggestion=f"Add at least {self.min_sections} sections",
                impact_score=7.0
            ))
        
        # Check hierarchy consistency (optimized)
        hierarchy_issues = self._check_hierarchy_optimized(headers)
        if hierarchy_issues:
            score -= len(hierarchy_issues) * 10
            for issue in hierarchy_issues[:2]:  # Limit issues
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity=SeverityLevel.MEDIUM,
                    description=issue,
                    suggestion="Fix heading hierarchy",
                    impact_score=4.0
                ))
        
        # Check for lists and organization
        lists = self.pattern_cache.count('lists', content)
        numbered = self.pattern_cache.count('numbered_lists', content)
        
        if lists + numbered == 0 and len(content) > 1000:
            score -= 10
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity=SeverityLevel.LOW,
                description="No lists found",
                suggestion="Use lists to organize information",
                impact_score=2.0
            ))
        
        # Check for code organization in technical docs
        code_blocks = self.pattern_cache.findall('code_blocks', content)
        if code_blocks:
            unformatted = self._check_code_formatting_optimized(code_blocks)
            if unformatted > 0:
                score -= unformatted * 5
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity=SeverityLevel.LOW,
                    description=f"{unformatted} code blocks lack language specification",
                    suggestion="Add language identifiers to code blocks",
                    impact_score=2.0
                ))
        
        # Check for navigation elements
        has_toc = self._has_table_of_contents_optimized(content)
        if len(headers) > 5 and not has_toc:
            score -= 10
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity=SeverityLevel.LOW,
                description="Missing table of contents",
                suggestion="Add a table of contents for better navigation",
                impact_score=3.0
            ))
        
        return DimensionScore(
            dimension=self.dimension,
            score=max(0.0, min(100.0, score)),
            weight=0.20,
            issues=issues
        )
    
    @lru_cache(maxsize=32)
    def _check_hierarchy_optimized(self, headers: List[Tuple[str, str]]) -> List[str]:
        """Check heading hierarchy for issues (optimized)."""
        issues = []
        
        if not headers:
            return issues
        
        # Check if document starts with H1
        if headers[0][0] != '#':
            issues.append("Document should start with H1 (#)")
        
        # Check for skipped levels (simplified)
        prev_level = 0
        for level_str, _ in headers:
            level = len(level_str)
            if level > prev_level + 1 and prev_level > 0:
                issues.append(f"Skipped heading level: H{prev_level} to H{level}")
            prev_level = level
        
        return issues[:3]  # Limit issues
    
    def _check_code_formatting_optimized(self, code_blocks: List[str]) -> int:
        """Check code block formatting (optimized)."""
        unformatted = 0
        for block in code_blocks[:10]:  # Check first 10 for performance
            # Check if language is specified
            if block.startswith('```\n') or block.startswith('``` \n'):
                unformatted += 1
        return unformatted
    
    @lru_cache(maxsize=32)
    def _has_table_of_contents_optimized(self, content: str) -> bool:
        """Check for table of contents (optimized)."""
        toc_indicators = [
            'table of contents', 'contents', 'toc', '## contents',
            '## table of contents', '# table of contents'
        ]
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in toc_indicators)


# ============================================================================
# Optimized Accuracy Analyzer
# ============================================================================

class OptimizedAccuracyAnalyzer(OptimizedDimensionAnalyzer):
    """Optimized analyzer for technical accuracy and consistency."""
    
    def __init__(self):
        """Initialize accuracy analyzer."""
        super().__init__(QualityDimension.ACCURACY)
    
    def analyze(self, content: str) -> DimensionScore:
        """Analyze document accuracy with optimizations."""
        issues = []
        score = 100.0
        
        # Check for broken links (optimized)
        broken_links = self.pattern_cache.findall('broken_links', content)
        if broken_links:
            score -= len(broken_links) * 5
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity=SeverityLevel.MEDIUM,
                description=f"Found {len(broken_links)} broken links",
                suggestion="Fix or remove broken links",
                impact_score=5.0
            ))
        
        # Check for consistency in terminology (optimized)
        inconsistencies = self._check_terminology_consistency_optimized(content)
        if inconsistencies:
            score -= len(inconsistencies) * 3
            for term_pair in inconsistencies[:2]:
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity=SeverityLevel.LOW,
                    description=f"Inconsistent terminology: {term_pair[0]} vs {term_pair[1]}",
                    suggestion="Use consistent terminology throughout",
                    impact_score=2.0
                ))
        
        # Check for factual markers (simplified)
        uncertain_statements = self._check_uncertain_statements_optimized(content)
        if uncertain_statements > 3:
            score -= 10
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity=SeverityLevel.MEDIUM,
                description="Multiple uncertain statements found",
                suggestion="Verify and clarify uncertain information",
                impact_score=4.0
            ))
        
        # Check code snippets for basic syntax (if present)
        code_blocks = self.pattern_cache.findall('code_blocks', content)
        if code_blocks:
            syntax_errors = self._check_code_syntax_optimized(code_blocks)
            if syntax_errors:
                score -= syntax_errors * 10
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity=SeverityLevel.HIGH,
                    description=f"Found {syntax_errors} potential syntax errors",
                    suggestion="Review and fix code syntax",
                    impact_score=7.0
                ))
        
        return DimensionScore(
            dimension=self.dimension,
            score=max(0.0, min(100.0, score)),
            weight=0.25,
            issues=issues
        )
    
    @lru_cache(maxsize=32)
    def _check_terminology_consistency_optimized(self, text: str) -> List[Tuple[str, str]]:
        """Check for terminology consistency (optimized)."""
        inconsistencies = []
        
        # Common inconsistencies to check (limited set for performance)
        term_variants = [
            ('filename', 'file name'),
            ('backend', 'back-end'),
            ('frontend', 'front-end'),
            ('dataset', 'data set'),
            ('email', 'e-mail'),
        ]
        
        text_lower = text.lower()
        for term1, term2 in term_variants:
            if term1 in text_lower and term2 in text_lower:
                inconsistencies.append((term1, term2))
        
        return inconsistencies[:3]  # Limit results
    
    @lru_cache(maxsize=32)
    def _check_uncertain_statements_optimized(self, text: str) -> int:
        """Check for uncertain statements (optimized)."""
        uncertainty_markers = [
            'might be', 'could be', 'possibly', 'maybe',
            'probably', 'likely', 'perhaps', 'allegedly'
        ]
        
        count = 0
        text_lower = text.lower()
        for marker in uncertainty_markers:
            count += text_lower.count(marker)
        
        return count
    
    def _check_code_syntax_optimized(self, code_blocks: List[str]) -> int:
        """Basic syntax checking for code blocks (optimized)."""
        errors = 0
        
        for block in code_blocks[:5]:  # Check first 5 blocks for performance
            # Basic checks only
            lines = block.split('\n')[1:-1]  # Skip ``` markers
            
            for line in lines[:20]:  # Check first 20 lines
                # Check for unclosed brackets/parens (simplified)
                if line.count('(') != line.count(')'):
                    errors += 1
                    break
                if line.count('[') != line.count(']'):
                    errors += 1
                    break
                if line.count('{') != line.count('}'):
                    errors += 1
                    break
        
        return min(errors, 3)  # Cap errors


# ============================================================================
# Optimized Formatting Analyzer
# ============================================================================

class OptimizedFormattingAnalyzer(OptimizedDimensionAnalyzer):
    """Optimized analyzer for document formatting and style."""
    
    def __init__(self):
        """Initialize formatting analyzer."""
        super().__init__(QualityDimension.FORMATTING)
    
    def analyze(self, content: str) -> DimensionScore:
        """Analyze document formatting with optimizations."""
        issues = []
        score = 100.0
        
        # Check for whitespace issues (optimized)
        trailing_spaces = self.pattern_cache.count('whitespace_issues', content)
        if trailing_spaces > 0:
            score -= min(15, trailing_spaces * 2)
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity=SeverityLevel.LOW,
                description=f"Found {trailing_spaces} lines with trailing whitespace",
                suggestion="Remove trailing whitespace",
                impact_score=2.0
            ))
        
        # Check for multiple blank lines
        multiple_blanks = self.pattern_cache.count('multiple_blanks', content)
        if multiple_blanks > 0:
            score -= min(10, multiple_blanks * 3)
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity=SeverityLevel.LOW,
                description="Multiple consecutive blank lines found",
                suggestion="Use single blank lines between sections",
                impact_score=1.0
            ))
        
        # Check line length (sampling for performance)
        long_lines = self._check_line_length_optimized(content)
        if long_lines > 0:
            score -= min(10, long_lines)
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity=SeverityLevel.LOW,
                description=f"Found {long_lines} lines exceeding 120 characters",
                suggestion="Break long lines for better readability",
                impact_score=2.0
            ))
        
        # Check list formatting consistency
        inconsistent_lists = self._check_list_consistency_optimized(content)
        if inconsistent_lists:
            score -= 10
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity=SeverityLevel.LOW,
                description="Inconsistent list formatting",
                suggestion="Use consistent bullet style throughout",
                impact_score=2.0
            ))
        
        # Check markdown formatting
        formatting_errors = self._check_markdown_formatting_optimized(content)
        if formatting_errors:
            score -= len(formatting_errors) * 5
            for error in formatting_errors[:2]:
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity=SeverityLevel.LOW,
                    description=error,
                    suggestion="Fix markdown formatting",
                    impact_score=2.0
                ))
        
        return DimensionScore(
            dimension=self.dimension,
            score=max(0.0, min(100.0, score)),
            weight=0.10,
            issues=issues
        )
    
    @lru_cache(maxsize=32)
    def _check_line_length_optimized(self, text: str) -> int:
        """Check for long lines (optimized with sampling)."""
        lines = text.split('\n')
        
        # Sample lines for performance (check every 10th line)
        sample_size = max(1, len(lines) // 10)
        sampled_lines = lines[::10] if len(lines) > 100 else lines
        
        long_lines = sum(1 for line in sampled_lines if len(line) > 120)
        
        # Extrapolate to full document
        if len(lines) > 100:
            long_lines = long_lines * 10
        
        return long_lines
    
    @lru_cache(maxsize=32)
    def _check_list_consistency_optimized(self, text: str) -> bool:
        """Check list formatting consistency (optimized)."""
        bullets = self.pattern_cache.findall('inconsistent_bullets', text)
        
        if not bullets:
            return False
        
        # Check if mixed bullet styles
        bullet_types = set()
        for indent, bullet in bullets[:20]:  # Check first 20 items
            bullet_types.add(bullet.strip())
        
        return len(bullet_types) > 1
    
    @lru_cache(maxsize=32)
    def _check_markdown_formatting_optimized(self, text: str) -> List[str]:
        """Check markdown formatting issues (optimized)."""
        errors = []
        
        # Check for missing spaces after headers (sampling)
        lines = text.split('\n')
        for line in lines[:50]:  # Check first 50 lines
            if line.startswith('#') and not line.startswith('# '):
                if not re.match(r'^#{1,6}\s', line):
                    errors.append("Missing space after header marker")
                    break
        
        # Check for unescaped special characters (limited check)
        special_chars = ['*', '_', '[', ']']
        for char in special_chars:
            # Simple check for isolated special characters
            if f' {char} ' in text:
                errors.append(f"Potentially unescaped '{char}' character")
                break
        
        return errors[:3]  # Limit errors