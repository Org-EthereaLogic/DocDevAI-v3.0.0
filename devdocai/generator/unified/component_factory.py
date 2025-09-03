"""
Component factory for unified document generator.

This module implements the Factory pattern to create appropriate component
implementations based on the generation mode.
"""

import logging
from typing import Optional, Any
from pathlib import Path

from devdocai.generator.unified.config import (
    CacheConfig, SecurityConfig, PerformanceConfig
)
from devdocai.generator.unified.base_components import ComponentFactory

# Import existing implementations to wrap
from devdocai.generator.cache_manager import CacheManager, SemanticCache, FragmentCache
from devdocai.generator.token_optimizer import TokenOptimizer, StreamingOptimizer
from devdocai.generator.security.prompt_guard import PromptGuard
from devdocai.generator.security.rate_limiter import GenerationRateLimiter
from devdocai.generator.security.pii_protection import PIIProtectionEngine
from devdocai.generator.security.audit_logger import SecurityAuditLogger
from devdocai.generator.security.data_protection import DataProtectionManager

logger = logging.getLogger(__name__)


class UnifiedComponentFactory(ComponentFactory):
    """
    Factory for creating generation components based on configuration.
    
    This consolidates the component creation logic that was scattered
    across the three implementations.
    """
    
    def create_cache_manager(self, config: CacheConfig) -> Optional["UnifiedCacheManager"]:
        """Create cache manager based on configuration."""
        if not config.enabled:
            return None
        
        return UnifiedCacheManager(config)
    
    def create_security_manager(self, config: SecurityConfig) -> Optional["UnifiedSecurityManager"]:
        """Create security manager based on configuration."""
        if not config.enabled:
            return None
        
        return UnifiedSecurityManager(config)
    
    def create_optimizer(self, config: PerformanceConfig) -> Optional["UnifiedOptimizer"]:
        """Create optimizer based on configuration."""
        if not config.enabled:
            return None
        
        return UnifiedOptimizer(config)
    
    def create_llm_adapter(self, config: Any) -> Any:
        """Create LLM adapter - delegated to main generator."""
        # This is handled by the main generator since it needs
        # the configuration manager
        pass


class UnifiedCacheManager:
    """
    Unified cache manager that wraps existing cache implementations.
    
    Consolidates CacheManager, SemanticCache, and FragmentCache from
    the optimized implementation.
    """
    
    def __init__(self, config: CacheConfig):
        """Initialize with configuration."""
        self.config = config
        
        # Initialize cache components based on configuration
        self.semantic_cache = None
        self.fragment_cache = None
        self.main_cache = None
        
        if config.semantic_cache_size > 0:
            self.semantic_cache = SemanticCache(
                max_size=config.semantic_cache_size,
                similarity_threshold=config.similarity_threshold
            )
        
        if config.fragment_cache_size > 0:
            self.fragment_cache = FragmentCache(
                max_size=config.fragment_cache_size
            )
        
        # Main cache manager
        self.main_cache = CacheManager(
            semantic_cache_size=config.semantic_cache_size,
            fragment_cache_size=config.fragment_cache_size,
            ttl_seconds=config.ttl_seconds,
            memory_limit_mb=config.memory_limit_mb
        )
        
        self._encryption_enabled = config.encryption_enabled
        self._encryption_key = None
        
        if self._encryption_enabled:
            self._init_encryption()
    
    def _init_encryption(self):
        """Initialize encryption for secure caching."""
        from cryptography.fernet import Fernet
        self._encryption_key = Fernet.generate_key()
        self._cipher = Fernet(self._encryption_key)
    
    async def get(self, key: str) -> Optional[str]:
        """Get cached content."""
        if self.main_cache:
            content = await self.main_cache.get(key)
            
            if content and self._encryption_enabled:
                # Decrypt if encryption is enabled
                try:
                    content = self._cipher.decrypt(content.encode()).decode()
                except Exception as e:
                    logger.warning(f"Failed to decrypt cache: {e}")
                    return None
            
            return content
        return None
    
    async def set(self, key: str, value: str, ttl: Optional[int] = None):
        """Set cached content."""
        if self.main_cache:
            if self._encryption_enabled:
                # Encrypt before caching
                value = self._cipher.encrypt(value.encode()).decode()
            
            await self.main_cache.set(
                key,
                value,
                ttl=ttl or self.config.ttl_seconds
            )
    
    async def get_encrypted(self, key: str, user_id: str) -> Optional[str]:
        """Get encrypted cached content for enterprise mode."""
        # Add user ID to key for user-specific caching
        user_key = f"{user_id}:{key}"
        return await self.get(user_key)
    
    async def set_encrypted(self, key: str, value: str, user_id: str, ttl: int):
        """Set encrypted cached content for enterprise mode."""
        user_key = f"{user_id}:{key}"
        await self.set(user_key, value, ttl)
    
    async def invalidate(self, key: str):
        """Invalidate cached content."""
        if self.main_cache:
            await self.main_cache.invalidate(key)
    
    async def clear(self):
        """Clear all caches."""
        if self.main_cache:
            await self.main_cache.clear()
        if self.semantic_cache:
            self.semantic_cache.clear()
        if self.fragment_cache:
            self.fragment_cache.clear()
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        stats = {
            "enabled": self.config.enabled,
            "encryption_enabled": self._encryption_enabled
        }
        
        if self.main_cache:
            stats.update(self.main_cache.get_stats())
        
        return stats


