"""
Secure AI-Powered Document Generator for M004 Pass 3.

Integrates comprehensive security measures including prompt injection protection,
PII detection, rate limiting, data encryption, and audit logging while maintaining
performance optimizations from Pass 2.

Security Features:
- Prompt injection protection with 50+ patterns
- PII detection and masking
- Rate limiting and cost controls
- Encrypted caching and data isolation
- Comprehensive audit logging
- Template security validation
"""

import asyncio
import logging
import json
import time
import uuid
from typing import Dict, List, Optional, Any, Union, AsyncGenerator, Tuple
from pathlib import Path
from datetime import datetime
from enum import Enum
from concurrent.futures import ThreadPoolExecutor

# Core imports from optimized version
from devdocai.generator.ai_document_generator_optimized import (
    OptimizedAIDocumentGenerator,
    GenerationMode
)
from devdocai.generator.document_workflow import (
    DocumentWorkflow, DocumentType, ReviewPhase
)
from devdocai.generator.prompt_template_engine import (
    PromptTemplateEngine, PromptTemplate, RenderedPrompt
)
from devdocai.generator.cache_manager import CacheManager, get_cache_manager
from devdocai.generator.token_optimizer import TokenOptimizer, StreamingOptimizer, get_token_optimizer

# LLM and storage imports
from devdocai.llm_adapter.adapter_unified import UnifiedLLMAdapter, OperationMode
from devdocai.llm_adapter.config import LLMConfig, ProviderConfig, ProviderType
from devdocai.llm_adapter.providers.base import LLMRequest
from devdocai.storage import LocalStorageSystem
from devdocai.miair.engine_unified import UnifiedMIAIREngine
from devdocai.core.config import ConfigurationManager

# Security imports
from devdocai.generator.security.prompt_guard import (
    PromptGuard, SecurityException, ThreatLevel, InjectionDetection
)
from devdocai.generator.security.rate_limiter import (
    GenerationRateLimiter, RateLimitConfig, LimitType
)
from devdocai.generator.security.data_protection import (
    DataProtectionManager, DataClassification, ComplianceMode, ProtectedData
)
from devdocai.generator.security.audit_logger import (
    SecurityAuditLogger, EventCategory, EventSeverity, SecurityEvent
)

logger = logging.getLogger(__name__)


class SecurityMode(Enum):
    """Security operation modes."""
    STANDARD = "standard"  # Basic security
    ENHANCED = "enhanced"  # Enhanced security with PII detection
    STRICT = "strict"      # Maximum security, may impact performance
    COMPLIANCE = "compliance"  # Full compliance mode (GDPR/CCPA)


