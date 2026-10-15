#!/usr/bin/env python3
"""Classificação manual dos mutantes sobreviventes (métrica M11), codificada como regras revisáveis.

Cada mutante não detectado (sobrevivente ou sem cobertura) em ao menos uma execução recebe uma classe e o motivo:
- equivalente: nenhuma entrada distingue o mutante do original no domínio;
- regra sem propriedade: a regra afetada não é verificada por nenhuma de P1–P8;
- propriedade fraca: a regra é exercitada por alguma propriedade, mas o oráculo não observa a diferença.

As regras abaixo foram escritas depois de ler o código de cada sobrevivente (ver comentários) e
cobrem todos os casos; um mutante que não case com nenhuma regra é marcado como NAO_CLASSIFICADO,
para revisão.
"""
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
RES = RAIZ / "analysis" / "resultados"
FONTES = {
    "java": RAIZ / "java-api" / "src" / "main" / "java" / "br" / "pucminas" / "tcc" / "ingressos" / "domain",
    "node": RAIZ / "node-api" / "src" / "domain",
}
CACHE = {}


def linha_fonte(eco, arquivo, linha):
    caminho = FONTES[eco] / arquivo
    if caminho not in CACHE:
        CACHE[caminho] = caminho.read_text().splitlines()
    return CACHE[caminho][int(linha) - 1].strip()


VALIDACAO_ENTRADA = {
    "criarEvento": "R1 (dados do evento)",
    "criarLote": "R3/R4 (dados do lote e capacidade)",
    "buscarEvento": "R20 (entidade inexistente)",
    "buscarLote": "R20 (entidade inexistente)",
    "buscarReserva": "R20 (entidade inexistente)",
    "alterarStatusEvento": "R2 (evento inativo)",
    "exigirEventoAtivo": "R2 (evento inativo)",
}


def classificar(r):
    eco, metodo, op, codigo = r.ecossistema, r.metodo, r.operador, r.codigo
    rep = r.mutante_id.split(":", 4)[-1] if eco == "node" else ""

    # ---------------- equivalentes
    if metodo == "novoId":
        return "equivalente", "contador decrescente ainda gera identificadores únicos"
    if eco == "node" and op == "StringLiteral" and "novoId(" in codigo and rep == '""':
        return "equivalente", "prefixo vazio no identificador mantém identificadores únicos"
    if metodo == "calcularTotais" and "codigocupom" in codigo.lower() and (
            (eco == "java" and op == "RemoveConditionalMutator_EQUAL_ELSE")
            or (eco == "node" and op == "ConditionalExpression" and rep == "false")):
        return "equivalente", "buscar cupom com código nulo devolve nulo, igual ao atalho removido"

    # ---------------- regras sem propriedade
    if metodo in VALIDACAO_ENTRADA:
        return "regra sem propriedade", VALIDACAO_ENTRADA[metodo]
    if "exigirEventoAtivo" in codigo:
        return "regra sem propriedade", "R2 (evento inativo)"
    if metodo == "cadastrarCupom" and any(t in codigo for t in ("valorValido", "maximoValido", "DADOS_INVALIDOS")):
        return "regra sem propriedade", "R9 (validação do cupom)"
    if metodo == "adicionarItem" and any(t in codigo for t in ("quantidade <= 0", "QUANTIDADE_INVALIDA", "eventoId", "LOTE_INVALIDO")):
        return "regra sem propriedade", "R7 (validação do item)"
    if metodo == "confirmar" and any(t in codigo for t in ("isEmpty", "length === 0", "RESERVA_VAZIA")):
        return "regra sem propriedade", "R14 (reserva vazia)"
    if metodo == "aplicarCupom" and "exigirStatus" in codigo:
        return "regra sem propriedade", "R10 (cupom só em reserva CRIADA)"
    if eco == "node" and r.arquivo == "modelos.js" and op in ("StringLiteral", "ObjectLiteral"):
        return "regra sem propriedade", "nomes dos status e tipos definidos no SPEC (não verificados)"
    if eco == "java" and r.status_dominante == "NO_COVERAGE" and metodo.startswith("get"):
        return "regra sem propriedade", "dado do cadastro não usado por nenhuma regra verificada"

    # ---------------- propriedades fracas (o oráculo não observa a diferença)
    if metodo in ("subtotal", "calcular") or (metodo == "calcularTotais"):
        return "propriedade fraca", "P1–P4 só verificam limites e relações; nenhuma fixa o valor do subtotal"
    if metodo == "desconto":
        return "propriedade fraca", "P1, P2 e P4 aceitam qualquer desconto entre 0 e o subtotal"
    if metodo in ("aplicarCupom", "cadastrarCupom") or (eco == "java" and r.classe in ("Cupom", "Reserva")
                                                          and metodo in ("getTipo", "getValor", "getValidoAte",
                                                                         "getMaximoDescontoCentavos", "getCodigoCupom")):
        return "propriedade fraca", "cupom ignorado ou alterado gera desconto 0, aceito por P1–P4"
    if eco == "java" and metodo in ("getPrecoCentavos", "getQuantidade"):
        return "propriedade fraca", "preço/quantidade zerados geram subtotal 0, aceito por P1–P4"
    if eco == "java" and metodo == "getId":
        return "propriedade fraca", "geradores criam um único evento por cenário"
    if metodo == "confirmar":
        return "propriedade fraca", "P5/P6 aceitam recusa sem verificar a condição nem o código do erro"
    if op in ("NullReturnValsMutator",) or (eco == "java" and op == "NullReturnValsMutator"):
        return "propriedade fraca", "valor de retorno do serviço não é observado pelas propriedades"
    if metodo in ("pagar", "cancelar", "expirar", "encerrar", "adicionarItem"):
        return "propriedade fraca", "valor de retorno do serviço não é observado pelas propriedades"
    return "NAO_CLASSIFICADO", ""


def main():
    est = pd.read_csv(RES / "estabilidade_mutantes.csv")
    mut = pd.read_csv(RAIZ / "data" / "mutants.csv", keep_default_na=False)
    info = mut.drop_duplicates(["ecossistema", "mutante_id"])[["ecossistema", "mutante_id", "arquivo", "classe"]]
    dom = (mut.groupby(["ecossistema", "mutante_id"]).status.agg(lambda s: s.value_counts().idxmax())
           .rename("status_dominante").reset_index())
    sob = est[est.detectado_em < est.execucoes].merge(info, on=["ecossistema", "mutante_id"]).merge(dom, on=["ecossistema", "mutante_id"])
    sob["codigo"] = [linha_fonte(e, a, l) for e, a, l in zip(sob.ecossistema, sob.arquivo, sob.linha)]
    cls = sob.apply(classificar, axis=1, result_type="expand")
    sob["classe_sobrevivente"], sob["motivo"] = cls[0], cls[1]
    sob["nunca_detectado"] = sob.detectado_em == 0
    sob.to_csv(RES / "sobreviventes_classificados.csv", index=False)
    resumo = sob.groupby(["ecossistema", "classe_sobrevivente"]).size().unstack(fill_value=0)
    resumo.to_csv(RES / "sobreviventes_por_classe.csv")
    print(resumo)
    print(sob.groupby(["ecossistema", "classe_sobrevivente", "motivo"]).size().to_string())
    nc = sob[sob.classe_sobrevivente == "NAO_CLASSIFICADO"]
    if len(nc):
        print("\nNÃO CLASSIFICADOS:")
        print(nc[["ecossistema", "metodo", "linha", "operador", "codigo"]].to_string())


if __name__ == "__main__":
    main()
