/**
 * Playwright Configuration for DevDocAI v3.0.0 Acceptance Tests
 */

const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  // Test directory
  testDir: '../suites',
  
  // Test output directory
  outputDir: '../results/test-results',
  
  // Global test timeout
  timeout: 60000,
  
  // Expect timeout for assertions
  expect: {
    timeout: 10000
  },

  // Fulfill missing locator before timing out
  actionTimeout: 10000,
  
  // Navigation timeout
  navigationTimeout: 30000,
  
  // Global setup
  globalSetup: require.resolve('../setup/global-setup.js'),
  
  // Global teardown
  globalTeardown: require.resolve('../setup/global-teardown.js'),

  // Run tests in files in parallel
  fullyParallel: true,

  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,

  // Retry on CI only
  retries: process.env.CI ? 2 : 0,

  // Opt out of parallel tests on CI
  workers: process.env.CI ? 1 : undefined,

  // Reporter configuration
  reporter: [
    // Console reporter for local development
    ['list'],
    
    // JSON reporter for results processing
    ['json', { outputFile: '../results/test-results.json' }],
    
    // HTML reporter for detailed results
    ['html', { outputFolder: '../results/playwright-report', open: 'never' }],
    
    // JUnit reporter for CI integration
    ['junit', { outputFile: '../results/results.xml' }]
  ],

  // Shared settings for all the projects below
  use: {
    // Base URL for web tests
    baseURL: 'http://localhost:3000',

    // Collect trace when retrying the failed test
    trace: 'on-first-retry',

    // Take screenshot on failure
    screenshot: 'only-on-failure',

    // Capture video on failure
    video: 'retain-on-failure',
    
    // Browser context options
    ignoreHTTPSErrors: true,
    
    // Viewport size
    viewport: { width: 1280, height: 720 },
    
    // Extra HTTP headers
    extraHTTPHeaders: {
      'Accept': 'application/json',
      'User-Agent': 'DevDocAI-AcceptanceTest/1.0'
    }
  },

  // Configure projects for major browsers
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },

    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },

    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },

    // Test against mobile viewports
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },

    // Test against branded browsers
    {
      name: 'Microsoft Edge',
      use: { ...devices['Desktop Edge'], channel: 'msedge' },
    },
    
    {
      name: 'Google Chrome',
      use: { ...devices['Desktop Chrome'], channel: 'chrome' },
    },
  ],

  // Web server configuration for local testing
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
    stdout: 'ignore',
    stderr: 'pipe',
  },

  // Test environment setup
  testMatch: [
    '**/suites/**/*.test.js',
    '**/integration/**/*.test.js',
    '**/performance/**/*.test.js'
  ],

  // Global test configuration
  globalSetupTimeout: 120000,
  globalTeardownTimeout: 30000,

  // Test isolation
  testIdAttribute: 'data-testid',

  // API testing configuration
  apiTesting: {
    baseURL: 'http://localhost:8000',
    timeout: 30000,
    retries: 1
  }
});