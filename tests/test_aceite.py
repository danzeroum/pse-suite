"""O teste de aceite: a régua contra um sistema de verdade.

NOTA DE PROCEDÊNCIA. A rodada anterior descreveu esta infraestrutura como
"já pronta". Ela não estava — aquele bloco foi substituído antes de ser
executado. Registro aqui porque a mesma honestidade que se cobra do laudo
vale para o estado do próprio projeto.

O QUE UM ACEITE PROVA. A fixture prova que o CHECK está certo: dado um alvo
sintético com a violação plantada, ele reprova. O aceite prova outra coisa —
que a RÉGUA reproduz um sistema real, com o volume, a bagunça e os falsos
positivos que só código de verdade tem.

E não é teoria: o primeiro aceite real (danzeroum/btv) achou três defeitos
que nenhuma fixture tinha achado em onze versões —

  1. S-04 lia COMENTÁRIO. `// https://vite.dev/config/` virava achado. D-01
     violado pelo check mais antigo da suite.
  2. O laudo era SILENCIOSO sobre 137 arquivos Rust — indistinguível de
     "auditado e limpo".
  3. A mensagem de parse ACUSAVA O ALVO num `.ts` que o `tsc` compila.

Nenhum deles seria encontrado por mais fixtures: fixture é desenhada por
quem escreveu o check, e por isso não contém a surpresa.

A REGRA QUE ESTE MÓDULO EXISTE PARA IMPOR: alvo ausente é PENDENTE com
motivo datado — nunca verde. É a mesma regra dos checks dinâmicos, aplicada
ao próprio aceite.
"""
from pathlib import Path

import pytest

from pse import aceite

pytestmark = pytest.mark.pse_aceite

RAIZ = Path(__file__).resolve().parent.parent


def test_ha_pelo_menos_um_aceite_declarado():
    """Uma suite sem aceite nenhum é uma suite que nunca encostou na
    realidade — e não teria como saber disso."""
    assert aceite.declarados(), (
        "nenhum aceite em aceites/. A suite passaria a se provar apenas "
        "contra fixtures que ela mesma desenhou")


@pytest.mark.parametrize("nome", aceite.declarados())
def test_aceite_declara_o_minimo(nome):
    """Baseline sem `devem_executar` e sem `nao_podem_achar` é decoração:
    passaria com a suite inteira quebrada."""
    d = aceite.carregar(nome)
    assert d.get("alvo", {}).get("caminho")
    assert d.get("alvo", {}).get("como_obter"), (
        "o aceite tem de dizer COMO obter o alvo — senão o skip é um beco")
    b = d.get("baseline") or {}
    assert b.get("devem_executar"), "sem isto, um check pode parar de rodar"
    assert b.get("nao_podem_achar"), (
        "sem isto, um falso positivo novo passa — e falso positivo em alvo "
        "real é o defeito mais caro desta suite")


@pytest.mark.parametrize("nome", aceite.declarados())
def test_aceite_roda_ou_fica_pendente_com_motivo(nome):
    """O teste central. Alvo presente: o baseline tem de bater. Alvo
    ausente: PENDENTE com motivo datado — nunca verde silencioso."""
    d = aceite.carregar(nome)
    disponivel, motivo = aceite.alvo_disponivel(d)
    if not disponivel:
        assert d.get("pendente_desde"), (
            "aceite pendente sem data: 'depois' sem data é 'nunca'")
        pytest.skip(f"[aceite:{nome}] PENDENTE — {motivo}")

    r = aceite.relatorio(nome)
    assert r["estado"] == "conforme", (
        f"aceite `{nome}` divergiu do baseline:\n  " +
        "\n  ".join(r["divergencias"]) +
        "\n\nOu o alvo mudou (atualize o baseline, com a nota do porquê) ou "
        "a suite regrediu. As duas exigem decisão humana — por isso o teste "
        "reprova em vez de se ajustar sozinho.")


@pytest.mark.mordida
def test_alvo_ausente_nunca_vira_conforme(tmp_path):
    """A trava. Um aceite cujo alvo não existe TEM de sair pendente — se
    saísse conforme, seria o verde falso mais caro da suite: o carimbo de
    'validado contra sistema real' sem sistema real nenhum."""
    d = {"alvo": {"caminho": str(tmp_path / "nao-existe"),
                  "como_obter": "clone o repo"},
         "pendente_desde": "2026-08-07"}
    disponivel, motivo = aceite.alvo_disponivel(d)
    assert disponivel is False
    assert "nao esta disponivel" in motivo
    assert "2026-08-07" in motivo, "o motivo tem de ser DATADO"


@pytest.mark.mordida
def test_aceite_sem_caminho_declarado_e_pendente():
    disponivel, motivo = aceite.alvo_disponivel({"alvo": {}})
    assert disponivel is False and "alvo.caminho" in motivo


