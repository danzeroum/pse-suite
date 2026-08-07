"""S-10 e S-11: o input do usuario entra cru no modelo, e a saida do modelo
sai crua para um sink perigoso."""
import llm_client as llm
from flask import request

from db import cursor


def resumir_ticket():
    # sanitize later
    return llm.complete("resuma o atendimento: " + request.body)     # S-10


def responder_consulta():
    resposta = llm.complete("gere o SQL para: " + request.args["q"])
    cursor.execute(resposta)                                          # S-11
    return resposta


def executar_plano(passo):
    plano = llm.complete(f"como fazer: {request.form['tarefa']}")
    exec(plano)                                                       # S-11
