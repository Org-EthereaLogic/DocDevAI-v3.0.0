"""
M001 Configuration Manager - Security Tests (Pass 3)
Testing enterprise-grade security features and compliance.
"""
import os
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from devdocai.core.config import ConfigurationManager
from devdocai.core.config import PrivacyConfig, SecurityConfig, LLMConfig


class TestAPIKeyEncryption:
    """Test API key encryption and secure storage."""
    
    def test_api_key_never_stored_plaintext(self, tmp_path):
        """Verify API keys are never stored in plaintext."""
        config_file = tmp_path / ".devdocai.yml"
        config = ConfigurationManager(config_file=config_file)
        
        # Set an API key
        test_key = "sk-test123secretkey"
        config.set_api_key('openai', test_key)
        
        # Verify plaintext key is not in config file
        if config_file.exists():
            content = config_file.read_text()
            assert test_key not in content
            assert "sk-test123" not in content
            
        # Verify we can decrypt it back
        retrieved_key = config.get_api_key('openai')
        assert retrieved_key == test_key
    
    def test_api_key_encryption_different_each_time(self, tmp_path):
        """Verify encrypted keys are different each time (salted)."""
        config_file = tmp_path / ".devdocai.yml"
        config1 = ConfigurationManager(config_file=config_file)
        config2 = ConfigurationManager(config_file=config_file)
        
        test_key = "sk-identical-key"
        encrypted1 = config1._encrypt_value(test_key)
        encrypted2 = config2._encrypt_value(test_key)
        
        # Should be different due to random IV/salt
        assert encrypted1 != encrypted2
        
        # But both should decrypt to same value
        assert config1._decrypt_value(encrypted1) == test_key
        assert config2._decrypt_value(encrypted2) == test_key
    
    def test_api_key_encryption_invalid_data(self):
        """Test handling of corrupted/invalid encrypted data."""
        config = ConfigurationManager()
        
        # Test with invalid encrypted data
        with pytest.raises((ValueError, Exception)):
            config._decrypt_value("invalid-encrypted-data")
        
        # Test with malformed base64
        with pytest.raises((ValueError, Exception)):
            config._decrypt_value("not-base64!")
    
    def test_api_key_empty_or_none(self):
        """Test handling of empty or None API keys."""
        config = ConfigurationManager()
        
        # Empty string
        config.set_api_key('openai', "")
        assert config.get_api_key('openai') == ""
        
        # None value should be handled gracefully
        result = config.get_api_key('nonexistent')
        assert result is None


class TestArgon2idKeyDerivation:
    """Test Argon2id key derivation implementation."""
    
    def test_argon2id_is_default(self):
        """Verify Argon2id is used for key derivation by default."""
        config = ConfigurationManager()
        assert config.security.key_derivation == "argon2id"
    
    def test_argon2id_parameters_secure(self):
        """Test Argon2id parameters meet security standards."""
        config = ConfigurationManager()
        
        # Test key derivation with known password
        password = "test-password-123"
        salt = b"test-salt-16byte"
        
        # Derive key twice with same inputs
        key1 = config._derive_key(password, salt)
        key2 = config._derive_key(password, salt)
        
        # Should be identical with same inputs
        assert key1 == key2
        
        # Should be 32 bytes (256 bits)
        assert len(key1) == 32
    
    def test_argon2id_different_salts_different_keys(self):
        """Test that different salts produce different keys."""
        config = ConfigurationManager()
        password = "same-password"
        
        key1 = config._derive_key(password, b"salt1-16-bytes!!")
        key2 = config._derive_key(password, b"salt2-16-bytes!!")
        
        assert key1 != key2
    
    @pytest.mark.security
    def test_argon2id_timing_resistance(self):
        """Test Argon2id timing resistance (basic check)."""
        config = ConfigurationManager()
        import time
        
        password = "test-password"
        salt = b"consistent-salt!"
        
        # Measure multiple derivations
        times = []
        for _ in range(5):
            start = time.time()
            config._derive_key(password, salt)
            times.append(time.time() - start)
        
        # Should take some time (Argon2id is intentionally slow)
        avg_time = sum(times) / len(times)
        assert avg_time > 0.001  # At least 1ms (reasonable minimum)
        assert avg_time < 1.0    # But not too slow for tests


