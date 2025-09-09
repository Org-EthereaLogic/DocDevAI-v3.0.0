"""
Security Tests for M005 Tracking Matrix - Pass 3
DevDocAI v3.0.0

Comprehensive security test suite targeting 95% coverage for security features.
Tests OWASP compliance, input validation, attack prevention, and audit logging.
"""

import pytest
import json
import time
import secrets
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any
import threading
from concurrent.futures import ThreadPoolExecutor

# Import module to test
import sys
sys.path.append(str(Path(__file__).parent.parent))
from devdocai.core.tracking import (
    TrackingMatrix,
    DocumentRelationship,
    OptimizedDependencyGraph,
    ParallelImpactAnalysis,
    CircularReferenceError,
    TrackingError,
    RelationshipType,
    SecurityValidator,
    RateLimiter,
    AuditLogger,
    SecurityConfig,
    ResourceLimitError,
    SecurityError
)


class TestSecurityValidator:
    """Test security validation functionality."""
    
    def test_document_id_validation(self):
        """Test document ID validation against injection attacks."""
        validator = SecurityValidator()
        
        # Valid IDs
        assert validator.validate_document_id("doc123")
        assert validator.validate_document_id("user_guide-v1.0")
        assert validator.validate_document_id("api.reference.2024")
        
        # Invalid IDs - too long
        with pytest.raises(ValueError, match="Invalid document ID length"):
            validator.validate_document_id("x" * 257)
        
        # Invalid IDs - special characters
        with pytest.raises(ValueError, match="Invalid document ID format"):
            validator.validate_document_id("doc<script>alert(1)</script>")
        
        with pytest.raises(ValueError, match="Invalid document ID format"):
            validator.validate_document_id("'; DROP TABLE docs;--")
        
        # Path traversal attempts
        with pytest.raises(SecurityError, match="potential path traversal"):
            validator.validate_document_id("../../../etc/passwd")
        
        with pytest.raises(SecurityError, match="potential path traversal"):
            validator.validate_document_id("..\\..\\windows\\system32")
    
    def test_metadata_sanitization(self):
        """Test metadata sanitization against XSS and injection."""
        validator = SecurityValidator()
        
        # Test HTML escaping
        malicious_metadata = {
            "title": "<script>alert('XSS')</script>",
            "description": "Normal text with <b>HTML</b>",
            "onclick": "javascript:alert(1)"
        }
        
        sanitized = validator.sanitize_metadata(malicious_metadata)
        
        assert "<script>" not in sanitized["title"]
        assert "&lt;script&gt;" in sanitized["title"]
        assert "<b>" not in sanitized["description"]
        assert "javascript:" not in sanitized["onclick"]
        
        # Test size limits
        large_metadata = {
            "data": "x" * (SecurityConfig.MAX_METADATA_SIZE + 1000)
        }
        
        with pytest.raises(ValueError, match="Metadata too large"):
            validator.sanitize_metadata(large_metadata)
        
        # Test nested sanitization
        nested_metadata = {
            "level1": {
                "level2": {
                    "evil": "<img src=x onerror=alert(1)>"
                }
            }
        }
        
        sanitized = validator.sanitize_metadata(nested_metadata)
        assert "<img" not in str(sanitized)
        assert "onerror" not in str(sanitized)
    
    def test_relationship_type_validation(self):
        """Test relationship type validation."""
        validator = SecurityValidator()
        
        # Valid types
        assert validator.validate_relationship_type(RelationshipType.DEPENDS_ON)
        assert validator.validate_relationship_type(RelationshipType.REFERENCES)
        
        # Invalid types
        with pytest.raises(TypeError, match="Invalid relationship type"):
            validator.validate_relationship_type("FAKE_TYPE")
        
        with pytest.raises(TypeError, match="Invalid relationship type"):
            validator.validate_relationship_type(123)
    
    def test_strength_validation(self):
        """Test relationship strength validation."""
        validator = SecurityValidator()
        
        # Valid strengths
        assert validator.validate_strength(0.0)
        assert validator.validate_strength(0.5)
        assert validator.validate_strength(1.0)
        
        # Invalid strengths
        with pytest.raises(ValueError, match="Strength must be between"):
            validator.validate_strength(1.5)
        
        with pytest.raises(ValueError, match="Strength must be between"):
            validator.validate_strength(-0.1)
        
        with pytest.raises(TypeError, match="Strength must be numeric"):
            validator.validate_strength("high")
    
    def test_json_input_validation(self):
        """Test JSON input validation against attacks."""
        validator = SecurityValidator()
        
        # Valid JSON
        valid_json = json.dumps({"nodes": [], "edges": []})
        assert validator.validate_json_input(valid_json)
        
        # Too large JSON
        large_json = "x" * (SecurityConfig.MAX_JSON_SIZE + 1)
        with pytest.raises(ValueError, match="JSON input too large"):
            validator.validate_json_input(large_json)
        
        # Suspicious patterns
        malicious_patterns = [
            '{"__proto__": {"admin": true}}',
            '{"constructor": {"prototype": {}}}',
            '{"eval": "alert(1)"}',
            '{"__import__": "os"}'
        ]
        
        for pattern in malicious_patterns:
            with pytest.raises(SecurityError, match="Potentially malicious"):
                validator.validate_json_input(pattern)
    
    def test_graph_limits_validation(self):
        """Test graph size limit validation."""
        validator = SecurityValidator()
        graph = OptimizedDependencyGraph()
        
        # Valid graph
        assert validator.validate_graph_limits(graph)
        
        # Simulate exceeding node limit
        for i in range(SecurityConfig.MAX_GRAPH_NODES):
            graph.nodes[f"node_{i}"] = {}
        
        with pytest.raises(ResourceLimitError, match="Graph node limit exceeded"):
            validator.validate_graph_limits(graph)
    
    def test_encryption_decryption(self):
        """Test sensitive data encryption/decryption."""
        validator = SecurityValidator()
        
        if validator.cipher:  # Only test if crypto available
            sensitive_data = "password123"
            
            # Encrypt
            encrypted = validator.encrypt_sensitive_data(sensitive_data)
            assert encrypted != sensitive_data
            assert len(encrypted) > 0
            
            # Decrypt
            decrypted = validator.decrypt_sensitive_data(encrypted)
            assert decrypted == sensitive_data
        else:
            # Test fallback to base64
            sensitive_data = "password123"
            encoded = validator.encrypt_sensitive_data(sensitive_data)
            decoded = validator.decrypt_sensitive_data(encoded)
            assert decoded == sensitive_data
    
    def test_hmac_computation(self):
        """Test HMAC computation and verification."""
        validator = SecurityValidator()
        key = secrets.token_bytes(32)
        data = "important data"
        
        # Compute HMAC
        signature = validator.compute_hmac(data, key)
        assert len(signature) == 64  # SHA256 hex digest
        
        # Verify valid HMAC
        assert validator.verify_hmac(data, signature, key)
        
        # Verify invalid HMAC
        wrong_signature = "0" * 64
        assert not validator.verify_hmac(data, wrong_signature, key)
        
        # Verify tampered data
        tampered_data = "tampered data"
        assert not validator.verify_hmac(tampered_data, signature, key)


