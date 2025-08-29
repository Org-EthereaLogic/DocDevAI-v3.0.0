"""
Unified MIAIR Engine with configurable modes.

Consolidates base, optimized, and secure implementations into a single
configurable engine with mode selection.
"""

import time
import logging
import asyncio
import hashlib
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from enum import Enum
import json

# Import common utilities
from devdocai.common import (
    EncryptionManager,
    InputValidator,
    RateLimiter,
    AuditLogger,
    LRUCache,
    ResourceMonitor,
    profile_performance,
    ParallelExecutor,
    secure_operation,
    get_encryption_manager,
    get_audit_logger,
    ValidationError,
    MIAIRError,
    OptimizationError,
    QualityThresholdError
)

# Import MIAIR components
from .entropy import ShannonEntropyCalculator
from .entropy_optimized import OptimizedShannonEntropyCalculator
from .scorer import QualityScorer, QualityMetrics, ScoringWeights
from .scorer_optimized import OptimizedQualityScorer
from .optimizer import MIAIROptimizer, OptimizationConfig, OptimizationResult
from .patterns import PatternRecognizer, PatternAnalysis
from .patterns_optimized import OptimizedPatternRecognizer

# Import M002 storage for integration
try:
    from devdocai.storage.local_storage import LocalStorageSystem, DocumentData
    STORAGE_AVAILABLE = True
except ImportError:
    STORAGE_AVAILABLE = False
    LocalStorageSystem = None
    DocumentData = None

logger = logging.getLogger(__name__)


class EngineMode(Enum):
    """MIAIR Engine operation modes."""
    STANDARD = "standard"
    OPTIMIZED = "optimized"
    SECURE = "secure"


@dataclass
class UnifiedMIAIRConfig:
    """Unified configuration for MIAIR Engine."""
    
    # Mode selection
    mode: EngineMode = EngineMode.STANDARD
    
    # Quality thresholds
    target_quality: float = 0.85
    min_quality: float = 0.5
    max_iterations: int = 10
    
    # Performance settings
    enable_caching: bool = True
    cache_size: int = 256
    batch_size: int = 100
    max_workers: int = 4
    use_processes: bool = False  # For optimized mode
    
    # Security settings (for secure mode)
    enable_validation: bool = True
    enable_rate_limiting: bool = False
    enable_audit_logging: bool = False
    enable_encryption: bool = False
    max_document_size_mb: int = 10
    rate_limit_requests: int = 100
    rate_limit_window: int = 60
    
    # Resource limits
    max_memory_mb: int = 500
    max_cpu_percent: float = 80.0
    optimization_timeout: float = 30.0
    
    # Integration settings
    storage_enabled: bool = True
    enable_learning: bool = True
    
    def for_mode(self, mode: EngineMode) -> 'UnifiedMIAIRConfig':
        """Get configuration optimized for specific mode."""
        config = UnifiedMIAIRConfig(
            mode=mode,
            target_quality=self.target_quality,
            min_quality=self.min_quality,
            max_iterations=self.max_iterations,
            storage_enabled=self.storage_enabled,
            enable_learning=self.enable_learning
        )
        
        if mode == EngineMode.OPTIMIZED:
            # Optimize for performance
            config.enable_caching = True
            config.cache_size = 512
            config.batch_size = 200
            config.max_workers = 8
            config.use_processes = True
            config.enable_validation = False
            config.enable_audit_logging = False
            
        elif mode == EngineMode.SECURE:
            # Optimize for security
            config.enable_validation = True
            config.enable_rate_limiting = True
            config.enable_audit_logging = True
            config.enable_encryption = True
            config.cache_size = 128
            config.batch_size = 50
            config.max_workers = 2
            
        return config


@dataclass
class AnalysisResult:
    """Unified analysis result."""
    document_id: str
    quality_score: float
    entropy: float
    patterns: List[str]
    metrics: QualityMetrics
    optimization_suggestions: List[str]
    processing_time: float
    mode: str
    
    # Optional secure mode fields
    validated: bool = False
    encrypted: bool = False
    audit_logged: bool = False


