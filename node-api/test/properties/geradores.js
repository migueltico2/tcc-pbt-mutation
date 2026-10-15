'use strict';

/**
 * Geradores de dados das propriedades. As faixas seguem a tabela "Parâmetros dos geradores"
 * do SPEC.md e são idênticas às do java-api (properties/Geradores.java).
 */
const fc = require('fast-check');
const { ServicoIngressos } = require('../../src/domain/servicoIngressos');
const { TipoCupom } = require('../../src/domain/modelos');

const HOJE = '2026-10-15';

/** Data ISO deslocada em dias a partir de HOJE (aritmética em UTC). */
function deslocar(dias) {
  const d = new Date(`${HOJE}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + dias);
  return d.toISOString().slice(0, 10);
}

const lote = fc.record({
  preco: fc.integer({ min: 0, max: 100000 }),
  total: fc.integer({ min: 1, max: 50 }),
});

const item = fc.record({
  indiceLote: fc.integer({ min: 0, max: 3 }),
  quantidade: fc.integer({ min: 1, max: 10 }),
});

const itens = fc.array(item, { minLength: 1, maxLength: 5 });

const cenario = fc.record({
  lotes: fc.array(lote, { minLength: 1, maxLength: 4 }),
  itens,
});

const cupom = fc.constantFrom(TipoCupom.PERCENTUAL, TipoCupom.FIXO).chain((tipo) =>
  fc.record({
    tipo: fc.constant(tipo),
    valor: tipo === TipoCupom.PERCENTUAL ? fc.integer({ min: 1, max: 100 }) : fc.integer({ min: 1, max: 50000 }),
    minimo: fc.integer({ min: 0, max: 200000 }),
    // nil com probabilidade 1/(freq+1) = 25%, como injectNull(0.25) no jqwik
    maximo: fc.option(fc.integer({ min: 1, max: 50000 }), { nil: null, freq: 3 }),
    validadeOffset: fc.integer({ min: -30, max: 30 }),
  }),
);

/** Monta o cenário no serviço: evento, lotes e reservas com os itens. */
class Montado {
  constructor(lotes) {
    this.servico = new ServicoIngressos();
    this.eventoId = this.servico.criarEvento('Evento', '2026-12-01', 'BH', 200).id;
    this.loteIds = lotes.map((l) => this.servico.criarLote(this.eventoId, 'Lote', l.preco, l.total).id);
  }

  loteDoItem(it) {
    return this.loteIds[it.indiceLote % this.loteIds.length];
  }

  reservar(lista) {
    const reserva = this.servico.criarReserva(this.eventoId);
    for (const it of lista) {
      this.servico.adicionarItem(reserva.id, this.loteDoItem(it), it.quantidade);
    }
    return reserva;
  }

  cadastrar(c, codigo) {
    this.servico.cadastrarCupom(codigo, c.tipo, c.valor, c.minimo, c.maximo, deslocar(c.validadeOffset));
    return codigo;
  }

  disponibilidades() {
    return this.loteIds.map((id) => this.servico.buscarLote(id).quantidadeDisponivel);
  }

  pedidoPorLote(lista) {
    const pedido = this.loteIds.map(() => 0);
    for (const it of lista) {
      pedido[it.indiceLote % this.loteIds.length] += it.quantidade;
    }
    return pedido;
  }

  lote(i) {
    return this.servico.buscarLote(this.loteIds[i]);
  }
}

function verificar(condicao, mensagem) {
  if (!condicao) {
    throw new Error(mensagem);
  }
}

module.exports = { fc, HOJE, lote, item, itens, cenario, cupom, Montado, verificar };
