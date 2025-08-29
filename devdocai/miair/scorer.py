"""
Quality scoring system for documentation.

Implements multi-dimensional quality assessment across completeness, clarity,
consistency, and accuracy dimensions.
"""

import re
import math
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import numpy as np


class QualityDimension(Enum):
    """Quality assessment dimensions."""
    COMPLETENESS = "completeness"
    CLARITY = "clarity"
    CONSISTENCY = "consistency"
    ACCURACY = "accuracy"


@dataclass
class QualityMetrics:
    """Container for quality metrics."""
    completeness: float = 0.0
    clarity: float = 0.0
    consistency: float = 0.0
    accuracy: float = 0.0
    overall: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            'completeness': self.completeness,
            'clarity': self.clarity,
            'consistency': self.consistency,
            'accuracy': self.accuracy,
            'overall': self.overall
        }


@dataclass
class ScoringWeights:
    """Configurable weights for quality dimensions."""
    completeness: float = 0.25
    clarity: float = 0.25
    consistency: float = 0.25
    accuracy: float = 0.25
    
    def __post_init__(self):
        """Validate weights sum to 1.0."""
        total = self.completeness + self.clarity + self.consistency + self.accuracy
        if abs(total - 1.0) > 0.001:
            # Normalize weights
            self.completeness /= total
            self.clarity /= total
            self.consistency /= total
            self.accuracy /= total


