"""
M008: Secure LLM Adapter Implementation.

Production-ready LLM adapter with comprehensive security features including
input validation, rate limiting, audit logging, and OWASP compliance.
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Any, Union, AsyncGenerator
from decimal import Decimal
from datetime import datetime

from .config import LLMConfig, ProviderConfig, ProviderType
from .providers.base import BaseProvider, LLMRequest, LLMResponse
from .providers.openai import OpenAIProvider
from .providers.anthropic import AnthropicProvider
from .providers.google import GoogleProvider
from .providers.local import LocalProvider
from .cost_tracker import CostTracker, UsageRecord, CostAlert
from .fallback_manager import FallbackManager, FallbackAttempt
from .integrations import MIAIRIntegration, ConfigIntegration, QualityAnalyzer

# Import security components
from .security import (
    SecurityManager, SecurityConfig, SecurityContext,
    Role, Permission, APIKeyManager
)
from .validator import ValidationLevel, ThreatType
from .rate_limiter import RateLimitLevel
from .audit_logger import EventType, EventSeverity

# Performance optimizations
from .cache import ResponseCache
from .streaming import StreamingHandler
from .batch_processor import BatchProcessor
from .token_optimizer import TokenOptimizer
from .connection_pool import ConnectionPool

logger = logging.getLogger(__name__)


class SecureLLMAdapter:
    """
    Secure LLM Adapter with comprehensive protection.
    
    Implements defense-in-depth security architecture:
    - Input validation and sanitization
    - Rate limiting and DDoS protection
    - RBAC and permission management
    - Audit logging and compliance
    - API key encryption and rotation
    - OWASP Top 10 protection
    """
    
    def __init__(
        self,
        config: LLMConfig,
        security_config: Optional[SecurityConfig] = None
    ):
        """
        Initialize secure LLM adapter.
        
        Args:
            config: LLM adapter configuration
            security_config: Security configuration
        """
        self.config = config
        self.security_config = security_config or SecurityConfig()
        self.logger = logging.getLogger(f"{__name__}.SecureLLMAdapter")
        
        # Initialize security manager
        self.security_manager = SecurityManager(self.security_config)
        
        # Initialize secure API key management
        self._init_secure_api_keys()
        
        # Initialize providers with security
        self.providers: Dict[str, BaseProvider] = {}
        self._initialize_providers()
        
        # Initialize cost tracking with audit
        if self.config.cost_tracking_enabled:
            self.cost_tracker = CostTracker(self.config.cost_limits)
        else:
            self.cost_tracker = None
        
        # Initialize fallback manager with circuit breakers
        self.fallback_manager = FallbackManager(
            providers=self.providers,
            fallback_strategy=self.config.fallback_strategy
        )
        
        # Initialize MIAIR integration
        self.miair_integration = None
        if self.config.miair_integration_enabled:
            self.miair_integration = MIAIRIntegration(self)
        
        # Initialize quality analyzer
        self.quality_analyzer = QualityAnalyzer(self)
        
        # Performance components with security
        self.cache = ResponseCache(
            max_size=1000,
            ttl_seconds=3600,
            similarity_threshold=0.95
        )
        self.streaming_handler = StreamingHandler()
        self.batch_processor = BatchProcessor(self)
        self.token_optimizer = TokenOptimizer()
        self.connection_pool = ConnectionPool()
        
        # Security context cache
        self._security_contexts: Dict[str, SecurityContext] = {}
        
        self.logger.info(
            f"Secure LLM Adapter initialized with {len(self.providers)} providers "
            f"and {self.security_config.validation_level.value} validation"
        )
    
    def _init_secure_api_keys(self):
        """Initialize secure API key storage."""
        if not self.security_manager.api_key_manager:
            return
        
        # Migrate existing API keys to secure storage
        for name, provider_config in self.config.providers.items():
            if provider_config.api_key:
                # Store in secure manager
                key_id = self.security_manager.api_key_manager.store_api_key(
                    provider=name,
                    api_key=provider_config.api_key,
                    metadata={'original_config': True}
                )
                
                # Replace with key ID reference
                provider_config.api_key = None
                provider_config.api_key_encrypted = key_id
                
                self.logger.info(f"Migrated API key for {name} to secure storage")
    
    def _initialize_providers(self) -> None:
        """Initialize all configured providers with security."""
        provider_classes = {
            ProviderType.OPENAI: OpenAIProvider,
            ProviderType.ANTHROPIC: AnthropicProvider,
            ProviderType.GOOGLE: GoogleProvider,
            ProviderType.LOCAL: LocalProvider,
        }
        
        for name, config in self.config.providers.items():
            if not config.enabled:
                continue
            
            # Retrieve decrypted API key if needed
            if config.api_key_encrypted and self.security_manager.api_key_manager:
                config.api_key = self.security_manager.api_key_manager.retrieve_api_key(
                    config.api_key_encrypted
                )
                
                # Check if rotation is needed
                if self.security_manager.api_key_manager.check_rotation_needed(
                    config.api_key_encrypted,
                    self.security_config.api_key_rotation_days
                ):
                    self.logger.warning(f"API key rotation needed for {name}")
            
            # Create provider instance
            provider_class = provider_classes.get(config.provider_type)
            if provider_class:
                try:
                    self.providers[name] = provider_class(config)
                    
                    # Add circuit breaker
                    circuit_breaker = self.security_manager.get_circuit_breaker(name)
                    
                    self.logger.info(f"Initialized secure provider: {name}")
                except Exception as e:
                    self.logger.error(f"Failed to initialize provider {name}: {e}")
    
    async def create_session(
        self,
        user_id: str,
        roles: Optional[List[Role]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> SecurityContext:
        """
        Create a secure session for user.
        
        Args:
            user_id: User identifier
            roles: User roles (defaults to [Role.USER])
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Security context for the session
        """
        roles = roles or [Role.USER]
        
        context = await self.security_manager.create_session(
            user_id=user_id,
            roles=roles,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Cache context
        self._security_contexts[context.session_id] = context
        
        return context
    
    async def query(
        self,
        request: LLMRequest,
        session_id: Optional[str] = None,
        security_context: Optional[SecurityContext] = None
    ) -> LLMResponse:
        """
        Execute secure LLM query with full protection.
        
        Args:
            request: LLM request
            session_id: Session ID for existing session
            security_context: Security context (if not using session)
            
        Returns:
            LLM response
            
        Raises:
            SecurityError: If security validation fails
            ProviderError: If provider fails
        """
        # Get or create security context
        if security_context:
            context = security_context
        elif session_id and session_id in self._security_contexts:
            context = self._security_contexts[session_id]
        else:
            # Create temporary context for anonymous request
            context = await self.create_session(
                user_id=f"anonymous_{uuid.uuid4().hex[:8]}",
                roles=[Role.GUEST]
            )
        
        # Generate request ID
        request_id = str(uuid.uuid4())
        context.request_id = request_id
        
        try:
            # 1. Validate request
            is_valid, sanitized_prompt, error = await self.security_manager.validate_request(
                context=context,
                prompt=request.prompt,
                provider=request.provider or self.config.default_provider,
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )
            
            if not is_valid:
                raise SecurityError(f"Request validation failed: {error}")
            
            # Update request with sanitized prompt
            request.prompt = sanitized_prompt
            
            # 2. Check cache (with security hash)
            cache_key = self._generate_secure_cache_key(request, context)
            cached_response = await self.cache.get(cache_key)
            
            if cached_response:
                self.logger.info(f"Cache hit for request {request_id}")
                
                # Log cache hit
                if self.security_manager.audit_logger:
                    await self.security_manager.audit_logger.log_event(
                        AuditEvent(
                            event_id=request_id,
                            timestamp=datetime.utcnow(),
                            event_type=EventType.API_RESPONSE,
                            severity=EventSeverity.INFO,
                            user_id=context.user_id,
                            session_id=context.session_id,
                            request_id=request_id,
                            success=True,
                            data={'cache_hit': True}
                        )
                    )
                
                return cached_response
            
            # 3. Optimize tokens
            if self.token_optimizer:
                request = self.token_optimizer.optimize_request(request)
            
            # 4. Execute query with circuit breaker
            provider_name = request.provider or self.config.default_provider
            circuit_breaker = self.security_manager.get_circuit_breaker(provider_name)
            
            async def execute_query():
                provider = self.providers.get(provider_name)
                if not provider:
                    raise ValueError(f"Provider not found: {provider_name}")
                
                return await provider.query(request)
            
            # Execute with circuit breaker protection
            response = await circuit_breaker.call(execute_query)
            
            # 5. Validate response
            is_valid, sanitized_response, error = await self.security_manager.validate_response(
                context=context,
                response=response.content,
                provider=provider_name,
                model=request.model
            )
            
            if not is_valid:
                self.logger.warning(f"Response validation failed: {error}")
                response.content = sanitized_response or "[RESPONSE BLOCKED]"
            else:
                response.content = sanitized_response
            
            # 6. Track costs with audit
            if self.cost_tracker and response.usage:
                cost_alert = await self.cost_tracker.track_usage(
                    UsageRecord(
                        provider=provider_name,
                        model=request.model,
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens,
                        total_tokens=response.usage.total_tokens,
                        cost=response.cost or Decimal("0"),
                        timestamp=datetime.utcnow()
                    )
                )
                
                if cost_alert:
                    self.logger.warning(f"Cost alert: {cost_alert.message}")
            
            # 7. Cache response
            await self.cache.set(cache_key, response)
            
            # 8. Log successful response
            if self.security_manager.audit_logger:
                await self.security_manager.audit_logger.log_event(
                    AuditEvent(
                        event_id=str(uuid.uuid4()),
                        timestamp=datetime.utcnow(),
                        event_type=EventType.API_RESPONSE,
                        severity=EventSeverity.INFO,
                        user_id=context.user_id,
                        session_id=context.session_id,
                        request_id=request_id,
                        provider=provider_name,
                        model=request.model,
                        success=True,
                        data={
                            'tokens': response.usage.total_tokens if response.usage else 0,
                            'cost': float(response.cost) if response.cost else 0,
                            'latency_ms': response.latency_ms
                        }
                    )
                )
            
            return response
            
        except Exception as e:
            # Log error
            if self.security_manager.audit_logger:
                await self.security_manager.audit_logger.log_event(
                    AuditEvent(
                        event_id=str(uuid.uuid4()),
                        timestamp=datetime.utcnow(),
                        event_type=EventType.API_ERROR,
                        severity=EventSeverity.ERROR,
                        user_id=context.user_id,
                        session_id=context.session_id,
                        request_id=request_id,
                        success=False,
                        error_code=type(e).__name__,
                        error_message=str(e)
                    )
                )
            
            # Re-raise with context
            raise
    
    async def stream(
        self,
        request: LLMRequest,
        session_id: Optional[str] = None,
        security_context: Optional[SecurityContext] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream LLM response with security validation.
        
        Args:
            request: LLM request
            session_id: Session ID
            security_context: Security context
            
        Yields:
            Response chunks
        """
        # Get security context
        if security_context:
            context = security_context
        elif session_id and session_id in self._security_contexts:
            context = self._security_contexts[session_id]
        else:
            context = await self.create_session(
                user_id=f"stream_{uuid.uuid4().hex[:8]}",
                roles=[Role.GUEST]
            )
        
        # Check permission
        if not context.has_permission(Permission.LLM_STREAM):
            raise SecurityError("Permission denied for streaming")
        
        # Validate request
        is_valid, sanitized_prompt, error = await self.security_manager.validate_request(
            context=context,
            prompt=request.prompt,
            provider=request.provider or self.config.default_provider,
            model=request.model
        )
        
        if not is_valid:
            raise SecurityError(f"Request validation failed: {error}")
        
        request.prompt = sanitized_prompt
        
        # Stream with validation
        provider_name = request.provider or self.config.default_provider
        provider = self.providers.get(provider_name)
        
        if not provider:
            raise ValueError(f"Provider not found: {provider_name}")
        
        # Buffer for response validation
        response_buffer = []
        
        async for chunk in provider.stream(request):
            response_buffer.append(chunk)
            
            # Periodic validation (every 100 chunks)
            if len(response_buffer) % 100 == 0:
                full_response = ''.join(response_buffer)
                is_valid, _, error = await self.security_manager.validate_response(
                    context=context,
                    response=full_response,
                    provider=provider_name,
                    model=request.model
                )
                
                if not is_valid:
                    self.logger.warning(f"Stream validation failed: {error}")
                    return  # Stop streaming
            
            yield chunk
        
        # Final validation
        full_response = ''.join(response_buffer)
        await self.security_manager.validate_response(
            context=context,
            response=full_response,
            provider=provider_name,
            model=request.model
        )
    
    def _generate_secure_cache_key(
        self,
        request: LLMRequest,
        context: SecurityContext
    ) -> str:
        """Generate secure cache key including user context."""
        import hashlib
        
        # Include user context in cache key for security
        key_parts = [
            request.prompt,
            request.model,
            str(request.temperature),
            str(request.max_tokens),
            context.user_id,
            ','.join(r.value for r in context.roles)
        ]
        
        key_string = '|'.join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    async def get_security_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive security metrics.
        
        Returns:
            Security metrics dictionary
        """
        return await self.security_manager.export_security_metrics()
    
    async def check_compliance(self) -> Dict[str, bool]:
        """
        Check security compliance status.
        
        Returns:
            Compliance status dictionary
        """
        compliance = await self.security_manager.check_owasp_compliance()
        
        # Add additional compliance checks
        compliance.update({
            'gdpr_compliant': self.security_config.mask_pii_in_logs,
            'api_keys_encrypted': self.security_config.encrypt_api_keys,
            'audit_logging_enabled': self.security_config.enable_audit_logging,
            'rate_limiting_enabled': self.security_config.enable_rate_limiting,
            'session_security': self.security_config.session_timeout_minutes > 0,
        })
        
        return compliance
    
    async def export_user_data(self, user_id: str) -> Dict[str, Any]:
        """
        Export user data for GDPR compliance.
        
        Args:
            user_id: User identifier
            
        Returns:
            User data export
        """
        if not self.security_manager.audit_logger:
            return {'error': 'Audit logging not enabled'}
        
        return await self.security_manager.audit_logger.export_user_data(user_id)
    
    async def delete_user_data(self, user_id: str) -> int:
        """
        Delete user data for GDPR right to erasure.
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of records deleted
        """
        if not self.security_manager.audit_logger:
            return 0
        
        return await self.security_manager.audit_logger.delete_user_data(user_id)
    
    async def cleanup(self):
        """Cleanup resources and close connections."""
        # Cleanup sessions
        await self.security_manager.cleanup_sessions()
        
        # Cleanup old audit logs
        if self.security_manager.audit_logger:
            await self.security_manager.audit_logger.cleanup_old_events()
        
        # Close connections
        await self.connection_pool.close_all()
        
        # Close security manager
        await self.security_manager.close()
        
        self.logger.info("Secure LLM Adapter cleanup completed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()


class SecurityError(Exception):
    """Security-related error."""
    pass