module.exports = {
  testEnvironment: 'jsdom',
  preset: 'ts-jest',
  testMatch: ['<rootDir>/tests/unit/M011-UIComponents/**/*.test.{ts,tsx}'],
  setupFilesAfterEnv: ['<rootDir>/tests/unit/M011-UIComponents/setupTests.ts'],
  moduleNameMapping: {
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy'
  },
  collectCoverage: true,
  collectCoverageFrom: [
    'src/modules/M011-UIComponents/**/*.{ts,tsx}',
    '!src/modules/M011-UIComponents/**/index.{ts,tsx}'
  ]
};