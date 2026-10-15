package br.pucminas.tcc.ingressos.properties;

import br.pucminas.tcc.ingressos.domain.Modelos.StatusReserva;
import br.pucminas.tcc.ingressos.domain.RegraNegocioException;
import br.pucminas.tcc.ingressos.domain.Reserva;
import br.pucminas.tcc.ingressos.properties.Geradores.LoteSpec;
import br.pucminas.tcc.ingressos.properties.Geradores.Montado;
import net.jqwik.api.Arbitraries;
import net.jqwik.api.Arbitrary;
import net.jqwik.api.ForAll;
import net.jqwik.api.Property;
import net.jqwik.api.Provide;
import net.jqwik.api.constraints.IntRange;

import java.util.List;

import static br.pucminas.tcc.ingressos.properties.Geradores.verificar;

/** Propriedade P8 (módulo Status): modelo de referência da tabela de transições R18/R19. */
class PropriedadesStatusTest {

    enum Operacao { CONFIRMAR, PAGAR, CANCELAR, EXPIRAR, ADICIONAR }

    @Provide
    Arbitrary<List<Operacao>> operacoes() {
        return Arbitraries.of(Operacao.class).list().ofMinSize(1).ofMaxSize(8);
    }

    /** Modelo: status esperado após a operação, ou null se a transição é inválida. */
    static StatusReserva esperado(StatusReserva atual, Operacao op) {
        switch (op) {
            case CONFIRMAR: return atual == StatusReserva.CRIADA ? StatusReserva.CONFIRMADA : null;
            case PAGAR: return atual == StatusReserva.CONFIRMADA ? StatusReserva.PAGA : null;
            case CANCELAR:
                return atual == StatusReserva.CRIADA || atual == StatusReserva.CONFIRMADA ? StatusReserva.CANCELADA : null;
            case EXPIRAR:
                return atual == StatusReserva.CRIADA || atual == StatusReserva.CONFIRMADA ? StatusReserva.EXPIRADA : null;
            case ADICIONAR: return atual == StatusReserva.CRIADA ? StatusReserva.CRIADA : null;
            default: throw new IllegalStateException();
        }
    }

    /** P8 – Toda operação segue a tabela de transições ou é recusada sem mudar o status. */
    @Property
    void p8TransicoesValidas(@ForAll("operacoes") List<Operacao> ops, @ForAll @IntRange(min = 1, max = 10) int quantidade) {
        Montado m = new Montado(List.of(new LoteSpec(1000, 50)));
        Reserva r = m.servico.criarReserva(m.eventoId);
        m.servico.adicionarItem(r.getId(), m.loteIds.get(0), quantidade);
        for (Operacao op : ops) {
            StatusReserva antes = r.getStatus();
            StatusReserva esperado = esperado(antes, op);
            String erro = null;
            try {
                switch (op) {
                    case CONFIRMAR: m.servico.confirmar(r.getId()); break;
                    case PAGAR: m.servico.pagar(r.getId()); break;
                    case CANCELAR: m.servico.cancelar(r.getId()); break;
                    case EXPIRAR: m.servico.expirar(r.getId()); break;
                    case ADICIONAR: m.servico.adicionarItem(r.getId(), m.loteIds.get(0), 1); break;
                    default: throw new IllegalStateException();
                }
            } catch (RegraNegocioException e) {
                erro = e.getCodigo();
            }
            StatusReserva depois = m.servico.buscarReserva(r.getId()).getStatus();
            if (esperado == null) {
                verificar("TRANSICAO_INVALIDA".equals(erro), op + " a partir de " + antes + " deveria ser recusada, erro=" + erro);
                verificar(depois == antes, op + " recusada alterou o status de " + antes + " para " + depois);
            } else {
                verificar(erro == null, op + " a partir de " + antes + " deveria ser aceita, erro=" + erro);
                verificar(depois == esperado, op + " a partir de " + antes + ": esperado " + esperado + ", obtido " + depois);
            }
        }
    }
}
