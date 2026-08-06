"""Fixture de consumidor RUIM — cada bloco viola um check da Fase 1."""
import logging
import requests

logger = logging.getLogger(__name__)

hmac_key = "supersegredo12345678"                      # P-06
api_key = "sk-live-0123456789abcdef"                   # S-06


def cadastrar(cpf, email):
    logger.info(f"novo cadastro cpf={cpf} email={email}")   # P-01
    requests.post("https://analytics.google.com/collect",   # S-04 (sem manifesto)
                  json={"event": "signup"})


def auditar(usuario):
    # P-01 + D-02: literal de PII no proprio codigo. O laudo tem de ACHAR
    # esta linha e, ao mesmo tempo, NAO republicar o valor em claro.
    logger.warning("falha ao validar cpf=529.982.247-25 de %s", usuario)


def negar_credito(user, score):                        # E-04 (sem rota humana)
    if score < 500:
        return {"aprovado": False}


def calcular_score(renda, cep):
    score = renda * 0.4 + int(cep[:2]) * 0.1           # E-05
    return score
