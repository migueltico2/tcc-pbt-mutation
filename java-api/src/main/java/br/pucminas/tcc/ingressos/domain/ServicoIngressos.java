package br.pucminas.tcc.ingressos.domain;

import br.pucminas.tcc.ingressos.domain.CalculadoraPreco.ItemPrecificado;
import br.pucminas.tcc.ingressos.domain.CalculadoraPreco.Totais;
import br.pucminas.tcc.ingressos.domain.Modelos.StatusEvento;
import br.pucminas.tcc.ingressos.domain.Modelos.StatusReserva;
import br.pucminas.tcc.ingressos.domain.Modelos.TipoCupom;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Serviço de domínio com persistência em memória. Implementa as regras R1–R20 do SPEC.md.
 * É a única porta de entrada usada pela camada REST e pelos testes.
 */
public class ServicoIngressos {

    private final Map<String, Evento> eventos = new LinkedHashMap<>();
    private final Map<String, Lote> lotes = new LinkedHashMap<>();
    private final Map<String, Cupom> cupons = new LinkedHashMap<>();
    private final Map<String, Reserva> reservas = new LinkedHashMap<>();
    private int sequencia = 0;

    private String novoId(String prefixo) {
        sequencia++;
        return prefixo + "-" + sequencia;
    }

    // ---------------------------------------------------------------- eventos

    /** R1, R2. */
    public Evento criarEvento(String nome, String data, String local, int capacidade) {
        if (nome == null || nome.isBlank() || capacidade <= 0) {
            throw new RegraNegocioException("DADOS_INVALIDOS");
        }
        Evento evento = new Evento(novoId("EVT"), nome, data, local, capacidade);
        eventos.put(evento.getId(), evento);
        return evento;
    }

    public Evento buscarEvento(String id) {
        Evento evento = eventos.get(id);
        if (evento == null) {
            throw new RegraNegocioException("EVENTO_NAO_ENCONTRADO");
        }
        return evento;
    }

    public Evento alterarStatusEvento(String id, StatusEvento status) {
        Evento evento = buscarEvento(id);
        evento.setStatus(status);
        return evento;
    }

    // ---------------------------------------------------------------- lotes

    /** R3, R4, R5. */
    public Lote criarLote(String eventoId, String nome, long precoCentavos, int quantidadeTotal) {
        Evento evento = buscarEvento(eventoId);
        if (precoCentavos < 0 || quantidadeTotal <= 0) {
            throw new RegraNegocioException("DADOS_INVALIDOS");
        }
        int ocupado = 0;
        for (Lote lote : lotes.values()) {
            if (lote.getEventoId().equals(eventoId)) {
                ocupado += lote.getQuantidadeTotal();
            }
        }
        if (ocupado + quantidadeTotal > evento.getCapacidade()) {
            throw new RegraNegocioException("CAPACIDADE_EXCEDIDA");
        }
        Lote lote = new Lote(novoId("LOT"), eventoId, nome, precoCentavos, quantidadeTotal);
        lotes.put(lote.getId(), lote);
        return lote;
    }

    public Lote buscarLote(String id) {
        Lote lote = lotes.get(id);
        if (lote == null) {
            throw new RegraNegocioException("LOTE_NAO_ENCONTRADO");
        }
        return lote;
    }

    // ---------------------------------------------------------------- cupons

    /** R9. */
    public Cupom cadastrarCupom(String codigo, TipoCupom tipo, long valor, long minimoCentavos,
                                Long maximoDescontoCentavos, String validoAte) {
        boolean valorValido = tipo == TipoCupom.PERCENTUAL ? valor >= 1 && valor <= 100 : valor > 0;
        boolean maximoValido = maximoDescontoCentavos == null || maximoDescontoCentavos > 0;
        if (codigo == null || codigo.isBlank() || !valorValido || minimoCentavos < 0 || !maximoValido) {
            throw new RegraNegocioException("DADOS_INVALIDOS");
        }
        Cupom cupom = new Cupom(codigo, tipo, valor, minimoCentavos, maximoDescontoCentavos, validoAte);
        cupons.put(codigo, cupom);
        return cupom;
    }

    // ---------------------------------------------------------------- reservas

    /** R6. */
    public Reserva criarReserva(String eventoId) {
        Evento evento = buscarEvento(eventoId);
        exigirEventoAtivo(evento);
        Reserva reserva = new Reserva(novoId("RES"), eventoId);
        reservas.put(reserva.getId(), reserva);
        return reserva;
    }

    public Reserva buscarReserva(String id) {
        Reserva reserva = reservas.get(id);
        if (reserva == null) {
            throw new RegraNegocioException("RESERVA_NAO_ENCONTRADA");
        }
        return reserva;
    }

