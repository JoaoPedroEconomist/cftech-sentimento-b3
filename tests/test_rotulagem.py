import pandas as pd
import pytest

from src import config, rotulagem


def _r(sent, ironia=None):
    n = len(sent)
    d = {"id": [str(i) for i in range(n)], "sentimento": sent}
    for f in config.FLAGS:
        d[f] = [0] * n
    if ironia is not None:
        d["ironia"] = ironia
    return pd.DataFrame(d)


def test_kappa_perfeito():
    a = _r(["positivo", "neutro", "negativo", "positivo"])
    assert rotulagem.kappa_entre_humanos(a, a)["kappa_sentimento"] == pytest.approx(1.0)


def test_kappa_valor_conhecido():
    a = _r(["positivo", "positivo", "negativo", "negativo"])
    b = _r(["positivo", "negativo", "negativo", "negativo"])
    # po = 0.75 ; pe = 0.5*0.25 + 0.5*0.75 = 0.5 -> kappa = 0.5
    assert rotulagem.kappa_entre_humanos(a, b)["kappa_sentimento"] == pytest.approx(0.5)


def test_validar_rotulos_detecta_invalidos():
    r = _r(["positivo", "talvez"])
    assert any("inválidos" in e for e in rotulagem.validar_rotulos(r))


def test_divergencias_e_consenso():
    a = _r(["positivo", "neutro", "negativo"])
    b = _r(["positivo", "negativo", "negativo"])
    assert list(rotulagem.divergencias(a, b)["id"]) == ["1"]
    with pytest.raises(ValueError):
        rotulagem.consolidar_consenso(a, b)  # divergência sem decisão
    dec = pd.DataFrame({"id": ["1"], "sentimento": ["neutro"], **{f: [0] for f in config.FLAGS}})
    c = rotulagem.consolidar_consenso(a, b, dec)
    assert c.set_index("id").loc["1", "sentimento"] == "neutro"
    assert c.set_index("id").loc["0", "origem"] == "concordancia"
