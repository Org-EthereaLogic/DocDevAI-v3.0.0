"""
M009: Secure Enhancement Pipeline.

Secure wrapper for the Enhancement Pipeline with integrated security controls,
defense-in-depth architecture, and comprehensive security monitoring.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from contextlib import asynccontextmanager

# Import base pipeline
from .enhancement_pipeline import (
    EnhancementPipeline,
    DocumentContent,
    EnhancementResult,
    EnhancementConfig
)

# Import security modules
from .security_validator import SecurityValidator, ValidationResult, ThreatLevel
from .rate_limiter import MultiLevelRateLimiter, RateLimitResult, RateLimitStatus
from .secure_cache import SecureCache, CacheStatus
from .audit_logger import (
    AuditLogger, AuditEvent, EventType, EventSeverity,
    log_enhancement_operation, log_security_violation
)
from .resource_guard import ResourceGuard, ResourceExhaustionError
from .security_config import (
    SecurityConfigManager, SecurityProfile, SecurityMode,
    create_security_config_manager
)

# Import existing configuration
from .config import EnhancementSettings, OperationMode

logger = logging.getLogger(__name__)


@dataclass
class SecurityContext:
    """Security context for operations."""
    
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    operation: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.now)
    security_clearance: str = "standard"
    
    # Additional context
    content_classification: str = "internal"
    request_origin: str = "internal"
    user_permissions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "operation": self.operation,
            "timestamp": self.timestamp.isoformat(),
            "security_clearance": self.security_clearance,
            "content_classification": self.content_classification,
            "request_origin": self.request_origin,
            "user_permissions": self.user_permissions
        }


@dataclass
class SecurityOperationResult:
    """Result of secure operation."""
    
    success: bool
    result: Optional[EnhancementResult] = None
    security_events: List[str] = field(default_factory=list)
    violations: List[str] = field(default_factory=list)
    threat_level: ThreatLevel = ThreatLevel.NONE
    processing_time: float = 0.0
    security_overhead: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class SecureEnhancementPipeline:
    """
    Secure wrapper for Enhancement Pipeline.
    
    Provides comprehensive security integration with:
    - Input validation and sanitization
    - Multi-level rate limiting
    - Encrypted caching
    - Comprehensive audit logging
    - Resource protection
    - Security policy enforcement
    """
    
    def __init__(
        self,
        settings: Optional[EnhancementSettings] = None,
        security_config_manager: Optional[SecurityConfigManager] = None,
        security_level: str = "STANDARD"
    ):
        """Initialize secure enhancement pipeline."""
        self.settings = settings or EnhancementSettings()
        
        # Initialize security configuration
        self.security_manager = (
            security_config_manager or 
            create_security_config_manager(environment=security_level.lower())
        )
        
        # Get active security profile
        self.security_profile = self.security_manager.get_active_profile()
        if not self.security_profile:
            raise ValueError("No active security profile found")
        
        # Initialize base pipeline
        self._init_base_pipeline()
        
        # Initialize security components
        self._init_security_components()
        
        # Performance tracking
        self.total_operations = 0
        self.security_blocks = 0
        self.average_security_overhead = 0.0
        
        logger.info(f"Secure Enhancement Pipeline initialized with {self.security_profile.name} profile")
    
    def _init_base_pipeline(self) -> None:
        """Initialize base enhancement pipeline."""
        try:
            # Initialize with appropriate settings based on security mode
            if self.security_profile.security_mode == SecurityMode.DEVELOPMENT:
                self.base_pipeline = EnhancementPipeline(self.settings)
            else:
                # Use more conservative settings for production
                production_settings = EnhancementSettings.from_mode(OperationMode.STANDARD)
                production_settings.pipeline.use_cache = self.security_profile.cache_config.enable_encryption
                production_settings.pipeline.detailed_reporting = False  # Reduce info leakage
                self.base_pipeline = EnhancementPipeline(production_settings)
        
        except Exception as e:
            logger.error(f"Failed to initialize base pipeline: {e}")
            raise
    
    def _init_security_components(self) -> None:
        """Initialize security components based on profile."""
        profile = self.security_profile
        
        # Security validator
        if profile.validation_config.enable_prompt_injection_detection:
            self.validator = SecurityValidator(profile.validation_config)
        else:
            self.validator = None
        
        # Rate limiter
        if profile.rate_limiting_enabled:
            self.rate_limiter = MultiLevelRateLimiter(profile.rate_limit_config)
        else:
            self.rate_limiter = None
        
        # Secure cache
        if profile.cache_config.enable_encryption:
            self.secure_cache = SecureCache(profile.cache_config)
        else:
            self.secure_cache = None
        
        # Audit logger
        if profile.audit_logging_required:
            self.audit_logger = AuditLogger(profile.audit_config)
        else:
            self.audit_logger = None
        
        # Resource guard
        if profile.resource_monitoring_enabled:
            self.resource_guard = ResourceGuard(
                profile.resource_limits,
                profile.resource_limits.recovery_delay
            )
        else:
            self.resource_guard = None
    
    async def enhance_document_secure(
        self,
        document: Union[str, DocumentContent],
        config: Optional[EnhancementConfig] = None,
        security_context: Optional[SecurityContext] = None
    ) -> SecurityOperationResult:
        """
        Securely enhance a document with comprehensive security controls.
        
        Args:
            document: Document to enhance
            config: Enhancement configuration
            security_context: Security context information
            
        Returns:
            SecurityOperationResult with enhancement result and security metadata
        """
        start_time = time.time()
        security_start_time = time.time()
        security_events = []
        violations = []
        max_threat_level = ThreatLevel.NONE
        
        # Initialize security context if not provided
        if security_context is None:
            security_context = SecurityContext(
                operation="enhance_document",
                user_id="system"
            )
        
        try:
            self.total_operations += 1
            
            # Convert string to DocumentContent if needed
            if isinstance(document, str):
                document = DocumentContent(content=document)
            
            # === SECURITY LAYER 1: INPUT VALIDATION ===
            if self.validator:
                validation_result = self.validator.validate_content(
                    document.content,
                    document.doc_type,
                    metadata=document.metadata
                )
                
                if not validation_result.is_valid:
                    max_threat_level = max(max_threat_level, validation_result.threat_level)
                    violations.extend(validation_result.violations)
                    security_events.append("input_validation_failed")
                    
                    if validation_result.threat_level >= ThreatLevel.HIGH:
                        self.security_blocks += 1
                        
                        if self.audit_logger:
                            log_security_violation(
                                self.audit_logger,
                                "input_validation_failure",
                                f"High threat content detected: {validation_result.violations}",
                                security_context.user_id,
                                security_context.ip_address,
                                EventSeverity.WARNING
                            )
                        
                        return SecurityOperationResult(
                            success=False,
                            security_events=security_events,
                            violations=violations,
                            threat_level=max_threat_level,
                            processing_time=time.time() - start_time,
                            security_overhead=time.time() - security_start_time,
                            metadata={"blocked_reason": "high_threat_input"}
                        )
                    
                    # Use sanitized content if available
                    if validation_result.sanitized_content:
                        document.content = validation_result.sanitized_content
                        security_events.append("content_sanitized")
            
            # === SECURITY LAYER 2: RATE LIMITING ===
            if self.rate_limiter:
                rate_check = await self.rate_limiter.check_limits(
                    user_id=security_context.user_id,
                    ip_address=security_context.ip_address,
                    operation=security_context.operation,
                    content_size=len(document.content)
                )
                
                if not rate_check.allowed:
                    self.security_blocks += 1
                    violations.extend(rate_check.violated_limits)
                    security_events.append("rate_limit_exceeded")
                    
                    if self.audit_logger:
                        log_security_violation(
                            self.audit_logger,
                            "rate_limit_exceeded",
                            f"Rate limit violations: {rate_check.violated_limits}",
                            security_context.user_id,
                            security_context.ip_address,
                            EventSeverity.WARNING
                        )
                    
                    return SecurityOperationResult(
                        success=False,
                        security_events=security_events,
                        violations=violations,
                        threat_level=ThreatLevel.MEDIUM,
                        processing_time=time.time() - start_time,
                        security_overhead=time.time() - security_start_time,
                        metadata={"blocked_reason": "rate_limit_exceeded"}
                    )
            
            # === SECURITY LAYER 3: CACHE CHECK ===
            cache_result = None
            if self.secure_cache:
                cache_key = f"{security_context.user_id}:{document.content[:100]}"
                cache_result, cache_status = self.secure_cache.get(
                    cache_key,
                    isolation_key=security_context.user_id or "global"
                )
                
                if cache_status == CacheStatus.HIT and cache_result:
                    security_events.append("cache_hit")
                    
                    # Release rate limit resources
                    if self.rate_limiter:
                        self.rate_limiter.release_request(
                            security_context.user_id,
                            security_context.ip_address
                        )
                    
                    # Log cache hit
                    if self.audit_logger:
                        log_enhancement_operation(
                            self.audit_logger,
                            "enhance_document",
                            "cache_hit",
                            security_context.user_id,
                            time.time() - start_time,
                            len(document.content)
                        )
                    
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
            
            # === SECURITY LAYER 4: RESOURCE PROTECTION ===
            operation_id = None
            if self.resource_guard:
                resource_context = self.resource_guard.protect_operation(
                    memory_limit=self.security_profile.resource_limits.max_memory_per_operation,
                    cpu_time_limit=self.security_profile.resource_limits.max_cpu_time_per_operation,
                    timeout=self.security_profile.resource_limits.operation_timeout
                )
                operation_id = resource_context.__enter__()
            
            security_overhead = time.time() - security_start_time
            
            try:
                # === CORE ENHANCEMENT OPERATION ===
                enhancement_result = await self.base_pipeline.enhance_document(
                    document,
                    config
                )
                
                # === POST-PROCESSING SECURITY CHECKS ===
                if enhancement_result.success and self.validator:
                    # Validate enhanced content
                    output_validation = self.validator.validate_content(
                        enhancement_result.enhanced_content,
                        document.doc_type
                    )
                    
                    if not output_validation.is_valid:
                        violations.extend([f"output_{v}" for v in output_validation.violations])
                        security_events.append("output_validation_failed")
                        max_threat_level = max(max_threat_level, output_validation.threat_level)
                        
                        # Use sanitized output if available
                        if output_validation.sanitized_content:
                            enhancement_result.enhanced_content = output_validation.sanitized_content
                            security_events.append("output_sanitized")
                
                # === SECURE CACHING ===
                if self.secure_cache and enhancement_result.success:
                    cache_key = f"{security_context.user_id}:{document.content[:100]}"
                    self.secure_cache.put(
                        cache_key,
                        enhancement_result,
                        ttl=3600,  # 1 hour
                        isolation_key=security_context.user_id or "global"
                    )
                    security_events.append("cached_result")
                
                # === AUDIT LOGGING ===
                if self.audit_logger:
                    log_enhancement_operation(
                        self.audit_logger,
                        "enhance_document",
                        "success" if enhancement_result.success else "failure",
                        security_context.user_id,
                        time.time() - start_time,
                        len(document.content),
                        enhancement_result.total_cost
                    )
                
                # Update security overhead tracking
                self.average_security_overhead = (
                    (self.average_security_overhead * (self.total_operations - 1) + security_overhead) / 
                    self.total_operations
                )
                
                return SecurityOperationResult(
                    success=enhancement_result.success,
                    result=enhancement_result,
                    security_events=security_events,
                    violations=violations,
                    threat_level=max_threat_level,
                    processing_time=time.time() - start_time,
                    security_overhead=security_overhead + (time.time() - (start_time + security_overhead)),
                    metadata={
                        "base_pipeline_time": enhancement_result.processing_time,
                        "security_checks": len(security_events)
                    }
                )
            
            finally:
                # Clean up resource protection
                if self.resource_guard and operation_id:
                    resource_context.__exit__(None, None, None)
                
                # Release rate limiting resources
                if self.rate_limiter:
                    self.rate_limiter.release_request(
                        security_context.user_id,
                        security_context.ip_address
                    )
        
        except ResourceExhaustionError as e:
            self.security_blocks += 1
            violations.append("resource_exhaustion")
            security_events.append("resource_limit_exceeded")
            
            if self.audit_logger:
                log_security_violation(
                    self.audit_logger,
                    "resource_exhaustion",
                    str(e),
                    security_context.user_id,
                    security_context.ip_address,
                    EventSeverity.ERROR
                )
            
            return SecurityOperationResult(
                success=False,
                security_events=security_events,
                violations=violations,
                threat_level=ThreatLevel.HIGH,
                processing_time=time.time() - start_time,
                security_overhead=time.time() - security_start_time,
                metadata={"blocked_reason": "resource_exhaustion"}
            )
        
        except Exception as e:
            logger.error(f"Secure enhancement failed: {e}")
            violations.append("internal_error")
            security_events.append("operation_failed")
            
            if self.audit_logger:
                log_security_violation(
                    self.audit_logger,
                    "enhancement_failure",
                    str(e),
                    security_context.user_id,
                    security_context.ip_address,
                    EventSeverity.ERROR
                )
            
            return SecurityOperationResult(
                success=False,
                security_events=security_events,
                violations=violations,
                threat_level=ThreatLevel.CRITICAL,
                processing_time=time.time() - start_time,
                security_overhead=time.time() - security_start_time,
                metadata={"error": str(e)}
            )
    
    async def enhance_batch_secure(
        self,
        documents: List[Union[str, DocumentContent]],
        config: Optional[EnhancementConfig] = None,
        security_context: Optional[SecurityContext] = None
    ) -> List[SecurityOperationResult]:
        """
        Securely enhance multiple documents.
        
        Args:
            documents: List of documents to enhance
            config: Enhancement configuration
            security_context: Security context information
            
        Returns:
            List of SecurityOperationResult objects
        """
        if security_context is None:
            security_context = SecurityContext(
                operation="enhance_batch",
                user_id="system"
            )
        
        # Process documents individually for security isolation
        results = []
        
        for i, document in enumerate(documents):
            # Create per-document security context
            doc_context = SecurityContext(
                user_id=security_context.user_id,
                session_id=security_context.session_id,
                ip_address=security_context.ip_address,
                user_agent=security_context.user_agent,
                operation=f"enhance_batch_item_{i}",
                security_clearance=security_context.security_clearance,
                content_classification=security_context.content_classification,
                request_origin=security_context.request_origin,
                user_permissions=security_context.user_permissions
            )
            
            result = await self.enhance_document_secure(
                document,
                config,
                doc_context
            )
            
            results.append(result)
            
            # Stop batch processing if critical security violations
            if result.threat_level >= ThreatLevel.CRITICAL:
                logger.warning(f"Stopping batch processing due to critical security violation in document {i}")
                break
        
        # Log batch operation
        if self.audit_logger:
            successful_docs = sum(1 for r in results if r.success)
            log_enhancement_operation(
                self.audit_logger,
                "enhance_batch",
                "success" if successful_docs > 0 else "failure",
                security_context.user_id,
                sum(r.processing_time for r in results),
                sum(len(str(doc)) for doc in documents if isinstance(doc, str))
            )
        
        return results
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get comprehensive security status."""
        status = {
            "active_profile": self.security_profile.name,
            "security_mode": self.security_profile.security_mode.value,
            "total_operations": self.total_operations,
            "security_blocks": self.security_blocks,
            "block_rate": self.security_blocks / max(self.total_operations, 1),
            "average_security_overhead": self.average_security_overhead,
            "components": {}
        }
        
        # Validator status
        if self.validator:
            status["components"]["validator"] = self.validator.get_validation_stats()
        
        # Rate limiter status
        if self.rate_limiter:
            status["components"]["rate_limiter"] = self.rate_limiter.get_stats()
        
        # Cache status
        if self.secure_cache:
            status["components"]["cache"] = self.secure_cache.get_stats()
        
        # Resource guard status
        if self.resource_guard:
            status["components"]["resource_guard"] = self.resource_guard.get_status()
        
        # Audit logger status
        if self.audit_logger:
            status["components"]["audit_logger"] = self.audit_logger.get_stats()
        
        return status
    
    def get_security_health(self) -> Dict[str, Any]:
        """Get security health assessment."""
        health_issues = []
        health_score = 100
        
        # Check component health
        if self.validator:
            stats = self.validator.get_validation_stats()
            if stats["threat_ratio"] > 0.1:  # >10% threat detection
                health_issues.append("High threat detection rate")
                health_score -= 20
        
        if self.rate_limiter:
            stats = self.rate_limiter.get_stats()
            if stats["block_rate"] > 0.05:  # >5% blocking rate
                health_issues.append("High rate limiting activity")
                health_score -= 15
        
        if self.secure_cache:
            health = self.secure_cache.get_health_status()
            if health["status"] != "healthy":
                health_issues.extend(health["issues"])
                health_score -= 25
        
        if self.resource_guard:
            status = self.resource_guard.get_status()
            if status["violation_count"] > 0:
                health_issues.append("Resource violations detected")
                health_score -= 30
            if status["circuit_breaker_active"]:
                health_issues.append("Resource circuit breaker active")
                health_score -= 40
        
        # Security overhead check
        if self.average_security_overhead > 0.5:  # >500ms overhead
            health_issues.append("High security overhead")
            health_score -= 10
        
        health_status = "healthy"
        if health_score < 90:
            health_status = "warning"
        if health_score < 70:
            health_status = "degraded"
        if health_score < 50:
            health_status = "critical"
        
        return {
            "status": health_status,
            "score": max(health_score, 0),
            "issues": health_issues,
            "security_overhead_ms": self.average_security_overhead * 1000,
            "recommendation": self._get_health_recommendation(health_status, health_issues)
        }
    
    def _get_health_recommendation(self, status: str, issues: List[str]) -> str:
        """Get health improvement recommendation."""
        if status == "healthy":
            return "Security system is operating optimally"
        elif status == "warning":
            return "Monitor security metrics closely and consider tuning thresholds"
        elif status == "degraded":
            return "Review security policies and investigate recurring issues"
        else:  # critical
            return "Immediate attention required - security system may be compromised or overloaded"
    
    async def cleanup(self) -> None:
        """Clean up all security components."""
        try:
            # Clean up components
            if self.validator:
                # Validator doesn't need cleanup
                pass
            
            if self.rate_limiter:
                # Rate limiter doesn't need cleanup
                pass
            
            if self.secure_cache:
                self.secure_cache.cleanup_expired()
            
            if self.audit_logger:
                self.audit_logger.cleanup()
            
            if self.resource_guard:
                self.resource_guard.cleanup()
            
            if self.security_manager:
                self.security_manager.cleanup()
            
            # Clean up base pipeline
            await self.base_pipeline.cleanup()
            
            logger.info("Secure Enhancement Pipeline cleanup complete")
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


def create_secure_pipeline(
    security_level: str = "STANDARD",
    settings: Optional[EnhancementSettings] = None,
    config_path: Optional[Path] = None
) -> SecureEnhancementPipeline:
    """
    Factory function to create secure enhancement pipeline.
    
    Args:
        security_level: Security level (DEVELOPMENT, STANDARD, STRICT, PARANOID)
        settings: Enhancement settings
        config_path: Path to security configuration file
        
    Returns:
        Configured SecureEnhancementPipeline
    """
    # Create security configuration manager
    security_manager = create_security_config_manager(
        environment=security_level.lower(),
        config_path=config_path
    )
    
    return SecureEnhancementPipeline(
        settings=settings,
        security_config_manager=security_manager,
        security_level=security_level
    )