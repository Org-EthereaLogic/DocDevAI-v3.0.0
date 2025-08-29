# M005 Quality Engine - Refactoring Migration Guide

## Overview

The M005 Quality Engine has been refactored to consolidate multiple implementations into a unified, configurable system. This guide helps you migrate from the old multi-file structure to the new unified implementation.

## Key Changes

### 1. File Consolidation

**Before (7,561 lines):**
```
analyzer.py              (796 lines)
analyzer_optimized.py    (792 lines)
analyzer_original.py     (534 lines)
analyzer_secure.py       (773 lines)
dimensions.py            (823 lines)
dimensions_optimized.py  (771 lines)
dimensions_original.py   (823 lines)
```

**After (6,363 lines - 16% reduction):**
```
analyzer_unified.py      (438 lines) - Single unified analyzer
dimensions_unified.py    (1074 lines) - All dimensions consolidated
base_dimension.py        (255 lines) - Abstract base classes
config.py               (210 lines) - Configuration system
utils.py                (432 lines) - Common utilities
```

### 2. Import Changes

**Old imports:**
```python
from devdocai.quality.analyzer import QualityAnalyzer
from devdocai.quality.analyzer_optimized import OptimizedQualityAnalyzer
from devdocai.quality.analyzer_secure import SecureQualityAnalyzer
```

**New imports:**
```python
from devdocai.quality import QualityAnalyzer  # Unified analyzer
# OR
from devdocai.quality import UnifiedQualityAnalyzer

# With configuration
from devdocai.quality import QualityEngineConfig, OperationMode
```

### 3. Configuration-Based Operation Modes

**Old approach (separate classes):**
```python
# Basic analyzer
analyzer = QualityAnalyzer(config)

# Optimized analyzer
analyzer = OptimizedQualityAnalyzer(config)

# Secure analyzer
analyzer = SecureQualityAnalyzer(security_config)
```

**New approach (single class with modes):**
```python
# Basic mode
config = QualityEngineConfig.from_mode(OperationMode.BASIC)
analyzer = UnifiedQualityAnalyzer(config)

# Optimized mode
config = QualityEngineConfig.from_mode(OperationMode.OPTIMIZED)
analyzer = UnifiedQualityAnalyzer(config)

# Secure mode
config = QualityEngineConfig.from_mode(OperationMode.SECURE)
analyzer = UnifiedQualityAnalyzer(config)

# Balanced mode (default)
analyzer = UnifiedQualityAnalyzer()  # Uses balanced mode
```

### 4. Dimension Analyzers

**Old structure:**
```python
from devdocai.quality.dimensions import CompletenessAnalyzer
from devdocai.quality.dimensions_optimized import OptimizedCompletenessAnalyzer
```

**New structure:**
```python
from devdocai.quality.dimensions_unified import UnifiedCompletenessAnalyzer

# Configure for performance/security
analyzer = UnifiedCompletenessAnalyzer(
    performance_mode=True,
    security_enabled=True
)
```

### 5. API Compatibility

The unified implementation maintains backward compatibility through aliases:

```python
# This still works (QualityAnalyzer is aliased to UnifiedQualityAnalyzer)
from devdocai.quality import QualityAnalyzer
analyzer = QualityAnalyzer()
```

### 6. Configuration System

New centralized configuration with presets:

```python
from devdocai.quality import QualityEngineConfig, PRESETS

# Use presets
config = PRESETS['production']  # Balanced mode
config = PRESETS['development']  # Basic mode
config = PRESETS['performance']  # Optimized mode
config = PRESETS['security']     # Secure mode

# Custom configuration
config = QualityEngineConfig(
    mode=OperationMode.BALANCED,
    performance=PerformanceConfig(
        enable_parallel=True,
        cache_strategy=CacheStrategy.MEMORY,
        max_workers=8
    ),
    security=SecurityConfig(
        enable_input_validation=True,
        enable_pii_detection=True
    )
)
```

### 7. Environment Variables

Configure via environment:

```bash
export QUALITY_ENGINE_MODE=optimized
export QUALITY_MAX_WORKERS=16
export QUALITY_CACHE_DIR=/var/cache/quality
```

```python
# Automatically uses environment settings
config = QualityEngineConfig.from_env()
analyzer = UnifiedQualityAnalyzer(config)
```

## Migration Steps

### Step 1: Update Imports

Replace all old imports with the new unified imports:

```python
# Replace these
from devdocai.quality.analyzer import QualityAnalyzer
from devdocai.quality.analyzer_optimized import OptimizedQualityAnalyzer

# With this
from devdocai.quality import QualityAnalyzer, QualityEngineConfig, OperationMode
```

### Step 2: Update Analyzer Initialization

Replace separate analyzer classes with unified analyzer + configuration:

```python
# Old
if performance_needed:
    analyzer = OptimizedQualityAnalyzer(config)
else:
    analyzer = QualityAnalyzer(config)

# New
mode = OperationMode.OPTIMIZED if performance_needed else OperationMode.BASIC
config = QualityEngineConfig.from_mode(mode)
analyzer = UnifiedQualityAnalyzer(config)
```

### Step 3: Update Dimension Usage

If directly using dimension analyzers, update to unified versions:

```python
# Old
from devdocai.quality.dimensions import CompletenessAnalyzer
analyzer = CompletenessAnalyzer()

# New
from devdocai.quality.dimensions_unified import UnifiedCompletenessAnalyzer
analyzer = UnifiedCompletenessAnalyzer(performance_mode=True)
```

### Step 4: Update Tests

Update test imports and configurations:

```python
# Old test
def test_optimized_analyzer():
    analyzer = OptimizedQualityAnalyzer(config)
    ...

# New test
def test_optimized_mode():
    config = QualityEngineConfig.from_mode(OperationMode.OPTIMIZED)
    analyzer = UnifiedQualityAnalyzer(config)
    ...
```

## Benefits of Refactoring

1. **Code Reduction**: 16% fewer lines of code (1,198 lines removed)
2. **Maintainability**: Single source of truth for each component
3. **Flexibility**: Easy mode switching without code changes
4. **Configuration**: Centralized, environment-aware configuration
5. **Extensibility**: Base classes make adding new dimensions easier
6. **Performance**: Same performance characteristics, better caching
7. **Testing**: Unified test suite, easier to maintain

## Troubleshooting

### Issue: Missing attributes in SecurityConfig

If you see errors about missing attributes like `pii_types_to_detect`, `audit_log_path`, or `regex_timeout`, ensure you're using the latest configuration:

```python
from devdocai.quality.config import SecurityConfig

# These attributes are now included by default
config = QualityEngineConfig()
assert config.security.pii_types_to_detect is not None
assert config.security.audit_log_path is not None
```

### Issue: Import errors

If old imports fail, use the compatibility aliases:

```python
# This still works
from devdocai.quality import QualityAnalyzer

# But prefer the explicit name
from devdocai.quality import UnifiedQualityAnalyzer
```

### Issue: Performance differences

The unified implementation maintains the same performance characteristics. If you notice differences:

1. Ensure you're using the correct operation mode
2. Check cache configuration
3. Verify parallel processing is enabled

```python
# Debug configuration
config = QualityEngineConfig.from_mode(OperationMode.OPTIMIZED)
print(config.to_dict())  # Check actual settings
```

## Support

For questions or issues with the migration, please refer to:
- This migration guide
- The unified implementation source code
- The comprehensive test suite in `test_unified_analyzer.py`