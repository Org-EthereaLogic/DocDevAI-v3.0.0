"""
M004 Document Generator - Access control and rate limiting system.

Comprehensive access control, rate limiting, and resource protection
for secure document generation operations.
"""

import logging
import threading
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import json

from ...common.logging import get_logger
from ...common.security import RateLimiter as BaseRateLimiter, AuditLogger, get_audit_logger

logger = get_logger(__name__)


class AccessLevel(Enum):
    """Access levels for operations."""
    PUBLIC = "public"
    AUTHENTICATED = "authenticated"  
    AUTHORIZED = "authorized"
    ADMIN = "admin"
    SYSTEM = "system"


class ResourceType(Enum):
    """Types of resources that can be accessed."""
    TEMPLATE = "template"
    DOCUMENT = "document"
    BATCH_OPERATION = "batch_operation"
    ADMIN_FUNCTION = "admin_function"
    SYSTEM_FUNCTION = "system_function"


@dataclass
class Permission:
    """Permission definition."""
    resource_type: ResourceType
    action: str  # read, write, execute, delete, admin
    conditions: Optional[Dict[str, Any]] = None


@dataclass
class AccessPolicy:
    """Access control policy."""
    name: str
    access_level: AccessLevel
    permissions: List[Permission]
    rate_limits: Dict[str, int]  # operation -> requests per hour
    resource_quotas: Dict[str, int]  # resource -> max count
    time_restrictions: Optional[Dict[str, Any]] = None
    ip_restrictions: Optional[List[str]] = None


@dataclass
class ClientProfile:
    """Client access profile."""
    client_id: str
    access_level: AccessLevel
    policies: List[str]
    granted_permissions: Set[str]
    rate_limits: Dict[str, int]
    quotas_used: Dict[str, int]
    last_activity: datetime
    blocked: bool = False
    blocked_until: Optional[datetime] = None
    security_score: int = 100


