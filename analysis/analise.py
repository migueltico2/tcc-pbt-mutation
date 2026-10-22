#!/usr/bin/env python3
"""Análise do experimento fatorial (versão 2): tabelas, testes estatísticos e figuras do capítulo 5.

Fatores: ecossistema (java, node) × suíte (fraca = P1–P8, forte = P1–P17) × tentativas (10, 100, 1000),
30 execuções por configuração. Recortes de operadores: padrão (conjunto padrão de cada ferramenta)
e harmonizado (classes de mutação com equivalente direto nas duas ferramentas).

Entrada: data/runs.csv e data/mutants.csv (scripts/consolidate.py) e data/raw/v2/baseline-exemplos
Saída:   analysis/resultados/*.csv, analysis/resultados/resumo.json e analysis/figuras/*.pdf|png
"""
import gzip
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
from scipy import stats

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "analysis" / "resultados"
FIG = RAIZ / "analysis" / "figuras"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(RAIZ / "scripts"))
from consolidate import PADRAO_PIT, HARMONIZADO_PIT, HARMONIZADO_STRYKER, classe_equality  # noqa: E402

ECOS = ["java", "node"]
SUITES = ["fraca", "forte"]
TENT = [10, 100, 1000]
ROTULO = {"java": "Java", "node": "Node.js"}
ROT_SUITE = {"fraca": "Suíte fraca (P1–P8)", "forte": "Suíte forte (P1–P17)"}
COR = {"java": "#2a78d6", "node": "#eb6834"}            # slots 1 e 2 da paleta categórica validada
ESTILO = {"fraca": "--", "forte": "-"}
MARCA = {"fraca": "o", "forte": "s"}
TINTA, TINTA2, GRADE = "#0b0b0b", "#52514e", "#e4e3df"
ACESSORES = "Modelos (construtores e acessores)"
MODULOS = ["Eventos", "Lotes", "Reservas", "Cupons", "Disponibilidade", "Status", "Infraestrutura", ACESSORES]
CLASSES_HARM = ["aritmético", "limite relacional", "negação relacional", "condição forçada", "incremento"]
REF_T = 100                                               # configuração de referência (padrão das ferramentas)

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
mut["padrao"] = mut.padrao.astype(int).astype(bool)
mut = mut[mut.valido]
N_EXEC = runs.groupby(["ecossistema", "suite", "tentativas"]).execucao.nunique()


def salvar(fig, nome):
    fig.savefig(FIG / f"{nome}.pdf")
    fig.savefig(FIG / f"{nome}.png", dpi=200)
    plt.close(fig)


