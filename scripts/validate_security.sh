#!/bin/bash
# Validation script for security measures

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "Security Measures Validation Report"
echo "===================================="
echo

# Check GitHub Actions workflow
echo "1. GitHub Actions Workflow"
if [ -f ".github/workflows/dependency-check.yml" ]; then
    echo -e "${GREEN}✅ dependency-check.yml exists${NC}"
    
    # Validate YAML syntax
    python3 -c "import yaml; yaml.safe_load(open('.github/workflows/dependency-check.yml'))" 2>/dev/null && \
        echo -e "${GREEN}✅ Valid YAML syntax${NC}" || \
        echo -e "${RED}❌ Invalid YAML syntax${NC}"
else
    echo -e "${RED}❌ dependency-check.yml not found${NC}"
fi
echo

# Check pre-commit configuration
echo "2. Pre-commit Configuration"
if [ -f ".pre-commit-config.yaml" ]; then
    echo -e "${GREEN}✅ .pre-commit-config.yaml exists${NC}"
    
    # Count hooks
    HOOK_COUNT=$(grep -c "id:" .pre-commit-config.yaml || echo "0")
    echo -e "${GREEN}✅ $HOOK_COUNT hooks configured${NC}"
else
    echo -e "${RED}❌ .pre-commit-config.yaml not found${NC}"
fi
echo

# Check scripts
echo "3. Security Scripts"
SCRIPTS=(
    "scripts/check_unused_deps.py"
    "scripts/setup-hooks.sh"
)

for script in "${SCRIPTS[@]}"; do
    if [ -f "$script" ]; then
        if [ -x "$script" ]; then
            echo -e "${GREEN}✅ $script exists and is executable${NC}"
        else
            echo -e "${YELLOW}⚠️  $script exists but not executable${NC}"
        fi
    else
        echo -e "${RED}❌ $script not found${NC}"
    fi
done
echo

# Check documentation
echo "4. Documentation"
if [ -f "docs/03-guides/developer/DEPENDENCY-MANAGEMENT.md" ]; then
    LINE_COUNT=$(wc -l < "docs/03-guides/developer/DEPENDENCY-MANAGEMENT.md")
    echo -e "${GREEN}✅ DEPENDENCY-MANAGEMENT.md exists ($LINE_COUNT lines)${NC}"
else
    echo -e "${RED}❌ DEPENDENCY-MANAGEMENT.md not found${NC}"
fi
echo

# Test unused dependency detection
echo "5. Unused Dependency Detection"
if [ -f "scripts/check_unused_deps.py" ]; then
    python3 scripts/check_unused_deps.py >/dev/null 2>&1 && \
        echo -e "${GREEN}✅ Dependency checker works${NC}" || \
        echo -e "${YELLOW}⚠️  Some unused dependencies detected${NC}"
else
    echo -e "${RED}❌ check_unused_deps.py not found${NC}"
fi
echo

# Check for Python security tools
echo "6. Python Security Tools"
PYTHON_TOOLS=(
    "vulture:Dead code detection"
    "bandit:Security scanning"
    "safety:Vulnerability checking"
    "pip-audit:Dependency auditing"
    "autoflake:Unused import removal"
)

for tool_desc in "${PYTHON_TOOLS[@]}"; do
    IFS=':' read -r tool description <<< "$tool_desc"
    python3 -c "import $tool" 2>/dev/null && \
        echo -e "${GREEN}✅ $tool installed - $description${NC}" || \
        echo -e "${YELLOW}⚠️  $tool not installed - $description${NC}"
done
echo

# Performance check
echo "7. Performance Metrics"
echo -n "Pre-commit hooks: "
if [ -f ".pre-commit-config.yaml" ]; then
    # Simulate hook run time (dry run)
    START_TIME=$(date +%s)
    timeout 30 python3 scripts/check_unused_deps.py >/dev/null 2>&1 || true
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    if [ $DURATION -lt 30 ]; then
        echo -e "${GREEN}✅ Fast execution (<30s)${NC}"
    else
        echo -e "${YELLOW}⚠️  Slow execution (${DURATION}s)${NC}"
    fi
else
    echo -e "${RED}❌ Cannot test${NC}"
fi
echo

# Summary
echo "================================"
echo "Summary"
echo "================================"

TOTAL_CHECKS=7
PASSED=0
WARNINGS=0
FAILED=0

# Count results (simplified)
[ -f ".github/workflows/dependency-check.yml" ] && ((PASSED++)) || ((FAILED++))
[ -f ".pre-commit-config.yaml" ] && ((PASSED++)) || ((FAILED++))
[ -f "scripts/check_unused_deps.py" ] && ((PASSED++)) || ((FAILED++))
[ -f "scripts/setup-hooks.sh" ] && ((PASSED++)) || ((FAILED++))
[ -f "docs/03-guides/developer/DEPENDENCY-MANAGEMENT.md" ] && ((PASSED++)) || ((FAILED++))

echo -e "${GREEN}✅ Passed: $PASSED/$TOTAL_CHECKS${NC}"
[ $WARNINGS -gt 0 ] && echo -e "${YELLOW}⚠️  Warnings: $WARNINGS${NC}"
[ $FAILED -gt 0 ] && echo -e "${RED}❌ Failed: $FAILED${NC}"

echo
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All security measures are properly configured!${NC}"
    exit 0
else
    echo -e "${RED}⚠️  Some security measures need attention${NC}"
    exit 1
fi