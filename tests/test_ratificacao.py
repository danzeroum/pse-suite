"""As cinco ratificações, seladas pelo COMPORTAMENTO e não pela prosa.

`docs/RATIFICACOES.md` torna cada decisão localizável. Este módulo a torna
verdadeira: se uma linha daquela tabela deixar de valer, o teste reprova — e
uma tabela falsa é pior que uma tabela ausente, porque quem a lê para de
verificar.

O arquivo tem duas metades e as duas importam pelo mesmo motivo:

  * as cinco ratificações, cada uma provada pelo caso real que a originou;
  * a prova de que os dois checks bloqueados **não foram implementados**. Um
    check que nasce sem alvo real provando que dispara é hipótese, e a
    severidade dele é chute. "Não implementado no escuro" precisa ser fato
    verificável, não promessa — senão a próxima rodada implementa "só o
    esqueleto" e ninguém percebe.
"""
from pathlib import Path

import pytest

from pse import catalogo
from pse.checks import _credencial
from pse.engine import scan
from pse.engine.context import Contexto
from pse.engine.runner import executar

RAIZ = Path(__file__).resolve().parent.parent
DOC = RAIZ / "docs" / "RATIFICACOES.md"
CFG = {"catalog_path": "catalog.yaml"}


@pytest.fixture
def ctx(tmp_path):
    return Contexto(tmp_path)


def escrever(base, arquivos, packs=("privacy", "security")):
    for nome, corpo in arquivos.items():
        alvo = base / nome
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(corpo, encoding="utf-8")
    return executar(base, set(packs), CFG)


def de(res, cid):
    return [f for f in res["findings"] if f.check_id == cid]


# ============================================================ ratificação 1
@pytest.mark.pse_security
def test_r1_credencial_em_teste_e_medio_e_nao_some(tmp_path):
    res = escrever(tmp_path, {"tests/test_x.py": 'password = "test-secret"\n'})
    achados = de(res, "P-06")
    assert achados, "supressão não é o conserto — o achado tem de continuar lá"
    assert achados[0].severidade.value == "MEDIO"
    assert "REBAIXADA" in achados[0].descricao, (
        "achado rebaixado sem motivo escrito é pior que não rebaixado: o "
        "leitor vê MÉDIO e não sabe se a suíte julgou ou desistiu")


# ============================================================ ratificação 2
#
# A que parece uma exceção e não é. Um teste que prova que a API recusa token
# inválido PRECISA de um token inválido escrito ali — é o caso mais simpático
# que existe, e a tentação é criar uma categoria "não-credencial" e sumir com
# o achado. Isso seria crer na intenção declarada, que é o D-01 ao contrário.
@pytest.mark.pse_security
def test_r2_token_para_rejeicao_e_medio(tmp_path):
    res = escrever(tmp_path, {
        "tests/test_api_security.py":
            'def test_recusa_token_invalido():\n'
            '    api_key = "invalid-token-para-provar-a-recusa"\n'
            '    assert cliente.get("/x", token=api_key).status == 401\n'})
    achados = de(res, "S-06")
    assert achados, "o achado não pode sumir por intenção declarada"
    assert achados[0].severidade.value == "MEDIO"


@pytest.mark.pse_security
@pytest.mark.mordida
def test_r2_comentario_de_intencao_nao_muda_nada(tmp_path):
    """O selo da ratificação 2. Com e sem o comentário, o veredito é o mesmo:
    a suíte não lê intenção. Se um dia o comentário passar a rebaixar (ou a
    suprimir), este teste reprova — e é ele que impede a categoria
    'não-credencial' de nascer pela porta dos fundos."""
    corpo_sem = ('def test_recusa():\n'
                 '    api_key = "Kp7xR2mQvLt9Wz4Ny6Bd"\n')
    corpo_com = ('def test_recusa():\n'
                 '    # intentionally invalid — exists only to be rejected\n'
                 '    api_key = "Kp7xR2mQvLt9Wz4Ny6Bd"\n')
    sem = de(escrever(tmp_path / "a", {"tests/test_s.py": corpo_sem}), "S-06")
    com = de(escrever(tmp_path / "b", {"tests/test_s.py": corpo_com}), "S-06")
    assert len(sem) == len(com) == 1, "o comentário mudou a existência do achado"
    assert sem[0].severidade.value == com[0].severidade.value == "MEDIO"


@pytest.mark.pse_security
@pytest.mark.mordida
def test_r2_intencao_nao_rebaixa_fora_de_teste(tmp_path):
    """A outra ponta: o comentário não pode rebaixar credencial de produção.
    Se rebaixasse, mover o segredo seria desnecessário — bastaria escrever a
    frase certa ao lado dele."""
    res = escrever(tmp_path, {
        "app/config.py":
            '# intentionally invalid, only used in the rejection test\n'
            'secret_key = "Kp7xR2mQvLt9Wz4Ny6Bd"\n'})
    assert de(res, "P-06")[0].severidade.value == "CRITICO"


def test_r2_nao_existe_categoria_nao_credencial():
    """A garantia estrutural: `_credencial.severidade` só devolve CRITICO ou
    MEDIO. Não há `None`, não há `INFO`, não há ramo que faça o achado
    desaparecer — e a régua não tem grupo de supressão."""
    import inspect
    fonte = inspect.getsource(_credencial.severidade)
    assert "return None" not in fonte
    assert "INFO" not in fonte and "BAIXO" not in fonte


# ============================================================ ratificação 3
@pytest.mark.pse_security
@pytest.mark.mordida
def test_r3_o_decimo_nono_caso_segue_critico(tmp_path):
    """O caso que a correção cegou duas vezes antes de passar. Valor real,
    copiado do alvo: fixture inventada prova o que quem a escreveu imaginava."""
    res = escrever(tmp_path, {
        "scripts/generate_test_password.py":
            'password = "SecurePassword123!"\n'})
    assert de(res, "P-06")[0].severidade.value == "CRITICO"


