"""D-04, D-05, D-06, D-07 — o contrato com o consumidor.

O que um consumidor que pina o pacote precisa poder fazer: declarar packs e
ser obedecido, validar o laudo que recebe, provar que a trava morde sem
clonar este repositorio, e achar cada finding por arquivo:linha.
"""
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from pse.cli import main
from pse.engine import yamlloc
from pse.schemas_validate import LaudoInvalido, carregar, validar_laudo
from pse.selftest import autoprova

RAIZ = Path(__file__).resolve().parent.parent
FIX = Path(__file__).parent / "fixtures"


# ------------------------------------------------------------------ D-04
def _config(tmp_path, **packs):
    cfg = tmp_path / "pse-config.yaml"
    linhas = ["pse_suite:", "  catalog_path: catalog.yaml", "  packs:"]
    linhas += [f"    {p}: {{enabled: {str(v).lower()}}}" for p, v in packs.items()]
    cfg.write_text("\n".join(linhas) + "\n")
    return cfg


def test_pack_desabilitado_e_obedecido_e_declarado(tmp_path):
    """A declaracao do consumidor era decorativa: `enabled: false` seguia
    rodando. Agora vale — e a omissao aparece no laudo com o motivo."""
    cfg = _config(tmp_path, privacy=True, security=False, ethics=False)
    out = tmp_path / "l.json"
    main(["--path", str(FIX / "consumidor_ruim"), "--config", str(cfg),
          "--output", str(out)])
    laudo = json.loads(out.read_text(encoding="utf-8"))
    assert laudo["packs"] == ["privacy"]
    desab = {d["pack"]: d["motivo"] for d in laudo["packs_desabilitados"]}
    assert set(desab) == {"security", "ethics"}
    assert all(desab.values())
    assert not any(f["pack"] != "privacy" for f in laudo["findings"])


def test_desabilitar_tudo_nao_compra_um_verde(tmp_path):
    """Sem pack nenhum nao ha o que auditar — e laudo vazio nao e conforme."""
    cfg = _config(tmp_path, privacy=False, security=False, ethics=False)
    assert main(["--path", str(FIX / "consumidor_ruim"), "--config", str(cfg)]) == 30


# ------------------------------------------------------------------ D-05
def test_laudo_valida_contra_o_schema(tmp_path):
    out = tmp_path / "l.json"
    main(["--path", str(FIX / "consumidor_ruim"),
          "--config", str(FIX / "consumidor_ruim" / "pse-config.yaml"),
          "--output", str(out)])
    validar_laudo(json.loads(out.read_text(encoding="utf-8")))   # nao levanta


def test_schema_recusa_laudo_defeituoso():
    """O `$ref` entre laudo e finding tem de resolver de verdade — senao a
    validacao passa sem olhar os findings."""
    base = {
        "schema": "laudo-pse-1.0",
        "artifact": {"suite": "pse-suite", "suite_version": "0.2.0",
                     "schema_version": "laudo-pse-1.0", "catalog_hash": "0" * 64,
                     "timestamp_utc": "2026-08-06T00:00:00Z"},
        "veredito": "conforme", "exit_code": 0, "packs": ["privacy"],
        "resumo": {"total_findings": 1, "por_severidade": {}},
        "checks_executados": [], "checks_pulados": [],
        "checks_indeterminados": [],
        "findings": [{"check_id": "P-01", "pack": "privacy",
                      "severidade": "INVENTADA", "titulo": "t",
                      "descricao": "d", "recomendacao": "r"}],
    }
    with pytest.raises(LaudoInvalido):
        validar_laudo(base)


def test_check_pulado_sem_motivo_e_recusado_pelo_schema():
    """A doutrina esta no schema, nao so no codigo."""
    laudo = {
        "schema": "laudo-pse-1.0",
        "artifact": {"suite": "pse-suite", "suite_version": "0.2.0",
                     "schema_version": "laudo-pse-1.0", "catalog_hash": "0" * 64,
                     "timestamp_utc": "2026-08-06T00:00:00Z"},
        "veredito": "conforme", "exit_code": 0, "packs": ["privacy"],
        "resumo": {"total_findings": 0, "por_severidade": {}},
        "checks_executados": [], "checks_pulados": [{"id": "P-02", "motivo": ""}],
        "checks_indeterminados": [], "findings": [],
    }
    with pytest.raises(LaudoInvalido):
        validar_laudo(laudo)


