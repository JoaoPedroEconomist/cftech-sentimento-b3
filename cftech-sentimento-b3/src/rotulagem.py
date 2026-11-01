"""Etapa 03.2 — rotulagem humana independente, kappa entre humanos e consenso."""
from __future__ import annotations

import pandas as pd
from sklearn.metrics import cohen_kappa_score

from . import config

COLUNAS_ROTULO = ["id", "sentimento", *config.FLAGS, "observacao"]


def criar_template_rotulos(amostra: pd.DataFrame, posts: pd.DataFrame, saida) -> pd.DataFrame:
    """Cria CSV vazio para um anotador. Mostra só id e texto (nunca LLM nem rótulo do parceiro)."""
    m = amostra[["id"]].merge(posts[["id", "texto"]], on="id", how="left")
    tpl = m.copy()
    tpl["sentimento"] = ""
    for f in config.FLAGS:
        tpl[f] = ""
    tpl["observacao"] = ""
    tpl.to_csv(saida, index=False)
    return tpl


def validar_rotulos(df: pd.DataFrame) -> list[str]:
    """Retorna lista de problemas (vazio = ok)."""
    erros = []
    if df["id"].duplicated().any():
        erros.append("ids duplicados")
    ruins = ~df["sentimento"].isin(config.SENTIMENTOS)
    if ruins.any():
        erros.append(f"{int(ruins.sum())} sentimentos inválidos/vazios")
    for f in config.FLAGS:
        if f in df.columns and not df[f].isin([0, 1]).all():
            erros.append(f"flag {f} deve ser 0/1")
    return erros


def kappa(a: pd.Series, b: pd.Series, labels=None, weights=None) -> float:
    labels = labels or config.SENTIMENTOS
    return float(cohen_kappa_score(a, b, labels=labels, weights=weights))


def kappa_entre_humanos(ra: pd.DataFrame, rb: pd.DataFrame) -> dict:
    m = ra.merge(rb, on="id", suffixes=("_A", "_B"))
    out = {"n": len(m), "kappa_sentimento": kappa(m["sentimento_A"], m["sentimento_B"])}
    out["kappa_sentimento_ponderado"] = kappa(m["sentimento_A"], m["sentimento_B"], weights="linear")
    for f in config.FLAGS:
        a, b = m[f"{f}_A"], m[f"{f}_B"]
        out[f"kappa_{f}"] = float(cohen_kappa_score(a, b, labels=[0, 1])) if a.nunique() > 1 or b.nunique() > 1 else float("nan")
        out[f"concordancia_bruta_{f}"] = float((a == b).mean())
    return out


def divergencias(ra: pd.DataFrame, rb: pd.DataFrame) -> pd.DataFrame:
    """Lista os ids em que A e B discordam no sentimento ou em qualquer flag (para a discussão)."""
    m = ra.merge(rb, on="id", suffixes=("_A", "_B"))
    cond = m["sentimento_A"] != m["sentimento_B"]
    for f in config.FLAGS:
        cond |= m[f"{f}_A"] != m[f"{f}_B"]
    return m[cond].reset_index(drop=True)


def consolidar_consenso(ra: pd.DataFrame, rb: pd.DataFrame, decisoes: pd.DataFrame | None = None) -> pd.DataFrame:
    """Gabarito consolidado.
    Onde A e B concordam: mantém. Onde divergem: usa `decisoes` (id, sentimento, flags) acordadas na discussão.
    Divergências sem decisão geram erro — a dupla tem de resolver todas (a ordem existe para não ancorar no LLM)."""
    m = ra.merge(rb, on="id", suffixes=("_A", "_B"))
    linhas = []
    pend = []
    dec = decisoes.set_index("id") if decisoes is not None else pd.DataFrame()
    for _, r in m.iterrows():
        linha = {"id": r["id"]}
        divergiu = r["sentimento_A"] != r["sentimento_B"] or any(r[f"{f}_A"] != r[f"{f}_B"] for f in config.FLAGS)
        if not divergiu:
            linha["sentimento"] = r["sentimento_A"]
            for f in config.FLAGS:
                linha[f] = r[f"{f}_A"]
            linha["origem"] = "concordancia"
        elif r["id"] in dec.index:
            d = dec.loc[r["id"]]
            linha["sentimento"] = d["sentimento"]
            for f in config.FLAGS:
                linha[f] = d[f] if f in d.index else r[f"{f}_A"]
            linha["origem"] = "discussao"
        else:
            pend.append(r["id"])
            continue
        linhas.append(linha)
    if pend:
        raise ValueError(f"{len(pend)} divergências sem decisão (ex.: {pend[:5]}). Resolva em decisoes_consenso.csv")
    return pd.DataFrame(linhas)


def ler_rotulos(caminho) -> pd.DataFrame:
    df = pd.read_csv(caminho)
    for f in config.FLAGS:
        if f in df.columns:
            df[f] = df[f].fillna(0).astype(int)
    return df
