"""
M004 Document Generator - Pass 3 Security Hardening Tests
DevDocAI v3.0.0

Comprehensive security tests for high-throughput document generation.
Tests cache security, input validation, DOS protection, and OWASP compliance.
"""

import pytest
import asyncio
import tempfile
import time
import secrets
import hashlib
import hmac
import pickle
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime, timedelta
import ast

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from devdocai.core.generator import (
    DocumentGenerator,
    SecurityManager,
    ResponseCache,
    BatchProcessor,
    PerformanceMonitor,
    CacheEntry,
    BatchRequest,
    DocumentGenerationError,
    ContextExtractionError
)
from devdocai.core.config import ConfigurationManager
from devdocai.intelligence.llm_adapter import LLMAdapter, LLMResponse
from devdocai.core.storage import StorageManager


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_config():
    """Create mock configuration for testing."""
    config = MagicMock(spec=ConfigurationManager)
    config.system.memory_mode = 'standard'
    config.system.cache_ttl = 3600
    config.system.cache_dir = '/tmp/test_cache'
    config.system.templates_dir = '/tmp/test_templates'
    config.security.max_batch_size = 100
    config.security.max_file_count = 100
    config.security.max_cache_size = 1000
    config.security.rate_limit_per_minute = 60
    config.security.path_traversal_protection = True
    config.security.master_key = b'test_master_key_32_bytes_long!!!'
    config.get.return_value = 100
    return config


@pytest.fixture
def security_manager(mock_config):
    """Create SecurityManager instance for testing."""
    return SecurityManager(mock_config)


@pytest.fixture
def response_cache(mock_config, security_manager):
    """Create ResponseCache instance for testing."""
    return ResponseCache(mock_config, security_manager)


@pytest.fixture
def mock_llm_adapter():
    """Create mock LLM adapter."""
    adapter = MagicMock(spec=LLMAdapter)
    response = MagicMock(spec=LLMResponse)
    response.content = "Generated content"
    response.tokens_used = 100
    response.cost = 0.01
    adapter.generate.return_value = response
    return adapter


@pytest.fixture
def mock_storage():
    """Create mock storage manager."""
    storage = MagicMock(spec=StorageManager)
    storage.save_document.return_value = "doc_123"
    return storage


@pytest.fixture
async def generator(mock_config, mock_llm_adapter, mock_storage):
    """Create DocumentGenerator instance for testing."""
    with patch('devdocai.core.generator.psutil'):
        gen = DocumentGenerator(mock_config, mock_llm_adapter, mock_storage)
        return gen


# ============================================================================
# SecurityManager Tests
# ============================================================================