def test_schemas_viajam_no_wheel(tmp_path):
    """Sem isto o consumidor recebe a evidencia e nao consegue conferi-la."""
    r = subprocess.run([sys.executable, "-m", "pip", "wheel", str(RAIZ),
                        "-w", str(tmp_path), "--no-deps", "-q"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    nomes = zipfile.ZipFile(next(tmp_path.glob("*.whl"))).namelist()
    assert any(n.endswith("pse/schemas/laudo-pse-1.0.json") for n in nomes)
    assert any(n.endswith("pse/schemas/finding-1.0.json") for n in nomes)
    assert any(n.endswith("pse/data/pii-patterns.yaml") for n in nomes)
    assert any(n.endswith("pse/data/checks-catalog.yaml") for n in nomes)
    # D-06: a fixture da mordida tem de viajar junto, ou o passo negativo
    # documentado quebra por arquivo inexistente no consumidor.
    assert any(n.endswith("pse/fixtures/mordida/app.py") for n in nomes)
    assert any(n.endswith("pse/fixtures/mordida/catalog.yaml") for n in nomes)


def test_schemas_nao_ficaram_duplicados_na_raiz():
    assert not (RAIZ / "schemas").exists(), (
        "schemas/ na raiz E no pacote sao duas fontes que derivam")


# ------------------------------------------------------------------ D-06
@pytest.mark.mordida
def test_autoprova_embarcada_morde():
    r = autoprova()
    assert r["ok"], r["motivo"]
    assert {"P-01", "P-06", "P-08", "E-04"} <= set(r["encontrados"])


@pytest.mark.mordida
def test_self_test_pelo_cli():
    assert main(["--self-test"]) == 0


@pytest.mark.mordida
def test_manifesto_sai_completo(capsys):
    assert main(["--manifesto"]) == 0
    m = json.loads(capsys.readouterr().out)
    assert m["suite_version"] and len(m["catalog_hash"]) == 64
    assert m["schema_version"] == carregar("laudo-pse-1.0.json")["properties"]["schema"]["const"]
    assert m["autoprova"]["ok"]
    assert len(m["checks_implementados"]) + len(m["checks_previstos"]) == 30


# ------------------------------------------------------------------ D-07
def test_todo_finding_tem_endereco(tmp_path):
    """O criterio de aceite pede arquivo:linha. Achado de catalogo saia com
    linha null — e achado sem endereco custa ao revisor o trabalho que o
    laudo deveria poupar."""
    out = tmp_path / "l.json"
    main(["--path", str(FIX / "consumidor_ruim"),
          "--config", str(FIX / "consumidor_ruim" / "pse-config.yaml"),
          "--output", str(out)])
    laudo = json.loads(out.read_text(encoding="utf-8"))
    sem = [(f["check_id"], f["arquivo"], f["linha"]) for f in laudo["findings"]
           if not f["arquivo"] or not f["linha"]]
    assert not sem, f"findings sem arquivo:linha: {sem}"


def test_localizador_de_yaml_acha_a_linha_certa():
    texto = ("tables:\n"
             "  users:\n"
             "    fields:\n"
             "      cpf:\n"
             "        class: personal\n"
             "      genero:\n"
             "        class: sensitive\n")
    assert yamlloc.localizar(texto, ["tables", "users", "fields", "cpf"]) == 4
    assert yamlloc.localizar(texto, ["tables", "users", "fields", "genero"]) == 6
    assert yamlloc.localizar(texto, ["tables", "users", "fields", "nao_existe"]) is None


def test_localizador_acha_entrada_de_lista():
    texto = ("integrations:\n"
             "  - name: google-analytics\n"
             "    dpa_signed: true\n"
             "  - name: stripe\n"
             "    dpa_signed: false\n")
    assert yamlloc.localizar_valor(texto, "name", "stripe") == 4
    assert yamlloc.localizar_valor(texto, "name", "ausente") is None
