package br.pucminas.tcc.ingressos.properties;

import br.pucminas.tcc.ingressos.domain.Modelos.StatusEvento;
import br.pucminas.tcc.ingressos.domain.Modelos.TipoCupom;
import br.pucminas.tcc.ingressos.domain.Reserva;
import br.pucminas.tcc.ingressos.domain.ServicoIngressos;
import br.pucminas.tcc.ingressos.properties.Geradores.Cenario;
import br.pucminas.tcc.ingressos.properties.Geradores.Montado;
import net.jqwik.api.Arbitraries;
import net.jqwik.api.Arbitrary;
import net.jqwik.api.ForAll;
import net.jqwik.api.Property;
import net.jqwik.api.Provide;
import net.jqwik.api.constraints.IntRange;

import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.Objects;

import static br.pucminas.tcc.ingressos.properties.ApoioForte.codigoDoErro;
import static br.pucminas.tcc.ingressos.properties.Geradores.HOJE;
import static br.pucminas.tcc.ingressos.properties.Geradores.verificar;

/** Suíte forte, P13–P16 (Reservas, Cupons, Disponibilidade e Status): pré-condições das operações. */
class PropriedadesForteReservasTest {

    @Provide
    Arbitrary<Cenario> cenario() {
        return Geradores.cenarios();
    }

    @Provide
    Arbitrary<String> statusItem() {
        return Arbitraries.of("CRIADA", "CONFIRMADA", "CANCELADA");
    }

    @Provide
    Arbitrary<String> statusReserva() {
        return Arbitraries.of(ApoioForte.STATUS_RESERVA);
    }

    @Provide
    Arbitrary<String> statusEvento() {
        return Arbitraries.of(ApoioForte.STATUS_EVENTO);
    }

    @Provide
    Arbitrary<String> operacaoEvento() {
        return Arbitraries.of("CRIAR_RESERVA", "ADICIONAR", "CONFIRMAR");
    }

    @Provide
    Arbitrary<String> codigoCupom() {
        return Arbitraries.of("CUPOM", "NAO_EXISTE");
    }

    /** P13 – R7: ordem de verificação do SPEC (status, quantidade, lote do evento); item aceito é registrado. */
    @Property
    void p13ItensDaReserva(@ForAll("cenario") Cenario c, @ForAll("statusItem") String status,
                           @ForAll @IntRange(min = -3, max = 10) int quantidade, @ForAll boolean deOutroEvento,
                           @ForAll @IntRange(min = 0, max = 3) int indice) {
        Montado m = new Montado(c.lotes());
        String outro = m.servico.criarEvento("Outro", "2026-12-01", "BH", 100).getId();
        String loteOutro = m.servico.criarLote(outro, "Outro", 500, 10).getId();
        Reserva r = m.servico.criarReserva(m.eventoId);
        m.servico.adicionarItem(r.getId(), m.loteIds.get(0), 1);
        ApoioForte.levarAoStatus(m.servico, r.getId(), status);
        String alvo = deOutroEvento ? loteOutro : m.loteIds.get(indice % m.loteIds.size());
        int antes = m.servico.buscarReserva(r.getId()).getItens().size();
        String erro = codigoDoErro(() -> m.servico.adicionarItem(r.getId(), alvo, quantidade));
        String esperado = null;
        if (!status.equals("CRIADA")) {
            esperado = "TRANSICAO_INVALIDA";
        } else if (quantidade <= 0) {
            esperado = "QUANTIDADE_INVALIDA";
        } else if (deOutroEvento) {
            esperado = "LOTE_INVALIDO";
        }
        verificar(Objects.equals(erro, esperado), "esperado " + esperado + ", obtido " + erro);
        List<Reserva.Item> depois = m.servico.buscarReserva(r.getId()).getItens();
        if (esperado == null) {
            verificar(depois.size() == antes + 1, "item aceito não foi registrado");
            Reserva.Item ultimo = depois.get(depois.size() - 1);
            verificar(ultimo.getLoteId().equals(alvo) && ultimo.getQuantidade() == quantidade, "item registrado com dados errados");
        } else {
            verificar(depois.size() == antes, "item recusado alterou a reserva");
        }
    }

