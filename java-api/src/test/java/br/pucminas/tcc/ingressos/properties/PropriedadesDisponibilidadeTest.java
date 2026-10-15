package br.pucminas.tcc.ingressos.properties;

import br.pucminas.tcc.ingressos.domain.RegraNegocioException;
import br.pucminas.tcc.ingressos.domain.Reserva;
import br.pucminas.tcc.ingressos.properties.Geradores.Cenario;
import br.pucminas.tcc.ingressos.properties.Geradores.ItemSpec;
import br.pucminas.tcc.ingressos.properties.Geradores.Montado;
import net.jqwik.api.Arbitrary;
import net.jqwik.api.ForAll;
import net.jqwik.api.Property;
import net.jqwik.api.Provide;

import java.util.Arrays;
import java.util.List;

import static br.pucminas.tcc.ingressos.properties.Geradores.verificar;

/** Propriedades P5–P7 (módulo Disponibilidade). */
class PropriedadesDisponibilidadeTest {

    @Provide
    Arbitrary<Cenario> cenario() {
        return Geradores.cenarios();
    }

    @Provide
    Arbitrary<List<ItemSpec>> itens() {
        return Geradores.itens().list().ofMinSize(1).ofMaxSize(5);
    }

    private static boolean tentarConfirmar(Montado m, Reserva r) {
        try {
            m.servico.confirmar(r.getId());
            return true;
        } catch (RegraNegocioException e) {
            return false;
        }
    }

    private static void disponibilidadeNoIntervalo(Montado m) {
        for (int i = 0; i < m.loteIds.size(); i++) {
            int d = m.lote(i).getQuantidadeDisponivel();
            verificar(d >= 0 && d <= m.lote(i).getQuantidadeTotal(), "disponibilidade fora de [0, total]: " + d);
        }
    }

    /** P5 – Disponibilidade não negativa após confirmações (aceitas ou recusadas) de duas reservas. */
    @Property
    void p5DisponibilidadeNaoNegativa(@ForAll("cenario") Cenario c, @ForAll("itens") List<ItemSpec> outros) {
        Montado m = new Montado(c.lotes());
        Reserva r1 = m.reservar(c.itens());
        Reserva r2 = m.reservar(outros);
        tentarConfirmar(m, r1);
        disponibilidadeNoIntervalo(m);
        tentarConfirmar(m, r2);
        disponibilidadeNoIntervalo(m);
    }

    /** P6 – Confirmação aceita reduz exatamente o pedido; confirmação recusada não altera lotes. */
    @Property
    void p6ReducaoCorreta(@ForAll("cenario") Cenario c, @ForAll("itens") List<ItemSpec> outros) {
        Montado m = new Montado(c.lotes());
        Reserva r1 = m.reservar(c.itens());
        Reserva r2 = m.reservar(outros);
        verificarReducao(m, r1, c.itens());
        verificarReducao(m, r2, outros);
    }

    private static void verificarReducao(Montado m, Reserva r, List<ItemSpec> itens) {
        int[] antes = m.disponibilidades();
        int[] pedido = m.pedidoPorLote(itens);
        boolean aceita = tentarConfirmar(m, r);
        int[] depois = m.disponibilidades();
        for (int i = 0; i < antes.length; i++) {
            int esperado = aceita ? antes[i] - pedido[i] : antes[i];
            verificar(depois[i] == esperado, "lote " + i + ": esperado " + esperado + ", obtido " + depois[i]
                    + " (confirmação " + (aceita ? "aceita" : "recusada") + ")");
        }
    }

    /** P7 – Cancelar ou expirar uma reserva confirmada devolve a disponibilidade inicial. */
    @Property
    void p7CancelamentoRestaura(@ForAll("cenario") Cenario c, @ForAll boolean expirar) {
        Montado m = new Montado(c.lotes());
        Reserva r = m.reservar(c.itens());
        int[] antes = m.disponibilidades();
        tentarConfirmar(m, r);
        if (expirar) {
            m.servico.expirar(r.getId());
        } else {
            m.servico.cancelar(r.getId());
        }
        int[] depois = m.disponibilidades();
        verificar(Arrays.equals(antes, depois),
                "disponibilidade não restaurada: " + Arrays.toString(antes) + " -> " + Arrays.toString(depois));
    }
}
