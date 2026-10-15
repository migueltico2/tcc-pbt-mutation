#!/usr/bin/env python3
"""Consolida os relatórios brutos (data/raw) em data/runs.csv e data/mutants.csv.

- PIT: data/raw/java/run-XX/pit/mutations.xml (com fullMutationMatrix) + jacoco.csv
- StrykerJS: data/raw/node/run-XX/mutation.json (disableBail) + coverage-summary.json

Status normalizados: KILLED, TIMEOUT, SURVIVED, NO_COVERAGE, ERROR.
Mutation score = (KILLED + TIMEOUT) / (KILLED + TIMEOUT + SURVIVED + NO_COVERAGE); ERROR fica de fora,
que é como as duas ferramentas calculam o score.
"""
import csv
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RAW = RAIZ / "data" / "raw"

# ------------------------------------------------------------------ categorias de operador (D9)
# Categorias comuns às duas ferramentas e categorias exclusivas de cada uma.
CATEGORIA_PIT = {
    "MathMutator": "Aritmético",
    "InvertNegsMutator": "Aritmético",
    "ConditionalsBoundaryMutator": "Relacional",
    "NegateConditionalsMutator": "Relacional",
    "RemoveConditionalMutator_EQUAL_ELSE": "Condicional/lógico",
    "RemoveConditionalMutator_ORDER_ELSE": "Condicional/lógico",
    "RemoveConditionalMutator_EQUAL_IF": "Condicional/lógico",
    "RemoveConditionalMutator_ORDER_IF": "Condicional/lógico",
    "VoidMethodCallMutator": "Remoção de instrução",
    "IncrementsMutator": "Incremento",
    "EmptyObjectReturnValsMutator": "Valor de retorno",
    "NullReturnValsMutator": "Valor de retorno",
    "PrimitiveReturnsMutator": "Valor de retorno",
    "BooleanTrueReturnValsMutator": "Valor de retorno",
    "BooleanFalseReturnValsMutator": "Valor de retorno",
}
CATEGORIA_STRYKER = {
    "ArithmeticOperator": "Aritmético",
    "AssignmentOperator": "Aritmético",
    "UnaryOperator": "Aritmético",
    "EqualityOperator": "Relacional",
    "ConditionalExpression": "Condicional/lógico",
    "LogicalOperator": "Condicional/lógico",
    "BlockStatement": "Remoção de instrução",
    "CallExpression": "Remoção de instrução",
    "UpdateOperator": "Incremento",
    "StringLiteral": "Literal",
    "BooleanLiteral": "Literal",
    "ObjectLiteral": "Literal",
    "ArrayDeclaration": "Literal",
    "MethodExpression": "Chamada de método",
    "OptionalChaining": "Chamada de método",
    "ArrowFunction": "Chamada de método",
    "Regex": "Literal",
}
COMUNS = {"Aritmético", "Relacional", "Condicional/lógico", "Remoção de instrução", "Incremento"}

# ------------------------------------------------------------------ módulos (Tabela 1)
MODULO_POR_METODO = {
    "criarEvento": "Eventos", "buscarEvento": "Eventos", "alterarStatusEvento": "Eventos",
    "exigirEventoAtivo": "Eventos",
    "criarLote": "Lotes", "buscarLote": "Lotes",
    "criarReserva": "Reservas", "buscarReserva": "Reservas", "adicionarItem": "Reservas",
    "calcularTotais": "Reservas", "subtotal": "Reservas", "calcular": "Reservas",
    "cadastrarCupom": "Cupons", "aplicarCupom": "Cupons", "desconto": "Cupons",
    "confirmar": "Disponibilidade", "baixar": "Disponibilidade", "devolver": "Disponibilidade",
    "quantidadesPorLote": "Disponibilidade",
    "pagar": "Status", "cancelar": "Status", "expirar": "Status", "encerrar": "Status",
    "exigirStatus": "Status",
    "novoId": "Infraestrutura",
}
MODULO_ACESSORES = "Modelos (construtores e acessores)"


