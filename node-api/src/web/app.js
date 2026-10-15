'use strict';

/**
 * Camada REST fina (decisão D2): converte JSON em chamadas ao domínio e erros de regra em HTTP.
 * Não contém regra de negócio e fica fora da análise de mutação.
 */
const express = require('express');
const { ServicoIngressos } = require('../domain/servicoIngressos');
const { RegraNegocioError } = require('../domain/modelos');

function criarApp(servico = new ServicoIngressos(), relogio = () => new Date().toISOString().slice(0, 10)) {
  const app = express();
  app.use(express.json());

  const rota = (fn) => (req, res) => {
    try {
      const { status = 200, corpo } = fn(req);
      res.status(status).json(corpo);
    } catch (e) {
      if (e instanceof RegraNegocioError) {
        const http = e.codigo.endsWith('_NAO_ENCONTRADO') || e.codigo.endsWith('_NAO_ENCONTRADA') ? 404 : 422;
        res.status(http).json({ erro: e.codigo });
      } else {
        res.status(400).json({ erro: 'REQUISICAO_INVALIDA' });
      }
    }
  };

  const reservaComTotais = (reserva) => ({ ...reserva, totais: servico.calcularTotais(reserva.id, relogio()) });

  app.post('/eventos', rota((req) => {
    const { nome, data, local, capacidade } = req.body;
    return { status: 201, corpo: servico.criarEvento(nome, data, local, capacidade) };
  }));
  app.get('/eventos/:id', rota((req) => ({ corpo: servico.buscarEvento(req.params.id) })));
  app.patch('/eventos/:id/status', rota((req) => ({ corpo: servico.alterarStatusEvento(req.params.id, req.body.status) })));

  app.post('/eventos/:id/lotes', rota((req) => {
    const { nome, precoCentavos, quantidadeTotal } = req.body;
    return { status: 201, corpo: servico.criarLote(req.params.id, nome, precoCentavos, quantidadeTotal) };
  }));
  app.get('/lotes/:id', rota((req) => ({ corpo: servico.buscarLote(req.params.id) })));

  app.post('/cupons', rota((req) => {
    const { codigo, tipo, valor, minimoCentavos = 0, maximoDescontoCentavos = null, validoAte } = req.body;
    return { status: 201, corpo: servico.cadastrarCupom(codigo, tipo, valor, minimoCentavos, maximoDescontoCentavos, validoAte) };
  }));

  app.post('/reservas', rota((req) => ({ status: 201, corpo: reservaComTotais(servico.criarReserva(req.body.eventoId)) })));
  app.get('/reservas/:id', rota((req) => ({ corpo: reservaComTotais(servico.buscarReserva(req.params.id)) })));
  app.post('/reservas/:id/itens', rota((req) => ({
    corpo: reservaComTotais(servico.adicionarItem(req.params.id, req.body.loteId, req.body.quantidade)),
  })));
  app.put('/reservas/:id/cupom', rota((req) => ({ corpo: reservaComTotais(servico.aplicarCupom(req.params.id, req.body.codigo)) })));
  app.post('/reservas/:id/confirmacao', rota((req) => ({ corpo: reservaComTotais(servico.confirmar(req.params.id)) })));
  app.post('/reservas/:id/pagamento', rota((req) => ({ corpo: reservaComTotais(servico.pagar(req.params.id)) })));
  app.post('/reservas/:id/cancelamento', rota((req) => ({ corpo: reservaComTotais(servico.cancelar(req.params.id)) })));
  app.post('/reservas/:id/expiracao', rota((req) => ({ corpo: reservaComTotais(servico.expirar(req.params.id)) })));

  return app;
}

module.exports = { criarApp };
