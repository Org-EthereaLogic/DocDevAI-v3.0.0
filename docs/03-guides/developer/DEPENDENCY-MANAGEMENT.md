# Dependency Management Guide

## Overview

DocDevAI v3.0.0 implements comprehensive dependency management and security scanning to prevent vulnerabilities like the recent aiohttp incident (11 vulnerabilities from unused dependency). This guide covers our multi-layered approach to dependency security.

## Security Layers

### 1. Pre-commit Hooks (Developer's First Line of Defense)

Pre-commit hooks run automatically before each commit, catching issues early:

- **Security scanning**: Detects secrets, vulnerabilities, and security issues
- **Dead code detection**: Identifies unused imports and unreachable code
- **Dependency checking**: Finds unused packages before they enter the codebase
- **Auto-fixing**: Automatically fixes formatting and simple issues

### 2. CI/CD Pipeline (Automated Verification)

GitHub Actions workflow runs on every push and PR:

- **Multi-version testing**: Python 3.9-3.11, Node.js 18-20
- **Vulnerability scanning**: pip-audit, safety, npm audit
- **Unused dependency detection**: Custom analysis tools
- **Daily scheduled scans**: Catches new vulnerabilities in existing dependencies

### 3. Manual Tools (On-Demand Analysis)

Scripts and tools for deeper investigation:

- `scripts/check_unused_deps.py`: Detailed unused dependency analysis
- `pipdeptree`: Visualize dependency trees
- `vulture`: Find dead code with configurable confidence

## Installation

### Quick Setup

```bash
# Run the automated setup script
./scripts/setup-hooks.sh
```

This script will:
1. Check prerequisites (Python, Node.js, Git)
2. Install security tools (pre-commit, vulture, bandit, safety, etc.)
3. Configure pre-commit hooks
4. Run initial security checks
5. Create reference documentation

### Manual Setup

If you prefer manual installation:

```bash
# Install Python tools
pip install pre-commit vulture bandit safety pip-audit pipdeptree autoflake

# Install Node.js tools
npm install -g depcheck npm-audit-resolver better-npm-audit

# Install pre-commit hooks
pre-commit install --install-hooks
pre-commit install --hook-type commit-msg

# Create secrets baseline
detect-secrets scan --baseline .secrets.baseline
```

## Daily Workflow

### Before Committing

Pre-commit hooks run automatically, but you can run them manually:

```bash
# Run all hooks on staged files
pre-commit run

# Run all hooks on all files
pre-commit run --all-files

# Run specific hook
pre-commit run vulture --all-files
```

### Skipping Hooks (When Necessary)

Sometimes you need to skip hooks for legitimate reasons:

```bash
# Skip specific hooks
SKIP=vulture,mypy git commit -m "WIP: experimental feature"

# Skip all hooks (emergency only!)
git commit --no-verify -m "emergency fix"
```

**Important**: Always document why you skipped hooks in the commit message.

### Checking Dependencies

#### Find Unused Python Dependencies

```bash
# Basic check
python scripts/check_unused_deps.py

# Verbose output
python scripts/check_unused_deps.py --verbose

# Strict mode (exits with error if unused found)
python scripts/check_unused_deps.py --strict
```

#### Find Unused Node.js Dependencies

```bash
# Check for unused npm packages
npx depcheck

# With custom config
npx depcheck --config .depcheckrc.json
```

#### Security Audits

```bash
# Python security audit
pip-audit              # Check for known vulnerabilities
safety check          # Alternative vulnerability scanner
bandit -r devdocai    # Static security analysis

# Node.js security audit  
npm audit            # Built-in npm security audit
npm audit fix        # Auto-fix vulnerabilities
better-npm-audit audit  # Enhanced audit with fewer false positives
```

## Handling Common Scenarios

### False Positives

#### Dead Code Detection (Vulture)

Vulture might flag code that's actually used (e.g., SQLAlchemy models, Django views):

