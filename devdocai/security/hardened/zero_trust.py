"""
Zero Trust Architecture Manager for M010 Security Module
Implements principle of least privilege, continuous verification, and micro-segmentation.
"""

import json
import hashlib
import uuid
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import threading
import logging
from collections import defaultdict
import jwt
import ipaddress
from pathlib import Path

logger = logging.getLogger(__name__)


class AccessDecision(Enum):
    """Zero trust access decisions."""
    ALLOW = "allow"
    DENY = "deny"
    CHALLENGE = "challenge"
    STEP_UP = "step_up"  # Require additional authentication


class TrustLevel(Enum):
    """Trust levels for entities."""
    UNTRUSTED = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    VERIFIED = 4


class ResourceType(Enum):
    """Types of protected resources."""
    API = "api"
    DATABASE = "database"
    FILE = "file"
    SERVICE = "service"
    NETWORK = "network"
    FUNCTION = "function"


@dataclass
class Identity:
    """Represents an identity in the zero trust model."""
    identity_id: str
    type: str  # user, service, device
    name: str
    trust_level: TrustLevel
    attributes: Dict[str, Any] = field(default_factory=dict)
    last_verified: Optional[datetime] = None
    verification_methods: List[str] = field(default_factory=list)
    risk_score: float = 0.0


@dataclass
class Resource:
    """Represents a protected resource."""
    resource_id: str
    type: ResourceType
    name: str
    sensitivity_level: int  # 1-5
    owner: str
    permissions: Dict[str, List[str]] = field(default_factory=dict)
    encryption_required: bool = False
    audit_required: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AccessContext:
    """Context for access decisions."""
    identity: Identity
    resource: Resource
    action: str
    timestamp: datetime
    location: Optional[str] = None
    device_id: Optional[str] = None
    network_zone: Optional[str] = None
    session_id: Optional[str] = None
    risk_indicators: List[str] = field(default_factory=list)


@dataclass
class MicroSegment:
    """Represents a network micro-segment."""
    segment_id: str
    name: str
    trust_level: TrustLevel
    allowed_resources: Set[str] = field(default_factory=set)
    allowed_identities: Set[str] = field(default_factory=set)
    network_policies: Dict[str, Any] = field(default_factory=dict)
    isolation_level: str = "strict"  # strict, moderate, minimal


