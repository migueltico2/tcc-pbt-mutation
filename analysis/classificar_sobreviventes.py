#!/usr/bin/env python3
"""Pré-classificação dos mutantes não detectados (métrica M11), para revisão manual do autor.

Unidade: mutante distinto em uma configuração (ecossistema × suíte), considerando as 90 execuções da
configuração (3 níveis de tentativas × 30). Entram todos os mutantes não detectados em ao menos uma
execução. Classes:

- entrada não gerada: o oráculo da suíte detecta o defeito, mas só quando o gerador produz a entrada
  que o revela (em geral um valor exato de limite). Inclui os mutantes detectados em parte das
  execuções (o que muda com o número de tentativas e a semente) e os que nunca foram detectados
  porque a entrada necessária não apareceu (julgados manualmente);
- regra sem propriedade: nunca detectado, e a regra que o trecho implementa não é verificada por
  nenhuma propriedade da suíte;
- oráculo fraco: nunca detectado, embora a regra seja verificada por alguma propriedade da suíte; a
  propriedade exercita o trecho mas não observa a diferença (ex.: só verifica limites);
- equivalente: nenhuma entrada permitida pelo SPEC distingue o mutante do original na API de domínio.

As três primeiras saem de critérios objetivos (dados das execuções + mapa linha→regra abaixo, feito
lendo o código). Os mutantes nunca detectados por nenhuma das duas suítes foram lidos um a um; o
julgamento de cada um (equivalente ou oráculo fraco, com justificativa) está em MANUAL.
"""
import gzip
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
RES = RAIZ / "analysis" / "resultados"
RAW = RAIZ / "data" / "raw" / "v2"
FONTES = {
    "java": RAIZ / "java-api" / "src" / "main" / "java" / "br" / "pucminas" / "tcc" / "ingressos" / "domain",
    "node": RAIZ / "node-api" / "src" / "domain",
}
CACHE = {}

# Regras verificadas por cada suíte (SPEC.md, colunas "Regras" das tabelas de propriedades)
REGRAS_FRACA = {"R5", "R8", "R11", "R12", "R13", "R15", "R16", "R17", "R18", "R19"}
REGRAS_FORTE = {f"R{i}" for i in range(1, 21)}


def linha_fonte(eco, arquivo, linha):
    caminho = FONTES[eco] / arquivo
    if caminho not in CACHE:
        CACHE[caminho] = caminho.read_text().splitlines()
    return CACHE[caminho][int(linha) - 1].strip()


# ------------------------------------------------------------------ mapa linha → regra (lido no código)
def faixa(mapa, ini, fim, regra):
    for i in range(ini, fim + 1):
        mapa[i] = regra


MAPA = {}
# Java – ServicoIngressos.java
m = {}
faixa(m, 26, 28, "infra (identificadores)")
faixa(m, 33, 40, "R1"); faixa(m, 43, 48, "R20"); faixa(m, 51, 54, "R2")
faixa(m, 58, 63, "R3"); faixa(m, 64, 72, "R4"); faixa(m, 74, 76, "R5"); faixa(m, 79, 84, "R20")
faixa(m, 87, 99, "R9"); faixa(m, 103, 110, "R6"); faixa(m, 113, 118, "R20"); faixa(m, 121, 134, "R7")
faixa(m, 137, 142, "R10"); faixa(m, 145, 150, "R8"); faixa(m, 151, 152, "R12"); faixa(m, 153, 153, "R13")
faixa(m, 156, 159, "R18"); faixa(m, 160, 162, "R14"); faixa(m, 163, 167, "R15"); faixa(m, 170, 171, "R16")
faixa(m, 172, 174, "R18"); faixa(m, 177, 192, "R18"); faixa(m, 195, 200, "R19"); faixa(m, 201, 205, "R17")
faixa(m, 206, 207, "R18"); faixa(m, 210, 217, "R15"); faixa(m, 220, 223, "R18"); faixa(m, 226, 229, "R2")
MAPA[("java", "ServicoIngressos.java")] = m
m = {}
faixa(m, 1, 44, "R13"); faixa(m, 45, 51, "R8"); faixa(m, 55, 63, "R12"); faixa(m, 64, 72, "R11")
faixa(m, 73, 73, "R13"); faixa(m, 77, 82, "R13")
MAPA[("java", "CalculadoraPreco.java")] = m
m = {}
faixa(m, 1, 28, "R5"); faixa(m, 29, 32, "R16"); faixa(m, 33, 40, "R17")
MAPA[("java", "Lote.java")] = m
MAPA[("java", "Evento.java")] = {i: ("R2" if i in (20, 28, 30) else "R1") for i in range(1, 40)}
MAPA[("java", "Reserva.java")] = {i: ("R7" if i < 25 or i in (39, 43) else "R10" if i in (40, 44)
                                      else "R18" if i in (41, 45) else "R6") for i in range(1, 50)}
