#!/bin/bash
# Real API Testing Script for DevDocAI v3.0.0
# This script runs integration tests with real API calls

set -e  # Exit on any error

echo "🚀 DevDocAI v3.0.0 - Real API Integration Testing"
echo "=================================================="

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found in project root"
    echo "Please create .env file with your API keys:"
    echo "  OPENAI_API_KEY=sk-your-key-here"
    echo "  ANTHROPIC_API_KEY=your-key-here"
    echo "  GOOGLE_API_KEY=your-key-here"
    exit 1
fi

echo "✅ Found .env file with API keys"

# Check if virtual environment is active
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: No virtual environment detected"
    echo "Recommended: source .venv/bin/activate"
    echo ""
fi

# Check if required dependencies are installed
echo "🔍 Checking dependencies..."
python -c "import devdocai.core.config, devdocai.intelligence.llm_adapter" 2>/dev/null || {
    echo "❌ Error: DevDocAI modules not found"
    echo "Run: pip install -e ."
    exit 1
}

echo "✅ Dependencies verified"
echo ""

# Option 1: Run all integration tests
echo "Choose testing mode:"
echo "1) Run ALL integration tests (recommended)"
echo "2) Run SPECIFIC provider tests"
echo "3) Run PERFORMANCE tests only"
echo "4) Run with VERBOSE output"
echo ""
read -p "Enter choice [1-4]: " choice

case $choice in
    1)
        echo "🧪 Running all integration tests..."
        REAL_API_TESTING=1 python -m pytest tests/integration/test_real_api.py -v
        ;;
    2)
        echo "Available provider tests:"
        echo "  - test_real_openai_api_call"
        echo "  - test_real_anthropic_api_call" 
        echo "  - test_real_google_api_call"
        echo ""
        read -p "Enter test name (or press Enter for all): " test_name
        
        if [ -z "$test_name" ]; then
            REAL_API_TESTING=1 python -m pytest tests/integration/test_real_api.py::TestRealAPIIntegration -v
        else
            REAL_API_TESTING=1 python -m pytest tests/integration/test_real_api.py::TestRealAPIIntegration::$test_name -v
        fi
        ;;
    3)
        echo "🏃 Running performance tests..."
        REAL_API_TESTING=1 python -m pytest tests/integration/test_real_api.py::TestRealAPIPerformance -v
        ;;
    4)
        echo "🔍 Running with verbose output and live logs..."
        REAL_API_TESTING=1 python -m pytest tests/integration/test_real_api.py -v -s --tb=short
        ;;
    *)
        echo "❌ Invalid choice. Running all tests..."
        REAL_API_TESTING=1 python -m pytest tests/integration/test_real_api.py -v
        ;;
esac

echo ""
echo "✅ Real API testing completed!"
echo ""
echo "💡 Tips:"
echo "  - Check output above for any failed API calls"
echo "  - Cost tracking information is displayed during tests"
echo "  - Rate limiting may cause some tests to be slower"
echo "  - Authentication errors indicate invalid API keys"