'use strict';
// Suíte medida no experimento (decisão D7): somente testes de propriedade.
// SUITE=fraca (padrão): P1–P8, as propriedades do TCC I.
// SUITE=forte: P1–P8 + P9–P17 (oráculos exatos e regras sem cobertura).
const suite = process.env.SUITE || 'fraca';
const fraca = ['preco', 'disponibilidade', 'status'].map((n) => `<rootDir>/test/properties/${n}.prop.test.js`);
module.exports = {
  testEnvironment: 'node',
  testMatch: suite === 'forte' ? [...fraca, '<rootDir>/test/properties/fortes/*.prop.test.js'] : fraca,
  setupFiles: ['<rootDir>/test/properties/setup.js'],
  collectCoverageFrom: ['src/domain/**/*.js'],
  coverageReporters: ['json-summary', 'text'],
};
