/**
 * Jest Configuration for M011 UI Components
 * 
 * Specialized Jest configuration for testing M011 UI Components module
 * with React Testing Library, Material-UI, and TypeScript support.
 */

const baseConfig = require('./jest.config.js');

module.exports = {
  ...baseConfig,
  
  // Test environment for React components
  testEnvironment: 'jsdom',
  
  // Display name for this configuration
  displayName: 'M011 UI Components',
  
  // Root directories for this test suite
  roots: [
    '<rootDir>/src/modules/M011-UIComponents',
    '<rootDir>/tests/unit/M011-UIComponents'
  ],
  
  // Test file patterns
  testMatch: [
    '<rootDir>/tests/unit/M011-UIComponents/**/*.test.{ts,tsx}',
    '<rootDir>/src/modules/M011-UIComponents/**/__tests__/**/*.{ts,tsx}',
    '<rootDir>/src/modules/M011-UIComponents/**/*.{test,spec}.{ts,tsx}'
  ],
  
  // Setup files
  setupFilesAfterEnv: [
    '<rootDir>/tests/unit/M011-UIComponents/setupTests.ts'
  ],
  
  // Module name mapping for absolute imports
  moduleNameMapping: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^@m011/(.*)$': '<rootDir>/src/modules/M011-UIComponents/$1',
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
    '\\.(jpg|jpeg|png|gif|eot|otf|webp|svg|ttf|woff|woff2|mp4|webm|wav|mp3|m4a|aac|oga)$': 'jest-transform-stub'
  },
  
  // File extensions to consider
  moduleFileExtensions: [
    'ts',
    'tsx',
    'js',
    'jsx',
    'json'
  ],
  
  // Transform configuration
  transform: {
    '^.+\\.(ts|tsx)$': ['ts-jest', {
      tsconfig: {
        jsx: 'react-jsx'
      }
    }],
    '^.+\\.(js|jsx)$': ['babel-jest', {
      presets: [
        ['@babel/preset-env', { targets: { node: 'current' } }],
        ['@babel/preset-react', { runtime: 'automatic' }]
      ]
    }]
  },
  
  // Files to ignore during transformation
  transformIgnorePatterns: [
    'node_modules/(?!(.*\\.mjs$|@testing-library|@mui|recharts))'
  ],
  
  // Coverage configuration
  collectCoverage: true,
  collectCoverageFrom: [
    'src/modules/M011-UIComponents/**/*.{ts,tsx}',
    '!src/modules/M011-UIComponents/**/*.d.ts',
    '!src/modules/M011-UIComponents/**/*.stories.{ts,tsx}',
    '!src/modules/M011-UIComponents/**/index.{ts,tsx}',
    '!src/modules/M011-UIComponents/**/__tests__/**',
    '!src/modules/M011-UIComponents/**/*.test.{ts,tsx}'
  ],
  
  // Coverage thresholds for Pass 1 (80-85% target)
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80
    },
    // Core components should have higher coverage
    'src/modules/M011-UIComponents/core/': {
      branches: 85,
      functions: 85,
      lines: 85,
      statements: 85
    },
    // Common components are critical
    'src/modules/M011-UIComponents/components/common/': {
      branches: 85,
      functions: 85,
      lines: 85,
      statements: 85
    }
  },
  
  // Coverage output
  coverageDirectory: '<rootDir>/coverage/m011',
  coverageReporters: [
    'text',
    'lcov',
    'html',
    'json-summary'
  ],
  
  // Test timeout for React component tests
  testTimeout: 10000,
  
  // Clear mocks between tests
  clearMocks: true,
  restoreMocks: true,
  
  // Verbose output for debugging
  verbose: true,
  
  // Error handling
  errorOnDeprecated: true,
  
  // Watch plugins for development
  watchPlugins: [
    'jest-watch-typeahead/filename',
    'jest-watch-typeahead/testname'
  ],
  
  // Additional Jest options for React Testing Library
  testEnvironmentOptions: {
    url: 'http://localhost:3000'
  }
};