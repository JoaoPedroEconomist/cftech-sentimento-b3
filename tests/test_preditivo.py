import numpy as np
import pandas as pd
import pytest

from src import mercado, preditivo as pr

TZ = "America/Sao_Paulo"
# semana: seg 2026-03-02 ... sex 06; sáb 07/dom 08 sem pregão; seg 09
CAL = pd.DatetimeIndex(pd.bdate_range("2026-03-02", "2026-03-20"))


def _ts(s):
    return pd.Series([pd.Timestamp(s, tz=TZ)])


def test_post_antes_do_corte_vai_para_o_mesmo_dia():
    assert pr.atribuir_pregao(_ts("2026-03-04 14:30"), CAL).iloc[0] == pd.Timestamp("2026-03-04")


def test_post_das_20h_vai_para_o_dia_seguinte():
    assert pr.atribuir_pregao(_ts("2026-03-04 20:00"), CAL).iloc[0] == pd.Timestamp("2026-03-05")


def test_post_sexta_noite_vai_para_segunda():
    assert pr.atribuir_pregao(_ts("2026-03-06 21:00"), CAL).iloc[0] == pd.Timestamp("2026-03-09")


def test_post_no_fim_de_semana_vai_para_segunda():
    assert pr.atribuir_pregao(_ts("2026-03-07 10:00"), CAL).iloc[0] == pd.Timestamp("2026-03-09")


def test_post_apos_ultimo_pregao_e_descartado():
    assert pd.isna(pr.atribuir_pregao(_ts("2026-03-20 18:00"), CAL).iloc[0])


def test_corte_17h_exato():
    assert pr.atribuir_pregao(_ts("2026-03-04 16:59"), CAL).iloc[0] == pd.Timestamp("2026-03-04")
    assert pr.atribuir_pregao(_ts("2026-03-04 17:00"), CAL).iloc[0] == pd.Timestamp("2026-03-05")


def _posts_sent(sents, ticker="ZZZZ3", dia="2026-03-04", autores=None):
    n = len(sents)
    return pd.DataFrame(
        {
            "id": [f"p{i}" for i in range(n)],
            "autor_id": autores or [f"a{i}" for i in range(n)],
            "data_hora": [pd.Timestamp(f"{dia} 11:00", tz=TZ) + pd.Timedelta(minutes=i) for i in range(n)],
            "ticker": ticker,
            "sentimento": sents,
        }
    )


def test_indice_formula():
    d = _posts_sent(["positivo", "positivo", "negativo", "neutro"])
    idx = pr.indice_diario(d, CAL, n_min=3)
    assert idx.loc[0, "indice"] == pytest.approx((2 - 1) / 4)
    assert idx.loc[0, "n_posts"] == 4


def test_indice_n_min_filtra():
    d = _posts_sent(["positivo", "negativo"])
    assert pr.indice_diario(d, CAL, n_min=3).empty


def test_um_voto_por_autor():
    d = _posts_sent(["positivo"] * 5 + ["negativo"], autores=["spam"] * 5 + ["b"])
    base = pr.indice_diario(d, CAL, n_min=2)
    um = pr.indice_diario(d, CAL, n_min=2, um_voto_por_autor=True)
    assert base.loc[0, "indice"] == pytest.approx(4 / 6)
    assert um.loc[0, "indice"] == pytest.approx(0.0)  # spammer vale 1 voto


def test_excluir_ids_remove_coordenados():
    d = _posts_sent(["positivo"] * 3 + ["negativo"] * 3)
    idx = pr.indice_diario(d, CAL, n_min=2, excluir_ids={"p0", "p1", "p2"})
    assert idx.loc[0, "indice"] == pytest.approx(-1.0)


def test_mercado_retornos_e_sem_look_ahead():
    datas = pd.bdate_range("2026-01-01", periods=40)
    preco = 100 * np.exp(np.arange(40) * 0.01)
    vol = np.full(40, 1000.0)
    vol[30] = 5000.0
    p = pd.DataFrame({"ticker": "ZZZZ3", "data": datas, "close": preco, "adj_close": preco, "volume": vol})
    m = mercado.construir_painel_mercado(p).set_index("data")
    assert m.loc[datas[10], "ret_t"] == pytest.approx(0.01)
    assert m.loc[datas[10], "ret_f1"] == pytest.approx(0.01)
    assert m.loc[datas[10], "ret_acum_f1_f5"] == pytest.approx(0.05)
    # volume anormal usa só média passada: no dia do pico é ~log(5)
    assert m.loc[datas[30], "vol_anormal_t"] == pytest.approx(np.log(5), abs=1e-6)
    assert m.loc[datas[29], "vol_anormal_f1"] == pytest.approx(np.log(5), abs=1e-6)


def _painel_sintetico(n_t=12, n_d=120, beta=0.0, seed=0, segue_preco=False):
    rng = np.random.default_rng(seed)
    linhas = []
    for t in range(n_t):
        ret = rng.normal(0, 0.02, n_d + 2)
        for d in range(1, n_d):
            if segue_preco:
                indice = np.clip(ret[d] * 30 + rng.normal(0, 0.3), -1, 1)  # otimismo segue o retorno de hoje
            else:
                indice = np.clip(rng.normal(0, 0.5), -1, 1)
            y = beta * indice + ret[d + 1]
            linhas.append({"ticker": f"T{t:02d}3", "data": pd.Timestamp("2026-01-01") + pd.Timedelta(days=d), "indice": indice,
                           "log_volume_posts": np.log1p(rng.integers(3, 15)), "ret_t": ret[d], "ret_lag1": ret[d - 1], "ret_f1": y,
                           "ret_acum_f1_f5": y * 2, "vol_anormal_t": rng.normal(), "vol_anormal_f1": rng.normal()})
    return pd.DataFrame(linhas)