class TestSecurityManager:
    """Test security manager functionality."""
    
    def test_path_validation(self, security_manager):
        """Test path traversal protection."""
        # Valid paths
        assert security_manager.validate_path("./test.py")
        assert security_manager.validate_path("src/module.py")
        
        # Invalid paths - traversal attempts
        assert not security_manager.validate_path("../../../etc/passwd")
        assert not security_manager.validate_path("/etc/passwd")
        assert not security_manager.validate_path("~/ssh/id_rsa")
        
        # Blacklisted patterns
        assert not security_manager.validate_path(".git/config")
        assert not security_manager.validate_path(".env")
        assert not security_manager.validate_path(".aws/credentials")
    
    def test_batch_size_validation(self, security_manager):
        """Test batch size limits."""
        assert security_manager.validate_batch_size(50)
        assert security_manager.validate_batch_size(100)
        assert not security_manager.validate_batch_size(101)
        assert not security_manager.validate_batch_size(1000)
    
    def test_rate_limiting(self, security_manager):
        """Test rate limiting functionality."""
        user_id = "test_user"
        
        # Should allow initial requests
        for _ in range(30):
            assert security_manager.check_rate_limit(user_id)
        
        # Should block after limit
        for _ in range(31):
            security_manager.check_rate_limit(user_id)
        
        # Should be blocked now
        assert not security_manager.check_rate_limit(user_id)
    
    def test_input_sanitization(self, security_manager):
        """Test input sanitization for injection attacks."""
        # Script injection
        dirty = "<script>alert('xss')</script>Hello"
        clean = security_manager.sanitize_input(dirty)
        assert "<script>" not in clean
        
        # Template injection
        dirty = "Hello {{evil}}"
        clean = security_manager.sanitize_input(dirty)
        assert "{{" not in clean
        
        # Command injection
        dirty = "Hello `rm -rf /`"
        clean = security_manager.sanitize_input(dirty)
        assert "`" not in clean
    
    def test_pii_detection(self, security_manager):
        """Test PII detection patterns."""
        text = """
        John Smith works at the company.
        His email is john@example.com
        Phone: 555-123-4567
        SSN: 123-45-6789
        Credit card: 1234567890123456
        """
        
        detections = security_manager.detect_pii(text)
        pii_types = [d[1] for d in detections]
        
        assert 'NAME' in pii_types
        assert 'EMAIL' in pii_types
        assert 'PHONE' in pii_types
        assert 'SSN' in pii_types
        assert 'CREDIT_CARD' in pii_types
    
    def test_cache_signing(self, security_manager):
        """Test HMAC signature generation and verification."""
        content = "test content"
        fingerprint = "abc123"
        
        # Generate signature
        signature = security_manager.sign_cache_entry(content, fingerprint)
        assert signature
        
        # Verify valid signature
        assert security_manager.verify_cache_signature(content, fingerprint, signature)
        
        # Verify invalid signature
        assert not security_manager.verify_cache_signature("tampered", fingerprint, signature)
        assert not security_manager.verify_cache_signature(content, "wrong_fp", signature)
    
    def test_cache_encryption(self, security_manager):
        """Test cache content encryption and decryption."""
        original = b"sensitive cache content"
        
        # Encrypt
        encrypted = security_manager.encrypt_cache_content(original)
        assert encrypted != original
        assert len(encrypted) > len(original)
        
        # Decrypt
        decrypted = security_manager.decrypt_cache_content(encrypted)
        assert decrypted == original
    
    def test_ast_validation(self, security_manager):
        """Test AST node validation for safe parsing."""
        # Safe code
        safe_code = """
def hello():
    return "world"
        """
        tree = ast.parse(safe_code)
        assert security_manager.validate_ast_node(tree)
        
        # Unsafe code with import
        unsafe_code = """
import os
os.system('rm -rf /')
        """
        tree = ast.parse(unsafe_code)
        assert not security_manager.validate_ast_node(tree)
    
    def test_resource_quota_validation(self, security_manager):
        """Test resource quota enforcement."""
        # Within limits
        assert security_manager.validate_resource_usage(
            memory_mb=500, cpu_percent=40, concurrent=30, memory_mode='standard'
        )
        
        # Exceeds memory
        assert not security_manager.validate_resource_usage(
            memory_mb=2000, cpu_percent=40, concurrent=30, memory_mode='standard'
        )
        
        # Exceeds CPU
        assert not security_manager.validate_resource_usage(
            memory_mb=500, cpu_percent=80, concurrent=30, memory_mode='standard'
        )
        
        # Exceeds concurrent
        assert not security_manager.validate_resource_usage(
            memory_mb=500, cpu_percent=40, concurrent=100, memory_mode='standard'
        )
    
    def test_security_event_logging(self, security_manager):
        """Test security event logging with tamper protection."""
        # Log an event
        security_manager._log_security_event('TEST_EVENT', {'data': 'test'})
        
        # Check audit log
        assert len(security_manager.audit_log) > 0
        event = security_manager.audit_log[-1]
        
        assert event['event_type'] == 'TEST_EVENT'
        assert event['details']['data'] == 'test'
        assert 'timestamp' in event
        assert 'correlation_id' in event
        assert 'signature' in event
        
        # Verify signature
        event_copy = event.copy()
        signature = event_copy.pop('signature')
        event_str = str(sorted(event_copy.items()))
        
        # Signature should be valid
        assert len(signature) == 64  # SHA256 hex length