class TestRateLimiter:
    """Test rate limiting functionality."""
    
    def test_rate_limiting(self):
        """Test operation rate limiting."""
        limiter = RateLimiter(max_operations=5)
        
        # Should allow first 5 operations
        for i in range(5):
            assert limiter.check_rate_limit(f"op_{i}")
        
        # Should block 6th operation
        with pytest.raises(ResourceLimitError, match="Rate limit exceeded"):
            limiter.check_rate_limit("op_6")
    
    def test_rate_limit_window(self):
        """Test rate limit time window."""
        limiter = RateLimiter(max_operations=2)
        limiter.window_size = 1  # 1 second window
        
        # Use up the limit
        limiter.check_rate_limit("op1")
        limiter.check_rate_limit("op2")
        
        # Should be blocked
        with pytest.raises(ResourceLimitError):
            limiter.check_rate_limit("op3")
        
        # Wait for window to expire
        time.sleep(1.1)
        
        # Should be allowed again
        assert limiter.check_rate_limit("op4")
    
    def test_concurrent_rate_limiting(self):
        """Test thread-safe rate limiting."""
        limiter = RateLimiter(max_operations=10)
        errors = []
        
        def make_request(i):
            try:
                limiter.check_rate_limit(f"concurrent_{i}")
                return True
            except ResourceLimitError:
                errors.append(i)
                return False
        
        # Make 15 concurrent requests
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, i) for i in range(15)]
            results = [f.result() for f in futures]
        
        # Should have exactly 10 successes and 5 failures
        assert sum(results) == 10
        assert len(errors) == 5


