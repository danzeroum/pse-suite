"""E-11, E-12, E-13 — IA e a cadeia de terceiros que os checks anteriores nao veem.

Os tres atacam buracos distintos e nao sobrepoem o que ja existe:

  E-11  PII crua entrando em prompt de LLM. E-05/E-06 olham VIES do modelo;
        nenhum dos dois olha o que ENTRA nele.
  E-12  derivado (embedding/hash) exportado como se fosse anonimo. P-04
        cobra o catalogo; ninguem cobrava a coerencia entre o que sai
        derivado e o que o catalogo admite ser pessoal.
  E-13  host que vive DENTRO de node_modules/site-packages. S-04 varre o
        codigo de primeira parte e ignora dependencia por construcao — o
        terceiro-do-terceiro passava inteiro.

O maior risco desta rodada e falso-positivo CRITICO no E-11: por isso o
teste que prova que redacao correta NAO dispara vem antes do que prova que
a violacao dispara.
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
           "packs": {"ethics": {"fairness_dataset": "eval.csv",
                                "fairness_report": "fairness-report.yaml"}},
           "consent_model_path": "consent-model.yaml"}


def acha(res, cid):
    return [f for f in res["findings"] if f.check_id == cid]


# ============================================ E-11: nao punir redacao correta
@pytest.mark.pse_ethics
def test_e11_redacao_correta_nao_dispara():
    """O teste que mais importa. Falso-positivo em CRITICO ensina o operador
    a ignorar o laudo — e um laudo ignorado nao protege ninguem."""
    res = executar(BOM, {"ethics"}, CFG_BOM)
    assert not acha(res, "E-11"), [
        (f.arquivo, f.linha, f.snippet) for f in acha(res, "E-11")]
    assert "E-11" in res["checks_executados"]


@pytest.mark.pse_ethics
def test_e11_pii_crua_no_prompt_e_critico():
    res = executar(RUIM, {"ethics"}, CFG_RUIM)
    e11 = acha(res, "E-11")
    assert len(e11) == 1
    assert e11[0].severidade.value == "CRITICO"
    assert e11[0].arquivo == "ia.py" and e11[0].linha
    assert "Art. 42" in e11[0].base_legal


@pytest.mark.pse_ethics
def test_e11_comentario_citando_redact_nao_desliga(tmp_path):
    """A fixture ruim ja tem `# TODO: redact` na linha de cima da violacao.
    Mencao nao redige nada — a ancora e a chamada que executa (D-01)."""
    (tmp_path / "a.py").write_text(
        "import llm\n\n\n"
        "def f(user):\n"
        "    # redact aplicado no futuro\n"
        '    return llm.complete("cpf=" + user.cpf)\n')
    res = executar(tmp_path, {"ethics"}, {"decision_making": "automated"})
    assert acha(res, "E-11"), "comentario citando redact desligou um CRITICO"


@pytest.mark.pse_ethics
@pytest.mark.parametrize("chamada,esperado", [
    ('llm.complete(f"cliente {user.cpf}")', True),
    ('llm.complete(redact(f"cliente {user.cpf}"))', False),
    ('llm.complete(mascarar(user.cpf))', False),
    ('llm.complete("resumo generico do atendimento")', False),
    ('llm.complete(f"titular {user.email} reclamou")', True),
    ('llm.complete("cpf=529.982.247-25")', True),
])
def test_e11_limites(tmp_path, chamada, esperado):
    (tmp_path / "a.py").write_text(
        f"import llm\n\n\ndef f(user):\n    return {chamada}\n")
    res = executar(tmp_path, {"ethics"}, {"decision_making": "automated"})
    assert bool(acha(res, "E-11")) is esperado, chamada


@pytest.mark.pse_ethics
def test_e11_usa_a_regua_e_nao_lista_propria():
    """Se a regua muda, o check muda junto — nada de lista hardcoded."""
    import pse.checks.ethics.e11_pii_em_prompt as e11
    fonte = Path(e11.__file__).read_text(encoding="utf-8")
    for termo in ("cpf", "titulo_eleitor", "passaporte"):
        assert f'"{termo}"' not in fonte and f"'{termo}'" not in fonte


# ============================================ E-12
@pytest.mark.pse_ethics
def test_e12_derivado_de_campo_fora_do_catalogo():
    res = executar(RUIM, {"ethics"}, CFG_RUIM)
    e12 = acha(res, "E-12")
    assert len(e12) == 1
    assert e12[0].arquivo == "ia.py" and e12[0].linha
    assert "Art. 42" in e12[0].base_legal


@pytest.mark.pse_ethics
def test_e12_origem_catalogada_como_personal_nao_dispara():
    res = executar(BOM, {"ethics"}, CFG_BOM)
    assert not acha(res, "E-12"), [f.descricao for f in acha(res, "E-12")]


@pytest.mark.pse_ethics
def test_e12_sem_catalogo_e_indeterminado(tmp_path):
    """Sem inventario nao da para dizer se o campo e pessoal — e 'nao sei'
    nunca degrada para verde."""
    (tmp_path / "a.py").write_text(
        "def f(u):\n    hash_do_cpf = sha256(u.cpf)\n    broker.send(hash_do_cpf)\n")
    res = executar(tmp_path, {"ethics"}, {"decision_making": "automated"})
    motivos = {c["id"]: c["motivo"] for c in res["checks_indeterminados"]}
    assert "E-12" in motivos and "catalogo" in motivos["E-12"]


# ============================================ E-13
@pytest.mark.pse_ethics
def test_e13_host_de_dependencia_fora_do_manifesto():
    res = executar(RUIM, {"ethics"}, CFG_RUIM)
    e13 = acha(res, "E-13")
    assert len(e13) == 1
    assert e13[0].severidade.value == "ALTO"
    assert "telemetria.rastreador.example.net" in e13[0].titulo
    assert "rastreador-ui" in e13[0].descricao, "nao nomeou a dependencia culpada"
    assert e13[0].arquivo.startswith("node_modules/") and e13[0].linha
    assert "Art. 42" in e13[0].base_legal


@pytest.mark.pse_ethics
def test_e13_host_declarado_nao_dispara():
    res = executar(BOM, {"ethics"}, CFG_BOM)
    assert not acha(res, "E-13"), [f.titulo for f in acha(res, "E-13")]


@pytest.mark.pse_ethics
def test_e13_sem_manifesto_e_pulado_com_motivo(tmp_path):
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "x.js").write_text('fetch("https://a.example.net")')
    res = executar(tmp_path, {"ethics"}, {"decision_making": "automated"})
    pulados = {c["id"]: c["motivo"] for c in res["checks_pulados"]}
    assert "E-13" in pulados and pulados["E-13"]


@pytest.mark.pse_ethics
def test_e13_ve_o_que_s04_ignora_por_construcao():
    """A prova de que E-13 nao duplica S-04: o mesmo host que E-13 acha
    dentro da dependencia e invisivel para S-04."""
    res = executar(RUIM, {"ethics", "security"}, CFG_RUIM)
    hosts_s04 = " ".join(f.titulo for f in acha(res, "S-04"))
    assert "telemetria.rastreador.example.net" not in hosts_s04
    assert acha(res, "E-13")


# ============================================ regua e catalogo
def test_regua_llm_e_vigiada():
    """Remover a categoria llm da regua tem de reprovar — E-11 deriva dela
    os fornecedores que reconhece."""
    from pse.engine.context import Contexto
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        cats = Contexto(t).data["third-party-endpoints"]["categorias"]
    assert "llm" in cats and cats["llm"]
    assert any("openai" in h for h in cats["llm"])
    assert any("anthropic" in h for h in cats["llm"])


def test_catalogo_tem_os_tres():
    from pse import catalogo
    for cid in ("E-11", "E-12", "E-13"):
        m = catalogo.meta(cid)
        assert m.get("pack") == "ethics"
        assert m.get("status") == "implementado"
        assert m.get("canonical_mutation")
        assert "Art. 42" in m.get("base_legal", "")
    assert len(catalogo.CATALOGO) == 49
    assert len(catalogo.implementados()) == 49


def test_laudo_lista_os_tres(tmp_path):
    out = tmp_path / "l.json"
    main(["--path", str(RUIM), "--config", str(RUIM / "pse-config.yaml"),
          "--output", str(out)])
    laudo = json.loads(out.read_text(encoding="utf-8"))
    assert {"E-11", "E-12", "E-13"} <= set(laudo["checks_executados"])
    ids = {f["check_id"] for f in laudo["findings"]}
    assert {"E-11", "E-12", "E-13"} <= ids


@pytest.mark.mordida
def test_fixture_conforme_segue_verde(tmp_path):
    rc = main(["--path", str(BOM), "--config", str(BOM / "pse-config.yaml"),
               "--output", str(tmp_path / "l.json")])
    laudo = json.loads((tmp_path / "l.json").read_text(encoding="utf-8"))
    assert rc == 0, [(f["check_id"], f["titulo"]) for f in laudo["findings"]]
