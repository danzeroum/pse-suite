"""S-02 do conserto — a régua deixa de dizer duas coisas opostas.

Medido contra alvo real: P-01 acusou `test@example.com` num script de seed —
**três CRÍTICOs**. E `example.com` já estava na lista `ignorar` de
`third-party-endpoints.yaml` desde sempre, consultada por S-04. A mesma régua
dizia coisas opostas sobre o mesmo domínio, dependendo de qual check a lia.

A RFC 2606 e a RFC 6761 reservam `example.com/.org/.net` e os TLDs `.test`,
`.example`, `.invalid` e `.localhost` justamente para que ninguém precise
inventar domínio em documentação, seed e teste. Acusar quem seguiu a RFC é
punir o caso correto — D-08, o defeito que a suíte cobra dos outros.

O LIMITE É ESTREITO DE PROPÓSITO, e os testes de mordida deste arquivo são o
que o mantém: vale só para **valor literal** de e-mail em domínio reservado.
`user.email` vindo de variável segue disparando, CPF e telefone não têm
equivalente reservado e seguem valendo sempre, e um payload que traz um
e-mail reservado **e** um vivo continua sendo achado.
"""
import pytest

from pse.checks import _dominio
from pse.engine.context import Contexto
from pse.engine.runner import executar

CFG = {"catalog_path": "catalog.yaml"}


@pytest.fixture
def ctx(tmp_path):
    return Contexto(tmp_path)


def escrever(base, arquivos):
    for nome, corpo in arquivos.items():
        alvo = base / nome
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(corpo, encoding="utf-8")
    return executar(base, {"privacy", "security"}, CFG)


def de(res, cid):
    return [f for f in res["findings"] if f.check_id == cid]


# ================================================== o caso que foi medido
@pytest.mark.pse_privacy
def test_email_reservado_literal_em_seed_nao_dispara(tmp_path):
    """O caso literal do reconhecimento: três CRÍTICOs num script de seed."""
    res = escrever(tmp_path, {
        "scripts/seed.py":
            'import logging\n'
            'logger = logging.getLogger(__name__)\n'
            'logger.info("criando usuario test@example.com")\n'})
    assert not de(res, "P-01"), [f.snippet for f in de(res, "P-01")]


@pytest.mark.pse_privacy
@pytest.mark.parametrize("email", [
    "test@example.com", "user@example.org", "qa@example.net",
    "dev@meuapp.test", "x@servico.invalid", "a@algo.localhost",
    "b@mail.example.com",
])
def test_dominios_reservados_nao_disparam(tmp_path, email):
    res = escrever(tmp_path / email.replace("@", "_"), {
        "seed.py": f'import logging\nlogging.info("cliente {email}")\n'})
    assert not de(res, "P-01"), email


# ============================================ o que NÃO pode ter afrouxado
@pytest.mark.pse_privacy
@pytest.mark.mordida
def test_email_de_dominio_vivo_segue_disparando(tmp_path):
    res = escrever(tmp_path, {
        "app.py":
            'import logging\n'
            'logging.info("cliente joao.silva@bancoreal.com.br")\n'})
    assert de(res, "P-01"), "e-mail real parou de disparar — afrouxou demais"


@pytest.mark.pse_privacy
@pytest.mark.mordida
def test_variavel_de_pii_segue_disparando(tmp_path):
    """O vetor que importa, e o que a exceção não toca: `user.email` vindo de
    dado de titular real. A exceção é só para literal."""
    res = escrever(tmp_path, {
        "app.py":
            'import logging\n'
            'def f(user):\n'
            '    logging.info("cadastro %s", user.email)\n'})
    achados = de(res, "P-01")
    assert achados and achados[0].severidade == "CRITICO"


@pytest.mark.pse_privacy
@pytest.mark.mordida
def test_cpf_literal_segue_disparando(tmp_path):
    """CPF e telefone não têm domínio reservado equivalente — a exceção não
    os alcança, e alcançá-los seria afrouxar PII real."""
    res = escrever(tmp_path, {
        "app.py": 'import logging\nlogging.info("doc 529.982.247-25")\n'})
    assert de(res, "P-01")


@pytest.mark.pse_privacy
@pytest.mark.mordida
def test_um_email_vivo_ao_lado_de_um_reservado_ainda_dispara(tmp_path):
    """A pergunta é *todos são reservados?*, não *algum é?*. Basta um e-mail
    de domínio vivo para o vazamento existir, e a forma mais fácil de
    esconder um e-mail real seria colocar um `@example.com` ao lado."""
    res = escrever(tmp_path, {
        "app.py":
            'import logging\n'
            'logging.info("de test@example.com para joao@bancoreal.com.br")\n'})
    assert de(res, "P-01"), "um e-mail reservado ao lado escondeu o real"


# ========================================================= a régua coerente
def test_o_que_s04_ignora_p01_tambem_ignora(ctx):
    """A incoerência que a rodada fechou: a mesma lista, lida pelos dois."""
    for dominio in ctx.data["third-party-endpoints"]["ignorar"]:
        if "." not in str(dominio) or str(dominio)[0].isdigit():
            continue
        assert _dominio.dominio_reservado(ctx, dominio), dominio


def test_dominio_vivo_nao_e_reservado(ctx):
    for dominio in ("bancoreal.com.br", "gmail.com", "exemplo.com",
                    "example.com.br", "notexample.com"):
        assert not _dominio.dominio_reservado(ctx, dominio), dominio


def test_tld_reservado_casa_por_sufixo(ctx):
    """`api.meuapp.test` entra sem precisar ser listado — a lista de
    subdomínios possíveis nunca fecharia."""
    assert _dominio.dominio_reservado(ctx, "api.meuapp.test")
    assert _dominio.dominio_reservado(ctx, "qualquer.coisa.invalid")
    assert not _dominio.dominio_reservado(ctx, "meuapp.testing.com")


def test_so_o_dominio_e_julgado_nao_a_parte_local(ctx):
    assert _dominio.email_reservado(ctx, "joao.silva@example.com")
    assert not _dominio.email_reservado(ctx, "test@bancoreal.com.br")