MAPA[("java", "Cupom.java")] = {i: "R9" for i in range(1, 40)}
# Node – servicoIngressos.js
m = {}
faixa(m, 27, 31, "infra (identificadores)")
faixa(m, 35, 43, "R1"); faixa(m, 45, 51, "R20"); faixa(m, 53, 57, "R2")
faixa(m, 61, 66, "R3"); faixa(m, 67, 75, "R4"); faixa(m, 76, 79, "R5"); faixa(m, 81, 87, "R20")
faixa(m, 89, 101, "R9"); faixa(m, 105, 112, "R6"); faixa(m, 114, 120, "R20"); faixa(m, 122, 136, "R7")
faixa(m, 138, 144, "R10"); faixa(m, 146, 151, "R8"); faixa(m, 152, 153, "R12"); faixa(m, 154, 155, "R13")
faixa(m, 157, 160, "R18"); faixa(m, 161, 163, "R14"); faixa(m, 164, 169, "R15"); faixa(m, 170, 173, "R16")
faixa(m, 174, 176, "R18"); faixa(m, 178, 194, "R18"); faixa(m, 196, 201, "R19"); faixa(m, 202, 206, "R17")
faixa(m, 207, 209, "R18"); faixa(m, 213, 220, "R15"); faixa(m, 222, 226, "R18"); faixa(m, 228, 232, "R2")
MAPA[("node", "servicoIngressos.js")] = m
m = {}
faixa(m, 1, 14, "R8"); faixa(m, 16, 26, "R12"); faixa(m, 27, 35, "R11"); faixa(m, 36, 46, "R13")
MAPA[("node", "calculadoraPreco.js")] = m
m = {}
faixa(m, 1, 6, "R2"); faixa(m, 7, 14, "R18"); faixa(m, 15, 16, "R9"); faixa(m, 17, 23, "infra (erro)")
faixa(m, 24, 34, "R1"); m[31] = "R2"; faixa(m, 35, 45, "R5"); faixa(m, 46, 50, "R16"); faixa(m, 51, 55, "R17")
faixa(m, 56, 67, "R9"); faixa(m, 68, 79, "R6")
MAPA[("node", "modelos.js")] = m


def regra(eco, arquivo, linha):
    return MAPA.get((eco, arquivo), {}).get(int(linha), "?")


