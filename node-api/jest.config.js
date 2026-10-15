'use strict';
module.exports = {
  testEnvironment: 'node',
  setupFiles: ['<rootDir>/test/properties/setup.js'],
  testPathIgnorePatterns: ['/node_modules/', '/.stryker-tmp/'],
};
