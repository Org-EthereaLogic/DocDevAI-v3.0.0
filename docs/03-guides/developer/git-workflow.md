# Git Workflow - Sole Developer

## Overview

This project uses a simplified Git workflow optimized for sole developer
productivity.

## Main Branch Development

- All development happens directly on the `main` branch
- No feature branches or pull requests required
- Direct push to `main` is enabled and encouraged

## Quick Commands

### Regular Workflow

```bash
# Make your changes
git add -A
git commit -m "your commit message"
git push origin main
```

### Using Helper Script

```bash
# Use the provided helper script
./tools/git-push-main.sh
```

### Using Git Aliases

```bash
# Quick commit and push
git quick-commit "your commit message"

# Or just push to main
git push-main
```

## Configuration

The repository is configured for:

- Direct push to `main` branch
- No branch protection rules
- Simplified CI/CD triggers on `main` push

## Benefits

- Faster development cycle
- No merge conflicts
- Simplified mental model
- Direct deployment from `main`

---

_Configuration updated: 2025-08-24_
