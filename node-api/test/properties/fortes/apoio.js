'use strict';

/**
 * Apoio da suíte forte (P9–P17): geradores adicionais e modelos de referência derivados do SPEC.md.
 * As faixas são idênticas às do java-api (properties/GeradoresFortes.java).
 */
const { fc, HOJE, cenario, cupom, itens, Montado, verificar } = require('../geradores');
const { RegraNegocioError } = require('../../../src/domain/modelos');

// Nomes de tipos e status vêm do SPEC (contrato), não das constantes da implementação.
const PERCENTUAL = 'PERCENTUAL';
const FIXO = 'FIXO';

/** Executa fn e devolve o código do erro de negócio, ou null se não houve erro. Outros erros sobem. */
function codigoDoErro(fn) {
  try {
    fn();
    return null;
  } catch (e) {
    if (e instanceof RegraNegocioError) {
      return e.codigo;
    }
    throw e;
  }
}

// ---------------------------------------------------------------- modelos de referência (SPEC)

/** R8, R11–R13. lotes: [{preco}], itensSpec: [{indiceLote, quantidade}], c: cupom gerado ou null. */
function precoEsperado(lotes, itensSpec, c) {
  let subtotal = 0;
  for (const it of itensSpec) {
    subtotal += lotes[it.indiceLote % lotes.length].preco * it.quantidade;
  }
  let desconto = 0;
  const valido = c !== null && c.validadeOffset >= 0 && subtotal >= c.minimo;
  if (valido) {
    let bruto = c.tipo === PERCENTUAL ? Math.floor((subtotal * c.valor) / 100) : c.valor;
    if (c.maximo !== null) {
      bruto = Math.min(bruto, c.maximo);
    }
    desconto = Math.min(bruto, subtotal);
  }
  return { subtotal, desconto, total: subtotal - desconto };
}

/** R9. */
function cupomValido(c) {
  const valorOk = c.tipo === PERCENTUAL ? c.valor >= 1 && c.valor <= 100 : c.valor > 0;
  return c.codigo !== null && c.codigo.trim() !== '' && valorOk && c.minimo >= 0 && (c.maximo === null || c.maximo > 0);
}

/** R18: status de destino de cada operação, ou null se a transição é inválida. */
function destino(status, op) {
  const ativa = status === 'CRIADA' || status === 'CONFIRMADA';
  switch (op) {
    case 'CONFIRMAR':
      return status === 'CRIADA' ? 'CONFIRMADA' : null;
    case 'PAGAR':
      return status === 'CONFIRMADA' ? 'PAGA' : null;
    case 'CANCELAR':
      return ativa ? 'CANCELADA' : null;
    case 'EXPIRAR':
      return ativa ? 'EXPIRADA' : null;
    default:
      throw new Error(`operação desconhecida: ${op}`);
  }
}

/** Leva uma reserva recém-criada (com itens) ao status pedido usando as operações da API. */
function levarAoStatus(servico, reservaId, status) {
  const caminho = {
    CRIADA: [],
    CONFIRMADA: ['confirmar'],
    PAGA: ['confirmar', 'pagar'],
    CANCELADA: ['cancelar'],
    EXPIRADA: ['expirar'],
  }[status];
  for (const op of caminho) {
    servico[op](reservaId);
  }
}

// ---------------------------------------------------------------- geradores

const STATUS_RESERVA = ['CRIADA', 'CONFIRMADA', 'PAGA', 'CANCELADA', 'EXPIRADA'];
const STATUS_EVENTO = ['ATIVO', 'CANCELADO', 'ENCERRADO'];

const evento = fc.record({
  nome: fc.constantFrom('', '   ', 'Show', null),
  capacidade: fc.integer({ min: -5, max: 300 }),
});

const loteBruto = fc.record({
  preco: fc.integer({ min: -50, max: 100000 }),
  total: fc.integer({ min: -3, max: 80 }),
});

const cadastroLotes = fc.record({
  capacidade: fc.integer({ min: 1, max: 200 }),
  outroTotal: fc.integer({ min: 1, max: 50 }),
  lotes: fc.array(loteBruto, { minLength: 1, maxLength: 6 }),
});

const cupomBruto = fc.constantFrom(PERCENTUAL, FIXO).chain((tipo) =>
  fc.record({
    codigo: fc.constantFrom('', ' ', 'C1', null),
    tipo: fc.constant(tipo),
    valor: tipo === PERCENTUAL ? fc.integer({ min: -5, max: 110 }) : fc.integer({ min: -5, max: 60000 }),
    minimo: fc.integer({ min: -5, max: 1000 }),
    maximo: fc.option(fc.integer({ min: -5, max: 1000 }), { nil: null, freq: 3 }),
  }),
);

const operacaoEstoque = fc.record({
  reserva: fc.integer({ min: 0, max: 3 }),
  op: fc.constantFrom('CONFIRMAR', 'CANCELAR', 'EXPIRAR', 'PAGAR'),
});

module.exports = {
  fc,
  HOJE,
  cenario,
  cupom,
  itens,
  Montado,
  verificar,
  codigoDoErro,
  precoEsperado,
  cupomValido,
  destino,
  levarAoStatus,
  STATUS_RESERVA,
  STATUS_EVENTO,
  evento,
  cadastroLotes,
  cupomBruto,
  operacaoEstoque,
};
