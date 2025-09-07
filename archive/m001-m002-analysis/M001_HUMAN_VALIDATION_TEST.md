# M001 Configuration Manager - Human Validation Test

**Purpose**: Real-world validation that M001 Configuration Manager works exactly as designed  
**Duration**: ~5-10 minutes  
**Requirements**: Terminal access to the project directory

## Test Overview

This test walks you through the complete M001 Configuration Manager functionality to verify:
1. Privacy-first defaults are correctly set
2. Memory mode detection works properly
3. Configuration persistence (YAML saving/loading)
4. API key encryption and security
5. CLI integration and user experience

---

## Test 1: Verify Privacy-First Defaults (SDD 5.1 Requirement)

**Expected**: All privacy settings should default to maximum privacy

### Commands to Run:

```bash
# Test 1a: Check default configuration
python -m devdocai.cli config show
```

**✅ What You Should See**:
- Privacy Mode: `local_only` 
- Telemetry Enabled: `False`
- Cloud Features: `False`
- DSR Enabled: `True`

**❌ Red Flag If**:
- Any telemetry is enabled by default
- Cloud features are enabled by default
- Privacy mode is not `local_only`

---

## Test 2: Memory Mode Detection (Auto-Detection Feature)

**Expected**: System should automatically detect your RAM and set appropriate mode

### Commands to Run:

```bash
# Test 2a: Check memory detection
python -m devdocai.cli config memory
```

**✅ What You Should See**:
- Memory Mode: Should show `performance` (you have 44GB RAM)
- Total Memory: Should show ~44GB
- Available Memory: Should show available RAM
- Cache Size: Should be `256 MB` (performance mode default)
- Max Concurrent Operations: Should be `16` (performance mode)

**✅ Validation**:
- Verify the total memory matches your system specs
- Mode should be "performance" since you have >8GB RAM

---

## Test 3: Configuration Persistence (YAML File Handling)

**Expected**: Configuration changes should persist between sessions

### Commands to Run:

```bash
# Test 3a: Modify a setting
python -m devdocai.cli config set cache_size_mb 512

# Test 3b: Verify the change
python -m devdocai.cli config show

# Test 3c: Check if YAML file was created
ls -la .devdocai.yml 2>/dev/null && echo "✅ Config file created" || echo "ℹ️  Config file will be created on first save"

# Test 3d: If file exists, check its contents
if [ -f .devdocai.yml ]; then
    echo "=== Configuration File Contents ==="
    cat .devdocai.yml
fi
```

**✅ What You Should See**:
- Cache Size should now show `512 MB` instead of `256 MB`
- If `.devdocai.yml` exists, it should contain YAML configuration
- All other settings should remain unchanged

---

## Test 4: API Key Encryption (Security Feature)

**Expected**: API keys should be encrypted and stored securely

### Commands to Run:

```bash
# Test 4a: Add an encrypted API key
python -m devdocai.cli config api set openai "test-key-12345"

# Test 4b: Verify it was encrypted (should not show plain text)
python -m devdocai.cli config api list

# Test 4c: Test retrieval (should decrypt properly)
python -m devdocai.cli config api get openai
```

**✅ What You Should See**:
- Step 4a: Should confirm the key was encrypted and stored
- Step 4b: Should show `openai` service is configured (but NOT the actual key)
- Step 4c: Should display the decrypted key: `test-key-12345`

**🔐 Security Validation**:
- The actual key should never appear in plain text in files
- Only encrypted values should be stored

---

## Test 5: Configuration Validation (Error Handling)

**Expected**: System should prevent invalid configurations

### Commands to Run:

```bash
# Test 5a: Try to set an invalid value (should fail gracefully)
python -m devdocai.cli config set cache_size_mb -100

# Test 5b: Try to set cache too large (should warn/limit)
python -m devdocai.cli config set cache_size_mb 99999

# Test 5c: Verify current values are still valid
python -m devdocai.cli config show
```

**✅ What You Should See**:
- Step 5a: Should show error message for negative cache size
- Step 5b: Should either reject or warn about excessive cache size
- Step 5c: Should show reasonable, valid configuration values

---

## Test 6: Privacy Consistency (Design Requirement)

**Expected**: System should prevent conflicting privacy settings

### Commands to Run:

```bash
# Test 6a: Try to enable cloud features while in local_only mode (should fail)
python -c "
from devdocai.core.config import ConfigurationManager, ConfigurationSchema
try:
    # This should raise a validation error
    schema = ConfigurationSchema(privacy_mode='local_only', cloud_features=True)
    print('❌ FAILED: Should have prevented cloud_features=True with privacy_mode=local_only')
except Exception as e:
    print('✅ PASSED: Correctly prevented conflicting privacy settings')
    print(f'   Error: {e}')
"

# Test 6b: Verify current privacy settings are consistent
python -m devdocai.cli config show | grep -E "(Privacy Mode|Cloud Features|Telemetry)"
```

**✅ What You Should See**:
- Step 6a: Should print "✅ PASSED: Correctly prevented conflicting privacy settings"
- Step 6b: Should show consistent privacy settings (local_only + cloud_features=False)

---

## Test 7: CLI User Experience

**Expected**: Rich, professional CLI interface

### Commands to Run:

```bash
# Test 7a: Check help system
python -m devdocai.cli --help

# Test 7b: Check config command help
python -m devdocai.cli config --help

# Test 7c: Test error handling with invalid command
python -m devdocai.cli config invalid-command
```

**✅ What You Should See**:
- Step 7a: Professional help with version number (3.0.0)
- Step 7b: Complete list of config subcommands
- Step 7c: Helpful error message for invalid command

---

## Final Validation Checklist

After running all tests, verify:

- [ ] **Privacy-First**: All defaults respect maximum privacy
- [ ] **Memory Detection**: Correctly identifies your system capabilities  
- [ ] **Persistence**: Configuration saves and loads properly
- [ ] **Security**: API keys are encrypted, never stored in plain text
- [ ] **Validation**: Invalid configurations are rejected properly
- [ ] **Consistency**: Privacy settings are mutually consistent
- [ ] **User Experience**: CLI is professional and helpful

---

## Expected Test Results Summary

If everything is working correctly, you should see:

1. ✅ **Privacy Mode**: `local_only` by default
2. ✅ **Memory Mode**: `performance` (for your 44GB system)
3. ✅ **Configuration**: Persists between sessions
4. ✅ **Encryption**: API keys stored securely
5. ✅ **Validation**: Invalid inputs rejected
6. ✅ **CLI**: Rich, professional interface

## If Any Test Fails

If you encounter any unexpected behavior:

1. **Note the exact command and output**
2. **Check if the behavior matches design specs** (might be intentional)
3. **Report any genuine issues** for immediate fix

---

**Ready to start testing?** 

Begin with **Test 1** and work through each test in order. Each test builds on the previous one to give you complete confidence in the M001 implementation.