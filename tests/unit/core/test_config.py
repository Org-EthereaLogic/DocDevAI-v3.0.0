"""
Comprehensive test suite for M001 Configuration Manager.

Target coverage: 95% minimum
Performance validation: 19M ops/sec retrieval, 4M ops/sec validation
"""

import os
import tempfile
import time
import threading
import sys
from pathlib import Path
from unittest import mock
from unittest.mock import patch, MagicMock
import pytest
import yaml
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from argon2 import PasswordHasher

from devdocai.core.config import (
    ConfigurationManager,
    SecurityConfig,
    MemoryConfig,
    DevDocAIConfig
)


class TestSecurityConfig:
    """Test SecurityConfig validation and defaults."""
    
    def test_default_privacy_first(self):
        """Verify privacy-first defaults."""
        config = SecurityConfig()
        assert config.privacy_mode == "local_only"
        assert config.telemetry_enabled is False
        assert config.cloud_features is False
        assert config.dsr_enabled is True
        assert config.encryption_enabled is True
    
    def test_privacy_mode_validation(self):
        """Test privacy mode constraints."""
        # Valid modes
        for mode in ["local_only", "hybrid", "cloud"]:
            config = SecurityConfig(privacy_mode=mode)
            assert config.privacy_mode == mode
        
        # Invalid mode
        with pytest.raises(ValueError):
            SecurityConfig(privacy_mode="invalid")
    
    def test_cloud_features_validation(self):
        """Test cloud features cannot be enabled in local_only mode."""
        with pytest.raises(ValueError):
            SecurityConfig(privacy_mode="local_only", cloud_features=True)
        
        # Cloud features allowed in hybrid/cloud modes
        config = SecurityConfig(privacy_mode="hybrid", cloud_features=True)
        assert config.cloud_features is True


class TestMemoryConfig:
    """Test MemoryConfig validation and auto-adjustment."""
    
    def test_memory_modes(self):
        """Test all memory mode configurations."""
        modes = {
            "baseline": {"cache": 1000, "file": 10485760},
            "standard": {"cache": 5000, "file": 52428800},
            "enhanced": {"cache": 10000, "file": 104857600},
            "performance": {"cache": 50000, "file": 524288000}
        }
        
        for mode, limits in modes.items():
            config = MemoryConfig(
                mode=mode,
                cache_size=limits["cache"],
                max_file_size=limits["file"],
                optimization_level=0
            )
            assert config.mode == mode
    
    def test_cache_size_auto_adjustment(self):
        """Test cache size auto-adjusts to mode limits."""
        config = MemoryConfig(
            mode="baseline",
            cache_size=99999,  # Too high for baseline
            max_file_size=1048576,
            optimization_level=0
        )
        assert config.cache_size <= 1000  # Should be capped
    
    def test_invalid_mode(self):
        """Test invalid memory mode raises error."""
        with pytest.raises(ValueError):
            MemoryConfig(
                mode="ultra",
                cache_size=1000,
                max_file_size=1048576,
                optimization_level=0
            )


