"""Fixture CONFORME — o teste positivo de cada check corrigido.

Cada bloco aqui e a versao *certa* de uma violacao do consumidor_ruim.
Se algum check acusar este diretorio, ele tem falso-positivo: e o outro
lado da mordida, e falso-positivo em CRITICO ensina o operador a ignorar
o laudo (plano §9 risco 1).
"""
import logging

from mascaramento import mascarar
from revisao import enviar_para_revisao_humana
from fairness import aplicar_equalized_odds

logger = logging.getLogger(__name__)


def cadastrar(cpf, email):
    # P-01 conforme: o dado pessoal passa por mascaramento antes de logar.
    logger.info("novo cadastro cpf=%s email=%s", mascarar(cpf), mascarar(email))


def negar_credito(user, score):
    # E-04 conforme: a rota de revisao humana e uma CHAMADA que executa,
    # nao um comentario dizendo que um dia existira.
    if score < 500:
        return enviar_para_revisao_humana(user, motivo="score_abaixo_do_piso")
    return {"aprovado": True}


def calcular_score(renda, cep):
    # E-05 conforme: a variavel proxy passa por ajuste de fairness real.
    features = {"renda": renda, "cep": cep}
    return aplicar_equalized_odds(features)
