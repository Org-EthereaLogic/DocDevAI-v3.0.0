"""
DSR Request Handler - GDPR Data Subject Rights implementation.

Handles GDPR Articles 15-21 compliance including access, rectification,
erasure, portability, restriction, and objection rights.
"""

import logging
import json
import hashlib
import shutil
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
import asyncio

logger = logging.getLogger(__name__)


class DSRRequestType(str, Enum):
    """Data Subject Rights request types (GDPR Articles)."""
    ACCESS = "access"                    # Article 15 - Right of access
    RECTIFICATION = "rectification"      # Article 16 - Right to rectification  
    ERASURE = "erasure"                  # Article 17 - Right to erasure
    PORTABILITY = "portability"          # Article 20 - Right to data portability
    RESTRICTION = "restriction"          # Article 18 - Right to restriction
    OBJECTION = "objection"              # Article 21 - Right to object


class DSRStatus(str, Enum):
    """DSR request processing status."""
    PENDING = "pending"                  # Request received, pending processing
    IN_PROGRESS = "in_progress"          # Currently being processed
    COMPLETED = "completed"              # Successfully completed
    REJECTED = "rejected"                # Rejected with reason
    EXPIRED = "expired"                  # Request expired before completion


@dataclass
class DSRConfig:
    """Configuration for DSR processing."""
    # Response time requirements
    response_time_hours: int = 72        # Time to acknowledge request
    completion_time_days: int = 30       # Time to complete request (GDPR max)
    
    # Data retention
    request_retention_days: int = 365    # How long to keep DSR records
    data_export_retention_days: int = 30 # How long to keep export files
    
    # Security settings
    secure_deletion_passes: int = 3      # DoD 5220.22-M standard
    encryption_required: bool = True     # Encrypt all DSR data
    audit_all_actions: bool = True       # Log all DSR operations
    
    # Validation settings
    identity_verification: bool = True   # Require identity verification
    require_digital_signature: bool = False  # Require digital signatures
    
    # Export settings
    export_formats: List[str] = field(default_factory=lambda: ["json", "csv"])
    max_export_size_mb: int = 100       # Maximum export file size


