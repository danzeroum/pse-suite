"""A TRAVA — documentação de testes obrigatória, conferida a cada merge.

Gerar a doc não basta. Um gerador que ninguém é obrigado a rodar produz doc
velha do mesmo jeito; a única diferença é de quem é a culpa. Alguém acrescenta
P-25, esquece de rodar `python -m pse.testes`, e o merge entra com a doc
afirmando 57 checks quando há 58. A doc mente, e ninguém percebe até precisar
dela.

Este arquivo é o que fecha o buraco: ele REGENERA os dois documentos em
memória e COMPARA com o que está commitado. Divergiu, reprova — e a mensagem
diz exatamente como regenerar. O desenvolvedor não escolhe atualizar; o merge
o obriga.

É a doutrina da suíte aplicada a ela mesma. A PSE cobra dos alvos que a
ausência de achado não seja confundida com ausência de defeito; aqui ela cobra
de si que a ausência de divergência seja *verificada*, e não presumida. Uma
trava que o vigiado pode desligar não é trava — por isso não há flag, variável
de ambiente nem marcador que pule este arquivo.

E há uma segunda trava, que transforma o índice de lista em prova: **todo
check tem de ter teste**. Um documento que lista 57 checks e 559 funções sem
nunca verificar que as segundas cobrem os primeiros é meia-garantia. Check
órfão reprova o merge tanto quanto doc desatualizada — e foi assim que S-08
apareceu, depois de existir sem teste próprio desde a fase 1.

DETERMINISMO É PRÉ-REQUISITO, não detalhe. Gerador que produz bytes diferentes
a cada execução faz a comparação falhar por ruído; o time aprende a ignorar o
vermelho, e a trava morre de fadiga — o mesmo mecanismo pelo qual
falso-positivo em CRÍTICO ensina a ignorar o laudo. O primeiro teste do
arquivo é o de determinismo, e ele vale mais que os outros somados.
"""
import ast
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from pse import catalogo, testes

RAIZ = Path(__file__).resolve().parent.parent
WORKFLOWS = RAIZ / ".github" / "workflows"

REGENERAR = (
    "\n\n  Regenere e commite:\n"
    "    python -m pse.testes > docs/TESTES.md\n"
    "    python -m pse.testes --indice > docs/INDICE-DE-TESTES.md\n")


def _id_hipotetico(numero) -> str:
    """ID fabricado para as mordidas — composto em tempo de execução.

    Escrever `"P-78"` como literal aqui faria o próprio índice contar
    `test_indice.py` como cobertura do check hipotético (e, fora do
    monkeypatch, como referência fantasma). A trava morderia a mão que a
    testa. Compondo o ID, ele não chega à árvore sintática como literal — que
    é exatamente a âncora que o gerador usa (D-01).
    """
    return "P-%d" % numero


def _ficha_sintetica(tmp_path, nome, corpo):
    """Uma ficha de teste feita de código real, sem sujar `tests/`."""
    alvo = tmp_path / nome
    alvo.write_text(corpo, encoding="utf-8")
    return testes.analisar_arquivo_de_teste(alvo)


# ============================================================== determinismo
# Vale mais que o resto somado: sem ele, a comparação falha por ruído, o time
# aprende a ignorar o vermelho, e as duas travas abaixo morrem de fadiga.
def test_o_gerador_e_byte_identico_entre_execucoes():
    assert testes.gerar_documento() == testes.gerar_documento()


def test_o_indice_e_byte_identico_entre_execucoes():
    assert testes.gerar_indice() == testes.gerar_indice()