class EnhancedRateLimiter:
    """
    Enhanced rate limiter with multiple strategies.
    
    Features:
    - Token bucket algorithm
    - Sliding window rate limiting
    - Burst protection
    - Dynamic rate adjustment
    - Client-specific limits
    - Operation-specific limits
    """
    
    def __init__(self):
        """Initialize enhanced rate limiter."""
        self.client_buckets: Dict[str, Dict[str, Any]] = {}
        self.global_stats: Dict[str, List[Tuple[datetime, str]]] = {}
        self._lock = threading.Lock()
        
        # Rate limit configurations
        self.default_limits = {
            'template_render': 100,  # per hour
            'document_create': 50,
            'batch_operation': 10,
            'validation': 200,
            'admin_operation': 20
        }
        
        # Burst allowances
        self.burst_limits = {
            'template_render': 10,  # burst of 10 requests
            'document_create': 5,
            'batch_operation': 2,
            'validation': 20,
            'admin_operation': 2
        }
    
    def check_rate_limit(
        self, 
        client_id: str, 
        operation: str, 
        custom_limit: Optional[int] = None
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        Check if client is within rate limits for operation.
        
        Args:
            client_id: Client identifier
            operation: Operation being performed
            custom_limit: Custom rate limit override
            
        Returns:
            Tuple of (allowed, reason_if_denied, usage_stats)
        """
        with self._lock:
            now = datetime.now()
            
            # Get or create client bucket
            if client_id not in self.client_buckets:
                self.client_buckets[client_id] = {
                    'tokens': {},
                    'history': {},
                    'burst_used': {}
                }
            
            bucket = self.client_buckets[client_id]
            
            # Get rate limit for this operation
            rate_limit = custom_limit or self.default_limits.get(operation, 60)
            burst_limit = self.burst_limits.get(operation, 5)
            
            # Initialize operation tracking
            if operation not in bucket['tokens']:
                bucket['tokens'][operation] = rate_limit
                bucket['history'][operation] = []
                bucket['burst_used'][operation] = 0
            
            # Clean old history (sliding window)
            cutoff = now - timedelta(hours=1)
            bucket['history'][operation] = [
                timestamp for timestamp in bucket['history'][operation]
                if timestamp > cutoff
            ]
            
            # Check sliding window rate limit
            current_requests = len(bucket['history'][operation])
            if current_requests >= rate_limit:
                # Check if burst is available
                if bucket['burst_used'][operation] < burst_limit:
                    bucket['burst_used'][operation] += 1
                    bucket['history'][operation].append(now)
                    
                    usage_stats = self._get_usage_stats(client_id, operation, bucket)
                    return True, None, usage_stats
                else:
                    usage_stats = self._get_usage_stats(client_id, operation, bucket)
                    return False, f"Rate limit exceeded: {rate_limit} requests per hour", usage_stats
            
            # Token bucket refill (gradual)
            time_since_last = (now - bucket['history'][operation][-1]).total_seconds() if bucket['history'][operation] else 0
            tokens_to_add = min(rate_limit, bucket['tokens'][operation] + (time_since_last * rate_limit / 3600))
            bucket['tokens'][operation] = tokens_to_add
            
            # Consume token
            if bucket['tokens'][operation] >= 1:
                bucket['tokens'][operation] -= 1
                bucket['history'][operation].append(now)
                
                # Reset burst counter periodically
                if current_requests < rate_limit * 0.5:  # Reset when usage is low
                    bucket['burst_used'][operation] = max(0, bucket['burst_used'][operation] - 1)
                
                usage_stats = self._get_usage_stats(client_id, operation, bucket)
                return True, None, usage_stats
            else:
                usage_stats = self._get_usage_stats(client_id, operation, bucket)
                return False, "Token bucket exhausted", usage_stats
    
    def _get_usage_stats(self, client_id: str, operation: str, bucket: Dict[str, Any]) -> Dict[str, Any]:
        """Get usage statistics for client/operation."""
        rate_limit = self.default_limits.get(operation, 60)
        current_requests = len(bucket['history'][operation])
        
        return {
            'client_id': client_id,
            'operation': operation,
            'current_usage': current_requests,
            'rate_limit': rate_limit,
            'usage_percentage': (current_requests / rate_limit) * 100,
            'tokens_remaining': bucket['tokens'][operation],
            'burst_used': bucket['burst_used'][operation],
            'burst_available': self.burst_limits.get(operation, 5) - bucket['burst_used'][operation]
        }
    
    def get_client_usage_summary(self, client_id: str) -> Dict[str, Any]:
        """Get comprehensive usage summary for client."""
        with self._lock:
            if client_id not in self.client_buckets:
                return {'client_id': client_id, 'operations': {}}
            
            bucket = self.client_buckets[client_id]
            summary = {'client_id': client_id, 'operations': {}}
            
            for operation in bucket['history']:
                summary['operations'][operation] = self._get_usage_stats(client_id, operation, bucket)
            
            return summary


class AccessController:
    """
    Comprehensive access control system for M004.
    
    Features:
    - Role-based access control (RBAC)
    - Resource-level permissions
    - Dynamic policy enforcement
    - Client profiling and scoring
    - Adaptive rate limiting
    - Time-based restrictions
    - IP-based restrictions
    """
    
    def __init__(self):
        """Initialize access controller."""
        self.audit_logger = get_audit_logger()
        self.rate_limiter = EnhancedRateLimiter()
        self._lock = threading.Lock()
        
        # Client profiles and policies
        self.client_profiles: Dict[str, ClientProfile] = {}
        self.access_policies: Dict[str, AccessPolicy] = {}
        
        # Security tracking
        self.failed_attempts: Dict[str, List[datetime]] = {}
        self.suspicious_activities: Dict[str, List[Dict[str, Any]]] = {}
        
        self._initialize_default_policies()
        
        logger.info("AccessController initialized with comprehensive security controls")
    
    def _initialize_default_policies(self):
        """Initialize default access policies."""
        
        # Public policy - very limited access
        public_policy = AccessPolicy(
            name="public",
            access_level=AccessLevel.PUBLIC,
            permissions=[
                Permission(ResourceType.TEMPLATE, "read", {"category": "public"}),
            ],
            rate_limits={
                'template_render': 20,
                'document_create': 5,
                'validation': 50
            },
            resource_quotas={
                'documents_per_day': 10,
                'templates_per_hour': 5
            }
        )
        
        # Authenticated policy - normal user access
        authenticated_policy = AccessPolicy(
            name="authenticated",
            access_level=AccessLevel.AUTHENTICATED,
            permissions=[
                Permission(ResourceType.TEMPLATE, "read"),
                Permission(ResourceType.DOCUMENT, "read"),
                Permission(ResourceType.DOCUMENT, "write"),
            ],
            rate_limits={
                'template_render': 100,
                'document_create': 50,
                'validation': 200,
                'batch_operation': 5
            },
            resource_quotas={
                'documents_per_day': 100,
                'templates_per_hour': 20,
                'batch_size': 10
            }
        )
        
        # Authorized policy - elevated access
        authorized_policy = AccessPolicy(
            name="authorized",
            access_level=AccessLevel.AUTHORIZED,
            permissions=[
                Permission(ResourceType.TEMPLATE, "read"),
                Permission(ResourceType.TEMPLATE, "write"),
                Permission(ResourceType.DOCUMENT, "read"),
                Permission(ResourceType.DOCUMENT, "write"),
                Permission(ResourceType.BATCH_OPERATION, "execute"),
            ],
            rate_limits={
                'template_render': 500,
                'document_create': 200,
                'validation': 1000,
                'batch_operation': 20
            },
            resource_quotas={
                'documents_per_day': 1000,
                'templates_per_hour': 50,
                'batch_size': 50
            }
        )
        
        # Admin policy - administrative access
        admin_policy = AccessPolicy(
            name="admin",
            access_level=AccessLevel.ADMIN,
            permissions=[
                Permission(ResourceType.TEMPLATE, "read"),
                Permission(ResourceType.TEMPLATE, "write"),
                Permission(ResourceType.TEMPLATE, "delete"),
                Permission(ResourceType.DOCUMENT, "read"),
                Permission(ResourceType.DOCUMENT, "write"),
                Permission(ResourceType.DOCUMENT, "delete"),
                Permission(ResourceType.BATCH_OPERATION, "execute"),
                Permission(ResourceType.ADMIN_FUNCTION, "execute"),
            ],
            rate_limits={
                'template_render': 1000,
                'document_create': 500,
                'validation': 2000,
                'batch_operation': 50,
                'admin_operation': 100
            },
            resource_quotas={
                'documents_per_day': 10000,
                'templates_per_hour': 200,
                'batch_size': 200
            }
        )
        
        self.access_policies.update({
            "public": public_policy,
            "authenticated": authenticated_policy,
            "authorized": authorized_policy,
            "admin": admin_policy
        })
    
    def register_client(
        self, 
        client_id: str, 
        access_level: AccessLevel = AccessLevel.PUBLIC,
        custom_policies: Optional[List[str]] = None
    ) -> ClientProfile:
        """
        Register a new client with access controls.
        
        Args:
            client_id: Unique client identifier
            access_level: Client access level
            custom_policies: Custom policy names to apply
            
        Returns:
            Created client profile
        """
        with self._lock:
            policies = custom_policies or [access_level.value]
            
            # Calculate granted permissions
            granted_permissions = set()
            rate_limits = {}
            
            for policy_name in policies:
                policy = self.access_policies.get(policy_name)
                if policy:
                    for perm in policy.permissions:
                        perm_key = f"{perm.resource_type.value}:{perm.action}"
                        granted_permissions.add(perm_key)
                    
                    # Merge rate limits (take the maximum)
                    for op, limit in policy.rate_limits.items():
                        rate_limits[op] = max(rate_limits.get(op, 0), limit)
            
            profile = ClientProfile(
                client_id=client_id,
                access_level=access_level,
                policies=policies,
                granted_permissions=granted_permissions,
                rate_limits=rate_limits,
                quotas_used={},
                last_activity=datetime.now(),
                security_score=100
            )
            
            self.client_profiles[client_id] = profile
            
            self.audit_logger.log_event('client_registered', {
                'client_id': client_id,
                'access_level': access_level.value,
                'policies': policies,
                'permissions_count': len(granted_permissions),
                'timestamp': datetime.now().isoformat()
            })
            
            logger.info(f"Client registered: {client_id} with {access_level.value} access")
            return profile
    
    def check_access(
        self, 
        client_id: str, 
        resource_type: ResourceType, 
        action: str,
        resource_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        Check if client has access to perform action on resource.
        
        Args:
            client_id: Client identifier
            resource_type: Type of resource being accessed
            action: Action being performed
            resource_context: Additional context about the resource
            
        Returns:
            Tuple of (allowed, reason_if_denied, access_metadata)
        """
        with self._lock:
            # Get or create client profile
            profile = self.client_profiles.get(client_id)
            if not profile:
                # Auto-register as public user
                profile = self.register_client(client_id, AccessLevel.PUBLIC)
            
            # Update last activity
            profile.last_activity = datetime.now()
            
            # Check if client is blocked
            if profile.blocked:
                if profile.blocked_until and datetime.now() > profile.blocked_until:
                    profile.blocked = False
                    profile.blocked_until = None
                else:
                    return False, "Client is blocked", self._get_access_metadata(profile, "blocked")
            
            # Check permission
            permission_key = f"{resource_type.value}:{action}"
            if permission_key not in profile.granted_permissions:
                self._record_failed_attempt(client_id, "permission_denied", permission_key)
                return False, f"Permission denied for {permission_key}", self._get_access_metadata(profile, "permission_denied")
            
            # Check resource-specific conditions
            if not self._check_resource_conditions(profile, resource_type, action, resource_context):
                return False, "Resource access conditions not met", self._get_access_metadata(profile, "conditions_failed")
            
            # Check quotas
            quota_check = self._check_quotas(profile, resource_type, action)
            if not quota_check['allowed']:
                return False, quota_check['reason'], self._get_access_metadata(profile, "quota_exceeded")
            
            return True, None, self._get_access_metadata(profile, "granted")
    
    def check_rate_limit(
        self, 
        client_id: str, 
        operation: str
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        Check rate limits for client operation.
        
        Args:
            client_id: Client identifier
            operation: Operation being performed
            
        Returns:
            Tuple of (allowed, reason_if_denied, usage_stats)
        """
        profile = self.client_profiles.get(client_id)
        custom_limit = None
        
        if profile:
            custom_limit = profile.rate_limits.get(operation)
        
        allowed, reason, stats = self.rate_limiter.check_rate_limit(client_id, operation, custom_limit)
        
        if not allowed:
            self._record_failed_attempt(client_id, "rate_limit_exceeded", operation)
        
        return allowed, reason, stats
    
    def record_access(
        self, 
        client_id: str, 
        resource_type: ResourceType, 
        action: str, 
        success: bool,
        details: Optional[Dict[str, Any]] = None
    ):
        """Record access attempt for monitoring."""
        profile = self.client_profiles.get(client_id)
        if profile:
            profile.last_activity = datetime.now()
            
            # Update quota usage
            if success and resource_type == ResourceType.DOCUMENT and action == "write":
                profile.quotas_used['documents_per_day'] = profile.quotas_used.get('documents_per_day', 0) + 1
        
        self.audit_logger.log_event('resource_access', {
            'client_id': client_id,
            'resource_type': resource_type.value,
            'action': action,
            'success': success,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        })
    
    def block_client(
        self, 
        client_id: str, 
        duration_minutes: int = 60, 
        reason: str = "Security violation"
    ):
        """Block client for specified duration."""
        with self._lock:
            profile = self.client_profiles.get(client_id)
            if not profile:
                profile = self.register_client(client_id, AccessLevel.PUBLIC)
            
            profile.blocked = True
            profile.blocked_until = datetime.now() + timedelta(minutes=duration_minutes)
            profile.security_score = max(0, profile.security_score - 50)
            
            self.audit_logger.log_event('client_blocked', {
                'client_id': client_id,
                'duration_minutes': duration_minutes,
                'reason': reason,
                'security_score': profile.security_score,
                'timestamp': datetime.now().isoformat()
            })
            
            logger.warning(f"Client {client_id} blocked for {duration_minutes} minutes: {reason}")
    
    def calculate_client_risk_score(self, client_id: str) -> Dict[str, Any]:
        """Calculate comprehensive risk score for client."""
        with self._lock:
            profile = self.client_profiles.get(client_id)
            if not profile:
                return {'client_id': client_id, 'risk_score': 0, 'factors': [], 'recommendation': 'unknown'}
            
            risk_factors = []
            risk_score = 0
            
            # Check failed attempts
            if client_id in self.failed_attempts:
                recent_failures = [
                    attempt for attempt in self.failed_attempts[client_id]
                    if attempt > datetime.now() - timedelta(hours=1)
                ]
                if recent_failures:
                    risk_score += len(recent_failures) * 10
                    risk_factors.append(f"Recent failed attempts: {len(recent_failures)}")
            
            # Check suspicious activities
            if client_id in self.suspicious_activities:
                recent_suspicious = [
                    activity for activity in self.suspicious_activities[client_id]
                    if datetime.fromisoformat(activity['timestamp']) > datetime.now() - timedelta(hours=1)
                ]
                if recent_suspicious:
                    risk_score += len(recent_suspicious) * 15
                    risk_factors.append(f"Suspicious activities: {len(recent_suspicious)}")
            
            # Check quota usage
            for quota_type, used in profile.quotas_used.items():
                policy = self.access_policies.get(profile.access_level.value, {})
                limit = policy.resource_quotas.get(quota_type, 1000) if hasattr(policy, 'resource_quotas') else 1000
                
                usage_percentage = (used / limit) * 100
                if usage_percentage > 90:
                    risk_score += 20
                    risk_factors.append(f"High quota usage: {quota_type} at {usage_percentage:.1f}%")
                elif usage_percentage > 80:
                    risk_score += 10
                    risk_factors.append(f"Moderate quota usage: {quota_type} at {usage_percentage:.1f}%")
            
            # Security score factor
            if profile.security_score < 50:
                risk_score += 30
                risk_factors.append(f"Low security score: {profile.security_score}")
            elif profile.security_score < 80:
                risk_score += 15
                risk_factors.append(f"Moderate security score: {profile.security_score}")
            
            # Current block status
            if profile.blocked:
                risk_score += 50
                risk_factors.append("Currently blocked")
            
            # Determine recommendation
            if risk_score >= 80:
                recommendation = 'block'
            elif risk_score >= 50:
                recommendation = 'monitor_closely'
            elif risk_score >= 20:
                recommendation = 'monitor'
            else:
                recommendation = 'allow'
            
            return {
                'client_id': client_id,
                'risk_score': min(risk_score, 100),
                'factors': risk_factors,
                'recommendation': recommendation,
                'security_score': profile.security_score,
                'access_level': profile.access_level.value,
                'last_activity': profile.last_activity.isoformat(),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_access_summary(self, client_id: Optional[str] = None) -> Dict[str, Any]:
        """Get access control summary."""
        with self._lock:
            if client_id:
                # Single client summary
                profile = self.client_profiles.get(client_id)
                if not profile:
                    return {'error': f'Client {client_id} not found'}
                
                return {
                    'client_id': client_id,
                    'profile': {
                        'access_level': profile.access_level.value,
                        'policies': profile.policies,
                        'permissions_count': len(profile.granted_permissions),
                        'blocked': profile.blocked,
                        'security_score': profile.security_score,
                        'last_activity': profile.last_activity.isoformat()
                    },
                    'rate_limits': self.rate_limiter.get_client_usage_summary(client_id),
                    'risk_assessment': self.calculate_client_risk_score(client_id)
                }
            else:
                # System-wide summary
                now = datetime.now()
                active_clients = len([
                    client_id for client_id, profile in self.client_profiles.items()
                    if profile.last_activity > now - timedelta(hours=1)
                ])
                
                blocked_clients = len([
                    profile for profile in self.client_profiles.values()
                    if profile.blocked
                ])
                
                return {
                    'total_clients': len(self.client_profiles),
                    'active_clients': active_clients,
                    'blocked_clients': blocked_clients,
                    'policies_configured': len(self.access_policies),
                    'clients_by_access_level': {
                        level.value: len([
                            p for p in self.client_profiles.values()
                            if p.access_level == level
                        ])
                        for level in AccessLevel
                    }
                }
    
    def _check_resource_conditions(
        self, 
        profile: ClientProfile, 
        resource_type: ResourceType, 
        action: str, 
        context: Optional[Dict[str, Any]]
    ) -> bool:
        """Check resource-specific access conditions."""
        # This would implement complex condition checking
        # For now, basic implementation
        
        if resource_type == ResourceType.ADMIN_FUNCTION:
            return profile.access_level in [AccessLevel.ADMIN, AccessLevel.SYSTEM]
        
        if resource_type == ResourceType.BATCH_OPERATION and action == "execute":
            return profile.access_level in [AccessLevel.AUTHORIZED, AccessLevel.ADMIN, AccessLevel.SYSTEM]
        
        return True
    
    def _check_quotas(self, profile: ClientProfile, resource_type: ResourceType, action: str) -> Dict[str, Any]:
        """Check resource quotas."""
        if action != "write" or resource_type != ResourceType.DOCUMENT:
            return {'allowed': True}
        
        # Check daily document quota
        used_today = profile.quotas_used.get('documents_per_day', 0)
        
        # Get quota from policies
        max_daily = 0
        for policy_name in profile.policies:
            policy = self.access_policies.get(policy_name)
            if policy and hasattr(policy, 'resource_quotas'):
                quota = policy.resource_quotas.get('documents_per_day', 0)
                max_daily = max(max_daily, quota)
        
        if max_daily > 0 and used_today >= max_daily:
            return {'allowed': False, 'reason': f'Daily document quota exceeded: {used_today}/{max_daily}'}
        
        return {'allowed': True}
    
    def _record_failed_attempt(self, client_id: str, attempt_type: str, details: str):
        """Record failed access attempt."""
        if client_id not in self.failed_attempts:
            self.failed_attempts[client_id] = []
        
        self.failed_attempts[client_id].append(datetime.now())
        
        # Clean old attempts (last 24 hours)
        cutoff = datetime.now() - timedelta(hours=24)
        self.failed_attempts[client_id] = [
            attempt for attempt in self.failed_attempts[client_id]
            if attempt > cutoff
        ]
        
        # Check for suspicious pattern
        if len(self.failed_attempts[client_id]) > 10:  # 10 failures in 24 hours
            self._record_suspicious_activity(client_id, attempt_type, details)
    
    def _record_suspicious_activity(self, client_id: str, activity_type: str, details: str):
        """Record suspicious activity."""
        if client_id not in self.suspicious_activities:
            self.suspicious_activities[client_id] = []
        
        activity = {
            'type': activity_type,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        
        self.suspicious_activities[client_id].append(activity)
        
        # Auto-block for critical patterns
        if activity_type in ['permission_denied', 'rate_limit_exceeded']:
            recent_activities = [
                act for act in self.suspicious_activities[client_id]
                if datetime.fromisoformat(act['timestamp']) > datetime.now() - timedelta(minutes=15)
            ]
            
            if len(recent_activities) >= 5:  # 5 suspicious activities in 15 minutes
                self.block_client(client_id, 120, f"Suspicious activity pattern: {activity_type}")
    
    def _get_access_metadata(self, profile: ClientProfile, result: str) -> Dict[str, Any]:
        """Get access metadata for logging."""
        return {
            'client_id': profile.client_id,
            'access_level': profile.access_level.value,
            'security_score': profile.security_score,
            'blocked': profile.blocked,
            'result': result,
            'timestamp': datetime.now().isoformat()
        }