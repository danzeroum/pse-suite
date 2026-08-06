"""D-12 (catalogo dos 29) + E-00 (guarda de escopo do pack de etica)."""
import json
from pathlib import Path

import pytest

from pse import catalogo
from pse.cli import main
from pse.engine.registry import CHECKS
from pse.engine.runner import _carregar_checks, executar

FIX = Path(__file__).parent / "fixtures"

# Os 29 do plano §3 + E-00 (guarda de escopo) + E-11/E-12/E-13 (IA e cadeia
# de terceiros) + FE-01/FE-02/FE-03 (dominio frontend). Os tres ultimos sao o
# primeiro estrato cujo ID codifica o DOMINIO, nao o pilar.
PLANO = ([f"P-{i:02d}" for i in range(1, 12)] +
         [f"S-{i:02d}" for i in range(1, 9)] +
         [f"E-{i:02d}" for i in range(1, 11)])


def test_catalogo_cobre_os_29_do_plano():
    assert set(PLANO) <= set(catalogo.CATALOGO), (
        f"faltam no catalogo: {sorted(set(PLANO) - set(catalogo.CATALOGO))}")
    assert {"E-00", "E-11", "E-12", "E-13"} <= set(catalogo.CATALOGO)
    assert {"FE-01", "FE-02", "FE-03"} <= set(catalogo.CATALOGO)
    assert len(catalogo.CATALOGO) == len(PLANO) + 7


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


def test_catalogo_nao_tem_mais_previstos():
    """33/33. O catalogo do plano esta inteiro implementado."""
    assert catalogo.previstos() == [], (
        f"previstos: {[c['id'] for c in catalogo.previstos()]}")


def test_previsto_e_ausente_continua_dizivel(monkeypatch):
    """O MECANISMO tem de sobreviver ao catalogo ficar completo.

    Hoje nao ha check previsto — mas o dia em que o plano crescer, o laudo
    precisa continuar sabendo dizer 'declarado e ainda nao implementado'.
    Sem este teste, a capacidade morreria em silencio no primeiro refactor,
    e so alguem descobriria ao adicionar o check 34.
    """
    futuro = {**catalogo.meta("E-08"), "status": "previsto-fase-3"}
    monkeypatch.setitem(catalogo.CATALOGO, "E-08", futuro)
    previstos = catalogo.previstos()
    assert {c["id"] for c in previstos} == {"E-08"}
    for c in previstos:
        assert c["motivo"] and c["status"] and c["modo"]
    assert "E-08" not in catalogo.implementados()


def test_laudo_carrega_cobertura(tmp_path):
    out = tmp_path / "l.json"
    main(["--path", str(FIX / "consumidor_bom"),
          "--config", str(FIX / "consumidor_bom" / "pse-config.yaml"),
          "--output", str(out)])
    laudo = json.loads(out.read_text(encoding="utf-8"))
    assert laudo["cobertura"]["catalogo_total"] == 36
    assert laudo["cobertura"]["implementados_nos_packs"] == 36
    # O campo continua no laudo mesmo vazio: some-lo quando nao ha previstos
    # faria o consumidor perder a diferenca entre "nenhum pendente" e
    # "esta versao nem sabe responder isso".
    assert laudo["checks_previstos"] == []


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
