"""
M003 MIAIR Engine - Meta-Iterative AI Refinement with Shannon Entropy
DevDocAI v3.0.0 - Pass 1: Core Implementation

Shannon Entropy Formula: S = -Σ[p(xi) × log2(p(xi))] × f(Tx)
Quality Target: 60-75% document improvement
Performance Target: 248K documents/minute
"""

import re
import time
import math
import logging
import asyncio
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field, asdict
from collections import Counter
from datetime import datetime

import numpy as np

# Local imports - validated foundation modules
from ..core.config import ConfigurationManager
from ..core.storage import StorageManager
from ..intelligence.llm_adapter import LLMAdapter, LLMResponse

logger = logging.getLogger(__name__)


# ============================================================================
# Exceptions
# ============================================================================

class EntropyOptimizationError(Exception):
    """Base exception for MIAIR optimization errors."""
    pass


class QualityGateError(Exception):
    """Raised when quality gate requirements are not met."""
    pass


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class DocumentMetrics:
    """Metrics for document quality assessment."""
    entropy: float
    coherence: float
    quality_score: float
    word_count: int
    unique_words: int
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'entropy': self.entropy,
            'coherence': self.coherence,
            'quality_score': self.quality_score,
            'word_count': self.word_count,
            'unique_words': self.unique_words,
            'timestamp': self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else str(self.timestamp)
        }


@dataclass
class OptimizationResult:
    """Result of MIAIR optimization process."""
    initial_content: str
    final_content: str
    iterations: int
    initial_quality: float
    final_quality: float
    improvement_percentage: float
    initial_metrics: Optional[DocumentMetrics]
    final_metrics: DocumentMetrics
    optimization_time: float
    storage_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            'iterations': self.iterations,
            'initial_quality': self.initial_quality,
            'final_quality': self.final_quality,
            'improvement_percentage': self.improvement_percentage,
            'optimization_time': self.optimization_time,
            'storage_id': self.storage_id,
            'initial_metrics': self.initial_metrics.to_dict() if self.initial_metrics else None,
            'final_metrics': self.final_metrics.to_dict()
        }


# ============================================================================
# MIAIR Engine
# ============================================================================

