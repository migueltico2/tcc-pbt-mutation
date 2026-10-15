'use strict';

/**
 * Executa os casos de exemplo compartilhados (shared/casos-exemplo.json).
 * Os mesmos casos rodam na implementação Java: é a evidência de equivalência funcional.
 */
const fs = require('fs');
const path = require('path');

/** Procura shared/casos-exemplo.json subindo diretórios (funciona também na sandbox do StrykerJS). */
function localizarCasos() {
  let dir = __dirname;
  while (dir !== path.dirname(dir)) {
    const candidato = path.join(dir, 'shared', 'casos-exemplo.json');
    if (fs.existsSync(candidato)) {
      return candidato;
    }
    dir = path.dirname(dir);
  }
  throw new Error('shared/casos-exemplo.json não encontrado');
}

const casos = JSON.parse(fs.readFileSync(localizarCasos(), 'utf8'));
const { ServicoIngressos } = require('../../src/domain/servicoIngressos');

function resolver(arg, salvos) {
  if (typeof arg === 'string' && arg.startsWith('$')) {
    return salvos[arg.slice(1)];
  }
  return arg;
}

describe('casos de exemplo compartilhados', () => {
  test.each(casos.map((c) => [c.nome, c]))('%s', (_nome, caso) => {
    const servico = new ServicoIngressos();
    const salvos = {};
    caso.passos.forEach((passo, i) => {
      const args = passo.args.map((a) => resolver(a, salvos));
      let resultado;
      let erro = null;
      try {
        resultado = servico[passo.op](...args);
      } catch (e) {
        erro = e;
      }
      const contexto = `passo ${i} (${passo.op})`;
      if (passo.erro) {
        expect([contexto, erro && erro.codigo]).toEqual([contexto, passo.erro]);
        return;
      }
      if (erro) {
        throw new Error(`${contexto}: erro inesperado ${erro.codigo || erro.message}`);
      }
      if (passo.salvar) {
        salvos[passo.salvar] = resultado.id;
      }
      for (const [campo, valor] of Object.entries(passo.espera || {})) {
        expect([contexto, campo, resultado[campo]]).toEqual([contexto, campo, valor]);
      }
    });
  });
});
