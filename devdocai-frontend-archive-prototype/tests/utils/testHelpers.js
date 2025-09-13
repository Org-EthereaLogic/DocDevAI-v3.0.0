/**
 * Test utilities and helpers for DevDocAI frontend testing
 * Provides common testing patterns and mock data
 */

import { nextTick } from 'vue';
import { vi } from 'vitest';

// Mock form data for testing
export const mockFormData = {
  valid: {
    projectName: 'DevDocAI Test Project',
    description: 'A comprehensive testing project for DevDocAI with all required features and functionality.',
    author: 'Test Author',
    techStack: ['Vue.js', 'Python', 'FastAPI', 'Tailwind CSS'],
    features: ['AI-powered documentation', 'Real-time generation', 'Template marketplace']
  },
  invalid: {
    projectName: 'A',
    description: 'Short',
    author: '',
    techStack: [],
    features: []
  },
  malicious: {
    projectName: '<script>alert("xss")</script>Project',
    description: '<img src="x" onerror="alert(1)">Description',
    author: '<div onclick="alert(1)">Author</div>',
    techStack: ['<script>console.log("xss")</script>'],
    features: ['<iframe src="javascript:alert(1)"></iframe>']
  }
};

// API response mocks
export const mockApiResponses = {
  generateDocument: {
    success: {
      success: true,
      content: '# Test Project\n\nGenerated documentation content...',
      metadata: {
        generation_time: 2.5,
        model_used: 'gpt-4',
        cost: 0.05
      }
    },
    error: {
      success: false,
      error: 'API rate limit exceeded',
      details: 'Please wait before making another request'
    }
  },
  validateProject: {
    valid: {
      valid: true,
      suggestions: ['Consider adding more features']
    },
    invalid: {
      valid: false,
      errors: ['Project name is required', 'Description too short']
    }
  }
};

// Form filling helpers
export async function fillForm(wrapper, data) {
  for (const [key, value] of Object.entries(data)) {
    const input = wrapper.find(`[data-testid="${key}-input"]`);
    if (input.exists()) {
      await input.setValue(value);
      await input.trigger('blur');
    }
  }
  await nextTick();
}

export async function submitForm(wrapper) {
  const submitButton = wrapper.find('[data-testid="submit-button"]');
  await submitButton.trigger('click');
  await flushPromises();
}

export async function triggerValidation(wrapper, fieldName) {
  const input = wrapper.find(`[data-testid="${fieldName}-input"]`);
  if (input.exists()) {
    await input.setValue('');
    await input.trigger('blur');
    await nextTick();
  }
}

// Promise utilities
export function flushPromises() {
  return new Promise(resolve => setTimeout(resolve, 0));
}

export function waitForCondition(condition, timeout = 5000) {
  return new Promise((resolve, reject) => {
    const startTime = Date.now();
    const check = () => {
      if (condition()) {
        resolve();
      } else if (Date.now() - startTime > timeout) {
        reject(new Error('Condition not met within timeout'));
      } else {
        setTimeout(check, 10);
      }
    };
    check();
  });
}

// Component testing utilities
export function createMockComponent(name, template = '<div></div>') {
  return {
    name,
    template,
    props: ['modelValue'],
    emits: ['update:modelValue']
  };
}

export function mockApiService(responses = {}) {
  return {
    generateDocument: vi.fn().mockResolvedValue(responses.generateDocument || mockApiResponses.generateDocument.success),
    validateProject: vi.fn().mockResolvedValue(responses.validateProject || mockApiResponses.validateProject.valid),
    getTemplates: vi.fn().mockResolvedValue([]),
    cancelGeneration: vi.fn().mockResolvedValue({ success: true })
  };
}

// Accessibility testing helpers
export function createA11yMocks() {
  // Mock screen reader announcements
  const announcements = [];

  window.HTMLElement.prototype.setAttribute = vi.fn((attr, value) => {
    if (attr === 'aria-live') {
      announcements.push(value);
    }
  });

  return {
    getAnnouncements: () => announcements,
    clearAnnouncements: () => announcements.splice(0)
  };
}

