"""
M003 MIAIR Engine - Entropy Calculator

Implements Shannon entropy calculation with fractal-time scaling.

Mathematical Formula: S = -Σ[p(xi) × log2(p(xi))] × f(Tx)

Where:
- p(xi) = probability of semantic element type i
- f(Tx) = fractal-time scaling factor for iteration x
- S = normalized entropy score (0.0 to 1.0)

Key Features:
- Accurate Shannon entropy calculation
- Fractal-time scaling for iterative optimization
- Probability distribution analysis
- Edge case handling (empty documents, single elements)
- Performance optimized for real-time use
"""

import math
import re
from typing import List, Dict, Any, Set, Tuple
from collections import Counter
import logging

from .models import Document, SemanticElement, ElementType


logger = logging.getLogger(__name__)


class EntropyCalculator:
    """
    Implements Shannon entropy calculation with fractal-time scaling.
    
    Core mathematical implementation of the MIAIR entropy formula:
    S = -Σ[p(xi) × log2(p(xi))] × f(Tx)
    """
    
    def __init__(self):
        """Initialize entropy calculator with configuration."""
        self.min_probability = 1e-10  # Avoid log(0) errors
        self.max_content_length = 1_000_000  # 1MB safety limit
        
        # Compiled regex patterns for semantic element extraction
        self._patterns = self._compile_patterns()
        
        logger.debug("EntropyCalculator initialized with min_probability=%.2e", self.min_probability)
    
    def calculate_entropy(
        self,
        document: Document,
        iteration: int = 0
    ) -> float:
        """
        Calculate Shannon entropy for document.
        
        Args:
            document: Document to analyze
            iteration: Current iteration for fractal scaling (default: 0)
            
        Returns:
            Entropy score between 0.0 (highly ordered) and 1.0 (maximum disorder)
            
        Raises:
            ValueError: If document content is invalid
        """
        logger.debug(f"Calculating entropy for document {document.id}, iteration {iteration}")
        
        # Validate input
        if not document.content or not document.content.strip():
            logger.warning(f"Empty document content for {document.id}")
            return 1.0  # Maximum entropy for empty document
        
        if len(document.content) > self.max_content_length:
            raise ValueError(f"Document content too large: {len(document.content)} bytes")
        
        # Extract semantic elements for probability calculation
        elements = self._extract_semantic_elements(document.content)
        
        if not elements:
            logger.warning(f"No semantic elements found in document {document.id}")
            return 1.0  # Maximum entropy if no elements found
        
        # Calculate probability distribution
        prob_dist = self.calculate_probability_distribution(elements)
        
        if not prob_dist:
            return 1.0
        
        # Calculate Shannon entropy
        entropy = self._calculate_shannon_entropy(prob_dist)
        
        # Apply fractal-time scaling
        scaled_entropy = self.fractal_time_scaling(entropy, iteration)
        
        # Ensure bounds [0.0, 1.0]
        final_entropy = max(0.0, min(1.0, scaled_entropy))
        
        logger.debug(
            f"Document {document.id}: raw_entropy={entropy:.4f}, "
            f"scaled_entropy={scaled_entropy:.4f}, final={final_entropy:.4f}"
        )
        
        return final_entropy
    
    def calculate_probability_distribution(
        self,
        elements: List[SemanticElement]
    ) -> Dict[str, float]:
        """
        Calculate probability distribution of semantic elements.
        
        Args:
            elements: List of semantic elements
            
        Returns:
            Dictionary mapping element types to probabilities
        """
        if not elements:
            return {}
        
        # Count element occurrences by type
        element_counts = Counter(elem.type.value if isinstance(elem.type, ElementType) else str(elem.type) 
                               for elem in elements)
        total_count = sum(element_counts.values())
        
        if total_count == 0:
            return {}
        
        # Calculate probabilities
        prob_dist = {
            elem_type: count / total_count
            for elem_type, count in element_counts.items()
        }
        
        logger.debug(f"Probability distribution: {prob_dist}")
        return prob_dist
    
    def fractal_time_scaling(
        self,
        entropy: float,
        iteration: int
    ) -> float:
        """
        Apply fractal-time scaling factor f(Tx).
        
        Reduces entropy impact as iterations increase, modeling
        diminishing returns in optimization.
        
        Formula: f(Tx) = 1 / (1 + log(1 + iteration))
        
        Args:
            entropy: Base entropy value (0.0 to 1.0)
            iteration: Current iteration number (>= 0)
            
        Returns:
            Scaled entropy value
        """
        if iteration < 0:
            iteration = 0
        
        # Fractal scaling function
        # f(Tx) = 1 / (1 + log(1 + iteration))
        scaling_factor = 1.0 / (1.0 + math.log(1.0 + iteration))
        
        scaled_entropy = entropy * scaling_factor
        
        logger.debug(f"Fractal scaling: iteration={iteration}, factor={scaling_factor:.4f}")
        return scaled_entropy
    
    def _calculate_shannon_entropy(self, prob_dist: Dict[str, float]) -> float:
        """
        Calculate Shannon entropy from probability distribution.
        
        Formula: H = -Σ[p(xi) × log2(p(xi))]
        
        Args:
            prob_dist: Probability distribution
            
        Returns:
            Normalized Shannon entropy (0.0 to 1.0)
        """
        if not prob_dist:
            return 1.0
        
        # Calculate raw Shannon entropy
        entropy = 0.0
        for probability in prob_dist.values():
            if probability > self.min_probability:
                entropy -= probability * math.log2(probability)
        
        # Normalize to [0, 1] range
        # Maximum entropy occurs when all elements are equally distributed
        if len(prob_dist) > 1:
            max_entropy = math.log2(len(prob_dist))
            normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0.0
        else:
            # Single element type = perfect order = minimum entropy
            normalized_entropy = 0.0
        
        return normalized_entropy
    
    def _extract_semantic_elements(self, content: str) -> List[SemanticElement]:
        """
        Extract semantic elements from document content.
        
        This is a simplified implementation for Pass 1.
        Will be enhanced in subsequent passes.
        
        Args:
            content: Document content string
            
        Returns:
            List of semantic elements
        """
        elements = []
        position = 0
        
        # Extract headers (markdown-style)
        for match in self._patterns['headers'].finditer(content):
            elements.append(SemanticElement(
                type=ElementType.HEADER,
                content=match.group().strip(),
                position=match.start(),
                importance=0.9,  # Headers are important
                metadata={'level': len(match.group(1))}
            ))
        
        # Extract code blocks
        for match in self._patterns['code_blocks'].finditer(content):
            elements.append(SemanticElement(
                type=ElementType.CODE_BLOCK,
                content=match.group().strip(),
                position=match.start(),
                importance=0.7,
                metadata={'language': match.group(1) if match.group(1) else 'unknown'}
            ))
        
        # Extract list items
        for match in self._patterns['list_items'].finditer(content):
            elements.append(SemanticElement(
                type=ElementType.LIST_ITEM,
                content=match.group().strip(),
                position=match.start(),
                importance=0.6
            ))
        
        # Extract links
        for match in self._patterns['links'].finditer(content):
            elements.append(SemanticElement(
                type=ElementType.LINK,
                content=match.group().strip(),
                position=match.start(),
                importance=0.5,
                metadata={'url': match.group(2), 'text': match.group(1)}
            ))
        
        # Extract technical terms (basic heuristics)
        for match in self._patterns['technical_terms'].finditer(content):
            elements.append(SemanticElement(
                type=ElementType.TECHNICAL_TERM,
                content=match.group().strip(),
                position=match.start(),
                importance=0.6
            ))
        
        # Extract emphasis (bold/italic)
        for match in self._patterns['emphasis'].finditer(content):
            elements.append(SemanticElement(
                type=ElementType.EMPHASIS,
                content=match.group().strip(),
                position=match.start(),
                importance=0.4
            ))
        
        # Extract paragraphs (split by double newlines)
        paragraphs = re.split(r'\n\s*\n', content)
        for i, para in enumerate(paragraphs):
            if para.strip():
                elements.append(SemanticElement(
                    type=ElementType.PARAGRAPH,
                    content=para.strip(),
                    position=content.find(para),
                    importance=0.3,
                    metadata={'paragraph_index': i}
                ))
        
        # Sort by position for consistent ordering
        elements.sort(key=lambda x: x.position)
        
        logger.debug(f"Extracted {len(elements)} semantic elements")
        return elements
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for semantic element extraction."""
        return {
            # Markdown headers
            'headers': re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE),
            
            # Code blocks (```language or ```)
            'code_blocks': re.compile(r'```(\w+)?\n(.*?)\n```', re.DOTALL),
            
            # List items (- or * or numbers)
            'list_items': re.compile(r'^[\s]*[-*+]\s+(.+)$|^\s*\d+\.\s+(.+)$', re.MULTILINE),
            
            # Links [text](url)
            'links': re.compile(r'\[([^\]]+)\]\(([^)]+)\)'),
            
            # Technical terms (heuristic: capitalized words, acronyms, words with underscores)
            'technical_terms': re.compile(r'\b[A-Z][A-Z0-9_]{2,}\b|\b[a-z_]+_[a-z_]+\b|\b[A-Z][a-z]+(?:[A-Z][a-z]*)*\b'),
            
            # Emphasis (bold **text** or *text*, italic)
            'emphasis': re.compile(r'\*\*([^*]+)\*\*|\*([^*]+)\*|__([^_]+)__|_([^_]+)_'),
        }
    
    def get_entropy_analysis(self, document: Document) -> Dict[str, Any]:
        """
        Get detailed entropy analysis for debugging and optimization.
        
        Args:
            document: Document to analyze
            
        Returns:
            Dictionary with detailed entropy analysis
        """
        elements = self._extract_semantic_elements(document.content)
        prob_dist = self.calculate_probability_distribution(elements)
        entropy = self.calculate_entropy(document)
        
        # Calculate element type distribution
        type_counts = Counter(elem.type.value for elem in elements)
        
        # Calculate diversity metrics
        unique_types = len(set(elem.type for elem in elements))
        total_elements = len(elements)
        diversity_ratio = unique_types / total_elements if total_elements > 0 else 0
        
        return {
            'entropy': entropy,
            'total_elements': total_elements,
            'unique_element_types': unique_types,
            'diversity_ratio': diversity_ratio,
            'probability_distribution': prob_dist,
            'element_type_counts': dict(type_counts),
            'content_length': len(document.content),
            'content_lines': len(document.content.splitlines())
        }