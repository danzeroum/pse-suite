"""D-13 — a regua curada e vigiada.

Em 1eb616b, remover `cpf` de pii-patterns.yaml deixava os 6 testes verdes:
a cobertura de P-01 encolhia em silencio. Era exatamente o cenario que o
README usa para justificar a regua morar neste repositorio.

Este modulo torna a edicao da regua *bloqueante*: remover um termo exige
alterar este teste no mesmo PR — visivel, versionado e revisavel. O
`catalog_hash` no laudo (Gap 3) faz a outra metade: torna a edicao
*evidente na evidencia*, mesmo que alguem altere teste e regua juntos.
"""
import pytest

from pse.engine.context import Contexto

# Piso curado. Nao e a lista inteira — e o minimo que nao pode sumir sem
# que alguem assine embaixo. Acrescentar termos a regua nao quebra o teste;
# remover, sim.
PISO = {
    "pii-patterns": {
        "identificadores": {"cpf", "rg", "cnh", "passaporte", "cns", "titulo_eleitor"},
        "contato": {"email", "telefone", "celular", "endereco"},
        "credenciais": {"password", "senha", "token", "api_secret"},
    },
    "sensitive-fields": {
        "sensiveis": {"raca", "etnia", "religiao", "biometria", "saude",
                      "orientacao_sexual", "opiniao_politica",
                      "filiacao_sindical", "dado_genetico", "genero"},
    },
    "prohibited-filters": {
        "proxies_discriminacao": {"cep", "bairro", "nome_mae", "genero",
                                  "raca", "etnia"},
    },
}


# `credenciais` tem o piso INVERTIDO alem do normal: aqui, ACRESCENTAR termo
# encolhe a cobertura. Cada valor sintetico e uma credencial que a suite deixa
# de tratar como bloqueante, e inchar essa lista e a forma mais silenciosa de
# desligar P-06 e S-06 — mais silenciosa que apagar o check, porque os
# achados continuam saindo, em MEDIO, e o laudo parece o mesmo.
VALORES_QUE_NAO_PODEM_ENTRAR = {
    # Sequencia de digitos aparece dentro de segredo real com facilidade.
    # `123456` chegou a entrar e rebaixou as DUAS mutacoes canonicas.
    "123456", "1234567890", "0123456789", "000000", "111111",
    # Radicais curtos demais: casariam com metade dos segredos do mundo.
    "a", "ab", "abc", "key", "secret", "token", "pass", "pwd",
    # Marcas que descrevem AMBIENTE, nao valor descartavel. Um segredo de
    # staging e um segredo.
    "staging", "homolog", "dev", "local", "sandbox", "qa",
}


@pytest.fixture(scope="module")
def regua(tmp_path_factory):
    return Contexto(tmp_path_factory.mktemp("vazio")).data


@pytest.mark.parametrize("arquivo,grupo,esperado", [
    (a, g, termos) for a, grupos in PISO.items() for g, termos in grupos.items()
])
def test_piso_da_regua_intacto(regua, arquivo, grupo, esperado):
    presentes = set(regua[arquivo][grupo])
    faltando = esperado - presentes
    assert not faltando, (
        f"termo(s) removido(s) de pse/data/{arquivo}.yaml [{grupo}]: "
        f"{sorted(faltando)}. Remover da regua encolhe a cobertura dos checks "
        f"em silencio — se a remocao e intencional, altere o PISO neste teste "
        f"no mesmo PR, para que a decisao fique assinada."
    )


def test_terceiros_conhecidos_cobrem_as_tres_categorias(regua):
    cats = regua["third-party-endpoints"]["categorias"]
    assert {"analytics", "llm", "cdn"} <= set(cats)
    assert all(cats[c] for c in ("analytics", "llm", "cdn"))


def test_ignorar_nao_engole_host_real(regua):
    """A allowlist de hosts ignorados so pode conter dominios de exemplo.

    Um `ignorar: [amazonaws.com]` faria S-04 parar de ver metade da nuvem
    sem nenhum erro — a mesma classe de defeito que D-13.
    """
    permitidos = {"localhost", "127.0.0.1", "example.com", "example.org",
                  "example.net", "w3.org", "json-schema.org", "schema.org",
                  "localhost.localdomain"}
    excedente = set(regua["third-party-endpoints"]["ignorar"]) - permitidos
    assert not excedente, (
        f"hosts fora da lista de exemplos entraram em `ignorar`: {sorted(excedente)}"
    )


