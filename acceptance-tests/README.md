# DevDocAI v3.0.0 Acceptance Test Framework

Comprehensive acceptance testing framework for validating DevDocAI system integration and user story compliance.

## Overview

This framework provides end-to-end testing capabilities for the DevDocAI v3.0.0 system, which currently stands at **85% completion** with **11 of 13 modules operational**. The framework validates system readiness, user story compliance, module integration, and performance metrics.

## System Status

Based on live dashboard analysis:
- **Completion**: 85% (11/13 modules operational)
- **Operational Modules**: M001-M011 ✅
- **Pending Modules**: M012 (CLI), M013 (VS Code Extension) ⏳
- **Performance**: MIAIR 248K docs/min, Security A+, Storage 72K queries/sec
- **System Status**: Ready for production use

## Framework Architecture

```
acceptance-tests/
├── framework/           # Core testing framework
│   └── DevDocAITestFramework.js
├── interfaces/          # Module API interfaces
│   └── ModuleInterfaces.js
├── suites/             # Test suite implementations
│   └── user-stories.test.js
├── integration/        # Integration test cases
├── performance/        # Performance validation tests
├── config/            # Test configuration
│   └── playwright.config.js
├── setup/             # Global setup/teardown
│   ├── global-setup.js
│   └── global-teardown.js
├── scripts/           # Test execution scripts
│   └── run-acceptance-tests.js
└── results/           # Test execution results
```

## Test Categories

### 1. User Story Validation
Tests key user stories from the requirements specification:

- **US-001**: Document Generation - Auto-generate comprehensive docs
- **US-002**: Quality Analysis - Intelligent quality scoring  
- **US-003**: Template-Based Docs - Customizable template system
- **US-004**: Multi-Format Export - Markdown, HTML, PDF output
- **US-005**: Real-Time Updates - Auto-sync with code changes
- **US-009**: Performance Optimization - MIAIR engine efficiency
- **US-010**: Privacy-First Storage - Local encrypted storage
- **US-015**: Security Features - PII detection, threat scanning

### 2. System Integration
Validates module interconnectivity:

- **M004 ↔ M006**: Document Generator ↔ Template Registry
- **M003 ↔ M008**: MIAIR Engine ↔ LLM Adapter  
- **M005 ↔ M007**: Quality Engine ↔ Review Engine
- **M002 ↔ Security**: Local Storage ↔ Security Module

### 3. Performance Validation
Confirms system meets performance targets:

- **MIAIR Engine**: ≥248K docs/min processing
- **Local Storage**: ≥72K queries/sec throughput
- **Security Grade**: A+ security rating
- **API Response**: <2s simple, <10s complex requests

## Quick Start

### Prerequisites
- Node.js 18+ 
- DevDocAI v3.0.0 system running at `http://localhost:3000`
- Optional: API backend at `http://localhost:8000`

### Installation
```bash
cd acceptance-tests/
npm install
npx playwright install
```

### Running Tests

#### Complete Test Suite
```bash
# Run full acceptance test suite
node scripts/run-acceptance-tests.js

# Alternative: Use npm script
npm test
```

#### Individual Test Suites
```bash
# User story validation only
npm run test:user-stories

# Integration tests only  
npm run test:integration

# Performance tests only
npm run test:performance
```

#### Development Testing
```bash
# Run with browser UI (for debugging)
npm run test:ui

# Run in headed mode
npm run test:headed

# Run specific browser
npm run test:quick  # Chromium only
```

## Test Configuration

### Playwright Configuration
Located in `config/playwright.config.js`:
- **Browsers**: Chromium, Firefox, WebKit, Mobile Chrome/Safari
- **Timeouts**: 60s test, 30s navigation, 10s action
- **Reporters**: Console, JSON, HTML, JUnit
- **Web Server**: Auto-starts `npm run dev` if needed

### Environment Variables
```bash
# Required for system connection
BASE_URL=http://localhost:3000      # Frontend URL
API_URL=http://localhost:8000       # Backend API URL (optional)
NODE_ENV=test                       # Test environment

# Optional performance tuning  
PLAYWRIGHT_WORKERS=1                # Parallel worker count
PLAYWRIGHT_RETRIES=2                # Retry failed tests
```

## Framework Usage

### Basic Test Framework
```javascript
const { DevDocAITestFramework } = require('./framework/DevDocAITestFramework');

// Initialize framework
const framework = new DevDocAITestFramework();
await framework.initialize();

// Validate system readiness
const readiness = await framework.validateSystemReadiness();
console.log(`System ${readiness.ready ? 'ready' : 'not ready'}: ${readiness.completion}%`);

// Run user story tests
const us001 = await framework.validateUserStory001_DocumentGeneration();
const us002 = await framework.validateUserStory002_QualityAnalysis();

// Validate module integration
const integrations = await framework.validateModuleIntegration();
```

