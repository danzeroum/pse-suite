"""Os repo-provas do Relatorio de Validacao, virados testes permanentes.

Criterio de pronto da Etapa 3: cada teste aqui REPROVA em 1eb616b e passa
na versao corrigida. Sao as cinco maneiras medidas de a suite ficar verde
sem ter olhado:

  1. comentario matando E-04/E-05/P-02      (D-01)
  2. `.env` invisivel a varredura           (D-03)
  3. segredo em claro dentro do laudo       (D-02)
  4. regua editada em silencio              (D-13 -> tests/test_regua.py)
  5. alvo inexistente reportado conforme    (Gaps 2/5)
"""
import json
from pathlib import Path

import pytest

from pse.cli import main
from pse.engine.runner import executar

FIX = Path(__file__).parent / "fixtures"
RUIM = FIX / "consumidor_ruim"
SILENCIOSO = FIX / "consumidor_silencioso"
BOM = FIX / "consumidor_bom"

SEGREDO_PLANTADO = "R7pQ-chave-real-de-producao-2026"
CPF_PLANTADO = "529.982.247-25"


def ids(res):
    return {f.check_id for f in res["findings"]}


# ---------------------------------------------------------------- D-01
@pytest.mark.mordida
def test_comentario_nao_desliga_trava():
    """Violacao real + comentario citando o controle != controle presente.

    Em 1eb616b: 0 findings, exit 0. A trava se desligava com uma linha de
    comentario, sem rastro de configuracao.
    """
    cfg = {"catalog_path": "catalog.yaml", "decision_making": "automated"}
    res = executar(SILENCIOSO, {"privacy", "security", "ethics"}, cfg)
    encontrados = ids(res)
    for cid in ("E-04", "E-05", "P-02"):
        assert cid in encontrados, (
            f"{cid} foi suprimido por mencao em comentario — a ancora "
            f"voltou a ser a string, nao o fato."
        )


@pytest.mark.mordida
def test_silencioso_aborta_o_gate():
    rc = main(["--path", str(SILENCIOSO),
               "--config", str(SILENCIOSO / "pse-config.yaml")])
    assert rc != 0, "repositorio com violacoes reais nao pode sair conforme"


@pytest.mark.pse_ethics
def test_controle_real_suprime_o_achado():
    """O outro lado: chamada que executa de fato -> sem finding.

    Sem este teste, a correcao de D-01 poderia ser 'acusar sempre'.
    """
    cfg = {"catalog_path": "catalog.yaml", "decision_making": "automated"}
    res = executar(BOM, {"privacy", "security", "ethics"}, cfg)
    encontrados = ids(res)
    for cid in ("E-04", "E-05", "P-02", "P-01"):
        assert cid not in encontrados, (
            f"{cid} acusou a fixture conforme: falso-positivo. "
            f"Findings: {[(f.check_id, f.arquivo, f.linha) for f in res['findings']]}"
        )


# ---------------------------------------------------------------- D-03
@pytest.mark.mordida
def test_env_e_varrido():
    """`Path('.env').suffix == ''` — o arquivo onde segredo mais aparece
    era o unico que a suite nao lia."""
    res = executar(RUIM, {"privacy", "security"}, {"catalog_path": "catalog.yaml"})
    de_env = [f for f in res["findings"]
              if (f.arquivo or "").startswith(".env")]
    assert de_env, "nenhum finding veio de .env — a varredura continua cega ao arquivo"
    assert {f.check_id for f in de_env} & {"P-06", "S-06"}


# ---------------------------------------------------------------- D-02
@pytest.mark.mordida
def test_laudo_nao_publica_o_segredo(tmp_path):
    """A evidencia nao pode vazar o que ela prova que nao vaza (plano §5.2).

    Em 1eb616b o laudo trazia CPF, e-mail e chave de producao em claro.
    """
    out = tmp_path / "laudo.json"
    main(["--path", str(RUIM), "--config", str(RUIM / "pse-config.yaml"),
          "--output", str(out)])
    bruto = out.read_text(encoding="utf-8")

    assert SEGREDO_PLANTADO not in bruto, "chave plantada saiu em claro no laudo"
    assert CPF_PLANTADO not in bruto, "CPF plantado saiu em claro no laudo"

    laudo = json.loads(bruto)
    p06 = [f for f in laudo["findings"] if f["check_id"] == "P-06"]
    assert p06, "sanitizar nao pode significar deixar de achar"
    assert any(f["arquivo"] and f["linha"] for f in p06), (
        "o localizador e arquivo:linha — mascarar o snippet nao pode "
        "custar a rastreabilidade do achado"
    )


# ---------------------------------------------------------------- Gaps 2/5
@pytest.mark.mordida
def test_alvo_inexistente_nunca_e_conforme(tmp_path):
    """Medido em 1eb616b: exit 0, laudo gravado, 9 checks 'executados'.

    Auditar diretorio que nao existe produzia veredito conforme — a forma
    mais pura de verde-por-nao-olhar.
    """
    rc = main(["--path", str(tmp_path / "nao" / "existe"),
               "--output", str(tmp_path / "l.json")])
    assert rc == 30, f"entrada invalida deve sair 30, saiu {rc}"


@pytest.mark.mordida
def test_versao_nunca_e_fabricada(monkeypatch):
    """`0.1.0-dev` era inventado quando o pacote nao estava instalado:
    laudo com versao falsa, sem erro e sem aviso."""
    import importlib.metadata as md

    from pse import evidence
    from pse.model import VersaoIrresolvivel

    def explode(_):
        raise md.PackageNotFoundError("pse-suite")

    monkeypatch.setattr(evidence, "_metadata_version", explode)
    with pytest.raises(VersaoIrresolvivel):
        evidence.versao_suite()


# ---------------------------------------------------------------- fail-closed
@pytest.mark.mordida
def test_fixture_ruim_aborta_com_critico(tmp_path):
    out = tmp_path / "laudo.json"
    rc = main(["--path", str(RUIM), "--config", str(RUIM / "pse-config.yaml"),
               "--output", str(out)])
    assert rc == 10
    laudo = json.loads(out.read_text(encoding="utf-8"))
    assert laudo["veredito"] == "violacao"
    assert laudo["resumo"]["por_severidade"]["CRITICO"] >= 3


@pytest.mark.mordida
def test_fixture_conforme_nao_aborta(tmp_path):
    out = tmp_path / "laudo.json"
    rc = main(["--path", str(BOM), "--config", str(BOM / "pse-config.yaml"),
               "--output", str(out)])
    laudo = json.loads(out.read_text(encoding="utf-8"))
    assert rc == 0, (
        f"fixture conforme nao pode bloquear. veredito={laudo['veredito']} "
        f"findings={[(f['check_id'], f['arquivo'], f['linha']) for f in laudo['findings']]} "
        f"indeterminados={laudo.get('checks_indeterminados')}"
    )
