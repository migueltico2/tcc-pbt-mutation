package br.pucminas.tcc.ingressos.domain;

import br.pucminas.tcc.ingressos.domain.Modelos.StatusReserva;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class Reserva {

    /** Item de reserva: lote e quantidade (R7). */
    public static final class Item {
        private final String loteId;
        private final int quantidade;

        public Item(String loteId, int quantidade) {
            this.loteId = loteId;
            this.quantidade = quantidade;
        }

        public String getLoteId() { return loteId; }
        public int getQuantidade() { return quantidade; }
    }

    private final String id;
    private final String eventoId;
    private final List<Item> itens = new ArrayList<>();
    private String codigoCupom;
    private StatusReserva status;

    public Reserva(String id, String eventoId) {
        this.id = id;
        this.eventoId = eventoId;
        this.status = StatusReserva.CRIADA;
    }

    public String getId() { return id; }
    public String getEventoId() { return eventoId; }
    public List<Item> getItens() { return Collections.unmodifiableList(itens); }
    public String getCodigoCupom() { return codigoCupom; }
    public StatusReserva getStatus() { return status; }

    void adicionarItem(Item item) { itens.add(item); }
    void setCodigoCupom(String codigoCupom) { this.codigoCupom = codigoCupom; }
    void setStatus(StatusReserva status) { this.status = status; }
}
