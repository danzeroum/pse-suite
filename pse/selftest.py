"""`pse --self-test` — a prova de mordida executavel no consumidor (D-06).

A pergunta que este comando responde e "a trava desta versao instalada
ainda morde?", e ele a responde sem exigir o repositorio da suite: a
fixture viaja no wheel. Um consumidor que roda isto no CI descobre, no
proprio pipeline, se o gate parou de abortar.

Autoprova minima. A prova de mutacao completa (Gap 4 — todo check
bloqueante com inverso canonico) e o passo seguinte.
"""
from pathlib import Path

from pse.engine.runner import executar
from pse.model import Severidade

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "mordida"

# O que a fixture embarcada tem de produzir. Nao e "algum CRITICO": e
# ESTES, para que um check que pare de morder seja nomeado.
ESPERADOS = {"P-01", "P-06", "P-08", "E-04"}
CONFIG = {"catalog_path": "catalog.yaml", "decision_making": "automated"}


def autoprova() -> dict:
    """Audita a fixture embarcada e confere que a trava mordeu."""
    if not FIXTURE.exists():
        return {"ok": False, "motivo": f"fixture embarcada ausente: {FIXTURE}",
                "encontrados": [], "faltando": sorted(ESPERADOS)}

    res = executar(FIXTURE, {"privacy", "security", "ethics"}, CONFIG)
    criticos = {f.check_id for f in res["findings"]
                if f.severidade is Severidade.CRITICO}
    faltando = sorted(ESPERADOS - criticos)

    laudo_vaza = [f.check_id for f in res["findings"]
                  if f.snippet and "chave-falsa-plantada-1234" in f.snippet]

    ok = not faltando and not laudo_vaza
    motivo = "trava integra: a fixture embarcada produz os CRITICOs esperados"
    if faltando:
        motivo = (f"TRAVA QUEBRADA: check(s) {faltando} deixaram de produzir "
                  f"CRITICO na fixture embarcada")
    elif laudo_vaza:
        motivo = (f"SANITIZACAO QUEBRADA: {laudo_vaza} publicaram o segredo "
                  f"plantado em claro no finding")

    return {
        "ok": ok,
        "motivo": motivo,
        "encontrados": sorted(criticos),
        "faltando": faltando,
        "indeterminados": [c["id"] for c in res["checks_indeterminados"]],
    }
