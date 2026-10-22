'use strict';

/** Suíte forte, P10–P12 (Eventos, Lotes e Cupons): validação de cadastro e capacidade. */
const { ServicoIngressos } = require('../../../src/domain/servicoIngressos');
const { fc, verificar, codigoDoErro, cupomValido, evento, cadastroLotes, cupomBruto } = require('./apoio');

describe('forte: cadastro', () => {
  test('P10 validacao de evento', () => {
    // R1 e R2: dados inválidos são recusados; evento válido nasce ATIVO e é recuperável.
    fc.assert(
      fc.property(evento, (e) => {
        const s = new ServicoIngressos();
        let criado = null;
        const erro = codigoDoErro(() => {
          criado = s.criarEvento(e.nome, '2026-12-01', 'BH', e.capacidade);
        });
        const invalido = e.nome === null || e.nome.trim() === '' || e.capacidade <= 0;
        if (invalido) {
          verificar(erro === 'DADOS_INVALIDOS', `esperado DADOS_INVALIDOS, obtido ${erro}`);
          return;
        }
        verificar(erro === null, `evento válido recusado: ${erro}`);
        const lido = s.buscarEvento(criado.id);
        verificar(lido.status === 'ATIVO', `evento nasceu ${lido.status}`);
        verificar(lido.capacidade === e.capacidade && lido.nome === e.nome, 'dados do evento alterados');
      }),
    );
  });

  test('P11 validacao de lote e capacidade', () => {
    // R3, R4 e R5, com lotes de outro evento que não podem contar na capacidade.
    fc.assert(
      fc.property(cadastroLotes, (c) => {
        const s = new ServicoIngressos();
        const outro = s.criarEvento('Outro', '2026-12-01', 'BH', 200).id;
        s.criarLote(outro, 'Outro', 1000, c.outroTotal);
        const ev = s.criarEvento('Evento', '2026-12-01', 'BH', c.capacidade).id;
        let ocupado = 0;
        for (const l of c.lotes) {
          let lote = null;
          const erro = codigoDoErro(() => {
            lote = s.criarLote(ev, 'Lote', l.preco, l.total);
          });
          let esperado = null;
          if (l.preco < 0 || l.total <= 0) {
            esperado = 'DADOS_INVALIDOS';
          } else if (ocupado + l.total > c.capacidade) {
            esperado = 'CAPACIDADE_EXCEDIDA';
          }
          verificar(erro === esperado, `lote ${JSON.stringify(l)} com ocupação ${ocupado}: esperado ${esperado}, obtido ${erro}`);
          if (esperado === null) {
            ocupado += l.total;
            const lido = s.buscarLote(lote.id);
            verificar(lido.eventoId === ev, 'lote associado ao evento errado');
            verificar(lido.precoCentavos === l.preco, 'preço alterado');
            verificar(lido.quantidadeTotal === l.total, 'quantidade total alterada');
            verificar(lido.quantidadeDisponivel === l.total, 'lote não nasceu com disponibilidade = total');
          }
        }
      }),
    );
  });

  test('P12 validacao de cupom', () => {
    // R9: cadastro aceita exatamente os cupons válidos e preserva os dados.
    fc.assert(
      fc.property(cupomBruto, (c) => {
        const s = new ServicoIngressos();
        let criado = null;
        const erro = codigoDoErro(() => {
          criado = s.cadastrarCupom(c.codigo, c.tipo, c.valor, c.minimo, c.maximo, '2026-12-01');
        });
        if (!cupomValido(c)) {
          verificar(erro === 'DADOS_INVALIDOS', `cupom inválido ${JSON.stringify(c)} aceito ou erro ${erro}`);
          return;
        }
        verificar(erro === null, `cupom válido ${JSON.stringify(c)} recusado: ${erro}`);
        verificar(
          criado.codigo === c.codigo && criado.tipo === c.tipo && criado.valor === c.valor &&
            criado.minimoCentavos === c.minimo && criado.maximoDescontoCentavos === c.maximo &&
            criado.validoAte === '2026-12-01',
          'dados do cupom alterados',
        );
      }),
    );
  });
});
