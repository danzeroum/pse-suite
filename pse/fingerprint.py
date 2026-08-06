"""Procedencia: a quintupla que torna dois laudos comparaveis.

`(suite, version, commit, catalog_hash, schema_version)`.

O `catalog_hash` (Gap 3) e a outra metade do D-13. O teste-guarda de
`tests/test_regua.py` torna a edicao da regua *bloqueante no CI*; o hash
a torna *evidente na evidencia*: dois laudos que dizem `suite_version:
0.2.0` mas divergem no `catalog_hash` foram produzidos por reguas
diferentes, e isso fica visivel sem precisar confiar em ninguem.

Cobre os dois lados do que a suite mede com: os dados curados
(`pse/data/*.yaml`) e o codigo dos checks que os aplicam. Alterar
qualquer um dos dois muda o hash.
"""
import hashlib
from pathlib import Path

SCHEMA_VERSION = "laudo-pse-1.0"

_RAIZ = Path(__file__).resolve().parent


def _arquivos_da_regua():
    yield from sorted((_RAIZ / "data").glob("*.yaml"))
    yield from sorted((_RAIZ / "checks").rglob("*.py"))


def catalog_hash() -> str:
    """SHA-256 sobre a regua curada + o codigo dos checks.

    Determinista: caminhos relativos ordenados, conteudo em bytes, com o
    nome do arquivo entrando no digest para que renomear tambem conte.
    """
    h = hashlib.sha256()
    for p in _arquivos_da_regua():
        h.update(str(p.relative_to(_RAIZ)).encode("utf-8"))
        h.update(b"\0")
        h.update(p.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def fingerprint_config(config_path) -> str | None:
    if not config_path:
        return None
    p = Path(config_path)
    if not p.exists():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()
