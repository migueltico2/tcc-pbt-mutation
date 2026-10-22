'use strict';

/**
 * Suíte forte, P17 (Disponibilidade e Status): modelo de referência do estoque e dos status
 * sob uma sequência de operações sobre várias reservas (R15–R19).
 */
const { RegraNegocioError } = require('../../../src/domain/modelos');
const { fc, cenario, itens, Montado, verificar, destino, operacaoEstoque } = require('./apoio');

const METODO = { CONFIRMAR: 'confirmar', CANCELAR: 'cancelar', EXPIRAR: 'expirar', PAGAR: 'pagar' };

describe('forte: estoque', () => {
  test('P17 modelo de estoque', () => {
    fc.assert(
      fc.property(
        cenario,
        fc.array(itens, { minLength: 1, maxLength: 3 }),
        fc.array(operacaoEstoque, { minLength: 1, maxLength: 12 }),
        (c, outrasReservas, operacoes) => {
          const m = new Montado(c.lotes);
          const pedidos = [c.itens, ...outrasReservas];
          const reservas = pedidos.map((lista) => m.reservar(lista).id);
          // modelo
          const disponivel = c.lotes.map((l) => l.total);
          const status = reservas.map(() => 'CRIADA');
          const demanda = pedidos.map((lista) => m.pedidoPorLote(lista));

          for (const { reserva, op } of operacoes) {
            const k = reserva % reservas.length;
            let esperadoErro = null;
            let novoStatus = destino(status[k], op);
            if (novoStatus === null) {
              esperadoErro = 'TRANSICAO_INVALIDA';
            } else if (op === 'CONFIRMAR' && demanda[k].some((q, i) => q > disponivel[i])) {
              esperadoErro = 'DISPONIBILIDADE_INSUFICIENTE';
              novoStatus = null;
            }
            let erro = null;
            try {
              m.servico[METODO[op]](reservas[k]);
            } catch (e) {
              if (!(e instanceof RegraNegocioError)) {
                throw e;
              }
              erro = e.codigo;
            }
            verificar(erro === esperadoErro, `${op} na reserva ${k} (${status[k]}): esperado ${esperadoErro}, obtido ${erro}`);
            if (novoStatus !== null) {
              if (op === 'CONFIRMAR') {
                demanda[k].forEach((q, i) => (disponivel[i] -= q));
              } else if ((op === 'CANCELAR' || op === 'EXPIRAR') && status[k] === 'CONFIRMADA') {
                demanda[k].forEach((q, i) => (disponivel[i] += q));
              }
              status[k] = novoStatus;
            }
            const real = m.disponibilidades();
            verificar(real.every((v, i) => v === disponivel[i]), `estoque ${real} != modelo ${disponivel} após ${op}`);
            reservas.forEach((id, j) => {
              const s = m.servico.buscarReserva(id).status;
              verificar(s === status[j], `reserva ${j}: status ${s} != modelo ${status[j]}`);
            });
          }
        },
      ),
    );
  });
});