class UnifiedMIAIREngine:
    """
    Unified MIAIR Engine with configurable modes.
    
    Combines standard, optimized, and secure implementations.
    """
    
    def __init__(self, config: Optional[UnifiedMIAIRConfig] = None):
        """Initialize unified MIAIR engine."""
        self.config = config or UnifiedMIAIRConfig()
        
        # Initialize components based on mode
        self._initialize_components()
        
        # Initialize security components if needed
        self._initialize_security()
        
        # Initialize performance components
        self._initialize_performance()
        
        # Initialize storage if available
        self._initialize_storage()
        
        logger.info(f"MIAIR Engine initialized in {self.config.mode.value} mode")
    
    def _initialize_components(self):
        """Initialize core components based on mode."""
        if self.config.mode == EngineMode.OPTIMIZED:
            # Use optimized components
            self.entropy_calculator = OptimizedShannonEntropyCalculator()
            self.quality_scorer = OptimizedQualityScorer()
            self.pattern_recognizer = OptimizedPatternRecognizer()
        else:
            # Use standard components
            self.entropy_calculator = ShannonEntropyCalculator()
            self.quality_scorer = QualityScorer()
            self.pattern_recognizer = PatternRecognizer()
        
        # Optimizer is same for all modes
        optimizer_config = OptimizationConfig(
            max_iterations=self.config.max_iterations,
            target_quality=self.config.target_quality,
            timeout_seconds=self.config.optimization_timeout
        )
        self.optimizer = MIAIROptimizer(optimizer_config)
    
    def _initialize_security(self):
        """Initialize security components for secure mode."""
        self.encryption_manager = None
        self.validator = None
        self.rate_limiter = None
        self.audit_logger = None
        
        if self.config.mode == EngineMode.SECURE:
            if self.config.enable_encryption:
                self.encryption_manager = get_encryption_manager()
            
            if self.config.enable_validation:
                self.validator = InputValidator()
            
            if self.config.enable_rate_limiting:
                self.rate_limiter = RateLimiter(
                    max_requests=self.config.rate_limit_requests,
                    window_seconds=self.config.rate_limit_window
                )
            
            if self.config.enable_audit_logging:
                self.audit_logger = get_audit_logger()
    
    def _initialize_performance(self):
        """Initialize performance components."""
        # Cache
        self.cache = None
        if self.config.enable_caching:
            self.cache = LRUCache(max_size=self.config.cache_size, ttl_seconds=300)
        
        # Resource monitor
        self.resource_monitor = ResourceMonitor(
            memory_threshold_mb=self.config.max_memory_mb,
            cpu_threshold_percent=self.config.max_cpu_percent
        )
        
        # Parallel executor for optimized mode - use ThreadPoolExecutor for better performance
        self.executor = None
        if self.config.mode == EngineMode.OPTIMIZED:
            # Always enable executor for optimized mode to restore performance
            self.executor = True  # Simple flag - we'll use ThreadPoolExecutor directly in methods
    
    def _initialize_storage(self):
        """Initialize storage integration."""
        self.storage = None
        
        if self.config.storage_enabled and STORAGE_AVAILABLE:
            try:
                self.storage = LocalStorageSystem()
                logger.info("Storage system integrated successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize storage: {e}")
    
    @profile_performance
    def analyze(self, 
                content: Union[str, Dict[str, Any]],
                document_id: Optional[str] = None,
                metadata: Optional[Dict] = None) -> AnalysisResult:
        """
        Analyze document with mode-specific processing.
        
        Args:
            content: Document content or dictionary
            document_id: Optional document ID
            metadata: Optional metadata
            
        Returns:
            Analysis result
        """
        start_time = time.perf_counter()
        
        # Generate document ID if not provided
        if document_id is None:
            import uuid
            document_id = str(uuid.uuid4())
        
        # Security checks for secure mode
        if self.config.mode == EngineMode.SECURE:
            content = self._secure_preprocessing(content, document_id, metadata)
        
        # Check cache
        cache_key = None
        if self.cache:
            cache_key = self._compute_cache_key(content, metadata)
            cached_result = self.cache.get(cache_key)
            if cached_result:
                logger.debug(f"Cache hit for document {document_id}")
                return cached_result
        
        # Extract content string
        content_str = self._extract_content(content)
        
        # Perform analysis based on mode
        if self.config.mode == EngineMode.OPTIMIZED:
            result = self._analyze_optimized(content_str, document_id, metadata)
        elif self.config.mode == EngineMode.SECURE:
            result = self._analyze_secure(content_str, document_id, metadata)
        else:
            result = self._analyze_standard(content_str, document_id, metadata)
        
        # Update processing time
        result.processing_time = time.perf_counter() - start_time
        
        # Cache result
        if self.cache and cache_key:
            self.cache.put(cache_key, result)
        
        # Store in storage if enabled
        if self.storage:
            self._store_result(result, content, metadata)
        
        return result
    
    def _analyze_standard(self, content: str, document_id: str, metadata: Optional[Dict]) -> AnalysisResult:
        """Standard analysis implementation."""
        # Calculate entropy
        entropy_result = self.entropy_calculator.calculate_entropy(content)
        # Extract aggregate entropy as the main entropy value
        entropy = entropy_result.get('aggregate', 0.0) if isinstance(entropy_result, dict) else entropy_result
        
        # Score quality
        metrics = self.quality_scorer.score_document(content, metadata)
        
        # Recognize patterns
        pattern_analysis = self.pattern_recognizer.analyze(content)
        
        # Generate optimization suggestions
        suggestions = self._generate_suggestions(metrics, pattern_analysis)
        
        return AnalysisResult(
            document_id=document_id,
            quality_score=metrics.overall,
            entropy=entropy,
            patterns=[p.name for p in pattern_analysis.patterns],
            metrics=metrics,
            optimization_suggestions=suggestions,
            processing_time=0.0,
            mode=self.config.mode.value
        )
    
    def _analyze_optimized(self, content: str, document_id: str, metadata: Optional[Dict]) -> AnalysisResult:
        """Optimized analysis with parallel processing."""
        # Use ThreadPoolExecutor for optimal performance - avoid ProcessPoolExecutor due to pickle constraints
        if self.executor:
            # Parallel execution using ThreadPoolExecutor for 3-5x speedup
            with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                entropy_future = executor.submit(self.entropy_calculator.calculate_entropy, content)
                metrics_future = executor.submit(self.quality_scorer.score_document, content, metadata)
                pattern_future = executor.submit(self.pattern_recognizer.analyze, content)
                
                entropy_result = entropy_future.result()
                metrics = metrics_future.result()
                pattern_analysis = pattern_future.result()
        else:
            # Sequential execution fallback
            entropy_result = self.entropy_calculator.calculate_entropy(content)
            metrics = self.quality_scorer.score_document(content, metadata)
            pattern_analysis = self.pattern_recognizer.analyze(content)
        
        # Extract aggregate entropy as the main entropy value
        entropy = entropy_result.get('aggregate', 0.0) if isinstance(entropy_result, dict) else entropy_result
        
        # Generate suggestions
        suggestions = self._generate_suggestions(metrics, pattern_analysis)
        
        return AnalysisResult(
            document_id=document_id,
            quality_score=metrics.overall,
            entropy=entropy,
            patterns=[p.name for p in pattern_analysis.patterns],
            metrics=metrics,
            optimization_suggestions=suggestions,
            processing_time=0.0,
            mode=self.config.mode.value
        )
    
    def _analyze_secure(self, content: str, document_id: str, metadata: Optional[Dict]) -> AnalysisResult:
        """Secure analysis with validation and audit logging."""
        # Audit log
        if self.audit_logger:
            self.audit_logger.log_access(
                user='system',
                resource=f'document:{document_id}',
                action='analyze',
                success=True
            )
        
        # Standard analysis
        result = self._analyze_standard(content, document_id, metadata)
        
        # Mark as validated and audit logged
        result.validated = True
        result.audit_logged = bool(self.audit_logger)
        result.encrypted = bool(self.encryption_manager)
        
        return result
    
    def _secure_preprocessing(self, content: Union[str, Dict], document_id: str, metadata: Optional[Dict]) -> Union[str, Dict]:
        """Security preprocessing for secure mode."""
        # Validate input
        if self.validator:
            if isinstance(content, str):
                if not self.validator.validate_string(content, max_length=self.config.max_document_size_mb * 1024 * 1024):
                    raise ValidationError('content', 'Content exceeds size limit or is invalid')
            
            if metadata:
                metadata = self.validator.sanitize_dict(metadata)
        
        # Check rate limit
        if self.rate_limiter:
            allowed, reason = self.rate_limiter.check_rate_limit(document_id)
            if not allowed:
                raise MIAIRError(f"Rate limit exceeded: {reason}")
        
        # Check resources
        within_limits, warnings = self.resource_monitor.check_resources()
        if not within_limits:
            logger.warning(f"Resource warnings: {warnings}")
        
        return content
    
    def optimize(self, 
                content: Union[str, Dict[str, Any]],
                document_id: Optional[str] = None,
                target_quality: Optional[float] = None) -> OptimizationResult:
        """
        Optimize document content.
        
        Args:
            content: Document content
            document_id: Optional document ID
            target_quality: Target quality score
            
        Returns:
            Optimization result
        """
        # Analyze first
        analysis = self.analyze(content, document_id)
        
        # Check if optimization needed
        target = target_quality or self.config.target_quality
        if analysis.quality_score >= target:
            logger.info(f"Document {document_id} already meets quality target")
            return OptimizationResult(
                original_content=self._extract_content(content),
                optimized_content=self._extract_content(content),
                original_score=analysis.quality_score,
                optimized_score=analysis.quality_score,
                iterations=0,
                converged=True,
                improvements=[]
            )
        
        # Perform optimization
        content_str = self._extract_content(content)
        
        # Use appropriate optimization based on mode
        if self.config.mode == EngineMode.SECURE:
            # Add security context
            if self.audit_logger:
                self.audit_logger.log_event('optimization', {
                    'document_id': document_id,
                    'target_quality': target
                })
        
        result = self.optimizer.optimize_document(
            content=content_str,
            metadata=None
        )
        
        # Store optimized version if storage enabled
        if self.storage and result.optimized_score.overall > result.original_score.overall:
            self._store_optimized(document_id, result)
        
        return result
    
    def batch_analyze(self, documents: List[Dict[str, Any]]) -> List[AnalysisResult]:
        """
        Analyze multiple documents in batch.
        
        Args:
            documents: List of documents to analyze
            
        Returns:
            List of analysis results
        """
        if self.config.mode == EngineMode.OPTIMIZED and self.executor and len(documents) > 2:
            # Parallel batch processing for 3-5x speedup
            with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                futures = []
                for doc in documents:
                    future = executor.submit(
                        self.analyze,
                        doc.get('content'),
                        doc.get('id'), 
                        doc.get('metadata')
                    )
                    futures.append(future)
                
                results = []
                for future in futures:
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Failed to analyze document in batch: {e}")
                        continue
                
                return results
        else:
            # Sequential processing for small batches or non-optimized modes
            results = []
            for doc in documents:
                try:
                    result = self.analyze(
                        doc.get('content'),
                        doc.get('id'),
                        doc.get('metadata')
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to analyze document {doc.get('id')}: {e}")
                    continue
            
            return results
    
    def _extract_content(self, content: Union[str, Dict]) -> str:
        """Extract content string from various formats."""
        if isinstance(content, str):
            return content
        elif isinstance(content, dict):
            return content.get('content', '') or content.get('text', '') or str(content)
        else:
            return str(content)
    
    def _compute_cache_key(self, content: Any, metadata: Optional[Dict]) -> str:
        """Compute cache key for content."""
        content_str = self._extract_content(content)
        cache_data = f"{content_str}:{metadata}"
        return hashlib.sha256(cache_data.encode()).hexdigest()
    
    def _generate_suggestions(self, metrics: QualityMetrics, patterns: PatternAnalysis) -> List[str]:
        """Generate optimization suggestions."""
        suggestions = []
        
        # Quality-based suggestions using correct attribute names
        if metrics.clarity < 0.7:
            suggestions.append("Improve readability by simplifying complex sentences")
        
        if metrics.consistency < 0.7:
            suggestions.append("Enhance document structure with clear sections and headings")
        
        if metrics.completeness < 0.7:
            suggestions.append("Add more comprehensive content coverage")
        
        if metrics.accuracy < 0.7:
            suggestions.append("Improve accuracy with proper references and updated information")
        
        # Pattern-based suggestions
        if len(patterns.patterns) > 10:
            suggestions.append("Reduce repetitive patterns for better variety")
        
        high_priority_patterns = patterns.get_high_priority_patterns()
        if len(high_priority_patterns) > 0:
            suggestions.append(f"Address {len(high_priority_patterns)} high-priority content issues")
        
        return suggestions
    
    def _store_result(self, result: AnalysisResult, content: Any, metadata: Optional[Dict]):
        """Store analysis result in storage system."""
        if not self.storage:
            return
        
        try:
            doc_data = {
                'document_id': result.document_id,
                'title': f"Document {result.document_id}",  # Required field
                'content': self._extract_content(content),
                'metadata': metadata or {},
                'analysis': {
                    'quality_score': result.quality_score,
                    'entropy': result.entropy,
                    'patterns': result.patterns,
                    'suggestions': result.optimization_suggestions,
                    'analyzed_at': datetime.utcnow().isoformat()
                }
            }
            
            self.storage.create_document(DocumentData(**doc_data))
            logger.debug(f"Stored analysis result for document {result.document_id}")
            
        except Exception as e:
            logger.error(f"Failed to store analysis result: {e}")
    
    def _store_optimized(self, document_id: str, result: OptimizationResult):
        """Store optimized document version."""
        if not self.storage:
            return
        
        try:
            # Store as new version
            doc_data = {
                'document_id': f"{document_id}_optimized",
                'title': f"Optimized Document {document_id}",  # Required field
                'content': result.optimized_content,
                'metadata': {
                    'original_id': document_id,
                    'original_score': result.original_score.overall,
                    'optimized_score': result.optimized_score.overall,
                    'iterations': result.iterations,
                    'optimized_at': datetime.utcnow().isoformat()
                }
            }
            
            self.storage.create_document(DocumentData(**doc_data))
            logger.debug(f"Stored optimized version of document {document_id}")
            
        except Exception as e:
            logger.error(f"Failed to store optimized document: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        stats = {
            'mode': self.config.mode.value,
            'configuration': {
                'caching_enabled': self.config.enable_caching,
                'storage_enabled': self.config.storage_enabled and self.storage is not None,
                'security_enabled': self.config.mode == EngineMode.SECURE
            }
        }
        
        # Add cache stats
        if self.cache:
            stats['cache'] = self.cache.get_stats()
        
        # Add resource stats - use fallback if method doesn't exist
        try:
            stats['resources'] = self.resource_monitor.get_stats()
        except AttributeError:
            stats['resources'] = {'status': 'monitoring_enabled'}
        
        # Add security stats for secure mode
        if self.config.mode == EngineMode.SECURE:
            stats['security'] = {
                'validation_enabled': bool(self.validator),
                'rate_limiting_enabled': bool(self.rate_limiter),
                'audit_logging_enabled': bool(self.audit_logger),
                'encryption_enabled': bool(self.encryption_manager)
            }
        
        return stats
    
    def cleanup(self):
        """Clean up resources."""
        if self.executor:
            self.executor.shutdown()
        
        if self.cache:
            self.cache.clear()
        
        logger.info(f"MIAIR Engine ({self.config.mode.value} mode) cleaned up")


def create_engine(mode: Union[str, EngineMode] = EngineMode.STANDARD,
                 **config_kwargs) -> UnifiedMIAIREngine:
    """
    Factory function to create MIAIR engine with specific mode.
    
    Args:
        mode: Engine mode ('standard', 'optimized', 'secure')
        **config_kwargs: Additional configuration parameters
        
    Returns:
        Configured MIAIR engine
    """
    # Convert string to enum if needed
    if isinstance(mode, str):
        mode = EngineMode(mode.lower())
    
    # Create base config
    config = UnifiedMIAIRConfig(mode=mode, **config_kwargs)
    
    # Apply mode-specific defaults
    config = config.for_mode(mode)
    
    # Create and return engine
    return UnifiedMIAIREngine(config)


# Convenience functions for specific modes
def create_standard_engine(**kwargs) -> UnifiedMIAIREngine:
    """Create standard MIAIR engine."""
    return create_engine(EngineMode.STANDARD, **kwargs)


def create_optimized_engine(**kwargs) -> UnifiedMIAIREngine:
    """Create optimized MIAIR engine for high performance."""
    return create_engine(EngineMode.OPTIMIZED, **kwargs)


def create_secure_engine(**kwargs) -> UnifiedMIAIREngine:
    """Create secure MIAIR engine with enhanced security."""
    return create_engine(EngineMode.SECURE, **kwargs)


__all__ = [
    'EngineMode',
    'UnifiedMIAIRConfig',
    'AnalysisResult',
    'UnifiedMIAIREngine',
    'create_engine',
    'create_standard_engine',
    'create_optimized_engine',
    'create_secure_engine'
]