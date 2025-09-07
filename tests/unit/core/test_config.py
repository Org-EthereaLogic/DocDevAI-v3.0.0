"""
Test Suite for M001 Configuration Manager
Following Enhanced 4-Pass TDD Methodology - PASS 1 (80% Coverage Target)

Tests written BEFORE implementation as per TDD principles.
"""

import pytest
import tempfile
import os
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import time
from typing import Dict, Any

# Import will fail initially (TDD) - that's expected
from devdocai.core.config import (
    ConfigurationManager,
    PrivacyConfig,
    SystemConfig,
    SecurityConfig,
    LLMConfig,
    QualityConfig,
    ValidationError,
    ConfigurationError
)
from pydantic import ValidationError as PydanticValidationError


class TestPrivacyConfig:
    """Test privacy-first configuration defaults."""
    
    def test_privacy_defaults_are_private(self):
        """Test that all privacy defaults protect user privacy."""
        config = PrivacyConfig()
        assert config.telemetry is False, "Telemetry must be disabled by default"
        assert config.analytics is False, "Analytics must be disabled by default"
        assert config.local_only is True, "Local-only mode must be enabled by default"
    
    def test_privacy_config_validation(self):
        """Test privacy configuration validation with Pydantic v2."""
        # Valid configuration
        config = PrivacyConfig(telemetry=True, analytics=False, local_only=False)
        assert config.telemetry is True
        assert config.analytics is False
        assert config.local_only is False
        
        # Invalid types should raise validation error
        with pytest.raises(PydanticValidationError):
            PrivacyConfig(telemetry=[])  # Should be bool, not list
        
        with pytest.raises(PydanticValidationError):
            PrivacyConfig(analytics={})  # Should be bool, not dict
    
    def test_privacy_config_immutability(self):
        """Test that privacy config is immutable after creation."""
        config = PrivacyConfig()
        with pytest.raises(PydanticValidationError):
            config.telemetry = True  # Frozen Pydantic models are immutable


class TestSystemConfig:
    """Test system configuration with memory mode detection."""
    
    @patch('devdocai.core.config.psutil.virtual_memory')
    def test_memory_mode_auto_detection_baseline(self, mock_memory):
        """Test baseline mode detection for <2GB RAM."""
        mock_memory.return_value = Mock(total=1.5 * 1024**3)  # 1.5 GB
        config = SystemConfig()
        assert config.memory_mode == "baseline"
        assert 1.4 < config.detected_ram < 1.6  # Allow small float differences
    
    @patch('devdocai.core.config.psutil.virtual_memory')
    def test_memory_mode_auto_detection_standard(self, mock_memory):
        """Test standard mode detection for 2-4GB RAM."""
        mock_memory.return_value = Mock(total=3 * 1024**3)  # 3 GB
        config = SystemConfig()
        assert config.memory_mode == "standard"
        assert 2.9 < config.detected_ram < 3.1
        assert config.max_workers == 2
    
    @patch('devdocai.core.config.psutil.virtual_memory')
    def test_memory_mode_auto_detection_enhanced(self, mock_memory):
        """Test enhanced mode detection for 4-8GB RAM."""
        mock_memory.return_value = Mock(total=6 * 1024**3)  # 6 GB
        config = SystemConfig()
        assert config.memory_mode == "enhanced"
        assert 5.9 < config.detected_ram < 6.1
        assert config.max_workers == 4
    
    @patch('devdocai.core.config.psutil.virtual_memory')
    def test_memory_mode_auto_detection_performance(self, mock_memory):
        """Test performance mode detection for >8GB RAM."""
        mock_memory.return_value = Mock(total=16 * 1024**3)  # 16 GB
        config = SystemConfig()
        assert config.memory_mode == "performance"
        assert 15.9 < config.detected_ram < 16.1
        assert config.max_workers == 8
    
    def test_memory_mode_manual_override(self):
        """Test manual memory mode override."""
        config = SystemConfig(memory_mode="baseline")
        assert config.memory_mode == "baseline"
        # Manual mode shouldn't change based on RAM
        
    def test_invalid_memory_mode(self):
        """Test invalid memory mode raises error."""
        with pytest.raises(PydanticValidationError):
            SystemConfig(memory_mode="ultra")  # Invalid mode
    
    def test_cache_size_parsing(self):
        """Test cache size string parsing."""
        config = SystemConfig(cache_size="500MB")
        assert config.cache_size == "500MB"
        assert config.cache_size_bytes == 500 * 1024 * 1024
        
        config = SystemConfig(cache_size="2GB")
        assert config.cache_size_bytes == 2 * 1024**3


