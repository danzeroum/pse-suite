"""Validacao do laudo contra o schema versionado (D-05).

Os schemas existiam mas nao iam no wheel e nada os validava: o consumidor
que pinava o pacote recebia a evidencia e nao tinha como conferi-la, e o
`$ref` entre laudo e finding nao resolvia. Agora viajam dentro do pacote e
o proprio CLI valida antes de gravar — um laudo fora do schema e defeito da
suite, e defeito da suite nao pode sair como evidencia valida.
"""
import json
from functools import lru_cache
from pathlib import Path

_DIR = Path(__file__).resolve().parent / "schemas"


class LaudoInvalido(Exception):
    """O laudo produzido nao satisfaz laudo-pse-1.0 — defeito da suite."""


@lru_cache(maxsize=None)
def carregar(nome: str) -> dict:
    return json.loads((_DIR / nome).read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def _validador():
    """Registry local para o `$ref` resolver sem tocar a rede.

    Um validador que busca schema por HTTP seria uma dependencia de rede
    dentro do Trabalho B, que e declaradamente offline.
    """
    from jsonschema import Draft7Validator
    from referencing import Registry, Resource

    laudo = carregar("laudo-pse-1.0.json")
    finding = carregar("finding-1.0.json")
    registry = Registry().with_resources([
        (finding["$id"], Resource.from_contents(finding)),
        (laudo["$id"], Resource.from_contents(laudo)),
    ])
    return Draft7Validator(laudo, registry=registry)


@lru_cache(maxsize=None)
def _validador_de(nome: str):
    from jsonschema import Draft7Validator
    return Draft7Validator(carregar(nome))


def erros_de(nome: str, dado):
    """Erros de um documento do consumidor contra um schema da suite.

    Devolve os erros em vez de levantar: o check decide a severidade e
    transforma cada um num Finding com arquivo:linha.
    """
    return sorted(_validador_de(nome).iter_errors(dado),
                  key=lambda e: list(e.path))


def validar_laudo(laudo: dict) -> None:
    erros = sorted(_validador().iter_errors(laudo), key=lambda e: list(e.path))
    if erros:
        detalhe = "; ".join(
            f"{'/'.join(map(str, e.path)) or '<raiz>'}: {e.message}"
            for e in erros[:5])
        raise LaudoInvalido(
            f"laudo fora do schema laudo-pse-1.0 ({len(erros)} erro(s)): {detalhe}")
