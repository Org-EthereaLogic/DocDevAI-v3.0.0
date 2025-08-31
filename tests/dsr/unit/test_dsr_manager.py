"""
Unit tests for DSR Manager - Core GDPR workflow orchestration.

Tests comprehensive DSR request processing including:
- Request submission and validation
- Identity verification workflow
- Data discovery coordination
- DSR operation processing (all GDPR articles)
- Completion verification
- Audit trail integrity
- Timeline compliance (30-day GDPR requirement)
- Error handling and recovery
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from devdocai.dsr.core.dsr_manager import (
    DSRManager, DSRRequest, DSRType, DSRStatus, DSRPriority
)
from devdocai.core.config import ConfigurationManager


@pytest.fixture
async def config_manager():
    """Mock configuration manager for testing."""
    config = Mock(spec=ConfigurationManager)
    config.get_encryption_key = Mock(return_value="test_encryption_key_32_bytes_long!")
    return config


@pytest.fixture  
async def dsr_manager(config_manager):
    """Initialize DSR Manager for testing."""
    manager = DSRManager(config_manager)
    await manager.initialize_modules()
    return manager


@pytest.fixture
def sample_dsr_request():
    """Sample DSR request for testing."""
    return DSRRequest(
        user_id="test_user_123",
        user_email="test@example.com",
        dsr_type=DSRType.ACCESS,
        description="Test data access request",
        priority=DSRPriority.NORMAL
    )


class TestDSRRequestModel:
    """Test DSR request data model."""
    
    def test_dsr_request_creation(self):
        """Test DSR request creation with default values."""
        request = DSRRequest(
            user_id="user_123",
            user_email="user@test.com",
            dsr_type=DSRType.ACCESS
        )
        
        assert request.user_id == "user_123"
        assert request.user_email == "user@test.com"
        assert request.dsr_type == DSRType.ACCESS
        assert request.status == DSRStatus.INITIATED
        assert request.priority == DSRPriority.NORMAL
        assert len(request.request_id) > 0
        assert request.created_at <= datetime.utcnow()
        assert request.deadline > datetime.utcnow()
        assert request.audit_trail == []
    
    def test_audit_trail_functionality(self):
        """Test audit trail with hash chain integrity."""
        request = DSRRequest(user_id="test_user", user_email="test@test.com")
        
        # Add first audit entry
        request.add_audit_entry("request_submitted", {"details": "test"})
        assert len(request.audit_trail) == 1
        
        first_entry = request.audit_trail[0]
        assert first_entry["action"] == "request_submitted"
        assert first_entry["details"] == {"details": "test"}
        assert first_entry["prev_hash"] == ""
        assert len(first_entry["hash"]) == 64  # SHA-256 hex
        
        # Add second audit entry
        request.add_audit_entry("identity_verified", {"method": "email"})
        assert len(request.audit_trail) == 2
        
        second_entry = request.audit_trail[1]
        assert second_entry["prev_hash"] == first_entry["hash"]
        assert second_entry["hash"] != first_entry["hash"]
    
    def test_deadline_management(self):
        """Test GDPR 30-day deadline management."""
        request = DSRRequest(user_id="test_user", user_email="test@test.com")
        
        # Should not be approaching deadline initially (30 days)
        assert not request.is_approaching_deadline(10)
        assert request.days_until_deadline() >= 29
        
        # Simulate approaching deadline
        request.deadline = datetime.utcnow() + timedelta(days=5)
        assert request.is_approaching_deadline(10)
        assert request.days_until_deadline() <= 5


class TestDSRManagerCore:
    """Test core DSR Manager functionality."""
    
    @pytest.mark.asyncio
    async def test_dsr_manager_initialization(self, config_manager):
        """Test DSR Manager initialization."""
        manager = DSRManager(config_manager)
        
        assert manager.config_manager == config_manager
        assert manager.active_requests == {}
        assert manager.processing_stats["total_requests"] == 0
        assert manager.max_concurrent_requests == 10
        assert manager.identity_verification_required is True
        assert manager.audit_logging_enabled is True
    
    @pytest.mark.asyncio
    async def test_module_initialization(self, dsr_manager):
        """Test DocDevAI module integration."""
        # Should initialize without errors
        assert dsr_manager.storage_system is not None
        assert dsr_manager.miair_engine is not None
        assert dsr_manager.pii_detector is not None
    
    @pytest.mark.asyncio
    async def test_submit_dsr_request(self, dsr_manager):
        """Test DSR request submission."""
        request_id = await dsr_manager.submit_dsr_request(
            user_id="test_user_123",
            user_email="test@example.com",
            dsr_type=DSRType.ACCESS,
            description="Test access request",
            priority=DSRPriority.NORMAL
        )
        
        # Verify request was created and tracked
        assert request_id in dsr_manager.active_requests
        request = dsr_manager.active_requests[request_id]
        
        assert request.user_id == "test_user_123"
        assert request.user_email == "test@example.com"
        assert request.dsr_type == DSRType.ACCESS
        assert request.status == DSRStatus.INITIATED
        assert len(request.audit_trail) == 1
        assert request.audit_trail[0]["action"] == "request_submitted"
        
        # Verify statistics updated
        assert dsr_manager.processing_stats["total_requests"] == 1
    
    @pytest.mark.asyncio
    async def test_request_status_retrieval(self, dsr_manager):
        """Test DSR request status retrieval."""
        # Submit a request
        request_id = await dsr_manager.submit_dsr_request(
            user_id="test_user",
            user_email="test@example.com",
            dsr_type=DSRType.ERASURE
        )
        
        # Get status
        status = await dsr_manager.get_request_status(request_id)
        
        assert status is not None
        assert status["request_id"] == request_id
        assert status["status"] == DSRStatus.INITIATED.value
        assert status["dsr_type"] == DSRType.ERASURE.value
        assert "days_until_deadline" in status
        assert "processing_results" in status
        
        # Test non-existent request
        nonexistent_status = await dsr_manager.get_request_status("nonexistent_id")
        assert nonexistent_status is None


class TestDSRWorkflowProcessing:
    """Test complete DSR workflow processing."""
    
    @pytest.mark.asyncio
    async def test_identity_verification_placeholder(self, dsr_manager, sample_dsr_request):
        """Test identity verification workflow."""
        # Test the placeholder implementation
        result = await dsr_manager._verify_identity(sample_dsr_request)
        
        assert result is True
        assert sample_dsr_request.status == DSRStatus.IDENTITY_VERIFIED
        assert sample_dsr_request.identity_verified is True
        assert sample_dsr_request.verification_method == "multi_factor"
        assert sample_dsr_request.risk_score == 0.1
        
        # Check audit trail
        verification_entries = [
            entry for entry in sample_dsr_request.audit_trail 
            if "identity" in entry["action"]
        ]
        assert len(verification_entries) >= 2  # Started and verified
    
    @pytest.mark.asyncio  
    async def test_data_discovery_placeholder(self, dsr_manager, sample_dsr_request):
        """Test data discovery workflow."""
        result = await dsr_manager._discover_user_data(sample_dsr_request)
        
        assert result is True
        assert sample_dsr_request.status == DSRStatus.DATA_DISCOVERED
        assert "documents" in sample_dsr_request.discovered_data
        assert "configurations" in sample_dsr_request.discovered_data
        assert "total_size_bytes" in sample_dsr_request.discovered_data
    
    @pytest.mark.asyncio
    async def test_access_request_processing(self, dsr_manager):
        """Test GDPR Article 15 - Right of Access processing."""
        request = DSRRequest(
            user_id="test_user",
            user_email="test@test.com", 
            dsr_type=DSRType.ACCESS
        )
        
        result = await dsr_manager._process_access_request(request)
        
        assert result is True
        assert "export_format" in request.processing_results
        assert request.processing_results["export_format"] == "json"
        assert request.processing_results["encryption"] == "aes_256_gcm_user_key"
        assert request.export_file_path is not None
        
        # Check audit trail
        audit_actions = [entry["action"] for entry in request.audit_trail]
        assert "access_request_processed" in audit_actions
    
    @pytest.mark.asyncio
    async def test_erasure_request_processing(self, dsr_manager):
        """Test GDPR Article 17 - Right to Erasure processing."""
        request = DSRRequest(
            user_id="test_user",
            user_email="test@test.com",
            dsr_type=DSRType.ERASURE
        )
        
        result = await dsr_manager._process_erasure_request(request)
        
        assert result is True
        assert "deletion_method" in request.processing_results
        assert request.processing_results["deletion_method"] == "dod_5220_22_m"
        assert request.processing_results["verification_method"] == "cryptographic_proof"
        assert request.deletion_certificate is not None
    
    @pytest.mark.asyncio
    async def test_rectification_request_processing(self, dsr_manager):
        """Test GDPR Article 16 - Right to Rectification processing.""" 
        request = DSRRequest(
            user_id="test_user",
            user_email="test@test.com",
            dsr_type=DSRType.RECTIFICATION
        )
        
        result = await dsr_manager._process_rectification_request(request)
        
        assert result is True
        assert request.processing_results["audit_trail_updated"] is True
        assert request.processing_results["version_control"] is True
    
    @pytest.mark.asyncio
    async def test_complete_workflow_processing(self, dsr_manager):
        """Test complete DSR workflow from submission to completion."""
        request = DSRRequest(
            user_id="test_complete_user",
            user_email="complete@test.com",
            dsr_type=DSRType.ACCESS
        )
        
        # Process complete workflow
        result = await dsr_manager.process_dsr_request(request)
        
        assert result is True
        assert request.status == DSRStatus.COMPLETED
        assert request.completed_at is not None
        assert request.identity_verified is True
        assert len(request.discovered_data) > 0
        assert len(request.processing_results) > 0
        
        # Verify audit trail completeness
        audit_actions = [entry["action"] for entry in request.audit_trail]
        expected_actions = [
            "identity_verification_started",
            "identity_verified", 
            "data_discovery_started",
            "data_discovery_completed",
            "dsr_processing_started",
            "access_request_processed",
            "completion_verification_started", 
            "completion_verified",
            "request_completed"
        ]
        
        for action in expected_actions:
            assert action in audit_actions


class TestDSRStatisticsAndMonitoring:
    """Test DSR processing statistics and monitoring."""
    
    @pytest.mark.asyncio
    async def test_processing_statistics(self, dsr_manager):
        """Test DSR processing statistics collection."""
        initial_stats = await dsr_manager.get_processing_statistics()
        
        assert "total_requests" in initial_stats
        assert "successful_requests" in initial_stats 
        assert "failed_requests" in initial_stats
        assert "average_completion_time" in initial_stats
        assert "timeline_compliance_rate" in initial_stats
        assert initial_stats["active_requests"] == 0
    
    @pytest.mark.asyncio
    async def test_timeline_compliance_calculation(self, dsr_manager):
        """Test GDPR 30-day timeline compliance calculation."""
        # Create completed request within deadline
        request1 = DSRRequest(user_id="user1", user_email="user1@test.com")
        request1.status = DSRStatus.COMPLETED
        request1.completed_at = datetime.utcnow()
        dsr_manager.active_requests["req1"] = request1
        
        # Create completed request past deadline  
        request2 = DSRRequest(user_id="user2", user_email="user2@test.com")
        request2.status = DSRStatus.COMPLETED
        request2.deadline = datetime.utcnow() - timedelta(days=5)  # Past deadline
        request2.completed_at = datetime.utcnow()
        dsr_manager.active_requests["req2"] = request2
        
        # Calculate compliance rate
        compliance_rate = dsr_manager._calculate_timeline_compliance_rate()
        assert compliance_rate == 0.5  # 1 out of 2 requests compliant
    
    @pytest.mark.asyncio
    async def test_average_completion_time_calculation(self, dsr_manager):
        """Test average completion time calculation.""" 
        # Simulate completion times
        dsr_manager.processing_stats["completed_requests"] = 0
        dsr_manager.processing_stats["average_completion_time"] = 0.0
        
        # Add first completion time
        dsr_manager.processing_stats["completed_requests"] = 1
        dsr_manager._update_average_completion_time(120.0)  # 2 minutes
        assert dsr_manager.processing_stats["average_completion_time"] == 120.0
        
        # Add second completion time
        dsr_manager.processing_stats["completed_requests"] = 2
        dsr_manager._update_average_completion_time(180.0)  # 3 minutes  
        assert dsr_manager.processing_stats["average_completion_time"] == 150.0  # Average


class TestDSRErrorHandling:
    """Test DSR error handling and recovery."""
    
    @pytest.mark.asyncio
    async def test_data_discovery_error_handling(self, dsr_manager):
        """Test error handling during data discovery."""
        request = DSRRequest(user_id="error_user", user_email="error@test.com")
        
        # Mock data discovery to raise an exception
        with patch.object(dsr_manager, '_discover_user_data') as mock_discovery:
            mock_discovery.side_effect = Exception("Data discovery failed")
            
            result = await dsr_manager.process_dsr_request(request)
            
            assert result is False
            assert request.status == DSRStatus.PROCESSING_ERROR
            assert "Processing error" in request.error_messages[0]
            
            # Verify error logged in audit trail
            error_entries = [
                entry for entry in request.audit_trail 
                if "error" in entry["action"]
            ]
            assert len(error_entries) > 0
    
    @pytest.mark.asyncio 
    async def test_identity_verification_failure(self, dsr_manager):
        """Test identity verification failure handling."""
        request = DSRRequest(user_id="fail_user", user_email="fail@test.com")
        
        # Mock identity verification to fail
        with patch.object(dsr_manager, '_verify_identity') as mock_verify:
            mock_verify.return_value = False
            
            result = await dsr_manager.process_dsr_request(request)
            
            assert result is False
            # Request should not proceed past identity verification
    
    @pytest.mark.asyncio
    async def test_processing_retry_logic(self, dsr_manager):
        """Test DSR processing retry logic."""
        request = DSRRequest(user_id="retry_user", user_email="retry@test.com")
        
        # Verify retry counter initialization
        assert request.retry_count == 0
        assert request.max_retries == 3
        
        # Test retry increment (would be used in actual retry logic)
        request.retry_count += 1
        assert request.retry_count == 1
        assert request.retry_count < request.max_retries


class TestGDPRComplianceValidation:
    """Test GDPR compliance validation."""
    
    @pytest.mark.asyncio
    async def test_all_gdpr_article_support(self, dsr_manager):
        """Test support for all GDPR articles (15-21)."""
        gdpr_articles = [
            (DSRType.ACCESS, "Article 15 - Right of Access"),
            (DSRType.RECTIFICATION, "Article 16 - Right to Rectification"),
            (DSRType.ERASURE, "Article 17 - Right to Erasure"), 
            (DSRType.RESTRICTION, "Article 18 - Right to Restriction"),
            (DSRType.PORTABILITY, "Article 20 - Right to Data Portability"),
            (DSRType.OBJECTION, "Article 21 - Right to Object")
        ]
        
        for dsr_type, article_name in gdpr_articles:
            request = DSRRequest(
                user_id=f"gdpr_{dsr_type.value}_user",
                user_email=f"{dsr_type.value}@test.com",
                dsr_type=dsr_type
            )
            
            # Process specific DSR type
            result = await dsr_manager._process_dsr_operation(request)
            
            assert result is True, f"Failed to process {article_name}"
            assert request.status == DSRStatus.PROCESSING  # Should be in processing after operation
            assert len(request.processing_results) > 0
    
    @pytest.mark.asyncio
    async def test_audit_trail_gdpr_compliance(self, dsr_manager):
        """Test audit trail meets GDPR compliance requirements."""
        request = DSRRequest(user_id="audit_user", user_email="audit@test.com")
        
        # Process complete request
        await dsr_manager.process_dsr_request(request)
        
        # Verify audit trail completeness
        assert len(request.audit_trail) >= 5  # Multiple audit entries
        
        # Verify required audit information
        for entry in request.audit_trail:
            assert "timestamp" in entry
            assert "action" in entry
            assert "request_id" in entry 
            assert "status" in entry
            assert "hash" in entry  # Hash chain integrity
            
            # Verify timestamp format (ISO format)
            datetime.fromisoformat(entry["timestamp"])
    
    @pytest.mark.asyncio
    async def test_30_day_deadline_compliance(self, dsr_manager):
        """Test GDPR 30-day deadline compliance."""
        request = DSRRequest(user_id="deadline_user", user_email="deadline@test.com")
        
        # Verify deadline is set correctly (30 days from creation)
        expected_deadline = request.created_at + timedelta(days=30)
        time_diff = abs((request.deadline - expected_deadline).total_seconds())
        assert time_diff < 60  # Within 1 minute of expected
        
        # Test deadline warning system
        request.deadline = datetime.utcnow() + timedelta(days=5)
        assert request.is_approaching_deadline(10)  # 10-day warning
        assert request.days_until_deadline() <= 5


if __name__ == "__main__":
    # Run tests with proper async support
    pytest.main([__file__, "-v", "--tb=short"])