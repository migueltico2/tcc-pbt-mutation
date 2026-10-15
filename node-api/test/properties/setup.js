'use strict';
// Configuração do fast-check (equivalente à do jqwik no java-api):
// 100 execuções por propriedade e semente nova a cada execução (padrão do fast-check).
const fc = require('fast-check');

fc.configureGlobal({ numRuns: 100 });
