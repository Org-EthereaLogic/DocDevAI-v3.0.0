"""
MIAIR optimization engine for iterative document refinement.

Implements optimization strategies to improve document quality based on
entropy analysis and quality scores.
"""

import time
import copy
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import numpy as np

from .entropy import ShannonEntropyCalculator
from .scorer import QualityScorer, QualityMetrics, ScoringWeights


class OptimizationStrategy(Enum):
    """Available optimization strategies."""
    HILL_CLIMBING = "hill_climbing"
    SIMULATED_ANNEALING = "simulated_annealing"
    GRADIENT_BASED = "gradient_based"
    HYBRID = "hybrid"


@dataclass
class OptimizationConfig:
    """Configuration for optimization process."""
    strategy: OptimizationStrategy = OptimizationStrategy.HILL_CLIMBING
    max_iterations: int = 10
    target_quality: float = 0.85
    improvement_threshold: float = 0.01
    entropy_balance_weight: float = 0.3
    enable_caching: bool = True
    timeout_seconds: float = 30.0
    
    def __post_init__(self):
        """Validate configuration."""
        if not 0 <= self.target_quality <= 1:
            raise ValueError("target_quality must be between 0 and 1")
        if not 0 <= self.entropy_balance_weight <= 1:
            raise ValueError("entropy_balance_weight must be between 0 and 1")


@dataclass
class OptimizationResult:
    """Result of optimization process."""
    original_content: str
    optimized_content: str
    original_score: QualityMetrics
    optimized_score: QualityMetrics
    iterations: int
    improvements: List[Dict[str, Any]]
    success: bool
    elapsed_time: float
    
    def improvement_percentage(self) -> float:
        """Calculate overall improvement percentage."""
        if self.original_score.overall == 0:
            return 0.0
        return ((self.optimized_score.overall - self.original_score.overall) / 
                self.original_score.overall * 100)