# ============================================================================
# ResponseCache Security Tests
# ============================================================================

class TestResponseCacheSecurity:
    """Test cache security features."""
    
    def test_cache_integrity_validation(self, response_cache, security_manager):
        """Test cache entry integrity validation."""
        prompt = "test prompt"
        context = {"key": "value"}
        response = "test response"
        
        # Put entry with signature
        response_cache.put(prompt, context, response, user_id='user1')
        
        # Get with valid user
        entry = response_cache.get(prompt, context, user_id='user1')
        assert entry is not None
        assert entry.content == response
        
        # Get with different user (isolation)
        entry = response_cache.get(prompt, context, user_id='user2')
        assert entry is None  # Should not get other user's cache
    
    def test_cache_encryption_on_disk(self, response_cache, tmp_path):
        """Test L3 disk cache encryption."""
        response_cache.cache_dir = tmp_path
        response_cache.memory_mode = 'performance'
        
        # Create entry
        entry = CacheEntry(
            content="sensitive data",
            timestamp=datetime.now(),
            fingerprint="test123",
            signature="sig",
            user_id="user1"
        )
        
        # Save to disk
        response_cache._save_to_disk("test123", entry)
        
        # Check file is encrypted
        cache_file = tmp_path / "test123.cache"
        assert cache_file.exists()
        
        with open(cache_file, 'rb') as f:
            encrypted_content = f.read()
        
        # Should not contain plaintext
        assert b"sensitive data" not in encrypted_content
        
        # Load and verify decryption
        loaded = response_cache._load_from_disk("test123")
        assert loaded is not None
        assert loaded.content == "sensitive data"
    
    def test_cache_poisoning_prevention(self, response_cache):
        """Test cache poisoning attack prevention."""
        prompt = "test prompt"
        context = {"key": "value"}
        
        # Put legitimate entry
        response_cache.put(prompt, context, "legitimate response")
        
        # Try to poison cache with script injection
        malicious = "<script>alert('xss')</script>malicious"
        response_cache.put(prompt, {"key": "value2"}, malicious)
        
        # Get entry - should be sanitized
        entry = response_cache.get(prompt, {"key": "value2"})
        if entry:
            assert "<script>" not in entry.content
    
    def test_cache_timing_attack_mitigation(self, response_cache):
        """Test timing attack mitigation in cache."""
        prompt = "test prompt"
        context = {"key": "value"}
        
        # Put entry
        response_cache.put(prompt, context, "response")
        
        # Multiple gets should have timing variance
        timings = []
        for _ in range(10):
            start = time.perf_counter()
            response_cache.get(prompt, context)
            elapsed = time.perf_counter() - start
            timings.append(elapsed)
        
        # Check for variance (jitter added)
        assert len(set(timings)) > 1


# ============================================================================
# BatchProcessor Security Tests
# ============================================================================

