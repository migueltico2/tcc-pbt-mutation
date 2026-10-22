package br.pucminas.tcc.ingressos.properties;

import br.pucminas.tcc.ingressos.domain.RegraNegocioException;
import br.pucminas.tcc.ingressos.domain.ServicoIngressos;
import br.pucminas.tcc.ingressos.properties.Geradores.CupomSpec;
import br.pucminas.tcc.ingressos.properties.Geradores.ItemSpec;
import br.pucminas.tcc.ingressos.properties.Geradores.LoteSpec;
import net.jqwik.api.Arbitraries;
import net.jqwik.api.Arbitrary;
import net.jqwik.api.Combinators;

import java.util.List;

/**
 * Apoio da suíte forte (P9–P17): geradores adicionais e modelos de referência derivados do SPEC.md.
 * As faixas são idênticas às do node-api (test/properties/fortes/apoio.js). Nomes de tipos e
 * status são comparados com os nomes do SPEC (contrato), não com as constantes da implementação.
 */
final class ApoioForte {

    private ApoioForte() {
    }

    static final List<String> STATUS_RESERVA = List.of("CRIADA", "CONFIRMADA", "PAGA", "CANCELADA", "EXPIRADA");
    static final List<String> STATUS_EVENTO = List.of("ATIVO", "CANCELADO", "ENCERRADO");

    /** Executa a ação e devolve o código do erro de negócio, ou null se não houve erro. Outros erros sobem. */
    static String codigoDoErro(Runnable acao) {
        try {
            acao.run();
            return null;
        } catch (RegraNegocioException e) {
            return e.getCodigo();
        }
    }

    // ---------------------------------------------------------------- modelos de referência (SPEC)

    record Preco(long subtotal, long desconto, long total) { }

    /** R8, R11–R13. cupom null representa ausência de cupom ou código inexistente. */
    static Preco precoEsperado(List<LoteSpec> lotes, List<ItemSpec> itens, CupomSpec c) {
        long subtotal = 0;
        for (ItemSpec it : itens) {
            subtotal += lotes.get(it.indiceLote() % lotes.size()).preco() * it.quantidade();
        }
        long desconto = 0;
        boolean valido = c != null && c.validadeOffset() >= 0 && subtotal >= c.minimo();
        if (valido) {
            long bruto = c.tipo().name().equals("PERCENTUAL") ? Math.floorDiv(subtotal * c.valor(), 100) : c.valor();
            if (c.maximo() != null) {
                bruto = Math.min(bruto, c.maximo());
            }
            desconto = Math.min(bruto, subtotal);
        }
        return new Preco(subtotal, desconto, subtotal - desconto);
    }

    record EventoBruto(String nome, int capacidade) { }

    record LoteBruto(long preco, int total) { }

    record CadastroLotes(int capacidade, int outroTotal, List<LoteBruto> lotes) { }

    record CupomBruto(String codigo, String tipo, long valor, long minimo, Long maximo) { }

    record OperacaoEstoque(int reserva, String op) { }

    /** R9. */
    static boolean cupomValido(CupomBruto c) {
        boolean valorOk = c.tipo().equals("PERCENTUAL") ? c.valor() >= 1 && c.valor() <= 100 : c.valor() > 0;
        return c.codigo() != null && !c.codigo().isBlank() && valorOk && c.minimo() >= 0
                && (c.maximo() == null || c.maximo() > 0);
    }

    /** R18: status de destino de cada operação, ou null se a transição é inválida. */
    static String destino(String status, String op) {
        boolean ativa = status.equals("CRIADA") || status.equals("CONFIRMADA");
        switch (op) {
            case "CONFIRMAR": return status.equals("CRIADA") ? "CONFIRMADA" : null;
            case "PAGAR": return status.equals("CONFIRMADA") ? "PAGA" : null;
            case "CANCELAR": return ativa ? "CANCELADA" : null;
            case "EXPIRAR": return ativa ? "EXPIRADA" : null;
            default: throw new IllegalArgumentException("operação desconhecida: " + op);
        }
    }

    /** Leva uma reserva recém-criada (com itens) ao status pedido usando as operações da API. */
    static void levarAoStatus(ServicoIngressos s, String reservaId, String status) {
        switch (status) {
            case "CRIADA": break;
            case "CONFIRMADA": s.confirmar(reservaId); break;
            case "PAGA": s.confirmar(reservaId); s.pagar(reservaId); break;
            case "CANCELADA": s.cancelar(reservaId); break;
            case "EXPIRADA": s.expirar(reservaId); break;
            default: throw new IllegalArgumentException(status);
        }
    }

    // ---------------------------------------------------------------- geradores

    static Arbitrary<EventoBruto> eventos() {
        return Combinators.combine(
                Arbitraries.of("", "   ", "Show", null),
                Arbitraries.integers().between(-5, 300)).as(EventoBruto::new);
    }

    static Arbitrary<CadastroLotes> cadastrosLotes() {
        Arbitrary<LoteBruto> lote = Combinators.combine(
                Arbitraries.longs().between(-50, 100_000),
                Arbitraries.integers().between(-3, 80)).as(LoteBruto::new);
        return Combinators.combine(
                Arbitraries.integers().between(1, 200),
                Arbitraries.integers().between(1, 50),
                lote.list().ofMinSize(1).ofMaxSize(6)).as(CadastroLotes::new);
    }

    static Arbitrary<CupomBruto> cuponsBrutos() {
        return Arbitraries.of("PERCENTUAL", "FIXO").flatMap(tipo -> Combinators.combine(
                Arbitraries.of("", " ", "C1", null),
                tipo.equals("PERCENTUAL") ? Arbitraries.longs().between(-5, 110) : Arbitraries.longs().between(-5, 60_000),
                Arbitraries.longs().between(-5, 1000),
                Arbitraries.longs().between(-5, 1000).injectNull(0.25)
        ).as((codigo, valor, minimo, maximo) -> new CupomBruto(codigo, tipo, valor, minimo, maximo)));
    }

    static Arbitrary<OperacaoEstoque> operacoesEstoque() {
        return Combinators.combine(
                Arbitraries.integers().between(0, 3),
                Arbitraries.of("CONFIRMAR", "CANCELAR", "EXPIRAR", "PAGAR")).as(OperacaoEstoque::new);
    }
}
