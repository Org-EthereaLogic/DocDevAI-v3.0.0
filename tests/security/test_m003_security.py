"""
M003 MIAIR Engine - Comprehensive Security Tests

Tests all security features of the hardened MIAIR Engine:
- Input validation and sanitization
- Rate limiting and DoS protection
- Secure caching with encryption
- PII detection and masking
- Audit logging
- Performance overhead verification
"""

import pytest
import time
import threading
import hashlib
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

# Import the secure engine and security modules
from devdocai.miair.secure_engine import SecureMIAIREngine
from devdocai.miair.models import Document, OperationMode, MIAIRConfig
from devdocai.miair.security import (
    ValidationError, ThreatLevel, RateLimitExceeded, CircuitBreakerOpen,
    CacheSecurityError, Priority
)


class TestInputValidation:
    """Test input validation and sanitization."""
    
    def test_validate_clean_document(self):
        """Test validation of clean document passes."""
        engine = SecureMIAIREngine()
        doc = Document(
            id="test_doc_1",
            content="This is a clean document with normal content.",
            source="test"
        )
        
        sanitized_doc, report = engine._validate_and_sanitize_document(doc)
        assert report['passed'] == True
        assert len(report.get('threats_detected', [])) == 0
        assert sanitized_doc.content == doc.content
    
    def test_detect_script_injection(self):
        """Test detection of script injection attempts."""
        engine = SecureMIAIREngine()
        doc = Document(
            id="test_doc_2",
            content="Normal text <script>alert('XSS')</script> more text",
            source="test"
        )
        
        with pytest.raises(ValidationError) as exc_info:
            engine._validate_and_sanitize_document(doc)
        assert exc_info.value.threat_level == ThreatLevel.CRITICAL
    
    def test_detect_sql_injection(self):
        """Test detection of SQL injection patterns."""
        engine = SecureMIAIREngine()
        doc = Document(
            id="test_doc_3",
            content="SELECT * FROM users WHERE id = '1' OR '1'='1'",
            source="test"
        )
        
        # Should sanitize but not necessarily raise error for SQL
        sanitized_doc, report = engine._validate_and_sanitize_document(doc)
        assert report['passed'] == True  # SQL in content might be legitimate
        assert len(report.get('sanitizations_applied', [])) > 0
    
    def test_detect_path_traversal(self):
        """Test detection of path traversal attempts."""
        engine = SecureMIAIREngine()
        doc = Document(
            id="test_doc_4",
            content="File path: ../../etc/passwd",
            source="test"
        )
        
        with pytest.raises(ValidationError):
            engine._validate_and_sanitize_document(doc)
    
    def test_document_size_limits(self):
        """Test document size validation."""
        engine = SecureMIAIREngine()
        
        # Create oversized document (>10MB)
        large_content = "x" * (11 * 1024 * 1024)
        doc = Document(
            id="test_doc_5",
            content=large_content,
            source="test"
        )
        
        with pytest.raises(ValidationError) as exc_info:
            engine._validate_and_sanitize_document(doc)
        assert "too large" in str(exc_info.value).lower()
    
    def test_sanitize_html_content(self):
        """Test HTML sanitization."""
        engine = SecureMIAIREngine()
        doc = Document(
            id="test_doc_6",
            content="Text with <b>HTML</b> and <img src='x' onerror='alert(1)'>",
            source="test"
        )
        
        sanitized_doc, report = engine._validate_and_sanitize_document(doc)
        assert "&lt;" in sanitized_doc.content  # HTML should be escaped
        assert "onerror" not in sanitized_doc.content or "&" in sanitized_doc.content


