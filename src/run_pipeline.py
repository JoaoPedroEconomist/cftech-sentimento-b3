"""CLI do pipeline: `python -m src.run_pipeline <etapa> [opções]`.

Etapas: limpeza · amostra-rotulos · kappa-humanos · consenso · llm · concordancia · coordenacao · revisao-coordenacao · preditivo
"""
from __future__ import annotations

import argparse
import json
import sys

import pandas as pd

from . import config


def _env():
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass


def cmd_limpeza(_a):
    from .limpeza import main

    main()


def cmd_amostra_rotulos(_a):
    from .rotulagem import criar_template_rotulos

    posts = pd.read_parquet(config.POSTS_PARQUET)
    amostra = pd.read_csv(config.AMOSTRA_AVALIACAO)
    for who in ("A", "B"):
        out = config.DATA_PROC / f"rotulos_{who}.csv"
        if out.exists():
            print(f"{out.name} já existe — não sobrescrevo (evita perder rótulos).")
            continue
        criar_template_rotulos(amostra, posts, out)
        print(f"template criado: {out}")
    print("Cada membro preenche o SEU arquivo, sozinho, e commita antes de qualquer chamada ao LLM.")


def cmd_kappa_humanos(_a):
    from .rotulagem import divergencias, kappa_entre_humanos, ler_rotulos, validar_rotulos

    ra, rb = ler_rotulos(config.DATA_PROC / "rotulos_A.csv"), ler_rotulos(config.DATA_PROC / "rotulos_B.csv")
    for nome, r in (("A", ra), ("B", rb)):
        e = validar_rotulos(r)
        if e:
            sys.exit(f"rotulos_{nome}.csv inválido: {e}")
    res = kappa_entre_humanos(ra, rb)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    (config.DATA_PROC / "kappa_humanos.json").write_text(json.dumps(res, indent=2, ensure_ascii=False))
    d = divergencias(ra, rb)
    d.to_csv(config.DATA_PROC / "divergencias_humanos.csv", index=False)
    print(f"{len(d)} divergências em divergencias_humanos.csv. Resolva e crie decisoes_consenso.csv (id, sentimento, flags).")


def cmd_consenso(_a):
    from .rotulagem import consolidar_consenso, ler_rotulos

    ra, rb = ler_rotulos(config.DATA_PROC / "rotulos_A.csv"), ler_rotulos(config.DATA_PROC / "rotulos_B.csv")
    dec_p = config.DATA_PROC / "decisoes_consenso.csv"
    dec = ler_rotulos(dec_p) if dec_p.exists() else None
    cons = consolidar_consenso(ra, rb, dec)
    cons.to_csv(config.DATA_PROC / "rotulos_consenso.csv", index=False)
    print(f"consenso: {len(cons)} posts")


def cmd_llm(a):
    from .llm import classificar, registrar_custo
    from .limpeza import normalizar_texto

    _env()
    posts = pd.read_parquet(config.POSTS_PARQUET)
    amostra = pd.read_csv(config.AMOSTRA_AVALIACAO)
    ids_aval = set(amostra["id"].astype(str))
    proibidos = set(posts.loc[posts["id"].astype(str).isin(ids_aval), "texto"].map(normalizar_texto))
    base = posts[posts["id"].astype(str).isin(ids_aval)] if a.avaliacao else posts
    saida, info = classificar(base, a.versao, modelo=a.modelo, dry_run=a.dry_run, proibidos=proibidos)
    print(json.dumps(info, indent=2, ensure_ascii=False, default=str))
    if a.dry_run:
        return
    registrar_custo(info)
    if not a.avaliacao:
        dest = config.DATA_PROC / f"sentimento_llm_{a.versao}.parquet"
        saida.to_parquet(dest, index=False)
        # arquivo consolidado exigido pelo case: formato longo com coluna versao_prompt
        partes = [pd.read_parquet(p) for p in sorted(config.DATA_PROC.glob("sentimento_llm_v*.parquet"))]
        pd.concat(partes, ignore_index=True).to_parquet(config.LLM_PARQUET, index=False)
    else:
        saida.to_parquet(config.DATA_PROC / f"sentimento_llm_aval_{a.versao}.parquet", index=False)


def cmd_concordancia(_a):
    from . import concordancia as c
    from .rotulagem import ler_rotulos

    gab = ler_rotulos(config.DATA_PROC / "rotulos_consenso.csv")
    posts = pd.read_parquet(config.POSTS_PARQUET)
    res = {}
    for v in ("v1", "v2"):
        llm = pd.read_parquet(config.DATA_PROC / f"sentimento_llm_aval_{v}.parquet")
        m = c.juntar(gab, llm, posts)
        res[v] = m
        c.matriz_confusao(m).to_csv(config.REPORTS / f"matriz_confusao_{v}.csv")
        c.discordancias(m).to_csv(config.DATA_PROC / f"discordancias_{v}.csv", index=False)
    tab = c.tabela_kappas(res)
    tab.to_csv(config.REPORTS / "tabela_kappas.csv", index=False)
    print(tab.round(3).to_string(index=False))
    print("Revise discordancias_v*.csv e preencha 'categoria_erro_revisada' manualmente.")


