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
