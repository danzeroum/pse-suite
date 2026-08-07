"""E-08 — provenance/lineage: origem → transformação → destino rastreável.

O último check do catálogo. A pergunta que ele faz é a que ninguém consegue
responder depois de um incidente: *este dado veio de onde, passou por quê e
foi parar aonde?* Sem trilha, o Art. 18 vira exercício de arqueologia — não
dá para corrigir, eliminar ou portar o que ninguém sabe rastrear.

Dois cuidados herdados e testados aqui:
  D-01  menção não conta. Um README afirmando "temos rastreabilidade
        completa" é exatamente o tipo de evidência que este check recusa.
  D-08  sem falso-positivo em CRÍTICO. E-08 é ALTO: é gap de governança,
        não violação legal direta, e não entra no conjunto fail-closed.
"""
import json
from pathlib import Path

import pytest

from pse.cli import main
from pse.engine.runner import executar

FIX = Path(__file__).parent / "fixtures"
RUIM, BOM = FIX / "consumidor_ruim", FIX / "consumidor_bom"

CFG_RUIM = {"catalog_path": "catalog.yaml", "decision_making": "automated"}
CFG_BOM = {"catalog_path": "catalog.yaml", "decision_making": "automated",
           "lineage_path": "lineage.jsonl",
           "consent_model_path": "consent-model.yaml",
           "packs": {"ethics": {"fairness_dataset": "eval.csv",
                                "fairness_report": "fairness-report.yaml"}}}

CATALOGO_COM_PII = (
    "tables:\n  clientes:\n    fields:\n      cpf:\n        class: personal\n"
    "        owner: o\n        purpose: p\n        legal_basis: contrato\n"
    "        retention_years: 5\n")


def acha(res, cid="E-08"):
    return [f for f in res["findings"] if f.check_id == cid]


# ==================================================== o que o teste exige
@pytest.mark.pse_ethics
def test_tratamento_sem_trilha_e_achado():
    res = executar(RUIM, {"ethics"}, CFG_RUIM)
    e08 = acha(res)
    assert e08, "tratamento de dado pessoal sem lineage passou em silencio"
    assert e08[0].severidade.value == "ALTO"
    assert e08[0].arquivo and e08[0].linha, "achado global sem endereco"
    assert "rastreabilidade" in e08[0].base_legal.lower()


@pytest.mark.pse_ethics
def test_mencao_em_readme_nao_conta():
    """consumidor_ruim tem um README afirmando rastreabilidade completa.
    Se isso bastasse, a trava seria desligavel escrevendo um paragrafo."""
    texto = (RUIM / "README.md").read_text(encoding="utf-8").lower()
    assert "lineage" in texto and "rastreabilidade" in texto
    assert acha(executar(RUIM, {"ethics"}, CFG_RUIM)), (
        "afirmacao em README desligou o check — mencao virou fato")


@pytest.mark.pse_ethics
def test_lineage_declarado_e_resolvivel_nao_dispara():
    res = executar(BOM, {"ethics"}, CFG_BOM)
    assert not acha(res), [f.titulo for f in acha(res)]
    assert "E-08" in res["checks_executados"]


# ==================================================== limites
@pytest.mark.pse_ethics
def test_sem_tratamento_a_rastrear_e_pulado(tmp_path):
    (tmp_path / "app.py").write_text("def somar(a, b):\n    return a + b\n")
    res = executar(tmp_path, {"ethics"}, {"decision_making": "automated"})
    pulados = {c["id"]: c["motivo"] for c in res["checks_pulados"]}
    assert "E-08" in pulados and pulados["E-08"]


@pytest.mark.pse_ethics
def test_trilha_incompleta_e_achado(tmp_path):
    """Registro sem destino nao rastreia nada ate o fim."""
    (tmp_path / "catalog.yaml").write_text(CATALOGO_COM_PII)
    (tmp_path / "lineage.jsonl").write_text(json.dumps({
        "dataset": "clientes", "origem": "form", "transformacao": "validacao"}) + "\n")
    res = executar(tmp_path, {"ethics"},
                   {"catalog_path": "catalog.yaml", "lineage_path": "lineage.jsonl",
                    "decision_making": "automated"})
    e08 = acha(res)
    assert e08 and "destino" in " ".join(f.descricao for f in e08)


@pytest.mark.pse_ethics
def test_trilha_que_nao_cobre_a_tabela_e_achado(tmp_path):
    """Existir trilha nao basta: ela tem de alcancar os dados que existem."""
    (tmp_path / "catalog.yaml").write_text(
        CATALOGO_COM_PII +
        "  pedidos:\n    fields:\n      endereco:\n        class: personal\n"
        "        owner: o\n        purpose: p\n        legal_basis: contrato\n"
        "        retention_years: 2\n")
    (tmp_path / "lineage.jsonl").write_text(json.dumps({
        "dataset": "clientes", "origem": "form", "transformacao": "v",
        "destino": "db"}) + "\n")
    res = executar(tmp_path, {"ethics"},
                   {"catalog_path": "catalog.yaml", "lineage_path": "lineage.jsonl",
                    "decision_making": "automated"})
    e08 = acha(res)
    assert e08 and any("pedidos" in f.titulo for f in e08), [f.titulo for f in e08]
    assert not any("clientes" in f.titulo for f in e08)


