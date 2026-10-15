'use strict';

/** Propriedades P5–P7 (módulo Disponibilidade). */
const { fc, cenario, itens, Montado, verificar } = require('./geradores');
const { RegraNegocioError } = require('../../src/domain/modelos');

function tentarConfirmar(m, r) {
  try {
    m.servico.confirmar(r.id);
    return true;
  } catch (e) {
    if (e instanceof RegraNegocioError) {
      return false;
    }
    throw e;
  }
}

function disponibilidadeNoIntervalo(m) {
  m.loteIds.forEach((_, i) => {
    const d = m.lote(i).quantidadeDisponivel;
    verificar(d >= 0 && d <= m.lote(i).quantidadeTotal, `disponibilidade fora de [0, total]: ${d}`);
  });
}

function verificarReducao(m, r, lista) {
  const antes = m.disponibilidades();
  const pedido = m.pedidoPorLote(lista);
  const aceita = tentarConfirmar(m, r);
  const depois = m.disponibilidades();
  antes.forEach((valor, i) => {
    const esperado = aceita ? valor - pedido[i] : valor;
    verificar(
      depois[i] === esperado,
      `lote ${i}: esperado ${esperado}, obtido ${depois[i]} (confirmação ${aceita ? 'aceita' : 'recusada'})`,
    );
  });
}

describe('disponibilidade', () => {
  test('P5 disponibilidade nao negativa', () => {
    fc.assert(
      fc.property(cenario, itens, (c, outros) => {
        const m = new Montado(c.lotes);
        const r1 = m.reservar(c.itens);
        const r2 = m.reservar(outros);
        tentarConfirmar(m, r1);
        disponibilidadeNoIntervalo(m);
        tentarConfirmar(m, r2);
        disponibilidadeNoIntervalo(m);
      }),
    );
  });

  test('P6 reducao correta', () => {
    fc.assert(
      fc.property(cenario, itens, (c, outros) => {
        const m = new Montado(c.lotes);
        const r1 = m.reservar(c.itens);
        const r2 = m.reservar(outros);
        verificarReducao(m, r1, c.itens);
        verificarReducao(m, r2, outros);
      }),
    );
  });

  test('P7 cancelamento restaura', () => {
    fc.assert(
      fc.property(cenario, fc.boolean(), (c, expirar) => {
        const m = new Montado(c.lotes);
        const r = m.reservar(c.itens);
        const antes = m.disponibilidades();
        tentarConfirmar(m, r);
        if (expirar) {
          m.servico.expirar(r.id);
        } else {
          m.servico.cancelar(r.id);
        }
        const depois = m.disponibilidades();
        verificar(
          antes.every((v, i) => v === depois[i]),
          `disponibilidade não restaurada: ${antes} -> ${depois}`,
        );
      }),
    );
  });
});
