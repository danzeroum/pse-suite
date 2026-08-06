"""Catalogo dos checks — a declaracao autoritativa (D-12).

O registro por decorator so sabe o que foi *importado*. Sem uma declaracao
externa, o laudo nao consegue distinguir "este check nao se aplica" de
"este check ainda nao existe", e a metrica de cobertura do plano §8 nao e
calculavel. O catalogo torna "previsto e ausente" dizivel.

E a fonte unica de `titulo`, `base_legal`, `modo` e `status` — o decorator
apenas amarra o ID a funcao (fecha D-14: base legal declarada em um lugar so).
"""
from pathlib import Path

import yaml

_ARQUIVO = Path(__file__).resolve().parent / "data" / "checks-catalog.yaml"

IMPLEMENTADO = "implementado"

# A segunda dimensao da matriz. Ortogonal ao pilar de proposito: o pilar diz
# QUE VALOR esta em jogo, o dominio diz ONDE ele se manifesta no sistema.
DOMINIOS = ("frontend", "api", "backend", "data", "ai")

# O prefixo do ID codifica o PILAR, sempre e apenas. E a unica dimensao
# univalorada das duas: um check pertence a um pilar e pode pertencer a
# varios dominios. O lugar rigido (prefixo) tem de carregar o que tambem e
# rigido; o multivalorado vive em `domain`, que e lista.
#
# Esta regra mora AQUI e em nenhum outro lugar. Cada check nao a repete: o
# registro a consulta no momento em que o check se declara.
PREFIXO_DO_PILAR = {"privacy": "P", "security": "S", "ethics": "E"}
PILAR_DO_PREFIXO = {v: k for k, v in PREFIXO_DO_PILAR.items()}


def _carregar() -> dict:
    dados = yaml.safe_load(_ARQUIVO.read_text(encoding="utf-8")) or {}
    return dados.get("checks", {})


CATALOGO: dict = _carregar()


def meta(check_id: str) -> dict:
    return CATALOGO.get(check_id, {})


def existe(check_id: str) -> bool:
    return check_id in CATALOGO


def base_legal(check_id: str):
    return meta(check_id).get("base_legal")


def prefixo(check_id: str) -> str:
    return str(check_id).split("-")[0]


def pilar_esperado(check_id: str):
    """Pilar que o prefixo declara — ou None se o prefixo nao e do vocabulario."""
    return PILAR_DO_PREFIXO.get(prefixo(check_id))


def incoerencias_de_prefixo() -> list:
    """(check, prefixo, pack) para todo ID cujo prefixo nao case com o pilar.

    Prefixo fora de P/S/E entra aqui tambem: e como `FE-*` seria barrado se
    alguem tentar codificar dominio no prefixo de novo.
    """
    saida = []
    for cid, m in sorted(CATALOGO.items()):
        esperado = pilar_esperado(cid)
        if esperado is None or esperado != m.get("pack"):
            saida.append((cid, prefixo(cid), m.get("pack")))
    return saida


def dominios(check_id: str) -> list:
    d = meta(check_id).get("domain") or []
    return [d] if isinstance(d, str) else list(d)


def _casa_dominio(check_id: str, filtro) -> bool:
    """Sem filtro, tudo passa. Com filtro, basta um dominio em comum."""
    if not filtro:
        return True
    return bool(set(dominios(check_id)) & set(filtro))


def guardas_de(pack: str) -> list:
    return sorted(cid for cid, m in CATALOGO.items()
                  if m.get("pack") == pack and m.get("guarda_de_pack"))


def implementados(packs=None, doms=None) -> list:
    return sorted(cid for cid, m in CATALOGO.items()
                  if m.get("status") == IMPLEMENTADO
                  and (packs is None or m.get("pack") in packs)
                  and _casa_dominio(cid, doms))


def por_dominio(packs=None) -> dict:
    """Quantos checks implementados cada estrato tem — para o laudo."""
    saida = {}
    for d in DOMINIOS:
        saida[d] = len(implementados(packs, [d]))
    return saida


def previstos(packs=None, doms=None) -> list:
    """Checks declarados no plano que ainda nao existem nesta versao.

    Vao para o laudo com o motivo: previsto e ausente nunca e silencio.
    """
    saida = []
    for cid, m in sorted(CATALOGO.items()):
        if m.get("status") == IMPLEMENTADO:
            continue
        if packs is not None and m.get("pack") not in packs:
            continue
        if not _casa_dominio(cid, doms):
            continue
        saida.append({
            "id": cid,
            "pack": m.get("pack"),
            "domain": dominios(cid),
            "titulo": m.get("titulo"),
            "status": m.get("status"),
            "modo": m.get("modo"),
            "motivo": f"declarado no catalogo da suite como {m.get('status')} "
                      f"— nao implementado nesta versao do pacote",
        })
    return saida
