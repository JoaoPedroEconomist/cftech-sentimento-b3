"""Dados de mercado via yfinance: preços, retornos, volume anormal, liquidez e calendário de pregões."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import config


def baixar_precos(tickers: list[str], inicio, fim, cache_dir: Path | None = None, sufixo: str = ".SA") -> pd.DataFrame:
    """Baixa OHLCV de cada ticker B3 (ex.: PETR4 -> PETR4.SA). Cache em parquet por ticker.

    Retorna DataFrame longo: ticker, data (date), close, adj_close, volume."""
    import yfinance as yf  # import tardio: só quem baixa precisa

    cache_dir = cache_dir or (config.DATA_PROC / "precos")
    cache_dir.mkdir(parents=True, exist_ok=True)
    quadros = []
    for t in sorted(set(tickers)):
        arq = cache_dir / f"{t}.parquet"
        if arq.exists():
            q = pd.read_parquet(arq)
        else:
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


def baixar_calendario(inicio, fim, indice: str = "^BVSP") -> pd.DatetimeIndex:
    """Calendário de pregões a partir do Ibovespa."""
    import yfinance as yf

    h = yf.Ticker(indice).history(start=str(inicio), end=str(fim), auto_adjust=False).reset_index()
    return pd.DatetimeIndex(pd.to_datetime(h["Date"]).dt.tz_localize(None).dt.normalize()).sort_values().unique()


def calendario_de_precos(precos: pd.DataFrame, min_tickers: int = 1) -> pd.DatetimeIndex:
    """Fallback: dias em que ao menos `min_tickers` ativos negociaram."""
    c = precos.groupby("data")["ticker"].nunique()
    return pd.DatetimeIndex(c[c >= min_tickers].index).sort_values()


def construir_painel_mercado(precos: pd.DataFrame, janela_vol: int = config.JANELA_VOL_ANORMAL) -> pd.DataFrame:
    """Calcula, por ticker-dia (pregão t):
    ret_t, ret_lag1 (t-1), ret_f1 (t+1), ret_acum_f1_f5 (soma de t+1..t+5, em log), vol_anormal_t e vol_anormal_f1.
    vol_anormal = log(volume) − log(média dos `janela_vol` pregões ANTERIORES) → sem olhar o futuro."""
    saida = []
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
        saida.append(g[["ticker", "data", "ret_t", "ret_lag1", "ret_f1", "ret_acum_f1_f5", "vol_anormal_t", "vol_anormal_f1"]])
    return pd.concat(saida, ignore_index=True) if saida else pd.DataFrame()


def liquidez_por_ticker(precos: pd.DataFrame) -> pd.Series:
    """Volume financeiro mediano (close × volume) por ticker — usado como proxy de liquidez."""
    p = precos.assign(fin=precos["close"] * precos["volume"])
    return p.groupby("ticker")["fin"].median()