    /** P14 – R2, R6 e R14: só evento ATIVO aceita reservas, itens e confirmações; reserva vazia não confirma. */
    @Property
    void p14EventoInativoEReservaVazia(@ForAll("cenario") Cenario c, @ForAll("statusEvento") String statusEvento,
                                       @ForAll("operacaoEvento") String op, @ForAll boolean comItens) {
        Montado m = new Montado(c.lotes());
        Reserva r = m.servico.criarReserva(m.eventoId);
        if (comItens) {
            m.servico.adicionarItem(r.getId(), m.loteIds.get(0), 1);
        }
        m.servico.alterarStatusEvento(m.eventoId, StatusEvento.valueOf(statusEvento));
        boolean ativo = statusEvento.equals("ATIVO");
        int[] antes = m.disponibilidades();
        if (op.equals("CRIAR_RESERVA")) {
            Reserva[] nova = new Reserva[1];
            String erro = codigoDoErro(() -> nova[0] = m.servico.criarReserva(m.eventoId));
            verificar(Objects.equals(erro, ativo ? null : "EVENTO_INDISPONIVEL"), "criarReserva com evento " + statusEvento + ": " + erro);
            if (ativo) {
                Reserva lida = m.servico.buscarReserva(nova[0].getId());
                verificar(lida.getStatus().name().equals("CRIADA") && lida.getItens().isEmpty(), "reserva não nasceu CRIADA e vazia");
                verificar(lida.getEventoId().equals(m.eventoId) && lida.getCodigoCupom() == null, "reserva nasceu com dados errados");
            }
        } else if (op.equals("ADICIONAR")) {
            String erro = codigoDoErro(() -> m.servico.adicionarItem(r.getId(), m.loteIds.get(0), 1));
            verificar(Objects.equals(erro, ativo ? null : "EVENTO_INDISPONIVEL"), "adicionarItem com evento " + statusEvento + ": " + erro);
        } else {
            String erro = codigoDoErro(() -> m.servico.confirmar(r.getId()));
            String esperado = null;
            if (!comItens) {
                esperado = "RESERVA_VAZIA";
            } else if (!ativo) {
                esperado = "EVENTO_INDISPONIVEL";
            }
            verificar(Objects.equals(erro, esperado),
                    "confirmar (itens=" + comItens + ", evento " + statusEvento + "): esperado " + esperado + ", obtido " + erro);
            String status = m.servico.buscarReserva(r.getId()).getStatus().name();
            verificar(status.equals(esperado == null ? "CONFIRMADA" : "CRIADA"), "status após confirmar: " + status);
            if (esperado != null) {
                verificar(Arrays.equals(m.disponibilidades(), antes), "confirmação recusada alterou lotes");
            }
        }
    }

    /** P15 – R10: aplicar cupom só em reserva CRIADA; código inexistente é aceito e guardado. */
    @Property
    void p15CupomSoEmReservaCriada(@ForAll("cenario") Cenario c, @ForAll("statusReserva") String status,
                                   @ForAll("codigoCupom") String codigo) {
        Montado m = new Montado(c.lotes());
        m.servico.cadastrarCupom("CUPOM", TipoCupom.FIXO, 100, 0, null, "2026-12-01");
        Reserva r = m.servico.criarReserva(m.eventoId);
        m.servico.adicionarItem(r.getId(), m.loteIds.get(0), 1);
        ApoioForte.levarAoStatus(m.servico, r.getId(), status);
        String erro = codigoDoErro(() -> m.servico.aplicarCupom(r.getId(), codigo));
        Reserva lida = m.servico.buscarReserva(r.getId());
        if (status.equals("CRIADA")) {
            verificar(erro == null, "aplicar cupom em reserva CRIADA falhou: " + erro);
            verificar(codigo.equals(lida.getCodigoCupom()), "código do cupom não foi guardado");
        } else {
            verificar("TRANSICAO_INVALIDA".equals(erro), "aplicar cupom em " + status + ": " + erro);
            verificar(lida.getCodigoCupom() == null, "cupom recusado alterou a reserva");
        }
        verificar(lida.getStatus().name().equals(status), "aplicar cupom alterou o status");
        verificar(m.servico.calcularTotais(r.getId(), HOJE).getTotal() >= 0, "total negativo");
    }

