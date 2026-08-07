"""A fixture tem de existir no REPOSITORIO, não só no disco de quem a escreveu.

O defeito que este módulo existe para impedir já aconteceu, e enganou bem:
`dist/` no `.gitignore` — uma regra legítima, escrita para não versionar
build — engolia em silêncio

    tests/fixtures/consumidor_ruim/node_modules/rastreador-ui/dist/index.js

que é justamente a dependência que E-13 tem de encontrar. Três testes
verdes na máquina de quem escreveu a fixture, vermelhos em qualquer clone
limpo. Ninguém percebeu porque *working tree verde* parece prova, e não é:
os arquivos existiam localmente.

É o mesmo erro que a suite cobra dos outros — confundir "não vi problema"
com "não há problema". A diferença entre **verificar** (rodar aqui) e
**validar** (rodar no clone) é a mesma que existe entre um check que passou
e um check que morde.

A trava é ampla de propósito: em vez de listar as fixtures que os testes
citam — lista que envelhece no primeiro arquivo novo —, exige que TODO
arquivo sob as raízes de fixture esteja em `git ls-files`. Fixture nova
nasce protegida sem ninguém lembrar de nada.
"""
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
RAIZES_DE_FIXTURE = ("tests/fixtures", "pse/fixtures")

# Artefato de verdade continua sendo artefato mesmo dentro de fixture.
RUIDO = {"__pycache__", ".pytest_cache", ".mypy_cache", ".DS_Store"}


def _e_repositorio() -> bool:
    r = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"],
                       cwd=RAIZ, capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() == "true"


def _versionados() -> set:
    r = subprocess.run(["git", "ls-files", "-z", *RAIZES_DE_FIXTURE],
                       cwd=RAIZ, capture_output=True, text=True, check=True)
    return {p for p in r.stdout.split("\0") if p}


def _no_disco() -> set:
    saida = set()
    for base in RAIZES_DE_FIXTURE:
        for p in (RAIZ / base).rglob("*"):
            if not p.is_file():
                continue
            if any(parte in RUIDO or parte.endswith(".pyc") for parte in p.parts):
                continue
            saida.add(str(p.relative_to(RAIZ)))
    return saida


pytestmark = pytest.mark.skipif(
    not _e_repositorio(),
    reason="fora de um working tree git — a reprodutibilidade só é "
           "verificável de dentro do repositório")


@pytest.mark.mordida
def test_toda_fixture_no_disco_esta_versionada():
    """A trava. Arquivo de fixture que existe aqui e não está no repositório
    é um teste que só passa nesta máquina — e um teste assim é pior que
    nenhum, porque conta como cobertura."""
    faltando = sorted(_no_disco() - _versionados())
    assert not faltando, (
        "arquivo(s) de fixture fora do versionamento:\n  " +
        "\n  ".join(faltando) +
        "\n\nO teste que os usa passa aqui e reprova em clone limpo. "
        "Verifique se alguma regra de artefato no .gitignore (`dist/`, "
        "`build/`, `node_modules/`) os está engolindo e acrescente a exceção "
        "para `tests/fixtures/**` — nunca um `git add -f`, que resolve uma "
        "vez e é esquecido no próximo arquivo.")


@pytest.mark.mordida
def test_a_dependencia_que_o_e13_acusa_esta_no_repositorio():
    """O caso concreto que originou a trava, nomeado.

    E-13 varre `node_modules/` — o único lugar do repositório que a
    varredura normal ignora — e acusa `rastreador-ui` por falar com um host
    fora do manifesto. Sem este arquivo versionado, o achado não existe e o
    check aparenta estar conforme.
    """
    alvo = ("tests/fixtures/consumidor_ruim/node_modules/"
            "rastreador-ui/dist/index.js")
    assert alvo in _versionados(), (
        f"{alvo} não está no repositório — E-13 fica sem corpo de delito e "
        f"3 testes reprovam em clone limpo")
    assert (RAIZ / alvo).exists()


@pytest.mark.mordida
def test_a_trava_reprova_quando_uma_fixture_some(monkeypatch):
    """A trava tem de MORDER, não apenas existir.

    Sem isto, um refactor que quebrasse `_versionados()` — devolvendo o
    conjunto do disco, por exemplo — deixaria o teste eternamente verde e a
    proteção viraria decoração, que é exatamente o defeito que ela vigia.
    """
    real = _versionados()
    vitima = ("tests/fixtures/consumidor_ruim/node_modules/"
              "rastreador-ui/dist/index.js")
    monkeypatch.setitem(globals(), "_versionados", lambda: real - {vitima})
    with pytest.raises(AssertionError) as e:
        test_toda_fixture_no_disco_esta_versionada()
    assert vitima in str(e.value)


def test_todo_diretorio_de_fixture_citado_pelos_testes_existe():
    """As raízes que os testes de domínio apontam por caminho. Se uma sumir,
    o `executar()` roda contra um diretório vazio e devolve verde por não
    ter olhado — o pior resultado possível."""
    esperadas = [
        "consumidor_bom", "consumidor_ruim", "consumidor_silencioso",
        "consumidor_frontend_bom", "consumidor_frontend_ruim",
        "consumidor_api_bom", "consumidor_api_ruim",
        "consumidor_backend_bom", "consumidor_backend_ruim",
        "consumidor_data_bom", "consumidor_data_ruim",
        "consumidor_ia_bom", "consumidor_ia_ruim",
    ]
    versionados = _versionados()
    for nome in esperadas:
        prefixo = f"tests/fixtures/{nome}/"
        assert any(p.startswith(prefixo) for p in versionados), (
            f"fixture `{nome}` não tem nenhum arquivo versionado")
