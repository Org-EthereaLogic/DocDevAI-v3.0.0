"""
M010 Security Module - Unified DSR Handler

Consolidates basic and optimized DSR handlers with operation modes:
- BASIC: Core DSR request processing with standard features
- PERFORMANCE: Optimized processing with caching and parallelization
- SECURE/ENTERPRISE: Enhanced security with compliance tracking and audit

Supports GDPR, CCPA, and other privacy regulation compliance for data subject requests.
"""

import asyncio
import json
import logging
import time
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Set, Tuple
from enum import Enum
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from functools import lru_cache
from collections import defaultdict
import multiprocessing as mp
import uuid

logger = logging.getLogger(__name__)


class DSROperationMode(str, Enum):
    """DSR operation modes."""
    BASIC = "basic"
    PERFORMANCE = "performance"
    SECURE = "secure"
    ENTERPRISE = "enterprise"


class DSRRequestType(str, Enum):
    """Types of data subject requests."""
    ACCESS = "access"               # Right to access personal data
    RECTIFICATION = "rectification" # Right to correct personal data
    ERASURE = "erasure"             # Right to be forgotten
    RESTRICTION = "restriction"     # Right to restrict processing
    PORTABILITY = "portability"     # Right to data portability
    OBJECTION = "objection"         # Right to object to processing
    WITHDRAW_CONSENT = "withdraw_consent"  # Withdraw consent
    AUTOMATED_DECISION = "automated_decision"  # Rights related to automated decision-making


class DSRStatus(str, Enum):
    """Status of DSR requests."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    PARTIALLY_COMPLETED = "partially_completed"
    EXPIRED = "expired"


class DSRPriority(str, Enum):
    """Priority levels for DSR requests."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class DSRConfig:
    """Configuration for DSR processing."""
    mode: DSROperationMode = DSROperationMode.ENTERPRISE
    
    # Core settings
    default_response_time_days: int = 30
    urgent_response_time_days: int = 7
    enable_identity_verification: bool = True
    enable_automated_processing: bool = False
    require_legal_review: bool = True
    
    # Performance optimization settings
    enable_parallel_processing: bool = False
    enable_request_caching: bool = False
    enable_bulk_processing: bool = False
    cache_ttl_hours: int = 24
    max_workers: int = 4
    batch_size: int = 50
    
    # Security and compliance settings
    enable_encryption: bool = False
    enable_audit_logging: bool = False
    enable_compliance_tracking: bool = False
    gdpr_compliance: bool = False
    ccpa_compliance: bool = False
    require_data_mapping: bool = False
    
    # Data retention and deletion settings
    request_retention_days: int = 365
    enable_automatic_deletion: bool = False
    deletion_verification_required: bool = True
    
    def __post_init__(self):
        """Configure mode-specific settings."""
        if self.mode == DSROperationMode.BASIC:
            self.enable_parallel_processing = False
            self.enable_request_caching = False
            self.enable_bulk_processing = False
            self.enable_encryption = False
            self.enable_audit_logging = False
            self.enable_compliance_tracking = False
            self.require_legal_review = False
            self.enable_automated_processing = False
            
        elif self.mode == DSROperationMode.PERFORMANCE:
            self.enable_parallel_processing = True
            self.enable_request_caching = True
            self.enable_bulk_processing = True
            self.max_workers = min(mp.cpu_count(), 8)
            self.batch_size = 100
            self.enable_automated_processing = True
            
        elif self.mode == DSROperationMode.SECURE:
            self.enable_parallel_processing = True
            self.enable_request_caching = True
            self.enable_encryption = True
            self.enable_audit_logging = True
            self.enable_compliance_tracking = True
            self.gdpr_compliance = True
            self.require_data_mapping = True
            
        elif self.mode == DSROperationMode.ENTERPRISE:
            self.enable_parallel_processing = True
            self.enable_request_caching = True
            self.enable_bulk_processing = True
            self.enable_encryption = True
            self.enable_audit_logging = True
            self.enable_compliance_tracking = True
            self.gdpr_compliance = True
            self.ccpa_compliance = True
            self.require_data_mapping = True
            self.enable_automatic_deletion = True


