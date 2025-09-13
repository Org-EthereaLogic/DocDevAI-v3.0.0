/**
 * Test helpers and mock data for DevDocAI frontend testing
 */

// Mock document data
export const mockDocuments = {
  readme: {
    id: 'doc-001',
    type: 'readme',
    projectName: 'DevDocAI Test',
    description: 'A test project for DevDocAI',
    content: '# DevDocAI Test\n\nA test project for DevDocAI...',
    healthScore: 92,
    generatedAt: new Date().toISOString(),
    author: 'Test User',
    techStack: ['Python', 'Vue.js', 'FastAPI'],
    features: ['AI-powered generation', 'Real-time validation'],
    metadata: {
      version: '1.0.0',
      generateTime: 47.3,
      cost: 0.047,
      aiProvider: 'openai'
    }
  },
  apiDoc: {
    id: 'doc-002',
    type: 'api-doc',
    projectName: 'DevDocAI API',
    content: '# API Documentation\n\n## Endpoints...',
    healthScore: 88,
    generatedAt: new Date().toISOString(),
    endpoints: [
      { path: '/api/v1/documents', method: 'GET', description: 'List documents' },
      { path: '/api/v1/documents', method: 'POST', description: 'Create document' }
    ]
  },
  changelog: {
    id: 'doc-003',
    type: 'changelog',
    projectName: 'DevDocAI',
    version: '3.6.0',
    content: '# Changelog\n\n## v3.6.0...',
    healthScore: 95,
    generatedAt: new Date().toISOString(),
    changes: ['Added error handling', 'Improved validation'],
    breakingChanges: []
  }
};

// Mock API responses
export const mockApiResponses = {
  success: {
    document: mockDocuments.readme,
    metadata: {
      generatedAt: new Date().toISOString(),
      cost: 0.047,
      duration: 47.3
    }
  },
  error: {
    error: 'Generation failed',
    message: 'API key is invalid',
    code: 'AUTH_ERROR'
  },
  timeout: {
    error: 'Request timeout',
    message: 'Generation is taking longer than expected',
    code: 'TIMEOUT'
  },
  rateLimit: {
    error: 'Rate limit exceeded',
    message: 'Too many requests. Please wait 60 seconds.',
    code: 'RATE_LIMIT',
    retryAfter: 60
  }
};

// Mock form data
export const mockFormData = {
  valid: {
    projectName: 'Test Project',
    description: 'This is a test project for automated testing',
    techStack: ['Python', 'Vue.js'],
    features: ['Feature 1', 'Feature 2'],
    author: 'Test Author',
    installationSteps: ['npm install', 'npm run dev']
  },
  invalid: {
    projectName: '', // Missing required field
    description: 'Too short', // Less than 10 characters
    techStack: [],
    features: [],
    author: 'A', // Too short
    installationSteps: []
  },
  malicious: {
    projectName: '<script>alert("XSS")</script>',
    description: 'Normal description with <iframe src="evil.com"></iframe>',
    techStack: ['<img src=x onerror=alert(1)>'],
    features: ['javascript:alert(1)'],
    author: 'onclick=alert(1)',
    installationSteps: ['<script>fetch("evil.com")</script>']
  }
};

// Error simulation helpers
export const simulateNetworkError = () => {
  return Promise.reject(new Error('Network Error'));
};

export const simulateTimeout = (delay = 5000) => {
  return new Promise((_, reject) => {
    setTimeout(() => {
      const error = new Error('Request timeout');
      error.code = 'ECONNABORTED';
      reject(error);
    }, delay);
  });
};

export const simulateApiError = (status, message) => {
  const error = new Error(message);
  error.response = {
    status,
    data: { message, error: message },
    statusText: message
  };
  return Promise.reject(error);
};

// Validation helpers
export const validateFormField = (value, rules) => {
  for (const rule of rules) {
    const result = rule(value);
    if (result !== true) {
      return result; // Return error message
    }
  }
  return null; // No errors
};

// Testing validation rules
export const validationRules = {
  required: (message = 'This field is required') => (value) => {
    return !!value && value.trim().length > 0 ? true : message;
  },

  minLength: (min, message) => (value) => {
    const msg = message || `Must be at least ${min} characters`;
    return value && value.length >= min ? true : msg;
  },

  maxLength: (max, message) => (value) => {
    const msg = message || `Must be less than ${max} characters`;
    return value && value.length <= max ? true : msg;
  },

  pattern: (regex, message) => (value) => {
    const msg = message || 'Invalid format';
    return regex.test(value) ? true : msg;
  },

  noXss: (message = 'Contains potentially harmful content') => (value) => {
    const xssPatterns = [
      /<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi,
      /<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>/gi,
      /javascript:/gi,
      /on\w+\s*=/gi
    ];

    for (const pattern of xssPatterns) {
      if (pattern.test(value)) {
        return message;
      }
    }
    return true;
  }
};

