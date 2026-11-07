"""Etapa 03.1 — limpeza da base de posts e extração de tickers."""
from __future__ import annotations

import logging
import re
import unicodedata

import pandas as pd

from . import config

logger = logging.getLogger("limpeza")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def carregar_posts(caminho=None) -> pd.DataFrame:
    """Lê o snapshot (parquet ou csv) de data/raw ou data/ e padroniza colunas do schema."""
    if caminho is None:
        candidatos = [
            config.DATA_RAW / "posts.parquet",
            config.DATA_RAW / "posts.csv",
            config.RAIZ / "data" / "posts.parquet",
            config.RAIZ / "data" / "posts.csv",
        ]
        for p in candidatos:
            if p.exists():
                caminho = p
                break
        else:
            raise FileNotFoundError("Coloque o snapshot em data/raw/posts.parquet ou posts.csv")
    caminho = str(caminho)
    df = pd.read_parquet(caminho) if caminho.endswith(".parquet") else pd.read_csv(caminho)

    # Adapta nomes de colunas alternativos presentes no dataset real
    if "texto" not in df.columns and "comentario_resumo" in df.columns:
        df["texto"] = df["comentario_resumo"]
    if "data_hora" not in df.columns and "data" in df.columns:
        datas_extraidas = df["data"].astype(str).str.extract(r"(\d{4}-\d{2}-\d{2})")[0]
        base_datas = pd.to_datetime(datas_extraidas, errors="coerce").fillna(pd.Timestamp("2026-11-01"))
        df["data_hora"] = base_datas + pd.Timedelta(hours=14)  # 14h BRT (durante o pregão)
    if "plataforma" not in df.columns and "fonte" in df.columns:
        df["plataforma"] = df["fonte"]
    if "autor_id" not in df.columns:
        df["autor_id"] = "autor_" + df["id"].astype(str)

    faltam = [c for c in config.COLUNAS_OBRIGATORIAS if c not in df.columns]
    if faltam:
        raise ValueError(f"Colunas ausentes no snapshot: {faltam}")
    return df


def padronizar_fuso(serie: pd.Series, tz_origem: str = "UTC") -> pd.Series:
    """Converte para America/Sao_Paulo. Se o timestamp não tiver fuso, assume `tz_origem` e registra no log."""
    s = pd.to_datetime(serie, errors="coerce")
    tz_detectado = getattr(s.dt, "tz", None)
    if tz_detectado is None:
        logger.info(f"Fuso horário não especificado na base de origem. Assumindo '{tz_origem}' e convertendo para '{config.TZ_LOCAL}'.")
        s = s.dt.tz_localize(tz_origem)
    else:
        logger.info(f"Fuso horário detectado na base: '{tz_detectado}'. Convertendo para '{config.TZ_LOCAL}'.")
    return s.dt.tz_convert(config.TZ_LOCAL)


def normalizar_texto(t: str) -> str:
    """Normalização leve p/ detecção de duplicatas (não altera o texto original usado pelo LLM)."""
    t = sem_acento(str(t)).lower()
    t = re.sub(r"https?://\S+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def normalizar_ticker(t: str) -> str:
    """Normaliza ticker para maiúsculas e converte fracionário (ex: petr4 -> PETR4, PETR4F/petr4f -> PETR4)."""
    t = t.upper().strip()
    # Tickers fracionários B3 possuem 'F' no final de ações ordinárias/preferenciais (ex: PETR4F -> PETR4)
    if len(t) >= 6 and t.endswith("F") and t[-2].isdigit() and t[:4].isalpha():
        return t[:-1]
    return t


def extrair_tickers_regex(texto: str) -> list[str]:
    achados = re.findall(config.REGEX_TICKER, str(texto))
    normalizados = {normalizar_ticker(t) for t in achados}
    return sorted({t for t in normalizados if t not in config.STOPLIST_TICKERS})


# Expressões idiomáticas com o verbo valer que NÃO representam a empresa Vale S.A.
EXPRESSOES_VERBO_VALER = (
    r"\b(vale\s+a\s+pena|"
    r"nao\s+vale(\s+a\s+pena)?|"
    r"quanto\s+vale|"
    r"mais\s+vale|"
    r"vale\s+(lembrar|ressaltar|destacar|notar|dizer|mencionar|tudo|o\s+risco))\b"
)


def extrair_tickers_nome(texto: str) -> list[str]:
    """Menções por nome da empresa. Nomes ambíguos (ex.: 'vale') exigem contexto financeiro e excluem expressões comuns."""
    t = sem_acento(str(texto)).lower()
    achados = set()

    for nome, ticker in config.NOMES_EMPRESAS.items():
        if nome == "vale":
            # Remove expressões idiomáticas do verbo valer ("vale a pena", etc.)
            t_vale = re.sub(EXPRESSOES_VERBO_VALER, " ", t)
            if not re.search(r"\bvale\b", t_vale):
                continue
            palavras = set(re.findall(r"\w+", t_vale))
            if not (palavras & config.PALAVRAS_CONTEXTO_FINANCEIRO):
                continue
            achados.add(ticker)
        else:
            if re.search(rf"\b{re.escape(nome)}\b", t):
                if nome in config.NOMES_AMBIGUOS:
                    palavras = set(re.findall(r"\w+", t))
                    if not (palavras & config.PALAVRAS_CONTEXTO_FINANCEIRO):
                        continue
                achados.add(ticker)

    return sorted(achados)


def extrair_tickers(texto: str) -> list[str]:
    return sorted(set(extrair_tickers_regex(texto)) | set(extrair_tickers_nome(texto)))


def limpar_posts(df: pd.DataFrame, tz_origem: str = "UTC") -> pd.DataFrame:
    """Pipeline de limpeza: fuso, nulos, duplicatas exatas, tickers, tamanho do texto."""
    out = df.copy()
    n0 = len(out)
    out["id"] = out["id"].astype(str)
    if "autor_id" in out.columns:
        out["autor_id"] = out["autor_id"].astype(str)
    out["data_hora"] = padronizar_fuso(out["data_hora"], tz_origem)
    out = out.dropna(subset=["id", "data_hora", "texto"])
    out["texto"] = out["texto"].astype(str).str.strip()
    out = out[out["texto"].str.len() > 0]
    out = out.drop_duplicates(subset="id")
    # duplicata exata = mesmo autor + mesmo texto + mesmo instante
    out = out.drop_duplicates(subset=["autor_id", "texto", "data_hora"])
    out["texto_norm"] = out["texto"].map(normalizar_texto)
    if "ativo" in out.columns:
        out["tickers"] = [
            sorted(set(extrair_tickers(t)) | set(extrair_tickers(a)))
            for t, a in zip(out["texto"], out["ativo"].fillna(""))
        ]
    else:
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
