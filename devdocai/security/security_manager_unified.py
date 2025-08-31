"""
M010 Security Module - Unified Security Manager

Consolidated security management with operation modes:
- BASIC: Core security features (Pass 1 implementation)
- PERFORMANCE: Optimized operations (Pass 2 implementation)  
- SECURE: Enhanced security (Pass 3 basic hardening)
- ENTERPRISE: Full enterprise suite (Pass 3 complete hardening)

Consolidates security_manager.py, security_manager_optimized.py, and 
security_manager_hardened.py into a single unified implementation.
"""

import asyncio
import json
import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Callable, Set
from functools import lru_cache
from collections import defaultdict
import multiprocessing as mp

# Import existing security infrastructure
from ..common.security import (
    EncryptionManager, InputValidator, RateLimiter, 
    AuditLogger, security_context
)

# Import M001 configuration management
from ..core.config import ConfigurationManager

# Import component implementations (will be unified)
from .sbom.generator import SBOMGenerator
from .pii.detector_advanced import AdvancedPIIDetector
from .monitoring.threat_detector import ThreatDetector
from .dsr.request_handler import DSRRequestHandler
from .audit.compliance_reporter import ComplianceReporter

# Import optimized components
from .optimized.sbom_optimized import OptimizedSBOMGenerator
from .optimized.pii_optimized import OptimizedPIIDetector
from .optimized.threat_optimized import OptimizedThreatDetector
from .optimized.dsr_optimized import OptimizedDSRHandler
from .optimized.compliance_optimized import OptimizedComplianceReporter

# Import hardened components (enterprise features)
from .hardened.crypto_manager import CryptoManager
from .hardened.threat_intelligence import (
    ThreatIntelligenceEngine, 
    ThreatSeverity, 
    ThreatType,
    ThreatIndicator,
    ThreatEvent
)
from .hardened.zero_trust import (
    ZeroTrustManager,
    Identity,
    Resource,
    AccessContext,
    AccessDecision,
    TrustLevel,
    ResourceType
)
from .hardened.audit_forensics import (
    AuditForensics,
    AuditLevel,
    EventCategory,
    AuditEvent,
    ForensicArtifact
)
from .hardened.security_orchestrator import (
    SecurityOrchestrator,
    IncidentSeverity,
    IncidentStatus,
    SecurityIncident,
    SecurityPlaybook
)

logger = logging.getLogger(__name__)


class SecurityOperationMode(str, Enum):
    """Security operation modes for different deployment scenarios."""
    BASIC = "basic"           # Pass 1: Core security features
    PERFORMANCE = "performance" # Pass 2: Optimized operations
    SECURE = "secure"         # Pass 3: Enhanced security
    ENTERPRISE = "enterprise" # Pass 3: Full enterprise hardening


