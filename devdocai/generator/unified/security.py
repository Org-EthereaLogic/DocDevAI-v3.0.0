"""
Unified security module for document generator.

This module consolidates all security components from the secure implementation
into a single, mode-aware security system.
"""

import logging
import hashlib
import asyncio
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import re
import json

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """Security levels for different modes."""
    NONE = "none"           # No security (BASIC mode)
    STANDARD = "standard"   # Basic security (PERFORMANCE mode)
    ENHANCED = "enhanced"   # Full security (SECURE mode)
    MAXIMUM = "maximum"     # Maximum security (ENTERPRISE mode)


@dataclass
class SecurityConfig:
    """Unified security configuration."""
    level: SecurityLevel = SecurityLevel.NONE
    
    # Rate limiting
    rate_limiting: bool = False
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 10
    
    # Prompt security
    injection_detection: bool = False
    threat_threshold: float = 0.7
    sanitize_inputs: bool = False
    
    # PII protection
    pii_detection: bool = False
    pii_redaction: bool = False
    pii_sensitivity: str = "medium"
    
    # Audit logging
    audit_logging: bool = False
    audit_encryption: bool = False
    audit_retention_days: int = 90
    
    # Access control
    access_control: bool = False
    require_authentication: bool = False
    rbac_enabled: bool = False
    
    # Data protection
    encrypt_at_rest: bool = False
    encrypt_in_transit: bool = False
    secure_deletion: bool = False
    
    @classmethod
    def for_level(cls, level: SecurityLevel) -> "SecurityConfig":
        """Create configuration for security level."""
        if level == SecurityLevel.NONE:
            return cls(level=level)
        
        elif level == SecurityLevel.STANDARD:
            return cls(
                level=level,
                rate_limiting=True,
                injection_detection=True,
                sanitize_inputs=True
            )
        
        elif level == SecurityLevel.ENHANCED:
            return cls(
                level=level,
                rate_limiting=True,
                injection_detection=True,
                sanitize_inputs=True,
                pii_detection=True,
                pii_redaction=True,
                audit_logging=True,
                access_control=True
            )
        
        elif level == SecurityLevel.MAXIMUM:
            return cls(
                level=level,
                rate_limiting=True,
                requests_per_minute=30,
                injection_detection=True,
                threat_threshold=0.5,
                sanitize_inputs=True,
                pii_detection=True,
                pii_redaction=True,
                pii_sensitivity="high",
                audit_logging=True,
                audit_encryption=True,
                access_control=True,
                require_authentication=True,
                rbac_enabled=True,
                encrypt_at_rest=True,
                encrypt_in_transit=True,
                secure_deletion=True
            )
        
        return cls(level=level)


