"""Localizador de linha em YAML (D-07).

O criterio de aceite exige `arquivo:linha` em todo finding. Achados de
catalogo saiam com `linha: null` embora a linha do campo seja perfeitamente
determinavel — e um achado sem endereco custa ao revisor exatamente o
trabalho que o laudo deveria poupar.

Nao substitui o parser: o YAML ja foi carregado por `yaml.safe_load`. Isto
so reencontra, no texto bruto, a linha de uma chave que sabidamente existe.
"""
import re
from pathlib import Path

RX_CHAVE = re.compile(r"^(\s*)(?:-\s+)?([^\s#:][^:]*?)\s*:")


def _chaves(texto: str):
    for i, linha in enumerate(texto.splitlines(), 1):
        if not linha.strip() or linha.lstrip().startswith("#"):
            continue
        m = RX_CHAVE.match(linha)
        if m:
            yield i, len(m.group(1)), m.group(2).strip().strip("'\"")


def localizar(texto: str, caminho) -> int | None:
    """Linha da ultima chave de `caminho` (ex.: [tables, users, fields, cpf]).

    Casa por profundidade crescente de indentacao, que e o suficiente para
    catalogos escritos a mao e nao depende de round-trip do parser.
    """
    if not texto or not caminho:
        return None
    alvo = list(caminho)
    idx = 0
    indent_pai = -1
    achado = None
    for linha, indent, chave in _chaves(texto):
        if idx >= len(alvo):
            break
        if chave == alvo[idx] and indent > indent_pai:
            achado = linha
            indent_pai = indent
            idx += 1
    return achado if idx == len(alvo) else None


def localizar_em(arquivo, caminho) -> int | None:
    p = Path(arquivo)
    if not p.exists():
        return None
    try:
        return localizar(p.read_text(encoding="utf-8"), caminho)
    except OSError:
        return None


RX_PAR = re.compile(r"^\s*(?:-\s+)?([^\s#:][^:]*?)\s*:\s*(.+?)\s*(?:#.*)?$")


def localizar_valor(texto: str, chave: str, valor: str) -> int | None:
    """Linha de um par `chave: valor` — para entradas de lista, onde o
    caminho por indentacao nao identifica o item (ex.: `- name: stripe`)."""
    if not texto:
        return None
    for i, linha in enumerate(texto.splitlines(), 1):
        m = RX_PAR.match(linha)
        if m and m.group(1).strip() == chave:
            if m.group(2).strip().strip("'\"") == str(valor):
                return i
    return None


def localizar_valor_em(arquivo, chave: str, valor: str) -> int | None:
    p = Path(arquivo)
    if not p.exists():
        return None
    try:
        return localizar_valor(p.read_text(encoding="utf-8"), chave, valor)
    except OSError:
        return None
