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
