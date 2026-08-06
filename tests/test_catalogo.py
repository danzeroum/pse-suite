"""D-12 (catalogo dos 29) + E-00 (guarda de escopo do pack de etica)."""
import json
from pathlib import Path

import pytest

from pse import catalogo
from pse.cli import main
from pse.engine.registry import CHECKS
from pse.engine.runner import _carregar_checks, executar

FIX = Path(__file__).parent / "fixtures"

# Os 29 do plano §3 + E-00, a guarda que o plano v1 chama de EBD-000.
PLANO = ([f"P-{i:02d}" for i in range(1, 12)] +
         [f"S-{i:02d}" for i in range(1, 9)] +
         [f"E-{i:02d}" for i in range(1, 11)])


def test_catalogo_cobre_os_29_do_plano():
    assert set(PLANO) <= set(catalogo.CATALOGO), (
        f"faltam no catalogo: {sorted(set(PLANO) - set(catalogo.CATALOGO))}")
    assert "E-00" in catalogo.CATALOGO
    assert len(catalogo.CATALOGO) == len(PLANO) + 1


def test_registro_e_catalogo_nao_derivam():
    """Todo check registrado esta catalogado, e todo catalogado como
    `implementado` esta registrado. Sem isso, catalogo e codigo mentem um
    sobre o outro em silencio (D-12/D-14)."""
    _carregar_checks()
    registrados = set(CHECKS)
    assert registrados <= set(catalogo.CATALOGO)
    assert registrados == set(catalogo.implementados()), (
        f"registro != catalogo. So no registro: "
        f"{sorted(registrados - set(catalogo.implementados()))}; "
        f"so no catalogo: {sorted(set(catalogo.implementados()) - registrados)}")


def test_base_legal_tem_fonte_unica():
    """D-14: a base legal vem do catalogo, nao de uma copia no decorator."""
    _carregar_checks()
    for cid, meta in CHECKS.items():
        assert meta["base_legal"] == catalogo.base_legal(cid)
        assert meta["base_legal"], f"{cid} sem base legal declarada"


def test_previsto_e_ausente_e_dizivel():
    """O laudo tinha de saber dizer 'previsto e ausente' — nao so
    'executado' ou 'pulado'. E pre-requisito da Fase 2."""
    previstos = {c["id"] for c in catalogo.previstos()}
    assert len(previstos) == 9
    # S-07 segue previsto-fase-2 por escopo: nao estava na lista de checks
    # pedidos para esta fase. Previsto e ausente, com motivo — nao silencio.
    assert {"S-07", "P-07", "P-09", "P-10", "S-05",
            "E-06", "E-08", "E-09", "E-10"} == previstos
    for c in catalogo.previstos():
        assert c["motivo"] and c["status"] and c["modo"]


def test_laudo_carrega_cobertura_e_previstos(tmp_path):
    out = tmp_path / "l.json"
    main(["--path", str(FIX / "consumidor_bom"),
          "--config", str(FIX / "consumidor_bom" / "pse-config.yaml"),
          "--output", str(out)])
    laudo = json.loads(out.read_text(encoding="utf-8"))
    assert laudo["cobertura"]["catalogo_total"] == 30
    assert laudo["cobertura"]["implementados_nos_packs"] == 21
    assert {c["id"] for c in laudo["checks_previstos"]}


# ------------------------------------------------------------------ E-00
@pytest.mark.pse_ethics
def test_pack_etica_fora_de_escopo_nao_fica_verde(tmp_path):
    """Alvo sem decisao automatizada: o pack inteiro sai N/A DECLARADO com
    motivo computado. N/A e conforme sao estados distintos."""
    (tmp_path / "app.py").write_text(
        "def somar(a, b):\n    return a + b\n")
    res = executar(tmp_path, {"ethics"}, {"decision_making": "none"})
    assert not res["findings"]
    pulados = {c["id"]: c["motivo"] for c in res["checks_pulados"]}
    assert {"E-00", "E-04", "E-05", "E-07"} <= set(pulados)
    assert all(pulados.values()), "pack fora de escopo sem motivo e verde silencioso"
    assert "fora de escopo" in pulados["E-04"]
    assert res["packs_fora_de_escopo"][0]["pack"] == "ethics"


@pytest.mark.pse_ethics
def test_divergencia_entre_codigo_e_declaracao_e_achado(tmp_path):
    """Codigo mostra modelo, consumidor declara `none` -> ACHADO.

    A divergencia e exatamente o que um auditor precisa ver.
    """
    (tmp_path / "ml.py").write_text(
        "from sklearn.linear_model import LogisticRegression\n"
        "modelo = LogisticRegression()\n")
    res = executar(tmp_path, {"ethics"}, {"decision_making": "none"})
    e00 = [f for f in res["findings"] if f.check_id == "E-00"]
    assert e00, "declaracao divergente do codigo passou em silencio"
    assert e00[0].arquivo == "ml.py" and e00[0].linha
    # divergiu -> o pack NAO sai de escopo; os demais checks rodam
    assert "E-07" in res["checks_executados"]


@pytest.mark.pse_ethics
def test_escopo_declarado_mantem_o_pack_ativo(tmp_path):
    (tmp_path / "app.py").write_text("def somar(a, b):\n    return a + b\n")
    res = executar(tmp_path, {"ethics"}, {"decision_making": "automated"})
    assert "E-00" in res["checks_executados"]
    assert "E-04" in res["checks_executados"]


@pytest.mark.pse_ethics
def test_declaracao_invalida_nao_vira_escopo(tmp_path):
    (tmp_path / "app.py").write_text("def somar(a, b):\n    return a + b\n")
    res = executar(tmp_path, {"ethics"}, {"decision_making": "talvez"})
    pulados = {c["id"]: c["motivo"] for c in res["checks_pulados"]}
    assert "E-00" in pulados and "invalido" in pulados["E-00"]