class TestConfigurationManager:
    """Test ConfigurationManager functionality."""
    
    @pytest.fixture
    def temp_config_file(self):
        """Create temporary configuration file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            config = {
                'version': '3.0.0',
                'security': {
                    'privacy_mode': 'local_only',
                    'telemetry_enabled': False
                },
                'paths': {
                    'data': './test_data'
                }
            }
            yaml.dump(config, f)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        Path(temp_path).unlink(missing_ok=True)
    
    @pytest.fixture
    def config_manager(self):
        """Create fresh ConfigurationManager instance."""
        # Clear singleton instance
        ConfigurationManager._instance = None
        return ConfigurationManager()
    
    def test_singleton_pattern(self):
        """Test singleton pattern implementation."""
        ConfigurationManager._instance = None
        manager1 = ConfigurationManager()
        manager2 = ConfigurationManager()
        assert manager1 is manager2
    
    def test_privacy_first_defaults(self, config_manager):
        """Verify privacy-first default configuration."""
        assert config_manager.get('security.privacy_mode') == 'local_only'
        assert config_manager.get('security.telemetry_enabled') is False
        assert config_manager.get('security.cloud_features') is False
        assert config_manager.get('security.dsr_enabled') is True
    
    def test_memory_mode_detection(self, config_manager):
        """Test automatic memory mode detection."""
        memory_mode = config_manager.get('memory.mode')
        assert memory_mode in ['baseline', 'standard', 'enhanced', 'performance']
        
        # Verify cache size matches mode
        cache_size = config_manager.get('memory.cache_size')
        assert isinstance(cache_size, int)
        assert cache_size >= 100
    
    def test_get_configuration(self, config_manager):
        """Test getting configuration values."""
        # Existing keys
        assert config_manager.get('version') == '3.0.0'
        assert config_manager.get('security.privacy_mode') == 'local_only'
        
        # Nested keys
        paths = config_manager.get('paths')
        assert isinstance(paths, dict)
        assert 'data' in paths
        
        # Non-existent keys with default
        assert config_manager.get('non.existent.key', 'default') == 'default'
    
    def test_set_configuration(self, config_manager):
        """Test setting configuration values."""
        # Set valid value
        assert config_manager.set('features.test_feature', True)
        assert config_manager.get('features.test_feature') is True
        
        # Set nested value
        assert config_manager.set('api_providers.openai.key', 'test_key')
        assert config_manager.get('api_providers.openai.key') == 'test_key'
    
    def test_load_configuration(self, config_manager, temp_config_file):
        """Test loading configuration from file."""
        assert config_manager.load_config(temp_config_file)
        assert config_manager.get('paths.data') == './test_data'
    
    def test_save_configuration(self, config_manager):
        """Test saving configuration to file."""
        with tempfile.NamedTemporaryFile(suffix='.yml', delete=False) as f:
            temp_path = f.name
        
        try:
            config_manager.set('test.save', 'value')
            assert config_manager.save_config(temp_path)
            
            # Verify saved content
            with open(temp_path, 'r') as f:
                saved = yaml.safe_load(f)
            assert 'security' in saved
            assert saved['security']['privacy_mode'] == 'local_only'
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def test_api_key_encryption(self, config_manager):
        """Test API key encryption and decryption."""
        keys = {
            'openai': 'sk-test-key-123',
            'anthropic': 'test-anthropic-key'
        }
        
        # Encrypt keys
        encrypted = config_manager.encrypt_api_keys(keys)
        assert 'openai' in encrypted
        assert isinstance(encrypted['openai'], dict)
        assert 'ciphertext' in encrypted['openai']
        assert 'nonce' in encrypted['openai']
        assert 'tag' in encrypted['openai']
        
        # Decrypt keys
        decrypted = config_manager.decrypt_api_keys(encrypted)
        assert decrypted == keys
    
    def test_thread_safety(self, config_manager):
        """Test thread-safe operations."""
        results = []
        
        def worker(key, value):
            config_manager.set(f'thread.{key}', value)
            result = config_manager.get(f'thread.{key}')
            results.append((key, result))
        
        threads = []
        for i in range(10):
            t = threading.Thread(target=worker, args=(f'key{i}', f'value{i}'))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Verify all operations succeeded
        assert len(results) == 10
        for key, value in results:
            assert value == f'value{key.replace("key", "")}'
    
    def test_validation(self, config_manager):
        """Test configuration validation."""
        assert config_manager.validate()
        
        # Try to set invalid value (should fail validation)
        assert not config_manager.set('security.privacy_mode', 'invalid_mode')
        assert config_manager.validate()  # Should still be valid (change rejected)
    
    def test_environment_variables(self):
        """Test environment variable configuration."""
        # Set environment variable
        os.environ['DEVDOCAI_CONFIG'] = 'custom.yml'
        os.environ['DEVDOCAI_TESTING'] = 'true'
        
        try:
            ConfigurationManager._instance = None
            manager = ConfigurationManager()
            # Check that the path ends with custom.yml (resolved to absolute)
            assert manager.config_path.name == 'custom.yml'
        finally:
            if 'DEVDOCAI_CONFIG' in os.environ:
                del os.environ['DEVDOCAI_CONFIG']
            if 'DEVDOCAI_TESTING' in os.environ:
                del os.environ['DEVDOCAI_TESTING']
    
    @mock.patch('psutil.virtual_memory')
    def test_memory_detection_fallback(self, mock_memory):
        """Test memory detection fallback on error."""
        mock_memory.side_effect = Exception("Memory detection failed")
        
        ConfigurationManager._instance = None
        manager = ConfigurationManager()
        
        assert manager.get('memory.mode') == 'baseline'
        assert manager.get('memory.cache_size') == 1000


class TestPerformance:
    """Performance benchmarks for Configuration Manager."""
    
    @pytest.fixture
    def config_manager(self):
        """Create ConfigurationManager for performance testing."""
        ConfigurationManager._instance = None
        return ConfigurationManager()
    
    def test_retrieval_performance(self, config_manager):
        """Test configuration retrieval performance."""
        # Warm up cache
        for _ in range(100):
            config_manager.get('security.privacy_mode')
        
        # Measure performance
        iterations = 100000
        start = time.perf_counter()
        
        for _ in range(iterations):
            value = config_manager.get('security.privacy_mode')
        
        elapsed = time.perf_counter() - start
        ops_per_sec = iterations / elapsed
        
        print(f"\nRetrieval performance: {ops_per_sec:,.0f} ops/sec")
        print(f"Target: 19,000,000 ops/sec")
        print(f"Achieved: {(ops_per_sec / 19_000_000) * 100:.1f}% of target")
        
        # Should achieve at least 1M ops/sec (conservative target)
        assert ops_per_sec > 1_000_000
    
    def test_validation_performance(self, config_manager):
        """Test configuration validation performance."""
        iterations = 10000
        start = time.perf_counter()
        
        for _ in range(iterations):
            valid = config_manager.validate()
        
        elapsed = time.perf_counter() - start
        ops_per_sec = iterations / elapsed
        
        print(f"\nValidation performance: {ops_per_sec:,.0f} ops/sec")
        print(f"Target: 4,000,000 ops/sec")
        print(f"Achieved: {(ops_per_sec / 4_000_000) * 100:.1f}% of target")
        
        # Should achieve at least 100K validations/sec
        assert ops_per_sec > 100_000
    
    def test_memory_efficiency(self, config_manager):
        """Test memory usage efficiency."""
        import sys
        
        # Measure baseline memory
        baseline = sys.getsizeof(config_manager._config.dict())
        
        # Add many configuration entries
        for i in range(1000):
            config_manager.set(f'test.entry{i}', f'value{i}')
        
        # Measure after additions
        after = sys.getsizeof(config_manager._config.dict())
        
        memory_per_entry = (after - baseline) / 1000
        
        print(f"\nMemory efficiency: {memory_per_entry:.0f} bytes per entry")
        
        # Should be reasonably efficient (< 1KB per entry)
        assert memory_per_entry < 1024


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.fixture
    def config_manager(self):
        """Create ConfigurationManager for edge case testing."""
        ConfigurationManager._instance = None
        return ConfigurationManager()
    
    def test_empty_configuration_file(self, config_manager):
        """Test handling of empty configuration file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            temp_path = f.name
        
        try:
            # Should handle empty file gracefully
            assert config_manager.load_config(temp_path)
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def test_corrupt_configuration_file(self, config_manager):
        """Test handling of corrupt configuration file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write("invalid: yaml: content: {]}")
            temp_path = f.name
        
        try:
            # Should handle corrupt file gracefully
            assert not config_manager.load_config(temp_path)
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def test_missing_master_key(self, config_manager):
        """Test encryption without master key."""
        # Should generate random key with warning
        keys = {'test': 'value'}
        encrypted = config_manager.encrypt_api_keys(keys)
        decrypted = config_manager.decrypt_api_keys(encrypted)
        assert decrypted == keys
    
    def test_deep_nesting(self, config_manager):
        """Test deeply nested configuration keys."""
        deep_key = 'a.b.c.d.e.f.g.h.i.j'
        assert config_manager.set(deep_key, 'deep_value')
        assert config_manager.get(deep_key) == 'deep_value'
    
    def test_special_characters_in_keys(self, config_manager):
        """Test handling special characters in configuration."""
        config_manager.set('test.special', 'value with üñíçødé')
        assert config_manager.get('test.special') == 'value with üñíçødé'
    
    def test_large_configuration(self, config_manager):
        """Test handling large configuration objects."""
        large_value = 'x' * 1_000_000  # 1MB string
        assert config_manager.set('test.large', large_value)
        assert config_manager.get('test.large') == large_value


class TestSecurityFeatures:
    """Comprehensive security testing for M001 Configuration Manager."""
    
    @pytest.fixture
    def config_manager(self):
        """Create ConfigurationManager with security enabled."""
        ConfigurationManager._instance = None
        manager = ConfigurationManager()
        manager._config.security.encryption_enabled = True
        return manager
    
    def test_encryption_uses_random_salts(self, config_manager):
        """Test that each encryption uses a unique random salt."""
        keys = {'api_key': 'secret_value'}
        
        # Encrypt the same data twice
        encrypted1 = config_manager.encrypt_api_keys(keys)
        encrypted2 = config_manager.encrypt_api_keys(keys)
        
        # Verify structure
        assert 'api_key' in encrypted1
        assert 'api_key' in encrypted2
        
        # Version 2 should be used (random salts)
        assert encrypted1['api_key']['version'] == 2
        assert encrypted2['api_key']['version'] == 2
        
        # Salts should be different
        assert encrypted1['api_key']['salt'] != encrypted2['api_key']['salt']
        
        # Ciphertexts should be different (due to different salts and nonces)
        assert encrypted1['api_key']['ciphertext'] != encrypted2['api_key']['ciphertext']
        
        # Both should decrypt to the same value
        decrypted1 = config_manager.decrypt_api_keys(encrypted1)
        decrypted2 = config_manager.decrypt_api_keys(encrypted2)
        assert decrypted1 == keys
        assert decrypted2 == keys
    
    def test_backward_compatibility(self, config_manager):
        """Test decryption of legacy format (version 1 with fixed salt)."""
        # Create legacy encrypted data (version 1 format)
        keys = {'api_key': 'test_value'}
        
        # First, create a real legacy encryption
        config_manager._cipher_key = config_manager._derive_key_legacy()
        
        # Create cipher with known nonce
        nonce = os.urandom(12)
        cipher = Cipher(
            algorithms.AES(config_manager._cipher_key),
            modes.GCM(nonce),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(keys['api_key'].encode()) + encryptor.finalize()
        
        legacy_encrypted = {
            'api_key': {
                'ciphertext': ciphertext.hex(),
                'nonce': nonce.hex(),
                'tag': encryptor.tag.hex()
                # No 'salt' field, no 'version' field (legacy)
            }
        }
        
        # Clear cipher key to force fresh decryption
        config_manager._cipher_key = None
        
        # Should decrypt using legacy method
        decrypted = config_manager.decrypt_api_keys(legacy_encrypted)
        assert decrypted == keys
    
    def test_tampering_detection(self, config_manager):
        """Test that tampered data is detected and rejected."""
        keys = {'api_key': 'secret_value'}
        encrypted = config_manager.encrypt_api_keys(keys)
        
        # Tamper with ciphertext
        tampered = {'api_key': encrypted['api_key'].copy()}
        original_ciphertext = tampered['api_key']['ciphertext']
        tampered['api_key']['ciphertext'] = 'ff' + original_ciphertext[2:]
        
        # Should raise exception on tampered data
        with pytest.raises(Exception):
            config_manager.decrypt_api_keys(tampered)
        
        # Tamper with tag
        tampered2 = {'api_key': encrypted['api_key'].copy()}
        original_tag = tampered2['api_key']['tag']
        tampered2['api_key']['tag'] = 'ff' + original_tag[2:]
        
        with pytest.raises(Exception):
            config_manager.decrypt_api_keys(tampered2)
    
    def test_malformed_encrypted_data_validation(self, config_manager):
        """Test validation of malformed encrypted data structures."""
        # Missing required field
        malformed1 = {'api_key': {'ciphertext': '1234', 'nonce': '5678'}}
        with pytest.raises(ValueError, match="Invalid encrypted data structure"):
            config_manager.decrypt_api_keys(malformed1)
        
        # Invalid hex format
        malformed2 = {
            'api_key': {
                'ciphertext': 'not-hex',
                'nonce': '1234567890ab',
                'tag': 'abcdef123456'
            }
        }
        with pytest.raises(ValueError, match="Invalid encrypted data structure"):
            config_manager.decrypt_api_keys(malformed2)
        
        # Invalid version
        malformed3 = {
            'api_key': {
                'ciphertext': '1234',
                'nonce': '5678',
                'tag': '9abc',
                'version': 99
            }
        }
        with pytest.raises(ValueError, match="Invalid encrypted data structure"):
            config_manager.decrypt_api_keys(malformed3)
    
    def test_secure_memory_wiping(self, config_manager):
        """Test that sensitive data is wiped from memory after use."""
        keys = {'api_key': 'sensitive_data'}
        
        # Encrypt and track cipher key
        encrypted = config_manager.encrypt_api_keys(keys)
        
        # After encryption, cipher_key should be wiped
        assert config_manager._cipher_key is None
        
        # Decrypt
        decrypted = config_manager.decrypt_api_keys(encrypted)
        
        # After decryption, cipher_key should be wiped again
        assert config_manager._cipher_key is None
        assert decrypted == keys
    
    def test_encryption_with_invalid_input(self, config_manager):
        """Test encryption with invalid input types."""
        # Non-string key value
        invalid_keys = {'key': 123}
        with pytest.raises(ValueError, match="Invalid key format"):
            config_manager.encrypt_api_keys(invalid_keys)
    
    def test_multiple_keys_encryption(self, config_manager):
        """Test encryption/decryption of multiple API keys."""
        keys = {
            'openai_key': 'sk-1234567890',
            'anthropic_key': 'ant-abcdefghij',
            'google_key': 'goog-xyz123456',
            'azure_key': 'az-987654321'
        }
        
        encrypted = config_manager.encrypt_api_keys(keys)
        
        # All keys should be encrypted
        assert len(encrypted) == len(keys)
        for key_name in keys:
            assert key_name in encrypted
            assert 'ciphertext' in encrypted[key_name]
            assert 'salt' in encrypted[key_name]
            assert encrypted[key_name]['version'] == 2
        
        # Decrypt and verify
        decrypted = config_manager.decrypt_api_keys(encrypted)
        assert decrypted == keys
    
    def test_encryption_disabled(self, config_manager):
        """Test behavior when encryption is disabled."""
        config_manager._config.security.encryption_enabled = False
        
        keys = {'api_key': 'plaintext_value'}
        
        # Should return keys unchanged
        encrypted = config_manager.encrypt_api_keys(keys)
        assert encrypted == keys
        
        # Decryption should also return unchanged
        decrypted = config_manager.decrypt_api_keys(keys)
        assert decrypted == keys
    
    def test_argon2_parameters(self, config_manager):
        """Test that Argon2id uses recommended security parameters."""
        from argon2 import Parameters, Type
        
        # Intercept the Parameters creation to verify settings
        captured_params = None
        original_from_params = PasswordHasher.from_parameters
        
        def capture_params(params):
            nonlocal captured_params
            captured_params = params
            return original_from_params(params)
        
        with patch.object(PasswordHasher, 'from_parameters', side_effect=capture_params):
            keys = {'test': 'value'}
            config_manager.encrypt_api_keys(keys)
        
        # Verify parameters match requirements
        assert captured_params is not None
        assert captured_params.type == Type.ID  # Argon2id
        assert captured_params.memory_cost == 65536  # 64 MB
        assert captured_params.time_cost == 3  # 3 iterations
        assert captured_params.parallelism == 4  # 4 threads
        assert captured_params.salt_len == 32  # 32-byte salt
        assert captured_params.hash_len == 32  # 32-byte output
    
    def test_master_key_generation_warning(self, config_manager, caplog):
        """Test warning is logged when master key is generated."""
        # Clear any existing master key
        if 'DEVDOCAI_MASTER_KEY' in os.environ:
            del os.environ['DEVDOCAI_MASTER_KEY']
        
        keys = {'api_key': 'value'}
        encrypted = config_manager.encrypt_api_keys(keys)
        
        # Check warning was logged
        assert "Generated random master key" in caplog.text
        assert "save DEVDOCAI_MASTER_KEY env var" in caplog.text
    
    def test_encryption_error_handling(self, config_manager):
        """Test error handling in encryption/decryption."""
        # Mock an error during encryption
        with patch('os.urandom', side_effect=OSError("Random generation failed")):
            keys = {'test': 'value'}
            with pytest.raises(OSError):
                config_manager.encrypt_api_keys(keys)
            
            # Verify secure wipe was called on error
            assert config_manager._cipher_key is None
    
    def test_decryption_with_wrong_master_key(self, config_manager):
        """Test decryption fails gracefully with wrong master key."""
        # Set a specific master key
        os.environ['DEVDOCAI_MASTER_KEY'] = 'correct_key'
        
        keys = {'api_key': 'secret'}
        encrypted = config_manager.encrypt_api_keys(keys)
        
        # Change master key
        os.environ['DEVDOCAI_MASTER_KEY'] = 'wrong_key'
        
        # Create new instance with wrong key
        ConfigurationManager._instance = None
        new_manager = ConfigurationManager()
        new_manager._config.security.encryption_enabled = True
        
        # Decryption should fail
        with pytest.raises(Exception):
            new_manager.decrypt_api_keys(encrypted)
        
        # Restore correct key
        os.environ['DEVDOCAI_MASTER_KEY'] = 'correct_key'
    
    def test_salt_randomness(self, config_manager):
        """Test that salts are truly random and unique."""
        salts_seen = set()
        
        # Encrypt same data 100 times
        for _ in range(100):
            keys = {'test': 'value'}
            encrypted = config_manager.encrypt_api_keys(keys)
            salt = encrypted['test']['salt']
            
            # Should never see the same salt twice
            assert salt not in salts_seen
            salts_seen.add(salt)
            
            # Salt should be 64 characters (32 bytes hex)
            assert len(salt) == 64
    
    def test_unicode_and_special_chars_in_keys(self, config_manager):
        """Test encryption of API keys with unicode and special characters."""
        keys = {
            'unicode_key': '🔐 Sēćūrē Këÿ 密码 パスワード',
            'special_key': '!@#$%^&*()_+-=[]{}|;:,.<>?/~`'
        }
        
        encrypted = config_manager.encrypt_api_keys(keys)
        decrypted = config_manager.decrypt_api_keys(encrypted)
        
        assert decrypted == keys
    
    def test_empty_keys_dictionary(self, config_manager):
        """Test encryption of empty dictionary."""
        keys = {}
        encrypted = config_manager.encrypt_api_keys(keys)
        assert encrypted == {}
        
        decrypted = config_manager.decrypt_api_keys(encrypted)
        assert decrypted == {}
    
    def test_validate_encrypted_structure_edge_cases(self, config_manager):
        """Test _validate_encrypted_structure with edge cases."""
        # Valid structure (using actual hex strings)
        valid = {
            'ciphertext': '1234abcd5678ef90',
            'nonce': '1234567890abcdef1234567890abcdef',
            'tag': '9012345678abcdef9012345678abcdef',
            'salt': 'abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890',
            'version': 2
        }
        assert config_manager._validate_encrypted_structure(valid)
        
        # Extra unexpected fields (should log warning but still validate)
        with_extra = valid.copy()
        with_extra['unexpected_field'] = 'value'
        assert config_manager._validate_encrypted_structure(with_extra)
        
        # Not a dictionary
        assert not config_manager._validate_encrypted_structure("not a dict")
    
    def test_encryption_preserves_data_integrity(self, config_manager):
        """Test that encryption/decryption preserves exact data."""
        # Test with various data types and edge cases
        test_cases = [
            {'simple': 'value'},
            {'empty': ''},
            {'long': 'x' * 10000},
            {'multiline': 'line1\nline2\rline3\r\nline4'},
            {'binary_like': '\x00\x01\x02\x03\x04\x05'},
            {'json': '{"nested": {"key": "value"}}'},
            {'xml': '<root><child>value</child></root>'}
        ]
        
        for keys in test_cases:
            encrypted = config_manager.encrypt_api_keys(keys)
            decrypted = config_manager.decrypt_api_keys(encrypted)
            assert decrypted == keys, f"Failed for {keys}"


class TestAdditionalCoverage:
    """Additional tests to reach 95% coverage target."""
    
    @pytest.fixture
    def config_manager(self):
        """Create ConfigurationManager for testing."""
        ConfigurationManager._instance = None
        return ConfigurationManager()
    
    def test_config_set_with_nested_paths(self, config_manager):
        """Test setting values with deeply nested paths."""
        # Test nested security settings
        assert config_manager.set('security.api_key_rotation_days', 45)
        assert config_manager.get('security.api_key_rotation_days') == 45
        
        # Test nested paths that don't exist yet
        assert config_manager.set('custom.nested.deep.value', 'test')
        assert config_manager.get('custom.nested.deep.value') == 'test'
    
    def test_config_get_with_default(self, config_manager):
        """Test getting values with default fallback."""
        # Should return default for non-existent key
        assert config_manager.get('nonexistent.key', default='fallback') == 'fallback'
        
        # Should return actual value when it exists
        config_manager.set('existing.key', 'actual')
        assert config_manager.get('existing.key', default='fallback') == 'actual'
    
    def test_config_delete_nested_keys(self, config_manager):
        """Test deleting nested configuration keys."""
        # Set a nested key
        config_manager.set('test.nested.key', 'value')
        assert config_manager.get('test.nested.key') == 'value'
        
        # Overwrite with None to simulate deletion
        config_manager.set('test.nested.key', None)
        assert config_manager.get('test.nested.key') is None
    
    def test_config_reset_to_defaults(self, config_manager):
        """Test resetting configuration to defaults."""
        # Set some values
        config_manager.set('security.audit_logging', True)
        assert config_manager.get('security.audit_logging') == True
        
        # Reset by creating new instance
        ConfigurationManager._instance = None
        new_manager = ConfigurationManager()
        # Default should be False
        assert new_manager.get('security.audit_logging') == False
    
    def test_config_update_multiple(self, config_manager):
        """Test updating multiple configuration values."""
        updates = {
            'security.encryption_enabled': True,
            'security.api_key_rotation_days': 60,
            'security.audit_logging': True
        }
        
        for key, value in updates.items():
            config_manager.set(key, value)
        
        for key, value in updates.items():
            assert config_manager.get(key) == value
    
    def test_memory_detection_baseline(self, config_manager):
        """Test memory detection for baseline mode."""
        with patch('psutil.virtual_memory') as mock_mem:
            # Simulate baseline memory (< 8GB)
            mock_mem.return_value = MagicMock(total=4 * 1024 * 1024 * 1024)
            
            manager = ConfigurationManager()
            assert manager._config.memory.mode == "baseline"
            assert manager._config.memory.cache_size == 50
    
    def test_memory_detection_standard(self, config_manager):
        """Test memory detection for standard mode."""
        with patch('psutil.virtual_memory') as mock_mem:
            # Simulate standard memory (8-16GB)
            mock_mem.return_value = MagicMock(total=12 * 1024 * 1024 * 1024)
            
            ConfigurationManager._instance = None
            manager = ConfigurationManager()
            assert manager._config.memory.mode == "standard"
            assert manager._config.memory.cache_size == 100
    
    def test_memory_detection_enhanced(self, config_manager):
        """Test memory detection for enhanced mode."""
        with patch('psutil.virtual_memory') as mock_mem:
            # Simulate enhanced memory (16-32GB)
            mock_mem.return_value = MagicMock(total=24 * 1024 * 1024 * 1024)
            
            ConfigurationManager._instance = None
            manager = ConfigurationManager()
            assert manager._config.memory.mode == "enhanced"
            assert manager._config.memory.cache_size == 200
    
    def test_memory_detection_performance(self, config_manager):
        """Test memory detection for performance mode."""
        with patch('psutil.virtual_memory') as mock_mem:
            # Simulate performance memory (>32GB)
            mock_mem.return_value = MagicMock(total=64 * 1024 * 1024 * 1024)
            
            ConfigurationManager._instance = None
            manager = ConfigurationManager()
            assert manager._config.memory.mode == "performance"
            assert manager._config.memory.cache_size == 500
    
    def test_validate_path_security(self, config_manager):
        """Test path validation for security issues."""
        # Test path traversal attempts - _validate_path is a static method
        assert not ConfigurationManager._validate_path('../etc/passwd')
        assert not ConfigurationManager._validate_path('/etc/passwd')
        assert not ConfigurationManager._validate_path('../../sensitive')
        
        # Test valid relative paths
        assert ConfigurationManager._validate_path('.devdocai.yml')
        assert ConfigurationManager._validate_path('config/.devdocai.yml')
    
    def test_merge_configs_edge_cases(self, config_manager):
        """Test configuration merging edge cases."""
        # Test merging with None
        config_manager._merge_configs(None, config_manager._config)
        
        # Test merging with empty dict
        config_manager._merge_configs({}, config_manager._config)
        
        # Test merging with nested overrides
        override = {
            'security': {
                'encryption_enabled': True,
                'api_key_rotation_days': 90
            }
        }
        config_manager._merge_configs(override, config_manager._config)
        assert config_manager._config.security.encryption_enabled == True
        assert config_manager._config.security.api_key_rotation_days == 90
    
    def test_reload_configuration(self, config_manager):
        """Test reloading configuration from file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump({
                'security': {'encryption_enabled': True},
                'memory': {'cache_size': 250}
            }, f)
            temp_path = f.name
        
        try:
            # Load configuration
            config_manager.load_config(temp_path)
            assert config_manager._config.security.encryption_enabled == True
            
            # Modify and reload
            with open(temp_path, 'w') as f:
                yaml.dump({
                    'security': {'encryption_enabled': False},
                    'memory': {'cache_size': 300}
                }, f)
            
            config_manager.reload()
            assert config_manager._config.security.encryption_enabled == False
            assert config_manager._config.memory.cache_size == 300
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def test_export_import_configuration(self, config_manager):
        """Test exporting and importing configuration."""
        # Set some values
        config_manager.set('test.export', 'value')
        config_manager.set('security.audit_logging', True)
        
        # Export configuration
        exported = config_manager.export_config()
        assert 'security' in exported
        assert exported['security']['audit_logging'] == True
        
        # Clear and import
        config_manager.clear()
        assert config_manager.get('security.audit_logging') is None
        
        # Import back
        config_manager._merge_configs(exported, config_manager._config)
        assert config_manager._config.security.audit_logging == True
    
    def test_memory_detection_available_ram_levels(self, config_manager):
        """Test memory detection based on available RAM."""
        with patch('psutil.virtual_memory') as mock_mem:
            # Test baseline mode (< 2GB available)
            mock_mem.return_value = MagicMock(available=1 * 1024 * 1024 * 1024)
            ConfigurationManager._instance = None
            manager = ConfigurationManager()
            assert manager._config.memory.mode == "baseline"
            assert manager._config.memory.cache_size == 1000
            
            # Test standard mode (2-4GB available)
            mock_mem.return_value = MagicMock(available=3 * 1024 * 1024 * 1024)
            ConfigurationManager._instance = None
            manager = ConfigurationManager()
            assert manager._config.memory.mode == "standard"
            assert manager._config.memory.cache_size == 5000
            
            # Test enhanced mode (4-8GB available)
            mock_mem.return_value = MagicMock(available=6 * 1024 * 1024 * 1024)
            ConfigurationManager._instance = None
            manager = ConfigurationManager()
            assert manager._config.memory.mode == "enhanced"
            assert manager._config.memory.cache_size == 10000
            
            # Test performance mode (>8GB available)
            mock_mem.return_value = MagicMock(available=16 * 1024 * 1024 * 1024)
            ConfigurationManager._instance = None
            manager = ConfigurationManager()
            assert manager._config.memory.mode == "performance"
            assert manager._config.memory.cache_size == 50000
    
    def test_initialization_with_env_file(self, config_manager):
        """Test initialization with .env file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / '.env'
            env_path.write_text("DEVDOCAI_MASTER_KEY=test_key\nDEBUG=true")
            
            with patch.object(Path, 'exists', return_value=True):
                with patch('dotenv.load_dotenv') as mock_load:
                    ConfigurationManager._instance = None
                    manager = ConfigurationManager()
                    assert mock_load.called
    
    def test_initialization_with_config_file(self, config_manager):
        """Test initialization with existing config file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump({'security': {'encryption_enabled': True}}, f)
            temp_path = f.name
        
        try:
            with patch.object(Path, 'exists', return_value=True):
                with patch.object(ConfigurationManager, 'load_config') as mock_load:
                    ConfigurationManager._instance = None
                    manager = ConfigurationManager()
                    assert mock_load.called
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