// Mock store helpers
export const createMockDocumentStore = (initialState = {}) => {
  return {
    documents: initialState.documents || [],
    currentDocument: initialState.currentDocument || null,
    isLoading: initialState.isLoading || false,
    error: initialState.error || null,
    generationProgress: initialState.generationProgress || 0,
    generationStatus: initialState.generationStatus || null,

    // Actions
    generateDocument: jest.fn(() => Promise.resolve(mockApiResponses.success)),
    fetchDocuments: jest.fn(() => Promise.resolve({ documents: [mockDocuments.readme] })),
    updateDocument: jest.fn(() => Promise.resolve()),
    deleteDocument: jest.fn(() => Promise.resolve()),
    reviewDocument: jest.fn(() => Promise.resolve()),
    clearError: jest.fn(),
    validateDocumentData: jest.fn(() => null),
    retryOperation: jest.fn((operation) => operation()),

    // Computed
    hasError: initialState.error ? true : false,
    errorMessage: initialState.error || null
  };
};

export const createMockNotificationStore = () => {
  return {
    notifications: [],
    addSuccess: jest.fn(),
    addError: jest.fn(),
    addWarning: jest.fn(),
    addInfo: jest.fn(),
    remove: jest.fn(),
    clear: jest.fn()
  };
};

// Async testing utilities
export const waitForAsync = (ms = 0) => {
  return new Promise(resolve => setTimeout(resolve, ms));
};

export const flushPromises = () => {
  return new Promise(resolve => setImmediate(resolve));
};

// Component testing helpers
export const triggerValidation = async (wrapper, fieldName) => {
  const input = wrapper.find(`[data-testid="${fieldName}-input"]`);
  await input.trigger('blur');
  await wrapper.vm.$nextTick();
};

export const fillForm = async (wrapper, data) => {
  for (const [field, value] of Object.entries(data)) {
    const input = wrapper.find(`[data-testid="${field}-input"]`);
    if (input.exists()) {
      await input.setValue(value);
      await input.trigger('input');
    }
  }
  await wrapper.vm.$nextTick();
};

export const submitForm = async (wrapper) => {
  const submitButton = wrapper.find('[data-testid="submit-button"]');
  await submitButton.trigger('click');
  await flushPromises();
};

// API mock interceptors
export const setupApiMocks = (axios) => {
  const handlers = new Map();

  const mockAdapter = {
    onPost: (url) => ({
      reply: (handler) => {
        handlers.set(`POST:${url}`, handler);
      }
    }),
    onGet: (url) => ({
      reply: (handler) => {
        handlers.set(`GET:${url}`, handler);
      }
    }),
    reset: () => {
      handlers.clear();
    }
  };

  // Override axios methods
  const originalPost = axios.post;
  const originalGet = axios.get;

  axios.post = async (url, data) => {
    const handler = handlers.get(`POST:${url}`);
    if (handler) {
      const [status, response] = await handler(data);
      if (status >= 400) {
        const error = new Error('Request failed');
        error.response = { status, data: response };
        throw error;
      }
      return { status, data: response };
    }
    return originalPost.call(axios, url, data);
  };

  axios.get = async (url) => {
    const handler = handlers.get(`GET:${url}`);
    if (handler) {
      const [status, response] = await handler();
      if (status >= 400) {
        const error = new Error('Request failed');
        error.response = { status, data: response };
        throw error;
      }
      return { status, data: response };
    }
    return originalGet.call(axios, url);
  };

  return mockAdapter;
};

// Performance testing helpers
export const measurePerformance = async (fn, iterations = 100) => {
  const times = [];

  for (let i = 0; i < iterations; i++) {
    const start = performance.now();
    await fn();
    const end = performance.now();
    times.push(end - start);
  }

  return {
    average: times.reduce((a, b) => a + b, 0) / times.length,
    min: Math.min(...times),
    max: Math.max(...times),
    median: times.sort((a, b) => a - b)[Math.floor(times.length / 2)]
  };
};

// Accessibility testing helpers
export const checkA11y = (wrapper) => {
  const issues = [];

  // Check for missing alt text
  const images = wrapper.findAll('img');
  images.forEach(img => {
    if (!img.attributes('alt')) {
      issues.push('Image missing alt text');
    }
  });

  // Check for form labels
  const inputs = wrapper.findAll('input, textarea, select');
  inputs.forEach(input => {
    const id = input.attributes('id');
    if (id) {
      const label = wrapper.find(`label[for="${id}"]`);
      if (!label.exists()) {
        issues.push(`Input ${id} missing label`);
      }
    }
  });

  // Check for button text
  const buttons = wrapper.findAll('button');
  buttons.forEach(button => {
    if (!button.text() && !button.attributes('aria-label')) {
      issues.push('Button missing text or aria-label');
    }
  });

  return issues;
};

export default {
  mockDocuments,
  mockApiResponses,
  mockFormData,
  simulateNetworkError,
  simulateTimeout,
  simulateApiError,
  validateFormField,
  validationRules,
  createMockDocumentStore,
  createMockNotificationStore,
  waitForAsync,
  flushPromises,
  triggerValidation,
  fillForm,
  submitForm,
  setupApiMocks,
  measurePerformance,
  checkA11y
};
