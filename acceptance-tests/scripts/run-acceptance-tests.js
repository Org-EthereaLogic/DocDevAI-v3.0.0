#!/usr/bin/env node

/**
 * DevDocAI Acceptance Test Runner
 * Orchestrates the complete acceptance test suite execution
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs').promises;

class AcceptanceTestRunner {
  constructor() {
    this.testResults = {
      startTime: new Date().toISOString(),
      endTime: null,
      duration: null,
      suites: [],
      summary: {
        total: 0,
        passed: 0,
        failed: 0,
        skipped: 0
      },
      system: {
        readiness: null,
        performance: null,
        integration: null
      }
    };
  }

  async run() {
    console.log('🎯 DevDocAI Acceptance Test Suite Starting...\n');

    try {
      // Step 1: System validation
      await this.validateSystemReadiness();
      
      // Step 2: Run test suites
      await this.runTestSuites();
      
      // Step 3: Generate final report
      await this.generateFinalReport();

      console.log('\n✅ DevDocAI Acceptance Test Suite Complete!');
      
      return this.testResults.summary.failed === 0;
      
    } catch (error) {
      console.error('\n❌ DevDocAI Acceptance Test Suite Failed:', error.message);
      return false;
    }
  }

  async validateSystemReadiness() {
    console.log('🔍 Step 1: Validating System Readiness...');
    
    try {
      const { DevDocAITestFramework } = require('../framework/DevDocAITestFramework');
      const framework = new DevDocAITestFramework();
      
      await framework.initialize();
      const readiness = await framework.validateSystemReadiness();
      
      this.testResults.system.readiness = readiness;
      
      console.log(`   ✅ System Ready: ${readiness.completion}% complete`);
      console.log(`   ✅ Operational Modules: ${readiness.operational}/13`);
      
      if (readiness.completion < 85) {
        throw new Error(`System completion ${readiness.completion}% below required 85%`);
      }
      
    } catch (error) {
      console.error(`   ❌ System readiness failed: ${error.message}`);
      throw error;
    }
  }

  async runTestSuites() {
    console.log('\n🧪 Step 2: Running Test Suites...');
    
    const testSuites = [
      {
        name: 'User Stories',
        command: 'npx',
        args: ['playwright', 'test', 'suites/user-stories.test.js', '--reporter=json'],
        critical: true
      },
      {
        name: 'System Integration',
        command: 'npx', 
        args: ['playwright', 'test', 'integration/', '--reporter=json'],
        critical: false
      },
      {
        name: 'Performance Validation',
        command: 'npx',
        args: ['playwright', 'test', 'performance/', '--reporter=json'],
        critical: false
      }
    ];

    for (const suite of testSuites) {
      console.log(`\n   🔄 Running ${suite.name} Tests...`);
      
      try {
        const result = await this.runPlaywrightSuite(suite);
        
        this.testResults.suites.push({
          name: suite.name,
          status: result.failed === 0 ? 'PASSED' : 'FAILED',
          total: result.total,
          passed: result.passed,
          failed: result.failed,
          duration: result.duration
        });

        this.testResults.summary.total += result.total;
        this.testResults.summary.passed += result.passed;
        this.testResults.summary.failed += result.failed;

        if (result.failed === 0) {
          console.log(`   ✅ ${suite.name}: ${result.passed}/${result.total} tests passed`);
        } else {
          console.log(`   ❌ ${suite.name}: ${result.failed}/${result.total} tests failed`);
          
          if (suite.critical) {
            throw new Error(`Critical test suite '${suite.name}' failed`);
          }
        }
        
      } catch (error) {
        console.error(`   ❌ ${suite.name} execution failed: ${error.message}`);
        
        this.testResults.suites.push({
          name: suite.name,
          status: 'ERROR',
          error: error.message
        });

        if (suite.critical) {
          throw error;
        }
      }
    }
  }

  async runPlaywrightSuite(suite) {
    return new Promise((resolve, reject) => {
      const startTime = Date.now();
      
      const process = spawn(suite.command, suite.args, {
        cwd: path.resolve(__dirname, '..'),
        stdio: ['ignore', 'pipe', 'pipe']
      });

      let stdout = '';
      let stderr = '';

      process.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      process.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      process.on('close', (code) => {
        const duration = Date.now() - startTime;
        
        try {
          // Parse Playwright JSON output
          const lines = stdout.split('\n').filter(line => line.trim());
          let results = null;
          
          // Find JSON results in output
          for (const line of lines) {
            try {
              const parsed = JSON.parse(line);
              if (parsed.stats) {
                results = parsed;
                break;
              }
            } catch (e) {
              // Not JSON, continue
            }
          }

          if (results && results.stats) {
            resolve({
              total: results.stats.total || 0,
              passed: results.stats.expected || 0,
              failed: results.stats.unexpected || 0,
              skipped: results.stats.skipped || 0,
              duration: `${duration}ms`
            });
          } else {
            // Fallback parsing from exit code
            resolve({
              total: code === 0 ? 1 : 1,
              passed: code === 0 ? 1 : 0,
              failed: code === 0 ? 0 : 1,
              skipped: 0,
              duration: `${duration}ms`
            });
          }
          
        } catch (parseError) {
          reject(new Error(`Failed to parse test results: ${parseError.message}`));
        }
      });

      process.on('error', (error) => {
        reject(new Error(`Failed to run ${suite.command}: ${error.message}`));
      });
    });
  }

  async generateFinalReport() {
    console.log('\n📊 Step 3: Generating Final Report...');
    
    this.testResults.endTime = new Date().toISOString();
    this.testResults.duration = this.calculateDuration(
      this.testResults.startTime,
      this.testResults.endTime
    );

    // Calculate pass rate
    const passRate = this.testResults.summary.total > 0
      ? Math.round((this.testResults.summary.passed / this.testResults.summary.total) * 100)
      : 0;

    // Create results directory
    const resultsDir = path.resolve(__dirname, '../results');
    await fs.mkdir(resultsDir, { recursive: true });

    // Write detailed results
    const resultsFile = path.join(resultsDir, 'acceptance-test-results.json');
    await fs.writeFile(resultsFile, JSON.stringify(this.testResults, null, 2));

    // Create summary report
    const summaryReport = `
DevDocAI v3.0.0 Acceptance Test Results
======================================

Test Session: ${this.testResults.startTime}
Duration: ${this.testResults.duration}

System Status:
- Readiness: ${this.testResults.system.readiness?.ready ? 'READY' : 'NOT READY'}
- Completion: ${this.testResults.system.readiness?.completion}%
- Operational Modules: ${this.testResults.system.readiness?.operational}/13

Test Results Summary:
- Total Tests: ${this.testResults.summary.total}
- Passed: ${this.testResults.summary.passed}
- Failed: ${this.testResults.summary.failed}
- Skipped: ${this.testResults.summary.skipped}
- Pass Rate: ${passRate}%

Test Suites:
${this.testResults.suites.map(suite => 
  `- ${suite.name}: ${suite.status} (${suite.passed || 0}/${suite.total || 0})`
).join('\n')}

Overall Status: ${this.testResults.summary.failed === 0 ? '✅ PASSED' : '❌ FAILED'}

Generated: ${new Date().toISOString()}
`;

    const summaryFile = path.join(resultsDir, 'ACCEPTANCE_TEST_SUMMARY.txt');
    await fs.writeFile(summaryFile, summaryReport);

    console.log(`   📁 Results saved to: ${resultsFile}`);
    console.log(`   📄 Summary saved to: ${summaryFile}`);
    
    // Print summary to console
    console.log('\n' + '='.repeat(50));
    console.log('FINAL ACCEPTANCE TEST RESULTS');
    console.log('='.repeat(50));
    console.log(`Status: ${this.testResults.summary.failed === 0 ? '✅ PASSED' : '❌ FAILED'}`);
    console.log(`Total: ${this.testResults.summary.total} | Passed: ${this.testResults.summary.passed} | Failed: ${this.testResults.summary.failed}`);
    console.log(`Pass Rate: ${passRate}%`);
    console.log(`Duration: ${this.testResults.duration}`);
    console.log('='.repeat(50));
  }

  calculateDuration(startTime, endTime) {
    const start = new Date(startTime);
    const end = new Date(endTime);
    const durationMs = end - start;
    
    const minutes = Math.floor(durationMs / 60000);
    const seconds = Math.floor((durationMs % 60000) / 1000);
    
    return `${minutes}m ${seconds}s`;
  }
}

// CLI execution
async function main() {
  const runner = new AcceptanceTestRunner();
  const success = await runner.run();
  
  process.exit(success ? 0 : 1);
}

// Run if called directly
if (require.main === module) {
  main().catch(error => {
    console.error('Fatal error:', error);
    process.exit(1);
  });
}

module.exports = { AcceptanceTestRunner };