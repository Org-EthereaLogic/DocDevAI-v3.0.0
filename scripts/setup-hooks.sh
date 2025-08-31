#!/bin/bash
# Setup script for DocDevAI security hooks and dependency management
# This script installs pre-commit hooks and validates the development environment

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    local color=$1
    shift
    echo -e "${color}$@${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to get Python version
get_python_version() {
    python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
}

# Function to get Node version
get_node_version() {
    node -v | sed 's/v//'
}

print_color $BLUE "╔══════════════════════════════════════════════════════════════╗"
print_color $BLUE "║     DocDevAI v3.0.0 - Security Hooks Setup                  ║"
print_color $BLUE "╚══════════════════════════════════════════════════════════════╝"
echo

# Check for required tools
print_color $YELLOW "🔍 Checking prerequisites..."

# Check Python
if ! command_exists python3; then
    print_color $RED "❌ Python 3 is not installed"
    exit 1
fi

PYTHON_VERSION=$(get_python_version)
print_color $GREEN "✅ Python $PYTHON_VERSION detected"

# Check Node.js
if ! command_exists node; then
    print_color $RED "❌ Node.js is not installed"
    exit 1
fi

NODE_VERSION=$(get_node_version)
print_color $GREEN "✅ Node.js $NODE_VERSION detected"

# Check Git
if ! command_exists git; then
    print_color $RED "❌ Git is not installed"
    exit 1
fi

GIT_VERSION=$(git --version | awk '{print $3}')
print_color $GREEN "✅ Git $GIT_VERSION detected"

echo

# Install Python security tools
print_color $YELLOW "📦 Installing Python security tools..."

# Create a virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_color $BLUE "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate || {
    print_color $RED "Failed to activate virtual environment"
    exit 1
}

# Upgrade pip
pip install --quiet --upgrade pip

# Install security tools
print_color $BLUE "Installing security and analysis tools..."
pip install --quiet pre-commit vulture bandit safety pip-audit pipdeptree autoflake black isort flake8 mypy

# Install additional flake8 plugins
pip install --quiet flake8-docstrings flake8-bugbear flake8-comprehensions flake8-simplify

# Install type stubs
pip install --quiet types-requests types-PyYAML types-python-dateutil

print_color $GREEN "✅ Python security tools installed"
echo

# Install Node.js security tools
print_color $YELLOW "📦 Installing Node.js security tools..."

# Check if package.json exists
if [ -f "package.json" ]; then
    # Install npm packages if not already installed
    if [ ! -d "node_modules" ]; then
        npm install --silent
    fi
    
    # Install global tools
    npm install -g --silent depcheck npm-audit-resolver better-npm-audit license-checker
    
    print_color $GREEN "✅ Node.js security tools installed"
else
    print_color $YELLOW "⚠️  No package.json found, skipping Node.js tools"
fi

echo

# Setup pre-commit hooks
print_color $YELLOW "🔧 Setting up pre-commit hooks..."

# Initialize pre-commit
if [ -f ".pre-commit-config.yaml" ]; then
    pre-commit install --install-hooks
    pre-commit install --hook-type commit-msg
    
    # Create secrets baseline if it doesn't exist
    if [ ! -f ".secrets.baseline" ]; then
        print_color $BLUE "Creating secrets baseline..."
        detect-secrets scan --baseline .secrets.baseline > /dev/null 2>&1 || true
    fi
    
    # Create vulture whitelist if it doesn't exist
    if [ ! -f ".vulture_whitelist.py" ]; then
        print_color $BLUE "Creating vulture whitelist..."
        cat > .vulture_whitelist.py << 'EOF'
# Vulture whitelist - add false positives here
# SQLAlchemy model attributes
_.id
_.created_at
_.updated_at
_.deleted_at
_.metadata
_.query
_.session
_.__tablename__
_.__table_args__

# Pydantic model attributes
_.model_config
_.model_fields
_.model_validate

# Common test fixtures
_.fixture
_.pytest_fixture
EOF
    fi
    
    print_color $GREEN "✅ Pre-commit hooks installed"
else
    print_color $RED "❌ .pre-commit-config.yaml not found"
    exit 1
fi

echo

# Run initial checks
print_color $YELLOW "🔍 Running initial security checks..."

# Check for unused Python dependencies
print_color $BLUE "Checking for unused Python dependencies..."
python scripts/check_unused_deps.py || print_color $YELLOW "⚠️  Some unused dependencies detected (non-critical)"

# Check for security vulnerabilities
print_color $BLUE "Checking for security vulnerabilities..."
safety check --json > /dev/null 2>&1 || print_color $YELLOW "⚠️  Some vulnerabilities detected (review needed)"

# Run pre-commit on all files (dry run)
print_color $BLUE "Validating pre-commit configuration..."
pre-commit run --all-files --show-diff-on-failure || print_color $YELLOW "⚠️  Some files need formatting (will be fixed on commit)"

echo

# Create Git hooks directory if it doesn't exist
if [ ! -d ".git/hooks" ]; then
    mkdir -p .git/hooks
fi

