package br.pucminas.tcc.ingressos.domain;

/** Violação de regra de negócio, identificada por um dos códigos de erro do SPEC.md. */
public class RegraNegocioException extends RuntimeException {

    private final String codigo;

    public RegraNegocioException(String codigo) {
        super(codigo);
        this.codigo = codigo;
    }

    public String getCodigo() {
        return codigo;
    }
}
