# M001 Configuration Manager - Implementation Roadmap

## Executive Summary

M001 Configuration Manager is the **foundation module** of DevDocAI v3.0.0, providing centralized configuration management with privacy-first defaults, memory mode detection, and secure API key storage. This document provides a complete implementation roadmap following the Enhanced 4-Pass TDD methodology.

## Design Compliance Analysis

Based on comprehensive review of design documents:

### Core Requirements (from SDD Section 5.1)
- **Privacy-First**: Telemetry disabled by default (opt-in only)
- **Memory Mode Detection**: Automatic detection of system RAM for adaptive performance
- **Configuration Schema**: YAML-based with Pydantic v2 validation
- **Security**: AES-256-GCM encryption for API keys using Argon2id key derivation
- **Performance Targets**:
  - Configuration loading: <100ms
  - Validation: 4M operations/second
  - Retrieval: 19M operations/second

### Memory Modes (from Architecture Document)
| Mode | RAM | Features | Performance |
|------|-----|----------|-------------|
| **Baseline** | <2GB | Templates only, no AI | Sequential processing |
| **Standard** | 2-4GB | Full features, cloud AI | 2 concurrent operations |
| **Enhanced** | 4-8GB | Local AI models, caching | 4 concurrent operations |
| **Performance** | >8GB | All features, heavy cache | 8 concurrent operations |

### Configuration Schema Structure
```yaml
# .devdocai.yml
system:
  memory_mode: auto  # auto|baseline|standard|enhanced|performance
  max_workers: 4
  cache_size: 100MB

privacy:
  telemetry: false  # Opt-in only
  analytics: false
  local_only: true

security:
  encryption_enabled: true
  api_keys_encrypted: true

llm:
  provider: openai  # openai|anthropic|gemini|local
  api_key: ${ENCRYPTED}
  model: gpt-4
  max_tokens: 4000
  temperature: 0.7

quality:
  min_score: 85
  auto_enhance: true
  max_iterations: 3
```

## Implementation Plan - Enhanced 4-Pass TDD

### Pass 1: Core Implementation (Day 1-2)
**Goal**: 80% test coverage, basic functionality

#### 1.1 Test-Driven Development Structure
```python
# tests/unit/core/test_config.py
import pytest
from devdocai.core.config import ConfigurationManager

class TestConfigurationManager:
    """TDD tests for M001 - write these FIRST."""

    def test_initialization_with_defaults(self):
        """Test privacy-first defaults on initialization."""
        config = ConfigurationManager()
        assert config.privacy.telemetry is False
        assert config.privacy.local_only is True

    def test_memory_mode_detection(self):
        """Test automatic memory mode detection."""
        config = ConfigurationManager()
        assert config.system.memory_mode in ['baseline', 'standard', 'enhanced', 'performance']

    def test_yaml_loading(self):
        """Test configuration loading from YAML."""
        config = ConfigurationManager(config_file=".devdocai.yml")
        assert config is not None

    def test_schema_validation(self):
        """Test Pydantic v2 schema validation."""
        with pytest.raises(ValidationError):
            config = ConfigurationManager(invalid_data={'bad': 'schema'})

    def test_api_key_encryption(self):
        """Test AES-256-GCM encryption of API keys."""
        config = ConfigurationManager()
        encrypted = config.encrypt_api_key("test-key")
        assert encrypted != "test-key"
        assert config.decrypt_api_key(encrypted) == "test-key"
```

#### 1.2 Core Implementation
```python
# devdocai/core/config.py
from typing import Optional, Dict, Any, Literal
from pathlib import Path
import os
import psutil
import yaml
from pydantic import BaseModel, Field, validator
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from argon2 import PasswordHasher
import logging

logger = logging.getLogger(__name__)

MemoryMode = Literal["baseline", "standard", "enhanced", "performance"]

class PrivacyConfig(BaseModel):
    """Privacy configuration with opt-in defaults."""
    telemetry: bool = False
    analytics: bool = False
    local_only: bool = True

class SystemConfig(BaseModel):
    """System configuration with memory mode detection."""
    memory_mode: MemoryMode = "auto"
    detected_ram: Optional[int] = None
    max_workers: int = 4
    cache_size: str = "100MB"

    @validator('memory_mode', pre=True, always=True)
    def detect_memory_mode(cls, v):
        if v == "auto":
            ram_gb = psutil.virtual_memory().total / (1024**3)
            if ram_gb < 2:
                return "baseline"
            elif ram_gb < 4:
                return "standard"
            elif ram_gb < 8:
                return "enhanced"
            else:
                return "performance"
        return v

class SecurityConfig(BaseModel):
    """Security configuration for encryption."""
    encryption_enabled: bool = True
    api_keys_encrypted: bool = True
    key_derivation: str = "argon2id"

class ConfigurationManager:
    """M001: Centralized configuration management with privacy-first defaults."""

    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file or Path.home() / ".devdocai.yml"
        self.privacy = PrivacyConfig()
        self.system = SystemConfig()
        self.security = SecurityConfig()
        self._load_configuration()
        self._setup_encryption()

    def _load_configuration(self):
        """Load configuration from YAML with validation."""
        if self.config_file.exists():
            with open(self.config_file) as f:
                data = yaml.safe_load(f)
                self._validate_and_apply(data)

    def _validate_and_apply(self, data: Dict[str, Any]):
        """Validate configuration with Pydantic v2."""
        if 'privacy' in data:
            self.privacy = PrivacyConfig(**data['privacy'])
        if 'system' in data:
            self.system = SystemConfig(**data['system'])
        if 'security' in data:
            self.security = SecurityConfig(**data['security'])
```