class TestSecurityConfig:
    """Test security configuration for encryption."""
    
    def test_security_defaults(self):
        """Test secure defaults for security configuration."""
        config = SecurityConfig()
        assert config.encryption_enabled is True
        assert config.api_keys_encrypted is True
        assert config.key_derivation == "argon2id"
        assert config.encryption_algorithm == "AES-256-GCM"
    
    def test_encryption_key_generation(self):
        """Test that encryption keys are properly generated."""
        config = SecurityConfig()
        key = config.generate_key("test_password")
        assert len(key) == 32  # 256 bits for AES-256
        
        # Same password should generate same key (deterministic)
        key2 = config.generate_key("test_password")
        assert key == key2
        
        # Different passwords should generate different keys
        key3 = config.generate_key("different_password")
        assert key != key3


class TestLLMConfig:
    """Test LLM configuration with provider settings."""
    
    def test_llm_defaults(self):
        """Test LLM configuration defaults."""
        config = LLMConfig()
        assert config.provider == "openai"
        assert config.api_key is None  # No default API key
        assert config.model == "gpt-4"
        assert config.max_tokens == 4000
        assert config.temperature == 0.7
        assert config.timeout == 30
        assert config.retry_attempts == 3
    
    def test_llm_provider_validation(self):
        """Test LLM provider validation."""
        valid_providers = ["openai", "anthropic", "gemini", "local"]
        for provider in valid_providers:
            config = LLMConfig(provider=provider)
            assert config.provider == provider
        
        with pytest.raises(PydanticValidationError):
            LLMConfig(provider="invalid_provider")
    
    def test_llm_api_key_encryption_marker(self):
        """Test that API keys are marked for encryption."""
        config = LLMConfig(api_key="sk-test123")
        assert config.api_key == "sk-test123"
        assert config.requires_encryption is True


class TestQualityConfig:
    """Test quality configuration settings."""
    
    def test_quality_defaults(self):
        """Test quality configuration defaults."""
        config = QualityConfig()
        assert config.min_score == 85
        assert config.auto_enhance is True
        assert config.max_iterations == 3
        assert config.enable_miair is True
    
    def test_quality_score_validation(self):
        """Test quality score range validation."""
        config = QualityConfig(min_score=90)
        assert config.min_score == 90
        
        with pytest.raises(PydanticValidationError):
            QualityConfig(min_score=101)  # > 100
        
        with pytest.raises(PydanticValidationError):
            QualityConfig(min_score=-1)  # < 0