1. Add to `.vulture_whitelist.py`:
```python
# SQLAlchemy attributes
_.id
_.created_at
_.__tablename__

# Your false positive
_.my_special_method
```

2. Or use inline comments:
```python
def rarely_used_function():  # noqa: vulture
    pass
```

#### Unused Dependencies

Some packages aren't imported directly but are still needed:

1. Edit `scripts/check_unused_deps.py`:
```python
JUSTIFIED_UNUSED = {
    'package-name': "Used by CLI tool, not imported",
    'another-package': "Required by package-x at runtime",
}
```

2. Or document in requirements.txt:
```txt
# Required for CLI operations (not imported directly)
alembic>=1.12.0

# Runtime dependency of package-x
some-package>=1.0.0
```

#### Secret Detection

For false positives in secret detection:

```bash
# Update the baseline after reviewing
detect-secrets scan --baseline .secrets.baseline

# Or add inline comment
API_KEY = "not-a-real-key"  # pragma: allowlist secret
```

### Adding New Dependencies

1. **Justify the need**: Document why this dependency is necessary
2. **Check security**: Run `pip-audit` or `npm audit` after adding
3. **Check license**: Ensure license compatibility
4. **Update documentation**: Add to this guide if it's a special case

```bash
# Python
pip install new-package
pip freeze > requirements.txt
pip-audit  # Check for vulnerabilities

# Node.js
npm install new-package
npm audit  # Check for vulnerabilities
```

### Removing Dependencies

1. **Check usage**: Ensure it's truly unused
```bash
python scripts/check_unused_deps.py --verbose
```

2. **Remove package**:
```bash
# Python
pip uninstall package-name
pip freeze > requirements.txt

# Node.js
npm uninstall package-name
```

3. **Test thoroughly**: Run full test suite
```bash
pytest
npm test
```

### Updating Dependencies

1. **Check for updates**:
```bash
# Python
pip list --outdated

# Node.js  
npm outdated
```

2. **Update safely**:
```bash
# Python - update specific package
pip install --upgrade package-name

# Node.js - update specific package
npm update package-name

# Update all (careful!)
pip install --upgrade -r requirements.txt
npm update
```

3. **Test after updating**:
```bash
# Run security checks
pip-audit
npm audit

# Run tests
pytest
npm test
```

## CI/CD Integration

### GitHub Actions Workflow

The `.github/workflows/dependency-check.yml` workflow runs:

- **On every push**: to main/develop branches
- **On every PR**: before merging
- **Daily at 2 AM UTC**: scheduled vulnerability scan
- **On demand**: via workflow_dispatch

### Workflow Features

1. **Python checks**:
   - pip-audit for vulnerabilities
   - safety for known security issues
   - Custom unused dependency detection
   - vulture for dead code
   - bandit for security analysis

2. **Node.js checks**:
   - npm audit for vulnerabilities
   - depcheck for unused packages
   - License compliance verification

3. **Reporting**:
   - GitHub Step Summary with detailed results
   - Issue creation on scheduled scan failures
   - Non-blocking warnings for non-critical issues

### Configuring Strictness

By default, the CI only fails on critical issues. To make it stricter:

```yaml
# Trigger with strict mode
workflow_dispatch:
  inputs:
    strict_mode:
      default: 'true'  # Fail on warnings
```

Or modify the workflow to always be strict:

```yaml
env:
  STRICT_MODE: true  # Always fail on warnings
```

## Security Best Practices

### 1. Regular Audits

- Run security audits weekly: `pip-audit`, `npm audit`
- Review dependency updates monthly
- Check for unused dependencies before releases

### 2. Minimal Dependencies

- Only add dependencies that provide significant value
- Prefer standard library solutions when possible
- Consider vendoring critical small dependencies

### 3. Version Pinning

- Pin exact versions in production: `package==1.2.3`
- Use ranges in development: `package>=1.2.0,<2.0.0`
- Document why specific versions are required

### 4. Supply Chain Security

