"""Gap 5 — a versao tem UMA fonte, e ninguem a restata em silencio.

`0.1.0` no pyproject e `0.1.0-dev` no laudo ja divergiram na pratica: a
suite mentia sobre a propria procedencia sem erro e sem aviso. A fonte e
o pyproject; o laudo le dos metadados do pacote instalado, que o build
deriva dali. Este modulo torna a deriva impossivel de passar despercebida.
"""
import re
import tomllib
from pathlib import Path

import pytest

from pse import fingerprint
from pse.evidence import versao_suite

RAIZ = Path(__file__).resolve().parent.parent
RX_VERSAO = re.compile(r"pse[-_]suite\s*==\s*(\d+\.\d+\.\d+)|v(\d+\.\d+\.\d+)")


@pytest.fixture(scope="module")
def versao_pyproject():
    dados = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))
    return dados["project"]["version"]


def test_laudo_reporta_a_versao_do_pyproject(versao_pyproject):
    """Se falhar com o pyproject recem-alterado, o ambiente esta dessincronizado:
    `pip install -e .`. Um laudo nao pode declarar versao que o pacote nao tem."""
    assert versao_suite() == versao_pyproject


def test_versao_nao_e_restatada_no_codigo():
    """Numero de versao hardcoded em .py e deriva esperando acontecer."""
    ofensores = []
    for p in (RAIZ / "pse").rglob("*.py"):
        for i, linha in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if "version" in linha.lower() and re.search(r"[\"']\d+\.\d+\.\d+", linha):
                ofensores.append(f"{p.relative_to(RAIZ)}:{i}")
    assert not ofensores, f"versao restatada no codigo: {ofensores}"


@pytest.mark.parametrize("doc", ["README.md", "docs/COMO-ADOTAR.md"])
def test_docs_nao_derivam_da_versao(versao_pyproject, doc):
    """A documentacao pode citar a versao — mas nao pode citar OUTRA."""
    texto = (RAIZ / doc).read_text(encoding="utf-8")
    citadas = {m.group(1) or m.group(2) for m in RX_VERSAO.finditer(texto)}
    divergentes = citadas - {versao_pyproject}
    assert not divergentes, (
        f"{doc} cita versao(oes) {sorted(divergentes)} enquanto o pyproject "
        f"declara {versao_pyproject} — atualize no mesmo PR."
    )


def test_catalog_hash_e_estavel_e_sensivel():
    """O hash tem de ser determinista entre chamadas e mudar com a regua."""
    assert fingerprint.catalog_hash() == fingerprint.catalog_hash()
    assert len(fingerprint.catalog_hash()) == 64

    alvo = RAIZ / "pse" / "data" / "pii-patterns.yaml"
    original = alvo.read_bytes()
    antes = fingerprint.catalog_hash()
    try:
        alvo.write_bytes(original.replace(b"cpf, ", b""))
        assert fingerprint.catalog_hash() != antes, (
            "editar a regua nao mudou o catalog_hash — a adulteracao ficaria "
            "invisivel no laudo"
        )
    finally:
        alvo.write_bytes(original)
    assert fingerprint.catalog_hash() == antes
