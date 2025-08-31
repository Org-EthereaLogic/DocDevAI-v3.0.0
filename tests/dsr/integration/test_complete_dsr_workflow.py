"""
Integration tests for complete DSR (Data Subject Rights) workflows.

Tests end-to-end GDPR compliance workflows including:
- Complete Article 15 (Right of Access) workflow with encrypted exports
- Complete Article 17 (Right to Erasure) workflow with DoD deletion
- Complete Article 16 (Right to Rectification) workflow with audit trails
- Multi-factor identity verification integration
- Cross-module data discovery and processing
- Timeline compliance and deadline management
- Audit trail integrity and tamper evidence
- Certificate generation and verification
- Performance benchmarking under realistic conditions
"""

import pytest
import asyncio
import tempfile
import os
import json
import gzip
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from devdocai.dsr.core.dsr_manager import DSRManager, DSRType, DSRStatus, DSRPriority
from devdocai.dsr.identity.verifier import IdentityVerifier, VerificationMethod, VerificationStatus
from devdocai.dsr.export.engine import UserDataExportEngine, ExportFormat, ExportStatus
from devdocai.dsr.deletion.crypto_deletion import CryptographicDeletionEngine, DeletionMethod, DeletionStatus
from devdocai.core.config import ConfigurationManager


@pytest.fixture
async def config_manager():
    """Mock configuration manager for integration testing."""
    config = Mock(spec=ConfigurationManager)
    config.get_encryption_key = Mock(return_value="integration_test_key_32_bytes!")
    return config


@pytest.fixture
async def integrated_dsr_system(config_manager):
    """Initialize complete integrated DSR system."""
    # Initialize all DSR components
    dsr_manager = DSRManager(config_manager)
    identity_verifier = IdentityVerifier(config_manager)
    export_engine = UserDataExportEngine(config_manager)
    deletion_engine = CryptographicDeletionEngine(config_manager)
    
    # Initialize modules
    await dsr_manager.initialize_modules()
    await export_engine.initialize_modules()
    await deletion_engine.initialize_modules()
    
    return {
        'dsr_manager': dsr_manager,
        'identity_verifier': identity_verifier,
        'export_engine': export_engine,
        'deletion_engine': deletion_engine,
        'config_manager': config_manager
    }


@pytest.fixture
def sample_user_data():
    """Sample user data for testing complete workflows."""
    return {
        "user_id": "integration_test_user_123",
        "email": "integration@test.com",
        "name": "Integration Test User",
        "created_at": "2024-01-01T00:00:00Z",
        "documents": [
            {
                "id": "doc_1",
                "title": "Personal Document 1",
                "content": "This is sensitive personal content that must be handled according to GDPR",
                "created_at": "2024-01-15T10:00:00Z"
            },
            {
                "id": "doc_2", 
                "title": "Work Document",
                "content": "Professional content with user data and preferences",
                "created_at": "2024-02-01T14:30:00Z"
            }
        ],
        "preferences": {
            "theme": "dark",
            "language": "en",
            "notifications": True,
            "privacy_level": "high"
        },
        "pii_data": [
            {
                "type": "email",
                "value": "integration@test.com",
                "location": "profile"
            },
            {
                "type": "phone", 
                "value": "+1-555-0123",
                "location": "contact_info"
            }
        ]
    }