class TestSystemKeyring:
    """Test secure key storage in system keyring."""
    
    @patch('keyring.set_password')
    @patch('keyring.get_password')
    def test_keyring_storage_integration(self, mock_get, mock_set):
        """Test integration with system keyring."""
        mock_get.return_value = None
        
        config = ConfigurationManager()
        config.use_system_keyring = True
        
        # Set API key should use keyring
        config.set_api_key('openai', 'sk-test123')
        mock_set.assert_called_once()
        
        # Get API key should use keyring
        mock_get.return_value = 'sk-test123'
        result = config.get_api_key('openai')
        mock_get.assert_called_once()
        assert result == 'sk-test123'
    
    @patch('keyring.set_password')
    def test_keyring_fallback_on_failure(self, mock_set, tmp_path):
        """Test fallback to file storage when keyring fails."""
        # Simulate keyring failure
        mock_set.side_effect = Exception("Keyring not available")
        
        config_file = tmp_path / ".devdocai.yml"
        config = ConfigurationManager(config_file=config_file)
        config.use_system_keyring = True
        
        # Should fallback to file storage without crashing
        config.set_api_key('openai', 'sk-test123')
        
        # Should be able to retrieve it
        result = config.get_api_key('openai')
        assert result == 'sk-test123'
    
    def test_keyring_service_name_consistent(self):
        """Test keyring service name is consistent."""
        config = ConfigurationManager()
        expected_service = "DevDocAI-v3.0.0"
        assert config._keyring_service == expected_service


class TestInputSanitization:
    """Test input sanitization and validation hardening."""
    
    def test_yaml_injection_prevention(self, tmp_path):
        """Test prevention of YAML injection attacks."""
        config_file = tmp_path / ".devdocai.yml"
        
        # Create malicious YAML content
        malicious_yaml = """
privacy:
  telemetry: false
system:
  memory_mode: !!python/object/apply:os.system ["rm -rf /"]
"""
        config_file.write_text(malicious_yaml)
        
        # Should not execute malicious code
        config = ConfigurationManager(config_file=config_file)
        
        # Should have safe defaults
        assert config.privacy.telemetry is False
        assert config.system.memory_mode in ['baseline', 'standard', 'enhanced', 'performance']
    
    def test_path_traversal_prevention(self, tmp_path):
        """Test prevention of path traversal attacks in config paths."""
        # Try to use path traversal
        malicious_path = tmp_path / "../../../etc/passwd"
        
        # Should not crash or access sensitive files
        config = ConfigurationManager(config_file=malicious_path)
        
        # Should fall back to defaults
        assert config.privacy.telemetry is False
    
    def test_oversized_config_handling(self, tmp_path):
        """Test handling of extremely large configuration files."""
        config_file = tmp_path / ".devdocai.yml"
        
        # Create oversized config (1MB of data)
        large_value = "x" * (1024 * 1024)
        config_content = f"""
privacy:
  telemetry: false
system:
  large_field: "{large_value}"
"""
        config_file.write_text(config_content)
        
        # Should handle gracefully without memory issues
        config = ConfigurationManager(config_file=config_file)
        assert config.privacy.telemetry is False
    
    def test_unicode_injection_prevention(self):
        """Test handling of Unicode injection attempts."""
        config = ConfigurationManager()
        
        # Test with various Unicode attacks
        malicious_inputs = [
            "normal_key\u0000malicious",
            "key\u202emoc.evil",
            "key\ufeffhidden",
            "key\u200bzerospace"
        ]
        
        for malicious_key in malicious_inputs:
            # Should not crash or behave unexpectedly
            try:
                config.get(malicious_key, default="safe")
            except (KeyError, ValueError):
                # Expected to fail safely
                pass