class UnifiedSecurityManager:
    """
    Unified security manager that consolidates all security components.
    
    Combines PromptGuard, RateLimiter, PIIProtection, AuditLogger,
    and DataProtection from the secure implementation.
    """
    
    def __init__(self, config: SecurityConfig):
        """Initialize with configuration."""
        self.config = config
        
        # Initialize security components based on configuration
        self.prompt_guard = None
        self.rate_limiter = None
        self.pii_engine = None
        self.audit_logger = None
        self.data_protection = None
        
        if config.prompt_injection_detection:
            self.prompt_guard = PromptGuard(
                patterns_file=config.injection_patterns_file,
                threshold=config.threat_threshold
            )
        
        if config.rate_limiting_enabled:
            from devdocai.generator.security.rate_limiter import RateLimitConfig
            
            rate_config = RateLimitConfig(
                requests_per_minute=config.requests_per_minute,
                requests_per_hour=config.requests_per_hour,
                burst_size=config.burst_size
            )
            self.rate_limiter = GenerationRateLimiter(config=rate_config)
        
        if config.pii_detection_enabled:
            self.pii_engine = PIIProtectionEngine(
                sensitivity_level=config.pii_sensitivity_level,
                redaction_enabled=config.pii_redaction_enabled
            )
        
        if config.audit_logging_enabled:
            self.audit_logger = SecurityAuditLogger(
                log_path=config.audit_log_path or Path("audit.log"),
                encryption_enabled=config.log_encryption
            )
        
        if config.access_control_enabled:
            self.data_protection = DataProtectionManager()
        
        # Permission system for access control
        self._permissions = {}
        if config.role_based_permissions:
            self._init_rbac()
    
    def _init_rbac(self):
        """Initialize role-based access control."""
        # Default roles and permissions
        self._permissions = {
            "admin": ["*"],
            "developer": [
                "generate:readme",
                "generate:api",
                "generate:architecture",
                "generate:testing"
            ],
            "viewer": ["generate:readme"],
            "guest": []
        }
    
    async def check_rate_limit(self, user_id: str, session_id: Optional[str] = None) -> bool:
        """Check rate limit for user."""
        if not self.rate_limiter:
            return True
        
        client_id = session_id or user_id
        return await self.rate_limiter.check_limit(client_id)
    
    async def sanitize_input(self, data: dict) -> dict:
        """Sanitize input for security threats."""
        sanitized = data.copy()
        threats_detected = 0
        
        if self.prompt_guard:
            for key, value in data.items():
                if isinstance(value, str):
                    result = await self.prompt_guard.check_injection(value)
                    if result["threat_detected"]:
                        threats_detected += 1
                        sanitized[key] = result["sanitized"]
                    else:
                        sanitized[key] = value
                else:
                    sanitized[key] = value
        
        return {
            "sanitized": sanitized,
            "threats_detected": threats_detected
        }
    
    async def check_prompt_injection(self, prompt: str) -> dict:
        """Check for prompt injection."""
        if not self.prompt_guard:
            return {"threat_level": 0.0, "safe": True}
        
        result = await self.prompt_guard.analyze_threat(prompt)
        return {
            "threat_level": result.threat_level,
            "safe": result.threat_level < self.config.threat_threshold,
            "patterns_matched": result.patterns_matched
        }
    
    async def check_permission(
        self,
        user_id: str,
        action: str,
        user_permissions: list
    ) -> bool:
        """Check if user has permission for action."""
        if not self.config.access_control_enabled:
            return True
        
        # Check if any user permission allows the action
        for perm in user_permissions:
            if perm == "*" or perm == action:
                return True
            
            # Check role-based permissions
            if perm in self._permissions:
                role_perms = self._permissions[perm]
                if "*" in role_perms or action in role_perms:
                    return True
        
        return False
    
    async def check_pii(self, content: str) -> dict:
        """Check for PII in content."""
        if not self.pii_engine:
            return {"detected": False, "masked_content": content}
        
        result = await self.pii_engine.scan_and_protect(content)
        return {
            "detected": result.pii_detected,
            "masked_content": result.protected_content,
            "findings": result.findings
        }
    
    async def check_output(self, content: str) -> dict:
        """Check output for security issues."""
        safe = True
        sanitized_content = content
        
        # Check for PII
        if self.pii_engine:
            pii_result = await self.check_pii(content)
            if pii_result["detected"]:
                safe = False
                sanitized_content = pii_result["masked_content"]
        
        # Check for injection patterns in output
        if self.prompt_guard:
            injection_check = await self.check_prompt_injection(sanitized_content)
            if not injection_check["safe"]:
                safe = False
                # Remove suspicious patterns
                sanitized_content = self.prompt_guard.sanitize_output(sanitized_content)
        
        return {
            "safe": safe,
            "sanitized_content": sanitized_content
        }
    
    async def sanitize_output(self, content: str) -> str:
        """Sanitize output for streaming."""
        result = await self.check_output(content)
        return result["sanitized_content"]
    
    async def audit_log(self, event_type: str, data: dict):
        """Log security event."""
        if not self.audit_logger:
            return
        
        await self.audit_logger.log_event(
            event_type=event_type,
            user_id=data.get("user"),
            details=data
        )
    
    async def get_tenant_policies(self, tenant_id: str) -> dict:
        """Get tenant-specific policies."""
        # In a real implementation, this would fetch from database
        return {
            "max_document_size": 10000,
            "allowed_formats": ["markdown", "html", "pdf"],
            "require_approval": False
        }
    
    async def record_compliance(self, data: dict):
        """Record compliance data."""
        if self.audit_logger:
            await self.audit_logger.log_compliance(data)