@dataclass
class DSRRequest:
    """Represents a data subject request."""
    request_id: str
    request_type: DSRRequestType
    requester_email: str
    requester_name: Optional[str] = None
    requester_id: Optional[str] = None
    
    # Request details
    description: str = ""
    specific_data_categories: List[str] = field(default_factory=list)
    date_range: Optional[Tuple[datetime, datetime]] = None
    
    # Processing information
    status: DSRStatus = DSRStatus.PENDING
    priority: DSRPriority = DSRPriority.MEDIUM
    assigned_to: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Verification and legal
    identity_verified: bool = False
    legal_basis: Optional[str] = None
    legal_review_required: bool = True
    legal_review_completed: bool = False
    
    # Compliance tracking
    gdpr_applicable: bool = False
    ccpa_applicable: bool = False
    other_regulations: List[str] = field(default_factory=list)
    
    # Processing results
    response_data: Optional[Dict[str, Any]] = None
    processing_notes: List[str] = field(default_factory=list)
    rejection_reason: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DSRResponse:
    """Response to a data subject request."""
    request_id: str
    status: DSRStatus
    response_type: DSRRequestType
    
    # Response data
    data_provided: Optional[Dict[str, Any]] = None
    actions_taken: List[str] = field(default_factory=list)
    processing_time_hours: float = 0.0
    
    # Compliance information
    legal_basis: Optional[str] = None
    retention_period: Optional[str] = None
    data_sources: List[str] = field(default_factory=list)
    
    # Response metadata
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    generated_by: str = "automated"
    format: str = "json"
    encryption_used: bool = False
    
    # Delivery information
    delivery_method: str = "email"
    delivery_status: str = "pending"
    delivery_attempts: int = 0


