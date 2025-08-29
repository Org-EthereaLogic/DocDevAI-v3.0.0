"""
Main MIAIR Engine orchestrating all mathematical optimization components.

Integrates entropy calculation, quality scoring, pattern recognition, and
optimization to provide comprehensive document improvement capabilities.
"""

import time
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
import json

from .entropy import ShannonEntropyCalculator
from .scorer import QualityScorer, QualityMetrics, ScoringWeights
from .optimizer import MIAIROptimizer, OptimizationConfig, OptimizationResult
from .patterns import PatternRecognizer, PatternAnalysis

# Import M002 storage for integration
try:
    from devdocai.storage.local_storage import LocalStorageSystem, DocumentData
    STORAGE_AVAILABLE = True
except ImportError:
    STORAGE_AVAILABLE = False
    LocalStorageSystem = None
    DocumentData = None

logger = logging.getLogger(__name__)


@dataclass
class MIAIRConfig:
    """Configuration for MIAIR Engine."""
    # Quality thresholds
    target_quality: float = 0.85
    min_quality: float = 0.5
    
    # Optimization settings
    max_iterations: int = 10
    optimization_timeout: float = 30.0
    enable_learning: bool = True
    
    # Performance settings
    enable_caching: bool = True
    cache_size: int = 128
    batch_size: int = 10
    
    # Integration settings
    storage_enabled: bool = True
    save_improvements: bool = True
    track_metrics: bool = True
    
    # Weights
    scoring_weights: Optional[ScoringWeights] = None
    entropy_weight: float = 0.3


@dataclass
class DocumentAnalysis:
    """Complete document analysis results."""
    document_id: Optional[str]
    content: str
    entropy_stats: Dict[str, Any]
    quality_metrics: QualityMetrics
    patterns: PatternAnalysis
    improvement_potential: float
    recommendations: List[str]
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'document_id': self.document_id,
            'content_preview': self.content[:200] + '...' if len(self.content) > 200 else self.content,
            'entropy_stats': self.entropy_stats,
            'quality_metrics': self.quality_metrics.to_dict(),
            'patterns_summary': self.patterns.summary,
            'improvement_potential': self.improvement_potential,
            'recommendations': self.recommendations,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class BatchProcessingResult:
    """Results from batch document processing."""
    total_documents: int
    processed: int
    improved: int
    failed: int
    average_improvement: float
    total_time: float
    documents: List[Dict[str, Any]]