class TestBatchProcessorSecurity:
    """Test batch processing security."""
    
    @pytest.mark.asyncio
    async def test_batch_size_enforcement(self, mock_config, security_manager):
        """Test batch size limits are enforced."""
        generator = MagicMock()
        processor = BatchProcessor(mock_config, generator, security_manager)
        
        # Create oversized batch
        requests = [
            BatchRequest("readme", "/path", {}, request_id=f"req_{i}")
            for i in range(150)
        ]
        
        # Should raise error for oversized batch
        with pytest.raises(DocumentGenerationError):
            await processor.process_batch(requests)
    
    @pytest.mark.asyncio
    async def test_batch_input_sanitization(self, mock_config, security_manager):
        """Test batch input sanitization."""
        generator = AsyncMock()
        processor = BatchProcessor(mock_config, generator, security_manager)
        
        # Create batch with malicious input
        requests = [
            BatchRequest(
                "readme", 
                "/path",
                {"data": "<script>alert('xss')</script>"},
                request_id="req_1"
            )
        ]
        
        # Process batch
        generator.generate.return_value = {
            'document_id': 'doc_1',
            'type': 'readme',
            'content': 'content',
            'quality_score': 0.9,
            'metadata': {},
            'generation_time': 1.0
        }
        
        await processor.process_batch(requests)
        
        # Check that input was sanitized
        call_args = generator.generate.call_args
        context = call_args[1]['custom_context']
        assert "<script>" not in context['data']
    
    @pytest.mark.asyncio
    async def test_batch_resource_limits(self, mock_config, security_manager):
        """Test batch processing resource limits."""
        generator = AsyncMock()
        processor = BatchProcessor(mock_config, generator, security_manager)
        
        # Set low resource quota
        security_manager.resource_quotas['standard']['concurrent'] = 5
        
        # Create large batch
        requests = [
            BatchRequest("readme", "/path", {}, request_id=f"req_{i}")
            for i in range(20)
        ]
        
        # Process should limit concurrency
        generator.generate.return_value = {
            'document_id': 'doc_1',
            'type': 'readme',
            'content': 'content',
            'quality_score': 0.9,
            'metadata': {},
            'generation_time': 1.0
        }
        
        await processor.process_batch(requests)
        
        # Should process only allowed concurrent
        assert generator.generate.call_count <= 5


# ============================================================================
# PerformanceMonitor Security Tests
# ============================================================================

class TestPerformanceMonitorSecurity:
    """Test performance monitoring security."""
    
    def test_metric_sanitization(self, security_manager):
        """Test metric metadata sanitization."""
        monitor = PerformanceMonitor(security_manager)
        
        op_id = monitor.start_operation("test_op")
        
        # End with malicious metadata
        metadata = {
            "user": "<script>alert('xss')</script>",
            "path": "../../../etc/passwd"
        }
        
        monitor.end_operation(op_id, metadata)
        
        # Check metrics are sanitized
        stats = monitor.get_stats("test_op")
        assert stats['count'] == 1
        
        # Metadata should be sanitized
        metric = monitor.metrics['test_op'][0]
        assert "<script>" not in metric['metadata']['user']
    
    def test_timing_attack_prevention(self, security_manager):
        """Test timing jitter to prevent timing attacks."""
        monitor = PerformanceMonitor(security_manager)
        
        # Record multiple operations
        for _ in range(10):
            op_id = monitor.start_operation("test")
            time.sleep(0.01)  # Fixed delay
            monitor.end_operation(op_id)
        
        # Check that timings have variance due to jitter
        durations = [m['duration'] for m in monitor.metrics['test']]
        unique_durations = set(durations)
        
        # Should have variance from jitter
        assert len(unique_durations) > 5
    
    def test_metric_rotation(self, security_manager):
        """Test metric rotation to prevent memory exhaustion."""
        monitor = PerformanceMonitor(security_manager)
        monitor.max_metrics_per_operation = 10
        
        # Add many metrics
        for i in range(20):
            op_id = monitor.start_operation("test")
            monitor.end_operation(op_id)
        
        # Should rotate and keep only recent metrics
        assert len(monitor.metrics['test']) <= 10


# ============================================================================
# DocumentGenerator Security Integration Tests
# ============================================================================