### Module Interfaces
```javascript
const { ModuleInterfaceFactory } = require('./interfaces/ModuleInterfaces');

// Create specific module interface
const m001 = ModuleInterfaceFactory.create('M001-ConfigManager');
const config = await m001.loadConfiguration();

// Create all module interfaces
const interfaces = ModuleInterfaceFactory.createAll();
const storageStats = await interfaces['M002-LocalStorage'].getStorageStats();
```

## Test Results

### Result Locations
- **JSON Results**: `results/acceptance-test-results.json`
- **HTML Report**: `results/playwright-report/index.html`  
- **Text Summary**: `results/ACCEPTANCE_TEST_SUMMARY.txt`
- **Archives**: `archive/test-session-YYYY-MM-DD/`

### Result Analysis
```bash
# View HTML report
npm run test:report

# Check latest results
cat results/ACCEPTANCE_TEST_SUMMARY.txt

# View detailed JSON
jq '.summary' results/acceptance-test-results.json
```

## Expected Results

Based on current system status (85% complete):

### ✅ Expected to Pass
- System readiness validation (85% completion)
- Core user stories (US-001, US-002, US-009, US-010)
- Module integration for operational modules (M001-M011)
- Performance metrics validation
- Security features testing

### ⚠️ Expected to Skip/Warn
- CLI interface tests (M012 not implemented)
- VS Code extension tests (M013 not implemented)  
- Real-time watch functionality (US-005)
- Multi-format export (US-004) - may be partial

### 🎯 Success Criteria
- **Pass Rate**: ≥80% (allowing for unimplemented features)
- **System Ready**: ✅ True
- **Core Features**: All operational modules working
- **Integration**: Key module pairs connected
- **Performance**: Meets dashboard metrics

## Troubleshooting

### Common Issues

**System Not Running**
```bash
# Framework will auto-start development server
npm run dev:react

# Or manually start in background
npm run dev:react &
```

**API Backend Missing**
```
⚠️ API backend not available - tests will use fallback methods
```
This is expected - tests gracefully fallback to UI scraping.

**Port Conflicts**
```bash
# Check ports
lsof -i :3000 -i :8000

# Kill existing processes
pkill -f "webpack-dev-server"
```

**Playwright Install Issues**
```bash
# Reinstall browsers
npx playwright install --with-deps

# Or specific browser
npx playwright install chromium
```

### Debug Mode
```bash
# Run with debug output
DEBUG=pw:test npm test

# Step through tests
npm run test:debug

# Inspect specific test
npx playwright test --debug suites/user-stories.test.js
```

## Development

### Adding New Tests
```javascript
// 1. Add to user-stories.test.js
test('US-XXX: New User Story', async () => {
  const result = await testFramework.validateUserStoryXXX();
  expect(result.status).toBe('PASSED');
});

// 2. Implement in DevDocAITestFramework.js
async validateUserStoryXXX() {
  // Test implementation
  return { story: 'US-XXX', status: 'PASSED', details: '...' };
}
```

### Adding Module Interfaces
```javascript
// Add to ModuleInterfaces.js
class M012CLIInterface extends ModuleInterface {
  constructor() {
    super('M012-CLI');
  }
  
  async runCommand(command) {
    // Implementation
  }
}
```

## Integration with CI/CD

### GitHub Actions
```yaml
- name: Run Acceptance Tests
  run: |
    cd acceptance-tests
    npm install
    npx playwright install --with-deps
    node scripts/run-acceptance-tests.js
    
- name: Upload Test Results  
  uses: actions/upload-artifact@v3
  with:
    name: acceptance-test-results
    path: acceptance-tests/results/
```

### Results Integration
- **JSON output**: Compatible with test reporting tools
- **JUnit XML**: Standard CI/CD format
- **HTML reports**: Human-readable results
- **Exit codes**: 0 = pass, 1 = fail

## Next Steps

As M012 and M013 modules are completed:

1. **Update module interfaces** in `interfaces/ModuleInterfaces.js`
2. **Add CLI tests** for M012 command-line operations
3. **Add VS Code tests** for M013 extension functionality  
4. **Update system completion** target from 85% to 100%
5. **Enable full feature validation** for US-004, US-005

The framework is designed to automatically adapt as new modules come online, requiring minimal configuration changes.