class QualityScorer:
    """
    Multi-dimensional quality scorer for documentation.
    
    Evaluates documents across completeness, clarity, consistency,
    and accuracy dimensions to produce an overall quality score.
    """
    
    def __init__(self, weights: Optional[ScoringWeights] = None):
        """
        Initialize quality scorer with configurable weights.
        
        Args:
            weights: Custom weights for quality dimensions
        """
        self.weights = weights or ScoringWeights()
        self._init_patterns()
    
    def _init_patterns(self):
        """Initialize regex patterns for analysis."""
        # Documentation markers
        self.section_pattern = re.compile(r'^#{1,6}\s+.+', re.MULTILINE)
        self.code_block_pattern = re.compile(r'```[\s\S]*?```', re.MULTILINE)
        self.link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
        
        # Quality indicators
        self.todo_pattern = re.compile(r'\b(TODO|FIXME|XXX|HACK)\b', re.IGNORECASE)
        self.placeholder_pattern = re.compile(r'\[(placeholder|tbd|to be determined)\]', re.IGNORECASE)
        
        # Clarity indicators
        self.complex_sentence_pattern = re.compile(r'[^.!?]{150,}[.!?]')
        self.passive_voice_pattern = re.compile(r'\b(was|were|been|being|is|are|am)\s+\w+ed\b', re.IGNORECASE)
    
    def score_document(self, content: str, metadata: Optional[Dict] = None) -> QualityMetrics:
        """
        Score a document across all quality dimensions.
        
        Args:
            content: Document content to score
            metadata: Optional metadata for context
            
        Returns:
            QualityMetrics with dimensional and overall scores
        """
        if not content:
            return QualityMetrics()
        
        # Calculate individual dimension scores
        completeness = self.score_completeness(content, metadata)
        clarity = self.score_clarity(content)
        consistency = self.score_consistency(content)
        accuracy = self.score_accuracy(content, metadata)
        
        # Calculate weighted overall score
        overall = (
            self.weights.completeness * completeness +
            self.weights.clarity * clarity +
            self.weights.consistency * consistency +
            self.weights.accuracy * accuracy
        )
        
        return QualityMetrics(
            completeness=completeness,
            clarity=clarity,
            consistency=consistency,
            accuracy=accuracy,
            overall=overall
        )
    
    def score_completeness(self, content: str, metadata: Optional[Dict] = None) -> float:
        """
        Score document completeness.
        
        Evaluates:
        - Section structure and organization
        - Presence of required elements (intro, examples, references)
        - Coverage of topics
        - Absence of placeholders/TODOs
        """
        if not content:
            return 0.0
        
        scores = []
        
        # Check for section structure
        sections = self.section_pattern.findall(content)
        section_score = min(len(sections) / 5.0, 1.0)  # Expect at least 5 sections
        scores.append(section_score)
        
        # Check for code examples
        code_blocks = self.code_block_pattern.findall(content)
        code_score = min(len(code_blocks) / 3.0, 1.0)  # Expect some examples
        scores.append(code_score)
        
        # Check for links/references
        links = self.link_pattern.findall(content)
        link_score = min(len(links) / 2.0, 1.0)  # Expect some references
        scores.append(link_score)
        
        # Penalize TODOs and placeholders
        todos = self.todo_pattern.findall(content)
        placeholders = self.placeholder_pattern.findall(content)
        incompleteness_penalty = max(0, 1.0 - (len(todos) + len(placeholders)) * 0.1)
        scores.append(incompleteness_penalty)
        
        # Check content length (expecting reasonable documentation)
        word_count = len(content.split())
        length_score = min(word_count / 500.0, 1.0)  # Expect at least 500 words
        scores.append(length_score)
        
        # Check for essential sections
        essential_sections = ['introduction', 'usage', 'example', 'reference']
        content_lower = content.lower()
        found_essentials = sum(1 for section in essential_sections if section in content_lower)
        essential_score = found_essentials / len(essential_sections)
        scores.append(essential_score)
        
        return np.mean(scores)
    
    def score_clarity(self, content: str) -> float:
        """
        Score document clarity.
        
        Evaluates:
        - Sentence complexity
        - Vocabulary complexity
        - Active vs passive voice usage
        - Paragraph structure
        """
        if not content:
            return 0.0
        
        scores = []
        
        # Analyze sentence complexity
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if sentences:
            # Average sentence length (optimal: 15-20 words)
            avg_sentence_length = np.mean([len(s.split()) for s in sentences])
            optimal_length = 17.5
            length_deviation = abs(avg_sentence_length - optimal_length)
            sentence_score = max(0, 1.0 - length_deviation / 20.0)
            scores.append(sentence_score)
            
            # Check for overly complex sentences
            complex_sentences = self.complex_sentence_pattern.findall(content)
            complexity_score = max(0, 1.0 - len(complex_sentences) / max(len(sentences), 1) * 2)
            scores.append(complexity_score)
        
        # Check passive voice usage (prefer active voice)
        passive_instances = self.passive_voice_pattern.findall(content)
        words = content.split()
        passive_ratio = len(passive_instances) / max(len(words), 1)
        passive_score = max(0, 1.0 - passive_ratio * 20)  # Penalize heavy passive use
        scores.append(passive_score)
        
        # Check paragraph structure
        paragraphs = content.split('\n\n')
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        if paragraphs:
            # Optimal paragraph length: 3-5 sentences
            paragraph_scores = []
            for para in paragraphs:
                para_sentences = re.split(r'[.!?]+', para)
                para_sentences = [s for s in para_sentences if s.strip()]
                if 3 <= len(para_sentences) <= 5:
                    paragraph_scores.append(1.0)
                elif 2 <= len(para_sentences) <= 7:
                    paragraph_scores.append(0.7)
                else:
                    paragraph_scores.append(0.4)
            
            if paragraph_scores:
                scores.append(np.mean(paragraph_scores))
        
        # Check for clear headers and structure
        headers = self.section_pattern.findall(content)
        if headers:
            # Headers should be descriptive (not too short)
            header_lengths = [len(h.strip('#').strip().split()) for h in headers]
            avg_header_length = np.mean(header_lengths)
            header_score = min(avg_header_length / 3.0, 1.0)  # Expect 3+ words
            scores.append(header_score)
        
        return np.mean(scores) if scores else 0.5
    
    def score_consistency(self, content: str) -> float:
        """
        Score document consistency.
        
        Evaluates:
        - Terminology consistency
        - Formatting consistency
        - Style consistency
        - Structural patterns
        """
        if not content:
            return 0.0
        
        scores = []
        
        # Check terminology consistency
        words = re.findall(r'\b\w+\b', content.lower())
        
        # Look for common variations that should be consistent
        term_variations = {
            'setup': ['setup', 'set-up', 'set up'],
            'email': ['email', 'e-mail', 'Email'],
            'database': ['database', 'db', 'DB'],
            'api': ['api', 'API', 'Api']
        }
        
        consistency_scores = []
        for base_term, variations in term_variations.items():
            counts = [words.count(v.lower()) for v in variations]
            if sum(counts) > 0:
                # Calculate consistency (how dominant is the most common variant)
                max_count = max(counts)
                total_count = sum(counts)
                consistency = max_count / total_count
                consistency_scores.append(consistency)
        
        if consistency_scores:
            scores.append(np.mean(consistency_scores))
        
        # Check formatting consistency (code blocks)
        code_blocks = self.code_block_pattern.findall(content)
        if code_blocks:
            # Check if language identifiers are used consistently
            lang_pattern = re.compile(r'```(\w+)')
            languages = lang_pattern.findall(content)
            if languages:
                lang_consistency = len(languages) / len(code_blocks)
                scores.append(lang_consistency)
        
        # Check header level progression
        headers = self.section_pattern.findall(content)
        if headers:
            header_levels = [len(re.match(r'^#+', h).group()) for h in headers]
            
            # Check for logical progression (no skipping levels)
            progression_score = 1.0
            for i in range(1, len(header_levels)):
                level_diff = header_levels[i] - header_levels[i-1]
                if level_diff > 1:  # Skipped a level
                    progression_score -= 0.1
            
            scores.append(max(0, progression_score))
        
        # Check list formatting consistency
        bullet_lists = re.findall(r'^\s*[-*+]\s+', content, re.MULTILINE)
        if bullet_lists:
            # Check if consistent bullet style is used
            bullet_types = [b.strip()[0] for b in bullet_lists]
            most_common = max(set(bullet_types), key=bullet_types.count)
            bullet_consistency = bullet_types.count(most_common) / len(bullet_types)
            scores.append(bullet_consistency)
        
        # Check spacing consistency
        double_spaces = len(re.findall(r'  +', content))
        spacing_score = max(0, 1.0 - double_spaces / 100.0)  # Penalize inconsistent spacing
        scores.append(spacing_score)
        
        return np.mean(scores) if scores else 0.7
    
    def score_accuracy(self, content: str, metadata: Optional[Dict] = None) -> float:
        """
        Score document accuracy.
        
        Evaluates:
        - Technical correctness indicators
        - Up-to-date information
        - Proper references
        - No contradictions
        """
        if not content:
            return 0.0
        
        scores = []
        
        # Check for version information (indicates maintained docs)
        version_pattern = re.compile(r'\b(v?\d+\.\d+(?:\.\d+)?)\b', re.IGNORECASE)
        versions = version_pattern.findall(content)
        version_score = min(len(versions) / 2.0, 1.0)  # Expect some version refs
        scores.append(version_score)
        
        # Check for dates (recent updates indicate accuracy)
        date_pattern = re.compile(r'\b(202[0-9]|201[5-9])\b')
        dates = date_pattern.findall(content)
        if dates:
            # Recent dates score higher
            recent_dates = [d for d in dates if int(d) >= 2023]
            recency_score = len(recent_dates) / len(dates)
            scores.append(recency_score)
        
        # Check for proper code syntax in code blocks
        code_blocks = self.code_block_pattern.findall(content)
        if code_blocks:
            syntax_scores = []
            for block in code_blocks:
                # Basic syntax checks
                has_balanced_parens = block.count('(') == block.count(')')
                has_balanced_brackets = block.count('[') == block.count(']')
                has_balanced_braces = block.count('{') == block.count('}')
                
                syntax_score = sum([has_balanced_parens, has_balanced_brackets, has_balanced_braces]) / 3.0
                syntax_scores.append(syntax_score)
            
            if syntax_scores:
                scores.append(np.mean(syntax_scores))
        
        # Check for broken references (basic check)
        links = self.link_pattern.findall(content)
        if links:
            valid_links = []
            for link_text, link_url in links:
                # Basic URL validation
                is_valid = (
                    link_url.startswith(('http://', 'https://', '/', '#', './')) or
                    link_url.endswith(('.md', '.html', '.pdf'))
                )
                valid_links.append(1.0 if is_valid else 0.5)
            
            scores.append(np.mean(valid_links))
        
        # Check for warning/deprecation notices (good for accuracy)
        warning_pattern = re.compile(r'\b(deprecated|warning|note|important)\b', re.IGNORECASE)
        warnings = warning_pattern.findall(content)
        warning_score = min(len(warnings) / 3.0, 1.0)  # Some warnings are good
        scores.append(0.5 + warning_score * 0.5)  # Baseline + bonus
        
        # If metadata provided, check consistency with content
        if metadata:
            if 'last_updated' in metadata:
                # Recent updates indicate maintained accuracy
                scores.append(0.9)  # Assume good if metadata present
        
        return np.mean(scores) if scores else 0.6
    
    def analyze_quality_issues(self, content: str) -> Dict[str, List[str]]:
        """
        Identify specific quality issues in the document.
        
        Returns:
            Dictionary mapping issue types to lists of specific problems
        """
        issues = {
            'completeness': [],
            'clarity': [],
            'consistency': [],
            'accuracy': []
        }
        
        if not content:
            issues['completeness'].append("Document is empty")
            return issues
        
        # Completeness issues
        todos = self.todo_pattern.findall(content)
        if todos:
            issues['completeness'].append(f"Found {len(todos)} TODO/FIXME markers")
        
        placeholders = self.placeholder_pattern.findall(content)
        if placeholders:
            issues['completeness'].append(f"Found {len(placeholders)} placeholder sections")
        
        word_count = len(content.split())
        if word_count < 200:
            issues['completeness'].append(f"Document too short ({word_count} words)")
        
        # Clarity issues
        complex_sentences = self.complex_sentence_pattern.findall(content)
        if complex_sentences:
            issues['clarity'].append(f"Found {len(complex_sentences)} overly complex sentences")
        
        passive_instances = self.passive_voice_pattern.findall(content)
        passive_ratio = len(passive_instances) / max(len(content.split()), 1)
        if passive_ratio > 0.1:
            issues['clarity'].append(f"High passive voice usage ({passive_ratio:.1%})")
        
        # Consistency issues
        double_spaces = re.findall(r'  +', content)
        if len(double_spaces) > 5:
            issues['consistency'].append(f"Inconsistent spacing ({len(double_spaces)} instances)")
        
        # Accuracy issues
        broken_link_pattern = re.compile(r'\[([^\]]+)\]\(\s*\)')
        broken_links = broken_link_pattern.findall(content)
        if broken_links:
            issues['accuracy'].append(f"Found {len(broken_links)} potentially broken links")
        
        return issues
    
    def get_improvement_suggestions(self, metrics: QualityMetrics) -> List[str]:
        """
        Generate improvement suggestions based on quality metrics.
        
        Args:
            metrics: Current quality metrics
            
        Returns:
            List of actionable improvement suggestions
        """
        suggestions = []
        
        # Threshold for suggesting improvements
        threshold = 0.7
        
        if metrics.completeness < threshold:
            suggestions.append("Add more sections and examples to improve completeness")
            suggestions.append("Include introduction, usage, and reference sections")
            suggestions.append("Remove TODO markers and placeholder content")
        
        if metrics.clarity < threshold:
            suggestions.append("Simplify complex sentences for better readability")
            suggestions.append("Use active voice instead of passive voice")
            suggestions.append("Organize content into clear paragraphs (3-5 sentences each)")
        
        if metrics.consistency < threshold:
            suggestions.append("Standardize terminology throughout the document")
            suggestions.append("Use consistent formatting for code blocks and lists")
            suggestions.append("Ensure header levels follow logical progression")
        
        if metrics.accuracy < threshold:
            suggestions.append("Add version information and update dates")
            suggestions.append("Verify and fix any broken links")
            suggestions.append("Include warnings for deprecated features")
        
        if metrics.overall >= 0.85:
            suggestions.append("Document quality is excellent! Minor refinements may still be possible")
        elif metrics.overall < 0.5:
            suggestions.insert(0, "Major revision recommended - document needs significant improvement")
        
        return suggestions