class ZeroTrustManager:
    """
    Implements Zero Trust Architecture principles.
    
    Features:
    - Principle of Least Privilege (PoLP) enforcement
    - Continuous verification and re-authentication
    - Micro-segmentation for isolation
    - Identity and Access Management (IAM)
    - Risk-based access control
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the Zero Trust Manager."""
        self.config = config or {}
        
        # Identity and resource registries
        self._identities: Dict[str, Identity] = {}
        self._resources: Dict[str, Resource] = {}
        self._segments: Dict[str, MicroSegment] = {}
        
        # Policy engine
        self._policies: List[Dict[str, Any]] = []
        self._policy_cache: Dict[str, AccessDecision] = {}
        
        # Session management
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._session_timeout = timedelta(minutes=30)
        
        # Continuous verification
        self._verification_interval = timedelta(minutes=5)
        self._verification_challenges: Dict[str, Any] = {}
        
        # Risk scoring
        self._risk_weights = {
            'untrusted_network': 0.3,
            'unusual_location': 0.2,
            'unusual_time': 0.1,
            'failed_attempts': 0.2,
            'suspicious_behavior': 0.2
        }
        
        # Audit trail
        self._audit_log: List[Dict[str, Any]] = []
        self._max_audit_entries = 10000
        
        # Thread safety
        self._lock = threading.RLock()
        
        # JWT configuration for tokens
        self._jwt_secret = self._generate_jwt_secret()
        self._jwt_algorithm = 'HS256'
        
        # Initialize default policies
        self._load_default_policies()
        
        # Initialize micro-segments
        self._initialize_segments()
    
    def _generate_jwt_secret(self) -> str:
        """Generate a secure JWT secret."""
        return hashlib.sha256(
            f"{uuid.uuid4()}{datetime.utcnow()}".encode()
        ).hexdigest()
    
    def _load_default_policies(self):
        """Load default zero trust policies."""
        self._policies = [
            # Deny all by default
            {
                'name': 'default_deny',
                'priority': 999,
                'conditions': [{'type': 'always'}],
                'decision': AccessDecision.DENY
            },
            # Require high trust for sensitive resources
            {
                'name': 'sensitive_resource_protection',
                'priority': 10,
                'conditions': [
                    {'type': 'resource_sensitivity', 'operator': '>=', 'value': 4},
                    {'type': 'trust_level', 'operator': '<', 'value': TrustLevel.HIGH.value}
                ],
                'decision': AccessDecision.STEP_UP
            },
            # Challenge untrusted identities
            {
                'name': 'untrusted_challenge',
                'priority': 20,
                'conditions': [
                    {'type': 'trust_level', 'operator': '==', 'value': TrustLevel.UNTRUSTED.value}
                ],
                'decision': AccessDecision.CHALLENGE
            },
            # Time-based access control
            {
                'name': 'business_hours_only',
                'priority': 30,
                'conditions': [
                    {'type': 'time_range', 'start': '09:00', 'end': '18:00'},
                    {'type': 'weekday', 'days': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']}
                ],
                'decision': AccessDecision.ALLOW,
                'else_decision': AccessDecision.DENY
            },
            # Network zone restrictions
            {
                'name': 'internal_only',
                'priority': 40,
                'conditions': [
                    {'type': 'network_zone', 'value': 'internal'},
                    {'type': 'resource_type', 'value': ResourceType.DATABASE.value}
                ],
                'decision': AccessDecision.ALLOW
            }
        ]
    
    def _initialize_segments(self):
        """Initialize default micro-segments."""
        # Create default segments
        segments = [
            MicroSegment(
                segment_id='dmz',
                name='DMZ Zone',
                trust_level=TrustLevel.UNTRUSTED,
                isolation_level='strict'
            ),
            MicroSegment(
                segment_id='internal',
                name='Internal Network',
                trust_level=TrustLevel.MEDIUM,
                isolation_level='moderate'
            ),
            MicroSegment(
                segment_id='secure',
                name='Secure Zone',
                trust_level=TrustLevel.HIGH,
                isolation_level='strict'
            ),
            MicroSegment(
                segment_id='management',
                name='Management Network',
                trust_level=TrustLevel.VERIFIED,
                isolation_level='strict'
            )
        ]
        
        for segment in segments:
            self._segments[segment.segment_id] = segment
    
    def register_identity(self, identity: Identity) -> str:
        """Register a new identity in the system."""
        with self._lock:
            self._identities[identity.identity_id] = identity
            
            # Assign to appropriate segment
            segment_id = self._determine_segment(identity)
            if segment_id and segment_id in self._segments:
                self._segments[segment_id].allowed_identities.add(identity.identity_id)
            
            # Create audit entry
            self._audit_access({
                'action': 'register_identity',
                'identity_id': identity.identity_id,
                'trust_level': identity.trust_level.name
            })
            
            return identity.identity_id
    
    def register_resource(self, resource: Resource) -> str:
        """Register a protected resource."""
        with self._lock:
            self._resources[resource.resource_id] = resource
            
            # Assign to segment based on sensitivity
            segment_id = self._determine_resource_segment(resource)
            if segment_id and segment_id in self._segments:
                self._segments[segment_id].allowed_resources.add(resource.resource_id)
            
            # Create audit entry
            self._audit_access({
                'action': 'register_resource',
                'resource_id': resource.resource_id,
                'sensitivity': resource.sensitivity_level
            })
            
            return resource.resource_id
    
    def verify_access(self, context: AccessContext) -> Tuple[AccessDecision, Dict[str, Any]]:
        """
        Verify access request using zero trust principles.
        
        Returns:
            Tuple of (decision, details)
        """
        with self._lock:
            # Calculate risk score
            risk_score = self._calculate_risk_score(context)
            context.identity.risk_score = risk_score
            
            # Check cache
            cache_key = self._get_cache_key(context)
            if cache_key in self._policy_cache:
                cached_decision = self._policy_cache[cache_key]
                return cached_decision, {'cached': True, 'risk_score': risk_score}
            
            # Evaluate policies
            decision = self._evaluate_policies(context)
            
            # Perform continuous verification if needed
            if self._needs_reverification(context.identity):
                decision = AccessDecision.CHALLENGE
            
            # Check micro-segmentation
            if not self._check_segmentation(context):
                decision = AccessDecision.DENY
            
            # Cache decision
            self._policy_cache[cache_key] = decision
            
            # Audit access attempt
            self._audit_access({
                'identity': context.identity.identity_id,
                'resource': context.resource.resource_id,
                'action': context.action,
                'decision': decision.value,
                'risk_score': risk_score
            })
            
            details = {
                'risk_score': risk_score,
                'trust_level': context.identity.trust_level.value,
                'requires_mfa': decision == AccessDecision.STEP_UP,
                'session_id': context.session_id or self._create_session(context)
            }
            
            return decision, details
    
    def _calculate_risk_score(self, context: AccessContext) -> float:
        """Calculate risk score for access context."""
        risk_score = 0.0
        
        # Check network zone
        if context.network_zone == 'external':
            risk_score += self._risk_weights['untrusted_network']
        
        # Check location anomaly
        if self._is_unusual_location(context):
            risk_score += self._risk_weights['unusual_location']
        
        # Check time anomaly
        if self._is_unusual_time(context):
            risk_score += self._risk_weights['unusual_time']
        
        # Check risk indicators
        for indicator in context.risk_indicators:
            if indicator == 'failed_auth':
                risk_score += self._risk_weights['failed_attempts']
            elif indicator == 'suspicious':
                risk_score += self._risk_weights['suspicious_behavior']
        
        # Adjust based on trust level
        trust_modifier = (5 - context.identity.trust_level.value) / 5
        risk_score *= (1 + trust_modifier)
        
        return min(1.0, risk_score)
    
    def _is_unusual_location(self, context: AccessContext) -> bool:
        """Check if access is from unusual location."""
        if not context.location:
            return False
        
        # Check against identity's usual locations
        usual_locations = context.identity.attributes.get('usual_locations', [])
        return context.location not in usual_locations
    
    def _is_unusual_time(self, context: AccessContext) -> bool:
        """Check if access is at unusual time."""
        hour = context.timestamp.hour
        
        # Check if outside business hours
        if hour < 6 or hour > 22:
            return True
        
        # Check against identity's usual access patterns
        usual_hours = context.identity.attributes.get('usual_hours', range(9, 18))
        return hour not in usual_hours
    
    def _needs_reverification(self, identity: Identity) -> bool:
        """Check if identity needs reverification."""
        if not identity.last_verified:
            return True
        
        elapsed = datetime.utcnow() - identity.last_verified
        return elapsed > self._verification_interval
    
    def _check_segmentation(self, context: AccessContext) -> bool:
        """Check micro-segmentation rules."""
        # Find segments for identity and resource
        identity_segments = set()
        resource_segments = set()
        
        for segment_id, segment in self._segments.items():
            if context.identity.identity_id in segment.allowed_identities:
                identity_segments.add(segment_id)
            if context.resource.resource_id in segment.allowed_resources:
                resource_segments.add(segment_id)
        
        # Check if there's overlap (identity can access resource)
        return bool(identity_segments & resource_segments)
    
    def _evaluate_policies(self, context: AccessContext) -> AccessDecision:
        """Evaluate policies for access decision."""
        # Sort policies by priority
        sorted_policies = sorted(self._policies, key=lambda p: p['priority'])
        
        for policy in sorted_policies:
            if self._match_policy_conditions(policy, context):
                return policy['decision']
        
        # Default deny
        return AccessDecision.DENY
    
    def _match_policy_conditions(
        self, 
        policy: Dict[str, Any], 
        context: AccessContext
    ) -> bool:
        """Check if policy conditions match context."""
        for condition in policy['conditions']:
            if condition['type'] == 'always':
                return True
            
            elif condition['type'] == 'trust_level':
                op = condition['operator']
                value = condition['value']
                trust = context.identity.trust_level.value
                
                if op == '==' and trust != value:
                    return False
                elif op == '<' and trust >= value:
                    return False
                elif op == '>' and trust <= value:
                    return False
                elif op == '<=' and trust > value:
                    return False
                elif op == '>=' and trust < value:
                    return False
            
            elif condition['type'] == 'resource_sensitivity':
                op = condition['operator']
                value = condition['value']
                sensitivity = context.resource.sensitivity_level
                
                if op == '>=' and sensitivity < value:
                    return False
                elif op == '<=' and sensitivity > value:
                    return False
            
            elif condition['type'] == 'network_zone':
                if context.network_zone != condition['value']:
                    return False
            
            elif condition['type'] == 'resource_type':
                if context.resource.type.value != condition['value']:
                    return False
            
            elif condition['type'] == 'time_range':
                current_time = context.timestamp.strftime('%H:%M')
                if not (condition['start'] <= current_time <= condition['end']):
                    if 'else_decision' in policy:
                        return False
        
        return True
    
    def _get_cache_key(self, context: AccessContext) -> str:
        """Generate cache key for policy decision."""
        return hashlib.sha256(
            f"{context.identity.identity_id}:"
            f"{context.resource.resource_id}:"
            f"{context.action}:"
            f"{context.identity.trust_level.value}".encode()
        ).hexdigest()
    
    def _create_session(self, context: AccessContext) -> str:
        """Create a new session for identity."""
        session_id = str(uuid.uuid4())
        
        self._sessions[session_id] = {
            'identity_id': context.identity.identity_id,
            'created_at': datetime.utcnow(),
            'last_activity': datetime.utcnow(),
            'trust_level': context.identity.trust_level,
            'network_zone': context.network_zone,
            'device_id': context.device_id
        }
        
        return session_id
    
    def _determine_segment(self, identity: Identity) -> Optional[str]:
        """Determine appropriate segment for identity."""
        if identity.trust_level == TrustLevel.UNTRUSTED:
            return 'dmz'
        elif identity.trust_level in [TrustLevel.LOW, TrustLevel.MEDIUM]:
            return 'internal'
        elif identity.trust_level == TrustLevel.HIGH:
            return 'secure'
        elif identity.trust_level == TrustLevel.VERIFIED:
            return 'management'
        return None
    
    def _determine_resource_segment(self, resource: Resource) -> Optional[str]:
        """Determine appropriate segment for resource."""
        if resource.sensitivity_level >= 4:
            return 'secure'
        elif resource.sensitivity_level >= 2:
            return 'internal'
        else:
            return 'dmz'
    
    def challenge_identity(
        self, 
        identity_id: str, 
        challenge_type: str = 'mfa'
    ) -> Dict[str, Any]:
        """
        Issue a verification challenge to an identity.
        
        Args:
            identity_id: Identity to challenge
            challenge_type: Type of challenge (mfa, biometric, etc.)
        
        Returns:
            Challenge details
        """
        with self._lock:
            challenge_id = str(uuid.uuid4())
            challenge = {
                'challenge_id': challenge_id,
                'identity_id': identity_id,
                'type': challenge_type,
                'created_at': datetime.utcnow(),
                'expires_at': datetime.utcnow() + timedelta(minutes=5),
                'status': 'pending'
            }
            
            self._verification_challenges[challenge_id] = challenge
            
            return challenge
    
    def verify_challenge(
        self, 
        challenge_id: str, 
        response: str
    ) -> Tuple[bool, TrustLevel]:
        """
        Verify a challenge response.
        
        Returns:
            Tuple of (success, new_trust_level)
        """
        with self._lock:
            if challenge_id not in self._verification_challenges:
                return False, TrustLevel.UNTRUSTED
            
            challenge = self._verification_challenges[challenge_id]
            
            # Check expiration
            if datetime.utcnow() > challenge['expires_at']:
                challenge['status'] = 'expired'
                return False, TrustLevel.UNTRUSTED
            
            # Verify response (simplified - in production, implement proper MFA)
            if self._verify_challenge_response(challenge, response):
                challenge['status'] = 'verified'
                
                # Update identity trust level
                if challenge['identity_id'] in self._identities:
                    identity = self._identities[challenge['identity_id']]
                    identity.last_verified = datetime.utcnow()
                    
                    # Increase trust level
                    if identity.trust_level.value < TrustLevel.VERIFIED.value:
                        identity.trust_level = TrustLevel(identity.trust_level.value + 1)
                    
                    return True, identity.trust_level
            
            challenge['status'] = 'failed'
            return False, TrustLevel.UNTRUSTED
    
    def _verify_challenge_response(
        self, 
        challenge: Dict[str, Any], 
        response: str
    ) -> bool:
        """Verify challenge response (simplified)."""
        # In production, implement proper verification
        # This is a placeholder
        return len(response) == 6 and response.isdigit()
    
    def create_access_token(
        self, 
        identity: Identity, 
        resource: Resource, 
        permissions: List[str]
    ) -> str:
        """
        Create a JWT access token with least privilege.
        
        Returns:
            JWT token string
        """
        payload = {
            'sub': identity.identity_id,
            'resource': resource.resource_id,
            'permissions': permissions,
            'trust_level': identity.trust_level.value,
            'exp': datetime.utcnow() + timedelta(minutes=15),
            'iat': datetime.utcnow(),
            'jti': str(uuid.uuid4())
        }
        
        token = jwt.encode(payload, self._jwt_secret, algorithm=self._jwt_algorithm)
        return token
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode access token."""
        try:
            payload = jwt.decode(
                token, 
                self._jwt_secret, 
                algorithms=[self._jwt_algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
        return None
    
    def enforce_least_privilege(
        self, 
        identity_id: str, 
        resource_id: str
    ) -> List[str]:
        """
        Get minimum required permissions for identity on resource.
        
        Returns:
            List of allowed permissions
        """
        with self._lock:
            if identity_id not in self._identities:
                return []
            if resource_id not in self._resources:
                return []
            
            identity = self._identities[identity_id]
            resource = self._resources[resource_id]
            
            # Get base permissions for identity type
            base_permissions = resource.permissions.get(identity.type, [])
            
            # Filter based on trust level
            if identity.trust_level == TrustLevel.UNTRUSTED:
                return []
            elif identity.trust_level == TrustLevel.LOW:
                return [p for p in base_permissions if p in ['read']]
            elif identity.trust_level == TrustLevel.MEDIUM:
                return [p for p in base_permissions if p in ['read', 'write']]
            else:
                return base_permissions
    
    def _audit_access(self, event: Dict[str, Any]):
        """Add entry to audit log."""
        event['timestamp'] = datetime.utcnow().isoformat()
        event['audit_id'] = str(uuid.uuid4())
        
        self._audit_log.append(event)
        
        # Trim log if needed
        if len(self._audit_log) > self._max_audit_entries:
            self._audit_log = self._audit_log[-self._max_audit_entries:]
    
    def get_audit_trail(
        self, 
        identity_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get audit trail for identity or resource."""
        with self._lock:
            filtered_log = self._audit_log
            
            if identity_id:
                filtered_log = [
                    e for e in filtered_log 
                    if e.get('identity') == identity_id or e.get('identity_id') == identity_id
                ]
            
            if resource_id:
                filtered_log = [
                    e for e in filtered_log 
                    if e.get('resource') == resource_id or e.get('resource_id') == resource_id
                ]
            
            return filtered_log[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get zero trust statistics."""
        with self._lock:
            return {
                'total_identities': len(self._identities),
                'total_resources': len(self._resources),
                'total_segments': len(self._segments),
                'active_sessions': len(self._sessions),
                'pending_challenges': sum(
                    1 for c in self._verification_challenges.values() 
                    if c['status'] == 'pending'
                ),
                'audit_entries': len(self._audit_log),
                'cache_size': len(self._policy_cache),
                'trust_distribution': self._get_trust_distribution()
            }
    
    def _get_trust_distribution(self) -> Dict[str, int]:
        """Get distribution of trust levels."""
        distribution = defaultdict(int)
        for identity in self._identities.values():
            distribution[identity.trust_level.name] += 1
        return dict(distribution)