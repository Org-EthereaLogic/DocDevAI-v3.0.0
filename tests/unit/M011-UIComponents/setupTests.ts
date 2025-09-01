/**
 * Test Setup for M011 UI Components
 * 
 * Provides global test configuration and mocks for UI component testing
 */

import '@testing-library/jest-dom';
import { configure } from '@testing-library/react';

// Configure testing library
configure({ testIdAttribute: 'data-testid' });

// Mock VS Code API
global.acquireVsCodeApi = jest.fn(() => ({
  postMessage: jest.fn(),
  setState: jest.fn(),
  getState: jest.fn(() => ({}))
}));

// Mock Window APIs that might not be available in test environment
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // Deprecated
    removeListener: jest.fn(), // Deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock IntersectionObserver
global.IntersectionObserver = jest.fn().mockImplementation((callback, options) => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
  root: null,
  rootMargin: '',
  thresholds: [],
}));

// Mock ResizeObserver
global.ResizeObserver = jest.fn().mockImplementation((callback) => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
  length: 0,
  key: jest.fn(),
};

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
});

// Mock navigator.clipboard
Object.assign(navigator, {
  clipboard: {
    writeText: jest.fn().mockResolvedValue(''),
    readText: jest.fn().mockResolvedValue('')
  }
});

// Mock Chart libraries for dashboard widgets
jest.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => children,
  LineChart: ({ children }: any) => <div data-testid="line-chart">{children}</div>,
  Line: () => <div data-testid="line" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  RadarChart: ({ children }: any) => <div data-testid="radar-chart">{children}</div>,
  PolarGrid: () => <div data-testid="polar-grid" />,
  PolarAngleAxis: () => <div data-testid="polar-angle-axis" />,
  PolarRadiusAxis: () => <div data-testid="polar-radius-axis" />,
  Radar: () => <div data-testid="radar" />,
  BarChart: ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => <div data-testid="bar" />,
  ScatterChart: ({ children }: any) => <div data-testid="scatter-chart">{children}</div>,
  Scatter: () => <div data-testid="scatter" />
}));

// Mock D3 for complex visualizations
jest.mock('d3', () => ({
  select: jest.fn(() => ({
    selectAll: jest.fn(() => ({
      data: jest.fn(() => ({
        enter: jest.fn(() => ({
          append: jest.fn(() => ({
            attr: jest.fn().mockReturnThis(),
            style: jest.fn().mockReturnThis(),
            text: jest.fn().mockReturnThis()
          }))
        })),
        exit: jest.fn(() => ({
          remove: jest.fn()
        }))
      })),
      attr: jest.fn().mockReturnThis(),
      style: jest.fn().mockReturnThis()
    })),
    append: jest.fn().mockReturnThis(),
    attr: jest.fn().mockReturnThis(),
    style: jest.fn().mockReturnThis()
  }))
}));

// Console error suppression for expected errors during testing
const originalError = console.error;
beforeAll(() => {
  console.error = (...args: any[]) => {
    if (
      typeof args[0] === 'string' &&
      (args[0].includes('Warning: ReactDOM.render is deprecated') ||
       args[0].includes('Warning: React.createFactory() is deprecated') ||
       args[0].includes('The above error occurred'))
    ) {
      return;
    }
    originalError.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
});

// Global test utilities
global.testUtils = {
  mockTheme: {
    palette: {
      primary: { main: '#1976d2' },
      secondary: { main: '#dc004e' },
      error: { main: '#f44336' },
      warning: { main: '#ff9800' },
      success: { main: '#4caf50' },
      info: { main: '#2196f3' },
      text: {
        primary: '#000000',
        secondary: '#666666'
      },
      background: {
        default: '#ffffff',
        paper: '#ffffff'
      },
      divider: '#e0e0e0'
    },
    breakpoints: {
      down: jest.fn(() => 'max-width: 600px')
    },
    shadows: ['none', '0px 2px 4px rgba(0,0,0,0.1)'],
    zIndex: {
      modal: 1300
    }
  },
  
  mockStateManagerState: {
    ui: {
      theme: 'light',
      layout: 'dashboard',
      sidebarOpen: true,
      loading: false,
      error: null,
      notifications: [],
      accessibility: {
        highContrast: false,
        reduceMotion: false,
        keyboardNavigation: true,
        enhancedSupport: false
      }
    },
    components: {},
    backend: {
      connection: 'connected',
      lastSync: new Date(),
      errors: []
    }
  },

  createMockEvent: (type: string, data: any = {}) => ({
    id: `test-event-${Date.now()}`,
    type,
    source: 'test',
    timestamp: new Date(),
    data,
    metadata: {}
  }),

  waitForAnimation: () => new Promise(resolve => setTimeout(resolve, 100))
};

// Type augmentation for global test utilities
declare global {
  var testUtils: {
    mockTheme: any;
    mockStateManagerState: any;
    createMockEvent: (type: string, data?: any) => any;
    waitForAnimation: () => Promise<void>;
  };
  var acquireVsCodeApi: jest.Mock;
}