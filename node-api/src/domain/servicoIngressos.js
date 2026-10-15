'use strict';

const calculadora = require('./calculadoraPreco');
const {
  StatusEvento,
  StatusReserva,
  TipoCupom,
  RegraNegocioError,
  Evento,
  Lote,
  Cupom,
  Reserva,
} = require('./modelos');

/**
 * Serviço de domínio com persistência em memória. Implementa as regras R1–R20 do SPEC.md.
 * É a única porta de entrada usada pela camada REST e pelos testes.
 */
class ServicoIngressos {
  constructor() {
    this.eventos = new Map();
    this.lotes = new Map();
    this.cupons = new Map();
    this.reservas = new Map();
    this.sequencia = 0;
  }

  novoId(prefixo) {
    this.sequencia++;
    return `${prefixo}-${this.sequencia}`;
  }

  // ---------------------------------------------------------------- eventos

  /** R1, R2. */
  criarEvento(nome, data, local, capacidade) {
    if (nome == null || nome.trim() === '' || capacidade <= 0) {
      throw new RegraNegocioError('DADOS_INVALIDOS');
    }
    const evento = new Evento(this.novoId('EVT'), nome, data, local, capacidade);
    this.eventos.set(evento.id, evento);
    return evento;
  }

  buscarEvento(id) {
    const evento = this.eventos.get(id);
    if (evento === undefined) {
      throw new RegraNegocioError('EVENTO_NAO_ENCONTRADO');
    }
    return evento;
  }

  alterarStatusEvento(id, status) {
    const evento = this.buscarEvento(id);
    evento.status = status;
    return evento;
  }

  // ---------------------------------------------------------------- lotes

  /** R3, R4, R5. */
  criarLote(eventoId, nome, precoCentavos, quantidadeTotal) {
    const evento = this.buscarEvento(eventoId);
    if (precoCentavos < 0 || quantidadeTotal <= 0) {
      throw new RegraNegocioError('DADOS_INVALIDOS');
    }
    let ocupado = 0;
    for (const lote of this.lotes.values()) {
      if (lote.eventoId === eventoId) {
        ocupado += lote.quantidadeTotal;
      }
    }
    if (ocupado + quantidadeTotal > evento.capacidade) {
      throw new RegraNegocioError('CAPACIDADE_EXCEDIDA');
    }
    const lote = new Lote(this.novoId('LOT'), eventoId, nome, precoCentavos, quantidadeTotal);
    this.lotes.set(lote.id, lote);
    return lote;
  }

  buscarLote(id) {
    const lote = this.lotes.get(id);
    if (lote === undefined) {
      throw new RegraNegocioError('LOTE_NAO_ENCONTRADO');
    }
    return lote;
  }

  // ---------------------------------------------------------------- cupons

  /** R9. */
  cadastrarCupom(codigo, tipo, valor, minimoCentavos, maximoDescontoCentavos, validoAte) {
    const valorValido = tipo === TipoCupom.PERCENTUAL ? valor >= 1 && valor <= 100 : valor > 0;
    const maximoValido = maximoDescontoCentavos === null || maximoDescontoCentavos > 0;
    if (codigo == null || codigo.trim() === '' || !valorValido || minimoCentavos < 0 || !maximoValido) {
      throw new RegraNegocioError('DADOS_INVALIDOS');
    }
    const cupom = new Cupom(codigo, tipo, valor, minimoCentavos, maximoDescontoCentavos, validoAte);
    this.cupons.set(codigo, cupom);
    return cupom;
  }

  // ---------------------------------------------------------------- reservas

  /** R6. */
  criarReserva(eventoId) {
    const evento = this.buscarEvento(eventoId);
    exigirEventoAtivo(evento);
    const reserva = new Reserva(this.novoId('RES'), eventoId);
    this.reservas.set(reserva.id, reserva);
    return reserva;
  }

  buscarReserva(id) {
    const reserva = this.reservas.get(id);
    if (reserva === undefined) {
      throw new RegraNegocioError('RESERVA_NAO_ENCONTRADA');
    }
    return reserva;
  }