def modulo(metodo: str) -> str:
    return MODULO_POR_METODO.get(metodo, MODULO_ACESSORES)


def propriedade_de(nome_teste: str):
    m = re.search(r"\b[pP]([1-8])(?=[A-Z ])", nome_teste)
    return f"P{m.group(1)}" if m else None


# ------------------------------------------------------------------ Java / PIT
def ler_java(run_dir: Path):
    meta = json.loads((run_dir / "meta.json").read_text())
    root = ET.parse(run_dir / "pit" / "mutations.xml").getroot()
    mutantes = []
    for m in root.findall("mutation"):
        status_pit = m.get("status")
        status = {"KILLED": "KILLED", "TIMED_OUT": "TIMEOUT", "MEMORY_ERROR": "TIMEOUT",
                  "SURVIVED": "SURVIVED", "NO_COVERAGE": "NO_COVERAGE"}.get(status_pit, "ERROR")
        operador = m.findtext("mutator").split(".")[-1]
        metodo = m.findtext("mutatedMethod")
        classe = m.findtext("mutatedClass").split(".")[-1]
        if metodo in ("<init>", "<clinit>"):
            metodo_mod = MODULO_ACESSORES
        else:
            metodo_mod = modulo(metodo)
        killers = (m.findtext("killingTests") or "")
        props = sorted({p for p in (propriedade_de(t) for t in killers.split("|")) if p})
        mutantes.append({
            "mutante_id": f"{classe}.{metodo}:{m.findtext('lineNumber')}:{operador}:{m.findtext('indexes/index')}",
            "arquivo": m.findtext("sourceFile"), "classe": classe, "metodo": metodo,
            "linha": m.findtext("lineNumber"), "operador": operador,
            "categoria": CATEGORIA_PIT.get(operador, "Outro"), "modulo": metodo_mod,
            "status": status, "propriedades_que_mataram": "|".join(props),
        })
    linhas = cobertas = ramos = ramos_cob = 0
    with open(run_dir / "jacoco.csv") as f:
        for r in csv.DictReader(f):
            linhas += int(r["LINE_MISSED"]) + int(r["LINE_COVERED"])
            cobertas += int(r["LINE_COVERED"])
            ramos += int(r["BRANCH_MISSED"]) + int(r["BRANCH_COVERED"])
            ramos_cob += int(r["BRANCH_COVERED"])
    cobertura = {"cobertura_linhas": round(100 * cobertas / linhas, 2),
                 "cobertura_ramos": round(100 * ramos_cob / ramos, 2)}
    return meta, mutantes, cobertura


# ------------------------------------------------------------------ Node / Stryker
def mapa_funcoes(caminho: Path):
    """Linha -> nome da função/método que a contém (heurística por indentação do código do domínio)."""
    linhas = caminho.read_text().splitlines()
    atual, mapa = "<modulo>", {}
    for i, texto in enumerate(linhas, start=1):
        m = (re.match(r"^  (?:static )?(\w+)\([^)]*\) \{$", texto)
             or re.match(r"^function (\w+)\(", texto))
        if m:
            atual = "constructor" if m.group(1) == "constructor" else m.group(1)
        elif re.match(r"^(class|const|module\.exports|\}$)", texto):
            atual = "<modulo>" if not texto.startswith("}") else atual
        mapa[i] = atual
    return mapa