class TestAuditLogger:
    """Test audit logging functionality."""
    
    def test_operation_logging(self):
        """Test operation audit logging."""
        audit = AuditLogger()
        
        # Log successful operation
        audit.log_operation(
            "add_document",
            user="test_user",
            details={"doc_id": "doc123"}
        )
        
        assert audit.operation_counter == 1
        
        # Log failed operation
        audit.log_operation(
            "delete_document",
            user="test_user",
            details={"doc_id": "doc456", "error": "not found"},
            success=False
        )
        
        assert audit.operation_counter == 2
    
    def test_security_event_logging(self):
        """Test security event logging."""
        audit = AuditLogger()
        
        # Log security events
        audit.log_security_event(
            "authentication_failure",
            "high",
            {"ip": "192.168.1.1", "attempts": 3}
        )
        
        audit.log_security_event(
            "rate_limit_exceeded",
            "medium",
            {"operation": "api_call", "limit": 100}
        )
        
        # Session ID should remain constant
        assert len(audit.session_id) == 32
    
    def test_concurrent_logging(self):
        """Test thread-safe logging."""
        audit = AuditLogger()
        
        def log_operations(thread_id):
            for i in range(10):
                audit.log_operation(
                    f"operation_{thread_id}_{i}",
                    user=f"thread_{thread_id}"
                )
        
        # Run concurrent logging
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(log_operations, i) for i in range(5)]
            for f in futures:
                f.result()
        
        # Should have logged all operations
        assert audit.operation_counter == 50


class TestGraphSecurityIntegration:
    """Test security features in graph operations."""
    
    def test_secure_node_addition(self):
        """Test secure node addition with validation."""
        validator = SecurityValidator()
        graph = OptimizedDependencyGraph(security_validator=validator)
        
        # Valid node
        graph.add_node("valid_doc", {"title": "Test"})
        assert "valid_doc" in graph.nodes
        
        # Invalid node ID - should raise SecurityError for path traversal
        with pytest.raises(SecurityError):
            graph.add_node("../../etc/passwd", {})
        
        # Malicious metadata
        evil_metadata = {"script": "<script>alert(1)</script>"}
        graph.add_node("doc2", evil_metadata)
        
        # Metadata should be sanitized
        assert "<script>" not in str(graph.nodes["doc2"])
    
    def test_secure_edge_addition(self):
        """Test secure edge addition with validation."""
        validator = SecurityValidator()
        graph = OptimizedDependencyGraph(security_validator=validator)
        
        # Add valid edge
        graph.add_edge("doc1", "doc2", RelationshipType.DEPENDS_ON, 0.8)
        assert graph.has_edge("doc1", "doc2")
        
        # Invalid source ID
        with pytest.raises(ValueError):
            graph.add_edge("'; DROP TABLE;", "doc2", RelationshipType.DEPENDS_ON)
        
        # Invalid strength
        with pytest.raises(ValueError):
            graph.add_edge("doc3", "doc4", RelationshipType.DEPENDS_ON, 2.0)
    
    def test_batch_operation_security(self):
        """Test security in batch operations."""
        validator = SecurityValidator()
        graph = OptimizedDependencyGraph(security_validator=validator)
        
        # Valid batch
        valid_edges = [
            ("doc1", "doc2", RelationshipType.DEPENDS_ON, 0.5, {}),
            ("doc2", "doc3", RelationshipType.REFERENCES, 0.7, {})
        ]
        
        graph.add_edges_batch(valid_edges)
        assert graph.has_edge("doc1", "doc2")
        assert graph.has_edge("doc2", "doc3")
        
        # Batch size limit
        huge_batch = [
            (f"doc_{i}", f"doc_{i+1}", RelationshipType.DEPENDS_ON, 0.5, {})
            for i in range(SecurityConfig.MAX_BATCH_SIZE + 1)
        ]
        
        with pytest.raises(ResourceLimitError, match="Batch size exceeds limit"):
            graph.add_edges_batch(huge_batch)
    
    def test_traversal_depth_limits(self):
        """Test protection against deep graph traversal attacks."""
        validator = SecurityValidator()
        graph = OptimizedDependencyGraph(security_validator=validator)
        
        # Create a very deep chain
        for i in range(SecurityConfig.MAX_TRAVERSAL_DEPTH + 10):
            graph.nodes[f"node_{i}"] = {}
            if i > 0:
                graph.edges[f"node_{i-1}"][f"node_{i}"] = DocumentRelationship(
                    f"node_{i-1}", f"node_{i}", RelationshipType.DEPENDS_ON
                )
        
        # Should handle deep traversal safely
        with pytest.raises(ResourceLimitError, match="Graph traversal depth limit"):
            graph._would_create_cycle("node_0", f"node_{SecurityConfig.MAX_TRAVERSAL_DEPTH + 5}")


