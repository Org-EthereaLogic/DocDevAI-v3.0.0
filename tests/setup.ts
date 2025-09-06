/**
 * Jest Test Setup
 * Module 1: Core Infrastructure
 * 
 * Global test configuration and setup
 */

// Increase test timeout for CI environments
if (process.env.CI) {
  jest.setTimeout(30000);
}

// Mock console methods to reduce noise in tests
global.console = {
  ...console,
  // Uncomment to suppress console output during tests
  // log: jest.fn(),
  // debug: jest.fn(),
  // info: jest.fn(),
  // warn: jest.fn(),
  // error: jest.fn(),
};

// Add test utilities
(global as any).testUtils = {
  delay: (ms: number) => new Promise(resolve => setTimeout(resolve, ms))
};

// Clean up after all tests
afterAll(async () => {
  // Clean up any remaining resources
  jest.clearAllMocks();
  jest.clearAllTimers();
});