class TestConfigurationManager:
    """Test the main ConfigurationManager class."""
    
    def test_initialization_with_defaults(self):
        """Test ConfigurationManager initializes with privacy-first defaults."""
        config = ConfigurationManager()
        
        # Privacy-first defaults
        assert config.privacy.telemetry is False
        assert config.privacy.local_only is True
        
        # System should auto-detect memory mode
        assert config.system.memory_mode in ["baseline", "standard", "enhanced", "performance"]
        
        # Security should be enabled by default
        assert config.security.encryption_enabled is True
    
    def test_yaml_loading(self):
        """Test loading configuration from YAML file."""
        # Create temporary YAML config
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml_content = """
system:
  memory_mode: enhanced
  max_workers: 6
  cache_size: 200MB

privacy:
  telemetry: false
  analytics: false
  local_only: true

security:
  encryption_enabled: true
  api_keys_encrypted: true

llm:
  provider: anthropic
  model: claude-3
  max_tokens: 8000
  temperature: 0.5

quality:
  min_score: 90
  auto_enhance: true
  max_iterations: 5
"""
            f.write(yaml_content)
            temp_path = f.name
        
        try:
            config = ConfigurationManager(config_file=Path(temp_path))
            
            # Verify loaded values
            assert config.system.memory_mode == "enhanced"
            assert config.system.max_workers == 6
            assert config.llm.provider == "anthropic"
            assert config.llm.model == "claude-3"
            assert config.quality.min_score == 90
        finally:
            os.unlink(temp_path)
    
    def test_invalid_yaml_handling(self):
        """Test handling of invalid YAML configuration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name
        
        try:
            # Invalid YAML should log warning and use defaults
            config = ConfigurationManager(config_file=Path(temp_path))
            # Should have defaults even with invalid YAML
            assert config.privacy.telemetry is False
            assert config.privacy.local_only is True
        finally:
            os.unlink(temp_path)
    
    def test_missing_config_file(self):
        """Test handling of missing configuration file."""
        # Should not raise error, just use defaults
        config = ConfigurationManager(config_file=Path("/nonexistent/path.yml"))
        assert config.privacy.telemetry is False  # Should have defaults
    
    def test_api_key_encryption_decryption(self):
        """Test AES-256-GCM encryption and decryption of API keys."""
        config = ConfigurationManager()
        
        test_key = "sk-test-secret-api-key-12345"
        
        # Encrypt API key
        encrypted = config.encrypt_api_key(test_key)
        
        # Verify it's actually encrypted (not plaintext)
        assert encrypted != test_key
        assert "sk-test" not in encrypted
        
        # Decrypt and verify
        decrypted = config.decrypt_api_key(encrypted)
        assert decrypted == test_key
    
    def test_api_key_encryption_different_keys(self):
        """Test that different API keys produce different ciphertexts."""
        config = ConfigurationManager()
        
        key1 = "sk-key1"
        key2 = "sk-key2"
        
        encrypted1 = config.encrypt_api_key(key1)
        encrypted2 = config.encrypt_api_key(key2)
        
        assert encrypted1 != encrypted2
    
    def test_configuration_get_method(self):
        """Test configuration retrieval using get method."""
        config = ConfigurationManager()
        
        # Test dot notation access
        assert config.get("privacy.telemetry") is False
        assert config.get("security.encryption_enabled") is True
        
        # Test nested access
        assert config.get("system.memory_mode") in ["baseline", "standard", "enhanced", "performance"]
        
        # Test default for missing keys
        assert config.get("nonexistent.key", default="default_value") == "default_value"
    
    def test_configuration_set_method(self):
        """Test configuration setting using set method."""
        config = ConfigurationManager()
        
        # Set a value
        config.set("privacy.telemetry", True)
        assert config.get("privacy.telemetry") is True
        
        # Set nested value
        config.set("llm.temperature", 0.9)
        assert config.get("llm.temperature") == 0.9
        
        # Invalid path should raise error
        with pytest.raises(ConfigurationError):
            config.set("invalid.path.too.deep.nested", "value")
    
    def test_configuration_validation(self):
        """Test configuration validation against schema."""
        config = ConfigurationManager()
        
        # Valid configuration should pass
        valid_data = {
            "privacy": {"telemetry": False},
            "system": {"memory_mode": "enhanced"}
        }
        assert config.validate(valid_data) is True
        
        # Invalid configuration should fail
        invalid_data = {
            "privacy": {"telemetry": "not_a_bool"},
            "system": {"memory_mode": "invalid_mode"}
        }
        assert config.validate(invalid_data) is False
    
    def test_configuration_save(self):
        """Test saving configuration to YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".devdocai.yml"
            
            config = ConfigurationManager(config_file=config_path)
            config.set("privacy.telemetry", True)
            config.set("llm.provider", "anthropic")
            
            # Save configuration
            config.save()
            
            # Load and verify
            with open(config_path) as f:
                saved_data = yaml.safe_load(f)
            
            assert saved_data["privacy"]["telemetry"] is True
            assert saved_data["llm"]["provider"] == "anthropic"
    
    def test_environment_variable_override(self):
        """Test environment variable override of configuration."""
        os.environ["DEVDOCAI_LLM_PROVIDER"] = "gemini"
        os.environ["DEVDOCAI_PRIVACY_TELEMETRY"] = "true"
        
        try:
            config = ConfigurationManager()
            assert config.llm.provider == "gemini"
            assert config.privacy.telemetry is True
        finally:
            del os.environ["DEVDOCAI_LLM_PROVIDER"]
            del os.environ["DEVDOCAI_PRIVACY_TELEMETRY"]
    
    def test_configuration_performance_retrieval(self):
        """Test configuration retrieval performance (<100ms)."""
        config = ConfigurationManager()
        
        # Warm up
        config.get("system.memory_mode")
        
        # Measure retrieval time
        start = time.perf_counter()
        for _ in range(1000):
            config.get("system.memory_mode")
        elapsed = time.perf_counter() - start
        
        # Should be much faster than 100ms for 1000 retrievals
        assert elapsed < 0.1, f"Retrieval too slow: {elapsed:.3f}s for 1000 ops"
    
    def test_configuration_loading_performance(self):
        """Test configuration loading performance (<100ms)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml_content = """
