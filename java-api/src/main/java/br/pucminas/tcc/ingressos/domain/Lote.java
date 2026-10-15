package br.pucminas.tcc.ingressos.domain;

/** Lote de ingressos de um evento (R3–R5). */
public class Lote {

    private final String id;
    private final String eventoId;
    private final String nome;
    private final long precoCentavos;
    private final int quantidadeTotal;
    private int quantidadeDisponivel;

    public Lote(String id, String eventoId, String nome, long precoCentavos, int quantidadeTotal) {
        this.id = id;
        this.eventoId = eventoId;
        this.nome = nome;
        this.precoCentavos = precoCentavos;
        this.quantidadeTotal = quantidadeTotal;
        this.quantidadeDisponivel = quantidadeTotal;
    }

    public String getId() { return id; }
    public String getEventoId() { return eventoId; }
    public String getNome() { return nome; }
    public long getPrecoCentavos() { return precoCentavos; }
    public int getQuantidadeTotal() { return quantidadeTotal; }
    public int getQuantidadeDisponivel() { return quantidadeDisponivel; }

    /** R16: baixa a quantidade; a suficiência já foi verificada pelo serviço (R15). */
    void baixar(int quantidade) {
        quantidadeDisponivel -= quantidade;
    }

    /** R17: devolve a quantidade reservada. */
    void devolver(int quantidade) {
        quantidadeDisponivel += quantidade;
    }
}