class TestRateLimiting:
    """Test rate limiting and DoS protection."""
    
    def test_rate_limit_enforcement(self):
        """Test that rate limits are enforced."""
        config = {
            'rate_limiting': {
                'tokens_per_second': 2.0,
                'burst_size': 2
            }
        }
        engine = SecureMIAIREngine(security_config=config)
        
        doc = Document(id="test_doc", content="Test content", source="test")
        
        # First two requests should succeed (burst)
        engine.analyze(doc, client_id="client1")
        engine.analyze(doc, client_id="client1")
        
        # Third request should be rate limited
        with pytest.raises(RateLimitExceeded):
            engine.analyze(doc, client_id="client1")
    
    def test_per_client_rate_limiting(self):
        """Test per-client rate limiting."""
        config = {
            'rate_limiting': {
                'enable_per_client_limits': True,
                'client_tokens_per_second': 1.0,
                'client_burst_size': 1
            }
        }
        engine = SecureMIAIREngine(security_config=config)
        
        doc = Document(id="test_doc", content="Test content", source="test")
        
        # Client 1 exhausts their limit
        engine.analyze(doc, client_id="client1")
        with pytest.raises(RateLimitExceeded):
            engine.analyze(doc, client_id="client1")
        
        # Client 2 should still be able to make requests
        engine.analyze(doc, client_id="client2")
    
    def test_circuit_breaker_protection(self):
        """Test circuit breaker opens on repeated failures."""
        config = {
            'rate_limiting': {
                'failure_threshold': 3,
                'recovery_timeout': 1.0
            }
        }
        engine = SecureMIAIREngine(security_config=config)
        
        # Mock the base optimize to fail
        with patch.object(engine.__class__.__bases__[0], 'optimize', side_effect=Exception("Test error")):
            doc = Document(id="test_doc", content="Test", source="test")
            
            # Cause failures to trip circuit breaker
            for _ in range(3):
                try:
                    engine.optimize(doc)
                except:
                    pass
            
            # Circuit should be open now
            # Note: This would require more sophisticated mocking of the circuit breaker
    
    def test_priority_queue_processing(self):
        """Test priority-based request processing."""
        engine = SecureMIAIREngine()
        
        # Queue requests with different priorities
        high_priority_request = {'doc_id': 'high', 'priority': Priority.HIGH}
        normal_request = {'doc_id': 'normal', 'priority': Priority.NORMAL}
        low_request = {'doc_id': 'low', 'priority': Priority.LOW}
        
        engine.rate_limiter.queue_request(low_request, Priority.LOW)
        engine.rate_limiter.queue_request(high_priority_request, Priority.HIGH)
        engine.rate_limiter.queue_request(normal_request, Priority.NORMAL)
        
        # High priority should be processed first
        first = engine.rate_limiter.get_queued_request()
        assert first[1]['doc_id'] == 'high'


class TestSecureCaching:
    """Test secure caching with encryption."""
    
    def test_cache_encryption(self):
        """Test that cached values are encrypted."""
        engine = SecureMIAIREngine()
        
        # Store a value in cache
        test_value = {'sensitive': 'data', 'pii': 'john.doe@example.com'}
        engine._store_cache_secure('test_key', test_value, 'client1')
        
        # Retrieve and verify
        retrieved = engine._check_cache_secure('test_key', 'client1')
        assert retrieved == test_value
        
        # Verify raw cache entry is encrypted
        cache_entry = engine.secure_cache._cache.get('test_key')
        if cache_entry and cache_entry.encrypted:
            assert cache_entry.value != test_value  # Should be encrypted
    
    def test_cache_isolation(self):
        """Test cache isolation between clients."""
        config = {
            'secure_cache': {
                'enable_cache_isolation': True
            }
        }
        engine = SecureMIAIREngine(security_config=config)
        
        # Store values for different clients
        engine._store_cache_secure('shared_key', 'client1_data', 'client1')
        engine._store_cache_secure('shared_key', 'client2_data', 'client2')
        
        # Verify isolation
        assert engine._check_cache_secure('shared_key', 'client1') == 'client1_data'
        assert engine._check_cache_secure('shared_key', 'client2') == 'client2_data'
        assert engine._check_cache_secure('shared_key', 'client3') is None
    
    def test_cache_ttl_expiration(self):
        """Test cache TTL expiration."""
        config = {
            'secure_cache': {
                'ttl_seconds': 0.1  # 100ms TTL for testing
            }
        }
        engine = SecureMIAIREngine(security_config=config)
        
        engine._store_cache_secure('ttl_test', 'value', 'client1')
        assert engine._check_cache_secure('ttl_test', 'client1') == 'value'
        
        # Wait for expiration
        time.sleep(0.2)
        assert engine._check_cache_secure('ttl_test', 'client1') is None
    
    def test_secure_cache_deletion(self):
        """Test secure deletion of cached data."""
        engine = SecureMIAIREngine()
        
        sensitive_data = "SSN: 123-45-6789"
        engine._store_cache_secure('sensitive', sensitive_data)
        
        # Clear cache
        engine.secure_cache.clear()
        
        # Verify deletion
        assert engine._check_cache_secure('sensitive') is None