### Pass 2: Performance Optimization (Day 3)
**Goal**: Meet performance targets

#### 2.1 Performance Enhancements
- Implement caching for configuration retrieval (target: 19M ops/sec)
- Optimize validation pipeline (target: 4M ops/sec)
- Add lazy loading for heavy components
- Implement connection pooling for encrypted storage

#### 2.2 Benchmarks
```python
# tests/performance/test_config_performance.py
import pytest
from devdocai.core.config import ConfigurationManager

@pytest.mark.benchmark
def test_config_retrieval_performance(benchmark):
    """Test configuration retrieval meets 19M ops/sec target."""
    config = ConfigurationManager()
    result = benchmark(lambda: config.get('system.memory_mode'))
    assert benchmark.stats['ops'] > 19_000_000

@pytest.mark.benchmark
def test_validation_performance(benchmark):
    """Test validation meets 4M ops/sec target."""
    config = ConfigurationManager()
    data = {'privacy': {'telemetry': False}}
    result = benchmark(lambda: config.validate(data))
    assert benchmark.stats['ops'] > 4_000_000
```

### Pass 3: Security Hardening (Day 4)
**Goal**: Enterprise-grade security

#### 3.1 Security Implementation
- AES-256-GCM encryption with Argon2id key derivation
- Secure key storage in system keyring
- Input sanitization and validation
- Security audit logging

#### 3.2 Security Tests
```python
# tests/security/test_config_security.py
def test_api_key_encryption():
    """Verify API keys are never stored in plaintext."""
    config = ConfigurationManager()
    config.set_api_key('openai', 'sk-test123')

    # Check raw file doesn't contain plaintext
    with open(config.config_file) as f:
        content = f.read()
        assert 'sk-test123' not in content

def test_argon2id_key_derivation():
    """Verify Argon2id is used for key derivation."""
    config = ConfigurationManager()
    assert config.security.key_derivation == "argon2id"
```

### Pass 4: Refactoring & Integration (Day 5)
**Goal**: 40-50% code reduction, clean architecture

#### 4.1 Refactoring Targets
- Extract common patterns into base classes
- Implement strategy pattern for memory modes
- Create unified configuration interface
- Reduce cyclomatic complexity to <10

#### 4.2 Integration Points
- M002 Local Storage integration
- M003 MIAIR Engine configuration
- M008 LLM Adapter settings
- CLI and VS Code extension support

## Quality Gates

### Required Metrics
- **Test Coverage**: ≥95% (branch and line)
- **Cyclomatic Complexity**: <10
- **Performance**:
  - Retrieval: ≥19M ops/sec
  - Validation: ≥4M ops/sec
  - Load time: <100ms
- **Security**: Zero high/critical vulnerabilities
- **Documentation**: 100% public API documented

### Validation Checklist
- [ ] All tests passing (unit, integration, performance, security)
- [ ] Design document compliance verified
- [ ] Performance benchmarks met
- [ ] Security scan passed
- [ ] Code review completed
- [ ] Documentation updated

## File Structure

```
devdocai/
├── core/
│   ├── __init__.py
│   ├── config.py           # Main ConfigurationManager
│   ├── models.py           # Pydantic models
│   ├── encryption.py       # Security utilities
│   └── memory.py           # Memory mode detection
├── utils/
│   ├── validation.py       # Schema validation
│   └── cache.py           # Performance caching
tests/
├── unit/
│   └── core/
│       ├── test_config.py
│       ├── test_models.py
│       └── test_encryption.py
├── integration/
│   └── test_config_integration.py
├── performance/
│   └── test_config_performance.py
└── security/
    └── test_config_security.py
```

## Development Commands

```bash
# Setup environment
bash setup-dev.sh

# Run TDD tests (Pass 1)
pytest tests/unit/core/test_config.py -v

# Run performance benchmarks (Pass 2)
pytest tests/performance -v --benchmark-only

# Run security tests (Pass 3)
pytest tests/security -v -m security

# Check code quality (Pass 4)
black devdocai/core
ruff check devdocai/core
mypy devdocai/core

# Run all tests with coverage
pytest --cov=devdocai.core --cov-report=html --cov-fail-under=95
```

## Risk Mitigation

### Technical Risks
1. **Performance targets too aggressive**: Implement caching progressively
2. **Encryption overhead**: Use async operations where possible
3. **Memory detection accuracy**: Provide manual override option

### Mitigation Strategies
- Start with basic implementation, optimize iteratively
- Use profiling tools to identify bottlenecks
- Implement comprehensive error handling
- Provide fallback mechanisms for all features

## Success Criteria

M001 is considered complete when:
1. All quality gates are met (95% coverage, performance targets)
2. Design document specifications are fully implemented
3. Integration with other modules is verified
4. Production readiness is validated
5. Documentation is complete and accurate

## Timeline

- **Day 1-2**: Pass 1 - Core Implementation (TDD)
- **Day 3**: Pass 2 - Performance Optimization
- **Day 4**: Pass 3 - Security Hardening
- **Day 5**: Pass 4 - Refactoring & Integration
- **Day 6**: Final validation and documentation

Total: 6 days for M001 implementation following Enhanced 4-Pass TDD methodology.

## Next Steps

1. Begin with TDD tests in `tests/unit/core/test_config.py`
2. Implement minimal ConfigurationManager to pass tests
3. Iterate through each pass methodically
4. Tag git commits at each pass completion
5. Validate against design documents continuously

---

*This roadmap ensures 100% design compliance while following proven development methodology.*
