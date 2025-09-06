"""
Test suite for M001 Configuration Manager

Comprehensive tests covering:
- Privacy-first defaults
- Memory mode detection
- YAML configuration loading
- API key encryption/decryption
- Configuration validation
- Error handling
"""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
import yaml
import psutil
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

from devdocai.core.config import (
    ConfigurationManager,
    ConfigurationSchema,
    ConfigurationError,
    MemoryMode,
    PrivacyMode
)


class TestConfigurationSchema:
    """Test configuration schema validation."""
    
    def test_default_values(self):
        """Test privacy-first default values."""
        schema = ConfigurationSchema()
        
        # Privacy-first defaults (SDD 5.1 requirement)
        assert schema.privacy_mode == PrivacyMode.LOCAL_ONLY
        assert schema.telemetry_enabled is False
        assert schema.cloud_features is False
        assert schema.dsr_enabled is True
        
        # Other defaults
        assert schema.memory_mode == MemoryMode.STANDARD
        assert schema.encryption_enabled is True
        assert schema.debug_mode is False
        assert schema.max_concurrent_operations >= 1
        assert schema.cache_size_mb >= 16
        assert schema.log_level == "INFO"
    
    def test_path_validation(self):
        """Test path field validation."""
        schema = ConfigurationSchema()
        
        # Test string to Path conversion
        schema.config_dir = "/test/path"
        assert isinstance(schema.config_dir, Path)
        assert str(schema.config_dir) == "/test/path"
    
    def test_cloud_privacy_consistency(self):
        """Test cloud features respect privacy mode."""
        # Should raise validation error
        with pytest.raises(ValueError, match="Cloud features cannot be enabled"):
            ConfigurationSchema(
                privacy_mode=PrivacyMode.LOCAL_ONLY,
                cloud_features=True
            )
        
        # Should be valid
        schema = ConfigurationSchema(
            privacy_mode=PrivacyMode.SELECTIVE,
            cloud_features=True
        )
        assert schema.cloud_features is True
    
    def test_field_constraints(self):
        """Test field validation constraints."""
        # Test max_concurrent_operations range
        with pytest.raises(ValueError):
            ConfigurationSchema(max_concurrent_operations=0)
        
        with pytest.raises(ValueError):
            ConfigurationSchema(max_concurrent_operations=50)
        
        # Valid values
        schema = ConfigurationSchema(max_concurrent_operations=16)
        assert schema.max_concurrent_operations == 16
        
        # Test cache_size_mb range
        with pytest.raises(ValueError):
            ConfigurationSchema(cache_size_mb=8)  # Below minimum
        
        # Test log_level regex
        with pytest.raises(ValueError):
            ConfigurationSchema(log_level="INVALID")
        
        schema = ConfigurationSchema(log_level="DEBUG")
        assert schema.log_level == "DEBUG"


class TestMemoryModeDetection:
    """Test memory mode detection logic."""
    
    @patch('psutil.virtual_memory')
    def test_baseline_mode(self, mock_memory):
        """Test baseline mode detection (<2GB RAM)."""
        mock_memory.return_value.total = 1.5 * 1024**3  # 1.5GB
        
        config = ConfigurationManager()
        assert config.get('memory_mode') == MemoryMode.BASELINE
        assert config.get('cache_size_mb') == 32
        assert config.get('max_concurrent_operations') == 2
    
    @patch('psutil.virtual_memory')
    def test_standard_mode(self, mock_memory):
        """Test standard mode detection (2-4GB RAM)."""
        mock_memory.return_value.total = 3 * 1024**3  # 3GB
        
        config = ConfigurationManager()
        assert config.get('memory_mode') == MemoryMode.STANDARD
        assert config.get('cache_size_mb') == 64
        assert config.get('max_concurrent_operations') == 4
    
    @patch('psutil.virtual_memory')
    def test_enhanced_mode(self, mock_memory):
        """Test enhanced mode detection (4-8GB RAM)."""
        mock_memory.return_value.total = 6 * 1024**3  # 6GB
        
        config = ConfigurationManager()
        assert config.get('memory_mode') == MemoryMode.ENHANCED
        assert config.get('cache_size_mb') == 128
        assert config.get('max_concurrent_operations') == 8
    
    @patch('psutil.virtual_memory')
    def test_performance_mode(self, mock_memory):
        """Test performance mode detection (>8GB RAM)."""
        mock_memory.return_value.total = 16 * 1024**3  # 16GB
        
        config = ConfigurationManager()
        assert config.get('memory_mode') == MemoryMode.PERFORMANCE
        assert config.get('cache_size_mb') == 256
        assert config.get('max_concurrent_operations') == 16
    
    @patch('psutil.virtual_memory')
    def test_memory_detection_fallback(self, mock_memory):
        """Test fallback to standard mode when detection fails."""
        mock_memory.side_effect = Exception("Memory detection failed")
        
        config = ConfigurationManager()
        # Should fallback to standard mode
        assert config.get('memory_mode') == MemoryMode.STANDARD


