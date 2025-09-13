#!/usr/bin/env node

/**
 * Test Validation Script for DevDocAI Frontend
 * Validates testing infrastructure and generates comprehensive reports
 */

import { execSync } from 'child_process';
import { readFileSync, writeFileSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = join(__dirname, '..');

console.log('🧪 DevDocAI Frontend Test Validation\n');

// Validation Results
const results = {
  infrastructure: {},
  coverage: {},
  e2e: {},
  accessibility: {},
  performance: {},
  security: {},
  overall: { passed: 0, failed: 0, warnings: 0 }
};

/**
 * Execute command and capture output
 */
function executeCommand(command, options = {}) {
  try {
    const output = execSync(command, {
      cwd: projectRoot,
      encoding: 'utf8',
      stdio: 'pipe',
      ...options
    });
    return { success: true, output };
  } catch (error) {
    return { success: false, error: error.message, output: error.stdout };
  }
}

/**
 * Check if file exists
 */
function checkFile(filePath, description) {
  const fullPath = join(projectRoot, filePath);
  const exists = existsSync(fullPath);

  console.log(`${exists ? '✅' : '❌'} ${description}: ${filePath}`);

  if (exists) {
    results.overall.passed++;
  } else {
    results.overall.failed++;
  }

  return exists;
}

/**
 * Validate testing infrastructure
 */
function validateInfrastructure() {
  console.log('📋 Validating Testing Infrastructure\n');

  const checks = [
    ['package.json', 'Package configuration'],
    ['vite.config.js', 'Vite configuration'],
    ['playwright.config.js', 'Playwright configuration'],
    ['tests/setup.js', 'Test setup file'],
    ['tests/utils/testHelpers.js', 'Test utilities'],
    ['.github/workflows/frontend-testing.yml', 'CI/CD configuration'],
    ['TESTING.md', 'Testing documentation']
  ];

  checks.forEach(([file, description]) => {
    results.infrastructure[file] = checkFile(file, description);
  });

  // Check package.json test scripts
  try {
    const packageJson = JSON.parse(readFileSync(join(projectRoot, 'package.json'), 'utf8'));
    const requiredScripts = [
      'test', 'test:run', 'test:coverage', 'test:e2e', 'test:a11y', 'test:performance'
    ];

    console.log('\n📦 Test Scripts:');
    requiredScripts.forEach(script => {
      const exists = packageJson.scripts && packageJson.scripts[script];
      console.log(`${exists ? '✅' : '❌'} ${script}: ${exists ? packageJson.scripts[script] : 'Missing'}`);

      if (exists) {
        results.overall.passed++;
      } else {
        results.overall.failed++;
      }
    });

    // Check test dependencies
    console.log('\n📚 Test Dependencies:');
    const testDeps = [
      '@vue/test-utils', 'vitest', '@playwright/test', '@axe-core/playwright',
      '@vitest/coverage-v8', '@testing-library/vue', 'jsdom', 'happy-dom'
    ];

    testDeps.forEach(dep => {
      const exists = packageJson.devDependencies && packageJson.devDependencies[dep];
      console.log(`${exists ? '✅' : '❌'} ${dep}: ${exists ? packageJson.devDependencies[dep] : 'Missing'}`);

      if (exists) {
        results.overall.passed++;
      } else {
        results.overall.failed++;
      }
    });

  } catch (error) {
    console.log(`❌ Error reading package.json: ${error.message}`);
    results.overall.failed++;
  }
}

/**
 * Validate test files structure
 */
function validateTestStructure() {
  console.log('\n🏗️ Validating Test Structure\n');

  const testDirectories = [
    'tests/unit',
    'tests/unit/components',
    'tests/integration',
    'tests/e2e',
    'tests/utils'
  ];

  testDirectories.forEach(dir => {
    checkFile(dir, `Test directory: ${dir}`);
  });

  // Check for specific test files
  const testFiles = [
    'tests/unit/components/ReadmeForm.spec.js',
    'tests/unit/components/DocumentView.spec.js',
    'tests/integration/api-integration.spec.js',
    'tests/integration/store-integration.spec.js',
    'tests/e2e/document-generation.spec.js',
    'tests/e2e/accessibility.spec.js',
    'tests/e2e/performance.spec.js'
  ];

  console.log('\n📝 Test Files:');
  testFiles.forEach(file => {
    checkFile(file, `Test file: ${file}`);
  });
}

/**
 * Run unit tests and check coverage
 */
function validateUnitTests() {
  console.log('\n🧪 Running Unit Tests\n');

  const testResult = executeCommand('npm run test:run -- --reporter=verbose');

  if (testResult.success) {
    console.log('✅ Unit tests passed');
    results.overall.passed++;

    // Extract test count from output
    const testOutput = testResult.output;
    const testMatch = testOutput.match(/(\d+) passed/);
    if (testMatch) {
      results.coverage.testsRun = parseInt(testMatch[1]);
      console.log(`📊 Tests executed: ${results.coverage.testsRun}`);
    }
  } else {
    console.log('❌ Unit tests failed');
    console.log(testResult.error);
    results.overall.failed++;
  }

  // Run coverage analysis
  console.log('\n📊 Analyzing Test Coverage\n');

  const coverageResult = executeCommand('npm run test:coverage -- --reporter=json');

  if (coverageResult.success) {
    try {
      // Check if coverage report exists
      const coveragePath = join(projectRoot, 'coverage/coverage-summary.json');
      if (existsSync(coveragePath)) {
        const coverage = JSON.parse(readFileSync(coveragePath, 'utf8'));
        const total = coverage.total;

        console.log(`Lines: ${total.lines.pct}% (${total.lines.covered}/${total.lines.total})`);
        console.log(`Functions: ${total.functions.pct}% (${total.functions.covered}/${total.functions.total})`);
        console.log(`Branches: ${total.branches.pct}% (${total.branches.covered}/${total.branches.total})`);
        console.log(`Statements: ${total.statements.pct}% (${total.statements.covered}/${total.statements.total})`);

        results.coverage = {
          lines: total.lines.pct,
          functions: total.functions.pct,
          branches: total.branches.pct,
          statements: total.statements.pct
        };

        // Check if coverage meets thresholds (85%)
        const threshold = 85;
        const meetsThreshold =
          total.lines.pct >= threshold &&
          total.functions.pct >= threshold &&
          total.branches.pct >= threshold &&
          total.statements.pct >= threshold;

        if (meetsThreshold) {
          console.log('✅ Coverage thresholds met');
          results.overall.passed++;
        } else {
          console.log('⚠️ Coverage below 85% threshold');
          results.overall.warnings++;
        }
      } else {
        console.log('⚠️ Coverage report not found');
        results.overall.warnings++;
      }
    } catch (error) {
      console.log(`❌ Error reading coverage: ${error.message}`);
      results.overall.failed++;
    }
  } else {
    console.log('❌ Coverage analysis failed');
    results.overall.failed++;
  }
}

/**
 * Validate E2E testing setup
 */
function validateE2ESetup() {
  console.log('\n🎭 Validating E2E Testing Setup\n');

  // Check Playwright installation
  const playwrightCheck = executeCommand('npx playwright --version');

  if (playwrightCheck.success) {
    console.log('✅ Playwright installed');
    console.log(`Version: ${playwrightCheck.output.trim()}`);
    results.overall.passed++;
  } else {
    console.log('❌ Playwright not properly installed');
    results.overall.failed++;
  }

  // Check browser installation
  const browserCheck = executeCommand('npx playwright list-files', { timeout: 10000 });

  if (browserCheck.success) {
    console.log('✅ Playwright browsers available');
    results.overall.passed++;
  } else {
    console.log('⚠️ Playwright browsers may need installation');
    console.log('Run: npm run test:install');
    results.overall.warnings++;
  }

  // Validate E2E test files
  const e2eTests = [
    'tests/e2e/document-generation.spec.js',
    'tests/e2e/accessibility.spec.js',
    'tests/e2e/performance.spec.js'
  ];

  e2eTests.forEach(test => {
    if (existsSync(join(projectRoot, test))) {
      console.log(`✅ E2E test file: ${test}`);
      results.overall.passed++;
    } else {
      console.log(`❌ Missing E2E test: ${test}`);
      results.overall.failed++;
    }
  });
}

/**
 * Validate accessibility testing
 */
function validateAccessibilityTesting() {
  console.log('\n♿ Validating Accessibility Testing\n');

  // Check axe-core installation
  const axeCheck = executeCommand('node -e "require(\'@axe-core/playwright\')"');

  if (axeCheck.success) {
    console.log('✅ Axe-core Playwright integration available');
    results.overall.passed++;
  } else {
    console.log('❌ Axe-core Playwright integration missing');
    results.overall.failed++;
  }

  // Check accessibility test file
  if (existsSync(join(projectRoot, 'tests/e2e/accessibility.spec.js'))) {
    console.log('✅ Accessibility test suite available');
    results.overall.passed++;

    // Check test content for WCAG compliance
    try {
      const accessibilityTest = readFileSync(
        join(projectRoot, 'tests/e2e/accessibility.spec.js'),
        'utf8'
      );

      const wcagTests = [
        'wcag2a', 'wcag2aa', 'wcag21aa', 'color-contrast',
        'keyboard navigation', 'aria-label', 'screen reader'
      ];

      wcagTests.forEach(test => {
        if (accessibilityTest.includes(test) || accessibilityTest.toLowerCase().includes(test.toLowerCase())) {
          console.log(`✅ WCAG test coverage: ${test}`);
          results.overall.passed++;
        } else {
          console.log(`⚠️ Missing WCAG test: ${test}`);
          results.overall.warnings++;
        }
      });
    } catch (error) {
      console.log(`❌ Error reading accessibility tests: ${error.message}`);
      results.overall.failed++;
    }
  } else {
    console.log('❌ Accessibility test suite missing');
    results.overall.failed++;
  }
}

/**
 * Validate performance testing
 */
function validatePerformanceTesting() {
  console.log('\n⚡ Validating Performance Testing\n');

  // Check performance test file
  if (existsSync(join(projectRoot, 'tests/e2e/performance.spec.js'))) {
    console.log('✅ Performance test suite available');
    results.overall.passed++;

    try {
      const performanceTest = readFileSync(
        join(projectRoot, 'tests/e2e/performance.spec.js'),
        'utf8'
      );

      const coreWebVitals = [
        'First Contentful Paint', 'Largest Contentful Paint',
        'Cumulative Layout Shift', 'Core Web Vitals'
      ];

      coreWebVitals.forEach(metric => {
        if (performanceTest.includes(metric)) {
          console.log(`✅ Core Web Vitals test: ${metric}`);
          results.overall.passed++;
        } else {
          console.log(`⚠️ Missing performance test: ${metric}`);
          results.overall.warnings++;
        }
      });

      // Check for performance thresholds
      if (performanceTest.includes('toBeLessThan')) {
        console.log('✅ Performance thresholds defined');
        results.overall.passed++;
      } else {
        console.log('⚠️ Performance thresholds may be missing');
        results.overall.warnings++;
      }
    } catch (error) {
      console.log(`❌ Error reading performance tests: ${error.message}`);
      results.overall.failed++;
    }
  } else {
    console.log('❌ Performance test suite missing');
    results.overall.failed++;
  }
}

/**
 * Generate comprehensive report
 */
function generateReport() {
  console.log('\n📋 Test Validation Summary\n');

  const total = results.overall.passed + results.overall.failed + results.overall.warnings;
  const passRate = total > 0 ? Math.round((results.overall.passed / total) * 100) : 0;

  console.log(`Total Checks: ${total}`);
  console.log(`✅ Passed: ${results.overall.passed}`);
  console.log(`❌ Failed: ${results.overall.failed}`);
  console.log(`⚠️ Warnings: ${results.overall.warnings}`);
  console.log(`📊 Pass Rate: ${passRate}%\n`);

  // Coverage summary
  if (results.coverage.lines) {
    console.log('📊 Coverage Summary:');
    console.log(`Lines: ${results.coverage.lines}%`);
    console.log(`Functions: ${results.coverage.functions}%`);
    console.log(`Branches: ${results.coverage.branches}%`);
    console.log(`Statements: ${results.coverage.statements}%\n`);
  }

  // Recommendations
  console.log('💡 Recommendations:\n');

  if (results.overall.failed > 0) {
    console.log('❌ Critical Issues:');
    console.log('- Address failed checks before proceeding to production');
    console.log('- Ensure all required dependencies are installed');
    console.log('- Verify test files are properly configured\n');
  }

  if (results.overall.warnings > 0) {
    console.log('⚠️ Improvement Opportunities:');
    console.log('- Install missing browsers: npm run test:install');
    console.log('- Improve test coverage where below 85%');
    console.log('- Add missing WCAG compliance tests\n');
  }

  if (results.overall.failed === 0 && results.overall.warnings === 0) {
    console.log('🎉 Excellent! Testing infrastructure is fully configured and ready for production.\n');
  }

  // Save report to file
  const reportPath = join(projectRoot, 'test-validation-report.json');
  writeFileSync(reportPath, JSON.stringify(results, null, 2));
  console.log(`📄 Detailed report saved to: ${reportPath}\n`);

  // Generate markdown report
  const markdownReport = generateMarkdownReport();
  const markdownPath = join(projectRoot, 'TEST-VALIDATION-REPORT.md');
  writeFileSync(markdownPath, markdownReport);
  console.log(`📝 Markdown report saved to: ${markdownPath}\n`);

  // Exit with appropriate code
  process.exit(results.overall.failed > 0 ? 1 : 0);
}

/**
 * Generate markdown report
 */
function generateMarkdownReport() {
  const total = results.overall.passed + results.overall.failed + results.overall.warnings;
  const passRate = total > 0 ? Math.round((results.overall.passed / total) * 100) : 0;

  return `# DevDocAI Frontend Test Validation Report

Generated: ${new Date().toISOString()}

## Summary

| Metric | Value |
|--------|-------|
| Total Checks | ${total} |
| ✅ Passed | ${results.overall.passed} |
| ❌ Failed | ${results.overall.failed} |
| ⚠️ Warnings | ${results.overall.warnings} |
| Pass Rate | ${passRate}% |

## Infrastructure Validation

${Object.entries(results.infrastructure).map(([file, passed]) =>
  `- ${passed ? '✅' : '❌'} ${file}`
).join('\n')}

## Coverage Analysis

${results.coverage.lines ? `
| Coverage Type | Percentage |
|---------------|------------|
| Lines | ${results.coverage.lines}% |
| Functions | ${results.coverage.functions}% |
| Branches | ${results.coverage.branches}% |
| Statements | ${results.coverage.statements}% |
` : 'Coverage analysis not available'}

## Recommendations

${results.overall.failed > 0 ? `
### Critical Issues
- Address failed checks before proceeding to production
- Ensure all required dependencies are installed
- Verify test files are properly configured
` : ''}

${results.overall.warnings > 0 ? `
### Improvement Opportunities
- Install missing browsers: \`npm run test:install\`
- Improve test coverage where below 85%
- Add missing WCAG compliance tests
` : ''}

${results.overall.failed === 0 && results.overall.warnings === 0 ? `
### Status: Ready for Production ✅
Excellent! Testing infrastructure is fully configured and ready for production.
` : ''}

## Next Steps

1. Run the full test suite: \`npm run test:all\`
2. Check E2E tests: \`npm run test:e2e\`
3. Validate accessibility: \`npm run test:a11y\`
4. Monitor performance: \`npm run test:performance\`

---
Generated by DevDocAI Test Validation Script
`;
}

// Run validation
async function main() {
  try {
    validateInfrastructure();
    validateTestStructure();
    validateUnitTests();
    validateE2ESetup();
    validateAccessibilityTesting();
    validatePerformanceTesting();
    generateReport();
  } catch (error) {
    console.error('❌ Validation failed:', error.message);
    process.exit(1);
  }
}

main();
