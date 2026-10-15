#!/usr/bin/env python3
"""Análise do experimento: tabelas, testes estatísticos e figuras do capítulo 5.

Entrada: data/runs.csv e data/mutants.csv (gerados por scripts/consolidate.py)
Saída:   analysis/resultados/*.csv, analysis/resultados/resumo.json e analysis/figuras/*.pdf|png
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "analysis" / "resultados"
FIG = RAIZ / "analysis" / "figuras"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

ECO = {"java": "Java/Spring Boot (jqwik + PIT)", "node": "Node.js/Express (fast-check + StrykerJS)"}
ROTULO = {"java": "Java", "node": "Node.js"}
COR = {"java": "#2a78d6", "node": "#eb6834"}          # slots 1 e 2 da paleta categórica validada
COR_STATUS = {"Detectado": "#1baf7a", "Sobrevivente": "#eda100", "Sem cobertura": "#b9b8b3"}
TINTA, TINTA2, GRADE = "#0b0b0b", "#52514e", "#e4e3df"
ACESSORES = "Modelos (construtores e acessores)"
MODULOS = ["Eventos", "Lotes", "Reservas", "Cupons", "Disponibilidade", "Status", "Infraestrutura", ACESSORES]
COMUNS = ["Aritmético", "Relacional", "Condicional/lógico", "Remoção de instrução", "Incremento"]

plt.rcParams.update({
    "font.family": "serif", "font.size": 9, "axes.edgecolor": TINTA2, "axes.labelcolor": TINTA,
    "xtick.color": TINTA2, "ytick.color": TINTA2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRADE, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "legend.frameon": False, "figure.dpi": 150, "savefig.bbox": "tight",
})

runs = pd.read_csv(RAIZ / "data" / "runs.csv")
mut = pd.read_csv(RAIZ / "data" / "mutants.csv", keep_default_na=False)
mut["detectado"] = mut.status.isin(["KILLED", "TIMEOUT"])
mut["valido"] = mut.status != "ERROR"
N_EXEC = runs.groupby("ecossistema").execucao.nunique().to_dict()


def salvar(fig, nome):
    fig.savefig(FIG / f"{nome}.pdf")
    fig.savefig(FIG / f"{nome}.png", dpi=200)
    plt.close(fig)


def a12(x, y):
    """Vargha-Delaney Â12: probabilidade de um valor de x superar um de y (empates contam meio)."""
    x, y = np.asarray(x), np.asarray(y)
    maior = (x[:, None] > y[None, :]).sum()
    igual = (x[:, None] == y[None, :]).sum()
    return (maior + 0.5 * igual) / (len(x) * len(y))


def magnitude(a):
    d = abs(a - 0.5)
    return "desprezível" if d < 0.06 else "pequena" if d < 0.14 else "média" if d < 0.21 else "grande"


def score(df):
    v = df[df.valido]
    return 100 * v.detectado.sum() / len(v) if len(v) else np.nan


# ------------------------------------------------------------------ Tabela 5.1 (resumo)
def desc(s):
    return {"media": s.mean(), "dp": s.std(ddof=1), "mediana": s.median(), "min": s.min(), "max": s.max()}


resumo = {}
for eco, g in runs.groupby("ecossistema"):
    resumo[eco] = {
        "execucoes": int(len(g)),
        "gerados": desc(g.gerados), "mortos": desc(g.mortos), "timeout": desc(g.timeout),
        "sobreviventes": desc(g.sobreviventes), "sem_cobertura": desc(g.sem_cobertura), "erros": desc(g.erros),
        "mutation_score": desc(g.mutation_score),
        "mutation_score_comuns": desc(g.mutation_score_comuns), "gerados_comuns": desc(g.gerados_comuns),
        "mutation_score_sem_acessores": desc(g.mutation_score_sem_acessores),
        "cobertura_linhas": desc(g.cobertura_linhas), "cobertura_ramos": desc(g.cobertura_ramos),
        "tempo_suite_s": desc(g.tempo_suite_s), "tempo_mutacao_s": desc(g.tempo_mutacao_s),
    }

# ------------------------------------------------------------------ testes estatísticos (5.4)
testes = []
j, n = runs[runs.ecossistema == "java"], runs[runs.ecossistema == "node"]
for metrica in ["mutation_score", "mutation_score_comuns", "mutation_score_sem_acessores",
                "tempo_mutacao_s", "tempo_suite_s", "cobertura_linhas", "cobertura_ramos"]:
    x, y = j[metrica].to_numpy(), n[metrica].to_numpy()
    sw_x = stats.shapiro(x).pvalue if np.ptp(x) > 0 else float("nan")
    sw_y = stats.shapiro(y).pvalue if np.ptp(y) > 0 else float("nan")
    if np.ptp(np.concatenate([x, y])) == 0:
        u, p = float("nan"), 1.0
    else:
        res = stats.mannwhitneyu(x, y, alternative="two-sided")
        u, p = res.statistic, res.pvalue
    a = a12(x, y)
    testes.append({"metrica": metrica, "mediana_java": np.median(x), "mediana_node": np.median(y),
                   "dp_java": x.std(ddof=1), "dp_node": y.std(ddof=1),
                   "shapiro_p_java": sw_x, "shapiro_p_node": sw_y, "U": u, "p_valor": p,
                   "A12_java_vs_node": a, "magnitude": magnitude(a)})
testes = pd.DataFrame(testes)
testes.to_csv(OUT / "testes_estatisticos.csv", index=False)

# Teste por mutante nas categorias comuns: qui-quadrado detectado × não detectado.
# Unidade de análise = mutante distinto (não mutante × execução, que contaria cada mutante 30 vezes
# e inflaria a amostra). Um mutante conta como detectado se foi detectado na maioria das execuções.
por_mutante = (mut[mut.valido & mut.categoria.isin(COMUNS)]
               .groupby(["ecossistema", "mutante_id"]).detectado.mean().ge(0.5).reset_index())
cont = por_mutante.groupby("ecossistema").detectado.agg(["sum", "count"])
tab = np.array([[cont.loc[e, "sum"], cont.loc[e, "count"] - cont.loc[e, "sum"]] for e in ["java", "node"]])
chi2, p_chi, _, _ = stats.chi2_contingency(tab)
qui = {"tabela_detectado_nao": tab.tolist(), "chi2": chi2, "p_valor": p_chi}

# ------------------------------------------------------------------ por módulo e categoria
por_mod = (mut[mut.valido].groupby(["ecossistema", "modulo"])
           .agg(mutantes=("detectado", "size"), detectados=("detectado", "sum"),
                sem_cobertura=("status", lambda s: (s == "NO_COVERAGE").sum())).reset_index())
por_mod["mutantes_por_execucao"] = por_mod.apply(lambda r: r.mutantes / N_EXEC[r.ecossistema], axis=1)
por_mod["mutation_score"] = 100 * por_mod.detectados / por_mod.mutantes
por_mod["cobertura_mutantes"] = 100 * (por_mod.mutantes - por_mod.sem_cobertura) / por_mod.mutantes
por_mod.to_csv(OUT / "por_modulo.csv", index=False)

por_cat = (mut[mut.valido].groupby(["ecossistema", "categoria", "status"]).size()
           .unstack(fill_value=0).reset_index())
for c in ["KILLED", "TIMEOUT", "SURVIVED", "NO_COVERAGE"]:
    if c not in por_cat:
        por_cat[c] = 0
por_cat["total"] = por_cat[["KILLED", "TIMEOUT", "SURVIVED", "NO_COVERAGE"]].sum(axis=1)
por_cat["por_execucao"] = por_cat.apply(lambda r: r.total / N_EXEC[r.ecossistema], axis=1)
por_cat["mutation_score"] = 100 * (por_cat.KILLED + por_cat.TIMEOUT) / por_cat.total
por_cat.to_csv(OUT / "por_categoria.csv", index=False)

por_op = (mut[mut.valido].groupby(["ecossistema", "operador"])
          .agg(total=("detectado", "size"), detectados=("detectado", "sum")).reset_index())
por_op["por_execucao"] = por_op.apply(lambda r: r.total / N_EXEC[r.ecossistema], axis=1)
por_op["mutation_score"] = 100 * por_op.detectados / por_op.total
por_op.to_csv(OUT / "por_operador.csv", index=False)

# Propriedades: média, por execução, de mutantes mortos por cada propriedade; e mortes exclusivas
linhas = []
for (eco, ex), g in mut[mut.detectado].groupby(["ecossistema", "execucao"]):
    for p in [f"P{i}" for i in range(1, 9)]:
        mata = g.propriedades_que_mataram.str.split("|").apply(lambda l: p in l)
        so = g.propriedades_que_mataram == p
        linhas.append({"ecossistema": eco, "execucao": ex, "propriedade": p,
                       "mortos": int(mata.sum()), "exclusivos": int(so.sum())})
por_prop = (pd.DataFrame(linhas).groupby(["ecossistema", "propriedade"])
            .agg(mortos=("mortos", "mean"), exclusivos=("exclusivos", "mean")).reset_index())
por_prop.to_csv(OUT / "por_propriedade.csv", index=False)

# Estabilidade: com que frequência cada mutante sobreviveu nas execuções
estab = (mut[mut.valido].groupby(["ecossistema", "mutante_id", "modulo", "metodo", "linha", "operador", "categoria"])
         .agg(execucoes=("execucao", "nunique"), detectado_em=("detectado", "sum"),
              sem_cobertura_em=("status", lambda s: (s == "NO_COVERAGE").sum())).reset_index())
estab["sobreviveu_em"] = estab.execucoes - estab.detectado_em - estab.sem_cobertura_em
estab.to_csv(OUT / "estabilidade_mutantes.csv", index=False)
instaveis = estab[(estab.detectado_em > 0) & (estab.detectado_em < estab.execucoes)]

# Linha de base opcional: mutação só com os casos de exemplo (uma execução, determinística)
import sys as _sys
_sys.path.insert(0, str(RAIZ / "scripts"))
import xml.etree.ElementTree as ET
from consolidate import CATEGORIA_PIT, CATEGORIA_STRYKER, COMUNS as _COMUNS
base = {}
bdir = RAIZ / "data" / "raw" / "baseline-exemplos"
if (bdir / "java-pit" / "mutations.xml").exists():
    st, cat = [], []
    for m in ET.parse(bdir / "java-pit" / "mutations.xml").getroot().findall("mutation"):
        st.append(m.get("status")); cat.append(CATEGORIA_PIT.get(m.findtext("mutator").split(".")[-1], "Outro"))
    det = [s_ in ("KILLED", "TIMED_OUT", "MEMORY_ERROR") for s_ in st]
    val = [s_ in ("KILLED", "TIMED_OUT", "MEMORY_ERROR", "SURVIVED", "NO_COVERAGE") for s_ in st]
    com = [c in _COMUNS for c in cat]
    base["java"] = {"gerados": len(st), "detectados": sum(det), "validos": sum(val),
                    "mutation_score": 100 * sum(det) / sum(val),
                    "mutation_score_comuns": 100 * sum(d for d, c in zip(det, com) if c) / sum(v for v, c in zip(val, com) if c)}
if (bdir / "node-mutation.json").exists():
    rel = json.loads((bdir / "node-mutation.json").read_text())
    ms_ = [m for f in rel["files"].values() for m in f["mutants"]]
    det = [m["status"] in ("Killed", "Timeout") for m in ms_]
    val = [m["status"] in ("Killed", "Timeout", "Survived", "NoCoverage") for m in ms_]
    com = [CATEGORIA_STRYKER.get(m["mutatorName"], "Outro") in _COMUNS for m in ms_]
    base["node"] = {"gerados": len(ms_), "detectados": sum(det), "validos": sum(val),
                    "mutation_score": 100 * sum(det) / sum(val),
                    "mutation_score_comuns": 100 * sum(d for d, c in zip(det, com) if c) / sum(v for v, c in zip(val, com) if c)}
resumo["baseline_exemplos"] = base

# Recorte por subtipo: mutantes de limite (< <-> <=, > <-> >=) existem nas duas ferramentas
# (ConditionalsBoundary no PIT; parte do EqualityOperator no StrykerJS).
import re as _re
def _op(t):
    g = _re.search(r"(===|!==|==|!=|<=|>=|<|>)", t)
    return g.group(1) if g else "?"
lim = {"node": {"limite": [0, 0], "negacao": [0, 0]}}
for rd in sorted((RAIZ / "data" / "raw" / "node").glob("run-*")):
    rel = json.loads((rd / "mutation.json").read_text())
    for f, a in rel["files"].items():
        L = (RAIZ / "node-api" / f).read_text().splitlines()
        for m in a["mutants"]:
            if m["mutatorName"] != "EqualityOperator" or m["status"] not in ("Killed", "Timeout", "Survived", "NoCoverage"):
                continue
            st, en = m["location"]["start"], m["location"]["end"]
            o, r_ = _op(L[st["line"] - 1][st["column"] - 1:en["column"] - 1]), _op(m["replacement"])
            tipo = "limite" if {o, r_} in ({"<", "<="}, {">", ">="}) else "negacao"
            lim["node"][tipo][0] += m["status"] in ("Killed", "Timeout")
            lim["node"][tipo][1] += 1
jb = mut[(mut.ecossistema == "java") & (mut.operador == "ConditionalsBoundaryMutator") & mut.valido]
lim["java"] = {"limite": [int(jb.detectado.sum()), int(len(jb))]}
resumo["mutantes_limite"] = {e: {t: {"detectados_por_execucao": v[0] / N_EXEC[e], "total_por_execucao": v[1] / N_EXEC[e],
                                     "mutation_score": 100 * v[0] / v[1]} for t, v in d.items()} for e, d in lim.items()}

resumo["qui_quadrado_comuns"] = qui
resumo["mutantes_instaveis"] = instaveis.groupby("ecossistema").size().to_dict()
resumo["mutantes_por_execucao"] = (mut[mut.valido].groupby("ecossistema").size() /
                                   pd.Series(N_EXEC)).to_dict()
(OUT / "resumo.json").write_text(json.dumps(resumo, indent=2, ensure_ascii=False, default=float))

# ------------------------------------------------------------------ figuras
# Fig 5.1 – distribuição do mutation score por execução (três recortes)
fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.6), sharey=True)
recortes = [("mutation_score", "Todos os mutantes"), ("mutation_score_comuns", "Categorias comuns"),
            ("mutation_score_sem_acessores", "Sem construtores/acessores")]
rng = np.random.default_rng(7)
for ax, (col, titulo) in zip(axes, recortes):
    for i, eco in enumerate(["java", "node"]):
        v = runs[runs.ecossistema == eco][col].to_numpy()
        ax.boxplot(v, positions=[i], widths=0.5, patch_artist=True, showfliers=False,
                   boxprops=dict(facecolor=COR[eco] + "33", edgecolor=COR[eco], linewidth=1.2),
                   medianprops=dict(color=COR[eco], linewidth=2), whiskerprops=dict(color=COR[eco]),
                   capprops=dict(color=COR[eco]))
        ax.scatter(i + rng.uniform(-0.12, 0.12, len(v)), v, s=9, color=COR[eco], alpha=0.7,
                   edgecolor="white", linewidth=0.4, zorder=3)
    ax.set_xticks([0, 1], [ROTULO["java"], ROTULO["node"]])
    ax.set_title(titulo, fontsize=9, color=TINTA)
    ax.set_xlim(-0.6, 1.6)
lo = min(runs[c].min() for c, _ in recortes)
hi = max(runs[c].max() for c, _ in recortes)
axes[0].set_ylim(np.floor(lo) - 2, np.ceil(hi) + 2)
axes[0].set_ylabel("Mutation score (%)")
fig.tight_layout()
salvar(fig, "fig5_1_boxplot_mutation_score")

# Fig 5.2 – mutation score por módulo
fig, ax = plt.subplots(figsize=(7.2, 2.8))
mods = [m for m in MODULOS if m in set(por_mod.modulo)]
x = np.arange(len(mods))
w = 0.38
for k, eco in enumerate(["java", "node"]):
    d = por_mod[por_mod.ecossistema == eco].set_index("modulo").reindex(mods)
    barras = ax.bar(x + (k - 0.5) * w, d.mutation_score, w - 0.04, color=COR[eco], label=ROTULO[eco])
    for xi, (ms, q) in enumerate(zip(d.mutation_score, d.mutantes_por_execucao)):
        if not np.isnan(ms):
            ax.text(xi + (k - 0.5) * w, ms + 1.5, f"{ms:.0f}", ha="center", va="bottom", fontsize=7, color=TINTA2)
CURTO = {"Infraestrutura": "Infra.", ACESSORES: "Constr./\nacessores", "Disponibilidade": "Disponi-\nbilidade"}
ax.set_xticks(x, [CURTO.get(m, m) for m in mods], fontsize=8)
ax.set_ylabel("Mutation score (%)")
ax.set_ylim(0, 112)
ax.legend(loc="upper left", ncol=2, bbox_to_anchor=(0, 1.12))
fig.tight_layout()
salvar(fig, "fig5_2_score_por_modulo")

# Fig 5.3 – cobertura de mutantes × mutation score por módulo (halteres)
fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=True)
ordem = [m for m in MODULOS if m in set(por_mod.modulo)][::-1]
for ax, eco in zip(axes, ["java", "node"]):
    d = por_mod[por_mod.ecossistema == eco].set_index("modulo").reindex(ordem)
    y = np.arange(len(ordem))
    for yi, (c, m) in enumerate(zip(d.cobertura_mutantes, d.mutation_score)):
        if np.isnan(c):
            continue
        ax.plot([m, c], [yi, yi], color=GRADE, linewidth=3, zorder=1, solid_capstyle="round")
        ax.scatter(c, yi, s=34, facecolor="white", edgecolor=COR[eco], linewidth=1.5, zorder=3)
        ax.scatter(m, yi, s=34, color=COR[eco], zorder=4)
        ax.text(min(c, 100) + 3, yi, f"{c - m:.0f} p.p.", va="center", fontsize=7, color=TINTA2)
    ax.set_yticks(y, ["Constr./acessores" if m == ACESSORES else m for m in ordem], fontsize=8)
    ax.set_xlim(0, 118)
    ax.set_xticks([0, 20, 40, 60, 80, 100])
    ax.set_xlabel("%")
    ax.set_title(ECO[eco], fontsize=8.5, color=TINTA)
    ax.grid(axis="y", visible=False)
from matplotlib.lines import Line2D
leg = [Line2D([], [], marker="o", linestyle="", markerfacecolor="white", markeredgecolor=TINTA2, label="Mutantes cobertos (%)"),
       Line2D([], [], marker="o", linestyle="", color=TINTA2, label="Mutation score (%)")]
fig.legend(handles=leg, loc="upper center", ncol=2, fontsize=7.5, bbox_to_anchor=(0.55, 1.04))
fig.tight_layout()
salvar(fig, "fig5_3_cobertura_vs_score")

# Fig 5.4 – mutantes por categoria e status (média por execução)
cats = ["Aritmético", "Relacional", "Condicional/lógico", "Remoção de instrução", "Incremento",
        "Valor de retorno", "Literal", "Chamada de método"]
fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9), sharey=True, sharex=True)
for ax, eco in zip(axes, ["java", "node"]):
    d = por_cat[por_cat.ecossistema == eco].set_index("categoria").reindex(cats).fillna(0)
    ne = N_EXEC[eco]
    det = (d.KILLED + d.TIMEOUT) / ne
    sob = d.SURVIVED / ne
    sc = d.NO_COVERAGE / ne
    y = np.arange(len(cats))[::-1]
    ax.barh(y, det, color=COR_STATUS["Detectado"], label="Detectado", height=0.7)
    ax.barh(y, sob, left=det, color=COR_STATUS["Sobrevivente"], label="Sobrevivente", height=0.7,
            edgecolor="white", linewidth=1)
    ax.barh(y, sc, left=det + sob, color=COR_STATUS["Sem cobertura"], label="Sem cobertura", height=0.7,
            edgecolor="white", linewidth=1)
    for yi, tot in zip(y, det + sob + sc):
        if tot > 0:
            ax.text(tot + 1, yi, f"{tot:.0f}", va="center", fontsize=7, color=TINTA2)
    ax.set_yticks(y, [c + (" *" if c in COMUNS else "") for c in cats], fontsize=8)
    ax.set_title(ECO[eco], fontsize=8.5, color=TINTA)
    ax.set_xlabel("Mutantes por execução (média)")
    ax.set_xlim(0, 92)
    ax.grid(axis="y", visible=False)
axes[0].legend(loc="upper center", ncol=3, fontsize=7.5, bbox_to_anchor=(1.05, -0.22))
fig.tight_layout()
fig.subplots_adjust(wspace=0.08)
salvar(fig, "fig5_4_categorias_status")

# Fig 5.5 – mutantes mortos por propriedade (média por execução)
fig, ax = plt.subplots(figsize=(7.2, 2.6))
props = [f"P{i}" for i in range(1, 9)]
x = np.arange(len(props))
det_media = mut[mut.detectado].groupby("ecossistema").size() / pd.Series(N_EXEC)
for k, eco in enumerate(["java", "node"]):
    d = por_prop[por_prop.ecossistema == eco].set_index("propriedade").reindex(props)
    base = det_media[eco]
    ax.bar(x + (k - 0.5) * w, 100 * d.mortos / base, w - 0.04, color=COR[eco], label=f"{ROTULO[eco]} – mata",
           alpha=0.35)
    ax.bar(x + (k - 0.5) * w, 100 * d.exclusivos / base, w - 0.04, color=COR[eco],
           label=f"{ROTULO[eco]} – só ela mata")
ax.set_xticks(x, props)
ax.set_ylabel("% dos mutantes detectados")
ax.legend(ncol=4, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, 1.18))
fig.tight_layout()
salvar(fig, "fig5_5_mortos_por_propriedade")

# Fig 5.6 – tempo da análise de mutação
fig, ax = plt.subplots(figsize=(4.0, 2.6))
for i, eco in enumerate(["java", "node"]):
    v = runs[runs.ecossistema == eco].tempo_mutacao_s.to_numpy()
    ax.boxplot(v, positions=[i], widths=0.5, patch_artist=True, showfliers=False,
               boxprops=dict(facecolor=COR[eco] + "33", edgecolor=COR[eco], linewidth=1.2),
               medianprops=dict(color=COR[eco], linewidth=2), whiskerprops=dict(color=COR[eco]),
               capprops=dict(color=COR[eco]))
    ax.scatter(i + rng.uniform(-0.12, 0.12, len(v)), v, s=9, color=COR[eco], alpha=0.7,
               edgecolor="white", linewidth=0.4, zorder=3)
ax.set_xticks([0, 1], [ROTULO["java"] + "\n(PIT)", ROTULO["node"] + "\n(StrykerJS)"])
ax.set_ylabel("Tempo da análise de mutação (s)")
ax.set_xlim(-0.6, 1.6)
fig.tight_layout()
salvar(fig, "fig5_6_tempo_mutacao")

print(testes.round(4).to_string())
print(json.dumps({k: resumo[k]["mutation_score"] for k in ("java", "node")}, indent=1, default=float))