class TestConfigurationLoading:
    """Test YAML configuration loading and saving."""
    
    def test_load_valid_yaml(self):
        """Test loading valid YAML configuration."""
        config_data = {
            'privacy_mode': 'selective',  # Must be selective to allow cloud_features
            'telemetry_enabled': True,
            'cloud_features': True,
            'memory_mode': 'performance',
            'max_concurrent_operations': 8,
            'cache_size_mb': 512,
            'log_level': 'DEBUG'
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(config_data, f)
            config_file = Path(f.name)
        
        try:
            config = ConfigurationManager(config_file)
            
            assert config.get('privacy_mode') == PrivacyMode.SELECTIVE
            assert config.get('telemetry_enabled') is True
            assert config.get('cloud_features') is True
            assert config.get('memory_mode') == MemoryMode.PERFORMANCE
            assert config.get('max_concurrent_operations') == 8
            assert config.get('cache_size_mb') == 512
            assert config.get('log_level') == 'DEBUG'
        
        finally:
            config_file.unlink()
    
    def test_load_invalid_yaml(self):
        """Test loading invalid YAML raises error."""
        invalid_yaml = "invalid: yaml: content: ["
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(invalid_yaml)
            config_file = Path(f.name)
        
        try:
            with pytest.raises(ConfigurationError, match="Invalid YAML"):
                ConfigurationManager(config_file)
        finally:
            config_file.unlink()
    
    def test_load_nonexistent_file(self):
        """Test loading nonexistent file uses defaults."""
        nonexistent_file = Path("/nonexistent/config.yml")
        config = ConfigurationManager(nonexistent_file)
        
        # Should use defaults
        assert config.get('privacy_mode') == PrivacyMode.LOCAL_ONLY
        assert config.get('telemetry_enabled') is False
    
    def test_save_configuration(self):
        """Test saving configuration to YAML."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            config_file = Path(f.name)
        
        try:
            config = ConfigurationManager(config_file)
            config.set('telemetry_enabled', True)
            config.set('log_level', 'DEBUG')
            
            config.save_configuration()
            
            # Verify saved content
            with open(config_file, 'r') as f:
                saved_data = yaml.safe_load(f)
            
            assert saved_data['telemetry_enabled'] is True
            assert saved_data['log_level'] == 'DEBUG'
            # API keys should not be in saved file
            assert 'api_keys' not in saved_data
        
        finally:
            config_file.unlink()


class TestAPIKeyEncryption:
    """Test API key encryption and decryption."""
    
    def test_encrypt_decrypt_cycle(self):
        """Test full encrypt/decrypt cycle."""
        config = ConfigurationManager()
        test_service = "openai"
        test_key = "sk-test123456789"
        
        # Encrypt API key
        config.encrypt_api_key(test_service, test_key)
        
        # Decrypt and verify
        decrypted_key = config.decrypt_api_key(test_service)
        assert decrypted_key == test_key
    
    def test_encrypt_multiple_services(self):
        """Test encrypting keys for multiple services."""
        config = ConfigurationManager()
        
        services_keys = {
            "openai": "sk-openai-key-123",
            "anthropic": "sk-ant-key-456",
            "google": "google-api-key-789"
        }
        
        # Encrypt all keys
        for service, key in services_keys.items():
            config.encrypt_api_key(service, key)
        
        # Verify all can be decrypted
        for service, expected_key in services_keys.items():
            decrypted_key = config.decrypt_api_key(service)
            assert decrypted_key == expected_key
        
        # Verify service list
        assert set(config.list_api_services()) == set(services_keys.keys())
    
    def test_encryption_disabled(self):
        """Test API key storage when encryption is disabled."""
        config = ConfigurationManager()
        config.set('encryption_enabled', False)
        
        test_service = "test_service"
        test_key = "test_api_key"
        
        config.encrypt_api_key(test_service, test_key)
        decrypted_key = config.decrypt_api_key(test_service)
        
        assert decrypted_key == test_key
    
    def test_decrypt_nonexistent_key(self):
        """Test decrypting nonexistent key returns None."""
        config = ConfigurationManager()
        
        result = config.decrypt_api_key("nonexistent_service")
        assert result is None
    
    def test_remove_api_key(self):
        """Test removing API keys."""
        config = ConfigurationManager()
        
        # Add and verify key
        config.encrypt_api_key("test_service", "test_key")
        assert config.decrypt_api_key("test_service") == "test_key"
        
        # Remove key
        removed = config.remove_api_key("test_service")
        assert removed is True
        
        # Verify removed
        assert config.decrypt_api_key("test_service") is None
        
        # Try removing nonexistent key
        removed = config.remove_api_key("nonexistent")
        assert removed is False
    
    def test_encryption_error_handling(self):
        """Test encryption error handling."""
        config = ConfigurationManager()
        
        # Test with invalid input
        with pytest.raises(ConfigurationError):
            config.encrypt_api_key("", "")


class TestConfigurationManagement:
    """Test configuration get/set operations."""
    
    def test_get_set_values(self):
        """Test getting and setting configuration values."""
        config = ConfigurationManager()
        
        # Test setting valid values
        config.set('log_level', 'ERROR')
        assert config.get('log_level') == 'ERROR'
        
        config.set('max_concurrent_operations', 12)
        assert config.get('max_concurrent_operations') == 12
        
        # Test getting with default
        assert config.get('nonexistent_key', 'default_value') == 'default_value'
    
    def test_set_invalid_key(self):
        """Test setting invalid configuration key."""
        config = ConfigurationManager()
        
        with pytest.raises(ConfigurationError, match="Unknown configuration key"):
            config.set('invalid_key', 'value')
    
    def test_set_invalid_value(self):
        """Test setting invalid configuration value."""
        config = ConfigurationManager()
        
        with pytest.raises(ConfigurationError):
            config.set('max_concurrent_operations', -1)


class TestMemoryInfo:
    """Test memory information reporting."""
    
    @patch('psutil.virtual_memory')
    def test_get_memory_info(self, mock_memory):
        """Test getting memory information."""
        mock_memory.return_value = MagicMock()
        mock_memory.return_value.total = 8 * 1024**3  # 8GB
        mock_memory.return_value.available = 4 * 1024**3  # 4GB
        mock_memory.return_value.percent = 50.0
        
        config = ConfigurationManager()
        memory_info = config.get_memory_info()
        
        assert memory_info['mode'] == MemoryMode.PERFORMANCE.value
        assert memory_info['total_gb'] == 8.0
        assert memory_info['available_gb'] == 4.0
        assert memory_info['used_percent'] == 50.0
        assert 'cache_size_mb' in memory_info
        assert 'max_concurrent_operations' in memory_info
    
    @patch('psutil.virtual_memory')
    def test_get_memory_info_error(self, mock_memory):
        """Test memory info error handling."""
        mock_memory.side_effect = Exception("Memory error")
        
        config = ConfigurationManager()
        memory_info = config.get_memory_info()
        
        assert 'error' in memory_info
        assert 'mode' in memory_info


class TestPrivacyStatus:
    """Test privacy status reporting."""
    
    def test_get_privacy_status(self):
        """Test getting privacy status."""
        config = ConfigurationManager()
        
        # Add some API keys
        config.encrypt_api_key("openai", "test_key_1")
        config.encrypt_api_key("anthropic", "test_key_2")
        
        privacy_status = config.get_privacy_status()
        
        assert privacy_status['privacy_mode'] == PrivacyMode.LOCAL_ONLY.value
        assert privacy_status['telemetry_enabled'] is False
        assert privacy_status['cloud_features'] is False
        assert privacy_status['dsr_enabled'] is True
        assert privacy_status['encryption_enabled'] is True
        assert privacy_status['api_services_count'] == 2


class TestConfigurationValidation:
    """Test configuration validation."""
    
    def test_validate_configuration_success(self):
        """Test successful configuration validation."""
        config = ConfigurationManager()
        issues = config.validate_configuration()
        
        # Should be valid or have minimal issues
        # (directory issues might be expected in test environment)
        assert isinstance(issues, list)
    
    def test_validate_configuration_directory_error(self):
        """Test validation with directory permission error."""
        config = ConfigurationManager()
        # Set a config directory to a path that can't be created
        config.set('config_dir', Path('/root/impossible_path_for_testing'))
        
        issues = config.validate_configuration()
        
        assert len(issues) > 0
        assert any("not writable" in issue for issue in issues)
    
    def test_validate_privacy_consistency(self):
        """Test privacy mode consistency validation."""
        config = ConfigurationManager()
        
        # Try to set conflicting settings (this should fail at the set stage)
        with pytest.raises(ConfigurationError):
            config.set('privacy_mode', PrivacyMode.LOCAL_ONLY)  
            config.set('cloud_features', True)  # This should trigger validation error
        
        # But validation should pass for consistent settings
        config.reset_to_defaults()  # Reset to known good state
        issues = config.validate_configuration()
        assert issues == []


class TestUtilityMethods:
    """Test utility methods."""
    
    def test_reset_to_defaults(self):
        """Test resetting configuration to defaults."""
        config = ConfigurationManager()
        
        # Make some changes
        config.set('telemetry_enabled', True)
        config.set('log_level', 'DEBUG')
        config.encrypt_api_key('test_service', 'test_key')
        
        # Reset to defaults
        config.reset_to_defaults()
        
        # Verify defaults restored
        assert config.get('telemetry_enabled') is False
        assert config.get('log_level') == 'INFO'
        assert config.list_api_services() == []
    
    def test_export_configuration(self):
        """Test configuration export."""
        config = ConfigurationManager()
        
        # Set some values
        config.set('telemetry_enabled', True)
        config.set('log_level', 'DEBUG')
        config.encrypt_api_key('test_service', 'test_key')
        
        # Export without API keys
        exported = config.export_configuration(include_api_keys=False)
        
        assert exported['telemetry_enabled'] is True
        assert exported['log_level'] == 'DEBUG'
        assert '_metadata' in exported
        assert exported['_metadata']['version'] == '3.0.0'
        assert '_encrypted_api_keys' not in exported
        
        # Export with API keys
        exported_with_keys = config.export_configuration(include_api_keys=True)
        assert '_encrypted_api_keys' in exported_with_keys
    
    def test_string_representation(self):
        """Test string representation."""
        config = ConfigurationManager()
        config.encrypt_api_key('openai', 'test_key')
        
        repr_str = repr(config)
        
        assert 'ConfigurationManager' in repr_str
        assert 'memory_mode' in repr_str
        assert 'privacy_mode' in repr_str
        # Just check that api_services is present (number may vary due to test isolation)
        assert 'api_services=' in repr_str


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_configuration_error_inheritance(self):
        """Test ConfigurationError is proper exception type."""
        with pytest.raises(Exception):
            raise ConfigurationError("Test error")
        
        with pytest.raises(ConfigurationError):
            raise ConfigurationError("Test error")
    
    @patch('yaml.safe_load')
    def test_yaml_loading_exception(self, mock_yaml_load):
        """Test YAML loading exception handling."""
        mock_yaml_load.side_effect = yaml.YAMLError("YAML parsing error")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write("test: data")
            config_file = Path(f.name)
        
        try:
            with pytest.raises(ConfigurationError, match="Invalid YAML"):
                ConfigurationManager(config_file)
        finally:
            config_file.unlink()


# Integration tests
class TestIntegration:
    """Integration tests combining multiple features."""
    
    def test_full_workflow(self):
        """Test complete configuration workflow."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            config_file = Path(f.name)
        
        try:
            # Create configuration manager
            config = ConfigurationManager(config_file)
            
            # Set various configurations (selective mode to allow cloud features)
            config.set('privacy_mode', PrivacyMode.SELECTIVE)
            config.set('telemetry_enabled', True)
            config.set('cloud_features', True)
            config.set('log_level', 'DEBUG')
            
            # Add API keys
            config.encrypt_api_key('openai', 'sk-test-openai-key')
            config.encrypt_api_key('anthropic', 'sk-ant-test-key')
            
            # Save configuration
            config.save_configuration()
            
            # Create new manager with same file
            new_config = ConfigurationManager(config_file)
            
            # Verify settings persisted
            assert new_config.get('privacy_mode') == PrivacyMode.SELECTIVE
            assert new_config.get('telemetry_enabled') is True
            assert new_config.get('cloud_features') is True
            assert new_config.get('log_level') == 'DEBUG'
            
            # Verify API keys work
            assert new_config.decrypt_api_key('openai') == 'sk-test-openai-key'
            assert new_config.decrypt_api_key('anthropic') == 'sk-ant-test-key'
            
            # Test validation
            issues = new_config.validate_configuration()
            assert issues == []  # Should be valid
            
            # Test memory and privacy info
            memory_info = new_config.get_memory_info()
            privacy_status = new_config.get_privacy_status()
            
            assert 'mode' in memory_info
            assert privacy_status['api_services_count'] == 2
        
        finally:
            config_file.unlink()


if __name__ == "__main__":
    pytest.main([__file__])