    /** Operações sobre id inexistente e o código esperado (R20). */
    static final List<Map.Entry<String, String>> OPERACOES = List.of(
            Map.entry("buscarEvento", "EVENTO_NAO_ENCONTRADO"),
            Map.entry("alterarStatusEvento", "EVENTO_NAO_ENCONTRADO"),
            Map.entry("criarLote", "EVENTO_NAO_ENCONTRADO"),
            Map.entry("criarReserva", "EVENTO_NAO_ENCONTRADO"),
            Map.entry("buscarLote", "LOTE_NAO_ENCONTRADO"),
            Map.entry("adicionarItemLote", "LOTE_NAO_ENCONTRADO"),
            Map.entry("buscarReserva", "RESERVA_NAO_ENCONTRADA"),
            Map.entry("adicionarItem", "RESERVA_NAO_ENCONTRADA"),
            Map.entry("aplicarCupom", "RESERVA_NAO_ENCONTRADA"),
            Map.entry("calcularTotais", "RESERVA_NAO_ENCONTRADA"),
            Map.entry("confirmar", "RESERVA_NAO_ENCONTRADA"),
            Map.entry("pagar", "RESERVA_NAO_ENCONTRADA"),
            Map.entry("cancelar", "RESERVA_NAO_ENCONTRADA"),
            Map.entry("expirar", "RESERVA_NAO_ENCONTRADA"));

    /** P16 – R20: toda operação sobre id inexistente falha com o código da entidade; ids existentes são encontrados. */
    @Property
    void p16EntidadeInexistente(@ForAll("cenario") Cenario c, @ForAll @IntRange(min = 0, max = 13) int i,
                                @ForAll @IntRange(min = 1000, max = 9999) int n) {
        Montado m = new Montado(c.lotes());
        Reserva r = m.servico.criarReserva(m.eventoId);
        ServicoIngressos s = m.servico;
        String op = OPERACOES.get(i).getKey();
        String esperado = OPERACOES.get(i).getValue();
        Runnable chamada;
        switch (op) {
            case "buscarEvento": chamada = () -> s.buscarEvento("EVT-" + n); break;
            case "alterarStatusEvento": chamada = () -> s.alterarStatusEvento("EVT-" + n, StatusEvento.CANCELADO); break;
            case "criarLote": chamada = () -> s.criarLote("EVT-" + n, "Lote", 100, 1); break;
            case "criarReserva": chamada = () -> s.criarReserva("EVT-" + n); break;
            case "buscarLote": chamada = () -> s.buscarLote("LOT-" + n); break;
            case "adicionarItemLote": chamada = () -> s.adicionarItem(r.getId(), "LOT-" + n, 1); break;
            case "buscarReserva": chamada = () -> s.buscarReserva("RES-" + n); break;
            case "adicionarItem": chamada = () -> s.adicionarItem("RES-" + n, m.loteIds.get(0), 1); break;
            case "aplicarCupom": chamada = () -> s.aplicarCupom("RES-" + n, "CUPOM"); break;
            case "calcularTotais": chamada = () -> s.calcularTotais("RES-" + n, HOJE); break;
            case "confirmar": chamada = () -> s.confirmar("RES-" + n); break;
            case "pagar": chamada = () -> s.pagar("RES-" + n); break;
            case "cancelar": chamada = () -> s.cancelar("RES-" + n); break;
            case "expirar": chamada = () -> s.expirar("RES-" + n); break;
            default: throw new IllegalStateException(op);
        }
        String erro = codigoDoErro(chamada);
        verificar(esperado.equals(erro), op + " com id inexistente: esperado " + esperado + ", obtido " + erro);
        verificar(s.buscarEvento(m.eventoId).getId().equals(m.eventoId), "evento existente não encontrado");
        verificar(s.buscarLote(m.loteIds.get(0)).getId().equals(m.loteIds.get(0)), "lote existente não encontrado");
        verificar(s.buscarReserva(r.getId()).getId().equals(r.getId()), "reserva existente não encontrada");
    }
}
