"""Trabalho B contra fixture com violacoes + contrato de veredito."""
import json
from pathlib import Path

import pytest

from pse.cli import main
from pse.engine.runner import executar
from pse.model import (EXIT_CONFORME, EXIT_INDETERMINADO, EXIT_VIOLACAO_ALTA,
                       EXIT_VIOLACAO_CRITICA)

FIX = Path(__file__).parent / "fixtures" / "consumidor_ruim"
BOM = Path(__file__).parent / "fixtures" / "consumidor_bom"
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


# ==================================================== S-08, o órfão que a trava achou
#
# `Transferencia internacional sem base`, fase 1, existia desde o começo sem um
# único teste próprio. Ele aparecia na docstring de outro teste — e docstring
# não é teste. É o D-01 aplicado à própria suíte: a MENÇÃO do check não prova
# que alguém o exercitou.
#
# A prova de mutação canônica passava por ele, porque parametriza sobre
# `catalogo.implementados()` e alcança todos por construção. Ela prova que o
# inverso canônico fica vermelho; não prova que o caso conforme fica quieto,
# nem que o skip nomeia o motivo. É isso que os quatro abaixo cobrem.
MANIFESTO = {"catalog_path": "catalog.yaml", "third_party_manifest": "tp.yml"}


def com_manifesto(tmp_path, corpo):
    (tmp_path / "tp.yml").write_text(corpo, encoding="utf-8")
    return executar(tmp_path, {"security"}, MANIFESTO)


@pytest.mark.pse_security
def test_s08_destino_fora_do_br_sem_base_dispara(tmp_path):
    res = com_manifesto(tmp_path,
                        "integrations:\n"
                        "  - name: parceiro-us\n"
                        "    hosts: [api.parceiro.example.net]\n"
                        "    dpa_signed: true\n"
                        "    data_residency: US\n")
    achados = [f for f in res["findings"] if f.check_id == "S-08"]
    assert achados, "residência US declarada sem transfer_basis"
    assert achados[0].severidade.value == "ALTO"
    assert "parceiro-us" in achados[0].titulo


@pytest.mark.pse_security
def test_s08_base_declarada_desliga(tmp_path):
    """D-08: quem declarou a base fez o que o Art. 33 pede. Punir o manifesto
    correto ensina o time a parar de declarar residência."""
    res = com_manifesto(tmp_path,
                        "integrations:\n"
                        "  - name: parceiro-us\n"
                        "    hosts: [api.parceiro.example.net]\n"
                        "    dpa_signed: true\n"
                        "    data_residency: US\n"
                        "    transfer_basis: clausulas-contratuais-padrao\n")
    assert not [f for f in res["findings"] if f.check_id == "S-08"]
    assert "S-08" in res["checks_executados"], "verde por não ter olhado"


@pytest.mark.pse_security
def test_s08_residencia_nacional_nao_dispara(tmp_path):
    res = com_manifesto(tmp_path,
                        "integrations:\n"
                        "  - name: parceiro-br\n"
                        "    hosts: [api.parceiro.example.com.br]\n"
                        "    dpa_signed: true\n"
                        "    data_residency: BR\n")
    assert not [f for f in res["findings"] if f.check_id == "S-08"]


@pytest.mark.pse_security
def test_s08_sem_manifesto_e_pulado(tmp_path):
    """A ausência do manifesto já é cobrada por S-04. Cobrá-la duas vezes
    ensina a ignorar as duas — então aqui o desfecho é pular, com motivo."""
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    res = executar(tmp_path, {"security"}, MANIFESTO)
    pulados = {c["id"]: c["motivo"] for c in res["checks_pulados"]}
    assert "S-08" in pulados and "S-04" in pulados["S-08"]


@pytest.mark.pse_ethics
def test_pack_ethics_encontra_violacoes():
    res = executar(FIX, {"ethics"}, CFG)
    assert {"E-04", "E-05", "E-07"} <= ids(res)


# ------------------------------------------------- contrato de veredito
@pytest.mark.mordida
def test_critico_sai_10(tmp_path):
    """A trava morde: CRITICO -> exit 10, laudo com procedencia completa."""
    out = tmp_path / "laudo.json"
    rc = main(["--path", str(FIX), "--config", str(FIX / "pse-config.yaml"),
               "--output", str(out)])
    assert rc == EXIT_VIOLACAO_CRITICA
    laudo = json.loads(out.read_text(encoding="utf-8"))
    assert laudo["schema"] == "laudo-pse-1.0"
    assert laudo["veredito"] == "violacao"
    assert laudo["resumo"]["por_severidade"]["CRITICO"] >= 3
    art = laudo["artifact"]
    assert art["suite_version"] and art["config_fingerprint"]
    assert art["catalog_hash"] and art["schema_version"]   # Gap 3: a quintupla


