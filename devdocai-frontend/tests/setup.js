/**
 * Test setup for DevDocAI frontend
 * Configures the testing environment for Vue 3 components
 */

import { config } from '@vue/test-utils';
import { createPinia } from 'pinia';
import { vi } from 'vitest';

// Setup Pinia for testing
const pinia = createPinia();

// Configure Vue Test Utils
config.global.plugins = [pinia];

// Mock commonly used composables
config.global.mocks = {
  $t: (key) => key, // Mock i18n translations
  $route: {
    path: '/',
    params: {},
    query: {}
  },
  $router: {
    push: vi.fn(),
    back: vi.fn(),
    replace: vi.fn()
  }
};

// Mock window methods
global.alert = vi.fn();
global.confirm = vi.fn(() => true);
global.prompt = vi.fn();

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn()
};
global.localStorage = localStorageMock;

// Mock sessionStorage
const sessionStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn()
};
global.sessionStorage = sessionStorageMock;

// Mock fetch API
global.fetch = vi.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({}),
    text: () => Promise.resolve(''),
    blob: () => Promise.resolve(new Blob()),
    headers: new Headers()
  })
);

// Mock IntersectionObserver
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn()
}));

// Mock ResizeObserver
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn()
}));

// Mock performance API
global.performance = {
  now: vi.fn(() => Date.now()),
  mark: vi.fn(),
  measure: vi.fn(),
  clearMarks: vi.fn(),
  clearMeasures: vi.fn(),
  getEntriesByName: vi.fn(() => []),
  getEntriesByType: vi.fn(() => [])
};

// Mock console methods for cleaner test output
const originalConsoleError = console.error;
const originalConsoleWarn = console.warn;

console.error = (...args) => {
  // Filter out expected Vue warnings
  const message = args[0]?.toString() || '';
  if (
    message.includes('Failed to resolve component') ||
    message.includes('Invalid prop') ||
    message.includes('Missing required prop')
  ) {
    return;
  }
  originalConsoleError(...args);
};

console.warn = (...args) => {
  // Filter out expected warnings
  const message = args[0]?.toString() || '';
  if (
    message.includes('Experimental') ||
    message.includes('DevTools')
  ) {
    return;
  }
  originalConsoleWarn(...args);
};

// Custom matchers
expect.extend({
  toBeWithinRange(received, floor, ceiling) {
    const pass = received >= floor && received <= ceiling;
    if (pass) {
      return {
        message: () => `expected ${received} not to be within range ${floor} - ${ceiling}`,
        pass: true
      };
    } else {
      return {
        message: () => `expected ${received} to be within range ${floor} - ${ceiling}`,
        pass: false
      };
    }
  },

  toHaveBeenCalledWithError(received, expectedError) {
    const calls = received.mock.calls;
    const pass = calls.some(call => {
      const error = call[0];
      return error?.message === expectedError || error === expectedError;
    });

    if (pass) {
      return {
        message: () => `expected function not to have been called with error "${expectedError}"`,
        pass: true
      };
    } else {
      return {
        message: () => `expected function to have been called with error "${expectedError}"`,
        pass: false
      };
    }
  },

  toBeValidationError(received, field) {
    const pass = received?.field === field && received?.type === 'validation';
    if (pass) {
      return {
        message: () => `expected ${JSON.stringify(received)} not to be a validation error for field "${field}"`,
        pass: true
      };
    } else {
      return {
        message: () => `expected ${JSON.stringify(received)} to be a validation error for field "${field}"`,
        pass: false
      };
    }
  }
});

// Test utilities
export const nextTick = () => new Promise(resolve => setTimeout(resolve, 0));

export const flushPromises = () => {
  return new Promise(resolve => setImmediate(resolve));
};

export const createTestingPinia = (initialState = {}) => {
  const pinia = createPinia();

  // Apply initial state if provided
  if (initialState) {
    pinia.state.value = initialState;
  }

  return pinia;
};

// Cleanup after each test
afterEach(() => {
  vi.clearAllMocks();
  localStorageMock.clear();
  sessionStorageMock.clear();
});

// Export for use in tests
export default {
  nextTick,
  flushPromises,
  createTestingPinia
};
