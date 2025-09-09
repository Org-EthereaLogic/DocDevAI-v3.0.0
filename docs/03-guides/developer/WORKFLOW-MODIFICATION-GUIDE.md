# GitHub Actions Workflow Modification Guide

## Overview

This guide outlines the proper procedures for modifying GitHub Actions workflows in the DevDocAI project. Following these procedures helps prevent workflow failures and maintains CI/CD pipeline integrity.

## Pre-Modification Checklist

Before modifying any workflow file:

- [ ] Understand the current workflow purpose and structure
- [ ] Review recent workflow run history for context
- [ ] Ensure you have proper permissions
- [ ] Have YAML validation tools installed locally
- [ ] Create a feature branch for changes

## Required Tools

### Local Installation (Recommended)

```bash
# Install yamllint for YAML validation (REQUIRED)
pip install yamllint

# Install actionlint for GitHub Actions validation (HIGHLY RECOMMENDED)
# macOS
brew install actionlint

# Linux/WSL
go install github.com/rhysd/actionlint/cmd/actionlint@latest

# Alternative: Download pre-built binary
curl -L https://github.com/rhysd/actionlint/releases/latest/download/actionlint_1.6.26_linux_amd64.tar.gz | tar xz
sudo mv actionlint /usr/local/bin/

# Verify installation
yamllint --version
actionlint --version
```

### Development Container Setup

If using the DevDocAI development container, install tools inside the container:

```bash
# Enter the container
./docker-dev.sh shell

# Install validation tools
pip install yamllint
go install github.com/rhysd/actionlint/cmd/actionlint@latest

# Test the tools
yamllint .github/workflows/security-audit.yml
actionlint .github/workflows/security-audit.yml
```

## Workflow Modification Process

### 1. Create Feature Branch

```bash
git checkout -b fix/workflow-name-description
```

### 2. Make Changes

Edit the workflow file in `.github/workflows/`:

```yaml
# Example: Adding permissions block
jobs:
  deploy:
    permissions:
      contents: read
      deployments: write
```

### 3. Validate Locally

#### YAML Syntax Validation

```bash
# Validate YAML syntax
yamllint .github/workflows/your-workflow.yml

# Or use Python for basic validation
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/your-workflow.yml'))"
```

#### GitHub Actions Specific Validation

```bash
# If actionlint is installed
actionlint .github/workflows/your-workflow.yml

# Or use GitHub's online validator:
# https://rhysd.github.io/actionlint/
```

### 4. Test with Act (Optional)

