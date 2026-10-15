package br.pucminas.tcc.ingressos.domain;

import br.pucminas.tcc.ingressos.domain.Modelos.TipoCupom;

/** Cupom de desconto (R9). maximoDescontoCentavos nulo significa sem teto. */
public class Cupom {

    private final String codigo;
    private final TipoCupom tipo;
    private final long valor;
    private final long minimoCentavos;
    private final Long maximoDescontoCentavos;
    private final String validoAte;

    public Cupom(String codigo, TipoCupom tipo, long valor, long minimoCentavos,
                 Long maximoDescontoCentavos, String validoAte) {
        this.codigo = codigo;
        this.tipo = tipo;
        this.valor = valor;
        this.minimoCentavos = minimoCentavos;
        this.maximoDescontoCentavos = maximoDescontoCentavos;
        this.validoAte = validoAte;
    }

    public String getCodigo() { return codigo; }
    public TipoCupom getTipo() { return tipo; }
    public long getValor() { return valor; }
    public long getMinimoCentavos() { return minimoCentavos; }
    public Long getMaximoDescontoCentavos() { return maximoDescontoCentavos; }
    public String getValidoAte() { return validoAte; }
}