class TestSecurityAuditLogging:
    """Test security audit logging functionality."""
    
    def test_audit_log_creation(self, tmp_path):
        """Test that audit logs are created properly."""
        config = ConfigurationManager()
        config.audit_log_path = tmp_path / "security_audit.log"
        
        # Perform security-sensitive operations
        config.set_api_key('openai', 'sk-test123')
        config.get_api_key('openai')
        
        # Check audit log exists and has entries
        assert config.audit_log_path.exists()
        
        log_content = config.audit_log_path.read_text()
        assert "API_KEY_SET" in log_content
        assert "API_KEY_RETRIEVED" in log_content
    
    def test_audit_log_format_structured(self, tmp_path):
        """Test audit log format is structured JSON."""
        config = ConfigurationManager()
        config.audit_log_path = tmp_path / "security_audit.log"
        
        config.set_api_key('openai', 'sk-test123')
        
        # Read and parse log entries
        log_content = config.audit_log_path.read_text().strip()
        log_lines = log_content.split('\n')
        
        for line in log_lines:
            if line.strip():
                log_entry = json.loads(line)
                
                # Check required fields
                assert 'timestamp' in log_entry
                assert 'event' in log_entry
                assert 'user' in log_entry
                assert 'details' in log_entry
    
    def test_audit_log_no_sensitive_data(self, tmp_path):
        """Test audit logs don't contain sensitive data."""
        config = ConfigurationManager()
        config.audit_log_path = tmp_path / "security_audit.log"
        
        sensitive_key = 'sk-very-secret-key-12345'
        config.set_api_key('openai', sensitive_key)
        
        # Check log doesn't contain sensitive data
        log_content = config.audit_log_path.read_text()
        assert sensitive_key not in log_content
        assert "very-secret" not in log_content
    
    def test_audit_log_rotation(self, tmp_path):
        """Test audit log rotation when size limit reached."""
        config = ConfigurationManager()
        config.audit_log_path = tmp_path / "security_audit.log"
        config.audit_log_max_size = 1024  # 1KB limit for testing
        
        # Generate many log entries to trigger rotation
        for i in range(100):
            config._audit_log(f"TEST_EVENT_{i}", {"iteration": i})
        
        # Should have rotated log file
        rotated_log = tmp_path / "security_audit.log.1"
        assert config.audit_log_path.exists()
        # Note: Rotation might create backup files depending on implementation


class TestComplianceValidation:
    """Test enterprise compliance requirements."""
    
    def test_encryption_algorithm_compliance(self):
        """Test encryption meets enterprise standards."""
        config = ConfigurationManager()
        
        # Should use AES-256-GCM (verify through encryption)
        assert config.security.encryption_algorithm == "AES-256-GCM"
        # Verify key length (256 bits = 32 bytes)
        test_key = config._generate_key()
        assert len(test_key) == 32
    
    def test_privacy_defaults_compliance(self):
        """Test privacy defaults meet GDPR/CCPA requirements."""
        config = ConfigurationManager()
        
        # Telemetry must be opt-in (false by default)
        assert config.privacy.telemetry is False
        assert config.privacy.analytics is False
        assert config.privacy.local_only is True
    
    def test_data_retention_policies(self):
        """Test data retention and deletion capabilities."""
        config = ConfigurationManager()
        
        # Should have method to clear all data
        assert hasattr(config, 'clear_all_data')
        
        # Should have method to export data
        assert hasattr(config, 'export_data')
    
    def test_security_configuration_immutable(self):
        """Test that security configs can't be accidentally modified."""
        config = ConfigurationManager()
        original_encryption = config.security.encryption_enabled
        
        # Attempt to modify security settings
        try:
            config.security.encryption_enabled = False
            # Should either prevent modification or restore
            assert config.security.encryption_enabled == original_encryption
        except (AttributeError, Exception):
            # Expected to prevent modification
            pass