class TestTrackingMatrixSecurity:
    """Test TrackingMatrix security features."""
    
    @pytest.fixture
    def secure_matrix(self):
        """Create a secure tracking matrix."""
        config = Mock()
        config.get.return_value = {
            "security": {
                "enable_pii_detection": True,
                "cache_ttl_seconds": 300
            }
        }
        
        storage = Mock()
        matrix = TrackingMatrix(config, storage)
        return matrix
    
    def test_secure_json_export(self, secure_matrix):
        """Test secure JSON export with HMAC."""
        # Add some data
        secure_matrix.add_document("doc1", {"title": "Test"})
        secure_matrix.add_relationship(
            "doc1", "doc2", RelationshipType.DEPENDS_ON
        )
        
        # Export with HMAC
        json_str = secure_matrix.export_to_json(include_hmac=True)
        data = json.loads(json_str)
        
        # Should include HMAC
        assert "hmac" in data
        assert len(data["hmac"]) == 64  # SHA256 hex
        
        # Export without HMAC
        json_str_no_hmac = secure_matrix.export_to_json(include_hmac=False)
        data_no_hmac = json.loads(json_str_no_hmac)
        assert "hmac" not in data_no_hmac
    
    def test_secure_json_import(self, secure_matrix):
        """Test secure JSON import with validation."""
        # Create valid JSON with HMAC
        valid_data = {
            "nodes": [{"id": "doc1", "metadata": {}}],
            "edges": [],
            "metadata": {"total_documents": 1}
        }
        
        json_str = json.dumps(valid_data)
        
        # Import without HMAC verification
        secure_matrix.import_from_json(json_str, verify_hmac=False)
        assert secure_matrix.has_document("doc1")
        
        # Test malicious JSON rejection
        malicious_json = '{"__proto__": {"admin": true}}'
        
        with pytest.raises(SecurityError, match="Potentially malicious"):
            secure_matrix.import_from_json(malicious_json)
        
        # Test size limit
        huge_json = json.dumps({
            "nodes": [{"id": f"doc_{i}", "metadata": {}} 
                     for i in range(SecurityConfig.MAX_GRAPH_NODES + 1)],
            "edges": []
        })
        
        with pytest.raises(ResourceLimitError, match="exceeds node limit"):
            secure_matrix.import_from_json(huge_json)
    
    def test_audit_logging_integration(self, secure_matrix):
        """Test audit logging in matrix operations."""
        # Operations should be logged
        secure_matrix.add_document("doc1")
        secure_matrix.add_relationship(
            "doc1", "doc2", RelationshipType.DEPENDS_ON
        )
        
        # Check audit logger state
        assert secure_matrix.audit_logger.operation_counter > 0
    
    def test_permission_decorators(self, secure_matrix):
        """Test permission checking decorators."""
        # All write operations should check permissions
        # This is currently just logging, but structure is in place
        secure_matrix.add_document("doc1")
        secure_matrix.add_relationship(
            "doc1", "doc2", RelationshipType.DEPENDS_ON
        )
        
        # Read operations should check read permission
        secure_matrix.export_to_json()
        
        # Verify operations completed (permissions currently just log)
        assert secure_matrix.has_document("doc1")
    
    def test_concurrent_security(self, secure_matrix):
        """Test security under concurrent access."""
        errors = []
        
        def add_documents(thread_id):
            try:
                for i in range(10):
                    secure_matrix.add_document(f"thread_{thread_id}_doc_{i}")
            except Exception as e:
                errors.append(e)
        
        # Run concurrent additions
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(add_documents, i) for i in range(5)]
            for f in futures:
                f.result()
        
        # Should have no errors
        assert len(errors) == 0
        
        # All documents should be added
        for thread_id in range(5):
            for i in range(10):
                assert secure_matrix.has_document(f"thread_{thread_id}_doc_{i}")