Test workflows locally using [act](https://github.com/nektos/act):

```bash
# Install act
brew install act  # macOS
# or download from https://github.com/nektos/act

# Test workflow locally
act -W .github/workflows/your-workflow.yml
```

### 5. Commit Changes

```bash
# Stage changes
git add .github/workflows/your-workflow.yml

# Commit with descriptive message
git commit -m "fix(ci): correct permissions in deploy workflow

- Added missing permissions block to deploy-development job
- Fixed YAML syntax error in permissions declaration
- Validated with yamllint and actionlint"
```

### 6. Create Pull Request

```bash
# Push branch
git push origin fix/workflow-name-description

# Create PR via GitHub CLI
gh pr create --title "Fix workflow permissions" \
  --body "Fixes YAML syntax errors in deploy.yml workflow"
```

### 7. Monitor Workflow Runs

After merging:

1. Check Actions tab for workflow execution
2. Monitor for any failures
3. Review logs if issues occur

## Common Issues and Solutions

### Workflow-Level Permissions (Most Common Error)

**Problem**: Workflow fails immediately with "permissions" field error

```yaml
# ❌ CRITICAL ERROR - Causes 100% workflow failures
permissions:
  contents: read
  security-events: write

name: My Workflow
```

```yaml
# ✅ Correct - Permissions at job level
name: My Workflow

on:
  push:
    branches: [main]

jobs:
  my-job:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
```

**Root Cause**: GitHub Actions does not support workflow-level permissions in this format. The `permissions` block must be placed under individual jobs, not at the workflow level.

### Missing Permissions Block

**Problem**: Job fails with permission denied error

```yaml
# ❌ Incorrect
jobs:
  deploy:
    runs-on: ubuntu-latest
    contents: read  # Missing 'permissions:' key
```

```yaml
# ✅ Correct
jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      deployments: write
```

### Invalid YAML Indentation

**Problem**: Workflow fails to parse

```yaml
# ❌ Incorrect - inconsistent indentation
jobs:
  test:
   runs-on: ubuntu-latest
    steps:
     - uses: actions/checkout@v4
```

```yaml
# ✅ Correct - consistent 2-space indentation
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
```

### Undefined Secrets

**Problem**: Workflow fails with "secret not found"

```yaml
# Ensure secrets are defined in repository settings
# Settings → Secrets and variables → Actions

env:
  API_KEY: ${{ secrets.API_KEY }}  # Must exist in secrets
```

## Validation Checklist

Before committing workflow changes:

- [ ] YAML syntax validated with `yamllint`
- [ ] GitHub Actions syntax validated with `actionlint` or online validator
- [ ] Permissions blocks properly formatted
- [ ] All required secrets documented
- [ ] Environment variables defined
- [ ] Job dependencies correctly specified
- [ ] Conditional logic tested
- [ ] Branch protection rules considered

## Emergency Fixes

If a workflow is blocking critical operations:

1. **Revert via GitHub UI**:
   - Go to the problematic commit
   - Click "Revert"
   - Create revert PR
   - Merge immediately

2. **Quick Fix via CLI**:

```bash
# Revert last commit
git revert HEAD
git push origin main

# Or disable workflow temporarily
mv .github/workflows/problem.yml .github/workflows/problem.yml.disabled
git add -A
git commit -m "fix: temporarily disable failing workflow"
git push
```

## Best Practices

1. **Always validate locally** before pushing
2. **Use feature branches** for workflow changes
3. **Test incrementally** - make small changes
4. **Document changes** in commit messages
5. **Monitor after deployment** - check workflow runs
6. **Keep workflows simple** - complexity increases failure risk
7. **Version control secrets** documentation (not values!)
8. **Regular audits** - review and update workflows quarterly

## Automated Validation

The project includes comprehensive pre-commit hooks that automatically validate YAML files and prevent the most common workflow failures:

### Pre-Commit Hook Features

```bash
# Hook automatically runs on commit if YAML files are changed
git commit -m "fix: update workflow"
# 📝 Validating YAML files...
# 🔧 Validating GitHub Actions workflows...
# ✅ YAML syntax validation passed
# ✅ GitHub Actions workflow validation passed
```

**What Gets Checked:**

1. **YAML Syntax**: Basic YAML structure and formatting via `yamllint`
2. **GitHub Actions Syntax**: Comprehensive workflow validation via `actionlint`
3. **Common Field Ordering**: Detects workflow-level permissions blocks (primary failure cause)
4. **Workflow Structure**: Validates job definitions, steps, and dependencies
5. **Secret References**: Checks for undefined secrets and variables

### Manual Validation Commands

```bash
# Run all pre-commit checks
npm run pre-commit

# YAML-only validation
yamllint .github/workflows/*.yml

# GitHub Actions specific validation (if actionlint installed)
actionlint .github/workflows/*.yml

# Basic validation without actionlint
python3 -c "import yaml; [yaml.safe_load(open(f)) for f in ['.github/workflows/ci.yml']]"
```

### Prevention Measures Implemented

1. **Enhanced Pre-Commit Hooks**: Automatically catch permissions placement errors
2. **Actionlint Integration**: Comprehensive GitHub Actions workflow validation
3. **Field Ordering Detection**: Specific checks for workflow-level permissions
4. **Clear Error Messages**: Detailed guidance on how to fix common issues
5. **Fallback Validation**: Basic checks even without actionlint installed

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Workflow Syntax Reference](https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions)
- [YAML Specification](https://yaml.org/spec/)
- [actionlint Documentation](https://github.com/rhysd/actionlint)
- [yamllint Documentation](https://yamllint.readthedocs.io/)

## Support

If you encounter issues:

1. Check workflow run logs in GitHub Actions tab
2. Validate syntax with tools mentioned above
3. Review this guide for common issues
4. Consult team lead or DevOps engineer
5. Open issue in repository with details

---

**Last Updated**: 2025-08-25
**Version**: 1.0.0
**Maintained By**: DevOps Team