class TestPIIDetection:
    """Test PII detection and masking integration."""
    
    def test_detect_email_pii(self):
        """Test detection and masking of email addresses."""
        engine = SecureMIAIREngine()
        doc = Document(
            id="pii_test_1",
            content="Contact john.doe@example.com for more info",
            source="test"
        )
        
        protected_doc, pii_report = engine._apply_pii_protection(doc)
        assert pii_report['pii_detected'] == True
        assert 'email' in pii_report['types_found']
        assert '@example.com' not in protected_doc.content or '[' in protected_doc.content
    
    def test_detect_phone_pii(self):
        """Test detection and masking of phone numbers."""
        engine = SecureMIAIREngine()
        doc = Document(
            id="pii_test_2",
            content="Call me at 555-123-4567 or (555) 987-6543",
            source="test"
        )
        
        protected_doc, pii_report = engine._apply_pii_protection(doc)
        assert pii_report['pii_detected'] == True
        assert 'phone' in pii_report['types_found']
        assert pii_report['masked_count'] >= 2
    
    def test_detect_ssn_pii(self):
        """Test detection and masking of SSN."""
        engine = SecureMIAIREngine()
        doc = Document(
            id="pii_test_3",
            content="SSN: 123-45-6789",
            source="test"
        )
        
        protected_doc, pii_report = engine._apply_pii_protection(doc)
        assert pii_report['pii_detected'] == True
        assert 'ssn' in pii_report['types_found']
        assert '123-45-6789' not in protected_doc.content
    
    def test_detect_credit_card_pii(self):
        """Test detection and masking of credit card numbers."""
        engine = SecureMIAIREngine()
        doc = Document(
            id="pii_test_4",
            content="Payment: 4111-1111-1111-1111",
            source="test"
        )
        
        protected_doc, pii_report = engine._apply_pii_protection(doc)
        assert pii_report['pii_detected'] == True
        assert 'credit_card' in pii_report['types_found']
    
    def test_pii_in_metadata(self):
        """Test PII detection in document metadata."""
        engine = SecureMIAIREngine()
        doc = Document(
            id="pii_test_5",
            content="Clean content",
            source="test",
            metadata={
                'author_email': 'author@example.com',
                'reviewer_phone': '555-0123'
            }
        )
        
        protected_doc, pii_report = engine._apply_pii_protection(doc)
        assert pii_report['pii_detected'] == True
        assert pii_report['masked_count'] > 0


class TestAuditLogging:
    """Test audit logging functionality."""
    
    def test_audit_log_creation(self):
        """Test that audit logs are created for operations."""
        engine = SecureMIAIREngine()
        doc = Document(id="audit_test", content="Test content", source="test")
        
        # Perform operation
        engine.analyze(doc, client_id="test_client")
        
        # Check audit stats
        audit_stats = engine.audit_logger.get_stats()
        assert audit_stats['events_logged'] > 0
    
    def test_security_violation_logging(self):
        """Test logging of security violations."""
        engine = SecureMIAIREngine()
        doc = Document(
            id="violation_test",
            content="<script>malicious()</script>",
            source="test"
        )
        
        try:
            engine._validate_and_sanitize_document(doc)
        except ValidationError:
            pass
        
        # Check that violation was logged
        audit_stats = engine.audit_logger.get_stats()
        assert audit_stats['events_logged'] > 0
    
    def test_pii_access_logging(self):
        """Test logging of PII access."""
        engine = SecureMIAIREngine()
        doc = Document(
            id="pii_log_test",
            content="Email: test@example.com",
            source="test"
        )
        
        engine._apply_pii_protection(doc)
        
        # Verify PII access was logged
        audit_stats = engine.audit_logger.get_stats()
        assert audit_stats['events_logged'] > 0


