'use strict';

/** Suíte forte, P9 (Reservas e Cupons): oráculo exato do preço, calculado por um modelo do SPEC. */
const { fc, HOJE, cenario, cupom, Montado, verificar, precoEsperado } = require('./apoio');

describe('forte: preco', () => {
  test('P9 oraculo de preco', () => {
    // modo: 0 = cupom gerado (válido, vencido ou abaixo do mínimo), 1 = código inexistente, 2 = sem cupom
    fc.assert(
      fc.property(cenario, cupom, fc.integer({ min: 0, max: 2 }), (c, cp, modo) => {
        const m = new Montado(c.lotes);
        const r = m.reservar(c.itens);
        if (modo === 0) {
          m.servico.aplicarCupom(r.id, m.cadastrar(cp, 'CUPOM'));
        } else if (modo === 1) {
          m.servico.aplicarCupom(r.id, 'INEXISTENTE');
        }
        const esperado = precoEsperado(c.lotes, c.itens, modo === 0 ? cp : null);
        const t = m.servico.calcularTotais(r.id, HOJE);
        verificar(t.subtotal === esperado.subtotal, `subtotal ${t.subtotal} != ${esperado.subtotal}`);
        verificar(t.desconto === esperado.desconto, `desconto ${t.desconto} != ${esperado.desconto}`);
        verificar(t.total === esperado.total, `total ${t.total} != ${esperado.total}`);
      }),
    );
  });
});
