"""Etapa 03.5 — detecção de posts coordenados.

O código APONTA suspeitos; a DECISÃO é humana (revisão dos 30 clusters mais suspeitos).

Sinais combinados em um escore de suspeita por cluster:
  similaridade (TF-IDF + cosseno), rajada de autores distintos, autores com pouco histórico,
  baixa liquidez do ticker, linguagem de urgência / alvo de preço.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components
from sklearn.feature_extraction.text import TfidfVectorizer

from . import config
from .limpeza import explodir_tickers, sem_acento

DECISOES = ["coordenado", "provavelmente_coordenado", "organico"]


# ---------- sinais por post ----------
def urgencia_alvo(texto: str) -> bool:
    return bool(re.search(config.URGENCIA_REGEX, sem_acento(str(texto)).lower()))


def historico_autores(posts: pd.DataFrame) -> dict[str, pd.DatetimeIndex]:
    """Mapeia cada autor para os timestamps ordenados dos seus posts (para contagem sem olhar o futuro)."""
    p = posts.sort_values("data_hora")
    return {str(a): pd.DatetimeIndex(g["data_hora"]) for a, g in p.groupby("autor_id")}


def contar_posts_anteriores(autor: str, t_ref: pd.Timestamp, historico: dict[str, pd.DatetimeIndex] | pd.Series) -> int:
    """Conta estritamente os posts do autor publicados antes de t_ref (sem lookahead bias)."""
    if isinstance(historico, dict):
        idx = historico.get(str(autor))
        if idx is None or len(idx) == 0:
            return 0
        t_alvo = pd.to_datetime(t_ref)
        if idx.tz is not None and t_alvo.tz is None:
            t_alvo = t_alvo.tz_localize(idx.tz)
        elif idx.tz is None and t_alvo.tz is not None:
            t_alvo = t_alvo.tz_localize(None)
        return int(idx.searchsorted(t_alvo, side="left"))
    return int(historico.get(autor, 0))


def taxa_normal_ticker(ex: pd.DataFrame) -> dict[str, float]:
    """Calcula a taxa média normal de posts por hora de cada ticker na base."""
    taxas = {}
    for t, g in ex.groupby("ticker"):
        span_h = max(0.5, (g["data_hora"].max() - g["data_hora"].min()).total_seconds() / 3600)
        taxas[t] = len(g) / span_h
    return taxas


# ---------- clusters ----------
def _componentes_por_similaridade(X, limiar: float) -> np.ndarray:
    S = (X @ X.T).tocsr()
    S.data = np.where(S.data >= limiar, 1, 0)
    S.eliminate_zeros()
    n, lab = connected_components(csr_matrix(S), directed=False)
    return lab


def clusters_similaridade(ex: pd.DataFrame, X, limiar: float = config.LIMIAR_COSSENO) -> pd.DataFrame:
    """Agrupa, dentro de (ticker, dia), posts com cosseno >= limiar. Exige >= 2 autores distintos."""
    linhas = []
    ex = ex.reset_index(drop=True)
    ex["_dia"] = ex["data_hora"].dt.date
    for (ticker, _dia), g in ex.groupby(["ticker", "_dia"]):
        if len(g) < 2:
            continue
        idx = g.index.to_numpy()
        lab = _componentes_por_similaridade(X[idx], limiar)
        for c in np.unique(lab):
            memb = idx[lab == c]
            if len(memb) >= 2 and ex.loc[memb, "autor_id"].nunique() >= 2:
                linhas.append({"tipo": "similaridade", "ticker": ticker, "membros": memb.tolist()})
    return pd.DataFrame(linhas)


def clusters_rajada(
    ex: pd.DataFrame,
    janela_min: int = config.JANELA_RAJADA_MIN,
    min_autores: int = config.MIN_AUTORES_RAJADA,
) -> pd.DataFrame:
    """Sessões de posts do mesmo ticker separadas por lacunas > janela_min, com >= min_autores autores distintos."""
    linhas = []
    ex = ex.reset_index(drop=True)
    for ticker, g in ex.groupby("ticker"):
        g = g.sort_values("data_hora")
        gap = g["data_hora"].diff().dt.total_seconds().div(60)
        sessao = (gap > janela_min).cumsum()
        for _, s in g.groupby(sessao):
            if s["autor_id"].nunique() >= min_autores:
                linhas.append({"tipo": "rajada", "ticker": ticker, "membros": s.index.tolist()})
    return pd.DataFrame(linhas)


def _liquidez_percentil(liquidez: pd.Series | None) -> pd.Series | None:
    """liquidez: Series ticker -> volume financeiro médio. Retorna percentil [0,1] (1 = mais líquido)."""
    if liquidez is None or liquidez.empty:
        return None
    return liquidez.rank(pct=True)


def pontuar_clusters(
    clusters: pd.DataFrame,
    ex: pd.DataFrame,
    X,
    historico: dict[str, np.ndarray] | pd.Series,
    liquidez: pd.Series | None = None,
    pesos: dict | None = None,
    taxas_tickers: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Calcula as componentes e o escore (média ponderada; pesos renormalizados se faltar liquidez)."""
    pesos = dict(pesos or config.PESOS_SUSPEITA)
    liq_pct = _liquidez_percentil(liquidez)
    if liq_pct is None:
        pesos.pop("baixa_liquidez", None)
    soma = sum(pesos.values())
    pesos = {k: v / soma for k, v in pesos.items()}

    ex = ex.reset_index(drop=True)
    linhas = []
    for _, c in clusters.iterrows():
        memb = c["membros"]
        sub = ex.loc[memb]
        n_aut = sub["autor_id"].nunique()
        t_ini, t_fim = sub["data_hora"].min(), sub["data_hora"].max()
        span_min = max((t_fim - t_ini).total_seconds() / 60, 0.0)

        # similaridade média ao centroide (cosseno)
        Xm = X[memb]
        cen = np.asarray(Xm.mean(axis=0)).ravel()
        norm = np.linalg.norm(cen)
        sim = float((Xm @ cen / norm).mean()) if norm > 0 else 0.0

        # rajada: muitos autores em pouco tempo, comparada com o movimento normal do ticker
        raj_autores = min(1.0, n_aut / (2 * config.MIN_AUTORES_RAJADA))
        if span_min > config.JANELA_RAJADA_MIN:
            raj_autores *= config.JANELA_RAJADA_MIN / span_min

        if taxas_tickers and c["ticker"] in taxas_tickers:
            taxa_base = max(taxas_tickers[c["ticker"]], 0.05)
            span_h = max(span_min / 60.0, 5.0 / 60.0)  # mínimo de 5 minutos
            taxa_cluster = len(sub) / span_h
            ratio_anomalia = taxa_cluster / taxa_base
            raj_anomalia = min(1.0, ratio_anomalia / 4.0)
            raj = 0.5 * raj_autores + 0.5 * raj_anomalia
        else:
            raj = raj_autores

        # autores com pouco histórico (conta estritamente os posts ANTERIORES ao cluster)
        autores = sub["autor_id"].unique()
        novo = float(np.mean([contar_posts_anteriores(a, t_ini, historico) < config.MIN_POSTS_AUTOR_HISTORICO for a in autores]))

        # baixa liquidez
        baixa = float(1 - liq_pct.get(c["ticker"], 0.5)) if liq_pct is not None else np.nan

        # urgência / alvo
        urg = float(sub["texto"].map(urgencia_alvo).mean())

        comp = {"similaridade": sim, "rajada": raj, "autor_novo": novo, "baixa_liquidez": baixa, "urgencia_alvo": urg}
        escore = sum(pesos[k] * comp[k] for k in pesos)
        linhas.append(
            {
                "tipo": c["tipo"],
                "ticker": c["ticker"],
                "n_posts": len(sub),
                "n_autores": n_aut,
                "t_ini": t_ini,
                "t_fim": t_fim,
                "span_min": span_min,
                **{f"s_{k}": v for k, v in comp.items()},
                "escore": float(escore),
                "ids": sub["id"].astype(str).tolist(),
            }
        )
    out = pd.DataFrame(linhas)
    if out.empty:
        return out
    out = out.sort_values("escore", ascending=False).reset_index(drop=True)
    out.insert(0, "cluster_id", [f"C{i + 1:04d}" for i in range(len(out))])
    return out


