#!/bin/bash
# DevDocAI v3.0.0 - Development Environment Setup
# Run with: bash setup-dev.sh

set -e

echo "🚀 DevDocAI v3.0.0 - Development Environment Setup"
echo "=================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo "1. Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then 
    echo -e "${RED}❌ Python $PYTHON_VERSION is too old. Minimum required: $REQUIRED_VERSION${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Python $PYTHON_VERSION detected${NC}"

# Create virtual environment
echo ""
echo "2. Creating virtual environment..."
if [ -d "venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment already exists. Skipping...${NC}"
else
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created${NC}"
fi

# Activate virtual environment
echo ""
echo "3. Activating virtual environment..."
source venv/bin/activate
echo -e "${GREEN}✅ Virtual environment activated${NC}"

# Upgrade pip
echo ""
echo "4. Upgrading pip..."
pip install --upgrade pip setuptools wheel
echo -e "${GREEN}✅ pip upgraded${NC}"

# Install dependencies
echo ""
echo "5. Installing core dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo -e "${GREEN}✅ Core dependencies installed${NC}"
else
    echo -e "${YELLOW}⚠️  requirements.txt not found. Installing from pyproject.toml...${NC}"
    pip install -e .
fi

echo ""
echo "6. Installing development dependencies..."
if [ -f "requirements-dev.txt" ]; then
    pip install -r requirements-dev.txt
    echo -e "${GREEN}✅ Development dependencies installed${NC}"
else
    echo -e "${YELLOW}⚠️  requirements-dev.txt not found. Installing dev extras...${NC}"
    pip install -e ".[dev]"
fi

# Install pre-commit hooks
echo ""
echo "7. Setting up pre-commit hooks..."
if command -v pre-commit &> /dev/null; then
    pre-commit install
    echo -e "${GREEN}✅ Pre-commit hooks installed${NC}"
else
    echo -e "${YELLOW}⚠️  pre-commit not installed. Skipping...${NC}"
fi

# Create necessary directories
echo ""
echo "8. Creating project structure..."
mkdir -p devdocai/{core,intelligence,compliance,operations,templates,utils}
mkdir -p tests/{unit,integration,performance,security}/{core,intelligence,compliance,operations}
mkdir -p docs/{api,user,developer}
mkdir -p scripts
mkdir -p .devdocai  # For local configuration
echo -e "${GREEN}✅ Project structure created${NC}"

# Detect memory mode
echo ""
echo "9. Detecting system memory mode..."
TOTAL_RAM=$(free -m | awk '/^Mem:/{print $2}')
MEMORY_MODE="UNKNOWN"

if [ "$TOTAL_RAM" -lt 2048 ]; then
    MEMORY_MODE="BASELINE (<2GB)"
elif [ "$TOTAL_RAM" -lt 4096 ]; then
    MEMORY_MODE="STANDARD (2-4GB)"
elif [ "$TOTAL_RAM" -lt 8192 ]; then
    MEMORY_MODE="ENHANCED (4-8GB)"
else
    MEMORY_MODE="PERFORMANCE (>8GB)"
fi

echo -e "${GREEN}✅ System RAM: ${TOTAL_RAM}MB - Memory Mode: $MEMORY_MODE${NC}"

# Create default configuration
echo ""
echo "10. Creating default configuration..."
cat > .devdocai/config.yaml << EOF
# DevDocAI v3.0.0 Configuration
# Auto-generated on $(date)

# System settings
system:
  memory_mode: auto  # auto, baseline, standard, enhanced, performance
  detected_mode: ${MEMORY_MODE}
  
# Privacy settings (privacy-first defaults)
privacy:
  telemetry: false  # Opt-in only
  analytics: false
  local_only: true
  
# Security settings
security:
  encryption_enabled: true
  encryption_algorithm: AES-256-GCM
  key_derivation: argon2id
  
# Development settings
development:
  debug: true
  verbose: true
  
# Quality gates
quality:
  min_coverage: 95  # M001 requirement
  max_complexity: 10
  quality_threshold: 85  # Documentation quality gate
EOF
echo -e "${GREEN}✅ Default configuration created${NC}"

# Run initial tests
echo ""
echo "11. Running initial tests..."
echo -e "${YELLOW}Creating minimal test to verify setup...${NC}"

# Create a minimal test file
cat > tests/test_setup.py << EOF
"""Minimal test to verify environment setup."""

def test_import():
    """Test that devdocai package can be imported."""
    import devdocai
    assert devdocai.__version__ == "3.0.0"
    
def test_python_version():
    """Test Python version requirement."""
    import sys
    assert sys.version_info >= (3, 8)
EOF

# Run the test
if pytest tests/test_setup.py -v; then
    echo -e "${GREEN}✅ Initial tests passed${NC}"
else
    echo -e "${YELLOW}⚠️  Some tests failed. This is expected for initial setup.${NC}"
fi

# Display summary
echo ""
echo "=================================================="
echo -e "${GREEN}🎉 Development environment setup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Start M001 implementation: See docs/implementation-roadmap.md"
echo "3. Run tests: pytest"
echo "4. Check code quality: black devdocai && ruff check devdocai"
echo ""
echo "Memory Mode: $MEMORY_MODE"
echo "Python Version: $PYTHON_VERSION"
echo "Configuration: .devdocai/config.yaml"
echo ""
echo "Happy coding! 🚀"