def test_r3_a_posicao_e_a_fronteira_estao_declaradas(ctx):
    assert not _credencial.caminho_de_teste(ctx, "scripts/generate_test_password.py")
    assert _credencial.caminho_de_teste(ctx, "tests/test_login.py")
    assert not _credencial.valor_sintetico(ctx, 'p = "SecurePassword123!"')
    assert _credencial.valor_sintetico(ctx, 'p = "test-secret"')


# ============================================================ ratificação 4
@pytest.mark.pse_privacy
def test_r4_tsx_e_jsx_no_alcance(tmp_path):
    res = escrever(tmp_path, {
        "src/A.tsx": 'console.log("u", user.cpf);\n',
        "src/B.jsx": 'console.log("u", user.email);\n'})
    arquivos = {f.arquivo for f in de(res, "P-01")}
    assert any(a.endswith(".tsx") for a in arquivos), arquivos
    assert any(a.endswith(".jsx") for a in arquivos), arquivos


def test_r4_a_familia_vive_num_lugar_so():
    assert {".js", ".jsx", ".ts", ".tsx"} <= scan.ECMASCRIPT


# ============================================================ ratificação 5
@pytest.mark.pse_privacy
def test_r5_email_reservado_nao_dispara_e_o_vivo_dispara(tmp_path):
    reservado = escrever(tmp_path / "a", {
        "seed.py": 'import logging\nlogging.info("u test@example.com")\n'})
    vivo = escrever(tmp_path / "b", {
        "seed.py": 'import logging\nlogging.info("u joao@bancoreal.com.br")\n'})
    assert not de(reservado, "P-01")
    assert de(vivo, "P-01"), "e-mail real parou de disparar — afrouxou demais"


# ======================================= nada implementado no escuro (A-01/A-02)
#
# A prova de que a pendência é real, e não uma frase. Se um destes reprovar, ou
# o check foi implementado sem a resposta do dono, ou a resposta chegou e
# `docs/RATIFICACOES.md` não foi atualizado — e as duas exigem revisão humana.
CHECKS_BLOQUEADOS = ("P-12", "S-09")

# A trava de órfão reprova todo teste que cite ID fora do catálogo — é assim
# que se pega o teste que ficou para trás depois de um check ser renomeado.
# Aqui os IDs inexistentes SÃO o corpo de prova: eles existem para provar que
# os dois checks bloqueados não foram implementados. A exceção fica declarada,
# com motivo, e some no dia em que os checks entrarem.
CHECKS_FORA_DO_CATALOGO = {
    "P-12": "check de PAN, bloqueado por A-01 — citado aqui para provar que "
            "NÃO está no catálogo",
    "S-09": "ID alternativo do mesmo check de PAN (D-05), pela mesma razão",
}


@pytest.mark.mordida
def test_checks_bloqueados_por_pergunta_do_dono_nao_existem():
    """PAN (A-01) e sigilo em LLM (A-02 + D-07) seguem não implementados.

    Um check que nasce sem alvo real provando que dispara é hipótese, e a
    severidade dele é chute. PAN sem saber se é logado, e sigilo sem saber o
    provider, seriam exatamente isso."""
    for cid in CHECKS_BLOQUEADOS:
        assert cid not in catalogo.CATALOGO, (
            f"{cid} entrou no catálogo. Se A-01/A-02/D-07 foram respondidas, "
            f"atualize docs/RATIFICACOES.md e este teste no mesmo commit; "
            f"senão, o check nasceu no escuro.")


@pytest.mark.mordida
def test_e11_nao_ganhou_refino_de_sigilo_sem_a_declaracao():
    """O refino de sigilo depende de `llm_egress` no config (D-07), cuja
    omissão tem de levar a INDETERMINADO. Enquanto a declaração não existir no
    schema, o refino não pode existir no código — senão ele decide no
    silêncio, que é o oposto do que a especificação pede."""
    regua = RAIZ / "pse" / "data"
    assert not (regua / "sigilo.yaml").exists(), "régua de sigilo sem D-07"
    schema = (RAIZ / "pse" / "schemas").glob("*.json")
    for s in schema:
        assert "llm_egress" not in s.read_text(encoding="utf-8"), (
            f"`llm_egress` apareceu em {s.name} sem D-07 respondida")


def test_as_pendencias_estao_escritas_onde_alguem_acha():
    """Decisão que ninguém encontra não foi tomada — e pendência também não."""
    doc = DOC.read_text(encoding="utf-8")
    for marca in ("A-01", "A-02", "D-07"):
        assert marca in doc, f"{marca} sumiu de RATIFICACOES.md"
    pend = (RAIZ / "docs" / "reconhecimento" / "PENDENCIAS-DO-DONO.md")
    assert pend.is_file() and "A-01" in pend.read_text(encoding="utf-8")


# ============================================== o documento não pode mentir
def test_toda_ratificacao_da_tabela_tem_teste_aqui():
    """A tabela tem 5 linhas; este módulo tem de selar as 5. Uma linha nova
    sem teste torna o documento uma promessa."""
    doc = DOC.read_text(encoding="utf-8")
    linhas = [l for l in doc.splitlines()
              if l.startswith("| ") and l[2:3].isdigit()]
    assert len(linhas) == 5, f"a tabela mudou de tamanho ({len(linhas)} linhas)"
    fonte = Path(__file__).read_text(encoding="utf-8")
    for n in range(1, 6):
        assert f"def test_r{n}_" in fonte, f"ratificação {n} sem teste que a sele"