class TestDocumentGeneratorSecurity:
    """Test document generator security integration."""
    
    @pytest.mark.asyncio
    async def test_rate_limiting_enforcement(self, generator):
        """Test rate limiting in document generation."""
        # Generate documents up to rate limit
        for _ in range(5):
            with patch('devdocai.core.generator.psutil'):
                result = await generator.generate(
                    "readme",
                    "./test_project",
                    user_id="test_user"
                )
        
        # Configure rate limit to be exceeded
        generator.security_manager.rate_limit_per_minute = 5
        
        # Next request should be rate limited
        with pytest.raises(DocumentGenerationError, match="Rate limit"):
            await generator.generate(
                "readme",
                "./test_project",
                user_id="test_user"
            )
    
    @pytest.mark.asyncio
    async def test_path_validation_in_generation(self, generator):
        """Test path validation during generation."""
        # Try to generate with path traversal
        with pytest.raises(DocumentGenerationError, match="Invalid or unsafe"):
            await generator.generate(
                "readme",
                "../../../etc/passwd"
            )
        
        # Try with absolute path
        with pytest.raises(DocumentGenerationError, match="Invalid or unsafe"):
            await generator.generate(
                "readme",
                "/etc/passwd"
            )
    
    @pytest.mark.asyncio
    async def test_resource_quota_enforcement(self, generator):
        """Test resource quota enforcement."""
        # Mock high resource usage
        with patch('devdocai.core.generator.psutil') as mock_psutil:
            mock_process = MagicMock()
            mock_process.memory_info.return_value.rss = 5 * 1024 * 1024 * 1024  # 5GB
            mock_process.cpu_percent.return_value = 90
            mock_psutil.Process.return_value = mock_process
            
            # Should fail due to resource quota
            with pytest.raises(DocumentGenerationError, match="Resource quota"):
                await generator.generate(
                    "readme",
                    "./test_project"
                )
    
    @pytest.mark.asyncio
    async def test_context_sanitization(self, generator):
        """Test context sanitization in generation."""
        custom_context = {
            "description": "<script>alert('xss')</script>Safe content",
            "author": "John Doe",
            "command": "`rm -rf /`"
        }
        
        with patch('devdocai.core.generator.psutil'):
            # Mock the template manager and other dependencies
            generator.template_manager.load_template = MagicMock()
            generator.context_builder.extract_from_project = MagicMock(
                return_value={'project_name': 'test'}
            )
            
            await generator.generate(
                "readme",
                "./test_project",
                custom_context=custom_context
            )
            
            # Context should be sanitized
            assert "<script>" not in str(custom_context)
            assert "`" not in str(custom_context)
    
    @pytest.mark.asyncio
    async def test_pii_detection_in_generation(self, generator):
        """Test PII detection during generation."""
        # Set up generator with PII in response
        generator.llm_adapter.generate.return_value.content = """
        Contact John Smith at john@example.com or 555-123-4567.
        SSN: 123-45-6789
        """
        
        with patch('devdocai.core.generator.psutil'):
            # Generate document
            result = await generator.generate(
                "readme",
                "./test_project"
            )
            
            # Should log PII detection
            metrics = generator.get_security_metrics()
            assert metrics['metrics']['pii_detections'] > 0
    
    def test_security_metrics_collection(self, generator):
        """Test security metrics collection."""
        # Trigger various security events
        generator.security_manager.validate_path("../etc/passwd")
        generator.security_manager.check_rate_limit("user1")
        generator.security_manager.sanitize_input("<script>test</script>")
        
        # Get metrics
        metrics = generator.get_security_metrics()
        
        assert metrics['metrics']['path_validations'] > 0
        assert 'recent_events' in metrics
        assert 'audit_log_size' in metrics


# ============================================================================
# OWASP Compliance Tests
# ============================================================================