class SecurityStatus(str, Enum):
    """Security system status."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    MAINTENANCE = "maintenance"


class SecurityPosture(Enum):
    """Security posture levels for enterprise mode."""
    DEFENSIVE = "defensive"
    PROACTIVE = "proactive"
    ADAPTIVE = "adaptive"
    AUTONOMOUS = "autonomous"


@dataclass
class UnifiedSecurityConfig:
    """Unified security configuration supporting all operation modes."""
    mode: SecurityOperationMode = SecurityOperationMode.ENTERPRISE
    posture: SecurityPosture = SecurityPosture.PROACTIVE
    
    # Core security settings
    encryption_enabled: bool = True
    audit_logging: bool = True
    real_time_monitoring: bool = True
    
    # Component enablement
    sbom_enabled: bool = True
    pii_detection_enabled: bool = True
    dsr_enabled: bool = True
    threat_monitoring: bool = True
    compliance_reporting: bool = True
    
    # Performance settings (optimized mode)
    max_concurrent_operations: int = 10
    operation_timeout_seconds: int = 300
    cache_ttl_minutes: int = 30
    enable_connection_pooling: bool = False
    enable_global_cache: bool = False
    enable_parallel_processing: bool = False
    
    # Enterprise hardening settings
    enable_crypto_manager: bool = False
    enable_threat_intelligence: bool = False
    enable_zero_trust: bool = False
    enable_audit_forensics: bool = False
    enable_security_orchestrator: bool = False
    
    # Integration settings
    integrate_with_m001: bool = True
    integrate_with_m002: bool = True
    integrate_with_m008: bool = True
    
    # Alert settings
    alert_email: Optional[str] = None
    alert_webhook: Optional[str] = None
    critical_alert_immediate: bool = True
    
    def __post_init__(self):
        """Configure mode-specific settings."""
        if self.mode == SecurityOperationMode.BASIC:
            # Basic mode: minimal features
            self.enable_connection_pooling = False
            self.enable_global_cache = False
            self.enable_parallel_processing = False
            self.enable_crypto_manager = False
            self.enable_threat_intelligence = False
            self.enable_zero_trust = False
            self.enable_audit_forensics = False
            self.enable_security_orchestrator = False
            
        elif self.mode == SecurityOperationMode.PERFORMANCE:
            # Performance mode: optimizations enabled
            self.enable_connection_pooling = True
            self.enable_global_cache = True
            self.enable_parallel_processing = True
            self.max_concurrent_operations = 50
            
        elif self.mode == SecurityOperationMode.SECURE:
            # Secure mode: enhanced security
            self.enable_connection_pooling = True
            self.enable_global_cache = True
            self.enable_crypto_manager = True
            self.enable_audit_forensics = True
            
        elif self.mode == SecurityOperationMode.ENTERPRISE:
            # Enterprise mode: all features enabled
            self.enable_connection_pooling = True
            self.enable_global_cache = True
            self.enable_parallel_processing = True
            self.enable_crypto_manager = True
            self.enable_threat_intelligence = True
            self.enable_zero_trust = True
            self.enable_audit_forensics = True
            self.enable_security_orchestrator = True
            self.max_concurrent_operations = 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'mode': self.mode.value,
            'posture': self.posture.value,
            'encryption_enabled': self.encryption_enabled,
            'audit_logging': self.audit_logging,
            'real_time_monitoring': self.real_time_monitoring,
            'sbom_enabled': self.sbom_enabled,
            'pii_detection_enabled': self.pii_detection_enabled,
            'dsr_enabled': self.dsr_enabled,
            'threat_monitoring': self.threat_monitoring,
            'compliance_reporting': self.compliance_reporting,
            'max_concurrent_operations': self.max_concurrent_operations,
            'operation_timeout_seconds': self.operation_timeout_seconds,
            'cache_ttl_minutes': self.cache_ttl_minutes,
            'enable_connection_pooling': self.enable_connection_pooling,
            'enable_global_cache': self.enable_global_cache,
            'enable_parallel_processing': self.enable_parallel_processing,
            'enable_crypto_manager': self.enable_crypto_manager,
            'enable_threat_intelligence': self.enable_threat_intelligence,
            'enable_zero_trust': self.enable_zero_trust,
            'enable_audit_forensics': self.enable_audit_forensics,
            'enable_security_orchestrator': self.enable_security_orchestrator,
            'integrate_with_m001': self.integrate_with_m001,
            'integrate_with_m002': self.integrate_with_m002,
            'integrate_with_m008': self.integrate_with_m008,
            'alert_email': self.alert_email,
            'alert_webhook': self.alert_webhook,
            'critical_alert_immediate': self.critical_alert_immediate
        }


@dataclass
class SecurityMetrics:
    """Security metrics for monitoring and reporting."""
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    avg_operation_time_ms: float = 0.0
    
    # Component metrics
    sbom_operations: int = 0
    pii_detections: int = 0
    threat_detections: int = 0
    dsr_requests: int = 0
    compliance_checks: int = 0
    
    # Performance metrics
    cache_hits: int = 0
    cache_misses: int = 0
    concurrent_operations: int = 0
    
    # Security metrics (enterprise mode)
    security_incidents: int = 0
    zero_trust_decisions: int = 0
    forensic_artifacts: int = 0
    
    last_updated: datetime = field(default_factory=datetime.now)


class ConnectionPool:
    """Thread-safe connection pool for shared resources (performance mode)."""
    
    def __init__(self, factory, max_size: int = 10):
        self.factory = factory
        self.max_size = max_size
        self.pool = []
        self.in_use = set()
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)
    
    @contextmanager
    def get_connection(self):
        """Get connection from pool."""
        conn = self._acquire()
        try:
            yield conn
        finally:
            self._release(conn)
    
    def _acquire(self):
        """Acquire connection from pool."""
        with self.condition:
            while True:
                if self.pool:
                    conn = self.pool.pop()
                    self.in_use.add(conn)
                    return conn
                elif len(self.in_use) < self.max_size:
                    conn = self.factory()
                    self.in_use.add(conn)
                    return conn
                else:
                    self.condition.wait()
    
    def _release(self, conn):
        """Release connection back to pool."""
        with self.condition:
            self.in_use.discard(conn)
            self.pool.append(conn)
            self.condition.notify()


class GlobalCache:
    """Thread-safe global cache for performance optimization (performance mode)."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 1800):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache = {}
        self.access_times = {}
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self.lock:
            if key not in self.cache:
                return None
            
            entry_time, value = self.cache[key]
            if time.time() - entry_time > self.ttl_seconds:
                del self.cache[key]
                del self.access_times[key]
                return None
            
            self.access_times[key] = time.time()
            return value
    
    def set(self, key: str, value: Any):
        """Set value in cache."""
        with self.lock:
            current_time = time.time()
            
            # Evict if at capacity
            if len(self.cache) >= self.max_size and key not in self.cache:
                # Remove least recently used
                oldest_key = min(self.access_times.keys(), 
                               key=lambda k: self.access_times[k])
                del self.cache[oldest_key]
                del self.access_times[oldest_key]
            
            self.cache[key] = (current_time, value)
            self.access_times[key] = current_time
    
    def clear(self):
        """Clear cache."""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()