def test_o_gerador_e_identico_em_processo_novo():
    """Duas chamadas no mesmo processo compartilham dicionários já montados —
    e é justamente aí que uma iteração não-ordenada passaria despercebida.
    Processo novo tem hash seed novo: se algum `set` chegou ao texto sem
    `sorted`, é aqui que aparece."""
    def rodar():
        r = subprocess.run([sys.executable, "-m", "pse.testes"],
                           cwd=RAIZ, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        return r.stdout
    assert rodar() == rodar()


def test_nenhum_set_cru_chega_ao_texto():
    """A representação de um `set` no meio de uma tabela é o sintoma exato de
    iteração não-ordenada. Ela sobrevive a um teste de determinismo que roda
    duas vezes com a mesma seed — e reprova em CI dois meses depois."""
    for texto in (testes.gerar_documento(), testes.gerar_indice()):
        assert "{'" not in texto and '{"' not in texto, "set/dict cru no texto"


# ================================================= o timestamp fora do corpo
def test_o_que_vem_depois_da_marca_nao_entra_na_comparacao():
    """Versão do pacote e data de geração são voláteis de propósito. Sem
    separá-las, um bump de versão reprovaria o merge por ruído — e a trava
    ensinaria o time a ignorá-la."""
    doc = testes.gerar_documento(versao="9.9.9", data="2026-01-01")
    outro = testes.gerar_documento(versao="0.0.1", data="2030-12-31")
    assert doc != outro, "o rodapé deveria carregar os dois valores"
    assert testes.corpo_comparado(doc) == testes.corpo_comparado(outro)


def test_mudanca_de_conteudo_reprova_mesmo_com_a_marca():
    """A contrapartida: cortar no rodapé não pode virar desculpa para o corpo
    mudar de graça."""
    doc = testes.gerar_documento(versao="1.0.0")
    adulterado = doc.replace("Camada A", "Camada Z", 1)
    assert testes.corpo_comparado(doc) != testes.corpo_comparado(adulterado)


# ===================================== A TRAVA: o commitado bate com o gerado
def test_docs_testes_esta_atualizado():
    """O teste que o requisito do dono pediu: o CI regenera e compara ANTES do
    merge. Doc desatualizada mente, e mentir é o defeito que a suíte inteira
    combate."""
    assert testes.DOC_TESTES.is_file(), (
        f"{testes.DOC_TESTES.name} não existe." + REGENERAR)
    commitado = testes.DOC_TESTES.read_text(encoding="utf-8")
    gerado = testes.gerar_documento()
    assert testes.corpo_comparado(commitado) == testes.corpo_comparado(gerado), (
        "docs/TESTES.md está DESATUALIZADO: o código mudou e o documento não."
        + REGENERAR)


def test_indice_esta_atualizado():
    assert testes.DOC_INDICE.is_file(), (
        f"{testes.DOC_INDICE.name} não existe." + REGENERAR)
    commitado = testes.DOC_INDICE.read_text(encoding="utf-8")
    gerado = testes.gerar_indice()
    assert testes.corpo_comparado(commitado) == testes.corpo_comparado(gerado), (
        "docs/INDICE-DE-TESTES.md está DESATUALIZADO." + REGENERAR)


@pytest.mark.mordida
def test_check_novo_sem_regenerar_a_doc_reprova(monkeypatch):
    """A mordida da primeira trava. Um check entra no catálogo, ninguém roda o
    gerador — o merge tem de fechar, nomeando a divergência."""
    novo = _id_hipotetico(77)
    # Derivado, nunca digitado: um numero literal aqui quebraria esta mordida
    # a cada check novo — e o teste que cobra a doc de nao envelhecer nao pode
    # ser o primeiro a envelhecer.
    esperado = len(catalogo.CATALOGO) + 1
    falso = dict(catalogo.CATALOGO)
    falso[novo] = {"pack": "privacy", "domain": ["data"], "tipo": "estatico",
                   "modo": "inventory", "fase": 99, "status": "implementado",
                   "titulo": "check hipotético desta mordida",
                   "base_legal": "—"}
    monkeypatch.setattr(catalogo, "CATALOGO", falso)
    commitado = testes.DOC_TESTES.read_text(encoding="utf-8")
    gerado = testes.gerar_documento()
    assert testes.corpo_comparado(commitado) != testes.corpo_comparado(gerado)
    assert novo in gerado, "a doc gerada tem de nomear o check novo"
    assert f"**{esperado}** checks" in gerado


@pytest.mark.mordida
def test_a_mensagem_de_falha_ensina_a_regenerar():
    """Trava que reprova sem dizer o que fazer vira ticket, não conserto."""
    assert "python -m pse.testes > docs/TESTES.md" in REGENERAR
    assert "python -m pse.testes --indice" in REGENERAR


# ======================================= A TRAVA: todo check tem teste (órfão)
def test_nenhum_check_esta_orfao():
    """Sem isto, o índice seria uma lista. Com isto, é prova."""
    cob = testes.cobertura_de_checks()
    assert not cob["orfaos"], (
        "check(s) sem nenhum teste que os cubra: "
        + ", ".join(cob["orfaos"])
        + ". Um check que nunca foi exercitado é hipótese, não trava. "
          "Escreva o teste — importando o módulo do check ou citando o ID.")


@pytest.mark.mordida
def test_check_sem_teste_e_detectado_como_orfao(monkeypatch):
    novo = _id_hipotetico(78)
    falso = dict(catalogo.CATALOGO)
    falso[novo] = {"pack": "privacy", "domain": ["data"], "tipo": "estatico",
                   "modo": "inventory", "fase": 99, "status": "implementado",
                   "titulo": "check hipotético sem teste nenhum",
                   "base_legal": "—"}
    monkeypatch.setattr(catalogo, "CATALOGO", falso)
    assert novo in testes.cobertura_de_checks()["orfaos"]


def test_a_prova_de_mutacao_nao_conta_como_cobertura():
    """`test_mutacao.py` parametriza sobre `catalogo.implementados()` e alcança
    os 57 por construção. Se contasse como cobertura, nenhum check jamais
    seria órfão e a trava acima não provaria nada — S-08 teria continuado sem
    teste próprio para sempre."""
    cob = testes.cobertura_de_checks()
    sozinhos = [cid for cid, v in cob["por_check"].items()
                if v["arquivos"] == ["test_mutacao.py"]]
    assert not sozinhos, (
        "coberto SÓ pela prova de mutação: " + ", ".join(sozinhos)
        + " — a mutação alcança os 57 por construção e não discrimina nada")


# ============================== A TRAVA: teste citando check que não existe
def test_nenhuma_referencia_fantasma():
    cob = testes.cobertura_de_checks()
    assert not cob["fantasmas"], (
        "teste(s) citando check que não está no catálogo: "
        + "; ".join(f"{d['arquivo']} cita {d['id']}" for d in cob["fantasmas"])
        + f". Ou o check foi renomeado e o teste ficou para trás, ou a citação "
          f"é deliberada — e então declare-a em "
          f"`{testes.DECLARACAO_DE_EXCECAO}` no próprio módulo, com motivo.")


@pytest.mark.mordida
def test_citacao_de_check_inexistente_reprova(tmp_path):
    ausente = _id_hipotetico(88)
    ficha = _ficha_sintetica(tmp_path, "test_fantasma.py",
                             'def test_x():\n    assert "%s" != ""\n' % ausente)
    cob = testes.cobertura_de_checks(fichas=[ficha])
    assert {"arquivo": "test_fantasma.py", "id": ausente} in cob["fantasmas"]


@pytest.mark.mordida
def test_citacao_declarada_nao_reprova_e_aparece_no_indice(tmp_path):
    """A exceção existe, mas é DECLARADA — o padrão D-13 aplicado aqui: a
    lista curada é visível, nunca um filtro silencioso."""
    ausente = _id_hipotetico(88)
    ficha = _ficha_sintetica(
        tmp_path, "test_declarado.py",
        '%s = {"%s": "motivo escrito"}\n' % (testes.DECLARACAO_DE_EXCECAO, ausente)
        + 'def test_x():\n    assert "%s" != ""\n' % ausente)
    cob = testes.cobertura_de_checks(fichas=[ficha])
    assert not cob["fantasmas"]
    assert cob["excecoes_declaradas"] == [
        {"arquivo": "test_declarado.py", "id": ausente,
         "motivo": "motivo escrito"}]


@pytest.mark.mordida
def test_prefixo_de_dominio_nao_vira_fantasma(tmp_path):
    """`FE-01` e `AP-01` são IDs que a suíte barra por outro motivo (prefixo
    codifica pilar, nunca domínio) e que `test_dominio.py` cita de propósito.
    Confundi-los com check renomeado geraria ruído, e ruído mata trava."""
    ficha = _ficha_sintetica(tmp_path, "test_pref.py",
                             'def test_x():\n    assert "FE-01" != "AP-01"\n')
    assert not testes.cobertura_de_checks(fichas=[ficha])["fantasmas"]


# ================================================ a ancoragem no fato (D-01)
@pytest.mark.mordida
def test_check_citado_so_em_comentario_nao_conta_como_coberto(tmp_path):
    """D-01 aplicado ao próprio gerador. Foi exatamente assim que S-08 passou
    despercebido: ele aparecia na docstring de `test_backend_estrato.py` e em
    nenhuma linha de código. Menção não é cobertura."""
    ficha = _ficha_sintetica(
        tmp_path, "test_so_comentario.py",
        '"""Este arquivo fala de P-01 mas não o exercita."""\n'
        '# P-01 também aparece aqui\n'
        'def test_x():\n    assert True\n')
    cob = testes.cobertura_de_checks(fichas=[ficha])
    assert cob["por_check"]["P-01"]["arquivos"] == []


@pytest.mark.mordida
def test_import_do_modulo_do_check_conta_como_cobertura(tmp_path):
    ficha = _ficha_sintetica(
        tmp_path, "test_import.py",
        "from pse.checks.privacy.p20_hash_como_anonimizacao import hash_como_anonimizacao\n"
        "def test_x():\n    assert hash_como_anonimizacao\n")
    cob = testes.cobertura_de_checks(fichas=[ficha])
    assert cob["por_check"]["P-20"]["por_import"] == ["test_import.py"]


# ==================================================== a divisão não tem balde
@pytest.mark.mordida
def test_arquivo_de_teste_sem_familia_declarada_reprova(monkeypatch):
    """Um documento cuja divisão aceita qualquer coisa deixa de dividir. Não
    há balde `outros`: arquivo novo entra numa família ou funda uma."""
    original = testes.arquivos_de_teste

    def com_intruso():
        fichas = original()
        modelo = next(f for f in fichas if f["funcoes"])
        intruso = dict(modelo)
        intruso["arquivo"] = "test_sem_familia.py"
        return fichas + [intruso]

    monkeypatch.setattr(testes, "arquivos_de_teste", com_intruso)
    with pytest.raises(testes.FamiliaAusente) as e:
        testes.familias()
    assert "test_sem_familia.py" in str(e.value)
    assert "pse.testes" in str(e.value), "a mensagem tem de dizer onde declarar"


def test_toda_familia_declarada_existe_no_disco():
    """O simétrico: família apontando para arquivo que já foi removido."""
    for f in testes.familias():
        assert not f["ausentes"], (
            f"família '{f['chave']}' declara arquivo(s) inexistente(s): "
            + ", ".join(f["ausentes"]))


# ======================================================= as lacunas são reais
def test_as_lacunas_saem_do_estado_real_e_nao_de_prosa():
    """Uma doc obrigatória que só listasse o que tem cobertura seria
    propaganda. O teste de fogo: mudar o estado muda a lacuna."""
    antes = {i["titulo"]: i["aberta"] for i in testes.lacunas()}
    assert antes["Checks sem teste que os cubra (orfaos)"] is False
    assert antes["Nenhuma linguagem de servidor alem de Python tem parser"] is True


@pytest.mark.mordida
def test_orfao_novo_abre_a_lacuna_correspondente(monkeypatch):
    novo = _id_hipotetico(79)
    falso = dict(catalogo.CATALOGO)
    falso[novo] = {"pack": "privacy", "domain": ["data"], "tipo": "estatico",
                   "modo": "inventory", "fase": 99, "status": "implementado",
                   "titulo": "órfão de mordida", "base_legal": "—"}
    monkeypatch.setattr(catalogo, "CATALOGO", falso)
    item = [i for i in testes.lacunas()
            if i["titulo"] == "Checks sem teste que os cubra (orfaos)"][0]
    assert item["aberta"] and novo in item["detalhe"]


def test_a_secao_de_lacunas_esta_no_documento():
    doc = testes.gerar_documento()
    assert "# O que NAO esta testado" in doc
    for item in testes.lacunas():
        assert item["titulo"] in doc


def test_as_pendencias_vem_de_ratificacoes_e_nao_de_copia():
    """Ratificada uma pendência, ela sai da tabela de `RATIFICACOES.md` e sai
    deste documento no mesmo commit, sem ninguém lembrar."""
    pend = testes._pendencias_ratificadas()
    assert pend, "a tabela de pendências abertas sumiu de RATIFICACOES.md"
    doc = testes.gerar_documento()
    assert pend[0]["pendencia"][:30] in doc


# ================================================= fail-closed sem alvo válido
def test_sem_arvore_de_testes_o_gerador_recusa(monkeypatch, tmp_path):
    """Produzir um documento dizendo `0 testes` seria pior que não produzir
    nenhum: teria a forma de uma resposta."""
    monkeypatch.setattr(testes, "DIR_TESTES", tmp_path / "nao-existe")
    with pytest.raises(testes.ArvoreAusente):
        testes.arquivos_de_teste()


def test_argumento_desconhecido_e_entrada_invalida():
    assert testes._main(["pse.testes", "--indice"]) == 0
    assert testes._main(["pse.testes", "--seila"]) == 30


# ============================================ a trava roda no workflow de PR
def _workflows():
    assert WORKFLOWS.is_dir(), (
        f"{WORKFLOWS} não existe. A trava só vale se rodar ANTES do merge — "
        f"conferir localmente é o que já não estava acontecendo.")
    arquivos = sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml"))
    assert arquivos, "nenhum workflow declarado"
    return {p.name: yaml.safe_load(p.read_text(encoding="utf-8")) for p in arquivos}


def _jobs_com_pytest():
    saida = []
    for nome, wf in _workflows().items():
        gatilhos = wf.get("on") or wf.get(True) or {}
        for job_id, job in (wf.get("jobs") or {}).items():
            passos = [str(p.get("run", "")) for p in (job.get("steps") or [])]
            if any("pytest" in p for p in passos):
                saida.append((nome, job_id, job, passos, gatilhos))
    return saida


def test_existe_workflow_que_roda_a_suite():
    assert _jobs_com_pytest(), (
        "nenhum job de CI roda pytest — sem isso não há 'antes do merge'")


def test_o_workflow_dispara_em_pull_request():
    for nome, job_id, _, _, gatilhos in _jobs_com_pytest():
        assert "pull_request" in gatilhos, (
            f"{nome}:{job_id} não dispara em pull_request — a conferência "
            f"aconteceria depois do merge, que é tarde")


def test_a_trava_roda_no_mesmo_job_que_a_suite():
    """O requisito é explícito: mesmo job. Job separado pode ser desabilitado
    sozinho, ou ficar não-obrigatório na proteção de branch, sem que ninguém
    note que a conferência parou."""
    achou = False
    for nome, job_id, _, passos, _ in _jobs_com_pytest():
        tem_trava = any("test_indice.py" in p for p in passos)
        tem_suite = any("test_indice.py" not in p and "pytest" in p for p in passos)
        if tem_trava and tem_suite:
            achou = True
    assert achou, (
        "nenhum job roda a trava (tests/test_indice.py) e a suíte completa "
        "juntos — a trava tem de morrer no mesmo lugar em que a suíte morre")


def test_a_trava_nao_tem_como_ser_desligada():
    """Fail-closed sem flag, como todo gate da suíte. `continue-on-error`
    transformaria o vermelho em aviso, e aviso ninguém lê."""
    for nome, job_id, job, _, _ in _jobs_com_pytest():
        assert not job.get("continue-on-error"), f"{nome}:{job_id}"
        for passo in job.get("steps") or []:
            if "pytest" in str(passo.get("run", "")):
                assert not passo.get("continue-on-error"), f"{nome}:{job_id}"
                assert "|| true" not in str(passo.get("run")), f"{nome}:{job_id}"


def test_nenhum_skip_condicional_neste_arquivo():
    """A trava não pode se pular. Nenhum `skipif`, nenhum `skip`, nenhuma
    variável de ambiente que a apague — senão o vigiado desliga a trava."""
    arvore = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    for no in ast.walk(arvore):
        if isinstance(no, ast.Attribute) and no.attr in ("skip", "skipif", "xfail"):
            raise AssertionError(f"desligamento em test_indice.py: {no.attr}")
        if isinstance(no, ast.Attribute) and no.attr == "environ":
            raise AssertionError("trava lendo variável de ambiente")