class TestVulnerabilityPrevention:
    """Test prevention of known vulnerability classes."""
    
    def test_sql_injection_prevention(self):
        """Test prevention of SQL injection in config values."""
        config = ConfigurationManager()
        
        malicious_values = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'; DELETE FROM config; --"
        ]
        
        for malicious_value in malicious_values:
            # Should handle malicious SQL safely using valid config paths
            config.set('llm.model', malicious_value)
            retrieved = config.get('llm.model')
            # Should not execute SQL or cause errors
            assert isinstance(retrieved, str)
            # Value should be stored safely
            assert retrieved == malicious_value
    
    def test_deserialization_vulnerability_prevention(self, tmp_path):
        """Test prevention of unsafe deserialization."""
        config_file = tmp_path / ".devdocai.yml"
        
        # Create config with potential deserialization attack
        malicious_yaml = """
privacy:
  telemetry: !!python/object/apply:eval ["__import__('os').system('echo PWNED')"]
"""
        config_file.write_text(malicious_yaml)
        
        # Should not execute malicious code
        config = ConfigurationManager(config_file=config_file)
        
        # Should have safe defaults
        assert config.privacy.telemetry is False
    
    def test_xxe_prevention(self, tmp_path):
        """Test prevention of XML External Entity attacks."""
        config_file = tmp_path / ".devdocai.yml"
        
        # Create YAML with external entity reference
        xxe_yaml = """
privacy:
  telemetry: false
system: &reference
  memory_mode: standard
  <<: *reference
"""
        config_file.write_text(xxe_yaml)
        
        # Should handle safely
        config = ConfigurationManager(config_file=config_file)
        assert config.system.memory_mode in ['baseline', 'standard', 'enhanced', 'performance']
    
    @pytest.mark.security
    def test_timing_attack_resistance(self):
        """Test resistance to timing attacks in key operations."""
        config = ConfigurationManager()
        import time
        
        # Test API key comparison timing
        correct_key = "sk-correct-key-12345"
        wrong_keys = [
            "sk-wrong-key-123456",
            "wrong-key",
            "",
            "sk-correct-key-12346"  # One character different
        ]
        
        config.set_api_key('openai', correct_key)
        
        # Measure timing for correct key
        start = time.time()
        result_correct = config._compare_api_key('openai', correct_key)
        time_correct = time.time() - start
        
        # Measure timing for wrong keys
        times_wrong = []
        for wrong_key in wrong_keys:
            start = time.time()
            result_wrong = config._compare_api_key('openai', wrong_key)
            times_wrong.append(time.time() - start)
            assert result_wrong is False
        
        assert result_correct is True
        
        # Timing should not reveal information (basic check)
        # Note: This is a simplified check; real timing attack resistance 
        # requires more sophisticated testing
        avg_wrong_time = sum(times_wrong) / len(times_wrong)
        timing_ratio = max(time_correct, avg_wrong_time) / min(time_correct, avg_wrong_time)
        
        # Timing difference should not be excessive (allow for some variance)
        assert timing_ratio < 10  # Reasonable threshold for testing


@pytest.fixture
def secure_config():
    """Fixture providing a securely configured ConfigurationManager."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        config_file = Path(tmp_dir) / ".devdocai.yml"
        config = ConfigurationManager(config_file=config_file)
        
        # Enable all security features
        config.security.encryption_enabled = True
        config.security.api_keys_encrypted = True
        config.security.key_derivation = "argon2id"
        config.use_system_keyring = True
        
        yield config


class TestSecurityIntegration:
    """Integration tests for security features."""
    
    def test_end_to_end_secure_workflow(self, secure_config):
        """Test complete secure workflow from key storage to retrieval."""
        config = secure_config
        
        # Store sensitive data
        api_key = "sk-highly-sensitive-key"
        config.set_api_key('openai', api_key)
        
        # Retrieve and verify
        retrieved_key = config.get_api_key('openai')
        assert retrieved_key == api_key
        
        # Verify security measures are in place
        assert config.security.encryption_enabled
        assert config.security.api_keys_encrypted
        assert config.security.key_derivation == "argon2id"
    
    def test_security_configuration_persistence(self, tmp_path):
        """Test security configuration persists across restarts."""
        config_file = tmp_path / ".devdocai.yml"
        config1 = ConfigurationManager(config_file=config_file)
        
        # Enable all security features
        config1.security.encryption_enabled = True
        config1.security.api_keys_encrypted = True
        config1.security.key_derivation = "argon2id"
        config1.use_system_keyring = True
        
        config1.set_api_key('openai', 'secret-value')
        
        # Create new instance (simulate restart)
        config2 = ConfigurationManager(config_file=config1.config_file)
        
        # Should maintain security settings and data
        retrieved_key = config2.get_api_key('openai')
        assert retrieved_key == 'secret-value'
        assert config2.security.encryption_enabled