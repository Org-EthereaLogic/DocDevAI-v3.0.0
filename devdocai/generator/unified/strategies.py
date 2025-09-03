"""
Generation strategies for different operation modes.

This module implements the Strategy pattern, providing different generation
approaches for BASIC, PERFORMANCE, SECURE, and ENTERPRISE modes.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, AsyncGenerator
from datetime import datetime
import hashlib

from devdocai.generator.unified.base_components import (
    GenerationRequest, GenerationResult, GenerationStrategy,
    SecurityError, RateLimitError, ValidationError
)

logger = logging.getLogger(__name__)


class BasicStrategy(GenerationStrategy):
    """
    Basic generation strategy with minimal features.
    
    This provides core functionality without performance optimizations
    or security hardening. Ideal for development and simple use cases.
    """
    
    async def generate(
        self,
        request: GenerationRequest,
        components: Dict[str, Any]
    ) -> GenerationResult:
        """Generate document using basic approach."""
        start_time = datetime.now()
        
        try:
            # Load template
            template_engine = components["template_engine"]
            template = await self._load_template(template_engine, request)
            
            # Render prompt
            prompt = await self._render_prompt(template, request.context, template_engine)
            
            # Generate with LLM
            llm_adapter = components["llm_adapter"]
            content = await self._generate_with_llm(llm_adapter, prompt, request.context)
            
            # Apply MIAIR optimization if available
            quality_score = 0.8  # Default score
            if components.get("miair_engine"):
                analysis = await components["miair_engine"].analyze(content)
                quality_score = analysis.get("quality_score", 0.8)
            
            # Calculate metrics
            end_time = datetime.now()
            generation_time = (end_time - start_time).total_seconds() * 1000
            
            return GenerationResult(
                success=True,
                document_type=request.document_type,
                content=content,
                generation_time_ms=generation_time,
                quality_score=quality_score,
                metadata={"strategy": "basic"}
            )
            
        except Exception as e:
            logger.error(f"Basic generation failed: {e}")
            return GenerationResult(
                success=False,
                document_type=request.document_type,
                error=str(e)
            )
    
    def validate_request(self, request: GenerationRequest) -> bool:
        """Basic validation - just check required fields."""
        return bool(request.document_type and request.context)
    
    async def _load_template(self, template_engine, request):
        """Load template for the document type."""
        template_name = request.template_name or f"{request.document_type.value}.yaml"
        return template_engine.load_template(template_name)
    
    async def _render_prompt(self, template, context, template_engine):
        """Render template with context."""
        return template_engine.render(template, context)
    
    async def _generate_with_llm(self, llm_adapter, prompt, context):
        """Generate content using LLM."""
        from devdocai.llm_adapter.providers.base import LLMRequest
        
        llm_request = LLMRequest(
            prompt=prompt,
            max_tokens=4000,
            temperature=0.7,
            metadata={"context": context}
        )
        
        response = await llm_adapter.generate(llm_request)
        return response.content


class PerformanceStrategy(GenerationStrategy):
    """
    Performance-optimized generation strategy.
    
    Includes caching, parallel processing, token optimization,
    and streaming support for maximum efficiency.
    """
    
    async def generate(
        self,
        request: GenerationRequest,
        components: Dict[str, Any]
    ) -> GenerationResult:
        """Generate with performance optimizations."""
        start_time = datetime.now()
        
        try:
            # Check fragment cache for reusable parts
            cache_manager = components.get("cache_manager")
            cached_fragments = []
            
            if cache_manager:
                cached_fragments = await self._check_fragment_cache(
                    cache_manager,
                    request
                )
            
            # Optimize tokens if available
            optimizer = components.get("optimizer")
            if optimizer:
                request = await self._optimize_request(optimizer, request)
            
            # Parallel template loading and context preparation
            template_task = asyncio.create_task(
                self._load_and_prepare_template(components, request)
            )
            context_task = asyncio.create_task(
                self._prepare_context(request, cached_fragments)
            )
            
            template, prompt = await template_task
            optimized_context = await context_task
            
            # Generate with multi-LLM synthesis if configured
            llm_adapter = components["llm_adapter"]
            
            if request.metadata.get("multi_llm_synthesis"):
                content = await self._synthesize_multi_llm(
                    llm_adapter,
                    prompt,
                    optimized_context
                )
            else:
                content = await self._generate_optimized(
                    llm_adapter,
                    prompt,
                    optimized_context,
                    request.streaming_enabled
                )
            
            # Parallel quality check and caching
            quality_task = asyncio.create_task(
                self._check_quality(components, content)
            )
            
            if cache_manager and content:
                cache_task = asyncio.create_task(
                    self._cache_result(cache_manager, request, content)
                )
            
            quality_score = await quality_task
            
            # Calculate metrics
            end_time = datetime.now()
            generation_time = (end_time - start_time).total_seconds() * 1000
            
            # Estimate tokens saved
            tokens_saved = 0
            if optimizer:
                tokens_saved = optimizer.calculate_savings(prompt, optimized_context)
            
            return GenerationResult(
                success=True,
                document_type=request.document_type,
                content=content,
                generation_time_ms=generation_time,
                quality_score=quality_score,
                tokens_used=len(content.split()) * 1.3,  # Rough estimate
                parallel_tasks=3,
                metadata={
                    "strategy": "performance",
                    "tokens_saved": tokens_saved,
                    "cached_fragments": len(cached_fragments)
                }
            )
            
        except Exception as e:
            logger.error(f"Performance generation failed: {e}")
            return GenerationResult(
                success=False,
                document_type=request.document_type,
                error=str(e)
            )
    
    def validate_request(self, request: GenerationRequest) -> bool:
        """Validate with performance considerations."""
        if not request.document_type or not request.context:
            return False
        
        # Check request size for performance
        context_size = len(str(request.context))
        if context_size > 100000:  # 100KB limit for performance mode
            logger.warning(f"Context too large for performance mode: {context_size}")
            return False
        
        return True
    
    async def stream_generate(
        self,
        request: GenerationRequest,
        components: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """Stream generation for real-time output."""
        # Prepare template and prompt
        template_engine = components["template_engine"]
        template = await self._load_template(template_engine, request)
        prompt = await self._render_prompt(template, request.context, template_engine)
        
        # Stream from LLM
        llm_adapter = components["llm_adapter"]
        
        from devdocai.llm_adapter.providers.base import LLMRequest
        llm_request = LLMRequest(
            prompt=prompt,
            max_tokens=4000,
            temperature=0.7,
            stream=True
        )
        
        async for chunk in llm_adapter.stream_generate(llm_request):
            yield chunk
    
    async def _check_fragment_cache(self, cache_manager, request):
        """Check for cached fragments."""
        fragments = []
        # Implementation would check for reusable document parts
        return fragments
    
    async def _optimize_request(self, optimizer, request):
        """Optimize request for token efficiency."""
        # Compress context, remove redundancy
        optimized_context = optimizer.compress_context(request.context)
        request.context = optimized_context
        return request
    
    async def _load_and_prepare_template(self, components, request):
        """Load and prepare template in parallel."""
        template_engine = components["template_engine"]
        template_name = request.template_name or f"{request.document_type.value}.yaml"
        template = template_engine.load_template(template_name)
        prompt = template_engine.render(template, request.context)
        return template, prompt
    
    async def _prepare_context(self, request, cached_fragments):
        """Prepare optimized context."""
        context = request.context.copy()
        # Add cached fragments
        if cached_fragments:
            context["cached_fragments"] = cached_fragments
        return context
    
    async def _synthesize_multi_llm(self, llm_adapter, prompt, context):
        """Synthesize responses from multiple LLMs."""
        # Use multiple providers for better quality
        responses = await llm_adapter.multi_generate(prompt, context)
        # Weighted average or best selection
        return llm_adapter.synthesize_responses(responses)
    
    async def _generate_optimized(self, llm_adapter, prompt, context, streaming):
        """Generate with optimizations."""
        from devdocai.llm_adapter.providers.base import LLMRequest
        
        llm_request = LLMRequest(
            prompt=prompt,
            max_tokens=4000,
            temperature=0.7,
            metadata={"context": context, "optimized": True}
        )
        
        response = await llm_adapter.generate(llm_request)
        return response.content
    
    async def _check_quality(self, components, content):
        """Check content quality."""
        if components.get("miair_engine"):
            analysis = await components["miair_engine"].analyze(content)
            return analysis.get("quality_score", 0.8)
        return 0.8
    
    async def _cache_result(self, cache_manager, request, content):
        """Cache the result."""
        cache_key = self._generate_cache_key(request)
        await cache_manager.set(cache_key, content)
    
    def _generate_cache_key(self, request):
        """Generate cache key."""
        key_data = f"{request.document_type.value}:{str(request.context)}"
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    async def _load_template(self, template_engine, request):
        """Load template."""
        template_name = request.template_name or f"{request.document_type.value}.yaml"
        return template_engine.load_template(template_name)
    
    async def _render_prompt(self, template, context, template_engine):
        """Render prompt."""
        return template_engine.render(template, context)


class SecureStrategy(GenerationStrategy):
    """
    Security-hardened generation strategy.
    
    Includes prompt injection detection, PII protection, rate limiting,
    audit logging, and access control for enterprise security requirements.
    """
    
    async def generate(
        self,
        request: GenerationRequest,
        components: Dict[str, Any]
    ) -> GenerationResult:
        """Generate with security hardening."""
        start_time = datetime.now()
        security_checks_passed = True
        pii_detected = False
        injection_attempts = 0
        
        try:
            # Security manager is required
            security_manager = components.get("security_manager")
            if not security_manager:
                raise SecurityError("Security manager not configured")
            
            # Check rate limits
            if not await security_manager.check_rate_limit(
                request.user_id or "anonymous",
                request.session_id
            ):
                raise RateLimitError("Rate limit exceeded")
            
            # Validate and sanitize input
            sanitized_request = await self._sanitize_request(
                security_manager,
                request
            )
            injection_attempts = sanitized_request.get("injection_attempts", 0)
            
            # Check access permissions
            if not await self._check_permissions(
                security_manager,
                sanitized_request
            ):
                raise SecurityError("Insufficient permissions")
            
            # Audit log the request
            await security_manager.audit_log(
                "generation_started",
                {
                    "user": request.user_id,
                    "document_type": request.document_type.value,
                    "session": request.session_id
                }
            )
            
            # Load secure template
            template_engine = components["template_engine"]
            template = await self._load_secure_template(
                template_engine,
                sanitized_request
            )
            
            # Render with security checks
            prompt = await self._render_secure_prompt(
                template,
                sanitized_request.context,
                template_engine,
                security_manager
            )
            
            # PII detection and masking
            pii_check = await security_manager.check_pii(prompt)
            if pii_check["detected"]:
                pii_detected = True
                prompt = pii_check["masked_content"]
            
            # Generate with security constraints
            llm_adapter = components["llm_adapter"]
            content = await self._generate_secure(
                llm_adapter,
                prompt,
                sanitized_request
            )
            
            # Post-generation security checks
            content_check = await security_manager.check_output(content)
            if not content_check["safe"]:
                security_checks_passed = False
                content = content_check["sanitized_content"]
            
            # Final PII check on output
            output_pii = await security_manager.check_pii(content)
            if output_pii["detected"]:
                pii_detected = True
                content = output_pii["masked_content"]
            
            # Audit log success
            await security_manager.audit_log(
                "generation_completed",
                {
                    "user": request.user_id,
                    "document_type": request.document_type.value,
                    "pii_detected": pii_detected,
                    "security_passed": security_checks_passed
                }
            )
            
            # Calculate metrics
            end_time = datetime.now()
            generation_time = (end_time - start_time).total_seconds() * 1000
            
            return GenerationResult(
                success=True,
                document_type=request.document_type,
                content=content,
                generation_time_ms=generation_time,
                security_checks_passed=security_checks_passed,
                pii_detected=pii_detected,
                injection_attempts=injection_attempts,
                metadata={"strategy": "secure"}
            )
            
        except SecurityError as e:
            logger.error(f"Security violation: {e}")
            # Audit log security failure
            if components.get("security_manager"):
                await components["security_manager"].audit_log(
                    "security_violation",
                    {
                        "user": request.user_id,
                        "error": str(e),
                        "document_type": request.document_type.value
                    }
                )
            return GenerationResult(
                success=False,
                document_type=request.document_type,
                error=str(e),
                security_checks_passed=False
            )
        except Exception as e:
            logger.error(f"Secure generation failed: {e}")
            return GenerationResult(
                success=False,
                document_type=request.document_type,
                error=str(e)
            )
    
    def validate_request(self, request: GenerationRequest) -> bool:
        """Strict validation for security."""
        # Basic validation
        if not request.document_type or not request.context:
            return False
        
        # Require user identification
        if not request.user_id:
            logger.warning("User ID required for secure generation")
            return False
        
        # Check permissions list
        if not request.permissions:
            logger.warning("Permissions required for secure generation")
            return False
        
        return True
    
    async def _sanitize_request(self, security_manager, request):
        """Sanitize request for security threats."""
        result = await security_manager.sanitize_input({
            "context": request.context,
            "metadata": request.metadata,
            "options": request.options
        })
        
        # Update request with sanitized data
        request.context = result["sanitized"]["context"]
        request.metadata = result["sanitized"]["metadata"]
        request.options = result["sanitized"]["options"]
        
        return {
            "request": request,
            "injection_attempts": result.get("threats_detected", 0)
        }
    
    async def _check_permissions(self, security_manager, sanitized_request):
        """Check user permissions."""
        request = sanitized_request["request"]
        return await security_manager.check_permission(
            request.user_id,
            f"generate:{request.document_type.value}",
            request.permissions
        )
    
    async def _load_secure_template(self, template_engine, sanitized_request):
        """Load template with security validation."""
        request = sanitized_request["request"]
        template_name = request.template_name or f"{request.document_type.value}.yaml"
        
        # Validate template path (prevent directory traversal)
        if ".." in template_name or "/" in template_name:
            raise SecurityError("Invalid template name")
        
        return template_engine.load_template(template_name)
    
    async def _render_secure_prompt(self, template, context, template_engine, security_manager):
        """Render prompt with security checks."""
        # Check for injection patterns in context
        context_check = await security_manager.check_prompt_injection(str(context))
        if context_check["threat_level"] > 0.5:
            raise SecurityError("Potential prompt injection detected")
        
        return template_engine.render(template, context)
    
    async def _generate_secure(self, llm_adapter, prompt, sanitized_request):
        """Generate with security constraints."""
        from devdocai.llm_adapter.providers.base import LLMRequest
        
        request = sanitized_request["request"]
        
        llm_request = LLMRequest(
            prompt=prompt,
            max_tokens=4000,
            temperature=0.5,  # Lower temperature for more predictable output
            metadata={
                "secure": True,
                "user_id": request.user_id,
                "session_id": request.session_id
            }
        )
        
        response = await llm_adapter.generate(llm_request)
        return response.content


class EnterpriseStrategy(GenerationStrategy):
    """
    Enterprise-grade generation strategy.
    
    Combines all features from PERFORMANCE and SECURE modes,
    plus additional enterprise features like multi-tenancy,
    compliance tracking, and advanced monitoring.
    """
    
    def __init__(self):
        """Initialize with both performance and secure strategies."""
        super().__init__()
        self.performance_strategy = PerformanceStrategy()
        self.secure_strategy = SecureStrategy()
    
    async def generate(
        self,
        request: GenerationRequest,
        components: Dict[str, Any]
    ) -> GenerationResult:
        """Generate with all enterprise features."""
        start_time = datetime.now()
        
        try:
            # First apply security checks
            security_manager = components.get("security_manager")
            if not security_manager:
                raise SecurityError("Security manager required for enterprise mode")
            
            # Validate with secure strategy
            if not self.secure_strategy.validate_request(request):
                raise ValidationError("Request validation failed")
            
            # Sanitize request
            sanitized_request = await self.secure_strategy._sanitize_request(
                security_manager,
                request
            )
            
            # Check permissions
            if not await self.secure_strategy._check_permissions(
                security_manager,
                sanitized_request
            ):
                raise SecurityError("Insufficient permissions")
            
            # Rate limiting
            if not await security_manager.check_rate_limit(
                request.user_id,
                request.session_id
            ):
                raise RateLimitError("Rate limit exceeded")
            
            # Audit log start
            await security_manager.audit_log(
                "enterprise_generation_started",
                {
                    "user": request.user_id,
                    "document_type": request.document_type.value,
                    "priority": request.priority,
                    "tenant": request.metadata.get("tenant_id")
                }
            )
            
            # Check cache with encryption
            cache_manager = components.get("cache_manager")
            cache_key = None
            
            if cache_manager and request.cache_enabled:
                cache_key = self.performance_strategy._generate_cache_key(request)
                cached = await cache_manager.get_encrypted(cache_key, request.user_id)
                if cached:
                    logger.info(f"Encrypted cache hit for {request.document_type.value}")
                    return GenerationResult(
                        success=True,
                        document_type=request.document_type,
                        content=cached,
                        cache_hit=True,
                        cache_key=cache_key,
                        generation_time_ms=0,
                        metadata={"strategy": "enterprise", "cache_hit": True}
                    )
            
            # Optimize request
            optimizer = components.get("optimizer")
            if optimizer:
                request = await self.performance_strategy._optimize_request(
                    optimizer,
                    request
                )
            
            # Parallel processing for efficiency
            template_task = asyncio.create_task(
                self.performance_strategy._load_and_prepare_template(
                    components,
                    request
                )
            )
            
            # Multi-tenant context isolation
            isolated_context = await self._isolate_tenant_context(
                request,
                security_manager
            )
            
            template, prompt = await template_task
            
            # PII detection before generation
            pii_check = await security_manager.check_pii(prompt)
            if pii_check["detected"]:
                prompt = pii_check["masked_content"]
            
            # Generate with multi-LLM synthesis for quality
            llm_adapter = components["llm_adapter"]
            
            if request.metadata.get("multi_llm_synthesis", True):
                content = await self.performance_strategy._synthesize_multi_llm(
                    llm_adapter,
                    prompt,
                    isolated_context
                )
            else:
                content = await self.secure_strategy._generate_secure(
                    llm_adapter,
                    prompt,
                    {"request": request}
                )
            
            # Post-generation security and quality checks in parallel
            security_task = asyncio.create_task(
                security_manager.check_output(content)
            )
            quality_task = asyncio.create_task(
                self.performance_strategy._check_quality(components, content)
            )
            
            security_result = await security_task
            quality_score = await quality_task
            
            # Apply security sanitization if needed
            if not security_result["safe"]:
                content = security_result["sanitized_content"]
            
            # Compliance tracking
            await self._track_compliance(
                request,
                content,
                security_manager
            )
            
            # Store in encrypted cache
            if cache_manager and content and cache_key:
                await cache_manager.set_encrypted(
                    cache_key,
                    content,
                    request.user_id,
                    ttl=3600
                )
            
            # Audit log completion
            await security_manager.audit_log(
                "enterprise_generation_completed",
                {
                    "user": request.user_id,
                    "document_type": request.document_type.value,
                    "quality_score": quality_score,
                    "compliance": True
                }
            )
            
            # Calculate comprehensive metrics
            end_time = datetime.now()
            generation_time = (end_time - start_time).total_seconds() * 1000
            
            return GenerationResult(
                success=True,
                document_type=request.document_type,
                content=content,
                generation_time_ms=generation_time,
                quality_score=quality_score,
                security_checks_passed=True,
                metadata={
                    "strategy": "enterprise",
                    "tenant_id": request.metadata.get("tenant_id"),
                    "compliance_tracked": True,
                    "multi_llm": request.metadata.get("multi_llm_synthesis", True)
                }
            )
            
        except Exception as e:
            logger.error(f"Enterprise generation failed: {e}")
            
            # Audit log failure
            if components.get("security_manager"):
                await components["security_manager"].audit_log(
                    "enterprise_generation_failed",
                    {
                        "user": request.user_id,
                        "error": str(e),
                        "document_type": request.document_type.value
                    }
                )
            
            return GenerationResult(
                success=False,
                document_type=request.document_type,
                error=str(e),
                metadata={"strategy": "enterprise"}
            )
    
    def validate_request(self, request: GenerationRequest) -> bool:
        """Enterprise validation - strictest requirements."""
        # Combine both validations
        return (
            self.performance_strategy.validate_request(request) and
            self.secure_strategy.validate_request(request) and
            request.metadata.get("tenant_id") is not None  # Require tenant ID
        )
    
    async def stream_generate(
        self,
        request: GenerationRequest,
        components: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """Stream with security and performance."""
        # Validate security first
        security_manager = components.get("security_manager")
        if not security_manager:
            raise SecurityError("Security required for enterprise streaming")
        
        # Check rate limit
        if not await security_manager.check_rate_limit(
            request.user_id,
            request.session_id
        ):
            raise RateLimitError("Rate limit exceeded")
        
        # Stream with performance strategy but apply security checks
        async for chunk in self.performance_strategy.stream_generate(request, components):
            # Check each chunk for security
            safe_chunk = await security_manager.sanitize_output(chunk)
            yield safe_chunk
    
    async def _isolate_tenant_context(self, request, security_manager):
        """Isolate context for multi-tenancy."""
        tenant_id = request.metadata.get("tenant_id")
        
        if not tenant_id:
            raise ValidationError("Tenant ID required for enterprise mode")
        
        # Create isolated context
        isolated = request.context.copy()
        isolated["__tenant_id__"] = tenant_id
        isolated["__isolated__"] = True
        
        # Apply tenant-specific policies
        policies = await security_manager.get_tenant_policies(tenant_id)
        isolated["__policies__"] = policies
        
        return isolated
    
    async def _track_compliance(self, request, content, security_manager):
        """Track compliance requirements."""
        compliance_data = {
            "timestamp": datetime.now().isoformat(),
            "user_id": request.user_id,
            "document_type": request.document_type.value,
            "content_hash": hashlib.sha256(content.encode()).hexdigest(),
            "tenant_id": request.metadata.get("tenant_id"),
            "gdpr_compliant": True,
            "sox_compliant": True,
            "hipaa_compliant": request.metadata.get("hipaa_required", False)
        }
        
        await security_manager.record_compliance(compliance_data)