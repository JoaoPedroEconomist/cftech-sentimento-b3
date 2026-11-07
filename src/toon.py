"""Codec mínimo de TOON (Token-Oriented Object Notation), só o formato tabular de arrays uniformes.

    posts[2]{id,texto}:
      p1,"Compra, vai subir"
      p2,Alguém sabe o dividendo?

Os nomes dos campos aparecem uma vez no cabeçalho (JSON repete a chave em cada objeto), e o cabeçalho
declara o nº de linhas, o que permite validar respostas truncadas.
"""
from __future__ import annotations

import re

_HEADER = re.compile(r"^\s*([A-Za-z_]\w*)\[(\d+)\]\{([^}]*)\}:\s*$")
_RESERVADO = re.compile(r"^(true|false|null|-?\d+(\.\d+)?([eE][+-]?\d+)?)$")


def _fmt(v) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v) if isinstance(v, float) else str(v)
    s = str(v)
    precisa = s == "" or s != s.strip() or _RESERVADO.match(s) or any(c in s for c in ',"\\\n\r\t')
    if not precisa:
        return s
    s = s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
    return f'"{s}"'


def encode_tabular(nome: str, linhas: list[dict], campos: list[str]) -> str:
    cab = f"{nome}[{len(linhas)}]{{{','.join(campos)}}}:"
    corpo = ["  " + ",".join(_fmt(l.get(c)) for c in campos) for l in linhas]
    return "\n".join([cab, *corpo])


def _split(linha: str) -> list[str | None]:
    """Divide por vírgula respeitando aspas. Valores entre aspas voltam como str (marcados), os demais crus."""
    out: list = []
    i, n = 0, len(linha)
    while i <= n:
        if i < n and linha[i] == '"':
            j, buf = i + 1, []
            while j < n and linha[j] != '"':
                if linha[j] == "\\" and j + 1 < n:
                    j += 1
                    buf.append({"n": "\n", "r": "\r", "t": "\t"}.get(linha[j], linha[j]))
                else:
                    buf.append(linha[j])
                j += 1
            if j >= n:
                raise ValueError("aspas não fechadas")
            out.append(("q", "".join(buf)))
            j += 1
            if j < n and linha[j] != ",":
                raise ValueError("texto após aspas")
            i = j + 1
        else:
            j = linha.find(",", i)
            j = n if j == -1 else j
            out.append(("r", linha[i:j].strip()))
            i = j + 1
    return out


def _tipar(tok) -> object:
    tipo, v = tok
    if tipo == "q":
        return v
    if v == "null":
        return None
    if v == "true":
        return True
    if v == "false":
        return False
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    if re.fullmatch(r"-?\d*\.\d+([eE][+-]?\d+)?", v):
        return float(v)
    return v


def decode_tabular(texto: str, nome: str | None = None) -> list[dict]:
    """Lê o primeiro bloco tabular (ignora cercas ``` e texto antes do cabeçalho).
    Levanta ValueError se faltar cabeçalho, se o nº de linhas divergir do declarado ou se houver coluna a mais/menos."""
    linhas = [l for l in texto.replace("\r\n", "\n").split("\n") if not l.strip().startswith("```")]
    for k, l in enumerate(linhas):
        m = _HEADER.match(l)
        if m and (nome is None or m.group(1) == nome):
            n_decl, campos = int(m.group(2)), [c.strip() for c in m.group(3).split(",")]
            break
    else:
        raise ValueError("cabeçalho TOON não encontrado")
    corpo = [l for l in linhas[k + 1 :] if l.strip()]
    if len(corpo) != n_decl:
        raise ValueError(f"TOON declara {n_decl} linhas, recebi {len(corpo)}")
    out = []
    for l in corpo:
        l_limpa = re.sub(r'""([^"]+?)""', r'"\1"', l.strip())
        toks = _split(l_limpa)
        if len(toks) != len(campos):
            raise ValueError(f"linha com {len(toks)} colunas, esperado {len(campos)}")
        out.append({c: _tipar(t) for c, t in zip(campos, toks)})
    return out