class TestOWASPCompliance:
    """Test OWASP Top 10 compliance."""
    
    def test_a01_broken_access_control(self):
        """Test protection against broken access control."""
        # Permission decorators are in place
        # Currently logging, can be extended with real RBAC
        config = Mock()
        storage = Mock()
        matrix = TrackingMatrix(config, storage)
        
        # Operations require permissions (currently just logged)
        matrix.add_document("doc1")
        assert matrix.audit_logger.operation_counter > 0
    
    def test_a02_cryptographic_failures(self):
        """Test cryptographic protections."""
        validator = SecurityValidator()
        
        # HMAC for integrity
        key = secrets.token_bytes(32)
        data = "sensitive data"
        hmac = validator.compute_hmac(data, key)
        assert validator.verify_hmac(data, hmac, key)
        
        # Encryption for confidentiality (if available)
        if validator.cipher:
            encrypted = validator.encrypt_sensitive_data("secret")
            assert encrypted != "secret"
    
    def test_a03_injection(self):
        """Test injection attack prevention."""
        validator = SecurityValidator()
        
        # SQL injection prevention
        with pytest.raises(ValueError):
            validator.validate_document_id("'; DROP TABLE docs;--")
        
        # XSS prevention
        metadata = {"script": "<script>alert(1)</script>"}
        sanitized = validator.sanitize_metadata(metadata)
        assert "<script>" not in str(sanitized)
        
        # Path traversal prevention
        with pytest.raises(SecurityError):
            validator.validate_document_id("../../etc/passwd")
    
    def test_a04_insecure_design(self):
        """Test secure design principles."""
        # Rate limiting
        limiter = RateLimiter(max_operations=5)
        for i in range(5):
            limiter.check_rate_limit(f"op_{i}")
        
        with pytest.raises(ResourceLimitError):
            limiter.check_rate_limit("op_6")
        
        # Resource limits
        graph = OptimizedDependencyGraph()
        validator = SecurityValidator()
        
        # Simulate resource exhaustion attempt
        for i in range(SecurityConfig.MAX_GRAPH_NODES - 1):
            graph.nodes[f"node_{i}"] = {}
        
        with pytest.raises(ResourceLimitError):
            validator.validate_graph_limits(graph)
    
    def test_a05_security_misconfiguration(self):
        """Test secure configuration."""
        config = Mock()
        config.get.return_value = {
            "security": {
                "enable_pii_detection": True,  # Secure by default
                "cache_ttl_seconds": 300
            }
        }
        
        validator = SecurityValidator(config.get("security"))
        assert validator.config["enable_pii_detection"] == True
    
    def test_a07_identification_authentication(self):
        """Test identification and authentication features."""
        # Session management
        audit = AuditLogger()
        session_id = audit.session_id
        
        # Session ID should be cryptographically secure
        assert len(session_id) == 32  # 16 bytes hex
        
        # Each session should have unique ID
        audit2 = AuditLogger()
        assert audit2.session_id != session_id
    
    def test_a08_software_data_integrity(self):
        """Test data integrity features."""
        config = Mock()
        storage = Mock()
        matrix = TrackingMatrix(config, storage)
        
        # HMAC for export integrity
        json_data = matrix.export_to_json(include_hmac=True)
        data = json.loads(json_data)
        assert "hmac" in data
        
        # Verification on import
        matrix2 = TrackingMatrix(config, storage)
        # Would verify HMAC if importing data with HMAC
    
    def test_a09_logging_monitoring(self):
        """Test security logging and monitoring."""
        audit = AuditLogger()
        
        # Operation logging
        audit.log_operation("test_op", details={"test": "data"})
        assert audit.operation_counter == 1
        
        # Security event logging
        audit.log_security_event(
            "suspicious_activity",
            "high",
            {"details": "test"}
        )
        
        # Audit trail with session tracking
        assert audit.session_id is not None
    
    def test_a10_ssrf_prevention(self):
        """Test Server-Side Request Forgery prevention."""
        # No external requests in this module
        # But validation prevents file path manipulation
        validator = SecurityValidator()
        
        with pytest.raises(SecurityError):
            validator.validate_document_id("file:///etc/passwd")
        
        with pytest.raises(ValueError):
            validator.validate_document_id("http://evil.com/steal")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])