def a12(x, y):
    """Vargha-Delaney Â12: probabilidade de um valor de x superar um de y (empates contam meio)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    maior = (x[:, None] > y[None, :]).sum()
    igual = (x[:, None] == y[None, :]).sum()
    return (maior + 0.5 * igual) / (len(x) * len(y))


def magnitude(a):
    d = abs(a - 0.5)
    return "desprezível" if d < 0.06 else "pequena" if d < 0.14 else "média" if d < 0.21 else "grande"


def mw(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    if np.ptp(np.concatenate([x, y])) == 0:
        return float("nan"), 1.0
    r = stats.mannwhitneyu(x, y, alternative="two-sided")
    return float(r.statistic), float(r.pvalue)


def holm(p):
    p = np.asarray(p, float)
    ordem = np.argsort(p)
    m = len(p)
    ajust = np.empty(m)
    acum = 0.0
    for k, i in enumerate(ordem):
        acum = max(acum, (m - k) * p[i])
        ajust[i] = min(1.0, acum)
    return ajust


def desc(s):
    s = pd.Series(s, dtype=float)
    return {"media": s.mean(), "dp": s.std(ddof=1), "mediana": s.median(), "min": s.min(), "max": s.max(),
            "q1": s.quantile(0.25), "q3": s.quantile(0.75)}


def cfg(eco, suite, t):
    return runs[(runs.ecossistema == eco) & (runs.suite == suite) & (runs.tentativas == t)]


# ------------------------------------------------------------------ resumo por configuração
linhas = []
for (eco, suite, t), g in runs.groupby(["ecossistema", "suite", "tentativas"]):
    linha = {"ecossistema": eco, "suite": suite, "tentativas": t, "execucoes": len(g)}
    for col in ["mutation_score", "mutation_score_harmonizado", "mutation_score_sem_acessores",
                "mutation_score_todos_operadores", "gerados", "gerados_harmonizado", "gerados_todos_operadores",
                "mortos", "timeout", "sobreviventes", "sem_cobertura", "erros", "cobertura_linhas",
                "cobertura_ramos", "tempo_suite_s", "tempo_mutacao_s", "tempo_por_mutante_s"]:
        for k, v in desc(g[col]).items():
            linha[f"{col}_{k}"] = v
    linhas.append(linha)
resumo_cfg = pd.DataFrame(linhas)
resumo_cfg.to_csv(OUT / "resumo_configuracoes.csv", index=False)

# ------------------------------------------------------------------ testes de hipótese
testes = []


def registrar(hipotese, contexto, metrica, a_rot, b_rot, x, y):
    u, p = mw(x, y)
    a = a12(x, y)
    testes.append({"hipotese": hipotese, "contexto": contexto, "metrica": metrica, "grupo_a": a_rot,
                   "grupo_b": b_rot, "mediana_a": float(np.median(x)), "mediana_b": float(np.median(y)),
                   "U": u, "p_valor": p, "A12": a, "magnitude": magnitude(a)})


# H0,1 – ecossistema (Java × Node.js), em cada suíte × tentativas, nos dois recortes de operadores
for suite in SUITES:
    for t in TENT:
        for metrica in ["mutation_score", "mutation_score_harmonizado"]:
            registrar("H0,1 ecossistema", f"{suite}, t={t}", metrica, "java", "node",
                      cfg("java", suite, t)[metrica], cfg("node", suite, t)[metrica])
# H0,2 – suíte (forte × fraca), em cada ecossistema × tentativas
for eco in ECOS:
    for t in TENT:
        registrar("H0,2 suíte", f"{eco}, t={t}", "mutation_score", "forte", "fraca",
                  cfg(eco, "forte", t).mutation_score, cfg(eco, "fraca", t).mutation_score)
# H0,3 – tentativas (pares consecutivos), em cada ecossistema × suíte
kruskal = []
for eco in ECOS:
    for suite in SUITES:
        grupos = [cfg(eco, suite, t).mutation_score.to_numpy() for t in TENT]
        if np.ptp(np.concatenate(grupos)) == 0:
            h, p = float("nan"), 1.0
        else:
            h, p = stats.kruskal(*grupos)
        kruskal.append({"ecossistema": eco, "suite": suite, "H": h, "p_valor": p})
        for t1, t2 in [(100, 10), (1000, 100)]:
            registrar("H0,3 tentativas", f"{eco}, {suite}", "mutation_score", f"t={t1}", f"t={t2}",
                      cfg(eco, suite, t1).mutation_score, cfg(eco, suite, t2).mutation_score)
# H0,4 – tempo da análise de mutação (Java × Node.js) e tempo por mutante
for suite in SUITES:
    for t in TENT:
        for metrica in ["tempo_mutacao_s", "tempo_por_mutante_s"]:
            registrar("H0,4 tempo", f"{suite}, t={t}", metrica, "java", "node",
                      cfg("java", suite, t)[metrica], cfg("node", suite, t)[metrica])
testes = pd.DataFrame(testes)
testes["p_holm"] = holm(testes.p_valor)
testes.to_csv(OUT / "testes_estatisticos.csv", index=False)
kruskal = pd.DataFrame(kruskal)
kruskal["p_holm"] = holm(kruskal.p_valor)
kruskal.to_csv(OUT / "kruskal_tentativas.csv", index=False)

# Qui-quadrado por mutante distinto (recorte harmonizado, t = 100): unidade = mutante distinto,
# detectado se foi detectado na maioria das execuções (não mutante × execução, que inflaria a amostra).
qui = {}
for suite in SUITES:
    sub = mut[(mut.suite == suite) & (mut.tentativas == REF_T) & (mut.harmonizado != "")]
    pm = sub.groupby(["ecossistema", "mutante_id"]).detectado.mean().ge(0.5).reset_index()
    cont = pm.groupby("ecossistema").detectado.agg(["sum", "count"])
    tab = np.array([[cont.loc[e, "sum"], cont.loc[e, "count"] - cont.loc[e, "sum"]] for e in ECOS])
    chi2, p, _, _ = stats.chi2_contingency(tab)
    qui[suite] = {"tabela_detectado_nao": tab.tolist(), "chi2": float(chi2), "p_valor": float(p),
                  "fisher_p": float(stats.fisher_exact(tab).pvalue)}

# ------------------------------------------------------------------ recortes por mutante (t = referência)
ref = mut[mut.tentativas == REF_T]

# por classe harmonizada
ph = (ref[ref.harmonizado != ""].groupby(["ecossistema", "suite", "harmonizado"])
      .agg(avaliacoes=("detectado", "size"), detectados=("detectado", "sum")).reset_index())
ph["por_execucao"] = ph.apply(lambda r: r.avaliacoes / N_EXEC[(r.ecossistema, r.suite, REF_T)], axis=1)
ph["mutation_score"] = 100 * ph.detectados / ph.avaliacoes
ph.to_csv(OUT / "por_classe_harmonizada.csv", index=False)

# por módulo (operadores padrão)
pmod = (ref[ref.padrao].groupby(["ecossistema", "suite", "modulo"])
        .agg(avaliacoes=("detectado", "size"), detectados=("detectado", "sum"),
             sem_cobertura=("status", lambda s: (s == "NO_COVERAGE").sum())).reset_index())
pmod["mutation_score"] = 100 * pmod.detectados / pmod.avaliacoes
pmod["cobertura_mutantes"] = 100 * (pmod.avaliacoes - pmod.sem_cobertura) / pmod.avaliacoes
pmod.to_csv(OUT / "por_modulo.csv", index=False)

# por operador (todos os operadores, para transparência)
pop = (ref.groupby(["ecossistema", "suite", "operador", "padrao", "harmonizado"])
       .agg(avaliacoes=("detectado", "size"), detectados=("detectado", "sum")).reset_index())
pop["mutation_score"] = 100 * pop.detectados / pop.avaliacoes
pop.to_csv(OUT / "por_operador.csv", index=False)

# por propriedade (suíte forte, t = referência, operadores padrão): % dos detectados que cada propriedade mata
PROPS = [f"P{i}" for i in range(1, 18)]
linhas = []
for (eco, suite, ex), g in ref[ref.padrao & ref.detectado].groupby(["ecossistema", "suite", "execucao"]):
    listas = g.propriedades_que_mataram.str.split("|")
    for p in PROPS:
        linhas.append({"ecossistema": eco, "suite": suite, "execucao": ex, "propriedade": p,
                       "mata": 100 * listas.apply(lambda l: p in l).mean(),
                       "exclusivo": 100 * (g.propriedades_que_mataram == p).mean()})
pprop = pd.DataFrame(linhas).groupby(["ecossistema", "suite", "propriedade"])[["mata", "exclusivo"]].mean().reset_index()
pprop.to_csv(OUT / "por_propriedade.csv", index=False)

# estabilidade: mutantes com resultado diferente entre execuções da mesma configuração
est = (mut.groupby(["ecossistema", "suite", "tentativas", "mutante_id"]).detectado
       .agg(["sum", "size"]).reset_index())
est["instavel"] = (est["sum"] > 0) & (est["sum"] < est["size"])
instaveis = est.groupby(["ecossistema", "suite", "tentativas"]).instavel.sum().reset_index()
instaveis.to_csv(OUT / "mutantes_instaveis.csv", index=False)

# ------------------------------------------------------------------ linha de base (só exemplos)
base = {}
bdir = RAIZ / "data" / "raw" / "v2" / "baseline-exemplos"
if (bdir / "java-pit" / "mutations.xml.gz").exists():
    with gzip.open(bdir / "java-pit" / "mutations.xml.gz") as f:
        root = ET.parse(f).getroot()
    ms_ = [(m.get("status"), m.findtext("mutator").split(".")[-1]) for m in root.findall("mutation")]
    val = [(s in ("KILLED", "TIMED_OUT", "MEMORY_ERROR"), op) for s, op in ms_ if s != "RUN_ERROR"]
    pad = [d for d, op in val if op in PADRAO_PIT]
    har = [d for d, op in val if op in HARMONIZADO_PIT]
    base["java"] = {"gerados_padrao": len(pad), "mutation_score": 100 * np.mean(pad),
                    "gerados_harmonizado": len(har), "mutation_score_harmonizado": 100 * np.mean(har)}
if (bdir / "node-mutation.json.gz").exists():
    with gzip.open(bdir / "node-mutation.json.gz") as f:
        rel = json.load(f)
    pad, har = [], []
    for caminho, arq in rel["files"].items():
        fonte = (RAIZ / "node-api" / caminho).read_text().splitlines()
        for m in arq["mutants"]:
            if m["status"] not in ("Killed", "Timeout", "Survived", "NoCoverage"):
                continue
            d = m["status"] in ("Killed", "Timeout")
            pad.append(d)
            if m["mutatorName"] == "EqualityOperator":
                ini, fim = m["location"]["start"], m["location"]["end"]
                h = classe_equality(fonte[ini["line"] - 1][ini["column"] - 1:fim["column"] - 1], m.get("replacement", ""))
            else:
                h = HARMONIZADO_STRYKER.get(m["mutatorName"], "")
            if h:
                har.append(d)
    base["node"] = {"gerados_padrao": len(pad), "mutation_score": 100 * np.mean(pad),
                    "gerados_harmonizado": len(har), "mutation_score_harmonizado": 100 * np.mean(har)}

resumo = {
    "execucoes_por_configuracao": {f"{e}/{s}/t{t}": int(n) for (e, s, t), n in N_EXEC.items()},
    "total_execucoes": int(len(runs)),
    "total_avaliacoes_de_mutantes": int(len(mut)),
    "mutantes_distintos": {e: int(mut[mut.ecossistema == e].mutante_id.nunique()) for e in ECOS},
    "qui_quadrado_harmonizado_t100": qui,
    "baseline_exemplos": base,
    "kruskal_tentativas": kruskal.to_dict(orient="records"),
}
(OUT / "resumo.json").write_text(json.dumps(resumo, indent=2, ensure_ascii=False, default=float))

# ------------------------------------------------------------------ figuras
X = {10: 0, 100: 1, 1000: 2}


def painel_tentativas(ax, coluna, titulo):
    for eco in ECOS:
        for suite in SUITES:
            med, q1, q3 = [], [], []
            for t in TENT:
                v = cfg(eco, suite, t)[coluna]
                med.append(v.median()); q1.append(v.quantile(0.25)); q3.append(v.quantile(0.75))
            xs = np.array([X[t] for t in TENT]) + (-0.05 if eco == "java" else 0.05)
            ax.plot(xs, med, ESTILO[suite], color=COR[eco], linewidth=2, zorder=3)
            ax.vlines(xs, q1, q3, color=COR[eco], linewidth=2, alpha=0.5, zorder=2)
            ax.scatter(xs, med, marker=MARCA[suite], s=36, color=COR[eco], edgecolor="white", linewidth=1.2, zorder=4)
    ax.set_xticks([0, 1, 2], ["10", "100", "1000"])
    ax.set_xlabel("Tentativas por propriedade")
    ax.set_title(titulo, fontsize=9, color=TINTA)
    ax.set_xlim(-0.3, 2.3)


# Fig 5.1 – mutation score por tentativas, suíte e ecossistema (mediana e intervalo interquartil)
fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=True)
painel_tentativas(axes[0], "mutation_score", "Operadores padrão de cada ferramenta")
painel_tentativas(axes[1], "mutation_score_harmonizado", "Operadores harmonizados")
axes[0].set_ylabel("Mutation score (%)")
axes[0].set_ylim(40, 100)
leg = [Line2D([], [], color=COR["java"], linewidth=2, label="Java"),
       Line2D([], [], color=COR["node"], linewidth=2, label="Node.js"),
       Line2D([], [], color=TINTA2, linestyle="-", marker="s", label="Suíte forte (P1–P17)"),
       Line2D([], [], color=TINTA2, linestyle="--", marker="o", label="Suíte fraca (P1–P8)")]
fig.legend(handles=leg, loc="upper center", ncol=4, fontsize=7.5, bbox_to_anchor=(0.53, 1.06))
fig.tight_layout()
salvar(fig, "fig5_1_score_tentativas")

# Fig 5.2 – mutation score por classe harmonizada (t = 100), por suíte
fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.6), sharey=True, sharex=True)
classes = [c for c in CLASSES_HARM if c != "incremento"]
y = np.arange(len(classes))[::-1]
for ax, suite in zip(axes, SUITES):
    for k, eco in enumerate(ECOS):
        d = ph[(ph.ecossistema == eco) & (ph.suite == suite)].set_index("harmonizado").reindex(classes)
        yy = y + (0.17 if eco == "java" else -0.17)
        ax.barh(yy, d.mutation_score, height=0.32, color=COR[eco], label=ROTULO[eco])
        for yi, v, n in zip(yy, d.mutation_score, d.por_execucao):
            ax.text(v + 1.5, yi, f"{v:.0f}% (n={n:.0f})", va="center", fontsize=6.5, color=TINTA2)
    ax.set_yticks(y, classes, fontsize=8)
    ax.set_xlim(0, 125)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel("Mutation score (%)")
    ax.set_title(ROT_SUITE[suite] + ", 100 tentativas", fontsize=8.5, color=TINTA)
    ax.grid(axis="y", visible=False)
fig.legend(handles=[Line2D([], [], color=COR["java"], linewidth=6, label="Java"),
                    Line2D([], [], color=COR["node"], linewidth=6, label="Node.js")],
           loc="upper center", ncol=2, fontsize=7.5, bbox_to_anchor=(0.55, 1.07))
fig.tight_layout()
salvar(fig, "fig5_2_classes_harmonizadas")

# Fig 5.3 – cobertura de mutantes × mutation score por módulo (t = 100), suíte fraca e forte
ordem = [m for m in MODULOS if m in set(pmod.modulo)]
fig, axes = plt.subplots(2, 2, figsize=(7.2, 4.6), sharex=True, sharey=True)
for i, suite in enumerate(SUITES):
    for j, eco in enumerate(ECOS):
        ax = axes[i, j]
        d = pmod[(pmod.ecossistema == eco) & (pmod.suite == suite)].set_index("modulo").reindex(ordem)
        yy = np.arange(len(ordem))[::-1]
        for yi, (c, s) in zip(yy, zip(d.cobertura_mutantes, d.mutation_score)):
            if np.isnan(c):
                continue
            ax.plot([s, c], [yi, yi], color=GRADE, linewidth=3, zorder=1, solid_capstyle="round")
            ax.scatter(c, yi, s=30, facecolor="white", edgecolor=COR[eco], linewidth=1.4, zorder=3)
            ax.scatter(s, yi, s=30, color=COR[eco], zorder=4)
            ax.text(min(c, 100) + 3, yi, f"{c - s:.0f}", va="center", fontsize=6.5, color=TINTA2)
        ax.set_yticks(yy, ["Constr./acessores" if m == ACESSORES else m for m in ordem], fontsize=7.5)
        ax.set_xlim(0, 112)
        ax.set_title(f"{ROTULO[eco]} – {ROT_SUITE[suite]}", fontsize=8, color=TINTA)
        ax.grid(axis="y", visible=False)
for ax in axes[1]:
    ax.set_xlabel("%")
leg = [Line2D([], [], marker="o", linestyle="", markerfacecolor="white", markeredgecolor=TINTA2, label="Mutantes cobertos (%)"),
       Line2D([], [], marker="o", linestyle="", color=TINTA2, label="Mutation score (%)")]
fig.legend(handles=leg, loc="upper center", ncol=2, fontsize=7.5, bbox_to_anchor=(0.55, 1.03))
fig.tight_layout()
salvar(fig, "fig5_3_cobertura_vs_score")

# Fig 5.4 – contribuição de cada propriedade na suíte forte (t = 100)
fig, ax = plt.subplots(figsize=(7.2, 2.7))
x = np.arange(len(PROPS))
w = 0.4
for k, eco in enumerate(ECOS):
    d = pprop[(pprop.ecossistema == eco) & (pprop.suite == "forte")].set_index("propriedade").reindex(PROPS)
    ax.bar(x + (k - 0.5) * w, d.mata, w - 0.04, color=COR[eco], alpha=0.35, label=f"{ROTULO[eco]} – mata")
    ax.bar(x + (k - 0.5) * w, d.exclusivo, w - 0.04, color=COR[eco], label=f"{ROTULO[eco]} – só ela mata")
ax.axvline(7.5, color=TINTA2, linewidth=0.8, linestyle=":")
ax.text(3.5, 101, "fraca (TCC I)", ha="center", fontsize=7, color=TINTA2)
ax.text(12, 101, "acrescentadas na suíte forte", ha="center", fontsize=7, color=TINTA2)
ax.set_xticks(x, PROPS, fontsize=7.5)
ax.set_ylim(0, 108)
ax.set_ylabel("% dos mutantes detectados")
ax.legend(ncol=4, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, 1.2))
fig.tight_layout()
salvar(fig, "fig5_4_mortos_por_propriedade")

# Fig 5.5 – tempo por mutante
fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.7), sharey=False)
painel_tentativas(axes[0], "tempo_mutacao_s", "Tempo total da análise de mutação")
axes[0].set_ylabel("Segundos")
painel_tentativas(axes[1], "tempo_por_mutante_s", "Tempo por mutante avaliado")
axes[1].set_ylabel("Segundos por mutante")
fig.legend(handles=leg_t if (leg_t := [Line2D([], [], color=COR["java"], linewidth=2, label="Java (PIT)"),
                                       Line2D([], [], color=COR["node"], linewidth=2, label="Node.js (StrykerJS)"),
                                       Line2D([], [], color=TINTA2, linestyle="-", marker="s", label="Suíte forte"),
                                       Line2D([], [], color=TINTA2, linestyle="--", marker="o", label="Suíte fraca")]) else None,
           loc="upper center", ncol=4, fontsize=7.5, bbox_to_anchor=(0.53, 1.06))
fig.tight_layout()
salvar(fig, "fig5_5_tempo")

print(resumo_cfg[["ecossistema", "suite", "tentativas", "execucoes", "mutation_score_mediana", "mutation_score_dp",
                  "mutation_score_harmonizado_mediana", "tempo_mutacao_s_mediana"]].round(2).to_string())
print(testes[["hipotese", "contexto", "metrica", "mediana_a", "mediana_b", "p_holm", "A12", "magnitude"]].round(4).to_string())
print(json.dumps(qui, indent=1))


# ------------------------------------------------------------------ números citados no artigo
# Cada número do capítulo de resultados vem daqui (artigo/numeros.tex), para evitar transcrição manual.
def br(v, casas=1):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "--"
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", "\\,")


def pval(p):
    if p < 0.001:
        return "$p < 0{,}001$"
    return "$p = " + br(p, 3).replace("\\,", "").replace(",", "{,}") + "$"


NOMES = {"java": "Java", "node": "Node", "fraca": "Fraca", "forte": "Forte", 10: "Dez", 100: "Cem", 1000: "Mil"}
cmds = []


def cmd(nome, valor):
    cmds.append(f"\\newcommand{{\\{nome}}}{{{valor}}}")


for (eco, suite, t), g in runs.groupby(["ecossistema", "suite", "tentativas"]):
    base_nome = f"{NOMES[eco]}{NOMES[suite]}{NOMES[t]}"
    cmd(f"ms{base_nome}", br(g.mutation_score.median()))
    cmd(f"msq{base_nome}", f"{br(g.mutation_score.quantile(.25))}--{br(g.mutation_score.quantile(.75))}")
    cmd(f"msh{base_nome}", br(g.mutation_score_harmonizado.median()))
    cmd(f"cobl{base_nome}", br(g.cobertura_linhas.median()))
    cmd(f"cobr{base_nome}", br(g.cobertura_ramos.median()))
    cmd(f"tmut{base_nome}", br(g.tempo_mutacao_s.median()))
    cmd(f"tpm{base_nome}", br(g.tempo_por_mutante_s.median(), 2))
    cmd(f"tsuite{base_nome}", br(g.tempo_suite_s.median(), 2))
    cmd(f"ger{base_nome}", br(g.gerados.median(), 0))
    cmd(f"gerh{base_nome}", br(g.gerados_harmonizado.median(), 0))
    cmd(f"gert{base_nome}", br(g.gerados_todos_operadores.median(), 0))
    cmd(f"inst{base_nome}", str(int(instaveis[(instaveis.ecossistema == eco) & (instaveis.suite == suite)
                                               & (instaveis.tentativas == t)].instavel.iloc[0])))
HIP = {"H0,1": "Eco", "H0,2": "Suite", "H0,3": "Tent", "H0,4": "Tempo"}
MET = {"mutation_score": "", "mutation_score_harmonizado": "Harm", "tempo_mutacao_s": "Total",
       "tempo_por_mutante_s": "Mutante"}
for tst in testes.itertuples():
    partes = [HIP[tst.hipotese.split()[0]]]
    for item in tst.contexto.split(", "):
        partes.append(NOMES[int(item[2:])] if item.startswith("t=") else NOMES[item])
    if partes[0] == "Tent":
        partes.append(NOMES[int(tst.grupo_a[2:])])
    nome = "".join(partes) + MET[tst.metrica]
    cmd(f"aum{nome}", br(tst.A12, 2))
    cmd(f"p{nome}", pval(tst.p_holm))
    cmd(f"dec{nome}", "\\rejeita" if tst.p_holm < 0.05 else "\\naorejeita")
for k in kruskal.itertuples():
    cmd(f"kw{NOMES[k.ecossistema]}{NOMES[k.suite]}", pval(k.p_holm))
for suite in SUITES:
    cmd(f"chi{NOMES[suite]}", br(qui[suite]["chi2"], 2))
    cmd(f"pchi{NOMES[suite]}", pval(qui[suite]["p_valor"]))
for eco, b in base.items():
    cmd(f"base{NOMES[eco]}", br(b["mutation_score"]))
    cmd(f"baseh{NOMES[eco]}", br(b["mutation_score_harmonizado"]))
cmd("totalExecucoes", str(len(runs)))
cmd("totalAvaliacoes", br(len(mut), 0))
(RAIZ / "artigo" / "numeros.tex").write_text("% Gerado por analysis/analise.py — não editar à mão.\n" + "\n".join(cmds) + "\n")

# macros adicionais: classes harmonizadas, propriedades, módulos e linha de base por classe
EXT = ["Um", "Dois", "Tres", "Quatro", "Cinco", "Seis", "Sete", "Oito", "Nove", "Dez", "Onze", "Doze", "Treze",
       "Quatorze", "Quinze", "Dezesseis", "Dezessete"]
CLS = {"aritmético": "Arit", "limite relacional": "Limite", "negação relacional": "Negacao",
       "condição forçada": "Condicao", "incremento": "Incremento"}
for r in ph.itertuples():
    cmd(f"cls{NOMES[r.ecossistema]}{NOMES[r.suite]}{CLS[r.harmonizado]}", br(r.mutation_score))
    cmd(f"clsn{NOMES[r.ecossistema]}{NOMES[r.suite]}{CLS[r.harmonizado]}", br(r.por_execucao, 0))
for r in pprop.itertuples():
    k = EXT[int(r.propriedade[1:]) - 1]
    cmd(f"prop{NOMES[r.ecossistema]}{NOMES[r.suite]}{k}", br(r.mata, 0))
    cmd(f"propx{NOMES[r.ecossistema]}{NOMES[r.suite]}{k}", br(r.exclusivo, 0))
MOD = {"Eventos": "Eventos", "Lotes": "Lotes", "Reservas": "Reservas", "Cupons": "Cupons",
       "Disponibilidade": "Disponibilidade", "Status": "Status", "Infraestrutura": "Infra", ACESSORES: "Acessores"}
for r in pmod.itertuples():
    cmd(f"mod{NOMES[r.ecossistema]}{NOMES[r.suite]}{MOD[r.modulo]}", br(r.mutation_score, 0))
    cmd(f"modc{NOMES[r.ecossistema]}{NOMES[r.suite]}{MOD[r.modulo]}", br(r.cobertura_mutantes, 0))
(RAIZ / "artigo" / "numeros.tex").write_text("% Gerado por analysis/analise.py — não editar à mão.\n" + "\n".join(cmds) + "\n")