def _deduplicar_clusters(cl: pd.DataFrame) -> pd.DataFrame:
    """Clusters com exatamente os mesmos membros (ex.: similaridade e rajada) viram um só, com tipo combinado.
    Evita gastar vagas da revisão humana com o mesmo grupo de posts duas vezes."""
    if cl.empty:
        return cl
    cl = cl.assign(_k=cl["membros"].map(lambda m: tuple(sorted(m))))
    agg = cl.groupby("_k", sort=False).agg(tipo=("tipo", lambda s: "+".join(sorted(set(s)))), ticker=("ticker", "first"), membros=("membros", "first")).reset_index(drop=True)
    return agg


def detectar(posts: pd.DataFrame, liquidez: pd.Series | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pipeline completo. Retorna (clusters pontuados, mapa post->cluster)."""
    ex = explodir_tickers(posts).reset_index(drop=True)
    if ex.empty:
        return pd.DataFrame(), pd.DataFrame(columns=["id", "cluster_id"])
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1, sublinear_tf=True)
    X = vec.fit_transform(ex["texto_norm"]).tocsr()
    cl = pd.concat([clusters_similaridade(ex, X), clusters_rajada(ex)], ignore_index=True)
    cl = _deduplicar_clusters(cl)
    if cl.empty:
        return pd.DataFrame(), pd.DataFrame(columns=["id", "cluster_id"])
    hist = historico_autores(posts)
    taxas = taxa_normal_ticker(ex)
    pont = pontuar_clusters(cl, ex, X, hist, liquidez, taxas_tickers=taxas)
    mapa = pont[["cluster_id", "ids"]].explode("ids").rename(columns={"ids": "id"})[["id", "cluster_id"]]
    return pont, mapa


# ---------- revisão humana ----------
def amostra_para_revisao(clusters: pd.DataFrame, posts: pd.DataFrame, n: int = config.N_CLUSTERS_REVISAO, max_posts: int = 5) -> pd.DataFrame:
    """Top-n clusters por escore, com colunas vazias para a decisão humana (NÃO preencher por código)."""
    top = clusters.head(n).copy()
    txt = posts.set_index(posts["id"].astype(str))["texto"]
    top["exemplos_texto"] = top["ids"].map(lambda ids: " || ".join(txt.reindex(ids[:max_posts]).fillna("").str.slice(0, 160)))
    top["decisao_humana"] = ""  # coordenado | provavelmente_coordenado | organico
    top["justificativa"] = ""
    top["ids"] = top["ids"].map(lambda x: ";".join(x))
    return top


def validar_revisao(rev: pd.DataFrame) -> list[str]:
    erros = []
    if rev["decisao_humana"].isna().any() or (rev["decisao_humana"].astype(str).str.len() == 0).any():
        erros.append("há clusters sem decisão")
    ruins = ~rev["decisao_humana"].isin(DECISOES)
    if ruins.any():
        erros.append(f"{int(ruins.sum())} decisões fora de {DECISOES}")
    if (rev["justificativa"].fillna("").str.len() < 10).any():
        erros.append("justificativa ausente/curta em algum cluster")
    return erros


def posts_coordenados(rev: pd.DataFrame, incluir_provaveis: bool = True) -> set[str]:
    """Conjunto de ids de posts em clusters revisados como coordenados (e prováveis, opcionalmente)."""
    alvo = {"coordenado"} | ({"provavelmente_coordenado"} if incluir_provaveis else set())
    sel = rev[rev["decisao_humana"].isin(alvo)]
    ids: set[str] = set()
    for s in sel["ids"]:
        ids.update(str(s).split(";"))
    return ids


def precisao_no_topo(rev: pd.DataFrame) -> dict:
    """Quanto do top-n do detector foi confirmado por humanos (sinal de qualidade do escore)."""
    n = len(rev)
    conf = int((rev["decisao_humana"] == "coordenado").sum())
    prov = int((rev["decisao_humana"] == "provavelmente_coordenado").sum())
    return {"n": n, "coordenado": conf, "provavelmente": prov, "organico": n - conf - prov, "precisao_estrita": conf / n if n else float("nan"), "precisao_lata": (conf + prov) / n if n else float("nan")}
