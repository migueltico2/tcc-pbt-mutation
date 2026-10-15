'use strict';

/** Propriedade P8 (módulo Status): modelo de referência da tabela de transições R18/R19. */
const { fc, Montado, verificar } = require('./geradores');
const { StatusReserva, RegraNegocioError } = require('../../src/domain/modelos');

const OPERACOES = ['CONFIRMAR', 'PAGAR', 'CANCELAR', 'EXPIRAR', 'ADICIONAR'];

/** Modelo: status esperado após a operação, ou null se a transição é inválida. */
function esperado(atual, op) {
  switch (op) {
    case 'CONFIRMAR':
      return atual === StatusReserva.CRIADA ? StatusReserva.CONFIRMADA : null;
    case 'PAGAR':
      return atual === StatusReserva.CONFIRMADA ? StatusReserva.PAGA : null;
    case 'CANCELAR':
      return atual === StatusReserva.CRIADA || atual === StatusReserva.CONFIRMADA ? StatusReserva.CANCELADA : null;
    case 'EXPIRAR':
      return atual === StatusReserva.CRIADA || atual === StatusReserva.CONFIRMADA ? StatusReserva.EXPIRADA : null;
    case 'ADICIONAR':
      return atual === StatusReserva.CRIADA ? StatusReserva.CRIADA : null;
    default:
      throw new Error('operação desconhecida');
  }
}

describe('status', () => {
  test('P8 transicoes validas', () => {
    fc.assert(
      fc.property(
        fc.array(fc.constantFrom(...OPERACOES), { minLength: 1, maxLength: 8 }),
        fc.integer({ min: 1, max: 10 }),
        (ops, quantidade) => {
          const m = new Montado([{ preco: 1000, total: 50 }]);
          const r = m.servico.criarReserva(m.eventoId);
          m.servico.adicionarItem(r.id, m.loteIds[0], quantidade);
          for (const op of ops) {
            const antes = m.servico.buscarReserva(r.id).status;
            const esp = esperado(antes, op);
            let erro = null;
            try {
              switch (op) {
                case 'CONFIRMAR': m.servico.confirmar(r.id); break;
                case 'PAGAR': m.servico.pagar(r.id); break;
                case 'CANCELAR': m.servico.cancelar(r.id); break;
                case 'EXPIRAR': m.servico.expirar(r.id); break;
                case 'ADICIONAR': m.servico.adicionarItem(r.id, m.loteIds[0], 1); break;
                default: throw new Error('operação desconhecida');
              }
            } catch (e) {
              if (!(e instanceof RegraNegocioError)) {
                throw e;
              }
              erro = e.codigo;
            }
            const depois = m.servico.buscarReserva(r.id).status;
            if (esp === null) {
              verificar(erro === 'TRANSICAO_INVALIDA', `${op} a partir de ${antes} deveria ser recusada, erro=${erro}`);
              verificar(depois === antes, `${op} recusada alterou o status de ${antes} para ${depois}`);
            } else {
              verificar(erro === null, `${op} a partir de ${antes} deveria ser aceita, erro=${erro}`);
              verificar(depois === esp, `${op} a partir de ${antes}: esperado ${esp}, obtido ${depois}`);
            }
          }
        },
      ),
    );
  });
});
