"""Etapa 03.1 — limpeza da base de posts e extração de tickers."""
from __future__ import annotations

import re
import unicodedata

import pandas as pd

from . import config


def sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def carregar_posts(caminho=None) -> pd.DataFrame:
    """Lê o snapshot (parquet ou csv) de data/raw e valida o schema mínimo."""
    if caminho is None:
        for nome in config.POSTS_RAW_CANDIDATOS:
            p = config.DATA_RAW / nome
            if p.exists():
                caminho = p
                break
        else:
            raise FileNotFoundError("Coloque o snapshot em data/raw/posts.parquet ou posts.csv")
    caminho = str(caminho)
    df = pd.read_parquet(caminho) if caminho.endswith(".parquet") else pd.read_csv(caminho)
    faltam = [c for c in config.COLUNAS_OBRIGATORIAS if c not in df.columns]
    if faltam:
        raise ValueError(f"Colunas ausentes no snapshot: {faltam}")
    return df


def padronizar_fuso(serie: pd.Series, tz_origem: str = "UTC") -> pd.Series:
    """Converte para America/Sao_Paulo. Se o timestamp não tiver fuso, assume `tz_origem`."""
    s = pd.to_datetime(serie, errors="coerce")
    if s.dt.tz is None:
        s = s.dt.tz_localize(tz_origem)
    return s.dt.tz_convert(config.TZ_LOCAL)


def normalizar_texto(t: str) -> str:
    """Normalização leve p/ detecção de duplicatas (não altera o texto original usado pelo LLM)."""
    t = sem_acento(str(t)).lower()
    t = re.sub(r"https?://\S+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def extrair_tickers_regex(texto: str) -> list[str]:
    achados = re.findall(config.REGEX_TICKER, str(texto))
    return sorted({t for t in achados if t not in config.STOPLIST_TICKERS})


def extrair_tickers_nome(texto: str) -> list[str]:
    """Menções por nome da empresa. Nomes ambíguos (ex.: 'vale') exigem contexto financeiro."""
    t = sem_acento(str(texto)).lower()
    palavras = set(re.findall(r"\w+", t))
    tem_contexto = bool(palavras & config.PALAVRAS_CONTEXTO_FINANCEIRO)
    achados = set()
    for nome, ticker in config.NOMES_EMPRESAS.items():
        if re.search(rf"\b{re.escape(nome)}\b", t):
            if nome in config.NOMES_AMBIGUOS and not tem_contexto:
                continue
            achados.add(ticker)
    return sorted(achados)


def extrair_tickers(texto: str) -> list[str]:
    return sorted(set(extrair_tickers_regex(texto)) | set(extrair_tickers_nome(texto)))


def limpar_posts(df: pd.DataFrame, tz_origem: str = "UTC") -> pd.DataFrame:
    """Pipeline de limpeza: fuso, nulos, duplicatas exatas, tickers, tamanho do texto."""
    out = df.copy()
    n0 = len(out)
    out["data_hora"] = padronizar_fuso(out["data_hora"], tz_origem)
    out = out.dropna(subset=["id", "data_hora", "texto"])
    out["texto"] = out["texto"].astype(str).str.strip()
    out = out[out["texto"].str.len() > 0]
    out = out.drop_duplicates(subset="id")
    # duplicata exata = mesmo autor + mesmo texto + mesmo instante
    out = out.drop_duplicates(subset=["autor_id", "texto", "data_hora"])
    out["texto_norm"] = out["texto"].map(normalizar_texto)
    out["tickers"] = out["texto"].map(extrair_tickers)
    out["n_tickers"] = out["tickers"].str.len()
    out["tamanho_texto"] = out["texto"].str.len()
    out = out.sort_values("data_hora").reset_index(drop=True)
    out.attrs["n_removidos"] = n0 - len(out)
    return out


def explodir_tickers(df: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por (post, ticker). Posts sem ticker são descartados."""
    ex = df.explode("tickers").rename(columns={"tickers": "ticker"})
    return ex.dropna(subset=["ticker"]).reset_index(drop=True)


def resumo_exploracao(df: pd.DataFrame) -> dict[str, pd.DataFrame | pd.Series]:
    """Tabelas para o notebook 01 (posts/dia, posts/ticker, autores ativos, tamanho dos textos)."""
    ex = explodir_tickers(df)
    return {
        "posts_por_dia": df.groupby(df["data_hora"].dt.date).size().rename("posts"),
        "posts_por_ticker": ex.groupby("ticker").size().sort_values(ascending=False).rename("posts"),
        "autores_mais_ativos": df["autor_id"].value_counts().head(20),
        "tamanho_texto": df["tamanho_texto"].describe(),
        "sem_ticker": pd.Series({"posts_sem_ticker": int((df["n_tickers"] == 0).sum()), "total": len(df)}),
    }


def main() -> None:
    config.DATA_PROC.mkdir(parents=True, exist_ok=True)
    bruto = carregar_posts()
    limpo = limpar_posts(bruto)
    limpo.to_parquet(config.POSTS_PARQUET, index=False)
    print(f"{len(bruto)} -> {len(limpo)} posts ({limpo.attrs['n_removidos']} removidos). Salvo em {config.POSTS_PARQUET}")


if __name__ == "__main__":
    main()