    /** R7. */
    public Reserva adicionarItem(String reservaId, String loteId, int quantidade) {
        Reserva reserva = buscarReserva(reservaId);
        exigirStatus(reserva, StatusReserva.CRIADA);
        exigirEventoAtivo(buscarEvento(reserva.getEventoId()));
        if (quantidade <= 0) {
            throw new RegraNegocioException("QUANTIDADE_INVALIDA");
        }
        Lote lote = buscarLote(loteId);
        if (!lote.getEventoId().equals(reserva.getEventoId())) {
            throw new RegraNegocioException("LOTE_INVALIDO");
        }
        reserva.adicionarItem(new Reserva.Item(loteId, quantidade));
        return reserva;
    }

    /** R10. */
    public Reserva aplicarCupom(String reservaId, String codigo) {
        Reserva reserva = buscarReserva(reservaId);
        exigirStatus(reserva, StatusReserva.CRIADA);
        reserva.setCodigoCupom(codigo);
        return reserva;
    }

    /** R8, R11–R13. */
    public Totais calcularTotais(String reservaId, String hoje) {
        Reserva reserva = buscarReserva(reservaId);
        List<ItemPrecificado> itens = new ArrayList<>();
        for (Reserva.Item item : reserva.getItens()) {
            itens.add(new ItemPrecificado(buscarLote(item.getLoteId()).getPrecoCentavos(), item.getQuantidade()));
        }
        Cupom cupom = reserva.getCodigoCupom() == null ? null : cupons.get(reserva.getCodigoCupom());
        return CalculadoraPreco.calcular(itens, cupom, hoje);
    }

    /** R14, R15, R16. */
    public Reserva confirmar(String reservaId) {
        Reserva reserva = buscarReserva(reservaId);
        exigirStatus(reserva, StatusReserva.CRIADA);
        if (reserva.getItens().isEmpty()) {
            throw new RegraNegocioException("RESERVA_VAZIA");
        }
        exigirEventoAtivo(buscarEvento(reserva.getEventoId()));
        Map<String, Integer> pedido = quantidadesPorLote(reserva);
        for (Map.Entry<String, Integer> entrada : pedido.entrySet()) {
            if (buscarLote(entrada.getKey()).getQuantidadeDisponivel() < entrada.getValue()) {
                throw new RegraNegocioException("DISPONIBILIDADE_INSUFICIENTE");
            }
        }
        for (Map.Entry<String, Integer> entrada : pedido.entrySet()) {
            buscarLote(entrada.getKey()).baixar(entrada.getValue());
        }
        reserva.setStatus(StatusReserva.CONFIRMADA);
        return reserva;
    }

    /** R18: pagamento simulado. */
    public Reserva pagar(String reservaId) {
        Reserva reserva = buscarReserva(reservaId);
        exigirStatus(reserva, StatusReserva.CONFIRMADA);
        reserva.setStatus(StatusReserva.PAGA);
        return reserva;
    }

    /** R17, R18. */
    public Reserva cancelar(String reservaId) {
        return encerrar(reservaId, StatusReserva.CANCELADA);
    }

    /** R17, R18. */
    public Reserva expirar(String reservaId) {
        return encerrar(reservaId, StatusReserva.EXPIRADA);
    }

    private Reserva encerrar(String reservaId, StatusReserva destino) {
        Reserva reserva = buscarReserva(reservaId);
        StatusReserva atual = reserva.getStatus();
        if (atual != StatusReserva.CRIADA && atual != StatusReserva.CONFIRMADA) {
            throw new RegraNegocioException("TRANSICAO_INVALIDA");
        }
        if (atual == StatusReserva.CONFIRMADA) {
            for (Map.Entry<String, Integer> entrada : quantidadesPorLote(reserva).entrySet()) {
                buscarLote(entrada.getKey()).devolver(entrada.getValue());
            }
        }
        reserva.setStatus(destino);
        return reserva;
    }

    // ---------------------------------------------------------------- auxiliares

    private static Map<String, Integer> quantidadesPorLote(Reserva reserva) {
        Map<String, Integer> pedido = new LinkedHashMap<>();
        for (Reserva.Item item : reserva.getItens()) {
            pedido.merge(item.getLoteId(), item.getQuantidade(), Integer::sum);
        }
        return pedido;
    }

    private static void exigirStatus(Reserva reserva, StatusReserva esperado) {
        if (reserva.getStatus() != esperado) {
            throw new RegraNegocioException("TRANSICAO_INVALIDA");
        }
    }

    private static void exigirEventoAtivo(Evento evento) {
        if (evento.getStatus() != StatusEvento.ATIVO) {
            throw new RegraNegocioException("EVENTO_INDISPONIVEL");
        }
    }
}
