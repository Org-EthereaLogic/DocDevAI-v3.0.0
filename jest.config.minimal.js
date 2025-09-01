module.exports = {
  testEnvironment: 'jsdom',
  preset: 'ts-jest',
  testMatch: ['<rootDir>/tests/unit/M011-UIComponents/**/*.test.{ts,tsx}'],
  moduleNameMapping: {
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy'
  },
  collectCoverage: false,
  transform: {
    '^.+\\.tsx?$': ['ts-jest', {
      tsconfig: {
        jsx: 'react-jsx'
      }
    }]
  }
};