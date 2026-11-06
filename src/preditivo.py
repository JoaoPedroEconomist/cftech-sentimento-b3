"""Etapa 03.6 — índice diário de sentimento e teste do poder preditivo.

Regras centrais (ver docs/plano_de_testes.md, definido antes de rodar):
  * posts após o fechamento (ou em dia sem pregão) contam para o PRÓXIMO pregão;
  * o retorno do próprio dia (ret_t) e do dia anterior entram como controle (causalidade invertida);
  * erros-padrão cluster por ticker (>=10 tickers) ou HAC-painel; correção de Holm na família principal.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests

from . import config

DVS_PRINCIPAIS = ["ret_f1", "ret_acum_f1_f5", "vol_anormal_f1"]
DV_PLACEBO = "ret_lag1"  # o índice de t não pode "prever" o retorno passado; se prever, é causalidade invertida


# ---------- alinhamento de horário ----------
def atribuir_pregao(data_hora: pd.Series, calendario: pd.DatetimeIndex, hora_corte: int = config.HORA_CORTE) -> pd.Series:
    """Mapeia cada timestamp (tz-aware, America/Sao_Paulo) ao pregão ao qual o post "pertence".

    - post em dia de pregão antes do corte  -> esse pregão;
    - post após o corte, fim de semana ou feriado -> próximo pregão disponível;
    - post depois do último pregão do calendário -> NaT (descartado).
    """
    dh = pd.to_datetime(data_hora)
    if dh.dt.tz is None:
        dh = dh.dt.tz_localize(config.TZ_LOCAL)
    else:
        dh = dh.dt.tz_convert(config.TZ_LOCAL)
    dia = dh.dt.tz_localize(None).dt.normalize()
    apos_corte = dh.dt.hour >= hora_corte
    dia_ref = dia + pd.to_timedelta(apos_corte.astype(int), unit="D")
    cal = pd.DatetimeIndex(calendario).sort_values()
    pos = cal.searchsorted(dia_ref.to_numpy(), side="left")  # primeiro pregão >= dia_ref
    validos = pos < len(cal)
    saida = pd.Series(pd.NaT, index=data_hora.index, dtype="datetime64[ns]")
    saida[validos] = cal[pos[validos]]
    return saida


# ---------- índice diário ----------
def indice_diario(
    posts_sent: pd.DataFrame,
    calendario: pd.DatetimeIndex,
    hora_corte: int = config.HORA_CORTE,
    n_min: int = config.N_MIN_POSTS,
    um_voto_por_autor: bool = False,
    excluir_ids: set[str] | None = None,
) -> pd.DataFrame:
    """posts_sent: uma linha por (post, ticker) com colunas id, autor_id, data_hora, ticker, sentimento.

    indice = (pos − neg) / total, por ticker e pregão. `um_voto_por_autor` limita cada autor a 1 voto por
    ticker-dia (robustez a contas hiperativas; Liu & Son, 2024). `excluir_ids` remove posts coordenados."""
    d = posts_sent.copy()
    if excluir_ids:
        d = d[~d["id"].astype(str).isin(excluir_ids)]
    d["pregao"] = atribuir_pregao(d["data_hora"], calendario, hora_corte)
    d = d.dropna(subset=["pregao", "sentimento"])
    d["v"] = d["sentimento"].map({"positivo": 1, "negativo": -1, "neutro": 0})
    if um_voto_por_autor:
        g = d.groupby(["ticker", "pregao", "autor_id"], as_index=False).agg(v=("v", "mean"))
        g["pos"] = (g["v"] > 0).astype(int)
        g["neg"] = (g["v"] < 0).astype(int)
        g["tot"] = 1
        agg = g.groupby(["ticker", "pregao"]).agg(n_pos=("pos", "sum"), n_neg=("neg", "sum"), n_posts=("tot", "sum"), n_autores=("autor_id", "nunique")).reset_index()
    else:
        d["pos"] = (d["v"] > 0).astype(int)
        d["neg"] = (d["v"] < 0).astype(int)
        agg = d.groupby(["ticker", "pregao"]).agg(n_pos=("pos", "sum"), n_neg=("neg", "sum"), n_posts=("id", "size"), n_autores=("autor_id", "nunique")).reset_index()
    agg = agg[agg["n_posts"] >= n_min].copy()
    agg["indice"] = (agg["n_pos"] - agg["n_neg"]) / agg["n_posts"]
    agg["log_volume_posts"] = np.log1p(agg["n_posts"])
    return agg.rename(columns={"pregao": "data"})


def montar_painel(indice: pd.DataFrame, mercado: pd.DataFrame) -> pd.DataFrame:
    """Une o índice (ticker, data=pregão t) ao painel de mercado do mesmo ticker-dia t."""
    return indice.merge(mercado, on=["ticker", "data"], how="inner").sort_values(["ticker", "data"]).reset_index(drop=True)


# ---------- regressões ----------
def _formula(dv: str, controles: list[str], efeitos_fixos: bool, painel: pd.DataFrame) -> str:
    rhs = ["indice", *controles]
    if efeitos_fixos:
        if painel["ticker"].nunique() > 1:
            rhs.append("C(ticker)")
        if painel["data"].nunique() > 1:
            rhs.append("C(data)")
    return f"{dv} ~ " + " + ".join(rhs)


def controles_para(dv: str) -> list[str]:
    """Controles do modelo 'com controles' (docs/plano_de_testes.md)."""
    if dv == "vol_anormal_f1":
        return ["vol_anormal_t", "log_volume_posts"]
    if dv == DV_PLACEBO:
        return ["log_volume_posts"]  # no placebo NÃO controlamos o retorno passado: é a própria variável testada
    return ["ret_t", "ret_lag1", "log_volume_posts"]


def ajustar(painel: pd.DataFrame, dv: str, controles: list[str], efeitos_fixos: bool = False):
    """OLS com erros-padrão robustos. Retorna o resultado do statsmodels ou None se a amostra é insuficiente."""
    cols = ["indice", dv, *controles, "ticker", "data"]
    d = painel[cols].replace([np.inf, -np.inf], np.nan).dropna()
    if len(d) < 30 or d["indice"].nunique() < 2:
        return None
    # controles constantes são colineares com o intercepto (covariância singular): descarta
    controles = [c for c in controles if d[c].nunique() > 1]
    d = d.sort_values(["ticker", "data"]).reset_index(drop=True)
    form = _formula(dv, controles, efeitos_fixos, d)
    n_t = d["ticker"].nunique()
    cod = pd.factorize(d["ticker"])[0]
    mod = smf.ols(form, data=d)
    if n_t >= 10:
        res = mod.fit(cov_type="cluster", cov_kwds={"groups": cod})
    elif n_t == 1:
        res = mod.fit(cov_type="HAC", cov_kwds={"maxlags": config.HAC_LAGS})
    else:
        res = mod.fit(cov_type="hac-panel", cov_kwds={"groups": cod, "maxlags": config.HAC_LAGS})
    res._n_tickers = n_t  # type: ignore[attr-defined]
    return res


def rodar_testes(
    paineis: dict[str, pd.DataFrame],
    dvs: list[str] | None = None,
    efeitos_fixos: bool = False,
    incluir_placebo: bool = True,
) -> pd.DataFrame:
    """Roda a especificação fixa do plano: versões × DVs × {base, controles}.
    Aplica Holm aos testes da família principal (modelo 'controles' em DVs principais)."""
    dvs = list(dvs or DVS_PRINCIPAIS)
    alvo = dvs + ([DV_PLACEBO] if incluir_placebo else [])
    linhas = []
    for versao, painel in paineis.items():
        for dv in alvo:
            for modelo in ("base", "controles"):
                ctrl = [] if modelo == "base" else controles_para(dv)
                res = ajustar(painel, dv, ctrl, efeitos_fixos)
                if res is None or "indice" not in res.params:
                    linhas.append({"versao": versao, "dv": dv, "modelo": modelo, "coef": np.nan, "ep": np.nan, "t": np.nan, "p": np.nan, "n": 0, "n_tickers": 0, "r2": np.nan})
                    continue
                linhas.append(
                    {
                        "versao": versao,
                        "dv": dv,
                        "modelo": modelo,
                        "coef": float(res.params["indice"]),
                        "ep": float(res.bse["indice"]),
                        "t": float(res.tvalues["indice"]),
                        "p": float(res.pvalues["indice"]),
                        "n": int(res.nobs),
                        "n_tickers": int(res._n_tickers),
                        "r2": float(res.rsquared),
                    }
                )
    tab = pd.DataFrame(linhas)
    tab["familia_principal"] = (tab["modelo"] == "controles") & tab["dv"].isin(dvs)
    tab["p_holm"] = np.nan
    fam = tab["familia_principal"] & tab["p"].notna()
    if fam.sum() > 0:
        tab.loc[fam, "p_holm"] = multipletests(tab.loc[fam, "p"].to_numpy(), alpha=config.ALFA, method="holm")[1]
    return tab


def conclusao(tab: pd.DataFrame, alfa: float = config.ALFA) -> dict:
    """Aplica o critério do plano: sinal só se significativo após Holm, com mesmo sinal nas versões e sem sumir com ret_t."""
    fam = tab[tab["familia_principal"]].dropna(subset=["p_holm"])
    out = {}
    for dv, g in fam.groupby("dv"):
        sig = (g["p_holm"] < alfa)
        mesmo_sinal = g["coef"].gt(0).all() or g["coef"].lt(0).all()
        out[dv] = {"todas_versoes_significativas": bool(sig.all() and len(g) > 0), "mesmo_sinal": bool(mesmo_sinal), "n_versoes": int(len(g))}
    out["ha_sinal"] = any(v["todas_versoes_significativas"] and v["mesmo_sinal"] for v in out.values())
    return out
