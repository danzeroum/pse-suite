"""O lado conforme: o input passa por guarda antes do modelo, e a saida do
modelo e validada antes de qualquer sink."""
import llm_client as llm
from flask import request

from db import cursor
from guarda import normalizar_nfkc, truncar, delimitar, validar_sql


def resumir_ticket():
    bruto = request.body
    limpo = delimitar(truncar(normalizar_nfkc(bruto), 4000))
    return llm.complete(limpo)


def responder_consulta():
    pergunta = sanitizar_entrada(request.args["q"])
    resposta = llm.complete(pergunta)
    cursor.execute(validar_sql(resposta))
    return resposta


def sanitizar_entrada(texto):
    return delimitar(truncar(normalizar_nfkc(texto), 2000))