@pytest.mark.mordida
def test_alto_sem_critico_sai_11(tmp_path):
    """ALTO nao e silencio nem CRITICO: codigo proprio (D-11).

    A suite reporta a verdade em codigos distintos e nao possui flag que
    rebaixe o gate; a politica 'ALTO bloqueia em main' vive no CI do
    consumidor, protegida por CODEOWNERS.
    """
    (tmp_path / "models.py").write_text("class User:\n    deleted_at = None\n")
    rc = main(["--path", str(tmp_path), "--output", str(tmp_path / "l.json")])
    assert rc == EXIT_VIOLACAO_ALTA
    laudo = json.loads((tmp_path / "l.json").read_text(encoding="utf-8"))
    assert "CRITICO" not in laudo["resumo"]["por_severidade"]
    assert laudo["resumo"]["por_severidade"]["ALTO"] >= 1


@pytest.mark.mordida
def test_conforme_sai_0(tmp_path):
    rc = main(["--path", str(BOM), "--config", str(BOM / "pse-config.yaml"),
               "--output", str(tmp_path / "l.json")])
    assert rc == EXIT_CONFORME


@pytest.mark.mordida
def test_indeterminacao_bloqueia(tmp_path):
    """Fato nao decidivel nunca degrada para verde (exit 20).

    Arquivo Python que nao parseia: a suite nao consegue olhar, e isso
    bloqueia igual a uma violacao.
    """
    (tmp_path / "quebrado.py").write_text("def f(:\n    pass\n")
    (tmp_path / "catalog.yaml").write_text(
        "tables:\n  t:\n    fields:\n      cpf:\n        class: personal\n"
        "        owner: o\n        purpose: p\n        legal_basis: contrato\n"
        "        retention_years: 5\n")
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text("pse_suite:\n  catalog_path: catalog.yaml\n")
    out = tmp_path / "l.json"
    rc = main(["--path", str(tmp_path), "--config", str(cfg), "--output", str(out)])
    laudo = json.loads(out.read_text(encoding="utf-8"))
    assert laudo["checks_indeterminados"], "arquivo ilegivel virou silencio"
    assert all(c["motivo"] for c in laudo["checks_indeterminados"])
    assert rc == EXIT_INDETERMINADO
    assert laudo["veredito"] == "indeterminado"


@pytest.mark.mordida
def test_catalogo_ilegivel_sai_30(tmp_path):
    """YAML quebrado e entrada invalida, nunca 'catalogo ausente'."""
    (tmp_path / "catalog.yaml").write_text("tables: [isto: nao: e: yaml\n")
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text("pse_suite:\n  catalog_path: catalog.yaml\n")
    assert main(["--path", str(tmp_path), "--config", str(cfg)]) == 30


@pytest.mark.mordida
def test_config_inexistente_sai_30(tmp_path):
    assert main(["--path", str(tmp_path), "--config", str(tmp_path / "nada.yaml")]) == 30


@pytest.mark.mordida
def test_packs_invalidos_saem_30(tmp_path):
    assert main(["--path", str(tmp_path), "--packs", "privacidade"]) == 30


@pytest.mark.pse_security
@pytest.mark.mordida
def test_s04_nao_ve_host_em_comentario(tmp_path):
    """D-01 no check mais antigo da suite, encontrado pelo PRIMEIRO ALVO REAL.

    `// https://vite.dev/config/` num `vite.config.ts` do danzeroum/btv virava
    "host de terceiro nao registrado". Nenhuma fixture tinha URL em
    comentario, e por isso o defeito atravessou o projeto inteiro.

    O literal continua contando: `fetch("https://api.terceiro.com")` e egresso
    de verdade, e ali o literal E o fato. So a MENCAO sai.
    """
    (tmp_path / ".privacy").mkdir()
    (tmp_path / ".privacy" / "third-party-manifest.yml").write_text(
        "integrations: []\n", encoding="utf-8")
    (tmp_path / "vite.config.ts").write_text(
        "// https://vite.dev/config/\n"
        "import x from 'y'\n"
        "export default x\n", encoding="utf-8")
    (tmp_path / "cliente.py").write_text(
        '# https://so-um-comentario.example.net/doc\n'
        'import requests\n'
        'def f():\n'
        '    return requests.get("https://api.egresso-real.example.net/v1")\n',
        encoding="utf-8")

    res = executar(tmp_path, {"security"}, {})
    hosts = " ".join(f.titulo for f in res["findings"] if f.check_id == "S-04")
    assert "egresso-real" in hosts, "o egresso de verdade sumiu junto"
    assert "vite.dev" not in hosts, "host em comentario virou achado (D-01)"
    assert "so-um-comentario" not in hosts, "host em comentario virou achado (D-01)"
