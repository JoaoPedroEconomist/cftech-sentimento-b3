"""Etapa 03.4 — concordância humano × LLM e análise de erros."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, cohen_kappa_score, confusion_matrix, f1_score

from . import config

CATEGORIAS_ERRO = [
    "ironia",
    "giria_meme",
    "emoji",
    "pergunta_como_opiniao",
    "contexto_de_grupo",
    "negacao_condicional",
    "manipulacao",
    "ticker_ambiguo",
    "ambiguidade_do_rotulo",
    "erro_humano",
    "outro",
]


def juntar(gabarito: pd.DataFrame, llm: pd.DataFrame, texto: pd.DataFrame | None = None) -> pd.DataFrame:
    gab = gabarito.copy()
    gab["id"] = gab["id"].astype(str)
    ll = llm.copy()
    ll["id"] = ll["id"].astype(str)
    m = gab.merge(ll[["id", "sentimento", "confianca", "ironia", "justificativa_curta"]], on="id", suffixes=("_hum", "_llm"))
    if texto is not None:
        tx = texto.copy()
        tx["id"] = tx["id"].astype(str)
        m = m.merge(tx[["id", "texto"]], on="id", how="left")
    return m


def kappa_llm(m: pd.DataFrame, labels=None) -> dict:
    labels = labels or config.SENTIMENTOS
    y, p = m["sentimento_hum"], m["sentimento_llm"]
    return {
        "n": len(m),
        "kappa": float(cohen_kappa_score(y, p, labels=labels)),
        "kappa_ponderado": float(cohen_kappa_score(y, p, labels=labels, weights="linear")),
        "acuracia": float(accuracy_score(y, p)),
        "f1_macro": float(f1_score(y, p, labels=labels, average="macro", zero_division=0)),
    }


def kappa_por_ironia(m: pd.DataFrame) -> pd.DataFrame:
    """Kappa separado para posts com e sem ironia (flag do gabarito humano)."""
    linhas = []
    for nome, sub in [("sem_ironia", m[m["ironia_hum"] == 0]), ("com_ironia", m[m["ironia_hum"] == 1])]:
        if len(sub) < 2 or sub["sentimento_hum"].nunique() < 2:
            linhas.append({"grupo": nome, "n": len(sub), "kappa": np.nan, "acuracia": float(accuracy_score(sub["sentimento_hum"], sub["sentimento_llm"])) if len(sub) else np.nan})
            continue
        k = cohen_kappa_score(sub["sentimento_hum"], sub["sentimento_llm"], labels=config.SENTIMENTOS)
        linhas.append({"grupo": nome, "n": len(sub), "kappa": float(k), "acuracia": float(accuracy_score(sub["sentimento_hum"], sub["sentimento_llm"]))})
    return pd.DataFrame(linhas)


def matriz_confusao(m: pd.DataFrame, labels=None) -> pd.DataFrame:
    labels = labels or config.SENTIMENTOS
    cm = confusion_matrix(m["sentimento_hum"], m["sentimento_llm"], labels=labels)
    return pd.DataFrame(cm, index=[f"hum_{l}" for l in labels], columns=[f"llm_{l}" for l in labels])


def deteccao_ironia(m: pd.DataFrame) -> dict:
    """Quão bem o LLM sinaliza ironia (flag humana vs flag do LLM)."""
    y, p = m["ironia_hum"].astype(int), m["ironia_llm"].astype(int)
    tp = int(((y == 1) & (p == 1)).sum())
    fp = int(((y == 0) & (p == 1)).sum())
    fn = int(((y == 1) & (p == 0)).sum())
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn) if tp + fn else float("nan")
    return {"vp": tp, "fp": fp, "fn": fn, "precisao": prec, "recall": rec}


def tabela_kappas(resultados: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """resultados = {'v1': merge_v1, 'v2': merge_v2} -> tabela comparativa (entregável 04)."""
    linhas = []
    for versao, m in resultados.items():
        k = kappa_llm(m)
        ki = kappa_por_ironia(m).set_index("grupo")
        linhas.append(
            {
                "versao": versao,
                "n": k["n"],
                "kappa": k["kappa"],
                "kappa_ponderado": k["kappa_ponderado"],
                "acuracia": k["acuracia"],
                "f1_macro": k["f1_macro"],
                "n_sem_ironia": int(ki.loc["sem_ironia", "n"]),
                "kappa_sem_ironia": ki.loc["sem_ironia", "kappa"],
                "acuracia_sem_ironia": ki.loc["sem_ironia", "acuracia"],
                "n_com_ironia": int(ki.loc["com_ironia", "n"]),
                "kappa_com_ironia": ki.loc["com_ironia", "kappa"],
                "acuracia_com_ironia": ki.loc["com_ironia", "acuracia"],
            }
        )
    return pd.DataFrame(linhas)


def discordancias(m: pd.DataFrame) -> pd.DataFrame:
    """Posts em que humano ≠ LLM, com coluna vazia `categoria_erro` para preenchimento MANUAL.

    Sugere uma categoria inicial por heurística só como ponto de partida (a decisão final é humana)."""
    d = m[m["sentimento_hum"] != m["sentimento_llm"]].copy()
    d["categoria_erro"] = d.apply(_sugestao_categoria, axis=1)
    d["categoria_erro_revisada"] = ""
    d["comentario"] = ""
    return d.reset_index(drop=True)


def _sugestao_categoria(r: pd.Series) -> str:
    if r.get("ironia_hum", 0) == 1:
        return "ironia"
    if r.get("giria_meme", 0) == 1:
        return "giria_meme"
    if r.get("suspeita_coordenacao", 0) == 1:
        return "manipulacao"
    if r.get("irrelevante", 0) == 1:
        return "ticker_ambiguo"
    txt = str(r.get("texto", ""))
    if "?" in txt:
        return "pergunta_como_opiniao"
    if any(ord(c) > 0x1F000 for c in txt):
        return "emoji"
    return "outro"


def catalogo_erros(disc: pd.DataFrame, coluna: str = "categoria_erro_revisada") -> pd.DataFrame:
    """Resume o catálogo (usa a categoria revisada pela dupla quando preenchida; senão a sugerida)."""
    cat = disc[coluna].where(disc[coluna].astype(str).str.len() > 0, disc["categoria_erro"])
    g = disc.assign(categoria=cat).groupby("categoria")
    tab = g.agg(n=("id", "size"), conf_media_llm=("confianca", "mean")).sort_values("n", ascending=False)
    tab["pct"] = tab["n"] / tab["n"].sum()
    # erros com alta confiança: "justificativa convincente não é acerto"
    tab["n_conf_alta"] = g.apply(lambda x: int((x["confianca"] >= 0.8).sum()), include_groups=False)
    return tab.reset_index()


def ajustar_por_matriz(sent_llm: pd.Series, cm: pd.DataFrame, labels=None) -> pd.Series:
    """LLM 'corrigido' pela matriz de confusão: mapeia cada predição LLM para o rótulo humano mais provável
    dado essa predição (argmax P(hum | llm)). Deve ser estimado numa amostra e aplicado fora dela — documente o split."""
    labels = labels or config.SENTIMENTOS
    arr = cm.values.astype(float)  # linhas=hum, colunas=llm
    mapa = {}
    for j, l in enumerate(labels):
        col = arr[:, j]
        mapa[l] = labels[int(col.argmax())] if col.sum() > 0 else l
    return sent_llm.map(mapa)
