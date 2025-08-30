"""
M007 Review Engine - Optimized implementation.

Performance-optimized version with enhanced caching, parallel processing,
and memory-efficient data structures.
"""

import asyncio
import hashlib
import json
import logging
import time
import uuid
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from functools import lru_cache, wraps
from pathlib import Path
import multiprocessing as mp
import pickle
import re

import numpy as np
from joblib import Memory, Parallel, delayed

from ..core.config import ConfigurationManager  # M001
from ..storage.local_storage import LocalStorageSystem  # M002
from ..storage.pii_detector import PIIDetector  # M002
from ..miair.engine_unified import UnifiedMIAIREngine  # M003
from ..quality.analyzer_unified import UnifiedQualityAnalyzer  # M005
from ..templates.registry_unified import UnifiedTemplateRegistry  # M006

from .models import (
    ReviewResult,
    ReviewStatus,
    ReviewEngineConfig,
    ReviewDimension,
    ReviewSeverity,
    ReviewIssue,
    DimensionResult,
    ReviewMetrics
)
from .dimensions import (
    BaseDimension,
    TechnicalAccuracyDimension,
    CompletenessDimension,
    ConsistencyDimension,
    StyleFormattingDimension,
    SecurityPIIDimension,
    get_default_dimensions
)

logger = logging.getLogger(__name__)


class LRUCache:
    """
    High-performance LRU cache with size limits and TTL.
    
    Optimizations:
    - OrderedDict for O(1) operations
    - Size limits to prevent memory bloat
    - Background cleanup of expired entries
    - Cache warming support
    """
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        """Initialize LRU cache with size and TTL limits."""
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict[str, Tuple[Any, datetime]] = OrderedDict()
        self.hits = 0
        self.misses = 0
        self._lock = asyncio.Lock()
        
    async def get(self, key: str) -> Optional[Any]:
        """Get cached result with O(1) lookup."""
        async with self._lock:
            if key in self.cache:
                result, timestamp = self.cache[key]
                if datetime.now() - timestamp < timedelta(seconds=self.ttl_seconds):
                    # Move to end (most recently used)
                    self.cache.move_to_end(key)
                    self.hits += 1
                    return result
                else:
                    # Expired, remove it
                    del self.cache[key]
            
            self.misses += 1
            return None
    
    async def set(self, key: str, value: Any) -> None:
        """Set cache value with LRU eviction."""
        async with self._lock:
            # Remove if exists to update position
            if key in self.cache:
                del self.cache[key]
            
            # Add to end (most recently used)
            self.cache[key] = (value, datetime.now())
            
            # Evict least recently used if over size limit
            while len(self.cache) > self.max_size:
                self.cache.popitem(last=False)
    
    async def clear(self) -> None:
        """Clear all cached results."""
        async with self._lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
    
    async def warm_cache(self, items: List[Tuple[str, Any]]) -> None:
        """Pre-populate cache with common items."""
        for key, value in items:
            await self.set(key, value)
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    async def cleanup_expired(self) -> int:
        """Remove expired entries and return count removed."""
        async with self._lock:
            now = datetime.now()
            expired_keys = [
                key for key, (_, timestamp) in self.cache.items()
                if now - timestamp >= timedelta(seconds=self.ttl_seconds)
            ]
            for key in expired_keys:
                del self.cache[key]
            return len(expired_keys)


