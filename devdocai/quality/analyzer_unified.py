"""
Unified quality analyzer for M005 Quality Engine.

Combines all features from basic, optimized, and secure versions with
configurable operation modes for flexibility.
"""

import re
import time
import logging
import hashlib
import json
from typing import Dict, List, Optional, Any, Union, Iterator, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from pathlib import Path
from collections import deque
import threading

from .config import QualityEngineConfig, OperationMode, CacheStrategy
from .base_dimension import AnalysisContext
from .models import (
    QualityConfig, QualityReport, DimensionScore, QualityDimension,
    QualityIssue, SeverityLevel
)
from .scoring import QualityScorer
from .validators import DocumentValidator
from .exceptions import QualityEngineError, QualityGateFailure
from .security import QualitySecurityManager, SecureRegexHandler

# Import dimension analyzers
from .dimensions_unified import (
    UnifiedCompletenessAnalyzer,
    UnifiedClarityAnalyzer, 
    UnifiedStructureAnalyzer,
    UnifiedAccuracyAnalyzer,
    UnifiedFormattingAnalyzer
)

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages multi-level caching strategies."""
    
    def __init__(self, strategy: CacheStrategy, ttl: int = 3600):
        """Initialize cache manager."""
        self.strategy = strategy
        self.ttl = ttl
        self._memory_cache: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.Lock()
        
    def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        if self.strategy == CacheStrategy.NONE:
            return None
            
        with self._lock:
            if key in self._memory_cache:
                value, timestamp = self._memory_cache[key]
                if time.time() - timestamp < self.ttl:
                    return value
                else:
                    del self._memory_cache[key]
        return None
        
    def set(self, key: str, value: Any) -> None:
        """Set cached value."""
        if self.strategy == CacheStrategy.NONE:
            return
            
        with self._lock:
            self._memory_cache[key] = (value, time.time())
            
            # Implement simple LRU eviction
            if len(self._memory_cache) > 1000:
                # Remove oldest entries
                sorted_items = sorted(
                    self._memory_cache.items(),
                    key=lambda x: x[1][1]
                )
                for old_key, _ in sorted_items[:100]:
                    del self._memory_cache[old_key]
    
    def clear(self) -> None:
        """Clear all caches."""
        with self._lock:
            self._memory_cache.clear()


class UnifiedQualityAnalyzer:
    """Unified quality analyzer with configurable modes."""
    
    def __init__(self, config: Optional[QualityEngineConfig] = None):
        """Initialize unified analyzer."""
        self.config = config or QualityEngineConfig.from_env()
        
        # Initialize components based on configuration
        self._init_components()
        self._init_analyzers()
        self._init_security()
        self._init_performance()
        
        # Metrics tracking
        self._metrics = {
            'analyses_performed': 0,
            'total_time': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
    def _init_components(self) -> None:
        """Initialize core components."""
        self.scorer = QualityScorer()
        self.validator = DocumentValidator()
        self.cache = CacheManager(
            self.config.performance.cache_strategy,
            self.config.performance.cache_ttl_seconds
        )
        
    def _init_analyzers(self) -> None:
        """Initialize dimension analyzers."""
        # Create analyzers with appropriate configuration
        analyzer_config = {
            'performance_mode': self.config.mode in [OperationMode.OPTIMIZED, OperationMode.BALANCED],
            'security_enabled': self.config.mode in [OperationMode.SECURE, OperationMode.BALANCED]
        }
        
        self.analyzers = {
            QualityDimension.COMPLETENESS: UnifiedCompletenessAnalyzer(**analyzer_config),
            QualityDimension.CLARITY: UnifiedClarityAnalyzer(**analyzer_config),
            QualityDimension.STRUCTURE: UnifiedStructureAnalyzer(**analyzer_config),
            QualityDimension.ACCURACY: UnifiedAccuracyAnalyzer(**analyzer_config),
            QualityDimension.FORMATTING: UnifiedFormattingAnalyzer(**analyzer_config)
        }
        
    def _init_security(self) -> None:
        """Initialize security components."""
        if self.config.security.enable_input_validation:
            self.security_manager = QualitySecurityManager(self.config.security)
            self.regex_handler = SecureRegexHandler(
                max_complexity=self.config.security.max_regex_complexity
            )
        else:
            self.security_manager = None
            self.regex_handler = None
            
    def _init_performance(self) -> None:
        """Initialize performance components."""
        if self.config.performance.enable_parallel:
            self.executor = ThreadPoolExecutor(
                max_workers=self.config.performance.max_workers
            )
        else:
            self.executor = None
            
    def analyze(
        self,
        content: str,
        document_type: str = "markdown",
        metadata: Optional[Dict[str, Any]] = None
    ) -> QualityReport:
        """
        Analyze document quality.
        
        Args:
            content: Document content to analyze
            document_type: Type of document
            metadata: Additional metadata
            
        Returns:
            Quality report with scores and issues
        """
        start_time = time.perf_counter()
        
        try:
            # Security validation if enabled
            if self.security_manager:
                content = self.security_manager.validate_and_sanitize(content)
            
            # Create analysis context
            content_hash = hashlib.md5(content.encode()).hexdigest()
            context = AnalysisContext(
                content=content,
                content_hash=content_hash,
                document_type=document_type,
                metadata=metadata or {},
                cache_enabled=self.config.performance.cache_strategy != CacheStrategy.NONE,
                security_enabled=self.config.security.enable_input_validation,
                performance_mode=self.config.mode == OperationMode.OPTIMIZED
            )
            
            # Check cache
            cache_key = f"analysis:{content_hash}:{document_type}"
            cached_result = self.cache.get(cache_key)
            if cached_result:
                self._metrics['cache_hits'] += 1
                return cached_result
            
            self._metrics['cache_misses'] += 1
            
            # Perform analysis
            if self.config.performance.enable_parallel and self.executor:
                report = self._analyze_parallel(context)
            else:
                report = self._analyze_sequential(context)
            
            # Cache result
            self.cache.set(cache_key, report)
            
            # Update metrics
            elapsed = time.perf_counter() - start_time
            self._metrics['analyses_performed'] += 1
            self._metrics['total_time'] += elapsed
            
            # Add performance metadata
            report.metadata['analysis_time_ms'] = elapsed * 1000
            report.metadata['mode'] = self.config.mode.value
            
            return report
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise QualityEngineError(f"Analysis failed: {e}")
            
    def _analyze_sequential(self, context: AnalysisContext) -> QualityReport:
        """Perform sequential analysis."""
        dimension_scores = []
        all_issues = []
        
        for dimension, analyzer in self.analyzers.items():
            try:
                score = analyzer.analyze(context)
                dimension_scores.append(score)
                all_issues.extend(score.issues)
            except Exception as e:
                logger.warning(f"Dimension {dimension} analysis failed: {e}")
                # Create failed score
                dimension_scores.append(DimensionScore(
                    dimension=dimension,
                    score=0.0,
                    issues=[],
                    metadata={'error': str(e)}
                ))
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(dimension_scores)
        
        # Check quality gates
        gate_passed = self._check_quality_gates(overall_score, all_issues)
        
        return QualityReport(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            issues=all_issues,
            passed=gate_passed,
            timestamp=datetime.now(),
            metadata={
                'document_type': context.document_type,
                'content_hash': context.content_hash
            }
        )
        
    def _analyze_parallel(self, context: AnalysisContext) -> QualityReport:
        """Perform parallel analysis."""
        dimension_scores = []
        all_issues = []
        futures = {}
        
        # Submit analysis tasks
        for dimension, analyzer in self.analyzers.items():
            future = self.executor.submit(analyzer.analyze, context)
            futures[future] = dimension
        
        # Collect results
        for future in as_completed(futures):
            dimension = futures[future]
            try:
                score = future.result(timeout=self.config.security.timeout_seconds)
                dimension_scores.append(score)
                all_issues.extend(score.issues)
            except Exception as e:
                logger.warning(f"Dimension {dimension} analysis failed: {e}")
                dimension_scores.append(DimensionScore(
                    dimension=dimension,
                    score=0.0,
                    issues=[],
                    metadata={'error': str(e)}
                ))
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(dimension_scores)
        
        # Check quality gates
        gate_passed = self._check_quality_gates(overall_score, all_issues)
        
        return QualityReport(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            issues=all_issues,
            passed=gate_passed,
            timestamp=datetime.now(),
            metadata={
                'document_type': context.document_type,
                'content_hash': context.content_hash
            }
        )
        
    def _calculate_overall_score(self, dimension_scores: List[DimensionScore]) -> float:
        """Calculate weighted overall score."""
        weights = self.config.weights
        weight_map = {
            QualityDimension.COMPLETENESS: weights.completeness,
            QualityDimension.CLARITY: weights.clarity,
            QualityDimension.STRUCTURE: weights.structure,
            QualityDimension.ACCURACY: weights.accuracy,
            QualityDimension.FORMATTING: weights.formatting
        }
        
        total_score = 0.0
        for score in dimension_scores:
            weight = weight_map.get(score.dimension, 0.0)
            total_score += score.score * weight
            
        return round(total_score, 3)
        
    def _check_quality_gates(self, overall_score: float, issues: List[QualityIssue]) -> bool:
        """Check if quality gates pass."""
        thresholds = self.config.thresholds
        
        # Check overall score
        if overall_score < thresholds.min_overall_score:
            return False
        
        # Count issues by severity
        critical_count = sum(1 for i in issues if i.severity == SeverityLevel.CRITICAL)
        major_count = sum(1 for i in issues if i.severity == SeverityLevel.MAJOR)
        minor_count = sum(1 for i in issues if i.severity == SeverityLevel.MINOR)
        
        # Check issue thresholds
        if critical_count > thresholds.max_critical_issues:
            return False
        if major_count > thresholds.max_major_issues:
            return False
        if minor_count > thresholds.max_minor_issues:
            return False
            
        return True
        
    def analyze_batch(
        self,
        documents: List[Dict[str, Any]],
        parallel: bool = True
    ) -> List[QualityReport]:
        """
        Analyze multiple documents.
        
        Args:
            documents: List of documents to analyze
            parallel: Whether to process in parallel
            
        Returns:
            List of quality reports
        """
        if parallel and self.executor:
            futures = []
            for doc in documents:
                future = self.executor.submit(
                    self.analyze,
                    doc.get('content', ''),
                    doc.get('type', 'markdown'),
                    doc.get('metadata')
                )
                futures.append(future)
            
            reports = []
            for future in as_completed(futures):
                try:
                    report = future.result(timeout=self.config.security.timeout_seconds)
                    reports.append(report)
                except Exception as e:
                    logger.error(f"Batch analysis failed for document: {e}")
                    
            return reports
        else:
            return [
                self.analyze(
                    doc.get('content', ''),
                    doc.get('type', 'markdown'),
                    doc.get('metadata')
                )
                for doc in documents
            ]
            
    def get_metrics(self) -> Dict[str, Any]:
        """Get analyzer metrics."""
        metrics = self._metrics.copy()
        
        # Calculate derived metrics
        if metrics['analyses_performed'] > 0:
            metrics['avg_time_ms'] = (
                (metrics['total_time'] / metrics['analyses_performed']) * 1000
            )
            metrics['cache_hit_rate'] = (
                metrics['cache_hits'] / 
                (metrics['cache_hits'] + metrics['cache_misses'])
                if (metrics['cache_hits'] + metrics['cache_misses']) > 0
                else 0
            )
        
        # Add configuration info
        metrics['config'] = {
            'mode': self.config.mode.value,
            'parallel_enabled': self.config.performance.enable_parallel,
            'cache_strategy': self.config.performance.cache_strategy.value,
            'security_enabled': self.config.security.enable_input_validation
        }
        
        return metrics
        
    def clear_cache(self) -> None:
        """Clear all caches."""
        self.cache.clear()
        for analyzer in self.analyzers.values():
            analyzer.clear_cache()
            
    def close(self) -> None:
        """Clean up resources."""
        if self.executor:
            self.executor.shutdown(wait=True)
            
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()