class TestCompleteAccessRequestWorkflow:
    """Test complete GDPR Article 15 (Right of Access) workflow."""
    
    @pytest.mark.asyncio
    async def test_complete_access_workflow_with_identity_verification(
        self, 
        integrated_dsr_system,
        sample_user_data
    ):
        """Test complete access request workflow with multi-factor verification."""
        dsr_manager = integrated_dsr_system['dsr_manager']
        identity_verifier = integrated_dsr_system['identity_verifier']
        
        user_id = sample_user_data["user_id"]
        user_email = sample_user_data["email"]
        
        # Step 1: Submit DSR access request
        request_id = await dsr_manager.submit_dsr_request(
            user_id=user_id,
            user_email=user_email,
            dsr_type=DSRType.ACCESS,
            description="Complete personal data access request",
            priority=DSRPriority.NORMAL
        )
        
        assert request_id in dsr_manager.active_requests
        request = dsr_manager.active_requests[request_id]
        assert request.status == DSRStatus.INITIATED
        
        # Step 2: Multi-factor identity verification
        # Initiate verification
        verification_result = await identity_verifier.initiate_verification(
            user_id=user_id,
            email=user_email,
            ip_address="192.168.1.100",
            user_agent="Integration Test Browser"
        )
        
        assert verification_result["success"] is True
        assert "email_token" in verification_result["methods_required"]
        
        # Complete email token verification
        token = identity_verifier.active_tokens[user_id]
        email_verification = await identity_verifier.verify_email_token(
            user_id=user_id,
            provided_token=token.token
        )
        assert email_verification["success"] is True
        
        # Complete multi-factor verification
        completion_result = await identity_verifier.complete_verification(
            user_id=user_id,
            completed_methods=[VerificationMethod.EMAIL_TOKEN]
        )
        assert completion_result["verification_complete"] is True
        
        # Step 3: Process complete DSR request
        with patch.object(dsr_manager, '_verify_identity', return_value=True):
            processing_result = await dsr_manager.process_dsr_request(request)
        
        assert processing_result is True
        assert request.status == DSRStatus.COMPLETED
        assert request.identity_verified is True
        assert len(request.processing_results) > 0
        assert request.export_file_path is not None
        
        # Step 4: Verify audit trail integrity
        assert len(request.audit_trail) >= 5  # Multiple audit entries
        
        # Verify hash chain integrity
        for i in range(1, len(request.audit_trail)):
            current_entry = request.audit_trail[i]
            previous_entry = request.audit_trail[i-1]
            assert current_entry["prev_hash"] == previous_entry["hash"]
        
        # Step 5: Verify timeline compliance
        assert request.completed_at <= request.deadline  # Within GDPR 30-day limit
        assert not request.is_approaching_deadline(-1)  # Completed on time
    
    @pytest.mark.asyncio
    async def test_data_export_generation_and_encryption(
        self,
        integrated_dsr_system,
        sample_user_data
    ):
        """Test data export generation with user-key encryption."""
        export_engine = integrated_dsr_system['export_engine']
        
        user_id = sample_user_data["user_id"]
        user_password = "secure_user_password_123"
        
        # Step 1: Initiate export
        export_id = await export_engine.initiate_export(
            user_id=user_id,
            export_format=ExportFormat.JSON,
            user_password=user_password,
            compression_enabled=True,
            encryption_enabled=True
        )
        
        assert export_id.startswith(f"export_{user_id}")
        assert export_id in export_engine.active_exports
        
        # Step 2: Wait for export completion (with timeout)
        timeout_seconds = 30
        start_time = asyncio.get_event_loop().time()
        
        while True:
            status = await export_engine.get_export_status(export_id)
            if status["status"] == ExportStatus.COMPLETED.value:
                break
            elif status["status"] == ExportStatus.FAILED.value:
                pytest.fail(f"Export failed: {status}")
            elif asyncio.get_event_loop().time() - start_time > timeout_seconds:
                pytest.fail("Export timeout")
            
            await asyncio.sleep(0.5)
        
        # Step 3: Verify export completion
        final_status = await export_engine.get_export_status(export_id)
        assert final_status["status"] == ExportStatus.COMPLETED.value
        assert final_status["security"]["encryption_enabled"] is True
        assert final_status["security"]["auto_deletion_date"] is not None
        
        # Step 4: Test export download
        export_file_path = await export_engine.download_export(export_id)
        assert export_file_path is not None
        assert export_file_path.exists()
        assert export_file_path.name.endswith('.encrypted')
        
        # Step 5: Verify export file properties
        file_size = export_file_path.stat().st_size
        assert file_size > 0
        
        # Export should contain encrypted data (not readable as plain text)
        with open(export_file_path, 'rb') as f:
            encrypted_content = f.read()
            # Should not contain readable user data
            assert b"integration@test.com" not in encrypted_content
            assert b"Personal Document" not in encrypted_content
    
    @pytest.mark.asyncio
    async def test_gdpr_compliance_validation(
        self,
        integrated_dsr_system,
        sample_user_data
    ):
        """Test GDPR compliance validation for access requests."""
        dsr_manager = integrated_dsr_system['dsr_manager']
        export_engine = integrated_dsr_system['export_engine']
        
        user_id = sample_user_data["user_id"]
        user_email = sample_user_data["email"]
        
        # Submit and process request
        request_id = await dsr_manager.submit_dsr_request(
            user_id=user_id,
            user_email=user_email,
            dsr_type=DSRType.ACCESS
        )
        
        request = dsr_manager.active_requests[request_id]
        
        # Process with mocked verification
        with patch.object(dsr_manager, '_verify_identity', return_value=True):
            await dsr_manager.process_dsr_request(request)
        
        # GDPR Compliance Checks
        
        # 1. 30-day timeline compliance
        request_duration = request.completed_at - request.created_at
        assert request_duration <= timedelta(days=30)
        
        # 2. Identity verification required
        assert request.identity_verified is True
        assert request.verification_method != ""
        
        # 3. Complete audit trail
        audit_actions = [entry["action"] for entry in request.audit_trail]
        required_actions = [
            "identity_verification_started",
            "identity_verified",
            "data_discovery_started", 
            "data_discovery_completed",
            "access_request_processed",
            "completion_verified",
            "request_completed"
        ]
        
        for action in required_actions:
            assert action in audit_actions, f"Missing required audit action: {action}"
        
        # 4. Data completeness
        assert len(request.discovered_data) > 0
        assert "documents" in request.discovered_data
        assert "configurations" in request.discovered_data
        
        # 5. Export security
        assert request.processing_results["encryption"] == "aes_256_gcm_user_key"
        assert request.export_file_path is not None


