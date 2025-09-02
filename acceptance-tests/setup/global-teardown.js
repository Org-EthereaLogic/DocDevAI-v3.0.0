/**
 * Global Teardown for DevDocAI Acceptance Tests
 * Cleanup after test execution completes
 */

const fs = require('fs').promises;
const path = require('path');

async function globalTeardown() {
  console.log('🧹 DevDocAI Global Test Teardown Starting...');

  // Generate test summary report
  await generateTestSummaryReport();
  
  // Cleanup temporary test data
  await cleanupTestData();
  
  // Archive test results if needed
  await archiveTestResults();

  console.log('✅ DevDocAI Global Test Teardown Complete');
}

async function generateTestSummaryReport() {
  console.log('📊 Generating test summary report...');
  
  try {
    const resultsDir = path.join(__dirname, '../results');
    const resultsFile = path.join(resultsDir, 'test-results.json');
    
    // Check if test results exist
    let testResults = null;
    try {
      const resultsData = await fs.readFile(resultsFile, 'utf8');
      testResults = JSON.parse(resultsData);
    } catch (error) {
      console.log('⚠️  No test results file found - generating basic summary');
    }
    
    // Generate summary report
    const summaryReport = {
      timestamp: new Date().toISOString(),
      testSession: {
        startTime: testResults?.startTime || new Date().toISOString(),
        endTime: new Date().toISOString(),
        duration: testResults?.duration || 'unknown'
      },
      system: {
        version: 'DevDocAI v3.0.0',
        completion: '85%',
        operationalModules: 11,
        totalModules: 13
      },
      results: testResults?.suites || [],
      summary: {
        totalTests: testResults?.stats?.tests || 0,
        passed: testResults?.stats?.passes || 0,
        failed: testResults?.stats?.failures || 0,
        skipped: testResults?.stats?.skipped || 0,
        passRate: testResults?.stats?.tests > 0 
          ? Math.round((testResults.stats.passes / testResults.stats.tests) * 100) + '%'
          : '0%'
      },
      environment: {
        nodeVersion: process.version,
        platform: process.platform,
        testFramework: 'Playwright + Jest',
        baseUrl: 'http://localhost:3000'
      }
    };

    const summaryFile = path.join(resultsDir, 'test-summary.json');
    await fs.writeFile(summaryFile, JSON.stringify(summaryReport, null, 2));
    
    console.log('✅ Test summary report generated');
    console.log(`   Location: ${summaryFile}`);
    
    // Also create a human-readable summary
    const readableSummary = `
DevDocAI v3.0.0 Acceptance Test Summary
=====================================

Test Session: ${summaryReport.testSession.startTime}
Duration: ${summaryReport.testSession.duration}

System Status:
- Version: ${summaryReport.system.version}
- Completion: ${summaryReport.system.completion}
- Operational Modules: ${summaryReport.system.operationalModules}/${summaryReport.system.totalModules}

Test Results:
- Total Tests: ${summaryReport.summary.totalTests}
- Passed: ${summaryReport.summary.passed}
- Failed: ${summaryReport.summary.failed}
- Skipped: ${summaryReport.summary.skipped}
- Pass Rate: ${summaryReport.summary.passRate}

Environment:
- Node.js: ${summaryReport.environment.nodeVersion}
- Platform: ${summaryReport.environment.platform}
- Test Framework: ${summaryReport.environment.testFramework}
- Base URL: ${summaryReport.environment.baseUrl}

Generated: ${summaryReport.timestamp}
`;

    const readableFile = path.join(resultsDir, 'TEST_SUMMARY.txt');
    await fs.writeFile(readableFile, readableSummary);
    
    console.log('✅ Human-readable summary generated');
    console.log(`   Location: ${readableFile}`);
    
  } catch (error) {
    console.warn('⚠️  Test summary generation failed:', error.message);
  }
}

async function cleanupTestData() {
  console.log('🗑️  Cleaning up temporary test data...');
  
  try {
    // Remove test project directory
    const testProjectPath = '/tmp/devdocai-test-project';
    
    try {
      await fs.rmdir(testProjectPath, { recursive: true });
      console.log('✅ Test project directory cleaned');
    } catch (error) {
      if (error.code !== 'ENOENT') {
        console.warn(`⚠️  Could not clean test project: ${error.message}`);
      }
    }
    
    // Clean up any temporary files created during testing
    const tempFiles = [
      '/tmp/devdocai-test-export.pdf',
      '/tmp/devdocai-test-export.html',
      '/tmp/devdocai-test-cache',
      '/tmp/devdocai-test-logs'
    ];
    
    for (const tempFile of tempFiles) {
      try {
        await fs.unlink(tempFile);
        console.log(`✅ Cleaned temporary file: ${tempFile}`);
      } catch (error) {
        // File might not exist, that's fine
        if (error.code !== 'ENOENT') {
          console.warn(`⚠️  Could not clean ${tempFile}: ${error.message}`);
        }
      }
    }
    
  } catch (error) {
    console.warn('⚠️  Test data cleanup failed:', error.message);
  }
}