def ler_node(run_dir: Path):
    meta = json.loads((run_dir / "meta.json").read_text())
    rel = json.loads((run_dir / "mutation.json").read_text())
    nomes_testes = {}
    for arq in rel.get("testFiles", {}).values():
        for t in arq.get("tests", []):
            nomes_testes[t["id"]] = t["name"]
    mutantes = []
    for caminho_rel, arq in rel["files"].items():
        caminho = Path(rel.get("projectRoot", str(RAIZ / "node-api"))) / caminho_rel
        if not caminho.exists():
            caminho = RAIZ / "node-api" / caminho_rel
        funcoes = mapa_funcoes(caminho)
        nome_arquivo = Path(caminho_rel).name
        for m in arq["mutants"]:
            status = {"Killed": "KILLED", "Timeout": "TIMEOUT", "Survived": "SURVIVED",
                      "NoCoverage": "NO_COVERAGE"}.get(m["status"], "ERROR")
            linha = m["location"]["start"]["line"]
            metodo = funcoes.get(linha, "<modulo>")
            if nome_arquivo == "modelos.js" and metodo not in ("baixar", "devolver"):
                mod = MODULO_ACESSORES
            elif metodo in ("constructor", "<modulo>"):
                mod = MODULO_ACESSORES
            else:
                mod = modulo(metodo)
            props = sorted({p for p in (propriedade_de(nomes_testes.get(t, "")) for t in m.get("killedBy", []) or []) if p})
            mutantes.append({
                "mutante_id": (f"{nome_arquivo}:{linha}:{m['location']['start']['column']}-{m['location']['end']['line']}."
                               f"{m['location']['end']['column']}:{m['mutatorName']}:{m.get('replacement', '')}"),
                "arquivo": nome_arquivo, "classe": nome_arquivo.replace(".js", ""), "metodo": metodo,
                "linha": linha, "operador": m["mutatorName"],
                "categoria": CATEGORIA_STRYKER.get(m["mutatorName"], "Outro"), "modulo": mod,
                "status": status, "propriedades_que_mataram": "|".join(props),
            })
    total = json.loads((run_dir / "coverage-summary.json").read_text())["total"]
    cobertura = {"cobertura_linhas": total["lines"]["pct"], "cobertura_ramos": total["branches"]["pct"]}
    return meta, mutantes, cobertura


# ------------------------------------------------------------------ saída
def score(mutantes):
    det = sum(m["status"] in ("KILLED", "TIMEOUT") for m in mutantes)
    val = sum(m["status"] != "ERROR" for m in mutantes)
    return round(100 * det / val, 4) if val else None


def main():
    runs, todos = [], []
    for eco, leitor in (("java", ler_java), ("node", ler_node)):
        for run_dir in sorted((RAW / eco).glob("run-*")):
            if not (run_dir / "meta.json").exists():
                continue
            meta, mutantes, cobertura = leitor(run_dir)
            for m in mutantes:
                m.update({"ecossistema": eco, "execucao": meta["execucao"]})
            todos.extend(mutantes)
            cont = {s: sum(m["status"] == s for m in mutantes)
                    for s in ("KILLED", "TIMEOUT", "SURVIVED", "NO_COVERAGE", "ERROR")}
            comuns = [m for m in mutantes if m["categoria"] in COMUNS]
            sem_acessores = [m for m in mutantes if m["modulo"] != MODULO_ACESSORES]
            runs.append({
                "ecossistema": eco, "execucao": meta["execucao"],
                "gerados": len(mutantes), "mortos": cont["KILLED"], "timeout": cont["TIMEOUT"],
                "sobreviventes": cont["SURVIVED"], "sem_cobertura": cont["NO_COVERAGE"], "erros": cont["ERROR"],
                "mutation_score": score(mutantes),
                "mutation_score_comuns": score(comuns), "gerados_comuns": len(comuns),
                "mutation_score_sem_acessores": score(sem_acessores),
                "tempo_suite_s": meta["tempo_suite_s"], "tempo_mutacao_s": meta["tempo_mutacao_s"],
                **cobertura,
            })
    (RAIZ / "data").mkdir(exist_ok=True)
    with open(RAIZ / "data" / "runs.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(runs[0].keys()))
        w.writeheader()
        w.writerows(runs)
    campos = ["ecossistema", "execucao", "mutante_id", "modulo", "arquivo", "classe", "metodo", "linha",
              "operador", "categoria", "status", "propriedades_que_mataram"]
    with open(RAIZ / "data" / "mutants.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        w.writerows(todos)
    print(f"{len(runs)} execuções, {len(todos)} linhas de mutante", file=sys.stderr)


if __name__ == "__main__":
    main()