def test_detecta_sinal_verdadeiro():
    tab = pr.rodar_testes({"v": _painel_sintetico(beta=0.05)}, dvs=["ret_f1"], incluir_placebo=False)
    r = tab[(tab.modelo == "controles") & (tab.dv == "ret_f1")].iloc[0]
    assert r["coef"] == pytest.approx(0.05, abs=0.01) and r["p"] < 0.01 and r["p_holm"] < 0.05


def test_sem_sinal_nao_rejeita():
    tab = pr.rodar_testes({"v": _painel_sintetico(beta=0.0, seed=3)}, dvs=["ret_f1"], incluir_placebo=False)
    r = tab[(tab.modelo == "controles")].iloc[0]
    assert r["p"] > 0.01


def test_controle_de_retorno_passado_elimina_sinal_espurio():
    """Sentimento que só segue o preço de hoje: sem controle parece 'sinal' no placebo (ret_lag1) / com controle some."""
    p = _painel_sintetico(beta=0.0, seed=1, segue_preco=True)
    tab = pr.rodar_testes({"v": p}, dvs=["ret_f1"], incluir_placebo=False)
    r = tab[(tab.modelo == "controles")].iloc[0]
    assert r["p"] > 0.01  # ret_f1 independente; o índice não prevê o futuro


def test_holm_so_na_familia_principal():
    tab = pr.rodar_testes({"a": _painel_sintetico(seed=5), "b": _painel_sintetico(seed=6)})
    assert tab["p_holm"].notna().sum() == 2 * 3  # 2 versões × 3 DVs (modelo controles)
    assert (tab.loc[tab.p_holm.notna(), "p_holm"] >= tab.loc[tab.p_holm.notna(), "p"]).all()
    assert tab[tab.dv == pr.DV_PLACEBO]["p_holm"].isna().all()


def test_conclusao_ha_sinal():
    tab = pr.rodar_testes({"a": _painel_sintetico(beta=0.05, seed=1), "b": _painel_sintetico(beta=0.05, seed=2)}, dvs=["ret_f1"], incluir_placebo=False)
    assert pr.conclusao(tab)["ha_sinal"] is True


def test_controle_constante_nao_quebra():
    p = _painel_sintetico(beta=0.05, seed=9)
    p["log_volume_posts"] = 1.0  # constante: colinear com o intercepto
    tab = pr.rodar_testes({"v": p}, dvs=["ret_f1"], incluir_placebo=False)
    r = tab[(tab.modelo == "controles")].iloc[0]
    assert np.isfinite(r["p"]) and np.isfinite(r["ep"])


def test_horario_corte_b3_dinamico():
    # Inverno nos EUA (março antes do 2º domingo) -> 17h
    assert mercado.obter_hora_corte_b3(pd.Timestamp("2026-03-04")) == 17
    # Verão nos EUA (DST ativo: meados de março a out/nov) -> 18h
    assert mercado.obter_hora_corte_b3(pd.Timestamp("2026-03-15")) == 18
    assert mercado.obter_hora_corte_b3(pd.Timestamp("2026-06-15")) == 18

    # Post em dia de horário estendido às 17h30 pertence ao pregão do próprio dia
    cal = pd.DatetimeIndex(pd.bdate_range("2026-03-16", "2026-03-20"))
    ts_mesmo_dia = _ts("2026-03-16 17:30")
    assert pr.atribuir_pregao(ts_mesmo_dia, cal, hora_corte="dinamico").iloc[0] == pd.Timestamp("2026-03-16")
    # Post após 18h vai para o pregão seguinte
    ts_proximo_dia = _ts("2026-03-16 18:05")
    assert pr.atribuir_pregao(ts_proximo_dia, cal, hora_corte="dinamico").iloc[0] == pd.Timestamp("2026-03-17")


def test_mercado_retorno_em_excesso_ibovespa():
    datas = pd.bdate_range("2026-01-01", periods=20)
    preco_ativo = 100 * np.exp(np.arange(20) * 0.03)  # +3% ao dia
    preco_ibov = 1000 * np.exp(np.arange(20) * 0.01)   # +1% ao dia
    p_ativo = pd.DataFrame({"ticker": "VALE3", "data": datas, "close": preco_ativo, "adj_close": preco_ativo, "volume": np.full(20, 1000.0)})
    p_ibov = pd.DataFrame({"data": datas, "close": preco_ibov, "adj_close": preco_ibov, "volume": np.full(20, 50000.0)})

    painel = mercado.construir_painel_mercado(p_ativo, ibov=p_ibov).set_index("data")
    # Retorno bruto = 3%, retorno Ibov = 1%, retorno em excesso = 2%
    assert painel.loc[datas[5], "ret_t"] == pytest.approx(0.03, abs=1e-5)
    assert painel.loc[datas[5], "ret_excesso_t"] == pytest.approx(0.02, abs=1e-5)
    assert painel.loc[datas[5], "ret_excesso_f1"] == pytest.approx(0.02, abs=1e-5)
