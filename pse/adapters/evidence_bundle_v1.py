"""Adapter: laudo-pse-1.0 → evidence-bundle/v1 draft.

Converte um laudo PSE no formato de evidence-bundle/v1 draft definido em
common-controls/schemas/evidence-bundle-v1-draft.schema.json.

O adapter:
  1. Lê um laudo-pse-1.0 (JSON)
  2. Lê um assurance-context (JSON) com subject (commit, tree_hash, etc.)
  3. Produz um evidence-bundle/v1 draft (JSON)

Regras:
  - Preserva proveniência (suite_id, version, commit, source_schema, catalog_hash)
  - Mapeia checks_executados → assertions[status=passed]
  - Mapeia findings → assertions[status=failed] com details
  - Mapeia checks_pulados → assertions[status=skipped] com reason
  - Mapeia checks_indeterminados → assertions[status=errored] com reason
  - Mapeia checks_nao_habilitados → assertions[status=not_assessed] com reason
  - NÃO inventa PSE-DEP-* — nunca emite assertion com id PSE-DEP-*
  - Sanitiza: não copia literals brutos de findings
  - Exige context com subject (commit, tree_hash, target_lock_hash, scope_fingerprint)
  - Emite o documento no shape do contrato: {"evidence_bundle": {...}}

Exit codes:
  0  bundle gerado com sucesso
  1  laudo ou contexto inválido (não produz bundle)
  2  erro de execução
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pse import catalogo, fingerprint
from pse.model import Severidade
from pse.sanitize import sanitizar, sanitizar_finding

# Capabilities mapeadas por check ID (do catálogo da PSE v0.3.0)
# FIXME: isto deveria vir do catálogo, mas para o adapter piloto é hardcoded
CHECK_CAPABILITIES = {
    "P-01": "privacy.log-pii-masking",
    "P-02": "privacy.retention-purge-job",
    "P-03": "privacy.soft-delete-elimination",
    "P-04": "privacy.data-catalog-liveness",
    "P-05": "privacy.dto-minimization",
    "P-06": "privacy.pseudonymization-key-segregation",
    "P-07": "privacy.consent-granularity",
    "P-08": "privacy.sensitive-legal-basis",
    "P-09": "privacy.k-anonymity",
    "P-10": "privacy.portability-endpoint",
    "P-11": "privacy.oracle-resource",
    "S-01": "security.bola-idor",
    "S-02": "security.rate-limit",
    "S-03": "security.pii-in-error",
    "S-04": "security.third-party-dpa",
    "S-05": "security.egress-payload",
    "S-06": "security.hardcoded-credential",
    "S-07": "security.purpose-audit-log",
    "S-08": "security.international-transfer",
    "E-00": "ethics.automated-decision-scope",
    "E-01": "ethics.decision-explanation",
    "E-02": "ethics.decision-log",
    "E-03": "ethics.contestation-endpoint",
    "E-04": "ethics.human-in-the-loop",
    "E-05": "ethics.discrimination-proxy",
    "E-06": "ethics.fairness-disparity",
    "E-07": "ethics.model-card",
    "E-08": "ethics.lineage-traceability",
    "E-09": "ethics.kill-switch",
    "E-10": "ethics.uncertainty-quantification",
}

# Assertions planejadas mas NÃO emitidas pela PSE v0.3.0
FUTURE_ASSERTIONS = [
    {
        "id": "PSE-DEP-INVENTORY-MATCH",
        "capability": "security.dependency-inventory",
        "reason": "A release da PSE não emite assertion normalizada para inventário de dependências.",
    },
    {
        "id": "PSE-DEP-VULNERABILITY-SCAN",
        "capability": "security.dependency-vulnerability-scan",
        "reason": "A release da PSE não emite assertion normalizada para varredura de vulnerabilidades.",
    },
]

# severidade do finding-1.0 (laudo-pse-1.0) → enum do contrato draft.
# INFO não tem equivalente no contrato; a severidade é omitida nesse caso
# (details.severity é opcional no schema evidence-bundle-v1-draft).
SEVERITY_MAP = {
    "CRITICO": "critical",
    "ALTO": "high",
    "MEDIO": "medium",
    "BAIXO": "low",
}


class AdapterError(Exception):
    """Erro que impede o adapter de produzir um bundle válido."""


def _sha256_dict(d: dict) -> str:
    """Hash canônico de um dict (JSON sorted keys)."""
    canonical = json.dumps(d, sort_keys=True, ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _evidence_fingerprint(check_id: str, laudo: dict) -> str:
    """Hash da evidência do check = hash do check_id + contexto do laudo."""
    artifact = laudo.get("artifact", {})
    parts = [
        check_id,
        artifact.get("suite_version", ""),
        artifact.get("catalog_hash", ""),
        artifact.get("repo_commit", ""),
    ]
    h = hashlib.sha256("|".join(parts).encode("utf-8"))
    return "sha256:" + h.hexdigest()


def _map_mode(modo: str) -> str:
    """Mapeia modo PSE para execution_mode do bundle."""
    mapping = {
        "pse_inventory": "inventory",
        "pse_passive": "passive",
        "pse_active": "active_discovery",
    }
    return mapping.get(modo, "inventory")


def _map_runner_kind(modo: str, local: bool) -> str:
    """Infere runner_kind do modo e local_execution."""
    if local:
        return "agent"
    if modo in ("pse_passive", "pse_active"):
        return "ci"
    return "ci"


def adapt(laudo: dict, context: dict) -> dict:
    """Converte laudo-pse-1.0 em evidence-bundle/v1 draft.

    Args:
        laudo: documento JSON no formato laudo-pse-1.0
        context: documento JSON com subject (commit, tree_hash, etc.)

    Returns:
        dict no formato evidence-bundle/v1 draft

    Raises:
        AdapterError: se laudo ou contexto são inválidos
    """
    if not isinstance(laudo, dict) or laudo.get("schema") != "laudo-pse-1.0":
        raise AdapterError(
            "laudo inválido: schema deve ser 'laudo-pse-1.0'")

    artifact = laudo.get("artifact", {})
    if not artifact:
        raise AdapterError("laudo sem bloco artifact")

    # Validar proveniência essencial do laudo
    suite_commit = artifact.get("repo_commit")
    if not suite_commit:
        raise AdapterError("laudo sem artifact.repo_commit — proveniência da suíte ausente")

    catalog_hash_raw = artifact.get("catalog_hash")
    if not catalog_hash_raw or not isinstance(catalog_hash_raw, str):
        raise AdapterError("laudo sem artifact.catalog_hash — catálogo da suíte ausente")

    # Validar contexto
    subject = context.get("subject", {})
    required_subject = ["repository", "commit", "tree_hash",
                        "target_lock_hash", "scope_fingerprint"]
    missing = [f for f in required_subject if not subject.get(f)]
    if missing:
        raise AdapterError(
            f"contexto sem campos obrigatórios em subject: {missing}")

    local_execution = context.get("local_execution", False)
    modo = artifact.get("modo", "pse_inventory")

    # Construir producer
    producer = {
        "suite_id": "pse-suite",
        "suite_version": artifact.get("suite_version", ""),
        "suite_commit": artifact.get("repo_commit") or "0" * 40,
        "source_schema": artifact.get("schema_version", "laudo-pse-1.0"),
        "catalog_hash": "sha256:" + artifact.get("catalog_hash", ""),
        "local_execution": local_execution,
        "execution_mode": _map_mode(modo),
        "runner_kind": _map_runner_kind(modo, local_execution),
        "network_used": modo in ("pse_passive", "pse_active"),
    }

    # Authorization (do laudo se existir)
    auth = artifact.get("autorizacao")
    if auth:
        producer["authorization"] = {
            "attested_by": auth.get("attested_by"),
            "scope": auth.get("scope", []),
            "expires": auth.get("expires"),
            "target_fingerprint": auth.get("target_fingerprint"),
            "synthetic_identities": auth.get("synthetic_identities"),
        }
    elif producer["network_used"]:
        raise AdapterError(
            "laudo usa rede (modo passive/active) mas não tem authorization")

    # Construir assertions
    assertions = []

    # checks_executados → passed (se sem finding) ou failed (se tem finding)
    findings_by_check = {}
    for f in laudo.get("findings", []):
        cid = f.get("check_id", "")
        if cid not in findings_by_check:
            findings_by_check[cid] = []
        findings_by_check[cid].append(f)

    for cid in laudo.get("checks_executados", []):
        cap = CHECK_CAPABILITIES.get(cid, "unknown.unknown")
        ev_fp = _evidence_fingerprint(cid, laudo)

        if cid in findings_by_check:
            # Check executado com finding → failed
            f = findings_by_check[cid][0]  # primeiro finding do check
            details: dict = {
                "summary": sanitizar(f.get("titulo", ""))[:200],
                "dimension": f.get("domain", [""])[0] if isinstance(f.get("domain"), list) else f.get("domain", ""),
            }
            severity = SEVERITY_MAP.get(str(f.get("severidade", "")).upper())
            if severity:
                details["severity"] = severity
            assertions.append({
                "id": cid,
                "status": "failed",
                "evidence_fingerprint": ev_fp,
                "capability": cap,
                "executed_at": artifact.get("timestamp_utc", ""),
                "reason": sanitizar(f.get("descricao", ""))[:200],
                "details": details,
            })
        else:
            # Check executado sem finding → passed
            assertions.append({
                "id": cid,
                "status": "passed",
                "evidence_fingerprint": ev_fp,
                "capability": cap,
                "executed_at": artifact.get("timestamp_utc", ""),
            })

    # checks_pulados → skipped com reason
    for item in laudo.get("checks_pulados", []):
        cid = item.get("id", "")
        cap = CHECK_CAPABILITIES.get(cid, "unknown.unknown")
        assertions.append({
            "id": cid,
            "status": "skipped",
            "evidence_fingerprint": _evidence_fingerprint(cid, laudo),
            "capability": cap,
            "executed_at": artifact.get("timestamp_utc", ""),
            "reason": item.get("motivo", "N/A declarado sem motivo"),
        })

    # checks_indeterminados → errored com reason
    for item in laudo.get("checks_indeterminados", []):
        cid = item.get("id", "")
        cap = CHECK_CAPABILITIES.get(cid, "unknown.unknown")
        assertions.append({
            "id": cid,
            "status": "errored",
            "evidence_fingerprint": _evidence_fingerprint(cid, laudo),
            "capability": cap,
            "executed_at": artifact.get("timestamp_utc", ""),
            "reason": item.get("motivo", "indeterminado sem motivo"),
        })

    # checks_nao_habilitados → not_assessed com reason
    for item in laudo.get("checks_nao_habilitados", []):
        cid = item.get("id", "")
        cap = CHECK_CAPABILITIES.get(cid, "unknown.unknown")
        assertions.append({
            "id": cid,
            "status": "not_assessed",
            "evidence_fingerprint": _evidence_fingerprint(cid, laudo),
            "capability": cap,
            "executed_at": artifact.get("timestamp_utc", ""),
            "reason": item.get("motivo", "não habilitado sem motivo"),
        })

    # Se não há assertions (laudo vazio), erro
    if not assertions:
        raise AdapterError(
            "laudo não produziu nenhuma assertion — bundle vazio não é evidência")

    # Se local_execution=true, nenhum assertion pode ter status verde
    # (contrato: status restrito a not_assessed/not_applicable).
    if local_execution:
        for a in assertions:
            if a["status"] not in ("not_assessed", "not_applicable"):
                original = a["status"]
                reason = f"evidência local não pode produzir {original}"
                if a.get("reason"):
                    reason = f"{reason}: {a['reason']}"
                a["status"] = "not_assessed"
                a["reason"] = reason

    # Construir bundle
    bundle = {
        "schema_version": "evidence-bundle/v1-draft",
        "producer": producer,
        "subject": subject,
        "assertions": assertions,
        "integrity": {},  # preenchido abaixo
    }

    # Hash canônico (excluindo o próprio integrity.canonical_hash)
    bundle["integrity"] = {
        "canonical_hash": _sha256_dict({k: v for k, v in bundle.items()
                                         if k != "integrity"})
    }

    # Shape do contrato: o documento é {"evidence_bundle": {...}}
    return {"evidence_bundle": bundle}


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description="Adapter: laudo-pse-1.0 → evidence-bundle/v1 draft")
    parser.add_argument("--input-laudo", required=True,
                        help="caminho do laudo JSON")
    parser.add_argument("--context", required=True,
                        help="caminho do assurance-context JSON")
    parser.add_argument("--output", required=True,
                        help="caminho de saída do bundle JSON")
    args = parser.parse_args(argv)

    try:
        laudo = json.loads(Path(args.input_laudo).read_text(encoding="utf-8"))
    except Exception as e:
        print(f"✗ não consegui ler laudo: {e}", file=sys.stderr)
        return 2

    try:
        context = json.loads(Path(args.context).read_text(encoding="utf-8"))
    except Exception as e:
        print(f"✗ não consegui ler context: {e}", file=sys.stderr)
        return 2

    try:
        bundle = adapt(laudo, context)
    except AdapterError as e:
        print(f"✗ adapter: {e}", file=sys.stderr)
        return 1

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(f"✓ bundle gerado: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