- Verify package authenticity before installing
- Use lock files: `requirements.txt`, `package-lock.json`
- Monitor for typosquatting attacks

### 5. Automated Updates

- Use Dependabot for automated updates
- Configure security alerts in GitHub
- Review and test all automated updates

## Troubleshooting

### Pre-commit Hooks Not Running

```bash
# Reinstall hooks
pre-commit uninstall
pre-commit install --install-hooks

# Check hook status
pre-commit run --all-files --verbose
```

### CI Pipeline Failing

1. Check the workflow run logs in GitHub Actions
2. Run the same checks locally:
```bash
# Replicate CI environment
python scripts/check_unused_deps.py --strict
pip-audit
safety check
vulture devdocai --min-confidence 80
```

### Performance Issues

If hooks are slow:

```bash
# Skip expensive hooks during development
SKIP=mypy,vulture git commit -m "dev: quick commit"

# Run expensive checks separately
pre-commit run mypy --all-files
```

### Conflicts with IDE

Some IDEs have their own formatters that conflict with pre-commit:

1. Configure IDE to use the same tools (black, isort, eslint)
2. Or disable IDE formatting for the project
3. Or skip formatting hooks and let IDE handle it

## Advanced Configuration

### Custom Hook Configuration

Edit `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: custom-check
        name: Custom security check
        entry: ./scripts/my-custom-check.sh
        language: script
        files: \.(py|js)$
```

### Dependency Allowlists

Create `.dependency-allowlist.json`:

```json
{
  "python": {
    "allowed": ["numpy", "pandas", "sqlalchemy"],
    "banned": ["requests", "urllib3<2.0.0"],
    "exceptions": {
      "requests": "Use aiohttp instead"
    }
  }
}
```

### Security Policy

Create `SECURITY.md`:

```markdown
# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 3.0.x   | :white_check_mark: |
| < 3.0   | :x:                |

## Reporting Vulnerabilities

Email: security@devdocai.example.com
```

## Metrics and Monitoring

### Track Security Metrics

```bash
# Count vulnerabilities over time
git log --grep="security" --oneline | wc -l

# Track dependency changes
git diff HEAD~10 requirements.txt

# Measure hook execution time
time pre-commit run --all-files
```

### Security Dashboard

Create a dashboard to track:

- Number of dependencies
- Known vulnerabilities
- Time since last audit
- Unused dependency count
- Security issue resolution time

## Appendix: Tool Reference

### Python Security Tools

| Tool | Purpose | Command |
|------|---------|---------|
| pip-audit | Vulnerability scanning | `pip-audit` |
| safety | Known security issues | `safety check` |
| bandit | Static security analysis | `bandit -r devdocai` |
| vulture | Dead code detection | `vulture devdocai` |
| pipdeptree | Dependency visualization | `pipdeptree` |

### Node.js Security Tools

| Tool | Purpose | Command |
|------|---------|---------|
| npm audit | Vulnerability scanning | `npm audit` |
| depcheck | Unused dependencies | `npx depcheck` |
| better-npm-audit | Enhanced audit | `better-npm-audit audit` |
| license-checker | License compliance | `npx license-checker` |

### Pre-commit Hooks

| Hook | Purpose | Auto-fix |
|------|---------|----------|
| detect-secrets | Find secrets | No |
| bandit | Security scan | No |
| vulture | Dead code | No |
| autoflake | Unused imports | Yes |
| black | Format Python | Yes |
| isort | Sort imports | Yes |
| eslint | Lint JavaScript | Yes |

## Conclusion

Dependency management is critical for security. By following this guide and using our automated tools, you can:

- Prevent vulnerabilities before they enter the codebase
- Detect issues early through pre-commit hooks
- Maintain a clean, secure dependency tree
- Respond quickly to new vulnerabilities

Remember: **Every dependency is a potential security risk. Only add what you truly need, and always verify before trusting.**

For questions or suggestions, please open an issue or submit a PR to improve our dependency management process.