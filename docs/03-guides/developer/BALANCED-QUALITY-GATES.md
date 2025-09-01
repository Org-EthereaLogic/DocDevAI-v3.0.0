# Balanced Quality Gates System

This document explains DevDocAI's intelligent quality gates system that adapts validation strictness based on what you're changing and where you're committing.

## Overview

The quality gates system provides three tiers of validation:

1. **Documentation-Only**: Fast validation for documentation changes
2. **Work-in-Progress**: Relaxed validation for development modules  
3. **Production Code**: Full validation for completed modules

## Smart Pre-Commit Hooks

### File Type Detection

The system automatically detects:

- Documentation changes (`.md`, README, CLAUDE.md)
- Source code changes (`src/` directory)
- Work-in-progress modules (M002, M003, M004, etc.)
- Configuration changes (`.json`, `.yml`, `.yaml`)

### Validation Levels

#### 📝 Documentation-Only Commits

**Triggers**: Only `.md` files changed, no source code
**Validation**:

- ✅ Prettier formatting check
- ✅ YAML syntax validation (if workflows changed)
- ⏩ Skips TypeScript, ESLint, and test execution

```bash
# Example: Updating CLAUDE.md or README.md
git add CLAUDE.md
git commit -m "docs: update development guide"
# Fast validation ~5-10 seconds
```

#### 🚧 Work-in-Progress Commits

**Triggers**: Changes to M002-LocalStorageSystem, M003-, M004- modules
**Validation**:

- ⚠️ Relaxed TypeScript check (shows errors but allows commit)
- ⚠️ Relaxed ESLint check (max 50 warnings, uses `.eslintrc.wip.js`)
- ✅ Prettier formatting
- ⚡ Module-specific tests only

```bash
# Example: Working on M002 implementation
git add src/modules/M002-LocalStorageSystem/
git commit -m "feat(M002): add database connection service"
# Allows TypeScript errors during development
```

#### 🔧 Production Code Commits  

**Triggers**: Changes to M001 (completed modules) or non-WIP source code
**Validation**:

- ✅ Strict TypeScript type checking
- ✅ Full ESLint analysis
- ✅ Complete test execution
- ✅ Coverage verification (85% minimum)

```bash
# Example: Modifying completed M001 module
git add src/modules/M001-ConfigurationManager/
git commit -m "fix(M001): improve error handling"
# Full validation required
```

## Smart Pre-Push Hooks

### Branch-Based Validation

#### 🔒 Main/Master Branch

**Full CI Pipeline**: All quality gates must pass

- Build verification
- Complete test suite
- Security scanning
- Coverage validation

#### 🔧 Develop Branch

**Standard Validation**: Balanced approach

- Build check (warnings allowed)
- Module-specific tests
- Basic quality verification

#### 🌿 Feature Branches

**Minimal Validation**: Development-friendly

- TypeScript compilation check
- Work-in-progress modules allowed
- Focus on preventing major breakage

## New NPM Scripts

### Documentation Validation

```bash
npm run quality:check:docs     # Fast validation for docs
npm run prettier:check         # Check all file formatting
```

### Work-in-Progress Validation  

```bash
npm run quality:check:wip      # Relaxed validation for WIP modules
npm run lint:wip               # ESLint with relaxed rules
npm run ci:pipeline:wip        # WIP-friendly CI pipeline
```

### Production Validation

```bash
npm run quality:check          # Full validation (unchanged)
npm run ci:pipeline           # Complete CI pipeline (unchanged)
```

## Intelligent CI/CD Pipeline

The new `smart-ci.yml` workflow adapts based on:

### Change Detection

- Automatically detects file types in commits/PRs
- Identifies work-in-progress modules
- Determines documentation-only changes

### Adaptive Validation

- **Docs-only PRs**: Format validation only
- **WIP modules**: Relaxed TypeScript/ESLint checks
- **Production code**: Full validation pipeline
- **Main branch**: Strictest validation

### Parallel Execution

- Runs only necessary checks
- Skips irrelevant validations
- Provides clear feedback on what was checked

## Validation Helper Script

Use the validation helper to understand what checks will run:

```bash
./scripts/validation-helper.sh
```

**Output Example**:

```
🔍 DevDocAI Smart Validation Helper
==================================
📁 Staged files:
   CLAUDE.md
   README.md

🎯 Recommended validation strategy:
   📝 Documentation-only changes detected
   ✅ Quick validation: npm run quality:check:docs
   🚀 Quick commit: This should pass pre-commit hooks easily
```

## Override Options

### When to Use --no-verify

```bash
git commit --no-verify   # Emergency only - bypasses all hooks
git push --no-verify     # Emergency only - bypasses pre-push
```

**Appropriate scenarios**:

- Critical hotfixes
- Documentation typos in production
- CI/CD system issues
- Emergency deployments

**Never use for**:

- Regular development workflow
- Avoiding legitimate quality issues
- Bypassing test failures

## Configuration Files

### ESLint Configurations

- `.eslintrc.js`: Strict rules for production code
- `.eslintrc.wip.js`: Relaxed rules for work-in-progress modules

### Lint-Staged Configuration

- Smart file-type detection
- Conditional ESLint execution
- Work-in-progress module handling

### Hook Files

- `.husky/pre-commit`: Smart pre-commit validation
- `.husky/pre-push`: Branch-aware pre-push validation

## Benefits

### Developer Experience

- ✅ Fast documentation commits (~5-10 seconds)
- ✅ No more `--no-verify` needed for legitimate WIP code
- ✅ Clear feedback on validation requirements
- ✅ Context-aware error messages

### Code Quality

- ✅ Maintains high standards for production code
- ✅ Prevents broken code in main branch
- ✅ Allows iterative development in feature branches
- ✅ Comprehensive coverage for completed modules

### CI/CD Performance

- ✅ Runs only necessary checks
- ✅ Faster feedback loops
- ✅ Parallel execution optimization
- ✅ Clear validation status reporting

## Migration Notes

### Existing Workflows

- Old validation commands still work
- New scripts provide enhanced functionality
- Gradual adoption possible

### Team Onboarding

- Use `./scripts/validation-helper.sh` to understand changes
- Review staged files before committing
- Trust the system - it will guide you to the right validation level

## Troubleshooting

### Common Issues

**"TypeScript errors but hooks passed"**

- Expected for WIP modules in feature branches
- Fix errors before merging to develop/main

**"Pre-commit hooks taking too long"**  

- Check if you're committing large source changes
- Use `./scripts/validation-helper.sh` to verify detection

**"ESLint errors in WIP module"**

- Switch to WIP validation: `npm run quality:check:wip`
- Or commit to feature branch where relaxed rules apply

**"Documentation commit failed"**

- Usually formatting issue
- Run: `npm run prettier:fix-all`
- Recommit

### Getting Help

1. Run validation helper: `./scripts/validation-helper.sh`
2. Check file type detection in hook output
3. Use appropriate npm script for your change type
4. Review this guide for validation tier explanation
