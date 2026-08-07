"""S-01 do conserto — credencial em caminho de teste rebaixa, e não some.

A rodada de reconhecimento contra 6 alvos reais mediu o que nenhuma fixture
pegaria: dos **19 CRÍTICOs de credencial** (P-06 + S-06), **18 estavam sob
`tests/`** — `test-secret`, `wrong-password`, um token propositalmente
inválido num teste de rejeição. Em `Central_Inteligencia_Juridica`, os **três**
CRÍTICOs que produziram exit 10 eram *todos* fixtures: o veredito do laudo
estava sendo dirigido por falso-positivo.

É o D-08 virado contra a própria suíte. CRÍTICO falso ensina o operador a
ignorar a categoria inteira — e é nesse silêncio que o 19º caso, o real, passa
junto com os 18.

A CORREÇÃO É REBAIXAR, NUNCA SUPRIMIR, e a distinção é a coisa toda. Ignorar
`tests/` seria a trava que o vigiado desliga movendo o segredo para um arquivo
de teste, e segredo real vaza em teste com frequência suficiente para que a
suposição contrária seja irresponsável. MÉDIO mantém o achado no laudo e o
tira do gate.

O TESTE QUE MAIS IMPORTA DESTE ARQUIVO é
`test_o_decimo_nono_caso_nao_foi_cegado`: consertar 18 falsos não pode custar
o 1 verdadeiro. Se custar, a correção fez o oposto do que devia.
"""
import pytest

from pse.checks import _credencial
from pse.engine.context import Contexto
from pse.engine.runner import executar

CFG = {"catalog_path": "catalog.yaml"}
CREDENCIAIS = ("P-06", "S-06")


@pytest.fixture
def ctx(tmp_path):
    return Contexto(tmp_path)


def rodar(caminho):
    return executar(caminho, {"privacy", "security"}, CFG)


def escrever(base, arquivos):
    for nome, corpo in arquivos.items():
        alvo = base / nome
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(corpo, encoding="utf-8")
    return rodar(base)


def de(res, cid):
    return [f for f in res["findings"] if f.check_id == cid]


def severidades(res, cid):
    return {f.severidade.value for f in de(res, cid)}


# ============================================ o caso que motivou o conserto
@pytest.mark.pse_security
def test_credencial_em_caminho_de_teste_e_medio(tmp_path):
    res = escrever(tmp_path, {
        "tests/test_login.py": 'password = "test-secret-do-fixture"\n'})
    achados = de(res, "P-06")
    assert achados, "o achado NÃO pode sumir — supressão não é o conserto"
    assert severidades(res, "P-06") == {"MEDIO"}


@pytest.mark.pse_security
def test_token_propositalmente_invalido_em_teste_de_rejeicao_e_medio(tmp_path):
    """O caso literal do reconhecimento: um teste que prova que a API recusa
    token inválido precisa de um token inválido escrito ali. Reprovar o CI por
    causa dele é a suíte punindo quem escreveu o teste de segurança."""
    res = escrever(tmp_path, {
        "tests/test_auth.py":
            'def test_recusa():\n'
            '    api_key = "wrong-key-para-provar-a-recusa"\n'})
    assert de(res, "S-06"), "o achado continua visível"
    assert severidades(res, "S-06") == {"MEDIO"}


@pytest.mark.pse_security
def test_valor_sintetico_fora_de_teste_tambem_rebaixa(tmp_path):
    """`changeme` num script de exemplo não é segredo vivo, esteja onde
    estiver. As duas condições são independentes: caminho OU valor."""
    res = escrever(tmp_path, {
        "scripts/bootstrap.py": 'password = "changeme-antes-do-deploy"\n'})
    assert severidades(res, "P-06") == {"MEDIO"}


# ==================================== O TESTE QUE MAIS IMPORTA DESTE ARQUIVO
@pytest.mark.mordida
@pytest.mark.pse_security
def test_o_decimo_nono_caso_nao_foi_cegado(tmp_path):
    """O 19º dos 19: `reconcilia/scripts/generate_test_password.py`.

    Fora de `tests/`, valor não-sintético — o único dos 19 que merecia o
    CRÍTICO. O nome do arquivo contém `test`, e é exatamente por isso que ele
    é o caso perigoso, e ele cegou a suíte DUAS VEZES antes de passar:

    1. a marca `test_` casava em qualquer posição do nome, e
       `generate_test_password.py` virava "arquivo de teste";
    2. corrigida a âncora de caminho, a marca `password` casava DENTRO do
       valor real `SecurePassword123!` e o achado caía do mesmo jeito.

    A segunda só apareceu no reprocessamento dos 6 alvos — o teste original
    usava um literal inventado (`Kp7xR2mQvLt9Wz4Ny6Bd`) e passava. Por isso o
    valor aqui é o VERDADEIRO, copiado do alvo: fixture inventada prova o que
    quem a escreveu já imaginava."""
    res = escrever(tmp_path, {
        "scripts/generate_test_password.py":
            '"""Generate password hash for test user."""\n'
            'password = "SecurePassword123!"\n'})
    achados = de(res, "P-06")
    assert achados, "o segredo real sumiu — a correção cegou o check"
    assert severidades(res, "P-06") == {"CRITICO"}, (
        "consertar 18 falsos-positivos não pode custar o único verdadeiro")