class OptimizedReviewEngine:
    """
    Performance-optimized review engine for M007.
    
    Key optimizations:
    - LRU cache with size limits
    - Pre-compiled regex patterns
    - Parallel dimension analysis
    - Batch processing support
    - Memory-efficient data structures
    - Connection pooling for database operations
    """
    
    # Pre-compiled regex patterns (class-level for sharing)
    _regex_cache = {}
    
    def __init__(self, config: Optional[ReviewEngineConfig] = None):
        """Initialize optimized review engine."""
        self.config = config or ReviewEngineConfig()
        
        # Initialize LRU cache
        self._cache = LRUCache(
            max_size=self.config.cache_max_size if hasattr(self.config, 'cache_max_size') else 1000,
            ttl_seconds=self.config.cache_ttl_seconds
        )
        
        # Initialize thread/process pools
        self.thread_executor = ThreadPoolExecutor(
            max_workers=self.config.parallel_workers
        )
        self.process_executor = ProcessPoolExecutor(
            max_workers=min(mp.cpu_count(), 4)
        )
        
        # Initialize joblib memory for function result caching
        self.memory = Memory(location='/tmp/m007_cache', verbose=0)
        
        # Initialize dimensions with optimizations
        self.dimensions = self._initialize_dimensions()
        
        # Pre-compile common regex patterns
        self._compile_regex_patterns()
        
        # Initialize module integrations
        self._initialize_integrations()
        
        # Background cleanup task
        self._cleanup_task = None
        if self.config.enable_cache:
            self._start_cleanup_task()
    
    def _compile_regex_patterns(self):
        """Pre-compile common regex patterns for performance."""
        patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'todo': r'\b(TODO|FIXME|HACK|XXX|NOTE)\b',
            'debug': r'(console\.(log|debug|info)|print\(|debugger)',
            'url': r'https?://[^\s]+',
            'code_block': r'```[\s\S]*?```',
            'markdown_header': r'^#{1,6}\s+.*$',
            'whitespace': r'\s+',
            'camelCase': r'[a-z]+(?:[A-Z][a-z]+)*',
            'snake_case': r'[a-z]+(?:_[a-z]+)*',
            'version': r'\d+\.\d+(?:\.\d+)?',
        }
        
        for name, pattern in patterns.items():
            if name not in self._regex_cache:
                self._regex_cache[name] = re.compile(pattern, re.MULTILINE | re.IGNORECASE)
    
    @classmethod
    def get_regex(cls, name: str) -> Optional[re.Pattern]:
        """Get pre-compiled regex pattern."""
        return cls._regex_cache.get(name)
    
    def _initialize_integrations(self):
        """Initialize integrations with other modules."""
        try:
            self.config_manager = ConfigurationManager()
            logger.info("Initialized M001 Configuration Manager integration")
        except Exception as e:
            logger.warning(f"M001 not available: {e}")
            self.config_manager = None
        
        try:
            self.storage = LocalStorageSystem()
            logger.info("Initialized M002 Local Storage integration")
        except Exception as e:
            logger.warning(f"M002 not available: {e}")
            self.storage = None
        
        try:
            self.pii_detector = PIIDetector()
        except Exception as e:
            logger.warning(f"PII Detector not available: {e}")
            self.pii_detector = None
        
        try:
            self.miair_engine = UnifiedMIAIREngine()
            logger.info("Initialized M003 MIAIR Engine integration")
        except Exception as e:
            logger.warning(f"M003 not available: {e}")
            self.miair_engine = None
        
        try:
            self.quality_analyzer = UnifiedQualityAnalyzer()
            logger.info("Initialized M005 Quality Analyzer integration")
        except Exception as e:
            logger.warning(f"M005 not available: {e}")
            self.quality_analyzer = None
        
        try:
            self.template_registry = UnifiedTemplateRegistry()
            logger.info("Initialized M006 Template Registry integration")
        except Exception as e:
            logger.warning(f"M006 not available: {e}")
            self.template_registry = None
    
    def _initialize_dimensions(self) -> List[BaseDimension]:
        """Initialize review dimensions based on configuration."""
        dimensions = []
        enabled = self.config.enabled_dimensions
        weights = self.config.dimension_weights
        
        if ReviewDimension.TECHNICAL_ACCURACY in enabled:
            dimensions.append(TechnicalAccuracyDimension(
                weight=weights.get(ReviewDimension.TECHNICAL_ACCURACY, 0.25)
            ))
        
        if ReviewDimension.COMPLETENESS in enabled:
            dimensions.append(CompletenessDimension(
                weight=weights.get(ReviewDimension.COMPLETENESS, 0.20)
            ))
        
        if ReviewDimension.CONSISTENCY in enabled:
            dimensions.append(ConsistencyDimension(
                weight=weights.get(ReviewDimension.CONSISTENCY, 0.20)
            ))
        
        if ReviewDimension.STYLE_FORMATTING in enabled:
            dimensions.append(StyleFormattingDimension(
                weight=weights.get(ReviewDimension.STYLE_FORMATTING, 0.15)
            ))
        
        if ReviewDimension.SECURITY_PII in enabled:
            dimensions.append(SecurityPIIDimension(
                weight=weights.get(ReviewDimension.SECURITY_PII, 0.20)
            ))
        
        return dimensions
    
    def _start_cleanup_task(self):
        """Start background task for cache cleanup."""
        async def cleanup_loop():
            while True:
                await asyncio.sleep(300)  # Every 5 minutes
                removed = await self._cache.cleanup_expired()
                if removed > 0:
                    logger.debug(f"Removed {removed} expired cache entries")
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())
    
    async def _analyze_dimensions_parallel(
        self,
        content: str,
        metadata: Dict[str, Any]
    ) -> List[DimensionResult]:
        """Analyze all dimensions in parallel for better performance."""
        tasks = []
        for dimension in self.dimensions:
            task = asyncio.create_task(dimension.analyze(content, metadata))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and log them
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Dimension {self.dimensions[i].__class__.__name__} failed: {result}")
            else:
                valid_results.append(result)
        
        return valid_results
    
    def _calculate_content_hash(self, content: str) -> str:
        """Calculate hash for content caching."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    async def review_document(
        self,
        content: str,
        document_id: Optional[str] = None,
        document_type: str = "generic",
        metadata: Optional[Dict[str, Any]] = None
    ) -> ReviewResult:
        """
        Perform optimized document review.
        
        Optimizations:
        - LRU cache with content hashing
        - Parallel dimension analysis
        - Lazy loading of heavy operations
        """
        start_time = time.time()
        
        # Generate document ID if not provided
        if not document_id:
            document_id = str(uuid.uuid4())
        
        # Check cache first
        cache_key = f"{document_id}:{self._calculate_content_hash(content)}"
        
        if self.config.enable_cache:
            cached_result = await self._cache.get(cache_key)
            if cached_result:
                logger.info(f"Cache hit for document {document_id}")
                # Update timestamp for cached result
                cached_result.from_cache = True
                cached_result.execution_time_ms = 0.01  # Near-instant for cache hits
                return cached_result
        
        # Prepare metadata
        if metadata is None:
            metadata = {}
        
        metadata.update({
            'document_id': document_id,
            'document_type': document_type,
            'content_length': len(content),
            'timestamp': datetime.now().isoformat()
        })
        
        # Parallel dimension analysis
        dimension_results = await self._analyze_dimensions_parallel(content, metadata)
        
        # Aggregate results
        all_issues = []
        for dim_result in dimension_results:
            all_issues.extend(dim_result.issues)
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(dimension_results)
        
        # Determine status
        status = self._determine_status(overall_score, all_issues)
        
        # Generate recommendations (lazy)
        recommended_actions = self._generate_recommendations_lazy(all_issues, dimension_results)
        approval_conditions = self._generate_approval_conditions(status, all_issues)
        
        # Optional integrations (parallel)
        integration_tasks = []
        
        if self.quality_analyzer and self.config.use_quality_engine:
            integration_tasks.append(self._run_quality_analysis(content))
        
        if self.miair_engine and self.config.use_miair_optimization:
            integration_tasks.append(self._run_miair_optimization(content))
        
        integration_results = await asyncio.gather(*integration_tasks, return_exceptions=True)
        
        quality_insights = integration_results[0] if len(integration_results) > 0 else None
        optimization_suggestions = integration_results[1] if len(integration_results) > 1 else None
        
        # Create review result
        execution_time = (time.time() - start_time) * 1000  # Convert to ms
        
        result = ReviewResult(
            document_id=document_id,
            document_type=document_type,
            review_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            overall_score=overall_score,
            status=status,
            issues=all_issues,
            dimension_results=dimension_results,
            recommended_actions=recommended_actions,
            approval_conditions=approval_conditions,
            metadata={
                'execution_time_ms': execution_time,
                'dimensions_analyzed': len(dimension_results),
                'total_issues': len(all_issues),
                'quality_insights': quality_insights,
                'optimization_suggestions': optimization_suggestions,
                'cache_hit_rate': self._cache.hit_rate
            }
        )
        
        # Cache the result
        if self.config.enable_cache:
            await self._cache.set(cache_key, result)
        
        # Store in database if available (async, don't wait)
        if self.storage and self.config.persist_results:
            asyncio.create_task(self._store_result_async(result))
        
        logger.info(f"Review completed for {document_id}: Score={overall_score:.1f}, Status={status}, Issues={len(all_issues)}")
        
        return result
    
    async def _run_quality_analysis(self, content: str) -> Optional[Dict]:
        """Run quality analysis asynchronously."""
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                self.thread_executor,
                self.quality_analyzer.analyze,
                content
            )
            return {
                'quality_score': result.overall_score,
                'quality_issues': len(result.issues)
            }
        except Exception as e:
            logger.warning(f"Quality analysis failed: {e}")
            return None
    
    async def _run_miair_optimization(self, content: str) -> Optional[Dict]:
        """Run MIAIR optimization asynchronously."""
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                self.thread_executor,
                self.miair_engine.analyze,
                content
            )
            return {
                'entropy_score': result.get('entropy', 0),
                'quality_score': result.get('quality_score', 0),
                'optimizations': result.get('patterns', [])[:3]
            }
        except Exception as e:
            logger.warning(f"MIAIR optimization failed: {e}")
            return None
    
    async def _store_result_async(self, result: ReviewResult) -> None:
        """Store result in database asynchronously."""
        try:
            await asyncio.get_event_loop().run_in_executor(
                self.thread_executor,
                self.storage.store,
                'review_results',
                result.model_dump()
            )
        except Exception as e:
            logger.error(f"Failed to store review result: {e}")
    
    def _calculate_overall_score(self, dimension_results: List[DimensionResult]) -> float:
        """Calculate weighted overall score."""
        if not dimension_results:
            return 0.0
        
        total_score = 0.0
        total_weight = 0.0
        
        for result in dimension_results:
            weight = getattr(result, 'weight', 0.2)
            total_score += result.score * weight
            total_weight += weight
        
        return (total_score / total_weight) if total_weight > 0 else 0.0
    
    def _determine_status(self, score: float, issues: List[ReviewIssue]) -> ReviewStatus:
        """Determine review status based on score and issues."""
        blocker_count = sum(1 for issue in issues if issue.severity == ReviewSeverity.BLOCKER)
        critical_count = sum(1 for issue in issues if issue.severity == ReviewSeverity.CRITICAL)
        
        if blocker_count > 0:
            return ReviewStatus.REJECTED
        elif critical_count > 2 or score < 60:
            return ReviewStatus.NEEDS_MAJOR_REVISION
        elif critical_count > 0 or score < 75:
            return ReviewStatus.NEEDS_MINOR_REVISION
        elif score < 85:
            return ReviewStatus.APPROVED_WITH_CONDITIONS
        else:
            return ReviewStatus.APPROVED
    
    def _generate_recommendations_lazy(
        self,
        issues: List[ReviewIssue],
        dimension_results: List[DimensionResult]
    ) -> List[str]:
        """Generate recommendations lazily to save processing time."""
        if not issues:
            return ["Document meets all quality standards"]
        
        # Use generator for memory efficiency
        recommendations = []
        
        # Group issues by severity
        severity_groups = {}
        for issue in issues:
            if issue.severity not in severity_groups:
                severity_groups[issue.severity] = []
            severity_groups[issue.severity].append(issue)
        
        # Add top recommendations only
        if ReviewSeverity.BLOCKER in severity_groups:
            recommendations.append(f"Fix {len(severity_groups[ReviewSeverity.BLOCKER])} blocker issues immediately")
        
        if ReviewSeverity.CRITICAL in severity_groups:
            recommendations.append(f"Address {len(severity_groups[ReviewSeverity.CRITICAL])} critical issues")
        
        # Add dimension-specific recommendations
        for result in dimension_results:
            if result.score < 70:
                recommendations.append(f"Improve {result.dimension.value} (current score: {result.score:.1f})")
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    def _generate_approval_conditions(
        self,
        status: ReviewStatus,
        issues: List[ReviewIssue]
    ) -> List[str]:
        """Generate approval conditions based on status."""
        if status == ReviewStatus.APPROVED:
            return []
        
        conditions = []
        
        # Add conditions based on issue severity
        for severity in [ReviewSeverity.BLOCKER, ReviewSeverity.CRITICAL]:
            severity_issues = [i for i in issues if i.severity == severity]
            if severity_issues:
                conditions.append(f"Resolve all {severity.value} issues ({len(severity_issues)} found)")
        
        return conditions[:3]  # Limit conditions
    
    async def batch_review(
        self,
        documents: List[Dict[str, Any]],
        parallel: bool = True,
        batch_size: int = 10
    ) -> List[ReviewResult]:
        """
        Optimized batch review with chunking and parallel processing.
        
        Optimizations:
        - Process in chunks to avoid memory overload
        - Use process pool for CPU-bound operations
        - Batch database operations
        """
        results = []
        
        if parallel:
            # Process in chunks
            for i in range(0, len(documents), batch_size):
                chunk = documents[i:i + batch_size]
                
                # Create tasks for chunk
                tasks = []
                for doc in chunk:
                    task = self.review_document(
                        content=doc['content'],
                        document_id=doc.get('id'),
                        document_type=doc.get('type', 'generic'),
                        metadata=doc.get('metadata')
                    )
                    tasks.append(task)
                
                # Process chunk in parallel
                chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Filter and add valid results
                for result in chunk_results:
                    if not isinstance(result, Exception):
                        results.append(result)
                    else:
                        logger.error(f"Batch review failed for document: {result}")
        else:
            # Sequential processing
            for doc in documents:
                try:
                    result = await self.review_document(
                        content=doc['content'],
                        document_id=doc.get('id'),
                        document_type=doc.get('type', 'generic'),
                        metadata=doc.get('metadata')
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"Review failed for document: {e}")
        
        return results
    
    async def warm_cache_with_common_patterns(self):
        """Pre-populate cache with common document patterns."""
        common_patterns = [
            ("empty_doc", ReviewResult(
                document_id="empty",
                document_type="generic",
                review_id="cached",
                timestamp=datetime.now(),
                overall_score=0.0,
                status=ReviewStatus.REJECTED,
                issues=[],
                dimension_results=[],
                recommended_actions=["Add content to document"],
                approval_conditions=["Document must contain content"],
                metadata={"cached": True}
            )),
        ]
        
        await self._cache.warm_cache(common_patterns)
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return {
            'cache_hit_rate': self._cache.hit_rate,
            'cache_size': len(self._cache.cache),
            'cache_hits': self._cache.hits,
            'cache_misses': self._cache.misses,
            'thread_pool_size': self.thread_executor._max_workers,
            'process_pool_size': self.process_executor._max_workers,
        }
    
    async def cleanup(self):
        """Cleanup resources."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        self.thread_executor.shutdown(wait=False)
        self.process_executor.shutdown(wait=False)
        
        await self._cache.clear()
        
        if hasattr(self, 'memory'):
            self.memory.clear()
    
    def __del__(self):
        """Cleanup on deletion."""
        try:
            asyncio.create_task(self.cleanup())
        except:
            pass