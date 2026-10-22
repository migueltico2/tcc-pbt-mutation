'use strict';

/** Suíte forte, P13–P16 (Reservas, Cupons, Disponibilidade e Status): pré-condições das operações. */
const {
  fc,
  HOJE,
  cenario,
  Montado,
  verificar,
  codigoDoErro,
  levarAoStatus,
  STATUS_RESERVA,
  STATUS_EVENTO,
} = require('./apoio');

describe('forte: reservas', () => {
  test('P13 itens da reserva', () => {
    // R7: ordem de verificação do SPEC (status, quantidade, lote do evento); item aceito é registrado.
    fc.assert(
      fc.property(
        cenario,
        fc.constantFrom('CRIADA', 'CONFIRMADA', 'CANCELADA'),
        fc.integer({ min: -3, max: 10 }),
        fc.boolean(),
        fc.integer({ min: 0, max: 3 }),
        (c, status, quantidade, deOutroEvento, indice) => {
          const m = new Montado(c.lotes);
          const outro = m.servico.criarEvento('Outro', '2026-12-01', 'BH', 100).id;
          const loteOutro = m.servico.criarLote(outro, 'Outro', 500, 10).id;
          const r = m.servico.criarReserva(m.eventoId);
          m.servico.adicionarItem(r.id, m.loteIds[0], 1);
          levarAoStatus(m.servico, r.id, status);
          const alvo = deOutroEvento ? loteOutro : m.loteIds[indice % m.loteIds.length];
          const antes = m.servico.buscarReserva(r.id).itens.length;
          const erro = codigoDoErro(() => m.servico.adicionarItem(r.id, alvo, quantidade));
          let esperado = null;
          if (status !== 'CRIADA') {
            esperado = 'TRANSICAO_INVALIDA';
          } else if (quantidade <= 0) {
            esperado = 'QUANTIDADE_INVALIDA';
          } else if (deOutroEvento) {
            esperado = 'LOTE_INVALIDO';
          }
          verificar(erro === esperado, `esperado ${esperado}, obtido ${erro}`);
          const depois = m.servico.buscarReserva(r.id).itens;
          if (esperado === null) {
            verificar(depois.length === antes + 1, 'item aceito não foi registrado');
            const ultimo = depois[depois.length - 1];
            verificar(ultimo.loteId === alvo && ultimo.quantidade === quantidade, 'item registrado com dados errados');
          } else {
            verificar(depois.length === antes, 'item recusado alterou a reserva');
          }
        },
      ),
    );
  });

  test('P14 evento inativo e reserva vazia', () => {
    // R2, R6 e R14: só evento ATIVO aceita reservas, itens e confirmações; reserva vazia não confirma.
    fc.assert(
      fc.property(
        cenario,
        fc.constantFrom(...STATUS_EVENTO),
        fc.constantFrom('CRIAR_RESERVA', 'ADICIONAR', 'CONFIRMAR'),
        fc.boolean(),
        (c, statusEvento, op, comItens) => {
          const m = new Montado(c.lotes);
          const r = m.servico.criarReserva(m.eventoId);
          if (comItens) {
            m.servico.adicionarItem(r.id, m.loteIds[0], 1);
          }
          m.servico.alterarStatusEvento(m.eventoId, statusEvento);
          const ativo = statusEvento === 'ATIVO';
          const antes = m.disponibilidades();
          if (op === 'CRIAR_RESERVA') {
            let nova = null;
            const erro = codigoDoErro(() => {
              nova = m.servico.criarReserva(m.eventoId);
            });
            verificar(erro === (ativo ? null : 'EVENTO_INDISPONIVEL'), `criarReserva com evento ${statusEvento}: ${erro}`);
            if (ativo) {
              const lida = m.servico.buscarReserva(nova.id);
              verificar(lida.status === 'CRIADA' && lida.itens.length === 0, 'reserva não nasceu CRIADA e vazia');
              verificar(lida.eventoId === m.eventoId && lida.codigoCupom === null, 'reserva nasceu com dados errados');
            }
          } else if (op === 'ADICIONAR') {
            const erro = codigoDoErro(() => m.servico.adicionarItem(r.id, m.loteIds[0], 1));
            verificar(erro === (ativo ? null : 'EVENTO_INDISPONIVEL'), `adicionarItem com evento ${statusEvento}: ${erro}`);
          } else {
            const erro = codigoDoErro(() => m.servico.confirmar(r.id));
            let esperado = null;
            if (!comItens) {
              esperado = 'RESERVA_VAZIA';
            } else if (!ativo) {
              esperado = 'EVENTO_INDISPONIVEL';
            }
            verificar(erro === esperado, `confirmar (itens=${comItens}, evento ${statusEvento}): esperado ${esperado}, obtido ${erro}`);
            const status = m.servico.buscarReserva(r.id).status;
            verificar(status === (esperado === null ? 'CONFIRMADA' : 'CRIADA'), `status após confirmar: ${status}`);
            if (esperado !== null) {
              verificar(m.disponibilidades().every((v, i) => v === antes[i]), 'confirmação recusada alterou lotes');
            }
          }
        },
      ),
    );
  });

  test('P15 cupom so em reserva criada', () => {
    // R10: aplicar cupom só em reserva CRIADA; código inexistente é aceito e guardado.
    fc.assert(
      fc.property(
        cenario,
        fc.constantFrom(...STATUS_RESERVA),
        fc.constantFrom('CUPOM', 'NAO_EXISTE'),
        (c, status, codigo) => {
          const m = new Montado(c.lotes);
          m.servico.cadastrarCupom('CUPOM', 'FIXO', 100, 0, null, '2026-12-01');
          const r = m.servico.criarReserva(m.eventoId);
          m.servico.adicionarItem(r.id, m.loteIds[0], 1);
          levarAoStatus(m.servico, r.id, status);
          const erro = codigoDoErro(() => m.servico.aplicarCupom(r.id, codigo));
          const lida = m.servico.buscarReserva(r.id);
          if (status === 'CRIADA') {
            verificar(erro === null, `aplicar cupom em reserva CRIADA falhou: ${erro}`);
            verificar(lida.codigoCupom === codigo, 'código do cupom não foi guardado');
          } else {
            verificar(erro === 'TRANSICAO_INVALIDA', `aplicar cupom em ${status}: ${erro}`);
            verificar(lida.codigoCupom === null, 'cupom recusado alterou a reserva');
          }
          verificar(lida.status === status, 'aplicar cupom alterou o status');
          verificar(m.servico.calcularTotais(r.id, HOJE).total >= 0, 'total negativo');
        },
      ),
    );
  });

  test('P16 entidade inexistente', () => {
    // R20: toda operação sobre id inexistente falha com o código da entidade; ids existentes são encontrados.
    const OPERACOES = [
      ['buscarEvento', 'EVENTO_NAO_ENCONTRADO'],
      ['alterarStatusEvento', 'EVENTO_NAO_ENCONTRADO'],
      ['criarLote', 'EVENTO_NAO_ENCONTRADO'],
      ['criarReserva', 'EVENTO_NAO_ENCONTRADO'],
      ['buscarLote', 'LOTE_NAO_ENCONTRADO'],
      ['adicionarItemLote', 'LOTE_NAO_ENCONTRADO'],
      ['buscarReserva', 'RESERVA_NAO_ENCONTRADA'],
      ['adicionarItem', 'RESERVA_NAO_ENCONTRADA'],
      ['aplicarCupom', 'RESERVA_NAO_ENCONTRADA'],
      ['calcularTotais', 'RESERVA_NAO_ENCONTRADA'],
      ['confirmar', 'RESERVA_NAO_ENCONTRADA'],
      ['pagar', 'RESERVA_NAO_ENCONTRADA'],
      ['cancelar', 'RESERVA_NAO_ENCONTRADA'],
      ['expirar', 'RESERVA_NAO_ENCONTRADA'],
    ];
    fc.assert(
      fc.property(cenario, fc.integer({ min: 0, max: OPERACOES.length - 1 }), fc.integer({ min: 1000, max: 9999 }), (c, i, n) => {
        const m = new Montado(c.lotes);
        const r = m.servico.criarReserva(m.eventoId);
        const s = m.servico;
        const [op, esperado] = OPERACOES[i];
        const chamadas = {
          buscarEvento: () => s.buscarEvento(`EVT-${n}`),
          alterarStatusEvento: () => s.alterarStatusEvento(`EVT-${n}`, 'CANCELADO'),
          criarLote: () => s.criarLote(`EVT-${n}`, 'Lote', 100, 1),
          criarReserva: () => s.criarReserva(`EVT-${n}`),
          buscarLote: () => s.buscarLote(`LOT-${n}`),
          adicionarItemLote: () => s.adicionarItem(r.id, `LOT-${n}`, 1),
          buscarReserva: () => s.buscarReserva(`RES-${n}`),
          adicionarItem: () => s.adicionarItem(`RES-${n}`, m.loteIds[0], 1),
          aplicarCupom: () => s.aplicarCupom(`RES-${n}`, 'CUPOM'),
          calcularTotais: () => s.calcularTotais(`RES-${n}`, HOJE),
          confirmar: () => s.confirmar(`RES-${n}`),
          pagar: () => s.pagar(`RES-${n}`),
          cancelar: () => s.cancelar(`RES-${n}`),
          expirar: () => s.expirar(`RES-${n}`),
        };
        const erro = codigoDoErro(chamadas[op]);
        verificar(erro === esperado, `${op} com id inexistente: esperado ${esperado}, obtido ${erro}`);
        verificar(s.buscarEvento(m.eventoId).id === m.eventoId, 'evento existente não encontrado');
        verificar(s.buscarLote(m.loteIds[0]).id === m.loteIds[0], 'lote existente não encontrado');
        verificar(s.buscarReserva(r.id).id === r.id, 'reserva existente não encontrada');
      }),
    );
  });
});