@pytest.mark.mordida
@pytest.mark.pse_security
def test_valor_nao_sintetico_dentro_de_tests_segue_visivel(tmp_path):
    """Segredo real vaza em teste. Ele é rebaixado — não some — e a descrição
    diz por que foi rebaixado, para o revisor decidir com informação."""
    res = escrever(tmp_path, {
        "tests/test_integracao.py":
            'api_key = "AKIAQ7ZLPNM3XBVC2RTY"\n'})
    achados = de(res, "S-06")
    assert achados and achados[0].severidade.value == "MEDIO"
    assert "REBAIXADA" in achados[0].descricao
    assert "caminho de teste" in achados[0].descricao


@pytest.mark.mordida
@pytest.mark.pse_security
def test_comentario_dizendo_que_e_teste_nao_rebaixa(tmp_path):
    """D-01 aplicado ao próprio conserto. A âncora é o caminho e o literal —
    o vigiado não rebaixa nada escrevendo `# só um exemplo` ao lado da chave
    da AWS."""
    res = escrever(tmp_path, {
        "app/config.py":
            '# so um exemplo de teste, nao usar em producao\n'
            'secret_key = "Kp7xR2mQvLt9Wz4Ny6Bd"\n'})
    assert severidades(res, "P-06") == {"CRITICO"}


# ============================================== a fronteira do caminho
def test_diretorio_de_teste_casa_e_nome_parecido_nao(ctx):
    """`tests/` alcança `app/tests/x.py`; `app/testsuite.py` é código de
    produção com um nome infeliz, e continua sendo julgado como produção."""
    assert _credencial.caminho_de_teste(ctx, "app/tests/x.py")
    assert _credencial.caminho_de_teste(ctx, "tests/x.py")
    assert _credencial.caminho_de_teste(ctx, "src/__tests__/a.js")
    assert _credencial.caminho_de_teste(ctx, "app/conftest.py")
    assert _credencial.caminho_de_teste(ctx, "app/user.test.ts")
    assert not _credencial.caminho_de_teste(ctx, "app/testsuite.py")
    assert not _credencial.caminho_de_teste(ctx, "app/latest.py")
    assert not _credencial.caminho_de_teste(ctx, "scripts/generate_test_password.py")


def test_a_marca_casa_delimitada_e_nao_como_pedaco_de_palavra(ctx):
    """`SecurePassword123!` contém `password` e não é sintético; `test-secret`
    contém `test` delimitado e é. `_` e `-` são fronteira, letra e dígito
    não."""
    assert not _credencial.valor_sintetico(ctx, 'p = "SecurePassword123!"')
    assert not _credencial.valor_sintetico(ctx, 'p = "Contestable9xQ"')
    assert not _credencial.valor_sintetico(ctx, 'p = "latestKey42Zz"')
    assert _credencial.valor_sintetico(ctx, 'p = "test-secret"')
    assert _credencial.valor_sintetico(ctx, 'p = "changeme-antes"')
    assert _credencial.valor_sintetico(ctx, 'p = "your_api_key_here"')


def test_o_valor_e_julgado_e_nao_a_linha(ctx):
    """A primeira versão casava contra o snippet inteiro. Como o padrão de
    P-06 exige a palavra `password` na linha e `password` está entre os
    valores sintéticos, TODO achado de P-06 teria sido rebaixado — o check
    inteiro desligado por um detalhe de implementação."""
    assert not _credencial.valor_sintetico(ctx, 'password = "Kp7xR2mQvLt9Wz4"')
    assert _credencial.valor_sintetico(ctx, 'password = "password"')
    assert _credencial.valor_sintetico(ctx, 'api_key = "your_api_key_here"')
    assert _credencial.valor_sintetico(ctx, 'Authorization: Bearer fake-token-aqui')


def test_nao_ha_caminho_que_suprima(ctx):
    """A garantia estrutural: a função só devolve severidade, e a mais baixa
    que ela produz é MÉDIO. Não existe `None`, não existe `INFO`, não existe
    ramo que faça o achado desaparecer."""
    saidas = {
        _credencial.severidade(ctx, rel, snip).value
        for rel in ("tests/a.py", "app/a.py", "conftest.py")
        for snip in ('k = "changeme"', 'k = "Kp7xR2mQvLt9Wz4"')}
    assert saidas <= {"CRITICO", "MEDIO"}
    assert "MEDIO" in saidas and "CRITICO" in saidas


# ================================================== o efeito no veredito
@pytest.mark.mordida
def test_repo_so_com_credencial_de_teste_nao_produz_exit_critico(tmp_path):
    """O efeito medido em Central_Inteligencia_Juridica: os três CRÍTICOs que
    dirigiam o exit 10 eram fixtures. Com o conserto, o gate para de reprovar
    por esse motivo — e continua reprovando pelos motivos reais, se houver."""
    res = escrever(tmp_path, {
        "tests/test_a.py": 'password = "test-secret-um"\n',
        "tests/test_b.py": 'api_key = "test-secret-dois-aaaa"\n',
        "tests/conftest.py": 'secret_key = "fake-para-o-fixture"\n'})
    criticos = [f for f in res["findings"]
                if f.check_id in CREDENCIAIS and f.severidade.value == "CRITICO"]
    assert not criticos, [(f.arquivo, f.titulo) for f in criticos]
    medios = [f for f in res["findings"]
              if f.check_id in CREDENCIAIS and f.severidade.value == "MEDIO"]
    assert len(medios) == 3, "os três continuam no laudo, visíveis"