class UnifiedSecurityManager:
    """
    Unified Security Manager consolidating all security operations with configurable modes.
    
    Supports four operation modes:
    - BASIC: Core security features with minimal overhead
    - PERFORMANCE: Optimized operations with caching and parallelization
    - SECURE: Enhanced security with additional hardening
    - ENTERPRISE: Full enterprise security suite with all features
    """
    
    def __init__(self, config: Optional[UnifiedSecurityConfig] = None, 
                 config_manager: Optional[ConfigurationManager] = None):
        """Initialize unified security manager."""
        self.config = config or UnifiedSecurityConfig()
        self.config_manager = config_manager
        self.metrics = SecurityMetrics()
        self.status = SecurityStatus.HEALTHY
        self._initialized = False
        self._lock = threading.RLock()
        
        # Performance optimization components (initialized based on mode)
        self.connection_pool = None
        self.global_cache = None
        self.thread_pool = None
        self.process_pool = None
        
        # Core security components (mode-dependent implementation)
        self.sbom_generator = None
        self.pii_detector = None
        self.threat_detector = None
        self.dsr_handler = None
        self.compliance_reporter = None
        
        # Enterprise hardening components (enterprise mode only)
        self.crypto_manager = None
        self.threat_intelligence = None
        self.zero_trust_manager = None
        self.audit_forensics = None
        self.security_orchestrator = None
        
        # Existing security infrastructure
        self.encryption_manager = None
        self.input_validator = None
        self.rate_limiter = None
        self.audit_logger = None
        
        logger.info(f"Initialized UnifiedSecurityManager in {self.config.mode.value} mode")
    
    async def initialize(self) -> bool:
        """Initialize security manager and all components based on mode."""
        if self._initialized:
            return True
            
        try:
            with self._lock:
                logger.info(f"Initializing security manager in {self.config.mode.value} mode...")
                
                # Initialize performance components based on mode
                await self._initialize_performance_components()
                
                # Initialize core security components with mode-appropriate implementations
                await self._initialize_core_components()
                
                # Initialize enterprise hardening components if enabled
                await self._initialize_enterprise_components()
                
                # Initialize existing security infrastructure
                await self._initialize_security_infrastructure()
                
                # Perform initial health check
                await self._perform_health_check()
                
                self._initialized = True
                self.status = SecurityStatus.HEALTHY
                
                logger.info(f"Security manager initialized successfully in {self.config.mode.value} mode")
                return True
                
        except Exception as e:
            logger.error(f"Failed to initialize security manager: {e}")
            self.status = SecurityStatus.CRITICAL
            return False
    
    async def _initialize_performance_components(self):
        """Initialize performance optimization components."""
        if self.config.enable_connection_pooling:
            self.connection_pool = ConnectionPool(
                factory=lambda: {},  # Generic connection factory
                max_size=self.config.max_concurrent_operations // 2
            )
            logger.info("Connection pooling enabled")
        
        if self.config.enable_global_cache:
            self.global_cache = GlobalCache(
                max_size=1000,
                ttl_seconds=self.config.cache_ttl_minutes * 60
            )
            logger.info("Global caching enabled")
        
        if self.config.enable_parallel_processing:
            self.thread_pool = ThreadPoolExecutor(
                max_workers=self.config.max_concurrent_operations
            )
            self.process_pool = ProcessPoolExecutor(
                max_workers=min(mp.cpu_count(), 4)
            )
            logger.info("Parallel processing enabled")
    
    async def _initialize_core_components(self):
        """Initialize core security components with mode-appropriate implementations."""
        
        if self.config.sbom_enabled:
            if self.config.mode in [SecurityOperationMode.PERFORMANCE, 
                                   SecurityOperationMode.SECURE,
                                   SecurityOperationMode.ENTERPRISE]:
                self.sbom_generator = OptimizedSBOMGenerator()
                logger.info("Initialized optimized SBOM generator")
            else:
                self.sbom_generator = SBOMGenerator()
                logger.info("Initialized basic SBOM generator")
        
        if self.config.pii_detection_enabled:
            if self.config.mode in [SecurityOperationMode.PERFORMANCE,
                                   SecurityOperationMode.SECURE,
                                   SecurityOperationMode.ENTERPRISE]:
                self.pii_detector = OptimizedPIIDetector()
                logger.info("Initialized optimized PII detector")
            else:
                self.pii_detector = AdvancedPIIDetector()
                logger.info("Initialized advanced PII detector")
        
        if self.config.threat_monitoring:
            if self.config.mode in [SecurityOperationMode.PERFORMANCE,
                                   SecurityOperationMode.SECURE,
                                   SecurityOperationMode.ENTERPRISE]:
                self.threat_detector = OptimizedThreatDetector()
                logger.info("Initialized optimized threat detector")
            else:
                self.threat_detector = ThreatDetector()
                logger.info("Initialized basic threat detector")
        
        if self.config.dsr_enabled:
            if self.config.mode in [SecurityOperationMode.PERFORMANCE,
                                   SecurityOperationMode.SECURE,
                                   SecurityOperationMode.ENTERPRISE]:
                self.dsr_handler = OptimizedDSRHandler()
                logger.info("Initialized optimized DSR handler")
            else:
                self.dsr_handler = DSRRequestHandler()
                logger.info("Initialized basic DSR handler")
        
        if self.config.compliance_reporting:
            if self.config.mode in [SecurityOperationMode.PERFORMANCE,
                                   SecurityOperationMode.SECURE,
                                   SecurityOperationMode.ENTERPRISE]:
                self.compliance_reporter = OptimizedComplianceReporter()
                logger.info("Initialized optimized compliance reporter")
            else:
                self.compliance_reporter = ComplianceReporter()
                logger.info("Initialized basic compliance reporter")
    
    async def _initialize_enterprise_components(self):
        """Initialize enterprise hardening components."""
        
        if self.config.enable_crypto_manager:
            self.crypto_manager = CryptoManager()
            await self.crypto_manager.initialize()
            logger.info("Crypto manager enabled")
        
        if self.config.enable_threat_intelligence:
            self.threat_intelligence = ThreatIntelligenceEngine()
            await self.threat_intelligence.initialize()
            logger.info("Threat intelligence enabled")
        
        if self.config.enable_zero_trust:
            self.zero_trust_manager = ZeroTrustManager()
            await self.zero_trust_manager.initialize()
            logger.info("Zero trust manager enabled")
        
        if self.config.enable_audit_forensics:
            self.audit_forensics = AuditForensics()
            await self.audit_forensics.initialize()
            logger.info("Audit forensics enabled")
        
        if self.config.enable_security_orchestrator:
            self.security_orchestrator = SecurityOrchestrator(
                threat_intelligence=self.threat_intelligence,
                audit_forensics=self.audit_forensics
            )
            await self.security_orchestrator.initialize()
            logger.info("Security orchestrator enabled")
    
    async def _initialize_security_infrastructure(self):
        """Initialize existing security infrastructure."""
        self.encryption_manager = EncryptionManager(self.config_manager)
        self.input_validator = InputValidator()
        self.rate_limiter = RateLimiter()
        self.audit_logger = AuditLogger(self.config_manager)
        
        logger.info("Security infrastructure initialized")
    
    async def _perform_health_check(self) -> bool:
        """Perform comprehensive health check of all components."""
        try:
            # Check core components
            if self.sbom_generator and hasattr(self.sbom_generator, 'health_check'):
                if not await self.sbom_generator.health_check():
                    self.status = SecurityStatus.WARNING
                    
            if self.pii_detector and hasattr(self.pii_detector, 'health_check'):
                if not await self.pii_detector.health_check():
                    self.status = SecurityStatus.WARNING
            
            # Check enterprise components
            if self.crypto_manager and hasattr(self.crypto_manager, 'health_check'):
                if not await self.crypto_manager.health_check():
                    self.status = SecurityStatus.WARNING
                    
            logger.info(f"Health check completed. Status: {self.status.value}")
            return self.status != SecurityStatus.CRITICAL
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self.status = SecurityStatus.CRITICAL
            return False
    
    # Core Security Operations
    
    async def generate_sbom(self, project_path: Path, **kwargs) -> Dict[str, Any]:
        """Generate SBOM using mode-appropriate implementation."""
        if not self.sbom_generator:
            raise RuntimeError("SBOM generation not enabled")
            
        start_time = time.time()
        try:
            if self.config.mode == SecurityOperationMode.BASIC:
                result = self.sbom_generator.generate_sbom(str(project_path))
            else:
                # Use optimized implementation
                result = await self.sbom_generator.generate_sbom_async(str(project_path))
            
            self.metrics.sbom_operations += 1
            self.metrics.successful_operations += 1
            
            # Update average operation time
            operation_time = (time.time() - start_time) * 1000
            self._update_operation_time(operation_time)
            
            return result
            
        except Exception as e:
            self.metrics.failed_operations += 1
            logger.error(f"SBOM generation failed: {e}")
            raise
    
    async def detect_pii(self, content: str, **kwargs) -> Dict[str, Any]:
        """Detect PII using mode-appropriate implementation."""
        if not self.pii_detector:
            raise RuntimeError("PII detection not enabled")
            
        start_time = time.time()
        try:
            if self.config.mode == SecurityOperationMode.BASIC:
                result = self.pii_detector.detect_pii(content)
            else:
                # Use optimized implementation
                result = await self.pii_detector.detect_pii_async(content)
            
            self.metrics.pii_detections += 1
            self.metrics.successful_operations += 1
            
            # Update average operation time
            operation_time = (time.time() - start_time) * 1000
            self._update_operation_time(operation_time)
            
            return result
            
        except Exception as e:
            self.metrics.failed_operations += 1
            logger.error(f"PII detection failed: {e}")
            raise
    
    async def detect_threats(self, data: Any, **kwargs) -> Dict[str, Any]:
        """Detect security threats using mode-appropriate implementation."""
        if not self.threat_detector:
            raise RuntimeError("Threat detection not enabled")
            
        start_time = time.time()
        try:
            if self.config.mode == SecurityOperationMode.BASIC:
                result = self.threat_detector.detect_threats(data)
            else:
                # Use optimized implementation
                result = await self.threat_detector.detect_threats_async(data)
            
            # Enterprise threat intelligence integration
            if self.threat_intelligence:
                enriched_result = await self.threat_intelligence.enrich_threats(result)
                result.update(enriched_result)
            
            self.metrics.threat_detections += 1
            self.metrics.successful_operations += 1
            
            # Update average operation time
            operation_time = (time.time() - start_time) * 1000
            self._update_operation_time(operation_time)
            
            return result
            
        except Exception as e:
            self.metrics.failed_operations += 1
            logger.error(f"Threat detection failed: {e}")
            raise
    
    async def handle_dsr_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle DSR request using mode-appropriate implementation."""
        if not self.dsr_handler:
            raise RuntimeError("DSR handling not enabled")
            
        start_time = time.time()
        try:
            if self.config.mode == SecurityOperationMode.BASIC:
                result = self.dsr_handler.process_request(request_data)
            else:
                # Use optimized implementation
                result = await self.dsr_handler.process_request_async(request_data)
            
            self.metrics.dsr_requests += 1
            self.metrics.successful_operations += 1
            
            # Update average operation time
            operation_time = (time.time() - start_time) * 1000
            self._update_operation_time(operation_time)
            
            return result
            
        except Exception as e:
            self.metrics.failed_operations += 1
            logger.error(f"DSR request handling failed: {e}")
            raise
    
    async def generate_compliance_report(self, standard: str = "GDPR") -> Dict[str, Any]:
        """Generate compliance report using mode-appropriate implementation."""
        if not self.compliance_reporter:
            raise RuntimeError("Compliance reporting not enabled")
            
        start_time = time.time()
        try:
            if self.config.mode == SecurityOperationMode.BASIC:
                result = self.compliance_reporter.generate_report(standard)
            else:
                # Use optimized implementation
                result = await self.compliance_reporter.generate_report_async(standard)
            
            self.metrics.compliance_checks += 1
            self.metrics.successful_operations += 1
            
            # Update average operation time
            operation_time = (time.time() - start_time) * 1000
            self._update_operation_time(operation_time)
            
            return result
            
        except Exception as e:
            self.metrics.failed_operations += 1
            logger.error(f"Compliance report generation failed: {e}")
            raise
    
    # Enterprise Security Operations
    
    async def evaluate_zero_trust_access(self, identity: Identity, resource: Resource, 
                                       context: AccessContext) -> AccessDecision:
        """Evaluate zero trust access decision (enterprise mode only)."""
        if not self.zero_trust_manager:
            raise RuntimeError("Zero trust not enabled - requires SECURE or ENTERPRISE mode")
        
        try:
            decision = await self.zero_trust_manager.evaluate_access(identity, resource, context)
            self.metrics.zero_trust_decisions += 1
            return decision
        except Exception as e:
            logger.error(f"Zero trust evaluation failed: {e}")
            raise
    
    async def create_forensic_artifact(self, incident_data: Dict[str, Any]) -> ForensicArtifact:
        """Create forensic artifact for incident investigation (enterprise mode only)."""
        if not self.audit_forensics:
            raise RuntimeError("Audit forensics not enabled - requires SECURE or ENTERPRISE mode")
        
        try:
            artifact = await self.audit_forensics.create_artifact(incident_data)
            self.metrics.forensic_artifacts += 1
            return artifact
        except Exception as e:
            logger.error(f"Forensic artifact creation failed: {e}")
            raise
    
    async def handle_security_incident(self, incident: SecurityIncident) -> Dict[str, Any]:
        """Handle security incident using orchestrator (enterprise mode only)."""
        if not self.security_orchestrator:
            raise RuntimeError("Security orchestrator not enabled - requires ENTERPRISE mode")
        
        try:
            result = await self.security_orchestrator.handle_incident(incident)
            self.metrics.security_incidents += 1
            return result
        except Exception as e:
            logger.error(f"Security incident handling failed: {e}")
            raise
    
    # Utility Methods
    
    def _update_operation_time(self, operation_time_ms: float):
        """Update average operation time."""
        total_ops = self.metrics.total_operations
        current_avg = self.metrics.avg_operation_time_ms
        
        new_avg = ((current_avg * total_ops) + operation_time_ms) / (total_ops + 1)
        self.metrics.avg_operation_time_ms = new_avg
        self.metrics.total_operations += 1
    
    async def get_security_status(self) -> Dict[str, Any]:
        """Get comprehensive security status."""
        return {
            'status': self.status.value,
            'mode': self.config.mode.value,
            'posture': self.config.posture.value if hasattr(self.config, 'posture') else None,
            'initialized': self._initialized,
            'metrics': {
                'total_operations': self.metrics.total_operations,
                'successful_operations': self.metrics.successful_operations,
                'failed_operations': self.metrics.failed_operations,
                'success_rate': (self.metrics.successful_operations / max(1, self.metrics.total_operations)) * 100,
                'avg_operation_time_ms': round(self.metrics.avg_operation_time_ms, 2),
                'sbom_operations': self.metrics.sbom_operations,
                'pii_detections': self.metrics.pii_detections,
                'threat_detections': self.metrics.threat_detections,
                'dsr_requests': self.metrics.dsr_requests,
                'compliance_checks': self.metrics.compliance_checks,
                'security_incidents': self.metrics.security_incidents,
                'zero_trust_decisions': self.metrics.zero_trust_decisions,
                'forensic_artifacts': self.metrics.forensic_artifacts,
                'last_updated': self.metrics.last_updated.isoformat()
            },
            'components': {
                'sbom_enabled': self.sbom_generator is not None,
                'pii_detection_enabled': self.pii_detector is not None,
                'threat_monitoring_enabled': self.threat_detector is not None,
                'dsr_enabled': self.dsr_handler is not None,
                'compliance_enabled': self.compliance_reporter is not None,
                'crypto_manager_enabled': self.crypto_manager is not None,
                'threat_intelligence_enabled': self.threat_intelligence is not None,
                'zero_trust_enabled': self.zero_trust_manager is not None,
                'audit_forensics_enabled': self.audit_forensics is not None,
                'security_orchestrator_enabled': self.security_orchestrator is not None
            }
        }
    
    async def shutdown(self):
        """Gracefully shutdown security manager and all components."""
        logger.info("Shutting down security manager...")
        
        try:
            # Shutdown enterprise components
            if self.security_orchestrator:
                await self.security_orchestrator.shutdown()
            if self.audit_forensics:
                await self.audit_forensics.shutdown()
            if self.zero_trust_manager:
                await self.zero_trust_manager.shutdown()
            if self.threat_intelligence:
                await self.threat_intelligence.shutdown()
            if self.crypto_manager:
                await self.crypto_manager.shutdown()
            
            # Shutdown performance components
            if self.thread_pool:
                self.thread_pool.shutdown(wait=True)
            if self.process_pool:
                self.process_pool.shutdown(wait=True)
            if self.global_cache:
                self.global_cache.clear()
            
            self._initialized = False
            logger.info("Security manager shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Factory function for easy instantiation
def create_security_manager(mode: SecurityOperationMode = SecurityOperationMode.ENTERPRISE,
                           config_manager: Optional[ConfigurationManager] = None) -> UnifiedSecurityManager:
    """Create a unified security manager with the specified mode."""
    config = UnifiedSecurityConfig(mode=mode)
    return UnifiedSecurityManager(config=config, config_manager=config_manager)


# Convenience functions for different modes
def create_basic_security_manager(config_manager: Optional[ConfigurationManager] = None) -> UnifiedSecurityManager:
    """Create a basic security manager with minimal features."""
    return create_security_manager(SecurityOperationMode.BASIC, config_manager)


def create_performance_security_manager(config_manager: Optional[ConfigurationManager] = None) -> UnifiedSecurityManager:
    """Create a performance-optimized security manager."""
    return create_security_manager(SecurityOperationMode.PERFORMANCE, config_manager)


def create_secure_security_manager(config_manager: Optional[ConfigurationManager] = None) -> UnifiedSecurityManager:
    """Create a security-hardened manager."""
    return create_security_manager(SecurityOperationMode.SECURE, config_manager)


def create_enterprise_security_manager(config_manager: Optional[ConfigurationManager] = None) -> UnifiedSecurityManager:
    """Create a full enterprise security manager."""
    return create_security_manager(SecurityOperationMode.ENTERPRISE, config_manager)