async function archiveTestResults() {
  console.log('📦 Archiving test results...');
  
  try {
    const resultsDir = path.join(__dirname, '../results');
    const archiveDir = path.join(__dirname, '../archive');
    
    // Create archive directory if it doesn't exist
    try {
      await fs.mkdir(archiveDir, { recursive: true });
    } catch (error) {
      // Directory might already exist
    }
    
    // Create timestamped archive directory
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const sessionArchiveDir = path.join(archiveDir, `test-session-${timestamp}`);
    
    try {
      await fs.mkdir(sessionArchiveDir, { recursive: true });
      
      // Copy results to archive
      const files = await fs.readdir(resultsDir);
      
      for (const file of files) {
        const srcPath = path.join(resultsDir, file);
        const destPath = path.join(sessionArchiveDir, file);
        
        try {
          const stats = await fs.stat(srcPath);
          if (stats.isFile()) {
            await fs.copyFile(srcPath, destPath);
          } else if (stats.isDirectory()) {
            // Recursively copy directories (like playwright-report)
            await copyDirectory(srcPath, destPath);
          }
        } catch (copyError) {
          console.warn(`⚠️  Could not archive ${file}: ${copyError.message}`);
        }
      }
      
      console.log('✅ Test results archived');
      console.log(`   Location: ${sessionArchiveDir}`);
      
      // Keep only last 10 test sessions to avoid disk space issues
      await cleanupOldArchives(archiveDir);
      
    } catch (error) {
      console.warn(`⚠️  Could not create archive directory: ${error.message}`);
    }
    
  } catch (error) {
    console.warn('⚠️  Test results archiving failed:', error.message);
  }
}

async function copyDirectory(src, dest) {
  await fs.mkdir(dest, { recursive: true });
  const files = await fs.readdir(src);
  
  for (const file of files) {
    const srcPath = path.join(src, file);
    const destPath = path.join(dest, file);
    const stats = await fs.stat(srcPath);
    
    if (stats.isDirectory()) {
      await copyDirectory(srcPath, destPath);
    } else {
      await fs.copyFile(srcPath, destPath);
    }
  }
}

async function cleanupOldArchives(archiveDir, keepCount = 10) {
  try {
    const archives = await fs.readdir(archiveDir);
    const archiveWithStats = [];
    
    for (const archive of archives) {
      const archivePath = path.join(archiveDir, archive);
      const stats = await fs.stat(archivePath);
      
      if (stats.isDirectory()) {
        archiveWithStats.push({
          name: archive,
          path: archivePath,
          mtime: stats.mtime
        });
      }
    }
    
    // Sort by modification time (newest first)
    archiveWithStats.sort((a, b) => b.mtime - a.mtime);
    
    // Remove archives beyond keepCount
    const archivesToRemove = archiveWithStats.slice(keepCount);
    
    for (const archive of archivesToRemove) {
      await fs.rmdir(archive.path, { recursive: true });
      console.log(`🗑️  Removed old archive: ${archive.name}`);
    }
    
    if (archivesToRemove.length > 0) {
      console.log(`✅ Cleaned up ${archivesToRemove.length} old archive(s)`);
    }
    
  } catch (error) {
    console.warn('⚠️  Old archive cleanup failed:', error.message);
  }
}

// Log final system state
async function logFinalSystemState() {
  console.log('📋 Final system state:');
  
  try {
    const axios = require('axios');
    
    // Check if system is still running
    const healthResponse = await axios.get('http://localhost:3000/health', {
      timeout: 3000
    });
    
    if (healthResponse.status === 200) {
      console.log('✅ DevDocAI system still running and healthy');
    }
    
  } catch (error) {
    console.log('ℹ️  DevDocAI system may have been shut down (normal after tests)');
  }
}

// Export the main teardown function
module.exports = async () => {
  await logFinalSystemState();
  await globalTeardown();
};