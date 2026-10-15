'use strict';
// Suíte medida no experimento: somente os testes de propriedade (decisão D7).
module.exports = {
  testEnvironment: 'node',
  testMatch: ['<rootDir>/test/properties/**/*.prop.test.js'],
  setupFiles: ['<rootDir>/test/properties/setup.js'],
  collectCoverageFrom: ['src/domain/**/*.js'],
  coverageReporters: ['json-summary', 'text'],
};
