import json

import pandas as pd
import pytest

from src import config, llm, toon


def _fake_cliente(contador):
    def chamar(system, user, modelo):
        contador["n"] += 1
        posts = toon.decode_tabular(user, "posts")
        linhas = [{"id": p["id"], "sentimento": "positivo", "confianca": 0.9, "ironia": False, "justificativa_curta": "ok, tudo"} for p in posts]
        return toon.encode_tabular("resultados", linhas, ["id", "sentimento", "confianca", "ironia", "justificativa_curta"]), 100, 50

    return chamar


@pytest.fixture(autouse=True)
def cache_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_CACHE", tmp_path / "cache")


def test_parse_resposta_valida_e_invalida():
    ok = 'resultados[1]{id,sentimento,confianca,ironia,justificativa_curta}:\n  1,neutro,0.5,false,"x, y"'
    r = llm.parse_resposta(ok)[0]
    assert r.sentimento == "neutro" and r.justificativa_curta == "x, y" and r.id == "1"
    json_legado = '{"resultados":[{"id":"1","sentimento":"neutro","confianca":0.5,"ironia":false,"justificativa_curta":"x"}]}'
    assert llm.parse_resposta(json_legado)[0].sentimento == "neutro"
    with pytest.raises(ValueError):  # nº de linhas diverge do declarado (resposta truncada)
        llm.parse_resposta("resultados[2]{id,sentimento,confianca,ironia,justificativa_curta}:\n  1,neutro,0.5,false,\"x\"")
    with pytest.raises(ValueError):
        llm.parse_resposta('{"resultados":[{"id":"1","sentimento":"muito_bom","confianca":0.5,"ironia":false}]}')
    with pytest.raises(ValueError):
        llm.parse_resposta("sem json")


def test_parse_resposta_com_cerca_markdown():
    t = '```\nresultados[1]{id,sentimento,confianca,ironia,justificativa_curta}:\n  1,negativo,1,true,""\n```'
    assert llm.parse_resposta(t)[0].ironia is True


def test_cache_evita_chamada_repetida():
    posts = pd.DataFrame({"id": [str(i) for i in range(5)], "texto": [f"post {i}" for i in range(5)]})
    c = {"n": 0}
    out1, info1 = llm.classificar(posts, "v1", batch=10, chamar=_fake_cliente(c))
    assert len(out1) == 5 and c["n"] == 1
    out2, info2 = llm.classificar(posts, "v1", batch=10, chamar=_fake_cliente(c))
    assert c["n"] == 1  # nada novo chamado
    assert info2["em_cache"] == 5


def test_cache_chave_composta_id_e_texto():
    # Se dois posts têm o mesmo id mas textos diferentes (ex: post de teste vs real), o cache não colide
    posts1 = pd.DataFrame({"id": ["1"], "texto": ["PETR4 lucro recorde"]})
    posts2 = pd.DataFrame({"id": ["1"], "texto": ["VALE3 despencou prejuízo"]})
    c = {"n": 0}
    out1, _ = llm.classificar(posts1, "v1", chamar=_fake_cliente(c))
    assert c["n"] == 1
    out2, _ = llm.classificar(posts2, "v1", chamar=_fake_cliente(c))
    assert c["n"] == 2  # chamou novamente porque o texto do post mudou


def test_retry_em_json_invalido():
    posts = pd.DataFrame({"id": ["1"], "texto": ["x"]})
    estado = {"n": 0}

    def chamar(system, user, modelo):
        estado["n"] += 1
        if estado["n"] == 1:
            return "lixo", 10, 5
        return 'resultados[1]{id,sentimento,confianca,ironia,justificativa_curta}:\n  1,neutro,0.5,false,""', 10, 5

    import src.llm as m

    m.time.sleep = lambda s: None  # sem espera nos testes
    out, info = llm.classificar(posts, "v1", chamar=chamar)
    assert len(out) == 1 and estado["n"] == 2


def test_dry_run_nao_chama():
    posts = pd.DataFrame({"id": ["1", "2"], "texto": ["a", "b"]})
    c = {"n": 0}
    _, info = llm.classificar(posts, "v1", chamar=_fake_cliente(c), dry_run=True)
    assert c["n"] == 0 and info["tokens_in_estimados"] > 0


def test_custo(monkeypatch):
    c = llm.Custo(3.0, 15.0, None)
    c.somar(1_000_000, 100_000)
    assert c.usd == pytest.approx(3.0 + 1.5)
    c2 = llm.Custo(3.0, 15.0, 1.0)
    with pytest.raises(RuntimeError):
        c2.somar(1_000_000, 0)
