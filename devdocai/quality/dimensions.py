"""
Quality dimension analyzers for M005 Quality Engine.

Implements specific analyzers for each quality dimension.
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Set
from collections import Counter
from datetime import datetime, timedelta

from .models import QualityDimension, QualityIssue, SeverityLevel, DimensionScore
from .scoring import ScoringMetrics
from .exceptions import DimensionAnalysisError

logger = logging.getLogger(__name__)


class DimensionAnalyzer:
    """Base class for dimension analyzers."""
    
    def __init__(self, dimension: QualityDimension):
        """Initialize analyzer for specific dimension."""
        self.dimension = dimension
    
    def analyze(self, content: str, metadata: Dict = None) -> DimensionScore:
        """
        Analyze content for this dimension.
        
        Args:
            content: Document content to analyze
            metadata: Optional metadata about the document
            
        Returns:
            DimensionScore with analysis results
        """
        raise NotImplementedError("Subclasses must implement analyze()")
    
    def extract_metrics(self, content: str) -> ScoringMetrics:
        """Extract basic metrics from content."""
        lines = content.split('\n')
        words = content.split()
        sentences = re.split(r'[.!?]+', content)
        
        metrics = ScoringMetrics(
            word_count=len(words),
            sentence_count=len([s for s in sentences if s.strip()]),
            paragraph_count=len([p for p in content.split('\n\n') if p.strip()]),
            code_block_count=content.count('```'),
            heading_count=len(re.findall(r'^#+\s', content, re.MULTILINE)),
            link_count=len(re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', content)),
            image_count=len(re.findall(r'!\[([^\]]*)\]\(([^\)]+)\)', content)),
            list_count=len(re.findall(r'^\s*[-*+]\s', content, re.MULTILINE)),
            table_count=len(re.findall(r'^\|.*\|$', content, re.MULTILINE)) // 3  # Rough estimate
        )
        
        # Calculate averages
        if metrics.sentence_count > 0:
            metrics.avg_sentence_length = metrics.word_count / metrics.sentence_count
        if metrics.paragraph_count > 0:
            metrics.avg_paragraph_length = metrics.word_count / metrics.paragraph_count
        
        # Technical density (ratio of code blocks to paragraphs)
        if metrics.paragraph_count > 0:
            metrics.technical_density = metrics.code_block_count / metrics.paragraph_count
        
        return metrics


class CompletenessAnalyzer(DimensionAnalyzer):
    """Analyzes document completeness."""
    
    def __init__(self):
        super().__init__(QualityDimension.COMPLETENESS)
        self.required_sections = {
            'readme': ['description', 'installation', 'usage', 'license'],
            'api': ['overview', 'authentication', 'endpoints', 'errors'],
            'tutorial': ['introduction', 'prerequisites', 'steps', 'conclusion'],
            'reference': ['overview', 'api', 'examples', 'see also']
        }
    
    def analyze(self, content: str, metadata: Dict = None) -> DimensionScore:
        """Analyze completeness of document."""
        try:
            metrics = self.extract_metrics(content)
            doc_type = metadata.get('document_type', 'readme') if metadata else 'readme'
            
            # Extract sections from content
            sections = self._extract_sections(content)
            required = self.required_sections.get(doc_type, [])
            
            score = 100.0
            issues = []
            
            # Check required sections
            missing = set(required) - set(s.lower() for s in sections)
            if missing:
                penalty = len(missing) * 15
                score -= penalty
                for section in missing:
                    issues.append(QualityIssue(
                        dimension=self.dimension,
                        severity=SeverityLevel.HIGH,
                        description=f"Missing required section: {section}",
                        suggestion=f"Add '{section}' section",
                        impact_score=7.0
                    ))
            
            # Check content depth
            if metrics.word_count < 100:
                score -= 25
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity=SeverityLevel.HIGH,
                    description="Document too short (< 100 words)",
                    suggestion="Expand content with more details",
                    impact_score=8.0
                ))
            elif metrics.word_count < 300:
                score -= 10
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity=SeverityLevel.MEDIUM,
                    description="Document could be more detailed",
                    suggestion="Add examples or more explanation",
                    impact_score=4.0
                ))
            
            # Check for examples
            has_examples = bool(re.search(r'(example|sample|demo)', content, re.IGNORECASE))
            has_code = metrics.code_block_count > 0
            
            if not has_examples and not has_code:
                score -= 15
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity=SeverityLevel.MEDIUM,
                    description="No examples found",
                    suggestion="Add practical examples",
                    impact_score=5.0
                ))
            
            return DimensionScore(
                dimension=self.dimension,
                score=max(0.0, score),
                issues=issues,
                metrics={'sections': sections, 'word_count': metrics.word_count}
            )
            
        except Exception as e:
            logger.error(f"Completeness analysis failed: {e}")
            raise DimensionAnalysisError(self.dimension.value, str(e))
    
    def _extract_sections(self, content: str) -> List[str]:
        """Extract section headings from content."""
        headings = re.findall(r'^#+\s+(.+)$', content, re.MULTILINE)
        return [h.strip() for h in headings]


class ClarityAnalyzer(DimensionAnalyzer):
    """Analyzes document clarity and readability."""
    
    def __init__(self):
        super().__init__(QualityDimension.CLARITY)
        self.jargon_terms = {
            'api', 'sdk', 'orm', 'crud', 'rest', 'graphql', 'jwt', 'oauth',
            'ci/cd', 'devops', 'kubernetes', 'docker', 'microservices',
            'async', 'sync', 'mutex', 'semaphore', 'thread', 'coroutine'
        }
    
    def analyze(self, content: str, metadata: Dict = None) -> DimensionScore:
        """Analyze clarity of document."""
        try:
            metrics = self.extract_metrics(content)
            
            score = 100.0
            issues = []
            
            # Analyze sentence complexity
            complex_sentences = self._count_complex_sentences(content)
            if metrics.sentence_count > 0:
                complexity_ratio = complex_sentences / metrics.sentence_count
                if complexity_ratio > 0.3:
                    score -= 20
                    issues.append(QualityIssue(
                        dimension=self.dimension,
                        severity=SeverityLevel.MEDIUM,
                        description=f"{int(complexity_ratio * 100)}% sentences are complex",
                        suggestion="Simplify sentence structure",
                        impact_score=6.0
                    ))
            
            # Check average sentence length
            if metrics.avg_sentence_length > 25:
                score -= 15
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity=SeverityLevel.MEDIUM,
                    description=f"Average sentence length is {metrics.avg_sentence_length:.1f} words",
                    suggestion="Use shorter sentences",
                    impact_score=5.0
                ))
            
            # Analyze jargon usage
            jargon_count = self._count_jargon(content)
            if metrics.word_count > 0:
                jargon_density = (jargon_count / metrics.word_count) * 100
                if jargon_density > 5:
                    score -= 15
                    issues.append(QualityIssue(
                        dimension=self.dimension,
                        severity=SeverityLevel.MEDIUM,
                        description=f"High technical jargon density ({jargon_density:.1f}%)",
                        suggestion="Define technical terms or add glossary",
                        impact_score=5.0
                    ))
            
            # Check for passive voice
            passive_count = self._count_passive_voice(content)
            if metrics.sentence_count > 0:
                passive_ratio = passive_count / metrics.sentence_count
                if passive_ratio > 0.2:
                    score -= 10
                    issues.append(QualityIssue(
                        dimension=self.dimension,
                        severity=SeverityLevel.LOW,
                        description="Excessive use of passive voice",
                        suggestion="Use active voice for clearer writing",
                        impact_score=3.0
                    ))
            
            # Calculate readability
            readability = self._calculate_readability(content)
            metrics.readability_score = readability
            
            if readability < 30:
                score -= 20
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity=SeverityLevel.HIGH,
                    description=f"Poor readability score ({readability:.1f})",
                    suggestion="Simplify language and structure",
                    impact_score=7.0
                ))
            elif readability < 50:
                score -= 10
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity=SeverityLevel.LOW,
                    description=f"Readability could be improved ({readability:.1f})",
                    suggestion="Consider simplifying complex sections",
                    impact_score=3.0
                ))
            
            return DimensionScore(
                dimension=self.dimension,
                score=max(0.0, score),
                issues=issues,
                metrics={
                    'readability': readability,
                    'jargon_count': jargon_count,
                    'complex_sentences': complex_sentences
                }
            )
            
        except Exception as e:
            logger.error(f"Clarity analysis failed: {e}")
            raise DimensionAnalysisError(self.dimension.value, str(e))
    
    def _count_complex_sentences(self, content: str) -> int:
        """Count sentences with multiple clauses."""
        sentences = re.split(r'[.!?]+', content)
        complex_count = 0
        for sentence in sentences:
            # Count conjunctions and semicolons as complexity indicators
            if len(re.findall(r'\b(and|but|or|however|therefore|moreover)\b', sentence)) > 2:
                complex_count += 1
            elif ';' in sentence:
                complex_count += 1
            elif len(sentence.split(',')) > 3:
                complex_count += 1
        return complex_count
    
    def _count_jargon(self, content: str) -> int:
        """Count technical jargon terms."""
        words = content.lower().split()
        jargon_count = sum(1 for word in words if word in self.jargon_terms)
        return jargon_count
    
    def _count_passive_voice(self, content: str) -> int:
        """Count instances of passive voice (simplified)."""
        passive_patterns = [
            r'\b(was|were|been|being|is|are|am)\s+\w+ed\b',
            r'\b(was|were|been|being|is|are|am)\s+\w+en\b',
        ]
        count = 0
        for pattern in passive_patterns:
            count += len(re.findall(pattern, content, re.IGNORECASE))
        return count
    
    def _calculate_readability(self, content: str) -> float:
        """Calculate Flesch Reading Ease score."""
        sentences = re.split(r'[.!?]+', content)
        words = content.split()
        
        if not sentences or not words:
            return 0.0
        
        avg_sentence_length = len(words) / len(sentences)
        avg_syllables = sum(self._count_syllables(word) for word in words) / len(words)
        
        # Flesch Reading Ease formula
        score = 206.835 - 1.015 * avg_sentence_length - 84.6 * avg_syllables
        return max(0.0, min(100.0, score))
    
    def _count_syllables(self, word: str) -> int:
        """Count syllables in a word (simplified)."""
        word = word.lower()
        vowels = 'aeiou'
        syllables = 0
        previous_was_vowel = False
        
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not previous_was_vowel:
                syllables += 1
            previous_was_vowel = is_vowel
        
        return max(1, syllables)


class StructureAnalyzer(DimensionAnalyzer):
    """Analyzes document structure and organization."""
    
    def __init__(self):
        super().__init__(QualityDimension.STRUCTURE)
    
    def analyze(self, content: str, metadata: Dict = None) -> DimensionScore:
        """Analyze structure of document."""
        try:
            metrics = self.extract_metrics(content)
            
            score = 100.0
            issues = []
            
            # Extract heading hierarchy
            headings = self._extract_heading_hierarchy(content)
            
            # Check for headings
            if not headings:
                score -= 30
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity=SeverityLevel.HIGH,
                    description="No headings found",
                    suggestion="Add headings to structure content",
                    impact_score=8.0
                ))
            else:
                # Check heading hierarchy
                hierarchy_issues = self._check_heading_hierarchy(headings)
                for issue in hierarchy_issues:
                    score -= 10
                    issues.append(issue)
            
            # Check section balance
            section_sizes = self._get_section_sizes(content)
            if section_sizes:
                balance = self._calculate_balance(section_sizes)
                if balance < 0.3:
                    score -= 15
                    issues.append(QualityIssue(
                        dimension=self.dimension,
                        severity=SeverityLevel.MEDIUM,
                        description="Unbalanced section sizes",
                        suggestion="Distribute content more evenly",
                        impact_score=5.0
                    ))
            
            # Check for logical flow
            flow_score = self._check_logical_flow(content)
            if flow_score < 0.5:
                score -= 20
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity=SeverityLevel.MEDIUM,
                    description="Poor logical flow between sections",
                    suggestion="Improve transitions between sections",
                    impact_score=6.0
                ))
            
            # Check content variety
            if metrics.content_diversity < 0.3:
                score -= 10
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity=SeverityLevel.LOW,
                    description="Limited content variety",
                    suggestion="Add lists, tables, or code examples",
                    impact_score=3.0
                ))
            
            return DimensionScore(
                dimension=self.dimension,
                score=max(0.0, score),
                issues=issues,
                metrics={
                    'heading_count': len(headings),
                    'section_balance': balance if section_sizes else 0,
                    'content_diversity': metrics.content_diversity
                }
            )
            
        except Exception as e:
            logger.error(f"Structure analysis failed: {e}")
            raise DimensionAnalysisError(self.dimension.value, str(e))
    
    def _extract_heading_hierarchy(self, content: str) -> List[Tuple[int, str]]:
        """Extract headings with their levels."""
        headings = []
        for match in re.finditer(r'^(#+)\s+(.+)$', content, re.MULTILINE):
            level = len(match.group(1))
            title = match.group(2).strip()
            headings.append((level, title))
        return headings
    
    def _check_heading_hierarchy(self, headings: List[Tuple[int, str]]) -> List[QualityIssue]:
        """Check for heading hierarchy issues."""
        issues = []
        prev_level = 0
        
        for level, title in headings:
            if prev_level > 0 and level > prev_level + 1:
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity=SeverityLevel.MEDIUM,
                    description=f"Skipped heading level (H{prev_level} to H{level})",
                    location=title,
                    suggestion="Use sequential heading levels",
                    impact_score=4.0
                ))
            prev_level = level
        
        # Check for multiple H1s
        h1_count = sum(1 for level, _ in headings if level == 1)
        if h1_count > 1:
            issues.append(QualityIssue(
                dimension=self.dimension,
                severity=SeverityLevel.MEDIUM,
                description=f"Multiple H1 headings found ({h1_count})",
                suggestion="Use only one H1 per document",
                impact_score=5.0
            ))
        
        return issues
    
    def _get_section_sizes(self, content: str) -> List[int]:
        """Get word count for each section."""
        sections = re.split(r'^#+\s+.*$', content, flags=re.MULTILINE)
        return [len(section.split()) for section in sections if section.strip()]
    
    def _calculate_balance(self, sizes: List[int]) -> float:
        """Calculate balance score for section sizes (0-1)."""
        if not sizes:
            return 0.0
        
        avg_size = sum(sizes) / len(sizes)
        if avg_size == 0:
            return 0.0
        
        # Calculate variance
        variance = sum((s - avg_size) ** 2 for s in sizes) / len(sizes)
        std_dev = variance ** 0.5
        
        # Convert to balance score (lower variance = higher balance)
        coefficient_of_variation = std_dev / avg_size
        balance = max(0.0, 1.0 - coefficient_of_variation)
        
        return balance
    
    def _check_logical_flow(self, content: str) -> float:
        """Check logical flow between sections (simplified)."""
        # Look for transition words and phrases
        transitions = [
            'however', 'therefore', 'furthermore', 'moreover',
            'in addition', 'consequently', 'as a result', 'for example',
            'specifically', 'namely', 'in other words', 'that is'
        ]
        
        transition_count = 0
        for transition in transitions:
            transition_count += len(re.findall(rf'\b{transition}\b', content, re.IGNORECASE))
        
        # Normalize by word count
        words = len(content.split())
        if words == 0:
            return 0.0
        
        # Expect roughly 1 transition per 100 words
        expected = words / 100
        if expected == 0:
            return 1.0
        
        flow_score = min(1.0, transition_count / expected)
        return flow_score


class AccuracyAnalyzer(DimensionAnalyzer):
    """Analyzes document accuracy and correctness."""
    
    def __init__(self):
        super().__init__(QualityDimension.ACCURACY)
        self.outdated_patterns = [
            (r'python\s*2\.\d+', 'Python 2.x is outdated'),
            (r'angular\.?js\b', 'AngularJS is outdated'),
            (r'jquery\s*1\.\d+', 'jQuery 1.x is outdated'),
        ]
    
    def analyze(self, content: str, metadata: Dict = None) -> DimensionScore:
        """Analyze accuracy of document."""
        try:
            score = 100.0
            issues = []
            
            # Check for outdated references
            outdated = self._find_outdated_references(content)
            if outdated:
                score -= min(len(outdated) * 10, 30)
                for ref, reason in outdated:
                    issues.append(QualityIssue(
                        dimension=self.dimension,
                        severity=SeverityLevel.HIGH,
                        description=f"Outdated reference: {reason}",
                        location=ref,
                        suggestion="Update to current version",
                        impact_score=7.0
                    ))
            
            # Check for broken links
            broken_links = self._find_broken_links(content)
            if broken_links:
                score -= min(len(broken_links) * 5, 20)
                for link in broken_links[:5]:  # Limit to first 5
                    issues.append(QualityIssue(
                        dimension=self.dimension,
                        severity=SeverityLevel.MEDIUM,
                        description="Potentially broken link",
                        location=link,
                        suggestion="Verify link is accessible",
                        impact_score=4.0
                    ))
            
            # Check code blocks for syntax errors
            code_errors = self._check_code_blocks(content)
            if code_errors:
                score -= min(len(code_errors) * 15, 40)
                for error in code_errors:
                    issues.append(QualityIssue(
                        dimension=self.dimension,
                        severity=SeverityLevel.CRITICAL,
                        description=f"Code error: {error['error']}",
                        location=f"Line {error['line']}",
                        suggestion="Fix syntax error in code block",
                        impact_score=9.0
                    ))
            
            # Check for consistency
            inconsistencies = self._find_inconsistencies(content)
            if inconsistencies:
                score -= min(len(inconsistencies) * 5, 15)
                for inconsistency in inconsistencies:
                    issues.append(QualityIssue(
                        dimension=self.dimension,
                        severity=SeverityLevel.LOW,
                        description=inconsistency,
                        suggestion="Ensure consistent terminology",
                        impact_score=3.0
                    ))
            
            return DimensionScore(
                dimension=self.dimension,
                score=max(0.0, score),
                issues=issues,
                metrics={
                    'outdated_count': len(outdated),
                    'broken_links': len(broken_links),
                    'code_errors': len(code_errors)
                }
            )
            
        except Exception as e:
            logger.error(f"Accuracy analysis failed: {e}")
            raise DimensionAnalysisError(self.dimension.value, str(e))
    
    def _find_outdated_references(self, content: str) -> List[Tuple[str, str]]:
        """Find outdated technology references."""
        outdated = []
        for pattern, reason in self.outdated_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                outdated.append((match, reason))
        return outdated
    
    def _find_broken_links(self, content: str) -> List[str]:
        """Find potentially broken links (simplified check)."""
        broken = []
        link_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
        
        for match in re.finditer(link_pattern, content):
            url = match.group(2)
            # Simple heuristic checks
            if url.startswith('http://localhost') or url.startswith('http://127.0.0.1'):
                broken.append(url)
            elif 'example.com' in url:
                broken.append(url)
            elif url.endswith('.broken') or url.endswith('.invalid'):
                broken.append(url)
        
        return broken
    
    def _check_code_blocks(self, content: str) -> List[Dict]:
        """Check code blocks for basic syntax errors."""
        errors = []
        code_block_pattern = r'```(\w*)\n(.*?)\n```'
        
        for match in re.finditer(code_block_pattern, content, re.DOTALL):
            language = match.group(1).lower()
            code = match.group(2)
            
            if language in ['python', 'py']:
                errors.extend(self._check_python_syntax(code))
            elif language in ['javascript', 'js']:
                errors.extend(self._check_javascript_syntax(code))
        
        return errors
    
    def _check_python_syntax(self, code: str) -> List[Dict]:
        """Basic Python syntax checking."""
        errors = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Check for common syntax errors
            if line.strip() and not line.strip().startswith('#'):
                # Check for missing colons
                if any(line.strip().startswith(kw) for kw in ['if ', 'for ', 'while ', 'def ', 'class ']):
                    if not line.rstrip().endswith(':'):
                        errors.append({'line': i, 'error': 'Missing colon'})
                
                # Check for unbalanced parentheses
                if line.count('(') != line.count(')'):
                    errors.append({'line': i, 'error': 'Unbalanced parentheses'})
        
        return errors
    
    def _check_javascript_syntax(self, code: str) -> List[Dict]:
        """Basic JavaScript syntax checking."""
        errors = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Check for common syntax errors
            if line.strip() and not line.strip().startswith('//'):
                # Check for unbalanced braces
                if line.count('{') != line.count('}'):
                    errors.append({'line': i, 'error': 'Unbalanced braces'})
                
                # Check for missing semicolons (simplified)
                if not line.rstrip().endswith((';', '{', '}', ',')) and not line.strip().startswith(('if', 'for', 'while')):
                    if '=' in line or 'return' in line or 'const' in line or 'let' in line:
                        errors.append({'line': i, 'error': 'Possible missing semicolon'})
        
        return errors
    
    def _find_inconsistencies(self, content: str) -> List[str]:
        """Find terminology inconsistencies."""
        inconsistencies = []
        
        # Check for mixed terminology
        term_variants = [
            ['API', 'api', 'Api'],
            ['URL', 'url', 'Url'],
            ['ID', 'id', 'Id'],
        ]
        
        for variants in term_variants:
            found = [v for v in variants if v in content]
            if len(found) > 1:
                inconsistencies.append(f"Inconsistent capitalization: {', '.join(found)}")
        
        return inconsistencies


class FormattingAnalyzer(DimensionAnalyzer):
    """Analyzes document formatting and style."""
    
    def __init__(self):
        super().__init__(QualityDimension.FORMATTING)
    
    def analyze(self, content: str, metadata: Dict = None) -> DimensionScore:
        """Analyze formatting of document."""
        try:
            metrics = self.extract_metrics(content)
            
            score = 100.0
            issues = []
            
            # Check line length
            long_lines = self._find_long_lines(content)
            if long_lines:
                score -= min(len(long_lines) * 2, 15)
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity=SeverityLevel.LOW,
                    description=f"{len(long_lines)} lines exceed 100 characters",
                    suggestion="Break long lines for better readability",
                    impact_score=2.0
                ))
            
            # Check paragraph length
            if metrics.avg_paragraph_length > 500:
                score -= 10
                issues.append(QualityIssue(
                    dimension=self.dimension,
                    severity=SeverityLevel.LOW,
                    description="Paragraphs are too long",
                    suggestion="Break into smaller paragraphs",
                    impact_score=3.0
                ))
            
            # Check for formatting inconsistencies
            inconsistencies = self._find_formatting_issues(content)
            if inconsistencies:
                score -= min(len(inconsistencies) * 3, 20)
                for issue in inconsistencies[:5]:  # Limit to first 5
                    issues.append(QualityIssue(
                        dimension=self.dimension,
                        severity=SeverityLevel.LOW,
                        description=issue,
                        suggestion="Fix formatting inconsistency",
                        impact_score=2.0
                    ))
            
            # Check whitespace issues
            whitespace_issues = self._check_whitespace(content)
            if whitespace_issues:
                score -= min(len(whitespace_issues) * 2, 10)
                for issue in whitespace_issues[:3]:
                    issues.append(QualityIssue(
                        dimension=self.dimension,
                        severity=SeverityLevel.INFO,
                        description=issue,
                        suggestion="Clean up whitespace",
                        impact_score=1.0
                    ))
            
            return DimensionScore(
                dimension=self.dimension,
                score=max(0.0, score),
                issues=issues,
                metrics={
                    'long_lines': len(long_lines),
                    'formatting_issues': len(inconsistencies)
                }
            )
            
        except Exception as e:
            logger.error(f"Formatting analysis failed: {e}")
            raise DimensionAnalysisError(self.dimension.value, str(e))
    
    def _find_long_lines(self, content: str, max_length: int = 100) -> List[int]:
        """Find lines that exceed maximum length."""
        long_lines = []
        for i, line in enumerate(content.split('\n'), 1):
            if len(line) > max_length:
                long_lines.append(i)
        return long_lines
    
    def _find_formatting_issues(self, content: str) -> List[str]:
        """Find formatting inconsistencies."""
        issues = []
        
        # Check for mixed list styles
        if '- ' in content and '* ' in content:
            issues.append("Mixed list bullet styles (- and *)")
        
        # Check for inconsistent heading styles
        if '===' in content and '---' in content and '#' in content:
            issues.append("Mixed heading styles")
        
        # Check for tabs vs spaces
        lines = content.split('\n')
        has_tabs = any('\t' in line for line in lines)
        has_spaces = any(line.startswith('    ') for line in lines)
        if has_tabs and has_spaces:
            issues.append("Mixed tabs and spaces for indentation")
        
        return issues
    
    def _check_whitespace(self, content: str) -> List[str]:
        """Check for whitespace issues."""
        issues = []
        lines = content.split('\n')
        
        # Check for trailing whitespace
        trailing = sum(1 for line in lines if line.rstrip() != line)
        if trailing > 0:
            issues.append(f"{trailing} lines with trailing whitespace")
        
        # Check for multiple blank lines
        blank_count = 0
        max_blank = 0
        for line in lines:
            if not line.strip():
                blank_count += 1
                max_blank = max(max_blank, blank_count)
            else:
                blank_count = 0
        
        if max_blank > 2:
            issues.append(f"Multiple consecutive blank lines ({max_blank})")
        
        return issues