# ------------------------------------------------------------------ descrição de cada mutante
def descricoes():
    desc = {}
    for d in sorted((RAW / "java").glob("*-t*/run-*/pit/mutations.xml.gz"))[:2]:
        with gzip.open(d) as f:
            for x in ET.parse(f).getroot().findall("mutation"):
                classe = x.findtext("mutatedClass").split(".")[-1]
                mid = (f"{classe}.{x.findtext('mutatedMethod')}:{x.findtext('lineNumber')}:"
                       f"{x.findtext('mutator').split('.')[-1]}:{x.findtext('indexes/index')}")
                desc[("java", mid)] = x.findtext("description")
    for eco in ["node"]:
        for d in sorted((RAW / eco).glob("*-t*/run-*/mutation.json.gz"))[:1]:
            with gzip.open(d) as f:
                rel = json.load(f)
            for caminho, arq in rel["files"].items():
                nome = Path(caminho).name
                for x in arq["mutants"]:
                    lo = x["location"]
                    mid = (f"{nome}:{lo['start']['line']}:{lo['start']['column']}-{lo['end']['line']}."
                           f"{lo['end']['column']}:{x['mutatorName']}:{x.get('replacement', '')}")
                    desc[("node", mid)] = f"{x['mutatorName']}: substitui por {x.get('replacement', '')!r}"
    return desc


# ------------------------------------------------------------------ julgamentos manuais
# Mutantes nunca detectados por nenhuma das suítes, lidos um a um. Chave: (ecossistema, mutante_id).
# Valor: (classe, justificativa).
MANUAL = {}


def carregar_manual():
    arq = RAIZ / "analysis" / "julgamentos_manuais.json"
    if arq.exists():
        for k, v in json.loads(arq.read_text()).items():
            eco, mid = k.split("|", 1)
            MANUAL[(eco, mid)] = (v["classe"], v["justificativa"])


SIGLA = {"entrada não gerada": "Entrada", "oráculo fraco": "Oraculo", "regra sem propriedade": "Regra",
         "equivalente": "Equivalente"}


def escrever_macros(df, coluna):
    """artigo/numeros_classes.tex: contagens por ecossistema × suíte × classe (todos os operadores e padrão)."""
    linhas = ["% Gerado por analysis/classificar_sobreviventes.py ou importar_revisao.py — não editar à mão."]
    for eco in ("java", "node"):
        for suite in ("fraca", "forte"):
            for recorte, sub in (("", df), ("Pad", df[df.operador_padrao == 1])):
                g = sub[(sub.ecossistema == eco) & (sub.suite == suite)]
                base = f"cls{recorte}{eco.title()}{suite.title()}"
                linhas.append(f"\\newcommand{{\\{base}Total}}{{{len(g)}}}")
                for classe, sigla in SIGLA.items():
                    n = int((g[coluna] == classe).sum())
                    pct = f"{100 * n / len(g):.0f}" if len(g) else "0"
                    linhas.append(f"\\newcommand{{\\{base}{sigla}}}{{{n}}}")
                    linhas.append(f"\\newcommand{{\\{base}{sigla}Pct}}{{{pct}}}")
    (RAIZ / "artigo" / "numeros_classes.tex").write_text("\n".join(linhas) + "\n")


