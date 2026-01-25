module.exports = {
  rootDir: '..',
  testEnvironment: 'jsdom',
  testMatch: ['<rootDir>/tests/frontend/**/*.test.ts?(x)'],
  moduleNameMapper: {
    '\\.(css|less|scss)$': 'identity-obj-proxy',
  },
  setupFilesAfterEnv: ['<rootDir>/tests/frontend/setup/setupTests.ts'],
  moduleDirectories: ['node_modules', '<rootDir>/app/node_modules'],
  transform: {
    '^.+\\.(ts|tsx)$': [
      '<rootDir>/app/node_modules/ts-jest',
      {
        useESM: false,
        tsconfig: '<rootDir>/app/tsconfig.json',
      },
    ],
  },
  transformIgnorePatterns: [
    'node_modules/(?!.*)',
  ],
  globals: {
    __BACKEND_URL__: 'http://localhost:8000',
  },
};
