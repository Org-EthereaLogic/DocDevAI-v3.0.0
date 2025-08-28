"""
Comprehensive test suite for M001 Configuration Manager.

Target coverage: 95% minimum
Performance validation: 19M ops/sec retrieval, 4M ops/sec validation
"""

import os
import tempfile
import time
import threading
from pathlib import Path
from unittest import mock
import pytest
import yaml

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
        
        try:
            ConfigurationManager._instance = None
            manager = ConfigurationManager()
            assert manager.config_path == Path('custom.yml')
        finally:
            del os.environ['DEVDOCAI_CONFIG']
    
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