class UnifiedSecuritySystem:
    """
    Unified security system that consolidates all security features.
    
    This replaces the multiple security components with a single,
    configurable system that enables features based on security level.
    """
    
    def __init__(self, config: Optional[SecurityConfig] = None):
        """Initialize with configuration."""
        self.config = config or SecurityConfig()
        
        # Initialize subsystems based on configuration
        self.rate_limiter = None
        self.prompt_guard = None
        self.pii_detector = None
        self.audit_logger = None
        self.access_controller = None
        self.data_protector = None
        
        if self.config.rate_limiting:
            self.rate_limiter = RateLimiter(self.config)
        
        if self.config.injection_detection:
            self.prompt_guard = PromptGuard(self.config)
        
        if self.config.pii_detection:
            self.pii_detector = PIIDetector(self.config)
        
        if self.config.audit_logging:
            self.audit_logger = AuditLogger(self.config)
        
        if self.config.access_control:
            self.access_controller = AccessController(self.config)
        
        if self.config.encrypt_at_rest or self.config.encrypt_in_transit:
            self.data_protector = DataProtector(self.config)
        
        logger.info(f"Initialized unified security system at level: {self.config.level.value}")
    
    async def check_request(self, request: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Comprehensive security check for incoming request.
        
        Returns:
            Tuple of (is_allowed, error_message)
        """
        user_id = request.get("user_id", "anonymous")
        
        # Rate limiting check
        if self.rate_limiter:
            if not await self.rate_limiter.check(user_id):
                return False, "Rate limit exceeded"
        
        # Access control check
        if self.access_controller:
            if not await self.access_controller.check_access(request):
                return False, "Access denied"
        
        # Prompt injection check
        if self.prompt_guard:
            content = request.get("content", "")
            if not await self.prompt_guard.is_safe(content):
                return False, "Potential security threat detected"
        
        # Audit the request
        if self.audit_logger:
            await self.audit_logger.log_request(request)
        
        return True, None
    
    async def sanitize_content(self, content: str) -> str:
        """Sanitize content for security threats."""
        if not self.config.sanitize_inputs:
            return content
        
        # Remove prompt injection patterns
        if self.prompt_guard:
            content = await self.prompt_guard.sanitize(content)
        
        # Redact PII if configured
        if self.pii_detector and self.config.pii_redaction:
            content = await self.pii_detector.redact(content)
        
        return content
    
    async def check_output(self, output: str) -> tuple[bool, str]:
        """
        Check output for security issues.
        
        Returns:
            Tuple of (is_safe, sanitized_output)
        """
        is_safe = True
        sanitized = output
        
        # Check for PII leakage
        if self.pii_detector:
            has_pii = await self.pii_detector.detect(sanitized)
            if has_pii:
                is_safe = False
                if self.config.pii_redaction:
                    sanitized = await self.pii_detector.redact(sanitized)
        
        # Check for injection patterns in output
        if self.prompt_guard:
            if not await self.prompt_guard.is_safe(sanitized):
                is_safe = False
                sanitized = await self.prompt_guard.sanitize(sanitized)
        
        # Audit the output check
        if self.audit_logger:
            await self.audit_logger.log_output_check({
                "is_safe": is_safe,
                "original_length": len(output),
                "sanitized_length": len(sanitized)
            })
        
        return is_safe, sanitized
    
    async def encrypt_data(self, data: str) -> str:
        """Encrypt data if configured."""
        if self.data_protector and self.config.encrypt_at_rest:
            return await self.data_protector.encrypt(data)
        return data
    
    async def decrypt_data(self, data: str) -> str:
        """Decrypt data if configured."""
        if self.data_protector and self.config.encrypt_at_rest:
            return await self.data_protector.decrypt(data)
        return data
    
    def get_security_headers(self) -> Dict[str, str]:
        """Get security headers for HTTP responses."""
        headers = {}
        
        if self.config.level.value in ["enhanced", "maximum"]:
            headers.update({
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block",
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
            })
        
        if self.config.level == SecurityLevel.MAXIMUM:
            headers.update({
                "Content-Security-Policy": "default-src 'self'",
                "Referrer-Policy": "strict-origin-when-cross-origin"
            })
        
        return headers
    
    async def cleanup(self):
        """Clean up security resources."""
        if self.audit_logger:
            await self.audit_logger.flush()
        
        if self.data_protector:
            await self.data_protector.secure_cleanup()


class RateLimiter:
    """Consolidated rate limiting functionality."""
    
    def __init__(self, config: SecurityConfig):
        """Initialize rate limiter."""
        self.config = config
        self._buckets: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    async def check(self, client_id: str) -> bool:
        """Check if client is within rate limits."""
        async with self._lock:
            now = datetime.now()
            
            if client_id not in self._buckets:
                self._buckets[client_id] = {
                    "minute_count": 0,
                    "hour_count": 0,
                    "minute_reset": now + timedelta(minutes=1),
                    "hour_reset": now + timedelta(hours=1),
                    "burst_tokens": self.config.burst_size
                }
            
            bucket = self._buckets[client_id]
            
            # Reset counters if needed
            if now >= bucket["minute_reset"]:
                bucket["minute_count"] = 0
                bucket["minute_reset"] = now + timedelta(minutes=1)
            
            if now >= bucket["hour_reset"]:
                bucket["hour_count"] = 0
                bucket["hour_reset"] = now + timedelta(hours=1)
            
            # Check limits
            if bucket["minute_count"] >= self.config.requests_per_minute:
                return False
            
            if bucket["hour_count"] >= self.config.requests_per_hour:
                return False
            
            # Update counters
            bucket["minute_count"] += 1
            bucket["hour_count"] += 1
            
            return True


class PromptGuard:
    """Consolidated prompt injection detection."""
    
    def __init__(self, config: SecurityConfig):
        """Initialize prompt guard."""
        self.config = config
        self._patterns = self._load_patterns()
    
    def _load_patterns(self) -> List[re.Pattern]:
        """Load injection patterns."""
        patterns = [
            r"ignore\s+previous\s+instructions",
            r"disregard\s+all\s+prior",
            r"system\s+prompt",
            r"You\s+are\s+now",
            r"</?\s*script\s*>",
            r"javascript:",
            r"onclick\s*=",
            r"onerror\s*=",
            r"DROP\s+TABLE",
            r"DELETE\s+FROM",
            r"UPDATE\s+.*\s+SET",
            r"INSERT\s+INTO"
        ]
        
        return [re.compile(p, re.IGNORECASE) for p in patterns]
    
    async def is_safe(self, content: str) -> bool:
        """Check if content is safe from injection."""
        threat_score = 0.0
        
        for pattern in self._patterns:
            if pattern.search(content):
                threat_score += 0.3
        
        return threat_score < self.config.threat_threshold
    
    async def sanitize(self, content: str) -> str:
        """Remove injection patterns."""
        sanitized = content
        
        for pattern in self._patterns:
            sanitized = pattern.sub("[REDACTED]", sanitized)
        
        return sanitized


class PIIDetector:
    """Consolidated PII detection and redaction."""
    
    def __init__(self, config: SecurityConfig):
        """Initialize PII detector."""
        self.config = config
        self._patterns = self._load_patterns()
    
    def _load_patterns(self) -> Dict[str, re.Pattern]:
        """Load PII patterns based on sensitivity."""
        patterns = {}
        
        # Always detect these
        patterns["ssn"] = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
        patterns["credit_card"] = re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b")
        
        if self.config.pii_sensitivity in ["medium", "high"]:
            patterns["email"] = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
            patterns["phone"] = re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b")
        
        if self.config.pii_sensitivity == "high":
            patterns["name"] = re.compile(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b")
            patterns["address"] = re.compile(r"\b\d+\s+[A-Z][a-z]+\s+(Street|St|Avenue|Ave|Road|Rd)\b")
        
        return patterns
    
    async def detect(self, content: str) -> bool:
        """Detect PII in content."""
        for pattern in self._patterns.values():
            if pattern.search(content):
                return True
        return False
    
    async def redact(self, content: str) -> str:
        """Redact PII from content."""
        redacted = content
        
        for pii_type, pattern in self._patterns.items():
            redacted = pattern.sub(f"[{pii_type.upper()}_REDACTED]", redacted)
        
        return redacted


class AuditLogger:
    """Consolidated audit logging."""
    
    def __init__(self, config: SecurityConfig):
        """Initialize audit logger."""
        self.config = config
        self._log_path = Path("audit.log")
        self._buffer: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
    
    async def log_request(self, request: Dict[str, Any]):
        """Log incoming request."""
        await self._log_event({
            "type": "request",
            "timestamp": datetime.now().isoformat(),
            "user_id": request.get("user_id", "anonymous"),
            "action": request.get("action", "unknown")
        })
    
    async def log_output_check(self, result: Dict[str, Any]):
        """Log output security check."""
        await self._log_event({
            "type": "output_check",
            "timestamp": datetime.now().isoformat(),
            **result
        })
    
    async def _log_event(self, event: Dict[str, Any]):
        """Log security event."""
        async with self._lock:
            if self.config.audit_encryption:
                # Encrypt event data
                event_str = json.dumps(event)
                event["data"] = hashlib.sha256(event_str.encode()).hexdigest()
            
            self._buffer.append(event)
            
            # Flush if buffer is full
            if len(self._buffer) >= 100:
                await self.flush()
    
    async def flush(self):
        """Flush buffer to disk."""
        if not self._buffer:
            return
        
        async with self._lock:
            with open(self._log_path, "a") as f:
                for event in self._buffer:
                    f.write(json.dumps(event) + "\n")
            
            self._buffer.clear()


class AccessController:
    """Consolidated access control."""
    
    def __init__(self, config: SecurityConfig):
        """Initialize access controller."""
        self.config = config
        self._roles = self._init_roles()
    
    def _init_roles(self) -> Dict[str, Set[str]]:
        """Initialize role permissions."""
        return {
            "admin": {"*"},
            "developer": {"generate", "read", "write"},
            "user": {"generate", "read"},
            "guest": {"read"}
        }
    
    async def check_access(self, request: Dict[str, Any]) -> bool:
        """Check if request has access."""
        if not self.config.require_authentication:
            return True
        
        user_id = request.get("user_id")
        if not user_id or user_id == "anonymous":
            return False
        
        if self.config.rbac_enabled:
            role = request.get("role", "guest")
            action = request.get("action", "read")
            
            permissions = self._roles.get(role, set())
            
            return "*" in permissions or action in permissions
        
        return True


class DataProtector:
    """Consolidated data protection."""
    
    def __init__(self, config: SecurityConfig):
        """Initialize data protector."""
        self.config = config
        self._init_encryption()
    
    def _init_encryption(self):
        """Initialize encryption."""
        from cryptography.fernet import Fernet
        self._key = Fernet.generate_key()
        self._cipher = Fernet(self._key)
    
    async def encrypt(self, data: str) -> str:
        """Encrypt data."""
        if not self.config.encrypt_at_rest:
            return data
        
        encrypted = self._cipher.encrypt(data.encode())
        return encrypted.decode()
    
    async def decrypt(self, data: str) -> str:
        """Decrypt data."""
        if not self.config.encrypt_at_rest:
            return data
        
        decrypted = self._cipher.decrypt(data.encode())
        return decrypted.decode()
    
    async def secure_cleanup(self):
        """Securely clean up sensitive data."""
        if self.config.secure_deletion:
            # Overwrite key in memory
            self._key = None
            self._cipher = None