"""Etapa 03.3 — classificação de sentimento com LLM.

Requisitos do case: prompt versionado, JSON validado (pydantic), temperatura 0, lotes,
retry em caso de erro, cache por id (e versão do prompt) e registro de tokens/custo.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field, ValidationError, field_validator

from . import config, toon


# ---------- schema de saída ----------
class Resultado(BaseModel):
    id: str
    sentimento: Literal["positivo", "neutro", "negativo"]
    confianca: float = Field(ge=0, le=1)
    ironia: bool
    justificativa_curta: str = ""

    @field_validator("id", mode="before")
    @classmethod
    def _id_str(cls, v):
        return str(v)


class Lote(BaseModel):
    resultados: list[Resultado]


# ---------- prompt versionado ----------
def carregar_prompt(versao: str) -> tuple[str, str, str]:
    """Lê prompts/sentimento_<versao>.md. Retorna (system, user_template, hash)."""
    p = config.PROMPTS / f"sentimento_{versao}.md"
    txt = p.read_text(encoding="utf-8")
    h = hashlib.sha256(txt.encode()).hexdigest()[:10]
    # remove comentários HTML de cabeçalho
    import re

    txt_limpo = re.sub(r"<!--.*?-->", "", txt, flags=re.S)
    partes = txt_limpo.split("## USER")
    system = partes[0].replace("## SYSTEM", "").strip()
    user = partes[1].strip()
    return system, user, h


def montar_user(user_template: str, posts: list[dict]) -> str:
    """Posts em TOON tabular (nomes de campo uma só vez no cabeçalho)."""
    bloco = toon.encode_tabular("posts", [{"id": str(p["id"]), "texto": " ".join(str(p["texto"]).split())} for p in posts], ["id", "texto"])
    return user_template.replace("{{POSTS_TOON}}", bloco)


def parse_resposta(texto: str) -> list[Resultado]:
    """Lê a resposta (TOON tabular; aceita JSON legado) e valida cada linha. Levanta ValueError se inválida."""
    t = texto.strip()
    try:
        if "resultados[" in t:
            return [Resultado.model_validate(r) for r in toon.decode_tabular(t, "resultados")]
        ini, fim = t.find("{"), t.rfind("}")
        if ini == -1 or fim == -1:
            raise ValueError("resposta sem TOON/JSON")
        return Lote.model_validate_json(t[ini : fim + 1]).resultados
    except ValidationError as e:
        raise ValueError(f"fora do schema: {e.error_count()} erro(s)") from e


# ---------- custo ----------
class Custo:
    def __init__(self, preco_in: float | None, preco_out: float | None, orcamento: float | None):
        self.tok_in = 0
        self.tok_out = 0
        self.preco_in = preco_in
        self.preco_out = preco_out
        self.orcamento = orcamento

    def somar(self, tin: int, tout: int) -> None:
        self.tok_in += tin
        self.tok_out += tout
        if self.orcamento is not None and self.usd is not None and self.usd > self.orcamento:
            raise RuntimeError(f"Orçamento estourado: US$ {self.usd:.2f} > {self.orcamento:.2f}")

    @property
    def usd(self) -> float | None:
        if self.preco_in is None or self.preco_out is None:
            return None
        return self.tok_in / 1e6 * self.preco_in + self.tok_out / 1e6 * self.preco_out

    def resumo(self) -> dict:
        return {"tokens_in": self.tok_in, "tokens_out": self.tok_out, "custo_usd": self.usd}


def _float_env(nome: str) -> float | None:
    v = os.getenv(nome, "").strip()
    return float(v) if v else None


def estimar_tokens(texto: str) -> int:
    """Estimativa grosseira (~4 caracteres/token) para --dry-run."""
    return max(1, len(texto) // 4)


# ---------- cache em disco ----------
def _cache_path(versao: str, hash_prompt: str, modelo: str) -> Path:
    config.DATA_CACHE.mkdir(parents=True, exist_ok=True)
    return config.DATA_CACHE / f"cache_{versao}_{hash_prompt}_{modelo}.jsonl"


def ler_cache(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    out = {}
    for linha in path.read_text(encoding="utf-8").splitlines():
        if linha.strip():
            d = json.loads(linha)
            out[str(d["id"])] = d
    return out


def gravar_cache(path: Path, resultados: list[dict]) -> None:
    with path.open("a", encoding="utf-8") as f:
        for r in resultados:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


# ---------- chamada ao LLM (cliente injetável para testes) ----------
def chamar_anthropic(system: str, user: str, modelo: str, max_tokens: int = 2048):
    """Retorna (texto, tokens_in, tokens_out). O bloco de sistema (regras fixas) usa cache de prompt:
    a partir da 2ª chamada, a parte repetida é cobrada a uma fração do preço de entrada."""
    import anthropic

    client = anthropic.Anthropic()  # lê ANTHROPIC_API_KEY do ambiente
    resp = client.messages.create(
        model=modelo,
        max_tokens=max_tokens,
        temperature=0,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    )
    texto = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    u = resp.usage
    tin = u.input_tokens + (getattr(u, "cache_creation_input_tokens", 0) or 0) + (getattr(u, "cache_read_input_tokens", 0) or 0)
    return texto, tin, u.output_tokens


def chamar_gemini(system: str, user: str, modelo: str, max_tokens: int = 2048):
    """Retorna (texto, tokens_in, tokens_out). Chama Gemini via google.genai Interactions API."""
    from google import genai

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    client = genai.Client(api_key=api_key)
    prompt = f"{system}\n\n{user}" if system else user
    interaction = client.interactions.create(
        model=modelo,
        input=prompt,
    )
    texto = interaction.output_text or ""
    tin, tout = 0, 0
    if hasattr(interaction, "usage") and interaction.usage:
        tin = getattr(interaction.usage, "total_input_tokens", 0) or 0
        tout = getattr(interaction.usage, "total_output_tokens", 0) or 0
    return texto, tin, tout


def chamar_provedor(system: str, user: str, modelo: str, max_tokens: int = 2048):
    """Roteia para Gemini ou Anthropic dependendo do modelo ou da chave de API configurada."""
    api_key_ant = os.getenv("ANTHROPIC_API_KEY", "")
    if "gemini" in modelo.lower() or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or api_key_ant.startswith("AQ."):
        return chamar_gemini(system, user, modelo, max_tokens)
    return chamar_anthropic(system, user, modelo, max_tokens)


def classificar(
    posts: pd.DataFrame,
    versao: str,
    modelo: str | None = None,
    batch: int = config.LLM_BATCH,
    chamar=None,
    dry_run: bool = False,
    proibidos: set[str] | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Classifica `posts` (colunas id, texto). Usa cache por id; retry; registra custo.

    `proibidos`: textos normalizados da amostra de avaliação; levanta erro se aparecerem no prompt (contaminação).
    """
    if chamar is None:
        chamar = chamar_provedor
    modelo = modelo or os.getenv("LLM_MODEL", config.LLM_MODEL_PADRAO)
    system, user_tpl, h = carregar_prompt(versao)
    if proibidos:
        from .limpeza import normalizar_texto

        corpo = normalizar_texto(system + user_tpl)
        vazou = [t for t in proibidos if t and t in corpo]
        if vazou:
            raise ValueError(f"Contaminação: {len(vazou)} post(s) de avaliação aparecem no prompt {versao}")

    cache_p = _cache_path(versao, h, modelo)
    cache = ler_cache(cache_p)
    custo = Custo(_float_env("LLM_PRICE_IN_PER_MTOK"), _float_env("LLM_PRICE_OUT_PER_MTOK"), _float_env("LLM_BUDGET_USD"))

    pendentes = [r for r in posts[["id", "texto"]].to_dict("records") if str(r["id"]) not in cache]
    info = {"versao": versao, "hash_prompt": h, "modelo": modelo, "total": len(posts), "em_cache": len(posts) - len(pendentes), "chamadas": 0, "falhas": []}

    if dry_run:
        tin = sum(estimar_tokens(montar_user(user_tpl, pendentes[i : i + batch]) + system) for i in range(0, len(pendentes), batch))
        info.update({"dry_run": True, "tokens_in_estimados": tin, "tokens_out_estimados": len(pendentes) * 35})
        return pd.DataFrame(), info

    for i in range(0, len(pendentes), batch):
        lote = pendentes[i : i + batch]
        ids_lote = {str(p["id"]) for p in lote}
        user = montar_user(user_tpl, lote)
        ok = False
        for tent in range(1, config.LLM_MAX_RETRIES + 1):
            try:
                texto, tin, tout = chamar(system, user, modelo)
                custo.somar(tin, tout)
                info["chamadas"] += 1
                res = parse_resposta(texto)
                recebidos = {r.id for r in res}
                if recebidos != ids_lote:
                    raise ValueError(f"ids divergentes: faltam {len(ids_lote - recebidos)}, sobram {len(recebidos - ids_lote)}")
                linhas = [
                    {**r.model_dump(), "versao_prompt": versao, "hash_prompt": h, "modelo": modelo, "resposta_bruta_hash": hashlib.md5(texto.encode()).hexdigest()[:8]}
                    for r in res
                ]
                gravar_cache(cache_p, linhas)
                cache.update({r["id"]: r for r in linhas})
                ok = True
                break
            except RuntimeError:
                raise  # orçamento estourado: aborta
            except Exception as e:  # noqa: BLE001
                if tent == config.LLM_MAX_RETRIES:
                    info["falhas"].append({"ids": sorted(ids_lote)[:3], "erro": str(e)[:200]})
                else:
                    time.sleep(2**tent)
        if not ok and len(lote) > 1:
            # fallback: reprocessa 1 a 1 para isolar o post problemático
            for p in lote:
                try:
                    texto, tin, tout = chamar(system, montar_user(user_tpl, [p]), modelo)
                    custo.somar(tin, tout)
                    res = parse_resposta(texto)
                    linhas = [{**r.model_dump(), "versao_prompt": versao, "hash_prompt": h, "modelo": modelo, "resposta_bruta_hash": ""} for r in res if r.id == str(p["id"])]
                    gravar_cache(cache_p, linhas)
                    cache.update({r["id"]: r for r in linhas})
                except RuntimeError:
                    raise
                except Exception:  # noqa: BLE001
                    pass

    info.update(custo.resumo())
    saida = pd.DataFrame([cache[str(i)] for i in posts["id"].astype(str) if str(i) in cache])
    info["sem_resultado"] = len(posts) - len(saida)
    return saida, info


def registrar_custo(info: dict, caminho: Path | None = None) -> None:
    """Acumula o custo de cada execução em data/processed/custo_llm.jsonl (entregável: 'custo total registrado')."""
    caminho = caminho or (config.DATA_PROC / "custo_llm.jsonl")
    config.DATA_PROC.mkdir(parents=True, exist_ok=True)
    with caminho.open("a", encoding="utf-8") as f:
        f.write(json.dumps({**info, "ts": pd.Timestamp.now().isoformat()}, ensure_ascii=False) + "\n")
