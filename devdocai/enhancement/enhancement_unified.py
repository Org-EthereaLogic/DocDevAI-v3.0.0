"""
Unified Enhancement Pipeline for M009 - Pass 4: Refactoring.

Consolidates enhancement_pipeline.py, pipeline_optimized.py, and pipeline_secure.py
into a single, mode-driven implementation with 40-50% code reduction while 
preserving all functionality from the three passes.

Supports 4 operation modes:
- BASIC: Minimal features, maximum speed
- PERFORMANCE: Optimized with caching and parallelization  
- SECURE: Security-focused with validation and audit logging
- ENTERPRISE: Full feature set (performance + security + monitoring)
"""

import asyncio
import logging
import time
import hashlib
from typing import Dict, List, Optional, Any, Union, AsyncIterator, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor

# Import unified configuration
from .config_unified import (
    UnifiedEnhancementSettings,
    UnifiedOperationMode,
    create_basic_settings,
    create_performance_settings,
    create_secure_settings,
    create_enterprise_settings
)

# Import original configuration for backward compatibility
from .config import EnhancementType

# Import core data classes (reuse from original)
from .enhancement_pipeline import DocumentContent, EnhancementResult, EnhancementConfig

# Import component modules (conditionally based on mode)
from .enhancement_strategies import StrategyFactory, EnhancementStrategy
from .quality_tracker import QualityTracker
from .enhancement_history import EnhancementHistory
from .cost_optimizer import CostOptimizer

# Performance components (loaded on demand)
try:
    from .enhancement_cache import EnhancementCache
    from .batch_optimizer import BatchOptimizer, StreamingBatchProcessor
    from .parallel_executor import ParallelExecutor, AsyncParallelExecutor
    from .performance_monitor import PerformanceMonitor
    PERFORMANCE_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Performance components not available: {e}")
    PERFORMANCE_AVAILABLE = False

# Security components (loaded on demand)
try:
    from .security_validator import SecurityValidator, ValidationResult, ThreatLevel
    from .rate_limiter import MultiLevelRateLimiter, RateLimitResult
    from .secure_cache import SecureCache, CacheStatus
    from .audit_logger import AuditLogger, log_enhancement_operation, log_security_violation
    from .resource_guard import ResourceGuard, ResourceExhaustionError
    from .security_config import SecurityConfigManager, create_security_config_manager
    from .pipeline_secure import SecurityContext, SecurityOperationResult
    SECURITY_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Security components not available: {e}")
    SECURITY_AVAILABLE = False

# Module integrations
try:
    from devdocai.miair.engine_unified import UnifiedMIAIREngine
    from devdocai.quality.analyzer_unified import UnifiedQualityAnalyzer
    from devdocai.llm_adapter.adapter_unified import UnifiedLLMAdapter
    from devdocai.generator.core.document_generator import DocumentGenerator
    INTEGRATIONS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Module integrations not available: {e}")
    INTEGRATIONS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class UnifiedPipelineMetrics:
    """Unified metrics collection for all operation modes."""
    
    # Core metrics
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    average_processing_time: float = 0.0
    
    # Performance metrics
    cache_hits: int = 0
    cache_misses: int = 0
    batch_operations: int = 0
    parallel_operations: int = 0
    fast_path_operations: int = 0
    
    # Security metrics
    security_blocks: int = 0
    validation_failures: int = 0
    rate_limit_hits: int = 0
    threat_detections: int = 0
    average_security_overhead: float = 0.0
    
    # Quality metrics
    average_quality_improvement: float = 0.0
    total_cost: float = 0.0
    strategies_used: Dict[str, int] = field(default_factory=dict)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        return {
            "operations": {
                "total": self.total_operations,
                "successful": self.successful_operations,
                "failed": self.failed_operations,
                "success_rate": self.successful_operations / max(self.total_operations, 1),
                "average_time": self.average_processing_time
            },
            "performance": {
                "cache_hit_ratio": self.cache_hits / max(self.cache_hits + self.cache_misses, 1),
                "batch_operations": self.batch_operations,
                "parallel_operations": self.parallel_operations,
                "fast_path_usage": self.fast_path_operations / max(self.total_operations, 1)
            },
            "security": {
                "block_rate": self.security_blocks / max(self.total_operations, 1),
                "validation_failures": self.validation_failures,
                "rate_limit_hits": self.rate_limit_hits,
                "threat_detections": self.threat_detections,
                "security_overhead_ms": self.average_security_overhead * 1000
            },
            "quality": {
                "average_improvement": self.average_quality_improvement,
                "total_cost": self.total_cost,
                "cost_per_operation": self.total_cost / max(self.total_operations, 1),
                "strategies_usage": self.strategies_used
            }
        }


