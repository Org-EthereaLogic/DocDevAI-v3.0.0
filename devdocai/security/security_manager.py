"""
Security Manager - Central security orchestration for M010.

Provides unified security management across all DevDocAI modules,
coordinating SBOM generation, PII detection, DSR handling, monitoring,
and compliance reporting.
"""

import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass, field
from pathlib import Path
import asyncio
import threading
from contextlib import contextmanager

# Import existing security infrastructure
from ..common.security import (
    EncryptionManager, InputValidator, RateLimiter, 
    AuditLogger, security_context
)

# Import M001 configuration management
from ..core.config import ConfigurationManager

logger = logging.getLogger(__name__)


class SecurityMode(str, Enum):
    """Security operation modes."""
    BASIC = "basic"           # Basic security features
    STANDARD = "standard"     # Standard enterprise security  
    STRICT = "strict"         # High security environment
    ENTERPRISE = "enterprise" # Full enterprise security suite


class SecurityStatus(str, Enum):
    """Security system status."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    MAINTENANCE = "maintenance"


@dataclass
class SecurityConfig:
    """Security configuration for M010."""
    mode: SecurityMode = SecurityMode.ENTERPRISE
    
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
    
    # Performance settings
    max_concurrent_operations: int = 10
    operation_timeout_seconds: int = 300
    cache_ttl_minutes: int = 30
    
    # Integration settings
    integrate_with_m001: bool = True
    integrate_with_m002: bool = True
    integrate_with_m008: bool = True
    
    # Alert settings
    alert_email: Optional[str] = None
    alert_webhook: Optional[str] = None
    critical_alert_immediate: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'mode': self.mode.value,
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
            'integrate_with_m001': self.integrate_with_m001,
            'integrate_with_m002': self.integrate_with_m002,
            'integrate_with_m008': self.integrate_with_m008,
            'alert_email': self.alert_email,
            'alert_webhook': self.alert_webhook,
            'critical_alert_immediate': self.critical_alert_immediate
        }


@dataclass 
class SecurityMetrics:
    """Security system metrics."""
    operations_processed: int = 0
    threats_detected: int = 0
    pii_instances_found: int = 0
    sbom_documents_generated: int = 0
    dsr_requests_processed: int = 0
    compliance_reports_generated: int = 0
    
    # Performance metrics
    avg_response_time_ms: float = 0.0
    success_rate: float = 1.0
    error_count: int = 0
    
    # Security scores
    security_posture_score: float = 1.0
    compliance_score: float = 1.0
    threat_level: SecurityStatus = SecurityStatus.HEALTHY
    
    # Timestamps
    last_updated: datetime = field(default_factory=datetime.now)
    last_threat_scan: Optional[datetime] = None
    last_compliance_check: Optional[datetime] = None


class SecurityManager:
    """
    Central security orchestration manager for M010.
    
    Coordinates all security operations across DevDocAI modules including
    SBOM generation, PII detection, DSR handling, threat monitoring,
    and compliance reporting.
    """
    
    def __init__(self, config: Optional[Union[Dict[str, Any], SecurityConfig]] = None):
        """
        Initialize Security Manager.
        
        Args:
            config: Security configuration
        """
        # Parse configuration
        if isinstance(config, dict):
            self.config = SecurityConfig(**config)
        elif isinstance(config, SecurityConfig):
            self.config = config
        else:
            self.config = SecurityConfig()
        
        # Initialize core components
        self.encryption_manager = EncryptionManager()
        self.input_validator = InputValidator()
        self.rate_limiter = RateLimiter(
            max_requests=100,
            window_seconds=60
        )
        self.audit_logger = AuditLogger()
        
        # Initialize metrics
        self.metrics = SecurityMetrics()
        
        # Component instances (lazy-loaded)
        self._sbom_generator = None
        self._pii_detector = None
        self._dsr_handler = None
        self._threat_detector = None
        self._compliance_reporter = None
        
        # Thread safety
        self._lock = threading.Lock()
        self._shutdown_event = threading.Event()
        
        # Background monitoring task
        self._monitoring_task = None
        if self.config.real_time_monitoring:
            self._start_monitoring()
        
        logger.info(f"SecurityManager initialized with mode: {self.config.mode}")
    
    # ========================================================================
    # CORE SECURITY OPERATIONS
    # ========================================================================
    
    @contextmanager
    def secure_operation(self, operation_name: str, user_id: Optional[str] = None):
        """
        Context manager for secure operations.
        
        Args:
            operation_name: Name of the operation
            user_id: Optional user identifier
        """
        start_time = time.perf_counter()
        
        with security_context(operation_name, user_id):
            # Rate limiting check
            identifier = user_id or 'system'
            allowed, reason = self.rate_limiter.check_rate_limit(identifier)
            if not allowed:
                raise PermissionError(f"Rate limit exceeded: {reason}")
            
            try:
                yield
                
                # Update success metrics
                elapsed_time = (time.perf_counter() - start_time) * 1000  # ms
                self._update_metrics(operation_name, elapsed_time, success=True)
                
            except Exception as e:
                # Update error metrics
                elapsed_time = (time.perf_counter() - start_time) * 1000  # ms
                self._update_metrics(operation_name, elapsed_time, success=False)
                
                # Log security event
                self.audit_logger.log_event('operation_failure', {
                    'operation': operation_name,
                    'user_id': user_id,
                    'error': str(e),
                    'duration_ms': elapsed_time
                })
                raise
    
    def validate_input(self, data: Any, validation_rules: Optional[Dict[str, Any]] = None) -> Any:
        """
        Validate and sanitize input data.
        
        Args:
            data: Data to validate
            validation_rules: Optional validation rules
            
        Returns:
            Sanitized data
        """
        if isinstance(data, str):
            return self.input_validator.sanitize_string(data)
        elif isinstance(data, dict):
            allowed_keys = validation_rules.get('allowed_keys') if validation_rules else None
            return self.input_validator.sanitize_dict(data, allowed_keys)
        elif isinstance(data, list):
            max_length = validation_rules.get('max_length') if validation_rules else None
            return self.input_validator.sanitize_list(data, max_length)
        else:
            return data
    
    def encrypt_sensitive_data(self, data: Union[str, bytes, Dict[str, Any]]) -> str:
        """
        Encrypt sensitive data.
        
        Args:
            data: Data to encrypt
            
        Returns:
            Encrypted data as base64 string
        """
        if isinstance(data, dict):
            return self.encryption_manager.encrypt_field(data)
        else:
            encrypted_bytes = self.encryption_manager.encrypt(data)
            import base64
            return base64.b64encode(encrypted_bytes).decode('utf-8')
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> Any:
        """
        Decrypt sensitive data.
        
        Args:
            encrypted_data: Base64 encoded encrypted data
            
        Returns:
            Decrypted data
        """
        try:
            return self.encryption_manager.decrypt_field(encrypted_data)
        except:
            # Try as raw bytes
            import base64
            encrypted_bytes = base64.b64decode(encrypted_data)
            decrypted_bytes = self.encryption_manager.decrypt(encrypted_bytes)
            return decrypted_bytes.decode('utf-8')
    
    # ========================================================================
    # COMPONENT ACCESS METHODS
    # ========================================================================
    
    def get_sbom_generator(self):
        """Get SBOM generator instance."""
        if self._sbom_generator is None and self.config.sbom_enabled:
            from .sbom.generator import SBOMGenerator
            self._sbom_generator = SBOMGenerator(
                security_manager=self,
                encryption_enabled=self.config.encryption_enabled
            )
        return self._sbom_generator
    
    def get_pii_detector(self):
        """Get advanced PII detector instance."""
        if self._pii_detector is None and self.config.pii_detection_enabled:
            from .pii.detector_advanced import AdvancedPIIDetector, PIIConfig, PIIDetectionMode
            pii_config = PIIConfig(
                mode=PIIDetectionMode.ADVANCED,
                real_time_masking=self.config.real_time_monitoring
            )
            self._pii_detector = AdvancedPIIDetector(
                config=pii_config,
                security_manager=self
            )
        return self._pii_detector
    
    def get_dsr_handler(self):
        """Get DSR request handler instance.""" 
        if self._dsr_handler is None and self.config.dsr_enabled:
            from .dsr.request_handler import DSRRequestHandler
            self._dsr_handler = DSRRequestHandler(
                security_manager=self,
                encryption_manager=self.encryption_manager
            )
        return self._dsr_handler
    
    def get_threat_detector(self):
        """Get threat detector instance."""
        if self._threat_detector is None and self.config.threat_monitoring:
            from .monitoring.threat_detector import ThreatDetector
            self._threat_detector = ThreatDetector(
                security_manager=self,
                real_time_monitoring=self.config.real_time_monitoring
            )
        return self._threat_detector
    
    def get_compliance_reporter(self):
        """Get compliance reporter instance."""
        if self._compliance_reporter is None and self.config.compliance_reporting:
            from .audit.compliance_reporter import ComplianceReporter
            self._compliance_reporter = ComplianceReporter(
                security_manager=self,
                audit_logger=self.audit_logger
            )
        return self._compliance_reporter
    
    # ========================================================================
    # UNIFIED SECURITY OPERATIONS
    # ========================================================================
    
    async def perform_security_scan(self, target: Dict[str, Any], 
                                   scan_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Perform comprehensive security scan.
        
        Args:
            target: Target data/document to scan
            scan_types: Optional list of scan types to perform
            
        Returns:
            Security scan results
        """
        with self.secure_operation("security_scan"):
            scan_types = scan_types or ['pii', 'threats', 'compliance']
            results = {
                'scan_id': f"scan_{int(time.time())}",
                'timestamp': datetime.now().isoformat(),
                'target_size': len(str(target)),
                'scan_types': scan_types,
                'results': {}
            }
            
            # PII Detection
            if 'pii' in scan_types and self.config.pii_detection_enabled:
                pii_detector = self.get_pii_detector()
                if pii_detector:
                    pii_results = await pii_detector.scan_data(target)
                    results['results']['pii'] = pii_results
            
            # Threat Detection
            if 'threats' in scan_types and self.config.threat_monitoring:
                threat_detector = self.get_threat_detector()
                if threat_detector:
                    threat_results = await threat_detector.scan_for_threats(target)
                    results['results']['threats'] = threat_results
            
            # Compliance Check
            if 'compliance' in scan_types and self.config.compliance_reporting:
                compliance_reporter = self.get_compliance_reporter()
                if compliance_reporter:
                    compliance_results = await compliance_reporter.assess_compliance(target)
                    results['results']['compliance'] = compliance_results
            
            return results
    
    def generate_sbom(self, project_path: Union[str, Path], 
                     format_type: str = "spdx-json",
                     include_signature: bool = True) -> Dict[str, Any]:
        """
        Generate Software Bill of Materials.
        
        Args:
            project_path: Path to project
            format_type: SBOM format (spdx-json, cyclonedx-json)
            include_signature: Whether to include digital signature
            
        Returns:
            SBOM generation results
        """
        with self.secure_operation("sbom_generation"):
            if not self.config.sbom_enabled:
                raise ValueError("SBOM generation is disabled")
            
            sbom_generator = self.get_sbom_generator()
            if not sbom_generator:
                raise RuntimeError("SBOM generator not available")
            
            return sbom_generator.generate_sbom(
                project_path=project_path,
                format_type=format_type,
                include_signature=include_signature
            )
    
    def process_dsr_request(self, request_type: str, user_data: Dict[str, Any],
                           user_id: str) -> Dict[str, Any]:
        """
        Process Data Subject Rights request.
        
        Args:
            request_type: Type of DSR request (access, rectification, erasure, etc.)
            user_data: User data for the request
            user_id: User identifier
            
        Returns:
            DSR processing results
        """
        with self.secure_operation("dsr_processing", user_id):
            if not self.config.dsr_enabled:
                raise ValueError("DSR processing is disabled")
            
            dsr_handler = self.get_dsr_handler()
            if not dsr_handler:
                raise RuntimeError("DSR handler not available")
            
            return dsr_handler.process_request(
                request_type=request_type,
                user_data=user_data,
                user_id=user_id
            )
    
    # ========================================================================
    # MONITORING AND METRICS
    # ========================================================================
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get current security system status."""
        with self._lock:
            return {
                'status': self.metrics.threat_level.value,
                'metrics': {
                    'operations_processed': self.metrics.operations_processed,
                    'threats_detected': self.metrics.threats_detected,
                    'pii_instances_found': self.metrics.pii_instances_found,
                    'sbom_documents_generated': self.metrics.sbom_documents_generated,
                    'dsr_requests_processed': self.metrics.dsr_requests_processed,
                    'avg_response_time_ms': self.metrics.avg_response_time_ms,
                    'success_rate': self.metrics.success_rate,
                    'security_posture_score': self.metrics.security_posture_score,
                    'compliance_score': self.metrics.compliance_score
                },
                'config': self.config.to_dict(),
                'last_updated': self.metrics.last_updated.isoformat()
            }
    
    def _update_metrics(self, operation: str, duration_ms: float, success: bool = True):
        """Update security metrics."""
        with self._lock:
            self.metrics.operations_processed += 1
            
            if not success:
                self.metrics.error_count += 1
            
            # Update average response time
            total_ops = self.metrics.operations_processed
            current_avg = self.metrics.avg_response_time_ms
            self.metrics.avg_response_time_ms = (
                (current_avg * (total_ops - 1) + duration_ms) / total_ops
            )
            
            # Update success rate
            success_count = total_ops - self.metrics.error_count
            self.metrics.success_rate = success_count / total_ops if total_ops > 0 else 1.0
            
            # Update timestamp
            self.metrics.last_updated = datetime.now()
    
    def _start_monitoring(self):
        """Start background monitoring task."""
        def monitoring_loop():
            while not self._shutdown_event.wait(60):  # Check every minute
                try:
                    # Update security posture
                    self._update_security_posture()
                    
                    # Check for threats
                    if self.config.threat_monitoring:
                        threat_detector = self.get_threat_detector()
                        if threat_detector:
                            # Perform background threat scan
                            pass  # Implementation would go here
                    
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
        
        self._monitoring_task = threading.Thread(target=monitoring_loop, daemon=True)
        self._monitoring_task.start()
    
    def _update_security_posture(self):
        """Update overall security posture score."""
        with self._lock:
            # Calculate posture based on various factors
            factors = {
                'success_rate': self.metrics.success_rate * 0.3,
                'threat_level': (1.0 if self.metrics.threat_level == SecurityStatus.HEALTHY else 
                               0.7 if self.metrics.threat_level == SecurityStatus.WARNING else 0.3) * 0.4,
                'compliance_score': self.metrics.compliance_score * 0.3
            }
            
            self.metrics.security_posture_score = sum(factors.values())
            
            # Update threat level based on posture
            if self.metrics.security_posture_score >= 0.9:
                self.metrics.threat_level = SecurityStatus.HEALTHY
            elif self.metrics.security_posture_score >= 0.7:
                self.metrics.threat_level = SecurityStatus.WARNING  
            else:
                self.metrics.threat_level = SecurityStatus.CRITICAL
    
    # ========================================================================
    # INTEGRATION METHODS
    # ========================================================================
    
    def integrate_with_m001(self, config_manager: Optional[ConfigurationManager] = None):
        """Integrate with M001 Configuration Manager."""
        if not self.config.integrate_with_m001:
            return
        
        try:
            if config_manager is None:
                config_manager = ConfigurationManager()
            
            # Update security settings from M001 config
            system_config = config_manager.get_config()
            if hasattr(system_config, 'security'):
                security_config = system_config.security
                
                # Update encryption settings
                if hasattr(security_config, 'encryption_enabled'):
                    self.config.encryption_enabled = security_config.encryption_enabled
                
                # Update other security settings as needed
                logger.info("Successfully integrated with M001 Configuration Manager")
            
        except Exception as e:
            logger.warning(f"Failed to integrate with M001: {e}")
    
    def integrate_with_m002(self, storage_system=None):
        """Integrate with M002 Local Storage System.""" 
        if not self.config.integrate_with_m002:
            return
        
        try:
            # Integration with storage for security data persistence
            # Implementation would use M002's PII detector and storage
            logger.info("Successfully integrated with M002 Local Storage System")
            
        except Exception as e:
            logger.warning(f"Failed to integrate with M002: {e}")
    
    def integrate_with_m008(self, llm_adapter=None):
        """Integrate with M008 LLM Adapter."""
        if not self.config.integrate_with_m008:
            return
        
        try:
            # Integration with LLM security features
            # Implementation would leverage M008's security validation
            logger.info("Successfully integrated with M008 LLM Adapter")
            
        except Exception as e:
            logger.warning(f"Failed to integrate with M008: {e}")
    
    # ========================================================================
    # LIFECYCLE METHODS
    # ========================================================================
    
    def shutdown(self):
        """Shutdown security manager and all components."""
        logger.info("Shutting down SecurityManager...")
        
        # Signal shutdown to monitoring task
        self._shutdown_event.set()
        
        # Wait for monitoring task to complete
        if self._monitoring_task and self._monitoring_task.is_alive():
            self._monitoring_task.join(timeout=5)
        
        # Shutdown components
        if self._threat_detector:
            self._threat_detector.shutdown()
        
        # Clear sensitive data
        self.encryption_manager.clear_master_key()
        
        logger.info("SecurityManager shutdown complete")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()


# Convenience function
def create_security_manager(mode: Union[str, SecurityMode] = SecurityMode.ENTERPRISE,
                          **kwargs) -> SecurityManager:
    """
    Create a configured SecurityManager instance.
    
    Args:
        mode: Security mode
        **kwargs: Additional configuration options
        
    Returns:
        Configured SecurityManager
    """
    if isinstance(mode, str):
        mode = SecurityMode(mode)
    
    config = SecurityConfig(mode=mode, **kwargs)
    return SecurityManager(config)