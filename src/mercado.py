"""Dados de mercado via yfinance: preços, retornos, volume anormal, liquidez e calendário de pregões."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import config


def obter_hora_corte_b3(dt: pd.Timestamp | datetime.date) -> int:
    """Retorna o horário de fechamento do mercado regular da B3 (17h ou 18h BRT).
    
    A B3 estende o fechamento para 18:00 BRT durante o horário de verão nos EUA (DST)
    para manter sincronia com o fechamento das bolsas de NY (17h NY).
    - DST nos EUA: do 2º domingo de março ao 1º domingo de novembro -> 18h BRT
    - Restante do ano -> 17h BRT
    """
    ts = pd.to_datetime(dt)
    ano = ts.year
    mar_1 = pd.Timestamp(year=ano, month=3, day=1)
    segundo_domingo_mar = mar_1 + pd.Timedelta(days=(6 - mar_1.weekday()) % 7 + 7)

    nov_1 = pd.Timestamp(year=ano, month=11, day=1)
    primeiro_domingo_nov = nov_1 + pd.Timedelta(days=(6 - nov_1.weekday()) % 7)

    data_simples = ts.tz_localize(None) if ts.tzinfo is not None else ts
    if segundo_domingo_mar <= data_simples < primeiro_domingo_nov:
        return 18
    return 17


def baixar_precos(tickers: list[str], inicio, fim, cache_dir: Path | None = None, sufixo: str = ".SA") -> pd.DataFrame:
    """Baixa OHLCV de cada ticker B3 (ex.: PETR4 -> PETR4.SA).
    
    Valida se o cache cobre estritamente o período [inicio, fim]; se o período for diferente/incompleto,
    faz novo download para garantir que a janela histórica de 40 dias anteriores esteja presente.
    """
    import yfinance as yf  # import tardio: só quem baixa precisa

    cache_dir = cache_dir or (config.DATA_PROC / "precos")
    cache_dir.mkdir(parents=True, exist_ok=True)
    quadros = []
    req_ini = pd.to_datetime(inicio)
    req_fim = pd.to_datetime(fim)

    for t in sorted(set(tickers)):
        arq = cache_dir / f"{t}.parquet"
        reaproveitar = False
        if arq.exists():
            try:
                q = pd.read_parquet(arq)
                if not q.empty and "data" in q.columns:
                    c_ini = pd.to_datetime(q["data"]).min()
                    c_fim = pd.to_datetime(q["data"]).max()
                    # Cache é aceito se cobre todo o intervalo solicitado (tolerância de fim de semana/feriado)
                    if c_ini <= req_ini + pd.Timedelta(days=5) and c_fim >= req_fim - pd.Timedelta(days=5):
                        reaproveitar = True
                        quadros.append(q)
            except Exception:
                reaproveitar = False

        if not reaproveitar:
            h = yf.Ticker(f"{t}{sufixo}").history(start=str(inicio), end=str(fim), auto_adjust=False)
            if h.empty:
                continue
            h = h.reset_index()
            h["data"] = pd.to_datetime(h["Date"]).dt.tz_localize(None).dt.normalize()
            q = pd.DataFrame(
                {
                    "ticker": t,
                    "data": h["data"],
                    "close": h["Close"],
                    "adj_close": h["Adj Close"] if "Adj Close" in h else h["Close"],
                    "volume": h["Volume"],
                }
            )
            q.to_parquet(arq, index=False)
            quadros.append(q)

    return pd.concat(quadros, ignore_index=True) if quadros else pd.DataFrame(columns=["ticker", "data", "close", "adj_close", "volume"])


def baixar_ibov(inicio, fim, cache_dir: Path | None = None) -> pd.DataFrame:
    """Baixa preços do índice Ibovespa (^BVSP) para cálculo de retorno em excesso/anormal."""
    import yfinance as yf

    cache_dir = cache_dir or (config.DATA_PROC / "precos")
    cache_dir.mkdir(parents=True, exist_ok=True)
    arq = cache_dir / "IBOV.parquet"
    req_ini = pd.to_datetime(inicio)
    req_fim = pd.to_datetime(fim)

    if arq.exists():
        try:
            q = pd.read_parquet(arq)
            if not q.empty and "data" in q.columns:
                if q["data"].min() <= req_ini + pd.Timedelta(days=5) and q["data"].max() >= req_fim - pd.Timedelta(days=5):
                    return q
        except Exception:
            pass

    h = yf.Ticker("^BVSP").history(start=str(inicio), end=str(fim), auto_adjust=False)
    if h.empty:
        return pd.DataFrame(columns=["data", "close", "adj_close", "volume"])
    h = h.reset_index()
    h["data"] = pd.to_datetime(h["Date"]).dt.tz_localize(None).dt.normalize()
    q = pd.DataFrame(
        {
            "data": h["data"],
            "close": h["Close"],
            "adj_close": h["Adj Close"] if "Adj Close" in h else h["Close"],
            "volume": h["Volume"],
        }
    )
    q.to_parquet(arq, index=False)
    return q


def baixar_calendario(inicio, fim, indice: str = "^BVSP") -> pd.DatetimeIndex:
    """Calendário de pregões a partir do Ibovespa."""
    import yfinance as yf

    h = yf.Ticker(indice).history(start=str(inicio), end=str(fim), auto_adjust=False).reset_index()
    return pd.DatetimeIndex(pd.to_datetime(h["Date"]).dt.tz_localize(None).dt.normalize()).sort_values().unique()


def calendario_de_precos(precos: pd.DataFrame, min_tickers: int = 1) -> pd.DatetimeIndex:
    """Fallback: dias em que ao menos `min_tickers` ativos negociaram."""
    c = precos.groupby("data")["ticker"].nunique()
    return pd.DatetimeIndex(c[c >= min_tickers].index).sort_values()


def construir_painel_mercado(
    precos: pd.DataFrame,
    ibov: pd.DataFrame | None = None,
    janela_vol: int = config.JANELA_VOL_ANORMAL,
) -> pd.DataFrame:
    """Calcula, por ticker-dia (pregão t):
    ret_t, ret_lag1 (t-1), ret_f1 (t+1), ret_acum_f1_f5 (soma de t+1..t+5, em log), vol_anormal_t e vol_anormal_f1.
    Calcula também os retornos em excesso ao Ibovespa (ret_excesso_*) quando ibov estiver disponível.
    vol_anormal = log(volume) − log(média dos `janela_vol` pregões ANTERIORES) → sem olhar o futuro."""
    saida = []

    # Mapa de retornos do Ibovespa para cálculo de retorno anormal
    mapa_ibov = {}
    if ibov is not None and not ibov.empty:
        ib = ibov.sort_values("data").copy()
        ib = ib[ib["adj_close"] > 0]
        lp_ib = np.log(ib["adj_close"])
        ib["ret_ibov_t"] = lp_ib.diff()
        ib["ret_ibov_lag1"] = ib["ret_ibov_t"].shift(1)
        ib["ret_ibov_f1"] = ib["ret_ibov_t"].shift(-1)
        ib["ret_ibov_acum_f1_f5"] = lp_ib.shift(-5) - lp_ib
        mapa_ibov = ib.set_index("data")[["ret_ibov_t", "ret_ibov_lag1", "ret_ibov_f1", "ret_ibov_acum_f1_f5"]].to_dict("index")

    for t, g in precos.sort_values(["ticker", "data"]).groupby("ticker"):
        g = g.copy()
        g = g[(g["adj_close"] > 0)]
        lp = np.log(g["adj_close"])
        g["ret_t"] = lp.diff()
        g["ret_lag1"] = g["ret_t"].shift(1)
        g["ret_f1"] = g["ret_t"].shift(-1)
        g["ret_acum_f1_f5"] = lp.shift(-5) - lp
        vol = g["volume"].where(g["volume"] > 0)
        media_passada = vol.shift(1).rolling(janela_vol, min_periods=max(5, janela_vol // 2)).mean()
        g["vol_anormal_t"] = np.log(vol) - np.log(media_passada)
        g["vol_anormal_f1"] = g["vol_anormal_t"].shift(-1)

        # Retornos em excesso / anormais (descontando o Ibovespa)
        if mapa_ibov:
            g["ret_ibov_t"] = g["data"].map(lambda d: mapa_ibov.get(d, {}).get("ret_ibov_t", np.nan))
            g["ret_ibov_lag1"] = g["data"].map(lambda d: mapa_ibov.get(d, {}).get("ret_ibov_lag1", np.nan))
            g["ret_ibov_f1"] = g["data"].map(lambda d: mapa_ibov.get(d, {}).get("ret_ibov_f1", np.nan))
            g["ret_ibov_acum_f1_f5"] = g["data"].map(lambda d: mapa_ibov.get(d, {}).get("ret_ibov_acum_f1_f5", np.nan))

            g["ret_excesso_t"] = g["ret_t"] - g["ret_ibov_t"]
            g["ret_excesso_lag1"] = g["ret_lag1"] - g["ret_ibov_lag1"]
            g["ret_excesso_f1"] = g["ret_f1"] - g["ret_ibov_f1"]
            g["ret_excesso_acum_f1_f5"] = g["ret_acum_f1_f5"] - g["ret_ibov_acum_f1_f5"]
        else:
            g["ret_excesso_t"] = g["ret_t"]
            g["ret_excesso_lag1"] = g["ret_lag1"]
            g["ret_excesso_f1"] = g["ret_f1"]
            g["ret_excesso_acum_f1_f5"] = g["ret_acum_f1_f5"]

        cols = [
            "ticker",
            "data",
            "ret_t",
            "ret_lag1",
            "ret_f1",
            "ret_acum_f1_f5",
            "vol_anormal_t",
            "vol_anormal_f1",
            "ret_excesso_t",
            "ret_excesso_lag1",
            "ret_excesso_f1",
            "ret_excesso_acum_f1_f5",
        ]
        saida.append(g[cols])
    return pd.concat(saida, ignore_index=True) if saida else pd.DataFrame()


def liquidez_por_ticker(precos: pd.DataFrame) -> pd.Series:
    """Volume financeiro mediano (close × volume) por ticker — usado como proxy de liquidez."""
    p = precos.assign(fin=precos["close"] * precos["volume"])
    return p.groupby("ticker")["fin"].median()
