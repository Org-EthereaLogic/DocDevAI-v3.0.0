# Codacy Integration Guide

## Overview

DevDocAI uses Codacy for automated code quality analysis and coverage tracking. This document explains how to set up and use Codacy integration.

## Important: GitHub Repository Secret

**You must add the Codacy Project Token to GitHub Secrets:**

1. Go to your repository on GitHub
2. Navigate to Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Name: `CODACY_PROJECT_TOKEN`
5. Value: `dcdadf82f58d4b59b6e3f07aefdd0c92`
6. Click "Add secret"

Without this secret, the CI/CD pipeline cannot upload coverage or run analysis.

## Setup

### 1. Environment Configuration

Set your Codacy project token:
```bash
export CODACY_PROJECT_TOKEN=dcdadf82f58d4b59b6e3f07aefdd0c92
```

### 2. Local Analysis

Run Codacy analysis locally:
```bash
npm run codacy:analyze    # JSON output
npm run codacy:check     # Text output
npm run security:scan    # Security scanning with audit
```

### 3. Coverage Reporting

Generate and upload coverage:
```bash
# Generate coverage report
npm run test:coverage

# Upload to Codacy
npm run coverage:upload

# Or do both in one command
npm run coverage:report
```

## CI/CD Integration

Coverage is automatically uploaded to Codacy in GitHub Actions:
- Runs on every push to main/develop branches
- Runs on all pull requests
- Coverage reports are uploaded after unit tests

## Viewing Reports

### Codacy Dashboard
View your code quality and coverage reports at:
- [DevDocAI on Codacy](https://app.codacy.com/gh/Org-EthereaLogic/DevDocAI)

### Coverage Status
Current coverage metrics:
- **Lines**: Coverage percentage of executed lines
- **Statements**: Coverage percentage of executed statements
- **Functions**: Coverage percentage of called functions
- **Branches**: Coverage percentage of executed branches

## Quality Gates

The project enforces the following quality standards:
- **Minimum Coverage**: 80% (will increase to 90% after full implementation)
- **Code Quality**: Grade A or B required
- **Security Issues**: No critical or high severity issues allowed
- **Code Complexity**: Cyclomatic complexity < 10 per function

## Scripts Reference

| Script | Description |
|--------|-------------|
| `npm run codacy:analyze` | Run local Codacy analysis (JSON format) |
| `npm run codacy:check` | Run local Codacy analysis (text format) |
| `npm run coverage:upload` | Upload coverage to Codacy |
| `npm run coverage:report` | Generate coverage and upload |
| `npm run security:scan` | Run security audit with Codacy |

## Understanding Codacy Status

### Coverage vs Analysis

Codacy provides two different services:

1. **Coverage Reports** (✅ Working)
   - Shows test coverage percentages
   - Uploaded after running tests
   - Status: "Processed" means coverage was received

2. **Code Analysis** (🔄 Setup Required)
   - Static code analysis for quality issues
   - Requires Java runtime locally OR GitHub webhook
   - Status: "Commit not analyzed" means code quality analysis didn't run

### Why "Commit not analyzed"?

This message appears when Codacy hasn't performed static analysis on your code. This is separate from coverage and requires either:
- Java installed locally (for local analysis)
- GitHub webhook configured (for automatic analysis on push)
- GitHub Actions with Codacy Analysis CLI (configured in CI)

The coverage upload still works even if commits show "not analyzed".

## Troubleshooting

### "Commit not analyzed" Issue
1. **For local analysis**: Install Java from https://www.java.com
2. **For automatic analysis**: Push to GitHub (triggers webhook)
3. **Check status**: Visit https://app.codacy.com/gh/Org-EthereaLogic/DevDocAI

### Coverage Not Uploading
1. Ensure `CODACY_PROJECT_TOKEN` is set
2. Check coverage reports exist: `ls coverage/`
3. Run coverage generation: `npm run test:coverage`

### Local Analysis Issues
1. Ensure Java is installed (required for Codacy CLI)
2. Check network connection for downloading CLI
3. Try clearing cache: `rm -rf ~/.codacy`

### CI/CD Issues
1. Verify `CODACY_PROJECT_TOKEN` is set in GitHub Secrets
2. Check GitHub Actions logs for detailed errors
3. Ensure coverage reports are generated before upload

## Best Practices

1. **Run locally before pushing**: `npm run coverage:report`
2. **Fix issues immediately**: Address Codacy issues in the same commit
3. **Monitor trends**: Check coverage trends in Codacy dashboard
4. **Use quality gates**: Don't merge PRs that fail quality checks

## Integration Rules (from CLAUDE.md)

After ANY file modification:
- **MANDATORY**: Run `codacy_cli_analyze` for each edited file
- If issues found: Fix immediately before continuing

After ANY dependency installation:
- **IMMEDIATE**: Run security scan with `npm run security:scan`
- Check for vulnerabilities in new packages
- Fix security issues before any other work

## Support

For issues with Codacy integration:
1. Check [Codacy Documentation](https://docs.codacy.com)
2. Review GitHub Actions logs
3. Contact project maintainers