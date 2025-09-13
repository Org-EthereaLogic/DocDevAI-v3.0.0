# M001 Configuration Manager Test Plan

## Overview

The Configuration Manager (Module M001) provides centralized configuration management with privacy-first defaults and memory mode detection, forming the foundation for other components【F:docs/01-specifications/architecture/DESIGN-devdocsai-sdd.md†L600-L628】. Initial implementation achieved 84.09% branch coverage, leaving several validation and error-handling paths untested【F:docs/02-implementation/progress/M001-ConfigurationManager-Progress.md†L24-L53】. This plan targets comprehensive testing to raise branch coverage to at least 95%.

## Objectives

- Validate configuration loading, saving, and updating behaviors
- Verify all validation rules and error handling within `ConfigValidator`
- Confirm runtime logging and environment-specific behavior in the root module
- Achieve ≥95% branch coverage for Module M001

## Test Scope

- `src/index.ts`
- `src/modules/M001-ConfigurationManager/services/ConfigurationManager.ts`
- `src/modules/M001-ConfigurationManager/utils/ConfigValidator.ts`

## Test Cases

1. **Root Index Exports**
   - Import root index in test environment; ensure exports exist and no logs.
   - Set `NODE_ENV` to development; verify startup logs appear.
2. **Configuration Loading**
   - No config file → defaults loaded.
   - Valid config file → merged correctly.
   - Invalid JSON → error handled, defaults used.
   - Valid JSON but validation fails → warning emitted, defaults used.
   - `NODE_ENV` unset → environment defaults to `development`.
3. **Configuration Saving**
   - Successful save writes file.
   - Missing directory → created recursively.
   - Write error → throws and logs.
4. **Configuration Updates**
   - Valid partial update succeeds.
   - Invalid update rejected.
5. **Feature Flags**
   - Read specific flags.
   - Update multiple flags without affecting others.
6. **Memory Mode Retrieval**
   - Returns one of supported modes.
7. **Validation Scenarios**
   - Invalid version, environment, storage type, memory mode.
   - SQLite storage without path.
   - AI provider invalid, missing API key warning.
   - AI `maxTokens` and `temperature` out of range.
   - Storage max size negative.
   - Performance cache size invalid.
   - Unexpected errors handled gracefully.
8. **Validation Error Reporting**
   - `getValidationErrors` returns detailed messages for invalid config.
   - Returns empty array for valid config.

## Test Execution

Run all tests with coverage:

```
npm run test:coverage
```

## Expected Result

- All tests pass.
- Overall branch coverage ≥95%.
- No uncovered lines in Module M001 validation logic or configuration management paths.