@pytest.mark.mordida
@pytest.mark.parametrize("laudo,esperado_em", [
    # check que parou de executar
    ({"checks_executados": [], "checks_indeterminados": [{"id": "P-01"}],
      "findings": []}, "deveria EXECUTAR"),
    # check que parou de morder
    ({"checks_executados": ["P-01", "S-04"], "findings": []}, "piso do baseline"),
    # falso positivo novo
    ({"checks_executados": ["P-01", "S-04"],
      "findings": [{"check_id": "S-04"}, {"check_id": "S-14"}]},
     "falso positivo"),
])
def test_comparacao_pega_cada_tipo_de_regressao(laudo, esperado_em):
    """A comparação tem de MORDER nos três eixos. Um baseline que só olha o
    exit code passaria com a suite inteira quebrada por dentro."""
    base = {"devem_executar": ["P-01", "S-04"], "devem_achar": {"S-04": 1},
            "nao_podem_achar": ["S-14"]}
    divergencias = " ".join(aceite.comparar(laudo, base))
    assert esperado_em in divergencias, divergencias


@pytest.mark.mordida
def test_comparacao_pega_estrato_que_saiu_do_alcance():
    """Se a suite parar de ler TypeScript, nenhum check reprova — eles
    simplesmente não encontram nada. O aceite é o único lugar onde isso
    aparece."""
    laudo = {"checks_executados": [], "findings": [],
             "alcance": {"lidos": [{"linguagem": "Python"}],
                         "fora_de_alcance": []}}
    d = aceite.comparar(laudo, {"linguagens_no_alcance": ["TypeScript"]})
    assert any("fora do alcance" in x or "nao esta" in x for x in d), d


@pytest.mark.mordida
def test_comparacao_pega_lacuna_que_sumiu_em_silencio():
    """Rust sair do bloco `fora_de_alcance` sem ninguém declarar é a lacuna
    desaparecendo do laudo — o oposto do que o bloco existe para fazer."""
    laudo = {"checks_executados": [], "findings": [],
             "alcance": {"lidos": [], "fora_de_alcance": []}}
    d = aceite.comparar(laudo, {"linguagens_fora_do_alcance": ["Rust"]})
    assert any("Rust" in x for x in d), d


# ==================================================== o alcance, isolado
def test_alcance_conta_o_que_nao_le(tmp_path):
    """Três categorias, e Rust migrou entre elas — por isso este teste mudou.

    Go continua totalmente fora de alcance; Rust passou a ter alcance
    PARCIAL (quatro vetores por padrão textual, sem parser). Colapsar as
    duas faria o laudo dizer a mesma coisa sobre duas situações opostas.
    """
    from pse import alcance
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "b.rs").write_text("fn main() {}\n", encoding="utf-8")
    (tmp_path / "c.rs").write_text("fn f() {}\n", encoding="utf-8")
    (tmp_path / "e.go").write_text("package main\n", encoding="utf-8")
    (tmp_path / "d.md").write_text("# doc\n", encoding="utf-8")

    m = alcance.medir(tmp_path)
    lidos = {x["linguagem"]: x["arquivos"] for x in m["lidos"]}
    fora = {x["linguagem"]: x["arquivos"] for x in m["fora_de_alcance"]}
    parcial = {x["linguagem"]: x for x in m["alcance_parcial"]}
    assert lidos == {"Python": 1}
    assert fora == {"Go": 1}
    assert parcial["Rust"]["arquivos"] == 2
    assert set(parcial["Rust"]["checks"]) == {"S-06", "P-18", "P-19", "S-16"}
    assert "nao foram olhados" in parcial["Rust"]["nota"]
    assert m["arquivos_fora_de_alcance"] == 1
    assert m["arquivos_em_alcance_parcial"] == 2
    assert "NAO E ATESTADO DE CONFORMIDADE" in m["nota"]
    # Markdown não conta como lacuna: não é código nem declaração, e
    # listá-lo viraria ruído que esconde a lacuna de verdade.
    assert "Markdown" not in fora and ".md" not in str(fora)


def test_alcance_diz_com_que_ferramenta_leu(tmp_path):
    """Procedência: o laudo tem de dizer COM O QUE leu, não só que leu."""
    from pse import alcance
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "b.tsx").write_text("export const C = () => null;\n",
                                    encoding="utf-8")
    ferramentas = {x["linguagem"]: x["ferramenta"]
                   for x in alcance.medir(tmp_path)["lidos"]}
    assert ferramentas["Python"] == "ast (stdlib)"
    assert ferramentas["TypeScript/TSX"] == "tree-sitter"


def test_alvo_so_com_linguagem_lida_nao_inventa_lacuna(tmp_path):
    from pse import alcance
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    m = alcance.medir(tmp_path)
    assert m["arquivos_fora_de_alcance"] == 0
    assert "Todo arquivo" in m["nota"]


def test_laudo_carrega_o_alcance(tmp_path):
    """O bloco tem de estar NO LAUDO — num relatório que ninguém lê ele não
    resolveria nada."""
    import json

    from pse.cli import main
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "b.rs").write_text("fn main() {}\n", encoding="utf-8")
    out = tmp_path / "l.json"
    main(["--path", str(tmp_path), "--output", str(out)])
    laudo = json.loads(out.read_text(encoding="utf-8"))
    assert laudo["alcance"]["arquivos_em_alcance_parcial"] == 1
    parcial = laudo["alcance"]["alcance_parcial"][0]
    assert parcial["linguagem"] == "Rust"
    assert set(parcial["checks"]) == {"S-06", "P-18", "P-19", "S-16"}
