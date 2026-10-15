package br.pucminas.tcc.ingressos.domain;

/**
 * Tipos enumerados e exceção de regra de negócio do domínio (ver SPEC.md).
 * Agrupados neste arquivo apenas para manter o domínio compacto.
 */
public final class Modelos {

    private Modelos() {
    }

    public enum StatusEvento { ATIVO, CANCELADO, ENCERRADO }

    public enum StatusReserva { CRIADA, CONFIRMADA, PAGA, CANCELADA, EXPIRADA }

    public enum TipoCupom { PERCENTUAL, FIXO }
}