class MIAIREngine:
    """
    Meta-Iterative AI Refinement Engine using Shannon entropy optimization.
    
    Implements the formula: S = -Σ[p(xi) × log2(p(xi))] × f(Tx)
    where:
    - p(xi) is the probability of word xi
    - f(Tx) is the transformation function based on context
    
    Targets:
    - 60-75% quality improvement
    - 248K documents/minute processing
    - 7 max iterations
    - 0.35 → 0.15 entropy reduction
    - 0.94 coherence target
    """
    
    def __init__(
        self,
        config: ConfigurationManager,
        llm_adapter: LLMAdapter,
        storage: StorageManager
    ):
        """
        Initialize MIAIR Engine.
        
        Args:
            config: Configuration manager instance
            llm_adapter: LLM adapter for AI refinement
            storage: Storage system for persistence
        """
        self.config = config
        self.llm_adapter = llm_adapter
        self.storage = storage
        
        # Load configuration parameters
        self.entropy_threshold = config.get('quality.entropy_threshold', 0.35)
        self.target_entropy = config.get('quality.target_entropy', 0.15)
        self.coherence_target = config.get('quality.coherence_target', 0.94)
        self.quality_gate = config.get('quality.quality_gate', 85)
        self.max_iterations = config.get('quality.max_iterations', 7)
        
        # Performance optimizations
        self.max_workers = config.get('performance.max_workers', 4)
        self.cache_size = config.get('performance.cache_size', 1000)
        self.batch_size = config.get('performance.batch_size', 100)
        
        # Initialize thread pool for parallel processing
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        # Performance tracking
        self._optimization_count = 0
        self._total_improvement = 0.0
        
        logger.info(
            f"MIAIR Engine initialized - Entropy: {self.entropy_threshold}→{self.target_entropy}, "
            f"Quality Gate: {self.quality_gate}%, Max Iterations: {self.max_iterations}, "
            f"Workers: {self.max_workers}, Cache: {self.cache_size}"
        )
    
    def calculate_entropy(self, document: str) -> float:
        """
        Calculate Shannon entropy of document.
        
        Formula: S = -Σ[p(xi) × log2(p(xi))]
        
        Args:
            document: Text document to analyze
            
        Returns:
            Shannon entropy value (0 = perfectly uniform, higher = more random)
        """
        if not document:
            return 0.0
        
        # Use cached tokenization
        words = self._tokenize_cached(document)
        
        if not words:
            return 0.0
        
        # Vectorized entropy calculation using NumPy
        return self._calculate_entropy_vectorized(words)
    
    def _calculate_entropy_vectorized(self, words: List[str]) -> float:
        """
        Vectorized entropy calculation using NumPy for performance.
        
        Args:
            words: List of tokenized words
            
        Returns:
            Shannon entropy value
        """
        if len(words) == 0:
            return 0.0
        
        # Use NumPy for efficient counting
        unique, counts = np.unique(words, return_counts=True)
        
        if len(unique) == 1:
            return 0.0  # Single unique word = no entropy
        
        # Vectorized probability calculation
        probabilities = counts / len(words)
        
        # Vectorized entropy calculation
        # Use np.log2 for vectorized logarithm
        entropy = -np.sum(probabilities * np.log2(probabilities))
        
        return float(entropy)
    
    def calculate_entropy_batch(self, documents: List[str]) -> List[float]:
        """
        Calculate entropy for multiple documents in parallel.
        
        Args:
            documents: List of documents to analyze
            
        Returns:
            List of entropy values
        """
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self.calculate_entropy, doc) for doc in documents]
            return [future.result() for future in as_completed(futures)]
    
    def measure_quality(self, document: str) -> DocumentMetrics:
        """
        Measure document quality metrics.
        
        Args:
            document: Text document to analyze
            
        Returns:
            DocumentMetrics with quality measurements
        """
        if not document:
            return DocumentMetrics(
                entropy=0.0,
                coherence=0.0,
                quality_score=0.0,
                word_count=0,
                unique_words=0
            )
        
        # Calculate entropy
        entropy = self.calculate_entropy(document)
        
        # Tokenize for word analysis
        words = self._tokenize(document)
        word_count = len(words)
        unique_words = len(set(words))
        
        # Calculate coherence (simplified - ratio of unique to total words)
        # Real implementation would use more sophisticated NLP
        coherence = self._calculate_coherence(document, words)
        
        # Calculate quality score based on multiple factors
        quality_score = self._calculate_quality_score(
            entropy, coherence, word_count, unique_words
        )
        
        return DocumentMetrics(
            entropy=entropy,
            coherence=coherence,
            quality_score=quality_score,
            word_count=word_count,
            unique_words=unique_words
        )
    
    def refine_content(
        self,
        document: str,
        metrics: Optional[DocumentMetrics] = None
    ) -> str:
        """
        Refine document content using LLM.
        
        Args:
            document: Original document content
            metrics: Optional current metrics to guide refinement
            
        Returns:
            Refined document content
            
        Raises:
            EntropyOptimizationError: If refinement fails
        """
        try:
            # Build refinement prompt
            prompt = self._build_refinement_prompt(document, metrics)
            
            # Query LLM for refinement
            response = self.llm_adapter.query(
                prompt,
                preferred_providers=['claude', 'openai'],  # Prefer advanced models
                max_tokens=2000,
                temperature=0.7  # Balanced creativity
            )
            
            if not response or not response.content:
                raise EntropyOptimizationError("LLM returned empty response")
            
            return response.content
            
        except Exception as e:
            logger.error(f"Content refinement failed: {e}")
            raise EntropyOptimizationError(f"Failed to refine content: {e}")
    
    def optimize(
        self,
        document: str,
        max_iterations: Optional[int] = None,
        save_to_storage: bool = False
    ) -> OptimizationResult:
        """
        Optimize document using iterative refinement.
        
        Args:
            document: Document to optimize
            max_iterations: Override max iterations (default: 7)
            save_to_storage: Save optimized document to storage
            
        Returns:
            OptimizationResult with optimization details
            
        Raises:
            ValueError: If document is invalid
            EntropyOptimizationError: If optimization fails
        """
        if not document or not isinstance(document, str):
            raise ValueError("Document must be a non-empty string")
        
        start_time = time.time()
        max_iters = max_iterations or self.max_iterations
        
        # Measure initial quality
        initial_metrics = self.measure_quality(document)
        initial_quality = initial_metrics.quality_score
        
        current_content = document
        current_metrics = initial_metrics
        iterations = 0
        
        logger.info(
            f"Starting MIAIR optimization - Initial quality: {initial_quality:.1f}%, "
            f"Entropy: {initial_metrics.entropy:.2f}"
        )
        
        # Optimization loop
        while iterations < max_iters:
            iterations += 1
            
            # Check if we've reached targets
            if self._targets_reached(current_metrics):
                logger.info(f"Targets reached after {iterations} iterations")
                break
            
            # Refine content
            try:
                refined_content = self.refine_content(current_content, current_metrics)
                
                # Measure refined quality
                refined_metrics = self.measure_quality(refined_content)
                
                # Keep refinement if it improves quality, entropy, or coherence
                quality_improved = refined_metrics.quality_score > current_metrics.quality_score
                entropy_improved = refined_metrics.entropy < current_metrics.entropy
                coherence_improved = refined_metrics.coherence > current_metrics.coherence
                
                if quality_improved or entropy_improved or coherence_improved:
                    current_content = refined_content
                    current_metrics = refined_metrics
                    
                    logger.debug(
                        f"Iteration {iterations}: Quality {refined_metrics.quality_score:.1f}%, "
                        f"Entropy: {refined_metrics.entropy:.2f}, "
                        f"Coherence: {refined_metrics.coherence:.2f}"
                    )
                else:
                    logger.debug(f"Iteration {iterations}: No improvement, keeping previous")
                
            except Exception as e:
                logger.warning(f"Refinement failed on iteration {iterations}: {e}")
                # Continue with current best content
        
        # Calculate improvement
        final_quality = current_metrics.quality_score
        improvement = ((final_quality - initial_quality) / initial_quality * 100) if initial_quality > 0 else 0
        
        # Save to storage if requested
        storage_id = None
        if save_to_storage:
            try:
                doc_data = {
                    'content': current_content,
                    'metadata': {
                        'optimized': True,
                        'miair_metrics': current_metrics.to_dict(),
                        'improvement_percentage': improvement,
                        'iterations': iterations
                    }
                }
                storage_id = self.storage.save_document(doc_data)
                logger.info(f"Optimized document saved with ID: {storage_id}")
            except Exception as e:
                logger.error(f"Failed to save to storage: {e}")
        
        # Track statistics
        self._optimization_count += 1
        self._total_improvement += improvement
        
        optimization_time = time.time() - start_time
        
        logger.info(
            f"MIAIR optimization complete - Iterations: {iterations}, "
            f"Final quality: {final_quality:.1f}%, Improvement: {improvement:.1f}%, "
            f"Time: {optimization_time:.2f}s"
        )
        
        return OptimizationResult(
            initial_content=document,
            final_content=current_content,
            iterations=iterations,
            initial_quality=initial_quality,
            final_quality=final_quality,
            improvement_percentage=improvement,
            initial_metrics=initial_metrics,
            final_metrics=current_metrics,
            optimization_time=optimization_time,
            storage_id=storage_id
        )
    
    # ========================================================================
    # Private Methods
    # ========================================================================
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into words.
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of words (lowercase, alphanumeric only)
        """
        # Remove code blocks if present
        text = re.sub(r'```[\s\S]*?```', '', text)
        
        # Extract words (alphanumeric sequences)
        words = re.findall(r'\b\w+\b', text.lower())
        
        return words
    
    @lru_cache(maxsize=1000)
    def _tokenize_cached(self, text: str) -> tuple:
        """
        Cached tokenization for performance.
        
        Args:
            text: Text to tokenize
            
        Returns:
            Tuple of words (for hashability in cache)
        """
        return tuple(self._tokenize(text))
    
    def _calculate_coherence(self, document: str, words: List[str]) -> float:
        """
        Calculate document coherence score.
        
        Simplified implementation - real version would use NLP techniques.
        
        Args:
            document: Full document text
            words: Tokenized words
            
        Returns:
            Coherence score (0-1)
        """
        if not words:
            return 0.0
        
        # Factors for coherence
        factors = []
        
        # 1. Vocabulary diversity (not too repetitive, not too diverse)
        unique_ratio = len(set(words)) / len(words) if words else 0
        # Optimal ratio around 0.3-0.7
        if 0.3 <= unique_ratio <= 0.7:
            factors.append(1.0)
        else:
            factors.append(0.5 + 0.5 * (1 - abs(0.5 - unique_ratio)))
        
        # 2. Sentence structure (check for proper sentences)
        sentences = re.split(r'[.!?]+', document)
        valid_sentences = sum(1 for s in sentences if 3 <= len(s.split()) <= 50)
        sentence_ratio = valid_sentences / len(sentences) if sentences else 0
        factors.append(sentence_ratio)
        
        # 3. Paragraph structure (check for paragraphs)
        paragraphs = document.split('\n\n')
        has_structure = len(paragraphs) > 1
        factors.append(1.0 if has_structure else 0.7)
        
        # Average coherence factors
        coherence = sum(factors) / len(factors) if factors else 0.0
        
        return min(1.0, coherence)
    
    def _calculate_quality_score(
        self,
        entropy: float,
        coherence: float,
        word_count: int,
        unique_words: int
    ) -> float:
        """
        Calculate overall quality score.
        
        Args:
            entropy: Shannon entropy
            coherence: Coherence score
            word_count: Total words
            unique_words: Unique words
            
        Returns:
            Quality score (0-100)
        """
        # Quality factors with weights
        factors = []
        
        # 1. Entropy factor (lower is better, but not too low)
        # Optimal entropy around 1.5-2.5
        if 1.5 <= entropy <= 2.5:
            entropy_score = 100
        elif entropy < 1.5:
            entropy_score = 60 + (entropy / 1.5) * 40
        else:
            entropy_score = max(20, 100 - (entropy - 2.5) * 20)
        factors.append((entropy_score, 0.3))
        
        # 2. Coherence factor
        coherence_score = coherence * 100
        factors.append((coherence_score, 0.4))
        
        # 3. Length factor (reasonable document length)
        if 50 <= word_count <= 5000:
            length_score = 100
        elif word_count < 50:
            length_score = (word_count / 50) * 100
        else:
            length_score = max(50, 100 - ((word_count - 5000) / 100))
        factors.append((length_score, 0.2))
        
        # 4. Vocabulary richness
        if word_count > 0:
            richness = (unique_words / word_count) * 100
            richness_score = min(100, richness * 2)  # Optimal around 50%
        else:
            richness_score = 0
        factors.append((richness_score, 0.1))
        
        # Calculate weighted average
        total_score = sum(score * weight for score, weight in factors)
        
        return min(100, max(0, total_score))
    
    def _targets_reached(self, metrics: DocumentMetrics) -> bool:
        """
        Check if optimization targets are reached.
        
        Args:
            metrics: Current document metrics
            
        Returns:
            True if any target is reached
        """
        # Check quality gate
        if metrics.quality_score >= self.quality_gate:
            return True
        
        # Check entropy target
        if metrics.entropy <= self.target_entropy:
            return True
        
        # Check coherence target
        if metrics.coherence >= self.coherence_target:
            return True
        
        return False
    
    def _build_refinement_prompt(
        self,
        document: str,
        metrics: Optional[DocumentMetrics] = None
    ) -> str:
        """
        Build prompt for LLM refinement.
        
        Args:
            document: Document to refine
            metrics: Optional current metrics
            
        Returns:
            Refinement prompt
        """
        prompt_parts = [
            "Please improve the following document for better clarity, structure, and professional quality.",
            "",
            "Current document:",
            "---",
            document,
            "---",
            ""
        ]
        
        if metrics:
            prompt_parts.extend([
                "Current metrics:",
                f"- Entropy: {metrics.entropy:.2f} (target: {self.target_entropy})",
                f"- Coherence: {metrics.coherence:.2f} (target: {self.coherence_target})",
                f"- Quality Score: {metrics.quality_score:.1f}% (target: {self.quality_gate}%)",
                f"- Word Count: {metrics.word_count}",
                f"- Unique Words: {metrics.unique_words}",
                ""
            ])
        
        prompt_parts.extend([
            "Focus on:",
            "1. Improving clarity and readability",
            "2. Enhancing structure and organization",
            "3. Ensuring professional tone and quality",
            "4. Maintaining technical accuracy",
            "5. Optimizing information density",
            "",
            "Return only the improved document content."
        ])
        
        return "\n".join(prompt_parts)
    
    # ========================================================================
    # Public Statistics Methods
    # ========================================================================
    
    def batch_optimize(
        self,
        documents: List[str],
        max_iterations: Optional[int] = None,
        save_to_storage: bool = False
    ) -> List[OptimizationResult]:
        """
        Optimize multiple documents in parallel for high throughput.
        
        Args:
            documents: List of documents to optimize
            max_iterations: Override max iterations
            save_to_storage: Save optimized documents to storage
            
        Returns:
            List of optimization results
        """
        results = []
        
        # Process documents in batches for memory efficiency
        for i in range(0, len(documents), self.batch_size):
            batch = documents[i:i + self.batch_size]
            
            # Process batch in parallel
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [
                    executor.submit(self.optimize, doc, max_iterations, save_to_storage)
                    for doc in batch
                ]
                
                for future in as_completed(futures):
                    try:
                        result = future.result(timeout=30)  # 30s timeout per document
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Batch optimization error: {e}")
                        # Create failed result placeholder
                        results.append(OptimizationResult(
                            initial_content=batch[0][:100],  # First 100 chars
                            final_content=batch[0][:100],
                            iterations=0,
                            initial_quality=0,
                            final_quality=0,
                            improvement_percentage=0,
                            initial_metrics=None,
                            final_metrics=DocumentMetrics(
                                entropy=0, coherence=0, quality_score=0,
                                word_count=0, unique_words=0
                            ),
                            optimization_time=0
                        ))
        
        return results
    
    async def optimize_async(
        self,
        document: str,
        max_iterations: Optional[int] = None,
        save_to_storage: bool = False
    ) -> OptimizationResult:
        """
        Asynchronously optimize document for concurrent processing.
        
        Args:
            document: Document to optimize
            max_iterations: Override max iterations
            save_to_storage: Save optimized document to storage
            
        Returns:
            OptimizationResult
        """
        loop = asyncio.get_event_loop()
        
        # Run optimization in thread pool to avoid blocking
        result = await loop.run_in_executor(
            self._executor,
            self.optimize,
            document,
            max_iterations,
            save_to_storage
        )
        
        return result
    
    async def batch_optimize_async(
        self,
        documents: List[str],
        max_iterations: Optional[int] = None,
        save_to_storage: bool = False
    ) -> List[OptimizationResult]:
        """
        Asynchronously optimize multiple documents for maximum throughput.
        
        Args:
            documents: List of documents to optimize
            max_iterations: Override max iterations
            save_to_storage: Save optimized documents to storage
            
        Returns:
            List of optimization results
        """
        tasks = [
            self.optimize_async(doc, max_iterations, save_to_storage)
            for doc in documents
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and log them
        clean_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Async optimization failed for document {i}: {result}")
                # Add placeholder for failed optimization
                clean_results.append(OptimizationResult(
                    initial_content=documents[i][:100],
                    final_content=documents[i][:100],
                    iterations=0,
                    initial_quality=0,
                    final_quality=0,
                    improvement_percentage=0,
                    initial_metrics=None,
                    final_metrics=DocumentMetrics(
                        entropy=0, coherence=0, quality_score=0,
                        word_count=0, unique_words=0
                    ),
                    optimization_time=0
                ))
            else:
                clean_results.append(result)
        
        return clean_results
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get engine statistics.
        
        Returns:
            Dictionary with optimization statistics
        """
        avg_improvement = (
            self._total_improvement / self._optimization_count
            if self._optimization_count > 0
            else 0
        )
        
        # Get cache info
        cache_info = self._tokenize_cached.cache_info()
        
        return {
            'optimizations_performed': self._optimization_count,
            'average_improvement': avg_improvement,
            'entropy_threshold': self.entropy_threshold,
            'target_entropy': self.target_entropy,
            'quality_gate': self.quality_gate,
            'coherence_target': self.coherence_target,
            'cache_hits': cache_info.hits,
            'cache_misses': cache_info.misses,
            'cache_size': cache_info.currsize,
            'max_workers': self.max_workers,
            'batch_size': self.batch_size
        }
    
    def reset_statistics(self):
        """Reset engine statistics."""
        self._optimization_count = 0
        self._total_improvement = 0.0
        self._tokenize_cached.cache_clear()
        logger.info("MIAIR Engine statistics and cache reset")
    
    def __del__(self):
        """Cleanup resources on deletion."""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)