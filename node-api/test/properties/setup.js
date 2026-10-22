'use strict';
// Configuração do fast-check (equivalente à do jqwik no java-api):
// número de execuções por propriedade (padrão 100; no experimento, PBT_TENTATIVAS = 10, 100 ou 1000)
// e semente nova a cada execução (padrão do fast-check).
const fc = require('fast-check');

const tentativas = Number(process.env.PBT_TENTATIVAS || 100);
fc.configureGlobal({ numRuns: tentativas });