// Performance testing utilities
export function measurePerformance(operation) {
  const start = performance.now();
  const result = operation();
  const end = performance.now();

  return {
    result,
    duration: end - start
  };
}

export async function measureAsyncPerformance(operation) {
  const start = performance.now();
  const result = await operation();
  const end = performance.now();

  return {
    result,
    duration: end - start
  };
}

// Store testing utilities
export function createMockStore(initialState = {}) {
  const state = { ...initialState };
  const mutations = {};
  const actions = {};

  return {
    state,
    commit: vi.fn((mutation, payload) => {
      if (mutations[mutation]) {
        mutations[mutation](state, payload);
      }
    }),
    dispatch: vi.fn((action, payload) => {
      if (actions[action]) {
        return actions[action]({ state, commit: this.commit }, payload);
      }
      return Promise.resolve();
    }),
    getters: {}
  };
}

// Network mocking utilities
export function mockNetworkError() {
  global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));
}

export function mockNetworkSuccess(response) {
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve(response),
    text: () => Promise.resolve(JSON.stringify(response))
  });
}

export function mockNetworkFailure(status = 500, message = 'Server error') {
  global.fetch = vi.fn().mockResolvedValue({
    ok: false,
    status,
    statusText: message,
    json: () => Promise.resolve({ error: message })
  });
}

// Error boundary testing
export function createErrorBoundary() {
  return {
    name: 'ErrorBoundary',
    data() {
      return {
        hasError: false,
        error: null
      };
    },
    errorCaptured(error) {
      this.hasError = true;
      this.error = error;
      return false;
    },
    template: `
      <div v-if="hasError" data-testid="error-boundary">
        Error: {{ error.message }}
      </div>
      <slot v-else></slot>
    `
  };
}

// Visual regression testing utilities
export function createVisualSnapshot(wrapper, name) {
  const html = wrapper.html();
  const styles = Array.from(document.styleSheets)
    .map(sheet => {
      try {
        return Array.from(sheet.cssRules).map(rule => rule.cssText).join('\n');
      } catch {
        return '';
      }
    })
    .join('\n');

  return {
    name,
    html,
    styles,
    timestamp: new Date().toISOString()
  };
}

// Custom matchers for Vitest
export const customMatchers = {
  toBeAccessible(received) {
    // Basic accessibility checks
    const hasAriaLabel = received.querySelector('[aria-label]');
    const hasAltText = Array.from(received.querySelectorAll('img')).every(img => img.alt);
    const hasValidHeadings = Array.from(received.querySelectorAll('h1,h2,h3,h4,h5,h6')).length > 0;

    const isAccessible = hasAriaLabel || hasAltText || hasValidHeadings;

    return {
      pass: isAccessible,
      message: () => isAccessible
        ? 'Element is accessible'
        : 'Element is not accessible - missing aria-label, alt text, or headings'
    };
  },

  toHaveValidForm(received) {
    const inputs = received.querySelectorAll('input, textarea, select');
    const hasLabels = Array.from(inputs).every(input => {
      return input.getAttribute('aria-label') ||
             input.getAttribute('aria-labelledby') ||
             received.querySelector(`label[for="${input.id}"]`);
    });

    return {
      pass: hasLabels,
      message: () => hasLabels
        ? 'Form has valid labels for all inputs'
        : 'Form is missing labels for some inputs'
    };
  }
};

export default {
  mockFormData,
  mockApiResponses,
  fillForm,
  submitForm,
  triggerValidation,
  flushPromises,
  waitForCondition,
  createMockComponent,
  mockApiService,
  createA11yMocks,
  measurePerformance,
  measureAsyncPerformance,
  createMockStore,
  mockNetworkError,
  mockNetworkSuccess,
  mockNetworkFailure,
  createErrorBoundary,
  createVisualSnapshot,
  customMatchers
};
