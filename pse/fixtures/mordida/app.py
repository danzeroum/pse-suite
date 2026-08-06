"""Fixture EMBARCADA NO PACOTE — a prova de mordida do consumidor (D-06).

O passo negativo documentado em COMO-ADOTAR derivava o caminho da fixture
do pacote instalado, mas `tests/` nunca ia no wheel: no consumidor real
aquele passo quebrava por arquivo inexistente, e a metrica "prova de
mordida: 100% dos workflows" era falsa por construcao.

Esta fixture viaja dentro do wheel. `pse --self-test` a audita e exige
vermelho: se a suite ficar verde aqui, a trava quebrou — e o consumidor
descobre isso no proprio CI, sem clonar este repositorio.

Valores FALSOS, plantados de proposito.
"""
import logging

logger = logging.getLogger(__name__)

hmac_key = "chave-falsa-plantada-1234"          # P-06 CRITICO


def cadastrar(cpf, email):
    logger.info("novo cadastro cpf=%s email=%s", cpf, email)   # P-01 CRITICO


def negar_credito(user, score):                 # E-04 CRITICO (sem rota humana)
    if score < 500:
        return {"aprovado": False}
    return {"aprovado": True}
