import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright Configuration for DevDocAI Frontend E2E Testing
 * Comprehensive cross-browser testing with accessibility and performance monitoring
 */
export default defineConfig({
  // Test directory
  testDir: './tests/e2e',

  // Global test timeout
  timeout: 30 * 1000,
  expect: {
    timeout: 5000
  },

  // Test configuration
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,

  // Test reporting
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'test-results.json' }],
    ['junit', { outputFile: 'junit-results.xml' }]
  ],

  // Global test setup
  use: {
    // Base URL for testing
    baseURL: 'http://localhost:5173',

    // Browser context options
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',

    // Viewport settings
    viewport: { width: 1280, height: 720 },

    // Device emulation
    userAgent: 'DevDocAI-Test-Agent/1.0',

    // Performance and accessibility
    actionTimeout: 10000,
    navigationTimeout: 15000
  },

  // Test projects for different browsers and scenarios
  projects: [
    // Desktop browsers
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      testMatch: /.*\.(test|spec)\.js$/
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
      testMatch: /.*\.(test|spec)\.js$/
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
      testMatch: /.*\.(test|spec)\.js$/
    },

    // Mobile browsers
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
      testMatch: /mobile\.(test|spec)\.js$/
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
      testMatch: /mobile\.(test|spec)\.js$/
    },

    // Accessibility testing
    {
      name: 'accessibility',
      use: { ...devices['Desktop Chrome'] },
      testMatch: /accessibility\.(test|spec)\.js$/
    },

    // Performance testing
    {
      name: 'performance',
      use: {
        ...devices['Desktop Chrome'],
        // Slower network for performance testing
        launchOptions: {
          args: ['--disable-web-security', '--disable-features=VizDisplayCompositor']
        }
      },
      testMatch: /performance\.(test|spec)\.js$/
    }
  ],

  // Development server
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000
  }
});