def cmd_coordenacao(_a):
    from . import coordenacao as co
    from . import mercado

    posts = pd.read_parquet(config.POSTS_PARQUET)
    liq = None
    try:
        from .limpeza import explodir_tickers

        tks = explodir_tickers(posts)["ticker"].unique().tolist()
        precos = mercado.baixar_precos(tks, posts["data_hora"].min().date(), (posts["data_hora"].max() + pd.Timedelta(days=10)).date())
        liq = mercado.liquidez_por_ticker(precos)
    except Exception as e:  # noqa: BLE001
        print(f"aviso: sem liquidez ({e}); pesos renormalizados")
    cl, mapa = co.detectar(posts, liq)
    cl.to_parquet(config.DATA_PROC / "clusters_todos.parquet", index=False)
    mapa.to_parquet(config.DATA_PROC / "post_cluster.parquet", index=False)
    rev = co.amostra_para_revisao(cl, posts)
    out = config.CLUSTERS_REVISADOS_CSV
    if out.exists():
        print(f"{out.name} já existe — não sobrescrevo (decisões humanas).")
    else:
        rev.to_csv(out, index=False)
        print(f"{len(rev)} clusters para revisão em {out}. Preencha decisao_humana e justificativa.")


def cmd_preditivo(a):
    from . import coordenacao as co
    from . import mercado, preditivo as pr
    from .concordancia import ajustar_por_matriz
    from .limpeza import explodir_tickers

    posts = pd.read_parquet(config.POSTS_PARQUET)
    llm = pd.read_parquet(config.LLM_PARQUET)
    ex = explodir_tickers(posts)[["id", "autor_id", "data_hora", "ticker"]]
    tks = ex["ticker"].unique().tolist()
    ini, fim = ex["data_hora"].min().date(), (ex["data_hora"].max() + pd.Timedelta(days=15)).date()
    precos = mercado.baixar_precos(tks, ini, fim)
    cal = mercado.baixar_calendario(ini, fim)
    merc = mercado.construir_painel_mercado(precos)

    def sinal(versao_col: pd.DataFrame, excluir=None):
        d = ex.merge(versao_col[["id", "sentimento"]], on="id")
        idx = pr.indice_diario(d, cal, hora_corte=a.hora_corte, n_min=a.n_min, um_voto_por_autor=a.um_voto, excluir_ids=excluir)
        return pr.montar_painel(idx, merc)

    v1 = llm[llm["versao_prompt"] == "v1"].copy()
    v2 = llm[llm["versao_prompt"] == "v2"].copy()
    rev = pd.read_csv(config.CLUSTERS_REVISADOS_CSV)
    erros = co.validar_revisao(rev)
    if erros:
        sys.exit(f"clusters_revisados.csv incompleto: {erros}")
    coord = co.posts_coordenados(rev)
    paineis = {
        "llm_bruto": sinal(v1),
        "llm_corrigido": sinal(v2),
        "sem_coordenados": sinal(v2, excluir=coord),
    }
    tab = pr.rodar_testes(paineis, efeitos_fixos=a.efeitos_fixos)
    tab.to_csv(config.REPORTS / "resultados_preditivo.csv", index=False)
    print(tab.round(4).to_string(index=False))
    print(json.dumps(pr.conclusao(tab), indent=2))


def main(argv=None):
    p = argparse.ArgumentParser(prog="run_pipeline")
    sp = p.add_subparsers(dest="etapa", required=True)
    for nome, fn in [("limpeza", cmd_limpeza), ("amostra-rotulos", cmd_amostra_rotulos), ("kappa-humanos", cmd_kappa_humanos), ("consenso", cmd_consenso), ("concordancia", cmd_concordancia), ("coordenacao", cmd_coordenacao)]:
        sp.add_parser(nome).set_defaults(fn=fn)
    s = sp.add_parser("llm")
    s.add_argument("--versao", required=True, choices=["v1", "v2"])
    s.add_argument("--avaliacao", action="store_true", help="só os 100 posts da amostra de avaliação")
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--modelo", default=None)
    s.set_defaults(fn=cmd_llm)
    s = sp.add_parser("preditivo")
    s.add_argument("--hora-corte", type=int, default=config.HORA_CORTE)
    s.add_argument("--n-min", type=int, default=config.N_MIN_POSTS)
    s.add_argument("--um-voto", action="store_true", help="1 voto por autor por ticker-dia (robustez)")
    s.add_argument("--efeitos-fixos", action="store_true")
    s.set_defaults(fn=cmd_preditivo)
    a = p.parse_args(argv)
    config.REPORTS.mkdir(exist_ok=True)
    a.fn(a)


if __name__ == "__main__":
    main()