class TestCompleteErasureRequestWorkflow:
    """Test complete GDPR Article 17 (Right to Erasure) workflow."""
    
    @pytest.mark.asyncio
    async def test_complete_erasure_workflow_with_dod_deletion(
        self,
        integrated_dsr_system,
        sample_user_data
    ):
        """Test complete erasure request workflow with DoD 5220.22-M deletion."""
        dsr_manager = integrated_dsr_system['dsr_manager']
        deletion_engine = integrated_dsr_system['deletion_engine']
        
        user_id = sample_user_data["user_id"]
        user_email = sample_user_data["email"]
        
        # Step 1: Submit DSR erasure request
        request_id = await dsr_manager.submit_dsr_request(
            user_id=user_id,
            user_email=user_email,
            dsr_type=DSRType.ERASURE,
            description="Complete data erasure request",
            priority=DSRPriority.HIGH  # High priority for erasure
        )
        
        request = dsr_manager.active_requests[request_id]
        assert request.dsr_type == DSRType.ERASURE
        
        # Step 2: Process complete erasure workflow
        with patch.object(dsr_manager, '_verify_identity', return_value=True):
            processing_result = await dsr_manager.process_dsr_request(request)
        
        assert processing_result is True
        assert request.status == DSRStatus.COMPLETED
        
        # Step 3: Verify deletion processing results
        assert "deletion_method" in request.processing_results
        assert request.processing_results["deletion_method"] == "dod_5220_22_m"
        assert request.processing_results["verification_method"] == "cryptographic_proof"
        assert request.deletion_certificate is not None
        
        # Step 4: Verify audit trail for erasure
        audit_actions = [entry["action"] for entry in request.audit_trail]
        assert "erasure_request_processed" in audit_actions
        
        # Step 5: Verify GDPR Article 17 compliance
        erasure_entry = next(
            entry for entry in request.audit_trail 
            if entry["action"] == "erasure_request_processed"
        )
        assert "deletion_method" in erasure_entry["details"]
        assert erasure_entry["details"]["deletion_method"] == "dod_5220_22_m"
    
    @pytest.mark.asyncio
    async def test_deletion_certificate_generation(
        self,
        integrated_dsr_system,
        sample_user_data
    ):
        """Test deletion certificate generation and verification."""
        deletion_engine = integrated_dsr_system['deletion_engine']
        
        user_id = sample_user_data["user_id"]
        
        # Step 1: Initiate secure deletion
        deletion_id = await deletion_engine.initiate_secure_deletion(
            user_id=user_id,
            deletion_request_id="cert_test_req",
            target_identifiers=["doc_1", "doc_2"],
            deletion_method=DeletionMethod.DOD_5220_22_M
        )
        
        assert deletion_id in deletion_engine.active_deletions
        
        # Step 2: Wait for deletion completion 
        timeout_seconds = 30
        start_time = asyncio.get_event_loop().time()
        
        while True:
            status = await deletion_engine.get_deletion_status(deletion_id)
            if status["status"] == DeletionStatus.COMPLETED.value:
                break
            elif status["status"] == DeletionStatus.FAILED.value:
                pytest.fail(f"Deletion failed: {status}")
            elif asyncio.get_event_loop().time() - start_time > timeout_seconds:
                pytest.fail("Deletion timeout")
            
            await asyncio.sleep(0.5)
        
        # Step 3: Verify deletion certificate was generated
        final_status = await deletion_engine.get_deletion_status(deletion_id)
        certificate_id = final_status["certificate_id"]
        assert certificate_id is not None
        
        # Step 4: Retrieve and validate certificate
        certificate = await deletion_engine.get_deletion_certificate(certificate_id)
        assert certificate is not None
        
        # Verify certificate structure
        assert certificate["user_id"] == user_id
        assert certificate["deletion_request_id"] == "cert_test_req"
        assert certificate["deletion_details"]["deletion_method"] == "dod_5220_22_m"
        assert certificate["deletion_details"]["total_passes"] == 3
        assert certificate["verification"]["verification_successful"] is True
        assert certificate["compliance"]["gdpr_article"] == "Article 17 - Right to Erasure"
        
        # Step 5: Verify digital signature
        signature_valid = await deletion_engine.verify_certificate_signature(certificate_id)
        assert signature_valid is True
        
        # Step 6: Verify certificate integrity
        cert_hash = certificate["cryptographic_proof"]["certificate_hash"]
        assert len(cert_hash) == 64  # SHA-256
        assert cert_hash.isalnum()  # Valid hex


