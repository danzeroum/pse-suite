"""Trabalho B contra fixture com violacoes + mordida do gate fail-closed."""
import json
from pathlib import Path

import pytest

from pse.cli import main
from pse.engine.runner import executar

FIX = Path(__file__).parent / "fixtures" / "consumidor_ruim"
CFG = {"catalog_path": "catalog.yaml"}


def ids(res):
    return {f.check_id for f in res["findings"]}


@pytest.mark.pse_privacy
def test_pack_privacy_encontra_violacoes():
    res = executar(FIX, {"privacy"}, CFG)
    assert {"P-01", "P-02", "P-03", "P-04", "P-06", "P-08"} <= ids(res)
    p08 = [f for f in res["findings"] if f.check_id == "P-08"]
    assert p08[0].severidade.value == "CRITICO"  # Art. 11 e trava estrutural


@pytest.mark.pse_privacy
def test_check_pulado_nunca_e_silencioso():
    res = executar(FIX.parent, {"privacy"}, {})  # dir sem catalogo
    pulados = {c["id"] for c in res["checks_pulados"]}
    assert "P-02" in pulados and "P-08" in pulados
    assert all(c["motivo"] for c in res["checks_pulados"])


@pytest.mark.pse_security
def test_pack_security_encontra_violacoes():
    res = executar(FIX, {"security"}, CFG)
    assert {"S-04", "S-06"} <= ids(res)
    hosts = [f for f in res["findings"] if f.check_id == "S-04"]
    assert any("analytics.google.com" in f.titulo for f in hosts)


@pytest.mark.pse_ethics
def test_pack_ethics_encontra_violacoes():
    res = executar(FIX, {"ethics"}, CFG)
    assert {"E-04", "E-05", "E-07"} <= ids(res)


@pytest.mark.mordida
def test_mordida_critico_aborta(tmp_path):
    """A trava morde: CRITICO -> exit 1, laudo com procedencia gravado."""
    out = tmp_path / "laudo.json"
    rc = main(["--path", str(FIX), "--config", str(FIX / "pse-config.yaml"),
               "--output", str(out)])
    assert rc == 1
    laudo = json.loads(out.read_text())
    assert laudo["schema"] == "laudo-pse-1.0"
    assert laudo["resumo"]["por_severidade"]["CRITICO"] >= 3  # P-06, P-08, S-06, E-04
    assert laudo["artifact"]["suite_version"]
    assert laudo["artifact"]["config_fingerprint"]


@pytest.mark.mordida
def test_repo_sem_critico_nao_aborta(tmp_path):
    (tmp_path / "app.py").write_text("def ok():\n    return 1\n")
    assert main(["--path", str(tmp_path)]) == 0
