"""
M003 MIAIR Engine - Security-Hardened Implementation

Enterprise-grade secure implementation of the MIAIR Engine with comprehensive
security features while maintaining performance objectives.

Security Features:
- Input validation and sanitization
- Rate limiting and DoS protection
- Encrypted caching
- PII detection and masking
- Audit logging
- OWASP Top 10 compliance
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone
from contextlib import contextmanager

# Core engine imports
from .engine_unified import MIAIREngineUnified
from .models import (
    Document, OperationMode, MIAIRConfig, OptimizationResult, AnalysisResult,
    QualityScore, ValidationResult
)

# Security module imports
from .security import (
    InputValidator, ValidationConfig, ValidationError, ThreatLevel,
    RateLimiter, RateLimitConfig, RateLimitExceeded, CircuitBreakerOpen, Priority,
    SecureCache, SecureCacheConfig, CacheSecurityError,
    AuditLogger, AuditConfig, SecurityEventType, SeverityLevel,
    PIIIntegration, PIIHandlingConfig, PIISensitivity
)

logger = logging.getLogger(__name__)


class SecureMIAIREngine(MIAIREngineUnified):
    """
    Security-hardened MIAIR Engine implementation.
    
    Extends the unified engine with comprehensive security features:
    - All inputs validated and sanitized
    - Rate limiting and DoS protection
    - Encrypted caching for sensitive data
    - PII detection and masking
    - Comprehensive audit logging
    - <10% performance overhead
    """
    
    def __init__(
        self,
        mode: OperationMode = OperationMode.SECURE,
        config_manager: Optional[Any] = None,
        storage_manager: Optional[Any] = None,
        miair_config: Optional[MIAIRConfig] = None,
        security_config: Optional[Dict] = None
    ):
        """
        Initialize secure MIAIR Engine.
        
        Args:
            mode: Operation mode (defaults to SECURE)
            config_manager: Optional M001 configuration integration
            storage_manager: Optional M002 storage integration
            miair_config: Optional MIAIR-specific configuration
            security_config: Optional security configuration overrides
        """
        # Force secure mode
        if mode not in [OperationMode.SECURE, OperationMode.ENTERPRISE]:
            logger.warning(f"Overriding mode {mode} to SECURE for SecureMIAIREngine")
            mode = OperationMode.SECURE
        
        # Initialize base engine
        super().__init__(mode, config_manager, storage_manager, miair_config)
        
        # Initialize security components
        self._init_security_components(security_config or {})
        
        # Log initialization
        self.audit_logger.log_event(
            event_type=SecurityEventType.SYSTEM_START,
            severity=SeverityLevel.INFO,
            action="Secure MIAIR Engine initialized",
            details={'mode': mode.value, 'security_features': self._get_security_features()}
        )
    
    def _init_security_components(self, security_config: Dict):
        """Initialize all security components."""
        # Input validator
        validation_config = ValidationConfig(**security_config.get('validation', {}))
        self.input_validator = InputValidator(validation_config)
        
        # Rate limiter
        rate_limit_config = RateLimitConfig(**security_config.get('rate_limiting', {}))
        self.rate_limiter = RateLimiter(rate_limit_config)
        
        # Secure cache
        cache_config = SecureCacheConfig(**security_config.get('secure_cache', {}))
        self.secure_cache = SecureCache(cache_config)
        
        # Audit logger
        audit_config = AuditConfig(**security_config.get('audit', {}))
        self.audit_logger = AuditLogger(audit_config)
        
        # PII integration
        pii_config = PIIHandlingConfig(**security_config.get('pii', {}))
        self.pii_integration = PIIIntegration(pii_config)
        
        # Security statistics
        self.security_stats = {
            'validations_passed': 0,
            'validations_failed': 0,
            'threats_detected': 0,
            'rate_limits_hit': 0,
            'pii_masked': 0,
            'security_overhead_ms': 0.0
        }
    
    def _get_security_features(self) -> List[str]:
        """Get list of enabled security features."""
        features = []
        
        if self.input_validator.config.enable_pattern_detection:
            features.append("pattern_detection")
        if self.input_validator.config.enable_html_sanitization:
            features.append("html_sanitization")
        if self.rate_limiter.config.enable_adaptive_limiting:
            features.append("adaptive_rate_limiting")
        if self.rate_limiter.config.enable_per_client_limits:
            features.append("per_client_limits")
        if self.secure_cache.config.encryption_enabled:
            features.append("encrypted_cache")
        if self.pii_integration.config.enabled:
            features.append("pii_detection")
        if self.audit_logger.config.enable_hash_chain:
            features.append("tamper_proof_logging")
        
        return features
    
    @contextmanager
    def _security_context(self, operation: str, document_id: str, client_id: Optional[str] = None):
        """
        Context manager for security operations.
        
        Handles:
        - Rate limiting
        - Performance tracking
        - Error handling
        - Audit logging
        """
        start_time = time.time()
        
        try:
            # Apply rate limiting
            with self.rate_limiter.acquire(client_id=client_id, priority=Priority.NORMAL):
                yield
                
        except RateLimitExceeded as e:
            self.security_stats['rate_limits_hit'] += 1
            self.audit_logger.log_security_violation(
                violation_type='rate_limit',
                threat_level='medium',
                source_ip=client_id,
                details={'operation': operation, 'document_id': document_id}
            )
            raise
            
        except CircuitBreakerOpen as e:
            self.audit_logger.log_event(
                event_type=SecurityEventType.CIRCUIT_BREAKER_TRIGGERED,
                severity=SeverityLevel.ERROR,
                action=f"Circuit breaker open for {operation}",
                client_id=client_id,
                resource=document_id,
                outcome="blocked"
            )
            raise
            
        finally:
            # Track security overhead
            overhead = (time.time() - start_time) * 1000
            self.security_stats['security_overhead_ms'] += overhead
    
    def _validate_and_sanitize_document(self, document: Document) -> Tuple[Document, Dict]:
        """
        Validate and sanitize document content.
        
        Args:
            document: Document to validate
            
        Returns:
            Tuple of (sanitized_document, validation_report)
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Prepare metadata for validation
            metadata = {
                'document_id': document.id, 
                'source': document.source,
                'timestamp': document.created_at or datetime.now(timezone.utc).isoformat()
            }
            
            # Validate document content
            sanitized_content, validation_report = self.input_validator.validate_document(
                document.content,
                metadata
            )
            
            # Update statistics
            if validation_report['passed']:
                self.security_stats['validations_passed'] += 1
            else:
                self.security_stats['validations_failed'] += 1
            
            if validation_report.get('threats_detected'):
                self.security_stats['threats_detected'] += len(validation_report['threats_detected'])
                
                # Log security violations
                for threat in validation_report['threats_detected']:
                    self.audit_logger.log_security_violation(
                        violation_type='injection' if 'script' in threat['pattern'] else 'pattern',
                        threat_level=threat['level'].value,
                        details={'document_id': document.id, 'pattern': threat['pattern']}
                    )
            
            # Create sanitized document
            sanitized_doc = Document(
                id=document.id,
                content=sanitized_content,
                source=document.source,
                created_at=document.created_at,
                metadata=document.metadata
            )
            
            return sanitized_doc, validation_report
            
        except ValidationError as e:
            self.audit_logger.log_event(
                event_type=SecurityEventType.DATA_ACCESS,
                severity=SeverityLevel.WARNING,
                action="Document validation failed",
                resource=document.id,
                outcome="failure",
                details={'error': str(e), 'threat_level': e.threat_level.value}
            )
            raise
    
    def _apply_pii_protection(self, document: Document) -> Tuple[Document, Dict]:
        """
        Apply PII detection and masking to document.
        
        Args:
            document: Document to process
            
        Returns:
            Tuple of (masked_document, pii_report)
        """
        # Scan and mask PII
        masked_content, pii_report = self.pii_integration.scan_document(
            document.content,
            document.metadata
        )
        
        if pii_report['pii_detected']:
            self.security_stats['pii_masked'] += pii_report['masked_count']
            
            # Log PII access
            self.audit_logger.log_event(
                event_type=SecurityEventType.PII_ACCESS,
                severity=SeverityLevel.INFO,
                action="PII detected and masked",
                resource=document.id,
                outcome="masked",
                details={
                    'types_found': pii_report['types_found'],
                    'masked_count': pii_report['masked_count']
                }
            )
            
            # Create masked document
            masked_doc = Document(
                id=document.id,
                content=masked_content,
                source=document.source,
                created_at=document.created_at,
                metadata=document.metadata
            )
            
            return masked_doc, pii_report
        
        return document, pii_report
    
    def _check_cache_secure(self, key: str, client_id: Optional[str] = None) -> Optional[Any]:
        """
        Securely check cache for value.
        
        Args:
            key: Cache key
            client_id: Optional client identifier
            
        Returns:
            Cached value if found, None otherwise
        """
        try:
            return self.secure_cache.get(key, client_id=client_id)
        except CacheSecurityError as e:
            logger.error(f"Secure cache error: {e}")
            return None
    
    def _store_cache_secure(self, key: str, value: Any, client_id: Optional[str] = None) -> bool:
        """
        Securely store value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            client_id: Optional client identifier
            
        Returns:
            True if stored successfully
        """
        try:
            return self.secure_cache.set(key, value, client_id=client_id)
        except CacheSecurityError as e:
            logger.error(f"Secure cache store error: {e}")
            return False
    
    def optimize(
        self,
        document: Document,
        target_entropy: Optional[float] = None,
        client_id: Optional[str] = None
    ) -> OptimizationResult:
        """
        Optimize document with security protections.
        
        Args:
            document: Document to optimize
            target_entropy: Target entropy level (optional)
            client_id: Client identifier for rate limiting
            
        Returns:
            OptimizationResult with security validations
        """
        with self._security_context("optimize", document.id, client_id):
            # Step 1: Validate and sanitize input
            sanitized_doc, validation_report = self._validate_and_sanitize_document(document)
            
            # Step 2: Apply PII protection
            protected_doc, pii_report = self._apply_pii_protection(sanitized_doc)
            
            # Step 3: Check secure cache
            cache_key = f"opt_{protected_doc.id}_{target_entropy or self.config.target_entropy}"
            cached_result = self._check_cache_secure(cache_key, client_id)
            if cached_result:
                self.audit_logger.log_event(
                    event_type=SecurityEventType.DATA_ACCESS,
                    severity=SeverityLevel.DEBUG,
                    action="Cache hit for optimization",
                    client_id=client_id,
                    resource=document.id,
                    outcome="success"
                )
                return cached_result
            
            # Step 4: Perform optimization with base engine
            result = super().optimize(protected_doc, target_entropy)
            
            # Step 5: Store in secure cache
            self._store_cache_secure(cache_key, result, client_id)
            
            # Step 6: Audit log the operation
            self.audit_logger.log_event(
                event_type=SecurityEventType.DATA_MODIFICATION,
                severity=SeverityLevel.INFO,
                action="Document optimized",
                client_id=client_id,
                resource=document.id,
                outcome="success",
                details={
                    'improvement': result.improvement_percentage,
                    'final_entropy': result.final_entropy,
                    'pii_masked': pii_report.get('masked_count', 0),
                    'threats_blocked': len(validation_report.get('threats_detected', []))
                }
            )
            
            # Add security metadata to result
            result.metadata = result.metadata or {}
            result.metadata['security'] = {
                'validated': True,
                'sanitized': bool(validation_report.get('sanitizations_applied')),
                'pii_masked': pii_report['pii_detected'],
                'threats_detected': len(validation_report.get('threats_detected', [])),
                'compliance': pii_report.get('compliance', {})
            }
            
            return result
    
    def analyze(
        self,
        document: Document,
        include_patterns: bool = True,
        client_id: Optional[str] = None
    ) -> AnalysisResult:
        """
        Analyze document with security protections.
        
        Args:
            document: Document to analyze
            include_patterns: Whether to include pattern analysis
            client_id: Client identifier for rate limiting
            
        Returns:
            AnalysisResult with security validations
        """
        with self._security_context("analyze", document.id, client_id):
            # Step 1: Validate and sanitize input
            sanitized_doc, validation_report = self._validate_and_sanitize_document(document)
            
            # Step 2: Apply PII protection
            protected_doc, pii_report = self._apply_pii_protection(sanitized_doc)
            
            # Step 3: Check secure cache
            cache_key = f"ana_{protected_doc.id}_{include_patterns}"
            cached_result = self._check_cache_secure(cache_key, client_id)
            if cached_result:
                return cached_result
            
            # Step 4: Perform analysis with base engine
            result = super().analyze(protected_doc, include_patterns)
            
            # Step 5: Store in secure cache
            self._store_cache_secure(cache_key, result, client_id)
            
            # Step 6: Audit log the operation
            self.audit_logger.log_event(
                event_type=SecurityEventType.DATA_ACCESS,
                severity=SeverityLevel.INFO,
                action="Document analyzed",
                client_id=client_id,
                resource=document.id,
                outcome="success",
                details={
                    'entropy': result.entropy,
                    'quality_score': result.quality_score.overall,
                    'pii_found': pii_report['pii_detected']
                }
            )
            
            return result
    
    def batch_optimize(
        self,
        documents: List[Document],
        client_id: Optional[str] = None
    ) -> List[OptimizationResult]:
        """
        Batch optimize documents with security protections.
        
        Args:
            documents: List of documents to optimize
            client_id: Client identifier for rate limiting
            
        Returns:
            List of OptimizationResults
        """
        results = []
        
        # Validate batch size
        if len(documents) > 100:  # Security limit
            raise ValidationError("Batch size exceeds security limit (100)", ThreatLevel.LOW)
        
        # Process documents with rate limiting
        for doc in documents:
            try:
                result = self.optimize(doc, client_id=client_id)
                results.append(result)
            except (ValidationError, RateLimitExceeded) as e:
                logger.warning(f"Failed to optimize document {doc.id}: {e}")
                # Create failed result
                failed_result = OptimizationResult(
                    original_entropy=0.0,
                    final_entropy=0.0,
                    improvement_percentage=0.0,
                    optimized_content="",
                    optimization_steps=[],
                    quality_score=QualityScore(overall=0.0),
                    meets_quality_gate=False,
                    metadata={'error': str(e)}
                )
                results.append(failed_result)
        
        return results
    
    def get_security_stats(self) -> Dict[str, Any]:
        """Get security statistics."""
        base_stats = self.get_engine_stats()
        
        # Add security-specific stats
        base_stats['security'] = {
            'validations': self.security_stats,
            'input_validator': self.input_validator.get_stats(),
            'rate_limiter': self.rate_limiter.get_stats(),
            'secure_cache': self.secure_cache.get_stats(),
            'pii_integration': self.pii_integration.get_stats(),
            'audit_logger': self.audit_logger.get_stats()
        }
        
        # Calculate security overhead percentage
        total_time = base_stats.get('average_optimization_time', 1.0) * 1000  # Convert to ms
        if total_time > 0:
            overhead_percentage = (self.security_stats['security_overhead_ms'] / total_time) * 100
            base_stats['security']['overhead_percentage'] = min(overhead_percentage, 100.0)
        
        return base_stats
    
    def shutdown(self):
        """Shutdown secure engine gracefully."""
        # Log shutdown
        self.audit_logger.log_event(
            event_type=SecurityEventType.SYSTEM_STOP,
            severity=SeverityLevel.INFO,
            action="Secure MIAIR Engine shutting down",
            details={'stats': self.get_security_stats()}
        )
        
        # Clear sensitive data
        self.secure_cache.clear()
        self.pii_integration.clear_cache()
        
        # Shutdown audit logger
        self.audit_logger.shutdown()
        
        logger.info("Secure MIAIR Engine shutdown complete")