@pytest.mark.pse_ethics
def test_trilha_ilegivel_e_indeterminado(tmp_path):
    """Arquivo quebrado nao e 'sem trilha': e 'nao consegui ler'. Bloqueia."""
    (tmp_path / "catalog.yaml").write_text(CATALOGO_COM_PII)
    (tmp_path / "lineage.jsonl").write_text("{isto nao e json\n")
    res = executar(tmp_path, {"ethics"},
                   {"catalog_path": "catalog.yaml", "lineage_path": "lineage.jsonl",
                    "decision_making": "automated"})
    motivos = {c["id"]: c["motivo"] for c in res["checks_indeterminados"]}
    assert "E-08" in motivos and "ilegivel" in motivos["E-08"].lower()
    assert not acha(res)


@pytest.mark.pse_ethics
def test_lineage_declarado_e_inexistente_e_achado(tmp_path):
    """Declaracao que nao resolve nao e declaracao."""
    (tmp_path / "catalog.yaml").write_text(CATALOGO_COM_PII)
    res = executar(tmp_path, {"ethics"},
                   {"catalog_path": "catalog.yaml",
                    "lineage_path": "docs/lineage.jsonl",
                    "decision_making": "automated"})
    e08 = acha(res)
    assert e08 and e08[0].arquivo == "docs/lineage.jsonl"


@pytest.mark.pse_ethics
def test_encontra_trilha_sem_declaracao_explicita(tmp_path):
    """`lineage.jsonl` na raiz vale sem o consumidor declarar o caminho."""
    (tmp_path / "catalog.yaml").write_text(CATALOGO_COM_PII)
    (tmp_path / "lineage.jsonl").write_text(json.dumps({
        "dataset": "clientes", "origem": "form", "transformacao": "v",
        "destino": "db"}) + "\n")
    res = executar(tmp_path, {"ethics"},
                   {"catalog_path": "catalog.yaml", "decision_making": "automated"})
    assert not acha(res)
    assert "E-08" in res["checks_executados"]


@pytest.mark.pse_ethics
def test_art_42_quando_ha_terceiro(tmp_path):
    """Trilha que atravessa terceiro traz a responsabilidade solidaria junto."""
    (tmp_path / "catalog.yaml").write_text(CATALOGO_COM_PII)
    (tmp_path / "tp.yml").write_text(
        "integrations:\n  - name: parceiro\n    hosts: [a.example.net]\n"
        "    dpa_signed: true\n    egress_fields: [id_pseudonimo]\n")
    res = executar(tmp_path, {"ethics"},
                   {"catalog_path": "catalog.yaml", "third_party_manifest": "tp.yml",
                    "decision_making": "automated"})
    e08 = acha(res)
    assert e08 and "Art. 42" in e08[0].base_legal


@pytest.mark.pse_ethics
def test_sem_terceiro_nao_invoca_art_42(tmp_path):
    (tmp_path / "catalog.yaml").write_text(CATALOGO_COM_PII)
    res = executar(tmp_path, {"ethics"},
                   {"catalog_path": "catalog.yaml", "decision_making": "automated"})
    e08 = acha(res)
    assert e08 and "Art. 42" not in e08[0].base_legal


# ==================================================== catalogo completo
def test_catalogo_100_por_cento_implementado():
    from pse import catalogo
    assert catalogo.previstos() == [], (
        f"ainda ha previstos: {[c['id'] for c in catalogo.previstos()]}")
    assert len(catalogo.implementados()) == len(catalogo.CATALOGO) == 43
    m = catalogo.meta("E-08")
    assert m["pack"] == "ethics" and m["canonical_mutation"]
    assert "rastreabilidade" in m["base_legal"].lower()


def test_laudo_sem_previstos(tmp_path):
    out = tmp_path / "l.json"
    main(["--path", str(BOM), "--config", str(BOM / "pse-config.yaml"),
          "--output", str(out)])
    laudo = json.loads(out.read_text(encoding="utf-8"))
    assert laudo["checks_previstos"] == []
    assert laudo["cobertura"]["catalogo_total"] == 43
    assert "E-08" in laudo["checks_executados"]


@pytest.mark.mordida
def test_fixture_conforme_segue_verde(tmp_path):
    rc = main(["--path", str(BOM), "--config", str(BOM / "pse-config.yaml"),
               "--output", str(tmp_path / "l.json")])
    laudo = json.loads((tmp_path / "l.json").read_text(encoding="utf-8"))
    assert rc == 0, [(f["check_id"], f["titulo"]) for f in laudo["findings"]]