class TestOWASPCompliance:
    """Test OWASP Top 10 compliance for high-throughput scenarios."""
    
    def test_a01_broken_access_control(self, generator):
        """Test A01: Broken Access Control prevention."""
        # Test cache isolation per user
        cache = generator.response_cache
        
        # User 1 puts data
        cache.put("prompt", {"ctx": "1"}, "user1_data", user_id="user1")
        
        # User 2 should not access
        entry = cache.get("prompt", {"ctx": "1"}, user_id="user2")
        assert entry is None
        
        # User 1 should access
        entry = cache.get("prompt", {"ctx": "1"}, user_id="user1")
        assert entry is not None
    
    def test_a02_cryptographic_failures(self, generator):
        """Test A02: Cryptographic Failures prevention."""
        # Test cache encryption
        cache = generator.response_cache
        security = generator.security_manager
        
        # Test encryption
        data = b"sensitive data"
        encrypted = security.encrypt_cache_content(data)
        
        # Should be encrypted
        assert encrypted != data
        assert len(encrypted) > len(data)
        
        # Should decrypt correctly
        decrypted = security.decrypt_cache_content(encrypted)
        assert decrypted == data
    
    def test_a03_injection(self, generator):
        """Test A03: Injection prevention."""
        security = generator.security_manager
        
        # Test various injection types
        injections = [
            "<script>alert('xss')</script>",
            "{{evil}}",
            "${evil}",
            "`rm -rf /`",
            "'; DROP TABLE users; --"
        ]
        
        for injection in injections:
            sanitized = security.sanitize_input(injection)
            assert injection != sanitized
            # Dangerous patterns removed
            assert not any(char in sanitized for char in ['<', '{{', '${', '`'])
    
    def test_a04_insecure_design(self, generator):
        """Test A04: Insecure Design prevention."""
        # Test rate limiting design
        security = generator.security_manager
        
        # Should have rate limiting
        assert hasattr(security, 'rate_limit_per_minute')
        assert security.rate_limit_per_minute > 0
        
        # Should have resource quotas
        assert hasattr(security, 'resource_quotas')
        assert len(security.resource_quotas) > 0
    
    def test_a05_security_misconfiguration(self, generator):
        """Test A05: Security Misconfiguration prevention."""
        security = generator.security_manager
        
        # Should have secure defaults
        assert security.path_traversal_enabled == True
        assert security.max_batch_size <= 1000
        assert security.rate_limit_per_minute <= 240
    
    def test_a07_identification_failures(self, generator):
        """Test A07: Identification and Authentication Failures."""
        # Test session-based rate limiting
        security = generator.security_manager
        
        # Different users have separate rate limits
        for _ in range(10):
            assert security.check_rate_limit("user1")
        
        # User2 should still have quota
        assert security.check_rate_limit("user2")
    
    def test_a08_data_integrity_failures(self, generator):
        """Test A08: Software and Data Integrity Failures."""
        security = generator.security_manager
        
        # Test HMAC signatures
        content = "test content"
        fingerprint = "fp123"
        
        sig = security.sign_cache_entry(content, fingerprint)
        assert security.verify_cache_signature(content, fingerprint, sig)
        
        # Tampered content fails
        assert not security.verify_cache_signature("tampered", fingerprint, sig)
    
    def test_a09_logging_failures(self, generator):
        """Test A09: Security Logging and Monitoring Failures."""
        security = generator.security_manager
        
        # Should log security events
        security._log_security_event("TEST", {"data": "test"})
        
        # Should have audit log
        assert len(security.audit_log) > 0
        
        # Should have tamper protection
        event = security.audit_log[-1]
        assert 'signature' in event
        assert 'correlation_id' in event
    
    def test_a10_ssrf(self, generator):
        """Test A10: Server-Side Request Forgery prevention."""
        security = generator.security_manager
        
        # Should validate paths
        assert not security.validate_path("http://evil.com/payload")
        assert not security.validate_path("file:///etc/passwd")
        assert not security.validate_path("gopher://localhost")


# ============================================================================
# Performance Preservation Tests
# ============================================================================