# ============================================ a regua do conserto de severidade
def test_piso_dos_caminhos_de_teste(regua):
    """Remover uma marca daqui faz P-06/S-06 voltarem a reprovar o CI por
    causa de fixture — o defeito que a rodada de reconhecimento mediu."""
    marcas = {str(m).lower() for m in regua["credenciais"]["caminhos_de_teste"]}
    piso = {"/tests/", "/fixtures/", "/__tests__/", "conftest",
            "^test_", "_test$", ".test.", ".spec."}
    faltando = piso - marcas
    assert not faltando, (
        f"marca(s) removida(s) de credenciais.yaml [caminhos_de_teste]: "
        f"{sorted(faltando)} — sem elas o gate volta a ser dirigido por fixture")


def test_a_posicao_da_marca_esta_declarada(regua):
    """`test_` sem ancora casaria `generate_test_password.py`, que e o unico
    caso REAL dos 19 medidos. A ancora nao e estilo: e o que impede o conserto
    de cegar o achado que ele existe para preservar."""
    marcas = {str(m).lower() for m in regua["credenciais"]["caminhos_de_teste"]}
    assert "test_" not in marcas, (
        "`test_` sem `^` casa em qualquer posicao do nome e cega "
        "`generate_test_password.py` — use `^test_`")
    assert "_test" not in marcas, "use `_test$`, nao `_test`"


def test_valor_sintetico_nao_pode_casar_segredo_real(regua):
    """O piso INVERTIDO. Acrescentar termo a esta lista encolhe a cobertura, e
    e o jeito mais silencioso de desligar os dois checks: os achados continuam
    saindo, em MEDIO, e o laudo parece o mesmo de antes."""
    valores = {str(v).lower() for v in regua["credenciais"]["valores_sinteticos"]}
    intrusos = valores & VALORES_QUE_NAO_PODEM_ENTRAR
    assert not intrusos, (
        f"marca(s) que rebaixariam segredo real em credenciais.yaml: "
        f"{sorted(intrusos)}. Marca que rebaixa por acidente e pior que marca "
        f"que falta — a primeira tira do gate um segredo vivo.")
    curtas = {v for v in valores if len(v) < 4}
    assert not curtas, (
        f"marca(s) curta(s) demais: {sorted(curtas)} — casariam por acidente")


def test_a_regua_de_credencial_nao_suprime(regua):
    """A garantia de contrato: nao existe grupo `ignorar` nesta regua. Se um
    dia existir, alguem esta transformando rebaixamento em supressao."""
    assert set(regua["credenciais"]) == {"caminhos_de_teste", "valores_sinteticos"}, (
        "grupo novo em credenciais.yaml — se for lista de supressao, a trava "
        "virou algo que o vigiado desliga movendo o segredo de arquivo")


def test_piso_dos_dominios_reservados(regua):
    """A lista que P-01, S-03 e S-04 leem JUNTOS desde a rodada de conserto.
    Remover `example.com` daqui reabre os tres CRITICOs de seed que a rodada
    de reconhecimento mediu; remover um TLD reabre a mesma classe."""
    tp = regua["third-party-endpoints"]
    ignorar = {str(d).lower() for d in tp["ignorar"]}
    assert {"example.com", "example.org", "example.net", "localhost"} <= ignorar
    tlds = {str(t).lower() for t in tp["tld_reservados"]}
    assert {".test", ".invalid", ".localhost", ".example"} <= tlds


def test_dominio_vivo_nunca_entra_como_reservado(regua):
    """Piso invertido. Acrescentar um dominio real aqui cega P-01, S-03 e S-04
    de uma vez — e o laudo segue com a mesma cara, sem achado nenhum."""
    tp = regua["third-party-endpoints"]
    reservados = {str(d).lower() for d in tp["ignorar"]}
    proibidos = {"gmail.com", "outlook.com", "hotmail.com", "com", "com.br",
                 "amazonaws.com", "googleapis.com", "sendgrid.net"}
    intrusos = reservados & proibidos
    assert not intrusos, (
        f"dominio vivo tratado como reservado: {sorted(intrusos)} — isto cega "
        f"P-01, S-03 e S-04 ao mesmo tempo, sem mudar a cara do laudo")
    tlds = {str(t).lower() for t in tp["tld_reservados"]}
    assert not (tlds & {".com", ".br", ".net", ".org", ".io", ".dev"}), (
        "TLD vivo na lista de reservados — casa por sufixo e apaga a internet "
        "inteira do alcance dos tres checks")
