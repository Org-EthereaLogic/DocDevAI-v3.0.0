/**
 * Global Setup for DevDocAI Acceptance Tests
 * Ensures system is ready before running tests
 */

const axios = require('axios');
const { spawn } = require('child_process');
const { promisify } = require('util');
const sleep = promisify(setTimeout);

async function globalSetup() {
  console.log('🚀 DevDocAI Global Test Setup Starting...');

  // System health check with retries
  await waitForSystemReady();
  
  // Verify required modules are operational
  await validateModuleStatus();
  
  // Initialize test data if needed
  await initializeTestData();

  console.log('✅ DevDocAI Global Test Setup Complete');
}

async function waitForSystemReady(maxRetries = 30, delay = 2000) {
  console.log('⏳ Waiting for DevDocAI system to be ready...');
  
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      // Check frontend health
      const frontendResponse = await axios.get('http://localhost:3000/health', {
        timeout: 5000
      });
      
      if (frontendResponse.status === 200) {
        console.log('✅ Frontend system ready');
        break;
      }
    } catch (error) {
      if (attempt === maxRetries) {
        console.error('❌ Frontend system failed to start within timeout');
        
        // Try to start the development server
        console.log('🔄 Attempting to start development server...');
        await startDevelopmentServer();
        
        // Wait a bit more after starting
        await sleep(5000);
        
        try {
          await axios.get('http://localhost:3000/health', { timeout: 5000 });
          console.log('✅ Frontend system ready after restart');
        } catch (restartError) {
          throw new Error(`DevDocAI frontend not available after restart: ${restartError.message}`);
        }
      } else {
        console.log(`⏳ Attempt ${attempt}/${maxRetries} - Frontend not ready, retrying in ${delay/1000}s...`);
        await sleep(delay);
      }
    }
  }

  // Check API backend (may not exist yet, so don't fail)
  try {
    const apiResponse = await axios.get('http://localhost:8000/health', {
      timeout: 3000
    });
    
    if (apiResponse.status === 200) {
      console.log('✅ API backend ready');
    }
  } catch (error) {
    console.log('⚠️  API backend not available - tests will use fallback methods');
  }
}

async function startDevelopmentServer() {
  return new Promise((resolve, reject) => {
    console.log('🚀 Starting React development server...');
    
    const devServer = spawn('npm', ['run', 'dev:react'], {
      cwd: process.cwd(),
      stdio: 'pipe',
      detached: true
    });

    let output = '';
    let started = false;

    devServer.stdout.on('data', (data) => {
      output += data.toString();
      
      // Look for webpack dev server ready messages
      if (output.includes('webpack compiled') || 
          output.includes('Local:') || 
          output.includes('localhost:3000')) {
        if (!started) {
          started = true;
          console.log('✅ Development server started');
          resolve();
        }
      }
    });

    devServer.stderr.on('data', (data) => {
      const error = data.toString();
      
      // Ignore common webpack warnings
      if (!error.includes('WARNING') && 
          !error.includes('deprecated') && 
          !error.includes('punycode')) {
        console.warn('⚠️  Dev server stderr:', error);
      }
    });

    // Timeout after 60 seconds
    setTimeout(() => {
      if (!started) {
        console.warn('⚠️  Development server start timeout - proceeding anyway');
        resolve();
      }
    }, 60000);

    devServer.on('error', (error) => {
      console.error('❌ Failed to start development server:', error);
      reject(error);
    });

    // Don't wait for exit since dev server runs continuously
    devServer.unref();
  });
}

async function validateModuleStatus() {
  console.log('🔍 Validating module operational status...');
  
  try {
    // Try to get system status from API
    const response = await axios.get('http://localhost:8000/api/system/status', {
      timeout: 5000
    });
    
    const status = response.data;
    
    if (status.operationalModules < 11) {
      console.warn(`⚠️  Only ${status.operationalModules}/13 modules operational - some tests may be skipped`);
    } else {
      console.log(`✅ ${status.operationalModules}/13 modules operational`);
    }
    
  } catch (error) {
    console.log('⚠️  Module status validation skipped - API not available');
    console.log('   Tests will validate system status during execution');
  }
}

async function initializeTestData() {
  console.log('📝 Initializing test data...');
  
  // Create test project directory if needed
  const testProjectPath = '/tmp/devdocai-test-project';
  
  try {
    const fs = require('fs').promises;
    await fs.mkdir(testProjectPath, { recursive: true });
    
    // Create sample test files
    await fs.writeFile(`${testProjectPath}/README.md`, `
# Test Project

This is a test project for DevDocAI acceptance testing.

## Features

- Document generation testing
- Quality analysis validation
- Performance benchmarking

## API

\`\`\`javascript
function testFunction() {
  return "Hello DevDocAI!";
}
\`\`\`
`);

    await fs.writeFile(`${testProjectPath}/package.json`, JSON.stringify({
      name: 'devdocai-test-project',
      version: '1.0.0',
      description: 'Test project for DevDocAI acceptance testing',
      main: 'index.js',
      scripts: {
        test: 'echo "Test project"'
      },
      keywords: ['test', 'devdocai'],
      author: 'DevDocAI Test Suite'
    }, null, 2));

    await fs.writeFile(`${testProjectPath}/index.js`, `
/**
 * Test JavaScript file for DevDocAI testing
 */

function testFunction() {
  return "Hello DevDocAI!";
}

function calculateSum(a, b) {
  return a + b;
}

module.exports = {
  testFunction,
  calculateSum
};
`);

    console.log(`✅ Test data initialized at ${testProjectPath}`);
    
  } catch (error) {
    console.warn('⚠️  Test data initialization failed:', error.message);
    console.log('   Tests will create data as needed');
  }
}

// Environment validation
async function validateEnvironment() {
  console.log('🔧 Validating test environment...');
  
  const requiredEnvVars = [
    'NODE_ENV',
    'PORT'
  ];
  
  const missingVars = requiredEnvVars.filter(varName => !process.env[varName]);
  
  if (missingVars.length > 0) {
    console.warn(`⚠️  Missing environment variables: ${missingVars.join(', ')}`);
    console.log('   Setting default values...');
    
    process.env.NODE_ENV = process.env.NODE_ENV || 'test';
    process.env.PORT = process.env.PORT || '3000';
  }
  
  console.log(`✅ Environment: NODE_ENV=${process.env.NODE_ENV}, PORT=${process.env.PORT}`);
}

// Cleanup function for test isolation
async function cleanupFromPreviousRun() {
  console.log('🧹 Cleaning up from previous test runs...');
  
  try {
    const fs = require('fs').promises;
    const path = require('path');
    
    // Clean up test results directory
    const resultsDir = path.join(__dirname, '../results');
    try {
      await fs.rmdir(resultsDir, { recursive: true });
      await fs.mkdir(resultsDir, { recursive: true });
      console.log('✅ Test results directory cleaned');
    } catch (error) {
      // Directory might not exist, that's fine
      await fs.mkdir(resultsDir, { recursive: true });
    }
    
  } catch (error) {
    console.warn('⚠️  Cleanup warning:', error.message);
  }
}

// Export the main setup function
module.exports = async () => {
  await validateEnvironment();
  await cleanupFromPreviousRun();
  await globalSetup();
};