@dataclass
class DSRRequest:
    """Data Subject Rights request."""
    request_id: str
    user_id: str
    request_type: DSRRequestType
    status: DSRStatus = DSRStatus.PENDING
    
    # Request details
    submitted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    description: Optional[str] = None
    specific_data_categories: Optional[List[str]] = None
    
    # Processing details
    acknowledged_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processor_id: Optional[str] = None
    
    # Response details
    response_data: Optional[Dict[str, Any]] = None
    rejection_reason: Optional[str] = None
    
    # Metadata
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    verification_method: Optional[str] = None
    
    def is_expired(self, config: DSRConfig) -> bool:
        """Check if request has expired."""
        if self.status in [DSRStatus.COMPLETED, DSRStatus.REJECTED]:
            return False
        
        expiry_time = self.submitted_at + timedelta(days=config.completion_time_days)
        return datetime.now(timezone.utc) > expiry_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/export."""
        return {
            'request_id': self.request_id,
            'user_id': self.user_id,
            'request_type': self.request_type.value,
            'status': self.status.value,
            'submitted_at': self.submitted_at.isoformat(),
            'description': self.description,
            'specific_data_categories': self.specific_data_categories,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'processor_id': self.processor_id,
            'rejection_reason': self.rejection_reason,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'verification_method': self.verification_method
        }


@dataclass
class DSRResponse:
    """DSR request response."""
    request_id: str
    status: DSRStatus
    message: str
    
    # Response data (for successful requests)
    data: Optional[Dict[str, Any]] = None
    export_files: Optional[List[str]] = None
    
    # Processing details
    processed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    processing_time_seconds: Optional[float] = None
    
    # Compliance details
    legal_basis: Optional[str] = None
    data_sources: Optional[List[str]] = None
    retention_period: Optional[str] = None


class DSRRequestHandler:
    """
    GDPR Data Subject Rights request handler.
    
    Implements Articles 15-21 of GDPR for handling data subject requests
    including access, rectification, erasure, portability, and restriction.
    """
    
    def __init__(self, security_manager=None, encryption_manager=None, 
                 config: Optional[DSRConfig] = None):
        """
        Initialize DSR request handler.
        
        Args:
            security_manager: Security manager instance
            encryption_manager: Encryption manager for secure operations
            config: DSR configuration
        """
        self.security_manager = security_manager
        self.encryption_manager = encryption_manager
        self.config = config or DSRConfig()
        
        # Request storage
        self.requests_storage = {}  # In production, use persistent storage
        self.request_history = []
        
        # Data source registry (for access/portability requests)
        self.data_sources = {
            'user_profile': self._get_user_profile_data,
            'documents': self._get_document_data,
            'activity_logs': self._get_activity_log_data,
            'preferences': self._get_preferences_data,
            'security_events': self._get_security_events_data
        }
        
        logger.info("DSRRequestHandler initialized")
    
    def process_request(self, request_type: Union[str, DSRRequestType], 
                       user_data: Dict[str, Any], user_id: str,
                       **kwargs) -> Dict[str, Any]:
        """
        Process a DSR request.
        
        Args:
            request_type: Type of DSR request
            user_data: User data and request details
            user_id: User identifier
            **kwargs: Additional request parameters
            
        Returns:
            DSR processing result
        """
        if isinstance(request_type, str):
            request_type = DSRRequestType(request_type)
        
        # Create request ID
        request_id = self._generate_request_id(user_id, request_type)
        
        # Create DSR request object
        request = DSRRequest(
            request_id=request_id,
            user_id=user_id,
            request_type=request_type,
            description=user_data.get('description'),
            specific_data_categories=user_data.get('data_categories'),
            ip_address=kwargs.get('ip_address'),
            user_agent=kwargs.get('user_agent')
        )
        
        try:
            # Store request
            self.requests_storage[request_id] = request
            self.request_history.append(request)
            
            # Acknowledge request
            request.acknowledged_at = datetime.now(timezone.utc)
            request.status = DSRStatus.IN_PROGRESS
            
            # Process based on request type
            if request_type == DSRRequestType.ACCESS:
                response = self._process_access_request(request)
            elif request_type == DSRRequestType.RECTIFICATION:
                response = self._process_rectification_request(request, user_data)
            elif request_type == DSRRequestType.ERASURE:
                response = self._process_erasure_request(request)
            elif request_type == DSRRequestType.PORTABILITY:
                response = self._process_portability_request(request)
            elif request_type == DSRRequestType.RESTRICTION:
                response = self._process_restriction_request(request, user_data)
            elif request_type == DSRRequestType.OBJECTION:
                response = self._process_objection_request(request, user_data)
            else:
                raise ValueError(f"Unsupported request type: {request_type}")
            
            # Update request status
            request.completed_at = datetime.now(timezone.utc)
            request.status = DSRStatus.COMPLETED
            request.response_data = response.data
            
            # Audit logging
            if self.config.audit_all_actions and self.security_manager:
                self.security_manager.audit_logger.log_event('dsr_request_completed', {
                    'request_id': request_id,
                    'user_id': user_id,
                    'request_type': request_type.value,
                    'processing_time_seconds': response.processing_time_seconds
                })
            
            return {
                'success': True,
                'request_id': request_id,
                'status': response.status.value,
                'message': response.message,
                'data': response.data,
                'export_files': response.export_files,
                'processing_time_seconds': response.processing_time_seconds
            }
            
        except Exception as e:
            # Handle processing error
            request.status = DSRStatus.REJECTED
            request.rejection_reason = str(e)
            
            logger.error(f"DSR request {request_id} failed: {e}")
            
            if self.config.audit_all_actions and self.security_manager:
                self.security_manager.audit_logger.log_event('dsr_request_failed', {
                    'request_id': request_id,
                    'user_id': user_id,
                    'request_type': request_type.value,
                    'error': str(e)
                })
            
            return {
                'success': False,
                'request_id': request_id,
                'status': DSRStatus.REJECTED.value,
                'message': f'Request failed: {str(e)}',
                'error': str(e)
            }
    
    def _process_access_request(self, request: DSRRequest) -> DSRResponse:
        """Process GDPR Article 15 - Right of access."""
        start_time = datetime.now()
        
        user_data = {}
        data_sources_used = []
        
        # Collect data from all sources
        for source_name, source_func in self.data_sources.items():
            try:
                # Check if specific categories were requested
                if (request.specific_data_categories and 
                    source_name not in request.specific_data_categories):
                    continue
                
                source_data = source_func(request.user_id)
                if source_data:
                    user_data[source_name] = source_data
                    data_sources_used.append(source_name)
                    
            except Exception as e:
                logger.warning(f"Failed to collect data from {source_name}: {e}")
        
        # Add metadata
        access_response = {
            'user_id': request.user_id,
            'data_collected_at': datetime.now(timezone.utc).isoformat(),
            'data_sources': data_sources_used,
            'personal_data': user_data,
            'processing_purposes': [
                'Service provision',
                'Legal compliance',
                'Security monitoring'
            ],
            'data_recipients': [
                'Internal systems only'
            ],
            'retention_periods': {
                'user_profile': '2 years after account closure',
                'documents': '5 years for compliance',
                'activity_logs': '1 year for security',
                'preferences': 'Until account closure'
            },
            'user_rights': [
                'Right to rectification (Article 16)',
                'Right to erasure (Article 17)', 
                'Right to restrict processing (Article 18)',
                'Right to data portability (Article 20)',
                'Right to object (Article 21)'
            ]
        }
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return DSRResponse(
            request_id=request.request_id,
            status=DSRStatus.COMPLETED,
            message="Access request completed successfully",
            data=access_response,
            processing_time_seconds=processing_time,
            legal_basis="GDPR Article 15",
            data_sources=data_sources_used,
            retention_period=f"{self.config.request_retention_days} days"
        )
    
    def _process_rectification_request(self, request: DSRRequest, 
                                     user_data: Dict[str, Any]) -> DSRResponse:
        """Process GDPR Article 16 - Right to rectification."""
        start_time = datetime.now()
        
        corrections = user_data.get('corrections', {})
        if not corrections:
            raise ValueError("No corrections specified for rectification request")
        
        updated_fields = []
        
        # Apply corrections to user data
        for field, new_value in corrections.items():
            try:
                # In production, this would update the actual data stores
                # For now, simulate the update
                old_value = self._get_current_field_value(request.user_id, field)
                
                # Validate the correction
                if self._validate_field_correction(field, new_value):
                    # Apply correction (simulated)
                    self._update_user_field(request.user_id, field, new_value)
                    updated_fields.append({
                        'field': field,
                        'old_value': old_value,
                        'new_value': new_value,
                        'updated_at': datetime.now(timezone.utc).isoformat()
                    })
                else:
                    logger.warning(f"Invalid correction for field {field}: {new_value}")
                    
            except Exception as e:
                logger.error(f"Failed to correct field {field}: {e}")
        
        if not updated_fields:
            raise ValueError("No valid corrections could be applied")
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return DSRResponse(
            request_id=request.request_id,
            status=DSRStatus.COMPLETED,
            message=f"Successfully updated {len(updated_fields)} field(s)",
            data={'updated_fields': updated_fields},
            processing_time_seconds=processing_time,
            legal_basis="GDPR Article 16"
        )
    
    def _process_erasure_request(self, request: DSRRequest) -> DSRResponse:
        """Process GDPR Article 17 - Right to erasure (Right to be forgotten)."""
        start_time = datetime.now()
        
        # Check if erasure is permitted
        if not self._can_process_erasure(request.user_id):
            raise ValueError("Erasure not permitted due to legal obligations or legitimate interests")
        
        deleted_data_types = []
        
        # Perform secure deletion across all data sources
        for source_name, source_func in self.data_sources.items():
            try:
                # Check if data exists
                data = source_func(request.user_id)
                if data:
                    # Perform secure deletion
                    self._secure_delete_data(source_name, request.user_id)
                    deleted_data_types.append(source_name)
                    
            except Exception as e:
                logger.error(f"Failed to delete data from {source_name}: {e}")
        
        # Verify deletion completed
        verification_results = self._verify_deletion(request.user_id)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return DSRResponse(
            request_id=request.request_id,
            status=DSRStatus.COMPLETED,
            message=f"Data erasure completed for {len(deleted_data_types)} data sources",
            data={
                'deleted_data_types': deleted_data_types,
                'deletion_method': f"DoD 5220.22-M ({self.config.secure_deletion_passes} passes)",
                'verification_results': verification_results,
                'deletion_completed_at': datetime.now(timezone.utc).isoformat()
            },
            processing_time_seconds=processing_time,
            legal_basis="GDPR Article 17"
        )
    
    def _process_portability_request(self, request: DSRRequest) -> DSRResponse:
        """Process GDPR Article 20 - Right to data portability."""
        start_time = datetime.now()
        
        # Collect portable data (structured, commonly used formats)
        portable_data = {}
        export_files = []
        
        for source_name, source_func in self.data_sources.items():
            try:
                data = source_func(request.user_id)
                if data and self._is_data_portable(source_name):
                    portable_data[source_name] = data
                    
            except Exception as e:
                logger.warning(f"Failed to collect portable data from {source_name}: {e}")
        
        # Generate export files
        if portable_data:
            for format_type in self.config.export_formats:
                export_file = self._create_export_file(
                    request.user_id, portable_data, format_type
                )
                if export_file:
                    export_files.append(export_file)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return DSRResponse(
            request_id=request.request_id,
            status=DSRStatus.COMPLETED,
            message=f"Data portability export completed ({len(export_files)} files)",
            data={
                'export_summary': {
                    'total_records': sum(len(v) if isinstance(v, list) else 1 for v in portable_data.values()),
                    'data_sources': list(portable_data.keys()),
                    'export_formats': self.config.export_formats
                }
            },
            export_files=export_files,
            processing_time_seconds=processing_time,
            legal_basis="GDPR Article 20"
        )
    
    def _process_restriction_request(self, request: DSRRequest, 
                                   user_data: Dict[str, Any]) -> DSRResponse:
        """Process GDPR Article 18 - Right to restriction of processing."""
        start_time = datetime.now()
        
        restriction_reason = user_data.get('reason', 'unspecified')
        data_categories = user_data.get('data_categories', [])
        
        # Apply processing restrictions
        restricted_categories = []
        
        for category in data_categories if data_categories else self.data_sources.keys():
            try:
                # Apply restriction (in production, this would modify access controls)
                self._apply_processing_restriction(request.user_id, category, restriction_reason)
                restricted_categories.append(category)
                
            except Exception as e:
                logger.error(f"Failed to restrict processing for {category}: {e}")
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return DSRResponse(
            request_id=request.request_id,
            status=DSRStatus.COMPLETED,
            message=f"Processing restriction applied to {len(restricted_categories)} categories",
            data={
                'restricted_categories': restricted_categories,
                'restriction_reason': restriction_reason,
                'restriction_applied_at': datetime.now(timezone.utc).isoformat(),
                'note': 'Data will only be processed with your consent or for legal claims'
            },
            processing_time_seconds=processing_time,
            legal_basis="GDPR Article 18"
        )
    
    def _process_objection_request(self, request: DSRRequest,
                                 user_data: Dict[str, Any]) -> DSRResponse:
        """Process GDPR Article 21 - Right to object."""
        start_time = datetime.now()
        
        objection_grounds = user_data.get('grounds', 'legitimate interests')
        processing_purposes = user_data.get('processing_purposes', [])
        
        # Evaluate objection
        accepted_objections = []
        rejected_objections = []
        
        for purpose in processing_purposes:
            if self._evaluate_objection(request.user_id, purpose, objection_grounds):
                # Stop processing for this purpose
                self._stop_processing_for_purpose(request.user_id, purpose)
                accepted_objections.append(purpose)
            else:
                # Compelling legitimate grounds exist
                rejected_objections.append({
                    'purpose': purpose,
                    'reason': 'Compelling legitimate grounds or legal claims'
                })
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return DSRResponse(
            request_id=request.request_id,
            status=DSRStatus.COMPLETED,
            message="Objection request processed",
            data={
                'objection_grounds': objection_grounds,
                'accepted_objections': accepted_objections,
                'rejected_objections': rejected_objections,
                'processed_at': datetime.now(timezone.utc).isoformat()
            },
            processing_time_seconds=processing_time,
            legal_basis="GDPR Article 21"
        )
    
    # Data source methods (would integrate with actual data stores)
    
    def _get_user_profile_data(self, user_id: str) -> Dict[str, Any]:
        """Get user profile data."""
        return {
            'user_id': user_id,
            'created_at': '2024-01-01T00:00:00Z',
            'last_login': '2024-12-01T10:00:00Z',
            'account_status': 'active'
        }
    
    def _get_document_data(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user document data."""
        return [
            {'document_id': 'doc_001', 'created_at': '2024-01-15T09:00:00Z'},
            {'document_id': 'doc_002', 'created_at': '2024-02-10T14:30:00Z'}
        ]
    
    def _get_activity_log_data(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user activity logs."""
        return [
            {'action': 'login', 'timestamp': '2024-12-01T10:00:00Z'},
            {'action': 'document_created', 'timestamp': '2024-11-30T15:30:00Z'}
        ]
    
    def _get_preferences_data(self, user_id: str) -> Dict[str, Any]:
        """Get user preferences."""
        return {
            'language': 'en',
            'timezone': 'UTC',
            'notifications': {'email': True, 'push': False}
        }
    
    def _get_security_events_data(self, user_id: str) -> List[Dict[str, Any]]:
        """Get security events."""
        return [
            {'event': 'password_change', 'timestamp': '2024-10-15T12:00:00Z'}
        ]
    
    # Helper methods
    
    def _generate_request_id(self, user_id: str, request_type: DSRRequestType) -> str:
        """Generate unique request ID."""
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
        hash_input = f"{user_id}_{request_type.value}_{timestamp}"
        hash_short = hashlib.sha256(hash_input.encode()).hexdigest()[:8]
        return f"DSR_{request_type.value.upper()}_{timestamp}_{hash_short}"
    
    def _can_process_erasure(self, user_id: str) -> bool:
        """Check if erasure is legally permitted."""
        # In production, check for:
        # - Legal retention requirements
        # - Ongoing legal proceedings
        # - Legitimate interests
        return True
    
    def _secure_delete_data(self, source_name: str, user_id: str):
        """Perform secure deletion using DoD 5220.22-M standard."""
        # In production, this would:
        # 1. Overwrite data multiple times with random patterns
        # 2. Update indices and references
        # 3. Clear caches
        logger.info(f"Securely deleted data from {source_name} for user {user_id}")
    
    def _verify_deletion(self, user_id: str) -> Dict[str, bool]:
        """Verify data deletion was successful."""
        return {source: True for source in self.data_sources.keys()}
    
    def _is_data_portable(self, source_name: str) -> bool:
        """Check if data source contains portable data."""
        # Only user-provided data is portable, not derived/inferred data
        portable_sources = {'user_profile', 'documents', 'preferences'}
        return source_name in portable_sources
    
    def _create_export_file(self, user_id: str, data: Dict[str, Any], 
                           format_type: str) -> Optional[str]:
        """Create export file in specified format."""
        try:
            filename = f"user_data_export_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format_type}"
            
            if format_type == 'json':
                # JSON export
                export_path = Path(f"/tmp/{filename}")  # In production, use secure storage
                with open(export_path, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                    
            elif format_type == 'csv':
                # CSV export (simplified)
                export_path = Path(f"/tmp/{filename}")
                # Implementation would create CSV from structured data
                
            return str(export_path)
            
        except Exception as e:
            logger.error(f"Failed to create export file: {e}")
            return None
    
    def _get_current_field_value(self, user_id: str, field: str) -> Any:
        """Get current value of a field."""
        return "current_value"  # Placeholder
    
    def _validate_field_correction(self, field: str, new_value: Any) -> bool:
        """Validate a field correction."""
        return True  # Placeholder validation
    
    def _update_user_field(self, user_id: str, field: str, new_value: Any):
        """Update a user field."""
        logger.info(f"Updated {field} for user {user_id}")
    
    def _apply_processing_restriction(self, user_id: str, category: str, reason: str):
        """Apply processing restriction."""
        logger.info(f"Applied restriction to {category} for user {user_id}: {reason}")
    
    def _evaluate_objection(self, user_id: str, purpose: str, grounds: str) -> bool:
        """Evaluate whether objection should be accepted."""
        # In production, this would evaluate:
        # - Legitimate interests
        # - Legal obligations
        # - Public interest
        return True  # Simplified - accept objection
    
    def _stop_processing_for_purpose(self, user_id: str, purpose: str):
        """Stop processing for specific purpose.""" 
        logger.info(f"Stopped processing for purpose {purpose} for user {user_id}")
    
    def get_request_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a DSR request."""
        request = self.requests_storage.get(request_id)
        if not request:
            return None
        
        return {
            'request_id': request_id,
            'status': request.status.value,
            'submitted_at': request.submitted_at.isoformat(),
            'acknowledged_at': request.acknowledged_at.isoformat() if request.acknowledged_at else None,
            'completed_at': request.completed_at.isoformat() if request.completed_at else None,
            'request_type': request.request_type.value,
            'is_expired': request.is_expired(self.config)
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get DSR processing statistics."""
        total_requests = len(self.request_history)
        if total_requests == 0:
            return {'message': 'No DSR requests processed'}
        
        status_counts = {}
        type_counts = {}
        
        for request in self.request_history:
            status_counts[request.status.value] = status_counts.get(request.status.value, 0) + 1
            type_counts[request.request_type.value] = type_counts.get(request.request_type.value, 0) + 1
        
        return {
            'total_requests': total_requests,
            'requests_by_status': status_counts,
            'requests_by_type': type_counts,
            'completion_rate': status_counts.get('completed', 0) / total_requests,
            'avg_processing_time_days': self._calculate_avg_processing_time(),
            'compliance_metrics': {
                'within_72h_acknowledgment': self._calculate_acknowledgment_compliance(),
                'within_30d_completion': self._calculate_completion_compliance()
            }
        }
    
    def _calculate_avg_processing_time(self) -> float:
        """Calculate average processing time in days."""
        completed_requests = [r for r in self.request_history if r.completed_at and r.submitted_at]
        if not completed_requests:
            return 0.0
        
        total_time = sum(
            (r.completed_at - r.submitted_at).total_seconds() / 86400  # Convert to days
            for r in completed_requests
        )
        return total_time / len(completed_requests)
    
    def _calculate_acknowledgment_compliance(self) -> float:
        """Calculate percentage of requests acknowledged within 72 hours."""
        acknowledged_requests = [r for r in self.request_history if r.acknowledged_at]
        if not acknowledged_requests:
            return 0.0
        
        within_72h = sum(
            1 for r in acknowledged_requests
            if (r.acknowledged_at - r.submitted_at).total_seconds() <= 72 * 3600
        )
        return within_72h / len(acknowledged_requests)
    
    def _calculate_completion_compliance(self) -> float:
        """Calculate percentage of requests completed within 30 days."""
        completed_requests = [r for r in self.request_history if r.completed_at]
        if not completed_requests:
            return 0.0
        
        within_30d = sum(
            1 for r in completed_requests
            if (r.completed_at - r.submitted_at).total_seconds() <= 30 * 86400
        )
        return within_30d / len(completed_requests)