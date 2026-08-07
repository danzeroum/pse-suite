"""A trava de check-órfão — todo check catalogado é exercitado por um teste.

Selar antes de expandir. Os três refinos que consertaram o gate precisam estar
travados por teste permanente **antes** de a suíte ganhar superfície nova —
senão uma rodada futura de checks reintroduz o falso-positivo que acabou de
sair, e ninguém percebe porque o laudo continua com a mesma cara.

Esta trava é a metade que faltava. `test_ratificacao.py` sela as decisões;
esta sela a **cobertura**: um check que existe no catálogo e que nenhum teste
roda é uma hipótese com número de identidade. Ele aparece no laudo, conta na
métrica de cobertura, e ninguém nunca o viu decidir nada.

DUAS EVIDÊNCIAS CONTAM, e as duas são âncora no fato:

  * **importação** — o teste importa o módulo do check;
  * **ID exercitado** — o ID aparece como literal dentro de uma função de
    teste que ALCANÇA o motor (`executar`, `main`, `provar`, `autoprova`),
    direta ou por um auxiliar do módulo.

O que **não** conta é citação em docstring ou comentário — não chegam à árvore
sintática. E não conta asserção que apenas verifica que o check está no
catálogo: isso testa a DECLARAÇÃO, não o comportamento. Foi por aí que S-08
passou anos coberto no papel — ele aparecia na docstring de outro teste, e em
nenhuma linha de código.

A prova de mutação canônica também não conta, e a exclusão é deliberada: ela
parametriza sobre `catalogo.implementados()` e alcança todos por construção.
Se contasse, nenhum check jamais seria órfão e esta trava não provaria nada.
Ela prova que o inverso canônico fica vermelho; não prova que o caso conforme
fica quieto, nem que o skip nomeia o motivo.
"""
import ast
from pathlib import Path

import pytest

from pse import catalogo
from pse.engine.registry import CHECKS
from pse.engine.runner import _carregar_checks

RAIZ = Path(__file__).resolve().parent.parent
DIR_TESTES = RAIZ / "tests"

# As portas por onde um teste EXERCITA um check. `provar_todas` e `autoprova`
# entram porque são entradas legítimas do motor; `provar` sozinha, não — ela é
# a prova de mutação, que alcança todos por construção e não discrimina nada.
MOTORES = ("executar", "main", "autoprova")

# Um módulo de teste que precise citar um ID fora do catálogo — para provar
# que ele NÃO existe, que é o caso de P-12/S-09 enquanto A-01/A-02 não forem
# respondidas — declara a exceção neste nome, com motivo. Declarada, ela é
# visível; calada, reprova. É o padrão da régua: a exceção é curada, nunca
# silenciosa.
DECLARACAO_DE_EXCECAO = "CHECKS_FORA_DO_CATALOGO"


def _alcanca(nome, chamadas_de, vistos=None):
    vistos = vistos if vistos is not None else set()
    if nome in vistos:
        return False
    vistos.add(nome)
    for chamada in chamadas_de.get(nome, ()):
        if chamada in MOTORES:
            return True
        if chamada in chamadas_de and _alcanca(chamada, chamadas_de, vistos):
            return True
    return False


def _cobertura():
    _carregar_checks()
    modulos = {CHECKS[c]["fn"].__module__: c for c in CHECKS}
    por_check = {c: set() for c in CHECKS}
    fantasmas = []
    for p in sorted(DIR_TESTES.glob("*.py")):
        arvore = ast.parse(p.read_text(encoding="utf-8"))
        chamadas_de = {
            no.name: {ast.unparse(x.func).split(".")[-1]
                      for x in ast.walk(no) if isinstance(x, ast.Call)}
            for no in arvore.body
            if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef))}
        for no in ast.walk(arvore):
            if isinstance(no, ast.ImportFrom) and (no.module or "") in modulos:
                por_check[modulos[no.module]].add(p.name)
        for no in ast.walk(arvore):
            if not isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not no.name.startswith("test_"):
                continue
            if not _alcanca(no.name, chamadas_de):
                continue
            for sub in ast.walk(no):
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                    if sub.value in por_check:
                        por_check[sub.value].add(p.name)
        declaradas = set()
        for no in arvore.body:
            if isinstance(no, ast.Assign) and len(no.targets) == 1:
                alvo = no.targets[0]
                if (isinstance(alvo, ast.Name)
                        and alvo.id == DECLARACAO_DE_EXCECAO
                        and isinstance(no.value, ast.Dict)):
                    declaradas = {k.value for k in no.value.keys
                                  if isinstance(k, ast.Constant)}
        # Citação de ID que não existe: check renomeado com teste para trás.
        for no in ast.walk(arvore):
            if isinstance(no, ast.Constant) and isinstance(no.value, str):
                v = no.value
                if (len(v) == 4 and v[1] == "-" and v[0] in "PSE"
                        and v[2:].isdigit() and not catalogo.existe(v)
                        and v not in declaradas):
                    fantasmas.append((p.name, v))
    return por_check, sorted(set(fantasmas))


def test_nenhum_check_implementado_esta_orfao():
    por_check, _ = _cobertura()
    orfaos = sorted(c for c in catalogo.implementados() if not por_check.get(c))
    assert not orfaos, (
        f"check(s) sem nenhum teste que os exercite: {orfaos}. Um check que "
        f"nunca foi visto decidindo nada é hipótese com número de identidade: "
        f"ele conta na cobertura do laudo e ninguém sabe se morde. Escreva o "
        f"teste — importando o módulo do check, ou citando o ID dentro de uma "
        f"função que rode o motor.")


def test_nenhum_teste_cita_check_que_nao_existe():
    _, fantasmas = _cobertura()
    assert not fantasmas, (
        f"teste(s) citando ID fora do catálogo: {fantasmas}. Ou o check foi "
        f"renomeado e o teste ficou para trás, ou a citação é deliberada — e "
        f"então ela precisa de motivo escrito.")


@pytest.mark.mordida
def test_asercao_sobre_o_catalogo_nao_conta_como_cobertura(monkeypatch, tmp_path):
    """A armadilha que deixou S-08 coberto no papel. Verificar que um check
    consta do catálogo testa a DECLARAÇÃO, não o comportamento — e contar isso
    como cobertura faria a trava aceitar exatamente o que ela existe para
    reprovar."""
    (tmp_path / "test_so_declara.py").write_text(
        "from pse import catalogo\n"
        "def test_x():\n"
        "    assert 'S-08' in catalogo.CATALOGO\n", encoding="utf-8")
    monkeypatch.setattr(__import__(__name__), "DIR_TESTES", tmp_path)
    por_check, _ = _cobertura()
    assert not por_check["S-08"], "asserção de pertencimento contou como teste"


@pytest.mark.mordida
def test_citacao_em_docstring_nao_conta(monkeypatch, tmp_path):
    """D-01 aplicado à própria trava. Foi assim que S-08 pareceu coberto: ele
    aparecia na docstring de `test_trabalho_b.py` e em nenhuma linha de
    código."""
    (tmp_path / "test_so_fala.py").write_text(
        '"""Este arquivo fala de S-08 e não o exercita."""\n'
        "# S-08 também aparece aqui\n"
        "def test_x():\n"
        "    assert True\n", encoding="utf-8")
    monkeypatch.setattr(__import__(__name__), "DIR_TESTES", tmp_path)
    por_check, _ = _cobertura()
    assert not por_check["S-08"]