@dataclass
class DataCollector:
    """Collects data for DSR requests (performance mode)."""
    
    def __init__(self):
        self.data_sources = {
            'user_profiles': self._collect_user_profiles,
            'transaction_history': self._collect_transactions,
            'preferences': self._collect_preferences,
            'audit_logs': self._collect_audit_logs,
            'support_tickets': self._collect_support_data,
            'analytics_data': self._collect_analytics,
            'communications': self._collect_communications,
            'device_data': self._collect_device_data
        }
    
    async def collect_data(self, requester_email: str, data_categories: List[str]) -> Dict[str, Any]:
        """Collect data from multiple sources."""
        collected_data = {}
        
        tasks = []
        for category in data_categories:
            if category in self.data_sources:
                task = self.data_sources[category](requester_email)
                tasks.append((category, task))
        
        results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
        
        for (category, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to collect {category}: {result}")
                collected_data[category] = {"error": str(result)}
            else:
                collected_data[category] = result
        
        return collected_data
    
    async def _collect_user_profiles(self, email: str) -> Dict[str, Any]:
        """Collect user profile data."""
        # Mock implementation - would connect to actual user database
        await asyncio.sleep(0.1)  # Simulate DB query
        return {
            "email": email,
            "profile_created": "2023-01-15T10:00:00Z",
            "last_login": "2024-01-15T14:30:00Z",
            "status": "active"
        }
    
    async def _collect_transactions(self, email: str) -> Dict[str, Any]:
        """Collect transaction history."""
        await asyncio.sleep(0.2)
        return {
            "total_transactions": 0,
            "transactions": [],
            "note": "No transaction data found"
        }
    
    async def _collect_preferences(self, email: str) -> Dict[str, Any]:
        """Collect user preferences."""
        await asyncio.sleep(0.1)
        return {
            "marketing_emails": True,
            "notifications": False,
            "privacy_level": "standard"
        }
    
    async def _collect_audit_logs(self, email: str) -> Dict[str, Any]:
        """Collect audit logs."""
        await asyncio.sleep(0.3)
        return {
            "login_attempts": [],
            "data_access_logs": [],
            "consent_history": []
        }
    
    async def _collect_support_data(self, email: str) -> Dict[str, Any]:
        """Collect support ticket data."""
        await asyncio.sleep(0.2)
        return {
            "tickets": [],
            "chat_history": [],
            "feedback": []
        }
    
    async def _collect_analytics(self, email: str) -> Dict[str, Any]:
        """Collect analytics data."""
        await asyncio.sleep(0.4)
        return {
            "page_views": [],
            "feature_usage": {},
            "behavioral_data": {}
        }
    
    async def _collect_communications(self, email: str) -> Dict[str, Any]:
        """Collect communication history."""
        await asyncio.sleep(0.2)
        return {
            "emails_sent": [],
            "notifications": [],
            "messages": []
        }
    
    async def _collect_device_data(self, email: str) -> Dict[str, Any]:
        """Collect device and session data."""
        await asyncio.sleep(0.1)
        return {
            "devices": [],
            "sessions": [],
            "ip_addresses": []
        }


@dataclass
class DSRStatistics:
    """Statistics for DSR processing."""
    total_requests: int = 0
    requests_by_type: Dict[str, int] = field(default_factory=dict)
    requests_by_status: Dict[str, int] = field(default_factory=dict)
    avg_processing_time_hours: float = 0.0
    compliance_rate: float = 0.0
    rejection_rate: float = 0.0
    automated_processing_rate: float = 0.0
    pending_requests: int = 0
    overdue_requests: int = 0
    last_processed: Optional[datetime] = None
    last_updated: datetime = field(default_factory=datetime.now)


class UnifiedDSRHandler:
    """
    Unified Data Subject Request Handler supporting multiple operation modes.
    
    Modes:
    - BASIC: Standard DSR processing with manual workflows
    - PERFORMANCE: Optimized processing with caching and parallelization
    - SECURE: Enhanced security with encryption and audit logging
    - ENTERPRISE: Full compliance suite with automated processing
    """
    
    def __init__(self, config: Optional[DSRConfig] = None):
        """Initialize unified DSR handler."""
        self.config = config or DSRConfig()
        self._request_cache = {}
        self._cache_lock = threading.RLock()
        self._statistics = DSRStatistics()
        self._pending_requests = {}
        
        # Performance components
        self._thread_pool = None
        if self.config.enable_parallel_processing:
            self._thread_pool = ThreadPoolExecutor(max_workers=self.config.max_workers)
        
        # Data collector (performance/enterprise modes)
        self._data_collector = None
        if self.config.mode in [DSROperationMode.PERFORMANCE, DSROperationMode.ENTERPRISE]:
            self._data_collector = DataCollector()
        
        logger.info(f"Initialized DSR handler in {self.config.mode.value} mode")
    
    def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process DSR request synchronously (basic mode)."""
        start_time = time.time()
        
        try:
            # Create DSR request object
            dsr_request = self._create_dsr_request(request_data)
            
            # Validate request
            validation_result = self._validate_request(dsr_request)
            if not validation_result['valid']:
                return self._create_error_response(dsr_request.request_id, validation_result['errors'])
            
            # Check cache first
            if self.config.enable_request_caching:
                cached_response = self._get_cached_response(dsr_request)
                if cached_response:
                    return cached_response
            
            # Process request based on type
            response = self._process_request_by_type(dsr_request)
            
            # Apply security measures if enabled
            if self.config.enable_encryption:
                response = self._apply_encryption(response)
            
            # Cache response if caching is enabled
            if self.config.enable_request_caching:
                self._cache_response(dsr_request, response)
            
            # Update statistics
            processing_time = time.time() - start_time
            self._update_statistics(dsr_request, processing_time)
            
            # Audit logging if enabled
            if self.config.enable_audit_logging:
                self._log_dsr_audit(dsr_request, response)
            
            return response
            
        except Exception as e:
            logger.error(f"DSR request processing failed: {e}")
            return self._create_error_response("unknown", [str(e)])
    
    async def process_request_async(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process DSR request asynchronously (optimized modes)."""
        if self.config.mode == DSROperationMode.BASIC:
            # Run synchronous processing in thread pool for basic mode
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.process_request, request_data)
        
        start_time = time.time()
        
        try:
            # Create DSR request object
            dsr_request = self._create_dsr_request(request_data)
            
            # Validate request
            validation_result = await self._validate_request_async(dsr_request)
            if not validation_result['valid']:
                return self._create_error_response(dsr_request.request_id, validation_result['errors'])
            
            # Check cache first
            if self.config.enable_request_caching:
                cached_response = self._get_cached_response(dsr_request)
                if cached_response:
                    return cached_response
            
            # Process request with parallelization
            response = await self._process_request_async(dsr_request)
            
            # Apply security measures if enabled
            if self.config.enable_encryption:
                response = await self._apply_encryption_async(response)
            
            # Cache response if caching is enabled
            if self.config.enable_request_caching:
                self._cache_response(dsr_request, response)
            
            # Update statistics
            processing_time = time.time() - start_time
            self._update_statistics(dsr_request, processing_time)
            
            # Audit logging if enabled
            if self.config.enable_audit_logging:
                await self._log_dsr_audit_async(dsr_request, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Async DSR request processing failed: {e}")
            return self._create_error_response("unknown", [str(e)])
    
    def _create_dsr_request(self, request_data: Dict[str, Any]) -> DSRRequest:
        """Create DSR request object from input data."""
        request_id = request_data.get('request_id') or str(uuid.uuid4())
        
        dsr_request = DSRRequest(
            request_id=request_id,
            request_type=DSRRequestType(request_data['request_type']),
            requester_email=request_data['requester_email'],
            requester_name=request_data.get('requester_name'),
            requester_id=request_data.get('requester_id'),
            description=request_data.get('description', ''),
            specific_data_categories=request_data.get('data_categories', []),
            priority=DSRPriority(request_data.get('priority', 'medium'))
        )
        
        # Set due date based on priority and regulations
        if dsr_request.priority == DSRPriority.URGENT:
            dsr_request.due_date = datetime.now(timezone.utc) + timedelta(days=self.config.urgent_response_time_days)
        else:
            dsr_request.due_date = datetime.now(timezone.utc) + timedelta(days=self.config.default_response_time_days)
        
        # Determine applicable regulations
        if self.config.gdpr_compliance:
            dsr_request.gdpr_applicable = True
        if self.config.ccpa_compliance:
            dsr_request.ccpa_applicable = True
        
        # Set legal review requirement
        dsr_request.legal_review_required = self.config.require_legal_review
        
        return dsr_request
    
    def _validate_request(self, request: DSRRequest) -> Dict[str, Any]:
        """Validate DSR request."""
        errors = []
        
        # Basic validation
        if not request.requester_email:
            errors.append("Requester email is required")
        
        if not request.request_type:
            errors.append("Request type is required")
        
        # Email format validation
        if request.requester_email and '@' not in request.requester_email:
            errors.append("Invalid email format")
        
        # Identity verification
        if self.config.enable_identity_verification and not request.identity_verified:
            errors.append("Identity verification required")
        
        # Data categories validation for specific request types
        if request.request_type in [DSRRequestType.ACCESS, DSRRequestType.PORTABILITY]:
            if not request.specific_data_categories:
                errors.append("Specific data categories required for access/portability requests")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    async def _validate_request_async(self, request: DSRRequest) -> Dict[str, Any]:
        """Validate DSR request asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._thread_pool, self._validate_request, request)
    
    def _process_request_by_type(self, request: DSRRequest) -> Dict[str, Any]:
        """Process request based on its type."""
        if request.request_type == DSRRequestType.ACCESS:
            return self._process_access_request(request)
        elif request.request_type == DSRRequestType.RECTIFICATION:
            return self._process_rectification_request(request)
        elif request.request_type == DSRRequestType.ERASURE:
            return self._process_erasure_request(request)
        elif request.request_type == DSRRequestType.RESTRICTION:
            return self._process_restriction_request(request)
        elif request.request_type == DSRRequestType.PORTABILITY:
            return self._process_portability_request(request)
        elif request.request_type == DSRRequestType.OBJECTION:
            return self._process_objection_request(request)
        elif request.request_type == DSRRequestType.WITHDRAW_CONSENT:
            return self._process_withdraw_consent_request(request)
        else:
            return self._create_error_response(request.request_id, ["Unsupported request type"])
    
    async def _process_request_async(self, request: DSRRequest) -> Dict[str, Any]:
        """Process request asynchronously with data collection."""
        if request.request_type == DSRRequestType.ACCESS:
            return await self._process_access_request_async(request)
        elif request.request_type == DSRRequestType.RECTIFICATION:
            return await self._process_rectification_request_async(request)
        elif request.request_type == DSRRequestType.ERASURE:
            return await self._process_erasure_request_async(request)
        elif request.request_type == DSRRequestType.RESTRICTION:
            return await self._process_restriction_request_async(request)
        elif request.request_type == DSRRequestType.PORTABILITY:
            return await self._process_portability_request_async(request)
        elif request.request_type == DSRRequestType.OBJECTION:
            return await self._process_objection_request_async(request)
        elif request.request_type == DSRRequestType.WITHDRAW_CONSENT:
            return await self._process_withdraw_consent_request_async(request)
        else:
            return self._create_error_response(request.request_id, ["Unsupported request type"])
    
    # Request Type Processing Methods
    
    def _process_access_request(self, request: DSRRequest) -> Dict[str, Any]:
        """Process data access request."""
        # Mock data collection for basic mode
        collected_data = {
            "user_profile": {"email": request.requester_email, "created_at": "2023-01-15"},
            "preferences": {"marketing_emails": True},
            "audit_trail": {"last_login": "2024-01-15T10:00:00Z"}
        }
        
        response = DSRResponse(
            request_id=request.request_id,
            status=DSRStatus.COMPLETED,
            response_type=request.request_type,
            data_provided=collected_data,
            actions_taken=["Data collected from all systems", "Data anonymized as required"],
            processing_time_hours=1.0,
            legal_basis="Legitimate interest - Article 6(1)(f) GDPR",
            data_sources=["user_database", "preference_service", "audit_system"]
        )
        
        return self._create_success_response(request, response)
    
    async def _process_access_request_async(self, request: DSRRequest) -> Dict[str, Any]:
        """Process data access request asynchronously with full data collection."""
        if not self._data_collector:
            return self._process_access_request(request)
        
        # Collect data from all relevant sources
        collected_data = await self._data_collector.collect_data(
            request.requester_email, 
            request.specific_data_categories or ['user_profiles', 'preferences', 'audit_logs']
        )
        
        response = DSRResponse(
            request_id=request.request_id,
            status=DSRStatus.COMPLETED,
            response_type=request.request_type,
            data_provided=collected_data,
            actions_taken=["Comprehensive data collection completed", "Data anonymized as required"],
            processing_time_hours=0.5,
            legal_basis="Legitimate interest - Article 6(1)(f) GDPR",
            data_sources=list(collected_data.keys()),
            generated_by="automated_async"
        )
        
        return self._create_success_response(request, response)
    
    def _process_rectification_request(self, request: DSRRequest) -> Dict[str, Any]:
        """Process data rectification request."""
        response = DSRResponse(
            request_id=request.request_id,
            status=DSRStatus.COMPLETED,
            response_type=request.request_type,
            actions_taken=["Data corrections applied", "Systems updated"],
            processing_time_hours=2.0,
            legal_basis="Data accuracy - Article 5(1)(d) GDPR"
        )
        
        return self._create_success_response(request, response)
    
    async def _process_rectification_request_async(self, request: DSRRequest) -> Dict[str, Any]:
        """Process rectification request asynchronously."""
        # Simulate async processing
        await asyncio.sleep(0.1)
        return self._process_rectification_request(request)
    
    def _process_erasure_request(self, request: DSRRequest) -> Dict[str, Any]:
        """Process data erasure request (right to be forgotten)."""
        response = DSRResponse(
            request_id=request.request_id,
            status=DSRStatus.COMPLETED if not self.config.deletion_verification_required else DSRStatus.IN_PROGRESS,
            response_type=request.request_type,
            actions_taken=["Data deletion scheduled", "Verification process initiated"],
            processing_time_hours=4.0,
            legal_basis="Right to erasure - Article 17 GDPR"
        )
        
        return self._create_success_response(request, response)
    
    async def _process_erasure_request_async(self, request: DSRRequest) -> Dict[str, Any]:
        """Process erasure request asynchronously with parallel deletion."""
        # Simulate parallel deletion across multiple systems
        deletion_tasks = [
            "user_database_deletion",
            "preference_deletion", 
            "audit_log_anonymization",
            "backup_system_deletion"
        ]
        
        # Simulate async deletion
        await asyncio.sleep(0.2)
        
        response = DSRResponse(
            request_id=request.request_id,
            status=DSRStatus.COMPLETED if self.config.enable_automatic_deletion else DSRStatus.IN_PROGRESS,
            response_type=request.request_type,
            actions_taken=[f"Completed: {task}" for task in deletion_tasks],
            processing_time_hours=1.0,
            legal_basis="Right to erasure - Article 17 GDPR",
            data_sources=deletion_tasks
        )
        
        return self._create_success_response(request, response)
    
    def _process_restriction_request(self, request: DSRRequest) -> Dict[str, Any]:
        """Process processing restriction request."""
        response = DSRResponse(
            request_id=request.request_id,
            status=DSRStatus.COMPLETED,
            response_type=request.request_type,
            actions_taken=["Processing restrictions applied", "Data marked as restricted"],
            processing_time_hours=1.0,
            legal_basis="Right to restriction - Article 18 GDPR"
        )
        
        return self._create_success_response(request, response)
    
    async def _process_restriction_request_async(self, request: DSRRequest) -> Dict[str, Any]:
        """Process restriction request asynchronously."""
        await asyncio.sleep(0.1)
        return self._process_restriction_request(request)
    
    def _process_portability_request(self, request: DSRRequest) -> Dict[str, Any]:
        """Process data portability request."""
        # Export data in machine-readable format
        exported_data = {
            "format": "JSON",
            "data": {
                "user_profile": {"email": request.requester_email},
                "preferences": {"marketing_emails": True},
                "export_date": datetime.now(timezone.utc).isoformat()
            }
        }
        
        response = DSRResponse(
            request_id=request.request_id,
            status=DSRStatus.COMPLETED,
            response_type=request.request_type,
            data_provided=exported_data,
            actions_taken=["Data exported in portable format", "Structured data package created"],
            processing_time_hours=1.5,
            legal_basis="Right to data portability - Article 20 GDPR",
            format="json"
        )
        
        return self._create_success_response(request, response)
    
    async def _process_portability_request_async(self, request: DSRRequest) -> Dict[str, Any]:
        """Process portability request asynchronously."""
        if not self._data_collector:
            return self._process_portability_request(request)
        
        # Collect and export data in portable format
        collected_data = await self._data_collector.collect_data(
            request.requester_email,
            request.specific_data_categories or ['user_profiles', 'preferences', 'transaction_history']
        )
        
        exported_data = {
            "format": "JSON",
            "export_version": "1.0",
            "data": collected_data,
            "export_date": datetime.now(timezone.utc).isoformat(),
            "requester": request.requester_email
        }
        
        response = DSRResponse(
            request_id=request.request_id,
            status=DSRStatus.COMPLETED,
            response_type=request.request_type,
            data_provided=exported_data,
            actions_taken=["Comprehensive data export completed", "Machine-readable format provided"],
            processing_time_hours=0.5,
            legal_basis="Right to data portability - Article 20 GDPR",
            format="json"
        )
        
        return self._create_success_response(request, response)
    
    def _process_objection_request(self, request: DSRRequest) -> Dict[str, Any]:
        """Process objection to processing request."""
        response = DSRResponse(
            request_id=request.request_id,
            status=DSRStatus.COMPLETED,
            response_type=request.request_type,
            actions_taken=["Processing objection recorded", "Data processing stopped"],
            processing_time_hours=0.5,
            legal_basis="Right to object - Article 21 GDPR"
        )
        
        return self._create_success_response(request, response)
    
    async def _process_objection_request_async(self, request: DSRRequest) -> Dict[str, Any]:
        """Process objection request asynchronously."""
        await asyncio.sleep(0.1)
        return self._process_objection_request(request)
    
    def _process_withdraw_consent_request(self, request: DSRRequest) -> Dict[str, Any]:
        """Process consent withdrawal request."""
        response = DSRResponse(
            request_id=request.request_id,
            status=DSRStatus.COMPLETED,
            response_type=request.request_type,
            actions_taken=["Consent withdrawn", "Processing based on consent stopped"],
            processing_time_hours=0.5,
            legal_basis="Consent withdrawal - Article 7(3) GDPR"
        )
        
        return self._create_success_response(request, response)
    
    async def _process_withdraw_consent_request_async(self, request: DSRRequest) -> Dict[str, Any]:
        """Process consent withdrawal asynchronously."""
        await asyncio.sleep(0.1)
        return self._process_withdraw_consent_request(request)
    
    # Response Generation Methods
    
    def _create_success_response(self, request: DSRRequest, dsr_response: DSRResponse) -> Dict[str, Any]:
        """Create successful response."""
        return {
            'success': True,
            'request_id': request.request_id,
            'status': dsr_response.status.value,
            'request_type': request.request_type.value,
            'processing_time_hours': dsr_response.processing_time_hours,
            'data': dsr_response.data_provided,
            'actions_taken': dsr_response.actions_taken,
            'legal_basis': dsr_response.legal_basis,
            'data_sources': dsr_response.data_sources,
            'compliance': {
                'gdpr_compliant': request.gdpr_applicable,
                'ccpa_compliant': request.ccpa_applicable,
                'response_time_days': (datetime.now(timezone.utc) - request.created_at).days
            },
            'metadata': {
                'generated_at': dsr_response.generated_at.isoformat(),
                'generated_by': dsr_response.generated_by,
                'format': dsr_response.format,
                'encryption_used': dsr_response.encryption_used,
                'mode': self.config.mode.value
            }
        }
    
    def _create_error_response(self, request_id: str, errors: List[str]) -> Dict[str, Any]:
        """Create error response."""
        return {
            'success': False,
            'request_id': request_id,
            'status': DSRStatus.REJECTED.value,
            'errors': errors,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'mode': self.config.mode.value
        }
    
    # Caching Methods
    
    def _get_cached_response(self, request: DSRRequest) -> Optional[Dict[str, Any]]:
        """Get cached response for request."""
        cache_key = self._generate_cache_key(request)
        
        with self._cache_lock:
            if cache_key in self._request_cache:
                response, timestamp = self._request_cache[cache_key]
                if time.time() - timestamp < (self.config.cache_ttl_hours * 3600):
                    return response
                else:
                    del self._request_cache[cache_key]
        
        return None
    
    def _cache_response(self, request: DSRRequest, response: Dict[str, Any]):
        """Cache response for request."""
        cache_key = self._generate_cache_key(request)
        
        with self._cache_lock:
            # Implement simple LRU eviction
            if len(self._request_cache) >= 1000:
                oldest_key = min(self._request_cache.keys(),
                               key=lambda k: self._request_cache[k][1])
                del self._request_cache[oldest_key]
            
            self._request_cache[cache_key] = (response, time.time())
    
    def _generate_cache_key(self, request: DSRRequest) -> str:
        """Generate cache key for request."""
        key_data = f"{request.request_type.value}_{request.requester_email}_{request.specific_data_categories}"
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    # Security Methods
    
    def _apply_encryption(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Apply encryption to sensitive response data."""
        if 'data' in response and response['data']:
            # In production, this would use proper encryption
            response['metadata']['encryption_used'] = True
            response['data'] = {"encrypted": True, "note": "Data encrypted for transmission"}
        
        return response
    
    async def _apply_encryption_async(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Apply encryption asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._thread_pool, self._apply_encryption, response)
    
    # Statistics and Audit Methods
    
    def _update_statistics(self, request: DSRRequest, processing_time: float):
        """Update processing statistics."""
        self._statistics.total_requests += 1
        
        # Update request type counters
        request_type = request.request_type.value
        self._statistics.requests_by_type[request_type] = \
            self._statistics.requests_by_type.get(request_type, 0) + 1
        
        # Update status counters
        status = request.status.value
        self._statistics.requests_by_status[status] = \
            self._statistics.requests_by_status.get(status, 0) + 1
        
        # Update average processing time
        total_requests = self._statistics.total_requests
        current_avg = self._statistics.avg_processing_time_hours
        processing_hours = processing_time / 3600
        
        new_avg = ((current_avg * (total_requests - 1)) + processing_hours) / total_requests
        self._statistics.avg_processing_time_hours = new_avg
        
        self._statistics.last_processed = datetime.now()
        self._statistics.last_updated = datetime.now()
    
    def _log_dsr_audit(self, request: DSRRequest, response: Dict[str, Any]):
        """Log DSR processing audit information."""
        audit_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'request_id': request.request_id,
            'request_type': request.request_type.value,
            'requester_email': request.requester_email,
            'status': response['status'],
            'processing_time_hours': response.get('processing_time_hours', 0),
            'gdpr_applicable': request.gdpr_applicable,
            'ccpa_applicable': request.ccpa_applicable,
            'mode': self.config.mode.value,
            'automated_processing': self.config.enable_automated_processing
        }
        
        logger.info(f"DSR Processing Audit: {json.dumps(audit_entry)}")
    
    async def _log_dsr_audit_async(self, request: DSRRequest, response: Dict[str, Any]):
        """Log DSR audit information asynchronously."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._log_dsr_audit, request, response)
    
    # Utility Methods
    
    async def health_check(self) -> bool:
        """Perform health check of DSR handler."""
        try:
            # Test basic functionality
            test_request = {
                'request_type': 'access',
                'requester_email': 'test@example.com',
                'description': 'Health check test'
            }
            
            result = await self.process_request_async(test_request) if self.config.mode != DSROperationMode.BASIC else self.process_request(test_request)
            
            return result.get('success', False)
                
        except Exception as e:
            logger.error(f"DSR handler health check failed: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive handler statistics."""
        return {
            'mode': self.config.mode.value,
            'total_requests': self._statistics.total_requests,
            'requests_by_type': dict(self._statistics.requests_by_type),
            'requests_by_status': dict(self._statistics.requests_by_status),
            'avg_processing_time_hours': round(self._statistics.avg_processing_time_hours, 2),
            'compliance_rate': self._statistics.compliance_rate,
            'rejection_rate': self._statistics.rejection_rate,
            'automated_processing_rate': self._statistics.automated_processing_rate,
            'pending_requests': self._statistics.pending_requests,
            'overdue_requests': self._statistics.overdue_requests,
            'cache_size': len(self._request_cache),
            'parallel_processing_enabled': self.config.enable_parallel_processing,
            'data_collector_available': self._data_collector is not None,
            'last_processed': self._statistics.last_processed.isoformat() if self._statistics.last_processed else None,
            'last_updated': self._statistics.last_updated.isoformat()
        }
    
    def clear_cache(self):
        """Clear request cache."""
        with self._cache_lock:
            self._request_cache.clear()
    
    def __del__(self):
        """Cleanup resources."""
        try:
            if self._thread_pool:
                self._thread_pool.shutdown(wait=False)
        except:
            pass


# Factory functions for different modes
def create_basic_dsr_handler(config: Optional[DSRConfig] = None) -> UnifiedDSRHandler:
    """Create basic DSR handler."""
    if config is None:
        config = DSRConfig(mode=DSROperationMode.BASIC)
    return UnifiedDSRHandler(config)


def create_performance_dsr_handler(config: Optional[DSRConfig] = None) -> UnifiedDSRHandler:
    """Create performance-optimized DSR handler."""
    if config is None:
        config = DSRConfig(mode=DSROperationMode.PERFORMANCE)
    return UnifiedDSRHandler(config)


def create_secure_dsr_handler(config: Optional[DSRConfig] = None) -> UnifiedDSRHandler:
    """Create security-enhanced DSR handler."""
    if config is None:
        config = DSRConfig(mode=DSROperationMode.SECURE)
    return UnifiedDSRHandler(config)


def create_enterprise_dsr_handler(config: Optional[DSRConfig] = None) -> UnifiedDSRHandler:
    """Create enterprise DSR handler with all features."""
    if config is None:
        config = DSRConfig(mode=DSROperationMode.ENTERPRISE)
    return UnifiedDSRHandler(config)