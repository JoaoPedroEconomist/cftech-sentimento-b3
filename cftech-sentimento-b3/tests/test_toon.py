import json

import pytest

from src import toon

C = ["id", "texto"]


def test_roundtrip_com_virgula_aspas_quebra_e_acento():
    linhas = [{"id": "1", "texto": 'Compra, vai "subir"\nja'}, {"id": "2", "texto": "Alguém sabe? 🚀"}, {"id": "3", "texto": ""}]
    assert toon.decode_tabular(toon.encode_tabular("posts", linhas, C), "posts") == linhas


def test_ids_numericos_ficam_string():
    out = toon.decode_tabular(toon.encode_tabular("posts", [{"id": "123", "texto": "x"}], C), "posts")
    assert out[0]["id"] == "123"


def test_tipos():
    r = toon.decode_tabular("r[1]{a,b,c,d}:\n  x,0.5,true,null", "r")[0]
    assert r == {"a": "x", "b": 0.5, "c": True, "d": None}


def test_erros():
    with pytest.raises(ValueError):
        toon.decode_tabular("sem cabecalho")
    with pytest.raises(ValueError):
        toon.decode_tabular("r[2]{a}:\n  1")  # truncado
    with pytest.raises(ValueError):
        toon.decode_tabular("r[1]{a,b}:\n  1")  # coluna faltando
    with pytest.raises(ValueError):
        toon.decode_tabular('r[1]{a}:\n  "aberta')


def test_economiza_caracteres_vs_json():
    linhas = [{"id": f"p{i}", "texto": f"texto do post numero {i}"} for i in range(20)]
    assert len(toon.encode_tabular("posts", linhas, C)) < 0.75 * len(json.dumps(linhas, ensure_ascii=False))
