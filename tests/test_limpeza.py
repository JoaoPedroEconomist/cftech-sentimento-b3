import pandas as pd

from src import limpeza


def test_extrai_ticker_regex():
    assert limpeza.extrair_tickers_regex("Comprei PETR4 e VALE3 hoje") == ["PETR4", "VALE3"]


def test_regex_ignora_stoplist_e_minusculas():
    assert limpeza.extrair_tickers_regex("COVID19 petr4") == []


def test_nome_ambiguo_exige_contexto():
    assert limpeza.extrair_tickers_nome("isso não vale nada") == []
    assert limpeza.extrair_tickers_nome("vale vai pagar dividendo, comprar o papel") == ["VALE3"]


def test_nome_sem_acento():
    assert "ITUB4" in limpeza.extrair_tickers_nome("Itaú divulgou balanço")


def test_fuso_naive_assume_utc():
    s = pd.Series(["2026-03-02 20:00:00"])
    r = limpeza.padronizar_fuso(s, "UTC")
    assert r.iloc[0].hour == 17  # UTC-3


def test_limpar_remove_duplicatas_exatas():
    df = pd.DataFrame(
        {
            "id": ["1", "2", "3"],
            "data_hora": ["2026-03-02 13:00:00"] * 3,
            "autor_id": ["a", "a", "b"],
            "plataforma": ["x"] * 3,
            "texto": ["PETR4 vai subir", "PETR4 vai subir", "PETR4 vai subir"],
        }
    )
    out = limpeza.limpar_posts(df)
    assert len(out) == 2  # o par (autor a, mesmo texto, mesmo instante) cai
    assert out.attrs["n_removidos"] == 1
    assert all(t == ["PETR4"] for t in out["tickers"])


def test_explodir_tickers():
    df = pd.DataFrame({"id": ["1", "2"], "tickers": [["PETR4", "VALE3"], []]})
    ex = limpeza.explodir_tickers(df)
    assert list(ex["ticker"]) == ["PETR4", "VALE3"]