system:
  memory_mode: enhanced
privacy:
  telemetry: false
security:
  encryption_enabled: true
llm:
  provider: openai
quality:
  min_score: 85
"""
            f.write(yaml_content)
            temp_path = f.name
        
        try:
            start = time.perf_counter()
            config = ConfigurationManager(config_file=Path(temp_path))
            elapsed = time.perf_counter() - start
            
            assert elapsed < 0.1, f"Loading too slow: {elapsed:.3f}s"
        finally:
            os.unlink(temp_path)
    
    def test_thread_safety(self):
        """Test that ConfigurationManager is thread-safe."""
        import threading
        
        config = ConfigurationManager()
        errors = []
        
        def worker():
            try:
                for _ in range(100):
                    config.get("system.memory_mode")
                    config.set("quality.min_score", 90)
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0, f"Thread safety errors: {errors}"


class TestConfigurationIntegration:
    """Integration tests for ConfigurationManager."""
    
    def test_full_configuration_lifecycle(self):
        """Test complete configuration lifecycle: load, modify, save, reload."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".devdocai.yml"
            
            # Create initial configuration
            config1 = ConfigurationManager(config_file=config_path)
            config1.set("llm.provider", "anthropic")
            config1.set("quality.min_score", 95)
            config1.save()
            
            # Load in new instance
            config2 = ConfigurationManager(config_file=config_path)
            assert config2.get("llm.provider") == "anthropic"
            assert config2.get("quality.min_score") == 95
            
            # Modify and save
            config2.set("llm.model", "claude-3-opus")
            config2.save()
            
            # Verify persistence
            config3 = ConfigurationManager(config_file=config_path)
            assert config3.get("llm.model") == "claude-3-opus"
    
    def test_encrypted_api_key_persistence(self):
        """Test that encrypted API keys persist correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".devdocai.yml"
            
            config = ConfigurationManager(config_file=config_path)
            
            # Set and encrypt API key
            api_key = "sk-secret-key-12345"
            config.set_api_key("openai", api_key)
            config.save()
            
            # Load in new instance
            config2 = ConfigurationManager(config_file=config_path)
            retrieved_key = config2.get_api_key("openai")
            
            assert retrieved_key == api_key
            
            # Verify raw file doesn't contain plaintext
            with open(config_path) as f:
                content = f.read()
                assert "sk-secret" not in content
                assert "${ENCRYPTED}" in content or "encrypted:" in content


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_corrupt_encryption_handling(self):
        """Test handling of corrupted encrypted data."""
        config = ConfigurationManager()
        
        with pytest.raises(ConfigurationError):
            config.decrypt_api_key("invalid_encrypted_data")
    
    def test_invalid_configuration_schema(self):
        """Test handling of invalid configuration schema."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml_content = """
system:
  memory_mode: invalid_mode
  max_workers: "not_a_number"
"""
            f.write(yaml_content)
            temp_path = f.name
        
        try:
            # Invalid schema should log error and use defaults
            config = ConfigurationManager(config_file=Path(temp_path))
            # Should have defaults even with invalid configuration
            assert config.privacy.telemetry is False
            assert config.system.memory_mode in ["baseline", "standard", "enhanced", "performance"]
        finally:
            os.unlink(temp_path)
    
    def test_permission_error_handling(self):
        """Test handling of file permission errors."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write("test: config")
            temp_path = f.name
        
        try:
            # Make file unreadable
            os.chmod(temp_path, 0o000)
            
            # Should fall back to defaults without crashing
            config = ConfigurationManager(config_file=Path(temp_path))
            assert config.privacy.telemetry is False
        finally:
            os.chmod(temp_path, 0o644)
            os.unlink(temp_path)


# Performance benchmarks will be in tests/performance/test_config_performance.py
# Security tests will be in tests/security/test_config_security.py