"""
M003 MIAIR Engine - Quality Metrics

Calculates and tracks document quality metrics for optimization assessment.

Key Features:
- Comprehensive quality scoring (completeness, clarity, consistency, structure, technical accuracy)
- Quality improvement measurement
- Quality gate validation (85% threshold)
- Detailed breakdown for optimization guidance
- Performance tracking and analytics
- Document type-specific scoring adjustments

Quality Dimensions:
- Completeness (25%): How complete is the information?
- Clarity (25%): How clear and understandable is the content?
- Consistency (20%): How consistent is the style and terminology?
- Structure (15%): How well organized is the document?
- Technical Accuracy (15%): How accurate is the technical content?
"""

import re
import logging
import math
from typing import Dict, Any, List, Optional, Tuple, Set
from collections import Counter
from dataclasses import dataclass

from .models import Document, QualityScore, DocumentType, SemanticElement, ElementType


logger = logging.getLogger(__name__)


@dataclass
class QualityAnalysis:
    """Detailed quality analysis results."""
    score: QualityScore
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
    metrics: Dict[str, float]


class QualityMetrics:
    """
    Calculate and track document quality metrics.
    
    Provides comprehensive quality assessment based on multiple dimensions
    to guide optimization and measure improvement.
    """
    
    def __init__(self):
        """Initialize quality metrics calculator."""
        # Quality dimension weights (must sum to 1.0)
        self.weights = {
            'completeness': 0.25,
            'clarity': 0.25,
            'consistency': 0.20,
            'structure': 0.15,
            'technical_accuracy': 0.15
        }
        
        # Quality thresholds
        self.quality_gate = 85.0  # Minimum acceptable quality
        self.excellence_threshold = 95.0  # Excellence benchmark
        
        # Analysis parameters
        self.min_words_for_analysis = 10
        self.readability_constants = self._load_readability_constants()
        self.technical_indicators = self._load_technical_indicators()
        
        logger.debug("QualityMetrics initialized with weights: %s", self.weights)
    
    def calculate_quality_score(
        self,
        document: Document,
        semantic_elements: Optional[List[SemanticElement]] = None
    ) -> QualityScore:
        """
        Calculate comprehensive quality score for document.
        
        Args:
            document: Document to evaluate
            semantic_elements: Pre-extracted semantic elements (optional)
            
        Returns:
            QualityScore with overall and dimensional scores
        """
        logger.debug(f"Calculating quality score for document {document.id}")
        
        if not document.content or len(document.content.strip()) < self.min_words_for_analysis:
            logger.warning(f"Document {document.id} too short for quality analysis")
            return self._create_minimal_score()
        
        # Calculate individual dimension scores
        completeness = self._assess_completeness(document, semantic_elements)
        clarity = self._assess_clarity(document)
        consistency = self._assess_consistency(document)
        structure = self._assess_structure(document, semantic_elements)
        technical_accuracy = self._assess_technical_accuracy(document)
        
        # Apply document type adjustments
        completeness, clarity, consistency, structure, technical_accuracy = \
            self._apply_document_type_adjustments(
                document.type, completeness, clarity, consistency, structure, technical_accuracy
            )
        
        # Calculate weighted overall score
        overall = (
            completeness * self.weights['completeness'] +
            clarity * self.weights['clarity'] +
            consistency * self.weights['consistency'] +
            structure * self.weights['structure'] +
            technical_accuracy * self.weights['technical_accuracy']
        )
        
        score = QualityScore(
            overall=round(overall, 2),
            completeness=round(completeness, 2),
            clarity=round(clarity, 2),
            consistency=round(consistency, 2),
            structure=round(structure, 2),
            technical_accuracy=round(technical_accuracy, 2)
        )
        
        logger.debug(f"Quality score for {document.id}: overall={score.overall}")
        return score
    
    def measure_improvement(
        self,
        initial_score: QualityScore,
        final_score: QualityScore
    ) -> float:
        """
        Measure quality improvement percentage.
        
        Args:
            initial_score: Initial quality score
            final_score: Final quality score after optimization
            
        Returns:
            Improvement percentage (can be negative if quality decreased)
        """
        if initial_score.overall == 0:
            return 100.0 if final_score.overall > 0 else 0.0
        
        improvement = ((final_score.overall - initial_score.overall) / initial_score.overall) * 100
        
        logger.debug(f"Quality improvement: {improvement:.2f}% ({initial_score.overall} -> {final_score.overall})")
        return round(improvement, 2)
    
    def validate_quality_gate(
        self,
        score: QualityScore,
        quality_gate: Optional[float] = None
    ) -> bool:
        """
        Check if document meets quality gate threshold.
        
        Args:
            score: Quality score to validate
            quality_gate: Override default quality gate (default: 85.0)
            
        Returns:
            True if meets quality gate, False otherwise
        """
        threshold = quality_gate if quality_gate is not None else self.quality_gate
        meets_gate = score.overall >= threshold
        
        logger.debug(f"Quality gate check: {score.overall} >= {threshold} = {meets_gate}")
        return meets_gate
    
    def analyze_quality(
        self,
        document: Document,
        semantic_elements: Optional[List[SemanticElement]] = None
    ) -> QualityAnalysis:
        """
        Perform detailed quality analysis with recommendations.
        
        Args:
            document: Document to analyze
            semantic_elements: Pre-extracted semantic elements
            
        Returns:
            QualityAnalysis with detailed breakdown and recommendations
        """
        score = self.calculate_quality_score(document, semantic_elements)
        
        # Identify strengths and weaknesses
        strengths = self._identify_strengths(score)
        weaknesses = self._identify_weaknesses(score)
        recommendations = self._generate_recommendations(score, document)
        
        # Calculate detailed metrics
        metrics = self._calculate_detailed_metrics(document)
        
        return QualityAnalysis(
            score=score,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
            metrics=metrics
        )
    
    def _assess_completeness(
        self, 
        document: Document, 
        semantic_elements: Optional[List[SemanticElement]]
    ) -> float:
        """
        Assess document completeness (25% of total score).
        
        Measures how complete the information is based on:
        - Presence of key sections
        - Information depth
        - Coverage of expected topics
        """
        score = 50.0  # Base score
        content = document.content
        
        # Extract semantic elements if not provided
        if semantic_elements is None:
            from .semantic_analyzer import SemanticAnalyzer
            analyzer = SemanticAnalyzer()
            semantic_elements = analyzer.extract_semantic_elements(document)
        
        element_types = set(elem.type for elem in semantic_elements)
        
        # Structure completeness
        if ElementType.HEADER in element_types:
            score += 10.0  # Has headers
        if ElementType.PARAGRAPH in element_types:
            score += 10.0  # Has content paragraphs
        
        # Content depth
        word_count = len(content.split())
        if word_count >= 100:
            score += 10.0
        elif word_count >= 50:
            score += 5.0
        
        # Technical completeness (for technical documents)
        if document.type in [DocumentType.API_DOCUMENTATION, DocumentType.TECHNICAL_SPEC]:
            if ElementType.CODE_BLOCK in element_types:
                score += 10.0  # Has code examples
            if ElementType.TECHNICAL_TERM in element_types:
                score += 5.0   # Has technical terms
            if ElementType.DEFINITION in element_types:
                score += 5.0   # Has definitions
        
        # Information organization
        headers = [elem for elem in semantic_elements if elem.type == ElementType.HEADER]
        if len(headers) >= 2:
            score += 5.0   # Multiple sections
        
        return min(100.0, score)
    
    def _assess_clarity(self, document: Document) -> float:
        """
        Assess document clarity (25% of total score).
        
        Measures how clear and understandable the content is:
        - Readability metrics
        - Sentence structure
        - Vocabulary complexity
        - Use of examples and explanations
        """
        score = 50.0  # Base score
        content = document.content
        
        # Basic readability assessment
        sentences = self._split_into_sentences(content)
        words = content.split()
        
        if not sentences or not words:
            return 0.0
        
        # Average sentence length (shorter is generally clearer)
        avg_sentence_length = len(words) / len(sentences)
        if avg_sentence_length <= 15:
            score += 20.0  # Good sentence length
        elif avg_sentence_length <= 25:
            score += 10.0  # Acceptable sentence length
        else:
            score -= 5.0   # Too long sentences
        
        # Syllable complexity (simplified)
        complex_words = sum(1 for word in words if self._count_syllables(word) >= 3)
        complex_ratio = complex_words / len(words) if words else 0
        
        if complex_ratio <= 0.15:
            score += 15.0  # Low complexity
        elif complex_ratio <= 0.25:
            score += 5.0   # Medium complexity
        else:
            score -= 10.0  # High complexity
        
        # Use of examples and explanations
        example_indicators = ['for example', 'e.g.', 'such as', 'like', 'including']
        examples_count = sum(content.lower().count(indicator) for indicator in example_indicators)
        if examples_count > 0:
            score += 10.0
        
        # Active voice preference (simplified detection)
        passive_indicators = ['was', 'were', 'been', 'being']
        total_words = len(words)
        passive_count = sum(content.lower().count(indicator) for indicator in passive_indicators)
        passive_ratio = passive_count / total_words if total_words > 0 else 0
        
        if passive_ratio <= 0.05:
            score += 5.0   # Low passive voice
        elif passive_ratio >= 0.15:
            score -= 5.0   # High passive voice
        
        return min(100.0, max(0.0, score))
    
    def _assess_consistency(self, document: Document) -> float:
        """
        Assess document consistency (20% of total score).
        
        Measures consistency in:
        - Terminology usage
        - Formatting and style
        - Tone and voice
        - Structural patterns
        """
        score = 60.0  # Base score
        content = document.content
        
        # Terminology consistency
        technical_terms = self._extract_technical_terms(content)
        if technical_terms:
            # Check for consistent usage of technical terms
            term_variations = self._detect_term_variations(technical_terms)
            if term_variations == 0:
                score += 15.0  # Consistent terminology
            else:
                score -= term_variations * 5.0  # Penalty for inconsistencies
        
        # Formatting consistency
        headers = re.findall(r'^(#{1,6})\s', content, re.MULTILINE)
        if headers:
            # Check header level consistency
            header_levels = [len(h) for h in headers]
            level_jumps = sum(1 for i in range(1, len(header_levels)) 
                            if header_levels[i] > header_levels[i-1] + 1)
            if level_jumps == 0:
                score += 10.0  # Consistent header hierarchy
            else:
                score -= level_jumps * 3.0
        
        # List formatting consistency
        list_markers = re.findall(r'^[\s]*[-*+]\s', content, re.MULTILINE)
        numbered_lists = re.findall(r'^\s*\d+\.\s', content, re.MULTILINE)
        
        if list_markers and len(set(marker.strip() for marker in list_markers)) == 1:
            score += 5.0   # Consistent bullet style
        if numbered_lists:
            score += 5.0   # Uses numbered lists appropriately
        
        # Tone consistency (simplified analysis)
        tone_score = self._analyze_tone_consistency(content)
        score += tone_score * 10.0  # Up to 10 points for tone
        
        return min(100.0, max(0.0, score))
    
    def _assess_structure(
        self, 
        document: Document, 
        semantic_elements: Optional[List[SemanticElement]]
    ) -> float:
        """
        Assess document structure (15% of total score).
        
        Measures structural organization:
        - Header hierarchy
        - Logical flow
        - Section organization
        - Navigation aids
        """
        score = 40.0  # Base score
        content = document.content
        
        # Extract semantic elements if needed
        if semantic_elements is None:
            from .semantic_analyzer import SemanticAnalyzer
            analyzer = SemanticAnalyzer()
            semantic_elements = analyzer.extract_semantic_elements(document)
        
        headers = [elem for elem in semantic_elements if elem.type == ElementType.HEADER]
        
        # Header hierarchy assessment
        if headers:
            header_levels = [elem.metadata.get('level', 1) for elem in headers]
            
            # Starts with H1
            if header_levels and header_levels[0] == 1:
                score += 15.0
            
            # No level skipping
            level_skips = sum(1 for i in range(1, len(header_levels))
                            if header_levels[i] > header_levels[i-1] + 1)
            if level_skips == 0:
                score += 15.0
            else:
                score -= level_skips * 5.0
            
            # Appropriate number of headers for content length
            words = len(content.split())
            headers_per_100_words = len(headers) / (words / 100) if words > 0 else 0
            if 0.5 <= headers_per_100_words <= 2.0:
                score += 10.0  # Good header density
        
        # Logical flow assessment
        paragraphs = [elem for elem in semantic_elements if elem.type == ElementType.PARAGRAPH]
        if len(paragraphs) >= 2:
            # Check for reasonable paragraph distribution
            score += 10.0
        
        # Navigation aids
        links = [elem for elem in semantic_elements if elem.type == ElementType.LINK]
        if links and len(content) > 1000:
            score += 5.0   # Has links in longer documents
        
        # Table of contents indicators
        toc_indicators = ['table of contents', 'contents:', '## contents', '# contents']
        if any(indicator in content.lower() for indicator in toc_indicators):
            score += 5.0
        
        return min(100.0, max(0.0, score))
    
    def _assess_technical_accuracy(self, document: Document) -> float:
        """
        Assess technical accuracy (15% of total score).
        
        Measures technical content quality:
        - Code syntax correctness
        - Technical terminology usage
        - Factual consistency
        - Reference accuracy
        """
        score = 70.0  # Base score (neutral for non-technical content)
        content = document.content
        
        # Code block assessment
        code_blocks = re.findall(r'```(\w*)\n(.*?)\n```', content, re.DOTALL)
        if code_blocks:
            valid_code_blocks = 0
            total_code_blocks = len(code_blocks)
            
            for lang, code in code_blocks:
                if self._assess_code_syntax(lang, code):
                    valid_code_blocks += 1
            
            if total_code_blocks > 0:
                code_accuracy = valid_code_blocks / total_code_blocks
                score += code_accuracy * 20.0  # Up to 20 points for code accuracy
        
        # Technical terminology assessment
        technical_terms = self._extract_technical_terms(content)
        if technical_terms:
            # Check for proper technical term usage
            proper_usage = self._assess_technical_term_usage(technical_terms, content)
            score += proper_usage * 10.0  # Up to 10 points
        
        # Reference and link validity (basic check)
        urls = re.findall(r'https?://[^\s\)]+', content)
        if urls:
            # Basic URL format validation
            valid_urls = sum(1 for url in urls if self._is_valid_url_format(url))
            if urls:
                url_accuracy = valid_urls / len(urls)
                score -= (1.0 - url_accuracy) * 5.0  # Penalty for invalid URLs
        
        return min(100.0, max(0.0, score))
    
    def _apply_document_type_adjustments(
        self,
        doc_type: DocumentType,
        completeness: float,
        clarity: float,
        consistency: float,
        structure: float,
        technical_accuracy: float
    ) -> Tuple[float, float, float, float, float]:
        """Apply document type-specific score adjustments."""
        
        if doc_type == DocumentType.API_DOCUMENTATION:
            # API docs should prioritize technical accuracy and structure
            technical_accuracy = min(100.0, technical_accuracy * 1.1)
            structure = min(100.0, structure * 1.05)
            
        elif doc_type == DocumentType.USER_GUIDE:
            # User guides should prioritize clarity and completeness
            clarity = min(100.0, clarity * 1.1)
            completeness = min(100.0, completeness * 1.05)
            
        elif doc_type == DocumentType.TECHNICAL_SPEC:
            # Technical specs need high accuracy and consistency
            technical_accuracy = min(100.0, technical_accuracy * 1.15)
            consistency = min(100.0, consistency * 1.1)
            
        elif doc_type == DocumentType.README:
            # READMEs should be clear and complete
            clarity = min(100.0, clarity * 1.05)
            completeness = min(100.0, completeness * 1.05)
            
        elif doc_type == DocumentType.TUTORIAL:
            # Tutorials need clarity and good structure
            clarity = min(100.0, clarity * 1.1)
            structure = min(100.0, structure * 1.05)
        
        return completeness, clarity, consistency, structure, technical_accuracy
    
    def _create_minimal_score(self) -> QualityScore:
        """Create minimal quality score for invalid/empty documents."""
        return QualityScore(
            overall=0.0,
            completeness=0.0,
            clarity=0.0,
            consistency=0.0,
            structure=0.0,
            technical_accuracy=0.0
        )
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _count_syllables(self, word: str) -> int:
        """Estimate syllable count for a word."""
        word = word.lower()
        vowels = 'aeiouy'
        syllables = 0
        prev_was_vowel = False
        
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_was_vowel:
                syllables += 1
            prev_was_vowel = is_vowel
        
        # Handle silent e
        if word.endswith('e') and syllables > 1:
            syllables -= 1
        
        return max(1, syllables)  # Every word has at least 1 syllable
    
    def _extract_technical_terms(self, content: str) -> List[str]:
        """Extract technical terms from content."""
        # Technical term patterns
        patterns = [
            r'\b[A-Z][A-Z0-9_]{2,}\b',  # ACRONYMS
            r'\b[a-z_]+_[a-z_]+\b',     # snake_case
            r'\b[A-Z][a-z]+(?:[A-Z][a-z]*)*\b'  # PascalCase
        ]
        
        terms = []
        for pattern in patterns:
            terms.extend(re.findall(pattern, content))
        
        return list(set(terms))  # Remove duplicates
    
    def _detect_term_variations(self, terms: List[str]) -> int:
        """Detect variations in technical term usage."""
        # Simplified: look for terms that might be variations of each other
        variations = 0
        
        for i, term1 in enumerate(terms):
            for term2 in terms[i+1:]:
                # Check if terms are similar (might be variations)
                if self._are_similar_terms(term1, term2):
                    variations += 1
        
        return variations
    
    def _are_similar_terms(self, term1: str, term2: str) -> bool:
        """Check if two terms might be variations of each other."""
        # Simple similarity check
        term1_lower = term1.lower()
        term2_lower = term2.lower()
        
        # Check if one contains the other
        if term1_lower in term2_lower or term2_lower in term1_lower:
            return len(term1) > 2 and len(term2) > 2  # Only for substantial terms
        
        return False
    
    def _analyze_tone_consistency(self, content: str) -> float:
        """Analyze tone consistency (simplified)."""
        # Check for consistent use of person (1st, 2nd, 3rd)
        first_person = len(re.findall(r'\b(I|we|our|us)\b', content, re.IGNORECASE))
        second_person = len(re.findall(r'\byou\b', content, re.IGNORECASE))
        
        total_words = len(content.split())
        if total_words == 0:
            return 0.5
        
        # Prefer consistent voice (not mixing too much)
        person_ratio = max(first_person, second_person) / total_words
        
        if person_ratio <= 0.02:  # Low personal pronouns (formal)
            return 0.8
        elif person_ratio <= 0.05:  # Moderate use
            return 0.6
        else:  # High use - check if consistent
            if abs(first_person - second_person) <= 2:
                return 0.7  # Consistent personal tone
            else:
                return 0.3  # Inconsistent tone
    
    def _assess_code_syntax(self, language: str, code: str) -> bool:
        """Basic code syntax assessment."""
        if not code or not code.strip():
            return False
        
        # Basic syntax checks for common languages
        code = code.strip()
        
        if language.lower() == 'python':
            # Check for basic Python syntax issues
            if code.count('(') != code.count(')'):
                return False
            if code.count('[') != code.count(']'):
                return False
            if code.count('{') != code.count('}'):
                return False
        
        elif language.lower() in ['javascript', 'js']:
            # Check for basic JavaScript syntax
            if code.count('(') != code.count(')'):
                return False
            if code.count('{') != code.count('}'):
                return False
            if not code.endswith((';', '}', ')', ']')):
                return False  # Should end with proper terminator
        
        # If we don't recognize the language, assume it's valid
        return True
    
    def _assess_technical_term_usage(self, terms: List[str], content: str) -> float:
        """Assess proper technical term usage."""
        if not terms:
            return 0.5
        
        # Check if technical terms are properly introduced or explained
        explained_terms = 0
        
        for term in terms:
            # Look for explanations or definitions near the term
            term_positions = [m.start() for m in re.finditer(re.escape(term), content)]
            
            for pos in term_positions:
                # Check context around the term
                start = max(0, pos - 100)
                end = min(len(content), pos + len(term) + 100)
                context = content[start:end].lower()
                
                # Look for definition indicators
                if any(indicator in context for indicator in ['is a', 'refers to', 'means', ':']):
                    explained_terms += 1
                    break  # Count each term only once
        
        return explained_terms / len(terms) if terms else 0.5
    
    def _is_valid_url_format(self, url: str) -> bool:
        """Basic URL format validation."""
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(url_pattern, url))
    
    def _identify_strengths(self, score: QualityScore) -> List[str]:
        """Identify quality strengths based on scores."""
        strengths = []
        
        if score.overall >= self.excellence_threshold:
            strengths.append("Excellent overall quality")
        elif score.overall >= self.quality_gate:
            strengths.append("Good overall quality meets standards")
        
        # Individual dimension strengths
        if score.completeness >= 85:
            strengths.append("Comprehensive and complete information")
        if score.clarity >= 85:
            strengths.append("Clear and understandable content")
        if score.consistency >= 85:
            strengths.append("Consistent style and terminology")
        if score.structure >= 85:
            strengths.append("Well-organized structure")
        if score.technical_accuracy >= 85:
            strengths.append("High technical accuracy")
        
        return strengths if strengths else ["Content has potential for improvement"]
    
    def _identify_weaknesses(self, score: QualityScore) -> List[str]:
        """Identify quality weaknesses based on scores."""
        weaknesses = []
        
        if score.overall < self.quality_gate:
            weaknesses.append(f"Overall quality below {self.quality_gate}% threshold")
        
        # Individual dimension weaknesses
        if score.completeness < 70:
            weaknesses.append("Information appears incomplete")
        if score.clarity < 70:
            weaknesses.append("Content could be clearer")
        if score.consistency < 70:
            weaknesses.append("Inconsistent style or terminology")
        if score.structure < 70:
            weaknesses.append("Poor document organization")
        if score.technical_accuracy < 70:
            weaknesses.append("Technical content needs review")
        
        return weaknesses
    
    def _generate_recommendations(self, score: QualityScore, document: Document) -> List[str]:
        """Generate improvement recommendations based on scores."""
        recommendations = []
        
        # Overall recommendations
        if score.overall < self.quality_gate:
            recommendations.append(f"Focus on improving overall quality to meet {self.quality_gate}% threshold")
        
        # Dimension-specific recommendations
        if score.completeness < 75:
            recommendations.append("Add more detailed information and examples")
        if score.clarity < 75:
            recommendations.append("Simplify language and improve readability")
        if score.consistency < 75:
            recommendations.append("Standardize terminology and formatting")
        if score.structure < 75:
            recommendations.append("Improve document organization with headers and sections")
        if score.technical_accuracy < 75:
            recommendations.append("Review and validate technical content")
        
        # Document type specific recommendations
        if document.type == DocumentType.API_DOCUMENTATION and score.technical_accuracy < 85:
            recommendations.append("Add more code examples and technical details")
        elif document.type == DocumentType.USER_GUIDE and score.clarity < 85:
            recommendations.append("Focus on user-friendly language and step-by-step guidance")
        
        return recommendations if recommendations else ["Continue maintaining current quality standards"]
    
    def _calculate_detailed_metrics(self, document: Document) -> Dict[str, float]:
        """Calculate detailed metrics for analysis."""
        content = document.content
        words = content.split()
        sentences = self._split_into_sentences(content)
        
        return {
            'word_count': len(words),
            'sentence_count': len(sentences),
            'paragraph_count': len(content.split('\n\n')),
            'avg_words_per_sentence': len(words) / len(sentences) if sentences else 0,
            'reading_time_minutes': len(words) / 200,  # Assume 200 WPM reading speed
            'technical_term_count': len(self._extract_technical_terms(content)),
            'code_block_count': len(re.findall(r'```', content)) // 2,
            'header_count': len(re.findall(r'^#+\s', content, re.MULTILINE))
        }
    
    def _load_readability_constants(self) -> Dict[str, float]:
        """Load constants for readability calculations."""
        return {
            'flesch_kincaid_age_constant': 206.835,
            'flesch_kincaid_asl_weight': 1.015,
            'flesch_kincaid_asw_weight': 84.6
        }
    
    def _load_technical_indicators(self) -> Set[str]:
        """Load technical indicator terms."""
        return {
            'api', 'sdk', 'framework', 'library', 'function', 'method', 'class',
            'variable', 'parameter', 'argument', 'return', 'exception', 'error',
            'database', 'server', 'client', 'request', 'response', 'endpoint'
        }