package br.pucminas.tcc.ingressos.properties;

import br.pucminas.tcc.ingressos.domain.CalculadoraPreco.Totais;
import br.pucminas.tcc.ingressos.domain.Reserva;
import br.pucminas.tcc.ingressos.properties.Geradores.Cenario;
import br.pucminas.tcc.ingressos.properties.Geradores.CupomSpec;
import br.pucminas.tcc.ingressos.properties.Geradores.ItemSpec;
import br.pucminas.tcc.ingressos.properties.Geradores.Montado;
import net.jqwik.api.Arbitraries;
import net.jqwik.api.Arbitrary;
import net.jqwik.api.ForAll;
import net.jqwik.api.Property;
import net.jqwik.api.Provide;
import net.jqwik.api.constraints.IntRange;
import net.jqwik.api.constraints.LongRange;
import net.jqwik.api.constraints.Size;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

import static br.pucminas.tcc.ingressos.properties.Geradores.HOJE;
import static br.pucminas.tcc.ingressos.properties.Geradores.verificar;

/** Propriedades P1–P4 (módulos Reservas e Cupons). */
class PropriedadesPrecoTest {

    @Provide
    Arbitrary<Cenario> cenario() {
        return Geradores.cenarios();
    }

    @Provide
    Arbitrary<CupomSpec> cupom() {
        return Geradores.cupons();
    }

    @Provide
    Arbitrary<List<Integer>> chaves() {
        return Arbitraries.integers().between(0, 1000).list().ofSize(5);
    }

    /** P1 – Total não negativo, com cupom válido, inexistente ou ausente (modo 0, 1, 2). */
    @Property
    void p1TotalNaoNegativo(@ForAll("cenario") Cenario c, @ForAll("cupom") CupomSpec cupom,
                            @ForAll @IntRange(min = 0, max = 2) int modo) {
        Montado m = new Montado(c.lotes());
        Reserva r = m.reservar(c.itens());
        if (modo == 0) {
            m.servico.aplicarCupom(r.getId(), m.cadastrar(cupom, "CUPOM"));
        } else if (modo == 1) {
            m.servico.aplicarCupom(r.getId(), "INEXISTENTE");
        }
        Totais t = m.servico.calcularTotais(r.getId(), HOJE);
        verificar(t.getTotal() >= 0, "total negativo: " + t.getTotal());
    }

    /** P2 – Desconto limitado: 0 ≤ desconto ≤ subtotal e total = subtotal − desconto. */
    @Property
    void p2DescontoLimitado(@ForAll("cenario") Cenario c, @ForAll("cupom") CupomSpec cupom) {
        Montado m = new Montado(c.lotes());
        Reserva r = m.reservar(c.itens());
        m.servico.aplicarCupom(r.getId(), m.cadastrar(cupom, "CUPOM"));
        Totais t = m.servico.calcularTotais(r.getId(), HOJE);
        verificar(t.getDesconto() >= 0, "desconto negativo: " + t.getDesconto());
        verificar(t.getDesconto() <= t.getSubtotal(), "desconto acima do subtotal");
        verificar(t.getTotal() == t.getSubtotal() - t.getDesconto(), "total diferente de subtotal - desconto");
    }

    /** P3 – Comutatividade do subtotal: a ordem dos itens não altera o subtotal. */
    @Property
    void p3ComutatividadeSubtotal(@ForAll("cenario") Cenario c, @ForAll("chaves") List<Integer> chaves) {
        Montado m = new Montado(c.lotes());
        List<Integer> indices = new ArrayList<>();
        for (int i = 0; i < c.itens().size(); i++) {
            indices.add(i);
        }
        indices.sort(Comparator.comparing(chaves::get));
        List<ItemSpec> permutados = new ArrayList<>();
        for (int i : indices) {
            permutados.add(c.itens().get(i));
        }
        Reserva original = m.reservar(c.itens());
        Reserva permutada = m.reservar(permutados);
        long a = m.servico.calcularTotais(original.getId(), HOJE).getSubtotal();
        long b = m.servico.calcularTotais(permutada.getId(), HOJE).getSubtotal();
        verificar(a == b, "subtotal mudou com a ordem: " + a + " != " + b);
    }

    /** P4 – Cupom inválido neutro: inexistente (0), expirado (1) ou mínimo acima do subtotal (2). */
    @Property
    void p4CupomInvalidoNeutro(@ForAll("cenario") Cenario c, @ForAll("cupom") CupomSpec cupom,
                               @ForAll @IntRange(min = 0, max = 2) int tipoInvalido,
                               @ForAll @IntRange(min = -30, max = -1) int offsetExpirado,
                               @ForAll @LongRange(min = 1, max = 100_000) long excessoMinimo) {
        Montado m = new Montado(c.lotes());
        Reserva r = m.reservar(c.itens());
        long subtotal = m.servico.calcularTotais(r.getId(), HOJE).getSubtotal();
        String codigo;
        if (tipoInvalido == 0) {
            codigo = "INEXISTENTE";
        } else if (tipoInvalido == 1) {
            codigo = m.cadastrar(new CupomSpec(cupom.tipo(), cupom.valor(), cupom.minimo(), cupom.maximo(), offsetExpirado), "VENCIDO");
        } else {
            codigo = m.cadastrar(new CupomSpec(cupom.tipo(), cupom.valor(), subtotal + excessoMinimo, cupom.maximo(),
                    cupom.validadeOffset()), "MINIMO");
        }
        m.servico.aplicarCupom(r.getId(), codigo);
        Totais t = m.servico.calcularTotais(r.getId(), HOJE);
        verificar(t.getTotal() == subtotal, "cupom inválido alterou o total: " + t.getTotal() + " != " + subtotal);
    }
}