  /** R7. */
  adicionarItem(reservaId, loteId, quantidade) {
    const reserva = this.buscarReserva(reservaId);
    exigirStatus(reserva, StatusReserva.CRIADA);
    exigirEventoAtivo(this.buscarEvento(reserva.eventoId));
    if (quantidade <= 0) {
      throw new RegraNegocioError('QUANTIDADE_INVALIDA');
    }
    const lote = this.buscarLote(loteId);
    if (lote.eventoId !== reserva.eventoId) {
      throw new RegraNegocioError('LOTE_INVALIDO');
    }
    reserva.itens.push({ loteId, quantidade });
    return reserva;
  }

  /** R10. */
  aplicarCupom(reservaId, codigo) {
    const reserva = this.buscarReserva(reservaId);
    exigirStatus(reserva, StatusReserva.CRIADA);
    reserva.codigoCupom = codigo;
    return reserva;
  }

  /** R8, R11–R13. */
  calcularTotais(reservaId, hoje) {
    const reserva = this.buscarReserva(reservaId);
    const itens = [];
    for (const item of reserva.itens) {
      itens.push({ precoCentavos: this.buscarLote(item.loteId).precoCentavos, quantidade: item.quantidade });
    }
    const cupom = reserva.codigoCupom === null ? null : this.cupons.get(reserva.codigoCupom) ?? null;
    return calculadora.calcular(itens, cupom, hoje);
  }

  /** R14, R15, R16. */
  confirmar(reservaId) {
    const reserva = this.buscarReserva(reservaId);
    exigirStatus(reserva, StatusReserva.CRIADA);
    if (reserva.itens.length === 0) {
      throw new RegraNegocioError('RESERVA_VAZIA');
    }
    exigirEventoAtivo(this.buscarEvento(reserva.eventoId));
    const pedido = quantidadesPorLote(reserva);
    for (const [loteId, quantidade] of pedido) {
      if (this.buscarLote(loteId).quantidadeDisponivel < quantidade) {
        throw new RegraNegocioError('DISPONIBILIDADE_INSUFICIENTE');
      }
    }
    for (const [loteId, quantidade] of pedido) {
      this.buscarLote(loteId).baixar(quantidade);
    }
    reserva.status = StatusReserva.CONFIRMADA;
    return reserva;
  }

  /** R18: pagamento simulado. */
  pagar(reservaId) {
    const reserva = this.buscarReserva(reservaId);
    exigirStatus(reserva, StatusReserva.CONFIRMADA);
    reserva.status = StatusReserva.PAGA;
    return reserva;
  }

  /** R17, R18. */
  cancelar(reservaId) {
    return this.encerrar(reservaId, StatusReserva.CANCELADA);
  }

  /** R17, R18. */
  expirar(reservaId) {
    return this.encerrar(reservaId, StatusReserva.EXPIRADA);
  }

  encerrar(reservaId, destino) {
    const reserva = this.buscarReserva(reservaId);
    const atual = reserva.status;
    if (atual !== StatusReserva.CRIADA && atual !== StatusReserva.CONFIRMADA) {
      throw new RegraNegocioError('TRANSICAO_INVALIDA');
    }
    if (atual === StatusReserva.CONFIRMADA) {
      for (const [loteId, quantidade] of quantidadesPorLote(reserva)) {
        this.buscarLote(loteId).devolver(quantidade);
      }
    }
    reserva.status = destino;
    return reserva;
  }
}

// ---------------------------------------------------------------- auxiliares

function quantidadesPorLote(reserva) {
  const pedido = new Map();
  for (const item of reserva.itens) {
    pedido.set(item.loteId, (pedido.get(item.loteId) ?? 0) + item.quantidade);
  }
  return pedido;
}

function exigirStatus(reserva, esperado) {
  if (reserva.status !== esperado) {
    throw new RegraNegocioError('TRANSICAO_INVALIDA');
  }
}

function exigirEventoAtivo(evento) {
  if (evento.status !== StatusEvento.ATIVO) {
    throw new RegraNegocioError('EVENTO_INDISPONIVEL');
  }
}

module.exports = { ServicoIngressos };