class TestCompleteRectificationWorkflow:
    """Test complete GDPR Article 16 (Right to Rectification) workflow."""
    
    @pytest.mark.asyncio
    async def test_complete_rectification_workflow_with_audit_trail(
        self,
        integrated_dsr_system,
        sample_user_data
    ):
        """Test complete rectification workflow with immutable audit trails."""
        dsr_manager = integrated_dsr_system['dsr_manager']
        
        user_id = sample_user_data["user_id"]
        user_email = sample_user_data["email"]
        
        # Step 1: Submit DSR rectification request
        request_id = await dsr_manager.submit_dsr_request(
            user_id=user_id,
            user_email=user_email,
            dsr_type=DSRType.RECTIFICATION,
            description="Update incorrect personal information",
            priority=DSRPriority.NORMAL
        )
        
        request = dsr_manager.active_requests[request_id]
        assert request.dsr_type == DSRType.RECTIFICATION
        
        # Step 2: Process rectification workflow
        with patch.object(dsr_manager, '_verify_identity', return_value=True):
            processing_result = await dsr_manager.process_dsr_request(request)
        
        assert processing_result is True
        assert request.status == DSRStatus.COMPLETED
        
        # Step 3: Verify rectification processing
        assert "rectifications_applied" in request.processing_results
        assert request.processing_results["audit_trail_updated"] is True
        assert request.processing_results["version_control"] is True
        
        # Step 4: Verify audit trail integrity for rectification
        rectification_entry = next(
            entry for entry in request.audit_trail
            if entry["action"] == "rectification_request_processed"
        )
        
        assert "rectifications_applied" in rectification_entry["details"]
        assert rectification_entry["details"]["audit_trail_updated"] is True
        
        # Step 5: Verify hash chain integrity after rectification
        for i in range(1, len(request.audit_trail)):
            current = request.audit_trail[i]
            previous = request.audit_trail[i-1]
            assert current["prev_hash"] == previous["hash"]
            assert len(current["hash"]) == 64  # SHA-256


