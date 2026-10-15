'use strict';

/** Entidades e erro de regra de negócio do domínio (ver SPEC.md). */

const StatusEvento = Object.freeze({ ATIVO: 'ATIVO', CANCELADO: 'CANCELADO', ENCERRADO: 'ENCERRADO' });

const StatusReserva = Object.freeze({
  CRIADA: 'CRIADA',
  CONFIRMADA: 'CONFIRMADA',
  PAGA: 'PAGA',
  CANCELADA: 'CANCELADA',
  EXPIRADA: 'EXPIRADA',
});

const TipoCupom = Object.freeze({ PERCENTUAL: 'PERCENTUAL', FIXO: 'FIXO' });

class RegraNegocioError extends Error {
  constructor(codigo) {
    super(codigo);
    this.codigo = codigo;
  }
}

class Evento {
  constructor(id, nome, data, local, capacidade) {
    this.id = id;
    this.nome = nome;
    this.data = data;
    this.local = local;
    this.capacidade = capacidade;
    this.status = StatusEvento.ATIVO;
  }
}

/** Lote de ingressos de um evento (R3–R5). */
class Lote {
  constructor(id, eventoId, nome, precoCentavos, quantidadeTotal) {
    this.id = id;
    this.eventoId = eventoId;
    this.nome = nome;
    this.precoCentavos = precoCentavos;
    this.quantidadeTotal = quantidadeTotal;
    this.quantidadeDisponivel = quantidadeTotal;
  }

  /** R16: baixa a quantidade; a suficiência já foi verificada pelo serviço (R15). */
  baixar(quantidade) {
    this.quantidadeDisponivel -= quantidade;
  }

  /** R17: devolve a quantidade reservada. */
  devolver(quantidade) {
    this.quantidadeDisponivel += quantidade;
  }
}

/** Cupom de desconto (R9). maximoDescontoCentavos null significa sem teto. */
class Cupom {
  constructor(codigo, tipo, valor, minimoCentavos, maximoDescontoCentavos, validoAte) {
    this.codigo = codigo;
    this.tipo = tipo;
    this.valor = valor;
    this.minimoCentavos = minimoCentavos;
    this.maximoDescontoCentavos = maximoDescontoCentavos;
    this.validoAte = validoAte;
  }
}

class Reserva {
  constructor(id, eventoId) {
    this.id = id;
    this.eventoId = eventoId;
    this.itens = [];
    this.codigoCupom = null;
    this.status = StatusReserva.CRIADA;
  }
}

module.exports = { StatusEvento, StatusReserva, TipoCupom, RegraNegocioError, Evento, Lote, Cupom, Reserva };
