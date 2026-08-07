"""Tokens do Trabalho A: nomes de variavel valem, valores vivem no cofre.

Os testes precisam de um valor qualquer no ambiente para provar o caminho
feliz — e para provar que esse valor NUNCA aparece num trace.
"""
import pytest

from helpers_alvo import TOKEN_A, TOKEN_B


@pytest.fixture(autouse=True)
def _tokens(monkeypatch):
    monkeypatch.setenv(TOKEN_A, "token-de-teste-a")
    monkeypatch.setenv(TOKEN_B, "token-de-teste-b")


# ---------------------------------------------------- camada dinamica
@pytest.fixture(scope="session")
def alvo_de_fixture():
    """Um servidor REAL em loopback, para o navegador visitar de verdade.

    Escopo de sessao: subir e derrubar um servidor por teste seria pagar
    caro por nada — cada teste abre a sua propria observacao, e e a
    observacao que precisa nascer virgem, nao o servidor.
    """
    from alvo_fixture.servir import AlvoDeFixture
    with AlvoDeFixture() as alvo:
        yield alvo


@pytest.fixture
def observacao_falsa():
    """Fabrica de NetworkLog, para provar a REGRA de um check sem navegador.

    Os dois caminhos existem de proposito e provam coisas diferentes: o log
    fabricado prova o que separa achado de nao-achado; o alvo de fixture
    prova que o motor observa. Um sem o outro deixa metade sem prova.
    """
    from pse.navegador.rede import (CookieObservado, NetworkLog,
                                    RequisicaoObservada)

    def montar(url="https://alvo.example.org/", requisicoes=(), cookies=(),
               html=""):
        return NetworkLog(
            url=url,
            requisicoes=tuple(RequisicaoObservada(u) for u in requisicoes),
            cookies=tuple(CookieObservado(**c) if isinstance(c, dict)
                          else c for c in cookies),
            html=html, engine="fixture")
    return montar
