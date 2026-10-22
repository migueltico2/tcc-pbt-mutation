package br.pucminas.tcc.ingressos.properties;

import br.pucminas.tcc.ingressos.domain.Cupom;
import br.pucminas.tcc.ingressos.domain.Evento;
import br.pucminas.tcc.ingressos.domain.Lote;
import br.pucminas.tcc.ingressos.domain.Modelos.TipoCupom;
import br.pucminas.tcc.ingressos.domain.ServicoIngressos;
import br.pucminas.tcc.ingressos.properties.ApoioForte.CadastroLotes;
import br.pucminas.tcc.ingressos.properties.ApoioForte.CupomBruto;
import br.pucminas.tcc.ingressos.properties.ApoioForte.EventoBruto;
import br.pucminas.tcc.ingressos.properties.ApoioForte.LoteBruto;
import net.jqwik.api.Arbitrary;
import net.jqwik.api.ForAll;
import net.jqwik.api.Property;
import net.jqwik.api.Provide;

import java.util.Objects;

import static br.pucminas.tcc.ingressos.properties.ApoioForte.codigoDoErro;
import static br.pucminas.tcc.ingressos.properties.Geradores.verificar;

/** Suíte forte, P10–P12 (Eventos, Lotes e Cupons): validação de cadastro e capacidade. */
class PropriedadesForteCadastroTest {

    @Provide
    Arbitrary<EventoBruto> evento() {
        return ApoioForte.eventos();
    }

    @Provide
    Arbitrary<CadastroLotes> cadastroLotes() {
        return ApoioForte.cadastrosLotes();
    }

    @Provide
    Arbitrary<CupomBruto> cupomBruto() {
        return ApoioForte.cuponsBrutos();
    }

    /** P10 – R1 e R2: dados inválidos são recusados; evento válido nasce ATIVO e é recuperável. */
    @Property
    void p10ValidacaoDeEvento(@ForAll("evento") EventoBruto e) {
        ServicoIngressos s = new ServicoIngressos();
        Evento[] criado = new Evento[1];
        String erro = codigoDoErro(() -> criado[0] = s.criarEvento(e.nome(), "2026-12-01", "BH", e.capacidade()));
        boolean invalido = e.nome() == null || e.nome().isBlank() || e.capacidade() <= 0;
        if (invalido) {
            verificar("DADOS_INVALIDOS".equals(erro), "esperado DADOS_INVALIDOS, obtido " + erro);
            return;
        }
        verificar(erro == null, "evento válido recusado: " + erro);
        Evento lido = s.buscarEvento(criado[0].getId());
        verificar(lido.getStatus().name().equals("ATIVO"), "evento nasceu " + lido.getStatus());
        verificar(lido.getCapacidade() == e.capacidade() && lido.getNome().equals(e.nome()), "dados do evento alterados");
    }

    /** P11 – R3, R4 e R5, com lotes de outro evento que não podem contar na capacidade. */
    @Property
    void p11ValidacaoDeLoteECapacidade(@ForAll("cadastroLotes") CadastroLotes c) {
        ServicoIngressos s = new ServicoIngressos();
        String outro = s.criarEvento("Outro", "2026-12-01", "BH", 200).getId();
        s.criarLote(outro, "Outro", 1000, c.outroTotal());
        String ev = s.criarEvento("Evento", "2026-12-01", "BH", c.capacidade()).getId();
        int ocupado = 0;
        for (LoteBruto l : c.lotes()) {
            Lote[] lote = new Lote[1];
            String erro = codigoDoErro(() -> lote[0] = s.criarLote(ev, "Lote", l.preco(), l.total()));
            String esperado = null;
            if (l.preco() < 0 || l.total() <= 0) {
                esperado = "DADOS_INVALIDOS";
            } else if (ocupado + l.total() > c.capacidade()) {
                esperado = "CAPACIDADE_EXCEDIDA";
            }
            verificar(Objects.equals(erro, esperado),
                    "lote " + l + " com ocupação " + ocupado + ": esperado " + esperado + ", obtido " + erro);
            if (esperado == null) {
                ocupado += l.total();
                Lote lido = s.buscarLote(lote[0].getId());
                verificar(lido.getEventoId().equals(ev), "lote associado ao evento errado");
                verificar(lido.getPrecoCentavos() == l.preco(), "preço alterado");
                verificar(lido.getQuantidadeTotal() == l.total(), "quantidade total alterada");
                verificar(lido.getQuantidadeDisponivel() == l.total(), "lote não nasceu com disponibilidade = total");
            }
        }
    }

    /** P12 – R9: cadastro aceita exatamente os cupons válidos e preserva os dados. */
    @Property
    void p12ValidacaoDeCupom(@ForAll("cupomBruto") CupomBruto c) {
        ServicoIngressos s = new ServicoIngressos();
        Cupom[] criado = new Cupom[1];
        String erro = codigoDoErro(() -> criado[0] = s.cadastrarCupom(c.codigo(), TipoCupom.valueOf(c.tipo()),
                c.valor(), c.minimo(), c.maximo(), "2026-12-01"));
        if (!ApoioForte.cupomValido(c)) {
            verificar("DADOS_INVALIDOS".equals(erro), "cupom inválido " + c + " aceito ou erro " + erro);
            return;
        }
        verificar(erro == null, "cupom válido " + c + " recusado: " + erro);
        Cupom k = criado[0];
        verificar(k.getCodigo().equals(c.codigo()) && k.getTipo().name().equals(c.tipo()) && k.getValor() == c.valor()
                        && k.getMinimoCentavos() == c.minimo() && Objects.equals(k.getMaximoDescontoCentavos(), c.maximo())
                        && k.getValidoAte().equals("2026-12-01"),
                "dados do cupom alterados");
    }
}