def main():
    carregar_manual()
    mut = pd.read_csv(RAIZ / "data" / "mutants.csv", keep_default_na=False)
    mut["detectado"] = mut.status.isin(["KILLED", "TIMEOUT"])
    mut = mut[mut.status != "ERROR"]
    agg = (mut.groupby(["ecossistema", "suite", "mutante_id", "arquivo", "metodo", "linha", "operador", "padrao",
                        "harmonizado"])
           .agg(execucoes=("detectado", "size"), detectado_em=("detectado", "sum"),
                sem_cobertura_em=("status", lambda s: (s == "NO_COVERAGE").sum())).reset_index())
    for t in (10, 100, 1000):
        por_t = (mut[mut.tentativas == t].groupby(["ecossistema", "suite", "mutante_id"]).detectado.mean()
                 .rename(f"taxa_t{t}"))
        agg = agg.join(por_t, on=["ecossistema", "suite", "mutante_id"])
    # detecção pela suíte forte (para classificar sobreviventes da fraca)
    forte = agg[agg.suite == "forte"].set_index(["ecossistema", "mutante_id"]).detectado_em
    agg["forte_detecta"] = [forte.get((e, i), 0) > 0 for e, i in zip(agg.ecossistema, agg.mutante_id)]
    nunca_detectado_global = set(
        (e, i) for (e, i), g in agg.groupby(["ecossistema", "mutante_id"]) if g.detectado_em.sum() == 0)

    desc = descricoes()
    linhas = []
    pendentes = []
    for r in agg[agg.detectado_em < agg.execucoes].itertuples():
        rg = regra(r.ecossistema, r.arquivo, r.linha)
        regras_suite = REGRAS_FRACA if r.suite == "fraca" else REGRAS_FORTE
        if r.detectado_em > 0:
            classe, motivo = "entrada não gerada", (f"detectado em {r.detectado_em} de {r.execucoes} execuções; depende "
                                                    "de o gerador produzir a entrada que revela o defeito")
        elif (r.ecossistema, r.mutante_id) in MANUAL:
            classe, motivo = MANUAL[(r.ecossistema, r.mutante_id)]
            if classe in ("oráculo fraco", "entrada não gerada") and rg not in regras_suite:
                classe, motivo = "regra sem propriedade", f"{rg} não é verificada pela suíte {r.suite}; " + motivo
        elif rg in regras_suite:
            classe, motivo = "oráculo fraco", (f"{rg} é verificada pela suíte {r.suite}, mas nenhuma propriedade "
                                               "observa a diferença" + ("; a suíte forte detecta" if r.forte_detecta else ""))
        else:
            classe, motivo = "regra sem propriedade", (f"{rg} não é verificada pela suíte {r.suite}"
                                                       + ("; a suíte forte detecta" if r.forte_detecta else ""))
        if (r.ecossistema, r.mutante_id) in nunca_detectado_global and (r.ecossistema, r.mutante_id) not in MANUAL:
            pendentes.append((r.ecossistema, r.mutante_id))
        linhas.append({
            "ecossistema": r.ecossistema, "suite": r.suite, "mutante_id": r.mutante_id, "arquivo": r.arquivo,
            "linha": r.linha, "metodo": r.metodo, "codigo": linha_fonte(r.ecossistema, r.arquivo, r.linha),
            "operador": r.operador, "mutacao": desc.get((r.ecossistema, r.mutante_id), ""),
            "operador_padrao": int(r.padrao), "classe_harmonizada": r.harmonizado, "regra": rg,
            "execucoes": r.execucoes, "detectado_em": r.detectado_em, "sem_cobertura_em": r.sem_cobertura_em,
            "taxa_deteccao_t10": round(r.taxa_t10, 3), "taxa_deteccao_t100": round(r.taxa_t100, 3),
            "taxa_deteccao_t1000": round(r.taxa_t1000, 3),
            "suite_forte_detecta": int(r.forte_detecta), "classe": classe, "justificativa": motivo,
        })
    out = pd.DataFrame(linhas).sort_values(["ecossistema", "suite", "arquivo", "linha", "operador"])
    out.to_csv(RES / "sobreviventes_classificados.csv", index=False)
    resumo = (out.groupby(["ecossistema", "suite", "classe"]).size().unstack(fill_value=0))
    resumo.to_csv(RES / "sobreviventes_por_classe.csv")
    resumo_p = (out[out.operador_padrao == 1].groupby(["ecossistema", "suite", "classe"]).size()
                .unstack(fill_value=0))
    resumo_p.to_csv(RES / "sobreviventes_por_classe_operadores_padrao.csv")
    escrever_macros(out, "classe")
    pend = sorted(set(pendentes))
    (RES / "pendentes_julgamento_manual.json").write_text(json.dumps(
        [{"ecossistema": e, "mutante_id": i, "regra": out[(out.ecossistema == e) & (out.mutante_id == i)].regra.iloc[0],
          "codigo": out[(out.ecossistema == e) & (out.mutante_id == i)].codigo.iloc[0],
          "mutacao": desc.get((e, i), "")} for e, i in pend], indent=1, ensure_ascii=False))
    print(resumo)
    print(f"pendentes de julgamento manual: {len(pend)}")


if __name__ == "__main__":
    main()