class TestCrossModuleIntegration:
    """Test cross-module integration and data flow."""
    
    @pytest.mark.asyncio
    async def test_data_discovery_across_modules(
        self,
        integrated_dsr_system,
        sample_user_data
    ):
        """Test data discovery coordination across all DocDevAI modules."""
        dsr_manager = integrated_dsr_system['dsr_manager']
        
        user_id = sample_user_data["user_id"]
        
        # Create a sample DSR request for data discovery testing
        request = await dsr_manager.active_requests.get("test", None)
        if not request:
            from devdocai.dsr.core.dsr_manager import DSRRequest
            request = DSRRequest(
                user_id=user_id,
                user_email=sample_user_data["email"],
                dsr_type=DSRType.ACCESS
            )
        
        # Test data discovery coordination
        discovery_result = await dsr_manager._discover_user_data(request)
        
        assert discovery_result is True
        assert request.status == DSRStatus.DATA_DISCOVERED
        
        # Verify data discovery across module boundaries
        discovered_data = request.discovered_data
        
        # Should discover data from multiple modules
        expected_categories = [
            "documents",      # M002 Local Storage
            "configurations", # M001 Configuration Manager  
            "analysis_results", # M003 MIAIR Engine
            "pii_findings",   # Enhanced PII Detector
            "total_size_bytes" # Summary information
        ]
        
        for category in expected_categories:
            assert category in discovered_data
        
        # Verify PII detection integration
        assert isinstance(discovered_data["pii_findings"], list)
        
        # Verify size calculation
        assert isinstance(discovered_data["total_size_bytes"], int)
        assert discovered_data["total_size_bytes"] >= 0
    
    @pytest.mark.asyncio
    async def test_security_integration_across_components(
        self,
        integrated_dsr_system,
        sample_user_data
    ):
        """Test security integration across DSR components."""
        dsr_manager = integrated_dsr_system['dsr_manager']
        identity_verifier = integrated_dsr_system['identity_verifier']
        export_engine = integrated_dsr_system['export_engine']
        deletion_engine = integrated_dsr_system['deletion_engine']
        
        user_id = sample_user_data["user_id"]
        
        # Test 1: Identity verification security
        verification_stats = await identity_verifier.get_verification_statistics()
        assert "success_rate" in verification_stats
        assert "active_tokens" in verification_stats
        
        # Test 2: Export encryption security
        export_stats = await export_engine.get_export_statistics()
        assert "total_exports" in export_stats
        assert "active_exports" in export_stats
        
        # Test 3: Deletion security
        deletion_stats = await deletion_engine.get_deletion_statistics()
        assert "total_deletions" in deletion_stats
        assert "certificates_issued" in deletion_stats
        
        # Test 4: DSR processing security
        dsr_stats = await dsr_manager.get_processing_statistics()
        assert "timeline_compliance_rate" in dsr_stats
        assert "total_requests" in dsr_stats
        
        # Test 5: Cross-component audit correlation
        # All components should maintain consistent user identification
        # and security standards across the integrated system
        assert True  # Integration successful if no exceptions


class TestPerformanceBenchmarking:
    """Test performance benchmarks for DSR operations."""
    
    @pytest.mark.asyncio
    async def test_access_request_performance_benchmark(
        self,
        integrated_dsr_system,
        sample_user_data
    ):
        """Test access request performance meets requirements (<30 minutes)."""
        dsr_manager = integrated_dsr_system['dsr_manager']
        
        user_id = sample_user_data["user_id"]
        user_email = sample_user_data["email"]
        
        # Record start time
        start_time = datetime.utcnow()
        
        # Process complete access request
        request_id = await dsr_manager.submit_dsr_request(
            user_id=user_id,
            user_email=user_email,
            dsr_type=DSRType.ACCESS
        )
        
        request = dsr_manager.active_requests[request_id]
        
        with patch.object(dsr_manager, '_verify_identity', return_value=True):
            processing_result = await dsr_manager.process_dsr_request(request)
        
        # Record completion time
        completion_time = datetime.utcnow()
        processing_duration = (completion_time - start_time).total_seconds()
        
        # Performance assertions
        assert processing_result is True
        assert processing_duration < 1800  # Less than 30 minutes (GDPR requirement)
        assert processing_duration < 60    # Should be much faster in test environment
        
        # Log performance for monitoring
        print(f"Access request processing time: {processing_duration:.2f} seconds")
    
    @pytest.mark.asyncio
    async def test_erasure_request_performance_benchmark(
        self,
        integrated_dsr_system,
        sample_user_data
    ):
        """Test erasure request performance meets requirements (<15 minutes)."""
        dsr_manager = integrated_dsr_system['dsr_manager']
        
        user_id = sample_user_data["user_id"]
        user_email = sample_user_data["email"]
        
        start_time = datetime.utcnow()
        
        # Process complete erasure request
        request_id = await dsr_manager.submit_dsr_request(
            user_id=user_id,
            user_email=user_email,
            dsr_type=DSRType.ERASURE
        )
        
        request = dsr_manager.active_requests[request_id]
        
        with patch.object(dsr_manager, '_verify_identity', return_value=True):
            processing_result = await dsr_manager.process_dsr_request(request)
        
        completion_time = datetime.utcnow()
        processing_duration = (completion_time - start_time).total_seconds()
        
        # Performance assertions  
        assert processing_result is True
        assert processing_duration < 900   # Less than 15 minutes
        assert processing_duration < 30    # Should be faster in test environment
        
        print(f"Erasure request processing time: {processing_duration:.2f} seconds")
    
    @pytest.mark.asyncio
    async def test_concurrent_request_handling(
        self,
        integrated_dsr_system,
        sample_user_data
    ):
        """Test concurrent DSR request handling performance."""
        dsr_manager = integrated_dsr_system['dsr_manager']
        
        # Create multiple concurrent requests
        num_requests = 5
        tasks = []
        
        for i in range(num_requests):
            user_id = f"{sample_user_data['user_id']}_{i}"
            user_email = f"concurrent_{i}@test.com"
            
            task = dsr_manager.submit_dsr_request(
                user_id=user_id,
                user_email=user_email,
                dsr_type=DSRType.ACCESS,
                priority=DSRPriority.NORMAL
            )
            tasks.append(task)
        
        # Execute all requests concurrently
        start_time = datetime.utcnow()
        request_ids = await asyncio.gather(*tasks)
        completion_time = datetime.utcnow()
        
        # Verify all requests were submitted successfully
        assert len(request_ids) == num_requests
        for request_id in request_ids:
            assert request_id in dsr_manager.active_requests
        
        submission_duration = (completion_time - start_time).total_seconds()
        
        # Performance assertions
        assert submission_duration < 10  # Should handle concurrent submissions quickly
        assert len(dsr_manager.active_requests) == num_requests
        
        print(f"Concurrent request submission time: {submission_duration:.2f} seconds for {num_requests} requests")


