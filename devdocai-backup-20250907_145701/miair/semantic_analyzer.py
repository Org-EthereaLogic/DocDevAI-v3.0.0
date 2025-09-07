"""
M003 MIAIR Engine - Semantic Analyzer

Extracts and analyzes semantic elements from documents for entropy calculation.

Key Features:
- Semantic element extraction (headers, paragraphs, code, lists, etc.)
- Pattern identification and analysis
- Coherence measurement
- Structure analysis
- Importance scoring
- Document quality assessment

This module provides the semantic foundation for MIAIR's entropy calculations
by breaking down documents into meaningful components and analyzing their
relationships and patterns.
"""

import re
import logging
from typing import List, Dict, Any, Set, Tuple, Optional
from collections import Counter, defaultdict
from dataclasses import dataclass
import math

from .models import Document, SemanticElement, ElementType


logger = logging.getLogger(__name__)


@dataclass
class StructureAnalysis:
    """Analysis of document structure."""
    header_hierarchy: List[int]  # Header levels found
    paragraph_count: int
    list_count: int
    code_block_count: int
    link_count: int
    structure_score: float  # 0.0 to 1.0
    issues: List[str]  # Structural issues found


@dataclass 
class PatternAnalysis:
    """Analysis of patterns in semantic elements."""
    repetitions: Dict[str, int]  # Repeated content patterns
    structure_issues: List[str]  # Structure-related issues
    missing_elements: List[str]  # Expected but missing elements
    coherence_score: float  # 0.0 to 1.0