class UnifiedOptimizer:
    """
    Unified optimizer that consolidates token optimization components.
    
    Combines TokenOptimizer and StreamingOptimizer from the performance
    implementation.
    """
    
    def __init__(self, config: PerformanceConfig):
        """Initialize with configuration."""
        self.config = config
        
        # Initialize optimization components
        self.token_optimizer = None
        self.streaming_optimizer = None
        
        if config.token_optimization_enabled:
            self.token_optimizer = TokenOptimizer(
                compression_level=config.compression_level,
                max_context_reuse=config.max_context_reuse
            )
        
        if config.streaming_enabled:
            self.streaming_optimizer = StreamingOptimizer(
                chunk_size=config.chunk_size,
                buffer_size=config.buffer_size
            )
        
        self._parallel_enabled = config.parallel_generation
        self._max_workers = config.max_workers
    
    def compress_context(self, context: dict) -> dict:
        """Compress context for token efficiency."""
        if not self.token_optimizer:
            return context
        
        return self.token_optimizer.compress(context)
    
    def calculate_savings(self, original: str, optimized: dict) -> int:
        """Calculate token savings."""
        if not self.token_optimizer:
            return 0
        
        original_tokens = self.token_optimizer.estimate_tokens(original)
        optimized_tokens = self.token_optimizer.estimate_tokens(str(optimized))
        
        return max(0, original_tokens - optimized_tokens)
    
    async def optimize_for_streaming(self, content: str) -> list:
        """Optimize content for streaming."""
        if not self.streaming_optimizer:
            return [content]
        
        return self.streaming_optimizer.chunk_content(content)
    
    def get_parallel_config(self) -> dict:
        """Get parallel processing configuration."""
        return {
            "enabled": self._parallel_enabled,
            "max_workers": self._max_workers,
            "batch_size": self.config.batch_size
        }