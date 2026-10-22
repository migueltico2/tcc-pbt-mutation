package br.pucminas.tcc.ingressos.properties;

import br.pucminas.tcc.ingressos.domain.CalculadoraPreco.Totais;
import br.pucminas.tcc.ingressos.domain.Reserva;
import br.pucminas.tcc.ingressos.properties.ApoioForte.Preco;
import br.pucminas.tcc.ingressos.properties.Geradores.Cenario;
import br.pucminas.tcc.ingressos.properties.Geradores.CupomSpec;
import br.pucminas.tcc.ingressos.properties.Geradores.Montado;
import net.jqwik.api.Arbitrary;
import net.jqwik.api.ForAll;
import net.jqwik.api.Property;
import net.jqwik.api.Provide;
import net.jqwik.api.constraints.IntRange;

import static br.pucminas.tcc.ingressos.properties.Geradores.HOJE;
import static br.pucminas.tcc.ingressos.properties.Geradores.verificar;

/** Suíte forte, P9 (Reservas e Cupons): oráculo exato do preço, calculado por um modelo do SPEC. */
class PropriedadesFortePrecoTest {

    @Provide
    Arbitrary<Cenario> cenario() {
        return Geradores.cenarios();
    }

    @Provide
    Arbitrary<CupomSpec> cupom() {
        return Geradores.cupons();
    }

    /** P9 – modo: 0 = cupom gerado (válido, vencido ou abaixo do mínimo), 1 = inexistente, 2 = sem cupom. */
    @Property
    void p9OraculoDePreco(@ForAll("cenario") Cenario c, @ForAll("cupom") CupomSpec cupom,
                          @ForAll @IntRange(min = 0, max = 2) int modo) {
        Montado m = new Montado(c.lotes());
        Reserva r = m.reservar(c.itens());
        if (modo == 0) {
            m.servico.aplicarCupom(r.getId(), m.cadastrar(cupom, "CUPOM"));
        } else if (modo == 1) {
            m.servico.aplicarCupom(r.getId(), "INEXISTENTE");
        }
        Preco esperado = ApoioForte.precoEsperado(c.lotes(), c.itens(), modo == 0 ? cupom : null);
        Totais t = m.servico.calcularTotais(r.getId(), HOJE);
        verificar(t.getSubtotal() == esperado.subtotal(), "subtotal " + t.getSubtotal() + " != " + esperado.subtotal());
        verificar(t.getDesconto() == esperado.desconto(), "desconto " + t.getDesconto() + " != " + esperado.desconto());
        verificar(t.getTotal() == esperado.total(), "total " + t.getTotal() + " != " + esperado.total());
    }
}
