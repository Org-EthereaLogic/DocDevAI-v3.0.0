"""
M003 MIAIR Engine - Unified Engine Implementation

Meta-Iterative AI Refinement Engine for documentation quality optimization.

Key Features:
- Unified architecture with 4 operation modes (BASIC, PERFORMANCE, SECURE, ENTERPRISE)
- Shannon entropy calculations with fractal-time scaling
- Integration with M001 Configuration Manager and M002 Storage System
- Comprehensive optimization strategies
- Quality measurement and improvement tracking
- Security validation and audit logging
- Performance optimization with caching

Mathematical Foundation:
- Formula: S = -Σ[p(xi) × log2(p(xi))] × f(Tx)
- Entropy threshold: 0.35 (maximum acceptable)
- Target entropy: 0.15 (optimized state)
- Quality gate: 85% minimum
- Target improvement: 60-75% (Pass 1: 40-50%)

This is the main entry point for all MIAIR operations, providing a consistent
interface while adapting behavior based on the selected operation mode.
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

# M001 Integration
try:
    from ..core.config import ConfigurationManager, MemoryMode
except ImportError:
    # Fallback for development
    ConfigurationManager = None
    MemoryMode = None

# M002 Integration  
try:
    from ..storage.storage_manager_unified import UnifiedStorageManager
except ImportError:
    # Fallback for development
    UnifiedStorageManager = None

from .models import (
    Document, OperationMode, MIAIRConfig, OptimizationResult, AnalysisResult,
    QualityScore, ValidationResult
)
from .entropy_calculator import EntropyCalculator
from .semantic_analyzer import SemanticAnalyzer
from .quality_metrics import QualityMetrics
from .optimization_strategies import create_strategy


logger = logging.getLogger(__name__)


class MIAIREngineUnified:
    """
    Meta-Iterative AI Refinement Engine with unified architecture.
    
    Supports 4 operation modes:
    - BASIC: Core functionality with simple optimization
    - PERFORMANCE: High-performance with caching and parallel processing
    - SECURE: Security-focused with validation and audit logging
    - ENTERPRISE: Full-featured with advanced analytics
    """
    
    def __init__(
        self,
        mode: OperationMode = OperationMode.BASIC,
        config_manager: Optional['ConfigurationManager'] = None,
        storage_manager: Optional['UnifiedStorageManager'] = None,
        miair_config: Optional[MIAIRConfig] = None
    ):
        """
        Initialize MIAIR Engine with specified operation mode.
        
        Args:
            mode: Operation mode determining feature set
            config_manager: Optional M001 configuration integration
            storage_manager: Optional M002 storage integration
            miair_config: Optional MIAIR-specific configuration override
        """
        self.mode = mode
        self.logger = logging.getLogger(f"{__name__}.{mode.value}")
        self.initialization_time = datetime.now(timezone.utc)
        
        # Integration points
        self.config_manager = config_manager
        self.storage_manager = storage_manager
        
        # Load configuration
        self.config = self._load_configuration(miair_config)
        
        # Initialize core components (always loaded)
        self.entropy_calculator = EntropyCalculator()
        self.semantic_analyzer = SemanticAnalyzer()
        self.quality_metrics = QualityMetrics()
        
        # Initialize mode-specific components
        self._initialize_mode_components()
        
        # Load optimization strategy based on mode
        self.strategy = create_strategy(mode)
        
        # Performance tracking
        self.stats = self._initialize_stats()
        
        self.logger.info(f"MIAIR Engine initialized in {mode.value} mode")
        self._log_initialization_details()
    
    def optimize(
        self,
        document: Document,
        target_entropy: Optional[float] = None,
        max_iterations: Optional[int] = None
    ) -> OptimizationResult:
        """
        Optimize document to achieve target entropy and quality improvement.
        
        Args:
            document: Document to optimize
            target_entropy: Override default target entropy
            max_iterations: Override default max iterations
            
        Returns:
            OptimizationResult with optimized document and metrics
            
        Raises:
            ValueError: If document validation fails
        """
        start_time = time.time()
        self.logger.debug(f"Starting optimization for document {document.id}")
        
        # Use configured defaults if not specified
        target_entropy = target_entropy or self.config.target_entropy
        max_iterations = max_iterations or self.config.max_iterations
        
        # Validate input (for secure modes)
        if self.mode in [OperationMode.SECURE, OperationMode.ENTERPRISE]:
            validation = self._validate_document(document)
            if not validation.valid:
                raise ValueError(f"Document validation failed: {validation.issues}")
        
        # Calculate initial metrics
        initial_entropy = self.entropy_calculator.calculate_entropy(document)
        initial_quality = self.quality_metrics.calculate_quality_score(document)
        
        self.logger.debug(
            f"Initial metrics - Entropy: {initial_entropy:.4f}, Quality: {initial_quality.overall:.2f}"
        )
        
        # Check if already optimized
        if (initial_entropy <= target_entropy and 
            self.quality_metrics.validate_quality_gate(initial_quality, self.config.quality_gate)):
            self.logger.info("Document already meets optimization targets")
            return self._create_optimization_result(
                document, document, initial_entropy, initial_entropy,
                0.0, 0, initial_quality, time.time() - start_time
            )
        
        # Perform optimization using selected strategy
        try:
            optimized_doc = self.strategy.optimize(
                document=document,
                target_entropy=target_entropy,
                max_iterations=max_iterations,
                entropy_calculator=self.entropy_calculator,
                quality_metrics=self.quality_metrics
            )
        except Exception as e:
            self.logger.error(f"Optimization failed: {e}")
            raise
        
        # Calculate final metrics
        final_entropy = self.entropy_calculator.calculate_entropy(optimized_doc)
        final_quality = self.quality_metrics.calculate_quality_score(optimized_doc)
        improvement = self._calculate_improvement(initial_entropy, final_entropy)
        iterations = optimized_doc.metadata.get('optimization_iterations', 0)
        
        execution_time = time.time() - start_time
        
        self.logger.info(
            f"Optimization completed - Entropy: {initial_entropy:.4f} -> {final_entropy:.4f}, "
            f"Quality: {initial_quality.overall:.2f} -> {final_quality.overall:.2f}, "
            f"Improvement: {improvement:.2f}%, Iterations: {iterations}, Time: {execution_time:.2f}s"
        )
        
        # Store results if storage available
        result = self._create_optimization_result(
            document, optimized_doc, initial_entropy, final_entropy,
            improvement, iterations, final_quality, execution_time
        )
        
        if self.storage_manager:
            self._store_optimization_results(document, optimized_doc, result)
        
        # Audit logging for secure modes
        if self.mode in [OperationMode.SECURE, OperationMode.ENTERPRISE]:
            self._audit_optimization(document.id, result)
        
        # Update statistics
        self._update_stats(result)
        
        return result
    
    def analyze(
        self,
        document: Document,
        include_patterns: bool = True
    ) -> AnalysisResult:
        """
        Analyze document without optimization.
        
        Args:
            document: Document to analyze
            include_patterns: Whether to include pattern analysis (slower)
            
        Returns:
            AnalysisResult with entropy, quality metrics, and improvement potential
        """
        self.logger.debug(f"Analyzing document {document.id}")
        
        # Use performance engine if available
        if self.mode in [OperationMode.PERFORMANCE, OperationMode.ENTERPRISE]:
            if hasattr(self, 'performance_engine'):
                return self.performance_engine.analyze(document)
        
        # Calculate entropy
        entropy = self.entropy_calculator.calculate_entropy(document)
        
        # Calculate quality score
        quality_score = self.quality_metrics.calculate_quality_score(document)
        
        # Extract semantic elements
        semantic_elements = self.semantic_analyzer.extract_semantic_elements(document)
        
        # Calculate improvement potential
        improvement_potential = self._estimate_improvement_potential(
            current_entropy=entropy,
            target_entropy=self.config.target_entropy,
            current_quality=quality_score.overall
        )
        
        # Check quality gate
        meets_quality_gate = self.quality_metrics.validate_quality_gate(
            quality_score, self.config.quality_gate
        )
        
        # Pattern analysis (optional for performance)
        patterns = {}
        if include_patterns:
            pattern_analysis = self.semantic_analyzer.identify_patterns(semantic_elements)
            patterns = {
                'repetitions': pattern_analysis.repetitions,
                'structure_issues': pattern_analysis.structure_issues,
                'missing_elements': pattern_analysis.missing_elements,
                'coherence_score': pattern_analysis.coherence_score
            }
        
        result = AnalysisResult(
            entropy=entropy,
            quality_score=quality_score,
            semantic_elements=semantic_elements,
            improvement_potential=improvement_potential,
            meets_quality_gate=meets_quality_gate,
            patterns=patterns
        )
        
        self.logger.debug(
            f"Analysis completed - Entropy: {entropy:.4f}, Quality: {quality_score.overall:.2f}, "
            f"Improvement potential: {improvement_potential:.2f}%"
        )
        
        return result
    
    def get_engine_stats(self) -> Dict[str, Any]:
        """
        Get engine performance statistics.
        
        Returns:
            Dictionary with performance and usage statistics
        """
        uptime = (datetime.now(timezone.utc) - self.initialization_time).total_seconds()
        
        return {
            'mode': self.mode.value,
            'uptime_seconds': uptime,
            'optimizations_completed': self.stats['optimizations_completed'],
            'analyses_completed': self.stats['analyses_completed'],
            'total_documents_processed': self.stats['total_documents_processed'],
            'average_optimization_time': self.stats['total_optimization_time'] / max(1, self.stats['optimizations_completed']),
            'average_improvement': self.stats['total_improvement'] / max(1, self.stats['optimizations_completed']),
            'quality_gate_pass_rate': self.stats['quality_gate_passes'] / max(1, self.stats['optimizations_completed']),
            'cache_hit_rate': getattr(self.strategy, 'cache', {}).get('hit_rate', 0.0),
            'configuration': self.config.model_dump() if hasattr(self.config, 'model_dump') else str(self.config)
        }
    
    def clear_cache(self):
        """Clear optimization cache (if available)."""
        if hasattr(self.strategy, 'cache') and hasattr(self.strategy.cache, 'clear'):
            self.strategy.cache.clear()
            self.logger.info("Optimization cache cleared")
        else:
            self.logger.debug("No cache available to clear")
    
    def validate_document(self, document: Document) -> ValidationResult:
        """
        Validate document for processing.
        
        Args:
            document: Document to validate
            
        Returns:
            ValidationResult with validation status and issues
        """
        return self._validate_document(document)
    
    def _load_configuration(self, miair_config: Optional[MIAIRConfig]) -> MIAIRConfig:
        """Load MIAIR configuration from various sources."""
        
        # Start with defaults
        config = MIAIRConfig()
        
        # Override with M001 configuration if available
        if self.config_manager:
            try:
                config_data = self.config_manager.get_config()
                
                # Map M001 configuration to MIAIR config
                if hasattr(config_data, 'quality'):
                    config.entropy_threshold = getattr(config_data.quality, 'entropy_threshold', 0.35)
                    config.target_entropy = getattr(config_data.quality, 'entropy_target', 0.15)
                    config.quality_gate = getattr(config_data.quality, 'quality_gate', 85.0)
                    config.max_iterations = getattr(config_data.quality, 'max_iterations', 7)
                
                # Map memory mode to performance settings
                memory_mode = getattr(self.config_manager, 'memory_mode', None)
                if memory_mode:
                    config = self._adjust_config_for_memory_mode(config, memory_mode)
                
            except Exception as e:
                self.logger.warning(f"Failed to load M001 configuration: {e}")
        
        # Override with explicit MIAIR config
        if miair_config:
            config = miair_config
        
        # Validate configuration
        self._validate_configuration(config)
        
        return config
    
    def _adjust_config_for_memory_mode(self, config: MIAIRConfig, memory_mode) -> MIAIRConfig:
        """Adjust configuration based on memory mode."""
        
        if memory_mode == 'baseline':
            config.cache_size = 50
            config.parallel_workers = 2
            config.max_iterations = 5
            
        elif memory_mode == 'standard':
            config.cache_size = 100
            config.parallel_workers = 4
            config.max_iterations = 7
            
        elif memory_mode == 'enhanced':
            config.cache_size = 200
            config.parallel_workers = 6
            config.max_iterations = 10
            
        elif memory_mode == 'performance':
            config.cache_size = 500
            config.parallel_workers = 8
            config.max_iterations = 12
        
        return config
    
    def _validate_configuration(self, config: MIAIRConfig):
        """Validate MIAIR configuration."""
        if config.target_entropy >= config.entropy_threshold:
            raise ValueError(
                f"Target entropy ({config.target_entropy}) must be less than "
                f"entropy threshold ({config.entropy_threshold})"
            )
        
        if config.quality_gate <= 0 or config.quality_gate > 100:
            raise ValueError(f"Quality gate must be between 0 and 100, got {config.quality_gate}")
    
    def _initialize_mode_components(self):
        """Initialize components based on operation mode."""
        
        if self.mode in [OperationMode.PERFORMANCE, OperationMode.ENTERPRISE]:
            # Import and initialize performance components
            from .performance_optimized import (
                MIAIREnginePerformance, OptimizedEntropyCalculator, 
                CacheManager, BatchProcessor
            )
            
            # Initialize performance engine
            self.performance_engine = MIAIREnginePerformance(
                cache_size=10000,
                max_workers=4,
                enable_async=True
            )
            
            # Replace default components with optimized versions
            self.entropy_calculator = self.performance_engine.entropy_calculator
            self.batch_processor = self.performance_engine.batch_processor
            self.cache_manager = self.performance_engine.cache_manager
            
            self.logger.debug("Performance mode - caching and parallel processing enabled")
            
        if self.mode in [OperationMode.SECURE, OperationMode.ENTERPRISE]:
            # Security components
            self.security_validator = self._create_security_validator()
            self.audit_logger = self._create_audit_logger()
            self.logger.debug("Security mode - validation and audit logging enabled")
            
        if self.mode == OperationMode.ENTERPRISE:
            # Enterprise-specific components
            self.advanced_analytics = self._create_analytics_engine()
            self.logger.debug("Enterprise mode - advanced analytics enabled")
    
    def _initialize_stats(self) -> Dict[str, float]:
        """Initialize performance statistics tracking."""
        return {
            'optimizations_completed': 0,
            'analyses_completed': 0,
            'total_documents_processed': 0,
            'total_optimization_time': 0.0,
            'total_improvement': 0.0,
            'quality_gate_passes': 0
        }
    
    def _create_security_validator(self) -> Dict[str, Any]:
        """Create security validator for secure modes."""
        return {
            'max_content_size': self.config.input_size_limit,
            'rate_limit_window': 60,  # seconds
            'rate_limit_count': self.config.rate_limit_per_minute,
            'blocked_patterns': [
                r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>',
                r'javascript:',
                r'data:text/html',
                r'vbscript:',
            ],
            'requests_in_window': {}
        }
    
    def _create_audit_logger(self) -> Dict[str, Any]:
        """Create audit logger for secure modes."""
        return {
            'log_entries': [],
            'enabled': True,
            'max_entries': 10000
        }
    
    def _create_analytics_engine(self) -> Dict[str, Any]:
        """Create analytics engine for enterprise mode."""
        return {
            'metrics': [],
            'enabled': True,
            'track_performance': True,
            'track_quality_trends': True,
            'generate_reports': True
        }
    
    def _validate_document(self, document: Document) -> ValidationResult:
        """Validate document for security and processing requirements."""
        issues = []
        risk_level = 'low'
        
        # Basic validation
        if not document.content or not document.content.strip():
            issues.append("Document content is empty")
            return ValidationResult(valid=False, issues=issues, risk_level='medium')
        
        # Size validation
        if len(document.content) > self.config.input_size_limit:
            issues.append(f"Document size ({len(document.content)} bytes) exceeds limit ({self.config.input_size_limit} bytes)")
            risk_level = 'high'
        
        # Security validation (for secure modes)
        if (hasattr(self, 'security_validator') and 
            self.mode in [OperationMode.SECURE, OperationMode.ENTERPRISE]):
            
            # Check for blocked patterns
            for pattern in self.security_validator['blocked_patterns']:
                import re
                if re.search(pattern, document.content, re.IGNORECASE):
                    issues.append(f"Content contains potentially unsafe pattern: {pattern}")
                    risk_level = 'high'
            
            # Rate limiting check
            current_time = time.time()
            window_start = current_time - self.security_validator['rate_limit_window']
            
            # Clean old entries
            self.security_validator['requests_in_window'] = {
                k: v for k, v in self.security_validator['requests_in_window'].items()
                if v > window_start
            }
            
            # Check rate limit (simplified - using document ID as identifier)
            request_count = len([
                t for t in self.security_validator['requests_in_window'].values()
                if t > window_start
            ])
            
            if request_count >= self.security_validator['rate_limit_count']:
                issues.append("Rate limit exceeded")
                risk_level = 'medium'
            else:
                # Record this request
                self.security_validator['requests_in_window'][document.id] = current_time
        
        return ValidationResult(
            valid=len(issues) == 0,
            issues=issues,
            risk_level=risk_level,
            details={'validation_time': time.time(), 'mode': self.mode.value}
        )
    
    def _calculate_improvement(self, initial_entropy: float, final_entropy: float) -> float:
        """Calculate improvement percentage from entropy reduction."""
        if initial_entropy == 0:
            return 100.0 if final_entropy < initial_entropy else 0.0
        
        # Calculate entropy improvement (lower entropy is better)
        entropy_improvement = max(0, initial_entropy - final_entropy) / initial_entropy * 100
        
        return round(entropy_improvement, 2)
    
    def _estimate_improvement_potential(
        self, 
        current_entropy: float, 
        target_entropy: float,
        current_quality: float
    ) -> float:
        """Estimate improvement potential based on current metrics."""
        
        # Entropy-based potential
        entropy_potential = 0.0
        if current_entropy > target_entropy:
            max_entropy_improvement = (current_entropy - target_entropy) / current_entropy * 100
            entropy_potential = max_entropy_improvement * 0.7  # Conservative estimate
        
        # Quality-based potential
        quality_potential = max(0, self.config.quality_gate - current_quality)
        
        # Combined potential (weighted average)
        total_potential = (entropy_potential * 0.6) + (quality_potential * 0.4)
        
        return round(min(100.0, total_potential), 2)
    
    def _create_optimization_result(
        self,
        original_doc: Document,
        optimized_doc: Document,
        initial_entropy: float,
        final_entropy: float,
        improvement: float,
        iterations: int,
        quality_score: QualityScore,
        execution_time: float
    ) -> OptimizationResult:
        """Create optimization result object."""
        
        return OptimizationResult(
            document=optimized_doc,
            initial_entropy=initial_entropy,
            final_entropy=final_entropy,
            improvement=improvement,
            iterations=iterations,
            quality_score=quality_score,
            execution_time_ms=execution_time * 1000  # Convert to milliseconds
        )
    
    def _store_optimization_results(
        self, 
        original_doc: Document,
        optimized_doc: Document, 
        result: OptimizationResult
    ):
        """Store optimization results in M002 storage system."""
        try:
            # Create new version of the document
            self.storage_manager.create_version(
                document_id=original_doc.id,
                content=optimized_doc.content,
                metadata={
                    'entropy': result.final_entropy,
                    'quality_score': result.quality_score.overall,
                    'improvement': result.improvement,
                    'iterations': result.iterations,
                    'optimization_mode': self.mode.value,
                    'execution_time_ms': result.execution_time_ms
                }
            )
            
            # Store MIAIR-specific metadata
            self.storage_manager.store_metadata(
                document_id=original_doc.id,
                key='miair_optimization',
                value={
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'mode': self.mode.value,
                    'initial_entropy': result.initial_entropy,
                    'final_entropy': result.final_entropy,
                    'improvement_percentage': result.improvement,
                    'iterations_used': result.iterations,
                    'quality_breakdown': result.quality_score.model_dump() if hasattr(result.quality_score, 'model_dump') else str(result.quality_score),
                    'target_achieved': result.final_entropy <= self.config.target_entropy
                }
            )
            
            self.logger.debug(f"Optimization results stored for document {original_doc.id}")
            
        except Exception as e:
            self.logger.warning(f"Failed to store optimization results: {e}")
    
    def _audit_optimization(self, document_id: str, result: OptimizationResult):
        """Log optimization audit entry."""
        if hasattr(self, 'audit_logger') and self.audit_logger['enabled']:
            entry = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'document_id': document_id,
                'operation': 'optimization',
                'mode': self.mode.value,
                'initial_entropy': result.initial_entropy,
                'final_entropy': result.final_entropy,
                'improvement': result.improvement,
                'iterations': result.iterations,
                'execution_time_ms': result.execution_time_ms,
                'quality_score': result.quality_score.overall
            }
            
            self.audit_logger['log_entries'].append(entry)
            
            # Limit audit log size
            if len(self.audit_logger['log_entries']) > self.audit_logger['max_entries']:
                self.audit_logger['log_entries'] = self.audit_logger['log_entries'][-self.audit_logger['max_entries']:]
            
            self.logger.debug(f"Audit entry created for optimization {document_id}")
    
    def analyze_batch(self, documents: List[Document]) -> List[AnalysisResult]:
        """
        Analyze a batch of documents with parallel processing.
        
        Args:
            documents: List of documents to analyze
            
        Returns:
            List of AnalysisResult objects
        """
        if self.mode in [OperationMode.PERFORMANCE, OperationMode.ENTERPRISE]:
            if hasattr(self, 'performance_engine'):
                return self.performance_engine.analyze_batch(documents)
        
        # Fallback to sequential processing
        return [self.analyze(doc) for doc in documents]
    
    async def analyze_batch_async(self, documents: List[Document]) -> List[AnalysisResult]:
        """
        Analyze a batch of documents asynchronously.
        
        Args:
            documents: List of documents to analyze
            
        Returns:
            List of AnalysisResult objects
        """
        if self.mode in [OperationMode.PERFORMANCE, OperationMode.ENTERPRISE]:
            if hasattr(self, 'performance_engine'):
                return await self.performance_engine.analyze_batch_async(documents)
        
        # Fallback to sync processing
        return self.analyze_batch(documents)
    
    def _update_stats(self, result: OptimizationResult):
        """Update engine statistics."""
        self.stats['optimizations_completed'] += 1
        self.stats['total_documents_processed'] += 1
        self.stats['total_optimization_time'] += result.execution_time_ms / 1000  # Convert to seconds
        self.stats['total_improvement'] += result.improvement
        
        if self.quality_metrics.validate_quality_gate(result.quality_score, self.config.quality_gate):
            self.stats['quality_gate_passes'] += 1
    
    def _log_initialization_details(self):
        """Log detailed initialization information."""
        self.logger.debug(f"Configuration: entropy_threshold={self.config.entropy_threshold}, "
                         f"target_entropy={self.config.target_entropy}, "
                         f"quality_gate={self.config.quality_gate}, "
                         f"max_iterations={self.config.max_iterations}")
        
        if self.config_manager:
            self.logger.debug("M001 Configuration Manager integration: ENABLED")
        else:
            self.logger.debug("M001 Configuration Manager integration: DISABLED")
            
        if self.storage_manager:
            self.logger.debug("M002 Storage Manager integration: ENABLED")
        else:
            self.logger.debug("M002 Storage Manager integration: DISABLED")
        
        self.logger.debug(f"Strategy: {self.strategy.__class__.__name__}")
        
        if self.mode in [OperationMode.SECURE, OperationMode.ENTERPRISE]:
            self.logger.debug("Security features: ENABLED")
            
        if self.mode in [OperationMode.PERFORMANCE, OperationMode.ENTERPRISE]:
            self.logger.debug("Performance features: ENABLED")
            
        if self.mode == OperationMode.ENTERPRISE:
            self.logger.debug("Enterprise features: ENABLED")


# Convenience functions for common use cases

def create_miair_engine(
    mode: OperationMode = OperationMode.BASIC,
    config_manager: Optional['ConfigurationManager'] = None,
    storage_manager: Optional['UnifiedStorageManager'] = None
) -> MIAIREngineUnified:
    """
    Factory function to create MIAIR engine instance.
    
    Args:
        mode: Operation mode
        config_manager: Optional M001 configuration manager
        storage_manager: Optional M002 storage manager
        
    Returns:
        Configured MIAIR engine instance
    """
    return MIAIREngineUnified(
        mode=mode,
        config_manager=config_manager,
        storage_manager=storage_manager
    )


def optimize_document(
    document: Document,
    mode: OperationMode = OperationMode.BASIC,
    target_entropy: Optional[float] = None
) -> OptimizationResult:
    """
    Convenience function to optimize a single document.
    
    Args:
        document: Document to optimize
        mode: Operation mode to use
        target_entropy: Optional target entropy override
        
    Returns:
        OptimizationResult with optimized document and metrics
    """
    engine = create_miair_engine(mode)
    return engine.optimize(document, target_entropy=target_entropy)


def analyze_document(
    document: Document,
    mode: OperationMode = OperationMode.BASIC
) -> AnalysisResult:
    """
    Convenience function to analyze a single document.
    
    Args:
        document: Document to analyze
        mode: Operation mode to use
        
    Returns:
        AnalysisResult with entropy, quality, and improvement potential
    """
    engine = create_miair_engine(mode)
    return engine.analyze(document)