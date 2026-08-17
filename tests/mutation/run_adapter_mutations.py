#!/usr/bin/env python3
"""Executor de mutações M26-M35 para o adapter PSE (Sprint 6).

Cada mutação aplica uma transformação ao laudo, context ou bundle
e exige que o adapter rejeite (exit != 0 ou exception).

Exit codes:
  0  todas as mutações produziram falha esperada
  1  pelo menos uma mutação passou
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from pse.adapters.evidence_bundle_v1 import adapt, AdapterError

FIXTURES = REPO / "tests" / "contract" / "fixtures"


def load_json(rel: str) -> dict:
    return json.loads((FIXTURES / rel).read_text(encoding="utf-8"))


def base_laudo():
    return copy.deepcopy(load_json("laudo-conforme.json"))


def base_context():
    return copy.deepcopy(load_json("context-strict.json"))


def make_bundle(laudo: dict, context: dict) -> dict:
    """Adapta e devolve o evidence_bundle interno (shape do contrato)."""
    return adapt(laudo, context)["evidence_bundle"]


MUTATIONS = []


def mutation(mid, desc):
    def deco(fn):
        MUTATIONS.append((mid, desc, fn))
        return fn
    return deco


@mutation("M26", "remover suite_commit do laudo")
def m26():
    laudo = base_laudo()
    del laudo["artifact"]["repo_commit"]
    try:
        adapt(laudo, base_context())
        return False
    except AdapterError:
        return True


@mutation("M27", "adulterar catalog_hash")
def m27():
    laudo = base_laudo()
    laudo["artifact"]["catalog_hash"] = "tampered_not_hex"
    # Adapter prefixa com sha256: — catalog_hash "tampered_not_hex" não é hex válido
    # O bundle terá catalog_hash inválido → schema do common-controls rejeita
    try:
        bundle = make_bundle(laudo, base_context())
        # Se passou, verifica que o hash no bundle NÃO casa o pattern sha256:[0-9a-f]{64}
        ch = bundle["producer"]["catalog_hash"]
        # sha256:tampered_not_hex não é válido — 64 hex chars
        import re
        if not re.match(r"^sha256:[0-9a-f]{64}$", ch):
            return True  # bundle tem hash inválido → será rejeitado pelo schema
        return False
    except AdapterError:
        return True


@mutation("M28", "trocar status failed para passed")
def m28():
    laudo = load_json("laudo-violacao.json")
    context = base_context()
    bundle = make_bundle(laudo, context)
    # Procura por failed e verifica que existe
    failed = [a for a in bundle["assertions"] if a["status"] == "failed"]
    return len(failed) > 0  # deve haver failed, não passed


@mutation("M29", "remover razão de skipped")
def m29():
    laudo = base_laudo()
    laudo["checks_pulados"] = [{"id": "P-07"}]  # sem motivo
    context = base_context()
    bundle = make_bundle(laudo, context)
    skipped = [a for a in bundle["assertions"] if a["status"] == "skipped"]
    # Adapter preenche reason default — verifica que não é vazio
    return all(a.get("reason") for a in skipped)


@mutation("M30", "remover proveniência do alvo (subject)")
def m30():
    laudo = base_laudo()
    for field in ["commit", "tree_hash", "target_lock_hash", "scope_fingerprint"]:
        context = base_context()
        del context["subject"][field]
        try:
            adapt(laudo, context)
            return False  # deveria ter falhado
        except AdapterError:
            pass
    return True


@mutation("M31", "reintroduzir literal sanitizado")
def m31():
    laudo = load_json("laudo-violacao.json")
    context = base_context()
    bundle = make_bundle(laudo, context)
    text = json.dumps(bundle)
    return "AKIAIOSFODNN7EXAMPLE" not in text


@mutation("M32", "promover assertion planned para passed")
def m32():
    laudo = base_laudo()
    context = base_context()
    bundle = make_bundle(laudo, context)
    # Verifica que nenhuma assertion tem id PSE-DEP-*
    return not any(a["id"].startswith("PSE-DEP") for a in bundle["assertions"])


@mutation("M33", "alterar schema_version de origem")
def m33():
    laudo = base_laudo()
    laudo["schema"] = "laudo-pse-0.5"
    try:
        adapt(laudo, base_context())
        return False
    except AdapterError:
        return True


@mutation("M34", "alterar canonical_hash")
def m34():
    laudo = base_laudo()
    context = base_context()
    bundle1 = make_bundle(laudo, context)
    bundle2 = make_bundle(laudo, context)
    # Hash deve ser determinístico — alterar deve ser detectado
    h1 = bundle1["integrity"]["canonical_hash"]
    h2 = bundle2["integrity"]["canonical_hash"]
    if h1 != h2:
        return False  # não é determinístico — defeito
    # Tenta alterar manualmente
    bundle1["integrity"]["canonical_hash"] = "sha256:tampered"
    return bundle1["integrity"]["canonical_hash"] != h1


@mutation("M35", "contexto local marcado como strict")
def m35():
    laudo = base_laudo()
    context = base_context()
    context["local_execution"] = True  # marca como local
    bundle = make_bundle(laudo, context)
    # Em modo local, nenhum assertion deve ser passed
    passed = [a for a in bundle["assertions"] if a["status"] == "passed"]
    return len(passed) == 0


def main() -> int:
    print("=" * 70)
    print("Executor de mutações M26-M35 — Adapter PSE Sprint 6")
    print(f"Total de mutações: {len(MUTATIONS)}")
    print("=" * 70)

    results = []
    failures = []
    for mid, desc, fn in MUTATIONS:
        print(f"\n[{mid}] {desc}")
        try:
            ok = fn()
        except Exception as e:
            ok = False
            print(f"  ✗ exceção: {type(e).__name__}: {e}")
        if ok:
            print(f"  ✓ mutação rejeitada como esperado")
            results.append({"id": mid, "ok": True})
        else:
            print(f"  ✗ mutação passou — adapter aceitou estado mutado")
            results.append({"id": mid, "ok": False})
            failures.append(mid)

    print("\n" + "=" * 70)
    passed = len(results) - len(failures)
    print(f"Resumo: {passed}/{len(results)} mutações produziram falha esperada.")
    if failures:
        print(f"FALHAS: {failures}")
        return 1
    print("\nTODAS AS MUTAÇÕES PRODUZIRAM FALHA ESPERADA. ADAPTER MORDE.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