class MIAIROptimizer:
    """
    Main optimization engine for document quality improvement.
    
    Uses entropy analysis and quality scoring to iteratively
    refine documents toward target quality threshold.
    """
    
    def __init__(self, 
                 config: Optional[OptimizationConfig] = None,
                 entropy_calculator: Optional[ShannonEntropyCalculator] = None,
                 quality_scorer: Optional[QualityScorer] = None):
        """
        Initialize optimizer with configuration and components.
        
        Args:
            config: Optimization configuration
            entropy_calculator: Entropy calculation component
            quality_scorer: Quality scoring component
        """
        self.config = config or OptimizationConfig()
        self.entropy_calc = entropy_calculator or ShannonEntropyCalculator()
        self.scorer = quality_scorer or QualityScorer()
        self._refinement_cache = {} if self.config.enable_caching else None
        self._init_refinement_strategies()
    
    def _init_refinement_strategies(self):
        """Initialize refinement strategies for different quality issues."""
        self.refinement_strategies = {
            'completeness': [
                self._add_missing_sections,
                self._expand_content,
                self._add_examples
            ],
            'clarity': [
                self._simplify_sentences,
                self._improve_structure,
                self._activate_voice
            ],
            'consistency': [
                self._standardize_terminology,
                self._fix_formatting,
                self._normalize_style
            ],
            'accuracy': [
                self._update_references,
                self._add_metadata,
                self._fix_technical_issues
            ]
        }
    
    def optimize_document(self, 
                         content: str,
                         metadata: Optional[Dict] = None) -> OptimizationResult:
        """
        Optimize a document to improve its quality score.
        
        Args:
            content: Document content to optimize
            metadata: Optional metadata for context
            
        Returns:
            OptimizationResult with optimized content and metrics
        """
        start_time = time.time()
        
        # Initial assessment
        original_score = self.scorer.score_document(content, metadata)
        original_entropy = self.entropy_calc.calculate_entropy(content, 'all')
        
        # Initialize optimization state
        current_content = content
        current_score = original_score
        improvements = []
        iteration = 0
        
        # Optimization loop
        while (iteration < self.config.max_iterations and
               current_score.overall < self.config.target_quality and
               time.time() - start_time < self.config.timeout_seconds):
            
            iteration += 1
            
            # Apply optimization strategy
            if self.config.strategy == OptimizationStrategy.HILL_CLIMBING:
                refined_content, improvement = self._hill_climbing_step(
                    current_content, current_score, metadata
                )
            elif self.config.strategy == OptimizationStrategy.GRADIENT_BASED:
                refined_content, improvement = self._gradient_based_step(
                    current_content, current_score, metadata
                )
            else:
                # Default to hill climbing
                refined_content, improvement = self._hill_climbing_step(
                    current_content, current_score, metadata
                )
            
            # Evaluate refinement
            refined_score = self.scorer.score_document(refined_content, metadata)
            
            # Check if improvement meets threshold
            score_improvement = refined_score.overall - current_score.overall
            
            if score_improvement >= self.config.improvement_threshold:
                # Accept refinement
                current_content = refined_content
                current_score = refined_score
                
                improvement['iteration'] = iteration
                improvement['score_improvement'] = score_improvement
                improvement['new_score'] = refined_score.overall
                improvements.append(improvement)
                
                # Check entropy balance
                refined_entropy = self.entropy_calc.calculate_entropy(refined_content, 'all')
                entropy_change = abs(refined_entropy.get('aggregate', 0) - 
                                   original_entropy.get('aggregate', 0))
                
                # Penalize excessive entropy change
                if entropy_change > 0.3:
                    # Apply entropy balance weight
                    current_score.overall *= (1 - self.config.entropy_balance_weight * entropy_change)
            else:
                # No significant improvement, try different strategy
                if iteration >= self.config.max_iterations // 2:
                    # Switch strategy midway if not making progress
                    break
        
        # Calculate final metrics
        elapsed_time = time.time() - start_time
        success = current_score.overall >= self.config.target_quality
        
        return OptimizationResult(
            original_content=content,
            optimized_content=current_content,
            original_score=original_score,
            optimized_score=current_score,
            iterations=iteration,
            improvements=improvements,
            success=success,
            elapsed_time=elapsed_time
        )
    
    def _hill_climbing_step(self,
                           content: str,
                           current_score: QualityMetrics,
                           metadata: Optional[Dict]) -> Tuple[str, Dict]:
        """
        Perform one hill climbing optimization step.
        
        Applies the best refinement from available strategies.
        """
        best_content = content
        best_improvement = 0.0
        best_strategy = None
        
        # Identify weakest dimension
        dimensions = {
            'completeness': current_score.completeness,
            'clarity': current_score.clarity,
            'consistency': current_score.consistency,
            'accuracy': current_score.accuracy
        }
        
        weakest_dimension = min(dimensions, key=dimensions.get)
        
        # Try refinement strategies for weakest dimension
        strategies = self.refinement_strategies.get(weakest_dimension, [])
        
        for strategy in strategies:
            try:
                # Apply refinement strategy
                refined_content = strategy(content, metadata)
                
                if refined_content and refined_content != content:
                    # Evaluate improvement
                    refined_score = self.scorer.score_document(refined_content, metadata)
                    improvement = refined_score.overall - current_score.overall
                    
                    if improvement > best_improvement:
                        best_content = refined_content
                        best_improvement = improvement
                        best_strategy = strategy.__name__
            except Exception as e:
                # Skip failed refinement
                continue
        
        improvement_info = {
            'strategy': best_strategy or 'none',
            'dimension': weakest_dimension,
            'improvement': best_improvement
        }
        
        return best_content, improvement_info
    
    def _gradient_based_step(self,
                           content: str,
                           current_score: QualityMetrics,
                           metadata: Optional[Dict]) -> Tuple[str, Dict]:
        """
        Perform gradient-based optimization step.
        
        Estimates gradient direction and applies multiple refinements.
        """
        # Calculate gradients for each dimension
        gradients = self._calculate_quality_gradients(content, current_score, metadata)
        
        # Apply refinements based on gradient magnitudes
        refined_content = content
        total_improvement = 0.0
        applied_strategies = []
        
        for dimension, gradient in sorted(gradients.items(), key=lambda x: x[1], reverse=True):
            if gradient > 0.1:  # Significant gradient
                strategies = self.refinement_strategies.get(dimension, [])
                if strategies:
                    strategy = strategies[0]  # Use primary strategy
                    try:
                        temp_content = strategy(refined_content, metadata)
                        if temp_content and temp_content != refined_content:
                            # Evaluate improvement
                            temp_score = self.scorer.score_document(temp_content, metadata)
                            improvement = temp_score.overall - current_score.overall
                            
                            if improvement > 0:
                                refined_content = temp_content
                                total_improvement += improvement
                                applied_strategies.append(strategy.__name__)
                    except Exception:
                        continue
        
        improvement_info = {
            'strategy': 'gradient_based',
            'applied_strategies': applied_strategies,
            'improvement': total_improvement,
            'gradients': gradients
        }
        
        return refined_content, improvement_info
    
    def _calculate_quality_gradients(self,
                                    content: str,
                                    current_score: QualityMetrics,
                                    metadata: Optional[Dict]) -> Dict[str, float]:
        """
        Calculate improvement gradients for each quality dimension.
        
        Returns estimated improvement potential for each dimension.
        """
        # Maximum possible score is 1.0
        gradients = {
            'completeness': 1.0 - current_score.completeness,
            'clarity': 1.0 - current_score.clarity,
            'consistency': 1.0 - current_score.consistency,
            'accuracy': 1.0 - current_score.accuracy
        }
        
        # Weight by dimension importance
        weights = self.scorer.weights
        gradients['completeness'] *= weights.completeness
        gradients['clarity'] *= weights.clarity
        gradients['consistency'] *= weights.consistency
        gradients['accuracy'] *= weights.accuracy
        
        return gradients
    
    # Refinement strategies for completeness
    def _add_missing_sections(self, content: str, metadata: Optional[Dict]) -> str:
        """Add missing standard sections to improve completeness."""
        required_sections = ['## Introduction', '## Usage', '## Examples', '## References']
        
        for section in required_sections:
            if section.lower() not in content.lower():
                # Add placeholder section
                if section == '## Introduction':
                    content = f"{section}\n\nThis document provides comprehensive information about the topic.\n\n" + content
                elif section == '## Usage':
                    if '## Introduction' in content:
                        parts = content.split('## Introduction')
                        content = parts[0] + '## Introduction' + parts[1].split('\n\n', 1)[0] + f"\n\n{section}\n\nDetailed usage instructions and guidelines.\n\n" + '\n\n'.join(parts[1].split('\n\n')[1:])
                    else:
                        content += f"\n\n{section}\n\nDetailed usage instructions and guidelines.\n"
                elif section == '## Examples':
                    content += f"\n\n{section}\n\n```python\n# Example code\nprint('Example implementation')\n```\n"
                elif section == '## References':
                    content += f"\n\n{section}\n\n- [Documentation](docs/)\n- [API Reference](api/)\n"
        
        return content
    
    def _expand_content(self, content: str, metadata: Optional[Dict]) -> str:
        """Expand content with more details."""
        # Simple expansion: add clarifying phrases
        lines = content.split('\n')
        expanded_lines = []
        
        for line in lines:
            expanded_lines.append(line)
            
            # Add details after headers
            if line.startswith('#') and not line.startswith('###'):
                section_name = line.strip('#').strip()
                if len(expanded_lines) < len(lines) - 1:
                    next_line = lines[lines.index(line) + 1] if lines.index(line) < len(lines) - 1 else ""
                    if not next_line.strip():
                        expanded_lines.append(f"\nThis section covers {section_name.lower()} in detail.")
        
        return '\n'.join(expanded_lines)
    
    def _add_examples(self, content: str, metadata: Optional[Dict]) -> str:
        """Add code examples to improve completeness."""
        if '```' not in content:
            # Add a basic example
            content += "\n\n## Code Example\n\n```python\n# Example implementation\ndef example_function():\n    \"\"\"Demonstrates usage.\"\"\"\n    return 'result'\n```\n"
        
        return content
    
    # Refinement strategies for clarity
    def _simplify_sentences(self, content: str, metadata: Optional[Dict]) -> str:
        """Simplify complex sentences for better clarity."""
        import re
        
        # Split very long sentences
        sentences = re.split(r'([.!?]+)', content)
        simplified = []
        
        for i in range(0, len(sentences), 2):
            if i + 1 < len(sentences):
                sentence = sentences[i] + sentences[i + 1]
                
                # If sentence is too long, try to split it
                if len(sentence.split()) > 30:
                    # Look for conjunctions to split on
                    if ', and' in sentence:
                        parts = sentence.split(', and', 1)
                        simplified.append(parts[0] + '.')
                        simplified.append('Additionally, ' + parts[1])
                    elif ', but' in sentence:
                        parts = sentence.split(', but', 1)
                        simplified.append(parts[0] + '.')
                        simplified.append('However, ' + parts[1])
                    else:
                        simplified.append(sentence)
                else:
                    simplified.append(sentence)
        
        return ''.join(simplified)
    
    def _improve_structure(self, content: str, metadata: Optional[Dict]) -> str:
        """Improve document structure and organization."""
        # Ensure proper paragraph spacing
        lines = content.split('\n')
        improved = []
        
        for i, line in enumerate(lines):
            improved.append(line)
            
            # Add spacing after headers
            if line.startswith('#'):
                if i + 1 < len(lines) and lines[i + 1].strip() and not lines[i + 1].startswith('#'):
                    improved.append('')
        
        return '\n'.join(improved)
    
    def _activate_voice(self, content: str, metadata: Optional[Dict]) -> str:
        """Convert passive voice to active where possible."""
        # Simple passive to active conversions
        replacements = [
            ('was created by', 'created'),
            ('is used by', 'uses'),
            ('was designed to', 'designed to'),
            ('can be configured', 'configure'),
            ('should be considered', 'consider')
        ]
        
        result = content
        for passive, active in replacements:
            result = result.replace(passive, active)
        
        return result
    
    # Refinement strategies for consistency
    def _standardize_terminology(self, content: str, metadata: Optional[Dict]) -> str:
        """Standardize terminology throughout document."""
        # Common standardizations
        replacements = [
            ('e-mail', 'email'),
            ('E-mail', 'email'),
            ('set-up', 'setup'),
            ('set up', 'setup'),
            ('data base', 'database'),
            ('web site', 'website')
        ]
        
        result = content
        for variant, standard in replacements:
            result = result.replace(variant, standard)
        
        return result
    
    def _fix_formatting(self, content: str, metadata: Optional[Dict]) -> str:
        """Fix formatting inconsistencies."""
        import re
        
        # Fix multiple spaces
        result = re.sub(r'  +', ' ', content)
        
        # Ensure consistent bullet points
        result = re.sub(r'^\*\s+', '- ', result, flags=re.MULTILINE)
        result = re.sub(r'^\+\s+', '- ', result, flags=re.MULTILINE)
        
        return result
    
    def _normalize_style(self, content: str, metadata: Optional[Dict]) -> str:
        """Normalize writing style."""
        # Ensure consistent capitalization in headers
        lines = content.split('\n')
        normalized = []
        
        for line in lines:
            if line.startswith('#'):
                # Title case for headers
                header_part = line.split(' ', 1)
                if len(header_part) == 2:
                    header_level = header_part[0]
                    header_text = header_part[1]
                    # Simple title case
                    title_cased = ' '.join(word.capitalize() for word in header_text.split())
                    normalized.append(f"{header_level} {title_cased}")
                else:
                    normalized.append(line)
            else:
                normalized.append(line)
        
        return '\n'.join(normalized)
    
    # Refinement strategies for accuracy
    def _update_references(self, content: str, metadata: Optional[Dict]) -> str:
        """Update and fix references."""
        import re
        
        # Fix empty links
        result = re.sub(r'\[([^\]]+)\]\(\)', r'[\1](#)', content)
        
        # Add missing link protocols
        result = re.sub(r'\[([^\]]+)\]\(([^:)]+\.com[^)]*)\)', r'[\1](https://\2)', result)
        
        return result
    
    def _add_metadata(self, content: str, metadata: Optional[Dict]) -> str:
        """Add metadata information to improve accuracy tracking."""
        if metadata and 'version' not in content.lower():
            # Add version info if available
            if 'version' in metadata:
                content = f"Version: {metadata['version']}\n\n" + content
        
        # Add update timestamp
        if 'last updated' not in content.lower():
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d")
            content = f"Last Updated: {timestamp}\n\n" + content
        
        return content
    
    def _fix_technical_issues(self, content: str, metadata: Optional[Dict]) -> str:
        """Fix technical accuracy issues."""
        # Fix common technical errors
        replacements = [
            ('Python 2', 'Python 3'),  # Update outdated references
            ('depreciated', 'deprecated'),  # Common typo
            ('asyncronous', 'asynchronous'),
            ('authentification', 'authentication')
        ]
        
        result = content
        for incorrect, correct in replacements:
            result = result.replace(incorrect, correct)
        
        return result
    
    def calculate_improvement(self,
                            original_score: QualityMetrics,
                            optimized_score: QualityMetrics) -> Dict[str, float]:
        """
        Calculate detailed improvement metrics.
        
        Args:
            original_score: Original quality metrics
            optimized_score: Optimized quality metrics
            
        Returns:
            Dictionary with improvement percentages for each dimension
        """
        improvements = {}
        
        for dimension in ['completeness', 'clarity', 'consistency', 'accuracy', 'overall']:
            original_val = getattr(original_score, dimension)
            optimized_val = getattr(optimized_score, dimension)
            
            if original_val == 0:
                improvement = 100.0 if optimized_val > 0 else 0.0
            else:
                improvement = ((optimized_val - original_val) / original_val) * 100
            
            improvements[dimension] = improvement
        
        return improvements