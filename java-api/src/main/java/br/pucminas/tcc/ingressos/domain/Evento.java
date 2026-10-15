package br.pucminas.tcc.ingressos.domain;

import br.pucminas.tcc.ingressos.domain.Modelos.StatusEvento;

public class Evento {

    private final String id;
    private final String nome;
    private final String data;
    private final String local;
    private final int capacidade;
    private StatusEvento status;

    public Evento(String id, String nome, String data, String local, int capacidade) {
        this.id = id;
        this.nome = nome;
        this.data = data;
        this.local = local;
        this.capacidade = capacidade;
        this.status = StatusEvento.ATIVO;
    }

    public String getId() { return id; }
    public String getNome() { return nome; }
    public String getData() { return data; }
    public String getLocal() { return local; }
    public int getCapacidade() { return capacidade; }
    public StatusEvento getStatus() { return status; }

    void setStatus(StatusEvento status) { this.status = status; }
}
