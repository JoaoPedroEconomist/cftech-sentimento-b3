import pandas as pd
import pytest

from src import concordancia as c
from src import config


def _m():
    return pd.DataFrame(
        {
            "id": list("abcdef"),
            "sentimento_hum": ["positivo", "negativo", "neutro", "negativo", "positivo", "neutro"],
            "sentimento_llm": ["positivo", "positivo", "neutro", "negativo", "neutro", "neutro"],
            "ironia_hum": [0, 1, 0, 0, 0, 0],
            "ironia_llm": [False, False, False, False, False, True],
            "giria_meme": [0, 0, 0, 0, 1, 0],
            "suspeita_coordenacao": 0,
            "irrelevante": 0,
            "confianca": [0.9, 0.95, 0.8, 0.7, 0.6, 0.9],
            "justificativa_curta": "x",
            "texto": ["a", "que ótimo 🙃", "c", "d", "e foguete", "f?"],
        }
    )


def test_kappa_llm_e_acuracia():
    k = c.kappa_llm(_m())
    assert k["acuracia"] == pytest.approx(4 / 6)
    assert -1 <= k["kappa"] <= 1


def test_matriz_confusao_soma():
    cm = c.matriz_confusao(_m())
    assert cm.values.sum() == 6
    assert cm.loc["hum_negativo", "llm_positivo"] == 1


def test_kappa_por_ironia_tem_dois_grupos():
    t = c.kappa_por_ironia(_m())
    assert set(t["grupo"]) == {"sem_ironia", "com_ironia"}
    assert t.set_index("grupo").loc["com_ironia", "n"] == 1


def test_deteccao_ironia():
    d = c.deteccao_ironia(_m())
    assert d["vp"] == 0 and d["fn"] == 1 and d["fp"] == 1


def test_discordancias_e_catalogo():
    d = c.discordancias(_m())
    assert len(d) == 2
    assert set(d["categoria_erro"]) == {"ironia", "giria_meme"}
    cat = c.catalogo_erros(d)
    assert cat["n"].sum() == 2
    assert cat.set_index("categoria").loc["ironia", "n_conf_alta"] == 1  # erro com confiança 0.95


def test_ajuste_por_matriz():
    cm = pd.DataFrame([[8, 2, 0], [1, 3, 6], [0, 1, 9]], index=[f"hum_{l}" for l in config.SENTIMENTOS], columns=[f"llm_{l}" for l in config.SENTIMENTOS])
    s = pd.Series(["positivo", "neutro", "negativo"])
    adj = c.ajustar_por_matriz(s, cm)
    # coluna llm_positivo: max na linha hum_positivo(9)? colunas: negativo=[8,1,0], neutro=[2,3,1], positivo=[0,6,9]
    assert list(adj) == ["positivo", "neutro", "negativo"]


def test_tabela_kappas_inclui_acuracia_e_contagem_ironia():
    m = _m()
    tab = c.tabela_kappas({"v1": m})
    assert "acuracia_com_ironia" in tab.columns
    assert "n_com_ironia" in tab.columns
    assert "acuracia_sem_ironia" in tab.columns
    assert "n_sem_ironia" in tab.columns
    assert tab.loc[0, "n_com_ironia"] == 1
    assert tab.loc[0, "n_sem_ironia"] == 5
