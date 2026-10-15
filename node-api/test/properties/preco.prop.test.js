'use strict';

/** Propriedades P1–P4 (módulos Reservas e Cupons). */
const { fc, HOJE, cenario, cupom, Montado, verificar } = require('./geradores');

const chaves = fc.array(fc.integer({ min: 0, max: 1000 }), { minLength: 5, maxLength: 5 });

describe('preco', () => {
  test('P1 total nao negativo', () => {
    // modo: 0 = cupom gerado, 1 = código inexistente, 2 = sem cupom
    fc.assert(
      fc.property(cenario, cupom, fc.integer({ min: 0, max: 2 }), (c, cp, modo) => {
        const m = new Montado(c.lotes);
        const r = m.reservar(c.itens);
        if (modo === 0) {
          m.servico.aplicarCupom(r.id, m.cadastrar(cp, 'CUPOM'));
        } else if (modo === 1) {
          m.servico.aplicarCupom(r.id, 'INEXISTENTE');
        }
        const t = m.servico.calcularTotais(r.id, HOJE);
        verificar(t.total >= 0, `total negativo: ${t.total}`);
      }),
    );
  });

  test('P2 desconto limitado', () => {
    fc.assert(
      fc.property(cenario, cupom, (c, cp) => {
        const m = new Montado(c.lotes);
        const r = m.reservar(c.itens);
        m.servico.aplicarCupom(r.id, m.cadastrar(cp, 'CUPOM'));
        const t = m.servico.calcularTotais(r.id, HOJE);
        verificar(t.desconto >= 0, `desconto negativo: ${t.desconto}`);
        verificar(t.desconto <= t.subtotal, 'desconto acima do subtotal');
        verificar(t.total === t.subtotal - t.desconto, 'total diferente de subtotal - desconto');
      }),
    );
  });

  test('P3 comutatividade do subtotal', () => {
    fc.assert(
      fc.property(cenario, chaves, (c, ks) => {
        const m = new Montado(c.lotes);
        const indices = c.itens.map((_, i) => i);
        indices.sort((a, b) => ks[a] - ks[b]); // ordenação estável, como no Java
        const permutados = indices.map((i) => c.itens[i]);
        const original = m.reservar(c.itens);
        const permutada = m.reservar(permutados);
        const a = m.servico.calcularTotais(original.id, HOJE).subtotal;
        const b = m.servico.calcularTotais(permutada.id, HOJE).subtotal;
        verificar(a === b, `subtotal mudou com a ordem: ${a} != ${b}`);
      }),
    );
  });

  test('P4 cupom invalido neutro', () => {
    // tipoInvalido: 0 = inexistente, 1 = expirado, 2 = mínimo acima do subtotal
    fc.assert(
      fc.property(
        cenario,
        cupom,
        fc.integer({ min: 0, max: 2 }),
        fc.integer({ min: -30, max: -1 }),
        fc.integer({ min: 1, max: 100000 }),
        (c, cp, tipoInvalido, offsetExpirado, excessoMinimo) => {
          const m = new Montado(c.lotes);
          const r = m.reservar(c.itens);
          const subtotal = m.servico.calcularTotais(r.id, HOJE).subtotal;
          let codigo;
          if (tipoInvalido === 0) {
            codigo = 'INEXISTENTE';
          } else if (tipoInvalido === 1) {
            codigo = m.cadastrar({ ...cp, validadeOffset: offsetExpirado }, 'VENCIDO');
          } else {
            codigo = m.cadastrar({ ...cp, minimo: subtotal + excessoMinimo }, 'MINIMO');
          }
          m.servico.aplicarCupom(r.id, codigo);
          const t = m.servico.calcularTotais(r.id, HOJE);
          verificar(t.total === subtotal, `cupom inválido alterou o total: ${t.total} != ${subtotal}`);
        },
      ),
    );
  });
});
