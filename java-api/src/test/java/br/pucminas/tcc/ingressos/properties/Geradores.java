package br.pucminas.tcc.ingressos.properties;

import br.pucminas.tcc.ingressos.domain.Lote;
import br.pucminas.tcc.ingressos.domain.Modelos.TipoCupom;
import br.pucminas.tcc.ingressos.domain.Reserva;
import br.pucminas.tcc.ingressos.domain.ServicoIngressos;
import net.jqwik.api.Arbitraries;
import net.jqwik.api.Arbitrary;
import net.jqwik.api.Combinators;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

/**
 * Geradores de dados das propriedades. As faixas seguem a tabela "Parâmetros dos geradores"
 * do SPEC.md e são idênticas às do node-api (test/properties/geradores.js).
 */
final class Geradores {

    static final String HOJE = "2026-10-15";

    private Geradores() {
    }

    /** Especificação de lote: preço 0..100000 centavos, quantidade total 1..50. */
    record LoteSpec(long preco, int total) { }

    /** Item: índice do lote (resolvido módulo nº de lotes) e quantidade 1..10. */
    record ItemSpec(int indiceLote, int quantidade) { }

    /** Cupom gerado; validadeOffset em dias relativo a HOJE. */
    record CupomSpec(TipoCupom tipo, long valor, long minimo, Long maximo, int validadeOffset) {
        String validoAte() {
            return LocalDate.parse(HOJE).plusDays(validadeOffset).toString();
        }
    }

    /** Cenário: lotes de um evento e itens de uma reserva. */
    record Cenario(List<LoteSpec> lotes, List<ItemSpec> itens) { }

    static Arbitrary<LoteSpec> lotes() {
        return Combinators.combine(
                Arbitraries.longs().between(0, 100_000),
                Arbitraries.integers().between(1, 50)).as(LoteSpec::new);
    }

    static Arbitrary<ItemSpec> itens() {
        return Combinators.combine(
                Arbitraries.integers().between(0, 3),
                Arbitraries.integers().between(1, 10)).as(ItemSpec::new);
    }

    static Arbitrary<Cenario> cenarios() {
        return Combinators.combine(
                lotes().list().ofMinSize(1).ofMaxSize(4),
                itens().list().ofMinSize(1).ofMaxSize(5)).as(Cenario::new);
    }

    static Arbitrary<CupomSpec> cupons() {
        Arbitrary<TipoCupom> tipo = Arbitraries.of(TipoCupom.PERCENTUAL, TipoCupom.FIXO);
        return tipo.flatMap(t -> Combinators.combine(
                t == TipoCupom.PERCENTUAL ? Arbitraries.longs().between(1, 100) : Arbitraries.longs().between(1, 50_000),
                Arbitraries.longs().between(0, 200_000),
                Arbitraries.longs().between(1, 50_000).injectNull(0.25),
                Arbitraries.integers().between(-30, 30)
        ).as((valor, minimo, maximo, offset) -> new CupomSpec(t, valor, minimo, maximo, offset)));
    }

    /** Monta o cenário no serviço: evento, lotes e uma reserva com os itens. */
    static final class Montado {
        final ServicoIngressos servico = new ServicoIngressos();
        final String eventoId;
        final List<String> loteIds = new ArrayList<>();

        Montado(List<LoteSpec> lotes) {
            eventoId = servico.criarEvento("Evento", "2026-12-01", "BH", 200).getId();
            for (LoteSpec l : lotes) {
                loteIds.add(servico.criarLote(eventoId, "Lote", l.preco(), l.total()).getId());
            }
        }

        String loteDoItem(ItemSpec item) {
            return loteIds.get(item.indiceLote() % loteIds.size());
        }

        Reserva reservar(List<ItemSpec> itens) {
            Reserva reserva = servico.criarReserva(eventoId);
            for (ItemSpec item : itens) {
                servico.adicionarItem(reserva.getId(), loteDoItem(item), item.quantidade());
            }
            return reserva;
        }

        String cadastrar(CupomSpec c, String codigo) {
            servico.cadastrarCupom(codigo, c.tipo(), c.valor(), c.minimo(), c.maximo(), c.validoAte());
            return codigo;
        }

        int[] disponibilidades() {
            int[] d = new int[loteIds.size()];
            for (int i = 0; i < d.length; i++) {
                d[i] = servico.buscarLote(loteIds.get(i)).getQuantidadeDisponivel();
            }
            return d;
        }

        int[] pedidoPorLote(List<ItemSpec> itens) {
            int[] pedido = new int[loteIds.size()];
            for (ItemSpec item : itens) {
                pedido[item.indiceLote() % loteIds.size()] += item.quantidade();
            }
            return pedido;
        }

        Lote lote(int i) {
            return servico.buscarLote(loteIds.get(i));
        }
    }

    static void verificar(boolean condicao, String mensagem) {
        if (!condicao) {
            throw new AssertionError(mensagem);
        }
    }
}
