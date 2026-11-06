import pandas as pd

from src import coordenacao as co
from src import limpeza


def _posts():
    t0 = pd.Timestamp("2026-03-02 11:00", tz="America/Sao_Paulo")
    linhas = []
    # campanha: 4 autores novos, texto quase idêntico, em 4 minutos, com urgência
    for i in range(4):
        linhas.append({"id": f"c{i}", "data_hora": t0 + pd.Timedelta(minutes=i), "autor_id": f"novo{i}", "plataforma": "x",
                       "texto": "ZZZZ3 vai a R$ 50 hoje! Entra agora antes que decole 🚀"})
    # conversa orgânica: textos diferentes, horas diferentes, autores com histórico
    textos = ["ZZZZ3 divulgou balanço e achei fraco", "Alguém sabe o dividendo de ZZZZ3?", "Mantenho posição em ZZZZ3 no longo prazo"]
    for i, tx in enumerate(textos):
        linhas.append({"id": f"o{i}", "data_hora": t0 + pd.Timedelta(hours=2 * (i + 1)), "autor_id": f"vet{i}", "plataforma": "x", "texto": tx})
    # histórico dos veteranos
    for v in range(3):
        for k in range(10):
            linhas.append({"id": f"h{v}_{k}", "data_hora": t0 - pd.Timedelta(days=k + 1), "autor_id": f"vet{v}", "plataforma": "x", "texto": f"outro assunto {k} sobre AAAA4"})
    return limpeza.limpar_posts(pd.DataFrame(linhas), tz_origem="America/Sao_Paulo")


def test_urgencia():
    assert co.urgencia_alvo("Entra agora que vai a R$ 50")
    assert not co.urgencia_alvo("Balanço fraco no trimestre")


def test_detecta_campanha_no_topo():
    posts = _posts()
    cl, mapa = co.detectar(posts)
    assert not cl.empty
    topo = cl.iloc[0]
    assert topo["ticker"] == "ZZZZ3"
    assert topo["n_autores"] == 4
    assert set(topo["ids"]) == {"c0", "c1", "c2", "c3"}
    assert topo["s_urgencia_alvo"] == 1.0
    assert topo["s_autor_novo"] == 1.0
    assert set(mapa["id"]) >= {"c0", "c1", "c2", "c3"}


def test_organico_nao_forma_cluster_de_similaridade():
    posts = _posts()
    cl, _ = co.detectar(posts)
    ids_org = {"o0", "o1", "o2"}
    for _, c in cl.iterrows():
        assert not ids_org.issubset(set(c["ids"]))


def test_revisao_e_posts_coordenados():
    posts = _posts()
    cl, _ = co.detectar(posts)
    rev = co.amostra_para_revisao(cl, posts, n=5)
    assert (rev["decisao_humana"] == "").all()  # o código NUNCA decide
    assert co.validar_revisao(rev)  # incompleto -> erros
    rev.loc[0, ["decisao_humana", "justificativa"]] = ["coordenado", "texto idêntico, 4 contas novas em 4 min"]
    rev.loc[1:, ["decisao_humana", "justificativa"]] = ["organico", "conversa espontânea variada"]
    assert co.validar_revisao(rev) == []
    assert {"c0", "c1", "c2", "c3"} <= co.posts_coordenados(rev)
    p = co.precisao_no_topo(rev)
    assert p["coordenado"] == 1 and p["n"] == len(rev)


def test_clusters_identicos_sao_unificados():
    posts = _posts()
    cl, _ = co.detectar(posts)
    chaves = cl["ids"].map(lambda x: tuple(sorted(x)))
    assert chaves.is_unique
    assert "similaridade" in cl.iloc[0]["tipo"] and "rajada" in cl.iloc[0]["tipo"]