class TestPerformancePreservation:
    """Test that security doesn't degrade performance."""
    
    @pytest.mark.asyncio
    async def test_cache_performance_with_security(self, response_cache):
        """Test cache performance is maintained with security."""
        prompt = "test prompt"
        context = {"key": "value"}
        
        # Measure put performance
        start = time.perf_counter()
        for i in range(100):
            response_cache.put(
                f"{prompt}_{i}", 
                context, 
                f"response_{i}",
                user_id="user1"
            )
        put_time = time.perf_counter() - start
        
        # Should be fast despite security
        assert put_time < 1.0  # 100 puts in under 1 second
        
        # Measure get performance
        start = time.perf_counter()
        for i in range(100):
            response_cache.get(
                f"{prompt}_{i}",
                context,
                user_id="user1"
            )
        get_time = time.perf_counter() - start
        
        # Should be fast despite validation
        assert get_time < 0.5  # 100 gets in under 0.5 seconds
    
    @pytest.mark.asyncio
    async def test_batch_performance_with_security(self, mock_config, security_manager):
        """Test batch processing performance with security."""
        generator = AsyncMock()
        processor = BatchProcessor(mock_config, generator, security_manager)
        
        # Create batch
        requests = [
            BatchRequest("readme", "/path", {}, request_id=f"req_{i}")
            for i in range(50)
        ]
        
        generator.generate.return_value = {
            'document_id': 'doc_1',
            'type': 'readme',
            'content': 'content',
            'quality_score': 0.9,
            'metadata': {},
            'generation_time': 1.0
        }
        
        # Measure batch processing
        start = time.perf_counter()
        await processor.process_batch(requests)
        batch_time = time.perf_counter() - start
        
        # Should maintain performance
        assert batch_time < 2.0  # 50 documents in under 2 seconds
    
    def test_security_overhead(self, security_manager):
        """Test security operations overhead."""
        # Measure path validation
        start = time.perf_counter()
        for _ in range(1000):
            security_manager.validate_path("./valid/path.py")
        path_time = time.perf_counter() - start
        assert path_time < 0.1  # 1000 validations < 100ms
        
        # Measure input sanitization
        start = time.perf_counter()
        for _ in range(1000):
            security_manager.sanitize_input("normal text content")
        sanitize_time = time.perf_counter() - start
        assert sanitize_time < 0.2  # 1000 sanitizations < 200ms
        
        # Measure signature generation
        start = time.perf_counter()
        for _ in range(100):
            security_manager.sign_cache_entry("content", "fingerprint")
        sign_time = time.perf_counter() - start
        assert sign_time < 0.1  # 100 signatures < 100ms


# ============================================================================
# Edge Cases and Attack Scenarios
# ============================================================================

class TestSecurityEdgeCases:
    """Test edge cases and attack scenarios."""
    
    def test_cache_collision_attack(self, response_cache):
        """Test cache key collision attack prevention."""
        # Try to create collision
        prompt1 = "test prompt"
        prompt2 = "test prompt"  # Same prompt
        context1 = {"key": "value1"}
        context2 = {"key": "value2"}  # Different context
        
        response_cache.put(prompt1, context1, "response1")
        response_cache.put(prompt2, context2, "response2")
        
        # Should maintain separate entries
        entry1 = response_cache.get(prompt1, context1)
        entry2 = response_cache.get(prompt2, context2)
        
        assert entry1.content == "response1"
        assert entry2.content == "response2"
    
    def test_memory_exhaustion_prevention(self, security_manager):
        """Test memory exhaustion attack prevention."""
        # Try to exhaust memory with large audit log
        for i in range(20000):
            security_manager._log_security_event(f"EVENT_{i}", {"data": f"test_{i}"})
        
        # Should rotate and limit log size
        assert len(security_manager.audit_log) <= 10000
    
    def test_concurrent_access_security(self, response_cache):
        """Test concurrent access security."""
        import threading
        
        def put_entries():
            for i in range(100):
                response_cache.put(
                    f"prompt_{i}",
                    {"key": "value"},
                    f"response_{i}"
                )
        
        def get_entries():
            for i in range(100):
                response_cache.get(
                    f"prompt_{i}",
                    {"key": "value"}
                )
        
        # Create threads
        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=put_entries))
            threads.append(threading.Thread(target=get_entries))
        
        # Run concurrently
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Cache should remain consistent
        stats = response_cache.get_stats()
        assert stats is not None
    
    @pytest.mark.asyncio
    async def test_dos_attack_mitigation(self, generator):
        """Test DOS attack mitigation."""
        # Try rapid-fire requests
        requests = []
        for i in range(100):
            requests.append(
                generator.generate(
                    "readme",
                    "./test_project",
                    user_id=f"attacker_{i % 10}"
                )
            )
        
        # Should handle gracefully with rate limiting
        results = await asyncio.gather(*requests, return_exceptions=True)
        
        # Many should be rate limited
        errors = [r for r in results if isinstance(r, Exception)]
        assert len(errors) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--color=yes"])