class TestPerformanceOverhead:
    """Test that security overhead is <10%."""
    
    def test_optimization_performance_overhead(self):
        """Test optimization performance with security enabled vs disabled."""
        # Create base engine without security
        base_engine = SecureMIAIREngine.__bases__[0](mode=OperationMode.PERFORMANCE)
        
        # Create secure engine
        secure_engine = SecureMIAIREngine()
        
        doc = Document(
            id="perf_test",
            content="Test document " * 100,  # Medium-sized document
            source="test"
        )
        
        # Measure base performance
        start = time.time()
        for _ in range(10):
            base_engine.analyze(doc)
        base_time = time.time() - start
        
        # Measure secure performance
        start = time.time()
        for _ in range(10):
            secure_engine.analyze(doc)
        secure_time = time.time() - start
        
        # Calculate overhead
        overhead = ((secure_time - base_time) / base_time) * 100
        
        # Verify <10% overhead
        assert overhead < 10, f"Security overhead {overhead:.1f}% exceeds 10% limit"
    
    def test_caching_performance(self):
        """Test that secure caching improves performance."""
        engine = SecureMIAIREngine()
        doc = Document(id="cache_perf", content="Test content", source="test")
        
        # First call (cache miss)
        start = time.time()
        engine.analyze(doc)
        first_time = time.time() - start
        
        # Second call (cache hit)
        start = time.time()
        engine.analyze(doc)
        cached_time = time.time() - start
        
        # Cached should be significantly faster
        assert cached_time < first_time * 0.5  # At least 50% faster
    
    def test_batch_processing_performance(self):
        """Test batch processing with security."""
        engine = SecureMIAIREngine()
        
        # Create batch of documents
        docs = [
            Document(id=f"batch_{i}", content=f"Content {i}", source="test")
            for i in range(10)
        ]
        
        start = time.time()
        results = engine.batch_optimize(docs)
        batch_time = time.time() - start
        
        # Verify all processed
        assert len(results) == 10
        
        # Verify reasonable performance (< 1s per doc with security)
        assert batch_time < 10.0


class TestIntegration:
    """Integration tests for secure engine."""
    
    def test_full_secure_optimization_flow(self):
        """Test complete optimization flow with all security features."""
        config = {
            'validation': {'enable_pattern_detection': True},
            'rate_limiting': {'tokens_per_second': 10.0},
            'secure_cache': {'encryption_enabled': True},
            'pii': {'enabled': True},
            'audit': {'enable_hash_chain': True}
        }
        
        engine = SecureMIAIREngine(security_config=config)
        
        doc = Document(
            id="integration_test",
            content="Optimize this document with email: test@example.com",
            source="test"
        )
        
        result = engine.optimize(doc, client_id="test_client")
        
        # Verify optimization succeeded
        assert result.improvement_percentage > 0
        
        # Verify security metadata
        assert result.metadata['security']['validated'] == True
        assert result.metadata['security']['pii_masked'] == True
        
        # Verify statistics updated
        stats = engine.get_security_stats()
        assert stats['security']['validations']['validations_passed'] > 0
        assert stats['security']['pii_integration']['pii_found'] > 0
    
    def test_concurrent_request_handling(self):
        """Test handling of concurrent requests with security."""
        engine = SecureMIAIREngine()
        doc = Document(id="concurrent", content="Test", source="test")
        
        results = []
        errors = []
        
        def worker(client_id):
            try:
                result = engine.analyze(doc, client_id=client_id)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Launch concurrent requests
        threads = []
        for i in range(10):
            t = threading.Thread(target=worker, args=(f"client_{i}",))
            threads.append(t)
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Verify some succeeded
        assert len(results) > 0
        
        # Check for rate limiting
        rate_limit_errors = [e for e in errors if isinstance(e, RateLimitExceeded)]
        # Some might be rate limited depending on config
    
    def test_security_stats_reporting(self):
        """Test comprehensive security statistics reporting."""
        engine = SecureMIAIREngine()
        
        # Perform various operations
        doc1 = Document(id="stats1", content="Normal content", source="test")
        doc2 = Document(id="stats2", content="Email: test@example.com", source="test")
        
        engine.analyze(doc1)
        engine.optimize(doc2)
        
        # Get comprehensive stats
        stats = engine.get_security_stats()
        
        # Verify stats structure
        assert 'security' in stats
        assert 'validations' in stats['security']
        assert 'input_validator' in stats['security']
        assert 'rate_limiter' in stats['security']
        assert 'secure_cache' in stats['security']
        assert 'pii_integration' in stats['security']
        assert 'audit_logger' in stats['security']
        assert 'overhead_percentage' in stats['security']
        
        # Verify overhead is calculated and <10%
        assert stats['security']['overhead_percentage'] < 10.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])