#!/usr/bin/env ts-node

/**
 * Module 1: Real-World Test Runner
 * 
 * Executes comprehensive real-world validation tests for Module 1
 */

import { execSync } from 'child_process';
import * as fs from 'fs-extra';
import * as path from 'path';
import * as chalk from 'chalk';

console.log(chalk.bold.cyan('\n╔════════════════════════════════════════════════════════════╗'));
console.log(chalk.bold.cyan('║     MODULE 1: CORE INFRASTRUCTURE - PASS 5 VALIDATION     ║'));
console.log(chalk.bold.cyan('╚════════════════════════════════════════════════════════════╝\n'));

interface TestSuite {
  name: string;
  file: string;
  description: string;
}

const testSuites: TestSuite[] = [
  {
    name: 'Real-World Scenarios',
    file: 'tests/real-world/module1-real-world.test.ts',
    description: 'Comprehensive usage scenarios and integration testing'
  },
  {
    name: 'Edge Cases & Stress',
    file: 'tests/real-world/edge-cases.test.ts',
    description: 'Extreme conditions, boundary cases, and attack scenarios'
  },
  {
    name: 'Performance Benchmarks',
    file: 'tests/real-world/performance-benchmark.test.ts',
    description: 'Performance validation under various load conditions'
  }
];

async function runTestSuite(suite: TestSuite): Promise<boolean> {
  console.log(chalk.bold.yellow(`\n▶ Running: ${suite.name}`));
  console.log(chalk.gray(`  ${suite.description}`));
  console.log(chalk.gray('─'.repeat(60)));

  try {
    // Check if test file exists
    const testPath = path.join(process.cwd(), suite.file);
    if (!await fs.pathExists(testPath)) {
      console.log(chalk.red(`  ✗ Test file not found: ${suite.file}`));
      return false;
    }

    // Run the test
    const command = `npx jest ${suite.file} --verbose --runInBand`;
    
    execSync(command, {
      stdio: 'inherit',
      env: {
        ...process.env,
        NODE_ENV: 'test',
        FORCE_COLOR: '1'
      }
    });

    console.log(chalk.green(`  ✓ ${suite.name} passed`));
    return true;

  } catch (error) {
    console.log(chalk.red(`  ✗ ${suite.name} failed`));
    if (error instanceof Error) {
      console.log(chalk.red(`    Error: ${error.message}`));
    }
    return false;
  }
}

async function generateReport(results: Map<string, boolean>) {
  console.log(chalk.bold.cyan('\n╔════════════════════════════════════════════════════════════╗'));
  console.log(chalk.bold.cyan('║                    TEST RESULTS SUMMARY                    ║'));
  console.log(chalk.bold.cyan('╚════════════════════════════════════════════════════════════╝\n'));

  let passed = 0;
  let failed = 0;

  results.forEach((success, name) => {
    if (success) {
      console.log(chalk.green(`  ✓ ${name}`));
      passed++;
    } else {
      console.log(chalk.red(`  ✗ ${name}`));
      failed++;
    }
  });

  console.log(chalk.gray('\n' + '─'.repeat(60)));
  
  const total = passed + failed;
  const percentage = (passed / total * 100).toFixed(1);
  
  console.log(chalk.bold(`\n  Total: ${total} test suites`));
  console.log(chalk.green(`  Passed: ${passed}`));
  console.log(chalk.red(`  Failed: ${failed}`));
  console.log(chalk.bold(`  Success Rate: ${percentage}%`));

  if (passed === total) {
    console.log(chalk.bold.green('\n🎉 ALL TESTS PASSED! Module 1 is production-ready!'));
    
    // Create validation report
    const report = {
      timestamp: new Date().toISOString(),
      module: 'M001-CoreInfrastructure',
      pass: 5,
      status: 'VALIDATED',
      results: {
        total: total,
        passed: passed,
        failed: failed,
        successRate: percentage
      },
      suites: Array.from(results.entries()).map(([name, success]) => ({
        name,
        status: success ? 'PASSED' : 'FAILED'
      })),
      conclusion: 'Module 1: Core Infrastructure has successfully completed Pass 5 Real-World Testing and is certified as production-ready.'
    };

    // Save report
    const reportPath = path.join(process.cwd(), 'MODULE_1_VALIDATION_REPORT.json');
    await fs.writeJSON(reportPath, report, { spaces: 2 });
    console.log(chalk.gray(`\n  Report saved to: ${reportPath}`));

  } else {
    console.log(chalk.bold.red('\n⚠️  Some tests failed. Please review and fix issues before certification.'));
  }
}

async function main() {
  console.log(chalk.gray('Starting real-world validation tests...'));
  console.log(chalk.gray(`Node version: ${process.version}`));
  console.log(chalk.gray(`Test environment: ${process.env.NODE_ENV || 'development'}`));
  console.log(chalk.gray(`Current directory: ${process.cwd()}\n`));

  const results = new Map<string, boolean>();

  // Run each test suite
  for (const suite of testSuites) {
    const success = await runTestSuite(suite);
    results.set(suite.name, success);
    
    // Add delay between suites
    if (testSuites.indexOf(suite) < testSuites.length - 1) {
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
  }

  // Generate final report
  await generateReport(results);

  // Exit with appropriate code
  const allPassed = Array.from(results.values()).every(v => v);
  process.exit(allPassed ? 0 : 1);
}

// Handle errors
process.on('unhandledRejection', (error) => {
  console.error(chalk.red('\n✗ Unhandled error:'), error);
  process.exit(1);
});

// Run tests
main().catch((error) => {
  console.error(chalk.red('\n✗ Test runner failed:'), error);
  process.exit(1);
});