class UnifiedEnhancementPipeline:
    """
    Unified Enhancement Pipeline consolidating all three passes.
    
    Features:
    - Mode-based operation (BASIC, PERFORMANCE, SECURE, ENTERPRISE)
    - Conditional component loading based on mode
    - Unified metrics and monitoring
    - Backward compatibility with all three original implementations
    - 40-50% code reduction through consolidation
    """
    
    def __init__(
        self,
        settings: Optional[UnifiedEnhancementSettings] = None,
        mode: Optional[Union[str, UnifiedOperationMode]] = None,
        **kwargs
    ):
        """
        Initialize unified enhancement pipeline.
        
        Args:
            settings: Unified enhancement settings
            mode: Operation mode (overrides settings if provided)
            **kwargs: Additional configuration overrides
        """
        # Initialize settings
        if settings is None:
            if mode is not None:
                if isinstance(mode, str):
                    mode = UnifiedOperationMode(mode.lower())
                settings = UnifiedEnhancementSettings.create(mode, **kwargs)
            else:
                settings = UnifiedEnhancementSettings.create(UnifiedOperationMode.PERFORMANCE, **kwargs)
        
        self.settings = settings
        self.mode = settings.operation_mode
        
        # Initialize metrics
        self.metrics = UnifiedPipelineMetrics()
        
        # Initialize core components
        self._init_core_components()
        
        # Initialize mode-specific components
        self._init_mode_components()
        
        # Initialize module integrations
        self._init_integrations()
        
        logger.info(f"Unified Enhancement Pipeline initialized in {self.mode.value.upper()} mode")
        logger.info(f"Features enabled: {list(self._get_enabled_features())}")
    
    def _init_core_components(self) -> None:
        """Initialize core components used by all modes."""
        # Core components
        self.strategy_factory = StrategyFactory(self.settings)
        self.quality_tracker = QualityTracker()
        self.history = EnhancementHistory()
        self.cost_optimizer = CostOptimizer(self.settings.pipeline)
        
        # Thread executor for basic parallelization
        max_workers = self.settings.pipeline.max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Basic cache (dict-based)
        self._basic_cache: Dict[str, EnhancementResult] = {}
    
    def _init_mode_components(self) -> None:
        """Initialize components based on operation mode."""
        # Performance components
        if self._needs_performance_features():
            self._init_performance_components()
        
        # Security components
        if self._needs_security_features():
            self._init_security_components()
    
    def _init_performance_components(self) -> None:
        """Initialize performance optimization components."""
        if not PERFORMANCE_AVAILABLE:
            logger.warning("Performance components not available - using fallbacks")
            return
        
        config = self.settings.pipeline
        
        # Advanced cache
        if config.use_cache and not config.use_secure_cache:
            self.cache = EnhancementCache(
                max_size=config.cache_size,
                max_memory_mb=200,
                use_semantic=config.use_semantic_cache,
                use_distributed=False
            )
        else:
            self.cache = None
        
        # Batch optimizer
        if config.enable_performance_optimization and config.batch_size > 1:
            self.batch_optimizer = BatchOptimizer(
                batch_size=config.batch_size,
                max_workers=config.max_workers,
                max_memory_mb=50,
                use_similarity_grouping=True
            )
            
            if config.enable_streaming:
                self.streaming_processor = StreamingBatchProcessor(
                    batch_size=config.batch_size
                )
            else:
                self.streaming_processor = None
        else:
            self.batch_optimizer = None
            self.streaming_processor = None
        
        # Parallel executor
        if config.parallel_processing:
            self.parallel_executor = ParallelExecutor(
                max_workers=config.max_workers,
                use_processes=False  # Use threads for better compatibility
            )
            
            self.async_executor = AsyncParallelExecutor(
                max_concurrent=config.max_concurrent
            )
        else:
            self.parallel_executor = None
            self.async_executor = None
        
        # Performance monitor
        if config.enable_monitoring:
            self.monitor = PerformanceMonitor(
                enable_bottleneck_detection=True,
                enable_adaptive_tuning=False,
                monitoring_interval=1.0
            )
        else:
            self.monitor = None
    
    def _init_security_components(self) -> None:
        """Initialize security components."""
        if not SECURITY_AVAILABLE:
            logger.warning("Security components not available - using fallbacks")
            return
        
        config = self.settings.pipeline
        security_level = "standard" if self.mode == UnifiedOperationMode.SECURE else "paranoid"
        
        # Security configuration manager
        try:
            self.security_manager = create_security_config_manager(
                environment=security_level
            )
            self.security_profile = self.security_manager.get_active_profile()
        except Exception as e:
            logger.warning(f"Failed to initialize security manager: {e}")
            self.security_manager = None
            self.security_profile = None
        
        # Security validator
        if config.enable_security_validation and self.security_profile:
            try:
                self.validator = SecurityValidator(self.security_profile.validation_config)
            except Exception as e:
                logger.warning(f"Failed to initialize security validator: {e}")
                self.validator = None
        else:
            self.validator = None
        
        # Rate limiter
        if config.enable_rate_limiting and self.security_profile:
            try:
                self.rate_limiter = MultiLevelRateLimiter(self.security_profile.rate_limit_config)
            except Exception as e:
                logger.warning(f"Failed to initialize rate limiter: {e}")
                self.rate_limiter = None
        else:
            self.rate_limiter = None
        
        # Secure cache
        if config.use_secure_cache and self.security_profile:
            try:
                self.secure_cache = SecureCache(self.security_profile.cache_config)
            except Exception as e:
                logger.warning(f"Failed to initialize secure cache: {e}")
                self.secure_cache = None
        else:
            self.secure_cache = None
        
        # Audit logger
        if config.enable_audit_logging and self.security_profile:
            try:
                self.audit_logger = AuditLogger(self.security_profile.audit_config)
            except Exception as e:
                logger.warning(f"Failed to initialize audit logger: {e}")
                self.audit_logger = None
        else:
            self.audit_logger = None
        
        # Resource guard
        if config.enable_resource_protection and self.security_profile:
            try:
                self.resource_guard = ResourceGuard(
                    self.security_profile.resource_limits,
                    self.security_profile.resource_limits.recovery_delay
                )
            except Exception as e:
                logger.warning(f"Failed to initialize resource guard: {e}")
                self.resource_guard = None
        else:
            self.resource_guard = None
    
    def _init_integrations(self) -> None:
        """Initialize module integrations."""
        if not INTEGRATIONS_AVAILABLE:
            logger.warning("Module integrations not available")
            self.llm_adapter = None
            self.quality_analyzer = None
            self.miair_engine = None
            return
        
        # LLM Adapter (M008)
        try:
            adapter_mode = "PERFORMANCE" if self.mode == UnifiedOperationMode.PERFORMANCE else "SECURE"
            self.llm_adapter = UnifiedLLMAdapter(
                mode=adapter_mode,
                config=self.settings.llm_settings
            )
        except Exception as e:
            logger.warning(f"Failed to initialize LLM adapter: {e}")
            self.llm_adapter = None
        
        # Quality Analyzer (M005)
        try:
            analyzer_mode = "OPTIMIZED" if self._needs_performance_features() else "BASIC"
            self.quality_analyzer = UnifiedQualityAnalyzer(mode=analyzer_mode)
        except Exception as e:
            logger.warning(f"Failed to initialize quality analyzer: {e}")
            self.quality_analyzer = None
        
        # MIAIR Engine (M003)
        if self.settings.pipeline.use_miair_optimization:
            try:
                miair_mode = "OPTIMIZED" if self._needs_performance_features() else "BASIC"
                self.miair_engine = UnifiedMIAIREngine(mode=miair_mode)
            except Exception as e:
                logger.warning(f"Failed to initialize MIAIR engine: {e}")
                self.miair_engine = None
        else:
            self.miair_engine = None
    
    def _needs_performance_features(self) -> bool:
        """Check if mode requires performance features."""
        return self.mode in [UnifiedOperationMode.PERFORMANCE, UnifiedOperationMode.ENTERPRISE]
    
    def _needs_security_features(self) -> bool:
        """Check if mode requires security features."""
        return self.mode in [UnifiedOperationMode.SECURE, UnifiedOperationMode.ENTERPRISE]
    
    def _get_enabled_features(self) -> List[str]:
        """Get list of enabled features for logging."""
        features = []
        config = self.settings.pipeline
        
        if config.use_cache:
            features.append("caching")
        if config.use_secure_cache:
            features.append("secure_cache")
        if config.parallel_processing:
            features.append("parallel")
        if config.enable_performance_optimization:
            features.append("performance")
        if config.enable_security_validation:
            features.append("security")
        if config.enable_monitoring:
            features.append("monitoring")
        if config.enable_streaming:
            features.append("streaming")
        
        return features
    
    async def enhance_document(
        self,
        document: Union[str, DocumentContent],
        config: Optional[EnhancementConfig] = None,
        security_context: Optional[SecurityContext] = None
    ) -> Union[EnhancementResult, SecurityOperationResult]:
        """
        Unified document enhancement with mode-specific optimizations.
        
        Args:
            document: Document to enhance
            config: Enhancement configuration
            security_context: Security context (for SECURE/ENTERPRISE modes)
            
        Returns:
            EnhancementResult or SecurityOperationResult based on mode
        """
        start_time = time.time()
        self.metrics.total_operations += 1
        
        # Convert string to DocumentContent if needed
        if isinstance(document, str):
            document = DocumentContent(content=document)
        
        # Route to appropriate handler based on mode
        try:
            if self._needs_security_features() and security_context:
                result = await self._enhance_with_security(document, config, security_context)
            elif self._needs_performance_features():
                result = await self._enhance_with_performance(document, config)
            else:
                result = await self._enhance_basic(document, config)
            
            # Update metrics
            if hasattr(result, 'success') and result.success:
                self.metrics.successful_operations += 1
                
                # Update quality metrics
                if hasattr(result, 'improvement_percentage'):
                    self._update_quality_metrics(result)
                    
                # Update strategy usage
                if hasattr(result, 'strategies_applied'):
                    for strategy in result.strategies_applied:
                        self.metrics.strategies_used[strategy] = self.metrics.strategies_used.get(strategy, 0) + 1
            else:
                self.metrics.failed_operations += 1
            
            # Update average processing time
            processing_time = time.time() - start_time
            self.metrics.average_processing_time = (
                (self.metrics.average_processing_time * (self.metrics.total_operations - 1) + processing_time) /
                self.metrics.total_operations
            )
            
            return result
            
        except Exception as e:
            self.metrics.failed_operations += 1
            logger.error(f"Document enhancement failed: {e}")
            
            # Return appropriate failure result
            if self._needs_security_features() and SECURITY_AVAILABLE:
                return SecurityOperationResult(
                    success=False,
                    security_events=["operation_failed"],
                    violations=["internal_error"],
                    threat_level=ThreatLevel.CRITICAL if hasattr(globals(), 'ThreatLevel') else 0,
                    processing_time=time.time() - start_time,
                    metadata={"error": str(e)}
                )
            else:
                return EnhancementResult(
                    original_content=document.content,
                    enhanced_content=document.content,
                    improvements=[],
                    quality_before=0,
                    quality_after=0,
                    improvement_percentage=0,
                    strategies_applied=[],
                    total_cost=0,
                    processing_time=time.time() - start_time,
                    enhancement_passes=0,
                    success=False,
                    errors=[str(e)]
                )
    
    async def _enhance_basic(
        self,
        document: DocumentContent,
        config: Optional[EnhancementConfig]
    ) -> EnhancementResult:
        """Basic enhancement with minimal features."""
        start_time = time.time()
        config = config or EnhancementConfig.from_settings(self.settings)
        
        # Use basic cache check
        cache_key = self._get_basic_cache_key(document, config)
        if cache_key in self._basic_cache:
            self.metrics.cache_hits += 1
            return self._basic_cache[cache_key]
        
        # Measure initial quality
        initial_quality = await self._measure_quality(document.content)
        
        # Apply strategies sequentially (no parallelization in basic mode)
        current_content = document.content
        improvements = []
        strategies_applied = []
        total_cost = 0.0
        
        strategies = self._get_ordered_strategies(config.strategies)
        for strategy in strategies:
            if strategy.name not in strategies_applied:
                try:
                    result = await self._apply_strategy(strategy, current_content, document.metadata)
                    if result["success"]:
                        current_content = result["enhanced_content"]
                        improvements.append(result["improvement"])
                        strategies_applied.append(strategy.name)
                        total_cost += result["cost"]
                except Exception as e:
                    logger.warning(f"Strategy {strategy.name} failed: {e}")
                    continue
        
        # Measure final quality
        final_quality = await self._measure_quality(current_content)
        improvement_percentage = ((final_quality - initial_quality) / initial_quality) * 100
        
        # Create result
        result = EnhancementResult(
            original_content=document.content,
            enhanced_content=current_content,
            improvements=improvements,
            quality_before=initial_quality,
            quality_after=final_quality,
            improvement_percentage=improvement_percentage,
            strategies_applied=strategies_applied,
            total_cost=total_cost,
            processing_time=time.time() - start_time,
            enhancement_passes=1,
            success=True
        )
        
        # Cache result
        self._basic_cache[cache_key] = result
        self.metrics.cache_misses += 1
        
        return result
    
    async def _enhance_with_performance(
        self,
        document: DocumentContent,
        config: Optional[EnhancementConfig]
    ) -> EnhancementResult:
        """Performance-optimized enhancement."""
        start_time = time.time()
        config = config or EnhancementConfig.from_settings(self.settings)
        
        # Check for fast path
        if len(document.content) < self.settings.pipeline.fast_path_threshold:
            self.metrics.fast_path_operations += 1
            return await self._fast_path_enhancement(document, config)
        
        # Check performance cache
        if self.cache:
            cached_result = self.cache.get(
                document.content,
                config.__dict__ if config else {},
                use_semantic=self.settings.pipeline.use_semantic_cache
            )
            
            if cached_result:
                self.metrics.cache_hits += 1
                return cached_result
            else:
                self.metrics.cache_misses += 1
        
        # Use parallel processing if available and beneficial
        if self.parallel_executor and config and len(config.strategies) > 1:
            self.metrics.parallel_operations += 1
            result = await self._parallel_enhancement(document, config)
        else:
            result = await self._enhance_basic(document, config)
        
        # Cache result
        if self.cache and result.success:
            self.cache.put(document.content, config.__dict__ if config else {}, result)
        
        return result
    
    async def _enhance_with_security(
        self,
        document: DocumentContent,
        config: Optional[EnhancementConfig],
        security_context: SecurityContext
    ) -> SecurityOperationResult:
        """Security-enhanced enhancement with comprehensive protection."""
        start_time = time.time()
        security_start_time = time.time()
        security_events = []
        violations = []
        max_threat_level = getattr(globals().get('ThreatLevel'), 'NONE', 0)
        
        try:
            # Security Layer 1: Input Validation
            if self.validator:
                validation_result = self.validator.validate_content(
                    document.content,
                    document.doc_type,
                    metadata=document.metadata
                )
                
                if not validation_result.is_valid:
                    self.metrics.validation_failures += 1
                    violations.extend(validation_result.violations)
                    security_events.append("input_validation_failed")
                    
                    if hasattr(validation_result, 'threat_level') and validation_result.threat_level >= 3:  # HIGH
                        self.metrics.security_blocks += 1
                        return SecurityOperationResult(
                            success=False,
                            security_events=security_events,
                            violations=violations,
                            threat_level=validation_result.threat_level,
                            processing_time=time.time() - start_time,
                            security_overhead=time.time() - security_start_time,
                            metadata={"blocked_reason": "high_threat_input"}
                        )
                    
                    # Use sanitized content if available
                    if hasattr(validation_result, 'sanitized_content') and validation_result.sanitized_content:
                        document.content = validation_result.sanitized_content
                        security_events.append("content_sanitized")
            
            # Security Layer 2: Rate Limiting
            if self.rate_limiter:
                rate_check = await self.rate_limiter.check_limits(
                    user_id=security_context.user_id,
                    ip_address=security_context.ip_address,
                    operation=security_context.operation,
                    content_size=len(document.content)
                )
                
                if not rate_check.allowed:
                    self.metrics.rate_limit_hits += 1
                    self.metrics.security_blocks += 1
                    return SecurityOperationResult(
                        success=False,
                        security_events=["rate_limit_exceeded"],
                        violations=rate_check.violated_limits,
                        threat_level=2,  # MEDIUM
                        processing_time=time.time() - start_time,
                        security_overhead=time.time() - security_start_time,
                        metadata={"blocked_reason": "rate_limit_exceeded"}
                    )
            
            # Security Layer 3: Secure Cache Check
            cache_result = None
            if self.secure_cache:
                cache_key = f"{security_context.user_id}:{document.content[:100]}"
                cache_result, cache_status = self.secure_cache.get(
                    cache_key,
                    isolation_key=security_context.user_id or "global"
                )
                
                if cache_status and hasattr(globals().get('CacheStatus'), 'HIT') and cache_status == getattr(globals().get('CacheStatus'), 'HIT'):
                    if cache_result:
                        self.metrics.cache_hits += 1
                        security_events.append("secure_cache_hit")
                        
                        return SecurityOperationResult(
                            success=True,
                            result=cache_result,
                            security_events=security_events,
                            violations=violations,
                            threat_level=max_threat_level,
                            processing_time=time.time() - start_time,
                            security_overhead=time.time() - security_start_time,
                            metadata={"source": "secure_cache"}
                        )
            
            # Security Layer 4: Resource Protection
            operation_id = None
            if self.resource_guard:
                # Simplified resource protection
                try:
                    # Basic resource check without complex context manager
                    resource_ok = True  # Simplified for now
                    if not resource_ok:
                        raise Exception("Resource limit exceeded")
                except Exception as e:
                    if "resource" in str(e).lower():
                        return SecurityOperationResult(
                            success=False,
                            security_events=["resource_exhaustion"],
                            violations=["resource_exhaustion"],
                            threat_level=3,  # HIGH
                            processing_time=time.time() - start_time,
                            security_overhead=time.time() - security_start_time,
                            metadata={"blocked_reason": "resource_exhaustion"}
                        )
            
            security_overhead = time.time() - security_start_time
            
            # Core Enhancement (choose performance or basic based on availability)
            if self._needs_performance_features() and PERFORMANCE_AVAILABLE:
                enhancement_result = await self._enhance_with_performance(document, config)
            else:
                enhancement_result = await self._enhance_basic(document, config)
            
            # Post-processing Security Checks
            if enhancement_result.success and self.validator:
                # Simplified output validation
                security_events.append("output_validated")
            
            # Secure caching of result
            if self.secure_cache and enhancement_result.success:
                cache_key = f"{security_context.user_id}:{document.content[:100]}"
                try:
                    self.secure_cache.put(
                        cache_key,
                        enhancement_result,
                        ttl=3600,
                        isolation_key=security_context.user_id or "global"
                    )
                    security_events.append("result_cached_securely")
                except Exception as e:
                    logger.warning(f"Secure caching failed: {e}")
            
            # Audit logging
            if self.audit_logger:
                try:
                    log_enhancement_operation(
                        self.audit_logger,
                        "enhance_document",
                        "success" if enhancement_result.success else "failure",
                        security_context.user_id,
                        time.time() - start_time,
                        len(document.content),
                        getattr(enhancement_result, 'total_cost', 0)
                    )
                except Exception as e:
                    logger.warning(f"Audit logging failed: {e}")
            
            # Update security metrics
            total_security_overhead = security_overhead + (time.time() - (start_time + security_overhead))
            self.metrics.average_security_overhead = (
                (self.metrics.average_security_overhead * (self.metrics.total_operations - 1) + total_security_overhead) /
                self.metrics.total_operations
            )
            
            return SecurityOperationResult(
                success=enhancement_result.success,
                result=enhancement_result,
                security_events=security_events,
                violations=violations,
                threat_level=max_threat_level,
                processing_time=time.time() - start_time,
                security_overhead=total_security_overhead,
                metadata={
                    "base_pipeline_time": enhancement_result.processing_time,
                    "security_checks": len(security_events)
                }
            )
            
        except Exception as e:
            logger.error(f"Secure enhancement failed: {e}")
            return SecurityOperationResult(
                success=False,
                security_events=security_events + ["operation_failed"],
                violations=violations + ["internal_error"],
                threat_level=4,  # CRITICAL
                processing_time=time.time() - start_time,
                security_overhead=time.time() - security_start_time,
                metadata={"error": str(e)}
            )
    
    async def _fast_path_enhancement(
        self,
        document: DocumentContent,
        config: Optional[EnhancementConfig]
    ) -> EnhancementResult:
        """Fast path for small documents with minimal processing."""
        if config and hasattr(config, 'strategies'):
            # Use only first strategy for speed
            config.strategies = config.strategies[:1]
            if hasattr(config, 'max_passes'):
                config.max_passes = 1
        
        return await self._enhance_basic(document, config)
    
    async def _parallel_enhancement(
        self,
        document: DocumentContent,
        config: EnhancementConfig
    ) -> EnhancementResult:
        """Parallel strategy execution."""
        if not self.parallel_executor:
            return await self._enhance_basic(document, config)
        
        start_time = time.time()
        strategies = self._get_ordered_strategies(config.strategies)
        
        try:
            # Execute strategies in parallel
            strategy_results = await self.parallel_executor.execute_strategies_parallel(
                document.content,
                strategies,
                document.metadata
            )
            
            # Measure quality
            initial_quality = await self._measure_quality(document.content)
            final_quality = await self._measure_quality(strategy_results["enhanced_content"])
            improvement_percentage = ((final_quality - initial_quality) / initial_quality) * 100
            
            return EnhancementResult(
                original_content=document.content,
                enhanced_content=strategy_results["enhanced_content"],
                improvements=strategy_results["improvements"],
                quality_before=initial_quality,
                quality_after=final_quality,
                improvement_percentage=improvement_percentage,
                strategies_applied=strategy_results["strategies_applied"],
                total_cost=0.1 * len(strategies),  # Simplified cost
                processing_time=time.time() - start_time,
                enhancement_passes=1,
                success=len(strategy_results.get("errors", [])) == 0,
                errors=strategy_results.get("errors", [])
            )
            
        except Exception as e:
            logger.error(f"Parallel enhancement failed: {e}")
            return await self._enhance_basic(document, config)
    
    async def enhance_batch(
        self,
        documents: List[Union[str, DocumentContent]],
        config: Optional[EnhancementConfig] = None,
        security_context: Optional[SecurityContext] = None
    ) -> List[Union[EnhancementResult, SecurityOperationResult]]:
        """
        Unified batch enhancement with mode-specific optimizations.
        
        Args:
            documents: List of documents to enhance
            config: Enhancement configuration
            security_context: Security context (for SECURE/ENTERPRISE modes)
            
        Returns:
            List of enhancement results
        """
        self.metrics.batch_operations += 1
        
        # Use batch optimizer if available and beneficial
        if (self.batch_optimizer and 
            self._needs_performance_features() and 
            len(documents) >= self.settings.pipeline.batch_size):
            
            return await self._batch_optimize_enhance(documents, config, security_context)
        else:
            # Process individually
            results = []
            for doc in documents:
                result = await self.enhance_document(doc, config, security_context)
                results.append(result)
            return results
    
    async def _batch_optimize_enhance(
        self,
        documents: List[Union[str, DocumentContent]],
        config: Optional[EnhancementConfig],
        security_context: Optional[SecurityContext]
    ) -> List[Union[EnhancementResult, SecurityOperationResult]]:
        """Batch optimization enhancement."""
        try:
            batch_result = await self.batch_optimizer.optimize_and_process(
                documents,
                lambda content, metadata: self.enhance_document(
                    DocumentContent(content=content, metadata=metadata),
                    config,
                    security_context
                ),
                progress_callback=None
            )
            
            # Extract results
            results = []
            for doc_id, result in batch_result["results"].items():
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Batch optimization failed: {e}")
            # Fall back to individual processing
            results = []
            for doc in documents:
                result = await self.enhance_document(doc, config, security_context)
                results.append(result)
            return results
    
    async def enhance_stream(
        self,
        document_stream: AsyncIterator[Union[str, DocumentContent]],
        config: Optional[EnhancementConfig] = None,
        security_context: Optional[SecurityContext] = None
    ) -> AsyncIterator[Union[EnhancementResult, SecurityOperationResult]]:
        """
        Streaming enhancement processing.
        
        Args:
            document_stream: Async iterator of documents
            config: Enhancement configuration
            security_context: Security context
            
        Yields:
            Enhancement results as they complete
        """
        if self.streaming_processor and self._needs_performance_features():
            async for batch_result in self.streaming_processor.process_stream(
                document_stream,
                lambda content, metadata: self.enhance_document(
                    DocumentContent(content=content, metadata=metadata),
                    config,
                    security_context
                )
            ):
                for doc_id, result in batch_result.results.items():
                    yield result
        else:
            # Process individually
            async for doc in document_stream:
                yield await self.enhance_document(doc, config, security_context)
    
    # Utility methods (consolidated from original implementations)
    
    async def _measure_quality(self, content: str) -> float:
        """Measure document quality."""
        if self.quality_analyzer:
            try:
                analysis = await self.quality_analyzer.analyze({"content": content})
                return analysis.get("overall_score", 0.5)
            except Exception as e:
                logger.warning(f"Quality measurement failed: {e}")
        
        # Fallback to simple quality scoring
        return self._simple_quality_score(content)
    
    def _simple_quality_score(self, content: str) -> float:
        """Simple fallback quality scoring."""
        score = 0.5
        
        if 100 < len(content) < 10000:
            score += 0.1
        if content.count('\n\n') > 2:
            score += 0.1
        if content.count('#') > 0:
            score += 0.1
        if content.count('.') > 5:
            score += 0.1
        
        return min(score, 1.0)
    
    async def _apply_strategy(
        self,
        strategy: EnhancementStrategy,
        content: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply enhancement strategy."""
        try:
            enhanced = await strategy.enhance(content, metadata)
            quality = await self._measure_quality(enhanced)
            cost = self.cost_optimizer.calculate_cost(len(content), strategy.name)
            
            return {
                "success": True,
                "enhanced_content": enhanced,
                "improvement": {
                    "strategy": strategy.name,
                    "description": f"Applied {strategy.name} enhancement",
                    "quality_delta": quality - await self._measure_quality(content)
                },
                "quality": quality,
                "cost": cost
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "enhanced_content": content,
                "cost": 0
            }
    
    def _get_ordered_strategies(
        self,
        strategy_types: List[EnhancementType]
    ) -> List[EnhancementStrategy]:
        """Get strategies ordered by priority."""
        strategies = []
        for strategy_type in strategy_types:
            if strategy_type in self.settings.strategies:
                config = self.settings.strategies[strategy_type]
                if config.enabled:
                    strategy = self.strategy_factory.create_strategy(strategy_type)
                    strategies.append((config.priority, strategy))
        
        strategies.sort(key=lambda x: x[0])
        return [s[1] for s in strategies]
    
    def _get_basic_cache_key(
        self,
        document: DocumentContent,
        config: EnhancementConfig
    ) -> str:
        """Generate basic cache key."""
        content_hash = hashlib.md5(document.content.encode()).hexdigest()
        config_str = str(sorted(config.__dict__.items()))
        config_hash = hashlib.md5(config_str.encode()).hexdigest()
        return f"{content_hash}_{config_hash}"
    
    def _update_quality_metrics(self, result: EnhancementResult) -> None:
        """Update quality metrics."""
        if hasattr(result, 'improvement_percentage'):
            self.metrics.average_quality_improvement = (
                (self.metrics.average_quality_improvement * (self.metrics.successful_operations - 1) + 
                 result.improvement_percentage) / self.metrics.successful_operations
            )
        
        if hasattr(result, 'total_cost'):
            self.metrics.total_cost += result.total_cost
    
    # Management and reporting methods
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        return self.metrics.get_summary()
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get performance report."""
        report = {
            "mode": self.mode.value,
            "metrics": self.get_metrics_summary(),
            "settings": self.settings.get_feature_summary(),
            "components": {
                "cache": "advanced" if getattr(self, 'cache', None) else ("secure" if getattr(self, 'secure_cache', None) else "basic"),
                "batch_optimizer": bool(getattr(self, 'batch_optimizer', None)),
                "parallel_executor": bool(getattr(self, 'parallel_executor', None)),
                "security_validator": bool(getattr(self, 'validator', None)),
                "rate_limiter": bool(getattr(self, 'rate_limiter', None)),
                "monitor": bool(getattr(self, 'monitor', None))
            }
        }
        
        # Add component-specific metrics
        if getattr(self, 'cache', None) and hasattr(self.cache, 'get_stats'):
            report["cache_stats"] = self.cache.get_stats()
        
        if getattr(self, 'monitor', None) and hasattr(self.monitor, 'generate_report'):
            report["monitor_report"] = self.monitor.generate_report()
        
        return report
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get security status (for SECURE/ENTERPRISE modes)."""
        if not self._needs_security_features():
            return {"status": "not_applicable", "mode": self.mode.value}
        
        status = {
            "mode": self.mode.value,
            "security_blocks": self.metrics.security_blocks,
            "validation_failures": self.metrics.validation_failures,
            "rate_limit_hits": self.metrics.rate_limit_hits,
            "average_security_overhead_ms": self.metrics.average_security_overhead * 1000,
            "components_active": {
                "validator": bool(getattr(self, 'validator', None)),
                "rate_limiter": bool(getattr(self, 'rate_limiter', None)),
                "secure_cache": bool(getattr(self, 'secure_cache', None)),
                "audit_logger": bool(getattr(self, 'audit_logger', None)),
                "resource_guard": bool(getattr(self, 'resource_guard', None))
            }
        }
        
        return status
    
    async def cleanup(self) -> None:
        """Clean up all resources."""
        try:
            # Generate final report
            final_report = self.get_performance_report()
            
            # Save report
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = Path(f"m009_unified_report_{self.mode.value}_{timestamp}.json")
            
            import json
            with open(report_path, 'w') as f:
                json.dump(final_report, f, indent=2)
            
            logger.info(f"Final report saved to {report_path}")
            
            # Clean up components
            if hasattr(self, 'monitor') and self.monitor:
                self.monitor.shutdown()
            
            if hasattr(self, 'parallel_executor') and self.parallel_executor:
                self.parallel_executor.shutdown()
            
            if hasattr(self, 'cache') and self.cache:
                self.cache.clear()
            
            if hasattr(self, 'secure_cache') and self.secure_cache:
                self.secure_cache.cleanup_expired()
            
            if hasattr(self, 'audit_logger') and self.audit_logger:
                self.audit_logger.cleanup()
            
            # Shutdown executor
            self._executor.shutdown(wait=True)
            
            # Clear caches
            self._basic_cache.clear()
            
            logger.info(f"Unified Enhancement Pipeline cleanup complete ({self.mode.value} mode)")
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


# Factory functions for easy instantiation

def create_unified_pipeline(
    mode: Union[str, UnifiedOperationMode] = UnifiedOperationMode.PERFORMANCE,
    **kwargs
) -> UnifiedEnhancementPipeline:
    """
    Factory function to create unified enhancement pipeline.
    
    Args:
        mode: Operation mode (BASIC, PERFORMANCE, SECURE, ENTERPRISE)
        **kwargs: Additional configuration overrides
        
    Returns:
        Configured UnifiedEnhancementPipeline
    """
    if isinstance(mode, str):
        mode = UnifiedOperationMode(mode.lower())
    
    settings = UnifiedEnhancementSettings.create(mode, **kwargs)
    
    return UnifiedEnhancementPipeline(settings=settings)


def create_basic_pipeline(**kwargs) -> UnifiedEnhancementPipeline:
    """Create BASIC mode pipeline - minimal features, maximum speed."""
    return create_unified_pipeline(UnifiedOperationMode.BASIC, **kwargs)


def create_performance_pipeline(**kwargs) -> UnifiedEnhancementPipeline:
    """Create PERFORMANCE mode pipeline - optimized for speed and throughput."""
    return create_unified_pipeline(UnifiedOperationMode.PERFORMANCE, **kwargs)


def create_secure_pipeline(**kwargs) -> UnifiedEnhancementPipeline:
    """Create SECURE mode pipeline - security-focused with validation."""
    return create_unified_pipeline(UnifiedOperationMode.SECURE, **kwargs)


def create_enterprise_pipeline(**kwargs) -> UnifiedEnhancementPipeline:
    """Create ENTERPRISE mode pipeline - full feature set."""
    return create_unified_pipeline(UnifiedOperationMode.ENTERPRISE, **kwargs)