package br.pucminas.tcc.ingressos.domain;

import br.pucminas.tcc.ingressos.domain.Modelos.TipoCupom;

import java.util.List;

/** Regras de preço R8, R11, R12 e R13. Funções puras, sem estado. */
public final class CalculadoraPreco {

    private CalculadoraPreco() {
    }

    /** Item já precificado: preço unitário do lote e quantidade. */
    public static final class ItemPrecificado {
        private final long precoCentavos;
        private final int quantidade;

        public ItemPrecificado(long precoCentavos, int quantidade) {
            this.precoCentavos = precoCentavos;
            this.quantidade = quantidade;
        }

        public long getPrecoCentavos() { return precoCentavos; }
        public int getQuantidade() { return quantidade; }
    }

    /** Resultado do cálculo de uma reserva. */
    public static final class Totais {
        private final long subtotal;
        private final long desconto;
        private final long total;

        public Totais(long subtotal, long desconto, long total) {
            this.subtotal = subtotal;
            this.desconto = desconto;
            this.total = total;
        }

        public long getSubtotal() { return subtotal; }
        public long getDesconto() { return desconto; }
        public long getTotal() { return total; }
    }

    /** R8. */
    public static long subtotal(List<ItemPrecificado> itens) {
        long soma = 0;
        for (ItemPrecificado item : itens) {
            soma += item.getPrecoCentavos() * item.getQuantidade();
        }
        return soma;
    }

    /** R11, R12 e R13. cupom nulo representa ausência de cupom ou código inexistente. */
    public static long desconto(Cupom cupom, long subtotal, String hoje) {
        if (cupom == null) {
            return 0;
        }
        if (hoje.compareTo(cupom.getValidoAte()) > 0) {
            return 0;
        }
        if (subtotal < cupom.getMinimoCentavos()) {
            return 0;
        }
        long bruto;
        if (cupom.getTipo() == TipoCupom.PERCENTUAL) {
            bruto = subtotal * cupom.getValor() / 100;
        } else {
            bruto = cupom.getValor();
        }
        if (cupom.getMaximoDescontoCentavos() != null) {
            bruto = Math.min(bruto, cupom.getMaximoDescontoCentavos());
        }
        return Math.min(bruto, subtotal);
    }

    /** R13. */
    public static Totais calcular(List<ItemPrecificado> itens, Cupom cupom, String hoje) {
        long sub = subtotal(itens);
        long desc = desconto(cupom, sub, hoje);
        return new Totais(sub, desc, sub - desc);
    }
}