# Create a custom prepare-commit-msg hook for better messages
cat > .git/hooks/prepare-commit-msg << 'EOF'
#!/bin/bash
# Add issue number and emoji to commit messages

COMMIT_MSG_FILE=$1
COMMIT_SOURCE=$2

# Only add to user commits, not merges or squashes
if [ -z "$COMMIT_SOURCE" ]; then
    # Get current branch name
    BRANCH=$(git rev-parse --abbrev-ref HEAD)
    
    # Extract issue number if present
    ISSUE=$(echo "$BRANCH" | grep -oE '[0-9]+' | head -1)
    
    # Read current message
    MSG=$(cat "$COMMIT_MSG_FILE")
    
    # Add issue reference if not already present
    if [ -n "$ISSUE" ] && ! grep -q "#$ISSUE" "$COMMIT_MSG_FILE"; then
        echo "$MSG (#$ISSUE)" > "$COMMIT_MSG_FILE"
    fi
fi
EOF

chmod +x .git/hooks/prepare-commit-msg

# Create quick reference card
print_color $YELLOW "📚 Creating quick reference card..."

cat > SECURITY_HOOKS_REFERENCE.md << 'EOF'
# Security Hooks Quick Reference

## Pre-commit Hooks Installed

### Security Checks (Always Run)
- 🔐 **detect-secrets**: Prevents committing secrets/credentials
- 🛡️ **bandit**: Security vulnerability scanning
- 🔒 **safety**: Checks dependencies for known vulnerabilities

### Code Quality (Auto-fix when possible)
- 🧹 **autoflake**: Removes unused imports and variables (auto-fix)
- 🦅 **vulture**: Detects dead code
- 📦 **check-unused-deps**: Finds unused dependencies
- 🎨 **black**: Python code formatting (auto-fix)
- 📚 **isort**: Import sorting (auto-fix)
- 🔍 **flake8**: Python linting
- 🔎 **mypy**: Type checking

## Usage Commands

### Run all hooks manually
```bash
pre-commit run --all-files
```

### Run specific hook
```bash
pre-commit run <hook-id> --all-files
```

### Skip hooks for a commit (use sparingly)
```bash
# Skip specific hooks
SKIP=vulture,mypy git commit -m "message"

# Skip all hooks (emergency only)
git commit --no-verify -m "emergency fix"
```

### Update hooks to latest versions
```bash
pre-commit autoupdate
```

### Check for unused dependencies
```bash
python scripts/check_unused_deps.py --verbose
```

### Security audit
```bash
# Python
pip-audit
safety check

# Node.js
npm audit
better-npm-audit audit
```

## Handling False Positives

### Vulture (dead code)
Add to `.vulture_whitelist.py`:
```python
_.false_positive_function
_.FalsePositiveClass
```

### Detect-secrets
Update baseline:
```bash
detect-secrets scan --baseline .secrets.baseline
```

### Unused dependencies
Edit `scripts/check_unused_deps.py` and add to `JUSTIFIED_UNUSED`:
```python
'package-name': "Reason for keeping this package"
```

## CI/CD Integration

GitHub Actions workflow runs automatically on:
- Every push to main/develop
- Every pull request
- Daily at 2 AM UTC (scheduled scan)

View results: Actions tab → Dependency and Security Check workflow

## Getting Help

- Run `./scripts/setup-hooks.sh` to reinstall
- Check `.pre-commit-config.yaml` for hook configuration
- Review `.github/workflows/dependency-check.yml` for CI settings
EOF

print_color $GREEN "✅ Quick reference saved to SECURITY_HOOKS_REFERENCE.md"

echo
print_color $GREEN "╔══════════════════════════════════════════════════════════════╗"
print_color $GREEN "║     ✅ Security Hooks Setup Complete!                       ║"
print_color $GREEN "╚══════════════════════════════════════════════════════════════╝"
echo

print_color $BLUE "📋 Next steps:"
echo "  1. Review SECURITY_HOOKS_REFERENCE.md for usage guide"
echo "  2. Run 'pre-commit run --all-files' to check existing code"
echo "  3. Commit your changes - hooks will run automatically"
echo "  4. Check GitHub Actions for CI/CD security scans"
echo

print_color $YELLOW "💡 Tips:"
echo "  • Hooks run automatically on 'git commit'"
echo "  • Use 'SKIP=hook_name git commit' to skip specific hooks"
echo "  • Run 'python scripts/check_unused_deps.py' to check dependencies"
echo "  • Update hooks with 'pre-commit autoupdate'"
echo

# Show current status
if command_exists detect-secrets; then
    print_color $GREEN "✅ detect-secrets installed"
fi

if command_exists vulture; then
    print_color $GREEN "✅ vulture installed"
fi

if command_exists bandit; then
    print_color $GREEN "✅ bandit installed"
fi

if command_exists safety; then
    print_color $GREEN "✅ safety installed"
fi

if command_exists pre-commit; then
    HOOKS_INSTALLED=$(pre-commit --version)
    print_color $GREEN "✅ pre-commit $HOOKS_INSTALLED"
fi

echo
print_color $BLUE "🚀 Ready for secure development!"