class SecureAIDocumentGenerator(OptimizedAIDocumentGenerator):
    """
    Security-hardened AI document generator with comprehensive protection.
    
    Extends the optimized generator with:
    - Multi-layer prompt injection protection
    - PII detection and masking
    - Rate limiting and cost controls
    - Data encryption and isolation
    - Comprehensive audit logging
    - Security overhead <10%
    """
    
    def __init__(
        self,
        config_manager: Optional[ConfigurationManager] = None,
        storage: Optional[LocalStorageSystem] = None,
        template_dir: Optional[Path] = None,
        security_mode: SecurityMode = SecurityMode.ENHANCED,
        compliance_mode: ComplianceMode = ComplianceMode.GDPR,
        enable_audit: bool = True
    ):
        """
        Initialize secure AI document generator.
        
        Args:
            config_manager: M001 Configuration manager
            storage: M002 Storage system
            template_dir: Directory containing prompt templates
            security_mode: Security enforcement level
            compliance_mode: Compliance requirements
            enable_audit: Enable security audit logging
        """
        # Initialize base optimized generator
        super().__init__(
            config_manager=config_manager,
            storage=storage,
            template_dir=template_dir,
            enable_cache=True,
            enable_optimization=True,
            enable_streaming=True
        )
        
        self.security_mode = security_mode
        self.compliance_mode = compliance_mode
        self.enable_audit = enable_audit
        
        # Initialize security components
        self._init_security_components()
        
        # Track security metrics
        self.security_metrics = {
            "injections_blocked": 0,
            "pii_masked": 0,
            "rate_limits_hit": 0,
            "templates_validated": 0,
            "data_encrypted": 0,
            "security_overhead_ms": 0
        }
        
    def _init_security_components(self):
        """Initialize all security components."""
        # Prompt injection protection
        strict_mode = self.security_mode in [SecurityMode.STRICT, SecurityMode.COMPLIANCE]
        self.prompt_guard = PromptGuard(
            strict_mode=strict_mode,
            enable_logging=self.enable_audit
        )
        
        # Rate limiting
        rate_config = RateLimitConfig()
        if self.security_mode == SecurityMode.STRICT:
            # More restrictive limits for strict mode
            rate_config.requests_per_minute = 5
            rate_config.cost_per_day = 5.0
        self.rate_limiter = GenerationRateLimiter(config=rate_config)
        
        # Data protection
        enable_pii = self.security_mode != SecurityMode.STANDARD
        self.data_protection = DataProtectionManager(
            compliance_mode=self.compliance_mode,
            enable_encryption=True,
            enable_pii_detection=enable_pii,
            cache_dir=Path("./secure_cache")
        )
        
        # Audit logging
        if self.enable_audit:
            self.audit_logger = SecurityAuditLogger(
                log_dir=Path("./security_audit"),
                enable_encryption=True,
                enable_chain=True,
                retention_days=90
            )
        else:
            self.audit_logger = None
            
        logger.info(f"Security initialized in {self.security_mode.value} mode")
        
    async def generate_document(
        self,
        document_type: DocumentType,
        context: Dict[str, Any],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate document with comprehensive security checks.
        
        Args:
            document_type: Type of document to generate
            context: Document context and parameters
            user_id: User identifier for rate limiting
            session_id: Session for data isolation
            ip_address: Client IP for DDoS protection
            
        Returns:
            Generated document with security metadata
        """
        start_time = time.time()
        correlation_id = str(uuid.uuid4())
        
        # Create isolated session if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
            self.data_protection.isolate_session(session_id)
            
        try:
            # Step 1: Rate limiting check
            rate_check = await self._check_rate_limits(
                user_id or "anonymous",
                ip_address,
                context
            )
            if not rate_check["allowed"]:
                self._log_security_event(
                    "rate_limit_exceeded",
                    EventCategory.RATE_LIMIT,
                    EventSeverity.MEDIUM,
                    user_id=user_id,
                    details=rate_check,
                    correlation_id=correlation_id
                )
                raise SecurityException(f"Rate limit exceeded: {rate_check['reason']}")
                
            # Step 2: Input validation and sanitization
            sanitized_context = await self._sanitize_inputs(
                context,
                user_id,
                session_id,
                correlation_id
            )
            
            # Step 3: Template security validation
            template_safe = await self._validate_template_security(
                document_type,
                correlation_id
            )
            if not template_safe:
                raise SecurityException("Template security validation failed")
                
            # Step 4: Generate with security monitoring
            generation_result = await self._secure_generation(
                document_type,
                sanitized_context,
                user_id,
                session_id,
                correlation_id
            )
            
            # Step 5: Output validation
            validated_output = await self._validate_output(
                generation_result,
                session_id,
                correlation_id
            )
            
            # Step 6: Secure caching
            if self.enable_cache:
                await self._secure_cache_result(
                    validated_output,
                    session_id
                )
                
            # Record successful generation
            self.rate_limiter.record_success(
                user_id or "anonymous",
                generation_result.get("tokens_used", 0),
                generation_result.get("cost", 0.0),
                document_generated=True
            )
            
            # Calculate security overhead
            security_time = (time.time() - start_time) * 1000
            self.security_metrics["security_overhead_ms"] = security_time
            
            # Log successful generation
            self._log_security_event(
                "document_generated",
                EventCategory.DATA_ACCESS,
                EventSeverity.INFO,
                user_id=user_id,
                session_id=session_id,
                outcome="success",
                details={
                    "document_type": document_type.value,
                    "security_mode": self.security_mode.value,
                    "overhead_ms": security_time
                },
                correlation_id=correlation_id
            )
            
            return {
                **validated_output,
                "security_metadata": {
                    "session_id": session_id,
                    "correlation_id": correlation_id,
                    "security_mode": self.security_mode.value,
                    "pii_detected": generation_result.get("pii_detected", False),
                    "security_overhead_ms": security_time
                }
            }
            
        except SecurityException as e:
            # Handle security exceptions
            self._log_security_event(
                "security_exception",
                EventCategory.INJECTION_ATTEMPT,
                EventSeverity.HIGH,
                user_id=user_id,
                session_id=session_id,
                outcome="blocked",
                details={"error": str(e)},
                threat_indicators=["security_violation"],
                correlation_id=correlation_id
            )
            raise
            
        except Exception as e:
            # Handle other exceptions
            self.rate_limiter.record_error(user_id or "anonymous")
            self._log_security_event(
                "generation_error",
                EventCategory.DATA_ACCESS,
                EventSeverity.MEDIUM,
                user_id=user_id,
                session_id=session_id,
                outcome="failure",
                details={"error": str(e)},
                correlation_id=correlation_id
            )
            raise
            
        finally:
            # Cleanup session if created
            if session_id and not context.get("keep_session"):
                self.data_protection.cleanup_session(session_id)
                
    async def _check_rate_limits(
        self,
        user_id: str,
        ip_address: Optional[str],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check rate limits for request."""
        # Estimate tokens and cost
        estimated_tokens = self._estimate_tokens(context)
        estimated_cost = self._estimate_cost(estimated_tokens)
        
        # Check limits
        allowed, reason, details = self.rate_limiter.check_limits(
            user_id=user_id,
            request_type="document",
            estimated_tokens=estimated_tokens,
            estimated_cost=estimated_cost,
            ip_address=ip_address
        )
        
        return {
            "allowed": allowed,
            "reason": reason,
            "details": details,
            "estimated_tokens": estimated_tokens,
            "estimated_cost": estimated_cost
        }
        
    def _estimate_tokens(self, context: Dict[str, Any]) -> int:
        """Estimate token usage for request."""
        # Simple estimation based on context size
        context_str = json.dumps(context)
        # Rough estimate: 1 token per 4 characters
        base_tokens = len(context_str) // 4
        
        # Add expected response tokens
        response_tokens = 2000  # Average document size
        
        return base_tokens + response_tokens
        
    def _estimate_cost(self, tokens: int) -> float:
        """Estimate cost for token usage."""
        # Average cost per 1K tokens (varies by provider)
        cost_per_1k = 0.02  # $0.02 per 1K tokens
        return (tokens / 1000) * cost_per_1k
        
    async def _sanitize_inputs(
        self,
        context: Dict[str, Any],
        user_id: Optional[str],
        session_id: str,
        correlation_id: str
    ) -> Dict[str, Any]:
        """Sanitize and validate all inputs."""
        sanitized = {}
        threats_detected = []
        
        for key, value in context.items():
            if isinstance(value, str):
                # Check for prompt injection
                clean_value, detections = self.prompt_guard.sanitize_input(value)
                
                if detections:
                    threats_detected.extend(detections)
                    self.security_metrics["injections_blocked"] += len(detections)
                    
                # Check for PII
                has_pii, pii_matches, masked_value = self.data_protection.scan_for_pii(clean_value)
                
                if has_pii:
                    self.security_metrics["pii_masked"] += len(pii_matches)
                    clean_value = masked_value
                    
                sanitized[key] = clean_value
            else:
                sanitized[key] = value
                
        # Log if threats were detected
        if threats_detected:
            self._log_security_event(
                "injection_attempts_blocked",
                EventCategory.INJECTION_ATTEMPT,
                EventSeverity.HIGH,
                user_id=user_id,
                session_id=session_id,
                outcome="blocked",
                details={
                    "patterns_matched": len(threats_detected),
                    "categories": list(set(d.category for d in threats_detected))
                },
                threat_indicators=[d.pattern for d in threats_detected[:5]],  # First 5
                correlation_id=correlation_id
            )
            
        return sanitized
        
    async def _validate_template_security(
        self,
        document_type: DocumentType,
        correlation_id: str
    ) -> bool:
        """Validate template security."""
        try:
            # Get template for document type
            template_path = self.template_dir / f"{document_type.value}.yaml"
            
            if template_path.exists():
                with open(template_path, 'r') as f:
                    template_content = f.read()
                    
                # Check template safety
                is_safe, issues = self.prompt_guard.check_template_safety(template_content)
                
                self.security_metrics["templates_validated"] += 1
                
                if not is_safe:
                    self._log_security_event(
                        "template_validation_failed",
                        EventCategory.CONFIGURATION,
                        EventSeverity.HIGH,
                        details={
                            "template": document_type.value,
                            "issues": issues
                        },
                        threat_indicators=issues,
                        correlation_id=correlation_id
                    )
                    return False
                    
            return True
            
        except Exception as e:
            logger.error(f"Template validation error: {e}")
            return False
            
    async def _secure_generation(
        self,
        document_type: DocumentType,
        context: Dict[str, Any],
        user_id: Optional[str],
        session_id: str,
        correlation_id: str
    ) -> Dict[str, Any]:
        """Generate document with security monitoring."""
        # Create protected context
        protected_context = self.data_protection.encrypt_data(
            json.dumps(context),
            DataClassification.CONFIDENTIAL,
            session_id
        )
        self.security_metrics["data_encrypted"] += 1
        
        # Generate using parent class method
        result = await super().generate_document(document_type, context)
        
        # Add security tracking
        result["pii_detected"] = False
        result["session_id"] = session_id
        
        return result
        
    async def _validate_output(
        self,
        result: Dict[str, Any],
        session_id: str,
        correlation_id: str
    ) -> Dict[str, Any]:
        """Validate generated output for security issues."""
        if "content" in result:
            content = result["content"]
            
            # Check for prompt leakage
            is_safe, detections = self.prompt_guard.validate_output(content)
            
            if not is_safe:
                self._log_security_event(
                    "output_validation_failed",
                    EventCategory.DATA_ACCESS,
                    EventSeverity.CRITICAL,
                    session_id=session_id,
                    outcome="blocked",
                    details={
                        "detections": len(detections),
                        "categories": list(set(d.category for d in detections))
                    },
                    threat_indicators=[d.pattern for d in detections],
                    correlation_id=correlation_id
                )
                
                # Sanitize output
                result["content"] = "[Output blocked due to security violation]"
                result["security_blocked"] = True
                
            # Final PII scan
            has_pii, pii_matches, masked_content = self.data_protection.scan_for_pii(content)
            if has_pii:
                result["content"] = masked_content
                result["pii_detected"] = True
                result["pii_categories"] = list(set(m.category for m in pii_matches))
                
        return result
        
    async def _secure_cache_result(
        self,
        result: Dict[str, Any],
        session_id: str
    ):
        """Securely cache generation result."""
        # Encrypt sensitive fields before caching
        if "content" in result:
            encrypted = self.data_protection.encrypt_data(
                result["content"],
                DataClassification.INTERNAL,
                session_id
            )
            
            # Store encrypted reference
            cache_key = f"secure_{session_id}_{encrypted.original_hash}"
            
            # Use parent cache manager with encrypted data
            if hasattr(self, 'cache_manager'):
                await self.cache_manager.set(cache_key, {
                    "encrypted_ref": encrypted.original_hash,
                    "metadata": {
                        k: v for k, v in result.items()
                        if k not in ["content", "api_keys"]
                    }
                })
                
    def _log_security_event(
        self,
        action: str,
        category: EventCategory,
        severity: EventSeverity,
        **kwargs
    ):
        """Log security event to audit system."""
        if self.audit_logger:
            self.audit_logger.log_event(
                action=action,
                category=category,
                severity=severity,
                **kwargs
            )
            
    def get_security_metrics(self) -> Dict[str, Any]:
        """Get security metrics and statistics."""
        metrics = {
            **self.security_metrics,
            "prompt_guard_report": self.prompt_guard.get_security_report(),
            "rate_limiter_stats": self.rate_limiter.get_global_stats(),
            "data_protection_report": self.data_protection.get_compliance_report(),
        }
        
        if self.audit_logger:
            metrics["audit_stats"] = self.audit_logger.generate_compliance_report()
            
        return metrics
        
    def generate_security_report(
        self,
        user_id: Optional[str] = None,
        compliance_type: str = "SOC2"
    ) -> Dict[str, Any]:
        """
        Generate comprehensive security report.
        
        Args:
            user_id: Specific user to report on
            compliance_type: Type of compliance report
            
        Returns:
            Security report data
        """
        report = {
            "generated_at": datetime.now().isoformat(),
            "security_mode": self.security_mode.value,
            "compliance_mode": self.compliance_mode.value,
            "metrics": self.get_security_metrics()
        }
        
        if user_id:
            report["user_stats"] = self.rate_limiter.get_user_stats(user_id)
            
        if self.audit_logger:
            report["compliance_report"] = self.audit_logger.generate_compliance_report(
                compliance_type=compliance_type
            )
            
        return report
        
    async def cleanup(self):
        """Clean up security resources."""
        # Clean up expired data
        if hasattr(self.data_protection, 'cleanup_expired_data'):
            self.data_protection.cleanup_expired_data()
            
        # Clean up old audit logs
        if self.audit_logger:
            self.audit_logger.cleanup_old_logs()
            
        # Call parent cleanup
        if hasattr(super(), 'cleanup'):
            await super().cleanup()