class SemanticAnalyzer:
    """
    Extracts and analyzes semantic elements from documents.
    
    Provides comprehensive analysis of document structure, patterns,
    and semantic relationships for entropy calculation and optimization.
    """
    
    def __init__(self):
        """Initialize semantic analyzer with patterns and configurations."""
        self.patterns = self._compile_patterns()
        self.stopwords = self._load_stopwords()
        
        # Analysis thresholds and parameters
        self.min_paragraph_length = 10  # Minimum chars for paragraph
        self.max_repetition_threshold = 3  # Max repetitions before flagging
        self.coherence_window_size = 5  # Window size for coherence analysis
        
        logger.debug("SemanticAnalyzer initialized")
    
    def extract_semantic_elements(
        self,
        document: Document
    ) -> List[SemanticElement]:
        """
        Extract all semantic elements from document.
        
        Args:
            document: Document to analyze
            
        Returns:
            List of semantic elements with metadata and importance scores
        """
        logger.debug(f"Extracting semantic elements from document {document.id}")
        
        elements = []
        content = document.content
        
        if not content or not content.strip():
            logger.warning(f"Empty content in document {document.id}")
            return elements
        
        # Extract different types of elements
        elements.extend(self._extract_structure_elements(content))
        elements.extend(self._extract_content_elements(content))
        elements.extend(self._extract_technical_elements(content))
        elements.extend(self._extract_formatting_elements(content))
        
        # Sort by position and calculate importance scores
        elements.sort(key=lambda x: x.position)
        self._calculate_importance_scores(elements, document)
        
        logger.debug(f"Extracted {len(elements)} semantic elements")
        return elements
    
    def identify_patterns(
        self,
        elements: List[SemanticElement]
    ) -> PatternAnalysis:
        """
        Identify patterns in semantic elements.
        
        Args:
            elements: List of semantic elements to analyze
            
        Returns:
            PatternAnalysis with identified patterns and issues
        """
        logger.debug("Identifying patterns in semantic elements")
        
        # Find repetitions
        repetitions = self._find_repetitions(elements)
        
        # Analyze structure issues
        structure_issues = self._analyze_structure_issues(elements)
        
        # Identify missing elements
        missing_elements = self._identify_missing_elements(elements)
        
        # Calculate coherence score
        coherence_score = self._calculate_coherence(elements)
        
        return PatternAnalysis(
            repetitions=repetitions,
            structure_issues=structure_issues,
            missing_elements=missing_elements,
            coherence_score=coherence_score
        )
    
    def analyze_coherence(
        self,
        elements: List[SemanticElement]
    ) -> float:
        """
        Analyze document coherence based on element relationships.
        
        Coherence measures how well elements flow together and support
        the document's overall purpose.
        
        Args:
            elements: List of semantic elements
            
        Returns:
            Coherence score between 0.0 (incoherent) and 1.0 (highly coherent)
        """
        if not elements:
            return 0.0
        
        # Analyze element transitions
        transition_score = self._analyze_transitions(elements)
        
        # Analyze topic consistency
        topic_score = self._analyze_topic_consistency(elements)
        
        # Analyze structural coherence
        structure_score = self._analyze_structural_coherence(elements)
        
        # Calculate weighted average
        coherence = (
            transition_score * 0.4 +  # How well elements flow
            topic_score * 0.3 +       # Topic consistency
            structure_score * 0.3     # Structural organization
        )
        
        return min(1.0, max(0.0, coherence))
    
    def analyze_structure(
        self,
        document: Document
    ) -> StructureAnalysis:
        """
        Analyze document structure and organization.
        
        Args:
            document: Document to analyze
            
        Returns:
            StructureAnalysis with structural metrics and issues
        """
        content = document.content
        elements = self.extract_semantic_elements(document)
        
        # Analyze header hierarchy
        headers = [e for e in elements if e.type == ElementType.HEADER]
        header_hierarchy = []
        for header in headers:
            level = header.metadata.get('level', 1)
            header_hierarchy.append(level)
        
        # Count element types
        element_counts = Counter(e.type for e in elements)
        paragraph_count = element_counts.get(ElementType.PARAGRAPH, 0)
        list_count = element_counts.get(ElementType.LIST_ITEM, 0)
        code_block_count = element_counts.get(ElementType.CODE_BLOCK, 0)
        link_count = element_counts.get(ElementType.LINK, 0)
        
        # Calculate structure score
        structure_score = self._calculate_structure_score(
            header_hierarchy, element_counts, len(content)
        )
        
        # Identify structural issues
        issues = self._identify_structure_issues(
            header_hierarchy, element_counts, content
        )
        
        return StructureAnalysis(
            header_hierarchy=header_hierarchy,
            paragraph_count=paragraph_count,
            list_count=list_count,
            code_block_count=code_block_count,
            link_count=link_count,
            structure_score=structure_score,
            issues=issues
        )
    
    def _extract_structure_elements(self, content: str) -> List[SemanticElement]:
        """Extract structural elements (headers, lists)."""
        elements = []
        
        # Extract headers
        for match in self.patterns['headers'].finditer(content):
            level = len(match.group(1))  # Count # symbols
            header_text = match.group(2).strip()
            
            elements.append(SemanticElement(
                type=ElementType.HEADER,
                content=header_text,
                position=match.start(),
                importance=1.0 - (level - 1) * 0.1,  # Higher level = higher importance
                metadata={
                    'level': level,
                    'text': header_text,
                    'full_match': match.group(0)
                }
            ))
        
        # Extract list items
        for match in self.patterns['list_items'].finditer(content):
            item_text = (match.group(1) or match.group(2) or "").strip()
            
            elements.append(SemanticElement(
                type=ElementType.LIST_ITEM,
                content=item_text,
                position=match.start(),
                importance=0.6,
                metadata={
                    'text': item_text,
                    'is_numbered': match.group(0).strip()[0].isdigit()
                }
            ))
        
        return elements
    
    def _extract_content_elements(self, content: str) -> List[SemanticElement]:
        """Extract content elements (paragraphs, definitions)."""
        elements = []
        
        # Extract paragraphs (split by double newlines)
        paragraphs = re.split(r'\n\s*\n', content)
        current_pos = 0
        
        for i, para in enumerate(paragraphs):
            para = para.strip()
            if len(para) >= self.min_paragraph_length:
                # Find actual position in content
                pos = content.find(para, current_pos)
                if pos >= 0:
                    elements.append(SemanticElement(
                        type=ElementType.PARAGRAPH,
                        content=para,
                        position=pos,
                        importance=0.5,
                        metadata={
                            'index': i,
                            'word_count': len(para.split()),
                            'sentence_count': len(re.split(r'[.!?]+', para))
                        }
                    ))
                    current_pos = pos + len(para)
        
        # Extract definitions (lines starting with terms followed by colon)
        for match in self.patterns['definitions'].finditer(content):
            term = match.group(1).strip()
            definition = match.group(2).strip()
            
            elements.append(SemanticElement(
                type=ElementType.DEFINITION,
                content=f"{term}: {definition}",
                position=match.start(),
                importance=0.8,
                metadata={
                    'term': term,
                    'definition': definition
                }
            ))
        
        return elements
    
    def _extract_technical_elements(self, content: str) -> List[SemanticElement]:
        """Extract technical elements (code, specifications)."""
        elements = []
        
        # Extract code blocks
        for match in self.patterns['code_blocks'].finditer(content):
            language = match.group(1) or 'unknown'
            code = match.group(2).strip()
            
            elements.append(SemanticElement(
                type=ElementType.CODE_BLOCK,
                content=code,
                position=match.start(),
                importance=0.7,
                metadata={
                    'language': language,
                    'line_count': len(code.splitlines()),
                    'char_count': len(code)
                }
            ))
        
        # Extract inline code
        for match in self.patterns['inline_code'].finditer(content):
            code = match.group(1).strip()
            
            elements.append(SemanticElement(
                type=ElementType.CODE_BLOCK,
                content=code,
                position=match.start(),
                importance=0.5,
                metadata={
                    'inline': True,
                    'language': 'unknown'
                }
            ))
        
        # Extract technical terms
        for match in self.patterns['technical_terms'].finditer(content):
            term = match.group(0)
            
            elements.append(SemanticElement(
                type=ElementType.TECHNICAL_TERM,
                content=term,
                position=match.start(),
                importance=0.6,
                metadata={'term': term}
            ))
        
        return elements
    
    def _extract_formatting_elements(self, content: str) -> List[SemanticElement]:
        """Extract formatting elements (links, emphasis)."""
        elements = []
        
        # Extract links
        for match in self.patterns['links'].finditer(content):
            text = match.group(1)
            url = match.group(2)
            
            elements.append(SemanticElement(
                type=ElementType.LINK,
                content=text,
                position=match.start(),
                importance=0.5,
                metadata={
                    'text': text,
                    'url': url,
                    'is_external': url.startswith('http')
                }
            ))
        
        # Extract emphasis
        for match in self.patterns['emphasis'].finditer(content):
            text = next(g for g in match.groups() if g is not None)
            
            elements.append(SemanticElement(
                type=ElementType.EMPHASIS,
                content=text,
                position=match.start(),
                importance=0.4,
                metadata={'text': text}
            ))
        
        return elements
    
    def _calculate_importance_scores(
        self, 
        elements: List[SemanticElement], 
        document: Document
    ) -> None:
        """Calculate and update importance scores for elements."""
        if not elements:
            return
        
        # Adjust importance based on position (earlier elements more important)
        total_length = len(document.content)
        
        for element in elements:
            # Position factor (0.8 to 1.0, earlier positions get higher scores)
            position_factor = 1.0 - (element.position / total_length) * 0.2
            
            # Length factor for content elements
            if element.type in [ElementType.PARAGRAPH, ElementType.CODE_BLOCK]:
                content_length = len(element.content)
                length_factor = min(1.0, content_length / 100)  # Normalize to reasonable length
                element.importance *= (length_factor * 0.3 + 0.7)  # Weighted by length
            
            # Apply position factor
            element.importance *= position_factor
            
            # Ensure bounds [0.0, 1.0]
            element.importance = max(0.0, min(1.0, element.importance))
    
    def _find_repetitions(self, elements: List[SemanticElement]) -> Dict[str, int]:
        """Find repeated content patterns."""
        content_counter = Counter()
        
        for element in elements:
            # Normalize content for comparison
            normalized = re.sub(r'\s+', ' ', element.content.lower().strip())
            if len(normalized) > 10:  # Only check substantial content
                content_counter[normalized] += 1
        
        # Return only items that repeat more than threshold
        repetitions = {
            content: count for content, count in content_counter.items()
            if count > self.max_repetition_threshold
        }
        
        return repetitions
    
    def _analyze_structure_issues(self, elements: List[SemanticElement]) -> List[str]:
        """Analyze and identify structure issues."""
        issues = []
        
        headers = [e for e in elements if e.type == ElementType.HEADER]
        paragraphs = [e for e in elements if e.type == ElementType.PARAGRAPH]
        
        # Check header hierarchy
        if headers:
            levels = [h.metadata.get('level', 1) for h in headers]
            if levels and levels[0] != 1:
                issues.append("Document doesn't start with H1 header")
            
            # Check for level skipping
            for i in range(1, len(levels)):
                if levels[i] > levels[i-1] + 1:
                    issues.append(f"Header level skipping detected (H{levels[i-1]} to H{levels[i]})")
        
        # Check paragraph lengths
        if paragraphs:
            short_paragraphs = sum(1 for p in paragraphs if len(p.content) < 50)
            if short_paragraphs > len(paragraphs) * 0.5:
                issues.append("Many paragraphs are too short (< 50 characters)")
        
        return issues
    
    def _identify_missing_elements(self, elements: List[SemanticElement]) -> List[str]:
        """Identify expected but missing elements."""
        missing = []
        element_types = set(e.type for e in elements)
        
        # Check for common missing elements in documentation
        if ElementType.HEADER not in element_types:
            missing.append("No headers found - consider adding section headers")
        
        if ElementType.PARAGRAPH not in element_types:
            missing.append("No paragraphs found - consider adding descriptive content")
        
        # Check for technical documentation elements
        has_code = ElementType.CODE_BLOCK in element_types
        has_tech_terms = ElementType.TECHNICAL_TERM in element_types
        
        if not has_code and not has_tech_terms:
            missing.append("No technical content found - consider adding examples or code")
        
        return missing
    
    def _calculate_coherence(self, elements: List[SemanticElement]) -> float:
        """Calculate coherence score based on element relationships."""
        if len(elements) < 2:
            return 1.0 if elements else 0.0
        
        coherence_scores = []
        
        # Analyze transitions between adjacent elements
        for i in range(len(elements) - 1):
            current = elements[i]
            next_elem = elements[i + 1]
            
            # Score based on logical flow
            transition_score = self._score_transition(current, next_elem)
            coherence_scores.append(transition_score)
        
        # Return average coherence
        return sum(coherence_scores) / len(coherence_scores) if coherence_scores else 0.0
    
    def _score_transition(self, elem1: SemanticElement, elem2: SemanticElement) -> float:
        """Score the transition between two elements."""
        # Good transitions
        good_transitions = [
            (ElementType.HEADER, ElementType.PARAGRAPH),
            (ElementType.PARAGRAPH, ElementType.LIST_ITEM),
            (ElementType.PARAGRAPH, ElementType.CODE_BLOCK),
            (ElementType.DEFINITION, ElementType.PARAGRAPH),
        ]
        
        # Poor transitions
        poor_transitions = [
            (ElementType.CODE_BLOCK, ElementType.HEADER),
            (ElementType.LIST_ITEM, ElementType.HEADER),
        ]
        
        transition = (elem1.type, elem2.type)
        
        if transition in good_transitions:
            return 1.0
        elif transition in poor_transitions:
            return 0.3
        else:
            return 0.7  # Neutral transitions
    
    def _analyze_transitions(self, elements: List[SemanticElement]) -> float:
        """Analyze transition quality between elements."""
        return self._calculate_coherence(elements)  # Reuse coherence calculation
    
    def _analyze_topic_consistency(self, elements: List[SemanticElement]) -> float:
        """Analyze topic consistency across elements."""
        # Simplified topic consistency based on technical term distribution
        tech_terms = [e for e in elements if e.type == ElementType.TECHNICAL_TERM]
        
        if not tech_terms:
            return 0.7  # Neutral score if no technical terms
        
        # Check distribution of terms
        term_positions = [t.position for t in tech_terms]
        if len(term_positions) < 2:
            return 0.5
        
        # Calculate term density consistency (simplified approach)
        # Good consistency = even distribution of technical terms
        position_gaps = []
        for i in range(1, len(term_positions)):
            gap = term_positions[i] - term_positions[i-1]
            position_gaps.append(gap)
        
        if not position_gaps:
            return 0.5
        
        # Calculate variance in gaps (lower variance = better consistency)
        avg_gap = sum(position_gaps) / len(position_gaps)
        variance = sum((gap - avg_gap) ** 2 for gap in position_gaps) / len(position_gaps)
        
        # Convert variance to consistency score (0-1)
        consistency = 1.0 / (1.0 + math.sqrt(variance / avg_gap)) if avg_gap > 0 else 0.5
        
        return min(1.0, max(0.0, consistency))
    
    def _analyze_structural_coherence(self, elements: List[SemanticElement]) -> float:
        """Analyze structural coherence (header hierarchy, organization)."""
        headers = [e for e in elements if e.type == ElementType.HEADER]
        
        if not headers:
            return 0.5  # Neutral score if no headers
        
        levels = [h.metadata.get('level', 1) for h in headers]
        
        # Check for proper hierarchy
        hierarchy_score = 1.0
        for i in range(1, len(levels)):
            # Penalize level skipping
            if levels[i] > levels[i-1] + 1:
                hierarchy_score -= 0.2
            
            # Reward proper progression
            if levels[i] == levels[i-1] or levels[i] == levels[i-1] + 1:
                hierarchy_score += 0.1
        
        return min(1.0, max(0.0, hierarchy_score))
    
    def _calculate_structure_score(
        self, 
        header_hierarchy: List[int], 
        element_counts: Counter,
        content_length: int
    ) -> float:
        """Calculate overall structure score."""
        score = 0.5  # Base score
        
        # Header organization
        if header_hierarchy:
            if header_hierarchy[0] == 1:  # Starts with H1
                score += 0.1
            
            # Check hierarchy consistency
            hierarchy_issues = sum(
                1 for i in range(1, len(header_hierarchy))
                if header_hierarchy[i] > header_hierarchy[i-1] + 1
            )
            if hierarchy_issues == 0:
                score += 0.2
        
        # Content diversity
        unique_types = len(element_counts)
        if unique_types >= 4:  # Good variety of elements
            score += 0.2
        
        # Content balance
        total_elements = sum(element_counts.values())
        if total_elements > 0:
            paragraph_ratio = element_counts.get(ElementType.PARAGRAPH, 0) / total_elements
            if 0.3 <= paragraph_ratio <= 0.7:  # Good balance
                score += 0.1
        
        return min(1.0, max(0.0, score))
    
    def _identify_structure_issues(
        self, 
        header_hierarchy: List[int], 
        element_counts: Counter,
        content: str
    ) -> List[str]:
        """Identify structural issues in the document."""
        issues = []
        
        # Header issues
        if not header_hierarchy:
            issues.append("No headers found")
        elif header_hierarchy[0] != 1:
            issues.append("Document should start with H1 header")
        
        # Check for level skipping
        for i in range(1, len(header_hierarchy)):
            if header_hierarchy[i] > header_hierarchy[i-1] + 1:
                issues.append(f"Header level skipping: H{header_hierarchy[i-1]} to H{header_hierarchy[i]}")
        
        # Content issues
        if element_counts.get(ElementType.PARAGRAPH, 0) == 0:
            issues.append("No paragraphs found")
        
        if len(content) > 1000 and element_counts.get(ElementType.HEADER, 0) <= 1:
            issues.append("Long document with insufficient headers")
        
        return issues
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for element extraction."""
        return {
            # Headers: # Header or ## Header
            'headers': re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE),
            
            # Code blocks: ```lang\ncode\n```
            'code_blocks': re.compile(r'```(\w*)\n(.*?)\n```', re.DOTALL),
            
            # Inline code: `code`
            'inline_code': re.compile(r'`([^`]+)`'),
            
            # List items: - item or * item or 1. item
            'list_items': re.compile(r'^[\s]*[-*+]\s+(.+)$|^\s*\d+\.\s+(.+)$', re.MULTILINE),
            
            # Links: [text](url)
            'links': re.compile(r'\[([^\]]+)\]\(([^)]+)\)'),
            
            # Emphasis: **bold** or *italic*
            'emphasis': re.compile(r'\*\*([^*]+)\*\*|\*([^*]+)\*|__([^_]+)__|_([^_]+)_'),
            
            # Technical terms: CamelCase, ACRONYMS, snake_case
            'technical_terms': re.compile(r'\b[A-Z][A-Z0-9_]{2,}\b|\b[a-z_]+_[a-z_]+\b|\b[A-Z][a-z]+(?:[A-Z][a-z]*)*\b'),
            
            # Definitions: Term: Definition
            'definitions': re.compile(r'^([A-Z][^:]+):\s*(.+)$', re.MULTILINE),
        }
    
    def _load_stopwords(self) -> Set[str]:
        """Load common stopwords for text analysis."""
        return {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those'
        }