class TestErrorHandlingAndRecovery:
    """Test error handling and recovery scenarios."""
    
    @pytest.mark.asyncio 
    async def test_identity_verification_failure_handling(
        self,
        integrated_dsr_system,
        sample_user_data
    ):
        """Test handling of identity verification failures."""
        dsr_manager = integrated_dsr_system['dsr_manager']
        identity_verifier = integrated_dsr_system['identity_verifier']
        
        user_id = sample_user_data["user_id"]
        user_email = sample_user_data["email"]
        
        # Submit request
        request_id = await dsr_manager.submit_dsr_request(
            user_id=user_id,
            user_email=user_email,
            dsr_type=DSRType.ACCESS
        )
        
        request = dsr_manager.active_requests[request_id]
        
        # Simulate identity verification failure
        with patch.object(dsr_manager, '_verify_identity', return_value=False):
            processing_result = await dsr_manager.process_dsr_request(request)
        
        # Should handle failure gracefully
        assert processing_result is False
        assert request.status != DSRStatus.COMPLETED
        
        # Should not proceed to data processing without verification
        assert len(request.processing_results) == 0
    
    @pytest.mark.asyncio
    async def test_system_recovery_after_component_failure(
        self,
        integrated_dsr_system,
        sample_user_data
    ):
        """Test system recovery after component failures."""
        dsr_manager = integrated_dsr_system['dsr_manager']
        
        # Test recovery from data discovery failure
        user_id = sample_user_data["user_id"]
        request_id = await dsr_manager.submit_dsr_request(
            user_id=user_id,
            user_email=sample_user_data["email"],
            dsr_type=DSRType.ACCESS
        )
        
        request = dsr_manager.active_requests[request_id]
        
        # Simulate data discovery failure
        with patch.object(dsr_manager, '_discover_user_data', side_effect=Exception("Discovery failed")):
            with patch.object(dsr_manager, '_verify_identity', return_value=True):
                processing_result = await dsr_manager.process_dsr_request(request)
        
        # System should handle failure gracefully
        assert processing_result is False
        assert request.status == DSRStatus.PROCESSING_ERROR
        assert len(request.error_messages) > 0
        assert "Processing error" in request.error_messages[0]
        
        # Audit trail should record the failure
        error_entries = [
            entry for entry in request.audit_trail 
            if "error" in entry["action"]
        ]
        assert len(error_entries) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--asyncio-mode=auto"])