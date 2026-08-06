"""Montagem do laudo com procedencia (schema laudo-pse-1.0).

Tres responsabilidades, todas de choke point unico:
  - **procedencia completa** (Gap 3): a quintupla, com `catalog_hash`;
  - **sanitizacao** (D-02): nenhum finding e serializado sem passar pela regua;
  - **veredito** (Gaps 2/5 + D-15): tres estados, indeterminacao bloqueando.

Nada aqui inventa dado. Se a versao da suite nao resolve, o laudo nao sai:
`0.1.0-dev` era uma string fabricada que fazia o laudo mentir sobre a
propria procedencia, sem erro e sem aviso.
"""
import subprocess
import time
from pathlib import Path

from pse import catalogo, fingerprint
from pse.model import (EXIT_CONFORME, EXIT_INDETERMINADO, EXIT_VIOLACAO_ALTA,
                       EXIT_VIOLACAO_CRITICA, Severidade, Veredito,
                       VersaoIrresolvivel)
from pse.sanitize import sanitizar_finding


def _metadata_version(nome: str) -> str:
    from importlib.metadata import version
    return version(nome)


def versao_suite() -> str:
    """A versao vem de UMA fonte: os metadados do pacote instalado, que o
    build deriva do pyproject. Irresolvivel = ambiente quebrado -> exit 30."""
    try:
        return _metadata_version("pse-suite")
    except Exception as e:
        raise VersaoIrresolvivel(
            "versao da pse-suite irresolvivel: o pacote nao esta instalado no "
            "ambiente. Um laudo nao pode declarar procedencia que nao consegue "
            "provar — instale com `pip install -e .` ou pine a versao publicada."
        ) from e


def _commit(repo: Path):
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                             capture_output=True, text=True, timeout=5)
        return out.stdout.strip() or None
    except Exception:
        return None


def veredito(por_severidade: dict, indeterminados: list):
    """Precedencia ratificada: 10 > 20 > 11 > 0 (o 30 nasce antes do laudo).

    Violacao provada supera duvida no codigo de saida; ambas bloqueiam.
    """
    if por_severidade.get(Severidade.CRITICO.value):
        return Veredito.VIOLACAO, EXIT_VIOLACAO_CRITICA
    if indeterminados:
        return Veredito.INDETERMINADO, EXIT_INDETERMINADO
    if por_severidade.get(Severidade.ALTO.value):
        return Veredito.VIOLACAO, EXIT_VIOLACAO_ALTA
    return Veredito.CONFORME, EXIT_CONFORME


def montar_laudo(repo_path, resultados: dict, packs: set,
                 config_path=None) -> dict:
    repo = Path(repo_path)

    por_sev: dict = {}
    for f in resultados["findings"]:
        por_sev[f.severidade.value] = por_sev.get(f.severidade.value, 0) + 1

    indeterminados = resultados.get("checks_indeterminados", [])
    vered, codigo = veredito(por_sev, indeterminados)

    return {
        "schema": "laudo-pse-1.0",
        "artifact": {
            "suite": "pse-suite",
            "suite_version": versao_suite(),
            "schema_version": fingerprint.SCHEMA_VERSION,
            "catalog_hash": fingerprint.catalog_hash(),
            "repo_commit": _commit(repo),
            "config_fingerprint": fingerprint.fingerprint_config(config_path),
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        "veredito": vered.value,
        "exit_code": codigo,
        "packs": sorted(packs),
        "packs_desabilitados": resultados.get("packs_desabilitados", []),
        "resumo": {
            "total_findings": len(resultados["findings"]),
            "por_severidade": por_sev,
        },
        "cobertura": {
            "catalogo_total": len(catalogo.CATALOGO),
            "implementados_nos_packs": len(catalogo.implementados(packs)),
            "executados": len(resultados["checks_executados"]),
        },
        "checks_executados": resultados["checks_executados"],
        "checks_pulados": resultados["checks_pulados"],
        "checks_indeterminados": indeterminados,
        # Previsto e ausente: declarado no catalogo, ainda nao implementado.
        # Nunca silencio — e o que fara um check runtime sem alvo declarado
        # aparecer no laudo com motivo, na Fase 2.
        "checks_previstos": resultados.get("checks_previstos", []),
        "packs_fora_de_escopo": resultados.get("packs_fora_de_escopo", []),
        # Estado, nao defeito: o consumidor precisa saber o quanto ja esta
        # certo, nao so o que esta errado.
        "relatorios": resultados.get("relatorios", {}),
        # Choke point da sanitizacao: nenhum caminho serializa um finding
        # sem passar por aqui.
        "findings": [sanitizar_finding(f.to_dict()) for f in resultados["findings"]],
        "duracao_s": resultados["duracao_s"],
    }
