#!/usr/bin/env python3
"""Importa a planilha revisada (analysis/revisao/revisao_sobreviventes.xlsx) para os resultados.

Classe final = classe revisada quando preenchida; senão, a pré-classificação.
Saídas: analysis/resultados/sobreviventes_final.csv, sobreviventes_por_classe_final.csv,
artigo/numeros_classes.tex (contagens usadas no artigo) e um resumo da concordância.
"""
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "analysis"))
from classificar_sobreviventes import escrever_macros  # noqa: E402

PLAN = RAIZ / "analysis" / "revisao" / "revisao_sobreviventes.xlsx"
RES = RAIZ / "analysis" / "resultados"

rev = pd.read_excel(PLAN, sheet_name="Mutantes", dtype=str, keep_default_na=False)
rev = rev[rev["Nº"] != "ex."]
rev["classe_final"] = [r if r.strip() else p for r, p in zip(rev["Classe revisada"], rev["Pré-classificação"])]
base = pd.read_csv(RES / "sobreviventes_classificados.csv", keep_default_na=False)
rev = rev.rename(columns={"ID do mutante (não editar)": "mutante_id", "Ecossistema": "ecossistema", "Suíte": "suite"})
final = base.merge(rev[["ecossistema", "suite", "mutante_id", "Classe revisada", "Comentário do revisor", "classe_final"]],
                   on=["ecossistema", "suite", "mutante_id"], how="left", validate="one_to_one")
assert final.classe_final.notna().all(), "planilha não corresponde a sobreviventes_classificados.csv"
final.to_csv(RES / "sobreviventes_final.csv", index=False)
(final.groupby(["ecossistema", "suite", "classe_final"]).size().unstack(fill_value=0)
 .to_csv(RES / "sobreviventes_por_classe_final.csv"))
escrever_macros(final, "classe_final")
revisados = final[final["Classe revisada"].str.strip() != ""]
concordam = (revisados["Classe revisada"] == revisados["classe"]).sum()
print(f"{len(final)} mutantes; {len(revisados)} revisados; {concordam} concordam; {len(revisados) - concordam} divergem")