class MIAIREngine:
    """
    Main MIAIR Engine for document quality optimization.
    
    Orchestrates entropy analysis, quality scoring, pattern recognition,
    and iterative optimization to improve documentation quality.
    """
    
    def __init__(self, 
                 config: Optional[MIAIRConfig] = None,
                 storage_system: Optional[LocalStorageSystem] = None):
        """
        Initialize MIAIR Engine.
        
        Args:
            config: Engine configuration
            storage_system: Optional M002 storage integration
        """
        self.config = config or MIAIRConfig()
        
        # Initialize components
        self.entropy_calc = ShannonEntropyCalculator(cache_size=self.config.cache_size)
        self.scorer = QualityScorer(weights=self.config.scoring_weights)
        self.pattern_recognizer = PatternRecognizer(learning_enabled=self.config.enable_learning)
        
        # Initialize optimizer with config
        optimizer_config = OptimizationConfig(
            target_quality=self.config.target_quality,
            max_iterations=self.config.max_iterations,
            timeout_seconds=self.config.optimization_timeout,
            entropy_balance_weight=self.config.entropy_weight,
            enable_caching=self.config.enable_caching
        )
        self.optimizer = MIAIROptimizer(
            config=optimizer_config,
            entropy_calculator=self.entropy_calc,
            quality_scorer=self.scorer
        )
        
        # Storage integration
        if self.config.storage_enabled and STORAGE_AVAILABLE:
            self.storage = storage_system or LocalStorageSystem()
        else:
            self.storage = None
            if self.config.storage_enabled and not STORAGE_AVAILABLE:
                logger.warning("Storage requested but M002 not available")
        
        # Metrics tracking
        self.metrics = {
            'documents_analyzed': 0,
            'documents_optimized': 0,
            'total_improvement': 0.0,
            'patterns_identified': 0,
            'processing_time': 0.0
        }
        
        logger.info("MIAIR Engine initialized with target quality: %.2f", 
                   self.config.target_quality)
    
    def analyze_document(self, 
                        content: str,
                        document_id: Optional[str] = None,
                        metadata: Optional[Dict] = None) -> DocumentAnalysis:
        """
        Perform comprehensive document analysis.
        
        Args:
            content: Document content to analyze
            document_id: Optional document identifier
            metadata: Optional metadata for context
            
        Returns:
            DocumentAnalysis with complete assessment
        """
        start_time = time.time()
        
        # Calculate entropy statistics
        entropy_stats = self.entropy_calc.get_entropy_statistics(content)
        
        # Score quality
        quality_metrics = self.scorer.score_document(content, metadata)
        
        # Recognize patterns
        patterns = self.pattern_recognizer.analyze(content, metadata)
        
        # Calculate improvement potential
        improvement_potential = self._calculate_improvement_potential(
            quality_metrics, entropy_stats, patterns
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            quality_metrics, entropy_stats, patterns
        )
        
        # Update metrics
        if self.config.track_metrics:
            self.metrics['documents_analyzed'] += 1
            self.metrics['patterns_identified'] += len(patterns.patterns)
            self.metrics['processing_time'] += time.time() - start_time
        
        analysis = DocumentAnalysis(
            document_id=document_id,
            content=content,
            entropy_stats=entropy_stats,
            quality_metrics=quality_metrics,
            patterns=patterns,
            improvement_potential=improvement_potential,
            recommendations=recommendations
        )
        
        # Store analysis if storage enabled
        if self.storage and self.config.save_improvements:
            self._store_analysis(analysis, metadata)
        
        return analysis
    
    def optimize_document(self,
                         content: str,
                         document_id: Optional[str] = None,
                         metadata: Optional[Dict] = None) -> OptimizationResult:
        """
        Optimize document quality through iterative refinement.
        
        Args:
            content: Document content to optimize
            document_id: Optional document identifier
            metadata: Optional metadata for context
            
        Returns:
            OptimizationResult with improved content
        """
        start_time = time.time()
        
        # Perform initial analysis
        initial_analysis = self.analyze_document(content, document_id, metadata)
        
        # Skip optimization if quality already meets target
        if initial_analysis.quality_metrics.overall >= self.config.target_quality:
            logger.info("Document already meets quality target: %.2f", 
                       initial_analysis.quality_metrics.overall)
            return OptimizationResult(
                original_content=content,
                optimized_content=content,
                original_score=initial_analysis.quality_metrics,
                optimized_score=initial_analysis.quality_metrics,
                iterations=0,
                improvements=[],
                success=True,
                elapsed_time=time.time() - start_time
            )
        
        # Perform optimization
        result = self.optimizer.optimize_document(content, metadata)
        
        # Learn from successful improvements
        if self.config.enable_learning and result.success:
            addressed_patterns = self._identify_addressed_patterns(
                initial_analysis.patterns,
                result.optimized_content
            )
            self.pattern_recognizer.learn_from_improvement(
                content, result.optimized_content, addressed_patterns
            )
        
        # Update metrics
        if self.config.track_metrics:
            self.metrics['documents_optimized'] += 1
            self.metrics['total_improvement'] += result.improvement_percentage()
            self.metrics['processing_time'] += time.time() - start_time
        
        # Store optimization result if storage enabled
        if self.storage and self.config.save_improvements and result.success:
            self._store_optimization(document_id, result, metadata)
        
        return result
    
    def process_batch(self,
                     documents: List[Union[str, Dict[str, Any]]],
                     optimize: bool = True) -> BatchProcessingResult:
        """
        Process multiple documents in batch.
        
        Args:
            documents: List of document contents or dicts with content and metadata
            optimize: Whether to optimize or just analyze
            
        Returns:
            BatchProcessingResult with summary and details
        """
        start_time = time.time()
        results = []
        improved_count = 0
        failed_count = 0
        total_improvement = 0.0
        
        for i, doc in enumerate(documents):
            try:
                # Extract content and metadata
                if isinstance(doc, str):
                    content = doc
                    metadata = None
                    doc_id = f"batch_{i}"
                else:
                    content = doc.get('content', '')
                    metadata = doc.get('metadata', None)
                    doc_id = doc.get('id', f"batch_{i}")
                
                if optimize:
                    # Optimize document
                    result = self.optimize_document(content, doc_id, metadata)
                    
                    improvement = result.improvement_percentage()
                    if result.success:
                        improved_count += 1
                        total_improvement += improvement
                    
                    results.append({
                        'id': doc_id,
                        'success': result.success,
                        'improvement': improvement,
                        'original_score': result.original_score.overall,
                        'optimized_score': result.optimized_score.overall
                    })
                else:
                    # Just analyze
                    analysis = self.analyze_document(content, doc_id, metadata)
                    
                    results.append({
                        'id': doc_id,
                        'quality_score': analysis.quality_metrics.overall,
                        'improvement_potential': analysis.improvement_potential,
                        'pattern_count': len(analysis.patterns.patterns)
                    })
                
            except Exception as e:
                logger.error(f"Failed to process document {i}: {e}")
                failed_count += 1
                results.append({
                    'id': doc_id if 'doc_id' in locals() else f"batch_{i}",
                    'error': str(e)
                })
        
        # Calculate statistics
        processed_count = len(documents) - failed_count
        avg_improvement = total_improvement / improved_count if improved_count > 0 else 0.0
        
        return BatchProcessingResult(
            total_documents=len(documents),
            processed=processed_count,
            improved=improved_count,
            failed=failed_count,
            average_improvement=avg_improvement,
            total_time=time.time() - start_time,
            documents=results
        )
    
    def _calculate_improvement_potential(self,
                                        quality_metrics: QualityMetrics,
                                        entropy_stats: Dict[str, Any],
                                        patterns: PatternAnalysis) -> float:
        """
        Calculate potential for improvement based on current state.
        
        Returns value between 0 (no improvement possible) and 1 (high potential).
        """
        # Quality gap
        quality_gap = self.config.target_quality - quality_metrics.overall
        quality_potential = max(0, min(quality_gap / self.config.target_quality, 1.0))
        
        # Pattern severity
        if patterns.patterns:
            avg_severity = sum(p.severity for p in patterns.patterns) / len(patterns.patterns)
            pattern_potential = avg_severity
        else:
            pattern_potential = 0.0
        
        # Entropy balance (too high or too low indicates issues)
        entropy_aggregate = entropy_stats.get('information_density', 0.5)
        entropy_deviation = abs(entropy_aggregate - 0.6)  # Optimal around 0.6
        entropy_potential = min(entropy_deviation * 2, 1.0)
        
        # Weighted combination
        potential = (
            quality_potential * 0.5 +
            pattern_potential * 0.3 +
            entropy_potential * 0.2
        )
        
        return min(max(potential, 0.0), 1.0)
    
    def _generate_recommendations(self,
                                 quality_metrics: QualityMetrics,
                                 entropy_stats: Dict[str, Any],
                                 patterns: PatternAnalysis) -> List[str]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []
        
        # Quality-based recommendations
        quality_suggestions = self.scorer.get_improvement_suggestions(quality_metrics)
        recommendations.extend(quality_suggestions[:3])  # Top 3 quality suggestions
        
        # Pattern-based recommendations
        high_priority_patterns = patterns.get_high_priority_patterns()
        for pattern in high_priority_patterns[:2]:  # Top 2 patterns
            recommendations.append(f"{pattern.suggested_action} ({pattern.name})")
        
        # Entropy-based recommendations
        if entropy_stats['redundancy'] > 0.7:
            recommendations.append("Reduce redundancy by consolidating repetitive content")
        elif entropy_stats['redundancy'] < 0.2:
            recommendations.append("Add more structure and patterns for better readability")
        
        if entropy_stats['vocabulary_richness'] < 0.3:
            recommendations.append("Enrich vocabulary to improve content diversity")
        
        # Limit to top 5 recommendations
        return recommendations[:5]
    
    def _identify_addressed_patterns(self,
                                    original_patterns: PatternAnalysis,
                                    optimized_content: str) -> List:
        """Identify which patterns were successfully addressed."""
        # Re-analyze optimized content
        new_patterns = self.pattern_recognizer.analyze(optimized_content)
        
        addressed = []
        original_pattern_names = {p.name for p in original_patterns.patterns}
        new_pattern_names = {p.name for p in new_patterns.patterns}
        
        # Patterns that no longer appear are considered addressed
        for pattern in original_patterns.patterns:
            if pattern.name not in new_pattern_names:
                addressed.append(pattern)
        
        return addressed
    
    def _store_analysis(self, analysis: DocumentAnalysis, metadata: Optional[Dict]):
        """Store analysis results in M002 storage."""
        if not self.storage:
            return
        
        try:
            # Prepare document data
            doc_data = {
                'title': f"Analysis_{analysis.document_id or 'unknown'}",
                'content': json.dumps(analysis.to_dict(), indent=2),
                'type': 'analysis',
                'metadata': {
                    'quality_score': analysis.quality_metrics.overall,
                    'improvement_potential': analysis.improvement_potential,
                    'pattern_count': len(analysis.patterns.patterns),
                    'timestamp': analysis.timestamp.isoformat()
                }
            }
            
            if metadata:
                doc_data['metadata'].update(metadata)
            
            # Store in M002
            self.storage.create_document(DocumentData(**doc_data))
            
        except Exception as e:
            logger.error(f"Failed to store analysis: {e}")
    
    def _store_optimization(self,
                          document_id: Optional[str],
                          result: OptimizationResult,
                          metadata: Optional[Dict]):
        """Store optimization results in M002 storage."""
        if not self.storage:
            return
        
        try:
            # Prepare optimized document
            doc_data = {
                'title': f"Optimized_{document_id or 'document'}",
                'content': result.optimized_content,
                'type': 'optimized',
                'metadata': {
                    'original_score': result.original_score.overall,
                    'optimized_score': result.optimized_score.overall,
                    'improvement': result.improvement_percentage(),
                    'iterations': result.iterations,
                    'success': result.success,
                    'elapsed_time': result.elapsed_time
                }
            }
            
            if metadata:
                doc_data['metadata'].update(metadata)
            
            # Store in M002
            self.storage.create_document(DocumentData(**doc_data))
            
        except Exception as e:
            logger.error(f"Failed to store optimization: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get engine performance metrics.
        
        Returns:
            Dictionary with performance and quality metrics
        """
        metrics = self.metrics.copy()
        
        # Calculate averages
        if metrics['documents_analyzed'] > 0:
            metrics['avg_processing_time'] = (
                metrics['processing_time'] / metrics['documents_analyzed']
            )
            metrics['avg_patterns_per_doc'] = (
                metrics['patterns_identified'] / metrics['documents_analyzed']
            )
        
        if metrics['documents_optimized'] > 0:
            metrics['avg_improvement'] = (
                metrics['total_improvement'] / metrics['documents_optimized']
            )
        
        # Add component statistics
        metrics['pattern_statistics'] = self.pattern_recognizer.get_pattern_statistics()
        
        return metrics
    
    def reset_metrics(self):
        """Reset performance metrics."""
        self.metrics = {
            'documents_analyzed': 0,
            'documents_optimized': 0,
            'total_improvement': 0.0,
            'patterns_identified': 0,
            'processing_time': 0.0
        }
        logger.info("Metrics reset")