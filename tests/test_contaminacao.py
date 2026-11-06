"""Garante que nenhum dos 100 posts de avaliação aparece nos prompts (senão o kappa fica contaminado)."""
import pandas as pd
import pytest

from src import config, llm
from src.limpeza import normalizar_texto


def test_detecta_contaminacao():
    texto_aval = "post de avaliacao que nao pode aparecer"
    # simula prompt contendo o texto
    system, user, _ = llm.carregar_prompt("v2")
    corpo = normalizar_texto(system + user)
    assert texto_aval not in corpo  # prompt real está limpo
    posts = pd.DataFrame({"id": ["1"], "texto": ["x"]})
    # um 'proibido' presente no prompt deve estourar
    trecho = normalizar_texto("Mais um dia amando ver meu papel cair 8%")
    with pytest.raises(ValueError):
        llm.classificar(posts, "v2", dry_run=True, proibidos={trecho})


def test_prompts_existem_e_tem_placeholder():
    for v in ("v1", "v2"):
        _, user, h = llm.carregar_prompt(v)
        assert "{{POSTS_TOON}}" in user and len(h) == 10


@pytest.mark.skipif(not config.AMOSTRA_AVALIACAO.exists(), reason="amostra de avaliação não disponível")
def test_prompt_real_sem_posts_da_amostra():
    posts_p = config.POSTS_PARQUET
    if not posts_p.exists():
        pytest.skip("rode `limpeza` primeiro")
    posts = pd.read_parquet(posts_p)
    amostra = pd.read_csv(config.AMOSTRA_AVALIACAO)
    textos = posts[posts["id"].astype(str).isin(set(amostra["id"].astype(str)))]["texto"].map(normalizar_texto)
    for v in ("v1", "v2"):
        s, u, _ = llm.carregar_prompt(v)
        corpo = normalizar_texto(s + u)
        assert not any(t and t in corpo for t in textos), f"post de avaliação encontrado no prompt {v}"
