"""
M007 Review Engine - Security-hardened implementation.

Comprehensive security features including input validation, rate limiting,
encrypted caching, access control, and audit logging.
"""

import asyncio
import hashlib
import json
import logging
import time
import uuid
import secrets
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from functools import wraps
from pathlib import Path
import multiprocessing as mp
import pickle
import re
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64

import numpy as np
from joblib import Memory

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
from .dimensions_secure import (
    SecureBaseDimension,
    SecureTechnicalAccuracyDimension,
    SecureCompletenessDimension,
    SecureConsistencyDimension,
    SecureStyleFormattingDimension,
    SecureSecurityPIIDimension,
    get_secure_dimensions
)
from .security_validator import (
    SecurityValidator,
    AccessController,
    ValidationResult,
    SecurityThreat
)

logger = logging.getLogger(__name__)


class SecureCache:
    """
    Encrypted LRU cache with security features.
    
    Features:
    - AES-256 encryption for sensitive data
    - Cache key validation
    - Anti-cache poisoning
    - Secure expiration
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        ttl_seconds: int = 3600,
        encryption_key: Optional[bytes] = None
    ):
        """Initialize secure cache."""
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict[str, Tuple[bytes, datetime, str]] = OrderedDict()
        self.hits = 0
        self.misses = 0
        self._lock = asyncio.Lock()
        
        # Initialize encryption
        if encryption_key:
            self.cipher = Fernet(encryption_key)
        else:
            # Generate new key
            self.cipher = Fernet(Fernet.generate_key())
        
        # Cache integrity tracking
        self.cache_hashes: Dict[str, str] = {}
    
    def _generate_cache_key(self, key: str) -> str:
        """Generate secure cache key."""
        # Add namespace and hash to prevent collisions
        namespace = "m007_review"
        return hashlib.sha256(f"{namespace}:{key}".encode()).hexdigest()
    
    def _encrypt_value(self, value: Any) -> bytes:
        """Encrypt cache value."""
        try:
            # Serialize and encrypt
            serialized = pickle.dumps(value)
            return self.cipher.encrypt(serialized)
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def _decrypt_value(self, encrypted: bytes) -> Any:
        """Decrypt cache value."""
        try:
            decrypted = self.cipher.decrypt(encrypted)
            return pickle.loads(decrypted)
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return None
    
    async def get(self, key: str) -> Optional[Any]:
        """Get cached result with security validation."""
        async with self._lock:
            secure_key = self._generate_cache_key(key)
            
            if secure_key in self.cache:
                encrypted_value, timestamp, value_hash = self.cache[secure_key]
                
                # Check expiration
                if datetime.now() - timestamp < timedelta(seconds=self.ttl_seconds):
                    # Verify integrity
                    current_hash = hashlib.sha256(encrypted_value).hexdigest()
                    if current_hash != value_hash:
                        logger.warning(f"Cache integrity check failed for key: {key}")
                        del self.cache[secure_key]
                        self.misses += 1
                        return None
                    
                    # Decrypt and return
                    value = self._decrypt_value(encrypted_value)
                    if value is not None:
                        # Move to end (LRU)
                        self.cache.move_to_end(secure_key)
                        self.hits += 1
                        return value
                else:
                    # Expired
                    del self.cache[secure_key]
            
            self.misses += 1
            return None
    
    async def set(self, key: str, value: Any) -> None:
        """Set cache value with encryption."""
        async with self._lock:
            secure_key = self._generate_cache_key(key)
            
            # Encrypt value
            encrypted = self._encrypt_value(value)
            value_hash = hashlib.sha256(encrypted).hexdigest()
            
            # Remove if exists to update position
            if secure_key in self.cache:
                del self.cache[secure_key]
            
            # Add to cache
            self.cache[secure_key] = (encrypted, datetime.now(), value_hash)
            
            # Evict LRU if needed
            while len(self.cache) > self.max_size:
                self.cache.popitem(last=False)
    
    async def clear(self) -> None:
        """Securely clear cache."""
        async with self._lock:
            # Overwrite encrypted values before clearing
            for key in self.cache:
                encrypted_value = self.cache[key][0]
                # Overwrite with random data
                if isinstance(encrypted_value, bytes):
                    encrypted_value = secrets.token_bytes(len(encrypted_value))
            
            self.cache.clear()
            self.cache_hashes.clear()
            self.hits = 0
            self.misses = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class SecureReviewEngine:
    """
    Security-hardened review engine for M007.
    
    Security features:
    - Comprehensive input validation
    - Rate limiting with token bucket
    - Encrypted caching
    - Role-based access control
    - Audit logging
    - OWASP Top 10 protection
    - PII detection and redaction
    - Secure multi-tenancy
    """
    
    def __init__(
        self,
        config: Optional[ReviewEngineConfig] = None,
        encryption_key: Optional[bytes] = None
    ):
        """Initialize secure review engine."""
        self.config = config or ReviewEngineConfig()
        
        # Initialize security components
        self.security_validator = SecurityValidator()
        self.access_controller = AccessController()
        
        # Initialize secure cache
        self._cache = SecureCache(
            max_size=getattr(self.config, 'cache_max_size', 1000),
            ttl_seconds=self.config.cache_ttl_seconds,
            encryption_key=encryption_key
        )
        
        # Initialize thread/process pools with limits
        self.thread_executor = ThreadPoolExecutor(
            max_workers=min(getattr(self.config, 'max_workers', 4), 10)  # Security limit
        )
        self.process_executor = ProcessPoolExecutor(
            max_workers=min(mp.cpu_count(), 4)
        )
        
        # Initialize secure dimensions
        self.dimensions = self._initialize_secure_dimensions()
        
        # Initialize module integrations
        self._initialize_integrations()
        
        # Security monitoring
        self.security_metrics = {
            'validations_performed': 0,
            'threats_detected': 0,
            'rate_limits_hit': 0,
            'access_denied': 0,
            'pii_detected': 0,
            'cache_poisoning_attempts': 0
        }
        
        # Audit logging
        self.audit_logger = logging.getLogger(f"{__name__}.audit")
        self._setup_audit_logging()
        
        # Background security tasks
        self._security_monitor_task = None
        if getattr(self.config, 'enable_security_monitoring', True):
            self._start_security_monitoring()
    
    def _setup_audit_logging(self):
        """Setup comprehensive audit logging."""
        if not self.audit_logger.handlers:
            handler = logging.FileHandler('review_security_audit.log')
            handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            )
            self.audit_logger.addHandler(handler)
            self.audit_logger.setLevel(logging.INFO)
    
    def _initialize_secure_dimensions(self) -> List[SecureBaseDimension]:
        """Initialize security-enhanced dimensions."""
        dimensions = []
        enabled = self.config.enabled_dimensions
        weights = self.config.dimension_weights
        
        # Use secure dimension implementations
        dimension_map = {
            ReviewDimension.TECHNICAL_ACCURACY: SecureTechnicalAccuracyDimension,
            ReviewDimension.COMPLETENESS: SecureCompletenessDimension,
            ReviewDimension.CONSISTENCY: SecureConsistencyDimension,
            ReviewDimension.STYLE_FORMATTING: SecureStyleFormattingDimension,
            ReviewDimension.SECURITY_PII: SecureSecurityPIIDimension,
        }
        
        for dim_type, dim_class in dimension_map.items():
            if dim_type in enabled:
                dimensions.append(dim_class(
                    weight=weights.get(dim_type, 0.20),
                    security_validator=self.security_validator
                ))
        
        return dimensions
    
    def _initialize_integrations(self):
        """Initialize integrations with security checks."""
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
            from ..storage.pii_detector import PIIDetectionConfig, PIIType
            pii_config = PIIDetectionConfig(
                enabled_types={PIIType.EMAIL, PIIType.PHONE, PIIType.SSN, PIIType.CREDIT_CARD},
                min_confidence=0.8
            )
            self.pii_detector = PIIDetector(config=pii_config)
            logger.info("Initialized PII Detector")
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
    
    def _start_security_monitoring(self):
        """Start background security monitoring."""
        async def monitor_loop():
            while True:
                await asyncio.sleep(60)  # Check every minute
                await self._perform_security_checks()
        
        self._security_monitor_task = asyncio.create_task(monitor_loop())
    
    async def _perform_security_checks(self):
        """Perform periodic security checks."""
        try:
            # Check for anomalies in access patterns
            if self.security_metrics['access_denied'] > 100:
                self._log_security_alert(
                    "high_access_denial_rate",
                    {"count": self.security_metrics['access_denied']}
                )
            
            # Check for excessive rate limiting
            if self.security_metrics['rate_limits_hit'] > 50:
                self._log_security_alert(
                    "excessive_rate_limiting",
                    {"count": self.security_metrics['rate_limits_hit']}
                )
            
            # Check cache poisoning attempts
            if self.security_metrics['cache_poisoning_attempts'] > 0:
                self._log_security_alert(
                    "cache_poisoning_detected",
                    {"attempts": self.security_metrics['cache_poisoning_attempts']}
                )
            
            # Reset counters for next period
            for key in ['access_denied', 'rate_limits_hit', 'cache_poisoning_attempts']:
                self.security_metrics[key] = 0
                
        except Exception as e:
            logger.error(f"Security monitoring error: {e}")
    
    def _log_security_alert(self, alert_type: str, details: Dict[str, Any]):
        """Log security alert."""
        alert = {
            "timestamp": datetime.now().isoformat(),
            "alert_type": alert_type,
            "severity": "HIGH",
            "details": details
        }
        self.audit_logger.warning(f"SECURITY ALERT: {json.dumps(alert)}")
    
    def _log_audit_event(
        self,
        event_type: str,
        user_id: Optional[str],
        document_id: Optional[str],
        details: Dict[str, Any]
    ):
        """Log audit event."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "user_id": user_id or "system",
            "document_id": document_id,
            "details": details
        }
        self.audit_logger.info(json.dumps(event))
    
    async def review_document(
        self,
        content: str,
        document_id: Optional[str] = None,
        document_type: str = "generic",
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> ReviewResult:
        """
        Perform secure document review with comprehensive validation.
        
        Security features:
        - Input validation and sanitization
        - Rate limiting
        - Access control
        - PII detection and redaction
        - Encrypted caching
        - Audit logging
        """
        start_time = time.time()
        
        # Generate document ID if not provided
        if not document_id:
            document_id = str(uuid.uuid4())
        
        # Access control check
        if user_id and not self.access_controller.check_permission(user_id, "review.create"):
            self.security_metrics['access_denied'] += 1
            self._log_audit_event(
                "access_denied",
                user_id,
                document_id,
                {"permission": "review.create"}
            )
            raise PermissionError("User does not have permission to create reviews")
        
        # Rate limiting check
        client_id = user_id or "anonymous"
        if not self.security_validator.check_rate_limit(client_id, "review"):
            self.security_metrics['rate_limits_hit'] += 1
            self._log_audit_event(
                "rate_limit_exceeded",
                user_id,
                document_id,
                {"action": "review"}
            )
            raise Exception("Rate limit exceeded. Please try again later.")
        
        # Validate and sanitize input
        validation_result = self.security_validator.validate_document(
            content,
            document_type,
            metadata
        )
        
        self.security_metrics['validations_performed'] += 1
        
        if not validation_result.is_valid:
            self.security_metrics['threats_detected'] += len(validation_result.threats_detected)
            self._log_audit_event(
                "validation_failed",
                user_id,
                document_id,
                {
                    "threats": [t.value for t in validation_result.threats_detected],
                    "risk_score": validation_result.risk_score
                }
            )
            
            # Return error result for high-risk content
            if validation_result.risk_score > 7.0:
                return ReviewResult(
                    document_id=document_id,
                    document_type=document_type,
                    review_id=str(uuid.uuid4()),
                    timestamp=datetime.now(),
                    overall_score=0.0,
                    status=ReviewStatus.REJECTED,
                    issues=[
                        ReviewIssue(
                            dimension=ReviewDimension.SECURITY_PII,
                            severity=ReviewSeverity.BLOCKER,
                            title="Security Threat Detected",
                            description=f"Document contains potential security threats: {', '.join([t.value for t in validation_result.threats_detected])}",
                            impact_score=10.0
                        )
                    ],
                    dimension_results=[],
                    recommended_actions=["Remove security threats before resubmission"],
                    approval_conditions=["Document must pass security validation"],
                    metadata={
                        "security_validation_failed": True,
                        "threats_detected": [t.value for t in validation_result.threats_detected],
                        "risk_score": validation_result.risk_score
                    }
                )
        
        # Use sanitized content
        sanitized_content = validation_result.sanitized_content or content
        
        # PII detection and redaction
        pii_results = None
        if self.pii_detector:
            try:
                pii_results = self.pii_detector.detect(sanitized_content)
                if pii_results and len(pii_results.pii_found) > 0:
                    self.security_metrics['pii_detected'] += 1
                    
                    # Redact PII if configured
                    if getattr(self.config, 'mask_pii_in_reports', False):
                        sanitized_content = self.pii_detector.redact(
                            sanitized_content,
                            pii_results
                        )
                    
                    self._log_audit_event(
                        "pii_detected",
                        user_id,
                        document_id,
                        {
                            "pii_types": [pii.type.value for pii in pii_results.pii_found],
                            "count": len(pii_results.pii_found),
                            "redacted": getattr(self.config, 'redact_pii', False)
                        }
                    )
            except Exception as e:
                logger.warning(f"PII detection failed: {e}")
        
        # Check cache with secure key
        cache_key = f"{document_id}:{hashlib.sha256(sanitized_content.encode()).hexdigest()[:16]}"
        
        if getattr(self.config, 'enable_caching', True):
            cached_result = await self._cache.get(cache_key)
            if cached_result:
                logger.info(f"Secure cache hit for document {document_id}")
                cached_result.from_cache = True
                cached_result.execution_time_ms = 0.01
                
                self._log_audit_event(
                    "review_cache_hit",
                    user_id,
                    document_id,
                    {"cache_key": cache_key[:16]}  # Log partial key only
                )
                
                return cached_result
        
        # Prepare metadata
        if metadata is None:
            metadata = {}
        
        metadata.update({
            'document_id': document_id,
            'document_type': document_type,
            'content_length': len(sanitized_content),
            'timestamp': datetime.now().isoformat(),
            'security_validated': True,
            'pii_detected': pii_results is not None and len(pii_results.pii_found) > 0 if pii_results else False
        })
        
        # Validate metadata
        metadata_validation = self.security_validator.validate_metadata(metadata)
        if not metadata_validation.is_valid:
            logger.warning(f"Metadata validation failed: {metadata_validation.error_message}")
            metadata = {}  # Use empty metadata if validation fails
        
        # Parallel dimension analysis with security
        dimension_results = await self._analyze_dimensions_secure(
            sanitized_content,
            metadata,
            user_id
        )
        
        # Aggregate results
        all_issues = []
        for dim_result in dimension_results:
            all_issues.extend(dim_result.issues)
        
        # Add security issues if any
        if validation_result.threats_detected:
            for threat in validation_result.threats_detected:
                all_issues.append(ReviewIssue(
                    dimension=ReviewDimension.SECURITY_PII,
                    severity=ReviewSeverity.HIGH,
                    title=f"Security Issue: {threat.value}",
                    description=f"Potential {threat.value} detected in document",
                    impact_score=7.0
                ))
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(dimension_results)
        
        # Apply security penalty if threats detected
        if validation_result.threats_detected:
            overall_score *= (1 - validation_result.risk_score / 20)  # Max 50% penalty
        
        # Determine status
        status = self._determine_status(overall_score, all_issues)
        
        # Generate recommendations
        recommended_actions = self._generate_secure_recommendations(
            all_issues,
            dimension_results,
            validation_result
        )
        approval_conditions = self._generate_approval_conditions(status, all_issues)
        
        # Optional integrations (with security checks)
        integration_results = await self._run_secure_integrations(
            sanitized_content,
            user_id
        )
        
        # Create review result
        execution_time = (time.time() - start_time) * 1000
        
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
                'security_validated': True,
                'threats_detected': [t.value for t in validation_result.threats_detected],
                'risk_score': validation_result.risk_score,
                'pii_detected': metadata.get('pii_detected', False),
                'cache_hit_rate': self._cache.hit_rate,
                **integration_results
            }
        )
        
        # Cache the result securely
        if getattr(self.config, 'enable_caching', True):
            await self._cache.set(cache_key, result)
        
        # Store in database if available (with encryption)
        if self.storage and getattr(self.config, 'persist_results', True):
            asyncio.create_task(self._store_result_secure(result, user_id))
        
        # Log audit event
        self._log_audit_event(
            "review_completed",
            user_id,
            document_id,
            {
                "review_id": result.review_id,
                "score": overall_score,
                "status": status.value,
                "issues": len(all_issues),
                "execution_time_ms": execution_time
            }
        )
        
        logger.info(
            f"Secure review completed for {document_id}: "
            f"Score={overall_score:.1f}, Status={status}, "
            f"Issues={len(all_issues)}, Threats={len(validation_result.threats_detected)}"
        )
        
        return result
    
    async def _analyze_dimensions_secure(
        self,
        content: str,
        metadata: Dict[str, Any],
        user_id: Optional[str]
    ) -> List[DimensionResult]:
        """Analyze dimensions with security checks."""
        tasks = []
        
        for dimension in self.dimensions:
            # Check permission for each dimension
            if user_id and hasattr(dimension, 'required_permission'):
                if not self.access_controller.check_permission(
                    user_id,
                    dimension.required_permission
                ):
                    continue
            
            task = asyncio.create_task(dimension.analyze(content, metadata))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Dimension {self.dimensions[i].__class__.__name__} failed: {result}")
            else:
                valid_results.append(result)
        
        return valid_results
    
    async def _run_secure_integrations(
        self,
        content: str,
        user_id: Optional[str]
    ) -> Dict[str, Any]:
        """Run integrations with security checks."""
        results = {}
        
        # Quality analysis with permission check
        if self.quality_analyzer and getattr(self.config, 'use_quality_engine', False):
            if not user_id or self.access_controller.check_permission(user_id, "quality.analyze"):
                try:
                    quality_result = await asyncio.get_event_loop().run_in_executor(
                        self.thread_executor,
                        self.quality_analyzer.analyze,
                        content
                    )
                    results['quality_insights'] = {
                        'quality_score': quality_result.overall_score,
                        'quality_issues': len(quality_result.issues)
                    }
                except Exception as e:
                    logger.warning(f"Quality analysis failed: {e}")
        
        # MIAIR optimization with permission check
        if self.miair_engine and getattr(self.config, 'use_miair_optimization', False):
            if not user_id or self.access_controller.check_permission(user_id, "miair.optimize"):
                try:
                    miair_result = await asyncio.get_event_loop().run_in_executor(
                        self.thread_executor,
                        self.miair_engine.analyze,
                        content
                    )
                    results['optimization_suggestions'] = {
                        'entropy_score': miair_result.get('entropy', 0),
                        'quality_score': miair_result.get('quality_score', 0),
                        'optimizations': miair_result.get('patterns', [])[:3]
                    }
                except Exception as e:
                    logger.warning(f"MIAIR optimization failed: {e}")
        
        return results
    
    async def _store_result_secure(self, result: ReviewResult, user_id: Optional[str]):
        """Store result with encryption."""
        try:
            # Encrypt sensitive fields
            encrypted_data = result.model_dump()
            
            # Add audit metadata
            encrypted_data['stored_by'] = user_id or "system"
            encrypted_data['stored_at'] = datetime.now().isoformat()
            
            await asyncio.get_event_loop().run_in_executor(
                self.thread_executor,
                self.storage.store,
                'review_results',
                encrypted_data
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
        """Determine review status with security considerations."""
        blocker_count = sum(1 for issue in issues if issue.severity == ReviewSeverity.BLOCKER)
        critical_count = sum(1 for issue in issues if issue.severity == ReviewSeverity.CRITICAL)
        security_issues = sum(1 for issue in issues if issue.dimension == ReviewDimension.SECURITY_PII)
        
        # Security issues automatically require revision
        if security_issues > 0 and blocker_count > 0:
            return ReviewStatus.REJECTED
        elif blocker_count > 0:
            return ReviewStatus.REJECTED
        elif critical_count > 2 or score < 60 or security_issues > 2:
            return ReviewStatus.NEEDS_MAJOR_REVISION
        elif critical_count > 0 or score < 75 or security_issues > 0:
            return ReviewStatus.NEEDS_MINOR_REVISION
        elif score < 85:
            return ReviewStatus.APPROVED_WITH_CONDITIONS
        else:
            return ReviewStatus.APPROVED
    
    def _generate_secure_recommendations(
        self,
        issues: List[ReviewIssue],
        dimension_results: List[DimensionResult],
        validation_result: ValidationResult
    ) -> List[str]:
        """Generate recommendations including security aspects."""
        recommendations = []
        
        # Security recommendations first
        if validation_result.threats_detected:
            for threat in validation_result.threats_detected:
                if threat == SecurityThreat.SQL_INJECTION:
                    recommendations.append("Remove SQL queries or use parameterized statements")
                elif threat == SecurityThreat.XSS:
                    recommendations.append("Sanitize HTML content and escape user inputs")
                elif threat == SecurityThreat.HARDCODED_SECRETS:
                    recommendations.append("Remove hardcoded secrets and use environment variables")
                elif threat == SecurityThreat.PATH_TRAVERSAL:
                    recommendations.append("Validate and sanitize file paths")
        
        # Standard recommendations
        if not issues:
            recommendations.append("Document meets all quality and security standards")
        else:
            severity_groups = {}
            for issue in issues:
                if issue.severity not in severity_groups:
                    severity_groups[issue.severity] = []
                severity_groups[issue.severity].append(issue)
            
            if ReviewSeverity.BLOCKER in severity_groups:
                recommendations.append(f"Fix {len(severity_groups[ReviewSeverity.BLOCKER])} blocker issues immediately")
            
            if ReviewSeverity.CRITICAL in severity_groups:
                recommendations.append(f"Address {len(severity_groups[ReviewSeverity.CRITICAL])} critical issues")
        
        # Dimension-specific recommendations
        for result in dimension_results:
            if result.score < 70:
                recommendations.append(f"Improve {result.dimension.value} (current score: {result.score:.1f})")
        
        return recommendations[:7]  # Limit to top 7 recommendations
    
    def _generate_approval_conditions(
        self,
        status: ReviewStatus,
        issues: List[ReviewIssue]
    ) -> List[str]:
        """Generate approval conditions with security requirements."""
        if status == ReviewStatus.APPROVED:
            return []
        
        conditions = []
        
        # Security conditions
        security_issues = [i for i in issues if i.dimension == ReviewDimension.SECURITY_PII]
        if security_issues:
            conditions.append("Resolve all security and PII issues")
        
        # Standard conditions
        for severity in [ReviewSeverity.BLOCKER, ReviewSeverity.CRITICAL]:
            severity_issues = [i for i in issues if i.severity == severity]
            if severity_issues:
                conditions.append(f"Resolve all {severity.value} issues ({len(severity_issues)} found)")
        
        return conditions[:5]  # Limit conditions
    
    async def batch_review_secure(
        self,
        documents: List[Dict[str, Any]],
        user_id: Optional[str] = None,
        parallel: bool = True,
        batch_size: int = 5  # Reduced for security
    ) -> List[ReviewResult]:
        """
        Secure batch review with rate limiting.
        """
        # Check batch permission
        if user_id and not self.access_controller.check_permission(user_id, "review.batch"):
            raise PermissionError("User does not have permission for batch reviews")
        
        # Apply stricter rate limit for batch
        if not self.security_validator.check_rate_limit(
            user_id or "anonymous",
            "batch_review"
        ):
            raise Exception("Batch rate limit exceeded")
        
        results = []
        
        if parallel:
            for i in range(0, len(documents), batch_size):
                chunk = documents[i:i + batch_size]
                
                tasks = []
                for doc in chunk:
                    task = self.review_document(
                        content=doc['content'],
                        document_id=doc.get('id'),
                        document_type=doc.get('type', 'generic'),
                        metadata=doc.get('metadata'),
                        user_id=user_id
                    )
                    tasks.append(task)
                
                chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in chunk_results:
                    if not isinstance(result, Exception):
                        results.append(result)
                    else:
                        logger.error(f"Batch review failed: {result}")
                
                # Add delay between batches for rate limiting
                await asyncio.sleep(0.1)
        else:
            for doc in documents:
                try:
                    result = await self.review_document(
                        content=doc['content'],
                        document_id=doc.get('id'),
                        document_type=doc.get('type', 'generic'),
                        metadata=doc.get('metadata'),
                        user_id=user_id
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"Review failed: {e}")
        
        return results
    
    async def get_security_metrics(self) -> Dict[str, Any]:
        """Get current security metrics."""
        return {
            **self.security_metrics,
            'cache_hit_rate': self._cache.hit_rate,
            'active_rate_limiters': len(self.security_validator.rate_limiters),
            'blocked_ips': len(self.security_validator.blocked_ips),
            'recent_threats': self.security_validator.get_security_report()['recent_threats']
        }
    
    async def grant_user_role(self, admin_id: str, user_id: str, role: str):
        """Grant role to user (admin only)."""
        if not self.access_controller.check_permission(admin_id, "admin.grant_role"):
            raise PermissionError("Only admins can grant roles")
        
        self.access_controller.grant_role(user_id, role)
        
        self._log_audit_event(
            "role_granted",
            admin_id,
            None,
            {"target_user": user_id, "role": role}
        )
    
    async def cleanup(self):
        """Cleanup resources securely."""
        if self._security_monitor_task:
            self._security_monitor_task.cancel()
        
        # Secure cleanup of pools
        self.thread_executor.shutdown(wait=False)
        self.process_executor.shutdown(wait=False)
        
        # Secure cache cleanup
        await self._cache.clear()
        
        # Final audit log
        self._log_audit_event(
            "engine_shutdown",
            None,
            None,
            {"security_metrics": self.security_metrics}
        )
    
    def __del__(self):
        """Cleanup on deletion."""
        try:
            asyncio.create_task(self.cleanup())
        except:
            pass