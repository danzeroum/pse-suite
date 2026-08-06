"""Montagem do laudo com procedencia (schema laudo-pse-1.0)."""
import hashlib
import subprocess
import time
from pathlib import Path


def _versao_suite() -> str:
    try:
        from importlib.metadata import version
        return version("pse-suite")
    except Exception:
        return "0.1.0-dev"


def _commit(repo: Path):
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                             capture_output=True, text=True, timeout=5)
        return out.stdout.strip() or None
    except Exception:
        return None


def montar_laudo(repo_path, resultados: dict, packs: set,
                 config_path=None) -> dict:
    repo = Path(repo_path)
    fingerprint = None
    if config_path and Path(config_path).exists():
        fingerprint = hashlib.sha256(Path(config_path).read_bytes()).hexdigest()

    por_sev: dict = {}
    for f in resultados["findings"]:
        por_sev[f.severidade.value] = por_sev.get(f.severidade.value, 0) + 1

    return {
        "schema": "laudo-pse-1.0",
        "artifact": {
            "suite": "pse-suite",
            "suite_version": _versao_suite(),
            "repo_commit": _commit(repo),
            "config_fingerprint": fingerprint,
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        "packs": sorted(packs),
        "resumo": {
            "total_findings": len(resultados["findings"]),
            "por_severidade": por_sev,
        },
        "checks_executados": resultados["checks_executados"],
        "checks_pulados": resultados["checks_pulados"],
        "findings": [f.to_dict() for f in resultados["findings"]],
        "duracao_s": resultados["duracao_s"],
    }
