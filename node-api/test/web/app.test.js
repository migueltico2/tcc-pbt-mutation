'use strict';

/** Teste de fumaça da camada REST (fora da medição de mutação). */
const request = require('supertest');
const { criarApp } = require('../../src/web/app');

describe('API REST', () => {
  test('fluxo completo: evento, lote, cupom, reserva, confirmação e pagamento', async () => {
    const app = criarApp(undefined, () => '2026-10-15');
    const evento = await request(app).post('/eventos')
      .send({ nome: 'Show', data: '2026-12-01', local: 'BH', capacidade: 100 }).expect(201);
    const lote = await request(app).post(`/eventos/${evento.body.id}/lotes`)
      .send({ nome: 'Pista', precoCentavos: 5000, quantidadeTotal: 10 }).expect(201);
    await request(app).post('/cupons')
      .send({ codigo: 'DEZ', tipo: 'PERCENTUAL', valor: 10, validoAte: '2026-12-31' }).expect(201);
    const reserva = await request(app).post('/reservas').send({ eventoId: evento.body.id }).expect(201);
    const id = reserva.body.id;
    await request(app).post(`/reservas/${id}/itens`).send({ loteId: lote.body.id, quantidade: 2 }).expect(200);
    const comCupom = await request(app).put(`/reservas/${id}/cupom`).send({ codigo: 'DEZ' }).expect(200);
    expect(comCupom.body.totais).toEqual({ subtotal: 10000, desconto: 1000, total: 9000 });
    await request(app).post(`/reservas/${id}/confirmacao`).expect(200);
    const pago = await request(app).post(`/reservas/${id}/pagamento`).expect(200);
    expect(pago.body.status).toBe('PAGA');
    const loteDepois = await request(app).get(`/lotes/${lote.body.id}`).expect(200);
    expect(loteDepois.body.quantidadeDisponivel).toBe(8);
  });

  test('erros de regra viram 404 e 422', async () => {
    const app = criarApp();
    await request(app).get('/reservas/RES-1').expect(404, { erro: 'RESERVA_NAO_ENCONTRADA' });
    await request(app).post('/eventos').send({ nome: 'X', data: '2026-12-01', local: 'BH', capacidade: 0 })
      .expect(422, { erro: 'DADOS_INVALIDOS' });
  });
});
